# ReportForge #

## Ollama

Install:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start:
```bash
ollama serve
```

Pull model:
```bash
ollama pull llama3
```

Environment:
```bash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

Authenticated API:
```bash
curl -X POST http://localhost:8000/api/v1/ollama/extract `
  -H "Authorization: Bearer $TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"text":"Extract insights from this PDF content...","temperature":0.3,"max_tokens":1000}'
```

