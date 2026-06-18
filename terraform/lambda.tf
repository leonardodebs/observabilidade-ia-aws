# Lambdas — analyzer e incident-api

# ---------------------------------------------------------------------------
# Empacotamento do codigo (zip) via provider archive
# ---------------------------------------------------------------------------
data "archive_file" "analyzer" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/analyzer"
  output_path = "${path.module}/build/analyzer.zip"
}

data "archive_file" "api" {
  count       = var.criar_api ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../lambda/api"
  output_path = "${path.module}/build/api.zip"
}

# ---------------------------------------------------------------------------
# Dead Letter Queue do analyzer (eventos que falharam apos os retries)
# ---------------------------------------------------------------------------
resource "aws_sqs_queue" "analyzer_dlq" {
  name                      = "${var.prefixo}-analyzer-dlq"
  message_retention_seconds = 1209600 # 14 dias
}

# ---------------------------------------------------------------------------
# Lambda analyzer
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "analyzer" {
  function_name    = "${var.prefixo}-log-analyzer"
  role             = aws_iam_role.analyzer.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 60
  filename         = data.archive_file.analyzer.output_path
  source_code_hash = data.archive_file.analyzer.output_base64sha256

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      DYNAMODB_TABLE   = aws_dynamodb_table.incidentes.name
      SNS_TOPIC_ARN    = aws_sns_topic.incidentes_criticos.arn
      TTL_DIAS         = tostring(var.ttl_dias)
    }
  }

  # Eventos que falharem (apos os retries internos) vao para a DLQ.
  dead_letter_config {
    target_arn = aws_sqs_queue.analyzer_dlq.arn
  }
}

# Log group do analyzer (criado explicitamente para controlar a retencao)
resource "aws_cloudwatch_log_group" "analyzer" {
  name              = "/aws/lambda/${var.prefixo}-log-analyzer"
  retention_in_days = var.log_retention_dias
}

# Permite que o CloudWatch Logs (subscription filter) invoque o analyzer
resource "aws_lambda_permission" "logs_invoke" {
  statement_id  = "AllowCloudWatchLogsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analyzer.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "${aws_cloudwatch_log_group.app_simulation.arn}:*"
}

# ---------------------------------------------------------------------------
# Lambda incident-api (opcional) + Function URL
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "api" {
  count            = var.criar_api ? 1 : 0
  function_name    = "${var.prefixo}-incident-api"
  role             = aws_iam_role.api[0].arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  memory_size      = 256
  timeout          = 30
  filename         = data.archive_file.api[0].output_path
  source_code_hash = data.archive_file.api[0].output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.incidentes.name
    }
  }
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.criar_api ? 1 : 0
  name              = "/aws/lambda/${var.prefixo}-incident-api"
  retention_in_days = var.log_retention_dias
}

# Function URL com autenticacao IAM (SigV4). Sem API Gateway.
# Observacao: usamos AWS_IAM (e nao NONE) porque muitas contas corporativas
# bloqueiam Function URLs publicas via SCP. As requisicoes sao assinadas com
# SigV4 (ver src/api_client.py).
resource "aws_lambda_function_url" "api" {
  count              = var.criar_api ? 1 : 0
  function_name      = aws_lambda_function.api[0].function_name
  authorization_type = var.api_auth_type

  cors {
    allow_origins = ["*"]
    allow_methods = ["GET"]
  }
}

# Permissao publica de invocacao — criada somente quando auth = NONE.
resource "aws_lambda_permission" "api_url_publica" {
  count                  = var.criar_api && var.api_auth_type == "NONE" ? 1 : 0
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api[0].function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
