# Versoes e provider — Lab 4 Observabilidade com IA
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Projeto    = "lab4-observabilidade-ia"
      Ambiente   = var.ambiente
      Gerenciado = "terraform"
    }
  }
}
