import { FormEvent, useMemo, useState, useEffect, useRef } from 'react'
import {
  Bot,
  Loader2,
  Send,
  Sparkles,
  Cpu,
  Terminal,
  Workflow,
  Globe,
  ChevronRight,
  Activity,
  RadioTower,
  Layers,
  CheckCircle2,
  ShieldCheck,
  TerminalSquare,
  UserRound
} from 'lucide-react'

type AgentResponse = {
  response?: unknown
  message?: string
  status?: string
  error?: string
}

type TranscriptItem = {
  id: string
  role: 'user' | 'agent'
  content: string
  status?: 'ok' | 'error'
}

const quickPrompts = [
  'Help me draft a follow-up email to my last client.',
  'Summarize my agenda and tasks for today.',
  'Analyze the latest CRM data and give me insights.',
]

function formatResponse(payload: AgentResponse) {
  const value = payload.response ?? payload.message ?? payload.error ?? payload

  if (typeof value === 'string') {
    return value
  }

  return JSON.stringify(value, null, 2)
}

function App() {
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [transcript, setTranscript] = useState<TranscriptItem[]>([])
  
  // NEW: This helps the app "see" the chat window to scroll it
  const scrollRef = useRef<HTMLDivElement>(null)

  const canSubmit = input.trim().length > 0 && !isSubmitting
  
  const latestStatus = useMemo(() => {
    if (isSubmitting) return 'Dispatching'
    if (transcript.some((item) => item.status === 'error')) return 'Attention'
    return 'Ready'
  }, [isSubmitting, transcript])

  // NEW: This automatically scrolls the chat down when a new message arrives
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcript, isSubmitting])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const message = input.trim()
    if (!message) {
      return
    }

    setError('')
    setInput('')
    setIsSubmitting(true)

    const userItem: TranscriptItem = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
    }
    setTranscript((items) => [...items, userItem])
  
    
    const API_URL = '/api/trigger-agent/'; 

    try {
      const response = await fetch(API_URL, { 
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }), 
      });

      const text = await response.text()
      let data: any = {} // Changed from AgentResponse to 'any' temporarily for parsing
      
      try {
        data = JSON.parse(text)
      } catch {
        data = { message: text.trim() || 'System busy' }
      }

      if (!response.ok) {
        throw new Error(data.message || data.error || 'System busy')
      }

      // --- THE NEW TWEAK: Unpack Django's wrapper ---
      // If Django returns {"status": "ok", "response": {...}}, extract the inner response
      const finalData: AgentResponse = (data.status === 'ok' && data.response) 
        ? data.response 
        : data;
      // ----------------------------------------------

      setTranscript((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: 'agent',
          content: formatResponse(finalData), // Pass the unwrapped data here
          status: 'ok',
        },
      ])
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : 'System busy'
      setError(message)
      setTranscript((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: 'agent',
          content: message,
          status: 'error',
        },
      ])
    } finally {
      setIsSubmitting(false)
    }
  }

