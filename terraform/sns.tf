# SNS — topico de notificacao para incidentes CRITICO/ALTO

resource "aws_sns_topic" "incidentes_criticos" {
  name = "${var.prefixo}-critical-incidents"
}

# Inscricao por e-mail. Atencao: a AWS envia um e-mail de confirmacao que
# precisa ser aceito manualmente antes de comecar a receber notificacoes.
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.incidentes_criticos.arn
  protocol  = "email"
  endpoint  = var.notification_email
}
