from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import threading

import pytest

from acfqp import construction_accounting_owned_runtime_v1 as runtime
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v6 as registry_v6
import acfqp.h2_graph_transition_engine_v1 as engine
from acfqp.relational_graph_core_v1 import GraphTopologyV1
import acfqp.sequential_bernoulli_acquisition_v1 as sequential
from acfqp.v075_k7_root_cap_operation_boundary_manifest_v3 import (
    official_k7_root_cap_operation_boundary_manifest_v3,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:source-native-hook-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def _activation(label: str):
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    return runtime.activate_owned_construction_accounting_v1(
        occurrence_id=_id(label),
        recorder_id="source-native-hook-test-recorder-v1",
        counter_registry=registry,
        stage_profile=stage,
        boundary_profile=(
            official_k7_root_cap_operation_boundary_manifest_v3()
        ),
    )


def _enter_target_stage(target: partial.PartialNativeStageV1) -> None:
    for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1:
        runtime.enter_owned_stage_v1(stage)
        if stage is target:
            return
        runtime.exit_owned_stage_v1(stage)
    raise AssertionError("target stage is outside the five-stage profile")


def _complete_from_stage(
    target: partial.PartialNativeStageV1,
) -> partial.PartialNativeOccurrenceTranscriptV1:
    runtime.exit_owned_stage_v1(target)
    target_index = partial.ROOT_CAP_FIVE_STAGE_PLAN_V1.index(target)
    for stage in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1[target_index + 1 :]:
        runtime.enter_owned_stage_v1(stage)
        runtime.exit_owned_stage_v1(stage)
    result = runtime.complete_owned_occurrence_v1()
    assert result is not None
    return result


def _event_path_counts(
    transcript: partial.PartialNativeOccurrenceTranscriptV1,
) -> Counter[str]:
    return Counter(
        row.path
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
        for _ in range(row.amount)
    )


def _kernel() -> engine.H2GraphKernelV1:
    return engine.H2GraphKernelV1(
        topology=GraphTopologyV1(
            4,
            ((0, 1), (0, 2), (1, 3), (2, 3)),
        ),
        rank_cap=6,
        horizon=2,
        spawn_law=(
            (1, Fraction(99, 100)),
            (2, Fraction(1, 100)),
        ),
    )


def _profile() -> sequential.SequentialBernoulliProfileV1:
    return sequential.SequentialBernoulliProfileV1(
        confidence_alpha=Fraction(1, 1_000),
        target_half_width=Fraction(1, 16),
        checkpoints=(64,),
        boundary_grid_bits=8,
    )


def test_inactive_hooks_preserve_engine_and_sequential_outputs() -> None:
    kernel = _kernel()
    state = engine.H2GraphStateV1((1, 1, 2, 0))
    action = engine.H2GraphActionV1(0, 1, 0)
    first_stream = engine.DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=2,
        seed=17,
    )
    second_stream = engine.DeterministicH2GraphStreamV1(
        kernel=kernel,
        state=state,
        action=action,
        remaining_horizon=2,
        seed=17,
    )
    assert first_stream.draw() == second_stream.draw()

    sequential.clear_exact_bernoulli_math_cache_v1()
    first = sequential.build_anytime_bernoulli_checkpoint_v1(
        64, 7, _profile()
    )
    sequential.clear_exact_bernoulli_math_cache_v1()
    second = sequential.build_anytime_bernoulli_checkpoint_v1(
        64, 7, _profile()
    )
    assert first == second
    assert first.to_document() == second.to_document()


def test_inactive_sequential_cache_bypasses_accounting_classification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sequential.clear_exact_bernoulli_math_cache_v1()
    expected = sequential.build_anytime_bernoulli_checkpoint_v1(
        64, 7, _profile()
    )
    sequential.clear_exact_bernoulli_math_cache_v1()

    def forbidden_classification(**_kwargs: object) -> None:
        raise AssertionError(
            "inactive cache traffic entered accounting classification"
        )

    monkeypatch.setattr(
        sequential,
        "_classify_outer_confidence_cache_access_v2",
        forbidden_classification,
    )
    assert runtime.owned_accounting_active_v1() is False
    cold = sequential.build_anytime_bernoulli_checkpoint_v1(
        64, 7, _profile()
    )
    warm = sequential.build_anytime_bernoulli_checkpoint_v1(
        64, 7, _profile()
    )
    assert cold == expected
    assert warm == expected


def test_cold_cache_epoch_excludes_concurrent_registered_cache_users() -> None:
    sequential.clear_exact_bernoulli_math_cache_v1()
    started = threading.Event()
    finished = threading.Event()
    errors: list[BaseException] = []

    def cache_user() -> None:
        started.set()
        try:
            sequential.beta_binomial_sequence_mass_v1(64, 7)
            sequential._outer_confidence_bounds(  # noqa: SLF001
                64,
                7,
                Fraction(1, 1_000),
                8,
            )
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)
        finally:
            finished.set()

    with sequential.isolate_exact_bernoulli_math_cache_v1():
        worker = threading.Thread(target=cache_user)
        worker.start()
        assert started.wait(timeout=1)
        assert finished.wait(timeout=0.05) is False

    worker.join(timeout=2)
    assert finished.is_set()
    assert errors == []


