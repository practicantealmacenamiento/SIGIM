from __future__ import annotations

import os
from uuid import UUID

from django.conf import settings
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import logout as django_logout

from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication, get_authorization_header
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from drf_spectacular.utils import (
    extend_schema,
    OpenApiTypes,
    OpenApiParameter,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView  # ⬅️ NUEVO

# ===== Aplicación / Casos de uso =====
from app.application.commands import SaveAndAdvanceCommand
from app.application.services import SubmissionService, HistoryService
from app.application.questionnaire import QuestionnaireService
from app.application.exceptions import ValidationError, DomainError
from app.application.verification import VerificationService, InvalidImage, ExtractionFailed

# ===== Infraestructura / Adaptadores =====
from app.infrastructure.models import Submission, Question, Actor
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
from app.infrastructure.repositories import (
    DjangoAnswerRepository,
    DjangoSubmissionRepository,
    DjangoQuestionRepository,
    DjangoChoiceRepository,
    DjangoActorRepository,
    DjangoQuestionnaireRepository,
)
from app.infrastructure.storage import DjangoDefaultStorageAdapter
from app.infrastructure.vision import GoogleVisionAdapter


# ===============================
# VISTAS PRIVADAS DE ESQUEMA/DOCS (requiere staff) — NUEVO
# ===============================
class PrivateSchemaAPIView(SpectacularAPIView):
    """
    /api/schema/ — sólo visible a staff.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


class PrivateSwaggerUIView(SpectacularSwaggerView):
    """
    /api/docs/ — sólo visible a staff.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


# ===============================
# Verificación (OCR) — autenticado
# ===============================
class VerificacionUniversalAPIView(APIView):
    """
    POST /api/verificar/
    Sube una imagen y aplica OCR + reglas según semantic_tag de la pregunta.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=VerificationInputSerializer,
        responses={200: VerificationResponseSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Verificación"],
        description="OCR (Google Vision) + reglas por semantic_tag (placa, precinto, contenedor). Requiere usuario autenticado.",
    )
    def post(self, request):
        ser = VerificationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        try:
            question = Question.objects.get(id=data["question_id"])
        except Question.DoesNotExist:
            return Response({"error": "Pregunta no encontrada."}, status=404)

        adapter = GoogleVisionAdapter(mode=data.get("mode", "text"), language_hints=["es", "en"])
        service = VerificationService(adapter)

        imagen = request.FILES["imagen"]
        try:
            if hasattr(imagen, "seek"):
                imagen.seek(0)
        except Exception:
            pass
        imagen_bytes = imagen.read()

        tag = getattr(question, "semantic_tag", "") or "none"
        try:
            result = service.verificar_universal(tag, imagen_bytes)
            result["semantic_tag"] = tag
        except InvalidImage as e:
            return Response({"error": str(e)}, status=400)
        except ExtractionFailed as e:
            return Response({"error": str(e)}, status=502)

        return Response(VerificationResponseSerializer(result).data)


# ==========================================
# Cuestionario (primera pregunta) — autenticado
# ==========================================
class PrimeraPreguntaAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("questionnaire_id", OpenApiTypes.UUID, required=False)],
        responses={200: QuestionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Primera pregunta de un cuestionario (por orden). Requiere usuario autenticado.",
    )
    def get(self, request):
        qid = request.query_params.get("questionnaire_id")
        qs = Question.objects.filter(questionnaire=qid) if qid else Question.objects
        pregunta = qs.order_by("order").first()
        if not pregunta:
            return Response({"error": "No se encontró ninguna pregunta."}, status=404)
        return Response(QuestionModelSerializer(pregunta).data)


# ==========================================
# Guardar y Avanzar — autenticado (no admin)
# ==========================================
class GuardarYAvanzarAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar",
        tags=["Cuestionario"],
        description="Guarda una respuesta y devuelve la siguiente pregunta. Requiere usuario autenticado.",
    )
    def post(self, request):
        in_ser = SaveAndAdvanceInputSerializer(data=request.data)
        in_ser.is_valid(raise_exception=True)
        data = in_ser.validated_data

        # Validar pregunta
        try:
            q = Question.objects.get(id=data["question_id"])
        except Question.DoesNotExist:
            return Response({"error": "Pregunta no encontrada."}, status=404)

        # Manejo de archivos (0..2)
        uploads = []
        legacy = request.FILES.getlist("answer_file")
        if legacy:
            uploads.extend(legacy)
        if "answer_file" in data and data["answer_file"]:
            uploads.append(data["answer_file"])
        if "answer_file_extra" in data and data["answer_file_extra"]:
            uploads.append(data["answer_file_extra"])
        if len(uploads) > 2:
            uploads = uploads[:2]

        # Caso de uso
        service = QuestionnaireService(
            answer_repo=DjangoAnswerRepository(),
            submission_repo=DjangoSubmissionRepository(),
            question_repo=DjangoQuestionRepository(),
            choice_repo=DjangoChoiceRepository(),
            storage=DjangoDefaultStorageAdapter(),
        )

        cmd = SaveAndAdvanceCommand(
            submission_id=data["submission_id"],
            question_id=q.id,
            user_id=data.get("user_id"),
            answer_text=data.get("answer_text"),
            answer_choice_id=data.get("answer_choice_id"),
            uploads=uploads,
        )

        try:
            result = service.save_and_advance(cmd)
        except ValidationError as e:
            return Response({"error": str(e)}, status=400)
        except DomainError as e:
            return Response({"error": str(e)}, status=404)
        except DjangoValidationError as e:
            return Response({"error": getattr(e, "message_dict", str(e))}, status=400)

        return Response(SaveAndAdvanceResponseSerializer(result, context={"request": request}).data)


# ======================
# Submissions — autenticado
# ======================
class SubmissionListCreateAPIView(ListCreateAPIView):
    """
    GET lista submissions (paginado) / POST crea una submission (fase).
    Requiere usuario autenticado (no admin).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Submission.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SubmissionCreateSerializer
        return SubmissionModelSerializer

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
    def list(self, request, *args, **kwargs):
        repo = DjangoSubmissionRepository()
        qs = repo.list_for_api(request.query_params)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = SubmissionModelSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubmissionModelSerializer(
            qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        request=SubmissionCreateSerializer,
        responses={201: SubmissionModelSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Crea una nueva submission (fase). Requiere usuario autenticado.",
    )
    def create(self, request, *args, **kwargs):
        s = SubmissionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        repo = DjangoSubmissionRepository()
        created = repo.create_submission(**s.validated_data)
        return Response(SubmissionModelSerializer(created).data, status=201)


class SubmissionFinalizarAPIView(APIView):
    """
    POST /api/submissions/<id>/finalizar/ — marca finalizada y deriva placa si aplica.
    Requiere usuario autenticado (no admin).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Marca una submission como finalizada. Requiere usuario autenticado.",
    )
    def post(self, request, id):
        service = SubmissionService(
            submission_repo=DjangoSubmissionRepository(),
            answer_repo=DjangoAnswerRepository(),
            question_repo=DjangoQuestionRepository(),
        )
        try:
            updates = service.finalize_submission(id)
        except DomainError as e:
            return Response({"error": str(e)}, status=404)

        payload = {"mensaje": "Submission finalizada", **updates}
        return Response(payload)


class SubmissionDetailAPIView(RetrieveAPIView):
    """
    GET /api/submissions/<id>/ — detalle simple (autenticado).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SubmissionModelSerializer
    lookup_field = "id"

    def get_queryset(self):
        return DjangoSubmissionRepository().detail_queryset()


class SubmissionDetailEnrichedAPIView(APIView):
    """
    GET /api/submissions/<id>/enriched/ — detalle con respuestas (autenticado).
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: SubmissionModelSerializer},
        tags=["Submissions"],
        description="Detalle completo de una submission con respuestas. Requiere usuario autenticado.",
    )
    def get(self, request, id):
        repo = DjangoSubmissionRepository()
        submission = repo.get_detail(id)
        if not submission:
            return Response({'error': 'Submission no encontrada.'}, status=404)

        answers_qs = getattr(submission, 'answers', None).all() if submission else []
        return Response({
            'submission': SubmissionModelSerializer(submission).data,
            'answers': AnswerReadSerializer(answers_qs, many=True, context={'request': request}).data,
        })


# ======================
# Historial — autenticado
# ======================
class HistorialReguladoresAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("fecha_desde", OpenApiTypes.DATE, required=False),
            OpenApiParameter("fecha_hasta", OpenApiTypes.DATE, required=False),
            OpenApiParameter("solo_completados", OpenApiTypes.STR, required=False),
        ],
        responses={200: HistorialItemSerializer(many=True)},
        tags=["Historial"],
        description="Últimas fases por regulador_id. Requiere usuario autenticado.",
    )
    def get(self, request):
        p = request.query_params
        service = HistoryService(
            submission_repo=DjangoSubmissionRepository(),
            answer_repo=DjangoAnswerRepository(),
            question_repo=DjangoQuestionRepository(),
        )
        items = service.list_history(
            fecha_desde=p.get("fecha_desde"),
            fecha_hasta=p.get("fecha_hasta"),
            solo_completados=p.get("solo_completados") in ("1", "true", "True"),
        )
        return Response(HistorialItemSerializer(items, many=True).data)


# ============================================
# Media protegida — autenticado (no público)
# ============================================
class MediaProtectedAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("file_path", OpenApiTypes.STR, required=True)],
        description="Sirve archivos de MEDIA_ROOT controladamente. Requiere usuario autenticado.",
        responses={200: OpenApiTypes.BINARY, 404: OpenApiTypes.OBJECT},
        tags=["Media"],
    )
    def get(self, request, file_path):
        safe_root = os.path.abspath(settings.MEDIA_ROOT)
        abs_path = os.path.abspath(os.path.join(safe_root, file_path))
        if not abs_path.startswith(safe_root + os.sep):
            raise Http404("Ruta inválida")
        if not os.path.isfile(abs_path):
            raise Http404("Archivo no encontrado")
        return FileResponse(open(abs_path, "rb"))


# =====================================
# Catálogos — autenticado (no admin)
# =====================================
class ActorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/catalogos/actores/ — visible a usuarios autenticados.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ActorModelSerializer
    pagination_class = None
    queryset = Actor.objects.none()

    def list(self, request, *args, **kwargs):
        qs = DjangoActorRepository().public_list(request.query_params)
        return Response(self.get_serializer(qs, many=True).data)


# =====================================
# Lista de cuestionarios — autenticado
# =====================================
class QuestionnaireListAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionnaireListItemSerializer(many=True)},
        tags=["Cuestionario"],
        description="Lista de cuestionarios (id, título, versión, timezone). Requiere usuario autenticado.",
    )
    def get(self, request):
        qs = DjangoQuestionnaireRepository().list_minimal()
        return Response(QuestionnaireListItemSerializer(qs, many=True).data)


# =====================================
# Detalle de pregunta — autenticado
# =====================================
class QuestionDetailAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: QuestionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Detalle de una pregunta por id. Requiere usuario autenticado.",
    )
    def get(self, request, id):
        try:
            q = Question.objects.get(id=id)
        except Question.DoesNotExist:
            return Response({"error": "Pregunta no encontrada."}, status=404)
        return Response(QuestionModelSerializer(q).data)


# =====================================
# Admin (solo staff) — sin cambios
# =====================================
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminActorViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    /api/admin/actors/ — restringido a staff (panel administrativo).
    """
    serializer_class = ActorModelSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination
    queryset = Actor.objects.none()

    def get_queryset(self):
        return DjangoActorRepository().admin_queryset(self.request.query_params)

class LogoutAPIView(APIView):
    """
    POST /api/logout/  y también /api/admin/logout/ (mapeado en urls)
    - Idempotente y accesible sin auth (AllowAny) para que nunca falle el cierre.
    - Revoca token DRF (el del header; si hay usuario, todos los del usuario).
    - Invalida la sesión en servidor (flush()), de modo que un 'sessionid' viejo no sirve jamás.
    - Intenta borrar cookies en variantes comunes de domain/SameSite.
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        # 1) Revocar token del header (Bearer/Token ...) y, si hay user, todos los del user
        try:
            raw = get_authorization_header(request).decode("utf-8") if get_authorization_header(request) else ""
            key = raw.split()[1] if raw and raw.lower().startswith(("bearer ", "token ")) else None
            if key:
                Token.objects.filter(key=key).delete()
            if getattr(request, "user", None) and request.user.is_authenticated:
                Token.objects.filter(user=request.user).delete()
        except Exception:
            pass

        # 2) INVALIDAR sesión en servidor (aunque el cookie "sessionid" quede visible, ya no sirve)
        try:
            # flush borra la sesión del storage y rota la cookie server-side
            request.session.flush()
        except Exception:
            pass

        # 3) Logout Django (por si hubiera backends de auth atados a request.user)
        try:
            django_logout(request)
        except Exception:
            pass

        # 4) Respuesta + borrado AGRESIVO de cookies en variantes
        resp = Response({"ok": True}, status=status.HTTP_200_OK)
        resp["Cache-Control"] = "no-store"
        resp["Vary"] = "Cookie, Authorization"

        # Nombres relevantes (usa nombres desde settings por si los cambiaste)
        session_cookie = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        csrf_cookie = getattr(settings, "CSRF_COOKIE_NAME", "csrftoken")
        names = {
            session_cookie,
            csrf_cookie,
            "auth_token",
            "auth_username",
            "is_staff",
        }

        # Variantes de dominio: exacto, raíz (e.g. .empresa.com) y sin domain
        host = (request.get_host() or "").split(":")[0] or None
        parts = (host or "").split(".") if host else []
        domains = [None]
        if host: domains.append(host)
        if len(parts) >= 2: domains.append("." + ".".join(parts[-2:]))
        if len(parts) >= 3: domains.append("." + ".".join(parts[-3:]))

        # Safari/Chrome pueden exigir SameSite coincidente al borrar
        samesites = ["Lax", "Strict", "None"]

        for name in names:
            for d in domains:
                for ss in samesites:
                    # delete_cookie ya marca Max-Age=0 y Expires pasado
                    resp.delete_cookie(key=name, path="/", domain=d, samesite=ss)

        # Señal de UI
        try:
            resp.set_cookie(
                key="is_staff", value="0", path="/",
                samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
                secure=getattr(settings, "SESSION_COOKIE_SECURE", False),
                domain=getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            )
        except Exception:
            pass

        return resp