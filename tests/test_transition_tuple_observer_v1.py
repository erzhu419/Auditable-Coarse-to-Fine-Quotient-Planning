from __future__ import annotations

from dataclasses import fields, replace
from fractions import Fraction
import inspect
import json

import pytest

import acfqp.transition_tuple_observer_v1 as observer
import acfqp.variable_order_graph_rapm_v1 as legacy_graph


def _binding(
    context_key: str = "opaque_graph_w5_v0",
    lane: observer.ObservationLane = observer.ObservationLane.DISCOVERY,
) -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    tuple[int, int, int],
    observer.SupportEpochIdentityV1,
    observer.ObservationLane,
]:
    context = observer.public_context_by_key_v1(context_key)
    state = observer.root_state_v1(context)
    catalogue = observer.legal_action_catalogue_v1(
        context,
        state,
        observer.REGISTERED_HORIZON,
    )
    epoch = observer.support_epoch_identity_v1(context, 0)
    return context, catalogue, catalogue.actions[0], epoch, lane


def _open(
    context_key: str = "opaque_graph_w5_v0",
    lane: observer.ObservationLane = observer.ObservationLane.DISCOVERY,
) -> tuple[
    observer.PublicGraphContextV1,
    observer.LegalActionCatalogueV1,
    tuple[int, int, int],
    observer.SupportEpochIdentityV1,
    observer.OpaqueTargetLocalTransitionStreamV1,
]:
    context, catalogue, action, epoch, selected_lane = _binding(
        context_key,
        lane,
    )
    stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        selected_lane,
        epoch,
    )
    return context, catalogue, action, epoch, stream


