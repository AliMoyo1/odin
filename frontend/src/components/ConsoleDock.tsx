import { useEffect, useRef, useState, FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { globalSocket } from '../lib/ws'
import LabelCaps from './LabelCaps'
import { formatHHMMSS } from '../lib/format'

interface LogLine {
  time: string
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

export default function ConsoleDock() {
  const { pathname } = useLocation()
  const isDashboard = pathname === '/dashboard'
  const [lines, setLines] = useState<LogLine[]>([])
  const [connected, setConnected] = useState(globalSocket.isConnected)
  const linesRef = useRef<LogLine[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const off = globalSocket.on((e) => {
      try {
        const ev = JSON.parse(e.data as string) as { type: string; data?: Record<string, unknown> }
        if (ev.type === 'activity' || ev.type === 'notification.new') {
          const message =
            (ev.data?.action as string | undefined) ??
            (ev.data?.message as string | undefined) ??
            JSON.stringify(ev.data)
          const level: LogLine['level'] =
            ev.type === 'notification.new' ? 'INFO' : (ev.data?.level as LogLine['level'] | undefined) ?? 'INFO'
          const line: LogLine = { time: formatHHMMSS(new Date()), level, message }
          linesRef.current = [...linesRef.current.slice(-199), line]
          setLines([...linesRef.current])
        }
      } catch { /* ignore malformed events */ }
    })
    const offConn = globalSocket.onConnectionChange(setConnected)
    return () => { off(); offConn() }
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [lines])

  if (!isDashboard) {
    return (
      <div className="fixed bottom-0 left-[280px] right-0 h-12 bg-terminal-black/95 border-t border-glass-border flex items-center px-6 z-40 gap-4">
        <span className="material-symbols-outlined text-on-surface-variant/50" style={{ fontSize: 16 }}>terminal</span>
        <span className="text-code-sm font-code-sm text-status-safe/80 truncate flex-1">
          {lines[lines.length - 1]?.message ?? 'SYSTEM_NOMINAL'}
        </span>
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${connected ? 'bg-status-safe animate-ping' : 'bg-on-surface-variant/30'}`}
          aria-label={connected ? 'Connected' : 'Disconnected'}
        />
        <span className="text-code-sm font-code-sm text-on-surface-variant/40 terminal-blink shrink-0">odin@system:~$</span>
      </div>
    )
  }

  return (
    <div
      className="fixed bottom-0 left-[280px] right-0 h-[200px] bg-terminal-black/95 border-t border-glass-border flex z-40"
      role="log"
      aria-label="System console"
    >
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 font-code-sm text-code-sm space-y-0.5">
        <div className="flex items-center gap-2 mb-2 border-b border-glass-border pb-1.5">
          <span className="material-symbols-outlined text-on-surface-variant/50" style={{ fontSize: 14 }}>terminal</span>
          <LabelCaps dim>SYSTEM_CONSOLE</LabelCaps>
          <span className={`ml-auto w-2 h-2 rounded-full ${connected ? 'bg-status-safe animate-ping' : 'bg-on-surface-variant/30'}`} />
        </div>
        {lines.length === 0 && (
          <span className="text-on-surface-variant/30 terminal-blink">odin@system:~$ </span>
        )}
        {lines.map((l, i) => (
          <div key={i} className={`leading-5 ${l.level === 'WARN' ? 'text-system-amber' : l.level === 'ERROR' ? 'text-status-critical' : 'text-status-safe/80'}`}>
            [{l.time}] {l.level}: {l.message}
          </div>
        ))}
      </div>
      <HermesDirectChat />
    </div>
  )
}

function HermesDirectChat() {
  const [input, setInput] = useState('')
  const navigate = useNavigate()

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!input.trim()) return
    navigate('/chat')
  }

  return (
    <div className="w-80 border-l border-glass-border flex flex-col shrink-0">
      <div className="px-4 py-2 border-b border-glass-border flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-status-safe animate-ping shrink-0" />
        <LabelCaps>HERMES_DIRECT</LabelCaps>
      </div>
      <div className="flex-1 px-3 py-2 overflow-y-auto">
        <p className="text-code-sm font-code-sm text-on-surface-variant/40">Ask Hermes anything...</p>
      </div>
      <form onSubmit={handleSubmit} className="px-3 py-2 border-t border-glass-border flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 bg-terminal-black border border-outline-variant focus:border-primary text-code-sm font-code-sm text-on-surface px-3 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/30"
          placeholder="QUERY..."
          aria-label="Ask Hermes directly"
        />
        <button
          type="submit"
          className="bg-primary-container text-on-primary-container px-3 rounded-lg hover:shadow-[0_0_10px_rgba(255,107,0,0.5)] transition-all active:scale-95"
          aria-label="Send"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>send</span>
        </button>
      </form>
    </div>
  )
}
