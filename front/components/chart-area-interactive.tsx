"use client"

import * as React from "react"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts"
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { dashboardAPI } from "@/lib/api"
import { useDashboardStatsStore } from "@/lib/store"
import { BarChart2Icon } from "lucide-react"

// ─── Constants ────────────────────────────────────────────────
type Range = 7 | 30 | 90

const COLORS = {
  published: "#22d3ee",  // cyan-400
  scheduled: "#a78bfa",  // violet-400
  failed:    "#fb7185",  // rose-400
}

// ─── Custom tooltip ───────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-white/10 bg-[#0a0d16]/95 backdrop-blur px-4 py-3 shadow-2xl text-sm min-w-[148px]">
      <p className="font-semibold text-white/60 text-xs mb-2 pb-1.5 border-b border-white/10">
        {label}
      </p>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} className="flex items-center justify-between gap-4 mt-1">
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: entry.color }} />
            <span className="text-white/50 capitalize text-xs">{entry.dataKey}</span>
          </div>
          <span className="font-bold text-white text-xs">{entry.value}</span>
        </div>
      ))}
    </div>
  )
}

// ─── Legend ───────────────────────────────────────────────────
function ChartLegend() {
  return (
    <div className="flex items-center justify-center gap-5 pt-1">
      {(["published", "scheduled", "failed"] as const).map((key) => (
        <div key={key} className="flex items-center gap-1.5 text-[11px] text-muted-foreground capitalize">
          <span className="inline-block h-2 w-2.5 rounded-sm shrink-0" style={{ backgroundColor: COLORS[key] }} />
          {key}
        </div>
      ))}
    </div>
  )
}

// ─── Skeleton while loading ───────────────────────────────────
function ChartSkeleton() {
  const heights = [60, 90, 50, 120, 80, 110, 70, 100]
  return (
    <div className="flex items-end gap-3 h-[230px] px-2 pt-4">
      {heights.map((h, i) => (
        <Skeleton key={i} className="flex-1 rounded-md" style={{ height: h }} />
      ))}
    </div>
  )
}

// ─── Empty state ──────────────────────────────────────────────
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-[230px] gap-3 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
        <BarChart2Icon className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium">No activity yet</p>
        <p className="text-xs text-muted-foreground mt-0.5">Create posts to see your activity chart.</p>
      </div>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────
export function ChartAreaInteractive() {
  const [range, setRange] = React.useState<Range>(90)
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  // Zustand cache — no re-fetch if data is fresh for this range
  const cache       = useDashboardStatsStore((s) => s.cache)
  const isValid     = useDashboardStatsStore((s) => s.isValid)
  const setStats    = useDashboardStatsStore((s) => s.setStats)

  // Derived from cache
  const data   = (cache?.range === range ? cache.chart  : null)
  const totals = (cache?.range === range ? cache.totals : null)

  React.useEffect(() => {
    // Skip fetch if cache is still valid for current range
    if (isValid(range)) return

    let cancelled = false
    setLoading(true)
    setError(null)

    dashboardAPI
      .getStats(range)
      .then((res) => {
        if (cancelled) return
        setStats(res, range)
      })
      .catch((err) => {
        if (cancelled) return
        console.error("Dashboard stats error:", err)
        setError("Could not load activity data.")
      })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [range]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleRangeChange = (val: string | null) => {
    if (val) setRange(Number(val) as Range)
  }

  return (
    <Card className="border-border/40 bg-card/60 backdrop-blur-sm flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          {/* Title + live totals */}
          <div>
            <CardTitle className="text-base font-semibold">Post Activity</CardTitle>
            <CardDescription className="mt-1 flex flex-wrap gap-3 text-xs">
              {(["published", "scheduled", "failed"] as const).map((key) => (
                <span key={key} className="flex items-center gap-1.5">
                  <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: COLORS[key] }} />
                  <span className="text-muted-foreground">
                    {loading || !totals ? "—" : totals[key]} {key}
                  </span>
                </span>
              ))}
            </CardDescription>
          </div>

          {/* Range picker */}
          <Select value={String(range)} onValueChange={handleRangeChange}>
            <SelectTrigger
              className="h-7 w-32 text-xs border-border/50 bg-muted/40"
              aria-label="Select time range"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-xl">
              <SelectItem value="7"  className="text-xs">Last 7 days</SelectItem>
              <SelectItem value="30" className="text-xs">Last 30 days</SelectItem>
              <SelectItem value="90" className="text-xs">Last 3 months</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent className="flex-1 pt-2 pb-4 px-2 sm:px-4">
        {loading ? (
          <ChartSkeleton />
        ) : error ? (
          <div className="flex items-center justify-center h-[230px] text-xs text-muted-foreground">
            {error}
          </div>
        ) : !data || data.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={data} barCategoryGap="32%" barGap={3} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" strokeDasharray="4 4" />
                <XAxis
                  dataKey="week"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "rgba(255,255,255,0.30)", fontSize: 11 }}
                  tickMargin={8}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "rgba(255,255,255,0.30)", fontSize: 11 }}
                  allowDecimals={false}
                  width={28}
                />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.03)", radius: 6 }} content={<CustomTooltip />} />
                <Bar dataKey="published" fill={COLORS.published} radius={[4,4,0,0]} maxBarSize={24} fillOpacity={0.9} />
                <Bar dataKey="scheduled" fill={COLORS.scheduled} radius={[4,4,0,0]} maxBarSize={24} fillOpacity={0.85} />
                <Bar dataKey="failed"    fill={COLORS.failed}    radius={[4,4,0,0]} maxBarSize={24} fillOpacity={0.80} />
              </BarChart>
            </ResponsiveContainer>
            <ChartLegend />
          </>
        )}
      </CardContent>
    </Card>
  )
}
