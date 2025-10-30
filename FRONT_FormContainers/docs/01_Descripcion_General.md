# Descripcion General del Proyecto

El frontend de **SIGIM** implementa la experiencia web para el diligenciamiento y seguimiento de cuestionarios logisticos. Se construye sobre **Next.js 15** (App Router) y **React 19**, emplea componentes de cliente y servidor segun el flujo, y aplica estilos con **Tailwind CSS 4**. La aplicacion consume la API REST expuesta por el backend Django (`/api/v1/`) y comparte el mismo modelo de autenticacion unificada.

## Proposito de la plataforma
- Ofrecer a operadores y personal administrativo una interfaz accesible para crear, completar y revisar submissions en tiempo real.
- Integrar verificacion OCR, gestion de actores y control de fases dentro del flujo de formulario.
- Visibilizar historicos con filtros avanzados y exportacion, incluyendo herramientas para continuar la fase 2 desde la fase 1.
- Centralizar funciones administrativas (cuestionarios, actores, usuarios) en un panel protegido por roles.

## Principales modulos funcionales
- **Autenticacion y contexto** (`components/auth/`): `ClientAuthBootstrap` instala el `fetch` autenticado y sincroniza `localStorage`; el hook `useSessionState` + `AuthGate` protegen el árbol de componentes usando sólo el token almacenado.
- **Middleware de proteccion** (`middleware.ts`): intercepta rutas, redirige a `/login` si no hay sesion y restringe secciones `/admin` para personal con `is_staff=1`.
- **Formulario dinamico** (`components/formulario/`, `lib/api.form.ts`): `useFormFlow` coordina cuestionarios, draft local, guardado incremental y consumo de OCR. Las entradas especializadas en `components/inputs/` permiten manejar actores, archivos y preguntas choice.
- **Historial y panel** (`lib/api.historial.ts`, `lib/api.panel.ts`, rutas en `src/app/(routes)`): gestionan filtros, deduplicacion, hidratacion de actores y exportacion CSV. El panel permite iniciar fase 2 desde fase 1 finalizada.
- **Cliente administrativo** (`lib/api.admin.ts`): expone utilidades resilientes (`apiTry`, `installGlobalAuthFetch`) para CRUD de cuestionarios, actores y usuarios gestionando multiples prefijos del backend.
- **Capa de UI compartida** (`components/header/`, `components/theme/`): cabecera, tema claro/oscuro, fuentes personalizadas y elementos de accesibilidad (skip link, focus management).

## Integraciones y dependencias clave
- **Next.js 15 / React 19**: App Router, `use client` en paginas que requieren interactividad, `Suspense` para estados de carga, Turbopack en entorno de desarrollo.
- **Tailwind CSS 4**: estilos centralizados en `src/app/globals.css` y tokens reutilizables (`BTN`, `CARD`, etc.).
- **next-themes**: control de tema persistente compatible con SSR/CSR.
- **Clientes HTTP propios**: `lib/http.ts` y `lib/api.*.ts` encapsulan fetch, CSRF, manejo de tokens y deteccion de errores de DRF.
- **Almacenamiento local**: `lib/draft.ts` guarda borradores e identificadores en localStorage/sessionStorage con fallback en memoria para navegadores restringidos.
- **Iconografia y fuentes**: assets alojados en `components/header/logoPrebel.tsx` y `src/app/fonts`.

## Flujo operativo resumido
1. El usuario accede al dominio y el `middleware` verifica cookies (`sessionid`, `auth_token`).
2. `RootLayout` monta `ClientAuthBootstrap` y `AuthGate`; la sesion se sincroniza leyendo el token y consultando `whoami` de forma perezosa cuando existe.
3. El usuario accede al formulario (`/formulario`) seleccionando cuestionario y fase, o al panel/historial segun su rol.
4. Durante el diligenciamiento, `useFormFlow` gestiona borradores, guardado, verificacion OCR y finalizacion.
5. En funcionalidades administrativas, `api.admin.ts` inyecta encabezados de autorizacion y maneja prefijos alternos (`/management/`).
6. El historial (`/historial`) y panel (`/panel`) llaman a `fetchHistorialEnriched` y `listarFase1Finalizados` para mostrar datos consolidados y permiten exportar o continuar fases.

## Principios de diseño
- Mantener aislamiento entre componentes UI y logica de integracion (todos los llamados a backend viven en `lib/api.*.ts`).
- Evitar acoplarse a respuestas especificas del backend usando normalizadores y multiples rutas (`apiTry`).
- Usar hooks reutilizables (`useFormFlow`, `useDebounced`) para encapsular estados complejos.
- Garantizar accesibilidad basica (skip link, estados de foco, mensajes en texto) y soporte para tema oscuro.
- Registrar y limpiar artefactos de sesion para prevenir estados inconsistentes al alternar entre operadores y staff.

Esta documentacion sirve como referencia para desarrolladores, QA y personal de soporte que operan la interfaz de SIGIM.
