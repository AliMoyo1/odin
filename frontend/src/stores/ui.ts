import { create } from 'zustand'
import type { GatePending, Toast } from '../lib/types'

interface UIState {
  accessToken: string | null
  setAccessToken: (token: string | null) => void
  isRunActive: boolean
  setIsRunActive: (active: boolean) => void
  pendingGate: GatePending | null
  setPendingGate: (gate: GatePending | null) => void
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

let _toastSeq = 0

export const useUIStore = create<UIState>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  isRunActive: false,
  setIsRunActive: (active) => set({ isRunActive: active }),
  pendingGate: null,
  setPendingGate: (gate) => set({ pendingGate: gate }),
  toasts: [],
  addToast: (toast) =>
    set((s) => ({ toasts: [...s.toasts, { ...toast, id: String(++_toastSeq) }] })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
