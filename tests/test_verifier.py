"""
Tests for Verifier.
"""

from telos.core.contract import TelosContract
from telos.core.verifier import Verifier


def test_verifier_pass():
    contract = TelosContract(
        goal="Test passing invariants",
        invariants=["python -c 'exit(0)'"],
    )
    verifier = Verifier(contract=contract)
    result = verifier.run_check()
    assert result.passed is True
    assert "VERDICT: PASS" in result.format_diagnostic_report()


def test_verifier_fail():
    contract = TelosContract(
        goal="Test failing invariants",
        invariants=["python -c 'import sys; sys.stderr.write(\"Fatal bug\\n\"); exit(1)'"],
    )
    verifier = Verifier(contract=contract)
    result = verifier.run_check()
    assert result.passed is False
    assert "VERDICT: FAIL" in result.format_diagnostic_report()
    assert "Fatal bug" in result.format_diagnostic_report()
