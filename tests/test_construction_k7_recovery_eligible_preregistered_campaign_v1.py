from __future__ import annotations

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_recovery_eligible_preregistered_campaign_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:recovery-eligible-preregistered-campaign-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _minimal_input(role: str) -> bytes:
    return canonical_json_bytes({"role": role, "test_fixture": True})


@pytest.fixture(scope="module")
def prepared_registration(tmp_path_factory):
    root = tmp_path_factory.mktemp("recovery-campaign-registration")
    preparation = subject.executor_v1.prepare_recovery_eligible_accounted_runtime_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=root / "cas",
    )
    registration = subject.preregister_recovery_eligible_campaign_v1(
        runtime_preparation=preparation,
        binding_bytes=_minimal_input("SOURCE_BUNDLE_BINDING"),
        snapshot_bytes=_minimal_input("REUSABLE_RAPM_SNAPSHOT"),
        transition_bytes=_minimal_input("PROOF_DEPENDENCY_TRANSITION"),
        occurrence_requests=((_id("registered-1"), 6), (_id("registered-2"), 7)),
    )
    return preparation, registration


def test_domains_and_public_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 8
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error",
        "LOCAL_DOMAINS",
        "MAX_OCCURRENCE_COUNT",
        "MIN_OCCURRENCE_COUNT",
        "RecoveryEligibleCampaignClosureV1",
        "RecoveryEligibleCampaignCommitEventV1",
        "RecoveryEligibleCampaignInputBlobV1",
        "RecoveryEligibleCampaignOccurrenceRowV1",
        "RecoveryEligibleCampaignOccurrenceSpecV1",
        "RecoveryEligibleCampaignPreregistrationV1",
        "RecoveryEligibleCampaignWorkloadV1",
        "RecoveryEligiblePreregisteredCampaignResultV1",
        "preregister_recovery_eligible_campaign_v1",
        "run_recovery_eligible_preregistered_campaign_v1",
        "verify_recovery_eligible_campaign_preregistration_v1",
        "verify_recovery_eligible_preregistered_campaign_v1",
    }


def test_preregistration_freezes_shared_model_and_complete_denominator(
    prepared_registration,
) -> None:
    preparation, registration = prepared_registration
    verified = subject.verify_recovery_eligible_campaign_preregistration_v1(
        registration
    )
    document = verified.to_document()
    assert verified.runtime_preparation is preparation
    assert len(verified.input_blobs) == 3
    assert len(verified.workload.occurrences) == 2
    assert len({row.logical_occurrence_id for row in verified.workload.occurrences}) == 2
    assert len({row.query_ordinal for row in verified.workload.occurrences}) == 2
    assert all(
        row.input_blob_ids == verified.workload.input_blob_ids
        for row in verified.workload.occurrences
    )
    assert document["registration_stage"] == "BEFORE_FIRST_OCCURRENCE_WORKER_LAUNCH"
    assert document["execution_started_by_this_artifact"] is False
    assert document["campaign_result_present"] is False
    assert document["official_execution_allowed"] is False


def test_duplicate_occurrence_or_ordinal_is_rejected(prepared_registration) -> None:
    preparation, _registration = prepared_registration
    common = {
        "runtime_preparation": preparation,
        "binding_bytes": _minimal_input("SOURCE_BUNDLE_BINDING"),
        "snapshot_bytes": _minimal_input("REUSABLE_RAPM_SNAPSHOT"),
        "transition_bytes": _minimal_input("PROOF_DEPENDENCY_TRANSITION"),
    }
    with pytest.raises(subject.ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error):
        subject.preregister_recovery_eligible_campaign_v1(
            **common,
            occurrence_requests=((_id("same"), 6), (_id("same"), 7)),
        )
    with pytest.raises(subject.ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error):
        subject.preregister_recovery_eligible_campaign_v1(
            **common,
            occurrence_requests=((_id("one"), 6), (_id("two"), 6)),
        )


def test_deleted_denominator_is_classified_by_campaign_contract() -> None:
    deleted = SimpleNamespace(
        occurrence_bundles=(object(), object()),
        occurrence_rows=(object(),),
        occurrence_events=(object(), object()),
        closure=SimpleNamespace(occurrence_rows=(object(), object())),
    )
    with pytest.raises(
        subject.ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error,
        match="deleted or added",
    ):
        subject._require_registered_result_cardinality_v1(deleted, 2)


