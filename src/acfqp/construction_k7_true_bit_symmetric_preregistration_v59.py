"""Outcome-free V59 registration after the frozen V58r1 prefix-audit failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v59 as domains
from acfqp import construction_k7_true_bit_partial_preregistration_v58r1 as previous
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import bit_codelength_universal_stop_update_v14
from acfqp.generic_partial_factor_proposal_v15 import partial_factor_bit_codelength_stop_update_v15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.true_bit_symmetric_three_domain_campaign_core_v59 import (
    build_true_bit_symmetric_three_domain_campaign_document_v59,
)


SCHEMA_VERSION = "59.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.232"
PROFILE_KEY = "construction_k7_true_bit_symmetric_three_domain_v59"
IMPLEMENTATION_COMMIT = "64d0c0f"
PREREGISTRATION_ID = "99554f27032332e126e39294adcc36a601231a91d13fc5123f98fcb1557f7ff2"
EXPECTED_CANONICAL_BYTE_COUNT = 11_323
EXPECTED_CANONICAL_SHA256 = "e4c3746d2536550778388d8bd13c2ad1cb76ffaedbbf4e7683cc2a57aeb42fe6"
FAILED_V58_ID = previous.FAILED_V58_PREDECESSOR_ID
FAILED_V58R1_ID = "62786c619f6ea7354929c23e25fbd5ea4c9e24fee9cedb5917c0edb207186cf6"

BALANCED_TARGET_SEEDS = tuple(range(587_101, 587_113))
COUPLED_TARGET_SEEDS = tuple(range(588_101, 588_113))
MAINTENANCE_TARGET_SEEDS = tuple(range(589_101, 589_113))
DEVELOPMENT_SEEDS = previous.DEVELOPMENT_SEEDS + (589_931,)
WORKER_COUNT = 4
PLANNING_SEED_COUNT_PER_FAMILY = 1
MAXIMUM_ACQUISITION_LABELS = 160

SUCCESSOR_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_PREREGISTRATION_V59_DOMAIN,
    "acquisition": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_ACQUISITION_V59_DOMAIN,
    "certificate": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CERTIFICATE_V59_DOMAIN,
    "distinction": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_DISTINCTION_V59_DOMAIN,
    "episode": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_EPISODE_V59_DOMAIN,
    "sample_tax": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_SAMPLE_TAX_V59_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_CAMPAIGN_V59_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_TRUE_BIT_SYMMETRIC_VERIFICATION_V59_DOMAIN,
}

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v59.py",
    "src/acfqp/true_bit_symmetric_three_domain_campaign_core_v59.py",
    "src/acfqp/generic_bit_codelength_universal_synthesizer_v14.py",
    "src/acfqp/generic_partial_factor_proposal_v15.py",
    *previous.BOUND_SOURCE_PATHS,
)


class ConstructionK7TrueBitSymmetricPreregistrationV59Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TrueBitSymmetricPreregistrationV59Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append({"relative_path": relative, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return result


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def campaign_config_v59() -> dict[str, Any]:
    config = previous.campaign_config_v58r1()
    config["successor_domains"] = dict(SUCCESSOR_DOMAINS)
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", BALANCED_TARGET_SEEDS),
        ("COUPLED_EXCHANGE", COUPLED_TARGET_SEEDS),
        ("MAINTENANCE_CASCADE", MAINTENANCE_TARGET_SEEDS),
    ):
        config["families"][family].update(
            target_seeds=seeds,
            planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY,
            maximum_acquisition_labels=MAXIMUM_ACQUISITION_LABELS,
        )
    config["worker_count"] = WORKER_COUNT
    config["planning_seed_count_per_family"] = PLANNING_SEED_COUNT_PER_FAMILY
    config["failed_v58_id"] = FAILED_V58_ID
    config["failed_v58r1_id"] = FAILED_V58R1_ID
    return config


def _document() -> dict[str, Any]:
    registered = set(BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS)
    payload = {
        "schema": "acfqp.true_bit_symmetric_preregistration.v59",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "failed_v58_id": FAILED_V58_ID,
            "failed_v58r1_id": FAILED_V58R1_ID,
            "v57_campaign_id": previous.previous.V57_CAMPAIGN_ID,
            "v57_verification_id": previous.previous.V57_VERIFICATION_ID,
            "v51_factor_library_id": previous.previous.V51_FACTOR_LIBRARY_ID,
            "factor_library_labels": previous.previous.FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "successor_domains": dict(SUCCESSOR_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "complete_stop_callable": _callable_fact(bit_codelength_universal_stop_update_v14),
            "partial_stop_callable": _callable_fact(partial_factor_bit_codelength_stop_update_v15),
            "campaign_builder_callable": _callable_fact(build_true_bit_symmetric_three_domain_campaign_document_v59),
            "frozen_before_any_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(DEVELOPMENT_SEEDS).isdisjoint(registered),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {"target_seeds": list(BALANCED_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "MAINTENANCE_CASCADE": {"target_seeds": list(MAINTENANCE_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "matched_acquisition_contract": {
            "same_witness_blind_stream_and_query_order": True,
            "same_true_bit_two_part_code": True,
            "same_parameter_free_universal_mixture_eprocess": True,
            "only_switched_variable": "PARTIAL_FACTOR_PROPOSAL_LIBRARY_AVAILABLE",
            "symmetric_minimum_common_prefix_post_audit": True,
            "either_arm_may_stop_first": True,
            "fixed_minimum_label_floor": None,
            "fixed_confirmation_block": None,
            "reachable_frontier_exhaustion_stop_available": False,
            "heuristic_mdl_information_units_available": False,
            "predictive_evidence_to_mdl_credit_available": False,
        },
        "planning_and_recovery": {
            "planning_seed_count_per_family": PLANNING_SEED_COUNT_PER_FAMILY,
            "unknown_residual_causes_certificate_failure_before_execution": True,
            "complete_residual_recovery_only_after_failed_certificate": True,
            "receding_abstract_planning_after_recovery": True,
            "matched_direct_ground_baseline": True,
            "query_locality_minimality_claimed": False,
            "next_required_improvement": "CANDIDATE_DISAGREEMENT_LOCAL_RESIDUAL_QUERIES",
        },
        "sample_tax_contract": {
            "registered_occurrence_count": len(registered),
            "positive_acquisition_reduction_required_in_each_family": True,
            "positive_online_reduction_including_recovery_required": True,
            "positive_lifetime_reduction_after_offline_tax_required": True,
            "all_accounting_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "both_arm_stop_orders_observed": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "minimal_local_recovery_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "factor_library": previous.previous.FACTOR_LIBRARY,
        "future_content_domains": dict(SUCCESSOR_DOMAINS),
        "fresh_registered_outcome_execution_performed": False,
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v59(SUCCESSOR_DOMAINS["preregistration"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TrueBitSymmetricPreregistrationV59:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v59(SUCCESSOR_DOMAINS["preregistration"], payload) != self.preregistration_id
        ):
            _fail("V59 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: TrueBitSymmetricPreregistrationV59 | None = None


def freeze_true_bit_symmetric_preregistration_v59() -> TrueBitSymmetricPreregistrationV59:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V59 preregistration changed")
    if _CACHE is None:
        _CACHE = TrueBitSymmetricPreregistrationV59(_ISSUER, raw, identity)
    return _CACHE


def verify_true_bit_symmetric_preregistration_v59(value: Any) -> TrueBitSymmetricPreregistrationV59:
    if type(value) is not TrueBitSymmetricPreregistrationV59:
        _fail("V59 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_true_bit_symmetric_preregistration_v59()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V59 preregistration does not match frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "SUCCESSOR_DOMAINS",
    "campaign_config_v59",
    "freeze_true_bit_symmetric_preregistration_v59",
    "verify_true_bit_symmetric_preregistration_v59",
)
