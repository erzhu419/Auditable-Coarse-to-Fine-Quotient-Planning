"""Isolated Phase-II Research Package (`quotient_phase2`):
Decision-Functional Certification (`M2.0–M2.1`) importing frozen `green_response` strictly read-only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

from green_response.core import compute_source_manifest as compute_phase1_source_manifest

EXPECTED_FROZEN_PHASE1_PY_SHA256 = "271ac8df9caaa8af8aaa5af9d35d76578632b554d5071fe8fe74065ca0dc0c2d"


def verify_phase1_readonly_freeze() -> dict:
    """Asserts that `green_response/*.py` remains byte-for-byte identical to frozen commit `a26c116`."""
    p1 = compute_phase1_source_manifest()
    actual = p1["package_py_sha256"]
    if actual != EXPECTED_FROZEN_PHASE1_PY_SHA256:
        raise RuntimeError(
            f"Frozen Phase-I package_py_sha256 mismatch: expected {EXPECTED_FROZEN_PHASE1_PY_SHA256}, got {actual}"
        )
    return p1


def compute_phase2_manifest() -> dict:
    """Computes SHA-256 manifest of `quotient_phase2/*.py` alongside verified read-only Phase-I anchor."""
    p1 = verify_phase1_readonly_freeze()
    pkg_dir = Path(__file__).resolve().parent
    per_file: Dict[str, str] = {}
    agg = hashlib.sha256()
    for py_path in sorted(pkg_dir.glob("*.py")):
        raw = py_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        per_file[py_path.name] = digest
        agg.update(f"{py_path.name}:{digest}\n".encode("utf-8"))
    return {
        "phase2_package_py_sha256": agg.hexdigest(),
        "phase2_per_file_sha256": per_file,
        "frozen_phase1_package_py_sha256": p1["package_py_sha256"],
        "frozen_phase1_verified_intact": True,
    }
