import { motion, AnimatePresence } from 'framer-motion'
import { Plus, FileText } from 'lucide-react'
import { escapeHtml, ease } from '@/lib/utils'

interface UploadedFile {
  name: string
  status: 'loading' | 'ok' | 'error'
  chunks?: number
  error?: string
}

interface SourcesPanelProps {
  files: UploadedFile[]
  onUploadClick: () => void
}

export function SourcesPanel({ files, onUploadClick }: SourcesPanelProps) {
  return (
    <div className="flex flex-col h-full p-4 gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Sources</span>
        {files.length > 0 && (
          <span className="text-[11px] text-muted-foreground/40">
            {files.length} file{files.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      <motion.button
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onClick={onUploadClick}
        className="w-full flex items-center justify-center gap-2.5 py-3 rounded-2xl text-sm font-semibold text-background bg-foreground cursor-pointer sera-transition hover:opacity-90"
      >
        <Plus size={16} />
        <span>Upload Documents</span>
      </motion.button>

      <div className="flex-1 overflow-y-auto flex flex-col gap-2">
        <AnimatePresence>
          {files.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-10 px-4"
            >
              <FileText size={32} className="mx-auto mb-3 text-muted-foreground/10" strokeWidth={1.2} />
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">
                Knowledge Base
              </p>
              <p className="text-xs text-muted-foreground/40 leading-relaxed">
                Upload PDFs, TXT, or Markdown files to build your retrieval index.
              </p>
            </motion.div>
          ) : (
            files.map((file, i) => (
              <motion.div
                key={file.name + i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4, ease }}
                className="bg-card border border-border rounded-2xl p-3.5 sera-transition hover:border-foreground/10"
              >
                <div className="flex items-center gap-2.5 text-sm font-medium text-foreground truncate">
                  <FileText size={14} className="text-muted-foreground/25 shrink-0" strokeWidth={1.5} />
                  {escapeHtml(file.name)}
                </div>
                <div className="text-[11px] mt-1.5 pl-6 flex items-center gap-1.5">
                  {file.status === 'loading' && (
                    <span className="text-muted-foreground flex items-center gap-1.5">
                      <span className="inline-block w-3 h-3 border-[1.5px] border-border border-t-accent-glow rounded-full animate-spin" />
                      Indexing...
                    </span>
                  )}
                  {file.status === 'ok' && (
                    <span className="text-emerald-400/80">
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ duration: 0.3, ease }}
                        className="inline-block"
                      >
                        &#10003;
                      </motion.span>
                      {' '}{file.chunks} chunks indexed
                    </span>
                  )}
                  {file.status === 'error' && (
                    <span className="text-red-400/80">{file.error || 'Error'}</span>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
