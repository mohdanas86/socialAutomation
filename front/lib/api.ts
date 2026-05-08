import axios from 'axios'
import Cookie from 'js-cookie'
import { useAuthStore } from './store'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const client = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Add JWT token to all requests
client.interceptors.request.use((config) => {
    const token = Cookie.get('token') || useAuthStore.getState().token
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Handle 401 responses - redirect to login
client.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            useAuthStore.getState().logout()
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

// Auth API
export const authAPI = {
    getLoginUrl: async () => {
        const response = await client.get('/auth/linkedin/url')
        return response.data
    },
    callback: async (code: string) => {
        const response = await client.get('/auth/callback', {
            params: { code },
        })
        return response.data
    },
}

// User API
export const userAPI = {
    getMe: async () => {
        const response = await client.get('/api/me')
        return response.data
    },
}

// Post API
export const postAPI = {
    create: async (data: {
        content: string
        scheduled_time?: string
    }) => {
        const response = await client.post('/api/posts', data)
        return response.data
    },
    list: async (params?: { status?: string; skip?: number; limit?: number }) => {
        const response = await client.get('/api/posts', { params })
        return response.data
    },
    get: async (id: string) => {
        const response = await client.get(`/api/posts/${id}`)
        return response.data
    },
    update: async (
        id: string,
        data: { content?: string; scheduled_time?: string }
    ) => {
        const response = await client.put(`/api/posts/${id}`, data)
        return response.data
    },
    delete: async (id: string) => {
        const response = await client.delete(`/api/posts/${id}`)
        return response.data
    },
    retry: async (id: string) => {
        const response = await client.post(`/api/posts/${id}/retry`)
        return response.data
    },
    getStats: async (id: string) => {
        const response = await client.get(`/api/posts/${id}/stats`)
        return response.data
    },
}

// Dashboard API
export const dashboardAPI = {
    getStats: async (days: 7 | 30 | 90 = 90) => {
        const response = await client.get('/api/dashboard/stats', { params: { days } })
        return response.data as {
            chart: { week: string; published: number; scheduled: number; failed: number }[]
            totals: { published: number; scheduled: number; failed: number; draft: number }
        }
    },
}

export default client
