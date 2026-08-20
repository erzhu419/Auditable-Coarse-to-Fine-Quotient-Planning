import copy

import pytest

from acfqp.generic_canonical_source_pool_v48 import (
    GenericCanonicalSourcePoolV48Error,
    pool_canonical_source_evidence_v48,
)


def _member(name, state_order, action_order, offset):
    def raw(canonical, order):
        result = [0] * len(order)
        for canonical_index, raw_index in enumerate(order):
            result[raw_index] = canonical[canonical_index]
        return result

    actions = [(10 + offset, (0, 1)), (20 + offset, (1, -1))]
    catalogue = [
        {
            "action_key": key,
            "anonymous_fields": raw(fields, action_order),
        }
        for key, fields in actions
    ]
    rows = []
    for index, (key, fields) in enumerate(actions):
        rows.append(
            {
                "occurrence": 0,
                "transition_index": index,
                "pre_vector": raw((index, 3, 9), state_order),
                "legal_action_keys_before": sorted(key for key, _ in actions),
                "selected_action": {
                    "action_key": key,
                    "anonymous_fields": raw(fields, action_order),
                },
                "post_vector": raw((index + fields[0], 3, 9), state_order),
                "legal_action_keys_after": sorted(key for key, _ in actions),
                "terminal_acceptance_after": None,
                "outcome_tape_sha256": None,
            }
        )
    evidence = {
        "schema": "test.source",
        "source_evidence_id": "e" * 64 if name == "A" else "f" * 64,
        "layout": {
            "state_canonical_to_raw": list(state_order),
            "action_canonical_to_raw": list(action_order),
            "state_structural_colors": ["S0", "S1", "S2"],
            "action_structural_colors": ["A0", "A1"],
            "schema_signature": "same",
        },
        "unknown_residual_target_columns": [0, 2],
        "raw_transition_rows": rows,
    }
    return {
        "member_id": name,
        "source_evidence": evidence,
        "action_catalogue": catalogue,
    }


def test_v48_pools_permuted_members_without_semantic_names_or_target_outcomes():
    members = (
        _member("A", (2, 0, 1), (1, 0), 0),
        _member("B", (1, 2, 0), (0, 1), 100),
    )
    result = pool_canonical_source_evidence_v48(members)
    assert result["source_member_count"] == 2
    assert result["pooled_raw_transition_row_count"] == 4
    assert result["canonical_action_signature_count"] == 2
    assert result["family_or_named_coordinate_input_present"] is False
    assert result["target_outcome_input_present"] is False
    rows = result["raw_transition_rows"]
    order = result["layout"]["state_canonical_to_raw"]
    canonical = [tuple(row["pre_vector"][index] for index in order) for row in rows]
    assert canonical == [(0, 3, 9), (1, 3, 9), (0, 3, 9), (1, 3, 9)]
    assert rows[0]["selected_action"] == rows[2]["selected_action"]
    assert rows[1]["selected_action"] == rows[3]["selected_action"]


def test_v48_is_deterministic_and_rejects_incompatible_schema():
    members = [
        _member("A", (2, 0, 1), (1, 0), 0),
        _member("B", (1, 2, 0), (0, 1), 100),
    ]
    assert pool_canonical_source_evidence_v48(members) == (
        pool_canonical_source_evidence_v48(copy.deepcopy(members))
    )
    members[1]["source_evidence"]["layout"]["schema_signature"] = "foreign"
    with pytest.raises(GenericCanonicalSourcePoolV48Error):
        pool_canonical_source_evidence_v48(members)
