# Diagramas y Modelos

## Vista de capas
```mermaid
graph LR
    UI[Interfaces<br/>app/interfaces] --> APP[Aplicacion<br/>app/application]
    UI --> INFRA[Infraestructura<br/>app/infrastructure]
    APP --> DOMAIN[Dominio<br/>app/domain]
    INFRA --> DOMAIN
```

## Flujo Guardar y Avanzar
```mermaid
sequenceDiagram
    participant View as GuardarYAvanzarAPIView
    participant Factory as ServiceFactory
    participant Service as QuestionnaireService
    participant Repo as AnswerRepository
    participant Storage as FileStorage

    View->>Factory: get_questionnaire_service()
    Factory-->>View: QuestionnaireService
    View->>Service: save_and_advance(cmd)
    Service->>Repo: get(submission, question)
    Service->>Storage: save(file) (opcional)
    Service->>Repo: save(answer)
    Service-->>View: SaveAndAdvanceResult
```

## Modelo de datos principal
```mermaid
erDiagram
    Questionnaire ||--o{ Question : contiene
    Question ||--o{ Choice : ofrece
    Questionnaire ||--o{ Submission : recibe
    Submission ||--o{ Answer : registra
    Actor ||--o{ Submission : participa

    Questionnaire {
        uuid id
        string title
        string version
        string timezone
    }
    Question {
        uuid id
        string text
        string type
        bool required
        int order
        string semantic_tag
        string file_mode
    }
    Choice {
        uuid id
        string text
        uuid branch_to
    }
    Submission {
        uuid id
        uuid questionnaire_id
        uuid regulador_id
        string tipo_fase
        datetime fecha_creacion
        string placa_vehiculo
        string contenedor
        string precinto
        bool finalizado
        datetime fecha_cierre
    }
    Answer {
        uuid id
        uuid submission_id
        uuid question_id
        text answer_text
        uuid answer_choice_id
        string answer_file
        json ocr_meta
        json meta
        datetime timestamp
    }
    Actor {
        uuid id
        string tipo
        string nombre
        string documento
        json meta
    }
```

## Interaccion para historico por regulador
```mermaid
sequenceDiagram
    participant View as HistorialReguladoresAPIView
    participant Repo as SubmissionRepository
    participant Service as HistoryService

    View->>Service: list_history(filtros)
    Service->>Repo: history_aggregate(filtros)
    Repo-->>Service: filas (fase1_id, fase2_id, ultima_fecha)
    Service->>Repo: get_by_ids(ids)
    Repo-->>Service: mapa de submissions
    Service-->>View: lista consolidada
```

Estos diagramas resumen las relaciones clave y el flujo de mensajes mas relevante para comprender la plataforma.
