// API utilities for data loading
// Uses local JSON data from mock_data_json directory

import { format, formatDistanceToNow, isValid } from 'date-fns'

// ============ SAFE DATE UTILITIES ============

export function safeFormatDate(dateStr: string | null | undefined, formatStr: string = 'MMM d, yyyy'): string {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  if (!isValid(date)) return 'N/A'
  return format(date, formatStr)
}

export function safeFormatDistance(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A'
  const date = new Date(dateStr)
  if (!isValid(date)) return 'N/A'
  return formatDistanceToNow(date, { addSuffix: true })
}

export function isValidDate(dateStr: string | null | undefined): boolean {
  if (!dateStr) return false
  const date = new Date(dateStr)
  return isValid(date)
}

// ============ DATA TYPES ============

export interface Email {
  email_id: string
  thread_id: string
  from_email: string
  from_name?: string
  to_emails: string[]
  subject: string
  body_text: string
  received_utc: string
  actionability_gt: 'actionable' | 'informational' | 'noise'
  sensitivity: string
  correlation_id: string
  processed: boolean
  agent_actions?: string[]
  demo_sender?: boolean
  sender_name: string
  sender_title?: string
  processed_utc?: string
  agent_category?: string
  draft_reply?: string
  triage_result?: {
    category?: 'actionable' | 'informational' | 'noise' | 'unprocessed'
    priority?: string
    suggested_action?: string
  }
  ai_analysis?: {
    summary?: string
    key_points?: string[]
    sentiment?: string
    urgency?: string
    suggested_actions?: string[]
  }
}

export interface Task {
  task_id: string
  title: string
  description: string
  source: string
  source_ref_id?: string
  owner_user_id: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  status: 'todo' | 'in_progress' | 'completed' | 'scheduled' | 'blocked' | 'done'
  due_date_utc?: string
  due_date?: string
  estimated_duration_minutes?: number
  created_utc: string
  sensitivity: string
  correlation_id: string
  tags?: string[]
  category?: string
  client?: string
}

export interface Meeting {
  meeting_id: string
  title: string
  organizer_email: string
  participant_emails: string[]
  scheduled_start_utc: string
  scheduled_end_utc: string
  start_utc?: string
  end_utc?: string
  actual_start_utc?: string
  actual_end_utc?: string
  location: string
  meeting_type: string
  sensitivity: string
  correlation_id: string
  transcript_file?: string
}

export interface MoM {
  meeting_id: string
  title?: string
  date?: string
  attendees?: string[]
  summary?: string
  key_points?: string[]
  key_decisions?: string[]
  decisions?: string[] // Alternative field name
  action_items?: { task: string; owner: string; assignee?: string; due?: string; due_date?: string }[]
  actions?: { task: string; owner: string; assignee?: string; due?: string; due_date?: string }[] // Alternative field name
  next_steps?: string[]
  risks?: string[]
  generated_at?: string
  transcript?: string
}

export interface Followup {
  followup_id: string
  entity_type: string
  entity_id: string
  owner_user_id: string
  reason: string
  last_contacted_utc?: string | null
  next_contact_due_utc: string
  due_date?: string
  recommended_channel: string
  draft_message_gt: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  sensitivity: string
  correlation_id: string
  status?: 'pending' | 'sent' | 'dismissed' | 'snoozed'
  created_utc?: string
}

export interface WellnessConfig {
  version: string
  score: number
  description: string
  score_weights: Record<string, number>
  thresholds: Record<string, Record<string, number>>
  score_levels: Record<string, { min: number; max: number; emoji: string; label: string }>
  burnout_thresholds: Record<string, number>
  proactive_nudges: {
    enabled: boolean
    check_interval_minutes: number
    max_nudges_per_day: number
    quiet_hours: { start: string; end: string }
  }
  focus_blocks: Record<string, number | string>
  mood_tracking: { enabled: boolean; reminder_enabled: boolean; reminder_time: string }
}

