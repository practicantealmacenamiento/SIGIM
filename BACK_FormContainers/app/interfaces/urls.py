from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

# Vistas públicas/autenticadas (negocio + auth unificada)
from app.interfaces.views import (
    # Auth unificada
    UnifiedLoginAPIView,
    WhoAmIAPIView,
    UnifiedLogoutAPIView,

    # OCR / Cuestionario / Submissions / Catálogos / Media / Historial
    VerificacionUniversalAPIView,
    PrimeraPreguntaAPIView,
    GuardarYAvanzarAPIView,
    SubmissionViewSet,
    ActorViewSet,
    MediaProtectedAPIView,
    QuestionnaireListAPIView,
    HistorialReguladoresAPIView,
    QuestionDetailAPIView,
)

# Vistas de administración (CRUDs internos)
from app.interfaces.admin_views import (
    AdminQuestionnaireViewSet,
    AdminUserViewSet,
    AdminActorViewSet,
)

API_PREFIX = "api/v1/"

router = DefaultRouter()
router.trailing_slash = r'/?'  # evita 301/308 por barra final

# ======== RUTAS ADMIN (solo staff, permisos en los viewsets) ========
router.register(r'management/questionnaires', AdminQuestionnaireViewSet, basename='questionnaires')
router.register(r'management/users', AdminUserViewSet, basename='users')
router.register(r'management/actors', AdminActorViewSet, basename='admin-actors')

# ======== RUTAS PÚBLICAS AUTENTICADAS ========
router.register(r'catalogos/actores', ActorViewSet, basename='actors')
router.register(r'submissions', SubmissionViewSet, basename='submissions')

urlpatterns = [
    # Router bajo prefijo versionado
    path(API_PREFIX, include(router.urls)),

    # ======== AUTH UNIFICADA ========
    re_path(rf'^{API_PREFIX}login/?$', UnifiedLoginAPIView.as_view(), name='login'),
    re_path(rf'^{API_PREFIX}whoami/?$', WhoAmIAPIView.as_view(), name='whoami'),
    re_path(rf'^{API_PREFIX}logout/?$', UnifiedLogoutAPIView.as_view(), name='logout'),

    # ======== VERIFICACIÓN (OCR) ========
    re_path(rf'^{API_PREFIX}verificar/?$', VerificacionUniversalAPIView.as_view(), name='verificacion-universal'),

    # ======== CUESTIONARIO ========
    path(f'{API_PREFIX}cuestionario/primera/', PrimeraPreguntaAPIView.as_view(), name='primera-pregunta'),
    re_path(rf'^{API_PREFIX}cuestionario/guardar_avanzar/?$', GuardarYAvanzarAPIView.as_view(), name='guardar-y-avanzar'),

    # Acciones custom de Submission (fuera del router por claridad)
    path(f'{API_PREFIX}submissions/<uuid:pk>/finalize/', SubmissionViewSet.as_view({'post': 'finalize'}), name='submission-finalize'),
    path(f'{API_PREFIX}submissions/<uuid:pk>/enriched/', SubmissionViewSet.as_view({'get': 'enriched_detail'}), name='submission-enriched'),

    # ======== MEDIA PROTEGIDO ========
    path(f'{API_PREFIX}secure-media/<path:file_path>/', MediaProtectedAPIView.as_view(), name='secure-media'),

    # ======== HISTORIAL ========
    re_path(rf'^{API_PREFIX}historial/reguladores/?$', HistorialReguladoresAPIView.as_view(), name='historial-reguladores'),

    # ======== CUESTIONARIOS (lista) ========
    re_path(rf'^{API_PREFIX}cuestionarios/?$', QuestionnaireListAPIView.as_view(), name='cuestionarios-list'),

    # ======== PREGUNTA DETALLE ========
    re_path(rf'^{API_PREFIX}questions/(?P<id>[0-9a-f-]+)/?$', QuestionDetailAPIView.as_view(), name='question-detail'),
]
