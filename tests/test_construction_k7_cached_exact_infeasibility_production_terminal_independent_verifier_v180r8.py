from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8 as verifier
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
RETAINED_TERMINAL = (
    ROOT / ".tmp" / "v180r8-cached-exact-production" / "TERMINAL.json"
)
VERIFIER_SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8.py"
)


@pytest.fixture(scope="module")
def terminal_bytes() -> bytes:
    if not RETAINED_TERMINAL.is_file():
        pytest.skip("retained V180r8 production terminal is absent")
    raw = RETAINED_TERMINAL.read_bytes()
    assert len(raw) == verifier.EXPECTED_TERMINAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_TERMINAL_SHA256
    return raw


def test_v180r8_verifier_reconstructs_the_complete_terminal(
    terminal_bytes: bytes,
) -> None:
    result = verifier.verify_cached_exact_terminal_independently_v180r8(
        terminal_bytes
    )
    assert result["fresh_single_path_verified"] is True
    assert result["all_ten_paths_verified"] is False
    assert result["v9_counter_record_count"] == 269
    assert result["shared_resource_receipt_count"] == 9
    assert result["source_proof_replayed_without_v180r8_producer_import"] is True
    assert result["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert result["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert result["official_execution_allowed"] is False
    verification_bytes = canonical_json_bytes(result)
    assert result["verification_id"] == verifier.EXPECTED_VERIFICATION_ID
    assert len(verification_bytes) == verifier.EXPECTED_VERIFICATION_BYTE_COUNT
    assert hashlib.sha256(verification_bytes).hexdigest() == (
        verifier.EXPECTED_VERIFICATION_SHA256
    )


def test_v180r8_verifier_rejects_a_fully_rehashed_claim_flip(
    terminal_bytes: bytes,
) -> None:
    document = loads_canonical_json(terminal_bytes)
    assert type(document) is dict
    document["ground_solver_called_in_online_window"] = True
    payload = dict(document)
    payload.pop("production_terminal_bundle_id")
    document["production_terminal_bundle_id"] = domains.extension_content_id_v180r8(
        domains.CONSTRUCTION_K7_CACHED_EXECUTION_TERMINAL_V180R8_DOMAIN,
        payload,
    )
    forged = canonical_json_bytes(document)
    assert hashlib.sha256(forged).hexdigest() != hashlib.sha256(terminal_bytes).hexdigest()
    with pytest.raises(Exception):
        verifier.verify_cached_exact_terminal_independently_v180r8(forged)


def test_v180r8_verifier_import_surface_is_producer_free() -> None:
    source = VERIFIER_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
            imports.extend(alias.name for alias in node.names)
    assert not any("terminal_finalizer_v180r8" in item for item in imports)
    assert "run_cached_exact_infeasibility_production_occurrence_v180r8" not in source
