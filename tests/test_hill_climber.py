"""
Tests for HillClimber.
"""

from telos.core.contract import TelosContract, MetricSpec
from telos.core.checkpoint import CheckpointManager, PlateauRecord
from telos.core.hill_climber import HillClimber
import tempfile
from pathlib import Path


def test_hill_climber_measurement():
    with tempfile.TemporaryDirectory() as tmpdir:
        contract = TelosContract(
            goal="Minimize execution latency",
            metric=MetricSpec(
                command='python -c "print(12.5)"',
                direction="minimize",
            ),
        )
        mgr = CheckpointManager(root_dir=tmpdir)
        climber = HillClimber(contract=contract, checkpoint_mgr=mgr, root_dir=tmpdir)

        val = climber.measure_metric()
        assert val == 12.5

        # Initial baseline evaluation
        eval1 = climber.evaluate_step(latest_plateau=None)
        assert eval1.outcome == "PROGRESSED"
        assert eval1.metric_value == 12.5
        assert eval1.recommendation == "LOCK_PLATEAU"

        # Step evaluation against previous baseline of 15.0 (so 12.5 is an improvement for minimize)
        prev = PlateauRecord(
            index=1,
            timestamp="2026-10-15",
            git_commit="abc",
            metric_value=15.0,
            description="baseline",
            verified_invariants=[],
        )
        eval2 = climber.evaluate_step(latest_plateau=prev)
        assert eval2.outcome == "PROGRESSED"
        assert eval2.delta == -2.5
        assert eval2.recommendation == "LOCK_PLATEAU"

        # Step evaluation against previous baseline of 10.0 (so 12.5 is a regression for minimize)
        prev_better = PlateauRecord(
            index=2,
            timestamp="2026-10-15",
            git_commit="def",
            metric_value=10.0,
            description="faster",
            verified_invariants=[],
        )
        eval3 = climber.evaluate_step(latest_plateau=prev_better)
        assert eval3.outcome == "REGRESSED"
        assert eval3.delta == 2.5
        assert eval3.recommendation == "ROLLBACK"
