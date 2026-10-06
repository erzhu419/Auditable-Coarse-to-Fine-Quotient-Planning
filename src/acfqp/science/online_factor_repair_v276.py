"""Fixed-budget 2x2 test of online factor revision and lawful coverage."""

from __future__ import annotations

from fractions import Fraction as F
from math import lgamma
import random
from typing import Any

from .crossed_factor_transfer_v270 import CANDIDATE_SUBSETS, CASE, _stream
from .online_support_continual_v275 import (
    EPISODES_PER_PHASE, PHASES, PHASE_INDEX, QUERY_SCHEDULE, TRIALS_PER_EPISODE,
    SOURCE_AUDIT, SOURCE_FIT, SOURCE_PAIRS, TARGET_PAIRS, OLD_SUPPORT, OPERATORS,
    QUERIES, OnlineLearner, _contexts, _projection, _source_counts,
    _choose_policy, _exact_vectors, _law_for_phase, _consequence_vector_dynamic,
    select_factor_subsets,
)

SOURCE_SEEDS = (275401, 275402, 275403, 275404)
SEEDS = (276401, 276402, 276403, 276404)
COVERAGE_QUOTA = 4
ARMS = ("PASSIVE_FIXED", "PASSIVE_REVISED", "COVERED_FIXED", "COVERED_REVISED")
ROUTE_FOR_OPERATOR = {
    "SHORT_PASS": "SHORT", "DETOUR_PASS": "DETOUR_RETRY",
    "RECOVERY_RETRY": "DETOUR_RETRY",
}


def select_online_fields(
    source_contexts: tuple[Any, ...], source_streams: dict[str, Any],
    history: list[tuple[Any, str, int, int, str, str]],
) -> dict[str, Any]:
    """V270 scoring applied to source fit plus only committed online events."""
    selected, scores = {}, {}
    for operator in OPERATORS:
        alphabet = list(OLD_SUPPORT[operator])
        observations = []
        for context in source_contexts:
            observations.extend((context, outcome) for outcome in source_streams[context.context_id][operator][:SOURCE_FIT])
        for context, _phase, _episode, _trial, observed_operator, outcome in history:
            if observed_operator == operator:
                observations.append((context, outcome))
                if outcome not in alphabet:
                    alphabet.append(outcome)
        ranked = []
        for fields in CANDIDATE_SUBSETS:
            groups = {}
            for context, outcome in observations:
                counts = groups.setdefault(_projection(context, fields), dict.fromkeys(alphabet, 0))
                counts[outcome] += 1
            score = 0.0
            for counts in groups.values():
                score += lgamma(len(alphabet) / 2) - lgamma(sum(counts.values()) + len(alphabet) / 2)
                score += sum(lgamma(count + 0.5) - lgamma(0.5) for count in counts.values())
            ranked.append({"fields": fields, "score": score})
        best = min(ranked, key=lambda row: (-row["score"], len(row["fields"]), tuple(row["fields"])))
        selected[operator], scores[operator] = tuple(best["fields"]), ranked
    return {"selected_fields": selected, "scores": scores, "online_events_used": len(history)}


def coverage_request(learner: OnlineLearner, initial_fields: dict[str, tuple[str, ...]], context: Any) -> str | None:
    """An initial source-empty group receives a bounded execution quota."""
    source = _source_counts(context, learner.source_contexts, learner.source_streams, initial_fields)
    for operator in OPERATORS:
        if sum(source[operator].values()):
            continue
        key = _projection(context, initial_fields[operator])
        observed = sum(
            observed_operator == operator and _projection(past_context, initial_fields[operator]) == key
            for past_context, _phase, _episode, _trial, observed_operator, _outcome in learner.history
        )
        if observed < COVERAGE_QUOTA:
            return operator
    return None


