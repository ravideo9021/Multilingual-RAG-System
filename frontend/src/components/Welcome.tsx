import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { ease } from '@/lib/utils'

interface WelcomeProps {
  onChipClick: (text: string) => void
}

const CHIPS = [
  { text: 'भारत की राजधानी क्या है?', label: 'Hindi' },
  { text: 'Tell me about the Taj Mahal', label: 'English' },
  { text: 'ISRO ke baare mein batao', label: 'Hinglish' },
  { text: 'Summarize my documents', label: 'Action' },
]

export function Welcome({ onChipClick }: WelcomeProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.6, ease }}
      className="flex-1 flex flex-col items-center justify-center gap-8 px-6 py-12"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.1, ease }}
        className="flex flex-col items-center gap-4"
      >
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 5, ease: 'easeInOut', repeat: Infinity }}
          className="w-16 h-16 rounded-2xl bg-card border border-border flex items-center justify-center mb-2"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--accent-glow))" strokeWidth="1.5" strokeLinecap="round">
            <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
          </svg>
        </motion.div>

        <h1 className="text-4xl sm:text-5xl font-serif text-foreground tracking-tight text-center leading-[1.1]">
          Ask about your<br />documents
        </h1>

        <p className="text-base text-muted-foreground text-center max-w-[420px] leading-relaxed">
          Upload documents and ask questions in Hindi, English, or Hinglish. Cross-lingual retrieval finds relevant content regardless of language.
        </p>
      </motion.div>

      <div className="flex flex-col gap-2 w-full max-w-[480px]">
        {CHIPS.map((chip, i) => (
          <motion.button
            key={chip.text}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.08, duration: 0.5, ease }}
            whileHover={{ scale: 1.01, x: 4 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onChipClick(chip.text)}
            className="w-full flex items-center justify-between px-5 py-4 rounded-2xl text-left text-sm text-foreground/80 bg-card border border-border cursor-pointer sera-transition hover:bg-secondary hover:border-foreground/10 hover:text-foreground group"
          >
            <span className="flex-1 truncate">{chip.text}</span>
            <ArrowRight size={16} className="text-muted-foreground/30 group-hover:text-foreground/50 sera-transition shrink-0 ml-3" />
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
