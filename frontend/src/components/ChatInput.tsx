import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Paperclip, ArrowUp, ChevronDown, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MODELS, type ModelOption, type EffortLevel } from '@/types'

const EFFORT_LABELS = ['Low', 'Medium', 'Max Effort'] as const
const EASE_OUT = [0.16, 1, 0.3, 1] as const

interface ChatInputProps {
  onSend: (text: string) => void
  onAttach: () => void
  disabled: boolean
  selectedModel: ModelOption
  onModelChange: (model: ModelOption) => void
}

function DynamicBarsIcon({ level }: { level: string }) {
  const isMediumOrHigh = level === 'Medium' || level === 'Max Effort'
  const isHigh = level === 'Max Effort'
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1.5" y="8" width="2.5" height="4.5" rx="1" fill="currentColor" opacity={1} />
      <rect x="5.75" y="5" width="2.5" height="7.5" rx="1" fill="currentColor" className="transition-opacity duration-300" opacity={isMediumOrHigh ? 1 : 0.3} />
      <rect x="10" y="2" width="2.5" height="10.5" rx="1" fill="currentColor" className="transition-opacity duration-300" opacity={isHigh ? 1 : 0.3} />
    </svg>
  )
}

function MorphingText({ text }: { text: string }) {
  const [width, setWidth] = useState<number | 'auto'>('auto')
  const spanRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (spanRef.current) setWidth(spanRef.current.offsetWidth)
  }, [text])

  return (
    <span
      className="relative inline-flex items-center justify-center overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.175,0.885,0.32,1.275)]"
      style={{ width }}
    >
      <span ref={spanRef} className="invisible whitespace-nowrap px-0.5">{text}</span>
      <span key={text} className="absolute inset-0 flex items-center justify-center whitespace-nowrap" style={{ animation: 'pop-in 250ms cubic-bezier(0.23,1,0.32,1) both' }}>
        {text}
      </span>
    </span>
  )
}

