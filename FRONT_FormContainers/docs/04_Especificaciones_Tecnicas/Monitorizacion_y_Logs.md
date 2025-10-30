# Monitorizacion y Logs

## Fuentes de observabilidad
- **Console logging**: los clientes HTTP (`lib/http.ts`, `lib/api.*.ts`) lanzan errores enriquecidos con `status`, `data` y `url`. Habilita `NEXT_PUBLIC_AUTH_DEBUG=1` para rastrear bootstrap de sesion.
- **Reportes en UI**: componentes muestran estados vacios y mensajes de error derivados de los normalizadores (`normalizeApiError`, `pickErrorMessage`).
- **Navegador**: usa DevTools (Network, Performance) para medir latencia de `guardarYAvanzar`, `verificarImagen` y `fetchHistorial`.
- **Herramientas externas**: integra Sentry, Datadog RUM o Google Analytics para capturar errores en produccion y medir conversiones (no incluido por defecto).

## Eventos a registrar
- Inicio/cierre de sesion, incluidos errores de credenciales.
- Guardado de preguntas, respuestas con OCR y finalizacion de submissions.
- Exportaciones CSV y errores asociados (ej. filtros sin resultados).
- Acciones administrativas (creacion/edicion de cuestionarios, actores y usuarios).

## Indicadores sugeridos
- Latencia promedio de `guardarYAvanzar` y `verificarImagen`.
- Numero de drafts recuperados vs. enviados (indicador de continuidad).
- Errores 4xx/5xx mostrados en UI (conteo diario).
- Cantidad de exportaciones CSV y creaciones de fase 2 desde la vista panel.

## Alertas y dashboards
- Configura alertas en la herramienta de monitoreo cuando la tasa de errores supere un umbral definido (ej. >5% durante 10 minutos).
- Monitorea tiempos de carga inicial (`/login`, `/formulario`) y CLS/FID si el proyecto adopta Core Web Vitals.
- Registra en logs la version desplegada (tag) para correlacionar incidentes con builds especificas.

## Buenas practicas
- Evita loguear datos sensibles (documentos, tokens) en consola o herramientas externas.
- Limpia `console.log` temporales antes de publicar una release (excepcion: `NEXT_PUBLIC_AUTH_DEBUG`).
- Documenta en el runbook de soporte como acceder a la herramienta de monitoreo y que paneles consultar.

