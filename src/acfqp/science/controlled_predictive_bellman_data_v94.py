"""Fixed-grid, terminal-anchored H2 supervision from complete retained branches."""
from collections import Counter
from itertools import groupby
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_data_v91 import (
    OPTIONS, REPLICAS, TERMINAL, _rows, _key, _target, extract_prefix,
)
from acfqp.science.controlled_predictive_paired_continuation_data_v92 import _check_pair


N_STEP = 16
STRIDE = 16


def extract_bellman_rows(raw):
    """Extract observed H2 segments; complete return is separate from n-step target."""
    game = raw["game"]
    steps = game["steps"]
    if game["status"] not in TERMINAL:
        return []
    suffix = [0] * (len(steps) + 1)
    for index in range(len(steps) - 1, -1, -1):
        suffix[index] = suffix[index + 1] + steps[index]["score"]
    root, rows = raw["root"], []
    for index in range(4, len(steps), STRIDE):
        boundary = min(index + N_STEP, len(steps))
        active = boundary < len(steps)
        status = "ACTIVE" if active else game["status"]
        board = steps[boundary]["board"] if active else game["final_board"]
        rows.append(dict(query=root["query"], episode=root["episode"], board=list(steps[index]["board"]),
            next_board=list(board), next_active=active,
            n_target=_target(suffix[index] - suffix[boundary], status),
            target=_target(suffix[index], game["status"]), weight=1.0,
            option=raw["option"], replica=raw["replica"], step=index, steps=boundary - index))
    return rows


def load_batch(folder):
    """Load one incremental branch batch; both MC and Bellman require full roots.

    The existing V83 paired execution contract establishes that all active
    steps at index four or later use the corresponding query's H2 controller.
    No environment replay or new interaction is performed during extraction.
    """
    started = perf_counter()
    folder = Path(folder)
    branch_path, means_path = folder / "branch_games.jsonl.gz", folder / "new_rows.jsonl.gz"
    counts, environment, planning = Counter(), Counter(), Counter()
    retained = {}
    for row in _rows(means_path):
        key = _key(row) + (row["option"],)
        if key in retained:
            raise ValueError("duplicate retained paired mean")
        retained[key] = row["target"]
        counts["retained_mean_rows_read"] += 1
    roots, bellman_rows, seen, compared = [], [], set(), set()
    largest_difference = 0.0
    expected = {(option, replica) for option in OPTIONS for replica in range(REPLICAS)}
    for key, stream in groupby(_rows(branch_path), key=lambda row: _key(row["root"])):
        if key in seen:
            raise ValueError("branch root groups must be contiguous and unique")
        seen.add(key)
        indexed, prefixes = {}, {option: [] for option in OPTIONS}
        for raw in stream:
            game = raw["game"]
            if sum(step["score"] for step in game["steps"]) != game["return_score"]:
                raise ValueError("retained trajectory score disagrees with recorded transitions")
            identity = raw["option"], raw["replica"]
            if identity in indexed:
                raise ValueError("duplicate retained option and replica")
            indexed[identity] = raw
            prefixes[raw["option"]].append(extract_prefix(raw))
            counts["trajectories_read"] += 1
            counts["steps_read"] += len(game["steps"])
            counts["terminal_trajectories"] += game["status"] in TERMINAL
            counts["cutoff_trajectories"] += game["status"] == "CUTOFF"
            environment.update(game["work"])
            planning.update(raw["planning_counts"])
        for values in prefixes.values():
            values.sort(key=lambda prefix: prefix["replica"])
        complete = set(indexed) == expected and all(raw["game"]["status"] in TERMINAL for raw in indexed.values())
        query, episode, board = key
        root = dict(board=list(board), query=query, episode=episode, prefixes=prefixes,
                    mc_rows=[], censored=not complete)
        if complete:
            for option in OPTIONS[1:]:
                for replica in range(REPLICAS):
                    _check_pair(indexed[option, replica], indexed["H2", replica])
                    counts["execution_pairs_checked"] += 1
                deltas = [np.asarray(prefixes[option][replica]["full_target"]) -
                          np.asarray(prefixes["H2"][replica]["full_target"]) for replica in range(REPLICAS)]
                mean, mean_key = np.asarray(deltas).mean(axis=0), key + (option,)
                if mean_key not in retained or not np.allclose(mean, retained[mean_key], rtol=0, atol=1e-12):
                    raise ValueError("reconstructed MC means differ from retained new_rows")
                largest_difference = max(largest_difference, float(np.max(np.abs(mean - retained[mean_key]))))
                compared.add(mean_key)
                root["mc_rows"].append(dict(board=list(board), query=query, episode=episode,
                                            option=option, target=mean.tolist()))
            for raw in indexed.values():
                rows = extract_bellman_rows(raw)
                bellman_rows.extend(rows)
                counts["bellman_trajectories"] += bool(rows)
                counts["suffix_score_steps_processed"] += len(raw["game"]["steps"])
            counts["eligible_roots"] += 1
            counts["heldout_eligible_roots" if episode % 5 == 4 else "training_eligible_roots"] += 1
        else:
            counts["censored_roots"] += 1
            counts["censored_root_trajectories"] += len(indexed)
        roots.append(root)
    if compared != set(retained):
        raise ValueError("retained MC means include roots without complete terminal branches")
    counts.update(roots=len(roots), bellman_rows=len(bellman_rows), mc_rows=len(compared),
        training_bellman_rows=sum(row["episode"] % 5 != 4 for row in bellman_rows),
        heldout_bellman_rows=sum(row["episode"] % 5 == 4 for row in bellman_rows),
        terminal_anchor_rows=sum(not row["next_active"] for row in bellman_rows),
        bootstrap_rows=sum(row["next_active"] for row in bellman_rows),
        new_environment_transitions=0, tree_fits=0)
    return roots, bellman_rows, dict(source=str(folder.resolve()),
        paths=dict(branch_games=str(branch_path.resolve()), new_rows=str(means_path.resolve())),
        counts=dict(counts), inherited_environment_work=dict(environment), inherited_planning_work=dict(planning),
        complete_root_execution_contract_matches=True, retained_means_match=True,
        largest_mean_difference=largest_difference, n_step=N_STEP, stride=STRIDE, row_weight=1.0,
        seconds=perf_counter() - started)
