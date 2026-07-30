"""Exact construction-only incremental numerical models for open V0-075 runs.

This authority consumes only observer-signed controlled aggregate appends,
observer-signed complete support freezes, and an exact open-prefix
verification.  It compiles the same numerical row semantics as the batch
planning backend, reuses a parent row only when its complete source digest is
unchanged, and recomputes the full numerical planning proof at every model
epoch.  Portable replay verifies the parent first, recompiles every new or
changed row, inherits unchanged row bytes from that verified parent, and still
recomputes the complete numerical proof at every epoch.

The artifacts in this module are provisional construction evidence.  They do
not certify a plan or infeasibility and cannot authorize official execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.60.0"
PROFILE_KEY = "v075_live_incremental_model_authority_v2"
MAX_MODEL_EPOCHS = 64
MAX_CONTROLLED_APPENDS = 256
MAX_CANONICAL_INPUT_BYTES = 128 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
PRIVATE_LAW_ACCESS_ALLOWED = False
PER_DRAW_RECORDS_ALLOWED = False

TERMINAL_SCOPE = "INTERMEDIATE_MODEL_EPOCH_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
PRODUCTION_BLOCKER = (
    "live incremental model epochs are construction-only; dynamic acquisition "
    "termination, independent total lift, closed-lineage reconciliation, and "
    "the production bundle verifier are not integrated"
)

DOMAIN_TAGS = {
    "row_source_digest": (
        "acfqp:v075-live-incremental-row-source-digest:v2"
    ),
    "row_source_binding": (
        "acfqp:v075-live-incremental-row-source-binding:v2"
    ),
    "model_epoch": "acfqp:v075-live-incremental-model-epoch:v2",
    "verification": (
        "acfqp:v075-live-incremental-model-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 live model domains must be unique")


class V075LiveIncrementalModelV2InvariantViolation(ValueError):
    """A prefix, source row, model epoch, or replay was invalid."""


class V075LiveIncrementalModelProductionV2NotReady(RuntimeError):
    """The construction-only model authority cannot run in production."""


def _fail(message: str) -> NoReturn:
    raise V075LiveIncrementalModelV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveIncrementalModelV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075LiveIncrementalModelV2InvariantViolation(
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
        raise V075LiveIncrementalModelV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _replay_identity(
    claimed: backend.V075BatchNativeOccurrenceIdentityV1,
) -> backend.V075BatchNativeOccurrenceIdentityV1:
    try:
        replayed = backend.replay_v075_batch_native_occurrence_identity_v1(
            claimed
        )
    except Exception as error:
        raise V075LiveIncrementalModelV2InvariantViolation(
            "live model occurrence identity replay failed"
        ) from error
    if replayed.to_document() != claimed.to_document():
        _fail("live model occurrence differs from exact replay")
    return replayed


def _replay_open_prefix(
    claimed: control.V075OpenControlledBatchPrefixVerificationV2,
) -> control.V075OpenControlledBatchPrefixVerificationV2:
    if (
        type(claimed)
        is not control.V075OpenControlledBatchPrefixVerificationV2
    ):
        _fail("live model requires one exact open-prefix verification")
    try:
        replayed = control.verify_v075_open_controlled_batch_prefix_v2(
            heads=claimed.heads,
            appends=claimed.appends,
            support_freezes=claimed.support_freezes,
        )
    except Exception as error:
        raise V075LiveIncrementalModelV2InvariantViolation(
            "live model open-prefix verification replay failed"
        ) from error
    if (
        replayed.verification_id != claimed.verification_id
        or replayed.to_document() != claimed.to_document()
    ):
        _fail("open-prefix verification differs from exact replay")
    return replayed


def _replay_open_prefix_incrementally(
    *,
    claimed: control.V075OpenControlledBatchPrefixVerificationV2,
    parent: control.V075OpenControlledBatchPrefixVerificationV2,
) -> control.V075OpenControlledBatchPrefixVerificationV2:
    """Replay only the suffix after one already exact parent prefix."""

    if (
        type(claimed)
        is not control.V075OpenControlledBatchPrefixVerificationV2
        or type(parent)
        is not control.V075OpenControlledBatchPrefixVerificationV2
        or len(claimed.heads) <= len(parent.heads)
        or claimed.head_ids[: len(parent.head_ids)] != parent.head_ids
        or claimed.receipt_ids[: len(parent.receipt_ids)]
        != parent.receipt_ids
        or claimed.support_freeze_ids[: len(parent.support_freeze_ids)]
        != parent.support_freeze_ids
        or claimed.zero_head_id != parent.zero_head_id
        or claimed.occurrence_id != parent.occurrence_id
        or claimed.session_public_id != parent.session_public_id
        or claimed.observer_open_binding_id
        != parent.observer_open_binding_id
    ):
        _fail("live open prefix is not a strict extension of its parent")
    try:
        heads = parent.heads + tuple(
            control._replay_signed_head(item)  # noqa: SLF001
            for item in claimed.heads[len(parent.heads) :]
        )
        appends = parent.appends + tuple(
            control._replay_append(item)  # noqa: SLF001
            for item in claimed.appends[len(parent.appends) :]
        )
        freezes = parent.support_freezes + tuple(
            control._replay_support_freeze(item)  # noqa: SLF001
            for item in claimed.support_freezes[
                len(parent.support_freezes) :
            ]
        )
    except Exception as error:
        raise V075LiveIncrementalModelV2InvariantViolation(
            "live open-prefix suffix replay failed"
        ) from error
    if len(heads) != len(appends) + 1:
        _fail("live open-prefix suffix changed head/append cardinality")
    if freezes != tuple(
        sorted(
            freezes,
            key=lambda item: (
                item.frozen_at_head.entry_count,
                item.row_binding_id,
                item.freeze_id,
            ),
        )
    ):
        _fail("live open-prefix support freezes are reordered")
    for index, append in enumerate(appends):
        if (
            append.prior_head != heads[index]
            or append.resulting_head != heads[index + 1]
        ):
            _fail("live open-prefix suffix breaks the signed head chain")
    head_ids = {item.head_id for item in heads}
    receipt_ids = {item.receipt.receipt_id for item in appends}
    if any(
        freeze.frozen_at_head.head_id not in head_ids
        or freeze.discovery_append_receipt_id not in receipt_ids
        for freeze in freezes
    ):
        _fail("live support freeze is outside the exact append/head prefix")
    expected = control.V075OpenControlledBatchPrefixVerificationV2(
        control._OPEN_PREFIX_VERIFICATION_ISSUER,  # noqa: SLF001
        heads,
        appends,
        freezes,
        parent.occurrence_id,
        parent.session_public_id,
        parent.observer_open_binding_id,
        parent.zero_head_id,
        heads[-1].head_id,
        tuple(item.head_id for item in heads),
        tuple(item.intent.intent_id for item in appends),
        tuple(item.batch.batch_id for item in appends),
        tuple(item.receipt.receipt_id for item in appends),
        tuple(item.freeze_id for item in freezes),
        len(appends),
        heads[-1].total_accepted_draw_count,
    )
    if (
        expected.verification_id != claimed.verification_id
        or expected.to_document() != claimed.to_document()
    ):
        _fail("live open-prefix extension differs from exact suffix replay")
    return expected


_ROW_SOURCE_ISSUER = object()
_MODEL_EPOCH_ISSUER = object()
_VERIFICATION_ISSUER = object()
_MAX_TRUSTED_SAME_PROCESS_EPOCHS = 4_096
_TRUSTED_SAME_PROCESS_EPOCHS: dict[
    int,
    tuple[
        "V075LiveIncrementalModelEpochV2",
        str,
        str,
        str,
        str,
        str,
    ],
] = {}


@dataclass(frozen=True, slots=True)
class V075LiveModelRowSourceBindingV2:
    """Complete aggregate provenance for one numerical state-action row."""

    _issuer: object = field(repr=False, compare=False)
    row_binding_id: str
    discovery_append_receipt_id: str
    discovery_batch_id: str
    support_freeze_id: str
    validation_stream_id: str
    validation_append_receipt_ids: tuple[str, ...]
    validation_batch_ids: tuple[str, ...]
    validation_prefix_end: int
    validation_draw_cap: int
    source_digest: str
    numerical_row_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.row_binding_id, "live row binding"),
            (
                self.discovery_append_receipt_id,
                "live row discovery append receipt",
            ),
            (self.discovery_batch_id, "live row discovery batch"),
            (self.support_freeze_id, "live row support freeze"),
            (self.validation_stream_id, "live row validation stream"),
            (self.source_digest, "live row source digest"),
            (self.numerical_row_id, "live numerical row"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _ROW_SOURCE_ISSUER
            or type(self.validation_append_receipt_ids) is not tuple
            or not self.validation_append_receipt_ids
            or any(
                _cid(value, "live validation receipt") != value
                for value in self.validation_append_receipt_ids
            )
            or len(self.validation_append_receipt_ids)
            != len(set(self.validation_append_receipt_ids))
            or type(self.validation_batch_ids) is not tuple
            or not self.validation_batch_ids
            or any(
                _cid(value, "live validation batch") != value
                for value in self.validation_batch_ids
            )
            or len(self.validation_batch_ids)
            != len(set(self.validation_batch_ids))
            or len(self.validation_batch_ids)
            != len(self.validation_append_receipt_ids)
            or type(self.validation_prefix_end) is not int
            or self.validation_prefix_end <= 0
            or type(self.validation_draw_cap) is not int
            or self.validation_draw_cap < self.validation_prefix_end
        ):
            _fail("live model row source binding is malformed")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("row_source_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_model_row_source_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "row_binding_id": self.row_binding_id,
            "discovery_append_receipt_id": (
                self.discovery_append_receipt_id
            ),
            "discovery_batch_id": self.discovery_batch_id,
            "support_freeze_id": self.support_freeze_id,
            "validation_stream_id": self.validation_stream_id,
            "validation_append_receipt_ids": list(
                self.validation_append_receipt_ids
            ),
            "validation_batch_ids": list(self.validation_batch_ids),
            "validation_prefix_end": self.validation_prefix_end,
            "validation_draw_cap": self.validation_draw_cap,
            "validation_observer_epoch_index": 1,
            "source_digest": self.source_digest,
            "numerical_row_id": self.numerical_row_id,
            "discovery_counts_excluded": True,
            "complete_support_frozen_before_validation": True,
            "count_only": True,
            "per_draw_records_used": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class _CollectedRow:
    row_binding_id: str
    source_digest: str
    source_payload: dict[str, Any]
    discovery_append: control.V075ControlledBatchAppendV2
    support_freeze: control.V075ControlledCompleteSupportFreezeV2
    validation_appends: tuple[control.V075ControlledBatchAppendV2, ...]


def _stage_is_discovery(
    stage: control.V075ControlledBatchStageV2,
) -> bool:
    return stage in {
        control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
        control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
    }


def _stage_is_validation(
    stage: control.V075ControlledBatchStageV2,
) -> bool:
    return stage in {
        control.V075ControlledBatchStageV2.ROOT_VALIDATION,
        control.V075ControlledBatchStageV2.CHILD_VALIDATION,
    }


def _expected_stages(
    remaining_horizon: int,
) -> tuple[
    control.V075ControlledBatchStageV2,
    control.V075ControlledBatchStageV2,
]:
    if remaining_horizon == 2:
        return (
            control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
            control.V075ControlledBatchStageV2.ROOT_VALIDATION,
        )
    if remaining_horizon == 1:
        return (
            control.V075ControlledBatchStageV2.CHILD_DISCOVERY,
            control.V075ControlledBatchStageV2.CHILD_VALIDATION,
        )
    _fail("live model accepts only H2 root and H1 child rows")


def _source_payload(
    *,
    discovery: control.V075ControlledBatchAppendV2,
    support_freeze: control.V075ControlledCompleteSupportFreezeV2,
    validations: tuple[control.V075ControlledBatchAppendV2, ...],
) -> dict[str, Any]:
    row = discovery.batch.request.stream_identity.row_binding
    validation_requests = tuple(item.batch.request for item in validations)
    return {
        "schema": "acfqp.v075_live_incremental_row_source_digest.v2",
        "schema_version": SCHEMA_VERSION,
        "row_binding_id": row.row_binding_id,
        "discovery_append_receipt_id": discovery.receipt.receipt_id,
        "discovery_batch_id": discovery.batch.batch_id,
        "support_freeze_id": support_freeze.freeze_id,
        "validation_stream_id": (
            validation_requests[0].stream_identity.stream_id
        ),
        "validation_append_receipt_ids": [
            item.receipt.receipt_id for item in validations
        ],
        "validation_batch_ids": [
            item.batch.batch_id for item in validations
        ],
        "validation_request_ids": [
            item.request_id for item in validation_requests
        ],
        "validation_prefix_end": validation_requests[-1].accepted_draw_end,
        "validation_draw_cap": validation_requests[0].accepted_draw_cap,
        "validation_observer_epoch_index": 1,
        "complete_support_freeze_is_observer_signed": True,
        "count_only": True,
        "per_draw_records_used": False,
    }


def _compile_numerical_row(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    discovery: control.V075ControlledBatchAppendV2,
    support_freeze: control.V075ControlledCompleteSupportFreezeV2,
    validations: tuple[control.V075ControlledBatchAppendV2, ...],
) -> planning.V075NumericalRowV2:
    row_binding = discovery.batch.request.stream_identity.row_binding
    descriptors: list[planning.V075SupportDescriptorV2] = []
    for evidence in support_freeze.evidence:
        state = evidence.observed_state
        terminal = state.failure or row_binding.remaining_horizon == 1
        descriptor = planning.V075SupportDescriptorV2(
            planning._DESCRIPTOR_ISSUER,  # noqa: SLF001
            row_binding.context_id,
            state.state_id,
            state.ranks,
            state.failure,
            terminal,
        )
        descriptors.append(descriptor)
    support = tuple(
        sorted(descriptors, key=lambda item: item.descriptor_id)
    )
    if len({item.descriptor_id for item in support}) != len(support):
        _fail("live support freeze aliases one symbolic descriptor")

    counts: dict[tuple[tuple[int, ...], bool, bool], int] = {}
    draw_count = 0
    structural_reward = planning._merge_reward(row_binding)  # noqa: SLF001
    for append in validations:
        batch = append.batch
        draw_count += batch.request.accepted_draw_count
        for outcome in batch.outcomes:
            if (
                outcome.realized_row_reward != structural_reward
                or outcome.reward_sum != structural_reward * outcome.count
            ):
                _fail(
                    "live validation reward differs from deterministic "
                    "structural merge reward"
                )
            key = (
                outcome.next_ranks,
                outcome.failure,
                outcome.terminal,
            )
            counts[key] = counts.get(key, 0) + outcome.count
    if draw_count != validations[-1].batch.request.accepted_draw_end:
        _fail("live validation aggregate count differs from its prefix")
    if sum(counts.values()) != draw_count:
        _fail("live validation outcome counts do not partition the prefix")

    descriptor_counts: list[int] = []
    for descriptor in support:
        descriptor_counts.append(
            counts.get(
                (
                    descriptor.next_ranks,
                    descriptor.failure,
                    descriptor.terminal,
                ),
                0,
            )
        )
    other_count = draw_count - sum(descriptor_counts)
    if other_count < 0:
        _fail("live support event counts exceed the validation prefix")

    checkpoints = planning._allowed_checkpoints(  # noqa: SLF001
        arm=occurrence_identity.arm,
        remaining_horizon=row_binding.remaining_horizon,
        caps=worker.V075WorkerCapProfileV1(),
    )
    intervals = tuple(
        planning._checkpoint_interval(  # noqa: SLF001
            descriptor=descriptor,
            draw_count=draw_count,
            success_count=count,
            event_count=len(support) + 1,
            checkpoints=checkpoints,
        )
        for descriptor, count in zip(support, descriptor_counts)
    ) + (
        planning._checkpoint_interval(  # noqa: SLF001
            descriptor=None,
            draw_count=draw_count,
            success_count=other_count,
            event_count=len(support) + 1,
            checkpoints=checkpoints,
        ),
    )
    row = planning.V075NumericalRowV2(
        planning._ROW_ISSUER,  # noqa: SLF001
        row_binding.context_id,
        row_binding.row_binding_id,
        row_binding.state_id,
        row_binding.catalogue.state.ranks,
        row_binding.remaining_horizon,
        row_binding.action,
        structural_reward,
        support,
        intervals,
    )
    return planning._replay_numerical_row(row)  # noqa: SLF001


def _collect_rows(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    appends: tuple[control.V075ControlledBatchAppendV2, ...],
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ],
    portable_replay: bool,
) -> tuple[_CollectedRow, ...]:
    discoveries: dict[str, list[control.V075ControlledBatchAppendV2]] = {}
    validations: dict[str, list[control.V075ControlledBatchAppendV2]] = {}
    for append in appends:
        stream = append.batch.request.stream_identity
        stage = append.intent.semantic_authority.stage
        target = (
            discoveries
            if _stage_is_discovery(stage)
            else validations
            if _stage_is_validation(stage)
            else None
        )
        if target is None:
            _fail("open prefix contains an unregistered model stage")
        target.setdefault(stream.row_binding_id, []).append(append)

    freeze_by_row: dict[
        str,
        list[control.V075ControlledCompleteSupportFreezeV2],
    ] = {}
    for freeze in support_freezes:
        freeze_by_row.setdefault(freeze.row_binding_id, []).append(freeze)
    discovered_rows = set(discoveries)
    if (
        not discovered_rows
        or set(freeze_by_row) != discovered_rows
        or set(validations) != discovered_rows
    ):
        _fail(
            "every discovered live row requires exactly one complete freeze "
            "and a nonempty validation prefix"
        )

    collected: list[_CollectedRow] = []
    for row_id in sorted(discovered_rows):
        row_discoveries = discoveries[row_id]
        freezes = freeze_by_row[row_id]
        row_validations = validations[row_id]
        if len(row_discoveries) != 1 or len(freezes) != 1:
            _fail("live row discovery or support freeze was recapped")
        discovery = row_discoveries[0]
        freeze = freezes[0]
        row_binding = discovery.batch.request.stream_identity.row_binding
        expected_discovery, expected_validation = _expected_stages(
            row_binding.remaining_horizon
        )
        discovery_stream = discovery.batch.request.stream_identity
        if (
            discovery.intent.semantic_authority.stage
            is not expected_discovery
            or discovery_stream.lane
            is not graph.V075ObservationLaneV1.DISCOVERY
            or discovery_stream.observer_epoch_index != 0
            or freeze.discovery_append != discovery
            or freeze.frozen_at_head.entry_count
            < discovery.resulting_head.entry_count
        ):
            _fail(
                "live row lacks discovery-epoch-0 then complete-freeze order"
            )
        ordered = tuple(
            sorted(
                row_validations,
                key=lambda item: item.batch.request.accepted_draw_start,
            )
        )
        expected_start = 1
        validation_stream_id: str | None = None
        validation_cap: int | None = None
        expected_validation_stream = (
            control.derive_v075_controlled_validation_stream_v2(
                support_freeze=freeze,
            )
            if portable_replay
            else control._derive_validation_stream_from_owned_support_freeze(  # noqa: SLF001
                freeze
            )
        )
        for append in ordered:
            request = append.batch.request
            stream = request.stream_identity
            if (
                append.intent.semantic_authority.stage
                is not expected_validation
                or stream.lane
                is not graph.V075ObservationLaneV1.VALIDATION
                or stream.observer_epoch_index != 1
                or stream.row_binding != row_binding
                or stream != expected_validation_stream
                or append.intent.semantic_authority.support_freeze_id
                != freeze.freeze_id
                or append.prior_head.entry_count
                < freeze.frozen_at_head.entry_count
                or request.accepted_draw_start != expected_start
            ):
                _fail(
                    "live validation is stale, gapped, pre-freeze, or "
                    "bound to the wrong row/support"
                )
            if validation_stream_id is None:
                validation_stream_id = stream.stream_id
                validation_cap = request.accepted_draw_cap
            elif (
                validation_stream_id != stream.stream_id
                or validation_cap != request.accepted_draw_cap
            ):
                _fail("live validation changed stream or cap")
            expected_start = request.accepted_draw_end + 1
        if validation_stream_id is None or validation_cap is None:
            _fail("live row has no validation stream")
        draw_count = expected_start - 1
        checkpoints = planning._allowed_checkpoints(  # noqa: SLF001
            arm=occurrence_identity.arm,
            remaining_horizon=row_binding.remaining_horizon,
            caps=worker.V075WorkerCapProfileV1(),
        )
        if draw_count not in checkpoints:
            _fail("live validation prefix is not a registered checkpoint")

        payload = _source_payload(
            discovery=discovery,
            support_freeze=freeze,
            validations=ordered,
        )
        digest = _hash("row_source_digest", payload)
        collected.append(
            _CollectedRow(
                row_id,
                digest,
                payload,
                discovery,
                freeze,
                ordered,
            )
        )
    return tuple(collected)


def _row_source_binding(
    compiled: _CollectedRow,
    numerical_row: planning.V075NumericalRowV2,
) -> V075LiveModelRowSourceBindingV2:
    validations = compiled.validation_appends
    return V075LiveModelRowSourceBindingV2(
        _ROW_SOURCE_ISSUER,
        compiled.row_binding_id,
        compiled.discovery_append.receipt.receipt_id,
        compiled.discovery_append.batch.batch_id,
        compiled.support_freeze.freeze_id,
        validations[0].batch.request.stream_identity.stream_id,
        tuple(item.receipt.receipt_id for item in validations),
        tuple(item.batch.batch_id for item in validations),
        validations[-1].batch.request.accepted_draw_end,
        validations[0].batch.request.accepted_draw_cap,
        compiled.source_digest,
        numerical_row.row_id,
    )


def _replay_row_source_binding(
    claimed: V075LiveModelRowSourceBindingV2,
) -> V075LiveModelRowSourceBindingV2:
    if type(claimed) is not V075LiveModelRowSourceBindingV2:
        _fail("live row source replay rejects duck-typed inputs")
    replayed = V075LiveModelRowSourceBindingV2(
        _ROW_SOURCE_ISSUER,
        claimed.row_binding_id,
        claimed.discovery_append_receipt_id,
        claimed.discovery_batch_id,
        claimed.support_freeze_id,
        claimed.validation_stream_id,
        claimed.validation_append_receipt_ids,
        claimed.validation_batch_ids,
        claimed.validation_prefix_end,
        claimed.validation_draw_cap,
        claimed.source_digest,
        claimed.numerical_row_id,
    )
    if (
        replayed.binding_id != claimed.binding_id
        or replayed.to_document() != claimed.to_document()
    ):
        _fail("live row source differs from exact reconstruction")
    return replayed


@dataclass(frozen=True, slots=True)
class V075LiveIncrementalModelEpochV2:
    """One exact model/proof snapshot at an observer-signed journal head."""

    _issuer: object = field(repr=False, compare=False)
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    controlled_appends: tuple[control.V075ControlledBatchAppendV2, ...] = field(
        repr=False
    )
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ] = field(repr=False)
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ) = field(repr=False)
    parent_epoch: V075LiveIncrementalModelEpochV2 | None = field(
        repr=False
    )
    epoch_index: int
    context_id: str
    arm: worker.V075WorkerArmV1
    head_id: str
    route: planning.V075PlanningRouteV2
    row_sources: tuple[V075LiveModelRowSourceBindingV2, ...]
    model: planning.V075NumericalModelV2
    proof: planning.V075NumericalPlanningProofV2
    changed_row_binding_ids: tuple[str, ...]
    reused_row_binding_ids: tuple[str, ...]
    _model_epoch_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        identity = _replay_identity(self.occurrence_identity)
        _cid(self.context_id, "live model context")
        _cid(self.head_id, "live model journal head")
        if (
            self._issuer is not _MODEL_EPOCH_ISSUER
            or type(self.controlled_appends) is not tuple
            or not self.controlled_appends
            or len(self.controlled_appends) > MAX_CONTROLLED_APPENDS
            or any(
                type(item) is not control.V075ControlledBatchAppendV2
                for item in self.controlled_appends
            )
            or type(self.support_freezes) is not tuple
            or not self.support_freezes
            or any(
                type(item)
                is not control.V075ControlledCompleteSupportFreezeV2
                for item in self.support_freezes
            )
            or type(self.open_prefix_verification)
            is not control.V075OpenControlledBatchPrefixVerificationV2
            or (
                self.parent_epoch is not None
                and type(self.parent_epoch)
                is not V075LiveIncrementalModelEpochV2
            )
            or type(self.epoch_index) is not int
            or self.epoch_index not in range(1, MAX_MODEL_EPOCHS + 1)
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.route) is not planning.V075PlanningRouteV2
            or (
                self.route
                is planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND
            )
            != (
                self.arm
                is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            )
            or type(self.row_sources) is not tuple
            or not self.row_sources
            or len(
                {item.row_binding_id for item in self.row_sources}
            )
            != len(self.row_sources)
            or type(self.model) is not planning.V075NumericalModelV2
            or type(self.proof) is not planning.V075NumericalPlanningProofV2
            or self.proof.model.model_id != self.model.model_id
            or self.proof.route is not self.route
            or type(self.changed_row_binding_ids) is not tuple
            or type(self.reused_row_binding_ids) is not tuple
            or self.changed_row_binding_ids
            != tuple(sorted(set(self.changed_row_binding_ids)))
            or self.reused_row_binding_ids
            != tuple(sorted(set(self.reused_row_binding_ids)))
        ):
            _fail("live incremental model epoch is malformed")
        all_rows = tuple(item.row_binding_id for item in self.row_sources)
        if (
            set(self.changed_row_binding_ids)
            & set(self.reused_row_binding_ids)
            or set(self.changed_row_binding_ids)
            | set(self.reused_row_binding_ids)
            != set(all_rows)
            or identity.context_id != self.context_id
            or identity.arm is not self.arm
            or identity.occurrence_id
            != self.open_prefix_verification.occurrence_id
            or self.head_id
            != self.open_prefix_verification.current_head_id
            or tuple(
                item.receipt.receipt_id for item in self.controlled_appends
            )
            != self.open_prefix_verification.receipt_ids
            or tuple(item.freeze_id for item in self.support_freezes)
            != self.open_prefix_verification.support_freeze_ids
            or tuple(item.numerical_row_id for item in self.row_sources)
            != tuple(item.row_id for item in self.model.rows)
            or tuple(item.row_binding_id for item in self.row_sources)
            != tuple(item.row_binding_id for item in self.model.rows)
        ):
            _fail("live model identity, prefix, or row graph is inconsistent")
        if self.parent_epoch is None:
            if self.epoch_index != 1 or self.reused_row_binding_ids:
                _fail("first live model epoch cannot claim reused rows")
        else:
            parent = self.parent_epoch
            if (
                self.epoch_index != parent.epoch_index + 1
                or self.occurrence_identity != parent.occurrence_identity
                or self.route is not parent.route
                or self.open_prefix_verification.zero_head_id
                != parent.open_prefix_verification.zero_head_id
                or len(self.open_prefix_verification.head_ids)
                <= len(parent.open_prefix_verification.head_ids)
                or self.open_prefix_verification.head_ids[
                    : len(parent.open_prefix_verification.head_ids)
                ]
                != parent.open_prefix_verification.head_ids
                or self.open_prefix_verification.receipt_ids[
                    : len(parent.open_prefix_verification.receipt_ids)
                ]
                != parent.open_prefix_verification.receipt_ids
                or not set(parent.support_freeze_ids)
                <= set(self.support_freeze_ids)
                or not set(
                    item.row_binding_id for item in parent.row_sources
                )
                <= set(all_rows)
            ):
                _fail("live model parent is not one exact monotone prefix")
        object.__setattr__(
            self,
            "_model_epoch_id",
            _hash("model_epoch", self._payload()),
        )

    @property
    def parent_epoch_id(self) -> str | None:
        return (
            None
            if self.parent_epoch is None
            else self.parent_epoch.model_epoch_id
        )

    @property
    def occurrence_id(self) -> str:
        return self.occurrence_identity.occurrence_id

    @property
    def target_tape_namespace_id(self) -> str:
        return self.occurrence_identity.target_tape_namespace_id

    @property
    def append_receipt_ids(self) -> tuple[str, ...]:
        return tuple(item.receipt.receipt_id for item in self.controlled_appends)

    @property
    def support_freeze_ids(self) -> tuple[str, ...]:
        return tuple(item.freeze_id for item in self.support_freezes)

    def row_source_for_binding_v2(
        self,
        row_binding_id: str,
    ) -> V075LiveModelRowSourceBindingV2:
        _cid(row_binding_id, "requested live row binding")
        matches = tuple(
            item
            for item in self.row_sources
            if item.row_binding_id == row_binding_id
        )
        if len(matches) != 1:
            _fail("requested live row source is absent or duplicated")
        return matches[0]

    def controlled_append_by_receipt_id_v2(
        self,
        receipt_id: str,
    ) -> control.V075ControlledBatchAppendV2:
        _cid(receipt_id, "requested append receipt")
        matches = tuple(
            item
            for item in self.controlled_appends
            if item.receipt.receipt_id == receipt_id
        )
        if len(matches) != 1:
            _fail("requested controlled append is absent or duplicated")
        return matches[0]

    def support_freeze_by_id_v2(
        self,
        freeze_id: str,
    ) -> control.V075ControlledCompleteSupportFreezeV2:
        _cid(freeze_id, "requested complete support freeze")
        matches = tuple(
            item for item in self.support_freezes if item.freeze_id == freeze_id
        )
        if len(matches) != 1:
            _fail("requested complete support freeze is absent or duplicated")
        return matches[0]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_incremental_model_epoch.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "head_id": self.head_id,
            "epoch_index": self.epoch_index,
            "parent_epoch_id": self.parent_epoch_id,
            "open_prefix_verification_id": (
                self.open_prefix_verification.verification_id
            ),
            "append_receipt_ids": list(self.append_receipt_ids),
            "support_freeze_ids": list(self.support_freeze_ids),
            "route": self.route.value,
            "row_source_binding_ids": [
                item.binding_id for item in self.row_sources
            ],
            "numerical_model_id": self.model.model_id,
            "numerical_proof_id": self.proof.proof_id,
            "changed_row_binding_ids": list(
                self.changed_row_binding_ids
            ),
            "reused_row_binding_ids": list(
                self.reused_row_binding_ids
            ),
            "compiled_row_count": len(self.changed_row_binding_ids),
            "reused_row_count": len(self.reused_row_binding_ids),
            "full_proof_recompute_count": 1,
            "unchanged_source_digest_requires_byte_identical_row": True,
            "full_numerical_proof_recomputed_each_epoch": True,
            "operational_parent_validation": (
                "TRUSTED_SAME_PROCESS_IMMUTABLE_EPOCH_REGISTRY_V2"
            ),
            "operational_parent_registry_is_not_portable_verification": True,
            "operational_parent_deep_snapshot_sha256_verified": True,
            "portable_verifier_recursively_verifies_parent_chain": True,
            "portable_verifier_uses_full_control_prefix_replay_each_epoch": (
                True
            ),
            "portable_verifier_recompiles_root_and_changed_rows": True,
            "portable_verifier_inherits_unchanged_rows_from_verified_parent": (
                True
            ),
            "complete_support_freeze_required_per_row": True,
            "validation_epoch_set": [1],
            "operational_incremental_prefix_scope": (
                "TRUSTED_SAME_PROCESS_CONSTRUCTION_ONLY"
            ),
            "per_draw_records_used": False,
            "private_law_access": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def model_epoch_id(self) -> str:
        return self._model_epoch_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_sources": [item.to_document() for item in self.row_sources],
            "model": self.model.to_document(),
            "proof": self.proof.to_document(),
            "model_epoch_id": self.model_epoch_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _exact_prefix_inputs(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    controlled_appends: tuple[
        control.V075ControlledBatchAppendV2,
        ...,
    ],
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ],
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    parent_prefix: (
        control.V075OpenControlledBatchPrefixVerificationV2 | None
    ) = None,
    allow_trusted_owned_prefix: bool = False,
) -> tuple[
    backend.V075BatchNativeOccurrenceIdentityV1,
    tuple[control.V075ControlledBatchAppendV2, ...],
    tuple[control.V075ControlledCompleteSupportFreezeV2, ...],
    control.V075OpenControlledBatchPrefixVerificationV2,
]:
    identity = _replay_identity(occurrence_identity)
    if (
        type(controlled_appends) is not tuple
        or not controlled_appends
        or len(controlled_appends) > MAX_CONTROLLED_APPENDS
        or type(support_freezes) is not tuple
        or not support_freezes
    ):
        _fail("live model inputs are absent, untyped, or over cap")
    if (
        type(open_prefix_verification)
        is not control.V075OpenControlledBatchPrefixVerificationV2
        or identity.occurrence_id
        != open_prefix_verification.occurrence_id
        or tuple(
            item.receipt.receipt_id for item in controlled_appends
        )
        != open_prefix_verification.receipt_ids
        or tuple(item.freeze_id for item in support_freezes)
        != open_prefix_verification.support_freeze_ids
    ):
        _fail(
            "live model typed inputs differ from claimed prefix identities"
        )
    prefix = (
        control.validate_v075_trusted_owned_open_prefix_v2(
            claimed=open_prefix_verification,
            occurrence_identity=identity,
        )
        if allow_trusted_owned_prefix
        else _replay_open_prefix(open_prefix_verification)
    )
    appends = prefix.appends
    freezes = prefix.support_freezes
    if (
        tuple(item.receipt.receipt_id for item in controlled_appends)
        != prefix.receipt_ids
        or tuple(item.freeze_id for item in support_freezes)
        != prefix.support_freeze_ids
        or any(
            claimed is not replayed
            and claimed.to_document() != replayed.to_document()
            for claimed, replayed in zip(controlled_appends, appends)
        )
        or any(
            claimed is not replayed
            and claimed.to_document() != replayed.to_document()
            for claimed, replayed in zip(support_freezes, freezes)
        )
        or tuple(item.receipt.receipt_id for item in appends)
        != prefix.receipt_ids
        or tuple(item.freeze_id for item in freezes)
        != prefix.support_freeze_ids
        or identity.occurrence_id != prefix.occurrence_id
    ):
        _fail("live model inputs differ from their exact open prefix")
    for append in appends:
        request = append.batch.request
        stream = request.stream_identity
        if (
            request.occurrence_id != identity.occurrence_id
            or stream.target_tape_namespace_id
            != identity.target_tape_namespace_id
            or stream.context_id != identity.context_id
            or stream.arm != identity.arm.value
        ):
            _fail("live model append crossed occurrence, context, or arm")
    return identity, appends, freezes, prefix


def _validate_operational_parent(
    claimed: V075LiveIncrementalModelEpochV2,
) -> V075LiveIncrementalModelEpochV2:
    """Use factory provenance; portable full replay remains a separate API."""

    if type(claimed) is not V075LiveIncrementalModelEpochV2:
        _fail("operational parent is not one exact epoch")
    registration = _TRUSTED_SAME_PROCESS_EPOCHS.get(id(claimed))
    if (
        registration is None
        or registration[0] is not claimed
        or registration[1] != claimed.model_epoch_id
        or registration[2] != claimed.head_id
        or registration[3] != claimed.model.model_id
        or registration[4] != claimed.proof.proof_id
        or registration[5]
        != _deep_operational_epoch_snapshot_digest(claimed)
    ):
        _fail(
            "operational parent lacks trusted same-process immutable "
            "factory provenance"
        )
    return claimed


def _deep_operational_epoch_snapshot_digest(
    epoch: V075LiveIncrementalModelEpochV2,
) -> str:
    """Seal every nested field consumed by trusted incremental execution."""

    if (
        len(epoch.controlled_appends)
        != len(epoch.open_prefix_verification.appends)
        or any(
            left is not right
            for left, right in zip(
                epoch.controlled_appends,
                epoch.open_prefix_verification.appends,
            )
        )
        or len(epoch.support_freezes)
        != len(epoch.open_prefix_verification.support_freezes)
        or any(
            left is not right
            for left, right in zip(
                epoch.support_freezes,
                epoch.open_prefix_verification.support_freezes,
            )
        )
    ):
        _fail(
            "trusted epoch and open-prefix nested objects lost exact "
            "same-process alignment"
        )
    return control.same_process_structural_fingerprint_v2(epoch)


def _register_trusted_same_process_epoch(
    epoch: V075LiveIncrementalModelEpochV2,
) -> V075LiveIncrementalModelEpochV2:
    if len(_TRUSTED_SAME_PROCESS_EPOCHS) >= (
        _MAX_TRUSTED_SAME_PROCESS_EPOCHS
    ):
        _fail("trusted same-process live epoch registry reached its hard cap")
    _TRUSTED_SAME_PROCESS_EPOCHS[id(epoch)] = (
        epoch,
        epoch.model_epoch_id,
        epoch.head_id,
        epoch.model.model_id,
        epoch.proof.proof_id,
        _deep_operational_epoch_snapshot_digest(epoch),
    )
    return epoch


def _build_epoch(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    controlled_appends: tuple[
        control.V075ControlledBatchAppendV2,
        ...,
    ],
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ],
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    route: planning.V075PlanningRouteV2,
    parent_epoch: V075LiveIncrementalModelEpochV2 | None,
    replay_parent: bool,
    register_operational: bool,
    portable_prefix_replay: bool,
) -> V075LiveIncrementalModelEpochV2:
    if type(route) is not planning.V075PlanningRouteV2:
        _fail("live model route is not one exact registered route")
    identity_preview = _replay_identity(occurrence_identity)
    if (
        route is planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND
    ) != (
        identity_preview.arm
        is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ):
        _fail("live model route differs from its occurrence arm")
    parent = parent_epoch
    if parent is not None:
        if type(parent) is not V075LiveIncrementalModelEpochV2:
            _fail("live model parent is not one exact epoch")
        if replay_parent:
            parent = _validate_operational_parent(parent)
    identity, appends, freezes, prefix = _exact_prefix_inputs(
        occurrence_identity=occurrence_identity,
        controlled_appends=controlled_appends,
        support_freezes=support_freezes,
        open_prefix_verification=open_prefix_verification,
        parent_prefix=(
            None
            if parent is None
            else parent.open_prefix_verification
        ),
        allow_trusted_owned_prefix=not portable_prefix_replay,
    )

    collected = _collect_rows(
        occurrence_identity=identity,
        appends=appends,
        support_freezes=freezes,
        portable_replay=portable_prefix_replay,
    )
    parent_sources = (
        {}
        if parent is None
        else {item.row_binding_id: item for item in parent.row_sources}
    )
    parent_rows = (
        {}
        if parent is None
        else {item.row_binding_id: item for item in parent.model.rows}
    )
    current_bindings = {item.row_binding_id for item in collected}
    if parent is not None and not set(parent_sources) <= current_bindings:
        _fail("a live model prefix removed one parent numerical row")

    pairs: list[
        tuple[planning.V075NumericalRowV2, V075LiveModelRowSourceBindingV2]
    ] = []
    changed: list[str] = []
    reused: list[str] = []
    for item in collected:
        prior_source = parent_sources.get(item.row_binding_id)
        prior_row = parent_rows.get(item.row_binding_id)
        unchanged = (
            prior_source is not None
            and prior_row is not None
            and prior_source.source_digest == item.source_digest
        )
        recompiled = (
            _compile_numerical_row(
                occurrence_identity=identity,
                discovery=item.discovery_append,
                support_freeze=item.support_freeze,
                validations=item.validation_appends,
            )
            if not unchanged
            else None
        )
        if unchanged:
            numerical_row = prior_row
            reused.append(item.row_binding_id)
        else:
            if recompiled is None:  # pragma: no cover - guarded above
                _fail("changed live row was not compiled")
            numerical_row = recompiled
            changed.append(item.row_binding_id)
        pairs.append(
            (numerical_row, _row_source_binding(item, numerical_row))
        )
    ordered_pairs = tuple(
        sorted(pairs, key=lambda pair: pair[0].row_id)
    )
    rows = tuple(item[0] for item in ordered_pairs)
    row_sources = tuple(item[1] for item in ordered_pairs)
    context = rows[0]
    registered_context = planning._registered_context(  # noqa: SLF001
        context.context_id
    )
    model = planning.V075NumericalModelV2(
        planning._MODEL_ISSUER,  # noqa: SLF001
        registered_context,
        rows,
        "SIGNED_V2_AGGREGATES",
    )
    model = planning._replay_numerical_model(model)  # noqa: SLF001
    proof = planning.plan_v075_construction_numerical_model_v2(
        model=model,
        route=route,
    )
    epoch = V075LiveIncrementalModelEpochV2(
        _MODEL_EPOCH_ISSUER,
        identity,
        appends,
        freezes,
        prefix,
        parent,
        1 if parent is None else parent.epoch_index + 1,
        identity.context_id,
        identity.arm,
        prefix.current_head_id,
        route,
        row_sources,
        model,
        proof,
        tuple(sorted(changed)),
        tuple(sorted(reused)),
    )
    return (
        _register_trusted_same_process_epoch(epoch)
        if register_operational
        else epoch
    )


def freeze_v075_live_incremental_model_epoch_v2(
    *,
    occurrence_identity: backend.V075BatchNativeOccurrenceIdentityV1,
    controlled_appends: tuple[
        control.V075ControlledBatchAppendV2,
        ...,
    ],
    support_freezes: tuple[
        control.V075ControlledCompleteSupportFreezeV2,
        ...,
    ],
    open_prefix_verification: (
        control.V075OpenControlledBatchPrefixVerificationV2
    ),
    route: planning.V075PlanningRouteV2,
    parent_epoch: V075LiveIncrementalModelEpochV2 | None = None,
) -> V075LiveIncrementalModelEpochV2:
    """Compile and plan one exact observer-signed open-prefix model epoch."""

    try:
        return _build_epoch(
            occurrence_identity=occurrence_identity,
            controlled_appends=controlled_appends,
            support_freezes=support_freezes,
            open_prefix_verification=open_prefix_verification,
            route=route,
            parent_epoch=parent_epoch,
            replay_parent=True,
            register_operational=True,
            portable_prefix_replay=False,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        planning.V075BatchNativePlanningV2InvariantViolation,
    ) as error:
        if type(error) is V075LiveIncrementalModelV2InvariantViolation:
            raise
        raise V075LiveIncrementalModelV2InvariantViolation(
            "live model epoch construction failed"
        ) from error


def _replay_epoch(
    claimed: V075LiveIncrementalModelEpochV2,
    *,
    depth: int,
    seen_object_ids: frozenset[int],
) -> V075LiveIncrementalModelEpochV2:
    if (
        type(claimed) is not V075LiveIncrementalModelEpochV2
        or depth > MAX_MODEL_EPOCHS
        or id(claimed) in seen_object_ids
    ):
        _fail("live model epoch replay is untyped, cyclic, or over cap")
    # Reject stale cached source IDs before paying for recursive signatures or
    # numerical replay.  This is only a fail-fast screen; accepted epochs still
    # undergo the complete inductive verification below.
    tuple(_replay_row_source_binding(item) for item in claimed.row_sources)
    parent = (
        None
        if claimed.parent_epoch is None
        else _replay_epoch(
            claimed.parent_epoch,
            depth=depth + 1,
            seen_object_ids=seen_object_ids | {id(claimed)},
        )
    )
    replayed = _build_epoch(
        occurrence_identity=claimed.occurrence_identity,
        controlled_appends=claimed.controlled_appends,
        support_freezes=claimed.support_freezes,
        open_prefix_verification=claimed.open_prefix_verification,
        route=claimed.route,
        parent_epoch=parent,
        replay_parent=False,
        register_operational=False,
        portable_prefix_replay=True,
    )
    if (
        replayed.model_epoch_id != claimed.model_epoch_id
        or replayed.canonical_bytes != claimed.canonical_bytes
        or replayed.epoch_index != claimed.epoch_index
        or replayed.parent_epoch_id != claimed.parent_epoch_id
    ):
        _fail("live model epoch differs from exact reconstruction")
    return replayed


def replay_v075_live_incremental_model_epoch_v2(
    claimed: V075LiveIncrementalModelEpochV2,
) -> V075LiveIncrementalModelEpochV2:
    """Verify changed rows inductively and recompute every epoch proof."""

    try:
        return _replay_epoch(
            claimed,
            depth=1,
            seen_object_ids=frozenset(),
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        planning.V075BatchNativePlanningV2InvariantViolation,
    ) as error:
        if type(error) is V075LiveIncrementalModelV2InvariantViolation:
            raise
        raise V075LiveIncrementalModelV2InvariantViolation(
            "live model epoch exact replay failed"
        ) from error


@dataclass(frozen=True, slots=True)
class V075LiveIncrementalModelVerificationV2:
    """Content-addressed attestation of exact typed model-epoch replay."""

    _issuer: object = field(repr=False, compare=False)
    model_epoch_id: str
    parent_epoch_id: str | None
    head_id: str
    open_prefix_verification_id: str
    numerical_model_id: str
    numerical_proof_id: str
    row_source_binding_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.model_epoch_id, "verified live model epoch"),
            (self.head_id, "verified live model head"),
            (
                self.open_prefix_verification_id,
                "verified live model open prefix",
            ),
            (self.numerical_model_id, "verified live numerical model"),
            (self.numerical_proof_id, "verified live numerical proof"),
        ):
            _cid(value, label)
        if self.parent_epoch_id is not None:
            _cid(self.parent_epoch_id, "verified live parent epoch")
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.row_source_binding_ids) is not tuple
            or not self.row_source_binding_ids
            or any(
                _cid(value, "verified live row source") != value
                for value in self.row_source_binding_ids
            )
        ):
            _fail("live model verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_incremental_model_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_epoch_id": self.model_epoch_id,
            "parent_epoch_id": self.parent_epoch_id,
            "head_id": self.head_id,
            "open_prefix_verification_id": (
                self.open_prefix_verification_id
            ),
            "numerical_model_id": self.numerical_model_id,
            "numerical_proof_id": self.numerical_proof_id,
            "row_source_binding_ids": list(self.row_source_binding_ids),
            "parent_chain_exactly_replayed": True,
            "root_and_changed_rows_exactly_recompiled": True,
            "unchanged_rows_inherited_from_exact_parent": True,
            "numerical_proof_exactly_recomputed": True,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_live_incremental_model_epoch_bytes_v2(
    *,
    claimed: V075LiveIncrementalModelEpochV2,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveIncrementalModelEpochV2,
    V075LiveIncrementalModelVerificationV2,
]:
    """Replay one complete typed epoch chain and require canonical bytes."""

    document = _strict_document(claimed_bytes, "live model epoch")
    replayed = replay_v075_live_incremental_model_epoch_v2(claimed)
    if (
        set(document) != set(replayed.to_document())
        or claimed_bytes != replayed.canonical_bytes
    ):
        _fail("claimed live model epoch bytes differ from exact replay")
    verification = V075LiveIncrementalModelVerificationV2(
        _VERIFICATION_ISSUER,
        replayed.model_epoch_id,
        replayed.parent_epoch_id,
        replayed.head_id,
        replayed.open_prefix_verification.verification_id,
        replayed.model.model_id,
        replayed.proof.proof_id,
        tuple(item.binding_id for item in replayed.row_sources),
    )
    return replayed, verification


def execute_v075_production_live_incremental_model_v2(
    **_forbidden: Any,
) -> None:
    """Unconditional structural lock for the production-positive path."""

    raise V075LiveIncrementalModelProductionV2NotReady(PRODUCTION_BLOCKER)


__all__ = [
    "MAX_MODEL_EPOCHS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PROPOSED_CONTRACT_VERSION",
    "V075LiveIncrementalModelEpochV2",
    "V075LiveIncrementalModelProductionV2NotReady",
    "V075LiveIncrementalModelV2InvariantViolation",
    "V075LiveIncrementalModelVerificationV2",
    "V075LiveModelRowSourceBindingV2",
    "execute_v075_production_live_incremental_model_v2",
    "freeze_v075_live_incremental_model_epoch_v2",
    "replay_v075_live_incremental_model_epoch_v2",
    "verify_v075_live_incremental_model_epoch_bytes_v2",
]
