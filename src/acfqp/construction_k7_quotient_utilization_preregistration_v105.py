"""Outcome-free preregistration for actual quotient ordering V105."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v105 as domains
from acfqp import construction_k7_hierarchical_utilization_preregistration_v104 as previous
from acfqp.construction_k7_hierarchical_utilization_campaign_v104 import (
    CAMPAIGN_ID as V104_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V104_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_hierarchical_utilization_independent_verifier_v104 import (
    EXPECTED_CANONICAL_SHA256 as V104_VERIFICATION_SHA256,
    VERIFICATION_ID as V104_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMITS = ("39740c5",)
PREREGISTRATION_ID = "9310bb2f3b96c5b0540ef39c92989f628f6b3248bc1644baddfa5bb20a583cbe"
EXPECTED_CANONICAL_BYTE_COUNT = 10_503
EXPECTED_CANONICAL_SHA256 = "5e254a990782fa33fa9df3e7f0091f07c19de34d50c822207f78600decc5c584"
TARGET_OCCURRENCES = (
    ("BALANCED_BATCH_REFINEMENT", 1_017_101),
    ("BALANCED_BATCH_REFINEMENT", 1_017_102),
    ("MAINTENANCE_CASCADE", 1_017_103),
    ("MAINTENANCE_CASCADE", 1_017_104),
)
TARGET_EPISODE_INDICES = (141, 142, 143)
TARGET_WORKER_COUNT = 2
REQUIRED_TARGET_OCCURRENCE_COUNT = 4
REQUIRED_TARGET_FAMILIES = (
    "BALANCED_BATCH_REFINEMENT",
    "MAINTENANCE_CASCADE",
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v105.py",
        1559,
        "ed6783d6c2d4c6e097a88f112a4b835de3f9dab5a3378d17fd42ad0828100d84",
    ),
    (
        "src/acfqp/generic_observation_quotient_graph_v105.py",
        9026,
        "0bda5824221b0c3869b2f050cd0293ffabd14caf870a857587f56ddfcdd42561",
    ),
    (
        "src/acfqp/generic_actual_quotient_execution_receipt_v105.py",
        5014,
        "a469d5f3484694005fa295a0d6610638b6a8f5cfba6e95f585bbaef441881faf",
    ),
    (
        "src/acfqp/generic_persistent_quotient_sequence_v105.py",
        11529,
        "de2b660d06692ff5c6923623c154112a53c035e393487c535ec571c2e531da92",
    ),
    (
        "src/acfqp/actual_quotient_utilization_campaign_core_v105.py",
        12973,
        "00bb20bf7bea502691c47be48973fa229e8bdb501d2d41f7e54297cc257a99ab",
    ),
    *previous.FROZEN_SOURCE_FACTS,
)


class ConstructionK7QuotientUtilizationPreregistrationV105Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QuotientUtilizationPreregistrationV105Error(message)


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


def campaign_config_v105() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v104())
    config.update(
        target_occurrences=[
            {"family": family, "seed": seed}
            for family, seed in TARGET_OCCURRENCES
        ],
        target_episode_indices=TARGET_EPISODE_INDICES,
        target_worker_count=TARGET_WORKER_COUNT,
        required_target_occurrence_count=REQUIRED_TARGET_OCCURRENCE_COUNT,
        required_target_families=REQUIRED_TARGET_FAMILIES,
    )
    return config


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.actual_quotient_utilization_preregistration.v105",
        "implementation_commits": list(IMPLEMENTATION_COMMITS),
        "frozen_predecessors": {
            "v104_campaign_id": V104_CAMPAIGN_ID,
            "v104_campaign_sha256": V104_CAMPAIGN_SHA256,
            "v104_verification_id": V104_VERIFICATION_ID,
            "v104_verification_sha256": V104_VERIFICATION_SHA256,
            "v104_registered_gate_passed": True,
            "v104_partial_world_model_primary_ordering_verified": True,
            "v104_actual_engine_ordering_not_yet_independently_distinguished": True,
            "source_library_artifact_id": previous.previous.previous.previous.previous.SOURCE_LIBRARY_ARTIFACT_ID,
            "v62_residual_library_id": previous.previous.previous.previous.previous.V62_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v105_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V105),
            "frozen_before_any_registered_v105_target_outcome": True,
        },
        "identity_contract": {
            "target_occurrences": campaign_config_v105()["target_occurrences"],
            "target_seeds_unique": len(
                {seed for _family, seed in TARGET_OCCURRENCES}
            )
            == len(TARGET_OCCURRENCES),
            "target_seeds_not_previously_exposed": True,
            "required_target_families": list(REQUIRED_TARGET_FAMILIES),
            "target_episode_indices": list(TARGET_EPISODE_INDICES),
        },
        "construction_contract": {
            "observation_derived_projected_graph_enters_real_engine_action_order": True,
            "per_action_receipt_binds_quotient_plan_and_exact_engine_choice": True,
            "quotient_projection_derived_from_anonymous_partial_candidate": True,
            "every_projected_observation_edge_checked_by_compiled_factor_program": True,
            "residual_coordinates_quotiented_out_not_imputed": True,
            "initial_graph_uses_only_preregistered_acquisition_prefix": True,
            "later_graph_updates_only_use_local_rows_acquired_after_certificate_failure": True,
            "every_occurrence_requires_actual_quotient_ordering_strict_majority": True,
            "every_occurrence_requires_chosen_action_match_strict_majority": True,
            "exact_overlay_exclusively_discharges_safety": True,
            "every_new_ground_query_must_follow_failed_certificate": True,
        },
        "registered_gate": {
            "required_target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "every_action_actual_ordering_receipt_replays_independently": True,
            "every_occurrence_actual_quotient_ordering_strict_majority": True,
            "every_occurrence_chosen_action_match_strict_majority": True,
            "every_occurrence_later_zero_label_quotient_reuse": True,
            "aggregate_quotient_labels_below_cold_direct": True,
            "strict_incompatible_schema_no_transfer_required": True,
            "all_unfavourable_results_retained": True,
        },
        "resource_schedule": {
            "target_worker_count": TARGET_WORKER_COUNT,
            "maximum_simultaneous_worker_count": TARGET_WORKER_COUNT,
            "target_occurrence_count": REQUIRED_TARGET_OCCURRENCE_COUNT,
            "query_episode_count": len(TARGET_EPISODE_INDICES),
            "maximum_incremental_certificate_labels_per_episode": 100_000,
        },
        "accounting_contract": {
            "offline_source_labels_not_recharged": True,
            "initial_acquisition_and_certificate_local_labels_separate": True,
            "quotient_and_cold_direct_target_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "no_scalar_cost_aggregation": True,
        },
        "claim_boundary": {
            "registered_v105_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "registered_multistep_execution_primarily_ordered_by_observation_derived_quotient": False,
            "global_lumpability_claimed": False,
            "complete_ground_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v105(
            domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_PREREGISTRATION_V105_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class QuotientUtilizationPreregistrationV105:
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
            or domains.extension_content_id_v105(
                domains.CONSTRUCTION_K7_QUOTIENT_UTILIZATION_PREREGISTRATION_V105_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V105 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


_CACHE: QuotientUtilizationPreregistrationV105 | None = None


def freeze_quotient_utilization_preregistration_v105() -> QuotientUtilizationPreregistrationV105:
    global _CACHE
    if _CACHE is None:
        if _source_facts() != _frozen_source_facts():
            _fail("V105 preregistered source closure changed")
        document = _document()
        raw = canonical_json_bytes(document)
        identity = document["preregistration_id"]
        if PREREGISTRATION_ID != "0" * 64 and (
            identity != PREREGISTRATION_ID
            or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
            or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
        ):
            _fail("V105 frozen preregistration changed")
        _CACHE = QuotientUtilizationPreregistrationV105(_ISSUER, raw, identity)
    return _CACHE


def verify_quotient_utilization_preregistration_v105(
    value: Any,
) -> QuotientUtilizationPreregistrationV105:
    if type(value) is not QuotientUtilizationPreregistrationV105:
        _fail("V105 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_quotient_utilization_preregistration_v105()
    if value is not expected:
        _fail("V105 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "campaign_config_v105",
    "freeze_quotient_utilization_preregistration_v105",
    "verify_quotient_utilization_preregistration_v105",
)
