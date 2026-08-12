"""Producer-free semantic replay for the fresh-board support campaign."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.domains.g2048 import inverse_d4
from acfqp.domains.standard_2048 import (
    ACTION_ORDER,
    GOAL_RANK,
    Swipe2048Action,
    Swipe2048State,
    Swipe2048Status,
    boards_from_rows_v1,
    canonicalize_state_action_v1,
    canonicalize_state_v1,
    legal_actions_v1,
    select_seeded_outcome_v1,
    state_from_board_v1,
    step_v1,
    swipe_board_v1,
    transform_action_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_INDEPENDENT_VERIFICATION_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.156"
PROFILE_KEY = "construction_k7_standard_2048_fresh_board_support_world_model_v2"
OBSERVATION_PROFILE_KEY = "construction_k7_standard_2048_spawn_support_observation_v2"
PLANNING_HORIZON = 3
EPISODE_DECISION_COUNT = 4
SOURCE_SEED = "standard-2048-support-source-20260812-v2"
VALIDATION_SEED = "standard-2048-support-validation-20260812-v2"
SOURCE_STREAM_DOMAIN = b"acfqp:standard-2048-spawn-support-source:v2"
VALIDATION_STREAM_DOMAIN = b"acfqp:standard-2048-spawn-support-validation:v2"
SOURCE_RECORDS_PER_CARDINALITY = 8192
VALIDATION_RECORDS_PER_CARDINALITY = 1024
POSITION_RADIUS = Fraction(1, 32)
RANK_TWO_RADIUS = Fraction(1, 128)
UNKNOWN_SUPPORT_MASS_UPPER = Fraction(1, 128)
CONDITIONAL_CONFIDENCE_LOWER = Fraction(999, 1000)
SELECTED_SUPPORT_RULE = "ALL_SORTED_EMPTY_ORDINALS"
SUPPORT_CANDIDATES = (
    "ALL_SORTED_EMPTY_ORDINALS",
    "FIRST_EMPTY_ORDINAL_ONLY",
    "LAST_EMPTY_ORDINAL_ONLY",
    "EVEN_EMPTY_ORDINALS_ONLY",
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_INDEPENDENT_VERIFICATION_V2_DOMAIN
)
HELDOUT_EPISODE_SEEDS = (
    "standard-2048-fresh-board-a-20260812-v2",
    "standard-2048-fresh-board-b-20260812-v2",
)

DOMAINS = {
    "preregistration": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN,
    "row": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN,
    "model": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN,
    "audit": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN,
    "plan": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN,
    "direct": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN,
    "episode": CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN,
    "campaign": CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("support partial-dynamics domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("support partial-dynamics domains are not registered")

REGISTERED_FRESH_BOARDS = (
    boards_from_rows_v1((
        (1, 3, 2, 4),
        (2, 4, 3, 5),
        (3, 5, 4, 6),
        (1, 1, 2, 2),
    )),
    boards_from_rows_v1((
        (2, 1, 2, 3),
        (3, 2, 3, 4),
        (4, 3, 4, 5),
        (1, 1, 2, 2),
    )),
)
LEGACY_V1_ROOT_BOARD = boards_from_rows_v1((
        (1, 2, 3, 4),
        (2, 3, 4, 5),
        (3, 4, 5, 6),
        (1, 1, 2, 2),
    ))
if any(board == LEGACY_V1_ROOT_BOARD for board in REGISTERED_FRESH_BOARDS):  # pragma: no cover
    raise RuntimeError("fresh boards must not reuse the V1 root")


class ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error(ValueError):
    """Campaign bytes do not independently replay under registered semantics."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_document(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        try:
            return Fraction(value["numerator"], value["denominator"])
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error(
                "fraction document is invalid"
            ) from error
    _fail("fraction document changed")


def _support_record_stream(
    *, domain: bytes, seed: str, records_per_cardinality: int
) -> tuple[tuple[int, int, int, bool], ...]:
    records: list[tuple[int, int, int, bool]] = []
    for empty_count in range(1, 17):
        for index in range(records_per_cardinality):
            prefix = (
                domain
                + b"\x00"
                + seed.encode("utf-8")
                + b"\x00"
                + str(empty_count).encode("ascii")
                + b"\x00"
                + str(index).encode("ascii")
                + b"\x00"
            )
            position_digest = hashlib.sha256(prefix + b"position").digest()
            ordinal = (int.from_bytes(position_digest, "big") * empty_count) >> 256
            rank_digest = hashlib.sha256(prefix + b"rank").digest()
            rank = 2 if int.from_bytes(rank_digest, "big") * 10 < (1 << 256) else 1
            records.append((empty_count, ordinal, rank, True))
    return tuple(records)


def _source_support_records() -> tuple[tuple[int, int, int, bool], ...]:
    return _support_record_stream(
        domain=SOURCE_STREAM_DOMAIN,
        seed=SOURCE_SEED,
        records_per_cardinality=SOURCE_RECORDS_PER_CARDINALITY,
    )


def _validation_support_records() -> tuple[tuple[int, int, int, bool], ...]:
    return _support_record_stream(
        domain=VALIDATION_STREAM_DOMAIN,
        seed=VALIDATION_SEED,
        records_per_cardinality=VALIDATION_RECORDS_PER_CARDINALITY,
    )


