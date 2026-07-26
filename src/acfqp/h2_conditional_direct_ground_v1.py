"""Source-blind conditional-online direct comparator for the H2 LMB family.

The comparator receives only a preregistered query and its logical-occurrence
identity.  A fresh isolated process reconstructs the frozen LMB fixture,
enumerates the complete downstream action catalogue, acquires exactly the one
row absent from the registered offline base, and evaluates all four
deterministic H2 ground policies.

No checkpoint, overlay, reusable-model result, or recovery-source artifact is
an input to this module.  The comparator is deliberately conditional-online:
the registered S/N rows are frozen offline inputs, while the M row is queried
once per occurrence.  Its counters are narrow native event counts, not an
official scalar cost or a sample-efficiency claim.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.h2_query_family_model_v1 import (
    H2QueryFamilyOccurrenceV1,
    H2QueryFamilyQueryV1,
    registered_h2_query_family_occurrence_v1,
    registered_h2_query_family_protocol_v1,
    require_registered_h2_query_family_occurrence_v1,
    require_registered_h2_query_family_protocol_v1,
    require_registered_h2_query_family_query_v1,
)
from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.20.0"
PROFILE_KEY = "lmb_h2_conditional_online_direct_ground_v0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_H2_CONDITIONAL_ONLINE_DIRECT_GROUND"

TILE_TYPES = (1, 0, 0, 0, 1, 1)
BLOCKERS = (
    frozenset({4, 5}),
    frozenset({4}),
    frozenset({4}),
    frozenset({4, 5}),
    frozenset(),
    frozenset(),
)
TYPE_COUNT = 2
CAPACITY = 3
MAX_LAYERS = 4

EXPECTED_KERNEL_SOURCE_SHA256 = (
    "82bef64d20aa10bc6920fd67a9dc7db0c8c7e310170f93bf4e90c7995d5416da"
)
EXPECTED_KERNEL_ACTIONS_SOURCE_SHA256 = (
    "8f0e55e8cd6ab607c9983dc85a1474e87a59b192406736b4b4e08d0d5a9c142e"
)
EXPECTED_KERNEL_STEP_SOURCE_SHA256 = (
    "5849a61d4424df3146499125dcee95623a769caa539655ca66d53af9157ee6af"
)
EXPECTED_X0_STATE_ID = (
    "923ac69167104293200e5f71263951ec6207d04b576d759fa28f589ce5940c37"
)
EXPECTED_X1_STATE_ID = (
    "52acc4ceec0b25ef96c6c039e39adfdd5cbd728d9b974b7ebb029e4a7ec62226"
)
EXPECTED_OFFLINE_ACTION_IDS = {
    "S": "ecdb44bfdbb033cb123af61b70f31e9d05af1dc4e44a9a3afa89665c71cc9d47",
    "N1": "06e38f83f744b311078d3b79238bf87226e718b9eb765d3c90f11d5de4b1bc8e",
    "N2": "7e669425c9fcd4a227741ed1bbf4f585a037cbdb2cb4256077174212eedf610f",
    "N3": "a2458fcd6e21916217dd3651c1823709e4674a1a9268669fab4d32410abdde54",
}
EXPECTED_OFFLINE_GROUND_ROW_IDS = {
    "S": "cf0ebe94dc11825e0f1aa820487a5439efd1615d5fd2b95b16346f61c9b8274b",
    "N1": "a5a288985739f75fc7540a5d0df7b0d4a5e6d56b12989fb596b9dcdf4712b8d6",
    "N2": "c4566f8e43470f739188052a430a58cf8e3b956025f9d548885bbd1b64c40aa3",
    "N3": "db320fcc2bc7f7ad0fdbd4199f974574d581181e377f04c2c9465ffd3aab5503",
}

DOMAIN_TAGS = {
    "structural": "acfqp:h2-conditional-direct-structural:v1",
    "offline_base": "acfqp:h2-conditional-direct-offline-base:v1",
    "policy_evaluation": "acfqp:h2-conditional-direct-policy-evaluation:v1",
    "native_trace": "acfqp:h2-conditional-direct-native-trace:v1",
    "result": "acfqp:h2-conditional-direct-result:v1",
    "launch": "acfqp:h2-conditional-direct-launch:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("conditional-direct content domains must be unique")

_CANONICAL_LMB_ACTIONS = LMBKernel.actions
_CANONICAL_LMB_STEP = LMBKernel.step


class ConditionalDirectGroundInvariantViolation(ValueError):
    """The direct-comparator input, execution, or result is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ConditionalDirectGroundInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConditionalDirectGroundInvariantViolation(
            f"{name} must be a full lowercase SHA-256 content ID"
        ) from error


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ConditionalDirectGroundInvariantViolation(
            f"{name} must be an exact integer >= {minimum}"
        )
    return value


