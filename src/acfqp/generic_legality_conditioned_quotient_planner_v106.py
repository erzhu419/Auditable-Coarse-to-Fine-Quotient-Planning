"""Condition a fallible quotient plan on already-certified local legality."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_abstract_partial_agreement_shield_v99 import (
    shield_abstract_action_order_v99,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_observation_quotient_graph_v105 import (
    verify_observation_quotient_graph_v105,
)
from acfqp.generic_partial_factor_proposal_v15 import (
    PartialFactorCandidateV15,
    plan_partial_factor_observation_graph_v15,
    plan_partial_factor_program_v15,
)
from acfqp.phase3e_ids import canonical_json_bytes


_PLAN_DOMAIN = b"acfqp:generic-legality-conditioned-quotient-plan:v106\x00"


class GenericLegalityConditionedQuotientPlannerV106Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericLegalityConditionedQuotientPlannerV106Error(message)


def plan_legality_conditioned_quotient_v106(
    model: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    exact_legal_action_keys: tuple[int, ...],
    *,
    legality_support_source: str,
    legality_failure_index: int | None,
    maximum_depth: int,
) -> dict[str, Any]:
    verified = verify_observation_quotient_graph_v105(
        model, candidate, observed_rows, catalogue
    )
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
            legality_support_source
            in (
                "CERTIFICATE_LOCAL_LEGALITY_AFTER_FAILURE",
                "CERTIFICATE_LOCAL_LEGALITY_FROM_TRANSITION_AFTER_FAILURE",
            )
            and (type(legality_failure_index) is not int or legality_failure_index < 0)
        )
        or maximum_depth <= 0
    ):
        _fail("V106 legality-conditioned plan inventory changed")
    canonical = tuple(
        initial_raw_state[index]
        for index in candidate.layout.state_canonical_to_raw
    )
    targets = tuple(row["target_column"] for row in candidate.assignments)
    projected = tuple(canonical[target] for target in targets)
    forbidden = frozenset(
        (projected, action.key)
        for action in catalogue
        if action.key not in exact_legal_action_keys
    )
    try:
        plan = plan_partial_factor_observation_graph_v15(
            candidate,
            observed_rows,
            catalogue,
            initial_raw_state,
            forbidden_projection_actions=forbidden,
        )
        source = "OBSERVATION_QUOTIENT_GRAPH"
    except Exception as first_error:
        if not first_error.__class__.__module__.startswith("acfqp.generic_"):
            raise
        try:
            plan = plan_partial_factor_program_v15(
                candidate,
                observed_rows,
                catalogue,
                initial_raw_state,
                forbidden_projection_actions=forbidden,
                maximum_depth=maximum_depth,
            )
            source = "COMPILED_FACTOR_PROGRAM_FALLBACK"
        except Exception as second_error:
            if not second_error.__class__.__module__.startswith("acfqp.generic_"):
                raise
            _fail("V106 quotient model found no legality-conditioned continuation")
    actions = plan.get("action_keys")
    if (
        type(actions) is not list
        or not actions
        or actions[0] not in exact_legal_action_keys
        or any(type(key) is not int for key in actions)
    ):
        _fail("V106 legality-conditioned action path changed")
    shield = shield_abstract_action_order_v99(
        abstract_proposal=(actions[0],),
        partial_proposal=(actions[0],),
        legal_action_keys=exact_legal_action_keys,
    )
    payload = {
        "schema": "acfqp.generic_legality_conditioned_quotient_plan.v106",
        "quotient_graph_id": verified["quotient_graph_id"],
        "partial_candidate_id": candidate.public_document["candidate_id"],
        "planning_source": source,
        "initial_action_key": actions[0],
        "projected_action_path": list(actions),
        "abstract_support_branch_evaluations": plan.get(
            "projected_planning_compute_events", 0
        ),
        "embedded_projected_plan": plan,
        "exact_legal_action_keys_at_initial_state": list(exact_legal_action_keys),
        "legality_support_source": legality_support_source,
        "legality_failure_index": legality_failure_index,
        "agreement_shield_receipt": shield,
        "initial_illegal_actions_forbidden_in_abstract_search": True,
        "ground_legality_used_only_after_existing_support_or_failed_certificate": True,
        "ground_transition_accessed_during_abstract_search": False,
        "query_local_exact_overlay_remains_only_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "legality_conditioned_quotient_plan_id": hashlib.sha256(
            _PLAN_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("plan_legality_conditioned_quotient_v106",)
