'use client'

import { useState, useEffect } from 'react'
import { 
  Bell, RefreshCw, Clock, Mail, MessageSquare, Target,
  Send, Copy, ChevronDown, Sparkles, AlertTriangle, Search, X, Calendar
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { fetchFollowups, fetchNudges, type Followup } from '@/lib/api'
import { format, formatDistanceToNow, isPast, isToday, isTomorrow } from 'date-fns'
import { clsx } from 'clsx'

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'destructive'

// Severity styles - minimal, Apple-inspired
const severityStyles: Record<string, { indicator: string; badge: string }> = {
  critical: { indicator: 'bg-red-500', badge: 'bg-red-500/10 text-red-600 dark:text-red-400' },
  high: { indicator: 'bg-orange-500', badge: 'bg-orange-500/10 text-orange-600 dark:text-orange-400' },
  medium: { indicator: 'bg-yellow-500', badge: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400' },
  low: { indicator: 'bg-green-500', badge: 'bg-green-500/10 text-green-600 dark:text-green-400' },
}

function getSeverityVariant(severity: string): BadgeVariant {
  switch (severity) {
    case 'critical': return 'destructive'
    case 'high': return 'warning'
    case 'medium': return 'secondary'
    default: return 'default'
  }
}

function getChannelIcon(channel: string) {
  switch (channel) {
    case 'email': return <Mail className="h-4 w-4" />
    case 'slack': return <MessageSquare className="h-4 w-4" />
    case 'teams': return <MessageSquare className="h-4 w-4" />
    default: return <Bell className="h-4 w-4" />
  }
}

function getDueDateStyle(dueDate: string | null | undefined): { className: string; label: string; urgent: boolean } {
  if (!dueDate) return { className: 'text-muted-foreground/60', label: '', urgent: false }
  try {
    const date = new Date(dueDate)
    if (isNaN(date.getTime())) return { className: 'text-muted-foreground/60', label: '', urgent: false }
    if (isPast(date) && !isToday(date)) {
      return { className: 'text-red-600 dark:text-red-400 font-medium', label: 'Overdue', urgent: true }
    }
    if (isToday(date)) return { className: 'text-orange-600 dark:text-orange-400', label: 'Today', urgent: true }
    if (isTomorrow(date)) return { className: 'text-yellow-600 dark:text-yellow-400', label: 'Tomorrow', urgent: false }
    return { className: 'text-muted-foreground/70', label: formatDistanceToNow(date, { addSuffix: true }), urgent: false }
  } catch {
    return { className: 'text-muted-foreground/60', label: '', urgent: false }
  }
}

function safeFormatDate(dateStr: string | null | undefined, formatStr: string): string {
  if (!dateStr) return 'Not set'
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return 'Invalid date'
    return format(date, formatStr)
  } catch {
    return 'Invalid date'
  }
}

export default function NotificationsPage() {
  const [followups, setFollowups] = useState<Followup[]>([])
  const [selectedFollowup, setSelectedFollowup] = useState<Followup | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  useEffect(() => {
    loadFollowups()
  }, [])

  const loadFollowups = async () => {
    setLoading(true)
    try {
      const [data] = await Promise.all([
        fetchFollowups(),
        fetchNudges()
      ])
      setFollowups(data)
    } catch (error) {
      console.error('Failed to load followups:', error)
    }
    setLoading(false)
  }

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Filter and sort
  const filteredFollowups = followups.filter(f => {
    if (filterSeverity !== 'all' && f.severity !== filterSeverity) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return (f.draft_message_gt || '').toLowerCase().includes(q) || (f.reason || '').toLowerCase().includes(q)
    }
    return true
  }).sort((a, b) => {
    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
    return (severityOrder[a.severity] || 3) - (severityOrder[b.severity] || 3)
  })

  // Stats
  const stats = {
    total: followups.length,
    critical: followups.filter(f => f.severity === 'critical').length,
    high: followups.filter(f => f.severity === 'high').length,
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex bg-background">
      {/* Sidebar - Notification List */}
      <div className="w-[420px] border-r border-border/50 flex flex-col bg-background">
        {/* Header */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-5">
            <h1 className="text-[22px] font-semibold tracking-tight">Notifications</h1>
            <div className="flex items-center gap-1">
              {stats.critical > 0 && (
                <span className="px-2.5 py-1 text-xs font-medium bg-red-500 text-white rounded-full">
                  {stats.critical} critical
                </span>
              )}
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={loadFollowups}
                disabled={loading}
                className="h-8 w-8 rounded-full hover:bg-muted"
              >
                <RefreshCw className={clsx('h-4 w-4', loading && 'animate-spin')} />
              </Button>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <input
              type="text"
              placeholder="Search notifications"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 text-sm bg-muted/40 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-foreground/10 focus:bg-muted/60 transition-all placeholder:text-muted-foreground/50"
            />
          </div>

          {/* Filters - Pill buttons */}
          <div className="flex gap-2 flex-wrap">
            {(['all', 'critical', 'high', 'medium'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterSeverity(f)}
                className={clsx(
                  'px-3.5 py-1.5 text-[13px] font-medium rounded-full transition-all',
                  filterSeverity === f
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                )}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Notification List */}
        <div className="flex-1 overflow-y-auto">
          {filteredFollowups.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="w-14 h-14 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <Bell className="h-7 w-7 opacity-40" />
              </div>
              <p className="text-sm font-medium">No notifications</p>
              <p className="text-xs text-muted-foreground/60 mt-1">All caught up!</p>
            </div>
          ) : (
            <div>
              {filteredFollowups.map((followup, index) => {
                const style = severityStyles[followup.severity] || severityStyles.low
                const isSelected = selectedFollowup?.followup_id === followup.followup_id
                const dueStyle = getDueDateStyle(followup.next_contact_due_utc)
                
                return (
                  <button
                    key={followup.followup_id}
                    onClick={() => setSelectedFollowup(followup)}
                    className={clsx(
                      'w-full text-left px-5 py-4 transition-colors relative group',
                      isSelected ? 'bg-foreground/[0.05]' : 'hover:bg-muted/40',
                      index !== 0 && 'border-t border-border/30',
                      dueStyle.urgent && 'bg-red-50/30 dark:bg-red-950/10'
                    )}
                  >
                    {/* Severity indicator */}
                    <div className={clsx('absolute left-2 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full', style.indicator)} />
                    
                    <div className="flex gap-3.5 ml-2">
                      {/* Channel Icon */}
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center flex-shrink-0">
                        {getChannelIcon(followup.recommended_channel)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-[15px] font-semibold text-foreground truncate capitalize">
                            {followup.reason.replace(/_/g, ' ')}
                          </span>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {dueStyle.label && (
                              <span className={clsx('text-xs', dueStyle.className)}>
                                {dueStyle.label}
                              </span>
                            )}
                            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/40" />
                          </div>
                        </div>
                        <p className="text-[13px] text-muted-foreground/60 truncate mb-1.5">
                          {(followup.draft_message_gt || 'No message').slice(0, 80)}...
                        </p>
                        
                        {/* Bottom row */}
                        <div className="flex items-center gap-2">
                          <span className={clsx('px-2 py-0.5 text-[11px] font-medium rounded-full capitalize', style.badge)}>
                            {followup.severity}
                          </span>
                          <span className="text-[11px] text-muted-foreground/50 flex items-center gap-1">
                            {getChannelIcon(followup.recommended_channel)}
                            {followup.recommended_channel}
                          </span>
                          {dueStyle.urgent && (
                            <AlertTriangle className="h-3 w-3 text-red-500 ml-auto" />
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

      {/* Main Content - Notification Detail */}
      <div className="flex-1 flex flex-col bg-background">
        {selectedFollowup ? (
          <>
            {/* Header */}
            <div className="px-8 pt-8 pb-6 border-b border-border/30">
              {/* Top toolbar */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                    <Send className="h-4 w-4" /> Send Now
                  </Button>
                  <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                    <Calendar className="h-4 w-4" /> Snooze
                  </Button>
                </div>
                <div className="flex items-center gap-1">
                  <Button 
                    size="sm" 
                    className="h-9 px-4 rounded-lg gap-2 bg-foreground text-background hover:bg-foreground/90"
                  >
                    <Sparkles className="h-4 w-4" />
                    Regenerate
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground hover:text-red-500">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Title */}
              <h1 className="text-[28px] font-semibold tracking-tight mb-6 leading-tight capitalize">
                {selectedFollowup.reason.replace(/_/g, ' ')}
              </h1>

              {/* Meta info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={clsx(
                    'w-12 h-12 rounded-full flex items-center justify-center',
                    severityStyles[selectedFollowup.severity]?.badge || 'bg-muted'
                  )}>
                    {getChannelIcon(selectedFollowup.recommended_channel)}
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold capitalize">
                      {selectedFollowup.recommended_channel}
                    </p>
                    <p className="text-[13px] text-muted-foreground/70">
                      {selectedFollowup.entity_type} • {selectedFollowup.entity_id}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={getSeverityVariant(selectedFollowup.severity)} className="px-3 py-1.5 text-xs capitalize">
                    {selectedFollowup.severity}
                  </Badge>
                  {getDueDateStyle(selectedFollowup.next_contact_due_utc).urgent && (
                    <Badge variant="destructive" className="px-3 py-1.5 text-xs">
                      Urgent
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl px-8 py-8">
                {/* Due Date Warning */}
                {getDueDateStyle(selectedFollowup.next_contact_due_utc).urgent && (
                  <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50">
                    <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                      <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                    </div>
                    <div>
                      <span className="text-[14px] font-medium text-red-700 dark:text-red-400">
                        This follow-up requires immediate attention
                      </span>
                      <p className="text-[12px] text-red-600/70 dark:text-red-400/60 mt-0.5">
                        Due: {safeFormatDate(selectedFollowup.next_contact_due_utc, 'MMM d, yyyy h:mm a')}
                      </p>
                    </div>
                  </div>
                )}

                {/* AI Draft Message */}
                <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50 to-purple-50 dark:from-violet-950/40 dark:via-indigo-950/40 dark:to-purple-950/40 border border-violet-100 dark:border-violet-900/50">
                  <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      </div>
                      <span className="text-[15px] font-semibold text-violet-700 dark:text-violet-300">AI-Generated Message</span>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 px-3 gap-1.5"
                      onClick={() => copyToClipboard(selectedFollowup.draft_message_gt || '', selectedFollowup.followup_id)}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      {copiedId === selectedFollowup.followup_id ? 'Copied!' : 'Copy'}
                    </Button>
                  </div>
                  <div className="p-4 bg-white dark:bg-neutral-900 rounded-xl border border-violet-100 dark:border-violet-900/50">
                    <p className="text-[15px] leading-[1.7] text-foreground/85 whitespace-pre-wrap">
                      {selectedFollowup.draft_message_gt || 'No message available'}
                    </p>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <Button size="sm" className="h-9 px-4 rounded-lg gap-2 bg-violet-600 hover:bg-violet-700 text-white">
                      <Send className="h-3.5 w-3.5" /> Send
                    </Button>
                    <Button size="sm" variant="outline" className="h-9 px-4 rounded-lg border-violet-200 dark:border-violet-800">
                      Edit Draft
                    </Button>
                  </div>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-6 p-5 rounded-xl bg-muted/30 border border-border/50">
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Due Date</span>
                    <p className={clsx('text-[14px] font-medium mt-1', getDueDateStyle(selectedFollowup.next_contact_due_utc).className)}>
                      {safeFormatDate(selectedFollowup.next_contact_due_utc, 'MMM d, yyyy h:mm a')}
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Channel</span>
                    <p className="text-[14px] font-medium mt-1 capitalize">{selectedFollowup.recommended_channel}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Owner</span>
                    <p className="text-[14px] font-medium mt-1">{(selectedFollowup.owner_user_id || 'Unknown').replace('usr_', '').replace('_', ' ')}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Sensitivity</span>
                    <p className="text-[14px] font-medium mt-1 capitalize">{selectedFollowup.sensitivity || 'internal'}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Entity</span>
                    <p className="text-[14px] font-medium mt-1 capitalize">{selectedFollowup.entity_type}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Correlation ID</span>
                    <p className="text-[14px] font-medium mt-1 text-xs font-mono">{selectedFollowup.correlation_id || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <div className="w-20 h-20 rounded-3xl bg-muted/30 flex items-center justify-center mb-6">
              <Bell className="h-10 w-10 opacity-30" />
            </div>
            <h3 className="text-[18px] font-medium mb-2">No notification selected</h3>
            <p className="text-[14px] text-muted-foreground/60">Choose a notification from the list to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
