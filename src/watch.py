#!/usr/bin/env python3
"""
watch.py — Monitor em tempo real de incidentes.

Faz polling do DynamoDB a cada 10s e exibe novos incidentes com a biblioteca
Rich (codificados por cor segundo a severidade, com score de confianca da IA).

Uso:
    python src/watch.py
    python src/watch.py --interval 5
"""

import argparse
import time
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.live import Live

from common import TABELA_INCIDENTES, tabela_dynamodb

console = Console()

# Estilo Rich por severidade.
ESTILO_SEV = {
    "CRITICO": "bold white on red",
    "ALTO": "bold red",
    "MEDIO": "bold yellow",
    "BAIXO": "cyan",
}


def carregar_incidentes(limite: int = 20):
    itens = tabela_dynamodb().scan().get("Items", [])
    itens.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return itens[:limite]


def montar_tabela(itens, novos: set):
    tabela = Table(
        title=f"Incidentes em tempo real — {TABELA_INCIDENTES}  "
        f"({datetime.now().strftime('%H:%M:%S')})",
        expand=True,
    )
    tabela.add_column("Severidade", justify="center", no_wrap=True)
    tabela.add_column("Quando", no_wrap=True)
    tabela.add_column("Conf.", justify="right", no_wrap=True)
    tabela.add_column("Categoria", no_wrap=True)
    tabela.add_column("Titulo", overflow="fold")

    for item in itens:
        sev = item.get("severity", "?")
        estilo = ESTILO_SEV.get(sev, "white")
        ts = item.get("timestamp", "")[:19].replace("T", " ")
        conf = float(item.get("confianca", 0))
        marcador = "[bold green]● NOVO[/] " if item.get("incidentId") in novos else ""
        tabela.add_row(
            f"[{estilo}] {sev} [/]",
            ts,
            f"{conf:.0%}",
            item.get("categoria", "-"),
            marcador + item.get("titulo", ""),
        )
    return tabela


def main():
    parser = argparse.ArgumentParser(description="Monitor de incidentes em tempo real")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo de polling (s)")
    args = parser.parse_args()

    console.print(
        f"[bold]Monitorando[/] {TABELA_INCIDENTES} a cada {args.interval}s. "
        "Pressione Ctrl+C para sair.\n"
    )

    vistos: set = set()
    try:
        with Live(console=console, refresh_per_second=2, screen=False) as live:
            while True:
                itens = carregar_incidentes()
                ids_atuais = {i.get("incidentId") for i in itens}
                novos = ids_atuais - vistos if vistos else set()
                live.update(montar_tabela(itens, novos))
                vistos = ids_atuais
                time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor encerrado.[/]")


if __name__ == "__main__":
    main()
