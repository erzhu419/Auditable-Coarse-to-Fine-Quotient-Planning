from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8 as verifier
from acfqp import construction_k7_domain_registry_extension_v180r8 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
HELPER = Path(__file__).with_name("_cached_exact_v180r8_subprocess.py")
VERIFIER_SOURCE = (
    ROOT
    / "src"
    / "acfqp"
    / "construction_k7_cached_exact_infeasibility_production_terminal_independent_verifier_v180r8.py"
)


@pytest.fixture(scope="module")
def terminal_bytes(tmp_path_factory: pytest.TempPathFactory) -> bytes:
    root = tmp_path_factory.mktemp("v180r8-independent") / "producer"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(
        [sys.executable, str(HELPER), str(root)],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return (root / "TERMINAL.json").read_bytes()


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
