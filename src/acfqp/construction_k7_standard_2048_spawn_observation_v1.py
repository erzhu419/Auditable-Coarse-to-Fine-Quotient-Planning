"""Replayable source observations for a partial standard-2048 spawn law.

The learner receives 4,096 raw rank observations from an identity-separated
source archive.  It derives a fixed Hoeffding interval for the probability of
spawning rank two (tile value four).  The archive is a deterministic fixture:
the statistical statement is conditional on an idealized IID interpretation,
and the deterministic replay itself is explicitly not an IID proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math
from typing import Any, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_standard_2048_spawn_observation_v1"
SOURCE_OBSERVATION_SEED = (
    "standard-2048-source-spawn-rank-archive-20260812-v1"
)
SOURCE_STREAM_DOMAIN = b"acfqp:standard-2048-source-spawn-observation:v1\x00"
SOURCE_SAMPLE_COUNT = 4096
HOEFFDING_RADIUS = Fraction(1, 32)
CONDITIONAL_CONFIDENCE_LOWER = Fraction(999, 1000)
TAYLOR_EXPONENT = 8
TAYLOR_LAST_TERM = 13

ARCHIVE_DOMAIN = CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN
INTERVAL_DOMAIN = CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN
if {ARCHIVE_DOMAIN, INTERVAL_DOMAIN} - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("standard-2048 observation domains are not registered")


class ConstructionK7Standard2048SpawnObservationV1Error(ValueError):
    """The raw archive, interval derivation, or identity changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048SpawnObservationV1Error(message)


