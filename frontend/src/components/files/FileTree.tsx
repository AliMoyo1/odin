import { useState } from 'react'
import type { FileItem } from '../../lib/types'
import { formatBytes } from '../../lib/format'
import LabelCaps from '../LabelCaps'

interface FileTreeProps {
  items: FileItem[]
  onSelect: (item: FileItem) => void
  selectedPath?: string
}

export function FileTree({ items, onSelect, selectedPath }: FileTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const dirs  = items.filter((f) => f.is_dir).sort((a, b) => a.name.localeCompare(b.name))
  const files = items.filter((f) => !f.is_dir).sort((a, b) => a.name.localeCompare(b.name))

  function getIcon(item: FileItem): string {
    if (item.is_dir) return expanded.has(item.path) ? 'folder_open' : 'folder'
    const ext = item.name.split('.').pop()?.toLowerCase()
    if (['pdf', 'doc', 'docx'].includes(ext ?? '')) return 'description'
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext ?? '')) return 'image'
    if (['mp4', 'mkv', 'avi'].includes(ext ?? '')) return 'movie'
    if (['mp3', 'wav', 'flac'].includes(ext ?? '')) return 'audio_file'
    if (['zip', 'tar', 'gz'].includes(ext ?? '')) return 'archive'
    if (['py', 'js', 'ts', 'go', 'rs'].includes(ext ?? '')) return 'code'
    return 'insert_drive_file'
  }

  function toggleDir(path: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  return (
    <div className="space-y-0.5">
      <LabelCaps dim className="block px-2 pb-2 border-b border-glass-border mb-2">WORKSPACE</LabelCaps>
      {[...dirs, ...files].map((item) => (
        <button
          key={item.path}
          onClick={() => item.is_dir ? toggleDir(item.path) : onSelect(item)}
          className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors ${
            selectedPath === item.path
              ? 'bg-surface-container-high text-primary'
              : 'text-on-surface-variant hover:text-primary hover:bg-surface-container-low'
          }`}
        >
          <span className="material-symbols-outlined text-tertiary shrink-0" style={{ fontSize: 16 }}>{getIcon(item)}</span>
          <span className="text-code-sm font-code-sm truncate flex-1">{item.name}</span>
          {!item.is_dir && item.size !== null && (
            <span className="text-[10px] font-code-sm text-on-surface-variant/40 shrink-0">{formatBytes(item.size)}</span>
          )}
        </button>
      ))}
    </div>
  )
}
