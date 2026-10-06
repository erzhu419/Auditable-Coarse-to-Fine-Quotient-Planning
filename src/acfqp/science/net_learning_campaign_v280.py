"""Independent net-gain campaign for the unchanged V278 relevance controller."""

from fractions import Fraction as F
import random
from time import process_time

from . import query_relevant_coverage_v278 as v278
from .crossed_factor_transfer_v270 import FEATURES
from .continual_route_kernels_v202 import COST_PRIOR
from .crossed_factor_support_continual_v274 import DELAYED_COST, NEW_SUCCESSOR

SOURCE_SEEDS = tuple(28040100 + 100 * index for index in range(128))
SEEDS = tuple(28090100 + 100 * index for index in range(128))
ARMS = ("FULL_CONTEXT_LOCAL", "FROZEN_FACTOR", "FIXED_FACTOR_UPDATE",
        "PASSIVE_REVISED", "RELEVANT_REVISED")
PHASES = v278.PHASES
EPISODES_PER_PHASE = v278.EPISODES_PER_PHASE
TRIALS_PER_EPISODE = v278.TRIALS_PER_EPISODE
SOURCE_PAIRS, TARGETS = v278.SOURCE_PAIRS, v278.TARGETS
SOURCE_FIT, SOURCE_RESERVED = v278.SOURCE_FIT, v278.SOURCE_AUDIT
OPERATORS, QUERY_SCHEDULE = v278.OPERATORS, v278.QUERY_SCHEDULE
BOOTSTRAP_SEED, BOOTSTRAP_DRAWS = 28000001, 20_000
CPU_SCOPES = ("prediction", "selection", "coverage", "execution", "oracle_accounting")
CONTRASTS = (("RELEVANT_REVISED", "PASSIVE_REVISED"),
             ("RELEVANT_REVISED", "FULL_CONTEXT_LOCAL"),
             ("FIXED_FACTOR_UPDATE", "FROZEN_FACTOR"),
             ("PASSIVE_REVISED", "FIXED_FACTOR_UPDATE"),
             ("RELEVANT_REVISED", "FIXED_FACTOR_UPDATE"),
             ("PASSIVE_REVISED", "FULL_CONTEXT_LOCAL"))


def sampled_vector(policy, events):
    """Realized route consequence, using only the completed route events."""
    if policy == "WAIT":
        return F(0), F(0), F(0)
    short_cost, detour_cost = COST_PRIOR[v278.CASE["operating"]]
    if policy == "SHORT":
        outcome = events[0]["outcome"]
        return -short_cost, F(outcome == "LOST"), F(outcome == "DELIVERY")
    outcome = events[0]["outcome"]
    reward = -detour_cost
    if policy == "DETOUR_RETRY" and outcome == "RECOVERY":
        outcome = events[1]["outcome"]
        reward -= F(v278.CASE["retry_cost"])
        if outcome == NEW_SUCCESSOR:
            reward -= DELAYED_COST
    return reward, F(outcome in ("LOST", NEW_SUCCESSOR)), F(outcome == "DELIVERY")


