import { FormEvent, useMemo, useState } from 'react'
import {
  Bot,
  CheckCircle2,
  Loader2,
  RadioTower,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  UserRound,
  Workflow,
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
  'Summarize today\'s queued automation runs.',
  'Trigger the lead enrichment workflow for pending CRM records.',
  'Check failed invoice sync jobs and suggest the next action.',
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

  const canSubmit = input.trim().length > 0 && !isSubmitting
  const latestStatus = useMemo(() => {
    if (isSubmitting) {
      return 'Dispatching'
    }

    if (transcript.some((item) => item.status === 'error')) {
      return 'Attention'
    }

    return 'Ready'
  }, [isSubmitting, transcript])

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
  <main className="min-h-screen overflow-hidden px-4 py-4 sm:px-6 lg:px-8 bg-[#020617]">
    {/* YOUR FAVORITE GRID BACKGROUND - PRESERVED */}
    <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(238,242,248,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(238,242,248,0.03)_1px,transparent_1px)] bg-[size:44px_44px] [mask-image:linear-gradient(to_bottom,black,transparent_90%)]" />

    <section className="relative mx-auto flex h-[calc(100vh-2rem)] max-w-[1600px] gap-4">
      
      {/* 1. LEFT SIDEBAR: THE CONTROL PANEL */}
      <aside className="hidden w-80 flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-xl lg:flex">
        <div>
          {/* LOGO & HEADING - PRESERVED & POLISHED */}
          <div className="mb-12 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-400/30 bg-emerald-400/10 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.15)]">
              <Workflow className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">MOJO <span className="text-emerald-400">AI</span></h1>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-emerald-400/60">Agency Engine v1.0</p>
            </div>
          </div>

          {/* STATUS CARDS: THE "TRANSPARENT/OPAQUE" FEEL */}
          <div className="space-y-6">
            <div>
              <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-slate-500">System Vitality</p>
              <div className="rounded-xl border border-white/5 bg-slate-950/40 p-4 backdrop-blur-sm">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-slate-400">Relay Status</span>
                  <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                    <div className="h-1 w-1 animate-pulse rounded-full bg-emerald-400" />
                    {latestStatus}
                  </span>
                </div>
                <div className="h-1 w-full rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full w-full bg-emerald-400/40 animate-pulse" />
                </div>
              </div>
            </div>

            {/* PRESET PROMPTS: OPAQUE BUTTONS ON TRANSPARENT BASE */}
            <div className="space-y-2">
              <p className="mb-3 font-mono text-[10px] uppercase tracking-widest text-slate-500">Quick Actions</p>
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  className="w-full rounded-xl border border-white/5 bg-white/[0.03] px-4 py-3 text-left text-xs text-slate-400 transition-all hover:border-emerald-400/30 hover:bg-emerald-400/5 hover:text-white"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* BOTTOM TECH INFO: RELEGATED TO SECONDARY VIEW */}
        <div className="pt-6 border-t border-white/5 text-[11px] text-slate-500 font-mono leading-relaxed">
          <div className="flex items-center gap-2 mb-2">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400/50" />
            <span>SECURE DJANGO PROXY</span>
          </div>
          <p>Handshake active via /api/trigger-agent/</p>
        </div>
      </aside>

      {/* 2. MAIN CHAT AREA: THE HERO COMPONENT */}
      <section className="flex flex-1 flex-col rounded-2xl border border-white/10 bg-slate-950/20 shadow-2xl backdrop-blur-md overflow-hidden">
        
        {/* CHAT HEADER */}
        <header className="flex h-16 items-center justify-between border-b border-white/5 px-6 bg-white/[0.01]">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono uppercase tracking-widest text-slate-400 font-bold">Encrypted Session</span>
          </div>
          <button className="text-slate-500 hover:text-white transition-colors">
            <TerminalSquare className="h-4 w-4" />
          </button>
        </header>

        {/* MESSAGES AREA */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
          {transcript.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center opacity-40">
              <Sparkles className="h-12 w-12 text-emerald-400 mb-4" />
              <h3 className="text-xl font-medium text-white">Initialize Mojo AI</h3>
              <p className="max-w-xs text-sm text-slate-400 mt-2">Send an operational command to trigger your n8n workflow cluster.</p>
            </div>
          ) : (
            transcript.map((item) => (
              <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`relative max-w-[80%] rounded-2xl p-4 transition-all ${
                  item.role === 'user' 
                    ? 'bg-emerald-500 text-slate-950 font-medium shadow-[0_10px_30px_rgba(16,185,129,0.15)]' 
                    : item.status === 'error'
                      ? 'bg-rose-500/10 border border-rose-500/20 text-rose-200'
                      : 'bg-white/[0.04] border border-white/10 text-slate-100 backdrop-blur-sm'
                }`}>
                  <p className="font-mono text-[9px] uppercase tracking-[0.2em] mb-2 opacity-60">
                    {item.role === 'user' ? 'Operator' : 'Mojo Agent'}
                  </p>
                  <pre className="whitespace-pre-wrap break-words font-sans text-[14px] leading-relaxed">
                    {item.content}
                  </pre>
                </div>
              </div>
            ))
          )}
          {isSubmitting && (
            <div className="flex items-center gap-3 text-xs text-emerald-400/70 font-mono tracking-tight">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span className="animate-pulse italic">AGENCY_THINKING_PROMPT...</span>
            </div>
          )}
        </div>

        {/* INPUT BAR: FLOATING OPAQUE STYLE */}
        <div className="p-6 bg-gradient-to-t from-slate-950/60 to-transparent">
          <form onSubmit={handleSubmit} className="relative mx-auto max-w-4xl">
            {error && (
              <div className="absolute bottom-full mb-4 w-full rounded-lg border border-rose-500/20 bg-rose-500/10 px-4 py-2 text-xs text-rose-200 backdrop-blur-md">
                {error}
              </div>
            )}
            <div className="group relative flex items-center rounded-2xl border border-white/10 bg-slate-900/80 p-1.5 transition-all focus-within:border-emerald-400/40 focus-within:ring-4 focus-within:ring-emerald-400/5">
              <input
                disabled={isSubmitting}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Submit instruction to n8n bridge..."
                className="flex-1 bg-transparent px-4 py-3 text-sm text-white placeholder:text-slate-600 outline-none"
              />
              <button
                disabled={!canSubmit}
                className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-400 text-slate-950 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-30 disabled:grayscale"
              >
                {isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </div>
          </form>
        </div>
      </section>
    </section>
  </main>
)

}

export default App
