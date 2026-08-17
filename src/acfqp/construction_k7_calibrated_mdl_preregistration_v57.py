"""Outcome-free V57 registration for calibrated three-domain synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v57 as domains_v57
from acfqp import construction_k7_mdl_adaptive_preregistration_v56r1 as pre_v56r1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "57.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.229"
PROFILE_KEY = "construction_k7_calibrated_mdl_three_domain_v57"
PREREGISTRATION_ID = "2a2ecfb2c41165bea437f1f91b4114d1432e4e690e6bf2775a231b8d88ceb3fd"
EXPECTED_CANONICAL_BYTE_COUNT = 10_072
EXPECTED_CANONICAL_SHA256 = "d92224dfd30bb0cc0bf97cb3e9f2e0f9c4f7f74ab667c20d9a9fe79e6118e2a4"
IMPLEMENTATION_COMMIT = "00e7f05"

V56R1_CAMPAIGN_ID = (
    "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
)
V56R1_CAMPAIGN_SHA256 = (
    "67188187a8fcda709fdcd287d653c3140a7dcf40618b4588faae355ff761f3e5"
)
V56R1_VERIFICATION_ID = (
    "8aa9de632593f60ae8ac59cac3f0affa25568caf011211271913d8732e66733f"
)
V51_FACTOR_LIBRARY_ID = pre_v56r1.V51_FACTOR_LIBRARY_ID
FACTOR_LIBRARY_LABELS = pre_v56r1.FACTOR_LIBRARY_LABELS
FACTOR_LIBRARY = pre_v56r1.FACTOR_LIBRARY
TERMINAL_TOKENS = dict(pre_v56r1.TERMINAL_TOKENS)

BALANCED_TARGET_SEEDS = tuple(range(571_101, 571_133))
COUPLED_TARGET_SEEDS = tuple(range(572_101, 572_133))
MAINTENANCE_TARGET_SEEDS = tuple(range(573_101, 573_133))
DEVELOPMENT_SEEDS = (579_910, 579_911, 579_920, 579_921, 579_930, 579_931)
PLANNING_SEED_COUNT_PER_FAMILY = 4
WORKER_COUNT = 4
FACTOR_SIGNATURE_CREDIT_UNITS = 16
INVALIDATED_CANDIDATE_PENALTY_UNITS = 16
MINIMUM_REUSABLE_FACTOR_COUNT = 3
MAXIMUM_RELATION_OUTPUT_CANDIDATE = 64
MAXIMUM_LOCAL_RESYNTHESES = 8
GLOBAL_ALPHA_DENOMINATOR = 20
EPOCH_ALPHA_SPENDING_BASE = 2
SUCCESS_EVALUE_MULTIPLIER_NUMERATOR = 3
SUCCESS_EVALUE_MULTIPLIER_DENOMINATOR = 2
PREDICTIVE_EVIDENCE_CREDIT_UNITS_PER_BIT = 2

SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v57.py",
    "src/acfqp/generic_calibrated_mdl_joint_synthesizer_v12.py",
    "src/acfqp/calibrated_mdl_three_domain_campaign_core_v57.py",
    "src/acfqp/domains/stochastic_maintenance_cascade.py",
    *pre_v56r1.BOUND_SOURCE_PATHS,
)
FROZEN_V56_DOMAINS = dict(pre_v56r1.FROZEN_V56_DOMAINS)
SUCCESSOR_DOMAINS = {
    "preregistration": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_PREREGISTRATION_V57_DOMAIN
    ),
    "acquisition": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_ACQUISITION_V57_DOMAIN
    ),
    "sample_tax": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_SAMPLE_TAX_V57_DOMAIN
    ),
    "campaign": domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_CAMPAIGN_V57_DOMAIN,
    "verification": (
        domains_v57.CONSTRUCTION_K7_CALIBRATED_MDL_VERIFICATION_V57_DOMAIN
    ),
}
GENERIC_DOMAINS = dict(pre_v56r1.GENERIC_DOMAINS)


class ConstructionK7CalibratedMDLPreregistrationV57Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7CalibratedMDLPreregistrationV57Error(message)


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


def campaign_config_v57() -> dict[str, Any]:
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
            "MAINTENANCE_CASCADE": {
                "zone_count": 7,
                "repair_base": 2,
                "target_seeds": MAINTENANCE_TARGET_SEEDS,
                "planning_seed_count": PLANNING_SEED_COUNT_PER_FAMILY,
                "maximum_acquisition_labels": 200,
            },
        },
        "worker_count": WORKER_COUNT,
        "factor_signature_credit_units": FACTOR_SIGNATURE_CREDIT_UNITS,
        "invalidated_candidate_penalty_units": (
            INVALIDATED_CANDIDATE_PENALTY_UNITS
        ),
        "minimum_reusable_factor_count": MINIMUM_REUSABLE_FACTOR_COUNT,
        "maximum_relation_output_candidate": MAXIMUM_RELATION_OUTPUT_CANDIDATE,
        "maximum_local_resyntheses": MAXIMUM_LOCAL_RESYNTHESES,
        "global_alpha_denominator": GLOBAL_ALPHA_DENOMINATOR,
        "epoch_alpha_spending_base": EPOCH_ALPHA_SPENDING_BASE,
        "success_evalue_multiplier_numerator": (
            SUCCESS_EVALUE_MULTIPLIER_NUMERATOR
        ),
        "success_evalue_multiplier_denominator": (
            SUCCESS_EVALUE_MULTIPLIER_DENOMINATOR
        ),
        "predictive_evidence_credit_units_per_bit": (
            PREDICTIVE_EVIDENCE_CREDIT_UNITS_PER_BIT
        ),
        "factor_library_id": V51_FACTOR_LIBRARY_ID,
        "factor_library_labels": FACTOR_LIBRARY_LABELS,
        "v56r1_campaign_id": V56R1_CAMPAIGN_ID,
        "v56r1_verification_id": V56R1_VERIFICATION_ID,
    }


def _document() -> dict[str, Any]:
    registered = set(BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS)
    payload = {
        "schema": "acfqp.calibrated_mdl_preregistration.v57",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frozen_predecessors": {
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "v56r1_campaign_id": V56R1_CAMPAIGN_ID,
            "v56r1_campaign_sha256": V56R1_CAMPAIGN_SHA256,
            "v56r1_verification_id": V56R1_VERIFICATION_ID,
            "v51_factor_library_id": V51_FACTOR_LIBRARY_ID,
            "v51_factor_library_labels": FACTOR_LIBRARY_LABELS,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "successor_domains": dict(SUCCESSOR_DOMAINS),
            "unchanged_v56_subartifact_domains": dict(FROZEN_V56_DOMAINS),
            "generic_subartifact_domains": dict(GENERIC_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "frozen_before_any_v57_registered_outcome": True,
            "development_seed_identities_disjoint_from_registered_identities": (
                set(DEVELOPMENT_SEEDS).isdisjoint(registered)
            ),
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "raw_state_width": 6,
                "raw_action_field_width": 5,
                "target_seeds": list(BALANCED_TARGET_SEEDS),
            },
            "COUPLED_EXCHANGE": {
                "raw_state_width": 10,
                "raw_action_field_width": 6,
                "target_seeds": list(COUPLED_TARGET_SEEDS),
            },
            "MAINTENANCE_CASCADE": {
                "raw_state_width": 10,
                "raw_action_field_width": 6,
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS),
                "new_third_partial_stochastic_family": True,
            },
            "generation_witness_available_to_constructor": False,
            "semantic_bridge_available_to_constructor": False,
        },
        "calibrated_stopping_contract": {
            "candidate_frozen_before_each_scored_future_batch": True,
            "candidate_synthesis_attempted_after_every_support_query": True,
            "fixed_minimum_candidate_label_floor": None,
            "fixed_confirmation_block_size": None,
            "fixed_confidence_reserve": None,
            "reachable_frontier_exhaustion_stop_available": False,
            "predictive_null_success_probability_upper_bound": {
                "numerator": 1,
                "denominator": 2,
            },
            "success_evalue_multiplier": {"numerator": 3, "denominator": 2},
            "failure_evalue_multiplier": {"numerator": 1, "denominator": 2},
            "global_alpha": {"numerator": 1, "denominator": 20},
            "candidate_epoch_geometric_alpha_spending_base": 2,
            "stop_requires_exact_replay_evalue_threshold_and_nonnegative_"
            "combined_mdl_predictive_margin": True,
            "anytime_valid_for_registered_predictive_null": True,
            "distribution_free_global_dynamics_confidence_claimed": False,
        },
        "matched_single_switch_arms": {
            "arms": ["ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"],
            "same_synthesizer_query_order_mdl_and_eprocess": True,
            "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
            "factor_prior_on_code_credit_per_reusable_signature": 16,
            "factor_prior_off_code_credit": 0,
        },
        "planning_and_recovery": {
            "planning_seed_count_per_family": PLANNING_SEED_COUNT_PER_FAMILY,
            "receding_abstract_planning": True,
            "matched_direct_baseline_same_ground_kernel_and_objective": True,
            "identical_action_sequence_across_distinct_planners_required": False,
            "certificate_failure_before_every_local_ground_query": True,
            "counterexample_triggers_local_program_resynthesis": True,
        },
        "sample_tax_contract": {
            "registered_occurrence_count": len(registered),
            "factor_library_labels_charged_only_to_prior_on": FACTOR_LIBRARY_LABELS,
            "positive_incremental_reduction_required_in_each_family": True,
            "positive_online_and_lifetime_label_reduction_required": True,
            "all_accounting_axes_separate": True,
            "official_break_even_claimed": False,
        },
        "development_only": {
            "development_seeds": list(DEVELOPMENT_SEEDS),
            "factor_prior_on_acquisition_labels": 482,
            "strict_no_prior_acquisition_labels": 585,
            "incremental_reduction": 103,
            "temporary_factor_library_tax": 20,
            "lifetime_reduction": 83,
            "all_three_family_reductions_positive": True,
            "development_outcomes_not_registered_evidence": True,
        },
        "claim_boundary": {
            "v57_campaign_preregistered": True,
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
        "fresh_v57_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains_v57.extension_content_id_v57(
            SUCCESSOR_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CalibratedMDLPreregistrationV57:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V57 preregistration is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        payload = {key: value for key, value in document.items() if key != "preregistration_id"}
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains_v57.extension_content_id_v57(
                SUCCESSOR_DOMAINS["preregistration"], payload
            )
            != self.preregistration_id
        ):
            _fail("V57 preregistration bytes or identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: CalibratedMDLPreregistrationV57 | None = None


def freeze_calibrated_mdl_preregistration_v57() -> CalibratedMDLPreregistrationV57:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V57 preregistration changed")
    if _CACHE is None:
        _CACHE = CalibratedMDLPreregistrationV57(_ISSUER, raw, identity)
    return _CACHE


def verify_calibrated_mdl_preregistration_v57(
    value: Any,
) -> CalibratedMDLPreregistrationV57:
    if type(value) is not CalibratedMDLPreregistrationV57:
        _fail("V57 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_calibrated_mdl_preregistration_v57()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V57 preregistration does not match frozen bytes")
    return value


__all__ = (
    "FACTOR_LIBRARY",
    "FROZEN_V56_DOMAINS",
    "GENERIC_DOMAINS",
    "SUCCESSOR_DOMAINS",
    "CalibratedMDLPreregistrationV57",
    "campaign_config_v57",
    "freeze_calibrated_mdl_preregistration_v57",
    "verify_calibrated_mdl_preregistration_v57",
)
