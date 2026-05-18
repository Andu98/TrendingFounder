# Architecture Overview

## 1. High-Level System Diagram

```mermaid
flowchart TD
    subgraph UILayer["UI Layer"]
        A["Streamlit UI"] -->|"RPC calls"| B["Supabase DB"]
    end

    subgraph BackendLayer["Backend Layer"]
        C["Crawl Orchestrator"] -->|"fetches"| D["Cloudflare Radar API"]
        C -->|"enriches"| E["LMStudio LLM Service"]
        C -->|"stores"| B

        subgraph DomainLogic["Domain Logic"]
            F["Deduplication"]
            G["Scoring"]
        end

        C --> F
        C --> G
    end

    subgraph ExternalServices["External Services"]
        D
        E
    end

    B -->|"serves data to"| A
```

**Explanation:** The UI (Streamlit) talks directly to Supabase via RPCs. A daily crawl job (`Crawl Orchestrator`) pulls data from Cloudflare, optionally enriches it with an LLM, processes domains through deduplication and scoring, and persists everything in Supabase.

## 2. Main Data Flow Diagram

```mermaid
sequenceDiagram
    participant UI as Streamlit UI
    participant RPC as Supabase RPC
    participant DB as Supabase DB
    participant Crawler as Crawl Orchestrator
    participant Cloud as Cloudflare Radar API
    participant Dedup as Deduplication
    participant Scoring as Scoring
    participant LLM as LMStudio Client

    UI->>RPC: request get_domains_for_range
    RPC->>DB: execute stored procedure
    DB-->>RPC: rows with domains and scores
    RPC-->>UI: JSON payload
    UI->>UI: render tables and charts

    Note over Crawler: Daily crawl through cron or manual run
    Crawler->>Cloud: GET /radar/geolocations
    Cloud-->>Crawler: list of countries

    loop for each country and ranking type
        Crawler->>Cloud: GET /radar/ranking/top
        Cloud-->>Crawler: top domains list
        Crawler->>Dedup: dedupe_and_insert()

        alt new domain
            Crawler->>LLM: enrich domain
            LLM-->>Crawler: enrichment result
            Crawler->>Scoring: score_observation()
            Crawler->>DB: upsert domain and insert observation
        else duplicate domain
            Crawler->>DB: update duplicate counter
        end
    end
```

**Explanation:** The UI layer reads pre-computed data from Supabase. The crawler pulls raw data from Cloudflare, deduplicates domains, runs LLM enrichment when configured, scores observations, and writes the results back to Supabase.

## 3. Component / Module Diagram

```mermaid
classDiagram
    class StreamlitApp {
        +run()
    }

    class DataLoader {
        +load_collected_data()
        +load_today_data()
        +load_stats()
        +load_comments()
    }

    class CrawlOrchestrator {
        +run()
        +process_country()
    }

    class RadarService {
        +get_geolocations()
        +get_top_domains()
    }

    class CloudflareClient {
        +request()
        +get()
    }

    class LMStudioClient {
        +enrich()
    }

    class DomainRepository {
        +upsert_domain()
        +update_llm_fields()
    }

    class ObservationRepository {
        +insert_observation()
    }

    class CrawlRunRepository {
        +create_run()
        +update_progress()
        +complete_run()
    }

    class CrawlCountryStatusRepository {
        +upsert_country_status()
    }

    class Deduplication {
        +dedupe_and_insert()
    }

    class Scoring {
        +score_observation()
    }

    class SupabaseDB {
        +domains
        +domain_observations
        +crawl_runs
        +crawl_country_status
        +domain_comments
        +v_domains_today
        +v_crawl_country_progress
    }

    StreamlitApp --> DataLoader : uses
    DataLoader --> SupabaseDB : RPC and queries
    CrawlOrchestrator --> RadarService : uses
    RadarService --> CloudflareClient : HTTP
    CrawlOrchestrator --> LMStudioClient : optional enrichment
    CrawlOrchestrator --> Deduplication : calls
    CrawlOrchestrator --> Scoring : calls
    CrawlOrchestrator --> DomainRepository : writes
    CrawlOrchestrator --> ObservationRepository : writes
    CrawlOrchestrator --> CrawlRunRepository : status updates
    CrawlOrchestrator --> CrawlCountryStatusRepository : status updates
    DomainRepository --> SupabaseDB : writes
    ObservationRepository --> SupabaseDB : writes
    CrawlRunRepository --> SupabaseDB : writes
    CrawlCountryStatusRepository --> SupabaseDB : writes
```

**Explanation:** This diagram shows the main Python modules and their responsibilities, plus the Supabase persistence layer.

