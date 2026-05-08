'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { CreatePostForm } from '@/components/CreatePostForm'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function CreatePostPage() {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)

    useEffect(() => {
        if (!user) {
            router.push('/login')
        }
    }, [user, router])

    if (!user) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <LoadingSpinner message="Loading..." />
            </div>
        )
    }

    return (
        <main className="max-w-2xl mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-8">Create New Post</h1>
            <CreatePostForm />
        </main>
    )
}
