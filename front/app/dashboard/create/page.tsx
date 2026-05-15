'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { postAPI } from '@/lib/api'
import { usePostStore, useDashboardStatsStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
    SendIcon,
    ClockIcon,
    HashIcon,
    LightbulbIcon,
    CheckCircleIcon,
    AlertCircleIcon,
} from 'lucide-react'
import { DatePickerTime } from '@/components/date-picker-time'

const MAX_CHARS = 3000
const MIN_CHARS = 5

const TIPS = [
    'Keep it concise — posts under 1300 chars get the most reach',
    'Ask a question to drive comments',
    'Add 3–5 relevant hashtags at the end',
    'Use line breaks to improve readability',
    'Share a personal story or insight',
]

export default function CreatePostPage() {
    const router = useRouter()
    const addPost = usePostStore((s) => s.addPost)
    const invalidate = useDashboardStatsStore((s) => s.invalidate)

    const [content, setContent] = useState('')
    const [scheduledTime, setScheduledTime] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    const charCount = content.length
    const isValid = charCount >= MIN_CHARS && charCount <= MAX_CHARS

    /**
     * Convert local datetime-local value (YYYY-MM-DDTHH:mm) to UTC ISO.
     * new Date(localStr) already interprets the input in the browser's local timezone.
     */
    const localToIso = (localStr: string): string => {
        if (!localStr) return localStr
        const localDate = new Date(localStr)
        if (isNaN(localDate.getTime())) return localStr
        return localDate.toISOString()
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!isValid) return
        setError(null)
        setIsLoading(true)

        try {
            const isoTime = scheduledTime ? localToIso(scheduledTime) : undefined
            console.log(`[handleSubmit] Scheduled time (local): ${scheduledTime}`)
            console.log(`[handleSubmit] Scheduled time (UTC): ${isoTime}`)

            // Validate scheduled time is in the future using local interpretation.
            if (scheduledTime) {
                // Parse YYYY-MM-DDTHH:mm into a local Date (same logic as the date picker)
                const [datePart, timePart] = scheduledTime.split('T')
                let localScheduled: Date | null = null
                if (datePart && timePart) {
                    const [y, m, d] = datePart.split('-').map(Number)
                    const [hh, mm] = timePart.split(':').map(Number)
                    localScheduled = new Date(y, m - 1, d, hh, mm, 0, 0)
                }

                if (!localScheduled || isNaN(localScheduled.getTime())) {
                    setError('Invalid scheduled time format')
                    setIsLoading(false)
                    return
                }

                const now = new Date()
                const diffMs = localScheduled.getTime() - now.getTime()
                console.log(`[handleSubmit] Local scheduled: ${localScheduled.toString()} (diffMs=${diffMs})`)
                console.log(`[handleSubmit] UTC isoTime: ${isoTime}`)

                if (diffMs <= 0) {
                    setError('Scheduled time must be in the future')
                    setIsLoading(false)
                    return
                }
            }

            const post = await postAPI.create({
                content,
                // Convert local datetime-local input → UTC ISO string (with 'Z' suffix)
                scheduled_time: isoTime,
            })

            console.log(`[handleSubmit] Post created successfully:`, post)
            addPost(post)
            invalidate()   // bust the chart cache so it reflects the new post
            setSuccess(true)
            setTimeout(() => router.push('/dashboard/posts'), 1200)
        } catch (err: any) {
            console.error(`[handleSubmit] Error creating post:`, err)
            const errorMessage = err.response?.data?.detail || 'Failed to create post. Please try again.'
            setError(errorMessage)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="px-4 lg:px-6 max-w-3xl">
            {/* Page heading */}
            <div className="mb-6">
                <h2 className="text-xl font-semibold tracking-tight">Create Post</h2>
                <p className="text-sm text-muted-foreground mt-0.5">
                    Compose and schedule your LinkedIn content
                </p>
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
                {/* Compose card */}
                <Card className="border-border/50 bg-card/60 backdrop-blur-sm">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-base">Compose</CardTitle>
                        <CardDescription className="text-xs">
                            Write your LinkedIn post content below
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {/* Success */}
                            {success && (
                                <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
                                    <CheckCircleIcon className="h-4 w-4 shrink-0" />
                                    Post created! Redirecting to your posts…
                                </div>
                            )}

                            {/* Error */}
                            {error && (
                                <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
                                    <AlertCircleIcon className="h-4 w-4 shrink-0" />
                                    {error}
                                </div>
                            )}

                            {/* Content textarea */}
                            <div className="space-y-1.5">
                                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                    Post Content
                                </label>
                                <textarea
                                    value={content}
                                    onChange={(e) => setContent(e.target.value)}
                                    placeholder="What's on your mind? Share an insight, story, or update…"
                                    rows={10}
                                    disabled={isLoading || success}
                                    className="w-full resize-none rounded-lg border border-border/50 bg-muted/30 px-4 py-3 text-sm placeholder:text-muted-foreground/50 focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/30 disabled:opacity-60 transition-colors"
                                />
                                {/* Char counter */}
                                <div className="flex items-center justify-between text-[11px]">
                                    <span className={charCount > MAX_CHARS ? 'text-rose-400' : 'text-muted-foreground'}>
                                        {charCount < MIN_CHARS && charCount > 0
                                            ? `${MIN_CHARS - charCount} more characters needed`
                                            : ''}
                                    </span>
                                    <span className={charCount > MAX_CHARS ? 'text-rose-400 font-medium' : 'text-muted-foreground'}>
                                        {charCount} / {MAX_CHARS}
                                    </span>
                                </div>
                            </div>

                            {/* Schedule time */}
                            <div className="space-y-1.5">
                                <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                    <ClockIcon className="h-3 w-3" />
                                    Schedule Time
                                    <span className="normal-case text-[10px] text-muted-foreground/60">(optional)</span>
                                </label>
                                <DatePickerTime
                                    value={scheduledTime}
                                    onChange={(value) => setScheduledTime(value)}
                                    disabled={isLoading || success}
                                />
                                <p className="text-[11px] text-muted-foreground/60">
                                    Select any future date/time (24-hour format, e.g. 17:44 for 5:44 PM)
                                </p>
                            </div>

                            <Button
                                type="submit"
                                disabled={!isValid || isLoading || success}
                                className="w-full gap-2 p-5 cursor-pointer"
                            >
                                <SendIcon className="h-4 w-4" />
                                {isLoading ? 'Creating…' : success ? 'Created!' : 'Create Post'}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Tips sidebar */}
                <div className="space-y-4">
                    <Card className="border-border/40 bg-card/40">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <LightbulbIcon className="h-4 w-4 text-amber-400" />
                                Writing Tips
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {TIPS.map((tip, i) => (
                                <div key={i} className="flex gap-2 text-xs text-muted-foreground">
                                    <span className="text-primary mt-0.5 shrink-0">•</span>
                                    {tip}
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    <Card className="border-border/40 bg-card/40">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm flex items-center gap-2">
                                <HashIcon className="h-4 w-4 text-violet-400" />
                                Character Guide
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-xs text-muted-foreground">
                            <div className="flex justify-between">
                                <span>Minimum</span>
                                <span className="text-foreground font-medium">{MIN_CHARS} chars</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Sweet spot</span>
                                <span className="text-emerald-400 font-medium">600–1300</span>
                            </div>
                            <div className="flex justify-between">
                                <span>Maximum</span>
                                <span className="text-foreground font-medium">{MAX_CHARS} chars</span>
                            </div>
                            {/* Progress bar */}
                            <div className="mt-3 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-300"
                                    style={{
                                        width: `${Math.min((charCount / MAX_CHARS) * 100, 100)}%`,
                                        backgroundColor: charCount > MAX_CHARS ? '#fb7185'
                                            : charCount >= MIN_CHARS ? '#22d3ee' : '#6b7280',
                                    }}
                                />
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
