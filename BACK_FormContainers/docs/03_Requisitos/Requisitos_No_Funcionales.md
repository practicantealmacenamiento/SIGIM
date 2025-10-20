# Requisitos No Funcionales

## Seguridad
- RNF-01: Mantener claves y configuraciones sensibles en variables de entorno (`.env`), nunca en el repositorio.
- RNF-02: Forzar autenticacion en endpoints protegidos usando token o cookies de sesion con CSRF habilitado (`core/settings.py`).
- RNF-03: Servir archivos de evidencia unicamente a usuarios autenticados y validar rutas para evitar traversal (`MediaProtectedAPIView`).
- RNF-04: En produccion, configurar `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE` y `SECURE_PROXY_SSL_HEADER` segun el entorno.

## Rendimiento y escalabilidad
- RNF-10: Las operaciones frecuentes sobre submissions deben ejecutarse en menos de dos segundos con la carga esperada.
- RNF-11: Los repositorios deben usar consultas selectivas y `prefetch_related` para evitar n+1 (ver `DjangoSubmissionRepository`).
- RNF-12: El almacenamiento de archivos debe realizarse en streaming sin cargar el archivo completo a memoria (`DjangoDefaultStorageAdapter`).
- RNF-13: Redis y Celery deben estar disponibles cuando se ejecuten tareas asincronas o se requiera escalabilidad horizontal.

## Calidad y mantenibilidad
- RNF-20: La estructura de modulos debe cumplir los contratos de import-linter definidos en `pyproject.toml`.
- RNF-21: Las reglas de negocio deben permanecer en el dominio y los servicios de aplicacion, evitando dependencias del framework.
- RNF-22: Los errores de dominio deben traducirse a respuestas HTTP coherentes utilizando `DomainExceptionTranslator`.
- RNF-23: Las pruebas unitarias deben cubrir servicios de dominio y casos de uso (`app/tests`).

## Observabilidad y auditoria
- RNF-30: Configurar logging a nivel `INFO` en produccion y `DEBUG` en desarrollo (`core/settings.py`).
- RNF-31: Registrar eventos relevantes (login, creacion de submissions, errores de OCR) en la salida estandar o sistema de logs centralizado.
- RNF-32: Mantener timestamps (`fecha_creacion`, `fecha_cierre`, `timestamp`) para auditoria.

## Disponibilidad y recuperacion
- RNF-40: El sistema debe soportar reinicios controlados sin perdida de datos gracias a la persistencia en base de datos.
- RNF-41: Las tareas que dependen de servicios externos (OCR, storage) deben fallar de forma controlada y registrarse para reintentos manuales.

## Compatibilidad
- RNF-50: El backend debe operar con Python 3.12 y Django 5.2, segun `Dockerfile` y `requirements.txt`.
- RNF-51: Debe soportar despliegues en contenedores Docker y entornos virtuales Python equivalentes.
