# IAM — papeis e politicas dos Lambdas

data "aws_caller_identity" "atual" {}
data "aws_region" "atual" {}

# ---------------------------------------------------------------------------
# Politica de confianca (assume role) compartilhada pelos Lambdas
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ===========================================================================
# Papel do Lambda analyzer
# ===========================================================================
resource "aws_iam_role" "analyzer" {
  name               = "${var.prefixo}-log-analyzer-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "analyzer" {
  # Bedrock — invocar o modelo Claude Haiku (foundation model + inference profile)
  statement {
    sid     = "BedrockInvoke"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:*::foundation-model/*",
      "arn:aws:bedrock:*:${data.aws_caller_identity.atual.account_id}:inference-profile/*",
    ]
  }

  # DynamoDB — gravar e consultar incidentes (tabela + GSI)
  statement {
    sid = "DynamoDBWrite"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.incidentes.arn,
      "${aws_dynamodb_table.incidentes.arn}/index/*",
    ]
  }

  # SNS — publicar notificacoes
  statement {
    sid       = "SNSPublish"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.incidentes_criticos.arn]
  }

  # SQS — enviar para a Dead Letter Queue
  statement {
    sid       = "SQSDeadLetter"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.analyzer_dlq.arn]
  }

  # CloudWatch Logs — escrita dos proprios logs do Lambda
  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.atual.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "analyzer" {
  name   = "${var.prefixo}-analyzer-policy"
  role   = aws_iam_role.analyzer.id
  policy = data.aws_iam_policy_document.analyzer.json
}

# ===========================================================================
# Papel do Lambda incident-api
# ===========================================================================
resource "aws_iam_role" "api" {
  count              = var.criar_api ? 1 : 0
  name               = "${var.prefixo}-incident-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "api" {
  statement {
    sid = "DynamoDBRead"
    actions = [
      "dynamodb:Scan",
      "dynamodb:Query",
      "dynamodb:GetItem",
    ]
    resources = [
      aws_dynamodb_table.incidentes.arn,
      "${aws_dynamodb_table.incidentes.arn}/index/*",
    ]
  }

  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.atual.account_id}:*"]
  }
}

resource "aws_iam_role_policy" "api" {
  count  = var.criar_api ? 1 : 0
  name   = "${var.prefixo}-api-policy"
  role   = aws_iam_role.api[0].id
  policy = data.aws_iam_policy_document.api.json
}
