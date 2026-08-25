"""Freeze the unexecuted V180r12r1 aggregation as a stale predecessor.

The V180r12r1 authorization was valid only for its then-pinned source set.  It
was never executed, but two of those source roles were subsequently replaced
by independently frozen successors (V180r10r1 and V180r7r1).  This additive
record preserves V180r12, its failure, and V180r12r1 byte-for-byte while making
the old authorization permanently ineligible for execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NoReturn

from acfqp import construction_k7_domain_registry_extension_v180r12r2 as domains
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r1
    as predecessor_authorization,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_failure_v180r12
    as predecessor_failure,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12
    as predecessor_protocol,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12r1
    as stale_protocol,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_STALE_PREDECESSOR_ID = "3d764ef065567383bddc0d4ed2e9550ef4234ba1eabbd9f17c4746c45cde29c2"
EXPECTED_CANONICAL_BYTE_COUNT = 2442
EXPECTED_CANONICAL_SHA256 = "451ce6a8eb99db5666b5272c222feda95a7e028170dbbdb68f42ce70d13c4732"

PRESERVED_V180R12_PROTOCOL_ID = (
    "f0b5f52205b6f4eeb671bb86c5d048f72df14100bbabee7b22ce4619c66ccd15"
)
PRESERVED_V180R12_FAILURE_ID = (
    "b8348c51c19db9238281a9a59e66bba911c9c9756e80c04a9cb3111e8515a604"
)
PRESERVED_V180R12R1_PROTOCOL_ID = (
    "54816ae5405c50eba7294d59da21c4b70e7486ccdf89956f3c5b9fcf4c6219fe"
)
PRESERVED_V180R12R1_AUTHORIZATION_ID = (
    "cf1158297e790cfd5a794adbd2abc98819ff0f7ce736a4859a9795938ef1672f"
)
PRESERVED_V180R12R1_LOGICAL_OCCURRENCE_ID = (
    "8a2df3b6c5d43fc73e56b11dc937ed6d3c63df71de168911865624f9ec084610"
)

_PRESERVED_CANONICAL_FACTS = {
    "v180r12_protocol": {
        "content_id": PRESERVED_V180R12_PROTOCOL_ID,
        "byte_count": 5_033,
        "sha256": (
            "2c58ead754839c26631cb04b835ac496e774c11f14078e81edf687050fc09f2f"
        ),
    },
    "v180r12_failure": {
        "content_id": PRESERVED_V180R12_FAILURE_ID,
        "byte_count": 2_465,
        "sha256": (
            "7c74af102aa1d111a99ad43d3a8dd73192b059f2bc685bceeeac194ff8a2bbe5"
        ),
    },
    "v180r12r1_protocol": {
        "content_id": PRESERVED_V180R12R1_PROTOCOL_ID,
        "byte_count": 6_262,
        "sha256": (
            "414fc1100a6c6c04dc458f62b273cb870cd2099063eb2204ce8e496b69833bcc"
        ),
    },
    "v180r12r1_authorization": {
        "content_id": PRESERVED_V180R12R1_AUTHORIZATION_ID,
        "byte_count": 6_041,
        "sha256": (
            "11f89eb57dfdb7e3e480fae93cf195f5ef7a30ec43b1751e59bfc7d3e38b2f83"
        ),
    },
}

STALE_OUTPUT_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r1_ten_terminal_aggregation"
)


class TenTerminalAggregationStalePredecessorV180R12R2Error(ValueError):
    """The preserved predecessor or its unexecuted boundary changed."""


def _fail(message: str) -> NoReturn:
    raise TenTerminalAggregationStalePredecessorV180R12R2Error(message)


def _canonical_fact(raw: bytes, content_id: str) -> dict[str, Any]:
    return {
        "content_id": content_id,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _require_absent_symlink_free_target(root: Path, relative_path: str) -> None:
    relative = Path(relative_path)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        _fail("V180r12r1 output path escaped its frozen repository boundary")
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if not os.path.lexists(os.fspath(current)):
            continue
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail("V180r12r1 output ancestor is linked or non-directory")
    target = root / relative
    if os.path.lexists(os.fspath(target)):
        _fail("V180r12r1 stale output root has progress or a linked leaf")


def build_ten_terminal_aggregation_stale_predecessor_v180r12r2() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    v180r12 = predecessor_protocol.freeze_ten_terminal_aggregation_protocol_v180r12()
    v180r12_failure = (
        predecessor_failure.freeze_ten_terminal_aggregation_protocol_failure_v180r12()
    )
    v180r12r1 = stale_protocol.freeze_ten_terminal_aggregation_protocol_v180r12r1()
    v180r12r1_authorization = (
        predecessor_authorization.freeze_ten_terminal_aggregation_execution_authorization_v180r12r1()
    )
    actual_facts = {
        "v180r12_protocol": _canonical_fact(
            v180r12.canonical_bytes, v180r12.aggregation_protocol_id
        ),
        "v180r12_failure": _canonical_fact(
            v180r12_failure.canonical_bytes, v180r12_failure.failure_id
        ),
        "v180r12r1_protocol": _canonical_fact(
            v180r12r1.canonical_bytes, v180r12r1.aggregation_protocol_id
        ),
        "v180r12r1_authorization": _canonical_fact(
            v180r12r1_authorization.canonical_bytes,
            v180r12r1_authorization.authorization_id,
        ),
    }
    stale_authorization_document = v180r12r1_authorization.to_document()
    _require_absent_symlink_free_target(root, STALE_OUTPUT_ROOT_RELATIVE_PATH)
    if not (
        actual_facts == _PRESERVED_CANONICAL_FACTS
        and stale_authorization_document["logical_occurrence_id"]
        == PRESERVED_V180R12R1_LOGICAL_OCCURRENCE_ID
        and stale_authorization_document["aggregation_execution_started"] is False
        and stale_authorization_document[
            "same_authorization_rerun_after_progress_or_terminal_forbidden"
        ]
        is True
    ):
        _fail("V180r12/r12r1 preservation or unexecuted boundary changed")

    payload = {
        "schema": "acfqp.ten_terminal_aggregation_stale_predecessor.v180r12r2",
        "preserved_canonical_facts": actual_facts,
        "preserved_v180r12_protocol_id": PRESERVED_V180R12_PROTOCOL_ID,
        "preserved_v180r12_failure_id": PRESERVED_V180R12_FAILURE_ID,
        "preserved_v180r12r1_protocol_id": PRESERVED_V180R12R1_PROTOCOL_ID,
        "preserved_v180r12r1_authorization_id": (
            PRESERVED_V180R12R1_AUTHORIZATION_ID
        ),
        "preserved_v180r12r1_logical_occurrence_id": (
            PRESERVED_V180R12R1_LOGICAL_OCCURRENCE_ID
        ),
        "v180r12r1_status": "STALE_UNEXECUTED",
        "v180r12r1_output_root_relative_path": STALE_OUTPUT_ROOT_RELATIVE_PATH,
        "v180r12r1_output_root_present_at_stale_freeze": False,
        "v180r12r1_scientific_output_generated": False,
        "v180r12r1_authorization_execution_count": 0,
        "v180r12r1_same_authorization_execution_forbidden": True,
        "v180r12r1_same_logical_occurrence_reuse_forbidden": True,
        "stale_reason": (
            "PINNED_V180R10_AND_V180R7_SOURCES_SUPERSEDED_BY_"
            "INDEPENDENTLY_FROZEN_V180R10R1_AND_V180R7R1"
        ),
        "fresh_protocol_slot_nonce_and_logical_occurrence_required": True,
        "predecessors_retained_without_relabeling": True,
        "predecessor_outcome_reconstruction_performed": False,
        "v180r12r2_outcome_accessed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "outcome_free": True,
    }
    return {
        **payload,
        "stale_predecessor_id": domains.extension_content_id_v180r12r2(
            domains.CONSTRUCTION_K7_STALE_PREDECESSOR_V180R12R2_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class TenTerminalAggregationStalePredecessorV180R12R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    stale_predecessor_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("stale_predecessor_id") == self.stale_predecessor_id
        ):
            _fail("V180r12r2 stale-predecessor record is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document


@lru_cache(maxsize=1)
def freeze_ten_terminal_aggregation_stale_predecessor_v180r12r2() -> (
    TenTerminalAggregationStalePredecessorV180R12R2
):
    document = build_ten_terminal_aggregation_stale_predecessor_v180r12r2()
    raw = canonical_json_bytes(document)
    if EXPECTED_STALE_PREDECESSOR_ID != "0" * 64 and not (
        document["stale_predecessor_id"] == EXPECTED_STALE_PREDECESSOR_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        _fail("V180r12r2 stale-predecessor identity changed")
    return TenTerminalAggregationStalePredecessorV180R12R2(
        _ISSUER,
        raw,
        document["stale_predecessor_id"],
    )


__all__ = (
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_STALE_PREDECESSOR_ID",
    "PRESERVED_V180R12R1_AUTHORIZATION_ID",
    "PRESERVED_V180R12R1_LOGICAL_OCCURRENCE_ID",
    "PRESERVED_V180R12R1_PROTOCOL_ID",
    "PRESERVED_V180R12_FAILURE_ID",
    "PRESERVED_V180R12_PROTOCOL_ID",
    "STALE_OUTPUT_ROOT_RELATIVE_PATH",
    "TenTerminalAggregationStalePredecessorV180R12R2",
    "TenTerminalAggregationStalePredecessorV180R12R2Error",
    "build_ten_terminal_aggregation_stale_predecessor_v180r12r2",
    "freeze_ten_terminal_aggregation_stale_predecessor_v180r12r2",
)
