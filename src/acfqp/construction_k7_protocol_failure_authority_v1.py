"""K7 FQ13 predecision protocol-failure accounting authority.

The production Phase-3E runner records frozen-input reads through
``FailClosedAccessController`` and freezes the route decision before any
route-scoped access.  Consequently there is no genuine production
predecision violation in the current positive K7 occurrence.  This module
records that fact as a typed real-site blocker; it never converts a fabricated
event into a production claim.

It also freezes one canonical negative-control violation using the *same*
``ProtocolSequenceProfileV1``, ``AccessEventLogV1`` and semantic replay used by
the production runner: a ``KERNEL_STEP`` is requested before the route
decision is frozen.  The request is rejected by the access controller, so it
is protocol work but not a kernel transition.  The authority retains a
complete last-valid V6 prefix (202 observed CounterRecords, including native
zeroes), its WorkVector, and its exact eight-axis ComparisonVector.  The only
terminal is

``ROUTE_ATTEMPT / ATTEMPT_CLOSURE_NONCERTIFICATE / PROTOCOL_FAILURE``.

The byte verifier parses and semantically replays the profile, event log,
first violation, counter values, projection, and terminal without invoking
the producer.  This successor is a negative-control accounting authority; it
does not claim a production violation, infeasibility, a plan certificate,
logical-occurrence closure, or an official Gate result.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import re
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import (
    SHARED_AXES,
    ComparisonVectorV1,
    CounterRecordV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.access_protocol_v1 import (
    AccessEventLogV1,
    AccessEventV1,
    AccessOperation,
    AccessProtocolV1Error,
    AccessProtocolViolation,
    AccessRouteScope,
    AccessViolationReason,
    ForbiddenAccessViolationV1,
    ProtocolSequenceProfileV1,
    replay_access_protocol,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN,
    CONSTRUCTION_K7_PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_PROTOCOL_PREFIX_RECORDER_V1_DOMAIN,
    CONSTRUCTION_K7_PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.37"
PROFILE_KEY = "construction_k7_protocol_failure_authority_v1"

EXPECTED_COUNTER_RECORD_COUNT = registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT
EXPECTED_COMPARISON_AXIS_COUNT = len(SHARED_AXES)
ROUTE_KIND = RouteKindEnum.ABSTRACT_FAILED_PREFIX

TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "PROTOCOL_FAILURE"
SPECIFIC_CAUSE = "PRESELECTION_FORBIDDEN_ACCESS"

BLOCKER_CODE = "NO_PRODUCTION_PREDECISION_VIOLATION_OBSERVED"
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"

PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN = (
    CONSTRUCTION_K7_PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN
)
PROTOCOL_PREFIX_RECORDER_V1_DOMAIN = (
    CONSTRUCTION_K7_PROTOCOL_PREFIX_RECORDER_V1_DOMAIN
)
PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN = (
    CONSTRUCTION_K7_PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN
)
PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN = (
    CONSTRUCTION_K7_PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN
)
PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_K7_PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN
)

LOCAL_DOMAINS = frozenset(
    {
        PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN,
        PROTOCOL_PREFIX_RECORDER_V1_DOMAIN,
        PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN,
        PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN,
        PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS.issubset(  # pragma: no cover
    PHASE3E_DOMAIN_TAGS
):
    raise RuntimeError(
        "K7 protocol-failure domains must be unique and centrally registered"
    )

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_BLOCKER_ISSUER = object()
_TERMINAL_ISSUER = object()
_BUNDLE_ISSUER = object()
_VERIFICATION_ISSUER = object()


class ConstructionK7ProtocolFailureAuthorityV1Error(ValueError):
    """A protocol event, complete prefix, or terminal failed exact replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ProtocolFailureAuthorityV1Error(message)


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("K7 protocol-failure authority used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ProtocolFailureAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _identifier(value: Any, label: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        _fail(f"{label} must be one canonical identifier")
    return value


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        _fail(f"{label} must be one lowercase SHA-256")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7ProtocolFailureAuthorityV1Error(
            f"{label} bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are noncanonical")
    return document


def _fields(document: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != expected:
        _fail(f"{label} field set changed")
    return document


@dataclass(frozen=True, slots=True)
class K7ProtocolFailureRealSiteBlockerV1:
    """Typed statement that the registered production path did not violate FQ13."""

    _issuer: InitVar[object]
    blocker_code: str = BLOCKER_CODE
    _blocker_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BLOCKER_ISSUER or self.blocker_code != BLOCKER_CODE:
            _fail("protocol real-site blocker is caller-minted or relabelled")
        object.__setattr__(
            self,
            "_blocker_id",
            _local_id(PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_protocol_real_site_blocker.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "blocker_code": self.blocker_code,
            "production_runner_module": "acfqp.phase3e_runner_v1",
            "production_runner_symbol": "run_phase3e",
            "protocol_module": "acfqp.access_protocol_v1",
            "protocol_record_symbol": "FailClosedAccessController.record",
            "protocol_replay_symbol": "replay_access_protocol",
            "production_predecision_violation_observed": False,
            "canonical_negative_control_registered": True,
            "canonical_negative_control_is_production_event": False,
            "genuine_execution_claimed": False,
            "reason": (
                "the registered production runner replays COMMON frozen reads "
                "and freezes the route decision before route-scoped access"
            ),
        }

    @property
    def blocker_id(self) -> str:
        if (
            _local_id(PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN, self._payload())
            != self._blocker_id
        ):
            _fail("protocol real-site blocker changed after issuance")
        return self._blocker_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_real_site_blocker_id": self.blocker_id}

    @classmethod
    def _from_document(
        cls, document: Any
    ) -> "K7ProtocolFailureRealSiteBlockerV1":
        expected = set(cls(_BLOCKER_ISSUER).to_document())
        row = _fields(document, expected, "protocol real-site blocker")
        result = cls(_BLOCKER_ISSUER, row["blocker_code"])
        if row != result.to_document():
            _fail("protocol real-site blocker differs from the registered source fact")
        return result


def canonical_k7_protocol_real_site_blocker_v1() -> K7ProtocolFailureRealSiteBlockerV1:
    return K7ProtocolFailureRealSiteBlockerV1(_BLOCKER_ISSUER)


def _replay_first_violation(
    profile: ProtocolSequenceProfileV1,
    log: AccessEventLogV1,
) -> ForbiddenAccessViolationV1:
    """Return exactly the first semantic violation from the shared authority."""

    try:
        replay_access_protocol(log, profile)
    except AccessProtocolViolation as error:
        violation = error.violation
    except AccessProtocolV1Error as error:
        raise ConstructionK7ProtocolFailureAuthorityV1Error(
            "access sequence is structurally invalid, not a semantic violation"
        ) from error
    else:
        _fail("access sequence contains no protocol violation")
    if (
        violation.reason is not AccessViolationReason.PRESELECTION_FORBIDDEN_ACCESS
        or violation.operation is not AccessOperation.KERNEL_STEP
        or violation.offending_sequence_number != 2
        or violation.selected_route is not None
        or violation.route_decision_freeze_attestation_id is not None
        or violation.terminal_class != TERMINAL_CLASS
        or violation.terminal_code != TERMINAL_CODE
    ):
        _fail("canonical K7 negative control violation semantics changed")
    return violation


def _validate_canonical_fixture(
    profile: ProtocolSequenceProfileV1,
    log: AccessEventLogV1,
) -> ForbiddenAccessViolationV1:
    if profile != ProtocolSequenceProfileV1():
        _fail("protocol negative control must use the exact production profile")
    if (
        log.is_frozen
        or len(log.events) != 2
        or log.events[0].operation is not AccessOperation.READ_FROZEN_RAPM
        or log.events[0].route_scope is not AccessRouteScope.COMMON
        or log.events[0].artifact_id is None
        or log.events[1].operation is not AccessOperation.KERNEL_STEP
        or log.events[1].route_scope is not AccessRouteScope.LOCAL
        or log.events[1].artifact_id is not None
    ):
        _fail("canonical K7 predecision violation fixture changed")
    return _replay_first_violation(profile, log)


def _record_id_for(
    *,
    log_id: str,
    violation_id: str,
    path: str,
    value: int,
) -> str:
    return _local_id(
        PROTOCOL_PREFIX_RECORDER_V1_DOMAIN,
        {
            "schema": "acfqp.construction_k7_protocol_prefix_recorder.v1",
            "schema_version": SCHEMA_VERSION,
            "access_event_log_id": log_id,
            "forbidden_access_violation_id": violation_id,
            "path": path,
            "value": value,
            "observed": True,
            "evidence_kind": (
                "PROFILE_NATIVE_ZERO" if value == 0 else "DETECTION_PREFIX_EVENT"
            ),
        },
    )


def _materialize_complete_prefix(
    *,
    profile: ProtocolSequenceProfileV1,
    log: AccessEventLogV1,
    violation: ForbiddenAccessViolationV1,
) -> tuple[tuple[CounterRecordV1, ...], WorkVectorV1, ComparisonVectorV1]:
    expected_violation = _validate_canonical_fixture(profile, log)
    if violation.to_dict() != expected_violation.to_dict():
        _fail("claimed forbidden-access violation is not the first replayed violation")

    registry = registry_v6.official_counter_registry_v6()
    registry.validate_official_catalogue()
    profile_raw = canonical_json_bytes(profile.to_dict())
    log_raw = canonical_json_bytes(log.to_dict())
    violation_raw = canonical_json_bytes(violation.to_dict())
    values = {path: 0 for path in registry.required_paths}

    # Exact accounting boundary: profile/log reads and the violation artifact
    # written through detection.  The rejected KERNEL_STEP never executes.
    values.update(
        {
            "route.attempts": 1,
            "route.successes": 0,
            "route.failures": 1,
            "common.protocol_checks": len(log.events) + 1,
            "common.integrity_checks": 3,
            "common.hash_invocations": 3,
            "io.read_bytes": len(profile_raw) + len(log_raw),
            "io.output_bytes": len(log_raw) + len(violation_raw),
        }
    )
    if values["fallback.ground_steps"] != 0 or any(
        values[path] != 0
        for path in values
        if path.startswith(("local.", "fallback.", "rebuild."))
    ):
        _fail("predecision protocol failure cannot contain route execution work")
    if (
        values["route.attempts"]
        != values["route.successes"] + values["route.failures"]
        or values["solver.attempts"]
        != values["solver.successes"] + values["solver.failures"]
        or values["process.launches"]
        != values["process.exit_successes"] + values["process.exit_failures"]
        or values.get("branch.evaluations", 0) != 0
    ):
        _fail("protocol-failure prefix reconciliation changed")

    records = tuple(
        CounterRecordV1(
            registry.registry_id,
            path,
            values[path],
            True,
            _record_id_for(
                log_id=log.access_event_log_id,
                violation_id=violation.forbidden_access_violation_id,
                path=path,
                value=values[path],
            ),
            registry.by_path[path].semantics_id,
            registry.by_path[path].owner,
            registry.by_path[path].unit,
            registry.by_path[path].lane,
            registry.by_path[path].scope,
            registry.by_path[path].reducer,
        )
        for path in registry.required_paths
    )
    if (
        len(records) != EXPECTED_COUNTER_RECORD_COUNT
        or tuple(row.path for row in records) != registry.required_paths
        or len({row.record_id for row in records}) != len(records)
        or any(row.observed is not True for row in records)
    ):
        _fail("protocol-failure prefix lacks the exact 202 observed records")
    work = WorkVectorV1(
        registry.registry_id,
        log.route_attempt_id,
        ROUTE_KIND,
        records,
    )

    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry, comparison_profile
    )
    comparison_profile.validate(registry)
    actual_profile.validate(registry, comparison_profile)
    axes = {axis: 0 for axis in SHARED_AXES}
    for term in actual_profile.terms:
        contribution = values[term.source_leaf] * term.coefficient
        if term.reducer is ReducerEnum.SUM:
            axes[term.target_axis] += contribution
        else:
            axes[term.target_axis] = max(
                axes[term.target_axis], contribution
            )
    comparison = ComparisonVectorV1(
        comparison_profile.comparison_profile_id,
        work.work_vector_id,
        log.route_attempt_id,
        ROUTE_KIND,
        tuple(sorted(axes.items())),
    )
    return records, work, comparison


@dataclass(frozen=True, slots=True)
class K7ProtocolFailureTerminalAuthorityV1:
    _issuer: InitVar[object]
    route_attempt_id: str
    decision_point_id: str
    protocol_sequence_profile_id: str
    access_event_log_id: str
    forbidden_access_violation_id: str
    real_site_blocker_id: str
    work_vector_id: str
    comparison_vector_id: str
    counter_record_ids: tuple[str, ...]
    _terminal_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TERMINAL_ISSUER:
            _fail("protocol-failure terminal authority is caller-minted")
        for value, label in (
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.protocol_sequence_profile_id, "protocol profile"),
            (self.access_event_log_id, "access event log"),
            (self.forbidden_access_violation_id, "forbidden access violation"),
            (self.real_site_blocker_id, "real-site blocker"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            *((value, "counter record") for value in self.counter_record_ids),
        ):
            _cid(value, label)
        if (
            type(self.counter_record_ids) is not tuple
            or len(self.counter_record_ids) != EXPECTED_COUNTER_RECORD_COUNT
            or len(set(self.counter_record_ids)) != len(self.counter_record_ids)
        ):
            _fail("protocol-failure terminal record identities changed")
        object.__setattr__(
            self,
            "_terminal_id",
            _local_id(
                PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN, self._payload()
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_protocol_failure_terminal_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "access_event_log_id": self.access_event_log_id,
            "forbidden_access_violation_id": self.forbidden_access_violation_id,
            "real_site_blocker_id": self.real_site_blocker_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "counter_record_ids": list(self.counter_record_ids),
            "route_kind": ROUTE_KIND.value,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SPECIFIC_CAUSE,
            "integrity_failure": False,
            "cap_exhaustion": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "production_violation_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def terminal_id(self) -> str:
        if (
            _local_id(
                PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN, self._payload()
            )
            != self._terminal_id
        ):
            _fail("protocol-failure terminal changed after issuance")
        return self._terminal_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "protocol_failure_terminal_authority_id": self.terminal_id,
        }


@dataclass(frozen=True, slots=True)
class K7ProtocolFailureBundleV1:
    _issuer: InitVar[object]
    blocker: K7ProtocolFailureRealSiteBlockerV1
    profile: ProtocolSequenceProfileV1
    access_log: AccessEventLogV1
    violation: ForbiddenAccessViolationV1
    records: tuple[CounterRecordV1, ...]
    work_vector: WorkVectorV1
    comparison_vector: ComparisonVectorV1
    terminal: K7ProtocolFailureTerminalAuthorityV1
    _bundle_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BUNDLE_ISSUER
            or type(self.blocker) is not K7ProtocolFailureRealSiteBlockerV1
            or type(self.profile) is not ProtocolSequenceProfileV1
            or type(self.access_log) is not AccessEventLogV1
            or type(self.violation) is not ForbiddenAccessViolationV1
            or type(self.work_vector) is not WorkVectorV1
            or type(self.comparison_vector) is not ComparisonVectorV1
            or type(self.terminal) is not K7ProtocolFailureTerminalAuthorityV1
        ):
            _fail("protocol-failure bundle is caller-minted")
        if (
            len(self.records) != EXPECTED_COUNTER_RECORD_COUNT
            or tuple(row.record_id for row in self.records)
            != tuple(row.record_id for row in self.work_vector.records)
            or self.profile.protocol_sequence_profile_id
            != self.access_log.protocol_sequence_profile_id
            or self.violation.access_event_log_id
            != self.access_log.access_event_log_id
            or self.terminal.real_site_blocker_id != self.blocker.blocker_id
            or self.terminal.work_vector_id != self.work_vector.work_vector_id
            or self.terminal.comparison_vector_id
            != self.comparison_vector.comparison_vector_id
        ):
            _fail("protocol-failure bundle identity graph changed")
        object.__setattr__(
            self,
            "_bundle_id",
            _local_id(PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_protocol_failure_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_real_site_blocker": self.blocker.to_document(),
            "protocol_sequence_profile": self.profile.to_dict(),
            "access_event_log": self.access_log.to_dict(),
            "forbidden_access_violation": self.violation.to_dict(),
            "counter_record_ids": [row.record_id for row in self.records],
            "counter_records": [row.to_dict() for row in self.records],
            "last_valid_prefix_work_vector": self.work_vector.to_dict(),
            "last_valid_prefix_comparison_vector": self.comparison_vector.to_dict(),
            "protocol_failure_terminal_authority": self.terminal.to_document(),
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "specific_cause": SPECIFIC_CAUSE,
            "integrity_failure": False,
            "cap_exhaustion": False,
            "terminal_is_infeasibility_certificate": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "logical_occurrence_closed": False,
            "production_violation_claimed": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def bundle_id(self) -> str:
        if (
            _local_id(PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN, self._payload())
            != self._bundle_id
        ):
            _fail("protocol-failure bundle changed after issuance")
        return self._bundle_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_failure_bundle_id": self.bundle_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _terminal_for(
    *,
    blocker: K7ProtocolFailureRealSiteBlockerV1,
    profile: ProtocolSequenceProfileV1,
    log: AccessEventLogV1,
    violation: ForbiddenAccessViolationV1,
    records: tuple[CounterRecordV1, ...],
    work: WorkVectorV1,
    comparison: ComparisonVectorV1,
) -> K7ProtocolFailureTerminalAuthorityV1:
    return K7ProtocolFailureTerminalAuthorityV1(
        _TERMINAL_ISSUER,
        log.route_attempt_id,
        log.decision_point_id,
        profile.protocol_sequence_profile_id,
        log.access_event_log_id,
        violation.forbidden_access_violation_id,
        blocker.blocker_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        tuple(row.record_id for row in records),
    )


def issue_canonical_k7_protocol_failure_bundle_v1(
    *,
    route_attempt_id: str,
    decision_point_id: str,
    frozen_rapm_id: str,
) -> K7ProtocolFailureBundleV1:
    """Issue the registered negative control; never claim a production event."""

    attempt = _cid(route_attempt_id, "route attempt")
    point = _cid(decision_point_id, "decision point")
    rapm = _cid(frozen_rapm_id, "frozen RAPM")
    blocker = canonical_k7_protocol_real_site_blocker_v1()
    profile = ProtocolSequenceProfileV1()
    log = AccessEventLogV1(
        attempt,
        point,
        profile.protocol_sequence_profile_id,
        (
            AccessEventV1(
                1,
                attempt,
                point,
                AccessOperation.READ_FROZEN_RAPM,
                AccessRouteScope.COMMON,
                rapm,
            ),
            AccessEventV1(
                2,
                attempt,
                point,
                AccessOperation.KERNEL_STEP,
                AccessRouteScope.LOCAL,
            ),
        ),
    )
    violation = _validate_canonical_fixture(profile, log)
    records, work, comparison = _materialize_complete_prefix(
        profile=profile, log=log, violation=violation
    )
    terminal = _terminal_for(
        blocker=blocker,
        profile=profile,
        log=log,
        violation=violation,
        records=records,
        work=work,
        comparison=comparison,
    )
    return K7ProtocolFailureBundleV1(
        _BUNDLE_ISSUER,
        blocker,
        profile,
        log,
        violation,
        records,
        work,
        comparison,
        terminal,
    )


@dataclass(frozen=True, slots=True)
class K7ProtocolFailureVerificationV1:
    _issuer: InitVar[object]
    bundle_id: str
    bundle_sha256: str
    bundle_byte_count: int
    real_site_blocker_id: str
    protocol_sequence_profile_id: str
    access_event_log_id: str
    forbidden_access_violation_id: str
    work_vector_id: str
    comparison_vector_id: str
    terminal_authority_id: str
    verified_work_vector: WorkVectorV1
    verified_comparison_vector: ComparisonVectorV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.verified_work_vector) is not WorkVectorV1
            or type(self.verified_comparison_vector) is not ComparisonVectorV1
        ):
            _fail("protocol-failure verification is caller-minted")
        for value, label in (
            (self.bundle_id, "bundle"),
            (self.real_site_blocker_id, "real-site blocker"),
            (self.protocol_sequence_profile_id, "protocol profile"),
            (self.access_event_log_id, "access log"),
            (self.forbidden_access_violation_id, "violation"),
            (self.work_vector_id, "work vector"),
            (self.comparison_vector_id, "comparison vector"),
            (self.terminal_authority_id, "terminal authority"),
        ):
            _cid(value, label)
        _sha256(self.bundle_sha256, "bundle digest")
        _positive(self.bundle_byte_count, "bundle byte count")
        if (
            self.verified_work_vector.work_vector_id != self.work_vector_id
            or self.verified_comparison_vector.comparison_vector_id
            != self.comparison_vector_id
        ):
            _fail("verified accounting identities changed")
        object.__setattr__(
            self,
            "_verification_id",
            _local_id(PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_protocol_failure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "bundle_id": self.bundle_id,
            "bundle_sha256": self.bundle_sha256,
            "bundle_byte_count": self.bundle_byte_count,
            "real_site_blocker_id": self.real_site_blocker_id,
            "protocol_sequence_profile_id": self.protocol_sequence_profile_id,
            "access_event_log_id": self.access_event_log_id,
            "forbidden_access_violation_id": self.forbidden_access_violation_id,
            "work_vector_id": self.work_vector_id,
            "comparison_vector_id": self.comparison_vector_id,
            "terminal_authority_id": self.terminal_authority_id,
            "counter_record_count": EXPECTED_COUNTER_RECORD_COUNT,
            "comparison_axis_count": EXPECTED_COMPARISON_AXIS_COUNT,
            "first_violation_independently_replayed": True,
            "complete_prefix_independently_reconstructed": True,
            "producer_invoked": False,
            "verification_lane": "evaluation",
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "production_violation_claimed": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        if (
            _local_id(PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN, self._payload())
            != self._verification_id
        ):
            _fail("protocol-failure verification changed after issuance")
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "protocol_failure_verification_id": self.verification_id,
        }


_BUNDLE_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "protocol_real_site_blocker",
    "protocol_sequence_profile",
    "access_event_log",
    "forbidden_access_violation",
    "counter_record_ids",
    "counter_records",
    "last_valid_prefix_work_vector",
    "last_valid_prefix_comparison_vector",
    "protocol_failure_terminal_authority",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "specific_cause",
    "integrity_failure",
    "cap_exhaustion",
    "terminal_is_infeasibility_certificate",
    "plan_certificate",
    "infeasibility_certificate",
    "logical_occurrence_closed",
    "production_violation_claimed",
    "official_execution_allowed",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
    "official_scalar_cost",
    "official_N_break_even",
    "protocol_failure_bundle_id",
}


def _parse_terminal(
    document: Any,
    expected: K7ProtocolFailureTerminalAuthorityV1,
) -> None:
    row = _fields(
        document,
        set(expected.to_document()),
        "protocol-failure terminal authority",
    )
    if row != expected.to_document():
        _fail("protocol-failure terminal differs from independent replay")


def verify_k7_protocol_failure_bundle_bytes_v1(
    *,
    raw: bytes,
    expected_route_attempt_id: str,
    expected_decision_point_id: str,
    expected_frozen_rapm_id: str,
) -> K7ProtocolFailureVerificationV1:
    """Independently replay canonical bytes without invoking the producer."""

    attempt = _cid(expected_route_attempt_id, "anchored route attempt")
    point = _cid(expected_decision_point_id, "anchored decision point")
    rapm = _cid(expected_frozen_rapm_id, "anchored frozen RAPM")
    document = _fields(
        _canonical_object(raw, "protocol-failure bundle"),
        _BUNDLE_FIELDS,
        "protocol-failure bundle",
    )
    locks = {
        "schema": "acfqp.construction_k7_protocol_failure_bundle.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS,
        "terminal_code": TERMINAL_CODE,
        "specific_cause": SPECIFIC_CAUSE,
        "integrity_failure": False,
        "cap_exhaustion": False,
        "terminal_is_infeasibility_certificate": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
        "logical_occurrence_closed": False,
        "production_violation_claimed": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
        "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        "official_scalar_cost": None,
        "official_N_break_even": None,
    }
    if any(document.get(key) != value for key, value in locks.items()):
        _fail("protocol terminal relabel or Gate unlock detected")
    payload = dict(document)
    claimed_bundle_id = payload.pop("protocol_failure_bundle_id")
    replayed_bundle_id = _local_id(PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN, payload)
    if claimed_bundle_id != replayed_bundle_id:
        _fail("protocol-failure bundle content ID changed")

    blocker = K7ProtocolFailureRealSiteBlockerV1._from_document(
        document["protocol_real_site_blocker"]
    )
    try:
        profile = ProtocolSequenceProfileV1.from_dict(
            document["protocol_sequence_profile"]
        )
        log = AccessEventLogV1.from_dict(document["access_event_log"])
        claimed_violation = ForbiddenAccessViolationV1.from_dict(
            document["forbidden_access_violation"]
        )
    except (AccessProtocolV1Error, TypeError, ValueError) as error:
        raise ConstructionK7ProtocolFailureAuthorityV1Error(
            "protocol profile, sequence, or violation bytes are invalid"
        ) from error
    if (
        log.route_attempt_id != attempt
        or log.decision_point_id != point
        or log.events[0].artifact_id != rapm
    ):
        _fail("protocol-failure evidence was transplanted away from its anchors")
    violation = _validate_canonical_fixture(profile, log)
    if claimed_violation.to_dict() != violation.to_dict():
        _fail("claimed violation differs from the first semantic replay failure")

    records, work, comparison = _materialize_complete_prefix(
        profile=profile, log=log, violation=violation
    )
    if (
        document["counter_record_ids"] != [row.record_id for row in records]
        or document["counter_records"] != [row.to_dict() for row in records]
        or document["last_valid_prefix_work_vector"] != work.to_dict()
        or document["last_valid_prefix_comparison_vector"]
        != comparison.to_dict()
    ):
        _fail("complete last-valid protocol prefix differs from independent replay")
    terminal = _terminal_for(
        blocker=blocker,
        profile=profile,
        log=log,
        violation=violation,
        records=records,
        work=work,
        comparison=comparison,
    )
    _parse_terminal(document["protocol_failure_terminal_authority"], terminal)

    return K7ProtocolFailureVerificationV1(
        _VERIFICATION_ISSUER,
        replayed_bundle_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
        blocker.blocker_id,
        profile.protocol_sequence_profile_id,
        log.access_event_log_id,
        violation.forbidden_access_violation_id,
        work.work_vector_id,
        comparison.comparison_vector_id,
        terminal.terminal_id,
        work,
        comparison,
    )


__all__ = [
    "BLOCKER_CODE",
    "ConstructionK7ProtocolFailureAuthorityV1Error",
    "EXPECTED_COUNTER_RECORD_COUNT",
    "K7ProtocolFailureBundleV1",
    "K7ProtocolFailureRealSiteBlockerV1",
    "K7ProtocolFailureTerminalAuthorityV1",
    "K7ProtocolFailureVerificationV1",
    "PROPOSED_CONTRACT_VERSION",
    "PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN",
    "ROUTE_KIND",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "canonical_k7_protocol_real_site_blocker_v1",
    "issue_canonical_k7_protocol_failure_bundle_v1",
    "verify_k7_protocol_failure_bundle_bytes_v1",
]
