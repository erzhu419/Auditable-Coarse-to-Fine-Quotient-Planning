"""Outcome-free preregistration for fresh V91r2 source synthesis."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r2 as domains
from acfqp import construction_k7_occurrence_balanced_source_preregistration_v91r1 as previous
from acfqp.construction_k7_occurrence_balanced_source_failure_v91r1 import (
    FAILURE_ID as FAILED_V91R1_ID,
)
from acfqp.construction_k7_residual_factor_library_v62 import LIBRARY_ARTIFACT_ID
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    LIBRARY_ARTIFACT_ID as TEMPLATE_LIBRARY_ARTIFACT_ID,
)
from acfqp.generic_occurrence_balanced_compiler_ready_acquisition_v66 import (
    run_occurrence_balanced_compiler_ready_acquisition_v66,
)
from acfqp.generic_occurrence_balanced_model_compiler_v66 import (
    compile_occurrence_balanced_model_v66,
)
from acfqp.generic_prior_only_partial_acquisition_v67 import (
    acquire_prior_only_partial_candidate_v67,
)
from acfqp.prior_only_occurrence_source_campaign_core_v91r2 import (
    build_prior_only_occurrence_source_campaign_document_v91r2,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "a19c8d9"
PREREGISTRATION_ID = (
    "57ed9c74fb7944ffa6f21dc4450cb45d5299e81424b8229ac8055282b161e7b9"
)
EXPECTED_CANONICAL_BYTE_COUNT = 6_927
EXPECTED_CANONICAL_SHA256 = (
    "e1e8e35912e0508c65ce359d8ba736875f01ea94471022446d9e5db889735639"
)
SOURCE_FAMILY = "COUPLED_EXCHANGE"
SOURCE_POOL_SEEDS = (941_101, 941_102)
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 2
SOURCE_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS = 160
MAXIMUM_EXECUTION_STEPS = 12
MAXIMUM_TERMINAL_PROGRAM_CANDIDATES = 8
PREQUENTIAL_CONFIDENCE_DENOMINATOR = 4_096
SOURCE_STAGE_COUNT = 5
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v91r2.py",
    "src/acfqp/generic_prior_only_partial_acquisition_v67.py",
    "src/acfqp/generic_reference_aligned_source_pool_v65.py",
    "src/acfqp/generic_occurrence_balanced_relation_schedule_v66.py",
    "src/acfqp/generic_occurrence_balanced_compiler_ready_acquisition_v66.py",
    "src/acfqp/generic_occurrence_balanced_model_compiler_v66.py",
    "src/acfqp/generic_compiler_ready_acquisition_v52.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/prior_only_occurrence_source_campaign_core_v91r2.py",
)
FROZEN_SOURCE_FACTS: tuple[tuple[str, int, str], ...] = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v91r2.py",
        2088,
        "1b62a26a0a6ba83da1a57a4ed648688ecaf137208466af5b2e109bac0fb91a2b",
    ),
    (
        "src/acfqp/generic_prior_only_partial_acquisition_v67.py",
        7077,
        "bea4c52c4250435e4366fcc7b0f34a19bbb9f1373cf2decfc0b26f2fab7977bd",
    ),
    (
        "src/acfqp/generic_reference_aligned_source_pool_v65.py",
        13843,
        "1ca6032f6a497b02fa7067cc87c106f05f553437f99295fe72a81d3674b916a3",
    ),
    (
        "src/acfqp/generic_occurrence_balanced_relation_schedule_v66.py",
        4175,
        "5e17e883abea7d4151f05f7f01a928624c855849b4c38432d8327ddd7bb122c1",
    ),
    (
        "src/acfqp/generic_occurrence_balanced_compiler_ready_acquisition_v66.py",
        3024,
        "30ec40aa06776761db27e749f1464a008a6c7b86b298feb454f30d0528911195",
    ),
    (
        "src/acfqp/generic_occurrence_balanced_model_compiler_v66.py",
        10904,
        "87ff397712c562b06e43f71cfb0abb535298047588add7c32b726c8cc9ddca68",
    ),
    (
        "src/acfqp/generic_compiler_ready_acquisition_v52.py",
        14184,
        "bd22742ed4a3c17384053f5dc073dd00456085ddf9874fb41fa114b8e56048de",
    ),
    (
        "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
        36033,
        "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005",
    ),
    (
        "src/acfqp/prior_only_occurrence_source_campaign_core_v91r2.py",
        13727,
        "78ede6d9ff4a0a95e171a28b569614be0bf82e57f1653b903e1f2dd17e6a4d4c",
    ),
)


class ConstructionK7PriorOnlyOccurrenceSourcePreregistrationV91R2Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PriorOnlyOccurrenceSourcePreregistrationV91R2Error(
        message
    )


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v91r2() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v91r1())
    config.update(
        source_family=SOURCE_FAMILY,
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
        source_partial_acquisition_maximum_ground_labels=(
            SOURCE_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS
        ),
        maximum_execution_steps=MAXIMUM_EXECUTION_STEPS,
        maximum_terminal_program_candidates_to_try=(
            MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
        ),
        prequential_confidence_denominator=(
            PREQUENTIAL_CONFIDENCE_DENOMINATOR
        ),
    )
    config["families"][SOURCE_FAMILY] = {
        **config["families"][SOURCE_FAMILY],
        "stage_count": SOURCE_STAGE_COUNT,
    }
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.prior_only_occurrence_source_preregistration.v91r2",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "failed_v91r1_id": FAILED_V91R1_ID,
            "residual_factor_library_artifact_id": LIBRARY_ARTIFACT_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v91r2_domains": dict(
                domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R2
            ),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "prior_only_partial_acquisition_callable": _callable_fact(
                acquire_prior_only_partial_candidate_v67
            ),
            "occurrence_acquisition_callable": _callable_fact(
                run_occurrence_balanced_compiler_ready_acquisition_v66
            ),
            "model_compiler_callable": _callable_fact(
                compile_occurrence_balanced_model_v66
            ),
            "campaign_builder_callable": _callable_fact(
                build_prior_only_occurrence_source_campaign_document_v91r2
            ),
            "frozen_before_any_registered_v91r2_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "failed_v91r1_identity_preserved": True,
            "v91r1_failed_before_occurrence_balanced_schedule": True,
            "strict_complete_model_arm_not_required_by_source_only_synthesis": True,
            "strict_no_prior_arm_removed_not_totalized_or_relabelled": True,
            "matched_sample_tax_comparison_claimed": False,
            "failed_seed_diagnostic_is_not_registered_scientific_evidence": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS))
            == len(SOURCE_POOL_SEEDS),
            "source_stage_count": SOURCE_STAGE_COUNT,
            "fresh_target_identities_registered": [],
        },
        "source_partial_acquisition_contract": {
            "maximum_ground_support_labels": (
                SOURCE_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS
            ),
            "witness_blind_source_stream": True,
            "anonymous_factor_prior_only": True,
            "strict_complete_model_arm_executed": False,
            "frontier_exhaustion_used_as_positive_stop": False,
            "candidate_failure_may_retire_and_retrain": True,
            "proposal_is_not_safety_authority": True,
        },
        "model_acquisition_contract": {
            "prequential_confidence_denominator": (
                PREQUENTIAL_CONFIDENCE_DENOMINATOR
            ),
            "required_prequential_evidence_bits": 12,
            "confidence_selected_before_registered_outcomes": True,
            "fixed_label_floor_present": False,
            "fixed_confirmation_block_present": False,
            "heldout_rows_accessed_before_stop": False,
            "maximum_terminal_program_candidates_to_try": (
                MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
            ),
        },
        "registered_gate": {
            "required_relation": (
                "TWO_FRESH_PRIOR_ONLY_SOURCE_MEMBERS_AND_CERTIFICATE_DISCIPLINE_"
                "CLEAN_AND_REFERENCE_ALIGNED_AND_OCCURRENCE_BALANCED_AND_"
                "COMPILER_READY_HELDOUT_VALIDATED_AND_MULTIPLE_RESIDUAL_"
                "PROPOSALS_JOINTLY_COMPILED_AND_ZERO_TARGET_OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "irrelevant_strict_source_arm_must_be_absent": True,
            "multiple_residual_proposals_jointly_compiled_required": True,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "maximum_source_partial_acquisition_labels": (
                SOURCE_PARTIAL_ACQUISITION_MAXIMUM_GROUND_LABELS
            ),
            "maximum_execution_steps_per_source": MAXIMUM_EXECUTION_STEPS,
            "maximum_terminal_program_candidates_to_try": (
                MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
            ),
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_common_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "source_execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "target_axes_zero": True,
            "strict_arm_labels_are_zero_not_imputed": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v91r2_source_outcome_observed": False,
            "fresh_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "multi_step_target_plan_verified": False,
            "sample_tax_reduction_verified_in_second_domain": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v91r2_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v91r2(
            domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PREREGISTRATION_V91R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PriorOnlyOccurrenceSourcePreregistrationV91R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v91r2(
                domains.CONSTRUCTION_K7_PRIOR_ONLY_OCCURRENCE_SOURCE_PREREGISTRATION_V91R2_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V91r2 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PriorOnlyOccurrenceSourcePreregistrationV91R2 | None = None


def freeze_prior_only_occurrence_source_preregistration_v91r2(
) -> PriorOnlyOccurrenceSourcePreregistrationV91R2:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V91r2 frozen source facts changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r2 preregistration changed")
    _CACHE = PriorOnlyOccurrenceSourcePreregistrationV91R2(
        _ISSUER, raw, identity
    )
    return _CACHE


def verify_prior_only_occurrence_source_preregistration_v91r2(
    value: Any,
) -> PriorOnlyOccurrenceSourcePreregistrationV91R2:
    if type(value) is not PriorOnlyOccurrenceSourcePreregistrationV91R2:
        _fail("V91r2 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_prior_only_occurrence_source_preregistration_v91r2()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91r2 preregistration differs from frozen output")
    return value


__all__ = (
    "FAILED_V91R1_ID",
    "PREREGISTRATION_ID",
    "campaign_config_v91r2",
    "freeze_prior_only_occurrence_source_preregistration_v91r2",
    "verify_prior_only_occurrence_source_preregistration_v91r2",
)
