"""
Lambda API — Lab 4 Observabilidade com IA
=========================================
Expoe os incidentes via Lambda Function URL (sem API Gateway).

Rotas suportadas:
    GET /incidents               -> ultimos 20 incidentes (ordenados por timestamp desc)
    GET /incidents?severity=X    -> filtra por severidade usando o GSI severityIndex
    GET /incidents/{id}          -> detalhes de um unico incidente
    GET /stats                   -> estatisticas agregadas

Todos os comentarios estao em pt-BR.
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "lab4-incidents")
SEVERITY_INDEX = "severityIndex"

dynamodb = boto3.resource("dynamodb")
tabela = dynamodb.Table(DYNAMODB_TABLE)

SEVERIDADES_VALIDAS = {"CRITICO", "ALTO", "MEDIO", "BAIXO"}


# ---------------------------------------------------------------------------
# Utilitarios de resposta HTTP
# ---------------------------------------------------------------------------
class _JSONEncoder(json.JSONEncoder):
    """Serializa Decimal (DynamoDB) como int/float."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 else int(o)
        return super().default(o)


def resposta(status: int, corpo) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(corpo, ensure_ascii=False, cls=_JSONEncoder),
    }


# ---------------------------------------------------------------------------
# Acesso a dados
# ---------------------------------------------------------------------------
def listar_incidentes(limite: int = 20) -> list:
    """Retorna os incidentes mais recentes (scan + ordenacao por timestamp desc)."""
    itens = tabela.scan().get("Items", [])
    itens.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return itens[:limite]


def listar_por_severidade(severidade: str, limite: int = 20) -> list:
    """Consulta o GSI severityIndex filtrando por severidade (mais eficiente)."""
    resp = tabela.query(
        IndexName=SEVERITY_INDEX,
        KeyConditionExpression=Key("severity").eq(severidade),
        ScanIndexForward=False,  # timestamp desc
        Limit=limite,
    )
    return resp.get("Items", [])


def buscar_incidente(incident_id: str):
    """Busca um unico incidente pela chave primaria."""
    resp = tabela.get_item(Key={"incidentId": incident_id})
    return resp.get("Item")


def calcular_stats() -> dict:
    """Agrega estatisticas: total, por severidade, confianca media e ultimas 24h."""
    itens = tabela.scan().get("Items", [])
    total = len(itens)
    por_severidade = Counter(i.get("severity", "DESCONHECIDO") for i in itens)

    confiancas = [float(i.get("confianca", 0)) for i in itens if i.get("confianca") is not None]
    confianca_media = round(sum(confiancas) / len(confiancas), 3) if confiancas else 0.0

    limite_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    ultimas_24h = sum(
        1
        for i in itens
        if i.get("timestamp", "") >= limite_24h.isoformat()
    )

    # Garante presenca de todas as severidades no resultado.
    by_severity = {sev: por_severidade.get(sev, 0) for sev in sorted(SEVERIDADES_VALIDAS)}
    return {
        "total": total,
        "by_severity": by_severity,
        "avg_confidence": confianca_media,
        "last_24h": ultimas_24h,
    }


# ---------------------------------------------------------------------------
# Roteamento (Lambda Function URL — payload v2)
# ---------------------------------------------------------------------------
def handler(event, context):
    # Function URL usa o formato de payload HTTP API v2.
    contexto_http = event.get("requestContext", {}).get("http", {})
    metodo = contexto_http.get("method", "GET")
    caminho = (event.get("rawPath") or contexto_http.get("path") or "/").rstrip("/") or "/"
    params = event.get("queryStringParameters") or {}

    if metodo != "GET":
        return resposta(405, {"erro": "Metodo nao permitido"})

    try:
        # GET /stats
        if caminho == "/stats":
            return resposta(200, calcular_stats())

        # GET /incidents/{id}
        if caminho.startswith("/incidents/"):
            incident_id = caminho.split("/incidents/", 1)[1]
            item = buscar_incidente(incident_id)
            if not item:
                return resposta(404, {"erro": "Incidente nao encontrado", "id": incident_id})
            return resposta(200, item)

        # GET /incidents  (com filtro opcional ?severity=)
        if caminho in ("/incidents", "/"):
            severidade = (params.get("severity") or "").upper()
            if severidade:
                if severidade not in SEVERIDADES_VALIDAS:
                    return resposta(
                        400,
                        {"erro": "Severidade invalida", "validas": sorted(SEVERIDADES_VALIDAS)},
                    )
                itens = listar_por_severidade(severidade)
            else:
                itens = listar_incidentes()
            return resposta(200, {"total": len(itens), "incidents": itens})

        return resposta(404, {"erro": "Rota nao encontrada", "caminho": caminho})

    except Exception as exc:  # noqa: BLE001 — superficie de API, retorna erro tratado
        print(json.dumps({"nivel": "ERROR", "erro": str(exc), "caminho": caminho}))
        return resposta(500, {"erro": "Erro interno", "detalhe": str(exc)})
