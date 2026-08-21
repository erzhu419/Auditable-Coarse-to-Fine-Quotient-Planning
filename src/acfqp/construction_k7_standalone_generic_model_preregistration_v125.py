"""Outcome-free preregistration for the standalone V125 model carrier."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v125 as domains
from acfqp import construction_k7_cross_family_generic_compiler_preregistration_v124 as previous
from acfqp.construction_k7_cross_family_generic_compiler_campaign_v124 import (
    CAMPAIGN_ID as V124_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V124_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V124_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_cross_family_generic_compiler_independent_verifier_v124 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V124_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V124_VERIFICATION_SHA256,
    VERIFICATION_ID as V124_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_inventory_assembly_adapter_v118 import FAMILY, inventory_assembly_config_v118
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("07e05055ffcfe6298d812b913b4adf80b323b596",)
V124_VERIFICATION_COMMIT = "6d810eb1aac305ff7685d53c38cfb5722cd47ff1"
PREREGISTRATION_ID = "4ca6082580322556781685581428cde138d7c4797cf41ebd4e825500d53d7c2c"
EXPECTED_CANONICAL_BYTE_COUNT = 49_730
EXPECTED_CANONICAL_SHA256 = "52afe442ade42e6b6e9d56b472ebbbdbc72c5db4dec89bac62c72206f1e3ec1e"
TARGET_OCCURRENCES = ((FAMILY, 1_040_101), (FAMILY, 1_040_102))
TARGET_EPISODE_INDICES = (299, 300, 301)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    ("src/acfqp/construction_k7_domain_registry_extension_v125.py", 1_935, "657d18e4fc16fcc226f4b92ddfa08728a34322a745245ddcbf9f978a722891c0"),
    ("src/acfqp/standalone_generic_model_epoch_v125.py", 14_778, "a84b3ed2546b632597a006e10b0cc7b7bb966e241afa27631c7759fb00ccf927"),
    ("src/acfqp/standalone_generic_model_sequence_v125.py", 9_274, "ac0e4506c107a2b5660c337b67daf61886f6f266149821019fc041c606d0a00e"),
    ("src/acfqp/standalone_generic_model_campaign_core_v125.py", 10_327, "cf049d84eed3903da9d03bca3497b9a8db718bf50167c3d50a6ed2cdf5695242"),
    ("src/acfqp/construction_k7_cross_family_generic_compiler_campaign_v124.py", 3_755, "1abc1d863d1f27b0399991cd29b4194c02ed3e47b323b4986c43981514469910"),
    ("src/acfqp/construction_k7_cross_family_generic_compiler_independent_verifier_v124.py", 15_571, "78e98154447032649bfe5af5c990535aa5e7a9749ff71c3e604d767f59559434"),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7StandaloneGenericModelPreregistrationV125Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7StandaloneGenericModelPreregistrationV125Error(message)


def _frozen_source_facts():
    return [{"relative_path": path, "byte_count": count, "sha256": digest} for path, count, digest in FROZEN_SOURCE_FACTS]


def _source_facts():
    return [
        {"relative_path": path, "byte_count": len((SOURCE_ROOT / path).read_bytes()), "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest()}
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v125() -> dict[str, Any]:
    config = copy.deepcopy(inventory_assembly_config_v118())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[{"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(source_campaign_bytes: Mapping[str, bytes], v124_campaign_raw: bytes, v124_verification_raw: bytes):
    campaign, verification = loads_canonical_json(v124_campaign_raw), loads_canonical_json(v124_verification_raw)
    if (
        len(v124_campaign_raw) != V124_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v124_campaign_raw).hexdigest() != V124_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V124_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or len(v124_verification_raw) != V124_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v124_verification_raw).hexdigest() != V124_VERIFICATION_SHA256
        or verification.get("verification_id") != V124_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
    ):
        _fail("V125 frozen V124 predecessor changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.standalone_generic_model_preregistration.v125",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v124_campaign_id": V124_CAMPAIGN_ID,
            "v124_campaign_byte_count": V124_CAMPAIGN_BYTE_COUNT,
            "v124_campaign_sha256": V124_CAMPAIGN_SHA256,
            "v124_verification_id": V124_VERIFICATION_ID,
            "v124_verification_byte_count": V124_VERIFICATION_BYTE_COUNT,
            "v124_verification_sha256": V124_VERIFICATION_SHA256,
            "v124_verification_commit": V124_VERIFICATION_COMMIT,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {"source_facts": _frozen_source_facts(), "v125_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V125), "frozen_before_any_registered_v125_target_outcome": True},
        "identity_contract": {
            "target_family": FAMILY,
            "target_occurrences": campaign_config_v125()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_030_003,
            "development_episode_indices": [290, 291, 292],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "standalone_v125_state_carrier_required": True,
            "bootstrap_update_and_match_receipts_use_v125_domains": True,
            "retained_v113_state_carrier_present": False,
            "retained_v113_sequence_orchestration_present": True,
            "legacy_shape_specific_model_builder_called": False,
            "recursive_generic_program_compiler_required": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "target_family": FAMILY,
            "standalone_model_epoch_reconstructions": 6,
            "retained_v113_state_carrier_present": False,
            "retained_v113_sequence_orchestration_present": True,
            "all_three_episodes_succeeded": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "standalone_v125_state_carrier_used_in_every_occurrence": True,
            "retained_v113_state_carrier_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {"target_worker_count": TARGET_WORKER_COUNT, "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT, "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS, "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT, "query_episode_count": len(TARGET_EPISODE_INDICES), "maximum_incremental_certificate_labels_per_episode": 100_000},
        "accounting_contract": {"sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True, "unused_resource_headroom_not_counted_as_sample_labels": True, "no_scalar_cost_aggregation": True},
        "claim_boundary": {
            "registered_v125_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "retained_v113_state_carrier_present": False,
            "retained_v113_sequence_orchestration_present": True,
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
    return {**payload, "preregistration_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_PREREGISTRATION_V125_DOMAIN, payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class StandaloneGenericModelPreregistrationV125:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self):
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if self._issuer is not _ISSUER or canonical_json_bytes(document) != self.canonical_bytes or document.get("preregistration_id") != self.preregistration_id or domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_PREREGISTRATION_V125_DOMAIN, payload) != self.preregistration_id:
            _fail("V125 preregistration bytes or issuer changed")

    def to_document(self):
        return loads_canonical_json(self.canonical_bytes)


_CACHE = None


def freeze_standalone_generic_model_preregistration_v125(source_campaign_bytes: Mapping[str, bytes], v124_campaign_raw: bytes, v124_verification_raw: bytes):
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V125 preregistered source closure changed")
        document = _document(source_campaign_bytes, v124_campaign_raw, v124_verification_raw)
        raw, identity = canonical_json_bytes(document), document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
            _fail("V125 frozen preregistration changed")
        _CACHE = StandaloneGenericModelPreregistrationV125(_ISSUER, raw, identity)
    return _CACHE


__all__ = ("PREREGISTRATION_ID", "campaign_config_v125", "freeze_standalone_generic_model_preregistration_v125")
