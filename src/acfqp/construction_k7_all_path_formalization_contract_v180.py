"""Outcome-free contract for all-path accounting and economics formalization.

V179 completed the registered finite scientific objective.  V180 is a fresh,
non-retroactive successor: it fixes what must be observed before any global
Counter Completeness, economics, scalar, break-even, or official-execution
claim can be emitted.  It performs no terminal execution and reads no V180
outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_domain_registry_extension_v180 as domains
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.routing_v1 import TerminalCode


V179_COMPLETION_AUDIT_ID = (
    "373e67b24f19b130f556fbf5249b5661c27430a2f1ff15bc12dadb38d7238561"
)
V179_COMPLETION_VERIFICATION_ID = (
    "56fb4630b23cdfa0e28effaccaaabe30ddf8c9e18a40575ec30049fcabe9a3c9"
)
EXPECTED_CONTRACT_ID = "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
EXPECTED_CANONICAL_BYTE_COUNT = 3_250
EXPECTED_CANONICAL_SHA256 = "ca8f71df17e7e8d13e70b8cabf234e4d5d1c34bdbf65ed87b67ed9a98be610f9"


def _authority_ids() -> dict[str, str]:
    registry = registry_v9.official_counter_registry_v9()
    stage = registry_v9.official_stage_profile_v9(registry)
    comparison = registry_v9.official_comparison_profile_v9(registry)
    projection = registry_v9.official_actual_projection_profile_v9(
        registry, comparison
    )
    return {
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": projection.actual_projection_profile_id,
    }


def build_all_path_formalization_contract_v180() -> dict[str, Any]:
    authorities = _authority_ids()
    payload = {
        "schema": "acfqp.all_path_formalization_contract.v180",
        "predecessor": {
            "v179_completion_audit_id": V179_COMPLETION_AUDIT_ID,
            "v179_completion_verification_id": V179_COMPLETION_VERIFICATION_ID,
            "registered_finite_central_objective_completed": True,
            "v179_bytes_or_claims_mutated": False,
        },
        "accounting_authorities": {
            **authorities,
            "registry_version": "9.0.0",
            "registered_leaf_count": registry_v9.EXPECTED_V9_LEAF_COUNT,
            "required_leaf_count_per_vector": (
                registry_v9.EXPECTED_V9_REQUIRED_LEAF_COUNT
            ),
            "operational_leaf_count": registry_v9.EXPECTED_V9_OPERATIONAL_LEAF_COUNT,
            "all_required_native_zero_values_must_be_explicit": True,
            "nine_shared_resource_receipts_required_per_execution_window": True,
            "output_bytes_exact_fixed_point_required": True,
        },
        "terminal_coverage_contract": {
            "terminal_codes": [code.value for code in TerminalCode],
            "terminal_code_count": len(TerminalCode),
            "route_kinds": [route.value for route in RouteKindEnum],
            "route_kind_count": len(RouteKindEnum),
            "fresh_observed_occurrence_required_for_every_terminal_code": True,
            "success_fallback_ood_and_failure_paths_must_be_present": True,
            "counter_record_work_vector_comparison_vector_chain_required": True,
            "campaign_orchestration_work_vector_required": True,
            "failure_prefix_work_must_be_retained": True,
            "local_failure_and_fallback_vectors_must_remain_distinct": True,
            "producer_free_bytes_reconstruction_required": True,
            "historical_summary_to_counter_translation_forbidden": True,
        },
        "economics_protocol": {
            "primary_authority": "EXACT_WEIGHT_AGNOSTIC_WORK_VECTOR",
            "componentwise_dominance_and_pareto_report_required": True,
            "sample_labels_execution_steps_and_compute_axes_separate": True,
            "diagnostic_unit_work_v1_may_be_reported": True,
            "diagnostic_unit_work_v1_is_official_scalar": False,
            "official_scalar_requires_separate_preoutcome_calibration": True,
            "official_scalar_calibration_present_in_this_contract": False,
            "paired_wall_time_role": "DIAGNOSTIC_ONLY_UNTIL_REFERENCE_PROFILE",
            "reference_machine_profile_frozen": False,
            "outcome_selected_weights_forbidden": True,
        },
        "gate_order": [
            "ALL_PATH_PRODUCER_FREE_REPLAY",
            "COUNTER_COMPLETENESS_GATE",
            "WEIGHT_AGNOSTIC_WORKLOAD_ECONOMICS_GATE",
            "SEPARATELY_PREREGISTERED_SCALAR_GATE",
            "OFFICIAL_EXECUTION_GATE",
        ],
        "claim_locks": {
            "v180_terminal_outcomes_accessed": False,
            "all_path_native_accounting_complete": False,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "complete_ground_world_model_synthesized": False,
            "open_ended_world_model_invention_claimed": False,
            "arbitrary_unseen_domain_transfer_claimed": False,
            "broad_iid_sample_efficiency_claimed": False,
        },
    }
    return {
        **payload,
        "formalization_contract_id": domains.extension_content_id_v180(
            domains.CONSTRUCTION_K7_FORMALIZATION_CONTRACT_V180_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class AllPathFormalizationContractV180:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    formalization_contract_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_all_path_formalization_contract_v180() -> AllPathFormalizationContractV180:
    document = build_all_path_formalization_contract_v180()
    raw = canonical_json_bytes(document)
    if EXPECTED_CONTRACT_ID != "0" * 64 and not (
        document["formalization_contract_id"] == EXPECTED_CONTRACT_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180 frozen all-path formalization contract changed")
    return AllPathFormalizationContractV180(
        _ISSUER,
        raw,
        document["formalization_contract_id"],
    )


__all__ = (
    "EXPECTED_CONTRACT_ID",
    "freeze_all_path_formalization_contract_v180",
)
