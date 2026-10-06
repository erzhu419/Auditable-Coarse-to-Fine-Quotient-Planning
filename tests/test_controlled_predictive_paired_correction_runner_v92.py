"""Prevent duplicate acquisition and reference leakage at runner boundaries."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('paired_runner_v92',
    ROOT / 'scripts/run_controlled_predictive_paired_correction_v92.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_cumulative_prefix_reuse_frozen_head_and_inherited_cost(monkeypatch, tmp_path):
    acquired, fitted, evaluated = [], [], []

    class Selector:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        def to_payload(self):
            return {'checkpoint': self.checkpoint}

        @classmethod
        def from_payload(cls, payload):
            return cls(payload['checkpoint'])

    def load(folder):
        episode = int(folder.name.split('_')[-1]) - 1
        return [dict(episode=episode, query='reward', board=[episode] * 16,
            censored=False)], [dict(episode=episode)], {'counts': {}}

    def fit_models(rows, checkpoint):
        assert [row['episode'] for row in rows] == ([5] if checkpoint == 6 else [5, 11])
        return {name: Selector(checkpoint) for name in ('full', 'fold_0', 'fold_1')}, {}

    def acquire(roots, rule, life, folder):
        acquired.extend(root['episode'] for root in roots)
        return {MODULE.root_key(root): root['episode'] for root in roots}, {}

    def fit_heads(roots, pools, models, checkpoint):
        fitted.append((checkpoint, [root['episode'] for root in roots], sorted(pools.values())))
        return {name: Selector(checkpoint) for name in ('MC', 'PAIR_ONLY', 'CORRECTED')}, {}, {}

    def evaluate(life, checkpoint, folder, deployed, rule):
        evaluated.append({name: model.checkpoint if model else None for name, model in deployed.items()})
        return {'methods': {}}, [], []

    old = tmp_path / 'old' / 'life_0'
    old.mkdir(parents=True)
    for checkpoint in (6, 12):
        (old / f'checkpoint_{checkpoint}').mkdir()
        MODULE.save(old / f'checkpoint_{checkpoint}' / 'decomposed_selector.json',
                    {'checkpoint': checkpoint + 100})
    MODULE.save(old / 'run.json', {'checkpoints': [dict(episodes=cp,
        updates={'DECOMPOSED': {'counts': {'tree_fits': 8}, 'seconds': cp}}) for cp in (6, 12)]})
    monkeypatch.setattr(MODULE, 'SOURCE_V91', old.parent)
    monkeypatch.setattr(MODULE, 'load_batch', load)
    monkeypatch.setattr(MODULE, 'fit_models', fit_models)
    monkeypatch.setattr(MODULE, 'acquire_prefix_batch', acquire)
    monkeypatch.setattr(MODULE, 'fit_selectors', fit_heads)
    monkeypatch.setattr(MODULE, 'JointSelector', Selector)
    monkeypatch.setattr(MODULE, 'evaluate_checkpoint', evaluate)
    monkeypatch.setattr(MODULE, 'validate_roots', lambda *args: {'roots': []})
    monkeypatch.setattr(MODULE, 'LearnedDynamics', SimpleNamespace(from_payload=lambda payload: None))
    prior = {'checkpoints': [dict(episodes=cp,
        source=dict(work={'sampled_transitions': cp}, games=12),
        branches=dict(work={'sampled_transitions': cp * 10}, trajectories=480)) for cp in (6, 12)]}
    result = MODULE.lifecycle_run(0, tmp_path, {}, prior)
    assert acquired == [5, 11]
    assert fitted == [(6, [5], [5]), (12, [5, 11], [5, 11])]
    assert evaluated[0]['V91_DECOMPOSED'] == 106
    assert evaluated[1] == dict(H2_ONLY=None, MC=12, V91_DECOMPOSED=112,
        PAIR_ONLY=12, CORRECTED=12, CORRECTED_FROZEN_6=6)
    assert result['inherited']['source_work']['sampled_transitions'] == 18
    assert result['inherited']['branch_work']['sampled_transitions'] == 180
    assert sum(item['counts']['tree_fits'] for item in result['inherited']['v91_decomposed_fits']) == 16


@pytest.mark.parametrize('censored_replica', [None, 0, 8])
def test_independent_reference_split_keeps_each_censoring_status(monkeypatch, tmp_path, censored_replica):
    root = dict(life=1, query='reward', episode=0, board=[1] * 16)
    calls = []

    def prefix(option, replica, short=False):
        target = [0 if option == 'H2' else (10 if replica < 8 else 100), 0, 0]
        return dict(option=option, replica=replica, direct=[0, 0, 0],
            boundary_board=[0] * 16, status='ACTIVE',
            full_target=None if short or (option == 'SPACE_1' and replica == censored_replica) else target)

    def full_sample(sample, rule, life, replicas):
        calls.append(('full', life, replicas))
        raw = [prefix(option, replica) for replica in range(replicas) for option in MODULE.OPTIONS]
        return [], raw, {'ground_work': {'sampled_transitions': 123}}

    def short_sample(sample, rule, seed_base, replicas):
        calls.append(('short', seed_base, replicas))
        values = {option: [prefix(option, replica, True) for replica in range(replicas)]
                  for option in MODULE.OPTIONS}
        return values, [], {'ground_work': {'sampled_transitions': 456}}

    class Model:
        def predict_pair(self, *args):
            return [0, 0, 0]

    monkeypatch.setattr(MODULE, 'sample_root', full_sample)
    monkeypatch.setattr(MODULE, 'collect_prefixes', short_sample)
    monkeypatch.setattr(MODULE, 'extract_prefix', lambda row: row)
    result = MODULE.validate_roots([root], [], tmp_path, None, {}, Model())['roots'][0]
    assert calls == [('full', 92001, 24), ('short', 93010000000, 64)]
    assert MODULE.prefix_seed(root, 1) != calls[1][1]
    assert result['estimates']['complete'] == (censored_replica != 0)
    assert result['reference_complete'] == (censored_replica != 8)
    if result['estimates']['complete']:
        assert result['estimates']['estimates']['MC']['SPACE_1'] == [10, 0, 0]
        assert result['estimates']['details']['SPACE_1']['full_replicas'] == list(range(8))
    if result['reference_complete']:
        assert result['reference']['SPACE_1'] == [[100, 0, 0]] * 16
