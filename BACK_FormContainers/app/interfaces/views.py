from __future__ import annotations

import os
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import login as dj_login, logout as dj_logout

from rest_framework import viewsets, mixins, status, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from drf_spectacular.utils import (
    extend_schema,
    OpenApiTypes,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# ====== Autenticación unificada (sin ciclos) ======
from .auth import (
    BearerOrTokenAuthentication,
    auth_login_issue_token,
    build_user_payload,
)

# ===== Aplicación / Casos de uso =====
from app.application.commands import SaveAndAdvanceCommand, AddTableRowCommand, UpdateTableRowCommand, DeleteTableRowCommand
from app.application.services import SubmissionService, HistoryService
from app.application.questionnaire import QuestionnaireService
from app.application.verification import VerificationService, InvalidImage, ExtractionFailed
from app.domain.exceptions import DomainException

# ===== Manejo de excepciones =====
# (Asumimos que existe en tu repo; no lo tocamos)
from app.interfaces.exception_handlers import translate_domain_exception
from app.infrastructure.storage import load_questionnaire_layout
from app.infrastructure.models import Questionnaire as QuestionnaireModel

# ===== Infraestructura / Adaptadores =====
from app.infrastructure.serializers import (
    QuestionModelSerializer,
    SubmissionModelSerializer,
    SubmissionCreateSerializer,
    ActorModelSerializer,
    SaveAndAdvanceInputSerializer,
    SaveAndAdvanceResponseSerializer,
    AnswerReadSerializer,
    VerificationResponseSerializer,
    VerificationInputSerializer,
    QuestionnaireListItemSerializer,
    HistorialItemSerializer,
    AddTableRowInputSerializer, 
    UpdateTableRowInputSerializer, 
    TableRowOutputSerializer,
    GridDefinitionSerializer
)
from app.infrastructure.factories import get_service_factory
from app.infrastructure.repositories import DjangoSubmissionRepository, DjangoQuestionnaireRepository
from app.infrastructure.models import Question as QuestionModel
from app.application.commands import TableCellInput


# =========================================================
# VISTAS PRIVADAS DE ESQUEMA/DOCS (requiere staff)
# =========================================================
class PrivateSchemaAPIView(SpectacularAPIView):
    """ /api/schema/ — sólo visible a staff. """
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


class PrivateSwaggerUIView(SpectacularSwaggerView):
    """ /api/docs/ — sólo visible a staff. """
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


# =========================================================
# LOGIN UNIFICADO (username o email) + WHOAMI + LOGOUT
# =========================================================
class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    identifier = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not identifier:
            raise serializers.ValidationError("Debes enviar 'username', 'email' o 'identifier'.")
        if not attrs.get("password"):
            raise serializers.ValidationError("Debes enviar 'password'.")
        attrs["identifier"] = identifier
        return attrs


class LoginOutputSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = serializers.DictField()


def _set_auth_cookies(response: Response, request, user) -> Response:
    """
    - csrftoken (para POST con SessionAuthentication)
    - is_staff (ayuda a la UI)
    - auth_username (conveniencia)
    * No guardamos el token en cookie (el front usa Authorization: Bearer).
    """
    from django.middleware.csrf import get_token
    csrftoken = get_token(request)
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrftoken,
        secure=settings.CSRF_COOKIE_SECURE,
        samesite=settings.CSRF_COOKIE_SAMESITE,
    )
    response.set_cookie(
        "is_staff",
        "1" if getattr(user, "is_staff", False) else "0",
        secure=settings.CSRF_COOKIE_SECURE,
        samesite="Lax",
    )
    response.set_cookie(
        "auth_username",
        user.get_username(),
        secure=settings.CSRF_COOKIE_SECURE,
        samesite="Lax",
    )
    return response


def _clear_auth_cookies(response: Response) -> Response:
    for k in (settings.CSRF_COOKIE_NAME, "is_staff", "auth_username"):
        response.delete_cookie(k)
    return response


