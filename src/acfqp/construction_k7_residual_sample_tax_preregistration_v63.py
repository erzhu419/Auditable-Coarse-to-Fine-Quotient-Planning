"""Outcome-free preregistration for the fresh V63 residual sample-tax campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as previous
from acfqp.generic_adaptive_residual_factor_acquisition_v19 import (
    acquire_adaptive_residual_factor_v19,
    replay_adaptive_residual_factor_v19,
)
from acfqp.residual_factor_sample_tax_campaign_core_v63 import (
    build_residual_factor_sample_tax_campaign_document_v63,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "f02fb0a"
PREREGISTRATION_ID = "be0bbfd3c61bf14de72c1ed888be4444deb0f30fac75c8e620b996e6dfef4bab"
EXPECTED_CANONICAL_BYTE_COUNT = 5_613
EXPECTED_CANONICAL_SHA256 = "843fd6214965cb93dba0e95f90fbad181a5165c07a7fe9fe3ad754ea0ede3448"
V62_LIBRARY_ARTIFACT_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
V62_VERIFICATION_ID = "981c040ff7e3a88e75ec8189d09d9c1511b6efd0b9358f7d825b38c978b316d2"
BALANCED_TARGET_SEEDS = tuple(range(631_101, 631_105))
COUPLED_TARGET_SEEDS = tuple(range(632_101, 632_105))
MAINTENANCE_TARGET_SEEDS = tuple(range(633_101, 633_105))
WORKER_COUNT = 4
RESIDUAL_CONFIDENCE_DENOMINATOR = 64
MAXIMUM_PARTIAL_ABSTRACT_DEPTH = 12
MAXIMUM_PARTIAL_EXECUTION_STEPS = 96
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v63.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
    "src/acfqp/residual_factor_sample_tax_campaign_core_v63.py",
)
V63_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_PREREGISTRATION_V63_DOMAIN,
    "raw_query_pool": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_RAW_QUERY_POOL_V63_DOMAIN,
    "acquisition": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_ACQUISITION_V63_DOMAIN,
    "safety_episode": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63_DOMAIN,
    "summary": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_SUMMARY_V63_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_RESIDUAL_SAMPLE_TAX_VERIFICATION_V63_DOMAIN,
}


class ConstructionK7ResidualSampleTaxPreregistrationV63Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualSampleTaxPreregistrationV63Error(message)


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


def campaign_config_v63() -> dict[str, Any]:
    config = previous.campaign_config_v59()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", BALANCED_TARGET_SEEDS),
        ("COUPLED_EXCHANGE", COUPLED_TARGET_SEEDS),
        ("MAINTENANCE_CASCADE", MAINTENANCE_TARGET_SEEDS),
    ):
        config["families"][family]["target_seeds"] = seeds
    config["worker_count"] = WORKER_COUNT
    config["maximum_partial_abstract_depth"] = MAXIMUM_PARTIAL_ABSTRACT_DEPTH
    config["maximum_partial_execution_steps"] = MAXIMUM_PARTIAL_EXECUTION_STEPS
    config["residual_confidence_denominator"] = RESIDUAL_CONFIDENCE_DENOMINATOR
    config["v63_domains"] = dict(V63_DOMAINS)
    return config


def _document() -> dict[str, Any]:
    registered = set(
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.residual_sample_tax_preregistration.v63",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_library_artifact_id": V62_LIBRARY_ARTIFACT_ID,
            "v62_library_sha256": "a90880c455caa6f585bbadf67b84c7effb9e207c98296cd8e46b2a0555b9b1dc",
            "v62_verification_id": V62_VERIFICATION_ID,
            "v62_verification_sha256": "f943ed14b0d1f6afed971635e5c7ba8c44df18cb34b5347c59e05655a70e7869",
            "factor_library_id": previous.previous.previous.V51_FACTOR_LIBRARY_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v63_domains": dict(V63_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "adaptive_acquisition_callable": _callable_fact(
                acquire_adaptive_residual_factor_v19
            ),
            "adaptive_replay_callable": _callable_fact(
                replay_adaptive_residual_factor_v19
            ),
            "campaign_builder_callable": _callable_fact(
                build_residual_factor_sample_tax_campaign_document_v63
            ),
            "frozen_before_any_registered_v63_outcome": True,
            "development_identities_disjoint_from_registered_identities": min(
                registered
            )
            > 600_000,
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS)
            },
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS)},
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS)
            },
            "generation_witness_available_to_residual_acquisition": False,
        },
        "matched_ablation_contract": {
            "same_full_generic_candidate_grammar": True,
            "same_query_selection_synthesizer_and_stop_rule": True,
            "same_confidence_denominator": RESIDUAL_CONFIDENCE_DENOMINATOR,
            "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
            "prior_does_not_filter_strict_candidates": True,
            "positive_aggregate_label_reduction_required": True,
            "positive_label_reduction_required_in_every_family_projection": True,
            "positive_label_reduction_required_in_every_occurrence": False,
            "all_zero_or_negative_occurrence_results_retained": True,
        },
        "query_and_safety_contract": {
            "raw_query_pool_contexts_materialized_before_matched_label_selection": True,
            "query_selection_may_read_state_and_action_context_only": True,
            "query_selection_may_read_unselected_successor_outcome": False,
            "reachable_frontier_exhaustion_stop_available": False,
            "fixed_label_floor": None,
            "fixed_confirmation_block": None,
            "stopping_inputs": [
                "CANDIDATE_DISAGREEMENT",
                "MDL_DESCRIPTION_LENGTH",
                "CALIBRATED_TRUE_BIT_CONFIDENCE",
            ],
            "statistical_tail_errors_measured_not_suppressed": True,
            "tail_error_can_only_trigger_certificate_local_ground_recovery": True,
            "proposal_can_never_discharge_safety_certificate": True,
        },
        "accounting_contract": {
            "offline_development_labels_separate": True,
            "common_partial_acquisition_labels_separate": True,
            "prior_and_strict_residual_target_labels_separate": True,
            "full_safety_local_labels_separate": True,
            "execution_steps_separate": True,
            "planning_and_candidate_evaluation_compute_separate": True,
            "offline_tax_amortization_within_registered_occurrences_required": False,
            "diagnostic_break_even_projection_allowed_but_not_official": True,
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
        "future_content_domains": dict(V63_DOMAINS),
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v63(
            V63_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ResidualSampleTaxPreregistrationV63:
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
            or domains.extension_content_id_v63(V63_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V63 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ResidualSampleTaxPreregistrationV63 | None = None


def freeze_residual_sample_tax_preregistration_v63() -> ResidualSampleTaxPreregistrationV63:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V63 preregistration changed")
    if _CACHE is None:
        _CACHE = ResidualSampleTaxPreregistrationV63(_ISSUER, raw, identity)
    return _CACHE


def verify_residual_sample_tax_preregistration_v63(
    value: Any,
) -> ResidualSampleTaxPreregistrationV63:
    if type(value) is not ResidualSampleTaxPreregistrationV63:
        _fail("V63 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_residual_sample_tax_preregistration_v63()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V63 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V63_DOMAINS",
    "campaign_config_v63",
    "freeze_residual_sample_tax_preregistration_v63",
    "verify_residual_sample_tax_preregistration_v63",
)
