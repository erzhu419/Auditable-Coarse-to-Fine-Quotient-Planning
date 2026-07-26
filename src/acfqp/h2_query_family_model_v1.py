"""V0-056 durable, model-only H2 query-family proof layer.

The module consumes the *bytes* of the registered V0-055 C2 checkpoint, but
does not import or invoke its matching-buffer, action-local, recovery, or
semantic-replay authorities.  The source checkpoint is accepted only at its
frozen content identities.  Its eighteen active lower-node bindings seed W0.

Changed-query facets are then added lazily:

* Q1 ``(regret=0, risk=0)`` reuses all eighteen source bindings;
* Q2 ``(regret=3/4, risk=0)`` adds two regret gates and one selection facet;
* Q3 ``(regret=0, risk=1)`` adds two risk gates and one selection facet.

All facet keys are constructed and looked up before a value builder can run.
Hits never call the builder.  Facet commits are immutable, append-only and
root-free; the three per-occurrence certificate roots are always rebuilt in a
fresh process and never enter the store.

This is a narrow registered construction control.  Exact kernel calls are
reported as zero, but logical proof-node counts are not relabelled as kernel
samples, CPU work, or official workload economics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.20.0"
PROFILE_KEY = "lmb_h2_durable_query_family_model_v0"
SOURCE_PROFILE_KEY = "lmb_h2_two_generation_durable_action_local_recovery_v0"
SOURCE_ELIGIBILITY_RECIPE = (
    "EXACT_V0055_C2_ACTIVE18_ROOT_FREE_RAW_CAS_BINDING_V1"
)
OCCURRENCE_QUERY_INDICES = (1, 2, 3, 1, 2, 3, 1, 2, 3, 1)
ADDRESS_ORDER = (
    "ROW_S",
    "ROW_N1",
    "ROW_N2",
    "ROW_N3",
    "ROW_M",
    "Q_N",
    "Q_M",
    "U1",
    "U0",
    "PLAN_N",
    "PLAN_M",
    "REGRET_N",
    "REGRET_M",
    "RISK_N",
    "RISK_M",
    "COVERAGE_N",
    "COVERAGE_M",
    "SELECTION",
)
ADDRESS_INDEX = {value: index for index, value in enumerate(ADDRESS_ORDER)}
QUERY_FACET_ADDRESSES = {
    1: (),
    2: ("REGRET_N", "REGRET_M", "SELECTION"),
    3: ("RISK_N", "RISK_M", "SELECTION"),
}
SOURCE_C2_COMMIT_ID = (
    "cb644f0ba1fc61c7a589cf2f0779d5a852c6519512e4e235aed2893b97c57783"
)
SOURCE_C2_PAYLOAD_ID = (
    "b6d2c58d4586eabae72ded584531547858671b54e3808a0907cc37bf490c65dc"
)
SOURCE_PROTOCOL_ID = (
    "461aedcae3b3acade7bf197e8d6f12371531d8b69acfbb08f8ce39dddd851a42"
)
SOURCE_ACTIVE_PROJECTION_SHA256 = (
    "b122d4ec7d98b723717a0f547c693516aa74c64ce8e8e5051318063ce9a15a55"
)
SOURCE_DOMAIN_TAGS = {
    "commit": "acfqp:h2-durable-action-switch-commit:v1",
    "payload": "acfqp:h2-durable-action-switch-c2-payload:v1",
    "manifest": "acfqp:h2-durable-action-switch-c2-manifest:v1",
}
DOMAIN_TAGS = {
    "query": "acfqp:h2-query-family-query:v1",
    "semantics": "acfqp:h2-query-family-proof-semantics:v1",
    "protocol": "acfqp:h2-query-family-protocol:v1",
    "occurrence": "acfqp:h2-query-family-occurrence:v1",
    "preregistration": "acfqp:h2-query-family-preregistration:v1",
    "source_lease": "acfqp:h2-query-family-source-c2-lease:v1",
    "consumed_facet": "acfqp:h2-query-family-consumed-threshold-facet:v1",
    "facet_key": "acfqp:h2-query-family-facet-key:v1",
    "facet_entry": "acfqp:h2-query-family-facet-entry:v1",
    "store_payload": "acfqp:h2-query-family-store-payload:v1",
    "store_commit": "acfqp:h2-query-family-store-commit:v1",
    "resolution": "acfqp:h2-query-family-resolution:v1",
    "root": "acfqp:h2-query-family-fresh-root:v1",
    "certificate": "acfqp:h2-query-family-plan-certificate:v1",
    "result": "acfqp:h2-query-family-occurrence-result:v1",
    "initialization": "acfqp:h2-query-family-initialization:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-056 content domains must be unique")


class H2QueryFamilyInvariantViolation(ValueError):
    """A registered identity, source checkpoint, store, or worker is invalid."""


class H2QueryFamilyResolutionOutcome(str, Enum):
    COMPUTED = "COMPUTED"
    REUSED = "REUSED"


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        domain = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise H2QueryFamilyInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode() + b"\x00" + encoded).hexdigest()


def _source_content_id(role: str, payload: Mapping[str, Any]) -> str:
    document = dict(payload)
    document.pop(f"{role}_id", None)
    domain = SOURCE_DOMAIN_TAGS[role]
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(document)
    ).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise H2QueryFamilyInvariantViolation(
            f"{name} must be a full lowercase SHA-256 ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise H2QueryFamilyInvariantViolation(
            f"{name} must be an integer >= {minimum}"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise H2QueryFamilyInvariantViolation(f"{name} must be exact")
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        numerator = value["numerator"]
        denominator = value["denominator"]
        if (
            type(numerator) is not int
            or type(denominator) is not int
            or denominator <= 0
        ):
            raise H2QueryFamilyInvariantViolation(f"{name} rational is invalid")
        result = Fraction(numerator, denominator)
        if (
            result.numerator != numerator
            or result.denominator != denominator
        ):
            raise H2QueryFamilyInvariantViolation(
                f"{name} rational is not reduced"
            )
        return result
    raise H2QueryFamilyInvariantViolation(f"{name} must be exact")


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _same_document(left: Any, right: Any) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _mapping(value: Any, keys: set[str], name: str) -> Mapping[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise H2QueryFamilyInvariantViolation(f"{name} schema changed")
    return value


def _read_stable(path: Path) -> bytes:
    if not isinstance(path, Path):
        raise H2QueryFamilyInvariantViolation("read target must be a Path")
    try:
        before = path.lstat()
        if path.is_symlink() or not path.is_file() or before.st_nlink != 1:
            raise OSError("not a unique regular file")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened = os.fstat(descriptor)
            pieces: list[bytes] = []
            while True:
                piece = os.read(descriptor, 1024 * 1024)
                if not piece:
                    break
                pieces.append(piece)
            after_open = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = path.lstat()
    except OSError as error:
        raise H2QueryFamilyInvariantViolation(
            f"cannot stably read {path.name}"
        ) from error
    signature = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_size,
        row.st_mtime_ns,
        row.st_nlink,
    )
    if not (
        signature(before)
        == signature(opened)
        == signature(after_open)
        == signature(after)
    ):
        raise H2QueryFamilyInvariantViolation("artifact changed during read")
    return b"".join(pieces)


def _atomic_write(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise H2QueryFamilyInvariantViolation("append-only target already exists")
    temporary = path.with_name(f".{path.name}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _assert_model_only_import_boundary(*, fresh_worker: bool = False) -> None:
    forbidden = (
        "matching_buffer",
        "action_local",
        "durable_action_local_recovery",
    )
    imported = tuple(
        name for name in sys.modules if any(token in name for token in forbidden)
    )
    if fresh_worker and imported:
        raise H2QueryFamilyInvariantViolation(
            "fresh query-family worker crossed the model-only import boundary"
        )


@dataclass(frozen=True, slots=True)
class H2QueryFamilyQueryV1:
    query_index: int
    query_key: str
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction
    horizon: int = 2
    initial_state_key: str = "x0"
    return_upper: Fraction = Fraction(4)
    reward_basis: tuple[tuple[str, Fraction], ...] = (
        ("match", Fraction(1)),
        ("terminal_clear", Fraction(1)),
    )
    policy_class: str = "DETERMINISTIC_FINITE_HORIZON_MARKOV"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "normalized_regret_tolerance",
            _fraction(
                self.normalized_regret_tolerance,
                "normalized regret tolerance",
            ),
        )
        object.__setattr__(
            self, "risk_tolerance", _fraction(self.risk_tolerance, "risk tolerance")
        )
        object.__setattr__(
            self, "return_upper", _fraction(self.return_upper, "return upper")
        )
        expected = {
            1: ("Q1_STRICT", Fraction(0), Fraction(0)),
            2: ("Q2_REGRET_RELAXED", Fraction(3, 4), Fraction(0)),
            3: ("Q3_RISK_RELAXED", Fraction(0), Fraction(1)),
        }.get(self.query_index)
        if (
            expected is None
            or (self.query_key, self.normalized_regret_tolerance, self.risk_tolerance)
            != expected
            or self.horizon != 2
            or self.initial_state_key != "x0"
            or self.return_upper != 4
            or self.reward_basis
            != (("match", Fraction(1)), ("terminal_clear", Fraction(1)))
            or self.policy_class != "DETERMINISTIC_FINITE_HORIZON_MARKOV"
        ):
            raise H2QueryFamilyInvariantViolation("registered query changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_query.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "query_index": self.query_index,
            "query_key": self.query_key,
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "horizon": self.horizon,
            "initial_state_key": self.initial_state_key,
            "return_upper": _fdoc(self.return_upper),
            "reward_basis": [
                {"name": name, "weight": _fdoc(weight)}
                for name, weight in self.reward_basis
            ],
            "policy_class": self.policy_class,
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}

    @property
    def regret_facet_id(self) -> str:
        return H2QueryFamilyConsumedFacetV1(
            "NORMALIZED_REGRET_TOLERANCE",
            self.normalized_regret_tolerance,
        ).facet_id

    @property
    def risk_facet_id(self) -> str:
        return H2QueryFamilyConsumedFacetV1(
            "RISK_TOLERANCE", self.risk_tolerance
        ).facet_id

    @property
    def return_upper_facet_id(self) -> str:
        return H2QueryFamilyConsumedFacetV1(
            "RETURN_UPPER", self.return_upper
        ).facet_id


@dataclass(frozen=True, slots=True)
class H2QueryFamilyConsumedFacetV1:
    role: str
    value: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _fraction(self.value, "facet value"))
        if self.role not in (
            "NORMALIZED_REGRET_TOLERANCE",
            "RISK_TOLERANCE",
            "RETURN_UPPER",
        ):
            raise H2QueryFamilyInvariantViolation("consumed facet role changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_consumed_threshold_facet.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": self.role,
            "value": _fdoc(self.value),
        }

    @property
    def facet_id(self) -> str:
        return _content_id("consumed_facet", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "facet_id": self.facet_id}


def _registered_queries() -> tuple[H2QueryFamilyQueryV1, ...]:
    return (
        H2QueryFamilyQueryV1(1, "Q1_STRICT", Fraction(0), Fraction(0)),
        H2QueryFamilyQueryV1(
            2, "Q2_REGRET_RELAXED", Fraction(3, 4), Fraction(0)
        ),
        H2QueryFamilyQueryV1(3, "Q3_RISK_RELAXED", Fraction(0), Fraction(1)),
    )


@dataclass(frozen=True, slots=True)
class H2QueryFamilyProtocolV1:
    queries: tuple[H2QueryFamilyQueryV1, ...]
    occurrence_query_indices: tuple[int, ...]
    source_profile_key: str = SOURCE_PROFILE_KEY
    source_eligibility_recipe: str = SOURCE_ELIGIBILITY_RECIPE
    formula_registry: tuple[tuple[str, str], ...] = (
        ("REGRET", "EXACT_NORMALIZED_REGRET_GATE_V1"),
        ("RISK", "EXACT_FAILURE_UPPER_GATE_V1"),
        ("SELECTION", "CERTIFIED_REWARD_MAX_N_THEN_M_V1"),
    )
    source_active_lower_count: int = 18
    facet_count_per_changed_query: int = 3
    fresh_root_count_per_occurrence: int = 3
    maximum_global_union_count: int = 24
    root_persistence_allowed: bool = False
    ground_kernel_allowed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.queries) is not tuple
            or any(type(item) is not H2QueryFamilyQueryV1 for item in self.queries)
            or self.queries != _registered_queries()
            or self.occurrence_query_indices != OCCURRENCE_QUERY_INDICES
            or self.source_profile_key != SOURCE_PROFILE_KEY
            or self.source_eligibility_recipe != SOURCE_ELIGIBILITY_RECIPE
            or self.formula_registry
            != (
                ("REGRET", "EXACT_NORMALIZED_REGRET_GATE_V1"),
                ("RISK", "EXACT_FAILURE_UPPER_GATE_V1"),
                ("SELECTION", "CERTIFIED_REWARD_MAX_N_THEN_M_V1"),
            )
            or self.source_active_lower_count != 18
            or self.facet_count_per_changed_query != 3
            or self.fresh_root_count_per_occurrence != 3
            or self.maximum_global_union_count != 24
            or self.root_persistence_allowed is not False
            or self.ground_kernel_allowed is not False
        ):
            raise H2QueryFamilyInvariantViolation("registered protocol changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_protocol.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "queries": [item.to_document() for item in self.queries],
            "occurrence_query_indices": list(self.occurrence_query_indices),
            "source_profile_key": self.source_profile_key,
            "source_eligibility_recipe": self.source_eligibility_recipe,
            "formula_registry": [
                {"role": role, "formula_id": formula}
                for role, formula in self.formula_registry
            ],
            "source_active_lower_count": self.source_active_lower_count,
            "facet_count_per_changed_query": self.facet_count_per_changed_query,
            "fresh_root_count_per_occurrence": self.fresh_root_count_per_occurrence,
            "maximum_global_union_count": self.maximum_global_union_count,
            "root_persistence_allowed": self.root_persistence_allowed,
            "ground_kernel_allowed": self.ground_kernel_allowed,
        }

    @property
    def protocol_id(self) -> str:
        return _content_id("protocol", self._payload())

    @property
    def proof_semantics_id(self) -> str:
        return _content_id(
            "semantics",
            {
                "schema": "acfqp.h2_query_family_proof_semantics.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "source_profile_key": self.source_profile_key,
                "source_eligibility_recipe": self.source_eligibility_recipe,
                "formula_registry": [
                    {"role": role, "formula_id": formula}
                    for role, formula in self.formula_registry
                ],
                "address_order": list(ADDRESS_ORDER),
                "candidate_order": ["N", "M"],
                "schedule_mapping": [
                    {"action": "N", "schedule_code": "A0A0"},
                    {"action": "M", "schedule_code": "A0A1"},
                ],
                "tie_break": "REWARD_MAX_THEN_CANDIDATE_ORDER_V1",
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "protocol_id": self.protocol_id}

    def query(self, query_index: int) -> H2QueryFamilyQueryV1:
        if type(query_index) is not int or query_index not in (1, 2, 3):
            raise H2QueryFamilyInvariantViolation("query index is not registered")
        return self.queries[query_index - 1]


def registered_h2_query_family_protocol_v1() -> H2QueryFamilyProtocolV1:
    return H2QueryFamilyProtocolV1(_registered_queries(), OCCURRENCE_QUERY_INDICES)


@dataclass(frozen=True, slots=True)
class H2QueryFamilyOccurrenceV1:
    protocol_id: str
    occurrence_index: int
    query_index: int
    query_id: str

    def __post_init__(self) -> None:
        _cid(self.protocol_id, "occurrence protocol")
        _cid(self.query_id, "occurrence query")
        _integer(self.occurrence_index, "occurrence index", 1)
        if self.query_index not in (1, 2, 3):
            raise H2QueryFamilyInvariantViolation("occurrence query is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "occurrence_index": self.occurrence_index,
            "query_index": self.query_index,
            "query_id": self.query_id,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def registered_h2_query_family_occurrence_v1(
    occurrence_index: int,
) -> H2QueryFamilyOccurrenceV1:
    protocol = registered_h2_query_family_protocol_v1()
    _integer(occurrence_index, "occurrence index", 1)
    if occurrence_index > len(protocol.occurrence_query_indices):
        raise H2QueryFamilyInvariantViolation("occurrence is not preregistered")
    query_index = protocol.occurrence_query_indices[occurrence_index - 1]
    return H2QueryFamilyOccurrenceV1(
        protocol.protocol_id,
        occurrence_index,
        query_index,
        protocol.query(query_index).query_id,
    )


@dataclass(frozen=True, slots=True)
class H2QueryFamilyPreregistrationV1:
    protocol: H2QueryFamilyProtocolV1
    occurrences: tuple[H2QueryFamilyOccurrenceV1, ...]
    frozen_before_source_promotion: bool = True
    source_artifact_ids_absent: bool = True

    def __post_init__(self) -> None:
        if (
            type(self.protocol) is not H2QueryFamilyProtocolV1
            or self.protocol != registered_h2_query_family_protocol_v1()
            or self.occurrences
            != tuple(
                registered_h2_query_family_occurrence_v1(index)
                for index in range(1, 11)
            )
            or self.frozen_before_source_promotion is not True
            or self.source_artifact_ids_absent is not True
        ):
            raise H2QueryFamilyInvariantViolation("preregistration changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol": self.protocol.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "frozen_before_source_promotion": self.frozen_before_source_promotion,
            "source_artifact_ids_absent": self.source_artifact_ids_absent,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


def registered_h2_query_family_preregistration_v1(
) -> H2QueryFamilyPreregistrationV1:
    protocol = registered_h2_query_family_protocol_v1()
    return H2QueryFamilyPreregistrationV1(
        protocol,
        tuple(
            registered_h2_query_family_occurrence_v1(index)
            for index in range(1, 11)
        ),
    )


def require_registered_h2_query_family_protocol_v1(
    protocol: H2QueryFamilyProtocolV1,
) -> H2QueryFamilyProtocolV1:
    if (
        type(protocol) is not H2QueryFamilyProtocolV1
        or protocol.to_document()
        != registered_h2_query_family_protocol_v1().to_document()
    ):
        raise H2QueryFamilyInvariantViolation("protocol is not registered")
    return protocol


def require_registered_h2_query_family_query_v1(
    query: H2QueryFamilyQueryV1,
    protocol: H2QueryFamilyProtocolV1,
    expected_query_index: int,
) -> H2QueryFamilyQueryV1:
    require_registered_h2_query_family_protocol_v1(protocol)
    expected = protocol.query(expected_query_index)
    if type(query) is not H2QueryFamilyQueryV1 or query.to_document() != expected.to_document():
        raise H2QueryFamilyInvariantViolation("query is not the expected registered query")
    return query


def require_registered_h2_query_family_occurrence_v1(
    occurrence: H2QueryFamilyOccurrenceV1,
    protocol: H2QueryFamilyProtocolV1,
    expected_occurrence_index: int,
) -> H2QueryFamilyOccurrenceV1:
    require_registered_h2_query_family_protocol_v1(protocol)
    expected = registered_h2_query_family_occurrence_v1(expected_occurrence_index)
    if (
        type(occurrence) is not H2QueryFamilyOccurrenceV1
        or occurrence.to_document() != expected.to_document()
    ):
        raise H2QueryFamilyInvariantViolation(
            "occurrence is not the expected preregistered occurrence"
        )
    return occurrence


def parse_h2_query_family_query_document_v1(
    document: Any,
) -> H2QueryFamilyQueryV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "query_index",
            "query_key",
            "normalized_regret_tolerance",
            "risk_tolerance",
            "horizon",
            "initial_state_key",
            "return_upper",
            "reward_basis",
            "policy_class",
            "query_id",
        },
        "query",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_query.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["reward_basis"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("query schema changed")
    basis: list[tuple[str, Fraction]] = []
    for item in row["reward_basis"]:
        field = _mapping(item, {"name", "weight"}, "reward basis")
        basis.append((field["name"], _fraction(field["weight"], "reward weight")))
    result = H2QueryFamilyQueryV1(
        row["query_index"],
        row["query_key"],
        _fraction(
            row["normalized_regret_tolerance"], "normalized regret tolerance"
        ),
        _fraction(row["risk_tolerance"], "risk tolerance"),
        row["horizon"],
        row["initial_state_key"],
        _fraction(row["return_upper"], "return upper"),
        tuple(basis),
        row["policy_class"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("query is not canonical")
    return result


def parse_h2_query_family_protocol_document_v1(
    document: Any,
) -> H2QueryFamilyProtocolV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "contract_version",
            "profile_key",
            "queries",
            "occurrence_query_indices",
            "source_profile_key",
            "source_eligibility_recipe",
            "formula_registry",
            "source_active_lower_count",
            "facet_count_per_changed_query",
            "fresh_root_count_per_occurrence",
            "maximum_global_union_count",
            "root_persistence_allowed",
            "ground_kernel_allowed",
            "protocol_id",
        },
        "protocol",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_protocol.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["contract_version"] != CONTRACT_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["queries"]) is not list
        or type(row["occurrence_query_indices"]) is not list
        or type(row["formula_registry"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("protocol schema changed")
    formulas = []
    for item in row["formula_registry"]:
        field = _mapping(item, {"role", "formula_id"}, "formula registry")
        formulas.append((field["role"], field["formula_id"]))
    result = H2QueryFamilyProtocolV1(
        tuple(parse_h2_query_family_query_document_v1(item) for item in row["queries"]),
        tuple(row["occurrence_query_indices"]),
        row["source_profile_key"],
        row["source_eligibility_recipe"],
        tuple(formulas),
        row["source_active_lower_count"],
        row["facet_count_per_changed_query"],
        row["fresh_root_count_per_occurrence"],
        row["maximum_global_union_count"],
        row["root_persistence_allowed"],
        row["ground_kernel_allowed"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("protocol is not canonical")
    return result


def parse_h2_query_family_occurrence_document_v1(
    document: Any,
) -> H2QueryFamilyOccurrenceV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol_id",
            "occurrence_index",
            "query_index",
            "query_id",
            "occurrence_id",
        },
        "occurrence",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_occurrence.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise H2QueryFamilyInvariantViolation("occurrence schema changed")
    result = H2QueryFamilyOccurrenceV1(
        row["protocol_id"],
        row["occurrence_index"],
        row["query_index"],
        row["query_id"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("occurrence is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class H2QueryFamilySourceNodeRefV1:
    address: str
    node_key_id: str
    node_id: str
    node_document: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.address not in ADDRESS_INDEX:
            raise H2QueryFamilyInvariantViolation("source address changed")
        _cid(self.node_key_id, "source node key")
        _cid(self.node_id, "source node")
        row = _mapping(
            self.node_document,
            {
                "schema",
                "schema_version",
                "profile_key",
                "address",
                "kind",
                "input_slice_id",
                "ordered_parent_node_ids",
                "identity_terms",
                "node_key_id",
                "result_digest",
                "result_fields",
                "node_id",
            },
            "source semantic node",
        )
        if (
            row["schema"] != "acfqp.action_indexed_proof_node.v1"
            or row["schema_version"] != "1.0.0"
            or row["profile_key"]
            != "lmb_h2_action_indexed_semantic_switch_v0"
            or row["address"] != self.address
            or row["node_key_id"] != self.node_key_id
            or row["node_id"] != self.node_id
            or type(row["ordered_parent_node_ids"]) is not list
            or type(row["identity_terms"]) is not list
            or type(row["result_fields"]) is not list
        ):
            raise H2QueryFamilyInvariantViolation(
                "source semantic node binding changed"
            )
        names = []
        for item in row["result_fields"]:
            field = _mapping(
                item, {"name", "kind", "value"}, "source result field"
            )
            if field["kind"] == "FRACTION":
                _fraction(field["value"], "source fraction field")
            elif field["kind"] == "BOOLEAN":
                if type(field["value"]) is not bool:
                    raise H2QueryFamilyInvariantViolation(
                        "source boolean field changed"
                    )
            elif field["kind"] == "TEXT":
                if type(field["value"]) is not str:
                    raise H2QueryFamilyInvariantViolation(
                        "source text field changed"
                    )
            else:
                raise H2QueryFamilyInvariantViolation(
                    "source result-field kind changed"
                )
            names.append(field["name"])
        if names != sorted(names) or len(names) != len(set(names)):
            raise H2QueryFamilyInvariantViolation(
                "source result fields are not canonical"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "node_key_id": self.node_key_id,
            "node_id": self.node_id,
            "node_document": dict(self.node_document),
        }

    def field(self, name: str, kind: str) -> Any:
        for item in self.node_document["result_fields"]:
            if item["name"] == name and item["kind"] == kind:
                return item["value"]
        raise H2QueryFamilyInvariantViolation(
            f"source {self.address} lacks {kind} field {name}"
        )


@dataclass(frozen=True, slots=True)
class VerifiedH2QueryFamilySourceC2V1:
    commit_id: str
    payload_id: str
    manifest_id: str
    protocol_id: str
    active_source_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...]
    full_cache_entry_count: int
    active_final_entry_count: int
    cached_root_entry_count: int
    read_bytes: int

    def __post_init__(self) -> None:
        for value in (
            self.commit_id,
            self.payload_id,
            self.manifest_id,
            self.protocol_id,
        ):
            _cid(value, "source lease identity")
        if (
            self.commit_id != SOURCE_C2_COMMIT_ID
            or self.payload_id != SOURCE_C2_PAYLOAD_ID
            or self.protocol_id != SOURCE_PROTOCOL_ID
            or type(self.active_source_nodes) is not tuple
            or tuple(item.address for item in self.active_source_nodes)
            != ADDRESS_ORDER
            or len({item.node_key_id for item in self.active_source_nodes}) != 18
            or len({item.node_id for item in self.active_source_nodes}) != 18
            or hashlib.sha256(
                canonical_json_bytes(
                    [item.to_document() for item in self.active_source_nodes]
                )
            ).hexdigest()
            != SOURCE_ACTIVE_PROJECTION_SHA256
            or self.full_cache_entry_count != 28
            or self.active_final_entry_count != 18
            or self.cached_root_entry_count != 0
            or self.read_bytes <= 0
        ):
            raise H2QueryFamilyInvariantViolation("source C2 lease changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_source_c2_lease.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "commit_id": self.commit_id,
            "payload_id": self.payload_id,
            "manifest_id": self.manifest_id,
            "protocol_id": self.protocol_id,
            "active_source_nodes": [
                item.to_document() for item in self.active_source_nodes
            ],
            "full_cache_entry_count": self.full_cache_entry_count,
            "active_final_entry_count": self.active_final_entry_count,
            "cached_root_entry_count": self.cached_root_entry_count,
        }

    @property
    def source_lease_id(self) -> str:
        return _content_id("source_lease", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_lease_id": self.source_lease_id,
            "read_bytes": self.read_bytes,
        }


def load_verified_h2_query_family_source_c2_v1(
    source_c2_store_root: Path,
    expected_commit_id: str = SOURCE_C2_COMMIT_ID,
) -> VerifiedH2QueryFamilySourceC2V1:
    """Validate the frozen C2 raw CAS without running its semantic replay."""

    _assert_model_only_import_boundary()
    if not isinstance(source_c2_store_root, Path):
        raise H2QueryFamilyInvariantViolation("source store root must be a Path")
    expected = _cid(expected_commit_id, "expected source commit")
    if expected != SOURCE_C2_COMMIT_ID:
        raise H2QueryFamilyInvariantViolation("source C2 commit is not registered")
    if (
        not source_c2_store_root.is_dir()
        or source_c2_store_root.is_symlink()
        or {item.name for item in source_c2_store_root.iterdir()}
        != {"blobs", "commits"}
    ):
        raise H2QueryFamilyInvariantViolation("source C2 store topology changed")
    blobs = source_c2_store_root / "blobs"
    commits = source_c2_store_root / "commits"
    if (
        blobs.is_symlink()
        or commits.is_symlink()
        or not blobs.is_dir()
        or not commits.is_dir()
        or {item.name for item in commits.iterdir()} != {f"{expected}.json"}
    ):
        raise H2QueryFamilyInvariantViolation("source C2 directories changed")
    commit_bytes = _read_stable(commits / f"{expected}.json")
    commit = _mapping(
        loads_canonical_json(commit_bytes),
        {
            "schema",
            "schema_version",
            "profile_key",
            "checkpoint_kind",
            "protocol_id",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "manifest_id",
            "manifest_sha256",
            "manifest_size_bytes",
            "generation",
            "previous_commit_id",
            "commit_complete",
            "commit_id",
        },
        "source commit",
    )
    if (
        commit["schema"] != "acfqp.h2_durable_action_switch_commit.v1"
        or commit["schema_version"] != "1.0.0"
        or commit["profile_key"] != "lmb_h2_durable_action_switch_transport_v0"
        or commit["checkpoint_kind"] != "C2_FINAL"
        or commit["protocol_id"] != SOURCE_PROTOCOL_ID
        or commit["payload_id"] != SOURCE_C2_PAYLOAD_ID
        or commit["generation"] != 2
        or commit["commit_complete"] is not True
        or commit["commit_id"] != expected
        or _source_content_id("commit", commit) != expected
    ):
        raise H2QueryFamilyInvariantViolation("source C2 commit identity changed")
    manifest_id = _cid(commit["manifest_id"], "source manifest")
    expected_blobs = {
        f"{SOURCE_C2_PAYLOAD_ID}.json",
        f"{manifest_id}.json",
    }
    if {item.name for item in blobs.iterdir()} != expected_blobs:
        raise H2QueryFamilyInvariantViolation("source C2 blob set changed")
    payload_bytes = _read_stable(blobs / f"{SOURCE_C2_PAYLOAD_ID}.json")
    manifest_bytes = _read_stable(blobs / f"{manifest_id}.json")
    if (
        len(payload_bytes) != commit["payload_size_bytes"]
        or hashlib.sha256(payload_bytes).hexdigest() != commit["payload_sha256"]
        or len(manifest_bytes) != commit["manifest_size_bytes"]
        or hashlib.sha256(manifest_bytes).hexdigest() != commit["manifest_sha256"]
    ):
        raise H2QueryFamilyInvariantViolation("source C2 bytes changed")
    payload = loads_canonical_json(payload_bytes)
    if type(payload) is not dict:
        raise H2QueryFamilyInvariantViolation("source payload is not an object")
    manifest = loads_canonical_json(manifest_bytes)
    if type(manifest) is not dict:
        raise H2QueryFamilyInvariantViolation("source manifest is not an object")
    if (
        payload.get("schema")
        != "acfqp.h2_durable_action_switch_c2_payload.v1"
        or payload.get("profile_key")
        != "lmb_h2_durable_action_switch_transport_v0"
        or payload.get("payload_id") != SOURCE_C2_PAYLOAD_ID
        or _source_content_id("payload", payload) != SOURCE_C2_PAYLOAD_ID
        or manifest.get("schema")
        != "acfqp.h2_durable_action_switch_c2_manifest.v1"
        or manifest.get("manifest_id") != manifest_id
        or _source_content_id("manifest", manifest) != manifest_id
        or manifest.get("payload_id") != SOURCE_C2_PAYLOAD_ID
        or payload.get("full_cache_entry_count") != 28
        or payload.get("active_final_entry_count") != 18
        or payload.get("cached_root_entry_count") != 0
    ):
        raise H2QueryFamilyInvariantViolation("source C2 payload/manifest changed")
    documents = payload.get("lower_node_documents")
    bindings = payload.get("active_final_bindings")
    if type(documents) is not list or len(documents) != 28 or type(bindings) is not list:
        raise H2QueryFamilyInvariantViolation("source C2 lower graph changed")
    nodes: dict[str, Mapping[str, Any]] = {}
    for document in documents:
        if type(document) is not dict:
            raise H2QueryFamilyInvariantViolation("source lower node is not typed")
        node_id = _cid(document.get("node_id"), "source lower node")
        _cid(document.get("node_key_id"), "source lower node key")
        if node_id in nodes:
            raise H2QueryFamilyInvariantViolation("source lower nodes alias")
        nodes[node_id] = document
    refs = []
    for item in bindings:
        row = _mapping(
            item, {"address", "node_key_id", "node_id"}, "active source binding"
        )
        node_id = _cid(row["node_id"], "active source node")
        node = nodes.get(node_id)
        if (
            node is None
            or row["address"] not in ADDRESS_INDEX
            or node.get("address") != row["address"]
            or node.get("node_key_id") != row["node_key_id"]
        ):
            raise H2QueryFamilyInvariantViolation("active source binding changed")
        refs.append(
            H2QueryFamilySourceNodeRefV1(
                row["address"], row["node_key_id"], node_id, dict(node)
            )
        )
    refs.sort(key=lambda item: ADDRESS_INDEX[item.address])
    if tuple(item.address for item in refs) != ADDRESS_ORDER:
        raise H2QueryFamilyInvariantViolation("source active address set changed")
    return VerifiedH2QueryFamilySourceC2V1(
        expected,
        SOURCE_C2_PAYLOAD_ID,
        manifest_id,
        SOURCE_PROTOCOL_ID,
        tuple(refs),
        28,
        18,
        0,
        len(commit_bytes) + len(payload_bytes) + len(manifest_bytes),
    )


@dataclass(frozen=True, slots=True)
class H2QueryFamilyFacetKeyV1:
    proof_semantics_id: str
    address: str
    formula_id: str
    ordered_parent_node_ids: tuple[str, ...]
    consumed_facet_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value in (
            self.proof_semantics_id,
            *self.ordered_parent_node_ids,
            *self.consumed_facet_ids,
        ):
            _cid(value, "facet-key identity")
        if (
            self.address
            not in ("REGRET_N", "REGRET_M", "RISK_N", "RISK_M", "SELECTION")
            or self.formula_id
            not in (
                "EXACT_NORMALIZED_REGRET_GATE_V1",
                "EXACT_FAILURE_UPPER_GATE_V1",
                "CERTIFIED_REWARD_MAX_N_THEN_M_V1",
            )
            or type(self.ordered_parent_node_ids) is not tuple
            or not self.ordered_parent_node_ids
            or type(self.consumed_facet_ids) is not tuple
        ):
            raise H2QueryFamilyInvariantViolation("facet key changed")
        if (
            (self.address.startswith("REGRET_")
             and (
                 self.formula_id != "EXACT_NORMALIZED_REGRET_GATE_V1"
                 or len(self.ordered_parent_node_ids) != 2
                 or len(self.consumed_facet_ids) != 2
             ))
            or (
                self.address.startswith("RISK_")
                and (
                    self.formula_id != "EXACT_FAILURE_UPPER_GATE_V1"
                    or len(self.ordered_parent_node_ids) != 1
                    or len(self.consumed_facet_ids) != 1
                )
            )
            or (
                self.address == "SELECTION"
                and (
                    self.formula_id != "CERTIFIED_REWARD_MAX_N_THEN_M_V1"
                    or len(self.ordered_parent_node_ids) != 8
                    or self.consumed_facet_ids != ()
                )
            )
        ):
            raise H2QueryFamilyInvariantViolation(
                "facet key consumed-facet/parent arity changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_facet_key.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "proof_semantics_id": self.proof_semantics_id,
            "address": self.address,
            "formula_id": self.formula_id,
            "ordered_parent_node_ids": list(self.ordered_parent_node_ids),
            "consumed_facet_ids": list(self.consumed_facet_ids),
        }

    @property
    def facet_key_id(self) -> str:
        return _content_id("facet_key", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "facet_key_id": self.facet_key_id}


@dataclass(frozen=True, slots=True)
class H2QueryFamilyFacetEntryV1:
    key: H2QueryFamilyFacetKeyV1
    result_fields: tuple[tuple[str, str, Any], ...]

    def __post_init__(self) -> None:
        if type(self.key) is not H2QueryFamilyFacetKeyV1:
            raise H2QueryFamilyInvariantViolation("facet entry key changed")
        if (
            type(self.result_fields) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 3
                or type(item[0]) is not str
                or item[1] not in ("BOOLEAN", "FRACTION", "TEXT")
                for item in self.result_fields
            )
            or tuple(item[0] for item in self.result_fields)
            != tuple(sorted(item[0] for item in self.result_fields))
        ):
            raise H2QueryFamilyInvariantViolation("facet result fields changed")
        for _name, kind, value in self.result_fields:
            if kind == "BOOLEAN" and type(value) is not bool:
                raise H2QueryFamilyInvariantViolation("boolean facet field changed")
            if kind == "FRACTION":
                _fraction(value, "fraction facet field")
            if kind == "TEXT" and type(value) is not str:
                raise H2QueryFamilyInvariantViolation("text facet field changed")

    def _payload(self) -> dict[str, Any]:
        fields = []
        for name, kind, value in self.result_fields:
            fields.append(
                {
                    "name": name,
                    "kind": kind,
                    "value": _fdoc(value) if kind == "FRACTION" else value,
                }
            )
        return {
            "schema": "acfqp.h2_query_family_facet_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "key": self.key.to_document(),
            "result_fields": fields,
        }

    @property
    def node_id(self) -> str:
        return _content_id("facet_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "node_id": self.node_id}

    def field(self, name: str) -> Any:
        for field_name, _kind, value in self.result_fields:
            if field_name == name:
                return value
        raise H2QueryFamilyInvariantViolation(f"facet field {name} is absent")


def _parse_facet_key(document: Any) -> H2QueryFamilyFacetKeyV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "proof_semantics_id",
            "address",
            "formula_id",
            "ordered_parent_node_ids",
            "consumed_facet_ids",
            "facet_key_id",
        },
        "facet key",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_facet_key.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["ordered_parent_node_ids"]) is not list
        or type(row["consumed_facet_ids"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("facet-key schema changed")
    result = H2QueryFamilyFacetKeyV1(
        row["proof_semantics_id"],
        row["address"],
        row["formula_id"],
        tuple(row["ordered_parent_node_ids"]),
        tuple(row["consumed_facet_ids"]),
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("facet key is not canonical")
    return result


def _parse_facet_entry(document: Any) -> H2QueryFamilyFacetEntryV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "key",
            "result_fields",
            "node_id",
        },
        "facet entry",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_facet_entry.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["result_fields"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("facet-entry schema changed")
    fields = []
    for item in row["result_fields"]:
        field = _mapping(item, {"name", "kind", "value"}, "facet result field")
        value = field["value"]
        if field["kind"] == "FRACTION":
            value = _fraction(value, "facet fraction")
        fields.append((field["name"], field["kind"], value))
    result = H2QueryFamilyFacetEntryV1(
        _parse_facet_key(row["key"]), tuple(fields)
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("facet entry is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class H2QueryFamilyStorePayloadV1:
    protocol_id: str
    source_commit_id: str
    source_payload_id: str
    source_active_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...]
    facet_entries: tuple[H2QueryFamilyFacetEntryV1, ...]
    generation: int
    previous_payload_id: str | None
    active_lower_count: int = 18
    persisted_root_count: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.protocol_id,
            self.source_commit_id,
            self.source_payload_id,
        ):
            _cid(value, "store payload identity")
        if self.previous_payload_id is not None:
            _cid(self.previous_payload_id, "previous store payload")
        if (
            self.source_commit_id != SOURCE_C2_COMMIT_ID
            or self.source_payload_id != SOURCE_C2_PAYLOAD_ID
            or type(self.source_active_nodes) is not tuple
            or tuple(item.address for item in self.source_active_nodes)
            != ADDRESS_ORDER
            or hashlib.sha256(
                canonical_json_bytes(
                    [item.to_document() for item in self.source_active_nodes]
                )
            ).hexdigest()
            != SOURCE_ACTIVE_PROJECTION_SHA256
            or type(self.facet_entries) is not tuple
            or any(type(item) is not H2QueryFamilyFacetEntryV1 for item in self.facet_entries)
            or len({item.key.facet_key_id for item in self.facet_entries})
            != len(self.facet_entries)
            or self.generation not in (0, 1, 2)
            or self.generation * 3 != len(self.facet_entries)
            or (self.generation == 0) != (self.previous_payload_id is None)
            or self.active_lower_count != 18
            or self.persisted_root_count != 0
        ):
            raise H2QueryFamilyInvariantViolation("store payload changed")
        _validate_facet_entries_semantics(
            self.source_active_nodes, self.facet_entries
        )

    @property
    def logical_lower_count(self) -> int:
        return len(self.source_active_nodes) + len(self.facet_entries)

    @property
    def persisted_facet_count(self) -> int:
        return len(self.facet_entries)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_store_payload.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "source_commit_id": self.source_commit_id,
            "source_payload_id": self.source_payload_id,
            "source_active_nodes": [
                item.to_document() for item in self.source_active_nodes
            ],
            "facet_entries": [item.to_document() for item in self.facet_entries],
            "generation": self.generation,
            "previous_payload_id": (
                self.previous_payload_id
                if self.previous_payload_id is not None
                else {"kind": "NOT_APPLICABLE", "reason": "W0"}
            ),
            "logical_lower_count": self.logical_lower_count,
            "persisted_facet_count": self.persisted_facet_count,
            "active_lower_count": self.active_lower_count,
            "persisted_root_count": self.persisted_root_count,
        }

    @property
    def payload_id(self) -> str:
        return _content_id("store_payload", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "payload_id": self.payload_id}


@dataclass(frozen=True, slots=True)
class H2QueryFamilyFacetCommitV1:
    protocol_id: str
    source_commit_id: str
    payload_id: str
    payload_sha256: str
    payload_size_bytes: int
    generation: int
    previous_commit_id: str | None
    appended_query_index: int | None
    logical_lower_count: int
    persisted_facet_count: int
    persisted_root_count: int = 0
    commit_complete: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.protocol_id,
            self.source_commit_id,
            self.payload_id,
            self.payload_sha256,
        ):
            _cid(value, "store commit identity")
        if self.previous_commit_id is not None:
            _cid(self.previous_commit_id, "previous store commit")
        if (
            self.source_commit_id != SOURCE_C2_COMMIT_ID
            or self.generation not in (0, 1, 2)
            or (self.generation == 0)
            != (self.previous_commit_id is None and self.appended_query_index is None)
            or (
                self.generation > 0
                and (
                    self.previous_commit_id is None
                    or self.appended_query_index not in (2, 3)
                )
            )
            or self.payload_size_bytes <= 0
            or self.logical_lower_count != 18 + 3 * self.generation
            or self.persisted_facet_count != 3 * self.generation
            or self.persisted_root_count != 0
            or self.commit_complete is not True
        ):
            raise H2QueryFamilyInvariantViolation("store commit changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_store_commit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "source_commit_id": self.source_commit_id,
            "payload_id": self.payload_id,
            "payload_sha256": self.payload_sha256,
            "payload_size_bytes": self.payload_size_bytes,
            "generation": self.generation,
            "previous_commit_id": (
                self.previous_commit_id
                if self.previous_commit_id is not None
                else {"kind": "NOT_APPLICABLE", "reason": "W0"}
            ),
            "appended_query_index": (
                self.appended_query_index
                if self.appended_query_index is not None
                else {"kind": "NOT_APPLICABLE", "reason": "W0"}
            ),
            "logical_lower_count": self.logical_lower_count,
            "persisted_facet_count": self.persisted_facet_count,
            "persisted_root_count": self.persisted_root_count,
            "commit_complete": self.commit_complete,
        }

    @property
    def commit_id(self) -> str:
        return _content_id("store_commit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commit_id": self.commit_id}


def _parse_source_ref(document: Any) -> H2QueryFamilySourceNodeRefV1:
    row = _mapping(
        document,
        {"address", "node_key_id", "node_id", "node_document"},
        "source node ref",
    )
    return H2QueryFamilySourceNodeRefV1(
        row["address"],
        row["node_key_id"],
        row["node_id"],
        row["node_document"],
    )


def _parse_store_payload(document: Any) -> H2QueryFamilyStorePayloadV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol_id",
            "source_commit_id",
            "source_payload_id",
            "source_active_nodes",
            "facet_entries",
            "generation",
            "previous_payload_id",
            "logical_lower_count",
            "persisted_facet_count",
            "active_lower_count",
            "persisted_root_count",
            "payload_id",
        },
        "store payload",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_store_payload.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["source_active_nodes"]) is not list
        or type(row["facet_entries"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("store-payload schema changed")
    previous = row["previous_payload_id"]
    if type(previous) is dict:
        if previous != {"kind": "NOT_APPLICABLE", "reason": "W0"}:
            raise H2QueryFamilyInvariantViolation("payload typed null changed")
        previous = None
    result = H2QueryFamilyStorePayloadV1(
        row["protocol_id"],
        row["source_commit_id"],
        row["source_payload_id"],
        tuple(_parse_source_ref(item) for item in row["source_active_nodes"]),
        tuple(_parse_facet_entry(item) for item in row["facet_entries"]),
        row["generation"],
        previous,
        row["active_lower_count"],
        row["persisted_root_count"],
    )
    if (
        result.logical_lower_count != row["logical_lower_count"]
        or result.persisted_facet_count != row["persisted_facet_count"]
        or not _same_document(result.to_document(), row)
    ):
        raise H2QueryFamilyInvariantViolation("store payload is not canonical")
    return result


def _parse_store_commit(document: Any) -> H2QueryFamilyFacetCommitV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "protocol_id",
            "source_commit_id",
            "payload_id",
            "payload_sha256",
            "payload_size_bytes",
            "generation",
            "previous_commit_id",
            "appended_query_index",
            "logical_lower_count",
            "persisted_facet_count",
            "persisted_root_count",
            "commit_complete",
            "commit_id",
        },
        "store commit",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_store_commit.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise H2QueryFamilyInvariantViolation("store-commit schema changed")
    previous = row["previous_commit_id"]
    appended = row["appended_query_index"]
    if type(previous) is dict:
        if previous != {"kind": "NOT_APPLICABLE", "reason": "W0"}:
            raise H2QueryFamilyInvariantViolation("commit typed null changed")
        previous = None
    if type(appended) is dict:
        if appended != {"kind": "NOT_APPLICABLE", "reason": "W0"}:
            raise H2QueryFamilyInvariantViolation("append typed null changed")
        appended = None
    result = H2QueryFamilyFacetCommitV1(
        row["protocol_id"],
        row["source_commit_id"],
        row["payload_id"],
        row["payload_sha256"],
        row["payload_size_bytes"],
        row["generation"],
        previous,
        appended,
        row["logical_lower_count"],
        row["persisted_facet_count"],
        row["persisted_root_count"],
        row["commit_complete"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("store commit is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class VerifiedH2QueryFamilyStoreV1:
    expected_commit_id: str
    commit: H2QueryFamilyFacetCommitV1
    payload: H2QueryFamilyStorePayloadV1
    chain_commit_ids: tuple[str, ...]
    read_bytes: int

    def __post_init__(self) -> None:
        _cid(self.expected_commit_id, "expected store commit")
        if (
            type(self.commit) is not H2QueryFamilyFacetCommitV1
            or type(self.payload) is not H2QueryFamilyStorePayloadV1
            or self.expected_commit_id != self.commit.commit_id
            or self.commit.payload_id != self.payload.payload_id
            or self.commit.generation != self.payload.generation
            or self.commit.logical_lower_count != self.payload.logical_lower_count
            or self.commit.persisted_facet_count
            != self.payload.persisted_facet_count
            or len(self.chain_commit_ids) != self.commit.generation + 1
            or self.chain_commit_ids[-1] != self.commit.commit_id
            or self.read_bytes <= 0
        ):
            raise H2QueryFamilyInvariantViolation("verified store lease changed")


@dataclass(frozen=True, slots=True)
class H2QueryFamilyInitializationV1:
    commit: H2QueryFamilyFacetCommitV1
    source_lease_id: str
    read_bytes: int
    output_bytes: int

    def __post_init__(self) -> None:
        if (
            type(self.commit) is not H2QueryFamilyFacetCommitV1
            or self.commit.generation != 0
            or self.commit.logical_lower_count != 18
            or self.commit.persisted_facet_count != 0
            or self.commit.persisted_root_count != 0
            or self.read_bytes <= 0
            or self.output_bytes <= 0
        ):
            raise H2QueryFamilyInvariantViolation("W0 initialization changed")
        _cid(self.source_lease_id, "source lease")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_initialization.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "commit": self.commit.to_document(),
            "source_lease_id": self.source_lease_id,
            "read_bytes": self.read_bytes,
            "output_bytes": self.output_bytes,
        }

    @property
    def initialization_id(self) -> str:
        return _content_id("initialization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "initialization_id": self.initialization_id}


def _prepare_empty_store(store_root: Path) -> tuple[Path, Path]:
    if not isinstance(store_root, Path):
        raise H2QueryFamilyInvariantViolation("store root must be a Path")
    if store_root.exists():
        if (
            store_root.is_symlink()
            or not store_root.is_dir()
            or any(store_root.iterdir())
        ):
            raise H2QueryFamilyInvariantViolation(
                "W0 requires an empty real directory"
            )
    else:
        store_root.mkdir(parents=True)
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    blobs.mkdir()
    commits.mkdir()
    return blobs, commits


def initialize_h2_query_family_w0_v1(
    source_c2_store_root: Path,
    source_c2_commit_id: str,
    store_root: Path,
) -> H2QueryFamilyInitializationV1:
    """Promote the frozen source active-18 bindings into root-free W0."""

    source = load_verified_h2_query_family_source_c2_v1(
        source_c2_store_root, source_c2_commit_id
    )
    protocol = registered_h2_query_family_protocol_v1()
    payload = H2QueryFamilyStorePayloadV1(
        protocol.protocol_id,
        source.commit_id,
        source.payload_id,
        source.active_source_nodes,
        (),
        0,
        None,
    )
    payload_bytes = canonical_json_bytes(payload.to_document())
    commit = H2QueryFamilyFacetCommitV1(
        protocol.protocol_id,
        source.commit_id,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        0,
        None,
        None,
        18,
        0,
    )
    commit_bytes = canonical_json_bytes(commit.to_document())
    blobs, commits = _prepare_empty_store(store_root)
    _atomic_write(blobs / f"{payload.payload_id}.json", payload_bytes)
    _atomic_write(commits / f"{commit.commit_id}.json", commit_bytes)
    loaded = load_verified_h2_query_family_store_v1(
        store_root, commit.commit_id
    )
    if loaded.commit.to_document() != commit.to_document():
        raise H2QueryFamilyInvariantViolation("W0 reread changed")
    return H2QueryFamilyInitializationV1(
        commit,
        source.source_lease_id,
        source.read_bytes,
        len(payload_bytes) + len(commit_bytes),
    )


def load_verified_h2_query_family_store_v1(
    store_root: Path,
    expected_commit_id: str,
) -> VerifiedH2QueryFamilyStoreV1:
    if (
        not isinstance(store_root, Path)
        or not store_root.is_dir()
        or store_root.is_symlink()
        or {item.name for item in store_root.iterdir()} != {"blobs", "commits"}
    ):
        raise H2QueryFamilyInvariantViolation("query-family store topology changed")
    expected = _cid(expected_commit_id, "expected query-family commit")
    blobs = store_root / "blobs"
    commits = store_root / "commits"
    if (
        blobs.is_symlink()
        or commits.is_symlink()
        or not blobs.is_dir()
        or not commits.is_dir()
    ):
        raise H2QueryFamilyInvariantViolation("query-family store directories changed")
    commit_names = {item.name for item in commits.iterdir()}
    if not commit_names or any(
        not name.endswith(".json") or len(name) != 69 for name in commit_names
    ):
        raise H2QueryFamilyInvariantViolation("query-family commit set changed")
    parsed: dict[str, tuple[H2QueryFamilyFacetCommitV1, bytes]] = {}
    read_bytes = 0
    for name in sorted(commit_names):
        raw = _read_stable(commits / name)
        commit = _parse_store_commit(loads_canonical_json(raw))
        if name != f"{commit.commit_id}.json":
            raise H2QueryFamilyInvariantViolation("commit filename changed")
        parsed[commit.commit_id] = (commit, raw)
        read_bytes += len(raw)
    if expected not in parsed:
        raise H2QueryFamilyInvariantViolation("expected commit is absent")
    chain = []
    cursor: str | None = expected
    while cursor is not None:
        item = parsed.get(cursor)
        if item is None:
            raise H2QueryFamilyInvariantViolation("commit chain is broken")
        chain.append(cursor)
        cursor = item[0].previous_commit_id
    chain.reverse()
    if (
        len(chain) != len(parsed)
        or tuple(parsed[item][0].generation for item in chain)
        != tuple(range(len(chain)))
        or len(chain) > 3
    ):
        raise H2QueryFamilyInvariantViolation(
            "store contains forks, descendants, or gaps"
        )
    expected_blob_names = {
        f"{parsed[item][0].payload_id}.json" for item in chain
    }
    if {item.name for item in blobs.iterdir()} != expected_blob_names:
        raise H2QueryFamilyInvariantViolation("store blob set changed")
    previous_payload: H2QueryFamilyStorePayloadV1 | None = None
    final_payload: H2QueryFamilyStorePayloadV1 | None = None
    for commit_id in chain:
        commit = parsed[commit_id][0]
        raw = _read_stable(blobs / f"{commit.payload_id}.json")
        read_bytes += len(raw)
        if (
            len(raw) != commit.payload_size_bytes
            or hashlib.sha256(raw).hexdigest() != commit.payload_sha256
        ):
            raise H2QueryFamilyInvariantViolation("store payload bytes changed")
        payload = _parse_store_payload(loads_canonical_json(raw))
        if (
            payload.payload_id != commit.payload_id
            or payload.protocol_id != commit.protocol_id
            or payload.source_commit_id != commit.source_commit_id
            or payload.previous_payload_id
            != (previous_payload.payload_id if previous_payload is not None else None)
        ):
            raise H2QueryFamilyInvariantViolation("store payload chain changed")
        if previous_payload is not None:
            if (
                payload.source_active_nodes != previous_payload.source_active_nodes
                or payload.facet_entries[:-3] != previous_payload.facet_entries
                or len(payload.facet_entries)
                != len(previous_payload.facet_entries) + 3
                or _facet_group_query_index(
                    payload.source_active_nodes,
                    payload.facet_entries[-3:],
                )
                != commit.appended_query_index
            ):
                raise H2QueryFamilyInvariantViolation(
                    "facet commit is not append-only"
                )
        previous_payload = payload
        final_payload = payload
    assert final_payload is not None
    return VerifiedH2QueryFamilyStoreV1(
        expected,
        parsed[expected][0],
        final_payload,
        tuple(chain),
        read_bytes,
    )


def _append_facet_group(
    store_root: Path,
    lease: VerifiedH2QueryFamilyStoreV1,
    query_index: int,
    entries: tuple[H2QueryFamilyFacetEntryV1, ...],
) -> tuple[H2QueryFamilyFacetCommitV1, int]:
    if (
        type(lease) is not VerifiedH2QueryFamilyStoreV1
        or query_index not in (2, 3)
        or tuple(item.key.address for item in entries)
        != QUERY_FACET_ADDRESSES[query_index]
        or any(
            _facet_group_query_index(
                lease.payload.source_active_nodes,
                lease.payload.facet_entries[offset : offset + 3],
            )
            == query_index
            for offset in range(0, len(lease.payload.facet_entries), 3)
        )
        or _facet_group_query_index(
            lease.payload.source_active_nodes, entries
        )
        != query_index
    ):
        raise H2QueryFamilyInvariantViolation("facet append request changed")
    payload = H2QueryFamilyStorePayloadV1(
        lease.payload.protocol_id,
        lease.payload.source_commit_id,
        lease.payload.source_payload_id,
        lease.payload.source_active_nodes,
        tuple((*lease.payload.facet_entries, *entries)),
        lease.payload.generation + 1,
        lease.payload.payload_id,
    )
    payload_bytes = canonical_json_bytes(payload.to_document())
    commit = H2QueryFamilyFacetCommitV1(
        payload.protocol_id,
        payload.source_commit_id,
        payload.payload_id,
        hashlib.sha256(payload_bytes).hexdigest(),
        len(payload_bytes),
        payload.generation,
        lease.commit.commit_id,
        query_index,
        payload.logical_lower_count,
        payload.persisted_facet_count,
    )
    commit_bytes = canonical_json_bytes(commit.to_document())
    _atomic_write(
        store_root / "blobs" / f"{payload.payload_id}.json", payload_bytes
    )
    _atomic_write(
        store_root / "commits" / f"{commit.commit_id}.json", commit_bytes
    )
    return commit, len(payload_bytes) + len(commit_bytes)


def _gate_keys(
    protocol: H2QueryFamilyProtocolV1,
    query: H2QueryFamilyQueryV1,
    source_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...],
) -> tuple[H2QueryFamilyFacetKeyV1, H2QueryFamilyFacetKeyV1] | tuple[()]:
    """Build the two threshold-gate keys without executing their values."""

    if query.query_index == 1:
        return ()
    source = {item.address: item for item in source_nodes}
    formula = (
        "EXACT_NORMALIZED_REGRET_GATE_V1"
        if query.query_index == 2
        else "EXACT_FAILURE_UPPER_GATE_V1"
    )
    gate_addresses = QUERY_FACET_ADDRESSES[query.query_index][:-1]
    keys: list[H2QueryFamilyFacetKeyV1] = []
    for address in gate_addresses:
        if address.startswith("REGRET_"):
            suffix = address[-1]
            parents = (
                source["U0"].node_id,
                source[f"PLAN_{suffix}"].node_id,
            )
            consumed = (query.regret_facet_id,)
        else:
            suffix = address[-1]
            parents = (source[f"PLAN_{suffix}"].node_id,)
            consumed = (query.risk_facet_id,)
        keys.append(
            H2QueryFamilyFacetKeyV1(
                protocol.proof_semantics_id,
                address,
                formula,
                parents,
                (
                    query.return_upper_facet_id,
                    *consumed,
                )
                if address.startswith("REGRET_")
                else consumed,
            )
        )
    return tuple(keys)  # type: ignore[return-value]


def _selection_key(
    protocol: H2QueryFamilyProtocolV1,
    source_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...],
    gate_entries: Mapping[str, H2QueryFamilyFacetEntryV1],
) -> H2QueryFamilyFacetKeyV1:
    """Bind selection to resolved gate *node IDs*, never to gate key IDs."""

    source = {item.address: item for item in source_nodes}
    parents = []
    for address in (
        "PLAN_N",
        "REGRET_N",
        "RISK_N",
        "COVERAGE_N",
        "PLAN_M",
        "REGRET_M",
        "RISK_M",
        "COVERAGE_M",
    ):
        parents.append(
            gate_entries[address].node_id
            if address in gate_entries
            else source[address].node_id
        )
    return H2QueryFamilyFacetKeyV1(
        protocol.proof_semantics_id,
        "SELECTION",
        "CERTIFIED_REWARD_MAX_N_THEN_M_V1",
        tuple(parents),
        (),
    )


def _node_id(
    node: H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1,
) -> str:
    return node.node_id


def _node_field(
    node: H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1,
    name: str,
    kind: str,
) -> Any:
    if type(node) is H2QueryFamilySourceNodeRefV1:
        return node.field(name, kind)
    if type(node) is H2QueryFamilyFacetEntryV1:
        for field_name, field_kind, value in node.result_fields:
            if field_name == name and field_kind == kind:
                return value
    raise H2QueryFamilyInvariantViolation(
        f"semantic node lacks {kind} field {name}"
    )


def _consumed_facet_value(facet_id: str, role: str) -> Fraction:
    _cid(facet_id, "consumed threshold facet")
    if role == "NORMALIZED_REGRET_TOLERANCE":
        values = (Fraction(0), Fraction(3, 4))
    elif role == "RISK_TOLERANCE":
        values = (Fraction(0), Fraction(1))
    elif role == "RETURN_UPPER":
        values = (Fraction(4),)
    else:
        raise H2QueryFamilyInvariantViolation("consumed facet role changed")
    matches = [
        value
        for value in values
        if H2QueryFamilyConsumedFacetV1(role, value).facet_id == facet_id
    ]
    if len(matches) != 1:
        raise H2QueryFamilyInvariantViolation(
            "consumed facet is not a registered independent threshold facet"
        )
    return matches[0]


def _expected_facet_result_fields(
    key: H2QueryFamilyFacetKeyV1,
    semantic_nodes: Mapping[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ],
) -> tuple[tuple[str, str, Any], ...]:
    if key.address.startswith("REGRET_"):
        action = key.address[-1]
        u0 = semantic_nodes["U0"]
        plan = semantic_nodes[f"PLAN_{action}"]
        if key.ordered_parent_node_ids != (_node_id(u0), _node_id(plan)):
            raise H2QueryFamilyInvariantViolation(
                "regret gate is not bound to U0/PLAN parents"
            )
        return_upper = _consumed_facet_value(
            key.consumed_facet_ids[0], "RETURN_UPPER"
        )
        threshold = _consumed_facet_value(
            key.consumed_facet_ids[1],
            "NORMALIZED_REGRET_TOLERANCE",
        )
        regret = max(
            Fraction(0),
            (
                _fraction(
                    _node_field(u0, "reward_upper", "FRACTION"),
                    "U0 reward upper",
                )
                - _fraction(
                    _node_field(plan, "reward_lower", "FRACTION"),
                    "plan reward lower",
                )
            )
            / return_upper,
        )
        return (
            ("normalized_regret", "FRACTION", regret),
            ("passes", "BOOLEAN", regret <= threshold),
        )
    if key.address.startswith("RISK_"):
        action = key.address[-1]
        plan = semantic_nodes[f"PLAN_{action}"]
        if key.ordered_parent_node_ids != (_node_id(plan),):
            raise H2QueryFamilyInvariantViolation(
                "risk gate is not bound to its PLAN parent"
            )
        threshold = _consumed_facet_value(
            key.consumed_facet_ids[0], "RISK_TOLERANCE"
        )
        failure = _fraction(
            _node_field(plan, "failure_upper", "FRACTION"),
            "plan failure upper",
        )
        return (
            ("failure_upper", "FRACTION", failure),
            ("passes", "BOOLEAN", failure <= threshold),
        )
    if key.address == "SELECTION":
        parent_addresses = (
            "PLAN_N",
            "REGRET_N",
            "RISK_N",
            "COVERAGE_N",
            "PLAN_M",
            "REGRET_M",
            "RISK_M",
            "COVERAGE_M",
        )
        parents = tuple(semantic_nodes[item] for item in parent_addresses)
        if key.ordered_parent_node_ids != tuple(_node_id(item) for item in parents):
            raise H2QueryFamilyInvariantViolation(
                "selection is not bound to resolved gate node IDs"
            )
        candidates = []
        for action in ("N", "M"):
            plan = semantic_nodes[f"PLAN_{action}"]
            regret_pass = (
                _node_field(
                    semantic_nodes[f"REGRET_{action}"],
                    "passes",
                    "BOOLEAN",
                )
                is True
            )
            risk_pass = (
                _node_field(
                    semantic_nodes[f"RISK_{action}"],
                    "passes",
                    "BOOLEAN",
                )
                is True
            )
            coverage_pass = (
                _node_field(
                    semantic_nodes[f"COVERAGE_{action}"],
                    "passes",
                    "BOOLEAN",
                )
                is True
            )
            certified = regret_pass and risk_pass and coverage_pass
            feasible = risk_pass and coverage_pass
            reward = _fraction(
                _node_field(plan, "reward_lower", "FRACTION"),
                "candidate reward lower",
            )
            failure = _fraction(
                _node_field(plan, "failure_upper", "FRACTION"),
                "candidate failure upper",
            )
            candidates.append(
                (action, certified, feasible, reward, failure)
            )
        if any(row[1] for row in candidates):
            eligible = [row for row in candidates if row[1]]
            selection_mode = "CERTIFIED_REWARD_MAX"
        elif any(row[2] for row in candidates):
            eligible = [row for row in candidates if row[2]]
            selection_mode = "RISK_COVERAGE_FEASIBLE_REWARD_MAX"
        else:
            eligible = candidates
            selection_mode = "MIN_FAILURE_FALLBACK"
        selected = min(
            eligible,
            key=lambda row: (
                -row[3],
                row[4],
                ("N", "M").index(row[0]),
            ),
        )
        if selection_mode == "MIN_FAILURE_FALLBACK":
            raise H2QueryFamilyInvariantViolation(
                "registered projection requires unsafe selection fallback"
            )
        selected_action = selected[0]
        selected_certified = selected[1]
        schedule = {"N": "A0A0", "M": "A0A1"}[selected_action]
        return (
            ("certified", "BOOLEAN", selected_certified),
            ("selected_action", "TEXT", selected_action),
            ("selected_schedule_code", "TEXT", schedule),
            (
                "selection_mode",
                "TEXT",
                selection_mode,
            ),
        )
    raise H2QueryFamilyInvariantViolation("unknown facet address")


def _build_facet_entry(
    key: H2QueryFamilyFacetKeyV1,
    semantic_nodes: Mapping[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ],
) -> H2QueryFamilyFacetEntryV1:
    """Canonical value builder.  The resolver calls it only after a miss."""

    return H2QueryFamilyFacetEntryV1(
        key, _expected_facet_result_fields(key, semantic_nodes)
    )


def _facet_group_query_index(
    source_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...],
    entries: tuple[H2QueryFamilyFacetEntryV1, ...],
) -> int:
    if len(entries) != 3:
        raise H2QueryFamilyInvariantViolation("facet group must contain three nodes")
    addresses = tuple(item.key.address for item in entries)
    if addresses == QUERY_FACET_ADDRESSES[2]:
        query_index = 2
    elif addresses == QUERY_FACET_ADDRESSES[3]:
        query_index = 3
    else:
        raise H2QueryFamilyInvariantViolation("facet group addresses changed")
    protocol = registered_h2_query_family_protocol_v1()
    query = protocol.query(query_index)
    gate_keys = _gate_keys(protocol, query, source_nodes)
    if tuple(item.key.to_document() for item in entries[:2]) != tuple(
        item.to_document() for item in gate_keys
    ):
        raise H2QueryFamilyInvariantViolation("persisted gate keys changed")
    semantic: dict[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ] = {item.address: item for item in source_nodes}
    for entry in entries[:2]:
        if entry.result_fields != _expected_facet_result_fields(
            entry.key, semantic
        ):
            raise H2QueryFamilyInvariantViolation("persisted gate value changed")
        semantic[entry.key.address] = entry
    selection_key = _selection_key(protocol, source_nodes, {
        item.key.address: item for item in entries[:2]
    })
    if (
        entries[2].key.to_document() != selection_key.to_document()
        or entries[2].result_fields
        != _expected_facet_result_fields(selection_key, semantic)
    ):
        raise H2QueryFamilyInvariantViolation(
            "persisted selection key/value changed"
        )
    return query_index


def _validate_facet_entries_semantics(
    source_nodes: tuple[H2QueryFamilySourceNodeRefV1, ...],
    entries: tuple[H2QueryFamilyFacetEntryV1, ...],
) -> None:
    groups = []
    for offset in range(0, len(entries), 3):
        groups.append(
            _facet_group_query_index(
                source_nodes, entries[offset : offset + 3]
            )
        )
    if len(groups) != len(set(groups)):
        raise H2QueryFamilyInvariantViolation("duplicate facet group changed")


@dataclass(frozen=True, slots=True)
class H2QueryFamilyResolutionV1:
    sequence_number: int
    occurrence_id: str
    query_id: str
    address: str
    lookup_key_id: str
    node_id: str
    outcome: H2QueryFamilyResolutionOutcome

    def __post_init__(self) -> None:
        _integer(self.sequence_number, "resolution sequence", 1)
        for value in (
            self.occurrence_id,
            self.query_id,
            self.lookup_key_id,
            self.node_id,
        ):
            _cid(value, "resolution identity")
        if (
            self.address not in ADDRESS_INDEX
            or type(self.outcome) is not H2QueryFamilyResolutionOutcome
        ):
            raise H2QueryFamilyInvariantViolation("resolution changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "occurrence_id": self.occurrence_id,
            "query_id": self.query_id,
            "address": self.address,
            "lookup_key_id": self.lookup_key_id,
            "node_id": self.node_id,
            "outcome": self.outcome.value,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id("resolution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class H2QueryFamilyFreshRootV1:
    occurrence_id: str
    query_id: str
    role: str
    action: str
    selection_node_id: str
    plan_node_id: str
    regret_node_id: str
    risk_node_id: str
    coverage_node_id: str
    active_lower_node_ids: tuple[str, ...]
    parent_root_ids: tuple[str, ...]
    reward_lower: Fraction
    failure_upper: Fraction
    normalized_regret: Fraction
    certified: bool

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.query_id,
            self.selection_node_id,
            self.plan_node_id,
            self.regret_node_id,
            self.risk_node_id,
            self.coverage_node_id,
            *self.active_lower_node_ids,
            *self.parent_root_ids,
        ):
            _cid(value, "root identity")
        for name in ("reward_lower", "failure_upper", "normalized_regret"):
            object.__setattr__(self, name, _fraction(getattr(self, name), name))
        if (
            self.role not in ("CANDIDATE", "SELECTED")
            or self.action not in ("N", "M")
            or len(self.active_lower_node_ids) != 18
            or (
                self.role == "CANDIDATE"
                and self.parent_root_ids != ()
            )
            or (
                self.role == "SELECTED"
                and len(self.parent_root_ids) != 2
            )
        ):
            raise H2QueryFamilyInvariantViolation("fresh root changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_fresh_root.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "query_id": self.query_id,
            "role": self.role,
            "action": self.action,
            "selection_node_id": self.selection_node_id,
            "plan_node_id": self.plan_node_id,
            "regret_node_id": self.regret_node_id,
            "risk_node_id": self.risk_node_id,
            "coverage_node_id": self.coverage_node_id,
            "active_lower_node_ids": list(self.active_lower_node_ids),
            "parent_root_ids": list(self.parent_root_ids),
            "reward_lower": _fdoc(self.reward_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_regret": _fdoc(self.normalized_regret),
            "certified": self.certified,
        }

    @property
    def root_id(self) -> str:
        return _content_id("root", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "root_id": self.root_id}


@dataclass(frozen=True, slots=True)
class H2QueryFamilyPlanCertificateV1:
    occurrence_id: str
    query_id: str
    selected_root_id: str
    selection_node_id: str
    selected_action: str
    selected_schedule_code: str
    reward_lower: Fraction
    failure_upper: Fraction
    normalized_regret: Fraction
    certified: bool

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.query_id,
            self.selected_root_id,
            self.selection_node_id,
        ):
            _cid(value, "certificate identity")
        for name in ("reward_lower", "failure_upper", "normalized_regret"):
            object.__setattr__(self, name, _fraction(getattr(self, name), name))
        if (
            self.selected_action not in ("N", "M")
            or self.selected_schedule_code
            != {"N": "A0A0", "M": "A0A1"}[self.selected_action]
            or type(self.certified) is not bool
        ):
            raise H2QueryFamilyInvariantViolation("certificate domain changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_plan_certificate.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "query_id": self.query_id,
            "selected_root_id": self.selected_root_id,
            "selection_node_id": self.selection_node_id,
            "selected_action": self.selected_action,
            "selected_schedule_code": self.selected_schedule_code,
            "reward_lower": _fdoc(self.reward_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_regret": _fdoc(self.normalized_regret),
            "certified": self.certified,
        }

    @property
    def certificate_id(self) -> str:
        return _content_id("certificate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "certificate_id": self.certificate_id}


@dataclass(frozen=True, slots=True)
class H2QueryFamilyOccurrenceResultV1:
    occurrence_id: str
    query_id: str
    query_index: int
    before_commit_id: str
    after_commit_id: str
    logical_lower_count: int
    persisted_facet_count: int
    value_builder_calls: int
    identity_hits: int
    fresh_root_builder_calls: int
    ground_transition_calls: int
    process_launches: int
    store_read_bytes: int
    store_output_bytes: int
    resolutions: tuple[H2QueryFamilyResolutionV1, ...]
    fresh_roots: tuple[H2QueryFamilyFreshRootV1, ...]
    certificate: H2QueryFamilyPlanCertificateV1
    matching_buffer_imported: bool = False
    action_local_imported: bool = False
    recovery_imported: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.occurrence_id,
            self.query_id,
            self.before_commit_id,
            self.after_commit_id,
        ):
            _cid(value, "result identity")
        if (
            self.query_index not in (1, 2, 3)
            or self.logical_lower_count not in (18, 21, 24)
            or self.persisted_facet_count
            != self.logical_lower_count - 18
            or self.value_builder_calls not in (0, 3)
            or self.identity_hits != 18 - self.value_builder_calls
            or self.fresh_root_builder_calls != 3
            or self.ground_transition_calls != 0
            or self.process_launches not in (0, 1)
            or self.store_read_bytes <= 0
            or self.store_output_bytes < 0
            or len(self.resolutions) != 18
            or tuple(item.sequence_number for item in self.resolutions)
            != tuple(range(1, 19))
            or len(self.fresh_roots) != 3
            or any(
                type(item) is not H2QueryFamilyFreshRootV1
                for item in self.fresh_roots
            )
            or type(self.certificate) is not H2QueryFamilyPlanCertificateV1
            or self.certificate.occurrence_id != self.occurrence_id
            or self.certificate.query_id != self.query_id
            or self.matching_buffer_imported is not False
            or self.action_local_imported is not False
            or self.recovery_imported is not False
        ):
            raise H2QueryFamilyInvariantViolation("occurrence result changed")
        expected_output = self.value_builder_calls == 3
        if expected_output != (self.store_output_bytes > 0):
            raise H2QueryFamilyInvariantViolation("facet output accounting changed")
        if (
            tuple(item.address for item in self.resolutions) != ADDRESS_ORDER
            or any(
                item.occurrence_id != self.occurrence_id
                or item.query_id != self.query_id
                for item in self.resolutions
            )
            or sum(
                item.outcome is H2QueryFamilyResolutionOutcome.COMPUTED
                for item in self.resolutions
            )
            != self.value_builder_calls
        ):
            raise H2QueryFamilyInvariantViolation(
                "resolution/result binding changed"
            )
        root_n, root_m, selected = self.fresh_roots
        selected_candidate = root_n if selected.action == "N" else root_m
        active_ids = tuple(item.node_id for item in self.resolutions)
        resolution_nodes = {
            item.address: item.node_id for item in self.resolutions
        }
        if (
            (root_n.role, root_n.action, root_n.parent_root_ids)
            != ("CANDIDATE", "N", ())
            or (root_m.role, root_m.action, root_m.parent_root_ids)
            != ("CANDIDATE", "M", ())
            or (selected.role, selected.action)
            != ("SELECTED", self.certificate.selected_action)
            or selected.parent_root_ids != (root_n.root_id, root_m.root_id)
            or any(item.active_lower_node_ids != active_ids for item in self.fresh_roots)
            or any(
                item.occurrence_id != self.occurrence_id
                or item.query_id != self.query_id
                for item in self.fresh_roots
            )
            or any(
                item.selection_node_id != resolution_nodes["SELECTION"]
                for item in self.fresh_roots
            )
            or root_n.plan_node_id != resolution_nodes["PLAN_N"]
            or root_n.regret_node_id != resolution_nodes["REGRET_N"]
            or root_n.risk_node_id != resolution_nodes["RISK_N"]
            or root_n.coverage_node_id != resolution_nodes["COVERAGE_N"]
            or root_m.plan_node_id != resolution_nodes["PLAN_M"]
            or root_m.regret_node_id != resolution_nodes["REGRET_M"]
            or root_m.risk_node_id != resolution_nodes["RISK_M"]
            or root_m.coverage_node_id != resolution_nodes["COVERAGE_M"]
            or selected.plan_node_id != selected_candidate.plan_node_id
            or selected.regret_node_id != selected_candidate.regret_node_id
            or selected.risk_node_id != selected_candidate.risk_node_id
            or selected.coverage_node_id != selected_candidate.coverage_node_id
            or selected.reward_lower != selected_candidate.reward_lower
            or selected.failure_upper != selected_candidate.failure_upper
            or selected.normalized_regret
            != selected_candidate.normalized_regret
            or selected.certified is not selected_candidate.certified
            or self.certificate.selected_root_id != selected.root_id
            or self.certificate.selection_node_id != selected.selection_node_id
            or self.certificate.selected_action != selected.action
            or self.certificate.reward_lower != selected.reward_lower
            or self.certificate.failure_upper != selected.failure_upper
            or self.certificate.normalized_regret != selected.normalized_regret
            or self.certificate.certified is not selected.certified
        ):
            raise H2QueryFamilyInvariantViolation(
                "roots/certificate are not fully bound to lower resolutions"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_query_family_occurrence_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "query_id": self.query_id,
            "query_index": self.query_index,
            "before_commit_id": self.before_commit_id,
            "after_commit_id": self.after_commit_id,
            "logical_lower_count": self.logical_lower_count,
            "persisted_facet_count": self.persisted_facet_count,
            "value_builder_calls": self.value_builder_calls,
            "identity_hits": self.identity_hits,
            "fresh_root_builder_calls": self.fresh_root_builder_calls,
            "ground_transition_calls": self.ground_transition_calls,
            "process_launches": self.process_launches,
            "store_read_bytes": self.store_read_bytes,
            "store_output_bytes": self.store_output_bytes,
            "resolutions": [item.to_document() for item in self.resolutions],
            "fresh_roots": [item.to_document() for item in self.fresh_roots],
            "certificate": self.certificate.to_document(),
            "matching_buffer_imported": self.matching_buffer_imported,
            "action_local_imported": self.action_local_imported,
            "recovery_imported": self.recovery_imported,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def _active_lower_ids(
    query_index: int,
    payload: H2QueryFamilyStorePayloadV1,
    query_entries: Mapping[str, H2QueryFamilyFacetEntryV1],
) -> tuple[str, ...]:
    source = {item.address: item.node_id for item in payload.source_active_nodes}
    return tuple(
        query_entries[address].node_id
        if address in QUERY_FACET_ADDRESSES[query_index]
        else source[address]
        for address in ADDRESS_ORDER
    )


def _fresh_roots_and_certificate(
    occurrence: H2QueryFamilyOccurrenceV1,
    active_lower_ids: tuple[str, ...],
    semantic_nodes: Mapping[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ],
) -> tuple[
    tuple[H2QueryFamilyFreshRootV1, ...],
    H2QueryFamilyPlanCertificateV1,
]:
    selection = semantic_nodes["SELECTION"]
    candidate_roots = []
    for action in ("N", "M"):
        plan = semantic_nodes[f"PLAN_{action}"]
        regret = semantic_nodes[f"REGRET_{action}"]
        risk = semantic_nodes[f"RISK_{action}"]
        coverage = semantic_nodes[f"COVERAGE_{action}"]
        certified = all(
            _node_field(
                semantic_nodes[f"{role}_{action}"], "passes", "BOOLEAN"
            )
            is True
            for role in ("REGRET", "RISK", "COVERAGE")
        )
        candidate_roots.append(
            H2QueryFamilyFreshRootV1(
                occurrence.occurrence_id,
                occurrence.query_id,
                "CANDIDATE",
                action,
                _node_id(selection),
                _node_id(plan),
                _node_id(regret),
                _node_id(risk),
                _node_id(coverage),
                active_lower_ids,
                (),
                _fraction(
                    _node_field(plan, "reward_lower", "FRACTION"),
                    "root reward lower",
                ),
                _fraction(
                    _node_field(plan, "failure_upper", "FRACTION"),
                    "root failure upper",
                ),
                _fraction(
                    _node_field(regret, "normalized_regret", "FRACTION"),
                    "root normalized regret",
                ),
                certified,
            )
        )
    root_n, root_m = candidate_roots
    selected_action = _node_field(selection, "selected_action", "TEXT")
    selected_schedule = (
        _node_field(selection, "selected_schedule_code", "TEXT")
        if type(selection) is H2QueryFamilyFacetEntryV1
        else _node_field(selection, "schedule_code", "TEXT")
    )
    selected_candidate = root_n if selected_action == "N" else root_m
    selected = H2QueryFamilyFreshRootV1(
        occurrence.occurrence_id,
        occurrence.query_id,
        "SELECTED",
        selected_action,
        _node_id(selection),
        selected_candidate.plan_node_id,
        selected_candidate.regret_node_id,
        selected_candidate.risk_node_id,
        selected_candidate.coverage_node_id,
        active_lower_ids,
        (root_n.root_id, root_m.root_id),
        selected_candidate.reward_lower,
        selected_candidate.failure_upper,
        selected_candidate.normalized_regret,
        selected_candidate.certified,
    )
    certificate = H2QueryFamilyPlanCertificateV1(
        occurrence.occurrence_id,
        occurrence.query_id,
        selected.root_id,
        selected.selection_node_id,
        selected.action,
        selected_schedule,
        selected.reward_lower,
        selected.failure_upper,
        selected.normalized_regret,
        selected.certified,
    )
    return (root_n, root_m, selected), certificate


def resolve_h2_query_family_occurrence_v1(
    store_root: Path,
    expected_commit_id: str,
    occurrence: H2QueryFamilyOccurrenceV1,
    *,
    value_builder: Callable[
        [
            H2QueryFamilyFacetKeyV1,
            Mapping[
                str,
                H2QueryFamilySourceNodeRefV1
                | H2QueryFamilyFacetEntryV1,
            ],
        ],
        H2QueryFamilyFacetEntryV1,
    ] | None = None,
    _process_launches: int = 0,
) -> H2QueryFamilyOccurrenceResultV1:
    """Resolve one occurrence with a strict key-before-builder lazy protocol."""

    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence.occurrence_index
    )
    query = require_registered_h2_query_family_query_v1(
        protocol.query(occurrence.query_index),
        protocol,
        occurrence.query_index,
    )
    lease = load_verified_h2_query_family_store_v1(
        store_root, expected_commit_id
    )
    if lease.payload.protocol_id != protocol.protocol_id:
        raise H2QueryFamilyInvariantViolation("store/protocol binding changed")
    existing = {
        item.key.facet_key_id: item for item in lease.payload.facet_entries
    }
    builder = value_builder if value_builder is not None else _build_facet_entry
    semantic: dict[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ] = {item.address: item for item in lease.payload.source_active_nodes}
    built: list[H2QueryFamilyFacetEntryV1] = []
    keys: list[H2QueryFamilyFacetKeyV1] = []
    missed_key_ids: set[str] = set()
    # Phase A: gate keys exist before any gate builder can run.
    gate_keys = _gate_keys(protocol, query, lease.payload.source_active_nodes)
    gate_hits = {
        key.facet_key_id: existing.get(key.facet_key_id)
        for key in gate_keys
    }
    gate_misses = tuple(
        key for key in gate_keys if gate_hits[key.facet_key_id] is None
    )
    if len(gate_misses) not in (0, 2):
        raise H2QueryFamilyInvariantViolation(
            "partial threshold-gate hit is forbidden"
        )
    # Phase B: only gate misses reach the value builder.
    gate_entries: dict[str, H2QueryFamilyFacetEntryV1] = {}
    for key in gate_keys:
        entry = gate_hits[key.facet_key_id]
        if entry is None:
            entry = builder(key, semantic)
            missed_key_ids.add(key.facet_key_id)
            built.append(entry)
        if (
            type(entry) is not H2QueryFamilyFacetEntryV1
            or entry.key.to_document() != key.to_document()
            or entry.result_fields
            != _expected_facet_result_fields(key, semantic)
        ):
            raise H2QueryFamilyInvariantViolation(
                "value builder returned a noncanonical facet"
            )
        gate_entries[key.address] = entry
        semantic[key.address] = entry
        keys.append(key)
    # Phase C: selection key is constructed from resolved gate node IDs.
    if gate_keys:
        selection_key = _selection_key(
            protocol, lease.payload.source_active_nodes, gate_entries
        )
        keys.append(selection_key)
        selection_entry = existing.get(selection_key.facet_key_id)
        if selection_entry is None:
            selection_entry = builder(selection_key, semantic)
            missed_key_ids.add(selection_key.facet_key_id)
            built.append(selection_entry)
        if (
            type(selection_entry) is not H2QueryFamilyFacetEntryV1
            or selection_entry.key.to_document()
            != selection_key.to_document()
            or selection_entry.result_fields
            != _expected_facet_result_fields(selection_key, semantic)
        ):
            raise H2QueryFamilyInvariantViolation(
                "selection builder returned a noncanonical facet"
            )
        semantic["SELECTION"] = selection_entry
    if len(missed_key_ids) not in (0, 3):
        raise H2QueryFamilyInvariantViolation(
            "atomic facet group is partially materialized"
        )
    output_bytes = 0
    after_commit = lease.commit
    if built:
        after_commit, output_bytes = _append_facet_group(
            store_root, lease, occurrence.query_index, tuple(built)
        )
        after_lease = load_verified_h2_query_family_store_v1(
            store_root, after_commit.commit_id
        )
        store_read_bytes = lease.read_bytes + after_lease.read_bytes
        payload = after_lease.payload
    else:
        store_read_bytes = lease.read_bytes
        payload = lease.payload
    available = {
        item.key.facet_key_id: item for item in payload.facet_entries
    }
    query_entries = {
        key.address: available[key.facet_key_id] for key in keys
    }
    source = {item.address: item for item in payload.source_active_nodes}
    semantic = {**source, **query_entries}
    resolutions = []
    for sequence, address in enumerate(ADDRESS_ORDER, 1):
        if address in query_entries:
            key = next(item for item in keys if item.address == address)
            entry = query_entries[address]
            outcome = (
                H2QueryFamilyResolutionOutcome.COMPUTED
                if key.facet_key_id in missed_key_ids
                else H2QueryFamilyResolutionOutcome.REUSED
            )
            lookup_key_id = key.facet_key_id
            node_id = entry.node_id
        else:
            outcome = H2QueryFamilyResolutionOutcome.REUSED
            lookup_key_id = source[address].node_key_id
            node_id = source[address].node_id
        resolutions.append(
            H2QueryFamilyResolutionV1(
                sequence,
                occurrence.occurrence_id,
                occurrence.query_id,
                address,
                lookup_key_id,
                node_id,
                outcome,
            )
        )
    active_ids = _active_lower_ids(
        occurrence.query_index, payload, query_entries
    )
    roots, certificate = _fresh_roots_and_certificate(
        occurrence, active_ids, semantic
    )
    return H2QueryFamilyOccurrenceResultV1(
        occurrence.occurrence_id,
        occurrence.query_id,
        occurrence.query_index,
        lease.commit.commit_id,
        after_commit.commit_id,
        after_commit.logical_lower_count,
        after_commit.persisted_facet_count,
        len(missed_key_ids),
        18 - len(missed_key_ids),
        3,
        0,
        _process_launches,
        store_read_bytes,
        output_bytes,
        tuple(resolutions),
        roots,
        certificate,
    )


def _parse_resolution(document: Any) -> H2QueryFamilyResolutionV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "sequence_number",
            "occurrence_id",
            "query_id",
            "address",
            "lookup_key_id",
            "node_id",
            "outcome",
            "resolution_id",
        },
        "resolution",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_resolution.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise H2QueryFamilyInvariantViolation("resolution schema changed")
    try:
        outcome = H2QueryFamilyResolutionOutcome(row["outcome"])
    except (TypeError, ValueError) as error:
        raise H2QueryFamilyInvariantViolation("resolution outcome changed") from error
    result = H2QueryFamilyResolutionV1(
        row["sequence_number"],
        row["occurrence_id"],
        row["query_id"],
        row["address"],
        row["lookup_key_id"],
        row["node_id"],
        outcome,
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("resolution is not canonical")
    return result


def _parse_root(document: Any) -> H2QueryFamilyFreshRootV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "role",
            "action",
            "selection_node_id",
            "plan_node_id",
            "regret_node_id",
            "risk_node_id",
            "coverage_node_id",
            "active_lower_node_ids",
            "parent_root_ids",
            "reward_lower",
            "failure_upper",
            "normalized_regret",
            "certified",
            "root_id",
        },
        "fresh root",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_fresh_root.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["active_lower_node_ids"]) is not list
        or type(row["parent_root_ids"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("fresh-root schema changed")
    result = H2QueryFamilyFreshRootV1(
        row["occurrence_id"],
        row["query_id"],
        row["role"],
        row["action"],
        row["selection_node_id"],
        row["plan_node_id"],
        row["regret_node_id"],
        row["risk_node_id"],
        row["coverage_node_id"],
        tuple(row["active_lower_node_ids"]),
        tuple(row["parent_root_ids"]),
        _fraction(row["reward_lower"], "root reward lower"),
        _fraction(row["failure_upper"], "root failure upper"),
        _fraction(row["normalized_regret"], "root normalized regret"),
        row["certified"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("fresh root is not canonical")
    return result


def _parse_certificate(document: Any) -> H2QueryFamilyPlanCertificateV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "selected_root_id",
            "selection_node_id",
            "selected_action",
            "selected_schedule_code",
            "reward_lower",
            "failure_upper",
            "normalized_regret",
            "certified",
            "certificate_id",
        },
        "certificate",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_plan_certificate.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
    ):
        raise H2QueryFamilyInvariantViolation("certificate schema changed")
    result = H2QueryFamilyPlanCertificateV1(
        row["occurrence_id"],
        row["query_id"],
        row["selected_root_id"],
        row["selection_node_id"],
        row["selected_action"],
        row["selected_schedule_code"],
        _fraction(row["reward_lower"], "reward lower"),
        _fraction(row["failure_upper"], "failure upper"),
        _fraction(row["normalized_regret"], "normalized regret"),
        row["certified"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("certificate is not canonical")
    return result


def parse_h2_query_family_occurrence_result_document_v1(
    document: Any,
) -> H2QueryFamilyOccurrenceResultV1:
    row = _mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "query_id",
            "query_index",
            "before_commit_id",
            "after_commit_id",
            "logical_lower_count",
            "persisted_facet_count",
            "value_builder_calls",
            "identity_hits",
            "fresh_root_builder_calls",
            "ground_transition_calls",
            "process_launches",
            "store_read_bytes",
            "store_output_bytes",
            "resolutions",
            "fresh_roots",
            "certificate",
            "matching_buffer_imported",
            "action_local_imported",
            "recovery_imported",
            "result_id",
        },
        "occurrence result",
    )
    if (
        row["schema"] != "acfqp.h2_query_family_occurrence_result.v1"
        or row["schema_version"] != SCHEMA_VERSION
        or row["profile_key"] != PROFILE_KEY
        or type(row["resolutions"]) is not list
        or type(row["fresh_roots"]) is not list
    ):
        raise H2QueryFamilyInvariantViolation("occurrence-result schema changed")
    result = H2QueryFamilyOccurrenceResultV1(
        row["occurrence_id"],
        row["query_id"],
        row["query_index"],
        row["before_commit_id"],
        row["after_commit_id"],
        row["logical_lower_count"],
        row["persisted_facet_count"],
        row["value_builder_calls"],
        row["identity_hits"],
        row["fresh_root_builder_calls"],
        row["ground_transition_calls"],
        row["process_launches"],
        row["store_read_bytes"],
        row["store_output_bytes"],
        tuple(_parse_resolution(item) for item in row["resolutions"]),
        tuple(_parse_root(item) for item in row["fresh_roots"]),
        _parse_certificate(row["certificate"]),
        row["matching_buffer_imported"],
        row["action_local_imported"],
        row["recovery_imported"],
    )
    if not _same_document(result.to_document(), row):
        raise H2QueryFamilyInvariantViolation("occurrence result is not canonical")
    return result


def require_h2_query_family_occurrence_result_v1(
    result: H2QueryFamilyOccurrenceResultV1,
    occurrence: H2QueryFamilyOccurrenceV1,
) -> H2QueryFamilyOccurrenceResultV1:
    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence.occurrence_index
    )
    if (
        type(result) is not H2QueryFamilyOccurrenceResultV1
        or result.occurrence_id != occurrence.occurrence_id
        or result.query_id != occurrence.query_id
        or result.query_index != occurrence.query_index
        or result.certificate.selected_action != "M"
        or result.certificate.certified is not True
    ):
        raise H2QueryFamilyInvariantViolation(
            "occurrence result is not bound to the registered occurrence"
        )
    result.__post_init__()
    return result


def _reconstruct_expected_occurrence_result(
    before: VerifiedH2QueryFamilyStoreV1,
    after: VerifiedH2QueryFamilyStoreV1,
    occurrence: H2QueryFamilyOccurrenceV1,
    *,
    process_launches: int,
) -> H2QueryFamilyOccurrenceResultV1:
    """Rebuild the complete claimed result from verified before/after stores."""

    protocol = registered_h2_query_family_protocol_v1()
    query = protocol.query(occurrence.query_index)
    after_entries = {
        item.key.facet_key_id: item for item in after.payload.facet_entries
    }
    before_key_ids = {
        item.key.facet_key_id for item in before.payload.facet_entries
    }
    source = {item.address: item for item in after.payload.source_active_nodes}
    semantic: dict[
        str, H2QueryFamilySourceNodeRefV1 | H2QueryFamilyFacetEntryV1
    ] = dict(source)
    keys: list[H2QueryFamilyFacetKeyV1] = []
    gate_entries: dict[str, H2QueryFamilyFacetEntryV1] = {}
    for key in _gate_keys(protocol, query, after.payload.source_active_nodes):
        entry = after_entries.get(key.facet_key_id)
        if (
            entry is None
            or entry.result_fields
            != _expected_facet_result_fields(key, semantic)
        ):
            raise H2QueryFamilyInvariantViolation(
                "after-store lacks an exact query gate"
            )
        keys.append(key)
        gate_entries[key.address] = entry
        semantic[key.address] = entry
    if gate_entries:
        selection_key = _selection_key(
            protocol, after.payload.source_active_nodes, gate_entries
        )
        selection = after_entries.get(selection_key.facet_key_id)
        if (
            selection is None
            or selection.result_fields
            != _expected_facet_result_fields(selection_key, semantic)
        ):
            raise H2QueryFamilyInvariantViolation(
                "after-store lacks the exact resolved selection"
            )
        keys.append(selection_key)
        semantic["SELECTION"] = selection
    changed_key_ids = {
        key.facet_key_id for key in keys if key.facet_key_id not in before_key_ids
    }
    if len(changed_key_ids) not in (0, 3):
        raise H2QueryFamilyInvariantViolation(
            "before/after stores expose a partial query facet group"
        )
    if changed_key_ids:
        if (
            after.commit.previous_commit_id != before.commit.commit_id
            or after.commit.generation != before.commit.generation + 1
            or after.commit.appended_query_index != occurrence.query_index
        ):
            raise H2QueryFamilyInvariantViolation(
                "computed result is not bound to one append-only commit"
            )
        store_output_bytes = after.commit.payload_size_bytes + len(
            canonical_json_bytes(after.commit.to_document())
        )
        store_read_bytes = before.read_bytes + after.read_bytes
    else:
        if after.commit.commit_id != before.commit.commit_id:
            raise H2QueryFamilyInvariantViolation(
                "identity-hit result unexpectedly changed the store"
            )
        store_output_bytes = 0
        store_read_bytes = before.read_bytes
    query_entries = {
        key.address: after_entries[key.facet_key_id] for key in keys
    }
    semantic = {**source, **query_entries}
    resolutions = []
    for sequence, address in enumerate(ADDRESS_ORDER, 1):
        if address in query_entries:
            key = next(item for item in keys if item.address == address)
            resolutions.append(
                H2QueryFamilyResolutionV1(
                    sequence,
                    occurrence.occurrence_id,
                    occurrence.query_id,
                    address,
                    key.facet_key_id,
                    query_entries[address].node_id,
                    (
                        H2QueryFamilyResolutionOutcome.COMPUTED
                        if key.facet_key_id in changed_key_ids
                        else H2QueryFamilyResolutionOutcome.REUSED
                    ),
                )
            )
        else:
            resolutions.append(
                H2QueryFamilyResolutionV1(
                    sequence,
                    occurrence.occurrence_id,
                    occurrence.query_id,
                    address,
                    source[address].node_key_id,
                    source[address].node_id,
                    H2QueryFamilyResolutionOutcome.REUSED,
                )
            )
    active_ids = _active_lower_ids(
        occurrence.query_index, after.payload, query_entries
    )
    roots, certificate = _fresh_roots_and_certificate(
        occurrence, active_ids, semantic
    )
    return H2QueryFamilyOccurrenceResultV1(
        occurrence.occurrence_id,
        occurrence.query_id,
        occurrence.query_index,
        before.commit.commit_id,
        after.commit.commit_id,
        after.commit.logical_lower_count,
        after.commit.persisted_facet_count,
        len(changed_key_ids),
        18 - len(changed_key_ids),
        3,
        0,
        process_launches,
        store_read_bytes,
        store_output_bytes,
        tuple(resolutions),
        roots,
        certificate,
    )


def _worker_environment() -> dict[str, str]:
    result = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("LANG", "LC_ALL", "TZ"):
        if name in os.environ:
            result[name] = os.environ[name]
    return result


def _worker_command(
    *,
    store_root: Path,
    expected_commit_id: str,
    occurrence_index: int,
    output: Path,
    parent_process_id: int,
) -> tuple[str, ...]:
    source_root = Path(__file__).resolve().parents[1]
    bootstrap = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(source_root)!r});"
        "runpy.run_module("
        "'acfqp.h2_query_family_model_v1',run_name='__main__')"
    )
    return (
        sys.executable,
        "-I",
        "-s",
        "-B",
        "-c",
        bootstrap,
        "--worker",
        "--store-root",
        str(store_root.resolve()),
        "--expected-commit-id",
        expected_commit_id,
        "--occurrence-index",
        str(occurrence_index),
        "--output",
        str(output),
        "--parent-process-id",
        str(parent_process_id),
    )


def launch_h2_query_family_occurrence_fresh_worker_v1(
    store_root: Path,
    expected_commit_id: str,
    occurrence: H2QueryFamilyOccurrenceV1,
) -> H2QueryFamilyOccurrenceResultV1:
    """Resolve an occurrence in a fresh, isolated, model-only OS process."""

    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence.occurrence_index
    )
    before = load_verified_h2_query_family_store_v1(
        store_root, expected_commit_id
    )
    with tempfile.TemporaryDirectory(
        prefix="acfqp-h2-query-family-worker-"
    ) as directory:
        output = Path(directory) / "output.json"
        command = _worker_command(
            store_root=store_root,
            expected_commit_id=before.commit.commit_id,
            occurrence_index=occurrence.occurrence_index,
            output=output,
            parent_process_id=os.getpid(),
        )
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[2],
            env=_worker_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = process.communicate(timeout=1200)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise H2QueryFamilyInvariantViolation(
                "fresh query-family worker timed out"
            ) from error
        if process.returncode != 0:
            diagnostic = stderr.decode("utf-8", errors="replace")[-3000:]
            raise H2QueryFamilyInvariantViolation(
                f"fresh query-family worker failed with code "
                f"{process.returncode}: {diagnostic}"
            )
        if stdout:
            raise H2QueryFamilyInvariantViolation(
                "fresh query-family worker emitted stdout"
            )
        envelope = _mapping(
            loads_canonical_json(_read_stable(output)),
            {
                "schema",
                "schema_version",
                "profile_key",
                "child_process_id",
                "parent_process_id",
                "isolated_interpreter",
                "no_user_site",
                "bytecode_disabled",
                "artifact",
            },
            "worker envelope",
        )
        if (
            envelope["schema"] != "acfqp.h2_query_family_worker_envelope.v1"
            or envelope["schema_version"] != SCHEMA_VERSION
            or envelope["profile_key"] != PROFILE_KEY
            or envelope["child_process_id"] != process.pid
            or envelope["parent_process_id"] != os.getpid()
            or process.pid == os.getpid()
            or envelope["isolated_interpreter"] is not True
            or envelope["no_user_site"] is not True
            or envelope["bytecode_disabled"] is not True
        ):
            raise H2QueryFamilyInvariantViolation(
                "fresh worker process attestation changed"
            )
        result = parse_h2_query_family_occurrence_result_document_v1(
            envelope["artifact"]
        )
    require_h2_query_family_occurrence_result_v1(result, occurrence)
    after = load_verified_h2_query_family_store_v1(
        store_root, result.after_commit_id
    )
    expected = _reconstruct_expected_occurrence_result(
        before, after, occurrence, process_launches=1
    )
    if (
        result.to_document() != expected.to_document()
    ):
        raise H2QueryFamilyInvariantViolation(
            "worker result differs from host before/after semantic reconstruction"
        )
    return expected


def _worker_cli(arguments: argparse.Namespace) -> int:
    if os.getpid() == arguments.parent_process_id:
        raise H2QueryFamilyInvariantViolation("worker did not cross a process boundary")
    _assert_model_only_import_boundary(fresh_worker=True)
    occurrence = registered_h2_query_family_occurrence_v1(
        arguments.occurrence_index
    )
    result = resolve_h2_query_family_occurrence_v1(
        Path(arguments.store_root),
        arguments.expected_commit_id,
        occurrence,
        _process_launches=1,
    )
    # Check again after all parsing, lookup, building and persistence code ran.
    _assert_model_only_import_boundary(fresh_worker=True)
    envelope = {
        "schema": "acfqp.h2_query_family_worker_envelope.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "child_process_id": os.getpid(),
        "parent_process_id": arguments.parent_process_id,
        "isolated_interpreter": sys.flags.isolated == 1,
        "no_user_site": sys.flags.no_user_site == 1,
        "bytecode_disabled": sys.flags.dont_write_bytecode == 1,
        "artifact": result.to_document(),
    }
    output = Path(arguments.output)
    if output.exists() or output.is_symlink():
        raise H2QueryFamilyInvariantViolation("worker output target exists")
    _atomic_write(output, canonical_json_bytes(envelope))
    return 0


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--store-root")
    parser.add_argument("--expected-commit-id")
    parser.add_argument("--occurrence-index", type=int)
    parser.add_argument("--output")
    parser.add_argument("--parent-process-id", type=int)
    arguments = parser.parse_args(argv)
    if (
        not arguments.worker
        or type(arguments.store_root) is not str
        or type(arguments.expected_commit_id) is not str
        or type(arguments.occurrence_index) is not int
        or type(arguments.output) is not str
        or type(arguments.parent_process_id) is not int
    ):
        raise H2QueryFamilyInvariantViolation("worker arguments are incomplete")
    return _worker_cli(arguments)


__all__ = [
    "ADDRESS_ORDER",
    "CONTRACT_VERSION",
    "H2QueryFamilyFacetCommitV1",
    "H2QueryFamilyConsumedFacetV1",
    "H2QueryFamilyFacetEntryV1",
    "H2QueryFamilyFacetKeyV1",
    "H2QueryFamilyFreshRootV1",
    "H2QueryFamilyInitializationV1",
    "H2QueryFamilyInvariantViolation",
    "H2QueryFamilyOccurrenceResultV1",
    "H2QueryFamilyOccurrenceV1",
    "H2QueryFamilyPlanCertificateV1",
    "H2QueryFamilyPreregistrationV1",
    "H2QueryFamilyProtocolV1",
    "H2QueryFamilyQueryV1",
    "H2QueryFamilyResolutionOutcome",
    "H2QueryFamilyResolutionV1",
    "H2QueryFamilySourceNodeRefV1",
    "OCCURRENCE_QUERY_INDICES",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SOURCE_C2_COMMIT_ID",
    "SOURCE_C2_PAYLOAD_ID",
    "VerifiedH2QueryFamilySourceC2V1",
    "VerifiedH2QueryFamilyStoreV1",
    "initialize_h2_query_family_w0_v1",
    "launch_h2_query_family_occurrence_fresh_worker_v1",
    "load_verified_h2_query_family_source_c2_v1",
    "load_verified_h2_query_family_store_v1",
    "parse_h2_query_family_occurrence_document_v1",
    "parse_h2_query_family_occurrence_result_document_v1",
    "parse_h2_query_family_protocol_document_v1",
    "parse_h2_query_family_query_document_v1",
    "registered_h2_query_family_occurrence_v1",
    "registered_h2_query_family_preregistration_v1",
    "registered_h2_query_family_protocol_v1",
    "require_h2_query_family_occurrence_result_v1",
    "require_registered_h2_query_family_occurrence_v1",
    "require_registered_h2_query_family_protocol_v1",
    "require_registered_h2_query_family_query_v1",
    "resolve_h2_query_family_occurrence_v1",
]


if __name__ == "__main__":  # pragma: no cover - exercised by fresh workers
    raise SystemExit(_main())
