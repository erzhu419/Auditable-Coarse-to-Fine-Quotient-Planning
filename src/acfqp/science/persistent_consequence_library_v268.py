"""Two-step paired-outcome representation diagnostic for persistent modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from typing import Any

from .mechanism_switch_task_v205 import OPERATORS
from .persistent_consequence_library_v263 import (
    PHASES, QUERIES, WEATHER, _draw_rows, _empty_counts, _exact_vectors,
    consequence_vector, posterior,
)
from .persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, SEEDS, _add_counts, _audit_brier,
    _slice_counts,
)
from .persistent_consequence_library_v267 import _metrics_bank, _optimal_actions


def _pair_counts(rows: dict[str, list[str]], start: int, end: int) -> dict[str, int]:
    """Count a fixed-index DETOUR_PASS/RECOVERY_RETRY outcome pair."""
    counts = {name: 0 for name in (
        "DETOUR_DELIVERY", "DETOUR_LOST", "RECOVERY_RETRY_DELIVERY", "RECOVERY_RETRY_LOST")}
    for detour, retry in zip(rows["DETOUR_PASS"][start:end], rows["RECOVERY_RETRY"][start:end]):
        if detour == "DELIVERY":
            counts["DETOUR_DELIVERY"] += 1
        elif detour == "LOST":
            counts["DETOUR_LOST"] += 1
        elif retry == "DELIVERY":
            counts["RECOVERY_RETRY_DELIVERY"] += 1
        else:
            counts["RECOVERY_RETRY_LOST"] += 1
    return counts


def _add_pair_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for category, value in source.items():
        target[category] += value


def _pair_vectors(short: dict[str, F], pair: dict[str, F],
                  *, operating: str = "low", retry_cost: str = "19/20") -> dict[str, tuple[F, F, F]]:
    """Build route consequences from short and joint pair probabilities."""
    short_cost, detour_cost = {"low": (F(1, 10), F(1, 20)), "high": (F(3, 25), F(7, 100))}[operating]
    retry = F(retry_cost)
    detour_delivery = pair["DETOUR_DELIVERY"]
    detour_lost = pair["DETOUR_LOST"]
    recovery_delivery = pair["RECOVERY_RETRY_DELIVERY"]
    recovery_lost = pair["RECOVERY_RETRY_LOST"]
    recovery = recovery_delivery + recovery_lost
    return {
        "WAIT": (F(0), F(0), F(0)),
        "SHORT": (-short_cost, short["LOST"], short["DELIVERY"]),
        "DETOUR_RETURN": (-detour_cost, detour_lost, detour_delivery),
        "DETOUR_RETRY": (-detour_cost - recovery * retry,
                          detour_lost + recovery_lost,
                          detour_delivery + recovery_delivery),
    }


def _pair_model(short_counts: dict[str, int], pair_counts: dict[str, int],
                *, operating: str = "low", retry_cost: str = "19/20") -> dict[str, tuple[F, F, F]]:
    """Build route consequences from a joint paired posterior."""
    short_total = sum(short_counts.values())
    short = {name: F(2 * value + 1, 2 * short_total + 2) for name, value in short_counts.items()}
    pair_total = sum(pair_counts.values())
    pair = {name: F(2 * value + 1, 2 * pair_total + 4) for name, value in pair_counts.items()}
    return _pair_vectors(short, pair, operating=operating, retry_cost=retry_cost)


def _exact_pair_model(weather: str) -> dict[str, tuple[F, F, F]]:
    """Exact paired outcome under the declared route law, for post-hoc scoring."""
    law = WEATHER[weather]
    short = {"DELIVERY": law[0], "LOST": 1 - law[0]}
    _, detour_delivery, detour_lost, recovery, retry_delivery = law
    pair = {
        "DETOUR_DELIVERY": detour_delivery,
        "DETOUR_LOST": detour_lost,
        "RECOVERY_RETRY_DELIVERY": recovery * retry_delivery,
        "RECOVERY_RETRY_LOST": recovery * (1 - retry_delivery),
    }
    return _pair_vectors(short, pair)


def _assignment_agreement(existing: dict[str, dict[str, F]], local: dict[str, dict[str, F]]) -> dict[str, bool]:
    case = {"operating": "low", "retry_cost": "19/20"}
    existing_vectors = consequence_vector(case, existing)
    local_vectors = consequence_vector(case, local)
    return {name: _optimal_actions(existing_vectors, weights) == _optimal_actions(local_vectors, weights)
            for name, weights in QUERIES.items()}


@dataclass
class MarginalAssignmentLibrary:
    modules: list[Any] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        local_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        local_model = posterior(local_counts)
        checks, matches = [], []
        for module in self.modules:
            agreement = _assignment_agreement(posterior(module.counts), local_model)
            check = {"module_id": module.module_id, "agreement": agreement,
                     "all_match": all(agreement.values())}
            checks.append(check)
            if check["all_match"]:
                matches.append(module)
        if matches:
            module = min(matches, key=lambda candidate: candidate.module_id)
            reason, reused = "reuse_all_query_actions", True
            module.contexts.append(context_id)
        else:
            module = self._new(context_id)
            reason, reused = ("initial" if len(self.modules) == 1 else "abstain_local_split"), False
        _add_counts(module.counts, local_counts)
        self.assignments[context_id] = module.module_id
        audit_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}
        return {"module_id": module.module_id, "reason": reason, "reused": reused,
                "candidate_checks": checks, "candidate_count_before": len(checks),
                "module_count_after": len(self.modules),
                "audit_brier": _audit_brier(posterior(module.counts), audit_rows)}

    def _new(self, context_id: str) -> Any:
        module = type("Module", (), {})()
        module.module_id = len(self.modules)
        module.counts = _empty_counts()
        module.contexts = [context_id]
        self.modules.append(module)
        return module

    def model_for(self, context_id: str) -> dict[str, dict[str, F]]:
        return posterior(self.modules[self.assignments[context_id]].counts)


@dataclass
class ComposedModule:
    module_id: int
    short_counts: dict[str, int] = field(default_factory=lambda: {"DELIVERY": 0, "LOST": 0})
    pair_counts: dict[str, int] = field(default_factory=lambda: {name: 0 for name in (
        "DETOUR_DELIVERY", "DETOUR_LOST", "RECOVERY_RETRY_DELIVERY", "RECOVERY_RETRY_LOST")})
    contexts: list[str] = field(default_factory=list)


class LockedComposedLibrary:
    """Parallel pair model whose module IDs are imposed by marginal assignment."""

    def __init__(self) -> None:
        self.modules: list[ComposedModule] = []
        self.assignments: dict[str, int] = {}

    def ingest(self, context_id: str, rows: dict[str, list[str]], assignment: dict[str, Any]) -> None:
        module_id = assignment["module_id"]
        while len(self.modules) <= module_id:
            self.modules.append(ComposedModule(len(self.modules)))
        module = self.modules[module_id]
        if not module.contexts:
            module.contexts.append(context_id)
        elif assignment["reused"]:
            module.contexts.append(context_id)
        fit_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        for category, value in fit_counts["SHORT_PASS"].items():
            module.short_counts[category] += value
        _add_pair_counts(module.pair_counts, _pair_counts(rows, 0, FIT_PER_OPERATOR))
        self.assignments[context_id] = module_id

    def model_for(self, context_id: str) -> dict[str, tuple[F, F, F]]:
        module = self.modules[self.assignments[context_id]]
        return _pair_model(module.short_counts, module.pair_counts)


def _run_lifecycle(seed: int) -> dict[str, Any]:
    arms = ("RESET_MARGINAL", "RESET_COMPOSED", "LOCKED_MARGINAL", "LOCKED_COMPOSED")
    records = {arm: [] for arm in arms}
    assignment_library = MarginalAssignmentLibrary()
    composed_library = LockedComposedLibrary()
    for phase_index, (phase, weather) in enumerate(PHASES):
        law = WEATHER[weather]
        rows = _draw_rows({
            "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
            "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
            "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
        }, seed + phase_index)
        exact_marginal = _exact_vectors(weather)
        exact_composed = _exact_pair_model(weather)
        fit_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        assignment = assignment_library.ingest(f"opaque_{phase_index}", rows)
        composed_library.ingest(f"opaque_{phase_index}", rows, assignment)
        marginal_model = posterior(fit_counts)
        composed_model = _pair_model(fit_counts["SHORT_PASS"], _pair_counts(rows, 0, FIT_PER_OPERATOR))
        models = {
            "RESET_MARGINAL": (consequence_vector({"operating": "low", "retry_cost": "19/20"}, marginal_model), exact_marginal, None, 1),
            "RESET_COMPOSED": (composed_model, exact_composed, None, 1),
            "LOCKED_MARGINAL": (consequence_vector({"operating": "low", "retry_cost": "19/20"}, assignment_library.model_for(f"opaque_{phase_index}")), exact_marginal, assignment, len(assignment_library.modules)),
            "LOCKED_COMPOSED": (composed_library.model_for(f"opaque_{phase_index}"), exact_composed, assignment, len(composed_library.modules)),
        }
        for arm, (model, exact, assignment_record, modules) in models.items():
            row = {
                "phase": phase, "weather_for_audit": weather, "checkpoint": "shared_fit_prefix",
                "metrics": _metrics_bank(model, exact, queries=QUERIES),
                "pair_fit_count": FIT_PER_OPERATOR, "pair_audit_count": AUDIT_PER_OPERATOR,
                "observations": (phase_index + 1) * FIT_PER_OPERATOR * len(OPERATORS),
                "audit_observations": AUDIT_PER_OPERATOR * len(OPERATORS), "modules": modules,
            }
            if assignment_record is not None:
                row["assignment"] = assignment_record
            records[arm].append(row)
    return {"seed": seed, "arms": records}


def _summary(records: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    correct, sets, regrets = [], [], []
    for record in records:
        metrics = [item for row in record["arms"][arm] for item in row["metrics"].values()]
        correct.append(sum(item["policy_correct"] for item in metrics))
        sets.append(sum(item["set_action_agreement"] for item in metrics))
        regrets.append(sum(F(item["exact_value_regret"]) for item in metrics))
    return {"policy_correct_counts": correct, "mean_policy_correct": sum(correct) / len(correct),
            "set_action_agreement_counts": sets,
            "mean_set_action_agreement": sum(sets) / (len(records) * len(PHASES) * len(QUERIES)),
            "exact_regrets": [str(value) for value in regrets],
            "mean_exact_regret": str(sum(regrets, F(0)) / len(regrets))}


def run_replication() -> dict[str, Any]:
    records = [_run_lifecycle(seed) for seed in SEEDS]
    arms = ("RESET_MARGINAL", "RESET_COMPOSED", "LOCKED_MARGINAL", "LOCKED_COMPOSED")
    return {"schema": "acfqp.persistent_consequence_library.v268", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {
                "seeds": list(SEEDS), "fit_per_operator": FIT_PER_OPERATOR,
                "audit_per_operator": AUDIT_PER_OPERATOR,
                "queries": {name: tuple(map(str, value)) for name, value in QUERIES.items()},
                "pairing": "fixed-index DETOUR_PASS with RECOVERY_RETRY within the fit prefix",
                "pair_categories": ["DETOUR_DELIVERY", "DETOUR_LOST", "RECOVERY_RETRY_DELIVERY", "RECOVERY_RETRY_LOST"],
                "assignment_rule": "LOCKED arms use the V266 marginal action-agreement assignment exactly"},
            "records": records, "summary": {arm: _summary(records, arm) for arm in arms},
            "limitations": ["Pairing is a predeclared fixed-index diagnostic, not a new conditional sampling process.",
                            "The four-category joint estimator changes the prior and effective evidence: non-recovery retry rows do not enter the pair table.",
                            "Module assignment is frozen to the marginal rule, but this is not a pure representation-only comparison.",
                            "No confidence certificate, original Gate or U006 assurance is changed."]}


__all__ = [name for name in globals() if not name.startswith("_")]