def _pack_support_records(
    records: tuple[tuple[int, int, int, bool], ...]
) -> bytes:
    packed = bytearray()
    for empty_count, ordinal, rank, valid in records:
        if (
            not 1 <= empty_count <= 16
            or not 0 <= ordinal < empty_count
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("raw support record changed")
        packed.extend(
            (empty_count, ordinal | ((rank - 1) << 4) | (int(valid) << 5))
        )
    return bytes(packed)


def _support_archive_document(*, source: bool) -> dict[str, Any]:
    if source:
        records = _source_support_records()
        seed = SOURCE_SEED
        stream_domain = SOURCE_STREAM_DOMAIN
        per_cardinality = SOURCE_RECORDS_PER_CARDINALITY
        role = "SOURCE_CONSTRUCTION"
        domain = CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN
        identity = "support_source_archive_id"
    else:
        records = _validation_support_records()
        seed = VALIDATION_SEED
        stream_domain = VALIDATION_STREAM_DOMAIN
        per_cardinality = VALIDATION_RECORDS_PER_CARDINALITY
        role = "HELDOUT_VALIDATION"
        domain = CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN
        identity = "support_validation_archive_id"
    packed = _pack_support_records(records)
    payload = {
        "schema": "acfqp.standard_2048_spawn_support_observation_archive.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": OBSERVATION_PROFILE_KEY,
        "archive_role": role,
        "stream_domain_hex": stream_domain.hex(),
        "stream_seed": seed,
        "records_per_empty_cardinality": per_cardinality,
        "empty_cardinality_min": 1,
        "empty_cardinality_max": 16,
        "total_record_count": len(records),
        "observation_fields": [
            "post_swipe_empty_cardinality",
            "selected_sorted_empty_ordinal",
            "spawned_rank",
            "support_valid",
        ],
        "packed_records_hex": packed.hex(),
        "packed_records_sha256": hashlib.sha256(packed).hexdigest(),
        "invalid_support_observation_count": sum(not row[3] for row in records),
        "source_target_episode_identity_present": False,
        "deterministic_fixture_not_physical_randomness_evidence": True,
    }
    return {**payload, identity: content_id(domain, payload)}


def _candidate_covers(
    candidate: str, empty_count: int, ordinal: int, valid: bool
) -> bool:
    if not valid:
        return False
    if candidate == "ALL_SORTED_EMPTY_ORDINALS":
        return 0 <= ordinal < empty_count
    if candidate == "FIRST_EMPTY_ORDINAL_ONLY":
        return ordinal == 0
    if candidate == "LAST_EMPTY_ORDINAL_ONLY":
        return ordinal == empty_count - 1
    if candidate == "EVEN_EMPTY_ORDINALS_ONLY":
        return ordinal % 2 == 0
    _fail("support candidate grammar changed")


def _support_proposal_document(
    source_archive: dict[str, Any], validation_archive: dict[str, Any]
) -> dict[str, Any]:
    source_records = _source_support_records()
    validation_records = _validation_support_records()
    evaluations: list[dict[str, Any]] = []
    selected: list[str] = []
    selected_validation_passed = False
    for candidate in SUPPORT_CANDIDATES:
        source_violations = sum(
            not _candidate_covers(candidate, empty_count, ordinal, valid)
            for empty_count, ordinal, _, valid in source_records
        )
        validation_violations = sum(
            not _candidate_covers(candidate, empty_count, ordinal, valid)
            for empty_count, ordinal, _, valid in validation_records
        )
        source_selected = source_violations == 0
        validation_passed = validation_violations == 0
        if source_selected:
            selected.append(candidate)
            if candidate == SELECTED_SUPPORT_RULE:
                selected_validation_passed = validation_passed
        evaluations.append(
            {
                "candidate": candidate,
                "source_violation_count": source_violations,
                "heldout_validation_violation_count": validation_violations,
                "selected_from_source": source_selected,
                "heldout_validation_passed": validation_passed,
            }
        )
    if selected != [SELECTED_SUPPORT_RULE] or not selected_validation_passed:
        _fail("support proposal replay is not unique and heldout-valid")
    payload = {
        "schema": "acfqp.standard_2048_spawn_support_proposal.v2",
        "schema_version": SCHEMA_VERSION,
        "support_source_archive_id": source_archive["support_source_archive_id"],
        "support_validation_archive_id": validation_archive[
            "support_validation_archive_id"
        ],
        "candidate_meta_grammar": list(SUPPORT_CANDIDATES),
        "candidate_evaluations": evaluations,
        "selected_support_rule": SELECTED_SUPPORT_RULE,
        "selected_rule_semantics": (
            "ENUMERATE_EVERY_SORTED_POST_SWIPE_EMPTY_CELL_AS_POSSIBLE_SPAWN"
        ),
        "selected_uniquely_from_source_raw_observations": True,
        "heldout_validation_not_used_for_selection": True,
        "heldout_support_validation_passed": True,
        "fixed_human_meta_grammar": True,
        "open_ended_support_invention_claimed": False,
    }
    return {**payload, "support_proposal_id": content_id(
        CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN, payload
    )}


def support_ordinals_from_proposal_v2(
    *, support_proposal_id: str, selected_support_rule: str, empty_count: int
) -> tuple[int, ...]:
    if (
        type(support_proposal_id) is not str
        or len(support_proposal_id) != 64
        or selected_support_rule != SELECTED_SUPPORT_RULE
        or type(empty_count) is not int
        or not 1 <= empty_count <= 16
    ):
        _fail("support proposal execution input changed")
    return tuple(range(empty_count))


def _support_counts(
    records: tuple[tuple[int, int, int, bool], ...]
) -> dict[int, list[int]]:
    counts = {empty_count: [0] * empty_count for empty_count in range(1, 17)}
    for empty_count, ordinal, _, valid in records:
        if valid:
            counts[empty_count][ordinal] += 1
    return counts


def _support_interval_document(
    source_archive: dict[str, Any],
    validation_archive: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    source = _source_support_records()
    validation = _validation_support_records()
    source_counts = _support_counts(source)
    validation_counts = _support_counts(validation)
    position_rows: list[dict[str, Any]] = []
    validation_position_pass = True
    for empty_count in range(1, 17):
        categories: list[dict[str, Any]] = []
        for ordinal, count in enumerate(source_counts[empty_count]):
            empirical = Fraction(count, SOURCE_RECORDS_PER_CARDINALITY)
            lower = max(Fraction(), empirical - POSITION_RADIUS)
            upper = min(Fraction(1), empirical + POSITION_RADIUS)
            validation_empirical = Fraction(
                validation_counts[empty_count][ordinal],
                VALIDATION_RECORDS_PER_CARDINALITY,
            )
            inside = lower <= validation_empirical <= upper
            validation_position_pass &= inside
            categories.append(
                {
                    "sorted_empty_ordinal": ordinal,
                    "source_count": count,
                    "source_empirical_probability": _fdoc(empirical),
                    "probability_lower": _fdoc(lower),
                    "probability_upper": _fdoc(upper),
                    "heldout_validation_count": validation_counts[empty_count][ordinal],
                    "heldout_validation_empirical_probability": _fdoc(
                        validation_empirical
                    ),
                    "heldout_inside_source_interval": inside,
                }
            )
        if not (
            sum((_fraction_from_document(row["probability_lower"]) for row in categories), Fraction())
            <= 1
            <= sum((_fraction_from_document(row["probability_upper"]) for row in categories), Fraction())
        ):
            _fail("position interval box misses the simplex")
        position_rows.append(
            {
                "post_swipe_empty_cardinality": empty_count,
                "source_record_count": SOURCE_RECORDS_PER_CARDINALITY,
                "heldout_validation_record_count": VALIDATION_RECORDS_PER_CARDINALITY,
                "categories": categories,
            }
        )
    source_rank_two = sum(row[2] == 2 for row in source)
    validation_rank_two = sum(row[2] == 2 for row in validation)
    source_rank_probability = Fraction(source_rank_two, len(source))
    rank_lower = max(Fraction(), source_rank_probability - RANK_TWO_RADIUS)
    rank_upper = min(Fraction(1), source_rank_probability + RANK_TWO_RADIUS)
    validation_rank_probability = Fraction(validation_rank_two, len(validation))
    validation_rank_pass = rank_lower <= validation_rank_probability <= rank_upper
    taylor_lower = sum(
        (Fraction(16) ** term) / math.factorial(term) for term in range(10)
    )
    if (
        not validation_position_pass
        or not validation_rank_pass
        or not taylor_lower > 275000
    ):
        _fail("partial dynamics interval validation changed")
    payload = {
        "schema": "acfqp.standard_2048_partial_spawn_dynamics_interval.v2",
        "schema_version": SCHEMA_VERSION,
        "support_source_archive_id": source_archive["support_source_archive_id"],
        "support_validation_archive_id": validation_archive[
            "support_validation_archive_id"
        ],
        "support_proposal_id": proposal["support_proposal_id"],
        "selected_support_rule": SELECTED_SUPPORT_RULE,
        "position_radius": _fdoc(POSITION_RADIUS),
        "position_intervals": position_rows,
        "rank_two_source_count": source_rank_two,
        "rank_two_source_empirical_probability": _fdoc(source_rank_probability),
        "rank_two_probability_lower": _fdoc(rank_lower),
        "rank_two_probability_upper": _fdoc(rank_upper),
        "rank_two_heldout_validation_count": validation_rank_two,
        "rank_two_heldout_validation_empirical_probability": _fdoc(
            validation_rank_probability
        ),
        "rank_two_heldout_inside_source_interval": validation_rank_pass,
        "unknown_support_source_count": sum(not row[3] for row in source),
        "unknown_support_probability_lower": _fdoc(Fraction()),
        "unknown_support_probability_upper": _fdoc(UNKNOWN_SUPPORT_MASS_UPPER),
        "heldout_position_intervals_passed": validation_position_pass,
        "hoeffding_exponent": 16,
        "union_bound_coefficient": 275,
        "exp_sixteen_taylor_last_term": 9,
        "exp_sixteen_rational_lower_bound": _fdoc(taylor_lower),
        "conditional_confidence_lower": _fdoc(CONDITIONAL_CONFIDENCE_LOWER),
        "confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_replay_does_not_establish_iid": True,
    }
    return {**payload, "partial_dynamics_interval_id": content_id(
        CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN,
        payload,
    )}


@dataclass(frozen=True, slots=True)
class Standard2048SpawnSupportEvidenceV2:
    document: dict[str, Any]
    source_archive_id: str
    validation_archive_id: str
    support_proposal_id: str
    partial_dynamics_interval_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(canonical_json_bytes(self.document))


def build_standard_2048_spawn_support_evidence_v2(
) -> Standard2048SpawnSupportEvidenceV2:
    source = _support_archive_document(source=True)
    validation = _support_archive_document(source=False)
    proposal = _support_proposal_document(source, validation)
    interval = _support_interval_document(source, validation, proposal)
    return Standard2048SpawnSupportEvidenceV2(
        {
            "source_archive": source,
            "validation_archive": validation,
            "proposal": proposal,
            "interval": interval,
        },
        source["support_source_archive_id"],
        validation["support_validation_archive_id"],
        proposal["support_proposal_id"],
        interval["partial_dynamics_interval_id"],
    )


def verify_standard_2048_spawn_support_evidence_v2(
    evidence: Standard2048SpawnSupportEvidenceV2,
) -> Standard2048SpawnSupportEvidenceV2:
    if type(evidence) is not Standard2048SpawnSupportEvidenceV2:
        _fail("support evidence type changed")
    expected = build_standard_2048_spawn_support_evidence_v2()
    if canonical_json_bytes(evidence.document) != canonical_json_bytes(expected.document):
        _fail("support evidence differs from independent raw replay")
    return evidence


def _state_document(state: Swipe2048State) -> dict[str, Any]:
    return {"board_ranks": list(state.board), "status": state.status.value}


def _state_from_document(document: Mapping[str, Any]) -> Swipe2048State:
    if type(document) is not dict or set(document) != {"board_ranks", "status"}:
        _fail("state document changed")
    try:
        state = Swipe2048State(
            tuple(document["board_ranks"]), Swipe2048Status(document["status"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error(
            "state document is invalid"
        ) from error
    if state_from_board_v1(state.board) != state:
        _fail("state status is not derived from its board")
    return state


def _row_key(
    state: Swipe2048State, action: Swipe2048Action
) -> tuple[tuple[int, ...], str, str]:
    representative, transported_action, _ = canonicalize_state_action_v1(state, action)
    return (
        representative.board,
        representative.status.value,
        transported_action.value,
    )


def _key_document(key: tuple[tuple[int, ...], str, str]) -> dict[str, Any]:
    board, status, action = key
    return {
        "state": {"board_ranks": list(board), "status": status},
        "action": action,
    }


@dataclass(frozen=True, slots=True)
class Standard2048SupportPartialOutcomeV2:
    spawn_rank: int
    sorted_empty_ordinal: int
    position_probability_lower: Fraction
    position_probability_upper: Fraction
    next_state: Swipe2048State
    merge_score: int
    represented_support_outcome_count: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "position_probability_lower", Fraction(self.position_probability_lower)
        )
        object.__setattr__(
            self, "position_probability_upper", Fraction(self.position_probability_upper)
        )
        if (
            self.spawn_rank not in (1, 2)
            or type(self.sorted_empty_ordinal) is not int
            or self.sorted_empty_ordinal < 0
            or not 0 <= self.position_probability_lower
            <= self.position_probability_upper
            <= 1
            or type(self.next_state) is not Swipe2048State
            or type(self.merge_score) is not int
            or self.merge_score < 0
            or type(self.represented_support_outcome_count) is not int
            or self.represented_support_outcome_count <= 0
        ):
            _fail("partial outcome changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "spawn_rank": self.spawn_rank,
            "sorted_empty_ordinal": self.sorted_empty_ordinal,
            "position_probability_lower": _fdoc(self.position_probability_lower),
            "position_probability_upper": _fdoc(self.position_probability_upper),
            "next_state": _state_document(self.next_state),
            "merge_score": self.merge_score,
            "represented_support_outcome_count": self.represented_support_outcome_count,
        }


@dataclass(frozen=True, slots=True)
class Standard2048SupportPartialRowV2:
    state: Swipe2048State
    action: Swipe2048Action
    outcomes: tuple[Standard2048SupportPartialOutcomeV2, ...]
    support_outcome_count: int
    partial_dynamics_interval_id: str
    support_proposal_id: str
    unknown_support_mass_upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.state) is not Swipe2048State
            or canonicalize_state_v1(self.state)[0] != self.state
            or type(self.action) is not Swipe2048Action
            or self.action not in legal_actions_v1(self.state.board)
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(type(row) is not Standard2048SupportPartialOutcomeV2 for row in self.outcomes)
            or type(self.support_outcome_count) is not int
            or self.support_outcome_count <= 0
            or type(self.partial_dynamics_interval_id) is not str
            or len(self.partial_dynamics_interval_id) != 64
            or type(self.support_proposal_id) is not str
            or len(self.support_proposal_id) != 64
        ):
            _fail("partial row changed")
        object.__setattr__(
            self, "unknown_support_mass_upper", Fraction(self.unknown_support_mass_upper)
        )
        if not 0 <= self.unknown_support_mass_upper < 1:
            _fail("unknown support mass changed")
        for rank in (1, 2):
            rank_rows = tuple(row for row in self.outcomes if row.spawn_rank == rank)
            if not (
                sum((row.position_probability_lower for row in rank_rows), Fraction())
                <= 1
                <= sum((row.position_probability_upper for row in rank_rows), Fraction())
            ):
                _fail("position probability box does not intersect the simplex")
        if (
            sum(row.represented_support_outcome_count for row in self.outcomes)
            != self.support_outcome_count
        ):
            _fail("partial support count changed")

    @property
    def key(self) -> tuple[tuple[int, ...], str, str]:
        return self.state.board, self.state.status.value, self.action.value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_support_partial_spawn_row.v2",
            "schema_version": SCHEMA_VERSION,
            "state": _state_document(self.state),
            "action": self.action.value,
            "partial_dynamics_interval_id": self.partial_dynamics_interval_id,
            "support_proposal_id": self.support_proposal_id,
            "unknown_support_mass_upper": _fdoc(self.unknown_support_mass_upper),
            "outcomes": [row.to_document() for row in self.outcomes],
            "support_outcome_count": self.support_outcome_count,
            "support_and_position_law_observation_derived": True,
            "spawn_rank_probability_point_value_absent": True,
            "materialized_only_after_failed_proof": True,
        }

    @property
    def row_id(self) -> str:
        return content_id(DOMAINS["row"], self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "partial_row_id": self.row_id}


def _materialize_partial_row(
    key: tuple[tuple[int, ...], str, str],
    interval_id: str,
    support_proposal_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
) -> Standard2048SupportPartialRowV2:
    """Execute the learned support program without reading exact transition rows."""

    board, status_value, action_value = key
    state = Swipe2048State(board, Swipe2048Status(status_value))
    action = Swipe2048Action(action_value)
    moved, merge_score, changed = swipe_board_v1(state.board, action)
    if not changed:
        _fail("legal action did not change the board")
    empty_cells = tuple(index for index, rank in enumerate(moved) if rank == 0)
    ordinals = support_ordinals_from_proposal_v2(
        support_proposal_id=support_proposal_id,
        selected_support_rule=SELECTED_SUPPORT_RULE,
        empty_count=len(empty_cells),
    )
    if ordinals != tuple(range(len(empty_cells))):
        _fail("selected support program output changed")
    bounds = position_bounds.get(len(empty_cells))
    if bounds is None or len(bounds) != len(empty_cells):
        _fail("position interval cardinality changed")
    grouped: dict[tuple[int, int, tuple[int, ...], str, int, Fraction, Fraction], int] = {}
    for ordinal in ordinals:
        for rank in (1, 2):
            spawned = list(moved)
            spawned[empty_cells[ordinal]] = rank
            representative, _ = canonicalize_state_v1(
                state_from_board_v1(tuple(spawned))
            )
            lower, upper = bounds[ordinal]
            group_key = (
                rank,
                ordinal,
                representative.board,
                representative.status.value,
                merge_score,
                lower,
                upper,
            )
            grouped[group_key] = grouped.get(group_key, 0) + 1
    outcomes = tuple(
        Standard2048SupportPartialOutcomeV2(
            rank,
            ordinal,
            lower,
            upper,
            Swipe2048State(next_board, Swipe2048Status(next_status)),
            merge_score,
            count,
        )
        for (
            rank, ordinal, next_board, next_status, merge_score, lower, upper
        ), count in sorted(grouped.items())
    )
    return Standard2048SupportPartialRowV2(
        state,
        action,
        outcomes,
        2 * len(ordinals),
        interval_id,
        support_proposal_id,
        UNKNOWN_SUPPORT_MASS_UPPER,
    )


def _model_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
) -> dict[str, Any]:
    row_documents = [rows[key].to_document() for key in sorted(rows)]
    payload = {
        "schema": "acfqp.standard_2048_support_partial_d4_world_model.v2",
        "schema_version": SCHEMA_VERSION,
        "semantics": "STANDARD_4X4_SWIPE_THEN_OBSERVATION_DERIVED_PARTIAL_SPAWN_V2",
        "abstraction": "D4_QUOTIENT_WITH_SUPPORT_POSITION_RANK_UNKNOWN_INTERVALS_V2",
        "query_neutral": True,
        "support_source_archive_id": source_archive_id,
        "support_validation_archive_id": validation_archive_id,
        "support_proposal_id": support_proposal_id,
        "partial_dynamics_interval_id": interval_id,
        "support_position_rank_observation_derived": True,
        "unknown_support_mass_bounded": True,
        "unknown_support_score_upper_uses_finite_mass_horizon_cap": True,
        "rectangular_rowwise_interval_relaxation": True,
        "rows": row_documents,
        "row_count": len(row_documents),
        "support_outcome_count": sum(row.support_outcome_count for row in rows.values()),
    }
    return {**payload, "partial_world_model_id": content_id(DOMAINS["model"], payload)}


