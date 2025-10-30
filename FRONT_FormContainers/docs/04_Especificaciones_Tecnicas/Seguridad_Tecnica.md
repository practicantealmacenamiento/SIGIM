# Plan de Seguridad Tecnica

## Proteccion de rutas y sesiones
- El middleware de Next revisa cookies `sessionid`, `auth_token` e `is_staff` antes de servir paginas protegidas.
- `AuthProvider` limpia tokens y cookies al cerrar sesion y sincroniza `is_staff` con `whoami`.
- `installGlobalAuthFetch` añade `Authorization` en `window.fetch`, pero el backend sigue siendo la autoridad de permisos.

## Manejo de datos
- Los clientes HTTP normalizan errores sin imprimir detalles sensibles (se expone `error_id` cuando el backend lo provee).
- Las imagenes y respuestas se procesan en memoria y nunca se almacenan en el frontend; los borradores solo guardan metadatos necesarios.
- Los tokens se guardan en `localStorage` con claves configurables (`NEXT_PUBLIC_AUTH_TOKEN_KEY`) y se purgan al cerrar sesion.

## Comunicacion segura
- Requiere HTTPS en ambientes productivos; configura el proxy o hosting (Vercel, Nginx) para forzar TLS.
- Cuando se usa proxy (`NEXT_PUBLIC_API_URL=/api`), asegure rewrites seguros en `next.config.ts` para evitar exposicion de origenes internos.
- Evitar exponer la URL real del backend en navegadores compartidos si la politica requiere ocultarla (usar proxy relativo).

## Contenido estatico y build
- Las fuentes locales se sirven desde `src/app/fonts` con permisos limitados; evitar cargar fuentes externas sin revisar licencias.
- Garantizar que la build (`npm run build`) se genere en entorno controlado, firmando artefactos si la plataforma lo permite.

## Dependencias y auditorias
- Ejecutar `npm audit` y revisar vulnerabilidades criticas antes de cada release.
- Actualizar Next.js y React cuando existan parches de seguridad (seguir changelog oficial).
- Revisar configuraciones de ESLint para prevenir XSS (p. ej. `next/no-img-element`, `react/no-danger`).

## Integracion con backend
- Mantener sincronizadas politicas de CORS y CSRF en Django con los dominios del frontend.
- Evitar exponer endpoints administrativos a usuarios sin `is_staff`; el middleware y el backend deben coincidir en reglas.
- Documentar cualquier bypass temporal (feature flags) y removerlos tras la solucion permanente.

