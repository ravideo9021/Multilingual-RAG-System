import { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Clock } from 'lucide-react'
import { cn, langLabel, renderMarkdown, injectSourceChips, ease } from '@/lib/utils'
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
        'text-[10px] font-semibold px-2 py-0.5 rounded-lg uppercase tracking-wide',
        lang === 'hi' && 'bg-orange-400/10 text-orange-400/80',
        lang === 'en' && 'bg-blue-400/10 text-blue-400/80',
        lang === 'mix' && 'bg-purple-400/10 text-purple-400/80'
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
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease }}
      className={cn('flex flex-col', isUser ? 'items-end' : 'items-start max-w-[88%]')}
    >
      <div className={cn('flex items-center gap-2 mb-2', isUser && 'justify-end')}>
        {isUser ? (
          <>
            <LangBadge lang={message.lang} />
            <span className="text-[11px] font-medium text-muted-foreground">You</span>
            <div className="w-7 h-7 rounded-xl flex items-center justify-center text-[10px] font-bold text-background bg-foreground">
              Y
            </div>
          </>
        ) : (
          <>
            <div className="w-7 h-7 rounded-xl flex items-center justify-center text-[10px] font-bold text-primary bg-card border border-border">
              AI
            </div>
            <span className="text-[11px] font-medium text-muted-foreground">Assistant</span>
            <LangBadge lang={message.lang} />
          </>
        )}
      </div>

      {isUser ? (
        <div className="max-w-[75%] px-5 py-3.5 rounded-2xl rounded-br-lg text-[15px] leading-relaxed bg-card border border-border text-foreground">
          {message.content}
        </div>
      ) : (
        <div className="w-full">
          {message.isStreaming ? (
            <div className="text-[15px] leading-[1.8] text-foreground/85 bubble-content">
              {message.content.split(/(\s+)/).filter(w => w.trim()).map((word, i) => (
                <motion.span
                  key={i}
                  initial={{ opacity: 0, filter: 'blur(4px)' }}
                  animate={{ opacity: 1, filter: 'blur(0px)' }}
                  transition={{ duration: 0.3, ease }}
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
              className="text-[15px] leading-[1.8] text-foreground/85 bubble-content"
            />
          )}

          {!message.isStreaming && message.content && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15, duration: 0.4, ease }}
            >
              {onRetry && <MessageActions answer={message.content} onRetry={onRetry} />}
              {message.sources && <SourcesCollapsible sources={message.sources} />}

              {message.elapsedMs ? (
                <div className="flex items-center gap-1.5 mt-2 text-[11px] text-muted-foreground/40">
                  <Clock size={11} />
                  {(message.elapsedMs / 1000).toFixed(1)}s
                </div>
              ) : null}

              {originalQuery && onFollowUp && (
                <FollowUpSuggestions query={originalQuery} onSelect={onFollowUp} />
              )}
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  )
}
