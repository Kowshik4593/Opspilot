// Shared TypeScript types for the frontend

export type Priority = 'P0' | 'P1' | 'P2' | 'P3'

export type TaskStatus = 'open' | 'in_progress' | 'completed' | 'blocked'

export type MeetingStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled'

export type EmailActionability = 'actionable' | 'informational' | 'noise'

export interface User {
  id: string
  name: string
  email: string
  avatar_url?: string
  role?: string
}

export interface Email {
  id: string
  from: string
  to: string[]
  cc?: string[]
  bcc?: string[]
  subject: string
  body: string
  html_body?: string
  timestamp: string
  read: boolean
  starred?: boolean
  actionability_gt?: EmailActionability
  processed?: boolean
  priority?: Priority
  labels?: string[]
  attachments?: Attachment[]
}

export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  priority: Priority
  assigned_to: string
  assigned_by?: string
  due_date?: string
  created_at: string
  updated_at?: string
  completed_at?: string
  tags?: string[]
  attachments?: Attachment[]
}

export interface Meeting {
  id: string
  title: string
  description?: string
  start_time: string
  end_time: string
  attendees: string[]
  organizer?: string
  location?: string
  meeting_url?: string
  status: MeetingStatus
  agenda?: string
  notes?: string
  recording_url?: string
}

export interface Attachment {
  id: string
  name: string
  size: number
  type: string
  url: string
}

export interface Notification {
  id: string
  type: 'success' | 'warning' | 'info' | 'error'
  title: string
  message: string
  timestamp: Date
  read: boolean
  action_url?: string
  action_label?: string
}

export interface Report {
  id: string
  title: string
  type: 'daily' | 'weekly' | 'monthly'
  generated_at: string
  metrics: ReportMetric[]
  summary: string
}

export interface ReportMetric {
  label: string
  value: number | string
  change?: number
  unit?: string
}

export interface WellnessData {
  user_id: string
  date: string
  mood?: number // 1-5 scale
  energy_level?: number // 1-5 scale
  breaks_taken: number
  work_hours: number
  suggestions?: string[]
}

export interface AgentActivity {
  id: string
  agent_name: string
  action: string
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  result?: any
  error?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: Record<string, any>
}

export interface ChatSession {
  id: string
  user_id: string
  started_at: string
  ended_at?: string
  messages: ChatMessage[]
  context?: Record<string, any>
}

// API Response types
export interface ApiResponse<T> {
  data: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
  has_prev: boolean
}

// Form types
export interface EmailComposeForm {
  to: string[]
  cc?: string[]
  bcc?: string[]
  subject: string
  body: string
  attachments?: File[]
}

export interface TaskCreateForm {
  title: string
  description: string
  priority: Priority
  assigned_to: string
  due_date?: string
  tags?: string[]
}

export interface MeetingCreateForm {
  title: string
  description?: string
  start_time: string
  end_time: string
  attendees: string[]
  location?: string
  meeting_url?: string
}

// Filter types
export interface EmailFilters {
  actionability?: EmailActionability
  priority?: Priority
  read?: boolean
  starred?: boolean
  from?: string
  has_attachments?: boolean
}

export interface TaskFilters {
  status?: TaskStatus
  priority?: Priority
  assigned_to?: string
  due_before?: string
  due_after?: string
  tags?: string[]
}

export interface MeetingFilters {
  status?: MeetingStatus
  organizer?: string
  attendee?: string
  start_after?: string
  start_before?: string
}

// Sort types
export type SortOrder = 'asc' | 'desc'

export interface SortConfig<T> {
  key: keyof T
  order: SortOrder
}

// UI State types
export interface LoadingState {
  isLoading: boolean
  error?: string
}

export interface PaginationState {
  page: number
  pageSize: number
  total: number
}

export interface SelectionState<T> {
  selected: T[]
  isAllSelected: boolean
}
