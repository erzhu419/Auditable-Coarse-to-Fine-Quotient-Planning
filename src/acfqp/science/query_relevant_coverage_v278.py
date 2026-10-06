"""V278: lawful coverage filtered by query relevance and acquisition cost."""

from fractions import Fraction as F
import random

from .online_factor_repair_v276 import (
    PHASES, SOURCE_PAIRS, TARGET_PAIRS, SOURCE_FIT, SOURCE_AUDIT, OPERATORS,
    EPISODES_PER_PHASE, TRIALS_PER_EPISODE, QUERY_SCHEDULE, COVERAGE_QUOTA,
    QUERIES, CASE, OnlineLearner, _contexts, _stream, _projection, _source_counts,
    _choose_policy, _exact_vectors, _consequence_vector_dynamic,
    select_factor_subsets, select_online_fields, coverage_request,
    ROUTE_FOR_OPERATOR, execute_policy, regret,
)
from .online_factor_confirmation_v277 import _percentile

SOURCE_SEEDS = tuple(27840100 + 100 * index for index in range(64))
SEEDS = tuple(27890100 + 100 * index for index in range(64))
ARMS = ("PASSIVE_REVISED", "QUOTA_REVISED", "RELEVANT_REVISED", "COST_RELEVANT_REVISED")
BOOTSTRAP_SEED = 27800001
BOOTSTRAP_DRAWS = 20_000
TARGETS = _contexts(TARGET_PAIRS, "target")
SCHEDULE = tuple((TARGETS[trial % len(TARGETS)], QUERY_SCHEDULE[(episode - 1) % len(QUERY_SCHEDULE)])
                 for _phase in PHASES for episode in range(1, EPISODES_PER_PHASE + 1)
                 for trial in range(TRIALS_PER_EPISODE))


def utility(vector, query):
    weights = QUERIES[query]
    return weights[0] * vector[0] - weights[1] * vector[1] + weights[2] * vector[2]


def relevance_envelopes(model, operator, support):
    """Exact one-row worst regret, conditional on other posterior rows."""
    predicted = _consequence_vector_dynamic(CASE, model)
    greedy = {query: _choose_policy(predicted, weights) for query, weights in QUERIES.items()}
    result = dict.fromkeys(QUERIES, F(0))
    for outcome in support:
        vertex = {category: F(category == outcome) for category in support}
        values = _consequence_vector_dynamic(CASE, {**model, operator: vertex})
        for query in QUERIES:
            result[query] = max(result[query], regret(values, query, greedy[query]))
    return result


def remaining_query_counts(context, ordinal):
    pair = (context.road_profile, context.retry_service)
    return {query: sum((target.road_profile, target.retry_service) == pair and future_query == query
                       for target, future_query in SCHEDULE[ordinal:]) for query in QUERIES}


def relevant_request(learner, initial_fields, context, query, ordinal, model, use_cost):
    """Read only source fit, committed history and the public query schedule."""
    initial_source = _source_counts(context, learner.source_contexts, learner.source_streams, initial_fields)
    current_source = _source_counts(context, learner.source_contexts, learner.source_streams, learner.selected)
    predicted = _consequence_vector_dynamic(CASE, model)
    greedy = _choose_policy(predicted, QUERIES[query])
    traces = []
    for operator in OPERATORS:
        if sum(initial_source[operator].values()):
            continue
        key = _projection(context, initial_fields[operator])
        observed = sum(op == operator and _projection(past, initial_fields[operator]) == key
                       for past, _phase, _episode, _trial, op, _outcome in learner.history)
        remaining = COVERAGE_QUOTA - observed
        if remaining <= 0:
            continue
        trace = {"operator": operator, "remaining_quota": remaining}
        traces.append(trace)
        if sum(current_source[operator].values()):
            trace["reason"] = "CURRENT_SOURCE_COVERED"
            continue
        support = tuple(sorted(learner.known_support[operator]))
        envelopes = relevance_envelopes(model, operator, support)
        trace["relevance_by_query"] = {q: str(value) for q, value in envelopes.items()}
        if envelopes[query] == 0:
            trace["reason"] = "IRRELEVANT"
            continue
        if operator == "DETOUR_PASS":
            choices = {p: predicted[p] for p in ("DETOUR_RETURN", "DETOUR_RETRY")}
            probe = _choose_policy(choices, QUERIES[query])
        else:
            probe = ROUTE_FOR_OPERATOR[operator]
        reach = model["DETOUR_PASS"]["RECOVERY"] if operator == "RECOVERY_RETRY" else F(1)
        loss = utility(predicted[greedy], query) - utility(predicted[probe], query)
        counts = remaining_query_counts(context, ordinal)
        potential = sum((counts[q] * envelopes[q] for q in QUERIES), F(0))
        attempts = F(remaining) / reach if reach else None
        trace.update(probe=probe, reach_probability=str(reach), probe_loss=str(loss),
                     remaining_queries=counts, potential_gain=str(potential),
                     expected_attempts=str(attempts) if attempts is not None else None)
        if probe == greedy:
            trace["reason"] = "NATURAL"
            return operator, probe, traces
        if use_cost:
            if attempts is None or attempts > sum(counts.values()):
                trace["reason"] = "ATTEMPT_BUDGET"
                continue
            if attempts * loss > potential:
                trace["reason"] = "COST_EXCEEDS_POTENTIAL"
                continue
        trace["reason"] = "ACCEPT"
        return operator, probe, traces
    return None, greedy, traces


