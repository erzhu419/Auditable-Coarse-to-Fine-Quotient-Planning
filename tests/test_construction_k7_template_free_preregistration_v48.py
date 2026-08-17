from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_template_free_preregistration_v48 as pre


def test_v48_preregistration_is_frozen_outcome_free_and_template_free() -> None:
    frozen = pre.freeze_template_free_preregistration_v48()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_template_free_preregistration_v48(frozen) is frozen
    document = frozen.to_document()
    assert document["source_closure"]["frozen_before_any_v48_source_or_target_outcome"] is True
    assert document["typed_grammar"]["whole_program_template_count"] == 0
    assert document["typed_grammar"]["historical_complete_template_opcodes_available"] == []
    assert document["outcome_fields_present"] is False
    assert document["fresh_v48_outcome_execution_performed"] is False


def test_v48_registers_three_fresh_families_and_real_recovery_contract() -> None:
    document = pre.freeze_template_free_preregistration_v48().to_document()
    assert set(document["fresh_workloads"]) == {
        "D00",
        "D01",
        "D02",
        "maximum_source_labels_per_family",
        "all_source_and_target_seed_identities_fresh_after_v47r1",
    }
    assert document["fresh_workloads"]["D02"]["held_out_mode_absent_from_all_source_outcomes"] is True
    assert document["protocol"]["held_out_D02_mode_requires_failed_certificate_before_query"] is True
    assert document["protocol"]["immutable_overlay_reused_across_later_D02_occurrences"] is True
    assert document["protocol"]["planner_consumes_compiled_world_model_only"] is True


def test_v48_source_closure_and_claim_locks_are_exact() -> None:
    document = pre.freeze_template_free_preregistration_v48().to_document()
    for row in document["source_closure"]["source_facts"]:
        raw = (pre.SOURCE_ROOT / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    assert document["broad_world_model_synthesis_claimed"] is False
    assert document["broad_cross_domain_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_v48_preregistration_imports_no_environment_kernel() -> None:
    tree = ast.parse(Path(pre.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("acfqp.domains") for name in imported)

