import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useUIStore } from '../stores/ui'
import { globalSocket } from '../lib/ws'
import Sidebar from './Sidebar'
import TopBar from './TopBar'
import ConsoleDock from './ConsoleDock'
import Toaster from './Toast'
import { ApprovalModal } from './chat/ApprovalModal'
import type { GatePending } from '../lib/types'

export default function AppShell() {
  const pendingGate = useUIStore((s) => s.pendingGate)
  const setPendingGate = useUIStore((s) => s.setPendingGate)
  const setIsRunActive = useUIStore((s) => s.setIsRunActive)

  useEffect(() => {
    void globalSocket.connect()

    const off = globalSocket.on((e) => {
      try {
        const ev = JSON.parse(e.data as string) as { type: string; data?: Record<string, unknown> }

        if (ev.type === 'gate.locked' && ev.data) {
          setPendingGate({
            approvalId: ev.data.approval_id as string,
            conversationId: ev.data.conversation_id as string,
            toolName: ev.data.tool_name as string,
            arguments: (ev.data.arguments ?? {}) as Record<string, unknown>,
          } satisfies GatePending)
        }
        if (ev.type === 'run.started') setIsRunActive(true)
        if (ev.type === 'message.done' || ev.type === 'run.ended') setIsRunActive(false)
      } catch { /* ignore malformed */ }
    })

    return () => {
      off()
      globalSocket.close()
    }
  }, [setPendingGate, setIsRunActive])

  return (
    <div className="h-screen overflow-hidden bg-background">
      {/* z-index: sidebar 50, topbar/console 40, toasts 90, gate modal 100 */}
      <div className="ambient-layer" />
      <Sidebar />
      <TopBar />
      <main className="ml-[280px] pt-16 pb-12 h-screen overflow-y-auto">
        <Outlet />
      </main>
      <ConsoleDock />
      {pendingGate && (
        <ApprovalModal
          approvalId={pendingGate.approvalId}
          toolName={pendingGate.toolName}
          arguments={pendingGate.arguments}
          onClose={() => setPendingGate(null)}
        />
      )}
      <Toaster />
    </div>
  )
}