def test_registered_cache_users_remain_concurrent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendezvous = threading.Barrier(2)
    results: list[Fraction] = []
    errors: list[BaseException] = []

    def overlapping_cache_body(
        _draw_count: int,
        _success_count: int,
    ) -> Fraction:
        rendezvous.wait(timeout=1)
        return Fraction(1, 7)

    monkeypatch.setattr(
        sequential,
        "_beta_binomial_sequence_mass_cached_v1",
        overlapping_cache_body,
    )

    def cache_user() -> None:
        try:
            results.append(
                sequential.beta_binomial_sequence_mass_v1(7, 3)
            )
        except BaseException as error:  # pragma: no cover - asserted below
            errors.append(error)

    workers = [threading.Thread(target=cache_user) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)

    assert errors == []
    assert results == [Fraction(1, 7), Fraction(1, 7)]


def test_cold_miss_then_hit_charges_only_executed_sequential_work() -> None:
    sequential.clear_exact_bernoulli_math_cache_v1()
    with _activation("sequential-cold-miss-hit"):
        target = partial.PartialNativeStageV1.INITIAL_MODEL_BUILD
        _enter_target_stage(target)
        first = sequential.build_anytime_bernoulli_checkpoint_v1(
            64, 7, _profile()
        )
        second = sequential.build_anytime_bernoulli_checkpoint_v1(
            64, 7, _profile()
        )
        transcript = _complete_from_stage(target)

    assert second == first
    counts = _event_path_counts(transcript)
    assert counts["build.initial_confidence_cache_lookups"] == 2
    assert counts["build.initial_confidence_cache_misses"] == 1
    assert counts["build.initial_confidence_cache_hits"] == 1
    assert counts[
        "build.initial_sequential_exact_likelihood_comparisons"
    ] == first.exact_likelihood_comparisons
    assert counts[
        "build.initial_sequential_interval_log_search_evaluations"
    ] == first.log_search_evaluations
    assert first.exact_likelihood_comparisons > 0
    assert first.log_search_evaluations > 0
    log_sites = {
        row.site_id
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
        and row.path
        == "build.initial_sequential_interval_log_search_evaluations"
    }
    assert len(log_sites) == 2
    assert all(
        row.amount == 1
        for row in transcript.nodes
        if type(row) is partial.PartialNativeOperationEventV1
    )
    boundary_document = (
        official_k7_root_cap_operation_boundary_manifest_v3().to_document()
    )
    assert sequential.CONSTRUCTION_ACCOUNTING_CACHE_LIFECYCLE == (
        boundary_document["official_cache_lifecycle"]
    )
    assert sequential.CONSTRUCTION_ACCOUNTING_BETA_BINOMIAL_CACHE_POLICY == (
        boundary_document["beta_binomial_cache_accounting"]
    )


def test_engine_hooks_count_init_words_rejection_and_completed_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    words = iter(((1 << 64) - 1, 0))
    monkeypatch.setattr(engine, "splitmix64_v1", lambda _value: next(words))
    with _activation("engine-rejection"):
        target = partial.PartialNativeStageV1.INITIAL_ACQUISITION
        _enter_target_stage(target)
        stream = engine.DeterministicH2GraphStreamV1(
            kernel=_kernel(),
            state=engine.H2GraphStateV1((1, 1, 2, 0)),
            action=engine.H2GraphActionV1(0, 1, 0),
            remaining_horizon=2,
            seed=0,
        )
        sample = stream.draw()
        transcript = _complete_from_stage(target)

    assert sample.random_words == ((1 << 64) - 1, 0)
    assert sample.rejection_count == 1
    counts = _event_path_counts(transcript)
    assert counts["acquisition.initial_engine_stream_initialization_merges"] == 1
    assert counts["acquisition.initial_engine_random_word_calls"] == 2
    assert counts["acquisition.initial_engine_rejections"] == 1
    assert counts["acquisition.initial_engine_ground_draws"] == 1


def test_source_hook_in_the_wrong_active_stage_fails_closed() -> None:
    with _activation("wrong-stage") as session:
        runtime.enter_owned_stage_v1(
            partial.PartialNativeStageV1.PREOPEN_COMMON_PREFIX
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="no emittable boundary",
        ):
            engine.DeterministicH2GraphStreamV1(
                kernel=_kernel(),
                state=engine.H2GraphStateV1((1, 1, 2, 0)),
                action=engine.H2GraphActionV1(0, 1, 0),
                remaining_horizon=2,
                seed=0,
            )
        transcript = session.transcript

    terminal = transcript.nodes[-1]
    assert type(terminal) is partial.PartialNativeOccurrenceAbortV1
    assert terminal.reason == "UNKNOWN_OR_STAGE_UNBOUND_DISPATCH"

    sequential.clear_exact_bernoulli_math_cache_v1()
    with _activation("wrong-sequential-stage") as sequential_session:
        _enter_target_stage(
            partial.PartialNativeStageV1.INITIAL_ACQUISITION
        )
        with pytest.raises(
            runtime.OwnedConstructionAccountingRuntimeV1Error,
            match="no emittable boundary",
        ):
            sequential.build_anytime_bernoulli_checkpoint_v1(
                64, 7, _profile()
            )
        sequential_transcript = sequential_session.transcript
    sequential_terminal = sequential_transcript.nodes[-1]
    assert type(sequential_terminal) is partial.PartialNativeOccurrenceAbortV1
    assert sequential_terminal.reason == "UNKNOWN_OR_STAGE_UNBOUND_DISPATCH"
