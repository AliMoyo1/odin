import { apiFetch } from './api'

export type WsListener = (event: MessageEvent) => void

async function getTicket(): Promise<string> {
  const res = await apiFetch('/api/v1/ws-ticket', { method: 'POST' })
  if (!res.ok) throw new Error('Failed to obtain WS ticket')
  const data = await res.json() as { ticket: string }
  return data.ticket
}

export class OdinSocket {
  private ws: WebSocket | null = null
  private listeners = new Set<WsListener>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _closed = false
  private _connected = false
  private connectionListeners = new Set<(connected: boolean) => void>()

  async connect(): Promise<void> {
    this._closed = false
    await this._open()
  }

  private async _open(): Promise<void> {
    try {
      const ticket = await getTicket()
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      this.ws = new WebSocket(`${proto}://${location.host}/ws/events?ticket=${ticket}`)
      this.ws.onopen = () => {
        this._connected = true
        this.connectionListeners.forEach((l) => l(true))
      }
      this.ws.onmessage = (e) => this.listeners.forEach((l) => l(e))
      this.ws.onclose = () => {
        this._connected = false
        this.connectionListeners.forEach((l) => l(false))
        if (!this._closed) this._scheduleReconnect()
      }
      this.ws.onerror = () => {
        this.ws?.close()
      }
    } catch {
      this._scheduleReconnect()
    }
  }

  private _scheduleReconnect(): void {
    if (this._closed) return
    this.reconnectTimer = setTimeout(() => void this._open(), 3000)
  }

  on(listener: WsListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  onConnectionChange(listener: (connected: boolean) => void): () => void {
    this.connectionListeners.add(listener)
    return () => this.connectionListeners.delete(listener)
  }

  close(): void {
    this._closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }

  get isConnected(): boolean {
    return this._connected
  }
}

export const globalSocket = new OdinSocket()
