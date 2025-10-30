# Monitorizacion y Logs

## Configuracion base
- `core/settings.py` define logging estructurado con handler `console` y nivel `DEBUG` en desarrollo, `INFO` en produccion.
- `DomainExceptionMiddleware` y `DomainExceptionTranslator` registran cada excepcion de dominio con `error_id` y metadata (`logger=app.interfaces.exception_handlers`).
- DRF utiliza `DEFAULT_SCHEMA_CLASS=drf_spectacular`, permitiendo explorar la API y validar respuestas en `/api/v1/docs`.

## Eventos criticos a registrar
- Intentos de autenticacion (exitosos y fallidos) y cambios de rol en usuarios administrados.
- Creacion y finalizacion de submissions, incluyendo `submission_id`, `regulador_id`, `tipo_fase` y `created_by`.
- Errores en Guardar y Avanzar (validaciones, reglas de negocio, excepciones de infraestructura).
- Fallas de OCR (`ExtractionError`, `InvalidImageError`), indicando proveedor utilizado (Vision o mock) y `error_id`.
- Llamados a tareas administrativas (`report_vision_usage`, limpieza de archivos) y resultado.

## Fuentes de datos
- **Logs de aplicacion**: `docker logs`, CloudWatch, Stackdriver o plataforma equivalente.
- **Base de datos**: tablas `VisionMonthlyUsage`, `Submission`, `Answer` y `Actor` para auditoria cruzada.
- **Metrica OCR**: salida del comando `python manage.py report_vision_usage --year YYYY --month MM`.

## Monitoreo proactivo
- Health checks cada 60 s sobre `GET /api/v1/whoami` (autenticado) y `GET /api/v1/cuestionarios/`.
- Alertas por tasa de errores HTTP >= 5xx o latencias superiores a 2 s en Guardar y Avanzar.
- Seguimiento del crecimiento de la carpeta `media/` y correlacion con respuestas almacenadas.
- Alarmas cuando `VisionMonthlyUsage.count` se acerque al 80% de `VISION_MAX_PER_MONTH`.

## Tableros sugeridos
- Submissions creadas/finalizadas por dia, fase y regulador.
- Conteo de errores 4xx/5xx por endpoint y tipo de excepcion de dominio.
- Consumo OCR mensual (Vision vs mock) y porcentaje de fallos.
- Top 10 de preguntas que generan mas validaciones fallidas o truncamientos.

## Buenas practicas
- Enmascarar datos sensibles (documento, token) antes de escribir en logs.
- Incluir `request_id` o `X-Request-ID` en peticiones para correlacionar eventos.
- Automatizar revisiones de logs tras despliegues y documentar hallazgos relevantes en el plan de soporte.
