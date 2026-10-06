"""Reachable receipt mutations; no worlds, fitting, canonical rereads or bootstrap."""
from copy import deepcopy
import json
from math import log
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_split_risk_v301 as audit


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
    with pytest.raises(ValueError, match='new V301 independent paired game seeds'):
        audit.check_evaluation(games, 0, counts)


def test_actual_eval_cost_cannot_omit_initial_spawns(old_life):
    games, counts = new_evaluation(old_life)
    counts['environment']['raw_tile_productions'] -= 64
    with pytest.raises(ValueError, match='actual evaluation costs including initial'):
        audit.check_evaluation(games, 0, counts)



def test_secondary_improvement_cannot_replace_source_gain():
    summary = dict(paired_contrasts=dict(
        GLOBAL_RISK_minus_SOURCE=dict(ci95=[-.2,.3]),
        GLOBAL_RISK_minus_MC=dict(ci95=[.1,.9])),
        heldout_contrasts=dict(mse=dict(ci95=[-1.,-.5])),
        split_risk_gain_supported=False,
        split_risk_gain_status='NOT_SUPPORTED_'+audit.INTERVAL_SCOPE)
    audit.check_support(summary,0)
    summary['split_risk_gain_supported']=True
    with pytest.raises(ValueError,match='secondary utility or prediction cannot substitute'):
        audit.check_support(summary,0)


def split_components(old_life):
    heldout = deepcopy(old_life['arms']['FROZEN']['heldout'])
    rows = []
    games = old_life['dataset']['games'][old_life['dataset']['fit_game_count']:]
    for utility,game in zip(heldout['game_metrics'],games):
        y = float(game['status']=='WON'); risk_bias = .5-y
        reward_bias = utility['bias']-8.*risk_bias
        rows.append(dict({key:utility[key] for key in ('episode','start','end','count')},
            win_label=y, mean_risk_probability=.5, risk_bias=risk_bias,
            risk_brier=.25,risk_log_loss=log(2.),reward_bias=reward_bias,
            reward_mse=reward_bias**2,reward_mae=abs(reward_bias)))
    heldout['component_game_metrics'] = rows
    return heldout


@pytest.mark.parametrize('mutation,message',[
    ('label','risk label is factual'),
    ('unbounded','bounded Bernoulli'),
    ('recount_terminal','recombine once'),
    ('drop_sample','same heldout afterstates')])
def test_split_component_targets_and_combination_are_fixed(old_life,mutation,message):
    heldout = split_components(old_life)
    result = audit.check_components(heldout,old_life['dataset'])
    assert result['samples']==sum(row['count'] for row in heldout['game_metrics'])
    component = heldout['component_game_metrics'][0]
    if mutation=='label':
        component['win_label'] = 1.-component['win_label']
    elif mutation=='unbounded':
        component['mean_risk_probability'] = 1.01
    elif mutation=='recount_terminal':
        heldout['game_metrics'][0]['bias'] += 4.
    else:
        component['count'] -= 1
    with pytest.raises(ValueError,match=message):
        audit.check_components(heldout,old_life['dataset'])


