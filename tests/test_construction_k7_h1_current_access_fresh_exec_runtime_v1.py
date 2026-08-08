from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_current_access_authority_v1 as access_v1
from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "acfqp"
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


def _all_acfqp_sources() -> tuple[dict[str, bytes], dict[str, Path]]:
    sources: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        relative = path.relative_to(SOURCE_ROOT)
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        name = ".".join(("acfqp", *parts))
        sources[name] = path.read_bytes()
        paths[name] = path
    return sources, paths


@pytest.fixture(scope="module")
def current_chain():
    sources, paths = _all_acfqp_sources()
    closure = source_runtime_v2.build_construction_source_closure_v2(
        root_modules=current_v1.SOURCE_ARCHIVE_ROOT_MODULES,
        module_sources=sources,
        module_paths=paths,
    )
    archive = source_runtime_v2.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    runtime_lock = source_runtime_v2.verify_construction_runtime_dependency_lock_v2(
        dependency_lock_bytes=(ROOT / "specs" / "V075_DEPENDENCY_LOCK.json").read_bytes(),
        pyproject_bytes=(ROOT / "pyproject.toml").read_bytes(),
        timeout_seconds=30,
    )
    compiled = source_runtime_v2.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=archive,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    current_source = current_v1.issue_h1_current_source_fixture_v1(
        CANONICAL_BUNDLE,
        source_closure=closure,
        source_archive=archive,
        runtime_lock=runtime_lock,
        archive_compile_verification=compiled,
    )
    proof_bytes = durable_v1.issue_phase3e_exact_infeasibility_durable_proof_v1(
        CANONICAL_BUNDLE
    )
    identity = durable_v1.DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    legacy_current = acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )
    preexecution = acquisition_v1.replay_canonical_direct_fallback_preexecution_candidate_v1(
        proof_bytes,
        current_identity=legacy_current,
    )
    preexecution_bytes = canonical_json_bytes(preexecution.to_document())
    recipe = recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_bytes
    )
    proof_match = current_v1.issue_h1_durable_proof_match_attestation_v1(
        proof_bytes,
        current_source=current_source,
        recipe=recipe,
        preexecution_candidate_bytes=preexecution_bytes,
    )
    candidate = current_v1.freeze_h1_production_current_identity_candidate_v1(
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
    )
    candidate_verification = (
        current_v1.verify_h1_production_current_identity_candidate_bytes_v1(
            raw=candidate.canonical_bytes,
            current_source=current_source,
            proof_match_attestation=proof_match,
            recipe=recipe,
        )
    )
    return current_source, proof_match, recipe, candidate, candidate_verification


@pytest.fixture(scope="module")
def launch_chain(current_chain):
    current_source, proof_match, recipe, candidate, candidate_verification = current_chain
    profile = access_v1.official_h1_current_access_execution_profile_v1()
    context = access_v1.freeze_h1_current_access_predecision_context_v1(
        execution_profile=profile,
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
        current_identity_candidate=candidate,
        candidate_verification=candidate_verification,
        logical_occurrence_id=recipe.source.logical_occurrence_id,
        route_attempt_id=recipe.source.route_attempt_id,
        session_nonce=content_id(
            access_v1.FIXTURE_DOMAIN,
            {"schema": "acfqp.h1_current_access_runtime_test_nonce.v1"},
        ),
    )
    input_set = access_v1.freeze_h1_current_access_predecision_input_set_v1(
        execution_profile=profile,
        context=context,
    )
    raw = {
        "predecision_context_bytes": context.canonical_bytes,
        "current_source_fixture_bytes": current_source.canonical_bytes,
        "proof_match_attestation_bytes": canonical_json_bytes(
            proof_match.to_document()
        ),
        "h1_two_role_recipe_bytes": recipe.canonical_bytes,
        "current_identity_candidate_bytes": candidate.canonical_bytes,
        "candidate_verification_bytes": canonical_json_bytes(
            candidate_verification.to_document()
        ),
        "predecision_input_set": input_set,
    }
    return profile, context, input_set, raw


@pytest.fixture(scope="module")
def runtime_verification(launch_chain):
    _profile, _context, _input_set, raw = launch_chain
    result = runtime_v1.run_h1_current_access_fresh_exec_runtime_v1(**raw)
    if type(result) is runtime_v1.H1CurrentAccessRuntimeUnavailableV1:
        pytest.skip(f"native fresh-exec prerequisites unavailable: {result.reason.value}")
    assert type(result) is runtime_v1.H1CurrentAccessObservedRuntimeFactsVerificationV1
    return result


