from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
import shutil

import pytest

from acfqp.artifacts import (
    canonical_sha256,
    object_id,
    serialized_json_bytes,
    sha256_file,
    verify_artifact_bundle,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    RECOVERY_SELECTOR_ID,
    SELECTED_CONTINGENT_PLAN_DOMAIN,
    ModelOnlyRAPMSourceV1,
    Phase3ERAPMConsumerError,
    RAPMSourceLeaseV1,
    SelectedContingentPlanV1,
    _content_id,
    _stable_documents_for_semantic_hash,
    load_phase3c_model_source_v1,
    require_model_only_source_authority_v1,
    select_contingent_plan_v1,
)
from acfqp.portable import canonical_json
from acfqp.portable_planner import PortablePlanResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_BUNDLE = PROJECT_ROOT / "artifacts" / "phase3c"


def _reseal_manifest(bundle: Path, changed_paths: set[str]) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["files"]:
        if record["path"] not in changed_paths:
            continue
        path = bundle / record["path"]
        record["bytes"] = path.stat().st_size
        record["sha256"] = sha256_file(path)
    manifest["bundle_sha256"] = canonical_sha256(manifest["files"])
    manifest_path.write_bytes(serialized_json_bytes(manifest))
    (bundle / "manifest.sha256").write_text(
        sha256_file(manifest_path) + "  manifest.json\n", encoding="ascii"
    )


def _rewrite_run_semantic_identity(bundle: Path) -> None:
    run_path = bundle / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["semantic_hash"] = canonical_sha256(
        _stable_documents_for_semantic_hash(bundle)
    )
    payload = {
        field_name: value
        for field_name, value in run.items()
        if field_name not in {"run_id", "started_at", "finished_at"}
    }
    run["run_id"] = object_id(payload, "run")
    run_path.write_bytes(serialized_json_bytes(run))


def test_model_only_source_supports_both_queries_on_one_frozen_epoch() -> None:
    h1 = load_phase3c_model_source_v1(SOURCE_BUNDLE, query_key=ABSTRACT_QUERY_KEY)
    h2 = load_phase3c_model_source_v1(SOURCE_BUNDLE, query_key=LOCAL_QUERY_KEY)

    assert isinstance(h1, ModelOnlyRAPMSourceV1)
    assert h1.model.model_id == h2.model.model_id
    assert h1.build_epoch == h2.build_epoch
    assert h1.lease.legacy_build_epoch_id == h2.lease.legacy_build_epoch_id
    assert h1.query.horizon == 1
    assert h2.query.horizon == 2
    assert h1.lease.source_lease_id != h2.lease.source_lease_id
    assert hashlib.sha256(h1.portable_rapm_source_bytes).hexdigest() == (
        h1.lease.portable_rapm_sha256
    )
    assert h1.portable_query_source_bytes.decode("utf-8") == canonical_json(
        h1.query.to_dict()
    )
    assert RAPMSourceLeaseV1.from_dict(h1.lease.to_dict()) == h1.lease


def test_contingent_selection_certifies_h1_and_registers_h2_recovery_policy() -> None:
    h1_source = load_phase3c_model_source_v1(
        SOURCE_BUNDLE, query_key=ABSTRACT_QUERY_KEY
    )
    h2_source = load_phase3c_model_source_v1(
        SOURCE_BUNDLE, query_key=LOCAL_QUERY_KEY
    )

    h1 = select_contingent_plan_v1(h1_source)
    h2 = select_contingent_plan_v1(h2_source)

    assert h1.nominal_query_feasible is True
    assert h1.proposal_source == "nominal_constrained_selection"
    assert h1.proposal.expected_reward.numerator == 1
    assert h1.proposal.expected_reward.denominator == 32
    assert h1.proposal.failure_probability == 0

    assert h2.nominal_query_feasible is False
    assert h2.selector_id == RECOVERY_SELECTOR_ID
    assert h2.proposal_source == (
        "max_reward_then_min_risk_then_policy_signature_for_certificate_recovery"
    )
    h2_result = PortablePlanResult.from_dict(
        h2.planner_result, model=h2_source.model, query=h2_source.query
    )
    assert h2.proposal == min(
        h2_result.frontier,
        key=lambda point: (
            -point.expected_reward,
            point.failure_probability,
            point.policy.signature(),
        ),
    )
    assert h2.proposal.expected_reward.numerator == 3
    assert h2.proposal.expected_reward.denominator == 64
    assert h2.proposal.failure_probability.numerator == 21187
    assert h2.proposal.failure_probability.denominator == 80000

    assert SelectedContingentPlanV1.from_dict(
        h1.to_dict(), source=h1_source
    ) == h1
    assert SelectedContingentPlanV1.from_dict(
        h2.to_dict(), source=h2_source
    ) == h2


def test_planning_succeeds_when_ground_loader_and_fixture_are_poisoned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.domains as domains
    import acfqp.frozen_phase3c as frozen_phase3c
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ground-domain access occurred before abstract audit")

    monkeypatch.setattr(domains, "safe_chain_fixture", forbidden)
    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)

    source = consumer.load_phase3c_model_source_v1(
        SOURCE_BUNDLE, query_key=LOCAL_QUERY_KEY
    )
    plan = consumer.select_contingent_plan_v1(source)
    assert plan.nominal_query_feasible is False

    tree = ast.parse(inspect.getsource(consumer))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.domains" not in imported_modules
    assert "acfqp.frozen_phase3c" not in imported_modules
    assert "acfqp.phase3c" not in imported_modules


