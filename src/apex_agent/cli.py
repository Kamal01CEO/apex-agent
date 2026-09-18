"""Command Line Interface for Apex Agent with Interactive Chat & Session Memory."""

import os
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from apex_agent.agent.conversation_loop import ConversationalAgent
from apex_agent.agent.runtime import MemoryAgentRuntime
from apex_agent.agent.session_db import SessionDB
from apex_agent.autonomous.scheduler import AutonomousMemoryDaemon
from apex_agent.intelligence.conflicts import ConflictDetector
from apex_agent.intelligence.entities import EntityGraphEngine
from apex_agent.memory.pipeline import IngestionPipeline
from apex_agent.memory.search import HybridSearchEngine

app = typer.Typer(
    name="apex",
    help="Apex Agent — Personal Searchable Memory Assistant for Solo Founders",
    add_completion=False,
)
console = Console()


@app.command("chat")
def chat(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Resume an existing session ID"),
):
    """Starts an interactive conversational session with background tools and session persistence."""
    agent = ConversationalAgent(session_id=session)
    sess_id = agent.session_id

    console.print(
        Panel(
            f"[bold cyan]Apex Conversational Agent[/bold cyan] (Session: [bold yellow]{sess_id}[/bold yellow])\n"
            "Talk normally. The agent uses background memory search, knowledge graphs, and action tools.\n"
            "Type [bold red]/exit[/bold red] or [bold red]/quit[/bold red] to end session.",
            title="Apex Interactive Console",
            border_style="cyan",
        )
    )

    def tool_callback(name: str, args: dict):
        console.print(f"  [dim cyan]⚡ Tool call:[/dim cyan] [bold]{name}[/bold]({args})")

    while True:
        try:
            user_msg = console.input("\n[bold green]You[/bold green] > ").strip()
            if not user_msg:
                continue
            if user_msg.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print(f"[yellow]Session {sess_id} saved. Goodbye![/yellow]")
                break

            with console.status("[bold cyan]Agent reasoning & acting...[/bold cyan]"):
                reply = agent.interact(user_msg, on_tool_call=tool_callback)

            console.print(f"\n[bold cyan]Apex[/bold cyan] > {reply}")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[yellow]Session {sess_id} saved.[/yellow]")
            break


@app.command("sessions")
def sessions(
    limit: int = typer.Option(15, "--limit", "-l", help="Number of recent sessions to show"),
):
    """Lists all saved conversational sessions from SQLite."""
    sdb = SessionDB()
    sess_list = sdb.list_sessions(limit=limit)

    if not sess_list:
        console.print("[yellow]No conversational sessions recorded yet.[/yellow]")
        return

    table = Table(title="Saved Chat Sessions (SQLite state.db)", show_header=True, header_style="bold magenta")
    table.add_column("Session ID", style="cyan", width=18)
    table.add_column("Title", style="white")
    table.add_column("Messages", justify="right", width=10)
    table.add_column("Updated At", style="dim", width=22)

    for s in sess_list:
        table.add_row(
            s["id"],
            s["title"],
            str(s["message_count"]),
            s["updated_at"][:19].replace("T", " "),
        )

    console.print(table)


@app.command("run-goal")
def run_goal(
    goal: str = typer.Argument(..., help="Autonomous goal for the agent to achieve using tools"),
):
    """Runs an autonomous goal where the agent reasons, checks memory, and takes real actions."""
    agent = ConversationalAgent()
    console.print(Panel(f"[bold]Executing Autonomous Goal:[/bold] {goal}", title="Autonomous Execution", border_style="green"))

    def tool_callback(name: str, args: dict):
        console.print(f"  [bold yellow]✔ Action Executed:[/bold yellow] [bold]{name}[/bold] -> {args}")

    with console.status("[bold cyan]Agent pursuing goal autonomously...[/bold cyan]"):
        result = agent.interact(
            f"Autonomous Goal: {goal}\nInspect memory, find necessary facts, take required actions (like drafting emails or updating pipeline), and report what you accomplished.",
            on_tool_call=tool_callback
        )

    console.print(Panel(result, title="Goal Outcome Report", border_style="cyan"))


