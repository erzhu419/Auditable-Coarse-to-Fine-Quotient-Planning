from collections import Counter
from fractions import Fraction
from pathlib import Path
import numpy as np

from acfqp.science import natural_online_value_v286 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science import native_value_stream_v286 as native
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram


class TinyBank:
    def __init__(self, parent=None, kind=None, runtime=None):
        self.parent = parent or self
        self.weights = np.array([3.])
        self.updates, self.counts = 0, Counter()
        self.setup_counts, self.setup_seconds = Counter(source_parameters_copied=1), 0.


class RawStream:
    instances = []
    def __init__(self, template, seed, runtime, max_steps):
        self.seed, self.raw, self.pending = seed, 0, None
        self.counts = {key: Counter() for key in ('environment', 'planning', 'learning')}
        self.setup_counts, self.setup_seconds = Counter(), 0.
        self.calls = []
        self.instances.append(self)
    def state(self):
        return dict(raw_tiles=self.raw, pending_bank_id=self.pending, board=[0]*16,
                    random_draw_position=2*self.raw)
    def advance(self, active, bank_id, pending, model_p, env_p, tile_budget, max_postaction):
        before = self.state()
        self.calls.append(dict(raw=self.raw, bank=bank_id, model_p=model_p, env_p=env_p,
            quota=tile_budget, weight_before=active.weights[0], old_bank=pending))
        ranks = [2 if env_p == .5 else 1]*tile_budget
        raw = [dict(rank=rank, cell=0, kind='INITIAL' if self.raw+i<2 else 'POST_ACTION')
               for i, rank in enumerate(ranks)]
        self.raw += tile_budget
        self.pending = bank_id
        work = dict(environment=dict(raw_tile_productions=tile_budget), planning={}, learning={})
        for key, value in work.items():
            self.counts[key].update(value)
        if active.weights.flags.writeable:
            active.weights[0] += 100.
            active.updates += 1
        return dict(start=before, end=self.state(), raw_spawns=raw, actions=[], scores=[],
            completed_games=[], counts=work, updates=[])
    def evaluate_games(self, leaf, model_p, env_p, seeds, depth):
        return dict(game_summaries=[dict(seed=seed, utility=1., status='WON', steps=1) for seed in seeds],
            counts=dict(environment=dict(raw_tile_productions=3*len(seeds)), planning={}),
            seconds=0., cpu_seconds=0.)
    def close(self):
        pass


def test_raw_budget_routing_and_fresh_context_tables(monkeypatch):
    monkeypatch.setattr(core, 'RAW_TILES_PER_PHASE', 65)
    monkeypatch.setattr(core, 'QueryTD', TinyBank)
    monkeypatch.setattr(native, 'NativeValueStream', RawStream)
    warmed = SpawnMemory('LIBRARY')
    for _ in range(256):
        warmed.observe(1)
    frozen = TinyBank()
    frozen.weights.flags.writeable = False
    original = warmed.to_payload()
    records = []
    result, direct = core.run_arm(frozen, warmed, 0, 'PERSISTENT_TD', records.append, None)
    engine = RawStream.instances[-1]
    assert engine.raw == 195 and result['final_memory']['observations_seen'] == 256+195
    assert warmed.to_payload() == original
    assert all(call['quota'] <= 64 for call in engine.calls)
    assert all(result['phases'][phase]['training']['raw_tiles'] == 65 for phase, _ in core.PHASES)
    assert engine.calls[0]['model_p'] == 1./258. and engine.calls[0]['env_p'] == .1
    # B feedback creates a new bank. Its first weights come from source=3,
    # rather than from a mutated previous bank; the old pending bank survives.
    first_by_bank = {}
    for call in engine.calls:
        first_by_bank.setdefault(call['bank'], call)
    assert len(first_by_bank) >= 2
    assert all(call['weight_before'] == 3. for call in first_by_bank.values())
    assert all(call['old_bank'] is not None for call in list(first_by_bank.values())[1:])
    assert direct['game_summaries'] == result['phases']['A_prime']['game_summaries']
    train_rows = [r for r in records if r['kind'] == 'TRAIN']
    assert sum(len(r['raw_spawns']) for r in train_rows) == 195
    assert sum(s['kind'] == 'INITIAL' for r in train_rows for s in r['raw_spawns']) == 2


def test_seed_families_and_paired_endpoints():
    train = {core.training_seed(life) for life in range(16)}
    evaluation = {core.evaluation_seed(life, phase, episode)
        for life in range(16) for phase in range(3) for episode in range(16)}
    warmup = {286100000000+life*1000000+episode for life in range(16) for episode in range(10)}
    assert len(evaluation) == 768
    assert not train & evaluation and not train & warmup and not evaluation & warmup


def test_actual_driver_matches_raw_memories_and_keeps_frozen_control(monkeypatch):
    monkeypatch.setattr(core, 'RAW_TILES_PER_PHASE', 5)
    runtime = Path(__file__).resolve().parents[1]/'reports/natural_online_value_v286/runtime/driver_test'
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9,10)), (2, Fraction(1,10))), 'uniform', 4)
    source = NtupleValue(rule, runtime)
    source.weights.flags.writeable = False
    template = QueryTD(QueryParent(source, core.QUERY, core.QUERY, .5), 'PRIOR', runtime)
    template.freeze()
    warmed = SpawnMemory('LIBRARY')
    for index in range(319):
        warmed.observe(2 if index % 10 == 0 else 1)
    results, records = {}, []
    for arm in core.ARMS:
        results[arm], _ = core.run_arm(template, warmed, 15, arm, records.append, runtime)
    assert template.updates == 0
    assert not np.any(template.weights)
    for phase, _ in core.PHASES:
        memories = [results[a]['phases'][phase]['snapshot']['memory'] for a in core.ARMS]
        assert memories[0] == memories[1] == memories[2]
    assert all(r['final_stream']['raw_tiles'] == 15 for r in results.values())
    assert all(r['final_memory']['observations_seen'] == 334 for r in results.values())
    assert results['FROZEN']['new_value_updates'] == 0
    assert results['ORDINARY_TD']['new_value_updates'] > 0
    assert results['PERSISTENT_TD']['new_value_updates'] > 0
    for arm in core.ARMS:
        assert results[arm]['training_counts']['environment']['raw_tile_productions'] == 15
        assert sum(g['status'] == 'WON' for p in results[arm]['phases'].values()
                   for g in p['game_summaries']) > 0


def test_summary_omits_events_and_lifecycles_already_in_receipts():
    life = dict(lifecycle=0, arms={arm: dict(phases={phase:
        dict(training=dict(memory_events=[dict(kind='updated')]*2)) for phase, _ in core.PHASES})
        for arm in core.ARMS})
    result = dict(by_lifecycle=[life], parent_receipts=[dict(parent=0, lifecycles=[life], trace_bytes=10)])
    core.compact_summary(result)
    assert result['parent_receipts'] == [dict(parent=0, lifecycle_ids=[0], trace_bytes=10)]
    assert all(life['arms'][arm]['phases'][phase]['training'] == dict(memory_event_count=2)
        for arm in core.ARMS for phase, _ in core.PHASES)
