# Sistema de Formularios - Plataforma Completa

Plataforma interna que integra un backend Django (Clean Architecture) y un frontend Next.js para gestionar el ciclo completo de formularios regulados, incluyendo OCR, historial por fases y panel administrativo.

## Resumen funcional
- Formularios dinamicos por fases (entrada y salida) con validaciones, OCR y registros ligados a actores.
- Historial enriquecido con filtros por fechas, estado, actor y exportacion CSV directa desde el frontend.
- Autenticacion unificada: login, cookies con token, middleware protector y control de roles `is_staff`.
- APIs versionadas (`/api/v1`) con catalogos, cuestionarios, media protegida y vistas de administracion.
- Documentacion funcional y tecnica en `BACK_FormContainers/docs/` para soporte y despliegue.

## Estructura del repositorio
```
ROOT/
|-- BACK_FormContainers/    # Backend Django + Clean Architecture + docs tecnicos
|-- FRONT_FormContainers/   # Frontend Next.js 15 (App Router)
`-- README.md               # Guia general (este archivo)
```

## Stack principal
- Backend: Python 3.11, Django 5.2, Django REST Framework, Celery opcional, SQL Server (prod) y SQLite (dev), Google Vision (OCR).
- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS 4, next-themes, middleware de autenticacion personalizado.

## Requisitos
- Backend: Python 3.11+, pip, virtualenv recomendado, controlador "ODBC Driver 17 for SQL Server" para ambientes con MSSQL, Redis opcional (Celery).
- Frontend: Node.js 18+, npm 9+ (o equivalente), navegador moderno con soporte ES2022.

## Configuracion inicial
1. Crear y activar un entorno virtual en `BACK_FormContainers` (por ejemplo `python -m venv .venv`).
2. Copiar `.env.dev` a `.env` y ajustar claves sensibles: `SECRET_KEY`, `API_SECRET_TOKEN`, credenciales de base de datos, rutas de Google Vision.
3. Instalar dependencias backend: `pip install -r requirements.txt`.
4. Ejecutar migraciones iniciales: `python manage.py migrate` (usa SQLite en dev).
5. Copiar `FRONT_FormContainers/.env.local` (o crearlo) definiendo los `NEXT_PUBLIC_*` segun el entorno.
6. Instalar dependencias frontend: `npm install` dentro de `FRONT_FormContainers`.

## Backend
### Scripts utiles
- `python manage.py runserver 0.0.0.0:8000`: servidor de desarrollo.
- `python manage.py createsuperuser`: crear usuario staff para pruebas.
- `python manage.py collectstatic`: requerido para despliegues productivos.
- `pytest`: ejecuta pruebas unitarias desde la raiz del backend.

### Base de datos y tareas
- Desarrollo usa SQLite (`DB_BACKEND=sqlite`); produccion soporta MSSQL configurando variables `DB_*`.
- Celery y Redis estan preparados; activa los servicios ajustando `CELERY_BROKER` y `CELERY_BACKEND`.
- La capa `app/infrastructure` contiene los repositorios concretos y adaptadores externos (Vision, almacenamiento).

## Frontend
- `npm run dev`: desarrollo con Turbopack (http://localhost:3000) y middleware de proteccion de rutas.
- `npm run build` y `npm run start`: build y servidor productivo.
- `npm run lint`: asegura convenciones ESLint de Next.
- Configura el origen del backend mediante `NEXT_PUBLIC_BACKEND_ORIGIN` y `NEXT_PUBLIC_API_PREFIX`; si usas un proxy local, define `NEXT_PUBLIC_API_URL`.

## Variables de entorno
Variables clave del backend (`BACK_FormContainers/.env`):

| Variable | Descripcion | Obligatoria |
|----------|-------------|-------------|
| `DEBUG` | Activa modo desarrollo | Si (en dev) |
| `SECRET_KEY` | Clave interna de Django | Si |
| `ALLOWED_HOSTS` | Hosts permitidos por Django | Si |
| `API_SECRET_TOKEN` | Token compartido para clientes internos | Si |
| `DB_BACKEND` | `sqlite` o `mssql` segun ambiente | Si |
| `GOOGLE_APPLICATION_CREDENTIALS` | Ruta al JSON de Google Vision | Si (OCR) |
| `CELERY_BROKER` / `CELERY_BACKEND` | URLs de Redis para tareas | No |
| `NEXT_PUBLIC_BACKEND_ORIGIN` | URL que se expone al frontend | Si |

Variables clave del frontend (`FRONT_FormContainers/.env.local`):

| Variable | Descripcion | Obligatoria |
|----------|-------------|-------------|
| `NEXT_PUBLIC_BACKEND_ORIGIN` | URL publica del backend (`http://localhost:8000`) | Si |
| `NEXT_PUBLIC_API_PREFIX` | Prefijo versionado (`/api/v1`) | Si |
| `NEXT_PUBLIC_API_URL` | Proxy o URL absoluta alternativa | No |
| `NEXT_PUBLIC_USE_CREDENTIALS` | Fuerza `credentials: include` en fetch | No |
| `NEXT_PUBLIC_Q_FASE1_ID` | UUID default del cuestionario Fase 1 | No |
| `NEXT_PUBLIC_Q_FASE2_ID` | UUID default del cuestionario Fase 2 | No |
| `NEXT_PUBLIC_AUTH_DEBUG` | Activa trazas de autenticacion (`1`) | No |

