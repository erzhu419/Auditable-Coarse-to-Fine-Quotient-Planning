"""Detect observation leakage, cross-bank TD, eval contamination and wrong budgets."""
from collections import Counter
from copy import deepcopy
import gzip
import io
import json
from types import SimpleNamespace
import pytest

from scripts import run_controlled_predictive_context_bank_v122 as runner


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before = request.session.testsfailed
    yield
    path = runner.ROOT / 'reports/controlled_predictive_context_bank_runner_v122.checks.json'
    value = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    value['attempts'].append(dict(failures=request.session.testsfailed-before,
        environment_samples=0, model_samples=0, fits=0,
        scope='mocked causal trajectories, synthetic TD calls, exact budgets, checkpoint reuse and source extraction'))
    path.write_text(json.dumps(value, indent=2)+'\n')


class FakeValue:
    def __init__(self, rule=None, build_dir=None, updates=100, terminal=False):
        self.rule = rule or SimpleNamespace(goal_rank=11)
        self.counts, self.updates, self.events = Counter(), updates, []
        self.setup_counts, self.setup_seconds = Counter(allocated_weight_bytes=8), .1
        self.terminal = terminal

    @classmethod
    def load(cls, path, rule, build_dir):
        model = cls(rule, build_dir)
        model.last_load_seconds = .3
        return model

    def choose(self, board, query):
        self.events.append(('choose', board[0], self.updates))
        self.counts['choose_calls'] += 1
        afterstate = [11 if self.terminal and board[0] == 5 else board[0]+1] + [0]*15
        return dict(action='LEFT', afterstate=afterstate, value=board[0]*10+self.updates)

    def update(self, board, target, alpha):
        self.events.append(('update', board[0], target, alpha))
        self.updates += 1; self.counts['td_updates'] += 1


class FakeBank(FakeValue):
    def __init__(self, source, ranks, build_dir, switch_at=257):
        super().__init__(source.rule, build_dir, source.updates, source.terminal)
        self.router = SimpleNamespace(observations_seen=256, counts=Counter(observations_received=256))
        self.router.to_payload = lambda: dict(observations_seen=self.router.observations_seen,
            active_module_id=self.active_bank_id)
        self.active_bank_id, self.switch_at = 0, switch_at
        self.banks = {0: source}
        self.setup_counts, self.setup_seconds = Counter(), 0.

    def observe(self, rank):
        self.events.append(('observe', rank))
        self.router.observations_seen += 1
        self.counts['router_observations_received'] += 1
        if self.router.observations_seen == self.switch_at:
            self.active_bank_id = 1
            self.banks[1] = self.banks[0]
            return dict(kind='created', module_id=1, previous_module_id=0)

    def choose(self, board, query):
        return dict(super().choose(board, query), bank_id=self.active_bank_id)

    def update_pending(self, afterstate, bank_id, target, alpha):
        if bank_id != self.active_bank_id:
            self.events.append(('skip', afterstate[0]))
            self.counts['cross_context_update_skips'] += 1
            return False
        self.update(afterstate, target, alpha)
        return True

    def evaluation_copy(self):
        result = deepcopy(self)
        result.counts = Counter(evaluation_weight_views=len(self.banks))
        return result

    def to_payload(self):
        return dict(router=self.router.to_payload(), updates=self.updates,
            banks=[dict(bank_id=key) for key in self.banks])

    def save(self, directory):
        path = directory / 'bank_0.npz'; path.write_text(str(self.updates))
        self.counts['checkpoint_saves'] += 1
        return dict(self.to_payload(), model_files=[dict(path=str(path), bytes=path.stat().st_size)])


def fake_episode(status='LOST', calls=None):
    def run(seed, action, p4, max_steps):
        if calls is not None:
            calls.append((seed, p4, max_steps))
        steps, board = [], [3, 1]+[0]*14
        initial = list(board)
        for index in range(min(3, max_steps)):
            assert action(board, index) == 'LEFT'
            end = 11 if status == 'WON' and index == 2 else board[0]+1
            board = [end, 1]+[0]*14
            steps.append(dict(action='LEFT', spawned_cell=1, spawned_rank=1, score=4))
        actual = 'CUTOFF' if max_steps < 3 else status
        return dict(initial_board=initial,
            initial_spawns=[dict(cell=0, rank=1), dict(cell=1, rank=1)],
            final_board=board, return_score=4*len(steps), status=actual,
            steps_count=len(steps), steps=steps,
            work=dict(sampled_transitions=len(steps), initial_spawns=2), seconds=0.)
    return run


