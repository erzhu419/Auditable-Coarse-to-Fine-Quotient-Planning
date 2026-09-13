"""Constraint learning tests distinguish expressibility, fitting and recursion."""
from collections import Counter
import inspect
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from acfqp.science.controlled_predictive_encoder_v7 import (
    ACTIONS, FEATURE_NAMES, TrainingModel, _fit_tree, _leaf,
)
from acfqp.science.controlled_predictive_encoder_v8 import (
    _constraint_tree, _normalize_and_audit, fit_constraint_encoder,
    fit_uncapped_sse_encoder,
)
from acfqp.science.controlled_predictive_encoder_runtime_v8 import compile_encoded
from acfqp.science.controlled_predictive_quotient_v1 import (
    FiniteModel, Outcome, Query, audit_policy, compile_full_state, plan,
)


def _board(rank):
    return (0,) * 5 + (rank,) + (0,) * 10


LOST = (1, 2, 1, 2, 2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1)


def _training(*, contradictory_features=False, delayed=False):
    boards = {0: _board(1), 1: _board(1 if contradictory_features else 2),
              2: _board(1), 3: LOST}
    rows = {}
    for state in (0, 1):
        for action in ACTIONS:
            safe = action == ("UP" if state == 0 else "DOWN")
            rows[state, action] = (Outcome(1, 2 if safe else 3, 0),)
    layers = {0: 1, 1: 1, 2: 0, 3: 0}
    terminal = {0: "ACTIVE", 1: "ACTIVE", 2: "CUTOFF", 3: "LOST"}
    roots = (0, 1)
    if delayed:
        boards |= {4: _board(1), 5: _board(2)}
        layers |= {4: 2, 5: 2}
        terminal |= {4: "ACTIVE", 5: "ACTIVE"}
        rows |= {(state, action): (Outcome(1, state - 4, 0),)
                 for state in (4, 5) for action in ACTIONS}
        roots = (4, 5)
    return TrainingModel("synthetic_empirical", FiniteModel(layers, terminal, rows, roots), boards)


def test_xor_constraint_splits_when_uncapped_sse_has_zero_gain_and_reuses_pure_codes():
    # Both single-axis averages agree. SSE cannot make the first split, while
    # the cannot-merge criterion separates cross-label pairs and reaches purity.
    features = [(float(a), float(b)) + (0.0,) * (len(FEATURE_NAMES) - 2)
                for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))]
    classes = [0, 1, 1, 0]
    targets = [{("UP", "reward"): float(label)} for label in classes]
    sse, _ = _fit_tree(features, targets, max_depth=4, min_leaf=1, work=Counter())
    assert "leaf" in sse
    tree = _constraint_tree(features, classes, Counter())
    assert "leaf" not in tree
    signatures = [tuple(sorted(target.items())) for target in targets]
    report = _normalize_and_audit(tree, features, targets, signatures, classes,
        [(0, i) for i in range(4)], (SimpleNamespace(name="xor"),), ("UP",), Counter())
    assert report["leaves"] == 4 and report["output_codes"] == 2
    assert report["maximum_tree_depth"] == 2
    assert report["pure_leaf_code_reuses"] == 2
    assert report["unresolved_signature_pairs"] == 0
    codes = [_leaf(tree, values, Counter()) for values in features]
    assert codes[0] == codes[3] != codes[1] == codes[2]


def test_identical_feature_conflict_remains_explicit_and_causes_policy_loss():
    data = _training(contradictory_features=True)
    fit = fit_constraint_encoder([data])
    diagnostics = fit.diagnostics
    assert not diagnostics["all_training_predictive_constraints_satisfied"]
    assert not diagnostics["recursive_empirical_equivalence_supported"]
    assert diagnostics["unresolved_signature_pairs"] == 1
    assert diagnostics["identical_feature_conflicting_pairs"] == 1
    assert diagnostics["unresolved_feature_separable_pairs"] == 0
    group = next(group for group in diagnostics["groups"] if group["status"] == "ACTIVE")
    assert group["mixed_leaves"][0]["action_envelopes"]["UP"]["maximum_successor_tv"] == 1
    assert group["mixed_leaves"][0]["action_envelopes"]["UP"]["reward_range"] == 0
    assert group["identical_feature_collision_witness"]["left"]["source_state"] == 0
    compiled = compile_encoded(data.empirical, data.boards, fit.encoder).compiled
    query = Query(failure_penalty=1)
    solution = plan(compiled, query)
    audit = audit_policy(data.empirical, compiled, solution, query)
    full = plan(compile_full_state(data.empirical), query)
    assert full.values[0] == full.values[1] == 0
    assert audit.root_metrics[0]["value"] == -1
    assert audit.root_metrics[1]["value"] == 0


@pytest.mark.parametrize("fitter", [fit_constraint_encoder, fit_uncapped_sse_encoder])
def test_resolved_constraints_preserve_empirical_full_policy_and_bottom_up_targets(fitter):
    data = _training(delayed=True)
    fit = fitter([data])
    assert fit.diagnostics["all_training_predictive_constraints_satisfied"]
    assert fit.diagnostics["recursive_empirical_equivalence_supported"]
    assert fit.encoder.encode(_board(1), 1) != fit.encoder.encode(_board(2), 1)
    assert fit.encoder.encode(_board(1), 2) != fit.encoder.encode(_board(2), 2)
    compiled = compile_encoded(data.empirical, data.boards, fit.encoder).compiled
    full = compile_full_state(data.empirical)
    for query in (Query(), Query(failure_penalty=.37), Query(.5, 2, .25)):
        full_plan = plan(full, query)
        candidate = plan(compiled, query)
        for state in data.empirical.layers:
            assert candidate.values[compiled.state_to_cell[state]] == pytest.approx(full_plan.values[state])
        audit = audit_policy(data.empirical, compiled, candidate, query)
        for root in data.empirical.roots:
            assert audit.root_metrics[root]["value"] == pytest.approx(full_plan.values[root])


def test_lower_unresolved_collision_prevents_global_equivalence_despite_pure_upper_groups():
    data = _training(contradictory_features=True, delayed=True)
    fit = fit_constraint_encoder([data])
    upper = [group for group in fit.diagnostics["groups"] if group["horizon"] == 2]
    assert upper and all(group["local_predictive_constraints_satisfied"] for group in upper)
    assert all(group["unresolved_lower_horizon_group_present"] for group in upper)
    assert not fit.diagnostics["recursive_empirical_equivalence_supported"]
    assert fit.encoder.encode(_board(1), 2) == fit.encoder.encode(_board(2), 2)


def test_payload_contains_rules_and_fit_accepts_only_declared_empirical_training():
    data = _training()
    with patch("acfqp.domains.standard_2048.step_v1", side_effect=AssertionError("true transition enumerated")):
        fit = fit_constraint_encoder([data])
        fit_uncapped_sse_encoder([data])
    assert tuple(inspect.signature(fit_constraint_encoder).parameters) == ("training",)
    assert tuple(inspect.signature(fit_uncapped_sse_encoder).parameters) == ("training",)
    payload = json.loads(json.dumps(fit.encoder.to_payload()))
    assert set(payload) == {"schema", "feature_names", "trees", "unseen_active_group_leaf"}
    assert all(set(group) == {"horizon", "status", "legal", "tree"} for group in payload["trees"])
    assert fit.diagnostics["scientific_signature_tolerance"] == 0
    assert fit.diagnostics["work_counts"]["full_empirical_signatures_constructed"] == 2
