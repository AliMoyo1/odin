import type { Task } from '../../lib/types'
import { formatDueDate } from '../../lib/format'
import LabelCaps from '../LabelCaps'

const PRIORITY_BORDER: Record<string, string> = {
  critical: 'border-status-critical',
  high:     'border-status-critical',
  medium:   'border-primary',
  low:      'border-on-surface-variant/40',
}

const PRIORITY_DOT: Record<string, string> = {
  critical: 'bg-status-critical animate-ping',
  high:     'bg-status-critical animate-ping',
  medium:   'bg-primary',
  low:      'bg-on-surface-variant/40',
}

interface TaskCardProps {
  task: Task
  draggable?: boolean
  onClick?: () => void
}

export function TaskCard({ task, draggable = false, onClick }: TaskCardProps) {
  const border = PRIORITY_BORDER[task.priority] ?? 'border-outline-variant'
  const dot = PRIORITY_DOT[task.priority] ?? 'bg-outline-variant'
  const due = formatDueDate(task.due_date)

  return (
    <div
      draggable={draggable}
      onClick={onClick}
      className={`glass-panel p-3 rounded-lg border-l-2 ${border} space-y-1.5 ${draggable ? 'cursor-grab active:cursor-grabbing' : ''} ${onClick ? 'cursor-pointer hover:bg-surface-container-high/30 transition-colors' : ''}`}
    >
      <div className="flex items-start gap-2">
        <span className={`w-2 h-2 rounded-full shrink-0 mt-1.5 ${dot}`} />
        <p className="text-[11px] font-headline-md font-bold text-on-surface leading-tight break-words flex-1">{task.title}</p>
      </div>
      <div className="flex items-center justify-between gap-2 pl-4">
        <LabelCaps dim className="text-[9px]">{task.priority.toUpperCase()}</LabelCaps>
        {due && (
          <LabelCaps className={`text-[9px] ${due === 'OVERDUE' ? 'text-status-critical' : due === 'TODAY' ? 'text-system-amber' : 'text-on-surface-variant/60'}`}>
            {due}
          </LabelCaps>
        )}
      </div>
    </div>
  )
}
