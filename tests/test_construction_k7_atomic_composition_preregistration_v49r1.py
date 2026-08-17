from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_atomic_composition_preregistration_v49r1 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v49r1_is_fresh_outcome_free_successor_to_preserved_failure() -> None:
    frozen = pre.freeze_atomic_composition_preregistration_v49r1()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_atomic_composition_preregistration_v49r1(frozen) is frozen
    document = frozen.to_document()
    assert document["frozen_predecessor"]["v49_failure_id"] == pre.V49_FAILURE_ID
    assert document["frozen_predecessor"]["failed_predecessor_preserved_without_correction"] is True
    assert document["source_closure"]["frozen_before_any_v49r1_source_or_target_outcome"] is True
    assert document["fresh_v49r1_outcome_execution_performed"] is False
    assert document["recovery_correction"]["same_identity_rerun_forbidden"] is True


def test_v49r1_domains_seeds_and_claim_locks_are_fresh() -> None:
    document = pre.freeze_atomic_composition_preregistration_v49r1().to_document()
    assert len(pre.FUTURE_DOMAINS) == len(set(pre.FUTURE_DOMAINS.values())) == 13
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    assert set(pre.SOURCE_SEEDS).isdisjoint({491101, 491102, 491103})
    assert set(pre.TARGET_SEEDS).isdisjoint(range(491301, 491313))
    assert document["generic_atomic_search"]["specialized_discovery_pattern_count"] == 0
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


def test_v49r1_preregistration_imports_no_environment_kernel() -> None:
    tree = ast.parse(Path(pre.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("acfqp.domains") for name in imported)

