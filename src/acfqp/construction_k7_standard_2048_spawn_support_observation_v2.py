"""Observation-derived spawn support and position intervals for standard 2048.

Two identity-separated archives contain raw tuples
``(post-swipe empty cardinality, selected empty ordinal, spawned rank, valid)``.
The source archive selects one support rule from a small preregistered grammar
and constructs rank, position, and unknown-support intervals.  A second archive
is held out from construction and must replay inside those intervals.

The fixture is deterministic and the confidence statement is conditional on
the registered IID/shared-law interpretation.  It is not evidence of physical
randomness or open-ended support invention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "construction_k7_standard_2048_spawn_support_observation_v2"
SOURCE_SEED = "standard-2048-support-source-20260812-v2"
VALIDATION_SEED = "standard-2048-support-validation-20260812-v2"
SOURCE_STREAM_DOMAIN = b"acfqp:standard-2048-spawn-support-source:v2"
VALIDATION_STREAM_DOMAIN = b"acfqp:standard-2048-spawn-support-validation:v2"
SOURCE_RECORDS_PER_CARDINALITY = 8192
VALIDATION_RECORDS_PER_CARDINALITY = 1024
MIN_EMPTY_CARDINALITY = 1
MAX_EMPTY_CARDINALITY = 16
POSITION_RADIUS = Fraction(1, 32)
RANK_TWO_RADIUS = Fraction(1, 128)
UNKNOWN_SUPPORT_MASS_UPPER = Fraction(1, 128)
CONDITIONAL_CONFIDENCE_LOWER = Fraction(999, 1000)
HOEFFDING_EXPONENT = 16
UNION_BOUND_COEFFICIENT = 275
EXP_TAYLOR_LAST_TERM = 9

SUPPORT_CANDIDATES = (
    "ALL_SORTED_EMPTY_ORDINALS",
    "FIRST_EMPTY_ORDINAL_ONLY",
    "LAST_EMPTY_ORDINAL_ONLY",
    "EVEN_EMPTY_ORDINALS_ONLY",
)
SELECTED_SUPPORT_RULE = "ALL_SORTED_EMPTY_ORDINALS"

DOMAINS = {
    "source": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN,
    "validation": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN,
    "proposal": CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN,
    "interval": CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN,
}
if len(DOMAINS) != len(set(DOMAINS.values())):  # pragma: no cover
    raise RuntimeError("support observation domains must be unique")
if not set(DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("support observation domains are not registered")


class ConstructionK7Standard2048SpawnSupportObservationV2Error(ValueError):
    """The raw support archive, proposal, interval, or validation changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SpawnSupportObservationV2Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _record_stream(
    *, domain: bytes, seed: str, records_per_cardinality: int
) -> tuple[tuple[int, int, int, bool], ...]:
    records: list[tuple[int, int, int, bool]] = []
    for empty_count in range(MIN_EMPTY_CARDINALITY, MAX_EMPTY_CARDINALITY + 1):
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
            ordinal = (
                int.from_bytes(position_digest, "big") * empty_count
            ) >> 256
            rank_digest = hashlib.sha256(prefix + b"rank").digest()
            spawned_rank = 2 if int.from_bytes(rank_digest, "big") * 10 < (1 << 256) else 1
            records.append((empty_count, ordinal, spawned_rank, True))
    return tuple(records)


def source_records_v2() -> tuple[tuple[int, int, int, bool], ...]:
    return _record_stream(
        domain=SOURCE_STREAM_DOMAIN,
        seed=SOURCE_SEED,
        records_per_cardinality=SOURCE_RECORDS_PER_CARDINALITY,
    )


def validation_records_v2() -> tuple[tuple[int, int, int, bool], ...]:
    return _record_stream(
        domain=VALIDATION_STREAM_DOMAIN,
        seed=VALIDATION_SEED,
        records_per_cardinality=VALIDATION_RECORDS_PER_CARDINALITY,
    )


def _pack_records(records: tuple[tuple[int, int, int, bool], ...]) -> bytes:
    output = bytearray()
    for empty_count, ordinal, rank, valid in records:
        if (
            not 1 <= empty_count <= 16
            or not 0 <= ordinal < empty_count
            or rank not in (1, 2)
            or type(valid) is not bool
        ):
            _fail("raw support observation changed")
        flags = ordinal | ((rank - 1) << 4) | (int(valid) << 5)
        output.extend((empty_count, flags))
    return bytes(output)


