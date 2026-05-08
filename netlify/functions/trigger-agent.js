export default async (req) => {
  try {
    const { message } = await req.json()

    if (!message?.trim()) {
      return Response.json({ message: 'Message is required' }, { status: 400 })
    }

    const webhookUrl = process.env.N8N_WEBHOOK_URL
    if (!webhookUrl) {
      return Response.json({ message: 'System busy' }, { status: 503 })
    }

    const n8nRes = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 'User message': message }),
    })

    const text = await n8nRes.text()
    const response = text.trim() ? JSON.parse(text) : { message: 'Webhook received' }
    return Response.json({ status: 'ok', response })

  } catch (err) {
    return Response.json({ message: 'System busy' }, { status: 503 })
  }
}