def run_lifecycle(source_seed, seed):
    start = process_time()
    source_contexts = v278._contexts(SOURCE_PAIRS, "source")
    streams = {context.context_id: v278._stream(context, source_seed + index)
               for index, context in enumerate(source_contexts)}
    generation_cpu = process_time() - start
    start = process_time()
    initial = v278.select_factor_subsets(source_contexts, streams)
    source_cpu = {"generation": generation_cpu, "fit": process_time() - start}
    arms, selection_logs, totals = {}, {}, {}
    for arm in ARMS:
        local = arm == "FULL_CONTEXT_LOCAL"
        fields = {op: FEATURES for op in OPERATORS} if local else dict(initial["selected_fields"])
        learner = v278.OnlineLearner(
            "FROZEN_FACTOR_ONLINE" if arm == "FROZEN_FACTOR" else "CONTINUAL_FACTOR_ONLINE",
            fields, () if local else source_contexts, {} if local else streams)
        rows, selections = [], []
        cpu = dict.fromkeys(CPU_SCOPES, 0.0)
        for phase in PHASES:
            learner.begin_phase(phase)
            for episode in range(1, EPISODES_PER_PHASE + 1):
                if arm in ("PASSIVE_REVISED", "RELEVANT_REVISED"):
                    start = process_time()
                    selected = v278.select_online_fields(source_contexts, streams, learner.history)
                    learner.selected = selected["selected_fields"]
                    selections.append({"phase": phase, "episode": episode, **selected})
                    cpu["selection"] += process_time() - start
                query = QUERY_SCHEDULE[(episode - 1) % len(QUERY_SCHEDULE)]
                for trial in range(TRIALS_PER_EPISODE):
                    context = TARGETS[trial % len(TARGETS)]
                    start = process_time()
                    model = learner.model(context)
                    greedy = v278._choose_policy(v278._consequence_vector_dynamic(v278.CASE, model),
                                                v278.QUERIES[query])
                    cpu["prediction"] += process_time() - start
                    requested, policy, trace = None, greedy, []
                    if arm == "RELEVANT_REVISED":
                        start = process_time()
                        requested, policy, trace = v278.relevant_request(
                            learner, initial["selected_fields"], context, query, len(rows), model, use_cost=False)
                        cpu["coverage"] += process_time() - start
                    before = len(learner.history)
                    start = process_time()
                    events = v278.execute_policy(context, phase, seed, episode, trial, policy)
                    for event in events:
                        learner.observe(context, phase, episode, trial, event["operator"], event["outcome"])
                    cpu["execution"] += process_time() - start
                    # The oracle sees the completed action, never the controller.
                    start = process_time()
                    exact = v278._exact_vectors(context, phase)
                    executed_regret = v278.regret(exact, query, policy)
                    recommendation_regret = v278.regret(exact, query, greedy)
                    sampled = sampled_vector(policy, events)
                    sampled_utility = v278.utility(sampled, query)
                    cpu["oracle_accounting"] += process_time() - start
                    rows.append({"phase": phase, "episode": episode, "trial": trial, "query": query,
                        "context": context.as_dict(), "recommended_policy": greedy, "executed_policy": policy,
                        "coverage_request": requested, "coverage_trace": trace, "forced_override": policy != greedy,
                        "selected_fields": dict(learner.selected), "history_before": before,
                        "history_after": len(learner.history), "events": events,
                        "executed_regret": str(executed_regret),
                        "recommendation_regret": str(recommendation_regret),
                        "sampled_reward": str(sampled[0]), "sampled_failure": str(sampled[1]),
                        "sampled_success": str(sampled[2]), "sampled_utility": str(sampled_utility)})
        phase_totals = {}
        for phase in PHASES:
            items = [row for row in rows if row["phase"] == phase]
            phase_totals[phase] = {
                "opportunities": len(items),
                "executed_regret": str(sum((F(r["executed_regret"]) for r in items), F(0))),
                "recommendation_regret": str(sum((F(r["recommendation_regret"]) for r in items), F(0))),
                "executed_events": sum(len(r["events"]) for r in items),
                "coverage_opportunities": sum(r["coverage_request"] is not None for r in items),
                "forced_overrides": sum(r["forced_override"] for r in items),
                "operator_exposures": {op: sum(e["operator"] == op for r in items for e in r["events"])
                                       for op in OPERATORS}}
            phase_totals[phase].update({key: str(sum((F(r[key]) for r in items), F(0)))
                for key in ("sampled_reward", "sampled_failure", "sampled_success", "sampled_utility")})
        online_events = len(learner.history)
        source_fit = 0 if local else len(source_contexts) * len(OPERATORS) * SOURCE_FIT
        source_reserved = 0 if local else len(source_contexts) * len(OPERATORS) * SOURCE_RESERVED
        arms[arm], selection_logs[arm] = rows, selections
        totals[arm] = {"phases": phase_totals,
            "executed_regret": str(sum((F(p["executed_regret"]) for p in phase_totals.values()), F(0))),
            "recommendation_regret": str(sum((F(p["recommendation_regret"]) for p in phase_totals.values()), F(0))),
            "start_opportunities": len(rows), "online_events": online_events,
            "source_fit_cost": source_fit, "source_reserved_cost": source_reserved,
            "economic_source_observations": source_fit + source_reserved,
            "total_economic_observations": source_fit + source_reserved + online_events,
            "cpu_seconds": cpu, "final_fields": dict(learner.selected)}
        totals[arm].update({key: str(sum((F(p[key]) for p in phase_totals.values()), F(0)))
            for key in ("sampled_reward", "sampled_failure", "sampled_success", "sampled_utility")})
    return {"source_seed": source_seed, "seed": seed, "initial_selection": initial,
            "source_cpu_seconds": source_cpu, "arms": arms, "selections": selection_logs, "totals": totals}


