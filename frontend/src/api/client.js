const BASE = ''

async function get(path) {
  const res = await fetch(BASE + path)
  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(payload?.detail || `${res.status} ${res.statusText}`)
  }
  return payload
}

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(payload?.detail || `${res.status} ${res.statusText}`)
  }
  return payload
}

export const api = {
  getHistory: (limit = 20, offset = 0) =>
    get(`/api/history?limit=${limit}&offset=${offset}`),

  getInsights: (windowMinutes = 60) =>
    get(`/api/insights?window_minutes=${windowMinutes}`),

  getStats: () => get('/api/stats'),

  getThroughput: (hours = 24, bucketMinutes = 60) =>
    get(`/api/stats/throughput?hours=${hours}&bucket_minutes=${bucketMinutes}`),

  postCorrection: (body) => post('/api/corrections', body),

  getCorrection: (hash) => get(`/api/corrections/${hash}`),
}
