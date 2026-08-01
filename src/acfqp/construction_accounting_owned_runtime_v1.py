"""Inactive-by-default runtime for owner-bound partial native events.

Source modules may call :func:`emit_owned_operation_v1` unconditionally.
Without an explicitly activated trusted binding it is a no-op.  An active binding
fixes one exact registry, stage profile and operation-boundary profile, then
fails closed on every identity, site, path, reducer, stage, amount, nesting,
or thread-ownership mismatch.

This runtime emits only :mod:`construction_accounting_partial_native_v1`
chain nodes.  It does not emit counters, work vectors, comparisons, native
zeroes, or official-execution evidence.  The owned K7 wrapper and registered
primitive operation sites consume this API; this module still performs no
implicit installation at import time.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
import importlib
import re
import sys
import threading
from typing import Any, Iterator

from acfqp.accounting_v1 import ReducerEnum
from acfqp.construction_accounting_partial_native_v1 import (
    PartialNativeOccurrenceAbortV1,
    PartialNativeOccurrenceCompletionV1,
    PartialNativeOccurrenceStartV1,
    PartialNativeOccurrenceTranscriptV1,
    PartialNativeNotApplicableV1,
    PartialNativeOperationEventV1,
    PartialNativeOutputBindingV1,
    PartialNativeStageCompletionV1,
    PartialNativeStageStartV1,
    PartialNativeStageV1,
    ROOT_CAP_FIVE_STAGE_PLAN_V1,
    NO_ACTIVE_STAGE_REASON,
    NO_EXCEPTION_REASON,
    UNREPRESENTABLE_EXCEPTION_REASON,
)
from acfqp.phase3e_ids import parse_content_id


class OwnedConstructionAccountingRuntimeV1Error(RuntimeError):
    """The active owner-bound accounting protocol failed closed."""


_ACTIVE_RUNTIME: ContextVar["OwnedConstructionAccountingSessionV1 | None"] = (
    ContextVar("acfqp_owned_construction_accounting_runtime_v1", default=None)
)
_ABORT_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")
_DISPATCH_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise OwnedConstructionAccountingRuntimeV1Error(
            f"{field_name} must be an exact content ID"
        ) from error


def _stage_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    if type(raw) is not str:
        raise OwnedConstructionAccountingRuntimeV1Error(
            "stage value must be a string enum value"
        )
    return raw


def _partial_stage(value: Any) -> PartialNativeStageV1:
    try:
        return PartialNativeStageV1(_stage_value(value))
    except (TypeError, ValueError) as error:
        raise OwnedConstructionAccountingRuntimeV1Error(
            f"stage {value!r} is outside the five-stage partial profile"
        ) from error


def _profile_id(profile: Any, *names: str) -> str:
    found = [getattr(profile, name) for name in names if hasattr(profile, name)]
    if len(found) != 1:
        raise OwnedConstructionAccountingRuntimeV1Error(
            f"profile must expose exactly one of {names!r}"
        )
    return _cid(found[0], names[0])


def _stage_rule(stage_profile: Any, stage: PartialNativeStageV1) -> Any:
    by_stage = getattr(stage_profile, "by_stage", None)
    if type(by_stage) is not dict:
        raise OwnedConstructionAccountingRuntimeV1Error(
            "stage profile has no exact by-stage mapping"
        )
    matches = [
        rule for key, rule in by_stage.items() if _stage_value(key) == stage.value
    ]
    if len(matches) != 1:
        raise OwnedConstructionAccountingRuntimeV1Error(
            f"stage profile does not bind {stage.value} exactly once"
        )
    return matches[0]


def _classification_allows_emission(boundary: Any) -> bool:
    value = _stage_value(getattr(boundary, "classification", ""))
    return value.endswith("SCHEMA_ONLY") and "NATIVE_ZERO" not in value


def _operation_owner_binding(module_name: Any, symbol: Any) -> tuple[Any, Any]:
    """Resolve and freeze one owner's module-globals and code identities."""

    if type(module_name) is not str or type(symbol) is not str:
        return (None, None)
    try:
        module = importlib.import_module(module_name)
        selected = module
        for component in symbol.split("."):
            selected = getattr(selected, component)
    except (AttributeError, ImportError):
        return (None, None)
    function = getattr(selected, "__func__", selected)
    return (module.__dict__, getattr(function, "__code__", None))


