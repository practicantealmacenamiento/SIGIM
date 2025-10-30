# Plan de Despliegue

## Preparacion
1. Asegurarse de que la rama `main` este estable y sincronizada con el backend correspondiente.
2. Generar numero de version/tags (`frontend-vMAJOR.MINOR.PATCH`).
3. Ejecutar `npm run lint` y `npm run build` en CI o localmente.
4. Verificar que `.env.production` (o variables en la plataforma) contenga los valores definitivos (`NEXT_PUBLIC_BACKEND_ORIGIN`, `NEXT_PUBLIC_API_URL`, etc.).

## Construccion
```bash
npm ci               # garantiza dependencias limpias
npm run build        # genera .next/
```
El resultado puede desplegarse como:
- **Aplicacion Next.js hospedada** (Vercel, Netlify): subir la build o conectar el repositorio.
- **Aplicacion en contenedor**: copiar `.next/`, `package.json`, `next.config.ts` y ejecutar `npm run start`.
- **Exportacion estandar**: no se usa `next export` (la app depende de rutas dinamicas).

## Configuracion por entorno
- Establecer `NEXT_PUBLIC_API_URL` o rewrites para apuntar al backend correcto.
- Configurar `NEXT_PUBLIC_Q_FASE1_ID` y `NEXT_PUBLIC_Q_FASE2_ID` con UUIDs reales.
- Definir `NEXT_PUBLIC_USE_CREDENTIALS=true` para permitir cookies de sesion.
- Actualizar URLs de login y redireccion en proxies o balanceadores.

## Despliegue
1. Implementar la imagen o build en el hosting seleccionado.
2. Limpiar caches CDN si aplica.
3. Actualizar rutas DNS o registros de entorno (ej. `frontend.sigim.domain`).

## Validaciones post-despliegue
- Iniciar sesion y completar una submission en entorno productivo.
- Probar verificacion OCR, historial con filtros y exportacion CSV.
- Acceder al panel y confirmar creacion/continuacion de fase 2.
- Verificar rutas `/admin/*` con usuario staff.
- Revisar consola del navegador para verificar ausencia de errores y confirmar version desplegada.

## Rollback
- Mantener al menos la version anterior lista para restaurar (build o contenedor).
- Si surge incidente, revertir el despliegue y purgar caches.
- Documentar el motivo del rollback y coordinar correcciones antes del siguiente despliegue.

