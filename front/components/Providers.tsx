'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/store'
import { userAPI } from '@/lib/api'
import Cookie from 'js-cookie'

export function Providers({ children }: { children: React.ReactNode }) {
    const setUser = useAuthStore((state) => state.setUser)
    const setToken = useAuthStore((state) => state.setToken)

    useEffect(() => {
        // Check for token in URL (from OAuth callback)
        const params = new URLSearchParams(window.location.search)
        const token = params.get('token')

        if (token) {
            // Store token in cookie and state
            Cookie.set('token', token, { expires: 7 })
            setToken(token)
            // Remove token from URL
            window.history.replaceState({}, document.title, window.location.pathname)
        }

        // Fetch user if token exists
        const storedToken =
            token || Cookie.get('token') || useAuthStore.getState().token
        if (storedToken) {
            setToken(storedToken)
            userAPI
                .getMe()
                .then((user) => {
                    setUser(user)
                })
                .catch(() => {
                    Cookie.remove('token')
                    setToken(null)
                })
        }
    }, [setUser, setToken])

    return <>{children}</>
}