def _boolean(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ConditionalDirectGroundInvariantViolation(
            f"{name} must be an exact boolean"
        )
    return value


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ConditionalDirectGroundInvariantViolation(f"{name} must be exact")
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        numerator = value["numerator"]
        denominator = value["denominator"]
        if (
            type(numerator) is not int
            or type(denominator) is not int
            or denominator <= 0
        ):
            raise ConditionalDirectGroundInvariantViolation(
                f"{name} rational is invalid"
            )
        result = Fraction(numerator, denominator)
        if result.numerator != numerator or result.denominator != denominator:
            raise ConditionalDirectGroundInvariantViolation(
                f"{name} rational is not reduced"
            )
        return result
    raise ConditionalDirectGroundInvariantViolation(f"{name} must be exact")


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _normalize_document(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _fdoc(value)
    if type(value) is dict:
        return {
            key: _normalize_document(item)
            for key, item in value.items()
        }
    if type(value) in (list, tuple):
        return [_normalize_document(item) for item in value]
    return value


def _exact_mapping(
    value: Any,
    fields: set[str],
    where: str,
) -> dict[str, Any]:
    normalized = _normalize_document(value)
    if type(normalized) is not dict:
        raise ConditionalDirectGroundInvariantViolation(
            f"{where} must be an exact JSON object"
        )
    actual = set(normalized)
    if actual != fields:
        raise ConditionalDirectGroundInvariantViolation(
            f"{where} field set changed; "
            f"missing={sorted(fields - actual)!r}, "
            f"unknown={sorted(actual - fields)!r}"
        )
    return normalized


def _source_sha256(callable_or_class: Any) -> str:
    try:
        source = inspect.getsource(callable_or_class).encode("utf-8")
    except (OSError, TypeError) as error:
        raise ConditionalDirectGroundInvariantViolation(
            "canonical LMB source cannot be inspected"
        ) from error
    return hashlib.sha256(source).hexdigest()


def _kernel_file_sha256() -> str:
    source = inspect.getsourcefile(LMBKernel)
    if not source:
        raise ConditionalDirectGroundInvariantViolation(
            "canonical LMB kernel has no source file"
        )
    path = Path(source).resolve()
    try:
        if path.suffix != ".py" or not path.is_file() or path.is_symlink():
            raise OSError("not a regular Python source")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ConditionalDirectGroundInvariantViolation(
            "canonical LMB kernel source cannot be read"
        ) from error


def _assert_canonical_kernel_authority() -> None:
    if (
        LMBKernel.actions is not _CANONICAL_LMB_ACTIONS
        or LMBKernel.step is not _CANONICAL_LMB_STEP
        or getattr(_CANONICAL_LMB_ACTIONS, "__module__", None)
        != "acfqp.domains.matching_buffer"
        or getattr(_CANONICAL_LMB_ACTIONS, "__qualname__", None)
        != "LMBKernel.actions"
        or getattr(_CANONICAL_LMB_STEP, "__module__", None)
        != "acfqp.domains.matching_buffer"
        or getattr(_CANONICAL_LMB_STEP, "__qualname__", None) != "LMBKernel.step"
        or _kernel_file_sha256() != EXPECTED_KERNEL_SOURCE_SHA256
        or _source_sha256(_CANONICAL_LMB_ACTIONS)
        != EXPECTED_KERNEL_ACTIONS_SOURCE_SHA256
        or _source_sha256(_CANONICAL_LMB_STEP)
        != EXPECTED_KERNEL_STEP_SOURCE_SHA256
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "canonical LMB actions/step authority changed"
        )


def _literal_kernel_v1() -> LMBKernel:
    _assert_canonical_kernel_authority()
    return LMBKernel(
        TILE_TYPES,
        BLOCKERS,
        TYPE_COUNT,
        CAPACITY,
        MAX_LAYERS,
    )


def _structural_payload() -> dict[str, Any]:
    return {
        "schema": "acfqp.h2_conditional_direct_structural.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "kernel_class": "acfqp.domains.matching_buffer.LMBKernel",
        "tile_types": list(TILE_TYPES),
        "blockers": [sorted(item) for item in BLOCKERS],
        "type_count": TYPE_COUNT,
        "capacity": CAPACITY,
        "max_layers": MAX_LAYERS,
        "kernel_source_sha256": EXPECTED_KERNEL_SOURCE_SHA256,
        "kernel_actions_source_sha256": EXPECTED_KERNEL_ACTIONS_SOURCE_SHA256,
        "kernel_step_source_sha256": EXPECTED_KERNEL_STEP_SOURCE_SHA256,
    }


def conditional_direct_structural_id_v1() -> str:
    return _content_id("structural", _structural_payload())


_OFFLINE_ROWS = (
    ("S", "x0", 4, Fraction(0), False, False),
    ("N1", "x1", 1, Fraction(0), False, False),
    ("N2", "x1", 2, Fraction(0), False, False),
    ("N3", "x1", 3, Fraction(0), False, False),
)
_CANONICAL_OFFLINE_ROWS = _OFFLINE_ROWS


def _assert_offline_base() -> None:
    if (
        _OFFLINE_ROWS is not _CANONICAL_OFFLINE_ROWS
        or _OFFLINE_ROWS
        != (
            ("S", "x0", 4, Fraction(0), False, False),
            ("N1", "x1", 1, Fraction(0), False, False),
            ("N2", "x1", 2, Fraction(0), False, False),
            ("N3", "x1", 3, Fraction(0), False, False),
        )
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "registered offline S/N base changed"
        )


def _offline_base_payload() -> dict[str, Any]:
    _assert_offline_base()
    return {
        "schema": "acfqp.h2_conditional_direct_offline_base.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "structural_id": conditional_direct_structural_id_v1(),
        "rows": [
            {
                "name": name,
                "state_key": state_key,
                "state_id": (
                    EXPECTED_X0_STATE_ID
                    if state_key == "x0"
                    else EXPECTED_X1_STATE_ID
                ),
                "tile": tile,
                "action_key": f"tile={tile}",
                "action_id": EXPECTED_OFFLINE_ACTION_IDS[name],
                "ground_row_id": EXPECTED_OFFLINE_GROUND_ROW_IDS[name],
                "reward": _fdoc(reward),
                "failure": failure,
                "terminal": terminal,
                "lane": "OFFLINE_REGISTERED_BASE",
            }
            for name, state_key, tile, reward, failure, terminal in _OFFLINE_ROWS
        ],
        "offline_ground_work_charged_per_occurrence": False,
        "missing_online_row": "M",
    }


def conditional_direct_offline_base_id_v1() -> str:
    return _content_id("offline_base", _offline_base_payload())


def conditional_direct_offline_base_document_v1() -> dict[str, Any]:
    """Return the source-independent four-row C1 projection for host audit."""

    payload = _offline_base_payload()
    return {
        **payload,
        "offline_base_id": _content_id("offline_base", payload),
    }


@dataclass(frozen=True, slots=True)
class ConditionalDirectPolicyEvaluationV1:
    policy_index: int
    policy_code: str
    downstream_row: str
    downstream_tile: int
    reward: Fraction
    failure_probability: Fraction
    online_row: bool

    def __post_init__(self) -> None:
        _integer(self.policy_index, "policy index", 1)
        _integer(self.downstream_tile, "downstream tile")
        object.__setattr__(
            self, "reward", _fraction(self.reward, "policy reward")
        )
        object.__setattr__(
            self,
            "failure_probability",
            _fraction(self.failure_probability, "policy failure"),
        )
        if type(self.policy_code) is not str or type(self.downstream_row) is not str:
            raise ConditionalDirectGroundInvariantViolation(
                "policy code/row must be exact text"
            )
        _boolean(self.online_row, "online-row flag")
        expected = {
            1: ("A0A1", "M", 0, Fraction(1), Fraction(0), True),
            2: ("A0A0_N1", "N1", 1, Fraction(0), Fraction(0), False),
            3: ("A0A0_N2", "N2", 2, Fraction(0), Fraction(0), False),
            4: ("A0A0_N3", "N3", 3, Fraction(0), Fraction(0), False),
        }.get(self.policy_index)
        actual = (
            self.policy_code,
            self.downstream_row,
            self.downstream_tile,
            self.reward,
            self.failure_probability,
            self.online_row,
        )
        if expected is None or actual != expected:
            raise ConditionalDirectGroundInvariantViolation(
                "registered H2 policy evaluation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_conditional_direct_policy_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "policy_index": self.policy_index,
            "policy_code": self.policy_code,
            "downstream_row": self.downstream_row,
            "downstream_tile": self.downstream_tile,
            "reward": _fdoc(self.reward),
            "failure_probability": _fdoc(self.failure_probability),
            "online_row": self.online_row,
        }

    @property
    def evaluation_id(self) -> str:
        return _content_id("policy_evaluation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evaluation_id": self.evaluation_id}


def parse_conditional_direct_policy_evaluation_document_v1(
    document: Any,
) -> ConditionalDirectPolicyEvaluationV1:
    record = _exact_mapping(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "policy_index",
            "policy_code",
            "downstream_row",
            "downstream_tile",
            "reward",
            "failure_probability",
            "online_row",
            "evaluation_id",
        },
        "conditional-direct policy evaluation",
    )
    if (
        record["schema"]
        != "acfqp.h2_conditional_direct_policy_evaluation.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct policy schema/profile changed"
        )
    result = ConditionalDirectPolicyEvaluationV1(
        record["policy_index"],
        record["policy_code"],
        record["downstream_row"],
        record["downstream_tile"],
        _fraction(record["reward"], "policy reward"),
        _fraction(record["failure_probability"], "policy failure"),
        record["online_row"],
    )
    if record["evaluation_id"] != result.evaluation_id:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct policy content ID mismatch"
        )
    return result


