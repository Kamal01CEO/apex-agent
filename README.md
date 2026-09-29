# Apex Agent ⚡

> **Autonomous Personal Memory Agent for Solo Founders, Knowledge Workers, and Researchers**  
> An academic project demonstrating real-world AI agent architecture with multi-source memory, reasoning, and autonomous actions.

---

## 🎯 What is Apex Agent?

Apex Agent is a production-grade autonomous AI agent designed to solve a fundamental problem: **information fragmentation**. 

As a solo founder or knowledge worker, your information lives everywhere—WhatsApp chats, emails, PDFs, notes, calendar events. Traditional tools search these in isolation. Apex Agent unifies them into a searchable memory layer that understands relationships, detects conflicts, and acts autonomously.

**This is NOT a chatbot.** It's an autonomous agent that:
- Ingests data from multiple sources (WhatsApp, PDF, Email, Notes)
- Builds a knowledge graph of entities and relationships
- Detects conflicting information across sources
- Refuses to hallucinate—every answer cites its sources
- Sends you proactive alerts via Telegram
- Drafts emails, schedules follow-ups, and monitors your pipeline

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         APEX AGENT                               │
├─────────────────────────────────────────────────────────────────┤
│  INGESTION LAYER                                                 │
│  ├── WhatsApp Parser (.txt exports)                             │
│  ├── PDF Extractor (pdfplumber)                                 │
│  ├── Email Parser (.eml files)                                  │
│  └── Notes Parser (Markdown with frontmatter)                   │
├─────────────────────────────────────────────────────────────────┤
│  MEMORY LAYER                                                    │
│  ├── Chunker (400 tokens, 80 overlap)                           │
│  ├── Embedder (BGE-small-en-v1.5, 384-dim)                      │
│  ├── Vector Store (LanceDB for ANN)                             │
│  ├── FTS5 Index (BM25 keyword search)                            │
│  └── Hybrid Search (0.70 cosine + 0.30 BM25)                    │
├─────────────────────────────────────────────────────────────────┤
│  INTELLIGENCE LAYER                                              │
│  ├── Entity Graph (People ↔ Organizations ↔ Deals)              │
│  ├── Conflict Detector (flags contradicting sources)            │
│  ├── Anti-Hallucination Guard (context fencing, <0.15 refusal)  │
│  └── Semantic Cache (LRU + similarity matching)                 │
├─────────────────────────────────────────────────────────────────┤
│  AUTONOMOUS LAYER                                                │
│  ├── Email Composer (drafts follow-ups)                         │
│  ├── Pipeline Watchdog (monitors deal status)                   │
│  ├── Morning Brief (APScheduler cron, 07:00 daily)              │
│  └── Telegram Gateway (proactive alerts)                        │
├─────────────────────────────────────────────────────────────────┤
│  CONNECTORS & INTEGRATIONS                                       │
│  ├── Baileys (WhatsApp Web bridge)                              │
│  ├── Gmail API (OAuth2 + SMTP/IMAP)                             │
│  ├── Telegram Bot API                                           │
│  ├── Playwright MCP (browser automation)                        │
│  └── PPT Master (presentation generation)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Capabilities

### 1. Cross-Source Memory Ingestion
Unified `MemoryEvent` dataclass ingests from:
- **WhatsApp** - Chat exports parsed with regex, sender attribution preserved
- **PDFs** - Page-by-page extraction via pdfplumber
- **Emails** - RFC 2822 .eml parsing with full header retention
- **Notes** - Markdown with YAML frontmatter support

### 2. Hybrid Search Engine
Combines semantic understanding with exact keyword matching:
- **Vector Search**: LanceDB ANN for O(log n) retrieval (50-100x faster than brute-force)
- **FTS5**: SQLite BM25 for precise keyword matching
- **Hybrid Scoring**: 70% semantic + 30% lexical
- **Source Attribution**: Every result includes provenance (e.g., `whatsapp:Rahul:msg_123`)

### 3. Knowledge Graph
Entity-relationship mapping:
- Extracts People, Organizations, Topics, Events from chunks
- Builds relationship edges (Person `works_with` Person, Org `has_deal` Deal)
- Multi-hop traversal for "Who is involved with Project Alpha?"

### 4. Conflict Detection
Detects when sources disagree:
- "Sarah's meeting is on Tuesday" (WhatsApp) vs "Meeting with Sarah Thursday" (Email)
- Stores both claims with full provenance
- Flags conflicts in responses—"I found conflicting information..."

### 5. Anti-Hallucination Guard
Five-layer safety system prevents inventing facts:
1. **Context Fencing**: Agent only sees retrieved chunks, not raw knowledge
2. **Confidence Scoring**: Exact/semantic/weak/none levels
3. **Refusal Protocol**: Below 0.15 confidence → "I don't have this in memory"
4. **Zero-Invent**: Never generates claims without source
5. **Source Citations**: Every answer shows where information came from

