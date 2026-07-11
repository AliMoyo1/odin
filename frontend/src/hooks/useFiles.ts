import { useQuery } from '@tanstack/react-query'
import { apiJson } from '../lib/api'
import type { FileItem } from '../lib/types'

export function useFileList(dirPath: string) {
  return useQuery({
    queryKey: ['files', dirPath],
    queryFn: () => apiJson<FileItem[]>(`/api/v1/files/list?path=${encodeURIComponent(dirPath)}`),
    retry: 1,
  })
}
