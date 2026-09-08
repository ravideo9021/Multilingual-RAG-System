import { motion, AnimatePresence } from 'framer-motion'
import { Plus, FileText } from 'lucide-react'
import { escapeHtml, springBouncy } from '@/lib/utils'

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
    <div className="flex flex-col h-full">
      {/* Panel header (coming-soon-01 mono uppercase label) */}
      <div className="font-mono text-[10px] font-semibold text-zinc-600 uppercase tracking-[0.1em] px-4 pt-4 pb-3 flex items-center justify-between">
        <span>Sources</span>
        {files.length > 0 && (
          <span className="font-mono text-[10px] text-zinc-600 font-medium normal-case tracking-normal">
            {files.length} file{files.length > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Upload button */}
      <div className="px-3 pb-3">
        <motion.button
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          transition={springBouncy}
          onClick={onUploadClick}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-[13px] font-semibold text-white bg-gradient-to-br from-accent to-indigo-700 border-none cursor-pointer relative overflow-hidden hover:shadow-lg hover:shadow-indigo-500/30"
        >
          <Plus size={14} />
          <span>Upload Documents</span>
        </motion.button>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <AnimatePresence>
          {files.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-8 px-4"
            >
              <FileText size={28} className="mx-auto mb-2.5 opacity-15 text-zinc-500" strokeWidth={1.2} />
              <p className="font-mono text-[11px] uppercase tracking-wide text-zinc-600 mb-2">
                Knowledge Base
              </p>
              <p className="text-xs text-zinc-600 leading-relaxed">
                Upload PDFs, TXT, or Markdown files to build your retrieval index.
              </p>
            </motion.div>
          ) : (
            files.map((file, i) => (
              <motion.div
                key={file.name + i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, ...springBouncy }}
                className="bg-bg-card border border-white/[0.06] rounded-[10px] p-2.5 px-3 mb-1.5 transition-colors hover:border-white/10 hover:bg-bg-card-hover"
              >
                <div className="flex items-center gap-[7px] text-xs font-semibold text-white truncate">
                  <FileText size={13} className="opacity-35 shrink-0" strokeWidth={1.5} />
                  {escapeHtml(file.name)}
                </div>
                <div className="font-mono text-[10px] mt-1 pl-5 flex items-center gap-1 tracking-wide">
                  {file.status === 'loading' && (
                    <span className="text-zinc-500 flex items-center gap-1">
                      <span className="inline-block w-2.5 h-2.5 border-[1.5px] border-white/10 border-t-accent rounded-full animate-spin" />
                      Indexing...
                    </span>
                  )}
                  {file.status === 'ok' && (
                    <span className="text-emerald-400">
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={springBouncy}
                        className="inline-block"
                      >
                        &#10003;
                      </motion.span>
                      {' '}{file.chunks} chunks indexed
                    </span>
                  )}
                  {file.status === 'error' && (
                    <span className="text-red-400">{file.error || 'Error'}</span>
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
