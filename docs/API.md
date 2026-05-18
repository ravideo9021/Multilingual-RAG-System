# API

The backend is a FastAPI service that runs on `http://localhost:8000` by
default. The frontend at `http://localhost:7860` calls the same API directly.

## Health

```bash
curl http://localhost:8000/health
```

Returns service status, whether a persisted FAISS index was loaded, and the
configured LLM provider label.

## Stats

```bash
curl http://localhost:8000/stats
```

Returns index size, embedding model, embedding dimension, FAISS index type,
indexed languages, and the active LLM provider label.

## Ingest

Upload a text, Markdown, HTML, or PDF file. The backend extracts text, chunks it
with the script-aware chunker, embeds each chunk, and adds it to the in-memory
FAISS store for the current process.

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@backend/data/sample_corpus/india.en.txt"
```

Successful responses include the original filename and the number of chunks
indexed. Unsupported or unreadable files return `422`.

## Query

`POST /query` streams Server-Sent Events. The request body is JSON:

```json
{
  "query": "भारत की राजधानी क्या है?"
}
```

Example with curl:

```bash
curl -N -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"भारत की राजधानी क्या है?"}'
```

The stream can emit these event types:

| Event | Data |
|---|---|
| `sources` | JSON array of retrieved source passages |
| `token` | One generated text chunk |
| `citations` | JSON array of cited source ranks |
| `error` | Error message string |
| `done` | Empty completion marker |

If no documents are indexed, the backend skips retrieval and uses the configured
LLM as a direct chat model. If documents are indexed but retrieval finds no
relevant passages, the backend streams a fallback answer without citations.

## Runtime Requirements

- Start the backend with `make run`.
- Configure at least one LLM key in `.env` for generated answers:
  `OPENAI_API_KEY` for OpenRouter/OpenAI-compatible APIs, or `GEMINI_API_KEY`
  for Gemini.
- Run `bash scripts/download_models.sh` before retrieval so the fastText
  language-ID model is available.
