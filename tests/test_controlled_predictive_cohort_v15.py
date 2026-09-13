import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v14 import cases_v14
from acfqp.science.controlled_predictive_cohort_v15 import (
    CANDIDATE_METHODS, METHODS, ONLINE_METHODS, V14_ROSTER,
    build_cohort_roster_v15, cases_v15, freeze_cohort_roster_v15,
)


def test_v15_preserves_inputs_and_charges_shared_prefix_and_every_repeat_batch():
    source = json.loads((DEFAULT_REPORTS_DIR / V14_ROSTER).read_text())
    roster = build_cohort_roster_v15()
    assert cases_v15() == cases_v14()
    for key in ('cases', 'sample_seeds', 'queries', 'initial_query_order', 'query_roles',
                'historical_exposure', 'scenarios', 'historical_primary_case_splits', 'root_mass_groups', 'mass_bound'):
        assert roster[key] == source[key]
    assert (roster['case_count'], roster['case_seed_count'], roster['query_execution_context_count']) == (16, 48, 480)
    assert roster['sample_seeds'] == [832101, 832102, 832103]
    assert all(record['case']['horizon'] <= 3 for record in roster['cases'])
    assert roster['methods'] == list(METHODS) and len(METHODS) == 5
    assert roster['online_methods'] == list(ONLINE_METHODS)
    assert roster['candidate_methods'] == list(CANDIDATE_METHODS)
    assert roster['history_evaluation']['execution_tree_count'] == 1440
    assert roster['initial_shared_batch_cap'] == roster['initial_shared_row_cap'] == 32
    assert roster['total_episode_batch_cap'] * roster['samples_per_batch'] == roster['maximum_episode_physical_draws'] == 32768
    assert roster['online_per_decision_quota'] == '(128 - spent_batches) // remaining_horizon'
    warm = roster['warm_preparation']
    assert warm['physical_trajectory_count'] == 48 and warm['only_batch_zero']
    assert warm['shared_by_methods'] == list(ONLINE_METHODS)
    assert warm['integer_count_conversion']['performed_once_per_warm_prefix']
    assert warm['integer_count_conversion']['shared_by_methods'] == list(CANDIDATE_METHODS)
    assert not roster['source_fitting_enabled'] and roster['source_fees'] == 0
    assert not roster['lofo_scenarios_reexecuted']


def test_v15_freezes_proxy_and_indexed_stream_and_directed_examples_before_outcomes(tmp_path):
    roster = build_cohort_roster_v15()
    stream = roster['row_stream']
    assert stream['batch_zero_version'] == 'V12_V14_UNCHANGED'
    assert stream['batch_index_range'] == [0, 127] and stream['batch_seed_stride'] == 1000000
    assert not stream['mutable_random_cursor'] and not stream['discard_old_prefix_to_position_stream']
    assert not stream['complete_support_returned_to_planner']
    score = roster['resampling_score']
    assert not score['clipping'] and not score['statistical_confidence_interval']
    assert 'sqrt(256 * row_batch_count)' in score['radius']
    assert not roster['candidate_empirical_closure_stops_all_acquisition']
    assert roster['candidate_stopping'] == ['total_batch_cap', 'current_decision_quota', 'terminal_state', 'no_eligible_row']
    examples = roster['history_policy_examples']
    assert all(example['method'] == 'online_directed_resampling' for example in examples)
    assert [(e['case_name'], e['sample_seed'], len(e['query_names'])) for e in examples] == [
        ('v6_spawn_edge_rescue_2', 832101, 10), ('v6_crossing_rescue_pair_3', 832102, 1),
        ('v6_crossing_rescue_pair_2', 832102, 4)]
    assert roster['legacy_v14_comparison']['stage_a_mass_bound_warm_prefix_count'] == 48
    assert roster['legacy_v14_comparison']['online_mass_bound_query_tree_count'] == 480
    assert not roster['v15_target_acquisition_execution_or_outcomes_evaluated']
    assert not roster['original_deferred_24_case_cohort_loaded_or_executed']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v15(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v15(target)
