import { useState, useCallback, useRef, useEffect } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Header } from '@/components/Header'
import { Welcome } from '@/components/Welcome'
import { ChatInput } from '@/components/ChatInput'
import { StreamingMessage } from '@/components/StreamingMessage'
import { ThinkingCard } from '@/components/ThinkingCard'
import { SourcesPanel } from '@/components/SourcesPanel'
import type { FileUploadItem } from '@/components/ui/file-upload'
import { streamQuery } from '@/lib/api'
import { detectLang } from '@/lib/utils'
import { MODELS, type Message, type SourceHit, type ModelOption } from '@/types'

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isThinking, setIsThinking] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selectedModel, setSelectedModel] = useState<ModelOption>(MODELS[0])

  const [files, setFiles] = useState<FileUploadItem[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const lastQueryRef = useRef('')

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isThinking, scrollToBottom])

  const handleSend = useCallback(async (text: string) => {
    if (isStreaming) return
    lastQueryRef.current = text

    const lang = detectLang(text)
    const userMsg: Message = { id: generateId(), role: 'user', content: text, lang: lang || undefined }
    setMessages(prev => [...prev, userMsg])

    setIsThinking(true)
    setIsStreaming(true)

    const assistantId = generateId()
    let fullAnswer = ''
    let sources: SourceHit[] = []
    let elapsedMs = 0
    let firstToken = true
    let rLang = lang

    try {
      await streamQuery(text, {
        onSources: (s) => {
          sources = s
          if (s[0]?.language) {
            rLang = s[0].language === 'hi' ? 'hi' : s[0].language === 'en' ? 'en' : 'mix'
          }
        },
        onToken: (token) => {
          if (firstToken) {
            setIsThinking(false)
            firstToken = false
          }
          fullAnswer += token
          setMessages(prev => {
            const existing = prev.find(m => m.id === assistantId)
            if (existing) {
              return prev.map(m => m.id === assistantId ? { ...m, content: fullAnswer } : m)
            }
            return [...prev, {
              id: assistantId,
              role: 'assistant' as const,
              content: fullAnswer,
              lang: rLang || undefined,
              isStreaming: true,
            }]
          })
        },
        onError: (err) => {
          if (firstToken) {
            setIsThinking(false)
            firstToken = false
          }
          fullAnswer += (fullAnswer ? '\n\n' : '') + err
          setMessages(prev => {
            const existing = prev.find(m => m.id === assistantId)
            if (existing) {
              return prev.map(m => m.id === assistantId ? { ...m, content: fullAnswer } : m)
            }
            return [...prev, {
              id: assistantId,
              role: 'assistant' as const,
              content: fullAnswer,
              lang: rLang || undefined,
              isStreaming: true,
            }]
          })
        },
        onDone: (ms) => {
          elapsedMs = ms
        },
      })

      setMessages(prev =>
        prev.map(m => m.id === assistantId ? {
          ...m,
          content: fullAnswer || '*No response received.*',
          isStreaming: false,
          sources,
          elapsedMs,
          lang: rLang || undefined,
        } : m)
      )

      setMessages(prev => {
        if (!prev.find(m => m.id === assistantId)) {
          return [...prev, {
            id: assistantId,
            role: 'assistant' as const,
            content: fullAnswer || '*No response received.*',
            isStreaming: false,
            sources,
            elapsedMs,
            lang: rLang || undefined,
          }]
        }
        return prev
      })
    } catch {
      setMessages(prev => [...prev, {
        id: assistantId,
        role: 'assistant' as const,
        content: '*Could not connect to backend. Is the server running on port 8000?*',
        isStreaming: false,
      }])
    }

    setIsThinking(false)
    setIsStreaming(false)
  }, [isStreaming])

  const handleRetry = useCallback(() => {
    if (lastQueryRef.current) {
      handleSend(lastQueryRef.current)
    }
  }, [handleSend])

  const handleFollowUp = useCallback((text: string) => {
    handleSend(text)
  }, [handleSend])

  return (
    <div className="flex flex-col h-screen relative">
      <Header
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        sidebarOpen={sidebarOpen}
        fileCount={files.filter(f => f.status === 'success').length}
      />

      <div className="flex flex-1 min-h-0">
        <aside className={`hidden md:flex w-[280px] min-w-[240px] bg-background border-r border-border/50 flex-col ${sidebarOpen ? '!flex fixed top-14 left-0 bottom-0 z-[100] w-[300px] bg-background shadow-2xl shadow-black/50' : ''}`}>
          <SourcesPanel files={files} setFiles={setFiles} />
        </aside>

        <main className="flex-1 min-w-0 flex flex-col">
          <div className="flex-1 overflow-y-auto px-6 sm:px-10 py-8 flex flex-col gap-8">
            <AnimatePresence mode="wait">
              {messages.length === 0 && !isThinking && (
                <Welcome key="welcome" onChipClick={handleSend} />
              )}
            </AnimatePresence>

            {messages.map((msg, i) => (
              <StreamingMessage
                key={msg.id}
                message={msg}
                originalQuery={msg.role === 'assistant' ? lastQueryRef.current : undefined}
                onRetry={msg.role === 'assistant' && !msg.isStreaming ? handleRetry : undefined}
                onFollowUp={msg.role === 'assistant' && !msg.isStreaming && i === messages.length - 1 ? handleFollowUp : undefined}
              />
            ))}

            <AnimatePresence>
              {isThinking && <ThinkingCard key="thinking" />}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </div>

          <ChatInput
            onSend={handleSend}
            onAttach={() => setSidebarOpen(true)}
            disabled={isStreaming}
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
          />
        </main>
      </div>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-[99] bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}
