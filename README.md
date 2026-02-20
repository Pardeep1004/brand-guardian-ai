<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" />
  <img src="https://img.shields.io/badge/Azure_AI-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white" />
  <img src="https://img.shields.io/badge/GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white" />
</p>

<h1 align="center">🛡️ Brand Guardian AI</h1>

<p align="center">
  <strong>AI-Powered Video Compliance Auditing Platform</strong><br/>
  <em>Automatically audit YouTube ads against global brand safety &amp; regulatory compliance rules using RAG, LangGraph, and Azure AI.</em>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#%EF%B8%8F-architecture">Architecture</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-project-structure">Project Structure</a>
</p>

---

## 🎯 Problem Statement

Brands spend **billions** on video advertising across YouTube and social media. A single non-compliant ad — containing misleading claims, missing legal disclosures, or violating regional regulations — can lead to **regulatory fines, brand damage, and lost consumer trust**.

**Brand Guardian AI** automates the compliance review process that traditionally requires a team of legal reviewers watching every second of every ad manually.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎬 **YouTube Video Ingestion** | Paste any YouTube URL — the system downloads, uploads to Azure Video Indexer, and extracts transcript, OCR text, and detected brand logos automatically |
| 🔍 **RAG-Powered Compliance Audit** | Retrieves relevant compliance rules from a vector knowledge base (Azure AI Search) and uses GPT-4o to evaluate the video against those rules |
| 🌍 **Region-Aware Auditing** | Select Global, Europe, North America, or Asia — the audit adapts to region-specific regulations (GDPR, FTC, ASCI, etc.) |
| 📋 **Detailed Violation Reports** | Each audit generates a structured report with violation categories, severity levels (CRITICAL/HIGH/MEDIUM/LOW), and specific descriptions |
| 💬 **Interactive Chat Q&A** | After an audit completes, chat with the AI to ask follow-up questions about specific violations or compliance decisions |
| 📊 **Audit History & Persistence** | All audits are persisted in a SQLite database with full history, status tracking, and the ability to revisit past reports |
| 🔄 **Async Processing** | Audits run as background tasks with real-time status polling — the UI stays responsive during long processing times |
| 📡 **Azure Monitor Telemetry** | Full observability with OpenTelemetry integration — tracks request latency, error rates, and usage metrics in Azure Application Insights |
| 🧪 **LangSmith Tracing** | Every LLM call is traced for debugging, cost monitoring, and prompt evaluation |

---

## 🏗️ Architecture

```
                         ┌─────────────────────────────┐
                         │    Frontend (Jinja2 + JS)   │
                         │  • Video URL Input          │
                         │  • Region Selector          │
                         │  • Real-time Status Polling │
                         │  • Audit Report Viewer      │
                         │  • Interactive Chat Q&A     │
                         └──────────┬──────────────────┘
                                    │  HTTP / REST
                                    ▼
                         ┌─────────────────────────────┐
                         │   FastAPI Backend Server    │
                         │  • POST /audit (async)      │
                         │  • GET  /status/{task_id}   │
                         │  • GET  /history            │
                         │  • POST /chat               │
                         │  • GET  /health             │
                         └──────────┬──────────────────┘
                                    │  Background Task
                                    ▼
               ┌─────────────────────────────────────────────┐
               │          LangGraph Workflow (DAG)           │
               │                                             │
               │   START                                     │
               │     │                                       │
               │     ▼                                       │
               │   ┌─────────────────────┐                   │
               │   │  Node 1: Indexer    │                   │
               │   │  • yt-dlp download  │                   │
               │   │  • Azure VI upload  │                   │
               │   │  • Extract insights │                   │
               │   └─────────┬───────────┘                   │
               │             │                               │
               │             ▼                               │
               │   ┌─────────────────────┐                   │
               │   │  Node 2: Auditor    │                   │
               │   │  • RAG retrieval    │──── Azure AI Search
               │   │  • GPT-4o analysis  │──── Azure OpenAI
               │   │  • JSON report gen  │                   │
               │   └─────────┬───────────┘                   │
               │             │                               │
               │             ▼                               │
               │           END → Save to SQLite DB           │
               └─────────────────────────────────────────────┘
```

### How It Works (End-to-End Flow)

1. **User submits** a YouTube URL and selects a target region via the web UI
2. **FastAPI** creates an async background task and returns a `task_id` immediately
3. **Indexer Node** downloads the video with `yt-dlp`, uploads it to **Azure Video Indexer**, and waits for processing to extract transcript, OCR text, and brand logos
4. **Auditor Node** constructs a retrieval query with regional context, fetches relevant compliance rules from **Azure AI Search** (vector store), and sends the complete context to **GPT-4o** for analysis
5. **GPT-4o** evaluates the video content against the retrieved rules and returns a structured JSON report with violations, severities, and a markdown summary
6. **Results are persisted** in a SQLite database and displayed in the UI with real-time polling
7. **User can chat** with the AI about the audit results for deeper analysis

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **AI Orchestration** | LangGraph | Stateful DAG workflow for multi-step AI pipeline |
| **LLM** | Azure OpenAI GPT-4o | Compliance analysis and report generation |
| **Embeddings** | Azure OpenAI `text-embedding-3-small` | Document vectorization for RAG retrieval |
| **Vector Store** | Azure AI Search | Stores and retrieves compliance rule embeddings |
| **Video Processing** | Azure Video Indexer | Transcript extraction, OCR, brand/logo detection |
| **Video Download** | yt-dlp | YouTube video downloading |
| **Backend Framework** | FastAPI | Async REST API with background task processing |
| **Frontend** | Jinja2 + Vanilla JS | Glassmorphism UI with real-time polling |
| **Database** | SQLite + SQLAlchemy | Audit record persistence and history |
| **Observability** | Azure Monitor + OpenTelemetry | Request tracing, error tracking, performance metrics |
| **LLM Debugging** | LangSmith | LLM call tracing and prompt evaluation |
| **Package Manager** | uv | Fast Python dependency management |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- Azure account with the following services provisioned:
  - Azure OpenAI (GPT-4o + text-embedding-3-small deployments)
  - Azure AI Search
  - Azure Video Indexer
  - Azure Application Insights *(optional, for telemetry)*

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YourUsername/brand-guardian-ai.git
cd brand-guardian-ai

