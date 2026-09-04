output "storage_account_id" {
  value = azurerm_storage_account.lake.id
}

output "storage_account_name" {
  value = azurerm_storage_account.lake.name
}

output "container_names" {
  value = sort([for c in azurerm_storage_container.medallion : c.name])
}

output "dfs_endpoint" {
  description = "abfss:// endpoint Databricks and Synapse mount."
  value       = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "primary_connection_string" {
  description = "Written straight to Key Vault by the root module - never printed."
  value       = azurerm_storage_account.lake.primary_connection_string
  sensitive   = true
}
