"""
Telos Contract: End-state and invariant specification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class MetricSpec:
    command: str
    direction: str = "minimize"  # "minimize" or "maximize"
    regex: Optional[str] = None
    target: Optional[float] = None

    def is_better(self, new_val: float, current_val: float) -> bool:
        if self.direction == "minimize":
            return new_val < current_val
        return new_val > current_val

    def satisfies_target(self, val: float) -> bool:
        if self.target is None:
            return True
        if self.direction == "minimize":
            return val <= self.target
        return val >= self.target


@dataclass
class BudgetSpec:
    max_cycles: int = 15
    timeout_sec: int = 120


@dataclass
class TelosContract:
    goal: str
    invariants: List[str] = field(default_factory=list)
    metric: Optional[MetricSpec] = None
    allowed_scope: List[str] = field(default_factory=list)
    budget: BudgetSpec = field(default_factory=BudgetSpec)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TelosContract:
        metric_data = data.get("metric")
        metric = MetricSpec(**metric_data) if metric_data else None

        budget_data = data.get("budget", {})
        budget = BudgetSpec(**budget_data) if budget_data else BudgetSpec()

        return cls(
            goal=data.get("goal", "").strip(),
            invariants=data.get("invariants", []),
            metric=metric,
            allowed_scope=data.get("allowed_scope", []),
            budget=budget,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def load(cls, file_path: str | Path = "telos.yaml") -> TelosContract:
        path = Path(file_path)
        if not path.exists():
            # Check telos.json as alternative
            json_alt = path.with_suffix(".json")
            if json_alt.exists():
                path = json_alt
            else:
                raise FileNotFoundError(f"Contract file not found: {file_path}")

        raw_text = path.read_text(encoding="utf-8")
        if path.suffix in [".yaml", ".yml"]:
            if not HAS_YAML:
                raise ImportError(
                    "PyYAML is required to read .yaml contract files. "
                    "Install with `pip install pyyaml` or provide telos.json."
                )
            data = yaml.safe_load(raw_text) or {}
        else:
            data = json.loads(raw_text)

        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "goal": self.goal,
            "invariants": self.invariants,
            "allowed_scope": self.allowed_scope,
            "budget": {
                "max_cycles": self.budget.max_cycles,
                "timeout_sec": self.budget.timeout_sec,
            },
        }
        if self.metric:
            data["metric"] = {
                "command": self.metric.command,
                "direction": self.metric.direction,
                "regex": self.metric.regex,
                "target": self.metric.target,
            }
        if self.metadata:
            data["metadata"] = self.metadata
        return data

    def save(self, file_path: str | Path = "telos.yaml") -> None:
        path = Path(file_path)
        data = self.to_dict()
        if path.suffix in [".yaml", ".yml"] and HAS_YAML:
            path.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
