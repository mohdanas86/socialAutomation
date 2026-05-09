'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { postAPI } from '@/lib/api'
import { useDashboardStatsStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { formatDistanceToNow } from 'date-fns'
import {
    CheckCircleIcon,
    ClockIcon,
    AlertCircleIcon,
    FileTextIcon,
    RefreshCwIcon,
    Trash2Icon,
    PlusIcon,
    ChevronLeftIcon,
    ChevronRightIcon,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────
interface Post {
    _id: string
    content: string
    status: 'draft' | 'scheduled' | 'posted' | 'failed'
    scheduled_time?: string
    created_at: string
    platform: string
    retry_count: number
    last_error?: string
    posted_at?: string
}

const FILTER_TABS = ['all', 'scheduled', 'posted', 'failed', 'draft'] as const
type Filter = (typeof FILTER_TABS)[number]

const PAGE_SIZE = 12

// ─── Status config ────────────────────────────────────────────
const STATUS_CONFIG = {
    posted: { label: 'Published', icon: <CheckCircleIcon className="h-3.5 w-3.5" />, cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.1)]' },
    scheduled: { label: 'Scheduled', icon: <ClockIcon className="h-3.5 w-3.5" />, cls: 'bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/40 shadow-[0_0_10px_rgba(217,70,239,0.1)]' },
    failed: { label: 'Failed', icon: <AlertCircleIcon className="h-3.5 w-3.5" />, cls: 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-[0_0_10px_rgba(244,63,94,0.1)]' },
    draft: { label: 'Draft', icon: <FileTextIcon className="h-3.5 w-3.5" />, cls: 'bg-[#343234]/40 text-[#FEFEFF] border-[#343234] shadow-sm' },
} as const

/**
 * Robustly parse any UTC datetime string from the API.
 * Backend may send:
 *   - "2026-05-09T01:28:00"       → naive UTC (no tz info) → append 'Z'
 *   - "2026-05-09T01:28:00Z"      → already UTC with Z → parse as-is
 *   - "2026-05-09T01:28:00+00:00" → UTC with offset → parse as-is
 *   - "2026-05-09T01:28:00.000000" → naive with microseconds → append 'Z'
 * JS Date treats strings without tz as LOCAL time — we must always force UTC.
 */
const toUtcDate = (s: string): Date => {
    if (!s) return new Date(NaN)
    // Already has explicit timezone info
    if (s.endsWith('Z') || /[+\-]\d{2}:\d{2}$/.test(s)) {
        return new Date(s)
    }
    // Naive datetime — must be UTC (backend always stores UTC)
    return new Date(s + 'Z')
}

/**
 * Format a UTC date string for display in the user's local timezone.
 * Shows: "May 9, 06:58 AM IST" style.
 */
const formatTime = (s: string): string => {
    const d = toUtcDate(s)
    if (isNaN(d.getTime())) return 'Invalid date'
    return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short',
    })
}

