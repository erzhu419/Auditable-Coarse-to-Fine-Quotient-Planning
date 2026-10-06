"""Finite reachable continual-receipt mutations, without world or weight replay."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_continual_v303 as audit


@pytest.fixture(scope='module')
def old_shapes():
    """Old compact receipts supply only finite shapes, never V303 observations."""
    return json.loads((ROOT/'reports/split_risk_v301/summary.json').read_text())['by_lifecycle'][0]


@pytest.mark.parametrize('stage',audit.STAGES)
def test_each_stage_has_fresh_registered_source_stream(stage):
    row = dict(lifecycle=7,arm='FROZEN',phase=stage,true_p_four=.5 if stage == 'B' else .1,
        start=dict(stream_seed=audit.training_seed(7,stage)))
    audit.check_acquisition_context(row)
    row['start']['stream_seed'] = audit.training_seed(7,audit.STAGES[(audit.STAGES.index(stage)+1)%3])
    with pytest.raises(ValueError,match='fresh independent stage training stream'):
        audit.check_acquisition_context(row)


@pytest.mark.parametrize('stage',audit.STAGES)
def test_true_task_context_and_frozen_actor_remain_explicit(stage):
    row = dict(lifecycle=0,arm='FROZEN',phase=stage,true_p_four=.5 if stage == 'B' else .1,
        start=dict(stream_seed=audit.training_seed(0,stage)))
    row['true_p_four'] = .1 if stage == 'B' else .5
    with pytest.raises(ValueError,match='actual environment context'):
        audit.check_acquisition_context(row)
    row['true_p_four'] = .5 if stage == 'B' else .1; row['arm'] = 'LOCAL_RISK'
    with pytest.raises(ValueError,match='original frozen SOURCE'):
        audit.check_acquisition_context(row)


def update_receipt(before,samples):
    return dict(fit=dict(trained_afterstates=samples),head_updates_before=before,head_updates_after=before+samples)


def test_later_fit_increments_prior_head_instead_of_resetting_counter():
    value = update_receipt(42,17)
    assert audit.check_update_chain(value,'LOCAL_RISK',42) == 59
    value['head_updates_before'] = 0; value['head_updates_after'] = 17
    with pytest.raises(ValueError,match='without reset or double fit'):
        audit.check_update_chain(value,'LOCAL_RISK',42)


def test_second_fit_cannot_charge_prior_samples_again():
    value = update_receipt(42,17); value['head_updates_after'] += 42
    with pytest.raises(ValueError,match='without reset or double fit'):
        audit.check_update_chain(value,'MC',42)


def test_source_is_unfitted_at_every_stage():
    assert audit.check_update_chain(update_receipt(0,0),'SOURCE',0) == 0
    value = update_receipt(0,1); value['head_updates_after'] = 0
    with pytest.raises(ValueError,match='SOURCE remains unfitted'):
        audit.check_update_chain(value,'SOURCE',0)


def test_later_local_fit_allows_retained_reward_and_risk_predictions(old_shapes):
    fit = deepcopy(old_shapes['arms']['LOCAL_RISK']['fit']); mc = old_shapes['arms']['MC']['fit']
    first = fit['first_sample']; first['risk_probability'] = .37; first['reward_prediction'] += .25
    first['risk_error'] = first['risk_target']-first['risk_probability']
    first['reward_error'] = first['reward_target']-first['reward_prediction']
    first['combined_prediction'] = first['reward_prediction']+8*(first['risk_probability']-.5)
    assert audit.check_local_fit(fit,mc,old_shapes['dataset'],'B') == fit['trained_afterstates']
    assert audit.check_local_fit(fit,mc,old_shapes['dataset'],'A2') == fit['trained_afterstates']
    with pytest.raises(ValueError,match='A1 starts at original SOURCE'):
        audit.check_local_fit(fit,mc,old_shapes['dataset'],'A1')


def test_later_local_fit_still_requires_factual_suffix_and_terminal_labels(old_shapes):
    fit = deepcopy(old_shapes['arms']['LOCAL_RISK']['fit']); mc = old_shapes['arms']['MC']['fit']
    fit['last_sample']['risk_target'] = 1-fit['last_sample']['risk_target']
    with pytest.raises(ValueError,match='targets exclude current reward and terminal bonus'):
        audit.check_local_fit(fit,mc,old_shapes['dataset'],'A2')


def evaluation(old_shapes,task):
    old = old_shapes['arms']['SOURCE']; games = deepcopy(old['game_summaries'])
    for episode,game in enumerate(games):
        game['seed'] = audit.evaluation_seed(0,task,episode)
    return dict(game_summaries=games,counts=deepcopy(old['evaluation_counts']),
        estimated_p_four=.097,static_evaluation_valid=True)


def test_same_task_evaluation_uses_fixed_first_belief_not_a2_observations(old_shapes):
    value = evaluation(old_shapes,'A'); belief = dict(estimated_p_four=.097)
    audit.check_evaluation(value,0,'A',belief)
    value['estimated_p_four'] = .105
    with pytest.raises(ValueError,match='fixed first-task observed belief'):
        audit.check_evaluation(value,0,'A',belief)


def test_other_task_seed_or_checkpoint_specific_seed_is_not_retention_pair(old_shapes):
    value = evaluation(old_shapes,'B'); belief = dict(estimated_p_four=.097)
    audit.check_evaluation(value,0,'B',belief)
    value['game_summaries'][0]['seed'] = audit.evaluation_seed(0,'A',0)
    with pytest.raises(ValueError,match='identical across checkpoints'):
        audit.check_evaluation(value,0,'B',belief)


def test_latest_a_observations_cannot_replace_first_a_fit_belief(old_shapes):
    ds = old_shapes['dataset']; memory = deepcopy(ds['fit_memory'])
    module = memory['modules'][memory['active_module_id']]
    belief = dict(memory=memory,estimated_p_four=module['alpha']/(module['alpha']+module['beta']))
    audit.check_belief(belief,ds)
    memory['observations_seen'] += 64
    with pytest.raises(ValueError,match='first-task complete FIT-prefix belief'):
        audit.check_belief(belief,ds)


def training_budget():
    inherited = dict(source_training_raw_tiles=200,source_training_games=1,
        source_training_environment_counts={},source_training_seconds=1.,dynamics_raw_tiles=4,dynamics_costs={})
    stage = dict(acquisition=dict(warmup=dict(raw_tiles=256)),dataset=dict(costs=dict(excluded_tail_raw_tiles=1)))
    lives = [dict(stages={key:stage for key in audit.STAGES}) for _ in range(64)]
    economic = 204+192*(audit.RAW+256)
    account = dict(physical_acquisitions=192,new_actor_raw_tiles=192*audit.RAW,new_warmup_raw_tiles=192*256,
        new_training_environment_observations=192*(audit.RAW+256),
        new_raw_tiles_by_stage=dict.fromkeys(audit.STAGES,64*(audit.RAW+256)),
        inherited_costs_per_arm={arm:inherited for arm in audit.ARMS},
        economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS,economic),excluded_tail_raw_tiles=192)
    return account,inherited,lives


def test_three_stages_charge_source_once_and_all_new_inputs():
    args = training_budget()
    assert audit.check_training_budget(*args) == 204+192*(audit.RAW+256)
    args[0]['economic_training_raw_tiles_per_arm']['LOCAL_RISK'] += 408
    with pytest.raises(ValueError,match='SOURCE/dynamics charged once'):
        audit.check_training_budget(*args)


def test_sequence_cannot_charge_only_final_stage_data():
    args = training_budget(); args[0]['new_actor_raw_tiles'] = 64*audit.RAW
    with pytest.raises(ValueError,match='all three fresh carriers'):
        audit.check_training_budget(*args)


def test_each_stage_warmup_and_excluded_tail_remain_paid():
    args = training_budget(); args[0]['new_raw_tiles_by_stage']['B'] -= 256
    with pytest.raises(ValueError,match='per-stage warmup and actor budget'):
        audit.check_training_budget(*args)
    args = training_budget(); args[0]['excluded_tail_raw_tiles'] -= 64
    with pytest.raises(ValueError,match='every unfinished stage tail remains paid'):
        audit.check_training_budget(*args)


def test_recovery_cannot_replace_original_logged_utility():
    value = dict(head_updates_before=23,head_updates_after=40,evaluations={'A':dict(
        game_summaries=[dict(utility=1.) for _ in range(32)],counts=dict(environment={'raw_tile_productions':128},planning={}))})
    event = dict(event='continual_arm_complete',lifecycle=0,stage='B',arm='LOCAL_RISK',updates_before=23,
        updates_after=40,utilities={'A':1.})
    document = dict(by_lifecycle=[dict(lifecycle=0,stages={'B':dict(arms={'LOCAL_RISK':value})})],
        recovery=dict(original_completed_arm_receipts=1,regenerated_logged_arm_receipts=1,
            interrupted_logged_evaluation_counts=dict(environment={'raw_tile_productions':128},planning={})))
    audit.check_old_logged_events(document,[event])
    event['utilities']['A'] = 1.1
    with pytest.raises(ValueError,match='preserved original utility/update receipt reproduced exactly'):
        audit.check_old_logged_events(document,[event])


def test_interruption_costs_remain_lower_bounds_instead_of_false_total_closure():
    account = dict(new_training_environment_observations=200,
        economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS,400))
    recovery = dict(status='RECOVERED_SAME_FROZEN_COHORT',original_exit_code=143,historical_total_compute_closed=False,
        interrupted_retained_raw_tiles=150,current_new_acquisition_raw_tiles=100,additional_retained_incomplete_prefix_raw_tiles=50,
        training_raw_tiles_physical_lower_bound=250,economic_training_raw_tiles_lower_bound_per_arm=dict.fromkeys(audit.ARMS,450))
    audit.check_recovery_cost_scope(recovery,account)
    recovery['historical_total_compute_closed'] = True
    with pytest.raises(ValueError,match='unretained compute stays unknown'):
        audit.check_recovery_cost_scope(recovery,account)


def test_actual_warmup_shape_has_phase_and_truth_without_training_arm_field():
    for stage in audit.STAGES:
        audit.check_stage_context(dict(kind='WARMUP',phase=stage,true_p_four=.5 if stage == 'B' else .1))


def test_a1_and_a2_splits_use_actual_phase_qualified_cost_and_memory_names(old_shapes):
    for stage in audit.STAGES:
        ds = deepcopy(old_shapes['dataset']); costs = ds['costs']
        costs['full_'+stage+'_raw_tiles'] = costs.pop('full_B_raw_tiles')
        costs['full_'+stage+'_acquisition_counts'] = costs.pop('full_B_acquisition_counts')
        games = [{key:value for key,value in game.items() if key != 'split'} for game in ds['games']]
        scores = {game['episode']:[game['score']]+[0]*(game['steps']-1) for game in games}
        fit_last = games[ds['fit_game_count']-1]['episode']; memories = {fit_last:audit.learned(ds['fit_memory'])}
        training = dict(after_stream=dict(post_action_spawns=costs['fit_steps']+costs['heldout_steps']+costs['excluded_tail_steps']),
            counts=costs['full_'+stage+'_acquisition_counts'])
        assert audit.check_stage_split(ds,games,scores,memories,costs['warmup_raw_tiles'],training,stage) == ds['fit_game_count']