class UnifiedLoginAPIView(APIView):
    """
    Un único login para todos (staff o no).
    - Emite token (usar como Bearer).
    - Crea sesión Django.
    - Setea cookies no sensibles.
    """
    authentication_classes = []  # AllowAny
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=LoginInputSerializer,
        responses={200: LoginOutputSerializer},
        examples=[
            OpenApiExample("Por username", value={"username": "admin", "password": "******"}),
            OpenApiExample("Por email", value={"email": "admin@acme.com", "password": "******"}),
            OpenApiExample("Con identifier", value={"identifier": "user@acme.com", "password": "******"}),
        ],
    )
    def post(self, request, *args, **kwargs):
        ser = LoginInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        identifier = ser.validated_data["identifier"]
        password = ser.validated_data["password"]

        try:
            user, token_key = auth_login_issue_token(identifier, password)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        dj_login(request, user)

        payload = {"token": token_key, "user": build_user_payload(user)}
        out = LoginOutputSerializer(payload).data
        resp = Response(out, status=status.HTTP_200_OK)
        return _set_auth_cookies(resp, request, user)


class WhoAmIAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], responses={200: serializers.DictField})
    def get(self, request, *args, **kwargs):
        user = request.user
        data = {"user": build_user_payload(user), "auth_via": "token" if request.auth else "session"}
        resp = Response(data, status=status.HTTP_200_OK)
        return _set_auth_cookies(resp, request, user)


class UnifiedLogoutAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], responses={200: serializers.DictField})
    def post(self, request, *args, **kwargs):
        dj_logout(request)
        resp = Response({"detail": "ok"}, status=status.HTTP_200_OK)
        return _clear_auth_cookies(resp)


