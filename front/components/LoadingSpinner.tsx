'use client'

export function LoadingSpinner({ message }: { message?: string }) {
    return (
        <div className="flex flex-col items-center justify-center gap-4">
            <div className="w-12 h-12 border-4 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
            {message && <p className="text-gray-600">{message}</p>}
        </div>
    )
}
