import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v18 import cases_v18
from acfqp.science.controlled_predictive_cohort_v20 import (
    CANDIDATE_METHODS, METHODS, ONLINE_METHODS, V18_ROSTER, V19_ROSTER,
    build_cohort_roster_v20, cases_v20, freeze_cohort_roster_v20,
)


def test_v20_preserves_all_cases_queries_stopping_and_ten_source_witnesses():
    """Detect outcome-selected cohorts or changed controls in an allocation comparison."""
    source = json.loads((DEFAULT_REPORTS_DIR / V18_ROSTER).read_text())
    witness_source = json.loads((DEFAULT_REPORTS_DIR / V19_ROSTER).read_text())
    roster = build_cohort_roster_v20()
    assert cases_v20() == cases_v18()
    for key in ('cases', 'sample_seeds', 'queries', 'initial_query_order', 'query_roles',
                'historical_exposure', 'mass_bound', 'row_stream', 'balanced_resampling_score'):
        assert roster[key] == source[key]
    assert roster['source_witnesses'] == witness_source['source_witnesses']
    assert roster['witness_comparison']['included_all']
    assert len(roster['source_witnesses']) == roster['witness_comparison']['included_count'] == 10
    assert sum(not row['divergences'] for row in roster['source_witnesses']) == 4
    assert roster['candidate_stopping'][CANDIDATE_METHODS[0]] == roster['candidate_stopping'][CANDIDATE_METHODS[1]] == source['candidate_stopping'][CANDIDATE_METHODS[0]]
    assert {k:v for k,v in roster['gap_score'].items() if k != 'recomputation'} == {
        k:v for k,v in source['gap_score'].items() if k != 'recomputation'}
    assert roster['legacy_v18_comparison']['trace_ignored_fields'] == []
    assert 'current_cached_comparison' not in roster and 'legacy_v17_comparison' not in roster
    assert all(row['method'] == 'online_variance_gap_stop' for row in roster['history_policy_examples'])


def test_v20_freezes_five_methods_and_two_paid_conversions(tmp_path):
    """Detect uncharged candidate setup or silently changed physical batch budgets."""
    roster = build_cohort_roster_v20()
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16,48,480)
    assert len(METHODS) == 5 and len(ONLINE_METHODS) == 3
    assert roster['history_evaluation']['execution_tree_count'] == 1440
    assert roster['initial_shared_batch_cap'] == 32
    assert roster['total_episode_batch_cap'] * roster['samples_per_batch'] == 32768
    conversion = roster['warm_preparation']['integer_count_conversions']
    assert conversion['physical_conversions_per_case_seed'] == 2
    for key, method in zip(('cached_gap', 'variance'), CANDIDATE_METHODS):
        assert conversion[key]['shared_by_methods'] == [method]
    assert roster['variance_allocation']['score'] == 'c**2 * s2 * (1/n - 1/(n+256))'
    assert 'Zero empirical variance' in roster['variance_allocation']['fallback']
    assert not roster['v20_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['source_fitting_enabled'] and roster['source_fees'] == 0
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed'] and not roster['u006_assurance_started']
    target = tmp_path/'roster.json'
    freeze_cohort_roster_v20(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):freeze_cohort_roster_v20(target)
