'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { 
  Mail, 
  CheckSquare, 
  Calendar, 
  Bell, 
  BarChart3, 
  Heart, 
  MessageSquare,
  Activity,
  LayoutDashboard
} from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'
import { clsx } from 'clsx'
import { Button } from '@/components/ui/button'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Mail', href: '/mail', icon: Mail },
  { name: 'Tasks', href: '/tasks', icon: CheckSquare },
  { name: 'Calendar', href: '/calendar', icon: Calendar },
  { name: 'Notifications', href: '/notifications', icon: Bell },
  { name: 'Reports', href: '/reports', icon: BarChart3 },
  { name: 'Wellness', href: '/wellness', icon: Heart },
  { name: 'Assistant', href: '/assistant', icon: MessageSquare },
  { name: 'Activity', href: '/activity', icon: Activity },
]

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Header - Enterprise Grade */}
      <header className="sticky top-0 z-50 w-full h-16 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-16 items-center px-6">
          <div className="flex items-center mr-6 min-w-[240px]">
            <Image 
              src="/opspilot-logo.png" 
              alt="OpsPilot" 
              width={240} 
              height={56} 
              className="h-14 w-auto"
            />
          </div>
          
          <div className="flex-1 flex items-center justify-between">
            <nav className="flex items-center space-x-6 text-sm font-medium">
               {/* Top nav items could go here if needed */}
            </nav>
            <div className="flex items-center gap-4">
               <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-secondary/50 rounded-full border border-border/50">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-medium text-muted-foreground">System Operational</span>
               </div>
               <ThemeToggle />
               <Button variant="ghost" size="icon" className="rounded-full">
                 <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center border border-input">
                    <span className="text-xs font-semibold">JD</span>
                 </div>
               </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 border-r bg-background/50 hidden md:block overflow-y-auto py-6 px-4">
          <div className="mb-6 px-2">
            <h3 className="mb-2 px-2 text-xs font-semibold text-muted-foreground tracking-wider uppercase">Platform</h3>
            <div className="space-y-1">
              {navigation.slice(0, 5).map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={clsx(
                      'nav-item',
                      isActive ? 'nav-item-active' : 'nav-item-inactive'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </div>

          <div className="px-2">
            <h3 className="mb-2 px-2 text-xs font-semibold text-muted-foreground tracking-wider uppercase">Analysis</h3>
            <div className="space-y-1">
              {navigation.slice(5).map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={clsx(
                      'nav-item',
                      isActive ? 'nav-item-active' : 'nav-item-inactive'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.name}
                  </Link>
                )
              })}
            </div>
          </div>
          
          <div className="mt-auto pt-10 px-2 lg:block hidden">
             <div className="rounded-lg bg-secondary/50 p-4 border border-border/50">
                <p className="text-xs font-medium mb-1">Autonomous Agent</p>
                <div className="h-1.5 w-full bg-background rounded-full overflow-hidden">
                  <div className="h-full bg-primary w-2/3 rounded-full" />
                </div>
                <p className="text-[10px] text-muted-foreground mt-2">Processing tasks...</p>
             </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto bg-muted/20 p-8">
          <div className="mx-auto max-w-7xl animate-in fade-in duration-500 slide-in-from-bottom-2">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
