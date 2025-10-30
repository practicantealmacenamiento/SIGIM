# Plan de Soporte

## Objetivos
- Mantener el backend de SIGIM disponible durante ventanas criticas de ingreso y salida de mercancia.
- Detectar y resolver incidentes antes de que escalen a impactos operacionales.
- Coordinar mantenimientos preventivos y evolutivos de forma planificada y documentada.

## Niveles de soporte
- **Nivel 1 (Mesa de ayuda)**: monitorea alertas, verifica disponibilidad (`GET /api/v1/whoami`), recopila evidencias iniciales y escala segun severidad.
- **Nivel 2 (Equipo backend)**: analiza logs de Django, estado de Celery/Redis, consumo del OCR (`report_vision_usage`), aplica hotfixes y coordina despliegues.
- **Nivel 3 (Proveedores externos)**: Google Cloud Vision, almacenamiento externo u otros servicios; se activa tras descartar causas internas.

## Flujo de atencion
1. Registrar el incidente en la herramienta ITSM (timestamp, endpoint afectado, usuario, request_id si existe).
2. Mesa de ayuda valida servicio (`whoami`), revisa logs basicos y consulta el contador de OCR si aplica.
3. Equipo backend reproduce el escenario en staging, revisa excepciones (`DomainExceptionTranslator`) y consulta bancos de datos (`Submission`, `Answer`).
4. Implementar correccion o workaround, ejecutar pruebas (`pytest`, `python manage.py check`) y proceder a despliegue controlado.
5. Documentar la causa raiz, acciones tomadas y recomendaciones preventivas antes de cerrar el ticket.

## Mantenimiento preventivo
- Revisar semanalmente `pip list --outdated` y planificar actualizaciones de seguridad.
- Ejecutar `pytest`, `import-linter` y `python manage.py spectacular` en cada merge a `main`.
- Programar limpieza de archivos huerfanos en `media/` comparando con registros `Answer` y ejecutar scripts de depuracion.
- Revisar mensualmente `VisionMonthlyUsage` y ajustar `VISION_MAX_PER_MONTH` o alertas si se detectan picos inesperados.
- Auditar tokens DRF antiguos y cuentas staff inactivas, revocandolos cuando supere el periodo definido por TI.

## Indicadores clave
- MTTR (tiempo medio de resolucion) por severidad y tipo de incidente.
- Porcentaje de incidentes con causa raiz identificada y acciones preventivas implementadas.
- Tendencia de consumo OCR versus limite mensual y su correlacion con fallos de verificacion.
- Numero de regresiones detectadas por pruebas automatizadas posteriores a despliegues.

## Comunicaciones
- Notificar incidentes mayores via correo corporativo y canal en tiempo real (Teams/Slack).
- Mantener calendario compartido de ventanas de mantenimiento (minimo 48 h de aviso).
- Publicar postmortem resumido para incidentes severos, resaltando lecciones aprendidas y cambios permanentes.
