"""Parent-owned structural finalization of the nine shared resources.

The live meter deliberately leaves ``io.output_bytes`` unavailable because
the immutable result/counter/vector/manifest suffix does not exist at its
operational cutoff.  The output fixed-point mechanism renders that complete
suffix in memory.  This module joins those two structural objects only after
the parent supervisor has reached a later global terminal sequence, reaped the
child, and observed no descendants.

The fixed-point total contains the eight provisional operational output roles,
but not this later parent finalization wrapper.  No operational artifact byte
may be committed before a future joint renderer covers that complete parent
envelope; child IPC payload traffic belongs to its registered transport/read
boundary instead.
Successful finalization emits
exactly nine ``RECORDED_UNVERIFIED`` raw-source rows.  Source IDs and lifecycle
claims remain structurally bound but semantically unverified, so this module
does not issue a CounterRecord, WorkVector, ComparisonVector, or certificate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import Any, Mapping

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_live_meter_v1 as live_v1
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_OUTER_FINALIZATION_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_OUTER_RAW_SOURCE_ROW_V1_DOMAIN,
    CONSTRUCTION_SHARED_RESOURCE_OUTER_SOURCE_SET_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_shared_resource_outer_finalization_v1"

OUTER_FINALIZATION_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_OUTER_FINALIZATION_V1_DOMAIN
)
OUTER_RAW_SOURCE_ROW_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_OUTER_RAW_SOURCE_ROW_V1_DOMAIN
)
OUTER_SOURCE_SET_V1_DOMAIN = CONSTRUCTION_SHARED_RESOURCE_OUTER_SOURCE_SET_V1_DOMAIN

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    OUTER_FINALIZATION_V1_DOMAIN,
    OUTER_RAW_SOURCE_ROW_V1_DOMAIN,
    OUTER_SOURCE_SET_V1_DOMAIN,
)
LOCAL_DOMAIN_TAGS = frozenset(REQUESTED_PHASE3E_DOMAIN_TAGS)

OUTPUT_PATH = "io.output_bytes"
WORKING_PEAK_PATH = "memory.working_bytes_peak"
OUTPUT_UNAVAILABLE_STATUS = receipts_v1.MeasurementStatusV1.NOT_AVAILABLE
OUTPUT_UNAVAILABLE_REASON = "POST_CUTOFF_ACCOUNTING_SUFFIX_UNMEASURED"
OUTPUT_PREFIX_RELATION = "NO_COMMITTED_OUTPUT_BEFORE_COMPLETE_FIXED_POINT"


class ConstructionSharedResourceOuterFinalizationV1Error(ValueError):
    """The outer finalization identity, lifecycle, or source join is invalid."""


class OuterRawSourceKindV1(str, Enum):
    LIVE_MEASUREMENT_ROW = "LIVE_MEASUREMENT_ROW"
    POST_CUTOFF_SUPERVISOR_ENVELOPE = "POST_CUTOFF_SUPERVISOR_ENVELOPE"
    COMPLETE_OUTPUT_FIXED_POINT = "COMPLETE_OUTPUT_FIXED_POINT"


def _fail(message: str) -> None:
    raise ConstructionSharedResourceOuterFinalizationV1Error(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionSharedResourceOuterFinalizationV1Error(
            f"{field_name} must be one full content ID"
        ) from error


def _content_id(domain_tag: str, payload: Mapping[str, Any]) -> str:
    if domain_tag not in LOCAL_DOMAIN_TAGS:
        _fail("outer finalization used an undeclared content domain")
    return content_id(domain_tag, dict(payload))


def _exact_nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{field_name} must be a nonnegative exact integer")
    return value


def _exact_positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{field_name} must be a positive exact integer")
    return value


def _exact_true(value: Any, field_name: str) -> None:
    if type(value) is not bool or value is not True:
        _fail(f"{field_name} must be exact true")


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceOuterFinalizationV1Error(
            f"unknown {field_name} {value!r}"
        ) from error


_POST_CUTOFF_ENVELOPE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class PostCutoffSupervisorEnvelopeV1:
    """Structural finalizer claim describing a putative post-reap suffix.

    The live snapshot ends before child reap and therefore cannot establish the
    complete-window working-set maximum or the terminal lifecycle.  This exact
    type records a later sequence chain and a distinct final cgroup peak read.
    Its source semantics remain deliberately unverified in V1.
    """

    _issuer: InitVar[object]
    route_identity_id: str
    measurement_identity_binding_id: str
    execution_profile_id: str
    live_snapshot_id: str
    cutoff_source_id: str
    parent_global_terminal_source_id: str
    child_reap_source_id: str
    descendant_scan_source_id: str
    final_cgroup_peak_source_id: str
    cutoff_sequence: int
    child_reap_sequence: int
    descendant_scan_sequence: int
    final_cgroup_peak_sequence: int
    parent_global_terminal_sequence: int
    final_working_bytes_peak: int
    child_reaped: bool
    no_descendants: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _POST_CUTOFF_ENVELOPE_ISSUER:
            _fail("post-cutoff supervisor envelopes are finalizer-issued only")
        identity_ids = tuple(
            _cid(value, label)
            for value, label in (
                (self.route_identity_id, "envelope route identity"),
                (
                    self.measurement_identity_binding_id,
                    "envelope measurement identity binding",
                ),
                (self.execution_profile_id, "envelope execution profile"),
                (self.live_snapshot_id, "envelope live snapshot"),
            )
        )
        evidence_ids = tuple(
            _cid(value, label)
            for value, label in (
                (self.cutoff_source_id, "envelope cutoff source"),
                (
                    self.parent_global_terminal_source_id,
                    "envelope parent global terminal source",
                ),
                (self.child_reap_source_id, "envelope child-reap source"),
                (
                    self.descendant_scan_source_id,
                    "envelope descendant-scan source",
                ),
                (
                    self.final_cgroup_peak_source_id,
                    "envelope final cgroup-peak source",
                ),
            )
        )
        if len(set((*identity_ids, *evidence_ids))) != len(identity_ids) + len(
            evidence_ids
        ):
            _fail("post-cutoff envelope identity/evidence roles must be distinct")
        ordered_sequences = (
            _exact_nonnegative(self.cutoff_sequence, "envelope cutoff sequence"),
            _exact_positive(self.child_reap_sequence, "child-reap sequence"),
            _exact_positive(
                self.descendant_scan_sequence,
                "descendant-scan sequence",
            ),
            _exact_positive(
                self.final_cgroup_peak_sequence,
                "final cgroup-peak sequence",
            ),
            _exact_positive(
                self.parent_global_terminal_sequence,
                "parent global terminal sequence",
            ),
        )
        if ordered_sequences != tuple(sorted(ordered_sequences)) or len(
            set(ordered_sequences)
        ) != len(ordered_sequences):
            _fail(
                "post-cutoff lifecycle sequences must be strictly ordered "
                "cutoff < reap < descendant scan < final peak < terminal"
            )
        _exact_nonnegative(
            self.final_working_bytes_peak,
            "final working-bytes peak",
        )
        _exact_true(self.child_reaped, "child_reaped")
        _exact_true(self.no_descendants, "no_descendants")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_post_cutoff_supervisor_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_identity_id": self.route_identity_id,
            "measurement_identity_binding_id": (
                self.measurement_identity_binding_id
            ),
            "execution_profile_id": self.execution_profile_id,
            "live_measurement_snapshot_id": self.live_snapshot_id,
            "cutoff_source_id": self.cutoff_source_id,
            "parent_global_terminal_source_id": (
                self.parent_global_terminal_source_id
            ),
            "child_reap_source_id": self.child_reap_source_id,
            "descendant_scan_source_id": self.descendant_scan_source_id,
            "final_cgroup_peak_source_id": self.final_cgroup_peak_source_id,
            "cutoff_sequence": self.cutoff_sequence,
            "child_reap_sequence": self.child_reap_sequence,
            "descendant_scan_sequence": self.descendant_scan_sequence,
            "final_cgroup_peak_sequence": self.final_cgroup_peak_sequence,
            "parent_global_terminal_sequence": (
                self.parent_global_terminal_sequence
            ),
            "final_working_bytes_peak": self.final_working_bytes_peak,
            "child_reaped": self.child_reaped,
            "no_descendants": self.no_descendants,
            "issued_after_live_cutoff_claimed_structurally": True,
            "reap_and_descendant_scan_order_claimed_structurally": True,
            "supervisor_provenance_verified": False,
            "global_sequence_semantics_verified": False,
            "pre_cutoff_peak_accepted_as_final_peak": False,
            "source_evidence_semantics_verified": False,
            "numeric_projection_authorized": False,
            "official_execution_allowed": False,
        }


@dataclass(frozen=True, slots=True)
class ParentOwnedOuterSourceSetV1:
    """Typed structural claims for parent source roles and child lifecycle."""

    route_identity_id: str
    measurement_identity_binding_id: str
    execution_profile_id: str
    business_source_id: str
    cutoff_source_id: str
    process_supervisor_source_id: str
    mount_manifest_source_id: str
    post_cutoff_envelope: PostCutoffSupervisorEnvelopeV1 = field(repr=False)

    def __post_init__(self) -> None:
        identity_ids = tuple(
            _cid(value, label)
            for value, label in (
                (self.route_identity_id, "route identity"),
                (
                    self.measurement_identity_binding_id,
                    "measurement identity binding",
                ),
                (self.execution_profile_id, "execution profile"),
            )
        )
        if type(self.post_cutoff_envelope) is not PostCutoffSupervisorEnvelopeV1:
            _fail("outer source set requires one issued post-cutoff envelope")
        envelope = self.post_cutoff_envelope
        source_ids = tuple(
            _cid(value, label)
            for value, label in (
                (self.business_source_id, "business source"),
                (self.cutoff_source_id, "cutoff source"),
                (self.process_supervisor_source_id, "process supervisor source"),
                (self.mount_manifest_source_id, "mount manifest source"),
            )
        )
        envelope_ids = (
            envelope.parent_global_terminal_source_id,
            envelope.child_reap_source_id,
            envelope.descendant_scan_source_id,
            envelope.final_cgroup_peak_source_id,
        )
        all_ids = (*identity_ids, *source_ids, *envelope_ids)
        if len(set(all_ids)) != len(all_ids):
            _fail("outer finalization identity/source roles must be distinct")
        if (
            envelope.route_identity_id != self.route_identity_id
            or envelope.measurement_identity_binding_id
            != self.measurement_identity_binding_id
            or envelope.execution_profile_id != self.execution_profile_id
            or envelope.cutoff_source_id != self.cutoff_source_id
        ):
            _fail("post-cutoff envelope crossed its outer source-set identity")

    @property
    def parent_global_terminal_source_id(self) -> str:
        return self.post_cutoff_envelope.parent_global_terminal_source_id

    @property
    def cgroup_source_id(self) -> str:
        return self.post_cutoff_envelope.final_cgroup_peak_source_id

    @property
    def parent_global_terminal_sequence(self) -> int:
        return self.post_cutoff_envelope.parent_global_terminal_sequence

    @property
    def child_reaped(self) -> bool:
        return self.post_cutoff_envelope.child_reaped

    @property
    def no_descendants(self) -> bool:
        return self.post_cutoff_envelope.no_descendants

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_outer_source_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "route_identity_id": self.route_identity_id,
            "measurement_identity_binding_id": (
                self.measurement_identity_binding_id
            ),
            "execution_profile_id": self.execution_profile_id,
            "business_source_id": self.business_source_id,
            "cutoff_source_id": self.cutoff_source_id,
            "parent_global_terminal_source_id": (
                self.parent_global_terminal_source_id
            ),
            "process_supervisor_source_id": self.process_supervisor_source_id,
            "cgroup_source_id": self.cgroup_source_id,
            "mount_manifest_source_id": self.mount_manifest_source_id,
            "parent_global_terminal_sequence": self.parent_global_terminal_sequence,
            "child_reaped": self.child_reaped,
            "no_descendants": self.no_descendants,
            "post_cutoff_supervisor_envelope": (
                self.post_cutoff_envelope.to_document()
            ),
            "post_cutoff_supervisor_envelope_bound": True,
            "source_roles_parent_owned_claimed_structurally": True,
            "source_roles_parent_owned_semantics_verified": False,
            "post_reap_working_peak_comes_from_live_snapshot": False,
            "child_self_reported_peak_accepted": False,
            "source_evidence_semantics_verified": False,
            "central_domain_registered": True,
        }

    @property
    def source_set_id(self) -> str:
        return _content_id(OUTER_SOURCE_SET_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outer_source_set_id": self.source_set_id}


_ROW_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OuterFinalizedRawSourceRowV1:
    _issuer: InitVar[object]
    source_set_id: str
    live_snapshot_id: str
    fixed_point_result_id: str
    path: str
    reducer: ReducerEnum
    status: receipts_v1.MeasurementStatusV1
    value: int
    source_kind: OuterRawSourceKindV1
    source_row_id: str
    source_evidence_ids: tuple[str, ...]
    output_prefix_bytes: int | None
    output_prefix_relation: str | None
    prefix_added_to_final_value: bool
    complete_fixed_point_total_selected_once_structurally: bool

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("outer raw-source rows are finalizer-issued only")
        for value, label in (
            (self.source_set_id, "row source set"),
            (self.live_snapshot_id, "row live snapshot"),
            (self.fixed_point_result_id, "row fixed-point result"),
            (self.source_row_id, "row source row"),
        ):
            _cid(value, label)
        if self.path not in receipts_v1.SHARED_RESOURCE_PATHS:
            _fail("outer raw-source row uses an unknown shared-resource path")
        reducer = _enum(ReducerEnum, self.reducer, "row reducer")
        status = _enum(
            receipts_v1.MeasurementStatusV1,
            self.status,
            "row measurement status",
        )
        kind = _enum(OuterRawSourceKindV1, self.source_kind, "row source kind")
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "source_kind", kind)
        expected_reducer = (
            ReducerEnum.SUM
            if self.path in receipts_v1.SUM_SHARED_RESOURCE_PATHS
            else ReducerEnum.MAX
        )
        if reducer is not expected_reducer:
            _fail("outer raw-source row changed its V6 reducer")
        if status is not receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED:
            _fail("every finalized raw-source row must be RECORDED_UNVERIFIED")
        _exact_nonnegative(self.value, "raw-source value")
        if (
            type(self.source_evidence_ids) is not tuple
            or not self.source_evidence_ids
            or len(set(self.source_evidence_ids)) != len(self.source_evidence_ids)
        ):
            _fail("raw-source evidence IDs must be one nonempty unique tuple")
        for source_id in self.source_evidence_ids:
            _cid(source_id, "raw-source evidence")
        if type(self.prefix_added_to_final_value) is not bool:
            _fail("prefix_added_to_final_value must be an exact bool")
        if (
            type(self.complete_fixed_point_total_selected_once_structurally)
            is not bool
        ):
            _fail(
                "complete_fixed_point_total_selected_once_structurally "
                "must be an exact bool"
            )

        if self.path == OUTPUT_PATH:
            if (
                kind is not OuterRawSourceKindV1.COMPLETE_OUTPUT_FIXED_POINT
                or self.value <= 0
                or type(self.output_prefix_bytes) is not int
                or self.output_prefix_bytes != 0
                or self.output_prefix_relation != OUTPUT_PREFIX_RELATION
                or self.prefix_added_to_final_value is not False
                or self.complete_fixed_point_total_selected_once_structurally
                is not True
            ):
                _fail("final output row does not replace its prefix exactly once")
        elif self.path == WORKING_PEAK_PATH:
            if (
                kind
                is not OuterRawSourceKindV1.POST_CUTOFF_SUPERVISOR_ENVELOPE
                or self.output_prefix_bytes is not None
                or self.output_prefix_relation is not None
                or self.prefix_added_to_final_value is not False
                or self.complete_fixed_point_total_selected_once_structurally
                is not False
            ):
                _fail(
                    "final working-set peak must come from the post-cutoff "
                    "supervisor envelope"
                )
        elif (
            kind is not OuterRawSourceKindV1.LIVE_MEASUREMENT_ROW
            or self.output_prefix_bytes is not None
            or self.output_prefix_relation is not None
            or self.prefix_added_to_final_value is not False
            or self.complete_fixed_point_total_selected_once_structurally
            is not False
        ):
            _fail("non-output row carries output fixed-point semantics")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_shared_resource_outer_raw_source_row.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_source_set_id": self.source_set_id,
            "live_measurement_snapshot_id": self.live_snapshot_id,
            "output_bytes_fixed_point_result_id": self.fixed_point_result_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "status": self.status.value,
            "value": self.value,
            "source_kind": self.source_kind.value,
            "source_row_id": self.source_row_id,
            "source_evidence_ids": list(self.source_evidence_ids),
            "output_prefix_bytes": self.output_prefix_bytes,
            "output_prefix_relation": self.output_prefix_relation,
            "prefix_added_to_final_value": self.prefix_added_to_final_value,
            "complete_fixed_point_total_selected_once_structurally": (
                self.complete_fixed_point_total_selected_once_structurally
            ),
            "operational_output_charge_authorized": False,
            "source_evidence_semantics_verified": False,
            "numeric_projection_authorized": False,
            "central_domain_registered": True,
        }

    @property
    def raw_source_row_id(self) -> str:
        return _content_id(OUTER_RAW_SOURCE_ROW_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outer_raw_source_row_id": self.raw_source_row_id}


def _live_row_evidence_ids(
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    row: live_v1.LiveMeasurementRowV1,
) -> tuple[str, ...]:
    events = tuple(
        event.source_evidence_id
        for event in snapshot.events
        if event.path == row.path and event.charged
    )
    if events:
        return events
    zero = tuple(
        claim.source_evidence_id
        for claim in snapshot.zero_claims
        if claim.path == row.path
    )
    if len(zero) != 1:
        _fail("recorded live row lacks its exact event or zero-claim source")
    return zero


def _require_parent_owned_event_source(
    *,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    path: str,
    source_id: str,
    source_kind: live_v1.LiveSourceEvidenceKindV1,
    must_establish_maximum: bool,
) -> None:
    matches = tuple(
        event
        for event in snapshot.events
        if event.path == path
        and event.charged
        and event.source_evidence_id == source_id
        and event.source_kind is source_kind
    )
    if len(matches) != 1:
        _fail(f"{path} lacks its exact structurally bound source event")
    if must_establish_maximum:
        row = next(item for item in snapshot.rows if item.path == path)
        if matches[0].observed_value != row.value:
            _fail(
                f"{path} structurally bound source does not establish "
                "the recorded maximum"
            )


def issue_post_cutoff_supervisor_envelope_v1(
    *,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    identity_binding: receipts_v1.SharedResourceIdentityBindingV1,
    route_identity_id: str,
    parent_global_terminal_source_id: str,
    child_reap_source_id: str,
    descendant_scan_source_id: str,
    final_cgroup_peak_source_id: str,
    child_reap_sequence: int,
    descendant_scan_sequence: int,
    final_cgroup_peak_sequence: int,
    parent_global_terminal_sequence: int,
    final_working_bytes_peak: int,
    child_reaped: bool,
    no_descendants: bool,
) -> PostCutoffSupervisorEnvelopeV1:
    """Freeze one structural claim ordering reap, scan, peak, and terminal."""

    if type(snapshot) is not live_v1.SharedResourceMeasurementSnapshotV1:
        _fail("post-cutoff envelope requires one issued live snapshot")
    if type(identity_binding) is not receipts_v1.SharedResourceIdentityBindingV1:
        _fail("post-cutoff envelope requires one exact measurement identity binding")
    live_v1.replay_live_measurement_snapshot_structure_v1(snapshot)
    if snapshot.identity_binding_id != identity_binding.identity_binding_id:
        _fail("post-cutoff envelope crossed its measurement identity")
    post_cutoff_source_ids = (
        _cid(
            parent_global_terminal_source_id,
            "post-cutoff parent global terminal source",
        ),
        _cid(child_reap_source_id, "post-cutoff child-reap source"),
        _cid(descendant_scan_source_id, "post-cutoff descendant-scan source"),
        _cid(final_cgroup_peak_source_id, "post-cutoff final cgroup source"),
    )
    pre_cutoff_source_ids = {
        event.source_evidence_id for event in snapshot.events
    }
    if any(source_id in pre_cutoff_source_ids for source_id in post_cutoff_source_ids):
        _fail("post-cutoff envelope reused a pre-cutoff live source")
    live_working_row = next(
        row for row in snapshot.rows if row.path == WORKING_PEAK_PATH
    )
    if (
        live_working_row.status
        is not receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED
        or type(live_working_row.value) is not int
        or type(final_working_bytes_peak) is not int
        or final_working_bytes_peak < live_working_row.value
    ):
        _fail("final cgroup peak cannot be below the pre-cutoff observed peak")
    return PostCutoffSupervisorEnvelopeV1(
        _POST_CUTOFF_ENVELOPE_ISSUER,
        route_identity_id,
        identity_binding.identity_binding_id,
        identity_binding.execution_profile_id,
        snapshot.snapshot_id,
        snapshot.window.cutoff_marker_id,
        parent_global_terminal_source_id,
        child_reap_source_id,
        descendant_scan_source_id,
        final_cgroup_peak_source_id,
        snapshot.window.cutoff_sequence,
        child_reap_sequence,
        descendant_scan_sequence,
        final_cgroup_peak_sequence,
        parent_global_terminal_sequence,
        final_working_bytes_peak,
        child_reaped,
        no_descendants,
    )


def _validate_join(
    *,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    identity_binding: receipts_v1.SharedResourceIdentityBindingV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    sources: ParentOwnedOuterSourceSetV1,
) -> None:
    if type(snapshot) is not live_v1.SharedResourceMeasurementSnapshotV1:
        _fail("outer finalization requires one issued live measurement snapshot")
    if type(fixed_point) is not fixed_v1.OutputBytesFixedPointResultV1:
        _fail("outer finalization requires one issued output-byte fixed point")
    if type(identity_binding) is not receipts_v1.SharedResourceIdentityBindingV1:
        _fail("outer finalization requires one exact measurement identity binding")
    if type(sources.post_cutoff_envelope) is not PostCutoffSupervisorEnvelopeV1:
        _fail("outer finalization requires one issued post-cutoff envelope")
    sources.post_cutoff_envelope.__post_init__(_POST_CUTOFF_ENVELOPE_ISSUER)
    live_v1.replay_live_measurement_snapshot_structure_v1(snapshot)
    if (
        snapshot.identity_binding_id != identity_binding.identity_binding_id
        or sources.measurement_identity_binding_id
        != identity_binding.identity_binding_id
        or sources.execution_profile_id != identity_binding.execution_profile_id
        or sources.post_cutoff_envelope.live_snapshot_id != snapshot.snapshot_id
        or sources.post_cutoff_envelope.cutoff_sequence
        != snapshot.window.cutoff_sequence
    ):
        _fail("live snapshot crossed its measurement/execution identity")
    if fixed_point.profile.execution_identity_id != sources.route_identity_id:
        _fail("output fixed point crossed its route identity")
    if sources.cutoff_source_id != snapshot.window.cutoff_marker_id:
        _fail("outer cutoff source differs from the live snapshot cutoff")
    if (
        not fixed_point.iterations[-1].converged
        or fixed_point.fixed_artifacts.total_bytes != fixed_point.output_bytes
        or fixed_point.fixed_artifacts.candidate_output_bytes
        != fixed_point.output_bytes
        or fixed_point.fixed_point_replay_count != 2
    ):
        _fail("output suffix is not one replayed exact fixed point")

    unavailable = snapshot.unavailable_resolutions
    output_unavailable = tuple(
        item for item in unavailable if item.path == OUTPUT_PATH
    )
    if (
        len(output_unavailable) != 1
        or output_unavailable[0].status is not OUTPUT_UNAVAILABLE_STATUS
        or output_unavailable[0].reason_code != OUTPUT_UNAVAILABLE_REASON
    ):
        _fail("live output must use the exact post-cutoff typed unavailability")
    if any(item.path != OUTPUT_PATH for item in unavailable):
        _fail("all eight pre-output shared-resource paths must be recorded")
    output_row = next(row for row in snapshot.rows if row.path == OUTPUT_PATH)
    if (
        output_row.status is not OUTPUT_UNAVAILABLE_STATUS
        or output_row.value is not None
        or output_row.unavailable_resolution_id
        != output_unavailable[0].resolution_id
    ):
        _fail("live output row differs from its exact typed unavailability")
    if any(
        row.status is not receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED
        for row in snapshot.rows
        if row.path != OUTPUT_PATH
    ):
        _fail("all eight pre-output shared-resource paths must be recorded")

    prefix = snapshot.observed_prefix_values.get(OUTPUT_PATH, 0)
    if type(prefix) is not int or prefix != 0 or any(
        event.path == OUTPUT_PATH and event.charged for event in snapshot.events
    ):
        _fail("operational output was committed before the complete fixed point")

    _require_parent_owned_event_source(
        snapshot=snapshot,
        path="process.launches",
        source_id=sources.process_supervisor_source_id,
        source_kind=live_v1.LiveSourceEvidenceKindV1.PROCESS_SUPERVISOR_LAUNCH,
        must_establish_maximum=False,
    )
    process_events = tuple(
        event
        for event in snapshot.events
        if event.path == "process.launches" and event.charged
    )
    process_row = next(
        row for row in snapshot.rows if row.path == "process.launches"
    )
    if len(process_events) != 1 or process_row.value != 1:
        _fail("the registered K7 outer profile requires exactly one child launch")
    _require_parent_owned_event_source(
        snapshot=snapshot,
        path="io.mounted_bytes_peak",
        source_id=sources.mount_manifest_source_id,
        source_kind=live_v1.LiveSourceEvidenceKindV1.SUPERVISOR_MOUNT_MANIFEST,
        must_establish_maximum=True,
    )
    live_working_row = next(
        row for row in snapshot.rows if row.path == WORKING_PEAK_PATH
    )
    if (
        type(live_working_row.value) is not int
        or sources.post_cutoff_envelope.final_working_bytes_peak
        < live_working_row.value
        or sources.post_cutoff_envelope.final_cgroup_peak_source_id
        in {event.source_evidence_id for event in snapshot.events}
    ):
        _fail("post-cutoff final cgroup peak does not cover the live prefix")


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class ParentOwnedSharedResourceFinalizationV1:
    _issuer: InitVar[object]
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1 = field(repr=False)
    identity_binding: receipts_v1.SharedResourceIdentityBindingV1 = field(
        repr=False
    )
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1 = field(repr=False)
    sources: ParentOwnedOuterSourceSetV1 = field(repr=False)
    rows: tuple[OuterFinalizedRawSourceRowV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("outer shared-resource finalization is finalizer-issued only")
        if type(self.sources) is not ParentOwnedOuterSourceSetV1:
            _fail("outer finalization lacks one exact parent source set")
        _validate_join(
            snapshot=self.snapshot,
            identity_binding=self.identity_binding,
            fixed_point=self.fixed_point,
            sources=self.sources,
        )
        if (
            type(self.rows) is not tuple
            or tuple(row.path for row in self.rows)
            != receipts_v1.SHARED_RESOURCE_PATHS
            or any(
                type(row) is not OuterFinalizedRawSourceRowV1
                or row.source_set_id != self.sources.source_set_id
                or row.live_snapshot_id != self.snapshot.snapshot_id
                or row.fixed_point_result_id != self.fixed_point.result_id
                for row in self.rows
            )
        ):
            _fail("outer finalization must contain exactly nine bound raw-source rows")
        expected = _build_rows(
            snapshot=self.snapshot,
            fixed_point=self.fixed_point,
            sources=self.sources,
        )
        if tuple(row.raw_source_row_id for row in self.rows) != tuple(
            row.raw_source_row_id for row in expected
        ):
            _fail("outer finalization rows differ from the source replay")

    @property
    def raw_source_values(self) -> dict[str, int]:
        return {row.path: row.value for row in self.rows}

    def _payload(self) -> dict[str, Any]:
        prefix = self.snapshot.observed_prefix_values.get(OUTPUT_PATH, 0)
        return {
            "schema": "acfqp.construction_shared_resource_outer_finalization.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "outer_source_set_id": self.sources.source_set_id,
            "route_identity_id": self.sources.route_identity_id,
            "measurement_identity_binding_id": (
                self.sources.measurement_identity_binding_id
            ),
            "execution_profile_id": self.sources.execution_profile_id,
            "live_measurement_snapshot_id": self.snapshot.snapshot_id,
            "output_bytes_fixed_point_result_id": self.fixed_point.result_id,
            "parent_global_terminal_sequence": (
                self.sources.parent_global_terminal_sequence
            ),
            "live_cutoff_sequence": self.snapshot.window.cutoff_sequence,
            "outer_raw_source_row_ids": [
                row.raw_source_row_id for row in self.rows
            ],
            "shared_resource_paths": list(receipts_v1.SHARED_RESOURCE_PATHS),
            "raw_source_row_count": len(self.rows),
            "raw_source_status": (
                receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED.value
            ),
            "output_prefix_bytes": prefix,
            "complete_output_fixed_point_bytes": self.fixed_point.output_bytes,
            "output_prefix_relation": OUTPUT_PREFIX_RELATION,
            "output_commit_before_fixed_point": False,
            "output_prefix_added_to_complete_total": False,
            "complete_output_fixed_point_total_selected_once_structurally": True,
            "artifact_bytes_committed": False,
            "fixed_point_covers_outer_wrapper_bytes": False,
            "operational_output_semantics_verified": False,
            "operational_artifact_write_authorized": False,
            "parent_global_terminal_order_bound_structurally": True,
            "child_reaped": self.sources.child_reaped,
            "no_descendants": self.sources.no_descendants,
            "child_reaped_claim_semantics_verified": False,
            "no_descendants_claim_semantics_verified": False,
            "mount_manifest_source_bound": True,
            "post_cutoff_supervisor_envelope_bound": True,
            "post_cutoff_final_cgroup_source_bound_structurally": True,
            "post_cutoff_lifecycle_semantics_verified": False,
            "post_reap_working_peak_comes_from_live_snapshot": False,
            "pre_cutoff_peak_accepted_as_final_peak": False,
            "final_working_bytes_peak": (
                self.sources.post_cutoff_envelope.final_working_bytes_peak
            ),
            "process_supervisor_source_bound": True,
            "child_self_reported_peak_accepted": False,
            "source_evidence_semantics_verified": False,
            "formal_counter_records_issued": False,
            "formal_work_vector_authorized": False,
            "formal_comparison_vector_authorized": False,
            "numeric_projection_authorized": False,
            "official_execution_allowed": False,
            "central_domain_registered": True,
        }

    @property
    def finalization_id(self) -> str:
        return _content_id(OUTER_FINALIZATION_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "shared_resource_outer_finalization_id": self.finalization_id,
        }


def _build_rows(
    *,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    sources: ParentOwnedOuterSourceSetV1,
) -> tuple[OuterFinalizedRawSourceRowV1, ...]:
    prefix = snapshot.observed_prefix_values.get(OUTPUT_PATH, 0)
    rows: list[OuterFinalizedRawSourceRowV1] = []
    for live_row in snapshot.rows:
        if live_row.path == OUTPUT_PATH:
            rows.append(
                OuterFinalizedRawSourceRowV1(
                    _ROW_ISSUER,
                    sources.source_set_id,
                    snapshot.snapshot_id,
                    fixed_point.result_id,
                    live_row.path,
                    ReducerEnum.SUM,
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    fixed_point.output_bytes,
                    OuterRawSourceKindV1.COMPLETE_OUTPUT_FIXED_POINT,
                    fixed_point.result_id,
                    (
                        fixed_point.profile.profile_id,
                        fixed_point.fixed_artifacts.artifact_set_id,
                    ),
                    prefix,
                    OUTPUT_PREFIX_RELATION,
                    False,
                    True,
                )
            )
            continue
        if live_row.path == WORKING_PEAK_PATH:
            envelope = sources.post_cutoff_envelope
            rows.append(
                OuterFinalizedRawSourceRowV1(
                    _ROW_ISSUER,
                    sources.source_set_id,
                    snapshot.snapshot_id,
                    fixed_point.result_id,
                    live_row.path,
                    ReducerEnum.MAX,
                    receipts_v1.MeasurementStatusV1.RECORDED_UNVERIFIED,
                    envelope.final_working_bytes_peak,
                    OuterRawSourceKindV1.POST_CUTOFF_SUPERVISOR_ENVELOPE,
                    envelope.final_cgroup_peak_source_id,
                    (
                        envelope.child_reap_source_id,
                        envelope.descendant_scan_source_id,
                        envelope.final_cgroup_peak_source_id,
                        envelope.parent_global_terminal_source_id,
                    ),
                    None,
                    None,
                    False,
                    False,
                )
            )
            continue
        assert type(live_row.value) is int
        rows.append(
            OuterFinalizedRawSourceRowV1(
                _ROW_ISSUER,
                sources.source_set_id,
                snapshot.snapshot_id,
                fixed_point.result_id,
                live_row.path,
                live_row.reducer,
                live_row.status,
                live_row.value,
                OuterRawSourceKindV1.LIVE_MEASUREMENT_ROW,
                live_row.row_id,
                _live_row_evidence_ids(snapshot, live_row),
                None,
                None,
                False,
                False,
            )
        )
    return tuple(rows)


def finalize_parent_owned_shared_resources_v1(
    *,
    snapshot: live_v1.SharedResourceMeasurementSnapshotV1,
    identity_binding: receipts_v1.SharedResourceIdentityBindingV1,
    fixed_point: fixed_v1.OutputBytesFixedPointResultV1,
    route_identity_id: str,
    business_source_id: str,
    cutoff_source_id: str,
    process_supervisor_source_id: str,
    mount_manifest_source_id: str,
    post_cutoff_envelope: PostCutoffSupervisorEnvelopeV1,
) -> ParentOwnedSharedResourceFinalizationV1:
    """Join a closed live prefix to one structural eight-role fixed point."""

    if type(identity_binding) is not receipts_v1.SharedResourceIdentityBindingV1:
        _fail("outer finalization requires one exact measurement identity binding")
    sources = ParentOwnedOuterSourceSetV1(
        route_identity_id=route_identity_id,
        measurement_identity_binding_id=identity_binding.identity_binding_id,
        execution_profile_id=identity_binding.execution_profile_id,
        business_source_id=business_source_id,
        cutoff_source_id=cutoff_source_id,
        process_supervisor_source_id=process_supervisor_source_id,
        mount_manifest_source_id=mount_manifest_source_id,
        post_cutoff_envelope=post_cutoff_envelope,
    )
    _validate_join(
        snapshot=snapshot,
        identity_binding=identity_binding,
        fixed_point=fixed_point,
        sources=sources,
    )
    rows = _build_rows(snapshot=snapshot, fixed_point=fixed_point, sources=sources)
    return ParentOwnedSharedResourceFinalizationV1(
        _RESULT_ISSUER,
        snapshot,
        identity_binding,
        fixed_point,
        sources,
        rows,
    )


def replay_parent_owned_shared_resource_finalization_v1(
    result: ParentOwnedSharedResourceFinalizationV1,
) -> ParentOwnedSharedResourceFinalizationV1:
    """Replay the structural join without promoting its source claims."""

    if type(result) is not ParentOwnedSharedResourceFinalizationV1:
        _fail("outer finalization replay requires one issued result")
    _validate_join(
        snapshot=result.snapshot,
        identity_binding=result.identity_binding,
        fixed_point=result.fixed_point,
        sources=result.sources,
    )
    expected = _build_rows(
        snapshot=result.snapshot,
        fixed_point=result.fixed_point,
        sources=result.sources,
    )
    if tuple(row.raw_source_row_id for row in expected) != tuple(
        row.raw_source_row_id for row in result.rows
    ):
        _fail("outer finalization replay changed a raw-source row")
    return result


__all__ = [
    "ConstructionSharedResourceOuterFinalizationV1Error",
    "LOCAL_DOMAIN_TAGS",
    "OUTER_FINALIZATION_V1_DOMAIN",
    "OUTER_RAW_SOURCE_ROW_V1_DOMAIN",
    "OUTER_SOURCE_SET_V1_DOMAIN",
    "OUTPUT_PATH",
    "OUTPUT_PREFIX_RELATION",
    "OUTPUT_UNAVAILABLE_REASON",
    "OUTPUT_UNAVAILABLE_STATUS",
    "WORKING_PEAK_PATH",
    "OuterFinalizedRawSourceRowV1",
    "OuterRawSourceKindV1",
    "PROFILE_KEY",
    "ParentOwnedOuterSourceSetV1",
    "ParentOwnedSharedResourceFinalizationV1",
    "PostCutoffSupervisorEnvelopeV1",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "finalize_parent_owned_shared_resources_v1",
    "issue_post_cutoff_supervisor_envelope_v1",
    "replay_parent_owned_shared_resource_finalization_v1",
]