@dataclass(frozen=True, slots=True)
class ConditionalDirectNativeTraceV1:
    ground_transition_calls: int
    action_catalogue_calls: int
    policy_evaluations: int
    optimizer_calls: int
    process_launches: int
    offline_rows_consumed: int
    online_rows_acquired: int
    source_artifact_inputs: int
    checkpoint_inputs: int
    overlay_inputs: int

    def __post_init__(self) -> None:
        for field in (
            "ground_transition_calls",
            "action_catalogue_calls",
            "policy_evaluations",
            "optimizer_calls",
            "process_launches",
            "offline_rows_consumed",
            "online_rows_acquired",
            "source_artifact_inputs",
            "checkpoint_inputs",
            "overlay_inputs",
        ):
            _integer(getattr(self, field), field)
        if (
            self.ground_transition_calls,
            self.action_catalogue_calls,
            self.policy_evaluations,
            self.optimizer_calls,
            self.process_launches,
            self.offline_rows_consumed,
            self.online_rows_acquired,
            self.source_artifact_inputs,
            self.checkpoint_inputs,
            self.overlay_inputs,
        ) != (1, 1, 4, 1, 1, 4, 1, 0, 0, 0):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct native trace changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_conditional_direct_native_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ground_transition_calls": self.ground_transition_calls,
            "action_catalogue_calls": self.action_catalogue_calls,
            "policy_evaluations": self.policy_evaluations,
            "optimizer_calls": self.optimizer_calls,
            "process_launches": self.process_launches,
            "offline_rows_consumed": self.offline_rows_consumed,
            "online_rows_acquired": self.online_rows_acquired,
            "source_artifact_inputs": self.source_artifact_inputs,
            "checkpoint_inputs": self.checkpoint_inputs,
            "overlay_inputs": self.overlay_inputs,
        }

    @property
    def trace_id(self) -> str:
        return _content_id("native_trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


def parse_conditional_direct_native_trace_document_v1(
    document: Any,
) -> ConditionalDirectNativeTraceV1:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "ground_transition_calls",
        "action_catalogue_calls",
        "policy_evaluations",
        "optimizer_calls",
        "process_launches",
        "offline_rows_consumed",
        "online_rows_acquired",
        "source_artifact_inputs",
        "checkpoint_inputs",
        "overlay_inputs",
        "trace_id",
    }
    record = _exact_mapping(document, fields, "conditional-direct native trace")
    if (
        record["schema"] != "acfqp.h2_conditional_direct_native_trace.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct trace schema/profile changed"
        )
    result = ConditionalDirectNativeTraceV1(
        *(
            record[name]
            for name in (
                "ground_transition_calls",
                "action_catalogue_calls",
                "policy_evaluations",
                "optimizer_calls",
                "process_launches",
                "offline_rows_consumed",
                "online_rows_acquired",
                "source_artifact_inputs",
                "checkpoint_inputs",
                "overlay_inputs",
            )
        )
    )
    if record["trace_id"] != result.trace_id:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct trace content ID mismatch"
        )
    return result


class _ConditionalDirectNativeRecorderV1:
    """Trusted execution-local counter recorder; not a hostile capability."""

    __slots__ = (
        "_counts",
        "_frozen",
    )

    _FIELDS = (
        "ground_transition_calls",
        "action_catalogue_calls",
        "policy_evaluations",
        "optimizer_calls",
        "process_launches",
        "offline_rows_consumed",
        "online_rows_acquired",
        "source_artifact_inputs",
        "checkpoint_inputs",
        "overlay_inputs",
    )

    def __init__(self) -> None:
        self._counts = {name: 0 for name in self._FIELDS}
        self._frozen = False

    def record(self, name: str) -> None:
        if self._frozen or name not in self._counts:
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct recorder event is invalid or late"
            )
        self._counts[name] += 1

    def freeze(self) -> ConditionalDirectNativeTraceV1:
        if self._frozen:
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct recorder was already frozen"
            )
        expected = {
            "ground_transition_calls": 1,
            "action_catalogue_calls": 1,
            "policy_evaluations": 4,
            "optimizer_calls": 1,
            "process_launches": 1,
            "offline_rows_consumed": 4,
            "online_rows_acquired": 1,
            "source_artifact_inputs": 0,
            "checkpoint_inputs": 0,
            "overlay_inputs": 0,
        }
        if self._counts != expected:
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct dynamic execution counters are incomplete"
            )
        self._frozen = True
        return ConditionalDirectNativeTraceV1(
            *(self._counts[name] for name in self._FIELDS)
        )


