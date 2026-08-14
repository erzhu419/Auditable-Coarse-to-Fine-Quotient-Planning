"""Typed preservation of the invalid V46 out-of-grammar campaign attempt."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_lmb_opaque_column_failed_attempt_v46 as attempt
from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


PROFILE_KEY = "construction_k7_lmb_opaque_column_failure_v46"
FAILURE_ID = "b3303de4717ccc7232527cc83204279294d8756ccb965951bd27820abafa6a6b"
EXPECTED_CANONICAL_BYTE_COUNT = 2_058
EXPECTED_CANONICAL_SHA256 = "66df9119c5ed26693eb35cfb4bca70f0d5708aebe4b2fec7cc045a674d3c6589"


class ConstructionK7LMBOpaqueColumnFailureV46Error(ValueError):
    """The invalid attempt, grammar violation, or claim boundary changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7LMBOpaqueColumnFailureV46Error(message)


def _operator_heads(value: Any) -> set[str]:
    if type(value) is not list:
        return set()
    result = set()
    if value and type(value[0]) is str:
        result.add(value[0])
    for item in value[1:]:
        result.update(_operator_heads(item))
    return result


def _document() -> dict[str, Any]:
    frozen_attempt = attempt.freeze_lmb_opaque_column_failed_attempt_v46()
    attempted_document = frozen_attempt.to_document()
    program = attempted_document["derived_program"]
    registered = {
        row[0] for row in program["generic_relation_meta_grammar"]["constructors"]
    }
    used = set()
    for expression in program["compiled_typed_expressions"]:
        used.update(_operator_heads(expression[1]))
    unregistered = sorted(used - registered)
    expected_unregistered = [
        "ADD_ONE",
        "ALL_ACTION_IDS_INSERTED",
        "MODULO",
        "RELATION_VECTOR_AT",
        "RELATION_VECTOR_UPDATE",
    ]
    if unregistered != expected_unregistered:
        _fail("V46 grammar violation inventory changed")
    payload = {
        "schema": "acfqp.lmb_opaque_column_failure.v46",
        "schema_version": pre.SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "preregistration_id": pre.PREREGISTRATION_ID,
        "v45_campaign_id": pre.V45_CAMPAIGN_ID,
        "v45_verification_id": pre.V45_VERIFICATION_ID,
        "attempted_campaign_id": frozen_attempt.attempted_campaign_id,
        "attempted_campaign_byte_count": len(frozen_attempt.canonical_bytes),
        "attempted_campaign_sha256": hashlib.sha256(
            frozen_attempt.canonical_bytes
        ).hexdigest(),
        "registered_constructor_names": sorted(registered),
        "used_constructor_names": sorted(used),
        "unregistered_constructor_names": unregistered,
        "attempted_source_transition_label_count": program[
            "total_source_transition_label_count"
        ],
        "attempted_target_episode_count": len(attempted_document["episodes"]),
        "attempted_target_execution_transition_count": sum(
            len(episode["decisions"]) for episode in attempted_document["episodes"]
        ),
        "attempted_ood_environment_step_count": attempted_document[
            "ood_no_transfer"
        ]["environment_step_count"],
        "attempt_valid": False,
        "attempt_may_not_be_promoted_to_campaign_evidence": True,
        "same_identity_corrected_rerun_allowed": False,
        "successor_requires_fresh_preregistration_and_outcome_identities": True,
        "failure_code": "COMPILED_PROGRAM_USES_UNREGISTERED_RELATION_CONSTRUCTORS",
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
        "status": "TYPED_PREREGISTERED_CONSTRUCTION_FAILURE",
    }
    return {
        **payload,
        "failure_id": content_id(pre.FUTURE_DOMAINS["campaign"], payload),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class LMBOpaqueColumnFailureV46:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    failure_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("V46 failure is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("V46 failure bytes changed")
        payload = {key: value for key, value in document.items() if key != "failure_id"}
        if (
            document.get("failure_id") != self.failure_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.failure_id
        ):
            _fail("V46 failure identity changed")

    def to_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self.canonical_bytes)
        if type(value) is not dict:  # pragma: no cover
            raise AssertionError("V46 failure is not an object")
        return value


def freeze_lmb_opaque_column_failure_v46() -> LMBOpaqueColumnFailureV46:
    document = _document()
    raw = canonical_json_bytes(document)
    identity = document["failure_id"]
    if FAILURE_ID != "0" * 64 and (
        identity != FAILURE_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V46 failure changed")
    return LMBOpaqueColumnFailureV46(_ISSUER, raw, identity)


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "FAILURE_ID",
    "LMBOpaqueColumnFailureV46",
    "freeze_lmb_opaque_column_failure_v46",
)
