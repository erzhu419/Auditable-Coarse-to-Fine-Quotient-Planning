"""Owned five-stage K7 root-cap runner with partial native evidence.

The wrapped numerical result is the unchanged V2 result.  This successor only
adds an exact cold-cache lifecycle and a nonofficial partial-native transcript;
it emits no CounterRecord, WorkVector, ComparisonVector, or certificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
import threading
from typing import Any, Callable, Iterable, Mapping

from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN,
    V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN,
    V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)
from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_operational_context_v3 as operational_context
from acfqp import sequential_bernoulli_acquisition_v1 as bernoulli
from acfqp.construction_accounting_partial_native_v1 import (
    PartialNativeOccurrenceTranscriptV1,
    PartialNativeStageCompletionV1,
    PartialNativeTerminalKindV1,
    ROOT_CAP_FIVE_STAGE_PLAN_V1,
)
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution_identity
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_k7_root_cap_owned_partial_runner_v1"
RECORDER_ID = "v075-k7-root-cap-owned-partial-runner-v1"

COLD_CACHE_PROFILE_DOMAIN = V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN
COLD_CACHE_EPOCH_DOMAIN = V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN
OWNED_PARTIAL_RESULT_DOMAIN = V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN

_CACHE_PROFILE_ISSUER = object()
_CACHE_EPOCH_ISSUER = object()
_WRAPPER_RESULT_ISSUER = object()
_OWNED_PROCESS_LOCK = threading.Lock()


class V075K7RootCapOwnedPartialRunnerV1Error(RuntimeError):
    """An owned run failed; stage failures retain their aborted transcript."""

    def __init__(
        self,
        message: str,
        *,
        aborted_transcript: PartialNativeOccurrenceTranscriptV1 | None,
    ) -> None:
        super().__init__(message)
        self.aborted_transcript = aborted_transcript


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075K7RootCapOwnedPartialRunnerV1Error(
            f"{field_name} must be one exact content ID",
            aborted_transcript=None,
        ) from error


@dataclass(frozen=True, slots=True)
class V075K7RootCapColdCacheProfileV1:
    _issuer: InitVar[object]
    clear_authority_module: str
    clear_authority_symbol: str
    isolation_authority_symbol: str
    cleared_cache_symbols: tuple[str, ...]
    exclusive_owned_wrapper: bool

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CACHE_PROFILE_ISSUER
            or self.clear_authority_module
            != "acfqp.sequential_bernoulli_acquisition_v1"
            or self.clear_authority_symbol
            != "clear_exact_bernoulli_math_cache_v1"
            or self.isolation_authority_symbol
            != "isolate_exact_bernoulli_math_cache_v1"
            or self.cleared_cache_symbols
            != (
                "_beta_binomial_sequence_mass_cached_v1",
                "_outer_confidence_bounds_cached_v1",
            )
            or self.exclusive_owned_wrapper is not True
        ):
            raise V075K7RootCapOwnedPartialRunnerV1Error(
                "cold-cache profile changed",
                aborted_transcript=None,
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_cold_cache_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "clear_authority_module": self.clear_authority_module,
            "clear_authority_symbol": self.clear_authority_symbol,
            "isolation_authority_symbol": self.isolation_authority_symbol,
            "cleared_cache_symbols": list(self.cleared_cache_symbols),
            "clear_before_preopen_required": True,
            "clear_after_owned_scope_required": True,
            "exclusive_owned_wrapper": self.exclusive_owned_wrapper,
            "registered_cache_users_share_isolation_lock": True,
            "cache_state_changes_numerical_result": False,
        }

    @property
    def profile_id(self) -> str:
        return content_id(COLD_CACHE_PROFILE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cold_cache_profile_id": self.profile_id}


@lru_cache(maxsize=1)
def official_v075_k7_root_cap_cold_cache_profile_v1(
) -> V075K7RootCapColdCacheProfileV1:
    return V075K7RootCapColdCacheProfileV1(
        _CACHE_PROFILE_ISSUER,
        "acfqp.sequential_bernoulli_acquisition_v1",
        "clear_exact_bernoulli_math_cache_v1",
        "isolate_exact_bernoulli_math_cache_v1",
        (
            "_beta_binomial_sequence_mass_cached_v1",
            "_outer_confidence_bounds_cached_v1",
        ),
        True,
    )


@dataclass(frozen=True, slots=True)
class V075K7RootCapColdCacheEpochV1:
    _issuer: InitVar[object]
    profile_id: str
    occurrence_id: str
    schedule_id: str
    session_external_id_sha256: str

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CACHE_EPOCH_ISSUER:
            raise V075K7RootCapOwnedPartialRunnerV1Error(
                "cold-cache epoch is caller-minted",
                aborted_transcript=None,
            )
        for value, field_name in (
            (self.profile_id, "cold cache profile"),
            (self.occurrence_id, "cold cache occurrence"),
            (self.schedule_id, "cold cache schedule"),
            (self.session_external_id_sha256, "session external ID digest"),
        ):
            _cid(value, field_name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_cold_cache_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "cold_cache_profile_id": self.profile_id,
            "occurrence_id": self.occurrence_id,
            "schedule_id": self.schedule_id,
            "session_external_id_sha256": self.session_external_id_sha256,
            "exclusive_owned_wrapper_lock_acquired": True,
            "clear_before_preopen_committed": True,
            "clear_after_owned_scope_required": True,
        }

    @property
    def epoch_id(self) -> str:
        return content_id(COLD_CACHE_EPOCH_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cold_cache_epoch_id": self.epoch_id}


def _freeze_cold_cache_epoch(
    *,
    profile: V075K7RootCapColdCacheProfileV1,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    session_external_id: str,
) -> V075K7RootCapColdCacheEpochV1:
    return V075K7RootCapColdCacheEpochV1(
        _CACHE_EPOCH_ISSUER,
        profile.profile_id,
        schedule.occurrence.occurrence_id,
        schedule.schedule_id,
        hashlib.sha256(session_external_id.encode("utf-8")).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class V075K7RootCapOwnedPartialResultV1:
    _issuer: InitVar[object]
    result: runner.V075ObserverSignedMultiroundResultV2 = field(repr=False)
    transcript: PartialNativeOccurrenceTranscriptV1 = field(repr=False)
    cold_cache_profile: V075K7RootCapColdCacheProfileV1 = field(repr=False)
    cold_cache_epoch: V075K7RootCapColdCacheEpochV1 = field(repr=False)
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str

    def __post_init__(self, _issuer: object) -> None:
        for value, field_name in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.boundary_profile_id, "boundary profile"),
            (self.execution_profile_id, "execution identity profile"),
        ):
            _cid(value, field_name)
        completions = tuple(
            node
            for node in self.transcript.nodes
            if type(node) is PartialNativeStageCompletionV1
        )
        execution_profile = (
            execution_identity
            .official_v075_k7_root_cap_execution_identity_profile_v1()
        )
        if (
            _issuer is not _WRAPPER_RESULT_ISSUER
            or type(self.result)
            is not runner.V075ObserverSignedMultiroundResultV2
            or self.result.status
            is not (
                runner.V075ObserverSignedMultiroundTerminalStatusV2
                .CHILD_ACTION_ROW_CAP_EXCEEDED
            )
            or type(self.transcript)
            is not PartialNativeOccurrenceTranscriptV1
            or self.transcript.terminal_kind
            is not PartialNativeTerminalKindV1.COMPLETED
            or self.transcript.start.stage_plan != ROOT_CAP_FIVE_STAGE_PLAN_V1
            or self.transcript.start.counter_registry_id
            != self.counter_registry_id
            or self.transcript.start.stage_profile_id != self.stage_profile_id
            or self.transcript.start.boundary_profile_id
            != self.boundary_profile_id
            or self.execution_profile_id != execution_profile.profile_id
            or execution_profile.boundary_manifest_id
            != self.boundary_profile_id
            or len(completions) != 5
            or dict(
                (row.role, row.artifact_id)
                for row in completions[0].output_bindings
            ).get("cold_cache_profile")
            != self.cold_cache_profile.profile_id
            or dict(
                (row.role, row.artifact_id)
                for row in completions[0].output_bindings
            ).get("cold_cache_epoch")
            != self.cold_cache_epoch.epoch_id
            or dict(
                (row.role, row.artifact_id)
                for row in completions[0].output_bindings
            ).get("execution_profile")
            != self.execution_profile_id
            or dict(
                (row.role, row.artifact_id)
                for row in completions[-1].output_bindings
            ).get("multiround_result")
            != self.result.result_id
        ):
            raise V075K7RootCapOwnedPartialRunnerV1Error(
                "owned K7 partial wrapper binding changed",
                aborted_transcript=None,
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_owned_partial_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "original_result_id": self.result.result_id,
            "partial_native_transcript_id": self.transcript.transcript_id,
            "cold_cache_profile_id": self.cold_cache_profile.profile_id,
            "cold_cache_epoch_id": self.cold_cache_epoch.epoch_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "execution_profile_id": self.execution_profile_id,
            "terminal_status": self.result.status.value,
            "coverage_state": self.transcript.coverage_state,
            "cold_cache_cleared_before_preopen": True,
            "cold_cache_cleared_after_owned_scope": True,
            "evidence_sink_policy": (
                "COOPERATIVE_SAME_PROCESS_DEFERRED_AFTER_"
                "AUTHORITY_CLOSURE"
            ),
            "adversarial_callback_isolation_claimed": False,
            "original_v2_result_bytes_changed": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "official_execution_allowed": False,
            "certificate_issued": False,
        }

    @property
    def wrapper_id(self) -> str:
        return content_id(OWNED_PARTIAL_RESULT_DOMAIN, self._payload())

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owned_partial_result_id": self.wrapper_id}


def run_v075_k7_root_cap_owned_partial_v1(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Any]]],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
    evidence_sink: Callable[[Mapping[str, Any]], Any] | None = None,
) -> V075K7RootCapOwnedPartialResultV1:
    """Run one exclusive cold-cache K7 root-cap partial evidence occurrence."""

    execution_profile = (
        execution_identity
        .official_v075_k7_root_cap_execution_identity_profile_v1()
    )
    try:
        execution_identity.validate_v075_k7_root_cap_execution_identity_v1(
            profile=execution_profile,
            repository_root=repository_root,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=schedule_verification,
        )
    except execution_identity.V075K7RootCapExecutionIdentityV1Error as error:
        raise V075K7RootCapOwnedPartialRunnerV1Error(
            "owned K7 root-cap execution identity rejected",
            aborted_transcript=None,
        ) from error

    if not _OWNED_PROCESS_LOCK.acquire(blocking=False):
        raise V075K7RootCapOwnedPartialRunnerV1Error(
            "owned K7 root-cap execution is already active in this process",
            aborted_transcript=None,
        )
    session = None
    captured_evidence: list[Mapping[str, Any]] = []

    def capture_evidence(roots: Mapping[str, Any]) -> None:
        if captured_evidence:
            raise V075K7RootCapOwnedPartialRunnerV1Error(
                "owned K7 evidence roots were emitted more than once",
                aborted_transcript=None,
            )
        captured_evidence.append(roots)

    try:
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        boundary = official_k7_root_cap_operation_boundary_manifest_v3()
        cache_profile = official_v075_k7_root_cap_cold_cache_profile_v1()
        try:
            with bernoulli.isolate_exact_bernoulli_math_cache_v1():
                bernoulli.clear_exact_bernoulli_math_cache_v1()
                cache_epoch = _freeze_cold_cache_epoch(
                    profile=cache_profile,
                    schedule=schedule,
                    session_external_id=session_external_id,
                )
                try:
                    with accounting_runtime.activate_owned_construction_accounting_v1(
                        occurrence_id=schedule.occurrence.occurrence_id,
                        recorder_id=RECORDER_ID,
                        counter_registry=registry,
                        stage_profile=stage,
                        boundary_profile=boundary,
                    ) as active_session:
                        session = active_session
                        with operational_context._activate_owned_no_full_replay_v3():  # noqa: SLF001
                            result = (
                                runner
                                ._run_v075_k7_root_cap_owned_partial_driver_v1(  # noqa: SLF001
                                    cold_cache_epoch_id=cache_epoch.epoch_id,
                                    cold_cache_profile_id=(
                                        cache_profile.profile_id
                                    ),
                                    execution_profile_id=(
                                        execution_profile.profile_id
                                    ),
                                    repository_root=repository_root,
                                    namespace=namespace,
                                    schedule=schedule,
                                    schedule_verification=(
                                        schedule_verification
                                    ),
                                    authority=authority,
                                    private_salt=private_salt,
                                    private_environment=private_environment,
                                    observer_signer=observer_signer,
                                    session_external_id=session_external_id,
                                    evidence_sink=(
                                        capture_evidence
                                        if evidence_sink is not None
                                        else None
                                    ),
                                )
                            )
                            if len(captured_evidence) != (
                                1 if evidence_sink is not None else 0
                            ):
                                raise V075K7RootCapOwnedPartialRunnerV1Error(
                                    "owned K7 evidence-root capture changed",
                                    aborted_transcript=None,
                                )
                            transcript = (
                                accounting_runtime.complete_owned_occurrence_v1()
                            )
                finally:
                    # This executes after the accounting and operational
                    # scopes have terminalized, while every other registered
                    # cache user remains excluded by the isolation lock.
                    bernoulli.clear_exact_bernoulli_math_cache_v1()
            if transcript is None:  # pragma: no cover - active by construction
                raise V075K7RootCapOwnedPartialRunnerV1Error(
                    "owned partial transcript was not emitted",
                    aborted_transcript=None,
                )
            wrapped = V075K7RootCapOwnedPartialResultV1(
                _WRAPPER_RESULT_ISSUER,
                result,
                transcript,
                cache_profile,
                cache_epoch,
                registry.registry_id,
                stage.stage_profile_id,
                boundary.manifest_id,
                execution_profile.profile_id,
            )
            if evidence_sink is not None:
                roots = captured_evidence[0]
                snapshotter = runner._snapshot_construction_evidence_roots  # noqa: SLF001
                before = snapshotter(roots)
                try:
                    # The cooperative caller callback receives no active
                    # accounting, operational or cold-cache authority.  This
                    # is deliberately not an adversarial process sandbox.
                    evidence_sink(roots)
                except Exception as error:
                    raise V075K7RootCapOwnedPartialRunnerV1Error(
                        "deferred construction evidence sink failed",
                        aborted_transcript=None,
                    ) from error
                if snapshotter(roots) != before:
                    raise V075K7RootCapOwnedPartialRunnerV1Error(
                        "deferred evidence sink mutated immutable typed roots",
                        aborted_transcript=None,
                    )
            return wrapped
        except Exception as error:
            aborted = None
            if session is not None and session.is_terminal:
                candidate = session.transcript
                if candidate.terminal_kind is PartialNativeTerminalKindV1.ABORTED:
                    aborted = candidate
            if isinstance(error, V075K7RootCapOwnedPartialRunnerV1Error):
                if error.aborted_transcript is not None:
                    raise
            raise V075K7RootCapOwnedPartialRunnerV1Error(
                "owned K7 root-cap partial execution failed",
                aborted_transcript=aborted,
            ) from error
    finally:
        _OWNED_PROCESS_LOCK.release()


__all__ = [
    "COLD_CACHE_EPOCH_DOMAIN",
    "COLD_CACHE_PROFILE_DOMAIN",
    "OWNED_PARTIAL_RESULT_DOMAIN",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V075K7RootCapColdCacheEpochV1",
    "V075K7RootCapColdCacheProfileV1",
    "V075K7RootCapOwnedPartialResultV1",
    "V075K7RootCapOwnedPartialRunnerV1Error",
    "official_v075_k7_root_cap_cold_cache_profile_v1",
    "run_v075_k7_root_cap_owned_partial_v1",
]