def run_lifecycle(source_seed, seed):
    source_contexts = _contexts(SOURCE_PAIRS, "source")
    streams = {context.context_id: _stream(context, source_seed + index) for index, context in enumerate(source_contexts)}
    initial = select_factor_subsets(source_contexts, streams)
    arms, selection_logs, totals = {}, {}, {}
    for arm in ARMS:
        learner = OnlineLearner("CONTINUAL_FACTOR_ONLINE", dict(initial["selected_fields"]), source_contexts, streams)
        rows, selections = [], []
        for phase in PHASES:
            learner.begin_phase(phase)
            for episode in range(1, EPISODES_PER_PHASE + 1):
                selected = select_online_fields(source_contexts, streams, learner.history)
                learner.selected = selected["selected_fields"]
                selections.append({"phase": phase, "episode": episode, **selected})
                query = QUERY_SCHEDULE[(episode - 1) % len(QUERY_SCHEDULE)]
                for trial in range(TRIALS_PER_EPISODE):
                    context = TARGETS[trial % len(TARGETS)]
                    model = learner.model(context)
                    greedy = _choose_policy(_consequence_vector_dynamic(CASE, model), QUERIES[query])
                    requested, policy, trace = None, greedy, []
                    if arm == "QUOTA_REVISED":
                        requested = coverage_request(learner, initial["selected_fields"], context)
                        policy = ROUTE_FOR_OPERATOR[requested] if requested else greedy
                    elif arm != "PASSIVE_REVISED":
                        requested, policy, trace = relevant_request(learner, initial["selected_fields"], context,
                            query, len(rows), model, use_cost=arm == "COST_RELEVANT_REVISED")
                    before = len(learner.history)
                    events = execute_policy(context, phase, seed, episode, trial, policy)
                    for event in events:
                        learner.observe(context, phase, episode, trial, event["operator"], event["outcome"])
                    exact = _exact_vectors(context, phase)
                    rows.append({"phase": phase, "episode": episode, "trial": trial, "query": query,
                        "context": context.as_dict(), "recommended_policy": greedy, "executed_policy": policy,
                        "coverage_request": requested, "coverage_trace": trace, "forced_override": policy != greedy,
                        "selected_fields": dict(learner.selected), "history_before": before,
                        "history_after": len(learner.history), "events": events,
                        "executed_regret": str(regret(exact, query, policy)),
                        "recommendation_regret": str(regret(exact, query, greedy))})
        phase_totals = {}
        for phase in PHASES:
            items = [row for row in rows if row["phase"] == phase]
            phase_totals[phase] = {
                "opportunities": len(items), "executed_regret": str(sum((F(r["executed_regret"]) for r in items), F(0))),
                "executed_events": sum(len(r["events"]) for r in items),
                "coverage_opportunities": sum(r["coverage_request"] is not None for r in items),
                "forced_overrides": sum(r["forced_override"] for r in items),
                "operator_exposures": {op: sum(e["operator"] == op for r in items for e in r["events"]) for op in OPERATORS},
            }
        arms[arm], selection_logs[arm] = rows, selections
        totals[arm] = {"phases": phase_totals,
                      "executed_regret": str(sum((F(p["executed_regret"]) for p in phase_totals.values()), F(0))),
                      "source_fit_cost": len(source_contexts) * len(OPERATORS) * SOURCE_FIT,
                      "source_audit_cost": len(source_contexts) * len(OPERATORS) * SOURCE_AUDIT,
                      "final_fields": dict(learner.selected)}
    return {"source_seed": source_seed, "seed": seed, "initial_selection": initial,
            "arms": arms, "selections": selection_logs, "totals": totals}


