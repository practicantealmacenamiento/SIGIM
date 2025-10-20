# Monitorizacion y Logs

## Configuracion actual
- `core/settings.py` define un manejador `logging.StreamHandler` que envia eventos a la salida estandar.
- En desarrollo, `DEBUG=True` establece nivel `DEBUG` para el logger raiz y `INFO` para `django.request`.
- En produccion se recomienda fijar `DEBUG=False`, establecer nivel `INFO` o `WARNING` y redirigir la salida a un agregador (CloudWatch, Stackdriver, ELK).

## Eventos criticos a registrar
- Intentos de autenticacion fallidos y exitos (nivel `INFO`).
- Errores de OCR capturados por `DomainExceptionTranslator` (`ExtractionError`, `InvalidImageError`) con nivel `WARNING`.
- Creacion, finalizacion y edicion de submissions (nivel `INFO`) incluyendo `submission_id`, `user_id` y `regulador_id`.
- Excepciones no controladas (nivel `ERROR`) con stacktrace completo.

## Recoleccion y retencion
- Al desplegar en contenedores, utilizar drivers de logs (`json-file`, `awslogs`, `gcp`) para centralizar eventos.
- Definir politica de retencion minima de 90 dias para auditorias y trazabilidad logistica.
- Para almacenamiento en archivos, habilitar `logging.handlers.RotatingFileHandler` con compresion semanal.

## Monitoreo proactivo
- Configurar health checks sobre `GET /api/v1/whoami` y `/api/v1/cuestionario/primera/?questionnaire_id=...`.
- Medir tiempos de respuesta y tasa de errores (HTTP 5xx) mediante APM (New Relic, Datadog) o Prometheus/Nginx metrics.
- Supervisar el tamaño de la carpeta `media/` para anticipar necesidades de almacenamiento.
- Activar alertas cuando se registren mas de X `ExtractionError` en una hora, indicando problemas con el proveedor OCR.

## Dashboards sugeridos
- Graficas de submissions creadas/finalizadas por dia y por regulador.
- Conteo de errores 4xx/5xx por endpoint.
- Uso de OCR (cantidad de llamadas y porcentaje de exito vs fallo).

## Buenas practicas
- Enmascarar datos sensibles antes de registrarlos (no loguear contrasenias, tokens ni documentos completos).
- Adjuntar `request_id` o `trace_id` en cabeceras para correlacionar eventos entre servicios.
- Automatizar pruebas de logging con escenarios controlados (ejecutar `pytest` verificando que los handlers se configuran correctamente).
