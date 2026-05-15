import Link from "next/link"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { PlusIcon } from "lucide-react"
import React from "react"

interface SiteHeaderProps {
  title?: string
  breadcrumb?: { label: string; href?: string }[]
}

export function SiteHeader({ title = "Dashboard", breadcrumb }: SiteHeaderProps) {
  return (
    <header className="sticky top-0 z-50 flex py-3 shrink-0 items-center gap-2 border-b border-border/50 bg-background/80 backdrop-blur-sm transition-[width,height] ease-linear">
      <div className="flex w-full items-center gap-2 px-4 lg:gap-3 lg:px-6">
        <SidebarTrigger className="-ml-1 text-muted-foreground hover:text-foreground" />
        <Separator
          orientation="vertical"
          className="mx-1 h-4 opacity-30 data-vertical:self-auto"
        />

        {breadcrumb && breadcrumb.length > 0 ? (
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="/dashboard" className="text-muted-foreground hover:text-foreground text-sm">
                  Dashboard
                </BreadcrumbLink>
              </BreadcrumbItem>
              {breadcrumb.map((item, i) => (
                <React.Fragment key={i}>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    {item.href ? (
                      <BreadcrumbLink href={item.href} className="text-muted-foreground hover:text-foreground text-sm">
                        {item.label}
                      </BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage className="text-sm font-medium">
                        {item.label}
                      </BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                </React.Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        ) : (
          <h1 className="text-sm font-medium text-foreground">{title}</h1>
        )}

        <div className="ml-auto flex items-center gap-2">
          {/* Use Link wrapping Button — avoids the nativeButton/render prop warning */}
          <Link href="/dashboard/create">
            <Button
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20 rounded-sm border border-primary-border cursor-pointer"
            >
              <PlusIcon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Create Post</span>
              <span className="sm:hidden">New</span>
            </Button>
          </Link>
        </div>
      </div>
    </header>
  )
}
