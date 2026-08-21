"""Execute only the generic compiler/planner on a second structural family."""

from __future__ import annotations

from types import FunctionType, SimpleNamespace
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v124 as domains
from acfqp import generic_genesis_authorized_program_branch_sequence_v119 as v119
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113_sequence
from acfqp import generic_incremental_abstract_successor_v113 as v113
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp import generic_factor_planner_sequence_v122 as v122
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4, FlatRawTransitionV4
from acfqp.generic_compiled_quotient_model_v123 import (
    compile_generic_quotient_model_v123,
    generic_incremental_runtime_v123,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15


class CrossFamilyGenericCompilerSequenceV124Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise CrossFamilyGenericCompilerSequenceV124Error(message)


def _row(document: dict[str, Any]) -> FlatRawTransitionV4:
    selected = document["selected_action"]
    return FlatRawTransitionV4(
        document["occurrence"],
        document["transition_index"],
        tuple(document["pre_vector"]),
        tuple(document["legal_action_keys_before"]),
        FlatRawActionV4(selected["action_key"], tuple(selected["anonymous_fields"])),
        tuple(document["post_vector"]),
        tuple(document["legal_action_keys_after"]),
        document["terminal_acceptance_after"],
        document.get("outcome_tape_sha256"),
    )


def _deduplicate(rows: tuple[Any, ...]) -> tuple[Any, ...]:
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _generic_plan_function(runtime):
    proxy = SimpleNamespace(
        _verify_state=runtime.verify_state,
        _initial_projected_state=v113._initial_projected_state,  # noqa: SLF001
        _observation_graph_plan=v113._observation_graph_plan,  # noqa: SLF001
        GenericIncrementalAbstractSuccessorV113Error=v113.GenericIncrementalAbstractSuccessorV113Error,
        _V106_PLAN_DOMAIN=v113._V106_PLAN_DOMAIN,  # noqa: SLF001
    )
    namespace = dict(v122.__dict__)
    namespace["successor"] = proxy
    source = v122._plan_with_branch_cache_v122  # noqa: SLF001
    result = FunctionType(source.__code__, namespace, source.__name__, source.__defaults__, source.__closure__)
    result.__kwdefaults__ = source.__kwdefaults__
    return result


def _run_base_v124(
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
    proxy = SimpleNamespace(previous=v115.previous, _memoized_program_plan=v115._memoized_program_plan, _plan_with_branch_cache=planner)  # noqa: SLF001
    orderer_namespace = dict(v119.__dict__)
    orderer_namespace["v115"] = proxy
    source_orderer = v119._genesis_authorized_orderer  # noqa: SLF001
    orderer = FunctionType(source_orderer.__code__, orderer_namespace, source_orderer.__name__, source_orderer.__defaults__, source_orderer.__closure__)
    orderer.__kwdefaults__ = source_orderer.__kwdefaults__
    namespace = dict(v113_sequence.__dict__)
    namespace.update(
        _incremental_indexed_orderer=orderer,
        initialize_incremental_abstract_successor_v113=runtime.initialize,
        advance_incremental_abstract_successor_v113=runtime.advance,
        verify_incremental_successor_against_full_rebuild_v113=runtime.verify,
    )
    source = v113_sequence.run_incremental_abstract_successor_sequence_v113
    sequence = FunctionType(source.__code__, namespace, source.__name__, source.__defaults__, source.__closure__)
    sequence.__kwdefaults__ = source.__kwdefaults__
    return sequence(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=maximum_incremental_certificate_ground_support_labels,
    )


def _generic_reconstruction(
    base: dict[str, Any],
    candidate: PartialFactorCandidateV15,
    initial_rows: tuple[Any, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    persistent = _deduplicate(initial_rows)
    comparisons = checks = 0
    for episode, before, after in zip(
        base["episodes"],
        base["quotient_models_before_each_episode"],
        base["quotient_models_after_each_episode"],
        strict=True,
    ):
        rebuilt_before = compile_generic_quotient_model_v123(candidate, persistent, catalogue)
        comparisons += 1
        checks += rebuilt_before["source_projected_edge_program_checks"]
        if rebuilt_before != before:
            _fail("V124 before-model differs from independent generic reconstruction")
        new_rows = tuple(_row(row) for row in episode["raw_incremental_transition_rows"])
        persistent = _deduplicate((*persistent, *new_rows))
        rebuilt_after = compile_generic_quotient_model_v123(candidate, persistent, catalogue)
        comparisons += 1
        checks += rebuilt_after["source_projected_edge_program_checks"]
        if rebuilt_after != after:
            _fail("V124 after-model differs from independent generic reconstruction")
    return {
        "generic_model_epoch_reconstruction_count": comparisons,
        "generic_model_program_support_checks": checks,
        "every_model_epoch_reconstructed_only_by_generic_compiler": True,
        "legacy_shape_specific_model_builder_called": False,
        "legacy_matched_control_present": False,
    }


def run_cross_family_generic_compiler_sequence_v124(
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
    namespace["_run_base"] = _run_base_v124
    source = v119.run_genesis_authorized_program_branch_sequence_v119
    function = FunctionType(source.__code__, namespace, source.__name__, source.__defaults__, source.__closure__)
    function.__kwdefaults__ = source.__kwdefaults__
    v119_sequence = function(
        adapter,
        candidate,
        observed_rows,
        acquisition_ground_support_labels,
        episode_indices=episode_indices,
        maximum_abstract_depth=maximum_abstract_depth,
        maximum_execution_steps=maximum_execution_steps,
        maximum_incremental_certificate_ground_support_labels=maximum_incremental_certificate_ground_support_labels,
    )
    base = v119_sequence["genesis_authorized_base_sequence"]
    reconstruction = _generic_reconstruction(base, candidate, observed_rows, adapter.catalogue)
    plans = [
        receipt["abstract_plan"]
        for episode in base["episodes"]
        for receipt in episode["abstract_plan_receipts"]
    ]
    direct = sum(plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK" for plan in plans)
    if direct <= 0 or any(
        plan.get("legacy_shape_specific_planner_execution_adapter_called") is not False
        for plan in plans
        if plan["planning_source"] in {"OBSERVATION_QUOTIENT_GRAPH", "COMPILED_FACTOR_PROGRAM_FALLBACK"}
    ):
        _fail("V124 generic planner was not cleanly exercised")
    payload = {
        "schema": "acfqp.cross_family_generic_compiler_sequence.v124",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "generic_compiler_base_sequence": v119_sequence,
        "generic_compiler_base_sequence_id": v119_sequence["sequence_id"],
        "generic_model_epoch_reconstruction": reconstruction,
        "direct_generic_factor_program_plan_count": direct,
        "generic_quotient_model_compiler_verified": True,
        "generic_planner_execution_adapter_verified": True,
        "legacy_shape_specific_model_builder_called": False,
        "legacy_matched_model_control_present": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "retained_v113_state_carrier_present": True,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v124(
            domains.CONSTRUCTION_K7_CROSS_FAMILY_GENERIC_COMPILER_SEQUENCE_V124_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_cross_family_generic_compiler_sequence_v124",)