@dataclass(frozen=True, slots=True)
class _RobustValueV1:
    score_lower: Fraction
    score_upper: Fraction
    loss_upper: Fraction
    selected_action: Swipe2048Action | None


@dataclass(frozen=True, slots=True)
class _ExactValueV1:
    expected_score: Fraction
    loss_probability: Fraction
    selected_action: Swipe2048Action | None


def _better_robust(candidate: _RobustValueV1, current: _RobustValueV1 | None) -> bool:
    if current is None:
        return True
    candidate_key = (
        candidate.score_lower,
        -candidate.loss_upper,
        candidate.score_upper,
        -ACTION_ORDER.index(candidate.selected_action),
    )
    current_key = (
        current.score_lower,
        -current.loss_upper,
        current.score_upper,
        -ACTION_ORDER.index(current.selected_action),
    )
    return candidate_key > current_key


def _better_exact(candidate: _ExactValueV1, current: _ExactValueV1 | None) -> bool:
    if current is None:
        return True
    candidate_key = (
        candidate.expected_score,
        -candidate.loss_probability,
        -ACTION_ORDER.index(candidate.selected_action),
    )
    current_key = (
        current.expected_score,
        -current.loss_probability,
        -ACTION_ORDER.index(current.selected_action),
    )
    return candidate_key > current_key


