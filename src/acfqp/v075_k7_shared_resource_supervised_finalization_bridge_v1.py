"""Structural K7 join from typed supervisor events to outer finalization.

This successor accepts the exact K7 shared-resource identity derivation, one
closed live snapshot, one complete issuer-owned global-supervisor journal, and
one output-byte fixed point.  Every source role, post-cutoff sequence, lifecycle
boolean, and final peak passed to the older outer-finalization mechanism is
derived inside this module from the typed journal documents.

The journal still contains structural source claims rather than independently
replayed operating-system evidence.  Consequently this bridge emits no formal
CounterRecord, WorkVector, ComparisonVector, projection proof, certificate, or
official-execution authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, Mapping, NoReturn

from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_global_supervisor_journal_v1 as journal_v1
from acfqp import construction_shared_resource_live_meter_v1 as live_v1
from acfqp import construction_shared_resource_outer_finalization_v1 as outer_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import v075_k7_root_cap_shared_resource_identity_v1 as identity_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_SHARED_RESOURCE_REBASED_JOURNAL_EVENT_V1_DOMAIN,
    V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN,
    V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN,
    V075_K7_SHARED_RESOURCE_SUPERVISED_SOURCE_ROLE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.93.0"
PROFILE_KEY = "v075_k7_shared_resource_supervised_finalization_bridge_v1"

SUPERVISED_SOURCE_ROLE_V1_DOMAIN = (
    V075_K7_SHARED_RESOURCE_SUPERVISED_SOURCE_ROLE_V1_DOMAIN
)
REBASED_JOURNAL_EVENT_V1_DOMAIN = (
    V075_K7_SHARED_RESOURCE_REBASED_JOURNAL_EVENT_V1_DOMAIN
)
SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN = (
    V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN
)
SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN = (
    V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_SHARED_RESOURCE_SUPERVISED_SOURCE_ROLE_V1_DOMAIN",
    "V075_K7_SHARED_RESOURCE_REBASED_JOURNAL_EVENT_V1_DOMAIN",
    "V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN",
    "V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        SUPERVISED_SOURCE_ROLE_V1_DOMAIN,
        REBASED_JOURNAL_EVENT_V1_DOMAIN,
        SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN,
        SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("supervised-finalization bridge domains are unregistered")


class V075K7SharedResourceSupervisedFinalizationBridgeV1Error(ValueError):
    """One bridge input is crossed, stale, caller-minted, or incomplete."""


class SupervisedOuterSourceRoleV1(str, Enum):
    WINDOW_START_MARKER = "WINDOW_START_MARKER"
    BUSINESS_SOURCE = "BUSINESS_SOURCE"
    BUSINESS_CUTOFF_MARKER = "BUSINESS_CUTOFF_MARKER"
    PROCESS_SUPERVISOR_LAUNCH = "PROCESS_SUPERVISOR_LAUNCH"
    MOUNT_MANIFEST = "MOUNT_MANIFEST"
    PROCESS_REAP = "PROCESS_REAP"
    DESCENDANT_SCAN = "DESCENDANT_SCAN"
    FINAL_CGROUP_PEAK = "FINAL_CGROUP_PEAK"
    PARENT_TERMINAL = "PARENT_TERMINAL"


_ROLE_EVENT_KIND = {
    SupervisedOuterSourceRoleV1.WINDOW_START_MARKER: (
        journal_v1.GlobalSupervisorEventKindV1.WINDOW_START
    ),
    SupervisedOuterSourceRoleV1.BUSINESS_SOURCE: (
        journal_v1.GlobalSupervisorEventKindV1.BUSINESS_CUTOFF
    ),
    SupervisedOuterSourceRoleV1.BUSINESS_CUTOFF_MARKER: (
        journal_v1.GlobalSupervisorEventKindV1.BUSINESS_CUTOFF
    ),
    SupervisedOuterSourceRoleV1.PROCESS_SUPERVISOR_LAUNCH: (
        journal_v1.GlobalSupervisorEventKindV1.WINDOW_START
    ),
    SupervisedOuterSourceRoleV1.MOUNT_MANIFEST: (
        journal_v1.GlobalSupervisorEventKindV1.WINDOW_START
    ),
    SupervisedOuterSourceRoleV1.PROCESS_REAP: (
        journal_v1.GlobalSupervisorEventKindV1.PROCESS_REAP
    ),
    SupervisedOuterSourceRoleV1.DESCENDANT_SCAN: (
        journal_v1.GlobalSupervisorEventKindV1.DESCENDANT_SCAN
    ),
    SupervisedOuterSourceRoleV1.FINAL_CGROUP_PEAK: (
        journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK
    ),
    SupervisedOuterSourceRoleV1.PARENT_TERMINAL: (
        journal_v1.GlobalSupervisorEventKindV1.PARENT_TERMINAL
    ),
}

POST_CUTOFF_EVENT_KINDS = (
    journal_v1.GlobalSupervisorEventKindV1.PROCESS_REAP,
    journal_v1.GlobalSupervisorEventKindV1.DESCENDANT_SCAN,
    journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK,
    journal_v1.GlobalSupervisorEventKindV1.PARENT_TERMINAL,
)

OS_SOURCE_PROVENANCE_VERIFIED = False
SUPERVISOR_EVENT_SEMANTICS_VERIFIED = False
SOURCE_EVIDENCE_SEMANTICS_VERIFIED = False
COUNTER_RECORD_AUTHORIZED = False
WORK_VECTOR_AUTHORIZED = False
COMPARISON_VECTOR_AUTHORIZED = False
ACTUAL_PROJECTION_PROOF_AUTHORIZED = False
FORMAL_VECTOR_AUTHORIZED = False
OFFICIAL_EXECUTION_ALLOWED = False


def _fail(message: str) -> NoReturn:
    raise V075K7SharedResourceSupervisedFinalizationBridgeV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7SharedResourceSupervisedFinalizationBridgeV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAIN_TAGS:
        _fail("supervised-finalization bridge used an undeclared domain")
    return content_id(domain, dict(payload))


def _locks() -> dict[str, bool]:
    return {
        "os_source_provenance_verified": OS_SOURCE_PROVENANCE_VERIFIED,
        "supervisor_event_semantics_verified": (
            SUPERVISOR_EVENT_SEMANTICS_VERIFIED
        ),
        "source_evidence_semantics_verified": (
            SOURCE_EVIDENCE_SEMANTICS_VERIFIED
        ),
        "counter_record_authorized": COUNTER_RECORD_AUTHORIZED,
        "work_vector_authorized": WORK_VECTOR_AUTHORIZED,
        "comparison_vector_authorized": COMPARISON_VECTOR_AUTHORIZED,
        "actual_projection_proof_authorized": (
            ACTUAL_PROJECTION_PROOF_AUTHORIZED
        ),
        "formal_vector_authorized": FORMAL_VECTOR_AUTHORIZED,
        "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
    }


def derive_supervised_outer_source_role_id_v1(
    *,
    event: journal_v1.GlobalSupervisorEventV1,
    role: SupervisedOuterSourceRoleV1,
) -> str:
    """Derive a role-separated source ID from one complete typed event.

    This public helper exists so the live meter can bind its pre-cutoff source
    events to the same journal records before the final bridge is constructed.
    The final bridge accepts none of these IDs from its caller and derives all
    nine again from the frozen journal.
    """

    if type(event) is not journal_v1.GlobalSupervisorEventV1:
        _fail("source-role derivation requires one exact journal event")
    try:
        role = SupervisedOuterSourceRoleV1(role)
    except (TypeError, ValueError) as error:
        raise V075K7SharedResourceSupervisedFinalizationBridgeV1Error(
            "source-role derivation received an unknown role"
        ) from error
    if event.kind is not _ROLE_EVENT_KIND[role]:
        _fail("source role crossed its required typed journal event")
    payload = {
        "schema": "acfqp.v075_k7_supervised_outer_source_role.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_role": role.value,
        "required_event_kind": _ROLE_EVENT_KIND[role].value,
        "global_supervisor_event_id": event.event_id,
        "source_document_id": event.source_document.source_document_id,
        "typed_event_document": event.to_document(),
        "role_identity_derived_from_typed_event_document": True,
        "caller_source_id_accepted": False,
        "structural_source_claim_only": True,
        "formal_locks": _locks(),
    }
    return _content_id(SUPERVISED_SOURCE_ROLE_V1_DOMAIN, payload)


def _event_by_kind(
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
    kind: journal_v1.GlobalSupervisorEventKindV1,
) -> journal_v1.GlobalSupervisorEventV1:
    matches = tuple(event for event in journal.events if event.kind is kind)
    if len(matches) != 1:
        _fail("frozen journal lacks one exact typed lifecycle event")
    return matches[0]


def _source_role_ids(
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
) -> dict[SupervisedOuterSourceRoleV1, str]:
    return {
        role: derive_supervised_outer_source_role_id_v1(
            event=_event_by_kind(journal, required_kind), role=role
        )
        for role, required_kind in _ROLE_EVENT_KIND.items()
    }


_REBASED_ISSUER = object()


@dataclass(frozen=True, slots=True)
class RebasedPostCutoffJournalEventV1:
    """One journal-local post-cutoff event rebased to the live cutoff."""

    _issuer: InitVar[object]
    journal_id: str
    live_snapshot_id: str
    event_id: str
    source_document_id: str
    event_kind: journal_v1.GlobalSupervisorEventKindV1
    journal_cutoff_sequence: int
    journal_local_sequence: int
    live_cutoff_sequence: int
    rebased_global_sequence: int

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REBASED_ISSUER:
            _fail("rebased journal events are bridge-issued only")
        for value, label in (
            (self.journal_id, "rebased journal"),
            (self.live_snapshot_id, "rebased live snapshot"),
            (self.event_id, "rebased event"),
            (self.source_document_id, "rebased source document"),
        ):
            _cid(value, label)
        try:
            kind = journal_v1.GlobalSupervisorEventKindV1(self.event_kind)
        except (TypeError, ValueError) as error:
            raise V075K7SharedResourceSupervisedFinalizationBridgeV1Error(
                "rebased event kind is unknown"
            ) from error
        object.__setattr__(self, "event_kind", kind)
        if kind not in POST_CUTOFF_EVENT_KINDS:
            _fail("only post-cutoff lifecycle events may be rebased")
        for value, label in (
            (self.journal_cutoff_sequence, "journal cutoff sequence"),
            (self.journal_local_sequence, "journal local sequence"),
            (self.live_cutoff_sequence, "live cutoff sequence"),
            (self.rebased_global_sequence, "rebased global sequence"),
        ):
            if type(value) is not int or value < 0:
                _fail(f"{label} must be a nonnegative exact integer")
        expected = self.live_cutoff_sequence + (
            self.journal_local_sequence - self.journal_cutoff_sequence
        )
        if (
            self.journal_local_sequence <= self.journal_cutoff_sequence
            or self.rebased_global_sequence != expected
            or self.rebased_global_sequence <= self.live_cutoff_sequence
        ):
            _fail("post-cutoff event was not deterministically rebased")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_rebased_post_cutoff_journal_event.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "global_supervisor_event_journal_id": self.journal_id,
            "live_measurement_snapshot_id": self.live_snapshot_id,
            "global_supervisor_event_id": self.event_id,
            "source_document_id": self.source_document_id,
            "event_kind": self.event_kind.value,
            "journal_cutoff_sequence": self.journal_cutoff_sequence,
            "journal_local_sequence": self.journal_local_sequence,
            "live_cutoff_sequence": self.live_cutoff_sequence,
            "rebased_global_sequence": self.rebased_global_sequence,
            "rebase_formula": (
                "live_cutoff + (journal_local - journal_cutoff)"
            ),
            "sequence_supplied_by_caller": False,
            "journal_event_order_preserved": True,
            "formal_locks": _locks(),
        }

    @property
    def rebase_id(self) -> str:
        return _content_id(REBASED_JOURNAL_EVENT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "rebased_journal_event_id": self.rebase_id}


def _rebase_post_cutoff_events(
    *,
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
) -> tuple[RebasedPostCutoffJournalEventV1, ...]:
    cutoff = _event_by_kind(
        journal, journal_v1.GlobalSupervisorEventKindV1.BUSINESS_CUTOFF
    )
    return tuple(
        RebasedPostCutoffJournalEventV1(
            _REBASED_ISSUER,
            journal.journal_id,
            snapshot.snapshot_id,
            event.event_id,
            event.source_document.source_document_id,
            event.kind,
            cutoff.sequence,
            event.sequence,
            snapshot.window.cutoff_sequence,
            snapshot.window.cutoff_sequence + (event.sequence - cutoff.sequence),
        )
        for event in journal.events
        if event.kind in POST_CUTOFF_EVENT_KINDS
    )


def _validate_inputs(
    *,
    identity_derivation: (
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ),
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
) -> None:
    if (
        type(identity_derivation)
        is not identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ):
        _fail("bridge requires the exact K7 shared-resource identity derivation")
    if type(snapshot) is not live_v1.SharedResourceMeasurementSnapshotV1:
        _fail("bridge requires one exact live measurement snapshot")
    if type(journal) is not journal_v1.FrozenGlobalSupervisorEventJournalV1:
        _fail("bridge requires one exact frozen supervisor journal")
    if type(fixed_point) is not fixed_v1.OutputBytesFixedPointResultV1:
        _fail("bridge requires one exact output-byte fixed point")
    try:
        identity_derivation._assert_current()  # noqa: SLF001
        live_v1.replay_live_measurement_snapshot_structure_v1(snapshot)
        # The journal owns cached issuance IDs.  Never re-run __post_init__:
        # doing so after hostile mutation could refresh those caches.  Its
        # public render path performs the fail-closed freshness check.
        journal.to_document()
    except Exception as error:
        raise V075K7SharedResourceSupervisedFinalizationBridgeV1Error(
            "bridge input failed its upstream structural replay"
        ) from error

    binding = identity_derivation.identity_binding
    route_identity_id = identity_derivation.route_identity.route_identity_id
    scope = journal.scope
    if (
        scope.measurement_identity_binding_id != binding.identity_binding_id
        or scope.execution_profile_id != binding.execution_profile_id
    ):
        _fail("supervisor scope crossed the route-derived measurement identity")
    if (
        snapshot.identity_binding_id != binding.identity_binding_id
        or snapshot.window.identity_binding_id != binding.identity_binding_id
        or snapshot.window.window_key != scope.window_key
    ):
        _fail("live snapshot binding/window crossed the supervisor scope")
    roles = _source_role_ids(journal)
    if snapshot.window.start_marker_id != roles[
        SupervisedOuterSourceRoleV1.WINDOW_START_MARKER
    ]:
        _fail("live window start marker differs from the typed journal start")
    if snapshot.window.cutoff_marker_id != roles[
        SupervisedOuterSourceRoleV1.BUSINESS_CUTOFF_MARKER
    ]:
        _fail("live cutoff marker differs from the typed journal cutoff")
    if fixed_point.profile.execution_identity_id != route_identity_id:
        _fail("output fixed point crossed the exact K7 route identity")

    process_sources = tuple(
        event.source_evidence_id
        for event in snapshot.events
        if event.path == "process.launches"
        and event.charged
        and event.source_kind
        is live_v1.LiveSourceEvidenceKindV1.PROCESS_SUPERVISOR_LAUNCH
    )
    mount_sources = tuple(
        event.source_evidence_id
        for event in snapshot.events
        if event.path == "io.mounted_bytes_peak"
        and event.charged
        and event.source_kind
        is live_v1.LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST
    )
    if process_sources != (
        roles[SupervisedOuterSourceRoleV1.PROCESS_SUPERVISOR_LAUNCH],
    ):
        _fail("live process-launch source is not journal-derived")
    if roles[SupervisedOuterSourceRoleV1.MOUNT_MANIFEST] not in mount_sources:
        _fail("live mount-manifest source is not journal-derived")

    peak_event = _event_by_kind(
        journal, journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK
    )
    peak_source = peak_event.source_document
    if type(peak_source) is not journal_v1.FinalCgroupPeakSourceDocumentV1:
        _fail("FINAL_CGROUP_PEAK lacks its exact typed source document")
    live_peak_row = next(
        row for row in snapshot.rows if row.path == "memory.working_bytes_peak"
    )
    if (
        live_peak_row.status
        is not receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED
        or type(live_peak_row.value) is not int
        or peak_source.working_bytes_peak < live_peak_row.value
    ):
        _fail("typed FINAL_CGROUP_PEAK is below the live prefix maximum")


_BRIDGE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075K7SharedResourceSupervisedFinalizationBridgeV1:
    """Issuer-owned result of the exact structural five-authority join."""

    _issuer: InitVar[object]
    identity_derivation: (
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ) = field(repr=False, compare=False)
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1 = field(
        repr=False, compare=False
    )
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1 = field(
        repr=False, compare=False
    )
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(
        repr=False, compare=False
    )
    rebased_events: tuple[RebasedPostCutoffJournalEventV1, ...]
    outer_finalization: outer_v1.ParentOwnedSharedResourceFinalizationV1 = field(
        repr=False, compare=False
    )
    _validated_refs: tuple[object, ...] = field(
        init=False, repr=False, compare=False
    )
    _validated_ids: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BRIDGE_ISSUER:
            _fail("supervised-finalization bridge results are issuer-owned")
        self._validate_current_objects()
        object.__setattr__(
            self,
            "_validated_refs",
            (
                self.identity_derivation,
                self.snapshot,
                self.journal,
                self.fixed_point,
                self.outer_finalization,
            ),
        )
        object.__setattr__(
            self,
            "_validated_ids",
            (
                self.identity_derivation.derivation_id,
                self.snapshot.snapshot_id,
                self.journal.journal_id,
                self.fixed_point.result_id,
                self.outer_finalization.finalization_id,
            ),
        )
        self._assert_current()

    def _validate_current_objects(self) -> None:
        _validate_inputs(
            identity_derivation=self.identity_derivation,
            snapshot=self.snapshot,
            journal=self.journal,
            fixed_point=self.fixed_point,
        )
        if (
            type(self.rebased_events) is not tuple
            or tuple(item.event_kind for item in self.rebased_events)
            != POST_CUTOFF_EVENT_KINDS
            or any(
                type(item) is not RebasedPostCutoffJournalEventV1
                for item in self.rebased_events
            )
        ):
            _fail("bridge requires the exact ordered rebased post-cutoff events")
        expected_rebased = _rebase_post_cutoff_events(
            journal=self.journal, snapshot=self.snapshot
        )
        if tuple(item.rebase_id for item in self.rebased_events) != tuple(
            item.rebase_id for item in expected_rebased
        ):
            _fail("rebased post-cutoff event sequence differs from journal replay")
        if (
            type(self.outer_finalization)
            is not outer_v1.ParentOwnedSharedResourceFinalizationV1
        ):
            _fail("bridge requires one internally issued outer finalization")
        outer_v1.replay_parent_owned_shared_resource_finalization_v1(
            self.outer_finalization
        )

    def _assert_current(self) -> None:
        if hasattr(self, "_validated_refs") and (
            self._validated_refs
            != (
                self.identity_derivation,
                self.snapshot,
                self.journal,
                self.fixed_point,
                self.outer_finalization,
            )
            or any(
                current is not validated
                for current, validated in zip(
                    (
                        self.identity_derivation,
                        self.snapshot,
                        self.journal,
                        self.fixed_point,
                        self.outer_finalization,
                    ),
                    self._validated_refs,
                    strict=True,
                )
            )
        ):
            _fail("one bridge authority object was replaced")
        self._validate_current_objects()
        if hasattr(self, "_validated_ids") and self._validated_ids != (
            self.identity_derivation.derivation_id,
            self.snapshot.snapshot_id,
            self.journal.journal_id,
            self.fixed_point.result_id,
            self.outer_finalization.finalization_id,
        ):
            _fail("one bridge authority changed after issuance")

    def _payload(self) -> dict[str, Any]:
        binding = self.identity_derivation.identity_binding
        peak_event = _event_by_kind(
            self.journal,
            journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK,
        )
        peak_source = peak_event.source_document
        assert type(peak_source) is journal_v1.FinalCgroupPeakSourceDocumentV1
        roles = _source_role_ids(self.journal)
        return {
            "schema": (
                "acfqp.v075_k7_shared_resource_supervised_finalization_bridge.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_derivation_id": self.identity_derivation.derivation_id,
            "route_identity_id": (
                self.identity_derivation.route_identity.route_identity_id
            ),
            "shared_resource_identity_binding_id": binding.identity_binding_id,
            "execution_profile_id": binding.execution_profile_id,
            "live_measurement_snapshot_id": self.snapshot.snapshot_id,
            "global_supervisor_event_journal_id": self.journal.journal_id,
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "shared_resource_outer_finalization_id": (
                self.outer_finalization.finalization_id
            ),
            "derived_outer_source_roles": {
                role.value: roles[role]
                for role in SupervisedOuterSourceRoleV1
            },
            "rebased_post_cutoff_event_ids": [
                item.rebase_id for item in self.rebased_events
            ],
            "live_cutoff_sequence": self.snapshot.window.cutoff_sequence,
            "rebased_post_cutoff_sequences": [
                item.rebased_global_sequence for item in self.rebased_events
            ],
            "final_working_bytes_peak": peak_source.working_bytes_peak,
            "identity_scope_joined_exactly": True,
            "snapshot_window_joined_to_journal_scope": True,
            "journal_local_order_rebased_deterministically": True,
            "outer_source_ids_derived_internally": True,
            "caller_supplied_outer_source_ids": [],
            "caller_supplied_post_cutoff_sequences": [],
            "caller_supplied_lifecycle_bools": [],
            "caller_supplied_final_peak": False,
            "final_peak_derived_from_typed_final_cgroup_source": True,
            "final_peak_covers_live_prefix": True,
            "existing_outer_envelope_called_internally": True,
            "existing_outer_finalizer_called_internally": True,
            "hidden_signer_git_subprocess_eliminated": False,
            "hidden_signer_git_subprocess_blocker": (
                "SIGNER_GIT_SUBPROCESS_ELIMINATION_NOT_VERIFIED"
            ),
            "structural_bridge_only": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "actual_projection_proof_issued": False,
            "certificate_issued": False,
            "formal_locks": _locks(),
        }

    @property
    def bridge_id(self) -> str:
        self._assert_current()
        return _content_id(
            SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "supervised_finalization_bridge_id": self.bridge_id}


def finalize_v075_k7_supervised_shared_resources_v1(
    *,
    identity_derivation: (
        identity_v1.V075K7RootCapSharedResourceIdentityDerivationV1
    ),
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    journal: journal_v1.FrozenGlobalSupervisorEventJournalV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
) -> V075K7SharedResourceSupervisedFinalizationBridgeV1:
    """Derive the entire outer-finalizer argument set from typed authorities."""

    _validate_inputs(
        identity_derivation=identity_derivation,
        snapshot=snapshot,
        journal=journal,
        fixed_point=fixed_point,
    )
    binding = identity_derivation.identity_binding
    roles = _source_role_ids(journal)
    rebased = _rebase_post_cutoff_events(journal=journal, snapshot=snapshot)
    by_kind = {item.event_kind: item for item in rebased}

    reap_event = _event_by_kind(
        journal, journal_v1.GlobalSupervisorEventKindV1.PROCESS_REAP
    )
    scan_event = _event_by_kind(
        journal, journal_v1.GlobalSupervisorEventKindV1.DESCENDANT_SCAN
    )
    peak_event = _event_by_kind(
        journal, journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK
    )
    reap_source = reap_event.source_document
    scan_source = scan_event.source_document
    peak_source = peak_event.source_document
    assert type(reap_source) is journal_v1.ProcessReapSourceDocumentV1
    assert type(scan_source) is journal_v1.DescendantScanSourceDocumentV1
    assert type(peak_source) is journal_v1.FinalCgroupPeakSourceDocumentV1

    envelope = outer_v1.issue_post_cutoff_supervisor_envelope_v1(
        snapshot=snapshot,
        identity_binding=binding,
        route_identity_id=identity_derivation.route_identity.route_identity_id,
        parent_global_terminal_source_id=roles[
            SupervisedOuterSourceRoleV1.PARENT_TERMINAL
        ],
        child_reap_source_id=roles[SupervisedOuterSourceRoleV1.PROCESS_REAP],
        descendant_scan_source_id=roles[
            SupervisedOuterSourceRoleV1.DESCENDANT_SCAN
        ],
        final_cgroup_peak_source_id=roles[
            SupervisedOuterSourceRoleV1.FINAL_CGROUP_PEAK
        ],
        child_reap_sequence=by_kind[
            journal_v1.GlobalSupervisorEventKindV1.PROCESS_REAP
        ].rebased_global_sequence,
        descendant_scan_sequence=by_kind[
            journal_v1.GlobalSupervisorEventKindV1.DESCENDANT_SCAN
        ].rebased_global_sequence,
        final_cgroup_peak_sequence=by_kind[
            journal_v1.GlobalSupervisorEventKindV1.FINAL_CGROUP_PEAK
        ].rebased_global_sequence,
        parent_global_terminal_sequence=by_kind[
            journal_v1.GlobalSupervisorEventKindV1.PARENT_TERMINAL
        ].rebased_global_sequence,
        final_working_bytes_peak=peak_source.working_bytes_peak,
        child_reaped=reap_source.reap_complete,
        no_descendants=(
            scan_source.scan_complete and scan_source.descendant_count == 0
        ),
    )
    outer = outer_v1.finalize_parent_owned_shared_resources_v1(
        snapshot=snapshot,
        identity_binding=binding,
        fixed_point=fixed_point,
        route_identity_id=identity_derivation.route_identity.route_identity_id,
        business_source_id=roles[SupervisedOuterSourceRoleV1.BUSINESS_SOURCE],
        cutoff_source_id=roles[
            SupervisedOuterSourceRoleV1.BUSINESS_CUTOFF_MARKER
        ],
        process_supervisor_source_id=roles[
            SupervisedOuterSourceRoleV1.PROCESS_SUPERVISOR_LAUNCH
        ],
        mount_manifest_source_id=roles[
            SupervisedOuterSourceRoleV1.MOUNT_MANIFEST
        ],
        post_cutoff_envelope=envelope,
    )
    return V075K7SharedResourceSupervisedFinalizationBridgeV1(
        _BRIDGE_ISSUER,
        identity_derivation,
        snapshot,
        journal,
        fixed_point,
        rebased,
        outer,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075K7SharedResourceSupervisedFinalizationVerificationV1:
    _issuer: InitVar[object]
    bridge: V075K7SharedResourceSupervisedFinalizationBridgeV1 = field(
        repr=False, compare=False
    )
    _validated_bridge: V075K7SharedResourceSupervisedFinalizationBridgeV1 = field(
        init=False, repr=False, compare=False
    )
    _bridge_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("supervised-finalization verification is issuer-owned")
        if type(self.bridge) is not V075K7SharedResourceSupervisedFinalizationBridgeV1:
            _fail("verification requires one exact supervised bridge")
        self.bridge._assert_current()
        object.__setattr__(self, "_validated_bridge", self.bridge)
        object.__setattr__(self, "_bridge_id", self.bridge.bridge_id)

    def _assert_current(self) -> None:
        if self.bridge is not self._validated_bridge:
            _fail("verified supervised-finalization bridge object was replaced")
        self.bridge._assert_current()
        if self.bridge.bridge_id != self._bridge_id:
            _fail("verified supervised-finalization bridge changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_k7_shared_resource_supervised_finalization_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "supervised_finalization_bridge_id": self._bridge_id,
            "verification_result": "STRUCTURAL_PASS",
            "identity_window_journal_fixed_point_join_replayed": True,
            "semantic_source_verification_performed": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "actual_projection_proof_issued": False,
            "formal_locks": _locks(),
        }

    @property
    def verification_id(self) -> str:
        self._assert_current()
        return _content_id(
            SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "supervised_finalization_verification_id": self.verification_id,
        }


def verify_v075_k7_supervised_shared_resource_finalization_v1(
    bridge: V075K7SharedResourceSupervisedFinalizationBridgeV1,
) -> V075K7SharedResourceSupervisedFinalizationVerificationV1:
    return V075K7SharedResourceSupervisedFinalizationVerificationV1(
        _VERIFICATION_ISSUER, bridge
    )


__all__ = [
    "ACTUAL_PROJECTION_PROOF_AUTHORIZED",
    "COMPARISON_VECTOR_AUTHORIZED",
    "COUNTER_RECORD_AUTHORIZED",
    "FORMAL_VECTOR_AUTHORIZED",
    "LOCAL_DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OS_SOURCE_PROVENANCE_VERIFIED",
    "POST_CUTOFF_EVENT_KINDS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "RebasedPostCutoffJournalEventV1",
    "SOURCE_EVIDENCE_SEMANTICS_VERIFIED",
    "SUPERVISOR_EVENT_SEMANTICS_VERIFIED",
    "SupervisedOuterSourceRoleV1",
    "V075K7SharedResourceSupervisedFinalizationBridgeV1",
    "V075K7SharedResourceSupervisedFinalizationBridgeV1Error",
    "V075K7SharedResourceSupervisedFinalizationVerificationV1",
    "WORK_VECTOR_AUTHORIZED",
    "derive_supervised_outer_source_role_id_v1",
    "finalize_v075_k7_supervised_shared_resources_v1",
    "verify_v075_k7_supervised_shared_resource_finalization_v1",
]