def _reference_uncached_draws(
    context: observer.PublicGraphContextV1,
    catalogue: observer.LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: observer.ObservationLane,
    epoch: observer.SupportEpochIdentityV1,
    draw_count: int,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    """Reproduce the pre-optimization per-draw transition computation."""

    stream_id = observer._stream_id(
        context,
        catalogue,
        action,
        lane,
        epoch,
    )
    seed = observer._stream_seed(stream_id, lane)
    accepted_draws = 0
    random_word_calls = 0
    rejection_count = 0
    documents: list[dict[str, object]] = []
    for _ in range(draw_count):
        board, empty, reward = observer._merge_row(
            context,
            catalogue.state,
            action,
        )
        law_denominator, integer_law = observer._integer_hidden_law(context)
        outcome_denominator = len(empty) * law_denominator
        acceptance_limit = (
            observer._UINT64_MODULUS
            - (observer._UINT64_MODULUS % outcome_denominator)
        )
        start = random_word_calls + 1
        words: list[int] = []
        while True:
            word_index = random_word_calls + 1
            word = observer._splitmix64(
                seed + observer._SPLITMIX_GAMMA * word_index
            )
            random_word_calls += 1
            words.append(word)
            if word >= acceptance_limit:
                rejection_count += 1
                continue
            token = word % outcome_denominator
            empty_index = token // law_denominator
            rank_token = token % law_denominator
            spawn_rank = observer._rank_from_token(
                integer_law,
                rank_token,
            )
            break
        successor = board.copy()
        successor[empty[empty_index]] = spawn_rank
        provisional = observer.SymbolicGraphStateV1(tuple(successor))
        failure = not observer._legal_actions(context, provisional)
        next_state = observer.SymbolicGraphStateV1(
            tuple(successor),
            failure,
        )
        terminal = failure or catalogue.remaining_horizon == 1
        accepted_draws += 1
        digest = observer._raw_draw_digest(
            stream_id=stream_id,
            accepted_draw_index=accepted_draws,
            random_word_start_index=start,
            next_state=next_state,
            reward=reward,
            failure=failure,
            terminal=terminal,
            words=tuple(words),
        )
        commitment = observer.RawDrawCommitmentV1(
            stream_id,
            accepted_draws,
            start,
            len(words),
            len(words) - 1,
            digest,
        )
        documents.append(
            observer.ObservedJointTransitionV1(
                context.context_id,
                catalogue.catalogue_id,
                epoch.epoch_id,
                lane,
                stream_id,
                catalogue.state,
                action,
                catalogue.remaining_horizon,
                accepted_draws,
                next_state,
                reward,
                failure,
                terminal,
                commitment,
            ).to_document()
        )
    work = observer.TransitionStreamWorkV1(
        stream_id,
        accepted_draws,
        random_word_calls,
        rejection_count,
    )
    return tuple(documents), work.to_document()


def test_contract_and_public_contexts_are_law_free() -> None:
    assert observer.CONTRACT_VERSION == "1.32.0"
    contexts = observer.registered_public_graph_contexts_v1()
    assert tuple(item.context_key for item in contexts) == (
        "opaque_graph_w5_v0",
        "opaque_graph_k6_v0",
        "opaque_graph_k6_minus_edge_v0",
    )
    assert {item.topology.vertex_count for item in contexts} == {5, 6}
    assert not observer.EXACT_IID_IMPLEMENTATION_CLAIMED
    assert (
        observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
        == "DETERMINISTIC_SPLITMIX64_COUNTER_REPLAY_BENCHMARK"
    )
    assert "NOT_PROVEN" in observer.STATISTICAL_CLAIM_SCOPE
    assert {
        item.name for item in fields(observer.PublicGraphContextV1)
    } == {
        "context_key",
        "topology",
        "root_ranks",
        "horizon",
        "risk_tolerance",
        "rank_cap",
        "reward_ceiling",
        "normalized_regret_tolerance",
    }
    for context in contexts:
        encoded = json.dumps(
            context.to_document(),
            sort_keys=True,
        ).lower()
        assert "spawn" not in encoded
        assert "probability" not in encoded
        assert "support" not in encoded
        assert '"role"' not in encoded
        assert "positive" not in encoded
        assert "negative" not in encoded
        assert context.rank_cap == 6
        assert context.reward_ceiling == Fraction(3, 64)
        assert context.normalized_regret_tolerance == Fraction(1, 20)
    assert not any(name.startswith("_HIDDEN") for name in observer.__all__)


def test_public_context_tampering_is_rejected_at_construction() -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        replace(context, risk_tolerance=Fraction(1, 19))
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        replace(context, root_ranks=(1, 1, 2, 0, 1))
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        replace(context, reward_ceiling=Fraction(1, 16))
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.public_context_by_key_v1("variable_target_w5_v0")


def test_symbolic_root_and_exact_legal_action_catalogues_are_public() -> None:
    for context in observer.registered_public_graph_contexts_v1():
        root = observer.root_state_v1(context)
        catalogue = observer.legal_action_catalogue_v1(
            context,
            root,
            2,
        )
        assert root.ranks == context.root_ranks
        assert not root.failure
        assert len(catalogue.actions) == 2
        assert catalogue.actions == tuple(sorted(set(catalogue.actions)))
        assert all(action[2] in action[:2] for action in catalogue.actions)


def test_opaque_draw_exposes_only_joint_tuple_and_commitment() -> None:
    _, _, _, _, stream = _open()
    draw = stream.draw()
    public_fields = {
        item.name for item in fields(observer.ObservedJointTransitionV1)
    }
    assert {
        "next_state",
        "realized_row_reward",
        "failure",
        "terminal",
        "raw_commitment",
    } <= public_fields
    assert not {
        "ordinal",
        "support_count",
        "atom_count",
        "atom_descriptors",
        "probability",
        "spawn_rank",
    } & public_fields
    document = draw.to_document()
    forbidden_keys = {
        "ordinal",
        "support_count",
        "atom_count",
        "atom_descriptors",
        "probability",
        "spawn_rank",
        "random_words",
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            assert not forbidden_keys & set(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(document)
    assert draw.joint_tuple == (
        draw.next_state,
        draw.realized_row_reward,
        draw.failure,
        draw.terminal,
        draw.raw_commitment,
    )
    assert draw.raw_commitment.random_word_count >= 1
    assert (
        draw.raw_commitment.random_word_count
        == draw.raw_commitment.rejection_count + 1
    )


def test_execution_only_id_memoization_is_artifact_neutral_and_clearable() -> None:
    context, catalogue, _, epoch, stream = _open()
    draw = stream.draw()
    before = (
        context.context_id,
        catalogue.catalogue_id,
        epoch.epoch_id,
        draw.next_state.state_id,
        draw.raw_commitment.commitment_id,
        draw.observation_id,
        draw.to_document(),
    )
    observer.clear_transition_tuple_observer_id_cache_v1()
    after = (
        context.context_id,
        catalogue.catalogue_id,
        epoch.epoch_id,
        draw.next_state.state_id,
        draw.raw_commitment.commitment_id,
        draw.observation_id,
        draw.to_document(),
    )
    assert after == before


@pytest.mark.parametrize(
    ("context_key", "lane"),
    tuple(
        (context_key, lane)
        for context_key in (
            "opaque_graph_w5_v0",
            "opaque_graph_k6_v0",
            "opaque_graph_k6_minus_edge_v0",
        )
        for lane in observer.ObservationLane
    ),
)
def test_stream_invariant_cache_is_byte_exact_against_uncached_reference(
    context_key: str,
    lane: observer.ObservationLane,
) -> None:
    context, catalogue, action, epoch, stream = _open(context_key, lane)
    optimized = tuple(stream.draw().to_document() for _ in range(64))
    optimized_work = stream.work_snapshot().to_document()
    observer.clear_transition_tuple_observer_id_cache_v1()
    reference, reference_work = _reference_uncached_draws(
        context,
        catalogue,
        action,
        lane,
        epoch,
        64,
    )
    assert optimized == reference
    assert optimized_work == reference_work
    observer.clear_transition_tuple_observer_id_cache_v1()
    replayed = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        lane,
        epoch,
    )
    assert (
        tuple(replayed.draw().to_document() for _ in range(64))
        == reference
    )
    assert replayed.work_snapshot().to_document() == reference_work


def test_stream_invariant_cache_computes_merge_and_law_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, catalogue, action, epoch, _ = _open("opaque_graph_k6_v0")
    merge = observer._merge_row
    law = observer._integer_hidden_law
    calls = {"merge": 0, "law": 0}

    def counted_merge(*args: object, **kwargs: object) -> object:
        calls["merge"] += 1
        return merge(*args, **kwargs)

    def counted_law(*args: object, **kwargs: object) -> object:
        calls["law"] += 1
        return law(*args, **kwargs)

    monkeypatch.setattr(observer, "_merge_row", counted_merge)
    monkeypatch.setattr(observer, "_integer_hidden_law", counted_law)
    stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    tuple(stream.draw() for _ in range(64))
    assert calls == {"merge": 1, "law": 1}


def test_paired_consumers_replay_identical_state_action_lane_epoch_streams() -> None:
    context, catalogue, action, epoch, quotient_stream = _open()
    direct_stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    assert quotient_stream.stream_id == direct_stream.stream_id
    quotient_draws = tuple(
        quotient_stream.draw().to_document() for _ in range(8)
    )
    direct_draws = tuple(
        direct_stream.draw().to_document() for _ in range(8)
    )
    assert quotient_draws == direct_draws
    assert (
        quotient_stream.work_snapshot().to_document()
        == direct_stream.work_snapshot().to_document()
    )


def test_discovery_and_validation_are_domain_separated() -> None:
    context, catalogue, action, epoch, discovery = _open()
    validation = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.VALIDATION,
        epoch,
    )
    discovery_draw = discovery.draw()
    validation_draw = validation.draw()
    assert discovery.stream_id != validation.stream_id
    assert (
        discovery_draw.raw_commitment.raw_digest
        != validation_draw.raw_commitment.raw_digest
    )
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.verify_observed_transition_tuple_v1(
            context,
            catalogue,
            action,
            observer.ObservationLane.VALIDATION,
            epoch,
            discovery_draw,
        )


def test_support_epoch_changes_stream_and_requires_exact_parent_chain() -> None:
    context, catalogue, action, epoch0, stream0 = _open()
    first = stream0.draw()
    epoch1 = observer.support_epoch_identity_v1(
        context,
        1,
        (first.observation_id,),
        epoch0,
    )
    stream1 = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch1,
    )
    assert epoch1.epoch_id != epoch0.epoch_id
    assert stream1.stream_id != stream0.stream_id
    assert (
        stream1.draw().raw_commitment.raw_digest
        != first.raw_commitment.raw_digest
    )
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.support_epoch_identity_v1(
            context,
            2,
            (),
            epoch0,
        )
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.support_epoch_identity_v1(
            context,
            0,
            (first.observation_id, first.observation_id),
        )


