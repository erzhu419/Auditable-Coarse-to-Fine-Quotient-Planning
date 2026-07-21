from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

import acfqp.phase3e_local_adapter_v1 as local_adapter
import acfqp.phase3e_selected_route_bundle_v1 as selected_route_bundle
from acfqp.phase3e_ground_handoff_v1 import open_ground_binding_after_failed_audit_v1
from acfqp.phase3e_model_failure_consumer_v1 import (
    MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS,
    prepare_phase3e_from_model_failure_v1,
    verify_and_mint_model_only_failed_prefix_accounting_authority_v1,
)
from acfqp.phase3e_model_failure_occurrence_v1 import run_prepared_model_failure_occurrence_v1
from acfqp.phase3e_model_failure_preparation_accounting_v1 import (
    PREPARATION_OCCURRENCE_CHARGE_STATUS,
)
from acfqp.phase3e_model_only_executor_v1 import (
    execute_model_only_query_v1,
    model_only_execution_request_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import LOCAL_QUERY_KEY, load_phase3c_model_source_v1
from acfqp.phase3e_sealed_executor_v1 import RuntimeFactoryCardinalityV1, RuntimeTreeCASV1
from acfqp.phase3e_selected_route_bundle_v1 import (
    REMAINING_BLOCKERS,
    SEMANTIC_CERTIFICATE_STATUS,
    VERIFICATION_STATUS,
    Phase3ESelectedRouteBundleV1Error,
    SelectedRouteBundleRoleV1,
    verify_h2_model_failure_local_closure_bundle_v1,
    write_h2_model_failure_local_closure_bundle_v1,
)
from acfqp.phase3e_ids import (
    MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN,
    SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN,
    canonical_json_bytes,
    content_id,
)
from acfqp.routing_v1 import TerminalCode


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _deterministic_inprocess_local_worker(
    capability,
    ground_slice,
    request,
    *,
    operational_no_full_replay=False,
    runtime_source_root=None,
):
    from acfqp.general_local_solver import solve_general_local_recovery

    assert operational_no_full_replay is True
    assert runtime_source_root is not None
    result = solve_general_local_recovery(capability, ground_slice, request).to_dict()
    return result, {
        "schema": "acfqp.test_only_inprocess_runtime_attestation.v1",
        "attestation_id": "test-only-inprocess-local-worker",
        "result_id": result["result_id"],
        "working_set_limit_bytes": 256 * 1024 * 1024,
    }


@pytest.fixture(scope="module")
def selected_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    request = model_only_execution_request_v1(source)
    execution = execute_model_only_query_v1(source)
    prefix = verify_and_mint_model_only_failed_prefix_accounting_authority_v1(
        execution, source=source
    )
    ground = open_ground_binding_after_failed_audit_v1(
        PHASE3C,
        model_only_result=execution.model_only_result,
        abstract_audit_authority=prefix.audit_authority,
    )
    runtime = tmp_path_factory.mktemp("selected-route-runtime")
    cas = RuntimeTreeCASV1((runtime / "cas").resolve())
    manifest = cas.snapshot_build_tree(ROOT / "src")
    cardinality = RuntimeFactoryCardinalityV1.from_manifest(manifest)
    prepared = prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )
    patch = pytest.MonkeyPatch()
    patch.setattr(
        local_adapter,
        "_run_fresh_general_solver",
        _deterministic_inprocess_local_worker,
    )
    try:
        closure = run_prepared_model_failure_occurrence_v1(prepared)
    finally:
        patch.undo()
    bundle = tmp_path_factory.mktemp("selected-route-bundle") / "bundle"
    write_h2_model_failure_local_closure_bundle_v1(
        bundle,
        source_bundle=PHASE3C,
        request=request,
        closure=closure,
    )
    return bundle


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _resign_manifest(bundle: Path, manifest: dict) -> None:
    payload = dict(manifest)
    payload.pop("selected_route_bundle_manifest_id", None)
    manifest["selected_route_bundle_manifest_id"] = content_id(
        SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN, payload
    )
    raw = canonical_json_bytes(manifest)
    (bundle / "manifest.json").write_bytes(raw)
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    (bundle / "manifest.sha256").write_text(
        f"{digest}  manifest.json\n", encoding="ascii"
    )


def _resign_entry(bundle: Path, relative: str, document: dict) -> None:
    import hashlib

    raw = canonical_json_bytes(document)
    (bundle / relative).write_bytes(raw)
    manifest = _load(bundle / "manifest.json")
    entry = next(row for row in manifest["entries"] if row["relative_path"] == relative)
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    entry["size_bytes"] = len(raw)
    _resign_manifest(bundle, manifest)


