import {
  AlertCircle,
  CheckCircle2,
  FileText,
  FileCode2,
  FileIcon,
  Loader2,
  RotateCcw,
  UploadCloud,
  X,
} from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useId, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

export type FileUploadStatus = 'queued' | 'uploading' | 'success' | 'error'

export type FileUploadItem = {
  id: string
  name: string
  size: number
  type?: string
  progress?: number
  status?: FileUploadStatus
  error?: string
  file?: File
  chunks?: number
}

export interface FileUploadProps {
  value?: FileUploadItem[]
  onFilesAdded?: (items: FileUploadItem[], files: File[]) => void
  onRemove?: (item: FileUploadItem) => void
  onRetry?: (item: FileUploadItem) => void
  accept?: string
  multiple?: boolean
  maxFiles?: number
  disabled?: boolean
  title?: string
  description?: string
  className?: string
}

const EASE_OUT = [0.16, 1, 0.3, 1] as const
const ROW_TRANSITION = { duration: 0.22, ease: EASE_OUT } as const

const STATUS_LABEL: Record<FileUploadStatus, string> = {
  queued: 'Queued',
  uploading: 'Indexing',
  success: 'Indexed',
  error: 'Failed',
}

const STATUS_TONE: Record<FileUploadStatus, string> = {
  queued: 'text-muted-foreground',
  uploading: 'text-foreground',
  success: 'text-emerald-400',
  error: 'text-red-400',
}

function clampProgress(value: number | undefined, status: FileUploadStatus) {
  if (status === 'success') return 100
  if (value === undefined || Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, value))
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** exponent
  return `${value >= 10 || exponent === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[exponent]}`
}

function fileKind(item: FileUploadItem) {
  const extension = item.name.includes('.') ? item.name.split('.').pop() : undefined
  if (extension) return extension.toUpperCase()
  return 'FILE'
}

function getFileIcon(item: FileUploadItem) {
  const extension = item.name.includes('.') ? item.name.split('.').pop()?.toLowerCase() : undefined
  if (['css', 'html', 'js', 'jsx', 'json', 'ts', 'tsx', 'xml', 'yaml', 'yml'].includes(extension ?? '')) return FileCode2
  return FileText
}

export function createFileUploadItem(file: File, index = 0): FileUploadItem {
  return {
    id: `${Date.now()}-${index}-${file.name}`,
    name: file.name,
    size: file.size,
    type: file.type,
    progress: 0,
    status: 'uploading',
    file,
  }
}

function StatusIcon({ status }: { status: FileUploadStatus }) {
  const iconClassName = 'h-4 w-4'
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={status}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.16, ease: EASE_OUT }}
        className={cn('grid h-6 w-6 place-items-center', STATUS_TONE[status])}
      >
        {status === 'success' ? (
          <CheckCircle2 className={iconClassName} />
        ) : status === 'error' ? (
          <AlertCircle className={iconClassName} />
        ) : status === 'uploading' ? (
          <Loader2 className={cn(iconClassName, 'animate-spin')} />
        ) : (
          <FileIcon className={iconClassName} />
        )}
        <span className="sr-only">{STATUS_LABEL[status]}</span>
      </motion.span>
    </AnimatePresence>
  )
}

