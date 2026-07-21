from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from acfqp.artifacts import (
    canonical_sha256,
    serialized_json_bytes,
    sha256_file,
)
from acfqp.phase3e_bundle_v1 import (
    BUNDLE_SCOPE,
    REMAINING_BLOCKERS,
    Phase3EBundleManifestV1,
    Phase3EBundleRoleV1,
    Phase3EBundleV1Error,
    VerifiedH2FailedPrefixBundleV1,
    recorded_work_from_dict_v1,
    recorded_work_to_dict_v1,
    verify_h2_failed_prefix_bundle_v1,
    write_h2_failed_prefix_bundle_v1,
)
from acfqp.phase3e_ids import (
    PHASE3E_BUNDLE_MANIFEST_DOMAIN,
    canonical_json_bytes,
    content_id,
)
from acfqp.phase3e_model_only_executor_v1 import (
    ModelOnlyExecutionRequestV1,
    ModelOnlyQueryExecutionV1,
    execute_model_only_query_v1,
    model_only_execution_request_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    RAPMSourceLeaseV1,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


@pytest.fixture(scope="module")
def h2_bundle(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    request = model_only_execution_request_v1(source)
    execution = execute_model_only_query_v1(source)
    bundle = tmp_path_factory.mktemp("phase3e-h2-prefix") / "bundle"
    write_h2_failed_prefix_bundle_v1(
        bundle,
        source_bundle=PHASE3C,
        request=request,
        execution=execution,
    )
    return bundle


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _resign_bundle_manifest(bundle: Path, document: dict) -> None:
    payload = {
        key: value
        for key, value in document.items()
        if key != "phase3e_bundle_manifest_id"
    }
    document["phase3e_bundle_manifest_id"] = content_id(
        PHASE3E_BUNDLE_MANIFEST_DOMAIN, payload
    )
    raw = canonical_json_bytes(document)
    (bundle / "manifest.json").write_bytes(raw)
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(bundle / 'manifest.json')}  manifest.json\n",
        encoding="ascii",
    )


def _update_entry_bytes(bundle: Path, relative_path: str, document: dict) -> None:
    raw = canonical_json_bytes(document)
    (bundle / relative_path).write_bytes(raw)
    manifest = _load(bundle / "manifest.json")
    entry = next(
        row for row in manifest["entries"] if row["relative_path"] == relative_path
    )
    entry["sha256"] = sha256_file(bundle / relative_path)
    entry["size_bytes"] = len(raw)
    _resign_bundle_manifest(bundle, manifest)


def _copy_bundle(source: Path, target: Path) -> Path:
    shutil.copytree(source, target)
    return target


def _reseal_phase3c_manifest(bundle: Path, changed_path: str) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = _load(manifest_path)
    record = next(row for row in manifest["files"] if row["path"] == changed_path)
    target = bundle / changed_path
    record["bytes"] = target.stat().st_size
    record["sha256"] = sha256_file(target)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    manifest_path.write_bytes(serialized_json_bytes(manifest))
    (bundle / "manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  manifest.json\n", encoding="ascii"
    )


