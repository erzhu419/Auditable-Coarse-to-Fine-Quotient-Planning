"""V130 scheduling, paired labels and train/holdout isolation with mocks."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_controlled_predictive_paired_ntuple_v130 as runner

ROOT = Path(__file__).resolve().parents[1]
BOARD = [1, 1]+[0]*14
OTHER = [2, 0, 1]+[0]*13


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    before, started = request.session.testsfailed, perf_counter()
    yield
    path = ROOT/'reports/controlled_predictive_paired_ntuple_v130.runner_checks.json'
    log = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    log['attempts'].append(dict(tests=sum(i.module.__name__ == __name__ for i in request.session.items),
        failures=request.session.testsfailed-before, seconds=perf_counter()-started,
        newly_sampled_environment_transitions=0, environment_random_draws=0,
        native_model_calls=0, optimizer_steps=0,
        scope='Synthetic labels and mocked acquisition, fitting and phase execution; no native or environment calls'))
    path.write_text(json.dumps(log, indent=2)+'\n')


def choice():
    values = dict(DOWN=dict(afterstate=OTHER, score=4, value=13.),
        LEFT=dict(afterstate=BOARD, score=0, value=10.))
    return dict(action='LEFT', **values['LEFT'], action_values=values, status='ACTIVE')


def case(life, query, episode, index, available=True):
    return dict(root_id=runner.slot_id(life, query, episode, index), life=life, query=query,
        episode=episode, index=index, split='TRAIN' if episode < 12 else 'HOLDOUT',
        available=available, board=BOARD if available else None,
        parent=runner.prediction(choice()) if available else None,
        actions=['DOWN', 'LEFT'] if available else [])


def test_seed_namespaces_and_episode_slots_are_paired_disjoint_and_fixed():
    acquisition = {runner.source_seed(life, episode) for life in runner.LIVES for episode in range(16)}
    evaluation = {runner.evaluation_seed(life, replica) for life in runner.LIVES for replica in range(16)}
    suffix = {runner.suffix_seed(root, replica) for root in range(512) for replica in range(8)}
    assert (len(acquisition), len(evaluation), len(suffix)) == (64, 64, 4096)
    assert not acquisition & evaluation and not acquisition & suffix and not evaluation & suffix
    slots = [runner.slot_id(life, query, episode, index) for life in runner.LIVES
        for query in runner.QUERIES for episode in range(16) for index in runner.ROOT_INDICES]
    assert slots == list(range(512))
    train = {runner.suffix_seed(root, replica) for root in slots if root % 64 < 48 for replica in range(8)}
    heldout = suffix-train
    assert len(train) == 384*8 and len(heldout) == 128*8 and not train & heldout
    assert runner.source_seed(2, 3) == runner.BASE+10000000+200000+3
    assert runner.evaluation_seed(2, 3) == runner.BASE+90000000+200000+3
    assert runner.suffix_seed(511, 7) == runner.BASE+50000000+511000+7


def test_short_acquisition_keeps_missing_slots_without_replacement(tmp_path, monkeypatch):
    calls = []
    class Parent:
        counts = Counter()
        def choose(self, board):
            self.counts['choose_calls'] += 1
            return choice()
    def game(parent, life, query, method, episode, acquisition=False):
        calls.append((query, episode, acquisition))
        n = 129 if episode == 0 else 0
        return dict(query=query, episode=episode), dict(steps_count=n, steps=[dict(board=BOARD)]*n)
    monkeypatch.setattr(runner, 'EPISODES', 2)
    monkeypatch.setattr(runner, 'TRAIN_EPISODES', 1)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Parent(), {}))
    monkeypatch.setattr(runner, 'full_game', game)
    data = runner.prepare_lifecycle(dict(life=0), tmp_path)
    assert calls == [(q, e, True) for q in runner.QUERIES for e in range(2)]
    assert len(data['cases']) == 16 and sum(r['available'] for r in data['cases']) == 2
    assert all(r['index'] == 128 and r['episode'] == 0 for r in data['cases'] if r['available'])
    assert all(r['board'] is None and r['parent'] is None and r['actions'] == []
        for r in data['cases'] if not r['available'])
    assert all(r['split'] == ('TRAIN' if r['episode'] == 0 else 'HOLDOUT') for r in data['cases'])
    with gzip.open(tmp_path/data['trace'], 'rt') as stream:
        assert len(list(stream)) == 4


def test_roster_keeps_all_slots_duplicates_and_episode_splits_in_root_order():
    prepared = [dict(life=life, cases=[case(life, query, episode, index, index == 128)
        for query in runner.QUERIES for episode in range(16) for index in runner.ROOT_INDICES])
        for life in reversed(runner.LIVES)]
    roster = runner.assemble_roster(prepared)
    assert [r['root_id'] for r in roster['cases']] == list(range(512))
    assert len(roster['cases']) == 512 and sum(r['available'] for r in roster['cases']) == 128
    assert sum(r['split'] == 'TRAIN' for r in roster['cases']) == 384
    assert all(r['split'] == ('TRAIN' if r['episode'] < 12 else 'HOLDOUT') for r in roster['cases'])
    assert roster['training_branches'] == 96*2*8
    assert roster['heldout_parent_branches'] == 32*2*8
    assert roster['heldout_full_branches'] == 32*8 and roster['control_games'] == 384
    assert len({r['root_id'] for r in roster['cases'] if r['board'] == BOARD}) == 128
    assert runner.assemble_roster(list(reversed(prepared))) == roster
    roster['cases'][0]['actions'].clear()
    assert prepared[-1]['cases'][0]['actions'] == ['DOWN', 'LEFT']


def test_pair_labels_keep_paired_target_separate_from_bases_and_censor_cutoffs():
    root = case(0, 'risk1', 0, 128)
    root['actions'].append('UP')
    root['parent']['action_values']['UP'] = dict(afterstate=[11]+[0]*15, score=2048, value=2.)
    reference = [100.+i*3 for i in range(8)]
    outcomes = {action: [dict(replica=i, result=dict(status='LOST', utility=u+gap))
        for i, (u, gap) in enumerate(zip(reference, gaps))] for action, gaps in
        [('LEFT', [0.]*8), ('DOWN', list(range(1, 9))), ('UP', [-2.]*8)]}
    labels = runner.pair_labels(root, outcomes)
    assert [row['action'] for row in labels] == ['DOWN', 'UP']
    down, up = labels
    assert down['paired_gaps'] == list(range(1, 9)) and down['target_gap'] == 4.5
    assert down['base_gaps'] == dict(PRIOR=3., SCRATCH=4/2048.)
    assert up['target_gap'] == -2. and up['base_gaps'] == dict(PRIOR=-8., SCRATCH=2.)
    outcomes['DOWN'][6]['result']['status'] = 'CUTOFF'
    censored = runner.pair_labels(root, outcomes)
    assert not censored[0]['eligible'] and censored[0]['target_gap'] is None
    assert censored[0]['paired_gaps'] == down['paired_gaps'] and censored[1]['eligible']
    outcomes['LEFT'][0]['result']['status'] = 'CUTOFF'
    assert all(not row['eligible'] for row in runner.pair_labels(root, outcomes))


def test_fit_uses_only_train_complete_pairs_and_freezes_before_predictions(tmp_path, monkeypatch):
    events, models = [], []
    class Parent:
        def __init__(self):
            weights = np.zeros(1); weights.flags.writeable = False
            self.source = SimpleNamespace(weights=weights, updates=42)
            self.updates, self.counts = 42, Counter()
    class Head:
        def __init__(self, parent, kind, build):
            self.parent, self.kind = parent, kind
            self.weights, self.updates = np.zeros(1), 0
            self.counts, self.setup_counts, self.setup_seconds = Counter(), {}, 0.
            models.append(self)
        def fit_pair(self, after_a, after_b, base_gap, target_gap, rate):
            assert self.weights.flags.writeable
            events.append(('fit', self.kind, base_gap, target_gap, rate))
            self.updates += 1; self.counts['pair_fit_calls'] += 1
            return dict(error=target_gap-base_gap)
        def choose(self, board):
            assert not self.weights.flags.writeable
            events.append(('prediction', self.kind))
            return choice()
        def save(self, path):
            assert not self.weights.flags.writeable
            events.append(('save', self.kind))
            return dict(path=str(path), bytes=0, seconds=0.)
    def forced(root, action, replica, parent, method):
        assert root['split'] == 'TRAIN'
        events.append(('branch', root['root_id'], action, replica))
        cutoff = root['index'] == 256 and action == 'DOWN' and replica == 1
        return dict(result=dict(status='CUTOFF' if cutoff else 'LOST',
            utility=(5. if action == 'DOWN' else 0.)+replica))
    monkeypatch.setattr(runner, 'QueryParent', Parent)
    monkeypatch.setattr(runner, 'PairResidual', Head)
    monkeypatch.setattr(runner, 'load_parent', lambda *args: (Parent(), {}))
    monkeypatch.setattr(runner, 'forced_row', forced)
    monkeypatch.setattr(runner, 'SUFFIX_REPLICAS', 2)
    monkeypatch.setattr(runner, 'EPOCHS', 2)
    roots = [case(0, q, episode, index, available) for q in runner.QUERIES
        for episode, index, available in ((0, 128, True), (0, 256, True), (12, 128, True), (13, 256, False))]
    data = runner.fit_lifecycle(dict(life=0), roots, tmp_path)
    labels = json.loads((tmp_path/data['labels']).read_text())
    assert len(labels) == 4 and sum(row['eligible'] for row in labels) == 2
    assert [row['root_id'] for row in labels] == [r['root_id'] for r in roots if r['split'] == 'TRAIN']
    fits = [event for event in events if event[0] == 'fit']
    assert fits == [(event, kind, 3. if kind == 'PRIOR' else 4/2048., 5., .1)
        for _ in runner.QUERIES for kind in runner.KINDS for event in ['fit'] for _ in range(2)]
    assert sum(event[0] == 'branch' for event in events) == 16
    assert all(m.updates == 2 and not m.weights.flags.writeable for m in models)
    assert all(m.parent.source.updates == 42 for m in models)
    with gzip.open(tmp_path/data['epoch_trace'], 'rt') as stream:
        epochs = [json.loads(line) for line in stream]
    assert [(r['query'], r['kind'], r['epoch'], r['calls']) for r in epochs] == [
        (q, k, e, 1) for q in runner.QUERIES for k in runner.KINDS for e in range(2)]
    predictions = json.loads((tmp_path/data['predictions']).read_text())
    assert {r['root_id'] for r in predictions} == {r['root_id'] for r in roots if r['available']}


def test_run_saves_all_frozen_heads_before_any_heldout_execution(tmp_path, monkeypatch):
    previous = dict(snapshots=[dict(life=life, rule={}, models={}, counts={},
        old_returns={'must_not_enter': True}) for life in runner.LIVES], inherited_costs={'retained': 7})
    source = tmp_path/'source'; source.mkdir()
    (source/'source_capsule.json').write_text(json.dumps(previous))
    (source/'analysis.json').write_text(json.dumps(dict(complete=True, costs={'retained': 9})))
    events = []
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def submit(self, function, *args):
            return SimpleNamespace(result=lambda value=function(*args): value)
    def prepare(source, directory):
        assert 'old_returns' not in source
        events.append(('acquire', source['life']))
        return dict(life=source['life'], cases=[])
    def fit(source, roots, directory):
        assert (directory/'roster.json').exists()
        assert sum(event[0] == 'acquire' for event in events) == 4
        events.append(('fit', source['life']))
        return dict(life=source['life'], queries={q: {'frozen': True} for q in runner.QUERIES})
    def evaluate(source, fitted, roots, directory):
        frozen = json.loads((directory/'frozen_heads.json').read_text())
        assert frozen['status'] == 'frozen' and len(frozen['fit_lifecycles']) == 4
        assert sum(event[0] == 'fit' for event in events) == 4
        events.append(('heldout', source['life']))
        return dict(life=source['life'])
    monkeypatch.setattr(runner, 'SOURCE', source)
    monkeypatch.setattr(runner, 'snapshot_code', lambda directory: None)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', Pool)
    monkeypatch.setattr(runner, 'as_completed', lambda futures: reversed(futures))
    monkeypatch.setattr(runner, 'prepare_lifecycle', prepare)
    monkeypatch.setattr(runner, 'fit_lifecycle', fit)
    monkeypatch.setattr(runner, 'evaluate_lifecycle', evaluate)
    output = tmp_path/'run'; runner.run(output)
    saved = json.loads((output/'run.json').read_text())
    assert saved['status'] == 'complete'
    assert events == [(phase, life) for phase in ('acquire', 'fit', 'heldout') for life in runner.LIVES]
    assert saved['inherited_costs'] == dict(retained=7, v129_diagnosis={'retained': 9})
