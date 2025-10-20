# Objetivos y Alcance

## Objetivo general
Entregar una plataforma backend confiable que permita gestionar formularios logisticos de entrada y salida de vehiculos, garantizando la captura estructurada de datos, la validacion automatica mediante OCR y la trazabilidad de actores y evidencias.

## Objetivos especificos
- Centralizar el flujo de autenticacion y autorizacion para usuarios operativos y personal administrativo.
- Administrar cuestionarios versionados que puedan ajustarse sin modificar el codigo fuente.
- Permitir el guardado progresivo de respuestas, con control de navegacion y reglas de negocio por tipo de pregunta.
- Mantener un repositorio historico por regulador, separando fases de entrada y salida para auditoria.
- Integrar servicios OCR a traves de puertos desacoplados para validar campos criticos.
- Facilitar la administracion de catalogos maestros de actores desde endpoints protegidos.

## Alcance funcional
- Servicios REST autenticados bajo prefijo `api/v1/`.
- Endpoints para login unificado, verificacion OCR y flujo Guardar y Avanzar.
- CRUD de submissions, incluyendo detalle enriquecido y finalizacion.
- Consultas de historiales y listas resumidas de cuestionarios y actores.
- Gestion administrativa de usuarios internos, cuestionarios y catalogos.
- Publicacion controlada de archivos asociados a respuestas.

## Fuera de alcance
- Interfaces graficas de usuario (frontend) y operacion offline.
- Motor de reportes avanzados o BI fuera del historial expuesto.
- Provision automatica de infraestructura cloud o pipelines CI/CD.
- Migraciones automaticas a motores de base de datos distintos de los configurados.

## Indicadores de exito
- Cobertura completa de los flujos descritos en los requisitos funcionales.
- Tiempos de respuesta inferiores a dos segundos para operaciones CRUD tipicas sobre submissions.
- Capacidad de incorporar nuevos cuestionarios o preguntas sin alterar la capa de dominio.
- Trazabilidad de archivos y respuestas verificada mediante logs y endpoints de detalle.
