'use client'

import { useState, useEffect } from 'react'
import { 
  Heart, Smile, Frown, Meh, Coffee, Brain, Wind, Timer, Sun, Moon,
  TrendingUp, TrendingDown, AlertTriangle, RefreshCw, Play, Pause,
  Sparkles, Target, Activity, Clock, Zap, Volume2, Calendar
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  fetchWellnessConfig, fetchMoodHistory, fetchBreakSuggestions, 
  fetchWellnessScore, fetchWellnessJoke, fetchWellnessMotivation, fetchWellnessBreak,
  fetchBreathingExercise, fetchBurnoutRisk, fetchFocusBlocks, fetchMeetingDetox, logMood,
  type WellnessConfig, type MoodEntry 
} from '@/lib/api'
import { format, formatDistanceToNow } from 'date-fns'
import { clsx } from 'clsx'

// Safe date format helper
function safeFormatDate(dateStr: string | null | undefined, formatStr: string, fallback: string = 'N/A'): string {
  if (!dateStr) return fallback
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return fallback
    return format(date, formatStr)
  } catch {
    return fallback
  }
}

type MoodType = 'great' | 'good' | 'okay' | 'stressed' | 'overwhelmed'

const moodEmojis: Record<MoodType, { emoji: string; color: string; icon: any }> = {
  great: { emoji: '😊', color: 'text-green-500', icon: Smile },
  good: { emoji: '🙂', color: 'text-blue-500', icon: Smile },
  okay: { emoji: '😐', color: 'text-yellow-500', icon: Meh },
  stressed: { emoji: '😰', color: 'text-orange-500', icon: Frown },
  overwhelmed: { emoji: '😫', color: 'text-red-500', icon: Frown },
}

function getScoreLevel(score: number): { label: string; color: string; emoji: string } {
  if (score >= 80) return { label: 'Healthy', color: 'text-green-500', emoji: '🟢' }
  if (score >= 60) return { label: 'Moderate', color: 'text-yellow-500', emoji: '🟡' }
  if (score >= 40) return { label: 'Elevated', color: 'text-orange-500', emoji: '🟠' }
  return { label: 'Critical', color: 'text-red-500', emoji: '🔴' }
}

