"""Propose and exhaustively prove a reusable standard-2048 spawn program."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_v14 as swipe_v14
from acfqp import construction_k7_standard_2048_spawn_program_preregistration_v16 as pre
from acfqp.domains.standard_2048 import (
    SPAWN_DISTRIBUTION,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


SCHEMA_VERSION = pre.SCHEMA_VERSION
PROFILE_KEY = "construction_k7_standard_2048_spawn_program_v16"
STREAM_DOMAIN = b"acfqp:standard-2048-spawn-program-observation-tape:v16\x00"
PROOF_TRACE_DOMAIN = b"acfqp:standard-2048-spawn-program-support-proof-trace:v16\x00"
MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION = 4096
SELECTED_CANDIDATE_KEY = "UNIFORM_OVER_EMPTY_CELLS__RANK_TWO_1_OVER_10"
SELECTED_RANK_DISTRIBUTION = (
    (1, Fraction(9, 10)),
    (2, Fraction(1, 10)),
)
EXPECTED_SOURCE_ARCHIVE_ID = "630af9f4bff7d0581c809f5990a27f5e9ad432a1cdd94159bd8179db1882c3b5"
EXPECTED_VALIDATION_ARCHIVE_ID = "45ba6ebfb190f71f3fe4227d018b57b4ace0a29490d71b075bc427cccb163b6c"
EXPECTED_PROPOSAL_ID = "32856e6557710cb7a97f40400a5b5cb8f34afb7851b25f966e595df579437ebf"
EXPECTED_SELECTED_CANDIDATE_ID = "7bc3f2c1eefdc78d5b3386497e31dea4fb8b355110f4eee7708aedd9a5bbd645"
EXPECTED_SUPPORT_PROOF_ID = "973dd6629b6bebbaad932f0c73b976a906a4844fa44180a04f37d1eaf54e9367"
EXPECTED_PROOF_TRACE_SHA256 = "5cca2c8e3de74d692f417fb6e82be29223b9da00988285179cb0579c6a61f22f"
EXPECTED_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
EXPECTED_CAMPAIGN_ID = "c6d490d140676a9d045e678f1484635d925a655f4c67605afde28690e246aa53"
EXPECTED_CANONICAL_BYTE_COUNT = 309872
EXPECTED_CANONICAL_SHA256 = "cdae7c33d41375be5abfd2c7654ef97b0c320d66cf80962bcc178f94a8afa05b"


class ConstructionK7Standard2048SpawnProgramV16Error(ValueError):
    """Observation, proposal, proof, or composed model changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SpawnProgramV16Error(message)


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _draw_digest(
    seed: str, observation_index: int, attempt: int, label: str, counter: int
) -> bytes:
    return hashlib.sha256(
        STREAM_DOMAIN
        + seed.encode("utf-8")
        + b"\x00"
        + str(observation_index).encode("ascii")
        + b"\x00"
        + str(attempt).encode("ascii")
        + b"\x00"
        + label.encode("ascii")
        + b"\x00"
        + str(counter).encode("ascii")
    ).digest()


def _uniform_below(
    seed: str,
    observation_index: int,
    attempt: int,
    label: str,
    bound: int,
) -> tuple[int, tuple[bytes, ...]]:
    if type(bound) is not int or bound <= 0:
        _fail("uniform draw bound changed")
    scale = 1 << 256
    limit = scale - (scale % bound)
    consumed = []
    counter = 0
    while True:
        digest = _draw_digest(seed, observation_index, attempt, label, counter)
        consumed.append(digest)
        value = int.from_bytes(digest, "big")
        if value < limit:
            return value % bound, tuple(consumed)
        counter += 1


