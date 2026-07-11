import { useState } from 'react'
import { apiFetch } from '../../lib/api'
import { useUIStore } from '../../stores/ui'
import LabelCaps from '../LabelCaps'

interface ApprovalModalProps {
  approvalId: string
  toolName: string
  arguments: Record<string, unknown>
  onClose: () => void
}

export function ApprovalModal({ approvalId, toolName, arguments: args, onClose }: ApprovalModalProps) {
  const [remember, setRemember] = useState(false)
  const [loading, setLoading] = useState(false)
  const addToast = useUIStore((s) => s.addToast)

  async function handleApprove() {
    setLoading(true)
    try {
      const res = await apiFetch(`/api/v1/approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ remember }),
      })
      if (!res.ok && res.status !== 410) {
        addToast({ type: 'error', message: 'APPROVAL_FAILED' })
      }
    } finally {
      setLoading(false)
      onClose()
    }
  }

  async function handleDeny() {
    setLoading(true)
    try {
      await apiFetch(`/api/v1/approvals/${approvalId}/deny`, { method: 'POST' })
    } finally {
      setLoading(false)
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 bg-background/80 backdrop-blur-sm z-[100] flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="gate-title"
    >
      <div className="w-[400px] bg-terminal-black border-2 border-primary shadow-[0_0_50px_rgba(255,107,0,0.4)] rounded-xl overflow-hidden">
        <div className="bg-primary-container p-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-on-primary-container">lock</span>
          <LabelCaps className="text-on-primary-container">GATE_LOCKED</LabelCaps>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-body-sm font-body-sm text-on-surface">
            Hermes requests: <span className="text-primary font-bold">{toolName}</span>
          </p>

          <div className="bg-surface-container p-3 rounded-lg">
            <LabelCaps dim className="mb-2 block">ARGUMENTS</LabelCaps>
            <pre className="text-code-sm font-code-sm text-on-surface-variant overflow-x-auto">
              {JSON.stringify(args, null, 2)}
            </pre>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="accent-primary"
            />
            <LabelCaps dim>Remember for this project</LabelCaps>
          </label>

          <div className="space-y-2">
            <button
              onClick={() => void handleApprove()}
              disabled={loading}
              className="w-full bg-primary-container text-on-primary-container font-bold py-3 rounded-xl shadow-[0_0_15px_rgba(255,107,0,0.3)] hover:shadow-[0_0_25px_rgba(255,107,0,0.5)] active:scale-95 transition-all disabled:opacity-50 text-code-sm font-code-sm"
            >
              APPROVE_EXECUTION
            </button>
            <button
              onClick={() => void handleDeny()}
              disabled={loading}
              className="w-full border border-primary text-primary font-bold py-3 rounded-xl hover:bg-primary/5 active:scale-95 transition-all disabled:opacity-50 text-code-sm font-code-sm"
            >
              ABORT_SEQUENCE
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
