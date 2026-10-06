"""New finite linear-WIN contribution, labels and actual four-arm work cases."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_linear_contribution_v311 as audit


def factual_fit():
    # Two natural games: WON has three actions, LOST has two. The winning
    # afterstate is excluded, leaving four samples with four unique addresses
    # per sample and four addresses per game's normalized parameter commit.
    dataset = dict(games=[dict(episode=0, steps=3, status='WON'),
        dict(episode=1, steps=2, status='LOST')], fit_game_count=2, fit_step_end=5)
    mc = dict(learning_counts=dict(table_updates=8),
        consolidation_counts=dict(sample_unique_addresses=16),
        first_sample=dict(episode=0, step=0, raw_target=28., raw_prediction_before_update=4.),
        last_sample=dict(episode=1, step=1, raw_target=-4.))
    fit = dict(method='LINEAR_WIN2', alpha=.0025, frozen_game_start_targets=True,
        fitted_games=2, fitted_steps=5, trained_afterstates=4,
        reward_trained_afterstates=4, win_trained_afterstates=4,
        learning_counts=dict(td_updates=4, value_predictions=4, table_lookups=256,
            table_updates=16, table_update_occurrences=128,
            reward_predictions=4, win_predictions=4, reward_table_lookups=128,
            win_table_lookups=128, reward_table_updates=8, win_parameter_updates=8),
        target_counts=dict(terminal_game_labels=2, win_label_assignments=4,
            reward_suffix_target_assignments=5, reward_suffix_additions=5,
            goal_checks=5, skipped_winning_afterstates=1),
        normalization_counts=dict(games_processed=2, feature_extractions=4, feature_occurrences=128,
            feature_digit_reads=768, feature_address_multiply_adds=768,
            sort_calls=6, sort_items=256, denominator_occurrence_visits=128,
            game_unique_addresses=8, reward_gradient_products=16, reward_gradient_accumulations=16,
            win_gradient_products=16, win_gradient_accumulations=16, normalization_divisions=16,
            parameter_update_multiplications=16, game_parameter_commits=2,
            reward_game_commits=2, win_game_commits=2, reward_parameter_writes=8,
            win_parameter_writes=8, address_denominator_searches=16),
        representation_counts=dict(linear_win_table_lookups=128,
            combined_value_additions=8, combined_value_multiplications=4),
        first_sample=dict(episode=0, step=0, reward_target=24., win_target=1.,
            reward_prediction=4., win_prediction=.5, combined_prediction=4.,
            reward_error=20., win_error=.5),
        last_sample=dict(episode=1, step=1, reward_target=0., win_target=0.,
            reward_prediction=2., win_prediction=1.25, combined_prediction=8.,
            reward_error=-2., win_error=-1.25))
    return fit, mc, dataset


def setup():
    # Small parameter inventory keeps the byte relation visible; production
    # carries the actual SOURCE-sized tables through these same count fields.
    return dict(
        CONTEXT_MC=dict(source_weights_shared=False, private_weight_bytes=128,
            setup_counts=dict(source_parameters_copied=16, source_weight_bytes_copied=128,
                allocated_weight_parameters=16, allocated_weight_bytes=128)),
        CONTEXT_LINEAR_WIN=dict(source_weights_shared=False, private_weight_bytes=256,
            setup_counts=dict(source_parameters_copied=16, source_weight_bytes_copied=128,
                allocated_weight_parameters=32, allocated_weight_bytes=256,
                initialized_half_win_parameters=16)),
        CONTEXT_LOCAL=dict(source_weights_shared=False, private_weight_bytes=256,
            setup_counts=dict(source_parameters_copied=16, source_weight_bytes_copied=128,
                allocated_weight_parameters=32, allocated_weight_bytes=256,
                initialized_zero_risk_parameters=16)))


def test_active_two_table_linear_control_uses_win_labels_and_unclipped_prediction():
    fit, mc, dataset = factual_fit()
    assert audit.check_linear_fit(fit, mc, dataset) == 4
    assert fit['last_sample']['win_prediction'] > 1.
    audit.check_bank_setup(setup())


@pytest.mark.parametrize('key', ['first_sample','last_sample'])
def test_linear_terminal_target_cannot_be_loss_instead_of_win(key):
    fit, mc, dataset = factual_fit()
    fit[key]['win_target'] = 1.-fit[key]['win_target']
    with pytest.raises(ValueError, match='actual WIN rather than LOSS'):
        audit.check_linear_fit(fit, mc, dataset)


def test_reward_suffix_cannot_include_terminal_bonus():
    fit, mc, dataset = factual_fit(); fit['first_sample']['reward_target'] += 4.
    with pytest.raises(ValueError, match='reward target excludes terminal bonus'):
        audit.check_linear_fit(fit, mc, dataset)


@pytest.mark.parametrize('field', ['win_error','reward_error','combined_prediction'])
def test_frozen_linear_residuals_and_affine_combination_are_literal(field):
    fit, mc, dataset = factual_fit(); fit['last_sample'][field] += .1
    with pytest.raises(ValueError, match='R plus 8WIN minus 4'):
        audit.check_linear_fit(fit, mc, dataset)


def test_half_win_prediction_and_original_source_reward_are_required_for_every_new_bank():
    fit, mc, dataset = factual_fit()
    fit['first_sample'].update(win_prediction=0., combined_prediction=0., win_error=1.)
    with pytest.raises(ValueError, match='32 times 1/64'):
        audit.check_linear_fit(fit, mc, dataset)
    fit, mc, dataset = factual_fit()
    fit['first_sample'].update(reward_prediction=5., combined_prediction=5., reward_error=19.)
    with pytest.raises(ValueError, match='original SOURCE reward'):
        audit.check_linear_fit(fit, mc, dataset)


@pytest.mark.parametrize('field', ['table_lookups','table_updates','win_parameter_updates',
    'reward_table_updates','win_predictions','table_update_occurrences'])
def test_both_linear_tables_reads_and_writes_are_counted(field):
    fit, mc, dataset = factual_fit(); fit['learning_counts'][field] -= 1
    with pytest.raises(ValueError, match='both actual parameter writes are paid'):
        audit.check_linear_fit(fit, mc, dataset)


@pytest.mark.parametrize('field', ['normalization_divisions','win_gradient_products',
    'reward_gradient_accumulations','win_parameter_writes','reward_parameter_writes','win_game_commits'])
def test_linear_uses_matched_normalized_address_multiplicities_and_game_commits(field):
    fit, mc, dataset = factual_fit(); fit['normalization_counts'][field] -= 1
    with pytest.raises(ValueError, match='same game-start normalized address multiplicities'):
        audit.check_linear_fit(fit, mc, dataset)


def test_linear_win_cannot_fit_fewer_states_than_its_reward_and_scalar_mc():
    fit, mc, dataset = factual_fit(); fit['win_trained_afterstates'] = 3
    with pytest.raises(ValueError, match='same factual nonwinning afterstates'):
        audit.check_linear_fit(fit, mc, dataset)


@pytest.mark.parametrize('field', ['source_parameters_copied','source_weight_bytes_copied',
    'initialized_half_win_parameters','allocated_weight_parameters','allocated_weight_bytes'])
def test_linear_allocation_and_original_source_copy_are_real_work(field):
    value = setup(); value['CONTEXT_LINEAR_WIN']['setup_counts'][field] -= 1
    with pytest.raises(ValueError, match='full second WIN table'):
        audit.check_bank_setup(value)


def test_a_dummy_unallocated_linear_arm_is_not_a_capacity_matched_control():
    value = setup(); del value['CONTEXT_LINEAR_WIN']
    with pytest.raises(ValueError, match='all three matched learners'):
        audit.check_bank_setup(value)


@pytest.mark.parametrize('field', ['risk_sigmoid_evaluations','risk_log_loss_evaluations','win_clipping_calls'])
def test_linear_control_contains_no_sigmoid_log_loss_or_clipping_work(field):
    fit, mc, dataset = factual_fit(); fit['representation_counts'][field] = 1
    with pytest.raises(ValueError, match='without sigmoid or log loss'):
        audit.check_linear_fit(fit, mc, dataset)


def support(linear_lower=-.1):
    primary = linear_lower>0
    return dict(complete_game_endpoints=True, primary_local_over_linear_supported=primary,
        primary_local_over_linear_status=('SUPPORTED_' if primary else 'NOT_SUPPORTED_')+audit.INTERVAL_SCOPE,
        primary_local_over_mc_supported=True, primary_local_over_mc_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        final_ab_contrasts=dict(CONTEXT_LOCAL_minus_CONTEXT_LINEAR_WIN=dict(ci95=[linear_lower,.2]),
            CONTEXT_LOCAL_minus_CONTEXT_MC=dict(ci95=[.1,.2]), CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[.1,.2])),
        final_net_gain_supported=True, final_task_gain_supported=dict(A=True,B=False),
        final_dual_task_gain_supported=False,
        cells=dict(A3_A=dict(paired_contrasts=dict(CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[.1,.2]))),
            A3_B=dict(paired_contrasts=dict(CONTEXT_LOCAL_minus_SOURCE=dict(ci95=[-.1,.2])))),
        checkpoint_contrasts={name:dict(CONTEXT_LOCAL=dict(ci95=[0.,0.])) for name in audit.CHECKPOINTS},
        retention_status={name:'SUPPORTED_NONDECREASE' for name in audit.CHECKPOINTS},
        retention_supported=True, retained_gain_supported=primary)


def test_mc_gain_cannot_replace_new_linear_contribution_primary():
    value = support(); audit.check_support(value, 0)
    value['primary_local_over_linear_supported'] = value['retained_gain_supported'] = True
    with pytest.raises(ValueError, match='matched-capacity linear WIN interval'):
        audit.check_support(value, 0)


def test_positive_linear_primary_cannot_hide_literal_negative_local_retention():
    value = support(.1); value['checkpoint_contrasts']['A_return_A2']['CONTEXT_LOCAL']['ci95'] = [-.2,-.1]
    value['retention_status']['A_return_A2'] = 'SUPPORTED_LOSS'
    value['retention_supported'] = value['retained_gain_supported'] = False
    audit.check_support(value, 0)
    value['retained_gain_supported'] = True
    with pytest.raises(ValueError, match='all seven literal zero-margin'):
        audit.check_support(value, 0)


def test_linear_evaluation_probability_must_match_actual_selected_bank_for_four_arms():
    belief = dict(memory={}, estimated_p_four=.37)
    row = dict(evaluation_routes={'A':dict(context_id=2)}, planning_beliefs={'A':belief},
        arms={arm:dict(evaluations={'A':dict(estimated_p_four=.37)}) for arm in audit.ARMS})
    audit.check_bank_planning_beliefs(row, {'2':belief}, ('A',))
    row['arms']['CONTEXT_LINEAR_WIN']['evaluations']['A']['estimated_p_four'] = .1
    with pytest.raises(ValueError, match='all.*|SOURCE MC LINEAR_WIN and LOCAL share'):
        audit.check_bank_planning_beliefs(row, {'2':belief}, ('A',))