## 4. Sequence Diagram - Main User Flow (Dashboard Load)

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Streamlit as Streamlit Server
    participant RPC as Supabase RPC
    participant DB as Supabase DB

    User->>Browser: Open local dashboard
    Browser->>Streamlit: GET initial page
    Streamlit-->>Browser: HTML and Streamlit runtime
    Browser->>Streamlit: request filtered data
    Streamlit->>RPC: call get_domains_for_range with filters
    RPC->>DB: run stored procedure
    DB-->>RPC: domain rows and total count
    RPC-->>Streamlit: JSON payload
    Streamlit-->>Browser: render tables, metrics, and charts
```

**Explanation:** When a user opens the dashboard, Streamlit serves the page, fetches domain data via Supabase RPC, and renders the UI components.

## 5. Database Diagram

```mermaid
erDiagram
    DOMAIN {
        string id PK
        string normalized_domain
        string display_url
        datetime first_seen_at
        date first_seen_date
        string first_country_code
        string first_country_name
        string first_ranking_type
        float initial_score
        string review_status
        string llm_summary
        string llm_category
        string llm_business_model
        string llm_target_users
        string llm_localization_angle
        string llm_risk_notes
    }

    OBSERVATION {
        string id PK
        string domain_id FK
        string crawl_run_id FK
        date observed_date
        string country_code
        string country_name
        string ranking_type
        int rank
        float pct_rank_change
        float observation_score
    }

    CRAWL_RUN {
        string id PK
        date run_date
        string status
        datetime started_at
        datetime finished_at
    }

    CRAWL_COUNTRY_STATUS {
        string id PK
        string crawl_run_id FK
        string country_code
        string status
        int items_found
        int new_domains
        int duplicate_domains
    }

    COMMENT {
        string id PK
        string domain_id FK
        string author_name
        string message
        datetime created_at
    }

    DOMAIN ||--o{ OBSERVATION : has
    CRAWL_RUN ||--o{ OBSERVATION : produces
    CRAWL_RUN ||--o{ CRAWL_COUNTRY_STATUS : tracks
    DOMAIN ||--o{ COMMENT : has
```

**Explanation:** This diagram lists the primary Supabase tables and their relationships.

## 6. External Services Diagram

```mermaid
flowchart LR
    Crawler["Crawl Orchestrator"] --> Cloudflare["Cloudflare Radar API"]
    Crawler --> LLM["LMStudio LLM Service"]
    Crawler --> DB["Supabase DB"]

    Cloudflare --> Geo["GET /radar/geolocations"]
    Cloudflare --> Ranking["GET /radar/ranking/top"]
    LLM --> Enrich["enrich(domain)"]
    DB --> Tables["domains, observations, crawl runs, comments"]
```

**Explanation:** Cloudflare provides ranking and geolocation data. LMStudio provides optional LLM enrichment. Supabase stores the processed results.

## 7. Detailed Crawl Pipeline Diagram

```mermaid
flowchart LR
    subgraph Start["Start Crawl"]
        A["Create CrawlRun"] --> B["Fetch Country List"]
    end

    B --> C["Iterate Countries"]
    C --> D["Get Top Domains per RankingType"]
    D --> E["Deduplication"]
    E -->|"new"| F["LLM Enrichment"]
    F --> G["Scoring"]
    G --> H["Insert Observation"]
    E -->|"duplicate"| I["Skip LLM and Scoring"]
    I --> J["Update Duplicate Counters"]
    H --> K["Update CrawlRun Progress"]
    J --> K
    K --> L["Check for Pause or Stop"]
    L -->|"continue"| C
    L -->|"stop"| M["Complete CrawlRun"]
    M --> N["Persist Final Stats"]
```

**Explanation:** This shows each step of the daily crawl, including conditional LLM enrichment only for new domains and progress tracking.

## 8. Error Handling & Retry Diagram

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Radar as Cloudflare Radar
    participant LLM
    participant DB
    participant Logger

    Orchestrator->>Radar: GET /radar/ranking/top
    Radar-->>Orchestrator: 429 Too Many Requests
    Orchestrator->>Logger: warn rate limited
    Orchestrator->>Radar: retry with exponential backoff
    Radar-->>Orchestrator: 200 OK
    Orchestrator->>LLM: enrich domain

    alt LLM fails
        LLM-->>Orchestrator: exception
        Orchestrator->>Logger: error LLM enrichment failed
        Orchestrator->>DB: record observation without LLM fields
    else LLM succeeds
        LLM-->>Orchestrator: enrichment data
        Orchestrator->>DB: upsert domain with LLM fields
    end
```

**Explanation:** The orchestrator uses retry logic for Cloudflare calls. LLM enrichment failures are logged and the observation is still stored without LLM fields.

---

All diagrams are Mermaid-compatible and can be rendered independently by a Markdown documentation pipeline.
