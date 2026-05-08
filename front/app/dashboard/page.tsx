'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useAuthStore, usePostStore } from '@/lib/store'
import { postAPI } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { ChartAreaInteractive } from '@/components/chart-area-interactive'
import { SectionCards } from '@/components/section-cards'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
    FileTextIcon,
    CheckCircleIcon,
    ClockIcon,
    AlertCircleIcon,
    ArrowRightIcon,
    PlusIcon,
    SparklesIcon,
} from 'lucide-react'

// ─── Status badge ─────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
    const map: Record<string, { label: string; className: string }> = {
        posted:    { label: 'Published', className: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25' },
        scheduled: { label: 'Scheduled', className: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/25' },
        failed:    { label: 'Failed',    className: 'bg-rose-500/15 text-rose-400 border-rose-500/25' },
        draft:     { label: 'Draft',     className: 'bg-muted text-muted-foreground border-border' },
    }
    const config = map[status] ?? map.draft
    return (
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${config.className}`}>
            {config.label}
        </span>
    )
}

// ─── Recent post row ──────────────────────────────────────────
function PostRow({ post }: { post: { _id: string; content: string; status: string; scheduled_time?: string } }) {
    const iconMap: Record<string, React.ReactNode> = {
        posted:    <CheckCircleIcon className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />,
        scheduled: <ClockIcon       className="h-3.5 w-3.5 text-fuchsia-400 shrink-0 mt-0.5" />,
        failed:    <AlertCircleIcon className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />,
        draft:     <FileTextIcon    className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />,
    }
    return (
        <div className="flex items-start gap-3 rounded-lg border border-border/40 bg-card/50 p-3 transition-colors hover:bg-card/80 hover:border-border/60">
            {iconMap[post.status] ?? iconMap.draft}
            <div className="min-w-0 flex-1">
                <p className="line-clamp-2 text-sm leading-snug">{post.content}</p>
                {post.scheduled_time && (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                        {new Date(post.scheduled_time).toLocaleDateString('en-US', {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                        })}
                    </p>
                )}
            </div>
            <StatusBadge status={post.status} />
        </div>
    )
}

// ─── Page ─────────────────────────────────────────────────────
export default function DashboardPage() {
    const user    = useAuthStore((s) => s.user)
    const posts   = usePostStore((s) => s.posts)
    const setPosts = usePostStore((s) => s.setPosts)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError]         = useState<string | null>(null)
    const hasFetchedRef             = useRef(false)

    useEffect(() => {
        if (!user || hasFetchedRef.current) return
        setIsLoading(true)
        postAPI.list()
            .then((data) => { setPosts(data.items || []); hasFetchedRef.current = true })
            .catch(() => setError('Failed to load posts'))
            .finally(() => setIsLoading(false))
    }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

    if (isLoading) {
        return (
            <div className="flex flex-1 items-center justify-center">
                <LoadingSpinner message="Loading dashboard..." />
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-1 items-center justify-center px-4">
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-6 max-w-sm text-center space-y-3">
                    <AlertCircleIcon className="h-8 w-8 text-rose-400 mx-auto" />
                    <h2 className="font-semibold">Something went wrong</h2>
                    <p className="text-sm text-muted-foreground">{error}</p>
                    <Button size="sm" variant="outline" onClick={() => window.location.reload()}
                        className="border-rose-500/30 text-rose-400 hover:bg-rose-500/10">
                        Try again
                    </Button>
                </div>
            </div>
        )
    }

    const postedCount    = posts.filter((p) => p.status === 'posted').length
    const scheduledCount = posts.filter((p) => p.status === 'scheduled').length
    const failedCount    = posts.filter((p) => p.status === 'failed').length
    const recentPosts    = posts.slice(0, 6)
    const firstName      = user?.name?.split(' ')[0] ?? 'there'

    return (
        <>
            {/* Welcome banner */}
            <div className="flex flex-col gap-1 px-4 lg:px-6">
                <div className="flex items-center gap-2">
                    <SparklesIcon className="h-5 w-5 text-primary shrink-0" />
                    <h2 className="text-xl font-semibold tracking-tight">
                        Welcome back,{' '}
                        <span className="bg-gradient-to-r from-cyan-300 via-primary to-fuchsia-300 bg-clip-text text-transparent">
                            {firstName}
                        </span>
                    </h2>
                </div>
                <p className="text-sm text-muted-foreground pl-7">
                    Here's what's happening with your LinkedIn automation today.
                </p>
            </div>

            {/* Stats cards */}
            <SectionCards stats={{ total: posts.length, posted: postedCount, scheduled: scheduledCount, failed: failedCount }} />

            {/* Chart + Recent Posts */}
            <div className="grid gap-4 px-4 lg:px-6 lg:grid-cols-2">
                <ChartAreaInteractive />

                <Card className="border-border/50 flex flex-col">
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="text-base">Recent Posts</CardTitle>
                                <CardDescription className="text-xs mt-0.5">Latest activity across your queue</CardDescription>
                            </div>
                            <Link href="/dashboard/posts">
                                <Button variant="ghost" size="sm" className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground">
                                    View all <ArrowRightIcon className="h-3 w-3" />
                                </Button>
                            </Link>
                        </div>
                    </CardHeader>
                    <CardContent className="flex-1 space-y-2 pt-0">
                        {recentPosts.length === 0 ? (
                            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
                                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
                                    <FileTextIcon className="h-5 w-5 text-primary" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium">No posts yet</p>
                                    <p className="text-xs text-muted-foreground mt-0.5">Create your first LinkedIn post to get started.</p>
                                </div>
                                <Link href="/dashboard/create">
                                    <Button size="sm" className="mt-1 gap-1.5">
                                        <PlusIcon className="h-3.5 w-3.5" /> Create Post
                                    </Button>
                                </Link>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {recentPosts.map((post) => <PostRow key={post._id} post={post} />)}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </>
    )
}