export default function WellnessPage() {
  const [wellnessConfig, setWellnessConfig] = useState<WellnessConfig | null>(null)
  const [wellnessData, setWellnessData] = useState<any>(null)
  const [moodHistory, setMoodHistory] = useState<MoodEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedMood, setSelectedMood] = useState<MoodType | null>(null)
  const [showBreathingExercise, setShowBreathingExercise] = useState(false)
  const [breathingPhase, setBreathingPhase] = useState<'inhale' | 'hold' | 'exhale'>('inhale')
  const [breathingCount, setBreathingCount] = useState(0)
  const [joke, setJoke] = useState<any>(null)
  const [motivation, setMotivation] = useState<any>(null)
  const [breakSuggestion, setBreakSuggestion] = useState<any>(null)
  const [burnoutRisk, setBurnoutRisk] = useState<any>(null)
  const [focusBlocks, setFocusBlocks] = useState<any[]>([])
  const [meetingDetox, setMeetingDetox] = useState<any[]>([])
  const userEmail = 'alice@example.com' // Default user

  useEffect(() => {
    loadWellnessData()
  }, [])

  const loadWellnessData = async () => {
    setLoading(true)
    try {
      const [config, mood, scoreData] = await Promise.all([
        fetchWellnessConfig(),
        fetchMoodHistory(),
        fetchWellnessScore(userEmail)
      ])
      setWellnessConfig(config)
      setMoodHistory(mood)
      if (scoreData) setWellnessData(scoreData)
    } catch (error) {
      console.error('Failed to load wellness data:', error)
    }
    setLoading(false)
  }

  // Use dynamically calculated score from API, fallback to config or default
  const score = wellnessData?.score ?? wellnessConfig?.score ?? 72
  const scoreLevel = getScoreLevel(score)

  // Map factor names to icons
  const factorIcons: Record<string, any> = {
    p0_tasks: AlertTriangle,
    overdue: Clock,
    meetings: Calendar,
    focus_time: Target,
    email_backlog: Activity,
    nudge_pressure: Zap,
  }

  // Use real factors from API, with fallback to simulated data
  const factors = wellnessData?.factors?.map((f: any) => ({
    label: f.name?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()) || f.name,
    value: f.value,
    threshold: f.status || 'yellow',
    icon: factorIcons[f.name] || Activity,
    impact: f.impact > 0 ? `-${f.impact}` : '0',
    detail: f.detail,
  })) || [
    { label: 'P0 Tasks', value: 2, threshold: 'yellow', icon: AlertTriangle, impact: '-8' },
    { label: 'Overdue Items', value: 1, threshold: 'green', icon: Clock, impact: '-4' },
    { label: 'Meeting Hours', value: 5, threshold: 'yellow', icon: Calendar, impact: '-6' },
    { label: 'Focus Time', value: 45, threshold: 'orange', icon: Target, impact: '-10' },
    { label: 'Email Backlog', value: 8, threshold: 'yellow', icon: Activity, impact: '-5' },
    { label: 'Critical Nudges', value: 3, threshold: 'yellow', icon: Zap, impact: '-5' },
  ]

  const handleGetJoke = async () => {
    const result = await fetchWellnessJoke()
    if (result) setJoke(result)
  }

  const handleGetMotivation = async () => {
    const result = await fetchWellnessMotivation()
    if (result) setMotivation(result)
  }

  const handleGetBreak = async () => {
    const result = await fetchWellnessBreak('short')
    if (result) setBreakSuggestion(result)
  }

  const handleCheckBurnout = async () => {
    const result = await fetchBurnoutRisk(userEmail)
    if (result) setBurnoutRisk(result)
  }

  const handleGetFocusBlocks = async () => {
    const result = await fetchFocusBlocks()
    if (result) setFocusBlocks(result)
  }

  const handleGetMeetingDetox = async () => {
    const result = await fetchMeetingDetox()
    if (result) setMeetingDetox(result)
  }

  const handleMoodSelect = async (mood: MoodType) => {
    setSelectedMood(mood)
    await logMood(mood, userEmail)
  }

  const startBreathingExercise = async () => {
    const exercise = await fetchBreathingExercise('box')
    setShowBreathingExercise(true)
    setBreathingPhase('inhale')
    setBreathingCount(0)
    
    let count = 0
    const phases = ['inhale', 'hold', 'exhale'] as const
    let phaseIndex = 0
    
    const interval = setInterval(() => {
      count++
      if (count % 4 === 0) {
        phaseIndex = (phaseIndex + 1) % 3
        setBreathingPhase(phases[phaseIndex])
        if (phaseIndex === 0) {
          setBreathingCount(prev => prev + 1)
        }
      }
    }, 1000)

    setTimeout(() => {
      clearInterval(interval)
      setShowBreathingExercise(false)
    }, 60000) // 1 minute exercise
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col bg-background">
      {/* Header - Apple style */}
      <div className="px-6 pt-6 pb-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          <h1 className="text-[22px] font-semibold tracking-tight">Wellness</h1>
          <Button onClick={loadWellnessData} disabled={loading} variant="outline">
            <RefreshCw className={clsx('h-4 w-4 mr-2', loading && 'animate-spin')} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-6">
      {/* Main Score Card */}
      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <Card className="lg:col-span-1 bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5">
          <CardContent className="p-6 text-center">
            <div className="relative w-32 h-32 mx-auto mb-4">
              {/* Circular progress ring */}
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  className="text-muted/20"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="42"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="none"
                  strokeDasharray={`${score * 2.64} 264`}
                  strokeLinecap="round"
                  className={clsx(
                    score >= 80 ? 'text-green-500' :
                    score >= 60 ? 'text-yellow-500' :
                    score >= 40 ? 'text-orange-500' : 'text-red-500'
                  )}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-bold">{score}</span>
                <span className="text-sm text-muted-foreground">/ 100</span>
              </div>
            </div>
            <div className={clsx('text-xl font-semibold mb-1', scoreLevel.color)}>
              {scoreLevel.emoji} {scoreLevel.label}
            </div>
            <p className="text-sm text-muted-foreground">
              Your workload wellness score
            </p>
          </CardContent>
        </Card>

        {/* Factors Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Wellness Factors
            </CardTitle>
            <CardDescription>What's affecting your score today</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {factors.map((factor, i) => (
                <div 
                  key={i} 
                  className={clsx(
                    'p-3 rounded-lg border',
                    factor.threshold === 'green' ? 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900' :
                    factor.threshold === 'yellow' ? 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900' :
                    factor.threshold === 'orange' ? 'bg-orange-50 dark:bg-orange-950/20 border-orange-200 dark:border-orange-900' :
                    'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900'
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <factor.icon className={clsx(
                      'h-4 w-4',
                      factor.threshold === 'green' ? 'text-green-500' :
                      factor.threshold === 'yellow' ? 'text-yellow-500' :
                      factor.threshold === 'orange' ? 'text-orange-500' : 'text-red-500'
                    )} />
                    <span className={clsx(
                      'text-xs font-medium',
                      factor.threshold === 'green' ? 'text-green-600' :
                      factor.threshold === 'yellow' ? 'text-yellow-600' :
                      factor.threshold === 'orange' ? 'text-orange-600' : 'text-red-600'
                    )}>
                      {factor.impact}
                    </span>
                  </div>
                  <div className="text-lg font-bold">{factor.value}</div>
                  <div className="text-xs text-muted-foreground">{factor.label}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Action Cards Row */}
      <div className="grid md:grid-cols-3 gap-6 mb-6">
        {/* Mood Check-in */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Heart className="h-5 w-5" />
              Mood Check-in
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">How are you feeling right now?</p>
            <div className="grid grid-cols-5 gap-1">
              {(Object.keys(moodEmojis) as MoodType[]).map((mood) => (
                <button
                  key={mood}
                  onClick={() => handleMoodSelect(mood)}
                  className={clsx(
                    'p-2 rounded-lg transition-all text-center min-w-0',
                    selectedMood === mood 
                      ? 'bg-primary text-primary-foreground scale-105 shadow-md' 
                      : 'bg-muted/50 hover:bg-muted'
                  )}
                >
                  <span className="text-xl block">{moodEmojis[mood].emoji}</span>
                  <div className="text-[10px] mt-1 capitalize truncate">{mood}</div>
                </button>
              ))}
            </div>
            {selectedMood && (
              <div className="mt-4 p-3 bg-green-50 dark:bg-green-950/20 rounded-lg text-center">
                <p className="text-sm text-green-600 dark:text-green-400">
                  ✓ Logged! {moodEmojis[selectedMood].emoji} Feeling {selectedMood}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5" />
              Quick Wellness Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Button 
              variant="outline" 
              className="w-full justify-start gap-2"
              onClick={startBreathingExercise}
            >
              <Wind className="h-4 w-4" /> Breathing Exercise (1 min)
            </Button>
            <Button 
              variant="outline" 
              className="w-full justify-start gap-2"
              onClick={handleGetBreak}
            >
              <Coffee className="h-4 w-4" /> Get Break Suggestion
            </Button>
            <Button 
              variant="outline" 
              className="w-full justify-start gap-2"
              onClick={handleGetFocusBlocks}
            >
              <Target className="h-4 w-4" /> Find Focus Time
            </Button>
            <Button 
              variant="outline" 
              className="w-full justify-start gap-2"
              onClick={handleGetMotivation}
            >
              <Sparkles className="h-4 w-4" /> Get Motivation
            </Button>
          </CardContent>
        </Card>

        {/* Burnout Risk */}
        <Card className={clsx(
          score < 45 ? 'bg-gradient-to-br from-red-500/10 to-red-500/5 border-red-200 dark:border-red-900' :
          score < 60 ? 'bg-gradient-to-br from-yellow-500/10 to-yellow-500/5 border-yellow-200 dark:border-yellow-900' :
          'bg-gradient-to-br from-green-500/10 to-green-500/5 border-green-200 dark:border-green-900'
        )}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className={clsx(
                'h-5 w-5',
                score < 45 ? 'text-red-500' :
                score < 60 ? 'text-yellow-500' : 'text-green-500'
              )} />
              Burnout Risk Assessment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={clsx(
              'text-2xl font-bold mb-2',
              score < 45 ? 'text-red-600 dark:text-red-400' :
              score < 60 ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400'
            )}>
              {score < 45 ? '⚠️ High Risk' : score < 60 ? '⚡ Moderate Risk' : '✓ Low Risk'}
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              {score < 45 
                ? 'Multiple stress factors detected. Consider taking a break and prioritizing self-care.'
                : score < 60 
                ? 'Some stress factors present. Monitor closely and take preventive actions.'
                : 'Your workload is manageable. Keep up the good habits!'}
            </p>
            <div className="space-y-2">
              {score < 60 && (
                <>
                  <div className="text-xs text-muted-foreground">Recommendations:</div>
                  <ul className="text-sm space-y-1">
                    <li>• Schedule a 15-min break in the next hour</li>
                    <li>• Decline or reschedule one meeting today</li>
                    <li>• Delegate one non-critical task</li>
                  </ul>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Breathing Exercise Modal */}
      {showBreathingExercise && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-96 text-center">
            <CardHeader>
              <CardTitle>🌬️ Breathing Exercise</CardTitle>
              <CardDescription>Follow the rhythm to calm your mind</CardDescription>
            </CardHeader>
            <CardContent className="py-8">
              <div className={clsx(
                'w-32 h-32 rounded-full mx-auto flex items-center justify-center transition-all duration-1000',
                breathingPhase === 'inhale' && 'scale-125 bg-blue-500/20',
                breathingPhase === 'hold' && 'scale-125 bg-purple-500/20',
                breathingPhase === 'exhale' && 'scale-100 bg-green-500/20',
              )}>
                <span className="text-4xl">
                  {breathingPhase === 'inhale' ? '🌬️' : breathingPhase === 'hold' ? '⏸️' : '💨'}
                </span>
              </div>
              <div className="mt-4 text-xl font-semibold capitalize">
                {breathingPhase}
              </div>
              <div className="text-sm text-muted-foreground mt-2">
                Cycle {breathingCount + 1} of 5
              </div>
              <Button 
                variant="outline" 
                className="mt-6"
                onClick={() => setShowBreathingExercise(false)}
              >
                End Exercise
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Fun Section - Joke */}
      <Card className="bg-gradient-to-r from-purple-500/5 via-pink-500/5 to-purple-500/5">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-semibold flex items-center gap-2">
                😄 Need a Laugh?
              </h3>
              {joke ? (
                <div className="mt-2">
                  <p className="text-sm font-medium">{joke.setup || joke}</p>
                  {joke.punchline && (
                    <p className="text-sm text-muted-foreground mt-2 italic">
                      {joke.punchline}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground mt-2 italic">
                  Why do programmers prefer dark mode? Because light attracts bugs! 🐛
                </p>
              )}
            </div>
            <Button variant="outline" size="sm" onClick={handleGetJoke}>
              New Joke
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Motivation Section */}
      {motivation && (
        <Card className="mt-4 bg-gradient-to-r from-blue-500/5 via-cyan-500/5 to-blue-500/5">
          <CardContent className="p-6">
            <h3 className="font-semibold flex items-center gap-2">
              💪 Motivation
            </h3>
            <p className="text-sm font-medium mt-2">
              {motivation.quote || (typeof motivation === 'string' ? motivation : '')}
            </p>
            {motivation.explanation && (
              <p className="text-sm text-muted-foreground mt-1 italic">
                {motivation.explanation}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Break Suggestion */}
      {breakSuggestion && (
        <Card className="mt-4 bg-gradient-to-r from-green-500/5 via-emerald-500/5 to-green-500/5">
          <CardContent className="p-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold flex items-center gap-2">
                  <span className="text-xl">{breakSuggestion.emoji || '☕'}</span>
                  {breakSuggestion.activity || 'Break Suggestion'}
                </h3>
                {breakSuggestion.duration_minutes && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Duration: {breakSuggestion.duration_minutes} minutes
                  </p>
                )}
                <p className="text-sm mt-2">
                  {breakSuggestion.description || breakSuggestion.suggestion || 'Take a short break to refresh your mind.'}
                </p>
              </div>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setBreakSuggestion(null)}
              >
                ✕
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Focus Blocks */}
      {focusBlocks && focusBlocks.length > 0 && (
        <Card className="mt-4 bg-gradient-to-r from-orange-500/5 via-amber-500/5 to-orange-500/5">
          <CardContent className="p-6">
            <h3 className="font-semibold flex items-center gap-2">
              <Target className="h-5 w-5" /> Available Focus Blocks
            </h3>
            <div className="mt-2 space-y-2">
              {focusBlocks.map((block: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span>{block.start_time || block.start || block.time || 'Focus Block'}</span>
                  {block.end_time && <span className="text-muted-foreground">- {block.end_time}</span>}
                  {block.duration_minutes && <span className="text-muted-foreground">({block.duration_minutes} min)</span>}
                  {block.suggested_task && <span className="text-xs bg-muted px-2 py-0.5 rounded">{block.suggested_task}</span>}
                  {block.block_type && <Badge variant="outline" className="text-xs">{block.block_type}</Badge>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Mood History */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Mood History
          </CardTitle>
          <CardDescription>Your recent mood check-ins</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 flex-wrap">
            {(moodHistory.length > 0 ? moodHistory : [
              { timestamp: new Date(Date.now() - 3600000).toISOString(), mood: 'good' as MoodType },
              { timestamp: new Date(Date.now() - 86400000).toISOString(), mood: 'okay' as MoodType },
              { timestamp: new Date(Date.now() - 172800000).toISOString(), mood: 'great' as MoodType },
              { timestamp: new Date(Date.now() - 259200000).toISOString(), mood: 'stressed' as MoodType },
              { timestamp: new Date(Date.now() - 345600000).toISOString(), mood: 'good' as MoodType },
            ]).slice(0, 7).map((entry, i) => (
              <div key={i} className="text-center p-2 rounded-lg bg-muted/50">
                <div className="text-2xl">{moodEmojis[entry.mood as MoodType]?.emoji || '😐'}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  {safeFormatDate(entry.timestamp, 'EEE')}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      </div>
    </div>
  )
}
