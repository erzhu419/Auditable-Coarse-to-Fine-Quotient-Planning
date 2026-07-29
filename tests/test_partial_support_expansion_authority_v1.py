from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as graph_model
import acfqp.partial_support_expansion_authority_v1 as expansion
import acfqp.partial_support_robust_planner_v1 as robust
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _FakeEventInterval:
    event_key: str
    event_interval_id: str
    lower_probability: Fraction
    upper_probability: Fraction


@dataclass(frozen=True)
class _FakeValidationEvidence:
    sample_ids: tuple[str, ...]


@dataclass(frozen=True)
class _FakeAuthority:
    authority_id: str
    event_intervals: tuple[_FakeEventInterval, ...]
    validation_evidence: _FakeValidationEvidence


@dataclass(frozen=True)
class _FakeSupportEpoch:
    support_epoch_id: str
    support_epoch_index: int
    excluded_probability_sample_ids: tuple[str, ...]


@dataclass(frozen=True)
class _FakeObserverEpoch:
    epoch_id: str


@dataclass(frozen=True)
class _FakePartialRow:
    binding: acquisition.GraphObservationRowBindingV1
    support_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    novel_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    confidence_authority: _FakeAuthority
    support_epoch: _FakeSupportEpoch
    other_interval: _FakeEventInterval
    partial_row_id: str
    physical_evidence_id: str
    initial_discovery_observation_ids: tuple[str, ...]
    prior_validation_observation_ids: tuple[str, ...]
    current_validation_observation_ids: tuple[str, ...]
    observer_epoch_chain: tuple[_FakeObserverEpoch, ...]
    parent_row: _FakePartialRow | None = None

    @property
    def support_epoch_index(self) -> int:
        return self.support_epoch.support_epoch_index

    def to_document(self):
        return {
            "partial_row_id": self.partial_row_id,
            "parent_partial_row_id": (
                None if self.parent_row is None else self.parent_row.partial_row_id
            ),
        }


@dataclass(frozen=True)
class _Fixture:
    context: observer.PublicGraphContextV1
    root: observer.LegalActionCatalogueV1
    child: observer.LegalActionCatalogueV1
    rows: tuple[_FakePartialRow, ...]
    bridge: graph_model.ObservationSupportGraphModelBridgeV1
    threshold: robust.RobustThresholdProfileV1
    audit: robust.RobustPlanAuditV1


def _descriptor(
    ranks: tuple[int, ...],
    *,
    reward: Fraction,
    failure: bool,
    terminal: bool,
) -> acquisition.GraphObservedOutcomeDescriptorV1:
    return acquisition.GraphObservedOutcomeDescriptorV1(
        observer.SymbolicGraphStateV1(ranks, failure),
        reward,
        failure,
        terminal,
    )


def _fake_row(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    descriptor: acquisition.GraphObservedOutcomeDescriptorV1,
    *,
    other_upper: Fraction,
    novel: tuple[acquisition.GraphObservedOutcomeDescriptorV1, ...] = (),
) -> _FakePartialRow:
    binding = acquisition.GraphObservationRowBindingV1(
        context.context_id,
        catalogue.catalogue_id,
        catalogue.state.state_id,
        action,
        catalogue.remaining_horizon,
    )
    known = _FakeEventInterval(
        descriptor.outcome_id,
        _id(f"{binding.row_id}:known"),
        1 - other_upper,
        Fraction(1),
    )
    other = _FakeEventInterval(
        "OTHER",
        _id(f"{binding.row_id}:other"),
        Fraction(0),
        other_upper,
    )
    discovery = tuple(_id(f"{binding.row_id}:discovery:{i}") for i in range(4))
    validation = tuple(_id(f"{binding.row_id}:validation:{i}") for i in range(4))
    return _FakePartialRow(
        binding,
        (descriptor,),
        novel,
        _FakeAuthority(
            _id(f"{binding.row_id}:authority"),
            (known, other),
            _FakeValidationEvidence(validation),
        ),
        _FakeSupportEpoch(
            _id(f"{binding.row_id}:support:1"),
            1,
            discovery,
        ),
        other,
        _id(f"{binding.row_id}:partial"),
        _id(f"{binding.row_id}:physical"),
        discovery,
        (),
        validation,
        (_FakeObserverEpoch(_id(f"{binding.row_id}:observer:1")),),
    )


