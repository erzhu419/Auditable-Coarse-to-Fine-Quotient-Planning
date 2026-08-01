from __future__ import annotations

from dataclasses import replace

import pytest

from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN,
)
from acfqp import v075_k7_root_cap_operation_site_manifest_v1 as v1
from acfqp import v075_k7_root_cap_operation_site_manifest_v2 as manifest


def test_exact_scope_v1_link_and_all_claim_gates_remain_locked() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    document = frozen.to_document()
    assert document["registered_topology"] == "K7"
    assert document["registered_context_key"] == (
        "heldout_graph_k7_confirmatory_v1"
    )
    assert document["registered_arm"] == "NO_PRIOR"
    assert document["registered_route"] == "ADAPTIVE_QUOTIENT"
    assert document["registered_scientific_accepted_draws"] == 4_224
    assert document["audited_deterministic_trace_facts"] == {
        "acquisition_outcome_aggregate_rows": 41,
        "closure_replay_ground_steps": 4_224,
        "closure_replay_outcome_aggregate_rows": 41,
    }
    assert document["trace_facts_are_live_accounting_evidence"] is False
    assert document["stage_plan"] == [
        "PREOPEN_COMMON_PREFIX",
        "INITIAL_ACQUISITION",
        "INITIAL_MODEL_BUILD",
        "FAILED_ABSTRACT_PREFIX",
        "CLOSED_RECONCILIATION_AND_TERMINALIZATION",
    ]
    assert document["v1_operation_site_manifest_id"] == (
        v1.official_k7_root_cap_operation_site_manifest_v1().manifest_id
    )
    assert document["v1_direct_native_semantic_audit_passed"] is False
    assert document["v1_sink_imported_or_reused"] is False
    assert document["classification_counts"] == {
        "DIRECT_VALID_OWNER_MATCHED": 9,
        "NATIVE_ZERO_NOT_EXECUTED": 13,
        "REQUIRED_PENDING_HOOK": 10,
        "DERIVED_ONLY_RECONCILIATION": 1,
        "MISSING_COUNTER_FAMILY": 10,
    }
    for field in (
        "operation_site_instrumentation_complete",
        "counter_family_complete",
        "hash_check_io_peak_granularity_profile_complete",
        "official_execution_allowed",
        "scientific_endpoint_credit_allowed",
        "counter_completeness_gate_passed",
        "workload_economics_gate_passed",
    ):
        assert document[field] is False
    for field in (
        "live_operation_event_count",
        "live_counter_record_count",
        "work_vector_count",
        "comparison_vector_count",
        "actual_projection_proof_count",
    ):
        assert document[field] == 0


def test_direct_valid_sites_have_exact_v4_owner_and_correct_private_sources() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    registry = registry_v4.official_counter_registry_v4()
    direct = tuple(
        item
        for item in frozen.sites
        if item.classification
        is manifest.OperationSiteClassificationV2.DIRECT_VALID_OWNER_MATCHED
    )
    assert direct
    for site in direct:
        assert site.emitter_module is None
        assert site.emitter_symbol is None
        owner = site.operation_source_module.rsplit(".", 1)[-1]
        assert all(registry.by_path[path].owner == owner for path in site.target_paths)

    acquisition = frozen.by_key[
        "initial-acquisition.private-observer-batch"
    ]
    assert acquisition.operation_source_module == (
        "acfqp.v075_private_observer_boundary_v2"
    )
    assert acquisition.operation_source_symbol == (
        "V075PrivateObserverSessionV2.observe_batch_v2"
    )
    closure = frozen.by_key["closed.private-observer-replay"]
    assert closure.operation_source_module == (
        "acfqp.v075_private_observer_boundary_v2"
    )
    assert closure.operation_source_symbol == (
        "verify_loaded_private_observer_batch_closure_v2"
    )


