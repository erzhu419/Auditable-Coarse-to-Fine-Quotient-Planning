"""Causal anchor binding, fixed policy execution and observed-label semantics."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest

from acfqp.science import controlled_predictive_context_experience_v116 as module
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory

WORK = Counter()


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = Path(__file__).resolve().parents[1] / 'reports/controlled_predictive_context_experience_v116.checks.json'
    log = json.loads(path.read_text()) if path.exists() else {'attempts': []}
    log['attempts'].append(dict(failures=request.session.testsfailed - before,
        development_work=dict(WORK), newly_sampled_environment_transitions=0,
        new_synthetic_transitions=0, neural_model_fits=0,
        scope='handwritten observed trajectories and mocked environment/policy calls'))
    path.write_text(json.dumps(log, indent=2) + '\n')


def game(ranks, status='LOST'):
    steps = [dict(afterstate=[1] + [0] * 15, next_board=[1, rank] + [0] * 14,
        score=2048 * (index + 1), status='ACTIVE', spawned_rank=3-rank)
        for index, rank in enumerate(ranks)]
    if steps and status in ('LOST', 'WON'):
        steps[-1]['status'] = status
    return dict(status=status, steps=steps, seed='hidden', p_four='hidden')


def collect(trajectory, router=None):
    router = SpawnMemory('LIBRARY') if router is None else router
    before = router.counts.copy()
    result = module.causal_records(trajectory, 'GREEDY', 7, router)
    WORK.update({key: value - before[key] for key, value in router.counts.items()})
    WORK['handwritten_observed_steps'] += len(trajectory['steps'])
    return result


@pytest.mark.parametrize('policy', module.POLICIES)
def test_game_binds_each_action_to_one_policy_and_accounts_planning(monkeypatch, policy):
    rule, sentinel, calls = object(), {'status': 'CUTOFF'}, []
    def policy_action(board, chosen, supplied_rule, work):
        assert chosen == policy and supplied_rule is rule
        calls.append(tuple(board)); work['fixture_policy_calls'] += 1
        WORK['mock_policy_calls'] += 1
        return 'LEFT'
    def run_episode(seed, action, p_four, max_steps):
        assert (seed, p_four, max_steps) == (116001, .3, 8)
        for index in range(3):
            assert action((index,)*16, index) == 'LEFT'
        WORK['mock_episode_calls'] += 1
        return sentinel
    monkeypatch.setattr(module, 'policy_action', policy_action)
    monkeypatch.setattr(module, 'run_episode', run_episode)
    result, counts = module.policy_game(116001, policy, rule, .3, max_steps=8)
    assert result is sentinel and len(calls) == 3 and counts == {'fixture_policy_calls': 3}


def test_context_is_saved_before_its_spawn_and_hidden_metadata_is_unused():
    records, log = collect(game([2, 1, 2, 1, 1, 2]))
    contexts = log['causal_contexts']
    assert [row['context_observations_seen'] for row in contexts] == list(range(6))
    assert [row['context_p4'] for row in contexts] == [1/2, 2/3, 2/4, 3/5, 3/6, 3/7]
    assert all(row['context_module_id'] == 0 for row in contexts)
    assert [(row['anchor_step'], row['horizon']) for row in records] == [
        (0, 30), (0, 31), (4, 30), (4, 31), (5, 30), (5, 31)]
    for row in records:
        assert row['context_p4'] == contexts[row['anchor_step']]['context_p4']
        assert row['context_observations_seen'] == row['anchor_step']


def test_later_observations_do_not_rewrite_saved_anchor_contexts():
    first = game([1, 1, 2, 2, 1, 1])
    changed = deepcopy(first)
    changed['steps'][4]['next_board'][1] = 2
    changed['steps'][5]['next_board'][1] = 2
    rows_a, log_a = collect(first)
    rows_b, log_b = collect(changed)
    assert log_a['causal_contexts'][:5] == log_b['causal_contexts'][:5]
    assert log_a['causal_contexts'][5] != log_b['causal_contexts'][5]
    assert rows_a[:4] == rows_b[:4]


def test_boundary_event_applies_only_after_its_observation():
    router = SpawnMemory('LIBRARY')
    router.observations_seen = 255
    router.modules[0].update(alpha=1, beta=256)
    records, log = collect(game([2, 1]), router)
    assert log['causal_contexts'][0]['context_observations_seen'] == 255
    assert log['causal_contexts'][0]['context_p4'] == 1/257
    assert log['causal_contexts'][1]['context_p4'] == 2/258
    assert len(log['module_events']) == 1
    assert log['module_events'][0]['kind'] == 'initialized'
    assert log['module_events'][0]['step'] == 0 and log['module_events'][0]['obs_index'] == 256
    assert records[0]['context_p4'] == 1/257


def test_terminal_targets_exclude_anchor_reward_and_keep_joint_outcome():
    records, log = collect(game([1, 2, 1], 'WON'))
    assert [row['target'] for row in records] == [[5., 0., 1.], [5., 0., 1.], [0., 0., 1.], [0., 0., 1.]]
    assert all(row['episode'] == 7 and row['policy'] == 'GREEDY' for row in records)
    assert log['counts'] == dict(observed_transitions=3, labeled_records=4,
        candidate_windows=4, censored_windows_omitted=0)


def test_cutoff_keeps_only_complete_windows_and_does_not_fabricate_failure():
    records, log = collect(game([1] * 32, 'CUTOFF'))
    assert [(row['anchor_step'], row['horizon']) for row in records] == [(0, 30), (0, 31)]
    assert all(row['target'][1:] == [0., 0.] for row in records)
    assert log['counts'] == dict(observed_transitions=32, labeled_records=2,
        candidate_windows=18, censored_windows_omitted=16)


def test_empty_trajectory_produces_neither_context_nor_labels():
    records, log = collect(game([], 'CUTOFF'))
    assert records == [] and log['causal_contexts'] == [] and log['module_events'] == []
    assert all(value == 0 for value in log['counts'].values())
