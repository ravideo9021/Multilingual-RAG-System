import { motion } from 'framer-motion'
import { ArrowRight, Globe, Languages, FileSearch } from 'lucide-react'
import { ease } from '@/lib/utils'

interface WelcomeProps {
  onChipClick: (text: string) => void
}

const CHIPS = [
  { text: 'भारत की राजधानी क्या है?', label: 'Hindi', icon: Globe },
  { text: 'Tell me about the Taj Mahal', label: 'English', icon: FileSearch },
  { text: 'ISRO ke baare mein batao', label: 'Hinglish', icon: Languages },
  { text: 'Summarize my documents', label: 'Action', icon: FileSearch },
]

export function Welcome({ onChipClick }: WelcomeProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.6, ease }}
      className="flex-1 flex flex-col items-center justify-center gap-10 px-6 py-12"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.1, ease }}
        className="flex flex-col items-center gap-5"
      >
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 5, ease: 'easeInOut', repeat: Infinity }}
          className="w-16 h-16 rounded-2xl bg-card border border-border flex items-center justify-center mb-1"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5" strokeLinecap="round">
            <path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" />
          </svg>
        </motion.div>

        <h1 className="text-4xl sm:text-5xl font-serif text-foreground tracking-tight text-center leading-[1.1]">
          Ask about your<br />documents
        </h1>

        <p className="text-base text-muted-foreground text-center max-w-[440px] leading-relaxed">
          Upload documents and ask questions in Hindi, English, or Hinglish.
          Cross-lingual retrieval finds answers regardless of language.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-[520px]">
        {CHIPS.map((chip, i) => (
          <motion.button
            key={chip.text}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.08, duration: 0.5, ease }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChipClick(chip.text)}
            className="flex items-center gap-3 px-4 py-3.5 rounded-2xl text-left text-sm text-foreground/80 bg-card border border-border cursor-pointer transition-all duration-200 hover:bg-secondary hover:border-foreground/10 hover:text-foreground group"
          >
            <chip.icon size={16} className="text-muted-foreground/40 group-hover:text-foreground/60 transition-colors duration-200 shrink-0" />
            <span className="flex-1 truncate">{chip.text}</span>
            <ArrowRight size={14} className="text-muted-foreground/20 group-hover:text-foreground/40 transition-colors duration-200 shrink-0" />
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
