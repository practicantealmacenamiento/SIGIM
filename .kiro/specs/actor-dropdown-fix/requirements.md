# Requirements Document

## Introduction

Las preguntas de tipo "actor" (transportista, proveedor, receptor) en el formulario deben mostrar un campo de selección desplegable que permita buscar y seleccionar actores desde la base de datos, en lugar de mostrar un campo de texto simple. Actualmente, aunque el componente ActorInput existe y funciona correctamente, no se está mostrando para las preguntas que tienen semantic_tag de actor.

## Requirements

### Requirement 1

**User Story:** Como usuario llenando el formulario, quiero que las preguntas de transportista, proveedor y receptor muestren un campo de búsqueda desplegable, para poder seleccionar actores existentes de la base de datos en lugar de escribir texto libre.

#### Acceptance Criteria

1. WHEN una pregunta tiene semantic_tag "proveedor" THEN el sistema SHALL mostrar un ActorInput con tipo "PROVEEDOR"
2. WHEN una pregunta tiene semantic_tag "transportista" THEN el sistema SHALL mostrar un ActorInput con tipo "TRANSPORTISTA"  
3. WHEN una pregunta tiene semantic_tag "receptor" THEN el sistema SHALL mostrar un ActorInput con tipo "RECEPTOR"
4. WHEN el usuario escribe en el campo de búsqueda THEN el sistema SHALL mostrar una lista filtrada de actores del tipo correspondiente
5. WHEN el usuario selecciona un actor de la lista THEN el sistema SHALL guardar tanto el nombre como la referencia del actor

### Requirement 2

**User Story:** Como usuario, quiero que la búsqueda de actores sea eficiente y responsive, para poder encontrar rápidamente el actor que necesito.

#### Acceptance Criteria

1. WHEN el usuario escribe al menos 2 caracteres THEN el sistema SHALL realizar la búsqueda automáticamente
2. WHEN la búsqueda retorna resultados THEN el sistema SHALL mostrar máximo 12 actores en la lista desplegable
3. WHEN no hay resultados THEN el sistema SHALL mostrar el mensaje "Sin resultados"
4. WHEN hay un error en la búsqueda THEN el sistema SHALL mostrar un mensaje de error apropiado

### Requirement 3

**User Story:** Como desarrollador, quiero que el sistema mantenga la consistencia entre el frontend y backend, para asegurar que los datos se manejen correctamente.

#### Acceptance Criteria

1. WHEN se detecta una pregunta con semantic_tag de actor THEN el frontend SHALL usar el componente ActorInput existente
2. WHEN se selecciona un actor THEN el sistema SHALL guardar la referencia del actor en el submission
3. WHEN se carga un submission existente THEN el sistema SHALL mostrar el nombre del actor seleccionado previamente
4. IF el actor fue eliminado de la base de datos THEN el sistema SHALL mostrar solo el nombre guardado sin la funcionalidad de búsqueda