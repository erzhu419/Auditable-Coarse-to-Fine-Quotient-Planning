from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect

import pytest

import acfqp.observation_support_h2_closure_v1 as closure
import acfqp.transition_tuple_observer_v1 as observer


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def w5_closure() -> closure.ObservationSupportH2ClosureV1:
    closure.clear_observation_support_h2_closure_cache_v1()
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    return closure.acquire_observation_support_h2_closure_v1(
        context,
        2_048,
        max_workers=16,
    )


def test_profile_and_typed_identity_are_frozen(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    assert closure.CONTRACT_VERSION == "1.32.0"
    assert closure.PROFILE_KEY == "observation_support_h2_closure_v0"
    assert w5_closure.observation_only
    assert w5_closure.current_support_epoch_index == 1
    assert not w5_closure.validation_novel_child_expansion_allowed
    assert w5_closure.route_independent_physical_evidence
    assert w5_closure.physical_bundle_id == w5_closure.closure_id
    assert len(w5_closure.closure_id) == 64
    document = w5_closure.to_document()
    assert document["closure_id"] == w5_closure.closure_id
    assert document["child_discovery_rule"] == closure.CHILD_DISCOVERY_RULE
    assert document["validation_novel_rule"] == closure.VALIDATION_NOVEL_RULE


def test_root_and_discovery_known_child_closure_are_complete(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    assert len(w5_closure.root_rows) == len(
        w5_closure.root_catalogue.actions
    )
    assert {
        (row.binding.catalogue_id, row.binding.action)
        for row in w5_closure.root_rows
    } == {
        (w5_closure.root_catalogue.catalogue_id, action)
        for action in w5_closure.root_catalogue.actions
    }
    expected_state_ids = {
        descriptor.next_state.state_id
        for row in w5_closure.root_rows
        for descriptor in row.support_descriptors
        if not descriptor.failure and not descriptor.terminal
    }
    assert {
        item.state.state_id for item in w5_closure.child_catalogues
    } == expected_state_ids
    assert {
        (row.binding.catalogue_id, row.binding.action)
        for row in w5_closure.child_rows
    } == {
        (catalogue.catalogue_id, action)
        for catalogue in w5_closure.child_catalogues
        for action in catalogue.actions
    }
    assert all(
        row.binding.remaining_horizon == 2
        for row in w5_closure.root_rows
    )
    assert all(
        row.binding.remaining_horizon == 1
        for row in w5_closure.child_rows
    )


def test_validation_novel_outcomes_do_not_expand_current_epoch(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    discovery_states = {
        descriptor.next_state.state_id
        for row in w5_closure.root_rows
        for descriptor in row.support_descriptors
        if not descriptor.failure and not descriptor.terminal
    }
    novel_states = {
        descriptor.next_state.state_id
        for row in w5_closure.root_rows
        for descriptor in row.novel_descriptors
        if not descriptor.failure and not descriptor.terminal
    }
    child_states = {
        catalogue.state.state_id
        for catalogue in w5_closure.child_catalogues
    }
    assert child_states == discovery_states
    assert novel_states
    assert novel_states - child_states
    assert w5_closure.counters.validation_novel_descriptor_count > 0
    assert w5_closure.counters.validation_novel_child_expansions == 0


def test_native_row_counters_reconcile_exactly(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    counters = w5_closure.counters
    rows = w5_closure.all_rows
    assert counters.total_action_row_count == len(rows)
    assert counters.root_action_row_count == len(w5_closure.root_rows)
    assert counters.child_action_row_count == len(w5_closure.child_rows)
    assert counters.initial_discovery_draws == 64 * len(rows)
    assert counters.prior_validation_draws == 0
    assert counters.current_validation_draws == 2_048 * len(rows)
    assert counters.total_observer_draws == sum(
        row.counters.total_observer_draws for row in rows
    )
    assert counters.total_random_word_calls == sum(
        row.counters.total_random_word_calls for row in rows
    )
    assert counters.total_rejections == sum(
        row.counters.total_rejections for row in rows
    )
    assert counters.total_random_word_calls == (
        counters.total_observer_draws + counters.total_rejections
    )
    assert len(w5_closure.physical_evidence_ids) == len(rows)


def test_parallelism_is_not_part_of_physical_identity(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    serial_consumer = closure.acquire_observation_support_h2_closure_v1(
        context,
        2_048,
        max_workers=1,
    )
    assert serial_consumer is w5_closure
    assert serial_consumer.closure_id == w5_closure.closure_id
    assert serial_consumer.counters == w5_closure.counters
    assert "max_workers" not in w5_closure.to_document()


def test_direct_and_quotient_have_distinct_logical_charges_over_one_bundle(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    direct = closure.charge_direct_observation_support_h2_closure_v1(
        w5_closure,
        _id("direct H2 consumer"),
    )
    quotient = closure.charge_quotient_observation_support_h2_closure_v1(
        w5_closure,
        _id("quotient H2 consumer"),
    )
    assert direct.route is closure.ObservationSupportH2ClosureRoute.DIRECT
    assert (
        quotient.route
        is closure.ObservationSupportH2ClosureRoute.QUOTIENT
    )
    assert direct.charge_id != quotient.charge_id
    assert direct.closure_id == quotient.closure_id == w5_closure.closure_id
    assert (
        direct.physical_bundle_id
        == quotient.physical_bundle_id
        == w5_closure.physical_bundle_id
    )
    assert (
        direct.physical_evidence_ids
        == quotient.physical_evidence_ids
        == w5_closure.physical_evidence_ids
    )
    assert direct.counters == quotient.counters == w5_closure.counters


def test_semantic_replay_regenerates_every_raw_prefix(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    replay = closure.verify_observation_support_h2_closure_v1(
        w5_closure.context,
        w5_closure,
        max_workers=8,
    )
    assert replay.closure_id == w5_closure.closure_id
    assert len(replay.row_replay_bindings) == len(w5_closure.all_rows)
    assert {
        item[0] for item in replay.row_replay_bindings
    } == {
        item.partial_row_id for item in w5_closure.all_rows
    }
    assert (
        replay.replayed_observer_draws
        == w5_closure.counters.total_observer_draws
    )
    assert replay.exact_atom_enumerator_calls == 0
    assert not replay.exact_iid_implementation_claimed
    assert not replay.formal_exact_iid_plan_certificate
    assert not replay.independent_algorithm_implementation


def test_semantic_replay_does_not_cross_the_exact_oracle_boundary(
    w5_closure: closure.ObservationSupportH2ClosureV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("exact evaluation API entered raw-prefix replay")

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
    replay = closure.verify_observation_support_h2_closure_v1(
        w5_closure.context,
        w5_closure,
        max_workers=1,
    )
    assert replay.exact_atom_enumerator_calls == 0


def test_identity_and_closure_attacks_fail_closed(
    w5_closure: closure.ObservationSupportH2ClosureV1,
) -> None:
    with pytest.raises(
        closure.ObservationSupportH2ClosureInvariantViolation
    ):
        replace(
            w5_closure,
            child_catalogues=tuple(
                reversed(w5_closure.child_catalogues)
            ),
        )
    with pytest.raises(
        closure.ObservationSupportH2ClosureInvariantViolation
    ):
        replace(
            w5_closure,
            child_rows=w5_closure.child_rows[:-1],
        )
    with pytest.raises(
        closure.ObservationSupportH2ClosureInvariantViolation
    ):
        replace(
            w5_closure,
            counters=replace(
                w5_closure.counters,
                validation_novel_child_expansions=1,
            ),
        )
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    for checkpoint, workers in (
        (2_049, 1),
        (2_048, 0),
        (2_048, True),
        (2_048, closure.MAX_PROCESS_WORKERS + 1),
    ):
        with pytest.raises(
            closure.ObservationSupportH2ClosureInvariantViolation
        ):
            closure.acquire_observation_support_h2_closure_v1(
                context,
                checkpoint,
                workers,
            )


def test_operational_source_uses_only_observed_support_boundary() -> None:
    source = inspect.getsource(closure)
    prohibited = (
        "evaluation_" + "exact",
        "_HIDDEN" + "_SPAWN",
        ".at" + "oms(",
    )
    assert all(token not in source for token in prohibited)
    assert "support_descriptors" in source
    assert "novel_descriptors" in source
    assert "ProcessPoolExecutor" in source
