import LabelCaps from '../LabelCaps'

interface TelemetryFlowProps {
  toolName: string
  status: 'running' | 'done' | 'error'
  result?: string
}

export function TelemetryFlow({ toolName, status, result }: TelemetryFlowProps) {
  return (
    <div className="border-l-2 border-primary/20 ml-4 pl-6 py-2 space-y-2">
      <div className="flex items-center gap-2">
        <span
          className={`material-symbols-outlined text-status-safe ${status === 'running' ? 'animate-spin' : ''}`}
          style={{ fontSize: 16 }}
        >
          {status === 'running' ? 'sync' : status === 'done' ? 'check_circle' : 'error'}
        </span>
        <LabelCaps className={status === 'error' ? 'text-status-critical' : 'text-status-safe'}>
          {status === 'running' ? `EXECUTING: ${toolName}` : `${toolName}: ${status.toUpperCase()}`}
        </LabelCaps>
      </div>
      {result && (
        <div className="bg-terminal-black/50 border border-outline-variant/30 rounded-lg p-3">
          <pre className="text-code-sm font-code-sm text-on-surface-variant whitespace-pre-wrap break-words">{result}</pre>
        </div>
      )}
    </div>
  )
}
