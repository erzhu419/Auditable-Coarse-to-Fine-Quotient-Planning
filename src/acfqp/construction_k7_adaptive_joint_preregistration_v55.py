"""Outcome-free V55 registration for adaptive joint world-model synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v55 as domains_v55
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "55.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.226"
PROFILE_KEY = "construction_k7_adaptive_joint_world_model_v55"
PREREGISTRATION_ID = "78a207755fdd240b118305911f4ed99ed652cbbe2897f2144fa0d462fd99e44f"
EXPECTED_CANONICAL_BYTE_COUNT = 9_671
EXPECTED_CANONICAL_SHA256 = "32a50e4a44ccf6cfe2e07bd0d7bc2f180c73dab804cfdd5a0fd4128da040bd56"
IMPLEMENTATION_COMMIT = "f3d4276"

V54R1_CAMPAIGN_ID = "48f49e489e1cc5dfc98ec14c23565f66edfa93d51e15ca23f66f4668cc377223"
V54R1_CAMPAIGN_SHA256 = "9bf6f766b95fb18a81a7b69df037f9b61dba2f342579356636cc784d6955cfd9"
V54R1_VERIFICATION_ID = "a4d71d1f6517c032e8f7f14b4fd8b2e6ab9560ca96bd4741e2d5874ad06b5acc"
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
TARGET_STAGE_COUNT = 9
TARGET_UNIT_BASE = 5
TARGET_SEEDS = tuple(range(551_101, 551_229))
DEVELOPMENT_SEEDS = tuple(range(559_900, 559_932))
PLANNING_VALIDATION_SEED_COUNT = 8
WORKER_COUNT = 4
MINIMUM_CANDIDATE_LABELS = 80
MAXIMUM_ACQUISITION_LABELS = 128
CONFIRMATION_BLOCK_SIZE = 4
FACTOR_PRIOR_WEIGHT = 64
EXACT_LIKELIHOOD_BLOCK_WEIGHT = 64
STOPPING_WEIGHT = 64
MINIMUM_REUSABLE_FACTOR_COUNT = 3
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MAXIMUM_LOCAL_RESYNTHESES = 8

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v55.py",
    "src/acfqp/generic_adaptive_joint_factor_residual_synthesizer_v10.py",
    "src/acfqp/adaptive_joint_factor_residual_campaign_core_v55.py",
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_layout_factorized_world_model_v6.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/generic_joint_factor_residual_world_model_v9.py",
    "src/acfqp/domains/stochastic_batch_refinement.py",
    "src/acfqp/domains/stochastic_balanced_batch_refinement.py",
)

FUTURE_DOMAINS = {
    "preregistration": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_PREREGISTRATION_V55_DOMAIN,
    "candidate": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_CANDIDATE_V55_DOMAIN,
    "acquisition": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_ACQUISITION_V55_DOMAIN,
    "failed_certificate": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_FAILED_CERTIFICATE_V55_DOMAIN,
    "distinction": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_LOCAL_DISTINCTION_V55_DOMAIN,
    "episode": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_EPISODE_V55_DOMAIN,
    "validation": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_ISOLATED_VALIDATION_V55_DOMAIN,
    "ood": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_OOD_REJECTION_V55_DOMAIN,
    "sample_tax": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_SAMPLE_TAX_V55_DOMAIN,
    "campaign": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_CAMPAIGN_V55_DOMAIN,
    "verification": domains_v55.CONSTRUCTION_K7_ADAPTIVE_JOINT_VERIFICATION_V55_DOMAIN,
}
GENERIC_DOMAINS = {
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
}


class ConstructionK7AdaptiveJointPreregistrationV55Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveJointPreregistrationV55Error(message)


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


def campaign_config_v55() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "generic_domains": dict(GENERIC_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "target_stage_count": TARGET_STAGE_COUNT,
        "target_unit_base": TARGET_UNIT_BASE,
        "target_seeds": TARGET_SEEDS,
        "planning_validation_seed_count": PLANNING_VALIDATION_SEED_COUNT,
        "worker_count": WORKER_COUNT,
        "minimum_candidate_labels": MINIMUM_CANDIDATE_LABELS,
        "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
        "confirmation_block_size": CONFIRMATION_BLOCK_SIZE,
        "factor_prior_weight": FACTOR_PRIOR_WEIGHT,
        "exact_likelihood_block_weight": EXACT_LIKELIHOOD_BLOCK_WEIGHT,
        "stopping_weight": STOPPING_WEIGHT,
        "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "maximum_local_resyntheses": MAXIMUM_LOCAL_RESYNTHESES,
        "factor_library_id": V51_FACTOR_LIBRARY_ID,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
        "v54r1_campaign_id": V54R1_CAMPAIGN_ID,
        "v54r1_verification_id": V54R1_VERIFICATION_ID,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.adaptive_joint_preregistration.v55",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v54r1_campaign_id": V54R1_CAMPAIGN_ID,
            "v54r1_campaign_sha256": V54R1_CAMPAIGN_SHA256,
            "v54r1_verification_id": V54R1_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_library_labels": FACTOR_LIBRARY_LABELS,
            "v54r1_target_program_consumed": False,
            "v54r1_reusable_slot_inventory_consumed": False,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "extension_domains": dict(FUTURE_DOMAINS),
            "generic_subartifact_domains": dict(GENERIC_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "historical_content_id_callable": _callable_fact(content_id),
            "monolithic_phase3e_registry_source_not_extended_by_v55": True,
            "frozen_before_any_v55_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(
                DEVELOPMENT_SEEDS
            ).isdisjoint(TARGET_SEEDS),
        },
        "target_domain": {
            "family": "OPAQUE_BALANCED_STOCHASTIC_BATCH_REFINEMENT",
            "raw_state_width": 6,
            "raw_action_field_width": 5,
            "stage_count": TARGET_STAGE_COUNT,
            "unit_base": TARGET_UNIT_BASE,
            "target_seeds": list(TARGET_SEEDS),
            "planning_validation_seeds": list(
                TARGET_SEEDS[:PLANNING_VALIDATION_SEED_COUNT]
            ),
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "adaptive_joint_contract": {
            "witness_blind_depth_frontier_query_policy": True,
            "minimum_candidate_labels": MINIMUM_CANDIDATE_LABELS,
            "maximum_acquisition_labels": MAXIMUM_ACQUISITION_LABELS,
            "layout_program_legality_terminal_factor_and_residual_jointly_synthesized": True,
            "full_frontier_target_layout_calibration_forbidden": True,
            "shared_residual_scaffold_consumed": False,
            "predeclared_reusable_factor_slots_consumed": False,
            "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
            "at_least_one_novel_factor_required": True,
            "at_least_one_schema_bound_residual_required": True,
        },
        "matched_single_switch_arms": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_complete_program_synthesizer": True,
            "same_raw_query_order": True,
            "same_exact_replay_likelihood": True,
            "same_confirmation_block_size": CONFIRMATION_BLOCK_SIZE,
            "same_exact_likelihood_block_weight": EXACT_LIKELIHOOD_BLOCK_WEIGHT,
            "same_stopping_weight": STOPPING_WEIGHT,
            "factor_prior_on_initial_weight": FACTOR_PRIOR_WEIGHT,
            "factor_prior_off_initial_weight": 1,
            "only_switched_variable": "ANONYMOUS_FACTOR_SIGNATURE_INITIAL_WEIGHT",
        },
        "planning_and_recovery": {
            "receding_abstract_planning": True,
            "matched_strict_exact_context_baseline": True,
            "query_local_state_action_certificate": True,
            "local_ground_query_before_certificate_failure_forbidden": True,
            "counterexample_triggers_local_program_resynthesis_and_replanning": True,
            "maximum_local_resyntheses": MAXIMUM_LOCAL_RESYNTHESES,
        },
        "isolated_validation_and_ood": {
            "full_frontier_validation_seed_count": PLANNING_VALIDATION_SEED_COUNT,
            "validation_rows_consumed_for_acquisition_binding_or_planning": False,
            "honest_partial_dynamics_report_required": True,
            "strict_bitmask_ood_full_reconstruction_and_no_transfer_required": True,
            "ood_outcome_execution_forbidden": True,
        },
        "sample_tax_contract": {
            "registered_acquisition_occurrence_count": len(TARGET_SEEDS),
            "factor_library_labels_charged_only_to_prior_on": FACTOR_LIBRARY_LABELS,
            "minimum_incremental_savings_from_one_confirmation_block_per_occurrence": (
                len(TARGET_SEEDS) * CONFIRMATION_BLOCK_SIZE
            ),
            "minimum_savings_exceeds_historical_factor_library_tax": (
                len(TARGET_SEEDS) * CONFIRMATION_BLOCK_SIZE
                > FACTOR_LIBRARY_LABELS
            ),
            "positive_incremental_online_and_lifetime_label_reduction_required": True,
            "acquisition_local_recovery_validation_execution_derivation_planning_and_certificate_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "focused_campaign_seed_count": 8,
            "focused_prior_labels": 640,
            "focused_no_prior_labels": 672,
            "focused_incremental_reduction": 32,
            "focused_planning_seed_count": 2,
            "focused_matched_plans_and_certificate_first_recovery": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "adaptive_joint_campaign_preregistered": True,
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
        "fresh_v55_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains_v55.extension_content_id_v55(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AdaptiveJointPreregistrationV55:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V55 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains_v55.extension_content_id_v55(
                FUTURE_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V55 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: AdaptiveJointPreregistrationV55 | None = None


def freeze_adaptive_joint_preregistration_v55() -> AdaptiveJointPreregistrationV55:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V55 preregistration changed")
    if _CACHE is None:
        _CACHE = AdaptiveJointPreregistrationV55(_ISSUER, raw, identity)
    return _CACHE


def verify_adaptive_joint_preregistration_v55(value: Any) -> AdaptiveJointPreregistrationV55:
    if type(value) is not AdaptiveJointPreregistrationV55:
        _fail("V55 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_adaptive_joint_preregistration_v55()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V55 preregistration does not match frozen bytes")
    return value


__all__ = (
    "AdaptiveJointPreregistrationV55",
    "FACTOR_LIBRARY",
    "FUTURE_DOMAINS",
    "GENERIC_DOMAINS",
    "campaign_config_v55",
    "freeze_adaptive_joint_preregistration_v55",
    "verify_adaptive_joint_preregistration_v55",
)
