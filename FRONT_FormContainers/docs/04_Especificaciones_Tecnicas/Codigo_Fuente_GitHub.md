# Codigo Fuente y Estructura

## Repositorio
- Nombre sugerido: `sigim-frontend`.
- Rama principal: `main` (alineada con el backend).
- Pipeline recomendado: `npm run lint`, `npm run build`, pruebas E2E opcionales (Playwright/Cypress) y verificaciones de accesibilidad.

## Estructura principal
```
FRONT_FormContainers/
├── components/                # UI modular (auth, formulario, inputs, header, theme)
├── lib/                       # Clientes HTTP, utilidades de auth, draft y UI
├── src/app/                   # Rutas App Router (layout, formularios, historial, panel, admin)
│   ├── (routes)/              # Segmentos agrupados por dominio funcional
│   ├── helpers/               # Helpers compartidos (fetch patch, etc.)
│   └── fonts/                 # Fuentes locales (FFFAcid, Acid Grotesk)
├── types/                     # Tipos compartidos con el backend
├── public/                    # Recursos estaticos (imagenes, favicon)
├── middleware.ts              # Proteccion de rutas (login, admin)
├── next.config.ts             # Configuracion Next.js (rewrites/proxies)
├── eslint.config.mjs          # Reglas de linting
├── tsconfig.json              # Configuracion TypeScript
├── README.md                  # Guia rapida
└── docs/                      # Documentacion tecnica (este directorio)
```

## Convenciones principales
- Componentes de UI en `components/` exportan funciones puras y se anotan con `"use client"` cuando requieren hooks.
- Las rutas del App Router se organizan en grupos `src/app/(routes)/<modulo>/page.tsx` para aislar responsabilidades.
- Todo acceso a la API se canaliza mediante `lib/api.*.ts` o `lib/http.ts`; las paginas y componentes reciben datos mediante props/hook.
- Las variables `NEXT_PUBLIC_*` se leen exclusivamente dentro de los clientes `lib/api.*.ts` o en paginas de configuracion.
- Se usan tipos compartidos (`types/form.ts`) para garantizar compatibilidad con las respuestas del backend.

## Buenas practicas de versionamiento
- Usar commits atomicos con prefijos orientados a modulo (`feat(form)`, `fix(historial)`, `docs(front)`).
- Abrir Pull Requests describiendo cambios visuales y adjuntando capturas cuando se afecta la UI.
- Etiquetar versiones que van a produccion (`frontend-vMAJOR.MINOR.PATCH`) y referenciar el tag correspondiente del backend.
- Mantener GitHub Actions o pipelines equivalentes con tareas de lint/build y opcionalmente tests E2E.

## Recursos adicionales
- `README.md` en la raiz resume scripts y variables de entorno.
- `BACK_FormContainers/docs/` contiene la documentacion del backend con la cual debe mantenerse paridad de contratos.
- Se recomienda documentar flujos visuales en una herramienta de diseño (Figma, Miro) y enlazarlos desde la wiki corporativa.

