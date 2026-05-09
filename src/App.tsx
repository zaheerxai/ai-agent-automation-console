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
    <main className="min-h-screen overflow-hidden px-5 py-6 sm:px-8 lg:px-10">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(238,242,248,0.045)_1px,transparent_1px),linear-gradient(90deg,rgba(238,242,248,0.045)_1px,transparent_1px)] bg-[size:44px_44px] [mask-image:linear-gradient(to_bottom,black,transparent_82%)]" />

      <section className="relative mx-auto grid min-h-[calc(100vh-3rem)] max-w-7xl gap-6 lg:grid-cols-[0.9fr_1.5fr]">
        <aside className="flex flex-col justify-between rounded-[8px] border border-white/10 bg-white/[0.035] p-6 shadow-2xl shadow-black/30 backdrop-blur">
          <div>
            <div className="mb-10 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-[8px] border border-emerald-300/30 bg-emerald-300/10 text-emerald-200">
                <Workflow className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.28em] text-emerald-200/75">
                  Mojo AI
                </p>
                <h1 className="text-2xl font-semibold text-white">
                  Agent Automation Console
                </h1>
              </div>
            </div>

            <div className="space-y-5">
              <div>
                <p className="mb-2 font-mono text-xs uppercase tracking-[0.24em] text-slate-500">
                  Status
                </p>
                <div className="flex items-center justify-between rounded-[8px] border border-white/10 bg-slate-950/55 px-4 py-3">
                  <span className="flex items-center gap-2 text-sm text-slate-200">
                    <RadioTower className="h-4 w-4 text-cyan-200" />
                    N8N Workflow
                  </span>
                  <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-2.5 py-1 font-mono text-xs text-emerald-200">
                    {latestStatus}
                  </span>
                </div>
              </div>

              <div className="grid gap-3">
                <div className="flex items-start gap-3 rounded-[8px] border border-white/10 bg-white/[0.035] p-4">
                  <TerminalSquare className="mt-0.5 h-4 w-4 text-emerald-200" />
                  <p className="text-sm leading-6 text-slate-300">
                    Ask something from the AI, your input is sent via webhook to the webhook node on n8n
                  </p>
                </div>
                <div className="flex items-start gap-3 rounded-[8px] border border-white/10 bg-white/[0.035] p-4">
                  <ShieldCheck className="mt-0.5 h-4 w-4 text-cyan-200" />
                  <p className="text-sm leading-6 text-slate-300">
                    The input will be then passed to the AI node
                    {/* <span className="font-mono text-slate-100">
                      {' '}
                      
                    </span>
                    . */}
                  </p>
                    <div className="flex items-start gap-3 rounded-[8px] border border-white/10 bg-white/[0.035] p-4">
                  <TerminalSquare className="mt-0.5 h-4 w-4 text-emerald-200" />
                  <p className="text-sm leading-6 text-slate-300">
                    The AI will then respond, the answer is sent and shown in the chat here, through the respond to webhook node 
                  </p>
                 </div>
                   <div className="flex items-start gap-3 rounded-[8px] border border-white/10 bg-white/[0.035] p-4"></div>
                    
                </div>
              </div>
            </div>
          </div>

          <div className="mt-10 border-t border-white/10 pt-5">
            <p className="mb-3 font-mono text-xs uppercase tracking-[0.24em] text-slate-500">
              Prompt presets
            </p>
            <div className="space-y-2">
              {quickPrompts.map((prompt) => (
                <button
                  className="w-full rounded-[8px] border border-white/10 bg-slate-950/35 px-3 py-2.5 text-left text-sm leading-5 text-slate-300 transition hover:border-cyan-200/40 hover:bg-cyan-200/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-cyan-200/40"
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex min-h-[640px] flex-col rounded-[8px] border border-white/10 bg-[#111823]/90 shadow-2xl shadow-black/35">
          <header className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 px-5 py-4 sm:px-6">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-cyan-200/80">
                Live agent channel
              </p>
              <h2 className="mt-1 text-xl font-semibold text-white">
                Submit instructions to n8n
              </h2>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-2 text-sm text-slate-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-200" />
              JSON relay enabled
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-5 py-6 sm:px-6">
            {transcript.length === 0 ? (
              <div className="grid h-full place-items-center py-16 text-center">
                <div className="max-w-md">
                  <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-[8px] border border-cyan-200/25 bg-cyan-200/10 text-cyan-100">
                    <Sparkles className="h-6 w-6" aria-hidden="true" />
                  </div>
                  <h3 className="text-2xl font-semibold text-white">
                    Awaiting first instruction
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-slate-400">
                    Send an operational request and the Django backend will
                    forward it to the configured n8n webhook.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {transcript.map((item) => (
                  <article
                    className={`flex gap-3 ${
                      item.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                    key={item.id}
                  >
                    {item.role === 'agent' && (
                      <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] border border-emerald-300/25 bg-emerald-300/10 text-emerald-100">
                        <Bot className="h-4 w-4" />
                      </div>
                    )}
                    <div
                      className={`max-w-[min(720px,86%)] rounded-[8px] border px-4 py-3 ${
                        item.role === 'user'
                          ? 'border-cyan-200/25 bg-cyan-200/12 text-cyan-50'
                          : item.status === 'error'
                            ? 'border-rose-300/25 bg-rose-300/10 text-rose-50'
                            : 'border-white/10 bg-white/[0.045] text-slate-100'
                      }`}
                    >
                      <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.22em] text-slate-500">
                        {item.role === 'user' ? 'Operator' : 'Agent'}
                      </p>
                      <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-6">
                        {item.content}
                      </pre>
                    </div>
                    {item.role === 'user' && (
                      <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] border border-cyan-200/25 bg-cyan-200/10 text-cyan-100">
                        <UserRound className="h-4 w-4" />
                      </div>
                    )}
                  </article>
                ))}

                {isSubmitting && (
                  <div className="flex items-center gap-3 text-sm text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin text-emerald-200" />
                    <span className="animate-pulse">Agent is writing a response...</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <form
            className="border-t border-white/10 bg-slate-950/45 p-4 sm:p-5"
            onSubmit={handleSubmit}
          >
            {error && (
              <p className="mb-3 rounded-[8px] border border-rose-300/25 bg-rose-300/10 px-3 py-2 text-sm text-rose-100">
                {error}
              </p>
            )}
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="sr-only" htmlFor="agent-message">
                Agent instruction
              </label>
              <input
                className="min-h-12 flex-1 rounded-[8px] border border-white/10 bg-[#0d1117] px-4 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-200/45 focus:ring-2 focus:ring-cyan-200/20"
                disabled={isSubmitting}
                id="agent-message"
                onChange={(event) => setInput(event.target.value)}
                placeholder="Describe the workflow task to run..."
                type="text"
                value={input}
              />
              <button
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[8px] border border-emerald-200/30 bg-emerald-200 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-200/45 disabled:border-slate-700 disabled:bg-slate-800 disabled:text-slate-500"
                disabled={!canSubmit}
                type="submit"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Submit
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  )
}

export default App
