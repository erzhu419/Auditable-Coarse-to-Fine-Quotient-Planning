from acfqp.paid_prefix_profitability_identifiability_core_v165 import (
    build_paid_prefix_profitability_identifiability_audit_v165,
    invariant_paid_prefix_profitability_signature_v165,
)


def _acquisition(*, field, coordinate, offset):
    return {
        "classifier_decision_trace": [
            {
                "prefix_observation_count": 1,
                "anonymous_raw_delta_feature_rows": [
                    [1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
                    [1, 0, 1, 1, 1, 1, 0, 1, 1, 1],
                ],
            }
        ],
        "classifier_decision": "RELATION_COVERAGE",
        "query_policy_decision": "RELATION_COVERAGE",
        "paid_prefix_relation_candidates": [
            {
                "action_field": field,
                "state_delta_coordinate": coordinate,
                "relation_rows": [
                    {"action_field_value": offset + 11, "state_delta": 1},
                    {"action_field_value": offset + 19, "state_delta": 2},
                ],
                "paid_path_prefix_exhausted_anonymous_relation_support": True,
                "injective_positive_delta_relation": True,
            }
        ],
    }


def _occurrence(identity, reduction, *, field, coordinate, offset):
    return {
        "occurrence_id": identity * 64,
        "target_family": "SYNTHETIC",
        "seed": offset,
        "progressive_prior_acquisition": _acquisition(
            field=field, coordinate=coordinate, offset=offset
        ),
        "query_policy_sample_reduction_vs_legacy_path_first": reduction,
        "certified_positive_switch": True,
        "registered_gate": {"passed": True},
    }


def test_v165_signature_removes_cross_namespace_identity_and_opaque_values():
    left = invariant_paid_prefix_profitability_signature_v165(
        _acquisition(field=1, coordinate=7, offset=100)
    )
    right = invariant_paid_prefix_profitability_signature_v165(
        _acquisition(field=5, coordinate=2, offset=900)
    )
    assert left == right


def test_v165_detects_mixed_profitability_inside_one_invariant_class():
    campaign = {
        "campaign_id": "c" * 64,
        "target_occurrences": [
            _occurrence("a", 0, field=1, coordinate=7, offset=100),
            _occurrence("b", 9, field=5, coordinate=2, offset=900),
        ],
    }
    audit = build_paid_prefix_profitability_identifiability_audit_v165(
        [campaign],
        source_campaign_ids=["c" * 64],
        source_verification_ids=["d" * 64],
    )
    assert audit["mixed_profitability_signature_count"] == 1
    assert audit[
        "perfect_deterministic_classifier_exists_in_registered_signature_space"
    ] is False
    assert audit["profitability_classifier_issued"] is False
    assert audit["new_target_observation_labels"] == 0
