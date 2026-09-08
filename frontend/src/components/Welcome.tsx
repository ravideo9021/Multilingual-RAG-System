import { motion } from 'framer-motion'
import { MessageSquare } from 'lucide-react'
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
      {/* Glowing orb */}
      <div className="relative">
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 4, ease: 'easeInOut', repeat: Infinity }}
          className="w-[72px] h-[72px] rounded-full flex items-center justify-center"
          style={{
            background: 'radial-gradient(circle at 30% 30%, rgba(99,102,241,0.25), rgba(99,102,241,0.12))',
          }}
        >
          <MessageSquare size={30} className="text-indigo-400 relative z-10" strokeWidth={1.5} />
        </motion.div>
        <div
          className="absolute -inset-3 rounded-full animate-breathe"
          style={{
            background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
          }}
        />
      </div>

      {/* Title with serif font (coming-soon-01) */}
      <h1 className="font-serif text-[32px] text-white tracking-tight text-center">
        Ask about your documents
      </h1>

      <p className="text-sm text-zinc-500 text-center max-w-[460px] leading-relaxed">
        Upload documents and ask questions in Hindi, English, or Hinglish.
        Cross-lingual retrieval finds relevant content regardless of language.
      </p>

      {/* Suggestion chips with spring animation */}
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
            className="px-4 py-2 rounded-full text-[13px] font-sans text-zinc-400 bg-bg-card border border-white/[0.06] cursor-pointer transition-shadow hover:bg-accent-glow hover:border-accent hover:text-white hover:shadow-lg hover:shadow-indigo-500/10"
          >
            {chip}
          </motion.button>
        ))}
      </div>
    </motion.div>
  )
}
