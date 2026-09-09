###############################################################################
# Module: warehouse - Azure Database for PostgreSQL Flexible Server.
#
# PostgreSQL, not Azure SQL, for one decisive reason: it is what the
# application actually speaks. `pulse/db.py` supports exactly two engines -
# DuckDB and PostgreSQL - so provisioning Azure SQL would create a database the
# platform cannot connect to, and the "same code runs locally and on Azure"
# claim would be false at the only point it matters.
#
# This also makes the local rehearsal genuine: docker-compose runs
# postgres:16-alpine, this runs PostgreSQL 16, and the SQL in database/ is the
# same portable subset in both.
#
# Not Synapse: that is the right answer past roughly a terabyte, or when MPP
# genuinely helps the query shapes. Below that it is a large bill for a
# warehouse a single well-indexed server serves faster. The gold layer is
# already a star schema, so the migration stays a DDL change and a bulk copy.
###############################################################################

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-${var.suffix}-${var.name_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  version             = "16"

  administrator_login    = var.admin_username
  administrator_password = var.admin_password

  sku_name   = var.sku_name
  storage_mb = var.storage_mb

  backup_retention_days        = var.environment == "prod" ? 35 : 7
  geo_redundant_backup_enabled = var.environment == "prod"

  # Public access with a deny-by-default firewall. Turning this off on Flexible
  # Server is not a flag - it requires a delegated subnet and private DNS, which
  # is the documented next step in the README rather than something to half-do
  # here. `require_secure_transport` below means nothing crosses the wire in
  # clear text either way.
  public_network_access_enabled = true

  # HA doubles the bill, so it is opt-in and only prod turns it on. Burstable
  # (B-series) SKUs cannot do HA at all, which is why this is a dynamic block
  # rather than a conditional attribute.
  dynamic "high_availability" {
    for_each = var.enable_high_availability ? [1] : []
    content {
      mode = "ZoneRedundant"
    }
  }

  lifecycle {
    ignore_changes = [
      # Azure picks a zone at creation. Letting Terraform see drift here would
      # propose destroying and recreating the database on every plan.
      zone,
      high_availability[0].standby_availability_zone,
    ]
  }

  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_database" "warehouse" {
  name      = "pulse"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  # C collation so ORDER BY produces the same sequence as the DuckDB run and
  # the docker-compose Postgres, which is initdb'd with --locale=C.
  collation = "C"

  lifecycle {
    prevent_destroy = false # dev is torn down routinely; see destroy workflow
  }
}

# ---------------------------------------------------------------------------
# Server configuration
# ---------------------------------------------------------------------------
resource "azurerm_postgresql_flexible_server_configuration" "require_ssl" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "ON"
}

# The warehouse build is a small number of large statements, not many small
# ones. A higher work_mem is what keeps the star-schema joins in memory.
resource "azurerm_postgresql_flexible_server_configuration" "work_mem" {
  name      = "work_mem"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = var.environment == "prod" ? "65536" : "16384" # KB
}

# Log anything slower than 3 seconds. The pipeline's own timings live in
# ops.pipeline_runs; this catches what the database thinks is slow.
resource "azurerm_postgresql_flexible_server_configuration" "log_min_duration" {
  name      = "log_min_duration_statement"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "3000"
}

# ---------------------------------------------------------------------------
# Firewall
#
# Deny by default. `allowed_ip_ranges` is an empty list, so an operator has to
# make an active decision to open the database to a network, and there is no
# way to inherit a 0.0.0.0/0 rule from this module by accident.
#
# CI adds its own runner IP for the duration of a migration and removes it
# afterwards - see .github/workflows/deploy-application.yml.
# ---------------------------------------------------------------------------
resource "azurerm_postgresql_flexible_server_firewall_rule" "allowed" {
  for_each = { for rule in var.allowed_ip_ranges : rule.name => rule }

  name             = each.value.name
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = each.value.start_ip
  end_ip_address   = each.value.end_ip
}

# Lets Container Apps and Databricks reach the server. 0.0.0.0-0.0.0.0 is
# Azure's internal sentinel for "Azure services", NOT a wildcard.
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
resource "azurerm_monitor_diagnostic_setting" "postgres" {
  count = var.log_analytics_workspace_id == "" ? 0 : 1

  name                       = "diag-postgres"
  target_resource_id         = azurerm_postgresql_flexible_server.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "PostgreSQLLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
