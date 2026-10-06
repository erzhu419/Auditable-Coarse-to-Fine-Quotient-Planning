"""Reachable confirmation receipt mutations, without worlds, fitting or bootstrap."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_local_risk_v302 as audit


@pytest.fixture(scope='module')
def development_life():
    """Old compact receipts provide finite shapes, never fresh confirmation evidence."""
    return json.loads((ROOT/'reports/split_risk_v301/summary.json').read_text())['by_lifecycle'][0]


@pytest.mark.parametrize('base', [298200000000, 301200000000])
def test_new_training_cannot_reuse_development_streams(base):
    row = dict(lifecycle=7,arm='FROZEN',phase='B',true_p_four=.5,
        start=dict(stream_seed=audit.training_seed(7)))
    audit.check_acquisition_context(row)
    row['start']['stream_seed'] = base+7*10000000
    with pytest.raises(ValueError, match='independent B training stream'):
        audit.check_acquisition_context(row)


def test_training_actor_cannot_be_a_fitted_local_head():
    row = dict(lifecycle=0,arm='LOCAL_RISK',phase='B',true_p_four=.5,
        start=dict(stream_seed=audit.training_seed(0)))
    with pytest.raises(ValueError, match='frozen SOURCE actor'):
        audit.check_acquisition_context(row)


@pytest.mark.parametrize('phase,p', [('A', .5), ('B', .1)])
def test_new_world_context_remains_stable_b(phase,p):
    row = dict(lifecycle=0,arm='FROZEN',phase=phase,true_p_four=p,
        start=dict(stream_seed=audit.training_seed(0)))
    with pytest.raises(ValueError, match='stable B actual environment'):
        audit.check_acquisition_context(row)


def new_evaluation(life):
    arm = life['arms']['SOURCE']; games = deepcopy(arm['game_summaries'])
    for episode,game in enumerate(games):
        game['seed'] = audit.evaluation_seed(0,episode)
    return games,deepcopy(arm['evaluation_counts'])


@pytest.mark.parametrize('seed', [298900000000,301900000000,302200000000])
def test_evaluation_is_separate_from_old_science_and_new_training(development_life,seed):
    games,counts = new_evaluation(development_life)
    audit.check_evaluation(games,0,counts)
    games[0]['seed'] = seed
    with pytest.raises(ValueError, match='V302 independent paired evaluation seeds'):
        audit.check_evaluation(games,0,counts)


def test_evaluation_costs_include_initial_spawns(development_life):
    games,counts = new_evaluation(development_life)
    counts['environment']['raw_tile_productions'] -= 64
    with pytest.raises(ValueError, match='physical ledger'):
        audit.check_evaluation(games,0,counts)


def split_inputs(life):
    ds = deepcopy(life['dataset']); games = [{k:v for k,v in game.items() if k != 'split'} for game in ds['games']]
    scores = {game['episode']:[game['score']]+[0]*(game['steps']-1) for game in games}
    fit_last = games[ds['fit_game_count']-1]['episode']
    memories = {fit_last:audit.learned(ds['fit_memory'])}
    costs = ds['costs']; warm = costs['warmup_raw_tiles']
    training = dict(after_stream=dict(post_action_spawns=costs['fit_steps']+costs['heldout_steps']+costs['excluded_tail_steps']),
        counts=costs['full_B_acquisition_counts'])
    return ds,games,scores,memories,warm,training


def test_fit_prefix_cannot_observe_heldout_ranks(development_life):
    args = split_inputs(development_life)
    audit.check_split(*args)
    args[0]['fit_memory']['observations_seen'] += 64
    with pytest.raises(ValueError, match='heldout/future leaked'):
        audit.check_split(*args)


def test_unfinished_target_tail_remains_paid(development_life):
    args = split_inputs(development_life)
    args[0]['costs']['excluded_tail_raw_tiles'] += 1
    with pytest.raises(ValueError, match='paid full acquisition/excluded tail ledger'):
        audit.check_split(*args)


def test_frozen_local_fit_keeps_both_reward_and_risk_heads(development_life):
    fit = deepcopy(development_life['arms']['LOCAL_RISK']['fit']); mc = development_life['arms']['MC']['fit']
    assert audit.check_split_fit(fit,mc,development_life['dataset'],'LOCAL_RISK') == mc['trained_afterstates']
    fit['learning_counts']['risk_parameter_updates'] -= 1
    with pytest.raises(ValueError, match='separate reward and risk'):
        audit.check_split_fit(fit,mc,development_life['dataset'],'LOCAL_RISK')


def test_all_nonwinning_samples_get_factual_terminal_labels(development_life):
    fit = deepcopy(development_life['arms']['LOCAL_RISK']['fit']); mc = development_life['arms']['MC']['fit']
    fit['target_counts']['risk_label_assignments'] -= 1
    with pytest.raises(ValueError, match='risk labels use all nonwinning samples'):
        audit.check_split_fit(fit,mc,development_life['dataset'],'LOCAL_RISK')


def test_local_factual_heldout_components_are_preserved(development_life):
    local = deepcopy(development_life['arms']['LOCAL_RISK']['heldout'])
    source = development_life['arms']['SOURCE']['heldout']
    audit.check_split_heldout(local,source,development_life['dataset'],'LOCAL_RISK')
    local['component_game_metrics'][0]['win_label'] = 1.-local['component_game_metrics'][0]['win_label']
    with pytest.raises(ValueError, match='risk label is factual'):
        audit.check_split_heldout(local,source,development_life['dataset'],'LOCAL_RISK')


@pytest.mark.parametrize('ci,cutoffs', [([-.2,.3],0),([.1,.6],1)])
def test_source_gain_and_complete_endpoints_are_both_required(ci,cutoffs):
    summary = dict(paired_contrasts={'LOCAL_RISK_minus_SOURCE':dict(ci95=ci),
        'LOCAL_RISK_minus_MC':dict(ci95=[.5,1.5])},independent_local_learning_confirmed=False,
        independent_local_learning_status='NOT_CONFIRMED_'+audit.INTERVAL_SCOPE)
    audit.check_support(summary,cutoffs)
    summary['independent_local_learning_confirmed'] = True
    with pytest.raises(ValueError, match='against SOURCE is the confirmation endpoint'):
        audit.check_support(summary,cutoffs)


def test_positive_primary_is_correct_without_claiming_fresh_source():
    summary = dict(paired_contrasts={'LOCAL_RISK_minus_SOURCE':dict(ci95=[.1,.6])},
        independent_local_learning_confirmed=True,
        independent_local_learning_status='CONFIRMED_'+audit.INTERVAL_SCOPE)
    audit.check_support(summary,0)


def test_old_retained_training_interval_scope_is_not_new_confirmation(development_life):
    values = [float(i%3-1) for i in range(64)]
    saved = dict(mean=sum(values)/64,ci95=[-1.,1.],interval_scope=audit.INTERVAL_SCOPE,
        lifecycle_deltas={str(i):value for i,value in enumerate(values)},
        parent_mean_deltas={str(p):sum(values[p::4])/16 for p in range(4)},
        improved_equal_worse=[values.count(1.),values.count(0.),values.count(-1.)],
        adverse_lifecycles=[i for i,value in enumerate(values) if value < 0])
    audit.check_contrast(saved,values,'higher_is_better')
    saved['interval_scope'] += '_AND_RETAINED_B_TRAINING'
    with pytest.raises(ValueError, match='fresh training whole-life conditional interval scope'):
        audit.check_contrast(saved,values,'higher_is_better')


def training_budget():
    inherited = dict(source_training_raw_tiles=200,source_training_games=1,
        source_training_environment_counts={},source_training_seconds=1.,dynamics_raw_tiles=4,dynamics_costs={})
    warm = dict(raw_tiles=256,environment_counts=dict(raw_tile_productions=256),direct_counts={},memory_counts={})
    training = dict(counts=dict(environment=dict(raw_tile_productions=audit.RAW),planning={},learning={}),memory_counts={})
    reconstruction = dict(counts={},memory_counts={},cpu_seconds=0.)
    lives = [dict(acquisition=dict(warmup=warm,training=training,reconstruction=reconstruction),
        dataset=dict(costs=dict(excluded_tail_raw_tiles=1))) for _ in range(64)]
    economic = 204+64*(audit.RAW+256)
    accounting = dict(new_training_environment_observations=64*(audit.RAW+256),physical_acquisitions=64,
        new_warmup_raw_tiles=64*256,new_actor_B_raw_tiles=64*audit.RAW,
        inherited_costs_per_arm={arm:inherited for arm in audit.ARMS},
        economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS,economic),excluded_tail_raw_tiles=64,
        new_actor_B_counts=dict(environment=dict(raw_tile_productions=64*audit.RAW),planning={},learning={}),
        new_warmup_environment_counts=dict(raw_tile_productions=64*256),new_warmup_direct_counts={},
        new_warmup_memory_counts={},new_actor_memory_counts={},
        new_training_environment_counts=dict(raw_tile_productions=64*(audit.RAW+256)),
        reconstruction_counts={},reconstruction_memory_counts={},reconstruction_cpu_seconds=0.)
    return accounting,inherited,lives


def test_old_development_b_raw_cannot_enter_new_confirmation_input():
    args = training_budget()
    assert audit.check_training_budget(*args) == args[0]['economic_training_raw_tiles_per_arm']['SOURCE']
    args[0]['economic_training_raw_tiles_per_arm']['LOCAL_RISK'] += 8418915
    with pytest.raises(ValueError, match='all NEW B raw'):
        audit.check_training_budget(*args)


def test_initial_and_excluded_new_raw_cannot_be_replaced_by_fit_samples():
    args = training_budget()
    args[0]['new_actor_B_raw_tiles'] -= 64
    with pytest.raises(ValueError, match='all fresh B raw and warmup are paid'):
        audit.check_training_budget(*args)


def test_excluded_tail_is_not_a_free_training_budget_reduction():
    args = training_budget()
    args[0]['excluded_tail_raw_tiles'] = 0
    with pytest.raises(ValueError, match='unfinished new actor tail remains paid'):
        audit.check_training_budget(*args)
