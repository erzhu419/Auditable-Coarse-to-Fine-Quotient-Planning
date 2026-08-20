"""Outcome-free preregistration for the V73 reusable-model target campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v73 as domains
from acfqp import construction_k7_successor_version_space_preregistration_v72r1 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reusable_version_space_campaign_core_v73 import (
    build_reusable_version_space_campaign_document_v73,
)


IMPLEMENTATION_COMMIT = "09c7bc2"
PREREGISTRATION_ID = "8d05c4c1c5ec6dfab6be1e3ced0130656acefb729c5b93fc88169f48b45646f7"
EXPECTED_CANONICAL_BYTE_COUNT = 6_679
EXPECTED_CANONICAL_SHA256 = "67a0706ae0d59b7500d1b8d776ecf8c172b6735916eaa5b87973419a615ff700"
V72R1_CAMPAIGN_ID = "2d570b3853f574083cb7e93e2f0ca026a985ca6cd5b2b12475eb4ebc5ead1e80"
V72R1_VERIFICATION_ID = "8d2c9459b3e0ccea9d4b00b5ccc6808cd1e03ac6ac34ff8a97c4227c212287a6"
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
BALANCED_TARGET_SEEDS = (751_101, 751_102)
COUPLED_TARGET_SEEDS = (752_101, 752_102)
MAINTENANCE_TARGET_SEEDS = (753_101, 753_102)
SOURCE_EPISODE_INDEX = 0
TARGET_EPISODE_INDEX = 1
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
MINIMUM_COMPILED_OCCURRENCE_COUNT = 3
MINIMUM_REDUCED_OCCURRENCE_COUNT = 1
MAXIMUM_TARGET_GROUND_SUPPORT_LABELS = 100_000
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v73.py",
    "src/acfqp/reusable_version_space_campaign_core_v73.py",
    "src/acfqp/generic_reusable_version_space_certificate_planner_v43.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_adaptive_role_free_terminal_acquisition_v35.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
)


class ConstructionK7ReusableVersionSpacePreregistrationV73Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableVersionSpacePreregistrationV73Error(message)


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


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v73() -> dict[str, Any]:
    config = previous.campaign_config_v72r1()
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
        source_episode_index=SOURCE_EPISODE_INDEX,
        target_episode_index=TARGET_EPISODE_INDEX,
        minimum_compiled_occurrence_count=MINIMUM_COMPILED_OCCURRENCE_COUNT,
        minimum_reduced_occurrence_count=MINIMUM_REDUCED_OCCURRENCE_COUNT,
        maximum_target_ground_support_labels=MAXIMUM_TARGET_GROUND_SUPPORT_LABELS,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.reusable_version_space_preregistration.v73",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v72r1_preregistration_id": previous.PREREGISTRATION_ID,
            "v72r1_campaign_id": V72R1_CAMPAIGN_ID,
            "v72r1_verification_id": V72R1_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
            "v42_implementation_commit": "81882ba",
            "v43_implementation_commit": "f3bb653",
            "v73_campaign_core_implementation_commit": IMPLEMENTATION_COMMIT,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v73_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V73),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_reusable_version_space_campaign_document_v73
            ),
            "frozen_before_any_registered_v73_source_or_target_outcome": True,
        },
        "fresh_occurrence_identities": {
            "target_families": {
                "BALANCED_BATCH_REFINEMENT": list(BALANCED_TARGET_SEEDS),
                "COUPLED_EXCHANGE": list(COUPLED_TARGET_SEEDS),
                "MAINTENANCE_CASCADE": list(MAINTENANCE_TARGET_SEEDS),
            },
            "target_occurrence_count": TARGET_OCCURRENCE_COUNT,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "target_episode_index": TARGET_EPISODE_INDEX,
            "source_and_target_episode_disjoint": (
                SOURCE_EPISODE_INDEX != TARGET_EPISODE_INDEX
            ),
            "fresh_seed_count": len(set(all_seeds)),
            "fresh_and_identity_disjoint": len(all_seeds) == len(set(all_seeds))
            and min(all_seeds) > 750_000,
        },
        "construction_contract": {
            "source_episode_builds_certificate_local_v31_evidence": True,
            "source_v41_proposal_must_be_heldout_validated": True,
            "v42_reconstructs_all_nonstatus_residual_version_spaces": True,
            "all_batch_exact_residual_expressions_retained": True,
            "all_mdl_minimal_terminal_trees_retained": True,
            "source_model_frozen_before_target_episode": True,
            "target_outcomes_used_to_refit_source_model": False,
            "target_arms": [
                "REUSABLE_JOINT_VERSION_SPACE_MODEL",
                "STRICT_NO_REUSABLE_MODEL",
            ],
            "same_target_adapter_kernel_seed_episode": True,
            "same_exact_query_local_certificate_engine": True,
            "only_reusable_model_availability_differs": True,
            "every_unseen_ground_query_requires_prior_certificate_failure": True,
            "query_local_exact_overlay_only_safety_authority": True,
            "source_abstention_allowed_without_target_execution": True,
        },
        "registered_gate": {
            "required_relation": (
                "SOURCE_HELDOUT_FAILURES_EQ_ZERO_AND_COMPILED_GE_3_AND_ALL_"
                "COMPILED_TARGETS_MATCHED_SUCCESS_AND_ALL_COMPILED_OOD_REJECTED_"
                "AND_CERTIFICATE_DISCIPLINE_CLEAN_AND_AGGREGATE_DERIVED_TARGET_"
                "LABELS_LT_STRICT_AND_REDUCED_OCCURRENCES_GE_1"
            ),
            "minimum_compiled_occurrence_count": MINIMUM_COMPILED_OCCURRENCE_COUNT,
            "minimum_reduced_occurrence_count": MINIMUM_REDUCED_OCCURRENCE_COUNT,
            "aggregate_actual_target_label_reduction_required": True,
            "abstention_allowed": True,
            "all_occurrences_retained": True,
            "failed_predecessor_preserved_before_any_successor": True,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_target_ground_support_labels_per_arm_occurrence": (
                MAXIMUM_TARGET_GROUND_SUPPORT_LABELS
            ),
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_successor_support_states": 4_096,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_template_labels_separate": True,
            "offline_residual_labels_separate": True,
            "source_common_partial_labels_separate": True,
            "source_certificate_local_labels_separate": True,
            "source_acquisition_consumed_labels_separate": True,
            "target_certificate_local_labels_separate_by_arm": True,
            "source_and_target_execution_steps_separate": True,
            "source_partial_and_relational_planning_compute_separate": True,
            "target_abstract_planning_compute_separate_by_arm": True,
            "source_cost_not_subtracted_from_target_label_comparison": True,
        },
        "claim_boundary": {
            "registered_source_or_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "online_adaptive_model_refit_integrated": False,
            "source_cost_amortization_evaluated": False,
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
        "fresh_registered_v73_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v73(
            domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_PREREGISTRATION_V73_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReusableVersionSpacePreregistrationV73:
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
            or domains.extension_content_id_v73(
                domains.CONSTRUCTION_K7_REUSABLE_VERSION_SPACE_PREREGISTRATION_V73_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V73 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReusableVersionSpacePreregistrationV73 | None = None


def freeze_reusable_version_space_preregistration_v73(
) -> ReusableVersionSpacePreregistrationV73:
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
        _fail("frozen V73 preregistration changed")
    _CACHE = ReusableVersionSpacePreregistrationV73(_ISSUER, raw, identity)
    return _CACHE


def verify_reusable_version_space_preregistration_v73(
    value: Any,
) -> ReusableVersionSpacePreregistrationV73:
    if type(value) is not ReusableVersionSpacePreregistrationV73:
        _fail("V73 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_reusable_version_space_preregistration_v73()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V73 preregistration differs from frozen output")
    return value


__all__ = (
    "BALANCED_TARGET_SEEDS",
    "COUPLED_TARGET_SEEDS",
    "MAINTENANCE_TARGET_SEEDS",
    "PREREGISTRATION_ID",
    "campaign_config_v73",
    "freeze_reusable_version_space_preregistration_v73",
    "verify_reusable_version_space_preregistration_v73",
)
