# Makefile — Lab 4 Observabilidade com IA
# Atalhos para operar o pipeline completo.

TF      := terraform -chdir=terraform
# Usa o Python do venv (.venv) se existir; caso contrario, o python3 do sistema.
PY      := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
S       ?= db-connection-failure   # cenario padrao para `make simulate`
COUNT   ?= 10                       # quantidade padrao para `make simulate-random`
P       ?= /incidents              # caminho padrao para `make api`

.PHONY: help
help:  ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Infraestrutura
# ---------------------------------------------------------------------------
.PHONY: tf-init
tf-init:  ## Inicializa o Terraform
	$(TF) init

.PHONY: tf-plan
tf-plan:  ## Mostra o plano do Terraform
	$(TF) plan

.PHONY: tf-apply
tf-apply:  ## Cria/atualiza a infraestrutura na AWS
	$(TF) apply -auto-approve

.PHONY: tf-destroy
tf-destroy:  ## Destroi toda a infraestrutura
	$(TF) destroy -auto-approve

.PHONY: outputs
outputs:  ## Mostra os outputs do Terraform
	$(TF) output

# ---------------------------------------------------------------------------
# Dependencias locais
# ---------------------------------------------------------------------------
.PHONY: deps
deps:  ## Instala as dependencias Python locais
	$(PY) -m pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Operacao do pipeline
# ---------------------------------------------------------------------------
.PHONY: simulate
simulate:  ## Simula um cenario (uso: make simulate S=memory-leak)
	$(PY) src/simulate_logs.py --scenario $(S)

.PHONY: simulate-random
simulate-random:  ## Envia N logs aleatorios (uso: make simulate-random COUNT=5)
	$(PY) src/simulate_logs.py --random --count $(COUNT)

.PHONY: scenarios
scenarios:  ## Lista os cenarios disponiveis
	$(PY) src/simulate_logs.py --list

.PHONY: incidents
incidents:  ## Lista os incidentes mais recentes
	$(PY) src/query_incidents.py

.PHONY: watch
watch:  ## Monitor de incidentes em tempo real
	$(PY) src/watch.py

.PHONY: stats
stats:  ## Mostra estatisticas dos incidentes
	$(PY) src/query_incidents.py --stats

.PHONY: api
api:  ## Consulta a API HTTP assinada (uso: make api P=/stats)
	$(PY) src/api_client.py $(P)

# ---------------------------------------------------------------------------
# Front-end (React + Vite) e proxy (FastAPI)
# ---------------------------------------------------------------------------
.PHONY: proxy
proxy:  ## Sobe o proxy FastAPI (assina SigV4) em http://localhost:8000
	$(PY) backend/server.py

.PHONY: web-install
web-install:  ## Instala as dependencias do front-end (npm install)
	cd frontend && npm install

.PHONY: web
web:  ## Sobe o dashboard React (Vite) em http://localhost:5173
	cd frontend && npm run dev

.PHONY: web-build
web-build:  ## Build de producao do front-end
	cd frontend && npm run build

.PHONY: dashboard
dashboard:  ## Sobe proxy + front juntos (Ctrl+C encerra ambos)
	@echo "Proxy: http://localhost:8000  |  Dashboard: http://localhost:5173"
	@$(PY) backend/server.py & \
		PROXY_PID=$$!; \
		trap "kill $$PROXY_PID 2>/dev/null" EXIT INT TERM; \
		cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------
.PHONY: test-e2e
test-e2e:  ## Teste end-to-end (simula -> aguarda -> valida incidente)
	$(PY) tests/test_e2e.py