def _box_expectation_extreme(
    values: tuple[Fraction, ...],
    lower_bounds: tuple[Fraction, ...],
    upper_bounds: tuple[Fraction, ...],
    *,
    maximize: bool,
) -> Fraction:
    """Optimize one linear expectation over a box-constrained probability simplex."""

    if (
        not values
        or len(values) != len(lower_bounds)
        or len(values) != len(upper_bounds)
        or any(not 0 <= lower <= upper <= 1 for lower, upper in zip(lower_bounds, upper_bounds, strict=True))
    ):
        _fail("position probability box changed")
    probabilities = list(lower_bounds)
    remaining = Fraction(1) - sum(probabilities, Fraction())
    if remaining < 0 or sum(upper_bounds, Fraction()) < 1:
        _fail("position probability box misses the simplex")
    order = sorted(
        range(len(values)), key=lambda index: values[index], reverse=maximize
    )
    for index in order:
        addition = min(remaining, upper_bounds[index] - probabilities[index])
        probabilities[index] += addition
        remaining -= addition
        if remaining == 0:
            break
    if remaining:
        _fail("position probability optimization did not close")
    return sum(
        (probability * value for probability, value in zip(probabilities, values, strict=True)),
        Fraction(),
    )


def _unknown_spawn_score_upper(
    state: Swipe2048State, *, merge_score: int, remaining: int
) -> Fraction:
    if type(merge_score) is not int or merge_score < 0 or remaining < 1:
        _fail("unknown-support score-cap input changed")
    future_steps = remaining - 1
    post_spawn_mass_upper = sum((1 << rank) for rank in state.board if rank) + 4
    return Fraction(
        merge_score
        + future_steps * post_spawn_mass_upper
        + 2 * future_steps * (future_steps - 1)
    )


