variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "registry_name" {
  description = "Registry name: 5-50 lowercase alphanumeric characters, globally unique."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{5,50}$", var.registry_name))
    error_message = "registry_name must be 5-50 lowercase alphanumeric characters."
  }
}
variable "environment" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}
