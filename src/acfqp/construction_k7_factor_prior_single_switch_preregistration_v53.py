"""Outcome-free V53 registration for a factor-prior single-switch ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_ACQUISITION_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_CAMPAIGN_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_EPISODE_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_FAILED_CERTIFICATE_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_LOCAL_DISTINCTION_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PREREGISTRATION_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PROGRAM_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_SAMPLE_TAX_V53_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_VERIFICATION_V53_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "53.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.223"
PROFILE_KEY = "construction_k7_factor_prior_single_switch_ablation_v53"
PREREGISTRATION_ID = "d58d386856e9f3a71d77a8415591219d031dd626b6aa2b2d715e68afaddf14cb"
EXPECTED_CANONICAL_BYTE_COUNT = 13_189
EXPECTED_CANONICAL_SHA256 = "ccaeca3214aefcefe5cb02b17ec985ef005f20622a03eb23904c49efb949fe44"

IMPLEMENTATION_COMMIT = "1105550"
V51_EVIDENCE_COMMIT = "154815d"
V51_CAMPAIGN_ID = "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
V51_CAMPAIGN_SHA256 = "124bb3d89ee55b7f942161934c8f7c80236826b5b715473a7c81fa626bc52433"
V51_VERIFICATION_ID = "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
V51_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
V51_FACTOR_COMPOSED_PROGRAM_ID = "b3c2392fa4a5a6d73aba9feb0a49162e58b312940efece87e6b743a402fe0a99"
V52_EVIDENCE_COMMIT = "622807c"
V52_CAMPAIGN_ID = "8952b649ce5fb3fb9a5ce3de6e324d52ac42cad334c1a257e88bd2aca18f1898"
V52_CAMPAIGN_SHA256 = "fb8e2d80d2acabff1005caf160b67af8f309a087a4262477f253b5ce26e5dfb9"
V52_VERIFICATION_ID = "c64fe32237c35de4a3661db1e8bec724e878d81b19b3c6366d0d04683a9f03b2"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/generic_cross_schema_factor_library_v7.py",
    "src/acfqp/generic_factor_prior_adaptive_synthesizer_v8.py",
    "src/acfqp/domains/stochastic_maintenance_cascade.py",
    "src/acfqp/factor_prior_single_switch_core_v53.py",
    "src/acfqp/construction_k7_cross_schema_factor_campaign_v51.py",
)

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
TARGET_ZONE_COUNT = 10
TARGET_REPAIR_BASE = 8
TARGET_SEEDS = tuple(range(531_301, 532_325))
DEVELOPMENT_SEEDS = tuple(range(539_101, 539_117))
PLANNING_VALIDATION_SEED_COUNT = 16
MAXIMUM_SYNTHESIS_LABELS_PER_ARM = 1_024
LAYOUT_CONFIRMATION_COUNT = 2
FACTOR_PRIOR_WEIGHT = 64
POSTERIOR_THRESHOLD_NUMERATOR = 4
POSTERIOR_THRESHOLD_DENOMINATOR = 5
POSTERIOR_CONFIRMATION_COUNT = 1
MINIMUM_POST_LAYOUT_CONFIRMATION_LABELS = 2
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
SHARED_RESIDUAL_SCAFFOLD_LABELS = 213
FACTOR_LIBRARY_LABELS = 370

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PREREGISTRATION_V53_DOMAIN,
    "acquisition": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_ACQUISITION_V53_DOMAIN,
    "program": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_PROGRAM_V53_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_FAILED_CERTIFICATE_V53_DOMAIN,
    "distinction": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_LOCAL_DISTINCTION_V53_DOMAIN,
    "episode": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_EPISODE_V53_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_SAMPLE_TAX_V53_DOMAIN,
    "campaign": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_CAMPAIGN_V53_DOMAIN,
    "verification": CONSTRUCTION_K7_FACTOR_PRIOR_SINGLE_SWITCH_VERIFICATION_V53_DOMAIN,
}


class ConstructionK7FactorPriorSingleSwitchPreregistrationV53Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorSingleSwitchPreregistrationV53Error(message)


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


def campaign_config_v53() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "target_zone_count": TARGET_ZONE_COUNT,
        "target_repair_base": TARGET_REPAIR_BASE,
        "target_seeds": TARGET_SEEDS,
        "planning_validation_seed_count": PLANNING_VALIDATION_SEED_COUNT,
        "maximum_synthesis_labels_per_arm": MAXIMUM_SYNTHESIS_LABELS_PER_ARM,
        "layout_confirmation_count": LAYOUT_CONFIRMATION_COUNT,
        "factor_prior_weight": FACTOR_PRIOR_WEIGHT,
        "posterior_threshold_numerator": POSTERIOR_THRESHOLD_NUMERATOR,
        "posterior_threshold_denominator": POSTERIOR_THRESHOLD_DENOMINATOR,
        "posterior_confirmation_count": POSTERIOR_CONFIRMATION_COUNT,
        "minimum_post_layout_confirmation_labels": MINIMUM_POST_LAYOUT_CONFIRMATION_LABELS,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "shared_residual_scaffold_labels": SHARED_RESIDUAL_SCAFFOLD_LABELS,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
        "require_incremental_reduction": True,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.factor_prior_single_switch_preregistration.v53",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v51_evidence_commit": V51_EVIDENCE_COMMIT,
            "v51_campaign_id": V51_CAMPAIGN_ID,
            "v51_campaign_sha256": V51_CAMPAIGN_SHA256,
            "v51_verification_id": V51_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_composed_program_id": V51_FACTOR_COMPOSED_PROGRAM_ID,
            "v52_evidence_commit": V52_EVIDENCE_COMMIT,
            "v52_campaign_id": V52_CAMPAIGN_ID,
            "v52_campaign_sha256": V52_CAMPAIGN_SHA256,
            "v52_verification_id": V52_VERIFICATION_ID,
            "v52_full_pipeline_contrast_not_relabelled_factor_only": True,
            "all_predecessor_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v53_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(
                DEVELOPMENT_SEEDS
            ).isdisjoint(TARGET_SEEDS),
        },
        "target_domain": {
            "family": "STOCHASTIC_MAINTENANCE_CASCADE",
            "raw_state_width": 10,
            "raw_action_field_width": 6,
            "zone_count": TARGET_ZONE_COUNT,
            "repair_base": TARGET_REPAIR_BASE,
            "target_seeds": list(TARGET_SEEDS),
            "acquisition_occurrence_count": len(TARGET_SEEDS),
            "planning_validation_seed_count": PLANNING_VALIDATION_SEED_COUNT,
            "planning_validation_seeds": list(
                TARGET_SEEDS[:PLANNING_VALIDATION_SEED_COUNT]
            ),
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "matched_single_switch_arms": {
            "arms": ["FACTOR_SIGNATURE_PRIOR_ON", "FACTOR_SIGNATURE_PRIOR_OFF"],
            "same_finite_anonymous_candidate_grammar": True,
            "same_catalogue_equivalence_quotient": True,
            "same_witness_blind_bfs_query_schedule": True,
            "same_exact_zero_one_likelihood": True,
            "same_posterior_threshold": {
                "numerator": POSTERIOR_THRESHOLD_NUMERATOR,
                "denominator": POSTERIOR_THRESHOLD_DENOMINATOR,
            },
            "same_confirmation_rule": {
                "posterior_confirmation_count": POSTERIOR_CONFIRMATION_COUNT,
                "minimum_post_layout_labels": MINIMUM_POST_LAYOUT_CONFIRMATION_LABELS,
            },
            "same_shared_residual_scaffold": True,
            "factor_prior_on_multiplier": FACTOR_PRIOR_WEIGHT,
            "factor_prior_off_multiplier": 1,
            "only_switched_variable": "CROSS_SCHEMA_FACTOR_SIGNATURE_PRIOR_INITIAL_WEIGHT",
            "compiled_assignment_and_plan_equality_required": True,
        },
        "sample_tax_contract": {
            "shared_residual_scaffold_labels_charged_to_each_arm": SHARED_RESIDUAL_SCAFFOLD_LABELS,
            "historical_factor_library_labels_charged_only_to_prior_on": FACTOR_LIBRARY_LABELS,
            "development_occurrences": len(DEVELOPMENT_SEEDS),
            "development_incremental_label_reduction": 9,
            "development_result_used_only_to_freeze_horizon_not_as_registered_evidence": True,
            "registered_acquisition_occurrence_count": len(TARGET_SEEDS),
            "target_labels_execution_steps_planning_and_certificate_compute_separate": True,
            "positive_incremental_target_label_reduction_required": True,
            "positive_lifetime_label_reduction_and_diagnostic_break_even_within_horizon_required": True,
            "official_break_even_claimed": False,
        },
        "required_positive_conditions": [
            "COMMON_PREFIX_RAW_OBSERVATIONS_AND_SURVIVOR_COUNTS_MATCH_EXACTLY",
            "ONLY_FACTOR_SIGNATURE_PRIOR_MULTIPLIER_DIFFERS",
            "BOTH_ARMS_COMPILE_IDENTICAL_ASSIGNMENTS",
            "MATCHED_PLANNING_VALIDATION_ACTIONS_AND_OUTCOMES_SUCCEED",
            "EVERY_LOCAL_GROUND_DISTINCTION_FOLLOWS_CERTIFICATE_FAILURE",
            "TARGET_INCREMENTAL_LABEL_REDUCTION_IS_POSITIVE",
            "FULL_HISTORICAL_FACTOR_LIBRARY_TAX_AMORTIZES_WITHIN_FROZEN_HORIZON",
        ],
        "claim_boundary": {
            "factor_prior_single_variable_ablation_preregistered": True,
            "registered_outcome_observed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v53_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FactorPriorSingleSwitchPreregistrationV53:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V53 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V53 preregistration canonical bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V53 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_factor_prior_single_switch_preregistration_v53() -> FactorPriorSingleSwitchPreregistrationV53:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V53 preregistration changed")
    return FactorPriorSingleSwitchPreregistrationV53(_ISSUER, raw, identity)


def verify_factor_prior_single_switch_preregistration_v53(
    value: FactorPriorSingleSwitchPreregistrationV53,
) -> FactorPriorSingleSwitchPreregistrationV53:
    if type(value) is not FactorPriorSingleSwitchPreregistrationV53:
        _fail("V53 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_factor_prior_single_switch_preregistration_v53()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("V53 preregistration semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FUTURE_DOMAINS",
    "FactorPriorSingleSwitchPreregistrationV53",
    "PREREGISTRATION_ID",
    "campaign_config_v53",
    "freeze_factor_prior_single_switch_preregistration_v53",
    "verify_factor_prior_single_switch_preregistration_v53",
)
