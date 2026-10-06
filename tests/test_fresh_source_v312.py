"""Finite SOURCE construction checks; these fixtures are not confirmation games."""
from collections import Counter
from concurrent.futures import Future
import gzip
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from acfqp.science import fresh_source_v312 as source
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.natural_model_revision_v281 import load_sources


class TimingTD:
    def __init__(self, status):
        self.rule = SimpleNamespace(goal_rank=11)
        self.counts, self.updates = Counter(), 0
        self.events, self.chosen, self.status = [], 0, status

    def choose(self, board, query):
        assert query == dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
        step = self.chosen
        self.chosen += 1
        self.events.append(('choose', step, self.updates))
        self.counts['choose_calls'] += 1
        rank = 11 if self.status == 'WON' and step == 2 else step + 1
        return dict(action='LEFT', afterstate=[rank] + [0] * 15,
                    value=float(100 + step + self.updates))

    def update(self, afterstate, target, alpha):
        self.events.append(('update', afterstate[0], target, alpha))
        self.counts['td_updates'] += 1
        self.updates += 1


@pytest.mark.parametrize('status', ['LOST', 'WON', 'CUTOFF'])
def test_action_precedes_previous_update_and_terminal_tail(monkeypatch, status):
    model = TimingTD(status)

    def fake_episode(seed, act, p_four, max_steps):
        assert (seed, p_four, max_steps) == (31201210007, .1, 2000)
        for step in range(3):
            assert act((0,) * 16, step) == 'LEFT'
        return dict(initial_board=[1, 1] + [0] * 14,
            initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
            final_board=[11 if status == 'WON' else 2] + [0] * 15,
            status=status, return_score=12, steps_count=3,
            steps=[dict(action='LEFT', spawned_cell=i + 2, spawned_rank=1, score=4)
                   for i in range(3)],
            work=dict(initial_spawns=2, sampled_transitions=3), seconds=.125)

    monkeypatch.setattr(source, 'run_episode', fake_episode)
    row, raw = source.train_game(model, 2, 7)
    expected = [('choose', 0, 0), ('choose', 1, 0), ('update', 1, 101., .0025),
                ('choose', 2, 1), ('update', 2, 103., .0025)]
    if status == 'LOST':
        expected.append(('update', 3, -4., .0025))
    assert model.events == expected
    assert raw['decision_updates_before'] == [0, 0, 1]
    assert raw['decision_values'] == [100., 101., 103.]
    assert raw['previous_update_targets'] == [None, 101., 103.]
    assert raw['terminal_update_target'] == (-4. if status == 'LOST' else None)
    assert row['terminal_update'] == (status == 'LOST')
    assert row['analytic_terminal'] == (status == 'WON')
    assert row['censored_last_update'] == (status == 'CUTOFF')
    assert row['result']['updates_after'] == (3 if status == 'LOST' else 2)
    assert row['result']['learning_counts'] == dict(choose_calls=3,
                                                  td_updates=model.updates)
    assert raw['actions'] == ['LEFT'] * 3
    assert raw['spawned_cells'] == [2, 3, 4]
    assert raw['scores'] == [4] * 3
    assert row['result']['utility'] == 12 / 2048. + (4 if status == 'WON' else -4 if status == 'LOST' else 0)
    assert row['result']['seconds'] >= .125


@pytest.fixture
def runtime():
    root = source.ROOT / 'reports/fresh_source_v312/test_runtime'
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'finite_worker'
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    yield path


def test_native_worker_starts_zero_and_saves_only_final_sparse_checkpoint(monkeypatch, runtime):
    capsule = json.loads(source.DYNAMICS_CAPSULE.read_text())
    parent = capsule['snapshots'][0]
    monkeypatch.setattr(source, 'TRAIN_EPISODES', 2)
    monkeypatch.setattr(source, 'BLOCK_SIZE', 1)
    monkeypatch.setattr(source, 'MAX_STEPS', 24)
    lifecycle = source._run_parent(parent, runtime)
    q = lifecycle['queries']['risk_goal']
    checkpoints = list(runtime.rglob('*.npz'))
    assert len(checkpoints) == 1 and checkpoints[0].name == 'checkpoint_2.npz'
    assert q['initial_updates'] == 0 and q['initial_nonzero_parameters'] == 0
    assert q['setup_counts']['zero_initialized_weight_parameters'] == 4 * 11 ** 6
    assert q['setup_counts']['allocated_weight_parameters'] == 4 * 11 ** 6
    assert q['references'] == []
    with gzip.open(runtime / q['training_trace'], 'rt') as stream:
        traces = [json.loads(line) for line in stream]
    assert [row['seed'] for row in traces] == [31201010000, 31201010001]
    assert all(row['result']['status'] == 'CUTOFF' for row in traces)
    assert traces[0]['decision_values'][0] == traces[0]['scores'][0] / 2048.
    assert traces[0]['decision_updates_before'][:3] == [0, 0, 1]
    assert q['final_updates'] == sum(row['result']['steps'] - 1 for row in traces) == 46
    blocks = q['training_blocks']
    assert [b['end'] for b in blocks] == [1, 2]
    assert sum(b['games'] for b in blocks) == 2
    environment = sum((Counter(b['environment_counts']) for b in blocks), Counter())
    assert environment['initial_spawns'] + environment['sampled_transitions'] == 52
    checkpoint = q['checkpoints'][0]
    assert checkpoint['save_counts'] == dict(checkpoint_saves=1,
        checkpoint_scanned_parameters=4 * 11 ** 6,
        checkpoint_saved_parameters=checkpoint['nonzero_weights'])
    assert checkpoint['nonzero_weights'] > 0
    with np.load(checkpoints[0], allow_pickle=False) as saved:
        metadata = json.loads(str(saved['metadata']))
        assert saved['indices'].size == saved['values'].size == checkpoint['nonzero_weights']
        assert metadata['updates'] == 46
        assert metadata['setup_counts']['zero_initialized_weight_parameters'] == 4 * 11 ** 6
    restored = NtupleValue.load(checkpoints[0], LearnedDynamics.from_payload(parent['rule']),
                                runtime / 'restore_build')
    assert restored.updates == 46
    assert np.count_nonzero(restored.weights) == checkpoint['nonzero_weights']
    receipt = lifecycle['fresh_source_compute']
    assert receipt['worker_cpu_seconds'] >= receipt['setup_cpu_seconds'] + receipt['checkpoint_save_cpu_seconds'] > 0
    assert receipt['compiler_cpu_seconds'] > 0
    assert receipt['wall_seconds'] > 0


