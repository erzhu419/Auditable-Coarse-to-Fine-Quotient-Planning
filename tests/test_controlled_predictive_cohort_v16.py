import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v15 import cases_v15
from acfqp.science.controlled_predictive_cohort_v16 import (
    GAP_METHODS, METHODS, ONLINE_METHODS, V15_ROSTER,
    build_cohort_roster_v16, cases_v16, freeze_cohort_roster_v16,
)


def test_v16_preserves_exposed_inputs_stream_and_paid_budget():
    source = json.loads((DEFAULT_REPORTS_DIR / V15_ROSTER).read_text())
    roster = build_cohort_roster_v16()
    assert cases_v16() == cases_v15()
    for key in ('cases', 'sample_seeds', 'queries', 'initial_query_order', 'query_roles',
                'historical_exposure', 'scenarios', 'root_mass_groups', 'mass_bound', 'row_stream'):
        assert roster[key] == source[key]
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16, 48, 480)
    assert len(METHODS) == 6 and len(ONLINE_METHODS) == 4
    assert roster['history_evaluation']['execution_tree_count'] == 1920
    assert roster['initial_shared_batch_cap'] == 32
    assert roster['total_episode_batch_cap'] * roster['samples_per_batch'] == 32768
    assert roster['online_per_decision_quota'] == '(128 - spent_batches) // remaining_horizon'
    warm = roster['warm_preparation']
    assert warm['shared_by_methods'] == list(ONLINE_METHODS)
    conversion = warm['integer_count_conversions']
    assert conversion['balanced']['shared_by_methods'] == ['online_balanced_resampling']
    assert conversion['gap']['shared_by_methods'] == list(GAP_METHODS)
    assert conversion['physical_conversions_per_case_seed'] == 2
    assert roster['balanced_resampling_score'] == source['resampling_score']


def test_v16_local_gap_stop_and_unchanged_controls_are_frozen_exclusively(tmp_path):
    roster = build_cohort_roster_v16()
    gap = roster['gap_score']
    assert not gap['clipping'] and not gap['statistical_confidence_interval']
    assert 'Qminus >= challenger Qplus' in gap['separated']
    assert 'heuristic_action_separation' not in roster['candidate_stopping']['online_gap_continue']
    assert 'heuristic_action_separation' in roster['candidate_stopping']['online_gap_stop']
    assert roster['legacy_v14_comparison']['stage_a_mass_bound_warm_prefix_count'] == 48
    assert roster['legacy_v14_comparison']['online_mass_bound_query_tree_count'] == 480
    assert roster['legacy_v15_comparison']['query_tree_count'] == 480
    assert all(example['method'] == 'online_gap_stop' for example in roster['history_policy_examples'])
    assert not roster['v16_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['source_fitting_enabled'] and roster['source_fees'] == 0
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed']
    assert not roster['u006_assurance_started']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v16(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v16(target)
