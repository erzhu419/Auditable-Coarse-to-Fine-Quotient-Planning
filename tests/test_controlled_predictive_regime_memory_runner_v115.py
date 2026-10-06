"""The lifecycle preserves chronological memory and keeps truth out of learned planning."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from scripts import run_controlled_predictive_regime_memory_v115 as m
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


def rule():
    return LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform')


def fake_source(seed, action_fn, p_four, max_steps):
    steps = []
    for i in range(130):
        rank = 2 if i % 10 < round(10 * p_four) else 1
        steps.append(dict(afterstate=[0] * 16, next_board=[rank] + [0] * 15, spawned_rank=rank))
    return dict(seed=seed, status='LOST', steps=steps, steps_count=130,
        work=dict(sampled_transitions=130, environment_random_draws=264, initial_spawns=2), seconds=0.)


def test_cross_phase_memory_uses_previous_predictions_and_keeps_partial_block(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'SOURCE_GAMES', 2)
    monkeypatch.setattr(m, 'CHECKPOINTS', {name: (2,) for name, _ in m.PHASES})
    monkeypatch.setattr(m, 'run_episode', fake_source)
    def evaluate(method, payload, template, life, phase_index, after_game, replica, query):
        row = dict(method=method, query=query, replica=replica,
            seed=115900000 + life * 100000 + phase_index * 10000 + after_game * 100 + replica,
            result=dict(score=0, utility=0., status='LOST', steps=0,
                environment_counts={}, planning_counts={}, seconds=0., p4_used=.1))
        return row, row
    monkeypatch.setattr(m, 'evaluation_game', evaluate)
    result = m.lifecycle_run(0, tmp_path, rule().to_payload())
    assert all(result['checks'].values())
    rows = [row for phase in result['phases'] for row in phase['predictions']]
    assert len(rows) == 780 and [row['observation_index'] for row in rows] == list(range(1, 781))
    assert all(p['p4'] == .5 for p in rows[0]['methods'].values())
    assert all(p['p4'] == 2/3 for p in rows[1]['methods'].values())
    assert rows[260]['methods']['LIBRARY'] == rows[259]['methods']['LIBRARY']
    events = [e for phase in result['phases'] for e in phase['module_events']]
    assert [e['observation_index'] for e in events] == [256] + list(range(320, 781, 64))
    library = result['final_models']['LIBRARY']
    assert library['pending']['n'] == 12 and library['observations_seen'] == 780
    assert sum(len(ph['checkpoints'][0]['evaluations']) for ph in result['phases']) == 60
    assert json.loads((tmp_path / 'life_0/lifecycle.json').read_text()) == result


def test_learned_rule_uses_observation_posterior_not_hidden_environment_parameter(monkeypatch):
    memory = m.SpawnMemory('FROZEN')
    for rank in [1] * 8 + [2] * 2:
        memory.observe(rank)
    payload = memory.to_payload(); before = deepcopy(payload)
    captured = []
    def choose(board, query, knowledge, learned, rng, depth, work):
        captured.append(dict(learned.spawn_distribution)[2])
        assert learned.program == rule().program and knowledge is None and depth == 2
        return dict(action='LEFT', value=0., metrics={})
    def episode(seed, action_fn, p_four, max_steps):
        assert p_four == .3
        assert action_fn((1, 1) + (0,) * 14, 0) == 'LEFT'
        return dict(return_score=2048, status='LOST', steps_count=1, work={'sampled_transitions': 1}, seconds=0.)
    monkeypatch.setattr(m.planner, 'choose', choose)
    monkeypatch.setattr(m, 'run_episode', episode)
    result, _ = m.evaluation_game('FROZEN', payload, rule(), 0, 1, 1, 0, 'risk_goal')
    assert captured == [Fraction(1, 4)] and result['result']['p4_used'] == .25
    assert result['result']['utility'] == -3 and payload == before
    m.evaluation_game('KNOWN_PARAMETER', None, rule(), 0, 1, 1, 0, 'reward')
    assert captured[-1] == Fraction(3, 10)


def test_unique_run_does_not_repeat_an_existing_experiment(tmp_path):
    with pytest.raises(FileExistsError):
        m.run(tmp_path)
