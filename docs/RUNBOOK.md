# Runbook Operacional

Procedimentos de operação, verificação e troubleshooting do Sistema de
Observabilidade com IA. Todos os comandos assumem que você está na raiz do
projeto, com o `venv` ativado e credenciais AWS configuradas.

> Região padrão: `us-west-2`. Prefixo dos recursos: `lab4`.

---

## 1. Pré-requisitos

| Ferramenta | Versão | Verificar |
|------------|--------|-----------|
| AWS CLI | v2 | `aws sts get-caller-identity` |
| Terraform | ≥ 1.5 | `terraform -version` |
| Python | 3.12 | `python3 --version` |
| Node.js | ≥ 20 | `node --version` (apenas para o front) |
| Acesso ao Bedrock | Claude Haiku habilitado | ver seção 7.1 |

Setup inicial:
```bash
python3 -m venv .venv && . .venv/bin/activate
make deps
cp terraform/terraform.tfvars.example terraform/terraform.tfvars   # edite o e-mail
```

---

## 2. Operações comuns

### 2.1 Subir a infraestrutura
```bash
make tf-apply
```
Após o apply, **confirme a inscrição do SNS** no e-mail recebido da AWS
(assunto "AWS Notification - Subscription Confirmation"). Sem isso, as
notificações de incidentes não chegam.

### 2.2 Gerar incidentes de teste
```bash
make simulate S=db-connection-failure   # cenario especifico
make simulate-random COUNT=8            # varios aleatorios
make scenarios                          # lista os cenarios disponiveis
```
Cenários: `db-connection-failure`, `memory-leak`, `disk-full`, `auth-failure`, `network-timeout`.

### 2.3 Consultar incidentes
```bash
make incidents                              # lista recentes (DynamoDB)
make stats                                  # estatisticas agregadas
make watch                                  # monitor em tempo real
make api P=/stats                           # via API HTTP assinada (SigV4)
.venv/bin/python src/query_incidents.py --severity CRITICO
.venv/bin/python src/query_incidents.py --id <incidentId>
```

### 2.4 Subir o dashboard web
```bash
make web-install     # uma vez (npm install)
make dashboard       # proxy + React -> http://localhost:5173
```

### 2.5 Teste end-to-end
```bash
make test-e2e
# Esperado: "E2E test passed — incident <id> created with severity CRITICO"
```

### 2.6 Destruir tudo (encerrar custos)
```bash
make tf-destroy
```
> Sempre rode ao final de uma sessão de testes para não deixar recursos ativos.

---

## 3. Verificações de saúde (health checks)

```bash
# Recursos existem na conta?
aws lambda list-functions --region us-west-2 --query "Functions[?contains(FunctionName,'lab4')].FunctionName" --output text
aws dynamodb describe-table --table-name lab4-incidents --region us-west-2 --query "Table.TableStatus" --output text

# Quantidade de incidentes
aws dynamodb scan --table-name lab4-incidents --region us-west-2 --select COUNT --query Count --output text

# Mensagens presas na DLQ (idealmente 0)
aws sqs get-queue-attributes --region us-west-2 \
  --queue-url $(terraform -chdir=terraform output -raw dlq_url) \
  --attribute-names ApproximateNumberOfMessages \
  --query "Attributes.ApproximateNumberOfMessages" --output text

# Proxy/front no ar?
curl -s http://localhost:8000/api/health
```

---

## 4. Observabilidade (logs do próprio sistema)

Os logs do Lambda são JSON estruturado — ideais para CloudWatch Logs Insights.

```bash
# Acompanhar logs do analyzer em tempo real
aws logs tail /aws/lambda/lab4-log-analyzer --follow --region us-west-2

# Erros recentes
aws logs tail /aws/lambda/lab4-log-analyzer --since 30m --region us-west-2 --filter-pattern "ERROR"
```

Exemplo de consulta no Logs Insights:
```
fields @timestamp, nivel, mensagem, severity, duracaoMs
| filter nivel = "ERROR"
| sort @timestamp desc
| limit 50
```

---

## 5. Troubleshooting

### 5.1 Simulei um erro mas nenhum incidente aparece

**Diagnóstico (em ordem):**
1. O log casou o filtro? O texto precisa conter `ERROR`, `CRITICAL`, `Exception`,
   `Traceback` ou `FATAL`.
2. O Lambda foi invocado?
   ```bash
   aws logs tail /aws/lambda/lab4-log-analyzer --since 10m --region us-west-2
   ```
3. Há mensagens na DLQ? (indica falha no processamento — ver 5.2)
4. Aguarde: o pipeline leva ~10–30 s (entrega do filtro + chamada ao Bedrock).

### 5.2 Lambda falhando / mensagens na DLQ

**Causas prováveis e ações:**
- **`AccessDeniedException` no Bedrock** → modelo não habilitado ou sem permissão.
  Ver seção 7.1.
