"""
Outer Loop: Binary Verification Gate.
Evaluates acceptance invariants and produces deterministic verdicts.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from telos.core.contract import TelosContract


@dataclass
class InvariantResult:
    command: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float


@dataclass
class VerificationResult:
    passed: bool
    results: List[InvariantResult] = field(default_factory=list)
    failure_summary: Optional[str] = None

    def format_diagnostic_report(self) -> str:
        lines = []
        if self.passed:
            lines.append("VERDICT: PASS")
            lines.append(f"All {len(self.results)} acceptance invariants satisfied.")
            return "\n".join(lines)

        lines.append("VERDICT: FAIL")
        failed = [r for r in self.results if not r.passed]
        lines.append(f"{len(failed)} of {len(self.results)} invariants failed:")
        for r in failed:
            lines.append(f"\n[Command Failed (Exit Code {r.exit_code})]: {r.command}")
            if r.stderr.strip():
                lines.append("--- STDERR ---")
                lines.append(r.stderr.strip()[:2000])
            if r.stdout.strip():
                lines.append("--- STDOUT ---")
                lines.append(r.stdout.strip()[:2000])
        return "\n".join(lines)


class Verifier:
    def __init__(self, contract: TelosContract, root_dir: str | Path = "."):
        self.contract = contract
        self.root_dir = Path(root_dir).resolve()

    def run_check(self, timeout_sec: Optional[int] = None) -> VerificationResult:
        timeout = timeout_sec or self.contract.budget.timeout_sec
        results: List[InvariantResult] = []

        all_passed = True
        for cmd in self.contract.invariants:
            import time
            t0 = time.time()
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.root_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                duration = time.time() - t0
                passed = (proc.returncode == 0)
                if not passed:
                    all_passed = False
                results.append(
                    InvariantResult(
                        command=cmd,
                        passed=passed,
                        exit_code=proc.returncode,
                        stdout=proc.stdout,
                        stderr=proc.stderr,
                        duration_sec=duration,
                    )
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.time() - t0
                all_passed = False
                results.append(
                    InvariantResult(
                        command=cmd,
                        passed=False,
                        exit_code=-1,
                        stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                        stderr=f"Command timed out after {timeout} seconds",
                        duration_sec=duration,
                    )
                )

        failure_summary = None
        if not all_passed:
            failed_cmds = [r.command for r in results if not r.passed]
            failure_summary = f"Invariants failed: {', '.join(failed_cmds)}"

        return VerificationResult(
            passed=all_passed,
            results=results,
            failure_summary=failure_summary,
        )
