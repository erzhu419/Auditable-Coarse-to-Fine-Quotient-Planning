"""V275 execution-only continual support learning across contexts.

The learner is kept alive across a fixed A -> B -> A' lifecycle. Target
outcomes are never pre-generated: only operators reached by the selected route
draw an outcome, and the observation is committed after that draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction as F
import random
from typing import Any

from .crossed_factor_continual_v271 import (
    PHASES,
    SOURCE_AUDIT,
    SOURCE_FIT,
    SOURCE_PAIRS,
    TARGET_PAIRS,
    _contexts,
    _projection,
    select_factor_subsets,
)
from .crossed_factor_support_continual_v274 import (
    B_DELAYED_PROBABILITY,
    DELAYED_COST,
    NEW_SUCCESSOR,
    OLD_SUPPORT,
    _consequence_vector_dynamic,
    _law_for_phase as _support_law_for_phase,
)
from .crossed_factor_transfer_v270 import CASE, _stream
from .mechanism_switch_task_v205 import OPERATORS
from .persistent_consequence_library_v263 import QUERIES
from .persistent_consequence_library_v267 import _metrics_bank


SEEDS = (275401, 275402, 275403, 275404)
EPISODES_PER_PHASE = 12
TRIALS_PER_EPISODE = 8
QUERY_SCHEDULE = ("goal", "risk", "reward")
ARMS = (
    "PHASE_RESET_ONLINE",
    "FROZEN_FACTOR_ONLINE",
    "CONTINUAL_FACTOR_ONLINE",
    "LEGACY_COERCE_ONLINE",
)
PHASE_INDEX = {phase: index for index, phase in enumerate(PHASES)}
VISIBLE_CONTEXT_FIELDS = ("road_profile", "retry_service")


def _law_for_phase(context: Any, phase: str) -> dict[str, dict[str, F]]:
    return _support_law_for_phase(context, phase)


def _exact_vectors(context: Any, phase: str) -> dict[str, tuple[F, F, F]]:
    return _consequence_vector_dynamic(CASE, _law_for_phase(context, phase))


def _counter_rng(
    seed: int,
    context: Any,
    phase: str,
    episode: int,
    trial: int,
    visit: int,
    operator: str,
) -> random.Random:
    """Paired arm RNG keyed by context and opportunity, not by arm state."""
    operator_index = {name: index for index, name in enumerate(OPERATORS)}[operator]
    counter = (
        seed * 1_000_003
        + PHASE_INDEX[phase] * 100_003
        + context.road_profile * 10_007
        + context.retry_service * 1_009
        + episode * 101
        + trial * 17
        + visit * 7
        + operator_index
    )
    return random.Random(counter)


def _sample_outcome(
    context: Any,
    phase: str,
    seed: int,
    episode: int,
    trial: int,
    visit: int,
    operator: str,
) -> str:
    law = _law_for_phase(context, phase)[operator]
    rng = _counter_rng(seed, context, phase, episode, trial, visit, operator)
    categories = tuple(law)
    return rng.choices(categories, weights=[float(law[category]) for category in categories], k=1)[0]


def _source_counts(
    target: Any,
    source_contexts: tuple[Any, ...],
    source_streams: dict[str, dict[str, list[str]]],
    fields: dict[str, tuple[str, ...]],
) -> dict[str, dict[str, int]]:
    counts = {operator: {category: 0 for category in OLD_SUPPORT[operator]} for operator in OPERATORS}
    for context in source_contexts:
        for operator in OPERATORS:
            if _projection(context, fields[operator]) != _projection(target, fields[operator]):
                continue
            for outcome in source_streams[context.context_id][operator][:SOURCE_FIT]:
                counts[operator][outcome] += 1
    return counts


def _add_count(
    counts: dict[str, dict[str, int]], operator: str, outcome: str, *, coerce: bool = False
) -> None:
    if outcome not in counts[operator]:
        if coerce:
            outcome = "LOST"
        else:
            counts[operator][outcome] = 0
    counts[operator][outcome] += 1


def _posterior(counts: dict[str, dict[str, int]]) -> dict[str, dict[str, F]]:
    result: dict[str, dict[str, F]] = {}
    for operator, row in counts.items():
        total = sum(row.values())
        denominator = 2 * total + len(row)
        result[operator] = {category: F(2 * count + 1, denominator) for category, count in row.items()}
    return result


@dataclass
class OnlineLearner:
    arm: str
    selected: dict[str, tuple[str, ...]]
    source_contexts: tuple[Any, ...]
    source_streams: dict[str, dict[str, list[str]]]
    history: list[tuple[Any, str, int, int, str, str]] = field(default_factory=list)
    phase_history: list[tuple[Any, str, int, int, str, str]] = field(default_factory=list)
    known_support: dict[str, set[str]] = field(default_factory=lambda: {
        operator: set(categories) for operator, categories in OLD_SUPPORT.items()
    })
    first_new_support_episode: int | None = None
    first_new_support_by_phase: dict[str, int | None] = field(default_factory=dict)
    new_support_events: int = 0

    def begin_phase(self, phase: str) -> None:
        if self.arm == "PHASE_RESET_ONLINE":
            self.phase_history.clear()
            self.known_support = {operator: set(categories) for operator, categories in OLD_SUPPORT.items()}

    def observe(self, context: Any, phase: str, episode: int, trial: int, operator: str, outcome: str) -> None:
        event = (context, phase, episode, trial, operator, outcome)
        self.history.append(event)
        self.phase_history.append(event)
        if outcome not in OLD_SUPPORT[operator]:
            self.new_support_events += 1
            if self.first_new_support_episode is None:
                self.first_new_support_episode = episode
            self.first_new_support_by_phase.setdefault(phase, episode)
            self.known_support[operator].add(outcome)

    def _events(self) -> list[tuple[Any, str, int, int, str, str]]:
        if self.arm == "PHASE_RESET_ONLINE":
            return self.phase_history
        if self.arm == "FROZEN_FACTOR_ONLINE":
            return []
        return self.history

    def model(self, target: Any) -> dict[str, dict[str, F]]:
        if self.arm == "PHASE_RESET_ONLINE":
            fields = {operator: VISIBLE_CONTEXT_FIELDS for operator in OPERATORS}
            counts = {operator: {category: 0 for category in OLD_SUPPORT[operator]} for operator in OPERATORS}
        else:
            fields = self.selected
            counts = _source_counts(target, self.source_contexts, self.source_streams, fields)
        coerce = self.arm == "LEGACY_COERCE_ONLINE"
        for context, _phase, _episode, _trial, operator, outcome in self._events():
            if _projection(context, fields[operator]) != _projection(target, fields[operator]):
                continue
            _add_count(counts, operator, outcome, coerce=coerce)
        return _posterior(counts)


def _choose_policy(vectors: dict[str, tuple[F, F, F]], weights: tuple[F, F, F]) -> str:
    def utility(vector: tuple[F, F, F]) -> F:
        reward, failure, success = vector
        return weights[0] * reward - weights[1] * failure + weights[2] * success
    return min(vectors, key=lambda policy: (-utility(vectors[policy]), policy))


def _execute_policy(
    context: Any,
    phase: str,
    seed: int,
    episode: int,
    trial: int,
    policy: str,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    def sample(operator: str, visit: int) -> str:
        outcome = _sample_outcome(context, phase, seed, episode, trial, visit, operator)
        events.append({"operator": operator, "outcome": outcome, "visit": visit})
        return outcome

    if policy == "SHORT":
        sample("SHORT_PASS", 0)
    elif policy in ("DETOUR_RETURN", "DETOUR_RETRY"):
        detour = sample("DETOUR_PASS", 0)
        if policy == "DETOUR_RETRY" and detour == "RECOVERY":
            sample("RECOVERY_RETRY", 1)
    return events


def _trial_success(policy: str, events: list[dict[str, Any]]) -> bool:
    return policy in ("SHORT", "DETOUR_RETURN", "DETOUR_RETRY") and any(
        event["outcome"] == "DELIVERY" for event in events
    )


def _record_trial(
    learner: OnlineLearner,
    context: Any,
    phase: str,
    episode: int,
    trial: int,
    query: str,
    seed: int,
) -> dict[str, Any]:
    model = learner.model(context)
    predicted_vectors = _consequence_vector_dynamic(CASE, model)
    exact = _exact_vectors(context, phase)
    policy = _choose_policy(predicted_vectors, QUERIES[query])
    exact_policy = _choose_policy(exact, QUERIES[query])
    metrics = _metrics_bank(predicted_vectors, exact, queries={query: QUERIES[query]})[query]
    history_before = len(learner._events())
    committed_history_before = len(learner.history)
    events = _execute_policy(context, phase, seed, episode, trial, policy)
    for event in events:
        learner.observe(context, phase, episode, trial, event["operator"], event["outcome"])
    history_after = len(learner._events())
    committed_history_after = len(learner.history)
    return {
        "context": context.as_dict(), "phase": phase, "episode": episode, "trial": trial,
        "query": query, "predicted_policy": policy, "exact_policy": exact_policy,
        "policy_correct": metrics["policy_correct"], "exact_value_regret": str(metrics["exact_value_regret"]),
        "executed_events": events, "executed_event_count": len(events),
        "actual_success": _trial_success(policy, events),
        "history_before": history_before, "history_after": history_after,
        "committed_history_before": committed_history_before, "committed_history_after": committed_history_after,
        "new_support_observed": any(event["outcome"] == NEW_SUCCESSOR for event in events),
        "new_support_event_total": learner.new_support_events,
        "first_new_support_episode": learner.first_new_support_episode,
        "first_new_support_episode_in_phase": learner.first_new_support_by_phase.get(phase),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        grouped.setdefault(row["phase"], {}).setdefault(str(row["episode"]), []).append(row)
    result: dict[str, Any] = {}
    for phase, episodes in grouped.items():
        result[phase] = {}
        for episode, items in episodes.items():
            regrets = [F(item["exact_value_regret"]) for item in items]
            result[phase][episode] = {
                "denominator": len(items),
                "mean_policy_correct": sum(item["policy_correct"] for item in items) / len(items),
                "mean_exact_regret": str(sum(regrets, F(0)) / len(regrets)),
                "mean_actual_success": sum(item["actual_success"] for item in items) / len(items),
                "mean_executed_events": sum(item["executed_event_count"] for item in items) / len(items),
                "new_support_observations": sum(item["new_support_observed"] for item in items),
            }
    return result


def _lifecycle_summary(rows: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    by_phase: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_phase.setdefault(row["phase"], []).append(row)
    result: dict[str, Any] = {"seed": seed}
    for phase, items in by_phase.items():
        regrets = [F(item["exact_value_regret"]) for item in items]
        result[phase] = {
            "opportunities": len(items),
            "cumulative_exact_regret": str(sum(regrets, F(0))),
            "executed_events": sum(item["executed_event_count"] for item in items),
            "new_support_observations": sum(item["new_support_observed"] for item in items),
            "first_new_support_episode": next(
                (item["first_new_support_episode_in_phase"] for item in items
                 if item["first_new_support_episode_in_phase"] is not None),
                None,
            ),
        }
    return result


def run_replication() -> dict[str, Any]:
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    target_contexts = _contexts(TARGET_PAIRS, "target")
    records: list[dict[str, Any]] = []
    for seed in SEEDS:
        source_streams = {
            context.context_id: _stream(context, seed + index)
            for index, context in enumerate(source_contexts)
        }
        selected = select_factor_subsets(source_contexts, source_streams)
        arm_records: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
        arm_lifecycles: dict[str, dict[str, Any]] = {}
        for arm in ARMS:
            learner = OnlineLearner(arm, selected["selected_fields"], source_contexts, source_streams)
            for phase in PHASES:
                learner.begin_phase(phase)
                for episode in range(1, EPISODES_PER_PHASE + 1):
                    query = QUERY_SCHEDULE[(episode - 1) % len(QUERY_SCHEDULE)]
                    for trial in range(TRIALS_PER_EPISODE):
                        context = target_contexts[trial % len(target_contexts)]
                        row = _record_trial(learner, context, phase, episode, trial, query, seed)
                        row["arm"] = arm
                        row["source_fit_observations_available"] = 0 if arm == "PHASE_RESET_ONLINE" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT
                        row["source_audit_observations_available"] = 0 if arm == "PHASE_RESET_ONLINE" else len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT
                        row["model_visible_history"] = len(learner._events())
                        arm_records[arm].append(row)
            arm_lifecycles[arm] = _lifecycle_summary(arm_records[arm], seed)
            arm_lifecycles[arm]["source_cost"] = {
                "fit_observations": 0 if arm == "PHASE_RESET_ONLINE" else len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
                "audit_observations": 0 if arm == "PHASE_RESET_ONLINE" else len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT,
                "accounting": "paid once per seed for factor arms; not repeated per trial",
            }
        records.append({"seed": seed, "selected": selected, "arms": arm_records, "lifecycle": arm_lifecycles})

    summary = {arm: _summary([row for record in records for row in record["arms"][arm]]) for arm in ARMS}
    return {
        "schema": "acfqp.online_support_continual.v275",
        "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {
            "seeds": list(SEEDS), "source_pairs": SOURCE_PAIRS, "target_pairs": TARGET_PAIRS,
            "phase_order": PHASES, "episodes_per_phase": EPISODES_PER_PHASE,
            "trials_per_episode": TRIALS_PER_EPISODE, "query_schedule": QUERY_SCHEDULE,
            "visible_context_fields": VISIBLE_CONTEXT_FIELDS, "source_fit": SOURCE_FIT,
            "source_audit": SOURCE_AUDIT, "b_delayed_probability": str(B_DELAYED_PROBABILITY),
            "delayed_cost": str(DELAYED_COST), "arms": ARMS,
            "execution_sampling": "only executed operators draw and commit outcomes",
            "pairing_unit": "seed lifecycle; target contexts are repeated opportunities, not independent seeds",
        },
        "records": records,
        "summary": summary,
        "limitations": [
            "This is a synthetic execution-only continuation of V270-V274, not the original Gate.",
            "The source factor selector is learned from the fixed V270-style source slice.",
            "Source learning cost and online executed-event cost are reported separately.",
            "The finite route-trial horizon is not a natural full-game 2048 episode.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
