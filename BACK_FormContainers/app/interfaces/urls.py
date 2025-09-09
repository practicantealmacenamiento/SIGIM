from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.interfaces.views import (
    VerificacionUniversalAPIView,
    PrimeraPreguntaAPIView,
    GuardarYAvanzarAPIView,
    SubmissionListCreateAPIView,
    SubmissionDetailAPIView,
    SubmissionFinalizarAPIView,
    MediaProtectedAPIView,
    QuestionnaireListAPIView,
    HistorialReguladoresAPIView,
    ActorViewSet,
    AdminActorViewSet,
    QuestionDetailAPIView,
    LogoutAPIView,
)

# Admin imports (agregamos login + whoami)
from app.interfaces.admin_views import (
    AdminQuestionnaireViewSet,
    AdminUserViewSet,
    AdminLoginAPIView,
    AdminWhoAmI,
)

router = DefaultRouter()
# Este router ya acepta barra opcional
router.trailing_slash = r'/?'
router.register(r'admin/questionnaires', AdminQuestionnaireViewSet, basename='admin-questionnaires')
router.register(r'admin/users', AdminUserViewSet, basename='admin-users')
router.register(r'catalogos/actores', ActorViewSet, basename='actors')
router.register(r'admin/actors', AdminActorViewSet, basename='admin-actors')

urlpatterns = [
    path('api/', include(router.urls)),

    # OpenAPI & Docs (GET solamente; pueden quedar con barra fija sin problema)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ===== RUTAS MANUALES con barra opcional (evita 500 en POST sin "/") =====

    # Verificación (OCR) — POST
    re_path(r'^api/verificar/?$', VerificacionUniversalAPIView.as_view(), name='verificacion-universal'),

    # Cuestionario
    path('api/cuestionario/primera/', PrimeraPreguntaAPIView.as_view(), name='primera-pregunta'),  # GET
    re_path(r'^api/cuestionario/guardar_avanzar/?$', GuardarYAvanzarAPIView.as_view(), name='guardar-y-avanzar'),  # POST

    # Submissions
    re_path(r'^api/submissions/?$', SubmissionListCreateAPIView.as_view(), name='submissions-list'),  # GET/POST
    path('api/submissions/<uuid:id>/', SubmissionDetailAPIView.as_view(), name='submissions-detail'),  # GET
    re_path(r'^api/submissions/(?P<id>[0-9a-fA-F-]{32,36})/finalizar/?$', SubmissionFinalizarAPIView.as_view(), name='submission-finalizar'),  # POST

    # Media protegido (GET; se puede dejar con barra fija)
    path('api/secure-media/<path:file_path>/', MediaProtectedAPIView.as_view(), name='secure-media'),

    # Historial reguladores (GET)
    path('api/historial/reguladores/', HistorialReguladoresAPIView.as_view(), name='historial-reguladores'),

    # Auth token DRF (por si lo usas desde scripts; hace POST a veces)
    re_path(r'^api/api-token-auth/?$', obtain_auth_token, name='api_token_auth'),

    # Login admin (POST) y diagnóstico (GET) — AHORA con barra opcional
    re_path(r'^api/admin/login/?$', AdminLoginAPIView.as_view(), name='admin-login'),
    re_path(r'^api/admin/whoami/?$', AdminWhoAmI.as_view(), name='admin-whoami'),
    re_path(r"^api/admin/logout/?$", LogoutAPIView.as_view(), name="admin-logout"),
    re_path(r"^api/logout/?$", LogoutAPIView.as_view(), name="logout"),

    # Selector de cuestionarios y detalle de pregunta (GET)
    path('api/cuestionarios/', QuestionnaireListAPIView.as_view(), name='cuestionarios-list'),
    path('api/questions/<uuid:id>/', QuestionDetailAPIView.as_view(), name='question-detail'),
]
