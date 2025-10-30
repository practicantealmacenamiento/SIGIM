# Instalacion y Configuracion

## 1. Clonar y preparar repositorios
```bash
git clone <url-del-monorepo-o-frontend>
cd FRONT_FormContainers
npm install
```

Si el proyecto convive con el backend, mantenga ambos repos en paralelo (`BACK_FormContainers`, `FRONT_FormContainers`).

## 2. Variables de entorno
1. Copie `.env.local` de referencia (si existe) o cree uno nuevo.
2. Defina al menos:
   - `NEXT_PUBLIC_BACKEND_ORIGIN=http://localhost:8000`
   - `NEXT_PUBLIC_API_PREFIX=/api/v1`
   - `NEXT_PUBLIC_API_URL=/api` (cuando Next actua como proxy al backend)
   - `NEXT_PUBLIC_USE_CREDENTIALS=true`
   - `NEXT_PUBLIC_Q_FASE1_ID` y `NEXT_PUBLIC_Q_FASE2_ID` segun cuestionarios activos.
3. Opcionales:
   - `NEXT_PUBLIC_AUTH_DEBUG=1` para verbose logging en dev.
   - `NEXT_PUBLIC_ADMIN_PREFIX` y `NEXT_PUBLIC_ADMIN_MGMT_PREFIX` para entornos con prefijos personalizados.
   - `NEXT_PUBLIC_AUTH_TOKEN_KEY` cuando se desea un nombre distinto en `localStorage`.

## 3. Ejecucion en desarrollo
```bash
npm run dev
open http://localhost:3000
```
El servidor usa Turbopack y recarga en caliente. Los endpoints `/api/*` se pueden mapear a Django mediante rewrites en `next.config.ts`.

## 4. Build y verificacion
```bash
npm run lint
npm run build
npm run start # prueba la build en http://localhost:3000
```

## 5. Integracion con backend
- Configura en Django las cabeceras CORS y CSRF para `http://localhost:3000`.
- Si se usa proxy inverso, asegura que `NEXT_PUBLIC_API_URL` apunte al path reescrito (ej. `/backend`).
- Comprueba que el middleware de Next (`middleware.ts`) reciba las cookies `sessionid`, `csrftoken`, `auth_token` emitidas por el backend.

## 6. Testing manual
- Iniciar sesion con una cuenta de operador y recorrer el flujo de formulario.
- Probar carga de OCR e identificar que los mensajes de error sean visibles.
- Navegar al historial, aplicar filtros y exportar CSV.
- Ingresar al panel y crear/continuar fase 2.
- Acceder al modulo admin (solo usuarios staff) y realizar operaciones CRUD basicas.

## 7. Integraciones adicionales
- Para Sentry, agrega el SDK en `src/app/layout.tsx` y `next.config.ts`.
- Para Google Analytics, implementa el script en `src/app/layout.tsx` respetando las politicas de cookies de la organizacion.