def _sample_board_and_action(
    seed: str, observation_index: int, attempt: int
) -> tuple[Swipe2048State, Swipe2048Action, tuple[bytes, ...]] | None:
    draws = []
    occupied_offset, consumed = _uniform_below(
        seed, observation_index, attempt, "occupied-count", 11
    )
    draws.extend(consumed)
    occupied_count = 2 + occupied_offset
    positions = list(range(16))
    for offset in range(occupied_count):
        selected_offset, consumed = _uniform_below(
            seed,
            observation_index,
            attempt,
            f"occupied-position-{offset}",
            16 - offset,
        )
        draws.extend(consumed)
        selected = offset + selected_offset
        positions[offset], positions[selected] = positions[selected], positions[offset]
    board = [0] * 16
    for ordinal, position in enumerate(positions[:occupied_count]):
        rank_offset, consumed = _uniform_below(
            seed, observation_index, attempt, f"occupied-rank-{ordinal}", 6
        )
        draws.extend(consumed)
        board[position] = 1 + rank_offset
    state = state_from_board_v1(tuple(board))
    legal = legal_actions_v1(state.board)
    if state.status is not Swipe2048Status.ACTIVE or not legal:
        return None
    action_offset, consumed = _uniform_below(
        seed, observation_index, attempt, "legal-action", len(legal)
    )
    draws.extend(consumed)
    return state, legal[action_offset], tuple(draws)


def _observation_row(seed: str, observation_index: int) -> dict[str, Any]:
    for attempt in range(MAXIMUM_GENERATOR_ATTEMPTS_PER_OBSERVATION):
        sampled = _sample_board_and_action(seed, observation_index, attempt)
        if sampled is None:
            continue
        state, action, choice_draws = sampled
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=observation_index
        )
        post_swipe, merge_score = swipe_v14.apply_observation_proposed_swipe_program_v14(
            state.board,
            action.value,
            candidate_key="COMPACT_THEN_SINGLE_LEFT_GREEDY_MERGE_SKIP",
        )
        reconstructed = list(post_swipe)
        if (
            merge_score != outcome.merge_score
            or reconstructed[outcome.spawned_cell] != 0
        ):
            _fail("proved swipe program does not isolate observed spawn")
        reconstructed[outcome.spawned_cell] = outcome.spawned_rank
        if tuple(reconstructed) != outcome.next_state.board:
            _fail("observed spawn does not reconstruct successor")
        return {
            "observation_index": observation_index,
            "generator_attempt": attempt,
            "pre_state": _state_document(state),
            "action": action.value,
            "post_swipe_board_ranks": list(post_swipe),
            "spawned_cell": outcome.spawned_cell,
            "spawned_rank": outcome.spawned_rank,
            "observed_successor": _state_document(outcome.next_state),
            "merge_score": outcome.merge_score,
            "generator_choice_draw_count": len(choice_draws),
            "generator_choice_digest_sha256": hashlib.sha256(
                b"".join(choice_draws)
            ).hexdigest(),
            "outcome_tape_sha256": tape,
            "spawn_probability_or_source_rule_disclosed_to_selector": False,
            "target_policy_reward_or_rollout_disclosed_to_selector": False,
        }
    _fail("spawn observation generator exhausted its attempt cap")


def _archive(role: str, seed: str, count: int) -> dict[str, Any]:
    if role not in {"SOURCE_SELECTION", "HELDOUT_VALIDATION"}:
        _fail("spawn archive role changed")
    payload = {
        "schema": "acfqp.standard_2048_spawn_observation_archive.v16",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_program_preregistration_id": pre.PREREGISTRATION_ID,
        "archive_role": role,
        "stream_seed": seed,
        "stream_domain_hex": STREAM_DOMAIN.hex(),
        "observation_count": count,
        "rows": [_observation_row(seed, index) for index in range(count)],
        "deterministic_fixture_replay_not_iid_evidence": True,
        "exact_ground_kernel_used_by_observer_only": True,
        "source_rule_available_to_selector": False,
        "target_rollout_identity_present": False,
    }
    return {
        **payload,
        "spawn_observation_archive_id": content_id(
            pre.FUTURE_DOMAINS["observation_archive"], payload
        ),
    }


