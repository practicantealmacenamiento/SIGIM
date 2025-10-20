# Backend – Registro de Camiones

API REST construida con **Django 5 + DRF** bajo una arquitectura tipo **Hexagonal / Clean Architecture**.  
El proyecto separa claramente el dominio (`domain/`), aplicación (`application/`), infraestructura (`infrastructure/`) y capa de interfaces (`interfaces/`), permitiendo probar la lógica de negocio sin depender del ORM.

## Características principales

- Flujo de formulario dinámico con guardado pregunta a pregunta (`/api/v1/cuestionario/guardar_avanzar/`).
- Pregunta de **proveedores** con soporte para múltiples filas (JSON con `nombre`, `estibas`, `recipientes`, `unidad`, `orden_compra` opcional).
- OCR de placas/precintos con adaptador de storage y visión (mock o GCP Vision).
- Autenticación unificada (token DRF) con endpoints `/api/v1/login/`, `/api/v1/whoami/`, `/api/v1/logout/`.
- Serializadores manuales (sin `ModelSerializer`) y repositorios explícitos para evitar dependencias directas del ORM.
- OpenAPI/Swagger disponible vía `drf-spectacular` para uso interno (`/api/schema/`, `/api/docs/`). 

---

## Requisitos

- Python 3.10+ (se recomienda 3.11 o 3.12)
- Pip/Pipenv/Poetry (el proyecto usa `pyproject.toml` – puedes instalar con `pip install -r requirements.txt` si lo prefieres).
- SQLite viene soportado por defecto; puedes apuntar a Postgres cambiando variables de entorno.

---

## Instalación rápida

```bash
cd BACK_FormContainers
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuración de entorno

Replica `.env.dev` o `.env.prod` según necesidad. El archivo mínimo (`.env`) debería contener:

```env
DEBUG=True
SECRET_KEY=dev-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# CORS / CSRF para el frontend (ajusta los orígenes que uses)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Opcional: credenciales para OCR externo
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/credenciales.json
```

También puedes definir claves especiales para el API Admin en el frontend (`NEXT_PUBLIC_*`) y para storage/vision en un `.env` extendido.

---

## Migraciones y datos iniciales

```bash
python manage.py makemigrations   # (si hiciste cambios locales)
python manage.py migrate

# Crea un usuario administrador
python manage.py createsuperuser
```

> TIP: El formulario de login del frontend mostrará “Usuario y/o contraseña incorrectos” al recibir un 400 desde `/api/v1/login/`. 
> Asegúrate de crear al menos un usuario activo antes de probar.

---

## Servidor de desarrollo

```bash
python manage.py runserver
```

Endpoints principales:

- `POST /api/v1/login/` – Login (username o email) → devuelve token (`token`).
- `GET /api/v1/whoami/` – Requiere token o sesión. Devuelve `"user": {...}` y marca cookies auxiliares (`is_staff`, `auth_username`).
- `POST /api/v1/logout/` – Revoca token y limpia sesión/cookies.
- `POST /api/v1/cuestionario/guardar_avanzar/` – Guarda respuesta y retorna la siguiente pregunta. Para proveedores espera `answer_text` con JSON (ver ejemplo abajo).
- `GET /api/v1/historial/reguladores/` – Historial agregando fase 1 / fase 2 por regulador.

Swagger interno (personal staff): `/api/docs/` (requiere usuario staff).

---

## Proveedores con múltiples filas

Para la pregunta con `semantic_tag = "proveedor"` el frontend envía JSON en `answer_text`:

```json
[
  {
    "nombre": "Proveedor A",
    "estibas": 3,
    "recipientes": 5,
    "unidad": "KG",
    "orden_compra": "OC-001"   // Opcional: puede omitirse o ser "".
  },
  {
    "nombre": "Proveedor B",
    "estibas": 1,
    "recipientes": 2,
    "unidad": "UN",
    "orden_compra": ""         // Permitido: se almacenará vacío.
  }
]
```

El servicio (`QuestionnaireService.save_and_advance`) fusiona las filas por `(nombre, orden_compra)` y guarda cada proveedor como una `Answer` con `meta`:

```python
{
  "estibas": 3,
  "recipientes": 5,
  "unidad": "KG",
  "orden_compra": ""
}
```

En el historial (`/historial/{submission}`) se muestran todas las filas y sus datos en un panel de “Datos adicionales”.

---

## Estructura del proyecto

```
BACK_FormContainers/
├─ app/
│  ├─ domain/          # Entidades, reglas, puertos (interfaces)
│  ├─ application/     # Casos de uso (services), comandos, reglas de negocio
│  ├─ infrastructure/  # Modelos Django, repositorios concretos, serializers
│  └─ interfaces/      # Views DRF, serializers de entrada/salida, auth API
├─ core/settings.py    # Configuración Django (usa django-environ para .env)
├─ forms_export.json   # Ejemplo de cuestionario exportado (referencia)
└─ README.md           # Este archivo
```

---

## Flujo de autenticación

1. Frontend envía `POST /api/v1/login/` con `{ "username": "...", "password": "..." }`.
2. Backend autentica, emite token (tabla `authtoken_token`) y devuelve `{ "token": "...", "user": {...} }`.
3. También inicia sesión Django y setea cookies auxiliares (`csrftoken`, `is_staff`, `auth_username`).
4. El frontend guarda el token en `localStorage` y añade `Authorization: Bearer <token>` a las llamadas.
5. `GET /api/v1/whoami/` devuelve el usuario y renueva las cookies (ayuda a SSR y middleware).

Si el login falla con 400, el frontend muestra “Usuario y/o contraseña incorrectos” y no intenta rutas alternativas.

---

## Scripts útiles

```bash
# Ejecutar tests (unitarios + mappers)
pytest

# Generar archivo OpenAPI en build/
python manage.py spectacular --file build/openapi-schema.yaml

# Cargar fixtures (si añades dumps en backend/app/fixtures)
python manage.py loaddata fixtures/initial_data.json
```

---

## Trucos

- `python manage.py shell` → interactuar con repositorios/servicios (usa `ServiceFactory`).
- `python manage.py createsuperuser` → accede a Django admin (`/admin/`).
- `python manage.py collectstatic` → si sirves archivos estáticos en producción.

---

## Licencia / Autor

El código se entrega para uso interno del proyecto Registro de Camiones.  
Consúltanos antes de distribuirlo o integrarlo en otros sistemas.
