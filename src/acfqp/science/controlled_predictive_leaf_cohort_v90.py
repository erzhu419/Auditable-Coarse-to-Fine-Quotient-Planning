"""Freeze every V89 newly enabled intervention and its complete training leaf."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_evidence_fragments_v88 import EvidenceSelector
from acfqp.science.controlled_predictive_joint_fragments_v84 import QUERIES, _array, _utility
from acfqp.science.controlled_predictive_lifelong_v77 import _apply


CONTRAST = "EVIDENCE_SUPPORTED_minus_BALANCED_SUPPORTED"
METHODS = ("H2_ONLY", "EVIDENCE_SUPPORTED", "BALANCED_SUPPORTED")
EXPECTED_ROSTER = {(0, "reward", replica) for replica in (1, 3, 5, 8)} | {
    (2, "reward", replica) for replica in (1, 4, 14)}
EXPECTED_TRAINING = {0: [1, 6], 2: [0, 3, 8]}


def _read_rows(path):
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle]


def _history(game):
    return [(step["board"], step["action"], step["next_board"]) for step in game["episode"]["steps"]]


def _require(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def _leaf(selector, query, board, counts):
    return int(_apply(selector.trees[query], _array([dict(board=board)], counts), counts)[0])


def build_cohort(source: Path):
    """Read the frozen V89 cohort; outcomes annotate it and never select roots.

    Every same-leaf original training root supplies one control. Controls shared
    by several targets are represented once, with reuse explicit in groups.
    """
    started = perf_counter()
    source = Path(source)
    work = Counter()
    targets, controls, groups, roster = [], [], [], set()
    for life in range(3):
        folder = source / f"life_{life}"
        run = json.loads((folder / "run.json").read_text())
        work["run_files_read"] += 1
        enabled = [row for row in run["evaluation"]["gate_changes"][CONTRAST]
                   if row["category"] == "enabled"]
        if not enabled:
            continue
        selectors = {method: EvidenceSelector.from_payload(json.loads(
            (folder / ("evidence_selector.json" if method == "EVIDENCE_SUPPORTED"
                       else "balanced_selector.json")).read_text())) for method in METHODS[1:]}
        work["selector_files_read"] += 2
        base = _read_rows(folder / "base_paired_roots.jsonl.gz")
        work["base_roots_read"] += len(base)
        training = [root for root in base if root["episode"] % 5 != 4]
        work["heldout_roots_excluded"] += len(base) - len(training)
        selected_keys = {(row["query"], row["seed"]) for row in enabled}
        raw = {}
        for game in _read_rows(folder / "evaluation_games.jsonl.gz"):
            work["retained_games_read"] += 1
            if (game["query"], game["episode"]["seed"]) not in selected_keys or game["method"] not in METHODS:
                continue
            key = game["method"], game["query"], game["episode"]["seed"]
            _require(key not in raw, "duplicate retained V89 game")
            raw[key] = game
        grouped = {}
        for row in sorted(enabled, key=lambda row: (row["query"], row["replica"])):
            query, seed, replica = row["query"], row["seed"], row["replica"]
            identity = life, query, replica
            _require(identity not in roster, "duplicate enabled V89 event")
            _require(identity in EXPECTED_ROSTER, "enabled V89 event is outside the frozen cohort")
            roster.add(identity)
            _require(seed == 8990000 + life * 100 + replica, "V89 event seed disagrees with lifecycle and replica")
            _require(query == "reward" and row["old_option"] == "H2" and row["new_option"] == "SNAKE_4",
                     "V89 enabled event differs from the frozen candidate cohort")
            games = {method: raw[method, query, seed] for method in METHODS}
            h2, current, previous = (games[method] for method in METHODS)
            for method in METHODS[1:]:
                _require(len(games[method]["controller_events"]) == 1, "expected one retained intervention event")
            event, old_event = current["controller_events"][0], previous["controller_events"][0]
            board, step = event["board"], event["step"]
            for method in METHODS[1:]:
                stored = games[method]["controller_events"][0]
                fresh = selectors[method].select(board, query, work=work)
                _require(all(stored[key] == fresh[key] for key in
                    ("option", "predicted_advantage", "value", "predictions", "mode")),
                    "retained V89 event disagrees with its deployed selector")
            _require(event["option"] == row["new_option"] and old_event["option"] == row["old_option"],
                     "V89 gate table disagrees with retained event choices")
            _require(old_event["step"] == step and old_event["board"] == board,
                     "V89 methods do not share the trigger state")
            _require(all(game["episode"]["steps"][step]["board"] == board for game in games.values()),
                     "retained controller event board differs from its episode")
            _require(_history(current)[:step] == _history(previous)[:step] == _history(h2)[:step],
                     "V89 pretrigger histories differ")
            _require(_history(previous) == _history(h2), "disabled V89 comparison does not execute H2")
            selector = selectors["EVIDENCE_SUPPORTED"]
            leaf = _leaf(selector, query, board, work)
            _require(leaf == 4, "enabled V89 event moved outside its frozen leaf")
            option = event["option"]
            target_id = f"life_{life}_target_{seed}_{query}"
            current_score, h2_score = (game["episode"]["return_score"] for game in (current, h2))
            q = QUERIES[query]
            delta = [(current_score - h2_score) / 2048,
                float(current["episode"]["status"] == "LOST") - float(h2["episode"]["status"] == "LOST"),
                float(current["episode"]["status"] == "WON") - float(h2["episode"]["status"] == "WON")]
            targets.append(dict(id=target_id, kind="target", life=life, query=query, leaf=leaf,
                option=option, board=list(board), seed=seed, replica=replica, trigger_step=step,
                v89_score_delta=current_score - h2_score, v89_utility_delta=float(_utility(delta, q))))
            group_id = f"life_{life}_{query}_leaf_{leaf}"
            if group_id not in grouped:
                prediction = event["predictions"][option]
                group = dict(id=group_id, life=life, query=query, leaf=leaf, option=option,
                    target_ids=[], training_ids=[], predicted_target=list(prediction["target"]),
                    predicted_utility=prediction["value"], positive_fraction=prediction["positive_fraction"],
                    evidence_fractions=dict(prediction["evidence_fractions"]))
                matched = [root for root in training if root["query"] == query and
                           _leaf(selector, query, root["board"], work) == leaf]
                matched.sort(key=lambda root: root["episode"])
                _require([root["episode"] for root in matched] == EXPECTED_TRAINING[life],
                         "same-leaf training membership differs from frozen V89 cohort")
                for root in matched:
                    control_id = f"life_{life}_training_{root['episode']}_{query}"
                    controls.append(dict(id=control_id, kind="training", life=life, query=query,
                        leaf=leaf, option=option, board=list(root["board"]), episode=root["episode"],
                        n_replicas=root["n_replicas"]))
                    group["training_ids"].append(control_id)
                grouped[group_id] = group
            grouped[group_id]["target_ids"].append(target_id)
        groups.extend(grouped.values())
    _require(roster == EXPECTED_ROSTER, "enabled V89 cohort must retain all seven frozen events")
    _require(len({tuple(root["board"]) for root in targets + controls}) == len(targets) + len(controls),
             "frozen target or training boards overlap")
    work.update(target_roots=len(targets), unique_training_controls=len(controls), groups=len(groups),
                environment_transitions=0, tree_fits=0)
    checks = dict(frozen_roster_matches=True, heldout_excluded=True, all_same_leaf_training_roots_retained=True,
        stored_events_match_selectors=True, gate_choices_match=True, shared_trigger_matches=True,
        pretrigger_histories_match=True, balanced_histories_match_h2=True,
        controls_reused_once=True, target_and_control_boards_distinct=True)
    return dict(schema="acfqp.leaf_cohort.v90", source=str(source.resolve()), contrast=CONTRAST,
                targets=targets, controls=controls, groups=groups, checks=checks,
                mapping_work=dict(work), seconds=perf_counter() - started)
