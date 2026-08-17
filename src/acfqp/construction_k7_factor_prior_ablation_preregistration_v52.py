"""Outcome-free V52 registration for matched acquisition sample-tax ablation."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_ACQUISITION_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_CAMPAIGN_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_EPISODE_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_FAILED_CERTIFICATE_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_LOCAL_DISTINCTION_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_SAMPLE_TAX_V52_DOMAIN,
    CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_VERIFICATION_V52_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "52.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.222"
PROFILE_KEY = "construction_k7_factor_prior_acquisition_ablation_v52"
PREREGISTRATION_ID = "972617466efa02bee49d3976a7f65e70807eb9a9af0abd3628151fc7ad225fd2"
EXPECTED_CANONICAL_BYTE_COUNT = 5_418
EXPECTED_CANONICAL_SHA256 = "fe3837f719caf93b581f893ca23dadb6882ee081b8f60697bbc9203d4684bc8b"

IMPLEMENTATION_COMMIT = "48b9239"
V51_EVIDENCE_COMMIT = "154815d"
V51_CAMPAIGN_ID = "44a63b782201b3e53a32de1bc071d66fb06526903f96a037d2c55c8f3068e144"
V51_CAMPAIGN_SHA256 = "124bb3d89ee55b7f942161934c8f7c80236826b5b715473a7c81fa626bc52433"
V51_VERIFICATION_ID = "8d0e1044fe8db610375f35cd0956387b1ce6dca21d786cc62ae9bf1c69c66b3f"
V51_FACTOR_LIBRARY_ID = "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
V51_FACTOR_COMPOSED_PROGRAM_ID = "b3c2392fa4a5a6d73aba9feb0a49162e58b312940efece87e6b743a402fe0a99"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/phase3e_ids.py",
    "src/acfqp/generic_atomic_expression_world_model_v4.py",
    "src/acfqp/generic_layout_factorized_world_model_v5.py",
    "src/acfqp/domains/stochastic_maintenance_cascade.py",
    "src/acfqp/factor_prior_acquisition_ablation_core_v52.py",
    "src/acfqp/construction_k7_cross_schema_factor_campaign_v51.py",
)

TERMINAL_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
TARGET_ZONE_COUNT = 10
TARGET_REPAIR_BASE = 8
TARGET_SEEDS = tuple(range(521_301, 521_317))
DEVELOPMENT_SEEDS = tuple(range(529_101, 529_117))
MAXIMUM_PRIOR_LAYOUT_LABELS = 32
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MAXIMUM_NO_PRIOR_LABELS_PER_OCCURRENCE = 2_048
MINIMUM_REUSED_FACTOR_COUNT = 5
HISTORICAL_FACTOR_PRIOR_LABELS = 583
MAXIMUM_REGISTERED_BREAK_EVEN_OCCURRENCES = len(TARGET_SEEDS)

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_PREREGISTRATION_V52_DOMAIN,
    "acquisition": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_ACQUISITION_V52_DOMAIN,
    "failed_certificate": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_FAILED_CERTIFICATE_V52_DOMAIN,
    "distinction": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_LOCAL_DISTINCTION_V52_DOMAIN,
    "episode": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_EPISODE_V52_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_SAMPLE_TAX_V52_DOMAIN,
    "campaign": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_CAMPAIGN_V52_DOMAIN,
    "verification": CONSTRUCTION_K7_FACTOR_PRIOR_ABLATION_VERIFICATION_V52_DOMAIN,
}


class ConstructionK7FactorPriorAblationPreregistrationV52Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FactorPriorAblationPreregistrationV52Error(message)


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


def campaign_config_v52() -> dict[str, Any]:
    return {
        "domains": dict(FUTURE_DOMAINS),
        "terminal_tokens": dict(TERMINAL_TOKENS),
        "target_zone_count": TARGET_ZONE_COUNT,
        "target_repair_base": TARGET_REPAIR_BASE,
        "target_seeds": TARGET_SEEDS,
        "maximum_prior_layout_labels": MAXIMUM_PRIOR_LAYOUT_LABELS,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "maximum_no_prior_labels_per_occurrence": MAXIMUM_NO_PRIOR_LABELS_PER_OCCURRENCE,
        "minimum_reused_factor_count": MINIMUM_REUSED_FACTOR_COUNT,
        "historical_factor_prior_labels": HISTORICAL_FACTOR_PRIOR_LABELS,
        "maximum_registered_break_even_occurrences": MAXIMUM_REGISTERED_BREAK_EVEN_OCCURRENCES,
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.factor_prior_acquisition_ablation_preregistration.v52",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v51_evidence_commit": V51_EVIDENCE_COMMIT,
            "v51_campaign_id": V51_CAMPAIGN_ID,
            "v51_campaign_sha256": V51_CAMPAIGN_SHA256,
            "v51_verification_id": V51_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_composed_program_id": V51_FACTOR_COMPOSED_PROGRAM_ID,
            "v51_reused_factor_count": MINIMUM_REUSED_FACTOR_COUNT,
            "all_v51_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v52_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": set(
                DEVELOPMENT_SEEDS
            ).isdisjoint(TARGET_SEEDS),
        },
        "target_domain": {
            "family": "STOCHASTIC_MAINTENANCE_CASCADE",
            "ground_semantics_distinct_from_v51_coupled_exchange": True,
            "raw_state_width": 10,
            "raw_action_field_width": 6,
            "zone_count": TARGET_ZONE_COUNT,
            "repair_base": TARGET_REPAIR_BASE,
            "target_seeds": list(TARGET_SEEDS),
            "semantic_bridge_available_to_constructor": False,
            "generation_witness_available_to_constructor": False,
        },
        "matched_acquisition_arms": {
            "arms": [
                "FACTOR_COMPOSED_WORLD_MODEL_PRIOR",
                "STRICT_WITNESS_BLIND_EXACT_ACQUISITION_NO_PRIOR",
            ],
            "same_ground_kernel_seed_initial_state_and_outcome_tape_schedule": True,
            "prior_arm_receives_only_frozen_v51_anonymous_program_and_provenance": True,
            "no_prior_arm_factor_library_access_forbidden": True,
            "no_prior_arm_compiled_prior_access_forbidden": True,
            "no_prior_policy": "WITNESS_BLIND_EXHAUSTIVE_REACHABLE_STATE_ACTION_SUPPORT",
            "maximum_no_prior_labels_per_occurrence": MAXIMUM_NO_PRIOR_LABELS_PER_OCCURRENCE,
        },
        "prior_acquisition_and_recovery": {
            "layout_policy": "WITNESS_BLIND_BFS_UNTIL_TWO_CONSECUTIVE_IDENTICAL_MINIMUM_GRAPH_MATCHES",
            "maximum_layout_labels_per_occurrence": MAXIMUM_PRIOR_LAYOUT_LABELS,
            "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
            "local_ground_distinction_only_after_failed_certificate": True,
            "immutable_overlay_reused_across_registered_occurrences": True,
        },
        "sample_tax_contract": {
            "historical_v50_source_labels": 370,
            "v51_new_domain_source_labels": 213,
            "historical_factor_prior_labels": HISTORICAL_FACTOR_PRIOR_LABELS,
            "historical_prior_cost_included_before_first_target_occurrence": True,
            "target_acquisition_labels_counted_once_per_state_action_support": True,
            "execution_steps_not_counted_as_acquisition_labels": True,
            "planning_and_certificate_compute_not_counted_as_acquisition_labels": True,
            "maximum_registered_break_even_occurrences": MAXIMUM_REGISTERED_BREAK_EVEN_OCCURRENCES,
            "individual_factor_only_causal_effect_claimed": False,
            "causal_contrast": "FULL_FACTOR_COMPOSED_WORLD_MODEL_PRIOR_PIPELINE_VS_NO_PRIOR_EXACT_ACQUISITION",
        },
        "required_positive_conditions": [
            "ALL_MATCHED_HELD_OUT_OCCURRENCES_SUCCEED_IN_BOTH_ARMS",
            "NO_PRIOR_ARM_READS_NEITHER_FACTOR_LIBRARY_NOR_COMPILED_PRIOR",
            "EVERY_LOCAL_GROUND_DISTINCTION_FOLLOWS_A_FAILED_CERTIFICATE",
            "HISTORICAL_FACTOR_PRIOR_LABELS_INCLUDED_IN_CUMULATIVE_CURVE",
            "FACTOR_PRIOR_CUMULATIVE_LABELS_BELOW_NO_PRIOR_CUMULATIVE_LABELS",
            "REGISTERED_BREAK_EVEN_WITHIN_FROZEN_OCCURRENCE_HORIZON",
            "SAMPLE_EXECUTION_PLANNING_AND_CERTIFICATE_AXES_REMAIN_SEPARATE",
        ],
        "claim_boundary": {
            "matched_factor_composed_prior_pipeline_ablation": True,
            "individual_factor_only_causal_effect_claimed": False,
            "arbitrary_domain_or_schema_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "future_content_domains": dict(FUTURE_DOMAINS),
        "fresh_v52_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": content_id(FUTURE_DOMAINS["preregistration"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FactorPriorAblationPreregistrationV52:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V52 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V52 preregistration canonical bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            document.get("preregistration_id") != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V52 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_factor_prior_ablation_preregistration_v52() -> FactorPriorAblationPreregistrationV52:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V52 preregistration changed")
    return FactorPriorAblationPreregistrationV52(_ISSUER, raw, identity)


def verify_factor_prior_ablation_preregistration_v52(
    value: FactorPriorAblationPreregistrationV52,
) -> FactorPriorAblationPreregistrationV52:
    if type(value) is not FactorPriorAblationPreregistrationV52:
        _fail("V52 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_factor_prior_ablation_preregistration_v52()
    if value.canonical_bytes != expected.canonical_bytes:
        _fail("V52 preregistration semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FactorPriorAblationPreregistrationV52",
    "FUTURE_DOMAINS",
    "PREREGISTRATION_ID",
    "campaign_config_v52",
    "freeze_factor_prior_ablation_preregistration_v52",
    "verify_factor_prior_ablation_preregistration_v52",
)
