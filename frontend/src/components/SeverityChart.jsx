import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

// Cores por severidade (alinhadas ao tema do dashboard).
const CORES = {
  CRITICO: "#ef4444",
  ALTO: "#f97316",
  MEDIO: "#eab308",
  BAIXO: "#38bdf8",
};

export default function SeverityChart({ stats }) {
  const porSeveridade = stats?.by_severity ?? {};
  const dados = ["CRITICO", "ALTO", "MEDIO", "BAIXO"].map((s) => ({
    severidade: s,
    quantidade: porSeveridade[s] ?? 0,
  }));

  const vazio = dados.every((d) => d.quantidade === 0);

  if (vazio) {
    return <div className="grafico-vazio">Sem dados para exibir ainda.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={dados} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <XAxis dataKey="severidade" stroke="#94a3b8" fontSize={12} />
        <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
        <Tooltip
          cursor={{ fill: "rgba(148,163,184,0.08)" }}
          contentStyle={{
            background: "#0f172a",
            border: "1px solid #1e293b",
            borderRadius: 8,
            color: "#e2e8f0",
          }}
          formatter={(v) => [v, "Incidentes"]}
        />
        <Bar dataKey="quantidade" radius={[6, 6, 0, 0]}>
          {dados.map((d) => (
            <Cell key={d.severidade} fill={CORES[d.severidade]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
