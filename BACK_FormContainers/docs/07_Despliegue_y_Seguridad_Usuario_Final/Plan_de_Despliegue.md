# Plan de Despliegue

## Preparacion
1. Confirmar estabilidad de la rama `main` (CI en verde y aprobaciones completadas).
2. Actualizar version/tag correspondiente (`vMAJOR.MINOR.PATCH`) y registrar notas de entrega.
3. Verificar que `docs/` y el esquema OpenAPI esten actualizados.
4. Revisar `VisionMonthlyUsage` para asegurarse de que el contador no exceda el limite antes del cambio.

## Construccion de artefactos
```bash
docker build -t sigim-backend:<version> .
docker push <registry>/sigim-backend:<version>
```
- Incluir hash corto del commit como etiqueta secundaria para rastreo.
- Generar archivo `schema.yml` y adjuntarlo al paquete de despliegue si aplica.

## Configuracion del entorno
- Base de datos: SQL Server (produccion) o PostgreSQL segun politica; aplicar migraciones pendientes.
- Almacenamiento: configurar backend (S3, GCS, Azure) apuntando a `MEDIA_ROOT`. Ajustar credenciales en variables de entorno.
- OCR: cargar `GOOGLE_APPLICATION_CREDENTIALS` o habilitar `USE_MOCK_OCR` en ambientes sin Vision.
- Seguridad: definir `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `API_SECRET_TOKEN`, `VISION_MAX_PER_MONTH`.
- Redis/Celery: desplegar servicios cuando el entorno requiera procesamiento asincrono.

## Procedimiento de despliegue
1. Activar modo mantenimiento en la capa de front o balanceador (si se requiere ventana).
2. Actualizar servicios con la nueva imagen:
   ```bash
   docker compose pull
   docker compose up -d --no-deps --build django celery
   ```
   o el equivalente en Kubernetes/ECS/AKS.
3. Aplicar migraciones y recolectar estaticos:
   ```bash
   docker compose exec django python manage.py migrate
   docker compose exec django python manage.py collectstatic --noinput
   ```
4. Ejecutar tareas de soporte:
   ```bash
   docker compose exec django python manage.py report_vision_usage
   ```
   (verificar que el contador actualice correctamente).
5. Reiniciar workers Celery y servicios auxiliares que dependan del codigo.

## Validaciones post-despliegue
- Smoke tests:
  - `GET /api/v1/whoami` con token de prueba.
  - Crear submission dummy y ejecutar Guardar y Avanzar.
  - Verificacion OCR con imagen de referencia.
- Revisar logs (`docker logs`, CloudWatch, Stackdriver) en busca de errores 4xx/5xx anormales.
- Corroborar que el frontend consume el esquema nuevo sin rupturas.

## Tareas finales
- Desactivar modo mantenimiento y notificar a usuarios clave.
- Actualizar tablero de despliegues con tiempos, responsables y estado final.
- Archivar reporte con resumen de pruebas, incidentes y recomendaciones.
- Programar seguimiento a las 24 h para verificar estabilidad y consumo OCR.
