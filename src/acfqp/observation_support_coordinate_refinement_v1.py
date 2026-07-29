"""Target-observation-only coordinate refinement for V0-068.

This module is a narrow construction authority.  It accepts one complete
observation-only H=2 closure, the base relational model bridge rebuilt from
that closure, and the base quotient model's failed robust audit.  It then:

* replays the discovery transcript of every physical row and recomputes the
  discovery-known outcome multiplicities;
* records validation ``OTHER`` only as coordinate-proposal metadata;
* asks the target-local relational adapter to generate candidate programs;
* enumerates the base profile, every base-plus-one state or action program,
  and every base-plus-one-state-plus-one-action profile;
* rebuilds the complete interval model and re-solves the robust quotient for
  every candidate; and
* selects the first certified profile in the registered deterministic order.

Discovery counts never enter transition confidence.  Validation ``OTHER``
never becomes an invented outcome or a probability estimate.  The only
certificate authority is the exact bridge rebuild over the original
confidence-bound partial-support rows followed by the robust planner replay.
No exact kernel, source candidate registry, or manually supplied program is
accepted by the public entry point.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
import hashlib
from multiprocessing import get_context
import os
from typing import Any, Mapping

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.observation_support_relational_adapter_v1 as adapter
import acfqp.partial_support_confidence_v1 as support_confidence
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.portable_relational_skeleton_v1 import (
    FailedRelationalProofRefV1,
    PortableRelationalProgramV1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "target_observation_coordinate_refinement_v0"
REGISTERED_CANDIDATE_ORDER = (
    "BASE_THEN_SINGLE_STATE_THEN_SINGLE_ACTION_THEN_STATE_ACTION_"
    "BY_PROGRAM_ID"
)
PROPOSAL_COUNT_SEMANTICS = (
    "DISCOVERY_COUNTS_CONDITIONAL_KNOWN_ONLY_VALIDATION_OTHER_PROPOSAL_ONLY"
)
MAX_CANDIDATE_WORKERS = 32


DOMAIN_TAGS = {
    "row_replay": (
        "acfqp:observation-support-coordinate-refinement-row-replay:v1"
    ),
    "evidence_replay": (
        "acfqp:observation-support-coordinate-refinement-evidence-replay:v1"
    ),
    "candidate_spec": (
        "acfqp:observation-support-coordinate-refinement-candidate-spec:v1"
    ),
    "candidate_trace": (
        "acfqp:observation-support-coordinate-refinement-candidate-trace:v1"
    ),
    "result": "acfqp:observation-support-coordinate-refinement-result:v1",
    "verification": (
        "acfqp:observation-support-coordinate-refinement-verification:v1"
    ),
}


class ObservationSupportCoordinateRefinementInvariantViolation(ValueError):
    """A closure, evidence, candidate, rebuild, or audit binding is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _ids(values: Any, field: str) -> tuple[str, ...]:
    if type(values) is not tuple or values != tuple(sorted(set(values))):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            f"{field} must be a sorted distinct tuple"
        )
    for value in values:
        _cid(value, field)
    return values


class CoordinateCandidateKind(str, Enum):
    BASE = "BASE"
    SINGLE_STATE = "SINGLE_STATE"
    SINGLE_ACTION = "SINGLE_ACTION"
    STATE_ACTION = "STATE_ACTION"


class CoordinateRefinementOutcome(str, Enum):
    CERTIFIED_REFINEMENT = "CERTIFIED_REFINEMENT"
    NO_SOUND_COVER = "NO_SOUND_COVER"


