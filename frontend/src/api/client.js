const API_BASE = 'http://localhost:8000';

export async function fetchSignals(sector, conviction) {
  const params = new URLSearchParams();
  if (sector) params.append('sector', sector);
  if (conviction) params.append('conviction', conviction);
  
  const res = await fetch(`${API_BASE}/signals/?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch signals');
  return res.json();
}

export async function fetchSignalRationale(id) {
  const res = await fetch(`${API_BASE}/signals/${id}/rationale`);
  if (!res.ok) throw new Error('Failed to fetch rationale');
  return res.json();
}

export async function fetchSectorData(sectorName) {
  const res = await fetch(`${API_BASE}/sector/${sectorName}`);
  if (!res.ok) throw new Error('Failed to fetch sector');
  return res.json();
}

export async function searchSignals(query) {
  const res = await fetch(`${API_BASE}/search/?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Failed to search');
  return res.json();
}