class _CatalogueBoundKernelViewV1:
    """Expose a verified one-shot catalogue to the canonical step callable."""

    __slots__ = (
        "_kernel",
        "_guard",
    )

    def __init__(
        self,
        kernel: LMBKernel,
        guard: "_ConditionalDirectSingleUseMGuardV1",
    ) -> None:
        self._kernel = kernel
        self._guard = guard

    @property
    def tile_types(self) -> tuple[int, ...]:
        return self._kernel.tile_types

    @property
    def tile_count(self) -> int:
        return self._kernel.tile_count

    @property
    def capacity(self) -> int:
        return self._kernel.capacity

    def _validate_state(self, state: LMBState) -> None:
        self._kernel._validate_state(state)

    def actions(self, state: LMBState) -> tuple[LMBAction, ...]:
        return self._guard._consume_catalogue_inside_step(state)


class _ConditionalDirectSingleUseMGuardV1:
    """Trusted one-shot ordering guard for the registered catalogue/M call."""

    __slots__ = (
        "_recorder",
        "_catalogue",
        "_catalogue_consumed_inside_step",
        "_inside_step",
        "_stepped",
        "_closed",
    )

    def __init__(self, recorder: _ConditionalDirectNativeRecorderV1) -> None:
        if type(recorder) is not _ConditionalDirectNativeRecorderV1:
            raise ConditionalDirectGroundInvariantViolation(
                "single-use M guard requires its trusted recorder"
            )
        self._recorder = recorder
        self._catalogue: tuple[LMBAction, ...] | None = None
        self._catalogue_consumed_inside_step = False
        self._inside_step = False
        self._stepped = False
        self._closed = False

    @staticmethod
    def _require_x1(state: LMBState) -> None:
        if (
            type(state) is not LMBState
            or state != LMBState(48, (0, 2), LMBStatus.ACTIVE)
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct guard only accepts registered x1"
            )

    @staticmethod
    def _require_kernel(kernel: LMBKernel) -> None:
        if type(kernel) is not LMBKernel or (
            kernel.tile_types,
            kernel.blockers,
            kernel.type_count,
            kernel.capacity,
            kernel.max_layers,
        ) != (
            TILE_TYPES,
            BLOCKERS,
            TYPE_COUNT,
            CAPACITY,
            MAX_LAYERS,
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct guard requires the literal LMB kernel"
            )

    def actions(
        self,
        kernel: LMBKernel,
        state: LMBState,
    ) -> tuple[LMBAction, ...]:
        self._require_kernel(kernel)
        self._require_x1(state)
        if (
            self._closed
            or self._catalogue is not None
            or self._inside_step
            or self._stepped
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct catalogue call is duplicate or out of order"
            )
        catalogue = _CANONICAL_LMB_ACTIONS(kernel, state)
        if catalogue != tuple(LMBAction(tile) for tile in (0, 1, 2, 3)):
            raise ConditionalDirectGroundInvariantViolation(
                "complete downstream ground action catalogue changed"
            )
        self._catalogue = catalogue
        self._recorder.record("action_catalogue_calls")
        return catalogue

    def _consume_catalogue_inside_step(
        self,
        state: LMBState,
    ) -> tuple[LMBAction, ...]:
        self._require_x1(state)
        if (
            not self._inside_step
            or self._catalogue is None
            or self._catalogue_consumed_inside_step
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "canonical step catalogue access is missing, duplicate, or external"
            )
        self._catalogue_consumed_inside_step = True
        return self._catalogue

    def step_m(
        self,
        kernel: LMBKernel,
        state: LMBState,
        action: LMBAction,
    ) -> tuple[Any, ...]:
        self._require_kernel(kernel)
        self._require_x1(state)
        if type(action) is not LMBAction or action != LMBAction(0):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct guard only accepts the registered x1/M row"
            )
        if (
            self._closed
            or self._catalogue is None
            or self._stepped
            or self._inside_step
            or self._catalogue_consumed_inside_step
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct M step is duplicate or out of order"
            )
        self._inside_step = True
        self._recorder.record("ground_transition_calls")
        try:
            outcomes = _CANONICAL_LMB_STEP(
                _CatalogueBoundKernelViewV1(kernel, self),
                state,
                action,
            )
        finally:
            self._inside_step = False
        if not self._catalogue_consumed_inside_step:
            raise ConditionalDirectGroundInvariantViolation(
                "canonical step did not consume the verified catalogue"
            )
        self._stepped = True
        return outcomes

    def close(self) -> None:
        if (
            self._closed
            or self._catalogue is None
            or not self._catalogue_consumed_inside_step
            or not self._stepped
            or self._inside_step
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct single-use M guard is incomplete"
            )
        self._closed = True


