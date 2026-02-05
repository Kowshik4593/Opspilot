'use client'

import { useState, useEffect } from 'react'
import { 
  Mail, CheckSquare, Calendar, TrendingUp, AlertCircle, CheckCircle, 
  Heart, Bell, Bot, Sparkles, ArrowRight, Clock, Target, Zap,
  BarChart3, Users, Building2, RefreshCw, ArrowUpRight
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import Link from 'next/link'
import { 
  fetchEmails, fetchTasks, fetchMeetings, fetchFollowups, fetchWellnessConfig,
  type Email, type Task, type Meeting, type Followup
} from '@/lib/api'
import { format, isToday, isTomorrow, isPast, parseISO } from 'date-fns'
import { clsx } from 'clsx'

export default function DashboardPage() {
  const [emails, setEmails] = useState<Email[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [followups, setFollowups] = useState<Followup[]>([])
  const [wellnessScore, setWellnessScore] = useState(72)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      const [emailData, taskData, meetingData, followupData, wellnessData] = await Promise.all([
        fetchEmails().catch(() => []),
        fetchTasks().catch(() => []),
        fetchMeetings().catch(() => []),
        fetchFollowups().catch(() => []),
        fetchWellnessConfig().catch(() => ({ score: 75 }))
      ])
      setEmails(emailData)
      setTasks(taskData)
      setMeetings(meetingData)
      setFollowups(followupData)
      setWellnessScore(wellnessData?.score || 72)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    }
    setLoading(false)
  }

  // Calculate stats
  const actionableEmails = emails.filter(e => e.actionability_gt === 'actionable' || e.triage_result?.category === 'actionable').length
  const activeTasks = tasks.filter(t => t.status !== 'completed' && t.status !== 'done').length
  const p0Tasks = tasks.filter(t => t.priority === 'P0' && t.status !== 'completed' && t.status !== 'done').length
  const todayMeetings = meetings.filter(m => {
    const start = parseISO(m.scheduled_start_utc || m.start_utc || '')
    return isToday(start)
  }).length

  // Derived Activity Feed
  const recentActivity = [
    ...emails.slice(0, 3).map(e => ({
      type: 'email',
      icon: Mail,
      title: e.sender_name || e.from_email?.split('@')[0] || 'Unknown',
      subtitle: e.subject,
      time: e.received_utc,
      href: '/mail',
      priority: e.actionability_gt === 'actionable' ? 'high' : 'normal'
    })),
    ...tasks.slice(0, 3).map(t => ({
      type: 'task',
      icon: CheckSquare,
      title: t.title,
      subtitle: 'Priority ' + t.priority,
      time: t.created_utc,
      href: '/tasks',
      priority: t.priority === 'P0' ? 'high' : 'normal'
    }))
  ].sort((a, b) => new Date(b.time || '').getTime() - new Date(a.time || '').getTime()).slice(0, 5)

  if (loading) {
    return <DashboardSkeleton />
  }

  return (
    <div className='space-y-8 pb-8'>
      {/* Welcome Section */}
      <div className='flex flex-col gap-2'>
        <h1 className='text-3xl font-bold tracking-tight'>Overview</h1>
        <p className='text-muted-foreground'>
          Welcome back. Here's what's happening in your workspace today.
        </p>
      </div>

      {/* KPI Grid */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        <StatsCard 
          title='New Emails' 
          value={actionableEmails} 
          icon={Mail} 
          description='Actionable items'
          trend='+12% from yesterday'
        />
        <StatsCard 
          title='Active Tasks' 
          value={activeTasks} 
          icon={CheckSquare}
          description={p0Tasks + ' critical priority'} 
          alert={p0Tasks > 0}
        />
        <StatsCard 
          title='Meetings' 
          value={todayMeetings} 
          icon={Calendar} 
          description='Scheduled for today'
        />
        <StatsCard 
          title='Wellness' 
          value={wellnessScore + '%'} 
          icon={Heart} 
          description='Energy level'
          trendClass={wellnessScore > 80 ? 'text-emerald-500' : 'text-amber-500'}
        />
      </div>

      {/* Main Content Grid */}
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-7'>
        
        {/* Activity Feed (Left 4 cols) */}
        <Card className='col-span-4 border-border/60 shadow-sm' variant='default'>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Your latest communications and task updates.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className='space-y-6'>
              {recentActivity.map((item, index) => (
                <div key={index} className='flex items-start gap-4 group'>
                  <div className={clsx(
                    'mt-1 flex h-9 w-9 items-center justify-center rounded-full border transition-colors',
                    item.priority === 'high' 
                      ? 'border-amber-200 bg-amber-50 text-amber-600 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-400' 
                      : 'border-border bg-secondary/50 text-muted-foreground group-hover:bg-secondary group-hover:text-foreground'
                  )}>
                    <item.icon className='h-4 w-4' />
                  </div>
                  <div className='flex-1 space-y-1'>
                    <p className='text-sm font-medium leading-none'>{item.title}</p>
                    <p className='text-sm text-muted-foreground line-clamp-1'>{item.subtitle}</p>
                  </div>
                  <div className='flex items-center gap-2'>
                     <span className='text-xs text-muted-foreground tabular-nums'>
                      {item.time ? format(parseISO(item.time), 'h:mm a') : 'Now'}
                     </span>
                     <Button variant='ghost' size='icon' className='h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity' asChild>
                       <Link href={item.href}><ArrowUpRight className='h-4 w-4' /></Link>
                     </Button>
                  </div>
                </div>
              ))}
              
              {recentActivity.length === 0 && (
                <div className='text-center py-8 text-muted-foreground'>
                  No recent activity
                </div>
              )}
            </div>
          </CardContent>
          <CardFooter>
            <Button variant='outline' className='w-full text-xs' asChild>
              <Link href='/activity'>View all activity</Link>
            </Button>
          </CardFooter>
        </Card>

        {/* Side Widgets (Right 3 cols) */}
        <div className='col-span-3 space-y-4'>
            {/* Assistant Widget */}
            <Card className='bg-gradient-to-br from-primary/5 via-primary/0 to-transparent border-primary/10'>
                <CardHeader className='pb-3'>
                    <div className='flex items-center justify-between'>
                        <CardTitle className='text-base'>AI Assistant</CardTitle>
                        <Bot className='h-4 w-4 text-primary' />
                    </div>
                </CardHeader>
                <CardContent>
                    <div className='rounded-lg bg-background/50 border border-border/50 p-3 mb-3'>
                        <p className='text-sm text-muted-foreground'>
                          'You have 3 conflicts in your schedule next week. Shall I resolve them?'
                        </p>
                    </div>
                    <div className='flex gap-2'>
                        <Button size='sm' className='w-full text-xs'>Resolve</Button>
                        <Button size='sm' variant='outline' className='w-full text-xs'>Ignore</Button>
                    </div>
                </CardContent>
            </Card>

            {/* Meetings Widget */}
            <Card>
                <CardHeader>
                    <CardTitle className='text-base'>Upcoming</CardTitle>
                </CardHeader>
                <CardContent className='space-y-4'>
                  {meetings.slice(0, 3).map((m, i) => (
                    <div key={i} className='flex items-center gap-3'>
                        <div className='flex flex-col items-center justify-center w-10 h-10 rounded-lg bg-secondary/50 border border-border/50'>
                            <span className='text-[10px] font-bold uppercase text-muted-foreground'>
                              {m.scheduled_start_utc ? format(parseISO(m.scheduled_start_utc), 'MMM') : 'Tod'}
                            </span>
                            <span className='text-sm font-bold'>
                              {m.scheduled_start_utc ? format(parseISO(m.scheduled_start_utc), 'd') : 'Now'}
                            </span>
                        </div>
                        <div className='flex-1 overflow-hidden'>
                            <p className='text-sm font-medium truncate'>{m.subject || 'Meeting'}</p>
                            <p className='text-xs text-muted-foreground'>
                                {m.scheduled_start_utc ? format(parseISO(m.scheduled_start_utc), 'h:mm a') : 'TBD'}
                            </p>
                        </div>
                    </div>
                  ))}
                  {meetings.length === 0 && (
                      <p className='text-sm text-muted-foreground'>No upcoming meetings.</p>
                  )}
                </CardContent>
            </Card>
        </div>
      </div>
    </div>
  )
}

function StatsCard({ title, value, icon: Icon, description, trend, trendClass, alert }: any) {
  return (
    <Card className={clsx('transition-all', alert && 'border-amber-500/50 bg-amber-50/10')}>
      <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
        <CardTitle className='text-sm font-medium'>
          {title}
        </CardTitle>
        <Icon className={clsx('h-4 w-4 text-muted-foreground', alert && 'text-amber-500')} />
      </CardHeader>
      <CardContent>
        <div className='text-2xl font-bold'>{value}</div>
        <p className='text-xs text-muted-foreground mt-1'>
          {trend && <span className={clsx('mr-1', trendClass || 'text-emerald-500')}>{trend}</span>}
          {description}
        </p>
      </CardContent>
    </Card>
  )
}

function DashboardSkeleton() {
  return (
    <div className='space-y-8'>
      <div className='space-y-2'>
        <Skeleton className='h-8 w-[200px]' />
        <Skeleton className='h-4 w-[300px]' />
      </div>
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
        {[1,2,3,4].map(i => (
          <Card key={i}>
            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-2'>
              <Skeleton className='h-4 w-[100px]' />
              <Skeleton className='h-4 w-4' />
            </CardHeader>
            <CardContent>
              <Skeleton className='h-8 w-[60px] mb-2' />
              <Skeleton className='h-3 w-[120px]' />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-7'>
        <Card className='col-span-4'>
           <CardHeader><Skeleton className='h-6 w-[150px]' /></CardHeader>
           <CardContent className='space-y-4'>
              {[1,2,3].map(i => <div key={i} className='flex gap-4'><Skeleton className='h-10 w-10 rounded-full' /><div className='space-y-2'><Skeleton className='h-4 w-[250px]' /><Skeleton className='h-3 w-[200px]' /></div></div>)}
           </CardContent>
        </Card>
        <div className='col-span-3 space-y-4'>
           <Card className='h-[200px]'><CardHeader><Skeleton className='h-5 w-[100px]' /></CardHeader></Card>
        </div>
      </div>
    </div>
  )
}
