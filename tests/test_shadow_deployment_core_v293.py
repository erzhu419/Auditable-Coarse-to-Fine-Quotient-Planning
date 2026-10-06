from copy import deepcopy
from fractions import Fraction
from math import sqrt
from pathlib import Path
from statistics import stdev

import numpy as np
import pytest

from acfqp.science import shadow_deployment_core_v293 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from test_online_episode_stream_v292 import Head as BaseHead, Stream, setup as stream_setup
from test_retained_actor_data_v287 import game_events


def paired(differences, cutoff=None):
    return [dict(incumbent=dict(utility=0., status='LOST'),
        candidate=dict(utility=value, status='CUTOFF' if i == cutoff else 'WON'))
        for i, value in enumerate(differences)]


def test_environment_seed_families_use_the_uniform_prelaunch_offset():
    assert core.carrier_seed(0) == 293200010000
    assert core.deployment_seed(0, 0) == 293400010000
    assert core.validation_seed(0, 0, 0) == 293600010000
    assert core.evaluation_seed(0, 0, 0) == 293900010000
    groups = [
        {core.carrier_seed(life) for life in range(16)},
        {core.deployment_seed(life, arm) for life in range(16) for arm in range(3)},
        {core.validation_seed(life, phase, pair) for life in range(16) for phase in range(3) for pair in range(8)},
        {core.evaluation_seed(life, phase, episode) for life in range(16) for phase in range(3) for episode in range(32)},
    ]
    assert [len(group) for group in groups] == [16, 48, 384, 1536]
    assert len(set.union(*groups)) == sum(len(group) for group in groups)


def test_gate_uses_fixed_eight_pair_t_lower_bound_not_positive_mean_alone():
    differences = [1.]*7+[0.]
    result = core.select_submission(paired(differences))
    assert result['lower95'] == pytest.approx(.875-core.T_CRITICAL_7*stdev(differences)/sqrt(8))
    assert result['accept']
    noisy = core.select_submission(paired([20.]+[-1.]*7))
    assert noisy['mean_delta'] > 0. and noisy['lower95'] < 0. and not noisy['accept']
    assert not core.select_submission(paired([0.]*8))['accept']
    assert not core.select_submission(paired([1.]*8, cutoff=3))['accept']
    with pytest.raises(ValueError):
        core.select_submission(paired([1.]*7))


class Head(BaseHead):
    def __init__(self, parent=None, kind=None, runtime=None):
        super().__init__(parent, kind, runtime)
        self.target_query = dict(goal_bonus=4., failure_penalty=4.)


def prepare(monkeypatch):
    # Reuse lawful finite stream/fit receipts, with no additional environment draws.
    source, warmed, captures = stream_setup(monkeypatch)
    from acfqp.science import online_episode_stream_v292 as previous
    monkeypatch.setattr(core, 'fit_consolidated', previous.fit_consolidated)
    monkeypatch.setattr(core, 'QueryTD', Head)
    monkeypatch.setattr(core, 'NativeValueStream', Stream)
    carrier = len(game_events()[0])//2+1
    monkeypatch.setattr(core, 'CARRIER_RAW_PER_PHASE', carrier)
    monkeypatch.setattr(core, 'ONLINE_RAW_PER_PHASE', carrier+16*len(game_events()[0])+carrier+7)
    monkeypatch.setattr(core, 'EVALUATION_GAMES', 2)
    source = Head(); source.freeze()
    Stream.instances.clear()
    return source, warmed, captures


