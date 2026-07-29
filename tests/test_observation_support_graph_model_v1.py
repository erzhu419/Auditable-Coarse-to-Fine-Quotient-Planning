from __future__ import annotations

from dataclasses import replace
from dataclasses import dataclass
from fractions import Fraction
import hashlib

import pytest

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.observation_support_graph_model_v1 as bridge_module
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
class _FakeAuthority:
    authority_id: str
    event_intervals: tuple[_FakeEventInterval, ...]


@dataclass(frozen=True)
class _FakeSupportEpoch:
    support_epoch_id: str


@dataclass(frozen=True)
class _FakePartialRow:
    binding: acquisition.GraphObservationRowBindingV1
    support_descriptors: tuple[
        acquisition.GraphObservedOutcomeDescriptorV1, ...
    ]
    confidence_authority: _FakeAuthority
    support_epoch: _FakeSupportEpoch
    other_interval: _FakeEventInterval
    partial_row_id: str


def _synthetic_row(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    descriptor: acquisition.GraphObservedOutcomeDescriptorV1,
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
        _id(f"{binding.row_id}:known-event"),
        Fraction(99, 100),
        Fraction(1),
    )
    other = _FakeEventInterval(
        "OTHER",
        _id(f"{binding.row_id}:other-event"),
        Fraction(0),
        Fraction(1, 100),
    )
    authority = _FakeAuthority(
        _id(f"{binding.row_id}:authority"),
        (known, other),
    )
    return _FakePartialRow(
        binding=binding,
        support_descriptors=(descriptor,),
        confidence_authority=authority,
        support_epoch=_FakeSupportEpoch(
            _id(f"{binding.row_id}:support-epoch")
        ),
        other_interval=other,
        partial_row_id=_id(f"{binding.row_id}:partial-row"),
    )


def _install_fake_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        acquisition,
        "GraphPartialSupportRowV1",
        _FakePartialRow,
    )
    monkeypatch.setattr(
        bridge_module.confidence,
        "verify_partial_support_confidence_v1",
        lambda _authority: None,
    )


@pytest.fixture(scope="module")
def model_inputs():
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    root = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    failed = acquisition.GraphObservedOutcomeDescriptorV1(
        observer.SymbolicGraphStateV1((2, 0, 2, 1, 0), True),
        Fraction(1, 64),
        True,
        True,
    )
    safe_state = observer.SymbolicGraphStateV1((0, 2, 2, 1, 0), False)
    safe = acquisition.GraphObservedOutcomeDescriptorV1(
        safe_state,
        Fraction(1, 64),
        False,
        False,
    )
    child = observer.legal_action_catalogue_v1(
        context,
        safe_state,
        1,
    )
    terminal_one = acquisition.GraphObservedOutcomeDescriptorV1(
        observer.SymbolicGraphStateV1((1, 3, 0, 1, 0), False),
        Fraction(1, 32),
        False,
        True,
    )
    terminal_two = acquisition.GraphObservedOutcomeDescriptorV1(
        observer.SymbolicGraphStateV1((1, 0, 3, 1, 0), False),
        Fraction(1, 32),
        False,
        True,
    )
    rows = (
        _synthetic_row(context, root, root.actions[0], failed),
        _synthetic_row(context, root, root.actions[1], safe),
        _synthetic_row(context, child, child.actions[0], terminal_one),
        _synthetic_row(context, child, child.actions[1], terminal_two),
    )
    return context, root, child, rows


