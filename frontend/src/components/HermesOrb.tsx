interface HermesOrbProps {
  state?: 'idle' | 'thinking'
  size?: number
  className?: string
}

export default function HermesOrb({ state = 'idle', size = 40, className = '' }: HermesOrbProps) {
  return (
    <div
      className={`shrink-0 ${state === 'thinking' ? 'hermes-orb-thinking' : 'hermes-orb'} ${className}`}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'radial-gradient(circle at 35% 30%, #ffdbcc 0%, #ff6b00 35%, #7a3000 75%, #351000 100%)',
      }}
      aria-hidden="true"
    />
  )
}
