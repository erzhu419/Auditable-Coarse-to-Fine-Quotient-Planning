"""Producer-free replay of raw-context expression synthesis and planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_local_repair_independent_verifier_v18 as target_v18
from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    select_seeded_outcome_v1,
    state_from_board_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "21.0.0"
PREREGISTRATION_ID = "5a6aa3f7978445c695396bc7b3f4ab708d9f113e6ee0608e44bb255096d632e9"
TARGET_KERNEL_ID = "84d799a915676cee6ded5fac11597386a26c10c213c09a64164eb9a13e811d8a"
SWIPE_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
EXPECTED_CAMPAIGN_ID = "264749b3f9b4bd44d289476f829b0fc88076828ae7747a2a3b6c12fb6af75d4f"
EXPECTED_VERIFICATION_ID = "a43a70731bbc56c24bef3974256c5e1beb73a2c97aeb04336b8796f2bbe1998b"
BASE_RATE = Fraction(1, 10)
HORIZON = 3
RAW_CONTEXT_POOL = (
    ((5, 2, 2, 6, 1, 5, 5, 4, 5, 1, 3, 2, 5, 2, 2, 1), "UP"),
    ((1, 4, 2, 6, 4, 4, 1, 3, 1, 2, 0, 0, 5, 5, 6, 5), "RIGHT"),
    ((5, 2, 2, 6, 4, 1, 0, 6, 0, 4, 3, 2, 5, 5, 3, 2), "UP"),
    ((0, 1, 5, 2, 0, 0, 3, 2, 0, 0, 0, 0, 2, 2, 4, 1), "LEFT"),
    ((3, 4, 6, 1, 6, 3, 2, 2, 3, 6, 2, 5, 0, 3, 2, 0), "DOWN"),
    ((0, 5, 3, 1, 6, 2, 6, 0, 5, 5, 5, 0, 6, 0, 5, 1), "DOWN"),
    ((0, 0, 4, 5, 6, 0, 2, 0, 1, 0, 0, 1, 2, 1, 0, 0), "LEFT"),
    ((0, 5, 4, 0, 0, 5, 0, 2, 0, 0, 6, 0, 2, 0, 5, 3), "RIGHT"),
)
TARGET_BOARDS = (
    (3, 2, 1, 0, 3, 0, 3, 0, 4, 6, 4, 1, 4, 3, 5, 2),
    (2, 1, 0, 3, 0, 5, 4, 4, 3, 2, 6, 1, 3, 0, 3, 0),
    (2, 3, 3, 0, 2, 1, 0, 0, 2, 1, 5, 0, 6, 0, 3, 5),
)
TARGET_SEEDS = tuple(
    f"standard-2048-v180-expression-program-target-{index:02d}-20260813"
    for index in range(3)
)
Candidate = tuple[str, dict[str, Any], int, Fraction, tuple[Fraction, ...]]


class ConstructionK7Standard2048ExpressionProgramIndependentVerifierV21Error(ValueError):
    """Campaign differs from independent expression, acquisition, or plan replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExpressionProgramIndependentVerifierV21Error(message)


def _verify_id(document: Any, id_key: str, domain: str, label: str) -> dict[str, Any]:
    if type(document) is not dict:
        _fail(f"{label} document changed")
    payload = {key: value for key, value in document.items() if key != id_key}
    if document.get(id_key) != content_id(domain, payload):
        _fail(f"{label} identity changed")
    return document


def _state(document: Any) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state schema changed")
    state = Swipe2048State(tuple(document["board_ranks"]), Swipe2048Status(document["status"]))
    if state_from_board_v1(state.board) != state:
        _fail("state status changed")
    return state


def _adjacent_equal_nonzero(board: tuple[int, ...]) -> int:
    return sum(
        1
        for row in range(4)
        for column in range(4)
        for dr, dc in ((0, 1), (1, 0))
        if row + dr < 4
        and column + dc < 4
        and board[row * 4 + column]
        and board[row * 4 + column] == board[(row + dr) * 4 + column + dc]
    )


