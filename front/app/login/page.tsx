'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import Cookie from 'js-cookie'
import { useAuthStore } from '@/lib/store'

export default function LoginPage() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const hasRun = useRef(false)

    useEffect(() => {
        // If user is already authenticated (Providers already resolved them), go to dashboard
        if (user) {
            router.replace('/dashboard')
            return
        }

        // Only run the OAuth redirect once — not on every re-render
        if (hasRun.current) return
        hasRun.current = true

        const startOAuth = async () => {
            try {
                // Check cookie — if token exists, Providers will have set the user
                // Wait briefly in case Providers is still resolving
                const cookieToken = Cookie.get('token')
                if (cookieToken) {
                    router.replace('/dashboard')
                    return
                }

                // No token at all → start OAuth flow
                const { url } = await authAPI.getLoginUrl()
                window.location.href = url
            } catch {
                alert('Failed to start login. Please try again.')
            }
        }

        startOAuth()
    }, [user]) // Only re-run if the user object changes, NOT on token changes
    // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="min-h-screen bg-[#0b0f1a] flex items-center justify-center px-4">
            <div className="flex flex-col items-center gap-4 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 border border-primary/25">
                    <svg className="h-7 w-7 text-primary" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                    </svg>
                </div>
                <div>
                    <h1 className="text-lg font-semibold text-white">Connecting to LinkedIn</h1>
                    <p className="text-sm text-white/50 mt-1">Redirecting you to sign in…</p>
                </div>
                <LoadingSpinner message="" />
            </div>
        </div>
    )
}
