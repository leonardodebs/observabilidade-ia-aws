#!/usr/bin/env python3
"""
api_client.py — Cliente para a API de incidentes (Lambda Function URL).

A Function URL usa autenticacao AWS_IAM, entao as requisicoes precisam ser
assinadas com SigV4. Este cliente faz isso usando as credenciais locais
(botocore), sem dependencias externas alem de boto3/botocore.

Uso:
    python src/api_client.py /incidents
    python src/api_client.py "/incidents?severity=CRITICO"
    python src/api_client.py /stats
    python src/api_client.py /incidents/<id>

A URL da API e lida do output do Terraform (ou da variavel de ambiente API_URL).
"""

import json
import subprocess
import sys
from urllib.parse import urlparse

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib.request

from common import REGIAO


def obter_api_url() -> str:
    """Le a URL da API do output do Terraform."""
    import os

    if os.environ.get("API_URL"):
        return os.environ["API_URL"].rstrip("/")
    try:
        saida = subprocess.check_output(
            ["terraform", "-chdir=terraform", "output", "-raw", "api_function_url"],
            stderr=subprocess.DEVNULL,
        )
        return saida.decode().strip().rstrip("/")
    except Exception:  # noqa: BLE001
        print("Defina API_URL ou rode 'terraform apply' antes.", file=sys.stderr)
        sys.exit(1)


def chamar(caminho: str) -> dict:
    """Faz GET assinado com SigV4 para a Function URL."""
    base = obter_api_url()
    url = base + ("" if caminho.startswith("/") else "/") + caminho

    # Assinatura SigV4 para o servico 'lambda' (Function URL).
    sessao = boto3.Session()
    credenciais = sessao.get_credentials().get_frozen_credentials()
    requisicao = AWSRequest(method="GET", url=url)
    SigV4Auth(credenciais, "lambda", REGIAO).add_auth(requisicao)

    req = urllib.request.Request(url, headers=dict(requisicao.headers), method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else "/incidents"
    resultado = chamar(caminho)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
