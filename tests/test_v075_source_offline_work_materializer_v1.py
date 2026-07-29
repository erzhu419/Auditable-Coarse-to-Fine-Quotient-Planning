from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import inspect
import json
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as independent_v2,
)
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1
from acfqp import v072_verified_source_archive_component_v1 as component_v1
import acfqp.v075_source_offline_work_materializer_v1 as v075
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-source-offline-work-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _mechanics_counters() -> campaign_v1.CampaignCounterSummaryV1:
    """A real exact counter object for the small typed mechanics replay."""

    return campaign_v1.CampaignCounterSummaryV1(
        physical_unique_observer_draws=12,
        physical_unique_random_word_calls=14,
        physical_unique_rejections=2,
        logical_direct_rebuild_observer_draws=20,
        logical_quotient_rebuild_observer_draws=12,
        unique_support_epoch_count=3,
        promoted_support_epoch_count=1,
        promoted_outcome_count=2,
        base_model_build_count=3,
        coordinate_candidate_model_build_count=4,
        expansion_candidate_model_build_count=1,
        promoted_model_build_count=1,
        direct_audit_count=3,
        base_quotient_audit_count=3,
        coordinate_candidate_audit_count=4,
        expansion_causal_counterfactual_audit_count=1,
        promoted_replan_audit_count=1,
        fallback_exact_state_action_rows=2,
        standalone_exact_state_action_rows=2,
        operational_exact_support_queries=0,
        operational_exact_probability_queries=0,
    )


@pytest.fixture
def exact_source_replay(
    miniature_source_archive,
) -> recipe_v1.SourceReconstructionReplayV1:
    source_campaign, source_verification, source_archive = (
        miniature_source_archive
    )
    counters = _mechanics_counters()
    for name, value in (
        ("counters", counters),
        (
            "physical_unique_observer_draws",
            counters.physical_unique_observer_draws,
        ),
        (
            "aggregate_direct_unique_observer_draws",
            counters.logical_direct_rebuild_observer_draws,
        ),
        (
            "aggregate_quotient_unique_observer_draws",
            counters.logical_quotient_rebuild_observer_draws,
        ),
        ("official_execution_allowed", False),
        ("official_scalar_cost", None),
        ("official_N_break_even", None),
        ("COUNTER_COMPLETENESS_GATE_NOT_RUN", True),
    ):
        object.__setattr__(source_campaign, name, value)
    production = archive_v2.verify_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
        claimed=source_archive,
    )
    independent = (
        independent_v2.verify_source_acquisition_archive_independently_v2(
            source_campaign=source_campaign,
            source_verification=source_verification,
            claimed=source_archive,
        )
    )
    component = (
        component_v1.bind_v072_verified_source_archive_component_v1(
            archive=source_archive,
            production_verification=production,
            independent_attestation=independent,
        )
    )
    return recipe_v1.SourceReconstructionReplayV1(
        _id("mechanics-source-recipe"),
        source_campaign,
        source_verification,
        source_archive,
        production,
        independent,
        component,
    )


def _campaign_shell(
    replay: recipe_v1.SourceReconstructionReplayV1,
    counters: Any,
) -> campaign_v1.ObservationSupportCampaignV1:
    value = object.__new__(campaign_v1.ObservationSupportCampaignV1)
    for name, item in (
        ("counters", counters),
        (
            "physical_unique_observer_draws",
            getattr(counters, "physical_unique_observer_draws", 0),
        ),
        (
            "aggregate_direct_unique_observer_draws",
            getattr(counters, "logical_direct_rebuild_observer_draws", 0),
        ),
        (
            "aggregate_quotient_unique_observer_draws",
            getattr(counters, "logical_quotient_rebuild_observer_draws", 0),
        ),
        ("official_execution_allowed", False),
        ("official_scalar_cost", None),
        ("official_N_break_even", None),
        ("COUNTER_COMPLETENESS_GATE_NOT_RUN", True),
    ):
        object.__setattr__(value, name, item)
    return value