def _build_fixture(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root_other: Fraction,
    child_other: Fraction,
) -> _Fixture:
    monkeypatch.setattr(acquisition, "GraphPartialSupportRowV1", _FakePartialRow)
    monkeypatch.setattr(
        graph_model.confidence,
        "verify_partial_support_confidence_v1",
        lambda _authority: None,
    )
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    safe_state = observer.SymbolicGraphStateV1((0, 2, 2, 1, 0), False)
    child = observer.legal_action_catalogue_v1(context, safe_state, 1)
    failed = _descriptor(
        (2, 0, 2, 1, 0),
        reward=Fraction(1, 64),
        failure=True,
        terminal=True,
    )
    safe = _descriptor(
        safe_state.ranks,
        reward=Fraction(1, 64),
        failure=False,
        terminal=False,
    )
    terminal_one = _descriptor(
        (1, 3, 0, 1, 0),
        reward=Fraction(1, 32),
        failure=False,
        terminal=True,
    )
    terminal_two = _descriptor(
        (1, 0, 3, 1, 0),
        reward=Fraction(1, 32),
        failure=False,
        terminal=True,
    )
    novel = _descriptor(
        (0, 2, 1, 2, 0),
        reward=Fraction(1, 64),
        failure=False,
        terminal=False,
    )
    rows = (
        _fake_row(
            context,
            root,
            root.actions[0],
            failed,
            other_upper=Fraction(0),
        ),
        _fake_row(
            context,
            root,
            root.actions[1],
            safe,
            other_upper=root_other,
            novel=(novel,),
        ),
        _fake_row(
            context,
            child,
            child.actions[0],
            terminal_one,
            other_upper=child_other,
        ),
        _fake_row(
            context,
            child,
            child.actions[1],
            terminal_two,
            other_upper=child_other,
        ),
    )
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, child),
        partial_rows=rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    audit = robust.solve_ground_direct_robust_h2_v1(
        bridge.direct_model,
        threshold,
    )
    return _Fixture(context, root, child, rows, bridge, threshold, audit)


def _build_noncausal_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> _Fixture:
    """Four child branches make global OTHER causal but no single row causal."""

    monkeypatch.setattr(acquisition, "GraphPartialSupportRowV1", _FakePartialRow)
    monkeypatch.setattr(
        graph_model.confidence,
        "verify_partial_support_confidence_v1",
        lambda _authority: None,
    )
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    child_states = tuple(
        observer.SymbolicGraphStateV1(ranks, False)
        for ranks in (
            (0, 0, 0, 1, 1),
            (0, 0, 0, 2, 2),
            (0, 0, 1, 0, 1),
            (0, 0, 1, 1, 0),
        )
    )
    children = tuple(
        observer.legal_action_catalogue_v1(context, state, 1)
        for state in child_states
    )
    failed = _descriptor(
        (2, 0, 2, 1, 0),
        reward=Fraction(1, 64),
        failure=True,
        terminal=True,
    )
    safe_descriptors = tuple(
        _descriptor(
            state.ranks,
            reward=Fraction(1, 64),
            failure=False,
            terminal=False,
        )
        for state in child_states
    )
    novel = _descriptor(
        (0, 2, 1, 2, 0),
        reward=Fraction(1, 64),
        failure=False,
        terminal=False,
    )
    bad = _fake_row(
        context,
        root,
        root.actions[0],
        failed,
        other_upper=Fraction(0),
    )
    root_binding = acquisition.GraphObservationRowBindingV1(
        context.context_id,
        root.catalogue_id,
        root.state.state_id,
        root.actions[1],
        2,
    )
    root_known = tuple(
        _FakeEventInterval(
            descriptor.outcome_id,
            _id(f"{root_binding.row_id}:known:{descriptor.outcome_id}"),
            Fraction(99, 400),
            Fraction(1, 4),
        )
        for descriptor in safe_descriptors
    )
    root_other = _FakeEventInterval(
        "OTHER",
        _id(f"{root_binding.row_id}:other"),
        Fraction(0),
        Fraction(1, 100),
    )
    root_discovery = tuple(
        _id(f"{root_binding.row_id}:discovery:{index}") for index in range(4)
    )
    root_validation = tuple(
        _id(f"{root_binding.row_id}:validation:{index}") for index in range(4)
    )
    selected_root = _FakePartialRow(
        root_binding,
        safe_descriptors,
        (novel,),
        _FakeAuthority(
            _id(f"{root_binding.row_id}:authority"),
            (*root_known, root_other),
            _FakeValidationEvidence(root_validation),
        ),
        _FakeSupportEpoch(
            _id(f"{root_binding.row_id}:support:1"),
            1,
            root_discovery,
        ),
        root_other,
        _id(f"{root_binding.row_id}:partial"),
        _id(f"{root_binding.row_id}:physical"),
        root_discovery,
        (),
        root_validation,
        (_FakeObserverEpoch(_id(f"{root_binding.row_id}:observer:1")),),
    )
    child_rows: list[_FakePartialRow] = []
    for child_index, catalogue in enumerate(children):
        for action_index, action in enumerate(catalogue.actions):
            terminal = _descriptor(
                (
                    3,
                    child_index,
                    action_index,
                    (child_index + action_index) % 3,
                    0,
                ),
                reward=Fraction(1, 32),
                failure=False,
                terminal=True,
            )
            child_rows.append(
                _fake_row(
                    context,
                    catalogue,
                    action,
                    terminal,
                    other_upper=Fraction(3, 50),
                )
            )
    rows = (bad, selected_root, *child_rows)
    bridge = graph_model.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, *children),
        partial_rows=rows,
    )
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    audit = robust.solve_ground_direct_robust_h2_v1(
        bridge.direct_model,
        threshold,
    )
    return _Fixture(
        context,
        root,
        children[0],
        tuple(rows),
        bridge,
        threshold,
        audit,
    )


