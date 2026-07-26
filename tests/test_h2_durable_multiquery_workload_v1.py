"""V0-056 preregistered durable H=2 multiquery workload regressions."""

from __future__ import annotations

import ast
import copy
from dataclasses import fields
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Callable

import pytest

import acfqp.h2_conditional_direct_ground_v1 as direct
import acfqp.h2_durable_action_local_recovery_v1 as recovery
import acfqp.h2_durable_multiquery_workload_v1 as workload
import acfqp.h2_durable_multiquery_workload_pins_v1 as pins
import acfqp.h2_query_family_model_v1 as model
from acfqp.phase3e_ids import canonical_json_bytes


ModelViolation = model.H2QueryFamilyInvariantViolation
WorkloadViolation = workload.DurableMultiQueryWorkloadInvariantViolation


@pytest.fixture(scope="module")
def campaign(tmp_path_factory):
    root = tmp_path_factory.mktemp("v0056-campaign") / "campaign"
    result = workload.run_registered_h2_durable_multiquery_workload_v1(root)
    return root, result


@pytest.fixture(scope="module")
def verification(campaign):
    root, result = campaign
    before = workload._snapshot_id(root, "CAMPAIGN")
    report = workload.verify_registered_h2_durable_multiquery_workload_v1(
        root, result
    )
    after = workload._snapshot_id(root, "CAMPAIGN")
    return report, before, after


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert type(document) is dict
    return document


