"""
Lambda Analyzer — Lab 4 Observabilidade com IA
================================================
Recebe eventos de log do CloudWatch (via Subscription Filter), analisa a causa
raiz com o Amazon Bedrock (Claude Haiku), persiste o incidente no DynamoDB e
notifica via SNS quando a severidade for CRITICO ou ALTO.

Fluxo:
    CloudWatch Logs -> (gzip+base64) -> este Lambda
        -> Bedrock (analise de causa raiz)
        -> DynamoDB (persistencia do incidente, com chaves do GSI)
        -> SNS (notificacao se CRITICO/ALTO)

Todos os comentarios estao em pt-BR. Logs sao emitidos em JSON estruturado
para facilitar consultas no CloudWatch Logs Insights.
"""

import base64
import gzip
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Configuracao via variaveis de ambiente (injetadas pelo Terraform)
# ---------------------------------------------------------------------------
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "lab4-incidents")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")
# Severidades que disparam notificacao imediata via SNS.
NOTIFY_SEVERITIES = {"CRITICO", "ALTO"}
# TTL dos incidentes no DynamoDB (em dias) — economiza custo de armazenamento.
TTL_DIAS = int(os.environ.get("TTL_DIAS", "30"))
# Numero maximo de tentativas ao chamar o Bedrock.
BEDROCK_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Clientes AWS reaproveitados entre invocacoes (boa pratica de performance)
# ---------------------------------------------------------------------------
_bedrock_cfg = Config(
    region_name=os.environ.get("AWS_REGION", "us-west-2"),
    read_timeout=45,
    connect_timeout=10,
    retries={"max_attempts": 0},  # controlamos o retry manualmente (backoff exp.)
)
bedrock = boto3.client("bedrock-runtime", config=_bedrock_cfg)
dynamodb = boto3.resource("dynamodb")
tabela = dynamodb.Table(DYNAMODB_TABLE)
sns = boto3.client("sns")


# ---------------------------------------------------------------------------
# Logging estruturado (JSON) — pronto para CloudWatch Logs Insights
# ---------------------------------------------------------------------------
def log(nivel: str, mensagem: str, **campos):
    """Emite uma linha de log em JSON para facilitar consultas no Insights."""
    registro = {
        "nivel": nivel,
        "mensagem": mensagem,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **campos,
    }
    print(json.dumps(registro, ensure_ascii=False, default=str))


# ---------------------------------------------------------------------------
# Prompt do Bedrock — saida estruturada em JSON
# ---------------------------------------------------------------------------
PROMPT_SISTEMA = (
    "Voce e um Site Reliability Engineer (SRE) senior especialista em analise "
    "de incidentes de producao. Voce recebe trechos de logs de erro e produz "
    "uma analise tecnica de causa raiz, objetiva e acionavel, em portugues do "
    "Brasil. Responda SEMPRE e SOMENTE com um objeto JSON valido, sem texto "
    "adicional, sem markdown e sem cercas de codigo."
)


def montar_prompt_usuario(log_group: str, eventos_texto: str) -> str:
    """Monta o prompt do usuario com os logs e o schema de saida esperado."""
    return f"""Analise os logs de erro abaixo, originados do grupo de logs '{log_group}'.

=== LOGS ===
{eventos_texto}
=== FIM DOS LOGS ===

Produza um JSON EXATAMENTE com este schema (todas as chaves obrigatorias):
{{
  "titulo": "resumo curto do incidente (max 80 caracteres)",
  "severidade": "CRITICO | ALTO | MEDIO | BAIXO",
  "categoria": "BANCO_DADOS | MEMORIA | DISCO | AUTENTICACAO | REDE | APLICACAO | OUTRO",
  "causa_raiz": "explicacao tecnica da causa raiz provavel (1-3 frases)",
  "componente_afetado": "servico/componente provavelmente afetado",
  "acoes_recomendadas": ["acao 1", "acao 2", "acao 3"],
  "impacto": "descricao do impacto no usuario/negocio",
  "confianca": 0.0
}}

Regras de severidade:
- CRITICO: indisponibilidade total, perda de dados, falha em cascata.
- ALTO: degradacao grave, falha de componente critico, risco iminente.
- MEDIO: erro recorrente sem indisponibilidade total.
- BAIXO: erro isolado/transitorio.

O campo "confianca" e um numero entre 0.0 e 1.0 indicando sua confianca na analise.
Responda apenas com o JSON."""


