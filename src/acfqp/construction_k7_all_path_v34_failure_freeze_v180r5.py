"""Exact retained V180r5 V34 failure and all immutable partial outputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_all_path_v34_execution_authorization_v180r5 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r5 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = "910898634f1885cac1c7cf445157e89c50789ef8be174bb8f8a44bb455bbf19c"
EXPECTED_CANONICAL_BYTE_COUNT = 616
EXPECTED_CANONICAL_SHA256 = "02aaa5ac42cd8aa904ff98112c8238b0b3ce749275146728c76b6e7f1a42c9a0"
EXPECTED_PARTIAL_OUTPUT_FILE_COUNT = 79
EXPECTED_PARTIAL_OUTPUT_TOTAL_BYTES = 27_559_492
EXPECTED_PARTIAL_INVENTORY_BYTE_COUNT = 12_668
EXPECTED_PARTIAL_INVENTORY_SHA256 = (
    "2c454a46ebf016b811a78548dd15321faee6a2567441ac58952f5a0619b62992"
)


@dataclass(frozen=True, slots=True)
class FrozenV34FailureV180r5:
    canonical_bytes: bytes
    failure_id: str
    partial_inventory: tuple[dict[str, Any], ...]

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V180r5 retained failure is not one document")
        return document


def _inventory(output_root: Path) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "relative_path": path.relative_to(output_root).as_posix(),
            "byte_count": len(raw := path.read_bytes()),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        for path in sorted(
            candidate for candidate in output_root.rglob("*") if candidate.is_file()
        )
    )


def load_frozen_v34_failure_v180r5() -> FrozenV34FailureV180r5:
    root = Path(__file__).resolve().parents[2]
    exact_root = root / ".tmp" / "exact-freeze"
    failure_path = exact_root / "v180r5_v34_production_failure.json"
    output_root = exact_root / "v180r5_v34_production_output"
    raw = failure_path.read_bytes()
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        raise ValueError("V180r5 retained failure is not one document")
    payload = dict(document)
    failure_id = payload.pop("failure_id", None)
    inventory = _inventory(output_root)
    inventory_bytes = canonical_json_bytes(list(inventory))
    if not (
        canonical_json_bytes(document) == raw
        and set(document)
        == {
            "schema",
            "v34_execution_authorization_id",
            "failure_type",
            "failure_message",
            "output_root_created",
            "retained_output_file_count",
            "same_authorization_rerun_forbidden",
            "success_claimed",
            "COUNTER_COMPLETENESS_GATE",
            "WORKLOAD_ECONOMICS_GATE",
            "official_execution_allowed",
            "failure_id",
        }
        and failure_id == EXPECTED_FAILURE_ID
        and failure_id
        == domains.extension_content_id_v180r5(
            domains.CONSTRUCTION_K7_V34_EXECUTION_FAILURE_V180R5_DOMAIN,
            payload,
        )
        and document["v34_execution_authorization_id"]
        == authorization.EXPECTED_AUTHORIZATION_ID
        and document["failure_type"]
        == "ConstructionK7AllPathProductionTerminalFinalizerV180r3Error"
        and document["failure_message"]
        == "V34 operational WorkVector denominator changed"
        and document["output_root_created"] is True
        and document["retained_output_file_count"]
        == EXPECTED_PARTIAL_OUTPUT_FILE_COUNT
        and document["same_authorization_rerun_forbidden"] is True
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_execution_allowed"] is False
        and len(inventory) == EXPECTED_PARTIAL_OUTPUT_FILE_COUNT
        and sum(row["byte_count"] for row in inventory)
        == EXPECTED_PARTIAL_OUTPUT_TOTAL_BYTES
        and len(inventory_bytes) == EXPECTED_PARTIAL_INVENTORY_BYTE_COUNT
        and hashlib.sha256(inventory_bytes).hexdigest()
        == EXPECTED_PARTIAL_INVENTORY_SHA256
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V180r5 retained V34 failure or partial outputs changed")
    return FrozenV34FailureV180r5(raw, failure_id, inventory)


__all__ = (
    "EXPECTED_FAILURE_ID",
    "EXPECTED_PARTIAL_INVENTORY_SHA256",
    "EXPECTED_PARTIAL_OUTPUT_FILE_COUNT",
    "load_frozen_v34_failure_v180r5",
)
