# Instalacion y Configuracion

## 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd BACK_FormContainers
```

## 2. Preparar variables de entorno
1. Crear `./.env` a partir de un archivo de ejemplo.
2. Definir:
   - `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
   - Configuracion de base de datos (`DATABASE_URL` o `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
   - Credenciales OCR (`GOOGLE_APPLICATION_CREDENTIALS`) o banderas `USE_MOCK_OCR`, `GCV_DISABLED`.
   - `VISION_MAX_PER_MONTH` y `API_SECRET_TOKEN` si aplica.
   - `CELERY_BROKER` y `CELERY_BACKEND` cuando se ejecute Celery.

## 3. Instalar dependencias
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Migraciones y datos iniciales
```bash
python manage.py migrate
python manage.py createsuperuser    # Usuario administrativo
```
> Opcional: cargar fixtures especificas del proyecto si existen (`python manage.py loaddata <fixture.json>`).

## 5. Ejecutar servicios de desarrollo
```bash
python manage.py runserver 0.0.0.0:8000
```

### Ejecucion con Docker
```bash
docker compose up --build
```
- `django`: expone `http://localhost:8000`.
- `celery`: worker opcional para tareas asincronas.
- `redis`: soporte para colas/locks.

## 6. Verificaciones posteriores
- `python manage.py check`: valida configuracion de Django.
- `pytest`: ejecuta pruebas unitarias.
- `python manage.py spectacular --color --file schema.yml`: regenera el esquema OpenAPI.
- `python manage.py report_vision_usage`: corrobora que el contador OCR este operativo.
- `import-linter --config pyproject.toml`: valida contratos de arquitectura.

## 7. Configuracion de almacenamiento
- Desarrollo: `DjangoDefaultStorageAdapter` utiliza el filesystem local (`media/`).
- Produccion: ajustar `DEFAULT_FILE_STORAGE` o reemplazar el adaptador para apuntar a S3, GCS o Azure Blob. Mantener rutas relativas para compatibilidad con `MediaProtectedAPIView`.

## 8. Consideraciones para despliegue
- Establecer `DEBUG=False`, `SECURE_PROXY_SSL_HEADER`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE` y `ALLOWED_HOSTS` apropiados.
- Ejecutar `python manage.py collectstatic --noinput` si se sirven archivos estaticos desde Django.
- Configurar monitoreo de `VisionMonthlyUsage` para anticipar limites de OCR.
