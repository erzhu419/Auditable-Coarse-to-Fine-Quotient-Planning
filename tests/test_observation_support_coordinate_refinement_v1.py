from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.observation_support_coordinate_refinement_v1 as refinement
import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.observation_support_h2_closure_v1 as h2_closure
import acfqp.partial_support_confidence_v1 as confidence
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _FakeDiscoveryEvidence:
    observations: tuple[confidence.SplitSupportObservationV1, ...]
    discovery_evidence_id: str

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)


@dataclass(frozen=True)
class _FakeValidationEvidence:
    observations: tuple[confidence.SplitSupportObservationV1, ...]
    validation_evidence_id: str

    @property
    def sample_ids(self) -> tuple[str, ...]:
        return tuple(item.sample_id for item in self.observations)


@dataclass(frozen=True)
class _FakeSupportEpoch:
    support_epoch_id: str
    discovery_evidence: _FakeDiscoveryEvidence
    support_epoch_index: int = 1


@dataclass(frozen=True)
class _FakeInterval:
    event_key: str
    event_interval_id: str
    lower_probability: Fraction
    upper_probability: Fraction
    success_count: int


@dataclass(frozen=True)
class _FakeAuthority:
    authority_id: str
    validation_evidence: _FakeValidationEvidence
    event_intervals: tuple[_FakeInterval, ...]


@dataclass(frozen=True)
class _FakeCounters:
    initial_discovery_draws: int
    current_validation_draws: int


@dataclass(frozen=True)
class _FakePartialRow:
    binding: acquisition.GraphObservationRowBindingV1
    support_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    novel_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    support_epoch: _FakeSupportEpoch
    confidence_authority: _FakeAuthority
    other_interval: _FakeInterval
    initial_discovery_observation_ids: tuple[str, ...]
    current_validation_observation_ids: tuple[str, ...]
    counters: _FakeCounters
    partial_row_id: str
    physical_evidence_id: str
    prior_validation_observation_ids: tuple[str, ...] = ()
    route_independent_physical_prefix: bool = True

    @property
    def support_epoch_index(self) -> int:
        return self.support_epoch.support_epoch_index


@dataclass(frozen=True)
class _FakeClosure:
    context: observer.PublicGraphContextV1
    validation_checkpoint: int
    root_catalogue: observer.LegalActionCatalogueV1
    child_catalogues: tuple[observer.LegalActionCatalogueV1, ...]
    root_rows: tuple[_FakePartialRow, ...]
    child_rows: tuple[_FakePartialRow, ...]
    counters: object
    observation_only: bool = True
    current_support_epoch_index: int = 1
    validation_novel_child_expansion_allowed: bool = False
    route_independent_physical_evidence: bool = True

    @property
    def all_rows(self) -> tuple[_FakePartialRow, ...]:
        return (*self.root_rows, *self.child_rows)

    @property
    def closure_id(self) -> str:
        return _id(
            ":".join(
                (
                    self.context.context_id,
                    *(item.partial_row_id for item in self.all_rows),
                )
            )
        )

    def to_document(self) -> dict[str, object]:
        return {
            "context_id": self.context.context_id,
            "validation_checkpoint": self.validation_checkpoint,
            "root_catalogue_id": self.root_catalogue.catalogue_id,
            "child_catalogue_ids": [
                item.catalogue_id for item in self.child_catalogues
            ],
            "partial_row_ids": [
                item.partial_row_id for item in self.all_rows
            ],
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True)
class _Fixture:
    context: observer.PublicGraphContextV1
    closure: _FakeClosure
    bridge: graph_model.ObservationSupportGraphModelBridgeV1
    audit: robust.RobustPlanAuditV1


def _descriptor(
    state: observer.SymbolicGraphStateV1,
    reward: Fraction,
    *,
    terminal: bool,
) -> acquisition.GraphObservedOutcomeDescriptorV1:
    return acquisition.GraphObservedOutcomeDescriptorV1(
        state,
        reward,
        state.failure,
        terminal,
    )


def _observations(
    label: str,
    descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ],
) -> tuple[confidence.SplitSupportObservationV1, ...]:
    stream = _id(f"{label}:stream")
    return tuple(
        confidence.SplitSupportObservationV1(
            stream,
            _id(f"{label}:sample:{index}"),
            index,
            confidence.freeze_observed_joint_outcome_v1(descriptor),
        )
        for index, descriptor in enumerate(descriptors)
    )


