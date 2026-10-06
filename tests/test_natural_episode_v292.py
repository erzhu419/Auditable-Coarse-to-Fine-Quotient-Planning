"""Driver boundaries and physically paid training/evaluation accounting."""
from collections import Counter
import gzip
import json
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

from acfqp.science import natural_episode_v292 as core
from acfqp.science.online_episode_stream_v292 import training_seed, evaluation_seed


def test_new_seed_families_and_predeclared_roster_are_separate():
    warm = {core.warmup_seed(life, game) for life in range(16) for game in range(8)}
    train = {training_seed(life) for life in range(16)}
    evaluate = {evaluation_seed(life, phase, episode) for life in range(16) for phase in range(3) for episode in range(32)}
    old = {291900000000+life*1000000+episode for life in range(64) for episode in range(32)}
    assert len(evaluate) == 1536 and not evaluate & old
    assert not train & evaluate and not train & warm and not evaluate & warm
    assert max(warm) < min(train) < max(train) < min(evaluate)
    settings = core.configuration('fixture', {'driver':3})
    assert settings['lifecycles'] == list(range(16)) and len(settings['arms']) == 5
    assert settings['phases'] == (('A', .1), ('B', .5), ('A_prime', .1))


def test_accounting_pays_distinct_trajectories_and_all_extra_probes_once():
    def arm(name):
        return dict(training_counts={'environment':{'raw_tile_productions':30}, 'planning':{}, 'learning':{}},
            evaluation_counts={'environment':{'raw_tile_productions':10}, 'planning':{}},
            retention_evaluation_counts={'environment':{'raw_tile_productions':4}, 'planning':{}},
            a_head_on_B_evaluation_counts={'environment':{'raw_tile_productions':2 if name=='MEAN_H2' else 0}, 'planning':{}},
            fit_totals=dict(trained_afterstates=6 if name.startswith(('MEAN','NSEQ')) else 0,
                learning_counts={'table_updates':3}, target_counts={'target_buffer_doubles_peak':7},
                consolidation_counts={'native_buffer_bytes_peak':56}, cpu_seconds=.1),
            final_unfitted_game={'raw_tiles':3}, head_setup={'private_weight_bytes':32},
            retained_A_head_setup={'private_weight_bytes':32} if name=='MEAN_H2' else None,
            final_memory={'counts':{'observations_received':37}},
            costs={'cpu_seconds':1., 'reconstruction_cpu_seconds':.1, 'reconstruction_counts':{}})
    inherited = {'source_training_raw_tiles':100, 'dynamics_raw_tiles':5}
    old = {'accounting':{'inherited_costs_per_arm':{'FROZEN':inherited},
        'new_training_environment_observations':999, 'evaluation_counts':{}}}
    lives = [dict(warmup=dict(raw_tiles=7, game_summaries=[{}], environment_counts={}, direct_counts={}, memory_counts={}),
        arms={a:arm(a) for a in core.ARMS})]
    result = core.build_accounting(old, lives, [{'cpu_seconds':5., 'compiler_cpu_seconds':.2, 'trace_bytes':100}], .1, 2.)
    assert result['economic_training_raw_tiles_per_arm'] == dict.fromkeys(core.ARMS, 142)
    assert result['physical_training_raw_tiles'] == 150 and result['physical_warmup_raw_tiles'] == 7
    assert result['evaluation_counts']['environment']['raw_tile_productions'] == 72
    assert result['evaluation_counts_per_arm']['MEAN_H2']['environment']['raw_tile_productions'] == 16
    assert result['final_unfitted_raw_tiles_per_arm'] == dict.fromkeys(core.ARMS, 3)
    assert result['fit_buffer_peaks']['MEAN_H2']['native_buffer_bytes_peak'] == 56
    assert result['development_reference']['previous_target_acquisition_raw_tiles'] == 999


def test_actual_parent_emitter_keeps_shared_warmup_parent_and_five_arms(monkeypatch, tmp_path):
    template = SimpleNamespace(updates=0, counts=Counter())
    monkeypatch.setattr(core, 'load_leaf', lambda *args:(template, {}))
    def warmup(source, life, parent, emit):
        emit(dict(kind='WARMUP', lifecycle=life, parent=parent, summary={'seed':core.warmup_seed(life, 0)}))
        return object(), {'raw_tiles':256}
    def arm(source, warmed, life, name, emit, runtime):
        assert source is template
        return {'phases':{phase:{'snapshot':{'memory':{'observations_seen':256+(i+1)*131072}}}
            for i,(phase,_) in enumerate(core.PHASES)}}
    monkeypatch.setattr(core, 'warmup', warmup)
    monkeypatch.setattr(core, 'run_arm', arm)
    result = core._run_parent({'parent':1}, tmp_path)
    with gzip.open(result['trace_file'], 'rt') as stream:
        records = [json.loads(line) for line in stream]
    assert [l['lifecycle'] for l in result['lifecycles']] == [1, 5, 9, 13]
    assert len(records) == 4 and all(r['parent'] == 1 for r in records)
    assert all(list(l['arms']) == list(core.ARMS) for l in result['lifecycles'])
    assert template.updates == 0


def test_actual_native_host_consolidation_continues_across_three_small_phases(monkeypatch):
    from acfqp.science import online_episode_stream_v292 as online
    from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
    from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
    from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
    from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
    from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
    build = Path(__file__).resolve().parents[1]/'reports/natural_episode_v292/driver_native'
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    source = NtupleValue(rule, build)
    template = QueryTD(QueryParent(source, core.QUERY, core.QUERY, .5), 'PRIOR', build)
    template.freeze()
    memory = SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    monkeypatch.setattr(online, 'RAW_TILES_PER_PHASE', 40)
    monkeypatch.setattr(online, 'EVALUATION_GAMES', 2)
    monkeypatch.setattr(online, 'training_seed', lambda life:2920000300+life)
    monkeypatch.setattr(online, 'evaluation_seed', lambda life, phase, episode:2920000400+phase*1000+episode)
    records = []
    result = online.run_arm(template, memory, 0, 'MEAN_H2', records.append, build)
    assert result['final_stream']['raw_tiles'] == 120
    assert result['fit_totals']['trained_afterstates'] > 0
    assert result['training_counts']['environment']['raw_tile_productions'] == 120
    assert result['training_counts']['learning']['td_updates'] == result['fit_totals']['trained_afterstates']
    assert result['final_memory']['observations_seen'] == 376
    fits = [row for row in records if row['kind'] == 'GAME_FIT']
    assert fits and all(row['fitted'] for row in fits)
    for i, row in enumerate(records):
        if row['kind'] == 'TRAIN':
            assert row['actor_weights_readonly'] and row['leaf_updates_before'] == row['leaf_updates_after']
            if row['completed_games']:
                assert records[i+1]['kind'] == 'GAME_FIT'
    assert result['phases']['B']['training']['before_stream'] == result['phases']['A']['snapshot']['stream']
    assert result['phases']['B']['a_head_on_B']['model_p_four'] == result['phases']['B']['snapshot']['estimated_p_four']
    assert result['phases']['A']['retention_probe']['shared_with_current']
    assert template.updates == 0 and not template.weights.flags.writeable
