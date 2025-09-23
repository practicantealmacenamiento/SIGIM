# Plan de Implementación

- [x] 1. Refactorizar excepciones de dominio

  - Crear jerarquía de excepciones específicas del dominio
  - Separar excepciones de validación, entidad no encontrada y violación de reglas de negocio
  - Eliminar dependencias de excepciones de Django en la capa de dominio
  - _Requisitos: 1.5, 6.1_

- [x] 2. Purificar entidades de dominio

  - [x] 2.1 Refactorizar entidad Answer para eliminar dependencias externas

    - Convertir Answer a dataclass inmutable
    - Mover lógica de validación a métodos de la entidad
    - Eliminar importaciones de Django/DRF
    - _Requisitos: 1.1, 1.5_

  - [x] 2.2 Refactorizar entidades Question, Choice y Questionnaire

    - Convertir a dataclasses inmutables
    - Implementar métodos de validación de dominio
    - Asegurar independencia de frameworks
    - _Requisitos: 1.1, 1.5_

- [x] 3. Mejorar puertos de dominio

  - [x] 3.1 Refactorizar TextExtractorPort para mayor claridad

    - Definir interface más específica para OCR
    - Agregar métodos para diferentes tipos de extracción
    - Documentar contratos de los puertos
    - _Requisitos: 1.4_

  - [x] 3.2 Crear puerto para servicio de notificaciones

    - Definir interface para notificaciones del sistema
    - Agregar métodos para diferentes tipos de notificación
    - _Requisitos: 1.4_

- [x] 4. Implementar mapeo explícito entre capas

  - [x] 4.1 Crear funciones de mapeo modelo-entidad para Submission

    - Implementar función to_entity para convertir SubmissionModel a Submission
    - Implementar función to_model para convertir Submission a SubmissionModel
    - Manejar conversiones de tipos y validaciones
    - _Requisitos: 3.5_

  - [x] 4.2 Crear funciones de mapeo modelo-entidad para Answer

    - Implementar mapeo bidireccional entre AnswerModel y Answer
    - Manejar campos opcionales y validaciones
    - _Requisitos: 3.5_

  - [x] 4.3 Crear funciones de mapeo para Question y Choice

    - Implementar mapeo completo para entidades de cuestionario
    - Manejar relaciones y campos anidados
    - _Requisitos: 3.5_

- [x] 5. Refactorizar repositorios de infraestructura

  - [x] 5.1 Actualizar DjangoAnswerRepository para usar mapeo explícito

    - Reemplazar acceso directo a modelos con funciones de mapeo
    - Implementar conversión bidireccional en todos los métodos
    - Asegurar que retorne entidades de dominio
    - _Requisitos: 3.1, 3.5_

  - [x] 5.2 Actualizar DjangoSubmissionRepository para usar mapeo explícito

    - Implementar mapeo en todos los métodos CRUD
    - Manejar relaciones complejas con mapeo explícito
    - _Requisitos: 3.1, 3.5_

  - [x] 5.3 Actualizar otros repositorios (Question, Choice, Questionnaire)

    - Aplicar patrón de mapeo explícito consistentemente
    - Asegurar implementación completa de protocolos de dominio
    - _Requisitos: 3.1, 3.5_

- [x] 6. Implementar inyección de dependencias

  - [x] 6.1 Crear ServiceFactory para construcción de servicios

    - Implementar factory pattern para servicios de aplicación
    - Configurar inyección de todas las dependencias
    - Centralizar creación de instancias de servicios
    - _Requisitos: 5.1, 5.2_

  - [x] 6.2 Refactorizar servicios de aplicación para usar constructor injection

    - Modificar AnswerService para recibir dependencias por constructor
    - Modificar SubmissionService para usar inyección de dependencias
    - Modificar QuestionnaireService para eliminar dependencias directas
    - _Requisitos: 5.1, 2.3_

  - [x] 6.3 Actualizar VerificationService para usar puertos de dominio

    - Refactorizar para depender solo de TextExtractorPort
    - Eliminar dependencias directas de implementaciones
    - _Requisitos: 5.1, 2.1_

