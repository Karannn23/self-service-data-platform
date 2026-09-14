terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "project_rg" {
  name     = "rg-self-service-data-platform"
  location = "Central India"
}

resource "azurerm_storage_account" "project_storage" {
  name                     = "ssdpstorage${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.project_rg.name
  location                 = azurerm_resource_group.project_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    project = "self-service-data-platform"
    purpose = "portfolio-project"
  }
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}