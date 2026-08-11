"""Run a fresh abstract query from one reusable query-neutral model.

The public execution boundary accepts only the model-export trace, its exact
100-path BuildEpoch envelope, and a fresh logical-occurrence identity.  It
reconstructs the typed numerical model from canonical bytes and performs the
adaptive quotient search without accepting an observer, kernel, ground tape,
signer, acquisition schedule, or private law.

This slice returns either a numerical candidate or the exact failed-proof
frontier that a later causal authority may consume before permitting a local
ground-recovery transaction.  It does not itself authorize recovery, claim a
plan certificate, or issue a formal zero-ground CounterRecord.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_SPEC_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.84"
PROFILE_KEY = "construction_k7_reusable_abstract_query_v1"

SPEC_DOMAIN = CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_SPEC_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({SPEC_DOMAIN, RESULT_DOMAIN})
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("reusable abstract-query domains are not central")

_SPEC_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7ReusableAbstractQueryV1Error(ValueError):
    """The query, reusable model, or exact abstract proof changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ReusableAbstractQueryV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ReusableAbstractQueryV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class ReusableAbstractQuerySpecV1:
    _issuer: InitVar[object]
    reusable_build_epoch_envelope_id: str
    root_model_id: str
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    route: planning_v2.V075PlanningRouteV2
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SPEC_ISSUER:
            _fail("reusable abstract query spec is caller-minted")
        for value, label in (
            (self.reusable_build_epoch_envelope_id, "BuildEpoch envelope"),
            (self.root_model_id, "root model"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.threshold_profile_id, "threshold profile"),
        ):
            _cid(value, label)
        try:
            route = planning_v2.V075PlanningRouteV2(self.route)
        except (TypeError, ValueError) as error:
            raise ConstructionK7ReusableAbstractQueryV1Error(
                "reusable abstract query route changed"
            ) from error
        object.__setattr__(self, "route", route)
        if (
            type(self.query_ordinal) is not int
            or self.query_ordinal < 0
            or route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.threshold_profile_id
            != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        ):
            _fail("reusable abstract query profile changed")
        object.__setattr__(
            self,
            "_query_id",
            content_id(SPEC_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_reusable_abstract_query_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "reusable_build_epoch_envelope_id": self.reusable_build_epoch_envelope_id,
            "root_model_id": self.root_model_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "route": self.route.value,
            "query_api_accepts_ground_input": False,
            "query_api_accepts_private_law": False,
            "query_api_accepts_observer_or_signer": False,
            "model_construction_repeated": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(SPEC_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("reusable abstract query spec changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "reusable_abstract_query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class ReusableAbstractQueryResultV1:
    _issuer: InitVar[object]
    query: ReusableAbstractQuerySpecV1
    source_operational_trace_id: str
    root_model_epoch_id: str
    numerical_proof: planning_v2.V075NumericalPlanningProofV2
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.query) is not ReusableAbstractQuerySpecV1
            or type(self.numerical_proof)
            is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("reusable abstract query result is caller-minted")
        _cid(self.source_operational_trace_id, "source trace")
        _cid(self.root_model_epoch_id, "root model epoch")
        self.query.__post_init__(_SPEC_ISSUER)
        if (
            self.numerical_proof.model.model_id != self.query.root_model_id
            or self.numerical_proof.route is not self.query.route
        ):
            _fail("reusable abstract proof crossed its query/model")
        object.__setattr__(
            self,
            "_result_id",
            content_id(RESULT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.numerical_proof.failed_frontier
        policy = self.numerical_proof.policy
        return {
            "schema": "acfqp.construction_k7_reusable_abstract_query_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "reusable_abstract_query_id": self.query.query_id,
            "logical_occurrence_id": self.query.logical_occurrence_id,
            "reusable_build_epoch_envelope_id": self.query.reusable_build_epoch_envelope_id,
            "source_operational_trace_id": self.source_operational_trace_id,
            "root_model_epoch_id": self.root_model_epoch_id,
            "root_model_id": self.query.root_model_id,
            "threshold_profile_id": self.query.threshold_profile_id,
            "route": self.query.route.value,
            "numerical_proof_id": self.numerical_proof.proof_id,
            "numerical_outcome": self.numerical_proof.outcome.value,
            "policy_id": None if policy is None else policy.policy_id,
            "failed_frontier_id": None if frontier is None else frontier.frontier_id,
            "model_construction_repeated": False,
            "build_epoch_native_path_count_reused": 100,
            "ground_input_parameter_present": False,
            "private_law_input_present": False,
            "observer_or_signer_input_present": False,
            "formal_ground_access_zero_record_issued_here": False,
            "certificate_failed_frontier_present": frontier is not None,
            "local_ground_recovery_authorized_here": False,
            "ground_recovery_executed_here": False,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("reusable abstract query result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query": self.query.to_document(),
            "numerical_proof": self.numerical_proof.to_document(),
            "reusable_abstract_query_result_id": self.result_id,
        }


def freeze_reusable_abstract_query_spec_v1(
    *,
    build_epoch: build_v1.ReusableBuildEpochEnvelopeV1,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> ReusableAbstractQuerySpecV1:
    if type(build_epoch) is not build_v1.ReusableBuildEpochEnvelopeV1:
        _fail("reusable query requires one exact BuildEpoch envelope")
    # Revalidate the immutable typed envelope before borrowing its IDs.
    build_v1.require_reusable_build_epoch_envelope_v1(build_epoch)
    return ReusableAbstractQuerySpecV1(
        _SPEC_ISSUER,
        build_epoch.envelope_id,
        build_epoch.root_model_id,
        _cid(logical_occurrence_id, "logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
        planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )


def run_reusable_abstract_query_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    query: ReusableAbstractQuerySpecV1,
) -> ReusableAbstractQueryResultV1:
    if type(query) is not ReusableAbstractQuerySpecV1:
        _fail("reusable abstract query has a foreign type")
    query.__post_init__(_SPEC_ISSUER)
    build_epoch = build_v1.verify_reusable_build_epoch_authority_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        envelope_bytes=build_epoch_envelope_bytes,
    )
    if (
        query.reusable_build_epoch_envelope_id != build_epoch.envelope_id
        or query.root_model_id != build_epoch.root_model_id
    ):
        _fail("reusable abstract query crossed its BuildEpoch")
    trace = loads_canonical_json(source_trace_bytes)
    if type(trace) is not dict:
        _fail("reusable abstract query source trace is not one object")
    model = planning_v2.replay_v075_numerical_model_bytes_v2(
        canonical_json_bytes(trace["root_numerical_model"])
    )
    proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=model,
        route=query.route,
    )
    return ReusableAbstractQueryResultV1(
        _RESULT_ISSUER,
        query,
        build_epoch.source_operational_trace_id,
        build_epoch.root_model_epoch_id,
        proof,
    )


def verify_reusable_abstract_query_result_bytes_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    result_bytes: bytes,
) -> ReusableAbstractQueryResultV1:
    if type(result_bytes) is not bytes or not result_bytes:
        _fail("reusable abstract query result must be nonempty bytes")
    try:
        document = loads_canonical_json(result_bytes)
    except Exception as error:
        raise ConstructionK7ReusableAbstractQueryV1Error(
            "reusable abstract query result is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != result_bytes:
        _fail("reusable abstract query result is not one canonical object")
    build_epoch = build_v1.verify_reusable_build_epoch_authority_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        envelope_bytes=build_epoch_envelope_bytes,
    )
    query_document = document.get("query")
    if type(query_document) is not dict:
        _fail("reusable abstract query document is absent")
    try:
        query = ReusableAbstractQuerySpecV1(
            _SPEC_ISSUER,
            build_epoch.envelope_id,
            build_epoch.root_model_id,
            query_document["logical_occurrence_id"],
            query_document["query_ordinal"],
            query_document["threshold_profile_id"],
            planning_v2.V075PlanningRouteV2(query_document["route"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7ReusableAbstractQueryV1Error(
            "reusable abstract query spec failed replay"
        ) from error
    if canonical_json_bytes(query.to_document()) != canonical_json_bytes(query_document):
        _fail("reusable abstract query spec differs from replay")
    expected = run_reusable_abstract_query_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        query=query,
    )
    if canonical_json_bytes(expected.to_document()) != result_bytes:
        _fail("reusable abstract query result differs from exact replanning")
    return expected


__all__ = [
    "ConstructionK7ReusableAbstractQueryV1Error",
    "LOCAL_DOMAINS",
    "ReusableAbstractQueryResultV1",
    "ReusableAbstractQuerySpecV1",
    "freeze_reusable_abstract_query_spec_v1",
    "run_reusable_abstract_query_v1",
    "verify_reusable_abstract_query_result_bytes_v1",
]
