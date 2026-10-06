"""Incremental data isolation, frozen deployment and independent-return accounting."""
from collections import Counter
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('bellman_runner_v94', ROOT / 'scripts/run_controlled_predictive_bellman_v94.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_incremental_training_and_frozen_heads_never_receive_evaluation(monkeypatch, tmp_path):
    class Selector:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        def to_payload(self):
            return dict(checkpoint=self.checkpoint)

        @classmethod
        def from_payload(cls, payload):
            return cls(payload['checkpoint'])

    source = tmp_path / 'source'
    life_dir = source / 'life_3'
    prior, observed, evaluated = [], [], []
    for checkpoint in (6, 12):
        directory = life_dir / f'checkpoint_{checkpoint}'
        directory.mkdir(parents=True)
        costs = {name: {'total_training_transitions': checkpoint * 100} for name in
                 ('MC', 'MC_EXTRA', 'V91_DECOMPOSED', 'CORRECTED', 'H2_ONLY')}
        for name in ('mc', 'mc_extra', 'v91_decomposed', 'corrected'):
            M.save(directory / f'{name}_selector.json', dict(checkpoint=checkpoint))
        prior.append(dict(episodes=checkpoint, source={'work': {'sampled_transitions': 10}},
            branches={'work': {'sampled_transitions': 100}}, method_acquisition=costs,
            updates={'counts': {'tree_fits': 20}, 'mc_extra': {'counts': {'tree_fits': 2}}}))
    M.save(life_dir / 'run.json', {'checkpoints': prior})

    def load(folder):
        episode = int(folder.name.split('_')[-1]) - 1
        return [dict(episode=episode, censored=False)], [dict(episode=episode)], {}

    def fit(rows, checkpoint, iterations):
        observed.append((checkpoint, [row['episode'] for row in rows], iterations))
        return {name: {'full': Selector(checkpoint)} for name in M.VALUE_METHODS}, {'counts': {'tree_fits': 0}}

    def heads(roots, models, checkpoint):
        assert [row['episode'] for row in roots] == ([5] if checkpoint == 6 else [5, 11])
        return {name: Selector(checkpoint) for name in M.VALUE_METHODS}, {}, {'counts': {'tree_fits': 0}}

    def evaluate(life, checkpoint, folder, deployed, rule):
        evaluated.append({name: selector.checkpoint if selector else None for name, selector in deployed.items()})
        return {'methods': {}}, [{'evaluation_only': True}], []

    monkeypatch.setattr(M, 'SOURCE', source)
    monkeypatch.setattr(M, 'JointSelector', Selector)
    monkeypatch.setattr(M, 'LearnedDynamics', SimpleNamespace(from_payload=lambda payload: None))
    monkeypatch.setattr(M, 'load_batch', load)
    monkeypatch.setattr(M, 'fit_models', fit)
    monkeypatch.setattr(M, 'fit_heads', heads)
    monkeypatch.setattr(M, 'evaluate_checkpoint', evaluate)
    monkeypatch.setattr(M, 'validate_roots', lambda *args: {'roots': args[0]})
    result = M.lifecycle_run(3, tmp_path, {})
    assert observed == [(6, [5], 128), (12, [5, 11], 128)]
    assert evaluated[-1]['MC_TAIL_FROZEN_6'] == evaluated[-1]['FQE_FROZEN_6'] == 6
    assert evaluated[-1]['MC_TAIL'] == evaluated[-1]['FQE'] == 12
    assert evaluated[-1]['V92_CORRECTED'] == 12
    final = result['checkpoints'][-1]
    assert final['method_acquisition']['FQE']['total_training_transitions'] == 1200
    assert final['method_acquisition']['FQE_FROZEN_6']['total_training_transitions'] == 600
    assert final['inherited_acquisition']['source']['sampled_transitions'] == 10
    assert final['new_training_environment_transitions'] == 0


def test_fresh_natural_streams_remain_paired(monkeypatch):
    calls = []

    class Controller:
        def __init__(self, selector, query, rule, rng, mode):
            self.work, self.events = {}, []
            self.fragment_actions = 0
            self.selected_option = self.initiation_step = None
            self.rng = rng

    def episode(seed, act, max_steps):
        controller = act.__closure__[0].cell_contents
        calls.append((seed, controller.rng.random()))
        return dict(return_score=0, status='CUTOFF', steps_count=0, final_board=[1] * 16,
                    seconds=0, work={}, steps=[])

    monkeypatch.setattr(M, 'FragmentController', Controller)
    monkeypatch.setattr(M.experience, 'run_episode', episode)
    for checkpoint, method in ((6, 'FQE'), (12, 'FQE'), (12, 'MC_TAIL')):
        M.evaluate_game(method, SimpleNamespace(checkpoint=checkpoint), None, 3, checkpoint, 0, 'reward')
    assert calls[0][0] == 9550300 and calls[1][0] == 9610300
    assert calls[1] == calls[2] and calls[0][1] != calls[1][1]


def test_reference_separates_prefix_terminal_event_and_active_tail(monkeypatch):
    monkeypatch.setattr(M, 'REFERENCE_REPLICAS', 1)
    raw = []
    for option in M.OPTIONS:
        length, status = (2, 'LOST') if option == 'H2' else (5, 'WON')
        raw.append(dict(option=option, replica=0, game=dict(status=status, return_score=2048 * length,
            initial_board=[0] * 16, steps=[dict(score=2048, status=status if i == length - 1 else 'ACTIVE',
            next_board=[i + 1] * 16) for i in range(length)])))
    calls = []

    class Model:
        def predict(self, board, query, work):
            calls.append(board)
            return [1.5, .25, .75]

    models = {name: Model() for name in M.VALUE_METHODS}
    root = dict(query='reward', episode=0, life=3)
    record = M.validation_record(root, raw, {}, {}, models, Counter())
    assert record['reference_complete'] and record['active_boundaries'] == 4
    assert len(calls) == 8 and len(record['value_records']) == 4
    assert record['value_records'][0]['remaining_target'] == [1, 0, 1]
    assert record['reconstruction'][0]['Y'] == [3, -1, 1]
    assert record['reconstruction'][0]['Z']['FQE'] == [3.5, -.75, .75]
    raw[1]['game']['status'] = 'CUTOFF'
    record = M.validation_record(root, raw, {}, {}, models, Counter())
    assert not record['reference_complete'] and record['paired_reference'] == {}
    assert record['reconstruction'] == [] and len(record['value_records']) == 3
