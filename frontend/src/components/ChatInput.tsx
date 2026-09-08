import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Paperclip, Mic, ArrowUp, Sparkles } from 'lucide-react'
import { cn, springBouncy } from '@/lib/utils'
import type { EffortLevel } from '@/types'

const EFFORT_LABELS = ['Concise', 'Balanced', 'Detailed'] as const

interface ChatInputProps {
  onSend: (text: string) => void
  onAttach: () => void
  disabled: boolean
  modelName: string
}

export function ChatInput({ onSend, onAttach, disabled, modelName }: ChatInputProps) {
  const [text, setText] = useState('')
  const [effort, setEffort] = useState<EffortLevel>(2)
  const [isRecording, setIsRecording] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
    el.style.height = Math.min(el.scrollHeight, 140) + 'px'
  }

  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const cycleEffort = () => {
    setEffort(prev => ((prev + 1) % 3) as EffortLevel)
  }

  return (
    <div className="px-6 pb-4 pt-2" style={{ background: 'linear-gradient(to top, hsl(var(--background)) 60%, transparent)' }}>
      <motion.div
        layout
        className={cn(
          'max-w-[720px] mx-auto rounded-2xl px-4 pt-2.5 pb-2 transition-shadow',
          'bg-card border border-border',
          'focus-within:border-foreground/20 focus-within:shadow-[0_0_0_2px_hsl(var(--ring)/0.08)]'
        )}
      >
        <div className="flex items-center gap-1.5 mb-1.5 px-0.5">
          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-secondary border border-border font-mono text-[10px] font-semibold text-muted-foreground tracking-wide">
            <Sparkles size={10} className="text-warm opacity-70" />
            <span>{modelName}</span>
          </div>

          <motion.button
            whileTap={{ scale: 0.95 }}
            transition={springBouncy}
            onClick={cycleEffort}
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-md border font-mono text-[10px] font-medium cursor-pointer transition-colors',
              effort === 2
                ? 'text-warm border-warm/20 bg-secondary'
                : 'text-muted-foreground border-border bg-secondary hover:text-foreground'
            )}
          >
            <DynamicBars level={effort} />
            <span>{EFFORT_LABELS[effort]}</span>
          </motion.button>
        </div>

        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => { setText(e.target.value); autoGrow() }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask anything in Hindi, English, or Hinglish..."
          className="w-full bg-transparent border-none outline-none text-foreground text-sm leading-relaxed resize-none max-h-[140px] min-h-[24px] px-1 py-0 placeholder:text-muted-foreground/40"
        />

        <div className="flex items-center justify-between mt-1.5 px-0.5">
          <div className="flex items-center gap-0.5">
            <InputIconButton onClick={onAttach} tooltip="Attach file">
              <Paperclip size={16} />
            </InputIconButton>
            <InputIconButton
              onClick={() => setIsRecording(!isRecording)}
              tooltip="Voice input"
              active={isRecording}
            >
              <Mic size={16} />
            </InputIconButton>
          </div>

          <motion.button
            whileHover={!disabled ? { scale: 1.06 } : undefined}
            whileTap={!disabled ? { scale: 0.94 } : undefined}
            transition={springBouncy}
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer transition-all',
              disabled || !text.trim()
                ? 'bg-muted opacity-30 cursor-not-allowed'
                : 'bg-foreground text-background hover:bg-foreground/90'
            )}
          >
            <ArrowUp size={16} />
          </motion.button>
        </div>
      </motion.div>
    </div>
  )
}

function DynamicBars({ level }: { level: number }) {
  return (
    <div className="flex items-end gap-[1.5px] h-2.5">
      {[4, 7, 10].map((h, i) => (
        <motion.span
          key={i}
          animate={{ opacity: i <= level ? 1 : 0.25, height: h }}
          transition={springBouncy}
          className="w-[2.5px] rounded-sm bg-current"
        />
      ))}
    </div>
  )
}

function InputIconButton({
  children,
  onClick,
  tooltip,
  active,
}: {
  children: React.ReactNode
  onClick: () => void
  tooltip: string
  active?: boolean
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      transition={springBouncy}
      onClick={onClick}
      title={tooltip}
      className={cn(
        'flex items-center justify-center w-7 h-7 rounded-md bg-transparent border-none cursor-pointer transition-colors',
        active
          ? 'text-red-400'
          : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
      )}
    >
      {children}
    </motion.button>
  )
}
