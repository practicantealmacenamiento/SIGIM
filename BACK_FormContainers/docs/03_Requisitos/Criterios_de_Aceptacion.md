# Criterios de Aceptacion

## CA-01 Autenticacion unificada
**Como** operador **quiero** iniciar sesion con mi identificador corporativo **para** acceder a los servicios de SIGIM.
- Dado que envio `identifier` y `password` validos a `POST /api/v1/login`, **entonces** recibo `200 OK` con `token` y estructura `user`.
- Cuando consulto `GET /api/v1/whoami` con el token vigente, **entonces** obtengo mi perfil y cookies CSRF renovadas.
- Si ejecuto `POST /api/v1/logout`, **entonces** el backend revoca el token, borra cookies (`sessionid`, `csrftoken`, `is_staff`, `auth_username`) y retorna `{"detail": "ok"}`.

## CA-02 Creacion y cierre de submissions
**Como** operador **quiero** registrar inspecciones por cuestionario y fase **para** mantener trazabilidad.
- Dado un cuestionario activo, cuando envio `POST /api/v1/submissions/` con `questionnaire_id` y `tipo_fase`, **entonces** se crea la submission con `finalizado=false` y `fecha_cierre=null`.
- Si no proporciono `regulador_id`, **entonces** el backend acepta la creacion y me permite completarlo posteriormente via `PATCH` o durante Guardar y Avanzar.
- Cuando invoco `POST /api/v1/submissions/{id}/finalize/`, **entonces** la submission queda con `finalizado=true` y se establece `fecha_cierre`.

## CA-03 Guardar y Avanzar
**Como** operador **quiero** diligenciar el formulario paso a paso **para** completar la inspeccion sin perder avances.
- Dado que envio `POST /api/v1/cuestionario/guardar_avanzar` con una respuesta valida, **entonces** el servicio persiste la respuesta y retorna la siguiente pregunta en `next_question_id`.
- Si la pregunta permite archivos y adjunto un documento valido, **entonces** el backend lo guarda en `uploads/YYYY/MM/DD/` y retorna la ruta relativa.
- Si el `semantic_tag` es proveedor y envio una lista de proveedores, **entonces** el sistema realiza upsert de filas por nombre y orden de compra sin duplicar respuestas anteriores.
- Cuando regreso a una pregunta anterior con `force_truncate_future=true`, **entonces** las respuestas posteriores se eliminan para garantizar consistencia.

## CA-04 Verificacion OCR
**Como** operador **quiero** validar campos criticos automaticamente **para** minimizar errores manuales.
- Dado que subo una imagen nitida de la placa y ejecuto `POST /api/v1/verificar` con el `question_id` asociado, **entonces** obtengo `valido=true`, `platform` y el valor normalizado en el campo correspondiente.
- Si la imagen es invalida o el OCR falla, **entonces** el servicio devuelve `valido=false` y un mensaje derivado del dominio (`InvalidImageError` o `ExtractionError`) con codigo HTTP apropiado.
- Cada vez que la verificacion se ejecuta, **entonces** se incrementa el contador mensual (`VisionMonthlyUsage`) disponible para auditoria via comando de gestion.

## CA-05 Consulta de historial
**Como** analista **quiero** revisar historiales por regulador **para** auditar avances en fases 1 y 2.
- Cuando invoco `GET /api/v1/historial/reguladores` con filtros de fecha, **entonces** recibo una lista donde cada item contiene `fase1`, `fase2`, `placa_vehiculo`, `contenedor` y `ultima_fecha_cierre`.
- Si una fase no existe para determinado regulador, **entonces** el item omite esa fase manteniendo la otra disponible.
- Cuando ambas fases estan completas, **entonces** la respuesta consolida datos sin duplicados y deriva placa desde respuestas si no esta en la entidad.

## CA-06 Administracion de cuestionarios
**Como** usuario staff **quiero** versionar cuestionarios **para** adaptar el flujo a la operacion.
- Dado que envio `PUT /api/v1/management/questionnaires/{id}/` con preguntas validas, **entonces** el servicio actualiza el cuestionario conservando orden, tipos y `branch_to`.
- Si intento asignar una opcion sin texto o una pregunta sin contenido, **entonces** recibo `400 Bad Request` con detalle explicito (`question_text_blank` o `choice_text_blank`).
- Cuando consulto `GET /api/v1/management/questionnaires/{id}/`, **entonces** obtengo el cuestionario con preguntas, opciones, `semantic_tag` y metadatos listos para el editor.
