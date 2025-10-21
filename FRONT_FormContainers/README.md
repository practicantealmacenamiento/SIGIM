# Frontend - Sistema de Formularios

Aplicacion web construida con Next.js 15 (App Router) y React 19 para operar el sistema de formularios dinamicos de registro de carga. El frontend consume la API Django y ofrece autenticacion unificada, diligenciamiento de formularios por fases y herramientas internas de consulta.

## Caracteristicas clave
- Formulario dinamico por fases con soporte para OCR, actores y validaciones segun la definicion enviada por el backend.
- Vista de historial con filtros avanzados, exportacion CSV y deduplicacion de reguladores.
- Panel administrativo protegido (middleware + cookies) que solo expone rutas a personal con rol `is_staff`.
- Tema claro/oscuro, accesibilidad (skip links) y estilos con Tailwind CSS 4 + tipografias personalizadas.
- Cliente HTTP centralizado en `lib/` con manejo de tokens, cabeceras CSRF y deteccion de errores de DRF.

## Requisitos previos
- Node.js 18 o superior (recomendado LTS).
- npm 9+ o equivalente (yarn/pnpm funcionan si se gestionan manualmente).
- Backend en ejecucion o tunel accesible para consumir la API (`NEXT_PUBLIC_BACKEND_ORIGIN`).

## Instalacion rapida
1. Instalar dependencias: `npm install`
2. Duplicar el archivo `.env.local` (o crear uno nuevo) con las variables descritas abajo.
3. Ejecutar en desarrollo: `npm run dev`
4. Abrir `http://localhost:3000` y autenticarse con credenciales validas del backend.

## Scripts disponibles
- `npm run dev`: servidor de desarrollo con Turbopack.
- `npm run build`: compila la aplicacion para despliegue.
- `npm run start`: sirve la build generada.
- `npm run lint`: ejecuta ESLint con la configuracion de Next.

## Variables de entorno
Define al menos las siguientes claves en `.env.local`:

| Variable | Descripcion | Obligatorio |
|----------|-------------|-------------|
| `NEXT_PUBLIC_BACKEND_ORIGIN` | URL base del backend (por ejemplo `http://localhost:8000`) | Si |
| `NEXT_PUBLIC_API_PREFIX` | Prefijo versionado expuesto por Django (`/api/v1`) | Si |
| `NEXT_PUBLIC_API_URL` | Alternativa absoluta o relativa cuando se usa proxy (`/api`) | No |
| `NEXT_PUBLIC_USE_CREDENTIALS` | Envia cookies en las peticiones fetch (`true`/`false`) | No |
| `NEXT_PUBLIC_Q_FASE1_ID` | UUID del cuestionario por defecto para la fase 1 | No |
| `NEXT_PUBLIC_Q_FASE2_ID` | UUID del cuestionario para la fase 2 (historial) | No |
| `NEXT_PUBLIC_AUTH_DEBUG` | Habilita trazas del proveedor de auth (`1`) | No |

Si el backend requiere cabeceras especiales, ajusta `lib/http.ts` o agrega nuevas variables con la nomenclatura `NEXT_PUBLIC_*`.

## Flujo de autenticacion
- El componente `AuthProvider` consume `/api/login/` y `/api/whoami/`, almacena el token en la cookie `auth_token` y sincroniza la bandera `is_staff`.
- El middleware (`middleware.ts`) bloquea rutas si no existe `sessionid` o `auth_token` y redirige al login preservando la ruta solicitada (`?next=`).
- Durante la sesion el cliente HTTP (`lib/http.ts` y `lib/api.*.ts`) adjunta las cookies necesarias (`credentials: include`) y limpia la sesion ante errores 401.

## Estructura relevante
- `src/app/`: paginas del App Router (formulario, historial, panel, login).
- `components/`: UI modular para inputs, tarjetas, encabezados y autenticacion.
- `lib/`: clientes de API (`api.form.ts`, `api.historial.ts`, `api.admin.ts`) y utilidades compartidas.
- `middleware.ts`: proteccion de rutas a nivel de borde.
- `types/`: definiciones TypeScript exportadas por el backend.

## Trabajo diario
- Ejecuta `npm run lint` antes de subir cambios para asegurar convenciones uniformes.
- Ajusta las fuentes en `src/app/layout.tsx` cuando se agreguen tipografias nuevas.
- Para depurar peticiones, revisa `API_BASE` expuesta por `lib/api.form.ts`; muestra el destino final calculado con las variables de entorno.

Para detalles adicionales revisa la documentacion del backend en `BACK_FormContainers/docs/` y las instrucciones generales del repositorio en el README de la raiz.
