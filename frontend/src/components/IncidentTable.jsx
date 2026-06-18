import React from "react";

function formatarData(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// Tabela/lista de incidentes. Cada linha abre o modal de detalhes ao clicar.
export default function IncidentTable({ incidentes, carregando, onSelecionar }) {
  if (carregando) {
    return <div className="estado-vazio">Carregando incidentes…</div>;
  }
  if (!incidentes.length) {
    return (
      <div className="estado-vazio">
        Nenhum incidente encontrado. Gere alguns com{" "}
        <code>make simulate S=db-connection-failure</code>.
      </div>
    );
  }

  return (
    <div className="tabela-wrapper">
      <table className="tabela">
        <thead>
          <tr>
            <th>Severidade</th>
            <th>Quando</th>
            <th>Conf.</th>
            <th>Categoria</th>
            <th>Título</th>
          </tr>
        </thead>
        <tbody>
          {incidentes.map((inc) => {
            const sev = inc.severity || "?";
            const conf = Math.round((inc.confianca ?? 0) * 100);
            return (
              <tr
                key={inc.incidentId}
                className="linha"
                onClick={() => onSelecionar(inc)}
              >
                <td>
                  <span className={`badge badge-${sev}`}>{sev}</span>
                </td>
                <td className="celula-data">{formatarData(inc.timestamp)}</td>
                <td className="celula-conf">{conf}%</td>
                <td>
                  <span className="categoria">{inc.categoria || "-"}</span>
                </td>
                <td className="celula-titulo">{inc.titulo}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
