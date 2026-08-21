"""Audit whether exact ground work only certified abstractly proposed actions."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_applicability_conditioned_planner_v58 import (
    plan_applicability_conditioned_model_v58,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


_AUDIT_DOMAIN = b"acfqp:generic-abstract-proposal-primary-audit:v63\x00"


class GenericAbstractProposalPrimaryAuditV63Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAbstractProposalPrimaryAuditV63Error(message)


def audit_abstract_proposal_primary_v63(
    episode: Mapping[str, Any],
    model: Mapping[str, Any],
    applicability_program: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    maximum_abstract_depth: int,
    maximum_abstract_support_branch_evaluations: int,
    abstract_support_feasible_beam_width: int,
) -> dict[str, Any]:
    if (
        type(episode) is not dict
        or episode.get("arm") != "APPLICABILITY_CONDITIONED_WORLD_MODEL"
        or episode.get("success") is not True
        or type(candidate) is not PartialFactorCandidateV15
        or type(catalogue) is not tuple
        or not catalogue
    ):
        _fail("V63 proposal-primary audit inventory changed")
    query_rows: dict[tuple[int, ...], list[int]] = {}
    ordered_states = []
    for distinction in episode.get("local_distinctions", []):
        if distinction.get("distinction_kind") != "QUERY_LOCAL_EXACT_TRANSITION_SUPPORT":
            continue
        raw = tuple(distinction["raw_state"])
        if raw not in query_rows:
            query_rows[raw] = []
            ordered_states.append(raw)
        query_rows[raw].append(distinction["action_key"])
    if not query_rows:
        _fail("V63 episode carried no exact transition certificates")
    rows = []
    total_compute = 0
    mismatches = 0
    alternative_queries = 0
    for index, raw in enumerate(ordered_states):
        plan = plan_applicability_conditioned_model_v58(
            model,
            applicability_program,
            candidate,
            catalogue,
            raw,
            maximum_depth=maximum_abstract_depth,
            maximum_support_branch_evaluations=(
                maximum_abstract_support_branch_evaluations
            ),
            support_feasible_beam_width=abstract_support_feasible_beam_width,
        )
        queries = query_rows[raw]
        proposal = plan["initial_action_key"]
        match = queries[0] == proposal
        mismatches += not match
        alternative_queries += max(0, len(queries) - 1)
        total_compute += plan["abstract_support_branch_evaluations"]
        rows.append(
            {
                "state_index": index,
                "raw_state": list(raw),
                "abstract_proposed_action_key": proposal,
                "exactly_certified_action_keys_in_query_order": queries,
                "first_exactly_certified_action_matches_abstract_proposal": match,
                "non_proposed_alternative_action_query_count": max(
                    0, len(queries) - 1
                ),
                "abstract_plan_sha256": hashlib.sha256(
                    canonical_json_bytes(plan)
                ).hexdigest(),
                "abstract_support_branch_evaluations": plan[
                    "abstract_support_branch_evaluations"
                ],
            }
        )
    payload = {
        "schema": "acfqp.generic_abstract_proposal_primary_audit.v63",
        "episode_id": episode["episode_id"],
        "source_model_id": model["projected_disagreement_successor_model_id"],
        "action_applicability_program_id": applicability_program[
            "action_applicability_program_id"
        ],
        "projected_partial_candidate_id": candidate.public_document["candidate_id"],
        "audited_exact_transition_state_count": len(rows),
        "replayed_abstract_plan_count": len(rows),
        "proposal_mismatch_count": mismatches,
        "non_proposed_alternative_action_query_count": alternative_queries,
        "per_state_audit": rows,
        "replayed_abstract_planning_compute_events": total_compute,
        "every_exactly_certified_action_was_abstractly_proposed_first": (
            mismatches == 0
        ),
        "ground_search_over_non_proposed_actions_observed": alternative_queries > 0,
        "ground_queries_used_only_to_certify_abstractly_proposed_policy": (
            mismatches == 0 and alternative_queries == 0
        ),
        "abstract_model_used_as_safety_authority": False,
        "exact_query_local_certificate_remained_only_safety_authority": True,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "audit_id": hashlib.sha256(
            _AUDIT_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("audit_abstract_proposal_primary_v63",)
