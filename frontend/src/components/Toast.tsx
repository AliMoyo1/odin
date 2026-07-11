import { useEffect } from 'react'
import { useUIStore } from '../stores/ui'
import type { Toast } from '../lib/types'
import LabelCaps from './LabelCaps'

const COLORS: Record<Toast['type'], string> = {
  info:    'border-primary text-primary',
  warn:    'border-system-amber text-system-amber',
  error:   'border-status-critical text-status-critical',
  success: 'border-status-safe text-status-safe',
}

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useUIStore((s) => s.removeToast)

  useEffect(() => {
    const t = setTimeout(() => removeToast(toast.id), 4000)
    return () => clearTimeout(t)
  }, [toast.id, removeToast])

  return (
    <div className={`glass-panel px-4 py-3 rounded-xl border-l-2 ${COLORS[toast.type]} flex items-center justify-between gap-4 min-w-[280px]`}>
      <LabelCaps className={COLORS[toast.type]}>{toast.message}</LabelCaps>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-on-surface-variant hover:text-on-surface transition-colors"
        aria-label="Dismiss notification"
      >
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>close</span>
      </button>
    </div>
  )
}

export default function Toaster() {
  const toasts = useUIStore((s) => s.toasts)
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[90] flex flex-col gap-2" aria-live="polite" aria-label="Notifications">
      {toasts.map((t) => <ToastItem key={t.id} toast={t} />)}
    </div>
  )
}
