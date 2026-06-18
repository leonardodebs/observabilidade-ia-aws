#!/usr/bin/env python3
"""
query_incidents.py — CLI para visualizar incidentes persistidos no DynamoDB.

Uso:
    python src/query_incidents.py                     -> ultimos 10
    python src/query_incidents.py --severity CRITICO  -> filtra por severidade (GSI)
    python src/query_incidents.py --json              -> saida em JSON
    python src/query_incidents.py --stats             -> estatisticas
    python src/query_incidents.py --id <incidentId>   -> detalhes de um incidente
"""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from boto3.dynamodb.conditions import Key

from common import SEVERITY_INDEX, tabela_dynamodb

SEVERIDADES_VALIDAS = ["CRITICO", "ALTO", "MEDIO", "BAIXO"]

# Cores ANSI por severidade.
CORES = {
    "CRITICO": "\033[1;37;41m",  # branco sobre vermelho
    "ALTO": "\033[1;31m",        # vermelho
    "MEDIO": "\033[1;33m",       # amarelo
    "BAIXO": "\033[1;36m",       # ciano
}
RESET = "\033[0m"


def _json_default(o):
    if isinstance(o, Decimal):
        return float(o) if o % 1 else int(o)
    return str(o)


def listar(limite: int):
    itens = tabela_dynamodb().scan().get("Items", [])
    itens.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return itens[:limite]


def listar_por_severidade(severidade: str, limite: int):
    resp = tabela_dynamodb().query(
        IndexName=SEVERITY_INDEX,
        KeyConditionExpression=Key("severity").eq(severidade),
        ScanIndexForward=False,
        Limit=limite,
    )
    return resp.get("Items", [])


def buscar_por_id(incident_id: str):
    return tabela_dynamodb().get_item(Key={"incidentId": incident_id}).get("Item")


def stats():
    itens = tabela_dynamodb().scan().get("Items", [])
    por_sev = Counter(i.get("severity", "?") for i in itens)
    confs = [float(i.get("confianca", 0)) for i in itens]
    media = round(sum(confs) / len(confs), 3) if confs else 0.0
    limite_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    ult24 = sum(1 for i in itens if i.get("timestamp", "") >= limite_24h)
    return {
        "total": len(itens),
        "by_severity": {s: por_sev.get(s, 0) for s in SEVERIDADES_VALIDAS},
        "avg_confidence": media,
        "last_24h": ult24,
    }


def imprimir_incidente(item: dict, detalhado: bool = False):
    sev = item.get("severity", "?")
    cor = CORES.get(sev, "")
    ts = item.get("timestamp", "")[:19].replace("T", " ")
    conf = float(item.get("confianca", 0))
    print(f"{cor} {sev:8s} {RESET} {ts}  conf={conf:.0%}  {item.get('titulo', '')}")
    print(f"          id: {item.get('incidentId', '')}  | {item.get('categoria', '')}"
          f" | {item.get('componenteAfetado', '')}")
    print(f"          causa: {item.get('causaRaiz', '')}")
    if detalhado:
        print(f"          impacto: {item.get('impacto', '')}")
        acoes = item.get("acoesRecomendadas", [])
        if acoes:
            print("          acoes recomendadas:")
            for a in acoes:
                print(f"            - {a}")
        print(f"          log group: {item.get('logGroup', '')}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Consulta de incidentes — Lab 4")
    parser.add_argument("--severity", help="Filtra por severidade (CRITICO/ALTO/MEDIO/BAIXO)")
    parser.add_argument("--limit", type=int, default=10, help="Quantidade de incidentes")
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    parser.add_argument("--stats", action="store_true", help="Mostra estatisticas")
    parser.add_argument("--id", help="Detalhes de um incidente especifico")
    args = parser.parse_args()

    if args.stats:
        s = stats()
        if args.json:
            print(json.dumps(s, indent=2, ensure_ascii=False))
        else:
            print("=== Estatisticas de Incidentes ===")
            print(f"Total: {s['total']}   |   Ultimas 24h: {s['last_24h']}")
            print(f"Confianca media da IA: {s['avg_confidence']:.0%}")
            print("Por severidade:")
            for sev, n in s["by_severity"].items():
                cor = CORES.get(sev, "")
                print(f"  {cor} {sev:8s} {RESET} {n}")
        return

    if args.id:
        item = buscar_por_id(args.id)
        if not item:
            print(f"Incidente nao encontrado: {args.id}")
            return
        if args.json:
            print(json.dumps(item, indent=2, ensure_ascii=False, default=_json_default))
        else:
            imprimir_incidente(item, detalhado=True)
        return

    if args.severity:
        sev = args.severity.upper()
        itens = listar_por_severidade(sev, args.limit)
    else:
        itens = listar(args.limit)

    if args.json:
        print(json.dumps(itens, indent=2, ensure_ascii=False, default=_json_default))
        return

    if not itens:
        print("Nenhum incidente encontrado.")
        return

    print(f"=== {len(itens)} incidente(s) mais recente(s) ===\n")
    for item in itens:
        imprimir_incidente(item)


if __name__ == "__main__":
    main()