function FileUploadRow({
  item,
  onRemove,
  onRetry,
}: {
  item: FileUploadItem
  onRemove: (item: FileUploadItem) => void
  onRetry: (item: FileUploadItem) => void
}) {
  const status = item.status ?? 'queued'
  const progress = clampProgress(item.progress, status)
  const progressRatio = progress / 100
  const showProgress = status === 'uploading' || status === 'success'
  const LeadingIcon = getFileIcon(item)

  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={ROW_TRANSITION}
      className="relative overflow-hidden rounded-2xl border border-border bg-background p-3"
    >
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
          <LeadingIcon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-foreground">{item.name}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {fileKind(item)} · {formatBytes(item.size)}
                {status === 'success' && item.chunks ? ` · ${item.chunks} chunks` : null}
                {status === 'error' && item.error ? ` · ${item.error}` : null}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <StatusIcon status={status} />
              {status === 'error' && (
                <button
                  type="button"
                  onClick={() => onRetry(item)}
                  className="grid h-7 w-7 place-items-center rounded-full text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground active:scale-95"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                type="button"
                onClick={() => onRemove(item)}
                className="grid h-7 w-7 place-items-center rounded-full text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground active:scale-95"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          {showProgress && (
            <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-muted">
              <motion.div
                className={cn('h-full rounded-full', status === 'success' ? 'bg-emerald-500' : 'bg-foreground')}
                initial={false}
                animate={{ transform: `scaleX(${progressRatio})` }}
                style={{ transformOrigin: 'left' }}
                transition={{ duration: 0.28, ease: EASE_OUT }}
              />
            </div>
          )}
        </div>
      </div>
    </motion.li>
  )
}

export function FileUpload({
  value = [],
  onFilesAdded,
  onRemove,
  onRetry,
  accept = '.pdf,.txt,.md,.html,.htm',
  multiple = true,
  maxFiles,
  disabled = false,
  title = 'Drop files here',
  description = 'PDF, TXT, or Markdown files',
  className,
}: FileUploadProps) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const dragDepthRef = useRef(0)
  const [dragging, setDragging] = useState(false)

  const addFiles = useCallback(
    (incomingFiles: File[]) => {
      if (disabled || incomingFiles.length === 0) return
      const remainingSlots = maxFiles === undefined ? incomingFiles.length : maxFiles - value.length
      if (remainingSlots <= 0) return
      const files = incomingFiles.slice(0, multiple ? remainingSlots : Math.min(1, remainingSlots))
      const added = files.map((file, index) => createFileUploadItem(file, index))
      if (added.length === 0) return
      onFilesAdded?.(added, files)
    },
    [disabled, value.length, maxFiles, multiple, onFilesAdded],
  )

  const removeItem = useCallback(
    (item: FileUploadItem) => { onRemove?.(item) },
    [onRemove],
  )

  const retryItem = useCallback(
    (item: FileUploadItem) => { onRetry?.(item) },
    [onRetry],
  )

  const maxReached = maxFiles !== undefined && value.length >= maxFiles

  return (
    <div className={cn('w-full space-y-2.5', className)}>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled || maxReached}
        tabIndex={-1}
        className="sr-only"
        onChange={(event) => {
          addFiles(Array.from(event.currentTarget.files ?? []))
          event.currentTarget.value = ''
        }}
      />

      <button
        type="button"
        disabled={disabled || maxReached}
        data-dragging={dragging}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          if (disabled || maxReached) return
          event.preventDefault()
          dragDepthRef.current += 1
          setDragging(true)
        }}
        onDragOver={(event) => {
          if (disabled || maxReached) return
          event.preventDefault()
          event.dataTransfer.dropEffect = 'copy'
          setDragging(true)
        }}
        onDragLeave={(event) => {
          if (disabled || maxReached) return
          event.preventDefault()
          dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
          if (dragDepthRef.current === 0) setDragging(false)
        }}
        onDrop={(event) => {
          if (disabled || maxReached) return
          event.preventDefault()
          dragDepthRef.current = 0
          setDragging(false)
          addFiles(Array.from(event.dataTransfer.files))
        }}
        className={cn(
          'group relative flex w-full overflow-hidden rounded-2xl border border-dashed border-border bg-background outline-none',
          'transition-[border-color,transform] duration-200 active:scale-[0.99]',
          'hover:border-foreground/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'data-[dragging=true]:border-foreground/50',
          'disabled:pointer-events-none disabled:opacity-55',
          'flex-col items-center justify-center gap-2.5 p-6 text-center',
        )}
      >
        <motion.span
          className="grid shrink-0 place-items-center h-14 w-14 rounded-2xl bg-muted text-foreground border border-border"
          animate={{ transform: dragging ? 'translateY(-2px)' : 'translateY(0px)' }}
          transition={{ duration: 0.16, ease: EASE_OUT }}
        >
          <UploadCloud className="h-6 w-6" />
        </motion.span>
        <span className="min-w-0 max-w-xs">
          <span className="block text-sm font-semibold text-foreground">
            {maxReached ? 'Upload limit reached' : title}
          </span>
          <span className="block text-xs text-muted-foreground mt-1 leading-5">
            {maxReached ? `${value.length} of ${maxFiles} files added` : description}
          </span>
        </span>
        <span className="shrink-0 rounded-full border border-border text-xs font-medium text-foreground px-4 py-2 mt-1 transition-colors duration-150 group-hover:bg-muted">
          Browse
        </span>
      </button>

      <ul className="space-y-2">
        <AnimatePresence initial={false}>
          {value.map((item) => (
            <FileUploadRow
              key={item.id}
              item={item}
              onRemove={removeItem}
              onRetry={retryItem}
            />
          ))}
        </AnimatePresence>
      </ul>
    </div>
  )
}
