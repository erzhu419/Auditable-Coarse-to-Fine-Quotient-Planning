from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v46_is_outcome_free_and_imports_no_environment_kernel() -> None:
    frozen = pre.freeze_lmb_opaque_column_preregistration_v46()
    document = frozen.to_document()
    assert document["outcome_fields_present"] is False
    assert document["campaign_executed"] is False
    assert document["heldout_target"]["target_outcome_observed_before_registration"] is False
    tree = ast.parse(Path(pre.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("matching_buffer" in name or "standard_2048" in name for name in imported)


def test_v46_has_no_column_roles_or_coordinate_equality_scaffold() -> None:
    frozen = pre.freeze_lmb_opaque_column_preregistration_v46()
    document = frozen.to_document()
    adapter = document["opaque_flat_adapter_protocol"]
    grammar = document["generic_relation_meta_grammar"]
    rule = document["mdl_and_dependency_rule"]
    assert document["state_column_roles_predeclared"] is False
    assert document["coordinate_token_equality_scaffold_present"] is False
    assert adapter["state_column_semantic_names_exposed_to_synthesizer"] is False
    assert adapter["action_metadata_semantic_names_exposed_to_synthesizer"] is False
    assert adapter["coordinate_tokens_present"] is False
    assert adapter["direct_cross_interface_equal_values_present"] is False
    assert grammar["predeclared_state_column_roles"] == []
    assert grammar["predeclared_dynamic_column_indices"] == []
    assert grammar["predeclared_action_projection_field"] is None
    assert grammar["direct_descriptor_to_column_equality_constructor_present"] is False
    assert rule["support_signature_fields_predeclared"] == []
    assert rule["expected_factorization_predeclared"] is False
    assert rule["expected_projection_field_predeclared"] is None
    assert b"COORDINATE_TOKENS" not in frozen.canonical_bytes
    assert b"ACTION_PUBLIC_CLASS" not in frozen.canonical_bytes


def test_v46_registers_fresh_permuted_target_and_strict_ood_control() -> None:
    document = pre.freeze_lmb_opaque_column_preregistration_v46().to_document()
    target = document["heldout_target"]
    ood = document["ood_no_transfer_control"]
    assert target["tile_count_changed"] is True
    assert target["type_count_changed"] is True
    assert target["capacity_changed"] is True
    assert target["layer_depth_changed"] is True
    assert target["state_column_order_changed"] is True
    assert target["action_metadata_values_changed"] is True
    assert ood["domain_family"] == "STANDARD_2048"
    assert ood["expected_decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert ood["prior_or_overlay_access_allowed"] is False
    assert ood["transition_outcome_access_allowed"] is False
    assert ood["environment_step_allowed"] is False


def test_v46_identity_domains_accounting_and_claim_locks() -> None:
    frozen = pre.freeze_lmb_opaque_column_preregistration_v46()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    document = frozen.to_document()
    axes = document["accounting_axes"]
    assert axes["source_acquisition_labels"] == "labels"
    assert axes["target_local_distinction_labels"] == "labels"
    assert axes["execution_environment_steps"] == "steps"
    assert axes["factorization_relation_program_dependency_derivation"] == "compute events"
    assert axes["labels_steps_and_compute_may_not_be_collapsed"] is True
    assert document["open_ended_relation_grammar_invention_claimed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
