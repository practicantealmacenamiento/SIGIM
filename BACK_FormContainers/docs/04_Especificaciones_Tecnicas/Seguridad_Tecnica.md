# Plan de Seguridad Tecnica

## Controles de acceso
- Autenticacion unificada mediante tokens DRF o cookies de sesion; las vistas aplican `BearerOrTokenAuthentication` y `IsAuthenticated`.
- Rutas administrativas (`/api/v1/management/*`, `/api/v1/schema`, `/api/v1/docs`) protegidas con `IsAdminUser`.
- Integraciones de sistema a sistema pueden exigir `TokenRequiredForWrite` (header `Authorization: Bearer` o `X-API-KEY`), configurable via `API_SECRET_TOKEN`.

## Proteccion de datos
- Contrasenas cifradas con make_password (AdminUserService) y politicas de rotacion documentadas por TI.
- Archivos guardados con nombres aleatorios y rutas normalizadas (`DjangoDefaultStorageAdapter`), evitando exposicion directa del sistema de archivos.
- `MediaProtectedAPIView` valida rutas (`..`, backslashes) antes de servir archivos y usa `FileResponse` solo para usuarios autenticados.
- Campos sensibles (documentos, tokens) se enmascaran en logs y respuestas.

## Comunicacion segura
- Habilitar HTTPS en todos los entornos productivos y configurar `SECURE_PROXY_SSL_HEADER`, `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`.
- Restricciones CORS y CSRF basadas en listas blancas (`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`), permitiendo solo dominios autorizados.
- Limitar `ALLOWED_HOSTS` al dominio oficial y direcciones internas necesarias.

## Gestion de secretos
- Variables de entorno administradas por la plataforma (Vault, AWS SSM, Azure Key Vault). Nunca versionar credenciales en el repositorio.
- Rotar periodicamente `SECRET_KEY`, tokens de servicio y credenciales de Vision, manteniendo bitacora de cambios.
- Asegurar que el archivo de credenciales de Google Vision tenga permisos restringidos y no se monte en repositorios compartidos.

## Seguridad de archivos y payloads
- Limitar uploads a 32 MB (`DATA_UPLOAD_MAX_MEMORY_SIZE`) y validar tipo MIME mediante `SaveAndAdvanceInputSerializer`.
- Eliminar archivos al borrar respuestas (`Answer.delete`) o reemplazarlos (flag `delete_old_file_on_replace`).
- Considerar antivirus o escaneo externo cuando se habiliten adjuntos proveniente de terceros.

## Hardening y auditoria
- Ejecutar `python manage.py check --deploy` antes de liberar a produccion.
- Revisar vulnerabilidades con `pip-audit` o `safety` al menos una vez por mes.
- Registrar eventos criticos con `error_id` usando `DomainExceptionTranslator` para facilitar investigacion forense.
- Monitorear el contador `VisionMonthlyUsage` para detectar uso anomalo del servicio OCR y prevenir abuso.

## Respuesta ante incidentes
- Contar con procedimientos de revocacion rapida de tokens y desactivacion de cuentas.
- Mantener respaldos cifrados de base de datos y archivos, listos para restauracion.
- Documentar postmortems e incorporar acciones preventivas al plan de soporte.
