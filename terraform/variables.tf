# Variaveis de entrada — Lab 4 Observabilidade com IA

variable "aws_region" {
  description = "Regiao AWS onde os recursos serao criados."
  type        = string
  default     = "us-west-2"
}

variable "ambiente" {
  description = "Nome do ambiente (usado em tags)."
  type        = string
  default     = "lab"
}

variable "prefixo" {
  description = "Prefixo aplicado aos nomes dos recursos."
  type        = string
  default     = "lab4"
}

variable "bedrock_model_id" {
  description = "ID do modelo Bedrock (Claude Haiku via inference profile)."
  type        = string
  default     = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "notification_email" {
  description = "E-mail que recebera notificacoes de incidentes CRITICO/ALTO via SNS."
  type        = string
}

variable "ttl_dias" {
  description = "Dias ate a expiracao automatica (TTL) dos incidentes no DynamoDB."
  type        = number
  default     = 30
}

variable "criar_api" {
  description = "Se true, cria o Lambda incident-api com Function URL."
  type        = bool
  default     = true
}

variable "api_auth_type" {
  description = "Tipo de autenticacao da Function URL: AWS_IAM (assinado SigV4) ou NONE (publico). Contas com SCP costumam bloquear NONE."
  type        = string
  default     = "AWS_IAM"

  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.api_auth_type)
    error_message = "api_auth_type deve ser AWS_IAM ou NONE."
  }
}

variable "log_retention_dias" {
  description = "Retencao dos log groups do CloudWatch (em dias)."
  type        = number
  default     = 7
}