def _write_canonical(path: Path, document: dict[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(document))


def _rehash(document: dict[str, Any], role: str, id_field: str) -> str:
    document[id_field] = model._content_id(
        role,
        {key: value for key, value in document.items() if key != id_field},
    )
    return document[id_field]


def _clone_exact(instance: Any, **changes: Any) -> Any:
    """Create an exact-class negative control without invoking post-init."""

    clone = object.__new__(type(instance))
    for item in fields(instance):
        object.__setattr__(
            clone,
            item.name,
            changes.get(item.name, getattr(instance, item.name)),
        )
    return clone


def _copy_warm_store(campaign, tmp_path: Path, name: str) -> Path:
    root, _result = campaign
    target = tmp_path / name
    shutil.copytree(root / "warm-query-facets", target)
    return target


def _copy_w0_store(campaign, tmp_path: Path, name: str) -> Path:
    root, _result = campaign
    target = tmp_path / name
    # Occurrence 1 is Q1, so its reset arm remains exactly W0.
    shutil.copytree(
        root / "c2-base-reset-controls" / "occurrence-01",
        target,
    )
    return target


def _latest_payload_and_commit(
    store: Path, expected_commit_id: str
) -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
    commit_path = store / "commits" / f"{expected_commit_id}.json"
    commit = _read_json(commit_path)
    payload_path = store / "blobs" / f"{commit['payload_id']}.json"
    return payload_path, _read_json(payload_path), commit_path, commit


def _replace_latest_store_generation(
    store: Path,
    expected_commit_id: str,
    mutator: Callable[[dict[str, Any]], None],
) -> str:
    """Fully re-address the latest payload and commit after an attack."""

    payload_path, payload, commit_path, commit = _latest_payload_and_commit(
        store, expected_commit_id
    )
    mutator(payload)
    _rehash(payload, "store_payload", "payload_id")
    payload_bytes = canonical_json_bytes(payload)
    commit["payload_id"] = payload["payload_id"]
    commit["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    commit["payload_size_bytes"] = len(payload_bytes)
    _rehash(commit, "store_commit", "commit_id")
    commit_bytes = canonical_json_bytes(commit)

    payload_path.unlink()
    commit_path.unlink()
    _write_canonical(
        store / "blobs" / f"{payload['payload_id']}.json", payload
    )
    _write_canonical(
        store / "commits" / f"{commit['commit_id']}.json", commit
    )
    assert canonical_json_bytes(commit) == commit_bytes
    return commit["commit_id"]


def _rehash_occurrence_result(document: dict[str, Any]) -> None:
    _rehash(document, "result", "result_id")


def _rehash_root(document: dict[str, Any]) -> None:
    _rehash(document, "root", "root_id")


def _rehash_certificate(document: dict[str, Any]) -> None:
    _rehash(document, "certificate", "certificate_id")


def test_registered_status_contract_and_preregistration_precede_source(
    campaign,
) -> None:
    root, result = campaign
    assert workload.CONTRACT_VERSION == "1.20.0"
    assert (
        workload.PROFILE_KEY
        == "lmb_h2_preregistered_durable_multiquery_workload_v0"
    )
    assert result.status == (
        "CERTIFIED_REGISTERED_H2_PREREGISTERED_"
        "DURABLE_MULTIQUERY_WORKLOAD_CONTROL"
    )
    assert result.events == workload.EXPECTED_CAMPAIGN_EVENTS
    assert result.events[0] == "WORKLOAD_PROTOCOL_FROZEN_BEFORE_SOURCE"
    assert result.events[1] == "V0055_SOURCE_STARTED_WITHOUT_WORKLOAD_INPUT"
    assert result.preregistration.frozen_before_source_promotion is True
    assert result.preregistration.source_artifact_ids_absent is True
    prereg_files = tuple((root / "preregistration").iterdir())
    source_files = tuple(
        path for path in (root / "source").rglob("*") if path.is_file()
    )
    assert len(prereg_files) == 2
    assert source_files
    assert max(path.stat().st_mtime_ns for path in prereg_files) <= min(
        path.stat().st_mtime_ns for path in source_files
    )
    prereg_text = canonical_json_bytes(
        result.preregistration.to_document()
    ).decode("utf-8")
    for forbidden in (
        result.source_result_id,
        result.source_c1_commit_id,
        result.source_c2_commit_id,
        result.source_failed_verification_id,
        result.source_ground_authorization_id,
    ):
        assert forbidden not in prereg_text
    assert workload.require_durable_multiquery_workload_result_v1(result) is result


def test_exact_source_hash_pins_and_canonical_result_mapping(campaign) -> None:
    _root, result = campaign
    assert workload._module_sha256(model) == (
        pins.EXPECTED_QUERY_FAMILY_MODULE_SHA256
    )
    assert workload._module_sha256(direct) == (
        pins.EXPECTED_CONDITIONAL_DIRECT_MODULE_SHA256
    )
    assert workload._module_sha256(recovery) == (
        pins.EXPECTED_V0055_RECOVERY_MODULE_SHA256
    )
    assert workload._file_sha256(Path(workload.__file__).resolve()) == (
        pins.EXPECTED_ORCHESTRATOR_MODULE_SHA256
    )
    assert workload._callable_sha256(
        model.launch_h2_query_family_occurrence_fresh_worker_v1
    ) == pins.EXPECTED_QUERY_LAUNCH_SOURCE_SHA256
    assert workload._callable_sha256(
        model.initialize_h2_query_family_w0_v1
    ) == pins.EXPECTED_QUERY_INITIALIZE_SOURCE_SHA256
    assert workload._callable_sha256(
        direct.run_h2_conditional_direct_ground_fresh_worker_v1
    ) == pins.EXPECTED_DIRECT_LAUNCH_SOURCE_SHA256
    assert workload._callable_sha256(
        recovery.run_registered_h2_durable_action_local_recovery_v1
    ) == pins.EXPECTED_SOURCE_RUN_SOURCE_SHA256
    workload._assert_source_pins()

    expected_result_ids = {
        name: value
        for name, value in pins.EXPECTED_CANONICAL_IDS.items()
        if name != "evaluation_replay_report"
    }
    assert workload._visible_canonical_result_ids(result) == expected_result_ids
    workload._assert_canonical_result_ids(result)
    assert set(pins.EXPECTED_CANONICAL_IDS) == {
        *expected_result_ids,
        "evaluation_replay_report",
    }
    assert all(
        type(value) is str
        and len(value) == 64
        and value != "0" * 64
        and int(value, 16) >= 0
        for value in pins.EXPECTED_CANONICAL_IDS.values()
    )


@pytest.mark.parametrize(
    ("authority_module", "attribute"),
    (
        (
            model,
            "launch_h2_query_family_occurrence_fresh_worker_v1",
        ),
        (
            direct,
            "run_h2_conditional_direct_ground_fresh_worker_v1",
        ),
        (
            recovery,
            "run_registered_h2_durable_action_local_recovery_v1",
        ),
    ),
    ids=("model", "direct", "source"),
)
def test_monkeypatched_execution_authorities_are_rejected(
    monkeypatch, authority_module, attribute
) -> None:
    original = getattr(authority_module, attribute)

    def substituted(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(authority_module, attribute, substituted)
    with pytest.raises(
        WorkloadViolation,
        match="source or callable identity changed",
    ):
        workload._assert_source_pins()


def test_exact_telemetry_commit_chain_and_claim_locks(campaign) -> None:
    _root, result = campaign
    telemetry = result.telemetry
    assert (
        telemetry.source_ground_calls,
        telemetry.warm_target_ground_calls,
        telemetry.reset_target_ground_calls,
        telemetry.direct_ground_calls,
    ) == (1, 0, 0, 10)
    assert (
        telemetry.source_process_launches,
        telemetry.warm_target_process_launches,
        telemetry.reset_target_process_launches,
        telemetry.direct_process_launches,
    ) == (3, 10, 10, 10)
    assert (
        telemetry.warm_query_facet_builder_calls,
        telemetry.warm_query_facet_identity_hits,
        telemetry.warm_fresh_query_roots,
    ) == (6, 174, 30)
    assert (
        telemetry.reset_query_facet_builder_calls,
        telemetry.reset_query_facet_identity_hits,
        telemetry.reset_fresh_query_roots,
    ) == (18, 162, 30)
    assert (
        telemetry.direct_catalogue_calls,
        telemetry.direct_policy_evaluations,
        telemetry.direct_optimizer_calls,
    ) == (10, 40, 10)
    assert (
        telemetry.w0_logical_lower_count,
        telemetry.w1_logical_lower_count,
        telemetry.w2_logical_lower_count,
        telemetry.final_persisted_query_facet_count,
        telemetry.persisted_query_root_count,
    ) == (18, 21, 24, 6, 0)

    chain = tuple(
        (
            item.before_commit_id,
            item.after_commit_id,
            item.logical_lower_count,
            item.value_builder_calls,
            item.identity_hits,
        )
        for item in result.warm_occurrences
    )
    assert chain[:3] == (
        (result.w0_commit_id, result.w0_commit_id, 18, 0, 18),
        (result.w0_commit_id, result.w1_commit_id, 21, 3, 15),
        (result.w1_commit_id, result.w2_commit_id, 24, 3, 15),
    )
    assert chain[3:] == (
        (result.w2_commit_id, result.w2_commit_id, 24, 0, 18),
    ) * 7
    locks = result.claim_locks
    assert locks.registered_finite_h2_multiquery_workload_claimed is True
    assert locks.lazy_query_facet_lookup_claimed is True
    assert locks.sample_efficiency_claimed is False
    assert locks.ground_transition_calls_are_samples is False
    assert locks.counter_registry_v1_complete_claimed is False
    assert locks.official_execution_allowed is False
    assert locks.official_scalar_cost is None
    assert locks.official_N_break_even is None


def test_typed_reset_initializations_bind_w0_and_observed_io(campaign) -> None:
    _root, result = campaign
    initializations = result.base_reset_initializations
    resets = result.base_reset_occurrences
    matched = result.matched_occurrences
    assert len(initializations) == len(resets) == len(matched) == 10
    assert all(
        type(item) is model.H2QueryFamilyInitializationV1
        for item in initializations
    )
    assert {
        item.initialization_id for item in initializations
    } == {
        "5aef24c26ac200c833df57dbea6cdacbdca03d46c2e399d22451132545d5229f"
    }
    assert all(
        initialization.commit.commit_id
        == reset.before_commit_id
        == result.w0_commit_id
        for initialization, reset in zip(
            initializations, resets, strict=True
        )
    )
    for initialization, reset, row in zip(
        initializations, resets, matched, strict=True
    ):
        assert row.base_reset_initialization.to_document() == (
            initialization.to_document()
        )
        assert row.base_reset.to_document() == reset.to_document()
        assert row.base_reset_trace.observed_query_store_read_bytes == (
            initialization.read_bytes + reset.store_read_bytes
        )
        assert row.base_reset_trace.observed_query_store_output_bytes == (
            initialization.output_bytes + reset.store_output_bytes
        )
        assert row.warm_trace.observed_query_store_read_bytes == (
            row.warm.store_read_bytes
        )
        assert row.warm_trace.observed_query_store_output_bytes == (
            row.warm.store_output_bytes
        )

    traces = (
        result.source_trace,
        result.promotion_trace,
        *(
            trace
            for row in matched
            for trace in (
                row.warm_trace,
                row.base_reset_trace,
                row.direct_trace,
            )
        ),
    )
    assert all(trace.query_store_io_complete is False for trace in traces)
    assert all(
        trace.full_counter_registry_complete is False for trace in traces
    )


def test_scoped_trace_cannot_claim_complete_query_store_io(campaign) -> None:
    _root, result = campaign
    forged = _clone_exact(
        result.matched_occurrences[0].base_reset_trace,
        query_store_io_complete=True,
    )
    with pytest.raises(
        WorkloadViolation,
        match="scoped accounting classification changed",
    ):
        forged.__post_init__()


@pytest.mark.parametrize(
    "attack",
    ("deleted", "replaced", "wrong_commit", "wrong_bytes"),
)
def test_reset_initialization_deletion_replacement_and_binding_attacks_fail(
    campaign, attack
) -> None:
    _root, result = campaign
    values = list(result.base_reset_initializations)
    if attack == "deleted":
        values.pop()
    elif attack == "replaced":
        values[3] = _clone_exact(
            values[3],
            source_lease_id="0" * 64,
        )
    elif attack == "wrong_commit":
        wrong_commit = _clone_exact(
            values[3].commit,
            payload_id="0" * 64,
        )
        assert wrong_commit.commit_id != result.w0_commit_id
        values[3] = _clone_exact(values[3], commit=wrong_commit)
    elif attack == "wrong_bytes":
        values[3] = _clone_exact(
            values[3],
            read_bytes=values[3].read_bytes + 1,
            output_bytes=values[3].output_bytes + 1,
        )
    else:  # pragma: no cover - parameter guard
        raise AssertionError(attack)

    forged = _clone_exact(
        result,
        base_reset_initializations=tuple(values),
    )
    with pytest.raises(WorkloadViolation):
        forged.__post_init__()


def test_model_only_fresh_worker_results_and_forbidden_import_boundary(
    campaign,
) -> None:
    _root, result = campaign
    for item in (*result.warm_occurrences, *result.base_reset_occurrences):
        assert item.process_launches == 1
        assert item.ground_transition_calls == 0
        assert item.fresh_root_builder_calls == 3
        assert item.matching_buffer_imported is False
        assert item.action_local_imported is False
        assert item.recovery_imported is False

    source = Path(model.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    assert "acfqp.domains.matching_buffer" not in imports
    assert "acfqp.h2_action_local_semantic_switch_v1" not in imports
    assert "acfqp.h2_durable_action_local_recovery_v1" not in imports
    command = model._worker_command(
        store_root=Path("/tmp/acfqp-v0056-test-only"),
        expected_commit_id="0" * 64,
        occurrence_index=1,
        output=Path("/tmp/acfqp-v0056-test-only.json"),
        parent_process_id=1,
    )
    assert command[1:4] == ("-I", "-s", "-B")


def test_lazy_lookup_never_calls_poison_builder_on_hit(
    campaign, tmp_path
) -> None:
    _root, result = campaign
    copied = _copy_warm_store(campaign, tmp_path, "warm-hit")
    occurrence = model.registered_h2_query_family_occurrence_v1(4)
    calls = 0

    def poison(*_args):
        nonlocal calls
        calls += 1
        raise AssertionError("cache hit reached value builder")

    resolved = model.resolve_h2_query_family_occurrence_v1(
        copied,
        result.w2_commit_id,
        occurrence,
        value_builder=poison,
    )
    assert calls == 0
    assert (resolved.value_builder_calls, resolved.identity_hits) == (0, 18)
    assert resolved.before_commit_id == resolved.after_commit_id
    assert resolved.certificate.certified is True


def test_lazy_lookup_calls_poison_builder_on_miss(campaign, tmp_path) -> None:
    _root, result = campaign
    copied = _copy_w0_store(campaign, tmp_path, "warm-miss")
    occurrence = model.registered_h2_query_family_occurrence_v1(2)

    class PoisonReached(RuntimeError):
        pass

    calls = 0

    def poison(*_args):
        nonlocal calls
        calls += 1
        raise PoisonReached

    with pytest.raises(PoisonReached):
        model.resolve_h2_query_family_occurrence_v1(
            copied,
            result.w0_commit_id,
            occurrence,
            value_builder=poison,
        )
    assert calls == 1
    # No miss work was committed after the builder failed.
    lease = model.load_verified_h2_query_family_store_v1(
        copied, result.w0_commit_id
    )
    assert (lease.commit.generation, lease.payload.persisted_facet_count) == (
        0,
        0,
    )


@pytest.mark.parametrize("query_index", (2, 3))
def test_independent_consumed_facets_and_selection_resolved_parent_ids(
    campaign, query_index
) -> None:
    root, result = campaign
    lease = model.load_verified_h2_query_family_store_v1(
        root / "warm-query-facets", result.w2_commit_id
    )
    query = result.protocol.query(query_index)
    addresses = model.QUERY_FACET_ADDRESSES[query_index]
    groups = tuple(
        lease.payload.facet_entries[offset : offset + 3]
        for offset in range(0, len(lease.payload.facet_entries), 3)
    )
    group = next(
        item
        for item in groups
        if model._facet_group_query_index(
            lease.payload.source_active_nodes, item
        )
        == query_index
    )
    entries = {entry.key.address: entry for entry in group}
    gate_addresses = addresses[:-1]
    selection_address = addresses[-1]
    selection = entries[selection_address]
    for address in gate_addresses:
        if address.startswith("REGRET_"):
            assert entries[address].key.consumed_facet_ids == (
                query.return_upper_facet_id,
                query.regret_facet_id,
            )
        else:
            assert address.startswith("RISK_")
            assert entries[address].key.consumed_facet_ids == (
                query.risk_facet_id,
            )
    assert selection.key.consumed_facet_ids == ()
    key_text = canonical_json_bytes(
        entries[gate_addresses[0]].key.to_document()
    ).decode("utf-8")
    assert query.query_id not in key_text
    assert result.protocol.protocol_id not in key_text
    assert result.source_result_id not in key_text
    assert result.source_c2_commit_id not in key_text

    source = {item.address: item for item in lease.payload.source_active_nodes}
    resolved = {**source, **entries}
    expected_selection_parents = (
        source["PLAN_N"].node_id,
        resolved["REGRET_N"].node_id,
        resolved["RISK_N"].node_id,
        source["COVERAGE_N"].node_id,
        source["PLAN_M"].node_id,
        resolved["REGRET_M"].node_id,
        resolved["RISK_M"].node_id,
        source["COVERAGE_M"].node_id,
    )
    assert selection.key.ordered_parent_node_ids == expected_selection_parents
    occurrence = result.warm_occurrences[
        1 if query_index == 2 else 2
    ]
    assert occurrence.certificate.selection_node_id == selection.node_id
    assert occurrence.fresh_roots[-1].selection_node_id == selection.node_id


def test_consumed_threshold_facets_are_independent_across_queries(
    campaign,
) -> None:
    _root, result = campaign
    q1, q2, q3 = result.protocol.queries
    assert q1.return_upper_facet_id == q2.return_upper_facet_id
    assert q2.return_upper_facet_id == q3.return_upper_facet_id
    assert len({q1.regret_facet_id, q2.regret_facet_id}) == 2
    assert q1.regret_facet_id == q3.regret_facet_id
    assert q1.risk_facet_id == q2.risk_facet_id
    assert q1.risk_facet_id != q3.risk_facet_id
    assert len(
        {
            q1.regret_facet_id,
            q2.regret_facet_id,
            q1.risk_facet_id,
            q3.risk_facet_id,
            q1.return_upper_facet_id,
        }
    ) == 5


def test_w0_contains_exact_full_semantic_source_projection(campaign) -> None:
    root, result = campaign
    source = model.load_verified_h2_query_family_source_c2_v1(
        root / "source" / "c2", result.source_c2_commit_id
    )
    w0 = model.load_verified_h2_query_family_store_v1(
        root / "c2-base-reset-controls" / "occurrence-01",
        result.w0_commit_id,
    )
    assert tuple(
        item.to_document() for item in w0.payload.source_active_nodes
    ) == tuple(item.to_document() for item in source.active_source_nodes)
    assert len(w0.payload.source_active_nodes) == 18
    assert all(item.node_document for item in w0.payload.source_active_nodes)
    assert {
        item.node_document["schema"]
        for item in w0.payload.source_active_nodes
    } == {"acfqp.action_indexed_proof_node.v1"}

    source_payload_path = (
        root
        / "source"
        / "c2"
        / "blobs"
        / f"{source.payload_id}.json"
    )
    source_payload = _read_json(source_payload_path)
    documents = {
        item["node_id"]: item
        for item in source_payload["lower_node_documents"]
    }
    projected = {
        binding["address"]: (
            binding["node_key_id"],
            binding["node_id"],
            canonical_json_bytes(documents[binding["node_id"]]),
        )
        for binding in source_payload["active_final_bindings"]
    }
    expected = {
        item.address: (
            item.node_key_id,
            item.node_id,
            canonical_json_bytes(dict(item.node_document)),
        )
        for item in w0.payload.source_active_nodes
    }
    assert projected == expected


def test_matched_direct_control_and_offline_base_equivalence(campaign) -> None:
    _root, result = campaign
    proof = result.offline_base_equivalence
    offline = direct.conditional_direct_offline_base_document_v1()
    assert proof.direct_offline_base_id == offline["offline_base_id"]
    assert proof.ordered_source_ground_row_ids == tuple(
        row["ground_row_id"] for row in offline["rows"]
    )
    assert proof.ordered_direct_ground_row_ids == (
        proof.ordered_source_ground_row_ids
    )
    assert proof.exact_row_projection_match is True
    assert proof.direct_base_ground_calls_charged_per_occurrence is False

    for matched in result.matched_occurrences:
        certificate = matched.warm.certificate
        direct_result = matched.direct_result
        assert matched.warm.certificate.to_document() == (
            matched.base_reset.certificate.to_document()
        )
        assert (
            certificate.selected_action,
            certificate.reward_lower,
            certificate.failure_upper,
            certificate.normalized_regret,
            certificate.certified,
        ) == (
            direct_result.selected_action,
            direct_result.reward,
            direct_result.failure_probability,
            direct_result.normalized_regret,
            direct_result.certified,
        )
        assert (
            direct_result.exact_ground_transition_calls,
            direct_result.exact_action_catalogue_calls,
            direct_result.policy_evaluations,
            direct_result.optimizer_calls,
            direct_result.process_launches,
        ) == (1, 1, 4, 1, 1)


def test_fresh_direct_launch_isolation_flags(campaign) -> None:
    _root, result = campaign
    query = result.protocol.query(1)
    occurrence = result.preregistration.occurrences[0]
    launch = direct.run_h2_conditional_direct_ground_fresh_worker_v1(
        query, occurrence
    )
    direct.require_conditional_direct_launch_v1(launch)
    assert launch.child_process_id != launch.parent_process_id
    assert launch.fresh_process_attested is True
    assert launch.parent_process_distinct is True
    assert launch.isolated_interpreter is True
    assert launch.no_user_site is True
    assert launch.bytecode_disabled is True
    assert launch.process_launch_count == 1
    assert launch.accepted_input_roles == (
        "QUERY_INDEX",
        "OCCURRENCE_INDEX",
        "EXPECTED_QUERY_ID",
        "EXPECTED_OCCURRENCE_ID",
    )


@pytest.mark.parametrize(
    "attack",
    ("selection_parent", "consumed_facet", "facet_value"),
)
def test_fully_rehashed_store_facet_and_selection_attacks_fail(
    campaign, tmp_path, attack
) -> None:
    _root, result = campaign
    copied = _copy_warm_store(campaign, tmp_path, f"rehash-{attack}")

    def mutate(payload: dict[str, Any]) -> None:
        # The final appended group belongs to Q3 and ends in SELECTION.
        gate = payload["facet_entries"][-3]
        selection = payload["facet_entries"][-1]
        if attack == "selection_parent":
            selection["key"]["ordered_parent_node_ids"][0] = "0" * 64
            _rehash(selection["key"], "facet_key", "facet_key_id")
            _rehash(selection, "facet_entry", "node_id")
        elif attack == "consumed_facet":
            gate["key"]["consumed_facet_ids"][-1] = (
                result.protocol.query(2).regret_facet_id
            )
            _rehash(gate["key"], "facet_key", "facet_key_id")
            _rehash(gate, "facet_entry", "node_id")
        elif attack == "facet_value":
            field = gate["result_fields"][0]
            field["value"] = {"numerator": 99, "denominator": 1}
            _rehash(gate, "facet_entry", "node_id")
        else:  # pragma: no cover - parameter guard
            raise AssertionError(attack)

    new_commit_id = _replace_latest_store_generation(
        copied, result.w2_commit_id, mutate
    )
    with pytest.raises(ModelViolation):
        model.load_verified_h2_query_family_store_v1(
            copied, new_commit_id
        )


@pytest.mark.parametrize("attack", ("root", "certificate", "result"))
def test_root_certificate_and_result_stale_identity_mutations_fail(
    campaign, attack
) -> None:
    _root, result = campaign
    document = copy.deepcopy(result.warm_occurrences[0].to_document())
    if attack == "root":
        document["fresh_roots"][0]["certified"] = not document[
            "fresh_roots"
        ][0]["certified"]
    elif attack == "certificate":
        document["certificate"]["selected_action"] = "N"
    elif attack == "result":
        document["identity_hits"] -= 1
    else:  # pragma: no cover - parameter guard
        raise AssertionError(attack)
    with pytest.raises(ModelViolation):
        model.parse_h2_query_family_occurrence_result_document_v1(document)


@pytest.mark.parametrize(
    "attack",
    ("root_projection", "certificate_projection"),
)
def test_fully_rehashed_root_certificate_result_attacks_fail(
    campaign, attack
) -> None:
    _root, result = campaign
    document = copy.deepcopy(result.warm_occurrences[0].to_document())
    selected = document["fresh_roots"][-1]
    certificate = document["certificate"]
    if attack == "root_projection":
        selected["reward_lower"] = {"numerator": 99, "denominator": 1}
        _rehash_root(selected)
        certificate["selected_root_id"] = selected["root_id"]
        certificate["reward_lower"] = copy.deepcopy(selected["reward_lower"])
        _rehash_certificate(certificate)
    elif attack == "certificate_projection":
        certificate["reward_lower"] = {"numerator": 99, "denominator": 1}
        _rehash_certificate(certificate)
    else:  # pragma: no cover - parameter guard
        raise AssertionError(attack)
    _rehash_occurrence_result(document)
    with pytest.raises(ModelViolation):
        model.parse_h2_query_family_occurrence_result_document_v1(document)


def test_result_and_verification_require_live_authority(campaign) -> None:
    _root, result = campaign
    copied = _clone_exact(result)
    with pytest.raises(WorkloadViolation):
        workload.require_durable_multiquery_workload_result_v1(copied)
    mutated = _clone_exact(result, status="FORGED")
    with pytest.raises(WorkloadViolation):
        workload.require_durable_multiquery_workload_result_v1(mutated)


def test_same_implementation_verifier_preserves_original_store(
    campaign, verification
) -> None:
    _root, result = campaign
    report, before, after = verification
    assert before == after == result.campaign_snapshot_id
    assert report.claimed_result_id == result.result_id
    assert report.replayed_result_id == result.result_id
    assert report.exact_document_match is True
    assert report.original_store_unchanged is True
    assert report.protocol_reconstructed_before_replay_source is True
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    assert report.same_implementation_replay is True
    assert report.independent_algorithm is False
    assert (
        report.evaluation_ground_transition_calls,
        report.evaluation_process_launches,
    ) == (11, 33)
    assert report.report_id == pins.EXPECTED_CANONICAL_IDS[
        "evaluation_replay_report"
    ]
    assert (
        workload.require_durable_multiquery_workload_verification_v1(report)
        is report
    )
