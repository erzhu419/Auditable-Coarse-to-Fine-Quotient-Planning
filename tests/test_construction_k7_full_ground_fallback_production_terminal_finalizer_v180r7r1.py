from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7r1 as finalizer
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(finalizer.__file__).resolve().parents[2]
INPUT_ROOT = ROOT / ".tmp" / "recovery-eligible-retained-v1"
TEST_PROTOCOL_ID = hashlib.sha256(b"v180r7r1-test-protocol").hexdigest()


def _retained_inputs() -> dict[str, bytes]:
    return {
        "binding_bytes": (INPUT_ROOT / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        "snapshot_bytes": (INPUT_ROOT / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        "transition_bytes": (INPUT_ROOT / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    }


def _zero_source_vectors() -> tuple[finalizer.WorkVectorV1, ...]:
    registry = finalizer.registry_v6.official_counter_registry_v6()
    rows = []
    for route in finalizer._SCOPE_BY_ROUTE:  # noqa: SLF001
        recorder_id = hashlib.sha256(
            b"v180r7r1-test-source-recorder\x00" + route.value.encode()
        ).hexdigest()
        records = tuple(
            finalizer.CounterRecordV1.observe(
                registry,
                path,
                0,
                recorder_id=recorder_id,
            )
            for path in registry.required_paths
        )
        rows.append(
            finalizer.WorkVectorV1(
                registry.registry_id,
                finalizer.LOGICAL_OCCURRENCE_ID,
                route,
                records,
            )
        )
    return tuple(rows)


def _source_bundle_for_receipt() -> SimpleNamespace:
    vectors = _zero_source_vectors()
    comparisons = tuple(
        SimpleNamespace(
            work_vector_id=row.work_vector_id,
            comparison_vector_id=hashlib.sha256(
                b"v180r7r1-test-comparison\x00" + row.route_kind.value.encode()
            ).hexdigest(),
        )
        for row in vectors
    )
    proofs = tuple(
        SimpleNamespace(
            work_vector_id=row.work_vector_id,
            actual_projection_proof_id=hashlib.sha256(
                b"v180r7r1-test-proof\x00" + row.route_kind.value.encode()
            ).hexdigest(),
        )
        for row in vectors
    )
    receipts = tuple(
        SimpleNamespace(receipt_id=hashlib.sha256(f"receipt-{index}".encode()).hexdigest())
        for index in range(9)
    )
    return SimpleNamespace(
        bundle_id=hashlib.sha256(b"v180r7r1-test-source-bundle").hexdigest(),
        work_vectors=vectors,
        comparison_vectors=comparisons,
        actual_projection_proofs=proofs,
        receipt_set=SimpleNamespace(receipts=receipts),
        fixed_point=SimpleNamespace(output_bytes=17),
    )


def _slot() -> dict[str, str]:
    return {
        "production_execution_slot_id": hashlib.sha256(b"slot").hexdigest(),
        "predecessor_occurrence_slot_id": hashlib.sha256(b"prior-slot").hexdigest(),
        "execution_nonce": hashlib.sha256(b"nonce").hexdigest(),
        "materialization_manifest_id": hashlib.sha256(b"manifest").hexdigest(),
    }


def _materialization_reference() -> dict[str, object]:
    return {
        "schema": "acfqp.full_ground_fallback_materialized_source_reference.v180r7r1",
        "materialization_manifest_id": hashlib.sha256(b"manifest").hexdigest(),
        "materialized_source_tree_id": hashlib.sha256(b"tree").hexdigest(),
        "source_closure_id": finalizer.EXPECTED_SOURCE_CLOSURE_ID,
        "construction_work": {"axis": "ONE_TIME_CONSTRUCTION"},
        "one_time_construction_axis": True,
        "charged_to_any_route_component": False,
    }


def test_repaired_fallback_rejects_changed_retained_input(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        finalizer,
        "_require_absent_path_with_real_parents",
        lambda *_args: None,
    )
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="source binding retained predecessor changed",
    ):
        finalizer.run_full_ground_fallback_production_occurrence_v180r7r1(
            repository_root=ROOT,
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


def test_repaired_identity_is_fresh_but_keeps_query_ordinal_seven() -> None:
    old_identity = hashlib.sha256(
        b"acfqp:v180r7:fresh-full-ground-fallback-occurrence\x00ordinal-7"
    ).hexdigest()
    assert finalizer.LOGICAL_OCCURRENCE_ID == hashlib.sha256(
        b"acfqp:v180r7r1:fresh-full-ground-fallback-occurrence\x00ordinal-7"
    ).hexdigest()
    assert finalizer.LOGICAL_OCCURRENCE_ID != old_identity
    assert finalizer.QUERY_ORDINAL == 7
    assert tuple(finalizer._SCOPE_BY_ROUTE) == (  # noqa: SLF001
        finalizer.RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        finalizer.RouteKindEnum.LOCAL_ATTEMPT,
        finalizer.RouteKindEnum.DIRECT_FALLBACK,
    )


def test_output_inventory_requires_exact_regular_role_files(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    expected: dict[str, bytes] = {}
    for index, name in enumerate(sorted(finalizer.EXPECTED_SOURCE_OUTPUT_FILENAMES)):
        raw = f"role-{index}".encode()
        expected[name] = raw
        (output / name).write_bytes(raw)
    inventory = finalizer._output_inventory(output)  # noqa: SLF001
    assert inventory == tuple(
        {
            "relative_path": name,
            "canonical_byte_count": len(expected[name]),
            "canonical_sha256": hashlib.sha256(expected[name]).hexdigest(),
        }
        for name in sorted(expected)
    )
    (output / "UNREGISTERED.json").write_bytes(b"{}")
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="output role set changed",
    ):
        finalizer._output_inventory(output)  # noqa: SLF001


def test_output_inventory_rejects_symlinked_role(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    for name in finalizer.EXPECTED_SOURCE_OUTPUT_FILENAMES:
        (output / name).write_bytes(b"{}")
    target = tmp_path / "BUSINESS_RESULT.target"
    target.write_bytes(b"{}")
    (output / "BUSINESS_RESULT.json").unlink()
    (output / "BUSINESS_RESULT.json").symlink_to(target)
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="output role set changed|not one regular file|opened safely",
    ):
        finalizer._output_inventory(output)  # noqa: SLF001


def test_output_inventory_rejects_same_length_change_during_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    for name in finalizer.EXPECTED_SOURCE_OUTPUT_FILENAMES:
        (output / name).write_bytes(b"original")
    first = output / sorted(finalizer.EXPECTED_SOURCE_OUTPUT_FILENAMES)[0]
    raw_read = finalizer.os.read
    fired = False

    def mutate_after_read(fd: int, count: int) -> bytes:
        nonlocal fired
        raw = raw_read(fd, count)
        if raw and not fired:
            fired = True
            first.write_bytes(b"forged!!")
        return raw

    monkeypatch.setattr(finalizer.os, "read", mutate_after_read)
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="output role changed while reading",
    ):
        finalizer._output_inventory(output)  # noqa: SLF001
    assert fired is True


def test_output_inventory_must_match_durable_role_commits(tmp_path: Path) -> None:
    inventory = (
        {
            "relative_path": "BUSINESS_RESULT.json",
            "canonical_byte_count": 2,
            "canonical_sha256": hashlib.sha256(b"{}").hexdigest(),
        },
    )
    matching = SimpleNamespace(
        output_commit=SimpleNamespace(
            role_commits=(
                SimpleNamespace(
                    filename="BUSINESS_RESULT.json",
                    byte_count=2,
                    bytes_sha256=hashlib.sha256(b"{}").hexdigest(),
                ),
            )
        )
    )
    finalizer._require_output_commit_matches_inventory(  # noqa: SLF001
        matching, inventory
    )
    matching.output_commit.role_commits[0].bytes_sha256 = hashlib.sha256(
        b"[]"
    ).hexdigest()
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="inventory changed from its durable commit",
    ):
        finalizer._require_output_commit_matches_inventory(  # noqa: SLF001
            matching, inventory
        )


def test_absent_output_boundary_rejects_dangling_leaf_and_symlink_parent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "real-parent").mkdir(parents=True)
    dangling = root / "real-parent" / "cas"
    dangling.symlink_to(root / "missing-target")
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="changed or already exists",
    ):
        finalizer._require_absent_path_with_real_parents(  # noqa: SLF001
            root, dangling, "real-parent/cas"
        )
    (root / "linked-parent").symlink_to(root / "real-parent", target_is_directory=True)
    through_link = root / "linked-parent" / "output"
    with pytest.raises(
        finalizer.ConstructionK7FullGroundFallbackFinalizerV180r7r1Error,
        match="output parent changed",
    ):
        finalizer._require_absent_path_with_real_parents(  # noqa: SLF001
            root, through_link, "linked-parent/output"
        )


