"""
Inner Loop: Hill-Climbing Step Evaluator.
Measures metrics, compares to current plateau, validates scope, and recommends actions.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from telos.core.checkpoint import CheckpointManager, PlateauRecord
from telos.core.contract import TelosContract


@dataclass
class StepEvaluation:
    outcome: str  # "PROGRESSED", "STAGNANT", "REGRESSED", "SCOPE_VIOLATION", "NO_METRIC"
    metric_value: Optional[float]
    delta: Optional[float]
    recommendation: str  # "LOCK_PLATEAU", "KEEP_EXPLORING", "ROLLBACK"
    explanation: str
    violating_files: List[str]


class HillClimber:
    def __init__(
        self,
        contract: TelosContract,
        checkpoint_mgr: CheckpointManager,
        root_dir: str | Path = ".",
    ):
        self.contract = contract
        self.checkpoint_mgr = checkpoint_mgr
        self.root_dir = Path(root_dir).resolve()

    def check_scope_violations(self) -> List[str]:
        """Verify that only files within contract.allowed_scope have been modified."""
        if not self.contract.allowed_scope:
            return []  # No scope restrictions defined

        diff_summary = self.checkpoint_mgr.get_diff_summary()
        if not diff_summary:
            return []

        modified_files: List[str] = []
        for line in diff_summary.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                modified_files.append(parts[1])

        violations = []
        for mod_file in modified_files:
            matched = any(
                fnmatch.fnmatch(mod_file, pattern)
                for pattern in self.contract.allowed_scope
            )
            if not matched:
                violations.append(mod_file)

        return violations

    def measure_metric(self) -> Optional[float]:
        """Execute the metric command and parse the numeric value."""
        if not self.contract.metric:
            return None

        cmd = self.contract.metric.command
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(self.root_dir),
            capture_output=True,
            text=True,
            timeout=self.contract.budget.timeout_sec,
        )
        if proc.returncode != 0:
            return None

        output = proc.stdout.strip()
        if self.contract.metric.regex:
            match = re.search(self.contract.metric.regex, output)
            if match:
                val_str = match.group(1) if match.groups() else match.group(0)
                try:
                    return float(val_str)
                except ValueError:
                    return None
            return None

        # Try to parse entire stripped output or last number found
        try:
            return float(output)
        except ValueError:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", output)
            if nums:
                return float(nums[-1])
            return None

    def evaluate_step(self, latest_plateau: Optional[PlateauRecord] = None) -> StepEvaluation:
        # 1. Scope check
        violations = self.check_scope_violations()
        if violations:
            return StepEvaluation(
                outcome="SCOPE_VIOLATION",
                metric_value=None,
                delta=None,
                recommendation="ROLLBACK",
                explanation=f"Modifications detected outside allowed_scope: {', '.join(violations)}",
                violating_files=violations,
            )

        # 2. Metric evaluation
        if not self.contract.metric:
            return StepEvaluation(
                outcome="NO_METRIC",
                metric_value=None,
                delta=None,
                recommendation="KEEP_EXPLORING",
                explanation="No objective metric configured; step validated by invariants alone.",
                violating_files=[],
            )

        current_val = self.measure_metric()
        if current_val is None:
            return StepEvaluation(
                outcome="REGRESSED",
                metric_value=None,
                delta=None,
                recommendation="ROLLBACK",
                explanation=f"Metric command failed or output could not be parsed: {self.contract.metric.command}",
                violating_files=[],
            )

        base_val = latest_plateau.metric_value if latest_plateau else None
        if base_val is None:
            # First plateau baseline
            return StepEvaluation(
                outcome="PROGRESSED",
                metric_value=current_val,
                delta=0.0,
                recommendation="LOCK_PLATEAU",
                explanation=f"Established initial baseline metric value: {current_val}",
                violating_files=[],
            )

        delta = current_val - base_val
        if self.contract.metric.is_better(current_val, base_val):
            return StepEvaluation(
                outcome="PROGRESSED",
                metric_value=current_val,
                delta=delta,
                recommendation="LOCK_PLATEAU",
                explanation=f"Improved metric from {base_val} to {current_val} (delta: {delta:+.4f})",
                violating_files=[],
            )
        elif current_val == base_val:
            return StepEvaluation(
                outcome="STAGNANT",
                metric_value=current_val,
                delta=0.0,
                recommendation="KEEP_EXPLORING",
                explanation=f"Metric unchanged at {current_val}. Neutral plateau.",
                violating_files=[],
            )
        else:
            return StepEvaluation(
                outcome="REGRESSED",
                metric_value=current_val,
                delta=delta,
                recommendation="ROLLBACK",
                explanation=f"Metric regressed from {base_val} to {current_val} (delta: {delta:+.4f})",
                violating_files=[],
            )
