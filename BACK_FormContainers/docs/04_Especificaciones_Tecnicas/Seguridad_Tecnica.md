# Plan de Seguridad Tecnica

## Controles de acceso
- Autenticacion mediante token (header `Authorization: Bearer/Token`) o cookies de sesion con CSRF (`BearerOrTokenAuthentication`).
- Endpoints administrativos bajo `IsAdminUser` y rutas `api/v1/management/*`.
- Documentacion privada (`/api/schema`, `/api/docs`) disponible solo para usuarios staff autenticados.

## Proteccion de datos
- Campos sensibles (contrasenias) se cifran con `make_password` al crear usuarios administrativos (`AdminUserViewSet`).
- Archivos cargados se almacenan con nombres aleatorios (`uuid4`) evitando colisiones y exponiendo solo rutas relativas.
- Validacion estricta de rutas en `MediaProtectedAPIView` para prevenir path traversal.

## Comunicacion segura
- Configurar HTTPS en todos los entornos productivos; habilitar `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`.
- Mantener `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` sincronizados con los dominios oficiales.
- Para despliegues detras de proxy, propagar cabeceras `X-Forwarded-Proto` y `X-Forwarded-For`.

## Gestion de secretos
- Usar `.env` gestionado por la plataforma de despliegue (Vault, AWS SSM, Azure Key Vault).
- Rotar `SECRET_KEY` y tokens de API de forma periodica y documentar el proceso en el runbook de soporte.
- No almacenar credenciales OCR ni claves de base de datos en archivos versionados.

## Seguridad de archivos
- Validar tipo MIME y tamano de archivos en `GuardarYAvanzar` y `GuardarRespuestaSerializer`.
- Limitar a 32 MB el tamano maximo de subida (`DATA_UPLOAD_MAX_MEMORY_SIZE`).
- Considerar antivirus o scanner externo si se habilitan formatos adicionales.

## Hardening de dependencias
- Revisar vulnerabilidades con `pip-audit` o `safety` mensualmente.
- Mantener Docker base `python:3.12-alpine` actualizada con parches de seguridad.
- Ejecutar `python manage.py check --deploy` antes de cada liberacion para detectar configuraciones inseguras.

## Auditoria y trazabilidad
- Registrar eventos de login/logout y cambios administrativos.
- Mantener historial de submissions con timestamps para auditoria forense.
- En caso de incidentes, utilizar logs centralizados y respaldos de base de datos cifrados.
