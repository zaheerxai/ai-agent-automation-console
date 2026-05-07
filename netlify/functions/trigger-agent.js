export default async (req) => {
  const { message } = await req.json()

  if (!message?.trim()) {
    return Response.json({ message: 'Message is required' }, { status: 400 })
  }

  const webhookUrl = process.env.N8N_WEBHOOK_URL
  if (!webhookUrl) {
    return Response.json({ message: 'System busy' }, { status: 503 })
  }

  try {
    const n8nRes = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })

    const text = await n8nRes.text()
    const response = text ? JSON.parse(text) : { message: 'Webhook received' }
    return Response.json({ status: 'ok', response })
  } catch {
    return Response.json({ message: 'System busy' }, { status: 503 })
  }
}

export const config = { path: '/api/trigger-agent' }