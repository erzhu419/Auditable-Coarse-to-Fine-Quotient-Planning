"""Standalone evaluation-only parity replay for the owned fallback slice."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
    CanonicalOwnedFallbackRunnerResultV2,
    run_canonical_infeasible_fallback_owned_v2,
)
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackExecutionV1,
    run_ground_fallback_search_v1,
)
from acfqp.accounting_v1 import official_counter_registry_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "construction_k7_owned_fallback_parity_v2"
EXECUTION_LANE = "EVALUATION"
CHARGED_AS_OPERATIONAL_ROUTE_WORK = False
OFFICIAL_EXECUTION_ALLOWED = False
_PARITY_DOMAIN = "acfqp:construction-k7-owned-fallback-parity:v2"
_ISSUER = object()


class ConstructionK7OwnedFallbackParityV2Error(ValueError):
    """Owned/reference exact search parity or serialized replay failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7OwnedFallbackParityV2Error(message)


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        _PARITY_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _result_signature(execution: GroundFallbackExecutionV1) -> dict[str, Any]:
    result = execution.result
    return {
        "RouteDecisionContext_id": result.route_decision_context_id,
        "decision_point_id": result.decision_point_id,
        "route_decision_id": result.route_decision_id,
        "selected_upper_id": result.selected_upper_id,
        "route_attempt_id": result.route_attempt_id,
        "query_id": result.query_id,
        "ground_fallback_cap_profile_id": result.ground_fallback_cap_profile_id,
        "outcome": result.outcome.value,
        "search_complete": result.search_complete,
        "frontier": [row.to_dict() for row in result.frontier],
        "selected_policy_signature": [
            {"remaining": remaining, "state": state, "action": action}
            for remaining, state, action in result.selected_policy_signature
        ],
        "selected_expected_reward": result.selected_expected_reward,
        "selected_failure_probability": result.selected_failure_probability,
        "cap_exhausted_name": result.cap_exhausted_name,
        "composed_candidate_count": result.composed_candidate_count,
        "work_values": [
            {"path": path, "value": value}
            for path, value in sorted(execution.work_vector.values.items())
        ],
        "selected_policy_present": execution.selected_policy is not None,
    }


@dataclass(frozen=True, slots=True)
class OwnedFallbackParityReportV2:
    _issuer: InitVar[object]
    owned: CanonicalOwnedFallbackRunnerResultV2 = field(repr=False, compare=False)
    reference: GroundFallbackExecutionV1 = field(repr=False, compare=False)
    _parity_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.owned) is not CanonicalOwnedFallbackRunnerResultV2
            or type(self.reference) is not GroundFallbackExecutionV1
            or _result_signature(self.owned.execution)
            != _result_signature(self.reference)
        ):
            _fail("owned fallback differs from independent V1 exact search")
        object.__setattr__(self, "_parity_id", _content_id(self._payload()))

    def _payload(self) -> dict[str, Any]:
        signature = _result_signature(self.owned.execution)
        return {
            "schema": "acfqp.owned_fallback_parity_report.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "owned_runner_result_id": self.owned.result_id,
            "owned_ground_fallback_result_id": self.owned.execution.result.ground_fallback_result_id,
            "reference_ground_fallback_result_id": self.reference.result.ground_fallback_result_id,
            "reference_work_vector_id": self.reference.work_vector.work_vector_id,
            "exact_parity_signature": signature,
            "mathematical_result_equal": True,
            "native_counter_values_equal": True,
            "execution_lane": EXECUTION_LANE,
            "charged_as_operational_route_work": False,
            "counter_records_issued": 0,
            "work_vectors_v6_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifact_issued": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def parity_id(self) -> str:
        if _content_id(self._payload()) != self._parity_id:
            _fail("owned fallback parity report changed after issuance")
        return self._parity_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_fallback_parity_id": self.parity_id}


def evaluate_owned_fallback_parity_v2(
    proof_bytes: bytes,
    *,
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> OwnedFallbackParityReportV2:
    """Replay owned and historical exact searches in the evaluation lane."""

    owned = run_canonical_infeasible_fallback_owned_v2(
        proof_bytes,
        current_identity=current_identity,
        cap_profile=cap_profile,
    )
    proof, _verified, current = acquisition_v1._proof_document(
        proof_bytes,
        current_identity=current_identity,
    )
    preexecution = acquisition_v1._preexecution_candidate(
        proof,
        current_identity=current,
        cap_profile=cap_profile,
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    reference = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=preexecution.route_context.route_decision_context_id,
        decision_point_id=preexecution.decision_point.decision_point_id,
        route_decision_id=preexecution.decision.route_decision_id,
        selected_upper_id=preexecution.upper.route_upper_bound_envelope_id,
        route_attempt_id=preexecution.route_context.route_attempt_id,
        query_id=proof["identity"]["query_id"],
        cap_profile=preexecution.cap_profile,
        registry=official_counter_registry_v1(),
        recorder_id="canonical-infeasible-fallback-parity-reference-v1",
    )
    return OwnedFallbackParityReportV2(_ISSUER, owned, reference)


def verify_owned_fallback_runner_bytes_v2(
    *,
    raw: bytes,
    proof_bytes: bytes,
    current_identity: acquisition_v1.CanonicalFallbackCurrentIdentityV1,
    cap_profile: GroundFallbackCapProfileV1 | None = None,
) -> OwnedFallbackParityReportV2:
    """Independently replay a canonical runner document and exact V1 parity."""

    if type(raw) is not bytes or not raw:
        _fail("owned fallback runner bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7OwnedFallbackParityV2Error(
            "owned fallback runner bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("owned fallback runner bytes are noncanonical")
    report = evaluate_owned_fallback_parity_v2(
        proof_bytes,
        current_identity=current_identity,
        cap_profile=cap_profile,
    )
    if document != report.owned.to_document():
        _fail("owned fallback runner bytes differ from independent replay")
    return report


__all__ = (
    "CHARGED_AS_OPERATIONAL_ROUTE_WORK",
    "ConstructionK7OwnedFallbackParityV2Error",
    "EXECUTION_LANE",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OwnedFallbackParityReportV2",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "evaluate_owned_fallback_parity_v2",
    "verify_owned_fallback_runner_bytes_v2",
)
