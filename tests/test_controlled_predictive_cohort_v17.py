import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v16 import cases_v16
from acfqp.science.controlled_predictive_cohort_v17 import (
    GAP_METHODS, METHODS, ONLINE_METHODS, V16_ROSTER,
    build_cohort_roster_v17, cases_v17, freeze_cohort_roster_v17,
)


def test_v17_preserves_inputs_v16_stop_and_v15_balanced_allocation():
    """Detect input, gap threshold or acquisition changes that confound the stopping ablation."""
    source = json.loads((DEFAULT_REPORTS_DIR / V16_ROSTER).read_text())
    roster = build_cohort_roster_v17()
    assert cases_v17() == cases_v16()
    for key in ('cases', 'sample_seeds', 'queries', 'initial_query_order', 'query_roles',
                'historical_exposure', 'scenarios', 'root_mass_groups', 'mass_bound', 'row_stream',
                'gap_score', 'balanced_resampling_score'):
        assert roster[key] == source[key]
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16, 48, 480)
    assert len(METHODS) == 6 and len(ONLINE_METHODS) == 4
    assert roster['history_evaluation']['execution_tree_count'] == 1920
    assert roster['initial_shared_batch_cap'] == 32
    assert roster['total_episode_batch_cap'] * roster['samples_per_batch'] == 32768
    assert roster['online_per_decision_quota'] == '(128 - spent_batches) // remaining_horizon'
    for method in ('online_mass_bound', 'online_balanced_resampling'):
        assert roster['acquisition_methods'][method] == source['acquisition_methods'][method]
    assert 'heuristic_action_separation' not in roster['candidate_stopping'][GAP_METHODS[0]]
    assert 'heuristic_action_separation' in roster['candidate_stopping'][GAP_METHODS[1]]
    assert 'Fewest accumulated row batches' in roster['gap_allocation']['selection']
    assert roster['current_continue_comparison']['trace_ignored_fields'] == ['gap_assessments', 'decision_kind']


def test_v17_setup_attribution_and_retained_examples_freeze_exclusively(tmp_path):
    """Detect stale method attribution and overwritten frozen experimental evidence."""
    roster = build_cohort_roster_v17()
    warm = roster['warm_preparation']
    assert warm['shared_by_methods'] == list(ONLINE_METHODS)
    conversion = warm['integer_count_conversions']
    assert conversion['balanced']['shared_by_methods'] == ['online_balanced_resampling']
    assert conversion['gap']['shared_by_methods'] == list(GAP_METHODS)
    assert conversion['physical_conversions_per_case_seed'] == 2
    assert all(example['method'] == GAP_METHODS[1] for example in roster['history_policy_examples'])
    assert roster['legacy_v14_comparison']['stage_a_mass_bound_warm_prefix_count'] == 48
    assert roster['legacy_v15_comparison']['query_tree_count'] == roster['current_continue_comparison']['query_tree_count'] == 480
    assert not roster['v17_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['source_fitting_enabled'] and roster['source_fees'] == 0
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed']
    assert not roster['u006_assurance_started']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v17(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v17(target)
