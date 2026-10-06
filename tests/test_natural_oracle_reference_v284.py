"""Finite known-law and paired-cost fixtures; no new environment samples."""
from collections import Counter
from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import natural_oracle_reference_v284 as core

BOARD = (1, 1)+(0,)*14
AFTER = (2,)+(0,)*15
CHILD = (2, 1)+(0,)*14


class DummyPlanner:
    instances = []

    def __init__(self, leaf=None, depth=2, build_dir=None):
        assert depth == 2
        self.leaf = leaf
        self.counts, self.setup_counts = Counter(), Counter()
        self.setup_seconds = 0.
        self.spawn_probabilities = None
        self.instances.append(self)

    def choose(self, board, query):
        assert query == core.QUERY
        self.counts.update(choose_calls=1, generated_spawn_outcomes=2)
        return dict(action='LEFT', value=self.spawn_probabilities[1], afterstate=AFTER)


@pytest.mark.parametrize('p_four,status', [(.1, 'LOST'), (.5, 'WON'), (.1, 'CUTOFF')])
def test_true_law_fixed_for_every_decision_and_actual_game_billed(monkeypatch, p_four, status):
    def fake_episode(seed, act, probability, max_steps):
        assert seed == 123 and probability == p_four and max_steps == 8192
        assert act(BOARD, 0) == act(CHILD, 1) == 'LEFT'
        return dict(seed=seed, return_score=2048, status=status, steps_count=2,
            final_board=CHILD, steps=[dict(board=BOARD), dict(board=CHILD)],
            work=dict(sampled_transitions=2, initial_spawns=2))
    monkeypatch.setattr(core, 'run_episode', fake_episode)
    planner = DummyPlanner()
    summary, raw = core.play_known_game(planner, 123, p_four)
    assert planner.spawn_probabilities == (1.-p_four, p_four)
    assert raw['decisions'] == [dict(action='LEFT', value=p_four, p_four=p_four)]*2
    assert summary['utility'] == 1. + (4. if status == 'WON' else -4. if status == 'LOST' else 0.)
    costs = summary['costs']
    assert costs['environment_counts'] == dict(sampled_transitions=2, initial_spawns=2)
    assert costs['planning_counts'] == dict(choose_calls=2, generated_spawn_outcomes=4)
    assert costs['memory_counts'] == {} and costs['memory_cpu_seconds'] == 0.
    assert costs['cpu_seconds'] >= costs['decision_cpu_seconds']


def empty_costs():
    return dict(environment_counts=dict(sampled_transitions=1, initial_spawns=2),
        planning_counts=dict(generated_spawn_outcomes=2), memory_counts={},
        decision_seconds=0., decision_cpu_seconds=0., memory_seconds=0.,
        memory_cpu_seconds=0., environment_seconds=0., environment_cpu_seconds=0.,
        cpu_seconds=0., wall_seconds=0.)


def source_fixture():
    parents = [dict(parent=parent, inherited_training_costs=dict(
        environment_counts=dict(sampled_transitions=100+parent))) for parent in range(4)]
    rows = []
    for life in range(16):
        phases = {phase: dict(games=8, utility_sum=8., game_summaries=[
            dict(seed=28140100+100*life+8*phase_index+episode) for episode in range(8)])
            for phase_index, (phase, _) in enumerate(core.PHASES)}
        rows.append(dict(lifecycle=life, parent=life % 4, arms={arm:
            dict(total_utility=24., phases=deepcopy(phases), costs=empty_costs(),
                planner_setup_counts=dict(cpp_library_cache_hits=1), planner_setup_seconds=.01)
            for arm in core.BASELINES}))
    return dict(schema='acfqp.natural_model_revision.v281',
        settings=dict(lifecycles=list(range(16)), episodes_per_phase=8),
        source_provenance=dict(parents=parents, inherited_dynamics_costs=dict(source_examples=99)),
        summary=dict(by_lifecycle=rows, arms={arm: dict(costs=empty_costs()) for arm in core.BASELINES},
            accounting=dict(physical_warmup_games=16, physical_warmup_transitions=4800,
                warmup_costs=empty_costs(), warmup_memory_import_seconds=.3,
                warmup_memory_import_cpu_seconds=.2)))


