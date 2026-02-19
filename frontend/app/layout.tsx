import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
    title: 'Skylark Drones — AI Operations Coordinator',
    description: 'AI-powered drone operations coordination system for managing pilots, drones, missions, and conflict detection',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body className="antialiased">{children}</body>
        </html>
    )
}
