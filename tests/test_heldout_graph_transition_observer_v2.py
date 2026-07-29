from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib

import pytest

import acfqp.heldout_graph_transition_observer_v2 as observer
import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg
import acfqp.v072_development_synthetic_transition_control_v1 as synthetic


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture
def contexts() -> tuple[prereg.HeldoutPublicGraphContextV2, ...]:
    return prereg.registered_heldout_public_contexts_v2()


@pytest.fixture
def placeholder() -> observer.TargetExecutionAnchorPlaceholderV1:
    return observer.bind_target_execution_anchor_placeholder_v1(
        prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
        remote_main_commit_sha="1" * 40,
        remote_main_containment_attestation_id=_id(
            "development-placeholder-not-a-verified-remote-authority"
        ),
    )


def _row(
    context: prereg.HeldoutPublicGraphContextV2,
    action_index: int = 0,
) -> tuple[
    observer.HeldoutLegalActionCatalogueV2,
    observer.HeldoutObservationRowBindingV2,
]:
    state = observer.root_state_v2(context)
    catalogue = observer.legal_action_catalogue_v2(
        context,
        state,
        prereg.HORIZON,
    )
    binding = observer.observation_row_binding_v2(
        context,
        catalogue,
        catalogue.actions[action_index],
    )
    return catalogue, binding


def _chain(
    context: prereg.HeldoutPublicGraphContextV2,
    row: observer.HeldoutObservationRowBindingV2,
    arm: str,
    leaf_index: int,
) -> observer.HeldoutSupportEpochChainV2:
    bootstrap = observer.support_epoch_identity_v2(
        context,
        row,
        arm,
        0,
    )
    epochs = [bootstrap]
    if leaf_index >= 1:
        initial = observer.support_epoch_identity_v2(
            context,
            row,
            arm,
            1,
            tuple(sorted((_id("support-a"), _id("support-b")))),
            bootstrap,
        )
        epochs.append(initial)
    if leaf_index >= 2:
        promoted = observer.support_epoch_identity_v2(
            context,
            row,
            arm,
            2,
            tuple(
                sorted(
                    (
                        _id("support-a"),
                        _id("support-b"),
                        _id("novel-support-c"),
                    )
                )
            ),
            epochs[-1],
        )
        epochs.append(promoted)
    if leaf_index == 3:
        promoted_again = observer.support_epoch_identity_v2(
            context,
            row,
            arm,
            3,
            tuple(
                sorted(
                    (
                        _id("support-a"),
                        _id("support-b"),
                        _id("novel-support-c"),
                        _id("novel-support-d"),
                    )
                )
            ),
            epochs[-1],
        )
        epochs.append(promoted_again)
    return observer.support_epoch_chain_v2(
        context,
        row,
        arm,
        tuple(epochs),
    )


def test_registered_observer_is_isolated_and_gate_not_run() -> None:
    assert observer.PROPOSED_CONTRACT_VERSION == "1.36.0"
    assert observer.SAMPLE_EFFICIENCY_GATE_STATUS == "NOT_RUN"
    assert observer.OFFICIAL_EXECUTION_ALLOWED is False
    assert observer.EXACT_IID_IMPLEMENTATION_CLAIMED is False
    assert observer.PROFILE_KEY != "opaque_graph_transition_observer_v0"
    assert set(observer.DOMAIN_TAGS.values()).isdisjoint(
        synthetic.DOMAIN_TAGS.values()
    )


