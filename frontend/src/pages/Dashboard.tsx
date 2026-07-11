import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDashboard } from '../hooks/useDashboard'
import GlassPanel from '../components/GlassPanel'
import StatChip from '../components/StatChip'
import ProgressRing from '../components/ProgressRing'
import LabelCaps from '../components/LabelCaps'
import { formatHHMMSS, formatDateLine, formatDueDate, formatBytes } from '../lib/format'

const PRIORITY_BORDER: Record<string, string> = {
  critical: 'border-status-critical',
  high:     'border-status-critical',
  medium:   'border-primary',
  low:      'border-on-surface-variant/40',
}

export default function Dashboard() {
  const { data } = useDashboard()
  const [now, setNow] = useState(new Date())
  const navigate = useNavigate()

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const greeting = data
    ? `GOOD ${now.getHours() < 12 ? 'MORNING' : now.getHours() < 17 ? 'AFTERNOON' : 'EVENING'}, ${data.greeting_name.toUpperCase()}`
    : 'LOADING...'

  return (
    <div className="p-6 space-y-gutter min-h-full">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-headline-lg font-headline-lg text-primary uppercase tracking-tighter">{greeting}</h2>
          <p className="text-code-sm font-code-sm text-on-surface-variant/60 mt-1">
            {formatDateLine(now)} // {formatHHMMSS(now)}
          </p>
        </div>
        <div className="flex gap-3 shrink-0">
          <StatChip
            label="UNREAD"
            value={data?.unread_notifications ?? 0}
            borderColor="border-primary"
          />
          <StatChip
            label="ACTIVE_RUNS"
            value={data?.running_tasks.length ?? 0}
            borderColor="border-tertiary"
          />
        </div>
      </div>

      {/* Bento grid */}
      <div className="grid grid-cols-12 gap-gutter">
        {/* Left column */}
        <div className="lg:col-span-4 col-span-12 space-y-gutter">
          <GlassPanel label="PRIORITY_QUEUE">
            <div className="space-y-2">
              {data?.priorities.length === 0 && (
                <p className="text-code-sm font-code-sm text-on-surface-variant/30 text-center py-4">NO PENDING TASKS</p>
              )}
              {data?.priorities.map((t) => (
                <div
                  key={t.id}
                  className={`bg-surface-container-high/40 p-2 flex justify-between items-start border-l-2 rounded-sm cursor-pointer hover:bg-surface-container-high/60 transition-colors gap-2 ${PRIORITY_BORDER[t.priority] ?? 'border-outline-variant'}`}
                  onClick={() => navigate(`/tasks`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && navigate('/tasks')}
                  aria-label={`Task: ${t.title}`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-headline-md font-bold text-on-surface truncate">{t.title}</p>
                    <p className="text-[9px] font-code-sm text-on-surface-variant/50 uppercase mt-0.5">
                      {t.status} / {t.priority}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {t.due_date && (
                      <LabelCaps className={`text-[9px] ${
                        formatDueDate(t.due_date) === 'OVERDUE' ? 'text-status-critical' :
                        formatDueDate(t.due_date) === 'TODAY' ? 'text-system-amber' :
                        'text-on-surface-variant/60'
                      }`}>
                        {formatDueDate(t.due_date)}
                      </LabelCaps>
                    )}
                    <span
                      className={`w-2 h-2 rounded-full ${
                        ['critical','high'].includes(t.priority) ? 'bg-status-critical animate-ping' : 'bg-primary/60'
                      }`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </GlassPanel>

          <GlassPanel label="ACTIVE_STREAMS">
            {data?.running_tasks && data.running_tasks.length > 0 ? (
              <div className="flex flex-wrap gap-4 justify-center py-2">
                {data.running_tasks.map((t, i) => (
                  <ProgressRing key={i} percent={50} label={String(t.title ?? `TASK_${i}`)} />
                ))}
              </div>
            ) : (
              <p className="text-code-sm font-code-sm text-on-surface-variant/30 text-center py-6">NO_ACTIVE_STREAMS</p>
            )}
          </GlassPanel>
        </div>

        {/* Right column */}
        <div className="lg:col-span-8 col-span-12 space-y-gutter">
          <div className="glass-panel rounded-xl h-64 relative overflow-hidden flex items-center justify-center">
            <div className="ambient-layer opacity-50" />
            <div className="relative z-10 text-center space-y-2">
              <h3 className="text-headline-lg font-headline-lg text-primary">SYSTEM NOMINAL</h3>
              <p className="text-code-sm font-code-sm text-on-surface-variant/60">
                {data?.priorities.length ?? 0} task(s) due today
              </p>
            </div>
          </div>

          <GlassPanel label="RECENT_UPDATES">
            <div className="overflow-x-auto">
              <table className="w-full text-[11px] font-code-sm">
                <thead>
                  <tr className="border-b border-glass-border text-on-surface-variant/40 uppercase text-[9px]">
                    <th className="text-left pb-2 pr-4 font-normal">FILE</th>
                    <th className="text-right pb-2 font-normal">SIZE</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.recent_files.map((f, i) => (
                    <tr
                      key={i}
                      className="border-b border-glass-border/30 hover:bg-primary/5 transition-colors cursor-pointer"
                    >
                      <td className="py-1.5 pr-4">
                        <div className="flex items-center gap-2">
                          <span className="material-symbols-outlined text-tertiary" style={{ fontSize: 14 }}>description</span>
                          <span className="text-on-surface truncate max-w-[240px]">{f.path}</span>
                        </div>
                      </td>
                      <td className="py-1.5 text-right text-on-surface-variant/60 whitespace-nowrap">{formatBytes(f.size)}</td>
                    </tr>
                  ))}
                  {(!data?.recent_files || data.recent_files.length === 0) && (
                    <tr>
                      <td colSpan={2} className="py-4 text-center text-on-surface-variant/30">NO RECENT FILES</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  )
}
