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
      <div className={cn('flex items-center gap-[7px] mb-1.5', isUser && 'justify-end')}>
        {isUser ? (
          <>
            <LangBadge lang={message.lang} />
            <span className="font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.08em]">You</span>
            <div className="w-6 h-6 rounded-md flex items-center justify-center font-mono text-[10px] font-bold text-background bg-foreground">
              Y
            </div>
          </>
        ) : (
          <>
            <div className="w-6 h-6 rounded-md flex items-center justify-center font-mono text-[10px] font-bold text-warm bg-secondary border border-border">
              AI
            </div>
            <span className="font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-[0.08em]">Assistant</span>
            <LangBadge lang={message.lang} />
          </>
        )}
      </div>

      {isUser ? (
        <div className="max-w-[70%] px-4 py-3 rounded-2xl rounded-br-sm text-sm leading-relaxed bg-secondary border border-border text-foreground">
          {message.content}
        </div>
      ) : (
        <div className="w-full">
          {message.isStreaming ? (
            <div className="text-sm leading-[1.75] text-foreground/90 bubble-content">
              {message.content.split(/(\s+)/).filter(w => w.trim()).map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, filter: 'blur(4px)' }}
                  animate={{ opacity: 1, filter: 'blur(0px)' }}
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
              className="text-sm leading-[1.75] text-foreground/90 bubble-content"
            />
          )}

          {!message.isStreaming && message.content && (
            <>
              {onRetry && <MessageActions answer={message.content} onRetry={onRetry} />}
              {message.sources && <SourcesCollapsible sources={message.sources} />}

              {message.elapsedMs ? (
                <div className="flex items-center gap-1 mt-1.5 font-mono text-[10px] text-muted-foreground/50 tracking-wide">
                  <Clock size={10} />
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
