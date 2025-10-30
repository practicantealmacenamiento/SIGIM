from __future__ import annotations
from rest_framework import status, viewsets, mixins, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiParameter, OpenApiExample
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .auth import (
    BearerOrTokenAuthentication,
    auth_login_issue_token,
    auth_logout_revoke_token,
    build_user_payload,
)
from app.infrastructure.factories import get_service_factory
from app.infrastructure.serializers import (
    ActorModelSerializer,
    QuestionModelSerializer,
    SaveAndAdvanceInputSerializer,
    SaveAndAdvanceResponseSerializer,
    SubmissionCreateSerializer,
    SubmissionModelSerializer,
    VerificationInputSerializer,
    VerificationResponseSerializer,
)
from app.interfaces.http.services import (
    ActorAPIService,
    AuthAPIService,
    HistoryAPIService,
    InterfaceServices,
    MediaAPIService,
    QuestionnaireAPIService,
    SubmissionAPIService,
    VerificationAPIService,
    _as_bool,
    _parse_uuid,
)

# =====================================================================
# Helpers base
# =====================================================================

class _InterfaceMixin:
    """Helpers reutilizables para las vistas."""
    @property
    def factory(self):
        return get_service_factory()

    def interface_services(self) -> InterfaceServices:
        if not hasattr(self, "_iface_services"):
            fc = self.factory
            self._iface_services = InterfaceServices(
                questionnaire_service=fc.create_questionnaire_service(),
                submission_service=fc.create_submission_service(),
                history_service=fc.create_history_service(),
                verification_service=fc.create_verification_service(),
            )
        return self._iface_services

    def questionnaire_api(self) -> QuestionnaireAPIService:
        if not hasattr(self, "_questionnaire_api"):
            self._questionnaire_api = QuestionnaireAPIService(self.interface_services())
        return self._questionnaire_api

    def submission_api(self) -> SubmissionAPIService:
        if not hasattr(self, "_submission_api"):
            self._submission_api = SubmissionAPIService(self.interface_services())
        return self._submission_api

    def verification_api(self) -> VerificationAPIService:
        if not hasattr(self, "_verification_api"):
            self._verification_api = VerificationAPIService(self.interface_services().verification_service)
        return self._verification_api

    def history_api(self) -> HistoryAPIService:
        if not hasattr(self, "_history_api"):
            self._history_api = HistoryAPIService(self.interface_services())
        return self._history_api

    def actor_api(self) -> ActorAPIService:
        if not hasattr(self, "_actor_api"):
            self._actor_api = ActorAPIService()
        return self._actor_api

    def media_api(self) -> MediaAPIService:
        if not hasattr(self, "_media_api"):
            self._media_api = MediaAPIService()
        return self._media_api


class _BaseAuth(_InterfaceMixin, APIView):
    """Base con autenticacion por defecto y acceso a la factory."""
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

# =====================================================================
# Esquema privado
# =====================================================================

class PrivateSchemaAPIView(SpectacularAPIView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

class PrivateSwaggerUIView(SpectacularSwaggerView):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]

# =====================================================================
# Auth: login, whoami, logout
# =====================================================================

class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    identifier = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        ident = attrs.get("identifier") or attrs.get("username") or attrs.get("email")
        if not ident:
            raise serializers.ValidationError("Debes enviar 'username', 'email' o 'identifier'.")
        if not attrs.get("password"):
            raise serializers.ValidationError("Debes enviar 'password'.")
        attrs["identifier"] = ident
        return attrs

class LoginOutputSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = serializers.DictField()

class UnifiedLoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @property
    def auth_service(self):
        if not hasattr(self, "_auth_service"):
            self._auth_service = AuthAPIService(
                build_user_payload=build_user_payload,
                auth_login_issue_token=auth_login_issue_token,
                auth_logout_revoke_token=auth_logout_revoke_token,
            )
        return self._auth_service

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
    def post(self, request):
        ser = LoginInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self.auth_service.login(request, ser)

class WhoAmIAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAuthenticated]
    _auth_service = None

    @extend_schema(tags=["auth"], responses={200: serializers.DictField})
    def get(self, request):
        if not self._auth_service:
            self._auth_service = AuthAPIService(
                build_user_payload=build_user_payload,
                auth_login_issue_token=auth_login_issue_token,
                auth_logout_revoke_token=auth_logout_revoke_token,
            )
        return self._auth_service.whoami(request)

class UnifiedLogoutAPIView(APIView):
    authentication_classes = [BearerOrTokenAuthentication]
    permission_classes = [IsAuthenticated]
    _auth_service = None

    @extend_schema(tags=["auth"], responses={200: serializers.DictField})
    def post(self, request):
        if not self._auth_service:
            self._auth_service = AuthAPIService(
                build_user_payload=build_user_payload,
                auth_login_issue_token=auth_login_issue_token,
                auth_logout_revoke_token=auth_logout_revoke_token,
            )
        return self._auth_service.logout(request)

# =====================================================================
# Verificacion OCR
# =====================================================================