def sampling_key(seed: int, context: Any, phase: str, episode: int, trial: int, visit: int, operator: str) -> int:
    # Mixed-radix encoding is injective over the frozen supported roster.
    value = seed * 3 + PHASE_INDEX[phase]
    value = (value * 3 + context.road_profile) * 3 + context.retry_service
    value = value * (EPISODES_PER_PHASE + 1) + episode
    value = value * TRIALS_PER_EPISODE + trial
    return (value * 2 + visit) * len(OPERATORS) + OPERATORS.index(operator)


def execute_policy(context: Any, phase: str, seed: int, episode: int, trial: int, policy: str) -> list[dict[str, Any]]:
    events = []

    def sample(operator: str, visit: int) -> str:
        law = _law_for_phase(context, phase)[operator]
        rng = random.Random(sampling_key(seed, context, phase, episode, trial, visit, operator))
        outcome = rng.choices(tuple(law), weights=[float(p) for p in law.values()], k=1)[0]
        events.append({"operator": operator, "outcome": outcome, "visit": visit})
        return outcome

    if policy == "SHORT":
        sample("SHORT_PASS", 0)
    elif policy in ("DETOUR_RETURN", "DETOUR_RETRY"):
        recovery = sample("DETOUR_PASS", 0)
        if policy == "DETOUR_RETRY" and recovery == "RECOVERY":
            sample("RECOVERY_RETRY", 1)
    return events


def regret(vectors: dict[str, tuple[F, F, F]], query: str, policy: str) -> F:
    weights = QUERIES[query]
    utilities = {name: weights[0] * v[0] - weights[1] * v[1] + weights[2] * v[2] for name, v in vectors.items()}
    return max(utilities.values()) - utilities[policy]


def run_lifecycle(source_seed: int, seed: int) -> dict[str, Any]:
    source_contexts, targets = _contexts(SOURCE_PAIRS, "source"), _contexts(TARGET_PAIRS, "target")
    source_streams = {context.context_id: _stream(context, source_seed + index) for index, context in enumerate(source_contexts)}
    initial = select_factor_subsets(source_contexts, source_streams)
    rows_by_arm, selection_logs, totals = {}, {}, {}
    for arm in ARMS:
        learner = OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(initial["selected_fields"]), source_contexts, source_streams)
        rows, selections = [], []
        for phase in PHASES:
            learner.begin_phase(phase)
            for episode in range(1, EPISODES_PER_PHASE + 1):
                if arm.endswith("REVISED"):
                    selected = select_online_fields(source_contexts, source_streams, learner.history)
                    learner.selected = selected["selected_fields"]
                    selections.append({"phase": phase, "episode": episode, **selected})
                query = QUERY_SCHEDULE[(episode - 1) % len(QUERY_SCHEDULE)]
                for trial in range(TRIALS_PER_EPISODE):
                    context = targets[trial % len(targets)]
                    model = learner.model(context)
                    predicted = _consequence_vector_dynamic(CASE, model)
                    recommendation = _choose_policy(predicted, QUERIES[query])
                    requested = coverage_request(learner, initial["selected_fields"], context) if arm.startswith("COVERED") else None
                    policy = ROUTE_FOR_OPERATOR[requested] if requested else recommendation
                    before = len(learner.history)
                    events = execute_policy(context, phase, seed, episode, trial, policy)
                    for event in events:
                        learner.observe(context, phase, episode, trial, event["operator"], event["outcome"])
                    # Oracle quantities are diagnostics; computed after execution.
                    exact = _exact_vectors(context, phase)
                    rows.append({
                        "phase": phase, "episode": episode, "trial": trial, "query": query,
                        "context": context.as_dict(), "recommended_policy": recommendation,
                        "executed_policy": policy, "coverage_request": requested,
                        "selected_fields": dict(learner.selected),
                        "executed_regret": str(regret(exact, query, policy)),
                        "recommendation_regret": str(regret(exact, query, recommendation)),
                        "history_before": before, "history_after": len(learner.history),
                        "events": events, "short_delivery_estimate_before": str(model["SHORT_PASS"]["DELIVERY"]),
                    })
        rows_by_arm[arm], selection_logs[arm] = rows, selections
        phase_totals = {}
        for phase in PHASES:
            phase_rows = [row for row in rows if row["phase"] == phase]
            phase_totals[phase] = {
                "opportunities": len(phase_rows),
                "executed_regret": str(sum((F(row["executed_regret"]) for row in phase_rows), F(0))),
                "recommendation_regret": str(sum((F(row["recommendation_regret"]) for row in phase_rows), F(0))),
                "executed_events": sum(len(row["events"]) for row in phase_rows),
                "operator_exposures": {operator: sum(event["operator"] == operator for row in phase_rows for event in row["events"]) for operator in OPERATORS},
                "coverage_opportunities": sum(row["coverage_request"] is not None for row in phase_rows),
            }
        totals[arm] = {
            "phases": phase_totals,
            "executed_regret": str(sum((F(p["executed_regret"]) for p in phase_totals.values()), F(0))),
            "recommendation_regret": str(sum((F(p["recommendation_regret"]) for p in phase_totals.values()), F(0))),
            "source_fit_cost": len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
            "source_audit_cost": len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT,
            "final_fields": dict(learner.selected),
        }
    return {"source_seed": source_seed, "seed": seed, "initial_selection": initial,
            "arms": rows_by_arm, "selections": selection_logs, "totals": totals}


