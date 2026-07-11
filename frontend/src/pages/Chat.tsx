import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useMessages } from '../hooks/useConversations'
import { globalSocket } from '../lib/ws'
import { apiFetch } from '../lib/api'
import { useUIStore } from '../stores/ui'
import type { Message } from '../lib/types'
import { ThreadSidebar } from '../components/chat/ThreadSidebar'
import { ChatMessage } from '../components/chat/ChatMessage'
import { ChatInput } from '../components/chat/ChatInput'
import { ContextPanel } from '../components/chat/ContextPanel'
import { TelemetryFlow } from '../components/chat/TelemetryFlow'
import LabelCaps from '../components/LabelCaps'

interface ToolEvent {
  tool: string
  status: 'running' | 'done' | 'error'
  result?: string
}

interface TokenBudget {
  used: number
  limit: number
  provider: string
  latency_ms?: number
}

export default function Chat() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const setIsRunActive = useUIStore((s) => s.setIsRunActive)

  const { data: messages } = useMessages(conversationId)
  const [streamingContent, setStreamingContent] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([])
  const [tokenBudget, setTokenBudget] = useState<TokenBudget | undefined>()
  const scrollRef = useRef<HTMLDivElement>(null)
  const pendingDeltaRef = useRef('')
  const rafRef = useRef<number>(0)

  const flushDelta = useCallback(() => {
    if (pendingDeltaRef.current) {
      setStreamingContent((prev) => prev + pendingDeltaRef.current)
      pendingDeltaRef.current = ''
    }
  }, [])

  useEffect(() => {
    const off = globalSocket.on((e) => {
      try {
        const ev = JSON.parse(e.data as string) as {
          type: string
          data?: Record<string, unknown>
        }

        if (!conversationId || ev.data?.conversation_id !== conversationId) return

        if (ev.type === 'stream.delta') {
          pendingDeltaRef.current += ev.data?.delta as string ?? ''
          cancelAnimationFrame(rafRef.current)
          rafRef.current = requestAnimationFrame(flushDelta)
          setStreaming(true)
          setIsRunActive(true)
        }

        if (ev.type === 'tool.start') {
          setToolEvents((prev) => [...prev, { tool: ev.data?.tool as string, status: 'running' }])
        }

        if (ev.type === 'tool.result') {
          const tool = ev.data?.tool as string
          setToolEvents((prev) =>
            prev.map((t) => t.tool === tool && t.status === 'running'
              ? { ...t, status: ev.data?.error ? 'error' : 'done', result: ev.data?.result as string | undefined }
              : t
            )
          )
        }

        if (ev.type === 'message.done') {
          flushDelta()
          setStreaming(false)
          setIsRunActive(false)
          setStreamingContent('')
          setToolEvents([])
          void qc.invalidateQueries({ queryKey: ['messages', conversationId] })
          void qc.invalidateQueries({ queryKey: ['conversations'] })
          if (ev.data?.budget) {
            const b = ev.data.budget as Record<string, unknown>
            setTokenBudget({
              used: b.used as number,
              limit: b.limit as number,
              provider: b.provider as string,
              latency_ms: b.latency_ms as number | undefined,
            })
          }
        }
      } catch { /* ignore */ }
    })
    return () => {
      off()
      cancelAnimationFrame(rafRef.current)
    }
  }, [conversationId, flushDelta, qc, setIsRunActive])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streamingContent])

  async function ensureConversation(): Promise<string> {
    if (conversationId) return conversationId
    const res = await apiFetch('/api/v1/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: null }),
    })
    if (!res.ok) throw new Error('Failed to create conversation')
    const conv = await res.json() as { id: string }
    void qc.invalidateQueries({ queryKey: ['conversations'] })
    navigate(`/chat/${conv.id}`, { replace: true })
    return conv.id
  }

  async function handleSend(text: string) {
    const convId = await ensureConversation()
    setStreamingContent('')
    setToolEvents([])
    setStreaming(true)
    setIsRunActive(true)

    await apiFetch('/api/v1/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: convId, content: text }),
    })
    void qc.invalidateQueries({ queryKey: ['messages', convId] })
  }

  const displayMessages: (Message & { _streaming?: boolean })[] = messages ?? []
  const streamingMessage: Message | null = streaming ? {
    id: '_streaming',
    conversation_id: conversationId ?? '',
    role: 'assistant',
    content: streamingContent,
    content_blocks: null,
    token_count: null,
    created_at: new Date().toISOString(),
  } : null

  return (
    <div className="flex h-full overflow-hidden">
      <ThreadSidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {!conversationId ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <LabelCaps dim className="block">SELECT OR START A CONVERSATION</LabelCaps>
              <button
                onClick={() => void ensureConversation().then((id) => navigate(`/chat/${id}`))}
                className="bg-primary-container text-on-primary-container px-6 py-3 rounded-xl font-bold text-code-sm font-code-sm shadow-[0_0_15px_rgba(255,107,0,0.3)] hover:shadow-[0_0_25px_rgba(255,107,0,0.5)] transition-all"
              >
                NEW_CONVERSATION
              </button>
            </div>
          </div>
        ) : (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
              {displayMessages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
              {toolEvents.map((t, i) => (
                <TelemetryFlow key={`${t.tool}-${i}`} toolName={t.tool} status={t.status} result={t.result} />
              ))}
              {streamingMessage && (
                <ChatMessage message={streamingMessage} streaming />
              )}
            </div>
            <ChatInput
              onSend={(text) => void handleSend(text)}
              disabled={streaming}
              tokenBudget={tokenBudget}
            />
          </>
        )}
      </div>

      <ContextPanel tokenBudget={tokenBudget} />
    </div>
  )
}
