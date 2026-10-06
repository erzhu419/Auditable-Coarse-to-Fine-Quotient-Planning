"""Reachable observed-router, retained-head and claim/accounting failures."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_context_continual_v305 as audit


@pytest.fixture(scope='module')
def previous():
    return json.loads((ROOT/'reports/continual_v303/summary.json').read_text())['by_lifecycle'][0]


def training_route(memory, prototypes):
    statistics = audit.observed_statistics(memory)
    scores = audit.route_scores(statistics, prototypes)
    best = max(scores, key=lambda value:(value['log_bayes_factor'], -value['context_id'])) if scores else None
    created = best is None or best['log_bayes_factor'] < 0.
    context_id = len(prototypes) if created else best['context_id']
    before = None if created else dict(prototypes[context_id])
    after = dict(context_id=context_id, observations=statistics['observations'], fours=statistics['fours'], visits=1)
    if before:
        after.update(observations=before['observations']+statistics['observations'],
            fours=before['fours']+statistics['fours'], visits=before['visits']+1)
    return dict(statistics=statistics, scores=scores, context_id=context_id, created=created,
        prototype_before=before, prototype_after=after)


def prototypes(previous, stages=('A1', 'B')):
    values = []
    for stage in stages:
        memory = previous['stages'][stage]['dataset']['fit_memory']
        audit.check_training_route(training_route(memory, values), memory, values)
    return values


def test_actual_fit_counts_include_multiple_modules_and_pending_ranks(previous):
    memory = previous['stages']['B']['dataset']['fit_memory']
    statistics = audit.observed_statistics(memory)
    assert statistics['observations'] == 103915
    assert statistics['fours'] == 52030


def test_omitting_pending_raw_ranks_is_not_the_observed_fit_prefix(previous):
    memory = deepcopy(previous['stages']['B']['dataset']['fit_memory'])
    memory['pending']['n'] = 0; memory['pending']['fours'] = 0
    with pytest.raises(ValueError, match='uncommitted raw-rank'):
        audit.observed_statistics(memory)


def test_actual_retained_a_b_a_context_decisions_use_only_observed_counts(previous):
    values = []
    choices = []
    for stage in audit.STAGES:
        memory = previous['stages'][stage]['dataset']['fit_memory']
        choices.append(audit.check_training_route(training_route(memory, values), memory, values))
    assert choices == [(0, True), (1, True), (0, False)]
    assert [value['visits'] for value in values] == [2, 1]


def test_route_cannot_replace_whole_fit_counts_with_true_task_probability(previous):
    values = prototypes(previous, ('A1',))
    memory = previous['stages']['B']['dataset']['fit_memory']; route = training_route(memory, values)
    route['statistics']['fours'] = route['statistics']['observations']/2
    with pytest.raises(ValueError, match='observed FIT-prefix counts only'):
        audit.check_training_route(route, memory, values)


def test_negative_b_evidence_cannot_force_reuse_of_a_context(previous):
    values = prototypes(previous, ('A1',))
    memory = previous['stages']['B']['dataset']['fit_memory']; route = training_route(memory, values)
    route.update(context_id=0, created=False)
    with pytest.raises(ValueError, match='negative best evidence'):
        audit.check_training_route(route, memory, values)


def test_reactivated_a_prototype_receives_new_prefix_exactly_once(previous):
    values = prototypes(previous)
    memory = previous['stages']['A2']['dataset']['fit_memory']; route = training_route(memory, values)
    route['prototype_after']['observations'] += memory['observations_seen']
    with pytest.raises(ValueError, match='observation once'):
        audit.check_training_route(route, memory, values)


def test_static_eval_routes_existing_b_context_without_mutating_statistics(previous):
    values = prototypes(previous); before = deepcopy(values)
    belief = previous['evaluation_beliefs']['B']; statistics = audit.observed_statistics(belief['memory'])
    route = dict(statistics=statistics, scores=audit.route_scores(statistics, values), context_id=1)
    assert audit.check_evaluation_route(route, belief, values) == 1
    assert values == before
    route['context_id'] = 0
    with pytest.raises(ValueError, match='highest-evidence existing context'):
        audit.check_evaluation_route(route, belief, values)


def test_static_eval_cannot_use_later_a2_counts_for_original_a_belief(previous):
    values = prototypes(previous, audit.STAGES)
    belief = previous['evaluation_beliefs']['A']; statistics = audit.observed_statistics(belief['memory'])
    route = dict(statistics=statistics, scores=audit.route_scores(statistics, values), context_id=0)
    route['statistics'] = audit.observed_statistics(previous['stages']['A2']['dataset']['fit_memory'])
    with pytest.raises(ValueError, match='original frozen observed task'):
        audit.check_evaluation_route(route, belief, values)


def test_original_and_shared_controls_cannot_claim_new_evaluation_work(previous):
    old = previous['stages']['B']; value = deepcopy(old['arms']['LOCAL_RISK'])
    value.update(evaluation_is_new=False, heldout_is_new=False)
    audit.check_reused_arm(value, old, 'LOCAL_RISK')
    value['evaluation_is_new'] = True
    with pytest.raises(ValueError, match='without new physical work'):
        audit.check_reused_arm(value, old, 'LOCAL_RISK')


def test_reused_shared_control_cannot_change_a_terminal_outcome(previous):
    old = previous['stages']['B']; value = deepcopy(old['arms']['LOCAL_RISK'])
    value.update(evaluation_is_new=False, heldout_is_new=False)
    value['evaluations']['B']['game_summaries'][0]['utility'] += .01
    with pytest.raises(ValueError, match='full V303 arm receipts'):
        audit.check_reused_arm(value, old, 'LOCAL_RISK')


def test_private_context_heads_pay_both_reward_and_risk_allocation(previous):
    setup = deepcopy(previous['head_setup']['LOCAL_RISK']); audit.check_new_head(setup)
    setup['setup_counts']['allocated_weight_bytes'] //= 2
    with pytest.raises(ValueError, match='zero risk logits exactly once'):
        audit.check_new_head(setup)


def test_selected_context_fit_cannot_write_inactive_update_history():
    updates = [103775, 103194]
    row = dict(context_updates_before={'0':103775, '1':103194},
        context_updates_after={'0':206500, '1':103194})
    audit.check_context_updates(row, updates, 0, 102725)
    assert updates == [206500, 103194]
    updates = [103775, 103194]; row['context_updates_after']['1'] += 102725
    with pytest.raises(ValueError, match='only the selected context'):
        audit.check_context_updates(row, updates, 0, 102725)


def test_inactive_context_preservation_requires_full_terminal_outcomes(previous):
    original = previous['stages']['A1']['arms']['LOCAL_RISK']['evaluations']['A']
    current = deepcopy(original); current['seconds'] += 20.
    audit.check_equal_evaluation(current, original, 'inactive exact terminal outcomes')
    current['game_summaries'][0]['final_board'].reverse()
    with pytest.raises(ValueError, match='inactive exact terminal outcomes'):
        audit.check_equal_evaluation(current, original, 'inactive exact terminal outcomes')


def support():
    return dict(complete_game_endpoints=True, primary_repair_supported=True,
        primary_repair_status='SUPPORTED_'+audit.INTERVAL_SCOPE,
        final_ab_contrasts={'CONTEXT_LOCAL_minus_SHARED_LOCAL':dict(ci95=[.2, .6])},
        cells={cell:dict(paired_contrasts={'CONTEXT_LOCAL_minus_SOURCE':dict(ci95=[-.1, .4])})
            for cell in ('A2_A', 'A2_B')},
        final_task_gain_supported=dict(A=False, B=False), final_dual_task_gain_supported=False,
        checkpoint_contrasts={name:{'CONTEXT_LOCAL':dict(ci95=[0., 0.])} for name in audit.CHECKPOINTS},
        retention_status={name:'SUPPORTED_NONDECREASE' for name in ('A_after_B', 'B_after_A2', 'A_final_vs_A1')},
        retained_gain_supported=True, a_restoration_supported=False)


def test_shared_parameter_repair_does_not_establish_two_source_gains():
    value = support(); audit.check_support(value, 0)
    value['final_dual_task_gain_supported'] = True
    with pytest.raises(ValueError, match='individual final task gains'):
        audit.check_support(value, 0)


def test_retention_interval_crossing_zero_is_not_preservation():
    value = support(); value['checkpoint_contrasts']['A_final_vs_A1']['CONTEXT_LOCAL']['ci95'] = [-.1, .2]
    with pytest.raises(ValueError, match='do not establish preservation'):
        audit.check_support(value, 0)
    value['retention_status']['A_final_vs_A1'] = 'UNRESOLVED'; value['retained_gain_supported'] = False
    audit.check_support(value, 0)


def test_cutoff_blocks_repair_retention_and_gain_claims():
    with pytest.raises(ValueError, match='repair over shared parameters'):
        audit.check_support(support(), 1)


def budget():
    inherited = dict(source_training_raw_tiles=200, dynamics_raw_tiles=4)
    stage = dict(acquisition=dict(warmup=dict(raw_tiles=256), training=dict(raw_tiles=131072)))
    old = dict(by_lifecycle=[dict(stages=dict.fromkeys(audit.STAGES, stage)) for _ in range(64)],
        accounting=dict(inherited_costs_per_arm=dict(SOURCE=inherited)),
        recovery=dict(training_raw_tiles_physical_lower_bound=25600000))
    raw = dict.fromkeys(audit.STAGES, 64*(131072+256)); economic = 204+sum(raw.values())
    account = dict(new_training_environment_observations=0, physical_acquisitions=0,
        inherited_raw_tiles_by_stage=raw, inherited_costs_per_arm=dict.fromkeys(audit.ARMS, inherited),
        economic_training_raw_tiles_per_arm=dict.fromkeys(audit.ARMS, economic),
        historical_sequence_physical_training_raw_tiles_lower_bound=25600000, historical_total_compute_closed=False)
    return account, old


def test_context_bank_and_both_reference_arms_pay_full_observed_sequence():
    account, old = budget(); assert audit.check_training_budget(account, old) == 3*64*(131072+256)+204
    account['economic_training_raw_tiles_per_arm']['SOURCE'] = 204
    with pytest.raises(ValueError, match='every arm pays'):
        audit.check_training_budget(account, old)


def test_retained_data_reconstruction_does_not_create_new_training_acquisitions():
    account, old = budget(); account['physical_acquisitions'] = 192
    with pytest.raises(ValueError, match='no new training acquisition'):
        audit.check_training_budget(account, old)


def test_new_parameter_banks_do_not_repair_unavailable_historical_cpu():
    account, old = budget(); account['historical_total_compute_closed'] = True
    with pytest.raises(ValueError, match='unavailable historical CPU'):
        audit.check_training_budget(account, old)
