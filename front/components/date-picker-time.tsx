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

  const isSameLocalDate = (a: Date, b: Date): boolean => {
    return (
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    )
  }

  const getNextMinute = (): Date => {
    const d = new Date()
    d.setSeconds(0, 0)
    d.setMinutes(d.getMinutes() + 1)
    return d
  }

  /**
   * Parse the YYYY-MM-DDTHH:mm format back into local Date object.
   * CRITICAL: This Date represents LOCAL time, not UTC.
   */
  const parseLocalDateTime = (str: string | undefined): Date | undefined => {
    if (!str) return undefined
    const [datePart, timePart] = str.split('T')
    if (!datePart || !timePart) return undefined

    const [year, month, day] = datePart.split('-').map(Number)
    const [hour, minute] = timePart.split(':').map(Number)

    // Create Date in LOCAL timezone (this is what we stored)
    return new Date(year, month - 1, day, hour, minute, 0, 0)
  }

  const dateObj = parseLocalDateTime(value)
  const timeStr = dateObj ? format(dateObj, "HH:mm") : ""

  /**
   * Convert local Date components to YYYY-MM-DDTHH:mm format string.
   * The Date object represents LOCAL time, so we extract local components.
   */
  const formatLocalDateTime = (date: Date, hours: string, minutes: string): string => {
    const yyyy = date.getFullYear()
    const mm = String(date.getMonth() + 1).padStart(2, "0")
    const dd = String(date.getDate()).padStart(2, "0")
    return `${yyyy}-${mm}-${dd}T${hours}:${minutes}`
  }

  const handleDateSelect = (d: Date | undefined) => {
    if (!d) {
      onChange("")
      return
    }

    // Use current value time or default to 12:00
    const [hours, minutes] = timeStr ? timeStr.split(":") : ["12", "00"]

    // Create a new Date representing the selected date at the specified time (in local timezone)
    let selectedDate = new Date(d.getFullYear(), d.getMonth(), d.getDate(),
      parseInt(hours, 10), parseInt(minutes, 10), 0, 0)

    // If user picked today and selected time is already past, move to next minute.
    const now = new Date()
    if (isSameLocalDate(selectedDate, now) && selectedDate.getTime() <= now.getTime()) {
      const nextMinute = getNextMinute()
      selectedDate = new Date(
        d.getFullYear(),
        d.getMonth(),
        d.getDate(),
        nextMinute.getHours(),
        nextMinute.getMinutes(),
        0,
        0
      )
    }

    const result = formatLocalDateTime(
      selectedDate,
      String(selectedDate.getHours()).padStart(2, "0"),
      String(selectedDate.getMinutes()).padStart(2, "0")
    )
    console.log(`[DatePicker] Date selected: ${result}`)
    console.log(`[DatePicker] Selected date in future: ${selectedDate > new Date()}`)
    onChange(result)
    setOpen(false)
  }

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = e.target.value
    if (!dateObj) return

    const [hours, minutes] = newTime.split(":")

    // Create new Date with same date but new time
    let updatedDate = new Date(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate(),
      parseInt(hours, 10), parseInt(minutes, 10), 0, 0)

    const now = new Date()
    if (isSameLocalDate(updatedDate, now) && updatedDate.getTime() <= now.getTime()) {
      const nextMinute = getNextMinute()
      updatedDate = new Date(
        dateObj.getFullYear(),
        dateObj.getMonth(),
        dateObj.getDate(),
        nextMinute.getHours(),
        nextMinute.getMinutes(),
        0,
        0
      )
    }

    const result = formatLocalDateTime(
      updatedDate,
      String(updatedDate.getHours()).padStart(2, "0"),
      String(updatedDate.getMinutes()).padStart(2, "0")
    )
    console.log(`[DatePicker] Time changed: ${result}`)
    onChange(result)
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
              disabled={(date) => {
                // Disable dates before today
                const today = new Date()
                today.setHours(0, 0, 0, 0)
                return date < today
              }}
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
            step={60}
            className="w-full pl-9 h-10 border-border/50 bg-muted/30 focus:border-primary/50 focus:ring-primary/30 transition-colors [color-scheme:dark] [&::-webkit-calendar-picker-indicator]:hidden"
          />
        </div>
      </div>
    </div>
  )
}
