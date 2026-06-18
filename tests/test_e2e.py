#!/usr/bin/env python3
"""
test_e2e.py — Teste end-to-end do pipeline completo do Lab 4.

Fluxo verificado:
    1. Envia um log de erro conhecido via simulate_logs.py (cenario db-connection-failure).
    2. Faz polling no DynamoDB por ate 60s aguardando um novo incidente.
    3. Valida: incidente criado, log group correto, severidade valida, causa_raiz nao vazia.

Pode ser executado direto (python tests/test_e2e.py) ou via pytest.
"""

import os
import sys
import time

# Permite importar os modulos de src/.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_RAIZ, "src"))

from common import LOG_GROUP, tabela_dynamodb  # noqa: E402
from scenarios import CENARIOS  # noqa: E402
from simulate_logs import enviar_cenario  # noqa: E402
from common import cliente_logs  # noqa: E402

SEVERIDADES_VALIDAS = {"CRITICO", "ALTO", "MEDIO", "BAIXO"}
CENARIO = "db-connection-failure"
TIMEOUT_S = 60
INTERVALO_S = 5


def _ids_atuais() -> set:
    itens = tabela_dynamodb().scan(ProjectionExpression="incidentId").get("Items", [])
    return {i["incidentId"] for i in itens}


def test_pipeline_e2e():
    print(f"[E2E] Snapshot inicial de incidentes em {tabela_dynamodb().name}...")
    antes = _ids_atuais()
    print(f"[E2E] {len(antes)} incidente(s) pre-existente(s).")

    print(f"[E2E] Enviando cenario '{CENARIO}' para {LOG_GROUP}...")
    enviar_cenario(cliente_logs(), LOG_GROUP, CENARIO)

    print(f"[E2E] Aguardando novo incidente (timeout {TIMEOUT_S}s)...")
    novo_item = None
    deadline = time.time() + TIMEOUT_S
    while time.time() < deadline:
        time.sleep(INTERVALO_S)
        agora = _ids_atuais()
        novos = agora - antes
        if novos:
            novo_id = next(iter(novos))
            novo_item = tabela_dynamodb().get_item(Key={"incidentId": novo_id}).get("Item")
            break
        restante = int(deadline - time.time())
        print(f"[E2E]   ...sem incidente ainda ({restante}s restantes)")

    # Asserts
    assert novo_item is not None, "Nenhum incidente foi criado dentro do timeout"
    assert novo_item.get("logGroup") == LOG_GROUP, (
        f"Log group incorreto: {novo_item.get('logGroup')} != {LOG_GROUP}"
    )
    sev = novo_item.get("severity")
    assert sev in SEVERIDADES_VALIDAS, f"Severidade invalida: {sev}"
    causa = novo_item.get("causaRaiz", "")
    assert isinstance(causa, str) and causa.strip(), "causa_raiz vazia ou invalida"

    print(
        f"\nE2E test passed — incident {novo_item['incidentId']} "
        f"created with severity {sev}"
    )
    return novo_item


if __name__ == "__main__":
    try:
        test_pipeline_e2e()
    except AssertionError as exc:
        print(f"\n[E2E] FALHOU: {exc}", file=sys.stderr)
        sys.exit(1)
