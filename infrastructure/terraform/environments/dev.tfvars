# Development: the cheapest configuration that still exercises every component.
#
#   terraform init  -backend-config=backend-dev.hcl
#   terraform apply -var-file=environments/dev.tfvars
#
# NOT here, by design:
#   db_admin_password  -> TF_VAR_db_admin_password (GitHub environment secret)
#   subscription_id    -> ARM_SUBSCRIPTION_ID      (GitHub environment variable)
#   image_tag          -> passed by CI as the git SHA

project        = "pulse"
environment    = "dev"
location       = "uksouth"
location_short = "uks"
owner          = "data-platform"
cost_centre    = "analytics"

# Burstable Postgres: ~GBP 11/month, plenty for the demo data volumes.
db_sku_name          = "B_Standard_B1ms"
db_storage_mb        = 32768
db_high_availability = false

# One throughput unit handles ~1000 events/s; the demo producer uses a fraction.
event_hub_throughput_units = 1
event_hub_retention_days   = 1

enable_container_apps = true
enable_databricks     = false # run the batch pipeline locally or in CI for dev

tags = {
  auto_shutdown = "true"
  purpose       = "development"
}
