"""Outcome-free preregistration for the V78 pooled-source diagnostic."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v78 as domains
from acfqp import construction_k7_three_family_preregistration_v77 as previous
from acfqp.construction_k7_three_family_campaign_v77 import (
    CAMPAIGN_ID as V77_CAMPAIGN_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.pooled_source_campaign_core_v78 import (
    build_pooled_source_campaign_document_v78,
)


IMPLEMENTATION_COMMIT = "37f8a37"
PREREGISTRATION_ID = "d09b1ed1341bbefd2ce45b638e2dbf62bef4b9ae5b518217c1ad869ee1b97302"
EXPECTED_CANONICAL_BYTE_COUNT = 5_818
EXPECTED_CANONICAL_SHA256 = "edc1c1e54d99f2f20886b0b9c6d40049e59227aafb025bf62937987c7f1a1edb"
V77_FAILED_CAMPAIGN_ID = V77_CAMPAIGN_ID
SOURCE_FAMILY = "BALANCED_BATCH_REFINEMENT"
SOURCE_POOL_SEEDS = (779_101, 779_102)
SOURCE_EPISODE_INDEX = 0
SOURCE_WORKER_COUNT = 2
REQUIRED_SOURCE_MEMBER_COUNT = 2
TEMPLATE_LIBRARY_ARTIFACT_ID = previous.TEMPLATE_LIBRARY_ARTIFACT_ID
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v78.py",
    "src/acfqp/generic_canonical_source_pool_v48.py",
    "src/acfqp/pooled_source_campaign_core_v78.py",
    "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
    "src/acfqp/generic_learned_successor_support_acquisition_v41.py",
    "src/acfqp/generic_relation_covering_schedule_v39.py",
    "src/acfqp/generic_prequential_role_free_acquisition_v37.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/construction_k7_three_family_campaign_v77.py",
)


class ConstructionK7PooledSourcePreregistrationV78Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PooledSourcePreregistrationV78Error(message)


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


def campaign_config_v78() -> dict[str, Any]:
    config = previous.campaign_config_v77()
    config.update(
        source_family=SOURCE_FAMILY,
        source_pool_seeds=SOURCE_POOL_SEEDS,
        source_episode_index=SOURCE_EPISODE_INDEX,
        source_worker_count=SOURCE_WORKER_COUNT,
        required_source_member_count=REQUIRED_SOURCE_MEMBER_COUNT,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.canonical_pooled_source_preregistration.v78",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v77_failed_campaign_id": V77_FAILED_CAMPAIGN_ID,
            "v77_preregistration_id": previous.PREREGISTRATION_ID,
            "v76_failure_id": previous.V76_FAILURE_ID,
            "v75r5_campaign_id": previous.V75R5_CAMPAIGN_ID,
            "v75r5_verification_id": previous.V75R5_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v78_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V78),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_pooled_source_campaign_document_v78
            ),
            "frozen_before_any_registered_v78_source_outcome": True,
        },
        "failure_driven_successor_contract": {
            "v76_balanced_source_abstention_preserved": True,
            "v77_balanced_source_abstention_preserved": True,
            "blind_seed_substitution_used_as_fix": False,
            "multiple_fresh_source_occurrences_canonically_pooled": True,
            "source_only_gate_before_any_fresh_target": True,
        },
        "identity_contract": {
            "source_family": SOURCE_FAMILY,
            "source_pool_seeds": list(SOURCE_POOL_SEEDS),
            "source_seed_count": len(SOURCE_POOL_SEEDS),
            "source_seeds_unique": len(set(SOURCE_POOL_SEEDS))
            == len(SOURCE_POOL_SEEDS),
            "source_seeds_disjoint_from_v76_v77": min(SOURCE_POOL_SEEDS) > 779_000,
            "source_episode_index": SOURCE_EPISODE_INDEX,
            "fresh_target_identities_registered": [],
        },
        "construction_contract": {
            "source_layouts_projected_to_reference_canonical_coordinates": True,
            "anonymous_action_signatures_determine_pooled_keys": True,
            "all_member_rows_and_provenance_retained": True,
            "family_name_used_by_pooling_algorithm": False,
            "named_coordinate_used_by_pooling_algorithm": False,
            "target_outcome_used_by_pooling_or_acquisition": False,
            "same_v41_relation_covering_and_prequential_engine": True,
            "same_v42_joint_successor_version_space_compiler": True,
            "heldout_validation_required_before_model_compilation": True,
            "pooled_model_is_proposal_not_safety_authority": True,
        },
        "registered_gate": {
            "required_relation": (
                "TWO_FRESH_SOURCE_MEMBERS_AND_SOURCE_CERTIFICATE_DISCIPLINE_CLEAN_"
                "AND_POOLED_PROPOSAL_HELDOUT_VALIDATED_AND_POOLED_MODEL_COMPILED_"
                "AND_ZERO_FRESH_TARGET_OUTCOMES"
            ),
            "required_source_member_count": REQUIRED_SOURCE_MEMBER_COUNT,
            "target_execution_forbidden_in_this_slice": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "source_worker_count": SOURCE_WORKER_COUNT,
            "maximum_simultaneous_worker_count": SOURCE_WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_successor_support_states": 4_096,
            "maximum_relational_support_branch_evaluations_per_plan": 1_000_000,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "source_partial_labels_separate": True,
            "source_certificate_labels_separate": True,
            "pooled_query_groups_not_mislabeled_as_physical_samples": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "target_axes_zero_in_source_only_slice": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v78_source_outcome_observed": False,
            "fresh_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "three_family_transfer_verified": False,
            "sample_tax_reduction_verified": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_v78_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v78(
            domains.CONSTRUCTION_K7_POOLED_SOURCE_PREREGISTRATION_V78_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PooledSourcePreregistrationV78:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v78(
                domains.CONSTRUCTION_K7_POOLED_SOURCE_PREREGISTRATION_V78_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V78 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PooledSourcePreregistrationV78 | None = None


def freeze_pooled_source_preregistration_v78() -> PooledSourcePreregistrationV78:
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
        _fail("frozen V78 preregistration changed")
    _CACHE = PooledSourcePreregistrationV78(_ISSUER, raw, identity)
    return _CACHE


def verify_pooled_source_preregistration_v78(
    value: Any,
) -> PooledSourcePreregistrationV78:
    if type(value) is not PooledSourcePreregistrationV78:
        _fail("V78 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_pooled_source_preregistration_v78()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V78 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "SOURCE_FAMILY",
    "SOURCE_POOL_SEEDS",
    "campaign_config_v78",
    "freeze_pooled_source_preregistration_v78",
    "verify_pooled_source_preregistration_v78",
)
