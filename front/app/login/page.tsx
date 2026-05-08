'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function LoginPage() {
    const router = useRouter()

    useEffect(() => {
        const startOAuth = async () => {
            try {
                const { url } = await authAPI.getLoginUrl()
                window.location.href = url
            } catch (error) {
                alert('Failed to start login. Please try again.')
            }
        }

        startOAuth()
    }, [router])

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center px-4">
            <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
                <h1 className="text-2xl font-bold text-gray-900 mb-4">
                    Redirecting...
                </h1>
                <LoadingSpinner message="Connecting to LinkedIn..." />
            </div>
        </div>
    )
}