# 2. Create and activate virtual environment
uv venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
uv sync

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your Azure credentials (see .env.example for all required variables)

# 5. Index the compliance knowledge base (one-time setup)
python -m backend.scripts.index_documents

# 6. Start the server
uvicorn backend.src.api.server:app --reload --port 8000
```

Open **http://localhost:8000** in your browser and start auditing!

### Running a CLI Audit (Alternative)

```bash
# Edit the video_url in main.py, then run:
python main.py
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/audit` | Start a new compliance audit (async) |
| `GET` | `/status/{task_id}` | Check audit processing status |
| `GET` | `/history?limit=10` | Retrieve recent audit records |
| `POST` | `/chat` | Ask follow-up questions about an audit |
| `GET` | `/health` | Health check endpoint |

### Example Request

```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID", "region": "Europe"}'
```

### Example Response

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING"
}
```

---

## 📁 Project Structure

```
brand-guardian-ai/
├── main.py                          # CLI entry point for standalone audit runs
├── pyproject.toml                   # Project metadata & dependencies (uv)
├── .env.example                     # Template for required environment variables
│
├── backend/
│   ├── Dockerfile                   # Container configuration
│   ├── data/                        # Compliance knowledge base documents
│   │   ├── global-compliance-handbook.txt
│   │   ├── 1001a-influencer-guide-508_1.pdf
│   │   └── youtube-ad-specs.pdf
│   │
│   ├── scripts/
│   │   └── index_documents.py       # Knowledge base indexing script (PDF/TXT → Azure AI Search)
│   │
│   └── src/
│       ├── api/
│       │   ├── server.py            # FastAPI app — all REST endpoints
│       │   ├── models.py            # SQLAlchemy ORM models (AuditRecord)
│       │   ├── telemetry.py         # Azure Monitor / OpenTelemetry setup
│       │   ├── templates/
│       │   │   └── index.html       # Frontend UI (glassmorphism design)
│       │   └── static/              # Static assets
│       │
│       ├── graph/
│       │   ├── workflow.py          # LangGraph DAG definition (Indexer → Auditor → END)
│       │   ├── nodes.py             # Node logic — video indexing + RAG compliance audit
│       │   └── state.py             # TypedDict state schema (VideoAuditState)
│       │
│       └── services/
│           └── video_indexer.py     # Azure Video Indexer service connector
│
├── test_audit.py                    # Integration test for audit endpoint
└── test_health.py                   # Health check test
```

---

## 🔐 Security

- All API keys and credentials are loaded from environment variables via `.env` (never committed to git)
- `.env.example` provides a safe template with placeholder values
- Azure `DefaultAzureCredential` is used for Video Indexer authentication (supports managed identity in production)

---

## 📊 Observability

Brand Guardian AI includes **production-grade observability** out of the box:

- **Azure Application Insights** — Automatically captures HTTP request metrics, error rates, response times, and dependency calls via OpenTelemetry
- **LangSmith Tracing** — Every LLM invocation (prompts, completions, token usage, latency) is traced for debugging and cost monitoring
- **Structured Logging** — All components use Python's `logging` module with consistent formatting for easy log aggregation

---

## 🧠 Key Engineering Decisions

| Decision | Rationale |
|---|---|
| **LangGraph over LangChain Chains** | Provides explicit state management, conditional branching support, and DAG visualization — better suited for multi-step AI workflows |
| **Background Tasks over WebSockets** | Video processing takes 2–5 minutes; HTTP polling with `BackgroundTasks` is simpler and more reliable than maintaining WebSocket connections |
| **RAG over fine-tuning** | Compliance rules change frequently — RAG allows instant knowledge base updates without retraining. Documents are chunked (1000 chars, 200 overlap) for optimal retrieval |
| **Region-aware prompting** | Different markets have different regulations (GDPR in EU, FTC in US, ASCI in India) — the region parameter customizes both the retrieval query and the system prompt |
| **SQLite for persistence** | Lightweight, zero-config database ideal for development and single-server deployments. Easy to swap for PostgreSQL in production |

---

## 📄 License

This project is for educational and portfolio purposes.

---

<p align="center">
  <strong>Built with ❤️ by Pardeep Nirwan</strong><br/>
  <em>Azure AI • LangGraph • FastAPI • GPT-4o</em>
</p>
