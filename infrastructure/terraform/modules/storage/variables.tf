variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "storage_name" {
  description = "Storage account name: lowercase alphanumeric, max 24 characters."
  type        = string
}
variable "environment" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}
