import { useRef, DragEvent, ChangeEvent } from 'react'
import { useUIStore } from '../../stores/ui'
import LabelCaps from '../LabelCaps'

const MAX_SIZE_BYTES = 50 * 1024 * 1024
const ALLOWED_EXTS = ['.pdf', '.txt', '.md', '.docx', '.doc', '.csv', '.json', '.py', '.js', '.ts', '.go', '.rs']

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>
  children: React.ReactNode
  className?: string
}

export function UploadDropzone({ onUpload, children, className = '' }: UploadDropzoneProps) {
  const dragRef = useRef(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const addToast = useUIStore((s) => s.addToast)

  function validateAndUpload(file: File) {
    const ext = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '')
    if (!ALLOWED_EXTS.includes(ext)) {
      addToast({ type: 'warn', message: `FILE_TYPE_REJECTED: ${ext.toUpperCase()}` })
      return
    }
    if (file.size > MAX_SIZE_BYTES) {
      addToast({ type: 'warn', message: 'FILE_TOO_LARGE: 50MB MAX' })
      return
    }
    void onUpload(file)
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    e.currentTarget.classList.remove('drag-zone-active')
    dragRef.current = false
    const file = e.dataTransfer.files[0]
    if (file) validateAndUpload(file)
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault()
    if (!dragRef.current) {
      dragRef.current = true
      e.currentTarget.classList.add('drag-zone-active')
    }
  }

  function handleDragLeave(e: DragEvent) {
    e.currentTarget.classList.remove('drag-zone-active')
    dragRef.current = false
  }

  function handleFileInput(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) validateAndUpload(file)
    e.target.value = ''
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`relative rounded-xl border border-glass-border transition-colors ${className}`}
    >
      {children}
      <button
        onClick={() => inputRef.current?.click()}
        className="absolute bottom-3 right-3 flex items-center gap-2 bg-primary-container text-on-primary-container px-3 py-1.5 rounded-lg text-code-sm font-code-sm shadow-[0_0_10px_rgba(255,107,0,0.3)] hover:shadow-[0_0_20px_rgba(255,107,0,0.5)] transition-all"
        aria-label="Upload file"
      >
        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
        <LabelCaps>UPLOAD</LabelCaps>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_EXTS.join(',')}
        onChange={handleFileInput}
        className="hidden"
        aria-hidden="true"
      />
    </div>
  )
}
