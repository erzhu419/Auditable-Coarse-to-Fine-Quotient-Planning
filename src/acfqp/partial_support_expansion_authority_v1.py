"""Causal authorization for one immutable partial-support epoch expansion.

This authority is deliberately narrower than the graph-model builder.  It
does not rebuild a reachable closure.  It proves that one row is the earliest
selected-policy row whose ``OTHER`` interval is individually causal for the
failed certificate, authorizes promotion of that row only, and binds the
fresh epoch-2 evidence to a pending model-epoch rebuild.

The row-level causal test is semantic: for every selected, OTHER-positive
row, this module creates a counterfactual model in which only that row's
``OTHER`` coordinate is fixed to zero and reruns the same robust solver.
Rows are ordered by decreasing remaining horizon and then by content ID.
Thus the authorized row is a unique deterministic minimum, not an arbitrary
member of a broad failed frontier.

Promotion remains statistically honest.  Validation observations from the
parent epoch are proposal-only and are quarantined; the promoted row must use
a disjoint, fresh validation stream.  The returned model-epoch binding says
``closure_rebuild_required`` because newly named outcomes can add reachable
states and this authority does not silently invent their child catalogues.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
from multiprocessing import get_context
import os
from typing import Any, Iterable, Mapping

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "causal_partial_support_epoch2_expansion_v0"
EARLIEST_ROW_ORDER = "MAX_REMAINING_HORIZON_THEN_MIN_PLANNER_ROW_ID"
MAX_SUPPORT_EPOCH_INDEX = 2
MAX_COUNTERFACTUAL_WORKERS = 32

DOMAIN_TAGS = {
    "candidate": "acfqp:partial-support-row-causal-counterfactual:v1",
    "authorization": "acfqp:partial-support-expansion-authorization:v1",
    "model_epoch": "acfqp:partial-support-pending-model-epoch-binding:v1",
    "replacement": "acfqp:partial-support-promoted-row-replacement:v1",
}


class PartialSupportExpansionInvariantViolation(ValueError):
    """An audit, model, row lineage, authorization, or promotion is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise PartialSupportExpansionInvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise PartialSupportExpansionInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _ids(values: Any, field: str) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or values != tuple(sorted(set(values)))
    ):
        raise PartialSupportExpansionInvariantViolation(
            f"{field} must be a sorted distinct tuple"
        )
    for value in values:
        _cid(value, field)
    return values


class RowCounterfactualStatus(str, Enum):
    CERTIFICATE_CHANGED = "CERTIFICATE_CHANGED"
    STILL_FAILED = "STILL_FAILED"
    INFEASIBLE_SIMPLEX = "INFEASIBLE_SIMPLEX"