export interface MoodEntry {
  timestamp: string
  mood: 'great' | 'good' | 'okay' | 'stressed' | 'overwhelmed'
  notes?: string
}

export interface User {
  user_id: string
  display_name: string
  email: string
  role: string
  department?: string
  manager_id?: string
  timezone?: string
}

export interface EODReport {
  date: string
  completed_tasks: string[]
  pending_tasks: string[]
  blockers: string[]
  highlights: string[]
  meetings_attended: number
  emails_processed: number
}

export interface WeeklyReport {
  week_start: string
  week_end: string
  total_tasks_completed: number
  total_meetings: number
  wellness_average: number
  highlights: string[]
  areas_for_improvement: string[]
}

export interface AuditLog {
  timestamp: string
  action: string
  user_id: string
  details: string
  entity_type?: string
  entity_id?: string
}

export interface LLMUsage {
  timestamp: string
  model: string
  tokens_in: number
  tokens_out: number
  cost_usd: number
  agent: string
  operation: string
}

// ============ DATA LOADING FUNCTIONS ============

// All data is loaded from JSON files copied during build
// These files are served statically from the public directory

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8002/api/v1';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-unprotected';

// Use Next.js API route as proxy for emails to avoid CORS issues
const USE_PROXY = true;

const defaultHeaders = {
  'Content-Type': 'application/json',
  'x-api-key': API_KEY,
};

export async function fetchEmails(): Promise<Email[]> {
  // Use Next.js API route as proxy to avoid CORS issues
  const url = USE_PROXY ? '/api/emails' : `${API_BASE}/emails`
  try {
    const response = await fetch(url, { headers: USE_PROXY ? {} : defaultHeaders })
    if (!response.ok) throw new Error(`Failed to fetch emails: ${response.status}`)
    return await response.json()
  } catch (error) {
    console.error('Error fetching emails:', error)
    return mockEmails
  }
}

export async function fetchTasks(): Promise<Task[]> {
  // Use Next.js API route as proxy to avoid CORS issues
  const url = USE_PROXY ? '/api/tasks' : `${API_BASE}/tasks`
  try {
    const response = await fetch(url, { headers: USE_PROXY ? {} : defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch tasks')
    return await response.json()
  } catch (error) {
    console.error('Error fetching tasks:', error)
    return mockTasks
  }
}

export async function fetchMeetings(): Promise<Meeting[]> {
  // Use Next.js API route as proxy to avoid CORS issues
  const url = USE_PROXY ? '/api/meetings' : `${API_BASE}/meetings`
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error('Failed to fetch meetings')
    return await response.json()
  } catch (error) {
    console.error('Error fetching meetings:', error)
    return mockMeetings
  }
}

export async function fetchMoM(meetingId: string): Promise<MoM | null> {
  try {
    // Try backend API first
    const url = USE_PROXY ? `/api/meetings/${meetingId}/mom` : `${API_BASE}/meetings/${meetingId}/mom`
    const response = await fetch(url)
    if (response.ok) {
      const data = await response.json()
      if (data) return data
    }
    
    // Fallback to static file
    const staticResponse = await fetch(`/data/meetings/mom/${meetingId}.json`)
    if (!staticResponse.ok) return null
    return await staticResponse.json()
  } catch (error) {
    console.error('Error fetching MoM:', error)
    return null
  }
}

export async function fetchTranscript(filename: string): Promise<string | null> {
  try {
    // Extract meeting ID from filename if possible (e.g., "mtg_acme_phase1_retro.txt" -> "mtg_acme_phase1_retro")
    const meetingId = filename.replace('.txt', '')
    
    // Try backend API first
    const url = USE_PROXY ? `/api/meetings/${meetingId}/transcript` : `${API_BASE}/meetings/${meetingId}/transcript`
    const response = await fetch(url)
    if (response.ok) {
      const text = await response.text()
      if (text) return text
    }
    
    // Fallback to static file
    const staticResponse = await fetch(`/data/meetings/transcripts/${filename}`)
    if (!staticResponse.ok) return null
    return await staticResponse.text()
  } catch (error) {
    console.error('Error fetching transcript:', error)
    return null
  }
}

export async function fetchFollowups(): Promise<Followup[]> {
  // Use Next.js API route as proxy to avoid CORS issues
  const url = USE_PROXY ? '/api/followups' : `${API_BASE}/followups`
  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error('Failed to fetch followups')
    return await response.json()
  } catch (error) {
    console.error('Error fetching followups:', error)
    return []
  }
}

