'use client'

import { useState, useEffect } from 'react'
import { 
  Mail as MailIcon, RefreshCw, CheckCircle, 
  Send, Archive, Trash2, Reply, Forward,
  Search, Sparkles, Inbox, Star, MoreHorizontal,
  ChevronDown, Paperclip, Clock
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { fetchEmails, mockEmails, analyzeEmail, type Email } from '@/lib/api'
import { formatDistanceToNow, format, isToday, isYesterday } from 'date-fns'
import { clsx } from 'clsx'

// Helper to safely get initials
function getInitials(name: string | null | undefined, email: string | null | undefined): string {
  const source = name || email || 'U'
  return source.split(/[\s@.]/).filter(Boolean).map(n => n[0] || '').join('').slice(0, 2).toUpperCase() || 'U'
}

// Helper to safely format date - Apple Mail style
function safeTimeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return ''
    if (isToday(date)) return format(date, 'h:mm a')
    if (isYesterday(date)) return 'Yesterday'
    return format(date, 'MMM d')
  } catch {
    return ''
  }
}

// Minimal category indicators - Apple style (subtle)
const categoryStyles = {
  actionable: { 
    indicator: 'bg-red-500',
    badge: 'bg-red-500/10 text-red-600 dark:text-red-400',
  },
  informational: { 
    indicator: 'bg-blue-500',
    badge: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  },
  noise: { 
    indicator: 'bg-neutral-300 dark:bg-neutral-600',
    badge: 'bg-neutral-500/10 text-neutral-600 dark:text-neutral-400',
  }
}

