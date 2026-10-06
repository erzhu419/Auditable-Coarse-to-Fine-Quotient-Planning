"""Extract four-action consequences and terminal H2 tails from retained V83 branches."""
from collections import Counter
import gzip
from itertools import groupby
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS


REPLICAS = 8
PREFIX_ACTIONS = 4
TAIL_STRIDE = 16
TERMINAL = ("WON", "LOST")


def _rows(path):
    with gzip.open(path, "rt") as handle:
        for line in handle:
            yield json.loads(line)


def _key(root):
    return root["query"], root["episode"], tuple(root["board"])


def _target(score, status):
    return [score / 2048, float(status == "LOST"), float(status == "WON")]


def extract_prefix(raw, horizon=PREFIX_ACTIONS):
    """Keep the observed prefix and count a terminal event on only one side."""
    game = raw["game"]
    steps = game["steps"]
    used = min(horizon, len(steps))
    status = steps[used - 1]["status"] if used else game["status"]
    if game["status"] == "CUTOFF" and len(steps) < horizon:
        status = "CUTOFF"
    board = steps[used - 1]["next_board"] if used else game["initial_board"]
    direct = _target(sum(step["score"] for step in steps[:used]), status)
    complete = game["status"] in TERMINAL
    return dict(replica=raw["replica"], option=raw["option"], direct=direct,
        boundary_board=list(board), status=status,
        full_target=_target(game["return_score"], game["status"]) if complete else None)


def extract_h2_tail_rows(raw, stride=TAIL_STRIDE):
    """Use active states after action four, with equal total weight per trajectory."""
    game = raw["game"]
    steps = game["steps"]
    if game["status"] not in TERMINAL or len(steps) <= PREFIX_ACTIONS:
        return []
    selected = list(range(PREFIX_ACTIONS, len(steps), stride))
    if selected[-1] != len(steps) - 1:
        selected.append(len(steps) - 1)
    selected = set(selected)
    weight = 1.0 / len(selected)
    root = raw["root"]
    remaining, rows = 0, []
    for index in range(len(steps) - 1, PREFIX_ACTIONS - 1, -1):
        remaining += steps[index]["score"]
        if index in selected:
            rows.append(dict(query=root["query"], episode=root["episode"],
                board=list(steps[index]["board"]), target=_target(remaining, game["status"]),
                weight=weight, option=raw["option"], replica=raw["replica"], step=index))
    rows.reverse()
    return rows


def load_batch(folder):
    """Read one V83 incremental checkpoint, excluding censored roots as whole groups.

    The retained paired means are compared once during extraction. This function
    performs no simulation and records the historical work separately.
    """
    started = perf_counter()
    folder = Path(folder)
    branch_path, means_path = folder / "branch_games.jsonl.gz", folder / "new_rows.jsonl.gz"
    counts = Counter()
    inherited_environment, inherited_planning = Counter(), Counter()
    retained = {}
    for row in _rows(means_path):
        key = _key(row) + (row["option"],)
        if key in retained:
            raise ValueError("duplicate retained V83 paired mean")
        retained[key] = row["target"]
        counts["retained_mean_rows_read"] += 1
    roots, tail_rows, seen, compared = [], [], set(), set()
    largest_difference = 0.0
    for key, stream in groupby(_rows(branch_path), key=lambda row: _key(row["root"])):
        if key in seen:
            raise ValueError("V83 branch root groups must be contiguous and unique")
        seen.add(key)
        trajectories = list(stream)
        prefixes = {option: [] for option in OPTIONS}
        indexed = {}
        for raw in trajectories:
            game = raw["game"]
            if sum(step["score"] for step in game["steps"]) != game["return_score"]:
                raise ValueError("retained trajectory score disagrees with its recorded transitions")
            identity = raw["option"], raw["replica"]
            if identity in indexed:
                raise ValueError("duplicate retained V83 option and replica")
            indexed[identity] = extract_prefix(raw)
            prefixes[raw["option"]].append(indexed[identity])
            counts["trajectories_read"] += 1
            counts["steps_read"] += len(game["steps"])
            counts["terminal_trajectories"] += game["status"] in TERMINAL
            counts["cutoff_trajectories"] += game["status"] == "CUTOFF"
            inherited_environment.update(game.get("work", {}))
            inherited_planning.update(raw.get("planning_counts", {}))
        for values in prefixes.values():
            values.sort(key=lambda prefix: prefix["replica"])
        expected = {(option, replica) for option in OPTIONS for replica in range(REPLICAS)}
        complete = set(indexed) == expected and all(prefix["full_target"] is not None for prefix in indexed.values())
        query, episode, board = key
        root = dict(board=list(board), query=query, episode=episode, prefixes=prefixes,
                    mc_rows=[], censored=not complete)
        if complete:
            for option in OPTIONS[1:]:
                deltas = [np.asarray(indexed[option, replica]["full_target"]) -
                          np.asarray(indexed["H2", replica]["full_target"]) for replica in range(REPLICAS)]
                mean = np.asarray(deltas).mean(axis=0)
                mean_key = key + (option,)
                if mean_key not in retained or not np.allclose(mean, retained[mean_key], rtol=0, atol=1e-12):
                    raise ValueError("reconstructed V83 paired means differ from retained new_rows")
                largest_difference = max(largest_difference, float(np.max(np.abs(mean - retained[mean_key]))))
                compared.add(mean_key)
                root["mc_rows"].append(dict(board=list(board), query=query, episode=episode,
                                            option=option, target=mean.tolist()))
            for raw in trajectories:
                rows = extract_h2_tail_rows(raw)
                tail_rows.extend(rows)
                counts["tail_trajectories"] += bool(rows)
            counts["eligible_roots"] += 1
            counts["heldout_eligible_roots" if episode % 5 == 4 else "training_eligible_roots"] += 1
        else:
            counts["censored_roots"] += 1
            counts["censored_root_trajectories"] += len(trajectories)
        roots.append(root)
    if compared != set(retained):
        raise ValueError("retained V83 paired means include roots without complete terminal branches")
    counts.update(roots=len(roots), tail_rows=len(tail_rows), mc_rows=len(compared),
        training_tail_rows=sum(row["episode"] % 5 != 4 for row in tail_rows),
        heldout_tail_rows=sum(row["episode"] % 5 == 4 for row in tail_rows),
        new_environment_transitions=0, tree_fits=0)
    return roots, tail_rows, dict(source=str(folder.resolve()),
        paths=dict(branch_games=str(branch_path.resolve()), new_rows=str(means_path.resolve())),
        counts=dict(counts), inherited_environment_work=dict(inherited_environment),
        inherited_planning_work=dict(inherited_planning), largest_mean_difference=largest_difference,
        retained_means_match=True, seconds=perf_counter() - started)
