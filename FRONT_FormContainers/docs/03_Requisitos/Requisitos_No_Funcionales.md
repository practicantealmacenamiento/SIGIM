# Requisitos No Funcionales

## Seguridad
- **RNF-01**: El middleware y las utilidades de autenticación (`clearAuthToken`, `notifyAuthListeners`) deben limpiar artefactos de sesión (`auth_token`, `is_staff`, `sessionid`) al cerrar sesión para evitar escalamiento de privilegios.
- **RNF-02**: Todas las peticiones que modifiquen datos deben enviar `credentials: "include"` y cabecera `X-CSRFToken` cuando exista (`lib/http.ts`, `lib/api.form.ts`).
- **RNF-03**: El panel administrativo debe validar `is_staff` en el cliente y confiar en las restricciones del backend para acciones destructivas.
- **RNF-04**: Las variables `NEXT_PUBLIC_*` nunca deben exponer secretos; solo se utilizan para configuraciones publicas (URLs, IDs de cuestionario, banderas de debug).

## Rendimiento y UX
- **RNF-10**: Las paginas deben renderizar estados de carga (`Suspense`, placeholders) en menos de 200 ms para evitar pantallas en blanco.
- **RNF-11**: `useFormFlow` debe evitar peticiones duplicadas controlando `inFlight` y reusando resultados de OCR.
- **RNF-12**: Los helpers (`fetchApi`, `apiTry`) deben reutilizar headers y manejar timeouts para no bloquear la UI.
- **RNF-13**: Las listas paginadas y buscadores deben aplicar debouncing y limitar resultados para reducir carga en el backend.

## Calidad y mantenibilidad
- **RNF-20**: El codigo debe permanecer alineado con la estructura modular (App Router, `components/`, `lib/`, `types/`) y seguir las guias de estilo de ESLint/Prettier (`npm run lint`).
- **RNF-21**: Los normalizadores de errores (`pickErrorMessage`, `normalizeApiError`) deben mantener compatibilidad con las respuestas de DRF.
- **RNF-22**: Los componentes deben ser reutilizables y recibir props controladas para facilitar tests y futuras migraciones a Storybook.

## Observabilidad
- **RNF-30**: Los errores capturados en fetch deben lanzar exceptions con `status`, `data` y `url` para facilitar trazas en Sentry/console (`lib/http.ts`).
- **RNF-31**: La exportacion CSV debe registrar (en consola o herramienta externa) la cantidad de filas exportadas para auditoria.
- **RNF-32**: El equipo debe integrar herramientas de analitica o monitoreo (Sentry, Datadog RUM, Google Analytics) sin modificar el core de la aplicacion.

## Compatibilidad
- **RNF-40**: Compatibilidad garantizada con navegadores Chromium y Firefox recientes; Safari debe revisarse antes de cada despliegue mayor.
- **RNF-41**: La aplicacion debe ejecutarse con Node.js 18+ y browsers que soporten ECMAScript 2022.
- **RNF-42**: Los componentes deben evitar APIs solo disponibles en servidor durante la hidratacion (usar guards `typeof window !== "undefined"`).
