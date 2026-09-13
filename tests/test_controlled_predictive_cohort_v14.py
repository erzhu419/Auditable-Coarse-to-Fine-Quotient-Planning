import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v13 import cases_v13
from acfqp.science.controlled_predictive_cohort_v14 import (
    EXECUTION_ARMS, GOAL_QUERY_PAIRS, REFERENCE_ARMS, V13_ROSTER,
    build_cohort_roster_v14, cases_v14, freeze_cohort_roster_v14,
)


def test_v14_preserves_inputs_and_freezes_mass_groups_without_target_simulation():
    source = json.loads((DEFAULT_REPORTS_DIR / V13_ROSTER).read_text())
    roster = build_cohort_roster_v14()
    assert cases_v14() == cases_v13()
    assert [record['case'] for record in roster['cases']] == [record['case'] for record in source['cases']]
    for key in ('sample_seeds', 'queries', 'initial_query_order', 'query_roles', 'historical_exposure',
                'scenarios', 'historical_primary_case_splits', 'row_stream'):
        assert roster[key] == source[key]
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16, 48, 480)
    excluded = []
    for record in roster['cases']:
        case = record['case']
        mass = sum(2**rank for rank in case['board'] if rank)
        assert record['total_tile_mass'] == mass
        assert record['mass_plus_4h'] == mass + 4 * case['horizon']
        assert record['goal_mass_excluded'] == (mass + 4 * case['horizon'] < 2048)
        if record['goal_mass_excluded']:
            excluded.append(case['name'])
    assert roster['root_mass_groups']['goal_mass_excluded'] == excluded
    assert roster['mechanism_comparison']['case_names'] == excluded
    assert roster['mechanism_query_pairs'] == [{'goal_query': a, 'no_goal_query': b} for a, b in GOAL_QUERY_PAIRS]
    assert not roster['source_fitting_enabled'] and not roster['source_priority_enabled']
    assert roster['source_fees'] == 0 and not roster['lofo_scenarios_reexecuted']


def test_v14_freezes_independent_variants_budgets_examples_and_read_only_legacy_comparison(tmp_path):
    roster = build_cohort_roster_v14()
    assert roster['variants'] == ['LEGACY', 'MASS_BOUND']
    assert roster['stage_a']['row_checkpoints'] == [32, 128]
    assert roster['stage_a']['trajectory_count'] == 96
    assert roster['stage_b']['execution_arms'] == list(EXECUTION_ARMS)
    assert roster['stage_b']['reference_arms'] == list(REFERENCE_ARMS)
    assert len(EXECUTION_ARMS) + len(REFERENCE_ARMS) == 8
    assert roster['stage_b']['execution_tree_count'] == 1920
    assert not roster['stage_b']['cross_variant_warm_states_required_equal']
    assert roster['samples_per_acquired_row'] == 256
    assert roster['initial_shared_row_cap'] == 32 and roster['total_episode_row_cap'] == 128
    assert roster['online_per_decision_quota'] == '(128 - observed_rows) // remaining_horizon'
    assert [(example['case_name'], example['sample_seed'], len(example['query_names']))
            for example in roster['history_policy_examples']] == [
        ('v6_spawn_edge_rescue_2', 832101, 10), ('v6_crossing_rescue_pair_3', 832102, 1),
        ('v6_crossing_rescue_pair_2', 832102, 4)]
    assert roster['history_policy_examples'][2]['query_names'] == [
        'risk_1', 'goal_1_risk_1', 'probe_risk_0_5', 'probe_goal_2_risk_0_5']
    assert roster['legacy_v13_comparison']['stage_a_incremental_prefix_count'] == 96
    assert roster['legacy_v13_comparison']['stage_b_incremental_query_tree_count'] == 960
    assert not roster['v14_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v14(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v14(target)