def test_h2_failed_prefix_bundle_replays_without_runtime_authority(
    h2_bundle: Path,
    tmp_path: Path,
) -> None:
    verified = verify_h2_failed_prefix_bundle_v1(
        h2_bundle, source_bundle=PHASE3C
    )
    assert type(verified) is VerifiedH2FailedPrefixBundleV1
    assert not isinstance(verified.execution_artifact, ModelOnlyQueryExecutionV1)
    assert verified.manifest.bundle_scope == BUNDLE_SCOPE
    assert verified.manifest.model_only_outcome == "FAIL"
    assert verified.manifest.selected_route_status == "NOT_RUN"
    assert verified.manifest.terminal_status == "NOT_RUN"
    assert verified.manifest.occurrence_closure_status == "NOT_RUN"
    assert verified.manifest.remaining_blockers == REMAINING_BLOCKERS
    assert verified.manifest.official_execution_allowed is False
    assert verified.execution_artifact.model_only_result.ground_binding_required
    assert {entry.role for entry in verified.manifest.entries} == set(
        Phase3EBundleRoleV1
    )

    work_document = recorded_work_to_dict_v1(
        verified.recorded_work,
        expected_scope=verified.recorded_work.actual_projection_proof.work_scope,
    )
    assert (
        recorded_work_from_dict_v1(
            work_document,
            expected_scope=verified.recorded_work.actual_projection_proof.work_scope,
        )
        == verified.recorded_work
    )
    with pytest.raises(Phase3EBundleV1Error, match="authenticated H2 failed prefix"):
        write_h2_failed_prefix_bundle_v1(
            tmp_path / "transport-cannot-mint",
            source_bundle=PHASE3C,
            request=verified.request,
            execution=verified.execution_artifact,  # type: ignore[arg-type]
        )


