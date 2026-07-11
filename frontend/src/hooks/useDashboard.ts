import { useQuery } from '@tanstack/react-query'
import { apiJson } from '../lib/api'
import type { DashboardOut } from '../lib/types'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiJson<DashboardOut>('/api/v1/dashboard'),
    refetchInterval: 30_000,
  })
}
