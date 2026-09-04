# Production.
#
#   terraform init  -backend-config=backend-prod.hcl
#   terraform apply -var-file=environments/prod.tfvars
#
# Differences from dev, all deliberate:
#   * general-purpose (not burstable) Postgres - no noisy-neighbour throttling
#     halfway through a nightly warehouse build
#   * zone-redundant HA and geo-redundant backups
#   * auto-inflate on Event Hubs so a traffic spike is absorbed, not dropped
#   * 90-day log retention, 35-day database backups
#   * container apps never scale to zero - no cold start on the 8am dashboard
#   * alerting wired to a real inbox

project        = "pulse"
environment    = "prod"
location       = "uksouth"
location_short = "uks"
owner          = "data-platform"
cost_centre    = "analytics-prod"

db_sku_name   = "GP_Standard_D2s_v3"
db_storage_mb = 131072
# Doubles the compute bill. On, because a warehouse the business reports from
# should survive a zone failure.
db_high_availability = true

event_hub_throughput_units = 2
event_hub_retention_days   = 7

enable_container_apps = true
enable_databricks     = true

alert_email = "data-alerts@example.com"

tags = {
  auto_shutdown = "false"
  purpose       = "production"
  compliance    = "internal"
}
