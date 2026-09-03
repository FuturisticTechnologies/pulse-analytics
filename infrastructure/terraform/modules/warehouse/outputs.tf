output "server_fqdn" {
  description = "Set POSTGRES_HOST to this."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "server_name" {
  description = "Needed by the CI migration step to add and remove a firewall rule."
  value       = azurerm_postgresql_flexible_server.main.name
}

output "database_name" {
  value = azurerm_postgresql_flexible_server_database.warehouse.name
}

output "admin_username" {
  value = var.admin_username
}

output "connection_string" {
  description = <<-EOT
    libpq DSN, written to Key Vault by the root module and never an exposed
    output. sslmode=require because the server refuses anything else.
  EOT
  value = join(" ", [
    "host=${azurerm_postgresql_flexible_server.main.fqdn}",
    "port=5432",
    "dbname=${azurerm_postgresql_flexible_server_database.warehouse.name}",
    "user=${var.admin_username}",
    "password=${var.admin_password}",
    "sslmode=require",
  ])
  sensitive = true
}
