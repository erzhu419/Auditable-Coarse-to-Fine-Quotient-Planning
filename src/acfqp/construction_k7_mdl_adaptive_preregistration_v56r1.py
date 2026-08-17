"""Outcome-free V56r1 registration after the frozen V56 stop failure."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v56r1 as domains_v56r1
from acfqp import construction_k7_mdl_adaptive_failure_v56 as failure_v56
from acfqp import construction_k7_mdl_adaptive_preregistration_v56 as pre_v56
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "56.1.0"
PROPOSED_CONTRACT_VERSION = "2.0.228"
PROFILE_KEY = "construction_k7_mdl_adaptive_cross_domain_v56r1"
PREREGISTRATION_ID = "422df5321236e8e9b7f7516bae1e88fe428ef794fa940a2bae00479af00d52ed"
EXPECTED_CANONICAL_BYTE_COUNT = 9_503
EXPECTED_CANONICAL_SHA256 = "a9d7fa0118b93113c3c51b5e84c15a41d4e05db128e69e34e3bde5a75b5d6f50"
IMPLEMENTATION_COMMIT = "61c4d0e"
V56_FAILURE_ID = failure_v56.FAILURE_ID

V55_CAMPAIGN_ID = pre_v56.V55_CAMPAIGN_ID
V55_CAMPAIGN_SHA256 = pre_v56.V55_CAMPAIGN_SHA256
V55_VERIFICATION_ID = pre_v56.V55_VERIFICATION_ID
V51_FACTOR_LIBRARY_ID = pre_v56.V51_FACTOR_LIBRARY_ID
FACTOR_LIBRARY_LABELS = pre_v56.FACTOR_LIBRARY_LABELS
FACTOR_LIBRARY = pre_v56.FACTOR_LIBRARY

TERMINAL_TOKENS = dict(pre_v56.TERMINAL_TOKENS)
BALANCED_TARGET_SEEDS = tuple(range(563_101, 563_133))
COUPLED_TARGET_SEEDS = tuple(range(564_101, 564_133))
DEVELOPMENT_SEEDS = (569_930, 569_931, 569_940, 569_941)
PLANNING_SEED_COUNT_PER_FAMILY = 4
WORKER_COUNT = 4
FACTOR_SIGNATURE_CREDIT_UNITS = 16
CONFIDENCE_RESERVE_UNITS = 48
INVALIDATED_CANDIDATE_PENALTY_UNITS = 16
MINIMUM_REUSABLE_FACTOR_COUNT = 3
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MAXIMUM_LOCAL_RESYNTHESES = 8

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v56r1.py",
    "src/acfqp/generic_mdl_adaptive_joint_synthesizer_v11r1.py",
    "src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56r1.py",
    "src/acfqp/construction_k7_mdl_adaptive_failure_v56.py",
    *pre_v56.BOUND_SOURCE_PATHS,
)

FROZEN_V56_DOMAINS = {
    key: pre_v56.FUTURE_DOMAINS[key]
    for key in (
        "candidate",
        "failed_certificate",
        "distinction",
        "episode",
        "validation",
        "ood",
    )
}
SUCCESSOR_DOMAINS = {
    "preregistration": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_PREREGISTRATION_V56R1_DOMAIN
    ),
    "acquisition": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_ACQUISITION_V56R1_DOMAIN
    ),
    "sample_tax": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_SAMPLE_TAX_V56R1_DOMAIN
    ),
    "campaign": domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_CAMPAIGN_V56R1_DOMAIN,
    "verification": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_VERIFICATION_V56R1_DOMAIN
    ),
}
GENERIC_DOMAINS = dict(pre_v56.GENERIC_DOMAINS)


class ConstructionK7MDLAdaptivePreregistrationV56R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MDLAdaptivePreregistrationV56R1Error(message)


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


def campaign_config_v56r1() -> dict[str, Any]:
    return {
        "domains": dict(FROZEN_V56_DOMAINS),
        "successor_domains": dict(SUCCESSOR_DOMAINS),
        "generic_domains": dict(GENERIC_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "families": {
            "BALANCED_BATCH_REFINEMENT": {
                "stage_count": 9,
                "unit_base": 5,
                "target_seeds": BALANCED_TARGET_SEEDS,
                "planning_seed_count": PLANNING_SEED_COUNT_PER_FAMILY,
                "maximum_acquisition_labels": 128,
            },
            "COUPLED_EXCHANGE": {
                "stage_count": 7,
                "primary_base": 5,
                "target_seeds": COUPLED_TARGET_SEEDS,
                "planning_seed_count": PLANNING_SEED_COUNT_PER_FAMILY,
                "maximum_acquisition_labels": 160,
            },
        },
        "worker_count": WORKER_COUNT,
        "factor_signature_credit_units": FACTOR_SIGNATURE_CREDIT_UNITS,
        "confidence_reserve_units": CONFIDENCE_RESERVE_UNITS,
        "invalidated_candidate_penalty_units": (
            INVALIDATED_CANDIDATE_PENALTY_UNITS
        ),
        "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "maximum_local_resyntheses": MAXIMUM_LOCAL_RESYNTHESES,
        "factor_library_id": V51_FACTOR_LIBRARY_ID,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
        "v55_campaign_id": V55_CAMPAIGN_ID,
        "v55_verification_id": V55_VERIFICATION_ID,
        "v56_failure_id": V56_FAILURE_ID,
    }


def _document() -> dict[str, Any]:
    frozen_failure = failure_v56.freeze_mdl_adaptive_failure_v56()
    if frozen_failure["failure_id"] != V56_FAILURE_ID:
        _fail("V56r1 frozen predecessor identity changed")
    payload = {
        "schema": "acfqp.mdl_adaptive_preregistration.v56r1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v56_failure_id": V56_FAILURE_ID,
            "v56_failure_sha256": failure_v56.EXPECTED_CANONICAL_SHA256,
            "v56_same_identity_rerun_forbidden": True,
            "v55_campaign_id": V55_CAMPAIGN_ID,
            "v55_campaign_sha256": V55_CAMPAIGN_SHA256,
            "v55_verification_id": V55_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_library_labels": FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "successor_domains": dict(SUCCESSOR_DOMAINS),
            "unchanged_v56_subartifact_domains": dict(FROZEN_V56_DOMAINS),
            "generic_subartifact_domains": dict(GENERIC_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "monolithic_phase3e_registry_source_not_extended_by_v56r1": True,
            "v56_sources_not_modified_by_v56r1": True,
            "frozen_before_any_v56r1_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": (
                set(DEVELOPMENT_SEEDS).isdisjoint(BALANCED_TARGET_SEEDS)
                and set(DEVELOPMENT_SEEDS).isdisjoint(COUPLED_TARGET_SEEDS)
            ),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "raw_state_width": 6,
                "raw_action_field_width": 5,
                "stage_count": 9,
                "unit_base": 5,
                "target_seeds": list(BALANCED_TARGET_SEEDS),
            },
            "COUPLED_EXCHANGE": {
                "raw_state_width": 10,
                "raw_action_field_width": 6,
                "stage_count": 7,
                "primary_base": 5,
                "target_seeds": list(COUPLED_TARGET_SEEDS),
                "higher_order_composed_update_required": True,
            },
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "mdl_adaptive_successor_contract": {
            "candidate_synthesis_attempted_after_every_support_query": True,
            "fixed_minimum_candidate_label_floor": None,
            "fixed_confirmation_block_size": None,
            "stop_disjunction": [
                "POSITIVE_MDL_CONFIDENCE_MARGIN",
                "EXACT_ZERO_DISAGREEMENT_AT_REACHABLE_FRONTIER_CLOSURE",
            ],
            "exact_frontier_closure_is_a_stop_not_a_calibration_input": True,
            "frontier_closure_rule_same_in_both_arms": True,
            "candidate_must_have_zero_exact_replay_disagreements": True,
            "candidate_must_have_zero_unresolved_frontier_units": True,
            "v56_failed_target_not_retuned_or_reused": True,
        },
        "matched_single_switch_arms": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_complete_program_synthesizer": True,
            "same_raw_query_order": True,
            "same_mdl_confidence_or_exact_frontier_stop_rule": True,
            "factor_prior_on_code_credit_per_reusable_signature": (
                FACTOR_SIGNATURE_CREDIT_UNITS
            ),
            "factor_prior_off_code_credit": 0,
            "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
        },
        "planning_and_recovery": {
            "planning_seed_count_per_family": PLANNING_SEED_COUNT_PER_FAMILY,
            "receding_abstract_planning": True,
            "matched_strict_exact_context_baseline": True,
            "certificate_failure_before_every_local_ground_query": True,
            "counterexample_triggers_local_program_resynthesis": True,
            "maximum_local_resyntheses": MAXIMUM_LOCAL_RESYNTHESES,
        },
        "isolated_validation_and_ood": {
            "full_frontier_validation_is_outcome_isolated": True,
            "validation_rows_consumed_for_acquisition_binding_or_planning": False,
            "strict_incompatible_bitmask_ood_no_transfer": True,
            "ood_outcome_execution_forbidden": True,
        },
        "sample_tax_contract": {
            "registered_occurrence_count": (
                len(BALANCED_TARGET_SEEDS) + len(COUPLED_TARGET_SEEDS)
            ),
            "factor_library_labels_charged_only_to_prior_on": FACTOR_LIBRARY_LABELS,
            "positive_incremental_reduction_required_in_each_family": True,
            "positive_online_and_lifetime_label_reduction_required": True,
            "all_sample_execution_planning_and_certificate_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "factor_prior_on_acquisition_labels": 409,
            "strict_no_prior_acquisition_labels": 460,
            "incremental_reduction": 51,
            "temporary_factor_library_tax": 20,
            "lifetime_reduction": 30,
            "strict_no_prior_exact_frontier_closure_count": 2,
            "matched_two_family_plans": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "v56r1_campaign_preregistered": True,
            "registered_outcome_observed": False,
            "arbitrary_domain_transfer_claimed": False,
            "global_exact_dynamics_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "factor_library": FACTOR_LIBRARY,
        "future_content_domains": dict(SUCCESSOR_DOMAINS),
        "fresh_v56r1_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains_v56r1.extension_content_id_v56r1(
            SUCCESSOR_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MDLAdaptivePreregistrationV56R1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V56r1 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains_v56r1.extension_content_id_v56r1(
                SUCCESSOR_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V56r1 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: MDLAdaptivePreregistrationV56R1 | None = None


def freeze_mdl_adaptive_preregistration_v56r1() -> MDLAdaptivePreregistrationV56R1:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V56r1 preregistration changed")
    if _CACHE is None:
        _CACHE = MDLAdaptivePreregistrationV56R1(_ISSUER, raw, identity)
    return _CACHE


def verify_mdl_adaptive_preregistration_v56r1(
    value: Any,
) -> MDLAdaptivePreregistrationV56R1:
    if type(value) is not MDLAdaptivePreregistrationV56R1:
        _fail("V56r1 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_mdl_adaptive_preregistration_v56r1()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V56r1 preregistration does not match frozen bytes")
    return value


__all__ = (
    "FACTOR_LIBRARY",
    "FROZEN_V56_DOMAINS",
    "GENERIC_DOMAINS",
    "SUCCESSOR_DOMAINS",
    "MDLAdaptivePreregistrationV56R1",
    "campaign_config_v56r1",
    "freeze_mdl_adaptive_preregistration_v56r1",
    "verify_mdl_adaptive_preregistration_v56r1",
)
