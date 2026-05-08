'use client'

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/lib/store'
import { userAPI } from '@/lib/api'
import Cookie from 'js-cookie'

export function Providers({ children }: { children: React.ReactNode }) {
    const setUser = useAuthStore((state) => state.setUser)
    const setToken = useAuthStore((state) => state.setToken)
    const [isInitializing, setIsInitializing] = useState(true)

    useEffect(() => {
        const initializeAuth = async () => {
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

                // If we have a token, fetch user data
                if (token) {
                    try {
                        const user = await userAPI.getMe()
                        setUser(user)
                        setToken(token)
                    } catch (error) {
                        console.error('Failed to fetch user:', error)
                        // Token is invalid, clear it
                        Cookie.remove('token')
                        setToken(null)
                        setUser(null)
                    }
                }
            } finally {
                // Mark initialization as complete
                setIsInitializing(false)
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
