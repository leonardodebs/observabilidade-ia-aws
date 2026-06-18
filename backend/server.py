"""
backend/server.py — Proxy FastAPI para o front-end React.
==========================================================
O navegador nao consegue assinar requisicoes SigV4 para a Lambda Function URL
(autenticacao AWS_IAM). Este proxy roda localmente, usa as credenciais AWS da
maquina para assinar as chamadas e expoe os mesmos endpoints de forma simples
para o front (sem CORS/credenciais no browser).

Fluxo:
    React (Vite :5173) --/api/*--> FastAPI (:8000) --SigV4--> Lambda Function URL --> DynamoDB

Endpoints expostos:
    GET /api/health             -> status do proxy e descoberta da API
    GET /api/incidents          -> ultimos incidentes (com ?severity= opcional)
    GET /api/incidents/{id}      -> detalhe de um incidente
    GET /api/stats              -> estatisticas agregadas
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from functools import lru_cache

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

REGIAO = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or "us-west-2"

app = FastAPI(title="Observabilidade IA — Proxy", version="1.0.0")


# ---------------------------------------------------------------------------
# Descoberta da URL da Lambda API (via output do Terraform ou env API_URL)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def obter_api_url() -> str:
    if os.environ.get("API_URL"):
        return os.environ["API_URL"].rstrip("/")
    # Procura o diretorio terraform relativo a este arquivo.
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        saida = subprocess.check_output(
            ["terraform", f"-chdir={os.path.join(raiz, 'terraform')}",
             "output", "-raw", "api_function_url"],
            stderr=subprocess.DEVNULL,
        )
        return saida.decode().strip().rstrip("/")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Chamada assinada (SigV4) a Lambda Function URL
# ---------------------------------------------------------------------------
def chamar_api(caminho: str) -> dict:
    base = obter_api_url()
    if not base:
        raise HTTPException(
            status_code=503,
            detail="API nao encontrada. Rode 'make tf-apply' ou defina API_URL.",
        )
    url = base + ("" if caminho.startswith("/") else "/") + caminho

    sessao = boto3.Session()
    creds = sessao.get_credentials()
    if creds is None:
        raise HTTPException(status_code=500, detail="Credenciais AWS nao configuradas.")
    frozen = creds.get_frozen_credentials()

    req = AWSRequest(method="GET", url=url)
    SigV4Auth(frozen, "lambda", REGIAO).add_auth(req)

    pedido = urllib.request.Request(url, headers=dict(req.headers), method="GET")
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        corpo = exc.read().decode(errors="ignore")
        raise HTTPException(status_code=exc.code, detail=f"Erro na Lambda API: {corpo}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao acessar a API: {exc}")


# ---------------------------------------------------------------------------
# Endpoints do proxy
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    url = obter_api_url()
    return {
        "status": "ok" if url else "sem_api",
        "api_url": url or None,
        "regiao": REGIAO,
    }


@app.get("/api/incidents")
def incidents(severity: str | None = None):
    caminho = "/incidents"
    if severity:
        caminho += f"?severity={severity.upper()}"
    return JSONResponse(chamar_api(caminho))


@app.get("/api/incidents/{incident_id}")
def incident(incident_id: str):
    return JSONResponse(chamar_api(f"/incidents/{incident_id}"))


@app.get("/api/stats")
def stats():
    return JSONResponse(chamar_api("/stats"))


if __name__ == "__main__":
    import uvicorn

    porta = int(os.environ.get("PROXY_PORT", "8000"))
    print(f"Proxy em http://localhost:{porta}  (API alvo: {obter_api_url() or 'NAO ENCONTRADA'})")
    uvicorn.run(app, host="0.0.0.0", port=porta)
