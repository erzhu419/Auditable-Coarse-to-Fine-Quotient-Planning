"""Aligned H2 continuation differences from the original paired V83 branches."""
from collections import Counter
from itertools import groupby
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_data_v91 import (
    OPTIONS, REPLICAS, TERMINAL, _rows, _key, _target, extract_prefix,
)


PAIR_WEIGHT = 1.0 / ((len(OPTIONS) - 1) * REPLICAS)


def _check_pair(candidate, reference):
    if (_key(candidate["root"]) != _key(reference["root"])
            or candidate["replica"] != reference["replica"] or reference["option"] != "H2"
            or candidate["option"] not in OPTIONS[1:]
            or candidate["env_seed"] != reference["env_seed"]
            or candidate["model_seed"] != reference["model_seed"]):
        raise ValueError("paired tails require the same root, query, replica and random streams")
    for raw in (candidate, reference):
        game, controller = raw["game"], raw["controller"]
        n = len(game["steps"])
        duration = 0 if raw["option"] == "H2" else int(raw["option"].split("_")[1])
        if (raw["model_seed"] != raw["env_seed"] + 1_000_000_000_000
                or game["seed"] != raw["env_seed"] or game["initial_spawns"]
                or game["initial_board"] != raw["root"]["board"]
                or game["work"]["sampled_transitions"] != n
                or game["work"]["environment_random_draws"] != 2 * n
                or raw["planning_counts"]["model_uniform_draws"] != 4 * n
                or controller["selected_option"] != raw["option"]
                or controller["initiation_step"] != 0
                or controller["fragment_actions"] != min(duration, n)):
            raise ValueError("retained branch violates the aligned two/four-draw execution contract")


def _suffixes(raw):
    game = raw["game"]
    remaining = 0
    targets = [[0., 0., 0.] for _ in range(len(game["steps"]) + 1)]
    for index in range(len(game["steps"]) - 1, -1, -1):
        remaining += game["steps"][index]["score"]
        targets[index] = _target(remaining, game["status"])
    return targets


def extract_paired_tail_rows(candidate, reference, stride=16):
    """Sample a fixed observed-time grid, retaining an absorbed side as zero future."""
    _check_pair(candidate, reference)
    if any(raw["game"]["status"] not in TERMINAL for raw in (candidate, reference)):
        return []
    left, right = candidate["game"], reference["game"]
    nl, nr = len(left["steps"]), len(right["steps"])
    lt, rt = _suffixes(candidate), _suffixes(reference)
    rows = []
    for index in range(4, max(nl, nr), stride):
        la, ra = index < nl, index < nr
        lb = left["steps"][index]["board"] if la else left["final_board"]
        rb = right["steps"][index]["board"] if ra else right["final_board"]
        lv, rv = lt[index] if la else lt[-1], rt[index] if ra else rt[-1]
        rows.append(dict(candidate_board=list(lb), reference_board=list(rb),
            candidate_active=la, reference_active=ra, target=[a - b for a, b in zip(lv, rv)],
            query=candidate["root"]["query"], episode=candidate["root"]["episode"],
            option=candidate["option"], replica=candidate["replica"], step=index, weight=PAIR_WEIGHT))
    return rows


def load_batch(folder):
    """Stream one original incremental batch; whole-root censoring matches MC."""
    started = perf_counter()
    folder = Path(folder)
    branch_path, means_path = folder / "branch_games.jsonl.gz", folder / "new_rows.jsonl.gz"
    counts, environment, planning = Counter(), Counter(), Counter()
    retained = {}
    for row in _rows(means_path):
        key = _key(row) + (row["option"],)
        if key in retained:
            raise ValueError("duplicate retained V83 paired mean")
        retained[key] = row["target"]
        counts["retained_mean_rows_read"] += 1
    roots, paired_rows, seen, compared = [], [], set(), set()
    largest_difference = 0.0
    expected = {(option, replica) for option in OPTIONS for replica in range(REPLICAS)}
    for key, stream in groupby(_rows(branch_path), key=lambda row: _key(row["root"])):
        if key in seen:
            raise ValueError("V83 root groups must be contiguous and unique")
        seen.add(key)
        indexed, prefixes = {}, {option: [] for option in OPTIONS}
        for raw in stream:
            game = raw["game"]
            if sum(step["score"] for step in game["steps"]) != game["return_score"]:
                raise ValueError("retained trajectory score disagrees with recorded transitions")
            identity = raw["option"], raw["replica"]
            if identity in indexed:
                raise ValueError("duplicate V83 option and replica")
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
                deltas = []
                for replica in range(REPLICAS):
                    candidate, reference = indexed[option, replica], indexed["H2", replica]
                    pair = extract_paired_tail_rows(candidate, reference)
                    paired_rows.extend(pair)
                    counts["paired_trajectories"] += 1
                    counts["paired_score_steps_processed"] += len(candidate["game"]["steps"]) + len(reference["game"]["steps"])
                    cg, rg = candidate["game"], reference["game"]
                    deltas.append(np.asarray(_target(cg["return_score"], cg["status"])) -
                                  np.asarray(_target(rg["return_score"], rg["status"])))
                mean, mean_key = np.asarray(deltas).mean(axis=0), key + (option,)
                if mean_key not in retained or not np.allclose(mean, retained[mean_key], rtol=0, atol=1e-12):
                    raise ValueError("reconstructed V83 MC means differ from retained new_rows")
                largest_difference = max(largest_difference, float(np.max(np.abs(mean - retained[mean_key]))))
                compared.add(mean_key)
                root["mc_rows"].append(dict(board=list(board), query=query, episode=episode,
                                            option=option, target=mean.tolist()))
            counts["eligible_roots"] += 1
            counts["heldout_eligible_roots" if episode % 5 == 4 else "training_eligible_roots"] += 1
        else:
            counts["censored_roots"] += 1
            counts["censored_root_trajectories"] += len(indexed)
        roots.append(root)
    if compared != set(retained):
        raise ValueError("retained MC means include roots without complete terminal branches")
    counts.update(roots=len(roots), paired_rows=len(paired_rows), mc_rows=len(compared),
        training_paired_rows=sum(row["episode"] % 5 != 4 for row in paired_rows),
        heldout_paired_rows=sum(row["episode"] % 5 == 4 for row in paired_rows),
        new_environment_transitions=0, tree_fits=0)
    return roots, paired_rows, dict(source=str(folder.resolve()),
        paths=dict(branch_games=str(branch_path.resolve()), new_rows=str(means_path.resolve())),
        counts=dict(counts), inherited_environment_work=dict(environment), inherited_planning_work=dict(planning),
        paired_crn_contract_matches=True, retained_means_match=True,
        largest_mean_difference=largest_difference, row_weight=PAIR_WEIGHT, seconds=perf_counter() - started)
