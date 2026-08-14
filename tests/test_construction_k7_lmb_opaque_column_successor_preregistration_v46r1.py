from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from acfqp import construction_k7_lmb_opaque_column_failure_v46 as failure
from acfqp import construction_k7_lmb_opaque_column_preregistration_v46 as base
from acfqp import (
    construction_k7_lmb_opaque_column_successor_preregistration_v46r1 as pre,
)
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v46r1_is_outcome_free_and_imports_no_environment_kernel() -> None:
    frozen = pre.freeze_lmb_opaque_column_successor_preregistration_v46r1()
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


def test_v46r1_preserves_failure_and_registers_only_missing_constructors() -> None:
    document = pre.freeze_lmb_opaque_column_successor_preregistration_v46r1().to_document()
    predecessors = document["frozen_predecessors"]
    correction = document["grammar_correction"]
    assert predecessors["v46_preregistration_id"] == base.PREREGISTRATION_ID
    assert predecessors["v46_failure_id"] == failure.FAILURE_ID
    assert predecessors["v46_attempted_campaign_id"] == pre.V46_ATTEMPTED_CAMPAIGN_ID
    assert predecessors["v46_failure_preserved_before_successor_registration"] is True
    assert correction["exact_unregistered_constructor_names"] == list(pre.ADDED_CONSTRUCTORS)
    old = {row[0] for row in base.GENERIC_RELATION_META_GRAMMAR["constructors"]}
    new = {row[0] for row in pre.GENERIC_RELATION_META_GRAMMAR["constructors"]}
    assert new - old == set(pre.ADDED_CONSTRUCTORS)
    assert correction["no_other_constructor_added"] is True
    assert correction["same_identity_corrected_rerun_allowed"] is False


def test_v46r1_uses_fresh_identities_and_no_semantic_scaffold() -> None:
    document = pre.freeze_lmb_opaque_column_successor_preregistration_v46r1().to_document()
    assert set(pre.SOURCE_ACQUISITION_SEEDS).isdisjoint(base.SOURCE_ACQUISITION_SEEDS)
    assert pre.SOURCE_CONFIRMATION_SEED != base.SOURCE_CONFIRMATION_SEED
    assert set(pre.HELDOUT_SEEDS).isdisjoint(base.HELDOUT_SEEDS)
    grammar = document["generic_relation_meta_grammar"]
    adapter = document["opaque_flat_adapter_protocol"]
    assert grammar["predeclared_state_column_roles"] == []
    assert grammar["predeclared_dynamic_column_indices"] == []
    assert grammar["predeclared_action_projection_field"] is None
    assert grammar["coordinate_token_atom_present"] is False
    assert grammar["direct_descriptor_to_column_equality_constructor_present"] is False
    assert adapter["coordinate_tokens_present"] is False
    assert adapter["direct_cross_interface_equal_values_present"] is False
    assert document["state_column_roles_predeclared"] is False
    assert document["coordinate_token_equality_scaffold_present"] is False


def test_v46r1_ood_accounting_domains_and_claim_locks() -> None:
    frozen = pre.freeze_lmb_opaque_column_successor_preregistration_v46r1()
    document = frozen.to_document()
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    assert len(set(pre.FUTURE_DOMAINS.values())) == len(pre.FUTURE_DOMAINS)
    assert set(pre.FUTURE_DOMAINS.values()) <= PHASE3E_DOMAIN_TAGS
    ood = document["ood_no_transfer_control"]
    assert ood["expected_decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert ood["prior_or_overlay_access_allowed"] is False
    assert ood["transition_outcome_access_allowed"] is False
    assert ood["environment_step_allowed"] is False
    axes = document["accounting_axes"]
    assert axes["source_acquisition_labels"] == "labels"
    assert axes["target_local_distinction_labels"] == "labels"
    assert axes["execution_environment_steps"] == "steps"
    assert axes["factorization_relation_program_dependency_derivation"] == "compute events"
    assert axes["certificate_evaluations"] == "compute events"
    assert axes["labels_steps_and_compute_may_not_be_collapsed"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
