import { useQuery } from '@tanstack/react-query'
import { apiJson } from '../lib/api'
import type { Conversation, Message } from '../lib/types'

export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => apiJson<Conversation[]>('/api/v1/conversations'),
  })
}

export function useMessages(conversationId: string | undefined) {
  return useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => apiJson<Message[]>(`/api/v1/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
  })
}
