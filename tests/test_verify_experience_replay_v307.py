"""Independent source selection, factual suffix, retained-history and cost failures."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_experience_replay_v307 as audit


@pytest.fixture(scope='module')
def inputs():
    old = json.loads((ROOT/'reports/continual_v303/summary.json').read_text())['by_lifecycle'][0]
    current = json.loads((ROOT/'reports/policy_alignment_v306/summary.json').read_text())['by_lifecycle'][0]
    return old, current


def replay_life(inputs):
    old, current = inputs
    datasets = {audit.OLD:old['stages']['A1']['dataset'], audit.CURRENT:current['datasets'][audit.CURRENT]}
    plans, available = audit.expected_plans(datasets[audit.OLD], datasets[audit.CURRENT])
    offset = plans['MIXED_REPLAY']['fitted_full_steps']
    counts = dict(candidate_fit_games=sum(data['fit_game_count'] for data in datasets.values()),
        candidate_fit_afterstates=sum(data['fit_step_end'] for data in datasets.values()),
        selected_training_afterstates_per_arm=available[audit.CURRENT], copied_replay_afterstate_cells=16*offset,
        copied_replay_reward_values=offset, copied_replay_game_boundaries=len(plans['MIXED_REPLAY']['games']),
        selection_mask_bytes=4*(datasets[audit.CURRENT]['fit_step_end']+offset))
    return dict(lifecycle=0, parent=0, inputs=deepcopy(datasets),
        evaluation_belief=deepcopy(old['evaluation_beliefs']['A']),
        replay=dict(plans=plans, available=available, budget=available[audit.CURRENT], selection_counts=counts))


def test_actual_retained_fit_pools_supply_identical_supervised_budget(inputs):
    life = replay_life(inputs); audit.check_inputs_and_plans(life, *inputs)
    n = life['replay']['budget']; plans = life['replay']['plans']
    assert n == 105257
    assert plans['MIXED_REPLAY']['quotas'] == {audit.OLD:52628, audit.CURRENT:52629}
    assert all(sum(game['selected_count'] for game in plan['games']) == n for plan in plans.values())
    assert sum(game['steps'] for game in life['inputs'][audit.CURRENT]['games']) > life['inputs'][audit.CURRENT]['fit_step_end']


def test_full_game_breadth_first_selection_and_partial_midpoint_quantiles():
    rows = [dict(source=audit.OLD, source_game=i, eligible_steps=10) for i in range(5)]
    selected = audit.choose_source_games(rows, 23)
    assert [game['source_game'] for game in selected] == [1, 2, 4]
    assert [game['selected_count'] for game in selected] == [10, 10, 3]
    assert selected[-1]['selected_local_steps'] == [1, 5, 8]


@pytest.mark.parametrize('mutation', ('heldout', 'quota', 'terminal', 'order', 'partial', 'winning'))
def test_selected_source_game_step_identity_is_not_interchangeable(inputs, mutation):
    life = replay_life(inputs); plan = life['replay']['plans']['MIXED_REPLAY']; games = plan['games']
    if mutation == 'heldout':
        games[0]['source_game'] = life['inputs'][games[0]['source']]['fit_game_count']
    elif mutation == 'quota':
        plan['quotas'][audit.OLD] += 1
    elif mutation == 'terminal':
        games[0]['terminal_code'] *= -1
    elif mutation == 'order':
        games[0], games[1] = games[1], games[0]
    elif mutation == 'partial':
        next(game for game in games if game['selected_local_steps'] is not None)['selected_local_steps'][0] += 1
    else:
        game = next(game for game in games if game['terminal_code'] == 1)
        game['selected_local_steps'] = list(range(game['eligible_steps']))+[game['eligible_steps']]
    with pytest.raises(ValueError, match='source-game-step identities'):
        audit.check_inputs_and_plans(life, *inputs)


def test_mask_allocation_excludes_real_retained_heldout_afterstates(inputs):
    life = replay_life(inputs)
    total_steps = sum(game['steps'] for game in life['inputs'][audit.CURRENT]['games'])
    life['replay']['selection_counts']['selection_mask_bytes'] += 4*(total_steps-life['inputs'][audit.CURRENT]['fit_step_end'])
    with pytest.raises(ValueError, match='FIT-only mask allocations'):
        audit.check_inputs_and_plans(life, *inputs)


def test_current_inventory_cannot_be_replaced_by_source_actor_data(inputs):
    life = replay_life(inputs); life['inputs'][audit.CURRENT] = inputs[1]['datasets']['SOURCE_DATA']
    with pytest.raises(ValueError, match='current-policy factual inventories'):
        audit.check_inputs_and_plans(life, *inputs)


def test_replay_cannot_replace_observed_a1_probability_with_true_world_probability(inputs):
    life = replay_life(inputs); life['evaluation_belief']['estimated_p_four'] = .1
    with pytest.raises(ValueError, match='original observed A1 planning belief'):
        audit.check_inputs_and_plans(life, *inputs)


def target_example():
    plan = dict(games=[dict(source=audit.OLD, source_game=3, fit_start=0, fit_end=4,
        terminal_code=1, eligible_steps=3, selected_local_steps=[0, 2])])
    target = (8+16+2048)/2048.
    sample = dict(episode=0, step=0, reward_target=target, risk_target=1., reward_prediction=.25,
        risk_probability=.6, combined_prediction=.25+8*(.6-.5), reward_error=target-.25, risk_error=.4)
    return sample, plan, {(0, audit.OLD, 3):[4, 8, 16, 2048]}


def test_masked_target_keeps_unselected_future_and_winning_step_rewards():
    sample, plan, ledger = target_example(); audit.check_factual_sample(sample, plan, 0, ledger)
    sample['reward_target'] = 16/2048.
    with pytest.raises(ValueError, match='every unselected future reward'):
        audit.check_factual_sample(sample, plan, 0, ledger)


def test_replay_target_retains_original_natural_win_label():
    sample, plan, ledger = target_example(); sample['risk_target'] = 0.
    with pytest.raises(ValueError, match='original full natural game'):
        audit.check_factual_sample(sample, plan, 0, ledger)


def test_fitted_sample_cannot_select_an_unselected_or_winning_afterstate():
    sample, plan, ledger = target_example(); sample['step'] = 3
    with pytest.raises(ValueError, match='exact eligible selected source steps'):
        audit.check_factual_sample(sample, plan, 0, ledger)


def initialization(inputs):
    old, current = inputs
    arms = {arm:dict(head_setup=deepcopy(current['arms']['A1_FROZEN']['head_setup'])) for arm in audit.ARMS}
    for arm in audit.LEARNERS:
        arms[arm]['head_setup'] = deepcopy(current['arms']['CURRENT_DATA']['head_setup'])
    return dict(initial_fit=deepcopy(old['stages']['A1']['arms']['LOCAL_RISK']['fit']), arms=arms,
        initial_head_setup=deepcopy(arms['A1_FROZEN']['head_setup']))


def test_both_learners_copy_complete_a1_reward_and_risk_not_source_risk(inputs):
    life = initialization(inputs); assert audit.check_initialization(life, inputs[0]) == 103775
    life['arms']['MIXED_REPLAY']['head_setup']['setup_counts']['a1_parameters_copied'] //= 2
    with pytest.raises(ValueError, match='complete A1 reward and risk'):
        audit.check_initialization(life, inputs[0])


def test_a1_carrier_and_frozen_reference_are_one_physical_allocation(inputs):
    life = initialization(inputs); life['initial_head_setup']['private_weight_bytes'] *= 2
    with pytest.raises(ValueError, match='one physical head allocation'):
        audit.check_initialization(life, inputs[0])


def test_all_current_numerical_identity_ignores_only_new_mask_receipts_and_runtime(inputs):
    fit = deepcopy(inputs[1]['arms']['CURRENT_DATA']['fit'])
    fit.update(candidate_fitted_games=104, selected_games=104, selection_counts=dict(selected_nonwinning_afterstates=105257), seconds=0.)
    expected = audit.scientific_receipt(inputs[1]['arms']['CURRENT_DATA']['fit'])
    assert audit.original_fit_identity(fit) == expected
    fit['first_sample']['reward_prediction'] += .01
    with pytest.raises(ValueError):
        audit.equal_tree(audit.original_fit_identity(fit), expected, 'unchanged numerical new-only fit')


def budget():
    inherited = dict(source_training_raw_tiles=200, dynamics_raw_tiles=4)
    old = dict(accounting=dict(inherited_costs_per_arm=dict(SOURCE=inherited)),
        by_lifecycle=[dict(stages=dict(A1=dict(acquisition=dict(warmup=dict(raw_tiles=256), training=dict(raw_tiles=131072))))) for _ in range(64)])
    a1 = 64*(131072+256); current_raw = 64*131072
    current = dict(accounting=dict(new_training_raw_tiles_by_actor=dict(CURRENT_DATA=current_raw, SOURCE_DATA=current_raw)))
    account = dict(new_training_environment_observations=0, new_training_acquisitions=0,
        inherited_a1_raw_tiles=a1, inherited_current_raw_tiles=current_raw,
        inherited_costs_per_arm=dict.fromkeys(audit.ARMS, inherited), historical_total_compute_closed=False,
        economic_training_raw_tiles_per_arm={arm:204+a1+(current_raw if arm in audit.LEARNERS else 0) for arm in audit.ARMS})
    return account, old, current


def test_replay_charges_current_once_and_does_not_import_source_actor_costs():
    account, old, current = budget(); expected = audit.check_training_budget(account, old, current)
    assert expected['NEW_ONLY'] == expected['MIXED_REPLAY']
    assert expected['NEW_ONLY']-expected['A1_FROZEN'] == 64*131072
    account['economic_training_raw_tiles_per_arm']['MIXED_REPLAY'] += 64*131072
    with pytest.raises(ValueError, match='only replay learners pay'):
        audit.check_training_budget(account, old, current)


def test_reconstruction_is_not_a_new_training_environment_cohort():
    account, old, current = budget(); account['new_training_environment_observations'] = 64*131072
    with pytest.raises(ValueError, match='no new training environment data'):
        audit.check_training_budget(account, old, current)


def support():
    pairs = {left+'_minus_'+right:dict(ci95=[-.1, .2]) for left, right in audit.PAIRS}
    pairs[audit.PRIMARY]['ci95'] = [.2, .5]
    return dict(paired_contrasts=pairs, complete_game_endpoints=True,
        primary_replay_gain_supported=True, primary_replay_gain_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        replay_retention_status='UNRESOLVED', replay_no_degradation_supported=False,
        source_reference_gain_supported=dict(A1_FROZEN=False, NEW_ONLY=False, MIXED_REPLAY=False))


def test_replay_advantage_does_not_establish_a1_retention():
    value = support(); audit.check_support(value, 0); value['replay_no_degradation_supported'] = True
    with pytest.raises(ValueError, match='does not imply A1 retention'):
        audit.check_support(value, 0)


def test_source_gain_does_not_override_a1_loss():
    value = support(); value['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95'] = [-.5, -.2]
    value['replay_retention_status'] = 'SUPPORTED_LOSS'
    value['paired_contrasts']['MIXED_REPLAY_minus_SOURCE']['ci95'] = [.1, .4]
    value['source_reference_gain_supported']['MIXED_REPLAY'] = True
    audit.check_support(value, 0)


def test_zero_margin_retention_is_supported_but_cutoff_cannot_support_replay_gain():
    value = support(); value['paired_contrasts']['MIXED_REPLAY_minus_A1_FROZEN']['ci95'] = [0., .2]
    value.update(replay_retention_status='SUPPORTED_NONDECREASE', replay_no_degradation_supported=True)
    audit.check_support(value, 0)
    with pytest.raises(ValueError, match='complete endpoints'):
        audit.check_support(value, 1)
