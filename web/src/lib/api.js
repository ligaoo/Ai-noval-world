const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const formatErrorDetail = (payload, fallback) => {
  const detail = payload?.detail ?? payload?.message ?? payload
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  return JSON.stringify(detail, null, 2)
}

export async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const hasBody = options.body !== undefined && options.body !== null
  const body = hasBody && typeof options.body !== 'string' ? JSON.stringify(options.body) : options.body

  if (hasBody && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    body,
  })
  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    throw new Error(formatErrorDetail(data, `请求失败：${response.status}`))
  }

  return data
}

export const worldsApi = {
  list: () => apiRequest('/worlds'),
  get: (worldId) => apiRequest(`/worlds/${encodeURIComponent(worldId)}`),
  create: (payload) => apiRequest('/worlds/create', { method: 'POST', body: payload }),
  update: (worldId, payload) => apiRequest(`/worlds/${encodeURIComponent(worldId)}`, { method: 'PUT', body: payload }),
  updateCharacters: (worldId, characters) => apiRequest(`/worlds/${encodeURIComponent(worldId)}/characters`, { method: 'PUT', body: { characters } }),
  complete: (worldId, payload) => apiRequest(`/worlds/${encodeURIComponent(worldId)}/complete`, { method: 'POST', body: payload }),
}

export const generatorsApi = {
  characters: (payload) => apiRequest('/generate/characters', { method: 'POST', body: payload }),
  npcs: (payload) => apiRequest('/generate/npcs', { method: 'POST', body: payload }),
  clues: (payload) => apiRequest('/generate/clues', { method: 'POST', body: payload }),
}

export const bootstrapApi = {
  create: (payload) => apiRequest('/story/bootstrap', { method: 'POST', body: payload }),
  get: (bootstrapId) => apiRequest(`/story/bootstrap/${encodeURIComponent(bootstrapId)}`),
  confirm: (bootstrapId) => apiRequest(`/story/bootstrap/${encodeURIComponent(bootstrapId)}/confirm`, { method: 'POST' }),
  start: (bootstrapId) => apiRequest(`/story/bootstrap/${encodeURIComponent(bootstrapId)}/start`, { method: 'POST' }),
}

export const simulationsApi = {
  list: () => apiRequest('/simulations'),
  get: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}`),
  run: (payload) => apiRequest('/simulations/run', { method: 'POST', body: payload }),
  status: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}/status`),
  quality: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}/quality`),
  qualityControls: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}/quality-controls`),
  revealBudget: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}/reveal-budget`),
  continuity: (simId) => apiRequest(`/simulations/${encodeURIComponent(simId)}/continuity`),
  rewrite: (simId, payload) => apiRequest(`/simulations/${encodeURIComponent(simId)}/rewrite`, { method: 'POST', body: payload }),
}

export const novelRunsApi = {
  create: (payload) => apiRequest('/novel-runs', { method: 'POST', body: payload }),
  get: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}`),
  plan: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/plan`),
  state: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/state`),
  clueLedger: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/clue-ledger`),
  truthState: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/truth-state`),
  openThreadsState: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/open-threads-state`),
  runtime: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/runtime`),
  generateNextChapter: (longRunId) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/chapters/next`, { method: 'POST' }),
  chapter: (longRunId, chapterNo) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/chapters/${chapterNo}`),
  memory: (longRunId, limit = 200) => apiRequest(`/novel-runs/${encodeURIComponent(longRunId)}/memory?limit=${limit}`),
}

export const genresApi = {
  list: () => apiRequest('/genres'),
  profile: (genreId) => apiRequest(`/genres/${encodeURIComponent(genreId)}/profile`),
}