def test_incompatible_and_inherited_v4_leaves_are_explicit_native_zero() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    registry = registry_v4.official_counter_registry_v4()
    zeros = tuple(
        item
        for item in frozen.sites
        if item.classification
        is manifest.OperationSiteClassificationV2.NATIVE_ZERO_NOT_EXECUTED
    )
    zero_paths = {path for item in zeros for path in item.target_paths}
    assert "build.initial_outcome_projections" in zero_paths
    assert "closure.reconciliation_model_rows_built" in zero_paths
    assert "closure.reconciliation_source_units_compiled" in zero_paths
    inherited_owners = {
        "abstract_auditor",
        "abstract_planner",
        "v075_learned_support_quotient_planners_v1",
        "v075_semantic_replay_instrumentation_v2",
    }
    inherited_paths = {
        path
        for path, leaf in registry.by_path.items()
        if leaf.owner in inherited_owners
        and any(
            path
            in registry_v4.official_stage_profile_v4(registry)
            .by_stage[stage]
            .allowed_nonzero_paths
            for stage in manifest.ROOT_CAP_STAGE_PLAN
        )
    }
    assert inherited_paths <= zero_paths
    assert all(item.emitter_module is None for item in zeros)
    assert all(item.operation_source_module is None for item in zeros)


def test_common_hooks_remain_pending_and_route_views_are_derived_only() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    pending = tuple(
        item
        for item in frozen.sites
        if item.classification
        is manifest.OperationSiteClassificationV2.REQUIRED_PENDING_HOOK
    )
    assert len(pending) == 10
    assert all(item.emitter_module is None for item in pending)
    for stage in manifest.ROOT_CAP_STAGE_PLAN:
        prefix = stage.value.lower().replace("_", "-")
        assert f"{prefix}.common-sum-pending" in frozen.by_key
        assert f"{prefix}.capacity-peaks-pending" in frozen.by_key
    route = frozen.by_key["closed.route-reconciliation-pending"]
    assert route.classification is (
        manifest.OperationSiteClassificationV2.DERIVED_ONLY_RECONCILIATION
    )
    assert route.target_paths == (
        "route.attempts",
        "route.failures",
        "route.successes",
    )
    assert route.emitter_module is None
    assert route.emitter_symbol is None
    assert frozen.to_document()[
        "derived_only_reconciliation_issues_native_record"
    ] is False


def test_batch_v2_work_gaps_have_no_counter_leaf_or_emitter() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    missing = tuple(
        item
        for item in frozen.sites
        if item.classification
        is manifest.OperationSiteClassificationV2.MISSING_COUNTER_FAMILY
    )
    expected_families = {
        "batch_v2_concretizer_work",
        "batch_v2_interval_lp_work",
        "batch_v2_option_enumeration_work",
        "batch_v2_quotient_compilation_work",
        "batch_v2_selection_work",
    }
    assert len(missing) == 10
    assert {item.missing_counter_family for item in missing} == expected_families
    assert {item.stages[0] for item in missing} == {
        registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD,
        (
            registry_v4.ConstructionStageKindV4
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ),
    }
    assert all(not item.target_paths for item in missing)
    assert all(item.reducer is None for item in missing)
    assert all(item.emitter_module is None for item in missing)
    assert all(item.emitter_symbol is None for item in missing)


def test_audit_is_sinkless_domain_separated_and_tamper_evident() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v2()
    assert V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert (
        V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN
        in PHASE3E_DOMAIN_TAGS
    )
    assert "activate_k7_root_cap_operation_site_sink_v1" not in manifest.__dict__
    assert "add_k7_root_cap_native_operation_v1" not in manifest.__dict__
    assert "observe_k7_root_cap_native_peak_v1" not in manifest.__dict__
    assert all(len(item.site_audit_id) == 64 for item in frozen.sites)
    assert frozen.manifest_id not in {item.site_audit_id for item in frozen.sites}

    first = frozen.sites[0]
    changed = replace(first, audit_basis=first.audit_basis + " changed")
    changed_sites = tuple(
        sorted((changed, *frozen.sites[1:]), key=lambda item: item.site_key)
    )
    altered = replace(frozen, sites=changed_sites)
    assert changed.site_audit_id != first.site_audit_id
    assert altered.manifest_id != frozen.manifest_id
    with pytest.raises(
        manifest.V075K7RootCapOperationSiteManifestV2Error,
        match="official strict-owner K7",
    ):
        altered.validate_official()
