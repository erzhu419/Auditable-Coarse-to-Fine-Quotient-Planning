"""Outcome-free preregistration for fresh V70 role-free transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v70 as domains
from acfqp import construction_k7_source_complete_relational_preregistration_v69 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.role_free_relational_transfer_campaign_core_v70 import (
    build_role_free_relational_transfer_campaign_document_v70,
)


IMPLEMENTATION_COMMIT = "0717146"
PREREGISTRATION_ID = "394711e2323dff214f3a78241b9549d4a8af4e1877cde6530ab91740982b82e6"
EXPECTED_CANONICAL_BYTE_COUNT = 4_953
EXPECTED_CANONICAL_SHA256 = "b2ca66a6edc3a6b94fb89b0be1229b4178c6a2319fe7b41c697e244a379d26ed"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V69_CAMPAIGN_ID = "3a7655580b14f00a6833599f676c7b03719ae59cb5c48d2677545b47e38ad7a8"
V69_VERIFICATION_ID = "3c67ad21d01897448aa5a60c7fe4d802f2b1f477761451dc801e1b270c31d3ed"
TEMPLATE_LIBRARY_ARTIFACT_ID = "8657115a19bace2861b3a14ff780a2708b6e76101a2b7468e52e5285a113b2a9"
BALANCED_TARGET_SEEDS = (711_101, 711_102)
COUPLED_TARGET_SEEDS = (712_101, 712_102)
MAINTENANCE_TARGET_SEEDS = (713_101, 713_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/role_free_relational_transfer_campaign_core_v70.py",
    "src/acfqp/generic_role_free_relational_world_model_planner_v34.py",
    "src/acfqp/generic_role_free_relational_template_v33.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/generic_relational_residual_abstract_planner_v29.py",
    "src/acfqp/construction_k7_role_free_relational_template_library_v70.py",
)


class ConstructionK7RoleFreeRelationalTransferPreregistrationV70Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RoleFreeRelationalTransferPreregistrationV70Error(message)


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


def campaign_config_v70() -> dict[str, Any]:
    config = previous.campaign_config_v69()
    target_seeds = {
        "BALANCED_BATCH_REFINEMENT": BALANCED_TARGET_SEEDS,
        "COUPLED_EXCHANGE": COUPLED_TARGET_SEEDS,
        "MAINTENANCE_CASCADE": MAINTENANCE_TARGET_SEEDS,
    }
    for family, seeds in target_seeds.items():
        config["families"][family]["target_seeds"] = seeds
    config.update(
        target_seeds=target_seeds,
        target_occurrence_count=TARGET_OCCURRENCE_COUNT,
        worker_count=WORKER_COUNT,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
        residual_confidence_denominator=64,
        maximum_terminal_program_candidates_to_try=32,
        maximum_relational_support_branch_evaluations=1_000_000,
        relational_support_feasible_beam_width=32,
        offline_library_labels=204,
    )
    return config


def _document() -> dict[str, Any]:
    all_seeds = (
        BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    )
    payload = {
        "schema": "acfqp.role_free_relational_transfer_preregistration.v70",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v69_campaign_id": V69_CAMPAIGN_ID,
            "v69_verification_id": V69_VERIFICATION_ID,
            "template_library_artifact_id": TEMPLATE_LIBRARY_ARTIFACT_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v70_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V70),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_role_free_relational_transfer_campaign_document_v70
            ),
            "frozen_before_any_registered_v70_target_outcome": True,
        },
        "target_families": {
            "BALANCED_BATCH_REFINEMENT": {
                "target_seeds": list(BALANCED_TARGET_SEEDS)
            },
            "COUPLED_EXCHANGE": {"target_seeds": list(COUPLED_TARGET_SEEDS)},
            "MAINTENANCE_CASCADE": {
                "target_seeds": list(MAINTENANCE_TARGET_SEEDS)
            },
            "target_occurrence_count": TARGET_OCCURRENCE_COUNT,
            "fresh_and_identity_disjoint": len(all_seeds) == len(set(all_seeds))
            and min(all_seeds) > 710_000,
        },
        "registered_gate": {
            "required_relation": (
                "TRANSFER_PLAN_GT_ZERO_AND_ALL_INCOMPATIBLE_SCHEMA_OOD_REJECTED"
            ),
            "transfer_outperform_strict_required": False,
            "target_label_reduction_required": False,
        },
        "matched_transfer_contract": {
            "same_target_rows_residual_support_and_planner_caps_between_arms": True,
            "only_switched_variable": (
                "TERMINAL_PROGRAM_SOURCE_ROLE_FREE_LIBRARY_VS_TARGET_EXACT_CONTEXT"
            ),
            "target_observation_exactness_required_before_transfer_planning": True,
            "incompatible_schema_receives_no_template": True,
            "online_transfer_planner_integrated": False,
        },
        "safety_contract": {
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "transferred_abstract_plan_safety_authority": False,
            "future_unseen_dynamics_authority_present": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_relational_support_branch_evaluations": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_template_source_labels_separate": True,
            "offline_residual_library_labels_separate": True,
            "target_partial_and_certificate_labels_separate": True,
            "target_execution_steps_separate": True,
            "online_planning_compute_separate": True,
            "transfer_binding_compute_separate": True,
            "matched_transfer_and_strict_abstract_compute_separate": True,
        },
        "claim_boundary": {
            "registered_target_outcome_observed": False,
            "producer_free_verification_present": False,
            "online_transfer_planner_integrated": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_target_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v70(
            domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_PREREGISTRATION_V70_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RoleFreeRelationalTransferPreregistrationV70:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value for key, value in document.items() if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v70(
                domains.CONSTRUCTION_K7_ROLE_FREE_RELATIONAL_PREREGISTRATION_V70_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V70 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: RoleFreeRelationalTransferPreregistrationV70 | None = None


def freeze_role_free_relational_transfer_preregistration_v70() -> RoleFreeRelationalTransferPreregistrationV70:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V70 preregistration changed")
    if _CACHE is None:
        _CACHE = RoleFreeRelationalTransferPreregistrationV70(_ISSUER, raw, identity)
    return _CACHE


def verify_role_free_relational_transfer_preregistration_v70(
    value: Any,
) -> RoleFreeRelationalTransferPreregistrationV70:
    if type(value) is not RoleFreeRelationalTransferPreregistrationV70:
        _fail("V70 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_role_free_relational_transfer_preregistration_v70()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V70 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V69_CAMPAIGN_ID",
    "V69_VERIFICATION_ID",
    "TEMPLATE_LIBRARY_ARTIFACT_ID",
    "campaign_config_v70",
    "freeze_role_free_relational_transfer_preregistration_v70",
    "verify_role_free_relational_transfer_preregistration_v70",
)
