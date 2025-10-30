# Objetivos y Alcance

## Objetivo general
Proveer una interfaz web confiable, accesible y alineada al backend de SIGIM que permita a operadores y personal administrativo gestionar el flujo de ingreso de mercancia con eficiencia y trazabilidad.

## Objetivos especificos
- Orquestar autenticacion, session management y proteccion de rutas reutilizando los contratos `/api/login/`, `/api/whoami/` y cookies emitidas por el backend.
- Permitir el diligenciamiento de cuestionarios dinamicos (fases 1 y 2), incluyendo adjuntos, OCR, seleccion de actores y manejo de borradores.
- Exponer historiales y paneles de control con filtros, deduplicacion de reguladores, exportacion CSV y continuidad de fases.
- Ofrecer herramientas administrativas (cuestionarios, actores, usuarios) sobre la misma UI reutilizando clientes resilientes (`lib/api.admin.ts`).
- Adaptarse a configuraciones de despliegue variadas mediante variables `NEXT_PUBLIC_*` y un cliente HTTP parametrizable.
- Mantener experiencia de usuario consistente en tema claro/oscuro, accesibilidad minima y estados de carga predecibles.

## Alcance funcional
- Rutas publicas bajo App Router:
  - `/login`: autenticacion y bootstrap del `AuthProvider`.
  - `/formulario`: flujo Guardar y Avanzar con integracion OCR y actor picking.
  - `/historial`: consulta de historicos con filtros, detalle y exportacion.
  - `/panel`: herramientas de fase 2 y creacion de submissions derivadas.
  - `/admin/*`: CRUD de catalogos y usuarios para personal staff.
- Componentes reutilizables:
  - `components/inputs/`: controles especializados (text, number, date, choice, actor, file + OCR).
  - `components/formulario/useFormFlow`: estado principal del formulario, borradores y callbacks.
  - `components/auth/*`: contexto, gate, bootstrap y wrappers para fetch.
  - `components/header/`: navegacion, selector de tema, perfil de usuario.
- Clientes de datos:
  - `lib/api.form.ts`, `lib/api.historial.ts`, `lib/api.panel.ts`, `lib/api.admin.ts`, `lib/http.ts`.
  - Utilidades de almacenamiento y draft en `lib/draft.ts` y helpers de UI en `lib/ui.ts`.
- Tipos compartidos con el backend en `types/form.ts`.

## Fuera de alcance
- Renderizado offline o modos PWA (se requiere conectividad con el backend).
- Generacion de reportes BI avanzados; solo se ofrecen exportaciones CSV basicas.
- Gestion de cache persistente mas allá de borradores locales y datos en memoria.
- Integraciones directas con otros sistemas (ERP, WMS) distintas a la API REST existente.
- Automatizacion de despliegue (CI/CD) y monitoreo externo (debe configurarse en la plataforma objetivo).

## Indicadores de exito
- Flujo Guardar y Avanzar completado sin errores en navegadores soportados (Chrome/Edge/Firefox).
- Latencia de interaccion menor a 200 ms en operaciones tipicas (navegacion entre preguntas, autocompletado OCR, filtros del historial).
- Exportaciones CSV y continuacion de fases funcionando sin inconsistencias de datos.
- Capacidad de personalizar endpoints mediante `.env.local` sin modificar codigo fuente.
- Cobertura funcional validada por QA siguiendo los criterios definidos en `03_Requisitos/`.

