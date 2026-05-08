'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, usePostStore } from '@/lib/store'
import { postAPI } from '@/lib/api'
import { PostCard } from '@/components/PostCard'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function PostsPage() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const posts = usePostStore((state) => state.posts)
    const setPosts = usePostStore((state) => state.setPosts)
    const [isLoading, setIsLoading] = useState(true)
    const [status, setStatus] = useState<string>('all')

    useEffect(() => {
        if (!user) {
            router.push('/login')
            return
        }

        const fetchPosts = async () => {
            try {
                const data = await postAPI.list({
                    status: status !== 'all' ? status : undefined,
                })
                setPosts(data.posts || [])
            } catch (error) {
                console.error('Failed to fetch posts')
            } finally {
                setIsLoading(false)
            }
        }

        fetchPosts()
    }, [user, router, status, setPosts])

    if (!user || isLoading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <LoadingSpinner message="Loading posts..." />
            </div>
        )
    }

    const statuses = ['all', 'scheduled', 'posted', 'failed', 'draft']

    return (
        <main className="max-w-6xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Your Posts</h1>

            {/* Status Filters */}
            <div className="flex gap-2 mb-8 flex-wrap">
                {statuses.map((s) => (
                    <button
                        key={s}
                        onClick={() => setStatus(s)}
                        className={`px-4 py-2 rounded-lg font-medium transition ${
                            status === s
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
                        }`}
                    >
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                    </button>
                ))}
            </div>

            {/* Posts Grid */}
            {posts.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-gray-600 text-lg">No posts found</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {posts.map((post) => (
                        <PostCard key={post._id} post={post} />
                    ))}
                </div>
            )}
        </main>
    )
}
