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
  model?: string
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

export interface ModelOption {
  id: string
  name: string
  provider: string
}

export const MODELS: ModelOption[] = [
  { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', provider: 'Google' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', provider: 'OpenAI' },
  { id: 'llama-3.3-70b', name: 'Llama 3.3 70B', provider: 'Meta' },
  { id: 'mistral-small-3.1', name: 'Mistral Small 3.1', provider: 'Mistral' },
  { id: 'qwen-2.5-72b', name: 'Qwen 2.5 72B', provider: 'Alibaba' },
  { id: 'nvidia-nemotron-70b', name: 'Nemotron 70B', provider: 'NVIDIA' },
]