@dataclass(frozen=True, slots=True)
class RowOtherCounterfactualEvidenceV1:
    """Semantic result of zeroing OTHER in one and only one planner row."""

    parent_model_id: str
    parent_audit_id: str
    threshold_profile_id: str
    planner_row_id: str
    partial_row_id: str
    remaining_horizon: int
    zero_other_model_id: str | None
    replayed_audit_id: str | None
    status: RowCounterfactualStatus
    changes_failed_to_certified: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.parent_model_id, "candidate parent model"),
            (self.parent_audit_id, "candidate parent audit"),
            (self.threshold_profile_id, "candidate threshold"),
            (self.planner_row_id, "candidate planner row"),
            (self.partial_row_id, "candidate partial row"),
        ):
            _cid(value, field)
        for value, field in (
            (self.zero_other_model_id, "candidate zero-OTHER model"),
            (self.replayed_audit_id, "candidate replayed audit"),
        ):
            if value is not None:
                _cid(value, field)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.status) is not RowCounterfactualStatus
            or type(self.changes_failed_to_certified) is not bool
        ):
            raise PartialSupportExpansionInvariantViolation(
                "row counterfactual evidence is malformed"
            )
        changed = self.status is RowCounterfactualStatus.CERTIFICATE_CHANGED
        infeasible = self.status is RowCounterfactualStatus.INFEASIBLE_SIMPLEX
        if (
            self.changes_failed_to_certified is not changed
            or (
                infeasible
                and (
                    self.zero_other_model_id is not None
                    or self.replayed_audit_id is not None
                )
            )
            or (
                not infeasible
                and (
                    self.zero_other_model_id is None
                    or self.replayed_audit_id is None
                )
            )
        ):
            raise PartialSupportExpansionInvariantViolation(
                "row counterfactual conclusion is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_row_causal_counterfactual.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "planner_row_id": self.planner_row_id,
            "partial_row_id": self.partial_row_id,
            "remaining_horizon": self.remaining_horizon,
            "zero_other_model_id": self.zero_other_model_id,
            "replayed_audit_id": self.replayed_audit_id,
            "status": self.status.value,
            "changes_failed_to_certified": (
                self.changes_failed_to_certified
            ),
            "only_this_row_other_zeroed": True,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class PartialSupportExpansionAuthorizationV1:
    """Content-addressed permission for exactly one epoch-2 row promotion."""

    bridge_id: str
    context_id: str
    parent_model_id: str
    parent_audit_id: str
    threshold_profile_id: str
    solver_kind: robust.RobustSolverKind
    assignment_ids: tuple[str, ...]
    frontier_id: str
    source_partial_row_ids: tuple[str, ...]
    candidate_evidence: tuple[RowOtherCounterfactualEvidenceV1, ...]
    selected_evidence_id: str
    selected_planner_row_id: str
    selected_partial_row_id: str
    selected_parent_physical_evidence_id: str
    selected_parent_support_epoch_id: str
    selected_parent_confidence_authority_id: str
    selected_remaining_horizon: int
    selected_novel_outcome_ids: tuple[str, ...]
    checkpoint_draw_count: int
    earliest_row_order: str = EARLIEST_ROW_ORDER
    authorization_scope: str = "ONE_ROW_ONE_NEXT_SUPPORT_EPOCH"

    def __post_init__(self) -> None:
        for value, field in (
            (self.bridge_id, "authorization bridge"),
            (self.context_id, "authorization context"),
            (self.parent_model_id, "authorization parent model"),
            (self.parent_audit_id, "authorization parent audit"),
            (self.threshold_profile_id, "authorization threshold"),
            (self.frontier_id, "authorization frontier"),
            (self.selected_evidence_id, "selected causal evidence"),
            (self.selected_planner_row_id, "selected planner row"),
            (self.selected_partial_row_id, "selected partial row"),
            (
                self.selected_parent_physical_evidence_id,
                "selected parent physical evidence",
            ),
            (
                self.selected_parent_support_epoch_id,
                "selected parent support epoch",
            ),
            (
                self.selected_parent_confidence_authority_id,
                "selected parent confidence authority",
            ),
        ):
            _cid(value, field)
        _ids(self.assignment_ids, "authorization assignments")
        _ids(self.source_partial_row_ids, "authorization source rows")
        _ids(
            self.selected_novel_outcome_ids,
            "authorization novel outcomes",
        )
        if (
            type(self.solver_kind) is not robust.RobustSolverKind
            or type(self.candidate_evidence) is not tuple
            or not self.candidate_evidence
            or any(
                type(item) is not RowOtherCounterfactualEvidenceV1
                for item in self.candidate_evidence
            )
            or tuple(item.evidence_id for item in self.candidate_evidence)
            != tuple(
                sorted(
                    {
                        item.evidence_id for item in self.candidate_evidence
                    }
                )
            )
            or self.selected_evidence_id
            not in {item.evidence_id for item in self.candidate_evidence}
            or sum(
                item.changes_failed_to_certified
                for item in self.candidate_evidence
            )
            < 1
            or not self.selected_novel_outcome_ids
            or type(self.selected_remaining_horizon) is not int
            or self.selected_remaining_horizon not in (1, 2)
            or self.checkpoint_draw_count
            not in acquisition.VALIDATION_CHECKPOINTS
            or self.earliest_row_order != EARLIEST_ROW_ORDER
            or self.authorization_scope != "ONE_ROW_ONE_NEXT_SUPPORT_EPOCH"
        ):
            raise PartialSupportExpansionInvariantViolation(
                "partial-support expansion authorization is malformed"
            )
        selected = next(
            item
            for item in self.candidate_evidence
            if item.evidence_id == self.selected_evidence_id
        )
        causal = tuple(
            item
            for item in self.candidate_evidence
            if item.changes_failed_to_certified
        )
        expected = min(
            causal,
            key=lambda item: (-item.remaining_horizon, item.planner_row_id),
        )
        if (
            selected != expected
            or selected.planner_row_id != self.selected_planner_row_id
            or selected.partial_row_id != self.selected_partial_row_id
            or selected.remaining_horizon != self.selected_remaining_horizon
        ):
            raise PartialSupportExpansionInvariantViolation(
                "authorization did not select the unique earliest causal row"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_expansion_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "bridge_id": self.bridge_id,
            "context_id": self.context_id,
            "parent_model_id": self.parent_model_id,
            "parent_audit_id": self.parent_audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "solver_kind": self.solver_kind.value,
            "assignment_ids": list(self.assignment_ids),
            "frontier_id": self.frontier_id,
            "source_partial_row_ids": list(self.source_partial_row_ids),
            "candidate_evidence_ids": [
                item.evidence_id for item in self.candidate_evidence
            ],
            "selected_evidence_id": self.selected_evidence_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "selected_partial_row_id": self.selected_partial_row_id,
            "selected_parent_physical_evidence_id": (
                self.selected_parent_physical_evidence_id
            ),
            "selected_parent_support_epoch_id": (
                self.selected_parent_support_epoch_id
            ),
            "selected_parent_confidence_authority_id": (
                self.selected_parent_confidence_authority_id
            ),
            "selected_remaining_horizon": self.selected_remaining_horizon,
            "selected_novel_outcome_ids": list(
                self.selected_novel_outcome_ids
            ),
            "checkpoint_draw_count": self.checkpoint_draw_count,
            "earliest_row_order": self.earliest_row_order,
            "authorization_scope": self.authorization_scope,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate_evidence": [
                item.to_document() for item in self.candidate_evidence
            ],
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class PartialSupportPendingModelEpochV1:
    """Binding for a replacement row whose reachable closure must be rebuilt."""

    authorization_id: str
    context_id: str
    parent_bridge_id: str
    parent_model_id: str
    parent_source_partial_row_ids: tuple[str, ...]
    replaced_parent_partial_row_id: str
    promoted_partial_row_id: str
    parent_support_epoch_id: str
    promoted_support_epoch_id: str
    promoted_confidence_authority_id: str
    promoted_observer_epoch_id: str
    promoted_outcome_ids: tuple[str, ...]
    fresh_validation_observation_ids: tuple[str, ...]
    quarantined_parent_observation_ids: tuple[str, ...]
    closure_rebuild_required: bool = True
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.authorization_id, "model epoch authorization"),
            (self.context_id, "model epoch context"),
            (self.parent_bridge_id, "model epoch parent bridge"),
            (self.parent_model_id, "model epoch parent model"),
            (
                self.replaced_parent_partial_row_id,
                "model epoch replaced row",
            ),
            (self.promoted_partial_row_id, "model epoch promoted row"),
            (self.parent_support_epoch_id, "model epoch parent support"),
            (self.promoted_support_epoch_id, "model epoch promoted support"),
            (
                self.promoted_confidence_authority_id,
                "model epoch promoted confidence",
            ),
            (
                self.promoted_observer_epoch_id,
                "model epoch promoted observer epoch",
            ),
        ):
            _cid(value, field)
        for values, field in (
            (
                self.parent_source_partial_row_ids,
                "model epoch parent source rows",
            ),
            (self.promoted_outcome_ids, "model epoch promoted outcomes"),
            (
                self.fresh_validation_observation_ids,
                "model epoch fresh validation",
            ),
            (
                self.quarantined_parent_observation_ids,
                "model epoch quarantined parent observations",
            ),
        ):
            _ids(values, field)
        if (
            self.replaced_parent_partial_row_id
            not in self.parent_source_partial_row_ids
            or not self.promoted_outcome_ids
            or not self.fresh_validation_observation_ids
            or not self.quarantined_parent_observation_ids
            or set(self.fresh_validation_observation_ids)
            & set(self.quarantined_parent_observation_ids)
            or self.closure_rebuild_required is not True
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
        ):
            raise PartialSupportExpansionInvariantViolation(
                "pending model epoch binding is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_pending_model_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization_id,
            "context_id": self.context_id,
            "parent_bridge_id": self.parent_bridge_id,
            "parent_model_id": self.parent_model_id,
            "parent_source_partial_row_ids": list(
                self.parent_source_partial_row_ids
            ),
            "replaced_parent_partial_row_id": (
                self.replaced_parent_partial_row_id
            ),
            "promoted_partial_row_id": self.promoted_partial_row_id,
            "parent_support_epoch_id": self.parent_support_epoch_id,
            "promoted_support_epoch_id": self.promoted_support_epoch_id,
            "promoted_confidence_authority_id": (
                self.promoted_confidence_authority_id
            ),
            "promoted_observer_epoch_id": self.promoted_observer_epoch_id,
            "promoted_outcome_ids": list(self.promoted_outcome_ids),
            "fresh_validation_observation_ids": list(
                self.fresh_validation_observation_ids
            ),
            "quarantined_parent_observation_ids": list(
                self.quarantined_parent_observation_ids
            ),
            "closure_rebuild_required": True,
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
        }

    @property
    def pending_model_epoch_id(self) -> str:
        return _content_id("model_epoch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "pending_model_epoch_id": self.pending_model_epoch_id,
        }


