'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, usePostStore } from '@/lib/store'
import { postAPI } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import Link from 'next/link'

export default function DashboardPage() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const posts = usePostStore((state) => state.posts)
    const setPosts = usePostStore((state) => state.setPosts)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        if (!user) {
            router.push('/login')
            return
        }

        const fetchPosts = async () => {
            try {
                const data = await postAPI.list()
                setPosts(data.posts || [])
            } catch (error) {
                console.error('Failed to fetch posts')
            } finally {
                setIsLoading(false)
            }
        }

        fetchPosts()
    }, [user, router, setPosts])

    if (!user || isLoading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <LoadingSpinner message="Loading dashboard..." />
            </div>
        )
    }

    const postedCount = posts.filter((p) => p.status === 'posted').length
    const scheduledCount = posts.filter(
        (p) => p.status === 'scheduled'
    ).length
    const failedCount = posts.filter((p) => p.status === 'failed').length

    return (
        <main className="max-w-6xl mx-auto px-4 py-8">
            <div className="mb-8">
                <h1 className="text-4xl font-bold text-gray-900 mb-2">
                    Welcome, {user.name}!
                </h1>
                <p className="text-gray-600">Manage your automated LinkedIn posts</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-gray-600 font-medium">Posted</p>
                    <p className="text-3xl font-bold text-green-600">{postedCount}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-gray-600 font-medium">Scheduled</p>
                    <p className="text-3xl font-bold text-blue-600">
                        {scheduledCount}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-gray-600 font-medium">Failed</p>
                    <p className="text-3xl font-bold text-red-600">{failedCount}</p>
                </div>
            </div>

            {/* Quick Actions */}
            <div className="mb-8">
                <Link
                    href="/dashboard/create"
                    className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-medium"
                >
                    Create New Post
                </Link>
            </div>

            {/* Recent Posts */}
            <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                    Recent Posts
                </h2>

                {posts.length === 0 ? (
                    <p className="text-gray-600 text-center py-8">
                        No posts yet. Start by creating one!
                    </p>
                ) : (
                    <div className="space-y-4">
                        {posts.slice(0, 5).map((post) => (
                            <div
                                key={post._id}
                                className="border-l-4 border-blue-600 pl-4 py-2"
                            >
                                <div className="flex justify-between items-start">
                                    <p className="text-gray-800 line-clamp-2">
                                        {post.content}
                                    </p>
                                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                        {post.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                <Link
                    href="/dashboard/posts"
                    className="inline-block mt-4 text-blue-600 hover:text-blue-700 font-medium"
                >
                    View All Posts →
                </Link>
            </div>
        </main>
    )
}
