'use client'

import { useState, useEffect } from 'react'
import { 
  CheckSquare, Plus, Calendar as CalendarIcon, RefreshCw, 
  Clock, Search, Play, CheckCircle, Timer, Target, 
  MoreHorizontal, ChevronDown, Sparkles, AlertTriangle, FolderOpen
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { fetchTasks, mockTasks, type Task, formatDuration, fetchDayPlan, completeTask, updateTaskStatus } from '@/lib/api'
import { format, isPast, isToday, isTomorrow } from 'date-fns'
import { clsx } from 'clsx'

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'destructive'
type FilterStatus = 'all' | 'todo' | 'in_progress' | 'completed' | 'blocked'
type FilterPriority = 'all' | 'P0' | 'P1' | 'P2' | 'P3'

function getPriorityVariant(priority: string): BadgeVariant {
  switch (priority) {
    case 'P0': return 'destructive'
    case 'P1': return 'warning'
    case 'P2': return 'secondary'
    case 'P3': return 'default'
    default: return 'default'
  }
}

function getStatusVariant(status: string): BadgeVariant {
  switch (status) {
    case 'completed': case 'done': return 'success'
    case 'in_progress': return 'warning'
    case 'blocked': return 'destructive'
    default: return 'default'
  }
}

// Priority styles - minimal, Apple-inspired
const priorityStyles: Record<string, { indicator: string; badge: string }> = {
  P0: { indicator: 'bg-red-500', badge: 'bg-red-500/10 text-red-600 dark:text-red-400' },
  P1: { indicator: 'bg-orange-500', badge: 'bg-orange-500/10 text-orange-600 dark:text-orange-400' },
  P2: { indicator: 'bg-yellow-500', badge: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400' },
  P3: { indicator: 'bg-green-500', badge: 'bg-green-500/10 text-green-600 dark:text-green-400' },
}

function getDueDateStyle(dueDate: string | undefined): { className: string; label: string } {
  if (!dueDate) return { className: 'text-muted-foreground/60', label: '' }
  try {
    const date = new Date(dueDate)
    if (isNaN(date.getTime())) return { className: 'text-muted-foreground/60', label: '' }
    if (isPast(date) && !isToday(date)) {
      return { className: 'text-red-600 dark:text-red-400 font-medium', label: 'Overdue' }
    }
    if (isToday(date)) return { className: 'text-orange-600 dark:text-orange-400', label: 'Today' }
    if (isTomorrow(date)) return { className: 'text-yellow-600 dark:text-yellow-400', label: 'Tomorrow' }
    return { className: 'text-muted-foreground/70', label: format(date, 'MMM d') }
  } catch {
    return { className: 'text-muted-foreground/60', label: '' }
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed': case 'done': return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'in_progress': return <Play className="h-4 w-4 text-blue-500" />
    case 'blocked': return <AlertTriangle className="h-4 w-4 text-red-500" />
    default: return <Target className="h-4 w-4 text-muted-foreground/60" />
  }
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [filterPriority, setFilterPriority] = useState<FilterPriority>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [completingTask, setCompletingTask] = useState<string | null>(null)
  const [dayPlan, setDayPlan] = useState<any>(null)
  const [planningDay, setPlanningDay] = useState(false)

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const data = await fetchTasks()
      setTasks(data.length > 0 ? data : mockTasks)
    } catch (error) {
      console.error('Failed to load tasks:', error)
      setTasks(mockTasks)
    }
    setLoading(false)
  }

  const handleCompleteTask = async (taskId: string) => {
    setCompletingTask(taskId)
    await completeTask(taskId)
    setTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: 'completed' } : t))
    setCompletingTask(null)
  }

  const handleStartTask = async (taskId: string) => {
    await updateTaskStatus(taskId, 'in_progress')
    setTasks(prev => prev.map(t => t.task_id === taskId ? { ...t, status: 'in_progress' } : t))
  }

  const handlePlanMyDay = async () => {
    setPlanningDay(true)
    try {
      const plan = await fetchDayPlan('kowshik.naidu@contoso.com')
      setDayPlan(plan)
    } catch {
      setDayPlan({
        narrative: "Here's your AI-optimized day plan.",
        focus_blocks: [
          { title: "Focus on P0 items first", duration_minutes: 120 },
          { title: "Complete P1 tasks", duration_minutes: 90 }
        ]
      })
    }
    setPlanningDay(false)
  }

  // Filter and sort tasks
  const filteredTasks = tasks.filter(task => {
    if (filterStatus !== 'all' && task.status !== filterStatus) return false
    if (filterPriority !== 'all' && task.priority !== filterPriority) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      return task.title.toLowerCase().includes(q) || task.description.toLowerCase().includes(q)
    }
    return true
  }).sort((a, b) => {
    const priorityOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }
    return (priorityOrder[a.priority] || 3) - (priorityOrder[b.priority] || 3)
  })

  // Stats
  const stats = {
    total: tasks.length,
    active: tasks.filter(t => t.status !== 'completed' && t.status !== 'done').length,
    p0: tasks.filter(t => t.priority === 'P0' && t.status !== 'completed' && t.status !== 'done').length,
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex bg-background">
      {/* Sidebar - Task List */}
      <div className="w-[420px] border-r border-border/50 flex flex-col bg-background">
        {/* Header */}
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-center justify-between mb-5">
            <h1 className="text-[22px] font-semibold tracking-tight">Tasks</h1>
            <div className="flex items-center gap-1">
              {stats.p0 > 0 && (
                <span className="px-2.5 py-1 text-xs font-medium bg-red-500 text-white rounded-full">
                  {stats.p0} P0
                </span>
              )}
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={loadTasks}
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
              placeholder="Search tasks"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 text-sm bg-muted/40 border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-foreground/10 focus:bg-muted/60 transition-all placeholder:text-muted-foreground/50"
            />
          </div>

          {/* Filters - Pill buttons */}
          <div className="flex gap-2 flex-wrap">
            {(['all', 'todo', 'in_progress', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilterStatus(f)}
                className={clsx(
                  'px-3.5 py-1.5 text-[13px] font-medium rounded-full transition-all',
                  filterStatus === f
                    ? 'bg-foreground text-background'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                )}
              >
                {f === 'all' ? 'All' : f === 'in_progress' ? 'In Progress' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Task List */}
        <div className="flex-1 overflow-y-auto">
          {filteredTasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="w-14 h-14 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
                <CheckSquare className="h-7 w-7 opacity-40" />
              </div>
              <p className="text-sm font-medium">No tasks</p>
              <p className="text-xs text-muted-foreground/60 mt-1">All caught up!</p>
            </div>
          ) : (
            <div>
              {filteredTasks.map((task, index) => {
                const style = priorityStyles[task.priority] || priorityStyles.P3
                const isSelected = selectedTask?.task_id === task.task_id
                const dueStyle = getDueDateStyle(task.due_date_utc)
                const isCompleted = task.status === 'completed' || task.status === 'done'
                
                return (
                  <button
                    key={task.task_id}
                    onClick={() => setSelectedTask(task)}
                    className={clsx(
                      'w-full text-left px-5 py-4 transition-colors relative group',
                      isSelected ? 'bg-foreground/[0.05]' : 'hover:bg-muted/40',
                      index !== 0 && 'border-t border-border/30'
                    )}
                  >
                    {/* Priority indicator */}
                    <div className={clsx('absolute left-2 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full', style.indicator)} />
                    
                    <div className="flex gap-3.5 ml-2">
                      {/* Status Icon */}
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center flex-shrink-0">
                        {getStatusIcon(task.status)}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className={clsx(
                            'text-[15px] truncate',
                            isCompleted ? 'text-muted-foreground line-through' : 'font-semibold text-foreground'
                          )}>
                            {task.title}
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
                          {task.description?.slice(0, 80) || 'No description'}
                        </p>
                        
                        {/* Bottom row */}
                        <div className="flex items-center gap-2">
                          <span className={clsx('px-2 py-0.5 text-[11px] font-medium rounded-full', style.badge)}>
                            {task.priority}
                          </span>
                          {task.category && (
                            <span className="text-[11px] text-muted-foreground/50 flex items-center gap-1">
                              <FolderOpen className="h-3 w-3" />
                              {task.category}
                            </span>
                          )}
                          {task.estimated_duration_minutes && (
                            <span className="text-[11px] text-muted-foreground/50 flex items-center gap-1 ml-auto">
                              <Timer className="h-3 w-3" />
                              {formatDuration(task.estimated_duration_minutes)}
                            </span>
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

      {/* Main Content - Task Detail */}
      <div className="flex-1 flex flex-col bg-background">
        {selectedTask ? (
          <>
            {/* Task Header */}
            <div className="px-8 pt-8 pb-6 border-b border-border/30">
              {/* Top toolbar */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  {selectedTask.status !== 'completed' && selectedTask.status !== 'done' && (
                    <>
                      {selectedTask.status !== 'in_progress' && (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground"
                          onClick={() => handleStartTask(selectedTask.task_id)}
                        >
                          <Play className="h-4 w-4" /> Start
                        </Button>
                      )}
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-9 px-4 rounded-lg gap-2 text-muted-foreground hover:text-foreground"
                        onClick={() => handleCompleteTask(selectedTask.task_id)}
                        disabled={completingTask === selectedTask.task_id}
                      >
                        <CheckCircle className={clsx('h-4 w-4', completingTask === selectedTask.task_id && 'animate-spin')} />
                        {completingTask === selectedTask.task_id ? 'Completing...' : 'Complete'}
                      </Button>
                    </>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button 
                    size="sm" 
                    className="h-9 px-4 rounded-lg gap-2 bg-foreground text-background hover:bg-foreground/90"
                    onClick={handlePlanMyDay}
                    disabled={planningDay}
                  >
                    <Sparkles className={clsx('h-4 w-4', planningDay && 'animate-pulse')} />
                    {planningDay ? 'Planning...' : 'AI Plan Day'}
                  </Button>
                  <Button variant="ghost" size="icon" className="h-9 w-9 rounded-lg text-muted-foreground">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Title */}
              <h1 className="text-[28px] font-semibold tracking-tight mb-6 leading-tight">
                {selectedTask.title}
              </h1>

              {/* Meta info */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className={clsx(
                    'w-12 h-12 rounded-full flex items-center justify-center',
                    priorityStyles[selectedTask.priority]?.badge || 'bg-muted'
                  )}>
                    <span className="text-lg font-bold">{selectedTask.priority}</span>
                  </div>
                  <div>
                    <p className="text-[15px] font-semibold capitalize">
                      {selectedTask.status.replace('_', ' ')}
                    </p>
                    <p className="text-[13px] text-muted-foreground/70">
                      {selectedTask.source} • {selectedTask.category || 'Uncategorized'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={getPriorityVariant(selectedTask.priority)} className="px-3 py-1.5 text-xs">
                    {selectedTask.priority} Priority
                  </Badge>
                  <Badge variant={getStatusVariant(selectedTask.status)} className="px-3 py-1.5 text-xs capitalize">
                    {selectedTask.status.replace('_', ' ')}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Task Body */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl px-8 py-8">
                {/* AI Day Plan */}
                {dayPlan && (
                  <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50 to-purple-50 dark:from-violet-950/40 dark:via-indigo-950/40 dark:to-purple-950/40 border border-violet-100 dark:border-violet-900/50">
                    <div className="flex items-center gap-2.5 mb-5">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                      </div>
                      <span className="text-[15px] font-semibold text-violet-700 dark:text-violet-300">AI Day Plan</span>
                      <Button variant="ghost" size="sm" className="ml-auto h-7 text-xs" onClick={() => setDayPlan(null)}>
                        Dismiss
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">{dayPlan.narrative || dayPlan.summary}</p>
                    <div className="space-y-2">
                      {dayPlan.focus_blocks?.map((block: any, i: number) => (
                        <div key={i} className="flex items-center gap-4 p-3 bg-white dark:bg-neutral-900 rounded-xl border border-violet-100 dark:border-violet-900/50">
                          <span className="w-6 h-6 rounded-full bg-violet-500/10 text-violet-600 dark:text-violet-400 flex items-center justify-center text-xs font-medium">
                            {i + 1}
                          </span>
                          <span className="flex-1 text-sm">{block.title}</span>
                          <span className="text-xs text-muted-foreground">{block.duration_minutes} min</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Due Date Info */}
                {selectedTask.due_date_utc && (
                  <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-xl bg-muted/50 border border-border/50">
                    <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center">
                      <CalendarIcon className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <span className={clsx('text-[14px] font-medium', getDueDateStyle(selectedTask.due_date_utc).className)}>
                        Due {format(new Date(selectedTask.due_date_utc), 'EEEE, MMMM d, yyyy')}
                      </span>
                      {getDueDateStyle(selectedTask.due_date_utc).label === 'Overdue' && (
                        <p className="text-[12px] text-red-600/70 dark:text-red-400/60 mt-0.5">
                          This task is overdue!
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Description */}
                <div className="mb-8">
                  <h3 className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-3">Description</h3>
                  <div className="text-[15px] leading-[1.7] text-foreground/85 whitespace-pre-wrap">
                    {selectedTask.description || 'No description provided.'}
                  </div>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-6 p-5 rounded-xl bg-muted/30 border border-border/50">
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Owner</span>
                    <p className="text-[14px] font-medium mt-1">{(selectedTask.owner_user_id || 'Unassigned').replace('usr_', '').replace('_', ' ')}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Created</span>
                    <p className="text-[14px] font-medium mt-1">{selectedTask.created_utc ? format(new Date(selectedTask.created_utc), 'MMM d, yyyy') : 'N/A'}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Source</span>
                    <p className="text-[14px] font-medium mt-1 capitalize">{selectedTask.source}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">Duration</span>
                    <p className="text-[14px] font-medium mt-1">{selectedTask.estimated_duration_minutes ? formatDuration(selectedTask.estimated_duration_minutes) : 'Not estimated'}</p>
                  </div>
                </div>

                {/* Tags */}
                {selectedTask.tags && selectedTask.tags.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-3">Tags</h3>
                    <div className="flex flex-wrap gap-2">
                      {selectedTask.tags.map((tag, i) => (
                        <span key={i} className="px-3 py-1.5 text-[13px] rounded-full bg-muted text-muted-foreground">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <div className="w-20 h-20 rounded-3xl bg-muted/30 flex items-center justify-center mb-6">
              <CheckSquare className="h-10 w-10 opacity-30" />
            </div>
            <h3 className="text-[18px] font-medium mb-2">No task selected</h3>
            <p className="text-[14px] text-muted-foreground/60">Choose a task from the list to view details</p>
          </div>
        )}
      </div>
    </div>
  )
}
