from __future__ import annotations

import os
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import login as dj_login, logout as dj_logout

from rest_framework import viewsets, mixins, status, serializers
from rest_framework.authentication import SessionAuthentication
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
from app.application.commands import SaveAndAdvanceCommand
from app.application.questionnaire import QuestionnaireService
from app.application.verification import VerificationService, InvalidImage, ExtractionFailed
from app.domain.exceptions import DomainException

# ===== Manejo de excepciones =====
from app.interfaces.exception_handlers import translate_domain_exception

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
)
from app.infrastructure.factories import get_service_factory
from app.infrastructure.repositories import DjangoSubmissionRepository, DjangoQuestionnaireRepository


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
    parser_classes = [MultiPartParser, FormParser]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._factory = get_service_factory()

    def _get_questionnaire_service(self) -> QuestionnaireService:
        return self._factory.create_questionnaire_service()

    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar (primera pregunta)",
        tags=["Cuestionario"],
        description=(
            "Guarda una respuesta y devuelve la siguiente pregunta. "
            "Para la pregunta especial PROVEEDOR (sin grids): "
            "envía la lista completa en `proveedores` o como JSON en `answer_text`."
        ),
        examples=[
            OpenApiExample(
                "PROVEEDOR con lista estructurada",
                value={
                    "submission_id": "f4d7c2f6-5f2d-4a1d-8f6d-1d2e3c4b5a6f",
                    "question_id": "3a2b1c4d-5e6f-7081-9201-a2b3c4d5e6f7",
                    "proveedores": [
                        {"nombre":"ACME","estibas":3,"unidades":120,"unidad":"KG","recipientes":2,"orden_compra":"OC-123"},
                        {"nombre":"TransLuna","estibas":1,"unidades":40,"unidad":"UN","recipientes":None,"orden_compra":""}
                    ]
                }
            ),
            OpenApiExample(
                "PROVEEDOR con answer_text JSON",
                value={
                    "submission_id": "f4d7c2f6-5f2d-4a1d-8f6d-1d2e3c4b5a6f",
                    "question_id": "3a2b1c4d-5e6f-7081-9201-a2b3c4d5e6f7",
                    "answer_text": "[{\"nombre\":\"ACME\",\"estibas\":3,\"unidades\":120,\"unidad\":\"KG\"}]"
                }
            ),
        ],
    )
    def post(self, request):
        serializer = SaveAndAdvanceInputSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Datos normalizados desde el serializer
        cmd_kwargs = serializer.to_domain_input()

        # Compat: alias del front para texto crudo "value" (el serializer no lo maneja a propósito)
        if not cmd_kwargs.get("answer_text") and "value" in request.data:
            raw = request.data.get("value")
            cmd_kwargs["answer_text"] = None if raw is None else str(raw)

        # user_id del request tiene prioridad
        cmd_kwargs["user_id"] = getattr(request.user, "id", None)

        cmd = SaveAndAdvanceCommand(**cmd_kwargs)

        try:
            repo = DjangoSubmissionRepository()
            can_view_all = bool(getattr(request.user, "is_staff", False))
            if not repo.get_for_api(cmd.submission_id, user=request.user, include_all=can_view_all):
                return Response({"error": "Submission no encontrada."}, status=404)

            svc: QuestionnaireService = self._get_questionnaire_service()
            result = svc.save_and_advance(cmd)
            return Response(SaveAndAdvanceResponseSerializer(result).data)
        except DomainException as e:
            return translate_domain_exception(e)
        except DjangoValidationError as e:
            return Response({"error": e.message}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

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
            from uuid import UUID as _UUID
            svc = self._get_questionnaire_service()

            # 1) Dominio: obtener ENTIDAD de la primera pregunta
            d_question = svc.get_first_question(_UUID(qid))

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

    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar",
        tags=["Cuestionario"],
        description=(
            "Guarda una respuesta y devuelve la siguiente pregunta. "
            "Para la pregunta PROVEEDOR, envía `proveedores` o `answer_text` con JSON de lista."
        ),
        examples=[
            OpenApiExample(
                "PROVEEDOR con lista estructurada",
                value={
                    "submission_id": "f4d7c2f6-5f2d-4a1d-8f6d-1d2e3c4b5a6f",
                    "question_id": "3a2b1c4d-5e6f-7081-9201-a2b3c4d5e6f7",
                    "proveedores": [
                        {"nombre":"ACME","estibas":3,"unidades":120,"unidad":"KG","recipientes":2,"orden_compra":"OC-123"}
                    ]
                }
            )
        ],
    )
    def post(self, request):
        # 1) Validación base
        serializer = SaveAndAdvanceInputSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # 2) Datos normalizados desde el serializer
        cmd_kwargs = serializer.to_domain_input()

        # 3) Compat alias "value" para texto crudo
        if not cmd_kwargs.get("answer_text") and "value" in request.data:
            raw = request.data.get("value")
            cmd_kwargs["answer_text"] = None if raw is None else str(raw)

        # 4) user_id del request tiene prioridad
        cmd_kwargs["user_id"] = getattr(request.user, "id", None)

        # 5) Construir comando de aplicación
        cmd = SaveAndAdvanceCommand(**cmd_kwargs)

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
            created_by=request.user if getattr(request.user, "is_authenticated", False) else None,
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
            can_view_all = bool(getattr(request.user, "is_staff", False))
            qs = repo.list_for_api(
                request.query_params,
                user=request.user,
                include_all=can_view_all,
            )

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
            can_view_all = bool(getattr(request.user, "is_staff", False))
            obj = repo.get_for_api(pk, user=request.user, include_all=can_view_all)
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
            repo = DjangoSubmissionRepository()
            can_view_all = bool(getattr(request.user, "is_staff", False))
            if not repo.get_for_api(pk, user=request.user, include_all=can_view_all):
                return Response({"error": "Submission no encontrada."}, status=404)

            svc = get_service_factory().create_submission_service()
            updates = svc.finalize_submission(UUID(str(pk)))
            return Response({
                "detail": "Finalizada",
                "submission_id": str(pk),
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
            can_view_all = bool(getattr(request.user, "is_staff", False))
            submission_model = (
                repo.detail_queryset(user=request.user, include_all=can_view_all)
                .filter(id=pk)
                .first()
            )
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

            # 2) Servicio con dependencias inyectadas
            factory = get_service_factory()
            svc = factory.create_history_service()

            # 3) Caso de uso
            items = svc.list_history(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                solo_completados=solo_completados,
                user=request.user,
                include_all=bool(getattr(request.user, "is_staff", False)),
            )

            # 4) Paginación + serialización manual
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(items, request)
            if page is not None:
                serializer = HistorialItemSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            return Response(HistorialItemSerializer(items, many=True).data)
        except Exception as e:
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