@pytest.mark.parametrize('status', ['LOST', 'WON', 'CUTOFF'])
def test_causal_observation_before_choice_and_cross_context_skip(monkeypatch, status):
    monkeypatch.setattr(runner, 'run_episode', fake_episode(status))
    model = FakeBank(FakeValue(terminal=status == 'WON'), [1]*256, '.')
    row, raw = runner.td_game(model, 1, 'risk_goal', 'B', 'BANK', episode=3)
    assert model.events[:6] == [('choose', 3, 100), ('observe', 1), ('choose', 4, 100),
        ('skip', 4), ('observe', 1), ('choose', 5, 100)]
    assert raw['bank_ids'] == [0, 1, 1] and raw['cross_context_skips'] == [0]
    assert raw['routing_events'][0]['observed_action_index'] == 0
    assert row['result']['router_observations_after'] == 259
    assert raw['final_bank_id'] == 1
    assert row['result']['learning_counts']['router_observations_received'] == 3
    assert model.updates == (102 if status == 'LOST' else 101)
    assert row['terminal_update'] == (status == 'LOST')
    assert model.events[-1] == (('update', 6, -4., .0025) if status == 'LOST' else ('observe', 1))


def test_final_spawn_can_censor_terminal_td(monkeypatch):
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    model = FakeBank(FakeValue(), [1]*256, '.', switch_at=259)
    row, raw = runner.td_game(model, 0, 'reward', 'B', 'BANK', episode=0)
    assert row['terminal_update_attempted'] and not row['terminal_update']
    assert raw['cross_context_skips'] == [2] and model.updates == 102
    assert raw['bank_ids'] == [0, 0, 0] and raw['final_bank_id'] == 1


def test_evaluation_router_clones_are_discarded_and_initial_views_charged(monkeypatch):
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    monkeypatch.setattr(runner, 'REPLICAS', 2)
    model = FakeBank(FakeValue(), [1]*256, '.')
    stream = io.StringIO()
    rows = runner.evaluate(model, 0, 'reward', 'B', 'BANK', 0, stream)
    assert model.router.observations_seen == 256 and model.active_bank_id == 0
    assert model.updates == 100 and model.events == [] and model.counts == {}
    for row in rows:
        assert row['result']['router_observations_before'] == 256
        assert row['result']['router_observations_after'] == 259
        assert row['result']['learning_counts']['evaluation_weight_views'] == 1
        assert row['result']['updates_before'] == row['result']['updates_after'] == 100


def test_exact_transition_budget_and_phase_carry(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    monkeypatch.setattr(runner, 'TRAIN_TRANSITIONS', 8)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 4, 8))
    monkeypatch.setattr(runner, 'REPLICAS', 1)
    model = FakeBank(FakeValue(), [1]*256, '.')
    result = dict(training_blocks=[], checkpoints=[dict(model_ref='/source.npz')])
    train, control = io.StringIO(), io.StringIO()
    runner.train_phase(model, 0, 'reward', 'B', result, tmp_path, tmp_path,
        train, control, lambda: None)
    rows = [json.loads(line) for line in train.getvalue().splitlines()]
    assert [row['transitions_after'] for row in rows] == [3, 6, 8]
    assert [cp['transitions'] for cp in result['checkpoints'][1:]] == [6, 8]
    assert result['final_updates'] == 106 and model.router.observations_seen == 264
    assert rows[-1]['censored_last_update']
    assert [cp['bank_manifest']['router']['observations_seen'] for cp in result['checkpoints'][1:]] == [262, 264]


