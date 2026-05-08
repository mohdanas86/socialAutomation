"use client"

import * as React from "react"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { useAuthStore } from "@/lib/store"
import {
  LayoutDashboardIcon,
  FileTextIcon,
  CalendarClockIcon,
  PlusCircleIcon,
  SparklesIcon,
} from "lucide-react"

const navMain = [
  {
    title: "Overview",
    url: "/dashboard",
    icon: <LayoutDashboardIcon className="size-4" />,
  },
  {
    title: "Create Post",
    url: "/dashboard/create",
    icon: <PlusCircleIcon className="size-4" />,
  },
  {
    title: "My Posts",
    url: "/dashboard/posts",
    icon: <FileTextIcon className="size-4" />,
  },
  {
    title: "Scheduled",
    url: "/dashboard/schedule",
    icon: <CalendarClockIcon className="size-4" />,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const user = useAuthStore((state) => state.user)
  const userInfo = {
    name: user?.name || "Account",
    email: user?.email || "Not connected",
    avatar: "",
  }

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      {/* Brand header */}
      <SidebarHeader className="border-b border-sidebar-border/50 pb-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="data-[slot=sidebar-menu-button]:p-2! group"
              render={<a href="/dashboard" />}
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 border border-primary/25 ring-1 ring-primary/10 shrink-0">
                <SparklesIcon className="size-3.5 text-primary" />
              </div>
              <div className="flex flex-col gap-0 leading-none">
                <span className="text-sm font-semibold tracking-tight">
                  Social Auto
                </span>
                <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
                  LinkedIn
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Navigation */}
      <SidebarContent className="py-2">
        <NavMain items={navMain} />
      </SidebarContent>

      <SidebarSeparator className="opacity-30" />

      {/* User footer */}
      <SidebarFooter className="pt-2">
        <NavUser user={userInfo} />
      </SidebarFooter>
    </Sidebar>
  )
}