def test_builds_direct_and_relational_models_without_exact_authority(
    model_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, root, child, rows = model_inputs
    _install_fake_rows(monkeypatch)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("evaluation-only exact authority was called")

    monkeypatch.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    monkeypatch.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    bridge = bridge_module.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, child),
        partial_rows=rows,
    )

    assert bridge_module.CONTRACT_VERSION == "1.32.0"
    assert bridge.operational_exact_support_queries == 0
    assert bridge.operational_exact_probability_queries == 0
    assert len(bridge.source_partial_row_ids) == 4
    assert len(bridge.direct_model.rows) == 4
    assert bridge.direct_model.rows == bridge.quotient_model.rows
    assert bridge.direct_model.destinations == bridge.quotient_model.destinations
    assert sum(
        item.category is robust.DestinationCategory.OTHER
        for item in bridge.direct_model.destinations
    ) == 1
    assert (
        bridge.other_escape_handler.behavior
        == bridge_module.OTHER_ESCAPE_BEHAVIOR
    )
    assert (
        bridge.other_escape_handler.other_destination_id
        == bridge.other_destination_id
    )
    assert not bridge.other_escape_handler.requires_ground_action
    assert len(bridge.destination_bindings) == 4
    assert {
        item.category for item in bridge.destination_bindings
    } == {
        robust.DestinationCategory.ACTIVE_STATE,
        robust.DestinationCategory.FAILURE,
        robust.DestinationCategory.SUCCESS_TERMINAL,
    }
    assert all(
        catalogue.state_coordinate_key == catalogue.state_id
        and all(
            action.action_coordinate_key == action.action_id
            for action in catalogue.actions
        )
        for catalogue in bridge.direct_model.catalogues
    )
    assert bridge.quotient_model.concretizer_entries
    assert bridge.direct_model.model_id != bridge.quotient_model.model_id


def test_other_is_charged_once_and_reward_lower_is_adversarial(
    model_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, root, child, rows = model_inputs
    _install_fake_rows(monkeypatch)
    bridge = bridge_module.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, child),
        partial_rows=rows,
    )
    source_by_id = {item.partial_row_id: item for item in rows}
    for projection in bridge.row_projections:
        source = source_by_id[projection.partial_row_id]
        planner_row = projection.planner_row
        observed_reward = source.support_descriptors[0].realized_row_reward
        assert (
            planner_row.reward_lower
            == observed_reward * (1 - source.other_interval.upper_probability)
        )
        assert sum(
            item.destination_id == bridge.other_destination_id
            for item in planner_row.masses
        ) == 1
        assert len(projection.known_destination_ids) == 1
    assert {
        item.descriptor.outcome_id for item in bridge.destination_bindings
    } == {
        descriptor.outcome_id
        for row in rows
        for descriptor in row.support_descriptors
    }


def test_exact_bridge_replay_and_robust_planners(
    model_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, root, child, rows = model_inputs
    _install_fake_rows(monkeypatch)
    bridge = bridge_module.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, child),
        partial_rows=rows,
    )
    verification = (
        bridge_module.verify_observation_support_graph_models_v1(
            context=context,
            root_catalogue=root,
            catalogues=(root, child),
            partial_rows=rows,
            bridge=bridge,
        )
    )
    assert verification.bridge_id == bridge.bridge_id
    assert verification.operational_exact_support_queries == 0
    threshold = robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
    )
    direct_audit = robust.solve_ground_direct_robust_h2_v1(
        bridge.direct_model,
        threshold,
    )
    quotient_audit = robust.solve_quotient_robust_h2_v1(
        bridge.quotient_model,
        threshold,
    )
    assert direct_audit.kernel_calls == 0
    assert quotient_audit.kernel_calls == 0
    assert robust.verify_robust_plan_audit_v1(
        bridge.direct_model,
        threshold,
        direct_audit,
    ).valid
    assert robust.verify_robust_plan_audit_v1(
        bridge.quotient_model,
        threshold,
        quotient_audit,
    ).valid


def test_missing_child_rows_and_counter_injection_fail_closed(
    model_inputs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, root, child, rows = model_inputs
    _install_fake_rows(monkeypatch)
    with pytest.raises(
        bridge_module.ObservationSupportGraphModelInvariantViolation
    ):
        bridge_module.build_observation_support_graph_models_v1(
            context=context,
            root_catalogue=root,
            catalogues=(root, child),
            partial_rows=rows[:-1],
        )
    bridge = bridge_module.build_observation_support_graph_models_v1(
        context=context,
        root_catalogue=root,
        catalogues=(root, child),
        partial_rows=rows,
    )
    with pytest.raises(
        bridge_module.ObservationSupportGraphModelInvariantViolation
    ):
        replace(bridge, operational_exact_support_queries=1)
