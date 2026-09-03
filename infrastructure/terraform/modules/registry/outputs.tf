output "registry_id" {
  value = azurerm_container_registry.main.id
}

output "registry_name" {
  value = azurerm_container_registry.main.name
}

output "login_server" {
  description = "Set as the image prefix in the deploy workflow: <login_server>/pulse/dashboard:<sha>."
  value       = azurerm_container_registry.main.login_server
}
