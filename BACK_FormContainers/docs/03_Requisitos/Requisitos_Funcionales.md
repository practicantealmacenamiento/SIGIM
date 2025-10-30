# Requisitos Funcionales

Los requisitos se derivan del comportamiento observado en la capa de interfaces (`app/interfaces`), servicios de aplicacion (`app/application`) y adaptadores de infraestructura (`app/infrastructure`).

## Autenticacion y sesion
- **RF-01**: Permitir autenticacion por usuario, correo o identificador generico y devolver token valido junto con datos del usuario (`UnifiedLoginAPIView` + `AuthAPIService`).
- **RF-02**: Exponer `GET /api/v1/whoami` para recuperar el perfil del usuario autenticado y renovar cookies CSRF (`WhoAmIAPIView`).
- **RF-03**: Proveer `POST /api/v1/logout` que revoque tokens, cierre la sesion y limpie cookies auxiliares (`UnifiedLogoutAPIView`).
- **RF-04**: Aplicar `BearerOrTokenAuthentication` y `IsAuthenticated` sobre todos los endpoints operativos, reservando `AllowAny` únicamente para login.

## Gestion de cuestionarios
- **RF-10**: El staff debe crear, editar, listar y eliminar cuestionarios versionados via `AdminQuestionnaireViewSet`, respetando la validacion de campos requerida por `AdminQuestionnaireService`.
- **RF-11**: Las preguntas deben soportar tipos `text`, `number`, `date`, `choice`, `file`, mantener orden unico dentro del cuestionario y permitir ramificacion mediante `branch_to`.
- **RF-12**: Cada pregunta puede asociarse a un `semantic_tag` canonico (placa, contenedor, precinto, proveedor, etc.) que active reglas especificas en `QuestionnaireService` y `VerificationService`.
- **RF-13**: Debe existir al menos una pregunta activa por cuestionario para que el flujo Guardar y Avanzar funcione; de lo contrario `QuestionnaireService` debe lanzar `EntityNotFoundError`.

## Submissions y flujo Guardar y Avanzar
- **RF-20**: Crear submissions indicando cuestionario, fase (`entrada`, `salida`, `inspeccion`) y opcionalmente `regulador_id`, `placa` y `contenedor` (`SubmissionViewSet.create`).
- **RF-21**: `GuardarYAvanzarAPIView` debe validar existencia de submission y pregunta, persistir texto, opciones, archivos y metadatos, y retornar `SaveAndAdvanceResult` con la siguiente pregunta.
- **RF-22**: Cuando la pregunta usa actores (`semantic_tag` proveedor/transportista/receptor) y se envia `actor_id`, la submission debe actualizar los campos correspondientes mediante `save_partial_updates`.
- **RF-23**: El flujo debe soportar preguntas de proveedor en bloque (`proveedores`), mergeando filas por nombre y orden de compra sin borrar respuestas previas de la misma pregunta.
- **RF-24**: Con `force_truncate_future=True`, las respuestas posteriores a la pregunta actual deben eliminarse para mantener coherencia en la navegacion.
- **RF-25**: `SubmissionViewSet.finalize` debe marcar `finalizado=True`, registrar `fecha_cierre` y evitar nuevas respuestas para la submission.

## Verificacion OCR
- **RF-30**: `POST /api/v1/verificar` debe recibir `question_id` y un archivo de imagen, validar el `semantic_tag` y devolver texto normalizado, valor derivado (placa, contenedor, precinto) y `valido`.
- **RF-31**: Si la imagen es invalida o el OCR falla se debe emitir una `DomainException` traducida a HTTP por `DomainExceptionTranslator` (`VerificationService`).
- **RF-32**: El consumo del servicio debe incrementar el contador mensual (`VisionMonthlyUsage`) para auditar el uso contra `VISION_MAX_PER_MONTH`.

## Catalogos y actores
- **RF-40**: `ActorViewSet` debe listar actores filtrando por tipo, estado y termino de busqueda, limitando resultados segun el parametro `limit`.
- **RF-41**: `AdminActorViewSet` debe permitir CRUD completo, validando tipo y estado mediante `AdminActorService`.
- **RF-42**: Las respuestas del flujo deben almacenar referencias a actores (`actor_id`) y sincronizar campos derivados en la entidad `Submission`.

## Consultas y reportes
- **RF-50**: `SubmissionViewSet.list` debe admitir filtros por estado (`solo_finalizados`), borradores, fase, actores, rango de fechas, placa y contenedor via `SubmissionAPIService`.
- **RF-51**: `SubmissionViewSet.enriched_detail` debe retornar la submission, sus answers y archivos relacionados con serializadores de infraestructura.
- **RF-52**: `HistorialReguladoresAPIView`, a traves de `HistoryAPIService`, debe consolidar fase 1 y 2 usando `HistoryService`, derivando placa desde respuestas cuando no este en la entidad y respetando filtros `fecha_desde`, `fecha_hasta`, `solo_completados`.
- **RF-53**: `QuestionnaireListAPIView` debe listar cuestionarios y opcionalmente incluir preguntas completas (`include_questions=true`).
- **RF-54**: `QuestionDetailAPIView` debe permitir recuperar una pregunta especifica por UUID aplicando validaciones de entrada.

## Administracion interna
- **RF-60**: `AdminUserViewSet` debe permitir listar, crear, editar y eliminar usuarios internos, aplicando cifrado de contrasenia (`make_password`) y control de flags `is_staff`/`is_superuser`.
- **RF-61**: `AdminQuestionnaireViewSet` debe exponer endpoints documentados para actualizaciones completas (PUT) y parciales (PATCH) manteniendo integridad del orden y ramificacion.
- **RF-62**: `PrivateSchemaAPIView` y `PrivateSwaggerUIView` deben exponer la documentacion OpenAPI solo a usuarios con `is_staff=True`.

## Archivos y almacenamiento
- **RF-70**: Las cargas deben almacenarse bajo rutas seguras generadas por `DjangoDefaultStorageAdapter` y referenciarse con path relativo en las entidades `Answer`.
- **RF-71**: `MediaProtectedAPIView` debe validar la ruta solicitada, impedir traversal (`..`) y verificar existencia antes de servir el archivo.
- **RF-72**: Al reemplazar un archivo durante `UpdateAnswerCommand`, el almacenamiento debe eliminar el archivo anterior si `delete_old_file_on_replace=True`.

## Versionado y compatibilidad
- **RF-80**: Todas las rutas deben mantenerse bajo el prefijo `api/v1/` para garantizar compatibilidad con clientes existentes.
- **RF-81**: El backend debe publicar el esquema OpenAPI actualizado (`/api/v1/schema`) tras cada cambio relevante y permitir la exploracion interactiva en `/api/v1/docs`.
