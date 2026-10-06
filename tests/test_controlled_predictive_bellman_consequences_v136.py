"""Finite native joint targets, fixed-teacher streams and frozen readouts."""
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import controlled_predictive_bellman_consequences_v136 as core
from acfqp.science import controlled_predictive_online_query_td_v131 as single
from acfqp.science.controlled_predictive_contextual_ntuple_v134 import ConditionalQueryTD
from acfqp.science.controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from acfqp.science.controlled_predictive_ntuple_td_v120 import ACTIONS, ALPHA, NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/controlled_predictive_bellman_consequences_v136_build'
SOURCE = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
QUERIES = {risk: dict(reward_weight=1., failure_penalty=float(risk), goal_bonus=float(risk))
    for risk in (1, 2, 6, 8)}
SPARSE = [1, 1]+[0]*14
GOAL = [3, 3]+[0]*14
LOSS_BRANCH = [2, 1, 2, 1, 1, 2, 1, 2, 2, 1, 2, 1, 2, 1, 1, 1]
LOST = [1, 2, 1, 2, 2, 1, 2, 1]*2
SOURCES, LEAVES, MODELS, PLANNERS, STREAMS = [], [], [], [], []
ORACLE_WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_bellman_consequences_v136.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        model_work=dict(sum((model.counts for model in MODELS), Counter())),
        teacher_work=dict(sum((model.counts for model in PLANNERS), Counter())),
        leaf_work=dict(sum((model.counts for model in LEAVES), Counter())),
        source_work=dict(sum((model.counts for model in SOURCES), Counter())),
        oracle_work=dict(ORACLE_WORK),
        setup_counts=dict(sum((getattr(model, 'setup_counts', Counter())
            for model in SOURCES+LEAVES+MODELS+PLANNERS), Counter())),
        scripted_environment_work=dict(sum((stream.environment_counts for stream in STREAMS), Counter())),
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Static finite native checks and scripted teacher episodes; no natural-game samples.'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2)+'\n')


def components(representation='SINGLE', risk=8):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(8075, 9026)), (2, Fraction(951, 9026))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    source.weights.flags.writeable = False
    source.updates = 42
    SOURCES.append(source)
    parent = QueryParent(source, SOURCE, QUERIES[risk], .4)
    leaf = (single.QueryTD(parent, 'PRIOR', BUILD) if representation == 'SINGLE' else
        ConditionalQueryTD(parent, representation, BUILD))
    leaf.update(SPARSE, .7)
    leaf.freeze()
    LEAVES.append(leaf)
    model = core.PolicyComponents(leaf, BUILD)
    MODELS.append(model)
    return model


def comparable(choice):
    return dict(action=choice['action'], value=choice['value'], status=choice['status'],
        action_values={action: {field: row[field] for field in ('afterstate', 'score', 'value', 'tail_value')}
            for action, row in choice['action_values'].items()})


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
@pytest.mark.parametrize('risk', [1, 8])
def test_zero_components_exactly_recover_frozen_teacher_all_legal_values_and_h2(representation, risk):
    model = components(representation, risk)
    np.testing.assert_array_equal(model.weights[0], model.teacher_leaf.weights)
    assert not np.any(model.weights[1])
    assert not np.shares_memory(model.weights, model.teacher_leaf.weights)
    assert model.reward_intercept == model.teacher_leaf.offset
    assert model.setup_counts['allocated_weight_parameters'] == 2*model.teacher_leaf.weights.size
    assert model.setup_counts['source_parameters_copied'] == model.teacher_leaf.weights.size
    teacher = FrozenLeafPlanner(model.teacher_leaf, 2, BUILD)
    PLANNERS.append(teacher)
    for board in (SPARSE, GOAL, LOSS_BRANCH, LOST, [4]+[0]*15):
        assert comparable(model.choose(board, QUERIES[risk], depth=1)) == comparable(model.teacher_leaf.choose(board))
        assert comparable(model.choose(board, QUERIES[risk], depth=2)) == comparable(teacher.choose(board))
    assert model.value(SPARSE)['success'] == .5
    assert model.spawn_probabilities == (8075/9026, 951/9026)


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_joint_update_uses_two_prewrite_errors_and_original_feature_multiplicities(representation):
    model = components(representation)
    model.weights[1].reshape(-1)[:] = np.arange(model.head_size)%7*.001
    before = model.weights.copy()
    indices = [int(address) for address in model.feature_indices(SPARSE)]
    multiplicities = Counter(indices)
    raw, logit = 0., 0.
    for address in indices:
        raw += before[0].reshape(-1)[address]
        logit += before[1].reshape(-1)[address]
    success = 1./(1.+math.exp(-logit))
    target_reward, target_success = .9, .15
    reward_error = (target_reward-model.reward_intercept)-raw
    success_error = target_success-success
    expected = before.reshape(2, -1).copy()
    for address, m in multiplicities.items():
        expected[0, address] += ALPHA*reward_error*m
        expected[1, address] += ALPHA*success_error*m
    source_before = model.teacher_leaf.weights.copy()
    update = model.update(SPARSE, target_reward, target_success)
    assert update['pre_raw_reward'] == raw and update['pre_reward'] == raw+model.reward_intercept
    assert update['pre_logit'] == logit and update['pre_success'] == success
    assert update['raw_reward_target'] == target_reward-model.reward_intercept
    assert update['reward_error'] == reward_error and update['success_error'] == success_error
    np.testing.assert_array_equal(model.weights.reshape(2, -1), expected)
    np.testing.assert_array_equal(model.teacher_leaf.weights, source_before)
    assert update['work']['table_lookups'] == 64
    assert update['work']['reward_table_update_occurrences'] == update['work']['success_table_update_occurrences'] == 32
    assert update['work']['reward_table_updates'] == update['work']['success_table_updates'] == len(multiplicities)
    assert update['work']['update_feature_squared_norm'] == sum(m*m for m in multiplicities.values())
    assert model.updates == model.counts['reward_td_updates'] == model.counts['success_td_updates'] == 1


