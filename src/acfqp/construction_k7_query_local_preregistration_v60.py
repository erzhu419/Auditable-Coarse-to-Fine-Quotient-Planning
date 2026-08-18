"""Outcome-free registration for V60 query-local residual recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v60 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as previous
from acfqp.generic_certificate_guided_partial_planner_v16 import run_certificate_guided_partial_episode_v16
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.query_local_raw_evidence_campaign_core_v60 import build_query_local_raw_evidence_campaign_document_v60


IMPLEMENTATION_COMMIT = "f99257e"
PREREGISTRATION_ID = "3e5236983d198c9b491632363836c5088eebd6232bc10a5da94cbac6eaaff834"
EXPECTED_CANONICAL_BYTE_COUNT = 10_890
EXPECTED_CANONICAL_SHA256 = "5457a7463ccd7c66b4dc3deacf74b7334c0a94e8aa9f3cdbb7181a410b113a1f"
V59_CAMPAIGN_ID = "60ecb969f8b2b6cd7aa000d7306c213ab194293fc76a01190c73bae22e8b8d18"
V59_VERIFICATION_ID = "b9b783080837cf9ac2641bf73036363bfe5813f8be1893b114c8fe7ec0f95a8f"
BALANCED_TARGET_SEEDS = tuple(range(591_101, 591_113))
COUPLED_TARGET_SEEDS = tuple(range(592_101, 592_113))
MAINTENANCE_TARGET_SEEDS = tuple(range(593_101, 593_113))
DEVELOPMENT_SEEDS = previous.DEVELOPMENT_SEEDS
WORKER_COUNT = 4
PLANNING_SEED_COUNT_PER_FAMILY = 1
MAXIMUM_ACQUISITION_LABELS = 160
MAXIMUM_PARTIAL_ABSTRACT_DEPTH = 12
MAXIMUM_PARTIAL_EXECUTION_STEPS = 96

V60_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_QUERY_LOCAL_PREREGISTRATION_V60_DOMAIN,
    "acquisition": domains.CONSTRUCTION_K7_QUERY_LOCAL_ACQUISITION_V60_DOMAIN,
    "raw_evidence": domains.CONSTRUCTION_K7_QUERY_LOCAL_RAW_EVIDENCE_V60_DOMAIN,
    "certificate": domains.CONSTRUCTION_K7_QUERY_LOCAL_CERTIFICATE_V60_DOMAIN,
    "distinction": domains.CONSTRUCTION_K7_QUERY_LOCAL_DISTINCTION_V60_DOMAIN,
    "episode": domains.CONSTRUCTION_K7_QUERY_LOCAL_EPISODE_V60_DOMAIN,
    "sample_tax": domains.CONSTRUCTION_K7_QUERY_LOCAL_SAMPLE_TAX_V60_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_QUERY_LOCAL_CAMPAIGN_V60_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_QUERY_LOCAL_VERIFICATION_V60_DOMAIN,
}
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v60.py",
    "src/acfqp/generic_certificate_guided_partial_planner_v16.py",
    "src/acfqp/query_local_raw_evidence_campaign_core_v60.py",
    *previous.BOUND_SOURCE_PATHS,
)


class ConstructionK7QueryLocalPreregistrationV60Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryLocalPreregistrationV60Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative in BOUND_SOURCE_PATHS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append({"relative_path": relative, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return result


def _callable_fact(value: Any) -> dict[str, Any]:
    return {"module": value.__module__, "qualname": value.__qualname__, "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest()}


def campaign_config_v60() -> dict[str, Any]:
    config = previous.campaign_config_v59()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", BALANCED_TARGET_SEEDS),
        ("COUPLED_EXCHANGE", COUPLED_TARGET_SEEDS),
        ("MAINTENANCE_CASCADE", MAINTENANCE_TARGET_SEEDS),
    ):
        config["families"][family].update(target_seeds=seeds, planning_seed_count=PLANNING_SEED_COUNT_PER_FAMILY, maximum_acquisition_labels=MAXIMUM_ACQUISITION_LABELS)
    config["worker_count"] = WORKER_COUNT
    config["planning_seed_count_per_family"] = PLANNING_SEED_COUNT_PER_FAMILY
    config["maximum_partial_abstract_depth"] = MAXIMUM_PARTIAL_ABSTRACT_DEPTH
    config["maximum_partial_execution_steps"] = MAXIMUM_PARTIAL_EXECUTION_STEPS
    config["v60_domains"] = dict(V60_DOMAINS)
    config["v59_campaign_id"] = V59_CAMPAIGN_ID
    config["v59_verification_id"] = V59_VERIFICATION_ID
    return config


def _document() -> dict[str, Any]:
    registered = set(BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS)
    payload = {
        "schema": "acfqp.query_local_preregistration.v60",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v59_campaign_id": V59_CAMPAIGN_ID,
            "v59_campaign_sha256": "50117e4665dc29819e19e38ebf17a8fbaceb2ba9c466afc4bd377ed74f83e99a",
            "v59_verification_id": V59_VERIFICATION_ID,
            "v59_verification_sha256": "df0a035cec3b3a8790feaf1e20c6aed234b254cd403e7ac6b37d3081d16bb57e",
            "failed_v58r1_id": previous.FAILED_V58R1_ID,
            "factor_library_id": previous.previous.previous.V51_FACTOR_LIBRARY_ID,
            "factor_library_labels": previous.previous.previous.FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v60_domains": dict(V60_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "local_planner_callable": _callable_fact(run_certificate_guided_partial_episode_v16),
            "campaign_builder_callable": _callable_fact(build_query_local_raw_evidence_campaign_document_v60),
            "frozen_before_any_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(DEVELOPMENT_SEEDS).isdisjoint(registered),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {"target_seeds": list(BALANCED_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "MAINTENANCE_CASCADE": {"target_seeds": list(MAINTENANCE_TARGET_SEEDS), "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS},
            "generation_witness_available_to_constructor": False,
        },
        "raw_evidence_contract": {
            "every_acquisition_batch_embedded_as_canonical_raw_transition_rows": True,
            "symmetric_common_prefix_reconstructible_from_bytes": True,
            "raw_transition_hash_recomputed_before_issuance": True,
            "producer_free_raw_prefix_and_partial_dynamics_replay_required": True,
        },
        "query_local_recovery_contract": {
            "partial_model_proposes_action_order_without_ground_access": True,
            "unknown_residual_never_treated_as_safe": True,
            "every_ground_legality_or_transition_query_requires_prior_failed_certificate": True,
            "only_robust_proof_tree_state_actions_queried": True,
            "stream_prefix_residual_recovery_available": False,
            "complete_residual_world_model_synthesis_required": False,
            "maximum_abstract_depth": MAXIMUM_PARTIAL_ABSTRACT_DEPTH,
            "maximum_execution_steps": MAXIMUM_PARTIAL_EXECUTION_STEPS,
        },
        "sample_tax_contract": {
            "registered_occurrence_count": len(registered),
            "positive_family_acquisition_reduction_required": True,
            "positive_online_reduction_including_query_local_labels_required": True,
            "positive_lifetime_reduction_after_offline_tax_required": True,
            "all_accounting_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "matched_stopping_contract": {
            "same_true_bit_code_and_universal_eprocess": True,
            "symmetric_minimum_common_prefix_post_audit": True,
            "reachable_frontier_exhaustion_stop_available": False,
            "fixed_label_floor": None,
            "fixed_confirmation_block": None,
            "heuristic_mdl_information_units_available": False,
            "predictive_evidence_to_mdl_credit_available": False,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(V60_DOMAINS),
        "fresh_registered_outcome_execution_performed": False,
    }
    return {**payload, "preregistration_id": domains.extension_content_id_v60(V60_DOMAINS["preregistration"], payload)}


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class QueryLocalPreregistrationV60:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if self._issuer is not _ISSUER or type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes or document.get("preregistration_id") != self.preregistration_id or domains.extension_content_id_v60(V60_DOMAINS["preregistration"], payload) != self.preregistration_id:
            _fail("V60 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: QueryLocalPreregistrationV60 | None = None


def freeze_query_local_preregistration_v60() -> QueryLocalPreregistrationV60:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (identity != PREREGISTRATION_ID or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256):
        _fail("frozen V60 preregistration changed")
    if _CACHE is None:
        _CACHE = QueryLocalPreregistrationV60(_ISSUER, raw, identity)
    return _CACHE


def verify_query_local_preregistration_v60(value: Any) -> QueryLocalPreregistrationV60:
    if type(value) is not QueryLocalPreregistrationV60:
        _fail("V60 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_query_local_preregistration_v60()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V60 preregistration does not match frozen bytes")
    return value


__all__ = ("BOUND_SOURCE_PATHS", "V60_DOMAINS", "campaign_config_v60", "freeze_query_local_preregistration_v60", "verify_query_local_preregistration_v60")
