# Requisitos de Seguridad para Usuario Final

## Proteccion de credenciales
- El front debe enviar contrasenias exclusivamente mediante HTTPS.
- Almacenar tokens en memoria (no en localStorage) y usar encabezado `Authorization`.
- Rotar tokens mediante logout automatico tras 24 horas de inactividad.

## Manejo de sesion
- Consumir `whoami` al iniciar la aplicacion para validar vigencia de la sesion.
- Forzar cierre de sesion en el navegador cuando `POST /api/v1/logout` responda 200.
- Implementar renovacion de CSRF cuando cambie la cookie `csrftoken`.

## Politicas de datos
- Mostrar unicamente informacion necesaria en la UI (ej. enmascarar documentos de actores).
- Informar al usuario cuando se almacene una imagen o documento (cumplimiento de GDPR/LGPD si aplica).
- Ofrecer mecanismos de correccion de datos en caso de errores (contacto con la mesa de ayuda).

## Buenas practicas de interfaz
- Validar campos en el cliente antes de invocar Guardar y Avanzar para reducir reintentos.
- Integrar capturas de errores del backend en la UI mostrando mensajes amigables.
- Ofrecer indicadores de carga durante operaciones con archivos u OCR.

## Cumplimiento normativo
- Registrar consentimiento del usuario para uso de datos de placa y documentos.
- Asegurar que los operadores conozcan la politica de privacidad y tratamiento de datos.
- Disponer de canales de soporte para solicitudes de eliminacion o actualizacion de informacion personal.
