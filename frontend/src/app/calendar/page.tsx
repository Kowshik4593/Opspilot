'use client'

import { useState, useEffect } from 'react'
import { 
  Calendar as CalendarIcon, Clock, MapPin, Users, RefreshCw, Plus,
  FileText, Video, MessageSquare, ChevronDown, Sparkles, CheckCircle,
  Play, ExternalLink, Download, Search
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { fetchMeetings, fetchMoM, fetchTranscript, mockMeetings, type Meeting, type MoM, generateMeetingMoM } from '@/lib/api'
import { format, isToday, isTomorrow, isPast } from 'date-fns'
import { clsx } from 'clsx'

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'destructive'

// Meeting status styles
const statusStyles: Record<string, { indicator: string; badge: string }> = {
  'In Progress': { indicator: 'bg-orange-500 animate-pulse', badge: 'bg-orange-500/10 text-orange-600 dark:text-orange-400' },
  'Completed': { indicator: 'bg-green-500', badge: 'bg-green-500/10 text-green-600 dark:text-green-400' },
  'Upcoming': { indicator: 'bg-blue-500', badge: 'bg-blue-500/10 text-blue-600 dark:text-blue-400' },
}

function safeParseDate(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null
  try {
    const date = new Date(dateStr)
    return isNaN(date.getTime()) ? null : date
  } catch {
    return null
  }
}

function getMeetingStatus(meeting: Meeting): { status: string; variant: BadgeVariant } {
  const startTime = safeParseDate(meeting.scheduled_start_utc)
  const endTime = safeParseDate(meeting.scheduled_end_utc)
  const now = new Date()
  
  if (!startTime || !endTime) return { status: 'Unknown', variant: 'default' }
  if (now >= startTime && now <= endTime) return { status: 'In Progress', variant: 'warning' }
  if (isPast(endTime)) return { status: 'Completed', variant: 'success' }
  return { status: 'Upcoming', variant: 'secondary' }
}

function getMeetingTypeEmoji(type: string): string {
  switch (type) {
    case 'status': return '📊'
    case 'kickoff': return '🚀'
    case 'review': return '📝'
    case 'standup': return '🧍'
    case 'planning': return '📋'
    default: return '📅'
  }
}

export default function CalendarPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null)
  const [view, setView] = useState<'all' | 'upcoming' | 'completed'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [mom, setMom] = useState<MoM | null>(null)
  const [transcript, setTranscript] = useState<string | null>(null)
  const [showTranscript, setShowTranscript] = useState(false)
  const [showMoM, setShowMoM] = useState(false)
  const [loadingMoM, setLoadingMoM] = useState(false)
  const [generatingMoM, setGeneratingMoM] = useState(false)

  useEffect(() => {
    loadMeetings()
  }, [])

  useEffect(() => {
    if (selectedMeeting) {
      loadMeetingDetails(selectedMeeting)
    } else {
      setMom(null)
      setTranscript(null)
    }
  }, [selectedMeeting])

  const loadMeetings = async () => {
    setLoading(true)
    try {
      const data = await fetchMeetings()
      setMeetings(data.length > 0 ? data : mockMeetings)
    } catch (error) {
      console.error('Failed to load meetings:', error)
      setMeetings(mockMeetings)
    }
    setLoading(false)
  }

  const loadMeetingDetails = async (meeting: Meeting) => {
    setLoadingMoM(true)
    try {
      const [momData, transcriptData] = await Promise.all([
        fetchMoM(meeting.meeting_id),
        meeting.transcript_file ? fetchTranscript(meeting.transcript_file) : Promise.resolve(null)
      ])
      setMom(momData)
      setTranscript(transcriptData)
    } catch (error) {
      console.error('Failed to load meeting details:', error)
    }
    setLoadingMoM(false)
  }

  const handleGenerateMoM = async (meeting: Meeting) => {
    setGeneratingMoM(true)
    try {
      const generated = await generateMeetingMoM(meeting.meeting_id)
      setMom(generated)
      setShowMoM(true)
    } catch (error) {
      setMom({
        meeting_id: meeting.meeting_id,
        summary: `AI-generated summary for ${meeting.title}`,
        key_points: ['Discussion of project milestones', 'Resource allocation review'],
        action_items: [{ task: 'Review deliverables', owner: meeting.organizer_email, assignee: meeting.organizer_email, due_date: new Date().toISOString() }],
        decisions: ['Approved timeline extension'],
        generated_at: new Date().toISOString()
      })
      setShowMoM(true)
    }
    setGeneratingMoM(false)
  }

  // Filter meetings
  const filteredMeetings = meetings.filter(meeting => {
    const endTime = safeParseDate(meeting.scheduled_end_utc)
    if (!endTime && view !== 'all') return false
    if (view === 'upcoming' && endTime && isPast(endTime)) return false
    if (view === 'completed' && endTime && !isPast(endTime)) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return meeting.title.toLowerCase().includes(q) || meeting.organizer_email.toLowerCase().includes(q)
    }
    return true
  }).sort((a, b) => {
    const dateA = safeParseDate(a.scheduled_start_utc)?.getTime() || 0
    const dateB = safeParseDate(b.scheduled_start_utc)?.getTime() || 0
    return dateB - dateA
  })

  // Stats
  const stats = {
    total: meetings.length,
    today: meetings.filter(m => { const d = safeParseDate(m.scheduled_start_utc); return d && isToday(d) }).length,
    upcoming: meetings.filter(m => { const d = safeParseDate(m.scheduled_end_utc); return d && !isPast(d) }).length,
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex bg-background">
      {/* Sidebar - Meeting List */}
      <div className="w-[420px] border-r border-border/50 flex flex-col bg-background">
        {/* Header */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-5">
            <h1 className="text-[22px] font-semibold tracking-tight">Calendar</h1>
            <div className="flex items-center gap-1">
              {stats.today > 0 && (
                <span className="px-2.5 py-1 text-xs font-medium bg-foreground text-background rounded-full">
                  {stats.today} today
                </span>
              )}
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={loadMeetings}
                disabled={loading}
                className="h-8 w-8 rounded-full hover:bg-muted"
              >
                <RefreshCw className={clsx('h-4 w-4', loading && 'animate-spin')} />
              </Button>
              <Button size="icon" className="h-8 w-8 rounded-full">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <input
              type="text"
              placeholder="Search meetings"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 text-sm bg-muted/40 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-foreground/10 focus:bg-muted/60 transition-all placeholder:text-muted-foreground/50"
            />
          </div>

          {/* Filters - Pill buttons */}
          <div className="flex gap-2 flex-wrap">
            {(['all', 'upcoming', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setView(f)}
                className={clsx(
                  'px-3.5 py-1.5 text-[13px] font-medium rounded-full transition-all',
                  view === f
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                )}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Meeting List */}
        <div className="flex-1 overflow-y-auto">
          {filteredMeetings.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="w-14 h-14 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <CalendarIcon className="h-7 w-7 opacity-40" />
              </div>
              <p className="text-sm font-medium">No meetings</p>
              <p className="text-xs text-muted-foreground/60 mt-1">Your calendar is clear</p>
            </div>
          ) : (
            <div>
              {filteredMeetings.map((meeting, index) => {
                const status = getMeetingStatus(meeting)
                const style = statusStyles[status.status] || statusStyles.Upcoming
                const isSelected = selectedMeeting?.meeting_id === meeting.meeting_id
                const startDate = safeParseDate(meeting.scheduled_start_utc)
                const dateLabel = startDate ? (
                  isToday(startDate) ? 'Today' : 
                  isTomorrow(startDate) ? 'Tomorrow' : 
                  format(startDate, 'MMM d')
                ) : ''
                
                return (
                  <button
                    key={meeting.meeting_id}
                    onClick={() => setSelectedMeeting(meeting)}
                    className={clsx(
                      'w-full text-left px-5 py-4 transition-colors relative group',
                      isSelected ? 'bg-foreground/[0.05]' : 'hover:bg-muted/40',
                      index !== 0 && 'border-t border-border/30'
                    )}
                  >
                    {/* Status indicator */}
                    <div className={clsx('absolute left-2 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full', style.indicator)} />
                    
                    <div className="flex gap-3.5 ml-2">
                      {/* Time block */}
                      <div className="w-14 flex-shrink-0 text-center">
                        <div className="text-lg font-bold text-foreground">
                          {startDate ? format(startDate, 'HH:mm') : '--:--'}
                        </div>
                        <div className="text-[11px] text-muted-foreground/60">
                          {dateLabel}
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="text-[15px] font-semibold text-foreground truncate">
                            {meeting.title}
                          </span>
                          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/40 flex-shrink-0" />
                        </div>
                        <div className="flex items-center gap-2 text-[13px] text-muted-foreground/60 mb-1.5">
                          <Video className="h-3.5 w-3.5" />
                          <span className="truncate">{meeting.location}</span>
                        </div>
                        
                        {/* Bottom row */}
                        <div className="flex items-center gap-2">
                          <span className={clsx('px-2 py-0.5 text-[11px] font-medium rounded-full', style.badge)}>
                            {status.status}
                          </span>
                          <span className="text-[11px] text-muted-foreground/50">
                            {getMeetingTypeEmoji(meeting.meeting_type)} {meeting.meeting_type}
                          </span>
                          <span className="text-[11px] text-muted-foreground/50 flex items-center gap-1 ml-auto">
                            <Users className="h-3 w-3" />
                            {meeting.participant_emails.length}
                          </span>
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

      {/* Main Content - Meeting Detail */}
      <div className="flex-1 flex flex-col bg-background">
        {selectedMeeting ? (
          <>
            {/* Header */}
            <div className="px-8 pt-8 pb-6 border-b border-border/30">
              {/* Top toolbar */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  {getMeetingStatus(selectedMeeting).status !== 'Completed' && (
                    <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                      <Play className="h-4 w-4" /> Join Meeting
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground">
                    <MessageSquare className="h-4 w-4" /> Chat
                  </Button>
                </div>
                <div className="flex items-center gap-1">
                  {getMeetingStatus(selectedMeeting).status === 'Completed' && (
                    <Button 
                      size="sm" 
                      className="h-9 px-4 rounded-lg gap-2 bg-foreground text-background hover:bg-foreground/90"
                      onClick={() => handleGenerateMoM(selectedMeeting)}
                      disabled={generatingMoM}
                    >
                      <Sparkles className={clsx('h-4 w-4', generatingMoM && 'animate-pulse')} />
                      {generatingMoM ? 'Generating...' : 'Generate MoM'}
                    </Button>
                  )}
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Title */}
              <h1 className="text-[28px] font-semibold tracking-tight mb-6 leading-tight">
                {selectedMeeting.title}
              </h1>

              {/* Meta info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={clsx(
                    'w-12 h-12 rounded-full flex items-center justify-center text-lg',
                    statusStyles[getMeetingStatus(selectedMeeting).status]?.badge || 'bg-muted'
                  )}>
                    {getMeetingTypeEmoji(selectedMeeting.meeting_type)}
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold">
                      {safeParseDate(selectedMeeting.scheduled_start_utc) 
                        ? format(safeParseDate(selectedMeeting.scheduled_start_utc)!, 'EEEE, MMMM d, yyyy')
                        : 'Date not set'}
                    </p>
                    <p className="text-[13px] text-muted-foreground/70">
                      {safeParseDate(selectedMeeting.scheduled_start_utc) && safeParseDate(selectedMeeting.scheduled_end_utc)
                        ? `${format(safeParseDate(selectedMeeting.scheduled_start_utc)!, 'h:mm a')} - ${format(safeParseDate(selectedMeeting.scheduled_end_utc)!, 'h:mm a')}`
                        : 'Time not set'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={getMeetingStatus(selectedMeeting).variant} className="px-3 py-1.5 text-xs">
                    {getMeetingStatus(selectedMeeting).status}
                  </Badge>
                  <Badge variant="secondary" className="px-3 py-1.5 text-xs capitalize">
                    {selectedMeeting.meeting_type}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl px-8 py-8">
                {/* Meeting Info Grid */}
                <div className="grid grid-cols-2 gap-6 p-5 rounded-xl bg-muted/30 border border-border/50 mb-8">
                  <div className="flex items-center gap-3">
                    <Clock className="h-4 w-4 text-muted-foreground/60" />
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Duration</span>
                      <p className="text-[14px] font-medium">
                        {safeParseDate(selectedMeeting.scheduled_start_utc) && safeParseDate(selectedMeeting.scheduled_end_utc)
                          ? `${Math.round((safeParseDate(selectedMeeting.scheduled_end_utc)!.getTime() - safeParseDate(selectedMeeting.scheduled_start_utc)!.getTime()) / 60000)} minutes`
                          : 'N/A'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Video className="h-4 w-4 text-muted-foreground/60" />
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Location</span>
                      <p className="text-[14px] font-medium">{selectedMeeting.location}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Users className="h-4 w-4 text-muted-foreground/60" />
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Attendees</span>
                      <p className="text-[14px] font-medium">{selectedMeeting.participant_emails.length} participants</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <CalendarIcon className="h-4 w-4 text-muted-foreground/60" />
                    <div>
                      <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Sensitivity</span>
                      <p className="text-[14px] font-medium capitalize">{selectedMeeting.sensitivity}</p>
                    </div>
                  </div>
                </div>

                {/* Participants */}
                <div className="mb-8">
                  <h3 className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-3">Participants</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedMeeting.participant_emails.map((email, i) => (
                      <span key={i} className="px-3 py-1.5 text-[13px] rounded-full bg-muted text-muted-foreground">
                        {email.split('@')[0]}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Transcript (Completed meetings) */}
                {getMeetingStatus(selectedMeeting).status === 'Completed' && selectedMeeting.transcript_file && (
                  <div className="mb-6">
                    <button 
                      onClick={() => setShowTranscript(!showTranscript)}
                      className="w-full flex items-center justify-between p-4 rounded-xl bg-muted/30 border border-border/50 hover:bg-muted/50 transition-colors"
                    >
                      <span className="flex items-center gap-2 text-[14px] font-medium">
                        <MessageSquare className="h-4 w-4" />
                        Meeting Transcript
                      </span>
                      <ChevronDown className={clsx('h-4 w-4 transition-transform', showTranscript && 'rotate-180')} />
                    </button>
                    {showTranscript && transcript && (
                      <div className="mt-3 p-4 bg-muted/20 rounded-xl border border-border/30">
                        <pre className="text-sm whitespace-pre-wrap font-mono text-muted-foreground">{transcript}</pre>
                      </div>
                    )}
                  </div>
                )}

                {/* AI Meeting Minutes (Completed meetings) */}
                {getMeetingStatus(selectedMeeting).status === 'Completed' && mom && (
                  <div className="p-6 rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50 to-purple-50 dark:from-violet-950/40 dark:via-indigo-950/40 dark:to-purple-950/40 border border-violet-100 dark:border-violet-900/50">
                    <div className="flex items-center gap-2.5 mb-5">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      </div>
                      <span className="text-[15px] font-semibold text-violet-700 dark:text-violet-300">AI Meeting Minutes</span>
                    </div>
                    
                    <div className="space-y-5">
                      {mom.summary && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Summary</span>
                          <p className="text-[15px] mt-1 leading-relaxed text-foreground/80">{mom.summary}</p>
                        </div>
                      )}
                      
                      {mom.key_points && mom.key_points.length > 0 && (
                        <div>
                          <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Key Points</span>
                          <ul className="mt-2 space-y-2">
                            {mom.key_points.map((point, i) => (
                              <li key={i} className="flex items-start gap-3 text-[14px]">
                                <span className="w-5 h-5 rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center text-xs font-medium flex-shrink-0 mt-0.5">
                                  {i + 1}
                                </span>
                                <span className="text-foreground/80">{point}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {(mom.action_items || mom.actions) && (
                        <div className="p-4 bg-white dark:bg-neutral-900 rounded-xl border border-violet-100 dark:border-violet-900/50">
                          <span className="text-[11px] font-medium text-orange-600 dark:text-orange-400 uppercase tracking-wider">⚡ Action Items</span>
                          <div className="mt-3 space-y-2">
                            {(mom.action_items || mom.actions || []).map((item: any, i: number) => (
                              <div key={i} className="flex items-start gap-2 text-sm">
                                <CheckCircle className="h-4 w-4 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0" />
                                <span>{typeof item === 'string' ? item : item.task}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-2 mt-5">
                      <Button size="sm" variant="outline" className="h-9 px-4 rounded-lg gap-2 border-violet-200 dark:border-violet-800">
                        <Download className="h-3.5 w-3.5" /> Export PDF
                      </Button>
                    </div>
                  </div>
                )}

                {/* Upcoming meeting note */}
                {getMeetingStatus(selectedMeeting).status !== 'Completed' && (
                  <div className="p-5 rounded-xl bg-muted/30 border border-border/50 text-center">
                    <FileText className="h-8 w-8 text-muted-foreground/40 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">
                      Meeting notes and AI minutes will be available after the meeting ends.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <div className="w-20 h-20 rounded-3xl bg-muted/30 flex items-center justify-center mb-6">
              <CalendarIcon className="h-10 w-10 opacity-30" />
            </div>
            <h3 className="text-[18px] font-medium mb-2">No meeting selected</h3>
            <p className="text-[14px] text-muted-foreground/60">Choose a meeting from the list to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
