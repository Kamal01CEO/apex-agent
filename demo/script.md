# Apex Agent — Live Hackathon Demonstration Guide

> **Problem Statement**: AI for Everyday Life — The Memory Agent (★★★★☆)
> **Product**: Apex Agent — Autonomous Chief of Staff for Solo Founders
> **Presenter**: Kamal Rai | Founder, ApexArcGlobal

---

## 🎬 The 6-Minute Live Judge Demo Flow

### 1. Multi-Modal Ingestion (Cross-Data Ingestion)
Show how Apex Agent unifies diverse files into structured memory chunks with exact provenance:

```bash
apex ingest tests/fixtures/
```
*Say to judges*:
> "People lose data because notes, WhatsApp chats, emails, and PDFs are siloed. Apex Agent normalizes all 4 formats into structured `MemoryEvent` units, chunks them with an 80-token overlap, and embeds them locally using `all-MiniLM-L6-v2` into SQLite FTS5."

---

### 2. Hybrid Search & Source Attribution
Demonstrate precision retrieval with 70% dense vector + 30% BM25 keyword matching:

```bash
apex search "Sequoia valuation"
```
*Say to judges*:
> "Notice the source references: every chunk points to its exact origin (e.g. `whatsapp:sample_whatsapp.txt:Rahul:2026-09-15`). It gives exact confidence tiers (`EXACT`, `SEMANTIC`, `WEAK`), ensuring we never drift from grounded data."

---

### 3. Context & Entity-Relationship Graph
Explore the multi-hop knowledge graph:

```bash
apex entities "Rahul"
apex entities "Acme"
```
*Say to judges*:
> "We don't just dump text. The agent builds a relational graph in SQLite connecting People, Organizations, and Deals:
> - *Sarah Jenkins* ➔ `employed_by` ➔ *Acme Corp*
> - *Acme Corp* ➔ `client_of` ➔ *ApexArcGlobal ($45K + $6K/mo retainer)*
> - *Rahul Sequoia* ➔ `proposing` ➔ *Seed Round ($2M @ $10M pre-money)*"

---

### 4. Cross-Source Conflict Detection & Grounded Q&A
Demonstrate how the agent detects conflicting information across sources rather than guessing or hallucinating:

```bash
# View detected conflicts
apex conflicts

# Ask a direct question about contested terms
apex ask "What are the payment terms with Acme Corp?"
```
*Say to judges*:
> "When sources disagree — meeting notes state Net 15, but a follow-up email states Net 30 — generic chatbots hallucinate or silently guess. Apex Agent identifies the contradiction, explains the discrepancy, and presents both sources with exact timestamps."

---

### 5. Anti-Hallucination & Zero-Invent Refusal
Ask the agent about an unrecorded company:

```bash
apex ask "What deal did Microsoft offer us?"
```
*Say to judges*:
> "Unlike typical LLMs that make up plausible deals, our anti-hallucination guard executes a strict refusal protocol: *'Information Not Found in Memory'*. It confirms Sequoia and Acme are in memory, but refuses to invent a Microsoft deal."

---

### 6. BONUS: Autonomous Actions, Cold Outreach & Self-Improving Follow-Ups
Show the agent acting as a true autonomous operator with hands:

```bash
# 1. Discover enterprise leads matching ICP
apex run-goal "Scrape enterprise SaaS leads for ApexArcGlobal"

# 2. Dispatch personalized cold outreach
apex run-goal "Send cold outreach email to Ali Ghodsi at Databricks"

# 3. Schedule automated cron watchdog for follow-ups
apex run-goal "Schedule a follow-up cron watchdog for Ali Ghodsi to check if he replies in 2 days"

# 4. Self-Improvement Engine (Diagnose & improve unreplied emails)
apex run-goal "Ali Ghodsi didn't reply to our first email. Analyze why and autonomously improve the follow-up email"

# 5. Ingest WhatsApp conversation on the fly
apex run-goal "Save this WhatsApp conversation: Rahul from Sequoia agreed to meet next Tuesday at 3pm IST to discuss the $2M seed round"

# 6. Schedule confirmed meeting to calendar
apex run-goal "Schedule a strategic meeting with Rahul from Sequoia on our calendar"
```
*Say to judges*:
> "A true autonomous agent doesn't just chat. It executes tools:
> 1. It discovers leads and logs them to `pipeline.json`.
> 2. It writes real outreach files in `data/drafts/`.
> 3. It schedules cron watchdogs in `scheduled_tasks.json`.
> 4. **Self-Improvement**: When an email is ignored, it diagnoses *why* (too long, technical jargon), pivots to a 3-sentence pain-to-outcome pitch, and drafts an improved follow-up offer.
> 5. It manages calendar bookings and syncs them into memory."

---

### 7. Morning Intelligence Briefing
Trigger the autonomous founder briefing:

```bash
apex brief
```
*Say to judges*:
> "Every morning at 07:00 AM, the autonomous daemon reviews all memories, active deals, upcoming calls, and unresolved contract conflicts, and texts an actionable executive brief to the founder's Telegram."