def _safe_exception_identifier(value: Any) -> bool:
    return (
        type(value) is str
        and 0 < len(value) <= 512
        and all(33 <= ord(character) <= 126 for character in value)
    )


class OwnedConstructionAccountingSessionV1:
    """One thread-owned, exact five-stage partial-native occurrence."""

    def __init__(
        self,
        *,
        occurrence_id: str,
        recorder_id: str,
        counter_registry: Any,
        stage_profile: Any,
        boundary_profile: Any,
        allow_low_level_test_api: bool = False,
    ) -> None:
        self._lock = threading.RLock()
        self._owner_thread_id = threading.get_ident()
        self._counter_registry = counter_registry
        self._stage_profile = stage_profile
        self._boundary_profile = boundary_profile
        if type(allow_low_level_test_api) is not bool:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "low-level test API flag must be an exact bool"
            )
        self._allow_low_level_test_api = allow_low_level_test_api
        self._validate_binding()
        self._start = PartialNativeOccurrenceStartV1(
            occurrence_id=_cid(occurrence_id, "occurrence_id"),
            counter_registry_id=self.counter_registry_id,
            stage_profile_id=self.stage_profile_id,
            boundary_profile_id=self.boundary_profile_id,
            recorder_id=recorder_id,
        )
        self._nodes: list[Any] = []
        self._active_stage: PartialNativeStageV1 | None = None
        self._completed_stage_count = 0
        self._stage_event_count = 0
        self._total_event_count = 0
        self._terminal = False

    def _validate_binding(self) -> None:
        registry_id = _profile_id(self._counter_registry, "registry_id")
        stage_id = _profile_id(self._stage_profile, "stage_profile_id")
        boundary_id = _profile_id(
            self._boundary_profile, "boundary_profile_id", "manifest_id"
        )
        if _cid(getattr(self._stage_profile, "counter_registry_id", None), "stage counter_registry_id") != registry_id:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "stage profile is bound to a different counter registry"
            )
        if _cid(getattr(self._boundary_profile, "counter_registry_id", None), "boundary counter_registry_id") != registry_id:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "boundary profile is bound to a different counter registry"
            )
        if _cid(getattr(self._boundary_profile, "stage_profile_id", None), "boundary stage_profile_id") != stage_id:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "boundary profile is bound to a different stage profile"
            )
        for authority in (
            self._counter_registry,
            self._stage_profile,
            self._boundary_profile,
        ):
            validator = getattr(authority, "validate_official", None)
            if validator is None:
                validator = getattr(authority, "validate_official_catalogue", None)
            if validator is not None:
                try:
                    if authority is self._stage_profile:
                        validator(self._counter_registry)
                    else:
                        validator()
                except TypeError as error:
                    # Some additive stage profiles expose ``validate(registry)``
                    # rather than an official wrapper.
                    raise OwnedConstructionAccountingRuntimeV1Error(
                        "authority validator has an unsupported signature"
                    ) from error
                except Exception as error:
                    raise OwnedConstructionAccountingRuntimeV1Error(
                        "authority rejected the exact active binding"
                    ) from error
        stage_validator = getattr(self._stage_profile, "validate", None)
        if stage_validator is not None:
            try:
                stage_validator(self._counter_registry)
            except Exception as error:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "stage authority rejected the exact active binding"
                ) from error
        boundary_document = getattr(self._boundary_profile, "to_document", None)
        if boundary_document is not None:
            document = boundary_document()
            if type(document) is not dict or boundary_id not in document.values():
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "boundary-profile document omits its exact content ID"
                )
        by_path = getattr(self._counter_registry, "by_path", None)
        by_key = getattr(self._boundary_profile, "by_key", None)
        if type(by_path) is not dict or type(by_key) is not dict or not by_key:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "registry or boundary profile lacks its exact lookup map"
            )
        owner_bindings: dict[str, tuple[Any, Any]] = {}
        for site_id, boundary in by_key.items():
            if site_id != getattr(boundary, "boundary_key", site_id):
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "boundary lookup key differs from its site identity"
                )
            path = getattr(boundary, "target_path", None)
            if path not in by_path:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    f"boundary site {site_id!r} names an unknown path"
                )
            leaf = by_path[path]
            try:
                reducer = ReducerEnum(getattr(boundary, "reducer", None))
            except (TypeError, ValueError) as error:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    f"boundary site {site_id!r} has an invalid reducer"
                ) from error
            if reducer is not ReducerEnum(getattr(leaf, "reducer", None)):
                raise OwnedConstructionAccountingRuntimeV1Error(
                    f"boundary site {site_id!r} reducer differs from the registry"
                )
            try:
                stage = _partial_stage(getattr(boundary, "stage"))
            except OwnedConstructionAccountingRuntimeV1Error:
                # A generic manifest may also describe other profiles.  Such
                # sites remain unreachable in this exact five-stage binding.
                continue
            rule = _stage_rule(self._stage_profile, stage)
            if path not in tuple(getattr(rule, "allowed_nonzero_paths", ())):
                raise OwnedConstructionAccountingRuntimeV1Error(
                    f"boundary site {site_id!r} is outside its registered stage"
                )
            if _classification_allows_emission(boundary):
                owner_binding = _operation_owner_binding(
                    getattr(boundary, "operation_source_module", None),
                    getattr(boundary, "operation_source_symbol", None),
                )
                if None in owner_binding:
                    raise OwnedConstructionAccountingRuntimeV1Error(
                        f"boundary site {site_id!r} owner code is unavailable"
                    )
                owner_bindings[site_id] = owner_binding
        self.counter_registry_id = registry_id
        self.stage_profile_id = stage_id
        self.boundary_profile_id = boundary_id
        self._owner_bindings = owner_bindings

    @property
    def occurrence_start(self) -> PartialNativeOccurrenceStartV1:
        return self._start

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    @property
    def active_stage(self) -> PartialNativeStageV1 | None:
        return self._active_stage

    @property
    def transcript(self) -> PartialNativeOccurrenceTranscriptV1:
        if not self._terminal:
            raise OwnedConstructionAccountingRuntimeV1Error(
                "partial transcript is unavailable before completion or abort"
            )
        return PartialNativeOccurrenceTranscriptV1(
            self._start, tuple(self._nodes)
        )

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner_thread_id:
            self._protocol_abort(
                "CROSS_THREAD_ACTIVE_SCOPE",
                exception_type=OwnedConstructionAccountingRuntimeV1Error,
            )
            raise OwnedConstructionAccountingRuntimeV1Error(
                "active owned accounting scope crossed its owner thread"
            )

    def _next_predecessor(self) -> str:
        return self._nodes[-1].chain_id if self._nodes else self._start.chain_id

    def _event_ids(self) -> tuple[str, ...]:
        return tuple(
            node.event_id
            for node in self._nodes
            if type(node) is PartialNativeOperationEventV1
        )

    def _protocol_abort(
        self,
        reason: str,
        *,
        exception_type: type[BaseException] | None = None,
    ) -> None:
        with self._lock:
            if self._terminal:
                return
            active_index: int | PartialNativeNotApplicableV1
            active_kind: PartialNativeStageV1 | PartialNativeNotApplicableV1
            if self._active_stage is None:
                active_index = PartialNativeNotApplicableV1(
                    NO_ACTIVE_STAGE_REASON
                )
                active_kind = PartialNativeNotApplicableV1(
                    NO_ACTIVE_STAGE_REASON
                )
            else:
                active_index = self._completed_stage_count + 1
                active_kind = self._active_stage
            if exception_type is None:
                exception_module: str | PartialNativeNotApplicableV1 = (
                    PartialNativeNotApplicableV1(NO_EXCEPTION_REASON)
                )
                exception_qualname: str | PartialNativeNotApplicableV1 = (
                    PartialNativeNotApplicableV1(NO_EXCEPTION_REASON)
                )
            else:
                try:
                    candidate_module = exception_type.__module__
                    candidate_qualname = exception_type.__qualname__
                except BaseException:  # pragma: no cover - hostile metaclass
                    candidate_module = None
                    candidate_qualname = None
                if _safe_exception_identifier(
                    candidate_module
                ) and _safe_exception_identifier(candidate_qualname):
                    exception_module = candidate_module
                    exception_qualname = candidate_qualname
                else:
                    exception_module = PartialNativeNotApplicableV1(
                        UNREPRESENTABLE_EXCEPTION_REASON
                    )
                    exception_qualname = PartialNativeNotApplicableV1(
                        UNREPRESENTABLE_EXCEPTION_REASON
                    )
            self._nodes.append(
                PartialNativeOccurrenceAbortV1(
                    occurrence_start_id=self._start.start_id,
                    occurrence_id=self._start.occurrence_id,
                    counter_registry_id=self.counter_registry_id,
                    stage_profile_id=self.stage_profile_id,
                    boundary_profile_id=self.boundary_profile_id,
                    chain_sequence=len(self._nodes) + 1,
                    predecessor_chain_id=self._next_predecessor(),
                    completed_stage_count=self._completed_stage_count,
                    total_event_count=self._total_event_count,
                    emitted_event_ids=self._event_ids(),
                    aborted_stage_index=active_index,
                    aborted_stage_kind=active_kind,
                    exception_module=exception_module,
                    exception_qualname=exception_qualname,
                    reason=reason,
                )
            )
            self._terminal = True

    def _fail(self, reason: str, detail: str) -> None:
        self._protocol_abort(
            reason, exception_type=OwnedConstructionAccountingRuntimeV1Error
        )
        raise OwnedConstructionAccountingRuntimeV1Error(detail)

    def enter_stage(self, stage: Any) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            try:
                selected = _partial_stage(stage)
            except OwnedConstructionAccountingRuntimeV1Error:
                self._fail(
                    "STAGE_OUTSIDE_FIVE_STAGE_PROFILE",
                    "stage entry is outside the exact five-stage profile",
                )
                raise AssertionError("unreachable")
            if self._completed_stage_count >= len(
                ROOT_CAP_FIVE_STAGE_PLAN_V1
            ):
                self._fail(
                    "FIVE_STAGE_PLAN_EXHAUSTED",
                    "all five partial-native stages are already complete",
                )
            expected = ROOT_CAP_FIVE_STAGE_PLAN_V1[self._completed_stage_count]
            if self._active_stage is not None or selected is not expected:
                self._fail(
                    "STAGE_ORDER_VIOLATION",
                    "stage entry differs from the exact five-stage plan",
                )
            self._nodes.append(
                PartialNativeStageStartV1(
                    occurrence_start_id=self._start.start_id,
                    occurrence_id=self._start.occurrence_id,
                    counter_registry_id=self.counter_registry_id,
                    stage_profile_id=self.stage_profile_id,
                    boundary_profile_id=self.boundary_profile_id,
                    chain_sequence=len(self._nodes) + 1,
                    predecessor_chain_id=self._next_predecessor(),
                    stage_index=self._completed_stage_count + 1,
                    stage_kind=selected,
                )
            )
            self._active_stage = selected
            self._stage_event_count = 0

    def _emit_bound_boundary(self, boundary: Any, amount: Any) -> None:
        if type(amount) is not int or amount <= 0:
            self._fail(
                "NONPOSITIVE_OR_INEXACT_AMOUNT",
                "owned SUM amount must be a positive exact integer",
            )
        if self._active_stage is None:
            self._fail(
                "EVENT_OUTSIDE_ACTIVE_STAGE",
                "owned operation event has no active stage",
            )
        site_id = getattr(boundary, "boundary_key", None)
        path = getattr(boundary, "target_path", None)
        if type(site_id) is not str or type(path) is not str:
            self._fail(
                "MALFORMED_BOUNDARY_BINDING",
                "selected boundary has no exact site or path",
            )
        if not _classification_allows_emission(boundary):
            self._fail(
                "NONEMITTABLE_OPERATION_SITE",
                f"site {site_id!r} is native-zero or schema-forbidden",
            )
        try:
            boundary_stage = _partial_stage(getattr(boundary, "stage", None))
        except OwnedConstructionAccountingRuntimeV1Error:
            self._fail(
                "SITE_STAGE_MISMATCH",
                f"site {site_id!r} is outside the five-stage profile",
            )
            raise AssertionError("unreachable")
        if boundary_stage is not self._active_stage:
            self._fail(
                "SITE_STAGE_MISMATCH",
                f"site {site_id!r} is outside the active stage",
            )
        leaf = getattr(self._counter_registry, "by_path", {}).get(path)
        try:
            leaf_reducer = ReducerEnum(getattr(leaf, "reducer", None))
            boundary_reducer = ReducerEnum(
                getattr(boundary, "reducer", None)
            )
        except (TypeError, ValueError) as error:
            self._fail(
                "REDUCER_BINDING_INVALID",
                "site or registry reducer is invalid",
            )
            raise AssertionError("unreachable") from error
        if (
            leaf_reducer is not ReducerEnum.SUM
            or boundary_reducer is not ReducerEnum.SUM
        ):
            self._fail(
                "REDUCER_MISMATCH",
                "owned operation requires an exact SUM binding",
            )
        rule = _stage_rule(self._stage_profile, self._active_stage)
        if path not in tuple(getattr(rule, "allowed_nonzero_paths", ())):
            self._fail(
                "STAGE_PROFILE_PATH_MISMATCH",
                "counter path is outside the active stage profile",
            )
        self._nodes.append(
            PartialNativeOperationEventV1(
                occurrence_start_id=self._start.start_id,
                occurrence_id=self._start.occurrence_id,
                counter_registry_id=self.counter_registry_id,
                stage_profile_id=self.stage_profile_id,
                boundary_profile_id=self.boundary_profile_id,
                chain_sequence=len(self._nodes) + 1,
                predecessor_chain_id=self._next_predecessor(),
                stage_index=self._completed_stage_count + 1,
                stage_kind=self._active_stage,
                stage_event_sequence=self._stage_event_count + 1,
                site_id=site_id,
                path=path,
                reducer=ReducerEnum.SUM,
                amount=amount,
            )
        )
        self._stage_event_count += 1
        self._total_event_count += 1

    def emit_operation(
        self,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        caller_module: Any,
        caller_globals: Any,
        caller_code: Any,
    ) -> None:
        """Resolve one owner- and stage-bound operation inside the binding."""

        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            if self._active_stage is None:
                self._fail(
                    "EVENT_OUTSIDE_ACTIVE_STAGE",
                    "owned operation event has no active stage",
                )
            if (
                type(dispatch_key) is not str
                or _DISPATCH_KEY.fullmatch(dispatch_key) is None
            ):
                self._fail(
                    "MALFORMED_DISPATCH_KEY",
                    "operation dispatch key must be a canonical stage-neutral key",
                )
            if type(amount) is not int or amount != 1:
                self._fail(
                    "PRODUCTION_AMOUNT_NOT_UNIT",
                    "each production operation event must represent one primitive",
                )
            matches = tuple(
                boundary
                for boundary in getattr(
                    self._boundary_profile, "boundaries", ()
                )
                if _classification_allows_emission(boundary)
                and getattr(boundary, "dispatch_key", None) == dispatch_key
                and _stage_value(getattr(boundary, "stage", None))
                == self._active_stage.value
            )
            if len(matches) == 0:
                self._fail(
                    "UNKNOWN_OR_STAGE_UNBOUND_DISPATCH",
                    "dispatch key has no emittable boundary in the active stage",
                )
            if len(matches) > 1:
                self._fail(
                    "AMBIGUOUS_STAGE_DISPATCH",
                    "dispatch key has multiple emittable boundaries in the active stage",
                )
            boundary = matches[0]
            expected_globals, expected_code = self._owner_bindings.get(
                getattr(boundary, "boundary_key", ""),
                (None, None),
            )
            if (
                type(caller_module) is not str
                or caller_module
                != getattr(boundary, "operation_source_module", None)
                or caller_globals is not expected_globals
                or caller_code is not expected_code
            ):
                self._fail(
                    "OPERATION_OWNER_MISMATCH",
                    "dispatch caller differs from the registered operation owner",
                )
            self._emit_bound_boundary(boundary, amount)

    def emit_sum(self, site_id: Any, path: Any, amount: Any = 1) -> None:
        """Low-level explicit-boundary API for verifier/unit tests only."""

        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            if not self._allow_low_level_test_api:
                self._fail(
                    "LOW_LEVEL_API_FORBIDDEN",
                    "explicit site/path emission is disabled in production scopes",
                )
            if self._active_stage is None:
                self._fail(
                    "EVENT_OUTSIDE_ACTIVE_STAGE",
                    "owned operation event has no active stage",
                )
            if type(site_id) is not str or type(path) is not str:
                self._fail(
                    "MALFORMED_SITE_OR_PATH",
                    "owned site and path must be exact strings",
                )
            boundary = getattr(self._boundary_profile, "by_key", {}).get(site_id)
            if boundary is None:
                self._fail("UNKNOWN_OPERATION_SITE", f"unknown site {site_id!r}")
            if getattr(boundary, "target_path", None) != path:
                self._fail(
                    "SITE_PATH_MISMATCH",
                    f"site {site_id!r} is not bound to path {path!r}",
                )
            self._emit_bound_boundary(boundary, amount)

    def exit_stage(
        self,
        stage: Any | None = None,
        *,
        output_bindings: Any = (),
    ) -> None:
        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            if self._active_stage is None:
                self._fail(
                    "STAGE_EXIT_WITHOUT_ENTRY",
                    "stage exit has no active stage",
                )
            if stage is not None and _partial_stage(stage) is not self._active_stage:
                self._fail(
                    "STAGE_EXIT_MISMATCH",
                    "stage exit differs from the active stage",
                )
            try:
                outputs = tuple(
                    row
                    if type(row) is PartialNativeOutputBindingV1
                    else PartialNativeOutputBindingV1(*row)
                    for row in output_bindings
                )
                if tuple(sorted(outputs)) != outputs:
                    raise ValueError("output bindings are not sorted")
            except (TypeError, ValueError) as error:
                self._fail(
                    "MALFORMED_STAGE_OUTPUT_BINDINGS",
                    "stage outputs must be sorted (role, content_id) bindings",
                )
                raise AssertionError("unreachable") from error
            selected = self._active_stage
            self._nodes.append(
                PartialNativeStageCompletionV1(
                    occurrence_start_id=self._start.start_id,
                    occurrence_id=self._start.occurrence_id,
                    counter_registry_id=self.counter_registry_id,
                    stage_profile_id=self.stage_profile_id,
                    boundary_profile_id=self.boundary_profile_id,
                    chain_sequence=len(self._nodes) + 1,
                    predecessor_chain_id=self._next_predecessor(),
                    stage_index=self._completed_stage_count + 1,
                    stage_kind=selected,
                    stage_event_count=self._stage_event_count,
                    total_event_count=self._total_event_count,
                    output_bindings=outputs,
                )
            )
            self._completed_stage_count += 1
            self._active_stage = None
            self._stage_event_count = 0

    def complete_occurrence(self) -> PartialNativeOccurrenceTranscriptV1:
        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            if (
                self._active_stage is not None
                or self._completed_stage_count
                != len(ROOT_CAP_FIVE_STAGE_PLAN_V1)
            ):
                self._fail(
                    "PREMATURE_OCCURRENCE_COMPLETION",
                    "occurrence completion requires all five stage completions",
                )
            self._nodes.append(
                PartialNativeOccurrenceCompletionV1(
                    occurrence_start_id=self._start.start_id,
                    occurrence_id=self._start.occurrence_id,
                    counter_registry_id=self.counter_registry_id,
                    stage_profile_id=self.stage_profile_id,
                    boundary_profile_id=self.boundary_profile_id,
                    chain_sequence=len(self._nodes) + 1,
                    predecessor_chain_id=self._next_predecessor(),
                    completed_stage_count=self._completed_stage_count,
                    total_event_count=self._total_event_count,
                    emitted_event_ids=self._event_ids(),
                )
            )
            self._terminal = True
            return self.transcript

    def abort_occurrence(self, reason: str) -> PartialNativeOccurrenceTranscriptV1:
        with self._lock:
            self._check_thread()
            if self._terminal:
                raise OwnedConstructionAccountingRuntimeV1Error(
                    "partial-native occurrence is already terminal"
                )
            if type(reason) is not str or _ABORT_REASON.fullmatch(reason) is None:
                self._fail(
                    "MALFORMED_ABORT_REASON",
                    "abort reason must be a canonical public reason code",
                )
            self._protocol_abort(reason)
            return self.transcript


