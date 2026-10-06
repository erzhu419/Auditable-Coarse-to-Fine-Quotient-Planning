"""Finite exact signed features, normalized updates, and charged action gating."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.controlled_predictive_paired_advantage_v144 import AdvantagePlanner, PairedAdvantage

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT/'reports/v144_runtime_tmp/core_checks'
MODELS, SELECTORS = [], []
BOARD_A = [1, 1]+[0]*14
BOARD_B = [2, 0]+[0]*14
RISK1 = dict(reward_weight=1., failure_penalty=1., goal_bonus=1.)
RISK8 = dict(reward_weight=1., failure_penalty=8., goal_bonus=1.)


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_paired_advantage_v144.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        learner_work=dict(sum((model.counts for model in MODELS), Counter())),
        selector_work=dict(sum((model.counts for model in SELECTORS), Counter())),
        setup_counts=dict(sum((model.setup_counts for model in MODELS), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Static exact tuple features and synthetic three-component targets; both planner interfaces mocked.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def model():
    result = PairedAdvantage(); MODELS.append(result); return result


def explicit_features(board):
    patterns = ((0, 1, 2, 4, 5, 6), (4, 5, 6, 8, 9, 10),
                (0, 1, 2, 3, 4, 5), (4, 5, 6, 7, 8, 9))
    features = Counter()
    for table, cells in enumerate(patterns):
        for reflection in range(2):
            for rotation in range(4):
                address = 0
                for cell in cells:
                    row, column = divmod(cell, 4)
                    column = 3-column if reflection else column
                    for _ in range(rotation):
                        row, column = column, 3-row
                    address = address*11+board[4*row+column]
                features[table*11**6+address] += 1
    return features


def choice(action, board, score=0, value=10.):
    entry = dict(afterstate=list(board), score=score, value=value, tail_value=value-score/2048.)
    return dict(action=action, **entry, status='ACTIVE', action_values={action: dict(entry)})


class PlannerStub:
    def __init__(self, answer, work):
        self.answer, self.work, self.counts, self.calls = answer, Counter(work), Counter(), []

    def choose(self, board, query=None, **kwargs):
        self.calls.append(dict(board=list(board), query=deepcopy(query), **kwargs))
        self.counts.update(self.work)
        return deepcopy(self.answer)


def selector(learned, query=RISK1, baseline=None, candidate=None):
    baseline = choice('DOWN', BOARD_B) if baseline is None else baseline
    candidate = choice('LEFT', BOARD_A, value=-999.) if candidate is None else candidate
    teacher = PlannerStub(baseline, dict(choose_calls=1, learned_swipe_calls=20, value_predictions=16))
    rival = PlannerStub(candidate, dict(choose_calls=1, learned_swipe_calls=40, model_sampled_transitions=8))
    learned.freeze(); result = AdvantagePlanner(teacher, rival, learned, query)
    SELECTORS.append(result); return result


def test_normalized_update_preserves_signed_multiplicity_and_three_component_error():
    learned = model(); a, b = explicit_features(BOARD_A), explicit_features(BOARD_B)
    x = {i: a[i]-b[i] for i in a.keys() | b.keys() if a[i] != b[i]}
    assert any(abs(value) > 1 for value in x.values())
    assert any(value < 0 for value in x.values())
    target = [4., -.5, .5]; denominator = sum(value**2 for value in x.values())
    result = learned.update(BOARD_A, BOARD_B, target)
    assert result['prediction'] == [0., 0., 0.]
    assert result['error'] == target and result['denominator'] == denominator
    assert set(learned.weights) == set(x)
    for index, multiplicity in x.items():
        assert learned.weights[index] == pytest.approx([.1*multiplicity*y/denominator for y in target])
    assert learned.predict(BOARD_A, BOARD_B) == pytest.approx(np.array(target)*.1)
    second = learned.update(BOARD_A, BOARD_B, target)
    assert second['error'] == pytest.approx(np.array(target)*.9)
    assert learned.predict(BOARD_A, BOARD_B) == pytest.approx(np.array(target)*.19)


def test_identical_features_cancel_without_parameter_updates():
    learned = model()
    result = learned.update(BOARD_A, BOARD_A, [3., -.5, .5])
    assert result['denominator'] == 0 and not result['applied']
    assert learned.weights == {} and learned.updates == 0
    assert learned.predict(BOARD_A, BOARD_A) == [0., 0., 0.]
    assert learned.counts['pair_nonzero_difference_addresses'] == 0
    assert learned.counts['feature_occurrences'] == 128


def test_shared_features_cancel_and_reversing_pair_changes_all_signs():
    learned = model(); learned.update(BOARD_A, BOARD_B, [-2., .25, -.25])
    forward = learned.predict(BOARD_A, BOARD_B)
    assert learned.predict(BOARD_B, BOARD_A) == pytest.approx([-value for value in forward])
    assert forward[0] < 0 and forward[1] > 0 and forward[2] < 0
    a, b = explicit_features(BOARD_A), explicit_features(BOARD_B)
    cancelled = {i for i in a.keys() & b.keys() if a[i] == b[i]}
    assert cancelled and not cancelled.intersection(learned.weights)


def test_real_goal_rank_is_rejected_without_tuple_aliasing():
    learned = model(); goal = [11]+[0]*15
    with pytest.raises(ValueError, match='nonterminal'):
        learned.predict(goal, BOARD_B)
    with pytest.raises(ValueError, match='nonterminal'):
        learned.update(BOARD_A, goal, [0., 0., 1.])
    assert learned.weights == {} and learned.updates == 0


def test_frozen_sparse_json_roundtrip_preserves_weights_and_predictions():
    learned = model(); learned.update(BOARD_A, BOARD_B, [2., -.5, .5]); learned.freeze()
    before = learned.state(); path = TEMP/'paired_model.json'
    path.write_text(json.dumps(learned.to_payload()))
    loaded = PairedAdvantage.from_payload(json.loads(path.read_text())); MODELS.append(loaded)
    assert loaded.state() == before
    assert loaded.predict(BOARD_A, BOARD_B) == learned.predict(BOARD_A, BOARD_B)
    assert learned.state() == before
    with pytest.raises(RuntimeError, match='frozen'):
        loaded.update(BOARD_A, BOARD_B, [1., 0., 0.])
    with pytest.raises(TypeError):
        loaded.weights[0] = (1., 2., 3.)
    assert learned.to_payload()['storage']['weight_parameters'] == 3*len(learned.weights)


def test_selector_uses_risk_sign_and_counts_both_planners_on_fallback():
    learned = model(); learned.update(BOARD_A, BOARD_B, [2., .5, -.5])
    low = selector(learned, RISK1); high = selector(learned, RISK8)
    assert low.choose(BOARD_A)['action'] == 'LEFT'
    selected = high.choose(BOARD_A, simulation_seed=923, previous_action='RIGHT')
    assert selected['action'] == 'DOWN'
    assert selected['selection']['estimated_advantage'] == pytest.approx(.2-.4-.05)
    assert selected['counts']['baseline_learned_swipe_calls'] == 20
    assert selected['counts']['candidate_learned_swipe_calls'] == 40
    assert selected['counts']['candidate_model_sampled_transitions'] == 8
    assert selected['counts']['learner_pair_predictions'] == 1
    assert high.candidate.calls[0]['simulation_seed'] == 923
    assert high.candidate.calls[0]['previous_action'] == 'RIGHT'
    assert 'simulation_seed' not in high.teacher.calls[0]


def test_immediate_reward_counted_once_and_tie_preserves_h2():
    learned = model()
    tie = selector(learned)
    assert tie.choose(BOARD_A)['action'] == 'DOWN'
    immediate = selector(learned, baseline=choice('DOWN', BOARD_B, score=4),
                         candidate=choice('LEFT', BOARD_A, score=12, value=-999.))
    result = immediate.choose(BOARD_A)
    assert result['action'] == 'LEFT'
    assert result['value'] == 10.+8./2048.
    assert result['tail_value'] == 10.-4./2048.
    assert result['action_values']['LEFT']['value'] == result['value']
    assert result['value_kind'] == 'baseline_h2_proxy_plus_learned_advantage'
    assert result['selection']['candidate_choice']['value'] == -999.


def test_same_action_bypasses_learning_but_runs_and_charges_both_candidates():
    learned = model(); same = choice('DOWN', BOARD_B)
    planner = selector(learned, candidate=same)
    before = learned.state(); result = planner.choose(BOARD_A)
    assert result['action'] == 'DOWN' and result['selection']['same_action']
    assert learned.counts['pair_predictions'] == 0 and learned.state() == before
    assert len(planner.teacher.calls) == len(planner.candidate.calls) == 1
    assert result['counts']['candidate_learned_swipe_calls'] == 40
    assert result['counts']['same_action_bypasses'] == 1


@pytest.mark.parametrize('goal_side', ['candidate', 'baseline'])
def test_goal_pair_retains_h2_after_charging_both_without_prediction(goal_side):
    learned = model(); args = {goal_side: choice('LEFT' if goal_side == 'candidate' else 'DOWN',
                                               [11]+[0]*15, score=2048, value=100.)}
    planner = selector(learned, **args); before = learned.state()
    result = planner.choose(BOARD_A)
    assert result['action'] == 'DOWN'
    assert result['selection']['terminal_pair_bypass']
    assert result['counts']['terminal_pair_bypasses'] == 1
    assert result['counts']['baseline_learned_swipe_calls'] == 20
    assert result['counts']['candidate_learned_swipe_calls'] == 40
    assert learned.counts['pair_predictions'] == 0 and learned.state() == before


def test_unfrozen_or_changed_query_is_rejected_before_any_planner_work():
    learned = model()
    with pytest.raises(ValueError, match='frozen'):
        AdvantagePlanner(None, None, learned, RISK1)
    planner = selector(learned)
    with pytest.raises(ValueError, match='fixed'):
        planner.choose(BOARD_A, RISK8)
    assert not planner.teacher.calls and not planner.candidate.calls
