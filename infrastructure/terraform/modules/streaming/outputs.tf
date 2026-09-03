output "namespace_name" {
  value = azurerm_eventhub_namespace.main.name
}

output "kafka_bootstrap_server" {
  description = <<-EOT
    Set PULSE_KAFKA_BROKERS to this. The client also needs SASL_SSL with
    username '$ConnectionString' and the connection string as the password -
    that is the only Event Hubs-specific configuration in the whole platform.
  EOT
  value       = "${azurerm_eventhub_namespace.main.name}.servicebus.windows.net:9093"
}

output "hub_names" {
  value = sort([for h in azurerm_eventhub.topics : h.name])
}

output "connection_string" {
  description = "Consumer connection string; written to Key Vault by the root module."
  value       = azurerm_eventhub_namespace_authorization_rule.consumer.primary_connection_string
  sensitive   = true
}

output "producer_connection_string" {
  value     = azurerm_eventhub_namespace_authorization_rule.producer.primary_connection_string
  sensitive = true
}