def split_fit(old_life,kind):
    mc = old_life['arms']['EPISODE_MEAN_MC']['fit']; dataset = old_life['dataset']
    games = dataset['games'][:dataset['fit_game_count']]
    steps = sum(game['steps'] for game in games); wins = sum(game['status']=='WON' for game in games)
    n = steps-wins; writes = mc['learning_counts']['table_updates']
    risk_writes = writes if kind=='LOCAL_RISK' else 20*len(games)
    products = mc['consolidation_counts']['sample_unique_addresses']
    rep = dict(risk_sigmoid_evaluations=n,combined_value_additions=2*n,combined_value_multiplications=n)
    if kind=='LOCAL_RISK': rep['local_risk_table_lookups']=32*n
    else:
        rep.update(global_feature_extractions=n,global_board_cell_visits=16*n,adjacent_pair_visits=24*n,
            global_line_cell_visits=32*n,global_dot_products=n,global_weight_reads=20*n,
            global_dot_multiplications=20*n,global_dot_additions=20*n,max_tile_neighbor_probes=4*n)
    fit = dict(method=kind,alpha=.0025,frozen_game_start_targets=True,fitted_games=len(games),fitted_steps=steps,
        trained_afterstates=n,reward_trained_afterstates=n,risk_trained_afterstates=n,
        learning_counts=dict(td_updates=n,value_predictions=n,table_lookups=(64 if kind=='LOCAL_RISK' else 32)*n,
            table_updates=writes+risk_writes,table_update_occurrences=32*n,reward_predictions=n,risk_predictions=n,
            reward_table_lookups=32*n,risk_table_lookups=32*n if kind=='LOCAL_RISK' else 0,
            reward_table_updates=writes,risk_parameter_updates=risk_writes),
        target_counts=dict(terminal_game_labels=len(games),risk_label_assignments=n,
            reward_suffix_target_assignments=steps,reward_suffix_additions=steps,
            goal_checks=steps,skipped_winning_afterstates=wins),representation_counts=rep,
        normalization_counts=dict(games_processed=len(games),feature_extractions=n,feature_occurrences=32*n,
            feature_digit_reads=192*n,feature_address_multiply_adds=192*n,sort_calls=len(games)+n,sort_items=64*n,
            denominator_occurrence_visits=32*n,game_unique_addresses=writes,
            reward_gradient_products=products,reward_gradient_accumulations=products,
            risk_gradient_products=products if kind=='LOCAL_RISK' else 20*n,
            risk_gradient_accumulations=products if kind=='LOCAL_RISK' else 20*n,
            global_denominator_accumulations=20*n if kind=='GLOBAL_RISK' else 0,
            normalization_divisions=writes+risk_writes,parameter_update_multiplications=writes+risk_writes,
            game_parameter_commits=len(games),reward_game_commits=len(games),risk_game_commits=len(games),
            reward_parameter_writes=writes,risk_parameter_writes=risk_writes,address_denominator_searches=products))
    for key in ('first_sample','last_sample'):
        row = mc[key]; y = float(games[row['episode']]['status']=='WON')
        reward_target = row['raw_target']-(4. if y else -4.)
        reward = row['raw_prediction_before_update']
        fit[key] = dict(episode=row['episode'],step=row['step'],reward_target=reward_target,risk_target=y,
            risk_probability=.5,reward_prediction=reward,combined_prediction=reward,
            reward_error=reward_target-reward,risk_error=y-.5)
    return fit,mc


@pytest.mark.parametrize('kind',['LOCAL_RISK','GLOBAL_RISK'])
def test_correct_two_head_fit_counts_are_accepted(old_life,kind):
    fit,mc = split_fit(old_life,kind)
    assert audit.check_split_fit(fit,mc,old_life['dataset'],kind)==mc['trained_afterstates']


@pytest.mark.parametrize('mutation,message',[
    ('current_reward','exclude current reward'),
    ('online','game-start predictions'),
    ('risk_samples','same complete-game nonwinning samples'),
    ('winning_only','risk labels use all nonwinning samples'),
    ('extra_writes','separate reward and risk sample lookups'),
    ('hidden_features','20 visible global features')])
def test_two_head_fit_scope_cannot_change(old_life,mutation,message):
    fit,mc = split_fit(old_life,'GLOBAL_RISK')
    if mutation=='current_reward': fit['first_sample']['reward_target'] += 1.
    elif mutation=='online': fit['frozen_game_start_targets'] = False
    elif mutation=='risk_samples': fit['risk_trained_afterstates'] -= 1
    elif mutation=='winning_only': fit['target_counts']['risk_label_assignments'] -= 1
    elif mutation=='extra_writes': fit['learning_counts']['table_updates'] += 1
    else: fit['representation_counts']['global_weight_reads'] += 1
    with pytest.raises(ValueError,match=message):
        audit.check_split_fit(fit,mc,old_life['dataset'],'GLOBAL_RISK')
