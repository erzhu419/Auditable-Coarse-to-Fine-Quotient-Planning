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
EXPECTED_PHASE2_PY_SHA256 = "3dcf3834cc70af209c83afd3c3a494fb7dc0d0cddd17b1e2d1250ff8d65dc23c"


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