@contextmanager
def activate_owned_construction_accounting_v1(
    *,
    occurrence_id: str,
    recorder_id: str,
    counter_registry: Any,
    stage_profile: Any,
    boundary_profile: Any,
    _allow_low_level_test_api: bool = False,
) -> Iterator[OwnedConstructionAccountingSessionV1]:
    """Activate one thread-owned binding; nested bindings fail closed."""

    current = _ACTIVE_RUNTIME.get()
    if current is not None:
        current._protocol_abort(
            "NESTED_ACTIVE_SCOPE",
            exception_type=OwnedConstructionAccountingRuntimeV1Error,
        )
        raise OwnedConstructionAccountingRuntimeV1Error(
            "owned accounting scopes cannot be nested"
        )
    session = OwnedConstructionAccountingSessionV1(
        occurrence_id=occurrence_id,
        recorder_id=recorder_id,
        counter_registry=counter_registry,
        stage_profile=stage_profile,
        boundary_profile=boundary_profile,
        allow_low_level_test_api=_allow_low_level_test_api,
    )
    token: Token[Any] = _ACTIVE_RUNTIME.set(session)
    try:
        yield session
    except BaseException as error:
        if not session.is_terminal:
            session._protocol_abort(
                "ACTIVE_SCOPE_EXCEPTION", exception_type=type(error)
            )
        raise
    else:
        if not session.is_terminal:
            session._protocol_abort(
                "INCOMPLETE_SCOPE_EXIT",
                exception_type=OwnedConstructionAccountingRuntimeV1Error,
            )
            raise OwnedConstructionAccountingRuntimeV1Error(
                "active owned accounting scope exited without terminalization"
            )
    finally:
        _ACTIVE_RUNTIME.reset(token)