def _expressions(
    pre_board: tuple[int, ...], action: str, post_board: tuple[int, ...],
    merge_score: int, constants: tuple[int, ...],
) -> list[dict[str, Any]]:
    result = []
    for source, board in (
        ("PRE_BOARD_RANKS", pre_board),
        ("POST_SWIPE_BOARD_RANKS", post_board),
    ):
        for constant in constants:
            result.append(
                {
                    "expression_key": f"COUNT_EQ({source},{constant})",
                    "expression_ast": {
                        "operator": "COUNT_EQ", "vector_source": source, "constant": constant
                    },
                    "value": board.count(constant),
                }
            )
        for operator, value in (
            ("MAX", max(board)),
            ("SUM", sum(board)),
            ("DISTINCT_NONZERO_COUNT", len(set(board) - {0})),
            ("ORTHOGONAL_ADJACENT_EQUAL_NONZERO_PAIR_COUNT", _adjacent_equal_nonzero(board)),
        ):
            result.append(
                {
                    "expression_key": f"{operator}({source})",
                    "expression_ast": {"operator": operator, "vector_source": source},
                    "value": value,
                }
            )
    result.extend(
        (
            {
                "expression_key": "MERGE_SCORE",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "MERGE_SCORE"},
                "value": merge_score,
            },
            {
                "expression_key": "ACTION_ORDINAL",
                "expression_ast": {"operator": "RAW_SCALAR", "source": "ACTION_ORDINAL"},
                "value": tuple(action_.value for action_ in ACTION_ORDER).index(action),
            },
        )
    )
    return result


def _pool_expected() -> dict[str, Any]:
    raw = []
    constants = set()
    for ordinal, (board, action) in enumerate(RAW_CONTEXT_POOL):
        post, merge = swipe_v14.apply_independently_replayed_swipe_program_v14(board, action)
        raw.append((ordinal, board, action, post, merge))
        constants.update(board)
        constants.update(post)
    frozen_constants = tuple(sorted(constants))
    rows = []
    for ordinal, board, action, post, merge in raw:
        payload = {
            "pool_ordinal": ordinal,
            "pre_state_board_ranks": list(board),
            "action": action,
            "post_swipe_board_ranks": list(post),
            "merge_score": merge,
            "expression_values": _expressions(
                board, action, post, merge, frozen_constants
            ),
        }
        rows.append(
            {
                **payload,
                "structural_context_sha256": hashlib.sha256(
                    canonical_json_bytes(payload)
                ).hexdigest(),
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_structural_context_pool.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "swipe_world_model_id": SWIPE_WORLD_MODEL_ID,
        "observed_raw_rank_constants": list(frozen_constants),
        "rows": rows,
        "context_count": 8,
        "expression_count_per_context": len(rows[0]["expression_values"]),
        "all_expression_values_frozen_before_first_target_probability_query": True,
        "target_probability_or_formula_present": False,
        "named_empty_count_or_v20_feature_basis_present": False,
    }
    return {
        **payload,
        "structural_context_pool_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN, payload
        ),
    }


def _expression_maps(pool: dict[str, Any]) -> tuple[tuple[str, dict[str, Any], tuple[int, ...]], ...]:
    first = pool["rows"][0]["expression_values"]
    return tuple(
        (
            expression["expression_key"],
            expression["expression_ast"],
            tuple(row["expression_values"][index]["value"] for row in pool["rows"]),
        )
        for index, expression in enumerate(first)
    )


def _candidates_expected(
    pool: dict[str, Any], override: Fraction
) -> tuple[list[dict[str, Any]], tuple[Candidate, ...]]:
    artifacts = []
    native = []
    ordinal = 0
    for key, ast, values in _expression_maps(pool):
        for threshold in sorted(set(values)):
            predictions = tuple(override if value <= threshold else BASE_RATE for value in values)
            if len(set(predictions)) == 1:
                continue
            payload = {
                "schema": "acfqp.standard_2048_expression_candidate.v21",
                "schema_version": SCHEMA_VERSION,
                "expression_program_preregistration_id": PREREGISTRATION_ID,
                "structural_context_pool_id": pool["structural_context_pool_id"],
                "candidate_ordinal": ordinal,
                "expression_key": key,
                "expression_ast": ast,
                "threshold": threshold,
                "program_schema": "IF_EXPRESSION_LE_THRESHOLD_THEN_OVERRIDE_ELSE_BASE",
                "base_rank_two_probability": BASE_RATE,
                "override_rank_two_probability": override,
                "expression_values_over_frozen_pool": list(values),
                "predictions_over_frozen_pool": list(predictions),
                "constant_prediction_candidate": False,
                "expression_and_threshold_generated_from_structural_pool": True,
            }
            artifacts.append(
                {
                    **payload,
                    "expression_candidate_id": content_id(
                        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN,
                        payload,
                    ),
                }
            )
            native.append((key, ast, threshold, override, predictions))
            ordinal += 1
    return artifacts, tuple(native)


