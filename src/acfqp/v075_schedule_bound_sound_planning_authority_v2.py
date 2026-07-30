"""Schedule-bound construction planning authority for V0-075.

This bridge closes one deliberately narrow gap.  It first replays the complete
five-arm initial-acquisition terminal from its repository and construction
authority witnesses.  For an adaptive occurrence it then invokes the generic
aggregate compiler, but sends only the resulting numerical model to the
prior-free numerical planner.  The occurrence wrapper binds that proof back to
the exact profile, slot, schedule, lineage, lifecycle, and proposal.

The direct arm has only root discovery at this stage.  It therefore emits a
typed deferral before child expansion and does not manufacture a model,
validation evidence, or numerical proof.

Every outcome in this module is construction-only and noncertifying.  A
numerical candidate means only that an independent total lift is still
required.  Production execution remains unconditionally locked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_preopen_target_authorization_v2 as preopen_v2
from acfqp import v075_schedule_bound_acquisition_lifecycle_v2 as initial_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.50.0"
PROFILE_KEY = "v075_schedule_bound_sound_planning_authority_v2"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
PRIVATE_LAW_ACCESS_ALLOWED = False
PER_DRAW_REPLAY_ALLOWED = False
TARGET_ACCESS_ALLOWED = False

TERMINAL_SCOPE = "CONSTRUCTION_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "schedule-bound initial planning is construction-only; dynamic "
    "acquisition closure, independent total lift, isolated IPC, and "
    "production occurrence authority are not integrated"
)

DOMAIN_TAGS = {
    "result": "acfqp:v075-schedule-bound-sound-planning-result:v2",
    "verification": (
        "acfqp:v075-schedule-bound-sound-planning-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 schedule-bound planning domains must be unique")


class V075ScheduleBoundSoundPlanningV2InvariantViolation(ValueError):
    """An upstream witness, compiler result, proof, or wrapper was invalid."""


class V075ScheduleBoundSoundPlanningProductionV2NotReady(RuntimeError):
    """The construction bridge cannot authorize production execution."""


def _fail(message: str) -> NoReturn:
    raise V075ScheduleBoundSoundPlanningV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ScheduleBoundSoundPlanningV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ScheduleBoundSoundPlanningV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ScheduleBoundSoundPlanningV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


class V075ScheduleBoundPlanningTerminalCodeV2(str, Enum):
    CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT = (
        "CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT"
    )
    FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION = (
        "FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION"
    )
    PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION = (
        "PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION"
    )


_RESULT_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ScheduleBoundSoundPlanningResultV2:
    """Occurrence-bound wrapper around one prior-free numerical proof."""

    _issuer: object = field(repr=False, compare=False)
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ) = field(repr=False)
    compiler_output: planning_v2.V075ConstructionPlanningInputV2 | None = field(
        repr=False
    )
    numerical_proof: planning_v2.V075NumericalPlanningProofV2 | None = field(
        repr=False
    )
    terminal_code: V075ScheduleBoundPlanningTerminalCodeV2
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.initial_lifecycle)
            is not initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
            or type(self.terminal_code)
            is not V075ScheduleBoundPlanningTerminalCodeV2
        ):
            _fail("schedule-bound planning result is caller-minted")
        schedule = self.initial_lifecycle.schedule
        direct = schedule.occurrence.arm is acquisition_v2.DIRECT_ARM
        if direct:
            if (
                self.initial_lifecycle.terminal_code
                is not (
                    initial_v2.V075InitialAcquisitionTerminalCodeV2
                    .ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION
                )
                or self.compiler_output is not None
                or self.numerical_proof is not None
                or self.terminal_code
                is not (
                    V075ScheduleBoundPlanningTerminalCodeV2
                    .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
                )
                or schedule.proposal_view is not None
                or type(self.initial_lifecycle.current_lifecycle)
                is not initial_v2.V075InitialLifecycleNotApplicableV2
            ):
                _fail("direct initial planning invented post-discovery work")
        else:
            if (
                self.initial_lifecycle.terminal_code
                is not (
                    initial_v2.V075InitialAcquisitionTerminalCodeV2
                    .INITIAL_COMPLETE_AWAITING_SOUND_PLANNER
                )
                or type(self.initial_lifecycle.current_lifecycle)
                is not lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
                or type(self.compiler_output)
                is not planning_v2.V075ConstructionPlanningInputV2
                or type(self.numerical_proof)
                is not planning_v2.V075NumericalPlanningProofV2
                or schedule.proposal_view is None
            ):
                _fail("adaptive schedule-bound planning is incomplete")
            assert self.compiler_output is not None
            assert self.numerical_proof is not None
            expected_code = (
                (
                    V075ScheduleBoundPlanningTerminalCodeV2
                    .CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT
                )
                if self.numerical_proof.outcome
                is planning_v2.V075NumericalOutcomeV2.CANDIDATE
                else (
                    V075ScheduleBoundPlanningTerminalCodeV2
                    .FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION
                )
            )
            if (
                self.terminal_code is not expected_code
                or self.compiler_output.schedule_id != schedule.schedule_id
                or self.compiler_output.lineage_id
                != self.initial_lifecycle.lineage.lineage_id
                or self.compiler_output.lifecycle_closure_id
                != self.initial_lifecycle.current_lifecycle.closure_id
                or self.compiler_output.occurrence_id
                != schedule.occurrence.occurrence_id
                or self.compiler_output.target_tape_namespace_id
                != schedule.occurrence.target_tape_namespace_id
                or self.compiler_output.arm is not schedule.occurrence.arm
                or self.compiler_output.route
                is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
                or self.numerical_proof.model
                != self.compiler_output.model
                or self.numerical_proof.route
                is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            ):
                _fail("adaptive numerical proof or occurrence binding changed")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    @property
    def proposal_view_id(self) -> str | None:
        proposal = self.initial_lifecycle.schedule.proposal_view
        return None if proposal is None else proposal.proposal_view_id

    def _payload(self) -> dict[str, Any]:
        lifecycle = self.initial_lifecycle
        schedule = lifecycle.schedule
        proof = self.numerical_proof
        compiler = self.compiler_output
        direct = schedule.occurrence.arm is acquisition_v2.DIRECT_ARM
        candidate = (
            proof is not None
            and proof.outcome is planning_v2.V075NumericalOutcomeV2.CANDIDATE
        )
        failed = (
            proof is not None
            and proof.outcome
            is planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        )
        return {
            "schema": "acfqp.v075_schedule_bound_sound_planning_result.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": self.terminal_code.value,
            "initial_lifecycle_id": lifecycle.result_id,
            "acquisition_profile_id": lifecycle.profile.profile_id,
            "occurrence_slot_id": lifecycle.expected_slot.slot_id,
            "schedule_id": schedule.schedule_id,
            "lineage_id": lifecycle.lineage.lineage_id,
            "construction_authority_replay_id": (
                lifecycle.authority_replay.replay_id
            ),
            "current_lifecycle_id": (
                lifecycle.current_lifecycle.witness_id
                if direct
                else lifecycle.current_lifecycle.closure_id
            ),
            "occurrence_id": schedule.occurrence.occurrence_id,
            "target_tape_namespace_id": (
                schedule.occurrence.target_tape_namespace_id
            ),
            "context_id": schedule.occurrence.context_id,
            "arm": schedule.occurrence.arm.value,
            "route": (
                planning_v2.V075PlanningRouteV2.MATCHED_DIRECT_GROUND.value
                if direct
                else planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT.value
            ),
            "proposal_view_id": self.proposal_view_id,
            "proposal_bound_in_occurrence_wrapper": not direct,
            "compiler_output_id": (
                None if compiler is None else compiler.input_id
            ),
            "numerical_model_id": (
                None if compiler is None else compiler.model.model_id
            ),
            "numerical_proof_id": (
                None if proof is None else proof.proof_id
            ),
            "failed_frontier_id": (
                None
                if proof is None or proof.failed_frontier is None
                else proof.failed_frontier.frontier_id
            ),
            "numerical_proof_prior_free": not direct,
            "numerical_proof_contains_occurrence_identity": False,
            "numerical_proof_contains_arm_identity": False,
            "numerical_proof_contains_proposal_identity": False,
            "numerical_proof_contains_source_identity": False,
            "generic_compiler_schedule_boundary_superseded_by_exact_wrapper": (
                not direct
            ),
            "initial_schedule_bound": True,
            "child_expansion_complete": False,
            "dynamic_acquisition_complete": False,
            "planning_executed": not direct,
            "planning_deferred": direct,
            "candidate_awaiting_independent_total_lift": candidate,
            "failed_frontier_for_future_acquisition": failed,
            "candidate_is_not_certificate": candidate,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "per_draw_records_read": 0,
            "private_law_access": False,
            "target_accessed": False,
            "kernel_calls": 0,
            "j0_calls": 0,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "initial_lifecycle": self.initial_lifecycle.to_document(),
            "compiler_output": (
                None
                if self.compiler_output is None
                else self.compiler_output.to_document()
            ),
            "numerical_proof": (
                None
                if self.numerical_proof is None
                else self.numerical_proof.to_document()
            ),
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class V075ScheduleBoundSoundPlanningVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    result_id: str
    initial_lifecycle_id: str
    numerical_proof_id: str | None
    terminal_code: V075ScheduleBoundPlanningTerminalCodeV2
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.result_id, "verified schedule-bound planning result")
        _cid(self.initial_lifecycle_id, "verified initial lifecycle")
        if self.numerical_proof_id is not None:
            _cid(self.numerical_proof_id, "verified numerical proof")
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.terminal_code)
            is not V075ScheduleBoundPlanningTerminalCodeV2
            or (
                self.terminal_code
                is (
                    V075ScheduleBoundPlanningTerminalCodeV2
                    .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
                )
            )
            != (self.numerical_proof_id is None)
        ):
            _fail("schedule-bound planning verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_schedule_bound_sound_planning_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "initial_lifecycle_id": self.initial_lifecycle_id,
            "numerical_proof_id": self.numerical_proof_id,
            "terminal_code": self.terminal_code.value,
            "repository_schedule_replayed": True,
            "construction_authority_replayed": True,
            "initial_lifecycle_replayed": True,
            "generic_aggregate_compiler_replayed": (
                self.numerical_proof_id is not None
            ),
            "prior_free_numerical_planner_replayed": (
                self.numerical_proof_id is not None
            ),
            "canonical_result_bytes_replayed": True,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _replay_initial_lifecycle(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    claimed: initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2,
) -> initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2:
    if type(claimed) is not (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ):
        _fail("initial acquisition lifecycle claim is not one exact type")
    try:
        return (
            initial_v2
            .verify_v075_schedule_bound_initial_acquisition_lifecycle_bytes_v2(
                repository_root=repository_root,
                profile=profile,
                expected_slot=expected_slot,
                schedule=schedule,
                lineage=lineage,
                construction_authority=construction_authority,
                current_lifecycle=current_lifecycle,
                raw=claimed.canonical_bytes,
            )
        )
    except Exception as error:
        if type(error) is V075ScheduleBoundSoundPlanningV2InvariantViolation:
            raise
        raise V075ScheduleBoundSoundPlanningV2InvariantViolation(
            "exact schedule-bound initial lifecycle replay failed"
        ) from error


def freeze_v075_schedule_bound_sound_planning_authority_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ),
) -> V075ScheduleBoundSoundPlanningResultV2:
    """Replay initial acquisition and freeze one noncertifying planning leaf."""

    replayed = _replay_initial_lifecycle(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
        claimed=initial_lifecycle,
    )
    if replayed.schedule.occurrence.arm is acquisition_v2.DIRECT_ARM:
        return V075ScheduleBoundSoundPlanningResultV2(
            _RESULT_ISSUER,
            replayed,
            None,
            None,
            (
                V075ScheduleBoundPlanningTerminalCodeV2
                .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
            ),
        )
    if type(replayed.current_lifecycle) is not (
        lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
    ):
        _fail("adaptive initial lifecycle lacks its aggregate closure")
    try:
        compiler_output = (
            planning_v2.compile_v075_construction_planning_input_v2(
                repository_root=repository_root,
                schedule=replayed.schedule,
                lineage=replayed.lineage,
                lifecycle=replayed.current_lifecycle,
            )
        )
        numerical_proof = (
            planning_v2.plan_v075_construction_numerical_model_v2(
                model=compiler_output.model,
                route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
            )
        )
    except Exception as error:
        if type(error) is V075ScheduleBoundSoundPlanningV2InvariantViolation:
            raise
        raise V075ScheduleBoundSoundPlanningV2InvariantViolation(
            "aggregate compiler or prior-free numerical planner failed"
        ) from error
    terminal = (
        (
            V075ScheduleBoundPlanningTerminalCodeV2
            .CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT
        )
        if numerical_proof.outcome
        is planning_v2.V075NumericalOutcomeV2.CANDIDATE
        else (
            V075ScheduleBoundPlanningTerminalCodeV2
            .FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION
        )
    )
    return V075ScheduleBoundSoundPlanningResultV2(
        _RESULT_ISSUER,
        replayed,
        compiler_output,
        numerical_proof,
        terminal,
    )


def verify_v075_schedule_bound_sound_planning_result_bytes_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: initial_v2.LifecycleWitnessV2,
    initial_lifecycle: (
        initial_v2.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ),
    claimed_bytes: bytes,
) -> tuple[
    V075ScheduleBoundSoundPlanningResultV2,
    V075ScheduleBoundSoundPlanningVerificationV2,
]:
    """Rebuild every upstream witness, compiler object, proof, and byte."""

    document = _strict_document(
        claimed_bytes,
        "schedule-bound sound planning result",
    )
    expected = freeze_v075_schedule_bound_sound_planning_authority_v2(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
        initial_lifecycle=initial_lifecycle,
    )
    if (
        set(document) != set(expected.to_document())
        or claimed_bytes != expected.canonical_bytes
    ):
        _fail("schedule-bound planning result differs from exact byte replay")
    proof_id = (
        None
        if expected.numerical_proof is None
        else expected.numerical_proof.proof_id
    )
    return (
        expected,
        V075ScheduleBoundSoundPlanningVerificationV2(
            _VERIFICATION_ISSUER,
            expected.result_id,
            expected.initial_lifecycle.result_id,
            proof_id,
            expected.terminal_code,
        ),
    )


def open_v075_production_schedule_bound_sound_planning_authority_v2(
    *_args: Any,
    **_kwargs: Any,
) -> NoReturn:
    """Remain structurally locked regardless of monkeypatched constants."""

    raise V075ScheduleBoundSoundPlanningProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "DOMAIN_TAGS",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_REPLAY_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PRIVATE_LAW_ACCESS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_BLOCKER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TARGET_ACCESS_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075ScheduleBoundPlanningTerminalCodeV2",
    "V075ScheduleBoundSoundPlanningProductionV2NotReady",
    "V075ScheduleBoundSoundPlanningResultV2",
    "V075ScheduleBoundSoundPlanningV2InvariantViolation",
    "V075ScheduleBoundSoundPlanningVerificationV2",
    "freeze_v075_schedule_bound_sound_planning_authority_v2",
    "open_v075_production_schedule_bound_sound_planning_authority_v2",
    "verify_v075_schedule_bound_sound_planning_result_bytes_v2",
]
