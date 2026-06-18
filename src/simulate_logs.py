#!/usr/bin/env python3
"""
simulate_logs.py — Gera eventos de log de erro realistas e os envia ao
CloudWatch Logs (/lab4/app-simulation), disparando o pipeline de analise.

Uso:
    python src/simulate_logs.py --scenario db-connection-failure
    python src/simulate_logs.py --scenario memory-leak
    python src/simulate_logs.py --scenario disk-full
    python src/simulate_logs.py --scenario auth-failure
    python src/simulate_logs.py --random --count 10
    python src/simulate_logs.py --list
"""

import argparse
import random
import sys
import time
import uuid

from botocore.exceptions import ClientError

from common import LOG_GROUP, REGIAO, cliente_logs
from scenarios import CENARIOS


def garantir_log_stream(logs, log_group: str, log_stream: str):
    """Cria o log stream (idempotente — ignora se ja existir)."""
    try:
        logs.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceAlreadyExistsException":
            raise


def enviar_cenario(logs, log_group: str, nome_cenario: str) -> str:
    """Envia o trecho de log de um cenario como um unico evento multilinha."""
    gerar = CENARIOS[nome_cenario]
    mensagem = gerar()

    # Um stream por execucao evita conflito de sequenceToken em paralelo.
    log_stream = f"sim-{nome_cenario}-{uuid.uuid4().hex[:8]}"
    garantir_log_stream(logs, log_group, log_stream)

    logs.put_log_events(
        logGroupName=log_group,
        logStreamName=log_stream,
        logEvents=[{"timestamp": int(time.time() * 1000), "message": mensagem}],
    )
    return log_stream


def main():
    parser = argparse.ArgumentParser(description="Simulador de logs de erro — Lab 4")
    parser.add_argument("--scenario", help="Nome do cenario a simular")
    parser.add_argument("--random", action="store_true", help="Envia cenarios aleatorios")
    parser.add_argument("--count", type=int, default=1, help="Quantidade (com --random)")
    parser.add_argument("--list", action="store_true", help="Lista os cenarios disponiveis")
    args = parser.parse_args()

    if args.list:
        print("Cenarios disponiveis:")
        for nome in CENARIOS:
            print(f"  - {nome}")
        return

    logs = cliente_logs()

    # Monta a lista de cenarios a enviar.
    if args.random:
        cenarios = [random.choice(list(CENARIOS)) for _ in range(max(1, args.count))]
    elif args.scenario:
        if args.scenario not in CENARIOS:
            print(f"Cenario invalido: {args.scenario}", file=sys.stderr)
            print(f"Disponiveis: {', '.join(CENARIOS)}", file=sys.stderr)
            sys.exit(1)
        cenarios = [args.scenario]
    else:
        parser.print_help()
        sys.exit(1)

    print(f"Enviando {len(cenarios)} evento(s) para {LOG_GROUP} ({REGIAO})\n")
    for i, nome in enumerate(cenarios, 1):
        stream = enviar_cenario(logs, LOG_GROUP, nome)
        print(f"  [{i}/{len(cenarios)}] {nome:24s} -> stream {stream}")
        # Pequena pausa entre eventos aleatorios para evitar throttling.
        if args.random and i < len(cenarios):
            time.sleep(1)

    print("\nPronto. O Lambda analyzer sera disparado em alguns segundos.")
    print("Acompanhe com: python src/watch.py  (ou make watch)")


if __name__ == "__main__":
    main()