@app.command("ingest")
def ingest(
    path: str = typer.Argument(..., help="Path to file or directory to ingest into memory"),
):
    """Ingests WhatsApp chats, PDFs, .eml emails, or Markdown notes into memory."""
    target = Path(path).resolve()
    if not target.exists():
        console.print(f"[bold red]Error:[/bold red] File or directory not found: {target}")
        raise typer.Exit(1)

    pipeline = IngestionPipeline()

    files_to_process = []
    if target.is_dir():
        for ext in ("*.txt", "*.pdf", "*.eml", "*.md"):
            files_to_process.extend(list(target.glob(ext)))
    else:
        files_to_process = [target]

    if not files_to_process:
        console.print(f"[yellow]No supported files found in {target}[/yellow]")
        return

    with console.status("[bold cyan]Ingesting documents & building knowledge graph...[/bold cyan]"):
        total_events = 0
        for f in files_to_process:
            try:
                events = pipeline.ingest_file(f)
                total_events += len(events)
                console.print(f"  [green]✔[/green] Ingested [bold]{f.name}[/bold] -> {len(events)} events")
            except Exception as e:
                console.print(f"  [red]✘[/red] Failed to ingest {f.name}: {e}")

    console.print(
        Panel(
            f"[bold green]Ingestion Complete![/bold green]\nProcessed {len(files_to_process)} file(s) into {total_events} memory events.",
            title="Apex Memory Ingestion",
            border_style="green",
        )
    )


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results to return"),
):
    """Performs hybrid (FTS5 + Vector) memory retrieval with source attribution."""
    engine = HybridSearchEngine()
    results = engine.search(query, limit=limit)

    if not results:
        console.print("[yellow]No relevant memories found matching query.[/yellow]")
        return

    table = Table(title=f"Hybrid Search Results for: '{query}'", show_header=True, header_style="bold magenta")
    table.add_column("Confidence", style="bold", width=12)
    table.add_column("Score", justify="right", width=8)
    table.add_column("Source Reference", style="cyan", width=32)
    table.add_column("Snippet Preview", style="white")

    for r in results:
        conf_color = "green" if r.confidence.value == "exact" else "blue" if r.confidence.value == "semantic" else "yellow"
        snippet = r.chunk.content.strip().replace("\n", " ")[:90] + "..."
        table.add_row(
            f"[{conf_color}]{r.confidence.value.upper()}[/{conf_color}]",
            f"{r.relevance_score:.3f}",
            r.chunk.source_ref[:32],
            snippet,
        )

    console.print(table)


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Question to ask your memory agent"),
):
    """Answers questions strictly from memory with source citations and anti-hallucination guard."""
    runtime = MemoryAgentRuntime()

    with console.status("[bold cyan]Searching memory & verifying citations...[/bold cyan]"):
        answer = runtime.ask(question)

    console.print(
        Panel(
            answer,
            title="Apex Memory Assistant",
            subtitle="Grounded • Cited • Conflict-Checked",
            border_style="cyan",
        )
    )


@app.command("entities")
def entities(
    name: str = typer.Argument(..., help="Entity name (person, company, or topic)"),
):
    """Explores the entity relationship graph around a specific subject."""
    graph = EntityGraphEngine()
    ctx = graph.get_entity_context(name)

    ents = ctx.get("entities", [])
    rels = ctx.get("relationships", [])

    if not ents and not rels:
        console.print(f"[yellow]No entities found in knowledge graph for '{name}'[/yellow]")
        return

    console.print(f"\n[bold cyan]Knowledge Graph Context: {name}[/bold cyan]")
    if rels:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Entity A", style="green")
        table.add_column("Relationship", style="bold")
        table.add_column("Entity B", style="magenta")
        table.add_column("Context / Quote", style="white")
        table.add_column("Source", style="dim")

        for r in rels:
            table.add_row(
                r["entity_a"],
                r["relation_type"],
                r["entity_b"],
                r["context"][:50] + "...",
                r["source_ref"][:25],
            )
        console.print(table)


@app.command("conflicts")
def conflicts():
    """Lists all detected contradictions across ingested memory sources."""
    detector = ConflictDetector()
    unresolved = detector.get_unresolved_conflicts()

    if not unresolved:
        console.print("[green]✔ Zero data contradictions detected across your sources.[/green]")
        return

    console.print(f"\n[bold red]⚠️ {len(unresolved)} Contradiction(s) Detected Across Sources:[/bold red]\n")
    for idx, c in enumerate(unresolved, 1):
        panel_content = (
            f"[bold]Topic:[/bold] {c['topic']}\n\n"
            f"[cyan]Claim A:[/cyan] {c['claim_a']}\n"
            f"[dim]Source A:[/dim] {c['source_a']} ({c['timestamp_a']})\n\n"
            f"[yellow]Claim B:[/yellow] {c['claim_b']}\n"
            f"[dim]Source B:[/dim] {c['source_b']} ({c['timestamp_b']})\n\n"
            f"[bold]Discrepancy Notes:[/bold] {c['resolution_notes']}"
        )
        console.print(Panel(panel_content, title=f"Conflict #{idx}", border_style="red"))


@app.command("brief")
def brief():
    """Generates the autonomous Morning Founder Briefing from memory."""
    daemon = AutonomousMemoryDaemon()
    with console.status("[bold cyan]Assembling morning intelligence briefing...[/bold cyan]"):
        report = daemon.generate_morning_brief()
    console.print(Panel(report, title="Proactive Morning Briefing", border_style="magenta"))


@app.command("daemon")
def daemon():
    """Starts the 24/7 background autonomous cron daemon."""
    console.print("[bold green]Starting Apex Agent Autonomous Daemon (Press Ctrl+C to stop)...[/bold green]")
    daemon = AutonomousMemoryDaemon()
    try:
        daemon.start()
    except (KeyboardInterrupt, SystemExit):
        console.print("[yellow]Daemon stopped.[/yellow]")


def main():
    app()


if __name__ == "__main__":
    main()
