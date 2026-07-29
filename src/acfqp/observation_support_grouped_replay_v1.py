"""Semantics-preserving grouped raw-prefix replay for V0-068.

The legacy row verifier reconstructs one discovery/validation stream for
every immutable checkpoint row.  Campaign artifacts contain several
checkpoints of the same exact physical epoch-1 stream, so that approach
replays the same prefix repeatedly.  This module groups only rows whose
physical stream semantics are byte-for-byte identical, opens one fresh
uncached stream per group, and snapshots it at every requested checkpoint in
ascending order.

Every requested row is still reconstructed and compared in full.  The
returned :class:`GraphPartialSupportReplayVerificationV1` objects are exactly
the legacy objects, including their IDs and counter values.  Epoch-2 rows do
not expose a public incremental prefix builder and therefore remain complete
legacy singleton replays; they are never skipped or approximated.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
from multiprocessing import get_context
from typing import Any, Iterable, Mapping

from .phase3e_ids import canonical_json_bytes
from . import observation_support_graph_acquisition_v1 as acquisition
from . import observation_support_h2_closure_v1 as h2_closure
from . import partial_support_confidence_v1 as confidence
from . import transition_tuple_observer_v1 as observer


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_grouped_prefix_replay_v0"
MAX_REPLAY_WORKERS = 32
GROUPING_RULE = (
    "EXACT_EPOCH1_PHYSICAL_STREAM_SEMANTICS_ASCENDING_CHECKPOINTS"
)
EPOCH2_RULE = "FULL_LEGACY_SINGLETON_REPLAY_NO_SKIPPED_ROW"


class ObservationSupportGroupedReplayInvariantViolation(ValueError):
    """Raised when grouping or exact row replay cannot be justified."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except Exception as error:  # pragma: no cover - normalized boundary
        raise ObservationSupportGroupedReplayInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(
        f"acfqp:observation-support-grouped-replay:{role}:v1".encode(
            "utf-8"
        )
        + b"\x00"
        + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        )
    return value


def _workers(value: Any) -> int:
    if (
        type(value) is not int
        or isinstance(value, bool)
        or not 1 <= value <= MAX_REPLAY_WORKERS
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay worker count is outside the registered cap"
        )
    return value


def _registered_context(
    context: observer.PublicGraphContextV1,
) -> observer.PublicGraphContextV1:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay context is not exactly registered"
        )
    return context


def _canonical_catalogue(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
) -> observer.LegalActionCatalogueV1:
    if type(catalogue) is not observer.LegalActionCatalogueV1:
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay catalogue has the wrong concrete type"
        )
    expected = observer.legal_action_catalogue_v1(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if (
        catalogue != expected
        or catalogue.to_document() != expected.to_document()
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay catalogue is stale or noncanonical"
        )
    return expected


@dataclass(frozen=True, slots=True)
class GroupedRowReplayRequestV1:
    context: observer.PublicGraphContextV1
    catalogue: observer.LegalActionCatalogueV1
    row: acquisition.GraphPartialSupportRowV1

    def __post_init__(self) -> None:
        context = _registered_context(self.context)
        catalogue = _canonical_catalogue(context, self.catalogue)
        if (
            type(self.row) is not acquisition.GraphPartialSupportRowV1
            or self.row.binding.context_id != context.context_id
            or self.row.binding.catalogue_id != catalogue.catalogue_id
            or self.row.binding.state_id != catalogue.state.state_id
            or self.row.binding.remaining_horizon
            != catalogue.remaining_horizon
            or self.row.binding.action not in catalogue.actions
        ):
            raise ObservationSupportGroupedReplayInvariantViolation(
                "grouped replay request is stale, foreign, or illegal"
            )

    @property
    def partial_row_id(self) -> str:
        return self.row.partial_row_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.grouped_row_replay_request.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "partial_row_id": self.row.partial_row_id,
        }

    @property
    def request_id(self) -> str:
        return _content_id("request", self._payload())


