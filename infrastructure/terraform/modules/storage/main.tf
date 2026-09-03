###############################################################################
# Module: storage - the data lake.
#
# ADLS Gen2 (a storage account with hierarchical namespace on). The three
# medallion containers are the same three schemas the local warehouse uses, so
# a table is in the same conceptual place whichever backend is running.
###############################################################################

resource "azurerm_storage_account" "lake" {
  name                = var.storage_name
  resource_group_name = var.resource_group_name
  location            = var.location
  account_tier        = "Standard"
  # LRS in dev is a deliberate cost decision: the lake is rebuildable from the
  # source extracts, so paying for geo-redundancy on regenerable data is waste.
  account_replication_type = var.environment == "prod" ? "ZRS" : "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true # this is what makes it ADLS Gen2

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = var.environment != "prod" # prod uses Entra ID only

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = var.environment == "prod" ? 30 : 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "medallion" {
  for_each = toset(["bronze", "silver", "gold", "checkpoints", "exports"])

  name                  = each.key
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"
}

# Lifecycle management: bronze is the expensive container and the least often
# read after the first day, so it tiers down aggressively. Gold never tiers -
# it is what the dashboards query.
resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "bronze-tiering"
    enabled = true
    filters {
      prefix_match = ["bronze/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        # Modification time, not last-access time. Access-time tiering needs
        # `last_access_time_enabled` on the account, which bills for every read
        # - and bronze is written once and read by the nightly build, so its
        # age since writing is the honest signal anyway.
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 180
        delete_after_days_since_modification_greater_than          = var.environment == "prod" ? 1095 : 90
      }
      snapshot {
        delete_after_days_since_creation_greater_than = 30
      }
    }
  }

  rule {
    name    = "silver-tiering"
    enabled = true
    filters {
      prefix_match = ["silver/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 90
      }
    }
  }
}
