"""Outcome-free preregistration for fresh V65 online residual planning."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v65 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as previous
from acfqp.online_residual_planning_campaign_core_v65 import (
    build_online_residual_planning_campaign_document_v65,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "ff3d07a"
PREREGISTRATION_ID = "a50a86b6f05d4ec7f027f859936c4921c9a1dce58faf7034bcc6f1c39804f504"
EXPECTED_CANONICAL_BYTE_COUNT = 4_694
EXPECTED_CANONICAL_SHA256 = "a33aedc15b7e9ec64b12ec52d0743b7f72c7a82c06578ddb69b0e0f902e0d752"
V62_LIBRARY_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
V64_CAMPAIGN_ID = "b995c21c6e9b6f558d61cac084f9f8dd03eb694ffc0d026ace224e0abb175647"
V64_VERIFICATION_ID = "fe6b372c86255a7150b5321a394203607e78e1f333d238786a85f6e3b344a2bf"
BALANCED_TARGET_SEEDS = tuple(range(661_101, 661_107))
COUPLED_TARGET_SEEDS = tuple(range(662_101, 662_107))
MAINTENANCE_TARGET_SEEDS = tuple(range(663_101, 663_107))
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 18
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v65.py",
    "src/acfqp/online_residual_planning_campaign_core_v65.py",
    "src/acfqp/generic_online_residual_guided_planner_v21.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
    "src/acfqp/generic_total_adaptive_residual_acquisition_v20.py",
)


class ConstructionK7OnlineResidualPlanningPreregistrationV65Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OnlineResidualPlanningPreregistrationV65Error(message)


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


def campaign_config_v65() -> dict[str, Any]:
    config = previous.campaign_config_v59()
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
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
        residual_confidence_denominator=64,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.online_residual_planning_preregistration.v65",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v64_campaign_id": V64_CAMPAIGN_ID,
            "v64_campaign_sha256": "deb8260b7deb57a168309579e79b23942775f667523f025d44ea7f91b8c4e195",
            "v64_verification_id": V64_VERIFICATION_ID,
            "v64_verification_sha256": "cfb08891a206fe63340c36d6e4723666b1b3a059d53e122cade9f4bbe25616aa",
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v65_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V65),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_online_residual_planning_campaign_document_v65
            ),
            "frozen_before_any_registered_v65_outcome": True,
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
            and min(all_seeds) > 660_000,
        },
        "matched_online_contract": {
            "same_environment_seed_episode_partial_candidate_and_observations": True,
            "same_residual_synthesizer_totalizer_and_guidance_rule": True,
            "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
            "action_trajectories_required_to_match": False,
            "registered_relation": "PRIOR_CERTIFICATE_LOCAL_LABELS_LE_STRICT_CERTIFICATE_LOCAL_LABELS",
            "positive_reduction_required": False,
            "family_specific_noninferiority_required": False,
            "all_occurrences_and_family_projections_retained": True,
        },
        "safety_contract": {
            "residual_proposal_may_only_order_abstract_actions": True,
            "only_action_conditioned_zero_excess_proposals_may_order_actions": True,
            "previously_proved_delta_signatures_may_transfer_for_ordering": True,
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "residual_proposal_safety_authority": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
        },
        "accounting_contract": {
            "offline_labels_separate": True,
            "common_partial_labels_separate": True,
            "prior_and_strict_certificate_local_labels_separate": True,
            "legality_and_transition_labels_separate": True,
            "execution_steps_separate": True,
            "partial_planning_and_residual_synthesis_compute_separate": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "producer_free_verification_present": False,
            "complete_residual_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v65(
            domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_PREREGISTRATION_V65_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OnlineResidualPlanningPreregistrationV65:
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
            or domains.extension_content_id_v65(
                domains.CONSTRUCTION_K7_ONLINE_RESIDUAL_PLANNING_PREREGISTRATION_V65_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V65 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: OnlineResidualPlanningPreregistrationV65 | None = None


def freeze_online_residual_planning_preregistration_v65() -> OnlineResidualPlanningPreregistrationV65:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V65 preregistration changed")
    if _CACHE is None:
        _CACHE = OnlineResidualPlanningPreregistrationV65(_ISSUER, raw, identity)
    return _CACHE


def verify_online_residual_planning_preregistration_v65(
    value: Any,
) -> OnlineResidualPlanningPreregistrationV65:
    if type(value) is not OnlineResidualPlanningPreregistrationV65:
        _fail("V65 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_online_residual_planning_preregistration_v65()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V65 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V64_CAMPAIGN_ID",
    "V64_VERIFICATION_ID",
    "campaign_config_v65",
    "freeze_online_residual_planning_preregistration_v65",
    "verify_online_residual_planning_preregistration_v65",
)
