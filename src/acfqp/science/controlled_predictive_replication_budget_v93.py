"""Frozen round-robin terminal acquisition under an exact transition budget."""
from collections import Counter, defaultdict
from copy import deepcopy
from time import perf_counter

from acfqp.science.controlled_predictive_budgeted_fragments_v86 import sample_root
from acfqp.science.controlled_predictive_continuation_data_v91 import _key
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS


BASE_REPLICAS = 8


def _metadata(root):
    return dict(query=root["query"], episode=root["episode"], board=list(root["board"]))


def acquire_extra(roots, rule, life, checkpoint, budget, emit_raw_callback):
    """Return complete one-replica blocks; retain all incomplete-block costs.

    The roster and its order depend only on the frozen original training roots.
    Completion under a transition cap depends on realized trajectory lengths;
    this is a budgeted acquisition algorithm, not an unbiased estimator claim.
    """
    if budget < 0:
        raise ValueError("transition budget must be nonnegative")
    started = perf_counter()
    records = list(roots)
    roster = sorted([root for root in records if not root["censored"]
        and root["episode"] < checkpoint and root["episode"] % 5 != 4],
        key=lambda root: (root["episode"], root["query"], tuple(root["board"])))
    rotation = (life + checkpoint) % len(roster) if roster else 0
    roster = roster[rotation:] + roster[:rotation]
    statistics = [dict(root=_metadata(root), attempted_blocks=0, complete_extra_replicas=0,
        incorporated_transitions=0, unincorporated_transitions=0) for root in roster]
    complete_blocks, block_logs = [], []
    ground, planning, outcomes = Counter(), Counter(), Counter()
    incorporated, unincorporated = Counter(), Counter()
    attempt, trajectories = 0, 0
    while roster and ground["sampled_transitions"] < budget:
        index = attempt % len(roster)
        root = roster[index]
        remaining = budget - ground["sampled_transitions"]
        seed = 293_000_000_000 + life * 10_000_000 + checkpoint * 1_000_000 + attempt * 1000
        rows, raw, record = sample_root(root, rule, seed, remaining, replicas=1)
        # Reasons are recorded per trajectory. At exactly 2000 remaining actions,
        # the fixed cap and budget can both bind; their reason counts may overlap.
        consumed, budget_cutoffs, max_step_cutoffs = 0, 0, 0
        for row in raw:
            available = remaining - consumed
            if row["game"]["status"] == "CUTOFF":
                budget_cutoffs += available <= 2000
                max_step_cutoffs += available >= 2000
            consumed += row["game"]["work"]["sampled_transitions"]
            emit_raw_callback(dict(life=life, checkpoint=checkpoint, attempt=attempt,
                                   root=_metadata(root), **row))
        metadata = dict(root=_metadata(root), attempt=attempt, seed_base=seed)
        complete = record["complete_block"]
        if complete:
            complete_blocks.append(dict(checkpoint=checkpoint, **metadata, rows=deepcopy(rows)))
        cost = record["ground_work"]["sampled_transitions"]
        statistics[index]["attempted_blocks"] += 1
        statistics[index]["complete_extra_replicas"] += complete
        statistics[index]["incorporated_transitions" if complete else "unincorporated_transitions"] += cost
        (incorporated if complete else unincorporated).update(record["ground_work"])
        block_logs.append(dict(**metadata, **record,
            budget_truncated=not complete and record["budget_exhausted"],
            budget_cutoff_trajectories=budget_cutoffs, max_step_cutoff_trajectories=max_step_cutoffs))
        ground.update(record["ground_work"])
        planning.update(record["planning_counts"])
        outcomes.update(record["outcomes"])
        trajectories += record["trajectories"]
        attempt += 1
    return complete_blocks, dict(checkpoint=checkpoint, budget=budget,
        used_transitions=ground["sampled_transitions"], unused_budget=budget - ground["sampled_transitions"],
        roster=[_metadata(root) for root in roster], roster_rotation=rotation, root_statistics=statistics,
        attempted_blocks=attempt, complete_blocks=len(complete_blocks), incomplete_blocks=attempt - len(complete_blocks),
        budget_truncated_blocks=sum(block["budget_truncated"] for block in block_logs),
        budget_cutoff_trajectories=sum(block["budget_cutoff_trajectories"] for block in block_logs),
        max_step_cutoff_trajectories=sum(block["max_step_cutoff_trajectories"] for block in block_logs),
        ground_work=dict(ground), planning_counts=dict(planning), outcomes=dict(outcomes),
        incorporated_ground_work=dict(incorporated), unincorporated_ground_work=dict(unincorporated),
        trajectories=trajectories, blocks=block_logs, new_source_games=0, tree_fits=0,
        seconds=perf_counter() - started)


def merge_rows(roots, complete_blocks, checkpoint):
    """Weight the original eight-replica mean and each complete added pair once."""
    records, blocks = list(roots), list(complete_blocks)
    eligible = {_key(root): root for root in records
                if root["episode"] < checkpoint and not root["censored"]}
    extras = defaultdict(list)
    for block in blocks:
        if block["checkpoint"] > checkpoint:
            continue
        key = _key(block["root"])
        if key not in eligible or key[1] % 5 == 4:
            raise ValueError("extra block is outside the eligible original training roster")
        if {row["option"] for row in block["rows"]} != set(OPTIONS[1:]) or len(block["rows"]) != 4:
            raise ValueError("an extra block needs all four one-replica paired targets")
        extras[key].append({row["option"]: row["target"] for row in block["rows"]})
    rows, root_statistics = [], []
    for key, root in eligible.items():
        extra = extras[key]
        total = BASE_REPLICAS + len(extra)
        for original in root["mc_rows"]:
            row = deepcopy(original)
            row["target"] = [(BASE_REPLICAS * value + sum(block[row["option"]][component] for block in extra)) / total
                             for component, value in enumerate(original["target"])]
            rows.append(row)
        root_statistics.append(dict(root=_metadata(root), base_replicas=BASE_REPLICAS,
                                    extra_replicas=len(extra), total_replicas=total))
    return rows, dict(checkpoint=checkpoint, records=len(rows), roots=len(eligible),
        training_roots=sum(key[1] % 5 != 4 for key in eligible),
        heldout_roots=sum(key[1] % 5 == 4 for key in eligible),
        complete_extra_blocks=sum(len(values) for values in extras.values()), root_statistics=root_statistics,
        tree_fits=0, new_environment_transitions=0)
