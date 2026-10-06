"""Finite shared-feature and unchanged three-head LMS checks; no game sampling."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_paired_advantage_v144 import AdvantagePlanner
from acfqp.science.controlled_predictive_shared_local_advantage_v147 import (
    FEATURE_DEFINITION, SCHEMA, SharedLocalAdvantage)


ROOT = Path(__file__).resolve().parents[1]
MODELS = []
SELECTORS = []
CORNER = [1]+[0]*15
EDGE = [0, 1]+[0]*14


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_shared_local_advantage_v147.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        learner_work=dict(sum((model.counts for model in MODELS), Counter())),
        selector_work=dict(sum((model.counts for model in SELECTORS), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in MODELS), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        native_planner_calls=0,
        scope='Synthetic boards and targets with charged learner updates; mocked planner choices.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def model():
    result = SharedLocalAdvantage()
    MODELS.append(result)
    return result


def test_exact_hand_counted_empty_board_and_one_corner_tile():
    learner = model()
    empty = Counter({0: 4, 11: 8, 22: 4, 33: 4, 44: 8, 407: 4, 418: 8})
    assert learner._features([0]*16) == empty
    corner = empty.copy()
    corner.update({22: -1, 23: 1, 418: -2, 419: 2})
    assert learner._features(CORNER) == corner
    assert sum(corner.values()) == 40
    assert learner.counts == dict(feature_board_reads=32, feature_rank_reads=128,
        feature_occurrences=80, unary_feature_occurrences=32, pair_feature_occurrences=48)
    assert learner.setup_counts == dict(topology_integer_cells=64)
    assert not hasattr(learner, 'patterns')


def test_features_are_invariant_under_all_dihedral_board_symmetries():
    learner = model()
    board = (np.arange(16) % 11).reshape(4, 4)
    expected = learner._features(board.reshape(-1))
    for reflection in (board, np.fliplr(board)):
        for turns in range(4):
            assert learner._features(np.rot90(reflection, turns).reshape(-1)) == expected


def test_boundary_class_and_adjacency_both_distinguish_placements():
    learner = model()
    assert learner._features(CORNER) != learner._features(EDGE)
    adjacent, separated = [0]*16, [0]*16
    adjacent[1] = adjacent[2] = 1
    separated[1] = separated[4] = 1
    first, second = learner._features(adjacent), learner._features(separated)
    assert {i: n for i, n in first.items() if i < 33} == {
        i: n for i, n in second.items() if i < 33}
    assert first != second


def test_signed_counts_normalization_and_shared_preupdate_error():
    learner = model()
    difference = {23: 1, 22: -1, 12: -1, 11: 1, 419: 2, 418: -1,
                  45: -1, 44: 1, 408: -1, 407: 1, 451: -1}
    assert learner._difference(CORNER, EDGE) == difference
    target = [4., -.5, .25]
    update = learner.update(CORNER, EDGE, target)
    assert update['prediction'] == [0., 0., 0.] and update['error'] == target
    assert update['denominator'] == 14 and update['applied']
    for address, multiplicity in difference.items():
        assert learner.weights[address] == pytest.approx(
            [.1*multiplicity*value/14 for value in target])
    assert learner.predict(CORNER, EDGE) == pytest.approx(np.array(target)*.1)
    second = learner.update(CORNER, EDGE, target)
    assert second['error'] == pytest.approx(np.array(target)*.9)
    assert learner.predict(CORNER, EDGE) == pytest.approx(np.array(target)*.19)


def test_symmetry_equal_pair_has_no_identifiable_update():
    learner = model()
    rotated = list(reversed(CORNER))
    update = learner.update(CORNER, rotated, [1., -.5, .5])
    assert update['denominator'] == 0 and not update['applied']
    assert learner.updates == 0 and not learner.weights
    assert learner.counts['unidentifiable_pairs'] == 1


def test_terminal_scope_and_frozen_updates():
    learner = model()
    with pytest.raises(ValueError, match='nonterminal'):
        learner.predict([11]+[0]*15, EDGE)
    learner.freeze()
    with pytest.raises(RuntimeError, match='frozen'):
        learner.update(CORNER, EDGE, [1., 0., 0.])
    assert learner.updates == 0 and not learner.weights


def test_payload_roundtrip_preserves_state_without_mutating_payload():
    learner = model()
    learner.update(CORNER, EDGE, [1., -.5, .25])
    learner.freeze()
    payload = learner.to_payload()
    before = deepcopy(payload)
    restored = SharedLocalAdvantage.from_payload(payload)
    MODELS.append(restored)
    assert payload == before and payload['schema'] == SCHEMA
    assert payload['feature_definition'] == FEATURE_DEFINITION
    assert restored.state() == learner.state() and not restored.counts
    assert restored.setup_counts['loaded_weight_addresses'] == len(learner.weights)
    assert restored.predict(CORNER, EDGE) == pytest.approx(learner.predict(CORNER, EDGE))


def test_unchanged_selector_accepts_shared_model_and_charges_predictions():
    class Planner:
        def __init__(self, action, afterstate):
            self.action, self.afterstate, self.counts = action, afterstate, Counter()

        def choose(self, board, query=None, **kwargs):
            self.counts['mock_choose_calls'] += 1
            return dict(action=self.action, afterstate=self.afterstate, score=0,
                        value=0., tail_value=0., status='ACTIVE', action_values={})

    learner = model()
    learner.update(CORNER, EDGE, [1., 0., 0.])
    learner.freeze()
    selector = AdvantagePlanner(Planner('DOWN', EDGE), Planner('LEFT', CORNER),
                                learner, dict(reward_weight=1., failure_penalty=1., goal_bonus=1.))
    SELECTORS.append(selector)
    choice = selector.choose([0]*16)
    assert choice['action'] == 'LEFT' and choice['selection']['selected_h1']
    assert choice['selection']['estimated_advantage'] == pytest.approx(.1)
    assert selector.counts['learner_feature_occurrences'] == 80
    assert selector.counts['learner_feature_rank_reads'] == 128
    assert selector.counts['baseline_mock_choose_calls'] == 1
    assert selector.counts['candidate_mock_choose_calls'] == 1
