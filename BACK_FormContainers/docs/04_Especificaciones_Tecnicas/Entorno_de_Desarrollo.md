# Entorno de Desarrollo

## Requisitos minimos
- Sistema operativo: Windows 10+, macOS 12+ o cualquier distribucion Linux con soporte Docker.
- Python 3.12.8 (segun `Dockerfile`) y `pip` actualizado.
- Git 2.40+ para gestionar el repositorio.
- Redis 7 (opcional) cuando se ejecuten tareas Celery en local.
- Credenciales de Google Cloud Vision (opcional) para ejercicios de OCR en entorno de pruebas.

## Entorno virtual recomendado
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Archivos de configuracion
- Crear un archivo `.env` en `BACK_FormContainers/` tomando como referencia `.env.sqlserver` o el ejemplo del repo.
- Variables clave:
  - `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`.
  - `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` para habilitar el frontend local.
  - `GOOGLE_APPLICATION_CREDENTIALS` (ruta al JSON de Vision).
  - `API_SECRET_TOKEN` si se integran servicios externos.
- Para Celery, configurar `CELERY_BROKER` y `CELERY_BACKEND` (por defecto Redis en `core/settings.py`).

## Dependencias principales
- Django 5.2 y Django REST Framework 3.16.
- drf-spectacular 0.28 para documentacion OpenAPI.
- django-cors-headers y django-environ para configuraciones.
- Celery 5.5 y Redis 7 para procesamiento asincrono.

## Servicios Docker
El archivo `docker-compose.yml` define:
- `redis`: contenedor base para colas.
- `django`: ejecuta `python manage.py runserver` con el codigo montado en caliente.
- `celery`: dispara un worker enlazado al mismo codigo.

Para levantar el stack:
```bash
docker compose up --build
```

## Herramientas adicionales
- import-linter: valida la disciplina de importaciones de la arquitectura limpia (`pyproject.toml`).
- pytest: ejecutar pruebas unitarias con `pytest`.
- drf-spectacular: generar esquema via `python manage.py spectacular --color --file schema.yml`.