# ---------------------------------------------------------------------------
# Invocacao do Bedrock com retry e backoff exponencial
# ---------------------------------------------------------------------------
def invocar_bedrock(log_group: str, eventos_texto: str) -> dict:
    """Chama o Bedrock com ate BEDROCK_MAX_RETRIES tentativas (backoff exp.)."""
    corpo = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.2,
        "system": PROMPT_SISTEMA,
        "messages": [
            {"role": "user", "content": montar_prompt_usuario(log_group, eventos_texto)}
        ],
    }

    ultima_excecao = None
    for tentativa in range(1, BEDROCK_MAX_RETRIES + 1):
        try:
            resposta = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(corpo),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(resposta["body"].read())
            texto = payload["content"][0]["text"]
            uso = payload.get("usage", {})
            log(
                "INFO",
                "Bedrock respondeu",
                tentativa=tentativa,
                input_tokens=uso.get("input_tokens"),
                output_tokens=uso.get("output_tokens"),
            )
            return _extrair_json(texto)
        except (ClientError, KeyError, json.JSONDecodeError) as exc:
            ultima_excecao = exc
            espera = 2 ** tentativa  # 2s, 4s, 8s
            log(
                "WARN",
                "Falha ao invocar Bedrock; aplicando backoff",
                tentativa=tentativa,
                espera_segundos=espera,
                erro=str(exc),
            )
            if tentativa < BEDROCK_MAX_RETRIES:
                time.sleep(espera)

    # Esgotadas as tentativas: relanca para acionar a DLQ.
    log("ERROR", "Bedrock falhou apos todas as tentativas", erro=str(ultima_excecao))
    raise RuntimeError(f"Bedrock indisponivel: {ultima_excecao}")


def _extrair_json(texto: str) -> dict:
    """Extrai o objeto JSON da resposta do modelo, tolerante a cercas de codigo."""
    texto = texto.strip()
    if texto.startswith("```"):
        # Remove cercas ```json ... ```
        texto = texto.split("```", 2)[1]
        if texto.startswith("json"):
            texto = texto[4:]
        texto = texto.strip().rstrip("`").strip()
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise json.JSONDecodeError("JSON nao encontrado na resposta", texto, 0)
    return json.loads(texto[inicio : fim + 1])


# ---------------------------------------------------------------------------
# Persistencia no DynamoDB (com chaves do GSI: severity + timestamp)
# ---------------------------------------------------------------------------
def salvar_incidente(analise: dict, log_group: str, eventos_texto: str) -> dict:
    """Persiste o incidente no DynamoDB, incluindo as chaves do GSI severityIndex."""
    agora = datetime.now(timezone.utc)
    incident_id = str(uuid.uuid4())
    severidade = str(analise.get("severidade", "MEDIO")).upper()

    item = {
        "incidentId": incident_id,
        # Chaves do GSI 'severityIndex' (HASH=severity, RANGE=timestamp).
        "severity": severidade,
        "timestamp": agora.isoformat(),
        # Atributos da analise.
        "titulo": analise.get("titulo", "Incidente sem titulo"),
        "categoria": analise.get("categoria", "OUTRO"),
        "causaRaiz": analise.get("causa_raiz", ""),
        "componenteAfetado": analise.get("componente_afetado", ""),
        "acoesRecomendadas": analise.get("acoes_recomendadas", []),
        "impacto": analise.get("impacto", ""),
        "confianca": _to_decimal(analise.get("confianca", 0.0)),
        "logGroup": log_group,
        "logTrecho": eventos_texto[:4000],  # limita tamanho armazenado
        "criadoEm": agora.isoformat(),
        # TTL para expiracao automatica (economia de custo).
        "ttl": int((agora + timedelta(days=TTL_DIAS)).timestamp()),
    }
    tabela.put_item(Item=item)
    log("INFO", "Incidente persistido", incidentId=incident_id, severity=severidade)
    return item