export default function MailPage() {
  const [emails, setEmails] = useState<Email[]>([])
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null)
  const [filter, setFilter] = useState<'all' | 'actionable' | 'informational' | 'noise'>('all')
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [starred, setStarred] = useState<Set<string>>(new Set())

  useEffect(() => {
    loadEmails()
  }, [])

  const loadEmails = async () => {
    setLoading(true)
    try {
      const data = await fetchEmails()
      setEmails(data.length > 0 ? data : mockEmails)
    } catch (error) {
      console.error('Failed to load emails:', error)
      setEmails(mockEmails)
    }
    setLoading(false)
  }

  const handleAnalyzeEmail = async (email: Email) => {
    setAnalyzing(true)
    setAnalysisResult(null)
    try {
      const result = await analyzeEmail(email.email_id, 'user@example.com')
      setAnalysisResult(result)
    } catch (error) {
      console.error('Failed to analyze email:', error)
    }
    setAnalyzing(false)
  }

  const toggleStar = (emailId: string) => {
    setStarred(prev => {
      const next = new Set(prev)
      if (next.has(emailId)) next.delete(emailId)
      else next.add(emailId)
      return next
    })
  }

  // Filter emails
  const filteredEmails = emails.filter(email => {
    if (filter !== 'all' && email.actionability_gt !== filter) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (
        (email.subject || '').toLowerCase().includes(q) ||
        (email.sender_name || email.from_email || '').toLowerCase().includes(q) ||
        (email.body_text || '').toLowerCase().includes(q)
      )
    }
    return true
  }).sort((a, b) => new Date(b.received_utc).getTime() - new Date(a.received_utc).getTime())

  // Stats
  const stats = {
    total: emails.length,
    actionable: emails.filter(e => e.actionability_gt === 'actionable').length,
    unread: emails.filter(e => !e.processed).length
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex bg-background">
      {/* Sidebar - Email List */}
      <div className="w-[400px] border-r border-border/50 flex flex-col bg-background">
        {/* Header - Apple Mail style */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-5">
            <h1 className="text-[22px] font-semibold tracking-tight">Inbox</h1>
            <div className="flex items-center gap-1">
              {stats.unread > 0 && (
                <span className="px-2.5 py-1 text-xs font-medium bg-foreground text-background rounded-full">
                  {stats.unread} new
                </span>
              )}
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={loadEmails}
                disabled={loading}
                className="h-8 w-8 rounded-full hover:bg-muted"
              >
                <RefreshCw className={clsx('h-4 w-4', loading && 'animate-spin')} />
              </Button>
            </div>
          </div>

          {/* Search - Minimal Apple style */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <input
              type="text"
              placeholder="Search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 text-sm bg-muted/40 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-foreground/10 focus:bg-muted/60 transition-all placeholder:text-muted-foreground/50"
            />
          </div>

          {/* Filters - Pill buttons */}
          <div className="flex gap-2">
            {(['all', 'actionable', 'informational'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  'px-3.5 py-1.5 text-[13px] font-medium rounded-full transition-all',
                  filter === f
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                )}
              >
                {f === 'all' ? 'All Mail' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Email List - Clean, minimal */}
        <div className="flex-1 overflow-y-auto">
          {filteredEmails.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="w-14 h-14 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <MailIcon className="h-7 w-7 opacity-40" />
              </div>
              <p className="text-sm font-medium">No emails</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Your inbox is empty</p>
            </div>
          ) : (
            <div>
              {filteredEmails.map((email, index) => {
                const style = categoryStyles[email.actionability_gt] || categoryStyles.noise
                const isSelected = selectedEmail?.email_id === email.email_id
                const isStarred = starred.has(email.email_id)
                
                return (
                  <button
                    key={email.email_id}
                    onClick={() => {
                      setSelectedEmail(email)
                      setAnalysisResult(null)
                    }}
                    className={clsx(
                      'w-full text-left px-5 py-4 transition-colors relative group',
                      isSelected 
                        ? 'bg-foreground/[0.05]' 
                        : 'hover:bg-muted/40',
                      index !== 0 && 'border-t border-border/30'
                    )}
                  >
                    {/* Unread indicator */}
                    {!email.processed && (
                      <div className="absolute left-2 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-blue-500" />
                    )}
                    
                    <div className="flex gap-3.5">
                      {/* Avatar - Subtle gradient */}
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center text-[13px] font-semibold text-muted-foreground flex-shrink-0">
                        {getInitials(email.sender_name, email.from_email)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className={clsx(
                            'text-[15px] truncate',
                            !email.processed ? 'font-semibold text-foreground' : 'font-medium text-foreground/80'
                          )}>
                            {email.sender_name || email.from_email || 'Unknown'}
                          </span>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className="text-xs text-muted-foreground/70">
                              {safeTimeAgo(email.received_utc)}
                            </span>
                            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/40" />
                          </div>
                        </div>
                        <p className={clsx(
                          'text-[14px] truncate mb-1.5',
                          !email.processed ? 'text-foreground/90' : 'text-muted-foreground'
                        )}>
                          {email.subject || 'No subject'}
                        </p>
                        <p className="text-[13px] text-muted-foreground/60 truncate">
                          {(email.body_text || '').slice(0, 80)}...
                        </p>
                        
                        {/* Bottom row - Category dot + star */}
                        <div className="flex items-center gap-2 mt-2">
                          <span className={clsx('w-2 h-2 rounded-full', style.indicator)} />
                          <span className="text-[11px] text-muted-foreground/50 uppercase tracking-wider font-medium">
                            {email.actionability_gt}
                          </span>
                          {email.processed && (
                            <CheckCircle className="h-3.5 w-3.5 text-green-500/70 ml-auto" />
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Main Content - Email Detail */}
      <div className="flex-1 flex flex-col bg-background">
        {selectedEmail ? (
          <>
            {/* Email Header - Clean, minimal */}
            <div className="px-8 pt-8 pb-6 border-b border-border/30">
              {/* Top toolbar */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                    <Reply className="h-4 w-4" /> Reply
                  </Button>
                  <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                    <Forward className="h-4 w-4" /> Forward
                  </Button>
                </div>
                <div className="flex items-center gap-1">
                  <Button 
                    size="sm" 
                    className="h-9 px-4 rounded-lg gap-2 bg-foreground text-background hover:bg-foreground/90"
                    onClick={() => handleAnalyzeEmail(selectedEmail)}
                    disabled={analyzing}
                  >
                    <Sparkles className={clsx('h-4 w-4', analyzing && 'animate-pulse')} />
                    {analyzing ? 'Analyzing...' : 'AI Analyze'}
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground hover:text-foreground">
                    <Archive className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground hover:text-red-500">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Subject */}
              <h1 className="text-[28px] font-semibold tracking-tight mb-6 leading-tight">
                {selectedEmail.subject || 'No subject'}
              </h1>

              {/* Sender info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-neutral-200 to-neutral-100 dark:from-neutral-700 dark:to-neutral-800 flex items-center justify-center text-sm font-semibold text-foreground/70">
                    {getInitials(selectedEmail.sender_name, selectedEmail.from_email)}
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold">
                      {selectedEmail.sender_name || selectedEmail.from_email || 'Unknown'}
                    </p>
                    <p className="text-[13px] text-muted-foreground/70">
                      {selectedEmail.from_email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={clsx(
                    'px-3 py-1.5 rounded-full text-[12px] font-medium uppercase tracking-wide',
                    categoryStyles[selectedEmail.actionability_gt]?.badge
                  )}>
                    {selectedEmail.actionability_gt}
                  </span>
                  <span className="text-[13px] text-muted-foreground/60">
                    {safeTimeAgo(selectedEmail.received_utc)}
                  </span>
                </div>
              </div>
            </div>

            {/* Email Body - Clean reading experience */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl px-8 py-8">
                {/* AI Analysis Result - Beautiful gradient card */}
                {analysisResult && (
                  <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50 to-purple-50 dark:from-violet-950/40 dark:via-indigo-950/40 dark:to-purple-950/40 border border-violet-100 dark:border-violet-900/50">
                    <div className="flex items-center gap-2.5 mb-5">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      </div>
                      <span className="text-[15px] font-semibold text-violet-700 dark:text-violet-300">AI Analysis</span>
                    </div>
                    
                    <div className="space-y-5">
                      {analysisResult.triage_class && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Classification</span>
                          <p className="text-[15px] font-medium mt-1 capitalize">{analysisResult.triage_class}</p>
                        </div>
                      )}
                      
                      {analysisResult.summary && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Summary</span>
                          <p className="text-[15px] mt-1 leading-relaxed text-foreground/80">{analysisResult.summary}</p>
                        </div>
                      )}
                      
                      {analysisResult.actions && analysisResult.actions.length > 0 && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Suggested Actions</span>
                          <ul className="mt-2 space-y-2">
                            {analysisResult.actions.map((action: string, i: number) => (
                              <li key={i} className="flex items-start gap-3 text-[14px]">
                                <span className="w-5 h-5 rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center text-xs font-medium flex-shrink-0 mt-0.5">
                                  {i + 1}
                                </span>
                                <span className="text-foreground/80">{action}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {analysisResult.reply_draft && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Draft Reply</span>
                          <div className="mt-2 p-4 bg-white dark:bg-neutral-900 rounded-xl text-[14px] leading-relaxed whitespace-pre-wrap border border-violet-100 dark:border-violet-900/50">
                            {analysisResult.reply_draft}
                          </div>
                          <div className="flex gap-2 mt-3">
                            <Button size="sm" className="h-9 px-4 rounded-lg gap-2 bg-violet-600 hover:bg-violet-700 text-white">
                              <Send className="h-3.5 w-3.5" /> Use Draft
                            </Button>
                            <Button size="sm" variant="outline" className="h-9 px-4 rounded-lg border-violet-200 dark:border-violet-800">
                              Edit
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Processed Status */}
                {selectedEmail.processed && (
                  <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-green-50 dark:bg-green-950/30 border border-green-100 dark:border-green-900/50">
                    <div className="w-8 h-8 rounded-lg bg-green-500/10 flex items-center justify-center">
                      <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <span className="text-[14px] font-medium text-green-700 dark:text-green-400">Processed by AI Agent</span>
                      {selectedEmail.agent_actions && (
                        <p className="text-[12px] text-green-600/70 dark:text-green-400/60 mt-0.5">
                          Actions: {selectedEmail.agent_actions.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Email Content - Typography focused */}
                <div className="text-[15px] leading-[1.7] text-foreground/85 whitespace-pre-wrap">
                  {selectedEmail.body_text || 'No content'}
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Empty State - Elegant */
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <div className="w-20 h-20 rounded-3xl bg-muted/30 flex items-center justify-center mb-6">
              <MailIcon className="h-10 w-10 opacity-30" />
            </div>
            <h3 className="text-[18px] font-medium mb-2">No email selected</h3>
            <p className="text-[14px] text-muted-foreground/60">Choose an email from the list to view</p>
          </div>
        )}
      </div>
    </div>
  )
}
