interface LabelCapsProps {
  children: React.ReactNode
  className?: string
  dim?: boolean
  as?: 'span' | 'div' | 'p' | 'label'
}

export default function LabelCaps({ children, className = '', dim = false, as: Tag = 'span' }: LabelCapsProps) {
  return (
    <Tag className={`text-label-caps font-label-caps uppercase tracking-widest ${dim ? 'opacity-50' : ''} ${className}`}>
      {children}
    </Tag>
  )
}
