import { create } from 'zustand'

// ─── Auth Store ───────────────────────────────────────────────
interface User {
    _id: string
    email: string
    name: string
    linkedin_id: string
}

interface AuthStore {
    user: User | null
    token: string | null
    isLoading: boolean
    /** True once Providers has finished its async init — prevents premature redirects */
    isInitialized: boolean
    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    setIsLoading: (loading: boolean) => void
    setInitialized: (v: boolean) => void
    logout: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
    user: null,
    token: null,
    isLoading: false,
    isInitialized: false,
    setUser: (user) => set({ user }),
    setToken: (token) => set({ token }),
    setIsLoading: (loading) => set({ isLoading: loading }),
    setInitialized: (v) => set({ isInitialized: v }),
    logout: () => set({ user: null, token: null, isInitialized: true }),
}))

// ─── Post Store ───────────────────────────────────────────────
interface Post {
    _id: string
    content: string
    status: 'draft' | 'scheduled' | 'posted' | 'failed'
    scheduled_time?: string
    created_at: string
    linkedin_post_id?: string
    retry_count?: number
}

interface PostStore {
    posts: Post[]
    loading: boolean
    error: string | null
    setPosts: (posts: Post[]) => void
    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    addPost: (post: Post) => void
    updatePost: (id: string, post: Post) => void
    deletePost: (id: string) => void
}

export const usePostStore = create<PostStore>((set) => ({
    posts: [],
    loading: false,
    error: null,
    setPosts: (posts) => set({ posts }),
    setLoading: (loading) => set({ loading }),
    setError: (error) => set({ error }),
    addPost: (post) => set((state) => ({ posts: [post, ...state.posts] })),
    updatePost: (id, post) =>
        set((state) => ({
            posts: state.posts.map((p) => (p._id === id ? post : p)),
        })),
    deletePost: (id) =>
        set((state) => ({
            posts: state.posts.filter((p) => p._id !== id),
        })),
}))

// ─── Dashboard Stats Cache Store ──────────────────────────────
// Avoids redundant API calls — data is reused across page navigations
// until TTL expires or posts are mutated.

const STATS_TTL_MS = 5 * 60 * 1000 // 5 minutes

export interface ChartRow {
    week: string
    published: number
    scheduled: number
    failed: number
}

export interface StatsTotals {
    published: number
    scheduled: number
    failed: number
    draft: number
}

interface StatsCache {
    chart: ChartRow[]
    totals: StatsTotals
    range: number       // days requested (7 | 30 | 90)
    fetchedAt: number   // Date.now() timestamp
}

interface DashboardStatsStore {
    cache: StatsCache | null
    /** Store fresh data from the API */
    setStats: (data: { chart: ChartRow[]; totals: StatsTotals }, range: number) => void
    /** Is the current cache still valid for the given range? */
    isValid: (range: number) => boolean
    /** Invalidate cache (call after creating / deleting / updating a post) */
    invalidate: () => void
}

export const useDashboardStatsStore = create<DashboardStatsStore>((set, get) => ({
    cache: null,
    setStats: (data, range) =>
        set({
            cache: {
                ...data,
                range,
                fetchedAt: Date.now(),
            },
        }),
    isValid: (range) => {
        const c = get().cache
        if (!c) return false
        if (c.range !== range) return false
        return Date.now() - c.fetchedAt < STATS_TTL_MS
    },
    invalidate: () => set({ cache: null }),
}))
