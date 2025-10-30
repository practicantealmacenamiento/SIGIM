# Arquitectura y Patrones

## Enfoque general
SIGIM aplica Clean Architecture/Hexagonal: el dominio define la logica y contratos, mientras que aplicacion orquesta casos de uso, infraestructura implementa adaptadores y interfaces expone la API. Las dependencias siempre apuntan hacia el dominio y los contratos se validan con import-linter.

```
interfaces -> application -> domain
interfaces -> infrastructure -> domain
application -> domain
infrastructure -> domain
```

## Capas y responsabilidades
- **Dominio (`app/domain`)**
  - Entidades inmutables (`entities.py`): `Question`, `Questionnaire`, `Submission`, `Answer`, `Actor`, etc.
  - Reglas de negocio (`rules.py`): normalizacion de placa, validacion de precintos, semantica de preguntas.
  - Excepciones (`exceptions.py`) y puertos (`ports/*`).
- **Aplicacion (`app/application`)**
  - Casos de uso operativos: `services.py` (Submission/History/Media), `questionnaire.py` (Guardar y Avanzar), `verification.py` (OCR), `commands.py` (DTO inmutables).
  - Casos de uso administrativos: `services/admin_services.py` (usuarios, actores, cuestionarios).
  - No conocen Django ni el ORM; interactuan via puertos inyectados por la `ServiceFactory`.
- **Infraestructura (`app/infrastructure`)**
  - Modelos ORM y migraciones alineadas con el historico del proyecto.
  - Repositorios Django (`adapters/repositories/*`) que implementan los puertos del dominio.
  - Adaptadores externos (`adapters/external_adapters/*`): `TextExtractorAdapter`, `DevelopmentTextExtractor`, `DjangoDefaultStorageAdapter`.
  - `factories.py` crea instancias compartidas, resuelve adaptadores (OCR, almacenamiento) y centraliza configuraciones de ambiente.
  - Serializadores (`serializers.py`) mapean entidades a payloads HTTP.
  - Contadores de uso OCR (`usage_limits.py`) y comandos de soporte (`management/commands/report_vision_usage.py`).
- **Interfaces (`app/interfaces`)**
  - Vistas REST (`views.py`, `admin_views.py`) y servicios HTTP (`http/services.py`) que construyen comandos, validan input y formatean respuestas.
  - Autenticacion unificada (`auth.py`) y manejo de errores (`exception_handlers.py`) mediante `DomainExceptionTranslator`.
  - `InterfaceServices` coordina la reutilizacion de `QuestionnaireService`, `SubmissionService`, `HistoryService` y `VerificationService` en las vistas.

## Patrones destacados
- **Comandos inmutables**: `CreateAnswerCommand`, `UpdateAnswerCommand`, `SaveAndAdvanceCommand` encapsulan parametros y diferencian `UNSET` de `None`.
- **Servicio de aplicacion**: `QuestionnaireService` orquesta el flujo Guardar y Avanzar, soporta ramificacion por `branch_to`, adjuntos, actualizacion de actores y merge de proveedores.
- **Repositorios y puertos**: el dominio define contratos (`SubmissionRepository`, `AnswerRepository`, `TextExtractorPort`, `FileStorage`). La infraestructura los implementa con Django o adaptadores externos.
- **Factory centralizada**: `ServiceFactory` instancia repositorios, servicios y adaptadores, favoreciendo reutilizacion y pruebas (incluye helpers `with_text_extractor`, `with_file_storage`).
- **Servicios HTTP reutilizables**: `interfaces/http/services.py` concentra logica de validacion y serializacion para vistas REST, reduciendo duplicidad y facilitando pruebas.
- **Traduccion de excepciones**: `DomainExceptionTranslator`, `DomainExceptionMiddleware` y `custom_exception_handler` garantizan payloads consistentes (`error_id`, `type`, `details`).
- **DTO/Serializadores**: `infrastructure/serializers.py` mapea entidades a respuestas sin acoplarse al ORM.
- **Uso mensual OCR**: `VisionMonthlyUsage` registra consumo y soporta auditoria via comandos.

## Consideraciones de diseno
- Navegacion de cuestionarios basada en orden y ramificacion condicional (`branch_to`), administrada por servicios y validada en los casos administrativos (`AdminQuestionnaireService`).
- Representacion de proveedores en Guardar y Avanzar mediante colecciones tabulares, garantizando inmutabilidad y merge controlado.
- Actualizacion incremental de submissions (`save_partial_updates`) para evitar sobreescrituras masivas.
- Versionamiento de API bajo `api/v1/` y documentacion automatica con drf-spectacular.
- Pruebas en `app/tests` cubren entidades, reglas de dominio, flujo de cuestionario, historial logistico y limites de arquitectura (`test_architecture_boundaries.py`).