def _authorize(fixture: _Fixture):
    return expansion.authorize_partial_support_expansion_v1(
        bridge=fixture.bridge,
        audit=fixture.audit,
        threshold=fixture.threshold,
        partial_rows=fixture.rows,
    )


def test_authorizes_unique_earliest_individually_causal_selected_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(3, 50),
        child_other=Fraction(0),
    )
    assert fixture.audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert fixture.audit.counterfactual.changes_failed_to_certified
    authorization = _authorize(fixture)
    assert authorization.selected_remaining_horizon == 2
    assert authorization.selected_partial_row_id in {
        item.partial_row_id for item in fixture.rows
    }
    assert authorization.selected_novel_outcome_ids
    selected = next(
        item
        for item in authorization.candidate_evidence
        if item.evidence_id == authorization.selected_evidence_id
    )
    assert selected.changes_failed_to_certified
    assert authorization.assignment_ids == tuple(
        sorted(item.assignment_id for item in fixture.audit.assignments)
    )


def test_multiple_causal_rows_choose_earliest_horizon_deterministically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(3, 100),
        child_other=Fraction(3, 100),
    )
    authorization = _authorize(fixture)
    causal = tuple(
        item
        for item in authorization.candidate_evidence
        if item.changes_failed_to_certified
    )
    assert len(causal) >= 2
    assert authorization.selected_remaining_horizon == 2
    assert authorization.selected_evidence_id == min(
        causal,
        key=lambda item: (-item.remaining_horizon, item.planner_row_id),
    ).evidence_id


def test_rejects_certified_audit_without_failed_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(1, 100),
        child_other=Fraction(0),
    )
    assert fixture.audit.status is robust.RobustAuditStatus.CERTIFIED
    with pytest.raises(expansion.PartialSupportExpansionInvariantViolation):
        _authorize(fixture)


def test_rejects_global_but_not_row_local_causality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_noncausal_fixture(monkeypatch)
    assert fixture.audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert fixture.audit.counterfactual.changes_failed_to_certified
    with pytest.raises(
        expansion.PartialSupportExpansionInvariantViolation,
        match="individually causal",
    ):
        _authorize(fixture)


def test_stale_threshold_and_transplanted_row_set_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(3, 50),
        child_other=Fraction(0),
    )
    stale_threshold = robust.RobustThresholdProfileV1(
        fixture.context.context_id,
        Fraction(1, 10),
        fixture.bridge.reward_ceiling,
    )
    with pytest.raises(expansion.PartialSupportExpansionInvariantViolation):
        expansion.authorize_partial_support_expansion_v1(
            bridge=fixture.bridge,
            audit=fixture.audit,
            threshold=stale_threshold,
            partial_rows=fixture.rows,
        )
    with pytest.raises(expansion.PartialSupportExpansionInvariantViolation):
        expansion.authorize_partial_support_expansion_v1(
            bridge=fixture.bridge,
            audit=fixture.audit,
            threshold=fixture.threshold,
            partial_rows=fixture.rows[:-1],
        )


