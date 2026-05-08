'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import Cookie from 'js-cookie'

export function Navbar() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const logout = useAuthStore((state) => state.logout)

    const handleLogout = () => {
        Cookie.remove('token')
        logout()
        router.push('/')
    }

    if (!user) return null

    return (
        <nav className="bg-white shadow">
            <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
                <Link href="/dashboard" className="font-bold text-lg">
                    Social Automation
                </Link>

                <div className="flex items-center gap-6">
                    <Link
                        href="/dashboard/posts"
                        className="hover:text-blue-600"
                    >
                        Posts
                    </Link>
                    <Link
                        href="/dashboard/create"
                        className="hover:text-blue-600"
                    >
                        Create Post
                    </Link>

                    <div className="flex items-center gap-4">
                        <div className="text-right">
                            <p className="font-medium">{user.name}</p>
                            <p className="text-sm text-gray-600">{user.email}</p>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                        >
                            Logout
                        </button>
                    </div>
                </div>
            </div>
        </nav>
    )
}
