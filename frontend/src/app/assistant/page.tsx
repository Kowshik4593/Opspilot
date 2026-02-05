'use client'

import { useState, useRef, useEffect } from 'react'
import { 
  MessageSquare, Send, Sparkles, Brain, User, Bot, Eye, Zap, Lightbulb,
  RefreshCw, Trash2, ChevronDown, ChevronUp, Building2, Target,
  Mail, CheckSquare, AlertTriangle, HelpCircle, Clock, Briefcase
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { clsx } from 'clsx'
import { format } from 'date-fns'
import { sendAssistantMessage, startAssistantChat, startAutonomousAgent, fetchAutonomousStatus } from '@/lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ReasoningStep {
  type: 'thinking' | 'action' | 'observation'
  content: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  reasoningTrace?: ReasoningStep[]
  intent?: string
  confidence?: number
}

// Simulated responses based on query patterns
function getSimulatedResponse(query: string): { content: string; intent: string; confidence: number; reasoning: ReasoningStep[] } {
  const q = query.toLowerCase()
  
  if (q.includes('brief') || q.includes('summary')) {
    return {
      content: `## 📊 Your Morning Brief

**Priority Items:**
- 🔴 **2 P0 tasks** require immediate attention
- 📧 **3 actionable emails** need response
- ⚠️ **1 follow-up** is due today

**Key Meetings:**
- 10:00 AM - TechVision Weekly Sync
- 2:00 PM - Acme Corp Phase Review

**Wellness Score:** 72/100 (Moderate)

**Recommendation:** Start with the P0 task "Prepare TechVision demo" as it's due in 4 hours.`,
      intent: 'daily_brief',
      confidence: 0.95,
      reasoning: [
        { type: 'thinking', content: 'User wants a daily briefing. Let me gather data from all sources.' },
        { type: 'action', content: 'Querying tasks, emails, meetings, and wellness data...' },
        { type: 'observation', content: 'Found 2 P0 tasks, 3 actionable emails, 2 meetings today.' },
        { type: 'thinking', content: 'Formatting comprehensive brief with priorities and recommendations.' }
      ]
    }
  }
  
  if (q.includes('p0') || q.includes('priority') || q.includes('urgent')) {
    return {
      content: `## 🔴 P0 Tasks (Critical Priority)

1. **Prepare TechVision Demo Environment**
   - Due: Today, 2:00 PM
   - Client: TechVision Inc
   - Status: In Progress (40%)
   
2. **Review Acme Contract Terms**
   - Due: Tomorrow
   - Client: Acme Corp
   - Status: Not Started
   
**Suggested Actions:**
- Block 2 hours for TechVision demo prep
- Schedule 30 mins tomorrow morning for Acme review`,
      intent: 'task_query',
      confidence: 0.92,
      reasoning: [
        { type: 'thinking', content: 'User wants to see P0 (highest priority) tasks.' },
        { type: 'action', content: 'Filtering tasks by priority=P0...' },
        { type: 'observation', content: 'Found 2 P0 tasks with different due dates.' }
      ]
    }
  }
  
  if (q.includes('actionable') || q.includes('email')) {
    return {
      content: `## 📧 Actionable Emails

**Requires Response:**

1. **RE: Q4 Budget Review** - Sarah Chen
   - Category: Decision Required
   - Action: Approve or provide feedback on budget allocation
   - Suggested response drafted ✓

2. **Meeting Request: TechVision Demo** - Mike Johnson
   - Category: Meeting Request
   - Action: Confirm availability for Thursday 2pm
   
3. **Contract Amendment - Acme** - Legal Team
   - Category: Document Review
   - Action: Review and sign by EOD tomorrow

Would you like me to draft responses for any of these?`,
      intent: 'email_query',
      confidence: 0.88,
      reasoning: [
        { type: 'thinking', content: 'User wants actionable emails that need attention.' },
        { type: 'action', content: 'Querying emails with triage_result.suggested_action != null...' },
        { type: 'observation', content: 'Found 3 emails requiring user action.' }
      ]
    }
  }
  
  if (q.includes('follow') || q.includes('nudge')) {
    return {
      content: `## ⏰ Pending Follow-ups

**Due Today:**
- 🔴 **Acme Corp** - Waiting for project approval (3 days overdue)
  - Suggested: Send escalation to management

**Due This Week:**
- 🟡 **TechVision** - License renewal discussion
  - Due: Thursday
- 🟢 **GlobalTech** - Invoice confirmation
  - Due: Friday

**AI Suggestion:** The Acme follow-up is critical. I've drafted an escalation email for your review.`,
      intent: 'followup_query',
      confidence: 0.90,
      reasoning: [
        { type: 'thinking', content: 'User asking about pending follow-ups and nudges.' },
        { type: 'action', content: 'Fetching follow-ups sorted by due date...' },
        { type: 'observation', content: 'Found 1 overdue, 2 due this week.' }
      ]
    }
  }
  
  if (q.includes('risk') || q.includes('blocker')) {
    return {
      content: `## ⚠️ Current Risks & Blockers

**High Risk:**
1. **TechVision Demo** - Demo environment not fully tested
   - Impact: Client presentation Thursday
   - Mitigation: Schedule 2hr testing block today

**Medium Risk:**
2. **Acme Contract** - Legal review pending
   - Impact: May delay Q4 revenue recognition
   - Mitigation: Escalate to legal lead

**Blockers:**
- Waiting on AWS credentials from IT (requested 2 days ago)
- Pending budget approval for GlobalTech expansion`,
      intent: 'risk_assessment',
      confidence: 0.85,
      reasoning: [
        { type: 'thinking', content: 'User wants risk assessment across all workstreams.' },
        { type: 'action', content: 'Analyzing tasks, emails, and meetings for blockers...' },
        { type: 'observation', content: 'Identified 2 risks and 2 blockers.' }
      ]
    }
  }
  
  if (q.includes('acme')) {
    return {
      content: `## 🏢 Acme Corp - Client Insights

**Relationship Health:** 🟡 Moderate

**Open Items:**
- Contract renewal (P0, due tomorrow)
- Phase 2 planning session needed
- Outstanding invoice: $45,000

**Recent Activity:**
- Last meeting: Phase 1 Retrospective (2 days ago)
- Last email: Contract terms discussion (yesterday)

**Sentiment Analysis:** Positive but time-sensitive. Contract discussions require prompt attention.

**Recommended Actions:**
1. Prioritize contract review today
2. Schedule Phase 2 kickoff call
3. Follow up on invoice status`,
      intent: 'client_insights',
      confidence: 0.91,
      reasoning: [
        { type: 'thinking', content: 'User wants insights about Acme Corp client.' },
        { type: 'action', content: 'Aggregating Acme data from emails, meetings, tasks...' },
        { type: 'observation', content: 'Found contract renewal pending, recent retro meeting.' }
      ]
    }
  }
  
  if (q.includes('techvision')) {
    return {
      content: `## 🏢 TechVision Inc - Client Insights

**Relationship Health:** 🟢 Strong

**Open Items:**
- Demo preparation (P0, due today)
- License renewal discussion (P2)
- Training materials update (P3)

**Recent Activity:**
- Kickoff meeting completed successfully
- Weekly sync scheduled for today 10am

**Sentiment Analysis:** Very positive. Client excited about demo.

**Key Contacts:**
- Mike Johnson (Primary) - Engaged, responsive
- Sarah Lee (Technical) - Awaiting demo`,
      intent: 'client_insights',
      confidence: 0.89,
      reasoning: [
        { type: 'thinking', content: 'User wants insights about TechVision client.' },
        { type: 'action', content: 'Gathering TechVision data across all sources...' },
        { type: 'observation', content: 'Strong relationship, demo is priority item.' }
      ]
    }
  }
  
  if (q.includes('globaltech')) {
    return {
      content: `## 🏢 GlobalTech Solutions - Client Insights

**Relationship Health:** 🟡 Developing

**Open Items:**
- Discovery call follow-up (P2)
- Proposal draft (P2)
- Invoice confirmation pending

**Recent Activity:**
- Discovery call completed last week
- Initial proposal requested

**Sentiment Analysis:** Interested but early stage. Need to maintain momentum.

**Next Steps:**
1. Send proposal draft by Friday
2. Schedule technical deep-dive
3. Confirm invoice receipt`,
      intent: 'client_insights',
      confidence: 0.87,
      reasoning: [
        { type: 'thinking', content: 'User wants insights about GlobalTech client.' },
        { type: 'action', content: 'Searching for GlobalTech across data sources...' },
        { type: 'observation', content: 'New client, discovery phase, proposal needed.' }
      ]
    }
  }
  
  if (q.includes('help') || q.includes('what can')) {
    return {
      content: `## 🤖 OpsPilot Assistant Help

I can help you with:

**📧 Email Management**
- "Show actionable emails"
- "What needs response?"
- "Draft a reply to [email]"

**✅ Task Management**
- "Show my P0 tasks"
- "What's due today?"
- "Create a task for..."

**📅 Calendar & Meetings**
- "What meetings do I have?"
- "Summarize today's schedule"

**🔔 Follow-ups & Nudges**
- "What needs follow-up?"
- "Show overdue items"

**📊 Briefings & Insights**
- "Brief me" - Daily summary
- "[Client name] insights" - Client overview
- "What are my risks?"

**💚 Wellness**
- "How's my workload?"
- "Am I at burnout risk?"

Just ask naturally - I understand context!`,
      intent: 'help',
      confidence: 0.99,
      reasoning: [
        { type: 'thinking', content: 'User needs help understanding capabilities.' },
        { type: 'action', content: 'Generating capability overview...' },
        { type: 'observation', content: 'Providing comprehensive help guide.' }
      ]
    }
  }
  
  if (q.includes('focus') || q.includes('priorit')) {
    return {
      content: `## 🎯 What to Focus On

Based on your current workload and deadlines:

**Immediate (Next 2 Hours):**
1. 🔴 TechVision demo prep - critical path item
2. 📧 Respond to Sarah's budget email

**Today:**
3. Acme contract review start
4. Attend TechVision weekly sync

**This Week:**
5. GlobalTech proposal draft
6. Clear email backlog

**Time Blocking Suggestion:**
- 9-11am: Deep work on demo
- 11-12pm: Email catch-up
- 2-3pm: TechVision meeting
- 3-5pm: Acme contract review`,
      intent: 'prioritization',
      confidence: 0.93,
      reasoning: [
        { type: 'thinking', content: 'User wants help prioritizing their work.' },
        { type: 'action', content: 'Analyzing all tasks, emails, meetings by urgency...' },
        { type: 'observation', content: 'Demo prep is most urgent, then contract review.' }
      ]
    }
  }
  
  if (q.includes('escalat')) {
    return {
      content: `## 🚨 Items Needing Escalation

**Requires Management Attention:**

1. **Acme Contract Delay**
   - Issue: Legal review taking longer than expected
   - Impact: May delay Q4 close
   - Escalate to: VP of Sales
   
2. **AWS Credentials Request**
   - Issue: IT not responding (2 days)
   - Impact: Blocking TechVision demo
   - Escalate to: IT Manager

**Draft Escalation Ready:** I've prepared escalation emails for both items. Would you like to review them?`,
      intent: 'escalation_check',
      confidence: 0.86,
      reasoning: [
        { type: 'thinking', content: 'User wants to know what needs escalation.' },
        { type: 'action', content: 'Checking for blocked or overdue high-priority items...' },
        { type: 'observation', content: 'Found 2 items requiring management escalation.' }
      ]
    }
  }
  
  // Default response
  return {
    content: `I understand you're asking about "${query}". 

I can help you with:
- **Email triage** and responses
- **Task management** and prioritization  
- **Meeting summaries** and prep
- **Follow-up tracking**
- **Client insights**
- **Wellness monitoring**

Try asking "brief me" for a daily summary, or "help" for more options.`,
    intent: 'general',
    confidence: 0.6,
    reasoning: [
      { type: 'thinking', content: 'Processing general query, determining intent...' },
      { type: 'observation', content: 'Query does not match specific patterns, providing general help.' }
    ]
  }
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm **OpsPilot**, your AI workplace assistant. I can help you manage emails, schedule meetings, track tasks, and much more.\n\n💡 Try saying **\"brief me\"** or click a quick action below to get started!",
      timestamp: new Date(),
      intent: 'greeting',
      confidence: 1.0,
    },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [showReasoning, setShowReasoning] = useState(true)
  const [expandedReasoning, setExpandedReasoning] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const userEmail = 'alice@example.com'
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Auto-start autonomous agent on mount
  useEffect(() => {
    const startAgent = async () => {
      try {
        const status = await fetchAutonomousStatus()
        if (!status.is_running) {
          await startAutonomousAgent()
          console.log('[AGENT] Autonomous agent started automatically')
        }
      } catch (error) {
        console.warn('[AGENT] Could not start autonomous agent:', error)
      }
    }
    startAgent()
  }, [])

  const handleSend = async (query?: string) => {
    const messageText = query || input
    if (!messageText.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    try {
      // Initialize session if needed
      let currentSessionId = sessionId
      if (!currentSessionId) {
        try {
          currentSessionId = await startAssistantChat(userEmail)
        } catch (e) {
          console.warn('Failed to start chat session:', e)
        }
      }

      // Try backend first
      const backendResponse = await sendAssistantMessage(currentSessionId, userEmail, messageText)
      
      if (backendResponse && backendResponse.response) {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: backendResponse.response,
          timestamp: new Date(),
          reasoningTrace: backendResponse.reasoning_trace?.map((step: any) => ({
            type: step.type || 'thinking',
            content: step.content || step
          })),
          intent: backendResponse.intent || 'general',
          confidence: backendResponse.confidence || 0.8,
        }
        setMessages(prev => [...prev, aiMessage])
        if (backendResponse.session_id) {
          setSessionId(backendResponse.session_id)
        } else if (currentSessionId) {
          setSessionId(currentSessionId)
        }
      } else {
        throw new Error('No response content from backend')
      }
    } catch (error) {
      console.error('Error in handleSend:', error)
      // Fallback to simulated response on error
      const response = getSimulatedResponse(messageText)
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        reasoningTrace: response.reasoning,
        intent: response.intent,
        confidence: response.confidence,
      }
      setMessages(prev => [...prev, aiMessage])
    }
    
    setIsTyping(false)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const clearChat = () => {
    setMessages([{
      id: '1',
      role: 'assistant',
      content: "Chat cleared! How can I help you today?",
      timestamp: new Date(),
    }])
  }

  const quickActions = [
    { label: 'Brief Me', query: 'brief me', icon: Sparkles },
    { label: 'P0 Tasks', query: 'show my P0 tasks', icon: Target },
    { label: 'Actionable', query: 'show actionable emails', icon: Mail },
    { label: 'Follow-ups', query: 'what needs follow-up', icon: Clock },
    { label: 'Risks', query: 'what are my risks', icon: AlertTriangle },
    { label: 'Priorities', query: 'what should I focus on', icon: CheckSquare },
    { label: 'Escalations', query: 'what needs escalation', icon: AlertTriangle },
    { label: 'Help', query: 'help', icon: HelpCircle },
  ]

  const clientInsights = [
    { label: 'Acme Corp', query: 'acme insights', color: 'bg-blue-500' },
    { label: 'TechVision', query: 'techvision insights', color: 'bg-purple-500' },
    { label: 'GlobalTech', query: 'globaltech insights', color: 'bg-green-500' },
  ]

  const getReasoningIcon = (type: string) => {
    switch (type) {
      case 'thinking': return <Lightbulb className="h-3.5 w-3.5 text-yellow-500" />
      case 'action': return <Zap className="h-3.5 w-3.5 text-blue-500" />
      case 'observation': return <Eye className="h-3.5 w-3.5 text-green-500" />
      default: return <Brain className="h-3.5 w-3.5" />
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Compact Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-background/95 backdrop-blur flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">OpsPilot Assistant</h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input 
              type="checkbox" 
              checked={showReasoning}
              onChange={(e) => setShowReasoning(e.target.checked)}
              className="rounded"
            />
            <Brain className="h-4 w-4" />
            <span className="hidden sm:inline">Reasoning</span>
          </label>
          <Button variant="ghost" size="sm" onClick={clearChat}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Chat Area - Full Height */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={clsx(
              'flex gap-3',
              message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
            )}
          >
            {/* Avatar */}
            <div className={clsx(
              'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
              message.role === 'user' 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-gradient-to-br from-purple-500 to-blue-500 text-white'
            )}>
              {message.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            {/* Message Content */}
            <div className={clsx(
              'max-w-[80%] space-y-2',
              message.role === 'user' ? 'items-end' : 'items-start'
            )}>
              {/* Reasoning Trace */}
              {showReasoning && message.reasoningTrace && message.reasoningTrace.length > 0 && (
                <div className="mb-2">
                  <button
                    onClick={() => setExpandedReasoning(
                      expandedReasoning === message.id ? null : message.id
                    )}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Brain className="h-3 w-3" />
                    Reasoning ({message.reasoningTrace.length} steps)
                    {expandedReasoning === message.id 
                      ? <ChevronUp className="h-3 w-3" /> 
                      : <ChevronDown className="h-3 w-3" />}
                  </button>
                  {expandedReasoning === message.id && (
                    <div className="mt-2 p-3 bg-muted/50 rounded-lg space-y-2 text-sm">
                      {message.reasoningTrace.map((step, i) => (
                        <div key={i} className="flex items-start gap-2">
                          {getReasoningIcon(step.type)}
                          <div>
                            <span className="font-medium capitalize text-xs">{step.type}:</span>
                            <span className="ml-1 text-muted-foreground">{step.content}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Message Bubble */}
              <div
                className={clsx(
                  'rounded-lg p-4',
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted'
                )}
              >
                <div className="prose prose-sm dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Intent & Confidence */}
              {message.intent && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">
                    🎯 {message.intent}
                  </Badge>
                  {message.confidence && (
                    <span>
                      Confidence: {(message.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  <span>
                    {format(message.timestamp, 'h:mm a')}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <div className="bg-muted rounded-lg p-4">
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-foreground/40 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area - Fixed at Bottom */}
      <div className="border-t p-4 bg-background flex-shrink-0">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about tasks, emails, meetings... Try 'brief me' or 'show P0 tasks'"
            className="flex-1 px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isTyping}
          />
          <Button 
            onClick={() => handleSend()} 
            disabled={!input.trim() || isTyping}
            className="px-4"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        {/* Quick Actions Row */}
        <div className="flex flex-wrap gap-2 mt-3 max-w-4xl mx-auto justify-center">
          {quickActions.slice(0, 5).map((action, i) => (
            <Button
              key={i}
              variant="outline"
              size="sm"
              className="gap-1 text-xs"
              onClick={() => handleSend(action.query)}
              disabled={isTyping}
            >
              <action.icon className="h-3 w-3" />
              {action.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  )
}
