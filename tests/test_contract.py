"""
Tests for TelosContract.
"""

from pathlib import Path
import tempfile
from telos.core.contract import TelosContract, MetricSpec, BudgetSpec


def test_contract_roundtrip():
    contract = TelosContract(
        goal="Achieve 100% test pass rate",
        invariants=["pytest", "ruff check"],
        metric=MetricSpec(
            command="python -c 'print(42)'",
            direction="maximize",
            target=50.0,
        ),
        allowed_scope=["src/**", "tests/**"],
        budget=BudgetSpec(max_cycles=10, timeout_sec=30),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "telos.json"
        contract.save(json_file)

        loaded = TelosContract.load(json_file)
        assert loaded.goal == "Achieve 100% test pass rate"
        assert len(loaded.invariants) == 2
        assert loaded.metric is not None
        assert loaded.metric.direction == "maximize"
        assert loaded.metric.target == 50.0
        assert loaded.budget.max_cycles == 10


def test_metric_is_better():
    # Minimization
    m_min = MetricSpec(command="echo 1", direction="minimize")
    assert m_min.is_better(10.0, 20.0) is True
    assert m_min.is_better(25.0, 20.0) is False

    # Maximization
    m_max = MetricSpec(command="echo 1", direction="maximize")
    assert m_max.is_better(25.0, 20.0) is True
    assert m_max.is_better(15.0, 20.0) is False