def _row(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    distribution: tuple[
        tuple[acquisition.GraphObservedOutcomeDescriptorV1, int], ...
    ],
    *,
    validation_other: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ] = (),
) -> _FakePartialRow:
    binding = acquisition.GraphObservationRowBindingV1(
        context.context_id,
        catalogue.catalogue_id,
        catalogue.state.state_id,
        action,
        catalogue.remaining_horizon,
    )
    support = tuple(
        sorted(
            (item[0] for item in distribution),
            key=lambda item: item.outcome_id,
        )
    )
    count_by_id = {item.outcome_id: count for item, count in distribution}
    discovery_values = tuple(
        descriptor
        for descriptor in support
        for _ in range(count_by_id[descriptor.outcome_id])
    )
    validation_values = (*discovery_values, *validation_other)
    discovery = _observations(f"{binding.row_id}:discovery", discovery_values)
    validation = _observations(
        f"{binding.row_id}:validation",
        validation_values,
    )
    discovery_evidence = _FakeDiscoveryEvidence(
        discovery,
        _id(f"{binding.row_id}:discovery-evidence"),
    )
    validation_evidence = _FakeValidationEvidence(
        validation,
        _id(f"{binding.row_id}:validation-evidence"),
    )
    total = len(validation_values)
    known_intervals = tuple(
        _FakeInterval(
            descriptor.outcome_id,
            _id(f"{binding.row_id}:interval:{descriptor.outcome_id}"),
            Fraction(count_by_id[descriptor.outcome_id], total),
            Fraction(count_by_id[descriptor.outcome_id], total),
            count_by_id[descriptor.outcome_id],
        )
        for descriptor in support
    )
    other = _FakeInterval(
        "OTHER",
        _id(f"{binding.row_id}:interval:OTHER"),
        Fraction(len(validation_other), total),
        Fraction(len(validation_other), total),
        len(validation_other),
    )
    return _FakePartialRow(
        binding,
        support,
        tuple(
            sorted(
                set(validation_other),
                key=lambda item: item.outcome_id,
            )
        ),
        _FakeSupportEpoch(
            _id(f"{binding.row_id}:support"),
            discovery_evidence,
        ),
        _FakeAuthority(
            _id(f"{binding.row_id}:authority"),
            validation_evidence,
            (*known_intervals, other),
        ),
        other,
        discovery_evidence.sample_ids,
        validation_evidence.sample_ids,
        _FakeCounters(len(discovery), len(validation)),
        _id(f"{binding.row_id}:partial-row"),
        _id(f"{binding.row_id}:physical"),
    )


def _install_synthetic_types(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(refinement, "MAX_CANDIDATE_WORKERS", 1)
    monkeypatch.setattr(
        acquisition,
        "GraphPartialSupportRowV1",
        _FakePartialRow,
    )
    monkeypatch.setattr(
        h2_closure,
        "ObservationSupportH2ClosureV1",
        _FakeClosure,
    )
    monkeypatch.setattr(
        confidence,
        "verify_partial_support_confidence_v1",
        lambda _authority: None,
    )


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    refinable: bool,
) -> _Fixture:
    _install_synthetic_types(monkeypatch)
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    child_one_state = observer.SymbolicGraphStateV1(
        (0, 0, 0, 1, 1),
        False,
    )
    child_two_state = observer.SymbolicGraphStateV1(
        (
            (2, 0, 1, 0, 1)
            if refinable
            else (0, 0, 1, 0, 1)
        ),
        False,
    )
    children = tuple(
        observer.legal_action_catalogue_v1(context, state, 1)
        for state in (child_one_state, child_two_state)
    )
    root_safe = tuple(
        _descriptor(state, Fraction(0), terminal=False)
        for state in (child_one_state, child_two_state)
    )
    failure_state = observer.SymbolicGraphStateV1(
        (1, 2, 0, 0, 0),
        True,
    )
    root_bad = _descriptor(
        failure_state,
        Fraction(0),
        terminal=True,
    )
    root_rows = (
        _row(
            context,
            root,
            root.actions[0],
            ((root_safe[0], 2), (root_safe[1], 2)),
        ),
        _row(
            context,
            root,
            root.actions[1],
            ((root_bad, 4),),
        ),
    )
    child_rows: list[_FakePartialRow] = []
    for child_index, catalogue in enumerate(children):
        for action_index, action in enumerate(catalogue.actions):
            terminal = _descriptor(
                catalogue.state,
                (
                    Fraction(3, 64)
                    if action_index == child_index
                    else Fraction(0)
                ),
                terminal=True,
            )
            child_rows.append(
                _row(
                    context,
                    catalogue,
                    action,
                    ((terminal, 4),),
                )
            )
    closure = _FakeClosure(
        context,
        4,
        root,
        tuple(sorted(children, key=lambda item: item.catalogue_id)),
        tuple(sorted(root_rows, key=lambda item: item.binding.row_id)),
        tuple(
            sorted(child_rows, key=lambda item: item.binding.row_id)
        ),
        object(),
    )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, *children),
        partial_rows=closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    assert audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    return _Fixture(context, closure, bridge, audit)


