# Entorno de Desarrollo

## Requisitos minimos
- **Sistema operativo**: Windows 10+, macOS 12+ o distribucion Linux con soporte para Node.js 18.
- **Node.js**: v18.18 o superior (recomendado LTS). Next.js 15 requiere fetch y APIs modernas.
- **npm**: v9 o superior (yarn/pnpm son compatibles si se gestionan manualmente).
- **Backend**: instancia accesible de SIGIM (local o remota) para consumir `/api/v1/`.
- **Herramientas opcionales**: Chrome/Edge DevTools, extensión React Developer Tools, Sentry CLI (si se integra).

## Configuracion inicial
```bash
npm install
cp .env.local.example .env.local   # crea archivo con variables base (si existe ejemplo)
```

Variables recomendadas en `.env.local`:
- `NEXT_PUBLIC_BACKEND_ORIGIN` – URL absoluta del backend (ej. `http://localhost:8000`).
- `NEXT_PUBLIC_API_PREFIX` – prefijo versionado (`/api/v1` por defecto).
- `NEXT_PUBLIC_API_URL` – alternativa relativa (`/api`) o absoluta cuando se usa proxy.
- `NEXT_PUBLIC_Q_FASE1_ID` / `NEXT_PUBLIC_Q_FASE2_ID` – cuestionarios por defecto para fases.
- `NEXT_PUBLIC_USE_CREDENTIALS` – `true` para enviar cookies (default).
- `NEXT_PUBLIC_AUTH_DEBUG` – `1` habilita logs de autenticacion en consola.
- `NEXT_PUBLIC_ADMIN_PREFIX`, `NEXT_PUBLIC_ADMIN_MGMT_PREFIX` – ajustan clientes admin si el backend expone rutas diferentes.

## Scripts npm
- `npm run dev` – inicia el servidor de desarrollo (Turbopack) en `http://localhost:3000`.
- `npm run build` – genera la build optimizada (`.next/`).
- `npm run start` – sirve la build en modo produccion.
- `npm run lint` – ejecuta ESLint con la configuracion de Next 15.

## Herramientas y extensiones sugeridas
- **VSCode + ESLint** para linting en caliente.
- **Next DevTools** (experimental) para inspeccionar rutas y fetch cache.
- **React Developer Tools** para depurar estado de `AuthProvider` y `useFormFlow`.
- **Redux DevTools** no es necesario (no se usa Redux), pero se puede configurar para inspeccionar `zustand` si se incorpora a futuro.

## Integracion con backend
- Configura `NEXT_PUBLIC_API_URL=/api` y crea un rewrite en `next.config.ts` cuando el backend corre en el mismo host (proxy).
- En desarrollo local puedes usar `NEXT_PUBLIC_BACKEND_ORIGIN=http://127.0.0.1:8000` y dejar `NEXT_PUBLIC_API_URL` vacio para llamar directo.
- Asegurate de compartir cookies (`credentials: include`) y exponer `CSRF_TRUSTED_ORIGINS` en Django si usas dominio distinto.