@dataclass(frozen=True, slots=True)
class DiscoveryProposalRowReplayV1:
    """Counts replayed from split evidence; never a dynamics estimate."""

    partial_row_id: str
    physical_evidence_id: str
    row_binding_id: str
    catalogue_id: str
    support_epoch_id: str
    discovery_evidence_id: str
    validation_evidence_id: str
    confidence_authority_id: str
    proposal_row: adapter.DiscoveryKnownRelationalRowV1
    discovery_observation_ids: tuple[str, ...]
    validation_observation_ids: tuple[str, ...]
    discovery_draw_count: int
    validation_draw_count: int
    discovery_known_count: int
    validation_other_count: int
    probability_evidence_draw_count: int = 0
    other_is_proposal_only: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.partial_row_id, "row replay partial row"),
            (self.physical_evidence_id, "row replay physical evidence"),
            (self.row_binding_id, "row replay binding"),
            (self.catalogue_id, "row replay catalogue"),
            (self.support_epoch_id, "row replay support epoch"),
            (self.discovery_evidence_id, "row replay discovery evidence"),
            (self.validation_evidence_id, "row replay validation evidence"),
            (
                self.confidence_authority_id,
                "row replay confidence authority",
            ),
        ):
            _cid(value, field)
        if (
            type(self.proposal_row)
            is not adapter.DiscoveryKnownRelationalRowV1
            or self.proposal_row.support_epoch_id != self.support_epoch_id
            or self.proposal_row.catalogue.catalogue_id != self.catalogue_id
            or self.discovery_observation_ids
            != tuple(self.discovery_observation_ids)
            or self.validation_observation_ids
            != tuple(self.validation_observation_ids)
            or len(set(self.discovery_observation_ids))
            != len(self.discovery_observation_ids)
            or len(set(self.validation_observation_ids))
            != len(self.validation_observation_ids)
            or set(self.discovery_observation_ids)
            & set(self.validation_observation_ids)
            or any(
                _cid(item, "row replay observation") != item
                for item in (
                    *self.discovery_observation_ids,
                    *self.validation_observation_ids,
                )
            )
            or type(self.discovery_draw_count) is not int
            or self.discovery_draw_count <= 0
            or self.discovery_draw_count
            != len(self.discovery_observation_ids)
            or type(self.validation_draw_count) is not int
            or self.validation_draw_count <= 0
            or self.validation_draw_count
            != len(self.validation_observation_ids)
            or self.discovery_known_count != self.discovery_draw_count
            or self.proposal_row.known_count != self.discovery_known_count
            or self.validation_other_count != self.proposal_row.other_count
            or not 0 <= self.validation_other_count <= self.validation_draw_count
            or self.probability_evidence_draw_count != 0
            or self.other_is_proposal_only is not True
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "discovery/validation proposal replay changed its claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_row_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "partial_row_id": self.partial_row_id,
            "physical_evidence_id": self.physical_evidence_id,
            "row_binding_id": self.row_binding_id,
            "catalogue_id": self.catalogue_id,
            "support_epoch_id": self.support_epoch_id,
            "discovery_evidence_id": self.discovery_evidence_id,
            "validation_evidence_id": self.validation_evidence_id,
            "confidence_authority_id": self.confidence_authority_id,
            "proposal_row_id": self.proposal_row.proposal_row_id,
            "discovery_observation_ids": list(
                self.discovery_observation_ids
            ),
            "validation_observation_ids": list(
                self.validation_observation_ids
            ),
            "discovery_draw_count": self.discovery_draw_count,
            "validation_draw_count": self.validation_draw_count,
            "discovery_known_count": self.discovery_known_count,
            "validation_other_count": self.validation_other_count,
            "proposal_count_semantics": PROPOSAL_COUNT_SEMANTICS,
            "probability_evidence_draw_count": 0,
            "other_is_proposal_only": True,
        }

    @property
    def row_replay_id(self) -> str:
        return _content_id("row_replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "proposal_row": self.proposal_row.to_document(),
            "row_replay_id": self.row_replay_id,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryProposalEvidenceReplayV1:
    context_id: str
    closure_id: str
    base_bridge_id: str
    base_model_id: str
    failed_audit_id: str
    row_replays: tuple[DiscoveryProposalRowReplayV1, ...]
    total_discovery_draws: int
    total_validation_draws: int
    total_validation_other: int
    probability_evidence_draw_count: int = 0
    exact_oracle_query_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "evidence replay context"),
            (self.closure_id, "evidence replay closure"),
            (self.base_bridge_id, "evidence replay bridge"),
            (self.base_model_id, "evidence replay model"),
            (self.failed_audit_id, "evidence replay failed audit"),
        ):
            _cid(value, field)
        if (
            type(self.row_replays) is not tuple
            or not self.row_replays
            or any(
                type(item) is not DiscoveryProposalRowReplayV1
                for item in self.row_replays
            )
            or tuple(item.row_replay_id for item in self.row_replays)
            != tuple(
                sorted({item.row_replay_id for item in self.row_replays})
            )
            or self.total_discovery_draws
            != sum(item.discovery_draw_count for item in self.row_replays)
            or self.total_validation_draws
            != sum(item.validation_draw_count for item in self.row_replays)
            or self.total_validation_other
            != sum(item.validation_other_count for item in self.row_replays)
            or self.probability_evidence_draw_count != 0
            or self.exact_oracle_query_count != 0
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "aggregate proposal evidence replay is inconsistent"
            )

    @property
    def proposal_rows(
        self,
    ) -> tuple[adapter.DiscoveryKnownRelationalRowV1, ...]:
        return tuple(item.proposal_row for item in self.row_replays)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_"
                "evidence_replay.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "base_bridge_id": self.base_bridge_id,
            "base_model_id": self.base_model_id,
            "failed_audit_id": self.failed_audit_id,
            "row_replay_ids": [
                item.row_replay_id for item in self.row_replays
            ],
            "total_discovery_draws": self.total_discovery_draws,
            "total_validation_draws": self.total_validation_draws,
            "total_validation_other": self.total_validation_other,
            "proposal_count_semantics": PROPOSAL_COUNT_SEMANTICS,
            "probability_evidence_draw_count": 0,
            "exact_oracle_query_count": 0,
        }

    @property
    def evidence_replay_id(self) -> str:
        return _content_id("evidence_replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_replays": [item.to_document() for item in self.row_replays],
            "evidence_replay_id": self.evidence_replay_id,
        }


