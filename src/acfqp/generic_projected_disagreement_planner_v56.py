"""Plan with a verified V56 model through its exact V54 semantic view."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_contextual_ordinal_planner_v54 import (
    plan_contextual_ordinal_model_v54,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_projected_disagreement_model_compiler_v56 import (
    _v54_view,
    verify_projected_disagreement_model_v56,
)


def plan_projected_disagreement_model_v56(
    model: Mapping[str, Any],
    target_candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    initial_raw_state: tuple[int, ...],
    *,
    maximum_depth: int,
    maximum_robust_state_depth_evaluations: int = 4096,
    maximum_support_branch_evaluations: int = 1_000_000,
    support_feasible_beam_width: int = 64,
) -> dict[str, Any]:
    verified = verify_projected_disagreement_model_v56(model)
    inherited = plan_contextual_ordinal_model_v54(
        _v54_view(verified),
        target_candidate,
        catalogue,
        initial_raw_state,
        maximum_depth=maximum_depth,
        maximum_robust_state_depth_evaluations=maximum_robust_state_depth_evaluations,
        maximum_support_branch_evaluations=maximum_support_branch_evaluations,
        support_feasible_beam_width=support_feasible_beam_width,
    )
    result = copy.deepcopy(inherited)
    result["schema"] = "acfqp.generic_projected_disagreement_plan.v56"
    result.pop("contextual_ordinal_successor_model_id")
    result["projected_disagreement_successor_model_id"] = verified[
        "projected_disagreement_successor_model_id"
    ]
    result["v54_semantic_planner_reused_through_exact_nonpersistent_view"] = True
    return result


__all__ = ("plan_projected_disagreement_model_v56",)