def test_sigmoid_is_bounded_at_extreme_logits_and_soft_bce_gradient_does_not_vanish():
    model = components()
    model.weights[1].fill(1000./32)
    assert model.value(SPARSE)['success'] == 1.
    before = model.weights[1].copy()
    update = model.update(SPARSE, 0., .25)
    assert update['success_error'] == -.75
    assert np.any(model.weights[1] != before)
    model.weights[1].fill(-1000./32)
    value = model.value(SPARSE)
    assert value['success'] == 0. and value['failure'] == 1.
    goal = model.value([4]+[0]*15)
    assert goal == dict(raw_reward=0., reward=0., logit=None, success=1., failure=0.)


def scalar(model, score, vector, query):
    anchor = (score/2048.+vector['raw_reward'])+model.failure_shift+model.success_shift
    return (anchor+model.teacher_coefficient*(vector['success']-.5)
        +(model.teacher_failure-query['failure_penalty'])
        +((query['failure_penalty']+query['goal_bonus'])-model.teacher_coefficient)*vector['success'])


def oracle_direct(model, board, query):
    if max(board) >= model.radix:
        return dict(action=None, value=query['goal_bonus'], consequences=[0., 0., 1.], action_values={}, status='WON')
    actions = {}
    for action in ACTIONS:
        after, score, changed = model.rule.swipe(board, action, ORACLE_WORK)
        if not changed:
            continue
        vector = model.value(after)
        value = score/2048.+query['goal_bonus'] if max(after) >= model.radix else scalar(model, score, vector, query)
        actions[action] = dict(afterstate=list(after), score=score, value=value,
            tail_value=value-score/2048., consequences=[vector['reward'], vector['failure'], vector['success']])
    if not actions:
        return dict(action=None, value=-query['failure_penalty'], consequences=[0., 1., 0.], action_values={}, status='LOST')
    action = min(actions, key=lambda a: (-actions[a]['value'], a))
    return dict(action=action, **actions[action], action_values=actions, status='ACTIVE')


def oracle_h2(model, board, query):
    actions = {}
    for action in ACTIONS:
        after, score, changed = model.rule.swipe(board, action, ORACLE_WORK)
        if not changed:
            continue
        if max(after) >= model.radix:
            tail, reward, success = query['goal_bonus'], 0., 1.
        else:
            empty = [cell for cell, rank in enumerate(after) if rank == 0]
            tail, reward, success = 0., 0., 0.
            for cell in empty:
                for rank, exact_p in model.rule.spawn_distribution:
                    successor = list(after); successor[cell] = rank
                    chosen = oracle_direct(model, successor, query)
                    p = float(exact_p)/len(empty)
                    tail += p*chosen['value']
                    reward += p*(chosen.get('score', 0)/2048.+chosen['consequences'][0])
                    success += p*chosen['consequences'][2]
                    ORACLE_WORK['enumerated_spawn_outcomes'] += 1
            success = min(1., max(0., success))
        actions[action] = dict(afterstate=list(after), score=score, value=score/2048.+tail,
            tail_value=tail, consequences=[reward, 1.-success, success])
    action = min(actions, key=lambda a: (-actions[a]['value'], a))
    return dict(action=action, **actions[action], action_values=actions, status='ACTIVE')


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_reweighted_h2_uses_joint_components_of_one_chosen_action_per_branch(representation):
    model = components(representation)
    model.update(SPARSE, .5, .1)
    model.update(LOSS_BRANCH, 1.5, .9)
    model.freeze()
    before = model.weights.copy()
    for risk in (2, 6):
        for board in (SPARSE, GOAL, LOSS_BRANCH):
            expected = oracle_h2(model, board, QUERIES[risk])
            actual = model.choose(board, QUERIES[risk])
            assert comparable(actual) == comparable(expected)
            assert actual['action_values'] == expected['action_values']
            assert all(0. <= row['consequences'][2] <= 1. for row in actual['action_values'].values())
    np.testing.assert_array_equal(model.weights, before)