def test_shared_carrier_is_submission_independent_and_proposals_are_immutable(monkeypatch, tmp_path):
    source, warmed, fits = prepare(monkeypatch)
    before, records = warmed.to_payload(), []
    result = core.run_lifecycle(source, warmed, 0, records.append, tmp_path)
    assert len(fits) == 1
    carrier = next(engine for engine in Stream.instances if engine.state()['stream_seed'] == core.carrier_seed(0))
    assert all(call['weight'] == 3. for call in carrier.calls)
    assert result['shadow']['new_value_updates'] == len(game_events()[0])-2
    assert result['carrier']['final_memory']['observations_seen'] == 256+3*core.CARRIER_RAW_PER_PHASE
    assert warmed.to_payload() == before and source.updates == 0 and source.weights.tolist() == [3.]
    unconditional, validated = (result['arms'][arm] for arm in ('UNCONDITIONAL_H2', 'VALIDATED_H2'))
    assert [unconditional['phases'][p]['submission']['deployed_submission_id'] for p, _ in core.PHASES] == [1, 2, 3]
    assert [validated['phases'][p]['submission']['deployed_submission_id'] for p, _ in core.PHASES] == [0, 0, 0]
    assert unconditional['phases']['A']['game_summaries'][0]['utility'] == 3.
    assert unconditional['phases']['B']['game_summaries'][0]['utility'] == 13.
    assert unconditional['phases']['B']['a_head_on_B']['game_summaries'][0]['utility'] == 3.
    # B's shadow fit has already changed theta to 13. The actual B validation
    # must still execute A's unconditional incumbent proposal at theta=3.
    b_pair = [engine for engine in Stream.instances
              if engine.state()['stream_seed'] == core.validation_seed(0, 1, 0)]
    assert [engine.calls[0]['weight'] for engine in b_pair] == [3., 3., 3., 13., 3., 13.]
    assert len(result['head_copies']) == 6
    assert all(copy['setup_counts']['source_weight_bytes_copied'] == 8
               and copy['setup_counts']['snapshot_weight_bytes_copied'] == 8 for copy in result['head_copies'])
    fit_index = next(i for i, row in enumerate(records) if row['kind'] == 'SHADOW_FIT')
    assert records[fit_index-1]['kind'] == 'CARRIER_TRAIN'
    assert records[fit_index]['phase'] == 'B'
    assert all(engine.closed for engine in Stream.instances)


def test_actual_validation_is_paid_and_deployment_fills_exact_remaining_quota(monkeypatch, tmp_path):
    source, warmed, _ = prepare(monkeypatch)
    records = []
    result = core.run_lifecycle(source, warmed, 2, records.append, tmp_path)
    assert sum(row['kind'] == 'VALIDATION_GAME' for row in records) == 3*3*16
    for arm in core.ARMS:
        old_end = None
        for phase_index, (phase, _) in enumerate(core.PHASES):
            row = result['arms'][arm]['phases'][phase]
            validation, deployment = row['validation'], row['deployment']
            assert len(validation['pairs']) == 8 and len(validation['game_summaries']) == 16
            assert validation['raw_tiles'] == sum(game['raw_tiles'] for game in validation['game_summaries'])
            assert row['online_raw_tiles'] == core.ONLINE_RAW_PER_PHASE
            assert deployment['raw_tiles'] == core.ONLINE_RAW_PER_PHASE-core.CARRIER_RAW_PER_PHASE-validation['raw_tiles']
            assert deployment['after_stream']['raw_tiles']-deployment['before_stream']['raw_tiles'] == deployment['raw_tiles']
            if old_end is not None:
                assert deployment['before_stream'] == old_end
            old_end = deployment['after_stream']
            assert row['online_realized_utility'] == pytest.approx(result['carrier']['phases'][phase]['realized_utility']
                +validation['realized_utility']+deployment['realized_utility'])
            assert [pair['seed'] for pair in validation['pairs']] == [core.validation_seed(2, phase_index, i) for i in range(8)]
            checkpoint_index = next(i for i, event in enumerate(records)
                if event['kind'] == 'SUBMISSION' and event['arm'] == arm and event['phase'] == phase)
            previous_games = [event for event in records[:checkpoint_index] if event['kind'] == 'VALIDATION_GAME'
                and event['arm'] == arm and event['phase'] == phase]
            assert len(previous_games) == 16
    source_pairs = result['arms']['FROZEN_H2']['phases']['B']['validation']['pairs']
    assert all(pair['candidate_submission_id'] == pair['incumbent_submission_id'] == 0 for pair in source_pairs)
    assert all(row['actor_weights_readonly'] and not row['td_examples'] for row in records
               if row['kind'] in ('CARRIER_TRAIN', 'VALIDATION_TRAIN', 'DEPLOYMENT_TRAIN'))