def _epoch1_group_payload(
    request: GroupedRowReplayRequestV1,
) -> dict[str, Any]:
    row = request.row
    if row.support_epoch_index != 1:
        raise ObservationSupportGroupedReplayInvariantViolation(
            "only epoch-1 rows have a public incremental prefix stream"
        )
    if row.parent_row is not None or row.prior_validation_observation_ids:
        raise ObservationSupportGroupedReplayInvariantViolation(
            "epoch-1 grouped row unexpectedly has predecessor evidence"
        )
    return {
        "schema": "acfqp.grouped_row_replay_physical_stream.v1",
        "schema_version": SCHEMA_VERSION,
        "context_id": request.context.context_id,
        "catalogue_id": request.catalogue.catalogue_id,
        "row_binding_id": row.binding.row_id,
        "state_id": row.binding.state_id,
        "remaining_horizon": row.binding.remaining_horizon,
        "action": list(row.binding.action),
        "support_epoch_index": 1,
        "observer_epoch_ids": [
            item.epoch_id for item in row.observer_epoch_chain
        ],
        "support_epoch_id": row.support_epoch.support_epoch_id,
        "discovery_stream_domain_id": (
            row.support_epoch.discovery_evidence
            .discovery_stream_domain_id
        ),
        "validation_stream_domain_id": (
            row.support_epoch.validation_stream_domain_id
        ),
        "initial_discovery_observation_ids": list(
            row.initial_discovery_observation_ids
        ),
        "support_outcome_ids": list(
            row.support_epoch.support_outcome_ids
        ),
    }


def _group_id(request: GroupedRowReplayRequestV1) -> str:
    if request.row.support_epoch_index == 1:
        return _content_id(
            "physical_stream",
            _epoch1_group_payload(request),
        )
    # The public acquisition API has no incremental epoch-2 prefix object.
    # Bind the singleton to its full row identity and use the legacy verifier.
    return _content_id(
        "legacy_singleton",
        {
            "schema": "acfqp.grouped_row_replay_legacy_singleton.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": request.context.context_id,
            "catalogue_id": request.catalogue.catalogue_id,
            "partial_row_id": request.row.partial_row_id,
            "support_epoch_index": request.row.support_epoch_index,
            "rule": EPOCH2_RULE,
        },
    )


@dataclass(frozen=True, slots=True)
class _PhysicalReplayGroupV1:
    group_id: str
    requests: tuple[GroupedRowReplayRequestV1, ...]
    incrementally_grouped: bool

    def __post_init__(self) -> None:
        _cid(self.group_id, "physical replay group")
        if (
            type(self.requests) is not tuple
            or not self.requests
            or any(
                type(item) is not GroupedRowReplayRequestV1
                for item in self.requests
            )
            or type(self.incrementally_grouped) is not bool
            or any(_group_id(item) != self.group_id for item in self.requests)
        ):
            raise ObservationSupportGroupedReplayInvariantViolation(
                "physical replay group is malformed"
            )
        if self.incrementally_grouped:
            checkpoints = tuple(
                item.row.counters.current_validation_draws
                for item in self.requests
            )
            if (
                any(item.row.support_epoch_index != 1 for item in self.requests)
                or checkpoints != tuple(sorted(set(checkpoints)))
                or tuple(
                    item.row.partial_row_id for item in self.requests
                )
                != tuple(
                    item.row.partial_row_id
                    for item in sorted(
                        self.requests,
                        key=lambda request: (
                            request.row.counters.current_validation_draws,
                            request.row.partial_row_id,
                        ),
                    )
                )
            ):
                raise ObservationSupportGroupedReplayInvariantViolation(
                    "incremental group checkpoints are not unique and ascending"
                )
            _validate_epoch1_prefix_claims(self.requests)
        elif len(self.requests) != 1:
            raise ObservationSupportGroupedReplayInvariantViolation(
                "nonincremental replay groups must be exact singletons"
            )


def _validate_epoch1_prefix_claims(
    requests: tuple[GroupedRowReplayRequestV1, ...],
) -> None:
    first = requests[0].row
    discovery = first.initial_discovery_observation_ids
    support_epoch_document = first.support_epoch.to_document()
    support_descriptors = first.support_descriptors
    observer_epochs = tuple(
        item.to_document() for item in first.observer_epoch_chain
    )
    prior_validation: tuple[str, ...] = ()
    previous_validation: tuple[str, ...] = ()
    for request in requests:
        row = request.row
        current = row.current_validation_observation_ids
        if (
            row.initial_discovery_observation_ids != discovery
            or row.prior_validation_observation_ids != prior_validation
            or row.support_epoch.to_document() != support_epoch_document
            or row.support_descriptors != support_descriptors
            or tuple(
                item.to_document() for item in row.observer_epoch_chain
            )
            != observer_epochs
            or current[: len(previous_validation)] != previous_validation
            or len(current)
            != row.counters.current_validation_draws
        ):
            raise ObservationSupportGroupedReplayInvariantViolation(
                "claimed rows are not exact prefixes of one physical stream"
            )
        previous_validation = current


