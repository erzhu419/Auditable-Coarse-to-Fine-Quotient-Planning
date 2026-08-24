"""Outcome-free protocol for V185 composite-macro transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp import construction_k7_open_world_fair_expression_campaign_freeze_v184 as predecessor
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PROTOCOL_ID = "991138799d91ba70f29ba583062b2d2e4fe3ceba38a485d4244ba20fd978e1cc"
EXPECTED_CANONICAL_BYTE_COUNT = 5_071
EXPECTED_CANONICAL_SHA256 = "f85deaabbbca0591c63b509deab069440bb4e95f7f776f377adcd6ff45ee4c8b"

MANIFEST_COMMITMENTS_V185 = (
    "7ac8517bb9dac91874e2ca6bb3ea751efd7a95df9ca58e05d36fad08697f4366",
    "d773f41828d9a4cc24cbb3667dc271f6241ca289d016d211f4fa97482017bb54",
    "e81317c79f0d5eb39705d3b36d3002cb3f22ea3b3af2055b5ddac9f627d2617a",
    "16a8adf36525959036201e67c53e37246e3b96ca336b28a75f4749b489590100",
    "25bfe39d243a634577c98bd73f591c2a53ae34c48551c5cb74458bd5e1f21d33",
    "bb121a59a8412290cb04dc2a4178a00fdf3ff13cd79e52d29806d8863b1598c7",
)
MANIFEST_ROLES = (
    "FRESH_OFFLINE_SOURCE",
    "FRESH_MATCHED_TARGET_1",
    "FRESH_MATCHED_TARGET_2",
    "FRESH_MATCHED_TARGET_3",
    "FRESH_MATCHED_TARGET_4",
    "FRESH_INCOMPATIBLE_SCHEMA_OOD",
)
ARMS = (
    "REVALIDATED_OBSERVATION_DERIVED_COMPOSITE_MACRO_PRIOR",
    "EMPTY_MACRO_LIBRARY_NO_PRIOR",
)
TARGET_DISTRIBUTION_COUNT = 4
ACQUISITION_BLOCK_SIZE = 4
MINIMUM_TARGET_LABELS_PER_DISTRIBUTION = 12
MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION = 28
STABLE_CONFIRMATION_BLOCKS = 2
REVALIDATED_PRIOR_CONFIRMATION_CREDIT = 1
OFFLINE_SOURCE_LABELS = 28
MAXIMUM_MACRO_CANDIDATE_EVALUATIONS_PER_SCALAR = 5_000
MAXIMUM_FAIR_ENUMERATION_EVENTS_PER_SCALAR = 30_000
RESOURCE_STEP_CAP = 160
REGISTER_COUNT = 6
MAXIMUM_RESIDUAL_SUPPORT = 2
MINIMUM_MACRO_OCCURRENCES = 6
MINIMUM_MACRO_OPERATOR_COUNT = 2
MINIMUM_MACRO_MDL_GAIN_TOKENS = 1
MAXIMUM_MACRO_COUNT = 32
IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM = 4
MAXIMUM_DECISIONS_PER_OCCURRENCE = 6
MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM = 2
PLANNING_HORIZON = 4
TOTAL_WORK_AXES = (
    "source_labels",
    "target_labels",
    "macro_discovery_events",
    "synthesis_candidate_evaluations",
    "planning_compute_events",
    "certificate_evaluations",
    "execution_steps",
)

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v185.py",
    "src/acfqp/open_world_composite_macro_machine_v185.py",
    "src/acfqp/open_world_composite_macro_oracle_v185.py",
    "src/acfqp/open_world_fair_expression_machine_v184.py",
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


def _retained_predecessor_identity(root: Path) -> tuple[str, str]:
    output = root / ".tmp" / "exact-freeze" / "v184_fair_expression_campaign"
    if tuple(sorted(path.name for path in output.iterdir())) != (
        "CAMPAIGN.json",
        "VERIFICATION.json",
    ):
        raise ValueError("V185 predecessor inventory changed")
    campaign_bytes = (output / "CAMPAIGN.json").read_bytes()
    verification_bytes = (output / "VERIFICATION.json").read_bytes()
    campaign = loads_canonical_json(campaign_bytes)
    verification = loads_canonical_json(verification_bytes)
    if not (
        type(campaign) is dict
        and type(verification) is dict
        and canonical_json_bytes(campaign) == campaign_bytes
        and canonical_json_bytes(verification) == verification_bytes
        and campaign.get("campaign_id") == predecessor.EXPECTED_CAMPAIGN_ID
        and verification.get("verification_id")
        == predecessor.EXPECTED_VERIFICATION_ID
        and len(campaign_bytes) == predecessor.EXPECTED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_bytes).hexdigest()
        == predecessor.EXPECTED_CAMPAIGN_SHA256
        and len(verification_bytes)
        == predecessor.EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(verification_bytes).hexdigest()
        == predecessor.EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V185 predecessor retained identity changed")
    return campaign["campaign_id"], verification["verification_id"]


def build_open_world_composite_macro_protocol_v185() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    predecessor_campaign_id, predecessor_verification_id = (
        _retained_predecessor_identity(root)
    )
    payload = {
        "schema": "acfqp.open_world_composite_macro_protocol.v185",
        "predecessor_campaign_id": predecessor_campaign_id,
        "predecessor_verification_id": predecessor_verification_id,
        "predecessor_preserved": True,
        "predecessor_exact_retained_bytes_rechecked": True,
        "fresh_successor_identity_required": True,
        "manifest_commitments": list(MANIFEST_COMMITMENTS_V185),
        "manifest_roles": list(MANIFEST_ROLES),
        "manifest_count": len(MANIFEST_COMMITMENTS_V185),
        "target_distribution_count": TARGET_DISTRIBUTION_COUNT,
        "arms": list(ARMS),
        "acquisition_block_size": ACQUISITION_BLOCK_SIZE,
        "minimum_target_labels_per_distribution": MINIMUM_TARGET_LABELS_PER_DISTRIBUTION,
        "maximum_target_labels_per_distribution": MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION,
        "stable_confirmation_blocks": STABLE_CONFIRMATION_BLOCKS,
        "revalidated_prior_confirmation_credit": REVALIDATED_PRIOR_CONFIRMATION_CREDIT,
        "offline_source_labels": OFFLINE_SOURCE_LABELS,
        "maximum_macro_candidate_evaluations_per_scalar": MAXIMUM_MACRO_CANDIDATE_EVALUATIONS_PER_SCALAR,
        "maximum_fair_enumeration_events_per_scalar": MAXIMUM_FAIR_ENUMERATION_EVENTS_PER_SCALAR,
        "resource_step_cap": RESOURCE_STEP_CAP,
        "register_count": REGISTER_COUNT,
        "maximum_residual_support": MAXIMUM_RESIDUAL_SUPPORT,
        "minimum_macro_occurrences": MINIMUM_MACRO_OCCURRENCES,
        "minimum_macro_operator_count": MINIMUM_MACRO_OPERATOR_COUNT,
        "minimum_macro_mdl_gain_tokens": MINIMUM_MACRO_MDL_GAIN_TOKENS,
        "maximum_macro_count": MAXIMUM_MACRO_COUNT,
        "iid_occurrences_per_distribution_per_arm": IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM,
        "maximum_decisions_per_occurrence": MAXIMUM_DECISIONS_PER_OCCURRENCE,
        "maximum_local_ground_labels_per_distribution_per_arm": MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM,
        "planning_horizon": PLANNING_HORIZON,
        "total_work_axes": list(TOTAL_WORK_AXES),
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "manifest_preimages_revealed": False,
        "source_or_target_outcomes_accessed": False,
        "source_generation_witness_schedule_supplied": False,
        "layout_or_factor_boundary_supplied": False,
        "predeclared_reusable_factor_slots": [],
        "predeclared_macro_bodies": [],
        "macro_discovery_rule": "POSITIVE_EXACT_TOKEN_MDL_GAIN",
        "macro_leaves_anonymized_by_first_distinct_ATOM_occurrence": True,
        "macro_target_instantiations_revalidated_on_every_current_row": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "only_macro_library_prior_toggled_between_arms": True,
        "archive_mdl_discount_forbidden": True,
        "prior_credit_requires_current_row_revalidation": True,
        "same_target_stream_until_prior_stop": True,
        "candidate_language_countably_infinite": True,
        "actual_search_prefix_must_be_resource_bounded": True,
        "resource_cap_exhaustion_is_not_infeasibility": True,
        "structural_totality_certificate_required": True,
        "reusable_composite_operator_invention_required": True,
        "new_low_level_primitive_opcode_invention_claimed": False,
        "horizon_greater_than_two": True,
        "target_ground_rows_require_preceding_certificate_failure": True,
        "compute_cap_failure_cannot_request_ground_label": True,
        "incompatible_schema_prior_rejected_before_target_query": True,
        "componentwise_target_work_dominance_required": True,
        "source_target_local_labels_execution_macro_synthesis_planning_and_certificate_compute_separate": True,
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
        "protocol_id": domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_PROTOCOL_V185_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCompositeMacroProtocolV185:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    protocol_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V185 protocol is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_composite_macro_protocol_v185() -> OpenWorldCompositeMacroProtocolV185:
    document = build_open_world_composite_macro_protocol_v185()
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != "0" * 64 and not (
        document["protocol_id"] == EXPECTED_PROTOCOL_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V185 protocol changed")
    return OpenWorldCompositeMacroProtocolV185(
        _ISSUER,
        raw,
        document["protocol_id"],
    )


__all__ = (
    "ACQUISITION_BLOCK_SIZE",
    "ARMS",
    "EXPECTED_PROTOCOL_ID",
    "IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM",
    "MANIFEST_COMMITMENTS_V185",
    "MANIFEST_ROLES",
    "MAXIMUM_DECISIONS_PER_OCCURRENCE",
    "MAXIMUM_FAIR_ENUMERATION_EVENTS_PER_SCALAR",
    "MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM",
    "MAXIMUM_MACRO_CANDIDATE_EVALUATIONS_PER_SCALAR",
    "MAXIMUM_MACRO_COUNT",
    "MAXIMUM_RESIDUAL_SUPPORT",
    "MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION",
    "MINIMUM_MACRO_MDL_GAIN_TOKENS",
    "MINIMUM_MACRO_OCCURRENCES",
    "MINIMUM_MACRO_OPERATOR_COUNT",
    "MINIMUM_TARGET_LABELS_PER_DISTRIBUTION",
    "OFFLINE_SOURCE_LABELS",
    "PLANNING_HORIZON",
    "REGISTER_COUNT",
    "RESOURCE_STEP_CAP",
    "REVALIDATED_PRIOR_CONFIRMATION_CREDIT",
    "STABLE_CONFIRMATION_BLOCKS",
    "TARGET_DISTRIBUTION_COUNT",
    "TOTAL_WORK_AXES",
    "build_open_world_composite_macro_protocol_v185",
    "freeze_open_world_composite_macro_protocol_v185",
)
