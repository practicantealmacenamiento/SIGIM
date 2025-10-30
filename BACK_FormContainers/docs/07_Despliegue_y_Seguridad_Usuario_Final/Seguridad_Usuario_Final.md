# Requisitos de Seguridad para Usuario Final

## Proteccion de credenciales
- Consumir siempre la API mediante HTTPS; nunca exponer credenciales por canales inseguros.
- Almacenar tokens en memoria volátil (state managers, React context) y enviarlos en el header `Authorization: Token/Bearer`.
- Forzar logout automatico tras 24 h de inactividad o cuando `POST /api/v1/logout` devuelva `200 OK`.
- Rotar contrasenas segun politicas corporativas y evitar reutilizacion entre sistemas.

## Manejo de sesion
- Ejecutar `GET /api/v1/whoami` al iniciar la aplicacion para validar la sesion y obtener nuevo CSRF.
- Cuando el backend responda `401 Unauthorized`, limpiar el estado local y redirigir a login.
- Mantener sincronizadas las cookies `csrftoken` e `is_staff`; si cambian, refrescar permisos en la UI.

## Tratamiento de datos
- Mostrar solo informacion necesaria (placa, contenedor, actores); enmascarar documentos sensibles.
- Notificar al usuario cuando se sube evidencia (imagen/documento) y obtener consentimiento segun la politica de datos.
- Implementar mecanismos para corregir o solicitar eliminacion de datos (mesa de ayuda SIGIM).

## Interfaz y experiencia segura
- Validar datos en el cliente antes de enviar Guardar y Avanzar para reducir reintentos.
- Gestionar errores del backend mostrando mensajes amigables y referencia al `error_id` cuando exista.
- Proveer indicadores de progreso durante cargas de archivos o verificaciones OCR para evitar abandonos.
- Consumir archivos protegidos mediante el endpoint `/api/v1/secure-media/` sin exponer rutas directas.

## Cumplimiento y privacidad
- Mantener registro de consentimiento y finalidades de uso de datos de vehiculos y actores.
- Alinear mensajes y flujos de la UI con la politica de privacidad corporativa.
- Disponer de canal de soporte para solicitudes de habeas data (actualizacion o borrado de informacion).
