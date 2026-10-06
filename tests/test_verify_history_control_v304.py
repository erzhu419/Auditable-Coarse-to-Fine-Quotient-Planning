"""Reachable matched-history receipt failures; no native fit or new worlds."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_history_control_v304 as audit


@pytest.fixture(scope='module')
def previous():
    return json.loads((ROOT/'reports/continual_v303/summary.json').read_text())['by_lifecycle'][0]


def inventory(previous):
    return dict(lifecycle=previous['lifecycle'],parent=previous['parent'],
        datasets={stage:deepcopy(previous['stages'][stage]['dataset']) for stage in ('A1','B')},
        evaluation_belief=deepcopy(previous['evaluation_beliefs']['B']))


def inherited(previous, old_arm):
    row = previous['stages']['B']['arms'][old_arm]
    return dict(fit_by_stage={stage:deepcopy(previous['stages'][stage]['arms'][old_arm]['fit'])
            for stage in ('A1','B')},
        head_updates_by_stage={stage:dict(before=previous['stages'][stage]['arms'][old_arm]['head_updates_before'],
            after=previous['stages'][stage]['arms'][old_arm]['head_updates_after']) for stage in ('A1','B')},
        head_updates=row['head_updates_after'],head_setup=deepcopy(previous['head_setup'][old_arm]),
        heldout=deepcopy(row['heldout']),evaluation=deepcopy(row['evaluations']['B']),
        evaluation_is_new=True,heldout_is_new=True)


def test_same_b_facts_exclude_a2_replacement(previous):
    current = inventory(previous); audit.check_inventory(current, previous)
    current['datasets']['B'] = previous['stages']['A2']['dataset']
    with pytest.raises(ValueError, match='same complete chronological'):
        audit.check_inventory(current, previous)


def test_fit_belief_cannot_use_true_probability_or_a2_memory(previous):
    current = inventory(previous); current['evaluation_belief']['estimated_p_four'] = .5
    with pytest.raises(ValueError, match='same original observed B'):
        audit.check_inventory(current, previous)


@pytest.mark.parametrize('arm', audit.INHERITED)
def test_inherited_fit_is_paid_once_before_same_b_fit(previous, arm):
    value = inherited(previous, audit.INHERITED[arm]); datasets = inventory(previous)['datasets']
    assert audit.check_update_chain(value, arm, datasets) == sum(audit.fit_samples(ds) for ds in datasets.values())
    value['head_updates_by_stage']['B']['before'] = 0
    with pytest.raises(ValueError, match='retain A1 exactly once'):
        audit.check_update_chain(value, arm, datasets)


def test_fresh_b_cannot_fit_a1_or_report_inherited_counter(previous):
    value = inherited(previous,'MC'); datasets = inventory(previous)['datasets']
    with pytest.raises(ValueError, match='exact fit-stage inventory'):
        audit.check_update_chain(value,'MC_FRESH_B',datasets)
    value['fit_by_stage'].pop('A1'); value['head_updates_by_stage'].pop('A1')
    samples = audit.fit_samples(datasets['B']); value['head_updates_by_stage']['B'] = dict(before=0,after=samples)
    with pytest.raises(ValueError, match='actual fitted history'):
        audit.check_update_chain(value,'MC_FRESH_B',datasets)


def test_source_reused_evaluation_must_not_be_new_cost():
    value = dict(fit_by_stage={},head_updates_by_stage={},head_updates=0,evaluation_is_new=False,heldout_is_new=False)
    assert audit.check_update_chain(value,'SOURCE',{}) == 0
    value['evaluation_is_new'] = True
    with pytest.raises(ValueError, match='reused and four fitted-head'):
        audit.check_update_chain(value,'SOURCE',{})


@pytest.mark.parametrize('old_arm', ('MC','LOCAL_RISK'))
def test_inherited_scientific_replay_allows_time_and_cache_difference(previous,old_arm):
    value = inherited(previous,old_arm)
    value['fit_by_stage']['B'].update(seconds=99.,cpu_seconds=13.,setup_counts={'cpp_library_cache_hits':100})
    value['evaluation'].update(seconds=22.,cpu_seconds=12.,setup_counts={'cpp_library_cache_hits':1})
    audit.check_reproduced_arm(value,previous,old_arm)


@pytest.mark.parametrize('old_arm', ('MC','LOCAL_RISK'))
def test_inherited_replay_rejects_changed_first_prediction_even_if_game_mean_matches(previous,old_arm):
    value = inherited(previous,old_arm)
    field = 'raw_prediction_before_update' if old_arm=='MC' else 'reward_prediction'
    value['fit_by_stage']['A1']['first_sample'][field] += .001
    with pytest.raises(ValueError, match='targets predictions gradients'):
        audit.check_reproduced_arm(value,previous,old_arm)


def test_inherited_full_game_actions_cannot_be_replaced_by_equal_utility(previous):
    value = inherited(previous,'MC'); game = value['evaluation']['game_summaries'][0]
    game['final_board'] = list(reversed(game['final_board']))
    with pytest.raises(ValueError, match='all paired B actions and terminal'):
        audit.check_reproduced_arm(value,previous,'MC')


def test_fresh_mc_has_fixed_b_targets_while_prediction_can_change(previous):
    original = previous['stages']['B']['arms']['MC']['fit']; fit = deepcopy(original)
    fit['first_sample']['raw_prediction_before_update'] += .2
    fit['first_sample']['error'] -= .2
    audit.check_mc_fit(fit,original,previous['stages']['B']['dataset'])
    fit['first_sample']['raw_target'] += .2
    with pytest.raises(ValueError, match='MC labels remain fixed'):
        audit.check_mc_fit(fit,original,previous['stages']['B']['dataset'])


def test_fresh_mc_cannot_change_normalization_or_b_sample_budget(previous):
    original = previous['stages']['B']['arms']['MC']['fit']; fit = deepcopy(original)
    fit['consolidation_counts']['sample_unique_addresses'] += 1
    with pytest.raises(ValueError, match='address normalization and work'):
        audit.check_mc_fit(fit,original,previous['stages']['B']['dataset'])


def test_reused_v303_seeds_cannot_be_changed_to_fresh_eval_seed(previous):
    value = deepcopy(previous['stages']['B']['arms']['SOURCE']['evaluations']['B'])
    audit.check_evaluation(value,0,'B',previous['evaluation_beliefs']['B'])
    value['game_summaries'][0]['seed'] += 1000000000
    with pytest.raises(ValueError, match='remain identical across checkpoints'):
        audit.check_evaluation(value,0,'B',previous['evaluation_beliefs']['B'])


@pytest.mark.parametrize('arm,old_arm', (('MC_FRESH_B','MC'),('LOCAL_FRESH_B','LOCAL_RISK')))
def test_private_head_copy_and_zero_logit_counts_remain_paid(previous,arm,old_arm):
    setup = deepcopy(previous['head_setup'][old_arm]); audit.check_head_setup(setup,arm)
    setup['setup_counts']['allocated_weight_bytes'] -= 8
    with pytest.raises(ValueError, match='private weight allocation'):
        audit.check_head_setup(setup,arm)


def support():
    pairs = {
        'LOCAL_FRESH_B_minus_LOCAL_AFTER_A1_B':dict(ci95=[.2,.5]),
        'MC_FRESH_B_minus_MC_AFTER_A1_B':dict(ci95=[-.1,.2]),
        'LOCAL_FRESH_B_minus_SOURCE':dict(ci95=[-.1,.2]),
        'MC_FRESH_B_minus_SOURCE':dict(ci95=[-.1,.2]),
        'LOCAL_AFTER_A1_B_minus_SOURCE':dict(ci95=[-.4,-.1]),
        'MC_AFTER_A1_B_minus_SOURCE':dict(ci95=[-.4,-.1])}
    return dict(paired_contrasts=pairs,complete_game_endpoints=True,
        history_effect_status=dict(LOCAL='SUPPORTED_PENALTY',MC='UNRESOLVED'),
        fresh_b_gain_supported=dict(LOCAL=False,MC=False),
        history_negative_transfer_supported=dict(LOCAL=True,MC=False),
        primary_history_penalty_supported=True,history_diagnosis='HISTORY_NEGATIVE_TRANSFER_SUPPORTED')


def test_history_penalty_does_not_claim_fresh_b_gain():
    value = support(); audit.check_support(value,0)
    value['fresh_b_gain_supported']['LOCAL'] = True
    with pytest.raises(ValueError,match='remain separate claims'):
        audit.check_support(value,0)


def test_history_penalty_without_absolute_source_loss_is_not_negative_transfer():
    value = support(); value['paired_contrasts']['LOCAL_AFTER_A1_B_minus_SOURCE']['ci95'] = [-.1,.1]
    with pytest.raises(ValueError,match='remain separate claims'):
        audit.check_support(value,0)
    value['history_negative_transfer_supported']['LOCAL'] = False
    value['history_diagnosis'] = 'HISTORY_INITIALIZATION_PENALTY_SUPPORTED'
    audit.check_support(value,0)


def test_cutoff_does_not_support_history_diagnosis():
    with pytest.raises(ValueError,match='remain separate claims'):
        audit.check_support(support(),1)


def budget():
    base = dict(source_training_raw_tiles=200,dynamics_raw_tiles=4)
    stage = dict(acquisition=dict(warmup=dict(raw_tiles=256),training=dict(raw_tiles=131072)))
    old = dict(by_lifecycle=[dict(stages=dict(A1=stage,B=stage)) for _ in range(64)],
        accounting=dict(inherited_costs_per_arm=dict(SOURCE=base)),
        recovery=dict(training_raw_tiles_physical_lower_bound=25600000))
    raw = 64*(131072+256)
    economic = {arm:204+raw+(raw if arm in audit.INHERITED else 0) for arm in audit.ARMS}
    account = dict(new_training_environment_observations=0,physical_acquisitions=0,
        inherited_raw_tiles_by_stage=dict(A1=raw,B=raw),inherited_costs_per_arm=dict.fromkeys(audit.ARMS,base),
        economic_training_raw_tiles_per_arm=economic,historical_sequence_physical_training_raw_tiles_lower_bound=25600000,
        historical_total_compute_closed=False)
    return account,old


def test_same_b_exposure_includes_source_observed_b_model_cost():
    account,old = budget(); expected = audit.check_training_budget(account,old)
    assert expected['SOURCE'] == expected['LOCAL_FRESH_B']
    assert expected['LOCAL_AFTER_A1_B']-expected['LOCAL_FRESH_B'] == account['inherited_raw_tiles_by_stage']['A1']
    account['economic_training_raw_tiles_per_arm']['SOURCE'] = 204
    with pytest.raises(ValueError,match='all arms pay observed B model data'):
        audit.check_training_budget(account,old)


def test_no_new_training_raw_and_all_retained_stage_warmups_remain_paid():
    account,old = budget(); account['new_training_environment_observations'] = 1
    with pytest.raises(ValueError,match='do not create new training acquisitions'):
        audit.check_training_budget(account,old)
    account,old = budget(); account['inherited_raw_tiles_by_stage']['A1'] -= 256
    with pytest.raises(ValueError,match='retained warmups complete actor boundaries'):
        audit.check_training_budget(account,old)


def test_matched_replay_does_not_close_unavailable_original_sequence_cpu():
    account,old = budget(); account['historical_total_compute_closed'] = True
    with pytest.raises(ValueError,match='unavailable historical CPU remain explicit'):
        audit.check_training_budget(account,old)