## Flujo de desarrollo local
1. Terminal A (backend):
   ```
   cd BACK_FormContainers
   source .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
   python manage.py runserver 0.0.0.0:8000
   ```
2. Terminal B (frontend):
   ```
   cd FRONT_FormContainers
   npm run dev
   ```
3. Accede a `http://localhost:3000`, inicia sesion y valida que los llamados a `/api/v1` respondan con codigo 200.

## API y rutas destacadas
- `POST /api/v1/login/`, `GET /api/v1/whoami/`, `POST /api/v1/logout/`: autenticacion unificada.
- `POST /api/v1/verificar/`: OCR universal para preguntas configuradas.
- `POST /api/v1/submissions/` y `POST /api/v1/submissions/<uuid>/finalize/`: ciclo de vida de una submission.
- `POST /api/v1/cuestionario/guardar_avanzar/`: guarda respuestas y entrega la siguiente pregunta.
- `GET /api/v1/historial/reguladores/`: historial consolidado para el frontend.
- `GET /api/v1/management/*`: CRUD administrativo (usuarios, cuestionarios, actores) protegido por permisos.

## Arquitectura
- `app/domain`: entidades, reglas y puertos de negocio.
- `app/application`: servicios y casos de uso que coordinan la capa de dominio.
- `app/infrastructure`: implementaciones concretas (ORM, Vision, repositorios, storage).
- `app/interfaces`: vistas DRF, servicios HTTP reutilizables (`http/services.py`), autenticacion y manejo de excepciones.
- Frontend estructurado en `src/app` (App Router), `components/` (UI y widgets), `lib/` (clientes HTTP, utilidades) y `types/`.

## Documentacion
- Documentacion formal en `BACK_FormContainers/docs/README.md` con enlaces actualizados a descripcion general, requisitos, arquitectura y despliegue (alineado con la reorganizacion 2025).
- Para detalles de servicios HTTP reutilizables, historial y casos de uso revisa `BACK_FormContainers/docs/01_Descripcion_General.md` y `docs/05_Arquitectura_y_Disenio/Arquitectura_y_Patrones.md`.
- Esquema interactivo de la API disponible en `/api/v1/docs/` (Swagger) y `/api/v1/redoc/` cuando el backend esta en ejecucion.
- El frontend mantiene su documentacion funcional en `FRONT_FormContainers/docs/`.

## Testing y calidad
- Backend: `pytest` (puede configurarse coverage si se requiere), `python manage.py check` valida dependencias.
- Frontend: `npm run lint` asegura estilo; puede agregarse Playwright o Vitest segun necesidades.
- Ejecuta los comandos anteriores antes de preparar un release o merge importante.