def test_domains_are_unique_and_v075_only() -> None:
    assert len(v075.DOMAIN_TAGS) == len(set(v075.DOMAIN_TAGS.values()))
    assert all(
        domain.startswith("acfqp:v075-")
        for domain in v075.DOMAIN_TAGS.values()
    )


def test_production_integration_is_explicitly_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("full historical source replay was called")

    monkeypatch.setattr(
        recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        forbidden,
    )
    status = (
        v075.freeze_v075_source_offline_work_production_integration_status_v1()
    )
    document = status.to_document()

    assert (
        document["integration_replay_status"]
        == v075.PRODUCTION_INTEGRATION_REPLAY_STATUS
        == "NOT_RUN"
    )
    assert document["materialization_id"] is None
    assert document["counter_values_serialized"] is False
    assert document["source_reconstruction_replay_calls"] == 0
    assert document["counter_completeness_claimed"] is False
    assert document["economics_available"] is False
    assert document["official_execution_allowed"] is False
    assert document["target_execution_allowed"] is False


def test_materializer_accepts_only_one_exact_replay_argument() -> None:
    signature = inspect.signature(
        v075.materialize_v075_source_offline_work_v1
    )
    assert tuple(signature.parameters) == ("replay",)
    assert (
        signature.parameters["replay"].annotation
        == "recipe_v1.SourceReconstructionReplayV1"
    )


