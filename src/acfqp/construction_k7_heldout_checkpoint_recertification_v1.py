"""Held-out checkpoint recovery into a reusable abstract world model.

The registered W5 occurrence is structurally held out from the n=4 source
family.  A target-observation-only coordinate proposal is built at the 2,048
validation checkpoint and robust planning is performed on its quotient model.
When the certificate fails, this module freezes one causal recovery request,
extends only that row to the next preregistered checkpoint, installs the row as
an immutable overlay, and replans on the quotient model.  The process repeats
at most twice.

The construction intentionally stops at a conditional statistical plan
certificate.  It does not call the evaluation-only exact kernel or a ground
solver, does not complete every row to 4,096 draws, and does not unlock the
official accounting/economics gates.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import observation_support_coordinate_refinement_v1 as refinement
from acfqp import observation_support_graph_acquisition_v1 as acquisition
from acfqp import observation_support_graph_model_v1 as graph_model
from acfqp import observation_support_h2_closure_v1 as h2_closure
from acfqp import observation_support_relational_adapter_v1 as relational
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp import variable_order_graph_rapm_v1 as variable_order
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.119"
PROFILE_KEY = "construction_k7_heldout_checkpoint_recertification_v1"
TARGET_CONTEXT_KEY = "opaque_graph_w5_v0"
BASE_CHECKPOINT = 2_048
RECOVERY_CHECKPOINT = 4_096
MAX_LOCAL_TRANSACTIONS = 2
SELECTED_CANDIDATE_ORDINAL = 1
CAUSAL_SELECTION_RULE = (
    "ZERO_OTHER_CERTIFIES_THEN_HIGHEST_HORIZON_THEN_PLANNER_ROW_ID"
)

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN
)
CHECKPOINT_DOMAIN = CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN
CAUSAL_DOMAIN = CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN
REQUEST_DOMAIN = CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN
DELTA_DOMAIN = CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN
OVERLAY_DOMAIN = CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        PREREGISTRATION_DOMAIN,
        CHECKPOINT_DOMAIN,
        CAUSAL_DOMAIN,
        REQUEST_DOMAIN,
        DELTA_DOMAIN,
        OVERLAY_DOMAIN,
        RESULT_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 7 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out checkpoint domains are not central")

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"

_PREREGISTRATION_ISSUER = object()
_CHECKPOINT_ISSUER = object()
_CAUSAL_ISSUER = object()
_REQUEST_ISSUER = object()
_DELTA_ISSUER = object()
_OVERLAY_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7HeldoutCheckpointRecertificationV1Error(ValueError):
    """The held-out checkpoint, causal selection, or overlay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCheckpointRecertificationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCheckpointRecertificationV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("held-out checkpoint arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _digest_ids(values: tuple[str, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


def _aggregate_counters(
    root_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...],
    child_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
) -> h2_closure.ObservationSupportH2ClosureCountersV1:
    rows = (*root_rows, *child_rows)
    native = tuple(row.counters for row in rows)
    return h2_closure.ObservationSupportH2ClosureCountersV1(
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
        support_descriptor_count=sum(len(row.support_descriptors) for row in rows),
        validation_novel_descriptor_count=sum(len(row.novel_descriptors) for row in rows),
        initial_discovery_draws=sum(item.initial_discovery_draws for item in native),
        prior_validation_draws=sum(item.prior_validation_draws for item in native),
        current_validation_draws=sum(item.current_validation_draws for item in native),
        total_observer_draws=sum(item.total_observer_draws for item in native),
        discovery_random_word_calls=sum(item.discovery_random_word_calls for item in native),
        discovery_rejections=sum(item.discovery_rejections for item in native),
        prior_validation_random_word_calls=sum(
            item.prior_validation_random_word_calls for item in native
        ),
        prior_validation_rejections=sum(item.prior_validation_rejections for item in native),
        current_validation_random_word_calls=sum(
            item.current_validation_random_word_calls for item in native
        ),
        current_validation_rejections=sum(
            item.current_validation_rejections for item in native
        ),
        total_random_word_calls=sum(item.total_random_word_calls for item in native),
        total_rejections=sum(item.total_rejections for item in native),
    )


