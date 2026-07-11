export interface PriorityTask {
  id: string
  title: string
  status: string
  priority: string
  due_date: string | null
  project_id: string | null
}

export interface RecentFile {
  path: string
  size: number
  mtime: number
}

export interface DashboardOut {
  greeting_name: string
  server_time_utc: string
  priorities: PriorityTask[]
  recent_files: RecentFile[]
  running_tasks: Record<string, unknown>[]
  unread_notifications: number
}

export interface Task {
  id: string
  user_id: string
  project_id: string | null
  title: string
  description: string | null
  status: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'done' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'critical'
  due_date: string | null
  completed_at: string | null
  tags: string[] | null
  created_at: string
  updated_at: string
}

export interface SubTask {
  id: string
  task_id: string
  title: string
  done: boolean
  position: number
  created_at: string
}

export interface Conversation {
  id: string
  user_id: string
  project_id: string | null
  title: string | null
  summary: string | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'tool_result' | 'system'
  content: string | null
  content_blocks: unknown[] | null
  token_count: number | null
  created_at: string
}

export interface Notification {
  id: string
  title: string
  body: string | null
  category: string
  read_at: string | null
  created_at: string
}

export interface Project {
  id: string
  name: string
  status: string
  created_at: string
  updated_at: string
}

export interface Memory {
  id: string
  key: string
  value: string
  source: 'explicit' | 'implicit' | 'suggested'
  access_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeDoc {
  id: string
  project_id: string | null
  filename: string
  status: 'processing' | 'indexed' | 'error'
  chunk_count: number | null
  indexed_at: string | null
  created_at: string
}

export interface FileItem {
  name: string
  path: string
  is_dir: boolean
  size: number | null
  mtime: string | null
}

export interface GatePending {
  approvalId: string
  conversationId: string
  toolName: string
  arguments: Record<string, unknown>
}

export interface Toast {
  id: string
  message: string
  type: 'info' | 'warn' | 'error' | 'success'
}
