"""Outcome-free V48 registration for template-free cross-domain synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp.generic_template_free_world_model_v3 import (
    GENERIC_TYPES_V3,
    generic_opcode_documents_v3,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_TEMPLATE_FREE_ADAPTIVE_ACQUISITION_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_CAMPAIGN_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_DEPENDENCY_SUPPORT_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_LOCAL_DISTINCTION_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_OOD_REJECTION_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_PARTIAL_DYNAMICS_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_PREREGISTRATION_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_RAW_OBSERVATION_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_RECEDING_EPISODE_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_SAMPLE_TAX_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_TYPED_AST_PROGRAM_V48_DOMAIN,
    CONSTRUCTION_K7_TEMPLATE_FREE_VERIFICATION_V48_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "48.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.214"
PROFILE_KEY = "construction_k7_template_free_cross_domain_v48"
PREREGISTRATION_ID = "55f7a36ccb04361d377570cc6d3681b444be37705a0bbb5ae2b68fb41a88b79e"
EXPECTED_CANONICAL_BYTE_COUNT = 7012
EXPECTED_CANONICAL_SHA256 = "47c78b5802cf6b1f6c73d8ad61fdade3366fd338bb0f1aef70d5128fab19ca81"

V47_PREREGISTRATION_ID = "feeaa6e1337181e2d4489a9fddaf1bec912984d05cd02727e2c930d084cee177"
V47_FAILURE_ID = "93c13b08b8044ada9f7bca3b3f3c1972996ca0bf7b4a7ce865d691f497c692f0"
V47R1_PREREGISTRATION_ID = "2ad2e7a2409ed1d025b9659973115e8489266bb196db049a6340ba1f22e32ae8"
V47R1_CAMPAIGN_ID = "ec34a6a4d77e5ea8f1bb5483f0b78eaa0168a1aae302dad2cb9cc0475679fe7a"
V47R1_VERIFICATION_ID = "57027df9ed5cbb02d044b3a38d8c4f53ecb38f00fdb26c15bc9c8cbbe5cab0b1"

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/generic_template_free_world_model_v3.py",
    "src/acfqp/domains/matching_buffer.py",
    "src/acfqp/domains/stochastic_routing.py",
    "src/acfqp/domains/modular_walk.py",
)

LMB_SOURCE_SPEC = {"tile_count": 18, "type_count": 6, "capacity": 6, "max_layers": 4}
LMB_SOURCE_SEEDS = (481101, 481102, 481103)
LMB_TARGET_SPEC = {"tile_count": 21, "type_count": 7, "capacity": 7, "max_layers": 5}
LMB_TARGET_SEEDS = (481301, 481302, 481303, 481304)

ROUTING_SOURCE_SPEC = {"node_count": 8, "capacity": 10}
ROUTING_SOURCE_SEEDS = (482101, 482102, 482103)
ROUTING_SOURCE_EPISODES_PER_SEED = 8
ROUTING_TARGET_SPEC = {"node_count": 10, "capacity": 13}
ROUTING_TARGET_SEEDS = (482301, 482302, 482303, 482304)

MODULAR_SOURCE_SPEC = {
    "node_count": 6,
    "modulus": 7,
    "step_limit": 7,
    "mode_deltas": (1, 2, 3),
}
MODULAR_SOURCE_SEEDS = (483101, 483102, 483103)
MODULAR_TARGET_SPEC = {
    "node_count": 7,
    "modulus": 7,
    "step_limit": 8,
    "mode_deltas": (1, 2, 3, 4),
}
MODULAR_TARGET_SEEDS = (483301, 483302, 483303, 483304, 483305, 483306)
SHARED_MODE_TOKENS = (7_001, 7_003, 7_009, 7_013)

MAX_SOURCE_LABELS_PER_FAMILY = 256
RECEDING_HORIZON = 4
ARMS = ("COMPOSED_STRUCTURAL_PRIOR", "STRICT_EXACT_CONTEXT")
FLAT_LAYOUT_SALT = 0x481A
ACTION_FIELD_SALT = 0x481B

FUTURE_DOMAINS = {
    "preregistration": CONSTRUCTION_K7_TEMPLATE_FREE_PREREGISTRATION_V48_DOMAIN,
    "observation": CONSTRUCTION_K7_TEMPLATE_FREE_RAW_OBSERVATION_V48_DOMAIN,
    "program": CONSTRUCTION_K7_TEMPLATE_FREE_TYPED_AST_PROGRAM_V48_DOMAIN,
    "support": CONSTRUCTION_K7_TEMPLATE_FREE_DEPENDENCY_SUPPORT_V48_DOMAIN,
    "distinction": CONSTRUCTION_K7_TEMPLATE_FREE_LOCAL_DISTINCTION_V48_DOMAIN,
    "episode": CONSTRUCTION_K7_TEMPLATE_FREE_RECEDING_EPISODE_V48_DOMAIN,
    "partial": CONSTRUCTION_K7_TEMPLATE_FREE_PARTIAL_DYNAMICS_V48_DOMAIN,
    "acquisition": CONSTRUCTION_K7_TEMPLATE_FREE_ADAPTIVE_ACQUISITION_V48_DOMAIN,
    "sample_tax": CONSTRUCTION_K7_TEMPLATE_FREE_SAMPLE_TAX_V48_DOMAIN,
    "ood": CONSTRUCTION_K7_TEMPLATE_FREE_OOD_REJECTION_V48_DOMAIN,
    "campaign": CONSTRUCTION_K7_TEMPLATE_FREE_CAMPAIGN_V48_DOMAIN,
    "verification": CONSTRUCTION_K7_TEMPLATE_FREE_VERIFICATION_V48_DOMAIN,
}


class ConstructionK7TemplateFreePreregistrationV48Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7TemplateFreePreregistrationV48Error(message)


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


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.template_free_preregistration.v48",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessor": {
            "v47_preregistration_id": V47_PREREGISTRATION_ID,
            "v47_failure_id": V47_FAILURE_ID,
            "v47r1_preregistration_id": V47R1_PREREGISTRATION_ID,
            "v47r1_campaign_id": V47R1_CAMPAIGN_ID,
            "v47r1_verification_id": V47R1_VERIFICATION_ID,
            "all_predecessor_identities_preserved": True,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "frozen_before_any_v48_source_or_target_outcome": True,
        },
        "raw_interface": {
            "state": "OPAQUE_ORDERED_INTEGER_VECTOR",
            "action": "OPAQUE_KEY_PLUS_ANONYMOUS_INTEGER_FIELDS",
            "observation": [
                "PRE_VECTOR",
                "LEGAL_KEYS_BEFORE",
                "ACTION_KEY_AND_FIELDS",
                "POST_VECTOR",
                "LEGAL_KEYS_AFTER",
                "OPTIONAL_TAPE_SHA256",
            ],
            "domain_name_available_to_synthesizer": False,
            "semantic_state_or_action_names_available_to_synthesizer": False,
            "adapter_provided_abstract_state_present": False,
        },
        "typed_grammar": {
            "types": list(GENERIC_TYPES_V3),
            "opcodes": generic_opcode_documents_v3(),
            "whole_program_template_count": 0,
            "historical_complete_template_opcodes_available": [],
            "selection": "MIN_EXACT_RESIDUAL_THEN_TYPED_AST_MDL_THEN_CONTENT_HASH",
            "support_derivation": "EXACT_COMPILED_AST_DEPENDENCY_DELETION",
            "predeclared_semantic_support_names": [],
        },
        "fresh_workloads": {
            "D00": {
                "source_spec": LMB_SOURCE_SPEC,
                "source_seeds": list(LMB_SOURCE_SEEDS),
                "target_spec": LMB_TARGET_SPEC,
                "target_seeds": list(LMB_TARGET_SEEDS),
                "source_policy": "WITNESS_BLIND_ANONYMOUS_FIELD_COVERAGE_UNTIL_EXACT_AST",
            },
            "D01": {
                "source_spec": ROUTING_SOURCE_SPEC,
                "source_seeds": list(ROUTING_SOURCE_SEEDS),
                "source_episodes_per_seed": ROUTING_SOURCE_EPISODES_PER_SEED,
                "target_spec": ROUTING_TARGET_SPEC,
                "target_seeds": list(ROUTING_TARGET_SEEDS),
                "source_policy": "WITNESS_BLIND_LEAST_OBSERVED_FIELD_TUPLE_UNTIL_SUPPORT_CLOSED",
                "exact_probability_authority_claimed": False,
            },
            "D02": {
                "source_spec": {
                    **MODULAR_SOURCE_SPEC,
                    "mode_deltas": list(MODULAR_SOURCE_SPEC["mode_deltas"]),
                },
                "source_seeds": list(MODULAR_SOURCE_SEEDS),
                "target_spec": {
                    **MODULAR_TARGET_SPEC,
                    "mode_deltas": list(MODULAR_TARGET_SPEC["mode_deltas"]),
                },
                "target_seeds": list(MODULAR_TARGET_SEEDS),
                "source_policy": "WITNESS_BLIND_REACHABLE_FRONTIER_RELATION_COVERAGE",
                "shared_anonymous_mode_tokens": list(SHARED_MODE_TOKENS),
                "held_out_mode_token": SHARED_MODE_TOKENS[-1],
                "held_out_mode_absent_from_all_source_outcomes": True,
            },
            "maximum_source_labels_per_family": MAX_SOURCE_LABELS_PER_FAMILY,
            "all_source_and_target_seed_identities_fresh_after_v47r1": True,
        },
        "protocol": {
            "arms": list(ARMS),
            "receding_horizon": RECEDING_HORIZON,
            "planner_consumes_compiled_world_model_only": True,
            "kernel_transition_during_structural_planning_forbidden": True,
            "local_ground_label_only_after_failed_certificate": True,
            "held_out_D02_mode_requires_failed_certificate_before_query": True,
            "immutable_overlay_reused_across_later_D02_occurrences": True,
            "strict_control": "GROUND_QUERY_EACH_NEW_EXACT_STATE_ACTION_CONTEXT",
            "strict_ood_schema": "OPAQUE_CONTINUOUS_REAL_VECTOR",
            "strict_ood_prior_and_outcome_access": False,
        },
        "accounting": {
            "offline_source_labels": "SEPARATE_AXIS",
            "target_local_labels": "SEPARATE_AXIS",
            "execution_steps": "SEPARATE_AXIS",
            "synthesis_compute": "SEPARATE_AXIS",
            "planning_compute": "SEPARATE_AXIS",
            "certificate_compute": "SEPARATE_AXIS",
            "peak_cache": "SEPARATE_AXIS",
            "positive_sample_tax_condition": "SOURCE_PLUS_STRUCTURAL_TARGET_LABELS_LT_STRICT_TARGET_LABELS",
            "diagnostic_break_even_only": True,
        },
        "required_positive_conditions": [
            "THREE_DISTINCT_TYPED_ASTS_SYNTHESIZED_WITH_ZERO_WHOLE_PROGRAM_TEMPLATES",
            "THIRD_DOMAIN_REQUIRES_NEW_OPCODE_COMPOSITION",
            "PLANNER_CONSUMES_COMPILED_AST_NOT_TYPED_ADAPTER_ABSTRACTION",
            "FAILED_CERTIFICATE_PRECEDES_EVERY_LOCAL_GROUND_LABEL",
            "D02_HELD_OUT_RELATION_IS_LEARNED_ONCE_AND_OVERLAY_REUSED",
            "MATCHED_TOTAL_REGISTERED_LABEL_AXIS_BEATS_STRICT_CONTROL",
            "STRICT_OOD_NO_TRANSFER_NO_OUTCOME",
            "PRODUCER_FREE_RECONSTRUCTION_PASSES",
        ],
        "outcome_fields_present": False,
        "fresh_v48_outcome_execution_performed": False,
        "campaign_artifact_issued": False,
        "sample_tax_result_issued": False,
        "broad_world_model_synthesis_claimed": False,
        "broad_cross_domain_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "future_content_domains": FUTURE_DOMAINS,
    }
    return {
        **payload,
        "template_free_preregistration_id": content_id(
            FUTURE_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TemplateFreePreregistrationV48:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V48 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V48 preregistration bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "template_free_preregistration_id"
        }
        if (
            document.get("template_free_preregistration_id")
            != self.preregistration_id
            or content_id(FUTURE_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V48 preregistration identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


def freeze_template_free_preregistration_v48() -> TemplateFreePreregistrationV48:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["template_free_preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V48 preregistration changed")
    return TemplateFreePreregistrationV48(_ISSUER, raw, identity)


def verify_template_free_preregistration_v48(
    value: TemplateFreePreregistrationV48,
) -> TemplateFreePreregistrationV48:
    if type(value) is not TemplateFreePreregistrationV48:
        _fail("V48 preregistration rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V48 preregistration semantics changed")
    return value


__all__ = (
    "ACTION_FIELD_SALT",
    "ARMS",
    "BOUND_SOURCE_PATHS",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FLAT_LAYOUT_SALT",
    "FUTURE_DOMAINS",
    "LMB_SOURCE_SEEDS",
    "LMB_SOURCE_SPEC",
    "LMB_TARGET_SEEDS",
    "LMB_TARGET_SPEC",
    "MAX_SOURCE_LABELS_PER_FAMILY",
    "MODULAR_SOURCE_SEEDS",
    "MODULAR_SOURCE_SPEC",
    "MODULAR_TARGET_SEEDS",
    "MODULAR_TARGET_SPEC",
    "PREREGISTRATION_ID",
    "RECEDING_HORIZON",
    "ROUTING_SOURCE_EPISODES_PER_SEED",
    "ROUTING_SOURCE_SEEDS",
    "ROUTING_SOURCE_SPEC",
    "ROUTING_TARGET_SEEDS",
    "ROUTING_TARGET_SPEC",
    "SHARED_MODE_TOKENS",
    "TemplateFreePreregistrationV48",
    "freeze_template_free_preregistration_v48",
    "verify_template_free_preregistration_v48",
)
