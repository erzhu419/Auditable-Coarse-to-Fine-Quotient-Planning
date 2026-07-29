from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.observation_support_graph_acquisition_v1 as acquisition
import acfqp.partial_support_confidence_v1 as confidence
import acfqp.transition_tuple_observer_v1 as observer
import acfqp.variable_order_graph_rapm_v1 as legacy_graph


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def binding() -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    tuple[int, int, int],
]:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    state = observer.root_state_v1(context)
    catalogue = observer.legal_action_catalogue_v1(context, state, 2)
    return context, catalogue, catalogue.actions[0]


@pytest.fixture(scope="module")
def initial_row(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
) -> acquisition.GraphPartialSupportRowV1:
    context, catalogue, action = binding
    acquisition.acquire_graph_partial_support_row_v1.cache_clear()
    return acquisition.acquire_graph_partial_support_row_v1(
        context,
        catalogue,
        action,
        2_048,
    )


@pytest.fixture(scope="module")
def promoted_row(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> acquisition.GraphPartialSupportRowV1:
    context, catalogue, action = binding
    assert initial_row.novel_descriptors
    acquisition.promote_graph_partial_support_row_v1.cache_clear()
    return acquisition.promote_graph_partial_support_row_v1(
        initial_row,
        context,
        catalogue,
        action,
        2_048,
    )


def test_registered_split_profile_and_row_binding_are_frozen(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    context, catalogue, action = binding
    assert acquisition.CONTRACT_VERSION == "1.32.0"
    assert acquisition.DISCOVERY_DRAW_COUNT == 64
    assert acquisition.VALIDATION_CHECKPOINTS == (
        2_048,
        4_096,
        8_192,
        16_384,
    )
    assert initial_row.binding.context_id == context.context_id
    assert initial_row.binding.catalogue_id == catalogue.catalogue_id
    assert initial_row.binding.state_id == catalogue.state.state_id
    assert initial_row.binding.action == action
    assert initial_row.binding.remaining_horizon == 2
    changed_action = replace(
        initial_row.binding,
        action=catalogue.actions[1],
    )
    changed_horizon = replace(
        initial_row.binding,
        remaining_horizon=1,
    )
    assert changed_action.row_id != initial_row.binding.row_id
    assert changed_horizon.row_id != initial_row.binding.row_id


def test_outcome_identity_hashes_joint_tuple_not_sample_identity(
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    descriptor = initial_row.support_descriptors[0]
    replayed = acquisition.GraphObservedOutcomeDescriptorV1(
        descriptor.next_state,
        descriptor.realized_row_reward,
        descriptor.failure,
        descriptor.terminal,
    )
    assert replayed == descriptor
    assert replayed.outcome_id == descriptor.outcome_id
    assert {
        item.name
        for item in fields(acquisition.GraphObservedOutcomeDescriptorV1)
    } == {
        "next_state",
        "realized_row_reward",
        "failure",
        "terminal",
    }
    document = descriptor.to_document()
    assert "sample_id" not in document
    assert "observation_id" not in document
    assert "raw_commitment" not in document
    changed = replace(
        descriptor,
        realized_row_reward=(
            descriptor.realized_row_reward + Fraction(1, 128)
        ),
    )
    assert changed.outcome_id != descriptor.outcome_id


def test_initial_row_has_split_authority_mapping_and_one_other(
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    assert initial_row.support_epoch_index == 1
    assert len(initial_row.observer_epoch_chain) == 2
    assert tuple(
        item.epoch_index for item in initial_row.observer_epoch_chain
    ) == (0, 1)
    assert initial_row.support_epoch.support_epoch_index == 1
    assert (
        initial_row.confidence_authority.support_epoch
        == initial_row.support_epoch
    )
    assert tuple(
        item.outcome_id for item in initial_row.support_descriptors
    ) == initial_row.support_epoch.support_outcome_ids
    assert tuple(
        item.outcome_id for item in initial_row.novel_descriptors
    ) == initial_row.confidence_authority.novel_outcome_ids
    other_rows = tuple(
        item
        for item in initial_row.confidence_authority.event_intervals
        if item.event_kind is confidence.PartialSupportEventKind.OTHER
    )
    assert other_rows == (initial_row.other_interval,)
    assert (
        initial_row.confidence_authority.joint_simplex.other_coordinate_count
        == 1
    )
    assert (
        0
        < initial_row.other_interval.success_count
        < initial_row.counters.current_validation_draws
    )
    assert initial_row.novel_descriptors


def test_other_interval_remains_nonzero_even_after_zero_novel_count(
    initial_row: acquisition.GraphPartialSupportRowV1,
    promoted_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    assert initial_row.other_interval.upper_probability > 0
    assert promoted_row.other_interval.success_count == 0
    assert promoted_row.novel_descriptors == ()
    assert promoted_row.other_interval.lower_probability == 0
    assert promoted_row.other_interval.upper_probability > 0
    assert (
        promoted_row.confidence_authority.joint_simplex.other_upper_probability
        == promoted_row.other_interval.upper_probability
    )


def test_initial_native_draw_and_random_word_accounting_reconciles(
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    counters = initial_row.counters
    assert counters.support_epoch_index == 1
    assert counters.initial_discovery_draws == 64
    assert counters.prior_validation_draws == 0
    assert counters.current_validation_draws == 2_048
    assert counters.total_observer_draws == 2_112
    assert (
        len(initial_row.initial_discovery_observation_ids) == 64
    )
    assert initial_row.prior_validation_observation_ids == ()
    assert (
        len(initial_row.current_validation_observation_ids) == 2_048
    )
    assert (
        counters.total_random_word_calls
        == counters.total_observer_draws + counters.total_rejections
    )


def test_epoch_two_promotes_novel_support_but_quarantines_parent_samples(
    initial_row: acquisition.GraphPartialSupportRowV1,
    promoted_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    assert promoted_row.support_epoch_index == 2
    assert promoted_row.parent_row is initial_row
    assert len(promoted_row.observer_epoch_chain) == 3
    assert (
        promoted_row.observer_epoch_chain[-1].parent_epoch_id
        == initial_row.observer_epoch_chain[-1].epoch_id
    )
    assert set(
        item.outcome_id for item in initial_row.novel_descriptors
    ).issubset(
        item.outcome_id for item in promoted_row.support_descriptors
    )
    expected_prior = (
        initial_row.prior_validation_observation_ids
        + initial_row.current_validation_observation_ids
    )
    assert promoted_row.prior_validation_observation_ids == expected_prior
    assert not set(expected_prior) & set(
        promoted_row.current_validation_observation_ids
    )
    assert set(
        promoted_row.initial_discovery_observation_ids
        + promoted_row.prior_validation_observation_ids
    ) == set(
        promoted_row.support_epoch.excluded_probability_sample_ids
    )
    assert (
        promoted_row.confidence_authority.validation_evidence.validation_stream_domain_id
        != initial_row.confidence_authority.validation_evidence.validation_stream_domain_id
    )
    assert promoted_row.counters.total_observer_draws == 4_160


def test_parent_validation_cannot_be_relabeled_as_epoch_two_probability_evidence(
    promoted_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    old = (
        promoted_row.parent_row.confidence_authority.validation_evidence.observations
    )
    relabeled = tuple(
        replace(
            item,
            stream_domain_id=(
                promoted_row.support_epoch.validation_stream_domain_id
            ),
        )
        for item in old
    )
    with pytest.raises(
        confidence.PartialSupportConfidenceInvariantViolation
    ):
        confidence.build_partial_support_confidence_v1(
            promoted_row.support_epoch,
            relabeled,
        )


def test_route_independent_cache_and_separate_logical_charges(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    context, catalogue, action = binding
    shared = acquisition.acquire_graph_partial_support_row_v1(
        context,
        catalogue,
        action,
        2_048,
    )
    assert shared is initial_row
    quotient = acquisition.charge_graph_partial_support_row_v1(
        shared,
        _id("quotient-consumer"),
    )
    direct = acquisition.charge_graph_partial_support_row_v1(
        shared,
        _id("direct-consumer"),
    )
    assert quotient.charge_id != direct.charge_id
    assert quotient.logical_consumer_id != direct.logical_consumer_id
    assert quotient.partial_row_id == direct.partial_row_id
    assert quotient.physical_evidence_id == direct.physical_evidence_id
    assert quotient.counters == direct.counters == shared.counters


def test_two_fresh_prefix_handles_are_paired_before_any_validation(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
) -> None:
    context, catalogue, action = binding
    quotient = acquisition.open_graph_partial_support_prefix_v1(
        context,
        catalogue,
        action,
    )
    direct = acquisition.open_graph_partial_support_prefix_v1(
        context,
        catalogue,
        action,
    )
    assert quotient.row_id == direct.row_id
    assert (
        quotient._discovery_observer_ids
        == direct._discovery_observer_ids
    )
    assert (
        quotient._validation_stream.stream_id
        == direct._validation_stream.stream_id
    )
    assert quotient.current_validation_draw_count == 0
    assert direct.current_validation_draw_count == 0
    with pytest.raises(
        acquisition.ObservationSupportGraphAcquisitionInvariantViolation
    ):
        quotient.extend_validation_to(64)


def test_operational_prefix_never_calls_any_exact_atom_enumerator(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, catalogue, _ = binding

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("observation-only acquisition read exact atoms")

    monkeypatch.setattr(
        observer,
        "evaluation_exact_atoms_v1",
        forbidden,
    )
    monkeypatch.setattr(
        observer,
        "evaluation_exact_ground_search_v1",
        forbidden,
    )
    monkeypatch.setattr(
        legacy_graph.RelationalGraphMergeKernelV2,
        "atoms",
        forbidden,
    )
    prefix = acquisition.open_graph_partial_support_prefix_v1(
        context,
        catalogue,
        catalogue.actions[1],
    )
    row = prefix.extend_validation_to(2_048)
    assert row.counters.total_observer_draws == 2_112
    assert row.other_interval.upper_probability > 0


def test_standalone_replay_rebuilds_observer_and_confidence_chain(
    binding: tuple[
        observer.PublicGraphContextV1,
        observer.LegalActionCatalogueV1,
        tuple[int, int, int],
    ],
    promoted_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    context, catalogue, action = binding
    verification = acquisition.verify_graph_partial_support_row_v1(
        context,
        catalogue,
        action,
        promoted_row,
    )
    assert verification.partial_row_id == promoted_row.partial_row_id
    assert (
        verification.physical_evidence_id
        == promoted_row.physical_evidence_id
    )
    assert verification.replayed_support_epoch_index == 2
    assert (
        verification.replayed_observer_draws
        == promoted_row.counters.total_observer_draws
    )
    assert (
        verification.replayed_random_word_calls
        == promoted_row.counters.total_random_word_calls
    )
    assert verification.exact_atom_enumerator_calls == 0


def test_identity_and_counter_tampering_fail_closed(
    initial_row: acquisition.GraphPartialSupportRowV1,
) -> None:
    with pytest.raises(
        acquisition.ObservationSupportGraphAcquisitionInvariantViolation
    ):
        replace(
            initial_row.counters,
            total_observer_draws=2_111,
        )
    changed_other = replace(
        initial_row.other_interval,
        event_ordinal=0,
    )
    with pytest.raises(
        acquisition.ObservationSupportGraphAcquisitionInvariantViolation
    ):
        replace(initial_row, other_interval=changed_other)
    with pytest.raises(
        acquisition.ObservationSupportGraphAcquisitionInvariantViolation
    ):
        acquisition.charge_graph_partial_support_row_v1(
            initial_row,
            "short",
        )