@dataclass(frozen=True, slots=True)
class PartialSupportPromotedRowReplacementV1:
    authorization: PartialSupportExpansionAuthorizationV1
    parent_row: acquisition.GraphPartialSupportRowV1
    promoted_row: acquisition.GraphPartialSupportRowV1
    pending_model_epoch: PartialSupportPendingModelEpochV1

    def __post_init__(self) -> None:
        if (
            type(self.authorization)
            is not PartialSupportExpansionAuthorizationV1
            or type(self.parent_row) is not acquisition.GraphPartialSupportRowV1
            or type(self.promoted_row)
            is not acquisition.GraphPartialSupportRowV1
            or type(self.pending_model_epoch)
            is not PartialSupportPendingModelEpochV1
            or self.authorization.selected_partial_row_id
            != self.parent_row.partial_row_id
            or self.promoted_row.parent_row != self.parent_row
            or self.pending_model_epoch.authorization_id
            != self.authorization.authorization_id
            or self.pending_model_epoch.replaced_parent_partial_row_id
            != self.parent_row.partial_row_id
            or self.pending_model_epoch.promoted_partial_row_id
            != self.promoted_row.partial_row_id
        ):
            raise PartialSupportExpansionInvariantViolation(
                "promoted row replacement is not authorization-bound"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_support_promoted_row_replacement.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authorization_id": self.authorization.authorization_id,
            "parent_partial_row_id": self.parent_row.partial_row_id,
            "promoted_partial_row_id": self.promoted_row.partial_row_id,
            "pending_model_epoch_id": (
                self.pending_model_epoch.pending_model_epoch_id
            ),
        }

    @property
    def replacement_id(self) -> str:
        return _content_id("replacement", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization": self.authorization.to_document(),
            "promoted_row": self.promoted_row.to_document(),
            "pending_model_epoch": self.pending_model_epoch.to_document(),
            "replacement_id": self.replacement_id,
        }