export async function fetchWellnessConfig(): Promise<WellnessConfig | null> {
  try {
    const response = await fetch(`${API_BASE}/wellness`)
    if (!response.ok) return null
    return await response.json()
  } catch (error) {
    console.error('Error fetching wellness config:', error)
    return null
  }
}

export async function fetchMoodHistory(): Promise<MoodEntry[]> {
  try {
    const response = await fetch('/data/wellness/mood_history.json')
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching mood history:', error)
    return []
  }
}

export async function fetchBreakSuggestions(): Promise<any[]> {
  try {
    const response = await fetch('/data/wellness/break_suggestions.json')
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching break suggestions:', error)
    return []
  }
}

export async function fetchUsers(): Promise<User[]> {
  try {
    const response = await fetch(`${API_BASE}/users`)
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching users:', error)
    return []
  }
}

export async function fetchEODReport(): Promise<EODReport | null> {
  try {
    const response = await fetch('/data/reporting/eod.json')
    if (!response.ok) return null
    return await response.json()
  } catch (error) {
    console.error('Error fetching EOD report:', error)
    return null
  }
}

export async function fetchWeeklyReport(): Promise<WeeklyReport | null> {
  try {
    const response = await fetch('/data/reporting/weekly.json')
    if (!response.ok) return null
    return await response.json()
  } catch (error) {
    console.error('Error fetching weekly report:', error)
    return null
  }
}

export async function fetchAuditLog(): Promise<AuditLog[]> {
  try {
    const response = await fetch('/data/governance/audit_log.json')
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching audit log:', error)
    return []
  }
}

export async function fetchLLMUsage(): Promise<LLMUsage[]> {
  try {
    const response = await fetch('/data/governance/llm_usage.json')
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching LLM usage:', error)
    return []
  }
}

export async function fetchPendingActions(): Promise<any[]> {
  try {
    const response = await fetch('/data/governance/pending_actions.json')
    if (!response.ok) return []
    return await response.json()
  } catch (error) {
    console.error('Error fetching pending actions:', error)
    return []
  }
}

// ============ MOCK DATA (Fallback) ============

export const mockEmails: Email[] = [
  {
    email_id: 'eml_mock_1',
    thread_id: 'thr_mock_1',
    from_email: 'sara.johnson@acmecorp.com',
    to_emails: ['kowshik.naidu@contoso.com'],
    subject: 'Need status update for tomorrow\'s meeting',
    body_text: `Hi Kowshik,

Quick request - I need a status update on the Acme project for tomorrow's steering committee meeting.

Can you please send me:
- Current progress (% complete)
- Any blockers or risks
- Updated ETA for Phase 2

I need this by EOD today so I can prepare the slides.

Thanks!
Sara Johnson`,
    received_utc: new Date(Date.now() - 3600000).toISOString(),
    actionability_gt: 'actionable',
    sensitivity: 'internal',
    correlation_id: 'corr_mock_1',
    processed: true,
    agent_actions: ['create_task', 'draft_email_reply'],
    sender_name: 'Sara Johnson',
    sender_title: 'Product Manager, Acme Corp',
  },
  {
    email_id: 'eml_mock_2',
    thread_id: 'thr_mock_2',
    from_email: 'david.chen@techvision.com',
    to_emails: ['kowshik.naidu@contoso.com'],
    subject: 'Can we sync this week? Need 30 mins',
    body_text: `Hi Kowshik,

Hope you're having a good week!

I'd like to schedule a quick sync to discuss the Q2 roadmap priorities.

Would Thursday 2-3 PM work?

Thanks!
David Chen`,
    received_utc: new Date(Date.now() - 7200000).toISOString(),
    actionability_gt: 'actionable',
    sensitivity: 'internal',
    correlation_id: 'corr_mock_2',
    processed: false,
    sender_name: 'David Chen',
    sender_title: 'CTO, TechVision Inc',
  },
]

