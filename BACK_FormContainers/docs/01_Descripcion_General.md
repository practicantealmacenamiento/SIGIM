# Descripcion General del Proyecto

SIGIM (Sistema Integrado de Gestion de Ingreso de Mercancia) digitaliza el control de ingreso y salida de vehiculos de carga. El backend, implementado con **Django 5.2** y **Django REST Framework 3.16**, expone una API REST versionada (`/api/v1/`) que centraliza autenticacion, cuestionarios dinamicos, gestion de evidencias, historial logistico y verificaciones asistidas por OCR. El diseno aplica Clean Architecture para mantener la logica de negocio aislada de frameworks y facilitar la evolucion del producto.

## Proposito de la plataforma
- Automatizar la captura y validacion de informacion logisticamente relevante (placa, contenedor, precinto, actores involucrados).
- Asegurar trazabilidad completa de submissions, respuestas, archivos adjuntos y fases del regulador.
- Proveer herramientas administrativas para actualizar cuestionarios, administrar usuarios internos y controlar catalogos maestros.
- Integrar capacidades de reconocimiento optico de caracteres (OCR) con limites mensuales y trazabilidad de uso.

## Capas de la solucion
- **Dominio (`app/domain`)**: entidades inmutables (`entities.py`), reglas (`rules.py`) y puertos (`ports/*`). No depende de Django y modela conceptos como `Submission`, `Question`, `Actor`, `VisionMonthlyUsage` o las excepciones de negocio.
- **Aplicacion (`app/application`)**: casos de uso operativos (`services.py`, `questionnaire.py`, `verification.py`) y administrativos (`services/admin_services.py`). Orquestan repositorios mediante comandos inmutables (`commands.py`) y emiten estructuras de dominio puras.
- **Infraestructura (`app/infrastructure`)**: implementaciones Django de modelos, repositorios y adaptadores externos (`adapters/*`), ademas de la `ServiceFactory` que inyecta dependencias (OCR, almacenamiento, repositorios) y serializadores HTTP.
- **Interfaces (`app/interfaces`)**: vistas REST (`views.py`, `admin_views.py`) y servicios HTTP reutilizables (`http/services.py`) que traducen requests en comandos y respuestas de dominio. Incluye autenticacion unificada, middleware de excepciones y endpoints documentados con drf-spectacular.

## Servicios funcionales clave
- **Autenticacion unificada**: `UnifiedLoginAPIView`, `WhoAmIAPIView` y `UnifiedLogoutAPIView` combinan autenticacion por token y sesion, reutilizando `AuthAPIService` para emitir cookies y payloads consistentes.
- **Cuestionarios dinamicos**: `QuestionnaireListAPIView`, `PrimeraPreguntaAPIView` y `GuardarYAvanzarAPIView` exponen el flujo principal. `QuestionnaireService` soporta ramificacion (`branch_to`), etiquetas semanticas y manejo de bloques de proveedores.
- **Submissions**: `SubmissionViewSet` crea borradores, lista con filtros avanzados, finaliza el flujo, ofrece detalle enriquecido y sincroniza actores asociados mediante `SubmissionService`.
- **Verificacion OCR**: `VerificacionUniversalAPIView` delega en `VerificationService`, que normaliza resultados para placas, contenedores y precintos usando reglas del dominio y el puerto `TextExtractorPort`.
- **Historial logistico**: `HistorialReguladoresAPIView` consume `HistoryService` via `HistoryAPIService` para consolidar fases 1 y 2 por regulador, derivando campos clave cuando la entidad no los persiste.
- **Catalogo y administracion**: `ActorViewSet`, `AdminActorViewSet`, `AdminQuestionnaireViewSet` y `AdminUserViewSet` delegan en los servicios de aplicacion especializados (`application/services/admin_services.py`) a traves de los helpers de `interfaces/http/services.py`, manteniendo las reglas de negocio fuera de las vistas.

## Integraciones y persistencia
- **Base de datos**: en desarrollo se usa SQLite (`dbtest.sqlite3`). En produccion se soportan SQL Server y otros motores configurables via variables de entorno (`DB_ENGINE`, `DATABASE_URL`) sin modificar el dominio.
- **Almacenamiento de archivos**: `DjangoDefaultStorageAdapter` implementa el puerto `FileStorage`, genera rutas seguras (`uploads/YYYY/MM/DD/uuid.ext`) y expone URLs protegidas mediante `MediaProtectedAPIView`.
- **OCR**: `TextExtractorAdapter` prioriza Google Cloud Vision cuando las credenciales estan configuradas, con fallback automatico al mock `DevelopmentTextExtractor`. El consumo se contabiliza en `VisionMonthlyUsage` y puede auditarse via `python manage.py report_vision_usage`.
- **Observabilidad**: `core/settings.py` configura logging estructurado, protecciones CORS/CSRF y el limite `VISION_MAX_PER_MONTH` para OCR. Los servicios HTTP unificados trazan cada request relevante desde `interfaces/http/services.py`.

## Flujo operativo resumido
1. El operador inicia sesion (`POST /api/v1/login`) y el backend entrega token y cookies CSRF.
2. Se crea o reanuda una `Submission` (`POST /api/v1/submissions/`) indicando cuestionario y fase.
3. El flujo Guardar y Avanzar valida la respuesta, gestiona archivos, actualiza actores relacionados y determina la siguiente pregunta.
4. Opcionalmente se ejecutan verificaciones OCR (`POST /api/v1/verificar`) segun el `semantic_tag` de la pregunta.
5. `HistorialReguladoresAPIView` consolida las fases finalizadas y expone la vista consumida por el frontend de panel/historial.
6. Al finalizar el cuestionario, `SubmissionViewSet.finalize` marca el registro como cerrado y lo deja disponible para consultas, reportes y exportaciones CSV.

## Principios de diseno
- Respeto estricto a los contratos de Clean Architecture (ver `pyproject.toml` e import-linter).
- Comandos inmutables para separar datos de orquestacion (`CreateAnswerCommand`, `SaveAndAdvanceCommand`, `FinalizeSubmissionCommand`).
- Traduccion centralizada de excepciones de dominio mediante `DomainExceptionTranslator`, middleware dedicado y helpers en `interfaces/http/services.py`.
- Documentacion automatica de la API con drf-spectacular (`/api/v1/schema`, `/api/v1/docs`).
- Reutilizacion de servicios HTTP para alinear backend y frontend, evitando duplicar logica de validacion en las vistas.

Este documento resume el estado actual del backend de SIGIM y sirve de punto de partida para tareas de soporte, integracion y evolucion tecnica.

