"""Fixed-root paired resampling under matched actual-transition budgets."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_budgeted_fragments_v86 import sample_root
from acfqp.science.controlled_predictive_evidence_fragments_v88 import (
    OPTIONS, QUERIES, _key, paired_evidence,
)


ALLOCATIONS = ("BALANCED", "EVIDENCE")
REPLICAS = 8
BUDGET = 120000


def _save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")


def _write(handle, value):
    handle.write(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")


def _identity(root):
    return dict(query=root["query"], episode=root["episode"], board=list(root["board"]))


def refresh_root(root):
    """Recompute pooled means and uncertainty from all complete paired replicas."""
    samples = root["pair_deltas"]
    counts = {len(samples[option]) for option in OPTIONS[1:]}
    if len(counts) != 1:
        raise ValueError("a root must have matching paired replica counts for all options")
    means = np.asarray([np.asarray(samples[option], dtype=float).mean(axis=0)
                        for option in OPTIONS[1:]])
    root.update(n_replicas=counts.pop(), target=means.reshape(-1).tolist(),
                targets={option: mean.tolist() for option, mean in zip(OPTIONS[1:], means)},
                evidence={option: paired_evidence(samples[option], root["query"])
                          for option in OPTIONS[1:]})
    return root


def choose_root(roots, arm):
    """Use the already rotated roster; inspect only current complete-block evidence."""
    if arm not in ALLOCATIONS:
        raise ValueError("allocation must be BALANCED or EVIDENCE")
    unresolved = [{option: root["evidence"][option]["upper"] for option in OPTIONS[1:]
                   if root["evidence"][option]["label"] == 0} for root in roots]
    eligible = [index for index, values in enumerate(unresolved) if values]
    adaptive = arm == "EVIDENCE" and bool(eligible)
    if adaptive:
        index = min(eligible, key=lambda i: (-max(unresolved[i].values()), roots[i]["n_replicas"], i))
    else:
        index = min(range(len(roots)), key=lambda i: (roots[i]["n_replicas"], i))
    return roots[index], dict(rule="unresolved_upper" if adaptive else "balanced",
        balanced_fallback=arm == "EVIDENCE" and not eligible,
        unresolved_upper_bounds=unresolved[index],
        maximum_unresolved_upper=max(unresolved[index].values()) if unresolved[index] else None,
        n_replicas=roots[index]["n_replicas"], rotated_order=index)


def acquire_allocation(life, arm, base_roots, rule, folder, budget=BUDGET):
    """Append complete blocks, retaining every transition including the final partial block."""
    if arm not in ALLOCATIONS or budget < 0:
        raise ValueError("allocation must be BALANCED or EVIDENCE and budget nonnegative")
    started = perf_counter()
    folder = Path(folder)
    folder.mkdir()
    roots = deepcopy(list(base_roots))
    queries, logs = {}, []
    with gzip.open(folder / "branch_games.jsonl.gz", "wt") as branches:
        for qi, query in enumerate(QUERIES):
            tick = perf_counter()
            roster = sorted((root for root in roots if root["query"] == query
                             and root["episode"] % 5 != 4), key=lambda root: root["episode"])
            rotation = (life + qi) % len(roster)
            roster = roster[rotation:] + roster[:rotation]
            attempts = Counter()
            work, planning, outcomes = Counter(), Counter(), Counter()
            trajectories = completed = incomplete = block = 0
            while work["sampled_transitions"] < budget:
                root, priority = choose_root(roster, arm)
                attempt = attempts[_key(root)]
                seed = 89_000_000_000 + life * 1_000_000_000 + qi * 100_000_000 + root["episode"] * 100_000 + attempt * 100
                previous = root["n_replicas"]
                before = work["sampled_transitions"]
                _, raw, log = sample_root(root, rule, seed, budget - before, replicas=REPLICAS)
                identity = _identity(root)
                for game in raw:
                    _write(branches, dict(root=identity, block=block, root_attempt_index=attempt, **game))
                work.update(log["ground_work"])
                planning.update(log["planning_counts"])
                outcomes.update(log["outcomes"])
                trajectories += log["trajectories"]
                if log["complete_block"]:
                    for option in OPTIONS[1:]:
                        root["pair_deltas"][option].extend(deepcopy(log["pair_deltas"][option]))
                    refresh_root(root)
                    completed += 1
                else:
                    incomplete += 1
                logs.append(dict(root=identity, block=block, root_attempt_index=attempt, seed_base=seed,
                    original_replicas=previous, resulting_replicas=root["n_replicas"], priority=priority, **log))
                attempts[_key(root)] += 1
                block += 1
                assert before < work["sampled_transitions"] <= budget, (arm, query, before, dict(work), budget)
                print(json.dumps(dict(phase="acquisition", lifecycle=life, allocation=arm, query=query,
                    root_episode=root["episode"], root_attempt_index=attempt,
                    used_transitions=work["sampled_transitions"], budget=budget,
                    completed_blocks=completed, incomplete_blocks=incomplete)), flush=True)
            queries[query] = dict(budget=budget, used_transitions=work["sampled_transitions"],
                branch_work=dict(work), planning_counts=dict(planning), outcomes=dict(outcomes),
                branch_trajectories=trajectories, completed_blocks=completed, incomplete_blocks=incomplete,
                training_replica_counts={str(root["episode"]): root["n_replicas"] for root in roster},
                root_attempt_counts={str(root["episode"]): attempts[_key(root)] for root in roster},
                seconds=perf_counter() - tick)
    roots.sort(key=_key)
    with gzip.open(folder / "training_roots.jsonl.gz", "wt") as output:
        for root in roots:
            _write(output, root)
    _save(folder / "root_logs.json", logs)
    training_count = sum(root["episode"] % 5 != 4 for root in roots)
    record = dict(queries=queries, dataset=dict(roots=len(roots), training_roots=training_count,
        heldout_roots=len(roots) - training_count, records=4 * len(roots)),
        acquisition_seconds=perf_counter() - started)
    _save(folder / "acquisition.json", record)
    return roots, record


def collect_confirmation(life, base_roots, rule, folder, replicas=REPLICAS):
    """Fixed original training roster, fresh paired suffixes, shared by both frozen models."""
    started = perf_counter()
    folder = Path(folder)
    folder.mkdir()
    work, planning, outcomes = Counter(), Counter(), Counter()
    logs = []
    trajectories = complete = 0
    with gzip.open(folder / "branch_games.jsonl.gz", "wt") as branches:
        for qi, query in enumerate(QUERIES):
            roster = sorted((root for root in base_roots if root["query"] == query
                             and root["episode"] % 5 != 4), key=lambda root: root["episode"])
            for root in roster:
                identity = _identity(root)
                seed = 99_000_000_000 + life * 1_000_000_000 + qi * 100_000_000 + root["episode"] * 100_000
                _, raw, log = sample_root(identity, rule, seed, replicas * len(OPTIONS) * 2000, replicas=replicas)
                for game in raw:
                    _write(branches, dict(root=identity, **game))
                work.update(log["ground_work"])
                planning.update(log["planning_counts"])
                outcomes.update(log["outcomes"])
                trajectories += log["trajectories"]
                complete += int(log["complete_block"])
                logs.append(dict(root=identity, seed_base=seed, replicas=replicas, **log))
                print(json.dumps(dict(phase="confirmation", lifecycle=life, query=query,
                    root_episode=root["episode"], complete_block=log["complete_block"],
                    used_transitions=work["sampled_transitions"])), flush=True)
    _save(folder / "root_logs.json", logs)
    record = dict(branch_work=dict(work), planning_counts=dict(planning), outcomes=dict(outcomes),
        roots=len(logs), complete_roots=complete, incomplete_roots=len(logs) - complete,
        branch_trajectories=trajectories, replicas=replicas, seconds=perf_counter() - started)
    _save(folder / "acquisition.json", record)
    return record
