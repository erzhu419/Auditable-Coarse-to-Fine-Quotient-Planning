"""Outcome-free preregistration for the corrected V121r1 Gate."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v121r1 as domains
from acfqp import construction_k7_generic_artifact_subprogram_preregistration_v121 as previous
from acfqp.construction_k7_generic_artifact_subprogram_campaign_v121 import (
    CAMPAIGN_ID as FAILED_V121_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as FAILED_V121_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as FAILED_V121_CAMPAIGN_SHA256,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("0991d85c4543c6316487b4eea5e5b957e1d1df4b",)
FAILED_PREDECESSOR_COMMIT = "ad573d16f083640740af6f4a8bab9f4d4313d7f8"
PREREGISTRATION_ID = "edb57e586d5eb974fc39ac209d99fb06f8548ab669afff8da8b2c4c51a9cdf8b"
EXPECTED_CANONICAL_BYTE_COUNT = 45_392
EXPECTED_CANONICAL_SHA256 = "608565b379a306883109eb8be0101e24cce1fe09cd7a1b721a323a321fb30d05"
TARGET_OCCURRENCES = ((FAMILY, 1_034_101), (FAMILY, 1_034_102))
TARGET_EPISODE_INDICES = (278, 279, 280)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v121r1.py",
        1596,
        "e2d9730665b604eb8d56be5c85b50014959f8cb3c6fb716a80a29e65bbc2b171",
    ),
    (
        "src/acfqp/generic_subprogram_opportunity_independent_campaign_core_v121r1.py",
        10515,
        "7b705d917260005efbc87c37310e88816c748f0f95bdcec292fb61ad83bfe034",
    ),
    (
        "src/acfqp/construction_k7_generic_artifact_subprogram_preregistration_v121.py",
        14364,
        "1d9512baa5accbfe87cba674bfeae26e1dc4223864a45d8ca7f3ca2cf0a04174",
    ),
    (
        "src/acfqp/construction_k7_generic_artifact_subprogram_campaign_v121.py",
        5432,
        "540d18f72a12af1a0f78df68e80a60ba4f895ce0ff0cade87c5f2e73589c7167",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_instantiator_v121.py",
        17117,
        "517c327fffd654e6cefef5469533146d890f9f19ab031c3d63a4be253bcbd994",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_acquisition_v121.py",
        10120,
        "a174c61411dab5794650df71100f601fb89e75a58b9f9f9fcece332f8bcae830",
    ),
    (
        "src/acfqp/generic_artifact_subprogram_campaign_core_v121.py",
        13671,
        "606b5dc400975579a1eaccb1442458f87b2e564089a2425c6f6d50406c347796",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7GenericSubprogramPreregistrationV121R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericSubprogramPreregistrationV121R1Error(message)


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v121r1() -> dict[str, Any]:
    config = copy.deepcopy(dual_budget_config_v119())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(
    source_campaign_bytes: Mapping[str, bytes], failed_v121_raw: bytes
) -> dict[str, Any]:
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    failed = loads_canonical_json(failed_v121_raw)
    if (
        canonical_json_bytes(failed) != failed_v121_raw
        or len(failed_v121_raw) != FAILED_V121_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(failed_v121_raw).hexdigest()
        != FAILED_V121_CAMPAIGN_SHA256
        or failed.get("campaign_id") != FAILED_V121_CAMPAIGN_ID
        or failed.get("registered_gate", {}).get("passed") is not False
        or failed.get("registered_gate", {}).get("passed_target_occurrence_count")
        != 1
    ):
        _fail("V121r1 frozen failed V121 predecessor changed")
    payload = {
        "schema": "acfqp.generic_subprogram_opportunity_independent_preregistration.v121r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v121_campaign_id": FAILED_V121_CAMPAIGN_ID,
            "v121_campaign_byte_count": FAILED_V121_CAMPAIGN_BYTE_COUNT,
            "v121_campaign_sha256": FAILED_V121_CAMPAIGN_SHA256,
            "v121_failure_commit": FAILED_PREDECESSOR_COMMIT,
            "registered_gate_passed": False,
            "passed_occurrence_count": 1,
            "failed_occurrence_seed": 1_033_102,
            "failed_gate_key": "same_epoch_genesis_authorization_observed",
            "failed_gate_observed_value": False,
            "failed_occurrence_episode_success_count": 3,
            "failed_predecessor_identity_and_bytes_retained": True,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v121r1_domains": dict(
                domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V121R1
            ),
            "frozen_before_any_registered_v121r1_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v121r1()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "no_new_development_outcome_executed": True,
            "correction_tested_only_on_frozen_failed_v121_bytes": True,
        },
        "correction_contract": {
            "same_epoch_cache_hit_is_workload_opportunity_not_construction_obligation": True,
            "same_epoch_cache_hit_count_may_be_zero": True,
            "every_observed_zero_transition_hit_still_requires_exact_genesis_identity": True,
            "every_cross_epoch_hit_still_requires_authorization_chain": True,
            "all_nonopportunity_v121_gate_criteria_unchanged": True,
            "base_v121_occurrence_embedded_without_scientific_field_changes": True,
            "strict_no_prior_and_ood_controls_unchanged": True,
            "all_registered_episodes_must_succeed": True,
            "local_ground_distinction_only_after_certificate_failure": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "opportunity_independent_gate_used_in_every_occurrence": True,
            "all_scientific_outcome_fields_preserved": True,
            "generic_symbol_binding_used_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_acquisition_labels": 320,
            "strict_complete_model_attempts_per_occurrence": 1,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "same_epoch_genesis_authorized_cache_hits_are_diagnostic_not_gate": True,
            "sample_labels_execution_steps_binding_derivation_planning_dependency_and_library_derivation_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v121r1_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_generic_artifact_subprogram_partial_pipeline_verified": False,
            "legacy_shape_specific_planner_execution_adapter_present": True,
            "generic_planner_execution_adapter_verified": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
            "compiled_model_cache_or_receipt_used_as_safety_authority": False,
            "global_lumpability_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v121r1(
            domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_PREREGISTRATION_V121R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericSubprogramPreregistrationV121R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v121r1(
                domains.CONSTRUCTION_K7_GENERIC_SUBPROGRAM_PREREGISTRATION_V121R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V121r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericSubprogramPreregistrationV121R1 | None = None


def freeze_generic_subprogram_preregistration_v121r1(
    source_campaign_bytes: Mapping[str, bytes], failed_v121_raw: bytes
) -> GenericSubprogramPreregistrationV121R1:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V121r1 preregistered source closure changed")
        document = _document(source_campaign_bytes, failed_v121_raw)
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V121r1 frozen preregistration changed")
        _CACHE = GenericSubprogramPreregistrationV121R1(_ISSUER, raw, identity)
    return _CACHE


def verify_generic_subprogram_preregistration_v121r1(
    value: Any,
    source_campaign_bytes: Mapping[str, bytes],
    failed_v121_raw: bytes,
) -> GenericSubprogramPreregistrationV121R1:
    if type(value) is not GenericSubprogramPreregistrationV121R1:
        _fail("V121r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_generic_subprogram_preregistration_v121r1(
        source_campaign_bytes, failed_v121_raw
    )
    if value is not expected:
        _fail("V121r1 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v121r1",
    "freeze_generic_subprogram_preregistration_v121r1",
    "verify_generic_subprogram_preregistration_v121r1",
)
