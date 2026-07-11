import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiJson } from '../lib/api'
import type { Task } from '../lib/types'

export function useTasks(projectId?: string) {
  const params = projectId ? `?project_id=${projectId}` : ''
  return useQuery({
    queryKey: ['tasks', projectId ?? null],
    queryFn: () => apiJson<Task[]>(`/api/v1/tasks${params}`),
  })
}

export function useUpdateTaskStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: Task['status'] }) => {
      const res = await apiFetch(`/api/v1/tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!res.ok) throw new Error(await res.text())
      return res.json() as Promise<Task>
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['tasks'] })
      void qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
