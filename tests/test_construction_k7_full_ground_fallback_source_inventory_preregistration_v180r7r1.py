import hashlib
from pathlib import Path

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_full_ground_fallback_source_inventory_preregistration_v180r7r1 as preregistration


def test_v180r7r1_preregistration_preserves_exact_v180r7_failure() -> None:
    frozen = (
        preregistration.freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1()
    )
    document = frozen.to_document()
    preserved = document["preserved_failure"]
    assert frozen.preregistration_id == preregistration.EXPECTED_PREREGISTRATION_ID
    assert preserved["failed_execution_boundary_commit"] == (
        "fbf314a0d31acbe6e3055a9199c0a6f104492d0e"
    )
    assert preserved["failure_freeze_commit"] == (
        "7345339ed5c4c31f7f2789932b5a4bf81dcc6213"
    )
    assert preserved["failed_authorization_id"] == (
        "445851c4b3ceb25be1858e0c4c07e436631486efe12853db8fef4fdf9c5573e9"
    )
    assert preserved["failure_id"] == (
        "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
    )
    assert preserved["failure_canonical_byte_count"] == 649
    assert preserved["failure_canonical_sha256"] == (
        "b39a368f7299e44344108afeab84d8feef8c8a0dc19585f1a465c16557d62bdb"
    )
    assert preserved["retained_output_file_count"] == 0
    assert preserved["runtime_cas_created"] is False
    assert preserved["same_failed_authorization_rerun_forbidden"] is True
    retained = document["retained_predecessor_input_facts"]
    assert [row["byte_count"] for row in retained] == [
        4_405,
        388_638,
        859_154,
    ]
    root = Path(preregistration.__file__).resolve().parents[2]
    for fact in retained:
        raw = (root / fact["relative_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]


def test_v180r7r1_preregisters_the_exact_cap_split_and_repair_order() -> None:
    before = source_runtime_v2.MAX_MODULES
    document = (
        preregistration.freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1()
        .to_document()
    )
    diagnosis = document["failure_diagnosis"]
    catalog = document["candidate_inventory_contract"]
    closure = document["reachable_closure_contract"]
    assert diagnosis["failed_candidate_module_count"] == 1_951
    assert diagnosis["failed_candidate_source_byte_count"] == 49_436_039
    assert diagnosis["total_root_count"] == 151
    assert diagnosis["diagnostic_reachable_module_count"] == 307
    assert diagnosis["diagnostic_reachable_source_byte_count"] == 15_129_926
    assert catalog["maximum_candidate_module_count"] == 4_096
    assert catalog["maximum_candidate_source_byte_count"] == 64 * 1024 * 1024
    assert (
        catalog[
            "future_identity_wrappers_require_external_manifest_or_proven_exclusion"
        ]
        is True
    )
    assert (
        catalog[
            "authorization_source_must_not_contain_a_catalog_identity_that_hashes_itself"
        ]
        is True
    )
    assert closure["unchanged_v2_reachable_module_cap"] == 1_024
    assert closure["runtime_manifest_file_cap"] == 512
    assert closure["runtime_manifest_total_byte_cap"] == 16 * 1024 * 1024
    assert closure["v2_max_modules_global_mutation_forbidden"] is True
    assert closure["only_exact_reachable_subset_passed_to_v2_builder"] is True
    assert len(closure["repair_steps"]) == 11
    assert source_runtime_v2.MAX_MODULES == before == 1_024


def test_v180r7r1_preregistration_is_outcome_free_and_source_bound() -> None:
    document = (
        preregistration.freeze_full_ground_fallback_source_inventory_preregistration_v180r7r1()
        .to_document()
    )
    locks = document["claim_locks"]
    assert locks == {
        "same_failed_authorization_rerun": False,
        "retained_scientific_input_bytes_changed": False,
        "scientific_contract_changed": False,
        "algorithm_changed": False,
        "source_closure_transport_repair_only": True,
        "bounded_frozen_candidate_namespace_only": True,
        "open_world_source_completeness_claimed": False,
        "fresh_execution_authorization_issued": False,
        "fresh_fallback_execution_started": False,
        "production_outcome_accessed": False,
        "producer_free_verification_present": False,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    root = Path(preregistration.__file__).resolve().parents[2]
    source_facts = document["source_facts"]
    assert [row["relative_path"] for row in source_facts] == sorted(
        {row["relative_path"] for row in source_facts}
    )
    for fact in source_facts:
        raw = (root / fact["relative_path"]).read_bytes()
        assert len(raw) == fact["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == fact["sha256"]
    assert document["construction_only"] is True
    assert document["preregistered_before_any_v180r7r1_outcome"] is True
