#!/usr/bin/env bash
#
# One-time bootstrap for the GitHub Actions -> Azure deployment pipelines.
#
#   ./scripts/bootstrap_azure.sh dev  myorg/pulseanalytics
#   ./scripts/bootstrap_azure.sh prod myorg/pulseanalytics
#
# Creates, per environment:
#   * the Terraform state backend (once, shared by both environments)
#   * an Entra ID app registration with FEDERATED credentials - no client
#     secret, so there is nothing to rotate, leak, or find in a log in 2029
#   * the role assignments that app needs
#   * the GitHub environment, its variables and its one secret
#
# Idempotent: safe to re-run. Everything is created only if missing.
#
# Requires: az (logged in, with permission to create app registrations and
# assign roles) and gh (logged in to the repository).

set -euo pipefail

ENVIRONMENT="${1:-}"
REPO="${2:-}"
LOCATION="${3:-uksouth}"

if [[ -z "$ENVIRONMENT" || -z "$REPO" ]]; then
    cat >&2 <<'USAGE'
Usage: scripts/bootstrap_azure.sh <dev|prod> <owner/repo> [location]

  <dev|prod>    environment to bootstrap
  <owner/repo>  GitHub repository, e.g. acme/pulseanalytics
  [location]    Azure region (default: uksouth)
USAGE
    exit 1
fi

if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    echo "environment must be 'dev' or 'prod'" >&2
    exit 1
fi

for tool in az gh jq; do
    command -v "$tool" >/dev/null || { echo "$tool is not installed" >&2; exit 1; }
done

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
APP_NAME="github-pulseanalytics-${ENVIRONMENT}"

STATE_RG="rg-pulse-tfstate"
STATE_ACCOUNT="stpulsetfstate"
STATE_CONTAINER="tfstate"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

say "Subscription $(az account show --query name -o tsv) ($SUBSCRIPTION_ID)"
say "Environment  $ENVIRONMENT"
say "Repository   $REPO"

# ---------------------------------------------------------------------------
# 1. Terraform state backend
#
# Shared by both environments, with a different KEY per environment (see
# backend-*.hcl). Versioning is on because the state file is the only record of
# what exists - losing it means adopting every resource by hand.
# ---------------------------------------------------------------------------
say "Terraform state backend"

az group create --name "$STATE_RG" --location "$LOCATION" --output none
echo "  resource group $STATE_RG"

if ! az storage account show --name "$STATE_ACCOUNT" --resource-group "$STATE_RG" --output none 2>/dev/null; then
    az storage account create \
        --name "$STATE_ACCOUNT" \
        --resource-group "$STATE_RG" \
        --location "$LOCATION" \
        --sku Standard_LRS \
        --kind StorageV2 \
        --min-tls-version TLS1_2 \
        --allow-blob-public-access false \
        --allow-shared-key-access false \
        --output none
    echo "  created storage account $STATE_ACCOUNT"
else
    echo "  storage account $STATE_ACCOUNT already exists"
fi

# Blob versioning: a corrupted or truncated state file is recoverable.
az storage account blob-service-properties update \
    --account-name "$STATE_ACCOUNT" \
    --resource-group "$STATE_RG" \
    --enable-versioning true \
    --enable-delete-retention true \
    --delete-retention-days 30 \
    --output none
echo "  versioning and 30-day soft delete enabled"

# --auth-mode login: shared keys are disabled above on purpose, so the whole
# path from here to Terraform is Entra ID and nothing holds a storage key.
az storage container create \
    --name "$STATE_CONTAINER" \
    --account-name "$STATE_ACCOUNT" \
    --auth-mode login \
    --output none 2>/dev/null || true
echo "  container $STATE_CONTAINER"

# ---------------------------------------------------------------------------
# 2. Entra ID application with federated credentials
# ---------------------------------------------------------------------------
say "Entra ID application: $APP_NAME"

APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
if [[ -z "$APP_ID" ]]; then
    APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
    echo "  created application $APP_ID"
else
    echo "  application already exists: $APP_ID"
fi

if ! az ad sp show --id "$APP_ID" --output none 2>/dev/null; then
    az ad sp create --id "$APP_ID" --output none
    echo "  created service principal"
fi
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# Federated credentials: Entra ID trusts a GitHub-issued token whose `sub`
# claim matches exactly. That claim is the environment, so a token minted for
# dev cannot be replayed against prod.
add_federated_credential() {
    local name="$1" subject="$2"
    if az ad app federated-credential list --id "$APP_ID" \
        | jq -e --arg n "$name" '.[] | select(.name == $n)' >/dev/null 2>&1; then
        echo "  federated credential '$name' already exists"
        return
    fi
    az ad app federated-credential create --id "$APP_ID" --parameters "$(cat <<JSON
{
  "name": "$name",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "$subject",
  "description": "GitHub Actions - $subject",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON
    )" --output none
    echo "  federated credential '$name' -> $subject"
}

add_federated_credential "gh-env-${ENVIRONMENT}" "repo:${REPO}:environment:${ENVIRONMENT}"

# The prod plan job runs in a separate GitHub environment so the approver can
# read the plan before approving. Same identity, different subject claim.
if [[ "$ENVIRONMENT" == "prod" ]]; then
    add_federated_credential "gh-env-prod-plan" "repo:${REPO}:environment:prod-plan"
