# Arquitectura y Patrones

## Capas principales
- **Rutas (App Router)**: alojadas en `src/app/`, con grupos `(routes)` para organizar dominios (`formulario`, `historial`, `panel`, `admin`, `auth`). Cada pagina decide si es cliente (`"use client"`) o puede permanecer como componente de servidor.
- **Componentes**: ubicados en `components/`. Se divide en auth, formulario, inputs, header y theme. Los componentes encapsulan UI, validaciones y acciones especificas.
- **Hooks y estado**: `components/formulario/useFormFlow` maneja todo el estado del cuestionario (items, borradores, OCR, envios). `useSessionState` administra la señal de sesión y tokens compartidos.
- **Clientes HTTP**: `lib/http.ts` (wrapper base) y `lib/api.*.ts` para cada modulo (form, historial, panel, admin). Todos usan `fetch` con configuracion coherente de cabeceras y credenciales.
- **Utilidades**: `lib/draft.ts` (almacenamiento tolerante a browser), `lib/ui.ts` (helpers de presentacion), `lib/uuid.ts`, etc.
- **Proteccion de rutas**: `middleware.ts` corre en el edge y evita cargar paginas si no hay sesion valida.
- **Tipos**: `types/form.ts` replica contratos del backend para mantener tipado fuerte en TS.

## Patrones aplicados
- **Estado de autenticacion**: `useSessionState` expone las banderas `authed`, `isStaff` y `username`, reaccionando a cambios de `localStorage`, focus y eventos personalizados para evitar prop drilling.
- **Gateway HTTP centralizado**: `http.ts` y `fetchApi` agregan CSRF, `credentials`, normalizacion de errores y auth headers. Evita duplicar logica en componentes.
- **Strategy para prefijos de API**: `apiTry` (en `lib/api.admin.ts`) itera sobre posibles rutas (`/management`, `/admin`, `/usuarios`) para tolerar cambios de backend.
- **State machines ligeras**: `useFormFlow` controla transiciones (`loading`, `sending`, `mostrarResumen`, `finalizado`) y estados de cada pregunta (`saved`, `editing`, `autoFromOCR`).
- **Borradores tolerantes**: `lib/draft.ts` intenta usar localStorage, luego sessionStorage y finalmente memoria para garantizar persistencia aun con restricciones.
- **Inyeccion de fetch global**: `installGlobalAuthFetch` intercepta `window.fetch` para agregar `Authorization` cuando exista token, facilitando integracion con librerias de terceros.
- **Debounce y memoizacion**: `useDebounced` en `panel/page.tsx` y `useMemo` en varios componentes evitan renders o llamadas redundantes.
- **Segregacion de responsabilidades**: las paginas se limitan a obtener parametros, estados globales y renderizar componentes; la logica de negocio reside en hooks/utilidades.

## Consideraciones de diseño
- **Tema y accesibilidad**: `ThemeProvider` controla modo claro/oscuro; se incluyen skip links y estados focus visibles.
- **Internacionalizacion**: se usa localidad `es-CO` en formateadores (`Intl.DateTimeFormat`). El texto se mantiene en español consistente.
- **Errores de red**: se muestran mensajes legibles y se evita interrumpir la UI (por ejemplo, `normalizeApiError`).
- **Compatibilidad con backend**: los clientes normalizan respuestas variantes para soportar cambios graduales en el backend.
- **Optimismo controlado**: las operaciones esperan confirmacion del backend antes de marcar elementos como `saved`; los borradores se actualizan solo cuando es seguro.
- **Seguridad**: el middleware y los componentes admin validan `is_staff` para evitar exponer vistas sensibles, alineado con el backend.

Esta arquitectura permite evolucionar cada modulo de forma independiente sin romper el contrato con el backend ni sacrificar la experiencia del usuario final.
