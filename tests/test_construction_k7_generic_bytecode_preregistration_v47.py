from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_generic_bytecode_preregistration_v47 as pre
from acfqp import phase3e_ids


def test_v47_preregistration_is_frozen_and_outcome_free() -> None:
    frozen = pre.freeze_generic_bytecode_preregistration_v47()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert pre.verify_generic_bytecode_preregistration_v47(frozen) is frozen
    document = frozen.to_document()
    assert document["outcome_fields_present"] is False
    assert document["raw_transition_archive_materialized"] is False
    assert document["program_selection_executed"] is False
    assert document["target_planning_or_execution_performed"] is False
    assert document["sample_tax_result_observed"] is False


def test_v47_registers_only_generic_typed_grammar() -> None:
    document = pre.freeze_generic_bytecode_preregistration_v47().to_document()
    grammar = document["finite_generic_meta_grammar"]
    assert grammar["domain_named_primitive_count"] == 0
    assert grammar["lmb_named_primitive_count"] == 0
    assert grammar["registered_template_opcodes"] == ["T00", "T01"]
    text = repr(grammar["opcodes"]).lower()
    assert "lmb" not in text
    assert "routing" not in text
    assert "tile" not in text
    assert "buffer" not in text
    interface = document["raw_interface"]
    assert interface["adapter_provided_abstract_state_present"] is False
    assert interface["kernel_transition_allowed_during_planning"] is False


def test_v47_fresh_workloads_controls_and_accounting_are_frozen() -> None:
    document = pre.freeze_generic_bytecode_preregistration_v47().to_document()
    assert document["lmb_workload"]["source_seeds"] == list(pre.LMB_SOURCE_SEEDS)
    assert document["lmb_workload"]["target_seeds"] == list(pre.LMB_TARGET_SEEDS)
    stochastic = document["stochastic_partial_workload"]
    assert stochastic["source_seeds"] == list(pre.ROUTING_SOURCE_SEEDS)
    assert stochastic["target_seeds"] == list(pre.ROUTING_TARGET_SEEDS)
    assert stochastic["exact_probability_authority_claimed"] is False
    assert document["strict_ood_control"]["prior_access_allowed"] is False
    axes = document["accounting_axes"]
    assert axes["labels_steps_compute_and_peak_may_not_be_collapsed"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_v47_source_closure_and_domain_registry_are_exact() -> None:
    document = pre.freeze_generic_bytecode_preregistration_v47().to_document()
    for fact in document["source_closure"]["source_facts"]:
        raw = (pre.SOURCE_ROOT / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]
    for key, domain in pre.FUTURE_DOMAINS.items():
        assert key
        assert domain in phase3e_ids.PHASE3E_DOMAIN_TAG_REGISTRY.values()


def test_v47_preregistration_imports_no_environment_kernel() -> None:
    source = Path(pre.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("matching_buffer" in name for name in imported)
    assert not any("stochastic_routing" in name for name in imported)