@dataclass(frozen=True, slots=True)
class ConditionalDirectGroundResultV1:
    protocol_id: str
    query_id: str
    occurrence_id: str
    query_index: int
    occurrence_index: int
    structural_id: str
    offline_base_id: str
    complete_action_tiles: tuple[int, ...]
    policy_results: tuple[ConditionalDirectPolicyEvaluationV1, ...]
    selected_policy_code: str
    selected_row: str
    expected_reward: Fraction
    failure_probability: Fraction
    unrestricted_ground_value: Fraction
    return_upper: Fraction
    normalized_regret: Fraction
    normalized_regret_tolerance: Fraction
    risk_tolerance: Fraction
    regret_passed: bool
    risk_passed: bool
    certified: bool
    native_trace: ConditionalDirectNativeTraceV1
    status: str = SUCCESS_STATUS

    def __post_init__(self) -> None:
        for value, name in (
            (self.protocol_id, "protocol"),
            (self.query_id, "query"),
            (self.occurrence_id, "occurrence"),
            (self.structural_id, "structural"),
            (self.offline_base_id, "offline base"),
        ):
            _cid(value, name)
        _integer(self.query_index, "query index", 1)
        _integer(self.occurrence_index, "occurrence index", 1)
        if (
            type(self.complete_action_tiles) is not tuple
            or self.complete_action_tiles != (0, 1, 2, 3)
            or type(self.policy_results) is not tuple
            or len(self.policy_results) != 4
            or any(
                type(item) is not ConditionalDirectPolicyEvaluationV1
                for item in self.policy_results
            )
            or tuple(item.policy_index for item in self.policy_results)
            != (1, 2, 3, 4)
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "complete direct policy enumeration changed"
            )
        for field in (
            "expected_reward",
            "failure_probability",
            "unrestricted_ground_value",
            "return_upper",
            "normalized_regret",
            "normalized_regret_tolerance",
            "risk_tolerance",
        ):
            object.__setattr__(
                self, field, _fraction(getattr(self, field), field)
            )
        for field in ("regret_passed", "risk_passed", "certified"):
            _boolean(getattr(self, field), field)
        if type(self.native_trace) is not ConditionalDirectNativeTraceV1:
            raise ConditionalDirectGroundInvariantViolation(
                "direct result rejects copied native trace"
            )
        query = _registered_query_for_indices(
            self.query_index,
            self.occurrence_index,
            self.query_id,
            self.occurrence_id,
        )[0]
        protocol = registered_h2_query_family_protocol_v1()
        if (
            self.protocol_id != protocol.protocol_id
            or self.structural_id != conditional_direct_structural_id_v1()
            or self.offline_base_id != conditional_direct_offline_base_id_v1()
            or self.selected_policy_code != "A0A1"
            or self.selected_row != "M"
            or self.expected_reward != 1
            or self.failure_probability != 0
            or self.unrestricted_ground_value != 1
            or self.return_upper != 4
            or self.normalized_regret != 0
            or self.normalized_regret_tolerance
            != query.normalized_regret_tolerance
            or self.risk_tolerance != query.risk_tolerance
            or self.regret_passed is not True
            or self.risk_passed is not True
            or self.certified is not True
            or self.status != SUCCESS_STATUS
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct result semantics changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_conditional_direct_ground_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "protocol_id": self.protocol_id,
            "query_id": self.query_id,
            "occurrence_id": self.occurrence_id,
            "query_index": self.query_index,
            "occurrence_index": self.occurrence_index,
            "structural_id": self.structural_id,
            "offline_base_id": self.offline_base_id,
            "complete_action_tiles": list(self.complete_action_tiles),
            "policy_results": [
                item.to_document() for item in self.policy_results
            ],
            "policy_evaluations": self.policy_evaluations,
            "selected_policy_code": self.selected_policy_code,
            "selected_row": self.selected_row,
            "selected_action": self.selected_action,
            "expected_reward": _fdoc(self.expected_reward),
            "reward": _fdoc(self.reward),
            "failure_probability": _fdoc(self.failure_probability),
            "unrestricted_ground_value": _fdoc(self.unrestricted_ground_value),
            "return_upper": _fdoc(self.return_upper),
            "normalized_regret": _fdoc(self.normalized_regret),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "regret_passed": self.regret_passed,
            "risk_passed": self.risk_passed,
            "certified": self.certified,
            "native_trace": self.native_trace.to_document(),
            "exact_ground_transition_calls": (
                self.exact_ground_transition_calls
            ),
            "exact_action_catalogue_calls": (
                self.exact_action_catalogue_calls
            ),
            "optimizer_calls": self.optimizer_calls,
            "process_launches": self.process_launches,
            "matching_buffer_imported": self.matching_buffer_imported,
            "status": self.status,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

    @property
    def selected_action(self) -> str:
        return self.selected_row

    @property
    def reward(self) -> Fraction:
        return self.expected_reward

    @property
    def exact_ground_transition_calls(self) -> int:
        return self.native_trace.ground_transition_calls

    @property
    def exact_action_catalogue_calls(self) -> int:
        return self.native_trace.action_catalogue_calls

    @property
    def policy_evaluations(self) -> int:
        return self.native_trace.policy_evaluations

    @property
    def optimizer_calls(self) -> int:
        return self.native_trace.optimizer_calls

    @property
    def process_launches(self) -> int:
        return self.native_trace.process_launches

    @property
    def matching_buffer_imported(self) -> bool:
        return True


def parse_conditional_direct_ground_result_document_v1(
    document: Any,
) -> ConditionalDirectGroundResultV1:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "protocol_id",
        "query_id",
        "occurrence_id",
        "query_index",
        "occurrence_index",
        "structural_id",
        "offline_base_id",
        "complete_action_tiles",
        "policy_results",
        "policy_evaluations",
        "selected_policy_code",
        "selected_row",
        "selected_action",
        "expected_reward",
        "reward",
        "failure_probability",
        "unrestricted_ground_value",
        "return_upper",
        "normalized_regret",
        "normalized_regret_tolerance",
        "risk_tolerance",
        "regret_passed",
        "risk_passed",
        "certified",
        "native_trace",
        "exact_ground_transition_calls",
        "exact_action_catalogue_calls",
        "optimizer_calls",
        "process_launches",
        "matching_buffer_imported",
        "status",
        "result_id",
    }
    record = _exact_mapping(document, fields, "conditional-direct result")
    if (
        record["schema"] != "acfqp.h2_conditional_direct_ground_result.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
        or type(record["complete_action_tiles"]) is not list
        or type(record["policy_results"]) is not list
        or record["policy_evaluations"] != 4
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct result schema/profile changed"
        )
    result = ConditionalDirectGroundResultV1(
        record["protocol_id"],
        record["query_id"],
        record["occurrence_id"],
        record["query_index"],
        record["occurrence_index"],
        record["structural_id"],
        record["offline_base_id"],
        tuple(record["complete_action_tiles"]),
        tuple(
            parse_conditional_direct_policy_evaluation_document_v1(item)
            for item in record["policy_results"]
        ),
        record["selected_policy_code"],
        record["selected_row"],
        _fraction(record["expected_reward"], "expected reward"),
        _fraction(record["failure_probability"], "failure"),
        _fraction(record["unrestricted_ground_value"], "ground value"),
        _fraction(record["return_upper"], "return upper"),
        _fraction(record["normalized_regret"], "normalized regret"),
        _fraction(
            record["normalized_regret_tolerance"],
            "normalized regret tolerance",
        ),
        _fraction(record["risk_tolerance"], "risk tolerance"),
        record["regret_passed"],
        record["risk_passed"],
        record["certified"],
        parse_conditional_direct_native_trace_document_v1(
            record["native_trace"]
        ),
        record["status"],
    )
    if record["result_id"] != result.result_id:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct result content ID mismatch"
        )
    if (
        record["selected_action"] != result.selected_action
        or _fraction(record["reward"], "reward") != result.reward
        or record["exact_ground_transition_calls"]
        != result.exact_ground_transition_calls
        or record["exact_action_catalogue_calls"]
        != result.exact_action_catalogue_calls
        or record["optimizer_calls"] != result.optimizer_calls
        or record["process_launches"] != result.process_launches
        or record["matching_buffer_imported"]
        is not result.matching_buffer_imported
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct derived result fields changed"
        )
    return result