def _acquisition_expected(
    pool: dict[str, Any], pool_ordinal: int, query_ordinal: int,
    before: int | None, after: int, generated: bool,
) -> dict[str, Any]:
    row = pool["rows"][pool_ordinal]
    count = row["post_swipe_board_ranks"].count(0)
    payload = {
        "schema": "acfqp.standard_2048_expression_acquisition.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "structural_context_pool_id": pool["structural_context_pool_id"],
        "query_ordinal": query_ordinal,
        "pool_ordinal": pool_ordinal,
        "structural_context_sha256": row["structural_context_sha256"],
        "observed_rank_two_probability": target_v18.independently_replay_rank_two_probability_v18(count),
        "candidate_count_before": before,
        "candidate_count_after": after,
        "candidates_generated_after_this_query": generated,
        "context_and_all_expression_values_frozen_before_query": True,
        "full_state_action_outcome_row_materialized": False,
    }
    return {
        **payload,
        "expression_acquisition_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN, payload
        ),
    }


def _acquire_expected(
    pool: dict[str, Any], candidates: tuple[Candidate, ...]
) -> tuple[list[dict[str, Any]], Candidate]:
    first = target_v18.independently_replay_rank_two_probability_v18(
        pool["rows"][0]["post_swipe_board_ranks"].count(0)
    )
    remaining = tuple(candidate for candidate in candidates if candidate[4][0] == first)
    queries = [0]
    rows = [_acquisition_expected(pool, 0, 0, None, len(remaining), True)]
    while len(remaining) > 1:
        choices = []
        for ordinal in range(8):
            if ordinal in queries:
                continue
            buckets: dict[Fraction, int] = {}
            for candidate in remaining:
                value = candidate[4][ordinal]
                buckets[value] = buckets.get(value, 0) + 1
            if len(buckets) > 1:
                choices.append((max(buckets.values()), ordinal))
        if not choices:
            _fail("independent active acquisition cannot separate candidates")
        _, ordinal = min(choices)
        queries.append(ordinal)
        before = remaining
        observed = target_v18.independently_replay_rank_two_probability_v18(
            pool["rows"][ordinal]["post_swipe_board_ranks"].count(0)
        )
        remaining = tuple(candidate for candidate in remaining if candidate[4][ordinal] == observed)
        rows.append(
            _acquisition_expected(pool, ordinal, len(rows), len(before), len(remaining), False)
        )
    if len(rows) != 4 or len(remaining) != 1:
        _fail("independent active acquisition result changed")
    return rows, remaining[0]


def _proposal_expected(
    pool: dict[str, Any], artifacts: list[dict[str, Any]],
    acquisitions: list[dict[str, Any]], selected: Candidate,
) -> dict[str, Any]:
    selected_artifact = next(
        row for row in artifacts
        if row["expression_key"] == selected[0]
        and row["expression_ast"] == selected[1]
        and row["threshold"] == selected[2]
    )
    payload = {
        "schema": "acfqp.standard_2048_expression_proposal.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "structural_context_pool_id": pool["structural_context_pool_id"],
        "expression_candidate_artifacts": artifacts,
        "expression_candidate_count": len(artifacts),
        "expression_acquisition_ids": [row["expression_acquisition_id"] for row in acquisitions],
        "queried_pool_ordinals": [row["pool_ordinal"] for row in acquisitions],
        "version_space_counts_after_queries": [row["candidate_count_after"] for row in acquisitions],
        "selected_expression_candidate_id": selected_artifact["expression_candidate_id"],
        "selected_expression_key": selected[0],
        "selected_expression_ast": selected[1],
        "selected_threshold": selected[2],
        "selected_base_rank_two_probability": BASE_RATE,
        "selected_override_rank_two_probability": selected[3],
        "unique_program_consistent_with_all_queried_contexts": True,
        "named_empty_count_feature_supplied_to_synthesizer": False,
        "proposal_frozen_before_target_formula_access": True,
        "proposal_has_world_model_authority": False,
    }
    return {
        **payload,
        "expression_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN, payload
        ),
    }


