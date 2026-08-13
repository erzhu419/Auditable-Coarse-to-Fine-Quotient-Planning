from __future__ import annotations

from fractions import Fraction
import copy

import pytest

from acfqp import construction_k7_standard_2048_adaptive_expression_runtime_v35 as runtime
from acfqp import construction_k7_standard_2048_expression_program_preregistration_v21 as v21
from acfqp.domains.standard_2048 import state_from_board_v1


def _contexts() -> tuple[runtime.RawExpressionContextV35, ...]:
    return tuple(
        runtime.raw_expression_context_v35(tuple(board), action)
        for board, action in v21.RAW_CONTEXT_POOL
    )


def _synthetic_label(context: runtime.RawExpressionContextV35) -> Fraction:
    return (
        Fraction(1, 5)
        if context.post_swipe_board.count(1) <= 2
        else runtime.BASE_RANK_TWO_PROBABILITY
    )


def test_raw_context_replays_standard_swipe_and_rejects_noop() -> None:
    context = _contexts()[0]
    assert len(context.context_sha256) == 64
    assert context.to_document()["structural_context_sha256"] == context.context_sha256
    with pytest.raises(
        runtime.ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error
    ):
        runtime.raw_expression_context_v35((0,) * 16, "LEFT")


def test_h1_frontier_is_support_complete_and_target_free() -> None:
    board = (1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    frontier = runtime.enumerate_raw_frontier_contexts_v35(
        state_from_board_v1(board), horizon=1
    )
    assert len(frontier) == 4
    assert {row.action for row in frontier} == {"LEFT", "RIGHT", "UP", "DOWN"}
    assert all(0 in row.post_swipe_board for row in frontier)


def test_no_nonbase_label_requires_one_failed_frontier_query() -> None:
    contexts = _contexts()
    labels = {contexts[0].context_sha256: runtime.BASE_RANK_TWO_PROBABILITY}
    candidates, counters = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=labels
    )
    assert candidates == ()
    assert counters["model.structural_context_rows_frozen"] == 8
    decision = runtime.local_certificate_or_query_v35(
        frontier_contexts=contexts, candidates=candidates, labels=labels
    )
    assert decision.status == "QUERY_REQUIRED_NO_NONBASE_LABEL"
    assert decision.next_query_context_sha256 not in labels


def test_observed_raw_values_generate_a_consistent_nonempty_version_space() -> None:
    contexts = _contexts()
    labels = {
        context.context_sha256: _synthetic_label(context)
        for context in contexts[:4]
    }
    assert len(set(labels.values())) == 2
    candidates, counters = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=labels
    )
    assert candidates
    assert all(
        candidate.predict(context) == observed
        for candidate in candidates
        for context_id, observed in labels.items()
        for context in contexts
        if context.context_sha256 == context_id
    )
    assert counters["model.expression_candidates_materialized"] == len(candidates)
    assert counters["model.candidate_label_consistency_checks"] > 0
    assert counters["model.structural_expression_value_evaluations"] > 0


def test_local_disagreement_queries_then_full_local_labels_certify() -> None:
    contexts = _contexts()
    initial_labels = {
        context.context_sha256: _synthetic_label(context)
        for context in contexts[:4]
    }
    candidates, _ = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=initial_labels
    )
    decision = runtime.local_certificate_or_query_v35(
        frontier_contexts=contexts, candidates=candidates, labels=initial_labels
    )
    assert decision.status == "QUERY_REQUIRED_LOCAL_DISAGREEMENT"
    assert decision.next_query_context_sha256 not in initial_labels

    all_labels = {
        context.context_sha256: _synthetic_label(context) for context in contexts
    }
    final_candidates, _ = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=all_labels
    )
    certified = runtime.local_certificate_or_query_v35(
        frontier_contexts=contexts,
        candidates=final_candidates,
        labels=all_labels,
    )
    assert certified.status == "LOCALLY_CERTIFIED_ALL_SURVIVORS_AGREE"
    assert certified.selected_candidate_id is not None
    assert certified.next_query_context_sha256 is None


def test_first_frontier_candidate_universe_only_shrinks() -> None:
    contexts = _contexts()
    initial_labels = {
        context.context_sha256: _synthetic_label(context)
        for context in contexts[:3]
    }
    candidates, _ = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=initial_labels
    )
    new_context = contexts[3]
    filtered, checks = runtime.filter_expression_candidates_v35(
        candidates=candidates,
        contexts_by_id={context.context_sha256: context for context in contexts},
        labels={new_context.context_sha256: _synthetic_label(new_context)},
    )
    assert 0 < len(filtered) <= len(candidates)
    assert checks >= len(filtered)
    assert set(item.candidate_id for item in filtered).issubset(
        item.candidate_id for item in candidates
    )


def test_unknown_label_context_and_empty_archive_fail_closed() -> None:
    contexts = _contexts()
    with pytest.raises(
        runtime.ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error
    ):
        runtime.generate_consistent_expression_candidates_v35(
            archived_contexts=(), labels={}
        )
    with pytest.raises(
        runtime.ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error
    ):
        runtime.generate_consistent_expression_candidates_v35(
            archived_contexts=contexts,
            labels={"f" * 64: Fraction(1, 5)},
        )


def test_candidate_is_immutable_and_identity_bound() -> None:
    contexts = _contexts()
    labels = {
        context.context_sha256: _synthetic_label(context)
        for context in contexts[:4]
    }
    candidates, _ = runtime.generate_consistent_expression_candidates_v35(
        archived_contexts=contexts, labels=labels
    )
    candidate = candidates[0]
    with pytest.raises(TypeError):
        candidate.expression_ast["operator"] = "FORGED"  # type: ignore[index]
    tampered = copy.copy(candidate)
    object.__setattr__(tampered, "direction", "GT_OVERRIDE")
    if tampered.direction == candidate.direction:
        object.__setattr__(tampered, "direction", "LE_OVERRIDE")
    with pytest.raises(
        runtime.ConstructionK7Standard2048AdaptiveExpressionRuntimeV35Error
    ):
        runtime.filter_expression_candidates_v35(
            candidates=(tampered,),
            contexts_by_id={context.context_sha256: context for context in contexts},
            labels=labels,
        )
