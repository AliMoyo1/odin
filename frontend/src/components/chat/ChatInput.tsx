import { useRef, FormEvent, KeyboardEvent } from 'react'
import LabelCaps from '../LabelCaps'

interface ChatInputProps {
  onSend: (text: string) => void
  disabled?: boolean
  tokenBudget?: { used: number; limit: number; provider: string }
}

export function ChatInput({ onSend, disabled = false, tokenBudget }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = textareaRef.current?.value.trim()
    if (!text || disabled) return
    onSend(text)
    if (textareaRef.current) textareaRef.current.value = ''
    autoResize()
  }

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const form = (e.target as HTMLElement).closest('form')
      form?.requestSubmit()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-surface-container-lowest/80 backdrop-blur-md border-t border-glass-border px-4 py-3 space-y-2"
    >
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="Message Hermes..."
          className="flex-1 bg-terminal-black border border-outline-variant focus:border-primary rounded-xl text-body-sm font-body-sm text-on-surface px-4 py-3 focus:outline-none focus:ring-1 focus:ring-primary/30 resize-none overflow-hidden disabled:opacity-50"
          aria-label="Message input"
        />
        <button
          type="submit"
          disabled={disabled}
          className="bg-primary-container h-14 w-14 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(255,107,0,0.3)] hover:shadow-[0_0_25px_rgba(255,107,0,0.5)] hover:scale-105 active:scale-95 transition-all disabled:opacity-50 shrink-0"
          aria-label="Send message"
        >
          <span className="material-symbols-outlined text-on-primary-container">send</span>
        </button>
      </div>

      <div className="flex items-center gap-3">
        <span className="w-2 h-2 rounded-full bg-status-safe shrink-0" />
        <LabelCaps dim>Secure Channel</LabelCaps>
        {tokenBudget && (
          <>
            <span className="text-on-surface-variant/30 text-[10px] font-code-sm">|</span>
            <LabelCaps dim>{tokenBudget.provider.toUpperCase()} {tokenBudget.used}/{tokenBudget.limit} TOKENS</LabelCaps>
          </>
        )}
      </div>
    </form>
  )
}
