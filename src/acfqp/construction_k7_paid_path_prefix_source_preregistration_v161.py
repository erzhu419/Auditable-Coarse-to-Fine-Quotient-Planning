"""Outcome-free source preregistration for the V161 correction."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v161 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("2aef360",)
SOURCE_PREREGISTRATION_ID = "f3625303bb54a6354afc7bac8aaf36a87259501f8eb8fff3ecceb83ec72849c7"
EXPECTED_CANONICAL_BYTE_COUNT = 2_605
EXPECTED_CANONICAL_SHA256 = "726e8185481d2e9f85e29949acdb040063d7a57d7df2ab1a458be123ecec4f11"
V160_CLASSIFIER_RECEIPT_ID = "27b256a9a26ae86e49214932b77b2e507f34ff87bc3470ba42275330e48a9a12"
V160_FAILED_CAMPAIGN_ID = "38cbf013db9ceb15605807f5aa83564f7b89fc559d793dcfd7a049d7095771c6"
V160_FAILURE_SHA256 = "1d554b56462031920d3573ed1969997eedd8955426bfd024f8355bfab362d3ab"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v161.py",
        1_817,
        "fa80cd7e59a5ce1afb9afbe59fffb78d4af849218bdde6491cbea79f3c857b46",
    ),
    (
        "src/acfqp/paid_path_prefix_query_classifier_core_v161.py",
        2_698,
        "33c647f97d13ee5549af2e0c36719dd5150301e72557697516743cfeb3181f5f",
    ),
    (
        "src/acfqp/construction_k7_paid_path_prefix_classifier_receipt_v161.py",
        9_345,
        "309930d6e8c3e7ca7c9fe09f0255b45e76afe18df8276051bed15bca72430c83",
    ),
)


class ConstructionK7PaidPathPrefixSourcePreregistrationV161Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PaidPathPrefixSourcePreregistrationV161Error(message)


def _document():
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V161 source implementation changed before calibration")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    payload = {
        "schema": "acfqp.paid_path_prefix_source_preregistration.v161",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "source_v160_classifier_receipt_id": V160_CLASSIFIER_RECEIPT_ID,
        "failed_v160_campaign_id": V160_FAILED_CAMPAIGN_ID,
        "failed_v160_record_sha256": V160_FAILURE_SHA256,
        "required_source_trace_count": 12,
        "source_path_prefix_observation_cap": 8,
        "finite_generic_relation_meta_grammar": {
            "carrier": "ANONYMOUS_RAW_STATE_DELTA_INTEGER_VECTORS",
            "feature_vector_width": 10,
            "feature_relation_comparators": ["EQUAL", "NOT_EQUAL"],
            "feature_literal_comparators": ["EQUAL", "AT_LEAST"],
            "literal_values": "DERIVED_ONLY_FROM_REGISTERED_SOURCE_RAW_VECTORS",
            "stable_prefix_horizons": "DERIVED_FROM_REGISTERED_SOURCE_TRACE_LENGTHS",
            "aggregate": "COUNT_MATCHING_ROWS_GREATER_THAN_DERIVED_THRESHOLD",
            "exact_mdl_then_canonical_tie_break": True,
        },
        "registered_source_gate": {
            "v160_failed_identity_preserved_before_correction": True,
            "all_source_identities_fixed_before_v161_source_outcomes": True,
            "classifier_must_consume_only_the_exact_legacy_path_prefix": True,
            "safe_fallback_must_resume_the_same_generator_object": True,
            "no_sibling_probe_may_be_inserted_before_fallback": True,
            "stable_prefix_horizon_must_be_source_derived": True,
            "offline_source_labels_counted_separately_from_target_labels": True,
            "fresh_v161_target_identities_not_yet_registered_or_observed": True,
        },
        "claim_boundary": {
            "v161_source_outcomes_accessed": False,
            "fresh_v161_target_outcomes_accessed": False,
            "classifier_receipt_issued": False,
            "v160_failure_reclassified_as_success": False,
            "query_policy_is_model_planning_or_certificate_authority": False,
            "complete_world_model_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "source_preregistration_id": domains.extension_content_id_v161(
            domains.CONSTRUCTION_K7_SOURCE_PREREGISTRATION_V161_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PaidPathPrefixSourcePreregistrationV161:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_paid_path_prefix_source_preregistration_v161():
    document = _document()
    raw = canonical_json_bytes(document)
    if SOURCE_PREREGISTRATION_ID != "0" * 64 and not (
        document["source_preregistration_id"] == SOURCE_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V161 frozen source preregistration changed")
    return PaidPathPrefixSourcePreregistrationV161(
        _ISSUER, raw, document["source_preregistration_id"]
    )


__all__ = (
    "SOURCE_PREREGISTRATION_ID",
    "freeze_paid_path_prefix_source_preregistration_v161",
)