def _missing_frontier(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
) -> tuple[tuple[tuple[int, ...], str, str], ...]:
    missing: set[tuple[tuple[int, ...], str, str]] = set()
    visited: set[tuple[tuple[int, ...], str, int]] = set()

    def walk(state: Swipe2048State, remaining: int) -> None:
        representative, _ = canonicalize_state_v1(state)
        visit_key = (representative.board, representative.status.value, remaining)
        if (
            remaining == 0
            or representative.status is not Swipe2048Status.ACTIVE
            or visit_key in visited
        ):
            return
        visited.add(visit_key)
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                missing.add(key)
            else:
                for outcome in row.outcomes:
                    walk(outcome.next_state, remaining - 1)

    walk(root, horizon)
    return tuple(sorted(missing))


def _solve_robust(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[_RobustValueV1, tuple[str, ...]]:
    dependencies: set[str] = set()

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _RobustValueV1:
        state = Swipe2048State(board, Swipe2048Status(status_value))
        representative, _ = canonicalize_state_v1(state)
        if remaining == 0 or representative.status is Swipe2048Status.WON:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(), None)
        if representative.status is Swipe2048Status.LOST:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(1), None)
        best: _RobustValueV1 | None = None
        for action in legal_actions_v1(representative.board):
            key = _row_key(representative, action)
            row = rows.get(key)
            if row is None:
                _fail("robust solve reached an unresolved support row")
            dependencies.add(row.row_id)
            by_rank: dict[int, tuple[Fraction, Fraction, Fraction]] = {}
            for rank in (1, 2):
                rank_outcomes = tuple(
                    outcome for outcome in row.outcomes if outcome.spawn_rank == rank
                )
                lower_values: list[Fraction] = []
                upper_values: list[Fraction] = []
                loss_values: list[Fraction] = []
                for outcome in rank_outcomes:
                    child = solve(
                        outcome.next_state.board,
                        outcome.next_state.status.value,
                        remaining - 1,
                    )
                    lower_values.append(outcome.merge_score + child.score_lower)
                    upper_values.append(outcome.merge_score + child.score_upper)
                    loss_values.append(child.loss_upper)
                lower_bounds = tuple(
                    outcome.position_probability_lower for outcome in rank_outcomes
                )
                upper_bounds = tuple(
                    outcome.position_probability_upper for outcome in rank_outcomes
                )
                by_rank[rank] = (
                    _box_expectation_extreme(
                        tuple(lower_values), lower_bounds, upper_bounds, maximize=False
                    ),
                    _box_expectation_extreme(
                        tuple(upper_values), lower_bounds, upper_bounds, maximize=True
                    ),
                    _box_expectation_extreme(
                        tuple(loss_values), lower_bounds, upper_bounds, maximize=True
                    ),
                )
            lower_endpoints = tuple(
                (1 - probability) * by_rank[1][0] + probability * by_rank[2][0]
                for probability in (rank_two_lower, rank_two_upper)
            )
            upper_endpoints = tuple(
                (1 - probability) * by_rank[1][1] + probability * by_rank[2][1]
                for probability in (rank_two_lower, rank_two_upper)
            )
            loss_endpoints = tuple(
                (1 - probability) * by_rank[1][2] + probability * by_rank[2][2]
                for probability in (rank_two_lower, rank_two_upper)
            )
            known_upper = max(upper_endpoints)
            unknown_score_upper = _unknown_spawn_score_upper(
                representative,
                merge_score=row.outcomes[0].merge_score,
                remaining=remaining,
            )
            score_upper = known_upper + row.unknown_support_mass_upper * max(
                Fraction(), unknown_score_upper - known_upper
            )
            candidate = _RobustValueV1(
                (1 - row.unknown_support_mass_upper) * min(lower_endpoints),
                score_upper,
                min(
                    Fraction(1),
                    row.unknown_support_mass_upper
                    + (1 - row.unknown_support_mass_upper) * max(loss_endpoints),
                ),
                action,
            )
            if _better_robust(candidate, best):
                best = candidate
        if best is None:
            return _RobustValueV1(Fraction(), Fraction(), Fraction(1), None)
        return best

    representative, transform = canonicalize_state_v1(root)
    result = solve(representative.board, representative.status.value, horizon)
    if result.selected_action is None:
        return result, tuple(sorted(dependencies))
    lifted = transform_action_v1(result.selected_action, inverse_d4(transform))
    return (
        _RobustValueV1(
            result.score_lower, result.score_upper, result.loss_upper, lifted
        ),
        tuple(sorted(dependencies)),
    )