export const mockTasks: Task[] = [
  {
    task_id: 'tsk_mock_1',
    title: 'URGENT: Fix Acme CoreAPI auth token expiry issue',
    description: 'Critical P0 blocker for Feb 5 launch.',
    source: 'email',
    owner_user_id: 'usr_kowshik_naidu',
    priority: 'P0',
    status: 'in_progress',
    due_date_utc: new Date(Date.now() + 86400000).toISOString(),
    created_utc: new Date(Date.now() - 172800000).toISOString(),
    sensitivity: 'confidential',
    correlation_id: 'corr_mock_1',
    tags: ['acme', 'critical', 'api'],
    category: 'Client Work',
  },
  {
    task_id: 'tsk_mock_2',
    title: 'Review TechVision Phase 2 architecture',
    description: 'Deep dive technical review.',
    source: 'email',
    owner_user_id: 'usr_kowshik_naidu',
    priority: 'P1',
    status: 'todo',
    due_date_utc: new Date(Date.now() + 172800000).toISOString(),
    created_utc: new Date(Date.now() - 86400000).toISOString(),
    sensitivity: 'confidential',
    correlation_id: 'corr_mock_2',
    tags: ['techvision', 'architecture'],
    category: 'General',
  },
]

export const mockMeetings: Meeting[] = [
  {
    meeting_id: 'mtg_mock_1',
    title: 'Team Standup',
    organizer_email: 'kowshik.naidu@contoso.com',
    participant_emails: ['kowshik.naidu@contoso.com', 'priya.sharma@contoso.com'],
    scheduled_start_utc: new Date(Date.now() + 3600000).toISOString(),
    scheduled_end_utc: new Date(Date.now() + 5400000).toISOString(),
    location: 'Teams',
    meeting_type: 'status',
    sensitivity: 'internal',
    correlation_id: 'corr_mtg_1',
    transcript_file: 'standup_2025_01_30.txt',
  },
  {
    meeting_id: 'mtg_mock_2',
    title: 'Project Kickoff - Q1 Initiative',
    organizer_email: 'sara.johnson@acmecorp.com',
    participant_emails: ['sara.johnson@acmecorp.com', 'kowshik.naidu@contoso.com', 'david.chen@techvision.com'],
    scheduled_start_utc: new Date(Date.now() - 7200000).toISOString(),
    scheduled_end_utc: new Date(Date.now() - 3600000).toISOString(),
    location: 'Acme Corp - Room 302',
    meeting_type: 'kickoff',
    sensitivity: 'internal',
    correlation_id: 'corr_mtg_2',
    transcript_file: 'kickoff_2025_01_28.txt',
  },
]

// ============ HELPER FUNCTIONS ============

export function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'P0': return 'destructive'
    case 'P1': return 'warning'
    case 'P2': return 'secondary'
    case 'P3': return 'default'
    default: return 'default'
  }
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'completed': return 'success'
    case 'in_progress': return 'warning'
    case 'blocked': return 'destructive'
    case 'scheduled': return 'secondary'
    default: return 'default'
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity) {
    case 'critical': return 'destructive'
    case 'high': return 'warning'
    case 'medium': return 'secondary'
    case 'low': return 'default'
    default: return 'default'
  }
}

// ============ TASK MUTATION FUNCTIONS ============

