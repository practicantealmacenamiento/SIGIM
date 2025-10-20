# Instalacion y Configuracion

## Paso 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd BACK_FormContainers
```

## Paso 2. Configurar variables de entorno
- Copiar `.env` de ejemplo o crear uno nuevo.
- Ajustar `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
- Definir credenciales OCR si se usara Google Vision.
- En ambientes productivos, desactivar `DEBUG` y ajustar `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`.

## Paso 3. Instalar dependencias
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Paso 4. Aplicar migraciones
```bash
python manage.py migrate
```

Si se requiere data base de prueba, se puede cargar `forms_export.json` mediante un comando de gestion propio o scripts de carga (no incluido por defecto).

## Paso 5. Crear usuario administrativo
```bash
python manage.py createsuperuser
```

## Paso 6. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver 0.0.0.0:8000
```

## Ejecucion con Docker
```bash
docker compose up --build
```
- El servicio `django` expone `http://localhost:8000`.
- El worker `celery` queda escuchando tareas si se usan colas.

## Tareas posteriores
- Regenerar el esquema con `python manage.py spectacular --color --file schema.yml` cuando cambien las vistas.
- Ejecutar `pytest` antes de desplegar cambios.
- Configurar almacenamiento de archivos (S3, GCS, Azure) adaptando `DjangoDefaultStorageAdapter` si es necesario.
