"""Plan with the standalone V125 generic model-epoch carrier."""

from __future__ import annotations

from types import FunctionType, SimpleNamespace
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v125 as domains
from acfqp import generic_genesis_authorized_program_branch_sequence_v119 as v119
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113_sequence
from acfqp import generic_incremental_abstract_successor_v113 as v113_planning_primitives
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp import generic_factor_planner_sequence_v122 as v122
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4, FlatRawTransitionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.standalone_generic_model_epoch_v125 import (
    advance_standalone_generic_model_v125,
    compile_standalone_generic_model_v125,
    initialize_standalone_generic_model_v125,
    verify_standalone_generic_model_full_rebuild_v125,
    verify_standalone_generic_model_state_v125,
)


class StandaloneGenericModelSequenceV125Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise StandaloneGenericModelSequenceV125Error(message)


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


def _deduplicate(rows):
    unique = {(row.pre, row.action.key, row.post): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def _generic_plan_function():
    proxy = SimpleNamespace(
        _verify_state=verify_standalone_generic_model_state_v125,
        _initial_projected_state=v113_planning_primitives._initial_projected_state,  # noqa: SLF001
        _observation_graph_plan=v113_planning_primitives._observation_graph_plan,  # noqa: SLF001
        GenericIncrementalAbstractSuccessorV113Error=v113_planning_primitives.GenericIncrementalAbstractSuccessorV113Error,
        _V106_PLAN_DOMAIN=v113_planning_primitives._V106_PLAN_DOMAIN,  # noqa: SLF001
    )
    namespace = dict(v122.__dict__)
    namespace["successor"] = proxy
    source = v122._plan_with_branch_cache_v122  # noqa: SLF001
    function = FunctionType(source.__code__, namespace, source.__name__, source.__defaults__, source.__closure__)
    function.__kwdefaults__ = source.__kwdefaults__
    return function


def _run_base_v125(
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
    planner = _generic_plan_function()
    proxy = SimpleNamespace(previous=v115.previous, _memoized_program_plan=v115._memoized_program_plan, _plan_with_branch_cache=planner)  # noqa: SLF001
    orderer_namespace = dict(v119.__dict__)
    orderer_namespace["v115"] = proxy
    source_orderer = v119._genesis_authorized_orderer  # noqa: SLF001
    orderer = FunctionType(source_orderer.__code__, orderer_namespace, source_orderer.__name__, source_orderer.__defaults__, source_orderer.__closure__)
    orderer.__kwdefaults__ = source_orderer.__kwdefaults__
    namespace = dict(v113_sequence.__dict__)
    namespace.update(
        _incremental_indexed_orderer=orderer,
        initialize_incremental_abstract_successor_v113=initialize_standalone_generic_model_v125,
        advance_incremental_abstract_successor_v113=advance_standalone_generic_model_v125,
        verify_incremental_successor_against_full_rebuild_v113=verify_standalone_generic_model_full_rebuild_v125,
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


def _reconstruct(base, candidate, initial_rows, catalogue):
    persistent = _deduplicate(initial_rows)
    count = checks = 0
    for episode, before, after in zip(base["episodes"], base["quotient_models_before_each_episode"], base["quotient_models_after_each_episode"], strict=True):
        rebuilt = compile_standalone_generic_model_v125(candidate, persistent, catalogue)
        count += 1
        checks += rebuilt["source_projected_edge_program_checks"]
        if rebuilt != before:
            _fail("V125 before-model reconstruction changed")
        persistent = _deduplicate((*persistent, *( _row(row) for row in episode["raw_incremental_transition_rows"] )))
        rebuilt = compile_standalone_generic_model_v125(candidate, persistent, catalogue)
        count += 1
        checks += rebuilt["source_projected_edge_program_checks"]
        if rebuilt != after:
            _fail("V125 after-model reconstruction changed")
    receipts = [base["bootstrap_receipt"], *base["incremental_successor_update_receipts"], *base["full_rebuild_match_receipts"]]
    if any(receipt.get("retained_v113_state_carrier_present") is not False for receipt in receipts):
        _fail("V125 emitted a receipt backed by the V113 state carrier")
    return {
        "generic_model_epoch_reconstruction_count": count,
        "generic_model_program_support_checks": checks,
        "all_state_and_update_receipts_use_v125_domains": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
    }


def run_standalone_generic_model_sequence_v125(
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
    namespace["_run_base"] = _run_base_v125
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
    reconstruction = _reconstruct(base, candidate, observed_rows, adapter.catalogue)
    plans = [receipt["abstract_plan"] for episode in base["episodes"] for receipt in episode["abstract_plan_receipts"]]
    direct = sum(plan["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK" for plan in plans)
    if direct <= 0:
        _fail("V125 generic program fallback was not exercised")
    payload = {
        "schema": "acfqp.standalone_generic_model_sequence.v125",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "generic_compiler_base_sequence": v119_sequence,
        "generic_compiler_base_sequence_id": v119_sequence["sequence_id"],
        "standalone_generic_model_reconstruction": reconstruction,
        "direct_generic_factor_program_plan_count": direct,
        "standalone_v125_state_carrier_verified": True,
        "retained_v113_state_carrier_present": False,
        "retained_v113_sequence_orchestration_present": True,
        "legacy_shape_specific_model_builder_called": False,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
    }
    return {**payload, "sequence_id": domains.extension_content_id_v125(domains.CONSTRUCTION_K7_STANDALONE_GENERIC_MODEL_SEQUENCE_V125_DOMAIN, payload)}


__all__ = ("run_standalone_generic_model_sequence_v125",)
