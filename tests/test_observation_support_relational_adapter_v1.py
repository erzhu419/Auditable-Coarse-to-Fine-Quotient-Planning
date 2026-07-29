from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
import inspect
import json

import pytest

import acfqp.cross_graph_relational_support_v1 as legacy_source
import acfqp.observation_support_relational_adapter_v1 as adapter
import acfqp.portable_relational_skeleton_v1 as portable
import acfqp.transition_tuple_observer_v1 as observer
import acfqp.variable_order_graph_rapm_v1 as legacy_graph


def _w5_binding() -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    observer.SupportEpochIdentityV1,
]:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    catalogue = observer.legal_action_catalogue_v1(
        context,
        observer.root_state_v1(context),
        2,
    )
    return context, catalogue, observer.support_epoch_identity_v1(context, 0)


def _observed_proposal_row(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    epoch: observer.SupportEpochIdentityV1,
    action: tuple[int, int, int],
    *,
    draw_count: int = 64,
    other_count: int = 3,
) -> adapter.DiscoveryKnownRelationalRowV1:
    stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    descriptors = tuple(
        adapter.descriptor_from_observed_transition_v1(
            context,
            catalogue,
            action,
            stream.draw(),
        )
        for _ in range(draw_count)
    )
    counts = Counter(item.outcome_id for item in descriptors)
    representatives = {item.outcome_id: item for item in descriptors}
    known = tuple(
        adapter.DiscoveryKnownOutcomeCountV1(
            representatives[outcome_id],
            counts[outcome_id],
        )
        for outcome_id in sorted(counts)
    )
    return adapter.DiscoveryKnownRelationalRowV1(
        support_epoch_id=epoch.epoch_id,
        catalogue=catalogue,
        action=action,
        discovered_outcomes=known,
        other_count=other_count,
    )


@pytest.fixture(scope="module")
def w5_rows() -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
]:
    context, catalogue, epoch = _w5_binding()
    rows = tuple(
        _observed_proposal_row(context, catalogue, epoch, action)
        for action in catalogue.actions
    )
    return context, catalogue, rows


def test_frozen_v0066_skeleton_is_reconstructed_without_source_replay() -> None:
    skeleton = adapter.v0066_source_skeleton_v1()
    assert adapter.CONTRACT_VERSION == "1.32.0"
    assert skeleton.skeleton_id == adapter.V0066_SOURCE_SKELETON_ID
    assert (
        skeleton.source_observation_log_id
        == adapter.V0066_SOURCE_OBSERVATION_LOG_ID
    )
    assert skeleton.state_program.rendered == (
        "cardinality_actions(legal_actions)"
    )
    assert skeleton.action_program.rendered == (
        "cardinality_resources("
        "linked_filter(action_anchor,active_resources))"
    )


def test_public_w5_ir_and_programs_reproduce_expected_anonymous_coordinates(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    context, catalogue, _ = w5_rows
    profile = adapter.base_coordinate_profile_v1()
    state = adapter.relational_state_ir_v1(context, catalogue)

    assert state.structural_context_id == context.context_id
    assert state.resource_attributes == context.root_ranks
    assert state.active_resources == (0, 1, 2)
    assert len(state.linked_pairs) == 16
    assert adapter.state_coordinate_v1(profile, state) == (
        ("INTEGER", 2),
    )
    assert tuple(
        adapter.action_coordinate_v1(
            profile,
            state,
            adapter.action_slot_v1(context, catalogue, action),
        )
        for action in catalogue.actions
    ) == (
        (("INTEGER", 1),),
        (("INTEGER", 2),),
    )
    assert tuple(
        adapter.support_coordinate_v1(
            profile,
            context,
            catalogue,
            action,
        )
        for action in catalogue.actions
    ) == (
        (2, (("INTEGER", 2),), (("INTEGER", 1),)),
        (2, (("INTEGER", 2),), (("INTEGER", 2),)),
    )


def test_other_is_excluded_from_coordinate_log_and_cannot_certify(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    context, _, rows = w5_rows
    proposal = adapter.build_proposal_only_relational_observation_log_v1(
        context,
        rows,
    )

    assert type(proposal.anonymous_log) is (
        portable.AnonymousRelationalObservationLogV1
    )
    assert proposal.known_draw_count == 128
    assert proposal.excluded_other_draw_count == 6
    assert proposal.rows_with_other == 2
    assert proposal.coordinate_proposal_eligible
    assert not proposal.dynamics_certificate_eligible
    assert not proposal.plan_certificate_eligible
    assert all(
        sum(
            (outcome.probability for outcome in row.outcomes),
            Fraction(0),
        )
        == 1
        for row in proposal.anonymous_log.rows
    )
    anonymous_document = proposal.anonymous_log.to_document()
    encoded = json.dumps(anonymous_document, sort_keys=True)
    assert "OTHER" not in encoded

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(
                *(keys(item) for item in value.values())
            )
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value), set())
        return set()

    assert not {
        "other_count",
        "excluded_other_draw_count",
        "other_upper",
    } & keys(anonymous_document)
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        replace(proposal, dynamics_certificate_eligible=True)