def _candidate(ordinal: int) -> dict[str, Any]:
    key, cell_law, numerator, denominator = pre.SPAWN_PROGRAM_CANDIDATES[ordinal]
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_candidate.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": pre.PREREGISTRATION_ID,
        "candidate_ordinal": ordinal,
        "candidate_key": key,
        "cell_probability_law": cell_law,
        "rank_one_probability": Fraction(denominator - numerator, denominator),
        "rank_two_probability": Fraction(numerator, denominator),
        "rank_independent_of_cell_given_candidate": True,
        "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        "source_rule_or_target_policy_access": False,
    }
    return {
        **payload,
        "spawn_program_candidate_id": content_id(
            pre.FUTURE_DOMAINS["candidate"], payload
        ),
    }


def _cell_weights(cell_law: str, empty: tuple[int, ...]) -> tuple[int, ...]:
    if cell_law == "UNIFORM_OVER_EMPTY_CELLS":
        return (1,) * len(empty)
    if cell_law == "FIRST_EMPTY_CELL_ONLY":
        return (1,) + (0,) * (len(empty) - 1)
    if cell_law == "LAST_EMPTY_CELL_ONLY":
        return (0,) * (len(empty) - 1) + (1,)
    if cell_law == "CELL_INDEX_PLUS_ONE_WEIGHTED":
        return tuple(cell + 1 for cell in empty)
    if cell_law == "CORNER_EMPTY_CELL_DOUBLE_WEIGHTED":
        return tuple(2 if cell in {0, 3, 12, 15} else 1 for cell in empty)
    _fail("spawn cell law changed")


def _candidate_rows(
    candidate: dict[str, Any], empty: tuple[int, ...]
) -> tuple[tuple[int, int, Fraction], ...]:
    weights = _cell_weights(candidate["cell_probability_law"], empty)
    total = sum(weights)
    if total <= 0:
        _fail("candidate cell law has no support")
    result = []
    for cell, weight in zip(empty, weights, strict=True):
        cell_probability = Fraction(weight, total)
        for rank, rank_probability in (
            (1, candidate["rank_one_probability"]),
            (2, candidate["rank_two_probability"]),
        ):
            probability = cell_probability * rank_probability
            if probability:
                result.append((cell, rank, probability))
    if sum(row[2] for row in result) != 1:
        _fail("candidate spawn row is not normalized")
    return tuple(result)


def _prediction(candidate: dict[str, Any], row: dict[str, Any]) -> tuple[int, int]:
    empty = tuple(
        index for index, rank in enumerate(row["post_swipe_board_ranks"]) if rank == 0
    )
    threshold = Fraction(int(row["outcome_tape_sha256"], 16), 1 << 256)
    cumulative = Fraction()
    for cell, rank, probability in _candidate_rows(candidate, empty):
        cumulative += probability
        if threshold < cumulative:
            return cell, rank
    _fail("candidate tape escaped normalized spawn row")


