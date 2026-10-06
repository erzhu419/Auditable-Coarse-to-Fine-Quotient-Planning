"""Finite feedback fixtures: no V281 source or target draws in these tests."""
from collections import Counter
from fractions import Fraction
import json
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import natural_model_revision_v281 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BOARD = (1, 1) + (0,) * 14
AFTER = (2,) + (0,) * 15
CHILD = (2, 1) + (0,) * 14
FINAL = (2, 1, 2) + (0,) * 13


def empty_costs():
    return dict(environment_counts={}, planning_counts={}, memory_counts={},
        decision_seconds=0., decision_cpu_seconds=0., memory_seconds=0.,
        memory_cpu_seconds=0., environment_seconds=0., environment_cpu_seconds=0.,
        cpu_seconds=0., wall_seconds=0.)


class DummyPlanner:
    def __init__(self, leaf=None, depth=1, build_dir=None):
        self.counts = Counter()
        self.setup_counts, self.setup_seconds = Counter(), 0.
        self.spawn_probabilities = (.5, .5)

    def choose(self, board, query):
        self.counts['choose_calls'] += 1
        return dict(action='LEFT', value=0.,
                    afterstate=AFTER if tuple(board) == BOARD else CHILD)


@pytest.mark.parametrize('status', ['LOST', 'WON', 'CUTOFF'])
def test_previous_and_last_spawn_are_committed_once_and_initial_tiles_excluded(monkeypatch, status):
    def fake_episode(seed, act, p_four, max_steps):
        assert p_four == .5  # Environment receives the law, actor receives boards only.
        assert act(BOARD, 0) == 'LEFT'
        assert act(CHILD, 1) == 'LEFT'
        return dict(seed=seed, return_score=4, status=status, steps_count=2,
            final_board=FINAL, work=dict(sampled_transitions=2, initial_spawns=2),
            steps=[dict(afterstate=AFTER, next_board=CHILD),
                   dict(afterstate=CHILD, next_board=FINAL)])
    monkeypatch.setattr(core, 'run_episode', fake_episode)
    memory = SpawnMemory('POOLED')
    summary, raw = core.play_game(DummyPlanner(), memory, 123, .5)
    assert memory.observations_seen == 2
    assert [d['observations_before'] for d in raw['decisions']] == [0, 1]
    assert [d['p_four'] for d in raw['decisions']] == [.5, 1 / 3]
    assert summary['costs']['memory_counts']['observations_received'] == 2
    assert summary['costs']['environment_counts']['initial_spawns'] == 2
    assert summary['utility'] == 4 / 2048. + (4 if status == 'WON' else -4 if status == 'LOST' else 0)


def test_actor_feedback_does_not_take_phase_or_true_probability(monkeypatch):
    calls = []
    def fake_episode(seed, act, p_four, max_steps):
        calls.append(p_four)
        act(BOARD, 0)
        return dict(seed=seed, return_score=0, status='LOST', steps_count=1,
            final_board=CHILD, work=dict(sampled_transitions=1),
            steps=[dict(afterstate=AFTER, next_board=CHILD)])
    monkeypatch.setattr(core, 'run_episode', fake_episode)
    first = core.play_game(DummyPlanner(), SpawnMemory('LIBRARY'), 123, .1)[1]
    second = core.play_game(DummyPlanner(), SpawnMemory('LIBRARY'), 123, .5)[1]
    assert first['decisions'] == second['decisions']
    assert first['memory_events'] == second['memory_events']
    assert calls == [.1, .5]