def _verification_from_rebuilt(
    claimed: acquisition.GraphPartialSupportRowV1,
    rebuilt: acquisition.GraphPartialSupportRowV1,
) -> acquisition.GraphPartialSupportReplayVerificationV1:
    if (
        rebuilt != claimed
        or rebuilt.to_document() != claimed.to_document()
        or canonical_json_bytes(rebuilt.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped prefix snapshot differs from claimed immutable row"
        )
    confidence_verification = (
        confidence.verify_partial_support_confidence_v1(
            rebuilt.confidence_authority
        )
    )
    return acquisition.GraphPartialSupportReplayVerificationV1(
        rebuilt.partial_row_id,
        rebuilt.physical_evidence_id,
        confidence_verification.verification_id,
        rebuilt.support_epoch_index,
        rebuilt.counters.total_observer_draws,
        rebuilt.counters.total_random_word_calls,
        rebuilt.counters.total_rejections,
    )


def _replay_group_v1(
    group: _PhysicalReplayGroupV1,
) -> tuple[
    tuple[
        str,
        acquisition.GraphPartialSupportReplayVerificationV1,
    ],
    ...,
]:
    if not group.incrementally_grouped:
        request = group.requests[0]
        verification = acquisition.verify_graph_partial_support_row_v1(
            request.context,
            request.catalogue,
            request.row.binding.action,
            request.row,
        )
        return ((request.row.partial_row_id, verification),)

    first = group.requests[0]
    stream = acquisition.open_graph_partial_support_prefix_v1(
        first.context,
        first.catalogue,
        first.row.binding.action,
    )
    bindings: list[
        tuple[
            str,
            acquisition.GraphPartialSupportReplayVerificationV1,
        ]
    ] = []
    for request in group.requests:
        rebuilt = stream.extend_validation_to(
            request.row.counters.current_validation_draws
        )
        verification = _verification_from_rebuilt(request.row, rebuilt)
        bindings.append((request.row.partial_row_id, verification))
    return tuple(bindings)


@dataclass(frozen=True, slots=True)
class GroupedReplayBindingV1:
    partial_row_id: str
    physical_group_id: str
    verification: acquisition.GraphPartialSupportReplayVerificationV1

    def __post_init__(self) -> None:
        _cid(self.partial_row_id, "grouped replay partial row")
        _cid(self.physical_group_id, "grouped replay physical group")
        if (
            type(self.verification)
            is not acquisition.GraphPartialSupportReplayVerificationV1
            or self.verification.partial_row_id != self.partial_row_id
        ):
            raise ObservationSupportGroupedReplayInvariantViolation(
                "grouped replay binding does not attest its exact row"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.grouped_row_replay_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "partial_row_id": self.partial_row_id,
            "physical_group_id": self.physical_group_id,
            "verification_id": self.verification.verification_id,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class GroupedPrefixReplayResultV1:
    bindings: tuple[GroupedReplayBindingV1, ...]
    requested_row_count: int
    physical_stream_group_count: int
    incremental_epoch1_group_count: int
    legacy_singleton_group_count: int
    logical_replay_observer_draws: int
    physical_replay_observer_draws: int
    saved_replay_observer_draws: int
    all_rows_replayed: bool = True
    exact_verification_identity_preserved: bool = True
    persistent_cache_used: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.bindings) is not tuple
            or not self.bindings
            or any(
                type(item) is not GroupedReplayBindingV1
                for item in self.bindings
            )
            or tuple(item.partial_row_id for item in self.bindings)
            != tuple(
                sorted({item.partial_row_id for item in self.bindings})
            )
            or self.requested_row_count != len(self.bindings)
            or self.physical_stream_group_count
            != len({item.physical_group_id for item in self.bindings})
            or self.physical_stream_group_count
            != (
                self.incremental_epoch1_group_count
                + self.legacy_singleton_group_count
            )
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.logical_replay_observer_draws,
                    self.physical_replay_observer_draws,
                    self.saved_replay_observer_draws,
                )
            )
            or self.saved_replay_observer_draws
            != (
                self.logical_replay_observer_draws
                - self.physical_replay_observer_draws
            )
            or self.physical_replay_observer_draws
            > self.logical_replay_observer_draws
            or self.all_rows_replayed is not True
            or self.exact_verification_identity_preserved is not True
            or self.persistent_cache_used is not False
        ):
            raise ObservationSupportGroupedReplayInvariantViolation(
                "grouped prefix replay result does not reconcile"
            )

    @property
    def verification_by_partial_row_id(
        self,
    ) -> dict[
        str,
        acquisition.GraphPartialSupportReplayVerificationV1,
    ]:
        return {
            item.partial_row_id: item.verification
            for item in self.bindings
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.grouped_prefix_replay_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "binding_ids": [item.binding_id for item in self.bindings],
            "requested_row_count": self.requested_row_count,
            "physical_stream_group_count": (
                self.physical_stream_group_count
            ),
            "incremental_epoch1_group_count": (
                self.incremental_epoch1_group_count
            ),
            "legacy_singleton_group_count": (
                self.legacy_singleton_group_count
            ),
            "logical_replay_observer_draws": (
                self.logical_replay_observer_draws
            ),
            "physical_replay_observer_draws": (
                self.physical_replay_observer_draws
            ),
            "saved_replay_observer_draws": (
                self.saved_replay_observer_draws
            ),
            "all_rows_replayed": True,
            "exact_verification_identity_preserved": True,
            "persistent_cache_used": False,
            "grouping_rule": GROUPING_RULE,
            "epoch2_rule": EPOCH2_RULE,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "bindings": [item.to_document() for item in self.bindings],
            "result_id": self.result_id,
        }