def require_conditional_direct_ground_result_v1(
    result: ConditionalDirectGroundResultV1,
) -> ConditionalDirectGroundResultV1:
    if type(result) is not ConditionalDirectGroundResultV1:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct result rejects substitutions"
        )
    result.__post_init__()
    return result


@dataclass(frozen=True, slots=True)
class ConditionalDirectLaunchV1:
    result: ConditionalDirectGroundResultV1
    child_process_id: int
    parent_process_id: int
    fresh_process_attested: bool
    parent_process_distinct: bool
    isolated_interpreter: bool
    no_user_site: bool
    bytecode_disabled: bool
    accepted_input_roles: tuple[str, ...]
    process_launch_count: int

    def __post_init__(self) -> None:
        if type(self.result) is not ConditionalDirectGroundResultV1:
            raise ConditionalDirectGroundInvariantViolation(
                "direct launch rejects copied result"
            )
        _integer(self.child_process_id, "child process ID", 1)
        _integer(self.parent_process_id, "parent process ID", 1)
        for field in (
            "fresh_process_attested",
            "parent_process_distinct",
            "isolated_interpreter",
            "no_user_site",
            "bytecode_disabled",
        ):
            _boolean(getattr(self, field), field)
        _integer(self.process_launch_count, "process launch count")
        if (
            self.child_process_id == self.parent_process_id
            or self.fresh_process_attested is not True
            or self.parent_process_distinct is not True
            or self.isolated_interpreter is not True
            or self.no_user_site is not True
            or self.bytecode_disabled is not True
            or self.accepted_input_roles
            != (
                "QUERY_INDEX",
                "OCCURRENCE_INDEX",
                "EXPECTED_QUERY_ID",
                "EXPECTED_OCCURRENCE_ID",
            )
            or self.process_launch_count != 1
            or self.result.native_trace.process_launches != 1
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "fresh conditional-direct process attestation changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h2_conditional_direct_launch.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "result": self.result.to_document(),
            "child_process_id": self.child_process_id,
            "parent_process_id": self.parent_process_id,
            "fresh_process_attested": self.fresh_process_attested,
            "parent_process_distinct": self.parent_process_distinct,
            "isolated_interpreter": self.isolated_interpreter,
            "no_user_site": self.no_user_site,
            "bytecode_disabled": self.bytecode_disabled,
            "accepted_input_roles": list(self.accepted_input_roles),
            "process_launch_count": self.process_launch_count,
        }

    @property
    def launch_id(self) -> str:
        return _content_id("launch", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "launch_id": self.launch_id}


def parse_conditional_direct_launch_document_v1(
    document: Any,
) -> ConditionalDirectLaunchV1:
    fields = {
        "schema",
        "schema_version",
        "profile_key",
        "result",
        "child_process_id",
        "parent_process_id",
        "fresh_process_attested",
        "parent_process_distinct",
        "isolated_interpreter",
        "no_user_site",
        "bytecode_disabled",
        "accepted_input_roles",
        "process_launch_count",
        "launch_id",
    }
    record = _exact_mapping(document, fields, "conditional-direct launch")
    if (
        record["schema"] != "acfqp.h2_conditional_direct_launch.v1"
        or record["schema_version"] != SCHEMA_VERSION
        or record["profile_key"] != PROFILE_KEY
        or type(record["accepted_input_roles"]) is not list
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct launch schema/profile changed"
        )
    result = ConditionalDirectLaunchV1(
        parse_conditional_direct_ground_result_document_v1(record["result"]),
        record["child_process_id"],
        record["parent_process_id"],
        record["fresh_process_attested"],
        record["parent_process_distinct"],
        record["isolated_interpreter"],
        record["no_user_site"],
        record["bytecode_disabled"],
        tuple(record["accepted_input_roles"]),
        record["process_launch_count"],
    )
    if record["launch_id"] != result.launch_id:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct launch content ID mismatch"
        )
    return result


def require_conditional_direct_launch_v1(
    launch: ConditionalDirectLaunchV1,
) -> ConditionalDirectLaunchV1:
    if type(launch) is not ConditionalDirectLaunchV1:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct launch rejects substitutions"
        )
    launch.__post_init__()
    require_conditional_direct_ground_result_v1(launch.result)
    return launch


def _registered_query_for_indices(
    query_index: int,
    occurrence_index: int,
    expected_query_id: str,
    expected_occurrence_id: str,
) -> tuple[H2QueryFamilyQueryV1, H2QueryFamilyOccurrenceV1]:
    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_protocol_v1(protocol)
    _integer(query_index, "query index", 1)
    _integer(occurrence_index, "occurrence index", 1)
    _cid(expected_query_id, "expected query")
    _cid(expected_occurrence_id, "expected occurrence")
    try:
        query = protocol.query(query_index)
        occurrence = registered_h2_query_family_occurrence_v1(
            occurrence_index
        )
    except (IndexError, AttributeError, ValueError) as error:
        raise ConditionalDirectGroundInvariantViolation(
            "query/occurrence index lies outside the preregistration"
        ) from error
    require_registered_h2_query_family_query_v1(
        query, protocol, query_index
    )
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence_index
    )
    if (
        occurrence.query_index != query_index
        or occurrence.query_id != query.query_id
        or query.query_id != expected_query_id
        or occurrence.occurrence_id != expected_occurrence_id
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "query/occurrence identity does not match the preregistration"
        )
    return query, occurrence


