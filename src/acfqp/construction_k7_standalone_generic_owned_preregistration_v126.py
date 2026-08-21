"""Outcome-free preregistration for the V126 owned episode loop."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v126 as domains
from acfqp import construction_k7_standalone_generic_model_preregistration_v125 as previous
from acfqp.construction_k7_standalone_generic_model_campaign_v125 import (
    CAMPAIGN_ID as V125_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V125_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V125_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_standalone_generic_model_independent_verifier_v125 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V125_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V125_VERIFICATION_SHA256,
    VERIFICATION_ID as V125_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("3f735dfa3d025bbd3dc08cb793fc22e40c4b3201",)
V125_VERIFICATION_COMMIT = "a35468d"
PREREGISTRATION_ID = "d069767abba581d17917da663428ae29839267fa6255116d89d7b8f4a011da51"
EXPECTED_CANONICAL_BYTE_COUNT = 50_362
EXPECTED_CANONICAL_SHA256 = "8cd6fefda6a0cff993d89cdf4ba8054f4c7eeef4ebca7e398cd67cd3036011f6"
TARGET_OCCURRENCES = ((FAMILY, 1_041_101), (FAMILY, 1_041_102))
TARGET_EPISODE_INDICES = (305, 306, 307)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v126.py", 1_623, "e59c26dbef84dd7b1836745d05aba2e59db62010d472f0e3ee04bc6aaf0518c6"),
    ("src/acfqp/standalone_generic_owned_sequence_v126.py", 27_341, "66bdb98e9b4ce4994a2a2198bbadbe268aca59e5f5219e24e71ab3e77cc09a4a"),
    ("src/acfqp/standalone_generic_owned_campaign_core_v126.py", 10_979, "4dd8173438414aaf2cf058a80ea5f19b5ad5c65cde2304fa7c8a3912957fb0ad"),
    ("src/acfqp/construction_k7_standalone_generic_model_campaign_v125.py", 3_551, "afbd956737e93b00d2c5c180ec048213fe3175da18c9003f9f2f35d2ceda981a"),
    ("src/acfqp/construction_k7_standalone_generic_model_independent_verifier_v125.py", 30_548, "2adc1c93641967d32d16c2dc07aa90d516c50835ba96492ffe7e24614c1250df"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7StandaloneGenericOwnedPreregistrationV126Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericOwnedPreregistrationV126Error(message)


def _frozen_source_facts():
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _source_facts():
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v126() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v125())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v125_campaign_raw: bytes,
    v125_verification_raw: bytes,
) -> dict[str, Any]:
    campaign = loads_canonical_json(v125_campaign_raw)
    verification = loads_canonical_json(v125_verification_raw)
    if (
        len(v125_campaign_raw) != V125_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v125_campaign_raw).hexdigest() != V125_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V125_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v125_verification_raw) != V125_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v125_verification_raw).hexdigest() != V125_VERIFICATION_SHA256
        or verification.get("verification_id") != V125_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V126 frozen V125 predecessor changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.standalone_generic_owned_preregistration.v126",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v125_campaign_id": V125_CAMPAIGN_ID,
            "v125_campaign_byte_count": V125_CAMPAIGN_BYTE_COUNT,
            "v125_campaign_sha256": V125_CAMPAIGN_SHA256,
            "v125_verification_id": V125_VERIFICATION_ID,
            "v125_verification_byte_count": V125_VERIFICATION_BYTE_COUNT,
            "v125_verification_sha256": V125_VERIFICATION_SHA256,
            "v125_verification_commit": V125_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v126_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V126),
            "frozen_before_any_registered_v126_target_outcome": True,
        },
        "identity_contract": {
            "target_family": FAMILY,
            "target_occurrences": campaign_config_v126()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_030_004,
            "development_episode_indices": [302, 303, 304],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "owned_v126_episode_loop_required": True,
            "standalone_v125_state_carrier_required": True,
            "retained_v113_state_carrier_present": False,
            "retained_v113_sequence_orchestration_present": False,
            "retained_v119_sequence_orchestration_present": False,
            "retained_v119_ordering_primitives_present": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "target_family": FAMILY,
            "development_seed": 1_030_004,
            "owned_episode_loop_implementation_present": True,
            "retained_v113_sequence_orchestration_present": False,
            "retained_v119_sequence_orchestration_present": False,
            "all_three_episodes_succeeded": True,
            "lifetime_target_labels": 22,
            "execution_steps": 10,
            "direct_generic_factor_program_plans": 5,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "owned_v126_episode_loop_used_in_every_occurrence": True,
            "retained_v113_sequence_orchestration_absent_in_every_occurrence": True,
            "retained_v119_sequence_orchestration_absent_in_every_occurrence": True,
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
            "registered_v126_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "retained_v113_state_carrier_present": False,
            "retained_v113_sequence_orchestration_present": False,
            "retained_v119_sequence_orchestration_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v126(
            domains.CONSTRUCTION_K7_STANDALONE_GENERIC_OWNED_PREREGISTRATION_V126_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StandaloneGenericOwnedPreregistrationV126:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v126(
                domains.CONSTRUCTION_K7_STANDALONE_GENERIC_OWNED_PREREGISTRATION_V126_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V126 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def freeze_standalone_generic_owned_preregistration_v126(
    source_campaign_bytes: Mapping[str, bytes],
    v125_campaign_raw: bytes,
    v125_verification_raw: bytes,
):
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V126 preregistered source closure changed")
        document = _document(source_campaign_bytes, v125_campaign_raw, v125_verification_raw)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V126 frozen preregistration changed")
        _CACHE = StandaloneGenericOwnedPreregistrationV126(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v126",
    "freeze_standalone_generic_owned_preregistration_v126",
)
