"""Attempt-scoped wrapper retaining every V0-108 process-launch prefix.

The wrapper opens the V0-110A session before it asks the successor request to
replay itself, activates the fixed runtime launch sink around the complete
parent executor, and closes one immutable raw journal on success, typed
failure, or an otherwise escaping parent exception.  This is construction
evidence only: no raw count is promoted to a formal shared-resource value.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_attempt_process_supervisor_v1 as supervisor_v1
from acfqp import v075_k7_parent_atomic_executor_v1 as parent_v1
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ATTEMPT_PROCESS_ENVELOPE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.2"
PROFILE_KEY = "v075_k7_attempt_process_executor_v1"
CONNECTION_STATUS = "VERIFIED_ATTEMPT_WINDOW_RAW_SCOPE_INCOMPLETE"
LOCAL_DOMAINS = frozenset({V075_K7_ATTEMPT_PROCESS_ENVELOPE_V1_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("attempt-process executor domain is unregistered")

_ENVELOPE_ISSUER = object()


class V075K7AttemptProcessExecutorV1Error(RuntimeError):
    """The attempt wrapper, parent result, or raw journal was crossed."""


class V075K7AttemptProcessFinalizationV1Error(RuntimeError):
    """A wrapper failure retaining raw prefix evidence or a failure sentinel."""

    def __init__(
        self,
        message: str,
        *,
        raw_journal_bytes: bytes | None,
        emergency_prefix_bytes: bytes | None,
        emergency_prefix_snapshot: tuple[Any, ...] | None,
        original_exception_class: str,
    ) -> None:
        super().__init__(message)
        if (
            raw_journal_bytes is None
            and emergency_prefix_bytes is None
            and emergency_prefix_snapshot is None
        ):
            raise ValueError(
                "attempt finalization error requires retained prefix evidence"
            )
        self.raw_journal_bytes = raw_journal_bytes
        self.emergency_prefix_bytes = emergency_prefix_bytes
        self.emergency_prefix_snapshot = emergency_prefix_snapshot
        self.original_exception_class = original_exception_class


class AttemptScopedParentOutcomeV1(str, Enum):
    IDENTITY_BIND_FAILURE = "IDENTITY_BIND_FAILURE"
    PARENT_SUCCESS = "PARENT_SUCCESS"
    PARENT_TYPED_FAILURE = "PARENT_TYPED_FAILURE"
    PARENT_EXCEPTION = "PARENT_EXCEPTION"


def _fail(message: str) -> NoReturn:
    raise V075K7AttemptProcessExecutorV1Error(message)


def _hash(payload: Mapping[str, Any]) -> str:
    return content_id(V075_K7_ATTEMPT_PROCESS_ENVELOPE_V1_DOMAIN, dict(payload))


def _document(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise V075K7AttemptProcessExecutorV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{label} must be one canonical JSON object")
    return value


def _locks() -> dict[str, bool]:
    return {
        "attempt_wide_raw_process_evidence": False,
        "complete_attempt_wide_raw_process_evidence": False,
        "registered_prebind_through_parent_payload_raw_prefix": True,
        "independent_os_process_attestation_present": False,
        "semantic_source_evidence_verified": False,
        "eligible_as_shared_resource_resolution": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "attempt_terminal_issued": False,
        "plan_certificate_issued": False,
        "infeasibility_certificate_issued": False,
        "official_execution_allowed": False,
    }


@dataclass(frozen=True, slots=True)
class V075K7AttemptScopedParentEnvelopeV1:
    """Immutable join of one parent outcome and its raw launch journal."""

    _issuer: InitVar[object]
    outcome: AttemptScopedParentOutcomeV1
    parent_result: (
        parent_v1.V075K7ParentAtomicExecutionResultV1
        | parent_v1.V075K7ParentAtomicFailureV1
        | None
    ) = field(repr=False, compare=False)
    parent_exception_class: str | None
    parent_result_snapshot_bytes: bytes | None = field(
        repr=False, compare=False
    )
    journal: supervisor_v1.K7AttemptProcessRawJournalV1 = field(
        repr=False, compare=False
    )
    _frozen_payload_bytes: bytes = field(init=False, repr=False)
    _envelope_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ENVELOPE_ISSUER
            or type(self.journal)
            is not supervisor_v1.K7AttemptProcessRawJournalV1
        ):
            _fail("attempt-scoped parent envelope is caller-minted")
        try:
            outcome = AttemptScopedParentOutcomeV1(self.outcome)
        except (TypeError, ValueError) as error:
            raise V075K7AttemptProcessExecutorV1Error(
                "attempt-scoped parent outcome is unknown"
            ) from error
        object.__setattr__(self, "outcome", outcome)
        success = (
            type(self.parent_result)
            is parent_v1.V075K7ParentAtomicExecutionResultV1
        )
        typed_failure = (
            type(self.parent_result) is parent_v1.V075K7ParentAtomicFailureV1
        )
        if (
            (outcome is AttemptScopedParentOutcomeV1.PARENT_SUCCESS)
            != success
            or (
                outcome is AttemptScopedParentOutcomeV1.PARENT_TYPED_FAILURE
            )
            != typed_failure
            or (
                outcome
                in {
                    AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE,
                    AttemptScopedParentOutcomeV1.PARENT_EXCEPTION,
                }
            )
            != (self.parent_result is None)
            or (
                outcome
                in {
                    AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE,
                    AttemptScopedParentOutcomeV1.PARENT_EXCEPTION,
                }
            )
            != (self.parent_exception_class is not None)
            or (
                self.parent_exception_class is not None
                and (
                    type(self.parent_exception_class) is not str
                    or not self.parent_exception_class
                    or len(self.parent_exception_class) > 128
                )
            )
            or (self.parent_result is not None)
            != (self.parent_result_snapshot_bytes is not None)
        ):
            _fail("attempt-scoped parent outcome/result graph is inconsistent")
        parent_document = (
            None
            if self.parent_result_snapshot_bytes is None
            else _document(
                self.parent_result_snapshot_bytes,
                "frozen parent-result snapshot",
            )
        )
        if success and (
            self.journal.close_kind
            is not supervisor_v1.AttemptProcessCloseKindV1.SUCCESS
            or self.journal.observed_launch_count != 1
        ):
            _fail("successful parent result lacks its one-event raw journal")
        if (
            outcome is AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE
            and self.journal.close_kind
            not in {
                supervisor_v1.AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE,
                supervisor_v1.AttemptProcessCloseKindV1.PROTOCOL_FAILURE,
            }
        ):
            _fail("identity-bind failure crossed its raw journal")
        execution = self.journal.execution_document
        if (execution is None) != (
            outcome is AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE
        ):
            _fail("attempt-scoped envelope crossed its execution binding")
        if parent_document is not None:
            if (
                execution is None
                or parent_document.get("request_id")
                != execution.get("request_id")
            ):
                _fail("attempt-scoped envelope crossed its parent request")
            if success and (
                parent_document.get("route_identity_id")
                != execution.get("route_identity_id")
            ):
                _fail("attempt-scoped envelope crossed its parent route")
        snapshot = self._snapshot_payload()
        object.__setattr__(
            self, "_frozen_payload_bytes", canonical_json_bytes(snapshot)
        )
        object.__setattr__(self, "_envelope_id", _hash(snapshot))

    def _snapshot_payload(self) -> dict[str, Any]:
        parent_document = (
            None
            if self.parent_result_snapshot_bytes is None
            else _document(
                self.parent_result_snapshot_bytes,
                "frozen parent-result snapshot",
            )
        )
        execution = self.journal.execution_document
        return {
            "schema": "acfqp.v075_k7_attempt_scoped_parent_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": (
                None if execution is None else execution["request_id"]
            ),
            "route_identity_id": (
                None if execution is None else execution["route_identity_id"]
            ),
            "outcome": self.outcome.value,
            "parent_result": parent_document,
            "parent_exception_class": self.parent_exception_class,
            "two_frame_output_sha256": (
                None
                if parent_document is None
                else parent_document.get("two_frame_output_sha256")
            ),
            "two_frame_output_byte_count": (
                None
                if parent_document is None
                else parent_document.get("two_frame_output_byte_count")
            ),
            "raw_process_journal": self.journal.to_document(),
            "raw_process_journal_id": self.journal.raw_journal_id,
            "raw_observed_process_launches": (
                self.journal.observed_launch_count
            ),
            "process_connection_status": CONNECTION_STATUS,
            "caller_supplied_launch_total_accepted": False,
            "raw_count_is_not_formal_actual": True,
            **_locks(),
        }

    def _payload(self) -> dict[str, Any]:
        return _document(
            self._frozen_payload_bytes,
            "frozen attempt-scoped parent envelope payload",
        )

    @property
    def envelope_id(self) -> str:
        if _hash(self._payload()) != self._envelope_id:
            _fail("attempt-scoped parent envelope changed after issuance")
        return self._envelope_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attempt_scoped_parent_envelope_id": self.envelope_id,
        }


def _failure_close_kind(
    session: supervisor_v1.V075K7AttemptProcessSupervisorSessionV1,
) -> supervisor_v1.AttemptProcessCloseKindV1:
    return (
        supervisor_v1.AttemptProcessCloseKindV1.POSTLAUNCH_FAILURE
        if session.launch_edge_entered_count > 0
        else supervisor_v1.AttemptProcessCloseKindV1.PRELAUNCH_FAILURE
    )


def _freeze_parent_result_snapshot(
    *,
    session: supervisor_v1.V075K7AttemptProcessSupervisorSessionV1,
    result: (
        parent_v1.V075K7ParentAtomicExecutionResultV1
        | parent_v1.V075K7ParentAtomicFailureV1
    ),
) -> bytes:
    execution = session.execution
    if execution is None:
        _fail("parent result appeared before attempt identity binding")
    document = result.to_document()
    if document.get("request_id") != execution.request_id:
        _fail("parent result crossed the attempt request")
    if (
        type(result) is parent_v1.V075K7ParentAtomicExecutionResultV1
        and document.get("route_identity_id") != execution.route_identity_id
    ):
        _fail("successful parent result crossed the attempt route")
    return canonical_json_bytes(document)


def _raise_finalization_failure(
    *,
    session: supervisor_v1.V075K7AttemptProcessSupervisorSessionV1,
    journal: supervisor_v1.K7AttemptProcessRawJournalV1 | None,
    error: BaseException,
    message: str,
) -> NoReturn:
    raw_journal_bytes: bytes | None = None
    if journal is None:
        try:
            journal = session.journal
        except BaseException:
            journal = None
    if journal is not None:
        try:
            raw_journal_bytes = journal.canonical_bytes
        except BaseException:
            raw_journal_bytes = None
    emergency_prefix_bytes: bytes | None = None
    if raw_journal_bytes is None:
        try:
            emergency_prefix_bytes = session.emergency_prefix_bytes_v1()
        except BaseException:
            emergency_prefix_bytes = None
    emergency_prefix_snapshot: tuple[Any, ...] | None = None
    if raw_journal_bytes is None and emergency_prefix_bytes is None:
        try:
            emergency_prefix_snapshot = session.emergency_prefix_snapshot_v1()
        except BaseException as snapshot_error:
            emergency_prefix_snapshot = (
                "acfqp.v075_k7_attempt_process_unencoded_prefix_failure.v1",
                type(snapshot_error).__name__,
                type(error).__name__,
                False,
            )
    raise V075K7AttemptProcessFinalizationV1Error(
        message,
        raw_journal_bytes=raw_journal_bytes,
        emergency_prefix_bytes=emergency_prefix_bytes,
        emergency_prefix_snapshot=emergency_prefix_snapshot,
        original_exception_class=type(error).__name__,
    ) from error


def _issue_envelope_or_raise(
    *,
    session: supervisor_v1.V075K7AttemptProcessSupervisorSessionV1,
    outcome: AttemptScopedParentOutcomeV1,
    parent_result: (
        parent_v1.V075K7ParentAtomicExecutionResultV1
        | parent_v1.V075K7ParentAtomicFailureV1
        | None
    ),
    parent_exception_class: str | None,
    parent_result_snapshot_bytes: bytes | None,
    journal: supervisor_v1.K7AttemptProcessRawJournalV1,
) -> V075K7AttemptScopedParentEnvelopeV1:
    try:
        return V075K7AttemptScopedParentEnvelopeV1(
            _ENVELOPE_ISSUER,
            outcome,
            parent_result,
            parent_exception_class,
            parent_result_snapshot_bytes,
            journal,
        )
    except BaseException as error:
        _raise_finalization_failure(
            session=session,
            journal=journal,
            error=error,
            message=(
                "attempt envelope finalization failed after raw journal close"
            ),
        )


def execute_v075_k7_attempt_scoped_parent_v1(
    *,
    request: successor_v1.V075K7ParentOwnedSuccessorRequestV1,
    delegated_parent_fd: int,
    sealed_lifecycle_secret_fd: int,
    repository_root: Any,
    signer_private_root: Any,
    signer_private_key_path: Any,
) -> V075K7AttemptScopedParentEnvelopeV1:
    """Run one parent attempt under an earlier-opened write-ahead sink."""

    # This must remain the first attempt-owned operation.  The supervisor's
    # fixed-caller check also prevents callers from minting a standalone
    # "attempt-wide" zero journal.
    session = (
        supervisor_v1.start_v075_k7_attempt_process_supervisor_session_v1()
    )
    journal: supervisor_v1.K7AttemptProcessRawJournalV1 | None = None
    try:
        with session.activate_process_sink():
            try:
                session.bind_request(request)
            except BaseException as bind_error:
                outcome = AttemptScopedParentOutcomeV1.IDENTITY_BIND_FAILURE
                close_kind = (
                    supervisor_v1.AttemptProcessCloseKindV1.IDENTITY_BIND_FAILURE
                )
                parent_result = None
                parent_exception_class = type(bind_error).__name__
                parent_result_snapshot_bytes = None
            else:
                try:
                    result = parent_v1.execute_v075_k7_parent_atomic_attempt_v1(
                        request=request,
                        delegated_parent_fd=delegated_parent_fd,
                        sealed_lifecycle_secret_fd=sealed_lifecycle_secret_fd,
                        repository_root=repository_root,
                        signer_private_root=signer_private_root,
                        signer_private_key_path=signer_private_key_path,
                    )
                    if (
                        type(result)
                        is parent_v1.V075K7ParentAtomicExecutionResultV1
                    ):
                        outcome = AttemptScopedParentOutcomeV1.PARENT_SUCCESS
                        close_kind = (
                            supervisor_v1.AttemptProcessCloseKindV1.SUCCESS
                        )
                    elif type(result) is parent_v1.V075K7ParentAtomicFailureV1:
                        outcome = (
                            AttemptScopedParentOutcomeV1.PARENT_TYPED_FAILURE
                        )
                        close_kind = _failure_close_kind(session)
                    else:
                        raise V075K7AttemptProcessExecutorV1Error(
                            "parent contract returned a foreign object"
                        )
                    parent_result = result
                    parent_exception_class = None
                    parent_result_snapshot_bytes = (
                        _freeze_parent_result_snapshot(
                            session=session,
                            result=result,
                        )
                    )
                except BaseException as parent_error:
                    outcome = AttemptScopedParentOutcomeV1.PARENT_EXCEPTION
                    close_kind = _failure_close_kind(session)
                    parent_result = None
                    parent_exception_class = type(parent_error).__name__
                    parent_result_snapshot_bytes = None
            # Parent replay and publication payload freezing are complete.
            # Closing while the sink context is still installed makes any
            # late helper launch fail instead of silently escaping the window.
            journal = session.close(close_kind)
    except V075K7AttemptProcessFinalizationV1Error:
        raise
    except BaseException as error:
        if journal is None:
            if (
                session.state
                is supervisor_v1.AttemptProcessSessionStateV1.CLOSED
            ):
                _raise_finalization_failure(
                    session=session,
                    journal=None,
                    error=error,
                    message="attempt raw-journal closure failed",
                )
            try:
                journal = session.close(_failure_close_kind(session))
            except BaseException as close_error:
                _raise_finalization_failure(
                    session=session,
                    journal=None,
                    error=close_error,
                    message="attempt raw-journal closure failed",
                )
        _raise_finalization_failure(
            session=session,
            journal=journal,
            error=error,
            message="attempt sink finalization failed after raw journal close",
        )

    if journal is None:  # pragma: no cover - guarded by the close paths above
        _fail("attempt process journal disappeared after close")
    # A missing/extra launch converts the close to PROTOCOL_FAILURE.  Never
    # present a successful business result as a successful attempt envelope.
    if (
        outcome is AttemptScopedParentOutcomeV1.PARENT_SUCCESS
        and journal.close_kind
        is not supervisor_v1.AttemptProcessCloseKindV1.SUCCESS
    ):
        outcome = AttemptScopedParentOutcomeV1.PARENT_EXCEPTION
        parent_result = None
        parent_exception_class = "PROCESS_JOURNAL_PROTOCOL_FAILURE"
        parent_result_snapshot_bytes = None
    return _issue_envelope_or_raise(
        session=session,
        outcome=outcome,
        parent_result=parent_result,
        parent_exception_class=parent_exception_class,
        parent_result_snapshot_bytes=parent_result_snapshot_bytes,
        journal=journal,
    )


supervisor_v1._register_v075_k7_attempt_process_executor_callsite_v1(  # noqa: SLF001
    execute_v075_k7_attempt_scoped_parent_v1
)


__all__ = (
    "AttemptScopedParentOutcomeV1",
    "CONNECTION_STATUS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7AttemptProcessExecutorV1Error",
    "V075K7AttemptProcessFinalizationV1Error",
    "V075K7AttemptScopedParentEnvelopeV1",
    "execute_v075_k7_attempt_scoped_parent_v1",
)
