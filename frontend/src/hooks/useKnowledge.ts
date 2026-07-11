import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiJson } from '../lib/api'
import type { KnowledgeDoc } from '../lib/types'

export function useKnowledgeDocs(projectId?: string) {
  const params = projectId ? `?project_id=${projectId}` : ''
  return useQuery({
    queryKey: ['knowledge', projectId ?? null],
    queryFn: () => apiJson<KnowledgeDoc[]>(`/api/v1/knowledge/documents${params}`),
    retry: 1,
  })
}

export function useUploadDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      const res = await apiFetch('/api/v1/knowledge/upload', { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      return res.json() as Promise<KnowledgeDoc>
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['knowledge'] })
    },
  })
}
