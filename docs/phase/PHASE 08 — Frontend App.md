# PHASE 08 — Frontend App Shell, Landing Page & Mode Selection

## Phase Goal
Build the complete Next.js 14 frontend shell: global layout, navigation, landing page, and the critical Mode Selection screen. This is the first screen users see after landing. Everything depends on getting this UX right — it must feel like a career tool, not a form.

---

## Features Implemented
- Root layout with font, metadata, React Query provider, Toaster
- Public landing page (hero, how it works, outputs showcase)
- Dashboard layout with sidebar navigation
- Mode selection screen: "Instant Post" vs "Growth Automation"
- Theme: dark/light mode toggle (next-themes)
- Responsive mobile layout
- Loading skeletons

---

## Technical Architecture

```
src/
├── app/
│   ├── layout.tsx                    ← Root layout (providers, font, metadata)
│   ├── page.tsx                      ← Landing page
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── dashboard/
│       ├── layout.tsx                ← Dashboard layout (sidebar + topbar)
│       ├── page.tsx                  ← Mode selection (home)
│       ├── instant/
│       │   └── page.tsx              ← Instant Post flow
│       ├── schedule/
│       │   └── page.tsx              ← Growth Automation flow
│       ├── workspace/
│       │   └── page.tsx              ← All generated posts
│       └── settings/
│           └── page.tsx              ← LinkedIn connection, account
├── components/
│   ├── ui/                           ← Shadcn components
│   ├── shared/
│   │   ├── Navbar.tsx
│   │   ├── Sidebar.tsx
│   │   ├── ProtectedRoute.tsx
│   │   ├── ThemeToggle.tsx
│   │   └── LoadingSkeleton.tsx
│   └── landing/
│       ├── Hero.tsx
│       ├── HowItWorks.tsx
│       └── OutputShowcase.tsx
├── providers/
│   └── Providers.tsx                 ← ReactQuery + ThemeProvider
└── store/
    └── auth.ts
```

---

## Root Layout (`src/app/layout.tsx`)
```tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from '@/providers/Providers';
import { Toaster } from '@/components/ui/toaster';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Career Visibility Platform | Turn Projects Into Opportunities',
  description: 'Generate recruiter-friendly LinkedIn posts, resume bullets, and portfolio content from your GitHub projects using AI.',
  keywords: 'LinkedIn post generator, student career, AI content, GitHub to LinkedIn',
  openGraph: {
    title: 'AI Career Visibility Platform',
    description: 'Turn your projects into internship opportunities.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
```

---

## Providers (`src/providers/Providers.tsx`)
```tsx
'use client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { useState } from 'react';

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

---

## Landing Page (`src/app/page.tsx`)
```tsx
import Hero from '@/components/landing/Hero';
import HowItWorks from '@/components/landing/HowItWorks';
import OutputShowcase from '@/components/landing/OutputShowcase';
import Navbar from '@/components/shared/Navbar';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <OutputShowcase />

        {/* Final CTA */}
        <section className="py-24 text-center bg-primary/5">
          <h2 className="text-3xl font-bold mb-4">
            Ready to get noticed by recruiters?
          </h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Join thousands of students turning their GitHub projects into career opportunities.
          </p>
          <Link href="/register">
            <Button size="lg" className="px-10">
              Get Started Free →
            </Button>
          </Link>
        </section>
      </main>
    </div>
  );
}
```

## Hero Component (`src/components/landing/Hero.tsx`)
```tsx
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Zap, Calendar } from 'lucide-react';

