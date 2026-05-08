"use client"

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  FileTextIcon,
  CheckCircleIcon,
  CalendarClockIcon,
  AlertCircleIcon,
  TrendingUpIcon,
} from "lucide-react"

type SectionCardStats = {
  total: number
  posted: number
  scheduled: number
  failed: number
}

interface StatCardProps {
  title: string
  value: number
  icon: React.ReactNode
  gradient: string
  iconBg: string
  badge?: string
  badgeVariant?: "default" | "secondary" | "destructive" | "outline"
}

function StatCard({ title, value, icon, gradient, iconBg, badge, badgeVariant = "secondary" }: StatCardProps) {
  return (
    <Card
      className={`@container/card relative overflow-hidden border-border/50 ${gradient}`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconBg}`}>
            {icon}
          </div>
          {badge && (
            <Badge variant={badgeVariant} className="text-xs font-medium gap-1">
              <TrendingUpIcon className="h-3 w-3" />
              {badge}
            </Badge>
          )}
        </div>
        <CardTitle className="text-sm font-medium text-muted-foreground mt-3">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-3xl font-bold tracking-tight @[250px]/card:text-4xl">
          {value}
        </div>
      </CardContent>
    </Card>
  )
}

export function SectionCards({ stats }: { stats: SectionCardStats }) {
  const successRate = stats.total > 0 ? Math.round((stats.posted / stats.total) * 100) : 0

  return (
    <div className="grid grid-cols-1 gap-4 px-4 lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      <StatCard
        title="Total Posts"
        value={stats.total}
        icon={<FileTextIcon className="h-4 w-4 text-cyan-400" />}
        gradient="bg-gradient-to-br from-cyan-500/10 via-card to-card"
        iconBg="bg-cyan-500/15 border border-cyan-500/20"
        badge={stats.total > 0 ? "Active" : undefined}
      />
      <StatCard
        title="Published"
        value={stats.posted}
        icon={<CheckCircleIcon className="h-4 w-4 text-emerald-400" />}
        gradient="bg-gradient-to-br from-emerald-500/10 via-card to-card"
        iconBg="bg-emerald-500/15 border border-emerald-500/20"
        badge={successRate > 0 ? `${successRate}%` : undefined}
      />
      <StatCard
        title="Scheduled"
        value={stats.scheduled}
        icon={<CalendarClockIcon className="h-4 w-4 text-fuchsia-400" />}
        gradient="bg-gradient-to-br from-fuchsia-500/10 via-card to-card"
        iconBg="bg-fuchsia-500/15 border border-fuchsia-500/20"
        badge={stats.scheduled > 0 ? "Queued" : undefined}
      />
      <StatCard
        title="Failed"
        value={stats.failed}
        icon={<AlertCircleIcon className="h-4 w-4 text-rose-400" />}
        gradient="bg-gradient-to-br from-rose-500/10 via-card to-card"
        iconBg="bg-rose-500/15 border border-rose-500/20"
        badge={stats.failed > 0 ? "Needs attention" : undefined}
        badgeVariant={stats.failed > 0 ? "destructive" : "secondary"}
      />
    </div>
  )
}
