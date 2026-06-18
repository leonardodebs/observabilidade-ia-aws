# Exemplos de Variáveis de Ambiente e Configuração

Referência completa de toda a configuração do projeto: variáveis de ambiente dos
scripts, variáveis do Terraform e variáveis de ambiente dos Lambdas. Use como
template ao configurar o sistema.

> **Regra de ouro:** credenciais (chaves AWS) **nunca** vão em arquivos
> versionados. Use `aws configure` ou variáveis de ambiente padrão do SDK.
> Os arquivos `.env` e `terraform.tfvars` estão no `.gitignore`.

---

## 1. Configuração local — arquivo `.env`

Usado pelos scripts em `src/` e pelo proxy (`backend/server.py`). Copie de
`.env.example` e ajuste se necessário. Os scripts têm padrões sensatos, então
o `.env` é opcional na prática.

```bash
# ---- .env (copie de .env.example) ----

# Regiao AWS onde a infraestrutura foi criada.
AWS_DEFAULT_REGION=us-west-2

# Prefixo dos recursos (deve casar com a variavel 'prefixo' do Terraform).
PREFIXO=lab4

# Nomes derivados (sobrescreva apenas se mudar o prefixo no Terraform).
DYNAMODB_TABLE=lab4-incidents
LOG_GROUP=/lab4/app-simulation

# Opcional: URL da Lambda Function URL.
# Se ausente, e lida automaticamente do output do Terraform.
# API_URL=https://xxxx.lambda-url.us-west-2.on.aws
```

| Variável | Padrão | Obrigatória | Descrição |
|----------|--------|:-----------:|-----------|
| `AWS_DEFAULT_REGION` | `us-west-2` | não | Região dos recursos |
| `PREFIXO` | `lab4` | não | Prefixo dos nomes de recurso |
| `DYNAMODB_TABLE` | `lab4-incidents` | não | Nome da tabela de incidentes |
| `LOG_GROUP` | `/lab4/app-simulation` | não | Log group de origem |
| `API_URL` | (output do Terraform) | não | URL da Function URL (proxy/CLI) |
| `PROXY_PORT` | `8000` | não | Porta do proxy FastAPI |

---

## 2. Credenciais AWS (fora do versionamento)

O SDK procura credenciais nesta ordem. Use **uma** das opções:

**Opção A — `aws configure` (recomendado):**
```bash
aws configure
# AWS Access Key ID, Secret Access Key, region (us-west-2), output (json)
```

**Opção B — variáveis de ambiente:**
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-west-2
```

**Opção C — perfil nomeado:**
```bash
export AWS_PROFILE=meu-perfil
```

Permissões mínimas necessárias para **operar** (deploy + uso): acesso a
CloudWatch Logs, Lambda, DynamoDB, SNS, SQS, IAM e Bedrock na região escolhida.

---

## 3. Configuração da infraestrutura — `terraform.tfvars`

Copie de `terraform/terraform.tfvars.example`. **`notification_email` é o único
campo obrigatório.**

```hcl
# ---- terraform/terraform.tfvars ----

# OBRIGATORIO: e-mail que recebera notificacoes de incidentes CRITICO/ALTO.
# Apos o apply, confirme a inscricao no e-mail enviado pela AWS.
notification_email = "seu-email@exemplo.com"

# Regiao AWS (opcional).
aws_region = "us-west-2"

# Modelo Bedrock (opcional).
# bedrock_model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Autenticacao da Function URL: AWS_IAM (assinado) ou NONE (publico).
# Contas com SCP costumam bloquear NONE.
# api_auth_type = "AWS_IAM"

# Criar o Lambda da API com Function URL (opcional).
# criar_api = true

# Dias ate a expiracao automatica (TTL) dos incidentes.
# ttl_dias = 30

# Retencao dos log groups (em dias).
# log_retention_dias = 7
```

### Referência completa das variáveis do Terraform

| Variável | Tipo | Padrão | Obrigatória | Descrição |
|----------|------|--------|:-----------:|-----------|
| `notification_email` | string | — | **sim** | E-mail para notificações SNS |
| `aws_region` | string | `us-west-2` | não | Região AWS |
| `ambiente` | string | `lab` | não | Nome do ambiente (usado em tags) |
| `prefixo` | string | `lab4` | não | Prefixo dos recursos |
| `bedrock_model_id` | string | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | não | Modelo Bedrock |
| `api_auth_type` | string | `AWS_IAM` | não | `AWS_IAM` ou `NONE` |
| `criar_api` | bool | `true` | não | Cria o Lambda da API |
| `ttl_dias` | number | `30` | não | TTL dos incidentes (dias) |
| `log_retention_dias` | number | `7` | não | Retenção dos logs (dias) |

> **Como passar valores:** via `terraform.tfvars`, via `-var="chave=valor"`,
> ou via variáveis de ambiente `TF_VAR_<nome>` (ex.: `TF_VAR_notification_email`).

---

## 4. Variáveis de ambiente dos Lambdas (injetadas pelo Terraform)

Você **não** configura estas manualmente — o Terraform as injeta a partir dos
recursos criados. Listadas aqui para referência/depuração.

### Lambda `log-analyzer`
| Variável | Origem | Exemplo |
|----------|--------|---------|
| `BEDROCK_MODEL_ID` | `var.bedrock_model_id` | `us.anthropic.claude-haiku-4-5-...` |
| `DYNAMODB_TABLE` | nome da tabela | `lab4-incidents` |
| `SNS_TOPIC_ARN` | ARN do tópico | `arn:aws:sns:us-west-2:...:lab4-critical-incidents` |
| `TTL_DIAS` | `var.ttl_dias` | `30` |
| `AWS_REGION` | runtime Lambda | `us-west-2` (automática) |

### Lambda `incident-api`
| Variável | Origem | Exemplo |
|----------|--------|---------|
| `DYNAMODB_TABLE` | nome da tabela | `lab4-incidents` |

---

## 5. Checklist de configuração inicial

```text
[ ] Credenciais AWS configuradas      -> aws sts get-caller-identity
[ ] Acesso ao Bedrock Haiku habilitado -> ver RUNBOOK secao 7.1
[ ] terraform.tfvars criado com e-mail -> cp ...example terraform.tfvars
[ ] venv criado e deps instaladas      -> make deps
[ ] (front) npm install                -> make web-install
[ ] make tf-apply executado
[ ] Inscricao SNS confirmada no e-mail
[ ] make test-e2e passou
```

---

## 6. Boas práticas de segurança

- **Nunca** commitar `.env`, `terraform.tfvars` ou `*.tfstate` (já no `.gitignore`).
- Não colocar chaves AWS em `.env` — use a cadeia de credenciais do SDK.
- Rotacionar credenciais periodicamente; preferir perfis/SSO a chaves estáticas.
- Em produção, manter a Function URL em `AWS_IAM` (não exponha como `NONE`).
- Revisar as políticas IAM antes de ampliar permissões.

---

Ver também: [ARQUITETURA.md](ARQUITETURA.md) · [RUNBOOK.md](RUNBOOK.md) · [../README.md](../README.md)
