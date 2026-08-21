"""Run the retained certificate sequence with the V122 generic planner.

The historical incremental quotient graph remains a matched compiler control in
this slice.  Every fallback successor used to order actions is instead produced
by the recursive V122 interpreter.  The wrapper also replays every compiled
projected edge through that interpreter before issuing its sequence receipt.
"""

from __future__ import annotations

import copy
import hashlib
from types import FunctionType, SimpleNamespace
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v122 as domains
from acfqp import generic_genesis_authorized_program_branch_sequence_v119 as v119
from acfqp import generic_incremental_abstract_successor_sequence_v113 as v113_sequence
from acfqp import generic_incremental_abstract_successor_v113 as successor
from acfqp import generic_projected_program_memo_sequence_v115 as v115
from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_compiled_factor_planner_v122 import (
    derive_generic_terminal_rules_v122,
    generic_factor_successor_projections_v122,
    plan_generic_factor_program_v122,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class GenericFactorPlannerSequenceV122Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericFactorPlannerSequenceV122Error(message)


def _plan_with_branch_cache_v122(
    state: Any,
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    exact_legal_action_keys: tuple[int, ...],
    branch_cache: dict[tuple[tuple[int, ...], int], tuple[tuple[int, ...], ...]],
    *,
    legality_support_source: str,
    legality_failure_index: int | None,
    maximum_depth: int,
) -> dict[str, Any]:
    model, matched_legacy_rules = successor._verify_state(  # noqa: SLF001
        state, candidate, catalogue
    )
    generic_rules = derive_generic_terminal_rules_v122(
        candidate, model["projected_edge_rows"], model["projected_terminal_rows"]
    )
    if generic_rules != matched_legacy_rules:
        _fail("V122 generic terminal rule differs from the retained matched compiler")
    catalogue_keys = {action.key for action in catalogue}
    if (
        type(initial_raw_state) is not tuple
        or type(exact_legal_action_keys) is not tuple
        or not exact_legal_action_keys
        or len(set(exact_legal_action_keys)) != len(exact_legal_action_keys)
        or any(type(key) is not int or key not in catalogue_keys for key in exact_legal_action_keys)
        or legality_support_source
        not in (
            "PRELOADED_EXACT_LEGALITY_SUPPORT",
            "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
            "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
        )
        or (
            legality_support_source == "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and legality_failure_index is not None
        )
        or (
            legality_support_source != "PRELOADED_EXACT_LEGALITY_SUPPORT"
            and (type(legality_failure_index) is not int or legality_failure_index < 0)
        )
        or maximum_depth <= 0
    ):
        _fail("V122 legality-conditioned planner inventory changed")
    initial = successor._initial_projected_state(candidate, initial_raw_state)  # noqa: SLF001
    legal = frozenset(exact_legal_action_keys)
    try:
        plan = successor._observation_graph_plan(  # noqa: SLF001
            model, generic_rules, initial, legal, candidate
        )
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except successor.GenericIncrementalAbstractSuccessorV113Error:
        plan = plan_generic_factor_program_v122(
            candidate,
            catalogue,
            generic_rules,
            initial,
            legal,
            branch_cache,
            maximum_depth=maximum_depth,
        )
        source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
    actions = plan.get("action_keys")
    if type(actions) is not list or not actions or actions[0] not in legal:
        _fail("V122 planner action path changed")
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(actions[0],),
        partial_proposal=(actions[0],),
        legal_action_keys=exact_legal_action_keys,
    )
    payload = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "quotient_graph_id": model["quotient_graph_id"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "planning_source": source,
        "initial_action_key": actions[0],
        "projected_action_path": list(actions),
        "abstract_support_branch_evaluations": plan[
            "projected_planning_compute_events"
        ],
        "embedded_projected_plan": copy.deepcopy(plan),
        "exact_legal_action_keys_at_initial_state": list(exact_legal_action_keys),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "generic_terminal_rules_equal_retained_matched_compiler": True,
        "generic_factor_program_execution_adapter_used": source
        == "COMPILED_FACTOR_PROGRAM_FALLBACK",
        "legacy_shape_specific_planner_execution_adapter_called": False,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": hashlib.sha256(
            successor._V106_PLAN_DOMAIN + canonical_json_bytes(payload)  # noqa: SLF001
        ).hexdigest(),
    }


