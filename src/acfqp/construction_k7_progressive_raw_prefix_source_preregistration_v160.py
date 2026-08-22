"""Outcome-free preregistration of V160 raw-prefix source calibration."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v160 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("b7043f8",)
V157_POSITIVE_SEEDS = (1_047_811, 1_047_812, 1_047_813, 1_047_814)
V157_FALLBACK_SEEDS = (1_047_821, 1_047_822, 1_047_823, 1_047_824)
V159_MODULAR_SEEDS = (1_048_101, 1_048_102, 1_048_103, 1_048_104)
SOURCE_PREREGISTRATION_ID = "91622dda2410f0aa2b9444b0efbff4735486dab273b995a4171d2643d8210699"
EXPECTED_CANONICAL_BYTE_COUNT = 2_644
EXPECTED_CANONICAL_SHA256 = "b847f00774e21fc53c18bf5e67086f0280809fbfb506939d240aeb29581fd7ac"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v160.py",
        1_831,
        "0bf0952198d90f25de605d6c1b2be825277558d0061b3a9992aa9d9655a9ef6c",
    ),
    (
        "src/acfqp/progressive_raw_prefix_query_classifier_core_v160.py",
        10_700,
        "439552368965bd2e6b440e30e99e97dd07489c710b05b97399d56ded6faf5f57",
    ),
    (
        "src/acfqp/construction_k7_progressive_raw_prefix_classifier_receipt_v160.py",
        10_723,
        "46130f0d158db6d19663054ed38eef562aa500774300d316397605082808204f",
    ),
)


class ConstructionK7ProgressiveRawPrefixSourcePreregistrationV160Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProgressiveRawPrefixSourcePreregistrationV160Error(message)


def _document():
    source_facts = []
    for path, byte_count, digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / path).read_bytes()
        if len(raw) != byte_count or hashlib.sha256(raw).hexdigest() != digest:
            _fail("V160 source implementation changed before calibration")
        source_facts.append(
            {"relative_path": path, "byte_count": byte_count, "sha256": digest}
        )
    payload = {
        "schema": "acfqp.progressive_raw_prefix_source_preregistration.v160",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_implementation_source_facts": source_facts,
        "source_cohorts": [
            {
                "evidence": "FROZEN_V157_POSITIVE_QUERY_POLICY_OUTCOME",
                "seeds": list(V157_POSITIVE_SEEDS),
                "label": "RELATION_COVERAGE",
            },
            {
                "evidence": "FROZEN_V157_FALLBACK_QUERY_POLICY_OUTCOME",
                "seeds": list(V157_FALLBACK_SEEDS),
                "label": "PATH_FIRST_SAFE_FALLBACK",
            },
            {
                "evidence": "FROZEN_V159_MODULAR_RAW_FACTORIZATION_OUTCOME",
                "seeds": list(V159_MODULAR_SEEDS),
                "label": "PATH_FIRST_SAFE_FALLBACK",
            },
        ],
        "required_source_trace_count": 12,
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
            "all_source_identities_fixed_before_source_outcomes": True,
            "only_raw_state_action_successor_differences_feed_classifier": True,
            "no_named_initial_or_catalogue_support_primitive": True,
            "no_preregistered_literal_or_threshold_grid": True,
            "stable_prefix_horizon_must_be_derived": True,
            "full_initial_action_frontier_must_not_be_required": True,
            "offline_source_labels_counted_separately_from_target_labels": True,
            "fresh_v160_target_identities_not_yet_registered_or_observed": True,
        },
        "claim_boundary": {
            "source_outcomes_accessed": False,
            "fresh_v160_target_outcomes_accessed": False,
            "classifier_receipt_issued": False,
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
        "source_preregistration_id": domains.extension_content_id_v160(
            domains.CONSTRUCTION_K7_SOURCE_PREREGISTRATION_V160_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ProgressiveRawPrefixSourcePreregistrationV160:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_progressive_raw_prefix_source_preregistration_v160():
    document = _document()
    raw = canonical_json_bytes(document)
    if SOURCE_PREREGISTRATION_ID != "0" * 64 and not (
        document["source_preregistration_id"] == SOURCE_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V160 frozen source preregistration changed")
    return ProgressiveRawPrefixSourcePreregistrationV160(
        _ISSUER, raw, document["source_preregistration_id"]
    )


__all__ = (
    "SOURCE_PREREGISTRATION_ID",
    "freeze_progressive_raw_prefix_source_preregistration_v160",
)
