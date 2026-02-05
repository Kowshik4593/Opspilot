'use client'

import { useState, useEffect } from 'react'
import { 
  FileText, Calendar, Clock, RefreshCw, Download, ChevronDown,
  CheckCircle, AlertTriangle, TrendingUp, TrendingDown, Activity,
  Sparkles
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { fetchEODReport, fetchWeeklyReport, fetchEODReportAI, fetchWeeklyReportAI } from '@/lib/api'
import { format, formatDistanceToNow } from 'date-fns'
import { clsx } from 'clsx'

type ReportTab = 'eod' | 'weekly'

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<ReportTab>('eod')
  const [loading, setLoading] = useState(true)
  const [eodReport, setEodReport] = useState<any>(null)
  const [weeklyReport, setWeeklyReport] = useState<any>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    setLoading(true)
    try {
      const [eod, weekly, eodAI, weeklyAI] = await Promise.all([
        fetchEODReport(),
        fetchWeeklyReport(),
        fetchEODReportAI(),
        fetchWeeklyReportAI()
      ])
      // Use AI reports if available, fallback to static
      setEodReport(eodAI?.length > 0 ? eodAI[0] : eod)
      setWeeklyReport(weeklyAI?.length > 0 ? weeklyAI[0] : weekly)
    } catch (error) {
      console.error('Failed to load reports:', error)
    }
    setLoading(false)
  }

  const tabs = [
    { id: 'eod' as const, label: '📊 EOD Report', icon: FileText },
    { id: 'weekly' as const, label: '📅 Weekly Summary', icon: Calendar },
  ]

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col bg-background">
      {/* Header - Apple style */}
      <div className="px-6 pt-6 pb-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          <h1 className="text-[22px] font-semibold tracking-tight">Reports</h1>
          <div className="flex gap-2">
            <Button onClick={loadReports} disabled={loading} variant="outline">
              <RefreshCw className={clsx('h-4 w-4 mr-2', loading && 'animate-spin')} />
              Refresh
            </Button>
            <Button className="gap-2">
              <Download className="h-4 w-4" /> Export
            </Button>
          </div>
        </div>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-6">
      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2',
              activeTab === tab.id
                ? 'bg-primary text-primary-foreground shadow-md'
                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* EOD Report Tab */}
      {activeTab === 'eod' && (
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-gradient-to-br from-green-500/5 to-green-500/10 border-green-200 dark:border-green-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {eodReport?.completed_tasks?.length || 8}
                </div>
                <div className="text-xs text-muted-foreground">✅ Tasks Completed</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-yellow-500/5 to-yellow-500/10 border-yellow-200 dark:border-yellow-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {eodReport?.pending_tasks?.length || 5}
                </div>
                <div className="text-xs text-muted-foreground">⏳ Pending</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-200 dark:border-blue-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {eodReport?.meetings_attended || 4}
                </div>
                <div className="text-xs text-muted-foreground">📅 Meetings</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-purple-500/5 to-purple-500/10 border-purple-200 dark:border-purple-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {eodReport?.emails_processed || 23}
                </div>
                <div className="text-xs text-muted-foreground">📧 Emails Processed</div>
              </CardContent>
            </Card>
          </div>

          {/* EOD Summary Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    End of Day Summary
                  </CardTitle>
                  <CardDescription>
                    {format(new Date(), 'EEEE, MMMM d, yyyy')}
                  </CardDescription>
                </div>
                <Button size="sm" className="gap-2">
                  <Sparkles className="h-4 w-4" /> Generate with AI
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Completed Tasks */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2 text-green-600 dark:text-green-400">
                  <CheckCircle className="h-4 w-4" /> Completed Today
                </h4>
                <ul className="space-y-2">
                  {(eodReport?.completed_tasks || [
                    'Fixed Acme CoreAPI auth token expiry issue',
                    'Reviewed TechVision Phase 2 architecture',
                    'Completed compliance training',
                    'Attended war room for Acme API blocker'
                  ]).map((task: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Pending Tasks */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2 text-yellow-600 dark:text-yellow-400">
                  <Clock className="h-4 w-4" /> Pending / In Progress
                </h4>
                <ul className="space-y-2">
                  {(eodReport?.pending_tasks || [
                    'Coordinate Acme regression testing',
                    'Evaluate API Gateway addition for TechVision',
                    'Tech debt list for Q1 review'
                  ]).map((task: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Clock className="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                      {task}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Blockers */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2 text-red-600 dark:text-red-400">
                  <AlertTriangle className="h-4 w-4" /> Blockers
                </h4>
                <ul className="space-y-2">
                  {(eodReport?.blockers || [
                    'Waiting on client confirmation for war room time',
                    'Need infrastructure team access for firewall rules'
                  ]).map((blocker: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                      {blocker}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Highlights */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2 text-blue-600 dark:text-blue-400">
                  <TrendingUp className="h-4 w-4" /> Highlights
                </h4>
                <ul className="space-y-2">
                  {(eodReport?.highlights || [
                    'Successfully resolved P0 blocker for Acme launch',
                    'Finance approved $500k budget for TechVision Phase 2',
                    'Positive feedback from client on quick turnaround'
                  ]).map((highlight: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                      {highlight}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Weekly Summary Tab */}
      {activeTab === 'weekly' && (
        <div className="space-y-6">
          {/* Weekly Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-gradient-to-br from-green-500/5 to-green-500/10 border-green-200 dark:border-green-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {weeklyReport?.total_tasks_completed || 32}
                </div>
                <div className="text-xs text-muted-foreground">Tasks Completed</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-blue-500/5 to-blue-500/10 border-blue-200 dark:border-blue-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {weeklyReport?.total_meetings || 18}
                </div>
                <div className="text-xs text-muted-foreground">Meetings</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-purple-500/5 to-purple-500/10 border-purple-200 dark:border-purple-900">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                    {weeklyReport?.wellness_average || 72}%
                  </div>
                  <TrendingUp className="h-4 w-4 text-green-500" />
                </div>
                <div className="text-xs text-muted-foreground">Wellness Score</div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-orange-500/5 to-orange-500/10 border-orange-200 dark:border-orange-900">
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">87%</div>
                <div className="text-xs text-muted-foreground">Productivity</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Weekly Summary
              </CardTitle>
              <CardDescription>
                {weeklyReport?.week_start || 'Jan 20'} - {weeklyReport?.week_end || 'Jan 26, 2026'}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="font-medium mb-3">📈 Highlights</h4>
                <ul className="space-y-2">
                  {(weeklyReport?.highlights || [
                    'Delivered Acme API hotfix ahead of schedule',
                    'Completed TechVision Phase 1 milestone',
                    'Reduced email backlog by 40%',
                    'Improved team velocity by 15%'
                  ]).map((item: string, i: number) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-3">🎯 Areas for Improvement</h4>
                <ul className="space-y-2">
                  {(weeklyReport?.areas_for_improvement || [
                    'Focus time was 20% below target',
                    'Meeting hours exceeded recommended limit',
                    'Tech debt backlog growing'
                  ]).map((item: string, i: number) => (
                    <li key={i} className="text-sm flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      </div>
    </div>
  )
}
