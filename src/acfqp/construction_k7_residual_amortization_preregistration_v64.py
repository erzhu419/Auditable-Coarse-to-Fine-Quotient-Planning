"""Outcome-free preregistration for the fresh V64 amortization campaign."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v63r1 as procedure_domains
from acfqp import construction_k7_domain_registry_extension_v64 as domains
from acfqp import construction_k7_true_bit_symmetric_preregistration_v59 as previous
from acfqp.residual_prior_amortization_campaign_core_v64 import (
    build_residual_prior_amortization_campaign_document_v64,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


IMPLEMENTATION_COMMIT = "8124b0d"
PREREGISTRATION_ID = "00ce3d9d8979bb94c42378eb6acf0fbec0238f6eb34868cd3d7bc0df2dcd329c"
EXPECTED_CANONICAL_BYTE_COUNT = 5_228
EXPECTED_CANONICAL_SHA256 = "4f66aaa5b1d6eef33048e4a687ff126257606990df4bef1cbc7b47fff7cf282a"
FAILED_V63_ID = "716b0fba8968318c284a0840e2f109c861f819d5c52a177fdd41efee88c2fae0"
V62_LIBRARY_ID = "26e5e031eb6b57e73253bc85bc3d0c372f6444248ad0c4e3343a01f43353b3d0"
V63R1_CAMPAIGN_ID = "1e9f4fbdb13e9c7c477ec213fec3d0cda09d4b0af7698d8c7e774ebdbf320db8"
V63R1_VERIFICATION_ID = "9dcfc9aa1e363d13ea6f32f0208048657acd4428e6c65d48a3c434b45e531b2c"
BALANCED_TARGET_SEEDS = tuple(range(651_101, 651_125))
COUPLED_TARGET_SEEDS = tuple(range(652_101, 652_125))
MAINTENANCE_TARGET_SEEDS = tuple(range(653_101, 653_125))
WORKER_COUNT = 12
TARGET_OCCURRENCE_COUNT = 72
SOURCE_ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v64.py",
    "src/acfqp/residual_prior_amortization_campaign_core_v64.py",
    "src/acfqp/construction_k7_domain_registry_extension_v63r1.py",
    "src/acfqp/generic_adaptive_residual_factor_acquisition_v19.py",
    "src/acfqp/generic_total_adaptive_residual_acquisition_v20.py",
    "src/acfqp/total_residual_sample_tax_campaign_core_v63r1.py",
)
V64_DOMAINS = {
    "preregistration": domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_PREREGISTRATION_V64_DOMAIN,
    "campaign": domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_CAMPAIGN_V64_DOMAIN,
    "verification": domains.CONSTRUCTION_K7_RESIDUAL_AMORTIZATION_VERIFICATION_V64_DOMAIN,
}
PROCEDURE_DOMAINS = {
    "raw_query_pool": procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_RAW_QUERY_POOL_V63R1_DOMAIN,
    "acquisition": procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_ACQUISITION_V63R1_DOMAIN,
    "safety_episode": procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SAFETY_EPISODE_V63R1_DOMAIN,
    "summary": procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_SUMMARY_V63R1_DOMAIN,
    "campaign": procedure_domains.CONSTRUCTION_K7_TOTAL_RESIDUAL_SAMPLE_TAX_CAMPAIGN_V63R1_DOMAIN,
}


class ConstructionK7ResidualAmortizationPreregistrationV64Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualAmortizationPreregistrationV64Error(message)


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


def campaign_config_v64() -> dict[str, Any]:
    config = previous.campaign_config_v59()
    for family, seeds in (
        ("BALANCED_BATCH_REFINEMENT", BALANCED_TARGET_SEEDS),
        ("COUPLED_EXCHANGE", COUPLED_TARGET_SEEDS),
        ("MAINTENANCE_CASCADE", MAINTENANCE_TARGET_SEEDS),
    ):
        config["families"][family]["target_seeds"] = seeds
    config.update(
        worker_count=WORKER_COUNT,
        maximum_partial_abstract_depth=12,
        maximum_partial_execution_steps=96,
        residual_confidence_denominator=64,
        v63r1_domains=dict(PROCEDURE_DOMAINS),
    )
    return config


def _document() -> dict[str, Any]:
    seeds = BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    payload = {
        "schema": "acfqp.residual_prior_amortization_preregistration.v64",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "failed_v63_id": FAILED_V63_ID,
            "v62_library_artifact_id": V62_LIBRARY_ID,
            "v63r1_campaign_id": V63R1_CAMPAIGN_ID,
            "v63r1_campaign_sha256": "02d2149b39043e28354dc57e36a03cc3905d8266dbf25015486c0bda0c220e29",
            "v63r1_verification_id": V63R1_VERIFICATION_ID,
            "v63r1_verification_sha256": "2b0ea9fb8253f2bc1ba21396cdac6174509cc8d960e18166c6dac312fe1b2f17",
            "v63r1_diagnostic_break_even_occurrence_count": 59,
        },
        "source_closure": {
            "source_facts": _source_facts(),
            "v64_domains": dict(V64_DOMAINS),
            "procedure_domains": dict(PROCEDURE_DOMAINS),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "campaign_builder_callable": _callable_fact(
                build_residual_prior_amortization_campaign_document_v64
            ),
            "frozen_before_any_registered_v64_outcome": True,
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
            "all_identities_disjoint_from_v63_and_v63r1": len(seeds)
            == len(set(seeds))
            and min(seeds) > 650_000,
        },
        "amortization_gate": {
            "offline_development_label_tax": 204,
            "target_occurrence_count": TARGET_OCCURRENCE_COUNT,
            "prior_lifetime_labels_formula": "204 + PRIOR_TARGET_RESIDUAL_LABELS",
            "strict_lifetime_labels_formula": "STRICT_TARGET_RESIDUAL_LABELS",
            "required_relation": "PRIOR_LIFETIME_LABELS_LE_STRICT_LIFETIME_LABELS",
            "positive_margin_required": False,
            "all_occurrences_and_family_projections_retained": True,
            "family_specific_positive_reduction_required": False,
        },
        "procedure_contract": {
            "exact_v63r1_matched_procedure_reused": True,
            "same_full_candidate_grammar": True,
            "only_switched_variable": "FROZEN_RESIDUAL_FACTOR_EXPRESSION_PRIOR_CODE_LENGTH",
            "typed_abstention_retained": True,
            "query_pool_exhaustion_used_as_positive_stop": False,
            "certificate_local_ground_recovery_only": True,
        },
        "resource_schedule": {
            "worker_count": WORKER_COUNT,
            "worker_count_frozen_cap": WORKER_COUNT,
            "outcome_execution_may_not_exceed_frozen_worker_count": True,
        },
        "accounting_contract": {
            "offline_target_execution_and_compute_axes_separate": True,
            "observed_amortization_is_sample_accounting_not_official_economics": True,
        },
        "claim_boundary": {
            "registered_outcome_observed": False,
            "producer_free_verification_present": False,
            "complete_residual_world_model_synthesized": False,
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
        "preregistration_id": domains.extension_content_id_v64(
            V64_DOMAINS["preregistration"], payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ResidualAmortizationPreregistrationV64:
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
            or domains.extension_content_id_v64(V64_DOMAINS["preregistration"], payload)
            != self.preregistration_id
        ):
            _fail("V64 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: ResidualAmortizationPreregistrationV64 | None = None


def freeze_residual_amortization_preregistration_v64() -> ResidualAmortizationPreregistrationV64:
    global _CACHE
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V64 preregistration changed")
    if _CACHE is None:
        _CACHE = ResidualAmortizationPreregistrationV64(_ISSUER, raw, identity)
    return _CACHE


def verify_residual_amortization_preregistration_v64(
    value: Any,
) -> ResidualAmortizationPreregistrationV64:
    if type(value) is not ResidualAmortizationPreregistrationV64:
        _fail("V64 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_residual_amortization_preregistration_v64()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V64 preregistration differs from frozen bytes")
    return value


__all__ = (
    "BOUND_SOURCE_PATHS",
    "PROCEDURE_DOMAINS",
    "V64_DOMAINS",
    "campaign_config_v64",
    "freeze_residual_amortization_preregistration_v64",
    "verify_residual_amortization_preregistration_v64",
)
