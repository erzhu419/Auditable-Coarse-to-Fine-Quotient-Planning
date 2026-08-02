from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_accounting_evidence_closure_v1 as closure_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import construction_shared_resource_resolution_v2 as v2
from acfqp.phase3e_ids import canonical_json_bytes


def _cid(index: int) -> str:
    return f"{index:064x}"


def _identity() -> dict[str, str | int]:
    return {
        "live_envelope_id": _cid(101),
        "occurrence_id": _cid(102),
        "route_attempt_id": _cid(103),
        "decision_point_id": _cid(104),
        "measurement_window_id": _cid(105),
        "operational_cutoff_id": _cid(106),
        "covered_start_sequence": 7,
        "covered_cutoff_sequence": 91,
    }


def _component(
    requirement: v2.SharedResourceRequiredComponentV2,
    *,
    index: int,
    extra: dict[str, object] | None = None,
) -> v2.SharedResourceEvidenceComponentV2:
    document: dict[str, object] = {
        "schema": requirement.source_schema_id,
        "schema_version": "2.0.0",
        "component_key": requirement.component_key,
        "synthetic_test_fixture_only": True,
    }
    if extra:
        document.update(extra)
    raw = canonical_json_bytes(document)
    return v2.SharedResourceEvidenceComponentV2(
        requirement.component_key,
        requirement.source_schema_id,
        _cid(index),
        hashlib.sha256(raw).hexdigest(),
        raw,
    )


def _source(
    contract: v2.SharedResourcePathContractV2,
    *,
    component_count: int | None = None,
) -> v2.SharedResourceLiveSourceV2:
    selected = (
        contract.required_components
        if component_count is None
        else contract.required_components[:component_count]
    )
    components = tuple(
        _component(row, index=200 + offset)
        for offset, row in enumerate(selected)
    )
    return v2.SharedResourceLiveSourceV2(
        **_identity(),
        path=contract.path,
        exact_source_kind=contract.exact_source_kind,
        provenance_claims=contract.required_provenance,
        components=components,
    )


def _envelope(
    sources: tuple[v2.SharedResourceLiveSourceV2, ...] = (),
) -> v2.SharedResourceLiveEnvelopeV2:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    identity = _identity()
    return v2.SharedResourceLiveEnvelopeV2(
        live_envelope_schema_id=v2.LIVE_ENVELOPE_SCHEMA_ID,
        live_envelope_id=identity["live_envelope_id"],
        counter_registry_id=registry.registry_id,
        stage_profile_id=stage.stage_profile_id,
        occurrence_id=identity["occurrence_id"],
        route_attempt_id=identity["route_attempt_id"],
        decision_point_id=identity["decision_point_id"],
        measurement_window_id=identity["measurement_window_id"],
        operational_cutoff_id=identity["operational_cutoff_id"],
        measurement_start_sequence=identity["covered_start_sequence"],
        operational_cutoff_sequence=identity["covered_cutoff_sequence"],
        catalogue_fingerprint=(
            v2.official_shared_resource_catalogue_fingerprint_v2()
        ),
        sources=sources,
    )


def test_official_catalogue_has_exact_nine_v6_paths_and_metadata() -> None:
    catalogue = v2.official_shared_resource_resolution_catalogue_v2()
    registry = registry_v6.official_counter_registry_v6()
    assert tuple(row.path for row in catalogue) == (
        receipts_v1.SHARED_RESOURCE_PATHS
    )
    assert len(catalogue) == 9
    assert len({row.exact_source_kind for row in catalogue}) == 9
    assert len({row.semantic_verifier_key for row in catalogue}) == 9
    for row in catalogue:
        leaf = registry.by_path[row.path]
        assert row.owner == leaf.owner
        assert row.semantics_id == leaf.semantics_id
        assert row.unit == leaf.unit
        assert row.scope == leaf.scope
        assert row.reducer is leaf.reducer
        assert row.replay_availability is (
            v2.SharedResourceReplayAvailabilityV2.NOT_INSTALLED
        )
        assert (
            v2.SharedResourceProvenanceProofKindV2
            .OCCURRENCE_IDENTITY_BINDING
        ) in row.required_provenance
        assert (
            v2.SharedResourceProvenanceProofKindV2.CLOSED_INCLUSIVE_CUTOFF
        ) in row.required_provenance


def test_empty_live_envelope_returns_nine_typed_pending_resolutions() -> None:
    result = v2.verify_v075_k7_shared_resource_semantics_v2(_envelope())
    assert len(result.resolutions) == 9
    assert result.all_nine_verified_exact is False
    assert set(result.pending_live_fields) == set(v2.SHARED_RESOURCE_PATHS)
    for row, contract in zip(
        result.resolutions,
        v2.official_shared_resource_resolution_catalogue_v2(),
        strict=True,
    ):
        assert row.status is (
            v2.SharedResourceResolutionStatusV2.PENDING_LIVE_EVIDENCE
        )
        assert row.pending_reason is (
            v2.SharedResourcePendingReasonV2.SOURCE_PATH_ABSENT
        )
        assert row.exact_value is None
        assert row.source_artifact_ids == ()
        assert row.missing_component_keys == tuple(
            item.component_key for item in contract.required_components
        )
        assert row.eligible_as_verified_shared_resolution is False
        assert row.counter_record_issuance_authorized is False
    document = result.to_internal_document()
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["formal_vector_authorized"] is False


