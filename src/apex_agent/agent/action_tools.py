"""Action Tools for Autonomous and Conversational Execution."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from apex_agent.config import DATA_DIR, MEMORY_MD_PATH
from apex_agent.intelligence.conflicts import ConflictDetector
from apex_agent.intelligence.entities import EntityGraphEngine
from apex_agent.memory.index import SQLiteMemoryIndex
from apex_agent.memory.search import HybridSearchEngine


class ActionTools:
    """Provides tools the agent can autonomously call in the conversation loop."""

    def __init__(self, index: SQLiteMemoryIndex = None):
        self.index = index or SQLiteMemoryIndex()
        self.search_engine = HybridSearchEngine(index=self.index)
        self.graph_engine = EntityGraphEngine()
        self.conflict_detector = ConflictDetector()
        self.drafts_dir = DATA_DIR / "drafts"
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline_file = DATA_DIR / "pipeline.json"

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """OpenAI-compatible tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "memory_search",
                    "description": "Searches multi-modal personal memory (WhatsApp, emails, PDFs, notes) with hybrid retrieval.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search term or question to search memory for"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "entity_lookup",
                    "description": "Explores the relational knowledge graph for a specific person, organization, deal, or topic.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The name of the entity to inspect"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_conflicts",
                    "description": "Checks for recorded factual discrepancies or contradictions across sources.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "draft_email",
                    "description": "Drafts and queues an outbound email response grounded in memory context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string", "description": "Email address or contact name"},
                            "subject": {"type": "string", "description": "Subject line"},
                            "body": {"type": "string", "description": "The email body text"},
                            "context_notes": {"type": "string", "description": "Reason or rationale for this draft"}
                        },
                        "required": ["recipient", "subject", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_pipeline",
                    "description": "Updates CRM deal status, stage, or interaction notes for a prospect or client.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company": {"type": "string", "description": "Company or lead name"},
                            "stage": {"type": "string", "description": "Stage: researched | contacted | replied | meeting | proposal | won | lost"},
                            "deal_value": {"type": "string", "description": "Optional monetary valuation or retainer size"},
                            "notes": {"type": "string", "description": "Latest interaction notes"}
                        },
                        "required": ["company", "stage"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_fact",
                    "description": "Saves a permanent verified factual note to durable MEMORY.md.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fact": {"type": "string", "description": "The durable fact or preference to remember"}
                        },
                        "required": ["fact"]
                    }
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Executes a tool call and returns a stringified observation."""
        try:
            if name == "memory_search":
                query = args.get("query", "")
                results = self.search_engine.search(query, limit=5)
                if not results:
                    return "No matching memories found."
                out = []
                for idx, r in enumerate(results, 1):
                    out.append(f"[{idx}] Source: {r.chunk.source_ref} ({r.confidence.value})\n{r.chunk.content.strip()}")
                return "\n\n".join(out)

            elif name == "entity_lookup":
                name_arg = args.get("name", "")
                ctx = self.graph_engine.get_entity_context(name_arg)
                return json.dumps(ctx, indent=2)

            elif name == "check_conflicts":
                conflicts = self.conflict_detector.get_unresolved_conflicts()
                return json.dumps(conflicts, indent=2) if conflicts else "No unresolved conflicts detected."

            elif name == "draft_email":
                rec = args.get("recipient", "")
                subj = args.get("subject", "")
                body = args.get("body", "")
                notes = args.get("context_notes", "")
                draft_id = f"draft_{int(datetime.now().timestamp())}_{rec.split('@')[0]}"
                draft_path = self.drafts_dir / f"{draft_id}.md"

                content = (
                    f"# Outbound Draft: {subj}\n"
                    f"- **To**: {rec}\n"
                    f"- **Created**: {datetime.now().isoformat()}\n"
                    f"- **Context**: {notes}\n\n"
                    f"## Body\n\n{body}\n"
                )
                draft_path.write_text(content, encoding="utf-8")
                return f"Draft created successfully at {draft_path.name} (queued for sending)."

            elif name == "update_pipeline":
                comp = args.get("company", "")
                stage = args.get("stage", "")
                val = args.get("deal_value", "TBD")
                notes = args.get("notes", "")

                data = {}
                if self.pipeline_file.exists():
                    try:
                        data = json.loads(self.pipeline_file.read_text(encoding="utf-8"))
                    except Exception:
                        data = {}

                leads = data.setdefault("leads", {})
                leads[comp] = {
                    "company": comp,
                    "stage": stage,
                    "deal_value": val,
                    "notes": notes,
                    "updated_at": datetime.now().isoformat()
                }
                self.pipeline_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return f"Pipeline updated: {comp} marked as '{stage}' ({val})."

            elif name == "save_fact":
                fact = args.get("fact", "")
                with open(MEMORY_MD_PATH, "a", encoding="utf-8") as f:
                    f.write(f"\n- [{datetime.now().strftime('%Y-%m-%d')}] {fact}\n")
                return f"Fact saved to MEMORY.md: {fact}"

            return f"Unknown tool: {name}"
        except Exception as e:
            return f"Error executing tool {name}: {str(e)}"
