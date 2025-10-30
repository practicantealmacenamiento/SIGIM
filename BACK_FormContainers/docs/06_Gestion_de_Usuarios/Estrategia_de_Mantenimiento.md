# Estrategia de Mantenimiento y Actualizaciones

## Cadencia sugerida
- **Semanal**
  - Revisar logs de aplicacion y metricas de latencia.
  - Ejecutar `pytest` e `import-linter` para detectar regresiones.
  - Auditar `VisionMonthlyUsage` y crear alertas si el consumo supera el 70% del limite.
- **Mensual**
  - Actualizar dependencias menores (`pip list --outdated`, `pip-audit`).
  - Revisar reglas de cuestionario vigentes con el equipo funcional.
  - Limpiar submissions incompletos antiguos y archivos huérfanos en `media/`.
- **Trimestral**
  - Revisar arquitectura frente a nuevos requerimientos, validar contratos Clean Architecture.
  - Evaluar necesidad de refactorizar servicios criticos (GuardaryAvanzar, VerificationService, ServiceFactory).
  - Revisar accesos staff y rotar tokens o llaves de servicio.

## Flujo de cambio controlado
1. Crear rama desde `main`.
2. Implementar cambios respetando contratos (`commands`, puertos, servicios).
3. Ejecutar `pytest`, `python manage.py check`, `import-linter` y `python manage.py spectacular --file schema.yml`.
4. Actualizar documentacion (`docs/`) y agregar notas de despliegue.
5. Crear Pull Request con resumen del cambio, pruebas ejecutadas y riesgos.
6. Tras aprobacion, realizar merge (rebase o squash segun politica) y etiquetar version si aplica.

## Plan de rollback
- Generar backups de base de datos y almacenamiento antes de cada despliegue.
- Utilizar imagenes versionadas en Docker/ECS/Kubernetes para revertir rapidamente.
- Documentar pasos para revertir migraciones o aplicar hotfix en caso de error.
- Mantener scripts de restauracion validados en ambiente de staging.

## Documentacion continua
- Actualizar este repositorio de docs cada vez que cambien endpoints, flujos o configuraciones.
- Compartir el esquema OpenAPI actualizado con los equipos de frontend e integraciones.
- Registrar postmortems, lecciones aprendidas y manuales paso a paso en la base de conocimiento corporativa.

## Gestion de usuarios y accesos
- Revisar trimestralmente usuarios con `is_staff`/`is_superuser` y revocar cuentas inactivas.
- Mantener checklist de onboarding/offboarding (credenciales, permisos, tokens).
- Documentar la asignacion y rotacion de `API_SECRET_TOKEN` o cuentas de servicio.

## Automatizacion recomendada
- Pipeline CI/CD con etapas: lint (opcional), `pytest`, `import-linter`, `python manage.py check`, generacion de esquema, build de imagen Docker.
- Despliegue automatico a staging; produccion requiere aprobacion manual tras verificar smoke tests.
- Integrar herramientas de seguridad (SAST/DAST) y analitica de dependencias en la cadena de CI.