def test_exact_replay_materializes_all_native_counter_fields(
    exact_source_replay,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    document = materialized.to_document()
    counters = document["campaign_counters"]

    assert tuple(
        item.name
        for item in fields(campaign_v1.CampaignCounterSummaryV1)
    ) == v075.CAMPAIGN_COUNTER_FIELD_ORDER
    assert document["campaign_counter_field_order"] == list(
        v075.CAMPAIGN_COUNTER_FIELD_ORDER
    )
    assert all(name in counters for name in v075.CAMPAIGN_COUNTER_FIELD_ORDER)
    assert (
        document["campaign_counters_id"]
        == exact_source_replay.source_campaign.counters.counters_id
    )
    assert counters == exact_source_replay.source_campaign.counters.to_document()
    assert document["offline_sample_draw_count"] == 12
    assert document["offline_random_word_call_count"] == 14
    assert document["offline_rejection_count"] == 2
    assert document["sample_draw_offline_work_nonzero"] is True
    assert document["sample_draw_offline_work_replayable"] is True


def test_materialization_binds_complete_replay_identity_graph(
    exact_source_replay,
) -> None:
    value = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    assert (
        value.source_recipe_id,
        value.source_campaign_id,
        value.source_campaign_verification_id,
        value.source_archive_id,
        value.production_archive_verification_id,
        value.independent_archive_attestation_id,
        value.source_archive_component_id,
    ) == (
        exact_source_replay.recipe_id,
        exact_source_replay.source_campaign.campaign_id,
        exact_source_replay.source_verification.verification_id,
        exact_source_replay.archive.archive_id,
        exact_source_replay.production_verification.verification_id,
        exact_source_replay.independent_attestation.verification_id,
        exact_source_replay.component.component_id,
    )


def test_economics_and_completeness_remain_unavailable(
    exact_source_replay,
) -> None:
    document = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    ).to_document()

    assert document["counter_completeness_claimed"] is False
    assert document["comparison_work_vector_materialized"] is False
    assert document["economics_available"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["caller_counter_input_accepted"] is False
    assert document["zero_substitution_allowed"] is False
    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["may_certify"] is False
    assert document["target_execution_allowed"] is False


def test_strict_loader_and_independent_comparison_round_trip(
    exact_source_replay,
) -> None:
    value = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    loaded = v075.load_v075_source_offline_work_materialization_v1(
        value.canonical_bytes,
        expected_materialization_id=value.materialization_id,
        expected_source_recipe_id=value.source_recipe_id,
        expected_source_campaign_id=value.source_campaign_id,
        expected_campaign_counters_id=value.campaign_counters.counters_id,
    )
    verification = (
        v075.verify_v075_source_offline_work_bytes_independently_v1(
            replay=exact_source_replay,
            raw=value.canonical_bytes,
        )
    )

    assert loaded == value
    assert verification.materialization_id == value.materialization_id
    assert verification.recomputed_materialization_id == value.materialization_id
    assert verification.to_document()["exact_replay_object_compared"] is True
    assert (
        verification.to_document()[
            "source_reconstruction_replay_executed_by_verifier"
        ]
        is False
    )


def test_materialization_does_not_run_replay_or_observer(
    exact_source_replay,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("replay/observer was called")

    monkeypatch.setattr(
        recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        forbidden,
    )
    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    value = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    assert (
        value.to_document()[
            "source_reconstruction_replay_executed_by_materializer"
        ]
        is False
    )


def test_nonexact_replay_and_counter_are_rejected(
    exact_source_replay,
) -> None:
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.materialize_v075_source_offline_work_v1(
            SimpleNamespace()  # type: ignore[arg-type]
        )

    fake_counter = SimpleNamespace(
        physical_unique_observer_draws=12,
        physical_unique_random_word_calls=12,
        physical_unique_rejections=0,
        logical_direct_rebuild_observer_draws=20,
        logical_quotient_rebuild_observer_draws=12,
    )
    bad_campaign = _campaign_shell(exact_source_replay, fake_counter)
    bad_replay = replace(exact_source_replay, source_campaign=bad_campaign)
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.materialize_v075_source_offline_work_v1(bad_replay)


def test_zero_sample_work_cannot_substitute_for_replayed_work(
    exact_source_replay,
) -> None:
    zero_sample = campaign_v1.CampaignCounterSummaryV1(
        physical_unique_observer_draws=0,
        physical_unique_random_word_calls=0,
        physical_unique_rejections=0,
        logical_direct_rebuild_observer_draws=0,
        logical_quotient_rebuild_observer_draws=0,
        unique_support_epoch_count=1,
        promoted_support_epoch_count=0,
        promoted_outcome_count=0,
        base_model_build_count=1,
        coordinate_candidate_model_build_count=0,
        expansion_candidate_model_build_count=0,
        promoted_model_build_count=0,
        direct_audit_count=1,
        base_quotient_audit_count=1,
        coordinate_candidate_audit_count=0,
        expansion_causal_counterfactual_audit_count=0,
        promoted_replan_audit_count=0,
        fallback_exact_state_action_rows=0,
        standalone_exact_state_action_rows=0,
        operational_exact_support_queries=0,
        operational_exact_probability_queries=0,
    )
    bad_campaign = _campaign_shell(exact_source_replay, zero_sample)
    bad_replay = replace(exact_source_replay, source_campaign=bad_campaign)

    with pytest.raises(
        v075.V075SourceOfflineWorkMaterializationViolation,
        match="nonzero",
    ):
        v075.materialize_v075_source_offline_work_v1(bad_replay)


def test_caller_counter_and_target_inputs_are_not_api_parameters(
    exact_source_replay,
) -> None:
    with pytest.raises(TypeError):
        v075.materialize_v075_source_offline_work_v1(
            exact_source_replay,
            counters=_mechanics_counters(),  # type: ignore[call-arg]
        )
    with pytest.raises(TypeError):
        v075.materialize_v075_source_offline_work_v1(
            exact_source_replay,
            target_input={"old": "evidence"},  # type: ignore[call-arg]
        )


def test_cross_role_identity_alias_fails_closed(
    exact_source_replay,
) -> None:
    aliased = replace(
        exact_source_replay,
        recipe_id=exact_source_replay.archive.archive_id,
    )
    with pytest.raises(
        v075.V075SourceOfflineWorkMaterializationViolation,
        match="incompatible roles",
    ):
        v075.materialize_v075_source_offline_work_v1(aliased)


def test_relationship_mismatch_fails_closed(
    exact_source_replay,
) -> None:
    verification = object.__new__(
        campaign_v1.ObservationSupportCampaignVerificationV1
    )
    for name, value in (
        ("campaign_id", _id("foreign-campaign")),
        ("replayed_campaign_id", _id("foreign-campaign")),
        ("same_implementation_full_replay", True),
        ("independent_implementation_claimed", False),
        ("valid", True),
    ):
        object.__setattr__(verification, name, value)
    mismatched = replace(
        exact_source_replay,
        source_verification=verification,
    )
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.materialize_v075_source_offline_work_v1(mismatched)


@pytest.mark.parametrize(
    ("mutation", "value"),
    (
        ("counter_completeness_claimed", True),
        ("economics_available", True),
        ("official_scalar_cost", 0),
        ("target_execution_allowed", True),
        ("offline_sample_draw_count", 0),
    ),
)
def test_claim_or_derived_value_mutation_is_rejected(
    exact_source_replay,
    mutation: str,
    value: object,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    document = json.loads(materialized.canonical_bytes)
    document[mutation] = value

    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.load_v075_source_offline_work_materialization_v1(
            canonical_json_bytes(document),
            expected_materialization_id=materialized.materialization_id,
            expected_source_recipe_id=materialized.source_recipe_id,
            expected_source_campaign_id=materialized.source_campaign_id,
            expected_campaign_counters_id=(
                materialized.campaign_counters.counters_id
            ),
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("caller_counters", {"physical_unique_observer_draws": 1}),
        ("target_input", {"old_evidence_id": "0" * 64}),
        ("work_vector_id", "0" * 64),
    ),
)
def test_injected_counter_target_or_workvector_field_is_rejected(
    exact_source_replay,
    field_name: str,
    value: object,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    document = json.loads(materialized.canonical_bytes)
    document[field_name] = value
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.load_v075_source_offline_work_materialization_v1(
            canonical_json_bytes(document),
            expected_materialization_id=materialized.materialization_id,
            expected_source_recipe_id=materialized.source_recipe_id,
            expected_source_campaign_id=materialized.source_campaign_id,
            expected_campaign_counters_id=(
                materialized.campaign_counters.counters_id
            ),
        )


def test_missing_native_counter_and_stale_counter_id_are_rejected(
    exact_source_replay,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    missing = json.loads(materialized.canonical_bytes)
    missing["campaign_counters"].pop("promoted_outcome_count")
    stale = json.loads(materialized.canonical_bytes)
    stale["campaign_counters"]["promoted_outcome_count"] += 1

    for document in (missing, stale):
        with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
            v075.load_v075_source_offline_work_materialization_v1(
                canonical_json_bytes(document),
                expected_materialization_id=materialized.materialization_id,
                expected_source_recipe_id=materialized.source_recipe_id,
                expected_source_campaign_id=materialized.source_campaign_id,
                expected_campaign_counters_id=(
                    materialized.campaign_counters.counters_id
                ),
            )


def test_coherently_resigned_materialization_fails_replay_comparison(
    exact_source_replay,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    changed = replace(
        materialized,
        source_recipe_id=_id("coherently-resigned-recipe"),
    )
    assert changed.materialization_id != materialized.materialization_id
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.verify_v075_source_offline_work_independently_v1(
            replay=exact_source_replay,
            claimed=changed,
        )


def test_noncanonical_bytes_and_wrong_external_identity_are_rejected(
    exact_source_replay,
) -> None:
    materialized = v075.materialize_v075_source_offline_work_v1(
        exact_source_replay
    )
    arguments = {
        "expected_materialization_id": materialized.materialization_id,
        "expected_source_recipe_id": materialized.source_recipe_id,
        "expected_source_campaign_id": materialized.source_campaign_id,
        "expected_campaign_counters_id": (
            materialized.campaign_counters.counters_id
        ),
    }
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.load_v075_source_offline_work_materialization_v1(
            materialized.canonical_bytes + b"\n",
            **arguments,
        )
    with pytest.raises(v075.V075SourceOfflineWorkMaterializationViolation):
        v075.load_v075_source_offline_work_materialization_v1(
            materialized.canonical_bytes,
            **{
                **arguments,
                "expected_materialization_id": _id("wrong-materialization"),
            },
        )
