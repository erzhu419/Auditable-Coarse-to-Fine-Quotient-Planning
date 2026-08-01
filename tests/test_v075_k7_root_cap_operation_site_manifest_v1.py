from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_accounting_live_v3 as live
from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN,
)
from acfqp import v075_k7_root_cap_operation_site_manifest_v1 as manifest


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-root-cap-site-manifest-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _lifecycle(stage_kind):
    registry = registry_v4.official_counter_registry_v4()
    stage = registry_v4.official_stage_profile_v4(registry)
    comparison = registry_v4.official_comparison_profile_v4(registry)
    actual = registry_v4.official_actual_projection_profile_v4(
        registry, comparison
    )
    return live.open_construction_accounting_lifecycle_v3(
        subject_id=_id(f"subject-{stage_kind.value}"),
        recorder_id="trusted-k7-root-cap-site-test-v1",
        stage_plan=(stage_kind,),
        registry=registry,
        stage_profile=stage,
        comparison_profile=comparison,
        actual_projection_profile=actual,
    ), registry, stage, comparison, actual


def test_exact_nonfresh_scope_and_locked_absence_of_live_evidence() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v1()
    document = frozen.to_document()
    assert document["registered_topology"] == "K7"
    assert document["registered_context_key"] == (
        "heldout_graph_k7_confirmatory_v1"
    )
    assert document["registered_arm"] == "NO_PRIOR"
    assert document["registered_route"] == "ADAPTIVE_QUOTIENT"
    assert document["registered_scientific_accepted_draws"] == 4_224
    assert document["registered_terminal_status"] == (
        "CHILD_ACTION_ROW_CAP_EXCEEDED"
    )
    assert document["stage_plan"] == [
        item.value for item in manifest.ROOT_CAP_STAGE_PLAN
    ]
    assert document["forbidden_unused_stages"] == [
        "OPEN_INCREMENTAL_ACQUISITION",
        "OPEN_CHECKPOINT_REPLANNING",
        "LOCAL_ATTEMPT",
        "DIRECT_FALLBACK",
        "REBUILD",
    ]
    assert set(manifest.ROOT_CAP_STAGE_PLAN).isdisjoint(
        manifest.FORBIDDEN_UNUSED_STAGES
    )
    assert len(frozen.sites) == 23
    assert document["direct_native_hook_site_count"] == 13
    assert document["required_pending_hook_site_count"] == 10
    assert document["operation_site_instrumentation_complete"] is False
    assert (
        document["hash_check_io_peak_granularity_profile_complete"]
        is False
    )
    for field in (
        "live_operation_event_count",
        "live_counter_record_count",
        "work_vector_count",
        "comparison_vector_count",
        "actual_projection_proof_count",
    ):
        assert document[field] == 0
    assert document["caller_totals_allowed"] is False
    assert document["legacy_summary_translation_allowed"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["official_execution_allowed"] is False


def test_site_families_and_pending_common_hooks_are_exact() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v1()
    direct = tuple(
        item
        for item in frozen.sites
        if item.proof_mode
        is manifest.OperationSiteProofModeV1.DIRECT_NATIVE_HOOK_REQUIRED
    )
    targets = {path for item in direct for path in item.target_paths}
    for path in (
        "acquisition.initial_observer_accepted_draws",
        "acquisition.initial_observer_random_word_calls",
        "acquisition.initial_observer_rejections",
        "acquisition.initial_outcome_aggregate_rows",
        "acquisition.initial_signed_batches",
        "acquisition.initial_support_freezes",
        "build.initial_outcome_projections",
        "build.initial_source_units_compiled",
        "build.initial_model_rows_built",
        "build.initial_confidence_event_evaluations",
        "build.initial_exact_likelihood_comparisons",
        "build.initial_interval_log_search_evaluations",
        "build.initial_interval_lp_allocations",
        "build.initial_interval_row_evaluations",
        "build.initial_quotient_cells_compiled",
        "build.initial_semantic_actions_compiled",
        "build.initial_concretizer_ground_actions_compiled",
        "build.initial_policy_assignments_evaluated",
        "build.initial_dominance_comparisons",
        "build.initial_deterministic_tie_breaks",
        "audit.failed_child_catalogues_built",
        "common.abstract_audit_obligations",
        "closure.reconciliation_private_replay_ground_steps",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_rejections",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
        "closure.reconciliation_model_rows_built",
        "closure.reconciliation_policy_assignments_evaluated",
    ):
        assert path in targets

    pending = tuple(
        item
        for item in frozen.sites
        if item.proof_mode
        is manifest.OperationSiteProofModeV1.REQUIRED_PENDING_HOOK
    )
    assert {item.stages[0] for item in pending} == set(
        manifest.ROOT_CAP_STAGE_PLAN
    )
    for stage_kind in manifest.ROOT_CAP_STAGE_PLAN:
        stage_sites = [
            item for item in pending if item.stages == (stage_kind,)
        ]
        assert len(stage_sites) == 2
        stage_targets = {
            path for item in stage_sites for path in item.target_paths
        }
        assert {
            "common.hash_invocations",
            "common.integrity_checks",
            "common.protocol_checks",
            "io.read_bytes",
            "io.staged_bytes",
            "io.output_bytes",
            "io.mounted_bytes_peak",
            "memory.working_bytes_peak",
            "process.launches",
            "process.exit_successes",
            "process.exit_failures",
        } == stage_targets


def test_manifest_and_sites_are_domain_separated_and_tamper_evident() -> None:
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v1()
    assert V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert (
        V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN
        in PHASE3E_DOMAIN_TAGS
    )
    assert frozen.manifest_id != frozen.sites[0].site_id
    assert all(len(item.site_id) == 64 for item in frozen.sites)
    changed = replace(
        frozen.sites[0],
        source_symbol="run_v075_construction_observer_signed_multiround_occurrence_v2.changed",
    )
    changed_sites = tuple(
        sorted(
            (changed, *frozen.sites[1:]),
            key=lambda item: item.site_key,
        )
    )
    altered = replace(frozen, sites=changed_sites)
    assert altered.manifest_id != frozen.manifest_id
    with pytest.raises(
        manifest.V075K7RootCapOperationSiteManifestV1Error,
        match="official K7 root-cap",
    ):
        altered.validate_official()


def test_context_sink_emits_only_registered_native_stage_path_reducer() -> None:
    stage_kind = registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    lifecycle, registry, stage, comparison, actual = _lifecycle(stage_kind)
    active = lifecycle.begin_stage(stage_kind)
    frozen = manifest.official_k7_root_cap_operation_site_manifest_v1()
    batch = frozen.by_key["initial-acquisition.observer-batch"]
    peak = frozen.by_key[
        "initial-acquisition.capacity-peaks-pending"
    ]
    build = frozen.by_key["initial-build.discovery-outcome-projection"]
    support = frozen.by_key["initial-acquisition.support-freeze"]

    with pytest.raises(
        manifest.V075K7RootCapOperationSiteManifestV1Error,
        match="no active",
    ):
        manifest.add_k7_root_cap_native_operation_v1(
            site_id=batch.site_id,
            path="acquisition.initial_observer_accepted_draws",
        )

    with manifest.activate_k7_root_cap_operation_site_sink_v1(active):
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="cannot be nested",
        ):
            with manifest.activate_k7_root_cap_operation_site_sink_v1(active):
                pass
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="unknown operation-site",
        ):
            manifest.add_k7_root_cap_native_operation_v1(
                site_id=_id("foreign-site"),
                path="acquisition.initial_observer_accepted_draws",
            )
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="wrong construction stage",
        ):
            manifest.add_k7_root_cap_native_operation_v1(
                site_id=build.site_id,
                path="build.initial_outcome_projections",
            )
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="unregistered target path",
        ):
            manifest.add_k7_root_cap_native_operation_v1(
                site_id=batch.site_id,
                path="acquisition.initial_support_freezes",
            )
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="pending operation site",
        ):
            manifest.add_k7_root_cap_native_operation_v1(
                site_id=peak.site_id,
                path="io.mounted_bytes_peak",
            )
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="wrong reducer",
        ):
            manifest.observe_k7_root_cap_native_peak_v1(
                site_id=batch.site_id,
                path="acquisition.initial_observer_accepted_draws",
                value=1,
            )
        event = manifest.add_k7_root_cap_native_operation_v1(
            site_id=batch.site_id,
            path="acquisition.initial_observer_accepted_draws",
            amount=4_224,
        )
        manifest.add_k7_root_cap_native_operation_v1(
            site_id=support.site_id,
            path="acquisition.initial_support_freezes",
            amount=2,
        )
        with pytest.raises(
            manifest.V075K7RootCapOperationSiteManifestV1Error,
            match="pending operation site",
        ):
            manifest.observe_k7_root_cap_native_peak_v1(
                site_id=peak.site_id,
                path="io.mounted_bytes_peak",
                value=2_048,
            )

    assert event.operation_site_id == batch.site_id
    recorded = active.complete()
    lifecycle.finish()
    assert recorded.work_vector.values[
        "acquisition.initial_observer_accepted_draws"
    ] == 4_224
    assert recorded.work_vector.values[
        "acquisition.initial_support_freezes"
    ] == 2
    assert recorded.work_vector.values["io.mounted_bytes_peak"] == 0
    live.verify_recorded_stage_work_v3(
        recorded,
        registry,
        stage,
        comparison,
        actual,
    )


def test_sink_rejects_v3_registry_even_when_stage_name_matches() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("v3-subject"),
        recorder_id="trusted-v3-site-negative-v1",
        stage_plan=(
            registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    )
    with pytest.raises(
        manifest.V075K7RootCapOperationSiteManifestV1Error,
        match="exact K7 root-cap v4 profile",
    ):
        with manifest.activate_k7_root_cap_operation_site_sink_v1(active):
            pass
    active.complete()
    lifecycle.finish()
