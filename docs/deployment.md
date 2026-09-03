# Deployment

Two environments, deployed from GitHub Actions to Azure. No long-lived
credentials anywhere: GitHub mints a short-lived token that Entra ID trusts for
this repository and environment, and nothing is stored that could leak or need
rotating.

```
                     ┌──────────────── build once ────────────────┐
   push to main ───► │ docker build → dev ACR → trivy scan        │
                     └───────────────────┬────────────────────────┘
                                         ▼
                     ┌──────────── deploy to dev ─────────────────┐
                     │ migrate schemas → terraform apply → verify │
                     └───────────────────┬────────────────────────┘
                                         ▼  (manual / release)
                     ┌──────── promote the same image ────────────┐
   approval gate ──► │ az acr import → migrate → apply → verify   │
                     └────────────────────────────────────────────┘
```

The image is built **once**. Prod never gets a rebuild — it imports the exact
manifest dev ran. Every "works in dev, fails in prod" mystery starts with a
second build, so there isn't one.

---

## The workflows

| Workflow | Trigger | Does |
| --- | --- | --- |
| `deploy-infrastructure.yml` | PR → plan dev · push to main → apply dev · dispatch → either | Terraform: the Azure estate |
| `deploy-application.yml` | push to main → dev · release → prod · dispatch → either | Build, promote, migrate, deploy, verify |
| `_deploy-environment.yml` | called by the above | The per-environment deploy, shared so dev and prod cannot drift |
| `destroy-environment.yml` | manual only | Tears an environment down; refuses prod |
| `ci.yml` | every push | Tests, quality suite, Postgres portability — unchanged |

---

## One-time bootstrap

You need `az`, `gh` and `jq`, logged in, with permission to create app
registrations and assign roles.

```bash
./scripts/bootstrap_azure.sh dev  your-org/pulseanalytics
./scripts/bootstrap_azure.sh prod your-org/pulseanalytics
```

That creates, per environment:

- the Terraform state backend (shared account, **different state key** per
  environment — sharing one key means the first apply destroys the other
  environment, which is why `main.tf`'s backend block is deliberately empty and
  `-backend-config` is mandatory)
- an Entra ID app with **federated credentials** — subject
  `repo:<owner>/<repo>:environment:dev`, so a token minted for dev cannot be
  replayed against prod
- role assignments (see *Permissions* below)
- the GitHub environment, its variables, and a generated `DB_ADMIN_PASSWORD`

Then four things the script deliberately leaves to you, because they are policy
decisions rather than configuration:

**1. Required reviewers on `prod`.** Settings → Environments → prod → Required
reviewers. Without this, prod applies with no approval, and the whole two-job
prod design is pointless.

**2. First infrastructure apply.** Actions → *Deploy infrastructure* → Run
workflow → environment `dev`, apply ticked.

**3. Publish the registry to the environment**, so the build job can find it:

```bash
cd infrastructure/terraform
terraform init -backend-config=backend-dev.hcl
gh variable set REGISTRY_LOGIN_SERVER --env dev \
  --body "$(terraform output -raw registry_login_server)"

# and, so prod knows where to promote images FROM:
gh variable set SOURCE_REGISTRY_LOGIN_SERVER --env prod \
  --body "<the dev registry login server>"
```

**4. Let prod pull from the dev registry**, so `az acr import` can promote:

```bash
az role assignment create \
  --assignee-object-id <prod service principal object id> \
  --assignee-principal-type ServicePrincipal \
  --role AcrPull --scope <resource id of the dev ACR>
```

---

## Everyday operation

### Ship to dev

Merge to `main`. That is the whole procedure.

### Ship to prod

