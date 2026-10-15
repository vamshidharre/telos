"""
Tests for CheckpointManager.
"""

import tempfile
from pathlib import Path
from telos.core.checkpoint import CheckpointManager


def test_checkpoint_history_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = CheckpointManager(root_dir=tmpdir)
        assert len(mgr.load_history()) == 0

        # Lock first plateau without git auto_commit
        rec1 = mgr.lock_plateau(
            metric_value=42.0,
            description="Initial plateau",
            verified_invariants=["check1"],
            auto_commit=False,
        )
        assert rec1.index == 1
        assert rec1.metric_value == 42.0

        history = mgr.load_history()
        assert len(history) == 1
        assert history[0].description == "Initial plateau"

        # Lock second plateau
        rec2 = mgr.lock_plateau(
            metric_value=30.0,
            description="Optimized plateau",
            verified_invariants=["check1", "check2"],
            auto_commit=False,
        )
        assert rec2.index == 2
        assert mgr.get_latest_plateau().metric_value == 30.0
