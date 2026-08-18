"""Outcome-free registration for the fresh V58r1 true-bit successor."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v58r1 as domains
from acfqp import construction_k7_universal_mixture_preregistration_v58 as previous
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    bit_codelength_universal_stop_update_v14,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    partial_factor_bit_codelength_stop_update_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.true_bit_partial_three_domain_campaign_core_v58r1 import (
    build_true_bit_partial_three_domain_campaign_document_v58r1,
)


SCHEMA_VERSION = "58.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.231"
PROFILE_KEY = "construction_k7_true_bit_partial_three_domain_v58r1"
IMPLEMENTATION_COMMIT = "36c32fc"
PREREGISTRATION_ID = "9677242df0fb8c27190b00a5190e38b4cb33efd2541c8caafb65d10167368579"
EXPECTED_CANONICAL_BYTE_COUNT = 11_283
EXPECTED_CANONICAL_SHA256 = "8b0dde5b6ec31adcfd13e6759350f699382069731146a404602dd8c5eb8e16fa"
FAILED_V58_PREDECESSOR_ID = (
    "f90df0f0035140179b33e0b3a9d438dd232faf458b4efbd0be6d9f6a785d6ac2"
)

BALANCED_TARGET_SEEDS = tuple(range(584_101, 584_113))
COUPLED_TARGET_SEEDS = tuple(range(585_101, 585_113))
MAINTENANCE_TARGET_SEEDS = tuple(range(586_101, 586_113))
DEVELOPMENT_SEEDS = tuple(range(590_101, 590_105)) + tuple(
    range(590_201, 590_205)
) + tuple(range(590_301, 590_305))
WORKER_COUNT = 4
PLANNING_SEED_COUNT_PER_FAMILY = 1
MAXIMUM_ACQUISITION_LABELS = 160

SUCCESSOR_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_PREREGISTRATION_V58R1_DOMAIN,
    "acquisition": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_ACQUISITION_V58R1_DOMAIN,
    "certificate": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CERTIFICATE_V58R1_DOMAIN,
    "distinction": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_DISTINCTION_V58R1_DOMAIN,
    "episode": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_EPISODE_V58R1_DOMAIN,
    "sample_tax": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_SAMPLE_TAX_V58R1_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_CAMPAIGN_V58R1_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_TRUE_BIT_PARTIAL_VERIFICATION_V58R1_DOMAIN,
}

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v58r1.py",
    "src/acfqp/generic_bit_codelength_universal_synthesizer_v14.py",
    "src/acfqp/generic_partial_factor_proposal_v15.py",
    "src/acfqp/true_bit_partial_three_domain_campaign_core_v58r1.py",
    *previous.BOUND_SOURCE_PATHS,
)


class ConstructionK7TrueBitPartialPreregistrationV58R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TrueBitPartialPreregistrationV58R1Error(message)


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


def campaign_config_v58r1() -> dict[str, Any]:
    config = previous.campaign_config_v58()
    config["successor_domains"] = dict(SUCCESSOR_DOMAINS)
    config["families"]["BALANCED_BATCH_REFINEMENT"].update(
        target_seeds=BALANCED_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=MAXIMUM_ACQUISITION_LABELS,
    )
    config["families"]["COUPLED_EXCHANGE"].update(
        target_seeds=COUPLED_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=MAXIMUM_ACQUISITION_LABELS,
    )
    config["families"]["MAINTENANCE_CASCADE"].update(
        target_seeds=MAINTENANCE_TARGET_SEEDS,
        planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
        maximum_acquisition_labels=MAXIMUM_ACQUISITION_LABELS,
    )
    config["worker_count"] = WORKER_COUNT
    config["planning_seed_count_per_family"] = PLANNING_SEED_COUNT_PER_FAMILY
    config["failed_v58_predecessor_id"] = FAILED_V58_PREDECESSOR_ID
    for stale in (
        "factor_signature_credit_units",
        "invalidated_candidate_penalty_units",
        "predictive_evidence_credit_units_per_bit",
    ):
        config.pop(stale, None)
    return config


def _document() -> dict[str, Any]:
    registered = set(
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.true_bit_partial_preregistration.v58r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "failed_v58_predecessor_id": FAILED_V58_PREDECESSOR_ID,
            "v57_campaign_id": previous.V57_CAMPAIGN_ID,
            "v57_campaign_sha256": previous.V57_CAMPAIGN_SHA256,
            "v57_verification_id": previous.V57_VERIFICATION_ID,
            "v57_verification_sha256": previous.V57_VERIFICATION_SHA256,
            "v51_factor_library_id": previous.V51_FACTOR_LIBRARY_ID,
            "factor_library_labels": previous.FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "successor_domains": dict(SUCCESSOR_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "complete_stop_callable": _callable_fact(
                bit_codelength_universal_stop_update_v14
            ),
            "partial_stop_callable": _callable_fact(
                partial_factor_bit_codelength_stop_update_v15
            ),
            "campaign_builder_callable": _callable_fact(
                build_true_bit_partial_three_domain_campaign_document_v58r1
            ),
            "frozen_before_any_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": (
                set(DEVELOPMENT_SEEDS).isdisjoint(registered)
            ),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS),
                "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            },
            "COUPLED_EXCHANGE": {
                "target_seeds": list(COUPLED_TARGET_SEEDS),
                "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            },
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS),
                "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            },
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "matched_acquisition_contract": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_witness_blind_stream_and_query_order": True,
            "same_true_bit_two_part_code": True,
            "same_parameter_free_universal_mixture_eprocess": True,
            "only_switched_variable": "PARTIAL_FACTOR_PROPOSAL_LIBRARY_AVAILABLE",
            "partial_arm_unknown_residual_outputs_claimed": False,
            "strict_arm_complete_program_required": True,
            "partial_arm_requires_observed_accepting_projection_for_planning": True,
            "fixed_minimum_label_floor": None,
            "fixed_confirmation_block": None,
            "reachable_frontier_exhaustion_stop_available": False,
            "heuristic_mdl_information_units_available": False,
            "predictive_evidence_to_mdl_credit_available": False,
            "global_alpha": {"numerator": 1, "denominator": 20},
            "candidate_epoch_weight": "1/((j+1)*(j+2))",
        },
        "planning_and_recovery": {
            "planning_seed_count_per_family": PLANNING_SEED_COUNT_PER_FAMILY,
            "partial_model_requires_all_branch_residual_safety_certificate": True,
            "unknown_residual_causes_certificate_failure_before_execution": True,
            "complete_residual_recovery_only_after_failed_certificate": True,
            "receding_abstract_planning_after_recovery": True,
            "matched_direct_ground_baseline": True,
            "query_locality_minimality_claimed": False,
            "next_required_improvement": (
                "REPLACE_STREAM_PREFIX_RESIDUAL_RECOVERY_WITH_CANDIDATE_DISAGREEMENT_LOCAL_QUERIES"
            ),
        },
        "sample_tax_contract": {
            "registered_occurrence_count": len(registered),
            "positive_acquisition_reduction_required_in_each_family": True,
            "positive_online_reduction_including_recovery_required": True,
            "positive_lifetime_reduction_after_offline_tax_required": True,
            "sample_labels_execution_steps_derivation_planning_and_certificate_compute_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "family_aggregate_reduction_observed": True,
            "planning_safety_failure_observed_and_recovery_added": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "v58r1_campaign_preregistered": True,
            "registered_outcome_observed": False,
            "complete_world_model_from_partial_proposal_claimed": False,
            "minimal_local_recovery_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "factor_library": previous.FACTOR_LIBRARY,
        "future_content_domains": dict(SUCCESSOR_DOMAINS),
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v58r1(
            SUCCESSOR_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TrueBitPartialPreregistrationV58R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V58r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v58r1(
                SUCCESSOR_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V58r1 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TrueBitPartialPreregistrationV58R1 | None = None


def freeze_true_bit_partial_preregistration_v58r1() -> TrueBitPartialPreregistrationV58R1:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V58r1 preregistration changed")
    if _CACHE is None:
        _CACHE = TrueBitPartialPreregistrationV58R1(_ISSUER, raw, identity)
    return _CACHE


def verify_true_bit_partial_preregistration_v58r1(
    value: Any,
) -> TrueBitPartialPreregistrationV58R1:
    if type(value) is not TrueBitPartialPreregistrationV58R1:
        _fail("V58r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_true_bit_partial_preregistration_v58r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V58r1 preregistration does not match frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "SUCCESSOR_DOMAINS",
    "TrueBitPartialPreregistrationV58R1",
    "campaign_config_v58r1",
    "freeze_true_bit_partial_preregistration_v58r1",
    "verify_true_bit_partial_preregistration_v58r1",
)