def _audit_document(
    rows: Mapping[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> dict[str, Any]:
    model = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )
    missing = _missing_frontier(rows, root, horizon)
    payload: dict[str, Any] = {
        "schema": "acfqp.standard_2048_support_partial_model_audit.v2",
        "schema_version": SCHEMA_VERSION,
        "partial_world_model_id": model["partial_world_model_id"],
        "partial_dynamics_interval_id": interval_id,
        "support_proposal_id": support_proposal_id,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
        "status": "FAILED_PROOF_FRONTIER" if missing else "CERTIFIED_PARTIAL_DYNAMICS_ROBUST",
        "missing_frontier": [_key_document(key) for key in missing],
        "missing_frontier_count": len(missing),
    }
    if missing:
        payload.update(
            {
                "selected_action": None,
                "robust_score_lower": None,
                "robust_score_upper": None,
                "robust_loss_probability_upper": None,
                "ordered_dependency_row_ids": [],
                "robust_plan_id": None,
            }
        )
    else:
        value, dependencies = _solve_robust(
            rows, root, horizon, rank_two_lower, rank_two_upper
        )
        if value.selected_action is None:
            _fail("active root produced no interval-robust action")
        plan_payload = {
            "schema": "acfqp.standard_2048_support_interval_robust_plan.v2",
            "schema_version": SCHEMA_VERSION,
            "partial_world_model_id": model["partial_world_model_id"],
            "partial_dynamics_interval_id": interval_id,
            "support_proposal_id": support_proposal_id,
            "root_state": _state_document(root),
            "horizon": horizon,
            "objective": "MAX_SUPPORT_POSITION_RANK_ROBUST_SCORE_THEN_MIN_LOSS_V2",
            "selected_action": value.selected_action.value,
            "robust_score_lower": _fdoc(value.score_lower),
            "robust_score_upper": _fdoc(value.score_upper),
            "robust_loss_probability_upper": _fdoc(value.loss_upper),
            "ordered_dependency_row_ids": list(dependencies),
        }
        payload.update(
            {
                "selected_action": value.selected_action.value,
                "robust_score_lower": _fdoc(value.score_lower),
                "robust_score_upper": _fdoc(value.score_upper),
                "robust_loss_probability_upper": _fdoc(value.loss_upper),
                "ordered_dependency_row_ids": list(dependencies),
                "robust_plan_id": content_id(DOMAINS["plan"], plan_payload),
            }
        )
    return {**payload, "audit_id": content_id(DOMAINS["audit"], payload)}


def _recover_to_certificate(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    root: Swipe2048State,
    horizon: int,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    transactions: list[dict[str, Any]] = []
    added_rows = 0
    added_support = 0
    for transaction_index in range(1, horizon + 2):
        failed = _audit_document(
            rows,
            root,
            horizon,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        if failed["status"] == "CERTIFIED_PARTIAL_DYNAMICS_ROBUST":
            return transactions, failed, added_rows, added_support
        frontier = tuple(
            _row_key(
                _state_from_document(item["state"]),
                Swipe2048Action(item["action"]),
            )
            for item in failed["missing_frontier"]
        )
        predecessor = _model_document(
            rows,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
        )[
            "partial_world_model_id"
        ]
        recovered: list[Standard2048SupportPartialRowV2] = []
        for key in frontier:
            if key not in rows:
                row = _materialize_partial_row(
                    key, interval_id, support_proposal_id, position_bounds
                )
                rows[key] = row
                recovered.append(row)
                added_rows += 1
                added_support += row.support_outcome_count
        successor = _model_document(
            rows,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
        )[
            "partial_world_model_id"
        ]
        transactions.append(
            {
                "transaction_index": transaction_index,
                "failed_audit_id": failed["audit_id"],
                "failed_status": failed["status"],
                "predecessor_partial_world_model_id": predecessor,
                "recovered_frontier_count": len(recovered),
                "recovered_partial_row_ids": [row.row_id for row in recovered],
                "recovered_support_outcome_count": sum(
                    row.support_outcome_count for row in recovered
                ),
                "successor_partial_world_model_id": successor,
                "ground_support_access_before_failed_audit": False,
                "exact_spawn_or_position_probability_accessed_by_recovery": False,
            }
        )
    _fail("bounded interval recovery did not converge")


def _direct_plan(root: Swipe2048State, horizon: int) -> dict[str, Any]:
    touched_rows: set[tuple[tuple[int, ...], str, str]] = set()
    outcome_count = 0

    @lru_cache(maxsize=None)
    def solve(board: tuple[int, ...], status_value: str, remaining: int) -> _ExactValueV1:
        nonlocal outcome_count
        state = Swipe2048State(board, Swipe2048Status(status_value))
        if remaining == 0 or state.status is Swipe2048Status.WON:
            return _ExactValueV1(Fraction(), Fraction(), None)
        if state.status is Swipe2048Status.LOST:
            return _ExactValueV1(Fraction(), Fraction(1), None)
        best: _ExactValueV1 | None = None
        for action in legal_actions_v1(state.board):
            key = (state.board, state.status.value, action.value)
            outcomes = step_v1(state, action)
            if key not in touched_rows:
                touched_rows.add(key)
                outcome_count += len(outcomes)
            score = Fraction()
            loss = Fraction()
            for outcome in outcomes:
                child = solve(
                    outcome.next_state.board,
                    outcome.next_state.status.value,
                    remaining - 1,
                )
                score += outcome.probability * (
                    outcome.merge_score + child.expected_score
                )
                loss += outcome.probability * child.loss_probability
            candidate = _ExactValueV1(score, loss, action)
            if _better_exact(candidate, best):
                best = candidate
        if best is None:
            return _ExactValueV1(Fraction(), Fraction(1), None)
        return best

    value = solve(root.board, root.status.value, horizon)
    if value.selected_action is None:
        _fail("matched direct root produced no action")
    payload = {
        "schema": "acfqp.standard_2048_support_matched_direct.v2",
        "schema_version": SCHEMA_VERSION,
        "root_state": _state_document(root),
        "horizon": horizon,
        "objective": "MAX_EXACT_EXPECTED_SCORE_THEN_MIN_LOSS_V1",
        "selected_action": value.selected_action.value,
        "expected_merge_score": _fdoc(value.expected_score),
        "loss_probability_within_horizon": _fdoc(value.loss_probability),
        "ground_state_action_row_count": len(touched_rows),
        "ground_outcome_count": outcome_count,
        "cold_model_per_decision": True,
        "evaluation_lane_only": True,
        "partial_model_or_source_observations_used": False,
    }
    return {**payload, "matched_direct_plan_id": content_id(DOMAINS["direct"], payload)}


def _preregistration_document(
    evidence: Standard2048SpawnSupportEvidenceV2,
) -> dict[str, Any]:
    evidence_document = evidence.to_document()
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_support_preregistration.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "environment_semantics": "STANDARD_4X4_WHOLE_BOARD_SWIPE_THEN_SPAWN_V1",
        "registered_fresh_root_states": [
            _state_document(state_from_board_v1(board))
            for board in REGISTERED_FRESH_BOARDS
        ],
        "planning_horizon": PLANNING_HORIZON,
        "episode_decision_count": EPISODE_DECISION_COUNT,
        "heldout_episode_seeds": list(HELDOUT_EPISODE_SEEDS),
        "support_source_seed": SOURCE_SEED,
        "support_validation_seed": VALIDATION_SEED,
        "support_source_record_count": 16 * SOURCE_RECORDS_PER_CARDINALITY,
        "support_validation_record_count": 16 * VALIDATION_RECORDS_PER_CARDINALITY,
        "support_source_archive_id": evidence.source_archive_id,
        "support_validation_archive_id": evidence.validation_archive_id,
        "support_proposal_id": evidence.support_proposal_id,
        "partial_dynamics_interval_id": evidence.partial_dynamics_interval_id,
        "goal_rank": GOAL_RANK,
        "source_and_validation_archives_frozen_before_target_preregistration": True,
        "source_and_target_identities_disjoint": (
            SOURCE_SEED not in HELDOUT_EPISODE_SEEDS
            and VALIDATION_SEED not in HELDOUT_EPISODE_SEEDS
            and len(set(HELDOUT_EPISODE_SEEDS)) == len(HELDOUT_EPISODE_SEEDS)
        ),
        "fresh_roots_not_equal_to_v1_registered_root": all(
            board != LEGACY_V1_ROOT_BOARD for board in REGISTERED_FRESH_BOARDS
        ),
        "episode_seeds_and_matched_controls_frozen_before_model_construction": True,
        "observation_derived_dynamics_components": [
            "SPAWN_CELL_SUPPORT_PROGRAM",
            "SPAWN_POSITION_INTERVALS",
            "SPAWN_RANK_INTERVAL",
            "UNKNOWN_SUPPORT_MASS_BOUND",
        ],
        "known_structural_mechanics": ["WHOLE_BOARD_SWIPE", "D4_TRANSPORT"],
        "support_validation_passed_before_target_execution": evidence_document[
            "proposal"
        ]["heldout_support_validation_passed"],
    }
    return {
        **payload,
        "support_preregistration_id": content_id(DOMAINS["preregistration"], payload),
    }


def _run_episode(
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2],
    *,
    episode_index: int,
    initial_board: tuple[int, ...],
    seed: str,
    preregistration_id: str,
    source_archive_id: str,
    validation_archive_id: str,
    support_proposal_id: str,
    interval_id: str,
    position_bounds: Mapping[int, tuple[tuple[Fraction, Fraction], ...]],
    rank_two_lower: Fraction,
    rank_two_upper: Fraction,
) -> tuple[dict[str, Any], int, int, int, int]:
    initial_state = state_from_board_v1(initial_board)
    state = initial_state
    initial_model_id = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )[
        "partial_world_model_id"
    ]
    decisions: list[dict[str, Any]] = []
    episode_rows = 0
    episode_support = 0
    direct_rows = 0
    direct_outcomes = 0
    for decision_index in range(EPISODE_DECISION_COUNT):
        base_audit = _audit_document(
            rows,
            state,
            PLANNING_HORIZON,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            rank_two_lower,
            rank_two_upper,
        )
        transactions, certified, added_rows, added_support = _recover_to_certificate(
            rows,
            state,
            PLANNING_HORIZON,
            source_archive_id,
            validation_archive_id,
            support_proposal_id,
            interval_id,
            position_bounds,
            rank_two_lower,
            rank_two_upper,
        )
        direct = _direct_plan(state, PLANNING_HORIZON)
        if certified["selected_action"] != direct["selected_action"]:
            _fail("interval-robust and matched-direct selected actions differ")
        exact_score = _fraction_from_document(direct["expected_merge_score"])
        exact_loss = _fraction_from_document(direct["loss_probability_within_horizon"])
        if not (
            _fraction_from_document(certified["robust_score_lower"])
            <= exact_score
            <= _fraction_from_document(certified["robust_score_upper"])
            and exact_loss
            <= _fraction_from_document(certified["robust_loss_probability_upper"])
        ):
            _fail("exact matched value escaped the registered robust envelope")
        action = Swipe2048Action(certified["selected_action"])
        target_outcomes = step_v1(state, action)
        selected, digest = select_seeded_outcome_v1(
            target_outcomes, seed=seed, decision_index=decision_index
        )
        decision_payload = {
            "episode_index": episode_index,
            "decision_index": decision_index,
            "state_before_decision": _state_document(state),
            "base_audit": base_audit,
            "recovery_transactions": transactions,
            "certified_robust_plan": certified,
            "matched_direct_control": direct,
            "selected_action_agrees_with_matched_direct": True,
            "exact_direct_value_inside_robust_envelope": True,
            "incremental_partial_row_count": added_rows,
            "incremental_support_outcome_count": added_support,
            "executed_target_transition": {
                "target_seed": seed,
                "target_decision_index": decision_index,
                "spawn_tape_digest": digest,
                "selected_action": action.value,
                "selected_outcome_probability_evaluation_only": _fdoc(
                    selected.probability
                ),
                "spawned_cell": selected.spawned_cell,
                "spawned_rank": selected.spawned_rank,
                "merge_score": selected.merge_score,
                "successor_state": _state_document(selected.next_state),
                "target_observation_not_used_before_plan_freeze": True,
            },
        }
        decisions.append(decision_payload)
        state = selected.next_state
        episode_rows += added_rows
        episode_support += added_support
        direct_rows += direct["ground_state_action_row_count"]
        direct_outcomes += direct["ground_outcome_count"]
    final_model_id = _model_document(
        rows,
        source_archive_id,
        validation_archive_id,
        support_proposal_id,
        interval_id,
    )[
        "partial_world_model_id"
    ]
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_receding_episode.v2",
        "schema_version": SCHEMA_VERSION,
        "support_preregistration_id": preregistration_id,
        "episode_index": episode_index,
        "heldout_episode_seed": seed,
        "initial_state": _state_document(initial_state),
        "initial_partial_world_model_id": initial_model_id,
        "decisions": decisions,
        "decision_count": len(decisions),
        "terminal_state_after_registered_prefix": _state_document(state),
        "final_partial_world_model_id": final_model_id,
        "incremental_partial_row_count": episode_rows,
        "incremental_support_outcome_count": episode_support,
        "matched_direct_ground_row_count": direct_rows,
        "matched_direct_ground_outcome_count": direct_outcomes,
    }
    return (
        {**payload, "episode_id": content_id(DOMAINS["episode"], payload)},
        episode_rows,
        episode_support,
        direct_rows,
        direct_outcomes,
    )