@dataclass(frozen=True, slots=True)
class CoordinateCandidateSpecV1:
    ordinal: int
    kind: CoordinateCandidateKind
    coordinate_profile: adapter.ObservationSupportCoordinateProfileV1
    state_extra_program_ids: tuple[str, ...]
    action_extra_program_ids: tuple[str, ...]
    proposal_generation_id: str

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.kind) is not CoordinateCandidateKind
            or type(self.coordinate_profile)
            is not adapter.ObservationSupportCoordinateProfileV1
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "coordinate candidate spec is malformed"
            )
        _ids(self.state_extra_program_ids, "candidate state extras")
        _ids(self.action_extra_program_ids, "candidate action extras")
        _cid(self.proposal_generation_id, "candidate generation")
        expected = {
            CoordinateCandidateKind.BASE: (0, 0),
            CoordinateCandidateKind.SINGLE_STATE: (1, 0),
            CoordinateCandidateKind.SINGLE_ACTION: (0, 1),
            CoordinateCandidateKind.STATE_ACTION: (1, 1),
        }[self.kind]
        if (
            (len(self.state_extra_program_ids), len(self.action_extra_program_ids))
            != expected
            or (
                self.kind is CoordinateCandidateKind.BASE
                and (
                    self.coordinate_profile.refinement_generation_id
                    is not None
                    or self.coordinate_profile.proposal_only_refinement
                )
            )
            or (
                self.kind is not CoordinateCandidateKind.BASE
                and (
                    self.coordinate_profile.refinement_generation_id
                    != self.proposal_generation_id
                    or not self.coordinate_profile.proposal_only_refinement
                )
            )
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "candidate shape/profile provenance is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_"
                "candidate_spec.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "kind": self.kind.value,
            "coordinate_profile_id": self.coordinate_profile.profile_id,
            "state_extra_program_ids": list(self.state_extra_program_ids),
            "action_extra_program_ids": list(self.action_extra_program_ids),
            "proposal_generation_id": self.proposal_generation_id,
            "candidate_order": REGISTERED_CANDIDATE_ORDER,
        }

    @property
    def candidate_spec_id(self) -> str:
        return _content_id("candidate_spec", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "coordinate_profile": self.coordinate_profile.to_document(),
            "candidate_spec_id": self.candidate_spec_id,
        }