def test_target_observations_generate_minimal_combined_sound_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)
    result = refinement.refine_observation_support_coordinates_v1(
        context=fixture.context,
        closure=fixture.closure,
        base_bridge=fixture.bridge,
        failed_audit=fixture.audit,
    )

    assert result.certified
    assert result.outcome is (
        refinement.CoordinateRefinementOutcome.CERTIFIED_REFINEMENT
    )
    selected = next(
        item
        for item in result.candidate_traces
        if item.candidate.candidate_spec_id
        == result.selected_candidate_spec_id
    )
    assert selected.candidate.kind is (
        refinement.CoordinateCandidateKind.STATE_ACTION
    )
    assert all(
        not item.certified
        for item in result.candidate_traces[: selected.candidate.ordinal]
    )
    assert len(result.candidate_specs) == (
        1
        + len(result.proposal_generation.state_coordinate_candidates)
        + len(result.proposal_generation.action_coordinate_candidates)
        + (
            len(result.proposal_generation.state_coordinate_candidates)
            * len(result.proposal_generation.action_coordinate_candidates)
        )
    )
    assert result.exact_oracle_query_count == 0
    assert not result.exact_iid_implementation_claimed
    assert not result.formal_exact_iid_plan_certificate
    assert (
        result.statistical_claim_scope
        == observer.STATISTICAL_CLAIM_SCOPE
    )
    with pytest.raises(
        refinement.ObservationSupportCoordinateRefinementInvariantViolation
    ):
        replace(result, exact_iid_implementation_claimed=True)
    with pytest.raises(
        refinement.ObservationSupportCoordinateRefinementInvariantViolation
    ):
        replace(result, formal_exact_iid_plan_certificate=True)


def test_complete_replay_rebuilds_generation_models_and_audits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)
    result = refinement.refine_observation_support_coordinates_v1(
        context=fixture.context,
        closure=fixture.closure,
        base_bridge=fixture.bridge,
        failed_audit=fixture.audit,
    )
    verification = (
        refinement.verify_observation_support_coordinate_refinement_v1(
            context=fixture.context,
            closure=fixture.closure,
            base_bridge=fixture.bridge,
            failed_audit=fixture.audit,
            claimed=result,
        )
    )
    assert verification.valid
    assert verification.result_id == result.result_id
    assert not verification.exact_iid_implementation_claimed
    assert not verification.formal_exact_iid_plan_certificate


def test_discovery_counts_are_replayed_and_other_is_proposal_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)
    row = next(
        item
        for item in fixture.closure.root_rows
        if len(item.support_descriptors) == 2
    )
    other_root_row = next(
        item for item in fixture.closure.root_rows if item is not row
    )
    novel = _descriptor(
        observer.SymbolicGraphStateV1((0, 1, 0, 1, 0), True),
        Fraction(0),
        terminal=True,
    )
    # A foreign validation-only outcome changes only proposal metadata here.
    changed = _row(
        fixture.context,
        fixture.closure.root_catalogue,
        row.binding.action,
        tuple(
            (descriptor, 2) for descriptor in row.support_descriptors
        ),
        validation_other=(novel,),
    )
    changed_closure = replace(
        fixture.closure,
        root_rows=tuple(
            sorted(
                (changed, other_root_row),
                key=lambda item: item.binding.row_id,
            )
        ),
    )
    changed_bridge = graph_model.build_observation_support_graph_models_v1(
        context=fixture.context,
        root_catalogue=changed_closure.root_catalogue,
        catalogues=(
            changed_closure.root_catalogue,
            *changed_closure.child_catalogues,
        ),
        partial_rows=changed_closure.all_rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        fixture.context.context_id,
        fixture.context.risk_tolerance,
        changed_bridge.reward_ceiling,
    )
    failed = robust.solve_quotient_robust_h2_v1(
        changed_bridge.quotient_model,
        threshold,
    )
    replay = refinement.replay_discovery_proposal_evidence_v1(
        context=fixture.context,
        closure=changed_closure,
        base_bridge=changed_bridge,
        failed_audit=failed,
    )
    selected = next(
        item
        for item in replay.row_replays
        if item.partial_row_id == changed.partial_row_id
    )
    assert selected.discovery_known_count == 4
    assert selected.validation_other_count == 1
    assert selected.proposal_row.other_count == 1
    assert selected.probability_evidence_draw_count == 0
    proposal = (
        refinement.adapter.build_proposal_only_relational_observation_log_v1(
            fixture.context,
            replay.proposal_rows,
        )
    )
    assert proposal.excluded_other_draw_count == 1
    assert not proposal.dynamics_certificate_eligible
    assert not proposal.plan_certificate_eligible


