from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_atomic_composition_preregistration_v49 as pre


def test_v49_preregistration_is_outcome_free_and_generic() -> None:
    frozen = pre.freeze_atomic_composition_preregistration_v49()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_atomic_composition_preregistration_v49(frozen) is frozen
    document = frozen.to_document()
    grammar = document["generic_atomic_search"]
    assert grammar["whole_program_template_count"] == 0
    assert grammar["specialized_discovery_pattern_count"] == 0
    assert grammar["candidate_generation"] == "TYPED_BOTTOM_UP_ATOMIC_COMPOSITION"
    assert document["outcome_fields_present"] is False
    assert document["fresh_v49_outcome_execution_performed"] is False


def test_v49_registers_fresh_combination_and_recovery_protocol() -> None:
    document = pre.freeze_atomic_composition_preregistration_v49().to_document()
    workload = document["fresh_workload"]
    assert workload["target_requires_last_unseen_mode"] is True
    assert workload["held_out_mode_absent_from_all_source_outcomes"] is True
    assert workload["generation_witness_available_to_acquisition_or_synthesis"] is False
    assert document["protocol"]["local_ground_label_only_after_failed_certificate"] is True
    assert document["protocol"]["immutable_overlay_reused_across_later_occurrences"] is True
    assert document["protocol"]["support_probability_authority_claimed"] is False


def test_v49_source_closure_and_claim_locks_are_exact() -> None:
    document = pre.freeze_atomic_composition_preregistration_v49().to_document()
    for row in document["source_closure"]["source_facts"]:
        raw = (pre.SOURCE_ROOT / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    boundary = document["claim_boundary"]
    assert boundary["fresh_fourth_combination_domain_present"] is True
    assert boundary["fourth_unrelated_domain_authority_claimed"] is False
    assert boundary["open_ended_layout_discovery_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_v49_preregistration_imports_no_environment_kernel() -> None:
    tree = ast.parse(Path(pre.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("acfqp.domains") for name in imported)

