import { useCallback } from 'react'
import { FileUpload, createFileUploadItem, type FileUploadItem } from '@/components/ui/file-upload'
import { ingestFile } from '@/lib/api'

interface SourcesPanelProps {
  files: FileUploadItem[]
  setFiles: React.Dispatch<React.SetStateAction<FileUploadItem[]>>
}

export function SourcesPanel({ files, setFiles }: SourcesPanelProps) {
  const handleFilesAdded = useCallback(
    (added: FileUploadItem[], rawFiles: File[]) => {
      setFiles(prev => [...prev, ...added])

      added.forEach((item, i) => {
        const file = rawFiles[i]
        if (!file) return

        ingestFile(file)
          .then(result => {
            setFiles(prev =>
              prev.map(f =>
                f.id === item.id
                  ? { ...f, status: 'success' as const, progress: 100, chunks: result.chunks }
                  : f
              )
            )
          })
          .catch(() => {
            setFiles(prev =>
              prev.map(f =>
                f.id === item.id
                  ? { ...f, status: 'error' as const, error: 'Upload failed — is the backend running?' }
                  : f
              )
            )
          })
      })
    },
    [setFiles],
  )

  const handleRemove = useCallback(
    (item: FileUploadItem) => {
      setFiles(prev => prev.filter(f => f.id !== item.id))
    },
    [setFiles],
  )

  const handleRetry = useCallback(
    (item: FileUploadItem) => {
      if (!item.file) return

      setFiles(prev =>
        prev.map(f =>
          f.id === item.id ? { ...f, status: 'uploading' as const, progress: 0, error: undefined } : f
        )
      )

      ingestFile(item.file)
        .then(result => {
          setFiles(prev =>
            prev.map(f =>
              f.id === item.id
                ? { ...f, status: 'success' as const, progress: 100, chunks: result.chunks }
                : f
            )
          )
        })
        .catch(() => {
          setFiles(prev =>
            prev.map(f =>
              f.id === item.id
                ? { ...f, status: 'error' as const, error: 'Retry failed' }
                : f
            )
          )
        })
    },
    [setFiles],
  )

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
          Knowledge Base
        </span>
        {files.length > 0 && (
          <span className="text-[11px] text-muted-foreground/50">
            {files.filter(f => f.status === 'success').length} of {files.length} ready
          </span>
        )}
      </div>

      <FileUpload
        value={files}
        onFilesAdded={handleFilesAdded}
        onRemove={handleRemove}
        onRetry={handleRetry}
        title="Drop files to upload"
        description="PDF, TXT, or Markdown files for retrieval"
        maxFiles={20}
      />
    </div>
  )
}