def run_replication() -> dict[str, Any]:
    records = [run_lifecycle(source_seed, seed) for source_seed, seed in zip(SOURCE_SEEDS, SEEDS)]
    summaries = {}
    for arm in ARMS:
        totals = [record["totals"][arm] for record in records]
        summaries[arm] = {
            "mean_executed_regret": str(sum((F(total["executed_regret"]) for total in totals), F(0)) / len(totals)),
            "mean_recommendation_regret": str(sum((F(total["recommendation_regret"]) for total in totals), F(0)) / len(totals)),
            "phases": {phase: {
                "mean_executed_regret": str(sum((F(total["phases"][phase]["executed_regret"]) for total in totals), F(0)) / len(totals)),
                "mean_events": sum(total["phases"][phase]["executed_events"] for total in totals) / len(totals),
                "mean_coverage_opportunities": sum(total["phases"][phase]["coverage_opportunities"] for total in totals) / len(totals),
            } for phase in PHASES},
        }
    contrasts = {}
    for left, right in (("COVERED_REVISED", "PASSIVE_FIXED"), ("PASSIVE_REVISED", "PASSIVE_FIXED"),
                        ("COVERED_FIXED", "PASSIVE_FIXED"), ("COVERED_REVISED", "COVERED_FIXED"),
                        ("COVERED_REVISED", "PASSIVE_REVISED")):
        deltas = [F(record["totals"][left]["executed_regret"]) - F(record["totals"][right]["executed_regret"]) for record in records]
        contrasts[f"{left}_minus_{right}"] = {
            "per_seed_regret_delta": list(map(str, deltas)), "mean_regret_delta": str(sum(deltas, F(0)) / len(deltas)),
            "improved_equal_worse": [sum(d < 0 for d in deltas), sum(d == 0 for d in deltas), sum(d > 0 for d in deltas)],
        }
    return {
        "schema": "acfqp.online_factor_repair.v276", "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {"source_seeds": SOURCE_SEEDS, "seeds": SEEDS, "arms": ARMS, "phases": PHASES,
                     "episodes_per_phase": EPISODES_PER_PHASE, "trials_per_episode": TRIALS_PER_EPISODE,
                     "coverage_quota": COVERAGE_QUOTA, "coverage_keys": "initial source-selected fields",
                     "reselection": "episode start using source fit and only committed history",
                     "primary_endpoint": "actual executed policy regret over all 288 opportunities including coverage cost"},
        "records": records, "summary": summaries, "contrasts": contrasts,
    }