// ─── Post Card ────────────────────────────────────────────────
function PostCard({ post, onDelete, onRetry }: {
    post: Post
    onDelete: (id: string) => void
    onRetry: (id: string) => void
}) {
    const [busy, setBusy] = useState(false)
    const cfg = STATUS_CONFIG[post.status] ?? STATUS_CONFIG.draft

    const handleDelete = async () => {
        if (!confirm('Are you sure you want to delete this post?')) return
        setBusy(true)
        try {
            await postAPI.delete(post._id)
            onDelete(post._id)
        } catch (e: any) {
            alert(e?.response?.data?.detail || 'Failed to delete post')
        } finally {
            setBusy(false)
        }
    }

    const handleRetry = async () => {
        setBusy(true)
        try {
            const updated = await postAPI.retry(post._id)
            onRetry(updated._id || post._id)
        } catch (e: any) {
            alert(e?.response?.data?.detail || 'Failed to retry post')
        } finally {
            setBusy(false)
        }
    }

    return (
        <div className="flex flex-col gap-3 rounded-xl border border-border/40 bg-card/60 p-4 backdrop-blur-sm transition-all hover:border-border/60 hover:bg-card/80">
            {/* Header */}
            <div className="flex items-center justify-between gap-2">
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${cfg.cls}`}>
                    {cfg.icon} {cfg.label}
                </span>
                <span className="text-[11px] text-muted-foreground shrink-0">
                    {formatDistanceToNow(toUtcDate(post.created_at), { addSuffix: true })}
                </span>
            </div>

            {/* Content */}
            <p className="text-sm text-foreground/90 line-clamp-4 leading-relaxed flex-1">
                {post.content}
            </p>

            {/* Scheduled time */}
            {post.scheduled_time && (
                <div className="flex items-center gap-1.5 rounded-md bg-muted/40 px-2.5 py-1.5 text-[11px] text-muted-foreground">
                    <ClockIcon className="h-3 w-3 shrink-0" />
                    Scheduled:{' '}
                    {formatTime(post.scheduled_time)}
                </div>
            )}

            {/* Posted time */}
            {post.posted_at && (
                <div className="flex items-center gap-1.5 rounded-md bg-emerald-500/5 px-2.5 py-1.5 text-[11px] text-emerald-400/80">
                    <CheckCircleIcon className="h-3 w-3 shrink-0" />
                    Published:{' '}
                    {formatTime(post.posted_at!)}
                </div>
            )}

            {/* Error hint */}
            {post.last_error && post.status === 'failed' && (
                <p className="text-[11px] text-rose-400/80 line-clamp-2 bg-rose-500/5 rounded-md px-2.5 py-1.5">
                    ⚠ {post.last_error}
                </p>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-0.5 border-t border-border/30 mt-auto">
                {post.status === 'failed' && (
                    <Button size="sm" variant="ghost" onClick={handleRetry} disabled={busy}
                        className="h-7 gap-1.5 text-xs text-fuchsia-400 hover:bg-fuchsia-500/10 hover:text-fuchsia-300">
                        <RefreshCwIcon className="h-3 w-3" />
                        Retry
                    </Button>
                )}
                {post.status !== 'posted' && (
                    <Button size="sm" variant="ghost" onClick={handleDelete} disabled={busy}
                        className="h-7 gap-1.5 text-xs text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 ml-auto">
                        <Trash2Icon className="h-3 w-3" />
                        Delete
                    </Button>
                )}
            </div>
        </div>
    )
}

// ─── Skeleton loader ──────────────────────────────────────────
function SkeletonCard() {
    return (
        <div className="flex flex-col gap-3 rounded-xl border border-border/30 bg-card/40 p-4 animate-pulse">
            <div className="flex items-center justify-between">
                <div className="h-5 w-20 rounded-full bg-muted/60" />
                <div className="h-3 w-16 rounded bg-muted/40" />
            </div>
            <div className="space-y-2">
                <div className="h-3 w-full rounded bg-muted/50" />
                <div className="h-3 w-4/5 rounded bg-muted/50" />
                <div className="h-3 w-2/3 rounded bg-muted/40" />
            </div>
            <div className="h-3 w-1/2 rounded bg-muted/30 mt-1" />
        </div>
    )
}

// ─── Page ─────────────────────────────────────────────────────
export default function PostsPage() {
    const invalidate = useDashboardStatsStore((s) => s.invalidate)

    const [posts, setPosts] = useState<Post[]>([])
    const [total, setTotal] = useState(0)
    const [filter, setFilter] = useState<Filter>('all')
    const [page, setPage] = useState(1)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // ── Fetch from API ─────────────────────────────────────────
    const fetchPosts = useCallback(async (f: Filter, p: number) => {
        setIsLoading(true)
        setError(null)
        try {
            const data = await postAPI.list({
                status: f !== 'all' ? f : undefined,
                skip: (p - 1) * PAGE_SIZE,
                limit: PAGE_SIZE,
            })
            // API returns { items, total, page, per_page }
            setPosts(data.items ?? [])
            setTotal(data.total ?? 0)
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Failed to load posts. Please try again.'
            setError(detail)
            setPosts([])
            setTotal(0)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchPosts(filter, page)
    }, [filter, page, fetchPosts])

    // ── Handlers ───────────────────────────────────────────────
    const handleFilterChange = (tab: Filter) => {
        setFilter(tab)
        setPage(1)      // Reset to page 1 on filter change
    }

    const handleDelete = (deletedId: string) => {
        setPosts((prev) => prev.filter((p) => p._id !== deletedId))
        setTotal((prev) => Math.max(0, prev - 1))
        invalidate()
    }

    const handleRetry = (retriedId: string) => {
        // Re-fetch to get updated status
        fetchPosts(filter, page)
        invalidate()
    }

    const totalPages = Math.ceil(total / PAGE_SIZE)

    return (
        <div className="flex flex-col gap-5 px-4 lg:px-6">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">Your Posts</h2>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        {isLoading ? '…' : `${total} post${total !== 1 ? 's' : ''}`}
                        {filter !== 'all' && !isLoading && ` · filtered by ${filter}`}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button size="sm" variant="ghost"
                        onClick={() => fetchPosts(filter, page)}
                        className="gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                        disabled={isLoading}
                    >
                        <RefreshCwIcon className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                        Refresh
                    </Button>
                    <Link href="/dashboard/create">
                        <Button size="sm" className="gap-1.5">
                            <PlusIcon className="h-3.5 w-3.5" />
                            New Post
                        </Button>
                    </Link>
                </div>
            </div>

            {/* Filter tabs */}
            <div className="flex flex-wrap gap-1.5">
                {FILTER_TABS.map((tab) => (
                    <button
                        key={tab}
                        onClick={() => handleFilterChange(tab)}
                        className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${filter === tab
                                ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/25'
                                : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                            }`}
                    >
                        {tab === 'posted' ? 'Published' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {/* Error */}
            {error && (
                <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
                    <div className="flex items-center gap-2 text-sm text-rose-400">
                        <AlertCircleIcon className="h-4 w-4 shrink-0" />
                        {error}
                    </div>
                    <Button size="sm" variant="ghost" onClick={() => fetchPosts(filter, page)}
                        className="shrink-0 text-xs text-rose-400 hover:bg-rose-500/10">
                        Retry
                    </Button>
                </div>
            )}

            {/* Grid */}
            {isLoading ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
                </div>
            ) : posts.length === 0 && !error ? (
                <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
                        <FileTextIcon className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                        <p className="font-medium">
                            {filter === 'all' ? 'No posts yet' : `No ${filter === 'posted' ? 'published' : filter} posts`}
                        </p>
                        <p className="text-sm text-muted-foreground mt-0.5">
                            {filter === 'all'
                                ? 'Create your first LinkedIn post to get started.'
                                : 'Change the filter or create a new post.'}
                        </p>
                    </div>
                    <Link href="/dashboard/create">
                        <Button size="sm" className="gap-1.5">
                            <PlusIcon className="h-3.5 w-3.5" /> Create Post
                        </Button>
                    </Link>
                </div>
            ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {posts.map((post) => (
                        <PostCard
                            key={post._id}
                            post={post}
                            onDelete={handleDelete}
                            onRetry={handleRetry}
                        />
                    ))}
                </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && !isLoading && (
                <div className="flex items-center justify-between border-t border-border/30 pt-4">
                    <p className="text-xs text-muted-foreground">
                        Page {page} of {totalPages} · {total} posts
                    </p>
                    <div className="flex items-center gap-1.5">
                        <Button size="sm" variant="ghost" disabled={page <= 1}
                            onClick={() => setPage((p) => p - 1)}
                            className="h-8 w-8 p-0">
                            <ChevronLeftIcon className="h-4 w-4" />
                        </Button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1)
                            .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                            .reduce<(number | '...')[]>((acc, p, i, arr) => {
                                if (i > 0 && (arr[i - 1] as number) + 1 < p) acc.push('...')
                                acc.push(p)
                                return acc
                            }, [])
                            .map((p, i) =>
                                p === '...' ? (
                                    <span key={`ellipsis-${i}`} className="text-xs text-muted-foreground px-1">…</span>
                                ) : (
                                    <Button key={p} size="sm" variant={page === p ? 'default' : 'ghost'}
                                        onClick={() => setPage(p as number)}
                                        className="h-8 w-8 p-0 text-xs">
                                        {p}
                                    </Button>
                                )
                            )
                        }
                        <Button size="sm" variant="ghost" disabled={page >= totalPages}
                            onClick={() => setPage((p) => p + 1)}
                            className="h-8 w-8 p-0">
                            <ChevronRightIcon className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            )}
        </div>
    )
}