def _proof_expected(proposal: dict[str, Any]) -> dict[str, Any]:
    if proposal["selected_expression_ast"] != {
        "operator": "COUNT_EQ", "vector_source": "POST_SWIPE_BOARD_RANKS", "constant": 0
    }:
        _fail("independently selected expression does not normalize to empty count")
    threshold = proposal["selected_threshold"]
    override = proposal["selected_override_rank_two_probability"]
    rows = []
    for count in range(1, 17):
        predicted = override if count <= threshold else BASE_RATE
        target = target_v18.independently_replay_rank_two_probability_v18(count)
        rows.append(
            {
                "post_swipe_empty_count": count,
                "normalized_expression_value": count,
                "predicted_rank_two_probability": predicted,
                "target_rank_two_probability": target,
                "exact_match": predicted == target,
            }
        )
    payload = {
        "schema": "acfqp.standard_2048_expression_proof.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "expression_proposal_id": proposal["expression_proposal_id"],
        "proposal_frozen_before_target_formula_access": True,
        "normalization_rewrite": "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)=POST_SWIPE_EMPTY_COUNT",
        "proof_rows": rows,
        "proof_row_count": 16,
        "proof_mismatch_count": 0,
        "exact_formula_equivalence_proved": True,
        "proof_rows_not_counted_as_target_probability_queries": True,
    }
    return {
        **payload,
        "expression_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN, payload
        ),
    }


def _world_expected(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_expression_world_model.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "expression_proposal_id": proposal["expression_proposal_id"],
        "expression_proof_id": proof["expression_proof_id"],
        "swipe_world_model_id": SWIPE_WORLD_MODEL_ID,
        "selected_expression_ast": proposal["selected_expression_ast"],
        "selected_threshold": proposal["selected_threshold"],
        "base_rank_two_probability": BASE_RATE,
        "override_rank_two_probability": proposal["selected_override_rank_two_probability"],
        "normalized_planner_feature": "POST_SWIPE_EMPTY_COUNT",
        "exact_over_registered_target_kernel": True,
        "reusable_across_fresh_states_actions_and_episodes": True,
        "serialized_full_state_action_table_present": False,
        "open_ended_expression_language_claimed": False,
    }
    return {
        **payload,
        "expression_world_model_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN, payload
        ),
    }


def _root_rows(state: Swipe2048State) -> list[dict[str, Any]]:
    return [
        {
            "action": action,
            "expected_merge_score": score,
            "loss_probability_within_horizon": loss,
        }
        for action, score, loss in target_v18.independently_replay_target_root_values_v18(state)
    ]


def _best_action(rows: list[dict[str, Any]]) -> str:
    order = tuple(action.value for action in ACTION_ORDER)
    return max(
        rows,
        key=lambda row: (
            row["expected_merge_score"],
            -row["loss_probability_within_horizon"],
            -order.index(row["action"]),
        ),
    )["action"]