@pytest.mark.parametrize("source_index", range(3))
def test_record_to_record_lift_covers_v9_without_materialization_charge(
    source_index: int,
) -> None:
    source_vector = _zero_source_vectors()[source_index]
    receipt_id = hashlib.sha256(b"v180r7r1-test-receipt").hexdigest()
    lifted = finalizer._lift_component(  # noqa: SLF001
        source_vector=source_vector,
        receipt_id=receipt_id,
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
        row["schema"] == "acfqp.full_ground_fallback_v9_lift_lineage.v180r7r1"
        and row["historical_summary_translation_used"] is False
        and row["materialized_source_construction_work_charged_to_this_route"]
        is False
        for row in lifted["counter_lift_lineage"]
    )
    first_lineage = dict(lifted["counter_lift_lineage"][0])
    lineage_id = first_lineage.pop("lineage_id")
    assert lineage_id == finalizer.domains.extension_content_id_v180r7r1(
        finalizer.domains.CONSTRUCTION_K7_FALLBACK_V9_LIFT_LINEAGE_V180R7R1_DOMAIN,
        first_lineage,
    )
    assert lifted["independent_route_component"] is True
    assert lifted["materialized_source_construction_work_charged_to_component"] is False


def test_finalizer_calls_only_public_runner_with_frozen_materialized_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        finalizer,
        "_require_absent_path_with_real_parents",
        lambda *_args: None,
    )
    materialized_root = tmp_path / "v180r7r1_materialized_source"
    reference = finalizer._MaterializedSourceEvidenceReferenceV180r7r1(  # noqa: SLF001
        materialized_root,
        _materialization_reference(),
    )
    monkeypatch.setattr(
        finalizer,
        "_load_materialized_source_evidence",
        lambda _repository_root: reference,
    )
    monkeypatch.setattr(
        finalizer,
        "_slot",
        lambda: finalizer._ExecutionProtocolSlotReferenceV180r7r1(  # noqa: SLF001
            TEST_PROTOCOL_ID,
            _slot(),
        ),
    )
    captured: dict[str, object] = {}

    class StopAfterPublicCall(RuntimeError):
        pass

    def stop_after_public_call(**kwargs: object) -> None:
        captured.update(kwargs)
        raise StopAfterPublicCall

    monkeypatch.setattr(
        finalizer.recovery,
        "run_recovery_eligible_occurrence_accounting_v1",
        stop_after_public_call,
    )
    with pytest.raises(StopAfterPublicCall):
        finalizer.run_full_ground_fallback_production_occurrence_v180r7r1(
            repository_root=ROOT,
            runtime_cas_root=tmp_path / "cas",
            output_directory=tmp_path / "output",
            **_retained_inputs(),
        )
    assert captured["repository_root"] == materialized_root
    assert captured["logical_occurrence_id"] == finalizer.LOGICAL_OCCURRENCE_ID
    assert captured["query_ordinal"] == 7
    assert captured["timeout_seconds"] == 7_200
    runner_names = set(
        finalizer.run_full_ground_fallback_production_occurrence_v180r7r1.__code__.co_names
    )
    assert "run_recovery_eligible_occurrence_accounting_v1" in runner_names
    assert "verify_recovery_eligible_occurrence_accounting_v1" not in runner_names
    source = inspect.getsource(finalizer)
    assert "construction_k7_all_path_production_execution_protocol_v180r3" not in source
    assert "construction_k7_domain_registry_extension_v180r7 as" not in source
    assert "production_terminal_finalizer_v180r7 import" not in source