def bootstrap_interval(deltas):
    rng = random.Random(BOOTSTRAP_SEED)
    values = list(map(float, deltas))
    draws = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(BOOTSTRAP_DRAWS))
    return [v278._percentile(draws, .025), v278._percentile(draws, .975)]


def paired_contrast(deltas):
    return {"mean_regret_delta": str(sum(deltas, F(0)) / len(deltas)),
            "ci95": bootstrap_interval(deltas),
            "per_seed_regret_delta": list(map(str, deltas)),
            "improved_equal_worse": [sum(d < 0 for d in deltas), sum(d == 0 for d in deltas), sum(d > 0 for d in deltas)]}


def summarize(records):
    summaries = {}
    for arm in ARMS:
        items = [r["totals"][arm] for r in records]
        summaries[arm] = {
            "mean_executed_regret": str(sum((F(t["executed_regret"]) for t in items), F(0)) / len(items)),
            "mean_recommendation_regret": str(sum((F(t["recommendation_regret"]) for t in items), F(0)) / len(items)),
            "mean_start_opportunities": sum(t["start_opportunities"] for t in items) / len(items),
            "mean_online_events": sum(t["online_events"] for t in items) / len(items),
            "mean_source_fit_cost": sum(t["source_fit_cost"] for t in items) / len(items),
            "mean_source_reserved_cost": sum(t["source_reserved_cost"] for t in items) / len(items),
            "mean_total_economic_observations": sum(t["total_economic_observations"] for t in items) / len(items),
            "mean_coverage_opportunities": sum(sum(p["coverage_opportunities"] for p in t["phases"].values()) for t in items) / len(items),
            "mean_forced_overrides": sum(sum(p["forced_overrides"] for p in t["phases"].values()) for t in items) / len(items),
            "mean_cpu_seconds": {scope: sum(t["cpu_seconds"][scope] for t in items) / len(items) for scope in CPU_SCOPES},
            "phases": {p: str(sum((F(t["phases"][p]["executed_regret"]) for t in items), F(0)) / len(items)) for p in PHASES}}
        summaries[arm].update({f"mean_{key}": str(sum((F(t[key]) for t in items), F(0)) / len(items))
            for key in ("sampled_reward", "sampled_failure", "sampled_success", "sampled_utility")})
    contrasts = {f"{left}_minus_{right}": paired_contrast([
        F(r["totals"][left]["executed_regret"]) - F(r["totals"][right]["executed_regret"])
        for r in records]) for left, right in CONTRASTS}
    primary = contrasts["RELEVANT_REVISED_minus_PASSIVE_REVISED"]
    co_primary = contrasts["RELEVANT_REVISED_minus_FULL_CONTEXT_LOCAL"]
    supported = primary["ci95"][1] < 0 and co_primary["ci95"][1] < 0
    actual_return_contrasts = {}
    for left, right in CONTRASTS[:2]:
        deltas = [F(r["totals"][left]["sampled_utility"]) - F(r["totals"][right]["sampled_utility"])
                  for r in records]
        actual_return_contrasts[f"{left}_minus_{right}"] = {
            "mean_utility_delta": str(sum(deltas, F(0)) / len(deltas)),
            "ci95": bootstrap_interval(deltas), "per_seed_utility_delta": list(map(str, deltas)),
            "improved_equal_worse": [sum(d > 0 for d in deltas), sum(d == 0 for d in deltas), sum(d < 0 for d in deltas)]}
    return {"summary": summaries, "contrasts": contrasts, "actual_return_contrasts": actual_return_contrasts,
        "net_gain_result": "NET_GAIN_SUPPORTED" if supported else "NET_GAIN_NOT_SUPPORTED",
        "by_source": [{"source_seed": r["source_seed"], "seed": r["seed"],
            "initial_fields": r["initial_selection"]["selected_fields"], "totals": r["totals"],
            "primary_delta": primary["per_seed_regret_delta"][i],
            "co_primary_delta": co_primary["per_seed_regret_delta"][i]} for i, r in enumerate(records)],
        "accounting": {
            "physical_source_observations": len(records) * len(SOURCE_PAIRS) * len(OPERATORS) * (SOURCE_FIT + SOURCE_RESERVED),
            "physical_source_fit_observations": len(records) * len(SOURCE_PAIRS) * len(OPERATORS) * SOURCE_FIT,
            "physical_source_reserved_observations": len(records) * len(SOURCE_PAIRS) * len(OPERATORS) * SOURCE_RESERVED,
            "online_events_all_arms": sum(len(row["events"]) for r in records for arm in ARMS for row in r["arms"][arm]),
            "start_opportunities_all_arms": sum(r["totals"][arm]["start_opportunities"] for r in records for arm in ARMS),
            "shared_source_cpu_seconds": {scope: sum(r["source_cpu_seconds"][scope] for r in records)
                                          for scope in ("generation", "fit")}}}


