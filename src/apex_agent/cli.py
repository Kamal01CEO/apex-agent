"""Command Line Interface for Apex Agent using Typer and Rich."""

import os
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from apex_agent.agent.runtime import MemoryAgentRuntime
from apex_agent.agent.tools import MemoryAgentTools
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
    graph = EntityGraphEngine()

    files_to_process = []
    if target.is_dir():
        for ext in ("*.txt", "*.pdf", "*.eml", "*.md"):
            files_to_process.extend(list(target.glob(ext)))
    else:
        files_to_process = [target]

    if not files_to_process:
        console.print(f"[yellow]No supported files found in {target}[/yellow]")
        return

    with console.status("[bold cyan]Ingesting documents & extracting entities...[/bold cyan]"):
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
    else:
        console.print("[dim]No direct relationship links recorded yet.[/dim]")


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
