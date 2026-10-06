"""Query planning with policy-conditioned, jointly evaluated consequences.

The learned model predicts continuation reward, failure, and success for each
fixed policy. A decision always selects a complete policy vector. These are
finite-horizon estimates for receding-horizon control, not risk certificates.
"""
from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import sys


POLICIES = ("GREEDY", "SPACE", "SNAKE")
HORIZON = 32
SNAKE_CELLS = tuple(4 * row + col for row in range(4)
                    for col in (range(4) if row % 2 == 0 else range(3, -1, -1)))


def _moves(board, rule, work):
    status, moves = rule.classify(tuple(board), work)
    work["legal_swipes"] += len(moves)
    return status, sorted(moves)


def policy_action(board, policy, rule, work=None):
    """Choose a deterministic fixed continuation action; ties use action names."""
    if policy not in POLICIES:
        raise ValueError(f"unknown continuation policy {policy}")
    counts = Counter()
    _, moves = _moves(board, rule, counts)
    choices = []
    for action, afterstate, score in moves:
        empty = afterstate.count(0)
        if policy == "GREEDY":
            key = (score, empty)
        elif policy == "SPACE":
            key = (empty, score)
        else:
            key = (sum((2 ** afterstate[cell] if afterstate[cell] else 0) * 0.8 ** pos
                       for pos, cell in enumerate(SNAKE_CELLS)), score)
        choices.append((action, key))
    if work is not None:
        for key, value in counts.items():
            work[key] = work.get(key, 0) + value
    return max(choices, key=lambda item: item[1])[0] if choices else None


def _vector(reward=0.0, failure=0.0, success=0.0):
    return dict(reward=float(reward), failure=float(failure), success=float(success))


def _value(metrics, query):
    return (float(query.get("reward_weight", 1.0)) * metrics["reward"]
            - float(query.get("failure_penalty", 0.0)) * metrics["failure"]
            + float(query.get("goal_bonus", 0.0)) * metrics["success"])


def _entry(action, metrics, query, policy=None, branches=None):
    return dict(action=action, metrics=metrics, value=_value(metrics, query),
                policy=policy, branches=[] if branches is None else branches)


def _spawn(afterstate, draws, rule, work):
    empty = [cell for cell, rank in enumerate(afterstate) if rank == 0]
    if rule.spawn_location == "first":
        empty = empty[:1]
    elif rule.spawn_location == "last":
        empty = empty[-1:]
    cell = empty[min(int(draws[0] * len(empty)), len(empty) - 1)]
    cumulative = 0.0
    rank = rule.spawn_distribution[-1][0]
    for candidate, probability in rule.spawn_distribution:
        cumulative += float(probability)
        if draws[1] < cumulative:
            rank = candidate
            break
    child = list(afterstate)
    child[cell] = rank
    work["model_spawn_samples"] += 1
    return tuple(child)