### 6. Autonomous Actions
Agent acts without prompting:
- **Morning Brief** (07:00 cron): Upcoming events, stale contacts, recent changes
- **Pipeline Watchdog**: Detects deals going cold, drafts follow-up emails
- **Telegram Alerts**: Push notifications for important events
- **Email Dispatch**: Real SMTP email sending via Gmail OAuth

---

## 🔌 Connectors & Integrations

| Connector | Purpose | Status |
|-----------|---------|--------|
| **Baileys** | WhatsApp Web bridge for real-time chat ingestion | ✅ Integrated |
| **Gmail OAuth** | Email ingestion and dispatch via Gmail API | ✅ Integrated |
| **Telegram Bot** | Proactive alerts and two-way chat | ✅ Integrated |
| **Playwright MCP** | Browser automation for web scraping | ✅ Integrated |
| **PPT Master** | Generate presentations from memory | ✅ Integrated |
| **File Watcher** | Auto-ingest new files in watched directories | ✅ Built-in |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Kamal01CEO/apex-agent.git
cd apex-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Dependencies
- Python 3.11+
- SQLite 3 (built-in)
- LanceDB (vector storage)
- Sentence Transformers (BGE-small-en-v1.5)
- OpenAI-compatible LLM API

---

## 🚀 Quick Start

```bash
# Ingest data sources
apex ingest ~/Documents/whatsapp_exports/
apex ingest ~/Documents/pdfs/
apex ingest ~/Documents/emails/

# Search across all sources
apex search "What did Rahul say about the deadline?"

# Interactive chat mode
apex chat

# View entity graph
apex entities

# Check for conflicts
apex conflicts

# Start autonomous mode (morning brief + alerts)
apex autonomous --telegram-bot-token $TOKEN --chat-id $CHAT_ID
```

---

## 🎓 Academic Context

This project was developed as part of an academic exploration into autonomous AI agents and personal memory systems. It demonstrates:

1. **Multi-Modal Data Ingestion**: Unified pipeline for heterogeneous data sources
2. **Hybrid Retrieval**: Combining neural (semantic) and symbolic (keyword) search
3. **Knowledge Graphs**: Entity-relationship modeling in SQLite
4. **Conflict Resolution**: Detecting and surfacing contradictory information
5. **Anti-Hallucination**: Rigorous grounding and source attribution
6. **Autonomous Actions**: Agentic behavior with cron-based scheduling

### Key Research Questions
- How can personal AI agents maintain accurate memory without hallucinating?
- What data structures efficiently capture entity relationships across sources?
- How do we detect and surface conflicting information to users?
- What autonomous actions are appropriate for a personal memory agent?

---

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| Chunk Size | 400 tokens (80 overlap) |
| Embedding Dimension | 384 (BGE-small) |
| Vector Search | O(log n) via LanceDB ANN |
| Hybrid Scoring | 0.70 cosine + 0.30 BM25 |
| Refusal Threshold | < 0.15 confidence |
| Cache TTL | 1 hour (semantic similarity) |
| Ingestion Speed | ~10ms per chunk (local embedding) |

---

## 🛠️ Project Structure

```
apex-agent/
├── src/apex_agent/
│   ├── ingest/          # WhatsApp, PDF, Email, Notes parsers
│   ├── memory/          # Chunker, embedder, vector store, hybrid search
│   ├── intelligence/   # Entity graph, conflicts, anti-hallucination guard
│   ├── agent/           # Runtime, tools, conversation loop
│   ├── autonomous/      # Scheduler, notifier, action triggers
│   ├── channels/        # API integrations (Telegram, Gmail, etc.)
│   └── cli.py          # Typer CLI interface
├── integrations/        # MCP servers, bridges (Baileys, Playwright, etc.)
├── tests/              # Pytest test suite
├── demo/               # Demo data and scripts
├── docs/               # Architecture documentation
└── data/               # Runtime data (gitignored)
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ingest_and_search.py -v

# Run with coverage
pytest --cov=src/apex_agent tests/
```

---

## 📬 How to Contact the Agent

The agent exposes multiple interfaces:

### CLI
```bash
apex chat  # Interactive terminal session
```

### Telegram
1. Create a bot via [@BotFather](https://t.me/botfather)
2. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
3. Start autonomous mode: `apex autonomous`
4. Message your bot on Telegram

### Gmail Integration
```bash
apex auth-email  # OAuth flow for Gmail
apex check-inbox  # Monitor for new emails
```

### WhatsApp (via Baileys)
The `integrations/baileys` folder contains a WhatsApp Web bridge for chat ingestion.

---

## 📄 License

MIT License - Open source for academic and personal use.

---

## 👤 Author

**Kamal**  
ApexArc Global Founder  
[GitHub](https://github.com/Kamal01CEO) | [ApexArc Global](https://apexarc.global)

This project was built as an exploration into personal AI agents that truly work for their users—grounding knowledge in real data, acting autonomously, and never inventing facts.

---

## 🙏 Acknowledgments

Built with inspiration from:
- Hermes Agent Framework (personal AI OS architecture)
- Modern RAG systems and their limitations
- The need for a truly personal, trustworthy AI memory layer

---

**If you find this useful, please ⭐ star the repo!**
