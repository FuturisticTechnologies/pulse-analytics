/**
 * Diagram sources for the Business Requirements Document.
 *
 * These describe the BUSINESS, not the implementation. Where a diagram names a
 * system component it does so because a stakeholder needs to know where a
 * decision is made, never as a design instruction.
 */
window.DIAGRAMS = {
  /* =======================================================================
     Current state - how the questions were answered before
     ======================================================================= */
  asIs: `
flowchart TB
    classDef manual fill:#fbeaea,stroke:#d03b3b,color:#0b0b0b
    classDef wait fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef out fill:#f2f1ee,stroke:#898781,color:#52514e

    Q(["A question is asked<br/><i>'why did margin fall?'</i>"])
    A["Analyst exports from the<br/>order system"]:::manual
    B["Marketing exports from<br/>each ad platform"]:::manual
    C["Finance exports the<br/>ledger"]:::manual
    D["Three spreadsheets are<br/>reconciled by hand"]:::manual
    E{"Do the totals<br/>agree?"}:::wait
    F["Re-export and<br/>re-reconcile"]:::manual
    G["A number is produced"]:::out
    H{"Does anyone<br/>trust it?"}:::wait
    I["Meeting spent arguing<br/>about the number, not<br/>the decision"]:::manual
    J(["Decision, 5-10 working days later"]):::out

    Q --> A & B & C --> D --> E
    E -->|"no - usually"| F --> D
    E -->|"yes"| G --> H
    H -->|"no"| I --> A
    H -->|"yes"| J
`,

  /* =======================================================================
     Future state - swimlaned, with the platform in the middle
     ======================================================================= */
  toBe: `
flowchart TB
    classDef auto fill:#e9f6e9,stroke:#1baf7a,color:#0b0b0b
    classDef sys fill:#eaf3fe,stroke:#2a78d6,color:#0b0b0b
    classDef human fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef gate fill:#fbeaea,stroke:#d03b3b,color:#0b0b0b

    subgraph SRC["Source systems"]
        S1["Nightly extract"]:::sys
        S2["Live events"]:::sys
    end

    subgraph PLAT["PulseAnalytics — automated, nightly and continuous"]
        direction TB
        P1["Land raw, nothing rejected"]:::auto
        P2["Clean, de-duplicate, conform"]:::auto
        P3["Build the star schema<br/>and 23 marts"]:::auto
        P4{"64 quality checks"}:::gate
        P5["Publish"]:::auto
        P6["Hold and alert —<br/>yesterday's data stands"]:::gate
    end

    subgraph USE["Business"]
        U1["Open the role's dashboard"]:::human
        U2["Read the agreed number"]:::human
        U3(["Decide — same day"]):::human
    end

    S1 --> P1
    S2 --> P1
    P1 --> P2 --> P3 --> P4
    P4 -->|"all pass"| P5
    P4 -->|"an error check fails"| P6
    P5 --> U1 --> U2 --> U3
`,

  /* =======================================================================
     Month-end close - who does what, and when
     ======================================================================= */
  monthEnd: `
sequenceDiagram
    autonumber
    actor FIN as Finance
    participant PL as PulseAnalytics
    actor EXEC as Executive
    actor ANA as Data analyst

    Note over PL: nightly, unattended
    PL->>PL: rebuild the warehouse
    PL->>PL: run 64 quality checks

    alt an ERROR check fails
        PL-->>ANA: pipeline held, run marked failed
        ANA->>PL: investigate and correct
        ANA->>PL: re-run
    else all checks pass
        PL->>PL: publish the gold layer
    end

    FIN->>PL: open the Executive dashboard
    PL-->>FIN: revenue, margin, AOV — trailing 90 days vs prior 90
    FIN->>FIN: reconcile to the ledger
    Note right of FIN: one source, so this is a<br/>check rather than a rebuild

    EXEC->>PL: open the same dashboard
    PL-->>EXEC: the SAME numbers Finance saw
    EXEC->>EXEC: decide

    ANA->>PL: python -m analytics.run_analytics
    PL-->>ANA: insight report + CSV extracts
    ANA-->>EXEC: commentary on what moved and why
`,

  /* =======================================================================
     Retention intervention - the churn business process
     ======================================================================= */
  churnProcess: `
flowchart TB
    classDef sys fill:#eaf3fe,stroke:#2a78d6,color:#0b0b0b
    classDef human fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef dec fill:#e9f6e9,stroke:#1baf7a,color:#0b0b0b
    classDef stop fill:#f2f1ee,stroke:#898781,color:#52514e

    S(["Weekly retention cycle"])
    A["Score every ACTIVE customer<br/><i>already-churned are excluded —<br/>win-back, not retention</i>"]:::sys
    B["Rank by revenue at risk<br/><i>value x probability</i>"]:::sys
    C{"Risk band?"}:::dec
    D["Critical / High —<br/>personal outreach"]:::human
    E["Medium —<br/>automated win-back offer"]:::human
    F["Low —<br/>no action, monitor"]:::stop
    G["Record the intervention"]:::human
    H{"Did they order<br/>within 90 days?"}:::dec
    I["Retained — feeds the<br/>next model snapshot"]:::sys
    J["Lost — review whether the<br/>offer or the timing failed"]:::human
    E2(["End of cycle"])

    S --> A --> B --> C
    C -->|"Critical, High"| D --> G
    C -->|"Medium"| E --> G
    C -->|"Low"| F --> E2
    G --> H
    H -->|"yes"| I --> E2
    H -->|"no"| J --> E2
`,

  /* =======================================================================
     Conceptual data model - business entities, no keys
     ======================================================================= */
  conceptual: `
erDiagram
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ SESSION : browses
    CUSTOMER }o--|| REGION : "lives in"
    CUSTOMER }o--|| "LOYALTY TIER" : holds

    ORDER ||--|{ "ORDER LINE" : contains
    ORDER ||--o{ "PAYMENT ATTEMPT" : "settled by"
    ORDER }o--o| CAMPAIGN : "attributed to"
    ORDER }o--|| STORE : "placed at"

    "ORDER LINE" }o--|| PRODUCT : "is for"
    PRODUCT }o--|| CATEGORY : "belongs to"
    PRODUCT ||--o{ "STOCK POSITION" : "held as"

    SESSION ||--o{ "ACTIVITY EVENT" : "made up of"
    STORE }o--|| REGION : "sits in"
    CAMPAIGN }o--|| "MARKETING CHANNEL" : "runs on"

    CUSTOMER {
        string who "identity and demographics"
        date acquired
        string channel "how they arrived"
    }
    ORDER {
        datetime placed
        string status "completed drives revenue"
        money value
    }
    "ORDER LINE" {
        int quantity
        money price
        money cost
    }
    "PAYMENT ATTEMPT" {
        string outcome "captured, failed, refunded"
        int attempt
        string reason "why it declined"
    }
    "STOCK POSITION" {
        date week
        int on_hand "point in time, never summed over weeks"
        int reorder_point
    }
    CAMPAIGN {
        money spend
        date window
        string objective
    }
    SESSION {
        string device
        int deepest_step "how far down the funnel"
    }
`,

  /* =======================================================================
     Requirement areas mapped to the delivered capability
     ======================================================================= */
  scopeMap: `
flowchart LR
    classDef in fill:#e9f6e9,stroke:#1baf7a,color:#0b0b0b
    classDef partial fill:#fdf3e2,stroke:#eb6834,color:#0b0b0b
    classDef out fill:#f2f1ee,stroke:#898781,stroke-dasharray:5 3,color:#52514e

    subgraph R1["Release 1 — delivered"]
        direction TB
        A["Single agreed revenue<br/>definition"]:::in
        B["Automated nightly<br/>warehouse"]:::in
        C["Five role dashboards"]:::in
        D["Data-quality gate"]:::in
        E["Real-time trading<br/>and payment view"]:::in
        F["Customer segmentation,<br/>churn, CLV"]:::in
        G["Marketing return and<br/>attribution comparison"]:::in
        H["Inventory replenishment"]:::in
        I["Demand and revenue<br/>forecasting"]:::in
    end

    subgraph R2["Delivered with a stated limitation"]
        direction TB
        J["Incrementality<br/><i>baseline proxy only</i>"]:::partial
        K["Tier-at-time-of-purchase<br/><i>model ready, no source history</i>"]:::partial
        L["Alerting<br/><i>provisioned, not routed</i>"]:::partial
    end

    subgraph R3["Out of scope"]
        direction TB
        M["Write-back to source<br/>systems"]:::out
        N["Individual-level PII<br/>reporting"]:::out
        O["Financial statutory<br/>reporting"]:::out
        P["Real-time personalisation<br/>to the storefront"]:::out
    end

    R1 --> R2 --> R3
`,
};
