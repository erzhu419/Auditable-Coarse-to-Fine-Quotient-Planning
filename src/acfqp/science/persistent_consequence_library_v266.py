"""Query-action agreement applicability for persistent consequence modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS
from .persistent_consequence_library_v263 import (
    PHASES, QUERIES, WEATHER, _draw_rows, _empty_counts, _exact_vectors,
    _metrics, consequence_vector, posterior,
)
from .persistent_consequence_library_v265 import (
    AUDIT_PER_OPERATOR, FIT_PER_OPERATOR, GuardedLibrary, SEEDS,
    _add_counts, _audit_brier, _slice_counts,
)


def _optimal_actions(vectors: dict[str, tuple[F, F, F]], weights: tuple[F, F, F]) -> frozenset[str]:
    def utility(vector: tuple[F, F, F]) -> F:
        reward, failure, success = vector
        return weights[0] * reward - weights[1] * failure + weights[2] * success
    values = {policy: utility(vector) for policy, vector in vectors.items()}
    optimum = max(values.values())
    return frozenset(policy for policy, value in values.items() if value == optimum)


def _query_agrees(existing: dict[str, dict[str, F]], local: dict[str, dict[str, F]]) -> dict[str, bool]:
    existing_vectors = consequence_vector({"operating": "low", "retry_cost": "19/20"}, existing)
    local_vectors = consequence_vector({"operating": "low", "retry_cost": "19/20"}, local)
    return {name: _optimal_actions(existing_vectors, weights) == _optimal_actions(local_vectors, weights)
            for name, weights in QUERIES.items()}


@dataclass
class AgreementLibrary:
    modules: list[Any] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        local_counts = _slice_counts(rows, 0, FIT_PER_OPERATOR)
        local_model = posterior(local_counts)
        matches = []
        candidate_checks = []
        for module in self.modules:
            agreement = _query_agrees(posterior(module.counts), local_model)
            candidate_checks.append({"module_id": module.module_id, "agreement": agreement,
                                     "all_match": all(agreement.values())})
            if all(agreement.values()):
                matches.append((module, agreement))
        if matches:
            module, agreement = min(matches, key=lambda item: item[0].module_id)
            reason = "reuse_all_query_actions"
            module.contexts.append(context_id)
            reused = True
        else:
            module = self._new(context_id)
            agreement = {}
            reason = "initial" if not self.modules[:-1] else "abstain_local_split"
            reused = False
        # The current phase is added only to the selected or newly created
        # module. A rejected existing module is never polluted.
        _add_counts(module.counts, local_counts)
        self.assignments[context_id] = module.module_id
        audit_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}
        return {"module_id": module.module_id, "reason": reason, "reused": reused,
                "query_action_agreement": agreement, "candidate_checks": candidate_checks,
                "candidate_count_before": len(candidate_checks),
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
    records = {arm: [] for arm in ("RESET", "GLOBAL", "V265_GUARDED", "ACTION_AGREEMENT")}
    global_counts = _empty_counts()
    guarded = GuardedLibrary()
    agreement_library = AgreementLibrary()
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
        guarded_assignment = guarded.ingest(context_id, rows)
        agreement_assignment = agreement_library.ingest(context_id, rows)
        models = {
            "RESET": (posterior(fit_counts), None, 1),
            "GLOBAL": (posterior(global_counts), None, 1),
            "V265_GUARDED": (guarded.model_for(context_id), guarded_assignment, len(guarded.modules)),
            "ACTION_AGREEMENT": (agreement_library.model_for(context_id), agreement_assignment, len(agreement_library.modules)),
        }
        for arm, (model, assignment, modules) in models.items():
            row = {"phase": phase, "weather_for_audit": weather, "checkpoint": "shared_fit_prefix",
                   "metrics": _metrics(consequence_vector({"operating": "low", "retry_cost": "19/20"}, model), exact),
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
    for arm in ("RESET", "GLOBAL", "V265_GUARDED", "ACTION_AGREEMENT"):
        correct, regrets = [], []
        for record in records:
            rows = record["arms"][arm]
            correct.append(sum(item["policy_correct"] for row in rows for item in row["metrics"].values()))
            regrets.append(sum(F(item["exact_value_regret"]) for row in rows for item in row["metrics"].values()))
        summary[arm] = {"policy_correct_counts": correct, "mean_policy_correct": sum(correct) / len(correct),
                        "exact_regrets": [str(value) for value in regrets],
                        "mean_exact_regret": str(sum(regrets, F(0)) / len(regrets))}
    return {"schema": "acfqp.persistent_consequence_library.v266", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE", "settings": {"seeds": list(SEEDS),
                "fit_per_operator": FIT_PER_OPERATOR, "audit_per_operator": AUDIT_PER_OPERATOR,
                "queries": {name: tuple(map(str, value)) for name, value in QUERIES.items()},
                "rule": "reuse iff all three query optimal-action sets agree; otherwise abstain and create a local module"},
            "records": records, "summary": summary,
            "limitations": ["Paired development streams reuse V265's finite route data.",
                            "The action agreement rule covers only three supplied queries.",
                            "No confidence certificate, general strategic claim or original Gate is changed."]}


__all__ = [name for name in globals() if not name.startswith("_")]