def _model_for_audit(
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
) -> robust.PartialSupportIntervalModelV1:
    if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        return bridge.direct_model
    if audit.solver_kind is robust.RobustSolverKind.QUOTIENT:
        return bridge.quotient_model
    raise PartialSupportExpansionInvariantViolation(
        "audit solver kind is not registered"
    )


def _solve(
    model: robust.PartialSupportIntervalModelV1,
    threshold: robust.RobustThresholdProfileV1,
    solver_kind: robust.RobustSolverKind,
) -> robust.RobustPlanAuditV1:
    if solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        return robust.solve_ground_direct_robust_h2_v1(model, threshold)
    return robust.solve_quotient_robust_h2_v1(model, threshold)


def _single_row_zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> robust.PartialSupportIntervalModelV1:
    matches = tuple(item for item in model.rows if item.row_id == planner_row_id)
    if len(matches) != 1:
        raise PartialSupportExpansionInvariantViolation(
            "selected planner row is absent or duplicated"
        )
    selected = matches[0]
    masses = tuple(
        (
            robust.IntervalDestinationMassV1(
                item.destination_id,
                Fraction(0),
                Fraction(0),
            )
            if item.destination_id == selected.other_destination_id
            else item
        )
        for item in selected.masses
    )
    replacement_row = replace(selected, masses=masses)
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=(
            replacement_row if item.row_id == planner_row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _row_mapping(
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> tuple[
    dict[str, acquisition.GraphPartialSupportRowV1],
    dict[str, graph_model.GraphRowModelProjectionV1],
]:
    if (
        type(rows) is not tuple
        or not rows
        or any(type(item) is not acquisition.GraphPartialSupportRowV1 for item in rows)
        or tuple(sorted(item.partial_row_id for item in rows))
        != bridge.source_partial_row_ids
        or len({item.partial_row_id for item in rows}) != len(rows)
        or any(item.binding.context_id != bridge.context_id for item in rows)
    ):
        raise PartialSupportExpansionInvariantViolation(
            "partial rows do not exactly reproduce the authority-bound bridge"
        )
    by_partial = {item.partial_row_id: item for item in rows}
    by_planner: dict[str, graph_model.GraphRowModelProjectionV1] = {}
    for projection in bridge.row_projections:
        if projection.partial_row_id not in by_partial:
            raise PartialSupportExpansionInvariantViolation(
                "bridge projection has no exact source row"
            )
        if projection.planner_row.row_id in by_planner:
            raise PartialSupportExpansionInvariantViolation(
                "bridge has duplicate planner-row projections"
            )
        by_planner[projection.planner_row.row_id] = projection
    return by_partial, by_planner


def _validate_inputs(
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    dict[str, acquisition.GraphPartialSupportRowV1],
    dict[str, graph_model.GraphRowModelProjectionV1],
]:
    if (
        type(bridge)
        is not graph_model.ObservationSupportGraphModelBridgeV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or bridge.context_id != threshold.context_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
        or not audit.failed_frontier.other_only_counterfactual_changes
        or not audit.counterfactual.changes_failed_to_certified
    ):
        raise PartialSupportExpansionInvariantViolation(
            "support expansion requires one matching causal failed audit"
        )
    model = _model_for_audit(bridge, audit)
    if audit.model_id != model.model_id:
        raise PartialSupportExpansionInvariantViolation(
            "audit was transplanted from another bridge/model"
        )
    try:
        robust.verify_robust_plan_audit_v1(model, threshold, audit)
    except (ValueError, TypeError) as error:
        raise PartialSupportExpansionInvariantViolation(
            f"robust audit semantic replay failed: {error}"
        ) from error
    by_partial, by_planner = _row_mapping(bridge, rows)
    selected_ids = {
        item.row_id for item in audit.selected_row_bounds
    }
    provenance_ids = {
        item.row_id for item in audit.selected_row_provenance
    }
    other_ids = {
        item.row_id
        for item in audit.other_mass_upper_on_selected_policy
        if item.other_mass_upper > 0
    }
    frontier = audit.failed_frontier
    if (
        selected_ids != provenance_ids
        or selected_ids != set(frontier.selected_row_ids)
        or other_ids != set(frontier.other_positive_row_ids)
        or not other_ids
        or not other_ids.issubset(by_planner)
    ):
        raise PartialSupportExpansionInvariantViolation(
            "failed frontier does not exactly match selected row provenance"
        )
    return model, by_partial, by_planner


def _candidate_evidence(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    projection: graph_model.GraphRowModelProjectionV1,
) -> RowOtherCounterfactualEvidenceV1:
    row = projection.planner_row
    try:
        zero_model = _single_row_zero_other_model(model, row.row_id)
    except robust.PartialSupportRobustPlannerInvariantViolation:
        return RowOtherCounterfactualEvidenceV1(
            model.model_id,
            audit.audit_id,
            threshold.threshold_profile_id,
            row.row_id,
            projection.partial_row_id,
            row.remaining_horizon,
            None,
            None,
            RowCounterfactualStatus.INFEASIBLE_SIMPLEX,
            False,
        )
    replay = _solve(zero_model, threshold, audit.solver_kind)
    changed = replay.status is robust.RobustAuditStatus.CERTIFIED
    return RowOtherCounterfactualEvidenceV1(
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        row.row_id,
        projection.partial_row_id,
        row.remaining_horizon,
        zero_model.model_id,
        replay.audit_id,
        (
            RowCounterfactualStatus.CERTIFICATE_CHANGED
            if changed
            else RowCounterfactualStatus.STILL_FAILED
        ),
        changed,
    )


@dataclass(frozen=True, slots=True)
class _CandidateEvidenceTaskV1:
    model: robust.PartialSupportIntervalModelV1
    audit: robust.RobustPlanAuditV1
    threshold: robust.RobustThresholdProfileV1
    projection: graph_model.GraphRowModelProjectionV1


def _candidate_evidence_task_v1(
    task: _CandidateEvidenceTaskV1,
) -> RowOtherCounterfactualEvidenceV1:
    return _candidate_evidence(
        task.model,
        task.audit,
        task.threshold,
        task.projection,
    )


def authorize_partial_support_expansion_v1(
    *,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    partial_rows: Iterable[acquisition.GraphPartialSupportRowV1],
    checkpoint_draw_count: int = acquisition.VALIDATION_CHECKPOINTS[0],
) -> PartialSupportExpansionAuthorizationV1:
    """Authorize the unique earliest individually causal row, or fail closed."""

    rows = tuple(partial_rows)
    model, by_partial, by_planner = _validate_inputs(
        bridge,
        audit,
        threshold,
        rows,
    )
    assert audit.failed_frontier is not None
    tasks = tuple(
        _CandidateEvidenceTaskV1(
            model,
            audit,
            threshold,
            by_planner[row_id],
        )
        for row_id in audit.failed_frontier.other_positive_row_ids
    )
    real_operational_rows = bool(rows) and all(
        type(item).__module__
        == "acfqp.observation_support_graph_acquisition_v1"
        and type(item).__name__ == "GraphPartialSupportRowV1"
        for item in rows
    )
    if real_operational_rows and len(tasks) > 1:
        workers = min(
            MAX_COUNTERFACTUAL_WORKERS,
            len(tasks),
            os.cpu_count() or 1,
        )
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=get_context("spawn"),
        ) as executor:
            raw_candidates = tuple(
                executor.map(_candidate_evidence_task_v1, tasks)
            )
    else:
        raw_candidates = tuple(
            _candidate_evidence_task_v1(task) for task in tasks
        )
    candidates = tuple(
        sorted(raw_candidates, key=lambda item: item.evidence_id)
    )
    causal = tuple(
        item for item in candidates if item.changes_failed_to_certified
    )
    if not causal:
        raise PartialSupportExpansionInvariantViolation(
            "no selected row is individually causal for the failed proof"
        )
    selected = min(
        causal,
        key=lambda item: (-item.remaining_horizon, item.planner_row_id),
    )
    parent = by_partial[selected.partial_row_id]
    if (
        parent.support_epoch_index != 1
        or not parent.novel_descriptors
    ):
        raise PartialSupportExpansionInvariantViolation(
            "earliest causal row has no promotable novel epoch-1 outcomes"
        )
    novel_ids = tuple(
        sorted(item.outcome_id for item in parent.novel_descriptors)
    )
    assignment_ids = tuple(
        sorted(item.assignment_id for item in audit.assignments)
    )
    return PartialSupportExpansionAuthorizationV1(
        bridge.bridge_id,
        bridge.context_id,
        model.model_id,
        audit.audit_id,
        threshold.threshold_profile_id,
        audit.solver_kind,
        assignment_ids,
        audit.failed_frontier.frontier_id,
        bridge.source_partial_row_ids,
        candidates,
        selected.evidence_id,
        selected.planner_row_id,
        selected.partial_row_id,
        parent.physical_evidence_id,
        parent.support_epoch.support_epoch_id,
        parent.confidence_authority.authority_id,
        selected.remaining_horizon,
        novel_ids,
        checkpoint_draw_count,
    )


def _registered_context(
    context_id: str,
) -> observer.PublicGraphContextV1:
    matches = tuple(
        item
        for item in observer.registered_public_graph_contexts_v1()
        if item.context_id == context_id
    )
    if len(matches) != 1:
        raise PartialSupportExpansionInvariantViolation(
            "authorization context is no longer registered"
        )
    return matches[0]


def _catalogue_for_selected_row(
    *,
    context: observer.PublicGraphContextV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    parent: acquisition.GraphPartialSupportRowV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> tuple[observer.LegalActionCatalogueV1, tuple[int, int, int]]:
    action_matches = tuple(
        item
        for item in bridge.action_bindings
        if (
            item.catalogue_id == parent.binding.catalogue_id
            and item.state_id == parent.binding.state_id
            and item.remaining_horizon == parent.binding.remaining_horizon
            and item.action == parent.binding.action
        )
    )
    if len(action_matches) != 1:
        raise PartialSupportExpansionInvariantViolation(
            "selected row has no unique public action binding"
        )
    action_binding = action_matches[0]
    if action_binding.remaining_horizon == 2:
        state = observer.root_state_v1(context)
    else:
        states = {
            descriptor.next_state
            for row in rows
            for descriptor in row.support_descriptors
            if (
                not descriptor.failure
                and not descriptor.terminal
                and descriptor.next_state.state_id == action_binding.state_id
            )
        }
        if len(states) != 1:
            raise PartialSupportExpansionInvariantViolation(
                "selected continuation state lacks unique observed provenance"
            )
        state = next(iter(states))
    catalogue = observer.legal_action_catalogue_v1(
        context,
        state,
        action_binding.remaining_horizon,
    )
    if (
        catalogue.catalogue_id != action_binding.catalogue_id
        or action_binding.action not in catalogue.actions
        or catalogue.state.state_id != action_binding.state_id
    ):
        raise PartialSupportExpansionInvariantViolation(
            "reconstructed public catalogue differs from the bridge binding"
        )
    return catalogue, action_binding.action


def _validate_fresh_promotion(
    parent: acquisition.GraphPartialSupportRowV1,
    promoted: acquisition.GraphPartialSupportRowV1,
    authorization: PartialSupportExpansionAuthorizationV1,
) -> None:
    old_ids = tuple(
        sorted(
            {
                *parent.initial_discovery_observation_ids,
                *parent.prior_validation_observation_ids,
                *parent.current_validation_observation_ids,
            }
        )
    )
    new_ids = tuple(sorted(promoted.current_validation_observation_ids))
    promoted_support_ids = tuple(
        sorted(item.outcome_id for item in promoted.support_descriptors)
    )
    required_support_ids = {
        *(item.outcome_id for item in parent.support_descriptors),
        *authorization.selected_novel_outcome_ids,
    }
    if (
        promoted.parent_row != parent
        or promoted.binding != parent.binding
        or promoted.support_epoch_index != parent.support_epoch_index + 1
        or promoted.support_epoch_index != MAX_SUPPORT_EPOCH_INDEX
        or promoted.prior_validation_observation_ids
        != (
            parent.prior_validation_observation_ids
            + parent.current_validation_observation_ids
        )
        or len(new_ids) != authorization.checkpoint_draw_count
        or len(set(new_ids)) != len(new_ids)
        or set(old_ids) & set(new_ids)
        or not required_support_ids.issubset(promoted_support_ids)
        or tuple(
            promoted.confidence_authority.validation_evidence.sample_ids
        )
        != promoted.current_validation_observation_ids
        or not set(old_ids).issubset(
            promoted.support_epoch.excluded_probability_sample_ids
        )
    ):
        raise PartialSupportExpansionInvariantViolation(
            "promoted row reused old samples or changed its authorized lineage"
        )


def promote_authorized_partial_support_row_v1(
    *,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    partial_rows: Iterable[acquisition.GraphPartialSupportRowV1],
    authorization: PartialSupportExpansionAuthorizationV1,
) -> PartialSupportPromotedRowReplacementV1:
    """Execute one authorization-bound promotion with fresh validation."""

    rows = tuple(partial_rows)
    if (
        type(authorization)
        is not PartialSupportExpansionAuthorizationV1
    ):
        raise PartialSupportExpansionInvariantViolation(
            "row promotion requires a typed causal authorization"
        )
    expected = authorize_partial_support_expansion_v1(
        bridge=bridge,
        audit=audit,
        threshold=threshold,
        partial_rows=rows,
        checkpoint_draw_count=authorization.checkpoint_draw_count,
    )
    if (
        expected != authorization
        or expected.authorization_id != authorization.authorization_id
    ):
        raise PartialSupportExpansionInvariantViolation(
            "stale or transplanted expansion authorization"
        )
    by_partial = {item.partial_row_id: item for item in rows}
    parent = by_partial[authorization.selected_partial_row_id]
    context = _registered_context(authorization.context_id)
    catalogue, action = _catalogue_for_selected_row(
        context=context,
        bridge=bridge,
        parent=parent,
        rows=rows,
    )
    promoted = acquisition.promote_graph_partial_support_row_v1(
        parent,
        context,
        catalogue,
        action,
        authorization.checkpoint_draw_count,
    )
    _validate_fresh_promotion(parent, promoted, authorization)
    old_ids = tuple(
        sorted(
            {
                *parent.initial_discovery_observation_ids,
                *parent.prior_validation_observation_ids,
                *parent.current_validation_observation_ids,
            }
        )
    )
    pending = PartialSupportPendingModelEpochV1(
        authorization.authorization_id,
        authorization.context_id,
        authorization.bridge_id,
        authorization.parent_model_id,
        authorization.source_partial_row_ids,
        parent.partial_row_id,
        promoted.partial_row_id,
        parent.support_epoch.support_epoch_id,
        promoted.support_epoch.support_epoch_id,
        promoted.confidence_authority.authority_id,
        promoted.observer_epoch_chain[-1].epoch_id,
        tuple(
            sorted(item.outcome_id for item in promoted.support_descriptors)
        ),
        tuple(sorted(promoted.current_validation_observation_ids)),
        old_ids,
    )
    return PartialSupportPromotedRowReplacementV1(
        authorization,
        parent,
        promoted,
        pending,
    )


__all__ = [
    "CONTRACT_VERSION",
    "EARLIEST_ROW_ORDER",
    "MAX_COUNTERFACTUAL_WORKERS",
    "MAX_SUPPORT_EPOCH_INDEX",
    "PROFILE_KEY",
    "PartialSupportExpansionAuthorizationV1",
    "PartialSupportExpansionInvariantViolation",
    "PartialSupportPendingModelEpochV1",
    "PartialSupportPromotedRowReplacementV1",
    "RowCounterfactualStatus",
    "RowOtherCounterfactualEvidenceV1",
    "authorize_partial_support_expansion_v1",
    "promote_authorized_partial_support_row_v1",
]
