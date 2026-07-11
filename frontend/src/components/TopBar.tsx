import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUIStore } from '../stores/ui'
import HermesOrb from './HermesOrb'
import LabelCaps from './LabelCaps'

export default function TopBar() {
  const isRunActive = useUIStore((s) => s.isRunActive)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/chat?q=${encodeURIComponent(query)}`)
      setQuery('')
    }
  }

  return (
    <header className="fixed top-0 left-[280px] right-0 h-16 bg-background/80 backdrop-blur-md border-b border-glass-border flex items-center px-6 z-40 gap-4">
      <LabelCaps className="text-tertiary-container shrink-0">ORCHESTRATOR // ODIN_V1</LabelCaps>

      <div className="flex-1 flex justify-center">
        <HermesOrb state={isRunActive ? 'thinking' : 'idle'} size={28} />
      </div>

      <form onSubmit={handleSearch} className="flex items-center gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="QUERY_SYSTEM..."
          className="bg-surface-container-low rounded-full px-4 py-1.5 text-code-sm font-code-sm text-primary placeholder:text-on-surface-variant/40 border border-transparent focus:border-primary focus:outline-none w-44 transition-colors"
          aria-label="Search messages"
        />
      </form>

      <button className="relative text-on-surface-variant hover:text-primary transition-colors" aria-label="Notifications">
        <span className="material-symbols-outlined">notifications</span>
      </button>

      <div className="bg-surface-container-high px-3 py-1.5 rounded-xl border border-glass-border">
        <LabelCaps className="text-on-surface-variant">ODIN@USER</LabelCaps>
      </div>
    </header>
  )
}
