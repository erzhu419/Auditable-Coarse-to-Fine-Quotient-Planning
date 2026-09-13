import json

import pytest

from acfqp.science.controlled_predictive_cohort_v7 import DEFAULT_REPORTS_DIR
from acfqp.science.controlled_predictive_cohort_v21 import (
    METHODS, V20_ANALYSIS, V20_ROSTER, build_cohort_roster_v21, freeze_cohort_roster_v21,
)


def test_v21_preserves_union_groups_and_original_order():
    """Detect removal of unchanged old witnesses or relabeling from local outcomes."""
    source = json.loads((DEFAULT_REPORTS_DIR/V20_ROSTER).read_text())
    analysis = json.loads((DEFAULT_REPORTS_DIR/V20_ANALYSIS).read_text())
    roster = build_cohort_roster_v21()
    changed = analysis['pairs']['VARIANCE_versus_CACHED']['nonzero_component_contexts']
    assert roster['source_v20_changed_contexts'] == changed
    assert roster['source_witnesses'] == source['source_witnesses']
    expected = {(r['case'],r['seed'],r['query']) for r in changed+source['source_witnesses']}
    identities = [(r['case_name'],r['sample_seed'],r['query_name']) for r in roster['contexts']]
    assert set(identities) == expected and len(identities) == roster['context_count'] == 22
    assert roster['group_counts'] == {'improvement':7,'regression':13,'old_witness_only':2}
    assert sum(row['source_v20_changed'] for row in roster['contexts']) == 20
    assert sum(row['source_old_witness'] for row in roster['contexts']) == 10
    assert identities == sorted(identities, key=lambda key:(key[0],key[1],source['initial_query_order'].index(key[2])))
    for key in ('sample_seeds','queries','initial_query_order','query_roles','historical_exposure'):
        assert roster[key] == source[key]


def test_v21_fixed_remaining_quota_panel_and_physical_replay_freeze(tmp_path):
    """Detect the superseded eight-batch cap, endpoint-expanded panels or free replay sampling."""
    roster = build_cohort_roster_v21()
    assert roster['methods'] == list(METHODS) and roster['declared_local_arm_count'] == 44
    local = roster['local_intervention']
    assert local['fixed_batches_per_arm'] == 'K = node.quota - j'
    assert local['snapshot_spent_batches'] == 'node.batches_before + j'
    assert local['quota'] == '(128 - node.batches_before) // target_horizon'
    assert local['total_path_batch_cap'] * local['samples_per_batch'] == 32768
    assert not roster['fixed_state_panel']['endpoint_new_states_expand_panel']
    assert roster['target_evaluation']['horizons'] == [1,2,3]
    assert roster['warm_replay']['physical_replayed_batches'] == 96
    assert roster['warm_replay']['physical_replayed_draws'] == 24576
    assert not roster['common_snapshot_extraction_or_local_acquisition_evaluated']
    assert roster['source_fits'] == 0 and not roster['u006_assurance_started']
    target=tmp_path/'roster.json';freeze_cohort_roster_v21(target)
    assert json.loads(target.read_text()) == roster
    with pytest.raises(FileExistsError):freeze_cohort_roster_v21(target)
