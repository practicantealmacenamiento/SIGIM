# Codigo Fuente y Estructura

## Repositorio
- Nombre sugerido: `formulario-ia-backend`.
- Rama principal: `main` (ajustar segun estrategia del equipo).
- Integracion continua recomendada: ejecutar `pytest`, `python manage.py check` e import-linter.

## Estructura principal
```
BACK_FormContainers/
├── app/
│   ├── domain/          # Entidades, reglas y puertos
│   ├── application/     # Casos de uso y servicios
│   ├── infrastructure/  # Modelos Django, repositorios y adaptadores
│   └── interfaces/      # Vistas DRF, serializadores de entrada
├── core/                # Configuracion Django
├── docs/                # Documentacion funcional y tecnica
├── media/               # Archivos cargados en desarrollo
├── docker-compose.yml   # Orquestacion local
├── Dockerfile           # Imagen Python 3.12
├── requirements.txt     # Dependencias congeladas
└── pyproject.toml       # Reglas import-linter
```

## Buenas practicas de versionamiento
- Mantener commits atomicos con mensajes orientados a funcionalidad.
- Abrir Pull Requests con descripcion de cambios, pruebas ejecutadas y checklist de seguridad.
- Etiquetar versiones producto (tags) siguiendo `vMAJOR.MINOR.PATCH`.

## Referencias adicionales
- Los esquemas de base de datos y diagramas se documentan en `docs/05_Arquitectura_y_Disenio`.
- Material de soporte y flujos de cuestionarios puede exportarse en `forms_export.json`.
