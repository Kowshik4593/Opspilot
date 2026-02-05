# AWOA Frontend - Quick Setup Guide

## 🎯 Installation Steps

### Step 1: Install Node.js

1. **Download Node.js**: Visit [nodejs.org](https://nodejs.org/)
   - Download the **LTS version** (recommended: v18 or v20)
   - Choose the Windows installer (.msi)

2. **Run the installer**:
   - Accept the license agreement
   - Keep default installation path
   - ✅ Check "Automatically install necessary tools"
   - Click Install

3. **Verify installation**:
   ```powershell
   node --version    # Should show v18.x.x or v20.x.x
   npm --version     # Should show 9.x.x or 10.x.x
   ```

### Step 2: Install Frontend Dependencies

```powershell
# Navigate to frontend directory
cd C:\Users\306589\Documents\T1\frontend

# Install all dependencies (takes 1-2 minutes)
npm install
```

### Step 3: Start Development Server

```powershell
# Start the Next.js dev server
npm run dev
```

You should see:
```
   ▲ Next.js 14.1.0
   - Local:        http://localhost:3000
   - Ready in 2.3s
```

### Step 4: Open in Browser

Navigate to: **http://localhost:3000**

You'll see the AWOA dashboard with:
- ✅ Beautiful light/dark mode toggle
- ✅ Professional navigation sidebar
- ✅ Dashboard with stats
- ✅ Mail, Tasks, Calendar pages
- ✅ AI Assistant chat interface

---

## 🚀 Quick Commands

```powershell
# Development (with hot reload)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Type checking
npm run type-check

# Linting
npm run lint
```

---

## 🎨 What You Get

### Pages Built
- **Dashboard** (`/`) - Overview with activity feed
- **Mail** (`/mail`) - Outlook-style email client with filters
- **Tasks** (`/tasks`) - Kanban board with priority badges
- **Calendar** (`/calendar`) - Timeline view of meetings
- **Assistant** (`/assistant`) - AI chat interface
- **Notifications** (`/notifications`) - Alert center
- **Reports, Wellness, Activity** - Placeholder pages ready to build

### Features Included
- ✨ **Light/Dark Mode** - Perfect theme switching
- 🎨 **Professional Design** - Modern SaaS-quality UI
- 📱 **Responsive** - Works on desktop, tablet, mobile
- ⚡ **Fast** - Next.js optimizations + React Server Components
- 🔒 **Type-Safe** - Full TypeScript coverage
- ♿ **Accessible** - ARIA labels, keyboard navigation
- 🎯 **Production-Ready** - Deploy to Vercel in 2 minutes

---

## 🔌 Connecting to Python Backend

### Option 1: Use Mock Data (Default)
The frontend works immediately with realistic mock data. No backend needed for development!

### Option 2: Connect to Real Backend

1. **Create `.env.local`**:
   ```powershell
   cd C:\Users\306589\Documents\T1\frontend
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

2. **Start your Python backend** (in another terminal):
   ```powershell
   cd C:\Users\306589\Documents\T1
   .venv\Scripts\Activate.ps1
   # Start your FastAPI/Flask server on port 8000
   ```

3. **Restart Next.js**:
   ```powershell
   npm run dev
   ```

The frontend will automatically try to fetch from your backend and fall back to mock data if unavailable.

---

## 📦 What Was Created

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout with theme
│   │   ├── page.tsx                # Dashboard
│   │   ├── globals.css             # Tailwind + custom styles
│   │   ├── mail/page.tsx           # Email client
│   │   ├── tasks/page.tsx          # Task manager
│   │   ├── calendar/page.tsx       # Meeting scheduler
│   │   ├── assistant/page.tsx      # AI chat
│   │   ├── notifications/page.tsx  # Alert center
│   │   └── [reports|wellness|activity]/page.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   └── main-layout.tsx     # Navigation + header
│   │   ├── ui/
│   │   │   ├── card.tsx            # Reusable cards
│   │   │   ├── button.tsx          # Button variants
│   │   │   └── badge.tsx           # Status badges
│   │   ├── theme-provider.tsx      # Theme context
│   │   └── theme-toggle.tsx        # Dark mode button
│   └── lib/
│       └── api.ts                  # Backend integration + mocks
├── public/                          # Static assets
├── tailwind.config.ts              # Design system config
├── next.config.js                  # Next.js settings
├── tsconfig.json                   # TypeScript config
├── package.json                    # Dependencies
├── README.md                       # Full documentation
└── .env.example                    # Environment template
```

---

## 🎯 Next Steps

1. **Customize Colors**: Edit `tailwind.config.ts` to match your brand
2. **Add Logo**: Place logo in `public/` and update header
3. **Connect Backend**: Wire up real API endpoints
4. **Deploy**: Push to GitHub → Import to Vercel → Done!

---

## 🆘 Troubleshooting

### Port 3000 already in use
```powershell
# Use different port
npm run dev -- -p 3001
```

### Dependencies failing to install
```powershell
# Clear cache and reinstall
npm cache clean --force
rm -rf node_modules
npm install
```

### Dark mode not working
- Clear browser cache
- Check if theme toggle button is visible in header
- Inspect `<html>` element - should have `class="dark"` when enabled

---

## 📚 Tech Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **next-themes** - Theme switching
- **Lucide React** - Beautiful icons
- **date-fns** - Date formatting
- **SWR** - Data fetching

---

**Need help?** Check [README.md](README.md) for detailed docs or ask in the project chat!