@dataclass(frozen=True, slots=True)
class CoordinateCandidateTraceV1:
    candidate: CoordinateCandidateSpecV1
    context_id: str
    closure_id: str
    evidence_replay_id: str
    base_bridge_id: str
    failed_model_id: str
    failed_audit_id: str
    proposal_log_id: str
    proposal_generation_id: str
    rebuilt_bridge: graph_model.ObservationSupportGraphModelBridgeV1
    bridge_replay_id: str
    robust_audit: robust.RobustPlanAuditV1
    robust_verification_id: str
    certified: bool
    manual_program_count: int = 0
    source_registry_access_count: int = 0
    source_candidate_metric_access_count: int = 0
    exact_oracle_query_count: int = 0
    other_probability_evidence_draw_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "candidate trace context"),
            (self.closure_id, "candidate trace closure"),
            (self.evidence_replay_id, "candidate trace evidence"),
            (self.base_bridge_id, "candidate trace base bridge"),
            (self.failed_model_id, "candidate trace failed model"),
            (self.failed_audit_id, "candidate trace failed audit"),
            (self.proposal_log_id, "candidate trace proposal log"),
            (
                self.proposal_generation_id,
                "candidate trace proposal generation",
            ),
            (self.bridge_replay_id, "candidate trace bridge replay"),
            (
                self.robust_verification_id,
                "candidate trace robust verification",
            ),
        ):
            _cid(value, field)
        if (
            type(self.candidate) is not CoordinateCandidateSpecV1
            or type(self.rebuilt_bridge)
            is not graph_model.ObservationSupportGraphModelBridgeV1
            or type(self.robust_audit) is not robust.RobustPlanAuditV1
            or self.candidate.proposal_generation_id
            != self.proposal_generation_id
            or self.rebuilt_bridge.context_id != self.context_id
            or self.rebuilt_bridge.coordinate_profile_id
            != self.candidate.coordinate_profile.profile_id
            or self.robust_audit.solver_kind
            is not robust.RobustSolverKind.QUOTIENT
            or self.robust_audit.model_id
            != self.rebuilt_bridge.quotient_model.model_id
            or self.certified is not self.robust_audit.certified
            or self.manual_program_count != 0
            or self.source_registry_access_count != 0
            or self.source_candidate_metric_access_count != 0
            or self.exact_oracle_query_count != 0
            or self.other_probability_evidence_draw_count != 0
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "candidate trace crossed the target-observation authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_"
                "candidate_trace.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "candidate_spec_id": self.candidate.candidate_spec_id,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "evidence_replay_id": self.evidence_replay_id,
            "base_bridge_id": self.base_bridge_id,
            "failed_model_id": self.failed_model_id,
            "failed_audit_id": self.failed_audit_id,
            "proposal_log_id": self.proposal_log_id,
            "proposal_generation_id": self.proposal_generation_id,
            "rebuilt_bridge_id": self.rebuilt_bridge.bridge_id,
            "rebuilt_quotient_model_id": (
                self.rebuilt_bridge.quotient_model.model_id
            ),
            "bridge_replay_id": self.bridge_replay_id,
            "robust_audit_id": self.robust_audit.audit_id,
            "robust_verification_id": self.robust_verification_id,
            "certified": self.certified,
            "manual_program_count": 0,
            "source_registry_access_count": 0,
            "source_candidate_metric_access_count": 0,
            "exact_oracle_query_count": 0,
            "other_probability_evidence_draw_count": 0,
        }

    @property
    def candidate_trace_id(self) -> str:
        return _content_id("candidate_trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "candidate": self.candidate.to_document(),
            "robust_audit": self.robust_audit.to_document(),
            "candidate_trace_id": self.candidate_trace_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSupportCoordinateRefinementResultV1:
    context_id: str
    closure_id: str
    base_bridge_id: str
    base_model_id: str
    failed_audit_id: str
    threshold_profile_id: str
    evidence_replay: DiscoveryProposalEvidenceReplayV1
    failed_proof_ref: FailedRelationalProofRefV1
    proposal_log: adapter.ProposalOnlyAnonymousRelationalLogV1
    proposal_generation: adapter.ProposalOnlyRelationalProgramGenerationV1
    candidate_specs: tuple[CoordinateCandidateSpecV1, ...]
    candidate_traces: tuple[CoordinateCandidateTraceV1, ...]
    outcome: CoordinateRefinementOutcome
    selected_candidate_spec_id: str | None
    selected_profile_id: str | None
    selected_bridge_id: str | None
    selected_audit_id: str | None
    complete_candidate_enumeration: bool = True
    exact_oracle_query_count: int = 0
    randomness_implementation: str = (
        observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
    )
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = observer.STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "refinement result context"),
            (self.closure_id, "refinement result closure"),
            (self.base_bridge_id, "refinement result bridge"),
            (self.base_model_id, "refinement result model"),
            (self.failed_audit_id, "refinement result failed audit"),
            (self.threshold_profile_id, "refinement result threshold"),
        ):
            _cid(value, field)
        for value, field in (
            (self.selected_candidate_spec_id, "selected candidate"),
            (self.selected_profile_id, "selected profile"),
            (self.selected_bridge_id, "selected bridge"),
            (self.selected_audit_id, "selected audit"),
        ):
            if value is not None:
                _cid(value, field)
        if (
            type(self.evidence_replay)
            is not DiscoveryProposalEvidenceReplayV1
            or type(self.failed_proof_ref) is not FailedRelationalProofRefV1
            or type(self.proposal_log)
            is not adapter.ProposalOnlyAnonymousRelationalLogV1
            or type(self.proposal_generation)
            is not adapter.ProposalOnlyRelationalProgramGenerationV1
            or type(self.candidate_specs) is not tuple
            or not self.candidate_specs
            or type(self.candidate_traces) is not tuple
            or len(self.candidate_specs) != len(self.candidate_traces)
            or any(
                type(item) is not CoordinateCandidateSpecV1
                for item in self.candidate_specs
            )
            or any(
                type(item) is not CoordinateCandidateTraceV1
                for item in self.candidate_traces
            )
            or tuple(item.ordinal for item in self.candidate_specs)
            != tuple(range(len(self.candidate_specs)))
            or tuple(
                item.candidate.candidate_spec_id
                for item in self.candidate_traces
            )
            != tuple(item.candidate_spec_id for item in self.candidate_specs)
            or type(self.outcome) is not CoordinateRefinementOutcome
            or self.complete_candidate_enumeration is not True
            or self.exact_oracle_query_count != 0
            or self.randomness_implementation
            != observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope
            != observer.STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
            or self.evidence_replay.context_id != self.context_id
            or self.evidence_replay.closure_id != self.closure_id
            or self.evidence_replay.base_bridge_id != self.base_bridge_id
            or self.evidence_replay.base_model_id != self.base_model_id
            or self.evidence_replay.failed_audit_id != self.failed_audit_id
            or self.failed_proof_ref.target_context_id != self.context_id
            or self.failed_proof_ref.model_epoch_id != self.base_bridge_id
            or self.failed_proof_ref.failed_audit_id != self.failed_audit_id
            or self.proposal_log.proposal_log_id
            != self.proposal_generation.proposal_log_id
            or self.proposal_generation.portable_generation.failed_proof_ref_id
            != self.failed_proof_ref.failed_proof_ref_id
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "refinement result identity chain is incomplete"
            )
        expected_specs = _candidate_specs(
            adapter.base_coordinate_profile_v1(),
            self.proposal_generation,
        )
        if (
            self.candidate_specs != expected_specs
            or {
                item.proposal_row_id
                for item in self.evidence_replay.proposal_rows
            }
            != {
                item.proposal_row_id
                for item in self.proposal_log.proposal_rows
            }
            or self.candidate_traces[0].rebuilt_bridge.bridge_id
            != self.base_bridge_id
            or self.candidate_traces[0].robust_audit.audit_id
            != self.failed_audit_id
            or any(
                item.context_id != self.context_id
                or item.closure_id != self.closure_id
                or item.evidence_replay_id
                != self.evidence_replay.evidence_replay_id
                or item.base_bridge_id != self.base_bridge_id
                or item.failed_model_id != self.base_model_id
                or item.failed_audit_id != self.failed_audit_id
                or item.proposal_log_id != self.proposal_log.proposal_log_id
                or item.proposal_generation_id
                != self.proposal_generation.proposal_generation_id
                for item in self.candidate_traces
            )
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "candidate enumeration is not the exact generated authority chain"
            )
        certified = tuple(
            item for item in self.candidate_traces if item.certified
        )
        selected = certified[0] if certified else None
        expected_values = (
            (None, None, None, None)
            if selected is None
            else (
                selected.candidate.candidate_spec_id,
                selected.candidate.coordinate_profile.profile_id,
                selected.rebuilt_bridge.bridge_id,
                selected.robust_audit.audit_id,
            )
        )
        actual_values = (
            self.selected_candidate_spec_id,
            self.selected_profile_id,
            self.selected_bridge_id,
            self.selected_audit_id,
        )
        if (
            actual_values != expected_values
            or (
                selected is None
                and self.outcome
                is not CoordinateRefinementOutcome.NO_SOUND_COVER
            )
            or (
                selected is not None
                and self.outcome
                is not CoordinateRefinementOutcome.CERTIFIED_REFINEMENT
            )
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "refinement did not select the first certified candidate"
            )

    @property
    def certified(self) -> bool:
        return (
            self.outcome
            is CoordinateRefinementOutcome.CERTIFIED_REFINEMENT
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "base_bridge_id": self.base_bridge_id,
            "base_model_id": self.base_model_id,
            "failed_audit_id": self.failed_audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "evidence_replay_id": self.evidence_replay.evidence_replay_id,
            "failed_proof_ref_id": self.failed_proof_ref.failed_proof_ref_id,
            "proposal_log_id": self.proposal_log.proposal_log_id,
            "proposal_generation_id": (
                self.proposal_generation.proposal_generation_id
            ),
            "candidate_spec_ids": [
                item.candidate_spec_id for item in self.candidate_specs
            ],
            "candidate_trace_ids": [
                item.candidate_trace_id for item in self.candidate_traces
            ],
            "candidate_order": REGISTERED_CANDIDATE_ORDER,
            "outcome": self.outcome.value,
            "selected_candidate_spec_id": self.selected_candidate_spec_id,
            "selected_profile_id": self.selected_profile_id,
            "selected_bridge_id": self.selected_bridge_id,
            "selected_audit_id": self.selected_audit_id,
            "complete_candidate_enumeration": True,
            "exact_oracle_query_count": 0,
            "randomness_implementation": self.randomness_implementation,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evidence_replay": self.evidence_replay.to_document(),
            "failed_proof_ref": self.failed_proof_ref.to_document(),
            "proposal_log": self.proposal_log.to_document(),
            "proposal_generation": self.proposal_generation.to_document(),
            "candidate_specs": [
                item.to_document() for item in self.candidate_specs
            ],
            "candidate_traces": [
                item.to_document() for item in self.candidate_traces
            ],
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSupportCoordinateRefinementVerificationV1:
    result_id: str
    replayed_result_id: str
    selected_profile_id: str | None
    outcome: CoordinateRefinementOutcome
    valid: bool = True
    exact_oracle_query_count: int = 0
    exact_iid_implementation_claimed: bool = False
    statistical_claim_scope: str = observer.STATISTICAL_CLAIM_SCOPE
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        _cid(self.result_id, "verified refinement result")
        _cid(self.replayed_result_id, "replayed refinement result")
        if self.selected_profile_id is not None:
            _cid(self.selected_profile_id, "verified selected profile")
        if (
            self.result_id != self.replayed_result_id
            or type(self.outcome) is not CoordinateRefinementOutcome
            or self.valid is not True
            or self.exact_oracle_query_count != 0
            or self.exact_iid_implementation_claimed is not False
            or self.statistical_claim_scope
            != observer.STATISTICAL_CLAIM_SCOPE
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "coordinate refinement verification failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_coordinate_refinement_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "replayed_result_id": self.replayed_result_id,
            "selected_profile_id": self.selected_profile_id,
            "outcome": self.outcome.value,
            "valid": True,
            "exact_oracle_query_count": 0,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": self.statistical_claim_scope,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _closure_catalogues(
    closure: h2_closure.ObservationSupportH2ClosureV1,
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    return (closure.root_catalogue, *closure.child_catalogues)


def _replay_closure(
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
) -> None:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
        or type(closure) is not h2_closure.ObservationSupportH2ClosureV1
        or closure.context != context
        or closure.current_support_epoch_index != 1
        or closure.validation_novel_child_expansion_allowed
        or not closure.observation_only
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "coordinate refinement requires one complete epoch-1 H2 closure"
        )
    replayed = h2_closure.ObservationSupportH2ClosureV1(
        closure.context,
        closure.validation_checkpoint,
        closure.root_catalogue,
        closure.child_catalogues,
        closure.root_rows,
        closure.child_rows,
        closure.counters,
    )
    if (
        replayed.closure_id != closure.closure_id
        or canonical_json_bytes(replayed.to_document())
        != canonical_json_bytes(closure.to_document())
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "H2 closure does not replay byte-for-byte"
        )


def _row_replay(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    row: acquisition.GraphPartialSupportRowV1,
) -> DiscoveryProposalRowReplayV1:
    if (
        type(row) is not acquisition.GraphPartialSupportRowV1
        or row.binding.context_id != context.context_id
        or row.binding.catalogue_id != catalogue.catalogue_id
        or row.binding.state_id != catalogue.state.state_id
        or row.binding.remaining_horizon != catalogue.remaining_horizon
        or row.binding.action not in catalogue.actions
        or row.support_epoch_index != 1
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "proposal row is not an epoch-1 member of its public catalogue"
        )
    support_confidence.verify_partial_support_confidence_v1(
        row.confidence_authority
    )
    discovery = row.support_epoch.discovery_evidence
    validation = row.confidence_authority.validation_evidence
    observations = discovery.observations
    validation_observations = validation.observations
    support_by_id = {
        item.outcome_id: item for item in row.support_descriptors
    }
    counts = Counter(item.outcome.outcome_id for item in observations)
    if (
        tuple(sorted(counts)) != tuple(sorted(support_by_id))
        or discovery.sample_ids
        != row.initial_discovery_observation_ids
        or validation.sample_ids != row.current_validation_observation_ids
        or discovery.discovery_evidence_id
        != row.support_epoch.discovery_evidence.discovery_evidence_id
        or validation.validation_evidence_id
        != row.confidence_authority.validation_evidence.validation_evidence_id
        or row.counters.initial_discovery_draws != len(observations)
        or row.counters.current_validation_draws
        != len(validation_observations)
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "split transcripts do not reproduce the row identities"
        )
    for observation_item in observations:
        descriptor = support_by_id[observation_item.outcome.outcome_id]
        if canonical_json_bytes(dict(observation_item.outcome.document)) != (
            canonical_json_bytes(dict(descriptor.document))
        ):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "discovery transcript outcome document changed"
            )
    for observation_item in validation_observations:
        descriptor = support_by_id.get(observation_item.outcome.outcome_id)
        if descriptor is not None and canonical_json_bytes(
            dict(observation_item.outcome.document)
        ) != canonical_json_bytes(dict(descriptor.document)):
            raise ObservationSupportCoordinateRefinementInvariantViolation(
                "validation changed a discovery-known outcome document"
            )
    other_count = sum(
        item.outcome.outcome_id not in support_by_id
        for item in validation_observations
    )
    if (
        row.other_interval.success_count != other_count
        or row.other_interval
        != row.confidence_authority.event_intervals[-1]
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "validation OTHER count differs from confidence authority"
        )
    discovered: list[adapter.DiscoveryKnownOutcomeCountV1] = []
    for outcome_id in sorted(support_by_id):
        source = support_by_id[outcome_id]
        descriptor = adapter.discovered_outcome_descriptor_v1(
            context,
            catalogue,
            row.binding.action,
            source.next_state,
            source.realized_row_reward,
            source.failure,
            source.terminal,
        )
        discovered.append(
            adapter.DiscoveryKnownOutcomeCountV1(
                descriptor,
                counts[outcome_id],
            )
        )
    proposal = adapter.DiscoveryKnownRelationalRowV1(
        row.support_epoch.support_epoch_id,
        catalogue,
        row.binding.action,
        tuple(
            sorted(
                discovered,
                key=lambda item: item.descriptor.outcome_id,
            )
        ),
        other_count,
    )
    return DiscoveryProposalRowReplayV1(
        row.partial_row_id,
        row.physical_evidence_id,
        row.binding.row_id,
        catalogue.catalogue_id,
        row.support_epoch.support_epoch_id,
        discovery.discovery_evidence_id,
        validation.validation_evidence_id,
        row.confidence_authority.authority_id,
        proposal,
        discovery.sample_ids,
        validation.sample_ids,
        len(observations),
        len(validation_observations),
        sum(counts.values()),
        other_count,
    )


