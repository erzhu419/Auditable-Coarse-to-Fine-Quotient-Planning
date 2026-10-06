"""Reachable raw-physics, fixed-policy history, budget and scientific-claim failures."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_policy_data_v306 as audit


@pytest.fixture(scope='module')
def previous():
    return json.loads((ROOT/'reports/continual_v303/summary.json').read_text())['by_lifecycle'][0]


@pytest.fixture(scope='module')
def physical_prefix(previous):
    """One actual retained raw prefix; policy metadata adapts only the unit input shape."""
    with gzip.open(ROOT/'reports/continual_v303/parent_0_records.jsonl.gz', 'rt') as source:
        for line in source:
            row = json.loads(line)
            if row['kind'] == 'TRAIN':
                break
    row.update(arm='SOURCE_DATA', phase='A', model_p_four=previous['evaluation_beliefs']['A']['estimated_p_four'],
        actor_head_updates=0)
    for value in (row['start'], row['end'], *row['completed_games']):
        value['stream_seed'] = 306200000000
    count = row['counts']['planning'].get('value_predictions', 0)
    row['representation_counts'] = dict(risk_sigmoid_evaluations=count, local_risk_table_lookups=32*count,
        combined_value_additions=2*count, combined_value_multiplications=count)
    return row


def stream(previous):
    return audit.PhysicalStream(0, 'SOURCE_DATA', previous['evaluation_beliefs']['A'], 0)


@pytest.mark.parametrize('action', ('LEFT', 'RIGHT', 'UP', 'DOWN'))
def test_standard_swipe_merges_once_and_counts_actual_tile_values(action):
    board = [1]*16
    after, score = audit.swipe(board, action)
    assert score == 32 and after.count(2) == 8 and after.count(0) == 8


def test_actual_raw_prefix_rebuilds_board_pending_afterstate_and_raw_counts(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    rebuilt = stream(previous); rebuilt.train(deepcopy(physical_prefix))
    assert rebuilt.state == physical_prefix['end']
    assert rebuilt.fours == sum(value['rank'] == 2 for value in physical_prefix['raw_spawns'])


def test_occupied_initial_spawn_is_not_a_legal_raw_record(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    row = deepcopy(physical_prefix); row['raw_spawns'][1]['cell'] = row['raw_spawns'][0]['cell']
    with pytest.raises(ValueError, match='empty cell'):
        stream(previous).train(row)


def test_retained_merge_score_is_checked_against_actual_swipe(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    row = deepcopy(physical_prefix); row['scores'][0] += 4
    with pytest.raises(ValueError, match='independent merge score'):
        stream(previous).train(row)


def test_missing_pending_afterstate_is_not_a_matching_physical_boundary(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    row = deepcopy(physical_prefix); row['end']['pending_afterstate'] = None
    with pytest.raises(ValueError, match='end board pending state'):
        stream(previous).train(row)


def test_true_world_probability_cannot_replace_original_observed_planning_belief(previous, physical_prefix):
    row = deepcopy(physical_prefix); row['model_p_four'] = .1
    with pytest.raises(ValueError, match='original A1 observed belief'):
        stream(previous).check_context(row)


def test_current_actor_cannot_reset_the_retained_a1_parameter_history(previous, physical_prefix):
    row = deepcopy(physical_prefix); row.update(arm='CURRENT_DATA', actor_head_updates=0)
    rebuilt = audit.PhysicalStream(0, 'CURRENT_DATA', previous['evaluation_beliefs']['A'], 103775)
    with pytest.raises(ValueError, match='unchanged parameter history'):
        rebuilt.check_context(row)


def test_actor_does_not_fit_during_raw_acquisition(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    row = deepcopy(physical_prefix); row['counts']['learning'] = dict(td_updates=1)
    with pytest.raises(ValueError, match='remain frozen without training'):
        stream(previous).train(row)


def test_raw_seed_is_continuous_and_shared_not_synthetic_per_game(previous, physical_prefix, monkeypatch):
    monkeypatch.setattr(audit, 'CHUNK_RAW', len(physical_prefix['raw_spawns']))
    row = deepcopy(physical_prefix); row['start']['stream_seed'] += 1
    with pytest.raises(ValueError, match='same continuous seed'):
        stream(previous).train(row)


def initialization(previous):
    setup = previous['head_setup']['LOCAL_RISK']
    arms = {arm:dict(head_setup=deepcopy(setup)) for arm in audit.ARMS}
    for arm in audit.DATA_ARMS:
        counts = arms[arm]['head_setup']['setup_counts']; size = counts['source_parameters_copied']
        counts.update(a1_parameters_copied=2*size, a1_weight_bytes_copied=16*size)
    return dict(lifecycle=0, parent=0, evaluation_belief=deepcopy(previous['evaluation_beliefs']['A']),
        initial_fit=deepcopy(previous['stages']['A1']['arms']['LOCAL_RISK']['fit']),
        initial_head_setup=deepcopy(arms['A1_FROZEN']['head_setup']), arms=arms,
        datasets=dict.fromkeys(audit.DATA_ARMS, {}), acquisitions=dict.fromkeys(audit.DATA_ARMS, {}))


def test_two_learners_copy_reward_and_risk_from_identical_a1_parameters(previous):
    current = initialization(previous); assert audit.check_initialization(current, previous) == 103775
    current['arms']['CURRENT_DATA']['head_setup']['setup_counts']['a1_parameters_copied'] //= 2
    with pytest.raises(ValueError, match='complete A1 reward and risk'):
        audit.check_initialization(current, previous)


def test_a1_carrier_and_frozen_reference_share_one_allocation(previous):
    current = initialization(previous); current['initial_head_setup']['private_weight_bytes'] *= 2
    with pytest.raises(ValueError, match='one physical head allocation'):
        audit.check_initialization(current, previous)


def test_initial_fit_replays_full_a1_predictions_not_only_sample_count(previous):
    current = initialization(previous); current['initial_fit']['first_sample']['risk_probability'] += .01
    with pytest.raises(ValueError, match='V303 A1 numerical samples'):
        audit.check_initialization(current, previous)


def support():
    pairs = {left+'_minus_'+right:dict(ci95=[-.1, .2]) for left, right in audit.PAIRS}
    pairs[audit.PRIMARY]['ci95'] = [.2, .5]
    return dict(paired_contrasts=pairs, complete_game_endpoints=True,
        primary_policy_data_gain_supported=True, primary_policy_data_gain_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        current_policy_retention_status='UNRESOLVED', current_policy_no_degradation_supported=False,
        source_reference_gain_supported=dict(A1_FROZEN=False, SOURCE_DATA=False, CURRENT_DATA=False))


def test_actor_data_advantage_does_not_claim_a1_retention():
    value = support(); audit.check_support(value, 0)
    value['current_policy_no_degradation_supported'] = True
    with pytest.raises(ValueError, match='does not imply retention'):
        audit.check_support(value, 0)


def test_positive_source_gain_does_not_override_supported_a1_loss():
    value = support(); value['paired_contrasts']['CURRENT_DATA_minus_A1_FROZEN']['ci95'] = [-.5, -.2]
    value['current_policy_retention_status'] = 'SUPPORTED_LOSS'
    value['paired_contrasts']['CURRENT_DATA_minus_SOURCE']['ci95'] = [.1, .4]
    value['source_reference_gain_supported']['CURRENT_DATA'] = True
    audit.check_support(value, 0)
    value['current_policy_no_degradation_supported'] = True
    with pytest.raises(ValueError, match='does not imply retention'):
        audit.check_support(value, 0)


def test_new_game_cutoff_cannot_support_primary_actor_data_gain():
    with pytest.raises(ValueError, match='complete endpoints'):
        audit.check_support(support(), 1)


def budget():
    inherited = dict(source_training_raw_tiles=200, dynamics_raw_tiles=4)
    old = dict(by_lifecycle=[dict(stages=dict(A1=dict(acquisition=dict(warmup=dict(raw_tiles=256),
        training=dict(raw_tiles=audit.RAW))))) for _ in range(64)],
        accounting=dict(inherited_costs_per_arm=dict(SOURCE=inherited)))
    raw = 64*(audit.RAW+256); new_raw = dict.fromkeys(audit.DATA_ARMS, 64*audit.RAW)
    account = dict(inherited_a1_raw_tiles=raw, inherited_costs_per_arm=dict.fromkeys(audit.ARMS, inherited),
        economic_training_raw_tiles_per_arm={arm:204+raw+new_raw.get(arm, 0) for arm in audit.ARMS},
        new_training_raw_tiles_by_actor=new_raw, new_training_environment_observations=64*2*audit.RAW,
        physical_acquisitions=128, historical_total_compute_closed=False)
    return account, old


def test_raw_budget_matches_two_new_physical_cohorts_and_pays_a1_belief_for_source():
    account, old = budget(); expected = audit.check_training_budget(account, old)
    assert expected['CURRENT_DATA'] == expected['SOURCE_DATA']
    assert expected['CURRENT_DATA']-expected['A1_FROZEN'] == 64*audit.RAW
    account['economic_training_raw_tiles_per_arm']['SOURCE'] = 204
    with pytest.raises(ValueError, match='only updating learners pay'):
        audit.check_training_budget(account, old)


def test_new_physical_observations_do_not_omit_two_initial_tiles_or_tail():
    account, old = budget(); account['new_training_environment_observations'] -= 2
    with pytest.raises(ValueError, match='all initial and tail tiles'):
        audit.check_training_budget(account, old)


def test_new_actor_cohort_does_not_close_unknown_v303_historical_cpu():
    account, old = budget(); account['historical_total_compute_closed'] = True
    with pytest.raises(ValueError, match='unavailable original historical CPU'):
        audit.check_training_budget(account, old)
