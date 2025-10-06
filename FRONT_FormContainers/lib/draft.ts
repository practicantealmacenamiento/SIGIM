export function saveDraft(key: string, data: any) {
  try { localStorage.setItem(key, JSON.stringify(data)); } catch {}
}
export function loadDraft(key: string) {
  try { const d = localStorage.getItem(key); return d ? JSON.parse(d) : null; } catch { return null; }
}
export function clearDraft(key: string) {
  try { localStorage.removeItem(key); } catch {}
}
