# Requisitos No Funcionales

## Seguridad
- **RNF-01**: Gestionar claves, tokens y credenciales (DB, OCR, API_SECRET_TOKEN) mediante variables de entorno cargadas por `django-environ`.
- **RNF-02**: Exigir autenticacion en endpoints protegidos utilizando token DRF o sesion con CSRF, manteniendo `CSRF_COOKIE_SECURE` y `SESSION_COOKIE_SECURE` activos en produccion.
- **RNF-03**: Validar rutas de archivos antes de servirlos, evitando traversal (`MediaProtectedAPIView`) y eliminando archivos al limpiar respuestas (`DjangoDefaultStorageAdapter.delete`).
- **RNF-04**: Restringir acceso a endpoints administrativos mediante `IsAdminUser` y considerar `TokenRequiredForWrite` para integraciones de sistema a sistema.

## Rendimiento y escalabilidad
- **RNF-10**: Las operaciones de submission y Guardar y Avanzar deben responder en menos de 2 s bajo la carga nominal definida para SIGIM.
- **RNF-11**: Los repositorios Django deben usar `select_related` y `prefetch_related` para evitar consultas N+1 (`DjangoSubmissionRepository`).
- **RNF-12**: Las cargas de archivos deben procesarse en streaming para no superar `DATA_UPLOAD_MAX_MEMORY_SIZE` (32 MB).
- **RNF-13**: El limite `VISION_MAX_PER_MONTH` debe monitorearse y registrar consumo en `VisionMonthlyUsage`. Al excederlo, la capa de aplicacion debe impedir nuevas verificaciones hasta el siguiente mes.

## Calidad y mantenibilidad
- **RNF-20**: La estructura modular debe cumplir los contratos definidos en `pyproject.toml` validados por import-linter.
- **RNF-21**: Toda la logica de negocio debe residir en dominio o aplicacion; las vistas solo pueden orquestar servicios y serializadores.
- **RNF-22**: Las excepciones de dominio deben traducirse a HTTP mediante `DomainExceptionTranslator`, garantizando respuestas consistentes.
- **RNF-23**: Mantener pruebas unitarias y de integracion (`pytest`) cubriendo servicios de aplicacion, reglas de dominio y adaptadores criticos.

## Observabilidad y auditoria
- **RNF-30**: Configurar logging estructurado a nivel `INFO` en produccion y `DEBUG` en ambientes de desarrollo (`core/settings.py`).
- **RNF-31**: Registrar eventos relevantes: login/logout, creacion/finalizacion de submissions, errores de OCR y excepciones no controladas.
- **RNF-32**: Ejecutar el comando `python manage.py report_vision_usage` para auditar consumo de OCR y contrastarlo con alertas operativas.
- **RNF-33**: Conservar timestamps (`created_at`, `fecha_cierre`, `timestamp`) y campos de auditoria (`created_by`, `user`) para trazabilidad forense.

## Disponibilidad y recuperacion
- **RNF-40**: Asegurar que el backend se recupere ante reinicios controlados manteniendo el estado en la base de datos y el almacenamiento externo.
- **RNF-41**: Las fallas de servicios externos (OCR, storage) deben propagarse como excepciones de dominio manejadas para permitir reintentos manuales.
- **RNF-42**: Mantener respaldos periodicos de base de datos y media; documentar procedimientos de rollback en el plan de soporte.

## Compatibilidad y despliegue
- **RNF-50**: Operar con Python 3.12, Django 5.2 y DRF 3.16, conforme a `Dockerfile` y `requirements.txt`.
- **RNF-51**: Soportar ejecucion en contenedores Docker y entornos virtuales equivalentes sin alterar el comportamiento funcional.
- **RNF-52**: Garantizar que los endpoints actuales permanezcan compatibles mientras el prefijo `api/v1/` siga vigente.
