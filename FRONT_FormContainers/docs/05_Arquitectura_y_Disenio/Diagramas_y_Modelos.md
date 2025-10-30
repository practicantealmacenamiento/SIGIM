# Diagramas y Modelos

## Estructura de rutas
```mermaid
graph TD
    A[RootLayout<br/>src/app/layout.tsx] -->|Protege| B[(middleware.ts)]
    A --> C(/login)
    A --> D(/formulario)
    A --> E(/historial)
    A --> F(/panel)
    A --> G(/admin)
    A --> H(/):::home

    subgraph Auth Context
        C --> I[AuthProvider]
        I --> J[AuthGate]
    end

    classDef home fill=#f5f5f5,stroke=#999,color=#111;
```

## Flujo Guardar y Avanzar en el cliente
```mermaid
sequenceDiagram
    participant Page as /formulario/page.tsx
    participant Hook as useFormFlow
    participant Draft as lib/draft.ts
    participant API as lib/api.form.ts
    participant Back as Backend SIGIM

    Page->>Hook: useFormFlow(questionnaire_id, submission_id)
    Hook->>Draft: loadDraft()
    alt Hay borrador valido
        Hook-->>Page: resumeDraft
    else Sin borrador
        Hook->>API: getPrimeraPregunta()
        API->>Back: GET /api/v1/cuestionario/primera/
        Back-->>API: Question
        API-->>Hook: Question
    end
    loop Por cada respuesta
        Page->>Hook: submitOne(item)
        Hook->>API: guardarYAvanzar(FormData)
        API->>Back: POST /api/v1/cuestionario/guardar_avanzar/
        Back-->>API: SaveAndAdvanceResult
        API-->>Hook: SaveAndAdvanceResult
        Hook->>Draft: saveDraft()
    end
    Page->>Hook: onEnviar()
    Hook->>API: finalizarSubmission(id)
    API->>Back: POST /api/v1/submissions/{id}/finalize/
    Back-->>API: OK
    Hook->>Draft: clearDraft()
    Hook-->>Page: finalizado = true
```

## Historial enriquecido y exportacion
```mermaid
sequenceDiagram
    participant UI as /historial/page.tsx
    participant Client as fetchHistorialEnriched
    participant Back as Backend SIGIM
    participant CSV as exportHistorialCSV

    UI->>Client: fetchHistorialEnriched(filtros, query)
    Client->>Back: GET /api/v1/historial/reguladores/
    Back-->>Client: Items agrupados (fase1, fase2)
    Client->>Back: (opcional) GET actores relacionados
    Client-->>UI: rows deduplicadas + metadatos
    UI-->>CSV: exportHistorialCSV(rowsFiltrados)
    CSV-->>UI: Blob CSV descargable
```

## Diagrama de componentes principales
```mermaid
flowchart LR
    subgraph Auth
        AP[AuthProvider]
        AG[AuthGate]
        CB[ClientAuthBootstrap]
    end
    subgraph Formulario
        UF[useFormFlow]
        FI[components/inputs/*]
        QA[questionCard.tsx]
    end
    subgraph Datos
        HF[lib/http.ts]
        AF[lib/api.form.ts]
        AH[lib/api.historial.ts]
        AA[lib/api.admin.ts]
    end
    AP --> AG --> Header[components/header/header.tsx]
    CB --> AP
    UF --> AF
    FI --> UF
    QA --> UF
    AH --> HistorialUI[/historial/page.tsx/]
    AA --> AdminUI[/admin/*/]
    HF --> AF
    HF --> AH
    HF --> AA
```

