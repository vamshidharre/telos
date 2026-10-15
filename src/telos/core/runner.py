"""
Dual-Loop Orchestration Engine.
Coordinates the Outer Verification Gate with the Inner Hill-Climber Plateau Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from telos.core.checkpoint import CheckpointManager, PlateauRecord
from telos.core.contract import TelosContract
from telos.core.hill_climber import HillClimber, StepEvaluation
from telos.core.verifier import VerificationResult, Verifier


@dataclass
class CycleSummary:
    cycle_index: int
    verification: VerificationResult
    step_eval: Optional[StepEvaluation]
    locked_plateau: Optional[PlateauRecord]
    rolled_back: bool
    status_message: str


class TelosRunner:
    def __init__(self, contract_path: str | Path = "telos.yaml", root_dir: str | Path = "."):
        self.root_dir = Path(root_dir).resolve()
        self.contract = TelosContract.load(self.root_dir / contract_path)
        self.checkpoint_mgr = CheckpointManager(root_dir=self.root_dir)
        self.verifier = Verifier(contract=self.contract, root_dir=self.root_dir)
        self.climber = HillClimber(
            contract=self.contract,
            checkpoint_mgr=self.checkpoint_mgr,
            root_dir=self.root_dir,
        )

    def check(self) -> VerificationResult:
        """Run only the outer verification loop (binary criteria check)."""
        return self.verifier.run_check()

    def step(self, description: str = "iteration step", auto_rollback: bool = True) -> CycleSummary:
        """Execute one complete dual-loop cycle: evaluate invariants and metric step."""
        # 1. Run outer verification check
        verif = self.verifier.run_check()
        latest = self.checkpoint_mgr.get_latest_plateau()
        step_eval = self.climber.evaluate_step(latest_plateau=latest)

        history = self.checkpoint_mgr.load_history()
        cycle_idx = len(history) + 1

        locked = None
        rolled_back = False

        # If invariants failed:
        if not verif.passed:
            if auto_rollback and latest:
                success, msg = self.checkpoint_mgr.rollback_to_latest_plateau()
                rolled_back = success
                status_msg = f"Invariants failed. Auto-reverted to Plateau #{latest.index}. {verif.failure_summary}"
            else:
                status_msg = f"Invariants failed. {verif.failure_summary}"

            return CycleSummary(
                cycle_index=cycle_idx,
                verification=verif,
                step_eval=step_eval,
                locked_plateau=None,
                rolled_back=rolled_back,
                status_message=status_msg,
            )

        # Invariants passed! Check hill-climbing step
        if step_eval.recommendation == "LOCK_PLATEAU":
            # Progress made and invariants hold
            locked = self.checkpoint_mgr.lock_plateau(
                metric_value=step_eval.metric_value,
                description=description,
                verified_invariants=self.contract.invariants,
                auto_commit=True,
            )
            status_msg = f"Plateau #{locked.index} locked! Metric: {step_eval.metric_value} ({step_eval.explanation})"
        elif step_eval.recommendation == "ROLLBACK":
            if auto_rollback and latest:
                success, _ = self.checkpoint_mgr.rollback_to_latest_plateau()
                rolled_back = success
                status_msg = f"Regression detected ({step_eval.explanation}). Reverted to Plateau #{latest.index}."
            else:
                status_msg = f"Regression detected ({step_eval.explanation})."
        else:
            status_msg = f"Neutral step: {step_eval.explanation}"

        return CycleSummary(
            cycle_index=cycle_idx,
            verification=verif,
            step_eval=step_eval,
            locked_plateau=locked,
            rolled_back=rolled_back,
            status_message=status_msg,
        )