def test_receipt_keeps_three_routes_and_materialization_axis_separate() -> None:
    source_bundle = _source_bundle_for_receipt()
    reference = _materialization_reference()
    inventory = tuple(
        {
            "relative_path": f"role-{index}.json",
            "canonical_byte_count": 1,
            "canonical_sha256": hashlib.sha256(bytes([index])).hexdigest(),
        }
        for index in range(8)
    )
    receipt = finalizer._build_occurrence_receipt(  # noqa: SLF001
        execution_protocol_id=TEST_PROTOCOL_ID,
        slot=_slot(),
        source_bundle=source_bundle,
        inventory=inventory,
        materialization_reference=reference,
    )
    assert receipt["schema"].endswith(".v180r7r1")
    assert receipt["fallback_execution_protocol_id"] == TEST_PROTOCOL_ID
    assert [row["route_kind"] for row in receipt["source_route_components"]] == [
        route.value for route in finalizer._SCOPE_BY_ROUTE  # noqa: SLF001
    ]
    assert all(
        row["independent_route_component"] is True
        for row in receipt["source_route_components"]
    )
    assert receipt["materialized_source_reference"] == reference
    assert receipt["retained_predecessor_input_facts"] == [
        dict(row) for row in finalizer.RETAINED_PREDECESSOR_INPUT_FACTS
    ]
    assert receipt["materialization_is_separate_one_time_construction_axis"] is True
    assert receipt["materialization_work_charged_to_any_route_component"] is False
    assert receipt["historical_summary_translation_used"] is False
    assert receipt["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert receipt["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert receipt["official_scalar_cost"] is None
    assert receipt["official_N_break_even"] is None
    assert receipt["official_execution_allowed"] is False
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("production_occurrence_receipt_id")
    assert receipt_id == finalizer.domains.extension_content_id_v180r7r1(
        finalizer.domains.CONSTRUCTION_K7_FALLBACK_OCCURRENCE_RECEIPT_V180R7R1_DOMAIN,
        receipt_payload,
    )


def test_terminal_fixed_point_repeats_separate_materialization_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_bundle = SimpleNamespace(
        fixed_point=SimpleNamespace(output_bytes=17),
        work_vectors=(
            SimpleNamespace(route_kind=route)
            for route in finalizer._SCOPE_BY_ROUTE  # noqa: SLF001
        ),
        to_document=lambda: {"source": "bundle"},
    )
    source_bundle.work_vectors = tuple(source_bundle.work_vectors)
    monkeypatch.setattr(
        finalizer,
        "_lift_component",
        lambda source_vector, receipt_id, finalizer_output_bytes: {
            "route_kind": source_vector.route_kind.value,
            "receipt_id": receipt_id,
            "finalizer_output_bytes": finalizer_output_bytes,
            "independent_route_component": True,
            "materialized_source_construction_work_charged_to_component": False,
        },
    )
    reference = _materialization_reference()
    receipt = {
        "production_occurrence_receipt_id": hashlib.sha256(b"receipt").hexdigest(),
        "materialized_source_reference": reference,
    }
    raw = finalizer._materialize_bundle(  # noqa: SLF001
        execution_protocol_id=TEST_PROTOCOL_ID,
        slot=_slot(),
        receipt=receipt,
        source_bundle=source_bundle,
        inventory=(),
        materialization_reference=reference,
    )
    document = loads_canonical_json(raw)
    assert document["schema"].endswith(".v180r7r1")
    assert document["fallback_execution_protocol_id"] == TEST_PROTOCOL_ID
    assert document["materialized_source_reference"] == reference
    assert document["materialization_work_charged_to_any_route_component"] is False
    assert document["finalizer_output_bytes"] == len(raw)
    assert document["output_bytes_fixed_point"] == 17 + len(raw)
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    terminal_payload = dict(document)
    terminal_id = terminal_payload.pop("production_terminal_bundle_id")
    assert terminal_id == finalizer.domains.extension_content_id_v180r7r1(
        finalizer.domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
        terminal_payload,
    )
