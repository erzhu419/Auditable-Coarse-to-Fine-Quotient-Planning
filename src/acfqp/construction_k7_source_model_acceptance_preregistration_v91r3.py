"""Preregister the corrected, outcome-free V91r3 acceptance rule."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import marshal
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v91r3 as domains
from acfqp.construction_k7_prior_only_occurrence_source_campaign_v91r2 import (
    CAMPAIGN_ID as V91R2_CAMPAIGN_ID,
    EXPECTED_CANONICAL_SHA256 as V91R2_CAMPAIGN_SHA256,
)
from acfqp.construction_k7_prior_only_occurrence_source_independent_verifier_v91r2 import (
    EXPECTED_CANONICAL_SHA256 as V91R2_VERIFICATION_SHA256,
    VERIFICATION_ID as V91R2_VERIFICATION_ID,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from acfqp.source_model_acceptance_core_v91r3 import (
    build_source_model_acceptance_document_v91r3,
)


IMPLEMENTATION_COMMIT = "763f4d6"
PREREGISTRATION_ID = (
    "e1b7376e65f2c767e3c80db4eda9923f0e317612e3388663acf48e6a0dcb596d"
)
EXPECTED_CANONICAL_BYTE_COUNT = 2_973
EXPECTED_CANONICAL_SHA256 = (
    "7b5246661560248cea658da9560134b02ed64c6dfb51937409a1b26e57d87be0"
)
SOURCE_ROOT = Path(__file__).resolve().parents[2]
FROZEN_SOURCE_FACTS = (
    (
        "src/acfqp/construction_k7_domain_registry_extension_v91r3.py",
        1796,
        "7962a61881961f747d59ceb3b2f5342c9c3e18c26181685fee1d53d323b0075a",
    ),
    (
        "src/acfqp/source_model_acceptance_core_v91r3.py",
        4559,
        "20948fd88aac87e2208b8a6c56c98999c07afee3eaa851cbe006aff45afc7d27",
    ),
    (
        "src/acfqp/generic_joint_successor_version_space_planner_v42.py",
        36033,
        "d4b99c0f96688fc4d4dc4fae01a1d6896d254f166881ad5611c1e755c8bc1005",
    ),
)


class ConstructionK7SourceModelAcceptancePreregistrationV91R3Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SourceModelAcceptancePreregistrationV91R3Error(message)


def _source_facts() -> list[dict[str, Any]]:
    result = []
    for relative, _count, _digest in FROZEN_SOURCE_FACTS:
        raw = (SOURCE_ROOT / relative).read_bytes()
        result.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return result


def _frozen_source_facts() -> list[dict[str, Any]]:
    return [
        {"relative_path": path, "byte_count": count, "sha256": digest}
        for path, count, digest in FROZEN_SOURCE_FACTS
    ]


def _callable_fact(value: Any) -> dict[str, Any]:
    return {
        "module": value.__module__,
        "qualname": value.__qualname__,
        "code_sha256": hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
    }


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.source_model_acceptance_preregistration.v91r3",
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "frozen_predecessors": {
            "v91r2_campaign_id": V91R2_CAMPAIGN_ID,
            "v91r2_campaign_sha256": V91R2_CAMPAIGN_SHA256,
            "v91r2_verification_id": V91R2_VERIFICATION_ID,
            "v91r2_verification_sha256": V91R2_VERIFICATION_SHA256,
        },
        "source_closure": {
            "source_facts": _frozen_source_facts(),
            "v91r3_domains": dict(
                domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V91R3
            ),
            "canonicalizer_callable": _callable_fact(canonical_json_bytes),
            "acceptance_builder_callable": _callable_fact(
                build_source_model_acceptance_document_v91r3
            ),
            "frozen_before_acceptance_construction": True,
        },
        "corrected_gate_contract": {
            "every_observation_consistent_residual_candidate_must_be_retained": True,
            "nonempty_residual_version_space_required": True,
            "multiplicity_required_only_when_supported_by_observations": True,
            "singleton_version_space_is_not_a_failure": True,
            "synthetic_or_duplicate_uncertainty_forbidden": True,
            "v91r2_failure_preserved_without_reinterpretation": True,
        },
        "execution_contract": {
            "new_source_outcomes_forbidden": True,
            "new_target_outcomes_forbidden": True,
            "only_frozen_v91r2_bytes_may_be_consumed": True,
            "accepted_model_remains_proposal_not_safety_authority": True,
        },
        "claim_boundary": {
            "acceptance_result_constructed": False,
            "producer_free_verification_present": False,
            "fresh_target_outcome_observed": False,
            "multi_step_target_plan_verified": False,
            "sample_tax_reduction_verified_in_second_domain": False,
            "complete_world_model_synthesized": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        },
    }
    return {
        **payload,
        "preregistration_id": domains.extension_content_id_v91r3(
            domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_PREREGISTRATION_V91R3_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class SourceModelAcceptancePreregistrationV91R3:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    preregistration_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        payload = {
            key: value
            for key, value in document.items()
            if key != "preregistration_id"
        }
        if (
            self._issuer is not _ISSUER
            or type(document) is not dict
            or canonical_json_bytes(document) != self.canonical_bytes
            or document.get("preregistration_id") != self.preregistration_id
            or domains.extension_content_id_v91r3(
                domains.CONSTRUCTION_K7_SOURCE_MODEL_ACCEPTANCE_PREREGISTRATION_V91R3_DOMAIN,
                payload,
            )
            != self.preregistration_id
        ):
            _fail("V91r3 preregistration bytes or issuer changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


_CACHE: SourceModelAcceptancePreregistrationV91R3 | None = None


def freeze_source_model_acceptance_preregistration_v91r3(
) -> SourceModelAcceptancePreregistrationV91R3:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    if _source_facts() != _frozen_source_facts():
        _fail("V91r3 frozen source facts changed")
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["preregistration_id"]
    if PREREGISTRATION_ID != "0" * 64 and (
        identity != PREREGISTRATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V91r3 preregistration changed")
    _CACHE = SourceModelAcceptancePreregistrationV91R3(_ISSUER, raw, identity)
    return _CACHE


def verify_source_model_acceptance_preregistration_v91r3(
    value: Any,
) -> SourceModelAcceptancePreregistrationV91R3:
    if type(value) is not SourceModelAcceptancePreregistrationV91R3:
        _fail("V91r3 preregistration rejects foreign values")
    value.__post_init__()
    expected = freeze_source_model_acceptance_preregistration_v91r3()
    if value is not expected or value.canonical_bytes != expected.canonical_bytes:
        _fail("V91r3 preregistration differs from frozen output")
    return value


__all__ = (
    "PREREGISTRATION_ID",
    "freeze_source_model_acceptance_preregistration_v91r3",
    "verify_source_model_acceptance_preregistration_v91r3",
)
