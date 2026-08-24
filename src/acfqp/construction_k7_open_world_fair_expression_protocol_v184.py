"""Outcome-free protocol for the fresh V184 multi-distribution campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v184 as domains
from acfqp import construction_k7_open_world_ranked_machine_campaign_freeze_v183 as predecessor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = "849c28f54a36df1b3fd8077f3bae8eeb152a5200a474e72f3c313acb4f2d098a"
EXPECTED_CANONICAL_BYTE_COUNT = 4_225
EXPECTED_CANONICAL_SHA256 = "0f33f28a317e6596564d4655c41c04560969b0b2dd9c934238cac0b626043682"

MANIFEST_COMMITMENTS_V184 = (
    "1b5a64a49bdaf2225cc3a31ed7b6eba19d1953e78095b1c6202fa8c705b479df",
    "fbd4fb80d143aa84d7e72725dd3ad420476d91194769831b898e9ac82620853a",
    "e813ddc2906a2db5dc2bfb78b4bd5f2851eec2ea1b4015b1439257d076a80a43",
    "25556f2f65173a69a0a97f775795f5ea4bb29fb7095bd6e0919ac287b37312f5",
    "a8e1f3abac73f914cdfb29021d5f451145ea437b7b7fcfdf2b5ad6317e1baf7c",
    "7499a0d573fdc58c01ade33af02403fd826d2bec66119cc24096706fccf302c0",
)
MANIFEST_ROLES = (
    "FRESH_OFFLINE_SOURCE",
    "FRESH_MATCHED_TARGET_1",
    "FRESH_MATCHED_TARGET_2",
    "FRESH_MATCHED_TARGET_3",
    "FRESH_MATCHED_TARGET_4",
    "FRESH_INCOMPATIBLE_SCHEMA_OOD",
)
ARMS = ("REVALIDATED_FAIR_PROGRAM_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
TARGET_DISTRIBUTION_COUNT = 4
ACQUISITION_BLOCK_SIZE = 4
MINIMUM_TARGET_LABELS_PER_DISTRIBUTION = 12
MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION = 24
STABLE_CONFIRMATION_BLOCKS = 2
REVALIDATED_PRIOR_CONFIRMATION_CREDIT = 1
OFFLINE_SOURCE_LABELS = 20
MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR = 20_000
RESOURCE_STEP_CAP = 128
REGISTER_COUNT = 5
MAXIMUM_RESIDUAL_SUPPORT = 3
IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM = 4
MAXIMUM_DECISIONS_PER_OCCURRENCE = 5
MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM = 2
PLANNING_HORIZON = 3
TOTAL_WORK_AXES = (
    "target_labels",
    "synthesis_candidate_evaluations",
    "planning_compute_events",
    "certificate_evaluations",
    "execution_steps",
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v184.py",
    "src/acfqp/open_world_fair_expression_machine_v184.py",
    "src/acfqp/open_world_fair_expression_oracle_v184.py",
    "src/acfqp/open_world_ranked_machine_v183.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/phase3e_ids.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_fair_expression_protocol_v184() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    predecessor_verification = predecessor.verify_retained_open_world_ranked_machine_campaign_v183(
        root / ".tmp" / "exact-freeze" / "v183_ranked_machine_campaign"
    )
    payload = {
        "schema": "acfqp.open_world_fair_expression_protocol.v184",
        "predecessor_campaign_id": predecessor.EXPECTED_CAMPAIGN_ID,
        "predecessor_verification_id": predecessor_verification["verification_id"],
        "predecessor_preserved": True,
        "fresh_successor_identity_required": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V184),
        "manifest_roles": list(MANIFEST_ROLES),
        "manifest_count": len(MANIFEST_COMMITMENTS_V184),
        "target_distribution_count": TARGET_DISTRIBUTION_COUNT,
        "arms": list(ARMS),
        "acquisition_block_size": ACQUISITION_BLOCK_SIZE,
        "minimum_target_labels_per_distribution": MINIMUM_TARGET_LABELS_PER_DISTRIBUTION,
        "maximum_target_labels_per_distribution": MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION,
        "stable_confirmation_blocks": STABLE_CONFIRMATION_BLOCKS,
        "revalidated_prior_confirmation_credit": REVALIDATED_PRIOR_CONFIRMATION_CREDIT,
        "offline_source_labels": OFFLINE_SOURCE_LABELS,
        "maximum_enumeration_events_per_scalar": MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR,
        "resource_step_cap": RESOURCE_STEP_CAP,
        "register_count": REGISTER_COUNT,
        "maximum_residual_support": MAXIMUM_RESIDUAL_SUPPORT,
        "iid_occurrences_per_distribution_per_arm": IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM,
        "maximum_decisions_per_occurrence": MAXIMUM_DECISIONS_PER_OCCURRENCE,
        "maximum_local_ground_labels_per_distribution_per_arm": MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM,
        "planning_horizon": PLANNING_HORIZON,
        "total_work_axes": list(TOTAL_WORK_AXES),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "manifest_preimages_revealed": False,
        "source_or_target_outcomes_accessed": False,
        "whole_program_shape_catalog_forbidden": True,
        "candidate_language_countably_infinite": True,
        "fair_size_ordered_enumeration_required": True,
        "actual_search_prefix_must_be_resource_bounded": True,
        "resource_cap_exhaustion_is_not_infeasibility": True,
        "structural_totality_certificate_required": True,
        "new_primitive_opcode_invention_claimed": False,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "archive_mdl_discount_forbidden": True,
        "prior_credit_requires_current_row_revalidation": True,
        "same_target_stream_until_prior_stop": True,
        "horizon_greater_than_two": True,
        "target_ground_rows_require_preceding_certificate_failure": True,
        "compute_cap_failure_cannot_request_ground_label": True,
        "incompatible_schema_prior_rejected_before_target_query": True,
        "componentwise_target_work_dominance_required": True,
        "source_labels_target_labels_execution_steps_synthesis_planning_and_certificate_compute_separate": True,
        "multi_distribution_iid_sample_efficiency_required": True,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "protocol_id": domains.extension_content_id_v184(
            domains.CONSTRUCTION_K7_PROTOCOL_V184_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldFairExpressionProtocolV184:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V184 protocol is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_fair_expression_protocol_v184() -> OpenWorldFairExpressionProtocolV184:
    document = build_open_world_fair_expression_protocol_v184()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V184 protocol changed")
    return OpenWorldFairExpressionProtocolV184(
        _ISSUER,
        raw,
        document["protocol_id"],
    )


__all__ = (
    "ACQUISITION_BLOCK_SIZE",
    "ARMS",
    "EXPECTED_PROTOCOL_ID",
    "IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM",
    "MANIFEST_COMMITMENTS_V184",
    "MANIFEST_ROLES",
    "MAXIMUM_DECISIONS_PER_OCCURRENCE",
    "MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR",
    "MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM",
    "MAXIMUM_RESIDUAL_SUPPORT",
    "MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION",
    "MINIMUM_TARGET_LABELS_PER_DISTRIBUTION",
    "OFFLINE_SOURCE_LABELS",
    "PLANNING_HORIZON",
    "REGISTER_COUNT",
    "RESOURCE_STEP_CAP",
    "REVALIDATED_PRIOR_CONFIRMATION_CREDIT",
    "STABLE_CONFIRMATION_BLOCKS",
    "TARGET_DISTRIBUTION_COUNT",
    "TOTAL_WORK_AXES",
    "build_open_world_fair_expression_protocol_v184",
    "freeze_open_world_fair_expression_protocol_v184",
)
