"""Fair-prefix applicability diagnostic for persistent consequence modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS, WEATHER
from .persistent_consequence_library_v263 import (
    BRIER_SPLIT_THRESHOLD,
    COST_PRIOR,
    PHASES,
    QUERIES,
    _brier,
    _counts,
    _draw_rows,
    _empty_counts,
    _exact_vectors,
    _metrics,
    consequence_vector,
    posterior,
)

FIT_PER_OPERATOR = 48
TRAIN_PER_OPERATOR = 32
ROUTE_PER_OPERATOR = FIT_PER_OPERATOR - TRAIN_PER_OPERATOR
AUDIT_PER_OPERATOR = 16
AMBIGUITY_MARGIN = F(1, 20)
SEEDS = (265401, 265402, 265403, 265404)


def _slice_counts(rows: dict[str, list[str]], start: int, end: int) -> dict[str, dict[str, int]]:
    counts = _empty_counts()
    for operator in OPERATORS:
        for category in rows[operator][start:end]:
            counts[operator][category] += 1
    return counts


def _add_counts(target: dict[str, dict[str, int]], source: dict[str, dict[str, int]]) -> None:
    for operator in OPERATORS:
        for category, value in source[operator].items():
            target[operator][category] += value


@dataclass
class Module:
    module_id: int
    counts: dict[str, dict[str, int]] = field(default_factory=_empty_counts)
    contexts: list[str] = field(default_factory=list)


@dataclass
class LegacyLibrary:
    modules: list[Module] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        fit_rows = {operator: values[:FIT_PER_OPERATOR] for operator, values in rows.items()}
        if not self.modules:
            module, reason = self._new(context_id), "initial"
        else:
            scores = [(module, _brier(module.counts, fit_rows)) for module in self.modules]
            module, score = min(scores, key=lambda item: (item[1], item[0].module_id))
            if score > BRIER_SPLIT_THRESHOLD:
                module, reason = self._new(context_id), "fit_split_trigger"
            else:
                reason = "reuse"
                module.contexts.append(context_id)
        _add_counts(module.counts, _slice_counts(rows, 0, FIT_PER_OPERATOR))
        self.assignments[context_id] = module.module_id
        return {"module_id": module.module_id, "reason": reason, "module_count_after": len(self.modules)}

    def _new(self, context_id: str) -> Module:
        module = Module(len(self.modules), contexts=[context_id])
        self.modules.append(module)
        return module

    def model_for(self, context_id: str) -> dict[str, dict[str, F]]:
        return posterior(self.modules[self.assignments[context_id]].counts)


@dataclass
class GuardedLibrary:
    modules: list[Module] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        route_rows = {operator: values[TRAIN_PER_OPERATOR:FIT_PER_OPERATOR] for operator, values in rows.items()}
        train_counts = _slice_counts(rows, 0, TRAIN_PER_OPERATOR)
        local_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        local_brier = _brier(train_counts, route_rows)
        candidates = [(module, _brier(module.counts, route_rows)) for module in self.modules]
        if not candidates:
            module, reason, existing_brier = self._new(context_id), "initial", None
        else:
            module, existing_brier = min(candidates, key=lambda item: (item[1], item[0].module_id))
            reuse = (existing_brier <= BRIER_SPLIT_THRESHOLD
                     and existing_brier <= local_brier + AMBIGUITY_MARGIN)
            if reuse:
                reason = "reuse_confident"
                module.contexts.append(context_id)
            else:
                module, reason = self._new(context_id), "abstain_local_split"
        _add_counts(module.counts, local_counts)
        self.assignments[context_id] = module.module_id
        audit_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}
        audit_brier = _brier(module.counts, audit_rows)
        return {"module_id": module.module_id, "reason": reason, "module_count_after": len(self.modules),
                "local_route_brier": local_brier, "existing_route_brier": existing_brier,
                "audit_brier": audit_brier}

    def _new(self, context_id: str) -> Module:
        module = Module(len(self.modules), contexts=[context_id])
        self.modules.append(module)
        return module

    def model_for(self, context_id: str) -> dict[str, dict[str, F]]:
        return posterior(self.modules[self.assignments[context_id]].counts)


def _audit_brier(model: dict[str, dict[str, F]], rows: dict[str, list[str]]) -> F:
    squared = []
    for operator in OPERATORS:
        for category in rows[operator]:
            squared.append(sum((model[operator][candidate] - F(candidate == category)) ** 2
                               for candidate in ALPHABETS[operator]))
    return sum(squared, F(0)) / len(squared)


def _case_vectors(weather: str, model: dict[str, dict[str, F]]) -> dict[str, tuple[F, F, F]]:
    return consequence_vector({"operating": "low", "retry_cost": "19/20"}, model)


def _run_lifecycle(seed: int) -> dict[str, Any]:
    records = {arm: [] for arm in ("RESET", "GLOBAL", "LEGACY_LIBRARY", "GUARDED_LIBRARY")}
    global_counts = _empty_counts()
    legacy, guarded = LegacyLibrary(), GuardedLibrary()
    for phase_index, (phase, weather) in enumerate(PHASES):
        law = WEATHER[weather]
        rows = _draw_rows({
            "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
            "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
            "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
        }, seed + phase_index)
        exact = _exact_vectors(weather)
        fit_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        audit_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}

        _add_counts(global_counts, fit_counts)
        arms = {
            "RESET": (posterior(fit_counts), None, 1),
            "GLOBAL": (posterior(global_counts), None, 1),
        }
        context_id = f"opaque_{phase_index}"
        legacy_assignment = legacy.ingest(context_id, rows)
        guarded_assignment = guarded.ingest(context_id, rows)
        arms["LEGACY_LIBRARY"] = (legacy.model_for(context_id), legacy_assignment, len(legacy.modules))
        arms["GUARDED_LIBRARY"] = (guarded.model_for(context_id), guarded_assignment, len(guarded.modules))
        for arm, (model, assignment, modules) in arms.items():
            record = {"phase": phase, "weather_for_audit": weather, "checkpoint": "shared_fit_prefix",
                      "metrics": _metrics(_case_vectors(weather, model), exact),
                      "observations": (phase_index + 1) * FIT_PER_OPERATOR * len(OPERATORS),
                      "audit_observations": AUDIT_PER_OPERATOR * len(OPERATORS), "modules": modules}
            if assignment is not None:
                record["assignment"] = assignment
                record["audit_brier"] = _audit_brier(model, audit_rows)
            records[arm].append(record)
    return {"seed": seed, "arms": records}


def run_replication() -> dict[str, Any]:
    records = [_run_lifecycle(seed) for seed in SEEDS]
    summary = {}
    for arm in ("RESET", "GLOBAL", "LEGACY_LIBRARY", "GUARDED_LIBRARY"):
        correct = [sum(item["policy_correct"] for row in record["arms"][arm] for item in row["metrics"].values())
                   for record in records]
        regrets = [sum((F(item["exact_value_regret"]) if isinstance(item["exact_value_regret"], str)
                        else item["exact_value_regret"])
                       for row in record["arms"][arm] for item in row["metrics"].values())
                   for record in records]
        summary[arm] = {"policy_correct_counts": correct, "mean_policy_correct": sum(correct) / len(correct),
                        "exact_regrets": [str(value) for value in regrets],
                        "mean_exact_regret": str(sum(regrets, F(0)) / len(regrets))}
    return {"schema": "acfqp.persistent_consequence_library.v265", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {
                "seeds": list(SEEDS), "fit_per_operator": FIT_PER_OPERATOR,
                "train_per_operator": TRAIN_PER_OPERATOR, "route_per_operator": ROUTE_PER_OPERATOR,
                "audit_per_operator": AUDIT_PER_OPERATOR, "split_threshold": BRIER_SPLIT_THRESHOLD,
                "ambiguity_margin": AMBIGUITY_MARGIN, "queries": {name: tuple(map(str, value)) for name, value in QUERIES.items()},
            }, "records": records, "summary": summary,
            "limitations": ["Four finite route lifecycles are development evidence only.",
                            "The audit suffix is descriptive and never enters a model.",
                            "No confidence certificate, general strategic claim or original Gate is changed."]}


__all__ = [name for name in globals() if not name.startswith("_")]
