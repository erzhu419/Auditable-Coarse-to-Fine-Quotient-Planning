from __future__ import annotations

import inspect
from typing import Any

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_heldout_public_graph_adapter_v1 as adapter
from acfqp import (
    v072_heldout_public_graph_adapter_independent_verifier_v1
    as independent,
)
from acfqp import v072_synthetic_row_observation_adapter_v1 as synthetic


def _context(
    key: str,
) -> prereg.HeldoutPublicGraphContextV2:
    return next(
        item
        for item in prereg.registered_heldout_public_contexts_v2()
        if item.context_key == key
    )


def _action_triples(
    actions: tuple[cold.ColdPublicActionV1, ...],
) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        sorted(
            tuple(item.document["action"])
            for item in actions
        )
    )


@pytest.mark.parametrize(
    ("context_key", "expected_cap"),
    adapter.EXPECTED_CONTEXT_TOTAL_ROW_CAPS,
)
def test_three_clean_contexts_match_public_root_catalogues_and_ids(
    context_key: str,
    expected_cap: int,
) -> None:
    context = _context(context_key)
    public_root = observer.root_state_v2(context)
    public_catalogue = observer.legal_action_catalogue_v2(
        context,
        public_root,
        context.horizon,
    )
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )

    assert claimed.context is context
    assert claimed.context_id == context.context_id
    assert claimed.horizon == 2
    assert claimed.public_root_state == public_root
    assert (
        claimed.public_root_catalogue.to_document()
        == public_catalogue.to_document()
    )
    assert claimed.root_state.semantic_state_id == public_root.state_id
    assert claimed.root_state.document["public_state_id"] == (
        public_root.state_id
    )
    assert _action_triples(claimed.root_actions) == (
        public_catalogue.actions
    )

    by_triple = {
        tuple(item.document["action"]): item
        for item in claimed.root_actions
    }
    for action in public_catalogue.actions:
        row = observer.observation_row_binding_v2(
            context,
            public_catalogue,
            action,
        )
        cold_action = by_triple[action]
        assert cold_action.semantic_action_id == row.row_binding_id
        assert cold_action.document["public_row_binding_id"] == (
            row.row_binding_id
        )
        assert cold_action.document["public_catalogue_id"] == (
            public_catalogue.catalogue_id
        )

    assert claimed.context_specific_total_row_cap == expected_cap
    assert (
        claimed.context_specific_total_row_cap_key
        == claimed.total_row_cap_binding_v1
        .context_specific_total_row_cap_key
    )
    assert (
        claimed.total_row_cap_binding_v1.total_physical_row_cap
        == expected_cap
    )
    assert (
        claimed.total_row_cap_binding_v1.authority_class
        == "CONFIRMATORY_REGISTERED_PUBLIC_ONLY"
    )
    assert claimed.total_row_cap_binding_v1.preregistration_binding == {
        "kind": "NOT_FINALIZED_PUBLIC_ONLY",
        "final_preregistration_id": None,
    }
    assert (
        claimed.root_catalogue_v1().actions == claimed.root_actions
    )
    registered_cap = next(
        item
        for item in cold.registered_confirmatory_cold_h2_cap_registry_v1()
        .context_cap_evidence
        if item.context_id == context.context_id
    )
    assert cold.bind_cold_h2_total_row_cap_protocol_v1(
        claimed.total_row_cap_binding_v1
    ) == registered_cap

    proof = (
        independent
        .independently_verify_heldout_public_graph_adapter_v1(
            claimed
        )
    )
    assert proof.context_id == context.context_id
    assert proof.adapter_id == claimed.adapter_id
    assert proof.public_root_state_id == public_root.state_id
    assert proof.public_root_catalogue_id == (
        public_catalogue.catalogue_id
    )
    assert proof.hidden_law_queries == 0
    assert proof.kernel_calls == 0
    assert proof.registered_observations_generated == 0
    assert (
        independent.independently_verify_cold_public_catalogue_v1(
            claimed,
            claimed.root_catalogue_v1(),
        )
        == claimed.root_catalogue_v1().catalogue_id
    )