Either publish a GitHub release (the release commit's image is promoted), or
Actions → *Deploy application* → Run workflow → environment `prod`. Both wait on
the `prod` environment's reviewers.

### Roll back

Actions → *Deploy application* → Run workflow → environment `prod`, `image_tag`
= the last good SHA.

The image is already in the registry, so a rollback is a deploy, not a rebuild —
minutes rather than tens of minutes, at the moment you can least afford to wait.

### Change infrastructure

Open a PR touching `infrastructure/**`. The dev plan is posted as a PR comment
and updated in place on each push. Merging applies it to dev. For prod, dispatch
*Deploy infrastructure* with environment `prod`:

1. `plan-prod` runs with no approval gate and writes the plan to the run summary
2. `apply-prod` waits for a reviewer
3. on approval it applies **the saved plan file**, not a fresh plan

That last point is the reason prod is two jobs. A re-plan between approval and
apply can pick up a change nobody reviewed — which is how an approved "add one
firewall rule" becomes an unapproved "replace the database".

### Tear down dev

Actions → *Destroy environment* → environment `dev`, type `dev` to confirm, give
a reason. Rebuild with *Deploy infrastructure*, about fifteen minutes.

Dev costs ~£30/month to leave standing. Making teardown one audited click is
what stops it being left up "just in case".

---

## Design decisions worth defending

### Migrations run before the image rolls out

`--stage init` only, and it is idempotent: bronze is `DROP`+`CREATE`, ops tables
are `CREATE TABLE IF NOT EXISTS`, so redeploying does not erase the run log or
the streaming landing zone.

**Loading data is not a deployment step.** A deploy that also reloads the
warehouse cannot be rolled back quickly, and rollback speed is the property that
matters most when something is wrong.

### The firewall opens for one IP, for one step

The database denies by default. The runner adds a rule for its own public IP,
migrates, and removes it — in an `if: always()` step, so a *failed* migration
still closes the hole. A failed deploy that quietly leaves the database open to
a recycled cloud IP is worse than the failure.

### The image deploys through Terraform

`terraform apply -var image_tag=<sha>` rather than
`az containerapp update --image`. The CLI is faster and leaves Terraform
believing the old tag is running — so the next `apply` silently rolls the
deployment back. State stays truthful instead.

### Verification is part of the deploy

After apply, the workflow polls `/health` (which checks the database connection,
so a 200 means more than "the process started"), then asserts the *running
revision* is the tag it deployed. Without that second check the pipeline reports
green when a revision failed to activate and traffic still serves the old one.

### `latest` is never deployed

Every deployable tag is a git SHA. `main` exists in the registry as a pointer
for humans and nothing deploys from it. A moving tag makes a deployment
unreproducible and a rollback undefined.

---

## Permissions

The deploying identity holds three roles, each for a stated reason:

| Role | Scope | Why |
| --- | --- | --- |
| Contributor | subscription | creates the estate |
| Role Based Access Control Administrator | subscription | Terraform creates role *assignments* (the apps' AcrPull, Key Vault access) and Contributor cannot |
| Storage Blob Data Contributor | the state container only | read/write the Terraform state |

Owner would cover the first two and grant far more; two narrow roles are the
smaller blast radius.

**Hardening left undone, deliberately:** RBAC Administrator is unconstrained.
In a real tenant, add `--condition` so it can only assign the specific roles
Terraform needs. It is called out here rather than quietly shipped.

The workload identity — what the containers run as — is separate and much
smaller: AcrPull, Key Vault Secrets User, Storage Blob Data Contributor on the
lake. It is *user-assigned* rather than system-assigned to break an ordering
problem that bites every first deployment: a system-assigned identity does not
exist until the container app is created, but the app needs AcrPull before it
can pull the image to start.

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

Order-of-magnitude, not a quote — Databricks in particular is driven entirely by
how much compute the jobs consume. Check the pricing calculator for your own
region before committing.

The local stack costs nothing and demonstrates every capability. Deploy this
only when you need a shared, always-on environment.

---

## Troubleshooting

**`REGISTRY_LOGIN_SERVER is not set`** — step 3 of the bootstrap was skipped.
The registry does not exist until the first infrastructure apply, which is why
it is not set by the bootstrap script.

**`state describes 'dev' but this job targets 'prod'`** — the backend config and
the tfvars disagree. The deploy stopped before touching anything; check
`backend-*.hcl`.

**`AADSTS70021: No matching federated identity record found`** — the subject
claim does not match. It must be exactly
`repo:<owner>/<repo>:environment:<env>`. A job without an `environment:` key
mints a token with a *branch* subject, which will not match.

**`Image not found in registry` on a prod deploy** — that commit never reached
dev, so there is nothing to promote. Deploy it to dev first. This is the check
working: the alternative is prod silently building its own image.

**Terraform state lock held** — a previous run was cancelled mid-apply. Confirm
nothing is running, then
`terraform force-unlock <id>`. Do not force-unlock a run that might still be
live.

**A `terraform plan` shows the database being replaced** — usually
`db_sku_name` moving between tiers, or the zone drifting. `zone` and
`standby_availability_zone` are in `ignore_changes` for exactly this reason; if
something else is forcing replacement, stop and read the plan rather than
approving it.

---

## What is deliberately not here

- **Blue/green or canary.** Container Apps supports traffic splitting; the
  configuration uses `revision_mode = "Single"` and one revision at 100%.
  Progressive delivery needs a metric to promote or roll back on, and wiring
  one that nobody watches is theatre.
- **Private networking.** Both Postgres and the registry are reachable over the
  internet behind a deny-by-default firewall and TLS. Private endpoints and a
  VNet are the correct next step and a large amount of configuration that would
  obscure the architecture this repository exists to demonstrate.
- **Automated prod deploys.** Prod always waits for a human. That is a choice,
  not a missing feature.
- **Scheduled pipeline runs.** The deployment provisions Databricks; scheduling
  the nightly warehouse build on it is a separate piece of work, noted in
  [two-year-roadmap.md](two-year-roadmap.md) under orchestration.
