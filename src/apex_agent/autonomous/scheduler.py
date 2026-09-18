"""Autonomous Scheduler & Proactive Watchdogs (APScheduler)."""

from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apex_agent.agent.runtime import MemoryAgentRuntime
from apex_agent.autonomous.notifier import TelegramNotifier
from apex_agent.intelligence.conflicts import ConflictDetector
from apex_agent.llm import llm
from apex_agent.memory.search import HybridSearchEngine


class AutonomousMemoryDaemon:
    """Runs 24/7 background cron jobs that act autonomously on memory data."""

    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.runtime = MemoryAgentRuntime()
        self.notifier = TelegramNotifier()
        self.search_engine = HybridSearchEngine()
        self.conflict_detector = ConflictDetector()

    def generate_morning_brief(self) -> str:
        """Assembles morning intelligence report from memory across all ingested documents."""
        # Query upcoming meetings, deadlines, and active client terms
        meetings = self.search_engine.search("meeting call schedule Tuesday Wednesday", limit=4)
        deals = self.search_engine.search("contract valuation payment terms deal", limit=4)
        conflicts = self.conflict_detector.get_unresolved_conflicts()

        brief_chunks = [f"- {m.chunk.source_ref}: {m.chunk.content[:150]}" for m in meetings]
        brief_chunks += [f"- {d.chunk.source_ref}: {d.chunk.content[:150]}" for d in deals]

        prompt = f"""
Generate a concise, crisp Founder Morning Intelligence Briefing.
Current Date: {datetime.now().strftime('%A, %B %d, %Y')}

Relevant Memory Records:
{chr(10).join(brief_chunks)}

Active Discrepancies/Conflicts:
{conflicts}

Output Format:
🌅 *Apex Morning Intel Brief*
• **Upcoming Engagements & Schedule**
• **Active Deals & Key Milestones**
• **Critical Action Items & Warnings** (highlight any conflicting terms)
"""
        messages = [
            {"role": "system", "content": "You are a proactive Chief of Staff. Keep it direct, structured, and actionable."},
            {"role": "user", "content": prompt}
        ]

        brief = llm.chat_completion(messages, temperature=0.2, max_tokens=800)
        return brief

    def run_morning_briefing_job(self):
        """Executed daily at 07:00 or on demand."""
        brief = self.generate_morning_brief()
        self.notifier.send_message(brief)

    def run_conflict_watchdog_job(self):
        """Scans for newly surfaced contradictions."""
        conflicts = self.conflict_detector.get_unresolved_conflicts()
        if conflicts:
            msg = f"⚠️ *Proactive Alert: {len(conflicts)} Data Conflicts Require Review*\n\n"
            for c in conflicts[:3]:
                msg += f"• **{c['topic']}**\n  - {c['source_a']}: \"{c['claim_a'][:60]}...\"\n  - {c['source_b']}: \"{c['claim_b'][:60]}...\"\n"
            self.notifier.send_message(msg)

    def start(self):
        """Registers autonomous workflows and begins scheduler loop."""
        # 1. Daily morning briefing at 07:00 IST
        self.scheduler.add_job(
            self.run_morning_briefing_job,
            CronTrigger(hour=7, minute=0),
            id="morning_briefing",
            name="Daily Founder Morning Brief",
            replace_existing=True
        )

        # 2. Conflict watchdog runs every 30 minutes
        self.scheduler.add_job(
            self.run_conflict_watchdog_job,
            IntervalTrigger(minutes=30),
            id="conflict_watchdog",
            name="Continuous Conflict Watchdog",
            replace_existing=True
        )

        print("⚡ Autonomous Memory Daemon initialized with proactive cron triggers.")
        self.scheduler.start()
