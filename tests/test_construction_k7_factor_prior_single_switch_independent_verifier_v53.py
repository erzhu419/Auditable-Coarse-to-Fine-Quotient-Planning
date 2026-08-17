from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_factor_prior_single_switch_independent_verifier_v53 as verifier
from acfqp.phase3e_ids import loads_canonical_json


def test_v53_independent_verifier_has_no_v53_producer_or_core_import() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any("factor_prior_single_switch_campaign_v53" in name for name in imported)
    assert not any("factor_prior_single_switch_core_v53" in name for name in imported)


def test_v53_frozen_verification_identity_is_pinned() -> None:
    assert verifier.EXPECTED_CAMPAIGN_ID == "f99f19fb95af81fe25a8a3229bd0dbc35187e1e3cf9a9f97b824dbc31993d169"
    assert verifier.EXPECTED_CAMPAIGN_BYTE_COUNT == 33_058_905
    assert verifier.EXPECTED_CAMPAIGN_SHA256 == "6a435b190a2f5fefb4ede21b3483f90dfa199c93c555a6c6faf30aa3f5990234"
    assert verifier.VERIFICATION_ID == "13c4e805fdf7457033ca99b9422aa374cef108528aa230514c16bdf6347c9372"
    assert verifier.EXPECTED_CANONICAL_BYTE_COUNT == 1_892
    assert verifier.EXPECTED_CANONICAL_SHA256 == "68f6d2dee145b4d0513223fc40df0b72240fd95e70014d261943ae934e6d14bc"


@pytest.fixture(scope="module")
def full_verification_bytes():
    if os.environ.get("ACFQP_RUN_REAL_V53") != "1":
        pytest.skip("set ACFQP_RUN_REAL_V53=1 for the retained 1024-occurrence replay")
    return verifier.freeze_factor_prior_single_switch_verification_v53()


def test_v53_full_producer_free_replay(full_verification_bytes) -> None:
    raw = full_verification_bytes
    document = loads_canonical_json(raw)
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert document["factor_prior_on_target_labels"] == 4_604
    assert document["factor_prior_off_target_labels"] == 5_120
    assert document["incremental_target_label_reduction"] == 516
    assert document["lifetime_label_reduction"] == 146
    assert document["diagnostic_break_even_occurrence_count"] == 720
    assert document["on_steps"] == document["off_steps"] == 114
    assert document["on_certificates"] == document["off_certificates"] == 8
    assert document["producer_or_campaign_core_module_imported"] is False
    assert document["scientific_projection_independently_reconstructed"] is True
    assert document["full_campaign_presentation_bytes_reconstructed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v53_verification_rejects_noncanonical_or_changed_bytes(
    full_verification_bytes,
) -> None:
    with pytest.raises(ValueError):
        verifier.verify_factor_prior_single_switch_verification_bytes_v53(
            full_verification_bytes + b" "
        )