def emit_owned_sum_v1(site_id: Any, path: Any, amount: Any = 1) -> None:
    """Low-level explicit-boundary test API; not for production hooks."""

    session = _ACTIVE_RUNTIME.get()
    if session is not None:
        session.emit_sum(site_id, path, amount)


def emit_owned_operation_v1(dispatch_key: Any, amount: Any = 1) -> None:
    """Emit by owner-bound stage-neutral key, or no-op when inactive.

    Production source hooks use this API.  They cannot supply or infer a
    construction stage, counter path, boundary site, result type, caller, or
    fixture identity.  The trusted binding resolves those values and checks
    the direct caller's real module and code-object qualified name against the
    frozen operation owner.  An arbitrary callback therefore cannot mint an
    event merely by learning a public dispatch key.
    """

    session = _ACTIVE_RUNTIME.get()
    if session is not None:
        try:
            caller = sys._getframe(1)  # noqa: SLF001
        except (AttributeError, ValueError) as error:  # pragma: no cover
            session._protocol_abort(
                "CALLER_FRAME_UNAVAILABLE",
                exception_type=type(error),
            )
            raise OwnedConstructionAccountingRuntimeV1Error(
                "owned operation caller frame is unavailable"
            ) from error
        session.emit_operation(
            dispatch_key,
            amount,
            caller_module=caller.f_globals.get("__name__"),
            caller_globals=caller.f_globals,
            caller_code=caller.f_code,
        )


