'use client'

import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function Home() {
  const router = useRouter()
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    if (user) {
      router.push('/dashboard')
    }
  }, [user, router])

  if (user) return null

  return (
    <main className="min-h-screen relative overflow-hidden bg-[#0b0f1a] text-white">
      <div className="absolute -top-24 -left-24 h-72 w-72 rounded-full bg-fuchsia-500/30 blur-3xl" />
      <div className="absolute top-1/2 -right-24 h-80 w-80 rounded-full bg-cyan-400/30 blur-3xl" />
      <div className="absolute bottom-0 left-1/3 h-64 w-64 rounded-full bg-emerald-400/20 blur-3xl" />

      <div className="relative mx-auto max-w-6xl px-6 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1 text-xs uppercase tracking-widest text-white/80">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Auto-post. Zero chaos.
          </div>

          <h1 className="mt-6 text-4xl sm:text-6xl font-extrabold tracking-tight">
            Social Automation,
            <span className="block bg-gradient-to-r from-cyan-300 via-fuchsia-300 to-emerald-300 bg-clip-text text-transparent">
              but make it effortless
            </span>
          </h1>

          <p className="mt-4 text-base sm:text-lg text-white/70">
            Schedule, publish, and track LinkedIn posts with a clean, fast dashboard
            that feels like a cheat code for creators.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <Link href="/login">
              <Button className="w-full rounded-full bg-white text-black hover:bg-white/90 font-semibold h-12 px-6 text-base">
                Login with LinkedIn
              </Button>
            </Link>

            <a href="https://github.com/mohdanas86" target="_blank" rel="noopener noreferrer">
              <Button className="w-full rounded-full border border-white/20 bg-transparent text-white hover:bg-white/10 font-semibold h-12 px-6 text-base">
                View on GitHub
              </Button>
            </a>
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3 text-xs text-white/60">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">OpenID Connect</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Post Scheduler</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Retry Logic</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Analytics Ready</span>
          </div>
        </div>
      </div>
    </main>
  )
}
