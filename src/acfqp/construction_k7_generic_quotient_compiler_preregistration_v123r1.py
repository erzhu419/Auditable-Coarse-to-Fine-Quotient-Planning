"""Fresh preregistration after the frozen V123 acquisition-cap failure."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v123r1 as domains
from acfqp import construction_k7_generic_factor_planner_preregistration_v122 as previous
from acfqp.construction_k7_generic_factor_planner_campaign_v122 import (
    CAMPAIGN_ID as V122_CAMPAIGN_ID,
    EXPECTED_CANONICAL_BYTE_COUNT as V122_CAMPAIGN_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V122_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_generic_factor_planner_independent_verifier_v122 import (
    EXPECTED_CANONICAL_BYTE_COUNT as V122_VERIFICATION_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256 as V122_VERIFICATION_SHA256,
    VERIFICATION_ID as V122_VERIFICATION_ID,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import derive_artifact_factor_projection_v120
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.generic_quotient_compiler_campaign_core_v123r1 import (
    FAILED_V123_PREREGISTRATION_ID,
    FAILED_V123_RECORD_SHA256,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "5e97dd369c8c4f54e043c431a2975f5b65e9a4ba",
    "27e99c1dca14e84fd91202b86995557852bfcdc3",
    "7ef40cf78206adfe998862907af69bdc5edbd2bc",
)
FAILED_V123_FREEZE_COMMIT = "f429108"
PREREGISTRATION_ID = "f588553d3113543de67d365c2fc743b7bb09ec5d70110deb906d480bb0f62991"
EXPECTED_CANONICAL_BYTE_COUNT = 47_198
EXPECTED_CANONICAL_SHA256 = "6b9d9e22e1a618ed08f70e3e54c7ae26b3e80f43a145c609d3f61d37c4f8e0be"
TARGET_OCCURRENCES = ((FAMILY, 1_037_101), (FAMILY, 1_037_102))
TARGET_EPISODE_INDICES = (287, 288, 289)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
MAXIMUM_ACQUISITION_LABELS = 2_048
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v123r1.py",
        1_607,
        "98b43c4f0bf6b43717b358ccba87d2f8aeed0e78992858d786c33800356d0371",
    ),
    (
        "src/acfqp/generic_quotient_compiler_campaign_core_v123r1.py",
        3_725,
        "c3104f5a1b0951f467aff9ac560af6939fc7d94c5a9fa7165e4646e5fcbbb921",
    ),
    (
        "src/acfqp/construction_k7_domain_registry_extension_v123.py",
        1_648,
        "eabe6565fa0bfd37f2c1115b40edc77200fbeb89f04ddd420d2f8a9bae42d36c",
    ),
    (
        "src/acfqp/generic_compiled_quotient_model_v123.py",
        14_452,
        "00dd6c664398e6386cfbf9707b9c5a6e09f8dd2b4ea14fcd0378ae8974272a00",
    ),
    (
        "src/acfqp/generic_quotient_compiler_sequence_v123.py",
        10_377,
        "31a2925ce1764c3551c6e3553c037c340d7ea11485c5f464087d823a8879d139",
    ),
    (
        "src/acfqp/generic_quotient_compiler_campaign_core_v123.py",
        13_568,
        "abcc4640a4104e4b042231cde1bcc0d02f5ac836a9673f95e7e46f1bb86c4097",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7GenericQuotientCompilerPreregistrationV123r1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericQuotientCompilerPreregistrationV123r1Error(message)


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _source_facts() -> list[dict[str, Any]]:
    return [
        {
            "relative_path": path,
            "byte_count": len((SOURCE_ROOT / path).read_bytes()),
            "sha256": hashlib.sha256((SOURCE_ROOT / path).read_bytes()).hexdigest(),
        }
        for path, _count, _digest in FROZEN_SOURCE_FACTS
    ]


def campaign_config_v123r1() -> dict[str, Any]:
    config = copy.deepcopy(dual_budget_config_v119())
    config["families"][FAMILY]["maximum_acquisition_labels"] = MAXIMUM_ACQUISITION_LABELS
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
    failed_v123_raw: bytes,
) -> dict[str, Any]:
    v122_campaign = loads_canonical_json(v122_campaign_raw)
    v122_verification = loads_canonical_json(v122_verification_raw)
    failed = loads_canonical_json(failed_v123_raw)
    if (
        len(v122_campaign_raw) != V122_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v122_campaign_raw).hexdigest() != V122_CAMPAIGN_SHA256
        or v122_campaign.get("campaign_id") != V122_CAMPAIGN_ID
        or v122_campaign.get("registered_gate", {}).get("passed") is not True
        or len(v122_verification_raw) != V122_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v122_verification_raw).hexdigest() != V122_VERIFICATION_SHA256
        or v122_verification.get("verification_id") != V122_VERIFICATION_ID
        or v122_verification.get("registered_gate_independently_verified") is not True
        or hashlib.sha256(failed_v123_raw).hexdigest() != FAILED_V123_RECORD_SHA256
        or failed.get("preregistration_id") != FAILED_V123_PREREGISTRATION_ID
        or failed.get("same_identity_rerun_forbidden") is not True
        or failed.get("outcome_kind") != "PREREGISTERED_RESOURCE_CAP_FAILURE"
    ):
        _fail("V123r1 predecessor chain changed")
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.generic_quotient_compiler_preregistration.v123r1",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_failed_predecessor": {
            "v123_preregistration_id": FAILED_V123_PREREGISTRATION_ID,
            "v123_failure_record_sha256": FAILED_V123_RECORD_SHA256,
            "v123_failure_record_byte_count": len(failed_v123_raw),
            "v123_failure_freeze_commit": FAILED_V123_FREEZE_COMMIT,
            "failed_seed": failed["failed_seed"],
            "failed_resource_cap": failed["frozen_maximum_acquisition_labels"],
            "same_identity_rerun_forbidden": True,
        },
        "frozen_success_predecessor": {
            "v122_campaign_id": V122_CAMPAIGN_ID,
            "v122_campaign_sha256": V122_CAMPAIGN_SHA256,
            "v122_verification_id": V122_VERIFICATION_ID,
            "v122_verification_sha256": V122_VERIFICATION_SHA256,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v123r1_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V123R1),
            "frozen_before_any_registered_v123r1_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v123r1()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "failed_v123_target_identities_excluded": True,
            "development_identities_excluded": True,
        },
        "construction_contract": {
            "algorithm_identical_to_frozen_v123_core": True,
            "only_preregistered_resource_cap_and_fresh_identities_changed": True,
            "generic_recursive_typed_evaluator_compiles_projected_successors": True,
            "generic_compiler_rebuilds_every_incremental_model_epoch": True,
            "planner_consumes_only_generic_compiler_models": True,
            "legacy_model_builder_is_posthoc_unpriced_control_only": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "generic_model_compiler_used_in_every_occurrence": True,
            "generic_planner_used_in_every_occurrence": True,
            "legacy_model_builder_not_planning_input_in_every_occurrence": True,
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
            "legacy_matched_control_compute_charged_to_generic_arm": False,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v123r1_target_outcome_observed": False,
            "producer_free_verification_present": False,
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
        "preregistration_id": domains.extension_content_id_v123r1(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_PREREGISTRATION_V123R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericQuotientCompilerPreregistrationV123r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v123r1(
                domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_PREREGISTRATION_V123R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V123r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericQuotientCompilerPreregistrationV123r1 | None = None


def freeze_generic_quotient_compiler_preregistration_v123r1(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
    failed_v123_raw: bytes,
) -> GenericQuotientCompilerPreregistrationV123r1:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V123r1 preregistered source closure changed")
        document = _document(
            source_campaign_bytes,
            v122_campaign_raw,
            v122_verification_raw,
            failed_v123_raw,
        )
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V123r1 frozen preregistration changed")
        _CACHE = GenericQuotientCompilerPreregistrationV123r1(_ISSUER, raw, identity)
    return _CACHE


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v123r1",
    "freeze_generic_quotient_compiler_preregistration_v123r1",
)
