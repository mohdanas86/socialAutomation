'use client'

import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/lib/store'
import { userAPI } from '@/lib/api'
import Cookie from 'js-cookie'

export function Providers({ children }: { children: React.ReactNode }) {
    const setUser = useAuthStore((state) => state.setUser)
    const setToken = useAuthStore((state) => state.setToken)
    const setInitialized = useAuthStore((state) => state.setInitialized)
    const [isInitializing, setIsInitializing] = useState(true)
    const hasInitializedRef = useRef(false)
    const USER_CACHE_KEY = 'auth_user_cache'
    const USER_CACHE_TTL_MS = 5 * 60 * 1000

    useEffect(() => {
        const initializeAuth = async () => {
            if (hasInitializedRef.current) return
            hasInitializedRef.current = true

            try {
                // Check for token in URL (from OAuth callback)
                const params = new URLSearchParams(window.location.search)
                const tokenFromUrl = params.get('token')

                // Token priority: URL > Cookie > Store
                let token = tokenFromUrl || Cookie.get('token') || useAuthStore.getState().token

                if (tokenFromUrl) {
                    // Store token in cookie and state
                    Cookie.set('token', tokenFromUrl, { expires: 7 })
                    setToken(tokenFromUrl)
                    token = tokenFromUrl

                    // Remove token from URL (clean history)
                    window.history.replaceState({}, document.title, window.location.pathname)
                }

                // Try to hydrate user from cache first
                const cached = localStorage.getItem(USER_CACHE_KEY)
                let cachedUser: any = null
                let cachedAt = 0
                if (cached) {
                    try {
                        const parsed = JSON.parse(cached)
                        cachedUser = parsed.user || null
                        cachedAt = parsed.savedAt || 0
                    } catch (error) {
                        localStorage.removeItem(USER_CACHE_KEY)
                    }
                }

                const cacheIsFresh = cachedUser && Date.now() - cachedAt < USER_CACHE_TTL_MS

                if (token && cacheIsFresh) {
                    setUser(cachedUser)
                    setToken(token)
                }

                // If we have a token, fetch user data (skip if cache is fresh)
                if (token) {
                    try {
                        if (!cacheIsFresh) {
                            const user = await userAPI.getMe()
                            setUser(user)
                            setToken(token)
                            localStorage.setItem(
                                USER_CACHE_KEY,
                                JSON.stringify({ user, savedAt: Date.now() })
                            )
                        }
                    } catch (error) {
                        console.error('Failed to fetch user:', error)
                        // Token is invalid, clear it
                        Cookie.remove('token')
                        localStorage.removeItem(USER_CACHE_KEY)
                        setToken(null)
                        setUser(null)
                    }
                }
            } finally {
                setIsInitializing(false)
                setInitialized(true)  // Signal to all pages: auth is resolved
            }
        }

        initializeAuth()
    }, [setUser, setToken])

    // Don't render children until auth is initialized
    // This prevents premature redirects
    if (isInitializing) {
        return null
    }

    return <>{children}</>
}
