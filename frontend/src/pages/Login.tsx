import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setAccessToken } from '../lib/auth'
import { useUIStore } from '../stores/ui'
import GlassPanel from '../components/GlassPanel'
import HermesOrb from '../components/HermesOrb'
import LabelCaps from '../components/LabelCaps'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [preAuthToken, setPreAuthToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [step, setStep] = useState<'credentials' | 'totp'>('credentials')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setStoreToken = useUIStore((s) => s.setAccessToken)

  async function handleCredentials(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json() as Record<string, unknown>
      if (res.status === 200) {
        if (data.requires_totp) {
          setPreAuthToken(data.pre_auth_token as string)
          setStep('totp')
        } else {
          const token = data.access_token as string
          setAccessToken(token)
          setStoreToken(token)
          navigate('/dashboard')
        }
      } else if (res.status === 423) {
        setError('ACCOUNT_LOCKED: ' + String(data.detail ?? ''))
      } else {
        setError(String(data.detail ?? 'LOGIN_FAILED'))
      }
    } catch {
      setError('NETWORK_ERROR')
    } finally {
      setLoading(false)
    }
  }

  async function handleTotp(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/v1/auth/totp/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${preAuthToken}`,
        },
        credentials: 'include',
        body: JSON.stringify({ code: totpCode }),
      })
      const data = await res.json() as Record<string, unknown>
      if (res.status === 200) {
        const token = data.access_token as string
        setAccessToken(token)
        setStoreToken(token)
        navigate('/dashboard')
      } else if (res.status === 423) {
        setError('ACCOUNT_LOCKED: ' + String(data.detail ?? ''))
      } else {
        setError(String(data.detail ?? 'INVALID_CODE'))
      }
    } catch {
      setError('NETWORK_ERROR')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen bg-background flex items-center justify-center relative overflow-hidden">
      <div className="ambient-layer" />
      <div className="relative z-10 flex flex-col items-center gap-6 w-full max-w-sm px-4">
        <HermesOrb state="idle" size={80} />
        <GlassPanel className="w-full">
          <div className="text-center mb-6">
            <h1 className="text-headline-md font-headline-md font-bold text-primary">ODIN</h1>
            <LabelCaps dim>
              {step === 'credentials' ? 'SYSTEM_ACCESS' : 'TWO_FACTOR_AUTH'}
            </LabelCaps>
          </div>

          {step === 'credentials' ? (
            <form onSubmit={(e) => void handleCredentials(e)} className="space-y-4">
              <div>
                <LabelCaps dim as="label" className="block mb-1">EMAIL</LabelCaps>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  className="w-full bg-terminal-black border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary/30 rounded-lg text-code-sm font-code-sm text-on-surface px-3 py-2.5 focus:outline-none disabled:opacity-50"
                  placeholder="user@odin.local"
                  aria-label="Email address"
                />
              </div>
              <div>
                <LabelCaps dim as="label" className="block mb-1">PASSWORD</LabelCaps>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="w-full bg-terminal-black border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary/30 rounded-lg text-code-sm font-code-sm text-on-surface px-3 py-2.5 focus:outline-none disabled:opacity-50"
                  placeholder="..."
                  aria-label="Password"
                />
              </div>
              {error && (
                <p className="text-status-critical text-code-sm font-code-sm" role="alert">{error}</p>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-container text-on-primary-container font-bold py-3 rounded-xl shadow-[0_0_15px_rgba(255,107,0,0.3)] hover:shadow-[0_0_25px_rgba(255,107,0,0.5)] active:scale-95 transition-all disabled:opacity-50 text-code-sm font-code-sm"
              >
                {loading ? 'AUTHENTICATING...' : 'ACCESS_SYSTEM'}
              </button>
            </form>
          ) : (
            <form onSubmit={(e) => void handleTotp(e)} className="space-y-4">
              <p className="text-body-sm font-body-sm text-on-surface-variant text-center">
                Enter your 6-digit authenticator code
              </p>
              <input
                type="text"
                inputMode="numeric"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                required
                maxLength={6}
                disabled={loading}
                className="w-full bg-terminal-black border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary/30 rounded-lg text-code-sm font-code-sm text-on-surface px-3 py-2.5 focus:outline-none tracking-widest text-center text-xl disabled:opacity-50"
                placeholder="000000"
                aria-label="6-digit authentication code"
                autoFocus
              />
              {error && (
                <p className={`text-code-sm font-code-sm text-center ${error.includes('LOCKED') ? 'text-status-critical' : 'text-system-amber'}`} role="alert">
                  {error}
                </p>
              )}
              <button
                type="submit"
                disabled={loading || totpCode.length < 6}
                className="w-full bg-primary-container text-on-primary-container font-bold py-3 rounded-xl shadow-[0_0_15px_rgba(255,107,0,0.3)] active:scale-95 transition-all disabled:opacity-50 text-code-sm font-code-sm"
              >
                {loading ? 'VERIFYING...' : 'VERIFY_CODE'}
              </button>
              <button
                type="button"
                onClick={() => { setStep('credentials'); setError('') }}
                className="w-full text-on-surface-variant hover:text-primary text-code-sm font-code-sm py-2 transition-colors"
              >
                Back to login
              </button>
            </form>
          )}
        </GlassPanel>
      </div>
    </div>
  )
}
