import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v19 import (
    METHODS, PHASES, V18_DIVERGENCES, V18_ROSTER,
    build_cohort_roster_v19, freeze_cohort_roster_v19,
)


def test_v19_preserves_ten_witnesses_and_selects_every_recorded_divergence():
    """Detect omitted or newly selected witnesses that would change this local diagnostic cohort."""
    source = json.loads((DEFAULT_REPORTS_DIR / V18_DIVERGENCES).read_text())
    previous = json.loads((DEFAULT_REPORTS_DIR / V18_ROSTER).read_text())
    roster = build_cohort_roster_v19()
    assert roster['source_witnesses'] == source['witnesses']
    assert (roster['source_witness_count'], roster['context_count'], roster['excluded_context_count']) == (10, 6, 4)
    assert roster['direction_counts'] == {'regression': 2, 'improvement': 4}
    indices = [row['source_witness_index'] for row in roster['contexts']]
    excluded = [row['source_witness_index'] for row in roster['excluded_contexts']]
    assert sorted(indices + excluded) == list(range(10))
    for row in roster['contexts']:
        witness = source['witnesses'][row['source_witness_index']]
        divergence = witness['divergences'][row['source_divergence_index']]
        assert row['divergence'] == divergence
        assert row['target_key'] == divergence['key'] == row['history'][-1]
        assert row['history_edges'] == divergence['history_edges']
        assert row['compared_actions'] == ['LEFT', 'RIGHT'] and row['target_key'][0] == 2
        assert row['query'] == previous['queries'][row['query_name']]
        assert row['direction'] == ('regression' if witness['cached_minus_base_value'] < 0 else 'improvement')
    assert all(not row['source_witness']['divergences'] and row['reason'] == 'NO_FIRST_ACTION_DIVERGENCE'
               for row in roster['excluded_contexts'])
    for key in ('queries', 'initial_query_order', 'query_roles', 'sample_seeds', 'historical_exposure'):
        assert roster[key] == previous[key]


def test_v19_freezes_twenty_four_snapshots_and_replay_only_budget(tmp_path):
    """Detect unpaid regeneration, extra suffix samples or a missing method/phase snapshot."""
    roster = build_cohort_roster_v19()
    assert roster['snapshot_count'] == 24
    assert {(row['context_index'], row['method'], row['phase']) for row in roster['snapshot_manifest']} == {
        (i, method, phase) for i in range(6) for method in METHODS for phase in PHASES}
    warm = roster['warm_replay']
    assert roster['selected_sample_seeds'] == [832101, 832102]
    assert warm['trajectory_count'] == 2 and warm['total_replayed_batches'] == 64
    assert warm['physical_regenerated_draws'] == 16384 and warm['new_independent_draws'] == 0
    assert roster['suffix_replay']['new_provider_calls'] == roster['suffix_replay']['new_physical_draws'] == 0
    assert not roster['snapshot_construction_or_local_truth_evaluated']
    assert roster['all_source_witnesses_retained'] and roster['source_fits'] == 0
    assert not roster['u006_assurance_started'] and not roster['original_deferred_24_case_cohort_loaded_or_executed']
    target = tmp_path / 'roster.json'
    freeze_cohort_roster_v19(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):
        freeze_cohort_roster_v19(target)
