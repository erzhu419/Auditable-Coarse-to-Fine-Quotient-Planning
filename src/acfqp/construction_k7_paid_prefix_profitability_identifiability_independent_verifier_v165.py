"""Producer-free reconstruction of the frozen V165 identifiability audit."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v165 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


AUDIT_ID = "8de483f4f827caddf96dd367b470aba6b8fef409f3cc060c4f3308fd592cbdeb"
AUDIT_BYTE_COUNT = 126_086
AUDIT_SHA256 = "ebc57797a7b516d10d8a7a2d641b84a6d17621d47554c958235a1ec5981b8200"
V163_CAMPAIGN_ID = "193323db43d5524e5bebe3a1713e946ab7dbb77cf79307c957a13cded0d9c219"
V163_CAMPAIGN_BYTE_COUNT = 31_528_790
V163_CAMPAIGN_SHA256 = "9dab876ef04bd5b48698fdb9295aaf6efe1f6e3a51bd945fe84e449367aaa433"
V163_VERIFICATION_ID = (
    "5e856f8cab34726906f3e93924ea099d2027ee39aca0708efc5ebabec437975b"
)
V163_VERIFICATION_BYTE_COUNT = 28_544
V163_VERIFICATION_SHA256 = (
    "bd98840ef1a21d3897195e86093b0ed727acbb606dc544cd10df343d7dda002f"
)
V164_CAMPAIGN_ID = "108bc4cf4f61123c6da7812ae76a48c21027a3b5e32e80005952a93b2ab8da1c"
V164_CAMPAIGN_BYTE_COUNT = 33_323_896
V164_CAMPAIGN_SHA256 = "d964f250d8d6e0587cb80a1df50515ae9b74c319b0a4f5f24aee3cae262aa9f5"
V164_VERIFICATION_ID = (
    "1095eec978a045ac3fec2ef0848927ecf7ce3d290d68415656b28fe34b3f298f"
)
V164_VERIFICATION_BYTE_COUNT = 41_990
V164_VERIFICATION_SHA256 = (
    "91c6939851c37de8094be13bf113a17aef51abfc8379853af1f509559ea03be8"
)
VERIFICATION_ID = (
    "d9aab6590d650f534edf19b7f87fd51045cd0d07cdf9d528f9873de3421e6390"
)
EXPECTED_CANONICAL_BYTE_COUNT = 1_204
EXPECTED_CANONICAL_SHA256 = (
    "f1c2a75cd081550b9751b4d30e9b78eb07938741f69fd48df06f8a30268fffcd"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]


class ConstructionK7PaidPrefixProfitabilityIdentifiabilityIndependentVerifierV165Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPrefixProfitabilityIdentifiabilityIndependentVerifierV165Error(
        message
    )


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _frozen(raw, *, count, digest, key, identity, label):
    document = loads_canonical_json(raw)
    _require(
        canonical_json_bytes(document) == raw
        and len(raw) == count
        and hashlib.sha256(raw).hexdigest() == digest
        and document.get(key) == identity,
        f"V165 frozen {label} changed",
    )
    return document


def _normalized_relation(candidate):
    ordered = tuple(
        sorted(candidate["relation_rows"], key=lambda row: row["action_field_value"])
    )
    deltas = tuple(row["state_delta"] for row in ordered)
    _require(
        candidate["injective_positive_delta_relation"] is True
        and candidate["paid_path_prefix_exhausted_anonymous_relation_support"]
        is True
        and bool(deltas)
        and min(deltas) > 0
        and len(set(deltas)) == len(deltas),
        "V165 paid-prefix relation evidence changed",
    )
    return {
        "relation_support_cardinality": len(deltas),
        "ordered_state_delta_values": list(deltas),
        "state_delta_span": max(deltas) - min(deltas),
        "action_field_identity_retained": False,
        "state_coordinate_identity_retained": False,
        "opaque_action_values_retained": False,
    }


def _signature(acquisition):
    prefixes = []
    trace = acquisition["classifier_decision_trace"]
    _require(bool(trace), "V165 paid-prefix trace is empty")
    for expected_index, update in enumerate(trace, start=1):
        rows = tuple(tuple(row) for row in update["anonymous_raw_delta_feature_rows"])
        _require(
            update["prefix_observation_count"] == expected_index
            and bool(rows)
            and all(
                len(row) == 10 and all(type(value) is int for value in row)
                for row in rows
            ),
            "V165 paid-prefix feature trace changed",
        )
        prefixes.append(
            {
                "prefix_observation_count": expected_index,
                "anonymous_feature_row_multiset": [list(row) for row in sorted(rows)],
            }
        )
    relations = sorted(
        (_normalized_relation(row) for row in acquisition["paid_prefix_relation_candidates"]),
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
        "signature_id": _content_id(
            domains.CONSTRUCTION_K7_PROFITABILITY_SIGNATURE_V165_DOMAIN, payload
        ),
    }


def _expected_audit(campaigns, source_facts):
    campaign_ids = (V163_CAMPAIGN_ID, V164_CAMPAIGN_ID)
    verification_ids = (V163_VERIFICATION_ID, V164_VERIFICATION_ID)
    rows = []
    groups = defaultdict(list)
    for campaign, campaign_id in zip(campaigns, campaign_ids):
        for occurrence in campaign["target_occurrences"]:
            reduction = occurrence[
                "query_policy_sample_reduction_vs_legacy_path_first"
            ]
            _require(
                type(reduction) is int and reduction >= 0,
                "V165 historical noninferiority evidence changed",
            )
            signature = _signature(occurrence["progressive_prior_acquisition"])
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
        "frozen_implementation_source_facts": source_facts,
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
        "mixed_profitability_signature_ids": [row["signature_id"] for row in conflicts],
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
        "audit_id": _content_id(
            domains.CONSTRUCTION_K7_IDENTIFIABILITY_AUDIT_V165_DOMAIN, payload
        ),
    }


def freeze_paid_prefix_profitability_identifiability_verification_v165(
    audit_raw: bytes,
    v163_campaign_raw: bytes,
    v163_verification_raw: bytes,
    v164_campaign_raw: bytes,
    v164_verification_raw: bytes,
) -> bytes:
    audit = _frozen(
        audit_raw,
        count=AUDIT_BYTE_COUNT,
        digest=AUDIT_SHA256,
        key="audit_id",
        identity=AUDIT_ID,
        label="audit",
    )
    v163_campaign = _frozen(
        v163_campaign_raw,
        count=V163_CAMPAIGN_BYTE_COUNT,
        digest=V163_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V163_CAMPAIGN_ID,
        label="V163 campaign",
    )
    v163_verification = _frozen(
        v163_verification_raw,
        count=V163_VERIFICATION_BYTE_COUNT,
        digest=V163_VERIFICATION_SHA256,
        key="verification_id",
        identity=V163_VERIFICATION_ID,
        label="V163 verification",
    )
    v164_campaign = _frozen(
        v164_campaign_raw,
        count=V164_CAMPAIGN_BYTE_COUNT,
        digest=V164_CAMPAIGN_SHA256,
        key="campaign_id",
        identity=V164_CAMPAIGN_ID,
        label="V164 campaign",
    )
    v164_verification = _frozen(
        v164_verification_raw,
        count=V164_VERIFICATION_BYTE_COUNT,
        digest=V164_VERIFICATION_SHA256,
        key="verification_id",
        identity=V164_VERIFICATION_ID,
        label="V164 verification",
    )
    _require(
        v163_campaign["registered_gate"]["passed"] is True
        and v164_campaign["registered_gate"]["passed"] is True
        and v163_verification[
            "safe_query_and_factor_prior_sample_tax_evidence_independently_verified"
        ]
        is True
        and v164_verification[
            "query_and_factor_prior_sample_tax_replication_independently_verified"
        ]
        is True,
        "V165 predecessor semantics changed",
    )
    source_facts = audit["frozen_implementation_source_facts"]
    for fact in source_facts:
        raw = (SOURCE_ROOT / fact["relative_path"]).read_bytes()
        _require(
            set(fact) == {"relative_path", "byte_count", "sha256"}
            and len(raw) == fact["byte_count"]
            and hashlib.sha256(raw).hexdigest() == fact["sha256"],
            "V165 implementation source closure changed",
        )
    expected = _expected_audit((v163_campaign, v164_campaign), source_facts)
    _require(audit == expected, "V165 producer-free audit reconstruction changed")
    payload = {
        "schema": "acfqp.paid_prefix_profitability_identifiability_verification.v165",
        "audit_id": AUDIT_ID,
        "source_campaign_ids": [V163_CAMPAIGN_ID, V164_CAMPAIGN_ID],
        "source_verification_ids": [V163_VERIFICATION_ID, V164_VERIFICATION_ID],
        "source_occurrence_count": audit["source_occurrence_count"],
        "invariant_signature_count": audit["invariant_signature_count"],
        "mixed_profitability_signature_count": audit[
            "mixed_profitability_signature_count"
        ],
        "registered_paid_prefix_nonidentifiability_independently_verified": True,
        "producer_module_imported": False,
        "profitability_classifier_issued": False,
        "new_target_outcomes_accessed": False,
        "new_target_observation_labels": 0,
        "query_policy_classifier_is_model_planning_or_certificate_authority": False,
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": _content_id(
            domains.CONSTRUCTION_K7_VERIFICATION_V165_DOMAIN, payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V165 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_paid_prefix_profitability_identifiability_verification_v165",
)
