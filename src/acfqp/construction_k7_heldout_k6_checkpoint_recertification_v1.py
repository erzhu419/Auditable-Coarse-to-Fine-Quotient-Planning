"""Second held-out checkpoint recovery into a reusable K6 world model.

The K6 target is structurally distinct from the frozen four-vertex source
family and from the W5 held-out positive control.  The complete public H=2
row set is observed only to the preregistered 8,192 validation checkpoint.
Coordinate proposals and causal counterfactuals are then evaluated without
new observations.  Only after a content-addressed request has been frozen is
one H=2 row extended to 16,384.  The immutable one-row overlay is replanned
and certified; the other nineteen rows remain at 8,192.

This is a finite, conditional-statistical construction certificate.  It does
not invoke the evaluation-only exact kernel or a ground solver, does not
claim automatic coordinate-language invention, and does not unlock official
execution or economics gates.
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
    CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.127"
PROFILE_KEY = "construction_k7_heldout_k6_checkpoint_recertification_v1"
TARGET_CONTEXT_KEY = "opaque_graph_k6_v0"
BASE_CHECKPOINT = 8_192
RECOVERY_CHECKPOINT = 16_384
MAX_LOCAL_TRANSACTIONS = 1
EXPECTED_BASE_ROW_COUNT = 20
EXPECTED_COORDINATE_CANDIDATE_COUNT = 10
COORDINATE_SELECTION_RULE = (
    "MAX_CURRENT_MINIMUM_SLACK_THEN_LOWEST_REGISTERED_ORDINAL"
)
CAUSAL_SELECTION_RULE = (
    "MAX_ZERO_OTHER_MINIMUM_SLACK_THEN_HIGHEST_HORIZON_"
    "THEN_PLANNER_ROW_ID"
)

PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN
)
CHECKPOINT_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN
CAUSAL_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN
REQUEST_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN
DELTA_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN
OVERLAY_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN
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
    raise RuntimeError("held-out K6 checkpoint domains are not central")

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


class ConstructionK7HeldoutK6CheckpointRecertificationV1Error(ValueError):
    """A K6 checkpoint, causal selection, or immutable overlay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutK6CheckpointRecertificationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutK6CheckpointRecertificationV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("K6 checkpoint arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _digest_ids(values: tuple[str, ...]) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


def _audit_slack(
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    return min(
        threshold.risk_tolerance - audit.root_failure_upper,
        threshold.normalized_regret_tolerance
        - audit.normalized_regret_upper,
    )


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
        total_observer_draws=sum(item.total_observer_draws for item in native),
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
                _fail("one K6 discovery-known state has conflicting documents")
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
    if (
        len(streams) != len(closure.all_rows)
        or len(streams) != EXPECTED_BASE_ROW_COUNT
    ):
        _fail("retained K6 streams do not cover the registered H2 closure")
    return _RetainedClosureV1(closure, streams)


@dataclass(frozen=True, slots=True)
class K6CheckpointPreregistrationV1:
    _issuer: InitVar[object]
    context_id: str
    topology_id: str
    source_skeleton_id: str
    source_observation_log_id: str
    preregistration_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREREGISTRATION_ISSUER:
            _fail("K6 checkpoint preregistration is caller-minted")
        for value, label in (
            (self.context_id, "K6 context"),
            (self.topology_id, "K6 topology"),
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
            "schema": "acfqp.construction_k7_heldout_k6_checkpoint_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_context_key": TARGET_CONTEXT_KEY,
            "target_context_id": self.context_id,
            "target_topology_id": self.topology_id,
            "source_skeleton_id": self.source_skeleton_id,
            "source_observation_log_id": self.source_observation_log_id,
            "source_vertex_counts": [4],
            "target_vertex_count": 6,
            "validation_checkpoints": [BASE_CHECKPOINT, RECOVERY_CHECKPOINT],
            "max_local_transactions": MAX_LOCAL_TRANSACTIONS,
            "coordinate_selection_rule": COORDINATE_SELECTION_RULE,
            "causal_selection_rule": CAUSAL_SELECTION_RULE,
            "request_must_precede_new_observation": True,
            "full_target_closure_authorized": False,
            "evaluation_exact_kernel_authorized": False,
            "ground_solver_authorized": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class K6CoordinateCheckpointV1:
    _issuer: InitVar[object]
    preregistration_id: str
    closure_id: str
    base_bridge_id: str
    base_audit_id: str
    refinement_result_id: str
    candidate_spec_ids: tuple[str, ...]
    candidate_profile_ids: tuple[str, ...]
    candidate_audit_ids: tuple[str, ...]
    candidate_minimum_slacks: tuple[Fraction, ...]
    selected_ordinal: int
    selected_spec_id: str
    selected_profile_id: str
    checkpoint_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CHECKPOINT_ISSUER:
            _fail("K6 coordinate checkpoint is caller-minted")
        for value, label in (
            (self.preregistration_id, "checkpoint preregistration"),
            (self.closure_id, "checkpoint closure"),
            (self.base_bridge_id, "checkpoint base bridge"),
            (self.base_audit_id, "checkpoint base audit"),
            (self.refinement_result_id, "checkpoint refinement"),
            (self.selected_spec_id, "selected coordinate spec"),
            (self.selected_profile_id, "selected coordinate profile"),
        ):
            _cid(value, label)
        for values, label in (
            (self.candidate_spec_ids, "coordinate specs"),
            (self.candidate_profile_ids, "coordinate profiles"),
            (self.candidate_audit_ids, "coordinate audits"),
        ):
            for value in values:
                _cid(value, label)
        expected_ordinal = min(
            range(len(self.candidate_minimum_slacks)),
            key=lambda index: (-self.candidate_minimum_slacks[index], index),
        )
        if (
            len(self.candidate_spec_ids) != len(self.candidate_profile_ids)
            or len(self.candidate_spec_ids) != len(self.candidate_audit_ids)
            or len(self.candidate_spec_ids) != EXPECTED_COORDINATE_CANDIDATE_COUNT
            or len(self.candidate_minimum_slacks)
            != EXPECTED_COORDINATE_CANDIDATE_COUNT
            or any(type(value) is not Fraction for value in self.candidate_minimum_slacks)
            or self.selected_ordinal != expected_ordinal
            or self.selected_spec_id != self.candidate_spec_ids[self.selected_ordinal]
            or self.selected_profile_id
            != self.candidate_profile_ids[self.selected_ordinal]
        ):
            _fail("K6 coordinate selection is incomplete or future-dependent")
        object.__setattr__(
            self, "checkpoint_id", content_id(CHECKPOINT_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_coordinate_checkpoint.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration_id,
            "closure_id": self.closure_id,
            "base_bridge_id": self.base_bridge_id,
            "base_audit_id": self.base_audit_id,
            "base_audit_status": "FAILED_PROOF_FRONTIER",
            "refinement_result_id": self.refinement_result_id,
            "refinement_outcome": "NO_SOUND_COVER",
            "candidate_spec_ids": list(self.candidate_spec_ids),
            "candidate_profile_ids": list(self.candidate_profile_ids),
            "candidate_audit_ids": list(self.candidate_audit_ids),
            "candidate_minimum_slacks": [
                _fdoc(value) for value in self.candidate_minimum_slacks
            ],
            "selected_ordinal": self.selected_ordinal,
            "selected_spec_id": self.selected_spec_id,
            "selected_profile_id": self.selected_profile_id,
            "selection_rule": COORDINATE_SELECTION_RULE,
            "selected_using_future_checkpoint_data": False,
            "observer_draws_during_coordinate_selection": 0,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "checkpoint_id": self.checkpoint_id}


@dataclass(frozen=True, slots=True)
class K6CausalRowCandidateV1:
    planner_row_id: str
    partial_row_id: str
    row_binding_id: str
    remaining_horizon: int
    zero_other_model_id: str
    zero_other_audit_id: str
    root_reward_lower: Fraction
    root_failure_upper: Fraction
    normalized_regret_upper: Fraction
    minimum_certificate_slack: Fraction
    certified: bool

    def __post_init__(self) -> None:
        for value, label in (
            (self.planner_row_id, "causal planner row"),
            (self.partial_row_id, "causal partial row"),
            (self.row_binding_id, "causal row binding"),
            (self.zero_other_model_id, "causal zero-OTHER model"),
            (self.zero_other_audit_id, "causal zero-OTHER audit"),
        ):
            _cid(value, label)
        if (
            self.remaining_horizon not in (1, 2)
            or any(
                type(value) is not Fraction
                for value in (
                    self.root_reward_lower,
                    self.root_failure_upper,
                    self.normalized_regret_upper,
                    self.minimum_certificate_slack,
                )
            )
            or type(self.certified) is not bool
            or self.certified is not (self.minimum_certificate_slack >= 0)
        ):
            _fail("K6 causal candidate is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "planner_row_id": self.planner_row_id,
            "partial_row_id": self.partial_row_id,
            "row_binding_id": self.row_binding_id,
            "remaining_horizon": self.remaining_horizon,
            "zero_other_model_id": self.zero_other_model_id,
            "zero_other_audit_id": self.zero_other_audit_id,
            "root_reward_lower": _fdoc(self.root_reward_lower),
            "root_failure_upper": _fdoc(self.root_failure_upper),
            "normalized_regret_upper": _fdoc(self.normalized_regret_upper),
            "minimum_certificate_slack": _fdoc(self.minimum_certificate_slack),
            "certified": self.certified,
        }


def _causal_sort_key(
    item: K6CausalRowCandidateV1,
) -> tuple[Fraction, int, str]:
    return (-item.minimum_certificate_slack, -item.remaining_horizon, item.planner_row_id)


@dataclass(frozen=True, slots=True)
class K6CausalRowEvidenceV1:
    _issuer: InitVar[object]
    checkpoint_id: str
    failed_model_id: str
    failed_audit_id: str
    failed_frontier_id: str
    selected_assignment_ids: tuple[str, ...]
    candidates: tuple[K6CausalRowCandidateV1, ...]
    selected: K6CausalRowCandidateV1
    evidence_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CAUSAL_ISSUER:
            _fail("K6 causal evidence is caller-minted")
        for value, label in (
            (self.checkpoint_id, "causal checkpoint"),
            (self.failed_model_id, "causal failed model"),
            (self.failed_audit_id, "causal failed audit"),
            (self.failed_frontier_id, "causal frontier"),
        ):
            _cid(value, label)
        for value in self.selected_assignment_ids:
            _cid(value, "causal selected assignment")
        if (
            self.selected_assignment_ids
            != tuple(sorted(set(self.selected_assignment_ids)))
            or type(self.candidates) is not tuple
            or len(self.candidates) != EXPECTED_BASE_ROW_COUNT
            or any(type(item) is not K6CausalRowCandidateV1 for item in self.candidates)
            or self.candidates != tuple(sorted(self.candidates, key=_causal_sort_key))
            or len({item.planner_row_id for item in self.candidates})
            != len(self.candidates)
            or len({item.row_binding_id for item in self.candidates})
            != len(self.candidates)
            or self.selected != self.candidates[0]
            or not self.selected.certified
        ):
            _fail("K6 causal evidence changed the registered selection rule")
        object.__setattr__(
            self, "evidence_id", content_id(CAUSAL_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_causal_row_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "checkpoint_id": self.checkpoint_id,
            "failed_model_id": self.failed_model_id,
            "failed_audit_id": self.failed_audit_id,
            "failed_frontier_id": self.failed_frontier_id,
            "selected_assignment_ids": list(self.selected_assignment_ids),
            "candidates": [item.to_document() for item in self.candidates],
            "selected_planner_row_id": self.selected.planner_row_id,
            "selected_partial_row_id": self.selected.partial_row_id,
            "selected_row_binding_id": self.selected.row_binding_id,
            "selected_remaining_horizon": self.selected.remaining_horizon,
            "selected_minimum_certificate_slack": _fdoc(
                self.selected.minimum_certificate_slack
            ),
            "selection_rule": CAUSAL_SELECTION_RULE,
            "counterfactual_scope": "CURRENT_FAILED_MODEL_ONLY",
            "counterfactual_observer_draws": 0,
            "future_checkpoint_data_accesses": 0,
            "minimum_authorized_cardinality": 1,
            "zero_row_baseline_failed": True,
            "global_candidate_uniqueness_claimed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


@dataclass(frozen=True, slots=True)
class K6RecoveryRequestV1:
    _issuer: InitVar[object]
    preregistration_id: str
    causal_evidence_id: str
    row_binding_id: str
    before_partial_row_id: str
    request_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER:
            _fail("K6 recovery request is caller-minted")
        for value, label in (
            (self.preregistration_id, "request preregistration"),
            (self.causal_evidence_id, "request causal evidence"),
            (self.row_binding_id, "request row binding"),
            (self.before_partial_row_id, "request predecessor row"),
        ):
            _cid(value, label)
        object.__setattr__(
            self, "request_id", content_id(REQUEST_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_recovery_request.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_index": 1,
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
class K6ValidationDeltaV1:
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
            _fail("K6 validation delta is caller-minted")
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
        incremental_draws = RECOVERY_CHECKPOINT - BASE_CHECKPOINT
        if (
            self.before_partial_row_id == self.after_partial_row_id
            or self.before_confidence_authority_id
            == self.after_confidence_authority_id
            or type(self.incremental_random_word_calls) is not int
            or type(self.incremental_rejections) is not int
            or self.incremental_rejections < 0
            or self.incremental_random_word_calls
            != incremental_draws + self.incremental_rejections
        ):
            _fail("K6 validation delta counters or successor changed")
        object.__setattr__(self, "delta_id", content_id(DELTA_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_validation_delta.v1",
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
class K6OverlayEpochV1:
    _issuer: InitVar[object]
    prior_bridge_id: str
    prior_model_id: str
    prior_audit_id: str
    delta: K6ValidationDeltaV1
    changed_row_binding_ids: tuple[str, ...]
    preserved_row_binding_ids: tuple[str, ...]
    bridge: graph_model.ObservationSupportGraphModelBridgeV1 = field(repr=False)
    audit: robust.RobustPlanAuditV1 = field(repr=False)
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...] = field(repr=False)
    overlay_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OVERLAY_ISSUER:
            _fail("K6 overlay is caller-minted")
        for value, label in (
            (self.prior_bridge_id, "overlay prior bridge"),
            (self.prior_model_id, "overlay prior model"),
            (self.prior_audit_id, "overlay prior audit"),
        ):
            _cid(value, label)
        if (
            type(self.delta) is not K6ValidationDeltaV1
            or self.changed_row_binding_ids != (self.delta.row_binding_id,)
            or self.preserved_row_binding_ids
            != tuple(sorted(set(self.preserved_row_binding_ids)))
            or self.delta.row_binding_id in self.preserved_row_binding_ids
            or type(self.bridge) is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or self.audit.model_id != self.bridge.quotient_model.model_id
            or self.audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
            or not self.audit.certified
            or type(self.rows) is not tuple
            or len(self.rows) != EXPECTED_BASE_ROW_COUNT
            or {item.binding.row_id for item in self.rows}
            != set(self.changed_row_binding_ids) | set(self.preserved_row_binding_ids)
            or len(self.preserved_row_binding_ids) != EXPECTED_BASE_ROW_COUNT - 1
        ):
            _fail("K6 immutable overlay/model/audit binding is inconsistent")
        object.__setattr__(
            self, "overlay_id", content_id(OVERLAY_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_overlay_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transaction_index": 1,
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
            "final_quotient_model": self.bridge.quotient_model.to_document(),
            "audit": self.audit.to_document(),
            "overlay_id": self.overlay_id,
        }


@dataclass(frozen=True, slots=True)
class K6CheckpointRecertificationResultV1:
    _issuer: InitVar[object]
    preregistration: K6CheckpointPreregistrationV1
    checkpoint: K6CoordinateCheckpointV1
    causal_evidence: K6CausalRowEvidenceV1
    request: K6RecoveryRequestV1
    delta: K6ValidationDeltaV1
    overlay: K6OverlayEpochV1
    context: observer.PublicGraphContextV1 = field(repr=False)
    root_catalogue: observer.LegalActionCatalogueV1 = field(repr=False)
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...] = field(repr=False)
    coordinate_profile: relational.ObservationSupportCoordinateProfileV1 = field(repr=False)
    threshold: robust.RobustThresholdProfileV1 = field(repr=False)
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1 = field(repr=False)
    base_audit: robust.RobustPlanAuditV1 = field(repr=False)
    base_rows: tuple[acquisition.GraphPartialSupportRowV1, ...] = field(repr=False)
    result_id: str = field(init=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER:
            _fail("K6 recertification result is caller-minted")
        if (
            type(self.preregistration) is not K6CheckpointPreregistrationV1
            or type(self.checkpoint) is not K6CoordinateCheckpointV1
            or type(self.causal_evidence) is not K6CausalRowEvidenceV1
            or type(self.request) is not K6RecoveryRequestV1
            or type(self.delta) is not K6ValidationDeltaV1
            or type(self.overlay) is not K6OverlayEpochV1
            or type(self.context) is not observer.PublicGraphContextV1
            or self.context.context_key != TARGET_CONTEXT_KEY
            or type(self.root_catalogue) is not observer.LegalActionCatalogueV1
            or type(self.child_catalogues) is not tuple
            or type(self.coordinate_profile)
            is not relational.ObservationSupportCoordinateProfileV1
            or type(self.threshold) is not robust.RobustThresholdProfileV1
            or type(self.base_bridge)
            is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.base_audit) is not robust.RobustPlanAuditV1
            or self.base_audit.status
            is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            or type(self.base_rows) is not tuple
            or len(self.base_rows) != EXPECTED_BASE_ROW_COUNT
            or self.checkpoint.preregistration_id
            != self.preregistration.preregistration_id
            or self.checkpoint.base_bridge_id != self.base_bridge.bridge_id
            or self.checkpoint.base_audit_id != self.base_audit.audit_id
            or self.checkpoint.selected_profile_id
            != self.coordinate_profile.profile_id
            or self.causal_evidence.checkpoint_id != self.checkpoint.checkpoint_id
            or self.request.causal_evidence_id != self.causal_evidence.evidence_id
            or self.request.row_binding_id
            != self.causal_evidence.selected.row_binding_id
            or self.request.request_id != self.delta.request_id
            or self.delta.delta_id != self.overlay.delta.delta_id
            or self.overlay.changed_row_binding_ids != (self.request.row_binding_id,)
            or self.causal_evidence.selected.remaining_horizon != 2
        ):
            _fail("K6 recovery did not form the registered one-row proof")
        object.__setattr__(self, "result_id", content_id(RESULT_DOMAIN, self._payload()))

    @property
    def final_overlay(self) -> K6OverlayEpochV1:
        return self.overlay

    def _payload(self) -> dict[str, Any]:
        changed = self.overlay.changed_row_binding_ids
        preserved = self.overlay.preserved_row_binding_ids
        return {
            "schema": "acfqp.construction_k7_heldout_k6_recertification_result.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration.preregistration_id,
            "checkpoint_id": self.checkpoint.checkpoint_id,
            "causal_evidence_id": self.causal_evidence.evidence_id,
            "recovery_request_id": self.request.request_id,
            "validation_delta_id": self.delta.delta_id,
            "final_overlay_id": self.overlay.overlay_id,
            "target_context_id": self.context.context_id,
            "source_vertex_counts": [4],
            "target_vertex_count": 6,
            "base_bridge_id": self.base_bridge.bridge_id,
            "base_quotient_model_id": self.base_bridge.quotient_model.model_id,
            "base_audit_id": self.base_audit.audit_id,
            "base_audit_status": self.base_audit.status.value,
            "final_bridge_id": self.overlay.bridge.bridge_id,
            "final_quotient_model_id": self.overlay.bridge.quotient_model.model_id,
            "final_audit_id": self.overlay.audit.audit_id,
            "final_audit_status": self.overlay.audit.status.value,
            "final_root_failure_upper": _fdoc(self.overlay.audit.root_failure_upper),
            "final_normalized_regret_upper": _fdoc(
                self.overlay.audit.normalized_regret_upper
            ),
            "base_observer_draw_count": sum(
                item.counters.total_observer_draws for item in self.base_rows
            ),
            "incremental_local_ground_draw_count": (
                RECOVERY_CHECKPOINT - BASE_CHECKPOINT
            ),
            "changed_row_binding_ids": list(changed),
            "preserved_row_binding_ids": list(preserved),
            "changed_row_count": len(changed),
            "preserved_row_count": len(preserved),
            "minimum_recovery_cardinality_within_registered_screen": 1,
            "global_row_choice_uniqueness_claimed": False,
            "full_16384_row_closure_built": False,
            "rows_retained_at_base_checkpoint": len(preserved),
            "multi_step_plan_formed_in_abstract_model": True,
            "local_ground_restoration_only_after_certificate_failure": True,
            "query_neutral_overlay_reusable": True,
            "coordinate_candidates_observation_driven": True,
            "coordinate_primitive_invention_count": 0,
            "evaluation_exact_kernel_calls": 0,
            "ground_solver_invocations": 0,
            "construction_certificate_status": (
                "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
            ),
            "formal_exact_iid_plan_certificate": False,
            "heldout_family_scope": (
                "REGISTERED_N4_SOURCE_TO_W5_AND_K6_TARGETS_ONLY"
            ),
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
            "context": self.context.to_document(),
            "coordinate_profile": self.coordinate_profile.to_document(),
            "threshold": self.threshold.to_document(),
            "base_quotient_model": self.base_bridge.quotient_model.to_document(),
            "preregistration": self.preregistration.to_document(),
            "checkpoint": self.checkpoint.to_document(),
            "causal_evidence": self.causal_evidence.to_document(),
            "request": self.request.to_document(),
            "delta": self.delta.to_document(),
            "overlay": self.overlay.to_document(),
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
        rows.append(
            robust.IntervalSimplexRowV1(
                row.state_id,
                row.remaining_horizon,
                row.action_id,
                row.reward_lower,
                row.reward_upper,
                row.other_destination_id,
                tuple(
                    robust.IntervalDestinationMassV1(
                        mass.destination_id,
                        (
                            Fraction(0)
                            if mass.destination_id == row.other_destination_id
                            else mass.lower
                        ),
                        (
                            Fraction(0)
                            if mass.destination_id == row.other_destination_id
                            else mass.upper
                        ),
                    )
                    for mass in row.masses
                ),
            )
        )
    if not found:
        _fail("K6 failed frontier refers to an absent planner row")
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=rows,
        concretizer_entries=model.concretizer_entries,
    )


def _build_causal_evidence(
    *,
    checkpoint: K6CoordinateCheckpointV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    audit: robust.RobustPlanAuditV1,
    rows: tuple[acquisition.GraphPartialSupportRowV1, ...],
    threshold: robust.RobustThresholdProfileV1,
) -> K6CausalRowEvidenceV1:
    frontier = audit.failed_frontier
    if frontier is None:
        _fail("K6 causal localization requires a failed proof frontier")
    projection_by_planner = {
        item.planner_row.row_id: item for item in bridge.row_projections
    }
    row_by_partial = {item.partial_row_id: item for item in rows}
    best_by_binding: dict[str, K6CausalRowCandidateV1] = {}
    for planner_row_id in frontier.other_positive_row_ids:
        projection = projection_by_planner.get(planner_row_id)
        if projection is None:
            _fail("K6 frontier row lacks a physical projection")
        physical = row_by_partial[projection.partial_row_id]
        counterfactual = _zero_other_single_row_model(
            bridge.quotient_model, planner_row_id
        )
        counterfactual_audit = robust.solve_quotient_robust_h2_v1(
            counterfactual, threshold
        )
        robust.verify_robust_plan_audit_v1(
            counterfactual, threshold, counterfactual_audit
        )
        candidate = K6CausalRowCandidateV1(
            planner_row_id,
            physical.partial_row_id,
            physical.binding.row_id,
            physical.binding.remaining_horizon,
            counterfactual.model_id,
            counterfactual_audit.audit_id,
            counterfactual_audit.root_reward_lower,
            counterfactual_audit.root_failure_upper,
            counterfactual_audit.normalized_regret_upper,
            _audit_slack(counterfactual_audit, threshold),
            counterfactual_audit.certified,
        )
        prior = best_by_binding.get(physical.binding.row_id)
        if prior is None or _causal_sort_key(candidate) < _causal_sort_key(prior):
            best_by_binding[physical.binding.row_id] = candidate
    candidates = tuple(sorted(best_by_binding.values(), key=_causal_sort_key))
    return K6CausalRowEvidenceV1(
        _CAUSAL_ISSUER,
        checkpoint.checkpoint_id,
        bridge.quotient_model.model_id,
        audit.audit_id,
        frontier.frontier_id,
        tuple(sorted(item.assignment_id for item in audit.assignments)),
        candidates,
        candidates[0],
    )


def _build_preregistration(
    context: observer.PublicGraphContextV1,
) -> K6CheckpointPreregistrationV1:
    skeleton = relational.v0066_source_skeleton_v1()
    if (
        variable_order.SOURCE_VERTEX_COUNTS != (4,)
        or context.topology.vertex_count != 6
    ):
        _fail("registered K6 source/target structural split changed")
    return K6CheckpointPreregistrationV1(
        _PREREGISTRATION_ISSUER,
        context.context_id,
        context.topology.topology_id,
        skeleton.skeleton_id,
        skeleton.source_observation_log_id,
    )


def run_heldout_k6_checkpoint_recertification_v1(
) -> K6CheckpointRecertificationResultV1:
    """Run the preregistered K6 failed-proof/one-row-overlay fixture."""

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
        context.context_id,
        context.risk_tolerance,
        base_bridge.reward_ceiling,
    )
    base_audit = robust.solve_quotient_robust_h2_v1(
        base_bridge.quotient_model, threshold
    )
    robust.verify_robust_plan_audit_v1(
        base_bridge.quotient_model, threshold, base_audit
    )
    if base_audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER:
        _fail("K6 base quotient unexpectedly certified")

    refined = refinement.refine_observation_support_coordinates_v1(
        context=context,
        closure=closure,
        base_bridge=base_bridge,
        failed_audit=base_audit,
    )
    if (
        refined.outcome is not refinement.CoordinateRefinementOutcome.NO_SOUND_COVER
        or len(refined.candidate_specs) != EXPECTED_COORDINATE_CANDIDATE_COUNT
        or len(refined.candidate_traces) != EXPECTED_COORDINATE_CANDIDATE_COUNT
        or any(item.certified for item in refined.candidate_traces)
    ):
        _fail("K6 coordinate enumeration is no longer the registered failure")
    coordinate_slacks = tuple(
        _audit_slack(item.robust_audit, threshold)
        for item in refined.candidate_traces
    )
    selected_ordinal = min(
        range(len(coordinate_slacks)),
        key=lambda index: (-coordinate_slacks[index], index),
    )
    selected_spec = refined.candidate_specs[selected_ordinal]
    selected_trace = refined.candidate_traces[selected_ordinal]
    checkpoint = K6CoordinateCheckpointV1(
        _CHECKPOINT_ISSUER,
        preregistration.preregistration_id,
        closure.closure_id,
        base_bridge.bridge_id,
        base_audit.audit_id,
        refined.result_id,
        tuple(item.candidate_spec_id for item in refined.candidate_specs),
        tuple(item.coordinate_profile.profile_id for item in refined.candidate_specs),
        tuple(item.robust_audit.audit_id for item in refined.candidate_traces),
        coordinate_slacks,
        selected_ordinal,
        selected_spec.candidate_spec_id,
        selected_spec.coordinate_profile.profile_id,
    )

    causal = _build_causal_evidence(
        checkpoint=checkpoint,
        bridge=selected_trace.rebuilt_bridge,
        audit=selected_trace.robust_audit,
        rows=closure.all_rows,
        threshold=threshold,
    )
    selected_binding = causal.selected.row_binding_id
    rows_by_binding = {item.binding.row_id: item for item in closure.all_rows}
    before = rows_by_binding[selected_binding]
    request = K6RecoveryRequestV1(
        _REQUEST_ISSUER,
        preregistration.preregistration_id,
        causal.evidence_id,
        selected_binding,
        before.partial_row_id,
    )
    # The request ID above is materialized before this first suffix draw.
    _ = request.request_id
    after = retained.streams_by_binding_id[selected_binding].extend_validation_to(
        RECOVERY_CHECKPOINT
    )
    before_ids = before.current_validation_observation_ids
    after_ids = after.current_validation_observation_ids
    if (
        after.binding != before.binding
        or after_ids[: len(before_ids)] != before_ids
        or len(after_ids) - len(before_ids)
        != RECOVERY_CHECKPOINT - BASE_CHECKPOINT
        or len(set(after_ids)) != len(after_ids)
    ):
        _fail("K6 validation suffix is not one immutable prefix")
    delta = K6ValidationDeltaV1(
        _DELTA_ISSUER,
        request.request_id,
        selected_binding,
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
    rows_by_binding[selected_binding] = after
    final_rows = tuple(
        sorted(rows_by_binding.values(), key=lambda item: item.partial_row_id)
    )
    final_bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=catalogues,
        partial_rows=final_rows,
        coordinate_profile=selected_spec.coordinate_profile,
    )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=catalogues,
        partial_rows=final_rows,
        bridge=final_bridge,
        coordinate_profile=selected_spec.coordinate_profile,
    )
    final_audit = robust.solve_quotient_robust_h2_v1(
        final_bridge.quotient_model, threshold
    )
    robust.verify_robust_plan_audit_v1(
        final_bridge.quotient_model, threshold, final_audit
    )
    if not final_audit.certified:
        _fail("registered K6 one-row checkpoint overlay no longer certifies")
    preserved = tuple(sorted(set(rows_by_binding) - {selected_binding}))
    overlay = K6OverlayEpochV1(
        _OVERLAY_ISSUER,
        selected_trace.rebuilt_bridge.bridge_id,
        selected_trace.rebuilt_bridge.quotient_model.model_id,
        selected_trace.robust_audit.audit_id,
        delta,
        (selected_binding,),
        preserved,
        final_bridge,
        final_audit,
        final_rows,
    )
    return K6CheckpointRecertificationResultV1(
        _RESULT_ISSUER,
        preregistration,
        checkpoint,
        causal,
        request,
        delta,
        overlay,
        context,
        closure.root_catalogue,
        closure.child_catalogues,
        selected_spec.coordinate_profile,
        threshold,
        selected_trace.rebuilt_bridge,
        selected_trace.robust_audit,
        closure.all_rows,
    )


def verify_heldout_k6_checkpoint_recertification_v1(
    claimed: K6CheckpointRecertificationResultV1,
) -> Mapping[str, Any]:
    """Replay K6 model, causal selection, prefix, and final certificate."""

    if type(claimed) is not K6CheckpointRecertificationResultV1:
        _fail("claimed K6 recertification has the wrong concrete type")
    if content_id(RESULT_DOMAIN, claimed._payload()) != claimed.result_id:
        _fail("K6 result content ID changed")
    catalogues = (claimed.root_catalogue, *claimed.child_catalogues)
    graph_model.verify_observation_support_graph_models_v1(
        context=claimed.context,
        root_catalogue=claimed.root_catalogue,
        catalogues=catalogues,
        partial_rows=claimed.base_rows,
        bridge=claimed.base_bridge,
        coordinate_profile=claimed.coordinate_profile,
    )
    robust.verify_robust_plan_audit_v1(
        claimed.base_bridge.quotient_model,
        claimed.threshold,
        claimed.base_audit,
    )
    replayed_causal = _build_causal_evidence(
        checkpoint=claimed.checkpoint,
        bridge=claimed.base_bridge,
        audit=claimed.base_audit,
        rows=claimed.base_rows,
        threshold=claimed.threshold,
    )
    if replayed_causal.to_document() != claimed.causal_evidence.to_document():
        _fail("K6 causal evidence did not replay")
    base_by_binding = {item.binding.row_id: item for item in claimed.base_rows}
    final_by_binding = {item.binding.row_id: item for item in claimed.overlay.rows}
    selected = claimed.request.row_binding_id
    if set(base_by_binding) != set(final_by_binding):
        _fail("K6 overlay changed the physical row domain")
    before = base_by_binding[selected]
    after = final_by_binding[selected]
    before_ids = before.current_validation_observation_ids
    after_ids = after.current_validation_observation_ids
    if (
        after_ids[: len(before_ids)] != before_ids
        or _digest_ids(before_ids)
        != claimed.delta.before_observation_prefix_digest
        or _digest_ids(after_ids)
        != claimed.delta.after_observation_prefix_digest
        or any(
            base_by_binding[binding].partial_row_id
            != final_by_binding[binding].partial_row_id
            for binding in claimed.overlay.preserved_row_binding_ids
        )
    ):
        _fail("K6 overlay physical-prefix replay failed")
    graph_model.verify_observation_support_graph_models_v1(
        context=claimed.context,
        root_catalogue=claimed.root_catalogue,
        catalogues=catalogues,
        partial_rows=claimed.overlay.rows,
        bridge=claimed.overlay.bridge,
        coordinate_profile=claimed.coordinate_profile,
    )
    robust.verify_robust_plan_audit_v1(
        claimed.overlay.bridge.quotient_model,
        claimed.threshold,
        claimed.overlay.audit,
    )
    return {
        "schema": "acfqp.construction_k7_heldout_k6_recertification_verification.v1",
        "result_id": claimed.result_id,
        "replayed_causal_evidence_id": replayed_causal.evidence_id,
        "replayed_final_overlay_id": claimed.overlay.overlay_id,
        "replayed_final_audit_id": claimed.overlay.audit.audit_id,
        "transaction_count": 1,
        "changed_row_count": 1,
        "preserved_row_count": EXPECTED_BASE_ROW_COUNT - 1,
        "new_observer_draws_during_verification": 0,
        "evaluation_exact_kernel_calls": 0,
        "ground_solver_invocations": 0,
        "valid": True,
        "independent_implementation_claimed": False,
    }


__all__ = [
    "BASE_CHECKPOINT",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7HeldoutK6CheckpointRecertificationV1Error",
    "K6CausalRowCandidateV1",
    "K6CausalRowEvidenceV1",
    "K6CheckpointPreregistrationV1",
    "K6CheckpointRecertificationResultV1",
    "K6CoordinateCheckpointV1",
    "K6OverlayEpochV1",
    "K6RecoveryRequestV1",
    "K6ValidationDeltaV1",
    "LOCAL_DOMAINS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "RECOVERY_CHECKPOINT",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "run_heldout_k6_checkpoint_recertification_v1",
    "verify_heldout_k6_checkpoint_recertification_v1",
]
