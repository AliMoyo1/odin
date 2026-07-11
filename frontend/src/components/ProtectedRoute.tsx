import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useUIStore } from '../stores/ui'
import { setAccessToken } from '../lib/auth'
import HermesOrb from './HermesOrb'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const accessToken = useUIStore((s) => s.accessToken)
  const setStoreToken = useUIStore((s) => s.setAccessToken)
  const [checking, setChecking] = useState(!accessToken)

  useEffect(() => {
    if (accessToken) return
    void (async () => {
      try {
        const res = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include' })
        if (res.ok) {
          const data = await res.json() as { access_token: string }
          setAccessToken(data.access_token)
          setStoreToken(data.access_token)
        }
      } finally {
        setChecking(false)
      }
    })()
  }, [accessToken, setStoreToken])

  if (checking) {
    return (
      <div className="h-screen bg-background flex items-center justify-center">
        <HermesOrb state="thinking" size={60} />
      </div>
    )
  }

  if (!accessToken) return <Navigate to="/login" replace />
  return <>{children}</>
}
