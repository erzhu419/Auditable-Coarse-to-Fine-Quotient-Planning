from __future__ import annotations

from pathlib import Path
import hashlib

import pytest

from acfqp import construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7 as finalizer


def test_fallback_adapter_rejects_changed_retained_input(tmp_path: Path) -> None:
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7Error,
        match="source binding retained predecessor changed",
    ):
        finalizer.run_full_ground_fallback_production_occurrence_v180r7(
            repository_root=Path(finalizer.__file__).resolve().parents[2],
            runtime_cas_root=tmp_path / "cas",
            output_directory=tmp_path / "output",
            binding_bytes=b"{}",
            snapshot_bytes=b"{}",
            transition_bytes=b"{}",
        )


def test_v6_registry_is_an_exact_semantic_subset_of_v9() -> None:
    source, target = finalizer._verify_registry_extension()  # noqa: SLF001
    assert len(source.required_paths) == 202
    assert len(target.by_path) == 269
    assert set(source.by_path) <= set(target.by_path)


def test_fallback_identity_and_route_chain_are_preregistered() -> None:
    assert len(finalizer.LOGICAL_OCCURRENCE_ID) == 64
    assert finalizer.QUERY_ORDINAL == 7
    assert tuple(finalizer._SCOPE_BY_ROUTE) == (  # noqa: SLF001
        finalizer.RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        finalizer.RouteKindEnum.LOCAL_ATTEMPT,
        finalizer.RouteKindEnum.DIRECT_FALLBACK,
    )


def test_record_to_record_lift_covers_all_v9_paths_without_summary() -> None:
    source = finalizer.registry_v6.official_counter_registry_v6()
    recorder_id = hashlib.sha256(b"v180r7-test-source-recorder").hexdigest()
    records = tuple(
        finalizer.CounterRecordV1.observe(source, path, 0, recorder_id=recorder_id)
        for path in source.required_paths
    )
    source_vector = finalizer.WorkVectorV1(
        source.registry_id,
        hashlib.sha256(b"v180r7-test-occurrence").hexdigest(),
        finalizer.RouteKindEnum.DIRECT_FALLBACK,
        records,
    )
    lifted = finalizer._lift_component(  # noqa: SLF001
        source_vector=source_vector,
        receipt_id=hashlib.sha256(b"v180r7-test-receipt").hexdigest(),
        finalizer_output_bytes=0,
    )
    target_vector = finalizer.WorkVectorV1.from_dict(
        lifted["v9_work_vector"],
        finalizer.registry_v9.official_counter_registry_v9(),
    )
    assert len(target_vector.records) == 269
    assert len(lifted["counter_lift_lineage"]) == 269
    assert sum(
        row["target_path_absent_from_source_vector_native_zero_observation"]
        for row in lifted["counter_lift_lineage"]
    ) == 67
    assert all(
        row["historical_summary_translation_used"] is False
        for row in lifted["counter_lift_lineage"]
    )
