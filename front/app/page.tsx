'use client'

import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { useEffect } from 'react'
import Link from 'next/link'

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
    <main className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Social Automation
        </h1>
        <p className="text-gray-600 mb-8">
          Automate your LinkedIn posts and manage your social presence
          effortlessly.
        </p>

        <div className="space-y-4">
          <Link
            href="/login"
            className="block w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 font-medium"
          >
            Login with LinkedIn
          </Link>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full bg-gray-200 text-gray-900 py-3 rounded-lg hover:bg-gray-300 font-medium"
          >
            View on GitHub
          </a>
        </div>
      </div>
    </main>
  )
}
