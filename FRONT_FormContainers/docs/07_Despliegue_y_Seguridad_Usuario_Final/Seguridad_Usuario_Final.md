# Seguridad para Usuario Final

## Manejo de credenciales
- Acceder a SIGIM siempre mediante HTTPS para evitar exposicion de tokens.
- El token y las cookies se almacenan automaticamente por el navegador; no compartir sesiones ni reutilizar dispositivos sin cerrar sesion.
- El login redirige al home si ya existe sesion activa; cerrar sesion desde el menu principal antes de entregar el equipo a otro operador.

## Buenas practicas de uso
- Validar datos antes de enviarlos. El formulario muestra confirmaciones y estados de guardado; no cerrar la ventana hasta ver el estado `Guardado`.
- Para campos con OCR, revisar manualmente el valor extraido antes de continuar.
- Verificar que las exportaciones CSV se descarguen desde dominios confiables y almacenarlas de acuerdo a las politicas de la organizacion.

## Proteccion de datos personales
- El historial y panel muestran datos sensibles (placas, actores). Utilizar las herramientas solo para fines operativos autorizados.
- No compartir capturas que incluyan informacion personal sin redaccion previa.
- Respetar las politicas de privacidad corporativas y reportar cualquier acceso indebido.

## Gestion de sesiones
- El sistema expira automaticamente tras inactividad prolongada; si ocurre, iniciar sesion nuevamente.
- Al usar dispositivos compartidos, cerrar sesion y limpiar el navegador (cookies/cache) al finalizar el turno.
- Si se detecta comportamiento anomalo (por ejemplo, sesion abierta en otra ubicacion), contactar a soporte para forzar cierre de sesion desde el backend.

## Soporte y asistencia
- Ante dudas o errores visuales, capturar la pantalla y compartir el `error_id` mostrado (si aplica) con la mesa de ayuda.
- Reportar de inmediato cualquier falla de seguridad o vulnerabilidad percibida.

