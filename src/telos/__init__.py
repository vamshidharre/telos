"""
Telos: Dual-Loop Autonomous Agent Runtime
Based on End-State Invariants and Hill-Climbing Plateau Verification.
"""

__version__ = "0.1.0"
__author__ = "Vamshidhar Reddy"

from telos.core.contract import TelosContract
from telos.core.verifier import Verifier, VerificationResult
from telos.core.hill_climber import HillClimber, StepEvaluation
from telos.core.checkpoint import CheckpointManager
from telos.core.runner import TelosRunner

__all__ = [
    "TelosContract",
    "Verifier",
    "VerificationResult",
    "HillClimber",
    "StepEvaluation",
    "CheckpointManager",
    "TelosRunner",
]
