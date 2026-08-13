"""Producer-free replay of the observation-proposed 2048 spawn program."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14 as swipe_v14
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
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "16.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.175"
PROFILE_KEY = "construction_k7_standard_2048_spawn_program_v16"
PREREGISTRATION_ID = "9b868b003846c0ad0a966537922ef621ab5c1166533b00cfb02187d78399300a"
V14_PROGRAM_PROPOSAL_ID = "7164a54cad13246a55c891a71a1a879b15be7116fbcb49998e8b7619f9c0ce72"
V14_PROGRAM_LINE_PROOF_ID = "3960ef8c496eb00a81d08bf29243ee7f5cd5f50f5302f2b91cb836618bc322b6"
V14_FACTORED_WORLD_MODEL_ID = "40e9c27ea6cc4bb13749fe1d938d3054c886a739abf493bd731f3808905aaa07"
V15_EXACT_FACTOR_CAMPAIGN_ID = "0c9be0ddd9895dd9162b6408493d56a16ae4f9ed70591c41117781701a697645"
V15_INDEPENDENT_VERIFICATION_ID = "33777be770b7ae8eb45c4d22b2a8c5226dde4a443f2381ea402afd09826f7180"
SOURCE_SHA256 = "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c"
SOURCE_BYTE_COUNT = 14739
SOURCE_COUNT = 256
VALIDATION_COUNT = 128
SOURCE_SEED = "standard-2048-v175-spawn-source-20260813"
VALIDATION_SEED = "standard-2048-v175-spawn-validation-20260813"
STREAM_DOMAIN = b"acfqp:standard-2048-spawn-program-observation-tape:v16\x00"
PROOF_TRACE_DOMAIN = b"acfqp:standard-2048-spawn-program-support-proof-trace:v16\x00"
MAXIMUM_ATTEMPTS = 4096
EXPECTED_SOURCE_ARCHIVE_ID = "630af9f4bff7d0581c809f5990a27f5e9ad432a1cdd94159bd8179db1882c3b5"
EXPECTED_VALIDATION_ARCHIVE_ID = "45ba6ebfb190f71f3fe4227d018b57b4ace0a29490d71b075bc427cccb163b6c"
EXPECTED_PROPOSAL_ID = "32856e6557710cb7a97f40400a5b5cb8f34afb7851b25f966e595df579437ebf"
EXPECTED_SELECTED_CANDIDATE_ID = "7bc3f2c1eefdc78d5b3386497e31dea4fb8b355110f4eee7708aedd9a5bbd645"
EXPECTED_SUPPORT_PROOF_ID = "973dd6629b6bebbaad932f0c73b976a906a4844fa44180a04f37d1eaf54e9367"
EXPECTED_PROOF_TRACE_SHA256 = "5cca2c8e3de74d692f417fb6e82be29223b9da00988285179cb0579c6a61f22f"
EXPECTED_WORLD_MODEL_ID = "492750c86baf5d53f68b7f470a8d5e3f74a7b088dc5767329a5945a90f01f389"
EXPECTED_CAMPAIGN_ID = "c6d490d140676a9d045e678f1484635d925a655f4c67605afde28690e246aa53"
EXPECTED_VERIFICATION_ID = "a6fa6e31d8ee765e4a6c352384baed87ef7a38bba58af7590b85b666e94a8198"

CELL_LAWS = (
    "UNIFORM_OVER_EMPTY_CELLS",
    "FIRST_EMPTY_CELL_ONLY",
    "LAST_EMPTY_CELL_ONLY",
    "CELL_INDEX_PLUS_ONE_WEIGHTED",
    "CORNER_EMPTY_CELL_DOUBLE_WEIGHTED",
)
RANK_TWO_PROBABILITIES = ((0, 1), (1, 16), (1, 10), (1, 8), (1, 4))
CANDIDATES = tuple(
    (
        f"{law}__RANK_TWO_{numerator}_OVER_{denominator}",
        law,
        numerator,
        denominator,
    )
    for law in CELL_LAWS
    for numerator, denominator in RANK_TWO_PROBABILITIES
)


class ConstructionK7Standard2048SpawnProgramIndependentVerifierV16Error(ValueError):
    """Campaign bytes differ from independent observation and proof replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SpawnProgramIndependentVerifierV16Error(message)


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _draw(seed: str, index: int, attempt: int, label: str, counter: int) -> bytes:
    return hashlib.sha256(
        STREAM_DOMAIN
        + seed.encode()
        + b"\x00"
        + str(index).encode()
        + b"\x00"
        + str(attempt).encode()
        + b"\x00"
        + label.encode()
        + b"\x00"
        + str(counter).encode()
    ).digest()