def _score(candidate: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = 0
    first = None
    for row in rows:
        predicted = _prediction(candidate, row)
        observed = (row["spawned_cell"], row["spawned_rank"])
        if predicted != observed:
            mismatches += 1
            if first is None:
                first = {
                    "observation_index": row["observation_index"],
                    "predicted_spawned_cell": predicted[0],
                    "predicted_spawned_rank": predicted[1],
                    "observed_spawned_cell": observed[0],
                    "observed_spawned_rank": observed[1],
                }
    return {"mismatch_count": mismatches, "first_mismatch": first}


def _proposal(source: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    candidates = [_candidate(index) for index in range(len(pre.SPAWN_PROGRAM_CANDIDATES))]
    source_rows = source["rows"]
    source_scores = []
    for candidate in candidates:
        source_scores.append({
            "spawn_program_candidate_id": candidate["spawn_program_candidate_id"],
            "candidate_key": candidate["candidate_key"],
            **_score(candidate, source_rows),
        })
    minimum = min(row["mismatch_count"] for row in source_scores)
    winners = [row for row in source_scores if row["mismatch_count"] == minimum]
    if len(winners) != 1 or minimum != 0:
        _fail("source observations did not select one zero-mismatch spawn program")
    selected = next(
        candidate
        for candidate in candidates
        if candidate["spawn_program_candidate_id"]
        == winners[0]["spawn_program_candidate_id"]
    )
    validation_score = _score(selected, validation["rows"])
    if validation_score["mismatch_count"] != 0:
        _fail("source-selected spawn program failed heldout validation")
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_proposal.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": pre.PREREGISTRATION_ID,
        "source_observation_archive_id": source["spawn_observation_archive_id"],
        "validation_observation_archive_id": validation["spawn_observation_archive_id"],
        "candidate_documents": candidates,
        "source_candidate_evaluations": source_scores,
        "selected_candidate_id": selected["spawn_program_candidate_id"],
        "selected_candidate_key": selected["candidate_key"],
        "minimum_source_mismatch_count": minimum,
        "unique_source_selection": True,
        "heldout_validation_evaluation": validation_score,
        "heldout_validation_accepted": True,
        "validation_read_after_source_selection": True,
        "source_rule_or_target_policy_accessed": False,
        "exact_support_proof_accessed_before_proposal_freeze": False,
    }
    return {
        **payload,
        "spawn_program_proposal_id": content_id(
            pre.FUTURE_DOMAINS["proposal"], payload
        ),
    }


def _support_proof(proposal: dict[str, Any]) -> dict[str, Any]:
    source = (
        Path(__file__).resolve().parent / "domains" / "standard_2048.py"
    ).read_bytes()
    if (
        len(source) != pre.STANDARD_2048_SOURCE_BYTE_COUNT
        or hashlib.sha256(source).hexdigest() != pre.STANDARD_2048_SOURCE_SHA256
        or SPAWN_DISTRIBUTION
        != ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    ):
        _fail("postselection source-closed spawn contract changed")
    selected = next(
        row
        for row in proposal["candidate_documents"]
        if row["spawn_program_candidate_id"] == proposal["selected_candidate_id"]
    )
    trace = hashlib.sha256(PROOF_TRACE_DOMAIN)
    mismatch_count = 0
    support_row_evaluations = 0
    for mask in range(1, (1 << 16) - 1):
        empty = tuple(cell for cell in range(16) if mask & (1 << cell))
        actual = _candidate_rows(selected, empty)
        expected = tuple(
            (cell, rank, rank_probability / len(empty))
            for cell in empty
            for rank, rank_probability in SPAWN_DISTRIBUTION
        )
        support_row_evaluations += len(expected)
        if actual != expected:
            mismatch_count += 1
        trace.update(
            canonical_json_bytes(
                {
                    "empty_cell_mask": mask,
                    "candidate_rows": [
                        {"cell": cell, "rank": rank, "probability": probability}
                        for cell, rank, probability in actual
                    ],
                }
            )
        )
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_support_proof.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": pre.PREREGISTRATION_ID,
        "spawn_program_proposal_id": proposal["spawn_program_proposal_id"],
        "selected_candidate_id": proposal["selected_candidate_id"],
        "selected_candidate_key": proposal["selected_candidate_key"],
        "standard_2048_source_sha256": pre.STANDARD_2048_SOURCE_SHA256,
        "standard_2048_source_byte_count": pre.STANDARD_2048_SOURCE_BYTE_COUNT,
        "proof_reduction": "SPAWN_ROWS_FACTOR_THROUGH_POST_SWIPE_EMPTY_CELL_SUBSET",
        "nonempty_proper_empty_cell_subset_count": 65534,
        "support_row_evaluation_count": support_row_evaluations,
        "mismatch_count": mismatch_count,
        "trace_sha256": trace.hexdigest(),
        "exact_rational_probability_equality": mismatch_count == 0,
        "source_access_after_proposal_freeze": True,
        "transition_observation_count": 0,
    }
    return {
        **payload,
        "spawn_program_support_proof_id": content_id(
            pre.FUTURE_DOMAINS["support_proof"], payload
        ),
    }


