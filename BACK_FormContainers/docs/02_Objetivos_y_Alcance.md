# Objetivos y Alcance

## Objetivo general
Entregar y mantener un backend robusto para SIGIM que permita registrar, validar y auditar el ingreso de mercancia, asegurando integridad de datos, control de evidencias y trazabilidad completa de actores involucrados.

## Objetivos especificos
- Consolidar autenticacion, autorizacion y session management bajo endpoints REST versionados.
- Permitir la configuracion dinamica de cuestionarios y su ejecucion guiada (Guardar y Avanzar) sin modificar el nucleo de dominio.
- Proveer verificaciones OCR desacopladas que normalicen placas, contenedores y precintos, con seguimiento mensual de consumo (`VisionMonthlyUsage`).
- Facilitar la administracion de catalogos maestros (actores, usuarios, cuestionarios) mediante servicios dedicados para personal staff.
- Generar historiales por regulador y fase, derivando datos criticos desde respuestas cuando la entidad no los conserva explicitamente y exponiendolos de forma unificada para el frontend.
- Centralizar la traduccion entre vistas DRF y casos de uso mediante los servicios HTTP (`app/interfaces/http/services.py`), reduciendo duplicidad de validaciones.
- Exponer evidencias y archivos solo a usuarios autenticados mediante endpoints protegidos.

## Alcance funcional
- API REST autenticada bajo `api/v1/` con autenticacion unificada (token y sesion) y documentacion via drf-spectacular.
- Flujos de cuestionario: obtencion de la primera pregunta, Guardar y Avanzar, finalizacion de submissions y detalle enriquecido con respuestas.
- Servicios de verificacion OCR que enrutan automaticamente segun el `semantic_tag` de la pregunta.
- Listados de historial, catalogo de actores, administracion de cuestionarios, usuarios internos y actores por medio de servicios HTTP reutilizables.
- Reporte del uso mensual de OCR mediante comando `python manage.py report_vision_usage`.

## Fuera de alcance
- Interfaces graficas de usuario y experiencias offline (se atienden en el frontend).
- Reporteria avanzada o tableros BI fuera de los endpoints disponibles.
- Automatizacion de infraestructura cloud o pipelines CI/CD (requiere herramientas externas).
- Gestion de integraciones propietarias adicionales (e.g. ERP, WMS) que no usen los contratos existentes.

## Indicadores de exito
- Ejecucion satisfactoria de los requisitos funcionales y pruebas automatizadas (`pytest`, `import-linter`).
- Latencia promedio inferior a dos segundos en operaciones CRUD de submissions y verificacion OCR menor a tres segundos bajo carga nominal.
- Capacidad de publicar cambios en cuestionarios o reglas de negocio sin alterar capas inferiores del diseño.
- Seguimiento consistente del consumo OCR frente al limite `VISION_MAX_PER_MONTH` y ausencia de archivos huerfanos en almacenamiento.
