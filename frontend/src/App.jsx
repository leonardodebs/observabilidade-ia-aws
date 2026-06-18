import React, { useCallback, useEffect, useState } from "react";
import { buscarIncidentes, buscarStats, buscarHealth } from "./api.js";
import StatsCards from "./components/StatsCards.jsx";
import SeverityChart from "./components/SeverityChart.jsx";
import IncidentTable from "./components/IncidentTable.jsx";
import IncidentModal from "./components/IncidentModal.jsx";

const SEVERIDADES = ["TODAS", "CRITICO", "ALTO", "MEDIO", "BAIXO"];
const INTERVALO_MS = 10000; // auto-refresh a cada 10s

export default function App() {
  const [incidentes, setIncidentes] = useState([]);
  const [stats, setStats] = useState(null);
  const [filtro, setFiltro] = useState("TODAS");
  const [selecionado, setSelecionado] = useState(null);
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);

  const carregar = useCallback(async () => {
    try {
      const sev = filtro === "TODAS" ? undefined : filtro;
      const [resIncidentes, resStats] = await Promise.all([
        buscarIncidentes(sev),
        buscarStats(),
      ]);
      setIncidentes(resIncidentes.incidents || []);
      setStats(resStats);
      setErro(null);
      setUltimaAtualizacao(new Date());
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  }, [filtro]);

  // Carrega ao montar e quando o filtro muda.
  useEffect(() => {
    setCarregando(true);
    carregar();
  }, [carregar]);

  // Auto-refresh.
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(carregar, INTERVALO_MS);
    return () => clearInterval(id);
  }, [autoRefresh, carregar]);

  return (
    <div className="app">
      <header className="topo">
        <div className="titulo">
          <span className="logo">🔍</span>
          <div>
            <h1>Observabilidade IA</h1>
            <p className="subtitulo">
              Análise de incidentes em tempo real · CloudWatch → Bedrock → DynamoDB
            </p>
          </div>
        </div>
        <div className="controles">
          <span className={`pulso ${autoRefresh ? "ativo" : ""}`}>
            <span className="ponto" /> {autoRefresh ? "ao vivo" : "pausado"}
          </span>
          <button className="btn" onClick={() => setAutoRefresh((v) => !v)}>
            {autoRefresh ? "⏸ Pausar" : "▶ Retomar"}
          </button>
          <button className="btn" onClick={carregar}>
            ↻ Atualizar
          </button>
        </div>
      </header>

      {erro && (
        <div className="alerta-erro">
          <strong>Erro ao carregar dados:</strong> {erro}
          <div className="dica">
            Verifique se a infra está no ar (<code>make tf-apply</code>) e se o
            proxy está rodando (<code>make proxy</code>).
          </div>
        </div>
      )}

      <StatsCards stats={stats} />

      <div className="grade-principal">
        <section className="painel">
          <div className="painel-cabecalho">
            <h2>Incidentes</h2>
            <div className="filtros">
              {SEVERIDADES.map((s) => (
                <button
                  key={s}
                  className={`chip ${filtro === s ? "ativo" : ""} chip-${s}`}
                  onClick={() => setFiltro(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <IncidentTable
            incidentes={incidentes}
            carregando={carregando}
            onSelecionar={setSelecionado}
          />
        </section>

        <aside className="painel lateral">
          <h2>Distribuição por severidade</h2>
          <SeverityChart stats={stats} />
        </aside>
      </div>

      <footer className="rodape">
        {ultimaAtualizacao && (
          <span>
            Última atualização: {ultimaAtualizacao.toLocaleTimeString("pt-BR")}
          </span>
        )}
        <span>Lab 4 · AWS AI Services · Powered by Amazon Bedrock (Claude Haiku)</span>
      </footer>

      {selecionado && (
        <IncidentModal
          incidente={selecionado}
          onFechar={() => setSelecionado(null)}
        />
      )}
    </div>
  );
}