def test_replay_verifier_reconstructs_raw_tuple_and_work() -> None:
    context, catalogue, action, epoch, stream = _open(
        lane=observer.ObservationLane.VALIDATION
    )
    draws = tuple(stream.draw() for _ in range(7))
    verification = observer.verify_observed_transition_tuple_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.VALIDATION,
        epoch,
        draws[-1],
    )
    work = stream.work_snapshot()
    assert verification.observation_id == draws[-1].observation_id
    assert verification.replayed_accepted_draws == 7
    assert verification.replayed_random_word_calls == work.random_word_calls
    assert verification.replayed_rejections == work.rejection_count
    assert verification.tuple_replay_passed


def test_random_word_and_rejection_work_reconcile_when_tail_is_forced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, catalogue, action, epoch, _ = _open()
    original = observer._splitmix64
    calls = {"count": 0}

    def force_one_rejection(value: int) -> int:
        calls["count"] += 1
        if calls["count"] == 1:
            return (1 << 64) - 1
        return original(value)

    monkeypatch.setattr(observer, "_splitmix64", force_one_rejection)
    stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    draw = stream.draw()
    assert draw.raw_commitment.random_word_count == 2
    assert draw.raw_commitment.rejection_count == 1
    work = stream.work_snapshot()
    assert work.accepted_draws == 1
    assert work.random_word_calls == 2
    assert work.rejection_count == 1


