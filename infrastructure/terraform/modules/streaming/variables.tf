variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "suffix" { type = string }
variable "environment" { type = string }
variable "throughput_units" {
  type    = number
  default = 1
}
variable "retention_days" {
  type    = number
  default = 1
}
variable "tags" {
  type    = map(string)
  default = {}
}
