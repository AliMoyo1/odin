import { useRef, useEffect } from 'react'
import type { Message } from '../../lib/types'
import { formatTimeShort } from '../../lib/format'
import LabelCaps from '../LabelCaps'

interface ChatMessageProps {
  message: Message
  streaming?: boolean
}

function CodeBlock({ children }: { children: string }) {
  function handleCopy() {
    void navigator.clipboard.writeText(children)
  }

  return (
    <div className="bg-terminal-black rounded-lg border border-outline-variant my-2 overflow-hidden group">
      <div className="flex items-center justify-between px-3 py-1 border-b border-outline-variant/50">
        <LabelCaps dim>CODE</LabelCaps>
        <button
          onClick={handleCopy}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-on-surface-variant hover:text-primary"
          aria-label="Copy code"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>content_copy</span>
        </button>
      </div>
      <pre className="p-3 text-code-sm font-code-sm text-status-safe overflow-x-auto">{children}</pre>
    </div>
  )
}

function renderContent(text: string) {
  const parts = text.split(/(```[\s\S]*?```)/g)
  return parts.map((part, i) => {
    if (part.startsWith('```') && part.endsWith('```')) {
      const code = part.slice(3, -3).replace(/^[^\n]*\n/, '')
      return <CodeBlock key={i}>{code}</CodeBlock>
    }
    return <span key={i} className="whitespace-pre-wrap">{part}</span>
  })
}

export function ChatMessage({ message, streaming = false }: ChatMessageProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (streaming && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [message.content, streaming])

  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] space-y-1">
          <div className="bg-surface-container-high px-5 py-4 rounded-xl rounded-tr-none border border-glass-border">
            <p className="text-body-sm font-body-sm text-on-surface whitespace-pre-wrap">{message.content}</p>
          </div>
          <LabelCaps dim className="block text-right">USER // {formatTimeShort(message.created_at)}</LabelCaps>
        </div>
      </div>
    )
  }

  if (message.role === 'assistant') {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[85%] space-y-1">
          <div className={`relative ${streaming ? 'bg-surface-container-low' : 'glass-panel'} rounded-xl rounded-tl-none px-5 py-4`}>
            <div className="absolute left-0 top-0 bottom-0 w-[1px] bg-primary shadow-[0_0_10px_rgba(255,107,0,0.5)] rounded-l-xl" />
            <div className="text-body-sm font-body-sm text-on-surface">
              {renderContent(message.content ?? '')}
              {streaming && <span className="terminal-blink" />}
            </div>
          </div>
          <LabelCaps className="text-primary opacity-60">ODIN // {formatTimeShort(message.created_at)}</LabelCaps>
        </div>
      </div>
    )
  }

  return null
}
