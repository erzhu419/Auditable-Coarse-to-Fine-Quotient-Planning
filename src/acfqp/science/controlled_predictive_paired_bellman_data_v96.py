"""Synchronous paired H2 Bellman segments from complete retained V83 branches."""
from collections import Counter
from itertools import groupby
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_data_v91 import (
    OPTIONS, REPLICAS, TERMINAL, _rows, _key, _target, extract_prefix,
)
from acfqp.science.controlled_predictive_paired_continuation_data_v92 import (
    PAIR_WEIGHT, _check_pair, _suffixes,
)


N_STEP = 16
STRIDE = 16


def _state(game, suffixes, index):
    active = index < len(game["steps"])
    board = game["steps"][index]["board"] if active else game["final_board"]
    return list(board), active, suffixes[min(index, len(game["steps"]))]


def extract_paired_bellman_rows(candidate, reference):
    """Retain the fixed observed-time grid and zero future for an absorbed side.

    Segment targets subtract the next boundary's remaining R/F/S from the
    current boundary's remaining R/F/S. Thus a terminal event enters exactly
    its final segment, and never enters segments starting after absorption.
    """
    _check_pair(candidate, reference)
    if any(raw["game"]["status"] not in TERMINAL for raw in (candidate, reference)):
        return []
    left, right = candidate["game"], reference["game"]
    nl, nr = len(left["steps"]), len(right["steps"])
    lt, rt = _suffixes(candidate), _suffixes(reference)
    rows = []
    for index in range(4, max(nl, nr), STRIDE):
        lb, la, lv = _state(left, lt, index)
        rb, ra, rv = _state(right, rt, index)
        next_lb, next_la, next_lv = _state(left, lt, index + N_STEP)
        next_rb, next_ra, next_rv = _state(right, rt, index + N_STEP)
        rows.append(dict(candidate_board=lb, reference_board=rb,
            candidate_active=la, reference_active=ra,
            next_candidate_board=next_lb, next_reference_board=next_rb,
            next_candidate_active=next_la, next_reference_active=next_ra,
            n_target=[(a - an) - (b - bn) for a, an, b, bn in zip(lv, next_lv, rv, next_rv)],
            target=[a - b for a, b in zip(lv, rv)],
            query=candidate["root"]["query"], episode=candidate["root"]["episode"],
            option=candidate["option"], replica=candidate["replica"], step=index, weight=PAIR_WEIGHT,
            candidate_steps=min(index + N_STEP, nl) - min(index, nl),
            reference_steps=min(index + N_STEP, nr) - min(index, nr)))
    return rows


def load_batch(folder):
    """Stream one incremental batch with V92's complete-root and MC contracts."""
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
                    paired_rows.extend(extract_paired_bellman_rows(candidate, reference))
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
    diagonal = [row for row in paired_rows if row["candidate_active"] == row["reference_active"]
                and row["candidate_board"] == row["reference_board"]]
    counts.update(roots=len(roots), paired_rows=len(paired_rows), mc_rows=len(compared),
        training_paired_rows=sum(row["episode"] % 5 != 4 for row in paired_rows),
        heldout_paired_rows=sum(row["episode"] % 5 == 4 for row in paired_rows),
        bootstrap_rows=sum(row["next_candidate_active"] or row["next_reference_active"] for row in paired_rows),
        terminal_anchor_rows=sum(not row["next_candidate_active"] and not row["next_reference_active"] for row in paired_rows),
        candidate_absorbed_rows=sum(not row["candidate_active"] for row in paired_rows),
        reference_absorbed_rows=sum(not row["reference_active"] for row in paired_rows),
        next_candidate_absorbed_rows=sum(not row["next_candidate_active"] for row in paired_rows),
        next_reference_absorbed_rows=sum(not row["next_reference_active"] for row in paired_rows),
        diagonal_rows=len(diagonal),
        zero_diagonal_rows=sum(row["target"] == row["n_target"] == [0., 0., 0.] for row in diagonal),
        new_environment_transitions=0, tree_fits=0)
    return roots, paired_rows, dict(source=str(folder.resolve()),
        paths=dict(branch_games=str(branch_path.resolve()), new_rows=str(means_path.resolve())),
        counts=dict(counts), inherited_environment_work=dict(environment), inherited_planning_work=dict(planning),
        paired_crn_contract_matches=True, retained_means_match=True,
        largest_mean_difference=largest_difference, row_weight=PAIR_WEIGHT, n_step=N_STEP, stride=STRIDE,
        seconds=perf_counter() - started)
