"""Small development slice for persistent, query-reusable consequence modules.

The learner stores action-conditioned reward/failure/success consequences and
reuses them across opaque episodes.  It may split a module after a frozen
held-out prediction check; it never receives the simulator's probabilities or
optimal actions.  This is deliberately separate from the V262 row-confidence
route and is not a scientific Gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
import random
from typing import Any

from .mechanism_switch_task_v205 import ALPHABETS, OPERATORS, WEATHER
from .continual_route_kernels_v202 import COST_PRIOR

QUERIES = {
    "reward": (F(1), F(0), F(0)),
    "risk": (F(1), F(4), F(4)),
    "goal": (F(1), F(0), F(4)),
}
PHASES = (
    ("A0", "normal"),
    ("B", "wet"),
    ("A_prime", "normal"),
    ("C", "blocked"),
)
OPERATING = "low"
RETRY_COST = "19/20"
SAMPLES_PER_OPERATOR = 64
FIT_PER_OPERATOR = 48
VALIDATION_PER_OPERATOR = SAMPLES_PER_OPERATOR - FIT_PER_OPERATOR
# A module is split only when its held-out categorical Brier score is worse
# than the weak three-category prior (0.5); this is fixed before the run.
BRIER_SPLIT_THRESHOLD = F(1, 2)


def _empty_counts() -> dict[str, dict[str, int]]:
    return {operator: {category: 0 for category in ALPHABETS[operator]}
            for operator in OPERATORS}


def posterior(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, F]]:
    """Jeffreys-smoothed categorical posterior used by every arm."""
    result = {}
    for operator in OPERATORS:
        row = counts[operator]
        total = sum(row.values())
        denominator = 2 * total + len(ALPHABETS[operator])
        result[operator] = {
            category: F(2 * row[category] + 1, denominator)
            for category in ALPHABETS[operator]
        }
    return result


def consequence_vector(case: dict[str, str], probabilities: dict[str, dict[str, F]]) -> dict[str, tuple[F, F, F]]:
    """Return (reward, failure, success) for each realizable route policy."""
    short_cost, detour_cost = COST_PRIOR[case["operating"]]
    retry_cost = F(case["retry_cost"])
    short, detour, retry = (probabilities[operator] for operator in OPERATORS)
    return {
        "WAIT": (F(0), F(0), F(0)),
        "SHORT": (-short_cost, short["LOST"], short["DELIVERY"]),
        "DETOUR_RETURN": (-detour_cost, detour["LOST"], detour["DELIVERY"]),
        "DETOUR_RETRY": (
            -detour_cost - detour["RECOVERY"] * retry_cost,
            detour["LOST"] + detour["RECOVERY"] * retry["LOST"],
            detour["DELIVERY"] + detour["RECOVERY"] * retry["DELIVERY"],
        ),
    }


def choose_policy(vectors: dict[str, tuple[F, F, F]], weights: tuple[F, F, F]) -> str:
    def utility(vector: tuple[F, F, F]) -> F:
        reward, failure, success = vector
        reward_weight, failure_penalty, goal_bonus = weights
        return reward_weight * reward - failure_penalty * failure + goal_bonus * success

    return min(vectors, key=lambda policy: (-utility(vectors[policy]), policy))


def _draw_rows(law: dict[str, dict[str, F]], seed: int) -> dict[str, list[str]]:
    rng = random.Random(seed)
    rows: dict[str, list[str]] = {}
    for operator in OPERATORS:
        categories = tuple(ALPHABETS[operator])
        probabilities = [float(law[operator][category]) for category in categories]
        rows[operator] = [rng.choices(categories, weights=probabilities, k=1)[0]
                          for _ in range(SAMPLES_PER_OPERATOR)]
    return rows


def _counts(rows: dict[str, list[str]], end: int) -> dict[str, dict[str, int]]:
    counts = _empty_counts()
    for operator in OPERATORS:
        for category in rows[operator][:end]:
            counts[operator][category] += 1
    return counts


def _brier(module_counts: dict[str, dict[str, int]], rows: dict[str, list[str]]) -> F:
    probabilities = posterior(module_counts)
    squared = []
    for operator in OPERATORS:
        for category in rows[operator]:
            squared.append(sum((probabilities[operator][candidate]
                                - F(candidate == category)) ** 2
                               for candidate in ALPHABETS[operator]))
    return sum(squared, F(0)) / len(squared)


@dataclass
class Module:
    module_id: int
    counts: dict[str, dict[str, int]] = field(default_factory=_empty_counts)
    contexts: list[str] = field(default_factory=list)


@dataclass
class PersistentLibrary:
    """Persistent modules with a held-out split trigger.

    Context identifiers are opaque to the learner.  Assignment uses only fit
    rows and a frozen Brier threshold; validation rows are scored before they
    are committed to the selected module.
    """

    split_threshold: F = BRIER_SPLIT_THRESHOLD
    modules: list[Module] = field(default_factory=list)
    assignments: dict[str, int] = field(default_factory=dict)

    def ingest(self, context_id: str, rows: dict[str, list[str]]) -> dict[str, Any]:
        fit_rows = {operator: values[:FIT_PER_OPERATOR] for operator, values in rows.items()}
        validation_rows = {operator: values[FIT_PER_OPERATOR:] for operator, values in rows.items()}
        before = []
        for module in self.modules:
            before.append((module, _brier(module.counts, fit_rows)))
        if not before:
            module, reason = self._new_module(context_id), "initial"
        else:
            module, best = min(before, key=lambda item: (item[1], item[0].module_id))
            if best > self.split_threshold:
                module, reason = self._new_module(context_id), "heldout_split_trigger"
            else:
                module, reason = module, "reuse"
                module.contexts.append(context_id)
        for operator in OPERATORS:
            for category in fit_rows[operator]:
                module.counts[operator][category] += 1
        validation_brier = _brier(module.counts, validation_rows)
        # The validation prefix is charged and retained, but its score is
        # frozen before it is merged into the module.
        for operator in OPERATORS:
            for category in validation_rows[operator]:
                module.counts[operator][category] += 1
        self.assignments[context_id] = module.module_id
        return {
            "module_id": module.module_id,
            "reason": reason,
            "fit_rows": FIT_PER_OPERATOR * len(OPERATORS),
            "validation_rows": VALIDATION_PER_OPERATOR * len(OPERATORS),
            "validation_brier": validation_brier,
            "module_count_after": len(self.modules),
        }

    def _new_module(self, context_id: str) -> Module:
        module = Module(len(self.modules), contexts=[context_id])
        self.modules.append(module)
        return module

    def model_for(self, context_id: str) -> dict[str, dict[str, F]]:
        if context_id not in self.assignments:
            raise KeyError(f"context {context_id} has not been ingested")
        module = self.modules[self.assignments[context_id]]
        return posterior(module.counts)


def _exact_vectors(weather: str) -> dict[str, tuple[F, F, F]]:
    case = {"operating": OPERATING, "retry_cost": RETRY_COST}
    law = WEATHER[weather]
    return consequence_vector(case, {
        "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
        "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
        "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
    })


def _metrics(predicted: dict[str, tuple[F, F, F]], exact: dict[str, tuple[F, F, F]]) -> dict[str, Any]:
    rows = {}
    for query, weights in QUERIES.items():
        predicted_policy = choose_policy(predicted, weights)
        exact_policy = choose_policy(exact, weights)
        reward, failure, success = predicted[predicted_policy]
        er, ef, es = exact[exact_policy]
        predicted_value = weights[0] * reward - weights[1] * failure + weights[2] * success
        exact_value = weights[0] * er - weights[1] * ef + weights[2] * es
        rows[query] = {
            "predicted_policy": predicted_policy,
            "exact_policy": exact_policy,
            "policy_correct": predicted_policy == exact_policy,
            "exact_value_regret": exact_value - (weights[0] * exact[predicted_policy][0]
                                                  - weights[1] * exact[predicted_policy][1]
                                                  + weights[2] * exact[predicted_policy][2]),
            "predicted_value": predicted_value,
            "exact_optimal_value": exact_value,
        }
    return rows


def run_development(*, seed: int = 263000) -> dict[str, Any]:
    """Run one deterministic four-phase lifecycle with three frozen arms."""
    records: dict[str, list[dict[str, Any]]] = {"RESET": [], "GLOBAL": [], "LIBRARY": []}
    global_counts = _empty_counts()
    library = PersistentLibrary()
    for phase_index, (phase, weather) in enumerate(PHASES):
        case = {"operating": OPERATING, "retry_cost": RETRY_COST}
        law = WEATHER[weather]
        rows = _draw_rows({
            "SHORT_PASS": {"DELIVERY": law[0], "LOST": 1 - law[0]},
            "DETOUR_PASS": {"DELIVERY": law[1], "LOST": law[2], "RECOVERY": law[3]},
            "RECOVERY_RETRY": {"DELIVERY": law[4], "LOST": 1 - law[4]},
        }, seed + phase_index)
        exact = _exact_vectors(weather)
        fit_counts = _counts(rows, FIT_PER_OPERATOR)
        full_counts = _counts(rows, SAMPLES_PER_OPERATOR)
        # Reset arm consumes only the current episode's rows.
        records["RESET"].append({"phase": phase, "weather_for_audit": weather,
            "checkpoint": "fit", "metrics": _metrics(consequence_vector(case, posterior(fit_counts)), exact),
            "observations": FIT_PER_OPERATOR * len(OPERATORS), "modules": 1})
        for operator in OPERATORS:
            for category, count in full_counts[operator].items():
                global_counts[operator][category] += count
        records["GLOBAL"].append({"phase": phase, "weather_for_audit": weather,
            "checkpoint": "fit", "metrics": _metrics(consequence_vector(case, posterior(global_counts)), exact),
            "observations": (phase_index + 1) * SAMPLES_PER_OPERATOR * len(OPERATORS), "modules": 1})
        context_id = f"opaque_{phase_index}"
        assignment = library.ingest(context_id, rows)
        prediction = consequence_vector(case, library.model_for(context_id))
        records["LIBRARY"].append({"phase": phase, "weather_for_audit": weather,
            "checkpoint": "fit_then_validate", "metrics": _metrics(prediction, exact),
            "observations": (phase_index + 1) * SAMPLES_PER_OPERATOR * len(OPERATORS),
            "modules": len(library.modules), "assignment": assignment,
            "assignments": dict(library.assignments)})
    return {
        "schema": "acfqp.persistent_consequence_library.v263",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {
            "seed": seed, "phases": [{"name": name, "weather_for_audit": weather} for name, weather in PHASES],
            "samples_per_operator": SAMPLES_PER_OPERATOR, "fit_per_operator": FIT_PER_OPERATOR,
            "validation_per_operator": VALIDATION_PER_OPERATOR,
            "brier_split_threshold": BRIER_SPLIT_THRESHOLD,
            "queries": {name: tuple(map(str, weights)) for name, weights in QUERIES.items()},
        },
        "arms": records,
        "interpretation": {
            "persistent_library_is_structurally_different": True,
            "weather_is_audit_only": True,
            "opaque_contexts_are_not_used_as_features": True,
            "ground_truth_is_used_only_for_posthoc_metrics": True,
        },
        "limitations": [
            "Four finite route phases and 32 samples per operator are a development diagnostic, not a general-learning result.",
            "The library stores posterior consequence vectors; it does not certify confidence or replace the V262 row proof.",
            "The simulator has a supplied finite route grammar and no natural 2048 episodes.",
            "No original scientific Gate or U006 assurance is touched.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