def _verify_episodes(
    observed: Any, world_model_id: str
) -> tuple[int, int]:
    if type(observed) is not list or len(observed) != 3:
        _fail("episode inventory changed")
    decisions = 0
    for episode_index, episode in enumerate(observed):
        _verify_id(
            episode,
            "expression_episode_id",
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN,
            "episode",
        )
        state = state_from_board_v1(TARGET_BOARDS[episode_index])
        if (
            episode.get("episode_index") != episode_index
            or episode.get("execution_seed") != TARGET_SEEDS[episode_index]
            or _state(episode.get("initial_state")) != state
            or episode.get("expression_world_model_id") != world_model_id
        ):
            _fail("episode identity changed")
        rows = episode.get("decisions")
        if type(rows) is not list or len(rows) != 4:
            _fail("episode decision inventory changed")
        for decision_index, decision in enumerate(rows):
            certificate = _verify_id(
                decision.get("certificate"),
                "expression_plan_certificate_id",
                CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN,
                "certificate",
            )
            expected_rows = _root_rows(state)
            selected = _best_action(expected_rows)
            if (
                decision.get("decision_index") != decision_index
                or _state(decision.get("predecision_state")) != state
                or certificate.get("root_action_exact_values") != expected_rows
                or certificate.get("selected_action") != selected
                or certificate.get("root_state") != decision.get("predecision_state")
                or certificate.get("planning_horizon") != HORIZON
                or certificate.get("operational_target_probability_query_count") != 0
                or certificate.get("operational_ground_state_action_row_count") != 0
                or certificate.get("target_transition_accessed_before_certificate_freeze") is not False
                or certificate.get("status") != "CERTIFIED_RAW_CONTEXT_EXPRESSION_WORLD_MODEL_H3"
            ):
                _fail("expression plan certificate differs from independent root replay")
            control = decision.get("matched_cold_target_ground")
            if (
                type(control) is not dict
                or control.get("root_action_exact_values") != expected_rows
                or control.get("selected_action") != selected
                or control.get("lane") != "STANDALONE_EVALUATION_ONLY"
                or control.get("route_or_certificate_authority") is not False
                or decision.get("route") != "EXACT_RAW_CONTEXT_EXPRESSION_MODEL_CERTIFIED"
                or decision.get("all_root_action_values_exactly_equal") is not True
                or decision.get("selected_action_exact_value_and_loss_equivalent") is not True
                or decision.get("certificate_frozen_before_cold_evaluation_and_target_transition") is not True
            ):
                _fail("expression target comparison lane changed")
            outcome, tape = select_seeded_outcome_v1(
                target_v18.apply_independently_replayed_target_outcomes_v18(
                    state, Swipe2048Action(selected)
                ),
                seed=TARGET_SEEDS[episode_index],
                decision_index=decision_index,
            )
            if (
                decision.get("executed_action") != selected
                or decision.get("execution_tape_sha256") != tape
                or _state(decision.get("executed_next_state")) != outcome.next_state
                or decision.get("execution_transition_used_to_modify_world_model") is not False
            ):
                _fail("expression target transition changed")
            state = outcome.next_state
            decisions += 1
        if (
            _state(episode.get("final_state")) != state
            or episode.get("decision_count") != 4
            or episode.get("expression_model_certificate_count") != 4
            or episode.get("local_ground_recovery_count") != 0
            or episode.get("all_root_action_values_exactly_equal") is not True
        ):
            _fail("expression episode closure changed")
    return len(observed), decisions