def test_h2_probability_closure_keeps_all_success_branches_bounded_without_changing_q():
    model = components()
    model.weights[1].fill(1000./32)
    result = model.choose(SPARSE, QUERIES[2])
    assert all(0. <= row['consequences'][1] <= 1e-15 and
        1.-1e-15 <= row['consequences'][2] <= 1. for row in result['action_values'].values())
    assert comparable(result) == comparable(oracle_h2(model, SPARSE, QUERIES[2]))


@pytest.mark.parametrize('representation', ['SINGLE', 'CAPACITY'])
def test_checkpoint_preserves_both_heads_teacher_identity_and_frozen_readouts(tmp_path, representation):
    model = components(representation)
    model.update(SPARSE, .7, .2)
    model.freeze()
    saved = model.save(tmp_path/f'{representation}.npz')
    metadata = json.loads(Path(saved['sidecar']).read_text())
    assert metadata['parameter_count'] == 2*model.teacher_leaf.weights.size
    assert metadata['prior_success'] == .5 and metadata['reward_intercept'] == model.reward_intercept
    restored = core.PolicyComponents.load(saved['path'], model.teacher_leaf, BUILD)
    MODELS.append(restored)
    np.testing.assert_array_equal(restored.weights, model.weights)
    assert not restored.weights.flags.writeable and restored.updates == 1
    assert restored.load_counts['checkpoint_loaded_parameters'] == saved['nonzero_weights']
    for risk in (1, 2, 6, 8):
        assert comparable(restored.choose(LOSS_BRANCH, QUERIES[risk])) == comparable(model.choose(LOSS_BRANCH, QUERIES[risk]))
    with pytest.raises(RuntimeError, match='frozen'):
        restored.update(SPARSE, 0., .5)


class ScriptComponents:
    def __init__(self, events):
        self.events, self.weights = events, np.array([.4, -.2])
        self.counts, self.updates = Counter(), 0
        self.teacher_query, self.target_query = QUERIES[8], QUERIES[8]
        self.rule, self.radix = SimpleNamespace(goal_rank=100), 100

    def value(self, afterstate):
        self.events.append(('value', afterstate[0], self.weights.tolist()))
        self.counts['value_calls'] += 1
        if max(afterstate) >= 100:
            return dict(raw_reward=0., reward=0., logit=None, success=1., failure=0.)
        reward = float(self.weights[0]+afterstate[0]*.1)
        logit = float(self.weights[1]); success = 1./(1.+math.exp(-logit))
        return dict(raw_reward=reward, reward=reward, logit=logit, success=success, failure=1.-success)

    def update(self, afterstate, target_reward, target_success):
        self.events.append(('update', afterstate[0], target_reward, target_success))
        pre_reward = float(self.weights[0]+afterstate[0]*.1)
        pre_logit = float(self.weights[1]); pre_success = 1./(1.+math.exp(-pre_logit))
        reward_error, success_error = target_reward-pre_reward, target_success-pre_success
        self.weights += .05*np.array([reward_error, success_error])
        self.updates += 1; self.counts['td_updates'] += 1
        return dict(pre_raw_reward=pre_reward, pre_reward=pre_reward, pre_logit=pre_logit,
            pre_success=pre_success, target_reward=target_reward, target_success=target_success,
            raw_reward_target=target_reward, reward_error=reward_error, success_error=success_error,
            work=dict(td_updates=1))

    def choose(self, *args, **kwargs):
        raise AssertionError('the student must never choose a training action')