@pytest.mark.parametrize(
    "context_key",
    tuple(key for key, _ in adapter.EXPECTED_CONTEXT_TOTAL_ROW_CAPS),
)
def test_permuted_public_states_remain_deterministic_and_canonical(
    context_key: str,
) -> None:
    context = _context(context_key)
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    first_public = observer.HeldoutSymbolicGraphStateV2(
        (1, 1, 2, 2, 3, 3, 4),
        False,
    )
    permuted_public = observer.HeldoutSymbolicGraphStateV2(
        (2, 1, 1, 2, 3, 3, 4),
        False,
    )
    first = claimed.adapt_public_state_v1(first_public, 1)
    permuted = claimed.adapt_public_state_v1(permuted_public, 1)

    assert claimed.canonical_state_v1(first) == first
    assert claimed.canonical_state_v1(permuted) == permuted
    assert first.semantic_state_id == first_public.state_id
    assert permuted.semantic_state_id == permuted_public.state_id
    assert first.semantic_state_id != permuted.semantic_state_id
    assert first.state_record_id != permuted.state_record_id

    expected_first = observer.legal_action_catalogue_v2(
        context,
        first_public,
        1,
    )
    expected_permuted = observer.legal_action_catalogue_v2(
        context,
        permuted_public,
        1,
    )
    first_actions = claimed.legal_actions_v1(first, 1)
    permuted_actions = claimed.legal_actions_v1(permuted, 1)
    assert _action_triples(first_actions) == expected_first.actions
    assert (
        _action_triples(permuted_actions)
        == expected_permuted.actions
    )

    first_catalogue = cold.ColdPublicCatalogueV1(
        context.context_id,
        first,
        1,
        first_actions,
    )
    assert independent.independently_verify_cold_public_catalogue_v1(
        claimed,
        first_catalogue,
    ) == first_catalogue.catalogue_id


