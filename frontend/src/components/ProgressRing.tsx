const RADIUS = 42
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

interface ProgressRingProps {
  percent: number
  label: string
  color?: string
  size?: number
}

export default function ProgressRing({ percent, label, color = '#ff6b00', size = 100 }: ProgressRingProps) {
  const offset = CIRCUMFERENCE * (1 - Math.min(100, Math.max(0, percent)) / 100)

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="50" cy="50" r={RADIUS} fill="none" stroke="#20201f" strokeWidth="6" />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
        <text
          x="50"
          y="50"
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            fontSize: 16,
            fontFamily: 'JetBrains Mono',
            fontWeight: 700,
            fill: '#e5e2e1',
            transform: 'rotate(90deg)',
            transformOrigin: '50% 50%',
          }}
        >
          {Math.round(percent)}%
        </text>
      </svg>
      <span className="text-label-caps font-label-caps uppercase text-on-surface-variant">{label}</span>
    </div>
  )
}