fi

# ---------------------------------------------------------------------------
# 3. Role assignments
# ---------------------------------------------------------------------------
say "Role assignments"

assign() {
    local role="$1" scope="$2"
    if az role assignment list --assignee "$SP_OBJECT_ID" --scope "$scope" \
        --query "[?roleDefinitionName=='$role'] | length(@)" -o tsv | grep -q '^[1-9]'; then
        echo "  already has '$role'"
        return
    fi
    az role assignment create \
        --assignee-object-id "$SP_OBJECT_ID" \
        --assignee-principal-type ServicePrincipal \
        --role "$role" \
        --scope "$scope" \
        --output none
    echo "  granted '$role'"
}

# Contributor creates the estate. Terraform also creates ROLE ASSIGNMENTS (the
# container apps' AcrPull and Key Vault access), and Contributor cannot do
# that - hence RBAC Administrator as well. Owner would cover both and grant far
# more; two narrow roles are the smaller blast radius.
assign "Contributor"        "/subscriptions/${SUBSCRIPTION_ID}"
assign "Role Based Access Control Administrator" "/subscriptions/${SUBSCRIPTION_ID}"

# Read and write the state file. Scoped to the container, not the subscription.
assign "Storage Blob Data Contributor" \
    "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${STATE_RG}/providers/Microsoft.Storage/storageAccounts/${STATE_ACCOUNT}/blobServices/default/containers/${STATE_CONTAINER}"

echo
echo "  NOTE: 'Role Based Access Control Administrator' lets this principal grant"
echo "  roles. Constrain it in a real tenant with --condition so it can only"
echo "  assign the specific roles Terraform needs."

# ---------------------------------------------------------------------------
# 4. GitHub environment, variables and secret
# ---------------------------------------------------------------------------
say "GitHub environment: $ENVIRONMENT"

create_gh_environment() {
    local env_name="$1"
    gh api --method PUT "repos/${REPO}/environments/${env_name}" --silent 2>/dev/null \
        || echo "  (environment ${env_name} may already exist)"
    echo "  environment ${env_name}"

    gh variable set AZURE_CLIENT_ID       --env "$env_name" --repo "$REPO" --body "$APP_ID"
    gh variable set AZURE_TENANT_ID       --env "$env_name" --repo "$REPO" --body "$TENANT_ID"
    gh variable set AZURE_SUBSCRIPTION_ID --env "$env_name" --repo "$REPO" --body "$SUBSCRIPTION_ID"
    echo "  variables set"
}

create_gh_environment "$ENVIRONMENT"
if [[ "$ENVIRONMENT" == "prod" ]]; then
    # No required reviewers on prod-plan, by design: the approver has to be able
    # to see the plan before they are asked to approve the apply.
    create_gh_environment "prod-plan"
fi

# The database password. Generated here, stored in GitHub, and never printed -
# Terraform writes it to Key Vault, which is where anything else should read it.
if gh secret list --env "$ENVIRONMENT" --repo "$REPO" | grep -q '^DB_ADMIN_PASSWORD'; then
    echo "  DB_ADMIN_PASSWORD already set (leaving it alone)"
else
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | head -c 28)
    gh secret set DB_ADMIN_PASSWORD --env "$ENVIRONMENT" --repo "$REPO" --body "$DB_PASSWORD"
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        gh secret set DB_ADMIN_PASSWORD --env "prod-plan" --repo "$REPO" --body "$DB_PASSWORD"
    fi
    unset DB_PASSWORD
    echo "  DB_ADMIN_PASSWORD generated and stored"
fi

# ---------------------------------------------------------------------------
say "Done"

cat <<NEXT

Bootstrapped '$ENVIRONMENT' for $REPO.

  Client ID       $APP_ID
  Tenant ID       $TENANT_ID
  Subscription    $SUBSCRIPTION_ID
  State backend   $STATE_ACCOUNT/$STATE_CONTAINER/pulse-${ENVIRONMENT}.tfstate

Still to do by hand - these are policy decisions, not configuration:

  1. Required reviewers on the 'prod' environment:
       Settings -> Environments -> prod -> Required reviewers
     Without this, prod applies with no approval. The pipeline is built around
     that gate existing.

  2. First infrastructure deploy:
       Actions -> Deploy infrastructure -> Run workflow
         environment: $ENVIRONMENT
         apply: ticked

  3. After the first apply, publish the registry to the environment so the
     build job can find it:
       cd infrastructure/terraform
       terraform init -backend-config=backend-${ENVIRONMENT}.hcl
       gh variable set REGISTRY_LOGIN_SERVER --env $ENVIRONMENT --repo $REPO \\
         --body "\$(terraform output -raw registry_login_server)"

     And for prod, so it knows where to promote images FROM:
       gh variable set SOURCE_REGISTRY_LOGIN_SERVER --env prod --repo $REPO \\
         --body "<the dev registry login server>"

  4. Prod only - let the prod identity pull from the dev registry, so
     'az acr import' can promote an image rather than rebuild it:
       az role assignment create \\
         --assignee-object-id $SP_OBJECT_ID \\
         --assignee-principal-type ServicePrincipal \\
         --role AcrPull \\
         --scope <resource id of the DEV container registry>

Full runbook: docs/deployment.md
NEXT
