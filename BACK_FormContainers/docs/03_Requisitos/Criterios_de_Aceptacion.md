# Criterios de Aceptacion

## CA-01 Autenticacion unificada
**Como** operador autenticado **quiero** iniciar sesion con usuario o correo **para** acceder a la API.
- Dado que proveo `identifier` y `password` validos, cuando invoco `POST /api/v1/login` entonces recibo `token` y `user`.
- Cuando consulto `GET /api/v1/whoami` con token valido entonces obtengo mi perfil basico.
- Si ejecuto `POST /api/v1/logout`, las cookies `sessionid`, `csrftoken`, `is_staff` y `auth_username` deben eliminarse.

## CA-02 Creacion de submissions
**Como** operador **quiero** iniciar un registro de cuestionario **para** capturar informacion de vehiculos.
- Dado un cuestionario activo, cuando envio `POST /api/v1/submissions/` con `questionnaire_id` y `tipo_fase`, entonces el sistema crea la submission y retorna su identificador.
- Si omito `regulador_id`, el sistema debe aceptarlo y permitir completarlo posteriormente.
- Cuando la submission se crea, queda con `finalizado = false` y `fecha_cierre = null`.

## CA-03 Guardar y avanzar
**Como** operador **quiero** diligenciar el formulario paso a paso **para** completar la inspeccion.
- Dado que envio `POST /api/v1/cuestionario/guardar_avanzar` con una respuesta valida, entonces la respuesta se persiste y el payload retorna la siguiente pregunta.
- Si la pregunta acepta archivos, al cargar un archivo valido se debe guardar en `media/uploads/...` y retornarse la ruta relativa.
- Si regreso a una pregunta anterior con `force_truncate_future = true`, las respuestas posteriores se eliminan.
- Cuando se trata de la ultima pregunta y selecciono `finalizar = true`, la submission queda marcada como finalizada.

## CA-04 Verificacion OCR
**Como** operador **quiero** validar automaticamente campos criticos **para** reducir errores.
- Dado que adjunto una imagen legible de la placa, cuando llamo `POST /api/v1/verificar` con el `question_id` correspondiente entonces obtengo `valido = true` y el valor normalizado.
- Si la imagen es invalida o el OCR falla, la respuesta contiene `valido = false` y un mensaje descriptivo traducido desde el dominio.

## CA-05 Consulta de historial
**Como** regulador operador **quiero** consultar el historial de vehiculos **para** auditar fases anteriores.
- Cuando invoco `GET /api/v1/historial/reguladores` con filtros de fecha, recibo una lista donde cada item incluye `fase1`, `fase2`, `placa_vehiculo`, `contenedor` y `ultima_fecha_cierre`.
- Si no existen registros para un regulador dado, el item correspondiente omite la fase ausente.
- Cuando ambas fases estan completas, el item combina los datos sin duplicados.

## CA-06 Administracion de cuestionarios
**Como** usuario staff **quiero** configurar nuevas versiones de cuestionarios **para** adaptarlos a la operacion.
- Dado que envio `PUT /api/v1/management/questionnaires/{id}/` con preguntas validas, el sistema actualiza el cuestionario respetando el orden y las opciones ramificadas.
- Si intento eliminar una pregunta en uso, el sistema debe permitirlo siempre que no deje el cuestionario sin preguntas.
- Cuando consulto `GET /api/v1/management/questionnaires/{id}/`, la respuesta incluye preguntas, opciones y metadatos listos para el editor.
