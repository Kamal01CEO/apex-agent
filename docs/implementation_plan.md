# Apex Agent — 24-Hour Battle Plan

> **Clock starts**: Now (12:10 AM, Sep 19)
> **Deadline**: ~12:00 AM, Sep 20
> **Rule**: Ship what wins. Cut everything else.

---

## What WINS the Hackathon vs What Gets Cut

### ✅ KEEP (Judges evaluate these)

| Requirement | What We Build | Time |
|---|---|---|
| Cross-data retrieval | 4 ingesters: WhatsApp, PDF, email (.eml), notes (.md) | 3h |
| Hybrid search | SQLite FTS5 + sqlite-vec, source refs on every result | 3h |
| Relationships | Entity extraction + relationship graph in SQLite | 2h |
| Conflicts | Detect contradictions, show both sides with sources | 1.5h |
| Anti-hallucination | Context fencing + confidence scoring + refusal | 1.5h |
| BONUS: Autonomous | 2 cron jobs + Telegram alerts + action from memory | 3h |
| Demo | Pre-loaded data, killer queries, clean presentation | 2h |

### ❌ CUT (Not needed to win)

- ~~Web dashboard~~ → CLI is enough for demo
- ~~Content engine (blogs, X posts)~~ → not in problem statement
- ~~Cold outreach engine~~ → show simpler autonomous action
- ~~Self-improvement loop~~ → after hackathon
- ~~LinkedIn/Exa/Firecrawl MCP~~ → not needed for memory demo
- ~~Pipeline micro-CRM~~ → simplify to basic tracking
- ~~Weekly reports~~ → just morning brief
- ~~Screenshot OCR~~ → save for stretch goal
- ~~Calendar ingester~~ → save for stretch goal if time

---

## 24-Hour Timeline

```
NOW ─────────────────────────────────────────── DEADLINE
00:10                  08:00       16:00       00:00
  │                      │           │           │
  ├── SPRINT 1 ──────────┤           │           │
  │   Foundation +       │           │           │
  │   Ingestion +        │           │           │
  │   Search             │           │           │
  │                      │           │           │
  │                      ├── SPRINT 2 ┤          │
  │                      │  Entities + │          │
  │                      │  Conflicts +│          │
  │                      │  Anti-halluc│          │
  │                      │  + CLI demo │          │
  │                      │            │          │
  │                      │            ├── SPRINT 3
  │                      │            │  Autonomous
  │                      │            │  + Telegram
  │                      │            │  + Demo
  │                      │            │  + Submit
```

---

## SPRINT 1: Foundation (00:10 → 08:00) — 8 hours

### Hour 0-1: Project Scaffold
```
✅ git init apex-agent
✅ pyproject.toml (uv, dependencies)
✅ .gitignore, .env.example, README stub
✅ src/apex_agent/ package structure
✅ LLM client with silent fallback (9router → local Qwen)
✅ Config loader (.env based)

git commit: "feat: project scaffold + LLM client with silent fallback"
```

### Hour 1-3: Ingesters (4 types)
```
✅ MemoryEvent dataclass (the universal container)
✅ WhatsApp parser (regex-based .txt export parser)
✅ PDF ingester (pdfplumber, page-by-page)
✅ Email ingester (python email.parser for .eml files)
✅ Note ingester (markdown files, frontmatter-aware)
✅ Tests with sample fixtures

git commit: "feat: multi-format ingestion (WhatsApp, PDF, email, notes)"
```

### Hour 3-6: SQLite Hybrid Index + Search
```
✅ SQLite schema (chunks, chunks_fts, entities, relationships, conflicts)
✅ Chunker (400 tokens, 80 overlap)
✅ Embedder (sentence-transformers all-MiniLM-L6-v2 local, or OpenAI fallback)
✅ sqlite-vec integration for vector storage
✅ FTS5 integration for keyword search
✅ Hybrid search: 70% vector + 30% BM25
✅ Source reference on every result
✅ Ingestion pipeline: MemoryEvent → chunk → embed → index

git commit: "feat: hybrid search engine (FTS5 + sqlite-vec) with source refs"
```