class VerificacionUniversalAPIView(_BaseAuth):
    @extend_schema(
        request=VerificationInputSerializer,
        responses={200: VerificationResponseSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Verificacion"],
        description="OCR (Google Vision) + reglas por semantic_tag (placa, precinto, contenedor).",
    )
    def post(self, request):
        return self.verification_api().verify(request)

# =====================================================================
# Cuestionario  guardar & avanzar
# =====================================================================

class PrimeraPreguntaAPIView(_BaseAuth):
    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar (primera pregunta)",
        tags=["Cuestionario"],
    )
    def post(self, request):
        tmp = SaveAndAdvanceInputSerializer(data=request.data)
        tmp.is_valid(raise_exception=True)
        sid = tmp.validated_data["submission_id"]
        if not self.factory.create_submission_service().get_submission_for_api(
            sid,
            user=request.user,
            include_all=_as_bool(getattr(request.user, "is_staff", False)),
        ):
            return Response({"error": "Submission no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return self.questionnaire_api().save_and_advance(request)

    @extend_schema(
        parameters=[OpenApiParameter("questionnaire_id", OpenApiTypes.UUID, required=True)],
        responses={200: QuestionModelSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        tags=["Cuestionario"],
        description="Primera pregunta (por orden) de un cuestionario.",
    )
    def get(self, request):
        return self.questionnaire_api().first_question(request)


class GuardarYAvanzarAPIView(_BaseAuth):
    @extend_schema(
        request=SaveAndAdvanceInputSerializer,
        responses={200: SaveAndAdvanceResponseSerializer, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        summary="Guardar respuesta y avanzar",
        tags=["Cuestionario"],
    )
    def post(self, request):
        return self.questionnaire_api().save_and_advance(request)

# =====================================================================
# Submissions
# =====================================================================

class SubmissionViewSet(_InterfaceMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=SubmissionCreateSerializer,
        responses={201: SubmissionModelSerializer, 400: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Crea una submission vacia o inicial.",
    )
    def create(self, request, *args, **kwargs):
        return self.submission_api().create(request)

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
        description="Lista submissions con filtros.",
    )
    def list(self, request):
        return self.submission_api().list(request)

    @extend_schema(
        responses={200: SubmissionModelSerializer, 404: OpenApiTypes.OBJECT},
        tags=["Submissions"],
        description="Detalle de una submission.",
    )
    def retrieve(self, request, pk=None):
        return self.submission_api().retrieve(request, pk)

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        methods=["POST"],
        tags=["Submissions"],
        description="Finaliza una submission.",
    )
    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        return self.submission_api().finalize(request, pk)

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        methods=["GET"],
        tags=["Submissions"],
        description="Detalle enriquecido de una submission con respuestas.",
    )
    @action(detail=True, methods=["get"], url_path="enriched")
    def enriched_detail(self, request, pk=None):
        return self.submission_api().enriched_detail(request, pk)

# =====================================================================
# Catalogo de actores 
# =====================================================================

class ActorViewSet(_InterfaceMixin, viewsets.ViewSet):
    authentication_classes = [BearerOrTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="tipo", type=OpenApiTypes.STR, required=False, description="PROVEEDOR | TRANSPORTISTA | RECEPTOR"),
            OpenApiParameter(name="search", type=OpenApiTypes.STR, required=False, description="Texto a buscar"),
            OpenApiParameter(name="q", type=OpenApiTypes.STR, required=False, description="Alias de 'search'"),
            OpenApiParameter(name="limit", type=OpenApiTypes.INT, required=False, description="1100 (por defecto 15)"),
            OpenApiParameter(name="activo", type=OpenApiTypes.STR, required=False, description="true/false (default true)"),
        ],
        responses={200: ActorModelSerializer(many=True)},
        tags=["Catalogos"],
        description="Lista actores con filtros.",
    )
    def list(self, request):
        return self.actor_api().list(request)


class QuestionnaireListAPIView(_BaseAuth):
    """
    Devuelve el catalogo de cuestionarios disponible para el usuario.
    Parametro opcional:
        - include_questions=true -> incluye preguntas completas.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        repo = self.factory.get_questionnaire_repository()
        return self.questionnaire_api().list_catalog(request, repo)


class QuestionDetailAPIView(_BaseAuth):
    """Detalle de pregunta individual (texto, tipo, choices...)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id: str):
        question_id, error = _parse_uuid(id, field="question_id")
        if error:
            return error

        repo = self.factory.get_question_repository()
        return self.questionnaire_api().question_detail(request, repo, question_id)


class HistorialReguladoresAPIView(_BaseAuth):
    """ 
    Lista el historial de reguladores con ultimas fases completadas.
    Acepta filtros opcionales:
        - fecha_desde (YYYY-MM-DD)
        - fecha_hasta (YYYY-MM-DD)
        - solo_completados (bool)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return self.history_api().list(request)


class MediaProtectedAPIView(_BaseAuth):
    """Sirve archivos de media solo a usuarios autenticados."""

    def get(self, request, file_path: str):
        return self.media_api().serve(file_path=file_path)
