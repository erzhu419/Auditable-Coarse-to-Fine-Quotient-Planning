"""Outcome-free preregistration for fresh V69 source-complete world models."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v69 as domains
from acfqp import construction_k7_relational_world_model_preregistration_v68 as previous
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.source_complete_relational_campaign_core_v69 import (
    build_source_complete_relational_campaign_document_v69,
)


IMPLEMENTATION_COMMIT = "ab6f0a7"
PREREGISTRATION_ID = "056f3a4caf03c2bba595af958b67e2f1d124766c767eabea24e9c3ac4ff916a5"
EXPECTED_CANONICAL_BYTE_COUNT = 5_040
EXPECTED_CANONICAL_SHA256 = "10e6db2d85a828b4925ac9bda5f79b798798002675c6fb820a5a633c583da71b"
V62_LIBRARY_ID = previous.V62_LIBRARY_ID
V68_CAMPAIGN_ID = "607e55ff4f745dee3f1ddf8fd8cccb76ffc1bf4f25f6df143a9b61a08c50a944"
V68_VERIFICATION_ID = "6581428db574418a770777f5df03afde2b9299348b3b06fe997d321a909acb87"
BALANCED_TARGET_SEEDS = (701_101, 701_102)
COUPLED_TARGET_SEEDS = (702_101, 702_102)
MAINTENANCE_TARGET_SEEDS = (703_101, 703_102)
WORKER_COUNT = 6
TARGET_OCCURRENCE_COUNT = 6
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v69.py",
    "src/acfqp/source_complete_relational_campaign_core_v69.py",
    "src/acfqp/generic_source_complete_relational_world_model_v31.py",
    "src/acfqp/generic_relational_terminal_program_independent_replay_v32.py",
    "src/acfqp/generic_relational_world_model_certificate_planner_v30.py",
    "src/acfqp/generic_relational_residual_abstract_planner_v29.py",
    "src/acfqp/generic_relational_terminal_program_v28.py",
    "src/acfqp/generic_batch_exact_multi_residual_compiler_v27.py",
)


class ConstructionK7SourceCompleteRelationalPreregistrationV69Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceCompleteRelationalPreregistrationV69Error(message)


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


def campaign_config_v69() -> dict[str, Any]:
    config = previous.campaign_config_v68()
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
        "schema": "acfqp.source_complete_relational_preregistration.v69",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v62_residual_library_id": V62_LIBRARY_ID,
            "v68_campaign_id": V68_CAMPAIGN_ID,
            "v68_verification_id": V68_VERIFICATION_ID,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v69_domains": dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V69),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_source_complete_relational_campaign_document_v69
            ),
            "frozen_before_any_registered_v69_outcome": True,
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
            and min(all_seeds) > 700_000,
        },
        "registered_gate": {
            "required_relation": (
                "PRIOR_PLAN_GT_ZERO_AND_ACTIVE_GT_ZERO_AND_ALL_SOURCE_COMPLETE"
            ),
            "prior_vs_strict_improvement_required": False,
            "certificate_local_label_reduction_required": False,
        },
        "source_complete_contract": {
            "common_partial_raw_rows_retained": True,
            "query_local_raw_rows_retained": True,
            "exact_ordered_union_retained": True,
            "independent_status_coordinate_rederivation_required": True,
            "independent_relation_feature_inventory_rederivation_required": True,
            "independent_decision_tree_frontier_rederivation_required": True,
            "v28_v30_imports_forbidden_in_independent_replay": True,
        },
        "safety_contract": {
            "every_unseen_ground_query_requires_prior_failed_certificate": True,
            "query_local_exact_overlay_exclusively_discharges_safety": True,
            "relational_abstract_plan_safety_authority": False,
            "empirical_support_promoted_to_global_exact_dynamics": False,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "maximum_terminal_program_candidates_to_try": 32,
            "maximum_relational_support_branch_evaluations": 1_000_000,
            "relational_support_feasible_beam_width": 32,
        },
        "accounting_contract": {
            "offline_and_common_partial_labels_separate": True,
            "prior_and_strict_certificate_local_labels_separate": True,
            "execution_steps_separate": True,
            "derivation_and_planning_compute_separate": True,
            "retained_source_rows_separate": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "producer_free_verification_present": False,
            "complete_world_model_synthesized": False,
            "global_exact_dynamics_claimed": False,
            "arbitrary_domain_transfer_claimed": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
        "fresh_registered_outcome_execution_performed": False,
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v69(
            domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_PREREGISTRATION_V69_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceCompleteRelationalPreregistrationV69:
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
            or domains.extension_content_id_v69(
                domains.CONSTRUCTION_K7_SOURCE_COMPLETE_RELATIONAL_PREREGISTRATION_V69_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V69 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SourceCompleteRelationalPreregistrationV69 | None = None


def freeze_source_complete_relational_preregistration_v69() -> SourceCompleteRelationalPreregistrationV69:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V69 preregistration changed")
    if _CACHE is None:
        _CACHE = SourceCompleteRelationalPreregistrationV69(_ISSUER, raw, identity)
    return _CACHE


def verify_source_complete_relational_preregistration_v69(
    value: Any,
) -> SourceCompleteRelationalPreregistrationV69:
    if type(value) is not SourceCompleteRelationalPreregistrationV69:
        _fail("V69 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_source_complete_relational_preregistration_v69()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V69 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "V62_LIBRARY_ID",
    "V68_CAMPAIGN_ID",
    "V68_VERIFICATION_ID",
    "campaign_config_v69",
    "freeze_source_complete_relational_preregistration_v69",
    "verify_source_complete_relational_preregistration_v69",
)
