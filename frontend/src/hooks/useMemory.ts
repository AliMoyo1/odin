import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiJson } from '../lib/api'
import type { Memory } from '../lib/types'

export function useMemories() {
  return useQuery({
    queryKey: ['memories'],
    queryFn: () => apiJson<Memory[]>('/api/v1/memories'),
    retry: 1,
  })
}

export function useArchiveMemory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/api/v1/memories/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['memories'] })
    },
  })
}