def _execute_conditional_direct_ground_v1(
    query: H2QueryFamilyQueryV1,
    occurrence: H2QueryFamilyOccurrenceV1,
    parent_process_id: int,
) -> ConditionalDirectGroundResultV1:
    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_protocol_v1(protocol)
    require_registered_h2_query_family_query_v1(
        query, protocol, query.query_index
    )
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence.occurrence_index
    )
    _integer(parent_process_id, "parent process ID", 1)
    if os.getpid() == parent_process_id:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct execution is not a fresh process"
        )

    recorder = _ConditionalDirectNativeRecorderV1()
    recorder.record("process_launches")
    kernel = _literal_kernel_v1()
    _assert_offline_base()
    x1 = LMBState(48, (0, 2), LMBStatus.ACTIVE)
    guard = _ConditionalDirectSingleUseMGuardV1(recorder)
    actions = guard.actions(kernel, x1)
    outcomes = guard.step_m(kernel, x1, LMBAction(0))
    guard.close()
    if len(outcomes) != 1:
        raise ConditionalDirectGroundInvariantViolation(
            "registered M transition is not deterministic"
        )
    outcome = outcomes[0]
    m_reward = sum(
        value
        for name, value in outcome.reward_features
        if name == "match"
    )
    if (
        outcome.probability != 1
        or outcome.next_state
        != LMBState(49, (0, 0), LMBStatus.ACTIVE)
        or m_reward != 1
        or outcome.failure is not False
        or outcome.terminal is not False
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "registered conditional-online M row changed"
        )
    recorder.record("online_rows_acquired")

    recorder.record("offline_rows_consumed")
    n_evaluations_list: list[ConditionalDirectPolicyEvaluationV1] = []
    for policy_index, (
        name,
        state_key,
        tile,
        reward,
        failure,
        terminal,
    ) in enumerate(_OFFLINE_ROWS[1:], start=2):
        if state_key != "x1" or terminal is not False:
            raise ConditionalDirectGroundInvariantViolation(
                "registered offline N policy base changed"
            )
        recorder.record("offline_rows_consumed")
        evaluation = ConditionalDirectPolicyEvaluationV1(
            policy_index,
            f"A0A0_{name}",
            name,
            tile,
            reward,
            Fraction(int(failure)),
            False,
        )
        recorder.record("policy_evaluations")
        n_evaluations_list.append(evaluation)
    n_evaluations = tuple(n_evaluations_list)
    if len(n_evaluations) != 3:
        raise ConditionalDirectGroundInvariantViolation(
            "registered offline N policy base changed"
        )
    m_evaluation = ConditionalDirectPolicyEvaluationV1(
        1, "A0A1", "M", 0, m_reward, Fraction(0), True
    )
    recorder.record("policy_evaluations")
    evaluations = (
        m_evaluation,
        *n_evaluations,
    )
    recorder.record("optimizer_calls")
    selected = max(
        evaluations,
        key=lambda item: (
            item.reward,
            -item.failure_probability,
            -item.policy_index,
        ),
    )
    unrestricted = max(item.reward for item in evaluations)
    normalized_regret = (unrestricted - selected.reward) / Fraction(4)
    regret_passed = normalized_regret <= query.normalized_regret_tolerance
    risk_passed = selected.failure_probability <= query.risk_tolerance
    if selected.downstream_row != "M" or not regret_passed or not risk_passed:
        raise ConditionalDirectGroundInvariantViolation(
            "registered direct optimum/certificate changed"
        )
    native_trace = recorder.freeze()
    return ConditionalDirectGroundResultV1(
        protocol.protocol_id,
        query.query_id,
        occurrence.occurrence_id,
        query.query_index,
        occurrence.occurrence_index,
        conditional_direct_structural_id_v1(),
        conditional_direct_offline_base_id_v1(),
        tuple(action.tile for action in actions),
        evaluations,
        selected.policy_code,
        selected.downstream_row,
        selected.reward,
        selected.failure_probability,
        unrestricted,
        Fraction(4),
        normalized_regret,
        query.normalized_regret_tolerance,
        query.risk_tolerance,
        regret_passed,
        risk_passed,
        True,
        native_trace,
    )


def _worker_environment() -> dict[str, str]:
    environment = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
    }
    for name in ("LANG", "LC_ALL", "TZ"):
        value = os.environ.get(name)
        if value is not None:
            environment[name] = value
    return environment


def _read_canonical_regular(path: Path) -> bytes:
    try:
        if not path.is_file() or path.is_symlink():
            raise OSError("not a regular file")
        payload = path.read_bytes()
    except OSError as error:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct worker output is unreadable"
        ) from error
    try:
        document = loads_canonical_json(payload)
        if canonical_json_bytes(document) != payload:
            raise ValueError("not canonical bytes")
    except (TypeError, ValueError) as error:
        raise ConditionalDirectGroundInvariantViolation(
            "conditional-direct worker output is not canonical JSON"
        ) from error
    return payload