def test_lifecycle_runs_only_bank_training_and_correct_physical_roster(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'NtupleValue', FakeValue)
    monkeypatch.setattr(runner, 'ContextValueBank', FakeBank)
    monkeypatch.setattr(runner, 'LearnedDynamics', SimpleNamespace(from_payload=lambda _: SimpleNamespace(goal_rank=11)))
    monkeypatch.setattr(runner, 'run_episode', fake_episode())
    monkeypatch.setattr(runner, 'TRAIN_TRANSITIONS', 8)
    monkeypatch.setattr(runner, 'CHECKPOINTS', (0, 4, 8))
    monkeypatch.setattr(runner, 'REPLICAS', 1)
    monkeypatch.setattr(runner, 'QUERIES', {'reward': runner.QUERIES['reward']})
    source_model = dict(path='/retained.npz', updates=100, nonzero_weights=1)
    source = dict(life=0, rule={}, models=dict(reward=source_model),
        initial_ranks=dict(reward=[1]*256), initial_rank_sources=dict(reward={}),
        continued=dict(reward={phase:[dict(source_model, label=label, transitions=label)
            for label in runner.CHECKPOINTS] for phase in runner.PHASES}))
    result = runner.lifecycle_run(source, tmp_path)['queries']['reward']
    b, a = [result['phases'][phase]['methods'] for phase in runner.PHASES]
    assert b['BANK']['final_updates'] == 106 and a['BANK']['final_updates'] == 113
    assert a['BANK']['checkpoints'][0]['model_ref'] == b['BANK']['checkpoints'][-1]['model_ref']
    assert a['BANK']['checkpoints'][0]['bank_manifest']['router']['observations_seen'] == 264
    with gzip.open(tmp_path / result['control_trace'], 'rt') as stream:
        physical = [json.loads(line) for line in stream]
    with gzip.open(tmp_path / result['training_trace'], 'rt') as stream:
        training = [json.loads(line) for line in stream]
    logical = [row for phase in (b, a) for method in phase.values()
        for cp in method['checkpoints'] for row in cp['evaluations']]
    assert len(physical) == 13 and len(logical) == 14
    assert len(training) == 6 and all(row['method'] == 'BANK' for row in training)
    assert sum(row['reused_from'] is not None for row in logical) == 1


def test_source_reads_256_ranks_and_excludes_reset_and_outer(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, 'LIVES', (0,))
    monkeypatch.setattr(runner, 'SOURCE_V120', tmp_path)
    monkeypatch.setattr(runner, 'SOURCE', tmp_path / 'v121')
    models = {}
    for query in runner.QUERIES:
        folder = tmp_path / 'life_0' / query; folder.mkdir(parents=True)
        with gzip.open(folder / 'training.jsonl.gz', 'wt') as stream:
            stream.write(json.dumps(dict(spawned_ranks=[1]*200))+'\n')
            stream.write(json.dumps(dict(spawned_ranks=[2]*100))+'\n')
        models[query] = dict(path='/v120.npz', updates=100, nonzero_weights=1)
    def method(phase):
        return dict(training_blocks=[dict(games=1)], final_updates=107, final_transitions=8,
            training_episodes=3, checkpoints=[
                dict(label=0, transitions=0, updates=100,
                    model_ref='/v120.npz' if phase == 'B' else 'B_final.npz', evaluations='EXCLUDE_OUTER'),
                dict(label=524288, transitions=8, updates=107, model_ref=f'{phase}_final.npz',
                    model_metadata=dict(nonzero_weights=7), save_counts={'checkpoint_saves':1}, save_seconds=.2)])
    value = dict(model_setup=[dict(method='CONT'), dict(method='RESET', detail='EXCLUDE_RESET')],
        phases={phase:dict(methods=dict(CONT=method(phase), RESET='EXCLUDE_RESET')) for phase in runner.PHASES})
    previous = dict(inherited_costs={'prior':1}, lifecycles=[dict(life=0,
        queries={query:deepcopy(value) for query in runner.QUERIES})])
    capsule = runner.extract_source(previous, dict(snapshots=[dict(life=0, rule={}, models=models)]))
    source = capsule['snapshots'][0]
    assert source['initial_ranks']['reward'] == [1]*200+[2]*56
    assert source['initial_rank_sources']['reward']['rows_read'] == 2
    assert source['continued']['reward']['A_RETURN'][0]['nonzero_weights'] == 7
    assert 'EXCLUDE' not in json.dumps(capsule)
    assert capsule['inherited_costs']['shared_v120'] == {'prior':1}


def test_fresh_evaluations_and_training_seed_pairing():
    from scripts.run_controlled_predictive_ntuple_regime_v121 import train_seed as old_seed
    assert runner.train_seed(2, 'risk_goal', 'A_RETURN', 13) == old_seed(2, 'risk_goal', 'A_RETURN', 13)
    outer = {runner.evaluation_seed(life, phase, replica) for life in runner.LIVES
        for phase in runner.PHASES for replica in range(runner.REPLICAS)}
    assert len(outer) == 64 and min(outer) > 122 * 100_000_000
    assert max(outer) < 123 * 100_000_000
