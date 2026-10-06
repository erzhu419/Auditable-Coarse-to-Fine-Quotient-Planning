"""One query-selected, committed fragment followed permanently by H2.

The selector predicts complete paired terminal consequences of each fragment,
including its prescribed return to H2. Its zero H2 reference never enters a fit.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_lifelong_v77 import (
    FEATURE_NAMES as BOARD_FEATURE_NAMES, _predict, features,
)
from acfqp.science import controlled_predictive_lifelong_planner_v77 as planner
from acfqp.science.controlled_predictive_policy_advantage_v81 import Policy, QUERIES


OPTIONS = ("H2", "SPACE_1", "SNAKE_1", "SPACE_4", "SNAKE_4")
ONE_STEP_OPTIONS = OPTIONS[:3]
FEATURE_NAMES = (tuple("state_" + name for name in BOARD_FEATURE_NAMES[:-1])
                 + ("primitive_SPACE", "primitive_SNAKE", "duration_fraction"))
TREE_PARAMETERS = dict(max_depth=3, min_samples_leaf=8, random_state=8301)
TRIGGER_EMPTY_CELLS = 6


def _merge(work, counts):
    if work is not None:
        for name, value in counts.items():
            work[name] = work.get(name, 0) + value


def _utility(target, query):
    return (query["reward_weight"] * target[0]
            - query["failure_penalty"] * target[1]
            + query["goal_bonus"] * target[2])


def fragment_features(board, option, work=None):
    """39 observed-board and intervention features, without model sampling."""
    if option not in OPTIONS[1:]:
        raise ValueError("fragment features require a non-H2 option")
    primitive, duration = option.split("_")
    _merge(work, dict(fragment_feature_rows=1, board_feature_rows=1))
    return (features(board, 30)[:-1]
            + (float(primitive == "SPACE"), float(primitive == "SNAKE"), int(duration) / 4))


def _array(rows, counts):
    return np.asarray([fragment_features(row["board"], row["option"], counts)
                       for row in rows], dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


def _fit(x, y, counts):
    from sklearn.tree import DecisionTreeRegressor

    tree = DecisionTreeRegressor(**TREE_PARAMETERS).fit(x, y).tree_
    counts["tree_fits"] += 1
    counts["fit_rows"] += len(x)
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


class Selector:
    """Query-specific joint R/F/S trees, shared across the four interventions."""

    def __init__(self, trees, checkpoint):
        self.trees = trees
        self.checkpoint = checkpoint

    @classmethod
    def fit(cls, rows, checkpoint):
        started = perf_counter()
        records = list(rows)
        alternatives = [row for row in records if row["option"] != "H2"]
        counts = Counter(metadata_rows_read=len(records))
        trees, query_logs = {}, {}
        for query_name in QUERIES:
            selected = [row for row in alternatives if row["query"] == query_name]
            training = [row for row in selected if row["episode"] % 5 != 4]
            heldout = [row for row in selected if row["episode"] % 5 == 4]
            if not training:
                raise ValueError(f"checkpoint {checkpoint} has no training fragments for {query_name}")
            counts["training_rows_read"] += len(training)
            x = _array(training, counts)
            y = np.asarray([row["target"] for row in training], dtype=float).reshape((-1, 3))
            tree = trees[query_name] = _fit(x, y, counts)
            mse = None
            if heldout:
                counts["validation_rows_read"] += len(heldout)
                vx = _array(heldout, counts)
                vy = np.asarray([row["target"] for row in heldout], dtype=float)
                error = _predict(tree, vx, counts) - vy
                mse = np.mean(error * error, axis=0).tolist()
            query_logs[query_name] = dict(training_rows=len(training), heldout_rows=len(heldout),
                nodes=len(tree["left"]), leaves=sum(node < 0 for node in tree["left"]),
                training_target_mean=np.mean(y, axis=0).tolist(), heldout_mse_components=mse)
        return cls(trees, checkpoint), dict(checkpoint=checkpoint, input_records=len(records),
            reference_records_excluded=len(records) - len(alternatives),
            training_records=sum(row["episode"] % 5 != 4 for row in alternatives),
            heldout_records=sum(row["episode"] % 5 == 4 for row in alternatives),
            queries=query_logs, counts=dict(counts), seconds=perf_counter() - started)

    def select(self, board, query, allowed=None, work=None):
        allowed = OPTIONS if allowed is None else tuple(allowed)
        if "H2" not in allowed or any(option not in OPTIONS for option in allowed):
            raise ValueError("allowed options must include H2 and use the frozen option set")
        alternatives = [option for option in OPTIONS[1:] if option in allowed]
        counts = Counter(selector_decisions=1)
        predictions = {"H2": dict(target=[0.0, 0.0, 0.0], value=0.0)}
        chosen, best = "H2", 0.0
        if alternatives:
            x = _array([dict(board=board, option=option) for option in alternatives], counts)
            vectors = _predict(self.trees[query], x, counts)
            counts["fragment_prediction_rows"] += len(alternatives)
            for option, vector in zip(alternatives, vectors):
                target = vector.tolist()
                value = float(_utility(target, QUERIES[query]))
                predictions[option] = dict(target=target, value=value)
                if value > best:
                    chosen, best = option, value
        _merge(work, counts)
        return dict(option=chosen, predicted_advantage=predictions[chosen]["target"],
                    value=best, predictions=predictions)

    def to_payload(self):
        return dict(schema="acfqp.terminal_fragments.v83", checkpoint=self.checkpoint,
            options=list(OPTIONS), queries=deepcopy(QUERIES), feature_names=list(FEATURE_NAMES),
            tree_parameters=dict(TREE_PARAMETERS), trees=deepcopy(self.trees))

    @classmethod
    def from_payload(cls, payload):
        return cls(deepcopy(payload["trees"]), payload["checkpoint"])


class FragmentController:
    """Select once at the trigger, execute the commitment, then return to H2."""

    def __init__(self, selector, query, rule, rng, mode="FRAGMENT", immediate=False,
                 fixed_option=None):
        if mode not in ("H2_ONLY", "ONE_STEP", "FRAGMENT", "FIXED_SPACE4"):
            raise ValueError(f"unknown fragment control mode {mode}")
        if fixed_option is not None and fixed_option not in OPTIONS:
            raise ValueError(f"unknown fixed option {fixed_option}")
        if immediate and fixed_option is None:
            raise ValueError("immediate branch control requires a fixed option")
        self.selector, self.query, self.rule, self.rng = selector, query, rule, rng
        self.mode, self.immediate, self.fixed_option = mode, immediate, fixed_option
        self.work = Counter()
        self.events = []
        self.fragment_actions = 0
        self.initiation_step = None
        self.selected_option = None
        self.remaining_actions = 0
        self.finished_fragment = False
        self._h2 = Policy.base()

    def choose(self, board, step):
        status, _ = self.rule.classify(tuple(board), self.work)
        if status != "ACTIVE":
            return None
        self.work["controller_active_decisions"] += 1
        if (self.mode != "H2_ONLY" and self.selected_option is None
                and (self.immediate or tuple(board).count(0) <= TRIGGER_EMPTY_CELLS)):
            if self.fixed_option is not None or self.mode == "FIXED_SPACE4":
                option = self.fixed_option or "SPACE_4"
                selection = dict(option=option, predicted_advantage=None, value=None,
                                 predictions={})
            else:
                allowed = ONE_STEP_OPTIONS if self.mode == "ONE_STEP" else OPTIONS
                selection = self.selector.select(board, self.query, allowed, self.work)
                option = selection["option"]
            self.selected_option = option
            self.initiation_step = step
            self.remaining_actions = 0 if option == "H2" else int(option.split("_")[1])
            self.finished_fragment = self.remaining_actions == 0
            self.events.append(dict(step=step, board=list(board), **selection))
            self.work["fragment_selections"] += 1
            self.work["fragments_initiated"] += option != "H2"
        if self.remaining_actions:
            primitive = self.selected_option.split("_")[0]
            action = planner.policy_action(board, primitive, self.rule, self.work)
            for _ in range(4):
                self.rng.random()
            self.work["model_uniform_draws"] += 4
            self.work["dummy_model_uniform_draws"] += 4
            self.work["fragment_active_actions"] += 1
            self.fragment_actions += 1
            self.remaining_actions -= 1
            self.finished_fragment = self.remaining_actions == 0
            return action
        self.work["h2_active_actions"] += 1
        return self._h2.choose(board, self.query, self.rule, self.rng, self.work)["action"]