def _atomic_write_fresh(path: Path, payload: bytes) -> None:
    if not path.parent.is_dir() or path.exists():
        raise ConditionalDirectGroundInvariantViolation(
            "worker output target must be fresh"
        )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise ConditionalDirectGroundInvariantViolation(
            "worker could not commit its canonical output"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def run_h2_conditional_direct_ground_fresh_worker_v1(
    query: H2QueryFamilyQueryV1,
    occurrence: H2QueryFamilyOccurrenceV1,
) -> ConditionalDirectLaunchV1:
    """Launch one source-blind conditional-online comparator occurrence."""

    protocol = registered_h2_query_family_protocol_v1()
    require_registered_h2_query_family_protocol_v1(protocol)
    if type(query) is not H2QueryFamilyQueryV1:
        raise ConditionalDirectGroundInvariantViolation(
            "direct comparator requires the exact registered query type"
        )
    if type(occurrence) is not H2QueryFamilyOccurrenceV1:
        raise ConditionalDirectGroundInvariantViolation(
            "direct comparator requires the exact registered occurrence type"
        )
    require_registered_h2_query_family_query_v1(
        query, protocol, query.query_index
    )
    require_registered_h2_query_family_occurrence_v1(
        occurrence, protocol, occurrence.occurrence_index
    )
    if (
        occurrence.query_index != query.query_index
        or occurrence.query_id != query.query_id
    ):
        raise ConditionalDirectGroundInvariantViolation(
            "direct query and occurrence do not match"
        )

    source_root = Path(__file__).resolve().parents[1]
    bootstrap = (
        "import runpy,sys;"
        f"sys.path.insert(0,{str(source_root)!r});"
        "runpy.run_module("
        "'acfqp.h2_conditional_direct_ground_v1',run_name='__main__')"
    )
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v0056-direct-"
    ) as directory:
        output = Path(directory) / "direct-result.json"
        command = (
            sys.executable,
            "-I",
            "-s",
            "-B",
            "-c",
            bootstrap,
            "--worker",
            "--query-index",
            str(query.query_index),
            "--occurrence-index",
            str(occurrence.occurrence_index),
            "--expected-query-id",
            query.query_id,
            "--expected-occurrence-id",
            occurrence.occurrence_id,
            "--parent-process-id",
            str(os.getpid()),
            "--output",
            str(output),
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
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct worker timed out"
            ) from error
        if process.returncode != 0:
            diagnostic = stderr.decode("utf-8", errors="replace")[-2000:]
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct worker failed with code "
                f"{process.returncode}: {diagnostic}"
            )
        if stdout:
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct worker emitted unexpected stdout"
            )
        payload = _read_canonical_regular(output)
        envelope = _exact_mapping(
            loads_canonical_json(payload),
            {
                "schema",
                "schema_version",
                "profile_key",
                "child_process_id",
                "parent_process_id",
                "fresh_process_attested",
                "parent_process_distinct",
                "isolated_interpreter",
                "no_user_site",
                "bytecode_disabled",
                "accepted_input_roles",
                "result",
            },
            "conditional-direct worker envelope",
        )
        if (
            envelope["schema"]
            != "acfqp.h2_conditional_direct_worker_envelope.v1"
            or envelope["schema_version"] != SCHEMA_VERSION
            or envelope["profile_key"] != PROFILE_KEY
            or envelope["child_process_id"] != process.pid
            or envelope["parent_process_id"] != os.getpid()
            or envelope["fresh_process_attested"] is not True
            or envelope["parent_process_distinct"] is not True
            or envelope["isolated_interpreter"] is not True
            or envelope["no_user_site"] is not True
            or envelope["bytecode_disabled"] is not True
            or envelope["accepted_input_roles"]
            != [
                "QUERY_INDEX",
                "OCCURRENCE_INDEX",
                "EXPECTED_QUERY_ID",
                "EXPECTED_OCCURRENCE_ID",
            ]
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct worker OS/isolation envelope changed"
            )
        result = parse_conditional_direct_ground_result_document_v1(
            envelope["result"]
        )
        if (
            result.query_id != query.query_id
            or result.occurrence_id != occurrence.occurrence_id
            or result.query_index != query.query_index
            or result.occurrence_index != occurrence.occurrence_index
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "conditional-direct worker result context changed"
            )
        launch = ConditionalDirectLaunchV1(
            result,
            envelope["child_process_id"],
            envelope["parent_process_id"],
            envelope["fresh_process_attested"],
            envelope["parent_process_distinct"],
            envelope["isolated_interpreter"],
            envelope["no_user_site"],
            envelope["bytecode_disabled"],
            tuple(envelope["accepted_input_roles"]),
            1,
        )
        return require_conditional_direct_launch_v1(launch)


def _worker_cli(arguments: argparse.Namespace) -> int:
    try:
        if (
            sys.flags.isolated != 1
            or sys.flags.no_user_site != 1
            or sys.flags.dont_write_bytecode != 1
        ):
            raise ConditionalDirectGroundInvariantViolation(
                "worker interpreter isolation flags changed"
            )
        query, occurrence = _registered_query_for_indices(
            arguments.query_index,
            arguments.occurrence_index,
            arguments.expected_query_id,
            arguments.expected_occurrence_id,
        )
        result = _execute_conditional_direct_ground_v1(
            query,
            occurrence,
            arguments.parent_process_id,
        )
        output = Path(arguments.output)
        envelope = {
            "schema": "acfqp.h2_conditional_direct_worker_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "child_process_id": os.getpid(),
            "parent_process_id": arguments.parent_process_id,
            "fresh_process_attested": True,
            "parent_process_distinct": os.getpid()
            != arguments.parent_process_id,
            "isolated_interpreter": sys.flags.isolated == 1,
            "no_user_site": sys.flags.no_user_site == 1,
            "bytecode_disabled": sys.flags.dont_write_bytecode == 1,
            "accepted_input_roles": [
                "QUERY_INDEX",
                "OCCURRENCE_INDEX",
                "EXPECTED_QUERY_ID",
                "EXPECTED_OCCURRENCE_ID",
            ],
            "result": result.to_document(),
        }
        _atomic_write_fresh(output, canonical_json_bytes(envelope))
        return 0
    except Exception as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


def _main(argv: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="acfqp-h2-conditional-direct-ground-v1"
    )
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--query-index", type=int)
    parser.add_argument("--occurrence-index", type=int)
    parser.add_argument("--expected-query-id")
    parser.add_argument("--expected-occurrence-id")
    parser.add_argument("--parent-process-id", type=int)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    if (
        arguments.worker is not True
        or type(arguments.query_index) is not int
        or type(arguments.occurrence_index) is not int
        or type(arguments.expected_query_id) is not str
        or type(arguments.expected_occurrence_id) is not str
        or type(arguments.parent_process_id) is not int
        or type(arguments.output) is not str
    ):
        parser.error("the module is an internal fresh-process worker")
    return _worker_cli(arguments)


__all__ = [
    "CONTRACT_VERSION",
    "ConditionalDirectGroundInvariantViolation",
    "ConditionalDirectGroundResultV1",
    "ConditionalDirectLaunchV1",
    "ConditionalDirectNativeTraceV1",
    "ConditionalDirectPolicyEvaluationV1",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "SUCCESS_STATUS",
    "conditional_direct_offline_base_document_v1",
    "conditional_direct_offline_base_id_v1",
    "conditional_direct_structural_id_v1",
    "parse_conditional_direct_ground_result_document_v1",
    "parse_conditional_direct_launch_document_v1",
    "parse_conditional_direct_native_trace_document_v1",
    "parse_conditional_direct_policy_evaluation_document_v1",
    "require_conditional_direct_ground_result_v1",
    "require_conditional_direct_launch_v1",
    "run_h2_conditional_direct_ground_fresh_worker_v1",
]


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(_main())
