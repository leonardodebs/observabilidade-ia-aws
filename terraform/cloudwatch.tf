# CloudWatch Logs — grupo de simulacao e subscription filter

# Grupo de logs que recebe os eventos de teste (simulate_logs.py escreve aqui)
resource "aws_cloudwatch_log_group" "app_simulation" {
  name              = "/${var.prefixo}/app-simulation"
  retention_in_days = var.log_retention_dias
}

# Subscription Filter: encaminha eventos de erro para o Lambda analyzer.
# O padrao captura linhas contendo qualquer um dos termos abaixo.
resource "aws_cloudwatch_log_subscription_filter" "erros" {
  name            = "${var.prefixo}-erros-para-analyzer"
  log_group_name  = aws_cloudwatch_log_group.app_simulation.name
  filter_pattern  = "?ERROR ?CRITICAL ?Exception ?Traceback ?FATAL"
  destination_arn = aws_lambda_function.analyzer.arn

  # Garante que a permissao de invocacao exista antes do filtro.
  depends_on = [aws_lambda_permission.logs_invoke]
}