def _fdoc(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def source_observations_v1() -> tuple[int, ...]:
    """Return raw binary observations; one denotes a spawned rank-two tile."""

    threshold_scale = 1 << 256
    rows: list[int] = []
    for index in range(SOURCE_SAMPLE_COUNT):
        digest = hashlib.sha256(
            SOURCE_STREAM_DOMAIN
            + SOURCE_OBSERVATION_SEED.encode("utf-8")
            + b"\x00"
            + str(index).encode("ascii")
        ).digest()
        rows.append(int(int.from_bytes(digest, "big") * 10 < threshold_scale))
    return tuple(rows)


def _pack_bits(rows: tuple[int, ...]) -> bytes:
    if len(rows) % 8 or any(value not in (0, 1) for value in rows):
        _fail("raw observations are not a complete binary byte stream")
    output = bytearray()
    for start in range(0, len(rows), 8):
        value = 0
        for offset, bit in enumerate(rows[start : start + 8]):
            value |= bit << (7 - offset)
        output.append(value)
    return bytes(output)


def unpack_observation_bits_v1(packed: bytes) -> tuple[int, ...]:
    if type(packed) is not bytes or len(packed) != SOURCE_SAMPLE_COUNT // 8:
        _fail("packed source observation length changed")
    return tuple(
        (value >> shift) & 1
        for value in packed
        for shift in range(7, -1, -1)
    )


def _archive_document() -> dict[str, Any]:
    rows = source_observations_v1()
    packed = _pack_bits(rows)
    rank_two_count = sum(rows)
    payload = {
        "schema": "acfqp.standard_2048_spawn_observation_archive.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_stream_domain_hex": SOURCE_STREAM_DOMAIN.hex(),
        "source_observation_seed": SOURCE_OBSERVATION_SEED,
        "source_sample_count": SOURCE_SAMPLE_COUNT,
        "packed_rank_two_bits_hex": packed.hex(),
        "unpacked_observation_bytes_sha256": hashlib.sha256(bytes(rows)).hexdigest(),
        "rank_one_count": SOURCE_SAMPLE_COUNT - rank_two_count,
        "rank_two_count": rank_two_count,
        "source_archive_frozen_before_target_preregistration": True,
        "target_episode_identity_present": False,
        "deterministic_fixture_replay_not_iid_evidence": True,
    }
    return {**payload, "spawn_observation_archive_id": content_id(ARCHIVE_DOMAIN, payload)}


def _interval_document(archive: dict[str, Any]) -> dict[str, Any]:
    empirical = Fraction(archive["rank_two_count"], SOURCE_SAMPLE_COUNT)
    lower = max(Fraction(), empirical - HOEFFDING_RADIUS)
    upper = min(Fraction(1), empirical + HOEFFDING_RADIUS)
    taylor_lower = sum(
        (Fraction(TAYLOR_EXPONENT) ** term) / math.factorial(term)
        for term in range(TAYLOR_LAST_TERM + 1)
    )
    if not taylor_lower > 2000:
        raise AssertionError("registered exponential lower bound is too weak")
    payload = {
        "schema": "acfqp.standard_2048_spawn_probability_interval.v1",
        "schema_version": SCHEMA_VERSION,
        "spawn_observation_archive_id": archive["spawn_observation_archive_id"],
        "estimated_parameter": "P_SPAWN_RANK_TWO",
        "estimator": "RAW_EMPIRICAL_FREQUENCY_V1",
        "empirical_rank_two_probability": _fdoc(empirical),
        "hoeffding_radius": _fdoc(HOEFFDING_RADIUS),
        "rank_two_probability_lower": _fdoc(lower),
        "rank_two_probability_upper": _fdoc(upper),
        "conditional_confidence_lower": _fdoc(CONDITIONAL_CONFIDENCE_LOWER),
        "two_sided_hoeffding_exponent": TAYLOR_EXPONENT,
        "exp_eight_taylor_last_term": TAYLOR_LAST_TERM,
        "exp_eight_rational_lower_bound": _fdoc(taylor_lower),
        "proof_obligation": "2*EXP(-8)<1/1000_BECAUSE_EXP(8)>2000",
        "confidence_is_conditional_on_idealized_iid_source": True,
        "deterministic_replay_does_not_establish_iid": True,
        "known_position_support_not_estimated": True,
    }
    return {**payload, "spawn_probability_interval_id": content_id(INTERVAL_DOMAIN, payload)}


_EVIDENCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class Standard2048SpawnObservationEvidenceV1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    spawn_observation_archive_id: str
    spawn_probability_interval_id: str

    def __post_init__(self) -> None:
        if self._issuer is not _EVIDENCE_ISSUER or type(self.canonical_bytes) is not bytes:
            _fail("observation evidence is not issuer-created")
        document = loads_canonical_json(self.canonical_bytes)
        if (
            type(document) is not dict
            or set(document) != {"archive", "interval"}
            or canonical_json_bytes(document) != self.canonical_bytes
            or document["archive"].get("spawn_observation_archive_id")
            != self.spawn_observation_archive_id
            or document["interval"].get("spawn_probability_interval_id")
            != self.spawn_probability_interval_id
        ):
            _fail("observation evidence bytes changed")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise AssertionError("observation evidence root is not an object")
        return document


def build_standard_2048_spawn_observation_evidence_v1(
) -> Standard2048SpawnObservationEvidenceV1:
    archive = _archive_document()
    interval = _interval_document(archive)
    document = {"archive": archive, "interval": interval}
    return Standard2048SpawnObservationEvidenceV1(
        _EVIDENCE_ISSUER,
        canonical_json_bytes(document),
        archive["spawn_observation_archive_id"],
        interval["spawn_probability_interval_id"],
    )


def verify_standard_2048_spawn_observation_evidence_v1(
    evidence: Standard2048SpawnObservationEvidenceV1,
) -> Standard2048SpawnObservationEvidenceV1:
    if type(evidence) is not Standard2048SpawnObservationEvidenceV1:
        _fail("observation verifier rejects foreign values")
    evidence.__post_init__()
    archive = _archive_document()
    expected = {"archive": archive, "interval": _interval_document(archive)}
    if evidence.canonical_bytes != canonical_json_bytes(expected):
        _fail("observation evidence differs from exact raw replay")
    return evidence


__all__ = (
    "ARCHIVE_DOMAIN",
    "CONDITIONAL_CONFIDENCE_LOWER",
    "ConstructionK7Standard2048SpawnObservationV1Error",
    "HOEFFDING_RADIUS",
    "INTERVAL_DOMAIN",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SOURCE_OBSERVATION_SEED",
    "SOURCE_SAMPLE_COUNT",
    "SOURCE_STREAM_DOMAIN",
    "Standard2048SpawnObservationEvidenceV1",
    "build_standard_2048_spawn_observation_evidence_v1",
    "source_observations_v1",
    "unpack_observation_bits_v1",
    "verify_standard_2048_spawn_observation_evidence_v1",
)