def test_full_paired_cohort_shared_readonly_parents_and_no_repeated_warmup(monkeypatch, tmp_path):
    original = source_fixture()
    snapshot = deepcopy(original)
    source_path = tmp_path/'v281.json'
    source_path.write_text(json.dumps(original))
    calls, leaves, emitted = [], {}, []
    DummyPlanner.instances = []
    def fake_load(source, runtime):
        parent = source['parent']
        leaf = SimpleNamespace(updates=0, weights=np.array([float(parent)]))
        leaf.weights.flags.writeable = False
        leaves[parent] = leaf
        return leaf, dict(resident_source_and_leaf_weight_bytes=8)
    def fake_game(planner, seed, p_four):
        assert not planner.leaf.weights.flags.writeable
        calls.append((planner.leaf, seed, p_four))
        summary = dict(seed=seed, status='LOST', steps=1, utility=2., costs=empty_costs())
        return summary, dict(summary=summary, episode={}, decisions=[])
    monkeypatch.setattr(core, 'load_leaf', fake_load)
    monkeypatch.setattr(core, 'FrozenLeafPlanner', DummyPlanner)
    monkeypatch.setattr(core, 'play_known_game', fake_game)
    monkeypatch.setattr(core, 'BOOTSTRAP_DRAWS', 2)
    result = core.run_replication(source_path, emitted.append, tmp_path)
    assert len(leaves) == 4 and len(calls) == len(emitted) == 384
    for index, (leaf, seed, p_four) in enumerate(calls):
        life, offset = divmod(index, 24)
        phase, episode = divmod(offset, 8)
        assert leaf is leaves[life % 4]
        assert seed == 28140100+100*life+8*phase+episode
        assert p_four == core.PHASES[phase][1]
    accounting = result['accounting']
    assert accounting['new_online_games'] == accounting['new_online_transitions'] == 384
    assert accounting['new_source_observations'] == accounting['new_warmup_observations'] == 0
    assert accounting['new_warmup_games'] == accounting['new_value_parameter_updates'] == 0
    assert accounting['inherited_source_training_transitions'] == 406
    assert accounting['inherited_shared_warmup_games'] == 16
    assert accounting['inherited_shared_warmup_transitions'] == 4800
    assert result['source_provenance'] == snapshot['source_provenance']
    for baseline in core.BASELINES:
        assert result['summary']['arms'][baseline] == snapshot['summary']['arms'][baseline]
        retained = result['summary']['by_lifecycle'][0]['arms'][baseline]
        assert retained['costs'] == snapshot['summary']['by_lifecycle'][0]['arms'][baseline]['costs']
        assert retained['planner_setup_counts'] == dict(cpp_library_cache_hits=1)
        assert retained['planner_setup_seconds'] == .01
    assert accounting['inherited_warmup_memory_import_cpu_seconds'] == .2
    assert json.loads(source_path.read_text()) == snapshot
    assert all(row['arm'] == 'ORACLE_H2' for row in emitted)
    assert result['summary']['arms']['ORACLE_H2']['mean_lifecycle_utility'] == 48.
    for contrast in result['summary']['paired_contrasts'].values():
        assert contrast['mean'] == 24. and contrast['ci95'] == [24., 24.]
        assert all(phase['mean'] == 8. for phase in contrast['phases'].values())


def test_v284_bootstrap_keeps_fixed_parent_composition_and_uses_own_seed(monkeypatch):
    calls = []
    class WithinParentRng:
        def __init__(self, seed):
            assert seed == 28400001
        def choices(self, values, k):
            assert k == 4 and len({int(value-1) % 4 for value in values}) == 1
            calls.append(values)
            return [values[0]]*k
    monkeypatch.setattr(core.random, 'Random', WithinParentRng)
    monkeypatch.setattr(core, 'BOOTSTRAP_DRAWS', 3)
    records = [dict(parent=i % 4, arms={
        'ORACLE_H2': dict(total_utility=float(i+1)),
        'LIBRARY_H2': dict(total_utility=0.)}) for i in range(16)]
    contrast = core.paired_contrast(records, 'LIBRARY_H2')
    assert contrast['lifecycle_deltas'] == list(map(float, range(1, 17)))
    assert contrast['mean'] == 8.5 and contrast['ci95'] == [2.5, 2.5]
    assert contrast['parent_mean_deltas'] == {'0': 7., '1': 8., '2': 9., '3': 10.}
    assert len(calls) == 12
    assert contrast['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
