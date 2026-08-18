"""Outcome-free preregistration for the V61 persistent-overlay campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v61 as domains
from acfqp import construction_k7_query_local_preregistration_v60 as previous
from acfqp.generic_persistent_certificate_overlay_planner_v17 import (
    run_persistent_certificate_overlay_episodes_v17,
)
from acfqp.persistent_overlay_campaign_core_v61 import (
    build_persistent_overlay_campaign_document_v61,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "80fcf54"
PREREGISTRATION_ID = "b0d27cf87f48e5d2439e14279d8258fc52ca5cfb37c0cc1ed5f39fd4e103766c"
EXPECTED_CANONICAL_BYTE_COUNT = 10_882
EXPECTED_CANONICAL_SHA256 = "f0f2896e00ab723f6096d5f5008818f2335b064c0d771a0603b7d244411ecec2"
V60_CAMPAIGN_ID = "abb8c1dab6a8dd1599617dfd9927f741259e93102b06bdb650c849103aa5ff8c"
V60_VERIFICATION_ID = "d3a425b2f280ecd619a8aa8be2d41128ccc50acc7bc3c7038bd796645077e5c2"
BALANCED_TARGET_SEEDS = tuple(range(601_101, 601_105))
COUPLED_TARGET_SEEDS = tuple(range(602_101, 602_105))
MAINTENANCE_TARGET_SEEDS = tuple(range(603_101, 603_105))
EPISODE_INDICES = (0, 1, 2)
WORKER_COUNT = 4

V61_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_PREREGISTRATION_V61_DOMAIN,
    "raw_evidence": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RAW_EVIDENCE_V61_DOMAIN,
    "acquisition": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_ACQUISITION_V61_DOMAIN,
    "certificate": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CERTIFICATE_V61_DOMAIN,
    "distinction": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_DISTINCTION_V61_DOMAIN,
    "episode": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_EPISODE_V61_DOMAIN,
    "run": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_RUN_V61_DOMAIN,
    "sample_tax": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_SAMPLE_TAX_V61_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_CAMPAIGN_V61_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_PERSISTENT_OVERLAY_VERIFICATION_V61_DOMAIN,
}
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v61.py",
    "src/acfqp/generic_persistent_certificate_overlay_planner_v17.py",
    "src/acfqp/persistent_overlay_campaign_core_v61.py",
    *previous.BOUND_SOURCE_PATHS,
)


class ConstructionK7PersistentOverlayPreregistrationV61Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7PersistentOverlayPreregistrationV61Error(message)


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


def campaign_config_v61() -> dict[str, Any]:
    config = previous.campaign_config_v60()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", BALANCED_TARGET_SEEDS),
        ("COUPLED_EXCHANGE", COUPLED_TARGET_SEEDS),
        ("MAINTENANCE_CASCADE", MAINTENANCE_TARGET_SEEDS),
    ):
        config["families"][family]["target_seeds"] = seeds
    config["worker_count"] = WORKER_COUNT
    config["episode_indices"] = EPISODE_INDICES
    config["v61_domains"] = dict(V61_DOMAINS)
    config["v60_campaign_id"] = V60_CAMPAIGN_ID
    config["v60_verification_id"] = V60_VERIFICATION_ID
    return config


def _document() -> dict[str, Any]:
    registered = set(
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.persistent_overlay_preregistration.v61",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v60_campaign_id": V60_CAMPAIGN_ID,
            "v60_campaign_sha256": "820476b0d7a98ea5ea24383996a7b56d3202afdda265ff9f03779201c99ea69c",
            "v60_verification_id": V60_VERIFICATION_ID,
            "v60_verification_sha256": "1baad5793cc06d8573cd85b9e7ddcc34e848902d253641ad4f0d2de41f4ccf54",
            "factor_library_id": previous.previous.previous.previous.V51_FACTOR_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v61_domains": dict(V61_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "persistent_planner_callable": _callable_fact(
                run_persistent_certificate_overlay_episodes_v17
            ),
            "campaign_builder_callable": _callable_fact(
                build_persistent_overlay_campaign_document_v61
            ),
            "frozen_before_any_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": all(
                seed < 600_000 for seed in previous.DEVELOPMENT_SEEDS
            )
            and min(registered) > 600_000,
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {"target_seeds": list(BALANCED_TARGET_SEEDS)},
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS)},
            "MAINTENANCE_CASCADE": {"target_seeds": list(MAINTENANCE_TARGET_SEEDS)},
            "generation_witness_available_to_constructor": False,
        },
        "matched_overlay_contract": {
            "episode_indices": list(EPISODE_INDICES),
            "same_partial_candidate_same_initial_state_same_outcome_tapes": True,
            "persistent_arm_carries_occurrence_local_overlay_forward": True,
            "cold_arm_restarts_with_empty_overlay_each_episode": True,
            "only_switched_variable": "OCCURRENCE_LOCAL_PROOF_OVERLAY_PERSISTENCE",
            "positive_label_reduction_required_in_every_family": True,
            "later_persistent_episode_ground_query_count_required": 0,
            "cross_occurrence_ground_fact_reuse_allowed": False,
        },
        "evidence_contract": {
            "all_acquisition_and_local_transition_rows_embedded": True,
            "producer_free_raw_prefix_factor_and_overlay_replay_required": True,
            "certificate_must_precede_every_ground_query": True,
            "sample_execution_and_planning_compute_axes_separate": True,
        },
        "stopping_contract": {
            "reachable_frontier_exhaustion_stop_available": False,
            "fixed_label_floor": None,
            "fixed_confirmation_block": None,
            "candidate_disagreement_true_bit_and_calibrated_confidence_only": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "complete_residual_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(V61_DOMAINS),
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v61(
            V61_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PersistentOverlayPreregistrationV61:
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
            or domains.extension_content_id_v61(V61_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V61 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: PersistentOverlayPreregistrationV61 | None = None


def freeze_persistent_overlay_preregistration_v61() -> PersistentOverlayPreregistrationV61:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V61 preregistration changed")
    if _CACHE is None:
        _CACHE = PersistentOverlayPreregistrationV61(_ISSUER, raw, identity)
    return _CACHE


def verify_persistent_overlay_preregistration_v61(
    value: Any,
) -> PersistentOverlayPreregistrationV61:
    if type(value) is not PersistentOverlayPreregistrationV61:
        _fail("V61 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_persistent_overlay_preregistration_v61()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V61 preregistration does not match frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V61_DOMAINS",
    "campaign_config_v61",
    "freeze_persistent_overlay_preregistration_v61",
    "verify_persistent_overlay_preregistration_v61",
)