def test_registered_public_contexts_have_no_law_and_complete_root_actions(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    for context in contexts:
        public = context.to_document()
        assert "rank_probabilities" not in public
        assert "spawn" not in repr(public).lower()
        catalogue, _ = _row(context)
        assert catalogue.actions == ((0, 1, 0), (0, 1, 1))
        assert catalogue.to_document()["complete_exact_legal_action_catalogue"]


def test_complete_actions_follow_each_registered_topology(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    state = observer.HeldoutSymbolicGraphStateV2(
        (1, 1, 2, 2, 1, 1, 0)
    )
    for context in contexts:
        catalogue = observer.legal_action_catalogue_v2(
            context,
            state,
            1,
        )
        expected = tuple(
            sorted(
                (first, second, survivor)
                for first, second in context.topology.edges
                if state.ranks[first] > 0
                and state.ranks[first] == state.ranks[second]
                for survivor in (first, second)
            )
        )
        assert catalogue.actions == expected


def test_placeholder_is_content_addressed_but_explicitly_nonauthorizing(
    placeholder: observer.TargetExecutionAnchorPlaceholderV1,
) -> None:
    frozen = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    document = placeholder.to_document()
    assert placeholder.preregistration_id == frozen.preregistration_id
    assert placeholder.anchor_id != frozen.preregistration_id
    assert document["authorizes_registered_target_execution"] is False
    assert document["future_verified_remote_main_anchor_required"] is True
    assert document["sample_efficiency_gate_status"] == "NOT_RUN"

    for invalid_commit in (
        "not-a-remote-commit",
        "a" * 39,
        "A" * 40,
        "g" * 40,
        "a" * 41,
    ):
        with pytest.raises(
            observer.HeldoutGraphTransitionObserverV2InvariantViolation
        ):
            observer.bind_target_execution_anchor_placeholder_v1(
                frozen,
                remote_main_commit_sha=invalid_commit,
                remote_main_containment_attestation_id=_id(
                    "invalid-placeholder"
                ),
            )


@pytest.mark.parametrize("leaf_index", (0, 1, 2, 3))
def test_placeholder_cannot_open_any_registered_stream_stage(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
    placeholder: observer.TargetExecutionAnchorPlaceholderV1,
    monkeypatch: pytest.MonkeyPatch,
    leaf_index: int,
) -> None:
    context = contexts[0]
    catalogue, row = _row(context)
    chain = _chain(
        context,
        row,
        "SOURCE_CONSENSUS_PRIOR",
        leaf_index,
    )
    constructor_called = False
    original = observer.AnchorGatedHeldoutTransitionStreamV2

    def forbidden_constructor(*args: object, **kwargs: object) -> object:
        nonlocal constructor_called
        constructor_called = True
        return original(*args, **kwargs)

    monkeypatch.setattr(
        observer,
        "AnchorGatedHeldoutTransitionStreamV2",
        forbidden_constructor,
    )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="placeholder is nonauthorizing",
    ):
        observer.open_heldout_target_transition_stream_v2(
            placeholder,
            context,
            catalogue,
            catalogue.actions[0],
            "SOURCE_CONSENSUS_PRIOR",
            chain.leaf.required_lane,
            chain,
        )
    assert constructor_called is False


def test_support_chain_allows_exactly_two_promotions_after_initial_validation(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[0]
    _, row = _row(context)
    chain = _chain(context, row, "NO_PRIOR", 3)
    assert tuple(epoch.epoch_index for epoch in chain.epochs) == (0, 1, 2, 3)
    assert tuple(epoch.observer_stage for epoch in chain.epochs) == (
        "BOOTSTRAP_DISCOVERY",
        "INITIAL_VALIDATION",
        "PROMOTED_VALIDATION",
        "PROMOTED_VALIDATION",
    )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation
    ):
        observer.support_epoch_identity_v2(
            context,
            row,
            "NO_PRIOR",
            4,
            tuple(
                sorted(
                    (
                        _id("support-a"),
                        _id("support-b"),
                        _id("novel-support-c"),
                        _id("novel-support-d"),
                        _id("novel-support-e"),
                    )
                )
            ),
            chain.leaf,
        )


def test_placeholder_cannot_build_pair_or_reveal_registered_exact_atoms(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
    placeholder: observer.TargetExecutionAnchorPlaceholderV1,
) -> None:
    context = contexts[1]
    catalogue, row = _row(context)
    chain = _chain(context, row, "NO_PRIOR", 0)
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="placeholder is nonauthorizing",
    ):
        observer.arm_isolated_stream_pair_identity_v2(
            placeholder,
            context,
            catalogue,
            catalogue.actions[0],
            "NO_PRIOR",
            chain,
        )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="placeholder is nonauthorizing",
    ):
        observer.evaluation_only_exact_atoms_v2(
            placeholder,
            context,
            catalogue,
            catalogue.actions[0],
        )


def test_row_bindings_separate_actions_and_support_member_cap_is_not_campaign_cap(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[0]
    catalogue, first_row = _row(context, 0)
    _, second_row = _row(context, 1)
    assert first_row.row_binding_id != second_row.row_binding_id
    assert observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2 == 16
    assert context.maximum_physical_rows_per_confidence_epoch == 96

    bootstrap = _chain(
        context,
        first_row,
        "SOURCE_CONSENSUS_PRIOR",
        0,
    ).leaf
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation
    ):
        observer.support_epoch_identity_v2(
            context,
            first_row,
            "SOURCE_CONSENSUS_PRIOR",
            1,
            tuple(
                sorted(
                    _id(f"member-{index}")
                    for index in range(
                        observer.MAX_FROZEN_SUPPORT_MEMBERS_PER_ROW_V2 + 1
                    )
                )
            ),
            bootstrap,
        )
    assert catalogue.actions[0] == first_row.action


