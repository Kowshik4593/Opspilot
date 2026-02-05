'use client'

import { useState, useEffect } from 'react'
import { 
  Bot, Play, Square, RefreshCw, Mail, CheckSquare, Clock, Brain, Eye, Zap,
  AlertTriangle, CheckCircle, XCircle, Settings, Activity, Inbox, Bell,
  TrendingUp, BarChart3, ArrowRight, Loader2, Shield
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { clsx } from 'clsx'
import { format } from 'date-fns'
import { 
  fetchAutonomousStatus, startAutonomousAgent, stopAutonomousAgent,
  fetchProactiveNotifications, runProactiveCheck, fetchEmails
} from '@/lib/api'

interface AgentEvent {
  id: string
  timestamp: string
  eventType: 'thinking' | 'action' | 'observation' | 'completed' | 'error' | 'approval_needed' | 'new_email'
  content: string
  emailId?: string
}

interface PendingApproval {
  id: string
  actionType: string
  description: string
  risk: 'low' | 'medium' | 'high'
  timestamp: string
  emailId?: string
}

interface AgentTask {
  id: string
  title: string
  priority: 'P0' | 'P1' | 'P2' | 'P3'
  sourceRef: string
  createdAt: string
}

interface AgentFollowup {
  id: string
  reason: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  dueDate: string
}

// Fallback mock unprocessed emails (used only if API fails)
const mockUnprocessedEmails: { email_id: string; subject: string; from_email: string; received_utc: string }[] = []

// Simulated agent events
const mockEvents: AgentEvent[] = [
  { id: '1', timestamp: new Date(Date.now() - 60000).toISOString(), eventType: 'new_email', content: 'New email detected from legal@acme.com', emailId: 'em_new_001' },
  { id: '2', timestamp: new Date(Date.now() - 55000).toISOString(), eventType: 'thinking', content: 'Analyzing email content and determining priority...' },
  { id: '3', timestamp: new Date(Date.now() - 50000).toISOString(), eventType: 'action', content: 'Classifying email as "actionable" with high priority' },
  { id: '4', timestamp: new Date(Date.now() - 45000).toISOString(), eventType: 'observation', content: 'Contract keywords detected. Legal review required within 24h.' },
  { id: '5', timestamp: new Date(Date.now() - 40000).toISOString(), eventType: 'action', content: 'Creating task: "Review Acme contract" with P1 priority' },
  { id: '6', timestamp: new Date(Date.now() - 35000).toISOString(), eventType: 'completed', content: 'Email processed successfully. Task created, draft reply prepared.' },
]

// Simulated agent-created tasks
const mockAgentTasks: AgentTask[] = [
  { id: 't1', title: 'Review Acme contract terms', priority: 'P1', sourceRef: 'em_new_001', createdAt: new Date(Date.now() - 40000).toISOString() },
  { id: 't2', title: 'Follow up on TechVision demo', priority: 'P2', sourceRef: 'em_auto_002', createdAt: new Date(Date.now() - 3600000).toISOString() },
  { id: 't3', title: 'Respond to budget inquiry', priority: 'P2', sourceRef: 'em_auto_003', createdAt: new Date(Date.now() - 7200000).toISOString() },
]

// Simulated agent-created followups
const mockAgentFollowups: AgentFollowup[] = [
  { id: 'f1', reason: 'Awaiting contract signature from Acme', severity: 'high', dueDate: new Date(Date.now() + 86400000).toISOString() },
  { id: 'f2', reason: 'TechVision license renewal discussion', severity: 'medium', dueDate: new Date(Date.now() + 172800000).toISOString() },
]

// Simulated proactive alerts
const mockAlerts = [
  { id: 'a1', title: 'Burnout Risk Detected', message: 'Your wellness score dropped below 60. Consider taking a break.', priority: 'high', timestamp: new Date(Date.now() - 1800000).toISOString() },
  { id: 'a2', title: 'Deadline Approaching', message: 'TechVision demo prep due in 4 hours.', priority: 'medium', timestamp: new Date(Date.now() - 3600000).toISOString() },
]

export default function ActivityPage() {
  const [isAgentRunning, setIsAgentRunning] = useState(true)
  const [events, setEvents] = useState<AgentEvent[]>(mockEvents)
  const [unprocessedEmails, setUnprocessedEmails] = useState(mockUnprocessedEmails)
  const [processingEmailId, setProcessingEmailId] = useState<string | null>(null)
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>(mockAgentTasks)
  const [agentFollowups, setAgentFollowups] = useState<AgentFollowup[]>(mockAgentFollowups)
  const [alerts, setAlerts] = useState(mockAlerts)
  const [proactiveEnabled, setProactiveEnabled] = useState(true)
  const [loading, setLoading] = useState(false)
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set())
  const userEmail = 'alice@example.com'

  const [processedCount, setProcessedCount] = useState(0)
  const tasksCreated = agentTasks.length

  useEffect(() => {
    loadAgentStatus()
    loadUnprocessedEmails()
  }, [])

  const loadUnprocessedEmails = async () => {
    try {
      const allEmails = await fetchEmails()
      const unprocessed = allEmails.filter(e => !e.processed)
      const processed = allEmails.filter(e => e.processed)
      setUnprocessedEmails(unprocessed.map(e => ({
        email_id: e.email_id,
        subject: e.subject,
        from_email: e.from_email,
        received_utc: e.received_utc
      })))
      setProcessedCount(processed.length)
    } catch (error) {
      console.error('Error loading emails:', error)
    }
  }

  const loadAgentStatus = async () => {
    const status = await fetchAutonomousStatus()
    setIsAgentRunning(status?.is_running || false)
  }

  const toggleAgent = async () => {
    if (isAgentRunning) {
      await stopAutonomousAgent()
      setIsAgentRunning(false)
    } else {
      await startAutonomousAgent()
      setIsAgentRunning(true)
    }
  }

  const processEmail = async (emailId: string) => {
    setProcessingEmailId(emailId)
    
    // Simulate processing with events
    const newEvents: AgentEvent[] = []
    
    await new Promise(r => setTimeout(r, 500))
    newEvents.push({ id: Date.now().toString(), timestamp: new Date().toISOString(), eventType: 'thinking', content: 'Analyzing email content and context...' })
    setEvents(prev => [...newEvents, ...prev])
    
    await new Promise(r => setTimeout(r, 800))
    newEvents.push({ id: (Date.now() + 1).toString(), timestamp: new Date().toISOString(), eventType: 'action', content: 'Classifying email priority and category...' })
    setEvents(prev => [newEvents[newEvents.length - 1], ...prev])
    
    await new Promise(r => setTimeout(r, 600))
    newEvents.push({ id: (Date.now() + 2).toString(), timestamp: new Date().toISOString(), eventType: 'observation', content: 'Email requires action. Creating task...' })
    setEvents(prev => [newEvents[newEvents.length - 1], ...prev])
    
    await new Promise(r => setTimeout(r, 500))
    newEvents.push({ id: (Date.now() + 3).toString(), timestamp: new Date().toISOString(), eventType: 'completed', content: 'Email processed successfully!' })
    setEvents(prev => [newEvents[newEvents.length - 1], ...prev])
    
    // Remove from unprocessed
    setUnprocessedEmails(prev => prev.filter(e => e.email_id !== emailId))
    setProcessingEmailId(null)
  }

  const runManualCheck = async () => {
    setLoading(true)
    try {
      const results = await runProactiveCheck(userEmail)
      if (results && results.length > 0) {
        const newAlerts = results.map((r: any, i: number) => ({
          id: `a${Date.now()}_${i}`,
          title: r.title || 'Check Complete',
          message: r.message || 'Proactive check completed.',
          priority: r.priority || 'low',
          timestamp: new Date().toISOString()
        }))
        setAlerts(prev => [...newAlerts, ...prev])
      } else {
        const newAlert = {
          id: `a${Date.now()}`,
          title: 'Manual Check Complete',
          message: 'All systems nominal. No critical issues found.',
          priority: 'low' as const,
          timestamp: new Date().toISOString()
        }
        setAlerts(prev => [newAlert, ...prev])
      }
      // Refresh unprocessed emails after check
      await loadUnprocessedEmails()
    } catch (error) {
      console.error('Error running check:', error)
    }
    setLoading(false)
  }

  const dismissAlert = (alertId: string) => {
    setDismissedAlerts(prev => new Set([...prev, alertId]))
  }

  const getEventIcon = (type: AgentEvent['eventType']) => {
    switch (type) {
      case 'thinking': return <Brain className="h-4 w-4 text-yellow-500" />
      case 'action': return <Zap className="h-4 w-4 text-blue-500" />
      case 'observation': return <Eye className="h-4 w-4 text-green-500" />
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error': return <XCircle className="h-4 w-4 text-red-500" />
      case 'approval_needed': return <AlertTriangle className="h-4 w-4 text-orange-500" />
      case 'new_email': return <Mail className="h-4 w-4 text-purple-500" />
      default: return <Activity className="h-4 w-4" />
    }
  }

  const activeAlerts = alerts.filter(a => !dismissedAlerts.has(a.id))

  return (
    <div className="container py-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-1">🤖 Agent Activity</h1>
          <p className="text-muted-foreground">
            Monitor the AI agent as it autonomously processes incoming emails
          </p>
        </div>
        <Button onClick={() => window.location.reload()} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Agent Control Panel */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <Button 
                onClick={toggleAgent}
                variant={isAgentRunning ? 'destructive' : 'default'}
                className="gap-2"
              >
                {isAgentRunning ? (
                  <>
                    <Square className="h-4 w-4" />
                    Stop Agent
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Start Agent
                  </>
                )}
              </Button>
              
              <div className={clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium',
                isAgentRunning 
                  ? 'bg-green-100 dark:bg-green-950/30 text-green-700 dark:text-green-400'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
              )}>
                <div className={clsx(
                  'w-2 h-2 rounded-full',
                  isAgentRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                )} />
                {isAgentRunning ? 'Agent Running' : 'Agent Stopped'}
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold">{unprocessedEmails.length}</div>
                <div className="text-xs text-muted-foreground">Unprocessed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{processedCount}</div>
                <div className="text-xs text-muted-foreground">Processed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{tasksCreated}</div>
                <div className="text-xs text-muted-foreground">Tasks Created</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content - Two Columns */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Left Column - Unprocessed Emails & Events */}
        <div className="space-y-6">
          {/* Unprocessed Emails */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Inbox className="h-5 w-5" />
                Unprocessed Emails
              </CardTitle>
              <CardDescription>Emails waiting for AI processing</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {unprocessedEmails.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                  All emails have been processed!
                </div>
              ) : (
                unprocessedEmails.map((email) => (
                  <div 
                    key={email.email_id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate">{email.subject}</div>
                      <div className="text-sm text-muted-foreground" suppressHydrationWarning>
                        {email.from_email} · {format(new Date(email.received_utc), 'h:mm a')}
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => processEmail(email.email_id)}
                      disabled={processingEmailId === email.email_id}
                      className="ml-3"
                    >
                      {processingEmailId === email.email_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        'Process'
                      )}
                    </Button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Agent Reasoning Trace */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5" />
                Agent Reasoning Trace
              </CardTitle>
              <CardDescription>Real-time AI decision process</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {events.slice(0, 15).map((event) => (
                  <div 
                    key={event.id}
                    className="flex items-start gap-3 p-2 rounded-lg bg-muted/30"
                  >
                    {getEventIcon(event.eventType)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium uppercase text-muted-foreground">
                          {event.eventType}
                        </span>
                        <span className="text-xs text-muted-foreground" suppressHydrationWarning>
                          {format(new Date(event.timestamp), 'HH:mm:ss')}
                        </span>
                      </div>
                      <p className="text-sm mt-0.5 line-clamp-2">{event.content}</p>
                    </div>
                  </div>
                ))}
                {events.length === 0 && (
                  <div className="text-center py-6 text-muted-foreground">
                    No agent activity yet. Start the agent or manually process an email.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Actions Taken */}
        <div className="space-y-6">
          {/* Recently Created Tasks */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckSquare className="h-5 w-5" />
                Tasks Created by Agent
              </CardTitle>
              <CardDescription>Automated task generation from emails</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {agentTasks.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  No tasks created by agent yet.
                </div>
              ) : (
                agentTasks.map((task) => (
                  <div 
                    key={task.id}
                    className="p-3 rounded-lg border"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className={clsx(
                        'text-xs',
                        task.priority === 'P0' ? 'bg-red-500' :
                        task.priority === 'P1' ? 'bg-orange-500' :
                        task.priority === 'P2' ? 'bg-blue-500' : 'bg-gray-500'
                      )}>
                        {task.priority}
                      </Badge>
                      <span className="font-medium text-sm">{task.title}</span>
                    </div>
                    <div className="text-xs text-muted-foreground" suppressHydrationWarning>
                      Source: {task.sourceRef} · {format(new Date(task.createdAt), 'h:mm a')}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Recent Follow-ups */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Follow-ups Created
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {agentFollowups.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No follow-ups created yet.
                </div>
              ) : (
                agentFollowups.map((fu) => (
                  <div key={fu.id} className="flex items-center gap-2 text-sm">
                    <span className={clsx(
                      fu.severity === 'critical' ? 'text-red-500' :
                      fu.severity === 'high' ? 'text-orange-500' :
                      fu.severity === 'medium' ? 'text-yellow-500' : 'text-green-500'
                    )}>
                      {fu.severity === 'critical' ? '🔴' :
                       fu.severity === 'high' ? '🟠' :
                       fu.severity === 'medium' ? '🟡' : '🟢'}
                    </span>
                    <span className="flex-1 truncate">{fu.reason}</span>
                    <span className="text-xs text-muted-foreground" suppressHydrationWarning>
                      📅 {format(new Date(fu.dueDate), 'MMM d')}
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Session Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Session Statistics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <div className="text-2xl font-bold text-green-600">{processedCount}</div>
                  <div className="text-xs text-muted-foreground">Emails Processed</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <div className="text-2xl font-bold text-blue-600">{tasksCreated}</div>
                  <div className="text-xs text-muted-foreground">Tasks Created</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <div className="text-2xl font-bold text-purple-600">{agentFollowups.length}</div>
                  <div className="text-xs text-muted-foreground">Follow-ups Added</div>
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-center">
                  <div className="text-2xl font-bold text-orange-600">3</div>
                  <div className="text-xs text-muted-foreground">Drafts Created</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Proactive Alerts Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                🔔 Proactive Alerts & Monitoring
              </CardTitle>
              <CardDescription>24/7 background monitoring for burnout, deadlines, and workload</CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={proactiveEnabled}
                  onChange={(e) => setProactiveEnabled(e.target.checked)}
                  className="rounded"
                />
                <Shield className="h-4 w-4" />
                Enable Monitoring
              </label>
              <Button 
                variant="default" 
                size="sm" 
                onClick={runManualCheck}
                disabled={loading}
              >
                {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Activity className="h-4 w-4 mr-2" />}
                Run Check Now
              </Button>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setDismissedAlerts(new Set(alerts.map(a => a.id)))}
              >
                Clear All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {activeAlerts.length === 0 ? (
            <div className="text-center py-6">
              <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
              <p className="font-medium">All clear!</p>
              <p className="text-sm text-muted-foreground">No alerts right now.</p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm text-orange-600 dark:text-orange-400 font-medium mb-3">
                ⚠️ {activeAlerts.length} active alert(s) require attention
              </div>
              {activeAlerts.map((alert) => (
                <div 
                  key={alert.id}
                  className={clsx(
                    'flex items-start justify-between p-4 rounded-lg border',
                    alert.priority === 'high' ? 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900' :
                    alert.priority === 'medium' ? 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900' :
                    'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900'
                  )}
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className={clsx(
                        alert.priority === 'high' ? 'bg-red-500' :
                        alert.priority === 'medium' ? 'bg-orange-500' : 'bg-blue-500'
                      )}>
                        {alert.priority.toUpperCase()}
                      </Badge>
                      <span className="font-medium">{alert.title}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-1" suppressHydrationWarning>
                      🕐 {format(new Date(alert.timestamp), 'h:mm a')}
                    </p>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => dismissAlert(alert.id)}
                  >
                    ✖️
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
