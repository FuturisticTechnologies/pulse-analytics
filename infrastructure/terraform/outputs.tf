###############################################################################
# Outputs.
#
# Deliberately NO connection strings or keys. Every secret goes to Key Vault;
# what comes out here is only what a human or a CI job needs to find things.
# An output marked `sensitive` still lands in plaintext in the state file, so
# the safest secret output is the one that does not exist.
#
# The deploy-application workflow reads these with `terraform output -json`
# rather than deriving names by convention - Terraform state is the single
# source of truth for what exists, and convention-derived names break silently
# the first time someone changes the naming scheme.
###############################################################################

output "resource_group_name" {
  description = "Resource group holding the whole platform."
  value       = azurerm_resource_group.main.name
}

output "environment" {
  description = "Which environment this state describes - guards against a mis-targeted deploy."
  value       = var.environment
}

# --- storage -----------------------------------------------------------------
output "storage_account_name" {
  description = "ADLS Gen2 account - the bronze/silver/gold lake."
  value       = module.storage.storage_account_name
}

output "lake_containers" {
  description = "Medallion containers created in the lake."
  value       = module.storage.container_names
}

# --- registry ----------------------------------------------------------------
output "registry_login_server" {
  description = "Image prefix for the build job: <login_server>/<repository>:<sha>."
  value       = module.registry.login_server
}

output "registry_name" {
  description = "Registry name, for `az acr login`."
  value       = module.registry.registry_name
}

output "image_repository" {
  value = var.image_repository
}

output "deployed_image_tag" {
  description = "The tag currently deployed - what a rollback rolls back FROM."
  value       = var.image_tag
}

# --- streaming ---------------------------------------------------------------
output "event_hub_namespace" {
  description = "Event Hubs namespace (Kafka-protocol endpoint)."
  value       = module.streaming.namespace_name
}

output "kafka_bootstrap_server" {
  description = "Set PULSE_KAFKA_BROKERS to this - the existing client needs nothing else."
  value       = module.streaming.kafka_bootstrap_server
}

output "event_hub_topics" {
  description = "Event hubs, one per pulse.* topic."
  value       = module.streaming.hub_names
}

# --- warehouse ---------------------------------------------------------------
output "postgres_fqdn" {
  description = "Set POSTGRES_HOST to this."
  value       = module.warehouse.server_fqdn
}

output "postgres_server_name" {
  description = "Server name - the migration step uses it to add and remove its firewall rule."
  value       = module.warehouse.server_name
}

output "postgres_database" {
  value = module.warehouse.database_name
}

output "postgres_admin_username" {
  value = module.warehouse.admin_username
}

# --- identity and secrets ----------------------------------------------------
output "key_vault_name" {
  description = "Key Vault holding every connection string."
  value       = azurerm_key_vault.main.name
}

output "app_identity_client_id" {
  description = "Managed identity the container apps run as."
  value       = azurerm_user_assigned_identity.app.client_id
}

# --- compute -----------------------------------------------------------------
output "dashboard_url" {
  description = "Public URL of the Streamlit dashboard."
  value = var.enable_container_apps ? (
    "https://${azurerm_container_app.dashboard[0].ingress[0].fqdn}"
  ) : null
}

output "api_url" {
  description = "Public URL of the real-time API. The deploy smoke test hits /health here."
  value = var.enable_container_apps ? (
    "https://${azurerm_container_app.api[0].ingress[0].fqdn}"
  ) : null
}

output "dashboard_app_name" {
  value = var.enable_container_apps ? azurerm_container_app.dashboard[0].name : null
}

output "api_app_name" {
  value = var.enable_container_apps ? azurerm_container_app.api[0].name : null
}

output "databricks_workspace_url" {
  description = "Databricks workspace running the batch pipeline."
  value       = var.enable_databricks ? azurerm_databricks_workspace.main[0].workspace_url : null
}

output "application_insights_name" {
  description = "Application Insights resource for runtime telemetry."
  value       = azurerm_application_insights.main.name
}

# --- convenience -------------------------------------------------------------
output "environment_variables" {
  description = <<-EOT
    Paste these into the job or container that runs the pipeline. The password
    is referenced from Key Vault by name, never inlined.
  EOT
  value = {
    PULSE_DB_ENGINE      = "postgres"
    PULSE_STREAM_BACKEND = "kafka"
    PULSE_KAFKA_BROKERS  = module.streaming.kafka_bootstrap_server
    POSTGRES_HOST        = module.warehouse.server_fqdn
    POSTGRES_PORT        = "5432"
    POSTGRES_DB          = module.warehouse.database_name
    POSTGRES_USER        = module.warehouse.admin_username
    POSTGRES_SSLMODE     = "require"
    PULSE_KEY_VAULT      = azurerm_key_vault.main.name
    PULSE_LAKE_ACCOUNT   = module.storage.storage_account_name
  }
}
