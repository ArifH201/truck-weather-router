const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(message, fields) {
    super(message)
    this.fields = fields || {}
  }
}

async function post(path, body, signal) {
  let res
  try {
    res = await fetch(`${BASE}/api/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError('Cannot reach the server. Is the backend running?')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(data.error || `Request failed (${res.status})`, data.fields)
  return data
}

export const analyze = (payload, signal) => post('analyze', payload, signal)
export const heatmap = (payload, signal) => post('heatmap', payload, signal)

export async function health(signal) {
  const res = await fetch(`${BASE}/api/health`, { signal })
  return res.json()
}