def _uniform(
    seed: str, index: int, attempt: int, label: str, bound: int
) -> tuple[int, tuple[bytes, ...]]:
    scale = 1 << 256
    limit = scale - scale % bound
    counter = 0
    consumed = []
    while True:
        digest = _draw(seed, index, attempt, label, counter)
        consumed.append(digest)
        value = int.from_bytes(digest, "big")
        if value < limit:
            return value % bound, tuple(consumed)
        counter += 1


def _sample(
    seed: str, index: int, attempt: int
) -> tuple[Swipe2048State, Swipe2048Action, tuple[bytes, ...]] | None:
    draws = []
    offset, consumed = _uniform(seed, index, attempt, "occupied-count", 11)
    draws.extend(consumed)
    count = 2 + offset
    positions = list(range(16))
    for ordinal in range(count):
        offset, consumed = _uniform(
            seed, index, attempt, f"occupied-position-{ordinal}", 16 - ordinal
        )
        draws.extend(consumed)
        selected = ordinal + offset
        positions[ordinal], positions[selected] = positions[selected], positions[ordinal]
    board = [0] * 16
    for ordinal, position in enumerate(positions[:count]):
        offset, consumed = _uniform(
            seed, index, attempt, f"occupied-rank-{ordinal}", 6
        )
        draws.extend(consumed)
        board[position] = 1 + offset
    state = state_from_board_v1(tuple(board))
    legal = legal_actions_v1(state.board)
    if state.status is not Swipe2048Status.ACTIVE or not legal:
        return None
    offset, consumed = _uniform(seed, index, attempt, "legal-action", len(legal))
    draws.extend(consumed)
    return state, legal[offset], tuple(draws)


def _row(seed: str, index: int) -> dict[str, Any]:
    for attempt in range(MAXIMUM_ATTEMPTS):
        sampled = _sample(seed, index, attempt)
        if sampled is None:
            continue
        state, action, draws = sampled
        outcome, tape = select_seeded_outcome_v1(
            step_v1(state, action), seed=seed, decision_index=index
        )
        post_swipe, merge_score = swipe_v14.apply_independently_replayed_swipe_program_v14(
            state.board, action.value
        )
        reconstructed = list(post_swipe)
        if merge_score != outcome.merge_score or reconstructed[outcome.spawned_cell] != 0:
            _fail("independent swipe isolation changed")
        reconstructed[outcome.spawned_cell] = outcome.spawned_rank
        if tuple(reconstructed) != outcome.next_state.board:
            _fail("independent observed successor reconstruction changed")
        return {
            "observation_index": index,
            "generator_attempt": attempt,
            "pre_state": _state_document(state),
            "action": action.value,
            "post_swipe_board_ranks": list(post_swipe),
            "spawned_cell": outcome.spawned_cell,
            "spawned_rank": outcome.spawned_rank,
            "observed_successor": _state_document(outcome.next_state),
            "merge_score": outcome.merge_score,
            "generator_choice_draw_count": len(draws),
            "generator_choice_digest_sha256": hashlib.sha256(b"".join(draws)).hexdigest(),
            "outcome_tape_sha256": tape,
            "spawn_probability_or_source_rule_disclosed_to_selector": False,
            "target_policy_reward_or_rollout_disclosed_to_selector": False,
        }
    _fail("independent observation generator exhausted")


def _archive(role: str, seed: str, count: int) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_spawn_observation_archive.v16",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "archive_role": role,
        "stream_seed": seed,
        "stream_domain_hex": STREAM_DOMAIN.hex(),
        "observation_count": count,
        "rows": [_row(seed, index) for index in range(count)],
        "deterministic_fixture_replay_not_iid_evidence": True,
        "exact_ground_kernel_used_by_observer_only": True,
        "source_rule_available_to_selector": False,
        "target_rollout_identity_present": False,
    }
    return {
        **payload,
        "spawn_observation_archive_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN,
            payload,
        ),
    }


def _candidate(ordinal: int) -> dict[str, Any]:
    key, law, numerator, denominator = CANDIDATES[ordinal]
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_candidate.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "candidate_ordinal": ordinal,
        "candidate_key": key,
        "cell_probability_law": law,
        "rank_one_probability": Fraction(denominator - numerator, denominator),
        "rank_two_probability": Fraction(numerator, denominator),
        "rank_independent_of_cell_given_candidate": True,
        "outcome_order": "ASCENDING_CELL_THEN_ASCENDING_RANK",
        "source_rule_or_target_policy_access": False,
    }
    return {
        **payload,
        "spawn_program_candidate_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN,
            payload,
        ),
    }