def test_shared_whole_warmup_bills_excess_and_freezes_only_first_256(monkeypatch):
    monkeypatch.setattr(core, 'FrozenLeafPlanner', DummyPlanner)
    def fake_game(planner, memory, seed, p_four):
        raw = dict(episode=dict(steps=[dict(afterstate=AFTER, next_board=CHILD)] * 300))
        for _ in range(300):
            memory.observe(1)
        costs = empty_costs()
        costs['environment_counts'] = dict(sampled_transitions=300, initial_spawns=2)
        return dict(costs=costs, status='LOST', steps=300, utility=-4), raw
    monkeypatch.setattr(core, 'play_game', fake_game)
    receipts = []
    memories, report = core.warmup(None, 0, receipts.append)
    assert report['physical_games'] == 1 and report['observations'] == 300
    assert report['physical_costs']['environment_counts']['sampled_transitions'] == 300
    assert all(m.observations_seen == 300 for m in memories.values())
    assert memories['DIRECT'].to_payload() == memories['FROZEN_H2'].to_payload()
    assert memories['FROZEN_H2'].counts['beta_updates'] == 256
    assert memories['POOLED_H2'].counts['beta_updates'] == 300
    assert memories['LIBRARY_H2'].pending_n == 44
    assert len(receipts) == 1


def test_native_all_arms_use_same_readonly_leaf_and_no_new_td_updates():
    build = core.RUNTIME / 'tests'
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, build)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    parent = QueryParent(source, core.QUERY, core.QUERY, .5)
    leaf = QueryTD(parent, 'PRIOR', build)
    leaf.freeze()
    planners = {arm: core.FrozenLeafPlanner(leaf, 1 if arm == 'DIRECT' else 2, build)
                for arm in core.ARMS}
    assert all(p.model is leaf and p.weights is leaf.weights for p in planners.values())
    before = leaf.weights.copy()
    for planner in planners.values():
        planner.choose(BOARD, core.QUERY)
    np.testing.assert_array_equal(leaf.weights, before)
    assert leaf.updates == 0 and not leaf.weights.flags.writeable
    assert planners['DIRECT'].counts['generated_spawn_outcomes'] == 0
    assert planners['FROZEN_H2'].counts['generated_spawn_outcomes'] > 0


def test_new_seed_schedule_is_paired_and_all_lifecycles_disjoint():
    online = {core.environment_seed(life, phase, ep) for life in core.LIFECYCLES
              for phase in range(3) for ep in range(core.EPISODES_PER_PHASE)}
    assert len(online) == 16 * 3 * 8
    assert not online & {core.warmup_seed(life, ep) for life in core.LIFECYCLES for ep in range(20)}
    assert [core.environment_seed(0, phase, 0) for phase in range(3)] == [28140100, 28140108, 28140116]


