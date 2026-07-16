import { getBackendUrl } from '../lib/backendUrl'

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch(`${getBackendUrl()}/api/session`, { method: 'POST' })
  if (!res.ok) throw new Error(`create session failed: ${res.status}`)
  return res.json()
}

export async function endSession(sessionId: string): Promise<void> {
  await fetch(`${getBackendUrl()}/api/session/${sessionId}`, { method: 'DELETE' }).catch(() => {})
}

export function frameUrl(sessionId: string): string {
  return `${getBackendUrl()}/api/session/${sessionId}/frame?t=${Date.now()}`
}

export function imageUrl(url: string): string {
  return `${getBackendUrl()}${url}?t=${Date.now()}`
}

export async function health(): Promise<{ status: string; imagegen: string; prompting: string }> {
  const res = await fetch(`${getBackendUrl()}/api/health`)
  if (!res.ok) throw new Error(`health check failed: ${res.status}`)
  return res.json()
}
