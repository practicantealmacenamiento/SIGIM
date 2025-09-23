from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from app.interfaces.views import (
    VerificacionUniversalAPIView,
    PrimeraPreguntaAPIView,
    GuardarYAvanzarAPIView,
    SubmissionViewSet,
    MediaProtectedAPIView,
    QuestionnaireListAPIView,
    HistorialReguladoresAPIView,
    ActorViewSet,
    AdminActorViewSet,
    QuestionDetailAPIView,
)

# Admin imports (agregamos login + whoami)
from app.interfaces.admin_views import (
    AdminQuestionnaireViewSet,
    AdminUserViewSet,
    AdminLoginAPIView,
    AdminWhoAmI,
    AdminLogoutAPIView
)

router = DefaultRouter()
# Router con barra opcional para evitar 301 redirects
router.trailing_slash = r'/?'

# ===== RUTAS UNIFICADAS =====
# Management/Admin - usando una sola ruta consistente
router.register(r'management/questionnaires', AdminQuestionnaireViewSet, basename='questionnaires')
router.register(r'management/users', AdminUserViewSet, basename='users')
router.register(r'management/actors', AdminActorViewSet, basename='admin-actors')

# Public routes
router.register(r'catalogos/actores', ActorViewSet, basename='actors')
router.register(r'submissions', SubmissionViewSet, basename='submissions')

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

    # Custom submission actions (handled by ViewSet)
    path('api/submissions/<uuid:pk>/finalize/', SubmissionViewSet.as_view({'post': 'finalize'}), name='submission-finalize'),
    path('api/submissions/<uuid:pk>/enriched/', SubmissionViewSet.as_view({'get': 'enriched_detail'}), name='submission-enriched'),

    # Media protegido (GET; se puede dejar con barra fija)
    path('api/secure-media/<path:file_path>/', MediaProtectedAPIView.as_view(), name='secure-media'),

    # Historial reguladores (GET) - con barra opcional
    re_path(r'^api/historial/reguladores/?$', HistorialReguladoresAPIView.as_view(), name='historial-reguladores'),

    # Auth token DRF (por si lo usas desde scripts; hace POST a veces)
    re_path(r'^api/api-token-auth/?$', obtain_auth_token, name='api_token_auth'),

    # ===== AUTENTICACIÓN UNIFICADA =====
    # Una sola ruta de login/logout/whoami
    re_path(r'^api/login/?$', AdminLoginAPIView.as_view(), name='login'),
    re_path(r'^api/whoami/?$', AdminWhoAmI.as_view(), name='whoami'),
    re_path(r'^api/logout/?$', AdminLogoutAPIView.as_view(), name='logout'),

    # Selector de cuestionarios y detalle de pregunta (GET) - con barra opcional
    re_path(r'^api/cuestionarios/?$', QuestionnaireListAPIView.as_view(), name='cuestionarios-list'),
    re_path(r'^api/questions/(?P<id>[0-9a-f-]+)/?$', QuestionDetailAPIView.as_view(), name='question-detail'),
]