export async function completeTask(taskId: string): Promise<boolean> {
  try {
    const url = USE_PROXY ? `/api/tasks/${taskId}` : `${API_BASE}/tasks/${taskId}`
    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'completed' })
    })
    if (!response.ok) throw new Error('Failed to complete task')
    return true
  } catch (error) {
    console.error('Error completing task:', error)
    return false
  }
}

export async function updateTaskStatus(taskId: string, status: string): Promise<boolean> {
  try {
    const url = USE_PROXY ? `/api/tasks/${taskId}` : `${API_BASE}/tasks/${taskId}`
    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
    if (!response.ok) throw new Error('Failed to update task status')
    return true
  } catch (error) {
    console.error('Error updating task status:', error)
    return false
  }
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

// ============ AI AGENT API FUNCTIONS ============

// Wellness AI endpoints
export async function fetchWellnessScore(userEmail: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/score`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to fetch wellness score')
    return await response.json()
  } catch (error) {
    console.error('Error fetching wellness score:', error)
    return null
  }
}

export async function fetchWellnessJoke(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/joke`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch joke')
    return await response.json()
  } catch (error) {
    console.error('Error fetching joke:', error)
    return null
  }
}

export async function fetchWellnessMotivation(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/motivate`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch motivation')
    return await response.json()
  } catch (error) {
    console.error('Error fetching motivation:', error)
    return null
  }
}

export async function fetchWellnessBreak(breakType: string = 'short'): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/break`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ break_type: breakType })
    })
    if (!response.ok) throw new Error('Failed to fetch break suggestion')
    return await response.json()
  } catch (error) {
    console.error('Error fetching break suggestion:', error)
    return null
  }
}

export async function fetchBreathingExercise(exerciseType: string = 'box'): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/breathing`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ exercise_type: exerciseType })
    })
    if (!response.ok) throw new Error('Failed to fetch breathing exercise')
    return await response.json()
  } catch (error) {
    console.error('Error fetching breathing exercise:', error)
    return null
  }
}

export async function fetchBurnoutRisk(userEmail: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/burnout`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to fetch burnout risk')
    return await response.json()
  } catch (error) {
    console.error('Error fetching burnout risk:', error)
    return null
  }
}

export async function fetchFocusBlocks(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/focus_blocks`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch focus blocks')
    return await response.json()
  } catch (error) {
    console.error('Error fetching focus blocks:', error)
    return []
  }
}

export async function fetchMeetingDetox(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/meeting_detox`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch meeting detox')
    return await response.json()
  } catch (error) {
    console.error('Error fetching meeting detox:', error)
    return []
  }
}

export async function logMood(mood: string, userEmail: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/wellness/mood`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ mood, user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to log mood')
    return await response.json()
  } catch (error) {
    console.error('Error logging mood:', error)
    return null
  }
}

// Task AI endpoints
export async function fetchDayPlan(userEmail: string): Promise<any> {
  try {
    const url = USE_PROXY ? '/api/ai/plan_today' : `${API_BASE}/ai/plan_today`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to fetch day plan')
    return await response.json()
  } catch (error) {
    console.error('Error fetching day plan:', error)
    return null
  }
}

// Nudges/Followup AI endpoints  
export async function fetchNudges(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/ai/nudges`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch nudges')
    return await response.json()
  } catch (error) {
    console.error('Error fetching nudges:', error)
    return []
  }
}

// Reports AI endpoints
export async function fetchEODReportAI(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/ai/reports/eod`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch EOD report')
    return await response.json()
  } catch (error) {
    console.error('Error fetching EOD report:', error)
    return []
  }
}

export async function fetchWeeklyReportAI(): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/ai/reports/weekly`, { headers: defaultHeaders })
    if (!response.ok) throw new Error('Failed to fetch weekly report')
    return await response.json()
  } catch (error) {
    console.error('Error fetching weekly report:', error)
    return []
  }
}

