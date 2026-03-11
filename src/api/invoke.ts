const backendBase = (import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function invoke<T = unknown>(cmd: string, args: Record<string, unknown> = {}): Promise<T> {
  const res = await fetch(`${backendBase}/invoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cmd, args }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`invoke ${cmd} failed: ${res.status} ${text}`)
  }

  return (await res.json()) as T
}
