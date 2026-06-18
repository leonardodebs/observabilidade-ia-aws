import React, { useEffect } from "react";

function formatarData(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("pt-BR");
}

// Modal de detalhes de um incidente (abre ao clicar numa linha da tabela).
export default function IncidentModal({ incidente, onFechar }) {
  // Fecha com a tecla ESC.
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onFechar]);

  const sev = incidente.severity || "?";
  const conf = Math.round((incidente.confianca ?? 0) * 100);
  const acoes = incidente.acoesRecomendadas || [];

  return (
    <div className="modal-overlay" onClick={onFechar}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-cabecalho">
          <span className={`badge badge-${sev}`}>{sev}</span>
          <h2>{incidente.titulo}</h2>
          <button className="modal-fechar" onClick={onFechar}>
            ✕
          </button>
        </header>

        <div className="modal-meta">
          <div>
            <span className="meta-rotulo">Categoria</span>
            <span className="meta-valor">{incidente.categoria || "-"}</span>
          </div>
          <div>
            <span className="meta-rotulo">Componente</span>
            <span className="meta-valor">{incidente.componenteAfetado || "-"}</span>
          </div>
          <div>
            <span className="meta-rotulo">Confiança da IA</span>
            <span className="meta-valor">{conf}%</span>
          </div>
          <div>
            <span className="meta-rotulo">Detectado em</span>
            <span className="meta-valor">{formatarData(incidente.timestamp)}</span>
          </div>
        </div>

        <section className="modal-secao">
          <h3>🔬 Causa raiz</h3>
          <p>{incidente.causaRaiz || "—"}</p>
        </section>

        <section className="modal-secao">
          <h3>💥 Impacto</h3>
          <p>{incidente.impacto || "—"}</p>
        </section>

        <section className="modal-secao">
          <h3>🛠️ Ações recomendadas</h3>
          {acoes.length ? (
            <ol className="acoes">
              {acoes.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ol>
          ) : (
            <p>—</p>
          )}
        </section>

        <footer className="modal-rodape">
          <span className="meta-rotulo">ID</span>
          <code>{incidente.incidentId}</code>
          <span className="meta-rotulo">Origem</span>
          <code>{incidente.logGroup}</code>
        </footer>
      </div>
    </div>
  );
}