def _to_decimal(valor):
    """DynamoDB nao aceita float; converte para Decimal via string."""
    from decimal import Decimal

    try:
        return Decimal(str(round(float(valor), 4)))
    except (ValueError, TypeError):
        return Decimal("0")


# ---------------------------------------------------------------------------
# Notificacao via SNS
# ---------------------------------------------------------------------------
def notificar_sns(item: dict):
    """Publica no SNS quando a severidade for CRITICO/ALTO."""
    severidade = item["severity"]
    if severidade not in NOTIFY_SEVERITIES or not SNS_TOPIC_ARN:
        return

    acoes = "\n".join(f"  - {a}" for a in item.get("acoesRecomendadas", []))
    assunto = f"[{severidade}] {item['titulo']}"[:100]
    mensagem = f"""INCIDENTE DETECTADO — {severidade}

Titulo: {item['titulo']}
Categoria: {item['categoria']}
Componente: {item['componenteAfetado']}
Confianca da IA: {float(item['confianca']):.0%}

Causa raiz:
{item['causaRaiz']}

Impacto:
{item['impacto']}

Acoes recomendadas:
{acoes}

ID do incidente: {item['incidentId']}
Origem (log group): {item['logGroup']}
Detectado em: {item['timestamp']}
"""
    sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=assunto, Message=mensagem)
    log("INFO", "Notificacao SNS enviada", incidentId=item["incidentId"], severity=severidade)


# ---------------------------------------------------------------------------
# Decodificacao do payload do CloudWatch Logs
# ---------------------------------------------------------------------------
def decodificar_evento(event: dict) -> dict:
    """Descomprime o payload (gzip+base64) enviado pelo Subscription Filter."""
    dados = event["awslogs"]["data"]
    comprimido = base64.b64decode(dados)
    descomprimido = gzip.decompress(comprimido)
    return json.loads(descomprimido)


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------
def handler(event, context):
    inicio = time.time()
    try:
        dados_log = decodificar_evento(event)
    except (KeyError, ValueError) as exc:
        log("ERROR", "Payload de log invalido", erro=str(exc))
        raise

    log_group = dados_log.get("logGroup", "desconhecido")
    eventos = dados_log.get("logEvents", [])
    if not eventos:
        log("WARN", "Nenhum evento de log recebido; ignorando")
        return {"status": "vazio"}

    # Concatena as mensagens de log para enviar ao modelo.
    eventos_texto = "\n".join(e.get("message", "") for e in eventos).strip()
    log(
        "INFO",
        "Analisando eventos de log",
        logGroup=log_group,
        quantidadeEventos=len(eventos),
        tamanhoTexto=len(eventos_texto),
    )

    # 1) Analise de causa raiz com o Bedrock.
    analise = invocar_bedrock(log_group, eventos_texto)

    # 2) Persistencia do incidente.
    item = salvar_incidente(analise, log_group, eventos_texto)

    # 3) Notificacao (se aplicavel).
    notificar_sns(item)

    duracao_ms = int((time.time() - inicio) * 1000)
    log(
        "INFO",
        "Processamento concluido",
        incidentId=item["incidentId"],
        severity=item["severity"],
        duracaoMs=duracao_ms,
    )
    return {
        "status": "ok",
        "incidentId": item["incidentId"],
        "severity": item["severity"],
    }
