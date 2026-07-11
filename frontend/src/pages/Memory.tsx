import { useState } from 'react'
import { useMemories, useArchiveMemory } from '../hooks/useMemory'
import GlassPanel from '../components/GlassPanel'
import LabelCaps from '../components/LabelCaps'
import { useUIStore } from '../stores/ui'

type Tab = 'ACTIVE' | 'SUGGESTIONS' | 'REVIEW'

export default function Memory() {
  const [tab, setTab] = useState<Tab>('ACTIVE')
  const { data: memories = [], isError } = useMemories()
  const archive = useArchiveMemory()
  const addToast = useUIStore((s) => s.addToast)

  const active = memories.filter((m) => m.source !== 'suggested')
  const suggestions = memories.filter((m) => m.source === 'suggested')

  const TABS: Tab[] = ['ACTIVE', 'SUGGESTIONS', 'REVIEW']

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-headline-md font-headline-md font-bold text-primary">MEMORY_STORE</h2>
      </div>

      {/* Tab bar */}
      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              tab === t
                ? 'bg-primary-container text-on-primary-container shadow-[0_0_10px_rgba(255,107,0,0.3)]'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`}
          >
            <LabelCaps className={tab === t ? 'text-on-primary-container' : ''}>{t}</LabelCaps>
          </button>
        ))}
      </div>

      {isError && (
        <p className="text-system-amber text-code-sm font-code-sm">MEMORY_SERVICE_UNAVAILABLE (requires PLAN-06)</p>
      )}

      {tab === 'ACTIVE' && (
        <GlassPanel label="ACTIVE_MEMORIES" className="flex-1 overflow-y-auto">
          {active.length === 0 ? (
            <p className="text-on-surface-variant/30 text-code-sm font-code-sm text-center py-6">No active memories</p>
          ) : (
            <div className="space-y-2">
              {active.map((m) => (
                <div key={m.id} className="bg-surface-container p-3 rounded-lg flex items-start gap-3">
                  <span className="material-symbols-outlined text-tertiary shrink-0" style={{ fontSize: 18 }}>psychology</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-headline-md font-bold text-primary truncate">{m.key}</p>
                    <p className="text-body-sm font-body-sm text-on-surface mt-0.5">{m.value}</p>
                    <LabelCaps dim className="mt-1">ACCESS_COUNT: {m.access_count}</LabelCaps>
                  </div>
                  <button
                    onClick={() => archive.mutate(m.id, {
                      onSuccess: () => addToast({ type: 'info', message: 'MEMORY_ARCHIVED' }),
                      onError:   () => addToast({ type: 'error', message: 'ARCHIVE_FAILED' }),
                    })}
                    className="text-on-surface-variant/40 hover:text-status-critical transition-colors shrink-0"
                    aria-label={`Archive memory: ${m.key}`}
                  >
                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>archive</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </GlassPanel>
      )}

      {tab === 'SUGGESTIONS' && (
        <GlassPanel label="PENDING_SUGGESTIONS" className="flex-1 overflow-y-auto">
          {suggestions.length === 0 ? (
            <p className="text-on-surface-variant/30 text-code-sm font-code-sm text-center py-6">No suggestions</p>
          ) : (
            <div className="space-y-2">
              {suggestions.map((m) => (
                <div key={m.id} className="bg-surface-container p-3 rounded-lg space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-system-amber" style={{ fontSize: 16 }}>lightbulb</span>
                    <p className="text-[11px] font-headline-md font-bold text-system-amber">{m.key}</p>
                  </div>
                  <p className="text-body-sm font-body-sm text-on-surface">{m.value}</p>
                  <div className="flex gap-2">
                    <button className="flex-1 bg-primary-container text-on-primary-container py-1.5 rounded-lg text-code-sm font-code-sm font-bold">
                      APPROVE
                    </button>
                    <button className="flex-1 border border-outline-variant text-on-surface-variant py-1.5 rounded-lg text-code-sm font-code-sm">
                      REJECT
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassPanel>
      )}

      {tab === 'REVIEW' && (
        <GlassPanel label="REVIEW_QUEUE" className="flex-1 overflow-y-auto">
          <div className="space-y-3">
            <div className="bg-surface-container p-3 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <LabelCaps>CAPACITY</LabelCaps>
                <LabelCaps dim>{active.length} / 1000</LabelCaps>
              </div>
              <div className="h-1 bg-surface-container-high rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary shadow-[0_0_10px_rgba(255,107,0,0.5)]"
                  style={{ width: `${Math.min(100, (active.length / 1000) * 100)}%` }}
                />
              </div>
            </div>
            <p className="text-on-surface-variant/30 text-code-sm font-code-sm text-center py-4">
              Memory consolidation runs nightly via PLAN-09
            </p>
          </div>
        </GlassPanel>
      )}
    </div>
  )
}
