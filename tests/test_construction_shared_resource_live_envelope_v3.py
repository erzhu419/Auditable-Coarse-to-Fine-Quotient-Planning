from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_shared_resource_live_envelope_v3 as envelope_v3
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(b"acfqp:test:live-envelope:v3\x00" + label.encode()).hexdigest()


def _sources(*, crossed_path: str | None = None, nonce: str = "base") -> tuple[
    resolution_v2.SharedResourceLiveSourceV2, ...
]:
    rows = []
    runtime_id = _id("runtime")
    for index, contract in enumerate(
        resolution_v2.official_shared_resource_resolution_catalogue_v2()
    ):
        components = []
        for component_index, required in enumerate(contract.required_components):
            raw = canonical_json_bytes(
                {
                    "schema": required.source_schema_id,
                    "path": contract.path,
                    "component_key": required.component_key,
                    "nonce": nonce,
                }
            )
            components.append(
                resolution_v2.SharedResourceEvidenceComponentV2(
                    required.component_key,
                    required.source_schema_id,
                    _id(f"{nonce}:artifact:{index}:{component_index}"),
                    hashlib.sha256(raw).hexdigest(),
                    raw,
                )
            )
        rows.append(
            resolution_v2.SharedResourceLiveSourceV2(
                _id("foreign-runtime") if contract.path == crossed_path else runtime_id,
                _id("occurrence"),
                _id("attempt"),
                _id("decision"),
                _id("window"),
                _id(f"cutoff:{index}"),
                contract.path,
                contract.exact_source_kind,
                contract.required_provenance,
                100,
                101 + index,
                tuple(components),
            )
        )
    return tuple(rows)


def _freeze(
    sources: tuple[resolution_v2.SharedResourceLiveSourceV2, ...],
) -> envelope_v3.K7ProductionSharedResourceEnvelopeV3:
    return envelope_v3.freeze_k7_production_shared_resource_envelope_v3(
        production_runtime_envelope_id=_id("runtime"),
        occurrence_id=_id("occurrence"),
        route_attempt_id=_id("attempt"),
        decision_point_id=_id("decision"),
        measurement_window_id=_id("window"),
        production_runtime_replay_id=_id("runtime-replay"),
        terminal_closure_observation_id=_id("terminal-closure"),
        sources=sources,
    )


def test_nine_source_envelope_preserves_different_local_cutoffs() -> None:
    envelope = _freeze(_sources())
    assert tuple(row.source.path for row in envelope.bound_sources) == (
        resolution_v2.SHARED_RESOURCE_PATHS
    )
    assert len(
        {row.source.covered_cutoff_sequence for row in envelope.bound_sources}
    ) == 9
    document = envelope.to_document()
    assert document["identical_local_event_counts_required"] is False
    assert document["semantic_replayers_issued"] is False
    assert document["counter_records_issued"] is False
    assert document["formal_vector_authorized"] is False


def test_domains_are_central_and_role_separated() -> None:
    assert set(envelope_v3.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert len(set(envelope_v3.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 2


@pytest.mark.parametrize("variant", ("missing", "duplicate", "reordered"))
def test_exact_nine_path_set_is_required(variant: str) -> None:
    rows = list(_sources())
    if variant == "missing":
        rows.pop()
    elif variant == "duplicate":
        rows[-1] = rows[0]
    else:
        rows[0], rows[1] = rows[1], rows[0]
    with pytest.raises(
        envelope_v3.ConstructionSharedResourceLiveEnvelopeV3Error,
        match="ordered nine-source set|path contract",
    ):
        _freeze(tuple(rows))


def test_crossed_runtime_identity_is_rejected() -> None:
    path = resolution_v2.SHARED_RESOURCE_PATHS[4]
    with pytest.raises(
        envelope_v3.ConstructionSharedResourceLiveEnvelopeV3Error,
        match="crossed the runtime attempt",
    ):
        _freeze(_sources(crossed_path=path))


def test_bound_source_and_envelope_ids_change_with_component_bytes() -> None:
    first = _freeze(_sources(nonce="first"))
    second = _freeze(_sources(nonce="second"))
    assert first.envelope_id != second.envelope_id
    assert tuple(row.bound_source_id for row in first.bound_sources) != tuple(
        row.bound_source_id for row in second.bound_sources
    )


def test_public_constructors_cannot_mint_authority() -> None:
    source = _sources()[0]
    contract = resolution_v2.official_shared_resource_resolution_catalogue_v2()[0]
    with pytest.raises(
        envelope_v3.ConstructionSharedResourceLiveEnvelopeV3Error,
        match="caller-minted",
    ):
        envelope_v3.BoundSharedResourceSourceV3(
            object(),
            source,
            tuple(row.component_key for row in contract.required_components),
            tuple(row.source_schema_id for row in contract.required_components),
        )
