interface StatChipProps {
  label: string
  value: string | number
  borderColor?: string
}

export default function StatChip({ label, value, borderColor = 'border-primary' }: StatChipProps) {
  return (
    <div className={`bg-surface-container px-4 py-2 border-l-2 ${borderColor} rounded-sm`}>
      <div className="text-label-caps font-label-caps uppercase text-on-surface-variant opacity-50 leading-4">{label}</div>
      <div className="text-headline-md font-headline-md font-semibold text-on-surface">{value}</div>
    </div>
  )
}