def replay_discovery_proposal_evidence_v1(
    *,
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    failed_audit: robust.RobustPlanAuditV1,
) -> DiscoveryProposalEvidenceReplayV1:
    """Recompute all proposal counts from the immutable split transcripts."""

    _replay_closure(context, closure)
    catalogue_by_id = {
        item.catalogue_id: item for item in _closure_catalogues(closure)
    }
    replays = tuple(
        sorted(
            (
                _row_replay(
                    context,
                    catalogue_by_id[row.binding.catalogue_id],
                    row,
                )
                for row in closure.all_rows
            ),
            key=lambda item: item.row_replay_id,
        )
    )
    return DiscoveryProposalEvidenceReplayV1(
        context.context_id,
        closure.closure_id,
        base_bridge.bridge_id,
        base_bridge.quotient_model.model_id,
        failed_audit.audit_id,
        replays,
        sum(item.discovery_draw_count for item in replays),
        sum(item.validation_draw_count for item in replays),
        sum(item.validation_other_count for item in replays),
    )


def _candidate_specs(
    base: adapter.ObservationSupportCoordinateProfileV1,
    generation: adapter.ProposalOnlyRelationalProgramGenerationV1,
) -> tuple[CoordinateCandidateSpecV1, ...]:
    state = tuple(
        sorted(
            generation.state_coordinate_candidates,
            key=lambda item: item.program_id,
        )
    )
    action = tuple(
        sorted(
            generation.action_coordinate_candidates,
            key=lambda item: item.program_id,
        )
    )
    raw: list[
        tuple[
            CoordinateCandidateKind,
            tuple[PortableRelationalProgramV1, ...],
            tuple[PortableRelationalProgramV1, ...],
        ]
    ] = [(CoordinateCandidateKind.BASE, (), ())]
    raw.extend(
        (CoordinateCandidateKind.SINGLE_STATE, (item,), ())
        for item in state
    )
    raw.extend(
        (CoordinateCandidateKind.SINGLE_ACTION, (), (item,))
        for item in action
    )
    raw.extend(
        (CoordinateCandidateKind.STATE_ACTION, (s_item,), (a_item,))
        for s_item in state
        for a_item in action
    )
    specs: list[CoordinateCandidateSpecV1] = []
    for ordinal, (kind, state_extra, action_extra) in enumerate(raw):
        profile = (
            base
            if kind is CoordinateCandidateKind.BASE
            else adapter.ObservationSupportCoordinateProfileV1(
                base.skeleton_id,
                (*base.state_programs, *state_extra),
                (*base.action_programs, *action_extra),
                generation.proposal_generation_id,
                True,
            )
        )
        specs.append(
            CoordinateCandidateSpecV1(
                ordinal,
                kind,
                profile,
                tuple(sorted(item.program_id for item in state_extra)),
                tuple(sorted(item.program_id for item in action_extra)),
                generation.proposal_generation_id,
            )
        )
    return tuple(specs)


