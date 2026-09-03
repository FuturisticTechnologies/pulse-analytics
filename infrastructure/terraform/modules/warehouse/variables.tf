variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "suffix" { type = string }
variable "name_suffix" {
  description = "Random suffix - PostgreSQL Flexible Server names are DNS names and must be globally unique."
  type        = string
}
variable "environment" { type = string }

variable "admin_username" {
  description = "PostgreSQL administrator login."
  type        = string
}

variable "admin_password" {
  description = <<-EOT
    PostgreSQL administrator password. NEVER put this in a committed .tfvars.
    CI supplies it from a GitHub environment secret as TF_VAR_db_admin_password.
  EOT
  type        = string
  sensitive   = true
}

variable "sku_name" {
  description = <<-EOT
    Flexible Server SKU.
      B_Standard_B1ms      burstable, ~GBP 11/month  - dev
      GP_Standard_D2s_v3   general purpose, 2 vCPU   - prod
    Burstable SKUs cannot do high availability; see enable_high_availability.
  EOT
  type        = string
  default     = "B_Standard_B1ms"
}

variable "storage_mb" {
  description = "Allocated storage. Can be grown in place, never shrunk."
  type        = number
  default     = 32768
}

variable "enable_high_availability" {
  description = <<-EOT
    Zone-redundant HA. Roughly DOUBLES the compute bill, and is unavailable on
    burstable SKUs - so it is opt-in rather than derived from `environment`.
  EOT
  type        = bool
  default     = false
}

variable "allowed_ip_ranges" {
  description = <<-EOT
    IP ranges permitted to reach the database. Deliberately empty by default:
    an operator must make an explicit decision to open it, and there is no way
    to inherit a 0.0.0.0/0 rule from this module by accident.
  EOT
  type = list(object({
    name     = string
    start_ip = string
    end_ip   = string
  }))
  default = []
}

variable "log_analytics_workspace_id" {
  description = "Workspace for server diagnostics. Empty disables the setting."
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
