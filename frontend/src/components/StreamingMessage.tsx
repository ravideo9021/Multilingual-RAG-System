import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Clock } from 'lucide-react'
import { cn, langLabel, renderMarkdown, injectSourceChips } from '@/lib/utils'
import type { Message } from '@/types'
import { MessageActions } from './MessageActions'
import { SourcesCollapsible } from './SourcesCollapsible'
import { FollowUpSuggestions } from './FollowUpSuggestions'

interface StreamingMessageProps {
  message: Message
  originalQuery?: string
  onRetry?: () => void
  onFollowUp?: (text: string) => void
}

function LangBadge({ lang }: { lang?: string }) {
  if (!lang) return null
  const label = langLabel(lang)
  if (!label) return null

  return (
    <span
      className={cn(
        'font-mono text-[9px] font-bold px-[7px] py-0.5 rounded-md uppercase tracking-wide',
        lang === 'hi' && 'bg-orange-400/10 text-orange-400',
        lang === 'en' && 'bg-blue-400/10 text-blue-400',
        lang === 'mix' && 'bg-purple-400/10 text-purple-400'
      )}
    >
      {label}
    </span>
  )
}

export function StreamingMessage({ message, originalQuery, onRetry, onFollowUp }: StreamingMessageProps) {
  const bubbleRef = useRef<HTMLDivElement>(null)
  const isUser = message.role === 'user'

  useEffect(() => {
    if (bubbleRef.current && !message.isStreaming && message.role === 'assistant') {
      let html = renderMarkdown(message.content || '*No response received.*')
      if (message.sources?.length) {
        html = injectSourceChips(html, message.sources)
      }
      bubbleRef.current.innerHTML = html
    }
  }, [message.content, message.isStreaming, message.sources, message.role])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn('flex flex-col', isUser ? 'items-end' : 'items-start max-w-[88%]')}
    >
      {/* Header */}
      <div className={cn('flex items-center gap-[7px] mb-1.5', isUser && 'justify-end')}>
        {isUser ? (
          <>
            <LangBadge lang={message.lang} />
            <span className="font-mono text-[10px] font-semibold text-zinc-600 uppercase tracking-wide">You</span>
            <div className="w-[26px] h-[26px] rounded-lg flex items-center justify-center font-mono text-[10px] font-bold text-white bg-gradient-to-br from-accent to-indigo-700">
              Y
            </div>
          </>
        ) : (
          <>
            <div className="w-[26px] h-[26px] rounded-lg flex items-center justify-center font-mono text-[10px] font-bold text-zinc-500 bg-bg-card border border-white/[0.06]">
              AI
            </div>
            <span className="font-mono text-[10px] font-semibold text-zinc-600 uppercase tracking-wide">Assistant</span>
            <LangBadge lang={message.lang} />
          </>
        )}
      </div>

      {/* Bubble */}
      {isUser ? (
        <div className="max-w-[70%] px-[18px] py-3.5 rounded-2xl rounded-br-sm text-sm leading-relaxed bg-gradient-to-br from-indigo-950 to-[#1a1a35] border border-indigo-500/15 text-white">
          {message.content}
        </div>
      ) : (
        <div className="w-full">
          {message.isStreaming ? (
            <div className="text-sm leading-[1.75] text-white bubble-content">
              {/* Word-by-word fade-in (streaming-text) */}
              {message.content.split(/(\s+)/).filter(w => w.trim()).map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="inline"
                >
                  {word}{' '}
                </motion.span>
              ))}
              <span className="stream-cursor" />
            </div>
          ) : (
            <div
              ref={bubbleRef}
              className="text-sm leading-[1.75] text-white bubble-content"
            />
          )}

          {/* Post-stream elements */}
          {!message.isStreaming && message.content && (
            <>
              {onRetry && <MessageActions answer={message.content} onRetry={onRetry} />}
              {message.sources && <SourcesCollapsible sources={message.sources} />}

              {/* Elapsed badge */}
              {message.elapsedMs ? (
                <div className="flex items-center gap-1 mt-1.5 font-mono text-[10px] text-zinc-600 tracking-wide">
                  <Clock size={10} className="opacity-40" />
                  {(message.elapsedMs / 1000).toFixed(1)}s
                </div>
              ) : null}

              {originalQuery && onFollowUp && (
                <FollowUpSuggestions query={originalQuery} onSelect={onFollowUp} />
              )}
            </>
          )}
        </div>
      )}
    </motion.div>
  )
}
