# Design Document

## Overview

El problema actual es que las preguntas con `semantic_tag` de actor (proveedor, transportista, receptor) no están mostrando el componente `ActorInput` sino que se están renderizando como campos de texto normales. El componente `ActorInput` ya existe y funciona correctamente, pero la lógica de detección en `questionCard.tsx` no está funcionando como esperado.

## Architecture

### Current State Analysis

1. **Backend**: Funciona correctamente
   - Modelo `Actor` existe con tipos PROVEEDOR, TRANSPORTISTA, RECEPTOR
   - Endpoint `/api/catalogos/actores/` funciona y retorna datos correctos
   - Preguntas tienen `semantic_tag` configurado correctamente
   - `DjangoActorRepository` y `ActorModelSerializer` funcionan

2. **Frontend Components**: Existen y funcionan
   - `ActorInput` component está implementado y funcional
   - Lógica de detección `isActorTag()` está definida
   - Mapeo `TIPO_BY_SLUG` está correcto

3. **Problem Area**: Renderizado condicional en `questionCard.tsx`
   - La condición `isCatalog` no se está evaluando correctamente
   - Las preguntas de actor se están renderizando como `q.type === "text"` en lugar de usar `ActorInput`

## Components and Interfaces

### Component Flow
```
questionCard.tsx
├── tagOf(q) → extrae semantic_tag de la pregunta
├── isActorTag(slug) → verifica si es proveedor/transportista/receptor  
├── isCatalog = isActorTag(slug) → determina si usar ActorInput
└── Renderizado condicional basado en isCatalog
```

### Data Flow
```
Backend Question → Frontend Question → tagOf() → isActorTag() → isCatalog → ActorInput
```

## Root Cause Analysis

Después de revisar el código, el problema más probable es:

1. **Timing Issue**: El `semantic_tag` podría no estar disponible cuando se evalúa `isCatalog`
2. **Data Structure**: La pregunta podría no tener la propiedad `semantic_tag` en el momento del renderizado
3. **Case Sensitivity**: Posible problema de mayúsculas/minúsculas en la comparación

## Error Handling

### Debug Strategy
1. Agregar logging para verificar el valor de `semantic_tag` en tiempo de renderizado
2. Verificar que `isCatalog` se está evaluando correctamente
3. Confirmar que el componente se está re-renderizando cuando cambian los datos

### Fallback Behavior
- Si `semantic_tag` no está disponible, mantener el comportamiento actual (texto)
- Si hay error en la búsqueda de actores, mostrar mensaje de error pero permitir continuar
- Si el actor seleccionado ya no existe, mostrar el nombre guardado sin funcionalidad de búsqueda

## Testing Strategy

### Manual Testing
1. Verificar que preguntas con `semantic_tag` "proveedor" muestren ActorInput
2. Confirmar que la búsqueda funciona para cada tipo de actor
3. Validar que la selección guarda correctamente los datos
4. Probar el comportamiento con datos existentes

### Debug Points
1. Console.log en `tagOf()` para verificar `semantic_tag`
2. Console.log en `isActorTag()` para verificar la evaluación
3. Console.log en `isCatalog` para confirmar el resultado final
4. Verificar el renderizado condicional

## Implementation Notes

### Key Files to Modify
- `FRONT_FormContainers/components/formulario/questionCard.tsx`: Agregar debug y posible fix
- Posiblemente `FRONT_FormContainers/components/formulario/useFormFlow.tsx`: Si hay problema en el flujo de datos

### Debugging Approach
1. Primero agregar logging para identificar exactamente dónde falla la lógica
2. Verificar que los datos llegan correctamente desde el backend
3. Confirmar que la evaluación condicional funciona
4. Implementar fix basado en los hallazgos del debug