class Scenario:
    def __init__(self, monkeypatch, ending='LOST', limit=3):
        self.ending, self.limit = ending, limit
        monkeypatch.setattr(single, '_spawn', self.spawn)
        monkeypatch.setattr(single, '_status', self.status)
        monkeypatch.setattr(single.ground, 'swipe_board_v1', self.swipe)

    def swipe(self, board, action):
        result = list(board); result[0] += 1
        if result[0] == self.limit and self.ending == 'WON':
            result[1] = 100
        return tuple(result), 4*result[0]+8*int(action.value == 'RIGHT'), True

    def spawn(self, board, rng, work, p_four):
        draw_cell, draw_rank = rng.random(), rng.random()
        work['environment_random_draws'] += 2
        cell, rank = 14+int(draw_cell >= .5), 1+int(draw_rank >= 1.-p_four)
        result = list(board); result[cell] = rank
        return tuple(result), cell, rank

    def status(self, board, work):
        work['scripted_status_calls'] += 1
        return self.ending if board[0] == self.limit else 'ACTIVE'

    def stream(self, max_steps=2000):
        events = []
        model = ScriptComponents(events)
        teacher = SimpleNamespace(counts=Counter())

        def choose(board, query):
            events.append(('choose', board[0]))
            teacher.counts['choose_calls'] += 1
            action = 'RIGHT' if board[0]%2 == 0 else 'DOWN'
            after, score, _ = self.swipe(board, SimpleNamespace(value=action))
            return dict(action=action, afterstate=after, score=score, value=17.+board[0])

        teacher.choose = choose
        stream = core.TeacherTDStream(model, teacher, lambda episode: 136000+episode, max_steps)
        MODELS.append(model); PLANNERS.append(teacher); STREAMS.append(stream)
        return stream


def test_stream_uses_fixed_teacher_and_both_next_predictions_before_joint_update(monkeypatch):
    stream = Scenario(monkeypatch).stream()
    row, = stream.advance(2)
    assert [event[0] for event in stream.model.events] == ['choose', 'value', 'choose', 'value', 'update']
    assert row['joint_updates'][0] is None
    update, prediction = row['joint_updates'][1], row['next_components'][1]
    assert update['target_reward'] == row['scores'][1]/2048.+prediction['reward']
    assert update['target_success'] == prediction['success']
    assert row['chosen_values'] == [17., 18.]
    assert row['actions'] == ['RIGHT', 'DOWN']
    assert stream.teacher_counts['choose_calls'] == 2 and stream.model.updates == 1


@pytest.mark.parametrize('ending', ['WON', 'LOST'])
def test_terminal_joint_targets_keep_winning_reward_and_exclude_failure_reward(monkeypatch, ending):
    stream = Scenario(monkeypatch, ending).stream()
    row, = stream.advance(3)
    assert stream.pending is None and row['status'] == ending
    if ending == 'WON':
        assert row['next_components'][-1]['reward'] == 0.
        assert row['joint_updates'][-1]['target_reward'] == row['scores'][-1]/2048.
        assert row['joint_updates'][-1]['target_success'] == 1.
        assert row['terminal_update'] is None and stream.model.updates == 2
    else:
        assert row['terminal_update']['target_reward'] == row['terminal_update']['target_success'] == 0.
        assert row['terminal_update']['afterstate'][0] == 3 and stream.model.updates == 3


def test_budget_pause_resumes_same_teacher_rng_pending_and_both_heads(monkeypatch):
    scenario = Scenario(monkeypatch)
    full, split = scenario.stream(), scenario.stream()
    whole = full.advance(8)
    first = split.advance_to(2)
    state = (split.pending, split.rng.getstate(), split.model.weights.copy())
    split.model.value(split.pending)
    assert split.pending == state[0] and split.rng.getstate() == state[1]
    np.testing.assert_array_equal(split.model.weights, state[2])
    pieces = first+split.advance_to(5)+split.advance_to(8)
    for field in ('actions', 'scores', 'spawned_cells', 'spawned_ranks', 'chosen_values', 'next_components', 'joint_updates'):
        assert [value for row in pieces for value in row[field]] == [value for row in whole for value in row[field]]
    np.testing.assert_array_equal(split.model.weights, full.model.weights)
    assert split.pending == full.pending and split.rng.getstate() == full.rng.getstate()
    assert split.environment_counts == full.environment_counts
    assert split.teacher_counts == full.teacher_counts
    assert split.training_counts == full.training_counts
    assert first[0]['pending_after'] == pieces[1]['pending_before']


def test_zero_budget_and_actual_cutoff_do_not_generate_terminal_labels(monkeypatch):
    stream = Scenario(monkeypatch, ending='ACTIVE', limit=9).stream(max_steps=3)
    assert stream.advance(0) == [] and not stream.model.counts and not stream.teacher.counts
    row, = stream.advance(3)
    assert row['status'] == 'CUTOFF' and row['censored_last_update']
    assert row['terminal_update'] is None and row['pending_after'] is None
    assert stream.model.updates == 2 and stream.teacher_counts['choose_calls'] == 3
