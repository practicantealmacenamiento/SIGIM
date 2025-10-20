# Descripcion General del Proyecto

El backend **Formulario IA** provee servicios para el registro y control logistico de vehiculos de carga. La aplicacion expone una API REST construida con Django y Django REST Framework que permite a los usuarios autenticados diligenciar cuestionarios configurables, adjuntar evidencia (texto, imagen o PDF), validar informacion mediante OCR y consultar historiales por regulador. La implementacion adopta arquitectura limpia con capas bien definidas (`domain`, `application`, `infrastructure`, `interfaces`), lo que facilita el mantenimiento y la extensibilidad del producto.

## Proposito de la plataforma
- Digitalizar el flujo de ingreso y salida de vehiculos usando cuestionarios dinamicos.
- Garantizar trazabilidad de respuestas, archivos y actores involucrados (proveedor, transportista, receptor).
- Proporcionar herramientas de verificacion automatica (OCR) para reducir errores en campos criticos como placa, contenedor y precinto.
- Ofrecer capacidades administrativas para gestionar cuestionarios, usuarios internos y catalogos maestros.

## Componentes funcionales clave
- **Autenticacion unificada** (`UnifiedLoginAPIView` en `app/interfaces/views.py`) que acepta usuario o correo y entrega token o sesion.
- **Cuestionarios dinamicos** administrados en `AdminQuestionnaireViewSet`, con soporte para preguntas ramificadas y opciones condicionadas.
- **Submissions**: ciclo completo de creacion, guardado incremental (`GuardarYAvanzarAPIView`) y finalizacion de las respuestas.
- **Catalogo de actores** (`ActorViewSet` y `AdminActorViewSet`) para enlazar proveedores, transportistas y receptores a cada registro.
- **Verificacion OCR** mediante `VerificationService` y el puerto `TextExtractorPort` para validar documentos visuales.
- **Historial logistico** que agrupa fases por regulador y extrae datos resumidos (`HistoryService`).
- **Distribucion de archivos protegidos** alojados en `media/` y servidos de forma autenticada (`MediaProtectedAPIView`).

## Integraciones y dependencias
- Base de datos SQLite en desarrollo con posibilidad de migrar a Postgres sin cambios en dominio.
- Redis opcional para tareas Celery (definido en `docker-compose.yml`).
- Servicio OCR desacoplado; puede conectarse con Google Cloud Vision cuando se proveen credenciales.
- Almacenamiento de archivos delegado al adaptador `DjangoDefaultStorageAdapter`.

## Perfiles de usuario
- **Operador autenticado**: consume los cuestionarios, guarda respuestas y consulta historial.
- **Staff / Administrador**: accede a endpoints `/management/` para manejar cuestionarios, usuarios y actores; puede revisar la documentacion privada (`/api/docs`).

## Flujo operativo resumido
1. El usuario inicia sesion y obtiene token o cookies de sesion.
2. Crea o reanuda un `submission` seleccionando el cuestionario correspondiente.
3. Para cada pregunta se ejecuta Guardar y Avanzar, que valida la respuesta, almacena archivos y controla la navegacion.
4. El proceso puede invocar la verificacion OCR para validar campos criticos.
5. Al finalizar, el `submission` se marca como finalizado y queda disponible en el historial y los reportes.

## Principios de diseno
- Clean Architecture con limites de dependencia estrictos (ver `pyproject.toml`).
- Uso intensivo de servicios de dominio (`app/domain`) para encapsular reglas.
- Validacion defensiva y traduccion de excepciones de dominio a respuestas HTTP consistentes (`app/interfaces/exception_handlers.py`).
- Documentacion automatica con drf-spectacular y versionamiento de rutas bajo `api/v1/`.

Esta documentacion sirve como punto de partida para comprender el comportamiento global del backend y orientar decisiones de mantenimiento, integracion y despliegue.
