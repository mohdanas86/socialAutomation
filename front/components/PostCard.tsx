'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { postAPI } from '@/lib/api'
import { usePostStore } from '@/lib/store'

interface PostCardProps {
    post: any
}

export function PostCard({ post }: PostCardProps) {
    const [isLoading, setIsLoading] = useState(false)
    const deletePost = usePostStore((state) => state.deletePost)
    const updatePost = usePostStore((state) => state.updatePost)

    const handleDelete = async () => {
        if (!confirm('Delete this post?')) return

        setIsLoading(true)
        try {
            await postAPI.delete(post._id)
            deletePost(post._id)
        } catch (error) {
            alert('Failed to delete post')
        } finally {
            setIsLoading(false)
        }
    }

    const handleRetry = async () => {
        setIsLoading(true)
        try {
            const updated = await postAPI.retry(post._id)
            updatePost(post._id, updated)
        } catch (error) {
            alert('Failed to retry post')
        } finally {
            setIsLoading(false)
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'posted':
                return 'bg-green-100 text-green-800'
            case 'scheduled':
                return 'bg-blue-100 text-blue-800'
            case 'failed':
                return 'bg-red-100 text-red-800'
            case 'draft':
                return 'bg-gray-100 text-gray-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    return (
        <div className="border rounded-lg p-4 bg-white shadow-sm">
            <div className="flex justify-between items-start mb-2">
                <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(post.status)}`}
                >
                    {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
                </span>
                <span className="text-sm text-gray-500">
                    {formatDistanceToNow(new Date(post.created_at), {
                        addSuffix: true,
                    })}
                </span>
            </div>

            <p className="text-gray-800 mb-4 line-clamp-3">{post.content}</p>

            {post.scheduled_time && (
                <p className="text-sm text-gray-600 mb-4">
                    Scheduled:{' '}
                    {new Date(post.scheduled_time).toLocaleString()}
                </p>
            )}

            <div className="flex gap-2">
                {post.status === 'failed' && (
                    <button
                        onClick={handleRetry}
                        disabled={isLoading}
                        className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                    >
                        Retry
                    </button>
                )}

                {post.status !== 'posted' && (
                    <button
                        onClick={handleDelete}
                        disabled={isLoading}
                        className="text-sm bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 disabled:opacity-50"
                    >
                        Delete
                    </button>
                )}

                {post.status === 'posted' && (
                    <button
                        disabled
                        className="text-sm bg-gray-300 text-gray-700 px-3 py-1 rounded cursor-not-allowed"
                    >
                        Posted
                    </button>
                )}
            </div>
        </div>
    )
}
