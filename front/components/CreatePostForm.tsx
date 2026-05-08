'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { postAPI } from '@/lib/api'
import { usePostStore } from '@/lib/store'

export function CreatePostForm() {
    const router = useRouter()
    const [content, setContent] = useState('')
    const [scheduledTime, setScheduledTime] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)
    const addPost = usePostStore((state) => state.addPost)

    const charCount = content.length
    const maxChars = 3000
    const isValid = content.length >= 5 && content.length <= 3000

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setSuccess(false)

        if (!isValid) {
            setError('Post must be between 5 and 3000 characters')
            return
        }

        setIsLoading(true)

        try {
            const post = await postAPI.create({
                content,
                scheduled_time: scheduledTime || undefined,
            })

            addPost(post)
            setSuccess(true)
            setContent('')
            setScheduledTime('')

            setTimeout(() => {
                router.push('/dashboard/posts')
            }, 1500)
        } catch (err: any) {
            setError(
                err.response?.data?.detail || 'Failed to create post'
            )
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-4">
            {error && (
                <div className="bg-red-100 text-red-800 p-4 rounded">
                    {error}
                </div>
            )}

            {success && (
                <div className="bg-green-100 text-green-800 p-4 rounded">
                    Post created successfully! Redirecting...
                </div>
            )}

            <div>
                <label className="block text-sm font-medium mb-2">
                    Post Content
                </label>
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="What's on your mind?"
                    className="w-full border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    rows={8}
                    disabled={isLoading}
                />
                <div className="text-right text-sm text-gray-500 mt-2">
                    {charCount} / {maxChars}
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium mb-2">
                    Schedule Time (Optional)
                </label>
                <input
                    type="datetime-local"
                    value={scheduledTime}
                    onChange={(e) => setScheduledTime(e.target.value)}
                    className="w-full border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    disabled={isLoading}
                />
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
                <p className="font-medium text-blue-900 mb-2">Tips for Great Posts:</p>
                <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Keep it between 5 and 3000 characters</li>
                    <li>• Use proper capitalization (avoid ALL CAPS)</li>
                    <li>• Include 1-3 URLs maximum</li>
                    <li>• Engage your audience with questions</li>
                    <li>• Add hashtags to increase reach</li>
                </ul>
            </div>

            <button
                type="submit"
                disabled={!isValid || isLoading}
                className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
                {isLoading ? 'Creating...' : 'Create Post'}
            </button>
        </form>
    )
}