def _active_states(
    root_rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
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
                _fail("one discovery-known state has conflicting documents")
    return tuple(by_id[key] for key in sorted(by_id))


@dataclass(slots=True)
class _RetainedClosureV1:
    closure: h2_closure.ObservationSupportH2ClosureV1
    streams_by_binding_id: dict[str, Any]


def _acquire_retained_base_closure(
    context: observer.PublicGraphContextV1,
) -> _RetainedClosureV1:
    root_catalogue = observer.legal_action_catalogue_v1(
        context, observer.root_state_v1(context), 2
    )
    streams: dict[str, Any] = {}
    root_rows: list[acquisition.GraphPartialSupportRowV1] = []
    for action in root_catalogue.actions:
        stream = acquisition.open_graph_partial_support_prefix_v1(
            context, root_catalogue, action
        )
        row = stream.extend_validation_to(BASE_CHECKPOINT)
        streams[row.binding.row_id] = stream
        root_rows.append(row)
    root_tuple = tuple(sorted(root_rows, key=lambda item: item.binding.row_id))
    child_catalogues = tuple(
        sorted(
            (
                observer.legal_action_catalogue_v1(context, state, 1)
                for state in _active_states(root_tuple)
            ),
            key=lambda item: item.catalogue_id,
        )
    )
    child_rows: list[acquisition.GraphPartialSupportRowV1] = []
    for catalogue in child_catalogues:
        for action in catalogue.actions:
            stream = acquisition.open_graph_partial_support_prefix_v1(
                context, catalogue, action
            )
            row = stream.extend_validation_to(BASE_CHECKPOINT)
            streams[row.binding.row_id] = stream
            child_rows.append(row)
    child_tuple = tuple(sorted(child_rows, key=lambda item: item.binding.row_id))
    closure = h2_closure.ObservationSupportH2ClosureV1(
        context,
        BASE_CHECKPOINT,
        root_catalogue,
        child_catalogues,
        root_tuple,
        child_tuple,
        _aggregate_counters(root_tuple, child_catalogues, child_tuple),
    )
    if len(streams) != len(closure.all_rows):
        _fail("retained base streams do not cover the complete H2 closure")
    return _RetainedClosureV1(closure, streams)


@dataclass(frozen=True, slots=True)
class HeldoutCheckpointPreregistrationV1:
    _issuer: InitVar[object]
    context_id: str
    topology_id: str
    source_skeleton_id: str
    source_observation_log_id: str
    preregistration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREREGISTRATION_ISSUER:
            _fail("held-out checkpoint preregistration is caller-minted")
        for value, label in (
            (self.context_id, "target context"),
            (self.topology_id, "target topology"),
            (self.source_skeleton_id, "source skeleton"),
            (self.source_observation_log_id, "source observation log"),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_checkpoint_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_context_key": TARGET_CONTEXT_KEY,
            "target_context_id": self.context_id,
            "target_topology_id": self.topology_id,
            "source_skeleton_id": self.source_skeleton_id,
            "source_observation_log_id": self.source_observation_log_id,
            "source_vertex_counts": [4],
            "target_vertex_count": 5,
            "validation_checkpoints": [BASE_CHECKPOINT, RECOVERY_CHECKPOINT],
            "max_local_transactions": MAX_LOCAL_TRANSACTIONS,
            "coordinate_candidate_rule": "FIRST_NON_BASE_REGISTERED_CANDIDATE",
            "coordinate_candidate_ordinal": SELECTED_CANDIDATE_ORDINAL,
            "causal_selection_rule": CAUSAL_SELECTION_RULE,
            "request_must_precede_new_observation": True,
            "full_target_closure_authorized": False,
            "evaluation_exact_kernel_authorized": False,
            "ground_solver_authorized": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class HeldoutCoordinateCheckpointV1:
    _issuer: InitVar[object]
    preregistration_id: str
    closure_id: str
    base_bridge_id: str
    base_audit_id: str
    refinement_result_id: str
    candidate_spec_id: str
    coordinate_profile_id: str
    candidate_count: int
    failed_candidate_audit_ids: tuple[str, ...]
    checkpoint_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CHECKPOINT_ISSUER:
            _fail("coordinate checkpoint is caller-minted")
        for value, label in (
            (self.preregistration_id, "checkpoint preregistration"),
            (self.closure_id, "checkpoint closure"),
            (self.base_bridge_id, "checkpoint base bridge"),
            (self.base_audit_id, "checkpoint base audit"),
            (self.refinement_result_id, "checkpoint refinement"),
            (self.candidate_spec_id, "checkpoint candidate"),
            (self.coordinate_profile_id, "checkpoint profile"),
        ):
            _cid(value, label)
        if (
            type(self.candidate_count) is not int
            or self.candidate_count <= SELECTED_CANDIDATE_ORDINAL
            or type(self.failed_candidate_audit_ids) is not tuple
            or len(self.failed_candidate_audit_ids) != self.candidate_count
        ):
            _fail("coordinate checkpoint did not freeze the complete failed enumeration")
        for value in self.failed_candidate_audit_ids:
            _cid(value, "failed candidate audit")
        object.__setattr__(
            self, "checkpoint_id", content_id(CHECKPOINT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_coordinate_checkpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "closure_id": self.closure_id,
            "base_bridge_id": self.base_bridge_id,
            "base_audit_id": self.base_audit_id,
            "refinement_result_id": self.refinement_result_id,
            "candidate_spec_id": self.candidate_spec_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "candidate_ordinal": SELECTED_CANDIDATE_ORDINAL,
            "candidate_count": self.candidate_count,
            "failed_candidate_audit_ids": list(self.failed_candidate_audit_ids),
            "base_outcome": robust.RobustAuditStatus.FAILED_PROOF_FRONTIER.value,
            "refinement_outcome": refinement.CoordinateRefinementOutcome.NO_SOUND_COVER.value,
            "complete_candidate_enumeration": True,
            "selected_using_future_checkpoint_data": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "checkpoint_id": self.checkpoint_id}


@dataclass(frozen=True, slots=True)
class CausalRowCandidateV1:
    planner_row_id: str
    partial_row_id: str
    row_binding_id: str
    remaining_horizon: int
    zero_other_audit_id: str
    zero_other_failure_upper: Fraction
    zero_other_normalized_regret_upper: Fraction

    def __post_init__(self) -> None:
        for value, label in (
            (self.planner_row_id, "causal planner row"),
            (self.partial_row_id, "causal partial row"),
            (self.row_binding_id, "causal row binding"),
            (self.zero_other_audit_id, "causal counterfactual audit"),
        ):
            _cid(value, label)
        if self.remaining_horizon not in (1, 2):
            _fail("causal row horizon is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "planner_row_id": self.planner_row_id,
            "partial_row_id": self.partial_row_id,
            "row_binding_id": self.row_binding_id,
            "remaining_horizon": self.remaining_horizon,
            "zero_other_audit_id": self.zero_other_audit_id,
            "zero_other_failure_upper": _fdoc(self.zero_other_failure_upper),
            "zero_other_normalized_regret_upper": _fdoc(
                self.zero_other_normalized_regret_upper
            ),
        }


@dataclass(frozen=True, slots=True)
class HeldoutCausalRowEvidenceV1:
    _issuer: InitVar[object]
    transaction_index: int
    checkpoint_id: str
    prior_overlay_id: str | None
    failed_audit_id: str
    failed_frontier_id: str
    excluded_row_binding_ids: tuple[str, ...]
    causal_candidates: tuple[CausalRowCandidateV1, ...]
    selected: CausalRowCandidateV1
    evidence_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CAUSAL_ISSUER:
            _fail("causal row evidence is caller-minted")
        if self.transaction_index not in (1, 2):
            _fail("causal transaction index is outside the preregistered budget")
        for value, label in (
            (self.checkpoint_id, "causal checkpoint"),
            (self.failed_audit_id, "causal failed audit"),
            (self.failed_frontier_id, "causal frontier"),
        ):
            _cid(value, label)
        if self.prior_overlay_id is not None:
            _cid(self.prior_overlay_id, "causal prior overlay")
        if (
            self.excluded_row_binding_ids
            != tuple(sorted(set(self.excluded_row_binding_ids)))
            or type(self.causal_candidates) is not tuple
            or not self.causal_candidates
            or any(type(item) is not CausalRowCandidateV1 for item in self.causal_candidates)
            or self.selected not in self.causal_candidates
            or self.selected
            != sorted(
                self.causal_candidates,
                key=lambda item: (-item.remaining_horizon, item.planner_row_id),
            )[0]
            or self.selected.row_binding_id in self.excluded_row_binding_ids
        ):
            _fail("causal evidence changed the registered selection rule")
        object.__setattr__(self, "evidence_id", content_id(CAUSAL_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_causal_row_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_index": self.transaction_index,
            "checkpoint_id": self.checkpoint_id,
            "prior_overlay_id": self.prior_overlay_id,
            "failed_audit_id": self.failed_audit_id,
            "failed_frontier_id": self.failed_frontier_id,
            "excluded_row_binding_ids": list(self.excluded_row_binding_ids),
            "causal_candidates": [item.to_document() for item in self.causal_candidates],
            "selected_planner_row_id": self.selected.planner_row_id,
            "selected_partial_row_id": self.selected.partial_row_id,
            "selected_row_binding_id": self.selected.row_binding_id,
            "selected_remaining_horizon": self.selected.remaining_horizon,
            "selection_rule": CAUSAL_SELECTION_RULE,
            "counterfactual_is_selection_only": True,
            "counterfactual_probability_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class HeldoutRecoveryRequestV1:
    _issuer: InitVar[object]
    transaction_index: int
    preregistration_id: str
    causal_evidence_id: str
    row_binding_id: str
    before_partial_row_id: str
    request_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER or self.transaction_index not in (1, 2):
            _fail("recovery request is caller-minted or outside budget")
        for value, label in (
            (self.preregistration_id, "request preregistration"),
            (self.causal_evidence_id, "request causal evidence"),
            (self.row_binding_id, "request row binding"),
            (self.before_partial_row_id, "request predecessor row"),
        ):
            _cid(value, label)
        object.__setattr__(self, "request_id", content_id(REQUEST_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_recovery_request.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_index": self.transaction_index,
            "preregistration_id": self.preregistration_id,
            "causal_evidence_id": self.causal_evidence_id,
            "row_binding_id": self.row_binding_id,
            "before_partial_row_id": self.before_partial_row_id,
            "from_validation_checkpoint": BASE_CHECKPOINT,
            "to_validation_checkpoint": RECOVERY_CHECKPOINT,
            "authorized_incremental_draws": RECOVERY_CHECKPOINT - BASE_CHECKPOINT,
            "request_frozen_before_new_observation": True,
            "single_row_only": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class HeldoutValidationDeltaV1:
    _issuer: InitVar[object]
    request_id: str
    row_binding_id: str
    before_partial_row_id: str
    after_partial_row_id: str
    before_confidence_authority_id: str
    after_confidence_authority_id: str
    before_observation_prefix_digest: str
    after_observation_prefix_digest: str
    incremental_random_word_calls: int
    incremental_rejections: int
    delta_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DELTA_ISSUER:
            _fail("validation delta is caller-minted")
        for value, label in (
            (self.request_id, "delta request"),
            (self.row_binding_id, "delta row binding"),
            (self.before_partial_row_id, "delta predecessor row"),
            (self.after_partial_row_id, "delta successor row"),
            (self.before_confidence_authority_id, "delta predecessor authority"),
            (self.after_confidence_authority_id, "delta successor authority"),
            (self.before_observation_prefix_digest, "delta predecessor digest"),
            (self.after_observation_prefix_digest, "delta successor digest"),
        ):
            _cid(value, label)
        if (
            self.before_partial_row_id == self.after_partial_row_id
            or self.before_confidence_authority_id == self.after_confidence_authority_id
            or type(self.incremental_random_word_calls) is not int
            or self.incremental_random_word_calls < RECOVERY_CHECKPOINT - BASE_CHECKPOINT
            or type(self.incremental_rejections) is not int
            or self.incremental_rejections < 0
            or self.incremental_random_word_calls
            != RECOVERY_CHECKPOINT - BASE_CHECKPOINT + self.incremental_rejections
        ):
            _fail("validation delta counters or immutable successor changed")
        object.__setattr__(self, "delta_id", content_id(DELTA_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_validation_delta.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "row_binding_id": self.row_binding_id,
            "before_partial_row_id": self.before_partial_row_id,
            "after_partial_row_id": self.after_partial_row_id,
            "before_confidence_authority_id": self.before_confidence_authority_id,
            "after_confidence_authority_id": self.after_confidence_authority_id,
            "before_validation_checkpoint": BASE_CHECKPOINT,
            "after_validation_checkpoint": RECOVERY_CHECKPOINT,
            "incremental_observer_draws": RECOVERY_CHECKPOINT - BASE_CHECKPOINT,
            "incremental_random_word_calls": self.incremental_random_word_calls,
            "incremental_rejections": self.incremental_rejections,
            "before_observation_prefix_digest": self.before_observation_prefix_digest,
            "after_observation_prefix_digest": self.after_observation_prefix_digest,
            "predecessor_is_exact_prefix": True,
            "request_frozen_before_new_observation": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "delta_id": self.delta_id}


@dataclass(frozen=True, slots=True)
class HeldoutOverlayEpochV1:
    _issuer: InitVar[object]
    transaction_index: int
    prior_overlay_id: str | None
    prior_bridge_id: str
    prior_model_id: str
    prior_audit_id: str
    delta: HeldoutValidationDeltaV1
    changed_row_binding_ids: tuple[str, ...]
    preserved_row_binding_ids: tuple[str, ...]
    bridge: graph_model.ObservationSupportGraphModelBridgeV1 = field(repr=False)
    audit: robust.RobustPlanAuditV1 = field(repr=False)
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...] = field(repr=False)
    overlay_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OVERLAY_ISSUER or self.transaction_index not in (1, 2):
            _fail("overlay epoch is caller-minted or outside budget")
        for value, label in (
            (self.prior_bridge_id, "overlay prior bridge"),
            (self.prior_model_id, "overlay prior model"),
            (self.prior_audit_id, "overlay prior audit"),
        ):
            _cid(value, label)
        if self.prior_overlay_id is not None:
            _cid(self.prior_overlay_id, "overlay predecessor")
        if (
            type(self.delta) is not HeldoutValidationDeltaV1
            or self.changed_row_binding_ids != (self.delta.row_binding_id,)
            or self.preserved_row_binding_ids
            != tuple(sorted(set(self.preserved_row_binding_ids)))
            or self.delta.row_binding_id in self.preserved_row_binding_ids
            or type(self.bridge) is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or self.audit.model_id != self.bridge.quotient_model.model_id
            or self.audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
            or type(self.rows) is not tuple
            or len(self.rows) != 8
            or {item.binding.row_id for item in self.rows}
            != set(self.changed_row_binding_ids) | set(self.preserved_row_binding_ids)
        ):
            _fail("immutable overlay/model/audit binding is inconsistent")
        object.__setattr__(self, "overlay_id", content_id(OVERLAY_DOMAIN, self._payload()))

    @property
    def certified(self) -> bool:
        return self.audit.certified

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_overlay_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_index": self.transaction_index,
            "prior_overlay_id": self.prior_overlay_id,
            "prior_bridge_id": self.prior_bridge_id,
            "prior_model_id": self.prior_model_id,
            "prior_audit_id": self.prior_audit_id,
            "delta_id": self.delta.delta_id,
            "changed_row_binding_ids": list(self.changed_row_binding_ids),
            "preserved_row_binding_ids": list(self.preserved_row_binding_ids),
            "bridge_id": self.bridge.bridge_id,
            "quotient_model_id": self.bridge.quotient_model.model_id,
            "audit_id": self.audit.audit_id,
            "audit_status": self.audit.status.value,
            "root_failure_upper": _fdoc(self.audit.root_failure_upper),
            "normalized_regret_upper": _fdoc(self.audit.normalized_regret_upper),
            "immutable_query_neutral_overlay": True,
            "abstract_planner_invocations": 1,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "delta": self.delta.to_document(),
            "audit": self.audit.to_document(),
            "overlay_id": self.overlay_id,
        }


@dataclass(frozen=True, slots=True)
class HeldoutCheckpointTransactionV1:
    evidence: HeldoutCausalRowEvidenceV1
    request: HeldoutRecoveryRequestV1
    delta: HeldoutValidationDeltaV1
    overlay: HeldoutOverlayEpochV1

    def __post_init__(self) -> None:
        if (
            type(self.evidence) is not HeldoutCausalRowEvidenceV1
            or type(self.request) is not HeldoutRecoveryRequestV1
            or type(self.delta) is not HeldoutValidationDeltaV1
            or type(self.overlay) is not HeldoutOverlayEpochV1
            or self.evidence.transaction_index != self.request.transaction_index
            or self.request.transaction_index != self.overlay.transaction_index
            or self.request.causal_evidence_id != self.evidence.evidence_id
            or self.request.request_id != self.delta.request_id
            or self.delta.delta_id != self.overlay.delta.delta_id
        ):
            _fail("checkpoint transaction identity chain is incomplete")

    def to_document(self) -> dict[str, Any]:
        return {
            "evidence": self.evidence.to_document(),
            "request": self.request.to_document(),
            "delta": self.delta.to_document(),
            "overlay": self.overlay.to_document(),
        }


@dataclass(frozen=True, slots=True)
class HeldoutCheckpointRecertificationResultV1:
    _issuer: InitVar[object]
    preregistration: HeldoutCheckpointPreregistrationV1
    checkpoint: HeldoutCoordinateCheckpointV1
    context: observer.PublicGraphContextV1 = field(repr=False)
    root_catalogue: observer.LegalActionCatalogueV1 = field(repr=False)
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...] = field(repr=False)
    coordinate_profile: relational.ObservationSupportCoordinateProfileV1 = field(repr=False)
    threshold: robust.RobustThresholdProfileV1 = field(repr=False)
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1 = field(repr=False)
    base_audit: robust.RobustPlanAuditV1 = field(repr=False)
    base_rows: tuple[acquisition.GraphPartialSupportRowV1, ...] = field(repr=False)
    transactions: tuple[HeldoutCheckpointTransactionV1, ...]
    result_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("held-out recertification result is caller-minted")
        if (
            type(self.preregistration) is not HeldoutCheckpointPreregistrationV1
            or type(self.checkpoint) is not HeldoutCoordinateCheckpointV1
            or self.checkpoint.preregistration_id != self.preregistration.preregistration_id
            or type(self.context) is not observer.PublicGraphContextV1
            or self.context.context_key != TARGET_CONTEXT_KEY
            or type(self.root_catalogue) is not observer.LegalActionCatalogueV1
            or type(self.child_catalogues) is not tuple
            or type(self.coordinate_profile) is not relational.ObservationSupportCoordinateProfileV1
            or type(self.threshold) is not robust.RobustThresholdProfileV1
            or type(self.base_bridge) is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.base_audit) is not robust.RobustPlanAuditV1
            or self.base_audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            or type(self.base_rows) is not tuple
            or len(self.base_rows) != 8
            or type(self.transactions) is not tuple
            or len(self.transactions) != MAX_LOCAL_TRANSACTIONS
            or tuple(item.request.transaction_index for item in self.transactions) != (1, 2)
            or self.transactions[0].overlay.certified
            or not self.transactions[1].overlay.certified
            or self.transactions[0].evidence.selected.remaining_horizon != 2
            or self.transactions[1].evidence.selected.remaining_horizon != 1
            or len(
                {
                    item.evidence.selected.row_binding_id
                    for item in self.transactions
                }
            )
            != 2
        ):
            _fail("held-out recovery did not form the registered two-transaction proof")
        object.__setattr__(self, "result_id", content_id(RESULT_DOMAIN, self._payload()))

    @property
    def final_overlay(self) -> HeldoutOverlayEpochV1:
        return self.transactions[-1].overlay

    def _payload(self) -> dict[str, Any]:
        changed = tuple(
            sorted(item.evidence.selected.row_binding_id for item in self.transactions)
        )
        all_bindings = {item.binding.row_id for item in self.base_rows}
        preserved = tuple(sorted(all_bindings - set(changed)))
        return {
            "schema": "acfqp.construction_k7_heldout_checkpoint_recertification_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration.preregistration_id,
            "checkpoint_id": self.checkpoint.checkpoint_id,
            "target_context_id": self.context.context_id,
            "source_vertex_counts": [4],
            "target_vertex_count": 5,
            "base_bridge_id": self.base_bridge.bridge_id,
            "base_quotient_model_id": self.base_bridge.quotient_model.model_id,
            "base_audit_id": self.base_audit.audit_id,
            "base_audit_status": self.base_audit.status.value,
            "transaction_evidence_ids": [item.evidence.evidence_id for item in self.transactions],
            "recovery_request_ids": [item.request.request_id for item in self.transactions],
            "validation_delta_ids": [item.delta.delta_id for item in self.transactions],
            "overlay_ids": [item.overlay.overlay_id for item in self.transactions],
            "overlay_audit_statuses": [item.overlay.audit.status.value for item in self.transactions],
            "final_overlay_id": self.final_overlay.overlay_id,
            "final_bridge_id": self.final_overlay.bridge.bridge_id,
            "final_quotient_model_id": self.final_overlay.bridge.quotient_model.model_id,
            "final_audit_id": self.final_overlay.audit.audit_id,
            "final_root_failure_upper": _fdoc(self.final_overlay.audit.root_failure_upper),
            "final_normalized_regret_upper": _fdoc(
                self.final_overlay.audit.normalized_regret_upper
            ),
            "base_observer_draw_count": sum(
                item.counters.total_observer_draws for item in self.base_rows
            ),
            "incremental_local_ground_draw_count": 2
            * (RECOVERY_CHECKPOINT - BASE_CHECKPOINT),
            "changed_row_binding_ids": list(changed),
            "preserved_row_binding_ids": list(preserved),
            "changed_row_count": len(changed),
            "preserved_row_count": len(preserved),
            "full_4096_row_closure_built": False,
            "rows_retained_at_base_checkpoint": len(preserved),
            "multi_step_plan_formed_in_abstract_model": True,
            "local_ground_restoration_only_after_certificate_failure": True,
            "query_neutral_overlay_reusable": True,
            "evaluation_exact_kernel_calls": 0,
            "ground_solver_invocations": 0,
            "coordinate_primitive_invention_count": 0,
            "construction_certificate_status": (
                "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
            ),
            "formal_exact_iid_plan_certificate": False,
            "heldout_family_scope": "REGISTERED_N4_SOURCE_TO_W5_TARGET_ONLY",
            "broad_cross_domain_generalization_claimed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_STATUS,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_STATUS,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration": self.preregistration.to_document(),
            "checkpoint": self.checkpoint.to_document(),
            "transactions": [item.to_document() for item in self.transactions],
            "result_id": self.result_id,
        }


def _zero_other_single_row_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> robust.PartialSupportIntervalModelV1:
    rows: list[robust.IntervalSimplexRowV1] = []
    found = False
    for row in model.rows:
        if row.row_id != planner_row_id:
            rows.append(row)
            continue
        found = True
        masses = tuple(
            robust.IntervalDestinationMassV1(
                mass.destination_id,
                Fraction(0) if mass.destination_id == row.other_destination_id else mass.lower,
                Fraction(0) if mass.destination_id == row.other_destination_id else mass.upper,
            )
            for mass in row.masses
        )
        rows.append(
            robust.IntervalSimplexRowV1(
                row.state_id,
                row.remaining_horizon,
                row.action_id,
                row.reward_lower,
                row.reward_upper,
                row.other_destination_id,
                masses,
            )
        )
    if not found:
        _fail("failed frontier refers to a row outside the quotient model")
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=rows,
        concretizer_entries=model.concretizer_entries,
    )


def _causal_evidence(
    *,
    transaction_index: int,
    checkpoint: HeldoutCoordinateCheckpointV1,
    prior_overlay_id: str | None,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    threshold: robust.RobustThresholdProfileV1,
    excluded: tuple[str, ...],
) -> HeldoutCausalRowEvidenceV1:
    frontier = audit.failed_frontier
    if frontier is None:
        _fail("causal localization requires one failed proof frontier")
    projection_by_planner_row = {
        item.planner_row.row_id: item for item in bridge.row_projections
    }
    row_by_partial = {item.partial_row_id: item for item in rows}
    candidates: list[CausalRowCandidateV1] = []
    for planner_row_id in frontier.other_positive_row_ids:
        projection = projection_by_planner_row.get(planner_row_id)
        if projection is None:
            _fail("frontier row lacks a physical row projection")
        row = row_by_partial[projection.partial_row_id]
        if row.binding.row_id in excluded:
            continue
        counterfactual_model = _zero_other_single_row_model(
            bridge.quotient_model, planner_row_id
        )
        counterfactual_audit = robust.solve_quotient_robust_h2_v1(
            counterfactual_model, threshold
        )
        robust.verify_robust_plan_audit_v1(
            counterfactual_model, threshold, counterfactual_audit
        )
        if not counterfactual_audit.certified:
            continue
        candidates.append(
            CausalRowCandidateV1(
                planner_row_id,
                row.partial_row_id,
                row.binding.row_id,
                row.binding.remaining_horizon,
                counterfactual_audit.audit_id,
                counterfactual_audit.root_failure_upper,
                counterfactual_audit.normalized_regret_upper,
            )
        )
    ordered = tuple(
        sorted(candidates, key=lambda item: (-item.remaining_horizon, item.planner_row_id))
    )
    if not ordered:
        _fail("failed frontier has no sound singleton causal cover")
    return HeldoutCausalRowEvidenceV1(
        _CAUSAL_ISSUER,
        transaction_index,
        checkpoint.checkpoint_id,
        prior_overlay_id,
        audit.audit_id,
        frontier.frontier_id,
        excluded,
        ordered,
        ordered[0],
    )


def _build_preregistration(
    context: observer.PublicGraphContextV1,
) -> HeldoutCheckpointPreregistrationV1:
    skeleton = relational.v0066_source_skeleton_v1()
    if variable_order.SOURCE_VERTEX_COUNTS != (4,) or context.topology.vertex_count != 5:
        _fail("registered source/target structural split changed")
    return HeldoutCheckpointPreregistrationV1(
        _PREREGISTRATION_ISSUER,
        context.context_id,
        context.topology.topology_id,
        skeleton.skeleton_id,
        skeleton.source_observation_log_id,
    )


def run_heldout_checkpoint_recertification_v1(
) -> HeldoutCheckpointRecertificationResultV1:
    """Run the preregistered failed-proof/local-overlay/replan fixture."""

    context = observer.public_context_by_key_v1(TARGET_CONTEXT_KEY)
    preregistration = _build_preregistration(context)
    retained = _acquire_retained_base_closure(context)
    closure = retained.closure
    catalogues = (closure.root_catalogue, *closure.child_catalogues)
    base_profile = relational.base_coordinate_profile_v1()
    base_bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=catalogues,
        partial_rows=closure.all_rows,
        coordinate_profile=base_profile,
    )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=catalogues,
        partial_rows=closure.all_rows,
        bridge=base_bridge,
        coordinate_profile=base_profile,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id, context.risk_tolerance, base_bridge.reward_ceiling
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        base_bridge.quotient_model, threshold
    )
    robust.verify_robust_plan_audit_v1(
        base_bridge.quotient_model, threshold, base_audit
    )
    if base_audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER:
        _fail("held-out base quotient unexpectedly certified")
    refined = refinement.refine_observation_support_coordinates_v1(
        context=context,
        closure=closure,
        base_bridge=base_bridge,
        failed_audit=base_audit,
    )
    if (
        refined.outcome is not refinement.CoordinateRefinementOutcome.NO_SOUND_COVER
        or any(item.certified for item in refined.candidate_traces)
        or len(refined.candidate_specs) != len(refined.candidate_traces)
    ):
        _fail("base checkpoint is no longer the registered failed refinement control")
    selected_spec = refined.candidate_specs[SELECTED_CANDIDATE_ORDINAL]
    selected_trace = refined.candidate_traces[SELECTED_CANDIDATE_ORDINAL]
    if (
        selected_spec.kind is not refinement.CoordinateCandidateKind.SINGLE_STATE
        or selected_trace.candidate != selected_spec
        or selected_trace.certified
    ):
        _fail("first non-base observation-driven coordinate candidate changed")
    checkpoint = HeldoutCoordinateCheckpointV1(
        _CHECKPOINT_ISSUER,
        preregistration.preregistration_id,
        closure.closure_id,
        base_bridge.bridge_id,
        base_audit.audit_id,
        refined.result_id,
        selected_spec.candidate_spec_id,
        selected_spec.coordinate_profile.profile_id,
        len(refined.candidate_specs),
        tuple(item.robust_audit.audit_id for item in refined.candidate_traces),
    )

    current_rows = {item.binding.row_id: item for item in closure.all_rows}
    current_bridge = selected_trace.rebuilt_bridge
    current_audit = selected_trace.robust_audit
    recovered: tuple[str, ...] = ()
    prior_overlay_id: str | None = None
    transactions: list[HeldoutCheckpointTransactionV1] = []
    for transaction_index in (1, 2):
        evidence = _causal_evidence(
            transaction_index=transaction_index,
            checkpoint=checkpoint,
            prior_overlay_id=prior_overlay_id,
            bridge=current_bridge,
            audit=current_audit,
            rows=tuple(current_rows.values()),
            threshold=threshold,
            excluded=recovered,
        )
        binding_id = evidence.selected.row_binding_id
        before = current_rows[binding_id]
        request = HeldoutRecoveryRequestV1(
            _REQUEST_ISSUER,
            transaction_index,
            preregistration.preregistration_id,
            evidence.evidence_id,
            binding_id,
            before.partial_row_id,
        )
        # The content-addressed request above is frozen before this first new draw.
        after = retained.streams_by_binding_id[binding_id].extend_validation_to(
            RECOVERY_CHECKPOINT
        )
        before_ids = before.current_validation_observation_ids
        after_ids = after.current_validation_observation_ids
        if (
            after.binding != before.binding
            or after_ids[: len(before_ids)] != before_ids
            or len(after_ids) - len(before_ids) != RECOVERY_CHECKPOINT - BASE_CHECKPOINT
            or len(set(after_ids)) != len(after_ids)
        ):
            _fail("validation checkpoint extension is not one immutable prefix")
        delta = HeldoutValidationDeltaV1(
            _DELTA_ISSUER,
            request.request_id,
            binding_id,
            before.partial_row_id,
            after.partial_row_id,
            before.confidence_authority.authority_id,
            after.confidence_authority.authority_id,
            _digest_ids(before_ids),
            _digest_ids(after_ids),
            after.counters.current_validation_random_word_calls
            - before.counters.current_validation_random_word_calls,
            after.counters.current_validation_rejections
            - before.counters.current_validation_rejections,
        )
        prior_bridge = current_bridge
        prior_audit = current_audit
        current_rows[binding_id] = after
        ordered_rows = tuple(sorted(current_rows.values(), key=lambda item: item.partial_row_id))
        current_bridge = graph_model.build_observation_support_graph_models_v1(
            context=context,
            root_catalogue=closure.root_catalogue,
            catalogues=catalogues,
            partial_rows=ordered_rows,
            coordinate_profile=selected_spec.coordinate_profile,
        )
        graph_model.verify_observation_support_graph_models_v1(
            context=context,
            root_catalogue=closure.root_catalogue,
            catalogues=catalogues,
            partial_rows=ordered_rows,
            bridge=current_bridge,
            coordinate_profile=selected_spec.coordinate_profile,
        )
        current_audit = robust.solve_quotient_robust_h2_v1(
            current_bridge.quotient_model, threshold
        )
        robust.verify_robust_plan_audit_v1(
            current_bridge.quotient_model, threshold, current_audit
        )
        preserved = tuple(sorted(set(current_rows) - {binding_id}))
        overlay = HeldoutOverlayEpochV1(
            _OVERLAY_ISSUER,
            transaction_index,
            prior_overlay_id,
            prior_bridge.bridge_id,
            prior_bridge.quotient_model.model_id,
            prior_audit.audit_id,
            delta,
            (binding_id,),
            preserved,
            current_bridge,
            current_audit,
            ordered_rows,
        )
        transactions.append(HeldoutCheckpointTransactionV1(evidence, request, delta, overlay))
        recovered = tuple(sorted((*recovered, binding_id)))
        prior_overlay_id = overlay.overlay_id
    if transactions[0].overlay.certified or not transactions[1].overlay.certified:
        _fail("registered checkpoint sequence no longer fails then certifies")
    return HeldoutCheckpointRecertificationResultV1(
        _RESULT_ISSUER,
        preregistration,
        checkpoint,
        context,
        closure.root_catalogue,
        closure.child_catalogues,
        selected_spec.coordinate_profile,
        threshold,
        base_bridge,
        base_audit,
        closure.all_rows,
        tuple(transactions),
    )


def verify_heldout_checkpoint_recertification_v1(
    claimed: HeldoutCheckpointRecertificationResultV1,
) -> Mapping[str, Any]:
    """Replay every stored bridge/audit binding without drawing new samples."""

    if type(claimed) is not HeldoutCheckpointRecertificationResultV1:
        _fail("claimed held-out recertification has the wrong concrete type")
    if content_id(RESULT_DOMAIN, claimed._payload()) != claimed.result_id:
        _fail("held-out result content ID changed")
    catalogues = (claimed.root_catalogue, *claimed.child_catalogues)
    prior_overlay_id: str | None = None
    for transaction in claimed.transactions:
        overlay = transaction.overlay
        if overlay.prior_overlay_id != prior_overlay_id:
            _fail("overlay predecessor chain changed")
        graph_model.verify_observation_support_graph_models_v1(
            context=claimed.context,
            root_catalogue=claimed.root_catalogue,
            catalogues=catalogues,
            partial_rows=overlay.rows,
            bridge=overlay.bridge,
            coordinate_profile=claimed.coordinate_profile,
        )
        robust.verify_robust_plan_audit_v1(
            overlay.bridge.quotient_model, claimed.threshold, overlay.audit
        )
        prior_overlay_id = overlay.overlay_id
    return {
        "schema": "acfqp.construction_k7_heldout_checkpoint_recertification_verification.v1",
        "result_id": claimed.result_id,
        "replayed_final_overlay_id": claimed.final_overlay.overlay_id,
        "replayed_final_audit_id": claimed.final_overlay.audit.audit_id,
        "transaction_count": len(claimed.transactions),
        "new_observer_draws_during_verification": 0,
        "evaluation_exact_kernel_calls": 0,
        "ground_solver_invocations": 0,
        "valid": True,
        "independent_implementation_claimed": False,
    }


__all__ = [
    "BASE_CHECKPOINT",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7HeldoutCheckpointRecertificationV1Error",
    "HeldoutCausalRowEvidenceV1",
    "HeldoutCheckpointPreregistrationV1",
    "HeldoutCheckpointRecertificationResultV1",
    "HeldoutCheckpointTransactionV1",
    "HeldoutCoordinateCheckpointV1",
    "HeldoutOverlayEpochV1",
    "HeldoutRecoveryRequestV1",
    "HeldoutValidationDeltaV1",
    "LOCAL_DOMAINS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "RECOVERY_CHECKPOINT",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "run_heldout_checkpoint_recertification_v1",
    "verify_heldout_checkpoint_recertification_v1",
]
