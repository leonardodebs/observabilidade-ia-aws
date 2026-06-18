# DynamoDB — tabela de incidentes
# Chave primaria: incidentId (String)
# GSI severityIndex: consulta por severidade ordenada por timestamp
# TTL: atributo 'ttl' para expiracao automatica (economia de custo)

resource "aws_dynamodb_table" "incidentes" {
  name         = "${var.prefixo}-incidents"
  billing_mode = "PAY_PER_REQUEST" # on-demand: ideal para lab (paga por uso)
  hash_key     = "incidentId"

  attribute {
    name = "incidentId"
    type = "S"
  }

  # Atributos usados pelo GSI severityIndex.
  attribute {
    name = "severity"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "severityIndex"
    hash_key        = "severity"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false # desabilitado no lab para reduzir custo
  }
}
