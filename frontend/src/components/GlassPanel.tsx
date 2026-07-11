import LabelCaps from './LabelCaps'

interface GlassPanelProps {
  label?: string
  children: React.ReactNode
  className?: string
  headerRight?: React.ReactNode
}

export default function GlassPanel({ label, children, className = '', headerRight }: GlassPanelProps) {
  return (
    <div className={`glass-panel p-4 rounded-xl ${className}`}>
      {label && (
        <div className="border-b border-glass-border mb-3 pb-2 flex items-center justify-between">
          <LabelCaps>{label}</LabelCaps>
          {headerRight}
        </div>
      )}
      {children}
    </div>
  )
}
