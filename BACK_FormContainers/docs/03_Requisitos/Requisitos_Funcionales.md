# Requisitos Funcionales

Los siguientes requisitos derivan del comportamiento implementado en la capa de interfaces (`app/interfaces`), servicios de aplicacion (`app/application`) y repositorios (`app/infrastructure`).

## Autenticacion y sesion
- RF-01: El sistema debe permitir autenticarse usando usuario o correo y devolver un token valido (`UnifiedLoginAPIView`).
- RF-02: La API debe exponer un endpoint `whoami` que retorne los datos basicos del usuario autenticado.
- RF-03: Debe existir un endpoint de cierre de sesion que revoque cookies y token (`UnifiedLogoutAPIView`).
- RF-04: Las vistas privadas (`/api/v1/*`) deben forzar autenticacion mediante `BearerOrTokenAuthentication` o sesion.

## Gestion de cuestionarios
- RF-10: Los administradores deben poder crear, consultar, actualizar y eliminar cuestionarios versionados (`AdminQuestionnaireViewSet`).
- RF-11: Las preguntas deben soportar tipos `text`, `number`, `date`, `choice` y `file`, con orden y ramificacion opcional.
- RF-12: Cada pregunta puede asociarse a etiquetas semanticas (`semantic_tag`) para aplicar reglas de negocio especiales.
- RF-13: Se debe validar que al menos una pregunta exista por cuestionario antes de publicarlo (`QuestionnaireService`).

## Flujo Guardar y Avanzar
- RF-20: El sistema debe crear submissions vacias segun cuestionario, fase (entrada/salida) y regulador (`SubmissionViewSet.create`).
- RF-21: El caso de uso `save_and_advance` debe persistir texto, opciones, archivos y metadatos asociados a la pregunta actual.
- RF-22: Para preguntas con actores (proveedor, transportista, receptor) se debe enlazar el `actor_id` recibido y evitar duplicados.
- RF-23: La navegacion debe eliminar respuestas posteriores cuando el usuario retrocede y fuerza `force_truncate_future`.
- RF-24: Al finalizar el flujo, el submission debe marcarse como finalizado y registrar `fecha_cierre` (`SubmissionViewSet.finalize`).

## Verificacion OCR
- RF-30: Debe existir un endpoint `/api/v1/verificar` que reciba una imagen y retorne la verificacion segun `semantic_tag`.
- RF-31: El servicio de verificacion debe soportar placa, contenedor y precinto, devolviendo indicadores `valido` y datos normalizados.
- RF-32: Si el OCR falla o la imagen es invalida se debe retornar un error manejado de dominio (`VerificationService`).

## Catalogos y actores
- RF-40: Los usuarios autenticados deben poder consultar el catalogo de actores con filtros por tipo, texto y estado (`ActorViewSet`).
- RF-41: Los roles de staff deben administrar actores mediante CRUD completo (`AdminActorViewSet`).
- RF-42: Las respuestas deben poder almacenar referencias a actores seleccionados durante el flujo Guardar y Avanzar.

## Submissions y consultas
- RF-50: Debe existir listado paginado de submissions con filtros por estado, fase, regulador, fechas y placa (`SubmissionViewSet.list`).
- RF-51: El detalle enriquecido debe incluir answers, archivos y datos derivados (`SubmissionViewSet.enriched_detail`).
- RF-52: Los usuarios deben acceder al historial por regulador, agrupando fase 1 y fase 2 en un mismo item (`HistorialReguladoresAPIView`).
- RF-53: El API debe devolver la lista de cuestionarios activos para poblar selectores (`QuestionnaireListAPIView`).
- RF-54: El detalle de una pregunta debe poder consultarse por identificador (`QuestionDetailAPIView`).

## Administracion de usuarios internos
- RF-60: El personal de staff debe poder listar, crear y actualizar usuarios internos con control de contrasenia (`AdminUserViewSet`).
- RF-61: La creacion de usuarios debe forzar la generacion de contrasenia cifrada y permitir asignar roles de staff o superusuario.

## Archivos y almacenamiento
- RF-70: Los archivos cargados deben guardarse en rutas seguras bajo `uploads/YYYY/MM/DD/` (`DjangoDefaultStorageAdapter`).
- RF-71: Debe existir un endpoint protegido que sirva archivos de media solo a usuarios autenticados (`MediaProtectedAPIView`).
- RF-72: Al reemplazar o eliminar respuestas con archivos debe intentar borrarse el archivo anterior para evitar residuos.

## Documentacion y versionado
- RF-80: El API debe exponer un esquema OpenAPI privado accesible para personal staff (`PrivateSchemaAPIView`, `PrivateSwaggerUIView`).
- RF-81: Todas las rutas publicas deben versionarse bajo el prefijo `api/v1/`.