def test_publication_loads_only_capsule_and_closes_cost_ledger(monkeypatch, tmp_path):
    capsule = json.loads(source.DYNAMICS_CAPSULE.read_text())
    dynamics_input = tmp_path / 'dynamics_only.json'
    dynamics_input.write_text(json.dumps(capsule))
    output = tmp_path / 'fresh_source'
    submitted = []

    def worker(parent, directory):
        life = parent['life']
        submitted.append(life)
        return dict(life=life, queries=dict(risk_goal=dict(
            training_blocks=[dict(start=0, end=4096, games=4096,
                environment_counts=dict(initial_spawns=8192, sampled_transitions=life + 10),
                learning_counts=dict(td_updates=life + 3), seconds=life + .5)],
            setup_counts=dict(allocated_weight_parameters=4 * 11 ** 6,
                              zero_initialized_weight_parameters=4 * 11 ** 6),
            setup_seconds=.1, checkpoints=[dict(episodes=4096,
                model_file=f'life_{life}/risk_goal/checkpoint_4096.npz', updates=life + 3,
                save_counts=dict(checkpoint_saves=1), save_seconds=.2)])),
            fresh_source_compute=dict(worker_cpu_seconds=life + 1., compiler_cpu_seconds=.25,
                wall_seconds=life + 2., setup_cpu_seconds=.1, checkpoint_save_cpu_seconds=.2))

    class InlinePool:
        def __init__(self, max_workers):
            assert max_workers == 4

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, function, *args):
            future = Future()
            future.set_result(function(*args))
            return future

    monkeypatch.setattr(source, '_run_parent', worker)
    monkeypatch.setattr(source, 'ProcessPoolExecutor', InlinePool)
    summary = source.run(dynamics_input, output)
    assert submitted == [0, 1, 2, 3]
    config = summary['settings']
    assert config['seed_base'] == 31200000000
    assert config['games_per_parent'] == 4096 and config['checkpoints'] == [4096]
    assert config['alpha'] == .0025 and config['max_steps'] == 2000
    assert config['query'] == dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
    assert config['p_four'] == .1 and config['initialization'] == 'ZERO_NTUPLE_WEIGHTS'
    assert source.training_seed(3, 4095) == 31201314095
    published = load_sources(output)
    assert len(published['parents']) == 4
    assert all(p['checkpoint'].startswith(str(output)) for p in published['parents'])
    assert [p['updates'] for p in published['parents']] == [3, 4, 5, 6]
    assert json.loads((output / 'source_capsule.json').read_text()) == capsule
    costs = summary['accounting']['inherited_costs_per_arm']['SOURCE']
    assert costs['source_training_games'] == 16384
    assert costs['source_training_raw_tiles'] == 4 * 8192 + 46
    assert costs['source_training_environment_counts'] == dict(initial_spawns=32768,
                                                               sampled_transitions=46)
    assert costs['source_training_seconds'] == 8.
    assert costs['dynamics_raw_tiles'] == 49069
    assert costs['dynamics_costs'] == capsule['inherited_costs']
    compute = costs['fresh_source_compute']
    assert compute['worker_cpu_seconds'] == 10.
    assert compute['compiler_cpu_seconds'] == 1.
    assert compute['full_source_cpu_seconds'] == 11. + compute['coordinator_cpu_seconds']
    assert compute['includes_source_setup_training_checkpoint_save'] is True
    assert summary['status'] == 'SOURCE_COMPLETE'
    assert json.loads((output / 'source_summary.json').read_text()) == summary
    with pytest.raises(FileExistsError):
        source.run(dynamics_input, output)
