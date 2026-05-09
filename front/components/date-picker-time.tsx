"use client"

import * as React from "react"
import { format } from "date-fns"
import { CalendarIcon, ClockIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"

export function DatePickerTime({
    value,
    onChange,
    disabled
}: {
    value?: string,
    onChange: (value: string) => void,
    disabled?: boolean
}) {
  const [open, setOpen] = React.useState(false)

  // We rely on the "YYYY-MM-DDTHH:mm" format, matching `<input type="datetime-local" />`
  // so the value works exactly the same in the parent component.
  const dateObj = value ? new Date(value) : undefined
  const timeStr = value ? format(dateObj!, "HH:mm") : ""

  const handleDateSelect = (d: Date | undefined) => {
    if (!d) {
      onChange("")
      return
    }
    const [hours, minutes] = timeStr ? timeStr.split(":") : ["12", "00"]
    d.setHours(parseInt(hours, 10))
    d.setMinutes(parseInt(minutes, 10))
    
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, "0")
    const dd = String(d.getDate()).padStart(2, "0")
    onChange(`${yyyy}-${mm}-${dd}T${hours}:${minutes}`)
    setOpen(false)
  }

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = e.target.value
    if (!dateObj) return
    const d = new Date(dateObj)
    const [hours, minutes] = newTime.split(":")
    d.setHours(parseInt(hours, 10))
    d.setMinutes(parseInt(minutes, 10))
    
    const yyyy = d.getFullYear()
    const mm = String(d.getMonth() + 1).padStart(2, "0")
    const dd = String(d.getDate()).padStart(2, "0")
    onChange(`${yyyy}-${mm}-${dd}T${hours}:${minutes}`)
  }

  return (
    <div className="flex flex-col sm:flex-row items-center gap-3 w-full">
      <div className="w-full flex-1">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger
            render={
              <Button
                variant="outline"
                disabled={disabled}
                className={cn(
                  "w-full justify-start text-left font-normal border-border/50 bg-muted/30 px-4 py-5 hover:bg-muted/50",
                  !dateObj && "text-muted-foreground"
                )}
              />
            }
          >
            <CalendarIcon className="mr-2 h-4 w-4 opacity-50" />
            {dateObj ? format(dateObj, "PPP") : "Select date"}
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0 border-border/50 bg-card" align="start">
            <Calendar
              mode="single"
              selected={dateObj}
              onSelect={handleDateSelect}
            />
          </PopoverContent>
        </Popover>
      </div>
      <div className="w-full sm:w-40 shrink-0">
        <div className="relative">
            <ClockIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground/50" />
            <Input
              type="time"
              disabled={disabled || !dateObj}
              value={timeStr}
              onChange={handleTimeChange}
              className="w-full pl-9 h-10 border-border/50 bg-muted/30 focus:border-primary/50 focus:ring-primary/30 transition-colors [color-scheme:dark] [&::-webkit-calendar-picker-indicator]:hidden"
            />
        </div>
      </div>
    </div>
  )
}
