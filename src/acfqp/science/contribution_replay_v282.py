"""Fixed-prefix contribution diagnostics on immutable V280 execution data.

Every variant reads the same RELEVANT_REVISED committed history. Predictions
precede the current row's events; no variant executes a counterfactual policy.
Source-factor, parameter-update and structure-update differences are therefore
recommendation diagnostics, not new on-policy performance estimates.
"""

from fractions import Fraction as F

from . import net_learning_campaign_v280 as online
from . import query_relevant_coverage_v278 as route
from .crossed_factor_transfer_v270 import FEATURES
from .crossed_factor_support_continual_v274 import OLD_SUPPORT

VARIANTS = ("LOCAL_FULL", "SOURCE_FROZEN", "SOURCE_FIXED_UPDATE", "SOURCE_MAP_REVISED")
HISTORY_ARM = "RELEVANT_REVISED"
CONTRIBUTIONS = (("SOURCE_FIXED_UPDATE", "LOCAL_FULL", "source_factor_transfer"),
                 ("SOURCE_FIXED_UPDATE", "SOURCE_FROZEN", "parameter_update"),
                 ("SOURCE_MAP_REVISED", "SOURCE_FIXED_UPDATE", "structure_update"))


def model_from_prefix(variant, target, initial_fields, current_fields,
                      source_contexts, source_streams, history):
    """Jeffreys row means from the variant's allowed source and committed rows."""
    if variant not in VARIANTS:
        raise ValueError("unknown fixed-prefix contribution variant")
    fields = ({op: FEATURES for op in route.OPERATORS} if variant == "LOCAL_FULL"
              else current_fields if variant == "SOURCE_MAP_REVISED" else initial_fields)
    counts = {op: dict.fromkeys(OLD_SUPPORT[op], 0) for op in route.OPERATORS}
    if variant != "LOCAL_FULL":
        for context in source_contexts:
            for op in route.OPERATORS:
                if route._projection(context, fields[op]) == route._projection(target, fields[op]):
                    for outcome in source_streams[context.context_id][op][:online.SOURCE_FIT]:
                        counts[op][outcome] = counts[op].get(outcome, 0) + 1
    if variant != "SOURCE_FROZEN":
        for context, _phase, _episode, _trial, op, outcome in history:
            if route._projection(context, fields[op]) == route._projection(target, fields[op]):
                counts[op][outcome] = counts[op].get(outcome, 0) + 1
    return {op: {category: F(2*n+1, 2*sum(row.values())+len(row))
                 for category, n in row.items()} for op, row in counts.items()}


def replay_history(record, source_contexts, streams):
    """Replay one source's actual relevant-controller prefixes without sampling."""
    initial = {op: tuple(fields) for op, fields in record["initial_selection"]["selected_fields"].items()}
    selections = {(row["phase"], row["episode"]): row for row in record["selections"][HISTORY_ARM]}
    history, changed = [], []
    phase_totals = {phase: {variant: F(0) for variant in VARIANTS} for phase in online.PHASES}
    comparisons = {label: dict(improved=0, equal=0, worse=0, changed_policy=0)
                   for _left, _right, label in CONTRIBUTIONS}
    active = None
    for ordinal, row in enumerate(record["arms"][HISTORY_ARM]):
        phase, episode, trial = row["phase"], row["episode"], row["trial"]
        visible = row["context"]
        target = route._contexts(((visible["road_profile"], visible["retry_service"]),), "target")[0]
        key = phase, episode
        if key != active:
            selection = selections[key]
            if selection["online_events_used"] != len(history):
                raise ValueError("episode selection differs from its committed prefix")
            fields = {op: tuple(value) for op, value in selection["selected_fields"].items()}
            active = key
        if row["history_before"] != len(history):
            raise ValueError("recommendation differs from its committed prefix")
        if fields != {op: tuple(value) for op, value in row["selected_fields"].items()}:
            raise ValueError("retained recommendation and episode selection disagree")
        predictions, choices = {}, {}
        for variant in VARIANTS:
            model = model_from_prefix(variant, target, initial, fields, source_contexts, streams, history)
            predictions[variant] = route._consequence_vector_dynamic(route.CASE, model)
            choices[variant] = route._choose_policy(predictions[variant], route.QUERIES[row["query"]])
        # These exact quantities diagnose already-retained choices only.
        exact = route._exact_vectors(target, phase)
        regrets = {variant: route.regret(exact, row["query"], policy)
                   for variant, policy in choices.items()}
        if (choices["SOURCE_MAP_REVISED"] != row["recommended_policy"]
                or regrets["SOURCE_MAP_REVISED"] != F(row["recommendation_regret"])):
            raise ValueError("MAP replay does not reproduce immutable V280 recommendation")
        for variant in VARIANTS:
            phase_totals[phase][variant] += regrets[variant]
        for left, right, label in CONTRIBUTIONS:
            delta = regrets[left]-regrets[right]
            bucket = comparisons[label]
            bucket["improved" if delta < 0 else "worse" if delta > 0 else "equal"] += 1
            bucket["changed_policy"] += choices[left] != choices[right]
        if len(set(choices.values())) > 1:
            changed.append(dict(ordinal=ordinal, phase=phase, episode=episode, trial=trial,
                context=visible, query=row["query"], history_before=len(history), policies=choices,
                regrets={variant: str(value) for variant, value in regrets.items()},
                initial_fields=initial, revised_fields=fields))
        for event in row["events"]:
            history.append((target, phase, episode, trial, event["operator"], event["outcome"]))
        if row["history_after"] != len(history):
            raise ValueError("committed event count differs from immutable V280 history")
    totals = {variant: sum((values[variant] for values in phase_totals.values()), F(0))
              for variant in VARIANTS}
    return dict(source_seed=record["source_seed"], seed=record["seed"],
        opportunities=len(record["arms"][HISTORY_ARM]), committed_events=len(history),
        regrets={variant: str(value) for variant, value in totals.items()},
        phase_regrets={phase: {variant: str(value) for variant, value in values.items()}
                       for phase, values in phase_totals.items()},
        contributions={label: dict(left=left, right=right, delta=str(totals[left]-totals[right]),
                                  **comparisons[label]) for left, right, label in CONTRIBUTIONS},
        changed_prediction_rows=changed)


