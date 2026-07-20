from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil

import pytest

import acfqp.abstraction.quotient as quotient_module
import acfqp.aliased_safe_chain as aliased_module
import acfqp.build_coverage as coverage_module
import acfqp.phase3c as phase3c_module
import acfqp.portable as portable_module
from acfqp.build_coverage import SuiteBuildCoverage
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.frozen_phase3c import (
    FrozenPhase3CLoadError,
    FrozenPhase3CWorld,
    load_frozen_phase3c_world,
)
from acfqp.phase3c import Phase3CWorld, run_phase3c
from acfqp.portable import fraction_from_json


@pytest.fixture(scope="session")
def frozen_phase3c_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    bundle = tmp_path_factory.mktemp("frozen-phase3c-source") / "bundle"
    run_phase3c(bundle)
    return bundle


def _forbidden(name: str):
    def fail(*_args, **_kwargs):
        raise AssertionError(f"forbidden consumption-time call: {name}")

    return fail


def test_loader_binds_exact_source_without_any_builder_or_ground_step(
    frozen_phase3c_source: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_bytes = (frozen_phase3c_source / "build/portable_rapm.json").read_bytes()
    epoch_bytes = (frozen_phase3c_source / "build/epoch.json").read_bytes()

    monkeypatch.setattr(
        phase3c_module,
        "construct_phase3c_world",
        _forbidden("construct_phase3c_world"),
    )
    monkeypatch.setattr(
        aliased_module,
        "build_initial_partition",
        _forbidden("build_initial_partition"),
    )
    monkeypatch.setattr(
        quotient_module,
        "build_quotient_models",
        _forbidden("build_quotient_models"),
    )
    monkeypatch.setattr(
        portable_module,
        "build_portable_rapm",
        _forbidden("build_portable_rapm"),
    )
    monkeypatch.setattr(
        coverage_module,
        "transition_closure",
        _forbidden("transition_closure"),
    )
    monkeypatch.setattr(
        SuiteBuildCoverage,
        "from_queries",
        classmethod(_forbidden("SuiteBuildCoverage.from_queries")),
    )
    monkeypatch.setattr(
        G2048SafeChainKernel,
        "step",
        _forbidden("G2048SafeChainKernel.step"),
    )

    world = load_frozen_phase3c_world(frozen_phase3c_source)

    assert isinstance(world, FrozenPhase3CWorld)
    assert isinstance(world, Phase3CWorld)
    assert world.portable_rapm_source_bytes == model_bytes
    assert world.build_epoch_source_bytes == epoch_bytes
    assert world.portable_rapm_source_sha256 == hashlib.sha256(model_bytes).hexdigest()
    assert world.build_epoch_source_sha256 == hashlib.sha256(epoch_bytes).hexdigest()
    assert world.portable.model.model_id == world.build_epoch["portable_rapm_id"]
    assert world.portable.model.coverage_id == world.build_epoch["coverage_id"]
    assert len(world.coverage.covered_states) == 192
    assert len(world.partition.cell_ids) == 11
    assert len(world.models.nominal.entries) == 20
    assert len(world.models.envelope.entries) == 20
    assert world.binding_counters["structural_candidate_states_scanned"] == 4802
    assert world.binding_counters["portable_states_bound"] == 192
    assert world.binding_counters["kernel_step_calls"] == 0
    assert world.binding_counters["transition_closure_calls"] == 0
    assert world.binding_counters["partition_builder_calls"] == 0
    assert world.binding_counters["quotient_builder_calls"] == 0
    assert world.binding_counters["portable_rapm_builder_calls"] == 0


def test_loader_exposes_content_addressed_local_pre_audit_upper(
    frozen_phase3c_source: Path,
) -> None:
    world = load_frozen_phase3c_world(frozen_phase3c_source)
    row = world.local_pre_recovery_document
    payload = dict(row)
    audit_id = payload.pop("audit_id")

    from acfqp.artifacts import object_id

    assert audit_id == object_id(payload, "audit")
    assert row["query_key"] == "g2048.safe_chain.h2.delta05.local_recovery"
    assert row["ground_query_id"] == object_id(world.queries[1].query, "query")
    assert row["portable_model_id"] == world.portable.model.model_id
    assert world.unrestricted_reward_upper == fraction_from_json(
        row["unrestricted_reward_upper"]
    )
    assert world.unrestricted_reward_upper == Fraction(3, 64)
    assert world.source_run_document["status"] == "PHASE3C_LOCAL_RECOVERY_PASS"
    assert world.source_locality_document[
        "coverage_positive_probability_outcomes"
    ] == 576
    assert world.source_authorization_document[
        "authorized_state_action_count"
    ] == 40
    assert set(world.source_manifest_document["required_paths"]) == {
        record["path"] for record in world.source_manifest_document["files"]
    }


def test_loader_rejects_any_source_byte_tampering(
    frozen_phase3c_source: Path,
    tmp_path: Path,
) -> None:
    forged = tmp_path / "forged"
    shutil.copytree(frozen_phase3c_source, forged)
    epoch_path = forged / "build/epoch.json"
    epoch = json.loads(epoch_path.read_text(encoding="utf-8"))
    epoch["abstract_cells"] += 1
    epoch_path.write_text(json.dumps(epoch, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(FrozenPhase3CLoadError, match="artifact integrity failed"):
        load_frozen_phase3c_world(forged)


def test_loaded_registry_and_serialized_concretizer_are_ground_bound(
    frozen_phase3c_source: Path,
) -> None:
    world = load_frozen_phase3c_world(frozen_phase3c_source)
    adapter = world.portable.serialized_adapter()
    state = world.queries[1].query.initial_distribution[0][1]
    cell = world.partition.cell_of(state)
    labels = adapter.labels(world.kernel, state)

    assert labels == world.models.envelope.actions(cell)
    for label in labels:
        assert adapter.concretize(world.kernel, state, label) == world.adapter.concretize(
            world.kernel, state, label
        )
        assert world.models.envelope.concretizer(
            state, label
        ) == adapter.concretize(world.kernel, state, label)
    portable_query = world.portable.query_from_spec(world.queries[1].query)
    assert portable_query.model_id == world.portable.model.model_id
    assert portable_query.horizon == 2