def test_complete_raw_source_is_not_promoted_without_semantic_replay() -> None:
    contract = v2.official_shared_resource_resolution_catalogue_v2()[0]
    result = v2.verify_v075_k7_shared_resource_semantics_v2(
        _envelope((_source(contract),))
    )
    row = result.resolutions[0]
    assert row.path == contract.path
    assert row.present_component_keys == tuple(
        item.component_key for item in contract.required_components
    )
    assert row.missing_component_keys == ()
    assert row.pending_reason is (
        v2.SharedResourcePendingReasonV2.SEMANTIC_REPLAYER_NOT_INSTALLED
    )
    assert row.exact_value is None
    assert row.source_bytes_replayed is False
    assert row.provenance_replayed is False
    assert row.semantic_verifier_id is None


def test_partial_raw_source_names_every_missing_live_component() -> None:
    contract = v2.official_shared_resource_resolution_catalogue_v2()[0]
    source = _source(contract, component_count=1)
    result = v2.verify_v075_k7_shared_resource_semantics_v2(
        _envelope((source,))
    )
    row = result.resolutions[0]
    assert row.pending_reason is (
        v2.SharedResourcePendingReasonV2.REQUIRED_COMPONENTS_ABSENT
    )
    assert row.present_component_keys == (
        contract.required_components[0].component_key,
    )
    assert row.missing_component_keys == tuple(
        item.component_key for item in contract.required_components[1:]
    )


@pytest.mark.parametrize(
    "legacy_type",
    [
        receipts_v1.SharedResourceReceiptSetV1,
        receipts_v1.SharedResourceReceiptV1,
        closure_v1.EvidenceClosureV1,
        closure_v1.RequiredPathResolutionV1,
    ],
)
def test_historical_unverified_runtime_objects_cannot_be_relabelled(
    legacy_type: type[object],
) -> None:
    legacy = object.__new__(legacy_type)
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="cannot be relabelled",
    ):
        v2.verify_v075_k7_shared_resource_semantics_v2(legacy)


def test_mapping_spoof_cannot_replace_typed_live_envelope() -> None:
    forged = {
        "schema": v2.LIVE_ENVELOPE_SCHEMA_ID,
        "source_evidence_semantics_verified": True,
        "reported_values": {path: 0 for path in v2.SHARED_RESOURCE_PATHS},
    }
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="typed live-envelope adapter",
    ):
        v2.verify_v075_k7_shared_resource_semantics_v2(forged)


def test_unverified_or_v1_component_bytes_are_rejected_before_replay() -> None:
    raw_v1 = canonical_json_bytes(
        {
            "schema": "acfqp.construction_shared_resource_receipt.v1",
            "source_evidence_semantics_verified": False,
        }
    )
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="cannot be relabelled",
    ):
        v2.SharedResourceEvidenceComponentV2(
            "hash_event_transcript",
            "acfqp.construction_shared_resource_receipt.v1",
            _cid(301),
            hashlib.sha256(raw_v1).hexdigest(),
            raw_v1,
        )

    requirement = (
        v2.official_shared_resource_resolution_catalogue_v2()[0]
        .required_components[0]
    )
    raw_false = canonical_json_bytes(
        {
            "schema": requirement.source_schema_id,
            "source_evidence_semantics_verified": False,
        }
    )
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="explicitly unverified",
    ):
        v2.SharedResourceEvidenceComponentV2(
            requirement.component_key,
            requirement.source_schema_id,
            _cid(302),
            hashlib.sha256(raw_false).hexdigest(),
            raw_false,
        )


def test_fixed_catalogue_and_source_contracts_fail_closed_on_tamper() -> None:
    catalogue = v2.official_shared_resource_resolution_catalogue_v2()
    forged_catalogue = (
        replace(
            catalogue[0],
            semantic_verifier_key="verify_caller_claimed_value_v2",
        ),
    ) + catalogue[1:]
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="exact fixed nine-path catalogue",
    ):
        v2.verify_v075_k7_shared_resource_semantics_v2(
            _envelope(), catalogue=forged_catalogue
        )

    contract = catalogue[0]
    wrong_source = replace(
        _source(contract),
        exact_source_kind=(
            v2.SharedResourceExactSourceKindV2.READ_TRANSFER_JOURNAL
        ),
    )
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="source kind differs",
    ):
        v2.verify_v075_k7_shared_resource_semantics_v2(
            _envelope((wrong_source,))
        )


def test_shared_resolution_is_privately_issued_and_not_a_counter_record() -> None:
    result = v2.verify_v075_k7_shared_resource_semantics_v2(_envelope())
    row = result.resolutions[0]
    kwargs = {name: getattr(row, name) for name in row.__slots__}
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="caller-minted",
    ):
        v2.SharedResourceResolutionV2(object(), **kwargs)
    assert not hasattr(v2, "CounterRecordV6")
    assert not hasattr(v2, "materialize_counter_records_v6")


def test_envelope_rejects_crossed_identity_and_catalogue() -> None:
    contract = v2.official_shared_resource_resolution_catalogue_v2()[0]
    crossed = replace(_source(contract), occurrence_id=_cid(999))
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="crossed its envelope identity",
    ):
        _envelope((crossed,))
    with pytest.raises(
        v2.ConstructionSharedResourceResolutionV2Error,
        match="fixed nine-path catalogue",
    ):
        replace(_envelope(), catalogue_fingerprint="f" * 64)
