'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Message = {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
}

type SystemStatus = {
    status: string
    google_sheets_connected: boolean
    pilots_loaded: number
    drones_loaded: number
    missions_loaded: number
}

const SUGGESTED_QUERIES = [
    "Show all available pilots",
    "Detect all conflicts",
    "Find pilots for PRJ001",
    "Which drones can fly in Rainy weather?",
    "Show active assignments",
    "Urgent reassignment for Project-A",
    "Calculate cost for pilot P001 for PRJ002",
    "Update Arjun's status to On Leave",
]

function TypingIndicator() {
    return (
        <div className="flex items-center gap-2 p-4">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-sm flex-shrink-0">
                🤖
            </div>
            <div className="glass rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
            </div>
        </div>
    )
}

function StatusBar({ status }: { status: SystemStatus | null }) {
    if (!status) return null
    return (
        <div className="flex items-center gap-4 text-xs">
            <span className={`flex items-center gap-1 ${status.google_sheets_connected ? 'text-emerald-400' : 'text-amber-400'}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${status.google_sheets_connected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                {status.google_sheets_connected ? 'Sheets Synced' : 'CSV Mode'}
            </span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">✈️ {status.pilots_loaded} pilots</span>
            <span className="text-slate-400">🚁 {status.drones_loaded} drones</span>
            <span className="text-slate-400">📋 {status.missions_loaded} missions</span>
        </div>
    )
}

function MessageBubble({ msg }: { msg: Message }) {
    const isUser = msg.role === 'user'
    const [timeStr, setTimeStr] = useState('')

    useEffect(() => {
        setTimeStr(msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
    }, [msg.timestamp])

    return (
        <div className={`flex items-start gap-3 animate-fade-in ${isUser ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 ${isUser
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600'
                : 'bg-gradient-to-br from-cyan-500 to-blue-600'
                }`}>
                {isUser ? '👤' : '🤖'}
            </div>
            <div className={`max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser
                    ? 'bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-tr-sm'
                    : 'glass text-slate-200 rounded-tl-sm'
                    }`}>
                    {isUser ? (
                        <p>{msg.content}</p>
                    ) : (
                        <div className="prose-dark">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                    )}
                </div>
                {timeStr && <span className="text-xs text-slate-600 px-1">{timeStr}</span>}
            </div>
        </div>
    )
}

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '0',
            role: 'assistant',
            content: `👋 **Welcome to Skylark Drones AI Operations Coordinator!**

I'm **SkyBot**, your intelligent drone operations assistant. I can help you with:

- 🧑‍✈️ **Pilot Management** — Query availability, skills, certifications & update statuses
- 🚁 **Drone Fleet** — Check availability, weather compatibility & maintenance status  
- 📋 **Mission Matching** — Find optimal pilot+drone combos for each project
- ⚠️ **Conflict Detection** — Spot double-bookings, budget overruns & weather risks
- 🚨 **Urgent Reassignment** — Handle emergency crew changes instantly

All status updates sync automatically to **Google Sheets**. What would you like to do?`,
            timestamp: new Date(0), // fixed epoch — avoids SSR/CSR hydration mismatch
        }
    ])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [status, setStatus] = useState<SystemStatus | null>(null)
    const [sidebarOpen, setSidebarOpen] = useState(true)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLTextAreaElement>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, isLoading])

    useEffect(() => {
        fetch(`${API_URL}/api/status`)
            .then(r => r.json())
            .then(setStatus)
            .catch(() => setStatus(null))
    }, [])

    const sendMessage = useCallback(async (text: string) => {
        if (!text.trim() || isLoading) return

        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text.trim(),
            timestamp: new Date(),
        }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setIsLoading(true)

        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text.trim(), session_id: sessionId }),
            })

            if (!res.ok) throw new Error(`API error: ${res.status}`)
            const data = await res.json()

            if (!sessionId) setSessionId(data.session_id)

            const assistantMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
                timestamp: new Date(),
            }
            setMessages(prev => [...prev, assistantMsg])

            // Refresh status after write operations
            if (text.toLowerCase().includes('update') || text.toLowerCase().includes('status')) {
                fetch(`${API_URL}/api/status`).then(r => r.json()).then(setStatus).catch(() => { })
            }
        } catch (err: unknown) {
            const errMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `❌ **Connection Error:** Could not reach the backend.\n\nMake sure the FastAPI server is running:\n\`\`\`\ncd backend && uvicorn main:app --reload\n\`\`\``,
                timestamp: new Date(),
            }
            setMessages(prev => [...prev, errMsg])
        } finally {
            setIsLoading(false)
            setTimeout(() => inputRef.current?.focus(), 100)
        }
    }, [isLoading, sessionId])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendMessage(input)
        }
    }

    const clearChat = async () => {
        if (sessionId) {
            await fetch(`${API_URL}/api/chat/${sessionId}`, { method: 'DELETE' }).catch(() => { })
        }
        setSessionId(null)
        setMessages([{
            id: Date.now().toString(),
            role: 'assistant',
            content: '🔄 Conversation cleared. How can I help you with drone operations?',
            timestamp: new Date(),
        }])
    }

    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <div className={`${sidebarOpen ? 'w-72' : 'w-0'} transition-all duration-300 overflow-hidden flex-shrink-0`}>
                <div className="w-72 h-full glass-dark flex flex-col border-r border-blue-900/30">
                    {/* Logo */}
                    <div className="p-5 border-b border-blue-900/20">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-xl">
                                🚁
                            </div>
                            <div>
                                <h1 className="font-bold text-white text-sm leading-tight">Skylark Drones</h1>
                                <p className="text-xs text-blue-400">AI Operations Coordinator</p>
                            </div>
                        </div>
                    </div>

                    {/* Status */}
                    <div className="p-4 border-b border-blue-900/20">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">System Status</p>
                        {status ? (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Google Sheets</span>
                                    <span className={status.google_sheets_connected ? 'text-emerald-400' : 'text-amber-400'}>
                                        {status.google_sheets_connected ? '✓ Connected' : '⚠ CSV Mode'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Pilots</span>
                                    <span className="text-blue-300">{status.pilots_loaded}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Drones</span>
                                    <span className="text-cyan-300">{status.drones_loaded}</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Missions</span>
                                    <span className="text-purple-300">{status.missions_loaded}</span>
                                </div>
                            </div>
                        ) : (
                            <p className="text-xs text-slate-600">Connecting...</p>
                        )}
                    </div>

                    {/* Suggested Queries */}
                    <div className="flex-1 p-4 overflow-y-auto">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">Quick Actions</p>
                        <div className="space-y-1.5">
                            {SUGGESTED_QUERIES.map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => sendMessage(q)}
                                    disabled={isLoading}
                                    className="w-full text-left text-xs px-3 py-2.5 rounded-lg text-slate-300 hover:bg-blue-900/30 hover:text-blue-300 transition-all duration-150 disabled:opacity-50 border border-transparent hover:border-blue-800/40"
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Clear button */}
                    <div className="p-4 border-t border-blue-900/20">
                        <button
                            onClick={clearChat}
                            className="w-full text-xs py-2 px-3 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-900/10 border border-slate-700/40 hover:border-red-800/40 transition-all"
                        >
                            🗑 Clear Conversation
                        </button>
                    </div>
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="glass-dark border-b border-blue-900/20 px-4 py-3 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setSidebarOpen(o => !o)}
                            className="w-8 h-8 rounded-lg hover:bg-blue-900/30 flex items-center justify-center text-slate-400 hover:text-white transition-all"
                        >
                            ☰
                        </button>
                        <div>
                            <h2 className="text-sm font-semibold text-white">SkyBot — Operations Coordinator</h2>
                            <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                <span className="text-xs text-slate-400">Powered by Gemini AI</span>
                            </div>
                        </div>
                    </div>
                    <StatusBar status={status} />
                </header>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
                    {messages.map(msg => (
                        <MessageBubble key={msg.id} msg={msg} />
                    ))}
                    {isLoading && <TypingIndicator />}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="flex-shrink-0 p-4 border-t border-blue-900/20 glass-dark">
                    <div className="flex items-end gap-2 glass rounded-2xl px-4 py-3 glow-blue">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask me about pilots, drones, missions, conflicts... (Enter to send)"
                            disabled={isLoading}
                            rows={1}
                            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 resize-none outline-none max-h-32 leading-relaxed"
                            style={{ minHeight: '24px' }}
                        />
                        <button
                            onClick={() => sendMessage(input)}
                            disabled={isLoading || !input.trim()}
                            className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white hover:from-blue-400 hover:to-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 flex-shrink-0 shadow-lg"
                        >
                            {isLoading ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
                                </svg>
                            )}
                        </button>
                    </div>
                    <p className="text-center text-xs text-slate-700 mt-2">
                        Shift+Enter for new line · All data syncs to Google Sheets
                    </p>
                </div>
            </div>
        </div>
    )
}
