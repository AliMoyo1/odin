import { useState } from 'react'
import { useKnowledgeDocs, useUploadDocument } from '../hooks/useKnowledge'
import GlassPanel from '../components/GlassPanel'
import LabelCaps from '../components/LabelCaps'
import { useUIStore } from '../stores/ui'
import { formatRelative } from '../lib/format'
import { apiFetch } from '../lib/api'

interface SearchResult {
  chunk_id: string
  document_id: string
  filename: string
  text: string
  score: number
  page: number | null
}

const STATUS_ICON: Record<string, string> = {
  processing: 'sync',
  indexed:    'check_circle',
  error:      'error',
}
const STATUS_COLOR: Record<string, string> = {
  processing: 'text-tertiary animate-spin',
  indexed:    'text-status-safe',
  error:      'text-status-critical',
}

export default function Knowledge() {
  const { data: docs = [], isError } = useKnowledgeDocs()
  const upload = useUploadDocument()
  const addToast = useUIStore((s) => s.addToast)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await apiFetch(`/api/v1/knowledge/search?q=${encodeURIComponent(query)}&limit=5`)
      if (res.ok) {
        setResults(await res.json() as SearchResult[])
      } else {
        addToast({ type: 'warn', message: 'SEARCH_UNAVAILABLE (requires PLAN-05)' })
      }
    } finally {
      setSearching(false)
    }
  }

  async function handleUpload(file: File) {
    upload.mutate(file, {
      onSuccess: () => addToast({ type: 'success', message: 'DOCUMENT_QUEUED_FOR_INDEXING' }),
      onError: () => addToast({ type: 'error', message: 'UPLOAD_FAILED' }),
    })
  }

  async function handleFileDrop(e: React.DragEvent) {
    e.preventDefault()
    e.currentTarget.classList.remove('drag-zone-active')
    const file = e.dataTransfer.files[0]
    if (file) await handleUpload(file)
  }

  return (
    <div className="p-6 h-full flex flex-col gap-gutter">
      <div className="flex items-center justify-between">
        <h2 className="text-headline-md font-headline-md font-bold text-primary">KNOWLEDGE_BASE</h2>
      </div>

      {/* Search */}
      <form onSubmit={(e) => void handleSearch(e)} className="flex gap-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="SEMANTIC_QUERY..."
          className="flex-1 bg-terminal-black border border-outline-variant focus:border-primary text-code-sm font-code-sm text-on-surface px-4 py-2.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary/30"
          aria-label="Knowledge base search"
        />
        <button
          type="submit"
          disabled={searching}
          className="bg-primary-container text-on-primary-container px-4 py-2.5 rounded-lg text-code-sm font-code-sm font-bold disabled:opacity-50 hover:shadow-[0_0_10px_rgba(255,107,0,0.5)] transition-all"
        >
          {searching ? 'SEARCHING...' : 'SEARCH'}
        </button>
      </form>

      {/* Search results */}
      {results.length > 0 && (
        <GlassPanel label="SEARCH_RESULTS">
          <div className="space-y-3">
            {results.map((r) => (
              <div key={r.chunk_id} className="bg-surface-container p-3 rounded-lg space-y-2">
                <p className="text-body-sm font-body-sm text-on-surface">{r.text}</p>
                <div className="flex items-center gap-3">
                  <LabelCaps className="text-primary">[Source: {r.filename}{r.page ? `, p.${r.page}` : ''}]</LabelCaps>
                  <div className="flex-1 h-1 bg-surface-container-high rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary/60"
                      style={{ width: `${Math.round(r.score * 100)}%` }}
                    />
                  </div>
                  <LabelCaps dim>{Math.round(r.score * 100)}%</LabelCaps>
                </div>
              </div>
            ))}
          </div>
        </GlassPanel>
      )}

      <div className="flex-1 flex gap-gutter min-h-0">
        {/* Document list */}
        <GlassPanel label="DOCUMENTS" className="flex-1 overflow-y-auto">
          {isError ? (
            <p className="text-system-amber text-code-sm font-code-sm text-center py-4">
              KNOWLEDGE_SERVICE_UNAVAILABLE (requires PLAN-05)
            </p>
          ) : docs.length === 0 ? (
            <p className="text-on-surface-variant/30 text-code-sm font-code-sm text-center py-4">No documents indexed</p>
          ) : (
            <table className="w-full text-[11px] font-code-sm">
              <thead>
                <tr className="border-b border-glass-border text-on-surface-variant/40 text-[9px]">
                  <th className="text-left pb-2 pr-4 font-normal uppercase">FILE</th>
                  <th className="text-center pb-2 pr-4 font-normal uppercase">STATUS</th>
                  <th className="text-right pb-2 font-normal uppercase">INDEXED</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id} className="border-b border-glass-border/30 hover:bg-primary/5 transition-colors">
                    <td className="py-1.5 pr-4 text-on-surface">{d.filename}</td>
                    <td className="py-1.5 pr-4 text-center">
                      <span className={`material-symbols-outlined ${STATUS_COLOR[d.status] ?? 'text-on-surface-variant'}`} style={{ fontSize: 16 }}>
                        {STATUS_ICON[d.status] ?? 'help'}
                      </span>
                    </td>
                    <td className="py-1.5 text-right text-on-surface-variant/60">
                      {d.indexed_at ? formatRelative(d.indexed_at) : 'pending'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </GlassPanel>

        {/* Upload zone */}
        <div
          onDrop={(e) => void handleFileDrop(e)}
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('drag-zone-active') }}
          onDragLeave={(e) => e.currentTarget.classList.remove('drag-zone-active')}
          className="w-64 glass-panel rounded-xl flex flex-col items-center justify-center gap-3 border-2 border-dashed border-glass-border shrink-0 cursor-pointer transition-colors"
          onClick={() => document.getElementById('kb-upload-input')?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && document.getElementById('kb-upload-input')?.click()}
          aria-label="Upload document to knowledge base"
        >
          <span className="material-symbols-outlined text-on-surface-variant/30" style={{ fontSize: 48 }}>upload_file</span>
          <LabelCaps dim>DROP DOCUMENT HERE</LabelCaps>
          <LabelCaps dim className="text-[9px]">PDF, TXT, MD, DOCX</LabelCaps>
          <input
            id="kb-upload-input"
            type="file"
            accept=".pdf,.txt,.md,.docx,.doc,.csv"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleUpload(f) }}
            className="hidden"
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
  )
}