def test_bundle_verifier_never_calls_portable_planner_or_solver(
    h2_bundle: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import acfqp.phase3e_model_only_v1 as model_only
    import acfqp.phase3e_rapm_consumer_v1 as consumer
    import acfqp.portable_planner as planner

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("independent bundle verifier invoked a planner/solver")

    monkeypatch.setattr(model_only, "run_phase3e_model_only_from_source_v1", forbidden)
    monkeypatch.setattr(consumer, "solve_portable_pareto", forbidden)
    monkeypatch.setattr(planner, "solve_portable_pareto", forbidden)

    verified = verify_h2_failed_prefix_bundle_v1(
        h2_bundle, source_bundle=PHASE3C
    )
    assert verified.execution_artifact.model_only_result.outcome.value == "FAIL"


def test_manifest_rejects_missing_cross_role_and_path_traversal(
    h2_bundle: Path,
) -> None:
    source = _load(h2_bundle / "manifest.json")

    missing = json.loads(json.dumps(source))
    missing["entries"].pop()
    with pytest.raises(Phase3EBundleV1Error, match="missing or extra"):
        Phase3EBundleManifestV1.from_dict(missing)

    cross_role = json.loads(json.dumps(source))
    cross_role["entries"][0]["role"] = "MODEL_ONLY_REQUEST"
    with pytest.raises(
        Phase3EBundleV1Error,
        match="role/schema/domain/path|incomplete or duplicated",
    ):
        Phase3EBundleManifestV1.from_dict(cross_role)

    traversal = json.loads(json.dumps(source))
    traversal["entries"][0]["relative_path"] = "../escape.json"
    with pytest.raises(Phase3EBundleV1Error, match="traversal"):
        Phase3EBundleManifestV1.from_dict(traversal)

    duplicate = json.loads(json.dumps(source))
    duplicate["entries"][1]["content_id"] = duplicate["entries"][0]["content_id"]
    with pytest.raises(Phase3EBundleV1Error, match="reuses one content ID"):
        Phase3EBundleManifestV1.from_dict(duplicate)


def test_bundle_rejects_tampered_or_unlisted_bytes(
    h2_bundle: Path, tmp_path: Path
) -> None:
    tampered = _copy_bundle(h2_bundle, tmp_path / "tampered")
    result_path = tampered / "model_only/result.json"
    result_path.write_bytes(result_path.read_bytes() + b" ")
    with pytest.raises(Phase3EBundleV1Error, match="byte digest mismatch"):
        verify_h2_failed_prefix_bundle_v1(tampered, source_bundle=PHASE3C)

    extra = _copy_bundle(h2_bundle, tmp_path / "extra")
    (extra / "unregistered.json").write_text("{}", encoding="ascii")
    with pytest.raises(Phase3EBundleV1Error, match="topology mismatch"):
        verify_h2_failed_prefix_bundle_v1(extra, source_bundle=PHASE3C)


def test_bundle_rejects_resigned_spliced_result_and_work(
    h2_bundle: Path, tmp_path: Path
) -> None:
    result_attack = _copy_bundle(h2_bundle, tmp_path / "result-attack")
    result_path = result_attack / "model_only/result.json"
    result_document = _load(result_path)
    result_document["ground_binding_required"] = False
    _update_entry_bytes(
        result_attack, "model_only/result.json", result_document
    )
    with pytest.raises(Phase3EBundleV1Error, match="standalone model-only result"):
        verify_h2_failed_prefix_bundle_v1(
            result_attack, source_bundle=PHASE3C
        )

    work_attack = _copy_bundle(h2_bundle, tmp_path / "work-attack")
    work_path = work_attack / "accounting/common_prefix_recorded_work.json"
    work_document = _load(work_path)
    work_document["work_vector"]["records"][0]["value"] += 1
    _update_entry_bytes(
        work_attack,
        "accounting/common_prefix_recorded_work.json",
        work_document,
    )
    with pytest.raises(Phase3EBundleV1Error, match="recorded-work transport"):
        verify_h2_failed_prefix_bundle_v1(work_attack, source_bundle=PHASE3C)


def test_self_consistent_forged_request_cannot_replace_phase3c_parent(
    h2_bundle: Path, tmp_path: Path
) -> None:
    attacked = _copy_bundle(h2_bundle, tmp_path / "forged-request")
    request_path = attacked / "model_only/request.json"
    original = _load(request_path)
    original_lease = RAPMSourceLeaseV1.from_dict(original["source_lease"])
    forged_lease = replace(
        original_lease,
        source_bundle_sha256="1" * 64,
    )
    forged_request = ModelOnlyExecutionRequestV1(
        forged_lease,
        original["portable_rapm_base64"],
        original["portable_query_base64"],
        model_only_execution_request_v1(
            load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
        ).regret_tolerance,
    )
    _update_entry_bytes(attacked, "model_only/request.json", forged_request.to_dict())
    manifest = _load(attacked / "manifest.json")
    request_entry = next(
        row for row in manifest["entries"] if row["role"] == "MODEL_ONLY_REQUEST"
    )
    request_entry["content_id"] = forged_request.request_id
    manifest["model_only_request_id"] = forged_request.request_id
    manifest["source_bundle_sha256"] = forged_lease.source_bundle_sha256
    manifest["source_lease_id"] = forged_lease.source_lease_id
    _resign_bundle_manifest(attacked, manifest)

    with pytest.raises(Phase3EBundleV1Error, match="verified Phase3C parent source"):
        verify_h2_failed_prefix_bundle_v1(attacked, source_bundle=PHASE3C)


def test_foreign_but_valid_phase3c_parent_is_rejected(
    h2_bundle: Path, tmp_path: Path
) -> None:
    foreign_parent = tmp_path / "foreign-phase3c"
    shutil.copytree(PHASE3C, foreign_parent)
    run_path = foreign_parent / "run.json"
    run = _load(run_path)
    run["started_at"] = "2099-01-01T00:00:00+00:00"
    run_path.write_bytes(serialized_json_bytes(run))
    _reseal_phase3c_manifest(foreign_parent, "run.json")

    # The parent is independently valid and semantically carries the same H2,
    # but its full bundle/manifest lease differs from the one in this bundle.
    foreign_source = load_phase3c_model_source_v1(
        foreign_parent, query_key=LOCAL_QUERY_KEY
    )
    original_source = load_phase3c_model_source_v1(
        PHASE3C, query_key=LOCAL_QUERY_KEY
    )
    assert foreign_source.model == original_source.model
    assert foreign_source.query == original_source.query
    assert foreign_source.lease != original_source.lease

    with pytest.raises(Phase3EBundleV1Error, match="verified Phase3C parent source"):
        verify_h2_failed_prefix_bundle_v1(
            h2_bundle, source_bundle=foreign_parent
        )
