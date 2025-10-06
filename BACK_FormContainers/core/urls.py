from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Docs privadas (solo staff)
from app.interfaces.views import PrivateSchemaAPIView, PrivateSwaggerUIView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API de la app
    path("", include("app.interfaces.urls")),

    # OpenAPI/Swagger privados (solo staff)
    path("api/schema/", PrivateSchemaAPIView.as_view(), name="schema"),
    path("api/docs/", PrivateSwaggerUIView.as_view(url_name="schema"), name="swagger-ui"),
]

# Media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