def _invalid_call() -> None:
    runtime_v1.run_h1_current_access_fresh_exec_runtime_v1(
        predecision_context_bytes=b"x",
        current_source_fixture_bytes=b"x",
        proof_match_attestation_bytes=b"x",
        h1_two_role_recipe_bytes=b"x",
        current_identity_candidate_bytes=b"x",
        candidate_verification_bytes=b"x",
        predecision_input_set=None,
    )


def test_prelaunch_source_ast_runtime_and_retention_are_exact() -> None:
    profile = runtime_v1.official_h1_current_access_fresh_exec_runtime_profile_v1()
    source = runtime_v1.official_h1_current_access_fresh_exec_source_manifest_v1()
    manifest = runtime_v1.official_h1_current_access_fresh_exec_runtime_manifest_v1()
    assert runtime_v1.require_h1_current_access_fresh_exec_runtime_profile_v1(profile) is profile
    assert runtime_v1.require_h1_current_access_fresh_exec_source_manifest_v1(source) is source
    assert runtime_v1.require_h1_current_access_fresh_exec_runtime_manifest_v1(manifest) is manifest
    source_document = source.to_document()
    assert source_document["project_imports"] == []
    assert source_document["full_ast_exact_match_required_at_prelaunch"] is True
    assert source_document["full_ast_sha256"] == runtime_v1._CHILD_SOURCE_AST_SHA256
    assert profile.to_document()["sealed_input_roles"] == list(runtime_v1.INPUT_ROLES)
    assert manifest.to_document()["python_executable"] == "/usr/bin/python3"


def test_same_length_source_and_unlisted_helper_mutations_fail_before_parsing(
    monkeypatch,
) -> None:
    source = runtime_v1._CHILD_SOURCE
    changed = ("x" if source[0] != "x" else "y") + source[1:]
    assert len(changed) == len(source)
    monkeypatch.setattr(runtime_v1, "_CHILD_SOURCE", changed)
    with pytest.raises(
        runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
        match="global object changed",
    ):
        _invalid_call()
    monkeypatch.setattr(runtime_v1, "_CHILD_SOURCE", source)
    original = runtime_v1.official_h1_current_access_fresh_exec_runtime_manifest_v1
    monkeypatch.setattr(
        runtime_v1,
        "official_h1_current_access_fresh_exec_runtime_manifest_v1",
        lambda: original(),
    )
    with pytest.raises(
        runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
        match="helper .*runtime_manifest",
    ):
        _invalid_call()


def test_fail_and_verifier_code_mutation_cannot_disable_closure_abort() -> None:
    fail_code = runtime_v1._fail.__code__
    verifier_code = runtime_v1._verify_frozen_runtime_closure_v1.__code__
    try:
        runtime_v1._fail.__code__ = (lambda _message: None).__code__
        runtime_v1._verify_frozen_runtime_closure_v1.__code__ = (
            lambda _frozen: None
        ).__code__
        with pytest.raises(
            runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
            match="public runner closure changed",
        ):
            _invalid_call()
    finally:
        runtime_v1._fail.__code__ = fail_code
        runtime_v1._verify_frozen_runtime_closure_v1.__code__ = verifier_code
    runtime_v1._verify_frozen_runtime_closure_v1(
        runtime_v1._FROZEN_RUNTIME_CLOSURE
    )


def test_import_time_missing_native_prerequisite_is_typed_unavailable() -> None:
    script = r'''
import json
from pathlib import Path
original = Path.is_file
def unavailable(self):
    if str(self) == "/usr/bin/python3":
        return False
    return original(self)
Path.is_file = unavailable
from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime
result = runtime.run_h1_current_access_fresh_exec_runtime_v1(
    predecision_context_bytes=b"x",
    current_source_fixture_bytes=b"x",
    proof_match_attestation_bytes=b"x",
    h1_two_role_recipe_bytes=b"x",
    current_identity_candidate_bytes=b"x",
    candidate_verification_bytes=b"x",
    predecision_input_set=None,
)
print(json.dumps(result.to_document(), sort_keys=True))
'''
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    document = json.loads(completed.stdout)
    assert document["reason"] == "PYTHON_EXECUTABLE_UNAVAILABLE"
    assert document["process_launches"] == 0
    assert document["observed_runtime_facts_issued"] is False
    assert document["production_current_access_evidence_issued"] is False


@pytest.mark.parametrize(
    "argument",
    (
        "predecision_context_bytes",
        "current_source_fixture_bytes",
        "proof_match_attestation_bytes",
        "h1_two_role_recipe_bytes",
        "current_identity_candidate_bytes",
        "candidate_verification_bytes",
    ),
)
def test_each_structural_input_mutation_fails_before_facts(
    launch_chain,
    argument: str,
) -> None:
    _profile, _context, _input_set, raw = launch_chain
    attacked = dict(raw)
    document = loads_canonical_json(attacked[argument])
    document["schema_version"] = "9.9.9"
    attacked[argument] = canonical_json_bytes(document)
    before = len(runtime_v1._LIVE_FACTS)
    with pytest.raises(runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error):
        runtime_v1.run_h1_current_access_fresh_exec_runtime_v1(**attacked)
    assert len(runtime_v1._LIVE_FACTS) == before


