# ⚡ AWOA Frontend - Quick Reference

## 🚀 Quick Start (3 Commands)

```powershell
cd frontend
npm install
npm run dev
```

Open: **http://localhost:3000**

---

## 📂 File Locations

| What | Where |
|------|-------|
| **Pages** | `src/app/[page]/page.tsx` |
| **Layout** | `src/components/layout/main-layout.tsx` |
| **UI Components** | `src/components/ui/` |
| **API Functions** | `src/lib/api.ts` |
| **Styles** | `src/app/globals.css` |
| **Config** | `tailwind.config.ts`, `next.config.js` |

---

## 🎨 Component Quick Reference

### Import Components
```tsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
```

### Button Variants
```tsx
<Button variant="default">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>

<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
```

### Card Structure
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    Content here
  </CardContent>
  <CardFooter>
    Footer actions
  </CardFooter>
</Card>
```

### Badges
```tsx
<Badge variant="default">Default</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="destructive">Error</Badge>
```

---

## 🎨 Tailwind Classes - Common Patterns

### Layout
```tsx
className="container py-8"                    // Page wrapper
className="grid gap-6 md:grid-cols-2"        // Responsive grid
className="flex items-center justify-between" // Flex layout
className="space-y-4"                         // Vertical spacing
```

### Colors
```tsx
className="bg-primary text-primary-foreground" // Primary button
className="bg-secondary text-secondary-foreground" // Secondary
className="text-muted-foreground"             // Subtle text
className="border border-input"               // Input border
```

### Hover Effects
```tsx
className="hover:bg-accent hover:text-accent-foreground"
className="hover:border-primary/50 hover:shadow-md"
className="transition-theme" // Smooth color transitions
```

### Responsive
```tsx
className="md:grid-cols-2 lg:grid-cols-3"  // Responsive columns
className="hidden md:block"                 // Hide on mobile
className="text-sm md:text-base"            // Responsive text
```

---

## 🔧 Common Tasks

### Add New Page

1. **Create page file**:
   ```
   src/app/my-page/page.tsx
   ```

2. **Basic template**:
   ```tsx
   export default function MyPage() {
     return (
       <div className="container py-8">
         <h1 className="text-4xl font-bold mb-2">My Page</h1>
         <p className="text-muted-foreground text-lg">Description</p>
       </div>
     )
   }
   ```

3. **Add to navigation** (`src/components/layout/main-layout.tsx`):
   ```tsx
   { name: 'My Page', href: '/my-page', icon: YourIcon }
   ```

### Add API Endpoint

In `src/lib/api.ts`:
```typescript
export async function fetchMyData(): Promise<MyType[]> {
  try {
    const response = await fetch(`${API_BASE}/api/my-endpoint`)
    if (!response.ok) throw new Error('Failed to fetch')
    return await response.json()
  } catch (error) {
    console.error('Error:', error)
    return []
  }
}
```

### Use in Component
```tsx
'use client'

import { useState, useEffect } from 'react'
import { fetchMyData } from '@/lib/api'

export default function MyPage() {
  const [data, setData] = useState([])
  
  useEffect(() => {
    fetchMyData().then(setData)
  }, [])
  
  return <div>{/* Use data */}</div>
}
```

---

## 🌓 Theme Access

```tsx
'use client'

import { useTheme } from 'next-themes'

function MyComponent() {
  const { theme, setTheme } = useTheme()
  
  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      Toggle Theme
    </button>
  )
}
```

---

## 📱 Icons

Import from Lucide React:
```tsx
import { Mail, CheckSquare, Calendar, Bell, Settings } from 'lucide-react'

<Mail className="h-5 w-5" />
<CheckSquare className="h-4 w-4 text-muted-foreground" />
```

Browse all icons: https://lucide.dev/icons/

---

## 🎨 Color Variables

Use in className:
```tsx
className="bg-primary text-primary-foreground"
className="bg-secondary text-secondary-foreground"
className="bg-muted text-muted-foreground"
className="bg-accent text-accent-foreground"
className="bg-card text-card-foreground"
className="border-border"
```

---

## 🔥 Hot Tips

### Client vs Server Components
```tsx
// Server Component (default) - faster, can't use hooks
export default function ServerComponent() {
  return <div>Static content</div>
}

// Client Component - interactive, uses hooks
'use client'

export default function ClientComponent() {
  const [state, setState] = useState()
  return <div>Interactive</div>
}
```

### Loading States
```tsx
const [loading, setLoading] = useState(false)

<Button disabled={loading}>
  {loading ? 'Loading...' : 'Submit'}
</Button>
```

### Conditional Classes
```tsx
import { clsx } from 'clsx'

<div className={clsx(
  'base-class',
  isActive && 'active-class',
  'another-class'
)} />
```

---

## 🐛 Troubleshooting

### Port already in use
```powershell
npm run dev -- -p 3001
```

### Clear cache
```powershell
rm -rf .next node_modules
npm install
```

### Type errors
```powershell
npm run type-check
```

### Linting
```powershell
npm run lint
```

---

## 📚 Documentation Links

- **Next.js**: https://nextjs.org/docs
- **Tailwind**: https://tailwindcss.com/docs
- **Lucide Icons**: https://lucide.dev
- **TypeScript**: https://typescriptlang.org/docs
- **React**: https://react.dev

---

## 🆘 Need Help?

1. Check [`README.md`](README.md) - full documentation
2. See [`SETUP.md`](SETUP.md) - installation guide
3. Review [`DESIGN.md`](DESIGN.md) - design system
4. Read [`COMPARISON.md`](COMPARISON.md) - vs Streamlit

---

**Keep this file handy for quick lookups! 🎯**
