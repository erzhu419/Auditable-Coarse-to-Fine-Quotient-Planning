"""Compose a transferred role-free terminal template with residual dynamics."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_residual_abstract_planner_v29 import (
    plan_relational_residual_abstract_frontier_v29,
)
from acfqp.generic_role_free_relational_template_v33 import (
    instantiate_role_free_relational_template_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericRoleFreeRelationalWorldModelPlannerV34Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericRoleFreeRelationalWorldModelPlannerV34Error(message)


def plan_role_free_relational_world_model_v34(
    candidate: PartialFactorCandidateV15,
    observed_rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    batch_exact_residual_support: Mapping[str, Any],
    role_free_template_library: Mapping[str, Any],
    target_source_evidence: Mapping[str, Any],
    *,
    maximum_depth: int,
    maximum_terminal_program_candidates_to_try: int = 32,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 32,
) -> dict[str, Any]:
    instantiation = instantiate_role_free_relational_template_v33(
        role_free_template_library,
        target_source_evidence,
        maximum_exact_instantiations=maximum_terminal_program_candidates_to_try,
    )
    terminal = instantiation.get("instantiated_terminal_program")
    if type(terminal) is not dict:
        _fail("V34 target rejected every role-free relational template")
    plan = plan_relational_residual_abstract_frontier_v29(
        candidate,
        observed_rows,
        catalogue,
        initial_raw_state,
        batch_exact_residual_support,
        terminal,
        maximum_depth=maximum_depth,
        maximum_terminal_program_candidates_to_try=(
            maximum_terminal_program_candidates_to_try
        ),
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
    )
    payload = {
        "schema": "acfqp.generic_role_free_relational_world_model_plan.v34",
        "template_library_id": role_free_template_library.get("template_library_id"),
        "target_instantiation_id": instantiation["instantiation_id"],
        "instantiated_terminal_program_id": terminal["terminal_program_id"],
        "batch_exact_multi_residual_id": batch_exact_residual_support.get(
            "batch_exact_multi_residual_id"
        ),
        "abstract_plan": plan,
        "initial_action_key": plan["initial_action_key"],
        "cross_occurrence_role_free_template_reused": True,
        "target_observation_exactness_required_before_planning": True,
        "all_observed_state_coordinates_represented": True,
        "ground_transition_accessed_during_abstract_search": False,
        "abstract_plan_used_as_safety_authority": False,
        "future_unseen_dynamics_authority_present": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "role_free_world_model_plan_id": hashlib.sha256(
            b"acfqp:generic-role-free-relational-world-model-plan:v34\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("plan_role_free_relational_world_model_v34",)
