import React from "react";

// Cartoes de resumo no topo do dashboard.
export default function StatsCards({ stats }) {
  const total = stats?.total ?? 0;
  const sev = stats?.by_severity ?? {};
  const conf = stats?.avg_confidence ?? 0;
  const ult24 = stats?.last_24h ?? 0;

  const cartoes = [
    { rotulo: "Total de incidentes", valor: total, classe: "neutro", icone: "📊" },
    { rotulo: "Críticos", valor: sev.CRITICO ?? 0, classe: "critico", icone: "🔴" },
    { rotulo: "Altos", valor: sev.ALTO ?? 0, classe: "alto", icone: "🟠" },
    { rotulo: "Últimas 24h", valor: ult24, classe: "neutro", icone: "🕐" },
    {
      rotulo: "Confiança média (IA)",
      valor: `${Math.round(conf * 100)}%`,
      classe: "confianca",
      icone: "🎯",
    },
  ];

  return (
    <div className="cartoes">
      {cartoes.map((c) => (
        <div key={c.rotulo} className={`cartao ${c.classe}`}>
          <span className="cartao-icone">{c.icone}</span>
          <div className="cartao-valor">{c.valor}</div>
          <div className="cartao-rotulo">{c.rotulo}</div>
        </div>
      ))}
    </div>
  );
}
