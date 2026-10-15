"""
Git-backed Checkpoint Manager for plateau-to-plateau hill climbing.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class PlateauRecord:
    index: int
    timestamp: str
    git_commit: str
    metric_value: Optional[float]
    description: str
    verified_invariants: List[str]


class CheckpointManager:
    def __init__(self, root_dir: str | Path = "."):
        self.root_dir = Path(root_dir).resolve()
        self.state_dir = self.root_dir / ".telos"
        self.history_file = self.state_dir / "history.json"
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def _run_git(self, args: List[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git"] + args,
            cwd=str(self.root_dir),
            capture_output=True,
            text=True,
            check=False,
        )

    def is_git_repo(self) -> bool:
        res = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return res.returncode == 0 and res.stdout.strip() == "true"

    def get_head_commit(self) -> str:
        res = self._run_git(["rev-parse", "HEAD"])
        if res.returncode != 0:
            return "uncommitted"
        return res.stdout.strip()

    def get_diff_summary(self) -> str:
        res = self._run_git(["status", "--short"])
        return res.stdout.strip()

    def load_history(self) -> List[PlateauRecord]:
        if not self.history_file.exists():
            return []
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            return [PlateauRecord(**item) for item in data]
        except Exception:
            return []

    def _save_history(self, history: List[PlateauRecord]) -> None:
        raw = [asdict(rec) for rec in history]
        self.history_file.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def get_latest_plateau(self) -> Optional[PlateauRecord]:
        history = self.load_history()
        return history[-1] if history else None

    def lock_plateau(
        self,
        metric_value: Optional[float],
        description: str,
        verified_invariants: List[str],
        auto_commit: bool = True,
    ) -> PlateauRecord:
        """Lock in a new confirmed plateau."""
        history = self.load_history()
        next_idx = len(history) + 1
        commit_hash = "manual"

        if auto_commit and self.is_git_repo():
            # Stage all changes
            self._run_git(["add", "-A"])
            msg = f"telos(plateau-{next_idx}): {description}"
            commit_res = self._run_git(["commit", "-m", msg])
            if commit_res.returncode == 0:
                commit_hash = self.get_head_commit()
            else:
                commit_hash = self.get_head_commit()
            
            # Tag the plateau
            tag_name = f"telos-plateau-{next_idx}"
            self._run_git(["tag", "-f", tag_name])

        now_str = datetime.now(timezone.utc).isoformat()
        record = PlateauRecord(
            index=next_idx,
            timestamp=now_str,
            git_commit=commit_hash,
            metric_value=metric_value,
            description=description,
            verified_invariants=verified_invariants,
        )
        history.append(record)
        self._save_history(history)
        return record

    def rollback_to_latest_plateau(self) -> tuple[bool, str]:
        """Rollback working tree to the latest confirmed plateau."""
        latest = self.get_latest_plateau()
        if not latest:
            return False, "No previous plateau recorded in Telos history."

        if not self.is_git_repo():
            return False, "Not inside a git repository; cannot auto-rollback."

        # Hard reset to the plateau commit
        if latest.git_commit and latest.git_commit != "manual":
            res = self._run_git(["reset", "--hard", latest.git_commit])
            if res.returncode != 0:
                return False, f"Git reset failed: {res.stderr.strip()}"
            # Clean untracked files
            self._run_git(["clean", "-fd"])
            return True, f"Successfully rolled back to Plateau #{latest.index} ({latest.git_commit[:8]})."
        
        # Fallback to tag
        tag_name = f"telos-plateau-{latest.index}"
        res = self._run_git(["reset", "--hard", tag_name])
        if res.returncode == 0:
            self._run_git(["clean", "-fd"])
            return True, f"Successfully rolled back to tag {tag_name}."

        return False, f"Could not restore plateau {latest.index} commit: {latest.git_commit}"
