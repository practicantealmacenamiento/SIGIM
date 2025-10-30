# Codigo Fuente y Estructura

## Repositorio
- Nombre sugerido: `sigim-backend`.
- Rama principal: `main` (o la definida por el equipo de TI).
- CI recomendada: `pytest`, `python manage.py check`, `import-linter`, generacion de esquema (`python manage.py spectacular --file schema.yml`).

## Estructura principal
```
BACK_FormContainers/
|-- app/
|   |-- application/        # Casos de uso (operativos y admin)
|   |   |-- services/       # Servicios agrupados (admin_services.py, services.py)
|   |   |-- commands.py
|   |   |-- questionnaire.py
|   |   `-- verification.py
|   |-- domain/             # Entidades, reglas de negocio, puertos
|   |-- infrastructure/     # Modelos ORM, repositorios y adaptadores externos
|   |   |-- adapters/
|   |   `-- factories.py
|   |-- interfaces/         # Vistas DRF, auth, servicios HTTP y excepciones
|   |   |-- http/services.py
|   |   |-- views.py
|   |   `-- admin_views.py
|   `-- tests/              # Pruebas de dominio, aplicacion e integracion
|-- core/                   # Configuracion Django (settings, urls raiz)
|-- docs/                   # Documentacion tecnica del backend (esta carpeta)
|-- media/                  # Archivos cargados en desarrollo
|-- docker-compose.yml      # Orquestacion local (django, celery, redis)
|-- Dockerfile              # Imagen base Python 3.12 slim
|-- requirements.txt        # Dependencias congeladas
`-- pyproject.toml          # Contratos de import-linter
```

## Convenciones
- Mantener modulos sin dependencias ciclicas respetando la separacion `interfaces -> application -> domain` y `infrastructure -> domain`.
- Construir servicios de aplicacion mediante `app/infrastructure/factories.py` para evitar acoplar vistas con infraestructura.
- Exponer nueva logica HTTP a traves de `app/interfaces/http/services.py`, reutilizando la traduccion de comandos en todas las vistas.
- Ubicar adaptadores externos en `app/infrastructure/adapters` implementando los puertos declarados en `app/domain/ports`.

## Buenas practicas de versionamiento
- Commits atomicos con contexto de negocio o ticket asociado.
- Pull Requests con descripcion, pruebas ejecutadas y riesgos identificados.
- Tags semanticos `vMAJOR.MINOR.PATCH` para versiones liberadas de SIGIM.

## Referencias adicionales
- Diagramas y detalles de arquitectura: `docs/05_Arquitectura_y_Disenio/*`.
- Comandos de soporte y reportes: `app/management/commands/`.
- Monitoreo del uso de OCR: `app/infrastructure/usage_limits.py` y comando `report_vision_usage`.

