# Azure infrastructure

The local stack and this Azure deployment run **the same code**. Nothing in
`etl/`, `analytics/` or `streaming/` changes between them — only environment
variables. That property is the whole point of this configuration, and it is
what makes the local demo an honest rehearsal rather than a lookalike.

| Local | Azure | What changes in the code |
| --- | --- | --- |
| `data/raw/*.csv` | ADLS Gen2, container `bronze` | `PULSE_RAW_DIR` |
| `postgres:16-alpine` (docker) | Azure Database for PostgreSQL Flexible 16 | `POSTGRES_HOST`, `POSTGRES_SSLMODE` |
| Redpanda | Event Hubs (Kafka protocol) | `PULSE_KAFKA_BROKERS` + SASL |
| `python -m etl.pipeline` | Databricks job running that module | nothing |
| Streamlit + FastAPI | two Container Apps from one image | nothing |
| `dashboards/powerbi/*` | Power BI Service | nothing |

**Deployment is automated.** See [docs/deployment.md](../../docs/deployment.md)
for the bootstrap, the runbook and the rollback procedure. What follows is the
infrastructure design.

---

## Layout

```
terraform/
├── main.tf              resource group, identity, Key Vault, container apps
├── variables.tf         every input, with the cheapest working default
├── outputs.tf           no secrets - everything sensitive goes to Key Vault
├── backend-dev.hcl      per-environment STATE KEY
├── backend-prod.hcl
├── environments/        dev.tfvars, prod.tfvars
└── modules/
    ├── storage/         ADLS Gen2 + medallion containers + lifecycle tiering
    ├── registry/        ACR - one image, promoted dev -> prod
    ├── streaming/       Event Hubs namespace, one hub per pulse.* topic
    └── warehouse/       PostgreSQL Flexible Server + database + firewall
```

## Running it by hand

Normally CI does this. Locally:

```bash
cd infrastructure/terraform

export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
export TF_VAR_db_admin_password="$(openssl rand -base64 24)"

# The backend block is EMPTY on purpose - you must say which environment.
terraform init  -backend-config=backend-dev.hcl
terraform plan  -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars

terraform output -json environment_variables
```

---

## Decisions worth defending in a review

### PostgreSQL, not Azure SQL

Not a preference — a correctness requirement. `pulse/db.py` supports exactly two
engines, DuckDB and PostgreSQL. Provisioning Azure SQL would create a database
the platform cannot connect to, and the "same code runs locally and on Azure"
claim would be false at the only point where it matters.

It also makes the local rehearsal genuine: docker-compose runs
`postgres:16-alpine`, this runs PostgreSQL 16, and `database/` is the same
portable SQL in both. CI proves it by building the entire warehouse on
PostgreSQL on every push.

### PostgreSQL, not Synapse

Synapse Dedicated is right past roughly a terabyte, or when MPP genuinely helps
the query shapes. Below that it is a large bill for a warehouse a single
well-indexed server serves faster.

The migration path is real, not aspirational. The gold layer is already a
Kimball star schema with surrogate keys, so moving to Synapse is:

1. re-create the DDL with `DISTRIBUTION = HASH(customer_key)` on the large facts
   and `REPLICATE` on the dimensions;
2. `COPY INTO` from the gold parquet the pipeline already writes to ADLS;
3. change `POSTGRES_HOST`.

No transformation logic changes, because the transformation logic is portable
SQL in `database/`.

### The backend block is empty

```hcl
backend "azurerm" {}
```

The state key must differ per environment, or dev and prod share one state file
and the first `apply` destroys the other environment. An empty block makes it
*impossible* to run Terraform without saying which environment you mean —
a default here would be a footgun with the safety off. CI asserts the two keys
are distinct.

### Secrets are outputs of nothing

Connection strings go straight into Key Vault from the root module. A
`sensitive = true` output still lands in plaintext in the state file, so the
safest secret output is the one that does not exist. The container apps read
Key Vault through a managed identity.

### The firewall opens nothing by default

`db_allowed_ip_ranges` is an empty list; an operator has to make an active
decision to open the database to a network. There is no way to inherit
`0.0.0.0/0` from this module by accident. (The `allow-azure-services` rule uses
`0.0.0.0`–`0.0.0.0`, which is Azure's internal sentinel for "Azure services",
not a wildcard.)

CI does not use that variable — it adds a rule for its own runner IP around the
migration step and removes it in an `if: always()` step.

### One user-assigned identity, created before the apps

A system-assigned identity does not exist until the container app is created,
but the app needs `AcrPull` *before* it can pull its image to start. That
ordering problem bites every first deployment. Creating the identity first
breaks the cycle.

### High availability is opt-in, not derived from `environment`

`db_high_availability` roughly doubles the compute bill and is unavailable on
burstable SKUs. Deriving it from `environment` would mean someone turns on a
second database by accident; making it explicit means the cost is a decision.

### Environments differ by SKU and policy, not by structure

dev and prod create the same resources. What changes is burstable vs general
purpose, LRS vs ZRS, retention, HA, and whether the apps scale to zero. A dev
environment shaped differently from prod does not test prod.

---

## Cost

Rough monthly figures for `uksouth` at the defaults:

| Resource | dev | prod |
| --- | ---: | ---: |
| PostgreSQL Flexible Server | ~£11 (B1ms burstable) | ~£175 (D2s_v3 + zone-redundant HA) |
| Event Hubs Standard | ~£17 (1 TU) | ~£35 (2 TU, auto-inflate) |
| ADLS Gen2 | ~£2 | ~£25 |
| Container Registry | ~£4 (Basic) | ~£16 (Standard) |
| Container Apps | ~£0 (scales to zero) | ~£45 (2 apps, always warm) |
| Log Analytics + App Insights | ~£5 | ~£40 |
| Databricks | off in dev | ~£120+ (workload-dependent) |
| **Total** | **~£40/month** | **~£455/month** |

Order-of-magnitude, not a quote. Check the pricing calculator for your own
region before committing to anything.

The local stack costs nothing and demonstrates every capability. Deploy this
only when you need a shared, always-on environment — and tear dev down when you
do not (*Destroy environment* workflow, about fifteen minutes to rebuild).

---

## What is deliberately not here

- **Private endpoints and a VNet.** Correct for a real production deployment,
  and a large amount of configuration that would obscure the architecture this
  repository exists to demonstrate. Both Postgres and the registry are reachable
  over the internet behind a deny-by-default firewall and enforced TLS; this is
  where the hardening work starts.
- **A constrained RBAC Administrator role.** The deploying principal can assign
  any role. In a real tenant, add `--condition` so it can only assign the
  specific roles Terraform needs. Called out rather than quietly shipped.
- **Purview / Unity Catalog.** The `premium` Databricks SKU in prod enables
  Unity Catalog; wiring the catalogue itself is separate work.
- **A scheduled pipeline job.** The workspace is provisioned; scheduling the
  nightly warehouse build on it is noted in the roadmap under orchestration.
