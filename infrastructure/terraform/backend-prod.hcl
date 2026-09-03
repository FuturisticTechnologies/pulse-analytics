# Backend configuration for the PROD state file.
#   terraform init -backend-config=backend-prod.hcl
#
# The key differs per environment. Sharing one state file between dev and prod
# means the first apply destroys the other environment - which is why the
# backend block in main.tf is deliberately empty and this cannot be forgotten.
resource_group_name  = "rg-pulse-tfstate"
storage_account_name = "stpulsetfstate"
container_name       = "tfstate"
key                  = "pulse-prod.tfstate"

# Entra ID auth, not a storage access key. The CI principal gets
# "Storage Blob Data Contributor" on the container; no key is stored anywhere.
use_azuread_auth = true