def _verify_preregistration(document: Any) -> None:
    row = _verify_id(
        document,
        "expression_program_preregistration_id",
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN,
        "preregistration",
    )
    if (
        row["expression_program_preregistration_id"] != PREREGISTRATION_ID
        or row.get("outcome_fields_present") is not False
        or row.get("target_probability_query_count") != 0
        or row.get("expression_or_program_selected") is not False
        or row.get("open_ended_coordinate_invention_claimed") is not False
    ):
        _fail("expression preregistration locks changed")


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048ExpressionProgramIndependentVerificationV21:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("expression verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("expression verification bytes changed")
        payload = {
            key: value for key, value in document.items() if key != "expression_verification_id"
        }
        if (
            document.get("expression_verification_id") != self.verification_id
            or document.get("expression_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("expression verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("expression verification is not an object")
        return document


def verify_standard_2048_expression_program_bytes_independently_v21(
    canonical_bytes: bytes,
) -> Standard2048ExpressionProgramIndependentVerificationV21:
    try:
        observed = loads_canonical_json(canonical_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048ExpressionProgramIndependentVerifierV21Error(
            "expression campaign bytes are not canonical"
        ) from error
    root = _verify_id(
        observed,
        "expression_campaign_id",
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN,
        "campaign",
    )
    if root["expression_campaign_id"] != EXPECTED_CAMPAIGN_ID:
        _fail("expression campaign identity changed")
    _verify_preregistration(root.get("expression_program_preregistration"))
    pool = _pool_expected()
    if root.get("structural_context_pool") != pool:
        _fail("structural expression pool differs from independent replay")
    first = target_v18.independently_replay_rank_two_probability_v18(
        pool["rows"][0]["post_swipe_board_ranks"].count(0)
    )
    artifacts, candidates = _candidates_expected(pool, first)
    acquisitions, selected = _acquire_expected(pool, candidates)
    if root.get("expression_acquisitions") != acquisitions:
        _fail("active expression acquisitions differ from independent replay")
    proposal = _proposal_expected(pool, artifacts, acquisitions, selected)
    if root.get("expression_proposal") != proposal:
        _fail("expression proposal differs from independent synthesis")
    proof = _proof_expected(proposal)
    if root.get("expression_proof") != proof:
        _fail("expression exact proof differs from independent replay")
    world = _world_expected(proposal, proof)
    if root.get("expression_world_model") != world:
        _fail("expression world model differs from independent reconstruction")
    episode_count, decision_count = _verify_episodes(
        root.get("episodes"), world["expression_world_model_id"]
    )
    if (
        episode_count != 3
        or decision_count != 12
        or root.get("target_probability_query_count") != 4
        or root.get("queried_pool_ordinals") != [0, 2, 1, 3]
        or root.get("version_space_counts_after_queries") != [31, 14, 7, 1]
        or root.get("generated_primitive_expression_count") != 26
        or root.get("generated_expression_program_candidate_count") != 78
        or root.get("selected_expression_key") != "COUNT_EQ(POST_SWIPE_BOARD_RANKS,0)"
        or root.get("selected_threshold") != 4
        or root.get("retained_query_reduction_against_no_prior") != 6
        or root.get("expression_query_fraction_of_no_prior") != Fraction(2, 5)
        or root.get("named_empty_count_or_v20_feature_basis_supplied_to_synthesizer") is not False
        or root.get("v20_result_used_during_v21_grammar_and_fixture_design") is not True
        or root.get("blind_new_target_discovery_claimed") is not False
        or root.get("open_ended_expression_or_coordinate_invention_completed") is not False
        or root.get("broad_or_physical_iid_sample_efficiency_claimed") is not False
        or root.get("official_execution_allowed") is not False
    ):
        _fail("expression campaign aggregate or claim boundary changed")
    payload = {
        "schema": "acfqp.standard_2048_expression_independent_verification.v21",
        "schema_version": SCHEMA_VERSION,
        "expression_program_preregistration_id": PREREGISTRATION_ID,
        "expression_campaign_id": EXPECTED_CAMPAIGN_ID,
        "structural_context_pool_id": pool["structural_context_pool_id"],
        "expression_proposal_id": proposal["expression_proposal_id"],
        "expression_proof_id": proof["expression_proof_id"],
        "expression_world_model_id": world["expression_world_model_id"],
        "twenty_six_primitive_expressions_independently_generated": True,
        "seventy_eight_program_candidates_independently_generated": True,
        "four_minimax_queries_independently_replayed": True,
        "unique_count_eq_post_zero_expression_independently_selected": True,
        "all_16_formula_rows_independently_proved": True,
        "all_12_h3_root_values_actions_and_transitions_independently_replayed": True,
        "evaluation_only_compute_counter_aggregates_independently_verified": False,
        "retained_six_query_difference_against_v19_no_prior_verified": True,
        "blind_discovery_or_open_ended_expression_invention_verified": False,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "full_game_or_broad_world_model_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN, payload
    )
    if EXPECTED_VERIFICATION_ID != "0" * 64 and verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen expression verification identity changed")
    return Standard2048ExpressionProgramIndependentVerificationV21(
        _ISSUER,
        canonical_json_bytes({**payload, "expression_verification_id": verification_id}),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "ConstructionK7Standard2048ExpressionProgramIndependentVerifierV21Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048ExpressionProgramIndependentVerificationV21",
    "verify_standard_2048_expression_program_bytes_independently_v21",
)
