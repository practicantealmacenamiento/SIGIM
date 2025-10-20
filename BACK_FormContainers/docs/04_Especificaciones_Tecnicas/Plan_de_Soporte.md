# Plan de Soporte

## Objetivos
- Garantizar operacion estable del backend en horarios criticos de cargue y descargue.
- Detectar y resolver incidentes antes de que impacten la operacion logistica.
- Coordinar mantenimientos preventivos y evolutivos de forma planificada.

## Niveles de soporte
- **Nivel 1 (Mesa de ayuda)**: recibe alertas de monitoreo, valida disponibilidad del servicio (`/api/v1/whoami`) y escala segun severidad.
- **Nivel 2 (Equipo backend)**: analiza logs de Django, revisa tareas en cola, restaura servicios Docker o workers Celery, ajusta configuraciones.
- **Nivel 3 (Proveedores externos)**: atiende fallas en OCR (Google Vision) o almacenamiento externo. Se activa solo tras descartar causas internas.

## Flujos de atencion
1. Registro del incidente en la herramienta ITSM (ej. Jira Service Management) con datos minimos: timestamp, endpoint afectado, token afectado.
2. Mesa de ayuda ejecuta script de diagnostico: `python manage.py check` y prueba de ping al worker Celery.
3. Si el incidente es funcional (validaciones, reglas de negocio) se asigna a analistas para reproduccion con datos de ejemplo.
4. Tras la solucion, el ticket se cierra adjuntando evidencia (logs, capturas) y actualizando la base de conocimiento.

## Mantenimiento preventivo
- Revisar semanalmente dependencias criticas con `pip list --outdated`.
- Ejecutar `pytest` e import-linter en cada merge a la rama principal.
- Programar tareas de limpieza de archivos huérfanos en `media/` (scripts que consulten `Answer` sin referencia).
- Validar que los tokens inactivos se roten segun politicas de TI (limpieza de `Token` DRF).

## Indicadores de soporte
- Tiempo medio de resolucion por severidad.
- Porcentaje de incidentes cerrados con causa raiz identificada.
- Numero de regresiones detectadas en pruebas automatizadas tras despliegues.

## Comunicaciones
- Notificaciones de incidentes mayores via correo y canal de alertas en tiempo real (Teams/Slack).
- Calendario compartido de ventanas de mantenimiento con minimo 48 horas de anticipacion.