def test_no_generated_coordinate_cover_returns_typed_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=False)
    result = refinement.refine_observation_support_coordinates_v1(
        context=fixture.context,
        closure=fixture.closure,
        base_bridge=fixture.bridge,
        failed_audit=fixture.audit,
    )
    assert not result.certified
    assert result.outcome is (
        refinement.CoordinateRefinementOutcome.NO_SOUND_COVER
    )
    assert result.selected_profile_id is None
    assert all(not item.certified for item in result.candidate_traces)


def test_stale_audit_and_handmade_program_paths_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)
    direct = robust.solve_ground_direct_robust_h2_v1(
        fixture.bridge.direct_model,
        robust.RobustThresholdProfileV1(
            fixture.context.context_id,
            fixture.context.risk_tolerance,
            fixture.bridge.reward_ceiling,
        ),
    )
    with pytest.raises(
        refinement.ObservationSupportCoordinateRefinementInvariantViolation
    ):
        refinement.refine_observation_support_coordinates_v1(
            context=fixture.context,
            closure=fixture.closure,
            base_bridge=fixture.bridge,
            failed_audit=direct,
        )
    signature = (
        refinement.refine_observation_support_coordinates_v1
        .__annotations__
    )
    assert "coordinate_program" not in signature
    assert "candidate_registry" not in signature


def test_discovery_document_tamper_and_validation_other_count_tamper_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)
    row = next(
        item
        for item in fixture.closure.root_rows
        if len(item.support_descriptors) == 2
    )
    other_root_row = next(
        item for item in fixture.closure.root_rows if item is not row
    )
    observation = row.support_epoch.discovery_evidence.observations[0]
    foreign_descriptor = row.support_descriptors[1]
    tampered_observation = replace(
        observation,
        outcome=confidence.OpaqueObservedJointOutcomeV1(
            observation.outcome.outcome_id,
            foreign_descriptor.document,
        ),
    )
    tampered_discovery = replace(
        row.support_epoch.discovery_evidence,
        observations=(
            tampered_observation,
            *row.support_epoch.discovery_evidence.observations[1:],
        ),
    )
    tampered_row = replace(
        row,
        support_epoch=replace(
            row.support_epoch,
            discovery_evidence=tampered_discovery,
        ),
    )
    tampered_closure = replace(
        fixture.closure,
        root_rows=tuple(
            sorted(
                (tampered_row, other_root_row),
                key=lambda item: item.binding.row_id,
            )
        ),
    )
    with pytest.raises(
        refinement.ObservationSupportCoordinateRefinementInvariantViolation,
        match="document",
    ):
        refinement.replay_discovery_proposal_evidence_v1(
            context=fixture.context,
            closure=tampered_closure,
            base_bridge=fixture.bridge,
            failed_audit=fixture.audit,
        )

    wrong_other = replace(row.other_interval, success_count=1)
    wrong_authority = replace(
        row.confidence_authority,
        event_intervals=(
            *row.confidence_authority.event_intervals[:-1],
            wrong_other,
        ),
    )
    wrong_row = replace(
        row,
        confidence_authority=wrong_authority,
        other_interval=wrong_other,
    )
    wrong_closure = replace(
        fixture.closure,
        root_rows=tuple(
            sorted(
                (wrong_row, other_root_row),
                key=lambda item: item.binding.row_id,
            )
        ),
    )
    with pytest.raises(
        refinement.ObservationSupportCoordinateRefinementInvariantViolation,
        match="OTHER",
    ):
        refinement.replay_discovery_proposal_evidence_v1(
            context=fixture.context,
            closure=wrong_closure,
            base_bridge=fixture.bridge,
            failed_audit=fixture.audit,
        )


def test_operational_path_never_calls_exact_evaluation_oracle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(monkeypatch, refinable=True)

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("evaluation-only exact oracle was called")

    monkeypatch.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    monkeypatch.setattr(
        observer,
        "evaluation_exact_ground_search_v1",
        forbidden,
    )
    result = refinement.refine_observation_support_coordinates_v1(
        context=fixture.context,
        closure=fixture.closure,
        base_bridge=fixture.bridge,
        failed_audit=fixture.audit,
    )
    assert result.exact_oracle_query_count == 0