export function ChatInput({ onSend, onAttach, disabled, selectedModel, onModelChange }: ChatInputProps) {
  const [text, setText] = useState('')
  const [effort, setEffort] = useState<EffortLevel>(1)
  const [modelOpen, setModelOpen] = useState(false)
  const [hoverIdx, setHoverIdx] = useState(-1)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const autoGrow = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  useEffect(() => { textareaRef.current?.focus() }, [])

  const cycleEffort = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setEffort(prev => ((prev + 1) % 3) as EffortLevel)
  }, [])

  useEffect(() => {
    if (!modelOpen) return
    const handleOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setModelOpen(false)
      }
    }
    document.addEventListener('mousedown', handleOutside)
    return () => document.removeEventListener('mousedown', handleOutside)
  }, [modelOpen])

  const hasValue = text.trim() !== ''

  return (
    <div className="px-5 pb-5 pt-2" style={{ background: 'linear-gradient(to top, hsl(var(--background)) 60%, transparent)' }}>
      <div
        ref={containerRef}
        className={cn(
          'max-w-[720px] mx-auto rounded-3xl px-4 pt-3 pb-2.5',
          'bg-card border border-border shadow-sm',
          'transition-[border-color,box-shadow] duration-200',
          'focus-within:border-ring/40 focus-within:ring-1 focus-within:ring-ring/20',
        )}
      >
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => { setText(e.target.value); autoGrow() }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask anything in Hindi, English, or Hinglish..."
          className="prompt-scrollbar w-full bg-transparent border-none outline-none text-foreground text-sm leading-[22px] resize-none max-h-[160px] min-h-[28px] px-1 py-1 placeholder:font-medium placeholder:text-muted-foreground/40"
        />

        <div className="flex items-center justify-between mt-2">
          <div className="flex items-center gap-0.5">
            <div className="relative">
              <button
                type="button"
                onMouseDown={e => e.preventDefault()}
                onClick={e => { e.stopPropagation(); setModelOpen(prev => !prev) }}
                className={cn(
                  'group flex items-center gap-1.5 rounded-full px-2.5 py-1 text-foreground/50 transition-all duration-200 outline-none hover:bg-accent/60 hover:text-foreground cursor-default',
                  modelOpen && 'bg-accent/60 text-foreground',
                )}
              >
                <ProviderIcon provider={selectedModel.provider} />
                <span className="text-xs font-semibold select-none">
                  <MorphingText text={selectedModel.name} />
                </span>
                <ChevronDown size={12} className={cn('transition-transform duration-200', modelOpen && 'rotate-180')} />
              </button>

              <AnimatePresence>
                {modelOpen && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 8 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 8 }}
                    transition={{ duration: 0.2, ease: EASE_OUT }}
                    className="absolute bottom-full left-0 mb-2.5 z-50 w-52 rounded-2xl border border-border bg-card/95 p-1 shadow-xl backdrop-blur-md"
                    onMouseLeave={() => setHoverIdx(-1)}
                  >
                    <div className="relative flex flex-col gap-0.5">
                      {hoverIdx >= 0 && (
                        <motion.div
                          layoutId="model-hover"
                          className="absolute left-0 right-0 h-8 rounded-xl bg-accent pointer-events-none"
                          style={{ top: hoverIdx * 34 }}
                          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                        />
                      )}
                      {MODELS.map((model, idx) => (
                        <button
                          key={model.id}
                          type="button"
                          onMouseDown={e => e.preventDefault()}
                          onMouseEnter={() => setHoverIdx(idx)}
                          onClick={e => { e.stopPropagation(); onModelChange(model); setModelOpen(false) }}
                          className="group relative flex h-8 w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-left text-xs font-medium text-foreground/80 outline-none active:scale-[0.98] cursor-default z-10"
                        >
                          <span className="flex items-center gap-2">
                            <ProviderIcon provider={model.provider} />
                            {model.name}
                          </span>
                          {model.id === selectedModel.id && (
                            <Check size={12} className="text-foreground/50" />
                          )}
                        </button>
                      ))}
                    </div>
                    <div className="mt-1 pt-1 border-t border-border px-2.5 pb-1">
                      <span className="text-[10px] text-muted-foreground/50">via OpenRouter API</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <button
              type="button"
              onMouseDown={e => e.preventDefault()}
              onClick={cycleEffort}
              className="group flex items-center gap-1 rounded-full px-2 py-1 text-foreground/50 transition-all duration-200 hover:bg-accent/60 hover:text-foreground outline-none cursor-default"
            >
              <DynamicBarsIcon level={EFFORT_LABELS[effort]} />
              <span className="text-xs font-semibold select-none">
                <MorphingText text={EFFORT_LABELS[effort]} />
              </span>
            </button>

            <button
              type="button"
              onMouseDown={e => e.preventDefault()}
              onClick={e => { e.stopPropagation(); onAttach() }}
              className="flex h-7 w-7 items-center justify-center rounded-full text-foreground/50 transition-all duration-200 hover:bg-accent/60 hover:text-foreground outline-none cursor-default ml-auto"
            >
              <Paperclip size={15} />
            </button>
          </div>

          <motion.button
            whileHover={!disabled && hasValue ? { scale: 1.05 } : undefined}
            whileTap={!disabled && hasValue ? { scale: 0.95 } : undefined}
            onMouseDown={e => { e.preventDefault(); e.stopPropagation() }}
            onClick={handleSend}
            disabled={disabled || !hasValue}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-full transition-all duration-300 outline-none cursor-default',
              disabled || !hasValue
                ? 'bg-muted text-muted-foreground opacity-40 cursor-not-allowed'
                : 'bg-primary text-primary-foreground hover:opacity-90',
            )}
          >
            <ArrowUp size={14} />
          </motion.button>
        </div>
      </div>
    </div>
  )
}

function ProviderIcon({ provider }: { provider: string }) {
  const colors: Record<string, string> = {
    Google: '#4285F4',
    OpenAI: '#10a37f',
    Meta: '#0668E1',
    Mistral: '#F7D046',
    Alibaba: '#FF6A00',
    NVIDIA: '#76B900',
  }
  const color = colors[provider] || '#888'
  return (
    <span
      className="inline-block w-3 h-3 rounded-full shrink-0"
      style={{ background: color }}
    />
  )
}
