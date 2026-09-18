"""Bridge to execute Hermes directly using the founder's active model (zai.glm-5)."""

import subprocess
from typing import Optional


class HermesBridge:
    """Invokes Hermes CLI or returns grounded synthesis directly."""

    @staticmethod
    def ask_hermes(prompt: str, session_id: Optional[str] = None) -> str:
        """Runs prompt through Hermes engine directly."""
        cmd = ["hermes", "chat", "-q", prompt]
        if session_id:
            cmd.extend(["--resume", session_id])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45,
            )
            stdout = res.stdout

            # Extract assistant speech box from output
            if "╭─ ⚕ Hermes" in stdout:
                parts = stdout.split("╭─ ⚕ Hermes")[-1].split("╰─")[0]
                lines = [l.strip(" │") for l in parts.split("\n") if l.strip(" │")]
                return "\n".join(lines).strip()

            # Fallback to stripped raw stdout
            lines = [l for l in stdout.split("\n") if not l.startswith("│") and not l.startswith("╭") and not l.startswith("╰")]
            clean = "\n".join(lines).strip()
            return clean if clean else stdout.strip()
        except Exception as e:
            return f"Hermes bridge error: {e}"
