# Criterios de Aceptacion

## CA-01 Autenticacion
**Como** operador **quiero** iniciar sesion en SIGIM **para** acceder a los modulos protegidos.
- Dado que envio credenciales validas en `/login`, cuando presiono "Ingresar" entonces `AuthProvider` guarda el token y redirige a `/`.
- Cuando la pagina se recarga, `AuthProvider` ejecuta `whoami` y mantiene el estado autenticado sin solicitar credenciales nuevamente.
- Si el middleware detecta ausencia de sesion, debe redirigirme a `/login` conservando `?next=` con la ruta solicitada.

## CA-02 Formulario Guardar y Avanzar
**Como** operador **quiero** completar el cuestionario **para** registrar la inspeccion.
- Dado un `questionnaire_id` valido, cuando accedo a `/formulario` entonces veo la primera pregunta con los componentes de entrada correspondientes.
- Si adjunto archivos o selecciono actores, la UI debe marcar la pregunta como guardada tras recibir respuesta exitosa del backend.
- Si cierro la pestaña con preguntas pendientes, al volver se me debe ofrecer reanudar el borrador guardado.
- Al finalizar el cuestionario, el sistema muestra un resumen y bloquea acciones adicionales hasta iniciar una nueva submission.

## CA-03 Verificacion OCR
**Como** operador **quiero** validar datos por OCR **para** reducir errores manuales.
- Cuando subo una imagen en una pregunta con `semantic_tag` compatible, el sistema muestra el resultado de OCR y autocompleta el campo.
- Si el OCR falla, debo recibir un mensaje legible y la posibilidad de reintentar el proceso.
- El valor autocompletado puede editarse manualmente antes de guardar.

## CA-04 Historial y exportacion
**Como** analista **quiero** filtrar y exportar el historial **para** analizar tendencias.
- Al ingresar a `/historial`, con filtros por fecha/placa, debo ver resultados deduplicados por regulador con fases 1 y 2 agrupadas.
- Cuando hago clic en "Exportar CSV", el navegador debe descargar un archivo con los campos mostrados en la vista.
- Si no existen registros para los filtros aplicados, la UI debe mostrar estado vacio y no generar CSV.

## CA-05 Panel de fase 2
**Como** staff **quiero** continuar la fase 2 desde la fase 1 **para** evitar reprocesos.
- En `/panel` debo poder buscar submissions finalizadas de fase 1 por placa, ver datos relevantes y un boton "Iniciar Fase 2".
- Si ya existe una fase 2, el sistema muestra modal para continuar el registro existente.
- Al crear una nueva fase 2 se debe redirigir a `/formulario` con el `questionnaire_id` y `submission_id` adecuados.

## CA-06 Administracion
**Como** staff **quiero** administrar catalogos y cuestionarios **para** mantener la operacion.
- Los listados deben paginarse y permitir busqueda basica, mostrando mensajes de exito/error derivados de `api.admin.ts`.
- Al crear o actualizar un cuestionario se debe mostrar el formulario con preguntas, opciones y etiquetas; los cambios deben reflejarse al recargar la pagina.
- Las acciones deben respetar el rol `is_staff`; si pierdo permisos, debo ser redirigido al inicio.