# =========================================================
# VERIFICACIÓN OCR — autenticado
# =========================================================
class VerificacionUniversalAPIView(APIView):
    """
    Universal OCR verification endpoint.
    Maneja solo HTTP y delega al VerificationService.
    """
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_verification_service(self) -> VerificationService:
        return self._factory.create_verification_service()

    @extend_schema(
        request=VerificationInputSerializer,
        responses={200: VerificationResponseSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Verificación"],
        description="OCR (Google Vision) + reglas por semantic_tag (placa, precinto, contenedor). Requiere usuario autenticado.",
    )
    def post(self, request):
        # Input validation
        serializer = VerificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Extract image file
        if "imagen" not in request.FILES:
            return Response({"error": "Se requiere una imagen."}, status=400)
        imagen_file = request.FILES["imagen"]

        # Delegate to service
        try:
            service = self._get_verification_service()
            result = service.verify_with_question(data["question_id"], imagen_file)
            return Response(VerificationResponseSerializer(result).data)
        except DomainException as e:
            return translate_domain_exception(e)
        except (InvalidImage, ExtractionFailed) as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# =========================================================
# CUESTIONARIO — autenticado
# =========================================================
class PrimeraPreguntaAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_questionnaire_service(self) -> QuestionnaireService:
        return self._factory.create_questionnaire_service()

    @extend_schema(
        parameters=[OpenApiParameter("questionnaire_id", OpenApiTypes.UUID, required=True)],
        responses={200: QuestionModelSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Retorna la primera pregunta (por orden) del cuestionario indicado. Requiere usuario autenticado.",
    )
    def get(self, request):
        qid = request.query_params.get("questionnaire_id")
        if not qid:
            return Response({"error": "Falta 'questionnaire_id'."}, status=400)

        try:
            from uuid import UUID
            svc = self._get_questionnaire_service()

            # 1) Dominio: obtener ENTIDAD de la primera pregunta
            d_question = svc.get_first_question(UUID(qid))  # <- ahora sí pasamos el ID requerido

            # 2) Infra: convertir a modelo para el serializer actual
            from app.infrastructure.repositories import DjangoQuestionRepository
            repo = DjangoQuestionRepository()
            q_model = repo.get_by_id(str(d_question.id))
            if not q_model:
                return Response({"error": "Pregunta no encontrada."}, status=404)

            return Response(QuestionModelSerializer(q_model).data)

        except ValueError:
            return Response({"error": "questionnaire_id inválido."}, status=400)
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# GuardarYAvanzarAPIView (solo la parte relevante)

class GuardarYAvanzarAPIView(APIView):
    """
    Guarda respuesta y avanza a la siguiente.
    """
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_questionnaire_service(self) -> QuestionnaireService:
        return self._factory.create_questionnaire_service()

    # ❌ Ya no dependemos de nombres específicos como "archivo"/"archivos".
    #    Dejamos este helper sin uso o puedes eliminarlo.
    def _prepare_uploads(self, request, data):
        return {}

    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar",
        tags=["Cuestionario"],
        description="Guarda una respuesta y devuelve la siguiente pregunta. Requiere usuario autenticado.",
    )
    def post(self, request):
        # 1) Validación base (IMPORTANTE: pasar el request en el context)
        serializer = SaveAndAdvanceInputSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2) Normalización de alias del front (compatibilidad)
        answer_text = data.get("answer_text")
        if answer_text is None and "value" in request.data:
            raw = request.data.get("value")
            answer_text = None if raw is None else str(raw)

        answer_choice_id = data.get("answer_choice_id")
        if answer_choice_id is None and "choice_id" in request.data:
            from uuid import UUID
            try:
                answer_choice_id = UUID(str(request.data.get("choice_id")))
            except Exception:
                answer_choice_id = None

        # 3) TOMAMOS LOS ARCHIVOS QUE YA AGRUPÓ EL SERIALIZER
        uploads_files = data.get("_uploads", [])
        actor_id = data.get("actor_id")

        # 4) Construir comando de aplicación
        cmd = SaveAndAdvanceCommand(
            submission_id=data["submission_id"],
            question_id=data["question_id"],
            answer_text=answer_text,
            answer_choice_id=answer_choice_id,
            uploads=uploads_files,
            actor_id=actor_id,
        )

        try:
            svc: QuestionnaireService = self._get_questionnaire_service()
            result = svc.save_and_advance(cmd)
            return Response(SaveAndAdvanceResponseSerializer(result).data)
        except DomainException as e:
            return translate_domain_exception(e)
        except DjangoValidationError as e:
            return Response({"error": e.message}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# =========================================================
# SUBMISSIONS — autenticado
# =========================================================
class StandardPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class SubmissionViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        request=AddTableRowInputSerializer,
        responses={200: TableRowOutputSerializer},
        methods=["POST"],
        tags=["Submissions", "Tabular"],
        summary="Agregar una fila (row) a una submission tabular",
        description=(
            "Agrega una línea a una tabla (grid) para este cuestionario. "
            "Cada celda referencia una pregunta (columna). "
            "Para columnas con semantic_tag de actor (proveedor/transportista/receptor) "
            "DEBE enviarse actor_id y no se permite texto libre. "
            "Archivos: enviar como 'cells[<index>][file]'."
        ),
        examples=[
            OpenApiExample(
                "JSON sin archivos",
                value={
                    "submission_id": "00000000-0000-0000-0000-000000000001",
                    "cells": [
                        {"question_id":"...","answer_text":"ABC123"},
                        {"question_id":"...","actor_id":"..."}
                    ]
                }
            )
        ]
    )
    @action(detail=True, methods=["post"], url_path="table-rows")
    def add_table_row(self, request, pk=None):
        ser = AddTableRowInputSerializer(
            data={**request.data, "submission_id": pk},
            context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        svc = get_service_factory().create_tabular_form_service()
        result = svc.add_row(AddTableRowCommand(
            submission_id=ser.validated_data["submission_id"],
            row_index=ser.validated_data.get("row_index"),
            cells=[TableCellInput(**c) for c in ser.validated_data["cells"]],
        ))
        return Response(TableRowOutputSerializer(result).data)

    @extend_schema(
        request=UpdateTableRowInputSerializer,
        responses={200: TableRowOutputSerializer},
        methods=["PUT","PATCH"],
        tags=["Submissions", "Tabular"],
        summary="Actualizar una fila específica",
    )
    @action(detail=True, methods=["put","patch"], url_path=r"table-rows/(?P<row_index>\d+)")
    def update_table_row(self, request, pk=None, row_index=None):
        ser = UpdateTableRowInputSerializer(
            data={**request.data, "submission_id": pk, "row_index": row_index},
            context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        svc = get_service_factory().create_tabular_form_service()
        result = svc.update_row(UpdateTableRowCommand(
            submission_id=ser.validated_data["submission_id"],
            row_index=int(ser.validated_data["row_index"]),
            cells=[TableCellInput(**c) for c in ser.validated_data["cells"]],
        ))
        return Response(TableRowOutputSerializer(result).data)

    @extend_schema(
        responses={204: OpenApiTypes.NONE},
        methods=["DELETE"],
        tags=["Submissions", "Tabular"],
        summary="Eliminar una fila específica",
    )
    @action(detail=True, methods=["delete"], url_path=r"table-rows/(?P<row_index>\d+)")
    def delete_table_row(self, request, pk=None, row_index=None):
        svc = get_service_factory().create_tabular_form_service()
        svc.delete_row(DeleteTableRowCommand(
            submission_id=UUID(str(pk)),
            row_index=int(row_index)
        ))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[OpenApiParameter("as_table", OpenApiTypes.BOOL, required=False)],
        responses={200: OpenApiTypes.OBJECT},
        methods=["GET"],
        tags=["Submissions", "Tabular"],
        summary="Detalle enriquecido (modo tabla)",
        description="Si `as_table=1`, retorna filas (rows) agrupadas por índice."
    )
    @action(detail=True, methods=["get"], url_path="table-rows")
    def list_table_rows(self, request, pk=None):
        # GET /api/v1/submissions/<id>/table-rows/
        svc = get_service_factory().create_tabular_form_service()
        rows = svc.list_rows(UUID(str(pk)))
        return Response({
            "submission_id": str(pk),
            "rows": TableRowOutputSerializer(rows, many=True).data
        })

    @extend_schema(
        request=SubmissionCreateSerializer,
        responses={201: SubmissionModelSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Crea una submission vacía o inicial. Requiere usuario autenticado.",
    )
    def create(self, request, *args, **kwargs):
        serializer = SubmissionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        repo = DjangoSubmissionRepository()
        created = repo.create_submission(
            questionnaire_id=data.get("questionnaire_id") or data.get("questionnaire"),
            tipo_fase=data["tipo_fase"],
            regulador_id=data.get("regulador_id"),
            placa_vehiculo=data.get("placa_vehiculo"),
        )
        return Response(
            SubmissionModelSerializer(created, context={"request": request}).data,
            status=201,
    )
    @extend_schema(
        parameters=[
            OpenApiParameter("incluir_borradores", OpenApiTypes.STR, required=False),
            OpenApiParameter("solo_finalizados", OpenApiTypes.STR, required=False),
            OpenApiParameter("tipo_fase", OpenApiTypes.STR, required=False),
            OpenApiParameter("proveedor_id", OpenApiTypes.UUID, required=False),
            OpenApiParameter("transportista_id", OpenApiTypes.UUID, required=False),
            OpenApiParameter("receptor_id", OpenApiTypes.UUID, required=False),
        ],
        responses={200: SubmissionModelSerializer(many=True)},
        tags=["Submissions"],
        description="Lista submissions con filtros. Requiere usuario autenticado.",
    )
    def list(self, request):
        try:
            repo = DjangoSubmissionRepository()
            qs = repo.list_for_api(request.query_params)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(qs, request)
            if page is not None:
                serializer = SubmissionModelSerializer(page, many=True, context={"request": request})
                return paginator.get_paginated_response(serializer.data)

            serializer = SubmissionModelSerializer(qs, many=True, context={"request": request})
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        responses={200: SubmissionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Detalle de una submission. Requiere usuario autenticado.",
    )
    def retrieve(self, request, pk=None):
        try:
            repo = DjangoSubmissionRepository()
            obj = repo.get_for_api(pk)
            if not obj:
                return Response({"error": "Submission no encontrada."}, status=404)
            return Response(SubmissionModelSerializer(obj, context={"request": request}).data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        methods=["POST"],
        tags=["Submissions"],
        description="Finaliza una submission. Requiere usuario autenticado.",
    )
    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        try:
            # ✅ Inyección por fábrica (mantiene la capa de aplicación desacoplada)
            svc = get_service_factory().create_submission_service()

            # ✅ Ejecutar caso de uso (retorna un dict con los updates)
            updates = svc.finalize_submission(UUID(str(pk)))

            # ✅ No acceder a result.id (no existe). Devolvemos el id de la ruta.
            #    Mantenemos la respuesta simple y estable para el front.
            return Response({
                "detail": "Finalizada",
                "submission_id": str(pk),
                # si necesitas inspección en UI/admin, puedes exponer los updates:
                # "updates": updates,
            })

        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        methods=["GET"],
        tags=["Submissions"],
        description="Detalle enriquecido de una submission con respuestas. Requiere usuario autenticado.",
    )
    @action(detail=True, methods=["get"], url_path="enriched")
    def enriched_detail(self, request, pk=None):
        try:
            repo = DjangoSubmissionRepository()
            submission_model = repo.detail_queryset().filter(id=pk).first()
            if not submission_model:
                return Response({'error': 'Submission no encontrada.'}, status=404)
            return Response({
                'submission': SubmissionModelSerializer(submission_model, context={"request": request}).data,
                'answers': AnswerReadSerializer(submission_model.answers.all(), many=True, context={'request': request}).data,
            })
        except DomainException as e:
            return translate_domain_exception(e)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# =========================================================
# HISTORIAL — autenticado
# =========================================================
class HistorialReguladoresAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        responses={200: HistorialItemSerializer(many=True)},
        tags=["Historial"],
        description="Historial para reguladores. Requiere usuario autenticado.",
    )
    def get(self, request):
        """
        GET /api/v1/historial/reguladores/?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD&solo_completados=1
        """
        try:
            # 1) Parseo de query params
            fecha_desde = request.query_params.get("fecha_desde") or None
            fecha_hasta = request.query_params.get("fecha_hasta") or None
            sc = (request.query_params.get("solo_completados") or "").strip().lower()
            solo_completados = sc in ("1", "true", "t", "yes", "y")

            # 2) Servicio con dependencias inyectadas (repositorios)
            factory = get_service_factory()
            svc = factory.create_history_service()  # ✅ inyecta submission_repo, answer_repo, question_repo

            # 3) Caso de uso
            items = svc.list_history(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                solo_completados=solo_completados,
            )

            # 4) Paginación + serialización manual
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(items, request)
            if page is not None:
                serializer = HistorialItemSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            return Response(HistorialItemSerializer(items, many=True).data)
        except Exception as e:
            # Devuelve el error legible al front
            return Response({"error": str(e)}, status=500)


