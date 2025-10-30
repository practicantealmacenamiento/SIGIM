# Entorno de Desarrollo

## Requisitos minimos
- Sistema operativo: Windows 10+, macOS 12+ o cualquier distribucion Linux con soporte Docker.
- Python 3.12.x y `pip` actualizado (alineado con el `Dockerfile`).
- Git 2.40+ para gestionar el repositorio y ramas de trabajo.
- Redis 7 (opcional) cuando se prueben tareas Celery o throttling basado en colas.
- Credenciales de Google Cloud Vision (opcional) para emular OCR real; en su ausencia se usa el mock integrado.

## Configuracion local
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Archivo `.env`
Crear `BACK_FormContainers/.env` tomando como referencia los ejemplos del repositorio. Variables destacadas:
- `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
- `DATABASE_URL` o variables `DB_*` para usar SQL Server; si se omite se activa SQLite (`dbtest.sqlite3`).
- `GOOGLE_APPLICATION_CREDENTIALS`: ruta al JSON del servicio de Vision.
- `USE_MOCK_OCR=1`: fuerza el uso del mock `DevelopmentTextExtractor`.
- `VISION_MAX_PER_MONTH`: limite mensual de verificaciones OCR (por defecto 1999).
- `API_SECRET_TOKEN`: token para integraciones de escritura (si se usa `TokenRequiredForWrite`).
- `CELERY_BROKER`, `CELERY_BACKEND`: direccion de Redis cuando se ejecuta Celery.

### Servicios Docker
`docker-compose.yml` incluye servicios de referencia:
- `django`: aplica migraciones y expone `http://localhost:8000`.
- `celery`: worker opcional enlazado a Redis.
- `redis`: instancia local para mensajeria y throttling.

Para levantar el entorno:
```bash
docker compose up --build
```

## Dependencias principales
- Django 5.2, Django REST Framework 3.16, drf-spectacular 0.28, django-cors-headers, django-environ.
- Celery 5.5 (opcional), Redis 7, pytest 8.3, import-linter.
- Adaptadores propios para OCR (`TextExtractorAdapter`) y almacenamiento (`DjangoDefaultStorageAdapter`).

## Comandos utiles
- `python manage.py migrate` — aplica migraciones.
- `python manage.py createsuperuser` — crea usuario administrativo.
- `python manage.py spectacular --color --file schema.yml` — regenera el esquema OpenAPI.
- `python manage.py report_vision_usage` — consulta el contador mensual de OCR.
- `pytest` — ejecuta pruebas unitarias e integracion.
- `import-linter --config pyproject.toml` — valida los contratos de arquitectura.

## Buenas practicas en desarrollo
- Ejecutar `pytest` y `python manage.py check` antes de subir cambios.
- Regenerar el esquema OpenAPI al modificar vistas o serializadores.
- Usar el mock OCR por defecto y habilitar Vision real solo cuando sea necesario, evitando consumir la cuota de `VISION_MAX_PER_MONTH`.
- Mantener el repositorio limpio (sin archivos generados en `media/` o `staticfiles`) antes de crear un commit.
