"""Bounded production campaign orchestrator for V0-075.

The runner consumes an already frozen fifteen-occurrence plan and fifteen
already-open, independently authorized occurrence lifecycles.  It never
creates a preregistration, opens an observer, derives a private environment,
or generates a key or secret.  Occurrences execute concurrently, while every
portable result is restored to the immutable scientific order before
semantic reconciliation.

Private execution inputs are deliberately nonportable.  The portable run
contains only verifier-derived occurrence, reconciliation, endpoint, and
runner-coordination evidence.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
from pathlib import Path
import threading
from typing import Any, Callable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_preopen_target_authorization_v1 as preopen
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_production_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_production_complete_bundle_endpoint_v1 as endpoint
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_ipc_v1 as ipc
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_production_campaign_runner_v1"

REGISTERED_MAX_WORKERS = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
PRODUCTION_CAMPAIGN_RUNNER_READY = True
TARGET_EXECUTION_OPENED = False
TARGET_AUTHORITY_CREATED = False
PRIVATE_LAW_DERIVATION_ALLOWED = False
SECRET_GENERATION_ALLOWED = False

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

DOMAIN_TAGS = {
    "profile": "acfqp:v075-production-campaign-runner-profile:v1",
    "input_binding": (
        "acfqp:v075-authorized-occurrence-execution-input-binding:v1"
    ),
    "work": "acfqp:v075-production-campaign-runner-native-work:v1",
    "run": "acfqp:v075-production-campaign-run:v1",
    "run_failure": "acfqp:v075-production-campaign-run-failure:v1",
    "verification": (
        "acfqp:v075-production-campaign-run-verification:v1"
    ),
    "construction_boundary": (
        "acfqp:v075-construction-campaign-runner-boundary-result:v1"
    ),
    "construction_fixture": (
        "acfqp:v075-construction-campaign-runner-fixture-evidence:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 production runner content domains overlap")


class V075ProductionCampaignRunnerInvariantViolation(ValueError):
    """A profile, input graph, result, order, or replay was invalid."""


class V075ProductionCampaignRunnerProtocolOrIntegrityFailure(RuntimeError):
    """A thread or occurrence boundary invalidated the whole campaign."""

    def __init__(
        self,
        reason: str,
        failed_scientific_ordinals: tuple[int, ...],
        failure_artifact: (
            V075ProductionCampaignRunFailureV1 | None
        ) = None,
    ) -> None:
        self.reason = reason
        self.failed_scientific_ordinals = failed_scientific_ordinals
        self.failure_artifact = failure_artifact
        super().__init__(
            "V0-075 production campaign failed closed: "
            f"{reason}; ordinals={failed_scientific_ordinals}"
        )


def _fail(message: str) -> None:
    raise V075ProductionCampaignRunnerInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionCampaignRunnerInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionCampaignRunnerInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


_PROFILE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignRunnerProfileV1:
    """Immutable scheduling profile intended for final preregistration."""

    _issuer: object = field(repr=False, compare=False)
    max_workers: int = REGISTERED_MAX_WORKERS
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _PROFILE_ISSUER
            or type(self.max_workers) is not int
            or self.max_workers != REGISTERED_MAX_WORKERS
            or not 1
            <= self.max_workers
            <= occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        ):
            _fail("production runner profile is caller-minted or changed")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_campaign_runner_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "max_workers": self.max_workers,
            "executor": "THREAD_POOL_OVER_ISOLATED_OCCURRENCE_IPC",
            "occurrence_count": (
                occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            ),
            "one_fresh_ipc_child_per_occurrence": True,
            "per_occurrence_algorithm_changed": False,
            "accuracy_reduction_allowed": False,
            "result_order": "IMMUTABLE_SCIENTIFIC_ORDER",
            "final_preregistration_binding_required": True,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def freeze_v075_production_campaign_runner_profile_v1(
) -> V075ProductionCampaignRunnerProfileV1:
    return V075ProductionCampaignRunnerProfileV1(_PROFILE_ISSUER)


_INPUT_ISSUER = object()


@dataclass(frozen=True, slots=True, repr=False)
class V075AuthorizedOccurrenceExecutionInputV1:
    """Nonserializable holder for one already-authorized occurrence."""

    _issuer: object = field(repr=False, compare=False)
    plan: occurrence_plan.V075ProductionOccurrencePlanV1 = field(repr=False)
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1 = field(
        repr=False
    )
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1 = field(repr=False)
    authority: preopen.V075ObserverOpenAuthorizationV1 = field(repr=False)
    private_salt: bytes = field(repr=False)
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1 = field(
        repr=False
    )
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _INPUT_ISSUER:
            _fail("authorized execution input is issuer-only")
        _validate_one_authorized_input_v1(self)
        object.__setattr__(
            self,
            "_binding_id",
            _hash("input_binding", self._public_payload()),
        )

    def _public_payload(self) -> dict[str, Any]:
        binding = self.controller.open_binding
        return {
            "schema": (
                "acfqp.v075_authorized_occurrence_execution_input_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan.plan_id,
            "plan_entry_id": self.entry.entry_id,
            "occurrence_id": self.entry.occurrence_id,
            "scientific_ordinal": self.entry.scientific_ordinal,
            "ipc_profile_id": self.ipc_profile.profile_id,
            "observer_open_binding_id": binding.observer_open_binding_id,
            "observer_session_public_id": binding.session_public_id,
            "observer_authorization_id": self.authority.authorization_id,
            "environment_commitment_id": (
                self.authority.opaque_environment_commitment.commitment_id
            ),
            "private_salt_present": True,
            "private_environment_present": True,
            "private_salt_serialized": False,
            "private_environment_serialized": False,
            "private_law_serialized": False,
            "portable": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def __repr__(self) -> str:
        return (
            "<V075AuthorizedOccurrenceExecutionInputV1 "
            f"occurrence_id={self.entry.occurrence_id} private=redacted>"
        )

    def __reduce_ex__(self, _protocol: int) -> Any:
        raise TypeError("authorized occurrence execution inputs are not portable")


def _validate_one_authorized_input_v1(
    value: V075AuthorizedOccurrenceExecutionInputV1,
) -> None:
    if (
        type(value.plan)
        is not occurrence_plan.V075ProductionOccurrencePlanV1
        or type(value.entry)
        is not occurrence_plan.V075ProductionOccurrencePlanEntryV1
        or type(value.controller)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
        or type(value.ipc_profile)
        is not ipc.V075ProductionOccurrenceIPCProfileV1
        or type(value.authority)
        is not preopen.V075ObserverOpenAuthorizationV1
        or type(value.private_salt) is not bytes
        or len(value.private_salt) < public.MINIMUM_SECRET_SALT_BYTES
        or len(set(value.private_salt)) < 16
        or type(value.private_environment)
        is not private_env.V075PrivateGeneratedEnvironmentV1
    ):
        _fail("authorized occurrence input contains an inexact private type")
    entry = value.entry
    plan = value.plan
    binding = value.controller.open_binding
    namespace = binding.namespace
    open_authority = binding.observer_open_binding
    expected_source = (
        plan.source_prior_transport
        if entry.arm.value == "SOURCE_CONSENSUS_PRIOR"
        else None
    )
    if (
        plan.entries[entry.scientific_ordinal] != entry
        or binding.authority_scope
        is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        or binding.occurrence_id != entry.occurrence_id
        or binding.context_id != entry.context_id
        or binding.arm is not entry.arm
        or binding.route_cap_profile != plan.cap_profile
        or namespace.target_tape_namespace_id
        != plan.target_tape_namespace_id
        or namespace.remote_main_anchor.external_id
        != plan.remote_main_anchor_id
        or namespace.final_preregistration.external_id
        != plan.final_preregistration_id
        or value.ipc_profile.occurrence_identity
        != entry.occurrence_identity
        or value.ipc_profile.open_lifecycle_binding != binding
        or value.ipc_profile.context
        != namespace.family.replicate_contexts[entry.context_ordinal]
        or value.ipc_profile.source_prior_transport != expected_source
        or value.ipc_profile.behavior
        is not ipc.V075ProductionIPCBehaviorV1.HONEST
        or value.authority.anchor.anchor_id
        != plan.remote_main_anchor_id
        or value.authority.anchor.final_preregistration_id
        != plan.final_preregistration_id
        or value.authority.anchor.family_generation_id
        != plan.public_family_generation_id
        or value.authority.opaque_environment_commitment
        != namespace.environment_commitment
        or value.authority.signer_registry != namespace.signer_registry
        or open_authority.upstream_authority_id
        != value.authority.authorization_id
        or open_authority.verification_attestation_id
        != value.authority.private_reveal_attestation.attestation_id
        or not open_authority.independent_final_authority_verified
        or not open_authority.observer_open_authorized
        or value.private_environment.family != namespace.family
        or value.controller.batches
        or value.controller.events
        or value.controller.aggregate_support_evidence
    ):
        _fail("authorized occurrence input is stale, open, or transplanted")


def bind_v075_authorized_occurrence_execution_input_v1(
    *,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    authority: preopen.V075ObserverOpenAuthorizationV1,
    private_salt: bytes,
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
) -> V075AuthorizedOccurrenceExecutionInputV1:
    """Bind existing authorities without opening or deriving target state."""

    return V075AuthorizedOccurrenceExecutionInputV1(
        _INPUT_ISSUER,
        plan,
        entry,
        controller,
        ipc_profile,
        authority,
        private_salt,
        private_environment,
    )


def bind_v075_production_occurrence_execution_input_v1(
    *,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    authority: preopen.V075ObserverOpenAuthorizationV1,
    private_salt: bytes,
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
) -> V075AuthorizedOccurrenceExecutionInputV1:
    """Registry-canonical alias for the issuer-bound input factory."""

    return bind_v075_authorized_occurrence_execution_input_v1(
        plan=plan,
        entry=entry,
        controller=controller,
        ipc_profile=ipc_profile,
        authority=authority,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def _validate_production_execution_inputs_v1(
    *,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    execution_inputs: tuple[V075AuthorizedOccurrenceExecutionInputV1, ...],
) -> None:
    if (
        type(execution_inputs) is not tuple
        or len(execution_inputs)
        != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        or any(
            type(item) is not V075AuthorizedOccurrenceExecutionInputV1
            for item in execution_inputs
        )
    ):
        _fail("runner requires exactly fifteen issuer-bound execution inputs")
    if tuple(item.entry for item in execution_inputs) != plan.entries:
        _fail("execution inputs are missing, duplicated, or reordered")
    for item in execution_inputs:
        _validate_one_authorized_input_v1(item)
        if item.plan != plan:
            _fail("execution input carries a foreign production plan")
    if (
        len({item.binding_id for item in execution_inputs})
        != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        or len(
            {
                item.controller.open_binding.session_public_id
                for item in execution_inputs
            }
        )
        != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        or any(
            item.authority is not execution_inputs[0].authority
            for item in execution_inputs
        )
        or any(
            item.private_environment
            is not execution_inputs[0].private_environment
            for item in execution_inputs
        )
        or any(
            not hmac.compare_digest(
                item.private_salt,
                execution_inputs[0].private_salt,
            )
            for item in execution_inputs
        )
    ):
        _fail("execution inputs duplicate or transplant campaign authority")


def _execute_v075_production_occurrence_boundary_v1(
    value: V075AuthorizedOccurrenceExecutionInputV1,
) -> occurrence.V075ProductionOccurrenceAuthorityResultV1:
    if type(value) is not V075AuthorizedOccurrenceExecutionInputV1:
        _fail("production occurrence boundary received an inexact input")
    return occurrence.execute_v075_production_occurrence_v1(
        repository_root=_RUNNER_REPOSITORY_ROOT.get(),
        plan=value.plan,
        entry=value.entry,
        controller=value.controller,
        ipc_profile=value.ipc_profile,
        authority=value.authority,
        private_salt=value.private_salt,
        private_environment=value.private_environment,
    )


class _RepositoryRootBinding:
    """Thread-visible immutable root installed only around one run."""

    def __init__(self) -> None:
        self._value: str | Path | None = None
        self._lock = threading.Lock()

    def install(self, value: str | Path) -> None:
        with self._lock:
            if self._value is not None:
                _fail("production runner repository root is already installed")
            self._value = value

    def get(self) -> str | Path:
        with self._lock:
            if self._value is None:
                _fail("production occurrence boundary lacks repository root")
            return self._value

    def clear(self) -> None:
        with self._lock:
            self._value = None


_RUNNER_REPOSITORY_ROOT = _RepositoryRootBinding()
_REGISTERED_PRODUCTION_BOUNDARY = (
    _execute_v075_production_occurrence_boundary_v1
)


@dataclass(frozen=True, slots=True)
class _ParallelScheduleOutcome:
    results: tuple[Any, ...]
    completion_ordinals: tuple[int, ...]
    peak_active_tasks: int


def _run_parallel_schedule_v1(
    *,
    values: tuple[Any, ...],
    max_workers: int,
    boundary: Callable[[Any], Any],
    production_failure_context: tuple[
        V075ProductionCampaignRunnerProfileV1,
        occurrence_plan.V075ProductionOccurrencePlanV1,
    ]
    | None = None,
) -> _ParallelScheduleOutcome:
    if (
        type(values) is not tuple
        or len(values) != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        or type(max_workers) is not int
        or max_workers != REGISTERED_MAX_WORKERS
        or not callable(boundary)
    ):
        _fail("parallel schedule is incomplete or unregistered")
    lock = threading.Lock()
    active = 0
    peak = 0

    def invoke(value: Any) -> Any:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            return boundary(value)
        finally:
            with lock:
                active -= 1

    slots: list[Any | None] = [None] * len(values)
    completion: list[int] = []
    failed: list[int] = []
    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="acfqp-v075-occurrence",
    ) as pool:
        futures = {
            pool.submit(invoke, item): index
            for index, item in enumerate(values)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                slots[index] = future.result()
            except Exception:
                # Exception text is intentionally not propagated: a private
                # boundary must not gain an error-message exfiltration lane.
                failed.append(index)
            completion.append(index)
    if failed:
        artifact = (
            None
            if production_failure_context is None
            else _issue_run_failure_v1(
                profile=production_failure_context[0],
                plan=production_failure_context[1],
                code=(
                    V075ProductionCampaignRunFailureCodeV1
                    .RUNNER_THREAD_EXCEPTION
                ),
                results=tuple(slots),
                failed_ordinals=tuple(sorted(failed)),
                completion_ordinals=tuple(completion),
                peak_active_tasks=peak,
            )
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "THREAD_EXCEPTION",
            tuple(sorted(failed)),
            artifact,
        )
    if any(item is None for item in slots):
        missing = tuple(
            index for index, item in enumerate(slots) if item is None
        )
        artifact = (
            None
            if production_failure_context is None
            else _issue_run_failure_v1(
                profile=production_failure_context[0],
                plan=production_failure_context[1],
                code=(
                    V075ProductionCampaignRunFailureCodeV1
                    .MISSING_THREAD_RESULT
                ),
                results=tuple(slots),
                failed_ordinals=missing,
                completion_ordinals=tuple(completion),
                peak_active_tasks=peak,
            )
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "MISSING_THREAD_RESULT",
            missing,
            artifact,
        )
    return _ParallelScheduleOutcome(
        tuple(slots),
        tuple(completion),
        peak,
    )


class V075ProductionCampaignRunFailureCodeV1(str, Enum):
    RUNNER_THREAD_EXCEPTION = "RUNNER_THREAD_EXCEPTION"
    MISSING_THREAD_RESULT = "MISSING_THREAD_RESULT"
    OCCURRENCE_OUTPUT_IDENTITY_FAILURE = (
        "OCCURRENCE_OUTPUT_IDENTITY_FAILURE"
    )
    OCCURRENCE_SEMANTIC_VERIFICATION_FAILURE = (
        "OCCURRENCE_SEMANTIC_VERIFICATION_FAILURE"
    )
    CAMPAIGN_RECONCILIATION_OR_ENDPOINT_FAILURE = (
        "CAMPAIGN_RECONCILIATION_OR_ENDPOINT_FAILURE"
    )
    PROTOCOL_OR_INTEGRITY_TERMINAL = (
        "PROTOCOL_OR_INTEGRITY_TERMINAL"
    )


_FAILURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignRunFailureV1:
    """Non-scientific closure retaining completed public work references."""

    _issuer: object = field(repr=False, compare=False)
    runner_profile_id: str
    plan_id: str
    failure_code: V075ProductionCampaignRunFailureCodeV1
    completed_slot_ordinals: tuple[int, ...]
    claimed_result_scientific_ordinals: tuple[int, ...]
    completed_result_ids: tuple[str, ...]
    completed_online_work_ids: tuple[str, ...]
    completed_accepted_draw_counts: tuple[int, ...]
    completed_process_launch_counts: tuple[int, ...]
    failed_ordinals: tuple[int, ...]
    completion_ordinals: tuple[int, ...]
    peak_active_tasks: int
    future_submissions: int
    future_completions: int
    _failure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.runner_profile_id, "failed-run runner profile")
        _cid(self.plan_id, "failed-run plan")
        for value in (
            *self.completed_result_ids,
            *self.completed_online_work_ids,
        ):
            _cid(value, "failed-run completed work reference")
        size = len(self.completed_slot_ordinals)
        expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        if (
            self._issuer is not _FAILURE_ISSUER
            or type(self.failure_code)
            is not V075ProductionCampaignRunFailureCodeV1
            or any(
                type(values) is not tuple
                for values in (
                    self.completed_slot_ordinals,
                    self.claimed_result_scientific_ordinals,
                    self.completed_result_ids,
                    self.completed_online_work_ids,
                    self.completed_accepted_draw_counts,
                    self.completed_process_launch_counts,
                    self.failed_ordinals,
                    self.completion_ordinals,
                )
            )
            or any(
                len(values) != size
                for values in (
                    self.claimed_result_scientific_ordinals,
                    self.completed_result_ids,
                    self.completed_online_work_ids,
                    self.completed_accepted_draw_counts,
                    self.completed_process_launch_counts,
                )
            )
            or self.completed_slot_ordinals
            != tuple(sorted(set(self.completed_slot_ordinals)))
            or any(
                value not in range(expected)
                for value in (
                    *self.completed_slot_ordinals,
                    *self.claimed_result_scientific_ordinals,
                    *self.failed_ordinals,
                    *self.completion_ordinals,
                )
            )
            or self.failed_ordinals
            != tuple(sorted(set(self.failed_ordinals)))
            or len(self.completion_ordinals) != expected
            or set(self.completion_ordinals) != set(range(expected))
            or any(
                type(value) is not int or value < 0
                for value in (
                    *self.completed_accepted_draw_counts,
                    *self.completed_process_launch_counts,
                )
            )
            or type(self.peak_active_tasks) is not int
            or not 1 <= self.peak_active_tasks <= REGISTERED_MAX_WORKERS
            or self.future_submissions != expected
            or self.future_completions != expected
        ):
            _fail("production run failure artifact is malformed")
        object.__setattr__(
            self,
            "_failure_id",
            _hash("run_failure", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_campaign_run_failure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runner_profile_id": self.runner_profile_id,
            "plan_id": self.plan_id,
            "terminal_scope": "CAMPAIGN_RUN_ATTEMPT",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": self.failure_code.value,
            "scientific_verdict": None,
            "reconciliation_id": None,
            "endpoint_verification_id": None,
            "completed_slot_ordinals": list(
                self.completed_slot_ordinals
            ),
            "claimed_result_scientific_ordinals": list(
                self.claimed_result_scientific_ordinals
            ),
            "completed_result_ids": list(self.completed_result_ids),
            "completed_online_work_ids": list(
                self.completed_online_work_ids
            ),
            "completed_accepted_draw_counts": list(
                self.completed_accepted_draw_counts
            ),
            "completed_process_launch_counts": list(
                self.completed_process_launch_counts
            ),
            "failed_ordinals": list(self.failed_ordinals),
            "completion_ordinals": list(self.completion_ordinals),
            "peak_active_tasks": self.peak_active_tasks,
            "future_submissions": self.future_submissions,
            "future_completions": self.future_completions,
            "completed_work_retained": True,
            "exception_text_serialized": False,
            "private_input_serialized": False,
            "eligible_for_reconciliation": False,
            "eligible_for_scientific_endpoint": False,
            "can_be_relabelled_scientific_pass_or_fail": False,
            "target_execution_opened_by_runner": False,
        }

    @property
    def failure_id(self) -> str:
        return self._failure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "failure_id": self.failure_id}


def _issue_run_failure_v1(
    *,
    profile: V075ProductionCampaignRunnerProfileV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    code: V075ProductionCampaignRunFailureCodeV1,
    results: tuple[Any, ...],
    failed_ordinals: tuple[int, ...],
    completion_ordinals: tuple[int, ...],
    peak_active_tasks: int,
) -> V075ProductionCampaignRunFailureV1:
    completed = tuple(
        (index, item)
        for index, item in enumerate(results)
        if type(item)
        is occurrence.V075ProductionOccurrenceAuthorityResultV1
    )
    value = V075ProductionCampaignRunFailureV1(
        _FAILURE_ISSUER,
        profile.profile_id,
        plan.plan_id,
        code,
        tuple(index for index, _item in completed),
        tuple(
            item.plan_entry.scientific_ordinal for _index, item in completed
        ),
        tuple(item.result_id for _index, item in completed),
        tuple(
            item.ipc_result.actual_work.work_id
            for _index, item in completed
        ),
        tuple(
            (
                item.ipc_result.actual_work.accepted_draws
                if type(
                    getattr(
                        item.ipc_result.actual_work,
                        "accepted_draws",
                        None,
                    )
                )
                is int
                else 0
            )
            for _index, item in completed
        ),
        tuple(
            (
                item.ipc_result.actual_work.process_launches
                if type(
                    getattr(
                        item.ipc_result.actual_work,
                        "process_launches",
                        None,
                    )
                )
                is int
                else 0
            )
            for _index, item in completed
        ),
        tuple(sorted(set(failed_ordinals))),
        completion_ordinals,
        peak_active_tasks,
        occurrence_plan.EXPECTED_OCCURRENCE_COUNT,
        occurrence_plan.EXPECTED_OCCURRENCE_COUNT,
    )
    _assert_no_private_material_serialized_v1(value.to_document())
    return value


_WORK_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignRunnerNativeWorkV1:
    """Runner-only coordination work; occurrence work is not double charged."""

    _issuer: object = field(repr=False, compare=False)
    profile_id: str
    plan_id: str
    future_submissions: int
    future_completions: int
    scientific_result_slot_writes: int
    occurrence_process_exit_checks: int
    coordinated_occurrence_process_launches_reference_only: int
    thread_pool_creations: int
    runner_os_process_launches: int
    thread_exceptions: int
    completion_ordinals: tuple[int, ...]
    peak_active_tasks: int
    _work_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.profile_id, "runner-work profile")
        _cid(self.plan_id, "runner-work plan")
        expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        if (
            self._issuer is not _WORK_ISSUER
            or self.future_submissions != expected
            or self.future_completions != expected
            or self.scientific_result_slot_writes != expected
            or self.occurrence_process_exit_checks != expected
            or self.coordinated_occurrence_process_launches_reference_only
            != expected
            or self.thread_pool_creations != 1
            or self.runner_os_process_launches != 0
            or self.thread_exceptions != 0
            or type(self.completion_ordinals) is not tuple
            or len(self.completion_ordinals) != expected
            or set(self.completion_ordinals) != set(range(expected))
            or type(self.peak_active_tasks) is not int
            or not 1 <= self.peak_active_tasks <= REGISTERED_MAX_WORKERS
        ):
            _fail("runner native work is incomplete or double charged")
        object.__setattr__(
            self,
            "_work_id",
            _hash("work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_campaign_runner_native_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "runner_profile_id": self.profile_id,
            "plan_id": self.plan_id,
            "lane": "OPERATIONAL_RUNNER_COORDINATION",
            "future_submissions": self.future_submissions,
            "future_completions": self.future_completions,
            "scientific_result_slot_writes": (
                self.scientific_result_slot_writes
            ),
            "occurrence_process_exit_checks": (
                self.occurrence_process_exit_checks
            ),
            "coordinated_occurrence_process_launches_reference_only": (
                self.coordinated_occurrence_process_launches_reference_only
            ),
            "thread_pool_creations": self.thread_pool_creations,
            "runner_os_process_launches": self.runner_os_process_launches,
            "thread_exceptions": self.thread_exceptions,
            "completion_ordinals": list(self.completion_ordinals),
            "peak_active_tasks": self.peak_active_tasks,
            "occurrence_process_launches_charged_in_occurrence_work": True,
            "runner_does_not_double_charge_occurrence_processes": True,
            "completion_order_retained_as_runner_evidence": True,
            "completion_order_not_used_as_scientific_order": True,
        }

    @property
    def work_id(self) -> str:
        return self._work_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _derive_runner_work_v1(
    *,
    profile: V075ProductionCampaignRunnerProfileV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    verifications: tuple[
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1, ...
    ],
    completion_ordinals: tuple[int, ...],
    peak_active_tasks: int,
) -> V075ProductionCampaignRunnerNativeWorkV1:
    expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
    if (
        len(verifications) != expected
        or sum(item.process_launch_count for item in verifications) != expected
        or any(item.process_launch_count != 1 for item in verifications)
    ):
        _fail("runner process coordination differs from occurrence work")
    return V075ProductionCampaignRunnerNativeWorkV1(
        _WORK_ISSUER,
        profile.profile_id,
        plan.plan_id,
        expected,
        expected,
        expected,
        expected,
        expected,
        1,
        0,
        0,
        completion_ordinals,
        peak_active_tasks,
    )


_FORBIDDEN_PRIVATE_KEYS = {
    "private_salt",
    "secret_salt",
    "private_environment",
    "secret_environment",
    "secret_laws",
    "target_law",
    "target_tape",
    "random_words",
    "accepted_draw_indices",
    "secret_generation_seed",
}


def _assert_no_private_material_serialized_v1(value: Any) -> None:
    if isinstance(value, bytes):
        _fail("portable runner artifact contains raw bytes")
    if type(value) is dict:
        for key, item in value.items():
            if key in _FORBIDDEN_PRIVATE_KEYS:
                _fail("portable runner artifact contains a private field")
            if (
                key.endswith("_serialized")
                and type(item) is bool
                and item
            ):
                _fail("portable runner artifact claims private serialization")
            _assert_no_private_material_serialized_v1(item)
    elif type(value) in {list, tuple}:
        for item in value:
            _assert_no_private_material_serialized_v1(item)


_RUN_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignRunV1:
    _issuer: object = field(repr=False, compare=False)
    profile: V075ProductionCampaignRunnerProfileV1
    plan: occurrence_plan.V075ProductionOccurrencePlanV1 = field(repr=False)
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    )
    occurrence_results: tuple[
        occurrence.V075ProductionOccurrenceAuthorityResultV1, ...
    ] = field(repr=False)
    occurrence_verifications: tuple[
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1, ...
    ]
    reconciliation: reconciliation.V075ProductionCampaignReconciliationV1
    reconciliation_verification: (
        reconciliation.V075ProductionCampaignReconciliationVerificationV1
    )
    endpoint_verification: (
        endpoint.V075ProductionCompleteBundleEndpointVerificationV1
    )
    runner_work: V075ProductionCampaignRunnerNativeWorkV1
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        if (
            self._issuer is not _RUN_ISSUER
            or type(self.profile)
            is not V075ProductionCampaignRunnerProfileV1
            or self.profile
            != freeze_v075_production_campaign_runner_profile_v1()
            or type(self.plan)
            is not occurrence_plan.V075ProductionOccurrencePlanV1
            or type(self.plan_verification)
            is not occurrence_plan.V075ProductionOccurrencePlanVerificationV1
            or type(self.occurrence_results) is not tuple
            or len(self.occurrence_results) != expected
            or any(
                type(item)
                is not occurrence.V075ProductionOccurrenceAuthorityResultV1
                for item in self.occurrence_results
            )
            or type(self.occurrence_verifications) is not tuple
            or len(self.occurrence_verifications) != expected
            or any(
                type(item)
                is not occurrence
                .V075ProductionOccurrenceAuthorityVerificationV1
                for item in self.occurrence_verifications
            )
            or tuple(item.plan_entry for item in self.occurrence_results)
            != self.plan.entries
            or tuple(
                item.result_id for item in self.occurrence_results
            )
            != tuple(
                item.result_id for item in self.occurrence_verifications
            )
            or type(self.reconciliation)
            is not reconciliation.V075ProductionCampaignReconciliationV1
            or self.reconciliation.plan != self.plan
            or tuple(
                item.result for item in self.reconciliation.occurrences
            )
            != self.occurrence_results
            or type(self.reconciliation_verification)
            is not reconciliation
            .V075ProductionCampaignReconciliationVerificationV1
            or self.reconciliation_verification.reconciliation_id
            != self.reconciliation.reconciliation_id
            or type(self.endpoint_verification)
            is not endpoint
            .V075ProductionCompleteBundleEndpointVerificationV1
            or self.endpoint_verification.reconciliation
            != self.reconciliation
            or type(self.runner_work)
            is not V075ProductionCampaignRunnerNativeWorkV1
            or self.runner_work.profile_id != self.profile.profile_id
            or self.runner_work.plan_id != self.plan.plan_id
        ):
            _fail("production campaign run is partial, reordered, or foreign")
        object.__setattr__(
            self,
            "_run_id",
            _hash("run", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_campaign_run.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "runner_profile_id": self.profile.profile_id,
            "plan_id": self.plan.plan_id,
            "plan_verification_id": self.plan_verification.verification_id,
            "occurrence_result_ids": [
                item.result_id for item in self.occurrence_results
            ],
            "occurrence_verification_ids": [
                item.verification_id
                for item in self.occurrence_verifications
            ],
            "scientific_ordinals": list(
                range(occurrence_plan.EXPECTED_OCCURRENCE_COUNT)
            ),
            "reconciliation_id": self.reconciliation.reconciliation_id,
            "reconciliation_verification_id": (
                self.reconciliation_verification.verification_id
            ),
            "endpoint_verification_id": (
                self.endpoint_verification.verification_id
            ),
            "scientific_verdict": self.endpoint_verification.verdict.value,
            "runner_work_id": self.runner_work.work_id,
            "logical_occurrence_denominator": (
                occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            ),
            "all_occurrence_terminals_retained": True,
            "completion_order_not_used_as_scientific_order": True,
            "scientific_order_restored": True,
            "target_execution_opened_by_runner": False,
            "target_authority_created_by_runner": False,
            "preauthorized_target_execution_consumed": True,
            "private_law_derived_by_runner": False,
            "secret_generated_by_runner": False,
            "private_salt_serialized": False,
            "private_environment_serialized": False,
            "private_law_serialized": False,
            "random_words_serialized": False,
            "accepted_draw_indices_serialized": False,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
            "official_scalar_cost": OFFICIAL_SCALAR_COST,
            "official_N_break_even": OFFICIAL_N_BREAK_EVEN,
            "workload_economics_gate_status": (
                WORKLOAD_ECONOMICS_GATE_STATUS
            ),
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "runner_profile": self.profile.to_document(),
            "plan_verification": self.plan_verification.to_document(),
            "occurrence_verifications": [
                item.to_document() for item in self.occurrence_verifications
            ],
            "reconciliation": self.reconciliation.to_document(),
            "reconciliation_verification": (
                self.reconciliation_verification.to_document()
            ),
            "endpoint_verification": (
                self.endpoint_verification.to_document()
            ),
            "runner_work": self.runner_work.to_document(),
            "run_id": self.run_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _finalize_v075_production_campaign_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    profile: V075ProductionCampaignRunnerProfileV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    results: tuple[
        occurrence.V075ProductionOccurrenceAuthorityResultV1, ...
    ],
    completion_ordinals: tuple[int, ...],
    peak_active_tasks: int,
) -> V075ProductionCampaignRunV1:
    expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
    if (
        type(results) is not tuple
        or len(results) != expected
        or any(
            type(item)
            is not occurrence.V075ProductionOccurrenceAuthorityResultV1
            for item in results
        )
    ):
        artifact = _issue_run_failure_v1(
            profile=profile,
            plan=plan,
            code=(
                V075ProductionCampaignRunFailureCodeV1
                .OCCURRENCE_OUTPUT_IDENTITY_FAILURE
            ),
            results=results,
            failed_ordinals=tuple(range(expected)),
            completion_ordinals=completion_ordinals,
            peak_active_tasks=peak_active_tasks,
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "UNTYPED_OR_MISSING_OCCURRENCE_RESULT",
            tuple(range(expected)),
            artifact,
        )
    invalid = tuple(
        index
        for index, result in enumerate(results)
        if (
            result.plan != plan
            or result.plan_verification != plan_verification
            or result.plan_entry != plan.entries[index]
            or result.authority_scope
            is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
        )
    )
    if invalid or len({item.result_id for item in results}) != expected:
        failed = invalid if invalid else tuple(range(expected))
        artifact = _issue_run_failure_v1(
            profile=profile,
            plan=plan,
            code=(
                V075ProductionCampaignRunFailureCodeV1
                .OCCURRENCE_OUTPUT_IDENTITY_FAILURE
            ),
            results=results,
            failed_ordinals=failed,
            completion_ordinals=completion_ordinals,
            peak_active_tasks=peak_active_tasks,
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "REORDERED_DUPLICATED_OR_TRANSPLANTED_RESULT",
            failed,
            artifact,
        )

    verifications = []
    for index, result in enumerate(results):
        try:
            verified = (
                occurrence
                .verify_v075_production_occurrence_authority_result_v1(
                    repository_root=repository_root,
                    namespace=namespace,
                    claimed=result,
                )
            )
        except Exception as error:
            artifact = _issue_run_failure_v1(
                profile=profile,
                plan=plan,
                code=(
                    V075ProductionCampaignRunFailureCodeV1
                    .OCCURRENCE_SEMANTIC_VERIFICATION_FAILURE
                ),
                results=results,
                failed_ordinals=(index,),
                completion_ordinals=completion_ordinals,
                peak_active_tasks=peak_active_tasks,
            )
            raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
                "OCCURRENCE_SEMANTIC_VERIFICATION_FAILED",
                (index,),
                artifact,
            ) from error
        verifications.append(verified)
    typed_verifications = tuple(verifications)

    try:
        reconciled = reconciliation.reconcile_v075_production_campaign_v1(
            repository_root=repository_root,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=results,
            occurrence_verifications=typed_verifications,
        )
        reconciled_verification = (
            reconciliation
            .verify_v075_production_campaign_reconciliation_v1(
                repository_root=repository_root,
                namespace=namespace,
                claimed=reconciled,
            )
        )
        endpoint_verification = (
            endpoint.verify_v075_production_complete_bundle_endpoint_v1(
                repository_root=repository_root,
                namespace=namespace,
                claimed=reconciled,
            )
        )
    except endpoint.V075ProductionCompleteBundleProtocolOrIntegrityFailure as error:
        invalidating_ids = set(error.invalidating_occurrence_ids)
        failed = tuple(
            index
            for index, item in enumerate(results)
            if item.occurrence_id in invalidating_ids
        )
        artifact = _issue_run_failure_v1(
            profile=profile,
            plan=plan,
            code=(
                V075ProductionCampaignRunFailureCodeV1
                .PROTOCOL_OR_INTEGRITY_TERMINAL
            ),
            results=results,
            failed_ordinals=(
                failed if failed else tuple(range(expected))
            ),
            completion_ordinals=completion_ordinals,
            peak_active_tasks=peak_active_tasks,
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "PROTOCOL_OR_INTEGRITY_TERMINAL",
            failed if failed else tuple(range(expected)),
            artifact,
        ) from error
    except Exception as error:
        artifact = _issue_run_failure_v1(
            profile=profile,
            plan=plan,
            code=(
                V075ProductionCampaignRunFailureCodeV1
                .CAMPAIGN_RECONCILIATION_OR_ENDPOINT_FAILURE
            ),
            results=results,
            failed_ordinals=tuple(range(expected)),
            completion_ordinals=completion_ordinals,
            peak_active_tasks=peak_active_tasks,
        )
        raise V075ProductionCampaignRunnerProtocolOrIntegrityFailure(
            "CAMPAIGN_RECONCILIATION_OR_ENDPOINT_FAILED",
            tuple(range(expected)),
            artifact,
        ) from error

    runner_work = _derive_runner_work_v1(
        profile=profile,
        plan=plan,
        verifications=typed_verifications,
        completion_ordinals=completion_ordinals,
        peak_active_tasks=peak_active_tasks,
    )
    value = V075ProductionCampaignRunV1(
        _RUN_ISSUER,
        profile,
        plan,
        plan_verification,
        results,
        typed_verifications,
        reconciled,
        reconciled_verification,
        endpoint_verification,
        runner_work,
    )
    _assert_no_private_material_serialized_v1(value.to_document())
    return value


def run_v075_production_campaign_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    profile: V075ProductionCampaignRunnerProfileV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    execution_inputs: tuple[
        V075AuthorizedOccurrenceExecutionInputV1, ...
    ],
) -> V075ProductionCampaignRunV1:
    """Execute the exact preauthorized 15-way campaign concurrently."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(profile) is not V075ProductionCampaignRunnerProfileV1
        or profile != freeze_v075_production_campaign_runner_profile_v1()
        or type(plan)
        is not occurrence_plan.V075ProductionOccurrencePlanV1
        or type(plan_verification)
        is not occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ):
        _fail("production runner requires exact frozen public authorities")
    replayed, verified = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=repository_root,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )
    if replayed != plan or verified != plan_verification:
        _fail("production plan changed under runner preflight replay")
    _validate_production_execution_inputs_v1(
        plan=plan,
        execution_inputs=execution_inputs,
    )

    _RUNNER_REPOSITORY_ROOT.install(repository_root)
    try:
        scheduled = _run_parallel_schedule_v1(
            values=execution_inputs,
            max_workers=profile.max_workers,
            boundary=_execute_v075_production_occurrence_boundary_v1,
            production_failure_context=(profile, plan),
        )
    finally:
        _RUNNER_REPOSITORY_ROOT.clear()
    return _finalize_v075_production_campaign_v1(
        repository_root=repository_root,
        namespace=namespace,
        profile=profile,
        plan=plan,
        plan_verification=plan_verification,
        results=scheduled.results,
        completion_ordinals=scheduled.completion_ordinals,
        peak_active_tasks=scheduled.peak_active_tasks,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignRunVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    run_id: str
    replayed_run_id: str
    runner_profile_id: str
    plan_id: str
    runner_work_id: str
    reconciliation_id: str
    endpoint_verification_id: str
    occurrence_result_ids: tuple[str, ...]
    scientific_verdict: endpoint.V075ProductionScientificEndpointVerdictV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.run_id, "verified campaign run"),
            (self.replayed_run_id, "replayed campaign run"),
            (self.runner_profile_id, "verified runner profile"),
            (self.plan_id, "verified runner plan"),
            (self.runner_work_id, "verified runner work"),
            (self.reconciliation_id, "verified reconciliation"),
            (
                self.endpoint_verification_id,
                "verified scientific endpoint",
            ),
            *((item, "verified occurrence result") for item in self.occurrence_result_ids),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or self.run_id != self.replayed_run_id
            or type(self.occurrence_result_ids) is not tuple
            or len(self.occurrence_result_ids)
            != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            or len(set(self.occurrence_result_ids))
            != occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            or type(self.scientific_verdict)
            is not endpoint.V075ProductionScientificEndpointVerdictV1
        ):
            _fail("campaign-run verification is partial or caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_campaign_run_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "run_id": self.run_id,
            "replayed_run_id": self.replayed_run_id,
            "runner_profile_id": self.runner_profile_id,
            "plan_id": self.plan_id,
            "runner_work_id": self.runner_work_id,
            "reconciliation_id": self.reconciliation_id,
            "endpoint_verification_id": self.endpoint_verification_id,
            "occurrence_result_ids": list(self.occurrence_result_ids),
            "scientific_verdict": self.scientific_verdict.value,
            "semantic_occurrence_replays": (
                occurrence_plan.EXPECTED_OCCURRENCE_COUNT
            ),
            "scientific_order_replayed": True,
            "reconciliation_replayed": True,
            "endpoint_rederived": True,
            "runner_native_work_rederived": True,
            "private_material_scan_passed": True,
            "target_execution_opened_by_verifier": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_production_campaign_run_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    claimed: V075ProductionCampaignRunV1,
) -> V075ProductionCampaignRunVerificationV1:
    """Replay all public semantics without rerunning any occurrence."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(claimed) is not V075ProductionCampaignRunV1
    ):
        _fail("campaign-run verifier requires exact public types")
    replayed_plan, replayed_plan_verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=repository_root,
            namespace=namespace,
            raw=claimed.plan.canonical_bytes,
        )
    )
    if (
        replayed_plan != claimed.plan
        or replayed_plan_verification != claimed.plan_verification
    ):
        _fail("campaign-run plan differs under verifier replay")
    replayed_verifications = tuple(
        occurrence.verify_v075_production_occurrence_authority_result_v1(
            repository_root=repository_root,
            namespace=namespace,
            claimed=item,
        )
        for item in claimed.occurrence_results
    )
    if replayed_verifications != claimed.occurrence_verifications:
        _fail("campaign-run occurrence verification changed under replay")
    replayed_reconciliation = (
        reconciliation.reconcile_v075_production_campaign_v1(
            repository_root=repository_root,
            namespace=namespace,
            plan=claimed.plan,
            plan_verification=claimed.plan_verification,
            occurrence_results=claimed.occurrence_results,
            occurrence_verifications=replayed_verifications,
        )
    )
    if (
        replayed_reconciliation.canonical_bytes
        != claimed.reconciliation.canonical_bytes
    ):
        _fail("campaign reconciliation changed under run verification")
    replayed_reconciliation_verification = (
        reconciliation.verify_v075_production_campaign_reconciliation_v1(
            repository_root=repository_root,
            namespace=namespace,
            claimed=replayed_reconciliation,
        )
    )
    replayed_endpoint = (
        endpoint.verify_v075_production_complete_bundle_endpoint_v1(
            repository_root=repository_root,
            namespace=namespace,
            claimed=replayed_reconciliation,
        )
    )
    replayed_work = _derive_runner_work_v1(
        profile=claimed.profile,
        plan=claimed.plan,
        verifications=replayed_verifications,
        completion_ordinals=claimed.runner_work.completion_ordinals,
        peak_active_tasks=claimed.runner_work.peak_active_tasks,
    )
    replayed_run = V075ProductionCampaignRunV1(
        _RUN_ISSUER,
        claimed.profile,
        claimed.plan,
        claimed.plan_verification,
        claimed.occurrence_results,
        replayed_verifications,
        replayed_reconciliation,
        replayed_reconciliation_verification,
        replayed_endpoint,
        replayed_work,
    )
    _assert_no_private_material_serialized_v1(replayed_run.to_document())
    if (
        replayed_run.run_id != claimed.run_id
        or replayed_run.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("production campaign run changed under independent replay")
    return V075ProductionCampaignRunVerificationV1(
        _VERIFICATION_ISSUER,
        claimed.run_id,
        replayed_run.run_id,
        claimed.profile.profile_id,
        claimed.plan.plan_id,
        claimed.runner_work.work_id,
        claimed.reconciliation.reconciliation_id,
        claimed.endpoint_verification.verification_id,
        tuple(item.result_id for item in claimed.occurrence_results),
        claimed.endpoint_verification.verdict,
    )


_CONSTRUCTION_BOUNDARY_ISSUER = object()
_CONSTRUCTION_FIXTURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ConstructionCampaignRunnerBoundaryResultV1:
    _issuer: object = field(repr=False, compare=False)
    entry_id: str
    scientific_ordinal: int
    marker_id: str
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.entry_id, "construction runner entry")
        _cid(self.marker_id, "construction runner marker")
        if (
            self._issuer is not _CONSTRUCTION_BOUNDARY_ISSUER
            or type(self.scientific_ordinal) is not int
            or self.scientific_ordinal
            not in range(occurrence_plan.EXPECTED_OCCURRENCE_COUNT)
        ):
            _fail("construction boundary result is caller-minted")
        object.__setattr__(
            self,
            "_result_id",
            _hash("construction_boundary", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_campaign_runner_boundary_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "entry_id": self.entry_id,
            "scientific_ordinal": self.scientific_ordinal,
            "marker_id": self.marker_id,
            "construction_fixture": True,
            "production_evidence": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def issue_v075_construction_campaign_runner_boundary_result_v1(
    *,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    marker_id: str,
) -> V075ConstructionCampaignRunnerBoundaryResultV1:
    if type(entry) is not occurrence_plan.V075ProductionOccurrencePlanEntryV1:
        _fail("construction boundary issuer requires one exact plan entry")
    return V075ConstructionCampaignRunnerBoundaryResultV1(
        _CONSTRUCTION_BOUNDARY_ISSUER,
        entry.entry_id,
        entry.scientific_ordinal,
        marker_id,
    )


@dataclass(frozen=True, slots=True)
class V075ConstructionCampaignRunnerFixtureEvidenceV1:
    _issuer: object = field(repr=False, compare=False)
    profile_id: str
    plan_id: str
    results: tuple[V075ConstructionCampaignRunnerBoundaryResultV1, ...]
    completion_ordinals: tuple[int, ...]
    peak_active_tasks: int
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.profile_id, "construction runner profile")
        _cid(self.plan_id, "construction runner plan")
        expected = occurrence_plan.EXPECTED_OCCURRENCE_COUNT
        if (
            self._issuer is not _CONSTRUCTION_FIXTURE_ISSUER
            or type(self.results) is not tuple
            or len(self.results) != expected
            or any(
                type(item)
                is not V075ConstructionCampaignRunnerBoundaryResultV1
                for item in self.results
            )
            or tuple(item.scientific_ordinal for item in self.results)
            != tuple(range(expected))
            or type(self.completion_ordinals) is not tuple
            or set(self.completion_ordinals) != set(range(expected))
            or len(self.completion_ordinals) != expected
            or type(self.peak_active_tasks) is not int
            or not 1 <= self.peak_active_tasks <= REGISTERED_MAX_WORKERS
        ):
            _fail("construction runner evidence is partial or reordered")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash("construction_fixture", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_campaign_runner_fixture_evidence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "runner_profile_id": self.profile_id,
            "plan_id": self.plan_id,
            "result_ids": [item.result_id for item in self.results],
            "scientific_ordinals": [
                item.scientific_ordinal for item in self.results
            ],
            "completion_ordinals": list(self.completion_ordinals),
            "future_submissions": len(self.results),
            "future_completions": len(self.results),
            "peak_active_tasks": self.peak_active_tasks,
            "scientific_order_restored": True,
            "construction_fixture": True,
            "production_evidence": False,
            "target_opened": False,
        }

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "results": [item.to_document() for item in self.results],
            "evidence_id": self.evidence_id,
        }


def execute_v075_construction_campaign_runner_fixture_v1(
    *,
    profile: V075ProductionCampaignRunnerProfileV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
) -> V075ConstructionCampaignRunnerFixtureEvidenceV1:
    """Exercise scheduling only behind a monkeypatched occurrence boundary."""

    if (
        type(profile) is not V075ProductionCampaignRunnerProfileV1
        or profile != freeze_v075_production_campaign_runner_profile_v1()
        or type(plan)
        is not occurrence_plan.V075ProductionOccurrencePlanV1
        or _execute_v075_production_occurrence_boundary_v1
        is _REGISTERED_PRODUCTION_BOUNDARY
    ):
        _fail(
            "construction runner fixture requires exact public inputs and "
            "an explicit test-only boundary monkeypatch"
        )
    scheduled = _run_parallel_schedule_v1(
        values=plan.entries,
        max_workers=profile.max_workers,
        boundary=_execute_v075_production_occurrence_boundary_v1,
    )
    results = scheduled.results
    if (
        any(
            type(item)
            is not V075ConstructionCampaignRunnerBoundaryResultV1
            for item in results
        )
        or tuple(item.entry_id for item in results)
        != tuple(item.entry_id for item in plan.entries)
    ):
        _fail("construction boundary results were reordered or transplanted")
    return V075ConstructionCampaignRunnerFixtureEvidenceV1(
        _CONSTRUCTION_FIXTURE_ISSUER,
        profile.profile_id,
        plan.plan_id,
        results,
        scheduled.completion_ordinals,
        scheduled.peak_active_tasks,
    )


__all__ = [
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRIVATE_LAW_DERIVATION_ALLOWED",
    "PRODUCTION_CAMPAIGN_RUNNER_READY",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_MAX_WORKERS",
    "SCHEMA_VERSION",
    "SECRET_GENERATION_ALLOWED",
    "TARGET_AUTHORITY_CREATED",
    "TARGET_EXECUTION_OPENED",
    "V075AuthorizedOccurrenceExecutionInputV1",
    "V075ConstructionCampaignRunnerBoundaryResultV1",
    "V075ConstructionCampaignRunnerFixtureEvidenceV1",
    "V075ProductionCampaignRunV1",
    "V075ProductionCampaignRunFailureCodeV1",
    "V075ProductionCampaignRunFailureV1",
    "V075ProductionCampaignRunnerInvariantViolation",
    "V075ProductionCampaignRunnerNativeWorkV1",
    "V075ProductionCampaignRunnerProfileV1",
    "V075ProductionCampaignRunnerProtocolOrIntegrityFailure",
    "V075ProductionCampaignRunVerificationV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "bind_v075_authorized_occurrence_execution_input_v1",
    "bind_v075_production_occurrence_execution_input_v1",
    "execute_v075_construction_campaign_runner_fixture_v1",
    "freeze_v075_production_campaign_runner_profile_v1",
    "issue_v075_construction_campaign_runner_boundary_result_v1",
    "run_v075_production_campaign_v1",
    "verify_v075_production_campaign_run_v1",
]
