"""Outcome-free preregistration for fresh V72 successor-support evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v72 as domains
from acfqp import construction_k7_role_free_prequential_preregistration_v71 as previous
from acfqp.generic_learned_successor_support_acquisition_v41 import (
    RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.successor_version_space_campaign_core_v72 import (
    build_successor_version_space_campaign_document_v72,
)


IMPLEMENTATION_COMMIT = "155c628"
PREREGISTRATION_ID = "79c720e3f6db4102b86467cb5af31107e6254e8695c7b42035fd49038d413c7b"
EXPECTED_CANONICAL_BYTE_COUNT = 6_482
EXPECTED_CANONICAL_SHA256 = "de79a6d219979414d0b725cc9eb6031b239b859b6c15ee9c6ee2cce9c3249be3"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V71_CAMPAIGN_ID = "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
V71_VERIFICATION_ID = "faf1e3d0569cacd98514c35874b0c59fb685436a326e899cb7dcc70ed94994fa"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
BALANCED_TARGET_SEEDS = (731_101, 731_102)
COUPLED_TARGET_SEEDS = (732_101, 732_102)
MAINTENANCE_TARGET_SEEDS = (733_101, 733_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v72.py",
    "src/acfqp/successor_version_space_campaign_core_v72.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_adaptive_role_free_terminal_acquisition_v35.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_relational_terminal_program_independent_replay_v32.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
)


class ConstructionK7SuccessorVersionSpacePreregistrationV72Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SuccessorVersionSpacePreregistrationV72Error(message)


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


def campaign_config_v72() -> dict[str, Any]:
    config = previous.campaign_config_v71()
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
        prequential_confidence_denominator=64,
        successor_confidence_denominator=64,
        maximum_successor_support_states=4_096,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
        residual_confidence_denominator=64,
        maximum_terminal_program_candidates_to_try=32,
        maximum_relational_support_branch_evaluations=1_000_000,
        relational_support_feasible_beam_width=32,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.successor_version_space_preregistration.v72",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v71_campaign_id": V71_CAMPAIGN_ID,
            "v71_verification_id": V71_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "v41_implementation_commit": "410fa53",
        },
        "retained_development_diagnostic": dict(
            RETAINED_V71_DEVELOPMENT_DIAGNOSTIC_V41
        ),
        "source_closure": {
            "source_facts": _source_facts(),
            "v72_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V72),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_successor_version_space_campaign_document_v72
            ),
            "frozen_before_any_registered_v72_target_outcome": True,
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
            and min(all_seeds) > 730_000,
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
            "schedule_compute_separate": True,
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
        "preregistration_id": domains.extension_content_id_v72(
            domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_PREREGISTRATION_V72_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SuccessorVersionSpacePreregistrationV72:
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
            or domains.extension_content_id_v72(
                domains.CONSTRUCTION_K7_SUCCESSOR_VERSION_SPACE_PREREGISTRATION_V72_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V72 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SuccessorVersionSpacePreregistrationV72 | None = None


def freeze_successor_version_space_preregistration_v72(
) -> SuccessorVersionSpacePreregistrationV72:
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
        _fail("frozen V72 preregistration changed")
    _CACHE = SuccessorVersionSpacePreregistrationV72(_ISSUER, raw, identity)
    return _CACHE


def verify_successor_version_space_preregistration_v72(
    value: Any,
) -> SuccessorVersionSpacePreregistrationV72:
    if type(value) is not SuccessorVersionSpacePreregistrationV72:
        _fail("V72 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_successor_version_space_preregistration_v72()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V72 preregistration differs from frozen output")
    return value


__all__ = (
    "BALANCED_TARGET_SEEDS",
    "COUPLED_TARGET_SEEDS",
    "MAINTENANCE_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v72",
    "freeze_successor_version_space_preregistration_v72",
    "verify_successor_version_space_preregistration_v72",
)
