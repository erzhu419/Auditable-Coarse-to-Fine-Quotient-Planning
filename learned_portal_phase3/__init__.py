"""Phase-III (`learned_portal_phase3`):
PAC-Certified Spectral-Portal Quotient Learning (SPQL) from Unknown-Dynamics Exploration Trajectories.

Strictly isolated from frozen Phase-I (`green_response/`) and frozen Phase-II SISC (`quotient_phase2/`).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

from quotient_phase2 import compute_phase2_manifest


EXPECTED_PHASE1_PY_SHA256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"
EXPECTED_PHASE2_PY_SHA256 = "e6ea565b8a4e87e7298c93bf01351ee5c2787fed3a91fc6a7caebcfe4b44e9c6"
FROZEN_P3_V1_EXPLORATORY_JSON_SHA256 = "0e2c76ea204ba7ad66341d243ee0d992e23158d16573a430d0ab602d6f98e161"


def verify_phase3_v1_archive_untouched() -> Dict[str, object]:
    """Verify exploratory Phase-III v1 benchmark archive remains byte-identical (`R333-D03`)."""
    p3_dir = Path(__file__).resolve().parent
    fp = p3_dir / "p3_neurips_benchmark_results.json"
    if not fp.exists():
        raise RuntimeError(f"Missing frozen Phase-III v1 exploratory archive: {fp}")
    actual = hashlib.sha256(fp.read_bytes()).hexdigest()
    if actual != FROZEN_P3_V1_EXPLORATORY_JSON_SHA256:
        raise RuntimeError(
            f"Frozen p3_neurips_benchmark_results.json modified! Expected {FROZEN_P3_V1_EXPLORATORY_JSON_SHA256}, got {actual}"
        )
    return {"file": fp.name, "sha256": actual, "verified_untouched": True}


def verify_phase1_and_phase2_untouched() -> Dict[str, str]:
    m2 = compute_phase2_manifest()
    p1_sha = str(m2["frozen_phase1_package_py_sha256"])
    p2_sha = str(m2["phase2_package_py_sha256"])
    if p1_sha != EXPECTED_PHASE1_PY_SHA256:
        raise RuntimeError(f"Phase-I green_response modified: {p1_sha} != {EXPECTED_PHASE1_PY_SHA256}")
    if p2_sha != EXPECTED_PHASE2_PY_SHA256:
        raise RuntimeError(f"Phase-II quotient_phase2 modified: {p2_sha} != {EXPECTED_PHASE2_PY_SHA256}")
    return {"phase1_py_sha256": p1_sha, "phase2_py_sha256": p2_sha}


def compute_phase3_manifest() -> Dict[str, object]:
    p3_dir = Path(__file__).resolve().parent
    per_file: Dict[str, str] = {}
    agg = hashlib.sha256()
    for py_path in sorted(p3_dir.glob("*.py")):
        digest = hashlib.sha256(py_path.read_bytes()).hexdigest()
        per_file[py_path.name] = digest
        agg.update(f"{py_path.name}:{digest}\n".encode("utf-8"))
    return {
        "phase3_package_py_sha256": agg.hexdigest(),
        "phase3_per_file_sha256": per_file,
        **verify_phase1_and_phase2_untouched(),
    }
