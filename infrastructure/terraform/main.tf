###############################################################################
# PulseAnalytics on Azure
#
# The local stack (DuckDB + file-based event bus, or Postgres + Redpanda in
# docker) and this Azure deployment run the SAME code. Nothing in etl/,
# analytics/ or streaming/ changes between them - only environment variables.
# That is the property this whole configuration exists to preserve:
#
#   local                          Azure
#   ------------------------------ ------------------------------------------
#   data/raw/*.csv                 ADLS Gen2, container `bronze`
#   postgres:16-alpine (docker)    Azure Database for PostgreSQL Flexible 16
#   Redpanda (Kafka protocol)      Event Hubs (Kafka protocol - same client)
#   python -m etl.pipeline         Databricks job running the same module
#   Streamlit + FastAPI            two Container Apps from one image
#   dashboards/powerbi/*           Power BI Service, same model
#
# Deployed by .github/workflows/deploy-infrastructure.yml. See
# docs/deployment.md for the bootstrap and the runbook.
#
# Cost note: nothing here is free. The defaults are the smallest tier that
# actually works, and `environment = "dev"` picks burstable/consumption
# everywhere it is available. See README.md in this folder for the estimate.
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # PARTIAL backend configuration: deliberately empty.
  #
  # The state key must differ per environment or dev and prod share one state
  # file and the first `apply` destroys the other environment. Leaving it empty
  # here means it is impossible to run Terraform without saying which
  # environment you mean:
  #
  #     terraform init -backend-config=backend-dev.hcl
  #     terraform init -backend-config=backend-prod.hcl
  #
  # A default would be a footgun with the safety off.
  backend "azurerm" {}
}

provider "azurerm" {
  # subscription_id comes from ARM_SUBSCRIPTION_ID, set by the workflow from a
  # GitHub environment variable - so the same configuration targets a different
  # subscription per environment without an edit.
  subscription_id = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy = false # never silently destroy secrets
    }
    resource_group {
      # Refuse to delete a resource group that still contains something
      # Terraform does not know about.
      prevent_deletion_if_contains_resources = true
    }
  }
}

# ---------------------------------------------------------------------------
# Naming and tagging
#
# One place that decides what everything is called. Consistent names are what
# make a cost report readable six months later.
# ---------------------------------------------------------------------------
locals {
  suffix = "${var.project}-${var.environment}-${var.location_short}"

  # Storage account and registry names allow no hyphens and have tight length
  # limits, so they are built separately from the readable suffix.
  storage_name  = substr(replace("st${var.project}${var.environment}${random_string.suffix.result}", "-", ""), 0, 24)
  registry_name = substr(replace("cr${var.project}${var.environment}${random_string.suffix.result}", "-", ""), 0, 50)

  tags = merge(var.tags, {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
    cost_centre = var.cost_centre
    owner       = var.owner
    # Set by CI so any resource can be traced back to the commit that made it.
    deployed_from = var.git_sha
  })
}

resource "random_string" "suffix" {
  length  = 5
  special = false
  upper   = false
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.suffix}"
  location = var.location
  tags     = local.tags
}

# ---------------------------------------------------------------------------
# Observability first - other modules send diagnostics to it
# ---------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "other"
  tags                = local.tags
}

# ---------------------------------------------------------------------------
# Modules - one per architectural layer, matching the local stack one-for-one
# ---------------------------------------------------------------------------
module "storage" {
  source = "./modules/storage"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  storage_name        = local.storage_name
  environment         = var.environment
  tags                = local.tags
}

module "registry" {
  source = "./modules/registry"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  registry_name       = local.registry_name
  environment         = var.environment
  tags                = local.tags
}

module "streaming" {
  source = "./modules/streaming"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  suffix              = local.suffix
  environment         = var.environment
  throughput_units    = var.event_hub_throughput_units
  retention_days      = var.event_hub_retention_days
  tags                = local.tags
}

module "warehouse" {
  source = "./modules/warehouse"

  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  suffix                     = local.suffix
  name_suffix                = random_string.suffix.result
  environment                = var.environment
  admin_username             = var.db_admin_username
  admin_password             = var.db_admin_password
  sku_name                   = var.db_sku_name
  storage_mb                 = var.db_storage_mb
  enable_high_availability   = var.db_high_availability
  allowed_ip_ranges          = var.db_allowed_ip_ranges
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# ---------------------------------------------------------------------------
# Workload identity
#
# ONE user-assigned identity that the container apps run as. User-assigned
# rather than system-assigned because of an ordering problem that bites every
# first deployment: a system-assigned identity does not exist until the
# container app is created, but the app needs AcrPull *before* it can pull the
# image to start. Creating the identity first breaks the cycle.
# ---------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.suffix}-app"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "app_acr_pull" {
  scope                = module.registry.registry_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_role_assignment" "app_lake_reader" {
  scope                = module.storage.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# ---------------------------------------------------------------------------
# Secrets
#
# Nothing that is a secret is ever an output of this configuration, and no
# connection string is ever written to a tfvars file that could be committed.
# ---------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${substr(local.suffix, 0, 12)}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = var.environment == "prod"
  soft_delete_retention_days = 7
  rbac_authorization_enabled = true
  tags                       = local.tags
}

# The deploying principal needs to be able to write the secrets below. Without
# this the very first apply fails with a 403 that is easy to misread as a
# Terraform bug.
resource "azurerm_role_assignment" "deployer_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_key_vault_secret" "event_hub_connection" {
  name         = "event-hub-connection"
  value        = module.streaming.connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_key_vault]
}

