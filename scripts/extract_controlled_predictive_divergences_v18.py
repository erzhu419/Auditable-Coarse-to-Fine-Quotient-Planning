"""Posthoc first action divergences from an already-loaded V18 history payload.

No model, profile, provider or environment is constructed. Only the two actions
actually selected at a shared state are compared; full legal-action sets and
counterfactual action values are not retained here.
"""

from collections import Counter
import math


BASE = "online_mass_bound"
CACHED = "online_cached_balanced_gap_stop"
CASE = "v6_crossing_rescue_pair_3"
TOL = 1e-10


def _key(key):
    return key[0], tuple(key[1])


def _pair(pair):
    return _key(pair[0]), pair[1]


def _edge_key(edge):
    return _key(edge["node"]["key"]), edge["reward"], edge["probability"]


def _advance(node, prior, alias, checks):
    counts = prior.copy()
    if alias == "BASE":
        for pair in node["requested_rows"]:
            counts[_pair(pair)] += 1
        before, after = node["rows_before"], node["rows_after"]
    else:
        for request in node["requested_batches"]:
            pair, index = _pair(request["row_key"]), request["batch_index"]
            checks["batch_index_checks"] += 1
            checks["batch_index_mismatches"] += int(counts[pair] != index)
            counts[pair] = index + 1
        before, after = node["batches_before"], node["batches_after"]
    checks["path_batch_total_checks"] += 2
    checks["path_batch_total_mismatches"] += int(sum(prior.values()) != before)
    checks["path_batch_total_mismatches"] += int(sum(counts.values()) != after)
    return counts


def _decision(node, counts, actions, alias):
    gap = node.get("gap_assessments", [])
    missing = []
    if "acquisition_stop_reason" not in node:
        missing.append("acquisition_stop_reason_not_recorded")
    if not gap:
        missing.append("gap_assessment_not_recorded_at_this_decision")
    return {
        "action": node["action"],
        "selected_action_batch_counts": {action: counts[_key(node["key"]), action] for action in actions},
        "quota": node["quota"],
        "batches_before": node["rows_before"] if alias == "BASE" else node["batches_before"],
        "batches_after": node["rows_after"] if alias == "BASE" else node["batches_after"],
        "lower": node["lower"], "upper": node["upper"], "unresolved": node["unresolved"],
        "acquisition_stop_reason": node.get("acquisition_stop_reason"),
        "last_gap_assessment": gap[-1] if gap else None,
        "unavailable": missing,
    }


def _context(case, run, query, group):
    base, cached = run["methods"][BASE][query], run["methods"][CACHED][query]
    prefix = run["shared_warm"]["prefix"]
    initial = Counter(_pair(pair) for pair in prefix["requested_row_order"])
    checks = Counter(warm_rows_checks=1, warm_rows_mismatches=int(
        sum(initial.values()) != prefix["actual_rows_acquired"] or any(n != 1 for n in initial.values())))
    divergences, unavailable = [], []

    def visit(old, new, old_prior, new_prior, history, history_edges, reach):
        if old["key"] != new["key"]:
            unavailable.append({"history": history, "reason": "shared_history_state_mismatch"})
            return
        history = history + [old["key"]]
        if "action" not in old or "action" not in new:
            if old.get("status") != new.get("status"):
                unavailable.append({"history": history, "reason": "terminal_status_mismatch"})
            return
        checks["shared_decision_nodes"] += 1
        old_counts = _advance(old, old_prior, "BASE", checks)
        new_counts = _advance(new, new_prior, "CACHED", checks)
        if old["action"] != new["action"]:
            actions = sorted({old["action"], new["action"]})
            divergences.append({
                "key": old["key"], "history": history, "history_edges": history_edges,
                "true_shared_history_reach": reach, "compared_selected_actions": actions,
                "BASE": _decision(old, old_counts, actions, "BASE"),
                "CACHED": _decision(new, new_counts, actions, "CACHED"),
            })
            return
        old_edges, new_edges = sorted(old["children"], key=_edge_key), sorted(new["children"], key=_edge_key)
        if [_edge_key(edge) for edge in old_edges] != [_edge_key(edge) for edge in new_edges]:
            unavailable.append({"history": history, "reason": "same_action_child_edges_do_not_match"})
            return
        for old_edge, new_edge in zip(old_edges, new_edges):
            edge_record = {"action": old["action"], "reward": old_edge["reward"],
                           "probability": old_edge["probability"]}
            visit(old_edge["node"], new_edge["node"], old_counts, new_counts,
                  history, history_edges + [edge_record], reach * old_edge["probability"])

    visit(base["trace"], cached["trace"], initial, initial, [], [], 1.0)
    return {
        "case": case["case"]["name"], "seed": run["sample_seed"], "query": query, "group": group,
        "root_components": {alias: row["root_metrics"] for alias, row in (("BASE", base), ("CACHED", cached))},
        "cached_minus_base_value": cached["root_metrics"]["value"] - base["root_metrics"]["value"],
        "base_extra_regret_over_full": base["quality"]["root_extra_regret_over_full_state"],
        "first_divergence_count": len(divergences),
        "probability_of_reaching_a_first_divergence": math.fsum(row["true_shared_history_reach"] for row in divergences),
        "divergences": divergences, "retained_count_checks": dict(checks), "unavailable": unavailable,
    }


def summarize(payload):
    witnesses, unavailable = [], []
    for case in payload["cases"]:
        if case["case"]["name"] != CASE:
            continue
        for run in case["sampled_runs"]:
            seed = run["sample_seed"]
            if seed not in (832101, 832102):
                continue
            for query in payload["settings"]["query_order"]:
                base, cached = run["methods"][BASE][query], run["methods"][CACHED][query]
                group = None
                if seed == 832101 and query in ("risk_5", "probe_risk_2"):
                    if cached["root_metrics"]["value"] < base["root_metrics"]["value"] - TOL:
                        group = "two_cached_regressions_versus_base"
                    else:
                        unavailable.append({"seed": seed, "query": query, "reason": "retained_cached_regression_not_present"})
                if seed == 832102 and base["quality"]["root_extra_regret_over_full_state"] > TOL:
                    group = "original_eight_base_worse_than_full"
                if group:
                    witnesses.append(_context(case, run, query, group))
    checks = Counter()
    for witness in witnesses:
        checks.update(witness["retained_count_checks"])
    return {
        "schema": "acfqp.controlled_predictive_first_divergences.v18",
        "witness_context_count": len(witnesses),
        "group_context_counts": dict(Counter(w["group"] for w in witnesses)),
        "contexts_with_action_divergence": sum(bool(w["divergences"]) for w in witnesses),
        "first_divergence_count": sum(w["first_divergence_count"] for w in witnesses),
        "retained_count_checks": dict(checks), "witnesses": witnesses, "unavailable": unavailable,
        "scope": "Posthoc retained V18 BASE versus CACHED histories only, stopping at each branch's first action difference. Batch counts include the shared warm and all acquisition on that actual history. True reach uses only shared retained transition edges. The two selected actions are compared; other actions, their legality, local counterfactual values and causal explanations are unavailable. BASE stop reasons and gap diagnostics were not recorded. Last gap assessment precedes the last batch if the quota was exhausted, so it need not describe the final updated model. No new observations or ground-model calls.",
    }
