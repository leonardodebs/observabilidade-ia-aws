// Cliente HTTP do front-end. Fala com o proxy local (/api/*),
// que por sua vez assina (SigV4) e encaminha para a Lambda API.

async function getJSON(caminho) {
  const resp = await fetch(caminho);
  if (!resp.ok) {
    let detalhe = resp.statusText;
    try {
      const corpo = await resp.json();
      detalhe = corpo.detail || JSON.stringify(corpo);
    } catch {
      /* ignora corpo nao-JSON */
    }
    throw new Error(`HTTP ${resp.status}: ${detalhe}`);
  }
  return resp.json();
}

export function buscarIncidentes(severity) {
  const qs = severity ? `?severity=${encodeURIComponent(severity)}` : "";
  return getJSON(`/api/incidents${qs}`);
}

export function buscarStats() {
  return getJSON("/api/stats");
}

export function buscarHealth() {
  return getJSON("/api/health");
}