def test_selected_local_bundle_replays_accounting_routing_terminal_topology(
    selected_bundle: Path,
) -> None:
    verified = verify_h2_model_failure_local_closure_bundle_v1(
        selected_bundle, source_bundle=PHASE3C
    )
    assert verified.manifest.verification_status == VERIFICATION_STATUS
    assert verified.manifest.semantic_certificate_status == SEMANTIC_CERTIFICATE_STATUS
    assert verified.manifest.remaining_blockers == REMAINING_BLOCKERS
    assert tuple(REMAINING_BLOCKERS[:4]) == MODEL_FAILURE_CONSUMER_ACCOUNTING_BLOCKERS
    assert verified.manifest.official_execution_allowed is False
    assert verified.manifest.official_scalar_cost is None
    assert verified.manifest.official_N_break_even is None
    assert verified.terminal.terminal_code is TerminalCode.LOCAL_GROUND_RECOVERY
    assert verified.to_dict()["semantic_certificate_status"] == "NOT_MINTED_FROM_TRANSPORT"
    manifest = _load(selected_bundle / "manifest.json")
    identities = {
        row["name"]: row["content_id"] for row in manifest["identities"]
    }
    preparation = _load(selected_bundle / "accounting/preparation_accounting.json")
    trace = _load(selected_bundle / "accounting/preparation_trace.json")
    incremental = _load(
        selected_bundle / "accounting/preparation_incremental_work.json"
    )
    aggregate = _load(
        selected_bundle / "accounting/preparation_aggregate_work.json"
    )
    assert len(manifest["entries"]) == 54
    assert preparation["occurrence_charge_status"] == (
        PREPARATION_OCCURRENCE_CHARGE_STATUS
    )
    assert trace["post_decision_point_component"] is True
    assert preparation["trace_id"] == trace["model_failure_preparation_trace_id"]
    assert preparation["preparation_work_vector_id"] == incremental["work_vector"][
        "work_vector_id"
    ]
    assert preparation["aggregate_work_vector_id"] == aggregate["work_vector"][
        "work_vector_id"
    ]
    assert identities["preparation_accounting_id"] == preparation[
        "model_failure_preparation_accounting_id"
    ]
    assert identities["preparation_trace_id"] == preparation["trace_id"]
    assert _load(selected_bundle / "accounting/common_core_work.json") == _load(
        selected_bundle / "accounting/failed_prefix_work.json"
    )
    occurrence = _load(
        selected_bundle / "accounting/occurrence_work_aggregate.json"
    )
    occurrence_raw_ids = {
        raw["work_vector_id"]
        for component in occurrence["component_refs"]
        for raw in component["raw_work_refs"]
    }
    assert preparation["preparation_work_vector_id"] not in occurrence_raw_ids
    assert preparation["aggregate_work_vector_id"] not in occurrence_raw_ids


@pytest.mark.parametrize("attack", ["missing", "extra", "symlink"])
def test_selected_bundle_rejects_topology_attacks(
    selected_bundle: Path,
    tmp_path: Path,
    attack: str,
) -> None:
    target = tmp_path / "bundle"
    shutil.copytree(selected_bundle, target)
    if attack == "missing":
        (target / "terminal" / "terminal.json").unlink()
    elif attack == "extra":
        (target / "unexpected.json").write_text("{}", encoding="utf-8")
    else:
        path = target / "routing" / "decision.json"
        path.unlink()
        path.symlink_to(target / "routing" / "local_upper.json")
    with pytest.raises(Phase3ESelectedRouteBundleV1Error, match="topology|symlink|regular"):
        verify_h2_model_failure_local_closure_bundle_v1(target, source_bundle=PHASE3C)


@pytest.mark.parametrize(
    ("attack", "message"),
    (
        ("same_bytes_replacement", "changed or was replaced"),
        ("symlink_replacement", "changed or was replaced"),
        ("growth", "grew during pinned read"),
        ("truncation", "truncated during pinned read"),
    ),
)
def test_descriptor_pinned_read_rejects_deterministic_mid_read_attacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
    message: str,
) -> None:
    root = tmp_path / "bundle"
    path = root / "routing" / "decision.json"
    path.parent.mkdir(parents=True)
    original = b'{"stable":"bundle bytes"}\n'
    path.write_bytes(original)
    displaced = tmp_path / f"displaced-{attack}.json"
    injected = False
    attack_stage = (
        "after_exact_read"
        if attack in {"same_bytes_replacement", "symlink_replacement"}
        else "after_initial_fstat"
    )

    def inject(
        stage: str,
        observed_path: Path,
        relative: str,
        _descriptor: int,
    ) -> None:
        nonlocal injected
        if injected or stage != attack_stage:
            return
        assert relative == "routing/decision.json"
        assert observed_path == path
        injected = True
        if attack == "same_bytes_replacement":
            path.replace(displaced)
            path.write_bytes(original)
        elif attack == "symlink_replacement":
            path.replace(displaced)
            path.symlink_to(displaced)
        elif attack == "growth":
            with path.open("ab") as stream:
                stream.write(b"forged growth")
        else:
            path.write_bytes(original[:-3])

    monkeypatch.setattr(
        selected_route_bundle,
        "_DESCRIPTOR_READ_TEST_HOOK_V1",
        inject,
    )
    with pytest.raises(Phase3ESelectedRouteBundleV1Error, match=message):
        selected_route_bundle._read_regular(root, "routing/decision.json")
    assert injected is True


