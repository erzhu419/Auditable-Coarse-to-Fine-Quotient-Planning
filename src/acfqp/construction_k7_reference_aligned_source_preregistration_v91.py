"""Outcome-free preregistration for V91 coupled-source model synthesis."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_bounded_source_preregistration_v82 as previous
from acfqp import construction_k7_domain_registry_extension_v91 as domains
from acfqp.construction_k7_abstract_planning_primary_independent_verifier_v90 import (
    VERIFICATION_ID as V90_VERIFICATION_ID,
)
from acfqp.construction_k7_residual_factor_library_v62 import LIBRARY_ARTIFACT_ID
from acfqp.construction_k7_role_free_relational_template_library_v70 import (
    LIBRARY_ARTIFACT_ID as TEMPLATE_LIBRARY_ARTIFACT_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.reference_aligned_source_campaign_core_v91 import (
    build_reference_aligned_source_campaign_document_v91,
)


IMPLEMENTATION_COMMIT = "10a4f43"
PREREGISTRATION_ID = "9a4d8dc9a8d40024708df19e6689d59b94aed082fa9c6468f4867c34604578de"
EXPECTED_CANONICAL_BYTE_COUNT = 6_319
EXPECTED_CANONICAL_SHA256 = "dd40cb7bef5c2ba756e3c0e258a4c83a499a0f70821a7004137d127a8c7b43b1"
SOURCE_FAMILY = "COUPLED_EXCHANGE"
SOURCE_POOL_SEEDS = (921_101, 921_102)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 2
MAXIMUM_EXECUTION_STEPS = 12
MAXIMUM_TERMINAL_PROGRAM_CANDIDATES = 8
SOURCE_STAGE_COUNT = 5
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v91.py",
    "src/acfqp/generic_reference_aligned_source_pool_v65.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_compiler_ready_acquisition_v52.py",
    "src/acfqp/generic_compiler_ready_model_compiler_v52.py",
    "src/acfqp/generic_version_space_retaining_model_compiler_v51.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/reference_aligned_source_campaign_core_v91.py",
)
FROZEN_SOURCE_FACTS: tuple[tuple[str, int, str], ...] = (
    ("src/acfqp/construction_k7_domain_registry_extension_v91.py", 1528, "92d98be83a3d666c8c17ade505c27ee48ebdfd2f56a4641a851d82083a3943d7"),
    ("src/acfqp/generic_reference_aligned_source_pool_v65.py", 13843, "1ca6032f6a497b02fa7067cc87c106f05f553437f99295fe72a81d3674b916a3"),
    ("src/acfqp/generic_canonical_source_pool_v48.py", 10924, "d066f256e5b0e9b8cf512999fc86d8b699752df452681310473eda2cb4d2a835"),
    ("src/acfqp/generic_layout_factorized_world_model_v5.py", 36010, "83d0f1505b039b705f44646662d69311a52aeb9c785ad45976014406a0b252ad"),
    ("src/acfqp/generic_compiler_ready_acquisition_v52.py", 14184, "bd22742ed4a3c17384053f5dc073dd00456085ddf9874fb41fa114b8e56048de"),
    ("src/acfqp/generic_compiler_ready_model_compiler_v52.py", 6823, "f07b01b855f477e5d1853a9fe5ac76073da944443bdb92100da9f31f331ac14f"),
    ("src/acfqp/generic_version_space_retaining_model_compiler_v51.py", 10718, "b1ad634f052c710b65cdb85b88cea95a1773a024dc2e481521ae40ba68eebc67"),
    ("src/acfqp/generic_joint_successor_version_space_planner_v42.py", 36033, "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005"),
    ("src/acfqp/generic_source_complete_relational_world_model_v31.py", 5009, "efb982d243604a038dd9a173f84a8ccf8e26a87f9183e9393f23465ba5177bf0"),
    ("src/acfqp/reference_aligned_source_campaign_core_v91.py", 10248, "7ca67130c5464d160d091fa05789b9fde1e24675ed6b149c96a887c485c7cea5"),
)


class ConstructionK7ReferenceAlignedSourcePreregistrationV91Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReferenceAlignedSourcePreregistrationV91Error(message)


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


def campaign_config_v91() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v82())
    config.update(
        source_family=SOURCE_FAMILY,
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
        maximum_execution_steps=MAXIMUM_EXECUTION_STEPS,
        maximum_terminal_program_candidates_to_try=(
            MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
        ),
    )
    config["families"][SOURCE_FAMILY] = {
        **config["families"][SOURCE_FAMILY],
        "stage_count": SOURCE_STAGE_COUNT,
    }
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.reference_aligned_source_preregistration.v91",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v90_verification_id": V90_VERIFICATION_ID,
            "v82_failure_id": previous.V81_FAILED_CAMPAIGN_ID,
            "residual_factor_library_artifact_id": LIBRARY_ARTIFACT_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v91_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_reference_aligned_source_campaign_document_v91
            ),
            "frozen_before_any_registered_v91_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "coupled_construction_fixture_exact_layout_partition_produced_two_singletons": True,
            "coupled_construction_fixture_reference_alignment_recovered_one_shared_coordinate_system": True,
            "blind_seed_substitution_or_posthoc_source_selection_used": False,
            "all_fixed_source_members_must_be_retained": True,
            "finite_observation_structural_colors_not_used_as_hard_equality_gate": True,
            "stored_partial_candidate_layout_must_replay_from_issuance_prefix": True,
            "all_source_rows_then_used_for_unique_reference_alignment": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS))
            == len(SOURCE_POOL_SEEDS),
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "source_stage_count": SOURCE_STAGE_COUNT,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "reference_member_selected_by_minimum_content_id": True,
            "alignment_uses_only_anonymous_common_partial_source_observations": True,
            "source_terminal_acceptance_observations_available_to_matcher": True,
            "family_or_named_coordinate_used_by_alignment": False,
            "target_outcome_used_by_alignment_or_compiler": False,
            "v48_pooling_only_after_unique_reference_alignment": True,
            "v52_compiler_ready_heldout_validation_required": True,
            "all_batch_exact_residual_proposals_jointly_compiled": True,
            "compiled_model_is_proposal_not_safety_authority": True,
            "fresh_target_execution_forbidden": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_FRESH_COUPLED_SOURCE_MEMBERS_AND_CERTIFICATE_DISCIPLINE_"
                "CLEAN_AND_EVERY_SOURCE_LAYOUT_REPLAYED_AND_UNIQUELY_REFERENCE_"
                "ALIGNED_AND_POOLED_AND_COMPILER_READY_HELDOUT_VALIDATED_AND_"
                "MULTIPLE_RESIDUAL_PROPOSALS_JOINTLY_COMPILED_AND_ZERO_TARGET_"
                "OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "multiple_residual_proposals_jointly_compiled_required": True,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "maximum_execution_steps_per_source": MAXIMUM_EXECUTION_STEPS,
            "maximum_terminal_program_candidates_to_try": (
                MAXIMUM_TERMINAL_PROGRAM_CANDIDATES
            ),
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_common_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "source_execution_steps_separate": True,
            "alignment_derivation_compute_separate": True,
            "terminal_and_compiler_compute_separate": True,
            "planning_compute_separate": True,
            "target_axes_zero": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v91_source_outcome_observed": False,
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
        "fresh_registered_v91_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v91(
            domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_PREREGISTRATION_V91_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ReferenceAlignedSourcePreregistrationV91:
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
            or domains.extension_content_id_v91(
                domains.CONSTRUCTION_K7_REFERENCE_ALIGNED_PREREGISTRATION_V91_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V91 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ReferenceAlignedSourcePreregistrationV91 | None = None


def freeze_reference_aligned_source_preregistration_v91(
) -> ReferenceAlignedSourcePreregistrationV91:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V91 frozen source facts changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91 preregistration changed")
    _CACHE = ReferenceAlignedSourcePreregistrationV91(_ISSUER, raw, identity)
    return _CACHE


def verify_reference_aligned_source_preregistration_v91(
    value: Any,
) -> ReferenceAlignedSourcePreregistrationV91:
    if type(value) is not ReferenceAlignedSourcePreregistrationV91:
        _fail("V91 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_reference_aligned_source_preregistration_v91()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v91",
    "freeze_reference_aligned_source_preregistration_v91",
    "verify_reference_aligned_source_preregistration_v91",
)