### Hour 6-8: Markdown Memory Store + Wire It Up
```
✅ MEMORY.md read/write (curated core facts)
✅ Daily log files (memory/YYYY-MM-DD.md)
✅ Ingest command: `apex ingest <file_or_dir>`
✅ Search command: `apex search "query"`
✅ End-to-end test: ingest sample WhatsApp → search → get cited result
✅ Basic test suite for ingest + search

git commit: "feat: markdown memory store + CLI ingest/search commands"
```

**Sprint 1 deliverable**: You can ingest WhatsApp/PDF/email/notes and search across all of them with source citations.

---

## SPRINT 2: Intelligence (08:00 → 16:00) — 8 hours

### Hour 8-10: Entity Extraction + Relationship Graph
```
✅ Entity extractor (LLM-based: extract people, orgs, topics from chunks)
✅ Entity deduplication (fuzzy match names)
✅ Relationship builder (entity_a → relation → entity_b)
✅ Store in entities + relationships tables
✅ entity_lookup tool: "What do I know about Rahul?"
✅ Graph traversal: find all connected entities + their chunks

git commit: "feat: entity extraction + relationship graph"
```

### Hour 10-12: Conflict Detection + Anti-Hallucination
```
✅ Conflict detector:
   - Group results by entity
   - LLM check: do these statements contradict?
   - Store conflicts with both sources
   - Present both sides in answers
✅ Context fencing (from Hermes memory_manager.py pattern)
✅ Confidence scoring (exact/semantic/weak/none)
✅ Refusal protocol (no data → "I don't have this in memory")
✅ Hallucination guard tests

git commit: "feat: conflict detection + anti-hallucination guard"
```

### Hour 12-14: Agent Runtime
```
✅ Agent runtime (LLM loop with tools)
✅ Tools:
   - memory_search(query, filters) → hybrid search
   - entity_lookup(name) → relationship graph
   - save_memory(content, source) → add to index
   - list_conflicts() → show unresolved conflicts
✅ System prompt: MEMORY.md injected, tool-based retrieval only
✅ Anti-hallucination prompt engineering

git commit: "feat: agent runtime with tool-based retrieval"
```

### Hour 14-16: CLI Polish + Demo Data
```
✅ CLI interface: `apex chat` (interactive agent mode)
✅ CLI: `apex ingest <path>` (batch ingest)
✅ CLI: `apex search <query>` (direct search)
✅ CLI: `apex entities` (show entity graph)
✅ CLI: `apex conflicts` (show conflicts)
✅ Create demo dataset (realistic WhatsApp + PDF + email + notes)
✅ Test all 5 hackathon requirements end-to-end

git commit: "feat: CLI interface + demo dataset"
```

**Sprint 2 deliverable**: Full memory agent that hits ALL 5 core requirements. Demo-ready for the core challenge.

---

## SPRINT 3: Autonomous + Polish (16:00 → 00:00) — 8 hours

### Hour 16-18: Autonomous Actions (BONUS)
```
✅ Telegram notifier (reuse existing Hermes Telegram gateway)
   OR simple python-telegram-bot direct send
✅ Cron job 1: Morning briefing
   - Scan memory for today's events, overdue items, recent changes
   - Format and send to Telegram
✅ Cron job 2: Inbox monitor (if Gmail MCP available)
   - Check for new emails matching known entities
   - Alert: "New email from Rahul about Project Alpha"
   - Link to relevant memory context
✅ Action trigger: agent detects stale contact → drafts follow-up

git commit: "feat: autonomous agent with cron jobs + Telegram alerts"
```

### Hour 18-20: Integration + HUD Bridge
```
✅ Push memory events to Jarvis HUD Engram API (if time)
✅ Register any needed MCP servers in Hermes config
✅ Hermes skill: apex-memory (SKILL.md for Hermes integration)
✅ Test autonomous workflows end-to-end

git commit: "feat: Jarvis HUD + Hermes integration"
```

