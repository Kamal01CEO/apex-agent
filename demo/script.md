# Apex Agent — Hackathon Demo Walkthrough

> Problem Statement: **AI for Everyday Life — The Memory Agent**
> Built by: Kamal Rai | ApexArcGlobal

Follow these 6 steps to demonstrate that Apex Agent satisfies and exceeds every single hackathon requirement.

---

### Step 1: Multi-Modal Ingestion (Across 4 Data Types)
Show how the agent normalizes and ingests WhatsApp chats, emails, notes, and PDFs:

```bash
# Ingest all multi-modal test fixtures
apex ingest tests/fixtures/
```
**What to point out to judges:**
- Notice how different source formats are unified into structured memory events with exact provenance metadata.
- Text is automatically chunked into 400-token windows with 80-token overlap, embedded, and indexed into SQLite with FTS5 and vector tables.

---

### Step 2: Hybrid Search with Source Provenance
Search across WhatsApp messages, notes, and emails with combined keyword + semantic matching:

```bash
apex search "Sequoia valuation"
```
**What to point out to judges:**
- Demonstrates **70% Vector + 30% BM25 hybrid ranking**.
- Shows exact confidence ratings (`EXACT`, `SEMANTIC`, `WEAK`).
- Shows clickable-style source references (e.g. `whatsapp:sample_whatsapp.txt:Rahul Sequoia:2026-09-15`).

---

### Step 3: Context & Relationships Knowledge Graph
Traverse connections between people, companies, events, and documents:

```bash
apex entities "Rahul"
apex entities "Acme"
```
**What to point out to judges:**
- The agent doesn't just store raw text; it extracts entities and builds a live relational graph:
  - *Sarah Jenkins* -> `employed_by` -> *Acme Corp*
  - *Acme Corp* -> `negotiating_with` -> *ApexArcGlobal*
  - *Rahul Sequoia* -> `proposing` -> *$2M Seed Round @ $10M Valuation*
  - *Data pipeline stalls* -> `pain_point_for` -> *Acme Corp*

---

### Step 4: Conflict & Contradiction Detection
Demonstrate how the agent catches conflicting information across different sources rather than guessing or silently picking one:

```bash
# View all detected contradictions
apex conflicts

# Ask a direct question about contested terms
apex ask "What are the payment terms with Acme Corp?"
```
**What to point out to judges:**
- The agent flags that the meeting notes agreed on **Net 15 days**, but Sarah Jenkins' subsequent email stated corporate policy requires **Net 30 days**.
- Explains why they contradict and presents both versions with exact timestamps and sources.

---

### Step 5: Anti-Hallucination & Refusal Protocol
Ask the agent about something that does NOT exist in its memory:

```bash
apex ask "What deal did Microsoft offer us?"
```
**What to point out to judges:**
- Unlike generic LLMs that hallucinate plausible-sounding answers, Apex Agent strictly adheres to its anti-hallucination protocol:
  - Outputs: `"Information Not Found in Memory"`
  - Explains what deals *are* present in memory (Sequoia, Acme Corp) and confirms Microsoft is nowhere in the records.

---

### Step 6: BONUS — Autonomous Chief of Staff
Show the autonomous agent acting proactively on recalled memory without waiting for user prompts:

```bash
# Generate Founder Morning Intelligence Briefing
apex brief

# (Optional) Run the 24/7 background autonomous cron daemon
apex daemon
```
**What to point out to judges:**
- Assembles upcoming schedules, active deals, and highlights urgent discrepancies (like the Net 15 vs Net 30 payment dispute) into an actionable morning brief delivered to the founder's Telegram.
