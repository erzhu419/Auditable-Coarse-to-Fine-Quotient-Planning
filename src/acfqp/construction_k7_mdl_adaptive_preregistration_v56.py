"""Outcome-free V56 registration for MDL adaptive two-domain synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "56.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.227"
PROFILE_KEY = "construction_k7_mdl_adaptive_cross_domain_v56"
PREREGISTRATION_ID = "e78cb6b1698f88d27e2368798f331b3d289f2ff381d98b7a6207a2710706bd6e"
EXPECTED_CANONICAL_BYTE_COUNT = 9_286
EXPECTED_CANONICAL_SHA256 = "3cb1a4cc6dc0df7473ec5b45c00e42c936bb8dcf1587e76edb81dfb79b57bf88"
IMPLEMENTATION_COMMIT = "8d6a606"

V55_CAMPAIGN_ID = "ea85860f499ac631a7f3e6b306974be2a2d7c9de88cde3cf492380ebd59ec589"
V55_CAMPAIGN_SHA256 = "38363f222d1b4047e4ce6f2fd5e6c4aea595709b473e9aed44d90fd54245128a"
V55_VERIFICATION_ID = "ec6fe8ee01a663030ffdd146613d1f4231000f27bae0773f47c15b6d398fd1f6"
V51_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
FACTOR_LIBRARY_LABELS = 370
FACTOR_LIBRARY = {
    "factor_library_id": V51_FACTOR_LIBRARY_ID,
    "cross_schema_subprograms": [
        {
            "signature_sha256": signature,
            "source_schema_pairs": [[7, 5], [9, 6]],
        }
        for signature in (
            "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
        )
    ],
}

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
BALANCED_TARGET_SEEDS = tuple(range(561_101, 561_133))
COUPLED_TARGET_SEEDS = tuple(range(562_101, 562_133))
DEVELOPMENT_SEEDS = (569_910, 569_911, 569_920, 569_921)
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
    "src/acfqp/construction_k7_domain_registry_extension_v56.py",
    "src/acfqp/generic_mdl_adaptive_joint_synthesizer_v11.py",
    "src/acfqp/adaptive_mdl_cross_domain_campaign_core_v56.py",
    "src/acfqp/generic_adaptive_joint_factor_residual_synthesizer_v10.py",
    "src/acfqp/generic_joint_factor_residual_world_model_v9.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/domains/stochastic_batch_refinement.py",
    "src/acfqp/domains/stochastic_balanced_batch_refinement.py",
    "src/acfqp/domains/stochastic_coupled_exchange.py",
)

FUTURE_DOMAINS = {
    "preregistration": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_PREREGISTRATION_V56_DOMAIN,
    "candidate": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_CANDIDATE_V56_DOMAIN,
    "acquisition": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_ACQUISITION_V56_DOMAIN,
    "failed_certificate": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_FAILED_CERTIFICATE_V56_DOMAIN,
    "distinction": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_LOCAL_DISTINCTION_V56_DOMAIN,
    "episode": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_EPISODE_V56_DOMAIN,
    "validation": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_ISOLATED_VALIDATION_V56_DOMAIN,
    "ood": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_OOD_REJECTION_V56_DOMAIN,
    "sample_tax": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_SAMPLE_TAX_V56_DOMAIN,
    "campaign": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_CAMPAIGN_V56_DOMAIN,
    "verification": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_VERIFICATION_V56_DOMAIN,
}
GENERIC_DOMAINS = {
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
}


class ConstructionK7MDLAdaptivePreregistrationV56Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MDLAdaptivePreregistrationV56Error(message)


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


def campaign_config_v56() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
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
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_preregistration.v56",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v55_campaign_id": V55_CAMPAIGN_ID,
            "v55_campaign_sha256": V55_CAMPAIGN_SHA256,
            "v55_verification_id": V55_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_library_labels": FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "extension_domains": dict(FUTURE_DOMAINS),
            "generic_subartifact_domains": dict(GENERIC_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "historical_content_id_callable": _callable_fact(content_id),
            "monolithic_phase3e_registry_source_not_extended_by_v56": True,
            "v55_extension_source_not_modified_by_v56": True,
            "frozen_before_any_v56_registered_outcome": True,
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
        "mdl_adaptive_contract": {
            "candidate_synthesis_attempted_after_every_support_query": True,
            "fixed_minimum_candidate_label_floor": None,
            "fixed_confirmation_block_size": None,
            "complete_layout_program_factor_and_residual_synthesized": True,
            "observed_information_definition": (
                "RAW_OUTCOME_ROWS_PLUS_DISTINCT_PRE_STATES_PLUS_DISTINCT_ACTIONS_"
                "PLUS_TERMINAL_OBSERVATIONS"
            ),
            "program_description_definition": (
                "STRUCTURAL_TOKENS_TIMES_TYPED_MAX_FIELD_INDEX_CODEWORD"
            ),
            "unresolved_discovered_frontier_penalty": True,
            "invalidated_candidate_disagreement_penalty": (
                INVALIDATED_CANDIDATE_PENALTY_UNITS
            ),
            "confidence_reserve_units": CONFIDENCE_RESERVE_UNITS,
            "statistical_confidence_interval_claimed": False,
        },
        "matched_single_switch_arms": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_complete_program_synthesizer": True,
            "same_raw_query_order": True,
            "same_integer_mdl_and_confidence_formula": True,
            "same_confidence_reserve_units": CONFIDENCE_RESERVE_UNITS,
            "same_disagreement_penalty_units": (
                INVALIDATED_CANDIDATE_PENALTY_UNITS
            ),
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
            "honest_partial_dynamics_report_required": True,
            "strict_incompatible_bitmask_ood_no_transfer": True,
            "ood_outcome_execution_forbidden": True,
        },
        "sample_tax_contract": {
            "registered_occurrence_count": (
                len(BALANCED_TARGET_SEEDS) + len(COUPLED_TARGET_SEEDS)
            ),
            "factor_library_labels_charged_only_to_prior_on": (
                FACTOR_LIBRARY_LABELS
            ),
            "positive_incremental_reduction_required_in_each_family": True,
            "positive_online_and_lifetime_label_reduction_required": True,
            "offline_acquisition_recovery_validation_execution_derivation_"
            "planning_and_certificate_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "factor_prior_on_acquisition_labels": 356,
            "strict_no_prior_acquisition_labels": 431,
            "incremental_reduction": 75,
            "temporary_factor_library_tax": 20,
            "lifetime_reduction": 55,
            "matched_two_family_plans": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "mdl_adaptive_campaign_preregistered": True,
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
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v56_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains_v56.extension_content_id_v56(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class MDLAdaptivePreregistrationV56:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V56 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains_v56.extension_content_id_v56(
                FUTURE_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V56 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: MDLAdaptivePreregistrationV56 | None = None


def freeze_mdl_adaptive_preregistration_v56() -> MDLAdaptivePreregistrationV56:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V56 preregistration changed")
    if _CACHE is None:
        _CACHE = MDLAdaptivePreregistrationV56(_ISSUER, raw, identity)
    return _CACHE


def verify_mdl_adaptive_preregistration_v56(
    value: Any,
) -> MDLAdaptivePreregistrationV56:
    if type(value) is not MDLAdaptivePreregistrationV56:
        _fail("V56 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_mdl_adaptive_preregistration_v56()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V56 preregistration does not match frozen bytes")
    return value


__all__ = (
    "FACTOR_LIBRARY",
    "FUTURE_DOMAINS",
    "GENERIC_DOMAINS",
    "MDLAdaptivePreregistrationV56",
    "campaign_config_v56",
    "freeze_mdl_adaptive_preregistration_v56",
    "verify_mdl_adaptive_preregistration_v56",
)
