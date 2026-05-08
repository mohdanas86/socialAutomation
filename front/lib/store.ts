import { create } from 'zustand'

// Auth Store
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
    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    setIsLoading: (loading: boolean) => void
    logout: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
    user: null,
    token: null,
    isLoading: false,
    setUser: (user) => set({ user }),
    setToken: (token) => set({ token }),
    setIsLoading: (loading) => set({ isLoading: loading }),
    logout: () => set({ user: null, token: null }),
}))

// Post Store
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
