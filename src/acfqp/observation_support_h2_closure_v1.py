"""Observation-only H=2 acquisition closure for V0-068.

The closure first acquires every legal root state-action row.  Only active
successor states frozen by those rows' discovery support are then admitted
to the current support epoch.  For each admitted successor, the public legal
action catalogue is constructed at remaining horizon one and every legal
child row is acquired.

Validation-only novel outcomes remain represented by ``OTHER``.  They never
expand this immutable closure.  Row acquisition may be scheduled in separate
processes, but scheduling is deliberately absent from all evidence
identities: one-worker and many-worker executions produce the same canonical
bundle.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
import hashlib
from multiprocessing import get_context
from threading import Lock
from typing import Any, Iterable, Mapping

import acfqp.observation_support_graph_acquisition_v1 as graph_acquisition
import acfqp.transition_tuple_observer_v1 as transition_observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_h2_closure_v0"
REGISTERED_HORIZON = 2
MAX_PROCESS_WORKERS = 192

CHILD_DISCOVERY_RULE = (
    "ROOT_DISCOVERY_SUPPORT_ACTIVE_NONTERMINAL_SUCCESSORS_ONLY"
)
VALIDATION_NOVEL_RULE = (
    "VALIDATION_NOVEL_OUTCOMES_REMAIN_OTHER_AND_DO_NOT_EXPAND_EPOCH"
)
PHYSICAL_EVIDENCE_RULE = (
    "ROUTE_INDEPENDENT_ROWS_SHARED_BY_DIRECT_AND_QUOTIENT_CONSUMERS"
)


class ObservationSupportH2ClosureInvariantViolation(ValueError):
    """A closure identity, support boundary, or work record is invalid."""


DOMAIN_TAGS = {
    "counters": "acfqp:observation-support-h2-closure-counters:v1",
    "bundle": "acfqp:observation-support-h2-closure-bundle:v1",
    "charge": "acfqp:observation-support-h2-closure-logical-charge:v1",
    "semantic_replay": (
        "acfqp:observation-support-h2-closure-semantic-replay:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("H2 closure content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportH2ClosureInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportH2ClosureInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _registered_context(
    context: Any,
) -> transition_observer.PublicGraphContextV1:
    if (
        type(context) is not transition_observer.PublicGraphContextV1
        or context
        not in transition_observer.registered_public_graph_contexts_v1()
        or context.horizon != REGISTERED_HORIZON
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "H2 closure requires one exact registered public context"
        )
    return context


def _checkpoint(value: Any) -> int:
    if (
        type(value) is not int
        or value not in graph_acquisition.VALIDATION_CHECKPOINTS
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "validation draw count is not a registered checkpoint"
        )
    return value


def _workers(value: Any) -> int:
    if (
        type(value) is not int
        or not 1 <= value <= MAX_PROCESS_WORKERS
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "max_workers must be an integer in the registered range"
        )
    return value


def _sorted_catalogues(
    values: Iterable[transition_observer.LegalActionCatalogueV1],
) -> tuple[transition_observer.LegalActionCatalogueV1, ...]:
    output = tuple(sorted(values, key=lambda item: item.catalogue_id))
    if (
        any(
            type(item) is not transition_observer.LegalActionCatalogueV1
            for item in output
        )
        or tuple(item.catalogue_id for item in output)
        != tuple(sorted({item.catalogue_id for item in output}))
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "child catalogues must be unique and content-ID sorted"
        )
    return output


def _sorted_rows(
    values: Iterable[graph_acquisition.GraphPartialSupportRowV1],
) -> tuple[graph_acquisition.GraphPartialSupportRowV1, ...]:
    output = tuple(sorted(values, key=lambda item: item.binding.row_id))
    if (
        any(
            type(item) is not graph_acquisition.GraphPartialSupportRowV1
            for item in output
        )
        or tuple(item.binding.row_id for item in output)
        != tuple(sorted({item.binding.row_id for item in output}))
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "closure rows must be unique and binding-ID sorted"
        )
    return output


def _active_discovery_states(
    root_rows: tuple[graph_acquisition.GraphPartialSupportRowV1, ...],
) -> tuple[transition_observer.SymbolicGraphStateV1, ...]:
    by_id: dict[str, transition_observer.SymbolicGraphStateV1] = {}
    for row in root_rows:
        for descriptor in row.support_descriptors:
            if descriptor.failure or descriptor.terminal:
                continue
            state = descriptor.next_state
            prior = by_id.setdefault(state.state_id, state)
            if canonical_json_bytes(prior.to_document()) != (
                canonical_json_bytes(state.to_document())
            ):
                raise ObservationSupportH2ClosureInvariantViolation(
                    "one state identity has conflicting symbolic documents"
                )
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(frozen=True, slots=True)
class ObservationSupportH2ClosureCountersV1:
    root_catalogue_count: int
    child_catalogue_count: int
    root_action_row_count: int
    child_action_row_count: int
    total_action_row_count: int
    discovery_known_active_descriptor_count: int
    discovery_known_child_state_count: int
    support_descriptor_count: int
    validation_novel_descriptor_count: int
    initial_discovery_draws: int
    prior_validation_draws: int
    current_validation_draws: int
    total_observer_draws: int
    discovery_random_word_calls: int
    discovery_rejections: int
    prior_validation_random_word_calls: int
    prior_validation_rejections: int
    current_validation_random_word_calls: int
    current_validation_rejections: int
    total_random_word_calls: int
    total_rejections: int
    validation_novel_child_expansions: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, field)
            for field in self.__dataclass_fields__
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.root_catalogue_count != 1
            or self.total_action_row_count
            != self.root_action_row_count + self.child_action_row_count
            or self.discovery_known_child_state_count
            != self.child_catalogue_count
            or self.initial_discovery_draws
            != (
                graph_acquisition.DISCOVERY_DRAW_COUNT
                * self.total_action_row_count
            )
            or self.total_observer_draws
            != (
                self.initial_discovery_draws
                + self.prior_validation_draws
                + self.current_validation_draws
            )
            or self.discovery_random_word_calls
            != self.initial_discovery_draws + self.discovery_rejections
            or self.prior_validation_random_word_calls
            != self.prior_validation_draws
            + self.prior_validation_rejections
            or self.current_validation_random_word_calls
            != self.current_validation_draws
            + self.current_validation_rejections
            or self.total_random_word_calls
            != (
                self.discovery_random_word_calls
                + self.prior_validation_random_word_calls
                + self.current_validation_random_word_calls
            )
            or self.total_rejections
            != (
                self.discovery_rejections
                + self.prior_validation_rejections
                + self.current_validation_rejections
            )
            or self.validation_novel_child_expansions != 0
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure native counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_h2_closure_counters.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
        }

    @property
    def counters_id(self) -> str:
        return _content_id("counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


def _aggregate_counters(
    root_rows: tuple[graph_acquisition.GraphPartialSupportRowV1, ...],
    child_catalogues: tuple[
        transition_observer.LegalActionCatalogueV1,
        ...,
    ],
    child_rows: tuple[graph_acquisition.GraphPartialSupportRowV1, ...],
) -> ObservationSupportH2ClosureCountersV1:
    rows = (*root_rows, *child_rows)
    native = tuple(row.counters for row in rows)
    return ObservationSupportH2ClosureCountersV1(
        root_catalogue_count=1,
        child_catalogue_count=len(child_catalogues),
        root_action_row_count=len(root_rows),
        child_action_row_count=len(child_rows),
        total_action_row_count=len(rows),
        discovery_known_active_descriptor_count=sum(
            1
            for row in root_rows
            for descriptor in row.support_descriptors
            if not descriptor.failure and not descriptor.terminal
        ),
        discovery_known_child_state_count=len(child_catalogues),
        support_descriptor_count=sum(
            len(row.support_descriptors) for row in rows
        ),
        validation_novel_descriptor_count=sum(
            len(row.novel_descriptors) for row in rows
        ),
        initial_discovery_draws=sum(
            item.initial_discovery_draws for item in native
        ),
        prior_validation_draws=sum(
            item.prior_validation_draws for item in native
        ),
        current_validation_draws=sum(
            item.current_validation_draws for item in native
        ),
        total_observer_draws=sum(
            item.total_observer_draws for item in native
        ),
        discovery_random_word_calls=sum(
            item.discovery_random_word_calls for item in native
        ),
        discovery_rejections=sum(
            item.discovery_rejections for item in native
        ),
        prior_validation_random_word_calls=sum(
            item.prior_validation_random_word_calls for item in native
        ),
        prior_validation_rejections=sum(
            item.prior_validation_rejections for item in native
        ),
        current_validation_random_word_calls=sum(
            item.current_validation_random_word_calls for item in native
        ),
        current_validation_rejections=sum(
            item.current_validation_rejections for item in native
        ),
        total_random_word_calls=sum(
            item.total_random_word_calls for item in native
        ),
        total_rejections=sum(item.total_rejections for item in native),
    )


def _row_ref(
    row: graph_acquisition.GraphPartialSupportRowV1,
) -> dict[str, Any]:
    return {
        "partial_row_id": row.partial_row_id,
        "row_binding_id": row.binding.row_id,
        "catalogue_id": row.binding.catalogue_id,
        "state_id": row.binding.state_id,
        "action": list(row.binding.action),
        "remaining_horizon": row.binding.remaining_horizon,
        "physical_evidence_id": row.physical_evidence_id,
        "support_epoch_id": row.support_epoch.support_epoch_id,
        "confidence_authority_id": row.confidence_authority.authority_id,
        "counters_id": row.counters.counters_id,
    }


@dataclass(frozen=True, slots=True)
class ObservationSupportH2ClosureV1:
    context: transition_observer.PublicGraphContextV1
    validation_checkpoint: int
    root_catalogue: transition_observer.LegalActionCatalogueV1
    child_catalogues: tuple[
        transition_observer.LegalActionCatalogueV1,
        ...,
    ]
    root_rows: tuple[graph_acquisition.GraphPartialSupportRowV1, ...]
    child_rows: tuple[graph_acquisition.GraphPartialSupportRowV1, ...]
    counters: ObservationSupportH2ClosureCountersV1
    observation_only: bool = True
    current_support_epoch_index: int = 1
    validation_novel_child_expansion_allowed: bool = False
    route_independent_physical_evidence: bool = True

    def __post_init__(self) -> None:
        context = _registered_context(self.context)
        checkpoint = _checkpoint(self.validation_checkpoint)
        if (
            type(self.root_catalogue)
            is not transition_observer.LegalActionCatalogueV1
            or type(self.child_catalogues) is not tuple
            or type(self.root_rows) is not tuple
            or type(self.child_rows) is not tuple
            or type(self.counters)
            is not ObservationSupportH2ClosureCountersV1
            or self.observation_only is not True
            or self.current_support_epoch_index != 1
            or self.validation_novel_child_expansion_allowed is not False
            or self.route_independent_physical_evidence is not True
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure has an invalid concrete schema"
            )
        expected_root = transition_observer.legal_action_catalogue_v1(
            context,
            transition_observer.root_state_v1(context),
            REGISTERED_HORIZON,
        )
        if self.root_catalogue.to_document() != expected_root.to_document():
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure root catalogue is not canonical"
            )
        catalogues = _sorted_catalogues(self.child_catalogues)
        root_rows = _sorted_rows(self.root_rows)
        child_rows = _sorted_rows(self.child_rows)
        if (
            catalogues != self.child_catalogues
            or root_rows != self.root_rows
            or child_rows != self.child_rows
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure members are not canonically sorted"
            )
        expected_states = _active_discovery_states(root_rows)
        expected_catalogues = _sorted_catalogues(
            transition_observer.legal_action_catalogue_v1(
                context,
                state,
                1,
            )
            for state in expected_states
        )
        if tuple(
            item.to_document() for item in catalogues
        ) != tuple(item.to_document() for item in expected_catalogues):
            raise ObservationSupportH2ClosureInvariantViolation(
                "child closure differs from root discovery-known support"
            )
        expected_root_bindings = {
            (self.root_catalogue.catalogue_id, action)
            for action in self.root_catalogue.actions
        }
        actual_root_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in root_rows
        }
        expected_child_bindings = {
            (catalogue.catalogue_id, action)
            for catalogue in catalogues
            for action in catalogue.actions
        }
        actual_child_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in child_rows
        }
        rows = (*root_rows, *child_rows)
        if (
            actual_root_bindings != expected_root_bindings
            or len(actual_root_bindings) != len(root_rows)
            or actual_child_bindings != expected_child_bindings
            or len(actual_child_bindings) != len(child_rows)
            or any(
                row.binding.context_id != context.context_id
                or row.support_epoch_index != 1
                or row.counters.current_validation_draws != checkpoint
                or not row.route_independent_physical_prefix
                for row in rows
            )
            or any(
                row.binding.remaining_horizon != REGISTERED_HORIZON
                for row in root_rows
            )
            or any(
                row.binding.remaining_horizon != 1 for row in child_rows
            )
            or len({row.physical_evidence_id for row in rows}) != len(rows)
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure does not contain every required physical row"
            )
        expected_counters = _aggregate_counters(
            root_rows,
            catalogues,
            child_rows,
        )
        if self.counters != expected_counters:
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure counters differ from native row counters"
            )

    @property
    def all_rows(
        self,
    ) -> tuple[graph_acquisition.GraphPartialSupportRowV1, ...]:
        return (*self.root_rows, *self.child_rows)

    @property
    def physical_evidence_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(row.physical_evidence_id for row in self.all_rows)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_h2_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "validation_checkpoint": self.validation_checkpoint,
            "root_catalogue_id": self.root_catalogue.catalogue_id,
            "child_catalogue_ids": [
                item.catalogue_id for item in self.child_catalogues
            ],
            "root_partial_row_ids": [
                item.partial_row_id for item in self.root_rows
            ],
            "child_partial_row_ids": [
                item.partial_row_id for item in self.child_rows
            ],
            "physical_evidence_ids": list(self.physical_evidence_ids),
            "counters_id": self.counters.counters_id,
            "observation_only": True,
            "current_support_epoch_index": 1,
            "child_discovery_rule": CHILD_DISCOVERY_RULE,
            "validation_novel_rule": VALIDATION_NOVEL_RULE,
            "validation_novel_child_expansion_allowed": False,
            "route_independent_physical_evidence": True,
            "physical_evidence_rule": PHYSICAL_EVIDENCE_RULE,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("bundle", self._payload())

    @property
    def physical_bundle_id(self) -> str:
        return self.closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "context": self.context.to_document(),
            "root_catalogue": self.root_catalogue.to_document(),
            "child_catalogues": [
                item.to_document() for item in self.child_catalogues
            ],
            "root_row_refs": [_row_ref(item) for item in self.root_rows],
            "child_row_refs": [_row_ref(item) for item in self.child_rows],
            "counters": self.counters.to_document(),
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class _RowTaskV1:
    context: transition_observer.PublicGraphContextV1
    catalogue: transition_observer.LegalActionCatalogueV1
    action: tuple[int, int, int]
    checkpoint: int


@dataclass(frozen=True, slots=True)
class _RowReplayTaskV1:
    context: transition_observer.PublicGraphContextV1
    catalogue: transition_observer.LegalActionCatalogueV1
    action: tuple[int, int, int]
    row: graph_acquisition.GraphPartialSupportRowV1


def _acquire_row_task_v1(
    task: _RowTaskV1,
) -> graph_acquisition.GraphPartialSupportRowV1:
    return graph_acquisition.acquire_graph_partial_support_row_v1(
        task.context,
        task.catalogue,
        task.action,
        task.checkpoint,
    )


def _replay_row_task_v1(
    task: _RowReplayTaskV1,
) -> graph_acquisition.GraphPartialSupportReplayVerificationV1:
    return graph_acquisition.verify_graph_partial_support_row_v1(
        task.context,
        task.catalogue,
        task.action,
        task.row,
    )


def _run_tasks_serial_v1(
    tasks: tuple[_RowTaskV1, ...],
) -> tuple[graph_acquisition.GraphPartialSupportRowV1, ...]:
    return tuple(_acquire_row_task_v1(task) for task in tasks)


def _run_tasks_parallel_v1(
    executor: ProcessPoolExecutor,
    tasks: tuple[_RowTaskV1, ...],
) -> tuple[graph_acquisition.GraphPartialSupportRowV1, ...]:
    if not tasks:
        return ()
    return tuple(executor.map(_acquire_row_task_v1, tasks))


def _root_tasks(
    context: transition_observer.PublicGraphContextV1,
    catalogue: transition_observer.LegalActionCatalogueV1,
    checkpoint: int,
) -> tuple[_RowTaskV1, ...]:
    return tuple(
        _RowTaskV1(context, catalogue, action, checkpoint)
        for action in catalogue.actions
    )


def _child_tasks(
    context: transition_observer.PublicGraphContextV1,
    catalogues: tuple[transition_observer.LegalActionCatalogueV1, ...],
    checkpoint: int,
) -> tuple[_RowTaskV1, ...]:
    return tuple(
        _RowTaskV1(context, catalogue, action, checkpoint)
        for catalogue in catalogues
        for action in catalogue.actions
    )


_CLOSURE_CACHE: dict[
    tuple[str, int],
    ObservationSupportH2ClosureV1,
] = {}
_CLOSURE_CACHE_LOCK = Lock()


def clear_observation_support_h2_closure_cache_v1() -> None:
    """Clear only the route-independent in-process closure cache."""

    with _CLOSURE_CACHE_LOCK:
        _CLOSURE_CACHE.clear()


def _cached_closure(
    context_id: str,
    checkpoint: int,
) -> ObservationSupportH2ClosureV1 | None:
    with _CLOSURE_CACHE_LOCK:
        return _CLOSURE_CACHE.get((context_id, checkpoint))


def _store_closure(
    closure: ObservationSupportH2ClosureV1,
) -> ObservationSupportH2ClosureV1:
    key = (closure.context.context_id, closure.validation_checkpoint)
    with _CLOSURE_CACHE_LOCK:
        prior = _CLOSURE_CACHE.setdefault(key, closure)
    if prior.closure_id != closure.closure_id:
        raise ObservationSupportH2ClosureInvariantViolation(
            "route-independent closure replay changed its identity"
        )
    return prior


def acquire_observation_support_h2_closure_v1(
    context: transition_observer.PublicGraphContextV1,
    validation_checkpoint: int = (
        graph_acquisition.VALIDATION_CHECKPOINTS[0]
    ),
    max_workers: int = 1,
) -> ObservationSupportH2ClosureV1:
    """Acquire the complete discovery-known H=2 physical row closure."""

    registered = _registered_context(context)
    checkpoint = _checkpoint(validation_checkpoint)
    workers = _workers(max_workers)
    cached = _cached_closure(registered.context_id, checkpoint)
    if cached is not None:
        return cached

    root_catalogue = transition_observer.legal_action_catalogue_v1(
        registered,
        transition_observer.root_state_v1(registered),
        REGISTERED_HORIZON,
    )
    root_tasks = _root_tasks(registered, root_catalogue, checkpoint)
    if workers == 1:
        root_rows = _sorted_rows(_run_tasks_serial_v1(root_tasks))
        child_catalogues = _sorted_catalogues(
            transition_observer.legal_action_catalogue_v1(
                registered,
                state,
                1,
            )
            for state in _active_discovery_states(root_rows)
        )
        child_rows = _sorted_rows(
            _run_tasks_serial_v1(
                _child_tasks(registered, child_catalogues, checkpoint)
            )
        )
    else:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=get_context("spawn"),
        ) as executor:
            root_rows = _sorted_rows(
                _run_tasks_parallel_v1(executor, root_tasks)
            )
            child_catalogues = _sorted_catalogues(
                transition_observer.legal_action_catalogue_v1(
                    registered,
                    state,
                    1,
                )
                for state in _active_discovery_states(root_rows)
            )
            child_rows = _sorted_rows(
                _run_tasks_parallel_v1(
                    executor,
                    _child_tasks(
                        registered,
                        child_catalogues,
                        checkpoint,
                    ),
                )
            )
    counters = _aggregate_counters(
        root_rows,
        child_catalogues,
        child_rows,
    )
    return _store_closure(
        ObservationSupportH2ClosureV1(
            registered,
            checkpoint,
            root_catalogue,
            child_catalogues,
            root_rows,
            child_rows,
            counters,
        )
    )


@dataclass(frozen=True, slots=True)
class ObservationSupportH2ClosureReplayVerificationV1:
    """Same-implementation raw-prefix replay for every closure row."""

    context_id: str
    closure_id: str
    validation_checkpoint: int
    row_replay_bindings: tuple[tuple[str, str], ...]
    replayed_observer_draws: int
    replayed_random_word_calls: int
    replayed_rejections: int
    exact_atom_enumerator_calls: int = 0
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = (
        transition_observer.STATISTICAL_CLAIM_SCOPE
    )
    formal_exact_iid_plan_certificate: bool = False
    independent_algorithm_implementation: bool = False
    verification_result: str = (
        "VALID_SAME_IMPLEMENTATION_RAW_PREFIX_CLOSURE_REPLAY"
    )

    def __post_init__(self) -> None:
        _cid(self.context_id, "replay context")
        _cid(self.closure_id, "replay closure")
        bindings = self.row_replay_bindings
        if (
            type(self.validation_checkpoint) is not int
            or self.validation_checkpoint
            not in graph_acquisition.VALIDATION_CHECKPOINTS
            or type(bindings) is not tuple
            or not bindings
            or any(
                type(item) is not tuple
                or len(item) != 2
                or _cid(item[0], "replayed partial row") != item[0]
                or _cid(item[1], "row replay verification") != item[1]
                for item in bindings
            )
            or bindings
            != tuple(sorted(bindings, key=lambda item: item[0]))
            or len({item[0] for item in bindings}) != len(bindings)
            or type(self.replayed_observer_draws) is not int
            or self.replayed_observer_draws <= 0
            or type(self.replayed_random_word_calls) is not int
            or self.replayed_random_word_calls < self.replayed_observer_draws
            or type(self.replayed_rejections) is not int
            or self.replayed_rejections < 0
            or self.replayed_random_word_calls
            != self.replayed_observer_draws + self.replayed_rejections
            or self.exact_atom_enumerator_calls != 0
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope
            != transition_observer.STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
            or self.independent_algorithm_implementation is not False
            or self.verification_result
            != "VALID_SAME_IMPLEMENTATION_RAW_PREFIX_CLOSURE_REPLAY"
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure semantic replay is malformed or overclaims"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_h2_closure_semantic_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "validation_checkpoint": self.validation_checkpoint,
            "row_replay_bindings": [
                {
                    "partial_row_id": partial_row_id,
                    "row_replay_verification_id": replay_id,
                }
                for partial_row_id, replay_id in self.row_replay_bindings
            ],
            "replayed_observer_draws": self.replayed_observer_draws,
            "replayed_random_word_calls": self.replayed_random_word_calls,
            "replayed_rejections": self.replayed_rejections,
            "exact_atom_enumerator_calls": 0,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
            "independent_algorithm_implementation": False,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("semantic_replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_observation_support_h2_closure_v1(
    context: transition_observer.PublicGraphContextV1,
    closure: ObservationSupportH2ClosureV1,
    max_workers: int = 1,
) -> ObservationSupportH2ClosureReplayVerificationV1:
    """Regenerate every consumed raw prefix and reconstruct the closure."""

    registered = _registered_context(context)
    workers = _workers(max_workers)
    if (
        type(closure) is not ObservationSupportH2ClosureV1
        or closure.context != registered
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "semantic replay requires the exact registered closure"
        )
    reconstructed = ObservationSupportH2ClosureV1(
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
        raise ObservationSupportH2ClosureInvariantViolation(
            "closure failed canonical reconstruction before raw replay"
        )
    catalogue_by_id = {
        item.catalogue_id: item
        for item in (closure.root_catalogue, *closure.child_catalogues)
    }
    tasks = tuple(
        _RowReplayTaskV1(
            registered,
            catalogue_by_id[row.binding.catalogue_id],
            row.binding.action,
            row,
        )
        for row in sorted(
            closure.all_rows,
            key=lambda item: item.partial_row_id,
        )
    )
    if workers == 1:
        row_replays = tuple(_replay_row_task_v1(item) for item in tasks)
    else:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=get_context("spawn"),
        ) as executor:
            row_replays = tuple(executor.map(_replay_row_task_v1, tasks))
    bindings = tuple(
        (
            task.row.partial_row_id,
            replay.verification_id,
        )
        for task, replay in zip(tasks, row_replays)
    )
    if (
        tuple(item.partial_row_id for item in row_replays)
        != tuple(item[0] for item in bindings)
        or sum(item.replayed_observer_draws for item in row_replays)
        != closure.counters.total_observer_draws
        or sum(item.replayed_random_word_calls for item in row_replays)
        != closure.counters.total_random_word_calls
        or sum(item.replayed_rejections for item in row_replays)
        != closure.counters.total_rejections
    ):
        raise ObservationSupportH2ClosureInvariantViolation(
            "raw row replay does not reconcile with closure counters"
        )
    return ObservationSupportH2ClosureReplayVerificationV1(
        registered.context_id,
        closure.closure_id,
        closure.validation_checkpoint,
        bindings,
        closure.counters.total_observer_draws,
        closure.counters.total_random_word_calls,
        closure.counters.total_rejections,
    )


class ObservationSupportH2ClosureRoute(str, Enum):
    DIRECT = "DIRECT"
    QUOTIENT = "QUOTIENT"


@dataclass(frozen=True, slots=True)
class ObservationSupportH2ClosureLogicalChargeV1:
    logical_consumer_id: str
    route: ObservationSupportH2ClosureRoute
    closure_id: str
    physical_bundle_id: str
    physical_evidence_ids: tuple[str, ...]
    counters: ObservationSupportH2ClosureCountersV1
    shared_physical_computation_allowed: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_consumer_id, "closure logical consumer"),
            (self.closure_id, "charged closure"),
            (self.physical_bundle_id, "charged physical bundle"),
        ):
            _cid(value, field)
        if (
            type(self.route) is not ObservationSupportH2ClosureRoute
            or self.closure_id != self.physical_bundle_id
            or type(self.physical_evidence_ids) is not tuple
            or self.physical_evidence_ids
            != tuple(sorted(set(self.physical_evidence_ids)))
            or any(
                _cid(item, "charged physical evidence") is None
                for item in self.physical_evidence_ids
            )
            or type(self.counters)
            is not ObservationSupportH2ClosureCountersV1
            or len(self.physical_evidence_ids)
            != self.counters.total_action_row_count
            or self.shared_physical_computation_allowed is not True
        ):
            raise ObservationSupportH2ClosureInvariantViolation(
                "H2 closure logical charge is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_h2_closure_logical_charge.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "logical_consumer_id": self.logical_consumer_id,
            "route": self.route.value,
            "closure_id": self.closure_id,
            "physical_bundle_id": self.physical_bundle_id,
            "physical_evidence_ids": list(self.physical_evidence_ids),
            "counters_id": self.counters.counters_id,
            "shared_physical_computation_allowed": True,
            "physical_evidence_rule": PHYSICAL_EVIDENCE_RULE,
        }

    @property
    def charge_id(self) -> str:
        return _content_id("charge", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": self.counters.to_document(),
            "charge_id": self.charge_id,
        }


def charge_observation_support_h2_closure_v1(
    closure: ObservationSupportH2ClosureV1,
    logical_consumer_id: str,
    route: ObservationSupportH2ClosureRoute,
) -> ObservationSupportH2ClosureLogicalChargeV1:
    if type(closure) is not ObservationSupportH2ClosureV1:
        raise ObservationSupportH2ClosureInvariantViolation(
            "logical charge requires one canonical H2 closure"
        )
    _cid(logical_consumer_id, "closure logical consumer")
    if type(route) is not ObservationSupportH2ClosureRoute:
        raise ObservationSupportH2ClosureInvariantViolation(
            "logical charge route is not canonical"
        )
    return ObservationSupportH2ClosureLogicalChargeV1(
        logical_consumer_id,
        route,
        closure.closure_id,
        closure.physical_bundle_id,
        closure.physical_evidence_ids,
        closure.counters,
    )


def charge_direct_observation_support_h2_closure_v1(
    closure: ObservationSupportH2ClosureV1,
    logical_consumer_id: str,
) -> ObservationSupportH2ClosureLogicalChargeV1:
    return charge_observation_support_h2_closure_v1(
        closure,
        logical_consumer_id,
        ObservationSupportH2ClosureRoute.DIRECT,
    )


def charge_quotient_observation_support_h2_closure_v1(
    closure: ObservationSupportH2ClosureV1,
    logical_consumer_id: str,
) -> ObservationSupportH2ClosureLogicalChargeV1:
    return charge_observation_support_h2_closure_v1(
        closure,
        logical_consumer_id,
        ObservationSupportH2ClosureRoute.QUOTIENT,
    )


__all__ = [
    "CHILD_DISCOVERY_RULE",
    "CONTRACT_VERSION",
    "MAX_PROCESS_WORKERS",
    "ObservationSupportH2ClosureCountersV1",
    "ObservationSupportH2ClosureInvariantViolation",
    "ObservationSupportH2ClosureLogicalChargeV1",
    "ObservationSupportH2ClosureReplayVerificationV1",
    "ObservationSupportH2ClosureRoute",
    "ObservationSupportH2ClosureV1",
    "PHYSICAL_EVIDENCE_RULE",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "VALIDATION_NOVEL_RULE",
    "acquire_observation_support_h2_closure_v1",
    "charge_direct_observation_support_h2_closure_v1",
    "charge_observation_support_h2_closure_v1",
    "charge_quotient_observation_support_h2_closure_v1",
    "clear_observation_support_h2_closure_cache_v1",
    "verify_observation_support_h2_closure_v1",
]
