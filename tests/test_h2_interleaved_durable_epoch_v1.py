"""Focused V0-057 interleaved durable-epoch regressions."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
from fractions import Fraction
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
from types import SimpleNamespace

import pytest

import acfqp.h2_interleaved_durable_epoch_v1 as interleaved
import acfqp.live_query_local_epoch_invalidation_v1 as live_source
import acfqp.multistep_query_refinement_v1 as multistep
import acfqp.partial_sound_audit_v1 as partial_audit
from acfqp._runtime_authority_v1 import bind_runtime_authority_v1
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    PartialAuditOutcome,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


Violation = interleaved.InterleavedDurableEpochInvariantViolation

EXPECTED_EVENT_ORDER = (
    "PREREGISTRATION_FROZEN",
    "QUERY_ELIGIBILITY_FROZEN",
    "AUTHENTIC_V0047_FIRST_EPOCH_STARTED",
    "ROUND_ONE_FOUR_ROWS_COMPLETED",
    "BOUNDARY_THREE_CATALOGUES_COMPLETED",
    "FIRST_11_9_EPOCH_FROZEN",
    "C1_ROOT_FREE_CHECKPOINT_FROZEN",
    "OCCURRENCE_1_Q_R_FIRST_EPOCH_STARTED",
    "OCCURRENCE_1_Q_R_CERTIFIED_ZERO_QUERY_GROUND",
    "OCCURRENCE_2_Q_S_FIRST_EPOCH_STARTED",
    "OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN",
    "ROUND_TWO_REQUEST_DERIVED_FROM_Q_S_FAILURE",
    "ROUND_TWO_NINE_ROWS_AUTHORIZED",
    "ROUND_TWO_NINE_ROWS_COMPLETED",
    "FINAL_20_0_EPOCH_FROZEN",
    "DELTA_AND_28_2_INVALIDATION_FROZEN",
    "C2_58_UNION_30_ACTIVE_FROZEN",
    "OCCURRENCE_2_Q_S_FINAL_REPLAN_STARTED",
    "OCCURRENCE_2_Q_S_CERTIFIED",
    "OCCURRENCE_3_Q_R_FINAL_CERTIFIED",
    "OCCURRENCE_4_Q_S_FINAL_CERTIFIED",
    "OCCURRENCE_5_Q_R_FINAL_CERTIFIED",
    "CAMPAIGN_RESULT_FROZEN",
)


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert type(value) is dict
    return value


def _write_canonical(path: Path, document: dict) -> None:
    path.write_bytes(interleaved._canonical_json_bytes(document))


def _pins_module():
    return importlib.import_module(
        "acfqp.h2_interleaved_durable_epoch_pins_v1"
    )


def _checkpoint_paths(
    root: Path,
    checkpoint: str,
    commit_id: str,
) -> tuple[Path, Path, dict, dict]:
    commit_path = root / checkpoint / "commits" / f"{commit_id}.json"
    commit = _read_json(commit_path)
    payload_path = (
        root
        / checkpoint
        / "blobs"
        / f"{commit['payload_id']}.json"
    )
    payload = _read_json(payload_path)
    return payload_path, commit_path, payload, commit


def _fully_rehash_checkpoint_commit(
    checkpoint_root: Path,
    expected_commit_id: str,
    mutator,
) -> str:
    commit_path = (
        checkpoint_root / "commits" / f"{expected_commit_id}.json"
    )
    commit = _read_json(commit_path)
    mutator(commit)
    commit.pop("commit_id", None)
    new_commit_id = interleaved._checkpoint_commit_id(commit)
    commit["commit_id"] = new_commit_id
    commit_path.unlink()
    _write_canonical(
        checkpoint_root / "commits" / f"{new_commit_id}.json",
        commit,
    )
    return new_commit_id


def _fully_rehash_checkpoint_payload(
    checkpoint_root: Path,
    expected_commit_id: str,
    mutator,
) -> str:
    payload_path, commit_path, payload, commit = _checkpoint_paths(
        checkpoint_root.parent,
        checkpoint_root.name,
        expected_commit_id,
    )
    mutator(payload)
    payload.pop("payload_id", None)
    new_payload_id = interleaved._checkpoint_payload_id(payload)
    payload["payload_id"] = new_payload_id
    payload_bytes = interleaved._canonical_json_bytes(payload)
    payload_path.unlink()
    _write_canonical(
        checkpoint_root / "blobs" / f"{new_payload_id}.json",
        payload,
    )
    commit["payload_id"] = new_payload_id
    commit["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    commit["payload_size_bytes"] = len(payload_bytes)
    commit.pop("commit_id", None)
    new_commit_id = interleaved._checkpoint_commit_id(commit)
    commit["commit_id"] = new_commit_id
    commit_path.unlink()
    _write_canonical(
        checkpoint_root / "commits" / f"{new_commit_id}.json",
        commit,
    )
    return new_commit_id


def _fully_rehash_facet_tip(
    facet_root: Path,
    expected_commit_id: str,
    mutator,
) -> str:
    commit_path = (
        facet_root / "commits" / f"{expected_commit_id}.json"
    )
    commit = _read_json(commit_path)
    payload_path = (
        facet_root / "blobs" / f"{commit['payload_id']}.json"
    )
    payload = _read_json(payload_path)
    mutator(payload)
    payload.pop("payload_id", None)
    new_payload_id = interleaved._facet_payload_id(payload)
    payload["payload_id"] = new_payload_id
    payload_bytes = interleaved._canonical_json_bytes(payload)
    payload_path.unlink()
    _write_canonical(
        facet_root / "blobs" / f"{new_payload_id}.json",
        payload,
    )
    commit["payload_id"] = new_payload_id
    commit["payload_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    commit["payload_size_bytes"] = len(payload_bytes)
    commit.pop("commit_id", None)
    new_commit_id = interleaved._facet_commit_id(commit)
    commit["commit_id"] = new_commit_id
    commit_path.unlink()
    _write_canonical(
        facet_root / "commits" / f"{new_commit_id}.json",
        commit,
    )
    return new_commit_id


def _rehash_source_chain(
    source_chain: dict,
    nested_name: str,
    identity_field: str,
    role: str,
    content_id,
) -> dict:
    attacked = copy.deepcopy(source_chain)
    nested = attacked[nested_name]
    nested.pop(identity_field, None)
    nested[identity_field] = content_id(role, nested)
    attacked.pop("source_chain_id", None)
    attacked["source_chain_id"] = interleaved._content_id(
        "source_chain", attacked
    )
    return attacked


def _fully_rehash_occurrence_facet_key(
    document: dict,
    field_name: str,
    forged_value: str,
) -> dict:
    attacked = copy.deepcopy(document)
    entry = attacked["appended_facet_entries"][0]
    old_entry_id = entry["facet_entry_id"]
    key = entry["key"]
    key[field_name] = forged_value
    key.pop("facet_key_id", None)
    key["facet_key_id"] = interleaved._content_id("facet_key", key)
    entry["facet_key_id"] = key["facet_key_id"]
    entry.pop("facet_entry_id", None)
    entry["facet_entry_id"] = interleaved._content_id(
        "facet_entry", entry
    )
    new_entry_id = entry["facet_entry_id"]
    attacked["appended_facet_entries"].sort(
        key=lambda item: item["facet_entry_id"]
    )
    remapped_root_ids: dict[str, str] = {}
    for root in attacked["candidate_roots"]:
        old_root_id = root["candidate_root_id"]
        for facet_field in (
            "regret_facet_entry_id",
            "risk_facet_entry_id",
        ):
            if root[facet_field] == old_entry_id:
                root[facet_field] = new_entry_id
        root.pop("candidate_root_id", None)
        root["candidate_root_id"] = interleaved._content_id(
            "candidate_root", root
        )
        remapped_root_ids[old_root_id] = root["candidate_root_id"]
    proposal = attacked["proposal"]
    proposal["candidate_root_ids"] = [
        remapped_root_ids[value]
        for value in proposal["candidate_root_ids"]
    ]
    proposal.pop("proposal_id", None)
    proposal["proposal_id"] = interleaved._content_id(
        "proposal", proposal
    )
    selected = attacked["selected_root"]
    selected["proposal_id"] = proposal["proposal_id"]
    for facet_field in (
        "regret_facet_entry_id",
        "risk_facet_entry_id",
    ):
        if selected[facet_field] == old_entry_id:
            selected[facet_field] = new_entry_id
    selected_request = selected["proof_request"]
    selected_request["proposal_id"] = proposal["proposal_id"]
    selected_request.pop("proof_request_id", None)
    selected_request["proof_request_id"] = interleaved._content_id(
        "proof_request", selected_request
    )
    selected["proof_request_id"] = selected_request["proof_request_id"]
    selected.pop("selected_root_id", None)
    selected["selected_root_id"] = interleaved._content_id(
        "selected_root", selected
    )
    certificate = attacked["certificate"]
    certificate["proposal_id"] = proposal["proposal_id"]
    certificate["selected_root_id"] = selected["selected_root_id"]
    certificate.pop("certificate_id", None)
    certificate["certificate_id"] = interleaved._content_id(
        "certificate", certificate
    )
    attacked.pop("result_id", None)
    attacked["result_id"] = interleaved._content_id(
        "occurrence_result", attacked
    )
    return attacked


@pytest.fixture(scope="module")
def interleaved_campaign(tmp_path_factory):
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    base_model = synthesis.partial_build_result.model
    initial_state_id = source["observed_by_ground"][
        source["extra"]
    ].state_id
    thresholds = _thresholds(base_model, initial_state_id, horizon=2)
    base_proposal = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
    )
    assert base_proposal.selected_plan is not None
    failed_audit = audit_partial_fixed_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal.selected_plan,
    )
    assert (
        failed_audit.audit_result.outcome
        is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    )
    kernel = multistep.canonical_lmb_query_kernel_v1()
    root = tmp_path_factory.mktemp("v0057") / "campaign"
    result = interleaved.run_lmb_h2_interleaved_durable_epoch_v1(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal,
        failed_audit,
        kernel,
        root,
    )
    return {
        **source,
        "synthesis": synthesis,
        "thresholds": thresholds,
        "base_proposal": base_proposal,
        "failed_audit": failed_audit,
        "kernel": kernel,
        "root": root,
        "result": result,
    }


@pytest.fixture(scope="module")
def interleaved_verification(interleaved_campaign):
    item = interleaved_campaign
    return interleaved.verify_lmb_h2_interleaved_durable_epoch_v1(
        item["log"],
        item["profile"],
        item["authority"],
        item["synthesis"],
        item["thresholds"],
        item["base_proposal"],
        item["failed_audit"],
        item["kernel"],
        item["root"],
        item["result"],
    )


def test_public_api_excludes_completed_results_and_caller_artifacts() -> None:
    runner = interleaved.run_lmb_h2_interleaved_durable_epoch_v1
    verifier = interleaved.verify_lmb_h2_interleaved_durable_epoch_v1
    nine = (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "kernel",
        "store_root",
    )
    assert tuple(inspect.signature(runner).parameters) == nine
    assert tuple(inspect.signature(verifier).parameters) == (
        *nine,
        "claimed_result",
    )
    forbidden = {
        "source_result",
        "live_result",
        "first_model",
        "final_model",
        "rows",
        "frontier",
        "selected_plan",
        "cache",
        "expected_result",
        "completed_result",
    }
    assert not forbidden & set(inspect.signature(runner).parameters)
    with pytest.raises(TypeError):
        runner(source_result=object())  # type: ignore[call-arg]


def test_relaxed_query_is_typed_without_mutating_historical_registry() -> None:
    relaxed, strict = interleaved.registered_interleaved_queries_v1()
    assert type(relaxed) is interleaved.InterleavedThresholdQueryV1
    assert type(strict) is interleaved.InterleavedThresholdQueryV1
    assert (
        relaxed.query_code,
        relaxed.normalized_regret_tolerance,
        relaxed.risk_tolerance,
    ) == ("Q_R", Fraction(3, 4), Fraction(1))
    assert (
        strict.query_code,
        strict.normalized_regret_tolerance,
        strict.risk_tolerance,
    ) == ("Q_S", Fraction(0), Fraction(0))
    assert Fraction(3, 4) not in (
        partial_audit.REGISTERED_NORMALIZED_REGRET_TOLERANCES
    )
    assert Fraction(1) not in partial_audit.REGISTERED_RISK_TOLERANCES


def test_verifier_is_explicit_same_implementation_fresh_store_replay() -> None:
    source = inspect.getsource(
        interleaved.verify_lmb_h2_interleaved_durable_epoch_v1
    )
    assert "_execute_lmb_h2_interleaved_durable_epoch_v1" in source
    assert "run_lmb_h2_interleaved_durable_epoch_v1(" not in source
    assert source.index("_invoke_canonical_source_pin_assert") < source.index(
        "require_interleaved_durable_epoch_result_v1"
    )
    assert source.index(
        "require_interleaved_durable_epoch_result_v1"
    ) < source.index("tempfile.TemporaryDirectory")
    report_signature = inspect.signature(
        interleaved.InterleavedDurableEpochVerificationReportV1
    )
    assert (
        report_signature.parameters[
            "evaluation_ground_transition_calls"
        ].default,
        report_signature.parameters[
            "evaluation_worker_process_launches"
        ].default,
        report_signature.parameters[
            "same_implementation_full_replay"
        ].default,
        report_signature.parameters["independent_algorithm"].default,
        report_signature.parameters["evaluation_lane_only"].default,
        report_signature.parameters[
            "included_in_operational_work"
        ].default,
        report_signature.parameters[
            "evaluation_host_checkpoint_store_load_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_cross_store_lineage_check_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_facet_store_load_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_worker_result_reconstruction_comparison_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_input_snapshot_hash_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_immutability_comparison_count"
        ].default,
        report_signature.parameters[
            "evaluation_host_worker_semantic_assertion_count"
        ].default,
        report_signature.parameters[
            "claimed_result_semantic_validation_count"
        ].default,
        report_signature.parameters[
            "claimed_campaign_snapshot_hash_count"
        ].default,
        report_signature.parameters[
            "replayed_document_comparison_count"
        ].default,
    ) == (
        13,
        12,
        True,
        False,
        True,
        False,
        23,
        9,
        36,
        12,
        64,
        32,
        12,
        1,
        2,
        1,
    )


def test_source_pins_are_literal_nonzero_and_match_actual_authorities() -> None:
    pins = _pins_module()
    pin_path = Path(pins.__file__).resolve()
    tree = ast.parse(pin_path.read_text(encoding="utf-8"))
    project_imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            project_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            project_imports.add(node.module)
    assert not {
        name for name in project_imports if name.startswith("acfqp")
    }
    literal_assignments: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is str
        ):
            literal_assignments[node.targets[0].id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is str
        ):
            literal_assignments[node.target.id] = node.value.value
    expected = {
        name: value
        for name, value in vars(pins).items()
        if name.startswith("EXPECTED_") and name.endswith("_SHA256")
    }
    assert "EXPECTED_ORCHESTRATOR_MODULE_SHA256" in expected
    assert len(expected) >= 5
    assert set(expected) <= set(literal_assignments)
    assert expected == {
        name: literal_assignments[name] for name in expected
    }
    assignment_counts = {name: 0 for name in expected}
    for node in tree.body:
        targets: tuple[ast.expr, ...]
        value: ast.expr | None
        if isinstance(node, ast.Assign):
            targets = tuple(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id in expected:
                assignment_counts[target.id] += 1
                assert isinstance(value, ast.Constant)
                assert type(value.value) is str
    assert set(assignment_counts.values()) == {1}
    assert all(
        type(value) is str
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        and value != "0" * 64
        for value in expected.values()
    )
    assert hashlib.sha256(
        Path(interleaved.__file__).resolve().read_bytes()
    ).hexdigest() == expected["EXPECTED_ORCHESTRATOR_MODULE_SHA256"]
    interleaved._assert_source_pins()


def test_source_pin_mismatch_fails_before_campaign_root_or_ground(
    interleaved_campaign,
    tmp_path,
    monkeypatch,
) -> None:
    pins = _pins_module()
    bad = "f" * 64
    monkeypatch.setattr(
        pins, "EXPECTED_ORCHESTRATOR_MODULE_SHA256", bad
    )
    monkeypatch.setattr(
        interleaved, "EXPECTED_ORCHESTRATOR_MODULE_SHA256", bad
    )
    root = tmp_path / "pin-mismatch-campaign"
    item = interleaved_campaign
    with pytest.raises(Violation):
        interleaved.run_lmb_h2_interleaved_durable_epoch_v1(
            item["log"],
            item["profile"],
            item["authority"],
            item["synthesis"],
            item["thresholds"],
            item["base_proposal"],
            item["failed_audit"],
            item["kernel"],
            root,
        )
    assert not root.exists()


def test_replacing_pin_verifier_with_noop_fails_before_campaign_root(
    interleaved_campaign,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        interleaved,
        "_assert_source_pins",
        lambda **_kwargs: None,
    )
    root = tmp_path / "pin-verifier-noop-campaign"
    item = interleaved_campaign
    with pytest.raises(Violation):
        interleaved.run_lmb_h2_interleaved_durable_epoch_v1(
            item["log"],
            item["profile"],
            item["authority"],
            item["synthesis"],
            item["thresholds"],
            item["base_proposal"],
            item["failed_audit"],
            item["kernel"],
            root,
        )
    assert not root.exists()


def test_monkeypatched_upstream_callable_fails_before_campaign_root(
    interleaved_campaign,
    tmp_path,
    monkeypatch,
) -> None:
    original = multistep._acquire

    def substituted(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(multistep, "_acquire", substituted)
    root = tmp_path / "callable-mismatch-campaign"
    item = interleaved_campaign
    with pytest.raises(Violation):
        interleaved.run_lmb_h2_interleaved_durable_epoch_v1(
            item["log"],
            item["profile"],
            item["authority"],
            item["synthesis"],
            item["thresholds"],
            item["base_proposal"],
            item["failed_audit"],
            item["kernel"],
            root,
        )
    assert not root.exists()


def test_worker_pin_mismatch_fails_before_checkpoint_read(
    monkeypatch,
) -> None:
    pins = _pins_module()
    bad = "f" * 64
    monkeypatch.setattr(
        pins, "EXPECTED_ORCHESTRATOR_MODULE_SHA256", bad
    )
    monkeypatch.setattr(
        interleaved, "EXPECTED_ORCHESTRATOR_MODULE_SHA256", bad
    )
    checkpoint_read = False

    def forbidden_checkpoint_read(*_args, **_kwargs):
        nonlocal checkpoint_read
        checkpoint_read = True
        raise AssertionError("worker read checkpoint before source pins")

    monkeypatch.setattr(
        interleaved, "_load_checkpoint", forbidden_checkpoint_read
    )
    worker_status = interleaved._worker_main(
        [
            "unread-checkpoint",
            "a" * 64,
            "NONE",
            "NONE",
            "unread-facets",
            "b" * 64,
            "unread-query",
            "unread-occurrence",
            "unwritten-result",
            str(os.getppid()),
        ]
    )
    assert worker_status == 1
    assert checkpoint_read is False


def test_registered_positive_campaign_and_preregistration_order(
    interleaved_campaign,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    assert interleaved.CONTRACT_VERSION == "1.21.0"
    assert result.status == interleaved.SUCCESS_STATUS
    assert (
        tuple(item.query.query_code for item in result.preregistration.occurrences)
        == ("Q_R", "Q_S", "Q_R", "Q_S", "Q_R")
    )
    assert tuple(
        item.event_kind for item in result.event_log.events
    ) == EXPECTED_EVENT_ORDER
    assert (
        result.preregistration.derived_source_artifact_ids_absent
        is True
    )
    assert result.preregistration.frozen_before_source_ground is True
    assert result.preregistration.input_authority_ids == (
        result.source_chain["input_authority_ids"]
    )
    assert result.preregistration.input_authority_ids == {
        "observation_log_id": interleaved_campaign["log"].log_id,
        "semantics_profile_id": (
            interleaved_campaign["profile"].profile_id
        ),
        "observation_authority_id": (
            interleaved_campaign["authority"].authority_id
        ),
        "observed_synthesis_result_id": (
            interleaved_campaign["synthesis"].result_id
        ),
        "source_thresholds_id": (
            interleaved_campaign["thresholds"].thresholds_id
        ),
        "base_plan_proposal_id": (
            interleaved_campaign["base_proposal"].result_id
        ),
        "failed_audit_id": interleaved_campaign[
            "failed_audit"
        ].result_id,
        "kernel_digest": result.source_chain["input_authority_ids"][
            "kernel_digest"
        ],
    }
    base_model = (
        interleaved_campaign["synthesis"].partial_build_result.model
    )
    thresholds_document = interleaved_campaign[
        "thresholds"
    ].to_document()
    return_bound = thresholds_document["return_bound_proof"]
    assert (
        result.preregistration.horizon,
        result.preregistration.goal_id,
        result.preregistration.return_bound_proof_id,
        result.preregistration.return_bound_formula_id,
        result.preregistration.return_upper,
        result.preregistration.unrestricted_upper_formula_id,
        result.preregistration.base_model_id,
        result.preregistration.structural_id,
        result.preregistration.environment_instance_id,
        result.preregistration.coordinate_proposal_id,
    ) == (
        2,
        thresholds_document["goal_id"],
        return_bound["proof_id"],
        return_bound["formula_id"],
        Fraction(
            return_bound["return_upper"]["numerator"],
            return_bound["return_upper"]["denominator"],
        ),
        thresholds_document["unrestricted_upper_formula_id"],
        base_model.model_id,
        return_bound["structural_id"],
        return_bound["environment_instance_id"],
        base_model.coordinate_proposal_id,
    )
    expected_structural_scope = (
        interleaved._structural_state_action_concretizer_scope(
            base_model.to_document(),
            return_bound,
            interleaved_campaign["profile"].to_document(),
        )
    )
    assert (
        result.preregistration.structural_state_action_concretizer_scope
        == expected_structural_scope
    )
    assert (
        result.preregistration.structural_state_action_concretizer_digest
        == interleaved._structural_state_action_concretizer_digest(
            expected_structural_scope
        )
    )
    preregistration_path = root / "preregistration.json"
    assert preregistration_path.is_file()
    preregistration_text = preregistration_path.read_text(encoding="utf-8")
    for forbidden in (
        result.source_chain["source_chain_id"],
        result.first_checkpoint_commit["commit_id"],
        result.final_checkpoint_commit["commit_id"],
        result.ground_repair_authorization.authorization_id,
        *interleaved._EXPECTED_EPOCH_MODEL_IDS.values(),
    ):
        assert forbidden not in preregistration_text
    assert preregistration_path.stat().st_mtime_ns <= min(
        path.stat().st_mtime_ns
        for directory in (root / "c1", root / "facets-c1")
        for path in directory.rglob("*")
        if path.is_file()
    )
    assert (
        interleaved.require_interleaved_durable_epoch_result_v1(result)
        is result
    )
    with pytest.raises(Violation):
        replace(
            result.preregistration,
            occurrences=(
                result.preregistration.occurrences[1],
                result.preregistration.occurrences[0],
                *result.preregistration.occurrences[2:],
            ),
        )


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    (
        ("initial_distribution_digest", "a" * 64),
        ("reward_basis_digest", "b" * 64),
        ("return_bound_proof_id", "c" * 64),
        ("return_upper", Fraction(3)),
        ("structural_id", "d" * 64),
        ("environment_instance_id", "e" * 64),
        ("coordinate_proposal_id", "f" * 64),
        ("structural_state_action_concretizer_digest", "1" * 64),
        ("policy_class", "FORGED_RANDOMIZED_POLICY"),
        ("candidate_order", tuple(reversed(interleaved.SCHEDULE_ORDER))),
    ),
)
def test_preregistration_scope_cannot_be_rehashed_away_from_inputs(
    interleaved_campaign,
    field_name: str,
    forged_value,
) -> None:
    result = interleaved_campaign["result"]
    with pytest.raises(Violation):
        attacked = replace(
            result.preregistration,
            **{field_name: forged_value},
        )
        replace(
            result,
            preregistration=attacked,
            _instance_mint=None,
        )


@pytest.mark.parametrize("field_name", ("semantics_profile_id", "kernel_digest"))
def test_preregistered_authority_map_cannot_be_rehashed_away_from_source(
    interleaved_campaign,
    field_name: str,
) -> None:
    result = interleaved_campaign["result"]
    attacked_authorities = dict(
        result.preregistration.input_authority_ids
    )
    attacked_authorities[field_name] = "9" * 64
    with pytest.raises(Violation):
        attacked = replace(
            result.preregistration,
            input_authority_ids=attacked_authorities,
        )
        replace(
            result,
            preregistration=attacked,
            _instance_mint=None,
        )


def test_coherently_rehashed_structural_scope_cannot_replace_input_scope(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    scope = copy.deepcopy(
        result.preregistration.structural_state_action_concretizer_scope
    )
    scope["semantics_profile"]["concretizer_rule"] = (
        "FORGED_QUERY_TIME_CONCRETIZER"
    )
    digest = interleaved._structural_state_action_concretizer_digest(
        scope
    )
    attacked = replace(
        result.preregistration,
        structural_state_action_concretizer_scope=scope,
        structural_state_action_concretizer_digest=digest,
    )
    with pytest.raises(Violation):
        replace(
            result,
            preregistration=attacked,
            _instance_mint=None,
        )


def test_o1_pass_precedes_o2_failure_and_only_o2_authorizes_ground(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    by_label = {
        item.execution_label: item for item in result.worker_executions
    }
    o1 = by_label["O1_FIRST"].occurrence_result
    o2 = by_label["O2_FAILED_FIRST"].occurrence_result
    assert o1["certificate"]["certified"] is True
    assert o1["certificate"]["failed_proof_frontier"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "SELECTED_PLAN_CERTIFIED",
    }
    assert o2["certificate"]["certified"] is False
    assert (
        o2["certificate"]["failed_proof_frontier"][
            "local_recovery_authorized"
        ]
        is False
    )
    authorization = result.ground_repair_authorization
    assert (
        authorization.failed_occurrence_result_id == o2["result_id"]
    )
    assert authorization.occurrence_id == (
        result.preregistration.occurrences[1].occurrence_id
    )
    assert authorization.failed_frontier_id == (
        o2["certificate"]["failed_proof_frontier"]["frontier_id"]
    )
    kinds = tuple(item.event_kind for item in result.event_log.events)
    assert kinds.index(
        "OCCURRENCE_1_Q_R_CERTIFIED_ZERO_QUERY_GROUND"
    ) < kinds.index("OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN")
    assert kinds.index(
        "OCCURRENCE_2_Q_S_SELECTED_FAILURE_FROZEN"
    ) < kinds.index("ROUND_TWO_NINE_ROWS_AUTHORIZED")


def test_roots_are_bound_to_closed_role_specific_proof_requests(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    execution = next(
        item
        for item in result.worker_executions
        if item.execution_label == "O2_FAILED_FIRST"
    )
    occurrence_result = execution.occurrence_result
    selected = occurrence_result["selected_root"]
    candidate = occurrence_result["candidate_roots"][0]
    for root, role, expected_proof_role in (
        (
            candidate,
            "candidate_root",
            "CANDIDATE_RANKING_AUDIT",
        ),
        (
            selected,
            "selected_root",
            "INDEPENDENT_SELECTED_PLAN_CERTIFICATE",
        ),
    ):
        request = root["proof_request"]
        assert root["proof_request_id"] == request["proof_request_id"]
        assert root["proof_role"] == request["proof_role"]
        assert root["proof_role"] == expected_proof_role
        assert request["occurrence_id"] == root["occurrence_id"]
        assert request["query_id"] == root["query_id"]
        assert request["checkpoint_commit_id"] == (
            root["checkpoint_commit_id"]
        )
        assert request["model_id"] == root["model_id"]
        assert request["epoch_name"] == root["epoch_name"]
        assert request["evidence_request_id"] == (
            root["evidence_request_id"]
        )
        assert request["metric_id"] == root["metric_id"]
        assert request["schedule_code"] == root["schedule_code"]
        interleaved._validate_root_document(
            root,
            role=role,
            occurrence_id=root["occurrence_id"],
            query_id=root["query_id"],
            checkpoint_commit_id=root["checkpoint_commit_id"],
            model_id=root["model_id"],
            epoch_name=root["epoch_name"],
            evidence_request_id=root["evidence_request_id"],
        )
    assert candidate["proof_request"]["proposal_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "CANDIDATE_PRECEDES_PROPOSAL",
    }
    assert selected["proof_request"]["proposal_id"] == (
        selected["proposal_id"]
    )


@pytest.mark.parametrize(
    "attack",
    (
        "occurrence_id",
        "model_id",
        "evidence_request_id",
        "proof_role",
        "selected_request_on_candidate",
    ),
)
def test_fully_rehashed_proof_request_transplants_fail(
    interleaved_campaign,
    attack: str,
) -> None:
    result = interleaved_campaign["result"]
    occurrence_result = next(
        item.occurrence_result
        for item in result.worker_executions
        if item.execution_label == "O2_FAILED_FIRST"
    )
    selected = occurrence_result["selected_root"]
    if attack == "selected_request_on_candidate":
        attacked = copy.deepcopy(
            occurrence_result["candidate_roots"][0]
        )
        role = "candidate_root"
        attacked["proof_request"] = copy.deepcopy(
            selected["proof_request"]
        )
    else:
        attacked = copy.deepcopy(selected)
        role = "selected_root"
        if attack == "proof_role":
            attacked["proof_request"]["proof_role"] = (
                "CANDIDATE_RANKING_AUDIT"
            )
        else:
            attacked["proof_request"][attack] = "f" * 64
        attacked["proof_request"].pop("proof_request_id", None)
        attacked["proof_request"]["proof_request_id"] = (
            interleaved._content_id(
                "proof_request", attacked["proof_request"]
            )
        )
    attacked["proof_request_id"] = attacked["proof_request"][
        "proof_request_id"
    ]
    identity_field = (
        "candidate_root_id"
        if role == "candidate_root"
        else "selected_root_id"
    )
    attacked.pop(identity_field, None)
    attacked[identity_field] = interleaved._content_id(role, attacked)
    with pytest.raises(Violation):
        interleaved._validate_root_document(
            attacked,
            role=role,
            occurrence_id=attacked["occurrence_id"],
            query_id=attacked["query_id"],
            checkpoint_commit_id=attacked["checkpoint_commit_id"],
            model_id=attacked["model_id"],
            epoch_name=attacked["epoch_name"],
            evidence_request_id=attacked["evidence_request_id"],
        )


def test_relaxed_pass_root_cannot_be_reminted_as_ground_authority(
    interleaved_campaign,
) -> None:
    """A process-minted ID-only transplant is still semantically invalid."""

    result = interleaved_campaign["result"]
    o1 = next(
        item.occurrence_result
        for item in result.worker_executions
        if item.execution_label == "O1_FIRST"
    )
    forged = replace(
        result.ground_repair_authorization,
        occurrence_id=o1["occurrence"]["occurrence_id"],
        failed_occurrence_result_id=o1["result_id"],
        failed_frontier_id=o1["certificate"]["certificate_id"],
        _instance_mint=None,
    )
    forged = bind_runtime_authority_v1(
        forged, issuer=interleaved._GROUND_AUTH_ISSUER
    )
    with pytest.raises(Violation):
        interleaved._require_ground_repair_authorization(forged)


def test_candidate_root_or_c1_identity_cannot_be_reminted_as_authority(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    failed_execution = next(
        item
        for item in result.worker_executions
        if item.execution_label == "O2_FAILED_FIRST"
    )
    candidate = failed_execution.occurrence_result["candidate_roots"][0]
    for forged_fields in (
        {
            "failed_certificate_id": candidate["candidate_root_id"],
        },
        {
            "failed_occurrence_result_id": (
                result.first_checkpoint_commit["commit_id"]
            ),
            "failed_certificate_id": (
                result.first_checkpoint_commit["commit_id"]
            ),
            "failed_frontier_id": (
                result.first_checkpoint_commit["commit_id"]
            ),
        },
    ):
        forged = replace(
            result.ground_repair_authorization,
            **forged_fields,
            _instance_mint=None,
        )
        forged = bind_runtime_authority_v1(
            forged, issuer=interleaved._GROUND_AUTH_ISSUER
        )
        with pytest.raises(Violation):
            interleaved._require_ground_repair_authorization(forged)


@pytest.mark.parametrize("mode", ("less", "more", "reordered"))
def test_ground_gate_rejects_nonexact_nine_row_scope(
    interleaved_campaign,
    mode: str,
) -> None:
    authorization = interleaved_campaign[
        "result"
    ].ground_repair_authorization
    rows = authorization.authorized_ground_row_ids
    if mode == "less":
        attacked = rows[:-1]
    elif mode == "more":
        attacked = (*rows, "f" * 64)
    else:
        attacked = tuple(reversed(rows))
    nonce = object()
    calls = 0

    class FakeMultistep:
        @staticmethod
        def _acquire(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            return object()

    request = SimpleNamespace(
        request_id=authorization.evidence_request_id,
        requested_ground_row_ids=attacked,
    )
    with pytest.raises(Violation):
        gate = interleaved._SingleUseGroundRepairGate(
            authorization, nonce
        )
        gate.acquire(
            multistep=FakeMultistep,
            request=request,
            observation_log=object(),
            boundary=object(),
            kernel=object(),
            nonce=nonce,
        )
    assert calls == 0


@pytest.mark.parametrize(
    ("field_name", "forged_value"),
    (
        ("selected_plan_risk_row_count", 2),
        ("unrestricted_value_challenger_row_count", 8),
        ("requested_distinct_ground_row_count", 8),
    ),
)
def test_ground_authorization_rejects_changed_cardinality_claims(
    interleaved_campaign,
    field_name: str,
    forged_value: int,
) -> None:
    authorization = interleaved_campaign[
        "result"
    ].ground_repair_authorization
    with pytest.raises(Violation):
        replace(
            authorization,
            **{field_name: forged_value, "_instance_mint": None},
        )


def test_consumed_ground_authorization_cannot_be_replayed_by_new_gate(
    interleaved_campaign,
) -> None:
    authorization = interleaved_campaign[
        "result"
    ].ground_repair_authorization
    semantic_authority = (
        interleaved._registered_ground_semantic_authority(authorization)
    )
    request = semantic_authority._request
    calls = 0

    class FakeMultistep:
        @staticmethod
        def _acquire(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            return object()

    for _ in range(2):
        nonce = object()
        with pytest.raises(Violation):
            replay_gate = interleaved._SingleUseGroundRepairGate(
                authorization, nonce
            )
            replay_gate.acquire(
                multistep=FakeMultistep,
                request=request,
                observation_log=object(),
                boundary=object(),
                kernel=object(),
                nonce=nonce,
            )
        assert calls == 0


def test_round_two_evidence_is_exact_ordered_nine_row_bundle(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    request = result.source_chain["round_two_request"]
    bundle = result.source_chain["round_two_bundle"]
    authorization = result.ground_repair_authorization
    requested = tuple(request["requested_ground_row_ids"])
    observed = tuple(item["ground_row_id"] for item in bundle["evidence"])
    assert len(requested) == len(set(requested)) == 9
    assert requested == tuple(sorted(requested))
    assert requested == authorization.authorized_ground_row_ids
    assert observed == requested
    assert tuple(item["sequence_number"] for item in bundle["evidence"]) == (
        tuple(range(1, 10))
    )
    assert (
        request["selected_plan_risk_row_count"],
        request["unrestricted_value_challenger_row_count"],
        request["requested_distinct_ground_row_count"],
    ) == (3, 9, 9)
    assert (
        authorization.selected_plan_risk_row_count,
        authorization.unrestricted_value_challenger_row_count,
        authorization.requested_distinct_ground_row_count,
    ) == (3, 9, 9)
    safe = [
        item
        for item in bundle["evidence"]
        if item["terminal"] is False
        and item["failure"] is False
        and item["reward_features"]
        == [
            {
                "name": "match",
                "value": {"numerator": 1, "denominator": 1},
            }
        ]
    ]
    failed = [
        item
        for item in bundle["evidence"]
        if item["terminal"] is True
        and item["failure"] is True
        and item["reward_features"] == []
    ]
    assert (len(safe), len(failed)) == (3, 6)
    assert bundle["exact_kernel_query_count"] == 9
    assert bundle["extra_ground_row_access_count"] == 0


@pytest.mark.parametrize(
    "attack",
    (
        "unknown_nested_field",
        "round_two_parent",
        "round_two_outcome",
        "final_model",
        "invalidation_delta",
    ),
)
def test_fully_rehashed_nested_source_transport_attacks_fail(
    interleaved_campaign,
    attack: str,
) -> None:
    result = interleaved_campaign["result"]
    attacked = copy.deepcopy(result.source_chain)
    if attack == "unknown_nested_field":
        attacked["round_one_bundle"]["unregistered_transport_field"] = True
        attacked = _rehash_source_chain(
            attacked,
            "round_one_bundle",
            "bundle_id",
            "bundle",
            multistep._content_id,
        )
    elif attack == "round_two_parent":
        attacked["round_two_bundle"]["request_id"] = attacked[
            "round_one_request"
        ]["request_id"]
        attacked = _rehash_source_chain(
            attacked,
            "round_two_bundle",
            "bundle_id",
            "bundle",
            multistep._content_id,
        )
    elif attack == "round_two_outcome":
        evidence = next(
            item
            for item in attacked["round_two_bundle"]["evidence"]
            if item["terminal"] is False
        )
        evidence["reward_features"] = []
        evidence.pop("evidence_id", None)
        evidence["evidence_id"] = multistep._content_id(
            "evidence", evidence
        )
        attacked = _rehash_source_chain(
            attacked,
            "round_two_bundle",
            "bundle_id",
            "bundle",
            multistep._content_id,
        )
    elif attack == "final_model":
        attacked["final_overlay_build"]["model"]["model_id"] = "a" * 64
        attacked = _rehash_source_chain(
            attacked,
            "final_overlay_build",
            "result_id",
            "build",
            multistep._content_id,
        )
    else:
        attacked["invalidation_manifest"]["delta_id"] = "b" * 64
        attacked = _rehash_source_chain(
            attacked,
            "invalidation_manifest",
            "manifest_id",
            "invalidation",
            live_source._content_id,
        )
    with pytest.raises(Violation):
        replace(
            result,
            source_chain=attacked,
            _instance_mint=None,
        )


def test_checkpoint_commit_schema_generation_and_predecessor_chain(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    first = result.first_checkpoint_commit
    final = result.final_checkpoint_commit
    assert first["schema"] == (
        "acfqp.interleaved_epoch_checkpoint_commit.v1"
    )
    assert final["schema"] == first["schema"]
    assert first["generation"] == 1
    assert first["previous_commit_id"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "FIRST_EPOCH",
    }
    assert final["generation"] == 2
    assert final["previous_commit_id"] == first["commit_id"]


def test_c2_loader_requires_the_external_expected_c1_predecessor(
    interleaved_campaign,
) -> None:
    loader = interleaved._load_checkpoint
    assert "expected_previous_commit_id" in inspect.signature(
        loader
    ).parameters
    assert "predecessor_store_root" in inspect.signature(
        loader
    ).parameters
    result = interleaved_campaign["result"]
    payload, commit = loader(
        interleaved_campaign["root"] / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=interleaved_campaign["root"] / "c1",
    )
    assert payload["epoch_name"] == "FINAL"
    assert commit["previous_commit_id"] == (
        result.first_checkpoint_commit["commit_id"]
    )
    with pytest.raises(Violation):
        loader(
            interleaved_campaign["root"] / "c2",
            result.final_checkpoint_commit["commit_id"],
            expected_previous_commit_id="f" * 64,
            predecessor_store_root=interleaved_campaign["root"] / "c1",
        )


@pytest.mark.parametrize(
    ("checkpoint", "attack"),
    (
        ("c1", "schema"),
        ("c1", "generation"),
        ("c1", "predecessor"),
        ("c2", "schema"),
        ("c2", "generation"),
        ("c2", "predecessor"),
    ),
)
def test_fully_rehashed_checkpoint_commit_semantic_attacks_fail(
    interleaved_campaign,
    tmp_path,
    checkpoint: str,
    attack: str,
) -> None:
    result = interleaved_campaign["result"]
    original_id = (
        result.first_checkpoint_commit["commit_id"]
        if checkpoint == "c1"
        else result.final_checkpoint_commit["commit_id"]
    )
    copied = tmp_path / f"{checkpoint}-{attack}"
    shutil.copytree(interleaved_campaign["root"] / checkpoint, copied)

    def mutate(document: dict) -> None:
        if attack == "schema":
            document["schema"] = "acfqp.forged_checkpoint_commit.v1"
        elif attack == "generation":
            document["generation"] = 9
        elif checkpoint == "c1":
            document["previous_commit_id"] = "a" * 64
        else:
            document["previous_commit_id"] = "b" * 64

    new_id = _fully_rehash_checkpoint_commit(
        copied, original_id, mutate
    )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            copied,
            new_id,
            expected_previous_commit_id=(
                None
                if checkpoint == "c1"
                else result.first_checkpoint_commit["commit_id"]
            ),
            predecessor_store_root=(
                None
                if checkpoint == "c1"
                else interleaved_campaign["root"] / "c1"
            ),
        )


@pytest.mark.parametrize("field", ("union", "active"))
def test_fully_rehashed_checkpoint_array_reordering_fails(
    interleaved_campaign,
    tmp_path,
    field: str,
) -> None:
    result = interleaved_campaign["result"]
    copied = tmp_path / f"c2-reordered-{field}"
    shutil.copytree(interleaved_campaign["root"] / "c2", copied)

    def mutate(payload: dict) -> None:
        name = (
            "union_lower_entries"
            if field == "union"
            else "active_lower_entry_ids"
        )
        payload[name] = list(reversed(payload[name]))

    new_id = _fully_rehash_checkpoint_payload(
        copied,
        result.final_checkpoint_commit["commit_id"],
        mutate,
    )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            copied,
            new_id,
            expected_previous_commit_id=(
                result.first_checkpoint_commit["commit_id"]
            ),
            predecessor_store_root=interleaved_campaign["root"] / "c1",
        )


@pytest.mark.parametrize(
    ("checkpoint", "directory"),
    (("c1", "blobs"), ("c1", "commits"), ("c2", "blobs"), ("c2", "commits")),
)
def test_checkpoint_child_directory_symlinks_fail(
    interleaved_campaign,
    tmp_path,
    checkpoint: str,
    directory: str,
) -> None:
    result = interleaved_campaign["result"]
    copied = tmp_path / f"{checkpoint}-{directory}-symlink"
    shutil.copytree(interleaved_campaign["root"] / checkpoint, copied)
    target = tmp_path / f"outside-{checkpoint}-{directory}"
    shutil.move(str(copied / directory), target)
    (copied / directory).symlink_to(target, target_is_directory=True)
    commit_id = (
        result.first_checkpoint_commit["commit_id"]
        if checkpoint == "c1"
        else result.final_checkpoint_commit["commit_id"]
    )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            copied,
            commit_id,
            expected_previous_commit_id=(
                None
                if checkpoint == "c1"
                else result.first_checkpoint_commit["commit_id"]
            ),
            predecessor_store_root=(
                None
                if checkpoint == "c1"
                else interleaved_campaign["root"] / "c1"
            ),
        )


@pytest.mark.parametrize("attack", ("persisted_root_count", "root_entry"))
def test_fully_rehashed_checkpoint_root_persistence_attacks_fail(
    interleaved_campaign,
    tmp_path,
    attack: str,
) -> None:
    result = interleaved_campaign["result"]
    copied = tmp_path / f"c2-{attack}"
    shutil.copytree(interleaved_campaign["root"] / "c2", copied)
    forged_root = copy.deepcopy(
        result.worker_executions[-1].occurrence_result[
            "candidate_roots"
        ][0]
    )

    def mutate(payload: dict) -> None:
        if attack == "persisted_root_count":
            payload["persisted_root_count"] = 1
        else:
            # Preserve the 58-record cardinality so this tests the closed
            # lower-record schema rather than only a length mismatch.
            payload["union_lower_entries"][0] = forged_root

    new_id = _fully_rehash_checkpoint_payload(
        copied,
        result.final_checkpoint_commit["commit_id"],
        mutate,
    )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            copied,
            new_id,
            expected_previous_commit_id=(
                result.first_checkpoint_commit["commit_id"]
            ),
            predecessor_store_root=interleaved_campaign["root"] / "c1",
        )


@pytest.mark.parametrize(
    "attack",
    ("horizon", "model", "query_scope"),
)
def test_fully_rehashed_eligibility_scope_escalation_fails(
    interleaved_campaign,
    tmp_path,
    attack: str,
) -> None:
    result = interleaved_campaign["result"]
    copied = tmp_path / f"c2-eligibility-{attack}"
    shutil.copytree(interleaved_campaign["root"] / "c2", copied)

    def mutate(payload: dict) -> None:
        eligibility = payload["eligibility"]
        if attack == "horizon":
            eligibility["horizon"] = 3
        elif attack == "model":
            eligibility["model_id"] = "a" * 64
        else:
            eligibility["query_ids"] = eligibility["query_ids"][:-1]
        eligibility.pop("eligibility_id", None)
        eligibility["eligibility_id"] = interleaved._content_id(
            "eligibility", eligibility
        )

    new_id = _fully_rehash_checkpoint_payload(
        copied,
        result.final_checkpoint_commit["commit_id"],
        mutate,
    )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            copied,
            new_id,
            expected_previous_commit_id=(
                result.first_checkpoint_commit["commit_id"]
            ),
            predecessor_store_root=interleaved_campaign["root"] / "c1",
        )


def test_first_epoch_query_facets_cannot_be_transplanted_into_final_store(
    interleaved_campaign,
    tmp_path,
) -> None:
    result = interleaved_campaign["result"]
    first_payload, _ = interleaved._load_facet_store(
        interleaved_campaign["root"] / "facets-c1",
        result.first_final_facet_commit["commit_id"],
    )
    assert len(first_payload["entries"]) == 8
    copied = tmp_path / "facets-c2-transplanted-c1"
    shutil.copytree(
        interleaved_campaign["root"] / "facets-c2", copied
    )

    def mutate(payload: dict) -> None:
        assert len(payload["entries"]) == 8
        payload["entries"] = copy.deepcopy(first_payload["entries"])

    new_id = _fully_rehash_facet_tip(
        copied,
        result.final_final_facet_commit["commit_id"],
        mutate,
    )
    with pytest.raises(Violation):
        interleaved._load_facet_store(copied, new_id)


@pytest.mark.parametrize(
    "field_name",
    ("query_id", "eligibility_id", "source_d_entry_id"),
)
def test_fully_rehashed_facet_context_cannot_escape_checkpoint_metric(
    interleaved_campaign,
    field_name: str,
) -> None:
    result = interleaved_campaign["result"]
    execution = next(
        item
        for item in result.worker_executions
        if item.execution_label == "O1_FIRST"
    )
    checkpoint = result.first_checkpoint_payload
    if field_name == "query_id":
        forged_value = result.preregistration.queries[1].query_id
    elif field_name == "eligibility_id":
        forged_value = result.final_checkpoint_payload[
            "eligibility"
        ]["eligibility_id"]
    else:
        original = execution.occurrence_result[
            "appended_facet_entries"
        ][0]["key"]["source_d_entry_id"]
        forged_value = next(
            metric["ordered_lower_entry_ids"][6]
            for metric in checkpoint["candidate_metrics"]
            if metric["ordered_lower_entry_ids"][6] != original
        )
    attacked = _fully_rehash_occurrence_facet_key(
        execution.occurrence_result,
        field_name,
        forged_value,
    )
    if field_name in {"query_id", "eligibility_id"}:
        with pytest.raises(Violation):
            interleaved._validate_occurrence_result_document(
                attacked,
                expected_after_facet_commit_id=(
                    execution.after_facet_commit_id
                ),
            )
    else:
        interleaved._validate_occurrence_result_document(
            attacked,
            expected_after_facet_commit_id=(
                execution.after_facet_commit_id
            ),
        )
        with pytest.raises(Violation):
            interleaved._validate_occurrence_checkpoint_semantics(
                attacked,
                checkpoint,
            )


def test_exact_30_to_58_partition_and_only_two_c0_reuses(
    interleaved_campaign,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    first, _ = interleaved._load_checkpoint(
        root / "c1",
        result.first_checkpoint_commit["commit_id"],
        expected_previous_commit_id=None,
        predecessor_store_root=None,
    )
    final, _ = interleaved._load_checkpoint(
        root / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=root / "c1",
    )
    first_active = set(first["active_lower_entry_ids"])
    final_active = set(final["active_lower_entry_ids"])
    final_inactive = set(final["inactive_lower_entry_ids"])
    final_union = {
        item["entry"]["entry_id"] for item in final["union_lower_entries"]
    }
    assert (len(first_active), len(final_active)) == (30, 30)
    assert len(final_union) == 58
    assert len(final_inactive) == 28
    assert first_active - final_active == final_inactive
    assert len(final_active - first_active) == 28
    shared = first_active & final_active
    assert len(shared) == 2
    slot_by_id = {
        item["entry"]["entry_id"]: item["entry"]["key"]["slot"]
        for item in final["union_lower_entries"]
    }
    assert {slot_by_id[item] for item in shared} == {"C0"}
    assert final["persisted_root_count"] == 0
    assert all(
        item["entry"]["key"]["slot"] != "R"
        for item in final["union_lower_entries"]
    )


def test_c2_requires_an_independently_loaded_c1_store(
    interleaved_campaign,
    tmp_path,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    c1_id = result.first_checkpoint_commit["commit_id"]
    c2_id = result.final_checkpoint_commit["commit_id"]
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            root / "c2",
            c2_id,
            expected_previous_commit_id=c1_id,
            predecessor_store_root=None,
        )
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            root / "c2",
            c2_id,
            expected_previous_commit_id=c1_id,
            predecessor_store_root=root / "c2",
        )
    wrong_c1 = tmp_path / "wrong-c1"
    shutil.copytree(root / "c1", wrong_c1)
    payload_path, _, _, _ = _checkpoint_paths(
        tmp_path, "wrong-c1", c1_id
    )
    payload_path.write_bytes(payload_path.read_bytes() + b"\n")
    with pytest.raises(Violation):
        interleaved._load_checkpoint(
            root / "c2",
            c2_id,
            expected_previous_commit_id=c1_id,
            predecessor_store_root=wrong_c1,
        )


@pytest.mark.parametrize(
    "attack",
    (
        "missing_historical_record",
        "extra_inactive_id",
        "changed_historical_record",
        "wrong_shared_c0",
    ),
)
def test_cross_store_lineage_rejects_fully_rehashed_semantic_attacks(
    interleaved_campaign,
    attack: str,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    first, first_commit = interleaved._load_checkpoint(
        root / "c1",
        result.first_checkpoint_commit["commit_id"],
        expected_previous_commit_id=None,
        predecessor_store_root=None,
    )
    final, final_commit = interleaved._load_checkpoint(
        root / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=root / "c1",
    )
    attacked = copy.deepcopy(final)
    first_active = set(first["active_lower_entry_ids"])
    final_active = set(final["active_lower_entry_ids"])
    shared = first_active & final_active
    if attack == "missing_historical_record":
        historical_id = next(iter(first_active - shared))
        attacked["union_lower_entries"] = [
            item
            for item in attacked["union_lower_entries"]
            if item["entry"]["entry_id"] != historical_id
        ]
    elif attack == "extra_inactive_id":
        attacked["inactive_lower_entry_ids"].append(
            next(iter(final_active))
        )
    elif attack == "changed_historical_record":
        historical_id = next(iter(first_active))
        record = next(
            item
            for item in attacked["union_lower_entries"]
            if item["entry"]["entry_id"] == historical_id
        )
        record["value_document"]["cross_store_forgery"] = True
    else:
        shared_id = next(iter(shared))
        new_id = next(iter(final_active - first_active))
        attacked["active_lower_entry_ids"] = sorted(
            new_id if value == shared_id else value
            for value in attacked["active_lower_entry_ids"]
        )
        attacked["inactive_lower_entry_ids"] = sorted(
            set(
                item["entry"]["entry_id"]
                for item in attacked["union_lower_entries"]
            )
            - set(attacked["active_lower_entry_ids"])
        )
    with pytest.raises(Violation):
        interleaved._validate_cross_store_checkpoint_lineage(
            first,
            first_commit,
            attacked,
            final_commit,
        )


def test_each_of_28_stale_first_core_nodes_is_rejected_if_reactivated(
    interleaved_campaign,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    final, _ = interleaved._load_checkpoint(
        root / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=root / "c1",
    )
    stale = tuple(final["inactive_lower_entry_ids"])
    assert len(stale) == 28
    for stale_id in stale:
        attacked = copy.deepcopy(final)
        attacked["active_lower_entry_ids"][0] = stale_id
        attacked["active_lower_entry_ids"] = sorted(
            set(attacked["active_lower_entry_ids"])
        )
        # Preserve cardinality so rejection cannot be attributed only to a
        # trivial 31-entry active set.
        if len(attacked["active_lower_entry_ids"]) != 30:
            replacement = next(
                value
                for value in final["active_lower_entry_ids"]
                if value not in attacked["active_lower_entry_ids"]
            )
            attacked["active_lower_entry_ids"].append(replacement)
            attacked["active_lower_entry_ids"].sort()
        attacked["inactive_lower_entry_ids"] = sorted(
            {
                item["entry"]["entry_id"]
                for item in attacked["union_lower_entries"]
            }
            - set(attacked["active_lower_entry_ids"])
        )
        attacked.pop("payload_id")
        attacked["payload_id"] = interleaved._checkpoint_payload_id(
            attacked
        )
        with pytest.raises(Violation):
            interleaved._validate_checkpoint_payload(attacked)


@pytest.mark.parametrize("slot", ("E", "F"))
def test_stale_strict_gate_entries_cannot_overwrite_final_core(
    interleaved_campaign,
    slot: str,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    final, _ = interleaved._load_checkpoint(
        root / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=root / "c1",
    )
    by_id = {
        item["entry"]["entry_id"]: item
        for item in final["union_lower_entries"]
    }
    stale_id = next(
        value
        for value in final["inactive_lower_entry_ids"]
        if by_id[value]["entry"]["key"]["slot"] == slot
    )
    active_id = next(
        value
        for value in final["active_lower_entry_ids"]
        if by_id[value]["entry"]["key"]["slot"] == slot
    )
    attacked = copy.deepcopy(final)
    attacked["active_lower_entry_ids"] = sorted(
        stale_id if value == active_id else value
        for value in attacked["active_lower_entry_ids"]
    )
    attacked["inactive_lower_entry_ids"] = sorted(
        set(by_id) - set(attacked["active_lower_entry_ids"])
    )
    attacked.pop("payload_id")
    attacked["payload_id"] = interleaved._checkpoint_payload_id(
        attacked
    )
    with pytest.raises(Violation):
        interleaved._validate_checkpoint_payload(attacked)


def test_forcing_either_c0_reuse_to_miss_is_rejected(
    interleaved_campaign,
) -> None:
    root = interleaved_campaign["root"]
    result = interleaved_campaign["result"]
    first, _ = interleaved._load_checkpoint(
        root / "c1",
        result.first_checkpoint_commit["commit_id"],
        expected_previous_commit_id=None,
        predecessor_store_root=None,
    )
    final, _ = interleaved._load_checkpoint(
        root / "c2",
        result.final_checkpoint_commit["commit_id"],
        expected_previous_commit_id=(
            result.first_checkpoint_commit["commit_id"]
        ),
        predecessor_store_root=root / "c1",
    )
    shared = set(first["active_lower_entry_ids"]) & set(
        final["active_lower_entry_ids"]
    )
    assert len(shared) == 2
    for c0_id in shared:
        attacked = copy.deepcopy(final)
        replacement = next(
            value
            for value in final["inactive_lower_entry_ids"]
            if value != c0_id
        )
        attacked["active_lower_entry_ids"] = sorted(
            replacement if value == c0_id else value
            for value in attacked["active_lower_entry_ids"]
        )
        attacked["inactive_lower_entry_ids"] = sorted(
            {
                item["entry"]["entry_id"]
                for item in attacked["union_lower_entries"]
            }
            - set(attacked["active_lower_entry_ids"])
        )
        attacked.pop("payload_id")
        attacked["payload_id"] = interleaved._checkpoint_payload_id(
            attacked
        )
        with pytest.raises(Violation):
            interleaved._validate_checkpoint_payload(attacked)


def test_worker_processes_are_model_only_and_host_reconstructed(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    assert len(result.worker_executions) == 6
    for execution in result.worker_executions:
        worker = execution.occurrence_result
        assert execution.fresh_os_process is True
        assert execution.exclusive_worker_output is True
        assert execution.host_exact_reconstruction_match is True
        assert worker["ground_transition_calls"] == 0
        assert worker["matching_buffer_imported"] is False
        assert worker["live_epoch_module_imported"] is False

    tree = ast.parse(
        Path(interleaved.__file__).read_text(encoding="utf-8")
    )
    top_level_imports = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            top_level_imports.add(node.module)
    assert "acfqp.domains.matching_buffer" not in top_level_imports
    assert (
        "acfqp.live_query_local_epoch_invalidation_v1"
        not in top_level_imports
    )
    assert "acfqp.multistep_query_refinement_v1" not in top_level_imports


def test_final_worker_protocol_binds_and_snapshots_all_three_stores() -> None:
    launcher = interleaved._launch_interleaved_worker
    assert "checkpoint_predecessor_store_root" in inspect.signature(
        launcher
    ).parameters
    source = inspect.getsource(launcher)
    assert source.count("_directory_snapshot_id(") == 6
    assert source.count("PREDECESSOR_CHECKPOINT_BEFORE") == 2
    assert source.index("checkpoint_predecessor_store_root.resolve()") < (
        source.index("subprocess.Popen")
    )
    assert source.index("subprocess.Popen") < source.rindex(
        "PREDECESSOR_CHECKPOINT_BEFORE"
    )


def test_worker_semantic_poison_is_rejected_by_host_reconstruction(
    interleaved_campaign,
    tmp_path,
    monkeypatch,
) -> None:
    result = interleaved_campaign["result"]
    predecessor_root = tmp_path / "c1"
    checkpoint_root = tmp_path / "c2"
    facet_root = tmp_path / "facets-c2"
    shutil.copytree(
        interleaved_campaign["root"] / "c1", predecessor_root
    )
    shutil.copytree(
        interleaved_campaign["root"] / "c2", checkpoint_root
    )
    shutil.copytree(
        interleaved_campaign["root"] / "facets-c2", facet_root
    )
    query = next(
        item
        for item in result.preregistration.queries
        if item.query_code == "Q_R"
    )
    occurrence = result.preregistration.occurrences[4]
    original_read = interleaved._read_canonical

    def poisoned_read(path: Path):
        document, size = original_read(path)
        if path.name != "result.json":
            return document, size
        poisoned = copy.deepcopy(document)
        certificate = poisoned["certificate"]
        certificate["failure_upper"] = {
            "numerator": 1,
            "denominator": 1,
        }
        poisoned["ground_transition_calls"] = 1
        poisoned["matching_buffer_imported"] = True
        poisoned["live_epoch_module_imported"] = True
        certificate.pop("certificate_id", None)
        certificate["certificate_id"] = interleaved._content_id(
            "certificate", certificate
        )
        poisoned.pop("result_id", None)
        poisoned["result_id"] = interleaved._content_id(
            "occurrence_result", poisoned
        )
        return poisoned, size

    monkeypatch.setattr(interleaved, "_read_canonical", poisoned_read)
    with pytest.raises(
        Violation, match="worker result differs from host lease replay"
    ):
        interleaved._launch_interleaved_worker(
            tmp_path / "poison-campaign",
            "MAIN_GLOBAL_FACETS",
            "O5_FINAL",
            checkpoint_root,
            result.final_checkpoint_commit["commit_id"],
            result.first_checkpoint_commit["commit_id"],
            predecessor_root,
            facet_root,
            result.final_final_facet_commit["commit_id"],
            query,
            occurrence,
        )


def test_final_worker_cannot_bind_c1_or_transplant_occurrence_role(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    workers = result.worker_executions
    o3 = workers[3]
    o5 = workers[5]
    with pytest.raises(Violation):
        attacked_document = copy.deepcopy(o3.occurrence_result)
        attacked_document["checkpoint_commit_id"] = (
            result.first_checkpoint_commit["commit_id"]
        )
        attacked_document.pop("result_id", None)
        attacked_document["result_id"] = interleaved._content_id(
            "occurrence_result", attacked_document
        )
        replace(
            o3,
            checkpoint_commit_id=(
                result.first_checkpoint_commit["commit_id"]
            ),
            occurrence_result=attacked_document,
        )
    with pytest.raises(Violation):
        transplanted = replace(
            o5,
            occurrence_result=copy.deepcopy(o3.occurrence_result),
        )
        replace(
            result,
            worker_executions=(*workers[:5], transplanted),
            _instance_mint=None,
        )


def test_global_and_matched_reset_logical_facet_traces_are_exact(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    global_by_label = {
        item.execution_label: item for item in result.worker_executions
    }
    logical_labels = (
        "O1_FIRST",
        "O2_RECERTIFIED_FINAL",
        "O3_FINAL",
        "O4_FINAL",
        "O5_FINAL",
    )
    global_trace = tuple(
        (
            global_by_label[label].occurrence_result[
                "query_facet_builder_calls"
            ],
            global_by_label[label].occurrence_result[
                "lower_identity_hits"
            ],
        )
        for label in logical_labels
    )
    assert global_trace == (
        (8, 42),
        (0, 50),
        (8, 42),
        (0, 50),
        (0, 50),
    )
    assert tuple(map(sum, zip(*global_trace))) == (16, 234)
    global_native_trace = tuple(
        (
            item.occurrence_result["query_facet_builder_calls"],
            item.occurrence_result["lower_identity_hits"],
        )
        for item in result.worker_executions
    )
    assert tuple(map(sum, zip(*global_native_trace))) == (16, 284)

    reset_executions = result.matched_reset_worker_executions
    assert type(reset_executions) is tuple
    assert len(reset_executions) == 6
    reset_by_label = {
        item.execution_label: item for item in reset_executions
    }
    assert set(reset_by_label) == set(global_by_label)
    reset_trace = tuple(
        (
            reset_by_label[label].occurrence_result[
                "query_facet_builder_calls"
            ],
            reset_by_label[label].occurrence_result[
                "lower_identity_hits"
            ],
        )
        for label in logical_labels
    )
    assert reset_trace == (
        (8, 42),
        (0, 50),
        (8, 42),
        (0, 50),
        (8, 42),
    )
    assert tuple(map(sum, zip(*reset_trace))) == (24, 226)
    reset_native_trace = tuple(
        (
            item.occurrence_result["query_facet_builder_calls"],
            item.occurrence_result["lower_identity_hits"],
        )
        for item in reset_executions
    )
    assert tuple(map(sum, zip(*reset_native_trace))) == (24, 276)
    assert tuple(
        left + right
        for left, right in zip(
            tuple(map(sum, zip(*global_native_trace))),
            tuple(map(sum, zip(*reset_native_trace))),
        )
    ) == (40, 560)
    accounting = result.accounting
    assert accounting["host_verification_counter_scope"] == (
        "OPERATIONAL_PRE_ACCOUNTING_REGISTERED_CHECKS_ONLY"
    )
    assert (
        accounting["host_checkpoint_store_load_count"],
        accounting["host_cross_store_lineage_check_count"],
        accounting["host_facet_store_load_count"],
        accounting[
            "host_worker_result_reconstruction_comparison_count"
        ],
        accounting["host_input_snapshot_hash_count"],
        accounting["host_immutability_comparison_count"],
        accounting["host_worker_semantic_assertion_count"],
    ) == (23, 9, 36, 12, 64, 32, 12)
    assert (
        accounting[
            "main_host_worker_result_reconstruction_comparison_count"
        ],
        accounting[
            "reset_host_worker_result_reconstruction_comparison_count"
        ],
        accounting["main_host_worker_semantic_assertion_count"],
        accounting["reset_host_worker_semantic_assertion_count"],
    ) == (6, 6, 6, 6)
    assert all(
        (
            item.host_result_reconstruction_comparison_count,
            item.host_semantic_assertion_count,
        )
        == (1, 1)
        for item in (
            *result.worker_executions,
            *result.matched_reset_worker_executions,
        )
    )
    assert (
        accounting["main_native_query_facet_builder_calls"],
        accounting["main_native_lower_identity_hits"],
        accounting["reset_native_query_facet_builder_calls"],
        accounting["reset_native_lower_identity_hits"],
        accounting["campaign_native_query_facet_builder_calls"],
        accounting["campaign_native_lower_identity_hits"],
        accounting["main_logical_query_facet_builder_calls"],
        accounting["main_logical_lower_identity_hits"],
        accounting["reset_logical_query_facet_builder_calls"],
        accounting["reset_logical_lower_identity_hits"],
        accounting["fresh_worker_process_count"],
    ) == (16, 284, 24, 276, 40, 560, 16, 234, 24, 226, 12)
    assert (
        accounting["main_native_fresh_root_builder_calls"],
        accounting["reset_native_fresh_root_builder_calls"],
        accounting["campaign_native_fresh_root_builder_calls"],
        accounting["logical_occurrence_count"],
        accounting["main_fresh_worker_process_count"],
        accounting["reset_fresh_worker_process_count"],
        accounting["worker_ground_transition_calls"],
        accounting["round_one_ground_transition_calls"],
        accounting["certificate_triggered_ground_transition_calls"],
        accounting["source_ground_transition_calls"],
        accounting["boundary_catalogue_calls"],
        accounting["epoch_lower_recomputations"],
        accounting["epoch_lower_lookup_reuses"],
        accounting["epoch_distinct_entry_reuses"],
        accounting["epoch_reused_slots"],
    ) == (30, 30, 60, 5, 6, 6, 0, 4, 9, 13, 3, 28, 22, 2, ["C0"])
    recert = reset_by_label[
        "O2_RECERTIFIED_FINAL"
    ].occurrence_result
    assert (
        recert["query_facet_builder_calls"],
        recert["lower_identity_hits"],
    ) == (0, 50)
    assert recert["ground_transition_calls"] == 0


def test_typed_23_event_ledger_delete_reorder_and_rehash_attacks_fail(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    source = result.source_chain
    main_by_label = {
        item.execution_label: item for item in result.worker_executions
    }
    assert not hasattr(result, "events")
    event_log = result.event_log
    events = event_log.events
    assert type(events) is tuple
    assert len(events) == 23
    assert tuple(item.sequence_number for item in events) == tuple(
        range(1, 24)
    )
    assert tuple(item.event_kind for item in events) == EXPECTED_EVENT_ORDER
    occurrence_ids = tuple(
        item.occurrence_id for item in result.preregistration.occurrences
    )
    assert tuple(item.artifact_id for item in events) == (
        result.preregistration.preregistration_id,
        interleaved._query_eligibility_freeze_id(
            result.preregistration
        ),
        interleaved_campaign["failed_audit"].result_id,
        source["round_one_bundle"]["bundle_id"],
        source["boundary_expansion"]["expansion_id"],
        interleaved._EXPECTED_EPOCH_MODEL_IDS["FIRST"],
        result.first_checkpoint_commit["commit_id"],
        occurrence_ids[0],
        main_by_label["O1_FIRST"].execution_id,
        occurrence_ids[1],
        main_by_label["O2_FAILED_FIRST"].execution_id,
        source["round_two_request"]["request_id"],
        result.ground_repair_authorization.authorization_id,
        source["round_two_bundle"]["bundle_id"],
        interleaved._EXPECTED_EPOCH_MODEL_IDS["FINAL"],
        source["invalidation_manifest"]["manifest_id"],
        result.final_checkpoint_commit["commit_id"],
        occurrence_ids[1],
        main_by_label["O2_RECERTIFIED_FINAL"].execution_id,
        main_by_label["O3_FINAL"].execution_id,
        main_by_label["O4_FINAL"].execution_id,
        main_by_label["O5_FINAL"].execution_id,
        result.accounting["accounting_id"],
    )
    assert tuple(
        (
            item.cumulative_ground_transition_calls,
            item.cumulative_round_one_ground_transition_calls,
            item.cumulative_round_two_ground_transition_calls,
            item.cumulative_boundary_catalogue_calls,
            item.cumulative_main_worker_process_count,
            item.cumulative_reset_worker_process_count,
        )
        for item in events
    ) == (
        (0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0),
        (4, 4, 0, 0, 0, 0),
        (4, 4, 0, 3, 0, 0),
        (4, 4, 0, 3, 0, 0),
        (4, 4, 0, 3, 0, 0),
        (4, 4, 0, 3, 0, 0),
        (4, 4, 0, 3, 1, 0),
        (4, 4, 0, 3, 1, 0),
        (4, 4, 0, 3, 2, 0),
        (4, 4, 0, 3, 2, 0),
        (4, 4, 0, 3, 2, 0),
        (13, 4, 9, 3, 2, 0),
        (13, 4, 9, 3, 2, 0),
        (13, 4, 9, 3, 2, 0),
        (13, 4, 9, 3, 2, 0),
        (13, 4, 9, 3, 2, 0),
        (13, 4, 9, 3, 3, 0),
        (13, 4, 9, 3, 4, 0),
        (13, 4, 9, 3, 5, 0),
        (13, 4, 9, 3, 6, 0),
        (13, 4, 9, 3, 6, 6),
    )
    no_occurrence = {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_OCCURRENCE_CONTEXT",
    }
    no_epoch = {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_EPOCH_CONTEXT",
    }
    expected_occurrence_context = (
        (no_occurrence,) * 7
        + (1, 1)
        + (2,) * 10
        + (3, 4, 5)
        + (no_occurrence,)
    )
    expected_epoch_context = (
        (no_epoch,) * 2
        + ("FIRST",) * 12
        + ("FINAL",) * 8
        + (no_epoch,)
    )
    assert tuple(
        item.occurrence_index for item in events
    ) == expected_occurrence_context
    assert tuple(
        item.epoch_name for item in events
    ) == expected_epoch_context
    assert event_log.preregistration_id == (
        result.preregistration.preregistration_id
    )
    assert event_log.final_event_count == 23
    event_root = interleaved_campaign["root"] / "events"
    event_paths = tuple(
        event_root / f"{index:02d}-{kind}.json"
        for index, kind in enumerate(EXPECTED_EVENT_ORDER, 1)
    )
    assert {item.name for item in event_root.iterdir()} == {
        *(path.name for path in event_paths),
        "event-log.json",
    }
    assert tuple(_read_json(path) for path in event_paths) == tuple(
        item.to_document() for item in events
    )
    assert _read_json(event_root / "event-log.json") == (
        event_log.to_document()
    )
    assert tuple(path.stat().st_mtime_ns for path in event_paths) == tuple(
        sorted(path.stat().st_mtime_ns for path in event_paths)
    )
    assert events[0].previous_event_id == {
        "kind": "NOT_APPLICABLE",
        "reason": "EVENT_LOG_GENESIS",
    }
    assert tuple(
        item.previous_event_id for item in events[1:]
    ) == tuple(item.event_id for item in events[:-1])
    for attacked in (
        events[:-1],
        (events[1], events[0], *events[2:]),
    ):
        with pytest.raises(Violation):
            replace(event_log, events=attacked)
    readdressed = replace(
        events[10],
        artifact_id=events[9].artifact_id,
    )
    with pytest.raises(Violation):
        replace(
            event_log,
            events=(*events[:10], readdressed, *events[11:]),
        )
    for counter_field in (
        "cumulative_ground_transition_calls",
        "cumulative_round_one_ground_transition_calls",
        "cumulative_round_two_ground_transition_calls",
        "cumulative_boundary_catalogue_calls",
        "cumulative_main_worker_process_count",
        "cumulative_reset_worker_process_count",
    ):
        with pytest.raises(Violation):
            changed_counter = replace(
                events[18],
                **{
                    counter_field: (
                        getattr(events[18], counter_field) + 1
                    ),
                    "_instance_mint": None,
                },
            )
            replace(
                event_log,
                events=(
                    *events[:18],
                    changed_counter,
                    *events[19:],
                ),
                _instance_mint=None,
            )
    for event_index, field_name, attacked_value in (
        (7, "occurrence_index", 2),
        (14, "occurrence_index", 3),
        (7, "epoch_name", "FINAL"),
        (14, "epoch_name", "FIRST"),
    ):
        with pytest.raises(Violation):
            changed_context = replace(
                events[event_index],
                **{
                    field_name: attacked_value,
                    "_instance_mint": None,
                },
            )
            replace(
                event_log,
                events=(
                    *events[:event_index],
                    changed_context,
                    *events[event_index + 1 :],
                ),
                _instance_mint=None,
            )


def test_result_and_accounting_tampering_fail_at_semantic_boundary(
    interleaved_campaign,
) -> None:
    result = interleaved_campaign["result"]
    with pytest.raises(Violation):
        interleaved.require_interleaved_durable_epoch_result_v1(
            copy.copy(result)
        )
    for counter_field in (
        "host_checkpoint_store_load_count",
        "host_cross_store_lineage_check_count",
        "host_facet_store_load_count",
        "host_worker_result_reconstruction_comparison_count",
        "host_input_snapshot_hash_count",
        "host_immutability_comparison_count",
        "host_worker_semantic_assertion_count",
        "certificate_triggered_ground_transition_calls",
    ):
        attacked_accounting = copy.deepcopy(result.accounting)
        attacked_accounting[counter_field] += 1
        attacked_accounting.pop("accounting_id", None)
        attacked_accounting["accounting_id"] = interleaved._content_id(
            "accounting", attacked_accounting
        )
        with pytest.raises(Violation):
            replace(
                result,
                accounting=attacked_accounting,
                _instance_mint=None,
            )
    for attack in ("delete", "scope", "evaluation_injection"):
        attacked_accounting = copy.deepcopy(result.accounting)
        if attack == "delete":
            attacked_accounting.pop("host_facet_store_load_count")
        elif attack == "scope":
            attacked_accounting["host_verification_counter_scope"] = (
                "FORGED_EVALUATION_AND_OPERATIONAL_MIX"
            )
        else:
            attacked_accounting[
                "claimed_result_semantic_validation_count"
            ] = 1
        attacked_accounting.pop("accounting_id", None)
        attacked_accounting["accounting_id"] = interleaved._content_id(
            "accounting", attacked_accounting
        )
        with pytest.raises(Violation):
            replace(
                result,
                accounting=attacked_accounting,
                _instance_mint=None,
            )
    with pytest.raises(Violation):
        replace(result, policy_switch_claimed=True, _instance_mint=None)
    for claim_field in (
        "promotion_authorized",
        "learned_dynamics_claimed",
        "coordinate_invention_claimed",
        "sample_efficiency_claimed",
        "workload_economics_claimed",
        "official_execution_allowed",
    ):
        with pytest.raises(Violation):
            replace(
                result,
                **{claim_field: True, "_instance_mint": None},
            )
    with pytest.raises(Violation):
        replace(
            result,
            event_log=replace(
                result.event_log,
                events=(
                    result.event_log.events[1],
                    result.event_log.events[0],
                    *result.event_log.events[2:],
                ),
            ),
            _instance_mint=None,
        )


def test_full_evaluation_replay_is_exact_and_original_store_is_unchanged(
    interleaved_campaign,
    interleaved_verification,
) -> None:
    result = interleaved_campaign["result"]
    report = interleaved_verification
    assert report.claimed_result_id == result.result_id
    assert report.replayed_result_id == result.result_id
    assert report.original_campaign_snapshot_id == (
        result.campaign_snapshot_id
    )
    assert report.exact_document_match is True
    assert report.evaluation_ground_transition_calls == 13
    assert report.evaluation_worker_process_launches == 12
    assert (
        report.evaluation_host_checkpoint_store_load_count,
        report.evaluation_host_cross_store_lineage_check_count,
        report.evaluation_host_facet_store_load_count,
        report.evaluation_host_worker_result_reconstruction_comparison_count,
        report.evaluation_host_input_snapshot_hash_count,
        report.evaluation_host_immutability_comparison_count,
        report.evaluation_host_worker_semantic_assertion_count,
        report.claimed_result_semantic_validation_count,
        report.claimed_campaign_snapshot_hash_count,
        report.replayed_document_comparison_count,
    ) == (23, 9, 36, 12, 64, 32, 12, 1, 2, 1)
    assert report.same_implementation_full_replay is True
    assert report.independent_algorithm is False
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    for field_name in (
        "evaluation_host_checkpoint_store_load_count",
        "evaluation_host_cross_store_lineage_check_count",
        "evaluation_host_facet_store_load_count",
        "evaluation_host_worker_result_reconstruction_comparison_count",
        "evaluation_host_input_snapshot_hash_count",
        "evaluation_host_immutability_comparison_count",
        "evaluation_host_worker_semantic_assertion_count",
        "claimed_result_semantic_validation_count",
        "claimed_campaign_snapshot_hash_count",
        "replayed_document_comparison_count",
    ):
        with pytest.raises(Violation):
            replace(
                report,
                **{field_name: getattr(report, field_name) + 1},
            )