def test_source_loader_recomputes_run_semantic_hash_not_only_manifest_hash(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "phase3c"
    shutil.copytree(SOURCE_BUNDLE, bundle)
    metrics_path = bundle / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["model_only_consumer_attack_probe"] = 1
    metrics_path.write_bytes(serialized_json_bytes(metrics))
    _reseal_manifest(bundle, {"metrics.json"})
    assert verify_artifact_bundle(bundle) == []

    with pytest.raises(Phase3ERAPMConsumerError, match="semantic hash mismatch"):
        load_phase3c_model_source_v1(bundle, query_key=ABSTRACT_QUERY_KEY)


def test_historical_expected_route_cannot_choose_the_new_contingent_plan(
    tmp_path: Path,
) -> None:
    original_source = load_phase3c_model_source_v1(
        SOURCE_BUNDLE, query_key=LOCAL_QUERY_KEY
    )
    original_plan = select_contingent_plan_v1(original_source)

    bundle = tmp_path / "phase3c"
    shutil.copytree(SOURCE_BUNDLE, bundle)
    registry_path = bundle / "workload" / "query_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for record in registry["records"]:
        if record["query_key"] == LOCAL_QUERY_KEY:
            record["expected_route"] = "ATTACKER_CHOOSES_ABSTRACT_CERTIFIED"
    registry_path.write_bytes(serialized_json_bytes(registry))
    _rewrite_run_semantic_identity(bundle)
    _reseal_manifest(bundle, {"workload/query_registry.json", "run.json"})
    assert verify_artifact_bundle(bundle) == []

    attacked_source = load_phase3c_model_source_v1(bundle, query_key=LOCAL_QUERY_KEY)
    attacked_plan = select_contingent_plan_v1(attacked_source)
    assert attacked_plan.nominal_query_feasible is False
    assert attacked_plan.selector_id == RECOVERY_SELECTOR_ID
    assert attacked_plan.proposal.to_dict() == original_plan.proposal.to_dict()
    # Provenance still changes because the lease binds the changed bundle.
    assert attacked_plan.source_lease_id != original_plan.source_lease_id


def test_selected_plan_rejects_a_resigned_selector_claim() -> None:
    source = load_phase3c_model_source_v1(SOURCE_BUNDLE, query_key=LOCAL_QUERY_KEY)
    plan = select_contingent_plan_v1(source)
    document = copy.deepcopy(plan.to_dict())
    document["proposal_source"] = "attacker_selected_historical_route"
    payload = dict(document)
    payload.pop("selected_contingent_plan_id")
    document["selected_contingent_plan_id"] = _content_id(
        SELECTED_CONTINGENT_PLAN_DOMAIN, payload
    )

    with pytest.raises(
        Phase3ERAPMConsumerError,
        match="does not match the deterministic selector",
    ):
        SelectedContingentPlanV1.from_dict(document, source=source)


def test_bundle_or_query_tampering_is_rejected_before_planning(tmp_path: Path) -> None:
    bundle = tmp_path / "phase3c"
    shutil.copytree(SOURCE_BUNDLE, bundle)
    model_path = bundle / "build" / "portable_rapm.json"
    model_path.write_bytes(model_path.read_bytes() + b" ")

    with pytest.raises(Phase3ERAPMConsumerError, match="integrity failed"):
        load_phase3c_model_source_v1(bundle, query_key=LOCAL_QUERY_KEY)

    with pytest.raises(Phase3ERAPMConsumerError, match="unsupported query key"):
        load_phase3c_model_source_v1(SOURCE_BUNDLE, query_key="not-registered")


def test_source_is_live_loader_authority_not_a_replaceable_dataclass_or_lease() -> None:
    source = load_phase3c_model_source_v1(
        SOURCE_BUNDLE, query_key=ABSTRACT_QUERY_KEY
    )
    assert require_model_only_source_authority_v1(source) is source
    assert RAPMSourceLeaseV1.from_dict(source.lease.to_dict()) == source.lease

    # The source has no public constructor, while its lease remains ordinary
    # serializable evidence.  Even copies that retain the private token are not
    # the exact object registered by the loader.
    with pytest.raises(Phase3ERAPMConsumerError, match="opaque live authority"):
        ModelOnlyRAPMSourceV1()
    with pytest.raises(Phase3ERAPMConsumerError, match="opaque live authority"):
        dataclasses.replace(source)
    for lost_authority in (copy.copy(source), copy.deepcopy(source)):
        with pytest.raises(
            Phase3ERAPMConsumerError,
            match="lost or never held live loader authority",
        ):
            select_contingent_plan_v1(lost_authority)

    with pytest.raises(Phase3ERAPMConsumerError, match="live .* authority"):
        select_contingent_plan_v1(source.lease)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "relative",
    (
        "manifest.json",
        "run.json",
        "build/portable_rapm.json",
        "build/epoch.json",
        "campaign/portable_queries.jsonl",
        "workload/query_registry.json",
    ),
)
def test_loader_rejects_concurrent_replacement_of_every_semantic_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    import acfqp.phase3e_rapm_consumer_v1 as consumer

    bundle = tmp_path / "phase3c"
    shutil.copytree(SOURCE_BUNDLE, bundle)
    target = bundle / relative
    original_read = consumer._read_source_bytes
    attacked = False

    def replace_after_snapshot_read(path: Path) -> bytes:
        nonlocal attacked
        source_bytes = original_read(path)
        if path == target and not attacked:
            attacked = True
            target.write_bytes(source_bytes + b" ")
        return source_bytes

    monkeypatch.setattr(consumer, "_read_source_bytes", replace_after_snapshot_read)
    with pytest.raises(
        Phase3ERAPMConsumerError,
        match="changed while loading",
    ):
        load_phase3c_model_source_v1(bundle, query_key=ABSTRACT_QUERY_KEY)
    assert attacked