def test_canonical_state_rejects_semantic_id_or_document_substitution() -> None:
    context = _context("heldout_graph_k7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    root = claimed.root_state_v1()
    wrong_document = dict(root.document)
    wrong_document["ranks"] = [1, 2, 1, 0, 0, 0, 0]
    forged = cold.ColdPublicStateV1(
        root.semantic_state_id,
        wrong_document,
    )
    with pytest.raises(
        adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
        match="caller-supplied or stale",
    ):
        claimed.canonical_state_v1(forged)

    with pytest.raises(
        adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
        match="failure flag",
    ):
        claimed.adapt_public_state_v1(
            observer.HeldoutSymbolicGraphStateV2(
                (1, 2, 3, 4, 5, 6, 0),
                False,
            ),
            1,
        )


def _forged_reordered_catalogue(
    source: observer.HeldoutLegalActionCatalogueV2,
) -> observer.HeldoutLegalActionCatalogueV2:
    forged = object.__new__(observer.HeldoutLegalActionCatalogueV2)
    object.__setattr__(forged, "context_id", source.context_id)
    object.__setattr__(forged, "state", source.state)
    object.__setattr__(
        forged,
        "remaining_horizon",
        source.remaining_horizon,
    )
    object.__setattr__(
        forged,
        "actions",
        tuple(reversed(source.actions)),
    )
    return forged


def test_missing_extra_and_reordered_public_actions_fail_closed() -> None:
    context = _context("heldout_graph_k7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    source = observer.legal_action_catalogue_v2(
        context,
        observer.root_state_v2(context),
        2,
    )
    missing = observer.HeldoutLegalActionCatalogueV2(
        source.context_id,
        source.state,
        source.remaining_horizon,
        source.actions[:-1],
    )
    extra = observer.HeldoutLegalActionCatalogueV2(
        source.context_id,
        source.state,
        source.remaining_horizon,
        tuple(sorted((*source.actions, (0, 2, 0)))),
    )
    reordered = _forged_reordered_catalogue(source)

    for attacked in (missing, extra, reordered):
        with pytest.raises(
            adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
            match="omits, adds, or reorders",
        ):
            claimed.adapt_public_legal_action_catalogue_v1(attacked)


def test_foreign_retired_synthetic_and_duck_contexts_are_rejected() -> None:
    k7 = _context("heldout_graph_k7_confirmatory_v1")
    w7 = _context("heldout_graph_w7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(k7)
    foreign = observer.legal_action_catalogue_v2(
        w7,
        observer.root_state_v2(w7),
        2,
    )
    with pytest.raises(
        adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
        match="for this context",
    ):
        claimed.adapt_public_legal_action_catalogue_v1(foreign)

    for attacked_context in (
        prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS[0],
        synthetic.DevelopmentSyntheticPhysicalRowV2(),
        type(
            "DuckContext",
            (),
            {
                "context_id": k7.context_id,
                "context_key": k7.context_key,
                "topology": k7.topology,
                "root_ranks": k7.root_ranks,
                "horizon": 2,
            },
        )(),
    ):
        with pytest.raises(
            adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
            match="exact clean registered public context",
        ):
            adapter.registered_heldout_public_graph_adapter_v1(
                attacked_context  # type: ignore[arg-type]
            )


def test_caller_topology_action_ids_and_mapping_are_not_api_inputs() -> None:
    context = _context("heldout_graph_k7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    factory_parameters = inspect.signature(
        adapter.registered_heldout_public_graph_adapter_v1
    ).parameters
    assert tuple(factory_parameters) == ("context",)
    assert "topology" not in factory_parameters
    assert "context_id" not in factory_parameters
    assert "action_mapping" not in factory_parameters

    with pytest.raises(TypeError):
        adapter.registered_heldout_public_graph_adapter_v1(
            context,
            topology=context.topology,  # type: ignore[call-arg]
        )
    with pytest.raises(TypeError):
        claimed.legal_actions_v1(
            claimed.root_state,
            2,
            action_mapping={},  # type: ignore[call-arg]
        )
    with pytest.raises(
        adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
        match="cap binding changed",
    ):
        adapter.HeldoutPublicTotalRowCapBindingV1(
            context.context_id,
            context.context_key,
            96,
            "a" * 64,
        )


def test_independent_verifier_does_not_call_production_adapter_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context("heldout_graph_w7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    catalogue = claimed.root_catalogue_v1()

    def bomb(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("production adapter method was called")

    for name in (
        "root_state_v1",
        "root_catalogue_v1",
        "adapt_public_state_v1",
        "canonical_state_v1",
        "legal_actions_v1",
        "adapt_public_legal_action_catalogue_v1",
        "to_document",
    ):
        monkeypatch.setattr(
            adapter.HeldoutPublicGraphColdClosureAdapterV1,
            name,
            bomb,
        )
    monkeypatch.setattr(
        adapter.HeldoutPublicGraphColdClosureAdapterV1,
        "adapter_id",
        property(bomb),
    )

    proof = (
        independent
        .independently_verify_heldout_public_graph_adapter_v1(
            claimed
        )
    )
    assert proof.context_id == context.context_id
    assert independent.independently_verify_cold_public_catalogue_v1(
        claimed,
        catalogue,
    ) == catalogue.catalogue_id


def test_independent_verifier_rejects_duck_and_reordered_frozen_actions() -> None:
    context = _context("heldout_graph_k7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    with pytest.raises(
        independent
        .V072HeldoutPublicGraphAdapterIndependentVerificationFailure,
        match="duck-typed",
    ):
        independent.independently_verify_heldout_public_graph_adapter_v1(
            type(
                "DuckAdapter",
                (),
                {
                    "context": claimed.context,
                    "root_state": claimed.root_state,
                    "root_actions": claimed.root_actions,
                    "adapter_id": claimed.adapter_id,
                },
            )()  # type: ignore[arg-type]
        )

    attacked = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    object.__setattr__(
        attacked,
        "root_actions",
        tuple(reversed(attacked.root_actions)),
    )
    with pytest.raises(
        independent
        .V072HeldoutPublicGraphAdapterIndependentVerificationFailure,
        match="reordered",
    ):
        independent.independently_verify_heldout_public_graph_adapter_v1(
            attacked
        )


def test_hidden_law_kernel_and_observer_builder_apis_are_never_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context("heldout_graph_k7_minus_two_confirmatory_v1")

    def bomb(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        raise AssertionError("non-public authority was called")

    for owner, name in (
        (
            prereg,
            "freeze_transfer_guided_acquisition_preregistration_v1",
        ),
        (prereg, "frozen_heldout_environment_manifest_v1"),
        (observer, "root_state_v2"),
        (observer, "legal_action_catalogue_v2"),
        (observer, "observation_row_binding_v2"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (observer, "evaluation_only_exact_atoms_v2"),
    ):
        monkeypatch.setattr(owner, name, bomb)

    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    assert claimed.context_id == context.context_id
    assert len(claimed.root_actions) == 2
    proof = (
        independent
        .independently_verify_heldout_public_graph_adapter_v1(
            claimed
        )
    )
    assert proof.hidden_law_queries == 0
    assert proof.kernel_calls == 0
    assert proof.outcome_enumeration_calls == 0


def test_row_outcome_and_registered_observation_boundaries_are_locked() -> None:
    context = _context("heldout_graph_k7_confirmatory_v1")
    claimed = adapter.registered_heldout_public_graph_adapter_v1(
        context
    )
    for entry in (
        claimed.adapt_row_evidence_v1,
        claimed.adapt_outcome_descriptor_v1,
        claimed.adapt_registered_observation_v1,
    ):
        with pytest.raises(
            adapter.V072HeldoutPublicGraphAdapterInvariantViolation,
            match="locked",
        ):
            entry(object())

    document = claimed.to_document()
    assert document["final_preregistration_id"] is None
    assert document["target_execution_anchor_id"] is None
    assert document["target_execution_allowed"] is False
    assert document["registered_observations_generated"] == 0
    assert document["outcome_enumeration_calls"] == 0
    assert document["hidden_law_queries"] == 0
    source = inspect.getsource(adapter)
    assert "RecordedTransitionDescriptorV2" not in source
