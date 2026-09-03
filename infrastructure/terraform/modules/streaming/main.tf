###############################################################################
# Module: streaming - Azure Event Hubs.
#
# Event Hubs exposes a Kafka-protocol endpoint, so streaming/bus.py connects to
# it with the SAME confluent-kafka client it uses against Redpanda locally.
# Only PULSE_KAFKA_BROKERS and the SASL credentials change. That is the entire
# reason the local demo is an honest rehearsal of production rather than a
# separate program that happens to look similar.
#
# One hub per pulse.* topic, partitioned by the key the producer already sets
# (customer_id for orders and activity, order_id for payments, product_id for
# inventory) so per-entity ordering is preserved.
###############################################################################

resource "azurerm_eventhub_namespace" "main" {
  name                = "evhns-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  # Standard is the cheapest tier that speaks the Kafka protocol - Basic does
  # not, and would force a client rewrite.
  sku                      = "Standard"
  capacity                 = var.throughput_units
  auto_inflate_enabled     = var.environment == "prod"
  maximum_throughput_units = var.environment == "prod" ? 10 : null
  minimum_tls_version      = "1.2"
  tags                     = var.tags
}

locals {
  # Partition counts sized to the local topic volumes: activity is ~12x orders.
  hubs = {
    "pulse.orders"            = { partitions = var.environment == "prod" ? 8 : 2 }
    "pulse.payments"          = { partitions = var.environment == "prod" ? 8 : 2 }
    "pulse.inventory"         = { partitions = var.environment == "prod" ? 4 : 2 }
    "pulse.customer_activity" = { partitions = var.environment == "prod" ? 16 : 4 }
  }
}

resource "azurerm_eventhub" "topics" {
  for_each = local.hubs

  name              = each.key
  namespace_id      = azurerm_eventhub_namespace.main.id
  partition_count   = each.value.partitions
  message_retention = var.retention_days
}

# One consumer group per downstream job. Sharing $Default between the warehouse
# loader and the alerting job would make them steal each other's offsets.
resource "azurerm_eventhub_consumer_group" "warehouse_loader" {
  for_each = azurerm_eventhub.topics

  name                = "pulse-analytics"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = each.value.name
  resource_group_name = var.resource_group_name
}

resource "azurerm_eventhub_consumer_group" "realtime_kpis" {
  for_each = azurerm_eventhub.topics

  name                = "pulse-realtime-kpis"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = each.value.name
  resource_group_name = var.resource_group_name
}

# Least privilege: the producer may only send, the consumer may only listen.
resource "azurerm_eventhub_namespace_authorization_rule" "producer" {
  name                = "producer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name

  listen = false
  send   = true
  manage = false
}

resource "azurerm_eventhub_namespace_authorization_rule" "consumer" {
  name                = "consumer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name

  listen = true
  send   = false
  manage = false
}
