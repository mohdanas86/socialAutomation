import type { Metadata } from 'next'
import { Providers } from '@/components/Providers'
import { TooltipProvider } from '@/components/ui/tooltip'
import './globals.css'
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ['latin'], variable: '--font-sans' });

export const metadata: Metadata = {
  title: 'Social Automation',
  description: 'Automate your LinkedIn posts',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body>
        <Providers>
          <TooltipProvider>
            {children}
          </TooltipProvider>
        </Providers>
      </body>
    </html>
  )
}
