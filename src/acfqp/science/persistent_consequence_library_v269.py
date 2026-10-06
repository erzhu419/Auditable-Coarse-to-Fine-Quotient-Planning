"""Factorized local-residual diagnostic with frozen V266 assignments."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS
from .persistent_consequence_library_v263 import (
    PHASES, QUERIES, WEATHER, _draw_rows, _empty_counts, _exact_vectors,
    consequence_vector, posterior,
)
from .persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, SEEDS, _add_counts, _audit_brier,
    _slice_counts,
)
from .persistent_consequence_library_v267 import _metrics_bank, _optimal_actions

KAPPA = F(FIT_PER_OPERATOR)


def _copy_counts(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    return {operator: dict(values) for operator, values in counts.items()}


def _shrink_model(local_counts: dict[str, dict[str, int]],
                  baseline_counts: dict[str, dict[str, int]]) -> dict[str, dict[str, F]]:
    """Jeffreys local posterior plus one fixed historical-context baseline."""
    baseline_present = any(sum(values.values()) for values in baseline_counts.values())
    kappa = KAPPA if baseline_present else F(0)
    base = posterior(baseline_counts)
    result = {}
    for operator in OPERATORS:
        alphabet = ALPHABETS[operator]
        local_total = sum(local_counts[operator].values())
        denominator = 2 * local_total + len(alphabet) + kappa
        result[operator] = {
            category: (2 * local_counts[operator][category] + 1 + kappa * base[operator][category]) / denominator
            for category in alphabet
        }
    return result


def _assignment_agreement(existing: dict[str, dict[str, F]], local: dict[str, dict[str, F]]) -> dict[str, bool]:
    case = {"operating": "low", "retry_cost": "19/20"}
    existing_vectors = consequence_vector(case, existing)
    local_vectors = consequence_vector(case, local)
    return {name: _optimal_actions(existing_vectors, weights) == _optimal_actions(local_vectors, weights)
            for name, weights in QUERIES.items()}


@dataclass
class AssignmentLibrary:
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
            history_counts = _copy_counts(module.counts)
            reason, reused = "reuse_all_query_actions", True
            module.contexts.append(context_id)
        else:
            module = self._new(context_id)
            history_counts = _empty_counts()
            reason, reused = ("initial" if len(self.modules) == 1 else "abstain_local_split"), False
        _add_counts(module.counts, local_counts)
        self.assignments[context_id] = module.module_id
        audit_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}
        return {"module_id": module.module_id, "reason": reason, "reused": reused,
                "candidate_checks": checks, "candidate_count_before": len(checks),
                "module_count_after": len(self.modules), "history_counts": history_counts,
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


def _run_lifecycle(seed: int) -> dict[str, Any]:
    arms = ("RESET", "LOCKED_MARGINAL", "GLOBAL_SHRINK", "FACTORIZED_MODULE")
    records = {arm: [] for arm in arms}
    library = AssignmentLibrary()
    global_counts = _empty_counts()
    for phase_index, (phase, weather) in enumerate(PHASES):
        law = WEATHER[weather]
        rows = _draw_rows({
            "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
            "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
            "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
        }, seed + phase_index)
        exact = _exact_vectors(weather)
        fit_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        global_before = _copy_counts(global_counts)
        assignment = library.ingest(f"opaque_{phase_index}", rows)
        _add_counts(global_counts, fit_counts)
        models = {
            "RESET": posterior(fit_counts),
            "LOCKED_MARGINAL": library.model_for(f"opaque_{phase_index}"),
            "GLOBAL_SHRINK": _shrink_model(fit_counts, global_before),
            "FACTORIZED_MODULE": _shrink_model(fit_counts, assignment["history_counts"]),
        }
        for arm, model in models.items():
            row = {"phase": phase, "weather_for_audit": weather,
                   "checkpoint": "shared_fit_prefix",
                   "metrics": _metrics_bank(consequence_vector({"operating": "low", "retry_cost": "19/20"}, model), exact, queries=QUERIES),
                   "observations": (phase_index + 1) * FIT_PER_OPERATOR * len(OPERATORS),
                   "audit_observations": AUDIT_PER_OPERATOR * len(OPERATORS),
                   "modules": len(library.modules),
                   "kappa": str(KAPPA if arm in ("GLOBAL_SHRINK", "FACTORIZED_MODULE")
                                 and (sum(sum(values.values()) for values in (
                                     global_before if arm == "GLOBAL_SHRINK" else assignment["history_counts"]
                                 ).values()) > 0) else F(0)),
                   "base_source": {"RESET": "none", "LOCKED_MARGINAL": "module_history_committed",
                                   "GLOBAL_SHRINK": "global_history", "FACTORIZED_MODULE": "module_history"}[arm]}
            if arm != "RESET":
                row["assignment"] = assignment
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
    arms = ("RESET", "LOCKED_MARGINAL", "GLOBAL_SHRINK", "FACTORIZED_MODULE")
    return {"schema": "acfqp.persistent_consequence_library.v269", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {
                "seeds": list(SEEDS), "fit_per_operator": FIT_PER_OPERATOR,
                "audit_per_operator": AUDIT_PER_OPERATOR, "kappa": str(KAPPA),
                "queries": {name: tuple(map(str, value)) for name, value in QUERIES.items()},
                "assignment_rule": "LOCKED and FACTORIZED arms use V266 marginal action-agreement assignment"},
            "records": records, "summary": {arm: _summary(records, arm) for arm in arms},
            "limitations": ["KAPPA=48 is a fixed doubled-count baseline, equivalent to 24 categorical pseudo-observations; it was not tuned from these outcomes.",
                            "No weather or phase labels enter the estimator.",
                            "No confidence certificate, original Gate or U006 assurance is changed."]}


__all__ = [name for name in globals() if not name.startswith("_")]
