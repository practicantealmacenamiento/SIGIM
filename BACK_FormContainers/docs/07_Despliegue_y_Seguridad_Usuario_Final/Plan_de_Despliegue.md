# Plan de Despliegue

## Preparacion
1. Confirmar que la rama `main` se encuentre estable y aprobada.
2. Actualizar version en los artefactos necesarios (tags, notas de version).
3. Ejecutar pipeline de integracion continua con pruebas y validaciones de arquitectura.

## Construccion de artefactos
- Generar imagen Docker:
  ```bash
  docker build -t registro-camiones-backend:<version> .
  ```
- Empujar la imagen al registry correspondiente (ECR, ACR, GCR).

## Configuracion del entorno
- Provisionar base de datos (PostgreSQL recomendado para produccion).
- Configurar variables de entorno (ver `docs/04_Especificaciones_Tecnicas/Entorno_de_Desarrollo.md`).
- Definir storage permanente para `MEDIA_ROOT` (S3, GCS, Azure Blob).
- Desplegar Redis administrado o contenedor dedicado si se usan tareas Celery.

## Ejecucion de despliegue
1. Detener trafico entrante (modo mantenimiento) si se requiere ventana.
2. Descargar la nueva imagen y recrear servicios:
   ```bash
   docker compose pull
   docker compose up -d --no-deps --build django celery
   ```
   o equivalente en la plataforma (ECS, AKS, Kubernetes).
3. Ejecutar migraciones:
   ```bash
   docker compose exec django python manage.py migrate
   ```
4. Generar archivos estaticos si se usan (`python manage.py collectstatic --noinput`).
5. Reiniciar workers Celery para cargar la nueva version.

## Validaciones post-despliegue
- Realizar smoke tests:
  - `GET /api/v1/whoami` usando token de prueba.
  - Crear submission en ambiente controlado.
  - Ejecutar verificacion OCR con imagen de ejemplo.
- Verificar logs en busca de errores (`docker logs`, CloudWatch, Stackdriver).
- Confirmar que el autoscaling (si existe) reconoce la nueva imagen.

## Tareas finales
- Levantar el modo mantenimiento y notificar a los usuarios.
- Actualizar la documentacion si hubo cambios relevantes.
- Archivar reporte de despliegue con tiempos, responsables e incidencias.