def _campaign_document() -> dict[str, Any]:
    evidence = build_standard_2048_spawn_support_evidence_v2()
    verify_standard_2048_spawn_support_evidence_v2(evidence)
    evidence_document = evidence.to_document()
    interval = evidence_document["interval"]
    rank_two_lower = Fraction(interval["rank_two_probability_lower"])
    rank_two_upper = Fraction(interval["rank_two_probability_upper"])
    position_bounds = {
        row["post_swipe_empty_cardinality"]: tuple(
            (
                Fraction(category["probability_lower"]),
                Fraction(category["probability_upper"]),
            )
            for category in row["categories"]
        )
        for row in interval["position_intervals"]
    }
    preregistration = _preregistration_document(evidence)
    rows: dict[tuple[tuple[int, ...], str, str], Standard2048SupportPartialRowV2] = {}
    episodes: list[dict[str, Any]] = []
    total_rows = 0
    total_support = 0
    total_direct_rows = 0
    total_direct_outcomes = 0
    for episode_index, (initial_board, seed) in enumerate(
        zip(REGISTERED_FRESH_BOARDS, HELDOUT_EPISODE_SEEDS, strict=True)
    ):
        episode, added_rows, added_support, direct_rows, direct_outcomes = _run_episode(
            rows,
            episode_index=episode_index,
            initial_board=initial_board,
            seed=seed,
            preregistration_id=preregistration["support_preregistration_id"],
            source_archive_id=evidence.source_archive_id,
            validation_archive_id=evidence.validation_archive_id,
            support_proposal_id=evidence.support_proposal_id,
            interval_id=evidence.partial_dynamics_interval_id,
            position_bounds=position_bounds,
            rank_two_lower=rank_two_lower,
            rank_two_upper=rank_two_upper,
        )
        episodes.append(episode)
        total_rows += added_rows
        total_support += added_support
        total_direct_rows += direct_rows
        total_direct_outcomes += direct_outcomes
    final_model = _model_document(
        rows,
        evidence.source_archive_id,
        evidence.validation_archive_id,
        evidence.support_proposal_id,
        evidence.partial_dynamics_interval_id,
    )
    total_decisions = len(HELDOUT_EPISODE_SEEDS) * EPISODE_DECISION_COUNT
    payload = {
        "schema": "acfqp.standard_2048_fresh_board_support_world_model_campaign.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "spawn_support_observation_evidence": evidence_document,
        "support_preregistration": preregistration,
        "episodes": episodes,
        "episode_count": len(episodes),
        "total_receding_decision_count": total_decisions,
        "final_partial_world_model": final_model,
        "partial_model_ground_support_row_count": total_rows,
        "partial_model_support_outcome_count": total_support,
        "matched_direct_total_ground_row_count": total_direct_rows,
        "matched_direct_total_ground_outcome_count": total_direct_outcomes,
        "sample_tax_telemetry": {
            "offline_source_transition_observation_count": (
                16 * SOURCE_RECORDS_PER_CARDINALITY
            ),
            "offline_validation_transition_observation_count": (
                16 * VALIDATION_RECORDS_PER_CARDINALITY
            ),
            "online_target_transition_observation_count": total_decisions,
            "partial_model_support_row_count": total_rows,
            "partial_model_support_outcome_count": total_support,
            "matched_direct_ground_row_count": total_direct_rows,
            "matched_direct_ground_outcome_count": total_direct_outcomes,
            "scalar_crossing_claimed": False,
        },
        "standard_4x4_swipe_spawn_semantics_executed": True,
        "multiple_heldout_seeds_executed": True,
        "longer_receding_rollout_executed": True,
        "persistent_world_model_reused_across_episodes": True,
        "spawn_support_program_observation_derived": True,
        "spawn_position_law_observation_derived_partial": True,
        "spawn_rank_law_observation_derived_partial": True,
        "unknown_support_mass_bounded_from_observations": True,
        "unknown_support_score_upper_uses_finite_mass_horizon_cap": True,
        "fresh_non_v1_boards_executed": True,
        "source_target_identity_separated": True,
        "certificate_failure_triggered_ground_recovery": True,
        "ground_support_rows_materialized_only_after_failed_proof": True,
        "all_selected_actions_match_cold_direct": True,
        "exact_target_values_inside_robust_envelopes": True,
        "multi_step_planning_completed_in_partial_abstract_model": True,
        "formal_exact_iid_claimed": False,
        "unknown_support_complete_learning_claimed": False,
        "open_ended_support_invention_claimed": False,
        "observation_derived_coordinate_invention_claimed": False,
        "full_standard_2048_game_completed": False,
        "real_game_ui_adapter_present": False,
        "broad_sample_efficiency_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "NOT_RUN",
        "workload_economics_gate_status": "NOT_RUN",
    }
    return {**payload, "campaign_id": content_id(DOMAINS["campaign"], payload)}