- [x] 7. Refactorizar serializadores para eliminar ModelSerializer

  - [x] 7.1 Convertir serializadores de lectura a serializadores manuales

    - Reemplazar SubmissionModelSerializer con serializer manual
    - Reemplazar AnswerReadSerializer para usar entidades de dominio
    - Eliminar dependencias de modelos Django en serializadores
    - _Requisitos: 4.2, 3.4_

  - [x] 7.2 Actualizar serializadores de escritura

    - Refactorizar GuardarRespuestaSerializer para ser completamente manual
    - Actualizar SaveAndAdvanceInputSerializer sin dependencias de modelo
    - _Requisitos: 4.2, 3.4_

  - [x] 7.3 Crear serializadores de respuesta basados en entidades

    - Implementar serializadores que trabajen directamente con entidades de dominio
    - Asegurar separación completa de modelos de infraestructura
    - _Requisitos: 4.2, 3.4_

- [x] 8. Simplificar controladores HTTP

  - [x] 8.1 Refactorizar SubmissionViewSet para delegar a servicios

    - Eliminar lógica de negocio de las vistas
    - Implementar solo validación de entrada y llamadas a servicios
    - Usar factory para obtener servicios de aplicación
    - _Requisitos: 4.1, 5.3_

  - [x] 8.2 Refactorizar GuardarYAvanzarAPIView

    - Simplificar vista para solo manejar HTTP y delegar a QuestionnaireService

    - Implementar manejo de errores consistente
    - _Requisitos: 4.1, 5.3_

  - [x] 8.3 Refactorizar VerificacionUniversalAPIView

    - Delegar completamente a VerificationService
    - Eliminar lógica de negocio de la vista
    - _Requisitos: 4.1, 5.3_

- [x] 9. Implementar manejo consistente de errores

  - [x] 9.1 Crear traductor de excepciones de dominio a HTTP

    - Implementar función para mapear excepciones de dominio a códigos HTTP
    - Crear middleware o decorator para manejo automático
    - _Requisitos: 6.4, 4.4_

  - [x] 9.2 Actualizar servicios de aplicación para usar excepciones de dominio

    - Refactorizar AnswerService para lanzar excepciones de dominio
    - Refactorizar SubmissionService para manejo consistente de errores
    - _Requisitos: 6.2, 2.4_

  - [x] 9.3 Actualizar vistas para usar traductor de excepciones

    - Aplicar manejo consistente en todas las vistas
    - Eliminar manejo ad-hoc de excepciones
    - _Requisitos: 6.4, 4.4_

- [x] 10. Implementar adaptadores de servicios externos

  - [x] 10.1 Refactorizar GoogleVisionAdapter para implementar puerto de dominio

    - Asegurar que implemente exactamente TextExtractorPort
    - Manejar errores específicos del servicio y traducir a excepciones de dominio
    - _Requisitos: 3.2, 6.3_

  - [x] 10.2 Refactorizar DjangoDefaultStorageAdapter

    - Implementar completamente FileStorage port
    - Manejar errores de storage y traducir apropiadamente
    - _Requisitos: 3.2, 6.3_

- [x] 11. Crear pruebas arquitectónicas

  - [x] 11.1 Implementar pruebas de límites de capas

    - Crear pruebas que verifiquen que domain no importe de capas externas
    - Verificar que application solo dependa de domain
    - Verificar que infrastructure implemente interfaces de domain
    - _Requisitos: 7.5, 8.3_

  - [x] 11.2 Implementar pruebas unitarias de dominio

    - Crear pruebas para entidades sin dependencias externas
    - Probar reglas de negocio y validaciones
    - _Requisitos: 7.1_

  - [x] 11.3 Implementar pruebas de servicios de aplicación con mocks

    - Crear pruebas que usen mocks para repositorios y puertos
    - Verificar orquestación de casos de uso
    - _Requisitos: 7.2_

- [x] 12. Validar cumplimiento de Clean Architecture


  - [x] 12.1 Ejecutar análisis estático de dependencias

    - Usar herramientas como import-linter para validar arquitectura
    - Configurar reglas de dependencias entre capas
    - _Requisitos: 8.3, 7.5_

  - [x] 12.2 Revisar y documentar patrones arquitectónicos

    - Documentar convenciones de nomenclatura por capa
    - Crear guías para futuras implementaciones
    - _Requisitos: 8.1, 8.4_

  - [x] 12.3 Ejecutar suite completa de pruebas

    - Verificar que todas las pruebas pasen después de refactoring
    - Validar que no hay regresiones funcionales
    - _Requisitos: 7.5_
