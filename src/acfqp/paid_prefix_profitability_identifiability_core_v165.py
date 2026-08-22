"""Audit whether the registered anonymous paid prefix identifies switch benefit."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Mapping

from acfqp import construction_k7_domain_registry_extension_v165 as domains
from acfqp.phase3e_ids import canonical_json_bytes


def _normalized_relation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    rows = tuple(candidate["relation_rows"])
    ordered = tuple(sorted(rows, key=lambda row: row["action_field_value"]))
    deltas = tuple(row["state_delta"] for row in ordered)
    if not (
        candidate["injective_positive_delta_relation"] is True
        and candidate["paid_path_prefix_exhausted_anonymous_relation_support"]
        is True
        and deltas
        and min(deltas) > 0
        and len(set(deltas)) == len(deltas)
    ):
        raise ValueError("V165 paid-prefix relation evidence changed")
    return {
        "relation_support_cardinality": len(deltas),
        "ordered_state_delta_values": list(deltas),
        "state_delta_span": max(deltas) - min(deltas),
        "action_field_identity_retained": False,
        "state_coordinate_identity_retained": False,
        "opaque_action_values_retained": False,
    }


def invariant_paid_prefix_profitability_signature_v165(
    acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    """Remove descriptor/coordinate identities from the already-paid evidence."""

    trace = acquisition["classifier_decision_trace"]
    if not trace:
        raise ValueError("V165 paid-prefix decision trace is empty")
    prefixes = []
    for expected_index, update in enumerate(trace, start=1):
        rows = tuple(tuple(row) for row in update["anonymous_raw_delta_feature_rows"])
        if not (
            update["prefix_observation_count"] == expected_index
            and rows
            and all(len(row) == 10 and all(type(value) is int for value in row) for row in rows)
        ):
            raise ValueError("V165 anonymous paid-prefix feature trace changed")
        prefixes.append(
            {
                "prefix_observation_count": expected_index,
                "anonymous_feature_row_multiset": [list(row) for row in sorted(rows)],
            }
        )
    relations = sorted(
        (
            _normalized_relation(candidate)
            for candidate in acquisition["paid_prefix_relation_candidates"]
        ),
        key=canonical_json_bytes,
    )
    payload = {
        "schema": "acfqp.paid_prefix_profitability_signature.v165",
        "prefixes": prefixes,
        "classifier_decision": acquisition["classifier_decision"],
        "query_policy_decision": acquisition["query_policy_decision"],
        "normalized_relation_candidates": relations,
        "descriptor_field_permutation_invariant": True,
        "state_coordinate_permutation_invariant": True,
        "opaque_descriptor_value_renaming_invariant": True,
        "absolute_seed_family_and_occurrence_identity_retained": False,
        "ground_outcome_beyond_paid_prefix_accessed": False,
    }
    return {
        **payload,
        "signature_id": domains.extension_content_id_v165(
            domains.CONSTRUCTION_K7_PROFITABILITY_SIGNATURE_V165_DOMAIN, payload
        ),
    }


def build_paid_prefix_profitability_identifiability_audit_v165(
    source_campaigns: Iterable[Mapping[str, Any]],
    *,
    source_campaign_ids: Iterable[str],
    source_verification_ids: Iterable[str],
    frozen_implementation_source_facts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    campaigns = tuple(source_campaigns)
    campaign_ids = tuple(source_campaign_ids)
    verification_ids = tuple(source_verification_ids)
    if not (
        len(campaigns) == len(campaign_ids) == len(verification_ids)
        and campaigns
    ):
        raise ValueError("V165 source campaign inventory changed")
    rows = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for campaign, campaign_id in zip(campaigns, campaign_ids):
        if campaign.get("campaign_id") != campaign_id:
            raise ValueError("V165 source campaign identity changed")
        for occurrence in campaign["target_occurrences"]:
            reduction = occurrence[
                "query_policy_sample_reduction_vs_legacy_path_first"
            ]
            if type(reduction) is not int or reduction < 0:
                raise ValueError("V165 historical noninferiority evidence changed")
            acquisition = occurrence["progressive_prior_acquisition"]
            signature = invariant_paid_prefix_profitability_signature_v165(acquisition)
            row = {
                "source_campaign_id": campaign_id,
                "source_occurrence_id": occurrence["occurrence_id"],
                "family": occurrence["target_family"],
                "seed": occurrence["seed"],
                "signature_id": signature["signature_id"],
                "signature": signature,
                "query_policy_labels_avoided": reduction,
                "strict_profitability_label": reduction > 0,
                "certified_positive_switch": occurrence["certified_positive_switch"],
                "registered_occurrence_gate_passed": occurrence["registered_gate"][
                    "passed"
                ],
            }
            rows.append(row)
            groups[signature["signature_id"]].append(row)
    classes = []
    for signature_id in sorted(groups):
        members = groups[signature_id]
        labels = {member["strict_profitability_label"] for member in members}
        classes.append(
            {
                "signature_id": signature_id,
                "signature": members[0]["signature"],
                "source_occurrence_ids": [
                    member["source_occurrence_id"] for member in members
                ],
                "member_count": len(members),
                "strictly_profitable_member_count": sum(
                    member["strict_profitability_label"] for member in members
                ),
                "zero_reduction_member_count": sum(
                    member["query_policy_labels_avoided"] == 0 for member in members
                ),
                "label_set": sorted(labels),
                "profitability_label_is_identifiable": len(labels) == 1,
            }
        )
    conflicts = [row for row in classes if not row["profitability_label_is_identifiable"]]
    payload = {
        "schema": "acfqp.paid_prefix_profitability_identifiability_audit.v165",
        "source_campaign_ids": list(campaign_ids),
        "source_verification_ids": list(verification_ids),
        "frozen_implementation_source_facts": [
            dict(row) for row in frozen_implementation_source_facts
        ],
        "source_occurrences": rows,
        "equivalence_classes": classes,
        "source_occurrence_count": len(rows),
        "strictly_profitable_occurrence_count": sum(
            row["strict_profitability_label"] for row in rows
        ),
        "zero_reduction_occurrence_count": sum(
            row["query_policy_labels_avoided"] == 0 for row in rows
        ),
        "invariant_signature_count": len(classes),
        "mixed_profitability_signature_count": len(conflicts),
        "mixed_profitability_signature_ids": [
            row["signature_id"] for row in conflicts
        ],
        "perfect_deterministic_classifier_exists_in_registered_signature_space": not conflicts,
        "registered_paid_prefix_profitability_is_identifiable": not conflicts,
        "zero_reduction_safe_switches_are_sample_label_regressions": False,
        "new_target_outcomes_accessed": False,
        "new_target_observation_labels": 0,
        "historical_outcome_annotations_consumed": len(rows),
        "audit_claim_scope": "ONLY_V163_AND_V164_FROZEN_OCCURRENCES_AND_REGISTERED_INVARIANT_SIGNATURE",
        "profitability_classifier_issued": False,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "audit_id": domains.extension_content_id_v165(
            domains.CONSTRUCTION_K7_IDENTIFIABILITY_AUDIT_V165_DOMAIN, payload
        ),
    }


__all__ = (
    "build_paid_prefix_profitability_identifiability_audit_v165",
    "invariant_paid_prefix_profitability_signature_v165",
)
