"""Outcome-free preregistration for the V123 generic quotient compiler."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v123 as domains
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
    freeze_generic_factor_planner_verification_v122,
)
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_dual_budget_adapter_v119 import FAMILY, dual_budget_config_v119
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = (
    "5e97dd369c8c4f54e043c431a2975f5b65e9a4ba",
    "27e99c1dca14e84fd91202b86995557852bfcdc3",
)
V122_VERIFICATION_COMMIT = "bba7a4074efdc89c3350eb204cd288428e693692"
PREREGISTRATION_ID = "abf11379f9075d225b0a0233d3f8d7fea7d57e26c7c2eaf0b9b0a8a1686d505d"
EXPECTED_CANONICAL_BYTE_COUNT = 48_219
EXPECTED_CANONICAL_SHA256 = "e66a9cc30b6d82038c1f166e8e0d24f11560235294e4755fc0cc168989cd9704"
TARGET_OCCURRENCES = ((FAMILY, 1_036_101), (FAMILY, 1_036_102))
TARGET_EPISODE_INDICES = (284, 285, 286)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 2
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
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
    (
        "src/acfqp/construction_k7_generic_factor_planner_campaign_v122.py",
        4_752,
        "367b805b2ed06d0a592651e386edca91735d8b0d8e4cb5179341186d54484f90",
    ),
    (
        "src/acfqp/construction_k7_generic_factor_planner_independent_verifier_v122.py",
        25_379,
        "8939be99bbdf7818cbf252f5744c3b04863618b55fd9b0b2f8135d8169cd76bf",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7GenericQuotientCompilerPreregistrationV123Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericQuotientCompilerPreregistrationV123Error(message)


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


def campaign_config_v123() -> dict[str, Any]:
    config = copy.deepcopy(dual_budget_config_v119())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed} for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
    )
    return config


def _verify_v122_predecessor(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
) -> None:
    campaign = loads_canonical_json(v122_campaign_raw)
    verification = loads_canonical_json(v122_verification_raw)
    failed_v121 = (
        SOURCE_ROOT / ".tmp/exact-freeze/v121_generic_artifact_subprogram_campaign.json"
    ).read_bytes()
    success_v121 = (
        SOURCE_ROOT / ".tmp/exact-freeze/v121r1_generic_subprogram_campaign.json"
    ).read_bytes()
    v121_verification = (
        SOURCE_ROOT / ".tmp/exact-freeze/v121r1_generic_subprogram_verification.json"
    ).read_bytes()
    if (
        canonical_json_bytes(campaign) != v122_campaign_raw
        or len(v122_campaign_raw) != V122_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(v122_campaign_raw).hexdigest() != V122_CAMPAIGN_SHA256
        or campaign.get("campaign_id") != V122_CAMPAIGN_ID
        or campaign.get("registered_gate", {}).get("passed") is not True
        or canonical_json_bytes(verification) != v122_verification_raw
        or len(v122_verification_raw) != V122_VERIFICATION_BYTE_COUNT
        or hashlib.sha256(v122_verification_raw).hexdigest()
        != V122_VERIFICATION_SHA256
        or verification.get("verification_id") != V122_VERIFICATION_ID
        or verification.get("registered_gate_independently_verified") is not True
        or freeze_generic_factor_planner_verification_v122(
            v122_campaign_raw,
            success_v121,
            failed_v121,
            v121_verification,
            dict(source_campaign_bytes),
        )
        != v122_verification_raw
    ):
        _fail("V123 frozen V122 predecessor changed")


def _document(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
) -> dict[str, Any]:
    _verify_v122_predecessor(
        source_campaign_bytes, v122_campaign_raw, v122_verification_raw
    )
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    payload = {
        "schema": "acfqp.generic_quotient_compiler_preregistration.v123",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_success_predecessor": {
            "v122_campaign_id": V122_CAMPAIGN_ID,
            "v122_campaign_byte_count": V122_CAMPAIGN_BYTE_COUNT,
            "v122_campaign_sha256": V122_CAMPAIGN_SHA256,
            "v122_verification_id": V122_VERIFICATION_ID,
            "v122_verification_byte_count": V122_VERIFICATION_BYTE_COUNT,
            "v122_verification_sha256": V122_VERIFICATION_SHA256,
            "v122_verification_commit": V122_VERIFICATION_COMMIT,
            "v122_identity_and_bytes_retained": True,
        },
        "artifact_factor_library": library,
        "artifact_factor_library_id": library["factor_library_id"],
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v123_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V123),
            "frozen_before_any_registered_v123_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v123()["target_occurrences"],
            "target_seeds_unique": True,
            "target_seeds_not_previously_exposed": True,
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
            "development_seed": 1_033_002,
            "development_episode_indices": [272, 273, 274],
            "development_identity_excluded_from_registered_gate": True,
        },
        "construction_contract": {
            "generic_recursive_typed_evaluator_compiles_projected_successors": True,
            "terminal_rules_derived_from_program_dependencies_and_raw_deltas": True,
            "generic_compiler_rebuilds_every_incremental_model_epoch": True,
            "planner_consumes_only_generic_compiler_models": True,
            "legacy_shape_specific_model_builder_used_only_as_posthoc_matched_control": True,
            "legacy_matched_control_compute_not_charged_to_generic_arm": True,
            "legacy_shape_specific_planner_execution_adapter_present": False,
            "unseen_expression_outside_v15_model_dispatch_must_compile": True,
            "higher_order_residual_must_remain_explicitly_unknown": True,
            "all_registered_episodes_must_succeed": True,
            "exact_query_local_certificate_remains_only_safety_authority": True,
            "local_ground_distinction_only_after_certificate_failure": True,
            "strict_incompatible_schema_no_transfer_required": True,
        },
        "development_evidence_retained_before_registration": {
            "generic_model_compiler_comparisons": 6,
            "legacy_model_builder_used_as_planning_input": False,
            "legacy_planner_adapter_present": False,
            "direct_generic_factor_program_plan_count_positive": True,
            "all_three_episodes_succeeded": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "generic_model_compiler_used_in_every_occurrence": True,
            "generic_planner_used_in_every_occurrence": True,
            "legacy_model_builder_not_planning_input_in_every_occurrence": True,
            "legacy_planner_adapter_absent_in_every_occurrence": True,
            "all_receding_episodes_succeed": True,
            "every_occurrence_retains_unknown_residual": True,
            "strict_control_outcomes_retained_without_gate_selection": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_acquisition_labels": 320,
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "sample_labels_execution_steps_derivation_planning_and_model_checks_separate": True,
            "legacy_matched_control_compute_charged_to_generic_arm": False,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v123_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_generic_quotient_compiler_pipeline_verified": False,
            "legacy_shape_specific_model_builder_used_as_planning_input": False,
            "legacy_shape_specific_planner_execution_adapter_present": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "sample_efficiency_improvement_claimed": False,
            "compiled_model_or_receipt_used_as_safety_authority": False,
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
        "preregistration_id": domains.extension_content_id_v123(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_PREREGISTRATION_V123_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericQuotientCompilerPreregistrationV123:
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
            or domains.extension_content_id_v123(
                domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_PREREGISTRATION_V123_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V123 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: GenericQuotientCompilerPreregistrationV123 | None = None


def freeze_generic_quotient_compiler_preregistration_v123(
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
) -> GenericQuotientCompilerPreregistrationV123:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V123 preregistered source closure changed")
        document = _document(
            source_campaign_bytes, v122_campaign_raw, v122_verification_raw
        )
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V123 frozen preregistration changed")
        _CACHE = GenericQuotientCompilerPreregistrationV123(_ISSUER, raw, identity)
    return _CACHE


def verify_generic_quotient_compiler_preregistration_v123(
    value: Any,
    source_campaign_bytes: Mapping[str, bytes],
    v122_campaign_raw: bytes,
    v122_verification_raw: bytes,
) -> GenericQuotientCompilerPreregistrationV123:
    if type(value) is not GenericQuotientCompilerPreregistrationV123:
        _fail("V123 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_generic_quotient_compiler_preregistration_v123(
        source_campaign_bytes, v122_campaign_raw, v122_verification_raw
    )
    if value is not expected:
        _fail("V123 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v123",
    "freeze_generic_quotient_compiler_preregistration_v123",
    "verify_generic_quotient_compiler_preregistration_v123",
)