def summarize_replay(records):
    result = {}
    for left, right, label in CONTRIBUTIONS:
        deltas = [F(record["contributions"][label]["delta"]) for record in records]
        result[label] = dict(left=left, right=right,
            mean_delta=str(sum(deltas, F(0))/len(deltas)), per_source_delta=list(map(str, deltas)),
            sources_improved_equal_worse=[sum(value < 0 for value in deltas),
                                          sum(value == 0 for value in deltas), sum(value > 0 for value in deltas)],
            decisions={field: sum(record["contributions"][label][field] for record in records)
                       for field in ("improved", "equal", "worse", "changed_policy")})
    return dict(mean_regret={variant: str(sum((F(record["regrets"][variant]) for record in records), F(0))/len(records))
                             for variant in VARIANTS}, contributions=result)


def online_cost_table(retained):
    """Actual V280 arm ledgers; source economics and physical corpus stay separate."""
    records, table = retained["records"], {}
    for arm in online.ARMS:
        items = [record["totals"][arm] for record in records]
        for record, total in zip(records, items):
            rows = record["arms"][arm]
            if (len(rows) != total["start_opportunities"]
                    or sum(len(row["events"]) for row in rows) != total["online_events"]
                    or total["source_fit_cost"]+total["source_reserved_cost"] != total["economic_source_observations"]
                    or total["economic_source_observations"]+total["online_events"] != total["total_economic_observations"]
                    or sum((F(row["executed_regret"]) for row in rows), F(0)) != F(total["executed_regret"])):
                raise ValueError("V280 actual cost ledger differs from retained decisions")
        n = len(items)
        table[arm] = dict(mean_executed_regret=str(sum((F(item["executed_regret"]) for item in items), F(0))/n),
            mean_sampled_utility=str(sum((F(item["sampled_utility"]) for item in items), F(0))/n),
            mean_start_opportunities=sum(item["start_opportunities"] for item in items)/n,
            mean_online_events=sum(item["online_events"] for item in items)/n,
            mean_source_fit=sum(item["source_fit_cost"] for item in items)/n,
            mean_source_reserved=sum(item["source_reserved_cost"] for item in items)/n,
            mean_total_economic_observations=sum(item["total_economic_observations"] for item in items)/n,
            mean_cpu_seconds={scope: sum(item["cpu_seconds"][scope] for item in items)/n for scope in online.CPU_SCOPES})
    contrasts = {f"{left}_minus_{right}": dict(
        per_source_executed_regret_delta=[str(F(record["totals"][left]["executed_regret"])-F(record["totals"][right]["executed_regret"])) for record in records],
        per_source_economic_observation_delta=[record["totals"][left]["total_economic_observations"]-record["totals"][right]["total_economic_observations"] for record in records])
        for left, right in online.CONTRASTS}
    return dict(arms=table, paired_actual_contrasts=contrasts,
        physical_source_observations=retained["accounting"]["physical_source_observations"],
        shared_source_cpu_seconds=retained["accounting"]["shared_source_cpu_seconds"],
        cpu_scope="individual V280 timed operations; excludes serialization, bootstrap and summary assembly",
        scope="actual on-policy V280 outcomes and costs; no equal-quality break-even extrapolation")


def natural_cost_contribution(document):
    """Preserve V281 same-leaf planning/direct paired performance and actual costs."""
    if document["settings"]["value_parameters"] != "SAME_FROZEN_LEAF_ALL_ARMS":
        raise ValueError("natural planning contrast requires the same frozen leaf knowledge")
    summary = document["summary"]
    pair = summary["paired_contrasts"]["FROZEN_H2-DIRECT"]
    return dict(comparison="FROZEN_H2-DIRECT", paired=pair,
        arms={arm: summary["arms"][arm] for arm in ("FROZEN_H2", "DIRECT")},
        shared_physical_accounting=summary["accounting"],
        inherited_source_costs=document["source_provenance"],
        parent_setup_costs=document["parent_setup_costs"],
        resident_source_and_leaf_weight_bytes=document["resident_source_and_leaf_weight_bytes"],
        recorded_run_wall_seconds=document["wall_seconds"],
        recorded_run_cpu_seconds=document["cpu_seconds"],
        output_bytes=document["output_bytes"],
        scope="same frozen parent/leaf knowledge; planning contribution conditional on these source models",
        by_lifecycle=[dict(lifecycle=row["lifecycle"], parent=row["parent"], seed_base=row["seed_base"],
                          shared_warmup={field: row["warmup"][field] for field in (
                              "observations", "physical_games", "physical_costs", "planner_setup_counts",
                              "planner_setup_seconds", "frozen_statistics_observations",
                              "memory_import_seconds", "memory_import_cpu_seconds", "memory_import_counts")},
                          arms={arm: {field: row["arms"][arm][field] for field in (
                              "total_utility", "costs", "planner_setup_counts", "planner_setup_seconds")}
                                for arm in ("FROZEN_H2", "DIRECT")})
                      for row in summary["by_lifecycle"]])
