"""Fresh seed separation, paid acquisition and actual three-head integration."""
from fractions import Fraction
from pathlib import Path

import numpy as np

from acfqp.science import independent_episode_v291 as core
from acfqp.science.independent_actor_data_v291 import training_seed, warmup_seed
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/'reports/independent_episode_v291/driver_tests'


def test_all_64_seed_families_are_fresh_and_separated():
    training = {training_seed(life) for life in range(64)}
    evaluation = {core.evaluation_seed(life, episode) for life in range(64) for episode in range(32)}
    warmup = {warmup_seed(life, game) for life in range(64) for game in range(8)}
    old = {290500000000+life*1000000+episode for life in range(16) for episode in range(16)}
    assert len(training) == 64 and len(evaluation) == 2048
    assert not training & evaluation and not warmup & training and not warmup & evaluation
    assert not evaluation & old
    assert max(warmup) < min(training) < max(training) < min(evaluation)
    assert core.EVALUATION_GAMES == 32 and core.RAW_BUDGET == 131072


def test_old_target_histories_are_development_and_new_full_acquisition_is_paid_once():
    def arm(samples, writes, peak):
        return dict(processed_training_samples=samples, fit=dict(learning_counts={
            'td_updates':samples, 'table_updates':writes}, target_counts={'suffix_games':2,
            'target_buffer_doubles_peak':peak}, consolidation_counts={'parameter_write_events':writes,
            'native_buffer_bytes_peak':peak*8}, seconds=.2, cpu_seconds=.1),
            heldout=dict(prediction_counts={'value_predictions':3}, target_counts={'suffix_games':1,
            'target_buffer_doubles_peak':3}, seconds=.1, cpu_seconds=.05),
            evaluation_counts={'environment':{'raw_tile_productions':10}, 'planning':{}},
            head_setup={'private_weight_bytes':0 if not samples else 32}, evaluation_cpu_seconds=.3)
    inherited = dict(source_training_raw_tiles=100, dynamics_raw_tiles=5, source_training_games=2,
        source_training_environment_counts={}, source_training_seconds=1., dynamics_costs={},
        warmup_raw_tiles=11, retained_actor_A_raw_tiles=999)
    old = {'accounting':{'inherited_costs_per_arm':{'FROZEN':inherited}, 'evaluation_counts':{}}}
    lives = [dict(lifecycle=i, dataset={'costs':{'excluded_tail_raw_tiles':3}},
        acquisition=dict(warmup=dict(raw_tiles=7, environment_counts={'sampled_transitions':5},
            direct_counts={}, memory_counts={}), training=dict(raw_tiles=20, memory_counts={},
            counts={'environment':{'raw_tile_productions':20}, 'planning':{}, 'learning':{}}),
            reconstruction={'counts':{}, 'memory_counts':{}, 'cpu_seconds':.1}),
        arms={a:arm(0 if a=='FROZEN' else 6, 2 if a=='EPISODE_MEAN_MC' else 5, 4+i)
            for a in core.ARMS}) for i in range(2)]
    result = core.build_accounting(old, lives, [{'cpu_seconds':3., 'compiler_cpu_seconds':.5,
        'trace_bytes':100}], .2, 4.)
    assert result['economic_training_raw_tiles_per_arm'] == dict.fromkeys(core.ARMS, 159)
    assert result['new_training_environment_observations'] == 54
    assert result['new_training_environment_counts']['raw_tile_productions'] == 54
    assert result['physical_acquisitions'] == 2 and result['excluded_tail_raw_tiles'] == 6
    assert 'retained_actor_A_raw_tiles' not in result['inherited_costs_per_arm']['FROZEN']
    assert result['development_reference']['previous_target_acquisition_raw_tiles'] == 1010
    assert result['processed_training_samples']['EPISODE_MEAN_MC'] == 12
    assert result['fit_counts']['EPISODE_MEAN_MC']['table_updates'] == 4
    assert result['consolidation_buffer_peaks']['EPISODE_MEAN_MC']['native_buffer_bytes_peak'] == 40
    assert result['evaluation_counts']['environment']['raw_tile_productions'] == 60


def test_actual_three_heads_use_identical_samples_and_fit_prefix_without_feedback():
    # Supported small-goal fixture checks native integration; no formal actor acquisition.
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 3)
    native = NtupleValue(rule, BUILD/'runtime')
    template = QueryTD(QueryParent(native, core.QUERY, core.QUERY, .5), 'PRIOR', BUILD/'runtime')
    template.freeze()
    memory = SpawnMemory('LIBRARY')
    for _ in range(256):
        memory.observe(1)
    board = np.asarray([1, 1, 0, 0]+[0]*12, dtype=np.int32)
    data = dict(afterstates=np.tile(board, (7, 1)), rewards=np.asarray([.1, .2, .3, .4, .5, .6, .7]),
        ends=np.asarray([2, 4, 7], dtype=np.int64), terminal_codes=np.full(3, -1, dtype=np.int32),
        fit_game_count=2, fit_step_end=4, fit_end_raw=8, fit_memory=memory.to_payload(), costs={},
        games=[dict(episode=i, split='FIT' if i<2 else 'HELDOUT') for i in range(3)])
    engine = core.NativeValueStream(template, core.evaluation_seed(0, 0), BUILD/'runtime')
    try:
        before = engine.state()
        life = core._run_lifecycle(template, data, {}, 0, 0, BUILD/'runtime', engine)
        assert engine.state() == before
    finally:
        engine.close()
    assert life['evaluation_snapshot']['estimated_p_four'] == 1/258
    assert [life['arms'][a]['processed_training_samples'] for a in core.ARMS] == [0, 4, 4]
    assert all(len(life['arms'][a]['game_summaries']) == 32 for a in core.ARMS)
    assert all(life['arms'][a]['sample_counter'] == life['arms'][a]['processed_training_samples'] for a in core.ARMS)
    assert all(life['arms'][a]['heldout']['game_metrics'][0]['count'] == 3 for a in core.ARMS)
    assert not template.weights.flags.writeable and template.updates == native.updates == 0
    np.testing.assert_array_equal(template.weights, native.weights)