// Email AI endpoints
export async function analyzeEmail(emailId: string, userEmail: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/email/analyze`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ email_id: emailId, user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to analyze email')
    return await response.json()
  } catch (error) {
    console.error('Error analyzing email:', error)
    return null
  }
}

// Meeting AI endpoints
export async function generateMeetingMoM(meetingId: string): Promise<any> {
  try {
    const response = await fetch(`${API_BASE}/ai/meeting/mom`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ meeting_id: meetingId })
    })
    if (!response.ok) throw new Error('Failed to generate MoM')
    return await response.json()
  } catch (error) {
    console.error('Error generating MoM:', error)
    return null
  }
}

// Assistant/Chat AI endpoints
export async function startAssistantChat(userEmail: string): Promise<string | null> {
  try {
    const url = USE_PROXY ? '/api/assistant/start' : `${API_BASE}/assistant/start`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to start chat')
    const data = await response.json()
    return data.session_id
  } catch (error) {
    console.error('Error starting chat:', error)
    return null
  }
}

export async function sendAssistantMessage(sessionId: string | null, userEmail: string, message: string): Promise<any> {
  try {
    const url = USE_PROXY ? '/api/assistant/chat' : `${API_BASE}/assistant/chat`
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, user_email: userEmail, message })
    })
    
    if (!response.ok) {
      const errorData = await response.text()
      throw new Error(`Failed to send message: ${response.status} ${response.statusText} - ${errorData}`)
    }
    
    const data = await response.json()
    
    // Validate response structure
    if (!data.response) {
      console.warn('Incomplete response from server:', data)
      return {
        response: 'I received your message but could not generate a response. Please try again.',
        session_id: data.session_id || sessionId,
        intent: data.intent || 'chat',
        confidence: data.confidence || 0
      }
    }
    
    return data
  } catch (error) {
    console.error('Error sending message:', error)
    throw error // Re-throw to allow caller to handle
  }
}

export async function endAssistantChat(sessionId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/assistant/end`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ session_id: sessionId })
    })
    return response.ok
  } catch (error) {
    console.error('Error ending chat:', error)
    return false
  }
}

// Autonomous agent endpoints
export async function fetchAutonomousStatus(): Promise<any> {
  try {
    const url = USE_PROXY ? '/api/autonomous/status' : `${API_BASE}/autonomous/status`
    const response = await fetch(url)
    if (!response.ok) throw new Error('Failed to fetch autonomous status')
    return await response.json()
  } catch (error) {
    console.error('Error fetching autonomous status:', error)
    return { is_running: false }
  }
}

export async function startAutonomousAgent(): Promise<boolean> {
  try {
    const url = USE_PROXY ? '/api/autonomous/start' : `${API_BASE}/autonomous/start`
    const response = await fetch(url, {
      method: 'POST',
    })
    return response.ok
  } catch (error) {
    console.error('Error starting autonomous agent:', error)
    return false
  }
}

export async function stopAutonomousAgent(): Promise<boolean> {
  try {
    const url = USE_PROXY ? '/api/autonomous/stop' : `${API_BASE}/autonomous/stop`
    const response = await fetch(url, {
      method: 'POST',
    })
    return response.ok
  } catch (error) {
    console.error('Error stopping autonomous agent:', error)
    return false
  }
}

// Proactive alerts endpoints
export async function fetchProactiveNotifications(userEmail: string): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/proactive/notifications`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to fetch proactive notifications')
    return await response.json()
  } catch (error) {
    console.error('Error fetching proactive notifications:', error)
    return []
  }
}

export async function runProactiveCheck(userEmail: string): Promise<any[]> {
  try {
    const response = await fetch(`${API_BASE}/proactive/check`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ user_email: userEmail })
    })
    if (!response.ok) throw new Error('Failed to run proactive check')
    return await response.json()
  } catch (error) {
    console.error('Error running proactive check:', error)
    return []
  }
}
