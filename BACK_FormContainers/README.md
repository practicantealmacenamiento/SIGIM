# API Registro de Camiones — Backend (Django REST, Hexagonal)

Arquitectura **Hexagonal/Clean** con capas `domain/`, `application/`, `infrastructure/`, `interfaces/`.
Servicios desacoplados del ORM, puertos/adaptadores para OCR/Storage y serializers manuales.

## Tecnologías
- Django, Django REST Framework
- drf-spectacular (OpenAPI)
- django-cors-headers, django-environ
- (Opcional) Google Cloud Vision

## Entorno
Crea `.env` (ya incluido de ejemplo):

```env
DEBUG=True
SECRET_KEY=dev-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,[::1]
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
API_SECRET_TOKEN=dev-123456
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales.json