# =========================================================
# MEDIA PROTEGIDO — autenticado
# =========================================================
class MediaProtectedAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("file_path", OpenApiTypes.STR, location="path", required=True)],
        responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT},
        tags=["Media"],
        description="Sirve archivos de MEDIA protegido. Requiere usuario autenticado.",
    )
    def get(self, request, file_path: str):
        safe_root = os.path.abspath(settings.MEDIA_ROOT)
        requested_path = os.path.abspath(os.path.join(safe_root, file_path))
        if not requested_path.startswith(safe_root):
            raise Http404("Archivo no encontrado.")
        if not os.path.exists(requested_path):
            raise Http404("Archivo no encontrado.")
        return FileResponse(open(requested_path, "rb"))


# =========================================================
# LISTA DE CUESTIONARIOS — autenticado
# =========================================================
class QuestionnaireListAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionnaireListItemSerializer(many=True)},
        tags=["Cuestionario"],
        description="Lista de cuestionarios (id, título, versión, timezone). Requiere usuario autenticado.",
    )
    def get(self, request):
        qs = DjangoQuestionnaireRepository().list_minimal()
        return Response(QuestionnaireListItemSerializer(qs, many=True).data)


# =========================================================
# DETALLE DE PREGUNTA — autenticado
# =========================================================
class QuestionDetailAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Detalle de una pregunta por id. Requiere usuario autenticado.",
    )
    def get(self, request, id):
        try:
            from app.infrastructure.repositories import DjangoQuestionRepository
            repo = DjangoQuestionRepository()
            q = repo.get_by_id(id)
            if not q:
                return Response({"error": "Pregunta no encontrada."}, status=404)
            return Response(QuestionModelSerializer(q).data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# =========================================================
# CATÁLOGO DE ACTORES — autenticado
# =========================================================
class ActorViewSet(viewsets.ViewSet):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tipo", type=OpenApiTypes.STR, required=False, description="PROVEEDOR | TRANSPORTISTA | RECEPTOR (también acepta proveedor/transportista/receptor en minúsculas)."),
            OpenApiParameter(name="search", type=OpenApiTypes.STR, required=False, description="Texto a buscar (nombre o documento)."),
            OpenApiParameter(name="q", type=OpenApiTypes.STR, required=False, description="Alias de 'search' por compatibilidad."),
            OpenApiParameter(name="limit", type=OpenApiTypes.INT, required=False, description="Límite de resultados (1–100). Default 15."),
            OpenApiParameter(name="activo", type=OpenApiTypes.STR, required=False, description="Filtrar por activo=true/false. Por defecto true."),
        ],
        responses={200: ActorModelSerializer(many=True)},
        tags=["Catálogos"],
        description="Lista actores (proveedores/transportistas/receptores) con filtros. Requiere usuario autenticado.",
    )
    def list(self, request):
        from app.infrastructure.models import Actor
        from django.db.models import Q

        qs = Actor.objects.all()

        # --- activo por defecto: true ---
        activo = request.query_params.get("activo")
        if activo is None or str(activo).lower() in ("1", "true", "yes", "y"):
            qs = qs.filter(activo=True)

        # --- filtro por tipo ---
        tipo = (request.query_params.get("tipo") or "").strip()
        if tipo:
            up = tipo.upper()
            slug_map = {"proveedor": "PROVEEDOR", "transportista": "TRANSPORTISTA", "receptor": "RECEPTOR"}
            if up in {"PROVEEDOR", "TRANSPORTISTA", "RECEPTOR"}:
                qs = qs.filter(tipo=up)
            elif tipo.lower() in slug_map:
                qs = qs.filter(tipo=slug_map[tipo.lower()])

        # --- búsqueda por nombre/documento ---
        term = (request.query_params.get("search") or request.query_params.get("q") or "").strip()
        if term:
            qs = qs.filter(Q(nombre__icontains=term) | Q(documento__icontains=term))

        # --- orden y límite seguro ---
        qs = qs.order_by("nombre")
        try:
            limit = int(request.query_params.get("limit", "15") or 15)
            limit = max(1, min(limit, 100))
        except Exception:
            limit = 15
        qs = qs[:limit]

        return Response(ActorModelSerializer(qs, many=True).data)

    @extend_schema(
        responses={200: ActorModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Catálogos"],
        description="Detalle de actor por ID. Requiere usuario autenticado.",
    )
    def retrieve(self, request, pk=None):
        from app.infrastructure.models import Actor
        try:
            actor = Actor.objects.get(pk=pk)
            return Response(ActorModelSerializer(actor).data)
        except Actor.DoesNotExist:
            return Response({"detail": "No encontrado."}, status=status.HTTP_404_NOT_FOUND)

class QuestionnaireGridDefinitionAPIView(APIView):
    """
    Devuelve el layout visual (anchos, headers) del cuestionario,
    para que el frontend pinte el grid idéntico al Excel.
    """
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("qid", OpenApiTypes.UUID, required=True)],
        responses={200: GridDefinitionSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionarios"],
        description="Layout JSON del cuestionario (anchos/headers exactamente como el Excel de origen)."
    )
    def get(self, request, qid: str):
        try:
            q = QuestionnaireModel.objects.filter(id=UUID(str(qid))).only("id", "title", "version", "timezone").first()
            if not q:
                return Response({"error": "Cuestionario no encontrado."}, status=404)
            layout = load_questionnaire_layout(q.id)
            if not layout:
                return Response({"error": "No hay layout cargado para este cuestionario."}, status=404)
            # Seguridad mínima: verificar que el layout corresponde
            layout["questionnaire_id"] = str(q.id)
            layout["title"] = q.title
            layout["version"] = q.version
            layout["timezone"] = q.timezone
            return Response(GridDefinitionSerializer(layout).data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)