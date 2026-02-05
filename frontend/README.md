# AWOA Frontend - Next.js

A truly exceptional, modern frontend for the Autonomous Workplace Operations Assistant (AWOA) built with Next.js 14, React, TypeScript, and Tailwind CSS.

## ✨ Features

- **Modern Tech Stack**: Next.js 14 with App Router, React 18, TypeScript
- **Professional Design**: Beautiful UI with Tailwind CSS and custom design system
- **Light/Dark Mode**: Seamless theme switching with `next-themes`
- **Responsive Layout**: Mobile-first design that works on all devices
- **Type-Safe**: Full TypeScript coverage for better developer experience
- **Performance**: Optimized with React Server Components and SWR for data fetching
- **Professional Typography**: Inter font with optimized rendering

## 🎨 Design Highlights

- **Exceptional UI/UX**: Clean, modern interface inspired by professional SaaS products
- **Theme System**: Comprehensive color palette that works perfectly in both light and dark modes
- **Component Library**: Reusable Card, Button, Badge components with variants
- **Smooth Transitions**: Thoughtful animations and transitions throughout
- **Accessibility**: Focus states, ARIA labels, keyboard navigation
- **Professional Typography**: Optimized font rendering with proper spacing and hierarchy

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Dashboard
│   │   ├── mail/              # Email management
│   │   ├── tasks/             # Task tracking
│   │   ├── calendar/          # Meeting scheduler
│   │   ├── assistant/         # AI chat interface
│   │   ├── notifications/     # Notification center
│   │   ├── reports/           # Analytics
│   │   ├── wellness/          # Wellbeing features
│   │   └── activity/          # Agent monitoring
│   ├── components/
│   │   ├── layout/            # Layout components
│   │   ├── ui/                # Reusable UI components
│   │   ├── theme-provider.tsx # Theme context
│   │   └── theme-toggle.tsx   # Dark mode toggle
│   └── lib/
│       └── api.ts             # Backend API integration
├── public/                     # Static assets
├── tailwind.config.ts         # Tailwind configuration
├── next.config.js             # Next.js configuration
└── package.json               # Dependencies
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Python backend running (optional - uses mock data as fallback)

### Installation

1. **Navigate to frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install dependencies**:
   ```powershell
   npm install
   ```

3. **Start development server**:
   ```powershell
   npm run dev
   ```

4. **Open in browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

### Development Commands

```powershell
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint

# Type check
npm run type-check
```

## 🔌 Backend Integration

The frontend is designed to work with your existing Python backend. Configure the API endpoint:

1. **Create `.env.local`**:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **API Routes**: The frontend expects these endpoints (falls back to mock data if unavailable):
   - `GET /api/emails` - Fetch emails
   - `GET /api/tasks` - Fetch tasks
   - `GET /api/meetings` - Fetch meetings

3. **Proxy Configuration**: The `next.config.js` includes a proxy to avoid CORS issues:
   ```javascript
   // Requests to /api/backend/* are proxied to Python backend
   http://localhost:3000/api/backend/emails → http://localhost:8000/emails
   ```

## 🎨 Customization

### Theme Colors

Edit color palette in [tailwind.config.ts](tailwind.config.ts):

```typescript
colors: {
  primary: 'hsl(221.2 83.2% 53.3%)',  // Your brand color
  // ... more colors
}
```

### Typography

Change fonts in [src/app/layout.tsx](src/app/layout.tsx):

```typescript
import { YourFont } from 'next/font/google'
```

### Components

All UI components are in [src/components/ui/](src/components/ui/) and can be customized:
- `card.tsx` - Card layouts
- `button.tsx` - Button variants
- `badge.tsx` - Status badges

## 📱 Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Overview with stats and activity |
| Mail | `/mail` | Outlook-style email client |
| Tasks | `/tasks` | Kanban-style task management |
| Calendar | `/calendar` | Timeline view of meetings |
| Assistant | `/assistant` | AI chat interface |
| Notifications | `/notifications` | Alert center |
| Reports | `/reports` | Analytics (coming soon) |
| Wellness | `/wellness` | Wellbeing tracking (coming soon) |
| Activity | `/activity` | Agent monitoring (coming soon) |

## 🛠 Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 3.4
- **Icons**: Lucide React
- **Theme**: next-themes
- **Date Handling**: date-fns
- **Data Fetching**: SWR
- **Utilities**: clsx

## 🔥 Key Features

### Light/Dark Mode
Perfect theme switching with system preference detection:
- Seamless transitions between themes
- Persistent user preference
- System theme sync
- Custom color palette for both modes

### Professional Design
- Modern glassmorphism effects
- Smooth hover states and transitions
- Consistent spacing and typography
- Professional color palette
- Accessible contrast ratios

### Responsive Layout
- Mobile-first approach
- Sidebar navigation collapses on mobile
- Touch-friendly interactive elements
- Optimized for all screen sizes

## 🚢 Deployment

### Vercel (Recommended)

1. **Push to GitHub**
2. **Import to Vercel**: [vercel.com/new](https://vercel.com/new)
3. **Configure**:
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `.next`
4. **Set Environment Variables**: `NEXT_PUBLIC_API_URL`

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Build Locally

```powershell
npm run build
npm start
```

## 🔄 Migration from Streamlit

This frontend replaces your Streamlit app with:

1. **Better Performance**: Static generation + client-side rendering
2. **Full Control**: Custom UI/UX without Streamlit limitations
3. **Modern Stack**: Industry-standard React/Next.js
4. **Scalability**: Easy to add features and pages
5. **SEO**: Server-side rendering support
6. **Deploy Anywhere**: Vercel, Netlify, AWS, Azure, etc.

### Keeping Python Backend

Your existing Python agents, orchestration, and data logic remain unchanged:
- Frontend consumes REST APIs from Python
- All business logic stays in Python
- Agents work exactly as before
- Just add FastAPI/Flask endpoints if needed

## 📚 Learn More

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/)
- [React](https://react.dev/)

## 🤝 Contributing

This frontend is designed to be extended. Add new pages by:

1. Create `src/app/your-page/page.tsx`
2. Add route to navigation in `src/components/layout/main-layout.tsx`
3. Create API functions in `src/lib/api.ts`

## 📄 License

Part of the AWOA project. See main project LICENSE.

---

**Built with ❤️ using Next.js 14, React, and Tailwind CSS**