export default function Hero() {
  return (
    <section className="min-h-[90vh] flex flex-col items-center justify-center text-center px-4 py-20">
      <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-1.5 rounded-full text-sm font-medium mb-6">
        ✨ AI-Powered Career Visibility for Students
      </div>

      <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight max-w-3xl mb-6 leading-tight">
        Turn Your Projects Into{' '}
        <span className="text-primary">Internship Opportunities</span>
      </h1>

      <p className="text-xl text-muted-foreground max-w-2xl mb-10">
        Paste your GitHub link. Get a recruiter-ready LinkedIn post, resume bullet,
        and portfolio summary — powered by AI that actually understands your work.
      </p>

      {/* Primary CTAs */}
      <div className="flex flex-col sm:flex-row gap-4 mb-16">
        <Link href="/dashboard">
          <Button size="lg" className="gap-2 px-8">
            <Zap className="w-5 h-5" />
            Generate Instant Post
          </Button>
        </Link>
        <Link href="/dashboard">
          <Button size="lg" variant="outline" className="gap-2 px-8">
            <Calendar className="w-5 h-5" />
            Plan Weekly Content
          </Button>
        </Link>
      </div>

      {/* Pain Points */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl text-sm text-muted-foreground">
        {[
          '😩 Built projects but nobody noticed?',
          '🤔 Don\'t know what to post on LinkedIn?',
          '📝 Struggling to explain your projects?',
          '🎯 Want internship visibility?',
        ].map(pain => (
          <div key={pain} className="bg-muted/40 rounded-lg p-4 text-left">
            {pain}
          </div>
        ))}
      </div>
    </section>
  );
}
```

## How It Works (`src/components/landing/HowItWorks.tsx`)
```tsx
import { GitBranch, Cpu, FileText, TrendingUp } from 'lucide-react';

const STEPS = [
  { icon: GitBranch, title: 'Paste Project / GitHub', desc: 'Share your project link or paste your README.' },
  { icon: Cpu, title: 'AI Understands Your Work', desc: 'Our AI analyzes impact, tech depth, and recruiter appeal.' },
  { icon: FileText, title: 'Generate Career Content', desc: 'Get LinkedIn post, resume bullet, and portfolio summary.' },
  { icon: TrendingUp, title: 'Post & Grow Professionally', desc: 'Publish instantly or schedule a week of content.' },
];

export default function HowItWorks() {
  return (
    <section className="py-24 px-4 bg-muted/30">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-4">How It Works</h2>
        <p className="text-center text-muted-foreground mb-16">From project to recruiter in under 30 seconds.</p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {STEPS.map((step, i) => (
            <div key={i} className="flex flex-col items-center text-center">
              <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
                <step.icon className="w-7 h-7 text-primary" />
              </div>
              <div className="text-xs text-muted-foreground mb-2">Step {i + 1}</div>
              <h3 className="font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

---

## Dashboard Layout (`src/app/dashboard/layout.tsx`)
```tsx
'use client';
import ProtectedRoute from '@/components/shared/ProtectedRoute';
import Sidebar from '@/components/shared/Sidebar';
import Topbar from '@/components/shared/Topbar';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-background overflow-hidden">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto p-6">
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
```

## Sidebar (`src/components/shared/Sidebar.tsx`)
```tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Zap, Calendar, LayoutGrid, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', icon: LayoutGrid, label: 'Home' },
  { href: '/dashboard/instant', icon: Zap, label: 'Instant Post' },
  { href: '/dashboard/schedule', icon: Calendar, label: 'Schedule' },
  { href: '/dashboard/workspace', icon: LayoutGrid, label: 'Workspace' },
  { href: '/dashboard/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r bg-background flex flex-col py-6 px-3 shrink-0">
      <div className="px-3 mb-8">
        <span className="font-bold text-lg text-primary">CareerAI</span>
      </div>
      <nav className="flex-1 space-y-1">
        {NAV_ITEMS.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              pathname === item.href
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

---

## Mode Selection Screen (`src/app/dashboard/page.tsx`)
```tsx
'use client';
import { useRouter } from 'next/navigation';
import { Zap, Calendar, ArrowRight } from 'lucide-react';
import { useAuthStore } from '@/store/auth';

const MODES = [
  {
    id: 'instant',
    icon: Zap,
    title: 'Instant Career Post',
    badge: 'Simple + Fast',
    description: 'Turn your project into a recruiter-friendly LinkedIn post instantly. Perfect for quick sharing.',
    features: ['LinkedIn post in 30 seconds', 'Resume bullet point', 'Portfolio summary'],
    cta: 'Start Instantly',
    href: '/dashboard/instant',
    accent: 'bg-amber-500/10 border-amber-500/20 text-amber-600',
    iconColor: 'text-amber-500',
  },
  {
    id: 'schedule',
    icon: Calendar,
    title: 'Growth Automation',
    badge: 'Advanced',
    description: 'Generate and schedule multiple LinkedIn posts automatically. Build your professional brand consistently.',
    features: ['Up to 20 posts generated', 'Auto-schedule & publish', 'Content calendar view'],
    cta: 'Build Schedule',
    href: '/dashboard/schedule',
    accent: 'bg-violet-500/10 border-violet-500/20 text-violet-600',
    iconColor: 'text-violet-500',
  },
];

export default function ModeSelectionPage() {
  const router = useRouter();
  const user = useAuthStore(s => s.user);

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">
          Welcome back{user?.name ? `, ${user.name.split(' ')[0]}` : ''} 👋
        </h1>
        <p className="text-muted-foreground text-lg">What do you want to do today?</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {MODES.map(mode => (
          <button
            key={mode.id}
            onClick={() => router.push(mode.href)}
            className="group text-left border-2 border-border hover:border-primary/40 rounded-2xl p-6 transition-all hover:shadow-lg hover:-translate-y-0.5 bg-card"
          >
            {/* Badge */}
            <span className={`inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full border mb-4 ${mode.accent}`}>
              {mode.badge}
            </span>

            {/* Icon */}
            <div className={`w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-4`}>
              <mode.icon className={`w-6 h-6 ${mode.iconColor}`} />
            </div>

            {/* Content */}
            <h2 className="text-xl font-bold mb-2">{mode.title}</h2>
            <p className="text-muted-foreground text-sm mb-4">{mode.description}</p>

            {/* Features */}
            <ul className="space-y-1.5 mb-6">
              {mode.features.map(f => (
                <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>

            {/* CTA */}
            <div className="flex items-center gap-2 font-semibold text-primary group-hover:gap-3 transition-all">
              {mode.cta}
              <ArrowRight className="w-4 h-4" />
            </div>
          </button>
        ))}
      </div>

      {/* Quick Stats */}
      <div className="mt-12 grid grid-cols-3 gap-4">
        {[
          { label: 'Posts Generated', value: '—' },
          { label: 'Posts Scheduled', value: '—' },
          { label: 'Published', value: '—' },
        ].map(stat => (
          <div key={stat.label} className="bg-muted/40 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold">{stat.value}</div>
            <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Topbar (`src/components/shared/Topbar.tsx`)
```tsx
'use client';
import { useAuthStore } from '@/store/auth';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import ThemeToggle from './ThemeToggle';
import { LogOut } from 'lucide-react';

export default function Topbar() {
  const { user, clearAuth } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    clearAuth();
    router.push('/login');
  };

  return (
    <header className="h-14 border-b flex items-center justify-between px-6 shrink-0">
      <div />
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <span className="text-sm text-muted-foreground hidden sm:block">
          {user?.email}
        </span>
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
}
```

## Theme Toggle (`src/components/shared/ThemeToggle.tsx`)
```tsx
'use client';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
    >
      {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </Button>
  );
}
```

---

## Navbar (`src/components/shared/Navbar.tsx`)
```tsx
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="font-bold text-xl text-primary">CareerAI</Link>
        <div className="flex items-center gap-3">
          <Link href="/login">
            <Button variant="ghost" size="sm">Sign In</Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get Started Free</Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}
```

---

## Backend Tasks
None in this phase — all frontend.

---

## Security Considerations
- `ProtectedRoute` wraps entire dashboard layout — no authenticated content leaks
- Landing page has no auth requirement — fully public

---

## Environment Variables
```env
# Add to frontend .env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=CareerAI
```

---

## Third-Party Packages to Install
```bash
cd frontend
npm install next-themes @tanstack/react-query
npx shadcn-ui@latest add button input textarea label select badge toaster
```

---

## Implementation Steps (Exact Order)

1. Install `next-themes` and `@tanstack/react-query`
2. Create `src/providers/Providers.tsx`
3. Update `src/app/layout.tsx` with metadata, font, Providers, Toaster
4. Create `src/components/shared/Navbar.tsx`
5. Create `src/components/landing/Hero.tsx`
6. Create `src/components/landing/HowItWorks.tsx`
7. Update `src/app/page.tsx` — landing page
8. Create `src/app/(auth)/login/page.tsx` and `register/page.tsx`
9. Create `src/components/shared/Sidebar.tsx`
10. Create `src/components/shared/Topbar.tsx`
11. Create `src/components/shared/ThemeToggle.tsx`
12. Create `src/app/dashboard/layout.tsx`
13. Create `src/app/dashboard/page.tsx` — Mode Selection screen
14. Test: visit `localhost:3000` → landing page renders
15. Test: visit `localhost:3000/dashboard` → redirects to login (ProtectedRoute)
16. Test: login → redirected to `/dashboard` → Mode Selection shows correctly
17. Test: click "Instant Post" → navigates to `/dashboard/instant`
18. Test: light/dark theme toggle works
19. Commit: `git commit -m "Phase 08: Frontend shell, landing page, mode selection"`

---

## Edge Cases
- User visits `/dashboard` with expired token → `ProtectedRoute` redirects to `/login`
- Theme flicker on load → `suppressHydrationWarning` on `<html>` handles it
- Mobile: Sidebar collapses to bottom nav bar on screens < 768px

---

## Deliverables / Checklist

- [ ] Landing page renders at `localhost:3000` with Hero, How It Works sections
- [ ] Navbar shows Sign In / Get Started
- [ ] Dashboard layout: Sidebar + Topbar renders correctly
- [ ] Mode Selection page: two cards (Instant Post + Growth Automation)
- [ ] Clicking mode card navigates to correct route
- [ ] `ProtectedRoute` redirects unauthenticated users to `/login`
- [ ] Theme toggle works (dark/light)
- [ ] Responsive layout on mobile
- [ ] React Query and ThemeProvider working
- [ ] Login / Register pages functional (from Phase 02)

---

## Definition of Completion
Landing page loads at `localhost:3000`. Authenticated user reaches `/dashboard` and sees the two-mode selection cards. Clicking either card navigates to the correct page. Unauthenticated access to `/dashboard` redirects to login. Light/dark mode toggle works.