import type { HealthData, StatsData, SourceHit } from '@/types'

const API_BASE = import.meta.env.DEV ? '' : ''

export async function fetchHealth(): Promise<HealthData> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function fetchStats(): Promise<StatsData> {
  const res = await fetch(`${API_BASE}/stats`)
  if (!res.ok) throw new Error('Stats fetch failed')
  return res.json()
}

export async function ingestFile(file: File): Promise<{ filename: string; chunks: number }> {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error('Ingest failed: ' + res.status)
  return res.json()
}

export interface StreamCallbacks {
  onSources: (sources: SourceHit[]) => void
  onToken: (token: string) => void
  onError: (error: string) => void
  onDone: (elapsedMs: number) => void
}

export async function streamQuery(query: string, callbacks: StreamCallbacks): Promise<void> {
  const resp = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 5 }),
  })
  if (!resp.ok) throw new Error('HTTP ' + resp.status)

  const reader = resp.body!.getReader()
  const dec = new TextDecoder()
  let buf = ''
  let evt = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop()!

    for (const line of lines) {
      if (line.startsWith('event:')) {
        evt = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        const d = line.slice(5).trim()
        if (evt === 'sources') {
          try { callbacks.onSources(JSON.parse(d)) } catch {}
        } else if (evt === 'token') {
          callbacks.onToken(d)
        } else if (evt === 'error') {
          callbacks.onError(d)
        } else if (evt === 'done') {
          try {
            const meta = JSON.parse(d)
            callbacks.onDone(meta.elapsed_ms || 0)
          } catch {
            callbacks.onDone(0)
          }
        }
      }
    }
  }
}