def test_contrast_resamples_whole_memory_lifecycles_and_reports_parent_means(monkeypatch):
    monkeypatch.setattr(core, 'BOOTSTRAP_DRAWS', 20)
    records = [dict(parent=i % 4, arms={
        'LIBRARY_H2': dict(total_utility=float(i + 1)),
        'POOLED_H2': dict(total_utility=0.)}) for i in range(16)]
    contrast = core.paired_contrast(records, 'LIBRARY_H2', 'POOLED_H2')
    assert contrast['lifecycle_deltas'] == list(map(float, range(1, 17)))
    assert contrast['mean'] == 8.5 and contrast['improved'] == 16
    assert contrast['parent_mean_deltas'] == {'0': 7., '1': 8., '2': 9., '3': 10.}
    assert contrast['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'


def test_cost_sum_does_not_charge_logical_shared_source_per_arm():
    first, second = empty_costs(), empty_costs()
    first['environment_counts'] = dict(sampled_transitions=3)
    second['environment_counts'] = dict(sampled_transitions=5)
    first['memory_counts'] = dict(observations_received=3)
    second['memory_counts'] = dict(observations_received=5)
    first['decision_cpu_seconds'], second['decision_cpu_seconds'] = 2., 4.
    total = core.sum_costs([first, second])
    assert total['environment_counts']['sampled_transitions'] == 8
    assert total['memory_counts']['observations_received'] == 8
    assert total['decision_cpu_seconds'] == 6.


def test_bootstrap_keeps_each_parent_composition_fixed(monkeypatch):
    monkeypatch.setattr(core, 'BOOTSTRAP_DRAWS', 3)
    calls = []
    class WithinParentRng:
        def __init__(self, seed):
            assert seed == core.BOOTSTRAP_SEED
        def choices(self, values, k):
            assert k == 4
            assert len({int(value - 1) % 4 for value in values}) == 1
            calls.append(values)
            return [values[0]] * k
    monkeypatch.setattr(core.random, 'Random', WithinParentRng)
    records = [dict(parent=i % 4, arms={
        'LIBRARY_H2': dict(total_utility=float(i + 1)),
        'POOLED_H2': dict(total_utility=0.)}) for i in range(16)]
    contrast = core.paired_contrast(records, 'LIBRARY_H2', 'POOLED_H2')
    assert len(calls) == 3 * 4
    assert contrast['ci95'] == [2.5, 2.5]
    assert contrast['mean'] == 8.5


def test_source_costs_include_required_parents_once_and_exclude_old_outer_games(tmp_path):
    q = dict(training_blocks=[dict(environment_counts=dict(sampled_transitions=5),
        learning_counts=dict(td_updates=4), seconds=1., games=1)],
        checkpoints=[dict(episodes=4096, model_file='leaf.npz', updates=4,
            save_counts=dict(checkpoint_saves=1), save_seconds=.1,
            evaluations=[dict(sampled_transitions=999999)])],
        setup_counts=dict(cpp_compilations=1), setup_seconds=.2,
        references=[dict(sampled_transitions=999999)])
    capsule = dict(snapshots=[dict(life=i, rule={}) for i in range(4)],
                   inherited_costs=dict(separate_dynamics=3))
    previous = dict(settings=dict(queries=dict(risk_goal=core.QUERY)),
        lifecycles=[dict(life=i, queries=dict(risk_goal=q,
            reward=dict(training_blocks=[dict(sampled_transitions=999999)]))) for i in range(4)])
    (tmp_path / 'source_capsule.json').write_text(json.dumps(capsule))
    (tmp_path / 'run.json').write_text(json.dumps(previous))
    sources = core.load_sources(tmp_path)
    assert [s['parent'] for s in sources['parents']] == [0, 1, 2, 3]
    assert sum(s['inherited_training_costs']['environment_counts']['sampled_transitions']
               for s in sources['parents']) == 20
    assert sources['inherited_dynamics_costs'] == dict(separate_dynamics=3)


def test_all_arms_keep_one_memory_across_phases_and_pair_actual_game_seeds(monkeypatch):
    monkeypatch.setattr(core, 'FrozenLeafPlanner', DummyPlanner)
    monkeypatch.setattr(core, 'EPISODES_PER_PHASE', 2)
    memories = {arm: SpawnMemory(method) for arm, method in core.METHODS.items()}
    for memory in memories.values():
        for _ in range(256):
            memory.observe(1)
    monkeypatch.setattr(core, 'warmup', lambda *args: (memories, {}))
    def fake_game(planner, memory, seed, p_four):
        memory.observe(2)
        costs = empty_costs()
        costs['environment_counts'] = dict(sampled_transitions=1)
        return dict(seed=seed, status='LOST', utility=-4., costs=costs), {}
    monkeypatch.setattr(core, 'play_game', fake_game)
    raw = []
    record = core.run_lifecycle(SimpleNamespace(updates=0), 3, raw.append)
    for arm in core.ARMS:
        assert record['arms'][arm]['memory_before']['observations_seen'] == 256
        assert record['arms'][arm]['memory_after']['observations_seen'] == 262
        assert record['arms'][arm]['costs']['environment_counts']['sampled_transitions'] == 6
        assert record['arms'][arm]['total_utility'] == -24.
        assert [g['seed'] for p in record['arms'][arm]['phases'].values()
                for g in p['game_summaries']] == list(range(core.seed_base(3), core.seed_base(3) + 6))
    assert len(raw) == 24
