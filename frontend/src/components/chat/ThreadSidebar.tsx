import { useNavigate, useParams } from 'react-router-dom'
import { useConversations } from '../../hooks/useConversations'
import { formatRelative } from '../../lib/format'
import LabelCaps from '../LabelCaps'
import { apiFetch } from '../../lib/api'
import type { Conversation } from '../../lib/types'
import { useQueryClient } from '@tanstack/react-query'

export function ThreadSidebar() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { data: conversations } = useConversations()
  const navigate = useNavigate()
  const qc = useQueryClient()

  async function createNew() {
    const res = await apiFetch('/api/v1/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: null }),
    })
    if (res.ok) {
      const conv = await res.json() as Conversation
      void qc.invalidateQueries({ queryKey: ['conversations'] })
      navigate(`/chat/${conv.id}`)
    }
  }

  const sorted = [...(conversations ?? [])].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )

  return (
    <div className="w-72 bg-surface-container-lowest border-r border-glass-border flex flex-col h-full shrink-0">
      <div className="px-4 py-3 border-b border-glass-border flex items-center justify-between">
        <LabelCaps>CONVERSATIONS</LabelCaps>
        <button
          onClick={() => void createNew()}
          className="text-primary hover:text-on-primary-container hover:bg-primary-container p-1 rounded-lg transition-colors"
          aria-label="New conversation"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sorted.map((conv) => {
          const isActive = conv.id === conversationId
          return (
            <button
              key={conv.id}
              onClick={() => navigate(`/chat/${conv.id}`)}
              className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-surface-container-high border-l-2 border-primary'
                  : 'hover:bg-surface-container-low border-l-2 border-transparent'
              }`}
            >
              <p className="text-body-sm font-body-sm text-on-surface truncate">
                {conv.title ?? 'Untitled'}
              </p>
              <p className="text-[11px] font-code-sm text-on-surface-variant/50 mt-0.5">
                {formatRelative(conv.updated_at)} / {conv.message_count} msgs
              </p>
            </button>
          )
        })}
        {sorted.length === 0 && (
          <p className="text-code-sm font-code-sm text-on-surface-variant/40 px-3 py-2">No conversations yet</p>
        )}
      </div>
    </div>
  )
}