def test_preregistration_is_durable_before_first_worker_launch(
    prepared_registration,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    preparation, _registration = prepared_registration
    campaign = tmp_path / "campaign"

    monkeypatch.setattr(
        subject.executor_v1,
        "prepare_recovery_eligible_accounted_runtime_v1",
        lambda **_kwargs: preparation,
    )

    class StopBeforeScience(RuntimeError):
        pass

    def stop_after_preregistration(*_args, **_kwargs):
        assert (campaign / "CAMPAIGN_PREREGISTRATION.json").is_file()
        assert (campaign / "0000_PREREGISTRATION_COMMITTED.json").is_file()
        assert not any(path.name.startswith("OCCURRENCE_") for path in campaign.iterdir())
        raise StopBeforeScience

    monkeypatch.setattr(
        subject.executor_v1,
        "execute_recovery_eligible_accounted_v1",
        stop_after_preregistration,
    )
    with pytest.raises(StopBeforeScience):
        subject.run_recovery_eligible_preregistered_campaign_v1(
            repository_root=Path(__file__).parents[1],
            runtime_cas_root=tmp_path / "unused-cas",
            campaign_directory=campaign,
            binding_bytes=_minimal_input("SOURCE_BUNDLE_BINDING"),
            snapshot_bytes=_minimal_input("REUSABLE_RAPM_SNAPSHOT"),
            transition_bytes=_minimal_input("PROOF_DEPENDENCY_TRANSITION"),
            occurrence_requests=((_id("order-1"), 6), (_id("order-2"), 7)),
        )


@pytest.fixture(scope="module")
def real_campaign(tmp_path_factory):
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    if (
        os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1"
        or not retained
    ):
        pytest.skip("real recovery-eligible campaign is disabled")
    retained_root = Path(retained)
    root = tmp_path_factory.mktemp("recovery-eligible-campaign-real")
    result = subject.run_recovery_eligible_preregistered_campaign_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=root / "cas",
        campaign_directory=root / "campaign",
        binding_bytes=(retained_root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(retained_root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(retained_root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
        occurrence_requests=((_id("real-campaign-1"), 6), (_id("real-campaign-2"), 7)),
        timeout_seconds=7_200,
    )
    return result


def test_real_campaign_reuses_model_and_closes_full_denominator(real_campaign) -> None:
    result = subject.verify_recovery_eligible_preregistered_campaign_v1(real_campaign)
    document = result.closure.to_document()
    assert document["logical_occurrence_count"] == 2
    assert document["closure_denominator"] == 2
    assert document["certification_coverage_denominator"] == 2
    assert document["economics_cost_denominator"] == 2
    assert document["plan_certificate_count"] == 2
    assert document["full_ground_fallback_certificate_count"] == 2
    assert document["noncertificate_count"] == 0
    assert document["shared_persistent_proof_cache_reused_across_all_occurrences"] is True
    assert len({row.persistent_proof_cache_id for row in result.occurrence_rows}) == 1
    assert len({row.recovery_eligible_checkpoint_id for row in result.occurrence_rows}) == 1
    assert document["campaign_orchestration_work_vector_issued"] is False
    assert document["cross_occurrence_overlay_persistence_authority"] is False
    assert document["official_execution_allowed"] is False


def test_real_campaign_keeps_every_bundle_and_exact_vector_prefix(real_campaign) -> None:
    result = real_campaign
    assert len(result.occurrence_bundles) == 2
    assert all(len(bundle.work_vectors) == 3 for bundle in result.occurrence_bundles)
    assert all(len(bundle.work_vectors[0].records) == 202 for bundle in result.occurrence_bundles)
    first, second = result.closure.vector_prefix_totals
    first_values = dict(first)
    second_values = dict(second)
    for axis in subject.SHARED_AXES:
        if axis in subject.PEAK_AXES:
            assert second_values[axis] == max(
                first_values[axis], dict(result.occurrence_rows[1].occurrence_comparison_values)[axis]
            )
        else:
            assert second_values[axis] == first_values[axis] + dict(
                result.occurrence_rows[1].occurrence_comparison_values
            )[axis]


def test_real_campaign_verifier_rejects_deleted_denominator_row(real_campaign) -> None:
    result = real_campaign
    original = result.occurrence_rows
    try:
        object.__setattr__(result, "occurrence_rows", original[:1])
        with pytest.raises(subject.ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error):
            subject.verify_recovery_eligible_preregistered_campaign_v1(result)
    finally:
        object.__setattr__(result, "occurrence_rows", original)


def test_real_campaign_verifier_rejects_committed_file_tamper(real_campaign) -> None:
    result = real_campaign
    target = result.campaign_directory / "CAMPAIGN_CLOSURE.json"
    raw = target.read_bytes()
    try:
        target.write_bytes(b"{}")
        with pytest.raises(subject.ConstructionK7RecoveryEligiblePreregisteredCampaignV1Error):
            subject.verify_recovery_eligible_preregistered_campaign_v1(result)
    finally:
        target.write_bytes(raw)
