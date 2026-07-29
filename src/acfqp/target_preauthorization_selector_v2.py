"""Preauthorization-only target-row selection for V0-072.

This module stops at a frozen authorization.  It has no observer,
materializer, worker, kernel, or certificate-emission API.  Candidate rows
come only from the current failed selected-policy frontier.  Their costs are
derived from frozen public action catalogues, while their gains are derived
by an exact one-row zero-``OTHER`` fixed-policy counterfactual.

Source information is a ranking overlay only.  The source-free
counterfactual artifacts are content-addressed independently of every source
prior and explicitly carry an empty certificate-input source field.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping, Sequence

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import verified_source_acquisition_archive_v2 as source_v2


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_preauthorization_only_target_selector_v0"
SAMPLE_EFFICIENCY_GATE_STATUS = "NOT_RUN"

MAX_ROUNDS = 2
MAX_FRONTIER_ROWS = 64
MAX_NEW_CHILD_ACTIONS_TOTAL = 19
PROMOTED_ROW_DRAWS = 2_048
CHILD_DISCOVERY_DRAWS = 64
CHILD_VALIDATION_DRAWS = 8_192
CHILD_ACTION_DRAWS = CHILD_DISCOVERY_DRAWS + CHILD_VALIDATION_DRAWS
MAX_TWO_ROUND_DRAW_UPPER = (
    MAX_ROUNDS * PROMOTED_ROW_DRAWS
    + MAX_NEW_CHILD_ACTIONS_TOTAL * CHILD_ACTION_DRAWS
)

ADAPTIVE_ARMS = (
    "SOURCE_CONSENSUS_PRIOR",
    "NO_PRIOR",
    "WRONG_CONSENSUS_PRIOR",
    "OOD_ABSTENTION",
)

REQUIRED_NATIVE_ZERO_PATHS = (
    "target_observer.calls",
    "target_observer.random_word_calls",
    "target_observer.accepted_draws",
    "target_materializer.calls",
    "target_materializer.ground_transition_calls",
    "target_worker.launches",
)


class TargetPreauthorizationSelectorV2InvariantViolation(ValueError):
    """A target selector identity, derivation, cap, or access invariant failed."""


class TargetSelectionArmV2(str, Enum):
    SOURCE_CONSENSUS_PRIOR = "SOURCE_CONSENSUS_PRIOR"
    NO_PRIOR = "NO_PRIOR"
    WRONG_CONSENSUS_PRIOR = "WRONG_CONSENSUS_PRIOR"
    OOD_ABSTENTION = "OOD_ABSTENTION"


class CounterfactualEvaluationStatusV2(str, Enum):
    EVALUATED = "EVALUATED"
    MASS_PRESERVING_OPTIMISTIC_RESOLUTION = (
        "MASS_PRESERVING_OPTIMISTIC_RESOLUTION"
    )
    INFEASIBLE_SIMPLEX = "INFEASIBLE_SIMPLEX"


class PriorResolutionKindV2(str, Enum):
    SOURCE_ARCHIVE_APPLIED = "SOURCE_ARCHIVE_APPLIED"
    NO_PRIOR = "NO_PRIOR"
    OOD_TYPED_ABSTENTION = "OOD_TYPED_ABSTENTION"


TARGET_FEATURE_DISPOSITIONS = (
    "APPLIED",
    "UNSEEN",
    "INSUFFICIENT_CONTEXTS",
    "DEGENERATE_CONTEXT_RANKING",
    "HIGH_DISAGREEMENT",
    "NONPOSITIVE_SOURCE_GAIN",
    "SCHEMA_MISMATCH",
)


DOMAIN_TAGS = {
    "row_metadata": "acfqp:v072-frontier-row-public-action-metadata:v2",
    "public_metadata": "acfqp:v072-frontier-public-action-metadata:v2",
    "candidate": "acfqp:v072-target-acquisition-candidate:v2",
    "registry": "acfqp:v072-target-candidate-registry:v2",
    "source_binding": "acfqp:v072-verified-source-prior-binding:v2",
    "ood_abstention": "acfqp:v072-ood-prior-typed-abstention:v2",
    "counterfactual": "acfqp:v072-one-row-counterfactual-gain:v2",
    "optimistic_destination": (
        "acfqp:v072-row-bound-optimistic-success-destination:v2"
    ),
    "optimistic_resolution": (
        "acfqp:v072-mass-preserving-optimistic-resolution:v2"
    ),
    "score": "acfqp:v072-arm-ranking-score:v2",
    "schedule_entry": "acfqp:v072-selection-schedule-entry:v2",
    "schedule": "acfqp:v072-selection-schedule-core:v2",
    "native_zero": "acfqp:v072-preauthorization-native-zero:v2",
    "access": "acfqp:v072-preauthorization-access-log:v2",
    "authorization": "acfqp:v072-target-row-authorization:v2",
    "prepared": "acfqp:v072-prepared-target-selection:v2",
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "target selector arithmetic must remain exact"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _maybe_fdoc(value: Fraction | None) -> dict[str, int] | None:
    return None if value is None else _fdoc(value)


def _ids(
    values: Sequence[str],
    field: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            f"{field} must be an immutable tuple"
        )
    output = tuple(_cid(value, field) for value in values)
    if (
        (not allow_empty and not output)
        or output != tuple(sorted(set(output)))
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            f"{field} must be content-ID sorted and distinct"
        )
    return output


def _arm(value: Any) -> TargetSelectionArmV2:
    if type(value) is not TargetSelectionArmV2:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "selector arm is not one registered adaptive arm"
        )
    return value


def exact_preexecution_draw_upper_v2(
    n_new_child_actions: int,
) -> int:
    """Legacy/development count formula; never confirmatory evidence.

    The confirmatory evidence-first path derives its integer upper from the
    complete content-addressed physical-row list and does not call this API.
    """

    if (
        type(n_new_child_actions) is not int
        or not 0 <= n_new_child_actions <= MAX_NEW_CHILD_ACTIONS_TOTAL
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "new-child action cardinality exceeds the registered cap"
        )
    return (
        PROMOTED_ROW_DRAWS
        + n_new_child_actions * CHILD_ACTION_DRAWS
    )


@dataclass(frozen=True, slots=True)
class FrontierRowPublicActionMetadataV2:
    """Public, result-blind materialization cardinality for one frontier row."""

    planner_row_id: str
    state_id: str
    action_id: str
    remaining_horizon: int
    newly_reachable_child_catalogues: tuple[
        robust.StateActionCatalogueV1, ...
    ]
    complete_for_bound_row: bool = True
    transition_outcomes_absent: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.planner_row_id, "public metadata planner row"),
            (self.state_id, "public metadata state"),
            (self.action_id, "public metadata action"),
        ):
            _cid(value, field)
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.newly_reachable_child_catalogues) is not tuple
            or any(
                type(item) is not robust.StateActionCatalogueV1
                for item in self.newly_reachable_child_catalogues
            )
            or tuple(
                item.catalogue_id
                for item in self.newly_reachable_child_catalogues
            )
            != tuple(
                sorted(
                    {
                        item.catalogue_id
                        for item in self.newly_reachable_child_catalogues
                    }
                )
            )
            or (
                self.remaining_horizon == 1
                and self.newly_reachable_child_catalogues
            )
            or self.n_new_child_actions > MAX_NEW_CHILD_ACTIONS_TOTAL
            or self.complete_for_bound_row is not True
            or self.transition_outcomes_absent is not True
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "public row/action cardinality metadata is malformed"
            )

    @property
    def n_new_child_actions(self) -> int:
        return sum(
            len(item.actions)
            for item in self.newly_reachable_child_catalogues
        )

    @property
    def exact_draw_upper(self) -> int:
        return exact_preexecution_draw_upper_v2(
            self.n_new_child_actions
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_frontier_row_public_action_metadata.v2",
            "schema_version": SCHEMA_VERSION,
            "planner_row_id": self.planner_row_id,
            "state_id": self.state_id,
            "action_id": self.action_id,
            "remaining_horizon": self.remaining_horizon,
            "new_child_catalogue_ids": [
                item.catalogue_id
                for item in self.newly_reachable_child_catalogues
            ],
            "n_new_child_actions": self.n_new_child_actions,
            "exact_draw_formula": (
                "2048+n_new_child_actions*(64+8192)"
            ),
            "exact_draw_upper": self.exact_draw_upper,
            "complete_for_bound_row": True,
            "transition_outcomes_absent": True,
            "execution_role": "LEGACY_DEVELOPMENT_NONCONFIRMATORY",
            "confirmatory_execution_allowed": False,
            "full_physical_row_list_evidence": False,
        }

    @property
    def metadata_id(self) -> str:
        return _content_id("row_metadata", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "newly_reachable_child_catalogues": [
                item.to_document()
                for item in self.newly_reachable_child_catalogues
            ],
            "metadata_id": self.metadata_id,
        }


@dataclass(frozen=True, slots=True)
class PublicFrontierActionCatalogueMetadataV2:
    model_id: str
    audit_id: str
    frontier_id: str
    support_epoch_id: str
    rows: tuple[FrontierRowPublicActionMetadataV2, ...]
    public_catalogue_only: bool = True
    observer_calls: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.model_id, "public metadata model"),
            (self.audit_id, "public metadata audit"),
            (self.frontier_id, "public metadata frontier"),
            (self.support_epoch_id, "public metadata support epoch"),
        ):
            _cid(value, field)
        if (
            type(self.rows) is not tuple
            or not self.rows
            or len(self.rows) > MAX_FRONTIER_ROWS
            or any(
                type(item) is not FrontierRowPublicActionMetadataV2
                for item in self.rows
            )
            or tuple(item.metadata_id for item in self.rows)
            != tuple(sorted({item.metadata_id for item in self.rows}))
            or len({item.planner_row_id for item in self.rows})
            != len(self.rows)
            or self.public_catalogue_only is not True
            or self.observer_calls != 0
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "frontier public action metadata is noncanonical"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_frontier_public_action_metadata.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "support_epoch_id": self.support_epoch_id,
            "row_metadata_ids": [
                item.metadata_id for item in self.rows
            ],
            "public_catalogue_only": True,
            "transition_outcomes_absent": True,
            "observer_calls": 0,
            "execution_role": "LEGACY_DEVELOPMENT_NONCONFIRMATORY",
            "confirmatory_execution_allowed": False,
            "full_physical_row_list_evidence": False,
        }

    @property
    def public_metadata_id(self) -> str:
        return _content_id("public_metadata", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "rows": [item.to_document() for item in self.rows],
            "public_metadata_id": self.public_metadata_id,
        }


def freeze_public_frontier_action_metadata_v2(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    support_epoch_id: str,
    newly_reachable_child_catalogues_by_row: Mapping[
        str, tuple[robust.StateActionCatalogueV1, ...]
    ],
) -> PublicFrontierActionCatalogueMetadataV2:
    """Freeze historical/development-only caller metadata.

    This compatibility path is nonconfirmatory and cannot substitute for
    ``PublicNovelChildCardinalityEvidenceV2``.
    """

    _cid(support_epoch_id, "support epoch")
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or audit.model_id != model.model_id
        or audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
        or type(newly_reachable_child_catalogues_by_row) is not dict
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "public metadata requires one immutable failed model/audit"
        )
    frontier_rows = audit.failed_frontier.selected_row_ids
    if (
        set(newly_reachable_child_catalogues_by_row) != set(frontier_rows)
        or len(frontier_rows) > MAX_FRONTIER_ROWS
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "public metadata must cover exactly the failed frontier rows"
        )
    row_by_id = {item.row_id: item for item in model.rows}
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    currently_reachable = set(robust._reachable_child_states(model))
    rows: list[FrontierRowPublicActionMetadataV2] = []
    for row_id in frontier_rows:
        row = row_by_id.get(row_id)
        catalogues = newly_reachable_child_catalogues_by_row[row_id]
        if (
            row is None
            or type(catalogues) is not tuple
            or any(
                catalogue_by_state.get(item.state_id) != item
                for item in catalogues
            )
            or any(
                item.state_id in currently_reachable
                for item in catalogues
            )
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "new-child catalogues are stale, private, or already reachable"
            )
        rows.append(
            FrontierRowPublicActionMetadataV2(
                row.row_id,
                row.state_id,
                row.action_id,
                row.remaining_horizon,
                tuple(
                    sorted(catalogues, key=lambda item: item.catalogue_id)
                ),
            )
        )
    return PublicFrontierActionCatalogueMetadataV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        support_epoch_id,
        tuple(sorted(rows, key=lambda item: item.metadata_id)),
    )


def _count_bin(value: int) -> str:
    if type(value) is not int or value < 0:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "portable feature count is invalid"
        )
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _portable_feature(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> source_v2.PortableAcquisitionCoreFeatureV2:
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    if provenance is None:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "frontier row lacks selected-policy provenance"
        )
    catalogue = {
        item.state_id: item for item in model.catalogues
    }[row.state_id]
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    action_key = assignment.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    if action_key is None:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "frontier row is not bound to the frozen selected action"
        )
    if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT:
        support_size = 1
    else:
        support_sizes = {
            len(item.ground_action_ids)
            for item in model.concretizer_entries
            if (
                item.state_id == row.state_id
                and item.abstract_action_key == action_key
            )
        }
        if len(support_sizes) != 1:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "frontier semantic action lacks one concretizer size"
            )
        support_size = next(iter(support_sizes))
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    categories = tuple(
        sorted(
            {
                destination_by_id[item.destination_id].category.value
                for item in row.masses
                if item.destination_id != row.other_destination_id
            }
        )
    )
    return source_v2.PortableAcquisitionCoreFeatureV2(
        "ROOT" if row.remaining_horizon == 2 else "CONTINUATION",
        provenance.category.value,
        _count_bin(len(catalogue.actions)),
        _count_bin(support_size),
        categories,
    )


@dataclass(frozen=True, slots=True)
class TargetAcquisitionCandidateV2:
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    support_epoch_id: str
    row_metadata: FrontierRowPublicActionMetadataV2
    feature: source_v2.PortableAcquisitionCoreFeatureV2

    def __post_init__(self) -> None:
        for value, field in (
            (self.model_id, "candidate model"),
            (self.audit_id, "candidate audit"),
            (self.frontier_id, "candidate frontier"),
            (self.threshold_profile_id, "candidate threshold"),
            (self.support_epoch_id, "candidate support epoch"),
        ):
            _cid(value, field)
        if (
            type(self.row_metadata)
            is not FrontierRowPublicActionMetadataV2
            or type(self.feature)
            is not source_v2.PortableAcquisitionCoreFeatureV2
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "target candidate lacks typed public metadata/feature"
            )

    @property
    def planner_row_id(self) -> str:
        return self.row_metadata.planner_row_id

    @property
    def n_new_child_actions(self) -> int:
        return self.row_metadata.n_new_child_actions

    @property
    def exact_draw_upper(self) -> int:
        return self.row_metadata.exact_draw_upper

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_target_acquisition_candidate.v2",
            "schema_version": SCHEMA_VERSION,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "support_epoch_id": self.support_epoch_id,
            "row_metadata_id": self.row_metadata.metadata_id,
            "planner_row_id": self.planner_row_id,
            "portable_feature_key": self.feature.feature_key,
            "n_new_child_actions": self.n_new_child_actions,
            "exact_preexecution_draw_upper": self.exact_draw_upper,
            "caller_supplied_gain": False,
            "caller_supplied_score": False,
            "execution_role": "LEGACY_DEVELOPMENT_NONCONFIRMATORY",
            "confirmatory_execution_allowed": False,
            "full_physical_row_list_evidence": False,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_metadata": self.row_metadata.to_document(),
            "portable_feature": self.feature.to_document(),
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class TargetCandidateRegistryV2:
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    support_epoch_id: str
    public_metadata_id: str
    round_index: int
    previous_registry_id: str | None
    previous_authorization_id: str | None
    cumulative_new_child_actions_before_round: int
    cumulative_draw_upper_before_round: int
    candidates: tuple[TargetAcquisitionCandidateV2, ...]
    fresh_from_current_frontier: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.model_id, "registry model"),
            (self.audit_id, "registry audit"),
            (self.frontier_id, "registry frontier"),
            (self.threshold_profile_id, "registry threshold"),
            (self.support_epoch_id, "registry support epoch"),
            (self.public_metadata_id, "registry public metadata"),
        ):
            _cid(value, field)
        if self.round_index == 1:
            if (
                self.previous_registry_id is not None
                or self.previous_authorization_id is not None
                or self.cumulative_new_child_actions_before_round != 0
                or self.cumulative_draw_upper_before_round != 0
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "round 1 cannot inherit a prior registry or budget"
                )
        elif self.round_index == 2:
            _cid(self.previous_registry_id, "previous registry")
            _cid(self.previous_authorization_id, "previous authorization")
            if (
                self.previous_registry_id == self.registry_id
                or self.cumulative_new_child_actions_before_round < 0
                or self.cumulative_draw_upper_before_round <= 0
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "round 2 lacks a distinct prior decision/budget"
                )
        else:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "target candidate registry round must be one or two"
            )
        if (
            type(self.cumulative_new_child_actions_before_round) is not int
            or self.cumulative_new_child_actions_before_round
            > MAX_NEW_CHILD_ACTIONS_TOTAL
            or type(self.cumulative_draw_upper_before_round) is not int
            or self.cumulative_draw_upper_before_round
            > MAX_TWO_ROUND_DRAW_UPPER
            or type(self.candidates) is not tuple
            or not self.candidates
            or len(self.candidates) > MAX_FRONTIER_ROWS
            or tuple(item.candidate_id for item in self.candidates)
            != tuple(sorted({item.candidate_id for item in self.candidates}))
            or {
                item.planner_row_id for item in self.candidates
            }
            != {
                item.row_metadata.planner_row_id
                for item in self.candidates
            }
            or any(
                (
                    item.model_id != self.model_id
                    or item.audit_id != self.audit_id
                    or item.frontier_id != self.frontier_id
                    or item.threshold_profile_id
                    != self.threshold_profile_id
                    or item.support_epoch_id != self.support_epoch_id
                )
                for item in self.candidates
            )
            or self.fresh_from_current_frontier is not True
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "target candidate registry is incomplete or stale"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_target_candidate_registry.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "support_epoch_id": self.support_epoch_id,
            "public_metadata_id": self.public_metadata_id,
            "round_index": self.round_index,
            "previous_registry": (
                {"kind": "NOT_APPLICABLE"}
                if self.previous_registry_id is None
                else {
                    "kind": "PREVIOUS_ROUND",
                    "registry_id": self.previous_registry_id,
                    "authorization_id": self.previous_authorization_id,
                }
            ),
            "cumulative_new_child_actions_before_round": (
                self.cumulative_new_child_actions_before_round
            ),
            "cumulative_draw_upper_before_round": (
                self.cumulative_draw_upper_before_round
            ),
            "candidate_ids": [
                item.candidate_id for item in self.candidates
            ],
            "fresh_from_current_frontier": True,
            "execution_role": "LEGACY_DEVELOPMENT_NONCONFIRMATORY",
            "confirmatory_execution_allowed": False,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidates": [item.to_document() for item in self.candidates],
            "registry_id": self.registry_id,
        }


@dataclass(frozen=True, slots=True)
class VerifiedSourcePriorBindingV2:
    """Portable ranking view whose canonical builder accepts only V2 archive."""

    archive_id: str
    feature_schema_id: str
    consensus: tuple[source_v2.NonrectangularFeatureConsensusV2, ...]
    source_frozen: bool = True
    may_certify: bool = False

    def __post_init__(self) -> None:
        _cid(self.archive_id, "source archive")
        if (
            self.feature_schema_id != source_v2.FEATURE_SCHEMA_ID
            or type(self.consensus) is not tuple
            or any(
                type(item)
                is not source_v2.NonrectangularFeatureConsensusV2
                for item in self.consensus
            )
            or tuple(item.consensus_id for item in self.consensus)
            != tuple(sorted({item.consensus_id for item in self.consensus}))
            or self.source_frozen is not True
            or self.may_certify is not False
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "verified source prior binding is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_verified_source_prior_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "archive_id": self.archive_id,
            "feature_schema_id": self.feature_schema_id,
            "consensus_ids": [
                item.consensus_id for item in self.consensus
            ],
            "source_frozen": True,
            "ranking_only": True,
            "may_certify": False,
        }

    @property
    def source_prior_binding_id(self) -> str:
        return _content_id("source_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "consensus": [item.to_document() for item in self.consensus],
            "source_prior_binding_id": self.source_prior_binding_id,
        }


def freeze_verified_source_prior_binding_v2(
    archive: source_v2.VerifiedSourceAcquisitionArchiveV2,
) -> VerifiedSourcePriorBindingV2:
    if type(archive) is not source_v2.VerifiedSourceAcquisitionArchiveV2:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "source prior builder requires the verified V2 archive"
        )
    return VerifiedSourcePriorBindingV2(
        archive.archive_id,
        source_v2.FEATURE_SCHEMA_ID,
        archive.consensus,
    )


@dataclass(frozen=True, slots=True)
class OodPriorTypedAbstentionV2:
    rejected_prior_id: str
    rejected_feature_schema_id: str
    reason: str = "SCHEMA_MISMATCH"
    source_numerical_inputs_absent: bool = True

    def __post_init__(self) -> None:
        _cid(self.rejected_prior_id, "OOD rejected prior")
        _cid(self.rejected_feature_schema_id, "OOD feature schema")
        if (
            self.rejected_feature_schema_id == source_v2.FEATURE_SCHEMA_ID
            or self.reason != "SCHEMA_MISMATCH"
            or self.source_numerical_inputs_absent is not True
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "OOD abstention must reject a mismatched schema without numbers"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_ood_prior_typed_abstention.v2",
            "schema_version": SCHEMA_VERSION,
            "rejected_prior_id": self.rejected_prior_id,
            "rejected_feature_schema_id": self.rejected_feature_schema_id,
            "reason": "SCHEMA_MISMATCH",
            "source_numerical_inputs": [],
            "source_numerical_inputs_absent": True,
            "ranking_multiplier": _fdoc(Fraction(1)),
        }

    @property
    def abstention_id(self) -> str:
        return _content_id("ood_abstention", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "abstention_id": self.abstention_id}


@dataclass(frozen=True, slots=True)
class OneRowCounterfactualGainV2:
    registry_id: str
    candidate_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    support_epoch_id: str
    planner_row_id: str
    exact_draw_upper: int
    status: CounterfactualEvaluationStatusV2
    zero_other_model_id: str | None
    current_slack: Fraction
    counterfactual_slack: Fraction | None
    gain: Fraction
    base: Fraction
    cardinality_evidence_id: str | None = None
    resolution_model_id: str | None = None
    resolution_destination_id: str | None = None
    optimistic_resolution_id: str | None = None

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "counterfactual registry"),
            (self.candidate_id, "counterfactual candidate"),
            (self.model_id, "counterfactual model"),
            (self.audit_id, "counterfactual audit"),
            (self.frontier_id, "counterfactual frontier"),
            (self.threshold_profile_id, "counterfactual threshold"),
            (self.support_epoch_id, "counterfactual support epoch"),
            (self.planner_row_id, "counterfactual row"),
        ):
            _cid(value, field)
        if self.zero_other_model_id is not None:
            _cid(self.zero_other_model_id, "zero-OTHER model")
        if self.cardinality_evidence_id is not None:
            _cid(
                self.cardinality_evidence_id,
                "public novel-child cardinality evidence",
            )
        for value, field in (
            (self.resolution_model_id, "optimistic resolution model"),
            (
                self.resolution_destination_id,
                "optimistic resolution destination",
            ),
            (
                self.optimistic_resolution_id,
                "optimistic resolution proof",
            ),
        ):
            if value is not None:
                _cid(value, field)
        if (
            type(self.exact_draw_upper) is not int
            or self.exact_draw_upper < PROMOTED_ROW_DRAWS
            or type(self.status)
            is not CounterfactualEvaluationStatusV2
            or type(self.current_slack) is not Fraction
            or type(self.gain) is not Fraction
            or type(self.base) is not Fraction
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "counterfactual gain has invalid exact fields"
            )
        if self.status is CounterfactualEvaluationStatusV2.EVALUATED:
            if (
                self.zero_other_model_id is None
                or self.resolution_model_id is not None
                or self.resolution_destination_id is not None
                or self.optimistic_resolution_id is not None
                or type(self.counterfactual_slack) is not Fraction
                or self.gain
                != max(
                    Fraction(0),
                    self.counterfactual_slack - self.current_slack,
                )
                or self.base != self.gain / self.exact_draw_upper
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "one-row exact gain/base was not derived"
                )
        elif (
            self.status
            is CounterfactualEvaluationStatusV2
            .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
        ):
            if (
                self.zero_other_model_id is not None
                or self.resolution_model_id is None
                or self.resolution_destination_id is None
                or self.optimistic_resolution_id is None
                or type(self.counterfactual_slack) is not Fraction
                or self.gain
                != max(
                    Fraction(0),
                    self.counterfactual_slack - self.current_slack,
                )
                or self.base != self.gain / self.exact_draw_upper
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "mass-preserving optimistic gain/base was not derived"
                )
        elif (
            self.zero_other_model_id is not None
            or self.resolution_model_id is not None
            or self.resolution_destination_id is not None
            or self.optimistic_resolution_id is not None
            or self.counterfactual_slack is not None
            or self.gain != 0
            or self.base != 0
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "infeasible counterfactual must be an ineligible zero"
            )

    @property
    def eligible(self) -> bool:
        return (
            self.status
            in (
                CounterfactualEvaluationStatusV2.EVALUATED,
                CounterfactualEvaluationStatusV2
                .MASS_PRESERVING_OPTIMISTIC_RESOLUTION,
            )
            and self.gain > 0
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_one_row_counterfactual_gain.v2",
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry_id,
            "candidate_id": self.candidate_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "support_epoch_id": self.support_epoch_id,
            "planner_row_id": self.planner_row_id,
            "exact_draw_upper": self.exact_draw_upper,
            "status": self.status.value,
            "zero_other_model_id": self.zero_other_model_id,
            "resolution_model_id": self.resolution_model_id,
            "resolution_destination_id": self.resolution_destination_id,
            "optimistic_resolution_id": self.optimistic_resolution_id,
            "resolution_semantics": (
                {
                    "kind": "MASS_PRESERVING_OPTIMISTIC_RESOLUTION",
                    "other_interval_preserved_exactly": True,
                    "resolved_as": "ROW_BOUND_SUCCESS_TERMINAL",
                    "proposal_only": True,
                    "certificate_authority": False,
                }
                if self.status
                is CounterfactualEvaluationStatusV2
                .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "ZERO_OTHER_OR_INFEASIBLE_COUNTERFACTUAL",
                }
            ),
            "current_slack": _fdoc(self.current_slack),
            "counterfactual_slack": _maybe_fdoc(
                self.counterfactual_slack
            ),
            "gain": _fdoc(self.gain),
            "base": _fdoc(self.base),
            "cardinality_evidence": (
                {
                    "kind": (
                        "LEGACY_DEVELOPMENT_PUBLIC_METADATA_WITHOUT_"
                        "FULL_ROW_LIST"
                    )
                }
                if self.cardinality_evidence_id is None
                else {
                    "kind": "PUBLIC_NOVEL_CHILD_FULL_ROW_LIST",
                    "cardinality_evidence_id": (
                        self.cardinality_evidence_id
                    ),
                }
            ),
            "eligible": self.eligible,
            "source_prior_inputs": [],
            "source_prior_inputs_absent": True,
            "ranking_only": True,
            "may_certify": False,
        }

    @property
    def counterfactual_id(self) -> str:
        return _content_id("counterfactual", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counterfactual_id": self.counterfactual_id,
        }


def derive_evidence_first_one_row_counterfactual_gain_v2(
    *,
    cardinality_evidence: Any,
    current_slack: Fraction,
    counterfactual_slack: Fraction,
    zero_other_model_id: str,
) -> OneRowCounterfactualGainV2:
    """Bind exact gain/base to a complete public row-list cost authority.

    This is the confirmatory V2 path.  The import is local to avoid a module
    cycle: the cardinality authority uses this module's immutable gain type.
    No row mapping, cardinality, or draw upper is accepted from the caller.
    """

    from acfqp import public_novel_child_cardinality_authority_v2 as child_v2

    if (
        type(cardinality_evidence)
        is not child_v2.PublicNovelChildCardinalityEvidenceV2
        or type(current_slack) is not Fraction
        or type(counterfactual_slack) is not Fraction
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "evidence-first gain requires exact full-row-list evidence/slack"
        )
    gain = max(Fraction(0), counterfactual_slack - current_slack)
    exact_upper = cardinality_evidence.exact_round_draw_upper
    return OneRowCounterfactualGainV2(
        _id_from_evidence(cardinality_evidence, "registry"),
        cardinality_evidence.selected_candidate_id,
        cardinality_evidence.model_id,
        cardinality_evidence.audit_id,
        cardinality_evidence.frontier_id,
        cardinality_evidence.threshold_profile_id,
        cardinality_evidence.parent_support_epoch_id,
        cardinality_evidence.selected_planner_row_id,
        exact_upper,
        CounterfactualEvaluationStatusV2.EVALUATED,
        _cid(zero_other_model_id, "zero-OTHER model"),
        current_slack,
        counterfactual_slack,
        gain,
        gain / exact_upper,
        cardinality_evidence.evidence_id,
    )


def _id_from_evidence(cardinality_evidence: Any, role: str) -> str:
    """Derive a role-separated selector identity from cardinality evidence."""

    return hashlib.sha256(
        (
            f"acfqp:v072-evidence-first-{role}:v2"
            + "\x00"
            + cardinality_evidence.evidence_id
        ).encode("utf-8")
    ).hexdigest()


def rank_evidence_first_no_prior_gains_v2(
    counterfactuals: tuple[OneRowCounterfactualGainV2, ...],
) -> tuple[OneRowCounterfactualGainV2, ...]:
    """Return the exact no-prior rank after full-row-list cost binding."""

    if (
        type(counterfactuals) is not tuple
        or not counterfactuals
        or any(
            type(item) is not OneRowCounterfactualGainV2
            or item.cardinality_evidence_id is None
            for item in counterfactuals
        )
        or len({item.counterfactual_id for item in counterfactuals})
        != len(counterfactuals)
        or len({item.candidate_id for item in counterfactuals})
        != len(counterfactuals)
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "evidence-first rank requires distinct full-row-list gains"
        )
    eligible = tuple(item for item in counterfactuals if item.eligible)
    if not eligible:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "evidence-first rank has no positive-gain candidate"
        )
    return tuple(
        sorted(
            eligible,
            key=lambda item: (
                -item.base,
                -item.gain,
                item.exact_draw_upper,
                item.candidate_id,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class TargetArmRankingScoreV2:
    counterfactual_id: str
    candidate_id: str
    feature_key: str
    arm: TargetSelectionArmV2
    source_prior_binding_id: str | None
    source_consensus_id: str | None
    source_feature_disposition: str
    source_midrank_q: Fraction | None
    base: Fraction
    multiplier: Fraction
    score: Fraction
    gain: Fraction
    exact_draw_upper: int
    gain_eligible: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.counterfactual_id, "score counterfactual"),
            (self.candidate_id, "score candidate"),
            (self.feature_key, "score feature"),
        ):
            _cid(value, field)
        arm = _arm(self.arm)
        if self.source_prior_binding_id is not None:
            _cid(self.source_prior_binding_id, "score source binding")
        if self.source_consensus_id is not None:
            _cid(self.source_consensus_id, "score source consensus")
        if (
            any(
                type(item) is not Fraction
                for item in (
                    self.base,
                    self.multiplier,
                    self.score,
                    self.gain,
                )
            )
            or (
                self.source_midrank_q is not None
                and (
                    type(self.source_midrank_q) is not Fraction
                    or not 0 <= self.source_midrank_q <= 1
                )
            )
            or type(self.exact_draw_upper) is not int
            or self.exact_draw_upper < PROMOTED_ROW_DRAWS
            or self.base != self.gain / self.exact_draw_upper
            or self.gain_eligible != (self.gain > 0)
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "arm score exact fields are inconsistent"
            )
        if arm in (
            TargetSelectionArmV2.NO_PRIOR,
            TargetSelectionArmV2.OOD_ABSTENTION,
        ):
            expected_multiplier = Fraction(1)
            if (
                self.source_prior_binding_id is not None
                or self.source_consensus_id is not None
                or self.source_midrank_q is not None
                    or self.source_feature_disposition
                    not in {"NO_PRIOR", "SCHEMA_MISMATCH"}
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "neutral arm score contains source numerical inputs"
                )
        else:
            if self.source_prior_binding_id is None:
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "source/wrong score lacks a frozen source binding"
                )
            if self.source_midrank_q is None:
                expected_multiplier = Fraction(1)
                if self.source_consensus_id is not None:
                    raise TargetPreauthorizationSelectorV2InvariantViolation(
                        "abstained source feature leaked a consensus number"
                    )
            else:
                if (
                    self.source_consensus_id is None
                    or self.source_feature_disposition != "APPLIED"
                ):
                    raise TargetPreauthorizationSelectorV2InvariantViolation(
                        "applied source score lacks consensus provenance"
                    )
                q = self.source_midrank_q
                expected_multiplier = (
                    Fraction(1, 2) + Fraction(3, 2) * q
                    if arm
                    is TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR
                    else Fraction(1, 2)
                    + Fraction(3, 2) * (1 - q)
                )
        if (
            self.multiplier != expected_multiplier
            or self.score != self.base * expected_multiplier
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "source or reversed ranking score was not derived"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_arm_ranking_score.v2",
            "schema_version": SCHEMA_VERSION,
            "counterfactual_id": self.counterfactual_id,
            "candidate_id": self.candidate_id,
            "feature_key": self.feature_key,
            "arm": self.arm.value,
            "source_prior_binding": (
                {"kind": "NOT_APPLICABLE"}
                if self.source_prior_binding_id is None
                else {
                    "kind": "VERIFIED_SOURCE_ARCHIVE",
                    "source_prior_binding_id": (
                        self.source_prior_binding_id
                    ),
                }
            ),
            "source_consensus_id": self.source_consensus_id,
            "source_feature_disposition": (
                self.source_feature_disposition
            ),
            "source_midrank_q": _maybe_fdoc(self.source_midrank_q),
            "base": _fdoc(self.base),
            "multiplier": _fdoc(self.multiplier),
            "score": _fdoc(self.score),
            "gain": _fdoc(self.gain),
            "exact_draw_upper": self.exact_draw_upper,
            "gain_eligible": self.gain_eligible,
            "ranking_only": True,
            "may_certify": False,
        }

    @property
    def score_id(self) -> str:
        return _content_id("score", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "score_id": self.score_id}


@dataclass(frozen=True, slots=True)
class TargetSelectionScheduleEntryV2:
    counterfactual_id: str
    candidate_id: str
    score: Fraction
    gain: Fraction
    exact_draw_upper: int
    gain_eligible: bool
    cap_eligible: bool

    def __post_init__(self) -> None:
        _cid(self.counterfactual_id, "schedule counterfactual")
        _cid(self.candidate_id, "schedule candidate")
        if (
            type(self.score) is not Fraction
            or type(self.gain) is not Fraction
            or type(self.exact_draw_upper) is not int
            or type(self.gain_eligible) is not bool
            or type(self.cap_eligible) is not bool
            or self.gain_eligible != (self.gain > 0)
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "schedule entry is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_selection_schedule_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "counterfactual_id": self.counterfactual_id,
            "candidate_id": self.candidate_id,
            "score": _fdoc(self.score),
            "gain": _fdoc(self.gain),
            "exact_draw_upper": self.exact_draw_upper,
            "gain_eligible": self.gain_eligible,
            "cap_eligible": self.cap_eligible,
        }

    @property
    def entry_id(self) -> str:
        return _content_id("schedule_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


def _ranking_key(
    item: TargetSelectionScheduleEntryV2,
) -> tuple[Fraction, Fraction, int, str]:
    return (
        -item.score,
        -item.gain,
        item.exact_draw_upper,
        item.candidate_id,
    )


@dataclass(frozen=True, slots=True)
class TargetSelectionScheduleCoreV2:
    registry_id: str
    round_index: int
    entries: tuple[TargetSelectionScheduleEntryV2, ...]
    selected_candidate_id: str
    arm_role_absent: bool = True
    source_prior_fields_absent: bool = True

    def __post_init__(self) -> None:
        _cid(self.registry_id, "schedule registry")
        _cid(self.selected_candidate_id, "schedule selected candidate")
        eligible = tuple(
            item
            for item in self.entries
            if item.gain_eligible and item.cap_eligible
        )
        if (
            self.round_index not in (1, 2)
            or type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not TargetSelectionScheduleEntryV2
                for item in self.entries
            )
            or self.entries != tuple(sorted(self.entries, key=_ranking_key))
            or len({item.candidate_id for item in self.entries})
            != len(self.entries)
            or not eligible
            or self.selected_candidate_id != eligible[0].candidate_id
            or self.arm_role_absent is not True
            or self.source_prior_fields_absent is not True
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "selection schedule is not the deterministic eligible order"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_selection_schedule_core.v2",
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry_id,
            "round_index": self.round_index,
            "entry_ids": [item.entry_id for item in self.entries],
            "selected_candidate_id": self.selected_candidate_id,
            "ranking_order": (
                "-score,-gain,exact_draw_upper,candidate_id"
            ),
            "arm_role_absent": True,
            "source_prior_fields_absent": True,
        }

    @property
    def schedule_core_id(self) -> str:
        return _content_id("schedule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "schedule_core_id": self.schedule_core_id,
        }


@dataclass(frozen=True, slots=True)
class NativeZeroPreauthorizationCounterV2:
    path: str
    value: int = 0
    observed: bool = True
    recorder_semantics_id: str = (
        "v072_trusted_pre_authorization_access_recorder_v1"
    )

    def __post_init__(self) -> None:
        if (
            type(self.path) is not str
            or self.path not in REQUIRED_NATIVE_ZERO_PATHS
            or self.value != 0
            or self.observed is not True
            or self.recorder_semantics_id
            != "v072_trusted_pre_authorization_access_recorder_v1"
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "forbidden preauthorization work is not a native zero"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_pre_authorization_native_zero.v2",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "value": 0,
            "observed": True,
            "recorder_semantics_id": self.recorder_semantics_id,
        }

    @property
    def counter_id(self) -> str:
        return _content_id("native_zero", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_id": self.counter_id}


@dataclass(frozen=True, slots=True)
class TargetPreauthorizationAccessLogV2:
    registry_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    support_epoch_id: str
    round_index: int
    public_catalogue_metadata_reads: int
    exact_counterfactual_evaluations: int
    source_consensus_lookups: int
    native_zero_counters: tuple[
        NativeZeroPreauthorizationCounterV2, ...
    ]
    authorization_frozen: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "access registry"),
            (self.model_id, "access model"),
            (self.audit_id, "access audit"),
            (self.frontier_id, "access frontier"),
            (self.threshold_profile_id, "access threshold"),
            (self.support_epoch_id, "access support epoch"),
        ):
            _cid(value, field)
        if (
            self.round_index not in (1, 2)
            or type(self.public_catalogue_metadata_reads) is not int
            or not 0
            < self.public_catalogue_metadata_reads
            <= MAX_FRONTIER_ROWS
            or type(self.exact_counterfactual_evaluations) is not int
            or self.exact_counterfactual_evaluations
            != self.public_catalogue_metadata_reads
            or type(self.source_consensus_lookups) is not int
            or not 0
            <= self.source_consensus_lookups
            <= self.public_catalogue_metadata_reads
            or type(self.native_zero_counters) is not tuple
            or tuple(
                item.path for item in self.native_zero_counters
            )
            != REQUIRED_NATIVE_ZERO_PATHS
            or any(
                type(item) is not NativeZeroPreauthorizationCounterV2
                for item in self.native_zero_counters
            )
            or self.authorization_frozen is not False
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "preauthorization access log is incomplete or reordered"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_pre_authorization_access_log.v2",
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "support_epoch_id": self.support_epoch_id,
            "round_index": self.round_index,
            "public_catalogue_metadata_reads": (
                self.public_catalogue_metadata_reads
            ),
            "exact_counterfactual_evaluations": (
                self.exact_counterfactual_evaluations
            ),
            "source_consensus_lookups": self.source_consensus_lookups,
            "native_zero_counter_ids": [
                item.counter_id for item in self.native_zero_counters
            ],
            "authorization_frozen": False,
        }

    @property
    def access_log_id(self) -> str:
        return _content_id("access", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "native_zero_counters": [
                item.to_document() for item in self.native_zero_counters
            ],
            "access_log_id": self.access_log_id,
        }


@dataclass(frozen=True, slots=True)
class TargetRowAuthorizationV2:
    registry_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    support_epoch_id: str
    source_prior_binding_id: str | None
    ood_abstention_id: str | None
    arm: TargetSelectionArmV2
    round_index: int
    schedule_core_id: str
    access_log_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    selected_exact_draw_upper: int
    cumulative_new_child_actions_after_selection: int
    cumulative_draw_upper_after_selection: int
    authorization_sequence: int
    target_access_sequence_minimum: int
    frozen_before_target_access: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.registry_id, "authorization registry"),
            (self.model_id, "authorization model"),
            (self.audit_id, "authorization audit"),
            (self.frontier_id, "authorization frontier"),
            (self.threshold_profile_id, "authorization threshold"),
            (self.support_epoch_id, "authorization support epoch"),
            (self.schedule_core_id, "authorization schedule"),
            (self.access_log_id, "authorization access log"),
            (self.selected_candidate_id, "authorization candidate"),
            (self.selected_planner_row_id, "authorization row"),
        ):
            _cid(value, field)
        arm = _arm(self.arm)
        if self.source_prior_binding_id is not None:
            _cid(
                self.source_prior_binding_id,
                "authorization source binding",
            )
        if self.ood_abstention_id is not None:
            _cid(self.ood_abstention_id, "authorization OOD abstention")
        if (
            (
                arm
                in (
                    TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
                    TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
                )
            )
            != (self.source_prior_binding_id is not None)
            or (
                arm is TargetSelectionArmV2.OOD_ABSTENTION
            )
            != (self.ood_abstention_id is not None)
            or type(self.selected_exact_draw_upper) is not int
            or self.selected_exact_draw_upper < PROMOTED_ROW_DRAWS
            or type(
                self.cumulative_new_child_actions_after_selection
            )
            is not int
            or not 0
            <= self.cumulative_new_child_actions_after_selection
            <= MAX_NEW_CHILD_ACTIONS_TOTAL
            or type(self.cumulative_draw_upper_after_selection) is not int
            or not 0
            < self.cumulative_draw_upper_after_selection
            <= MAX_TWO_ROUND_DRAW_UPPER
            or self.round_index not in (1, 2)
            or self.authorization_sequence != 2 * self.round_index - 1
            or self.target_access_sequence_minimum
            != self.authorization_sequence + 1
            or self.frozen_before_target_access is not True
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "target row authorization binding/cap/order is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_target_row_authorization.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "registry_id": self.registry_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "frontier_id": self.frontier_id,
            "threshold_profile_id": self.threshold_profile_id,
            "support_epoch_id": self.support_epoch_id,
            "source_prior": (
                {
                    "kind": "VERIFIED_SOURCE_ARCHIVE",
                    "source_prior_binding_id": (
                        self.source_prior_binding_id
                    ),
                }
                if self.source_prior_binding_id is not None
                else (
                    {
                        "kind": "OOD_TYPED_ABSTENTION",
                        "ood_abstention_id": self.ood_abstention_id,
                    }
                    if self.ood_abstention_id is not None
                    else {
                        "kind": "NOT_APPLICABLE",
                        "reason": "NO_PRIOR_ARM",
                    }
                )
            ),
            "arm": self.arm.value,
            "round_index": self.round_index,
            "schedule_core_id": self.schedule_core_id,
            "access_log_id": self.access_log_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "selected_exact_draw_upper": self.selected_exact_draw_upper,
            "cumulative_new_child_actions_after_selection": (
                self.cumulative_new_child_actions_after_selection
            ),
            "cumulative_draw_upper_after_selection": (
                self.cumulative_draw_upper_after_selection
            ),
            "authorization_sequence": self.authorization_sequence,
            "target_access_sequence_minimum": (
                self.target_access_sequence_minimum
            ),
            "frozen_before_target_access": True,
            "one_candidate_only": True,
            "certificate_authority": False,
            "execution_role": "LEGACY_DEVELOPMENT_NONCONFIRMATORY",
            "confirmatory_execution_allowed": False,
            "full_physical_row_list_evidence": False,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authorization_id": self.authorization_id}


@dataclass(frozen=True, slots=True)
class PreparedTargetSelectionV2:
    registry: TargetCandidateRegistryV2
    counterfactuals: tuple[OneRowCounterfactualGainV2, ...]
    scores: tuple[TargetArmRankingScoreV2, ...]
    schedule: TargetSelectionScheduleCoreV2
    access_log: TargetPreauthorizationAccessLogV2
    authorization: TargetRowAuthorizationV2
    source_prior_binding: VerifiedSourcePriorBindingV2 | None
    ood_abstention: OodPriorTypedAbstentionV2 | None
    proposal_only: bool = True
    sample_efficiency_gate_status: str = SAMPLE_EFFICIENCY_GATE_STATUS

    def __post_init__(self) -> None:
        candidate_by_id = {
            item.candidate_id: item for item in self.registry.candidates
        }
        counterfactual_by_candidate = {
            item.candidate_id: item for item in self.counterfactuals
        }
        score_by_candidate = {
            item.candidate_id: item for item in self.scores
        }
        selected = candidate_by_id.get(
            self.authorization.selected_candidate_id
        )
        if (
            type(self.registry) is not TargetCandidateRegistryV2
            or type(self.counterfactuals) is not tuple
            or tuple(
                item.counterfactual_id for item in self.counterfactuals
            )
            != tuple(
                sorted(
                    {
                        item.counterfactual_id
                        for item in self.counterfactuals
                    }
                )
            )
            or set(counterfactual_by_candidate) != set(candidate_by_id)
            or type(self.scores) is not tuple
            or tuple(item.score_id for item in self.scores)
            != tuple(sorted({item.score_id for item in self.scores}))
            or set(score_by_candidate) != set(candidate_by_id)
            or type(self.schedule)
            is not TargetSelectionScheduleCoreV2
            or type(self.access_log)
            is not TargetPreauthorizationAccessLogV2
            or type(self.authorization)
            is not TargetRowAuthorizationV2
            or self.schedule.registry_id != self.registry.registry_id
            or self.access_log.registry_id != self.registry.registry_id
            or self.authorization.registry_id != self.registry.registry_id
            or self.authorization.schedule_core_id
            != self.schedule.schedule_core_id
            or self.authorization.access_log_id
            != self.access_log.access_log_id
            or selected is None
            or self.authorization.selected_planner_row_id
            != selected.planner_row_id
            or self.authorization.selected_exact_draw_upper
            != selected.exact_draw_upper
            or self.authorization.round_index != self.registry.round_index
            or self.authorization.support_epoch_id
            != self.registry.support_epoch_id
            or self.proposal_only is not True
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "prepared selection does not bind one complete decision"
            )
        for candidate_id, score in score_by_candidate.items():
            counterfactual = counterfactual_by_candidate[candidate_id]
            if (
                score.counterfactual_id
                != counterfactual.counterfactual_id
                or score.gain != counterfactual.gain
                or score.base != counterfactual.base
                or score.exact_draw_upper
                != counterfactual.exact_draw_upper
            ):
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "arm score differs from its source-free counterfactual"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_prepared_target_selection.v2",
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry.registry_id,
            "counterfactual_ids": [
                item.counterfactual_id for item in self.counterfactuals
            ],
            "score_ids": [item.score_id for item in self.scores],
            "schedule_core_id": self.schedule.schedule_core_id,
            "access_log_id": self.access_log.access_log_id,
            "authorization_id": self.authorization.authorization_id,
            "source_prior_binding_id": (
                None
                if self.source_prior_binding is None
                else self.source_prior_binding.source_prior_binding_id
            ),
            "ood_abstention_id": (
                None
                if self.ood_abstention is None
                else self.ood_abstention.abstention_id
            ),
            "proposal_only": True,
            "target_access_performed": False,
            "sample_efficiency_gate_status": "NOT_RUN",
        }

    @property
    def prepared_selection_id(self) -> str:
        return _content_id("prepared", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "registry": self.registry.to_document(),
            "counterfactuals": [
                item.to_document() for item in self.counterfactuals
            ],
            "scores": [item.to_document() for item in self.scores],
            "schedule": self.schedule.to_document(),
            "access_log": self.access_log.to_document(),
            "authorization": self.authorization.to_document(),
            "source_prior_binding": (
                None
                if self.source_prior_binding is None
                else self.source_prior_binding.to_document()
            ),
            "ood_abstention": (
                None
                if self.ood_abstention is None
                else self.ood_abstention.to_document()
            ),
            "prepared_selection_id": self.prepared_selection_id,
        }


def freeze_target_candidate_registry_v2(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    public_metadata: PublicFrontierActionCatalogueMetadataV2,
    round_index: int,
    previous_selection: PreparedTargetSelectionV2 | None = None,
) -> TargetCandidateRegistryV2:
    """Freeze a fresh current-frontier registry without observer access."""

    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(public_metadata)
        is not PublicFrontierActionCatalogueMetadataV2
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or threshold.context_id != model.context_id
        or audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or audit.failed_frontier is None
        or public_metadata.model_id != model.model_id
        or public_metadata.audit_id != audit.audit_id
        or public_metadata.frontier_id
        != audit.failed_frontier.frontier_id
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "candidate registry parent chain is stale or not failed"
        )
    if round_index == 1:
        if previous_selection is not None:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "round 1 cannot consume a previous selection"
            )
        previous_registry_id = None
        previous_authorization_id = None
        cumulative_actions = 0
        cumulative_draws = 0
    elif round_index == 2:
        if (
            type(previous_selection) is not PreparedTargetSelectionV2
            or previous_selection.registry.round_index != 1
            or previous_selection.authorization.round_index != 1
            or model.model_id == previous_selection.registry.model_id
            or audit.audit_id == previous_selection.registry.audit_id
            or audit.failed_frontier.frontier_id
            == previous_selection.registry.frontier_id
            or public_metadata.support_epoch_id
            == previous_selection.registry.support_epoch_id
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "round 2 requires a genuinely rebuilt model/audit/frontier/epoch"
            )
        previous_registry_id = previous_selection.registry.registry_id
        previous_authorization_id = (
            previous_selection.authorization.authorization_id
        )
        cumulative_actions = (
            previous_selection.authorization
            .cumulative_new_child_actions_after_selection
        )
        cumulative_draws = (
            previous_selection.authorization
            .cumulative_draw_upper_after_selection
        )
    else:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "only two acquisition rounds are registered"
        )
    row_by_id = {item.row_id: item for item in model.rows}
    metadata_by_row = {
        item.planner_row_id: item for item in public_metadata.rows
    }
    if set(metadata_by_row) != set(
        audit.failed_frontier.selected_row_ids
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "public metadata differs from the current failed frontier"
        )
    candidates = []
    for row_id in audit.failed_frontier.selected_row_ids:
        row = row_by_id.get(row_id)
        metadata = metadata_by_row[row_id]
        if (
            row is None
            or (
                metadata.state_id,
                metadata.remaining_horizon,
                metadata.action_id,
            )
            != row.row_key
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "frontier row metadata was transplanted"
            )
        candidates.append(
            TargetAcquisitionCandidateV2(
                model.model_id,
                audit.audit_id,
                audit.failed_frontier.frontier_id,
                threshold.threshold_profile_id,
                public_metadata.support_epoch_id,
                metadata,
                _portable_feature(model=model, audit=audit, row=row),
            )
        )
    return TargetCandidateRegistryV2(
        model.model_id,
        audit.audit_id,
        audit.failed_frontier.frontier_id,
        threshold.threshold_profile_id,
        public_metadata.support_epoch_id,
        public_metadata.public_metadata_id,
        round_index,
        previous_registry_id,
        previous_authorization_id,
        cumulative_actions,
        cumulative_draws,
        tuple(sorted(candidates, key=lambda item: item.candidate_id)),
    )


def _one_row_zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> robust.PartialSupportIntervalModelV1:
    row = {item.row_id: item for item in model.rows}.get(planner_row_id)
    if row is None:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "zero-OTHER counterfactual row is absent"
        )
    replacement = replace(
        row,
        masses=tuple(
            (
                robust.IntervalDestinationMassV1(
                    item.destination_id,
                    Fraction(0),
                    Fraction(0),
                )
                if item.destination_id == row.other_destination_id
                else item
            )
            for item in row.masses
        ),
    )
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=(
            replacement if item.row_id == planner_row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )


def _mass_preserving_optimistic_resolution_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> tuple[robust.PartialSupportIntervalModelV1, str, str]:
    """Resolve one OTHER interval as row-bound success for ranking only.

    The original ``OTHER`` interval is copied exactly to a fresh
    content-addressed success-terminal destination and then set to zero.
    No other mass, row, or destination is changed.  This is an explicitly
    optimistic proposal score and never certificate evidence.
    """

    row = {item.row_id: item for item in model.rows}.get(planner_row_id)
    if row is None:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "optimistic-resolution row is absent"
        )
    other = row.other_mass
    zero_lower_sum = sum(
        (
            item.lower
            for item in row.masses
            if item.destination_id != row.other_destination_id
        ),
        Fraction(0),
    )
    zero_upper_sum = sum(
        (
            item.upper
            for item in row.masses
            if item.destination_id != row.other_destination_id
        ),
        Fraction(0),
    )
    if zero_lower_sum > 1 or zero_upper_sum >= 1:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "optimistic resolution requires the typed zero-OTHER "
            "upper-sum-deficit case"
        )
    destination_payload = {
        "schema": (
            "acfqp.v072_row_bound_optimistic_success_destination.v2"
        ),
        "schema_version": SCHEMA_VERSION,
        "model_id": model.model_id,
        "planner_row_id": row.row_id,
        "original_other_destination_id": row.other_destination_id,
        "preserved_lower": _fdoc(other.lower),
            "preserved_upper": _fdoc(other.upper),
            "zero_other_lower_sum": _fdoc(zero_lower_sum),
            "zero_other_upper_sum": _fdoc(zero_upper_sum),
            "zero_other_simplex_disposition": "UPPER_SUM_DEFICIT",
        "category": robust.DestinationCategory.SUCCESS_TERMINAL.value,
        "proposal_only": True,
        "certificate_authority": False,
    }
    destination_id = _content_id(
        "optimistic_destination",
        destination_payload,
    )
    destination = robust.RegisteredDestinationV1(
        destination_id,
        robust.DestinationCategory.SUCCESS_TERMINAL,
    )
    replacement = replace(
        row,
        masses=tuple(
            sorted(
                (
                    *(
                        (
                            robust.IntervalDestinationMassV1(
                                item.destination_id,
                                Fraction(0),
                                Fraction(0),
                            )
                            if item.destination_id
                            == row.other_destination_id
                            else item
                        )
                        for item in row.masses
                    ),
                    robust.IntervalDestinationMassV1(
                        destination_id,
                        other.lower,
                        other.upper,
                    ),
                ),
                key=lambda item: item.destination_id,
            )
        ),
    )
    resolved = robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=tuple(
            sorted(
                (*model.destinations, destination),
                key=lambda item: item.destination_id,
            )
        ),
        rows=(
            replacement if item.row_id == planner_row_id else item
            for item in model.rows
        ),
        concretizer_entries=model.concretizer_entries,
    )
    resolution_id = _content_id(
        "optimistic_resolution",
        {
            "schema": (
                "acfqp.v072_mass_preserving_optimistic_resolution.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_model_id": model.model_id,
            "planner_row_id": row.row_id,
            "source_other_destination_id": row.other_destination_id,
            "source_other_lower": _fdoc(other.lower),
            "source_other_upper": _fdoc(other.upper),
            "zero_other_lower_sum": _fdoc(zero_lower_sum),
            "zero_other_upper_sum": _fdoc(zero_upper_sum),
            "zero_other_simplex_disposition": "UPPER_SUM_DEFICIT",
            "resolution_destination_id": destination_id,
            "resolution_model_id": resolved.model_id,
            "unique_new_destination_count": 1,
            "other_interval_preserved_exactly": True,
            "all_other_rows_and_masses_unchanged": True,
            "proposal_only": True,
            "certificate_authority": False,
        },
    )
    return resolved, destination_id, resolution_id


def _fixed_ground_policy_metrics(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if (
        any(
            item.scope is not robust.PolicyScope.GROUND_STATE
            for item in audit.assignments
        )
        or len(assignment) != len(audit.assignments)
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "ground selected policy assignments are malformed"
        )
    catalogue_by_state, destination_by_id, row_by_key = (
        robust._registries(model)
    )
    child_values: dict[str, robust._StateActionEvaluation] = {}
    expected_keys: set[tuple[str, int]] = set()
    for state_id in robust._reachable_child_states(model):
        key = (state_id, 1)
        expected_keys.add(key)
        action_id = assignment.get(key)
        if action_id is None:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "ground selected policy omits a reachable child"
            )
        evaluated = robust._evaluate_ground_row(
            row_by_key[(state_id, 1, action_id)],
            destination_by_id=destination_by_id,
            child_values={},
            threshold=threshold,
            category=robust.SelectedRowCategory.CONTINUATION_SELECTED,
            policy_scope_key=state_id,
        )
        child_values[state_id] = robust._StateActionEvaluation(
            evaluated.bound.reward_lower,
            evaluated.bound.reward_upper,
            evaluated.bound.failure_upper,
            (evaluated,),
        )
    root_key = (model.root_state_id, 2)
    expected_keys.add(root_key)
    root_action = assignment.get(root_key)
    if root_action is None or set(assignment) != expected_keys:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "ground selected policy domain changed under counterfactual"
        )
    root = robust._evaluate_ground_row(
        row_by_key[(model.root_state_id, 2, root_action)],
        destination_by_id=destination_by_id,
        child_values=child_values,
        threshold=threshold,
        category=robust.SelectedRowCategory.ROOT_SELECTED,
        policy_scope_key=model.root_state_id,
    ).bound
    regret = max(
        Fraction(0),
        audit.unrestricted_reward_upper - root.reward_lower,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - root.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    return root.reward_lower, root.failure_upper, regret, slack


def _fixed_quotient_policy_metrics(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    assignment = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if (
        any(
            item.scope is not robust.PolicyScope.QUOTIENT_CELL
            for item in audit.assignments
        )
        or len(assignment) != len(audit.assignments)
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "quotient selected policy assignments are malformed"
        )
    catalogue_by_state, _, _ = robust._registries(model)
    child_states = robust._reachable_child_states(model)
    expected_keys: set[tuple[str, int]] = set()
    child_values: dict[str, robust._StateActionEvaluation] = {}
    for state_id in child_states:
        cell = catalogue_by_state[state_id].state_coordinate_key
        key = (cell, 1)
        expected_keys.add(key)
        action = assignment.get(key)
        if action is None:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "quotient selected policy omits a reachable cell"
            )
        child_values[state_id] = robust._evaluate_concretized_state_action(
            model,
            threshold,
            state_id=state_id,
            remaining_horizon=1,
            abstract_action_key=action,
            child_values={},
            category=(
                robust.SelectedRowCategory
                .CONTINUATION_CONCRETIZER_COMPONENT
            ),
        )
    root_cell = catalogue_by_state[
        model.root_state_id
    ].state_coordinate_key
    root_key = (root_cell, 2)
    expected_keys.add(root_key)
    root_action = assignment.get(root_key)
    if root_action is None or set(assignment) != expected_keys:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "quotient selected policy domain changed under counterfactual"
        )
    root = robust._evaluate_concretized_state_action(
        model,
        threshold,
        state_id=model.root_state_id,
        remaining_horizon=2,
        abstract_action_key=root_action,
        child_values=child_values,
        category=robust.SelectedRowCategory.ROOT_CONCRETIZER_COMPONENT,
    )
    regret = max(
        Fraction(0),
        audit.unrestricted_reward_upper - root.reward_lower,
    ) / threshold.reward_ceiling
    slack = min(
        threshold.risk_tolerance - root.failure_upper,
        threshold.normalized_regret_tolerance - regret,
    )
    return root.reward_lower, root.failure_upper, regret, slack


def _fixed_policy_slack(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    metrics = (
        _fixed_ground_policy_metrics(model, audit, threshold)
        if audit.solver_kind is robust.RobustSolverKind.GROUND_DIRECT
        else _fixed_quotient_policy_metrics(model, audit, threshold)
    )
    return metrics[-1]


def _counterfactuals(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetCandidateRegistryV2,
) -> tuple[OneRowCounterfactualGainV2, ...]:
    current_slack = min(
        threshold.risk_tolerance - audit.root_failure_upper,
        threshold.normalized_regret_tolerance
        - audit.normalized_regret_upper,
    )
    output = []
    for candidate in registry.candidates:
        common = (
            registry.registry_id,
            candidate.candidate_id,
            model.model_id,
            audit.audit_id,
            registry.frontier_id,
            threshold.threshold_profile_id,
            registry.support_epoch_id,
            candidate.planner_row_id,
            candidate.exact_draw_upper,
        )
        resolution_destination_id = None
        optimistic_resolution_id = None
        status = CounterfactualEvaluationStatusV2.EVALUATED
        candidate_row = {
            item.row_id: item for item in model.rows
        }.get(candidate.planner_row_id)
        if candidate_row is None:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "counterfactual candidate row is absent"
            )
        zero_lower_sum = sum(
            (
                item.lower
                for item in candidate_row.masses
                if item.destination_id
                != candidate_row.other_destination_id
            ),
            Fraction(0),
        )
        zero_upper_sum = sum(
            (
                item.upper
                for item in candidate_row.masses
                if item.destination_id
                != candidate_row.other_destination_id
            ),
            Fraction(0),
        )
        if zero_lower_sum > 1:
            output.append(
                OneRowCounterfactualGainV2(
                    *common,
                    CounterfactualEvaluationStatusV2.INFEASIBLE_SIMPLEX,
                    None,
                    current_slack,
                    None,
                    Fraction(0),
                    Fraction(0),
                )
            )
            continue
        if zero_upper_sum < 1:
            try:
                zero_model, resolution_destination_id, (
                    optimistic_resolution_id
                ) = _mass_preserving_optimistic_resolution_model(
                    model,
                    candidate.planner_row_id,
                )
                status = (
                    CounterfactualEvaluationStatusV2
                    .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
                )
            except robust.PartialSupportRobustPlannerInvariantViolation as error:
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "typed optimistic-resolution model construction failed"
                ) from error
        else:
            try:
                zero_model = _one_row_zero_other_model(
                    model,
                    candidate.planner_row_id,
                )
            except robust.PartialSupportRobustPlannerInvariantViolation as error:
                raise TargetPreauthorizationSelectorV2InvariantViolation(
                    "admissible zero-OTHER model construction failed"
                ) from error
        try:
            counterfactual_slack = _fixed_policy_slack(
                zero_model,
                audit,
                threshold,
            )
        except robust.PartialSupportRobustPlannerInvariantViolation as error:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "counterfactual fixed-policy replay failed"
            ) from error
        gain = max(Fraction(0), counterfactual_slack - current_slack)
        output.append(
            OneRowCounterfactualGainV2(
                *common,
                status,
                (
                    zero_model.model_id
                    if status
                    is CounterfactualEvaluationStatusV2.EVALUATED
                    else None
                ),
                current_slack,
                counterfactual_slack,
                gain,
                gain / candidate.exact_draw_upper,
                resolution_model_id=(
                    zero_model.model_id
                    if status
                    is CounterfactualEvaluationStatusV2
                    .MASS_PRESERVING_OPTIMISTIC_RESOLUTION
                    else None
                ),
                resolution_destination_id=resolution_destination_id,
                optimistic_resolution_id=optimistic_resolution_id,
            )
        )
    return tuple(
        sorted(output, key=lambda item: item.counterfactual_id)
    )


def _prior_resolution(
    *,
    arm: TargetSelectionArmV2,
    source_prior: VerifiedSourcePriorBindingV2 | None,
    ood_abstention: OodPriorTypedAbstentionV2 | None,
) -> PriorResolutionKindV2:
    if arm in (
        TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
    ):
        if (
            type(source_prior) is not VerifiedSourcePriorBindingV2
            or ood_abstention is not None
        ):
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "source/wrong arm requires exactly one verified source binding"
            )
        return PriorResolutionKindV2.SOURCE_ARCHIVE_APPLIED
    if arm is TargetSelectionArmV2.NO_PRIOR:
        if source_prior is not None or ood_abstention is not None:
            raise TargetPreauthorizationSelectorV2InvariantViolation(
                "no-prior arm received a prior artifact"
            )
        return PriorResolutionKindV2.NO_PRIOR
    if (
        source_prior is not None
        or type(ood_abstention) is not OodPriorTypedAbstentionV2
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "OOD arm requires typed schema abstention and no source numbers"
        )
    return PriorResolutionKindV2.OOD_TYPED_ABSTENTION


def _scores(
    *,
    registry: TargetCandidateRegistryV2,
    counterfactuals: tuple[OneRowCounterfactualGainV2, ...],
    arm: TargetSelectionArmV2,
    source_prior: VerifiedSourcePriorBindingV2 | None,
) -> tuple[TargetArmRankingScoreV2, ...]:
    candidate_by_id = {
        item.candidate_id: item for item in registry.candidates
    }
    consensus_by_feature = (
        {}
        if source_prior is None
        else {
            item.feature_key: item for item in source_prior.consensus
        }
    )
    output = []
    for counterfactual in counterfactuals:
        candidate = candidate_by_id[counterfactual.candidate_id]
        consensus = consensus_by_feature.get(candidate.feature.feature_key)
        if arm is TargetSelectionArmV2.NO_PRIOR:
            disposition = "NO_PRIOR"
            consensus_id = None
            q = None
            source_binding_id = None
            multiplier = Fraction(1)
        elif arm is TargetSelectionArmV2.OOD_ABSTENTION:
            disposition = "SCHEMA_MISMATCH"
            consensus_id = None
            q = None
            source_binding_id = None
            multiplier = Fraction(1)
        else:
            assert source_prior is not None
            source_binding_id = source_prior.source_prior_binding_id
            if (
                consensus is None
                or consensus.disposition.value != "APPLIED"
            ):
                disposition = (
                    "UNSEEN"
                    if consensus is None
                    else consensus.disposition.value
                )
                if disposition not in TARGET_FEATURE_DISPOSITIONS:
                    raise TargetPreauthorizationSelectorV2InvariantViolation(
                        "source archive disposition is not a V0-072 disposition"
                    )
                consensus_id = None
                q = None
                multiplier = Fraction(1)
            else:
                disposition = "APPLIED"
                consensus_id = consensus.consensus_id
                q = consensus.mean_midrank
                multiplier = (
                    Fraction(1, 2) + Fraction(3, 2) * q
                    if arm
                    is TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR
                    else Fraction(1, 2)
                    + Fraction(3, 2) * (1 - q)
                )
        output.append(
            TargetArmRankingScoreV2(
                counterfactual.counterfactual_id,
                counterfactual.candidate_id,
                candidate.feature.feature_key,
                arm,
                source_binding_id,
                consensus_id,
                disposition,
                q,
                counterfactual.base,
                multiplier,
                counterfactual.base * multiplier,
                counterfactual.gain,
                counterfactual.exact_draw_upper,
                counterfactual.eligible,
            )
        )
    return tuple(sorted(output, key=lambda item: item.score_id))


def _schedule(
    *,
    registry: TargetCandidateRegistryV2,
    scores: tuple[TargetArmRankingScoreV2, ...],
) -> TargetSelectionScheduleCoreV2:
    entries = []
    candidate_by_id = {
        item.candidate_id: item for item in registry.candidates
    }
    for score in scores:
        candidate = candidate_by_id[score.candidate_id]
        cap_eligible = (
            registry.cumulative_new_child_actions_before_round
            + candidate.n_new_child_actions
            <= MAX_NEW_CHILD_ACTIONS_TOTAL
            and registry.cumulative_draw_upper_before_round
            + candidate.exact_draw_upper
            <= MAX_TWO_ROUND_DRAW_UPPER
        )
        entries.append(
            TargetSelectionScheduleEntryV2(
                score.counterfactual_id,
                score.candidate_id,
                score.score,
                score.gain,
                score.exact_draw_upper,
                score.gain_eligible,
                cap_eligible,
            )
        )
    ordered = tuple(sorted(entries, key=_ranking_key))
    eligible = tuple(
        item
        for item in ordered
        if item.gain_eligible and item.cap_eligible
    )
    if not eligible:
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "no positive-gain candidate fits the preregistered cap"
        )
    return TargetSelectionScheduleCoreV2(
        registry.registry_id,
        registry.round_index,
        ordered,
        eligible[0].candidate_id,
    )


def prepare_target_selection_v2(
    *,
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
    registry: TargetCandidateRegistryV2,
    arm: TargetSelectionArmV2,
    source_prior: VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: OodPriorTypedAbstentionV2 | None = None,
) -> PreparedTargetSelectionV2:
    """Derive exact gains/scores and freeze one preaccess authorization."""

    arm = _arm(arm)
    if (
        type(model) is not robust.PartialSupportIntervalModelV1
        or type(audit) is not robust.RobustPlanAuditV1
        or type(threshold) is not robust.RobustThresholdProfileV1
        or type(registry) is not TargetCandidateRegistryV2
        or registry.model_id != model.model_id
        or registry.audit_id != audit.audit_id
        or registry.frontier_id
        != (
            None
            if audit.failed_frontier is None
            else audit.failed_frontier.frontier_id
        )
        or registry.threshold_profile_id
        != threshold.threshold_profile_id
        or audit.model_id != model.model_id
        or audit.threshold_profile_id != threshold.threshold_profile_id
        or audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    ):
        raise TargetPreauthorizationSelectorV2InvariantViolation(
            "prepare received a stale registry/model/audit/threshold chain"
        )
    _prior_resolution(
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    counterfactuals = _counterfactuals(
        model=model,
        audit=audit,
        threshold=threshold,
        registry=registry,
    )
    scores = _scores(
        registry=registry,
        counterfactuals=counterfactuals,
        arm=arm,
        source_prior=source_prior,
    )
    schedule = _schedule(registry=registry, scores=scores)
    native_zeros = tuple(
        NativeZeroPreauthorizationCounterV2(path)
        for path in REQUIRED_NATIVE_ZERO_PATHS
    )
    lookups = (
        len(registry.candidates)
        if arm
        in (
            TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
            TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
        )
        else 0
    )
    access = TargetPreauthorizationAccessLogV2(
        registry.registry_id,
        model.model_id,
        audit.audit_id,
        registry.frontier_id,
        threshold.threshold_profile_id,
        registry.support_epoch_id,
        registry.round_index,
        len(registry.candidates),
        len(counterfactuals),
        lookups,
        native_zeros,
    )
    selected = {
        item.candidate_id: item for item in registry.candidates
    }[schedule.selected_candidate_id]
    authorization = TargetRowAuthorizationV2(
        registry.registry_id,
        model.model_id,
        audit.audit_id,
        registry.frontier_id,
        threshold.threshold_profile_id,
        registry.support_epoch_id,
        (
            None
            if source_prior is None
            else source_prior.source_prior_binding_id
        ),
        (
            None
            if ood_abstention is None
            else ood_abstention.abstention_id
        ),
        arm,
        registry.round_index,
        schedule.schedule_core_id,
        access.access_log_id,
        selected.candidate_id,
        selected.planner_row_id,
        selected.exact_draw_upper,
        registry.cumulative_new_child_actions_before_round
        + selected.n_new_child_actions,
        registry.cumulative_draw_upper_before_round
        + selected.exact_draw_upper,
        2 * registry.round_index - 1,
        2 * registry.round_index,
    )
    return PreparedTargetSelectionV2(
        registry,
        counterfactuals,
        scores,
        schedule,
        access,
        authorization,
        source_prior,
        ood_abstention,
    )


__all__ = [
    "ADAPTIVE_ARMS",
    "CHILD_ACTION_DRAWS",
    "CHILD_DISCOVERY_DRAWS",
    "CHILD_VALIDATION_DRAWS",
    "CounterfactualEvaluationStatusV2",
    "derive_evidence_first_one_row_counterfactual_gain_v2",
    "rank_evidence_first_no_prior_gains_v2",
    "FrontierRowPublicActionMetadataV2",
    "MAX_FRONTIER_ROWS",
    "MAX_NEW_CHILD_ACTIONS_TOTAL",
    "MAX_ROUNDS",
    "MAX_TWO_ROUND_DRAW_UPPER",
    "NativeZeroPreauthorizationCounterV2",
    "OneRowCounterfactualGainV2",
    "OodPriorTypedAbstentionV2",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PROMOTED_ROW_DRAWS",
    "PreparedTargetSelectionV2",
    "PriorResolutionKindV2",
    "PublicFrontierActionCatalogueMetadataV2",
    "REQUIRED_NATIVE_ZERO_PATHS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "SCHEMA_VERSION",
    "TargetAcquisitionCandidateV2",
    "TargetArmRankingScoreV2",
    "TargetCandidateRegistryV2",
    "TargetPreauthorizationAccessLogV2",
    "TargetPreauthorizationSelectorV2InvariantViolation",
    "TargetRowAuthorizationV2",
    "TargetSelectionArmV2",
    "TargetSelectionScheduleCoreV2",
    "TargetSelectionScheduleEntryV2",
    "TARGET_FEATURE_DISPOSITIONS",
    "VerifiedSourcePriorBindingV2",
    "exact_preexecution_draw_upper_v2",
    "freeze_public_frontier_action_metadata_v2",
    "freeze_target_candidate_registry_v2",
    "freeze_verified_source_prior_binding_v2",
    "prepare_target_selection_v2",
]
