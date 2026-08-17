"""Candidate synthesis and finite MDL/disagreement stopping for V56.

There is no minimum-label gate and no confirmation block.  A complete
candidate is attempted after every witness-blind support query.  Once one can
be synthesized, the same exact integer score is evaluated in both arms:

    observed structural information
    + registered reusable-factor code credit
    - complete-program description length
    - unresolved discovered-frontier alternatives
    - invalidated-candidate disagreement penalty
    - preregistered confidence reserve.

Only the reusable-factor credit is switched.  All quantities are finite,
integer-valued, and reconstructible from raw observations and the compiled
anonymous program.  This is an auditable model-selection confidence score; it
is not asserted to be a distribution-free statistical confidence interval.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Callable, Mapping, NoReturn

from acfqp.generic_adaptive_joint_factor_residual_synthesizer_v10 import (
    AdaptiveJointCandidateV10,
    exact_candidate_replay_v10,
    synthesize_adaptive_joint_candidate_v10,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
)
from acfqp.generic_layout_factorized_world_model_v5 import DiscoveredLayoutV5
from acfqp.phase3e_ids import canonical_json_bytes


class GenericMDLAdaptiveJointSynthesizerV11Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericMDLAdaptiveJointSynthesizerV11Error(message)


@dataclass(frozen=True, slots=True)
class MDLAdaptiveJointCandidateV11:
    public_document: Mapping[str, Any]
    model: Mapping[str, Any]
    program: Mapping[str, Any]
    layout: DiscoveredLayoutV5
    issuance_rows: tuple[FlatRawTransitionV4, ...]
    _base: AdaptiveJointCandidateV10


def _structural_token_count(candidate: AdaptiveJointCandidateV10) -> int:
    rows = candidate.public_document["assignment_classifications"]
    return (
        len(candidate.layout.state_canonical_to_raw)
        + len(candidate.layout.action_canonical_to_raw)
        + sum(
            1
            + len(row["used_opcodes"])
            + len(row["state_dependencies"])
            + len(row["action_dependencies"])
            + len(row["next_dependencies"])
            + len(row["constant_dependencies"])
            + len(row["relation_dependencies"])
            for row in rows
        )
    )


def _codeword_units_per_token(state_width: int, action_width: int) -> int:
    # The opcode already identifies the state/action namespace, so an index is
    # encoded against the larger namespace rather than charging their sum.
    # Two additional units delimit the opcode and operand payload.
    return 2 + max(state_width, action_width).bit_length()


def _program_fingerprint(candidate: AdaptiveJointCandidateV10) -> str:
    projection = {
        "compiled_assignments": candidate.program["compiled_assignments"],
        "state_structural_colors": list(candidate.layout.state_colors),
        "action_structural_colors": list(candidate.layout.action_colors),
        "assignment_classifications": [
            {
                key: row[key]
                for key in (
                    "target_column",
                    "result_type",
                    "classification",
                    "signature_sha256",
                    "state_dependencies",
                    "action_dependencies",
                    "next_dependencies",
                    "constant_dependencies",
                    "relation_dependencies",
                    "used_opcodes",
                )
            }
            for row in candidate.public_document["assignment_classifications"]
        ],
    }
    return hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def _frontier_profile(
    rows: tuple[FlatRawTransitionV4, ...],
) -> dict[str, int]:
    queried = {(row.pre, row.action.key) for row in rows}
    legal_by_state: dict[tuple[int, ...], tuple[int, ...]] = {}
    for row in rows:
        legal_by_state[row.pre] = row.legal_before
        legal_by_state[row.post] = row.legal_after
    available = {
        (state, key)
        for state, legal in legal_by_state.items()
        for key in legal
    }
    return {
        "queried_state_action_count": len(queried),
        "discovered_state_count": len(legal_by_state),
        "unresolved_discovered_frontier_state_action_count": len(
            available - queried
        ),
        "terminal_observation_count": sum(
            row.terminal_acceptance_after is not None for row in rows
        ),
        "distinct_action_count": len({row.action.key for row in rows}),
    }


def synthesize_mdl_adaptive_joint_candidate_v11(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    factor_library: Mapping[str, Any],
    *,
    support_label_count: int,
    generic_domains: Mapping[str, str],
    candidate_domain: str,
    candidate_content_id: Callable[[str, Any], str],
    minimum_reusable_factor_count: int,
) -> MDLAdaptiveJointCandidateV11:
    base = synthesize_adaptive_joint_candidate_v10(
        rows,
        catalogue,
        factor_library,
        support_label_count=support_label_count,
        generic_domains=generic_domains,
        candidate_domain=candidate_domain,
        candidate_content_id=candidate_content_id,
        minimum_reusable_factor_count=minimum_reusable_factor_count,
    )
    state_width = len(base.layout.state_canonical_to_raw)
    action_width = len(base.layout.action_canonical_to_raw)
    tokens = _structural_token_count(base)
    codeword_units = _codeword_units_per_token(state_width, action_width)
    payload = {
        "schema": "acfqp.generic_mdl_adaptive_joint_candidate.v11",
        "underlying_complete_candidate_id": base.public_document["candidate_id"],
        "support_label_count_at_issuance": support_label_count,
        "raw_transition_count_at_issuance": len(rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "joint_model_id": base.model["joint_model_id"],
        "program_id": base.program["program_id"],
        "layout_id": base.layout.layout_id,
        "program_fingerprint_sha256": _program_fingerprint(base),
        "factorable_reusable_count": base.public_document[
            "factorable_reusable_count"
        ],
        "factorable_novel_count": base.public_document["factorable_novel_count"],
        "residual_schema_bound_count": base.public_document[
            "residual_schema_bound_count"
        ],
        "complete_program_structural_token_count": tokens,
        "self_delimiting_codeword_units_per_token": codeword_units,
        "complete_program_description_units": tokens * codeword_units,
        "minimum_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "complete_program_synthesized_from_raw_observations": True,
        "semantic_names_used": False,
    }
    document = {
        **payload,
        "candidate_id": candidate_content_id(candidate_domain, payload),
    }
    return MDLAdaptiveJointCandidateV11(
        document,
        base.model,
        base.program,
        base.layout,
        rows,
        base,
    )


def exact_candidate_replay_v11(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
) -> dict[str, Any]:
    return exact_candidate_replay_v10(candidate._base, rows, catalogue)


def mdl_confidence_stop_update_v11(
    candidate: MDLAdaptiveJointCandidateV11,
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    *,
    factor_prior_enabled: bool,
    invalidated_candidate_count: int,
    candidate_program_disagreement_count: int,
    factor_signature_credit_units: int,
    confidence_reserve_units: int,
    invalidated_candidate_penalty_units: int,
    minimum_reusable_factor_count: int,
) -> dict[str, Any]:
    if (
        invalidated_candidate_count < 0
        or candidate_program_disagreement_count < 0
        or factor_signature_credit_units <= 0
        or confidence_reserve_units <= 0
        or invalidated_candidate_penalty_units <= 0
        or minimum_reusable_factor_count <= 0
    ):
        _fail("V11 MDL stopping contract changed")
    replay = exact_candidate_replay_v11(candidate, rows, catalogue)
    frontier = _frontier_profile(rows)
    observed_information = (
        len(rows)
        + len({row.pre for row in rows})
        + frontier["distinct_action_count"]
        + frontier["terminal_observation_count"]
    )
    reusable = candidate.public_document["factorable_reusable_count"]
    prior_credit = (
        reusable * factor_signature_credit_units
        if factor_prior_enabled and reusable >= minimum_reusable_factor_count
        else 0
    )
    disagreement_penalty = (
        invalidated_candidate_count + candidate_program_disagreement_count
    ) * invalidated_candidate_penalty_units
    description = candidate.public_document[
        "complete_program_description_units"
    ]
    frontier_penalty = frontier[
        "unresolved_discovered_frontier_state_action_count"
    ]
    margin = (
        observed_information
        + prior_credit
        - description
        - frontier_penalty
        - disagreement_penalty
        - confidence_reserve_units
    )
    replay_disagreement = sum(
        replay[key]
        for key in (
            "legality_mismatch_count",
            "support_mismatch_count",
            "terminal_mismatch_count",
            "evaluation_failure_count",
        )
    )
    return {
        "schema": "acfqp.generic_mdl_confidence_stop_update.v11",
        "candidate_id": candidate.public_document["candidate_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "factorable_reusable_count": reusable,
        "registered_factor_code_credit_units": prior_credit,
        "observed_structural_information_units": observed_information,
        "complete_program_description_units": description,
        "unresolved_frontier_disagreement_units": frontier_penalty,
        "invalidated_candidate_count": invalidated_candidate_count,
        "candidate_program_disagreement_count": (
            candidate_program_disagreement_count
        ),
        "candidate_disagreement_penalty_units": disagreement_penalty,
        "confidence_reserve_units": confidence_reserve_units,
        "confidence_margin_units": margin,
        "current_candidate_replay_disagreement_count": replay_disagreement,
        "frontier_profile": frontier,
        "stopped": replay["exact"] is True and margin >= 0,
        "minimum_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "same_integer_mdl_formula_in_both_arms": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
        "statistical_confidence_interval_claimed": False,
    }


__all__ = (
    "GenericMDLAdaptiveJointSynthesizerV11Error",
    "MDLAdaptiveJointCandidateV11",
    "exact_candidate_replay_v11",
    "mdl_confidence_stop_update_v11",
    "synthesize_mdl_adaptive_joint_candidate_v11",
)
