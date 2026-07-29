"""Authority-bound consumption of one promoted partial-support row.

The V0-068 expansion authority deliberately stops at a pending model epoch:
promoting a root row can name previously hidden H=1 successor states, so a
sound consumer must construct their public action catalogues and acquire every
corresponding transition row before it rebuilds the robust model.

This module performs that missing step.  It preserves every unaffected parent
row byte-for-byte, substitutes exactly the authorized epoch-2 row, acquires
epoch-1 rows only for newly admitted child catalogues, rebuilds the
authority-bound graph-model bridge, and reruns the same robust planner.  The
new epoch is therefore a mixed support epoch: one promoted row is at epoch 2
and all newly materialized continuation rows begin at epoch 1.

No operational exact-support, exact-probability, or evaluation-only kernel
authority is imported or called.  Statistical conclusions retain the V0-068
conditional scope: the deterministic SplitMix replay implementation is not a
formal exact-IID implementation.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import hashlib
from multiprocessing import get_context
from typing import Any, Iterable, Mapping

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_relational_adapter_v1 as relational
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_promoted_h2_consumer_v0"
MAX_PROCESS_WORKERS = h2_closure.MAX_PROCESS_WORKERS

MIXED_EPOCH_RULE = (
    "ONE_AUTHORIZED_EPOCH2_REPLACEMENT_PLUS_UNCHANGED_PARENT_ROWS_AND_"
    "EPOCH1_ROWS_FOR_NEWLY_ADMITTED_H1_STATES"
)
PARENT_IMMUTABILITY_RULE = (
    "ALL_PARENT_ROWS_EXCEPT_AUTHORIZED_REPLACEMENT_RETAIN_EXACT_CONTENT_IDS"
)
SUPPORT_EXPANSION_RULE = (
    "ONLY_AUTHORIZED_PARENT_VALIDATION_NOVEL_OUTCOMES_ENTER_SUPPORT;"
    "FRESH_VALIDATION_NOVEL_OUTCOMES_REMAIN_OTHER"
)
STATISTICAL_CLAIM_SCOPE = observer.STATISTICAL_CLAIM_SCOPE


class ObservationSupportPromotedH2ConsumerInvariantViolation(ValueError):
    """A promotion, closure, model, counter, or replay binding is invalid."""


DOMAIN_TAGS = {
    "counters": "acfqp:observation-support-promoted-h2-counters:v1",
    "closure": "acfqp:observation-support-promoted-h2-closure:v1",
    "consumer": "acfqp:observation-support-promoted-h2-consumer:v1",
    "verification": (
        "acfqp:observation-support-promoted-h2-consumer-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("promoted H2 consumer content domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _sorted_ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    output = tuple(values)
    if output != tuple(sorted(set(output))):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            f"{field} must be distinct and content-ID sorted"
        )
    for value in output:
        _cid(value, field)
    return output


def _registered_context(
    context: Any,
) -> observer.PublicGraphContextV1:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
        or context.horizon != h2_closure.REGISTERED_HORIZON
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "promoted H2 consumption requires one registered H=2 context"
        )
    return context


def _workers(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= MAX_PROCESS_WORKERS:
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "max_workers must be an integer in the registered range"
        )
    return value


def _sorted_catalogues(
    values: Iterable[observer.LegalActionCatalogueV1],
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    output = tuple(sorted(values, key=lambda item: item.catalogue_id))
    if (
        any(type(item) is not observer.LegalActionCatalogueV1 for item in output)
        or tuple(item.catalogue_id for item in output)
        != tuple(sorted({item.catalogue_id for item in output}))
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "child catalogues must be typed, unique, and content-ID sorted"
        )
    return output


def _sorted_rows(
    values: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    output = tuple(sorted(values, key=lambda item: item.binding.row_id))
    if (
        any(
            type(item) is not acquisition.GraphPartialSupportRowV1
            for item in output
        )
        or tuple(item.binding.row_id for item in output)
        != tuple(sorted({item.binding.row_id for item in output}))
        or len({item.partial_row_id for item in output}) != len(output)
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "closure rows must be typed and unique by binding and content ID"
        )
    return output


def _active_root_states(
    root_rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> tuple[observer.SymbolicGraphStateV1, ...]:
    by_id: dict[str, observer.SymbolicGraphStateV1] = {}
    for row in root_rows:
        for descriptor in row.support_descriptors:
            if descriptor.failure or descriptor.terminal:
                continue
            state = descriptor.next_state
            prior = by_id.setdefault(state.state_id, state)
            if canonical_json_bytes(prior.to_document()) != canonical_json_bytes(
                state.to_document()
            ):
                raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                    "one active successor ID has conflicting symbolic bytes"
                )
    return tuple(by_id[key] for key in sorted(by_id))


def _row_ref(
    row: acquisition.GraphPartialSupportRowV1,
) -> dict[str, Any]:
    return {
        "partial_row_id": row.partial_row_id,
        "row_binding_id": row.binding.row_id,
        "catalogue_id": row.binding.catalogue_id,
        "state_id": row.binding.state_id,
        "remaining_horizon": row.binding.remaining_horizon,
        "action": list(row.binding.action),
        "support_epoch_index": row.support_epoch_index,
        "support_epoch_id": row.support_epoch.support_epoch_id,
        "confidence_authority_id": row.confidence_authority.authority_id,
        "physical_evidence_id": row.physical_evidence_id,
        "counters_id": row.counters.counters_id,
    }


@dataclass(frozen=True, slots=True)
class ObservationSupportPromotedH2IncrementalCountersV1:
    """Typed incremental facts for consuming the authorized replacement.

    ``selected_replan_policy_assignment_count`` is the cardinality of the
    selected plan artifact.  It is not a solver-enumeration counter and must
    not be projected as operational or economics work.
    """

    retained_parent_row_count: int
    result_row_count: int
    promoted_row_fresh_validation_draws: int
    promoted_row_fresh_random_word_calls: int
    promoted_row_fresh_rejections: int
    new_child_catalogue_count: int
    new_child_action_row_count: int
    new_child_discovery_draws: int
    new_child_validation_draws: int
    new_child_observer_draws: int
    new_child_random_word_calls: int
    new_child_rejections: int
    incremental_observer_draws: int
    incremental_random_word_calls: int
    incremental_rejections: int
    bridge_source_row_count: int
    bridge_projection_count: int
    selected_replan_policy_assignment_count: int
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    evaluation_exact_atom_calls: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, field) for field in self.__dataclass_fields__
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.result_row_count != self.retained_parent_row_count + 1
            + self.new_child_action_row_count
            or self.promoted_row_fresh_random_word_calls
            != self.promoted_row_fresh_validation_draws
            + self.promoted_row_fresh_rejections
            or self.new_child_observer_draws
            != self.new_child_discovery_draws
            + self.new_child_validation_draws
            or self.incremental_observer_draws
            != self.promoted_row_fresh_validation_draws
            + self.new_child_observer_draws
            or self.incremental_random_word_calls
            != self.promoted_row_fresh_random_word_calls
            + self.new_child_random_word_calls
            or self.incremental_rejections
            != self.promoted_row_fresh_rejections
            + self.new_child_rejections
            or self.incremental_random_word_calls
            != self.incremental_observer_draws
            + self.incremental_rejections
            or self.bridge_source_row_count != self.result_row_count
            or self.bridge_projection_count != self.result_row_count
            or self.selected_replan_policy_assignment_count <= 0
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or self.evaluation_exact_atom_calls != 0
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted H2 incremental counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_promoted_h2_incremental_counters.v1"
            ),
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


@dataclass(frozen=True, slots=True)
class ObservationSupportPromotedH2ClosureV1:
    """Complete mixed-epoch H=2 closure after one authorized promotion."""

    context: observer.PublicGraphContextV1
    parent_validation_checkpoint: int
    promoted_validation_checkpoint: int
    new_child_validation_checkpoint: int
    parent_closure: h2_closure.ObservationSupportH2ClosureV1
    replacement: expansion.PartialSupportPromotedRowReplacementV1
    root_catalogue: observer.LegalActionCatalogueV1
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...]
    root_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    child_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    newly_admitted_child_catalogue_ids: tuple[str, ...]
    newly_acquired_child_partial_row_ids: tuple[str, ...]
    counters: ObservationSupportPromotedH2IncrementalCountersV1
    observation_only: bool = True
    mixed_support_epoch: bool = True
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        context = _registered_context(self.context)
        if (
            type(self.parent_validation_checkpoint) is not int
            or self.parent_validation_checkpoint
            not in acquisition.VALIDATION_CHECKPOINTS
            or type(self.promoted_validation_checkpoint) is not int
            or self.promoted_validation_checkpoint
            not in acquisition.VALIDATION_CHECKPOINTS
            or type(self.new_child_validation_checkpoint) is not int
            or self.new_child_validation_checkpoint
            not in acquisition.VALIDATION_CHECKPOINTS
            or type(self.parent_closure)
            is not h2_closure.ObservationSupportH2ClosureV1
            or type(self.replacement)
            is not expansion.PartialSupportPromotedRowReplacementV1
            or type(self.root_catalogue)
            is not observer.LegalActionCatalogueV1
            or type(self.counters)
            is not ObservationSupportPromotedH2IncrementalCountersV1
            or self.observation_only is not True
            or self.mixed_support_epoch is not True
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted H2 closure has an invalid concrete schema"
            )
        parent = self.parent_closure
        replacement = self.replacement
        pending = replacement.pending_model_epoch
        quarantined_parent_ids = tuple(
            sorted(
                {
                    *replacement.parent_row.initial_discovery_observation_ids,
                    *replacement.parent_row.prior_validation_observation_ids,
                    *replacement.parent_row.current_validation_observation_ids,
                }
            )
        )
        if (
            parent.context != context
            or parent.validation_checkpoint
            != self.parent_validation_checkpoint
            or parent.root_catalogue != self.root_catalogue
            or replacement.authorization.context_id != context.context_id
            or replacement.authorization.checkpoint_draw_count
            != self.promoted_validation_checkpoint
            or pending.context_id != context.context_id
            or pending.parent_source_partial_row_ids
            != tuple(sorted(item.partial_row_id for item in parent.all_rows))
            or pending.replaced_parent_partial_row_id
            != replacement.parent_row.partial_row_id
            or pending.promoted_partial_row_id
            != replacement.promoted_row.partial_row_id
            or pending.promoted_confidence_authority_id
            != replacement.promoted_row.confidence_authority.authority_id
            or pending.promoted_observer_epoch_id
            != replacement.promoted_row.observer_epoch_chain[-1].epoch_id
            or pending.promoted_outcome_ids
            != tuple(
                sorted(
                    item.outcome_id
                    for item in replacement.promoted_row.support_descriptors
                )
            )
            or pending.fresh_validation_observation_ids
            != tuple(
                sorted(
                    replacement.promoted_row.current_validation_observation_ids
                )
            )
            or pending.quarantined_parent_observation_ids
            != quarantined_parent_ids
            or pending.closure_rebuild_required is not True
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted closure is stale relative to its immutable parent"
            )

        child_catalogues = _sorted_catalogues(self.child_catalogues)
        root_rows = _sorted_rows(self.root_rows)
        child_rows = _sorted_rows(self.child_rows)
        new_catalogue_ids = _sorted_ids(
            self.newly_admitted_child_catalogue_ids,
            "new child catalogue IDs",
        )
        new_row_ids = _sorted_ids(
            self.newly_acquired_child_partial_row_ids,
            "new child partial row IDs",
        )
        if (
            child_catalogues != self.child_catalogues
            or root_rows != self.root_rows
            or child_rows != self.child_rows
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted closure members are not canonically sorted"
            )

        expected_states = _active_root_states(root_rows)
        expected_catalogues = _sorted_catalogues(
            observer.legal_action_catalogue_v1(context, state, 1)
            for state in expected_states
        )
        if tuple(
            item.to_document() for item in child_catalogues
        ) != tuple(item.to_document() for item in expected_catalogues):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted closure omits an admitted root successor catalogue"
            )
        parent_catalogue_ids = {
            item.catalogue_id for item in parent.child_catalogues
        }
        actual_new_catalogue_ids = tuple(
            sorted(
                item.catalogue_id
                for item in child_catalogues
                if item.catalogue_id not in parent_catalogue_ids
            )
        )
        if actual_new_catalogue_ids != new_catalogue_ids:
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "new child catalogue provenance is incomplete"
            )

        expected_root_bindings = {
            (self.root_catalogue.catalogue_id, action)
            for action in self.root_catalogue.actions
        }
        expected_child_bindings = {
            (catalogue.catalogue_id, action)
            for catalogue in child_catalogues
            for action in catalogue.actions
        }
        actual_root_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in root_rows
        }
        actual_child_bindings = {
            (row.binding.catalogue_id, row.binding.action)
            for row in child_rows
        }
        if (
            actual_root_bindings != expected_root_bindings
            or actual_child_bindings != expected_child_bindings
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted closure does not cover every public legal action"
            )

        parent_by_binding = {
            row.binding.row_id: row for row in parent.all_rows
        }
        result_rows = (*root_rows, *child_rows)
        result_by_binding = {row.binding.row_id: row for row in result_rows}
        selected_binding = replacement.parent_row.binding.row_id
        if (
            parent_by_binding.get(selected_binding) != replacement.parent_row
            or result_by_binding.get(selected_binding)
            != replacement.promoted_row
            or set(parent_by_binding) - {selected_binding}
            - set(result_by_binding)
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "authorized parent replacement or retained-row set changed"
            )
        for binding_id, parent_row in parent_by_binding.items():
            if binding_id == selected_binding:
                continue
            if result_by_binding[binding_id].partial_row_id != (
                parent_row.partial_row_id
            ):
                raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                    "an unaffected parent row was mutated"
                )

        actual_new_rows = tuple(
            sorted(
                row.partial_row_id
                for row in child_rows
                if row.binding.catalogue_id in set(new_catalogue_ids)
            )
        )
        if (
            actual_new_rows != new_row_ids
            or any(
                row.support_epoch_index != 1
                or row.counters.current_validation_draws
                != self.new_child_validation_checkpoint
                for row in child_rows
                if row.partial_row_id in set(new_row_ids)
            )
            or sum(row.support_epoch_index == 2 for row in result_rows) != 1
            or replacement.promoted_row.support_epoch_index != 2
            or any(
                row.novel_descriptors
                and row.partial_row_id in set(new_row_ids)
                and row.support_epoch_index != 1
                for row in result_rows
            )
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "mixed support epoch or fresh child-row lineage is invalid"
            )

    @property
    def all_rows(
        self,
    ) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
        return (*self.root_rows, *self.child_rows)

    @property
    def public_catalogues(
        self,
    ) -> tuple[observer.LegalActionCatalogueV1, ...]:
        return (self.root_catalogue, *self.child_catalogues)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_promoted_h2_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "parent_validation_checkpoint": (
                self.parent_validation_checkpoint
            ),
            "promoted_validation_checkpoint": (
                self.promoted_validation_checkpoint
            ),
            "new_child_validation_checkpoint": (
                self.new_child_validation_checkpoint
            ),
            "parent_closure_id": self.parent_closure.closure_id,
            "replacement_id": self.replacement.replacement_id,
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
            "newly_admitted_child_catalogue_ids": list(
                self.newly_admitted_child_catalogue_ids
            ),
            "newly_acquired_child_partial_row_ids": list(
                self.newly_acquired_child_partial_row_ids
            ),
            "counters_id": self.counters.counters_id,
            "observation_only": True,
            "mixed_support_epoch": True,
            "mixed_epoch_rule": MIXED_EPOCH_RULE,
            "parent_immutability_rule": PARENT_IMMUTABILITY_RULE,
            "support_expansion_rule": SUPPORT_EXPANSION_RULE,
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
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
class ObservationSupportPromotedH2ConsumerV1:
    """Rebuilt bridge plus robust replan for one mixed support epoch."""

    context_id: str
    parent_closure_id: str
    parent_bridge_id: str
    replacement_id: str
    promoted_closure: ObservationSupportPromotedH2ClosureV1
    coordinate_profile_id: str
    bridge: graph_model.ObservationSupportGraphModelBridgeV1
    bridge_replay: graph_model.ObservationSupportGraphModelReplayV1
    threshold_profile_id: str
    audit: robust.RobustPlanAuditV1
    audit_replay: robust.RobustAuditVerificationV1
    counters: ObservationSupportPromotedH2IncrementalCountersV1
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    evaluation_exact_atom_calls: int = 0
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "consumer context"),
            (self.parent_closure_id, "consumer parent closure"),
            (self.parent_bridge_id, "consumer parent bridge"),
            (self.replacement_id, "consumer replacement"),
            (self.coordinate_profile_id, "consumer coordinate profile"),
            (self.threshold_profile_id, "consumer threshold"),
        ):
            _cid(value, field)
        if (
            type(self.promoted_closure)
            is not ObservationSupportPromotedH2ClosureV1
            or type(self.bridge)
            is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.bridge_replay)
            is not graph_model.ObservationSupportGraphModelReplayV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or type(self.audit_replay) is not robust.RobustAuditVerificationV1
            or type(self.counters)
            is not ObservationSupportPromotedH2IncrementalCountersV1
            or self.context_id != self.promoted_closure.context.context_id
            or self.parent_closure_id
            != self.promoted_closure.parent_closure.closure_id
            or self.parent_bridge_id
            != self.promoted_closure.replacement.authorization.bridge_id
            or self.replacement_id
            != self.promoted_closure.replacement.replacement_id
            or self.coordinate_profile_id != self.bridge.coordinate_profile_id
            or self.threshold_profile_id != self.audit.threshold_profile_id
            or self.bridge.context_id != self.context_id
            or self.bridge.source_partial_row_ids
            != tuple(
                sorted(
                    item.partial_row_id
                    for item in self.promoted_closure.all_rows
                )
            )
            or self.bridge_replay.bridge_id != self.bridge.bridge_id
            or self.audit_replay.audit_id != self.audit.audit_id
            or self.audit_replay.model_id != self.audit.model_id
            or self.audit.solver_kind
            is not self.promoted_closure.replacement.authorization.solver_kind
            or self.counters != self.promoted_closure.counters
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or self.evaluation_exact_atom_calls != 0
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted H2 consumer identities or authority scope changed"
            )
        expected_model = (
            self.bridge.direct_model
            if self.audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
            else self.bridge.quotient_model
        )
        if self.audit.model_id != expected_model.model_id:
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "replan audit is not bound to the rebuilt bridge"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_promoted_h2_consumer.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "parent_closure_id": self.parent_closure_id,
            "parent_bridge_id": self.parent_bridge_id,
            "replacement_id": self.replacement_id,
            "promoted_closure_id": self.promoted_closure.closure_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "bridge_id": self.bridge.bridge_id,
            "bridge_replay_id": self.bridge_replay.verification_id,
            "threshold_profile_id": self.threshold_profile_id,
            "audit_id": self.audit.audit_id,
            "audit_replay_id": self.audit_replay.verification_id,
            "audit_status": self.audit.status.value,
            "solver_kind": self.audit.solver_kind.value,
            "counters_id": self.counters.counters_id,
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
            "evaluation_exact_atom_calls": 0,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def consumer_id(self) -> str:
        return _content_id("consumer", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_closure": self.promoted_closure.to_document(),
            "bridge": self.bridge.to_document(),
            "bridge_replay": self.bridge_replay.to_document(),
            "audit": self.audit.to_document(),
            "audit_replay": self.audit_replay.to_document(),
            "counters": self.counters.to_document(),
            "consumer_id": self.consumer_id,
        }


@dataclass(frozen=True, slots=True)
class _NewChildRowTaskV1:
    context: observer.PublicGraphContextV1
    catalogue: observer.LegalActionCatalogueV1
    action: tuple[int, int, int]
    checkpoint: int


def _acquire_new_child_row_task_v1(
    task: _NewChildRowTaskV1,
) -> acquisition.GraphPartialSupportRowV1:
    return acquisition.acquire_graph_partial_support_row_v1(
        task.context,
        task.catalogue,
        task.action,
        task.checkpoint,
    )


def _replace_parent_row(
    rows: Iterable[acquisition.GraphPartialSupportRowV1],
    replacement: expansion.PartialSupportPromotedRowReplacementV1,
) -> tuple[acquisition.GraphPartialSupportRowV1, ...]:
    values = tuple(rows)
    matches = tuple(
        row
        for row in values
        if row.partial_row_id == replacement.parent_row.partial_row_id
    )
    if len(matches) not in (0, 1):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "authorized parent row is duplicated"
        )
    if not matches:
        return _sorted_rows(values)
    return _sorted_rows(
        replacement.promoted_row
        if row.partial_row_id == replacement.parent_row.partial_row_id
        else row
        for row in values
    )


def _build_incremental_counters(
    *,
    parent: h2_closure.ObservationSupportH2ClosureV1,
    replacement: expansion.PartialSupportPromotedRowReplacementV1,
    new_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    result_row_count: int,
    new_child_catalogue_count: int,
    selected_replan_policy_assignment_count: int,
) -> ObservationSupportPromotedH2IncrementalCountersV1:
    parent_counter = replacement.parent_row.counters
    promoted_counter = replacement.promoted_row.counters
    promotion_draws = (
        promoted_counter.total_observer_draws
        - parent_counter.total_observer_draws
    )
    promotion_words = (
        promoted_counter.total_random_word_calls
        - parent_counter.total_random_word_calls
    )
    promotion_rejections = (
        promoted_counter.total_rejections - parent_counter.total_rejections
    )
    if (
        promotion_draws != replacement.authorization.checkpoint_draw_count
        or promotion_words < promotion_draws
        or promotion_rejections < 0
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "promoted-row fresh work does not reconcile with its parent"
        )
    new_discovery = sum(
        row.counters.initial_discovery_draws for row in new_rows
    )
    new_validation = sum(
        row.counters.current_validation_draws for row in new_rows
    )
    new_observer = sum(row.counters.total_observer_draws for row in new_rows)
    new_words = sum(row.counters.total_random_word_calls for row in new_rows)
    new_rejections = sum(row.counters.total_rejections for row in new_rows)
    return ObservationSupportPromotedH2IncrementalCountersV1(
        retained_parent_row_count=len(parent.all_rows) - 1,
        result_row_count=result_row_count,
        promoted_row_fresh_validation_draws=promotion_draws,
        promoted_row_fresh_random_word_calls=promotion_words,
        promoted_row_fresh_rejections=promotion_rejections,
        new_child_catalogue_count=new_child_catalogue_count,
        new_child_action_row_count=len(new_rows),
        new_child_discovery_draws=new_discovery,
        new_child_validation_draws=new_validation,
        new_child_observer_draws=new_observer,
        new_child_random_word_calls=new_words,
        new_child_rejections=new_rejections,
        incremental_observer_draws=promotion_draws + new_observer,
        incremental_random_word_calls=promotion_words + new_words,
        incremental_rejections=promotion_rejections + new_rejections,
        bridge_source_row_count=result_row_count,
        bridge_projection_count=result_row_count,
        selected_replan_policy_assignment_count=(
            selected_replan_policy_assignment_count
        ),
    )


def _solve(
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> robust.RobustPlanAuditV1:
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        return robust.solve_ground_direct_robust_h2_v1(
            bridge.direct_model,
            threshold,
        )
    if solver_kind is robust.RobustSolverKind.QUOTIENT:
        return robust.solve_quotient_robust_h2_v1(
            bridge.quotient_model,
            threshold,
        )
    raise ObservationSupportPromotedH2ConsumerInvariantViolation(
        "replacement has an unregistered solver kind"
    )


def consume_partial_support_promoted_row_replacement_v1(
    *,
    context: observer.PublicGraphContextV1,
    parent_closure: h2_closure.ObservationSupportH2ClosureV1,
    parent_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    parent_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    replacement: expansion.PartialSupportPromotedRowReplacementV1,
    coordinate_profile: (
        relational.ObservationSupportCoordinateProfileV1 | None
    ) = None,
    new_child_validation_checkpoint: int | None = None,
    max_workers: int = 1,
) -> ObservationSupportPromotedH2ConsumerV1:
    """Close the pending epoch, rebuild its bridge, and robustly replan."""

    registered = _registered_context(context)
    workers = _workers(max_workers)
    profile = (
        relational.base_coordinate_profile_v1()
        if coordinate_profile is None
        else coordinate_profile
    )
    child_checkpoint = (
        parent_closure.validation_checkpoint
        if (
            type(parent_closure)
            is h2_closure.ObservationSupportH2ClosureV1
            and new_child_validation_checkpoint is None
        )
        else new_child_validation_checkpoint
    )
    if (
        type(parent_closure)
        is not h2_closure.ObservationSupportH2ClosureV1
        or parent_closure.context != registered
        or type(parent_bridge)
        is not graph_model.ObservationSupportGraphModelBridgeV1
        or type(parent_audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(replacement)
        is not expansion.PartialSupportPromotedRowReplacementV1
        or type(profile)
        is not relational.ObservationSupportCoordinateProfileV1
        or type(child_checkpoint) is not int
        or child_checkpoint not in acquisition.VALIDATION_CHECKPOINTS
        or parent_bridge.coordinate_profile_id != profile.profile_id
        or replacement.authorization.bridge_id != parent_bridge.bridge_id
        or replacement.authorization.parent_audit_id != parent_audit.audit_id
        or replacement.authorization.threshold_profile_id
        != threshold.threshold_profile_id
        or replacement.pending_model_epoch.parent_bridge_id
        != parent_bridge.bridge_id
        or replacement.pending_model_epoch.parent_source_partial_row_ids
        != tuple(
            sorted(item.partial_row_id for item in parent_closure.all_rows)
        )
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "consumer inputs are stale, transplanted, or untyped"
        )

    graph_model.verify_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=parent_closure.root_catalogue,
        catalogues=(
            parent_closure.root_catalogue,
            *parent_closure.child_catalogues,
        ),
        partial_rows=parent_closure.all_rows,
        bridge=parent_bridge,
        coordinate_profile=profile,
    )
    parent_model = (
        parent_bridge.direct_model
        if parent_audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else parent_bridge.quotient_model
    )
    robust.verify_robust_plan_audit_v1(
        parent_model,
        threshold,
        parent_audit,
    )
    expected_authorization = expansion.authorize_partial_support_expansion_v1(
        bridge=parent_bridge,
        audit=parent_audit,
        threshold=threshold,
        partial_rows=parent_closure.all_rows,
        checkpoint_draw_count=(
            replacement.authorization.checkpoint_draw_count
        ),
    )
    if (
        expected_authorization != replacement.authorization
        or expected_authorization.authorization_id
        != replacement.authorization.authorization_id
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "replacement authorization fails current semantic replay"
        )

    root_rows = _replace_parent_row(
        parent_closure.root_rows,
        replacement,
    )
    child_rows = _replace_parent_row(
        parent_closure.child_rows,
        replacement,
    )
    if (
        replacement.parent_row.partial_row_id
        not in {
            row.partial_row_id for row in parent_closure.root_rows
        }
        and replacement.parent_row.partial_row_id
        not in {
            row.partial_row_id for row in parent_closure.child_rows
        }
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "authorized parent row is absent from the parent closure"
        )

    child_catalogues = _sorted_catalogues(
        observer.legal_action_catalogue_v1(registered, state, 1)
        for state in _active_root_states(root_rows)
    )
    parent_catalogue_ids = {
        item.catalogue_id for item in parent_closure.child_catalogues
    }
    new_catalogues = tuple(
        item
        for item in child_catalogues
        if item.catalogue_id not in parent_catalogue_ids
    )
    tasks = tuple(
        _NewChildRowTaskV1(
            registered,
            catalogue,
            action,
            child_checkpoint,
        )
        for catalogue in new_catalogues
        for action in catalogue.actions
    )
    if workers == 1:
        new_rows = tuple(
            _acquire_new_child_row_task_v1(task) for task in tasks
        )
    else:
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=get_context("spawn"),
        ) as executor:
            new_rows = tuple(
                executor.map(_acquire_new_child_row_task_v1, tasks)
            )
    new_rows = _sorted_rows(new_rows) if new_rows else ()
    child_rows = _sorted_rows((*child_rows, *new_rows))

    bridge = graph_model.build_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=parent_closure.root_catalogue,
        catalogues=(parent_closure.root_catalogue, *child_catalogues),
        partial_rows=(*root_rows, *child_rows),
        coordinate_profile=profile,
    )
    bridge_replay = graph_model.verify_observation_support_graph_models_v1(
        context=registered,
        root_catalogue=parent_closure.root_catalogue,
        catalogues=(parent_closure.root_catalogue, *child_catalogues),
        partial_rows=(*root_rows, *child_rows),
        bridge=bridge,
        coordinate_profile=profile,
    )
    audit = _solve(bridge, threshold, replacement.authorization.solver_kind)
    audit_replay = robust.verify_robust_plan_audit_v1(
        (
            bridge.direct_model
            if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
            else bridge.quotient_model
        ),
        threshold,
        audit,
    )
    counters = _build_incremental_counters(
        parent=parent_closure,
        replacement=replacement,
        new_rows=new_rows,
        result_row_count=len(root_rows) + len(child_rows),
        new_child_catalogue_count=len(new_catalogues),
        selected_replan_policy_assignment_count=len(audit.assignments),
    )
    closure = ObservationSupportPromotedH2ClosureV1(
        registered,
        parent_closure.validation_checkpoint,
        replacement.authorization.checkpoint_draw_count,
        child_checkpoint,
        parent_closure,
        replacement,
        parent_closure.root_catalogue,
        child_catalogues,
        root_rows,
        child_rows,
        tuple(sorted(item.catalogue_id for item in new_catalogues)),
        tuple(sorted(item.partial_row_id for item in new_rows)),
        counters,
    )
    return ObservationSupportPromotedH2ConsumerV1(
        registered.context_id,
        parent_closure.closure_id,
        parent_bridge.bridge_id,
        replacement.replacement_id,
        closure,
        profile.profile_id,
        bridge,
        bridge_replay,
        threshold.threshold_profile_id,
        audit,
        audit_replay,
        counters,
    )


@dataclass(frozen=True, slots=True)
class ObservationSupportPromotedH2ConsumerVerificationV1:
    consumer_id: str
    replayed_consumer_id: str
    parent_closure_id: str
    replacement_id: str
    promoted_closure_id: str
    bridge_id: str
    audit_id: str
    replayed_incremental_observer_draws: int
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0
    evaluation_exact_atom_calls: int = 0
    same_implementation_semantic_replay: bool = True
    independent_algorithm_implementation: bool = False
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.consumer_id, "verified consumer"),
            (self.replayed_consumer_id, "replayed consumer"),
            (self.parent_closure_id, "verified parent closure"),
            (self.replacement_id, "verified replacement"),
            (self.promoted_closure_id, "verified promoted closure"),
            (self.bridge_id, "verified bridge"),
            (self.audit_id, "verified audit"),
        ):
            _cid(value, field)
        if (
            self.consumer_id != self.replayed_consumer_id
            or type(self.replayed_incremental_observer_draws) is not int
            or self.replayed_incremental_observer_draws <= 0
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
            or self.evaluation_exact_atom_calls != 0
            or self.same_implementation_semantic_replay is not True
            or self.independent_algorithm_implementation is not False
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportPromotedH2ConsumerInvariantViolation(
                "promoted H2 consumer replay is malformed or overclaims"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_promoted_h2_consumer_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "consumer_id": self.consumer_id,
            "replayed_consumer_id": self.replayed_consumer_id,
            "parent_closure_id": self.parent_closure_id,
            "replacement_id": self.replacement_id,
            "promoted_closure_id": self.promoted_closure_id,
            "bridge_id": self.bridge_id,
            "audit_id": self.audit_id,
            "replayed_incremental_observer_draws": (
                self.replayed_incremental_observer_draws
            ),
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
            "evaluation_exact_atom_calls": 0,
            "same_implementation_semantic_replay": True,
            "independent_algorithm_implementation": False,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_partial_support_promoted_h2_consumer_v1(
    *,
    context: observer.PublicGraphContextV1,
    parent_closure: h2_closure.ObservationSupportH2ClosureV1,
    parent_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    parent_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    replacement: expansion.PartialSupportPromotedRowReplacementV1,
    claimed: ObservationSupportPromotedH2ConsumerV1,
    coordinate_profile: (
        relational.ObservationSupportCoordinateProfileV1 | None
    ) = None,
    max_workers: int = 1,
) -> ObservationSupportPromotedH2ConsumerVerificationV1:
    """Same-implementation replay of the complete promoted-epoch consumer."""

    if type(claimed) is not ObservationSupportPromotedH2ConsumerV1:
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "consumer replay requires one concrete claimed result"
        )
    replayed = consume_partial_support_promoted_row_replacement_v1(
        context=context,
        parent_closure=parent_closure,
        parent_bridge=parent_bridge,
        parent_audit=parent_audit,
        threshold=threshold,
        replacement=replacement,
        coordinate_profile=coordinate_profile,
        new_child_validation_checkpoint=(
            claimed.promoted_closure.new_child_validation_checkpoint
        ),
        max_workers=max_workers,
    )
    if (
        replayed != claimed
        or replayed.consumer_id != claimed.consumer_id
        or canonical_json_bytes(replayed.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportPromotedH2ConsumerInvariantViolation(
            "claimed promoted-epoch consumer differs from semantic replay"
        )
    return ObservationSupportPromotedH2ConsumerVerificationV1(
        claimed.consumer_id,
        replayed.consumer_id,
        claimed.parent_closure_id,
        claimed.replacement_id,
        claimed.promoted_closure.closure_id,
        claimed.bridge.bridge_id,
        claimed.audit.audit_id,
        claimed.counters.incremental_observer_draws,
    )


__all__ = [
    "CONTRACT_VERSION",
    "MIXED_EPOCH_RULE",
    "PARENT_IMMUTABILITY_RULE",
    "PROFILE_KEY",
    "STATISTICAL_CLAIM_SCOPE",
    "SUPPORT_EXPANSION_RULE",
    "ObservationSupportPromotedH2ClosureV1",
    "ObservationSupportPromotedH2ConsumerInvariantViolation",
    "ObservationSupportPromotedH2ConsumerV1",
    "ObservationSupportPromotedH2ConsumerVerificationV1",
    "ObservationSupportPromotedH2IncrementalCountersV1",
    "consume_partial_support_promoted_row_replacement_v1",
    "verify_partial_support_promoted_h2_consumer_v1",
]
