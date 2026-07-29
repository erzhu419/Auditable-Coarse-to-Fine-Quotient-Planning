"""Typed V0-075 production-occurrence semantic authority.

This module is the bridge from the immutable fifteen-entry production plan to
one independently classifiable occurrence.  It accepts one exact plan entry,
executes the registered child IPC once, reconstructs the child planner result
without compiler/planner/search replay, closes the exact parent-owned observer
lifecycle, and—only for a ready candidate—runs the batch-native exact total
lift and its independent semantic verifier.

Construction and production entry points are deliberately separate.  The
construction entry point is a test fixture and can never create production
evidence.  The production entry point consumes an already-open, independently
authorized observer lifecycle; this module never opens the held-out target.

Portable documents contain only public artifacts and public attestations.  No
private salt, law, kernel, random word, or accepted-draw identity is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_occurrence_failure_lifecycle_authority_v1 as failure
from acfqp import v075_operational_planner_transport_v1 as transport
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_private_observer_boundary_v1 as observer
from acfqp import v075_production_occurrence_ipc_v1 as ipc
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_production_occurrence_authority_v1"

TARGET_EXECUTION_OPENED = False
HOST_MODEL_COMPILATION_ALLOWED = False
HOST_PLANNER_EXECUTION_ALLOWED = False
HOST_SOLVER_OR_SEARCH_ALLOWED = False
PRIVATE_MATERIAL_SERIALIZATION_ALLOWED = False

DOMAIN_TAGS = {
    "result": "acfqp:v075-production-occurrence-authority-result:v1",
    "verification": (
        "acfqp:v075-production-occurrence-authority-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 production-occurrence domains overlap")


class V075ProductionOccurrenceAuthorityInvariantViolation(ValueError):
    """A plan, IPC, lifecycle, transport, or total-lift binding failed."""


def _fail(message: str) -> None:
    raise V075ProductionOccurrenceAuthorityInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionOccurrenceAuthorityInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionOccurrenceAuthorityInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


class V075ProductionOccurrenceTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    INFEASIBILITY_CERTIFICATE = "INFEASIBILITY_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class V075ProductionOccurrenceTerminalCodeV1(str, Enum):
    EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE = (
        "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
    )
    EXACT_INFEASIBILITY_CERTIFICATE = "EXACT_INFEASIBILITY_CERTIFICATE"
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    STATISTICAL_ENVELOPE_MISS = "STATISTICAL_ENVELOPE_MISS"
    PLANNER_SEARCH_CAP_EXHAUSTED = "PLANNER_SEARCH_CAP_EXHAUSTED"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"
    ADAPTIVE_ROUND_LIMIT_REACHED = "ADAPTIVE_ROUND_LIMIT_REACHED"
    NO_UNCERTAIN_PROOF_FRONTIER = "NO_UNCERTAIN_PROOF_FRONTIER"
    DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED = (
        "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    )
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    PROCESS_FAILURE = "PROCESS_FAILURE"
    TIMEOUT = "TIMEOUT"


_CAP_TERMINALS = {
    V075ProductionOccurrenceTerminalCodeV1.PLANNER_SEARCH_CAP_EXHAUSTED,
    V075ProductionOccurrenceTerminalCodeV1.INCREMENTAL_CAP_EXHAUSTED,
    V075ProductionOccurrenceTerminalCodeV1.ADAPTIVE_ROUND_LIMIT_REACHED,
}

_FAILURE_TERMINALS = {
    V075ProductionOccurrenceTerminalCodeV1
    .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED,
    V075ProductionOccurrenceTerminalCodeV1.PROTOCOL_FAILURE,
    V075ProductionOccurrenceTerminalCodeV1.PROCESS_FAILURE,
    V075ProductionOccurrenceTerminalCodeV1.TIMEOUT,
}


def _candidate_terminal(
    status: (
        total_lift.V075BatchTotalLiftConstructionStatusV1
        | total_lift.V075BatchTotalLiftProductionStatusV1
    ),
) -> tuple[
    V075ProductionOccurrenceTerminalClassV1,
    V075ProductionOccurrenceTerminalCodeV1,
]:
    value = status.value
    if value in {
        "EXACT_POSITIVE_CONSTRUCTION_CONTROL",
        "EXACT_POSITIVE_PRODUCTION_CANDIDATE",
    }:
        return (
            V075ProductionOccurrenceTerminalClassV1.PLAN_CERTIFICATE,
            V075ProductionOccurrenceTerminalCodeV1
            .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE,
        )
    if value == "EXACT_GROUND_QUERY_INFEASIBLE":
        return (
            V075ProductionOccurrenceTerminalClassV1
            .INFEASIBILITY_CERTIFICATE,
            V075ProductionOccurrenceTerminalCodeV1
            .EXACT_INFEASIBILITY_CERTIFICATE,
        )
    mapping = {
        "EXACT_POLICY_RISK_FAILURE": (
            V075ProductionOccurrenceTerminalCodeV1
            .EXACT_POLICY_RISK_FAILURE
        ),
        "EXACT_POLICY_REGRET_FAILURE": (
            V075ProductionOccurrenceTerminalCodeV1
            .EXACT_POLICY_REGRET_FAILURE
        ),
        "STATISTICAL_ENVELOPE_MISS": (
            V075ProductionOccurrenceTerminalCodeV1
            .STATISTICAL_ENVELOPE_MISS
        ),
    }
    try:
        code = mapping[value]
    except KeyError as error:  # pragma: no cover - exhaustive registered enum
        raise V075ProductionOccurrenceAuthorityInvariantViolation(
            "unregistered total-lift status"
        ) from error
    return (
        V075ProductionOccurrenceTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE,
        code,
    )


def _ipc_terminal(
    value: str,
) -> V075ProductionOccurrenceTerminalCodeV1:
    try:
        return V075ProductionOccurrenceTerminalCodeV1(value)
    except ValueError as error:
        raise V075ProductionOccurrenceAuthorityInvariantViolation(
            "IPC emitted an unregistered production-occurrence terminal"
        ) from error


def _child_intent_count(
    value: ipc.V075ProductionIPCActualWorkV1,
) -> int:
    return (
        value.batch_intents
        + value.support_freeze_intents
        + value.round_begin_intents
    )


def _failure_actual_work(
    value: ipc.V075ProductionIPCActualWorkV1,
) -> failure.V075OccurrenceFailureActualWorkV1:
    if type(value) is not ipc.V075ProductionIPCActualWorkV1:
        _fail("failure work requires exact production IPC work")
    return failure.V075OccurrenceFailureActualWorkV1(
        process_launches=value.process_launches,
        child_messages=value.child_messages,
        parent_messages=value.parent_messages,
        batch_intents=value.batch_intents,
        support_freeze_intents=value.support_freeze_intents,
        round_begin_intents=value.round_begin_intents,
        accepted_draws=value.accepted_draws,
        outcome_aggregates=value.outcome_aggregates,
        child_bytes_read=value.child_bytes_read,
        parent_bytes_written=value.parent_bytes_written,
        protocol_checks=value.protocol_checks,
        host_operational_planner_replays=(
            value.host_operational_planner_replays
        ),
        child_exit_code=value.child_exit_code,
    )


def _failure_abort_stage(
    code: V075ProductionOccurrenceTerminalCodeV1,
) -> str:
    return {
        V075ProductionOccurrenceTerminalCodeV1
        .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED: "DIRECT_ROOT_DISCOVERY",
        V075ProductionOccurrenceTerminalCodeV1
        .PROTOCOL_FAILURE: "IPC_PROTOCOL",
        V075ProductionOccurrenceTerminalCodeV1
        .PROCESS_FAILURE: "CHILD_PROCESS",
        V075ProductionOccurrenceTerminalCodeV1.TIMEOUT: "CHILD_TIMEOUT",
    }[code]


def _sealed_lifecycle_document(
    value: lifecycle.V075SealedMultistageOccurrenceLifecycleV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_production_occurrence_sealed_lifecycle.v1",
        "schema_version": SCHEMA_VERSION,
        "closure": value.closure.to_document(),
        "verification": value.verification.to_document(),
        "signed_public_batches": [
            item.to_document() for item in value.batches
        ],
        "public_verifications": [
            item.to_document() for item in value.public_verifications
        ],
        "sequence_verifications": [
            item.to_document() for item in value.sequence_verifications
        ],
        "private_replay_verifications": [
            item.to_document()
            for item in value.private_replay_verifications
        ],
        "aggregate_support_evidence": [
            item.to_document()
            for item in value.aggregate_support_evidence
        ],
        "underlying_observer_closure": (
            value.underlying_closure.to_document()
        ),
        "underlying_observer_closure_verification": (
            value.underlying_closure_verification.to_document()
        ),
        "private_material_serialized": False,
    }


def _selected_source_transport(
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
) -> worker.V075SourcePriorTransportV1 | None:
    if (
        entry.arm
        is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    ):
        return plan.source_prior_transport
    return None


def _validate_preexecution_graph(
    *,
    repository_root: str | Path,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    expected_scope: lifecycle.V075LifecycleAuthorityScopeV1,
) -> occurrence_plan.V075ProductionOccurrencePlanVerificationV1:
    if (
        type(plan) is not occurrence_plan.V075ProductionOccurrencePlanV1
        or type(entry)
        is not occurrence_plan.V075ProductionOccurrencePlanEntryV1
        or type(controller)
        is not lifecycle.V075ParentOwnedMultistageObserverLifecycleV1
        or type(ipc_profile)
        is not ipc.V075ProductionOccurrenceIPCProfileV1
        or type(expected_scope)
        is not lifecycle.V075LifecycleAuthorityScopeV1
    ):
        _fail("production occurrence preexecution graph is untyped")
    namespace = controller.open_binding.namespace
    replayed, verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=repository_root,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )
    source_transport = _selected_source_transport(plan, entry)
    context = namespace.family.replicate_contexts[entry.context_ordinal]
    if (
        replayed != plan
        or verification.plan_id != plan.plan_id
        or plan.entries[entry.scientific_ordinal] != entry
        or entry.target_tape_namespace_id
        != namespace.target_tape_namespace_id
        or entry.remote_main_anchor_id
        != namespace.remote_main_anchor.external_id
        or entry.final_preregistration_id
        != namespace.final_preregistration.external_id
        or entry.public_family_generation_id
        != namespace.family.generation_id
        or entry.context_id != context.context_id
        or ipc_profile.occurrence_identity != entry.occurrence_identity
        or ipc_profile.open_lifecycle_binding
        != controller.open_binding
        or ipc_profile.context != context
        or ipc_profile.source_prior_transport != source_transport
        or ipc_profile.behavior
        is not ipc.V075ProductionIPCBehaviorV1.HONEST
        or controller.open_binding.authority_scope is not expected_scope
        or controller.open_binding.occurrence_id != entry.occurrence_id
        or controller.open_binding.context_id != entry.context_id
        or controller.open_binding.arm is not entry.arm
        or controller.open_binding.route_cap_profile
        != plan.cap_profile
    ):
        _fail(
            "plan, entry, namespace, authority, lifecycle, or IPC profile "
            "was transplanted"
        )
    return verification


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrenceAuthorityResultV1:
    _issuer: object = field(repr=False, compare=False)
    authority_scope: lifecycle.V075LifecycleAuthorityScopeV1
    plan: occurrence_plan.V075ProductionOccurrencePlanV1 = field(
        repr=False
    )
    plan_entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    )
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1 = field(
        repr=False
    )
    ipc_result: ipc.V075ProductionOccurrenceIPCResultV1
    operational_load: transport.V075OperationalPlannerLoadV1 | None
    sealed_lifecycle: (
        lifecycle.V075SealedMultistageOccurrenceLifecycleV1 | None
    )
    sealed_failure_lifecycle: (
        failure.V075SealedOccurrenceFailureLifecycleV1 | None
    )
    lineage: total_lift.V075BatchNativeLineageBindingV1 | None
    exact_replay: (
        total_lift.V075BatchNativeConstructionExactReplayV1
        | total_lift.V075BatchNativeProductionExactReplayV1
        | None
    )
    total_lift_candidate: (
        total_lift.V075BatchNativeConstructionTotalLiftCandidateV1
        | total_lift.V075BatchNativeProductionTotalLiftCandidateV1
        | None
    )
    total_lift_verification: (
        total_lift.V075BatchNativeConstructionTotalLiftVerificationV1
        | total_lift.V075BatchNativeProductionTotalLiftResultV1
        | None
    )
    terminal_class: V075ProductionOccurrenceTerminalClassV1
    terminal_code: V075ProductionOccurrenceTerminalCodeV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.authority_scope)
            is not lifecycle.V075LifecycleAuthorityScopeV1
            or type(self.plan)
            is not occurrence_plan.V075ProductionOccurrencePlanV1
            or type(self.plan_entry)
            is not occurrence_plan.V075ProductionOccurrencePlanEntryV1
            or type(self.plan_verification)
            is not occurrence_plan
            .V075ProductionOccurrencePlanVerificationV1
            or type(self.ipc_profile)
            is not ipc.V075ProductionOccurrenceIPCProfileV1
            or type(self.ipc_result)
            is not ipc.V075ProductionOccurrenceIPCResultV1
            or type(self.terminal_class)
            is not V075ProductionOccurrenceTerminalClassV1
            or type(self.terminal_code)
            is not V075ProductionOccurrenceTerminalCodeV1
        ):
            _fail("production occurrence result is untyped or caller-minted")
        entry = self.plan_entry
        result = self.ipc_result
        work = result.actual_work
        if (
            self.plan.entries[entry.scientific_ordinal] != entry
            or self.plan_verification.plan_id != self.plan.plan_id
            or self.plan_verification.entry_ids
            != tuple(item.entry_id for item in self.plan.entries)
            or self.plan_verification.occurrence_ids
            != tuple(item.occurrence_id for item in self.plan.entries)
            or self.ipc_profile.occurrence_identity
            != entry.occurrence_identity
            or result.profile_id != self.ipc_profile.profile_id
            or result.occurrence_id != entry.occurrence_id
            or result.authority_scope != self.authority_scope.value
            or result.observed_batches
            != tuple(result.observed_batches)
            or work.accepted_draws
            != sum(
                item.request.accepted_draw_count
                for item in result.observed_batches
            )
            or work.outcome_aggregates
            != sum(len(item.outcomes) for item in result.observed_batches)
            or work.process_launches != 1
            or work.host_operational_planner_replays != 0
        ):
            _fail("production occurrence result identity/work graph changed")

        standard = self.sealed_lifecycle is not None
        aborted = self.sealed_failure_lifecycle is not None
        if standard == aborted:
            _fail("occurrence must have exactly one typed lifecycle closure")

        if standard:
            sealed = self.sealed_lifecycle
            assert sealed is not None
            if (
                type(sealed)
                is not lifecycle.V075SealedMultistageOccurrenceLifecycleV1
                or sealed.closure.scope is not self.authority_scope
                or sealed.closure.occurrence_id != entry.occurrence_id
                or sealed.closure.context_id != entry.context_id
                or sealed.closure.arm != entry.arm.value
                or sealed.closure.target_tape_namespace_id
                != entry.target_tape_namespace_id
                or sealed.batches != result.observed_batches
                or sealed.closure.accepted_draw_count
                != work.accepted_draws
                or sealed.closure.process_launches
                != work.process_launches
                or sealed.closure.child_intent_count
                != _child_intent_count(work)
                or type(self.operational_load)
                is not transport.V075OperationalPlannerLoadV1
            ):
                _fail("successful lifecycle or operational load is stale")
        else:
            failed = self.sealed_failure_lifecycle
            assert failed is not None
            if (
                type(failed)
                is not failure.V075SealedOccurrenceFailureLifecycleV1
                or failed.closure.open_binding
                != self.ipc_profile.open_lifecycle_binding
                or failed.closure.open_binding.occurrence_id
                != entry.occurrence_id
                or failed.closure.batches != result.observed_batches
                or failed.closure.execution_evidence.actual_work
                != _failure_actual_work(work)
                or failed.closure.terminal_code.value
                != self.terminal_code.value
                or self.operational_load is not None
                or self.terminal_class
                is not V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
                or self.terminal_code not in _FAILURE_TERMINALS
            ):
                _fail("failure lifecycle did not retain exact IPC work")

        if self.operational_load is not None:
            loaded = self.operational_load
            child = result.child_result
            if (
                type(loaded)
                is not transport.V075OperationalPlannerLoadV1
                or type(child) is not dict
                or loaded.transport.occurrence_id != entry.occurrence_id
                or loaded.transport.transport_id
                != child.get("operational_planner_transport_id")
                or loaded.backend_result.to_document()
                != child.get("final_backend_result")
                or loaded.planner_result.to_document()
                != child.get("final_planner_result")
                or loaded.backend_result.request.occurrence_identity
                != entry.occurrence_identity
                or {
                    item.batch_id
                    for item in loaded.backend_result.request.batches
                }
                != {
                    item.batch_id for item in result.observed_batches
                }
            ):
                _fail("operational planner transport was transplanted")

        exact_values = (
            self.lineage,
            self.exact_replay,
            self.total_lift_candidate,
            self.total_lift_verification,
        )
        exact = all(item is not None for item in exact_values)
        if any(item is not None for item in exact_values) and not exact:
            _fail("exact total-lift chain is only partially present")
        if exact:
            assert self.lineage is not None
            assert self.exact_replay is not None
            assert self.total_lift_candidate is not None
            assert self.total_lift_verification is not None
            if (
                self.operational_load is None
                or self.sealed_lifecycle is None
                or self.lineage.envelope.policy.model.backend_result
                != self.operational_load.backend_result
                or self.lineage.envelope.policy.planner_result
                != self.operational_load.planner_result
                or self.lineage.sealed_lifecycle
                != self.sealed_lifecycle
                or self.exact_replay.lineage_id != self.lineage.lineage_id
                or self.total_lift_candidate.lineage_id
                != self.lineage.lineage_id
                or self.total_lift_candidate.exact_replay_id
                != self.exact_replay.replay_id
            ):
                _fail("exact total-lift identity chain was transplanted")
            if (
                self.authority_scope
                is lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
            ):
                if (
                    type(self.exact_replay)
                    is not total_lift
                    .V075BatchNativeConstructionExactReplayV1
                    or type(self.total_lift_candidate)
                    is not total_lift
                    .V075BatchNativeConstructionTotalLiftCandidateV1
                    or type(self.total_lift_verification)
                    is not total_lift
                    .V075BatchNativeConstructionTotalLiftVerificationV1
                    or self.total_lift_verification.candidate
                    != self.total_lift_candidate
                ):
                    _fail("construction exact-lift types crossed scope")
            else:
                if (
                    type(self.exact_replay)
                    is not total_lift
                    .V075BatchNativeProductionExactReplayV1
                    or type(self.total_lift_candidate)
                    is not total_lift
                    .V075BatchNativeProductionTotalLiftCandidateV1
                    or type(self.total_lift_verification)
                    is not total_lift
                    .V075BatchNativeProductionTotalLiftResultV1
                    or self.total_lift_verification.candidate
                    != self.total_lift_candidate
                ):
                    _fail("production exact-lift types crossed scope")
            expected_terminal = _candidate_terminal(
                self.total_lift_candidate.status
            )
            if (
                (self.terminal_class, self.terminal_code)
                != expected_terminal
                or self.sealed_lifecycle.closure.terminal_code
                is not lifecycle.V075LifecycleTerminalCodeV1
                .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
            ):
                _fail("exact total-lift terminal was misclassified")
        else:
            if (
                self.terminal_class
                is not V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
                or (
                    standard
                    and self.terminal_code
                    not in (
                        _CAP_TERMINALS
                        | {
                            V075ProductionOccurrenceTerminalCodeV1
                            .NO_UNCERTAIN_PROOF_FRONTIER
                        }
                    )
                )
            ):
                _fail("noncandidate occurrence was misclassified")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def occurrence_id(self) -> str:
        return self.plan_entry.occurrence_id

    @property
    def accepted_draw_count(self) -> int:
        return self.ipc_result.actual_work.accepted_draws

    @property
    def process_launch_count(self) -> int:
        return self.ipc_result.actual_work.process_launches

    @property
    def online_work_id(self) -> str:
        return self.ipc_result.actual_work.work_id

    @property
    def exact_valid_total_lift_plan(self) -> bool:
        return (
            self.terminal_class
            is V075ProductionOccurrenceTerminalClassV1.PLAN_CERTIFICATE
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_occurrence_authority_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_scope": self.authority_scope.value,
            "plan_id": self.plan.plan_id,
            "plan_entry_id": self.plan_entry.entry_id,
            "plan_verification_id": (
                self.plan_verification.verification_id
            ),
            "occurrence_id": self.occurrence_id,
            "context_id": self.plan_entry.context_id,
            "context_ordinal": self.plan_entry.context_ordinal,
            "arm": self.plan_entry.arm.value,
            "arm_ordinal": self.plan_entry.arm_ordinal,
            "scientific_ordinal": self.plan_entry.scientific_ordinal,
            "transport_ordinal": self.plan_entry.transport_ordinal,
            "ipc_profile_id": self.ipc_profile.profile_id,
            "ipc_result_id": self.ipc_result.result_id,
            "ipc_journal_id": self.ipc_result.journal_id,
            "ipc_actual_work_id": self.ipc_result.actual_work.work_id,
            "operational_planner_load_id": (
                None
                if self.operational_load is None
                else self.operational_load.load_id
            ),
            "multistage_closure_id": (
                None
                if self.sealed_lifecycle is None
                else self.sealed_lifecycle.closure.closure_id
            ),
            "failure_lifecycle_closure_id": (
                None
                if self.sealed_failure_lifecycle is None
                else self.sealed_failure_lifecycle.closure.closure_id
            ),
            "lineage_id": (
                None if self.lineage is None else self.lineage.lineage_id
            ),
            "exact_replay_id": (
                None
                if self.exact_replay is None
                else self.exact_replay.replay_id
            ),
            "total_lift_candidate_id": (
                None
                if self.total_lift_candidate is None
                else self.total_lift_candidate.candidate_id
            ),
            "total_lift_verification_id": (
                None
                if self.total_lift_verification is None
                else (
                    self.total_lift_verification.verification_id
                    if type(self.total_lift_verification)
                    is total_lift
                    .V075BatchNativeConstructionTotalLiftVerificationV1
                    else self.total_lift_verification.result_id
                )
            ),
            "terminal_scope": "LOGICAL_OCCURRENCE",
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "exact_valid_total_lift_plan": (
                self.exact_valid_total_lift_plan
            ),
            "accepted_draw_count": self.accepted_draw_count,
            "outcome_aggregate_count": (
                self.ipc_result.actual_work.outcome_aggregates
            ),
            "process_launch_count": self.process_launch_count,
            "child_message_count": (
                self.ipc_result.actual_work.child_messages
            ),
            "parent_message_count": (
                self.ipc_result.actual_work.parent_messages
            ),
            "child_bytes_read": (
                self.ipc_result.actual_work.child_bytes_read
            ),
            "parent_bytes_written": (
                self.ipc_result.actual_work.parent_bytes_written
            ),
            "host_model_compiler_calls": 0,
            "host_planner_calls": 0,
            "host_solver_or_search_calls": 0,
            "all_failed_work_retained": True,
            "construction_fixture": (
                self.authority_scope
                is lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
            ),
            "production_evidence": (
                self.authority_scope
                is lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
            ),
            "private_law_serialized": False,
            "private_salt_serialized": False,
            "private_kernel_serialized": False,
            "random_words_serialized": False,
            "accepted_draw_indices_serialized": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "plan_entry": self.plan_entry.to_document(),
            "plan_verification": self.plan_verification.to_document(),
            "ipc_result": self.ipc_result.to_document(),
            "operational_planner_load": (
                None
                if self.operational_load is None
                else self.operational_load.to_document()
            ),
            "sealed_lifecycle": (
                None
                if self.sealed_lifecycle is None
                else _sealed_lifecycle_document(self.sealed_lifecycle)
            ),
            "sealed_failure_lifecycle": (
                None
                if self.sealed_failure_lifecycle is None
                else self.sealed_failure_lifecycle.to_document()
            ),
            "batch_native_total_lift_lineage": (
                None
                if self.lineage is None
                else self.lineage.to_document()
            ),
            "exact_replay": (
                None
                if self.exact_replay is None
                else self.exact_replay.to_document()
            ),
            "total_lift_candidate": (
                None
                if self.total_lift_candidate is None
                else self.total_lift_candidate.to_document()
            ),
            "total_lift_verification": (
                None
                if self.total_lift_verification is None
                else self.total_lift_verification.to_document()
            ),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _load_operational_result(
    *,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
    ipc_result: ipc.V075ProductionOccurrenceIPCResultV1,
) -> transport.V075OperationalPlannerLoadV1:
    child = ipc_result.child_result
    if (
        ipc_result.status != "PASS"
        or type(child) is not dict
        or type(child.get("operational_planner_transport_bytes_hex"))
        is not str
    ):
        _fail("successful IPC result lacks one operational transport")
    try:
        claimed_bytes = bytes.fromhex(
            child["operational_planner_transport_bytes_hex"]
        )
    except ValueError as error:
        raise V075ProductionOccurrenceAuthorityInvariantViolation(
            "operational transport is not canonical hexadecimal"
        ) from error
    loaded = transport.load_v075_operational_planner_transport_v1(
        occurrence_identity=entry.occurrence_identity,
        batches=ipc_result.observed_batches,
        source_prior_transport=source_prior_transport,
        claimed_bytes=claimed_bytes,
    )
    if (
        loaded.transport.transport_id
        != child.get("operational_planner_transport_id")
        or loaded.transport.to_document()
        != child.get("operational_planner_transport")
    ):
        _fail("operational transport bytes/document/ID disagree")
    return loaded


def _issue_result(
    *,
    scope: lifecycle.V075LifecycleAuthorityScopeV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    ipc_result: ipc.V075ProductionOccurrenceIPCResultV1,
    operational_load: transport.V075OperationalPlannerLoadV1 | None,
    sealed_lifecycle: (
        lifecycle.V075SealedMultistageOccurrenceLifecycleV1 | None
    ),
    sealed_failure_lifecycle: (
        failure.V075SealedOccurrenceFailureLifecycleV1 | None
    ),
    lineage_value: total_lift.V075BatchNativeLineageBindingV1 | None,
    exact_replay: (
        total_lift.V075BatchNativeConstructionExactReplayV1
        | total_lift.V075BatchNativeProductionExactReplayV1
        | None
    ),
    candidate: (
        total_lift.V075BatchNativeConstructionTotalLiftCandidateV1
        | total_lift.V075BatchNativeProductionTotalLiftCandidateV1
        | None
    ),
    total_lift_verification: (
        total_lift.V075BatchNativeConstructionTotalLiftVerificationV1
        | total_lift.V075BatchNativeProductionTotalLiftResultV1
        | None
    ),
    terminal_class: V075ProductionOccurrenceTerminalClassV1,
    terminal_code: V075ProductionOccurrenceTerminalCodeV1,
) -> V075ProductionOccurrenceAuthorityResultV1:
    return V075ProductionOccurrenceAuthorityResultV1(
        _RESULT_ISSUER,
        scope,
        plan,
        entry,
        plan_verification,
        ipc_profile,
        ipc_result,
        operational_load,
        sealed_lifecycle,
        sealed_failure_lifecycle,
        lineage_value,
        exact_replay,
        candidate,
        total_lift_verification,
        terminal_class,
        terminal_code,
    )


def _close_construction_failure(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_result: ipc.V075ProductionOccurrenceIPCResultV1,
    authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_environment: (
        batched.V075ConstructionBatchReplayEnvironmentFixtureV1
    ),
) -> failure.V075SealedOccurrenceFailureLifecycleV1:
    code = failure.V075OccurrenceFailureTerminalCodeV1(
        ipc_result.terminal_code
    )
    evidence = failure.issue_v075_construction_failure_execution_fixture_v1(
        open_lifecycle_binding=controller.open_binding,
        terminal_code=code,
        actual_work=_failure_actual_work(ipc_result.actual_work),
    )
    authority_value = (
        failure.open_v075_occurrence_failure_lifecycle_authority_v1(
            controller
        )
    )
    sealed = authority_value.close_construction_v1(
        authority=authority,
        private_environment=private_environment,
        execution_evidence=evidence,
        abort_stage=_failure_abort_stage(
            V075ProductionOccurrenceTerminalCodeV1(code.value)
        ),
    )
    verified = (
        failure.verify_v075_construction_occurrence_failure_lifecycle_v1(
            closure=sealed.closure,
            authority=authority,
            private_environment=private_environment,
        )
    )
    if verified != sealed.verification:
        _fail("construction failure closure changed under independent replay")
    return sealed


def _close_production_failure(
    *,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_result: ipc.V075ProductionOccurrenceIPCResultV1,
    authority: Any,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    private_salt: bytes,
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
) -> failure.V075SealedOccurrenceFailureLifecycleV1:
    evidence = failure.freeze_v075_production_failure_execution_evidence_v1(
        ipc_result=ipc_result,
        controller=controller,
    )
    authority_value = (
        failure.open_v075_occurrence_failure_lifecycle_authority_v1(
            controller
        )
    )
    sealed = authority_value.close_production_v1(
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=private_environment,
        execution_evidence=evidence,
        abort_stage=_failure_abort_stage(
            V075ProductionOccurrenceTerminalCodeV1(
                evidence.terminal_code.value
            )
        ),
    )
    verified = failure.verify_v075_production_occurrence_failure_lifecycle_v1(
        closure=sealed.closure,
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    if verified != sealed.verification:
        _fail("production failure closure changed under independent replay")
    return sealed


def execute_v075_construction_occurrence_fixture_v1(
    *,
    repository_root: str | Path,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    authority: observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1,
    private_environment: (
        batched.V075ConstructionBatchReplayEnvironmentFixtureV1
    ),
) -> V075ProductionOccurrenceAuthorityResultV1:
    """Execute one exact construction-only occurrence fixture."""

    if (
        type(authority)
        is not observer.V075ConstructionOnlyObserverOpenAuthorityFixtureV1
        or type(private_environment)
        is not batched.V075ConstructionBatchReplayEnvironmentFixtureV1
        or authority.namespace != controller.open_binding.namespace
        or private_environment.namespace != authority.namespace
    ):
        _fail("construction occurrence authority/environment is transplanted")
    plan_verification = _validate_preexecution_graph(
        repository_root=repository_root,
        plan=plan,
        entry=entry,
        controller=controller,
        ipc_profile=ipc_profile,
        expected_scope=(
            lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        ),
    )
    ipc_result = (
        ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
            profile=ipc_profile,
            controller=controller,
        )
    )
    if ipc_result.status in {"FAILED", "NONCERTIFICATE"}:
        code = _ipc_terminal(ipc_result.terminal_code)
        if code not in _FAILURE_TERMINALS:
            _fail("construction IPC failure has no failure-lifecycle code")
        failed = _close_construction_failure(
            controller=controller,
            ipc_result=ipc_result,
            authority=authority,
            private_environment=private_environment,
        )
        return _issue_result(
            scope=(
                lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
            ),
            plan=plan,
            entry=entry,
            plan_verification=plan_verification,
            ipc_profile=ipc_profile,
            ipc_result=ipc_result,
            operational_load=None,
            sealed_lifecycle=None,
            sealed_failure_lifecycle=failed,
            lineage_value=None,
            exact_replay=None,
            candidate=None,
            total_lift_verification=None,
            terminal_class=(
                V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            ),
            terminal_code=code,
        )

    loaded = _load_operational_result(
        entry=entry,
        source_prior_transport=_selected_source_transport(plan, entry),
        ipc_result=ipc_result,
    )
    child = ipc_result.child_result
    assert child is not None
    child_terminal = child["terminal_code"]
    ready = loaded.planner_result.ready_for_exact_total_lift
    if ready != (
        child_terminal
        in {
            "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT",
            "READY_FOR_EXACT_TOTAL_LIFT",
        }
    ):
        _fail("child readiness and reconstructed planner disagree")
    lifecycle_terminal = (
        lifecycle.V075LifecycleTerminalCodeV1
        .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        if ready
        else (
            lifecycle.V075LifecycleTerminalCodeV1
            .NONCERTIFICATE_CAP_CLOSED
            if _ipc_terminal(child_terminal) in _CAP_TERMINALS
            else lifecycle.V075LifecycleTerminalCodeV1
            .NONCERTIFICATE_PROTOCOL_CLOSED
        )
    )
    sealed = controller.close_construction_v1(
        authority=authority,
        private_environment=private_environment,
        process_launches=ipc_result.actual_work.process_launches,
        child_intent_count=_child_intent_count(ipc_result.actual_work),
        terminal_code=lifecycle_terminal,
    )
    if not ready:
        code = _ipc_terminal(child_terminal)
        return _issue_result(
            scope=(
                lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
            ),
            plan=plan,
            entry=entry,
            plan_verification=plan_verification,
            ipc_profile=ipc_profile,
            ipc_result=ipc_result,
            operational_load=loaded,
            sealed_lifecycle=sealed,
            sealed_failure_lifecycle=None,
            lineage_value=None,
            exact_replay=None,
            candidate=None,
            total_lift_verification=None,
            terminal_class=(
                V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            ),
            terminal_code=code,
        )

    lineage_value = (
        total_lift.freeze_v075_batch_native_total_lift_lineage_v1(
            backend_result=loaded.backend_result,
            planner_result=loaded.planner_result,
            sealed_lifecycle=sealed,
        )
    )
    exact = total_lift.mint_v075_batch_native_construction_exact_replay_v1(
        lineage=lineage_value,
        authority=authority,
        private_environment=private_environment,
    )
    first_verification = (
        total_lift.evaluate_v075_batch_native_construction_total_lift_v1(
            lineage=lineage_value,
            exact_replay=exact,
        )
    )
    candidate = first_verification.candidate
    independent = (
        total_lift
        .verify_v075_batch_native_construction_total_lift_candidate_v1(
            lineage=lineage_value,
            exact_replay=exact,
            claimed=candidate,
        )
    )
    if independent != first_verification:
        _fail("construction total lift changed under independent replay")
    terminal_class, terminal_code = _candidate_terminal(candidate.status)
    return _issue_result(
        scope=lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY,
        plan=plan,
        entry=entry,
        plan_verification=plan_verification,
        ipc_profile=ipc_profile,
        ipc_result=ipc_result,
        operational_load=loaded,
        sealed_lifecycle=sealed,
        sealed_failure_lifecycle=None,
        lineage_value=lineage_value,
        exact_replay=exact,
        candidate=candidate,
        total_lift_verification=independent,
        terminal_class=terminal_class,
        terminal_code=terminal_code,
    )


def execute_v075_production_occurrence_v1(
    *,
    repository_root: str | Path,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    entry: occurrence_plan.V075ProductionOccurrencePlanEntryV1,
    controller: lifecycle.V075ParentOwnedMultistageObserverLifecycleV1,
    ipc_profile: ipc.V075ProductionOccurrenceIPCProfileV1,
    authority: Any,
    private_salt: bytes,
    private_environment: private_env.V075PrivateGeneratedEnvironmentV1,
) -> V075ProductionOccurrenceAuthorityResultV1:
    """Execute one preauthorized production occurrence.

    The caller must already own the exact open production lifecycle.  This
    function neither constructs nor opens an observer authority.
    """

    from acfqp import v075_preopen_target_authorization_v1 as preopen

    if (
        type(authority) is not preopen.V075ObserverOpenAuthorizationV1
        or type(private_salt) is not bytes
        or not private_salt
        or type(private_environment)
        is not private_env.V075PrivateGeneratedEnvironmentV1
        or private_environment.family
        != controller.open_binding.namespace.family
    ):
        _fail("production occurrence requires exact private authorities")
    plan_verification = _validate_preexecution_graph(
        repository_root=repository_root,
        plan=plan,
        entry=entry,
        controller=controller,
        ipc_profile=ipc_profile,
        expected_scope=lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
    )
    ipc_result = (
        ipc.execute_v075_production_adaptive_occurrence_ipc_v1(
            profile=ipc_profile,
            controller=controller,
        )
    )
    namespace = controller.open_binding.namespace
    if ipc_result.status in {"FAILED", "NONCERTIFICATE"}:
        code = _ipc_terminal(ipc_result.terminal_code)
        if code not in _FAILURE_TERMINALS:
            _fail("production IPC failure has no failure-lifecycle code")
        failed = _close_production_failure(
            controller=controller,
            ipc_result=ipc_result,
            authority=authority,
            namespace=namespace,
            private_salt=private_salt,
            private_environment=private_environment,
        )
        return _issue_result(
            scope=lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
            plan=plan,
            entry=entry,
            plan_verification=plan_verification,
            ipc_profile=ipc_profile,
            ipc_result=ipc_result,
            operational_load=None,
            sealed_lifecycle=None,
            sealed_failure_lifecycle=failed,
            lineage_value=None,
            exact_replay=None,
            candidate=None,
            total_lift_verification=None,
            terminal_class=(
                V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            ),
            terminal_code=code,
        )

    loaded = _load_operational_result(
        entry=entry,
        source_prior_transport=_selected_source_transport(plan, entry),
        ipc_result=ipc_result,
    )
    child = ipc_result.child_result
    assert child is not None
    child_terminal = child["terminal_code"]
    ready = loaded.planner_result.ready_for_exact_total_lift
    if ready != (
        child_terminal
        in {
            "CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT",
            "READY_FOR_EXACT_TOTAL_LIFT",
        }
    ):
        _fail("production child readiness differs from transported planner")
    lifecycle_terminal = (
        lifecycle.V075LifecycleTerminalCodeV1
        .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        if ready
        else (
            lifecycle.V075LifecycleTerminalCodeV1
            .NONCERTIFICATE_CAP_CLOSED
            if _ipc_terminal(child_terminal) in _CAP_TERMINALS
            else lifecycle.V075LifecycleTerminalCodeV1
            .NONCERTIFICATE_PROTOCOL_CLOSED
        )
    )
    sealed = controller.close_production_v1(
        authority=authority,
        namespace=namespace,
        private_salt=private_salt,
        private_environment=private_environment,
        process_launches=ipc_result.actual_work.process_launches,
        child_intent_count=_child_intent_count(ipc_result.actual_work),
        terminal_code=lifecycle_terminal,
    )
    if not ready:
        code = _ipc_terminal(child_terminal)
        return _issue_result(
            scope=lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
            plan=plan,
            entry=entry,
            plan_verification=plan_verification,
            ipc_profile=ipc_profile,
            ipc_result=ipc_result,
            operational_load=loaded,
            sealed_lifecycle=sealed,
            sealed_failure_lifecycle=None,
            lineage_value=None,
            exact_replay=None,
            candidate=None,
            total_lift_verification=None,
            terminal_class=(
                V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE
            ),
            terminal_code=code,
        )

    lineage_value = (
        total_lift.freeze_v075_batch_native_total_lift_lineage_v1(
            backend_result=loaded.backend_result,
            planner_result=loaded.planner_result,
            sealed_lifecycle=sealed,
        )
    )
    exact = total_lift.mint_v075_batch_native_production_exact_replay_v1(
        lineage=lineage_value,
        authority=authority,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    candidate = (
        total_lift.evaluate_v075_batch_native_production_total_lift_v1(
            lineage=lineage_value,
            exact_replay=exact,
        )
    )
    independent = (
        total_lift
        .verify_v075_batch_native_production_total_lift_candidate_v1(
            lineage=lineage_value,
            exact_replay=exact,
            claimed=candidate,
        )
    )
    terminal_class, terminal_code = _candidate_terminal(candidate.status)
    return _issue_result(
        scope=lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
        plan=plan,
        entry=entry,
        plan_verification=plan_verification,
        ipc_profile=ipc_profile,
        ipc_result=ipc_result,
        operational_load=loaded,
        sealed_lifecycle=sealed,
        sealed_failure_lifecycle=None,
        lineage_value=lineage_value,
        exact_replay=exact,
        candidate=candidate,
        total_lift_verification=independent,
        terminal_class=terminal_class,
        terminal_code=terminal_code,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrenceAuthorityVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    result_id: str
    occurrence_id: str
    plan_id: str
    plan_entry_id: str
    plan_verification_id: str
    ipc_result_id: str
    ipc_actual_work_id: str
    lifecycle_closure_id: str
    terminal_class: V075ProductionOccurrenceTerminalClassV1
    terminal_code: V075ProductionOccurrenceTerminalCodeV1
    accepted_draw_count: int
    outcome_aggregate_count: int
    process_launch_count: int
    child_message_count: int
    parent_message_count: int
    child_bytes_read: int
    parent_bytes_written: int
    protocol_check_count: int
    batch_intent_count: int
    support_freeze_intent_count: int
    round_begin_intent_count: int
    host_operational_planner_replay_count: int
    child_exit_code: int | None
    stderr_byte_count: int
    operational_transport_present: bool
    exact_chain_present: bool
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified occurrence result"),
            (self.occurrence_id, "verified occurrence"),
            (self.plan_id, "verified occurrence plan"),
            (self.plan_entry_id, "verified plan entry"),
            (self.plan_verification_id, "verified plan verification"),
            (self.ipc_result_id, "verified IPC result"),
            (self.ipc_actual_work_id, "verified IPC actual work"),
            (self.lifecycle_closure_id, "verified lifecycle closure"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.terminal_class)
            is not V075ProductionOccurrenceTerminalClassV1
            or type(self.terminal_code)
            is not V075ProductionOccurrenceTerminalCodeV1
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count < 0
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.outcome_aggregate_count,
                    self.child_message_count,
                    self.parent_message_count,
                    self.child_bytes_read,
                    self.parent_bytes_written,
                    self.protocol_check_count,
                    self.batch_intent_count,
                    self.support_freeze_intent_count,
                    self.round_begin_intent_count,
                    self.stderr_byte_count,
                )
            )
            or self.process_launch_count != 1
            or self.host_operational_planner_replay_count != 0
            or type(self.child_exit_code) not in {int, type(None)}
            or type(self.operational_transport_present) is not bool
            or type(self.exact_chain_present) is not bool
        ):
            _fail("occurrence verification is malformed or caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_occurrence_authority_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "occurrence_id": self.occurrence_id,
            "plan_id": self.plan_id,
            "plan_entry_id": self.plan_entry_id,
            "plan_verification_id": self.plan_verification_id,
            "ipc_result_id": self.ipc_result_id,
            "ipc_actual_work_id": self.ipc_actual_work_id,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "accepted_draw_count": self.accepted_draw_count,
            "outcome_aggregate_count": self.outcome_aggregate_count,
            "process_launch_count": self.process_launch_count,
            "child_message_count": self.child_message_count,
            "parent_message_count": self.parent_message_count,
            "child_bytes_read": self.child_bytes_read,
            "parent_bytes_written": self.parent_bytes_written,
            "protocol_check_count": self.protocol_check_count,
            "batch_intent_count": self.batch_intent_count,
            "support_freeze_intent_count": (
                self.support_freeze_intent_count
            ),
            "round_begin_intent_count": self.round_begin_intent_count,
            "host_operational_planner_replay_count": (
                self.host_operational_planner_replay_count
            ),
            "child_exit_code": self.child_exit_code,
            "stderr_byte_count": self.stderr_byte_count,
            "operational_transport_present": (
                self.operational_transport_present
            ),
            "exact_chain_present": self.exact_chain_present,
            "plan_replayed": True,
            "entry_identity_replayed": True,
            "ipc_work_reconciled": True,
            "operational_transport_reloaded_without_search": (
                self.operational_transport_present
            ),
            "operational_transport_absence_validated": (
                not self.operational_transport_present
            ),
            "lifecycle_signature_replayed": True,
            "total_lift_candidate_independently_recomputed": (
                self.exact_chain_present
            ),
            "exact_chain_absence_validated": (
                not self.exact_chain_present
            ),
            "host_model_compiler_calls": 0,
            "host_planner_calls": 0,
            "host_solver_or_search_calls": 0,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_production_occurrence_authority_result_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    claimed: V075ProductionOccurrenceAuthorityResultV1,
) -> V075ProductionOccurrenceAuthorityVerificationV1:
    """Independently replay every public occurrence identity and semantic edge."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(claimed)
        is not V075ProductionOccurrenceAuthorityResultV1
    ):
        _fail("occurrence verifier requires exact public types")
    replayed_plan, plan_verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=repository_root,
            namespace=namespace,
            raw=claimed.plan.canonical_bytes,
        )
    )
    if (
        replayed_plan != claimed.plan
        or plan_verification != claimed.plan_verification
        or claimed.plan_entry
        != replayed_plan.entries[claimed.plan_entry.scientific_ordinal]
        or claimed.ipc_profile.open_lifecycle_binding.namespace
        != namespace
    ):
        _fail("occurrence plan/entry differs under independent replay")

    if claimed.operational_load is not None:
        reloaded = _load_operational_result(
            entry=claimed.plan_entry,
            source_prior_transport=_selected_source_transport(
                claimed.plan,
                claimed.plan_entry,
            ),
            ipc_result=claimed.ipc_result,
        )
        if reloaded != claimed.operational_load:
            _fail("operational planner transport differs under reload")

    if claimed.sealed_lifecycle is not None:
        sealed = claimed.sealed_lifecycle
        replayed_lifecycle = (
            lifecycle.verify_v075_multistage_occurrence_closure_v1(
                closure=sealed.closure,
                batches=sealed.batches,
                public_verifications=sealed.public_verifications,
                sequence_verifications=sealed.sequence_verifications,
                private_replay_verifications=(
                    sealed.private_replay_verifications
                ),
                aggregate_support_evidence=(
                    sealed.aggregate_support_evidence
                ),
                underlying_closure=sealed.underlying_closure,
                underlying_closure_verification=(
                    sealed.underlying_closure_verification
                ),
                observer_open_binding=(
                    sealed.underlying_closure.authority_binding
                ),
            )
        )
        if replayed_lifecycle != sealed.verification:
            _fail("multistage lifecycle differs under independent replay")
        closure_id = sealed.closure.closure_id
    else:
        sealed_failure = claimed.sealed_failure_lifecycle
        assert sealed_failure is not None
        replayed_failure = (
            failure.verify_v075_occurrence_failure_lifecycle_public_v1(
                closure=sealed_failure.closure
            )
        )
        if replayed_failure != sealed_failure.verification:
            _fail("failure lifecycle differs under independent replay")
        closure_id = sealed_failure.closure.closure_id

    if claimed.total_lift_candidate is not None:
        assert claimed.lineage is not None
        assert claimed.exact_replay is not None
        if (
            claimed.authority_scope
            is lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY
        ):
            exact = claimed.exact_replay
            candidate = claimed.total_lift_candidate
            assert type(exact) is (
                total_lift.V075BatchNativeConstructionExactReplayV1
            )
            assert type(candidate) is (
                total_lift.V075BatchNativeConstructionTotalLiftCandidateV1
            )
            replayed_total = (
                total_lift
                .verify_v075_batch_native_construction_total_lift_candidate_v1(
                    lineage=claimed.lineage,
                    exact_replay=exact,
                    claimed=candidate,
                )
            )
        else:
            exact = claimed.exact_replay
            candidate = claimed.total_lift_candidate
            assert type(exact) is (
                total_lift.V075BatchNativeProductionExactReplayV1
            )
            assert type(candidate) is (
                total_lift.V075BatchNativeProductionTotalLiftCandidateV1
            )
            replayed_total = (
                total_lift
                .verify_v075_batch_native_production_total_lift_candidate_v1(
                    lineage=claimed.lineage,
                    exact_replay=exact,
                    claimed=candidate,
                )
            )
        if replayed_total != claimed.total_lift_verification:
            _fail("total-lift result differs under independent replay")

    # Reissuing the immutable result reruns all exact-type and identity checks.
    replayed_result = _issue_result(
        scope=claimed.authority_scope,
        plan=claimed.plan,
        entry=claimed.plan_entry,
        plan_verification=claimed.plan_verification,
        ipc_profile=claimed.ipc_profile,
        ipc_result=claimed.ipc_result,
        operational_load=claimed.operational_load,
        sealed_lifecycle=claimed.sealed_lifecycle,
        sealed_failure_lifecycle=claimed.sealed_failure_lifecycle,
        lineage_value=claimed.lineage,
        exact_replay=claimed.exact_replay,
        candidate=claimed.total_lift_candidate,
        total_lift_verification=claimed.total_lift_verification,
        terminal_class=claimed.terminal_class,
        terminal_code=claimed.terminal_code,
    )
    if replayed_result != claimed or replayed_result.result_id != claimed.result_id:
        _fail("occurrence result differs under semantic replay")
    return V075ProductionOccurrenceAuthorityVerificationV1(
        _VERIFICATION_ISSUER,
        claimed.result_id,
        claimed.occurrence_id,
        claimed.plan.plan_id,
        claimed.plan_entry.entry_id,
        claimed.plan_verification.verification_id,
        claimed.ipc_result.result_id,
        claimed.ipc_result.actual_work.work_id,
        closure_id,
        claimed.terminal_class,
        claimed.terminal_code,
        claimed.accepted_draw_count,
        claimed.ipc_result.actual_work.outcome_aggregates,
        claimed.process_launch_count,
        claimed.ipc_result.actual_work.child_messages,
        claimed.ipc_result.actual_work.parent_messages,
        claimed.ipc_result.actual_work.child_bytes_read,
        claimed.ipc_result.actual_work.parent_bytes_written,
        claimed.ipc_result.actual_work.protocol_checks,
        claimed.ipc_result.actual_work.batch_intents,
        claimed.ipc_result.actual_work.support_freeze_intents,
        claimed.ipc_result.actual_work.round_begin_intents,
        claimed.ipc_result.actual_work.host_operational_planner_replays,
        claimed.ipc_result.actual_work.child_exit_code,
        claimed.ipc_result.stderr_byte_count,
        claimed.operational_load is not None,
        claimed.total_lift_candidate is not None,
    )


__all__ = [
    "DOMAIN_TAGS",
    "HOST_MODEL_COMPILATION_ALLOWED",
    "HOST_PLANNER_EXECUTION_ALLOWED",
    "HOST_SOLVER_OR_SEARCH_ALLOWED",
    "PRIVATE_MATERIAL_SERIALIZATION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionOccurrenceAuthorityInvariantViolation",
    "V075ProductionOccurrenceAuthorityResultV1",
    "V075ProductionOccurrenceAuthorityVerificationV1",
    "V075ProductionOccurrenceTerminalClassV1",
    "V075ProductionOccurrenceTerminalCodeV1",
    "execute_v075_construction_occurrence_fixture_v1",
    "execute_v075_production_occurrence_v1",
    "verify_v075_production_occurrence_authority_result_v1",
]