def paired_contrast(deltas):
    rng = random.Random(BOOTSTRAP_SEED)
    values = list(map(float, deltas))
    draws = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(BOOTSTRAP_DRAWS))
    return {"mean_regret_delta": str(sum(deltas, F(0)) / len(deltas)),
            "ci95": [_percentile(draws, .025), _percentile(draws, .975)],
            "per_seed_regret_delta": list(map(str, deltas)),
            "improved_equal_worse": [sum(d < 0 for d in deltas), sum(d == 0 for d in deltas), sum(d > 0 for d in deltas)]}


def summarize(records):
    summaries = {}
    for arm in ARMS:
        items = [r["totals"][arm] for r in records]
        summaries[arm] = {
            "mean_executed_regret": str(sum((F(t["executed_regret"]) for t in items), F(0)) / len(items)),
            "mean_online_events": sum(sum(p["executed_events"] for p in t["phases"].values()) for t in items) / len(items),
            "mean_coverage_opportunities": sum(sum(p["coverage_opportunities"] for p in t["phases"].values()) for t in items) / len(items),
            "mean_forced_overrides": sum(sum(p["forced_overrides"] for p in t["phases"].values()) for t in items) / len(items),
            "phases": {p: str(sum((F(t["phases"][p]["executed_regret"]) for t in items), F(0)) / len(items)) for p in PHASES},
        }
    pairs = (("COST_RELEVANT_REVISED", "QUOTA_REVISED"), ("COST_RELEVANT_REVISED", "PASSIVE_REVISED"),
             ("RELEVANT_REVISED", "QUOTA_REVISED"), ("COST_RELEVANT_REVISED", "RELEVANT_REVISED"))
    contrasts = {f"{left}_minus_{right}": paired_contrast([
        F(r["totals"][left]["executed_regret"]) - F(r["totals"][right]["executed_regret"]) for r in records]) for left, right in pairs}
    primary = contrasts["COST_RELEVANT_REVISED_minus_QUOTA_REVISED"]
    return {"summary": summaries, "contrasts": contrasts,
            "primary_result": "SUPPORTED_ON_COHORT" if primary["ci95"][1] < 0 else "NOT_SUPPORTED_ON_COHORT",
            "by_source": [{"source_seed": r["source_seed"], "seed": r["seed"],
                "initial_fields": r["initial_selection"]["selected_fields"], "totals": r["totals"],
                "primary_delta": primary["per_seed_regret_delta"][i]} for i, r in enumerate(records)],
            "accounting": {"physical_source_observations": len(records) * len(SOURCE_PAIRS) * len(OPERATORS) * (SOURCE_FIT + SOURCE_AUDIT),
                "online_events_all_arms": sum(len(row["events"]) for r in records for arm in ARMS for row in r["arms"][arm]),
                "start_opportunities_all_arms": len(records) * len(ARMS) * len(SCHEDULE)}}


def run_replication():
    records = []
    for source_seed, seed in zip(SOURCE_SEEDS, SEEDS):
        records.append(run_lifecycle(source_seed, seed))
        print(f"completed {len(records)}/{len(SOURCE_SEEDS)} source_seed={source_seed} target_seed={seed}", flush=True)
    return {"schema": "acfqp.query_relevant_coverage.v278", "status": "DEVELOPMENT_COMPLETE",
            "scientific_gate": "NOT_A_FORMAL_GATE",
            "settings": {"source_seeds": SOURCE_SEEDS, "seeds": SEEDS, "arms": ARMS,
                "phase_order": PHASES, "episodes_per_phase": EPISODES_PER_PHASE,
                "trials_per_episode": TRIALS_PER_EPISODE, "coverage_quota": COVERAGE_QUOTA,
                "source_fit": SOURCE_FIT, "source_audit": SOURCE_AUDIT,
                "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
                "cost_budget": "current and later exact-context public query opportunities",
                "quota_keys": "initial source projections", "cost_rule": "optimistic frozen-model heuristic"},
            "records": records, **summarize(records)}
