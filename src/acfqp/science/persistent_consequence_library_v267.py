"""Held-out query-family transfer diagnostic for persistent modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS
from .persistent_consequence_library_v263 import (
    PHASES, QUERIES as PRIMARY_QUERIES, WEATHER, _draw_rows, _empty_counts,
    _exact_vectors, consequence_vector, posterior,
)
from .persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, SEEDS, _add_counts, _audit_brier,
    _slice_counts,
)

HELDOUT_QUERIES = {
    "moderate_risk": (F(1), F(2), F(2)),
    "high_goal": (F(1), F(1), F(6)),
    "strict_risk": (F(1), F(6), F(2)),
}
ALL_QUERIES = {**PRIMARY_QUERIES, **HELDOUT_QUERIES}


def _optimal_actions(vectors: dict[str, tuple[F, F, F]], weights: tuple[F, F, F]) -> frozenset[str]:
    def utility(vector: tuple[F, F, F]) -> F:
        reward, failure, success = vector
        return weights[0] * reward - weights[1] * failure + weights[2] * success
    values = {policy: utility(vector) for policy, vector in vectors.items()}
    optimum = max(values.values())
    return frozenset(policy for policy, value in values.items() if value == optimum)


def _agreement(existing: dict[str, dict[str, F]], local: dict[str, dict[str, F]],
               queries: dict[str, tuple[F, F, F]]) -> dict[str, bool]:
    existing_vectors = consequence_vector({"operating": "low", "retry_cost": "19/20"}, existing)
    local_vectors = consequence_vector({"operating": "low", "retry_cost": "19/20"}, local)
    return {name: _optimal_actions(existing_vectors, weights) == _optimal_actions(local_vectors, weights)
            for name, weights in queries.items()}


def _metrics_bank(predicted: dict[str, tuple[F, F, F]], exact: dict[str, tuple[F, F, F]],
                  queries: dict[str, tuple[F, F, F]]) -> dict[str, Any]:
    rows = {}
    for name, weights in queries.items():
        predicted_policy = min(predicted, key=lambda policy: (
            -weights[0] * predicted[policy][0] + weights[1] * predicted[policy][1]
            - weights[2] * predicted[policy][2], policy))
        exact_policy = min(exact, key=lambda policy: (
            -weights[0] * exact[policy][0] + weights[1] * exact[policy][1]
            - weights[2] * exact[policy][2], policy))
        exact_value = weights[0] * exact[exact_policy][0] - weights[1] * exact[exact_policy][1] + weights[2] * exact[exact_policy][2]
        chosen_value = weights[0] * exact[predicted_policy][0] - weights[1] * exact[predicted_policy][1] + weights[2] * exact[predicted_policy][2]
        predicted_value = weights[0] * predicted[predicted_policy][0] - weights[1] * predicted[predicted_policy][1] + weights[2] * predicted[predicted_policy][2]
        predicted_set = _optimal_actions(predicted, weights)
        exact_set = _optimal_actions(exact, weights)
        rows[name] = {"predicted_policy": predicted_policy, "exact_policy": exact_policy,
                      "policy_correct": predicted_policy == exact_policy,
                      "predicted_optimal_actions": sorted(predicted_set),
                      "exact_optimal_actions": sorted(exact_set),
                      "set_action_agreement": predicted_set == exact_set,
                      "exact_value_regret": exact_value - chosen_value,
                      "predicted_value": predicted_value, "exact_optimal_value": exact_value}
    return rows


@dataclass
class QueryAgreementLibrary:
    queries: dict[str, tuple[F, F, F]]
    modules: list[Any] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        local_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        local_model = posterior(local_counts)
        checks = []
        matches = []
        for module in self.modules:
            agreement = _agreement(posterior(module.counts), local_model, self.queries)
            check = {"module_id": module.module_id, "agreement": agreement,
                     "all_match": all(agreement.values())}
            checks.append(check)
            if check["all_match"]:
                matches.append(module)
        if matches:
            module = min(matches, key=lambda candidate: candidate.module_id)
            reason = "reuse_all_query_actions"
            reused = True
            module.contexts.append(context_id)
        else:
            module = self._new(context_id)
            reason = "initial" if len(self.modules) == 1 else "abstain_local_split"
            reused = False
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


def _run_lifecycle(seed: int) -> dict[str, Any]:
    records = {arm: [] for arm in ("RESET", "GLOBAL", "PRIMARY_AGREEMENT", "ALL_QUERY_AGREEMENT")}
    global_counts = _empty_counts()
    primary, all_queries = QueryAgreementLibrary(PRIMARY_QUERIES), QueryAgreementLibrary(ALL_QUERIES)
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
        context_id = f"opaque_{phase_index}"
        primary_assignment = primary.ingest(context_id, rows)
        all_assignment = all_queries.ingest(context_id, rows)
        models = {
            "RESET": (posterior(fit_counts), None, 1),
            "GLOBAL": (posterior(global_counts), None, 1),
            "PRIMARY_AGREEMENT": (primary.model_for(context_id), primary_assignment, len(primary.modules)),
            "ALL_QUERY_AGREEMENT": (all_queries.model_for(context_id), all_assignment, len(all_queries.modules)),
        }
        for arm, (model, assignment, modules) in models.items():
            row = {"phase": phase, "weather_for_audit": weather, "checkpoint": "shared_fit_prefix",
                   "primary_metrics": _metrics_bank(consequence_vector({"operating": "low", "retry_cost": "19/20"}, model), exact, PRIMARY_QUERIES),
                   "heldout_metrics": _metrics_bank(consequence_vector({"operating": "low", "retry_cost": "19/20"}, model), exact, HELDOUT_QUERIES),
                   "observations": (phase_index + 1) * FIT_PER_OPERATOR * len(OPERATORS),
                   "audit_observations": AUDIT_PER_OPERATOR * len(OPERATORS), "modules": modules}
            if assignment is not None:
                row["assignment"] = assignment
                row["audit_brier"] = _audit_brier(model, audit_rows)
            records[arm].append(row)
    return {"seed": seed, "arms": records}


def run_replication() -> dict[str, Any]:
    records = [_run_lifecycle(seed) for seed in SEEDS]
    summary = {}
    for arm in ("RESET", "GLOBAL", "PRIMARY_AGREEMENT", "ALL_QUERY_AGREEMENT"):
        primary, heldout = [], []
        primary_set, heldout_set = [], []
        for record in records:
            rows = record["arms"][arm]
            for name, bucket in (("primary_metrics", primary), ("heldout_metrics", heldout)):
                metrics = [item for row in rows for item in row[name].values()]
                bucket.append((sum(item["policy_correct"] for item in metrics),
                               sum(F(item["exact_value_regret"]) for item in metrics)))
            primary_set.append(sum(item["set_action_agreement"]
                                   for row in rows for item in row["primary_metrics"].values()))
            heldout_set.append(sum(item["set_action_agreement"]
                                   for row in rows for item in row["heldout_metrics"].values()))
        combined_policy = [p[0] + h[0] for p, h in zip(primary, heldout)]
        combined_regret = [p[1] + h[1] for p, h in zip(primary, heldout)]
        combined_set = [p + h for p, h in zip(primary_set, heldout_set)]
        summary[arm] = {
            "primary_policy_correct_counts": [value[0] for value in primary],
            "primary_mean_policy_correct": sum(value[0] for value in primary) / len(primary),
            "primary_set_action_agreement_counts": primary_set,
            "primary_mean_set_action_agreement": sum(primary_set) / (len(records) * len(PRIMARY_QUERIES) * len(PHASES)),
            "primary_exact_regrets": [str(value[1]) for value in primary],
            "primary_mean_exact_regret": str(sum((value[1] for value in primary), F(0)) / len(primary)),
            "heldout_policy_correct_counts": [value[0] for value in heldout],
            "heldout_mean_policy_correct": sum(value[0] for value in heldout) / len(heldout),
            "heldout_set_action_agreement_counts": heldout_set,
            "heldout_mean_set_action_agreement": sum(heldout_set) / (len(records) * len(HELDOUT_QUERIES) * len(PHASES)),
            "heldout_exact_regrets": [str(value[1]) for value in heldout],
            "heldout_mean_exact_regret": str(sum((value[1] for value in heldout), F(0)) / len(heldout)),
            "combined_policy_correct_counts": combined_policy,
            "combined_mean_policy_correct": sum(combined_policy) / len(combined_policy),
            "combined_set_action_agreement_counts": combined_set,
            "combined_mean_set_action_agreement": sum(combined_set) / (
                len(records) * (len(PRIMARY_QUERIES) + len(HELDOUT_QUERIES)) * len(PHASES)),
            "combined_exact_regrets": [str(value) for value in combined_regret],
            "combined_mean_exact_regret": str(sum(combined_regret, F(0)) / len(combined_regret)),
        }
    return {"schema": "acfqp.persistent_consequence_library.v267", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {
                "seeds": list(SEEDS), "fit_per_operator": FIT_PER_OPERATOR,
                "audit_per_operator": AUDIT_PER_OPERATOR,
                "primary_queries": {name: tuple(map(str, value)) for name, value in PRIMARY_QUERIES.items()},
                "heldout_queries": {name: tuple(map(str, value)) for name, value in HELDOUT_QUERIES.items()},
                "rule": "PRIMARY uses primary agreement; ALL uses primary plus held-out agreement"},
            "records": records, "summary": summary,
            "limitations": ["Paired V266 streams are replayed; no new environmental data are added.",
                            "The held-out bank is finite and only three queries.",
                            "No confidence certificate, general strategic claim or original Gate is changed."]}


__all__ = [name for name in globals() if not name.startswith("_")]
