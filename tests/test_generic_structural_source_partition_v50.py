import copy

from acfqp.generic_structural_source_partition_v50 import (
    partition_canonical_source_evidence_v50,
)


def _member(identity, state_colors, offset=0):
    layout = {
        "state_canonical_to_raw": [0, 1],
        "action_canonical_to_raw": [0],
        "schema_signature": "opaque-flat-v1",
        "state_structural_colors": state_colors,
        "action_structural_colors": [7],
    }
    action = {"action_key": 3 + offset, "anonymous_fields": [1]}
    row = {
        "occurrence": 0,
        "transition_index": 0,
        "pre_vector": [0, 4],
        "legal_action_keys_before": [3 + offset],
        "selected_action": action,
        "post_vector": [1, 4],
        "legal_action_keys_after": [3 + offset],
        "terminal_acceptance_after": None,
    }
    return {
        "member_id": identity,
        "source_evidence": {
            "layout": layout,
            "unknown_residual_target_columns": [1],
            "raw_transition_rows": [row],
        },
        "action_catalogue": [action],
    }


def test_v50_partitions_incompatible_sources_without_discarding_singletons():
    members = [
        _member("a" * 64, [1, 2]),
        _member("b" * 64, [1, 3]),
    ]
    result = partition_canonical_source_evidence_v50(members)
    assert result["structural_group_count"] == 2
    assert result["singleton_group_count"] == 2
    assert result["multi_member_group_count"] == 0
    assert result["every_source_member_retained_exactly_once"] is True
    assert all(
        row["source_evidence"]["singleton_source_retained_without_discard"]
        is True
        for row in result["structural_groups"]
    )
    assert result["family_or_named_coordinate_used_for_partition"] is False
    assert result["terminal_or_target_outcome_used_for_partition"] is False
    reversed_result = partition_canonical_source_evidence_v50(
        list(reversed(copy.deepcopy(members)))
    )
    assert reversed_result == result


def test_v50_pools_only_compatible_group_members():
    members = [
        _member("a" * 64, [1, 2], 0),
        _member("b" * 64, [1, 2], 1),
    ]
    result = partition_canonical_source_evidence_v50(members)
    assert result["structural_group_count"] == 1
    assert result["singleton_group_count"] == 0
    assert result["multi_member_group_count"] == 1
    group = result["structural_groups"][0]
    assert group["v48_cross_occurrence_pooling_applied"] is True
    assert group["source_evidence"]["source_member_count"] == 2
    assert group["source_evidence"]["all_members_retained_in_provenance"] is True