def _canonical_requests(
    requests: Iterable[GroupedRowReplayRequestV1],
) -> tuple[GroupedRowReplayRequestV1, ...]:
    values = tuple(requests)
    if (
        not values
        or any(
            type(item) is not GroupedRowReplayRequestV1
            for item in values
        )
        or len({item.partial_row_id for item in values}) != len(values)
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay requires nonempty distinct typed row requests"
        )
    return tuple(sorted(values, key=lambda item: item.partial_row_id))


def _physical_groups(
    requests: tuple[GroupedRowReplayRequestV1, ...],
) -> tuple[_PhysicalReplayGroupV1, ...]:
    by_group: dict[str, list[GroupedRowReplayRequestV1]] = {}
    for request in requests:
        by_group.setdefault(_group_id(request), []).append(request)
    groups: list[_PhysicalReplayGroupV1] = []
    for group_id in sorted(by_group):
        members = by_group[group_id]
        incremental = all(
            item.row.support_epoch_index == 1 for item in members
        )
        ordered = tuple(
            sorted(
                members,
                key=lambda item: (
                    item.row.counters.current_validation_draws,
                    item.row.partial_row_id,
                ),
            )
        )
        groups.append(
            _PhysicalReplayGroupV1(
                group_id,
                ordered,
                incremental,
            )
        )
    return tuple(groups)