def _weights(law: str, empty: tuple[int, ...]) -> tuple[int, ...]:
    if law == CELL_LAWS[0]:
        return (1,) * len(empty)
    if law == CELL_LAWS[1]:
        return (1,) + (0,) * (len(empty) - 1)
    if law == CELL_LAWS[2]:
        return (0,) * (len(empty) - 1) + (1,)
    if law == CELL_LAWS[3]:
        return tuple(cell + 1 for cell in empty)
    if law == CELL_LAWS[4]:
        return tuple(2 if cell in {0, 3, 12, 15} else 1 for cell in empty)
    _fail("independent cell law changed")


def _candidate_rows(
    candidate: dict[str, Any], empty: tuple[int, ...]
) -> tuple[tuple[int, int, Fraction], ...]:
    weights = _weights(candidate["cell_probability_law"], empty)
    total = sum(weights)
    rows = tuple(
        (cell, rank, Fraction(weight, total) * probability)
        for cell, weight in zip(empty, weights, strict=True)
        for rank, probability in (
            (1, candidate["rank_one_probability"]),
            (2, candidate["rank_two_probability"]),
        )
        if weight and probability
    )
    if sum(row[2] for row in rows) != 1:
        _fail("independent candidate row is not normalized")
    return rows


def _prediction(candidate: dict[str, Any], row: dict[str, Any]) -> tuple[int, int]:
    empty = tuple(i for i, rank in enumerate(row["post_swipe_board_ranks"]) if not rank)
    threshold = Fraction(int(row["outcome_tape_sha256"], 16), 1 << 256)
    cumulative = Fraction()
    for cell, rank, probability in _candidate_rows(candidate, empty):
        cumulative += probability
        if threshold < cumulative:
            return cell, rank
    _fail("independent candidate tape escaped")


def _score(candidate: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    first = None
    for row in rows:
        predicted = _prediction(candidate, row)
        observed = (row["spawned_cell"], row["spawned_rank"])
        if predicted != observed:
            count += 1
            if first is None:
                first = {
                    "observation_index": row["observation_index"],
                    "predicted_spawned_cell": predicted[0],
                    "predicted_spawned_rank": predicted[1],
                    "observed_spawned_cell": observed[0],
                    "observed_spawned_rank": observed[1],
                }
    return {"mismatch_count": count, "first_mismatch": first}


def _proposal(source: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    candidates = [_candidate(index) for index in range(len(CANDIDATES))]
    evaluations = [
        {
            "spawn_program_candidate_id": candidate["spawn_program_candidate_id"],
            "candidate_key": candidate["candidate_key"],
            **_score(candidate, source["rows"]),
        }
        for candidate in candidates
    ]
    minimum = min(row["mismatch_count"] for row in evaluations)
    winners = [row for row in evaluations if row["mismatch_count"] == minimum]
    if len(winners) != 1 or minimum != 0:
        _fail("independent source selection changed")
    selected = next(
        row
        for row in candidates
        if row["spawn_program_candidate_id"] == winners[0]["spawn_program_candidate_id"]
    )
    heldout = _score(selected, validation["rows"])
    if heldout["mismatch_count"]:
        _fail("independent heldout result changed")
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_proposal.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "source_observation_archive_id": source["spawn_observation_archive_id"],
        "validation_observation_archive_id": validation["spawn_observation_archive_id"],
        "candidate_documents": candidates,
        "source_candidate_evaluations": evaluations,
        "selected_candidate_id": selected["spawn_program_candidate_id"],
        "selected_candidate_key": selected["candidate_key"],
        "minimum_source_mismatch_count": minimum,
        "unique_source_selection": True,
        "heldout_validation_evaluation": heldout,
        "heldout_validation_accepted": True,
        "validation_read_after_source_selection": True,
        "source_rule_or_target_policy_accessed": False,
        "exact_support_proof_accessed_before_proposal_freeze": False,
    }
    return {
        **payload,
        "spawn_program_proposal_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN,
            payload,
        ),
    }


