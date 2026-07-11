import { useState } from 'react'
import type { Task } from '../../lib/types'
import { TaskCard } from './TaskCard'
import LabelCaps from '../LabelCaps'
import { useUIStore } from '../../stores/ui'
import { ApprovalModal } from '../chat/ApprovalModal'

const QUEUE_STATUSES = ['backlog', 'todo'] as const
const ACTIVE_STATUSES = ['in_progress', 'blocked'] as const
const DONE_STATUSES = ['done', 'cancelled'] as const

interface TaskBoardProps {
  tasks: Task[]
  onStatusChange: (id: string, status: Task['status']) => void
}

export function TaskBoard({ tasks, onStatusChange }: TaskBoardProps) {
  const [dragId, setDragId] = useState<string | null>(null)
  const pendingGate = useUIStore((s) => s.pendingGate)
  const setPendingGate = useUIStore((s) => s.setPendingGate)

  const queue  = tasks.filter((t) => (QUEUE_STATUSES as readonly string[]).includes(t.status))
  const active = tasks.filter((t) => (ACTIVE_STATUSES as readonly string[]).includes(t.status))
  const done   = tasks.filter((t) => (DONE_STATUSES as readonly string[]).includes(t.status))

  function handleDrop(targetStatus: Task['status']) {
    if (dragId) {
      onStatusChange(dragId, targetStatus)
      setDragId(null)
    }
  }

  return (
    <div className="grid grid-cols-4 gap-gutter h-full min-h-0">
      <Column
        title="QUEUE"
        headerColor="text-on-surface"
        tasks={queue}
        droppable
        onDrop={() => handleDrop('todo')}
        onDragStart={setDragId}
      />
      <Column
        title="ACTIVE_PROCESSING"
        headerColor="text-primary"
        tasks={active}
        droppable
        onDrop={() => handleDrop('in_progress')}
        onDragStart={setDragId}
      />
      <SafetyInterceptsColumn />
      <Column
        title="ARCHIVED"
        headerColor="text-status-safe"
        tasks={done}
        droppable={false}
        onDragStart={setDragId}
      />

      {pendingGate && (
        <ApprovalModal
          approvalId={pendingGate.approvalId}
          toolName={pendingGate.toolName}
          arguments={pendingGate.arguments}
          onClose={() => setPendingGate(null)}
        />
      )}
    </div>
  )
}

interface ColumnProps {
  title: string
  headerColor: string
  tasks: Task[]
  droppable: boolean
  onDrop?: () => void
  onDragStart: (id: string) => void
}

function Column({ title, headerColor, tasks, droppable, onDrop, onDragStart }: ColumnProps) {
  const [dragOver, setDragOver] = useState(false)

  return (
    <div
      className={`flex flex-col min-h-0 rounded-xl bg-surface-container/40 border border-glass-border transition-colors ${dragOver ? 'drag-zone-active' : ''}`}
      onDragOver={(e) => { if (droppable) { e.preventDefault(); setDragOver(true) } }}
      onDragLeave={() => setDragOver(false)}
      onDrop={() => { if (droppable && onDrop) { onDrop(); setDragOver(false) } }}
    >
      <div className="px-4 py-3 border-b border-glass-border">
        <LabelCaps className={headerColor}>{title}</LabelCaps>
        <span className="ml-2 text-[10px] font-code-sm text-on-surface-variant/50">{tasks.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {tasks.map((t) => (
          <div key={t.id} draggable={droppable} onDragStart={() => onDragStart(t.id)}>
            <TaskCard task={t} draggable={droppable} />
          </div>
        ))}
      </div>
    </div>
  )
}

function SafetyInterceptsColumn() {
  const pendingGate = useUIStore((s) => s.pendingGate)

  return (
    <div className="flex flex-col min-h-0 rounded-xl bg-surface-container/40 border border-glass-border">
      <div className="px-4 py-3 border-b border-glass-border">
        <LabelCaps className="text-system-amber">SAFETY_INTERCEPTS</LabelCaps>
        <span className="ml-2 text-[10px] font-code-sm text-on-surface-variant/50">{pendingGate ? 1 : 0}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {pendingGate ? (
          <button
            onClick={() => {}}
            className="w-full glass-panel p-3 rounded-lg border-l-2 border-system-amber text-left hover:bg-surface-container-high/30 transition-colors"
            aria-label={`Approve ${pendingGate.toolName}`}
          >
            <p className="text-[11px] font-headline-md font-bold text-system-amber">{pendingGate.toolName}</p>
            <p className="text-[9px] font-code-sm text-on-surface-variant/60 mt-1">Awaiting approval</p>
          </button>
        ) : (
          <p className="text-code-sm font-code-sm text-on-surface-variant/30 px-1">No pending intercepts</p>
        )}
      </div>
    </div>
  )
}