def unpack_records_v2(raw: bytes) -> tuple[tuple[int, int, int, bool], ...]:
    if type(raw) is not bytes or len(raw) % 2:
        _fail("packed support observations changed")
    records: list[tuple[int, int, int, bool]] = []
    for offset in range(0, len(raw), 2):
        empty_count = raw[offset]
        flags = raw[offset + 1]
        if flags & 0xC0:
            _fail("support observation reserved bits changed")
        ordinal = flags & 0x0F
        rank = 1 + ((flags >> 4) & 1)
        valid = bool((flags >> 5) & 1)
        if not 1 <= empty_count <= 16 or ordinal >= empty_count:
            _fail("support observation cardinality or ordinal changed")
        records.append((empty_count, ordinal, rank, valid))
    return tuple(records)


def _archive_document(*, source: bool) -> dict[str, Any]:
    if source:
        records = source_records_v2()
        seed = SOURCE_SEED
        stream_domain = SOURCE_STREAM_DOMAIN
        per_cardinality = SOURCE_RECORDS_PER_CARDINALITY
        schema_role = "SOURCE_CONSTRUCTION"
        domain = DOMAINS["source"]
        identity_name = "support_source_archive_id"
    else:
        records = validation_records_v2()
        seed = VALIDATION_SEED
        stream_domain = VALIDATION_STREAM_DOMAIN
        per_cardinality = VALIDATION_RECORDS_PER_CARDINALITY
        schema_role = "HELDOUT_VALIDATION"
        domain = DOMAINS["validation"]
        identity_name = "support_validation_archive_id"
    packed = _pack_records(records)
    payload = {
        "schema": "acfqp.standard_2048_spawn_support_observation_archive.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "archive_role": schema_role,
        "stream_domain_hex": stream_domain.hex(),
        "stream_seed": seed,
        "records_per_empty_cardinality": per_cardinality,
        "empty_cardinality_min": MIN_EMPTY_CARDINALITY,
        "empty_cardinality_max": MAX_EMPTY_CARDINALITY,
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
    return {**payload, identity_name: content_id(domain, payload)}


def _candidate_covers(candidate: str, empty_count: int, ordinal: int, valid: bool) -> bool:
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
    source_records = source_records_v2()
    validation_records = validation_records_v2()
    evaluations = []
    selected: list[str] = []
    heldout_selected_rule_passed = False
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
        heldout_validation_passed = validation_violations == 0
        if source_selected:
            selected.append(candidate)
            if candidate == SELECTED_SUPPORT_RULE:
                heldout_selected_rule_passed = heldout_validation_passed
        evaluations.append(
            {
                "candidate": candidate,
                "source_violation_count": source_violations,
                "heldout_validation_violation_count": validation_violations,
                "selected_from_source": source_selected,
                "heldout_validation_passed": heldout_validation_passed,
            }
        )
    if selected != [SELECTED_SUPPORT_RULE] or not heldout_selected_rule_passed:
        _fail("support proposal is not uniquely selected")
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
    return {**payload, "support_proposal_id": content_id(DOMAINS["proposal"], payload)}


def support_ordinals_from_proposal_v2(
    *, support_proposal_id: str, selected_support_rule: str, empty_count: int
) -> tuple[int, ...]:
    """Execute the single registered observation-derived support proposal."""

    if (
        type(support_proposal_id) is not str
        or len(support_proposal_id) != 64
        or selected_support_rule != SELECTED_SUPPORT_RULE
        or type(empty_count) is not int
        or not MIN_EMPTY_CARDINALITY <= empty_count <= MAX_EMPTY_CARDINALITY
    ):
        _fail("support proposal execution input changed")
    return tuple(range(empty_count))


def _counts_by_cardinality(
    records: tuple[tuple[int, int, int, bool], ...]
) -> dict[int, list[int]]:
    counts = {empty_count: [0] * empty_count for empty_count in range(1, 17)}
    for empty_count, ordinal, _, valid in records:
        if valid:
            counts[empty_count][ordinal] += 1
    return counts


def _interval_document(
    source_archive: dict[str, Any],
    validation_archive: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    source = source_records_v2()
    validation = validation_records_v2()
    source_counts = _counts_by_cardinality(source)
    validation_counts = _counts_by_cardinality(validation)
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
            sum(Fraction(row["probability_lower"]["numerator"], row["probability_lower"]["denominator"]) for row in categories)
            <= 1
            <= sum(Fraction(row["probability_upper"]["numerator"], row["probability_upper"]["denominator"]) for row in categories)
        ):
            _fail("position interval simplex is infeasible")
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
    source_rank_empirical = Fraction(source_rank_two, len(source))
    rank_lower = max(Fraction(), source_rank_empirical - RANK_TWO_RADIUS)
    rank_upper = min(Fraction(1), source_rank_empirical + RANK_TWO_RADIUS)
    validation_rank_empirical = Fraction(validation_rank_two, len(validation))
    validation_rank_pass = rank_lower <= validation_rank_empirical <= rank_upper
    taylor_lower = sum(
        (Fraction(HOEFFDING_EXPONENT) ** term) / math.factorial(term)
        for term in range(EXP_TAYLOR_LAST_TERM + 1)
    )
    if (
        not validation_position_pass
        or not validation_rank_pass
        or not taylor_lower > UNION_BOUND_COEFFICIENT * 1000
    ):
        _fail("partial dynamics interval validation failed")
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
        "rank_two_source_empirical_probability": _fdoc(source_rank_empirical),
        "rank_two_probability_lower": _fdoc(rank_lower),
        "rank_two_probability_upper": _fdoc(rank_upper),
        "rank_two_heldout_validation_count": validation_rank_two,
        "rank_two_heldout_validation_empirical_probability": _fdoc(
            validation_rank_empirical
        ),
        "rank_two_heldout_inside_source_interval": validation_rank_pass,
        "unknown_support_source_count": sum(not row[3] for row in source),
        "unknown_support_probability_lower": _fdoc(Fraction()),
        "unknown_support_probability_upper": _fdoc(UNKNOWN_SUPPORT_MASS_UPPER),
        "heldout_position_intervals_passed": validation_position_pass,
        "hoeffding_exponent": HOEFFDING_EXPONENT,
        "union_bound_coefficient": UNION_BOUND_COEFFICIENT,
        "exp_sixteen_taylor_last_term": EXP_TAYLOR_LAST_TERM,
        "exp_sixteen_rational_lower_bound": _fdoc(taylor_lower),
        "conditional_confidence_lower": _fdoc(CONDITIONAL_CONFIDENCE_LOWER),
        "confidence_is_conditional_on_registered_iid_shared_law": True,
        "deterministic_replay_does_not_establish_iid": True,
    }
    return {**payload, "partial_dynamics_interval_id": content_id(
        DOMAINS["interval"], payload
    )}


_EVIDENCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SpawnSupportEvidenceV2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    source_archive_id: str
    validation_archive_id: str
    support_proposal_id: str
    partial_dynamics_interval_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _EVIDENCE_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("support evidence is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or set(document) != {"source_archive", "validation_archive", "proposal", "interval"}
            or canonical_json_bytes(document) != self.canonical_bytes
            or document["source_archive"].get("support_source_archive_id")
            != self.source_archive_id
            or document["validation_archive"].get("support_validation_archive_id")
            != self.validation_archive_id
            or document["proposal"].get("support_proposal_id") != self.support_proposal_id
            or document["interval"].get("partial_dynamics_interval_id")
            != self.partial_dynamics_interval_id
        ):
            _fail("support evidence bytes changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("support evidence root is not an object")
        return document


def build_standard_2048_spawn_support_evidence_v2() -> Standard2048SpawnSupportEvidenceV2:
    source = _archive_document(source=True)
    validation = _archive_document(source=False)
    proposal = _support_proposal_document(source, validation)
    interval = _interval_document(source, validation, proposal)
    document = {
        "source_archive": source,
        "validation_archive": validation,
        "proposal": proposal,
        "interval": interval,
    }
    return Standard2048SpawnSupportEvidenceV2(
        _EVIDENCE_ISSUER,
        canonical_json_bytes(document),
        source["support_source_archive_id"],
        validation["support_validation_archive_id"],
        proposal["support_proposal_id"],
        interval["partial_dynamics_interval_id"],
    )


def verify_standard_2048_spawn_support_evidence_v2(
    evidence: Standard2048SpawnSupportEvidenceV2,
) -> Standard2048SpawnSupportEvidenceV2:
    if type(evidence) is not Standard2048SpawnSupportEvidenceV2:
        _fail("support verifier rejects foreign evidence")
    evidence.__post_init__()
    expected = build_standard_2048_spawn_support_evidence_v2()
    if evidence.canonical_bytes != expected.canonical_bytes:
        _fail("support evidence differs from raw semantic replay")
    return evidence


__all__ = (
    "CONDITIONAL_CONFIDENCE_LOWER",
    "ConstructionK7Standard2048SpawnSupportObservationV2Error",
    "DOMAINS",
    "MAX_EMPTY_CARDINALITY",
    "MIN_EMPTY_CARDINALITY",
    "POSITION_RADIUS",
    "PROFILE_KEY",
    "RANK_TWO_RADIUS",
    "SCHEMA_VERSION",
    "SELECTED_SUPPORT_RULE",
    "SOURCE_RECORDS_PER_CARDINALITY",
    "SOURCE_SEED",
    "Standard2048SpawnSupportEvidenceV2",
    "UNKNOWN_SUPPORT_MASS_UPPER",
    "VALIDATION_RECORDS_PER_CARDINALITY",
    "VALIDATION_SEED",
    "build_standard_2048_spawn_support_evidence_v2",
    "source_records_v2",
    "support_ordinals_from_proposal_v2",
    "unpack_records_v2",
    "validation_records_v2",
    "verify_standard_2048_spawn_support_evidence_v2",
)
