"""Run the certificate sequence with the V123 generic quotient compiler."""

from __future__ import annotations

import copy
from types import FunctionType, SimpleNamespace
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v123 as domains
from acfqp import generic_genesis_authorized_program_branch_sequence_v119 as v119
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113_sequence
from acfqp import generic_incremental_abstract_successor_v113 as v113
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp import generic_factor_planner_sequence_v122 as v122
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawTransitionV4
from acfqp.generic_compiled_quotient_model_v123 import (
    compile_generic_quotient_model_v123,
    generic_incremental_runtime_v123,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    compile_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


class GenericQuotientCompilerSequenceV123Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericQuotientCompilerSequenceV123Error(message)


def _row(document):
    selected = document["selected_action"]
    return FlatRawTransitionV4(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        v113.FlatRawActionV4(selected["action_key"], tuple(selected["anonymous_fields"])),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["terminal_acceptance_after"],
        document.get("outcome_tape_sha256"),
    )


def _deduplicate(rows):
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _generic_plan_function(runtime):
    proxy = SimpleNamespace(
        _verify_state=runtime.verify_state,
        _initial_projected_state=v113._initial_projected_state,  # noqa: SLF001
        _observation_graph_plan=v113._observation_graph_plan,  # noqa: SLF001
        GenericIncrementalAbstractSuccessorV113Error=(
            v113.GenericIncrementalAbstractSuccessorV113Error
        ),
        _V106_PLAN_DOMAIN=v113._V106_PLAN_DOMAIN,  # noqa: SLF001
    )
    namespace = dict(v122.__dict__)
    namespace["successor"] = proxy
    source = v122._plan_with_branch_cache_v122  # noqa: SLF001
    function = FunctionType(
        source.__code__,
        namespace,
        name=source.__name__,
        argdefs=source.__defaults__,
        closure=source.__closure__,
    )
    function.__kwdefaults__ = source.__kwdefaults__
    return function


def _run_base_v123(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    runtime = generic_incremental_runtime_v123()
    planner = _generic_plan_function(runtime)
    v115_proxy = SimpleNamespace(
        previous=v115.previous,
        _memoized_program_plan=v115._memoized_program_plan,  # noqa: SLF001
        _plan_with_branch_cache=planner,
    )
    orderer_namespace = dict(v119.__dict__)
    orderer_namespace["v115"] = v115_proxy
    source_orderer = v119._genesis_authorized_orderer  # noqa: SLF001
    orderer = FunctionType(
        source_orderer.__code__,
        orderer_namespace,
        name=source_orderer.__name__,
        argdefs=source_orderer.__defaults__,
        closure=source_orderer.__closure__,
    )
    orderer.__kwdefaults__ = source_orderer.__kwdefaults__
    namespace = dict(v113_sequence.__dict__)
    namespace.update(
        _incremental_indexed_orderer=orderer,
        initialize_incremental_abstract_successor_v113=runtime.initialize,
        advance_incremental_abstract_successor_v113=runtime.advance,
        verify_incremental_successor_against_full_rebuild_v113=runtime.verify,
    )
    source_sequence = v113_sequence.run_incremental_abstract_successor_sequence_v113
    sequence = FunctionType(
        source_sequence.__code__,
        namespace,
        name=source_sequence.__name__,
        argdefs=source_sequence.__defaults__,
        closure=source_sequence.__closure__,
    )
    sequence.__kwdefaults__ = source_sequence.__kwdefaults__
    return sequence(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )


def _matched_model_comparison(
    base: dict[str, Any],
    candidate: PartialFactorCandidateV15,
    initial_rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
) -> dict[str, Any]:
    persistent = _deduplicate(initial_rows)
    comparisons = generic_checks = legacy_checks = 0
    for episode, before, after in zip(
        base["episodes"],
        base["quotient_models_before_each_episode"],
        base["quotient_models_after_each_episode"],
        strict=True,
    ):
        generic_before = compile_generic_quotient_model_v123(candidate, persistent, catalogue)
        legacy_before = compile_observation_quotient_graph_v105(candidate, persistent, catalogue)
        comparisons += 1
        generic_checks += generic_before["source_projected_edge_program_checks"]
        legacy_checks += legacy_before["source_projected_edge_program_checks"]
        if generic_before != before or legacy_before != before:
            _fail("V123 model before episode differs from matched compiler evidence")
        new_rows = tuple(_row(row) for row in episode["raw_incremental_transition_rows"])
        persistent = _deduplicate((*persistent, *new_rows))
        generic_after = compile_generic_quotient_model_v123(candidate, persistent, catalogue)
        legacy_after = compile_observation_quotient_graph_v105(candidate, persistent, catalogue)
        comparisons += 1
        generic_checks += generic_after["source_projected_edge_program_checks"]
        legacy_checks += legacy_after["source_projected_edge_program_checks"]
        if generic_after != after or legacy_after != after:
            _fail("V123 model after episode differs from matched compiler evidence")
    return {
        "matched_model_comparison_count": comparisons,
        "generic_model_program_support_checks": generic_checks,
        "legacy_matched_control_program_support_checks": legacy_checks,
        "all_generic_models_equal_retained_v113_matched_control": True,
        "legacy_shape_specific_model_builder_used_as_planning_input": False,
        "legacy_matched_control_compute_charged_to_generic_arm": False,
    }


def run_generic_quotient_compiler_sequence_v123(
    adapter: Any,
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[Any, ...],
    acquisition_ground_support_labels: int,
    *,
    episode_indices: tuple[int, ...],
    maximum_abstract_depth: int,
    maximum_execution_steps: int,
    maximum_incremental_certificate_ground_support_labels: int,
) -> dict[str, Any]:
    namespace = dict(v119.__dict__)
    namespace["_run_base"] = _run_base_v123
    source = v119.run_genesis_authorized_program_branch_sequence_v119
    function = FunctionType(
        source.__code__,
        namespace,
        name=source.__name__,
        argdefs=source.__defaults__,
        closure=source.__closure__,
    )
    function.__kwdefaults__ = source.__kwdefaults__
    base = function(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=(
            maximum_incremental_certificate_ground_support_labels
        ),
    )
    comparison = _matched_model_comparison(
        base["genesis_authorized_base_sequence"],
        candidate,
        observed_rows,
        adapter.catalogue,
    )
    plans = [
        receipt["abstract_plan"]
        for episode in base["genesis_authorized_base_sequence"]["episodes"]
        for receipt in episode["abstract_plan_receipts"]
    ]
    direct = sum(row["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK" for row in plans)
    if direct <= 0 or any(
        row.get("legacy_shape_specific_planner_execution_adapter_called") is not False
        for row in plans
        if row["planning_source"] in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}
    ):
        _fail("V123 sequence did not exercise the generic planner cleanly")
    payload = {
        "schema": "acfqp.generic_quotient_compiler_sequence.v123",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "generic_compiler_base_sequence": base,
        "generic_compiler_base_sequence_id": base["sequence_id"],
        "generic_compiler_matched_control": comparison,
        "direct_generic_factor_program_plan_count": direct,
        "generic_quotient_model_compiler_verified": True,
        "generic_planner_execution_adapter_verified": True,
        "legacy_shape_specific_model_builder_used_as_planning_input": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v123(
            domains.CONSTRUCTION_K7_GENERIC_QUOTIENT_COMPILER_SEQUENCE_V123_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_generic_quotient_compiler_sequence_v123",)