@dataclass(frozen=True, slots=True)
class Standard2048FreshBoardSupportIndependentVerificationV2:
    campaign_id: str
    support_preregistration_id: str
    source_archive_id: str
    validation_archive_id: str
    support_proposal_id: str
    partial_dynamics_interval_id: str
    final_world_model_id: str
    final_world_model_row_count: int
    total_receding_decision_count: int

    @property
    def verification_id(self) -> str:
        return content_id(
            VERIFICATION_DOMAIN,
            {
                "campaign_id": self.campaign_id,
                "support_preregistration_id": self.support_preregistration_id,
                "source_archive_id": self.source_archive_id,
                "validation_archive_id": self.validation_archive_id,
                "support_proposal_id": self.support_proposal_id,
                "partial_dynamics_interval_id": self.partial_dynamics_interval_id,
                "final_world_model_id": self.final_world_model_id,
                "final_world_model_row_count": self.final_world_model_row_count,
                "total_receding_decision_count": self.total_receding_decision_count,
                "raw_source_and_validation_observations_replayed": True,
                "support_proposal_and_intervals_replayed": True,
                "partial_rows_and_failed_proof_recovery_replayed": True,
                "fresh_board_robust_plans_and_direct_controls_replayed": True,
                "physical_iid_or_full_game_authority_verified": False,
                "official_execution_allowed": False,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.standard_2048_fresh_board_support_independent_verification.v2",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "support_preregistration_id": self.support_preregistration_id,
            "source_archive_id": self.source_archive_id,
            "validation_archive_id": self.validation_archive_id,
            "support_proposal_id": self.support_proposal_id,
            "partial_dynamics_interval_id": self.partial_dynamics_interval_id,
            "final_world_model_id": self.final_world_model_id,
            "final_world_model_row_count": self.final_world_model_row_count,
            "total_receding_decision_count": self.total_receding_decision_count,
            "raw_source_and_validation_observations_replayed": True,
            "support_proposal_and_intervals_replayed": True,
            "partial_rows_and_failed_proof_recovery_replayed": True,
            "fresh_board_robust_plans_and_direct_controls_replayed": True,
            "physical_iid_or_full_game_authority_verified": False,
            "official_execution_allowed": False,
            "independent_verification_id": self.verification_id,
        }


@lru_cache(maxsize=1)
def _expected_campaign_bytes() -> bytes:
    return canonical_json_bytes(_campaign_document())


def verify_standard_2048_fresh_board_support_campaign_bytes_independently_v2(
    raw: bytes,
) -> Standard2048FreshBoardSupportIndependentVerificationV2:
    if type(raw) is not bytes:
        _fail("independent verifier requires exact bytes")
    observed = loads_canonical_json(raw)
    if type(observed) is not dict or canonical_json_bytes(observed) != raw:
        _fail("campaign bytes are not canonical JSON")
    if raw != _expected_campaign_bytes():
        _fail("campaign differs from independent raw and semantic replay")
    campaign_id = parse_content_id(observed["campaign_id"])
    payload = {key: value for key, value in observed.items() if key != "campaign_id"}
    if content_id(DOMAINS["campaign"], payload) != campaign_id:
        _fail("campaign content ID changed")
    evidence = observed["spawn_support_observation_evidence"]
    preregistration = observed["support_preregistration"]
    model = observed["final_partial_world_model"]
    return Standard2048FreshBoardSupportIndependentVerificationV2(
        campaign_id,
        parse_content_id(preregistration["support_preregistration_id"]),
        parse_content_id(evidence["source_archive"]["support_source_archive_id"]),
        parse_content_id(
            evidence["validation_archive"]["support_validation_archive_id"]
        ),
        parse_content_id(evidence["proposal"]["support_proposal_id"]),
        parse_content_id(evidence["interval"]["partial_dynamics_interval_id"]),
        parse_content_id(model["partial_world_model_id"]),
        model["row_count"],
        observed["total_receding_decision_count"],
    )


__all__ = (
    "ConstructionK7Standard2048FreshBoardSupportIndependentVerifierV2Error",
    "Standard2048FreshBoardSupportIndependentVerificationV2",
    "verify_standard_2048_fresh_board_support_campaign_bytes_independently_v2",
)
