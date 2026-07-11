import { getAccessToken, setAccessToken, clearAccessToken } from './auth'

let _refreshPromise: Promise<boolean> | null = null

async function _refresh(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = (async () => {
    try {
      const res = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' })
      if (!res.ok) return false
      const data = await res.json() as { access_token: string }
      setAccessToken(data.access_token)
      return true
    } catch {
      return false
    } finally {
      _refreshPromise = null
    }
  })()
  return _refreshPromise
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getAccessToken()
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  headers.set('X-Interface-Origin', 'web')

  const res = await fetch(path, { ...init, headers, credentials: 'include' })

  if (res.status === 401) {
    const ok = await _refresh()
    if (!ok) {
      clearAccessToken()
      window.location.href = '/login'
      return res
    }
    const retryToken = getAccessToken()
    const retryHeaders = new Headers(init.headers)
    if (retryToken) retryHeaders.set('Authorization', `Bearer ${retryToken}`)
    retryHeaders.set('X-Interface-Origin', 'web')
    return fetch(path, { ...init, headers: retryHeaders, credentials: 'include' })
  }

  return res
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}
