# Outputs — ARNs e nomes dos recursos criados

output "log_group_simulacao" {
  description = "Nome do log group que recebe os eventos de teste."
  value       = aws_cloudwatch_log_group.app_simulation.name
}

output "analyzer_function_name" {
  description = "Nome do Lambda analyzer."
  value       = aws_lambda_function.analyzer.function_name
}

output "analyzer_function_arn" {
  description = "ARN do Lambda analyzer."
  value       = aws_lambda_function.analyzer.arn
}

output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de incidentes."
  value       = aws_dynamodb_table.incidentes.name
}

output "dynamodb_table_arn" {
  description = "ARN da tabela DynamoDB de incidentes."
  value       = aws_dynamodb_table.incidentes.arn
}

output "sns_topic_arn" {
  description = "ARN do topico SNS de incidentes criticos."
  value       = aws_sns_topic.incidentes_criticos.arn
}

output "dlq_url" {
  description = "URL da Dead Letter Queue do analyzer."
  value       = aws_sqs_queue.analyzer_dlq.url
}

output "bedrock_model_id" {
  description = "ID do modelo Bedrock utilizado."
  value       = var.bedrock_model_id
}

output "api_function_url" {
  description = "URL publica da API de incidentes (Function URL)."
  value       = var.criar_api ? aws_lambda_function_url.api[0].function_url : "API desabilitada (criar_api=false)"
}
