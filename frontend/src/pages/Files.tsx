import { useState } from 'react'
import { apiFetch } from '../lib/api'
import { useFileList } from '../hooks/useFiles'
import { FileTree } from '../components/files/FileTree'
import { UploadDropzone } from '../components/files/UploadDropzone'
import GlassPanel from '../components/GlassPanel'
import LabelCaps from '../components/LabelCaps'
import { useUIStore } from '../stores/ui'
import type { FileItem } from '../lib/types'
import { formatBytes, formatRelative } from '../lib/format'

export default function Files() {
  const [dir] = useState('/')
  const [selected, setSelected] = useState<FileItem | null>(null)
  const { data: items = [], isError } = useFileList(dir)
  const addToast = useUIStore((s) => s.addToast)

  async function handleUpload(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await apiFetch(`/api/v1/files/upload?path=${encodeURIComponent(dir)}`, {
        method: 'POST',
        body: fd,
      })
      if (!res.ok) throw new Error(await res.text())
      addToast({ type: 'success', message: 'UPLOAD_COMPLETE' })
    } catch {
      addToast({ type: 'error', message: 'UPLOAD_FAILED' })
    }
  }

  return (
    <div className="p-6 h-full flex gap-gutter">
      <GlassPanel className="w-64 shrink-0 overflow-y-auto">
        <FileTree items={items} onSelect={setSelected} selectedPath={selected?.path} />
      </GlassPanel>

      <UploadDropzone onUpload={handleUpload} className="flex-1 flex flex-col gap-gutter p-0">
        <GlassPanel className="flex-1 overflow-y-auto" label="WORKSPACE_FILES">
          {isError ? (
            <p className="text-code-sm font-code-sm text-system-amber py-4 text-center">
              FILE_SERVICE_UNAVAILABLE (requires PLAN-05)
            </p>
          ) : (
            <table className="w-full text-[11px] font-code-sm">
              <thead>
                <tr className="border-b border-glass-border text-on-surface-variant/40 uppercase text-[9px]">
                  <th className="text-left pb-2 pr-4 font-normal">NAME</th>
                  <th className="text-right pb-2 pr-4 font-normal">SIZE</th>
                  <th className="text-right pb-2 font-normal">MODIFIED</th>
                </tr>
              </thead>
              <tbody>
                {items.filter((f) => !f.is_dir).map((f, i) => (
                  <tr
                    key={i}
                    onClick={() => setSelected(f)}
                    className={`border-b border-glass-border/30 hover:bg-primary/5 transition-colors cursor-pointer ${selected?.path === f.path ? 'bg-surface-container-high' : ''}`}
                  >
                    <td className="py-1.5 pr-4 text-on-surface">{f.name}</td>
                    <td className="py-1.5 pr-4 text-right text-on-surface-variant/60">{f.size !== null ? formatBytes(f.size) : ''}</td>
                    <td className="py-1.5 text-right text-on-surface-variant/60">{f.mtime ? formatRelative(f.mtime) : ''}</td>
                  </tr>
                ))}
                {items.filter((f) => !f.is_dir).length === 0 && (
                  <tr><td colSpan={3} className="py-6 text-center text-on-surface-variant/30">DROP FILES HERE OR CLICK UPLOAD</td></tr>
                )}
              </tbody>
            </table>
          )}
        </GlassPanel>

        <GlassPanel label="SYSTEM_METRICS">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-surface-container px-3 py-2 rounded-lg">
              <LabelCaps dim className="block">TOTAL_FILES</LabelCaps>
              <span className="text-headline-md font-headline-md text-on-surface">
                {items.filter((f) => !f.is_dir).length}
              </span>
            </div>
            <div className="bg-surface-container px-3 py-2 rounded-lg">
              <LabelCaps dim className="block">WORKSPACE</LabelCaps>
              <span className="text-headline-md font-headline-md text-on-surface">{dir}</span>
            </div>
            <div className="bg-surface-container px-3 py-2 rounded-lg">
              <LabelCaps dim className="block">SYNC_STATUS</LabelCaps>
              <span className="text-status-safe text-headline-md font-headline-md">OK</span>
            </div>
          </div>
        </GlassPanel>
      </UploadDropzone>
    </div>
  )
}
