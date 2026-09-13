import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v17 import cases_v17
from acfqp.science.controlled_predictive_cohort_v18 import (
    GAP_METHODS, METHODS, ONLINE_METHODS, V17_ROSTER,
    build_cohort_roster_v18, cases_v18, freeze_cohort_roster_v18,
)


def test_v18_preserves_inputs_and_full_stop_semantics():
    """Detect changed mathematical rules or validation exclusions in a computation-only comparison."""
    source = json.loads((DEFAULT_REPORTS_DIR / V17_ROSTER).read_text())
    roster = build_cohort_roster_v18()
    assert cases_v18() == cases_v17()
    for key in ('cases', 'sample_seeds', 'queries', 'initial_query_order', 'query_roles',
                'historical_exposure', 'scenarios', 'root_mass_groups', 'mass_bound', 'row_stream',
                'balanced_resampling_score'):
        assert roster[key] == source[key]
    for key in ('gap_score', 'gap_allocation'):
        assert {k: v for k, v in roster[key].items() if k != 'recomputation'} == {
            k: v for k, v in source[key].items() if k != 'recomputation'}
    for method in METHODS[2:5]:
        assert roster['acquisition_methods'][method] == source['acquisition_methods'][method]
    assert roster['candidate_stopping'][GAP_METHODS[1]] == roster['candidate_stopping'][GAP_METHODS[0]]
    assert roster['current_cached_comparison']['compared_fields'] == ['trace', 'root_metrics']
    assert roster['current_cached_comparison']['trace_ignored_fields'] == []
    assert 'online_balanced_gap_continue' not in roster['candidate_stopping']
    assert roster['initial_shared_batch_cap'] == 32
    assert roster['total_episode_batch_cap'] * roster['samples_per_batch'] == 32768
    assert roster['online_per_decision_quota'] == '(128 - spent_batches) // remaining_horizon'


def test_v18_three_paid_conversions_and_fixed_roster_are_exclusive(tmp_path):
    """Detect uncharged cache setup or stale method roles before any target acquisition."""
    roster = build_cohort_roster_v18()
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16, 48, 480)
    assert len(METHODS) == 6 and len(ONLINE_METHODS) == 4
    assert roster['history_evaluation']['execution_tree_count'] == 1920
    warm = roster['warm_preparation']
    assert warm['shared_by_methods'] == list(ONLINE_METHODS)
    conversions = warm['integer_count_conversions']
    assert conversions['physical_conversions_per_case_seed'] == 3
    for key, method in zip(('balanced', 'gap', 'cached_gap'), METHODS[3:]):
        assert conversions[key]['shared_by_methods'] == [method]
    assert all(example['method'] == GAP_METHODS[1] for example in roster['history_policy_examples'])
    assert roster['legacy_v14_comparison']['stage_a_mass_bound_warm_prefix_count'] == 48
    assert roster['legacy_v15_comparison']['query_tree_count'] == roster['legacy_v17_comparison']['query_tree_count'] == roster['current_cached_comparison']['query_tree_count'] == 480
    assert not roster['v18_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['source_fitting_enabled'] and roster['source_fees'] == 0
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed']
    assert not roster['u006_assurance_started']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v18(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v18(target)
