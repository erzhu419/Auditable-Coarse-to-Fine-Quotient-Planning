"""Frozen roster and physical versus same-budget economic acquisition."""
from collections import Counter
import gzip
import json
from types import SimpleNamespace

from acfqp.science import shadow_deployment_v293 as driver
from acfqp.science import shadow_deployment_analysis_v293 as analysis
from acfqp.science.shadow_deployment_core_v293 import (
    carrier_seed, deployment_seed, validation_seed, evaluation_seed)


def test_seed_families_do_not_reuse_learning_validation_or_science_streams():
    families = [
        {driver.warmup_seed(life, game) for life in range(16) for game in range(8)},
        {carrier_seed(life) for life in range(16)},
        {deployment_seed(life, arm) for life in range(16) for arm in range(3)},
        {validation_seed(life, phase, pair) for life in range(16) for phase in range(3) for pair in range(8)},
        {evaluation_seed(life, phase, game) for life in range(16) for phase in range(3) for game in range(32)}]
    assert [len(seeds) for seeds in families] == [128, 16, 48, 384, 1536]
    assert all(not left & right for i,left in enumerate(families) for right in families[i+1:])
    old = {292900000000+life*1000000+phase*100000+game
        for life in range(16) for phase in range(3) for game in range(32)}
    assert all(not seeds & old for seeds in families)
    config = driver.configuration('fixture', {'driver':3})
    assert config['lifecycles'] == list(range(16))
    assert config['arms'] == ('FROZEN_H2', 'UNCONDITIONAL_H2', 'VALIDATED_H2')
    assert config['carrier_raw_tiles_per_phase'] == 65536
    assert config['online_raw_tiles_per_arm_phase'] == 262144
    assert config['seed_warmup'] == driver.warmup_seed(0, 0)
    assert config['seed_carrier'] == carrier_seed(0)
    assert config['seed_deployment'] == deployment_seed(0, 0)
    assert config['seed_validation'] == validation_seed(0, 0, 0)
    assert config['seed_evaluation'] == evaluation_seed(0, 0, 0)
    assert all(analysis.science_seed(life, phase, game)==evaluation_seed(life, phase, game)
        for life in range(16) for phase in range(3) for game in range(32))
    assert all(analysis.validation_seed(life, phase, pair)==validation_seed(life, phase, pair)
        for life in range(16) for phase in range(3) for pair in range(8))


def test_shared_carrier_fit_and_A_probe_are_physically_charged_once():
    def counts(raw):
        return dict(environment={'raw_tile_productions':raw}, planning={}, learning={})
    arms = {}
    for arm in driver.ARMS:
        phases = {}
        for index,(phase,_) in enumerate(driver.PHASES):
            phases[phase] = dict(validation=dict(counts=counts(3+index), game_summaries=[{}]*16,
                cpu_seconds=.1), deployment={'cpu_seconds':.2}, game_summaries=[{}]*32,
                retention_probe=dict(shared_with_current=index==0, game_summaries=[{}]*32))
            if phase=='B':
                phases[phase]['a_head_on_B'] = {'game_summaries':[{}]*32}
        arms[arm] = dict(phases=phases, deployment_counts=counts(18),
            evaluation_counts=dict(environment={'raw_tile_productions':10}, planning={}),
            retention_evaluation_counts=dict(environment={'raw_tile_productions':4}, planning={}),
            a_head_on_B_evaluation_counts=dict(environment={'raw_tile_productions':2}, planning={}),
            final_unfitted_game={'raw_tiles':2})
    life = dict(arms=arms, warmup=dict(raw_tiles=7, game_summaries=[{}], environment_counts={},
        direct_counts={}, memory_counts={}), carrier=dict(training_counts=counts(30),
        phases={p:{'training':{'memory_counts':{'observations_received':10}}} for p,_ in driver.PHASES},
        retained_afterstate_steps_peak=9, final_unfitted_game={'raw_tiles':3},
        reconstruction_counts={}, reconstruction_cpu_seconds=.1),
        shadow=dict(fit_totals=dict(trained_afterstates=6, learning_counts={'table_updates':3},
            target_counts={'target_buffer_doubles_peak':7}, consolidation_counts={'native_buffer_bytes_peak':56},
            setup_counts={}, cpu_seconds=.1), head_setup={'setup_counts':{}, 'private_weight_bytes':32}),
        head_copies=[dict(setup_counts={'snapshot_weight_bytes_copied':32},
            private_weight_bytes=32, cpu_seconds=.01)])
    old = {'accounting':dict(inherited_costs_per_arm={'FROZEN_H2':{'source_training_raw_tiles':100,
        'dynamics_raw_tiles':5}}, physical_training_raw_tiles=999, evaluation_counts={})}
    result = driver.build_accounting(old, [life], [{'cpu_seconds':5., 'compiler_cpu_seconds':.2,
        'trace_bytes':100}], .1, 2.)
    assert result['physical_online_raw_tiles'] == 120
    assert result['online_raw_tiles_per_arm'] == dict.fromkeys(driver.ARMS, 60)
    assert result['economic_online_raw_tiles_per_arm'] == dict.fromkeys(driver.ARMS, 172)
    assert result['physical_processed_training_samples'] == 6
    assert result['economic_processed_training_samples_per_arm'] == {
        'FROZEN_H2':0, 'UNCONDITIONAL_H2':6, 'VALIDATED_H2':6}
    assert result['physical_evaluation_games'] == 576
    assert result['physical_validation_games'] == 144
    assert result['evaluation_counts']['environment']['raw_tile_productions'] == 48
    assert result['fit_buffer_peaks']['native_buffer_bytes_peak'] == 56
    assert result['physical_private_head_weight_bytes_created'] == 64


def test_parent_emitter_runs_each_lifecycle_once_with_one_shared_candidate_chain(monkeypatch, tmp_path):
    template = SimpleNamespace(updates=0, counts=Counter())
    monkeypatch.setattr(driver, 'load_leaf', lambda *args:(template, {}))
    def warmup(source, life, parent, emit):
        emit(dict(kind='WARMUP', lifecycle=life, parent=parent, summary={'seed':driver.warmup_seed(life, 0)}))
        return life, {'raw_tiles':256}
    seen = []
    def lifecycle(source, warmed, life, emit, runtime):
        assert source is template and warmed==life
        seen.append(life)
        return dict(carrier={'one_shared_stream':True}, shadow={'one_shared_chain':True},
            arms={arm:{} for arm in driver.ARMS})
    monkeypatch.setattr(driver, 'warmup', warmup)
    monkeypatch.setattr(driver, 'run_lifecycle', lifecycle)
    result = driver._run_parent({'parent':1}, tmp_path)
    with gzip.open(result['trace_file'], 'rt') as stream:
        records = [json.loads(line) for line in stream]
    assert seen == [1, 5, 9, 13]
    assert [life['lifecycle'] for life in result['lifecycles']] == seen
    assert all(row['parent']==1 for row in records) and len(records)==4
    assert template.updates == 0
