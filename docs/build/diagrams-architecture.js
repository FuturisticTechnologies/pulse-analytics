/**
 * Diagram sources for the Software Architecture Document.
 *
 * Kept out of the HTML because UML notation collides with the HTML parser:
 * `<<abstract>>` becomes an unknown element and `<|--` opens a tag. boot.js
 * injects these with textContent, so the parser never sees them.
 *
 * Every diagram describes the system as built. Where a diagram shows something
 * not yet implemented it says so on the face of the diagram, never silently.
 */
window.DIAGRAMS = {
  /* =======================================================================
     1. Context - who uses the system and what it talks to
     ======================================================================= */
  context: `
flowchart TB
    classDef actor fill:#eaf3fe,stroke:#2a78d6,stroke-width:1.5px,color:#0b0b0b
    classDef system fill:#2a78d6,stroke:#184f95,stroke-width:2px,color:#ffffff
    classDef ext fill:#f2f1ee,stroke:#898781,stroke-width:1.2px,color:#52514e

    EXEC["Executive<br/><i>revenue, margin, growth</i>"]:::actor
    SALES["Sales and merchandising<br/><i>what sold, what to stock</i>"]:::actor
    MKT["Marketing<br/><i>what the spend bought</i>"]:::actor
    OPS["Operations<br/><i>payments, stock, pipeline</i>"]:::actor
    ANALYST["Data analyst<br/><i>builds and operates it</i>"]:::actor

    PULSE["<b>PulseAnalytics</b><br/>Real-time business analytics platform"]:::system

    OLTP[("Order management system<br/><i>nightly extract</i>")]:::ext
    GATEWAY["Payment gateway<br/><i>authorisation events</i>"]:::ext
    WEB["Web and mobile storefront<br/><i>clickstream</i>"]:::ext
    WMS["Warehouse system<br/><i>stock movements</i>"]:::ext
    FX["FX rate service<br/><i>public API</i>"]:::ext
    PBI["Power BI Service"]:::ext

    OLTP -->|"orders, customers,<br/>products (batch)"| PULSE
    GATEWAY -->|"payment events<br/>(stream)"| PULSE
    WEB -->|"customer activity<br/>(stream)"| PULSE
    WMS -->|"stock events<br/>(stream)"| PULSE
    FX -->|"daily rates<br/>(degrades to fallback)"| PULSE

    PULSE --> EXEC
    PULSE --> SALES
    PULSE --> MKT
    PULSE --> OPS
    PULSE --> ANALYST
    PULSE -->|"curated star schema"| PBI
`,

  /* =======================================================================
     2. Containers - the deployable units
     ======================================================================= */
  containers: `
flowchart TB
    classDef store fill:#fdf3e2,stroke:#eb6834,stroke-width:1.4px,color:#0b0b0b
    classDef app fill:#eaf3fe,stroke:#2a78d6,stroke-width:1.4px,color:#0b0b0b
    classDef job fill:#e9f6e9,stroke:#1baf7a,stroke-width:1.4px,color:#0b0b0b
    classDef ext fill:#f2f1ee,stroke:#898781,stroke-dasharray:4 3,color:#52514e

    subgraph SOURCES["Source systems"]
        direction LR
        SRC1["Batch extract<br/>CSV / ADLS"]:::ext
        SRC2["Live event sources"]:::ext
        SRC3["FX API"]:::ext
    end

    subgraph INGEST["Ingestion"]
        direction LR
        ETL["<b>Batch pipeline</b><br/>python -m etl.pipeline<br/><i>6 stages, ~15 s</i>"]:::job
        PROD["<b>Event producer</b><br/>streaming.producer<br/><i>4 correlated topics</i>"]:::job
        CONS["<b>Stream consumer</b><br/>streaming.consumer<br/><i>micro-batched</i>"]:::job
    end

    BUS[["<b>Event bus</b><br/>files | Kafka | Event Hubs<br/><i>one client interface</i>"]]:::store

    subgraph WAREHOUSE["Warehouse - DuckDB or PostgreSQL"]
        direction LR
        BRONZE[("bronze<br/><i>raw landing</i>")]:::store
        SILVER[("silver<br/><i>cleaned</i>")]:::store
        GOLD[("gold<br/><i>star + 23 marts</i>")]:::store
        OPSS[("ops<br/><i>runs, quality, stream</i>")]:::store
    end

    subgraph CONSUME["Consumption"]
        direction LR
        DASH["<b>Dashboards</b><br/>Streamlit, 5 pages"]:::app
        API["<b>Real-time API</b><br/>FastAPI"]:::app
        MODELS["<b>Analytical models</b><br/>analytics.run_analytics"]:::job
        PBIX["Power BI"]:::ext
    end

    SRC1 --> ETL
    SRC3 --> ETL
    SRC2 --> PROD
    PROD --> BUS
    BUS --> CONS

    ETL --> BRONZE --> SILVER --> GOLD
    ETL -.->|"run log,<br/>quality results"| OPSS
    CONS -->|"landed events,<br/>rolling KPIs"| OPSS

    GOLD --> DASH
    GOLD --> API
    GOLD --> MODELS
    GOLD --> PBIX
    OPSS --> DASH
    OPSS --> API
`,

  /* =======================================================================
     4. Class diagram - the core runtime abstractions
     ======================================================================= */
  classes: `
classDiagram
    direction TB

    class Database {
        <<facade>>
        -DatabaseConfig config
        +connect() Connection
        +execute(sql, params) void
        +execute_script(script) int
        +execute_file(path) int
        +query(sql, params) DataFrame
        +scalar(sql, params) Any
        +write_frame(frame, schema, table, truncate) int
        +table_exists(schema, table) bool
        +healthcheck() dict
        -_adapt(sql) str
    }

    class DatabaseConfig {
        <<value object>>
        +str engine
        +Path duckdb_path
        +str host
        +int port
        +str sslmode
        +is_duckdb() bool
        +dsn() str
    }

    class EventBus {
        <<abstract>>
        +publish(topic, key, event)* void
        +consume(topics, max, timeout)* Iterator
        +flush() void
        +close() void
    }

    class FileEventBus {
        -Path directory
        -Path offset_dir
        +committed_offset(topic) int
        +commit(topic, offset) void
        +reset(topics) void
        +backlog(topics) dict
    }

    class KafkaEventBus {
        -Producer _producer
        -Consumer _consumer
    }

    class StreamConsumer {
        -EventBus bus
        -Database db
        -int batch_size
        +drain_once(timeout) int
        +run(duration) int
    }

    class RealtimeKpiProcessor {
        -int window_minutes
        +compute() dict
        +compute_and_store() dict
        +minute_series(minutes) DataFrame
        +recent_alerts(limit) DataFrame
    }

    class EventProducer {
        -Catalogue catalogue
        -ProducerState state
        +emit_order() void
        +emit_due_payments() void
        +emit_activity() void
        +run(rate, duration) dict
    }

    class Check {
        <<value object>>
        +str name
        +str layer
        +str dimension
        +str severity
        +float threshold_pct
        +str failing_sql
        +run(db) dict
    }

    class QualityReport {
        +str run_id
        +DataFrame results
        +failed() DataFrame
        +errors() DataFrame
        +pass_rate_pct() float
        +to_markdown() str
    }

    class RunContext {
        +str run_id
        +str pipeline
        +stage(name) ContextManager
        +failed() bool
        +print_summary() void
    }

    Database o-- DatabaseConfig : configured by
    EventBus <|-- FileEventBus : realises
    EventBus <|-- KafkaEventBus : realises
    StreamConsumer --> EventBus : consumes from
    StreamConsumer --> Database : writes to
    StreamConsumer *-- RealtimeKpiProcessor : owns
    RealtimeKpiProcessor --> Database : reads and writes
    EventProducer --> EventBus : publishes to
    Check --> Database : executes against
    QualityReport o-- Check : summarises
    RunContext --> Database : records runs in
`,

  /* =======================================================================
     5. Layering - allowed dependency directions
     ======================================================================= */
  layers: `
flowchart TB
    classDef l1 fill:#cde2fb,stroke:#2a78d6,color:#0b0b0b
    classDef l2 fill:#9ec5f4,stroke:#2a78d6,color:#0b0b0b
    classDef l3 fill:#3987e5,stroke:#184f95,color:#ffffff
    classDef l4 fill:#184f95,stroke:#0d366b,color:#ffffff
    classDef shared fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b

    PRES["<b>Presentation</b><br/>dashboards/ · streaming.processors.realtime_api"]:::l1
    ANALYSIS["<b>Analysis</b><br/>analytics/ — models on numpy and pandas"]:::l2
    ACCESS["<b>Curated access</b><br/>analytics.common.datasets · dashboards.data_access"]:::l2
    TRANSFORM["<b>Transformation</b><br/>database/*.sql — every business definition"]:::l3
    INGEST["<b>Ingestion</b><br/>etl.extract · etl.load · streaming.producer/consumer"]:::l3
    PLATFORM["<b>Platform</b><br/>pulse/ — config, Database facade, logging, KPI formatting"]:::l4
    SHARED["<b>Cross-cutting</b><br/>etl.quality · etl.run_context"]:::shared

    PRES --> ACCESS
    ANALYSIS --> ACCESS
    ACCESS --> TRANSFORM
    TRANSFORM --> INGEST
    INGEST --> PLATFORM
    ACCESS --> PLATFORM
    ANALYSIS --> PLATFORM
    PRES --> PLATFORM
    SHARED -.->|"observes"| INGEST
    SHARED -.->|"observes"| TRANSFORM
    SHARED --> PLATFORM
`,

  /* =======================================================================
     6. Data model - the star schema
     ======================================================================= */
  starSchema: `
erDiagram
    DIM_DATE ||--o{ FACT_SALES : "when"
    DIM_DATE ||--o{ FACT_ORDERS : "when"
    DIM_DATE ||--o{ FACT_PAYMENTS : "when"
    DIM_DATE ||--o{ FACT_INVENTORY : "when"
    DIM_DATE ||--o{ FACT_CUSTOMER_EVENTS : "when"

    DIM_CUSTOMER ||--o{ FACT_SALES : "who"
    DIM_CUSTOMER ||--o{ FACT_ORDERS : "who"
    DIM_CUSTOMER ||--o{ FACT_CUSTOMER_EVENTS : "who"
    DIM_CUSTOMER ||--o{ DIM_CUSTOMER_HISTORY : "versions"

    DIM_PRODUCT ||--o{ FACT_SALES : "what"
    DIM_PRODUCT ||--o{ FACT_INVENTORY : "what"

    DIM_STORE ||--o{ FACT_SALES : "where"
    DIM_STORE ||--o{ FACT_ORDERS : "where"
    DIM_REGION ||--o{ DIM_STORE : "groups"
    DIM_REGION ||--o{ FACT_SALES : "where"

    DIM_CAMPAIGN ||--o{ FACT_ORDERS : "attributed to"
    DIM_PAYMENT_METHOD ||--o{ FACT_PAYMENTS : "paid by"

    FACT_ORDERS ||--|{ FACT_SALES : "header to lines"

    DIM_DATE {
        int date_key PK "YYYYMMDD"
        date date_value
        int year_number
        string month_short
        bool is_weekend
        bool is_peak_season
    }
    DIM_CUSTOMER {
        int customer_key PK "-1 = Unknown"
        int customer_id "natural key"
        string full_name
        string loyalty_tier
        string acquisition_channel
        date signup_month
    }
    DIM_CUSTOMER_HISTORY {
        int customer_history_key PK
        int customer_id FK
        string loyalty_tier
        date valid_from "SCD Type 2"
        date valid_to
        bool is_current
    }
    DIM_PRODUCT {
        int product_key PK
        string sku
        string category
        float unit_price
        float margin_pct
        string price_band
    }
    DIM_STORE {
        int store_key PK
        string store_name
        string store_type
        bool is_digital
        float floor_sqm
    }
    DIM_REGION {
        int region_key PK
        string region_name
        string country
        string super_region
    }
    DIM_CAMPAIGN {
        int campaign_key PK "-1 = No Campaign"
        string campaign_name
        string channel
        float spend
    }
    DIM_PAYMENT_METHOD {
        int payment_method_key PK
        string payment_method
        string method_family
    }
    FACT_SALES {
        bigint sales_key PK "grain: ORDER LINE"
        int order_date_key FK
        int customer_key FK
        int product_key FK
        int quantity
        float net_amount
        float gross_profit
        bool is_revenue
    }
    FACT_ORDERS {
        bigint order_key PK "grain: ORDER HEADER"
        int order_date_key FK
        int customer_key FK
        int campaign_key FK
        float net_amount
        float shipping_amount
        int customer_order_seq
        bool is_first_order
    }
    FACT_PAYMENTS {
        bigint payment_key PK "grain: ATTEMPT"
        int payment_date_key FK
        int attempt_number
        bool is_final_attempt
        bool is_captured
        string failure_reason
    }
    FACT_INVENTORY {
        bigint inventory_key PK "grain: PRODUCT WEEK"
        int snapshot_date_key FK
        int on_hand_units "SEMI-ADDITIVE"
        float days_of_cover
        bool is_stockout
    }
    FACT_CUSTOMER_EVENTS {
        bigint event_key PK "grain: EVENT"
        int event_date_key FK
        string session_id
        string event_type
        int funnel_step
    }
`,

  /* =======================================================================
     7. Sequence - a batch pipeline run
     ======================================================================= */
  seqBatch: `
sequenceDiagram
    autonumber
    actor OP as Operator / scheduler
    participant CLI as etl.pipeline
    participant CTX as RunContext
    participant EX as etl.extract
    participant LD as etl.load
    participant DB as Database facade
    participant SQL as database/*.sql
    participant DQ as etl.quality

    OP->>CLI: --full-refresh --fail-on-error
    CLI->>CTX: new run_id

    rect rgb(250,250,247)
    Note over CLI,SQL: Stage 1-2 — land the raw data
    CLI->>CTX: stage("init schemas")
    CTX->>SQL: 001_schemas, 002_bronze, 003_ops
    Note right of SQL: ops.* uses CREATE IF NOT EXISTS<br/>so the run log and the streaming<br/>landing zone survive a refresh
    CLI->>CTX: stage("load bronze")
    CTX->>EX: read_table(...) x10
    EX-->>CTX: DataFrames + lineage columns
    CTX->>EX: fetch_fx_rates()
    alt endpoint reachable
        EX-->>CTX: live rates, source="frankfurter.app"
    else unreachable or offline
        EX-->>CTX: fallback curve, source="fallback"
    end
    CTX->>LD: load_all()
    LD->>DB: write_frame() per table
    end

    rect rgb(250,250,247)
    Note over CLI,SQL: Stage 3-5 — build the warehouse
    CLI->>CTX: stage("build silver")
    CTX->>DB: execute_file(010..016)
    CLI->>CTX: stage("build star schema")
    CTX->>DB: execute_file(020..026)
    CLI->>CTX: stage("build gold marts")
    CTX->>DB: execute_file(030..043)
    end

    CLI->>CTX: stage("data-quality suite")
    CTX->>DQ: run_checks(full_suite())
    loop 64 checks
        DQ->>DB: failing_rows / total_rows
    end
    DQ->>DB: persist to ops.data_quality_results
    DQ-->>CLI: QualityReport

    alt an ERROR check failed
        CLI-->>OP: exit 2 — the DATA is bad
    else a stage raised
        CLI-->>OP: exit 1 — the CODE broke
    else all green
        CLI-->>OP: exit 0 + reports/data_quality_report.md
    end
`,

  /* =======================================================================
     8. Sequence - the real-time path
     ======================================================================= */
  seqRealtime: `
sequenceDiagram
    autonumber
    participant SRC as Source system
    participant PR as EventProducer
    participant BUS as EventBus
    participant CN as StreamConsumer
    participant KPI as RealtimeKpiProcessor
    participant DB as ops.stream_events
    actor USER as Operations analyst

    SRC->>PR: order placed
    PR->>PR: decrement stock,<br/>queue authorisation
    PR->>BUS: publish(pulse.orders, key=customer_id)

    opt stock crossed the reorder point
        PR->>BUS: publish(pulse.inventory, low_stock | stockout)
    end

    Note over PR: the authorisation lands a few<br/>seconds later, as a real gateway does
    PR->>BUS: publish(pulse.payments, captured | failed)
    opt first attempt declined
        PR->>BUS: publish(pulse.payments, attempt 2)
    end

    loop every poll interval
        CN->>BUS: consume(topics, max_messages)
        BUS-->>CN: batch of envelopes
        CN->>CN: project() to the table columns
        CN->>DB: write batch
        CN->>BUS: commit(offset)
        Note right of CN: commit AFTER the write —<br/>a crash replays, never loses
    end

    loop every 5 s
        CN->>KPI: compute_and_store()
        KPI->>DB: window over MAX(event_ts)
        Note right of KPI: EVENT time, not wall clock,<br/>so a replay reproduces the KPIs
        KPI->>DB: append ops.realtime_kpis
    end

    USER->>DB: open the Real-time page
    DB-->>USER: live tiles, per-minute trend, alert feed
`,

  /* =======================================================================
     9. Sequence - promoting a release to production
     ======================================================================= */
  seqDeploy: `
sequenceDiagram
    autonumber
    actor DEV as Engineer
    participant GH as GitHub Actions
    participant OIDC as Entra ID
    participant ACRD as ACR (dev)
    participant ACRP as ACR (prod)
    participant TF as Terraform
    participant PG as PostgreSQL
    participant CA as Container Apps
    actor APR as Approver

    DEV->>GH: merge to main
    GH->>OIDC: request token<br/>(sub = repo:...:environment:dev)
    OIDC-->>GH: short-lived token
    GH->>ACRD: build and push :SHA
    GH->>GH: Trivy scan (fail on fixable CRITICAL)
    GH->>TF: apply -var image_tag=SHA (dev)
    GH->>CA: poll /health until 200
    GH-->>DEV: dev is live

    Note over DEV,APR: promotion — never a rebuild

    DEV->>GH: publish release / dispatch env=prod
    GH->>TF: plan (prod) -out=tfplan.binary
    GH-->>APR: plan in the run summary
    APR->>GH: approve the Apply job
    Note right of APR: the SAVED plan is applied,<br/>not a fresh one — what was<br/>reviewed is what is applied

    GH->>ACRP: az acr import :SHA from dev
    GH->>PG: open firewall for the runner IP
    GH->>PG: etl.pipeline --stage init
    GH->>PG: close firewall (always)
    GH->>TF: apply tfplan.binary
    GH->>CA: poll /health, then assert<br/>the running revision carries :SHA
    GH-->>DEV: prod is live
`,

  /* =======================================================================
     10. Activity - the data-quality gate
     ======================================================================= */
  actQuality: `
flowchart TB
    classDef start fill:#0b0b0b,stroke:#0b0b0b,color:#ffffff
    classDef act fill:#eaf3fe,stroke:#2a78d6,color:#0b0b0b
    classDef dec fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef bad fill:#fbeaea,stroke:#d03b3b,color:#0b0b0b
    classDef good fill:#e9f6e9,stroke:#0ca30c,color:#0b0b0b

    S(("start")):::start
    LOAD["Load the check suite<br/><i>bronze + silver + gold</i>"]:::act
    NEXT["Take the next check"]:::act
    RUN["Execute failing_sql<br/><i>returns failed_rows, total_rows</i>"]:::act
    ERR{"Did the check's<br/>own SQL raise?"}:::dec
    RECORD_ERR["Record status=fail,<br/>details='could not execute'"]:::bad
    RATE["observed = failed / total x 100"]:::act
    THRESH{"observed &lt;=<br/>threshold_pct?"}:::dec
    PASS["status = pass"]:::good
    FAIL["status = fail"]:::bad
    MORE{"More checks?"}:::dec
    PERSIST["Append every result to<br/>ops.data_quality_results"]:::act
    REPORT["Write reports/data_quality_report.md"]:::act
    GATE{"Any ERROR-severity<br/>failure, and --fail-on-error?"}:::dec
    EXIT2["exit 2 — the DATA is bad"]:::bad
    EXIT0["exit 0 — safe to publish"]:::good
    E(("end")):::start

    S --> LOAD --> NEXT --> RUN --> ERR
    ERR -->|"yes"| RECORD_ERR --> MORE
    ERR -->|"no"| RATE --> THRESH
    THRESH -->|"yes"| PASS --> MORE
    THRESH -->|"no"| FAIL --> MORE
    MORE -->|"yes"| NEXT
    MORE -->|"no"| PERSIST --> REPORT --> GATE
    GATE -->|"yes"| EXIT2 --> E
    GATE -->|"no"| EXIT0 --> E
`,

  /* =======================================================================
     11. State - order lifecycle
     ======================================================================= */
  stateOrder: `
stateDiagram-v2
    direction LR
    [*] --> Pending : order placed

    Pending --> Completed : payment captured
    Pending --> Cancelled : customer or fraud check
    Completed --> Returned : goods returned

    Cancelled --> [*]
    Returned --> [*]
    Completed --> [*]

    note right of Pending
        is_revenue = false
        Counted in orders_placed,
        excluded from revenue.
    end note

    note right of Completed
        is_revenue = true
        The ONLY state that
        contributes to revenue.
    end note

    note right of Cancelled
        Kept in the fact table and
        flagged, never deleted -
        operations needs to see it.
    end note
`,

  /* =======================================================================
     12. State - customer lifecycle
     ======================================================================= */
  stateCustomer: `
stateDiagram-v2
    direction LR
    [*] --> Prospect : signed up

    Prospect --> New : first completed order
    New --> Active : second order within 90 days
    New --> AtRisk : 91-180 days silent
    Active --> Active : orders again within 90 days
    Active --> AtRisk : 91-180 days silent
    AtRisk --> Active : wins back
    AtRisk --> Lapsed : 181-365 days silent
    Lapsed --> Active : wins back
    Lapsed --> Churned : over 365 days silent
    Churned --> Active : reactivated

    state "At Risk" as AtRisk

    note right of New
        'New' deliberately wins over
        'Active' so acquisition and
        retention cohorts are not
        double counted.
    end note

    note right of Churned
        Excluded from churn SCORING:
        a win-back problem, not a
        retention one.
    end note
`,

  /* =======================================================================
     14. Deployment - the local stack
     ======================================================================= */
  deployLocal: `
flowchart TB
    classDef node fill:#fcfcfb,stroke:#52514e,stroke-width:1.6px,color:#0b0b0b
    classDef art fill:#eaf3fe,stroke:#2a78d6,color:#0b0b0b
    classDef file fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b

    subgraph LAPTOP["&lt;&lt;device&gt;&gt; Developer workstation"]
        direction TB
        subgraph PY["&lt;&lt;execution environment&gt;&gt; Python 3.11 venv"]
            direction LR
            A1["etl.pipeline"]:::art
            A2["streaming.producer"]:::art
            A3["streaming.consumer"]:::art
            A4["Streamlit :8501"]:::art
            A5["FastAPI :8000"]:::art
        end
        DUCK[("pulse.duckdb<br/>&lt;&lt;file&gt;&gt;")]:::file
        NDJSON[("data/stream/*.jsonl<br/>&lt;&lt;file&gt;&gt;")]:::file
        RAW[("data/raw/*.csv<br/>&lt;&lt;file&gt;&gt;")]:::file
    end

    subgraph DOCKER["&lt;&lt;device&gt;&gt; Docker (optional - production rehearsal)"]
        direction LR
        PG[("postgres:16-alpine<br/>:5432")]:::file
        RP[("redpanda<br/>:19092 Kafka API")]:::file
    end

    RAW --> A1
    A1 --> DUCK
    A2 --> NDJSON --> A3 --> DUCK
    DUCK --> A4
    DUCK --> A5

    A1 -.->|"PULSE_DB_ENGINE=postgres"| PG
    A2 -.->|"PULSE_STREAM_BACKEND=kafka"| RP
    RP -.-> A3
`,

  /* =======================================================================
     15. Activity - CI and CD gates
     ======================================================================= */
  actPipeline: `
flowchart LR
    classDef gate fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef job fill:#eaf3fe,stroke:#2a78d6,color:#0b0b0b
    classDef stop fill:#fbeaea,stroke:#d03b3b,color:#0b0b0b
    classDef ok fill:#e9f6e9,stroke:#0ca30c,color:#0b0b0b

    PR(["Pull request"]) --> FAST["Fast checks<br/><i>compile, SQL parses,<br/>KPI docs match SQL</i>"]:::job
    FAST --> TEST["Build and test<br/><i>223 tests, py3.11 + 3.12</i>"]:::job
    FAST --> PGJOB["Portability<br/><i>whole warehouse on PostgreSQL</i>"]:::job
    FAST --> IMG["Image builds"]:::job
    FAST --> TFV["Terraform validates<br/><i>+ actionlint</i>"]:::job
    FAST --> PLAN["Plan (dev)<br/><i>posted as a PR comment</i>"]:::job

    TEST --> MERGE{"Merge to main"}:::gate
    PGJOB --> MERGE
    IMG --> MERGE
    TFV --> MERGE
    PLAN --> MERGE

    MERGE --> BUILD["Build image :SHA<br/>+ Trivy scan"]:::job
    BUILD --> DEVDEP["Deploy dev<br/><i>migrate, apply, verify</i>"]:::job
    DEVDEP --> REL{"Release published<br/>or manual dispatch"}:::gate
    REL --> PPLAN["Plan prod<br/><i>saved to a plan file</i>"]:::job
    PPLAN --> APPROVE{"Required<br/>reviewer"}:::gate
    APPROVE -->|"rejected"| STOP["No change"]:::stop
    APPROVE -->|"approved"| PROMOTE["Promote image<br/><i>acr import, no rebuild</i>"]:::job
    PROMOTE --> PAPPLY["Apply the APPROVED plan"]:::job
    PAPPLY --> VERIFY{"/health 200 and the<br/>running revision is :SHA?"}:::gate
    VERIFY -->|"no"| ROLL["Roll back:<br/>redeploy the last good SHA"]:::stop
    VERIFY -->|"yes"| LIVE["Production live"]:::ok
`,
};