def test_real_child_observes_exact_runtime_output_and_true_pidfd_reap(
    launch_chain,
    runtime_verification,
) -> None:
    profile, context, input_set, _raw = launch_chain
    verification = runtime_verification
    assert runtime_v1.require_h1_current_access_observed_runtime_facts_verification_v1(
        verification
    ) is verification
    document = verification.facts.to_document()
    assert document["child_pid"] != document["broker_pid"]
    assert document["h1_current_access_predecision_context_id"] == context.context_id
    assert document["h1_current_access_predecision_input_set_id"] == input_set.input_set_id
    assert document["pidfd_reap_api"] == "waitid(P_PIDFD,WEXITED)"
    assert document["pidfd_reap_observed"] is True
    assert document["popen_returncode_synchronized_after_pidfd_reap"] is True
    assert len(document["child_fd_manifest"]) == 10
    assert tuple(row["role"] for row in document["sealed_inputs"]) == runtime_v1.INPUT_ROLES
    assert tuple(
        row["role"] for row in document["broker_staged_descriptor_manifest"]
    ) == runtime_v1.INPUT_ROLES
    assert all(row["seals"] & 15 == 15 for row in document["broker_staged_descriptor_manifest"])
    assert all(row["pid"] == document["child_pid"] for row in document["scm_credentials"])
    assert document["child_result_sha256"] == runtime_v1._sha(
        canonical_json_bytes(document["child_result"])
    )
    assert document["child_result_byte_count"] == len(
        canonical_json_bytes(document["child_result"])
    )
    assert document["child_result"]["project_package_imported"] is False
    assert document["child_result"]["production_current_access_authority_issued"] is False
    assert document["same_process_private_state_adversary_resistance_claimed"] is False
    assert document["concurrent_mutation_during_checkpoint_interval_excluded"] is True
    assert set(document["forbidden_operation_zero_counts"].values()) == {0}
    raw_work = document["common_prefix_raw_work"]
    assert raw_work["process_launches"] == 1
    assert raw_work["sealed_inputs_staged"] == 6
    assert raw_work["pidfd_terminal_observations"] == 1
    assert raw_work["direct_child_pidfd_reaps"] == 1
    assert raw_work["formal_counter_records_issued"] == 0
    with pytest.raises(ChildProcessError):
        os.waitpid(document["child_pid"], os.WNOHANG)
    child = access_v1.issue_h1_current_access_child_result_v1(
        execution_profile=profile,
        context=context,
        input_set=input_set,
        runtime_verification=verification,
    )
    assert child.to_document()["production_evidence_eligible"] is True


def test_success_path_contains_no_pid_based_popen_reap() -> None:
    source = inspect.getsource(
        runtime_v1._run_h1_current_access_fresh_exec_runtime_impl_v1
    )
    assert "reaped = os.waitid(os.P_PIDFD, pidfd, os.WEXITED)" in source
    assert "process.returncode = 0" in source
    assert "process.wait(" not in source


def test_forged_facts_and_unretained_verification_are_rejected(
    launch_chain,
    runtime_verification,
) -> None:
    _profile, _context, input_set, raw = launch_chain
    document = runtime_verification.facts.to_document()
    payload = dict(document)
    payload.pop("h1_current_access_observed_runtime_facts_id")
    payload["pidfd_reap_observed"] = False
    forged = {
        **payload,
        "h1_current_access_observed_runtime_facts_id": content_id(
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
            payload,
        ),
    }
    with pytest.raises(
        runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
        match="live broker observation",
    ):
        runtime_v1.verify_h1_current_access_observed_runtime_facts_bytes_v1(
            canonical_json_bytes(forged),
            predecision_context_bytes=raw["predecision_context_bytes"],
            current_source_fixture_bytes=raw["current_source_fixture_bytes"],
            proof_match_attestation_bytes=raw["proof_match_attestation_bytes"],
            h1_two_role_recipe_bytes=raw["h1_two_role_recipe_bytes"],
            current_identity_candidate_bytes=raw["current_identity_candidate_bytes"],
            candidate_verification_bytes=raw["candidate_verification_bytes"],
            predecision_input_set=input_set,
        )
    shell = object.__new__(
        runtime_v1.H1CurrentAccessObservedRuntimeFactsVerificationV1
    )
    with pytest.raises(
        runtime_v1.ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
        match="not retained",
    ):
        runtime_v1.require_h1_current_access_observed_runtime_facts_verification_v1(
            shell
        )
