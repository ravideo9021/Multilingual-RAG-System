import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Paperclip, Mic, ArrowRight, Sun, BarChart3 } from 'lucide-react'
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
    <div className="px-8 pb-5 pt-3" style={{ background: 'linear-gradient(to top, #09090b 60%, transparent)' }}>
      <motion.div
        layout
        className={cn(
          'max-w-[720px] mx-auto rounded-3xl px-4 pt-2.5 pb-2 transition-shadow',
          'bg-bg-input border border-white/[0.06]',
          'focus-within:border-indigo-500/30 focus-within:shadow-[0_0_0_3px_rgba(99,102,241,0.12),0_-4px_32px_rgba(0,0,0,0.2)]'
        )}
        style={{ boxShadow: '0 -4px 24px rgba(0,0,0,0.15)' }}
      >
        {/* Top row: model pill + effort toggle (ai-chat-input) */}
        <div className="flex items-center gap-1.5 mb-1.5 px-0.5">
          {/* Model indicator pill */}
          <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-bg-card border border-white/[0.06] font-mono text-[10px] font-semibold text-zinc-500 tracking-wide">
            <Sun size={10} className="opacity-50" />
            <span>{modelName}</span>
          </div>

          {/* Effort level toggle with animated bars (ai-chat-input) */}
          <motion.button
            whileTap={{ scale: 0.95 }}
            transition={springBouncy}
            onClick={cycleEffort}
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-lg border font-mono text-[10px] font-medium cursor-pointer transition-colors',
              effort === 2
                ? 'text-indigo-400 border-indigo-500/20 bg-bg-card'
                : 'text-zinc-600 border-white/[0.06] bg-bg-card hover:text-zinc-500'
            )}
          >
            <div className="flex items-end gap-[1px] h-2.5">
              {[4, 7, 10].map((h, i) => (
                <motion.span
                  key={i}
                  animate={{
                    opacity: i <= effort ? 1 : 0.3,
                    height: h,
                  }}
                  transition={springBouncy}
                  className="w-[3px] rounded-sm bg-current"
                />
              ))}
            </div>
            <span>{EFFORT_LABELS[effort]}</span>
          </motion.button>
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={e => { setText(e.target.value); autoGrow() }}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask anything in Hindi, English, or Hinglish..."
          className="w-full bg-transparent border-none outline-none text-white text-sm font-sans leading-relaxed resize-none max-h-[140px] min-h-[24px] px-1 py-0 placeholder:text-zinc-600"
        />

        {/* Bottom row: actions (ai-chat-input) */}
        <div className="flex items-center justify-between mt-1.5 px-0.5">
          <div className="flex items-center gap-0.5">
            {/* Attach button */}
            <InputIconButton onClick={onAttach} tooltip="Attach file">
              <Paperclip size={16} />
            </InputIconButton>

            {/* Voice button with recording state */}
            <InputIconButton
              onClick={() => setIsRecording(!isRecording)}
              tooltip="Voice input"
              active={isRecording}
            >
              <Mic size={16} />
            </InputIconButton>
          </div>

          {/* Send button with spring animation */}
          <motion.button
            whileHover={!disabled ? { scale: 1.06 } : undefined}
            whileTap={!disabled ? { scale: 0.94 } : undefined}
            transition={springBouncy}
            onClick={handleSend}
            disabled={disabled || !text.trim()}
            className={cn(
              'w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all',
              disabled || !text.trim()
                ? 'bg-accent/20 opacity-20 cursor-not-allowed'
                : 'bg-accent text-white hover:bg-accent-hover hover:shadow-lg hover:shadow-indigo-500/25'
            )}
          >
            <ArrowRight size={16} />
          </motion.button>
        </div>
      </motion.div>
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
        'flex items-center justify-center w-8 h-8 rounded-[10px] bg-transparent border-none cursor-pointer transition-colors',
        active
          ? 'text-red-400 animate-pulse-dot'
          : 'text-zinc-600 hover:bg-bg-card hover:text-zinc-400'
      )}
    >
      {children}
    </motion.button>
  )
}
