"""
Utilitarios compartilhados pelos scripts do Lab 4 (src/).
Le configuracao do ambiente (.env) e expoe clientes boto3 e nomes de recursos.
"""

import os
from pathlib import Path

import boto3

# Carrega .env da raiz do projeto, se existir (sem depender de libs externas).
_RAIZ = Path(__file__).resolve().parent.parent


def _carregar_env():
    arquivo = _RAIZ / ".env"
    if not arquivo.exists():
        return
    for linha in arquivo.read_text().splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip())


_carregar_env()

# Nomes de recursos (devem casar com o prefixo do Terraform: "lab4").
PREFIXO = os.environ.get("PREFIXO", "lab4")
REGIAO = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-west-2"
LOG_GROUP = os.environ.get("LOG_GROUP", f"/{PREFIXO}/app-simulation")
TABELA_INCIDENTES = os.environ.get("DYNAMODB_TABLE", f"{PREFIXO}-incidents")
SEVERITY_INDEX = "severityIndex"


def cliente_logs():
    return boto3.client("logs", region_name=REGIAO)


def tabela_dynamodb():
    return boto3.resource("dynamodb", region_name=REGIAO).Table(TABELA_INCIDENTES)
