# Orchestrator backends

Splice supports **three orchestration modes**. Your code stays on your machine with **mock** or **Ollama**; **Bedrock** is optional for cloud teams.

| Mode | Privacy | Cost | Requires |
|------|---------|------|----------|
| **mock** | Code never leaves repo | Free | Nothing |
| **ollama** | Code stays local; LLM runs on your machine | Free (hardware) | [Ollama](https://ollama.com) |
| **bedrock** | Context sent to AWS | Pay per token | AWS + model access |

---

## Configure

Edit `.splice/config.json`:

```json
{
  "orchestrator": "ollama",
  "ollama": {
    "baseUrl": "http://localhost:11434",
    "model": "llama3.2",
    "timeoutSeconds": 60
  },
  "bedrock": {
    "modelId": "amazon.nova-lite-v1:0"
  }
}
```

Or use environment variables (override config):

```bash
export SPLICE_ORCHESTRATOR=ollama   # mock | ollama | bedrock
export OLLAMA_MODEL=llama3.2
export OLLAMA_BASE_URL=http://localhost:11434
```

---

## 1. Mock (default)

Deterministic Python rules — no LLM, no network.

```json
{ "orchestrator": "mock" }
```

Best for: fast hooks, offline work, simple error/diff/file routing.

---

## 2. Ollama (local LLM)

### Setup

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2

# Verify
python3 scripts/splice-cli.py doctor
```

### Enable

```json
{ "orchestrator": "ollama" }
```

### Recommended models (routing only — small is fine)

| Model | Size | Notes |
|-------|------|-------|
| `llama3.2` | ~2GB | Good default |
| `mistral` | ~4GB | Strong JSON adherence |
| `qwen2.5:7b` | ~4.7GB | Good for structured output |

Orchestration prompts are short — you do **not** need a 70B codegen model.

### Fallback

If Ollama is down, Splice falls back to **mock** automatically (`source: ollama-fallback`).

---

## 3. Bedrock (cloud)

For AWS-deployed API or local CLI with cloud routing:

```json
{ "orchestrator": "bedrock" }
```

```bash
export AWS_REGION=us-east-1
export SPLICE_ORCHESTRATOR=bedrock
```

CDK deploy sets `SPLICE_ORCHESTRATOR=bedrock` on Lambda automatically.

Enable **Amazon Nova Lite** in the Bedrock console for your region.

---

## Verify

```bash
python3 scripts/splice-cli.py doctor
python3 scripts/splice-cli.py orchestrate --assistant kiro --prompt "/harness test" --always
```

Check `orchestrator` and `source` in output:

- `orchestrator: mock` → `source: mock`
- `orchestrator: ollama` → `source: ollama` (or `ollama-fallback`)
- `orchestrator: bedrock` → `source: bedrock` (or `bedrock-fallback`)

---

## Privacy note

| Data | Mock | Ollama | Bedrock |
|------|------|--------|---------|
| Source files / errors | Read from disk locally | Sent to localhost Ollama only | Sent to AWS |
| Stored in bundle | `.splice/` in repo | Same | DynamoDB if API deployed |

Kiro and Cursor may still send context to **their** cloud models when you chat — Splice controls only the **orchestration** step.
