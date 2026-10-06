"""Four native arms consume the same facts and reuse both active linear arrays."""
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import linear_contribution_run_v311 as core
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from test_bank_belief_run_v310 import dataset

BUILD = Path(__file__).resolve().parents[1]/'reports/linear_contribution_v311/runtime_tests/driver'


def template():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape)%11*.001
    leaf = core.QueryTD(QueryParent(source, core.QUERY, core.QUERY, .5), 'PRIOR', BUILD)
    leaf.freeze()
    return leaf


def acquire_fixture(monkeypatch, source):
    acquired = []
    def acquire(leaf, life, parent, stage, router, emit, runtime, **kw):
        assert leaf is source and not leaf.weights.flags.writeable and leaf.updates==0
        i = core.STAGES.index(stage)
        assert kw['warmup_seed_base']==311100000000+i*100000
        assert kw['training_seed_base']==311200000000+i*100000
        assert kw['raw_budget']==131072
        memory = SpawnMemory('LIBRARY')
        for j in range(256):
            memory.observe(2 if core.TASKS[stage]=='B' and j<128 else 1)
        route = router.commit(memory.to_payload(), router.probe(memory.to_payload()))
        facts = dataset(stage, 120 if core.TASKS[stage]=='B' else 7) if route['created'] else None
        acquired.append((stage, route, facts))
        return dict(route=route, dataset=facts,
            detector_belief=dict(memory=memory.to_payload(), estimated_p_four=memory.predict()),
            acquisition=dict(warmup=dict(raw_tiles=256),
                training=dict(raw_tiles=20) if facts is not None else None))
    monkeypatch.setattr(core, 'acquire_stage', acquire)
    return acquired


def test_three_heads_initialize_with_active_equal_sized_linear_tables():
    source = template(); heads, setup = core._initialize(source, BUILD)
    assert set(heads)==set(core.LEARNERS)
    for head in heads.values():
        np.testing.assert_array_equal(head.weights, source.weights)
    linear, local = heads['CONTEXT_LINEAR_WIN'], heads['CONTEXT_LOCAL']
    np.testing.assert_array_equal(linear.win_weights, np.full_like(source.weights, 1./64))
    assert setup['CONTEXT_LINEAR_WIN']['private_weight_bytes']==setup['CONTEXT_LOCAL']['private_weight_bytes']
    assert setup['CONTEXT_MC']['private_weight_bytes']*2==setup['CONTEXT_LOCAL']['private_weight_bytes']
    assert not np.shares_memory(linear.weights, source.weights)
    assert not np.shares_memory(linear.win_weights, local.risk_weights)


def test_native_four_arm_lifecycle_fits_identical_facts_and_reuses_linear_arrays(monkeypatch):
    source = template(); acquired = acquire_fixture(monkeypatch, source)
    fitted = []
    actual = core.fit_linear
    def fit(leaf, data, runtime, alpha):
        result = actual(leaf, data, runtime, alpha=alpha)
        fitted.append((leaf, leaf.weights, leaf.win_weights, data))
        return result
    monkeypatch.setattr(core, 'fit_linear', fit)
    engine = core.NativeValueStream(source, 311900000000, BUILD)
    try:
        row = core._run_lifecycle(source, 0, 0, BUILD, engine, lambda _:None)
    finally:
        engine.close()
    assert [route['context_id'] for _,route,_ in acquired]==[0,1,0,1,0]
    assert len(fitted)==2
    for leaf, reward, win, facts in fitted:
        assert leaf.weights is reward and leaf.win_weights is win
        assert not reward.flags.writeable and not win.flags.writeable
        assert leaf.updates==facts['fit_step_end']==4
    for stage in core.STAGES:
        value = row['stages'][stage]
        assert set(value['arms'])==set(core.ARMS)
        fit_rows = [value['arms'][arm]['fit'] for arm in core.LEARNERS]
        assert {r['trained_afterstates'] for r in fit_rows}==({4} if stage in ('A1','B1') else {0})
        assert value['arms']['SOURCE']['processed_training_samples']==0
        for task, belief in value['planning_beliefs'].items():
            selected = value['evaluation_routes'][task]['context_id']
            assert belief==row['bank_beliefs'][str(selected)]
            for arm in core.ARMS:
                result = value['arms'][arm]['evaluations'][task]
                assert result['estimated_p_four']==belief['estimated_p_four']
                assert len(result['game_summaries'])==32
                assert all(r['status'] in ('WON','LOST') for r in result['game_summaries'])
    assert source.updates==0


def test_linear_fit_inventory_mismatch_stops_before_evaluation(monkeypatch):
    source = template(); acquire_fixture(monkeypatch, source)
    actual = core.fit_linear
    def wrong(leaf, data, runtime, alpha):
        result = actual(leaf, data, runtime, alpha=alpha)
        return dict(result, trained_afterstates=result['trained_afterstates']+1)
    monkeypatch.setattr(core, 'fit_linear', wrong)
    engine = core.NativeValueStream(source, 311900000000, BUILD)
    try:
        with pytest.raises(ValueError, match='First adaptation samples'):
            core._run_lifecycle(source, 0, 0, BUILD, engine, lambda _:None)
    finally:
        engine.close()