def _proof(proposal: dict[str, Any]) -> dict[str, Any]:
    source = (Path(__file__).resolve().parent / "domains" / "standard_2048.py").read_bytes()
    if (
        len(source) != SOURCE_BYTE_COUNT
        or hashlib.sha256(source).hexdigest() != SOURCE_SHA256
        or SPAWN_DISTRIBUTION != ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    ):
        _fail("independent source closure changed")
    selected = next(
        row
        for row in proposal["candidate_documents"]
        if row["spawn_program_candidate_id"] == proposal["selected_candidate_id"]
    )
    trace = hashlib.sha256(PROOF_TRACE_DOMAIN)
    mismatches = 0
    evaluations = 0
    for mask in range(1, (1 << 16) - 1):
        empty = tuple(cell for cell in range(16) if mask & (1 << cell))
        actual = _candidate_rows(selected, empty)
        expected = tuple(
            (cell, rank, probability / len(empty))
            for cell in empty
            for rank, probability in SPAWN_DISTRIBUTION
        )
        evaluations += len(expected)
        mismatches += actual != expected
        trace.update(canonical_json_bytes({
            "empty_cell_mask": mask,
            "candidate_rows": [
                {"cell": cell, "rank": rank, "probability": probability}
                for cell, rank, probability in actual
            ],
        }))
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_support_proof.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "spawn_program_proposal_id": proposal["spawn_program_proposal_id"],
        "selected_candidate_id": proposal["selected_candidate_id"],
        "selected_candidate_key": proposal["selected_candidate_key"],
        "standard_2048_source_sha256": SOURCE_SHA256,
        "standard_2048_source_byte_count": SOURCE_BYTE_COUNT,
        "proof_reduction": "SPAWN_ROWS_FACTOR_THROUGH_POST_SWIPE_EMPTY_CELL_SUBSET",
        "nonempty_proper_empty_cell_subset_count": 65534,
        "support_row_evaluation_count": evaluations,
        "mismatch_count": mismatches,
        "trace_sha256": trace.hexdigest(),
        "exact_rational_probability_equality": mismatches == 0,
        "source_access_after_proposal_freeze": True,
        "transition_observation_count": 0,
    }
    return {
        **payload,
        "spawn_program_support_proof_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN,
            payload,
        ),
    }


def _model(proposal: dict[str, Any], proof: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_synthesized_world_model.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "v14_program_proposal_id": V14_PROGRAM_PROPOSAL_ID,
        "v14_program_line_proof_id": V14_PROGRAM_LINE_PROOF_ID,
        "v14_factored_world_model_id": V14_FACTORED_WORLD_MODEL_ID,
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
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN,
            payload,
        ),
    }


def apply_independently_replayed_spawn_program_v16(
    post_swipe_board: tuple[int, ...],
) -> tuple[tuple[int, int, Fraction], ...]:
    """Apply only the independently selected and exhaustively proved program."""

    if (
        type(post_swipe_board) is not tuple
        or len(post_swipe_board) != 16
        or any(
            type(rank) is not int or not 0 <= rank <= 19
            for rank in post_swipe_board
        )
    ):
        _fail("independent spawn-program board changed")
    empty = tuple(
        index for index, rank in enumerate(post_swipe_board) if rank == 0
    )
    if not empty or len(empty) == 16:
        _fail("independent spawn-program support is out of scope")
    return tuple(
        (cell, rank, probability / len(empty))
        for cell in empty
        for rank, probability in ((1, Fraction(9, 10)), (2, Fraction(1, 10)))
    )


def _verify_preregistration(document: Any) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("embedded preregistration changed")
    payload = {
        key: value
        for key, value in document.items()
        if key != "spawn_program_preregistration_id"
    }
    if (
        document.get("spawn_program_preregistration_id") != PREREGISTRATION_ID
        or content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN,
            payload,
        )
        != PREREGISTRATION_ID
        or document.get("outcome_fields_present") is not False
        or document.get("target_planning_or_execution_performed") is not False
        or document.get("official_execution_allowed") is not False
    ):
        _fail("embedded preregistration identity or locks changed")
    return document


