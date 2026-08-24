"""Freeze the successful V180r10r1 retained V36 finish-forward evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_v36_retained_recovery_authorization_v180r10r1 as authorization
from acfqp import construction_k7_v36_retained_recovery_independent_verifier_v180r10r1 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_TERMINAL_ID = "9f73d1e948ce31025188565fbb94cfb9d53281e8b2ef783e5251ec6b17b0c66c"
EXPECTED_TERMINAL_BYTE_COUNT = 3_134_599
EXPECTED_TERMINAL_SHA256 = "2f2bd742d11f2750d5be0a3e61614912bccf84258b36ab6b62cbe8b1617496b3"
EXPECTED_VERIFICATION_ID = "8946eb3158196b005f4a3ff92b22ce521378839ceeb969fec899a5776e8721ef"
EXPECTED_VERIFICATION_BYTE_COUNT = 1_553
EXPECTED_VERIFICATION_SHA256 = "e6c38d65dd0d7f2cfb5193dbf99b6d54c99e785f1081102925428c8338236501"


def verify_retained_v36_recovery_evidence_v180r10r1(root: Path) -> dict[str, Any]:
    terminal_path = root / "v180r10r1_v36_retained_terminal.json"
    verification_path = root / "v180r10r1_v36_retained_verification.json"
    failure_path = root / "v180r10r1_v36_retained_failure.json"
    if not terminal_path.is_file() or not verification_path.is_file() or failure_path.exists():
        raise ValueError("V180r10r1 retained output inventory changed")
    terminal_bytes = terminal_path.read_bytes()
    terminal = loads_canonical_json(terminal_bytes)
    if not (
        type(terminal) is dict
        and canonical_json_bytes(terminal) == terminal_bytes
        and terminal["v36_retained_terminal_id"] == EXPECTED_TERMINAL_ID
        and terminal["v36_retained_recovery_authorization_id"]
        == authorization.EXPECTED_AUTHORIZATION_ID
        and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
        and hashlib.sha256(terminal_bytes).hexdigest() == EXPECTED_TERMINAL_SHA256
        and terminal["retained_occurrence_receipt"][
            "source_operational_work_vector_count"
        ]
        == 15
        and terminal["retained_occurrence_receipt"]["source_counter_record_count"]
        == 15 * 269
        and terminal["scientific_occurrence_rerun_by_successor"] is False
        and terminal["post_failure_finish_forward_only"] is True
        and terminal["operational_lane_literal_repaired"] == "OPERATIONAL"
        and terminal["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and terminal["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and terminal["official_scalar_cost"] is None
        and terminal["official_N_break_even"] is None
        and terminal["official_execution_allowed"] is False
    ):
        raise ValueError("V180r10r1 frozen terminal identity or claim boundary changed")
    source_root = root / "v180r10_v36_resource_successor_output"
    replayed = verifier.verify_v36_retained_recovery_bytes_independently_v180r10r1(
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
        and replayed["v36_retained_terminal_id"] == EXPECTED_TERMINAL_ID
        and replayed[
            "v35_and_v36_campaigns_reconstructed_without_producer_import"
        ]
        is True
        and replayed["source_v36_semantics_replayed_producer_free"] is True
        and replayed["scientific_occurrence_rerun"] is False
        and replayed["single_terminal_path_verified"] is True
        and replayed["all_ten_paths_verified"] is False
        and replayed["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and replayed["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and replayed["official_execution_allowed"] is False
    ):
        raise ValueError("V180r10r1 frozen independent verification changed")
    return replayed


__all__ = (
    "EXPECTED_TERMINAL_ID",
    "EXPECTED_VERIFICATION_ID",
    "verify_retained_v36_recovery_evidence_v180r10r1",
)
