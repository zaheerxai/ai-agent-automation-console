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
  <main className="relative min-h-screen bg-[#030712] text-slate-200 selection:bg-emerald-500/30">
    {/* Animated Background Mesh */}
    <div className="absolute inset-0 z-0 overflow-hidden">
      <div className="absolute -top-[10%] -left-[10%] h-[40%] w-[40%] rounded-full bg-emerald-500/5 blur-[120px]" />
      <div className="absolute top-[20%] -right-[10%] h-[30%] w-[30%] rounded-full bg-cyan-500/5 blur-[120px]" />
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150" />
    </div>

    <div className="relative z-10 flex h-screen flex-col">
      {/* 1. Sleek Top Navigation */}
      <header className="flex h-16 items-center justify-between border-b border-white/5 bg-slate-950/20 px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-500 p-1.5 shadow-[0_0_15px_rgba(52,211,153,0.3)]">
            <Workflow className="text-slate-950" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white">MOJO<span className="text-emerald-400">AI</span></span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1 text-[11px] font-medium tracking-wide text-emerald-400 uppercase">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            {latestStatus}
          </div>
          <button className="text-slate-400 hover:text-white transition-colors">
            <TerminalSquare className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* 2. Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left: Collapsible Preset Panel (Optional/Subtle) */}
        <aside className="hidden w-64 flex-col border-r border-white/5 bg-slate-950/10 p-6 lg:flex">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-slate-500">Fast Commands</p>
          <div className="space-y-3">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => setInput(prompt)}
                className="group w-full rounded-xl border border-white/5 bg-white/5 p-3 text-left text-xs text-slate-400 transition-all hover:border-emerald-500/30 hover:bg-emerald-500/5 hover:text-white"
              >
                {prompt}
              </button>
            ))}
          </div>
        </aside>

        {/* Center: The Chat Stage */}
        <section className="relative flex flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-8 scrollbar-hide">
            <div className="mx-auto max-w-3xl space-y-8">
              {transcript.length === 0 ? (
                <div className="flex h-[60vh] flex-col items-center justify-center text-center">
                  <div className="mb-6 rounded-2xl bg-gradient-to-b from-white/10 to-transparent p-6 ring-1 ring-white/10">
                    <Sparkles className="h-10 w-10 text-emerald-400" />
                  </div>
                  <h2 className="text-3xl font-bold text-white">How can Mojo automate today?</h2>
                  <p className="mt-4 max-w-sm text-slate-400">
                    Your direct interface to autonomous n8n workflows through a secured Django relay.
                  </p>
                </div>
              ) : (
                transcript.map((item) => (
                  <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`group relative max-w-[85%] rounded-2xl px-5 py-4 transition-all ${
                      item.role === 'user' 
                        ? 'bg-emerald-500 text-slate-950 shadow-[0_10px_20px_rgba(16,185,129,0.1)]' 
                        : 'bg-white/5 ring-1 ring-white/10 text-slate-200'
                    }`}>
                      <p className="whitespace-pre-wrap text-[15px] leading-relaxed">
                        {item.content}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 3. Immersive Input Bar */}
          <div className="p-6">
            <form 
              onSubmit={handleSubmit}
              className="mx-auto max-w-3xl relative flex items-center gap-2 rounded-2xl border border-white/10 bg-slate-900/50 p-2 backdrop-blur-xl focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10 transition-all"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Message Mojo..."
                className="flex-1 bg-transparent px-4 py-3 text-sm text-white placeholder:text-slate-500 outline-none"
              />
              <button
                disabled={!canSubmit}
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-400 text-slate-950 transition-transform active:scale-95 disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </form>
            <p className="mt-3 text-center text-[10px] text-slate-600">
              Agency Engine v1.0 • Secured via Django Proxy • Powered by n8n
            </p>
          </div>
        </section>
      </div>
    </div>
  </main>
)
}

export default App
