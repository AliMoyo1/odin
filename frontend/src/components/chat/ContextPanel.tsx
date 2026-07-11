import LabelCaps from '../LabelCaps'

interface TokenBudget {
  used: number
  limit: number
  provider: string
  latency_ms?: number
}

interface ContextPanelProps {
  tokenBudget?: TokenBudget
}

export function ContextPanel({ tokenBudget }: ContextPanelProps) {
  const pct = tokenBudget ? Math.min(100, (tokenBudget.used / tokenBudget.limit) * 100) : 0

  return (
    <div className="w-80 border-l border-glass-border flex flex-col h-full shrink-0 hidden xl:flex">
      <div className="px-4 py-3 border-b border-glass-border">
        <LabelCaps>ACTIVE_CONTEXT</LabelCaps>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-2">
          <LabelCaps dim className="block">ACTIVE_MEMORIES</LabelCaps>
          <p className="text-code-sm font-code-sm text-on-surface-variant/50">
            Memory retrieval available after PLAN-06
          </p>
        </div>
      </div>

      {tokenBudget && (
        <div className="p-4 border-t border-glass-border space-y-2">
          <LabelCaps>TOKEN_BUDGET</LabelCaps>
          <div className="h-1 bg-surface-container rounded-full overflow-hidden">
            <div
              className="h-full bg-primary shadow-[0_0_10px_rgba(255,107,0,0.5)] transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex gap-2">
            <div className="bg-terminal-black px-3 py-1.5 rounded-lg flex-1">
              <LabelCaps dim className="block">{tokenBudget.provider.toUpperCase()}</LabelCaps>
            </div>
            {tokenBudget.latency_ms !== undefined && (
              <div className="bg-terminal-black px-3 py-1.5 rounded-lg flex-1">
                <LabelCaps dim className="block">{tokenBudget.latency_ms}MS</LabelCaps>
              </div>
            )}
          </div>
          <LabelCaps dim className="block">
            {tokenBudget.used.toLocaleString()} / {tokenBudget.limit.toLocaleString()} TOKENS
          </LabelCaps>
        </div>
      )}
    </div>
  )
}