### Hour 20-22: Demo Polish
```
✅ Demo script (step-by-step what to show judges)
✅ Pre-load demo data that tells a compelling story
✅ Prepare 6 killer demo queries:
   1. Cross-type: "What did Rahul say about the deadline?"
   2. Relationship: "Who is involved with Project Alpha?"
   3. Conflict: "When is the meeting with Sarah?"
   4. Source ref: show citations on every answer
   5. Anti-hallucination: "What about our deal with Microsoft?" → REFUSES
   6. Autonomous: "Agent found Rahul went cold, drafted follow-up"
✅ README.md with architecture diagram, setup instructions, demo GIF
✅ Record demo video (backup in case live demo fails)

git commit: "docs: demo script + README + architecture docs"
```

### Hour 22-24: Testing + Git Cleanup + Submit
```
✅ Run full test suite
✅ Fix any broken tests
✅ Clean git history (squash messy commits if needed)
✅ Final README pass
✅ Tag release: v1.0.0
✅ Submit

git commit: "chore: final tests + cleanup"
git tag: v1.0.0
```

---

## Minimal File Structure (24h scope)

```
apex-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── src/apex_agent/
│   ├── __init__.py
│   ├── config.py              # env + config
│   ├── llm.py                 # silent fallback LLM client
│   ├── models.py              # MemoryEvent, Entity, Relationship, Conflict
│   │
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── whatsapp.py        # WhatsApp .txt parser
│   │   ├── pdf.py             # PDF extractor
│   │   ├── email.py           # .eml parser
│   │   └── notes.py           # Markdown notes
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── index.py           # SQLite FTS5 + sqlite-vec
│   │   ├── search.py          # Hybrid search + source refs
│   │   ├── chunker.py         # Text chunking
│   │   └── store.py           # MEMORY.md + daily logs
│   │
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── entities.py        # Entity extraction + graph
│   │   ├── conflicts.py       # Conflict detection
│   │   └── guard.py           # Anti-hallucination (fence + confidence + refusal)
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── runtime.py         # Agent loop
│   │   └── tools.py           # memory_search, entity_lookup, etc.
│   │
│   ├── autonomous/
│   │   ├── __init__.py
│   │   ├── scheduler.py       # APScheduler + cron jobs
│   │   └── notifier.py        # Telegram notifications
│   │
│   └── cli.py                 # typer CLI: ingest, search, chat, entities
│
├── tests/
│   ├── test_ingest.py
│   ├── test_search.py
│   ├── test_entities.py
│   ├── test_conflicts.py
│   ├── test_guard.py
│   └── fixtures/
│       ├── sample_whatsapp.txt
│       ├── sample.pdf
│       ├── sample.eml
│       └── sample_notes.md
│
├── demo/
│   ├── data/                  # Pre-loaded demo dataset
│   └── script.md              # Demo walkthrough
│
└── data/                      # Runtime (gitignored)
    ├── apex_index.db
    ├── MEMORY.md
    └── memory/
```

**Total files to write: ~25** (including tests and fixtures)

---

## Dependencies (keep minimal)

```toml
[project]
name = "apex-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai",                  # LLM client (OpenAI-compatible)
    "sqlite-vec",              # Vector search in SQLite
    "sentence-transformers",   # Local embeddings
    "pdfplumber",              # PDF extraction
    "typer[all]",              # CLI
    "rich",                    # Pretty terminal output
    "apscheduler",             # Cron scheduler
    "python-dotenv",           # .env loading
    "httpx",                   # Async HTTP (for Telegram, APIs)
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio"]
```

---

## What Makes Us Stand Out vs Generic RAG Apps

| Generic RAG | Our Agent |
|---|---|
| Black-box vector DB | **Human-readable** markdown memory + SQLite you can inspect |
| Dump top-k chunks blindly | **Tool-based retrieval** — agent decides when to search |
| No source tracking | **Every answer cites source** (whatsapp:Rahul:msg_123) |
| Ignores conflicts | **Detects contradictions**, shows both sides |
| Hallucinates freely | **5-layer anti-hallucination** with context fencing from Hermes |
| Passive chatbot | **Autonomous agent** that texts YOU with proactive alerts |
| No relationships | **Entity graph** connecting people↔events↔documents |

---

## Approve to Start Building

Once you say go, I will:
1. Create the project at `~/Documents/apex-agent/` (or your preferred location)
2. `git init` with proper first commit
3. Start Sprint 1 immediately
4. Commit after each major feature

**Ready?**