def _world_model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    if proposal["selected_candidate_key"] != SELECTED_CANDIDATE_KEY:
        _fail("observation-proposed spawn program is not the frozen standard candidate")
    if proof["mismatch_count"] != 0:
        _fail("spawn program proof did not close")
    payload = {
        "schema": "acfqp.standard_2048_synthesized_world_model.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": pre.PREREGISTRATION_ID,
        "v14_program_proposal_id": pre.V14_PROGRAM_PROPOSAL_ID,
        "v14_program_line_proof_id": pre.V14_PROGRAM_LINE_PROOF_ID,
        "v14_factored_world_model_id": pre.V14_FACTORED_WORLD_MODEL_ID,
        "spawn_program_proposal_id": proposal["spawn_program_proposal_id"],
        "spawn_program_support_proof_id": proof["spawn_program_support_proof_id"],
        "deterministic_swipe_component": "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM",
        "stochastic_spawn_component": "OBSERVATION_PROPOSED_EXACT_PROVED_PROGRAM",
        "successors_generated_by_composed_factored_programs": True,
        "full_state_action_rows_materialized": False,
        "exact_multistep_planning_semantics_available": True,
        "ground_access_before_certificate_failure": False,
        "target_rollout_or_policy_outcome_accessed": False,
        "broad_domain_generalization_claimed": False,
    }
    return {
        **payload,
        "synthesized_world_model_id": content_id(
            pre.FUTURE_DOMAINS["world_model"], payload
        ),
    }