- **`ThrottlingException`** → pico de chamadas; o retry com backoff normalmente
  resolve. Se persistir, reduza o volume de simulação.
- **Erro de parse do JSON da IA** → raro (parser é tolerante). Verifique o log
  `WARN`/`ERROR` do analyzer.

Para reprocessar mensagens da DLQ, inspecione-as:
```bash
aws sqs receive-message --region us-west-2 \
  --queue-url $(terraform -chdir=terraform output -raw dlq_url) --max-number-of-messages 5
```

### 5.3 API/Dashboard retorna 403 Forbidden

- A Function URL usa `AWS_IAM`. Use sempre o **proxy** (`make proxy`) ou
  `src/api_client.py` / `make api`, que assinam com SigV4. Chamadas diretas
  por `curl` sem assinatura retornam 403 — é o comportamento esperado.
- Se mesmo via proxy der 403, confirme que suas credenciais locais têm
  `lambda:InvokeFunctionUrl` e estão válidas (`aws sts get-caller-identity`).

### 5.4 Dashboard não carrega dados

```bash
curl -s http://localhost:8000/api/health     # proxy descobriu a API?
```
- `"status":"sem_api"` → rode `make tf-apply` ou defina `API_URL` no ambiente.
- Proxy não sobe → confirme que `fastapi`/`uvicorn` estão instalados (`make deps`).
- Erro de CORS no navegador → use `make dashboard`/`make web` (o Vite faz o
  proxy de `/api`); não abra o `index.html` direto do disco.

### 5.5 `terraform apply` falha

- **E-mail não definido** → a variável `notification_email` é obrigatória; edite
  `terraform/terraform.tfvars`.
- **Recurso já existe** → rode `make tf-destroy` antes, ou importe o recurso.
- **Lock de estado** → se um apply anterior foi interrompido, remova o lock
  conforme a mensagem do Terraform.

### 5.6 Não recebo e-mails do SNS

- Confirme a inscrição (link no e-mail da AWS). Status:
  ```bash
  aws sns list-subscriptions-by-topic --region us-west-2 \
    --topic-arn $(terraform -chdir=terraform output -raw sns_topic_arn) \
    --query "Subscriptions[].SubscriptionArn" --output text
  ```
  `PendingConfirmation` = ainda não confirmado.
- Lembre: só `CRITICO`/`ALTO` notificam. `MEDIO`/`BAIXO` não enviam e-mail.

---

## 6. Procedimentos de manutenção

### 6.1 Atualizar o código de um Lambda
Edite o arquivo em `lambda/.../handler.py` e rode:
```bash
make tf-apply   # o Terraform reempacota o zip e atualiza a funcao
```

### 6.2 Limpar incidentes manualmente
Os incidentes expiram sozinhos pelo TTL (30 dias). Para zerar antes disso, o
caminho mais simples é recriar a tabela:
```bash
make tf-destroy && make tf-apply
```

### 6.3 Trocar o modelo do Bedrock
Ajuste `bedrock_model_id` no `terraform.tfvars` e rode `make tf-apply`.

---

## 7. Apêndices

### 7.1 Verificar/habilitar acesso ao Bedrock
```bash
# Modelos Haiku disponiveis na regiao
aws bedrock list-foundation-models --region us-west-2 \
  --query "modelSummaries[?contains(modelId,'haiku')].modelId" --output text

# Teste de invocacao
aws bedrock-runtime invoke-model --region us-west-2 \
  --model-id "us.anthropic.claude-haiku-4-5-20251001-v1:0" \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"ok"}]}' \
  --cli-binary-format raw-in-base64-out /tmp/saida.json && echo OK
```
Se der `AccessDenied`, habilite o modelo no console do Bedrock
(*Model access*) e/ou ajuste a política IAM do papel `analyzer`.

### 7.2 Encerrar processos locais (proxy/Vite)
```bash
pkill -f "backend/server.py"   # proxy FastAPI
pkill -f "vite"                # dashboard
```

### 7.3 Tabela de referência rápida (alvos do Makefile)

| Comando | O que faz |
|---------|-----------|
| `make tf-apply` / `make tf-destroy` | Cria / destrói a infra |
| `make simulate S=<cenario>` | Dispara um cenário de erro |
| `make simulate-random COUNT=N` | Dispara N cenários aleatórios |
| `make incidents` / `make stats` | Lista incidentes / estatísticas |
| `make watch` | Monitor em tempo real (Rich) |
| `make api P=/stats` | Consulta a API assinada |
| `make proxy` / `make web` / `make dashboard` | Sobe proxy / front / ambos |
| `make test-e2e` | Teste ponta a ponta |

---

Ver também: [ARQUITETURA.md](ARQUITETURA.md) · [VARIAVEIS-AMBIENTE.md](VARIAVEIS-AMBIENTE.md) · [../README.md](../README.md)
