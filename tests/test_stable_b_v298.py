"""Stable-B execution, causal belief, fresh SOURCE copies and paid acquisition."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import independent_actor_data_v291 as acquisition
from acfqp.science import stable_b_v298 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from test_independent_actor_data_v291 import FrozenTemplate, RetainedStream, retained_warmup
from test_retained_actor_data_v287 import fixture

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/stable_b_v298/runtime/tests'


class BStream(RetainedStream):
    def advance(self, active, bank_id, pending, model_p, env_p, tile_budget, max_postaction):
        receipt = deepcopy(self.receipts[self.cursor])
        assert not active.weights.flags.writeable
        assert bank_id == 0 and env_p == .5 and max_postaction == 64
        assert model_p == receipt['model_p_four'] and model_p != env_p
        assert tile_budget == len(receipt['raw_spawns']) and self.current == receipt['start']
        self.calls.append(dict(tile_budget=tile_budget, pending=pending, model_p=model_p, env_p=env_p))
        self.cursor += 1
        self.current = receipt['end']
        for kind, counts in receipt['counts'].items():
            self.counts[kind].update(counts)
        receipt.update(updates=[], seconds=0., cpu_seconds=0.)
        return receipt


def acquire_b(monkeypatch, tmp_path, records):
    def warmup(seed, policy, p_four, max_steps):
        assert p_four == .5
        assert 298100000000 <= seed < 298200000000
        return retained_warmup(seed, policy, p_four, max_steps)
    monkeypatch.setattr(acquisition, 'run_episode', warmup)
    monkeypatch.setattr(acquisition, 'NativeValueStream', BStream)
    rows, _, _, _ = fixture()
    budget = next(row['snapshot']['stream']['raw_tiles'] for row in rows if row['kind']=='EVALUATION')
    return acquisition.acquire_dataset(FrozenTemplate(), 21, 1, records.append, tmp_path,
        raw_budget=budget, phase='B', p_four=.5,
        warmup_seed_base=298100000000, training_seed_base=298200000000)


def test_pure_b_receipts_use_new_stream_true_probability_and_only_observed_model(monkeypatch, tmp_path):
    records = []
    result = acquire_b(monkeypatch, tmp_path, records)
    data, paid = result['dataset'], result['acquisition']
    assert all(row['phase']=='B' and row['true_p_four']==.5 for row in records)
    assert all(row['start']['stream_seed']==298200000000+21*10000000
        for row in records if row['kind']=='TRAIN')
    assert 'actor_memory_A_end' not in data and 'full_A_raw_tiles' not in data['costs']
    assert data['actor_memory_B_end']['observations_seen']==paid['warmup']['raw_tiles']+paid['training']['raw_tiles']
    assert data['fit_memory']['observations_seen']==paid['warmup']['raw_tiles']+data['fit_end_raw']
    assert data['costs']['full_B_acquisition_counts']==paid['training']['counts']
    assert data['fit_game_count']==6 and [g['split'] for g in data['games']]==['FIT']*6+['HELDOUT']*2
    assert data['costs']['excluded_tail_raw_tiles']==5 and data['costs']['excluded_tail_steps']==3
    assert paid['new_value_updates']==0 and BStream.instances[-1].closed


@pytest.mark.parametrize('where', ['warmup', 'training'])
def test_b_cutoff_stays_retained_and_never_becomes_fit_label(monkeypatch, tmp_path, where):
    records = []
    if where == 'training':
        monkeypatch.setattr(BStream, 'cutoff', True)
    else:
        natural = retained_warmup
        def warmup(*args):
            row = natural(*args)
            row['status'] = 'CUTOFF'
            return row
        monkeypatch.setattr(__import__(__name__), 'retained_warmup', warmup)
    with pytest.raises(ValueError, match='cutoff retained'):
        acquire_b(monkeypatch, tmp_path, records)
    assert not any(row['kind']=='ACQUISITION_SNAPSHOT' for row in records)
    assert records[-1]['phase']=='B'


def small_leaf():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9,10)), (2, Fraction(1,10))), 'uniform', 3)
    native = NtupleValue(rule, BUILD)
    return QueryTD(QueryParent(native, core.QUERY, core.QUERY, .5), 'PRIOR', BUILD)


def test_actual_native_b_ranks_follow_environment_draws_instead_of_model_probability():
    leaf = small_leaf()
    leaf.freeze()
    engine = core.NativeValueStream(leaf, 29800003001, BUILD)
    try:
        receipt = engine.advance(leaf, 0, None, 1/258, .5, tile_budget=64)
        draws = engine.common_draws(29800003001, 64)
        assert [s['rank'] for s in receipt['raw_spawns']] == [1+(draw[1]>=1-.5) for draw in draws]
        assert any((draw[1]>=1-.5)!=(draw[1]>=1-1/258) for draw in draws)
        assert receipt['counts']['environment']['raw_tile_productions']==64
        assert receipt['counts']['environment']['environment_random_draws']==128
        assert not receipt['updates'] and leaf.updates==0
    finally:
        engine.close()


def test_three_fresh_source_heads_share_fit_prefix_and_new_b_evaluation_without_feedback(monkeypatch):
    template = small_leaf()
    template.freeze()
    memory = SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    final = SpawnMemory('LIBRARY')
    for i in range(512):
        final.observe(1+i%2)
    board = np.asarray([1,1,0,0]+[0]*12, dtype=np.int32)
    data = dict(afterstates=np.tile(board,(7,1)), rewards=np.asarray([.1,.2,.3,.4,.5,.6,.7]),
        ends=np.asarray([2,4,7],dtype=np.int64), terminal_codes=np.full(3,-1,dtype=np.int32),
        fit_game_count=2, fit_step_end=4, fit_end_raw=8, fit_memory=memory.to_payload(),
        actor_memory_B_end=final.to_payload(), costs={},
        games=[dict(episode=i,split='FIT' if i<2 else 'HELDOUT') for i in range(3)])
    initialized, evaluated = [], []
    def fresh(parent, kind, runtime):
        leaf = QueryTD(parent, kind, runtime)
        np.testing.assert_array_equal(leaf.weights, template.parent.source.weights)
        initialized.append(leaf.updates)
        return leaf
    monkeypatch.setattr(core, 'QueryTD', fresh)
    engine = core.NativeValueStream(template, core.evaluation_seed(0,0), BUILD)
    original = engine.evaluate_games
    def evaluate(leaf, p, env_p, seeds, **kwargs):
        assert p==1/258 and env_p==.5 and not leaf.weights.flags.writeable
        assert seeds==[core.evaluation_seed(0,e) for e in range(32)]
        evaluated.append((p,env_p))
        return original(leaf,p,env_p,seeds,**kwargs)
    engine.evaluate_games = evaluate
    try:
        before = engine.state()
        row = core._run_lifecycle(template,data,{},0,0,BUILD,engine)
        assert engine.state()==before
    finally:
        engine.close()
    assert initialized==[0,0] and evaluated==[(1/258,.5)]*3
    assert [row['arms'][a]['processed_training_samples'] for a in core.ARMS]==[0,4,4]
    assert all(row['arms'][a]['sample_counter']==row['arms'][a]['processed_training_samples'] for a in core.ARMS)
    assert template.updates==template.parent.source.updates==0
    np.testing.assert_array_equal(template.weights,template.parent.source.weights)


def test_b_accounting_pays_new_raw_and_source_but_not_old_a_target_acquisition():
    inherited = dict(source_training_raw_tiles=100, dynamics_raw_tiles=5, source_training_games=2,
        source_training_environment_counts={},source_training_seconds=1.,dynamics_costs={})
    old = dict(accounting=dict(inherited_costs_per_arm={'FROZEN':inherited},
        new_training_environment_observations=9999,evaluation_counts={}))
    def arm(samples):
        return dict(processed_training_samples=samples,fit=dict(learning_counts={},target_counts={},
            consolidation_counts={},seconds=0.,cpu_seconds=0.),heldout=dict(prediction_counts={},
            target_counts={},seconds=0.,cpu_seconds=0.),evaluation_counts=dict(environment={},planning={}),
            head_setup=dict(private_weight_bytes=32 if samples else 0),evaluation_cpu_seconds=0.)
    lives = [dict(dataset={'costs':{'excluded_tail_raw_tiles':3}},acquisition=dict(
        warmup=dict(raw_tiles=7,environment_counts={},direct_counts={},memory_counts={}),
        training=dict(raw_tiles=20,memory_counts={},counts=dict(environment={},planning={},learning={})),
        reconstruction=dict(counts={},memory_counts={},cpu_seconds=0.)),
        arms={a:arm(a!='FROZEN') for a in core.ARMS})]
    result = core.build_accounting(old,lives,[dict(cpu_seconds=1.,compiler_cpu_seconds=0.,trace_bytes=2)],0.,1.)
    assert result['new_training_environment_observations']==27 and result['new_actor_B_raw_tiles']==20
    assert result['economic_training_raw_tiles_per_arm']==dict.fromkeys(core.ARMS,132)
    assert result['development_reference']['previous_target_acquisition_raw_tiles']==9999
