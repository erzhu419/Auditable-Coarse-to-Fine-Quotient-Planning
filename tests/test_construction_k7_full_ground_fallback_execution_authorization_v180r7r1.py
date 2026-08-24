from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_v180r7r1
    as authorization,
)
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture(scope="module")
def frozen_authorization(
) -> authorization.FullGroundFallbackExecutionAuthorizationV180r7r1:
    return authorization.freeze_full_ground_fallback_execution_authorization_v180r7r1()


def test_v180r7r1_authorization_binds_protocol_lineage_and_inputs(
    frozen_authorization: (
        authorization.FullGroundFallbackExecutionAuthorizationV180r7r1
    ),
) -> None:
    document = frozen_authorization.to_document()
    payload = dict(document)
    identity = payload.pop("fallback_execution_authorization_id")
    assert identity == frozen_authorization.authorization_id
    assert identity == domains.extension_content_id_v180r7r1(
        domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_V180R7R1_DOMAIN,
        payload,
    )
    assert document["fallback_execution_protocol_id"] == (
        "0d037ddaa78b4f6fceca4409db55eeb0acb93d8c1d64953430debd108ef31889"
    )
    assert document["production_execution_slot"]["logical_occurrence_id"] == (
        "293485bc465428ff5b3f923b6d261153a272d30253644076f7dbf19c39cfc3aa"
    )
    assert document["logical_occurrence_id"] == document[
        "production_execution_slot"
    ]["logical_occurrence_id"]
    assert document["query_ordinal"] == 7
    assert document["preserved_v180r7_authorization_id"] == (
        "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
    )
    assert document["preserved_v180r7_failure_id"] == (
        "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
    )
    assert document["failed_v180r7_authorization_reused"] is False
    assert document["same_failed_authorization_rerun_forbidden"] is True
    assert document["source_catalog_manifest_id"] == (
        "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
    )
    assert document["source_closure_repair_id"] == (
        "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
    )
    assert document["materialization_manifest_id"] == (
        "1480c3e0a5bcfe7e88f9cbd6a346efd500c17a1826ca656aa527567a0c8ae7f3"
    )
    assert document["materialized_source_tree_id"] == (
        "5cc30a0a9eea4caa239953af930c8382d3194b2f2ad82847eb9c0ba79b7a2993"
    )
    assert [row["relative_path"] for row in document[
        "retained_predecessor_input_facts"
    ]] == sorted(row["relative_path"] for row in document[
        "retained_predecessor_input_facts"
    ])


def test_v180r7r1_authorization_source_facts_are_exact_and_cycle_free(
    frozen_authorization: (
        authorization.FullGroundFallbackExecutionAuthorizationV180r7r1
    ),
) -> None:
    document = frozen_authorization.to_document()
    facts = document["source_facts"]
    relative_paths = [row["relative_path"] for row in facts]
    assert relative_paths == sorted(
        {row["relative_path"] for row in facts}
    )
    assert all(set(row) == {"relative_path", "byte_count", "sha256"} for row in facts)
    root = Path(__file__).resolve().parents[1]
    for fact in facts:
        raw = (root / fact["relative_path"]).read_bytes()
        assert fact == {
            "relative_path": fact["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    required_live_paths = {
        "scripts/run_v180r7r1_full_ground_fallback_occurrence.py",
        (
            "src/acfqp/construction_k7_full_ground_fallback_"
            "production_terminal_finalizer_v180r7r1.py"
        ),
        (
            "src/acfqp/construction_k7_full_ground_fallback_"
            "production_terminal_independent_verifier_v180r7r1.py"
        ),
        (
            "src/acfqp/construction_k7_recovery_eligible_"
            "occurrence_accounting_v1.py"
        ),
        (
            "src/acfqp/construction_k7_recovery_eligible_"
            "supervised_executor_v1.py"
        ),
        "src/acfqp/construction_accounting_registry_v9.py",
        "src/acfqp/actual_accounting_v1.py",
    }
    assert required_live_paths <= set(relative_paths)
    exclusions = [
        (
            "src/acfqp/construction_k7_full_ground_fallback_execution_"
            "authorization_evidence_freeze_v180r7r1.py"
        ),
        (
            "src/acfqp/"
            "construction_k7_full_ground_fallback_execution_authorization_v180r7r1.py"
        ),
    ]
    assert document["source_fact_exclusions"] == sorted(exclusions)
    assert not set(exclusions) & {row["relative_path"] for row in facts}
    assert document[
        "authorization_self_source_bound_by_post_prereg_freeze"
    ] is False
    assert document["self_identity_cycle_avoided"] is True
    assert document["post_prereg_authorization_evidence_freeze_required"] is True
    replayed = authorization.replay_authorization_source_facts_v180r7r1(
        document
    )
    assert list(replayed) == facts


def test_v180r7r1_authorization_caps_paths_and_gates_are_exact(
    frozen_authorization: (
        authorization.FullGroundFallbackExecutionAuthorizationV180r7r1
    ),
) -> None:
    document = frozen_authorization.to_document()
    caps = document["resource_caps"]
    assert caps["worker_process_count"] == 1
    assert caps["timeout_seconds"] == 7_200
    assert caps["address_space_hard_cap_bytes"] == 24 * 1024**3
    assert caps["candidate_catalog_module_cap"] == 4_096
    assert caps["candidate_catalog_source_byte_cap"] == 64 * 1024**2
    assert caps["reachable_source_module_cap"] == 1_024
    assert caps["reachable_source_byte_cap"] == 16 * 1024**2
    assert caps["runtime_manifest_file_cap"] == 512
    assert document["runtime_cas_root_relative_path"].endswith(
        "v180r7r1_full_ground_fallback_cas"
    )
    assert document["output_root_relative_path"].endswith(
        "v180r7r1_full_ground_fallback_output"
    )
    assert document["terminal_relative_path"].endswith(
        "v180r7r1_full_ground_fallback_terminal_bundle.json"
    )
    assert document["failure_relative_path"].endswith(
        "v180r7r1_full_ground_fallback_failure.json"
    )
    assert document["one_worker_process_required"] is True
    assert document["one_isolated_worker_no_concurrent_campaign"] is True
    assert document[
        "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope"
    ] is True
    assert document["fresh_fallback_execution_started"] is False
    assert document["production_outcome_accessed"] is False
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["outcome_free"] is True
    assert canonical_json_bytes(document) == frozen_authorization.canonical_bytes
