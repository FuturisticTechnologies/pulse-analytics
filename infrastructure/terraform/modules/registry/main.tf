###############################################################################
# Module: registry - Azure Container Registry.
#
# The deployment pipeline builds one image and promotes that exact image
# through dev and then prod. That is only possible with a registry both
# environments can pull from, which is what this exists for.
#
# ACR rather than GHCR: Container Apps can pull from ACR with a managed
# identity, so there is no registry password stored anywhere - not in Terraform
# state, not in a GitHub secret, not on the container app. A cross-cloud
# registry would need a credential, and the whole point of the OIDC setup in
# the workflows is that nothing long-lived is stored.
###############################################################################

resource "azurerm_container_registry" "main" {
  name                = var.registry_name
  resource_group_name = var.resource_group_name
  location            = var.location

  # Basic is ~GBP 4/month and enough for this: the tier buys storage quota,
  # geo-replication and private endpoints, none of which are needed to hold a
  # handful of image tags.
  sku = var.environment == "prod" ? "Standard" : "Basic"

  # Admin user is the password-based path. It stays off precisely so nobody can
  # take the shortcut of putting a registry password in a secret.
  admin_enabled = false

  tags = var.tags
}

# Keep the last N untagged manifests only. Without this an ACR accumulates
# every layer of every build forever, and the storage quota is the first thing
# to fail - at 2am, during a deploy.
resource "azurerm_container_registry_task" "purge_untagged" {
  count = var.environment == "prod" ? 1 : 0

  name                  = "purge-untagged"
  container_registry_id = azurerm_container_registry.main.id
  platform {
    os = "Linux"
  }

  encoded_step {
    task_content = base64encode(<<-YAML
      version: v1.1.0
      steps:
        - cmd: acr purge --filter '.*:.*' --untagged --ago 30d --keep 10
          disableWorkingDirectoryOverride: true
          timeout: 3600
    YAML
    )
  }

  timer_trigger {
    name     = "weekly"
    schedule = "0 4 * * 0" # Sunday 04:00
    enabled  = true
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
