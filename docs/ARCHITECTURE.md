# Architecture

CSV and DuckDB data-analysis assistant with FastAPI, Streamlit, Pydantic AI, and safe degraded metadata for failed loads/queries/analysis.

This document is written for reviewers who want to understand how the project is shaped before reading the code. It emphasizes boundaries, dependencies, and degraded paths rather than marketing claims.

## Data Flow

1. CSV upload/load
2. DuckDB table creation
3. Natural-language question
4. Pydantic AI/Gemini analysis or degraded metadata
5. FastAPI/Streamlit response
6. Charts/exports

```mermaid
flowchart TB
    classDef input fill:#ecfeff,stroke:#0891b2,stroke-width:2px,color:#164e63
    classDef core fill:#eef2ff,stroke:#4f46e5,stroke-width:2px,color:#312e81
    classDef external fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#7c2d12
    classDef metadata fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef review fill:#fef2f2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d

    CSV[/CSV dataset/]:::input
    Question[/Natural-language question/]:::input
    User[/Analyst or reviewer/]:::review

    subgraph DataLayer["Data Loading Boundary"]
        Loader[DuckDBManager CSV loader]:::core
        DuckDB[(DuckDB)]:::external
        LoadMeta[last_load_metadata]:::metadata
    end

    subgraph Interfaces["User Interfaces"]
        API[FastAPI service]:::core
        App[Streamlit app]:::core
        CLI[data-analyst entrypoint]:::core
    end

    subgraph Intelligence["Analysis Boundary"]
        Agent[Pydantic AI analysis agent]:::core
        Gemini{{Gemini API optional}}:::external
        QueryResult[QueryResult metadata]:::metadata
        AnalysisMeta[Agent degraded metadata]:::metadata
    end

    subgraph Output["Reviewable Answers"]
        Response[Sanitized API or UI response]:::review
        Charts[Charts exports and tables]:::review
    end

    CSV --> Loader --> DuckDB
    Loader -. load failure .-> LoadMeta
    Question --> API
    Question --> App
    Question --> CLI
    API --> Agent
    App --> Agent
    CLI --> Agent
    Agent <-->|optional reasoning| Gemini
    Agent --> DuckDB
    DuckDB --> QueryResult --> Agent
    Agent -. provider failure .-> AnalysisMeta
    LoadMeta --> Response
    AnalysisMeta --> Response
    Agent --> Response --> User
    QueryResult --> Charts --> User
```

## Main Components

- **DuckDB manager**: Loads CSV files and records load/query metadata for callers.
- **Agent layer**: Returns analysis metadata instead of leaking provider failures.
- **FastAPI API**: Surfaces sanitized response metadata at service boundaries.
- **Streamlit app**: Provides an interactive local UI for datasets and questions.

## External Dependencies

- Python 3.11+
- DuckDB
- FastAPI
- Streamlit
- Optional Gemini/Pydantic AI configuration

The project is intentionally explicit about optional services. Mock, fallback, and degraded paths are labeled in result metadata so a demo cannot be mistaken for a successful production integration.

## Failure And Degraded Modes

- External-service failures are captured as warnings, status fields, or source metadata where the domain model supports it.
- Mock/demo behavior is opt-in or explicitly labeled.
- Generated outputs are treated as review candidates, not authoritative decisions.
- CLI output remains user-facing; library internals use logging or structured metadata.

## What To Review In Code

- CSV load and query metadata make failures explainable.
- Docker build and import smoke tests pass in CI.
- The app offers both API and Streamlit portfolio surfaces.

## Current Limits

- Analysis quality depends on dataset cleanliness and schema inference.
- Gemini/Pydantic AI paths need API configuration.
- Generated insights should be checked against the underlying data.