@dataclass(frozen=True, slots=True)
class _CandidateEvaluationTaskV1:
    context: observer.PublicGraphContextV1
    root_catalogue: observer.LegalActionCatalogueV1
    catalogues: tuple[observer.LegalActionCatalogueV1, ...]
    partial_rows: tuple[acquisition.GraphPartialSupportRowV1, ...]
    threshold: robust.RobustThresholdProfileV1
    candidate: CoordinateCandidateSpecV1


def _evaluate_candidate_task_v1(
    task: _CandidateEvaluationTaskV1,
) -> tuple[
    graph_model.ObservationSupportGraphModelBridgeV1,
    str,
    robust.RobustPlanAuditV1,
    str,
]:
    rebuilt = graph_model.build_observation_support_graph_models_v1(
        context=task.context,
        root_catalogue=task.root_catalogue,
        catalogues=task.catalogues,
        partial_rows=task.partial_rows,
        coordinate_profile=task.candidate.coordinate_profile,
    )
    bridge_replay = graph_model.verify_observation_support_graph_models_v1(
        context=task.context,
        root_catalogue=task.root_catalogue,
        catalogues=task.catalogues,
        partial_rows=task.partial_rows,
        bridge=rebuilt,
        coordinate_profile=task.candidate.coordinate_profile,
    )
    audit = robust.solve_quotient_robust_h2_v1(
        rebuilt.quotient_model,
        task.threshold,
    )
    audit_replay = robust.verify_robust_plan_audit_v1(
        rebuilt.quotient_model,
        task.threshold,
        audit,
    )
    return (
        rebuilt,
        bridge_replay.verification_id,
        audit,
        audit_replay.verification_id,
    )


