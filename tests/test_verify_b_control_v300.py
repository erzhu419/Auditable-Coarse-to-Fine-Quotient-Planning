"""Reachable receipt mutations; no worlds, fitting, canonical rereads or bootstrap."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_b_control_v300 as audit


@pytest.fixture(scope='module')
def old_life():
    return json.loads((ROOT/'reports/stable_b_v298/summary.json').read_text())['by_lifecycle'][0]


def test_fixed_prefix_belief_cannot_be_replaced_by_true_b_probability(old_life):
    current = deepcopy(old_life)
    audit.check_retained_inventory(current, old_life)
    current['evaluation_snapshot']['estimated_p_four'] = .5
    assert old_life['evaluation_snapshot']['estimated_p_four'] != .5
    with pytest.raises(ValueError, match='same blind fit-prefix belief'):
        audit.check_retained_inventory(current, old_life)


def test_fit_cannot_consume_a_heldout_complete_game(old_life):
    current = deepcopy(old_life)
    current['dataset']['fit_game_count'] += 1
    with pytest.raises(ValueError, match='fixed complete B training and heldout inventory'):
        audit.check_retained_inventory(current, old_life)


def test_mc_reproduction_checks_examples_not_only_producer_flag(old_life):
    previous = old_life['arms']['EPISODE_MEAN_MC']; current = deepcopy(previous)
    current['fit']['consolidation_counts']['native_buffer_bytes_peak'] += 8
    audit.check_mc_reproduction(current, previous)
    current['fit']['last_sample']['target'] += 1.
    with pytest.raises(ValueError, match='original MC nonpeak fit counts and examples'):
        audit.check_mc_reproduction(current, previous)


def test_original_source_mc_heldout_cannot_silently_change(old_life):
    previous = old_life['arms']['EPISODE_MEAN_MC']; current = deepcopy(previous)
    current['heldout']['game_metrics'][-1]['mse'] += .1
    with pytest.raises(ValueError, match='original full heldout MC reproduction'):
        audit.check_mc_reproduction(current, previous)


def test_control_full_heldout_cannot_drop_a_loss_game(old_life):
    previous = old_life['arms']['FROZEN']['heldout']; current = deepcopy(previous)
    audit.check_heldout(current, previous)
    current['game_metrics'].pop()
    with pytest.raises(ValueError, match='same complete heldout games'):
        audit.check_heldout(current, previous)


def test_control_full_heldout_cannot_replace_factual_mc_labels(old_life):
    previous = old_life['arms']['FROZEN']['heldout']; current = deepcopy(previous)
    current['game_metrics'][0]['mean_factual_future_utility'] += 1.
    with pytest.raises(ValueError, match='same factual full heldout labels and samples'):
        audit.check_heldout(current, previous)


def new_evaluation(old_life):
    arm = old_life['arms']['FROZEN']; games = deepcopy(arm['game_summaries'])
    for episode, game in enumerate(games):
        game['seed'] = audit.EVALUATION_BASE+episode
    return games, deepcopy(arm['evaluation_counts'])


def test_new_evaluation_cannot_reuse_v298_science_seeds(old_life):
    games, counts = new_evaluation(old_life)
    audit.check_evaluation(games, 0, counts)
    games[0]['seed'] = 298900000000
    with pytest.raises(ValueError, match='new V300 independent paired game seeds'):
        audit.check_evaluation(games, 0, counts)


def test_actual_eval_cost_cannot_omit_initial_spawns(old_life):
    games, counts = new_evaluation(old_life)
    counts['environment']['raw_tile_productions'] -= 64
    with pytest.raises(ValueError, match='actual evaluation costs including initial'):
        audit.check_evaluation(games, 0, counts)


def control_receipt(old_life):
    mc = old_life['arms']['EPISODE_MEAN_MC']['fit']; control = deepcopy(mc)
    samples = mc['trained_afterstates']; outcomes = 2*samples
    games = old_life['dataset']['games'][:old_life['dataset']['fit_game_count']]
    control.update(method='EXPECTED_CONTROL_MEAN',game_head_targets_frozen=True,
        model_p_four=old_life['evaluation_snapshot']['estimated_p_four'],
        target_counts=dict(goal_checks=sum(game['steps'] for game in games),
            raw_target_subtractions=samples,skipped_winning_afterstates=sum(game['status']=='WON' for game in games)),
        planning_counts=dict(expected_control_target_assignments=samples,
            empty_cell_count_visits=16*samples,empty_cell_branch_visits=16*samples,
            generated_spawn_outcomes=outcomes,leaf_choose_calls=outcomes,expanded_postspawn_states=outcomes,
            spawn_rank1_outcomes=samples,spawn_rank2_outcomes=samples,
            expectimax_probability_products=outcomes,expectimax_probability_sums=outcomes,
            spawn_board_cells_copied=16*outcomes,second_ply_swipe_calls=4*outcomes,
            learned_swipe_calls=4*outcomes,line_table_lookups=16*outcomes))
    return control,mc


@pytest.mark.parametrize('mutation,message',[
    ('true_probability','fixed observed B prefix belief'),
    ('unfrozen_target','game-start head'),
    ('extra_writes','target-only change preserves'),
    ('missing_branch','expected spawn branches probabilities')])
def test_control_target_and_update_must_stay_in_frozen_scope(old_life,mutation,message):
    control,mc = control_receipt(old_life); dataset = old_life['dataset']
    p = old_life['evaluation_snapshot']['estimated_p_four']
    audit.check_control_fit(control,mc,dataset,p)
    if mutation=='true_probability':
        control['model_p_four']=.5
    elif mutation=='unfrozen_target':
        control['game_head_targets_frozen']=False
    elif mutation=='extra_writes':
        control['learning_counts']['table_updates']+=1
    else:
        control['planning_counts']['generated_spawn_outcomes']+=1
    with pytest.raises(ValueError,match=message):
        audit.check_control_fit(control,mc,dataset,p)


def test_secondary_improvement_cannot_replace_source_gain():
    summary = dict(paired_contrasts=dict(
        EXPECTED_CONTROL_minus_SOURCE=dict(ci95=[-.2,.3]),
        EXPECTED_CONTROL_minus_MC=dict(ci95=[.1,.9])),
        heldout_contrasts=dict(mse=dict(ci95=[-1.,-.5])),
        control_target_gain_supported=False,
        control_target_gain_status='NOT_SUPPORTED_'+audit.INTERVAL_SCOPE)
    audit.check_support(summary,0)
    summary['control_target_gain_supported']=True
    with pytest.raises(ValueError,match='secondary utility or prediction cannot substitute'):
        audit.check_support(summary,0)
