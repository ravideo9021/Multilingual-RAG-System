import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { springBouncy } from '@/lib/utils'

interface WelcomeProps {
  onChipClick: (text: string) => void
}

const CHIPS = [
  'भारत की राजधानी क्या है?',
  'Tell me about the Taj Mahal',
  'ISRO ke baare mein batao',
  'Summarize my documents',
]

export function Welcome({ onChipClick }: WelcomeProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="flex-1 flex flex-col items-center justify-center gap-5 px-5 py-10"
    >
      <div className="relative">
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 4, ease: 'easeInOut', repeat: Infinity }}
          className="w-16 h-16 rounded-2xl bg-secondary border border-border flex items-center justify-center"
        >
          <Sparkles size={28} className="text-warm" strokeWidth={1.5} />
        </motion.div>
      </div>

      <h1 className="font-serif text-[32px] text-foreground tracking-tight text-center">
        Ask about your documents
      </h1>

      <p className="text-sm text-muted-foreground text-center max-w-[440px] leading-relaxed">
        Upload documents and ask questions in Hindi, English, or Hinglish.
        Cross-lingual retrieval finds relevant content regardless of language.
      </p>

      <div className="flex flex-wrap gap-2 justify-center mt-2 max-w-[560px]">
        {CHIPS.map((chip, i) => (
          <motion.button
            key={chip}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.08, ...springBouncy }}
            whileHover={{ y: -3, scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onChipClick(chip)}
            className="px-4 py-2 rounded-full text-[13px] text-muted-foreground bg-card border border-border cursor-pointer transition-all hover:bg-secondary hover:border-foreground/10 hover:text-foreground"
          >
            {chip}
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