def grouped_verify_graph_partial_support_rows_v1(
    requests: Iterable[GroupedRowReplayRequestV1],
    *,
    max_workers: int = 1,
) -> GroupedPrefixReplayResultV1:
    """Replay every row while sharing exact epoch-1 physical prefixes."""

    canonical = _canonical_requests(requests)
    workers = _workers(max_workers)
    groups = _physical_groups(canonical)
    if workers == 1 or len(groups) == 1:
        replayed_groups = tuple(_replay_group_v1(item) for item in groups)
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(groups)),
            mp_context=get_context("spawn"),
        ) as executor:
            replayed_groups = tuple(
                executor.map(_replay_group_v1, groups)
            )
    verification_by_row = {
        row_id: verification
        for group in replayed_groups
        for row_id, verification in group
    }
    if set(verification_by_row) != {
        item.partial_row_id for item in canonical
    }:
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped replay skipped or duplicated a requested row"
        )
    group_by_row = {
        request.partial_row_id: group.group_id
        for group in groups
        for request in group.requests
    }
    bindings = tuple(
        GroupedReplayBindingV1(
            row_id,
            group_by_row[row_id],
            verification_by_row[row_id],
        )
        for row_id in sorted(verification_by_row)
    )
    logical_draws = sum(
        item.row.counters.total_observer_draws for item in canonical
    )
    physical_draws = sum(
        (
            max(
                item.row.counters.total_observer_draws
                for item in group.requests
            )
            if group.incrementally_grouped
            else group.requests[0].row.counters.total_observer_draws
        )
        for group in groups
    )
    return GroupedPrefixReplayResultV1(
        bindings,
        len(canonical),
        len(groups),
        sum(item.incrementally_grouped for item in groups),
        sum(not item.incrementally_grouped for item in groups),
        logical_draws,
        physical_draws,
        logical_draws - physical_draws,
    )


def verify_observation_support_h2_closure_from_grouped_rows_v1(
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
    verification_by_partial_row_id: Mapping[
        str,
        acquisition.GraphPartialSupportReplayVerificationV1,
    ],
) -> h2_closure.ObservationSupportH2ClosureReplayVerificationV1:
    """Rebuild one legacy closure verification from exact row replays.

    The returned object has the same schema, document, and content ID as
    :func:`verify_observation_support_h2_closure_v1`.  Extra entries in the
    campaign-wide mapping are ignored; every row belonging to ``closure`` is
    nevertheless required and reconciled against the closure counters.
    """

    registered = _registered_context(context)
    if (
        type(closure) is not h2_closure.ObservationSupportH2ClosureV1
        or closure.context != registered
        or not isinstance(verification_by_partial_row_id, Mapping)
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped closure replay requires one exact registered closure"
        )
    reconstructed = h2_closure.ObservationSupportH2ClosureV1(
        closure.context,
        closure.validation_checkpoint,
        closure.root_catalogue,
        closure.child_catalogues,
        closure.root_rows,
        closure.child_rows,
        closure.counters,
    )
    if (
        reconstructed.closure_id != closure.closure_id
        or canonical_json_bytes(reconstructed.to_document())
        != canonical_json_bytes(closure.to_document())
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "closure failed canonical reconstruction before grouped replay"
        )
    rows = tuple(
        sorted(closure.all_rows, key=lambda item: item.partial_row_id)
    )
    try:
        row_replays = tuple(
            verification_by_partial_row_id[row.partial_row_id]
            for row in rows
        )
    except (KeyError, TypeError) as error:
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped closure replay is missing one required row"
        ) from error
    if (
        any(
            type(replay)
            is not acquisition.GraphPartialSupportReplayVerificationV1
            or replay.partial_row_id != row.partial_row_id
            for row, replay in zip(rows, row_replays)
        )
        or sum(item.replayed_observer_draws for item in row_replays)
        != closure.counters.total_observer_draws
        or sum(item.replayed_random_word_calls for item in row_replays)
        != closure.counters.total_random_word_calls
        or sum(item.replayed_rejections for item in row_replays)
        != closure.counters.total_rejections
    ):
        raise ObservationSupportGroupedReplayInvariantViolation(
            "grouped row replays do not reconcile with closure counters"
        )
    bindings = tuple(
        (row.partial_row_id, replay.verification_id)
        for row, replay in zip(rows, row_replays)
    )
    return h2_closure.ObservationSupportH2ClosureReplayVerificationV1(
        registered.context_id,
        closure.closure_id,
        closure.validation_checkpoint,
        bindings,
        closure.counters.total_observer_draws,
        closure.counters.total_random_word_calls,
        closure.counters.total_rejections,
    )


__all__ = [
    "CONTRACT_VERSION",
    "EPOCH2_RULE",
    "GROUPING_RULE",
    "GroupedPrefixReplayResultV1",
    "GroupedReplayBindingV1",
    "GroupedRowReplayRequestV1",
    "MAX_REPLAY_WORKERS",
    "ObservationSupportGroupedReplayInvariantViolation",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "grouped_verify_graph_partial_support_rows_v1",
    "verify_observation_support_h2_closure_from_grouped_rows_v1",
]
