###############################################################################
# Inputs.
#
# Every variable has a default that produces the CHEAPEST working deployment,
# so `terraform apply` with no tfvars is safe to run and safe to forget about.
# Per-environment values live in environments/{dev,prod}.tfvars; the two
# secrets (database password, subscription) come from the CI environment.
###############################################################################

variable "subscription_id" {
  description = <<-EOT
    Target subscription. Supplied by CI from a GitHub *environment* variable, so
    dev and prod can live in different subscriptions without editing anything.
    Locally, export ARM_SUBSCRIPTION_ID instead and leave this null.
  EOT
  type        = string
  default     = null
}

variable "project" {
  description = "Short project name; used in every resource name."
  type        = string
  default     = "pulse"

  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.project))
    error_message = "project must be 3-12 lowercase alphanumeric characters (Azure storage naming)."
  }
}

variable "environment" {
  description = "dev | test | prod. Selects SKUs, retention and scale-to-zero."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: dev, test, prod."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "uksouth"
}

variable "location_short" {
  description = "Region abbreviation used in resource names."
  type        = string
  default     = "uks"
}

variable "owner" {
  description = "Team or person accountable for these resources."
  type        = string
  default     = "data-platform"
}

variable "cost_centre" {
  description = "Cost centre tag - what makes the monthly bill attributable."
  type        = string
  default     = "analytics"
}

variable "git_sha" {
  description = <<-EOT
    Commit that produced this deployment, stamped onto every resource as a tag.
    Set by CI. Its value is what turns "when did this change?" from an
    archaeology exercise into one `az resource show`.
  EOT
  type        = string
  default     = "local"
}

variable "tags" {
  description = "Extra tags merged into the standard set."
  type        = map(string)
  default     = {}
}

# --- Container image ---------------------------------------------------------
variable "image_repository" {
  description = "Repository path inside the registry."
  type        = string
  default     = "pulse/platform"
}

variable "image_tag" {
  description = <<-EOT
    Image tag to run. CI passes the git SHA - never `latest`.

    `latest` makes a deployment unreproducible and a rollback impossible: two
    apply runs a week apart would silently deploy different code from identical
    configuration. Pinning to a SHA is what makes the rollback input on the
    deploy workflow actually work.
  EOT
  type        = string
  default     = "bootstrap"
}

# --- Event Hubs (the Kafka-protocol event bus) -------------------------------
variable "event_hub_throughput_units" {
  description = <<-EOT
    Throughput units. One TU is 1 MB/s in, 2 MB/s out, ~1000 events/s.
    The demo producer at 8 orders/s needs a small fraction of one.
  EOT
  type        = number
  default     = 1

  validation {
    condition     = var.event_hub_throughput_units >= 1 && var.event_hub_throughput_units <= 20
    error_message = "throughput units must be between 1 and 20."
  }
}

variable "event_hub_retention_days" {
  description = "How long an event stays replayable. 1 day on Standard; 7 with a capacity add-on."
  type        = number
  default     = 1
}

# --- Warehouse (PostgreSQL Flexible Server) ----------------------------------
variable "db_sku_name" {
  description = <<-EOT
    PostgreSQL Flexible Server SKU.
      B_Standard_B1ms      burstable, ~GBP 11/month - dev
      GP_Standard_D2s_v3   2 vCPU general purpose   - prod
  EOT
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  description = "Allocated storage. Can be grown in place, never shrunk."
  type        = number
  default     = 32768
}

variable "db_high_availability" {
  description = <<-EOT
    Zone-redundant HA. Roughly DOUBLES the compute bill and is unavailable on
    burstable SKUs, so it is an explicit opt-in rather than derived from
    `environment` - nobody should turn on a second database by accident.
  EOT
  type        = bool
  default     = false
}

variable "db_admin_username" {
  description = "PostgreSQL administrator login."
  type        = string
  default     = "pulseadmin"
}

variable "db_admin_password" {
  description = <<-EOT
    PostgreSQL administrator password. NEVER put this in a .tfvars file that is
    committed. CI supplies it from a GitHub environment secret:

        TF_VAR_db_admin_password: $${{ secrets.DB_ADMIN_PASSWORD }}

    Locally:
        export TF_VAR_db_admin_password="$(openssl rand -base64 24)"
  EOT
  type        = string
  sensitive   = true
}

variable "db_allowed_ip_ranges" {
  description = <<-EOT
    Developer IP ranges permitted to reach the database. Deliberately empty by
    default: an operator must make an explicit decision to open it, and there
    is no way to accidentally inherit a 0.0.0.0/0 rule.

    CI does not use this - it adds and removes its own runner IP around the
    migration step.
  EOT
  type = list(object({
    name     = string
    start_ip = string
    end_ip   = string
  }))
  default = []
}

# --- Compute -----------------------------------------------------------------
variable "enable_databricks" {
  description = "Create a Databricks workspace for the batch pipeline."
  type        = bool
  default     = false
}

variable "enable_container_apps" {
  description = "Host the dashboard and the real-time API on Container Apps."
  type        = bool
  default     = true
}

# --- Alerting ----------------------------------------------------------------
variable "alert_email" {
  description = "Where pipeline and API alerts go. Empty disables alerting."
  type        = string
  default     = ""
}
