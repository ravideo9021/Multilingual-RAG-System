import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

export function renderMarkdown(text: string): string {
  if (!text) return ''
  let h = escapeHtml(text)
  h = h.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _l, c) => '<pre><code>' + c.trim() + '</code></pre>')
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>')
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>')
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  h = h.replace(/^- (.+)$/gm, '<li>$1</li>')
  h = h.replace(/\n\n/g, '</p><p>')
  h = h.replace(/\n/g, '<br>')
  h = '<p>' + h + '</p>'
  h = h.replace(/<p><\/p>/g, '')
  h = h.replace(/<p>(<h[123]>)/g, '$1')
  h = h.replace(/(<\/h[123]>)<\/p>/g, '$1')
  h = h.replace(/<p>(<pre>)/g, '$1')
  h = h.replace(/(<\/pre>)<\/p>/g, '$1')
  return h
}

export function injectSourceChips(html: string, sources: { source?: string; title?: string }[]): string {
  return html.replace(/\[(\d+)\]/g, (match, num) => {
    const idx = parseInt(num) - 1
    if (idx >= 0 && idx < sources.length) {
      const name = escapeHtml(sources[idx].source || sources[idx].title || 'Source ' + num)
      return `<span class="source-chip" title="${name}">${num}</span>`
    }
    return match
  })
}

export function detectLang(text: string): 'hi' | 'en' | 'mix' | '' {
  let dev = 0, lat = 0
  for (const c of text) {
    const code = c.charCodeAt(0)
    if (code >= 0x0900 && code <= 0x097F) dev++
    else if ((code >= 65 && code <= 90) || (code >= 97 && code <= 122)) lat++
  }
  const total = dev + lat
  if (!total) return ''
  if (dev / total > 0.5) return 'hi'
  if (lat / total > 0.8) return 'en'
  return 'mix'
}

export function langLabel(l: string): string {
  return { hi: 'Hindi', en: 'English', mix: 'Hinglish' }[l] || ''
}

export const ease = [0.25, 0.1, 0.25, 1] as const
export const spring = { type: 'spring' as const, stiffness: 300, damping: 30 }
export const springBouncy = { type: 'spring' as const, stiffness: 250, damping: 22, mass: 0.8 }
