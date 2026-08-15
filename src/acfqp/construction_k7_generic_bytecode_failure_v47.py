"""Frozen V47 failure: target VM state could not remain adapter-independent."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.construction_k7_generic_bytecode_preregistration_v47 import (
    PREREGISTRATION_ID,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_GENERIC_BYTECODE_FAILURE_V47_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "47.0.0"
FAILURE_ID = "93c13b08b8044ada9f7bca3b3f3c1972996ca0bf7b4a7ce865d691f497c692f0"
EXPECTED_CANONICAL_BYTE_COUNT = 1567
EXPECTED_CANONICAL_SHA256 = "df3687da77ad518baafa3cff552ffa2198d0586b675c11a9a8367ee6b59915db"


class ConstructionK7GenericBytecodeFailureV47Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7GenericBytecodeFailureV47Error(message)


def _document() -> dict[str, Any]:
    payload = {
        "schema": "acfqp.generic_bytecode_failure.v47",
        "schema_version": SCHEMA_VERSION,
        "failed_preregistration_id": PREREGISTRATION_ID,
        "attempt_status": "FAILED_PREDECESSOR_FROZEN_NO_SCIENTIFIC_RESULT",
        "registered_workload_access": {
            "lmb_source_seeds_accessed": [470101, 470102, 470103, 470104],
            "lmb_target_seeds_planned_or_executed": [
                471301,
                471302,
                471303,
                471304,
                471305,
                471306,
            ],
            "stochastic_source_seeds_executed": [472101, 472102, 472103, 472104],
            "stochastic_source_episodes_per_seed": 8,
            "stochastic_target_seeds_planned": [
                473301,
                473302,
                473303,
                473304,
                473305,
                473306,
                473307,
                473308,
            ],
            "same_id_rerun_forbidden": True,
        },
        "first_contract_failure": {
            "component": "bind_scalar_categorical_target_v1",
            "missing_compiled_binding": "OPAQUE_RESOURCE_STATE_COLUMN",
            "missing_public_operation": "ANONYMOUS_VM_SUCCESSOR_EXECUTION",
            "consequence": (
                "TARGET_RECEDING_STATE_UPDATE_WOULD_REQUIRE_TYPED_DOMAIN_ADAPTER"
            ),
            "violated_preregistered_condition": (
                "PLANNER_CONSUMES_COMPILED_BYTECODE_ONLY"
            ),
        },
        "campaign_artifact_issued": False,
        "sample_tax_result_issued": False,
        "cross_domain_result_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "required_successor_actions": [
            "ADD_COMPLETE_TARGET_STATE_REGISTER_BINDING",
            "ADD_PUBLIC_DOMAIN_NEUTRAL_VM_EXECUTOR",
            "USE_FRESH_SOURCE_AND_TARGET_IDENTITIES",
            "PREREGISTER_SUCCESSOR_BEFORE_FRESH_OUTCOMES",
        ],
    }
    return {
        **payload,
        "generic_bytecode_failure_id": content_id(
            CONSTRUCTION_K7_GENERIC_BYTECODE_FAILURE_V47_DOMAIN, payload
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class GenericBytecodeFailureV47:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V47 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V47 failure bytes changed")
        payload = {key: value for key, value in document.items() if key != "generic_bytecode_failure_id"}
        if (
            document.get("generic_bytecode_failure_id") != self.failure_id
            or content_id(CONSTRUCTION_K7_GENERIC_BYTECODE_FAILURE_V47_DOMAIN, payload)
            != self.failure_id
        ):
            _fail("V47 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError
        return value


def freeze_generic_bytecode_failure_v47() -> GenericBytecodeFailureV47:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["generic_bytecode_failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V47 failure changed")
    return GenericBytecodeFailureV47(_ISSUER, raw, identity)


def verify_generic_bytecode_failure_v47(
    value: GenericBytecodeFailureV47,
) -> GenericBytecodeFailureV47:
    if type(value) is not GenericBytecodeFailureV47:
        _fail("V47 failure rejects foreign values")
    value.__post_init__()
    if value.canonical_bytes != canonical_json_bytes(_document()):
        _fail("V47 failure semantics changed")
    return value


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILURE_ID",
    "GenericBytecodeFailureV47",
    "freeze_generic_bytecode_failure_v47",
    "verify_generic_bytecode_failure_v47",
)