def _validate_base_authorities(
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    failed_audit: robust.RobustPlanAuditV1,
) -> tuple[
    adapter.ObservationSupportCoordinateProfileV1,
    robust.RobustThresholdProfileV1,
]:
    _replay_closure(context, closure)
    base = adapter.base_coordinate_profile_v1()
    if (
        type(base_bridge)
        is not graph_model.ObservationSupportGraphModelBridgeV1
        or base_bridge.context_id != context.context_id
        or base_bridge.coordinate_profile_id != base.profile_id
        or base_bridge.source_partial_row_ids
        != tuple(sorted(item.partial_row_id for item in closure.all_rows))
        or type(failed_audit) is not robust.RobustPlanAuditV1
        or failed_audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
        or failed_audit.model_id != base_bridge.quotient_model.model_id
        or failed_audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "base bridge is stale or audit is not its failed quotient authority"
        )
    graph_model.verify_observation_support_graph_models_v1(
        context=context,
        root_catalogue=closure.root_catalogue,
        catalogues=_closure_catalogues(closure),
        partial_rows=closure.all_rows,
        bridge=base_bridge,
        coordinate_profile=base,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        base_bridge.reward_ceiling,
    )
    if failed_audit.threshold_profile_id != threshold.threshold_profile_id:
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "failed quotient audit is bound to a different threshold"
        )
    robust.verify_robust_plan_audit_v1(
        base_bridge.quotient_model,
        threshold,
        failed_audit,
    )
    return base, threshold


