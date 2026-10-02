terraform {
  required_version = ">= 1.8.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.region
  # Make every AWS provider operation depend on the validated release opt-in.
  allowed_account_ids = var.aws_deployment_enabled ? null : ["000000000000"]
}
