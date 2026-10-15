"""
Telos CLI: Command-line interface for the dual-loop autonomous runtime.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from telos.core.checkpoint import CheckpointManager
from telos.core.contract import TelosContract
from telos.core.runner import TelosRunner


TEMPLATE_YAML = """# Telos Autonomous Verification Contract
goal: "Define the target end-state here (e.g. Optimize matrix multiplication and pass all benchmarks)"

# Outer Loop: Acceptance invariants that must NEVER fail (binary gate)
invariants:
  - "pytest tests/"
  - "python -m py_compile src/**/*.py"

# Inner Loop: Hill-climbing objective metric (ascent/plateau evaluation)
metric:
  command: 'python -c "import time; print(round(time.time() % 100, 2))"'
  direction: "minimize"
  target: 0.05

# Scope boundaries: Files allowed to be modified during exploration
allowed_scope:
  - "src/**"
  - "tests/**"

budget:
  max_cycles: 15
  timeout_sec: 60
"""


def cmd_init(args: argparse.Namespace) -> int:
    target = Path("telos.yaml")
    if target.exists() and not args.force:
        print(f"Error: {target} already exists. Use --force to overwrite.", file=sys.stderr)
        return 1

    target.write_text(TEMPLATE_YAML, encoding="utf-8")
    print(f"Initialized Telos contract at {target}")
    print("Edit this file to define your target end-state, invariants, and metric.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    try:
        runner = TelosRunner(contract_path=args.contract)
    except Exception as exc:
        print(f"Error loading contract: {exc}", file=sys.stderr)
        return 1

    result = runner.check()
    print(result.format_diagnostic_report())
    return 0 if result.passed else 1


def cmd_climb(args: argparse.Namespace) -> int:
    try:
        runner = TelosRunner(contract_path=args.contract)
    except Exception as exc:
        print(f"Error loading contract: {exc}", file=sys.stderr)
        return 1

    desc = args.message or "Plateau step"
    summary = runner.step(description=desc, auto_rollback=not args.no_rollback)

    print(f"=== Telos Cycle #{summary.cycle_index} ===")
    print(f"Status: {summary.status_message}")
    if summary.step_eval:
        print(f"Outcome: {summary.step_eval.outcome}")
        if summary.step_eval.metric_value is not None:
            print(f"Metric: {summary.step_eval.metric_value} (delta: {summary.step_eval.delta})")

    if summary.locked_plateau:
        print(f"Locked Plateau #{summary.locked_plateau.index} (git: {summary.locked_plateau.git_commit[:8]})")
        return 0

    if summary.rolled_back:
        print("NOTICE: Regression occurred; working tree was reverted to previous plateau.")
        return 2

    return 0 if summary.verification.passed else 1


def cmd_rollback(args: argparse.Namespace) -> int:
    mgr = CheckpointManager()
    success, msg = mgr.rollback_to_latest_plateau()
    if success:
        print(f"SUCCESS: {msg}")
        return 0
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    try:
        contract = TelosContract.load(args.contract)
    except Exception as exc:
        print(f"Error loading contract: {exc}", file=sys.stderr)
        return 1

    mgr = CheckpointManager()
    latest = mgr.get_latest_plateau()
    history = mgr.load_history()

    print("========================================")
    print(" TELOS: AUTONOMOUS RUNTIME STATUS")
    print("========================================")
    print(f"Goal: {contract.goal}")
    print(f"Total Plateaus Reached: {len(history)}")
    if latest:
        print(f"Current Plateau: #{latest.index} (commit: {latest.git_commit[:8]})")
        print(f"Current Metric: {latest.metric_value}")
        print(f"Last Description: {latest.description}")
        print(f"Last Locked: {latest.timestamp}")
    else:
        print("Current Plateau: None (baseline not yet locked)")

    print(f"\nInvariants ({len(contract.invariants)}):")
    for inv in contract.invariants:
        print(f"  • {inv}")

    if contract.metric:
        print(f"\nHill-Climbing Metric ({contract.metric.direction}):")
        print(f"  Command: {contract.metric.command}")
        if contract.metric.target is not None:
            print(f"  Target:  {contract.metric.target}")

    if contract.allowed_scope:
        print(f"\nAllowed Scope ({len(contract.allowed_scope)}):")
        for sc in contract.allowed_scope:
            print(f"  • {sc}")

    print("========================================")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    mgr = CheckpointManager()
    history = mgr.load_history()
    if not history:
        print("No plateaus recorded yet.")
        return 0

    print(f"{'#':<4} {'Commit':<10} {'Metric':<12} {'Description':<35} {'Timestamp'}")
    print("-" * 80)
    for rec in history:
        metric_str = f"{rec.metric_value:<12.4f}" if rec.metric_value is not None else "N/A"
        print(f"{rec.index:<4} {rec.git_commit[:8]:<10} {metric_str} {rec.description[:33]:<35} {rec.timestamp[:19]}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="telos",
        description="Telos: Dual-Loop Autonomous Agent Runtime for End-State Prompting and Plateau Ascent",
    )
    parser.add_argument(
        "--contract",
        "-c",
        default="telos.yaml",
        help="Path to contract file (default: telos.yaml)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a fresh telos.yaml contract")
    p_init.add_argument("--force", "-f", action="store_true", help="Overwrite existing contract")

    # check
    subparsers.add_parser("check", help="Run outer loop: evaluate binary acceptance invariants")

    # climb / step
    p_climb = subparsers.add_parser("climb", help="Run inner loop: evaluate hill-climbing step")
    p_climb.add_argument("-m", "--message", help="Description of the step/plateau")
    p_climb.add_argument("--no-rollback", action="store_true", help="Do not auto-rollback on regression")

    # rollback
    subparsers.add_parser("rollback", help="Roll back working tree to the latest confirmed plateau")

    # status
    subparsers.add_parser("status", help="Show current goal, plateau, and invariant status")

    # history
    subparsers.add_parser("history", help="List all plateau checkpoints recorded")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "init": cmd_init,
        "check": cmd_check,
        "climb": cmd_climb,
        "rollback": cmd_rollback,
        "status": cmd_status,
        "history": cmd_history,
    }

    exit_code = handlers[args.command](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
