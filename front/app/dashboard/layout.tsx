'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { AppSidebar } from '@/components/app-sidebar'
import { SiteHeader } from '@/components/site-header'
import { SidebarProvider } from '@/components/ui/sidebar'
import { LoadingSpinner } from '@/components/LoadingSpinner'

/**
 * Dashboard Layout
 * Wraps every page under /dashboard with:
 * - Auth guard (redirect to /login if not authenticated)
 * - Sidebar + Header shell
 *
 * Individual pages only need to return their <main> content.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter()
    const user = useAuthStore((state) => state.user)
    const isInitialized = useAuthStore((state) => state.isInitialized)

    useEffect(() => {
        if (!isInitialized) return
        if (!user) router.replace('/login')
    }, [user, isInitialized, router])

    // Still initializing — show nothing (Providers already shows null, belt-and-suspenders)
    if (!isInitialized || !user) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-background">
                <LoadingSpinner message="Loading..." />
            </div>
        )
    }

    return (
        <SidebarProvider>
            <AppSidebar />
            <div className="flex min-h-svh flex-1 flex-col bg-[#141313]">
                <SiteHeader />
                <main className="flex flex-1 flex-col gap-6 py-6 @container/main">
                    {children}
                </main>
            </div>
        </SidebarProvider>
    )
}