def test_stream_invariant_cache_preserves_forced_rejection_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, catalogue, action, epoch, _ = _open()
    stream_id = observer._stream_id(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    seed = observer._stream_seed(
        stream_id,
        observer.ObservationLane.DISCOVERY,
    )
    rejected_input = seed + observer._SPLITMIX_GAMMA
    original = observer._splitmix64

    def force_first_word_to_rejection(value: int) -> int:
        if value == rejected_input:
            return observer._UINT64_MODULUS - 1
        return original(value)

    monkeypatch.setattr(
        observer,
        "_splitmix64",
        force_first_word_to_rejection,
    )
    stream = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    optimized = tuple(stream.draw().to_document() for _ in range(8))
    optimized_work = stream.work_snapshot().to_document()
    observer.clear_transition_tuple_observer_id_cache_v1()
    reference, reference_work = _reference_uncached_draws(
        context,
        catalogue,
        action,
        observer.ObservationLane.DISCOVERY,
        epoch,
        8,
    )
    assert optimized == reference
    assert optimized_work == reference_work
    assert optimized[0]["raw_commitment"]["rejection_count"] == 1


def test_operational_observer_never_calls_legacy_or_evaluation_atom_enumerator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("operational observer read an exact atom row")

    monkeypatch.setattr(
        legacy_graph.RelationalGraphMergeKernelV2,
        "atoms",
        forbidden,
    )
    monkeypatch.setattr(
        observer,
        "evaluation_exact_atoms_v1",
        forbidden,
    )
    _, _, _, _, stream = _open("opaque_graph_k6_v0")
    draws = tuple(stream.draw() for _ in range(16))
    assert len(draws) == 16
    source = inspect.getsource(
        observer.OpaqueTargetLocalTransitionStreamV1.draw
    )
    assert "evaluation_exact_atoms_v1" not in source
    assert "RelationalGraphMergeKernelV2" not in source


def test_wrong_context_binding_is_rejected_before_sampling() -> None:
    w5, catalogue, action, epoch, _ = _open()
    k6 = observer.public_context_by_key_v1("opaque_graph_k6_v0")
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.open_target_local_transition_stream_v1(
            k6,
            catalogue,
            action,
            observer.ObservationLane.DISCOVERY,
            epoch,
        )
    forged_catalogue = replace(catalogue, context_id=k6.context_id)
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.open_target_local_transition_stream_v1(
            w5,
            forged_catalogue,
            action,
            observer.ObservationLane.DISCOVERY,
            epoch,
        )


def test_raw_tuple_and_commitment_tampering_fail_replay() -> None:
    context, catalogue, action, epoch, stream = _open()
    draw = stream.draw()
    changed_reward = replace(
        draw,
        realized_row_reward=draw.realized_row_reward + Fraction(1, 128),
    )
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.verify_observed_transition_tuple_v1(
            context,
            catalogue,
            action,
            observer.ObservationLane.DISCOVERY,
            epoch,
            changed_reward,
        )
    changed_commitment = replace(
        draw.raw_commitment,
        raw_digest="f" * 64,
    )
    changed_raw = replace(draw, raw_commitment=changed_commitment)
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.verify_observed_transition_tuple_v1(
            context,
            catalogue,
            action,
            observer.ObservationLane.DISCOVERY,
            epoch,
            changed_raw,
        )


def test_observation_context_transplant_fails_closed() -> None:
    w5, catalogue, action, epoch, stream = _open()
    draw = stream.draw()
    k6, k6_catalogue, k6_action, k6_epoch, _ = _open(
        "opaque_graph_k6_v0"
    )
    transplanted = replace(draw, context_id=k6.context_id)
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.verify_observed_transition_tuple_v1(
            k6,
            k6_catalogue,
            k6_action,
            observer.ObservationLane.DISCOVERY,
            k6_epoch,
            transplanted,
        )
    assert w5.context_id != k6.context_id
    assert catalogue.catalogue_id != k6_catalogue.catalogue_id
    assert action == k6_action
    assert epoch.epoch_id != k6_epoch.epoch_id


def test_evaluation_only_atom_rows_reveal_registered_hidden_laws() -> None:
    expected = {
        "opaque_graph_w5_v0": (
            6,
            tuple(
                sorted(
                    (
                        Fraction(33, 100),
                        Fraction(33, 100),
                        Fraction(33, 100),
                        Fraction(1, 300),
                        Fraction(1, 300),
                        Fraction(1, 300),
                    )
                )
            ),
        ),
        "opaque_graph_k6_v0": (
            12,
            tuple(
                sorted(
                    (
                        *([Fraction(197, 800)] * 4),
                        *([Fraction(1, 400)] * 4),
                        *([Fraction(1, 800)] * 4),
                    )
                )
            ),
        ),
        "opaque_graph_k6_minus_edge_v0": (
            8,
            tuple(
                sorted(
                    (
                        *([Fraction(99, 400)] * 4),
                        *([Fraction(1, 400)] * 4),
                    )
                )
            ),
        ),
    }
    for context in observer.registered_public_graph_contexts_v1():
        state = observer.root_state_v1(context)
        catalogue = observer.legal_action_catalogue_v1(
            context,
            state,
            2,
        )
        atoms = observer.evaluation_exact_atoms_v1(
            context,
            catalogue,
            catalogue.actions[0],
        )
        count, probabilities = expected[context.context_key]
        assert len(atoms) == count
        assert tuple(sorted(item.probability for item in atoms)) == probabilities
        assert sum((item.probability for item in atoms), Fraction(0)) == 1
        assert all(item.execution_lane == "EVALUATION_ONLY" for item in atoms)


def test_evaluation_only_exact_h2_ground_search_reproduces_registered_values() -> None:
    expected = {
        "opaque_graph_w5_v0": (
            Fraction(99, 5000),
            Fraction(3, 64),
            30,
        ),
        "opaque_graph_k6_v0": (
            Fraction(197, 10000),
            Fraction(3, 64),
            76,
        ),
        "opaque_graph_k6_minus_edge_v0": (
            Fraction(2277, 16000),
            Fraction(3, 64),
            60,
        ),
    }
    for context in observer.registered_public_graph_contexts_v1():
        result = observer.evaluation_exact_ground_search_v1(context)
        risk, reward, rows = expected[context.context_key]
        assert result.root_failure_probability == risk
        assert result.root_normalized_reward == reward
        assert result.evaluated_state_action_rows == rows
        assert result.root_failure_probability <= context.risk_tolerance
        assert result.feasible_under_public_risk
        assert result.complete_h2_deterministic_policy_search
        assert result.execution_lane == "EVALUATION_ONLY"


def test_missing_edge_context_is_a_feasible_ground_no_cover_separator() -> None:
    context = observer.public_context_by_key_v1(
        "opaque_graph_k6_minus_edge_v0"
    )

    assert context.risk_tolerance == Fraction(2847, 20000)
    assert Fraction(2277, 16000) < context.risk_tolerance
    assert context.risk_tolerance < Fraction(11393, 80000)


def test_content_id_domain_and_identity_changes_are_fail_closed() -> None:
    context, catalogue, action, epoch, stream = _open()
    draw = stream.draw()
    assert len(
        {
            context.context_id,
            catalogue.catalogue_id,
            epoch.epoch_id,
            stream.stream_id,
            draw.raw_commitment.commitment_id,
            draw.observation_id,
        }
    ) == 6
    other_action = catalogue.actions[1]
    other = observer.open_target_local_transition_stream_v1(
        context,
        catalogue,
        other_action,
        observer.ObservationLane.DISCOVERY,
        epoch,
    )
    assert other.stream_id != stream.stream_id
    with pytest.raises(observer.TransitionTupleObserverInvariantViolation):
        observer.SupportEpochIdentityV1(
            context.context_id,
            0,
            "short",
            None,
        )