return (
    <main className="relative min-h-screen bg-[#030711] text-slate-300 font-sans selection:bg-emerald-500/30 overflow-hidden">
      
      {/* 1. BACKGROUND LAYER (Glassmorphism & Gradients Preserved) */}
      <div className="pointer-events-none fixed inset-0 z-0 bg-[linear-gradient(rgba(16,185,129,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.05)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
      <div className="absolute top-[-10%] left-[-10%] h-[500px] w-[500px] rounded-full bg-emerald-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] h-[500px] w-[500px] rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" />

      {/* 2. MAIN INTERFACE CONTENT */}
      <div className="relative z-10 flex h-screen flex-col p-4 lg:p-6">
        <div className="mx-auto w-full max-w-7xl flex flex-1 gap-6 overflow-hidden">
          
          {/* SIDEBAR: Client-Facing Branding & Value Props */}
          <aside className="hidden w-80 flex-col gap-4 lg:flex">
            <div className="flex flex-col h-full rounded-2xl border border-white/5 bg-white/[0.02] p-6 backdrop-blur-xl">
              
              <div>
                <div className="mb-10 flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.15)]">
                    <Workflow className="h-5 w-5" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold tracking-tight text-white">MOJO <span className="text-emerald-400">AI</span></h1>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-emerald-400/60">Digital Assistant</p>
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-slate-500">System Health</p>
                    <div className="flex items-center justify-between rounded-xl border border-white/5 bg-slate-950/40 p-3 backdrop-blur-sm">
                      <span className="flex items-center gap-2 text-sm text-slate-300">
                        <Activity className="h-4 w-4 text-cyan-400" />
                        Intelligence Core
                      </span>
                      <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400 uppercase">
                        <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                        {latestStatus}
                      </span>
                    </div>
                  </div>

                  <div className="grid gap-3">
                    <div className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
                      <Bot className="mt-0.5 h-4 w-4 text-emerald-400" />
                      <p className="text-sm leading-relaxed text-slate-400">
                        Your dedicated AI workspace. Simply describe what you need, and Mojo will handle the heavy lifting.
                      </p>
                    </div>
                    <div className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
                      <Layers className="mt-0.5 h-4 w-4 text-cyan-400" />
                      <p className="text-sm leading-relaxed text-slate-400">
                        Seamlessly connected to your data. Ask questions, generate insights, and automate your daily tasks.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* QUICK ACTIONS */}
              <div className="mt-auto pt-6 border-t border-white/5">
                <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-slate-500">Suggested Actions</p>
                <div className="space-y-2">
                  {quickPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => setInput(prompt)}
                      className="group flex w-full items-start gap-3 rounded-xl border border-transparent bg-white/5 p-3 text-left transition-all hover:border-emerald-400/20 hover:bg-emerald-400/5"
                    >
                      <ChevronRight className="mt-1 h-3 w-3 shrink-0 text-slate-500 transition-colors group-hover:text-emerald-400" />
                      <span className="text-xs leading-relaxed text-slate-400 group-hover:text-white">{prompt}</span>
                    </button>
                  ))}
                </div>
              </div>

            </div>
          </aside>

          {/* CHAT WINDOW: The Product Experience */}
          <section className="flex flex-1 flex-col rounded-3xl border border-white/10 bg-slate-950/40 shadow-2xl backdrop-blur-2xl overflow-hidden ring-1 ring-white/5">
            
            <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 px-6 py-4 bg-white/[0.01]">
              <div className="flex items-center gap-3">
                <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <h2 className="text-sm font-medium text-white tracking-wide">
                  Secure Conversation
                </h2>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-white/5 bg-white/[0.02] px-3 py-1.5 text-xs text-slate-400 font-mono">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400/70" />
                Privacy Enhanced
              </div>
            </header>

            <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-8 space-y-8 scroll-smooth scrollbar-hide">
              {transcript.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center text-center opacity-80">
                  <div className="relative mb-6">
                    <div className="absolute inset-0 animate-ping rounded-full bg-emerald-400/20" />
                    <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/20 bg-emerald-400/10 text-emerald-400">
                      <Sparkles className="h-8 w-8" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-semibold text-white tracking-tight">How can I help you today?</h3>
                  <p className="max-w-sm text-sm text-slate-400 mt-3 leading-relaxed">
                    Ask me to analyze data, schedule a task, or answer questions about your current projects.
                  </p>
                </div>
              ) : (
                transcript.map((item) => (
                  <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-5 py-4 transition-all ${
                      item.role === 'user' 
                        ? 'bg-slate-900 border border-white/10 text-white shadow-xl' 
                        : item.status === 'error'
                          ? 'bg-rose-500/10 border border-rose-500/20 text-rose-200'
                          : 'bg-white/5 border border-white/5 text-slate-200'
                    }`}>
                      <p className="font-mono text-[10px] uppercase tracking-widest mb-2 opacity-50 flex items-center gap-2">
                        {item.role === 'user' ? <UserRound className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
                        {item.role === 'user' ? 'You' : 'Mojo AI'}
                      </p>
                      <pre className="whitespace-pre-wrap font-sans text-[14px] leading-relaxed">
                        {item.content}
                      </pre>
                    </div>
                  </div>
                ))
              )}
              
              {isSubmitting && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-5 py-4 bg-white/5 border border-white/5 text-slate-200">
                    <div className="flex items-center gap-3 text-sm text-slate-400">
                      <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
                      <span className="animate-pulse">Mojo is thinking...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 bg-gradient-to-t from-slate-950 to-transparent">
              <form onSubmit={handleSubmit} className="relative mx-auto max-w-4xl">
                {error && (
                  <div className="absolute bottom-full mb-4 w-full rounded-lg border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200 backdrop-blur-md">
                    {error}
                  </div>
                )}
                <div className="group relative flex items-center rounded-2xl border border-white/10 bg-slate-900/90 p-2 transition-all focus-within:border-emerald-400/40 focus-within:ring-4 focus-within:ring-emerald-400/5">
                  <input
                    disabled={isSubmitting}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Message Mojo AI..."
                    className="flex-1 bg-transparent px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none"
                  />
                  <button
                    disabled={!canSubmit}
                    className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-400 text-slate-950 transition-all hover:scale-105 active:scale-95 disabled:opacity-20 disabled:grayscale"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </div>
              </form>
              <div className="mt-4 flex justify-center gap-6 font-mono text-[10px] uppercase tracking-widest text-slate-600">
                <span>Powered by Mojo AI</span>
              </div>
            </div>
          </section>

        </div>
      </div>
    </main>
  )
}

export default App