def _expected(observed: dict[str, Any]) -> dict[str, Any]:
    preregistration = _verify_preregistration(observed["spawn_program_preregistration"])
    source = _archive("SOURCE_SELECTION", SOURCE_SEED, SOURCE_COUNT)
    validation = _archive("HELDOUT_VALIDATION", VALIDATION_SEED, VALIDATION_COUNT)
    proposal = _proposal(source, validation)
    proof = _proof(proposal)
    model = _model(proposal, proof)
    if (
        source["spawn_observation_archive_id"] != EXPECTED_SOURCE_ARCHIVE_ID
        or validation["spawn_observation_archive_id"] != EXPECTED_VALIDATION_ARCHIVE_ID
        or proposal["spawn_program_proposal_id"] != EXPECTED_PROPOSAL_ID
        or proposal["selected_candidate_id"] != EXPECTED_SELECTED_CANDIDATE_ID
        or proof["spawn_program_support_proof_id"] != EXPECTED_SUPPORT_PROOF_ID
        or proof["trace_sha256"] != EXPECTED_PROOF_TRACE_SHA256
        or model["synthesized_world_model_id"] != EXPECTED_WORLD_MODEL_ID
    ):
        _fail("independent frozen spawn-program identities changed")
    payload = {
        "schema": "acfqp.standard_2048_spawn_program_campaign.v16",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_program_preregistration": preregistration,
        "source_observation_archive": source,
        "validation_observation_archive": validation,
        "spawn_program_proposal": proposal,
        "spawn_program_support_proof": proof,
        "synthesized_world_model": model,
        "source_observation_count": SOURCE_COUNT,
        "validation_observation_count": VALIDATION_COUNT,
        "joint_swipe_and_spawn_observation_count": 1152,
        "matched_fixed_observation_control_count": 8192,
        "registered_observation_difference": 7040,
        "program_proof_compute_reported_separately": True,
        "target_transition_observation_count": 0,
        "unique_source_selection": True,
        "heldout_validation_accepted": True,
        "exact_postselection_support_proof_passed": True,
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
    return {
        **payload,
        "spawn_program_campaign_id": content_id(
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SpawnProgramIndependentVerificationV16:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str
    campaign_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("spawn-program verification is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != self.canonical_bytes:
            _fail("spawn-program verification bytes changed")
        payload = {
            key: value
            for key, value in document.items()
            if key != "spawn_program_verification_id"
        }
        if (
            document.get("spawn_program_verification_id") != self.verification_id
            or document.get("spawn_program_campaign_id") != self.campaign_id
            or content_id(
                CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN,
                payload,
            )
            != self.verification_id
        ):
            _fail("spawn-program verification identity changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("spawn-program verification is not an object")
        return document


def verify_standard_2048_spawn_program_bytes_independently_v16(
    canonical_bytes: bytes,
) -> Standard2048SpawnProgramIndependentVerificationV16:
    observed = loads_canonical_json(canonical_bytes)
    if (
        type(observed) is not dict
        or canonical_json_bytes(observed) != canonical_bytes
        or observed.get("spawn_program_campaign_id") != EXPECTED_CAMPAIGN_ID
    ):
        _fail("spawn-program campaign root or identity changed")
    payload = {
        key: value
        for key, value in observed.items()
        if key != "spawn_program_campaign_id"
    }
    if content_id(
        CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN, payload
    ) != EXPECTED_CAMPAIGN_ID:
        _fail("spawn-program campaign content identity changed")
    expected = _expected(observed)
    if observed != expected:
        _fail("spawn-program campaign differs from producer-free replay")
    verification_payload = {
        "schema": "acfqp.standard_2048_spawn_program_independent_verification.v16",
        "schema_version": SCHEMA_VERSION,
        "spawn_program_preregistration_id": PREREGISTRATION_ID,
        "spawn_program_campaign_id": EXPECTED_CAMPAIGN_ID,
        "source_and_validation_observations_independently_replayed": True,
        "all_25_candidate_programs_independently_scored": True,
        "unique_source_selection_and_heldout_acceptance_independently_replayed": True,
        "all_65534_empty_support_subsets_independently_replayed": True,
        "exact_rational_spawn_equivalence_independently_verified": True,
        "composed_swipe_and_spawn_world_model_independently_verified": True,
        "registered_observation_axis_reduction_independently_verified": True,
        "target_planning_or_full_game_verified": False,
        "broad_sample_efficiency_or_total_work_saving_verified": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    verification_id = content_id(
        CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN,
        verification_payload,
    )
    if verification_id != EXPECTED_VERIFICATION_ID:
        _fail("frozen spawn-program verification identity changed")
    return Standard2048SpawnProgramIndependentVerificationV16(
        _ISSUER,
        canonical_json_bytes(
            {**verification_payload, "spawn_program_verification_id": verification_id}
        ),
        verification_id,
        EXPECTED_CAMPAIGN_ID,
    )


__all__ = (
    "apply_independently_replayed_spawn_program_v16",
    "ConstructionK7Standard2048SpawnProgramIndependentVerifierV16Error",
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_VERIFICATION_ID",
    "Standard2048SpawnProgramIndependentVerificationV16",
    "verify_standard_2048_spawn_program_bytes_independently_v16",
)