@contextmanager
def suppress_owned_operation_emission_v1() -> Iterator[None]:
    """Run a cooperative non-accounting callback outside the active binding.

    This removes accounting authority only.  It is not a process sandbox and
    makes no claim against arbitrary mutation of Python module globals.
    """

    session = _ACTIVE_RUNTIME.get()
    if session is None:
        yield
        return
    session._check_thread()
    token: Token[Any] = _ACTIVE_RUNTIME.set(None)
    try:
        yield
    finally:
        _ACTIVE_RUNTIME.reset(token)


def owned_accounting_active_v1() -> bool:
    """Return whether this context has one live trusted accounting binding."""

    session = _ACTIVE_RUNTIME.get()
    return (
        type(session) is OwnedConstructionAccountingSessionV1
        and not session.is_terminal
    )


def enter_owned_stage_v1(stage: Any) -> None:
    """Enter a stage under an active binding; otherwise no-op."""

    session = _ACTIVE_RUNTIME.get()
    if session is not None:
        session.enter_stage(stage)


def exit_owned_stage_v1(
    stage: Any | None = None,
    *,
    output_bindings: Any = (),
) -> None:
    """Complete the active stage under a binding; otherwise no-op."""

    session = _ACTIVE_RUNTIME.get()
    if session is not None:
        session.exit_stage(stage, output_bindings=output_bindings)


def complete_owned_occurrence_v1(
) -> PartialNativeOccurrenceTranscriptV1 | None:
    """Complete an active occurrence; otherwise return ``None``."""

    session = _ACTIVE_RUNTIME.get()
    return session.complete_occurrence() if session is not None else None


def abort_owned_occurrence_v1(
    reason: str,
) -> PartialNativeOccurrenceTranscriptV1 | None:
    """Abort an active occurrence while retaining prior events."""

    session = _ACTIVE_RUNTIME.get()
    return session.abort_occurrence(reason) if session is not None else None


__all__ = [
    "OwnedConstructionAccountingRuntimeV1Error",
    "OwnedConstructionAccountingSessionV1",
    "abort_owned_occurrence_v1",
    "activate_owned_construction_accounting_v1",
    "complete_owned_occurrence_v1",
    "emit_owned_operation_v1",
    "emit_owned_sum_v1",
    "enter_owned_stage_v1",
    "exit_owned_stage_v1",
    "owned_accounting_active_v1",
    "suppress_owned_operation_emission_v1",
]
