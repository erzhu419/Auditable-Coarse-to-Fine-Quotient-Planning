from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as subject
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_heldout_cross_structural_campaign_v1 import (
    child_campaigns,
)


@pytest.fixture(scope="module")
def catalogue(child_campaigns):
    return subject.build_heldout_reusable_model_catalogue_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
    )


def test_domains_surface_and_import_boundary_are_narrow() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 3
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutReusableModelCatalogueV1Error",
        "HeldoutReusableModelCatalogueEntryV1",
        "HeldoutReusableModelCatalogueV1",
        "HeldoutReusableModelSelectionV1",
        "LOCAL_DOMAINS",
        "build_heldout_reusable_model_catalogue_v1",
        "build_heldout_reusable_model_catalogue_entry_v1",
        "build_heldout_reusable_model_catalogue_snapshot_v1",
        "select_heldout_reusable_model_v1",
        "verify_heldout_reusable_model_catalogue_v1",
    }
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    forbidden = (
        "checkpoint_recertification_v1",
        "overlay_abstract_reuse_v1",
        "abstract_campaign_v1",
        "ground",
        "exact_evaluation",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_catalogue_retains_two_distinct_independently_verified_models(
    catalogue,
) -> None:
    verified = subject.verify_heldout_reusable_model_catalogue_v1(catalogue)
    assert [entry.family_key for entry in verified.entries] == ["W5", "K6"]
    assert [entry.target_context_key for entry in verified.entries] == [
        "opaque_graph_w5_v0",
        "opaque_graph_k6_v0",
    ]
    assert [entry.target_vertex_count for entry in verified.entries] == [5, 6]
    assert len({entry.context_id for entry in verified.entries}) == 2
    assert len({entry.topology_id for entry in verified.entries}) == 2
    assert len({entry.source_overlay_id for entry in verified.entries}) == 2
    assert len({entry.quotient_model_id for entry in verified.entries}) == 2
    assert all(
        entry.to_document()["fresh_zero_ground_abstract_reuse_verified"] is True
        for entry in verified.entries
    )


@pytest.mark.parametrize(
    ("context_key", "family_key"),
    (
        ("opaque_graph_w5_v0", "W5"),
        ("opaque_graph_k6_v0", "K6"),
    ),
)
def test_exact_structural_identity_selects_only_its_own_model(
    catalogue,
    context_key: str,
    family_key: str,
) -> None:
    context = observer.public_context_by_key_v1(context_key)
    selected = subject.select_heldout_reusable_model_v1(catalogue, context)
    entry = next(item for item in catalogue.entries if item.family_key == family_key)
    document = selected.to_document()
    assert document["selection_outcome"] == "EXACT_MODEL_MATCH"
    assert document["selected_model_catalogue_entry_id"] == entry.entry_id
    assert document["selected_quotient_model_id"] == entry.quotient_model_id
    assert document["selected_source_overlay_id"] == entry.source_overlay_id
    assert document["cross_structural_model_transfer_attempted"] is False
    assert document["fresh_ground_or_observer_event_count"] == 0
    assert document["plan_certificate_issued"] is False


def test_registered_nearby_topology_is_a_typed_model_miss(catalogue) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_k6_minus_edge_v0")
    selected = subject.select_heldout_reusable_model_v1(catalogue, context)
    document = selected.to_document()
    assert document["selection_outcome"] == "MODEL_MISS"
    assert document["requested_vertex_count"] == 6
    assert document["selected_model_catalogue_entry_id"] is None
    assert document["selected_quotient_model_id"] is None
    assert document["selected_source_overlay_id"] is None
    assert document["cross_structural_model_transfer_attempted"] is False
    assert document["local_ground_recovery_authorized_here"] is False
    assert document["direct_fallback_executed_here"] is False
    assert document["plan_certificate_issued"] is False


def test_immutable_partial_snapshot_misses_until_exact_entry_is_promoted(
    child_campaigns,
) -> None:
    w5_entry = subject.build_heldout_reusable_model_catalogue_entry_v1(
        "W5", child_campaigns["W5"]["reuse_bytes"]
    )
    initial = subject.build_heldout_reusable_model_catalogue_snapshot_v1(
        (w5_entry,)
    )
    initial_document = initial.to_document()
    assert initial_document["registered_model_count"] == 1
    assert initial_document["registered_structural_context_keys"] == [
        "opaque_graph_w5_v0"
    ]
    miss = subject.select_heldout_reusable_model_v1(
        initial,
        observer.public_context_by_key_v1("opaque_graph_k6_v0"),
    )
    assert miss.outcome == "MODEL_MISS"

    k6_entry = subject.build_heldout_reusable_model_catalogue_entry_v1(
        "K6", child_campaigns["K6"]["reuse_bytes"]
    )
    promoted = subject.build_heldout_reusable_model_catalogue_snapshot_v1(
        (w5_entry, k6_entry)
    )
    hit = subject.select_heldout_reusable_model_v1(
        promoted,
        observer.public_context_by_key_v1("opaque_graph_k6_v0"),
    )
    assert promoted.catalogue_id != initial.catalogue_id
    assert promoted.to_document()["registered_model_count"] == 2
    assert hit.outcome == "EXACT_MODEL_MATCH"
    assert hit.selected_entry_id == k6_entry.entry_id


def test_selection_does_not_replay_model_or_touch_observer(
    catalogue,
    monkeypatch,
) -> None:
    context = observer.public_context_by_key_v1("opaque_graph_w5_v0")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("selection opened a model verifier or observer")

    monkeypatch.setattr(
        subject.w5_verifier_v1,
        "verify_heldout_overlay_abstract_reuse_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        subject.k6_verifier_v1,
        "verify_heldout_k6_overlay_abstract_reuse_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        observer,
        "open_target_local_transition_stream_v1",
        forbidden,
    )
    selected = subject.select_heldout_reusable_model_v1(catalogue, context)
    assert selected.outcome == "EXACT_MODEL_MATCH"


def test_crossed_reuse_bytes_are_rejected(child_campaigns) -> None:
    # A K6 payload cannot occupy the W5 catalogue slot even though both are H=2.
    with pytest.raises(
        (
            subject.ConstructionK7HeldoutReusableModelCatalogueV1Error,
            ValueError,
        )
    ):
        subject.build_heldout_reusable_model_catalogue_v1(
            w5_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
            k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        )


def test_entry_and_catalogue_mutations_are_rejected(catalogue) -> None:
    entry = catalogue.entries[0]
    original = entry.quotient_model_id
    try:
        object.__setattr__(entry, "quotient_model_id", catalogue.entries[1].quotient_model_id)
        with pytest.raises(subject.ConstructionK7HeldoutReusableModelCatalogueV1Error):
            subject.verify_heldout_reusable_model_catalogue_v1(catalogue)
    finally:
        object.__setattr__(entry, "quotient_model_id", original)
    subject.verify_heldout_reusable_model_catalogue_v1(catalogue)


def test_catalogue_claim_boundaries_remain_locked(catalogue) -> None:
    document = catalogue.to_document()
    assert document["selector_kind"] == "EXACT_CONTEXT_AND_TOPOLOGY_IDENTITY"
    assert document["nearby_structure_transfer_allowed"] is False
    assert document["model_miss_requires_new_construction_or_fallback"] is True
    assert document["persistent_storage_implemented"] is False
    assert document["official_execution_allowed"] is False