def apply_observation_proposed_spawn_program_v16(
    post_swipe_board: tuple[int, ...],
) -> tuple[tuple[int, int, Fraction], ...]:
    """Generate the exact proved spawn row without calling the ground kernel."""

    if (
        type(post_swipe_board) is not tuple
        or len(post_swipe_board) != 16
        or any(
            type(rank) is not int or not 0 <= rank <= 19
            for rank in post_swipe_board
        )
    ):
        _fail("observation-proposed spawn-program board changed")
    empty = tuple(
        index for index, rank in enumerate(post_swipe_board) if rank == 0
    )
    if not empty or len(empty) == 16:
        _fail("observation-proposed spawn-program support is out of scope")
    # The selected candidate is frozen and independently proved.  Apply its
    # reduced program directly; rebuilding its content-addressed proposal for
    # every Bellman row would add serialization work without new semantics.
    return tuple(
        (cell, rank, probability / len(empty))
        for cell in empty
        for rank, probability in SELECTED_RANK_DISTRIBUTION
    )


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SpawnProgramCampaignV16:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    synthesized_world_model_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("spawn-program campaign is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("spawn-program campaign bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "spawn_program_campaign_id"
        }
        if (
            document.get("spawn_program_campaign_id") != self.campaign_id
            or content_id(pre.FUTURE_DOMAINS["campaign"], payload) != self.campaign_id
            or document.get("synthesized_world_model", {}).get(
                "synthesized_world_model_id"
            )
            != self.synthesized_world_model_id
        ):
            _fail("spawn-program campaign identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("spawn-program campaign is not an object")
        return document


def run_standard_2048_spawn_program_campaign_v16(
) -> Standard2048SpawnProgramCampaignV16:
    preregistration = pre.freeze_standard_2048_spawn_program_preregistration_v16()
    source = _archive(
        "SOURCE_SELECTION", pre.SOURCE_STREAM_SEED, pre.SOURCE_OBSERVATION_COUNT
    )
    validation = _archive(
        "HELDOUT_VALIDATION",
        pre.VALIDATION_STREAM_SEED,
        pre.VALIDATION_OBSERVATION_COUNT,
    )
    proposal = _proposal(source, validation)
    proof = _support_proof(proposal)
    world_model = _world_model(proposal, proof)
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_campaign.v16",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": pre.PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_program_preregistration": preregistration.to_document(),
        "source_observation_archive": source,
        "validation_observation_archive": validation,
        "spawn_program_proposal": proposal,
        "spawn_program_support_proof": proof,
        "synthesized_world_model": world_model,
        "source_observation_count": pre.SOURCE_OBSERVATION_COUNT,
        "validation_observation_count": pre.VALIDATION_OBSERVATION_COUNT,
        "joint_swipe_and_spawn_observation_count": pre.JOINT_SWIPE_AND_SPAWN_OBSERVATION_COUNT,
        "matched_fixed_observation_control_count": pre.MATCHED_FIXED_OBSERVATION_CONTROL_COUNT,
        "registered_observation_difference": pre.REGISTERED_OBSERVATION_DIFFERENCE,
        "program_proof_compute_reported_separately": True,
        "target_transition_observation_count": 0,
        "unique_source_selection": proposal["unique_source_selection"],
        "heldout_validation_accepted": proposal["heldout_validation_accepted"],
        "exact_postselection_support_proof_passed": proof["mismatch_count"] == 0,
        "sample_tax_result": "POSITIVE_CONDITIONAL_PROGRAM_PROPOSAL_RESULT",
        "sample_tax_reduced_on_registered_observation_axis": True,
        "conditional_on_frozen_candidate_grammar_and_source_closed_proof": True,
        "total_operational_work_saving_claimed": False,
        "broad_or_physical_iid_sample_efficiency_claimed": False,
        "target_planning_or_execution_performed": False,
        "full_standard_2048_game_completed": False,
        "tile_2048_reached": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    campaign_id = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    canonical_bytes = canonical_json_bytes(
        {**payload, "spawn_program_campaign_id": campaign_id}
    )
    if (
        source["spawn_observation_archive_id"] != EXPECTED_SOURCE_ARCHIVE_ID
        or validation["spawn_observation_archive_id"]
        != EXPECTED_VALIDATION_ARCHIVE_ID
        or proposal["spawn_program_proposal_id"] != EXPECTED_PROPOSAL_ID
        or proposal["selected_candidate_id"] != EXPECTED_SELECTED_CANDIDATE_ID
        or proof["spawn_program_support_proof_id"] != EXPECTED_SUPPORT_PROOF_ID
        or proof["trace_sha256"] != EXPECTED_PROOF_TRACE_SHA256
        or world_model["synthesized_world_model_id"] != EXPECTED_WORLD_MODEL_ID
        or campaign_id != EXPECTED_CAMPAIGN_ID
        or len(canonical_bytes) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(canonical_bytes).hexdigest()
        != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen spawn-program campaign outcome changed")
    return Standard2048SpawnProgramCampaignV16(
        _ISSUER,
        canonical_bytes,
        campaign_id,
        world_model["synthesized_world_model_id"],
    )


def verify_standard_2048_spawn_program_campaign_v16(
    value: Standard2048SpawnProgramCampaignV16,
) -> Standard2048SpawnProgramCampaignV16:
    if type(value) is not Standard2048SpawnProgramCampaignV16:
        _fail("spawn-program campaign verifier rejects foreign values")
    value.__post_init__()
    document = value.to_document()
    if (
        document["spawn_program_preregistration"]["spawn_program_preregistration_id"]
        != pre.PREREGISTRATION_ID
        or document["spawn_program_proposal"]["selected_candidate_key"]
        != SELECTED_CANDIDATE_KEY
        or document["spawn_program_support_proof"]["mismatch_count"] != 0
        or document["sample_tax_reduced_on_registered_observation_axis"] is not True
        or document["target_planning_or_execution_performed"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("spawn-program campaign semantics or claim lock changed")
    return value


__all__ = (
    "apply_observation_proposed_spawn_program_v16",
    "ConstructionK7Standard2048SpawnProgramV16Error",
    "EXPECTED_CAMPAIGN_ID",
    "SELECTED_CANDIDATE_KEY",
    "Standard2048SpawnProgramCampaignV16",
    "run_standard_2048_spawn_program_campaign_v16",
    "verify_standard_2048_spawn_program_campaign_v16",
)
