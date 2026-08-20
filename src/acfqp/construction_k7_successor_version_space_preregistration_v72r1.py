"""Outcome-free preregistration for the corrected fresh V72r1 campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v72r1 as domains
from acfqp import construction_k7_successor_version_space_preregistration_v72 as previous
from acfqp.construction_k7_successor_version_space_failure_v72 import (
    FAILURE_ID as V72_FAILURE_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.successor_version_space_campaign_core_v72r1 import (
    build_successor_version_space_campaign_document_v72r1,
)


IMPLEMENTATION_COMMIT = "2c6562c"
PREREGISTRATION_ID = "c1c206669904aa5f7a57a1a8f2a514119e5c6221945105f6808b3a1a7f66c7ca"
EXPECTED_CANONICAL_BYTE_COUNT = 6_598
EXPECTED_CANONICAL_SHA256 = "31df99245881da35ccefdeb15b6bcc82e93633a1279abdb078131ed46e614c2a"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V71_CAMPAIGN_ID = previous.V71_CAMPAIGN_ID
V71_VERIFICATION_ID = previous.V71_VERIFICATION_ID
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
BALANCED_TARGET_SEEDS = (741_101, 741_102)
COUPLED_TARGET_SEEDS = (742_101, 742_102)
MAINTENANCE_TARGET_SEEDS = (743_101, 743_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v72r1.py",
    "src/acfqp/successor_version_space_campaign_core_v72r1.py",
    "src/acfqp/successor_version_space_campaign_core_v72.py",
    "src/acfqp/construction_k7_successor_version_space_failure_v72.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_adaptive_role_free_terminal_acquisition_v35.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_relational_terminal_program_independent_replay_v32.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
)


class ConstructionK7SuccessorVersionSpacePreregistrationV72R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SuccessorVersionSpacePreregistrationV72R1Error(message)


def _source_facts() -> list[dict[str, Any]]:
    rows = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        rows.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return rows


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v72r1() -> dict[str, Any]:
    config = previous.campaign_config_v72()
    target_seeds = {
        "BALANCED_BATCH_REFINEMENT": BALANCED_TARGET_SEEDS,
        "COUPLED_EXCHANGE": COUPLED_TARGET_SEEDS,
        "MAINTENANCE_CASCADE": MAINTENANCE_TARGET_SEEDS,
    }
    for family, seeds in target_seeds.items():
        config["families"][family]["target_seeds"] = seeds
    config.update(
        target_seeds=target_seeds,
        target_occurrence_count=TARGET_OCCURRENCE_COUNT,
        worker_count=WORKER_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.successor_version_space_preregistration.v72r1",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "preserved_v72_failure_id": V72_FAILURE_ID,
            "v72_preregistration_id": previous.PREREGISTRATION_ID,
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v71_campaign_id": V71_CAMPAIGN_ID,
            "v71_verification_id": V71_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "v41_implementation_commit": "410fa53",
        },
        "failure_correction": {
            "preserved_failure_phase": "POST_WORKER_OCCURRENCE_AGGREGATION",
            "same_v72_identity_rerun": False,
            "fresh_successor_identity": True,
            "corrected_schedule_accounting": (
                "SUM_RETAINED_STATE_AND_ACTION_RELATION_SIGNATURE_ROWS"
            ),
            "occurrence_constructor_semantics_changed": False,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v72r1_domains": dict(
                domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V72R1
            ),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_successor_version_space_campaign_document_v72r1
            ),
            "frozen_before_any_registered_v72r1_target_outcome": True,
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS)
            },
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS)},
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS)
            },
            "target_occurrence_count": TARGET_OCCURRENCE_COUNT,
            "fresh_and_identity_disjoint": len(all_seeds) == len(set(all_seeds))
            and min(all_seeds) > 740_000,
        },
        "matched_acquisition_contract": {
            "arms": [
                "ROLE_FREE_FACTOR_PRIOR_ON",
                "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
            ],
            "same_target_query_pool": True,
            "same_outcome_blind_relation_covering_schedule": True,
            "same_v41_successor_version_space_guard": True,
            "same_prequential_stop_engine": True,
            "only_terminal_program_prior_switched": True,
            "status_output_coordinate_used_as_successor_guard_input": False,
            "batch_exact_successor_version_space_not_point_estimate": True,
            "heldout_never_participates_in_stop": True,
            "prequential_confidence_denominator": 64,
            "maximum_successor_support_states": 4_096,
            "fixed_label_floor_present": False,
            "fixed_confirmation_block_present": False,
        },
        "registered_gate": {
            "required_relation": (
                "ZERO_HELDOUT_FAILED_IN_BOTH_ARMS_AND_EACH_ARM_VALIDATED_GT_ZERO_"
                "AND_JOINTLY_COMPARABLE_GT_ZERO_AND_ALL_OOD_REJECTED"
            ),
            "abstention_allowed": True,
            "sample_reduction_required": False,
            "all_occurrences_retained": True,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_successor_support_states": 4_096,
            "maximum_relational_support_branch_evaluations": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_template_labels_separate": True,
            "offline_residual_labels_separate": True,
            "underlying_target_source_generation_labels_separate": True,
            "counterfactual_arm_consumed_labels_separate": True,
            "post_stop_heldout_audit_labels_separate": True,
            "execution_steps_separate": True,
            "schedule_relation_compute_separate": True,
            "terminal_constructor_compute_separate": True,
            "successor_model_derivation_compute_separate": True,
            "online_planning_compute_separate": True,
        },
        "claim_boundary": {
            "registered_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "online_adaptive_acquisition_integrated": False,
            "online_actual_sample_reduction_claimed": False,
            "statistical_coverage_claimed": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_target_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v72r1(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_PREREGISTRATION_V72R1_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SuccessorVersionSpacePreregistrationV72R1:
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
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v72r1(
                domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_PREREGISTRATION_V72R1_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V72r1 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SuccessorVersionSpacePreregistrationV72R1 | None = None


def freeze_successor_version_space_preregistration_v72r1(
) -> SuccessorVersionSpacePreregistrationV72R1:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V72r1 preregistration changed")
    _CACHE = SuccessorVersionSpacePreregistrationV72R1(_ISSUER, raw, identity)
    return _CACHE


def verify_successor_version_space_preregistration_v72r1(
    value: Any,
) -> SuccessorVersionSpacePreregistrationV72R1:
    if type(value) is not SuccessorVersionSpacePreregistrationV72R1:
        _fail("V72r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_successor_version_space_preregistration_v72r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V72r1 preregistration differs from frozen output")
    return value


__all__ = (
    "BALANCED_TARGET_SEEDS",
    "COUPLED_TARGET_SEEDS",
    "MAINTENANCE_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v72r1",
    "freeze_successor_version_space_preregistration_v72r1",
    "verify_successor_version_space_preregistration_v72r1",
)
