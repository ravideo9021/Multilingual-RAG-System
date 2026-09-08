export interface SourceHit {
  rank: number
  text: string
  score?: number
  title?: string
  source?: string
  language?: string
  doc_id?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  lang?: string
  sources?: SourceHit[]
  elapsedMs?: number
  isStreaming?: boolean
}

export interface StatsData {
  index_size: number
  embedding_model: string
  embedding_dim: number
  faiss_index_type: string
  languages: string[]
  llm_provider: string
}

export interface HealthData {
  status: string
  index_loaded: boolean
  llm_provider: string
}

export type Lang = 'hi' | 'en' | 'mix' | ''
export type EffortLevel = 0 | 1 | 2