def _run_base_v122(
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
    proxy = SimpleNamespace(
        previous=v115.previous,
        _memoized_program_plan=v115._memoized_program_plan,  # noqa: SLF001
        _plan_with_branch_cache=_plan_with_branch_cache_v122,
    )
    orderer_namespace = dict(v119.__dict__)
    orderer_namespace["v115"] = proxy
    orderer_function = v119._genesis_authorized_orderer  # noqa: SLF001
    generic_orderer = FunctionType(
        orderer_function.__code__,
        orderer_namespace,
        name=orderer_function.__name__,
        argdefs=orderer_function.__defaults__,
        closure=orderer_function.__closure__,
    )
    generic_orderer.__kwdefaults__ = orderer_function.__kwdefaults__
    sequence_namespace = dict(v113_sequence.__dict__)
    sequence_namespace["_incremental_indexed_orderer"] = generic_orderer
    sequence_function = v113_sequence.run_incremental_abstract_successor_sequence_v113
    generic_sequence = FunctionType(
        sequence_function.__code__,
        sequence_namespace,
        name=sequence_function.__name__,
        argdefs=sequence_function.__defaults__,
        closure=sequence_function.__closure__,
    )
    generic_sequence.__kwdefaults__ = sequence_function.__kwdefaults__
    return generic_sequence(
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


def _canonical_actions(
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[int, FlatRawActionV4]:
    return {
        action.key: FlatRawActionV4(
            action.key,
            tuple(
                action.fields[index]
                for index in candidate.layout.action_canonical_to_raw
            ),
        )
        for action in catalogue
    }


def _verify_generic_model_edges(
    sequence: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    base = sequence["genesis_authorized_base_sequence"]
    models = [
        *base["quotient_models_before_each_episode"],
        *base["quotient_models_after_each_episode"],
    ]
    actions = _canonical_actions(candidate, catalogue)
    checks = rule_checks = 0
    seen: set[str] = set()
    for model in models:
        if model["quotient_graph_id"] in seen:
            continue
        seen.add(model["quotient_graph_id"])
        rules = derive_generic_terminal_rules_v122(
            candidate,
            model["projected_edge_rows"],
            model["projected_terminal_rows"],
        )
        if len(rules) != model["projected_state_width"]:
            _fail("V122 generic terminal-rule width changed")
        rule_checks += len(rules)
        for edge in model["projected_edge_rows"]:
            support = generic_factor_successor_projections_v122(
                candidate,
                tuple(edge["projected_pre"]),
                actions[edge["action_key"]],
            )
            checks += len(support)
            if tuple(edge["projected_post"]) not in support:
                _fail("V122 compiled projected edge escaped the generic program")
    plans = [
        receipt["abstract_plan"]
        for episode in base["episodes"]
        for receipt in episode["abstract_plan_receipts"]
    ]
    direct = [
        row
        for row in plans
        if row["planning_source"] == "COMPILED_FACTOR_PROGRAM_FALLBACK"
    ]
    memoized = [
        row
        for row in plans
        if row["planning_source"] == "COMPILED_FACTOR_PROGRAM_MEMOIZED"
    ]
    if any(
        row.get("generic_factor_program_execution_adapter_used") is not True
        or row.get("legacy_shape_specific_planner_execution_adapter_called") is not False
        or row["embedded_projected_plan"].get(
            "generic_planner_execution_adapter_verified"
        )
        is not True
        for row in direct
    ):
        _fail("V122 direct generic plan receipt changed")
    if any(
        row["source_compiled_factor_program_plan"].get(
            "legacy_shape_specific_planner_execution_adapter_called"
        )
        is not False
        or row["source_compiled_factor_program_plan"].get(
            "generic_terminal_rules_equal_retained_matched_compiler"
        )
        is not True
        for row in memoized
    ):
        _fail("V122 memoized plan lacks a V122 generic planner source")
    return {
        "distinct_compiled_model_count": len(seen),
        "generic_projected_edge_support_checks": checks,
        "generic_terminal_rule_checks": rule_checks,
        "direct_generic_factor_program_plan_count": len(direct),
        "memoized_generic_planner_source_count": len(memoized),
        "every_compiled_model_edge_replayed_by_generic_interpreter": True,
        "every_direct_program_fallback_used_generic_adapter": True,
        "every_memoized_plan_descends_from_v122_generic_planner_source": True,
        "legacy_shape_specific_planner_execution_adapter_called": False,
    }


def run_generic_factor_planner_sequence_v122(
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
    namespace["_run_base"] = _run_base_v122
    function = v119.run_genesis_authorized_program_branch_sequence_v119
    cloned = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = function.__kwdefaults__
    base = cloned(
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
    verification = _verify_generic_model_edges(base, candidate, adapter.catalogue)
    if verification["direct_generic_factor_program_plan_count"] <= 0:
        _fail("V122 workload did not exercise the generic program fallback")
    payload = {
        "schema": "acfqp.generic_factor_planner_sequence.v122",
        "family": adapter.family,
        "seed": adapter.seed,
        "episode_indices": list(episode_indices),
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "generic_planner_base_sequence": base,
        "generic_planner_base_sequence_id": base["sequence_id"],
        "generic_execution_verification": verification,
        "legacy_shape_specific_model_builder_retained_as_matched_control": True,
        "legacy_shape_specific_planner_execution_adapter_present": False,
        "generic_planner_execution_adapter_verified": True,
        "query_local_exact_overlay_exclusively_discharges_safety": True,
        "compiled_model_cache_or_receipt_used_as_safety_authority": False,
        "complete_ground_world_model_synthesized": False,
        "global_exact_dynamics_claimed": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "sequence_id": domains.extension_content_id_v122(
            domains.CONSTRUCTION_K7_GENERIC_FACTOR_PLANNER_SEQUENCE_V122_DOMAIN,
            payload,
        ),
    }


__all__ = ("run_generic_factor_planner_sequence_v122",)
