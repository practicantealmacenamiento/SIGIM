# Diagramas y Modelos

## Vista de capas
```mermaid
graph LR
    UI[Interfaces<br/>app/interfaces] -->|comandos/DTO| APP[Aplicacion<br/>app/application]
    APP -->|entidades/puertos| DOMAIN[Dominio<br/>app/domain]
    UI -->|serializadores/adaptadores| INFRA[Infraestructura<br/>app/infrastructure]
    INFRA -->|implementa puertos| DOMAIN
```

## Flujo Guardar y Avanzar
```mermaid
sequenceDiagram
    participant View as GuardarYAvanzarAPIView
    participant Factory as ServiceFactory
    participant Service as QuestionnaireService
    participant SubmissionRepo as SubmissionRepository
    participant AnswerRepo as AnswerRepository
    participant Storage as FileStorage

    View->>Factory: create_questionnaire_service()
    Factory-->>View: QuestionnaireService
    View->>Service: save_and_advance(cmd)
    Service->>SubmissionRepo: get(submission_id)
    Service->>AnswerRepo: list_by_submission_question()
    alt pregunta con archivo
        Service->>Storage: save(folder, file)
    end
    Service->>AnswerRepo: save(answer)
    Service-->>View: SaveAndAdvanceResult(next_question_id, is_finished)
```

## Verificacion OCR y contador mensual
```mermaid
sequenceDiagram
    participant API as VerificacionUniversalAPIView
    participant Service as VerificationService
    participant QRepo as QuestionRepository
    participant OCR as TextExtractorPort (Vision/Mock)
    participant Usage as VisionMonthlyUsage

    API->>Service: verify_with_question(question_id, file)
    Service->>QRepo: get(question_id)
    Service->>OCR: extract_text(image_bytes)
    Service-->>API: resultado normalizado
    API->>Usage: update counter (via adapters)
```

## Modelo de datos
```mermaid
erDiagram
    Questionnaire ||--o{ Question : contiene
    Question ||--o{ Choice : ofrece
    Questionnaire ||--o{ Submission : registra
    Submission ||--o{ Answer : almacena
    Actor ||--o{ Submission : participa
    VisionMonthlyUsage ||--|| VisionMonthlyUsage : self

    Questionnaire {
        uuid id
        string title
        string version
        string timezone
    }
    Question {
        uuid id
        uuid questionnaire_id
        string text
        string type
        bool required
        int order
        string semantic_tag
        string file_mode
    }
    Choice {
        uuid id
        uuid question_id
        string text
        uuid branch_to
    }
    Submission {
        uuid id
        uuid questionnaire_id
        uuid regulador_id
        string tipo_fase
        string placa_vehiculo
        string contenedor
        string precinto
        uuid proveedor_id
        uuid transportista_id
        uuid receptor_id
        bool finalizado
        datetime fecha_cierre
        datetime created_at
    }
    Answer {
        uuid id
        uuid submission_id
        uuid question_id
        text answer_text
        uuid answer_choice_id
        string answer_file
        json meta
        json ocr_meta
        datetime timestamp
        uuid user_id
    }
    Actor {
        uuid id
        string tipo
        string nombre
        string documento
        json meta
        bool activo
    }
    VisionMonthlyUsage {
        int year
        int month
        int count
        datetime updated_at
    }
```

## Historial por regulador
```mermaid
sequenceDiagram
    participant View as HistorialReguladoresAPIView
    participant Service as HistoryService
    participant Repo as SubmissionRepository
    participant AnswerRepo as AnswerRepository
    participant QuestionRepo as QuestionRepository

    View->>Service: list_history(filtros, user)
    Service->>Repo: history_aggregate(filtros)
    Repo-->>Service: filas (fase1_id, fase2_id, regulador_id, ultima_fecha)
    Service->>Repo: get_by_ids(ids)
    alt falta placa
        Service->>AnswerRepo: list_by_submission(fase_id)
        AnswerRepo-->>Service: answers
        Service->>QuestionRepo: get(question_id) (para detectar semantic_tag placa)
    end
    Service-->>View: lista consolidada (fase1, fase2, placa, contenedor)
```

Estos diagramas describen las interacciones principales del backend y sirven como referencia para nuevos colaboradores y tareas de soporte.