def refine_observation_support_coordinates_v1(
    *,
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    failed_audit: robust.RobustPlanAuditV1,
) -> ObservationSupportCoordinateRefinementResultV1:
    """Enumerate and certify target-local coordinates from observed rows."""

    base, threshold = _validate_base_authorities(
        context,
        closure,
        base_bridge,
        failed_audit,
    )
    evidence = replay_discovery_proposal_evidence_v1(
        context=context,
        closure=closure,
        base_bridge=base_bridge,
        failed_audit=failed_audit,
    )
    skeleton = adapter.v0066_source_skeleton_v1()
    failed_ref = FailedRelationalProofRefV1(
        context.context_id,
        base_bridge.bridge_id,
        failed_audit.audit_id,
        "RISK_OR_REGRET",
    )
    proposal_log = (
        adapter.build_proposal_only_relational_observation_log_v1(
            context,
            evidence.proposal_rows,
            skeleton,
        )
    )
    generation = adapter.generate_proposal_only_relational_candidates_v1(
        skeleton,
        failed_ref,
        proposal_log,
    )
    if (
        generation.portable_generation.source_registry_access_count != 0
        or generation.portable_generation.source_candidate_metric_access_count
        != 0
        or generation.portable_generation.primitive_invention_count != 0
        or generation.dynamics_certificate_eligible
        or generation.plan_certificate_eligible
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "target candidate generation crossed its proposal-only boundary"
        )
    specs = _candidate_specs(base, generation)
    tasks = tuple(
        _CandidateEvaluationTaskV1(
            context,
            closure.root_catalogue,
            _closure_catalogues(closure),
            closure.all_rows,
            threshold,
            candidate,
        )
        for candidate in specs
    )
    if (
        type(closure) is h2_closure.ObservationSupportH2ClosureV1
        and len(tasks) > 1
    ):
        workers = min(
            MAX_CANDIDATE_WORKERS,
            len(tasks),
            os.cpu_count() or 1,
        )
        if workers == 1:
            evaluated = tuple(
                _evaluate_candidate_task_v1(task) for task in tasks
            )
        else:
            with ProcessPoolExecutor(
                max_workers=workers,
                mp_context=get_context("spawn"),
            ) as executor:
                evaluated = tuple(
                    executor.map(_evaluate_candidate_task_v1, tasks)
                )
    else:
        evaluated = tuple(
            _evaluate_candidate_task_v1(task) for task in tasks
        )
    traces: list[CoordinateCandidateTraceV1] = []
    for candidate, (
        rebuilt,
        bridge_replay_id,
        audit,
        audit_replay_id,
    ) in zip(specs, evaluated):
        traces.append(
            CoordinateCandidateTraceV1(
                candidate,
                context.context_id,
                closure.closure_id,
                evidence.evidence_replay_id,
                base_bridge.bridge_id,
                base_bridge.quotient_model.model_id,
                failed_audit.audit_id,
                proposal_log.proposal_log_id,
                generation.proposal_generation_id,
                rebuilt,
                bridge_replay_id,
                audit,
                audit_replay_id,
                audit.certified,
            )
        )
    trace_tuple = tuple(traces)
    selected = next((item for item in trace_tuple if item.certified), None)
    return ObservationSupportCoordinateRefinementResultV1(
        context.context_id,
        closure.closure_id,
        base_bridge.bridge_id,
        base_bridge.quotient_model.model_id,
        failed_audit.audit_id,
        threshold.threshold_profile_id,
        evidence,
        failed_ref,
        proposal_log,
        generation,
        specs,
        trace_tuple,
        (
            CoordinateRefinementOutcome.NO_SOUND_COVER
            if selected is None
            else CoordinateRefinementOutcome.CERTIFIED_REFINEMENT
        ),
        (
            None
            if selected is None
            else selected.candidate.candidate_spec_id
        ),
        (
            None
            if selected is None
            else selected.candidate.coordinate_profile.profile_id
        ),
        None if selected is None else selected.rebuilt_bridge.bridge_id,
        None if selected is None else selected.robust_audit.audit_id,
    )


def verify_observation_support_coordinate_refinement_v1(
    *,
    context: observer.PublicGraphContextV1,
    closure: h2_closure.ObservationSupportH2ClosureV1,
    base_bridge: graph_model.ObservationSupportGraphModelBridgeV1,
    failed_audit: robust.RobustPlanAuditV1,
    claimed: ObservationSupportCoordinateRefinementResultV1,
) -> ObservationSupportCoordinateRefinementVerificationV1:
    """Re-run generation, every model rebuild, and every robust audit."""

    if (
        type(claimed)
        is not ObservationSupportCoordinateRefinementResultV1
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "claimed coordinate refinement has the wrong concrete type"
        )
    replayed = refine_observation_support_coordinates_v1(
        context=context,
        closure=closure,
        base_bridge=base_bridge,
        failed_audit=failed_audit,
    )
    if (
        replayed != claimed
        or replayed.result_id != claimed.result_id
        or canonical_json_bytes(replayed.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportCoordinateRefinementInvariantViolation(
            "claimed coordinate refinement differs from complete replay"
        )
    return ObservationSupportCoordinateRefinementVerificationV1(
        claimed.result_id,
        replayed.result_id,
        claimed.selected_profile_id,
        claimed.outcome,
    )


__all__ = [
    "CONTRACT_VERSION",
    "CoordinateCandidateKind",
    "CoordinateCandidateSpecV1",
    "CoordinateCandidateTraceV1",
    "CoordinateRefinementOutcome",
    "DiscoveryProposalEvidenceReplayV1",
    "DiscoveryProposalRowReplayV1",
    "MAX_CANDIDATE_WORKERS",
    "ObservationSupportCoordinateRefinementInvariantViolation",
    "ObservationSupportCoordinateRefinementResultV1",
    "ObservationSupportCoordinateRefinementVerificationV1",
    "PROFILE_KEY",
    "PROPOSAL_COUNT_SEMANTICS",
    "REGISTERED_CANDIDATE_ORDER",
    "SCHEMA_VERSION",
    "refine_observation_support_coordinates_v1",
    "replay_discovery_proposal_evidence_v1",
    "verify_observation_support_coordinate_refinement_v1",
]
