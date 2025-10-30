# Requisitos Funcionales

Los requisitos se basan en la implementacion vigente de Next.js y los clientes HTTP ubicados en `lib/`.

## Autenticacion y sesion
- **RF-01**: La aplicacion debe permitir iniciar sesion con usuario o correo, consumiendo `POST /api/login/` y almacenando token/cookies (`AuthProvider`, `components/auth`).
- **RF-02**: Durante el bootstrap se debe invocar `GET /api/whoami/` para determinar el estado de sesion y sincronizar `is_staff` en cookies (`AuthProvider` y `ClientAuthBootstrap`).
- **RF-03**: El middleware (`middleware.ts`) debe redirigir a `/login` cuando no existan `sessionid` ni `auth_token`, y bloquear `/admin/*` para usuarios sin `is_staff=1`.

## Formulario dinamico
- **RF-10**: `useFormFlow` debe crear o reanudar submissions consultando `createSubmission`, `getPrimeraPregunta` y `guardarYAvanzar` antes de renderizar el formulario.
- **RF-11**: Las respuestas deben soportar texto, numero, fecha, choice y archivos, incluyendo integracion con OCR (`verificarImagen`) y manejo de actores (`actorInput`).
- **RF-12**: El hook debe persistir borradores en almacenamiento local (`lib/draft.ts`) e informar al usuario cuando exista progreso previo.
- **RF-13**: Al finalizar el flujo se debe invocar `finalizarSubmission`, limpiar borradores y mostrar el resumen final.

## Historial y panel
- **RF-20**: `lib/api.historial.ts` debe listar historial de reguladores con filtros por fechas, placa y estado, deduplicando resultados (`fetchHistorialEnriched`).
- **RF-21**: La vista de historial (`src/app/(routes)/historial`) debe permitir exportar los resultados filtrados a CSV (`exportHistorialCSV`).
- **RF-22**: El panel (`src/app/(routes)/panel`) debe listar fase 1 finalizada, buscar fase 2 por placa y permitir continuar o crear fase 2 (`listarFase1Finalizados`, `buscarFase2PorPlaca`, `crearSubmissionFase2`).

## Catalogos y administracion
- **RF-30**: Las vistas administrativas (`/admin` y subrutas) deben consumir `lib/api.admin.ts` para CRUD de cuestionarios, actores y usuarios con reintentos (`apiTry`).
- **RF-31**: `installGlobalAuthFetch` debe inyectar encabezados `Authorization` a `window.fetch` cuando exista token almacenado.
- **RF-32**: El formulario debe exponer buscador de actores (`searchCatalogActors`) limitando resultados y mostrando tipo/documento.

## UI y accesibilidad
- **RF-40**: El layout debe renderizar `Header` con navegacion, datos del usuario y selector de tema (`components/header/header.tsx`).
- **RF-41**: Debe existir skip link visible al recibir foco para saltar al contenido principal (`layout.tsx`).
- **RF-42**: El tema claro/oscuro debe persistir mediante `ThemeProvider` y reflejarse en las clases utilitarias de Tailwind.

