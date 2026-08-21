"""Outcome-free V124 cross-family generic-compiler preregistration."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v124 as domains
from acfqp import construction_k7_generic_quotient_compiler_preregistration_v123r1 as previous
from acfqp.construction_k7_generic_quotient_compiler_campaign_v123r1 import (
    CAMPAIGN_ID as V123R1_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V123R1_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V123R1_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_generic_quotient_compiler_independent_verifier_v123r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V123R1_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V123R1_VERIFICATION_SHA256,
    VERIFICATION_ID as V123R1_VERIFICATION_ID,
    freeze_generic_quotient_compiler_verification_v123r1,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, inventory_assembly_config_v118
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("998a737bde72b782a097832cf1b054ea8d384f1f",)
V123R1_VERIFICATION_COMMIT = "d12eb43a74fe7dcc29a883d50e450fcd4fa4b662"
PREREGISTRATION_ID = "6c477fe146df4ba12cf0b0fcfd79c2dc7d865dac3a2781b1b586104ca1add7cc"
EXPECTED_CANONICAL_BYTE_COUNT = 48_345
EXPECTED_CANONICAL_SHA256 = "df120bb239418ace660f1cabf6faf9501fff632c5a83ebaf6933b3fcfaadc493"
TARGET_OCCURRENCES = ((FAMILY, 1_039_101), (FAMILY, 1_039_102))
TARGET_EPISODE_INDICES = (296, 297, 298)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v124.py",
        1_658,
        "5f41e098dfc80e32937ba15806f7dfafa51448a6f3729fad5b99d417b7053f84",
    ),
    (
        "src/acfqp/cross_family_generic_compiler_sequence_v124.py",
        9_450,
        "eb9edeb894deaacff731f23579125cc3c3e5ab672ec513dc7ce9bd1917669a7c",
    ),
    (
        "src/acfqp/cross_family_generic_compiler_campaign_core_v124.py",
        10_402,
        "227ef3001eb49e08f574856e1253d6a5f6806aa659bfc21f6fa491cff883e327",
    ),
    (
        "src/acfqp/construction_k7_generic_quotient_compiler_campaign_v123r1.py",
        4_168,
        "8ade677f096c6c210ebd5aad4aec136efc3e7857e84e9e62f94125bb7417efea",
    ),
    (
        "src/acfqp/construction_k7_generic_quotient_compiler_independent_verifier_v123r1.py",
        29_941,
        "de6316b88bb0f707ac44df4e373ecae283077a9579761469ba735ecdf55aded1",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7CrossFamilyGenericCompilerPreregistrationV124Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CrossFamilyGenericCompilerPreregistrationV124Error(message)


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v124() -> dict[str, Any]:
    config = copy.deepcopy(inventory_assembly_config_v118())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _verify_predecessor(
    source_campaign_bytes: Mapping[str, bytes],
    campaign_raw: bytes,
    verification_raw: bytes,
) -> None:
    campaign = loads_canonical_json(campaign_raw)
    verification = loads_canonical_json(verification_raw)
    root = SOURCE_ROOT / ".tmp/exact-freeze"
    if (
        len(campaign_raw) != V123R1_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(campaign_raw).hexdigest() != V123R1_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V123R1_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(verification_raw) != V123R1_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(verification_raw).hexdigest() != V123R1_VERIFICATION_SHA256
        or verification.get("verification_id") != V123R1_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
        or freeze_generic_quotient_compiler_verification_v123r1(
            campaign_raw,
            (root / "v122_generic_factor_planner_campaign.json").read_bytes(),
            (root / "v122_generic_factor_planner_verification.json").read_bytes(),
            (root / "v123_generic_quotient_compiler_failure.json").read_bytes(),
            (root / "v121r1_generic_subprogram_campaign.json").read_bytes(),
            (root / "v121_generic_artifact_subprogram_campaign.json").read_bytes(),
            (root / "v121r1_generic_subprogram_verification.json").read_bytes(),
            dict(source_campaign_bytes),
        )
        != verification_raw
    ):
        _fail("V124 frozen V123r1 predecessor changed")


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v123r1_campaign_raw: bytes,
    v123r1_verification_raw: bytes,
) -> dict[str, Any]:
    _verify_predecessor(source_campaign_bytes, v123r1_campaign_raw, v123r1_verification_raw)
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.cross_family_generic_compiler_preregistration.v124",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v123r1_campaign_id": V123R1_CAMPAIGN_ID,
            "v123r1_campaign_byte_count": V123R1_CAMPAIGN_BYTE_COUNT,
            "v123r1_campaign_sha256": V123R1_CAMPAIGN_SHA256,
            "v123r1_verification_id": V123R1_VERIFICATION_ID,
            "v123r1_verification_byte_count": V123R1_VERIFICATION_BYTE_COUNT,
            "v123r1_verification_sha256": V123R1_VERIFICATION_SHA256,
            "v123r1_verification_commit": V123R1_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v124_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V124),
            "frozen_before_any_registered_v124_target_outcome": True,
        },
        "identity_contract": {
            "target_family": FAMILY,
            "target_occurrences": campaign_config_v124()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_030_003,
            "development_episode_indices": [290, 291, 292],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "same_generic_compiler_and_planner_as_v123r1": True,
            "second_structural_family_uses_different_state_and_action_widths": True,
            "every_model_epoch_reconstructed_by_generic_compiler": True,
            "legacy_shape_specific_model_builder_called": False,
            "legacy_matched_model_control_present": False,
            "legacy_shape_specific_planner_execution_adapter_present": False,
            "retained_v113_state_carrier_must_be_reported": True,
            "all_registered_episodes_must_succeed": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "target_family": FAMILY,
            "partial_acquisition_labels": 56,
            "generic_model_epoch_reconstructions": 6,
            "direct_generic_factor_program_plan_count": 17,
            "legacy_model_builder_called": False,
            "all_three_episodes_succeeded": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "generic_compiler_used_in_every_occurrence": True,
            "legacy_model_builder_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
            "unused_resource_headroom_not_counted_as_sample_labels": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v124_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
            "retained_v113_state_carrier_present": True,
            "complete_ground_world_model_synthesized": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v124(domains.CONSTRUCTION_K7_CROSS_FAMILY_GENERIC_COMPILER_PREREGISTRATION_V124_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CrossFamilyGenericCompilerPreregistrationV124:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("preregistration_id") != self.preregistration_id or domains.extension_content_id_v124(domains.CONSTRUCTION_K7_CROSS_FAMILY_GENERIC_COMPILER_PREREGISTRATION_V124_DOMAIN, payload) != self.preregistration_id:
            _fail("V124 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: CrossFamilyGenericCompilerPreregistrationV124 | None = None


def freeze_cross_family_generic_compiler_preregistration_v124(
    source_campaign_bytes: Mapping[str, bytes],
    v123r1_campaign_raw: bytes,
    v123r1_verification_raw: bytes,
) -> CrossFamilyGenericCompilerPreregistrationV124:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V124 preregistered source closure changed")
        document = _document(source_campaign_bytes, v123r1_campaign_raw, v123r1_verification_raw)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
            _fail("V124 frozen preregistration changed")
        _CACHE = CrossFamilyGenericCompilerPreregistrationV124(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("PREREGISTRATION_ID", "campaign_config_v124", "freeze_cross_family_generic_compiler_preregistration_v124")