def test_w5_degree_refinement_candidate_is_generated_from_observed_rows(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    context, _, rows = w5_rows
    proposal = adapter.build_proposal_only_relational_observation_log_v1(
        context,
        rows,
    )
    skeleton = adapter.v0066_source_skeleton_v1()
    failed = portable.FailedRelationalProofRefV1(
        target_context_id=context.context_id,
        model_epoch_id="1" * 64,
        failed_audit_id="2" * 64,
        reason="ALIAS_WIDTH",
    )
    generation = adapter.generate_proposal_only_relational_candidates_v1(
        skeleton,
        failed,
        proposal,
    )

    assert "active_attribute_degree_signature" in {
        item.rendered for item in generation.state_coordinate_candidates
    }
    assert generation.coordinate_proposal_eligible
    assert not generation.dynamics_certificate_eligible
    assert not generation.plan_certificate_eligible
    assert (
        generation.portable_generation.source_registry_access_count
        == generation.portable_generation.source_candidate_metric_access_count
        == 0
    )


def test_small_structural_row_protocol_is_copied_before_projection(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    context, _, rows = w5_rows

    @dataclass(frozen=True)
    class ExternalRow:
        support_epoch_id: str
        catalogue: observer.LegalActionCatalogueV1
        action: tuple[int, int, int]
        discovered_outcomes: tuple[
            adapter.DiscoveryKnownOutcomeCountV1,
            ...,
        ]
        other_count: int

    external = tuple(
        ExternalRow(
            row.support_epoch_id,
            row.catalogue,
            row.action,
            row.discovered_outcomes,
            row.other_count,
        )
        for row in rows
    )
    proposal = adapter.build_proposal_only_relational_observation_log_v1(
        context,
        external,
    )
    assert all(
        type(item) is adapter.DiscoveryKnownRelationalRowV1
        for item in proposal.proposal_rows
    )


def test_context_and_action_transplants_are_rejected(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    w5, _, rows = w5_rows
    k6 = observer.public_context_by_key_v1("opaque_graph_k6_v0")
    k6_catalogue = observer.legal_action_catalogue_v1(
        k6,
        observer.root_state_v1(k6),
        2,
    )
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        adapter.relational_state_ir_v1(w5, k6_catalogue)
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        adapter.build_proposal_only_relational_observation_log_v1(
            k6,
            rows,
        )
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        replace(rows[0], action=rows[1].action)
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        adapter.action_slot_v1(w5, rows[0].catalogue, (3, 4, 3))


def test_other_cannot_be_smuggled_as_a_discovered_descriptor(
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    descriptor = w5_rows[2][0].discovered_outcomes[0].descriptor
    with pytest.raises(
        adapter.ObservationSupportRelationalAdapterInvariantViolation
    ):
        replace(descriptor, outcome_kind="OTHER")


def test_operational_adapter_never_calls_legacy_contexts_or_exact_atoms(
    monkeypatch: pytest.MonkeyPatch,
    w5_rows: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[adapter.DiscoveryKnownRelationalRowV1, ...],
    ],
) -> None:
    def forbidden(*_: object, **__: object) -> object:
        raise AssertionError("forbidden legacy/exact authority was called")

    monkeypatch.setattr(
        legacy_graph,
        "portable_graph_source_skeleton_v1",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_graph,
        "registered_variable_order_contexts_v1",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_graph,
        "registered_variable_order_family_v1",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_graph.RelationalGraphMergeKernelV2,
        "atoms",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_source,
        "registered_cross_graph_contexts_v1",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_source,
        "acquire_cross_graph_source_observations_v1",
        forbidden,
    )
    monkeypatch.setattr(
        observer,
        "evaluation_exact_atoms_v1",
        forbidden,
    )
    monkeypatch.setattr(
        portable,
        "synthesize_portable_relational_skeleton_v1",
        forbidden,
    )

    context, catalogue, rows = w5_rows
    skeleton = adapter.v0066_source_skeleton_v1()
    profile = adapter.base_coordinate_profile_v1(skeleton)
    state = adapter.relational_state_ir_v1(context, catalogue)
    assert adapter.state_coordinate_v1(profile, state) == (
        ("INTEGER", 2),
    )
    proposal = adapter.build_proposal_only_relational_observation_log_v1(
        context,
        rows,
        skeleton,
    )
    assert proposal.anonymous_log.rows

    source = inspect.getsource(adapter)
    for forbidden_name in (
        "RelationalGraphMergeKernelV2",
        "evaluation_exact_atoms_v1",
        "registered_variable_order_contexts_v1",
        "acquire_cross_graph_source_observations_v1",
    ):
        assert forbidden_name not in source