resource "azurerm_key_vault_secret" "database_connection" {
  name         = "database-connection"
  value        = module.warehouse.connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_key_vault]
}

resource "azurerm_key_vault_secret" "database_password" {
  name         = "database-password"
  value        = var.db_admin_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_key_vault]
}

resource "azurerm_key_vault_secret" "storage_connection" {
  name         = "storage-connection"
  value        = module.storage.primary_connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_key_vault]
}

# ---------------------------------------------------------------------------
# Compute: Container Apps for the dashboard and the API
# ---------------------------------------------------------------------------
resource "azurerm_container_app_environment" "main" {
  count = var.enable_container_apps ? 1 : 0

  name                       = "cae-${local.suffix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

locals {
  # Both apps run the SAME image and differ only by command - exactly as they
  # do in docker-compose. One image means one build, one scan, one promotion.
  container_image = "${module.registry.login_server}/${var.image_repository}:${var.image_tag}"

  app_environment = {
    PULSE_DB_ENGINE      = "postgres"
    PULSE_STREAM_BACKEND = "kafka"
    PULSE_KAFKA_BROKERS  = module.streaming.kafka_bootstrap_server
    POSTGRES_HOST        = module.warehouse.server_fqdn
    POSTGRES_PORT        = "5432"
    POSTGRES_DB          = module.warehouse.database_name
    POSTGRES_USER        = var.db_admin_username
    POSTGRES_SSLMODE     = "require"
    PULSE_LOG_LEVEL      = var.environment == "prod" ? "INFO" : "DEBUG"
    PULSE_ENVIRONMENT    = var.environment
  }
}

resource "azurerm_container_app" "dashboard" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "ca-${local.suffix}-dashboard"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = module.registry.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  secret {
    name                = "database-password"
    key_vault_secret_id = azurerm_key_vault_secret.database_password.versionless_id
    identity            = azurerm_user_assigned_identity.app.id
  }

  template {
    # Scale to zero out of hours in dev; at least one replica in prod so the
    # first visitor of the morning does not wait for a cold start.
    min_replicas = var.environment == "prod" ? 1 : 0
    max_replicas = 3

    container {
      name   = "dashboard"
      image  = local.container_image
      cpu    = 0.5
      memory = "1Gi"

      command = ["streamlit", "run", "dashboards/streamlit/app.py",
      "--server.address", "0.0.0.0", "--server.port", "8501"]

      dynamic "env" {
        for_each = local.app_environment
        content {
          name  = env.key
          value = env.value
        }
      }

      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "database-password"
      }

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      # Streamlit's own health endpoint. Without a probe, a container that
      # started but cannot reach the database still counts as healthy and
      # serves errors to users.
      liveness_probe {
        transport               = "HTTP"
        port                    = 8501
        path                    = "/_stcore/health"
        initial_delay           = 15
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8501
        path                    = "/_stcore/health"
        interval_seconds        = 10
        failure_count_threshold = 3
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8501
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.app_acr_pull]
}

resource "azurerm_container_app" "api" {
  count = var.enable_container_apps ? 1 : 0

  name                         = "ca-${local.suffix}-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main[0].id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = module.registry.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  secret {
    name                = "database-password"
    key_vault_secret_id = azurerm_key_vault_secret.database_password.versionless_id
    identity            = azurerm_user_assigned_identity.app.id
  }

  template {
    min_replicas = var.environment == "prod" ? 1 : 0
    max_replicas = 5

    container {
      name   = "api"
      image  = local.container_image
      cpu    = 0.25
      memory = "0.5Gi"

      command = ["uvicorn", "streaming.processors.realtime_api:app",
      "--host", "0.0.0.0", "--port", "8000"]

      dynamic "env" {
        for_each = local.app_environment
        content {
          name  = env.key
          value = env.value
        }
      }

      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "database-password"
      }

      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.main.connection_string
      }

      # /health is the endpoint the deploy workflow smoke-tests, and it checks
      # the database connection - so a green probe means more than "the process
      # is running".
      liveness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        initial_delay           = 10
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        interval_seconds        = 10
        failure_count_threshold = 3
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.app_acr_pull]
}

# ---------------------------------------------------------------------------
# Databricks - runs the batch pipeline
# ---------------------------------------------------------------------------
resource "azurerm_databricks_workspace" "main" {
  count = var.enable_databricks ? 1 : 0

  name                = "dbw-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  # "standard" is enough for the batch job; "premium" buys Unity Catalog and
  # table ACLs, which is what a production deployment needs and dev does not.
  sku  = var.environment == "prod" ? "premium" : "standard"
  tags = local.tags
}

# ---------------------------------------------------------------------------
# Alerting - the pipeline failing silently is the failure mode that costs money
# ---------------------------------------------------------------------------
resource "azurerm_monitor_action_group" "main" {
  count = var.alert_email == "" ? 0 : 1

  name                = "ag-${local.suffix}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "pulse"
  tags                = local.tags

  email_receiver {
    name          = "data-team"
    email_address = var.alert_email
  }
}

# A container app whose revision fails to become healthy is a failed deploy
# that the pipeline may already have reported as green.
resource "azurerm_monitor_metric_alert" "api_failures" {
  count = var.alert_email == "" || !var.enable_container_apps ? 0 : 1

  name                = "alert-${local.suffix}-api-5xx"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.api[0].id]
  description         = "The real-time API is returning server errors."
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 10

    dimension {
      name     = "statusCodeCategory"
      operator = "Include"
      values   = ["5xx"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }

  tags = local.tags
}