def test_selected_bundle_rejects_resigned_route_decision_splice(
    selected_bundle: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "bundle"
    shutil.copytree(selected_bundle, target)
    path = "routing/decision.json"
    document = _load(target / path)
    document["selected_upper_id"] = document["fallback_upper_id"]
    # The attacker can update byte hashes and the outer manifest, but cannot
    # make the inner content-addressed route decision replay.
    _resign_entry(target, path, document)
    with pytest.raises(Phase3ESelectedRouteBundleV1Error, match="typed replay|route-decision|decision"):
        verify_h2_model_failure_local_closure_bundle_v1(target, source_bundle=PHASE3C)


def test_selected_bundle_rejects_cross_role_bytes_even_when_outer_hashes_are_resigned(
    selected_bundle: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "bundle"
    shutil.copytree(selected_bundle, target)
    source = _load(target / "routing" / "fallback_cardinality.json")
    _resign_entry(target, "routing/local_cardinality.json", source)
    with pytest.raises(Phase3ESelectedRouteBundleV1Error, match="spliced|identity|upper"):
        verify_h2_model_failure_local_closure_bundle_v1(target, source_bundle=PHASE3C)


def test_selected_bundle_rejects_preparation_claimed_as_occurrence_charged(
    selected_bundle: Path,
    tmp_path: Path,
) -> None:
    target = tmp_path / "bundle"
    shutil.copytree(selected_bundle, target)
    path = "accounting/preparation_accounting.json"
    document = _load(target / path)
    document["occurrence_charge_status"] = "OCCURRENCE_CHARGED"
    _resign_entry(target, path, document)
    with pytest.raises(
        Phase3ESelectedRouteBundleV1Error,
        match="preparation accounting status|occurrence",
    ):
        verify_h2_model_failure_local_closure_bundle_v1(
            target, source_bundle=PHASE3C
        )


@pytest.mark.parametrize(
    ("field_name", "forged_value", "message"),
    (
        (
            "source_accounting_status",
            "FORGED_OFFICIAL_STATUS",
            "closure summary status",
        ),
        (
            "failed_prefix_accounting_authority_id",
            "a" * 64,
            "closure summary topology was spliced",
        ),
    ),
)
def test_selected_bundle_rejects_resigned_closure_source_binding_splices(
    selected_bundle: Path,
    tmp_path: Path,
    field_name: str,
    forged_value: str,
    message: str,
) -> None:
    target = tmp_path / "bundle"
    shutil.copytree(selected_bundle, target)
    relative_path = "terminal/closure.json"
    path = target / relative_path
    document = _load(path)
    document[field_name] = forged_value
    payload = dict(document)
    payload.pop("model_failure_occurrence_closure_id")
    closure_id = content_id(
        MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN,
        payload,
    )
    document["model_failure_occurrence_closure_id"] = closure_id
    raw = canonical_json_bytes(document)
    path.write_bytes(raw)

    manifest = _load(target / "manifest.json")
    entry = next(
        row
        for row in manifest["entries"]
        if row["role"] == SelectedRouteBundleRoleV1.CLOSURE_SUMMARY.value
    )
    entry["content_id"] = closure_id
    entry["sha256"] = hashlib.sha256(raw).hexdigest()
    entry["size_bytes"] = len(raw)
    identity = next(
        row for row in manifest["identities"] if row["name"] == "closure_id"
    )
    identity["content_id"] = closure_id
    _resign_manifest(target, manifest)

    with pytest.raises(Phase3ESelectedRouteBundleV1Error, match=message):
        verify_h2_model_failure_local_closure_bundle_v1(
            target, source_bundle=PHASE3C
        )


def test_selected_bundle_role_paths_are_fixed(selected_bundle: Path) -> None:
    manifest = _load(selected_bundle / "manifest.json")
    roles = {row["role"] for row in manifest["entries"]}
    assert roles == {role.value for role in SelectedRouteBundleRoleV1}
    assert len(manifest["entries"]) == len(SelectedRouteBundleRoleV1)
