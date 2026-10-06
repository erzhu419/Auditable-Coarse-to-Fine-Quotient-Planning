"""Synthetic controlled rows: learned predicates, exact Bellman, and bounds."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction

import pytest

from acfqp.science import controlled_predictive_deep_transfer_v200 as core


def state(board, legal, status="ACTIVE"):
    return dict(board=list(board), status=status, legal=list(legal))


def board(first, second=1, third=1):
    return [first, second, third]+[0]*13


def terminals():
    return [state([11]+[0]*15, [], "WON"), state([1, 2]*8, [], "LOST")]


def leaves(tree, path=()):
    if "cell" in tree:
        return [(path, tree)]
    return leaves(tree["left"], path+(0,))+leaves(tree["right"], path+(1,))


def root(model, h, mask):
    return next(item["tree"] for item in model["trees"][str(h)] if item["mask"] == list(mask))


def successor_source():
    states = [state(board(1 if i < 4 else 3, i+1), ["LEFT"]) for i in range(8)]
    states += [state(board(1 if i < 4 else 3, i+10), ["UP"]) for i in range(8)]
    states += terminals()
    rows = [[i, "LEFT", [[1, 1, 8+i, 0, 1]]] for i in range(8)]
    rows += [[8+i, "UP", [[1, 1, 16 if i < 4 else 17, 0, 1]]] for i in range(8)]
    return dict(states=states, rows=rows, controlled=list(range(16)))


def mixture_source():
    states = [state(board(1, 2), ["UP"]), state(board(2, 1), ["UP"]),
              state(board(3), ["DOWN", "LEFT"])] + terminals()
    rows = [[0, "UP", [[1, 2, 2, 1, 2], [1, 2, 4, 1, 6]]],
            [1, "UP", [[1, 1, 2, 1, 2]]],
            [2, "DOWN", [[1, 1, 3, 1, 3]]],
            [2, "LEFT", [[1, 1, 4, 3, 2]]]]
    return dict(states=states, rows=rows, controlled=[0, 1, 2])


def test_successor_cells_induce_new_predicate_and_route_unseen_board():
    source = successor_source()
    model = core.fit_model(source)
    # No immediate reward or h=0 ACTIVE labels distinguish these root boards.
    assert "cell" in root(model, 1, ["LEFT"])
    learned = root(model, 2, ["LEFT"])
    assert (learned["feature"], learned["threshold"]) == (0, 1)
    low = core.encode(model, source["states"][0]["board"], 2, "ACTIVE", ["LEFT"])
    high = core.encode(model, source["states"][4]["board"], 2, "ACTIVE", ["LEFT"])
    assert low != high
    unseen = board(2, 9, 7)
    assert unseen not in [item["board"] for item in source["states"]]
    assert core.encode(model, unseen, 2, "ACTIVE", ["LEFT"]) == high
    assert all(model["fit_counts"][f"h{h}_fit_states"] == 16 for h in core.HORIZONS)
    features = core.board_features([1, 1, 0, 2]+[0]*12)
    assert len(features) == 42 and features[16:19] == (1, 0, 0)
    assert features[28:40] == (0,)*12 and features[40:] == (13, 2)


def test_uniform_rational_rows_and_query_own_joint_bellman():
    source = mixture_source()
    model = core.fit_model(source, "COARSE")
    cell = core.encode(model, source["states"][0]["board"], 2, "ACTIVE", ["UP"])
    next_cell = core.encode(model, source["states"][2]["board"], 1, "ACTIVE", ["DOWN", "LEFT"])
    row = next(item for item in model["rows"] if item[:2] == [cell, "UP"])
    assert row[2] == [[1, 4, 1, 5, 12], [3, 4, next_cell, 5, 12]]
    queries = {
        "safe": dict(reward_weight=1, failure_penalty=2, goal_bonus=0),
        "reward": dict(reward_weight=1, failure_penalty=0, goal_bonus=0),
    }
    counts = Counter()
    plans = core.plan_model(model, queries, counts)
    assert plans["safe"]["policy"][next_cell] == "DOWN"
    assert plans["reward"]["policy"][next_cell] == "LEFT"
    assert plans["safe"]["values"][cell] == [Fraction(2, 3), Fraction(1, 4), Fraction(3, 4)]
    assert plans["reward"]["values"][cell] == [Fraction(37, 24), Fraction(1), Fraction(0)]
    assert core.action_values(model, plans["safe"], cell)["UP"] == plans["safe"]["values"][cell]
    assert plans["safe"]["values"][0] == [Fraction(0), Fraction(0), Fraction(1)]
    assert plans["safe"]["values"][1] == [Fraction(0), Fraction(1), Fraction(0)]
    assert counts["planning_compile_calls"] == 1 and counts["planning_component_accumulations"] > 0
    assert model["fit_counts"]["compiler_member_rows"] == 16
    near = {"DOWN": [Fraction(1), 0, 0], "LEFT": [Fraction(1)+core.UTILITY_EPS, 0, 0]}
    assert core.choose_action(near, queries["reward"]) == "DOWN"
    near["LEFT"][0] += core.UTILITY_EPS
    assert core.choose_action(near, queries["reward"]) == "LEFT"


def reward_source(masks, size, reward):
    states, rows = [], []
    for group, mask in enumerate(masks):
        for index in range(size):
            sid = len(states)
            states.append(state(board(index, index, group+1), mask))
            value = Fraction(reward(index))
            rows.append([sid, mask[0], [[1, 1, size*len(masks), value.numerator, value.denominator]]])
    states += terminals()
    return dict(states=states, rows=rows, controlled=list(range(size*len(masks))))


def test_mask_global_leaf_depth_minchild_and_feature_ties():
    # Equal single-action label geometry: after 24 leaves, the last eight tied
    # splits are allocated to the lexically first mask and then its paths.
    masks = [["LEFT"], ["RIGHT"], ["UP"]]
    source = reward_source(masks, 64, lambda i: i)
    model = core.fit_model(source)
    for h in core.HORIZONS:
        layer = model["trees"][str(h)]
        assert [len(leaves(item["tree"])) for item in layer] == [16, 8, 8]
        assert sum(len(leaves(item["tree"])) for item in layer) == 32
        for item in layer:
            assert item["tree"]["feature"] == 0  # Features 0 and 1 are tied.
            for path, leaf in leaves(item["tree"]):
                assert len(path) <= 6 and len(leaf["members"]) >= 4
                assert all(source["states"][sid]["legal"] == item["mask"] for sid in leaf["members"])
    deep = core.fit_model(reward_source([["LEFT"]], 64, lambda i: 4**(i//4)))
    assert max(len(path) for path, _ in leaves(root(deep, 1, ["LEFT"]))) == 6
    small = core.fit_model(reward_source([["LEFT"]], 7, lambda i: i))
    assert all("cell" in root(small, h, ["LEFT"]) for h in core.HORIZONS)
    coarse = core.fit_model(source, "COARSE")
    assert all(len(coarse["trees"][str(h)]) == 3 and
               all("cell" in item["tree"] for item in coarse["trees"][str(h)]) for h in core.HORIZONS)


def test_unknown_target_mask_and_source_mask_closure():
    source = mixture_source()
    model = core.fit_model(source)
    frozen = deepcopy(model)
    counts = Counter()
    assert core.encode(model, board(4), 4, "ACTIVE", ["RIGHT"], counts) is None
    assert core.encode(model, board(4), 0, "ACTIVE", ["RIGHT"], counts) == 2
    assert core.encode(model, board(11), 4, "WON", [], counts) == 0
    assert core.encode(model, board(4), 4, "LOST", [], counts) == 1
    assert counts["feature_calls"] == 1 and counts["encoding_calls"] == 4
    assert model == frozen
    incomplete = deepcopy(source)
    incomplete["controlled"] = [0, 1]
    with pytest.raises(ValueError, match="SOURCE successor legal mask has no controlled state"):
        core.fit_model(incomplete)