def test_three_science_components_preserve_saved_A_and_current_B_beliefs(monkeypatch, tmp_path):
    source, warmed, _ = prepare(monkeypatch)
    result = core.run_lifecycle(source, warmed, 1, lambda row: None, tmp_path)
    for arm in core.ARMS:
        value = result['arms'][arm]
        a, b, returned = (value['phases'][p] for p, _ in core.PHASES)
        assert a['retention_probe']['shared_with_current'] and a['retention_probe']['counts']['environment'] == {}
        assert b['retention_probe']['model_p_four'] == returned['retention_probe']['model_p_four'] == a['snapshot']['estimated_p_four']
        assert [game['seed'] for game in b['retention_probe']['game_summaries']] == [game['seed'] for game in a['game_summaries']]
        assert b['a_head_on_B']['model_p_four'] == b['snapshot']['estimated_p_four']
        assert [game['seed'] for game in b['a_head_on_B']['game_summaries']] == [game['seed'] for game in b['game_summaries']]
        assert value['evaluation_counts']['environment']['sampled_transitions'] == 6
        assert value['retention_evaluation_counts']['environment']['sampled_transitions'] == 4
        assert value['a_head_on_B_evaluation_counts']['environment']['sampled_transitions'] == 2


def test_actual_native_host_three_phases_three_arms_small_goal(monkeypatch):
    from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
    from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
    from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
    from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
    from acfqp.science.natural_model_revision_v281 import QUERY
    runtime = Path(__file__).resolve().parents[1]/'reports/shadow_deployment_v293/runtime/core_native'
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    native = NtupleValue(rule, runtime)
    native.weights.flags.writeable = False
    template = QueryTD(QueryParent(native, QUERY, QUERY, .5), 'PRIOR', runtime)
    template.freeze()
    warmed = SpawnMemory('LIBRARY')
    for index in range(256):
        warmed.observe(2 if index % 10 == 0 else 1)
    warm_payload, source_weights = warmed.to_payload(), template.weights.copy()
    monkeypatch.setattr(core, 'CARRIER_RAW_PER_PHASE', 120)
    monkeypatch.setattr(core, 'ONLINE_RAW_PER_PHASE', 4096)
    monkeypatch.setattr(core, 'EVALUATION_GAMES', 2)
    fixture_seed = 293000030000
    monkeypatch.setattr(core, 'carrier_seed', lambda life: fixture_seed+1)
    monkeypatch.setattr(core, 'validation_seed', lambda life, phase, pair: fixture_seed+1000+phase*100+pair)
    monkeypatch.setattr(core, 'deployment_seed', lambda life, arm: fixture_seed+2000+arm*100)
    monkeypatch.setattr(core, 'evaluation_seed', lambda life, phase, episode: fixture_seed+3000+phase*100+episode)
    records = []
    result = core.run_lifecycle(template, warmed, 15, records.append, runtime)
    assert result['carrier']['final_stream']['raw_tiles'] == 360
    assert result['carrier']['final_memory']['observations_seen'] == 616
    assert result['shadow']['new_value_updates'] > 0
    assert result['shadow']['fit_totals']['learning_counts']['td_updates'] == result['shadow']['new_value_updates']
    assert np.array_equal(source_weights, template.weights) and template.updates == 0
    assert warmed.to_payload() == warm_payload
    assert len(result['head_copies']) == 6
    for arm in core.ARMS:
        previous = None
        for phase, _ in core.PHASES:
            value = result['arms'][arm]['phases'][phase]
            assert value['online_raw_tiles'] == 4096
            assert len(value['validation']['game_summaries']) == 16
            assert not value['validation']['cutoff_games']
            assert all(game['status'] in ('WON', 'LOST') for game in value['game_summaries'])
            assert value['deployment']['raw_tiles'] == 4096-120-value['validation']['raw_tiles']
            if previous is not None:
                assert value['deployment']['before_stream'] == previous
            previous = value['deployment']['after_stream']
        b = result['arms'][arm]['phases']['B']
        assert b['a_head_on_B']['model_p_four'] == b['snapshot']['estimated_p_four']
    assert result['arms']['FROZEN_H2']['phases']['B']['game_summaries'] == result['arms']['FROZEN_H2']['phases']['B']['a_head_on_B']['game_summaries']
    assert all(not record['td_examples'] and record['leaf_updates_before'] == record['leaf_updates_after']
        for record in records if record['kind'] in ('CARRIER_TRAIN', 'VALIDATION_TRAIN', 'DEPLOYMENT_TRAIN'))
