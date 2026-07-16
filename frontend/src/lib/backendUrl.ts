const STORAGE_KEY = 'backend_url'

/** Resolves the REST base URL. Empty string means "same origin" (dev proxy / same-host prod). */
export function getBackendUrl(): string {
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    return ''
  }
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) return saved.replace(/\/$/, '')
  return 'http://localhost:8000'
}

export function getWsUrl(): string {
  const backend = getBackendUrl()
  if (!backend) {
    return `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}`
  }
  return backend.replace(/^http/, 'ws')
}

export function getSavedBackendUrl(): string {
  return localStorage.getItem(STORAGE_KEY) || 'http://localhost:8000'
}

export function setSavedBackendUrl(url: string): void {
  const trimmed = url.trim()
  if (!trimmed) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  const withScheme = /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`
  localStorage.setItem(STORAGE_KEY, withScheme)
}
