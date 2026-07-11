import { useTasks, useUpdateTaskStatus } from '../hooks/useTasks'
import { TaskBoard } from '../components/tasks/TaskBoard'
import LabelCaps from '../components/LabelCaps'
import type { Task } from '../lib/types'
import { useUIStore } from '../stores/ui'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { globalSocket } from '../lib/ws'

export default function Tasks() {
  const { data: tasks = [], isLoading } = useTasks()
  const updateStatus = useUpdateTaskStatus()
  const addToast = useUIStore((s) => s.addToast)
  const qc = useQueryClient()

  useEffect(() => {
    const off = globalSocket.on((e) => {
      try {
        const ev = JSON.parse(e.data as string) as { type: string }
        if (ev.type === 'task.changed') {
          void qc.invalidateQueries({ queryKey: ['tasks'] })
        }
      } catch { /* ignore */ }
    })
    return off
  }, [qc])

  function handleStatusChange(id: string, status: Task['status']) {
    updateStatus.mutate(
      { id, status },
      { onError: () => addToast({ type: 'error', message: 'STATUS_UPDATE_FAILED' }) }
    )
  }

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <LabelCaps dim>LOADING_TASKS...</LabelCaps>
      </div>
    )
  }

  return (
    <div className="p-6 flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-headline-md font-headline-md font-bold text-primary">TASK_BOARD</h2>
        <LabelCaps dim>{tasks.length} TOTAL</LabelCaps>
      </div>
      <div className="flex-1 min-h-0">
        <TaskBoard tasks={tasks} onStatusChange={handleStatusChange} />
      </div>
    </div>
  )
}
