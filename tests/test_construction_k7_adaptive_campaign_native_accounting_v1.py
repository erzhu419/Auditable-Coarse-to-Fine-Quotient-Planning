from __future__ import annotations

import pytest

from acfqp import construction_accounting_registry_v6 as v6
from acfqp import construction_accounting_registry_v7 as v7
from acfqp import construction_k7_adaptive_campaign_native_accounting_v1 as subject
from acfqp import transition_tuple_observer_v1 as observer


@pytest.fixture(scope="module")
def campaign():
    return subject.run_adaptive_campaign_native_accounting_v1()


def test_v7_is_an_exact_v6_prefix_plus_registered_adaptive_families():
    old = v6.official_counter_registry_v6()
    new = v7.official_counter_registry_v7()
    stage = v7.official_stage_profile_v7(new)
    comparison = v7.official_comparison_profile_v7(new)
    actual = v7.official_actual_projection_profile_v7(new, comparison)

    assert len(new.leaves) == 228
    assert len(new.operational_leaves) == 199
    assert len(new.required_paths) == 221
    assert [new.by_path[row.path].to_dict() for row in old.leaves] == [
        row.to_dict() for row in old.leaves
    ]
    assert len(comparison.terms) == len(new.operational_leaves)
    assert comparison.terms == actual.terms
    stage.validate(new)
    comparison.validate(new)
    actual.validate(new, comparison)


def test_same_window_campaign_covers_construct_reuse_and_unsupported(campaign):
    assert [row.result_outcome for row in campaign.occurrences] == [
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        "EXISTING_MODEL_REUSED",
        "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED",
        "EXISTING_MODEL_REUSED",
        "NO_CERTIFIABLE_CONSTRUCTOR",
    ]
    assert [row.phase for row in campaign.occurrences[0].components] == [
        "COMMON_PREFIX",
        "LOCAL_RECOVERY",
        "ABSTRACT_CERTIFICATE",
    ]
    assert [row.phase for row in campaign.occurrences[1].components] == [
        "COMMON_PREFIX",
        "ABSTRACT_CERTIFICATE",
    ]
    assert [row.phase for row in campaign.occurrences[4].components] == [
        "COMMON_PREFIX"
    ]


def test_constructed_models_charge_exact_local_evidence_and_recertification(campaign):
    for occurrence, expected_draws in (
        (campaign.occurrences[0], 4_096),
        (campaign.occurrences[2], 8_192),
    ):
        common, local, abstract = occurrence.components
        assert common.values["common.model_acquisition_ground_draws"] > 0
        assert local.values["local.model_acquisition_ground_draws"] == expected_draws
        assert local.values["local.model_outcome_projections"] == expected_draws
        assert local.values["local.model_catalogue_promotion_events"] == 1
        assert local.values["local.model_coordinate_candidate_evaluations"] > 0
        assert local.values["local.model_coordinate_candidate_rows_built"] > 0
        assert local.values["local.model_coordinate_candidate_bellman_backups"] > 0
        assert local.values["local.model_coordinate_candidate_audit_obligations"] > 0
        assert local.values["common.abstract_audit_obligations"] > 0
        assert abstract.values["common.abstract_audit_obligations"] > 0
        assert abstract.values["common.abstract_bellman_backups"] > 0


def test_exact_reuse_is_zero_local_ground_and_plans_in_the_model(campaign):
    for occurrence in (campaign.occurrences[1], campaign.occurrences[3]):
        common, abstract = occurrence.components
        assert common.values["common.constructor_program_candidate_evaluations"] == 62
        assert common.values["common.model_catalogue_selection_evaluations"] == 1
        assert abstract.values["common.abstract_audit_obligations"] > 0
        assert abstract.values["common.abstract_bellman_backups"] > 0
        assert all(
            component.values[path] == 0
            for component in occurrence.components
            for path in component.values
            if path.startswith("local.model_")
            or path in {
                "common.model_acquisition_ground_draws",
                "common.model_acquisition_random_word_calls",
            }
        )


def test_unsupported_control_stops_before_ground_access(campaign):
    component = campaign.occurrences[4].components[0]
    assert component.values["common.constructor_program_candidate_evaluations"] == 62
    assert component.values["common.model_catalogue_selection_evaluations"] == 1
    assert all(
        value == 0
        for path, value in component.values.items()
        if "model_acquisition" in path
        or "model_bridge" in path
        or path.startswith("local.")
        or path.startswith("fallback.")
    )


def test_every_component_has_explicit_nonshared_records_but_no_fake_receipts(campaign):
    expected_count = v7.EXPECTED_V7_REQUIRED_LEAF_COUNT - len(
        subject.SHARED_RESOURCE_PATHS
    )
    for occurrence in campaign.occurrences:
        for component in occurrence.components:
            assert len(component.records) == expected_count == 212
            assert {row.path for row in component.records}.isdisjoint(
                subject.SHARED_RESOURCE_PATHS
            )
            assert all(row.observed is True for row in component.records)
    document = campaign.to_document()
    assert document["shared_resource_receipts_present"] is False
    assert document["formal_work_vectors_issued"] is False
    assert document["formal_comparison_vectors_issued"] is False
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    assert all(
        any(event.target_path == "common.hash_invocations" for event in row.shared_events)
        for row in campaign.occurrences
    )
    assert all(
        any(event.target_path == "process.launches" for event in row.shared_events)
        for row in (campaign.occurrences[0], campaign.occurrences[2])
    )
    assert all(
        not any(event.target_path == "process.launches" for event in row.shared_events)
        for row in (campaign.occurrences[1], campaign.occurrences[3], campaign.occurrences[4])
    )


def test_component_rejects_missing_or_duplicate_counter_records(campaign):
    component = campaign.occurrences[0].components[0]
    with pytest.raises(
        subject.ConstructionK7AdaptiveCampaignNativeAccountingV1Error,
        match="omits a non-shared required counter",
    ):
        subject.AdaptiveNativeComponentV1(
            subject._COMPONENT_ISSUER,
            component.occurrence_id,
            component.phase,
            component.route_kind,
            component.recorder_id,
            component.events,
            component.records[:-1],
        )
    duplicate = tuple(sorted((*component.records, component.records[0]), key=lambda row: row.path))
    with pytest.raises(subject.ConstructionK7AdaptiveCampaignNativeAccountingV1Error):
        subject.AdaptiveNativeComponentV1(
            subject._COMPONENT_ISSUER,
            component.occurrence_id,
            component.phase,
            component.route_kind,
            component.recorder_id,
            component.events,
            duplicate,
        )


def test_operation_session_rejects_a_forged_caller():
    registry = v7.official_counter_registry_v7()
    manifest = subject.official_adaptive_operation_manifest_v1(registry)
    occurrence_id = "a" * 64
    session = subject._AdaptiveAccountingSessionV1(
        occurrence_id=occurrence_id,
        registry=registry,
        manifest=manifest,
    )
    with pytest.raises(
        subject.ConstructionK7AdaptiveCampaignNativeAccountingV1Error,
        match="caller differs",
    ):
        session.emit_operation(
            "adaptive-world-model.catalogue-selection",
            1,
            caller_module=observer.__name__,
            caller_globals=observer.__dict__,
            caller_code=observer.public_context_by_key_v1.__code__,
        )
