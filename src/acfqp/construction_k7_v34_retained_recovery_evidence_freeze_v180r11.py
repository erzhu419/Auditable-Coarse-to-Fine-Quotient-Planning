"""Freeze the successful V180r11 retained V34 finish-forward evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_v34_retained_recovery_authorization_v180r11 as authorization
from acfqp import construction_k7_v34_retained_recovery_independent_verifier_v180r11 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_TERMINAL_ID = "aaaed6c19b1c7061b409dfdd042a189b4e4ea94e269d1e7c0de6d748d0932f42"
EXPECTED_TERMINAL_BYTE_COUNT = 8_547_638
EXPECTED_TERMINAL_SHA256 = "b6d3e1e48bad2bcdf68594b87b801466479bf596e4758443014b067cf45659e4"
EXPECTED_VERIFICATION_ID = "caf0a523d3b7919d9a98460aab9faeed86eefd4dd6d7cc7bc28e9fc9dd4293c9"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_341
EXPECTED_VERIFICATION_SHA256 = "7080e808e8e03127e2ddea832bb093ba54430abfc1b5ff0e73e2c87e3fe9e5da"


def verify_retained_v34_recovery_evidence_v180r11(root: Path) -> dict[str, Any]:
    terminal_path = root / "v180r11_v34_retained_terminal.json"
    verification_path = root / "v180r11_v34_retained_verification.json"
    failure_path = root / "v180r11_v34_retained_failure.json"
    if not terminal_path.is_file() or not verification_path.is_file() or failure_path.exists():
        raise ValueError("V180r11 retained output inventory changed")
    terminal_bytes = terminal_path.read_bytes()
    terminal = loads_canonical_json(terminal_bytes)
    if not (
        type(terminal) is dict
        and canonical_json_bytes(terminal) == terminal_bytes
        and terminal["v34_retained_terminal_id"] == EXPECTED_TERMINAL_ID
        and terminal["v34_retained_recovery_authorization_id"]
        == authorization.EXPECTED_AUTHORIZATION_ID
        and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
        and hashlib.sha256(terminal_bytes).hexdigest() == EXPECTED_TERMINAL_SHA256
        and terminal["retained_occurrence_receipt"][
            "source_operational_work_vector_count"
        ]
        == 45
        and terminal["retained_occurrence_receipt"]["source_counter_record_count"]
        == 45 * 269
        and terminal["scientific_occurrence_rerun_by_successor"] is False
        and terminal["post_failure_finish_forward_only"] is True
        and terminal["operational_lane_literal_repaired"] == "OPERATIONAL"
        and terminal["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and terminal["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and terminal["official_execution_allowed"] is False
    ):
        raise ValueError("V180r11 frozen terminal identity or claim boundary changed")
    source_root = root / "v180r5_v34_production_output"
    replayed = verifier.verify_v34_retained_recovery_bytes_independently_v180r11(
        terminal_bytes,
        source_root,
        recovery_authorization_id=authorization.EXPECTED_AUTHORIZATION_ID,
    )
    replayed_bytes = canonical_json_bytes(replayed)
    retained_bytes = verification_path.read_bytes()
    retained = loads_canonical_json(retained_bytes)
    if not (
        type(retained) is dict
        and canonical_json_bytes(retained) == retained_bytes
        and retained_bytes == replayed_bytes
        and replayed["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(replayed_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(replayed_bytes).hexdigest()
        == EXPECTED_VERIFICATION_SHA256
        and replayed["v34_retained_terminal_id"] == EXPECTED_TERMINAL_ID
        and replayed["source_campaign_replayed_without_recovery_producer_import"]
        is True
        and replayed["scientific_occurrence_rerun"] is False
        and replayed["single_terminal_path_verified"] is True
        and replayed["all_ten_paths_verified"] is False
        and replayed["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and replayed["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and replayed["official_execution_allowed"] is False
    ):
        raise ValueError("V180r11 frozen independent verification changed")
    return replayed


__all__ = (
    "EXPECTED_TERMINAL_ID",
    "EXPECTED_VERIFICATION_ID",
    "verify_retained_v34_recovery_evidence_v180r11",
)