def run_replication():
    records = []
    for source_seed, seed in zip(SOURCE_SEEDS, SEEDS):
        records.append(run_lifecycle(source_seed, seed))
        print(f"completed {len(records)}/{len(SOURCE_SEEDS)} source_seed={source_seed} target_seed={seed}", flush=True)
    return {"schema": "acfqp.net_learning_campaign.v280", "status": "DEVELOPMENT_COMPLETE",
        "scientific_gate": "NOT_A_FORMAL_GATE",
        "settings": {"source_seeds": SOURCE_SEEDS, "seeds": SEEDS, "arms": ARMS,
            "phase_order": PHASES, "episodes_per_phase": EPISODES_PER_PHASE,
            "trials_per_episode": TRIALS_PER_EPISODE, "coverage_quota": v278.COVERAGE_QUOTA,
            "source_fit": SOURCE_FIT, "source_reserved": SOURCE_RESERVED,
            "bootstrap_draws": BOOTSTRAP_DRAWS, "bootstrap_seed": BOOTSTRAP_SEED,
            "primary": "RELEVANT_REVISED_minus_PASSIVE_REVISED",
            "co_primary": "RELEVANT_REVISED_minus_FULL_CONTEXT_LOCAL",
            "support_rule": "both whole-lifecycle paired upper 95% confidence limits strictly below zero",
            "controller": "unchanged V278 relevant_request(use_cost=False)",
            "budget": "same 288 START opportunities; LOCAL has no source cost, lifetime observation counts are unequal",
            "cpu_scopes": CPU_SCOPES,
            "cpu_method": "process_time; source generation/initial fit shared and separate from per-arm scopes"},
        "records": records, **summarize(records)}