def _fresh_promoted_row(
    parent: _FakePartialRow,
    checkpoint_draw_count: int,
    *,
    reuse_old: bool = False,
) -> _FakePartialRow:
    current = (
        parent.current_validation_observation_ids
        if reuse_old
        else tuple(
            _id(f"{parent.partial_row_id}:fresh:{index}")
            for index in range(checkpoint_draw_count)
        )
    )
    support = tuple(
        sorted(
            (*parent.support_descriptors, *parent.novel_descriptors),
            key=lambda item: item.outcome_id,
        )
    )
    known = tuple(
        _FakeEventInterval(
            item.outcome_id,
            _id(f"{parent.partial_row_id}:promoted:{item.outcome_id}"),
            Fraction(0),
            Fraction(1),
        )
        for item in support
    )
    other = _FakeEventInterval(
        "OTHER",
        _id(f"{parent.partial_row_id}:promoted:other"),
        Fraction(0),
        Fraction(1),
    )
    old_ids = tuple(
        sorted(
            {
                *parent.initial_discovery_observation_ids,
                *parent.prior_validation_observation_ids,
                *parent.current_validation_observation_ids,
            }
        )
    )
    return _FakePartialRow(
        parent.binding,
        support,
        (),
        _FakeAuthority(
            _id(f"{parent.partial_row_id}:promoted:authority"),
            (*known, other),
            _FakeValidationEvidence(current),
        ),
        _FakeSupportEpoch(
            _id(f"{parent.partial_row_id}:support:2"),
            2,
            old_ids,
        ),
        other,
        _id(f"{parent.partial_row_id}:promoted:partial"),
        _id(f"{parent.partial_row_id}:promoted:physical"),
        parent.initial_discovery_observation_ids,
        (
            parent.prior_validation_observation_ids
            + parent.current_validation_observation_ids
        ),
        current,
        (
            *parent.observer_epoch_chain,
            _FakeObserverEpoch(_id(f"{parent.partial_row_id}:observer:2")),
        ),
        parent,
    )


def test_legal_authorized_promotion_uses_fresh_validation_and_binds_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(3, 50),
        child_other=Fraction(0),
    )
    authorization = _authorize(fixture)

    def promote(parent, _context, _catalogue, _action, checkpoint):
        return _fresh_promoted_row(parent, checkpoint)

    monkeypatch.setattr(
        acquisition,
        "promote_graph_partial_support_row_v1",
        promote,
    )
    result = expansion.promote_authorized_partial_support_row_v1(
        bridge=fixture.bridge,
        audit=fixture.audit,
        threshold=fixture.threshold,
        partial_rows=fixture.rows,
        authorization=authorization,
    )
    assert result.promoted_row.support_epoch_index == 2
    assert result.promoted_row.parent_row == result.parent_row
    assert result.pending_model_epoch.closure_rebuild_required
    assert not (
        set(result.pending_model_epoch.fresh_validation_observation_ids)
        & set(result.pending_model_epoch.quarantined_parent_observation_ids)
    )
    assert (
        result.pending_model_epoch.authorization_id
        == authorization.authorization_id
    )


def test_old_validation_reuse_and_stale_authorization_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _build_fixture(
        monkeypatch,
        root_other=Fraction(3, 50),
        child_other=Fraction(0),
    )
    authorization = _authorize(fixture)

    def reuse(parent, _context, _catalogue, _action, checkpoint):
        return _fresh_promoted_row(parent, checkpoint, reuse_old=True)

    monkeypatch.setattr(
        acquisition,
        "promote_graph_partial_support_row_v1",
        reuse,
    )
    with pytest.raises(
        expansion.PartialSupportExpansionInvariantViolation,
        match="reused old samples",
    ):
        expansion.promote_authorized_partial_support_row_v1(
            bridge=fixture.bridge,
            audit=fixture.audit,
            threshold=fixture.threshold,
            partial_rows=fixture.rows,
            authorization=authorization,
        )

    stale = replace(
        authorization,
        selected_parent_physical_evidence_id=_id("stale-physical"),
    )
    with pytest.raises(
        expansion.PartialSupportExpansionInvariantViolation,
        match="stale or transplanted",
    ):
        expansion.promote_authorized_partial_support_row_v1(
            bridge=fixture.bridge,
            audit=fixture.audit,
            threshold=fixture.threshold,
            partial_rows=fixture.rows,
            authorization=stale,
        )
