# Arquitectura y Patrones

## Enfoque general
El backend sigue principios de Clean Architecture y arquitectura hexagonal. Las dependencias apuntan siempre hacia el dominio, manteniendo la logica de negocio aislada de frameworks.

```
interfaces  -> application -> domain
           \-> infrastructure -> domain
```

## Capas
- **Domain (`app/domain`)**: entidades inmutables (`entities.py`), reglas (`rules.py`), excepciones y puertos (`repositories.py`, `ports.py`). No depende de Django.
- **Application (`app/application`)**: servicios que orquestan casos de uso (`questionnaire.py`, `services.py`, `verification.py`). Consumen puertos definidos en dominio y exponen comandos/DTOs (`commands.py`).
- **Infrastructure (`app/infrastructure`)**: implementaciones concretas de repositorios, modelos ORM, serializadores externos y adaptadores de almacenamiento.
- **Interfaces (`app/interfaces`)**: vistas DRF, autenticacion, paginacion y traductores de excepciones.

Los contratos de dependencia se validan con import-linter (`pyproject.toml`).

## Patrones aplicados
- **Repositorios**: El dominio define interfaces (`SubmissionRepository`, `AnswerRepository`) y la infraestructura provee implementaciones Django (`DjangoSubmissionRepository`, `DjangoAnswerRepository`).
- **Servicio de aplicacion**: `QuestionnaireService` encapsula el flujo Guardar y Avanzar, coordinando repositorios y almacenamiento.
- **Comando**: `SaveAndAdvanceCommand`, `CreateAnswerCommand`, `UpdateAnswerCommand` encapsulan parametros de casos de uso.
- **Puertos y adaptadores**: `TextExtractorPort` y `FileStorage` permiten cambiar OCR o almacenamiento sin modificar dominio.
- **Factory**: `app/infrastructure/factories.py` construye servicios inyectando dependencias de forma centralizada.
- **DTO manual**: Serializadores en `app/infrastructure/serializers.py` no dependen del ORM para permitir reuso de entidades.

## Consideraciones de diseño
- Separacion de responsabilidades entre validacion (serializadores) y reglas (servicios de dominio).
- Uso extensivo de dataclasses para entidades, garantizando inmutabilidad y metodos de ayuda (`Submission.finalize`).
- Traductor centralizado de excepciones de dominio a HTTP (`DomainExceptionTranslator`) para uniformar respuestas.
- Versionamiento de API mediante `api/v1/` y documentacion automatica con drf-spectacular.
- Navegacion de cuestionarios basada en orden y `branch_to`, administrada desde vistas de staff.