def _compiler(rule):
    name = "acfqp_v77_effect_baseline"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name,
            Path(__file__).with_name("controlled_predictive_effect_contract_v74.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name].EffectCompiler(rule)


def choose(board, query, knowledge, rule, rng, depth=2, work=None):
    """Return the best complete R/F/S estimate and its executable policy choices.

    All active calls consume two common (cell, rank) random pairs, including
    depth-one calls. Every root action receives those same pairs. The knowledge
    contract is predict_many(afterstates, remaining_actions), shape (N, 3, 3),
    with axes POLICIES and (reward, failure, success). Its reward excludes the
    merge already performed to produce the afterstate.
    """
    if depth not in (1, 2):
        raise ValueError("V77 supports decision depth one or two")
    if knowledge is None and depth != 2:
        raise ValueError("The short-horizon baseline uses depth two")
    counts = Counter()
    status, root_moves = _moves(board, rule, counts)

    def finish(result):
        result["counts"] = dict(counts)
        if work is not None:
            for key, value in counts.items():
                work[key] = work.get(key, 0) + value
        return result

    if status != "ACTIVE":
        result = _entry(None, _vector(failure=status == "LOST", success=status == "WON"), query)
        result["action_values"] = {}
        return finish(result)
    draws = tuple((float(rng.random()), float(rng.random())) for _ in range(2))
    counts["model_uniform_draws"] += 4
    leaves = []
    roots = []
    compiler = _compiler(rule) if knowledge is None else None

    def leaf(action, afterstate, score):
        item = dict(action=action, afterstate=afterstate, score=score)
        if max(afterstate) >= rule.goal_rank:
            item["terminal"] = _vector(success=1)
        else:
            item["prediction_index"] = len(leaves)
            leaves.append(afterstate)
        return item

    for action, afterstate, score in root_moves:
        root = dict(action=action, score=score, branches=[])
        if depth == 1 or max(afterstate) >= rule.goal_rank:
            root["direct"] = leaf(action, afterstate, score)
        else:
            for sample, pair in enumerate(draws):
                child = _spawn(afterstate, pair, rule, counts)
                branch = dict(sample=sample, board=child, leaves=[])
                if compiler is not None:
                    contract = compiler.observation_contract(child)
                    counts["h2_cutoff_contracts"] += 1
                    counts["legal_swipes"] += len(contract)
                    branch["ready"] = []
                    for candidate, score2, mass in sorted(contract):
                        probabilities = dict(mass)
                        vector = _vector(score2 / 2048, probabilities.get("LOST", 0),
                                         probabilities.get("WON", 0))
                        branch["ready"].append(_entry(candidate, vector, query))
                    if not contract:
                        won = max(child) >= rule.goal_rank
                        branch["terminal"] = _vector(failure=not won, success=won)
                    root["branches"].append(branch)
                    continue
                child_status, moves = _moves(child, rule, counts)
                if child_status != "ACTIVE":
                    branch["terminal"] = _vector(failure=child_status == "LOST",
                                                  success=child_status == "WON")
                else:
                    branch["leaves"] = [leaf(a, moved, gained) for a, moved, gained in moves]
                root["branches"].append(branch)
        roots.append(root)

    if compiler is not None:
        for key, value in compiler.work.items():
            counts["h2_contract_" + key] += value

    predictions = None
    if leaves:
        predictions = knowledge.predict_many(leaves, HORIZON - depth)
        counts["knowledge_batch_calls"] += 1
        counts["predicted_afterstates"] += len(leaves)
        counts["policy_vectors"] += len(leaves) * len(POLICIES)

    def resolve(item):
        if "terminal" in item:
            vector = dict(item["terminal"])
            vector["reward"] += item["score"] / 2048
            return _entry(item["action"], vector, query)
        choices = []
        rows = predictions[item["prediction_index"]]
        for index, policy in sorted(enumerate(POLICIES), key=lambda pair: pair[1]):
            reward, failure, success = rows[index]
            vector = _vector(float(reward) + item["score"] / 2048, failure, success)
            choices.append(_entry(item["action"], vector, query, policy))
        return max(choices, key=lambda item: item["value"])

    candidates = []
    for root in roots:
        if "direct" in root:
            candidates.append(resolve(root["direct"]))
            continue
        branches = []
        for branch in root["branches"]:
            if "terminal" in branch:
                selected = _entry(None, branch["terminal"], query)
            elif "ready" in branch:
                selected = max(branch["ready"], key=lambda item: item["value"])
            else:
                selected = max((resolve(item) for item in branch["leaves"]),
                               key=lambda item: item["value"])
            selected.update(sample=branch["sample"], board=list(branch["board"]))
            branches.append(selected)
        vector = {metric: sum(item["metrics"][metric] for item in branches) / len(branches)
                  for metric in ("reward", "failure", "success")}
        vector["reward"] += root["score"] / 2048
        candidates.append(_entry(root["action"], vector, query, branches=branches))
    selected = dict(max(candidates, key=lambda item: item["value"]))
    selected["action_values"] = {item["action"]: item for item in candidates}
    return finish(selected)
