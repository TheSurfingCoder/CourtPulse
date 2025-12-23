import * as Sentry from '@sentry/nextjs';
import React from 'react'
import type { Metadata } from 'next'
import { Toaster } from 'sonner'
import '../styles/globals.css'

export function generateMetadata(): Metadata {
  return {
    title: 'CourtPulse - Find Sports Courts Near You',
    description: 'Discover and explore sports courts near you with CourtPulse',
    other: {
      ...Sentry.getTraceData()
    }
  };
}



export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Toaster 
          position="bottom-left"
          richColors
          closeButton
        />
        <div>
          {children}
        </div>
      </body>
    </html>
  )
}