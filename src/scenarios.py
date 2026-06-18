"""
Cenarios de erro realistas para simulacao de logs — Lab 4.
Cada cenario gera um trecho de log multilinha realista (stack traces em
ingles, mensagens em pt-BR) que sera enviado ao CloudWatch Logs.
"""

from datetime import datetime


def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# db-connection-failure: psycopg2 connection refused, pool esgotado
# ---------------------------------------------------------------------------
def db_connection_failure() -> str:
    t = _ts()
    return f"""{t} ERROR [pedidos-service] Falha ao obter conexao do pool de banco de dados
{t} CRITICAL [pedidos-service] Pool de conexoes esgotado (20/20 em uso) apos 30s de espera
Traceback (most recent call last):
  File "/app/db/pool.py", line 88, in get_connection
    conn = self._pool.getconn()
  File "/usr/lib/python3.12/site-packages/psycopg2/pool.py", line 174, in getconn
    raise PoolError("connection pool exhausted")
psycopg2.pool.PoolError: connection pool exhausted
{t} ERROR [pedidos-service] OperationalError: could not connect to server: Connection refused
        Is the server running on host "db-prod.internal" (10.0.3.21) and accepting
        TCP/IP connections on port 5432?
{t} FATAL [pedidos-service] Encerrando processamento de pedidos: banco indisponivel ha 45s"""


# ---------------------------------------------------------------------------
# memory-leak: Java OutOfMemoryError, GC overhead limit
# ---------------------------------------------------------------------------
def memory_leak() -> str:
    t = _ts()
    return f"""{t} ERROR [checkout-api] Excecao nao tratada na thread http-nio-8080-exec-42
java.lang.OutOfMemoryError: GC overhead limit exceeded
        at java.base/java.util.HashMap.newNode(HashMap.java:1901)
        at java.base/java.util.HashMap.putVal(HashMap.java:631)
        at com.loja.checkout.cache.SessionCache.store(SessionCache.java:114)
        at com.loja.checkout.SessionManager.persist(SessionManager.java:67)
{t} CRITICAL [checkout-api] Heap em 98% (3.9GB/4.0GB) — GC consumindo 95% do tempo de CPU
{t} ERROR [checkout-api] java.lang.OutOfMemoryError: Java heap space
{t} FATAL [checkout-api] JVM instavel; health check falhando, pod marcado para reinicio"""


# ---------------------------------------------------------------------------
# disk-full: No space left on device, IOError durante escrita
# ---------------------------------------------------------------------------
def disk_full() -> str:
    t = _ts()
    return f"""{t} ERROR [relatorios-worker] Falha ao gravar arquivo de relatorio em /var/data/reports
Traceback (most recent call last):
  File "/app/reports/writer.py", line 142, in flush
    f.write(buffer)
OSError: [Errno 28] No space left on device
{t} CRITICAL [relatorios-worker] Particao /var/data com 100% de uso (500GB/500GB)
{t} ERROR [relatorios-worker] IOError: nao foi possivel persistir o relatorio diario; fila acumulando
{t} ERROR [relatorios-worker] Logrotate falhou: cannot write compressed file: No space left on device"""


# ---------------------------------------------------------------------------
# auth-failure: JWT expirado, 401 Unauthorized, token invalido
# ---------------------------------------------------------------------------
def auth_failure() -> str:
    t = _ts()
    return f"""{t} ERROR [auth-gateway] Falha na validacao do token JWT
io.jsonwebtoken.ExpiredJwtException: JWT expired at 2026-06-17T11:58:02Z. Current time: 2026-06-17T12:14:55Z
        at io.jsonwebtoken.impl.DefaultJwtParser.parse(DefaultJwtParser.java:411)
        at com.loja.auth.TokenValidator.validate(TokenValidator.java:53)
{t} WARN [auth-gateway] 401 Unauthorized: invalid token para usuario id=88213 (rota /api/v1/pedidos)
{t} ERROR [auth-gateway] Pico de 4200 falhas de autenticacao/min — possivel chave de assinatura rotacionada sem propagacao
{t} ERROR [auth-gateway] Exception: invalid token signature; rejeitando requisicoes upstream"""


# ---------------------------------------------------------------------------
# Cenario extra: erro de rede / timeout em servico externo
# ---------------------------------------------------------------------------
def network_timeout() -> str:
    t = _ts()
    return f"""{t} ERROR [pagamentos-service] Timeout ao chamar gateway de pagamento externo
requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='api.gateway-pag.com', port=443):
        Max retries exceeded (Connection timed out after 10000ms)
{t} ERROR [pagamentos-service] Exception: 3 tentativas falharam; transacao tx_9f31a marcada como pendente
{t} CRITICAL [pagamentos-service] Circuit breaker ABERTO para gateway-pag apos 50 falhas consecutivas"""


# Mapa de cenarios disponiveis.
CENARIOS = {
    "db-connection-failure": db_connection_failure,
    "memory-leak": memory_leak,
    "disk-full": disk_full,
    "auth-failure": auth_failure,
    "network-timeout": network_timeout,
}