def test_support_chain_freezes_members_and_exact_three_stage_chronology(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[0]
    _, row = _row(context)
    promoted = _chain(
        context,
        row,
        "SOURCE_CONSENSUS_PRIOR",
        2,
    )
    assert tuple(epoch.epoch_index for epoch in promoted.epochs) == (0, 1, 2)
    assert tuple(epoch.observer_stage for epoch in promoted.epochs) == (
        "BOOTSTRAP_DISCOVERY",
        "INITIAL_VALIDATION",
        "PROMOTED_VALIDATION",
    )
    assert promoted.epochs[0].frozen_support_member_ids == ()
    assert promoted.epochs[1].frozen_support_member_count == 2
    assert promoted.epochs[2].frozen_support_member_count == 3
    assert promoted.leaf.required_lane is observer.ObservationLaneV2.VALIDATION
    assert promoted.to_document()["complete_bootstrap_to_leaf_chain"] is True
    assert (
        observer.verify_heldout_support_epoch_chain_v2(
            context,
            row,
            "SOURCE_CONSENSUS_PRIOR",
            promoted,
        )
        == promoted
    )


def test_support_ids_are_arm_disjoint_while_pairing_lineage_is_arm_free(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[2]
    _, row = _row(context)
    source = _chain(
        context,
        row,
        "SOURCE_CONSENSUS_PRIOR",
        2,
    )
    direct = _chain(
        context,
        row,
        "MATCHED_DIRECT_GROUND",
        2,
    )
    assert source.chain_id != direct.chain_id
    assert tuple(epoch.epoch_id for epoch in source.epochs) != tuple(
        epoch.epoch_id for epoch in direct.epochs
    )
    assert tuple(
        epoch.frozen_support_set_id for epoch in source.epochs
    ) != tuple(epoch.frozen_support_set_id for epoch in direct.epochs)
    assert tuple(
        epoch.arm_free_pairing_lineage_id for epoch in source.epochs
    ) == tuple(
        epoch.arm_free_pairing_lineage_id for epoch in direct.epochs
    )


def test_replacement_cannot_resign_support_or_pairing_commitments(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[0]
    _, row = _row(context)
    chain = _chain(
        context,
        row,
        "SOURCE_CONSENSUS_PRIOR",
        1,
    )
    leaf = chain.leaf
    for changes in (
        {"frozen_support_set_id": _id("forged-support-set")},
        {
            "arm_free_pairing_support_set_id": _id(
                "forged-pairing-support"
            )
        },
        {
            "arm_free_pairing_lineage_id": _id(
                "forged-pairing-lineage"
            )
        },
        {
            "parent_arm_free_pairing_lineage_id": _id(
                "forged-parent-pairing-lineage"
            )
        },
    ):
        with pytest.raises(
            observer.HeldoutGraphTransitionObserverV2InvariantViolation,
            match="commitments do not recompute",
        ):
            replace(leaf, **changes)


def test_full_chain_rejects_foreign_parent_skipped_parent_and_cross_row_reuse(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    context = contexts[0]
    _, row = _row(context, 0)
    _, other_row = _row(context, 1)
    chain = _chain(
        context,
        row,
        "SOURCE_CONSENSUS_PRIOR",
        2,
    )
    bootstrap, initial, promoted = chain.epochs

    forged_parent = replace(
        initial,
        parent_epoch_id=_id("coherently-resigned-foreign-parent"),
    )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="forged or skipped parent",
    ):
        observer.support_epoch_chain_v2(
            context,
            row,
            "SOURCE_CONSENSUS_PRIOR",
            (bootstrap, forged_parent),
        )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="index mismatch",
    ):
        observer.support_epoch_chain_v2(
            context,
            row,
            "SOURCE_CONSENSUS_PRIOR",
            (bootstrap, promoted),
        )
    with pytest.raises(
        observer.HeldoutGraphTransitionObserverV2InvariantViolation,
        match="row",
    ):
        observer.support_epoch_chain_v2(
            context,
            other_row,
            "SOURCE_CONSENSUS_PRIOR",
            chain.epochs,
        )


def test_registered_target_preanchor_fixture_generated_no_observation_artifact(
    contexts: tuple[prereg.HeldoutPublicGraphContextV2, ...],
) -> None:
    # This test suite constructs public catalogues and support identities only.
    # Positive execution lives in the domain-separated synthetic-control suite.
    assert all(
        context.to_document()["target_execution_allowed"] is False
        for context in contexts
    )
    assert (
        prereg.frozen_heldout_environment_manifest_v1()
        .target_observations_generated
        == 0
    )
