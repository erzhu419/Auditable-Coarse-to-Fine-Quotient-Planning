from __future__ import annotations

import copy
from dataclasses import replace
import inspect
from pathlib import Path

import pytest

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable_v1
from acfqp import phase3e_ids
from acfqp import phase3e_fallback_v1
from acfqp.abstraction import oracle as oracle_v1
from acfqp.planning import ground as ground_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


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
def source_chain():
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
    return closure, archive, runtime_lock, compiled


@pytest.fixture(scope="module")
def current_source(source_chain):
    closure, archive, runtime_lock, compiled = source_chain
    return current_v1.issue_h1_current_source_fixture_v1(
        CANONICAL_BUNDLE,
        source_closure=closure,
        source_archive=archive,
        runtime_lock=runtime_lock,
        archive_compile_verification=compiled,
    )


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return durable_v1.issue_phase3e_exact_infeasibility_durable_proof_v1(
        CANONICAL_BUNDLE
    )


@pytest.fixture(scope="module")
def legacy_current(proof_bytes: bytes):
    identity = durable_v1.DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    return acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )


@pytest.fixture(scope="module")
def preexecution_candidate_bytes(proof_bytes: bytes, legacy_current) -> bytes:
    candidate = acquisition_v1.replay_canonical_direct_fallback_preexecution_candidate_v1(
        proof_bytes,
        current_identity=legacy_current,
    )
    return canonical_json_bytes(candidate.to_document())


@pytest.fixture(scope="module")
def recipe(preexecution_candidate_bytes: bytes):
    return recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_candidate_bytes
    )


@pytest.fixture(scope="module")
def proof_match(
    proof_bytes: bytes,
    current_source,
    recipe,
    preexecution_candidate_bytes: bytes,
):
    return current_v1.issue_h1_durable_proof_match_attestation_v1(
        proof_bytes,
        current_source=current_source,
        recipe=recipe,
        preexecution_candidate_bytes=preexecution_candidate_bytes,
    )


@pytest.fixture(scope="module")
def candidate(current_source, proof_match, recipe):
    return current_v1.freeze_h1_production_current_identity_candidate_v1(
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
    )


def test_domains_profile_and_all_execution_gates_are_exact() -> None:
    assert current_v1.PROPOSED_CONTRACT_VERSION == "2.0.52"
    assert current_v1.PROFILE_KEY == (
        "construction_k7_h1_production_current_identity_v1"
    )
    assert len(set(current_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 6
    assert set(current_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= (
        phase3e_ids.PHASE3E_DOMAIN_TAGS
    )
    assert current_v1.CONSTRUCTION_ONLY is True
    assert current_v1.PRODUCTION_CURRENT_IDENTITY_CANDIDATE_PRESENT is True
    assert current_v1.PRODUCTION_CURRENT_IDENTITY_AUTHORITY_PRESENT is False
    assert current_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert current_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert current_v1.COUNTER_COMPLETENESS_GATE_STATUS.endswith("NOT_RUN")
    assert current_v1.WORKLOAD_ECONOMICS_GATE_STATUS.endswith("NOT_RUN")
    assert current_v1.SAMPLE_EFFICIENCY_GATE_STATUS.endswith("NOT_RUN")


def test_independent_source_has_exact_eight_coordinate_identity_and_archive_chain(
    current_source,
    source_chain,
) -> None:
    closure, archive, runtime_lock, compiled = source_chain
    identity = current_source.identity
    assert current_source.build_kernel.source_closure_id == closure.closure_id
    assert current_source.build_kernel.source_archive_id == archive.archive_id
    assert current_source.build_kernel.runtime_lock_verification_id == (
        runtime_lock.verification_id
    )
    assert current_source.build_kernel.archive_compile_verification_id == (
        compiled.verification_id
    )
    assert current_source.build_kernel.structural_id == identity.structural_id
    assert current_source.query.query_id == identity.query_id
    assert current_source.build_kernel.build_epoch_id == identity.build_epoch_id
    assert current_source.build_kernel.kernel_id == identity.kernel_id
    assert current_source.query.threshold_profile_id == identity.threshold_profile_id
    assert current_source.query.reward_profile_id == identity.reward_profile_id
    assert current_source.query.policy_class_id == identity.policy_class_id
    assert current_source.query.complete_search_profile_id == (
        identity.complete_search_profile_id
    )
    document = current_source.to_document()
    assert document["current_source_issued_before_claimant_comparison"] is True
    assert document["preregistered_current_identity_id"] == (
        current_v1.EXPECTED_CURRENT_IDENTITY.exact_infeasibility_identity_id
    )
    assert document["selected_bundle_bytes_matched_before_semantic_verifier"] is True
    assert document["current_identity_derived_from_selected_bundle_output"] is False
    assert document["current_source_api_accepts_claimant_proof"] is False
    assert document["claimant_identity_used_as_current"] is False
    assert document["semantic_replay_lane"] == "EVALUATION"
    assert document["charged_as_operational_route_work"] is False
    assert document["source_archive_role"] == (
        "CALLER_SUPPLIED_SELF_CONSISTENT_COMPILE_FIXTURE"
    )
    assert document["live_current_issuer_source_provenance_proven"] is False
    assert document["issuer_code_provenance_proven"] is False
    build_document = current_source.build_kernel.to_document()
    assert build_document["source_archive_proves_live_current_issuer_source"] is False
    assert build_document["source_archive_proves_issuer_code_provenance"] is False
    assert build_document["source_archive_semantic_authority"] is False


def test_claimant_proof_match_is_validated_and_plan_bound_without_revocation(
    current_source,
    proof_match,
    recipe,
) -> None:
    document = proof_match.to_document()
    result = document["verification_result"]
    assert proof_match.current_source_fixture_id == current_source.fixture_id
    assert result["outcome"] == "IDENTICAL_MATCH"
    assert result["minimum_failure_probability"].numerator == 383
    assert result["minimum_failure_probability"].denominator == 410
    assert result["proof_identity_id"] == result["current_identity_id"]
    assert document["selected_plan_id"] == recipe.source.selected_plan_id
    assert document["h1_direct_fallback_two_role_recipe_id"] == recipe.recipe_id
    assert document["preregistered_recipe_chain"] == dict(
        current_v1.EXPECTED_H1_RECIPE_CHAIN
    )
    assert document["preexecution_candidate_sha256"] == (
        current_v1.EXPECTED_H1_RECIPE_CHAIN["preexecution_sha256"]
    )
    assert document["preexecution_candidate_id"] == (
        current_v1.EXPECTED_H1_RECIPE_CHAIN["preexecution_candidate_id"]
    )
    assert document["preexecution_candidate_byte_count"] == (
        current_v1.EXPECTED_H1_PREEXECUTION_BYTE_COUNT
    )
    assert document["current_identity_supplied_explicitly_to_durable_verifier"] is True
    assert document["durable_verifier_default_self_match_used"] is False
    assert document["retained_verifier_handle_validated_and_plan_bound"] is True
    assert document["retained_verifier_handle_one_shot_revocation"] is False
    assert document["retained_verifier_handle_consumed"] is False
    assert document[
        "complete_recipe_chain_observed_from_exact_preexecution_bytes"
    ] is True
    assert document["recipe_chain_constants_used_to_fill_unobserved_fields"] is False


def test_route_time_candidate_is_exact_recipe_crosswalk_with_unobserved_calls(
    candidate,
    current_source,
    proof_match,
    recipe,
) -> None:
    document = candidate.to_document()
    assert document["current_source_fixture_id"] == current_source.fixture_id
    assert document["proof_match_attestation_id"] == proof_match.attestation_id
    assert document["h1_direct_fallback_two_role_recipe_id"] == recipe.recipe_id
    assert document["selected_plan_id"] == recipe.source.selected_plan_id
    rows = {item["coordinate"]: item for item in document["exact_identity_crosswalk"]}
    assert set(rows) == {
        "structural_id",
        "query_id",
        "BuildEpoch_id",
        "kernel_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    }
    assert all(item["current_value"] == item["proof_match_value"] for item in rows.values())
    for coordinate in (
        "structural_id",
        "query_id",
        "BuildEpoch_id",
        "kernel_id",
        "threshold_profile_id",
    ):
        assert rows[coordinate]["recipe_value"] == rows[coordinate]["current_value"]
        assert rows[coordinate]["recipe_coordinate_applicable"] is True
    for coordinate in (
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    ):
        assert rows[coordinate]["recipe_value"] is None
        assert rows[coordinate]["recipe_coordinate_applicable"] is False
    assert document["route_time_call_counts"] == {
        "kind": "UNOBSERVED",
        "reason": "OBSERVED_ROUTE_TIME_ACCESS_LOG_PENDING",
    }
    declaration = document["route_time_forbidden_api_declaration"]
    assert declaration["kind"] == "FORBIDDEN_API_DECLARATION_NOT_OBSERVED_COUNTERS"
    assert declaration["caller_supplied_zero_counters_accepted"] is False
    assert "KERNEL_STEP" in declaration["forbidden_operations"]
    assert document["production_current_identity_candidate"] is True
    assert document["production_current_identity_authority"] is False
    assert document["production_current_identity_candidate_id"] == (
        candidate.candidate_id
    )
    assert "production_current_identity_authority_id" not in document
    assert document["route_time_observed_access_log_id"] is None
    assert document["route_time_access_evidence_status"] == (
        "PENDING_OBSERVED_ACCESS_LOG"
    )
    assert document["production_execution_authorized"] is False
    assert document["same_process_unforgeability_claimed"] is False
    assert document["private_module_state_adversary_resistance_claimed"] is False
    assert document["eligible_as_production_consumer_authority"] is False
    assert document["production_consumers_must_reject_candidate"] is True


def test_private_registry_injection_cannot_promote_candidate_to_authority(
    candidate,
) -> None:
    forged = copy.copy(candidate)
    role = "H1_PRODUCTION_CURRENT_IDENTITY_CANDIDATE"
    current_v1._LIVE[id(forged)] = (
        forged,
        role,
        canonical_json_bytes(forged._payload()),
    )
    try:
        # The construction registry is mutable process-local defense in depth,
        # so the V1 profile explicitly does not claim this is unforgeable.
        assert forged.candidate_id == candidate.candidate_id
        with pytest.raises(
            current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
            match="construction candidate, not a production authority",
        ):
            current_v1.require_h1_production_current_identity_authority_v1(
                forged
            )
    finally:
        current_v1._LIVE.pop(id(forged), None)
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="construction candidate, not a production authority",
    ):
        current_v1.require_h1_production_current_identity_authority_v1(candidate)
    assert not hasattr(
        current_v1, "freeze_h1_production_current_identity_authority_v1"
    )
    assert not hasattr(current_v1, "H1ProductionCurrentIdentityAuthorityV1")


def test_route_freezer_and_bytes_verifier_do_not_replay_semantics(
    monkeypatch: pytest.MonkeyPatch,
    candidate,
    current_source,
    proof_match,
    recipe,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("route-time current-identity join replayed semantics")

    monkeypatch.setattr(
        current_v1,
        "issue_phase3e_exact_infeasibility_durable_proof_v1",
        forbidden,
    )
    monkeypatch.setattr(
        current_v1,
        "verify_phase3e_exact_infeasibility_durable_proof_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        current_v1,
        "bind_verified_durable_exact_infeasibility_to_plan_v1",
        forbidden,
    )
    monkeypatch.setattr(durable_v1, "_legal_actions", forbidden)
    monkeypatch.setattr(durable_v1, "_semantic_outcomes", forbidden)
    monkeypatch.setattr(durable_v1, "_frontier_from_rows", forbidden)
    monkeypatch.setattr(acquisition_v1.G2048Kernel, "initial_distribution", forbidden)
    monkeypatch.setattr(acquisition_v1.G2048Kernel, "actions", forbidden)
    monkeypatch.setattr(acquisition_v1.G2048Kernel, "step", forbidden)
    monkeypatch.setattr(acquisition_v1, "run_ground_fallback_search_v1", forbidden)
    monkeypatch.setattr(phase3e_fallback_v1, "run_ground_fallback_search_v1", forbidden)
    monkeypatch.setattr(ground_v1, "solve_ground_pareto", forbidden)
    monkeypatch.setattr(oracle_v1, "build_ground_oracle_table", forbidden)
    frozen = current_v1.freeze_h1_production_current_identity_candidate_v1(
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
    )
    verification = current_v1.verify_h1_production_current_identity_candidate_bytes_v1(
        raw=candidate.canonical_bytes,
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
    )
    assert frozen.to_document() == candidate.to_document()
    assert verification.candidate_id == candidate.candidate_id
    assert verification.to_document()[
        "structurally_invokes_durable_proof_verifier"
    ] is False
    assert verification.to_document()["structurally_invokes_kernel_or_planner"] is False
    assert verification.to_document()["route_time_access_evidence_status"] == (
        "PENDING_OBSERVED_ACCESS_LOG"
    )
    assert verification.to_document()[
        "production_current_identity_authority_verified"
    ] is False
    assert verification.to_document()["route_time_call_counts"]["kind"] == (
        "UNOBSERVED"
    )


def test_route_api_cannot_accept_claimant_identity_proof_or_zero_counters() -> None:
    source_parameters = inspect.signature(
        current_v1.issue_h1_current_source_fixture_v1
    ).parameters
    freeze_parameters = inspect.signature(
        current_v1.freeze_h1_production_current_identity_candidate_v1
    ).parameters
    verify_parameters = inspect.signature(
        current_v1.verify_h1_production_current_identity_candidate_bytes_v1
    ).parameters
    proof_match_parameters = inspect.signature(
        current_v1.issue_h1_durable_proof_match_attestation_v1
    ).parameters
    assert "claimant_proof_bytes" not in source_parameters
    forbidden = {
        "proof_bytes",
        "claimant_proof_bytes",
        "current_identity",
        "bundle_root",
        "phase05_bundle_root",
        "route_time_call_audit",
        "zero_counters",
    }
    assert forbidden.isdisjoint(freeze_parameters)
    assert forbidden.isdisjoint(verify_parameters)
    assert "recipe" in proof_match_parameters
    assert "preexecution_candidate_bytes" in proof_match_parameters
    assert "selected_plan_id" not in proof_match_parameters


def test_copies_and_tampered_bytes_are_rejected(
    current_source,
    proof_match,
    recipe,
    candidate,
) -> None:
    copied_source = copy.copy(current_source)
    with pytest.raises(current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error):
        current_v1.freeze_h1_production_current_identity_candidate_v1(
            current_source=copied_source,
            proof_match_attestation=proof_match,
            recipe=recipe,
        )
    copied_match = copy.copy(proof_match)
    with pytest.raises(current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error):
        current_v1.freeze_h1_production_current_identity_candidate_v1(
            current_source=current_source,
            proof_match_attestation=copied_match,
            recipe=recipe,
        )
    document = candidate.to_document()
    document["official_execution_allowed"] = True
    with pytest.raises(current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error):
        current_v1.verify_h1_production_current_identity_candidate_bytes_v1(
            raw=canonical_json_bytes(document),
            current_source=current_source,
            proof_match_attestation=proof_match,
            recipe=recipe,
        )


@pytest.mark.parametrize(
    "coordinate",
    (
        "structural_id",
        "query_id",
        "build_epoch_id",
        "kernel_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    ),
)
def test_each_current_identity_coordinate_mismatch_fails_closed(
    coordinate: str,
    current_source,
) -> None:
    crossed_identity = replace(current_source.identity, **{coordinate: "f" * 64})
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="eight-coordinate identity",
    ):
        current_v1.H1CurrentSourceFixtureV1(
            current_v1._CURRENT_SOURCE_ISSUER,
            current_source.build_kernel,
            current_source.query,
            crossed_identity,
        )


@pytest.mark.parametrize(
    ("profile_field", "key", "value"),
    (
        ("query_profile_bytes", "horizon", 2),
        ("threshold_profile_bytes", "delta", 1),
        ("reward_profile_bytes", "normalizer", 2),
        ("policy_class_profile_bytes", "policy_class", "randomized"),
        ("complete_search_profile_bytes", "search_complete", False),
    ),
)
def test_each_query_profile_tamper_is_rejected_by_constructor_guard(
    profile_field: str,
    key: str,
    value,
    current_source,
) -> None:
    query = current_source.query
    raw = getattr(query, profile_field)
    document = loads_canonical_json(raw)
    document[key] = value
    arguments = {
        "query_profile_bytes": query.query_profile_bytes,
        "threshold_profile_bytes": query.threshold_profile_bytes,
        "reward_profile_bytes": query.reward_profile_bytes,
        "policy_class_profile_bytes": query.policy_class_profile_bytes,
        "complete_search_profile_bytes": query.complete_search_profile_bytes,
    }
    arguments[profile_field] = canonical_json_bytes(document)
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="query/search profile",
    ):
        current_v1.H1CurrentQueryAttestationV1(
            current_v1._QUERY_ISSUER,
            query.current_source_proof_id,
            query.current_source_verification_id,
            **arguments,
        )


@pytest.mark.parametrize(
    "splice",
    ("closure", "member", "archive", "runtime_lock", "compile"),
)
def test_source_archive_closure_member_runtime_and_compile_splices_fail_closed(
    splice: str,
    source_chain,
) -> None:
    closure, archive, runtime_lock, compiled = source_chain
    bad_closure = closure
    bad_archive = archive
    bad_runtime = runtime_lock
    bad_compile = compiled
    if splice == "closure":
        bad_closure = copy.copy(closure)
        object.__setattr__(bad_closure, "root_modules", ("acfqp",))
    elif splice == "member":
        bad_closure = copy.copy(closure)
        object.__setattr__(bad_closure, "modules", closure.modules[:-1])
    elif splice == "archive":
        bad_archive = copy.copy(archive)
        object.__setattr__(bad_archive, "archive_sha256", "f" * 64)
    elif splice == "runtime_lock":
        bad_runtime = copy.copy(runtime_lock)
        object.__setattr__(bad_runtime, "_verification_id", "f" * 64)
    else:
        bad_compile = copy.copy(compiled)
        object.__setattr__(bad_compile, "source_archive_id", "f" * 64)
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="archive/compile chain",
    ):
        current_v1.issue_h1_current_source_fixture_v1(
            CANONICAL_BUNDLE,
            source_closure=bad_closure,
            source_archive=bad_archive,
            runtime_lock=bad_runtime,
            archive_compile_verification=bad_compile,
        )


def test_fully_self_consistent_alternate_archive_is_accepted_only_as_fixture(
    source_chain,
    tmp_path: Path,
) -> None:
    canonical_closure, canonical_archive, runtime_lock, _compiled = source_chain
    sources, paths = _all_acfqp_sources()
    altered_module = "acfqp.construction_k7_h1_production_current_identity_v1"
    sources[altered_module] = (
        sources[altered_module]
        + b"\n# caller-supplied alternate compile fixture; not live provenance\n"
    )
    alternate_path = tmp_path / "acfqp" / (
        "construction_k7_h1_production_current_identity_v1.py"
    )
    alternate_path.parent.mkdir(parents=True)
    alternate_path.write_bytes(sources[altered_module])
    paths[altered_module] = alternate_path
    closure = source_runtime_v2.build_construction_source_closure_v2(
        root_modules=current_v1.SOURCE_ARCHIVE_ROOT_MODULES,
        module_sources=sources,
        module_paths=paths,
    )
    archive = source_runtime_v2.build_deterministic_source_archive_v2(
        closure=closure,
        module_sources=sources,
    )
    compiled = source_runtime_v2.verify_construction_sealed_archive_compile_v2(
        closure=closure,
        archive=archive,
        runtime_lock=runtime_lock,
        timeout_seconds=30,
    )
    assert closure.closure_id != canonical_closure.closure_id
    assert archive.archive_id != canonical_archive.archive_id
    issued = current_v1.issue_h1_current_source_fixture_v1(
        CANONICAL_BUNDLE,
        source_closure=closure,
        source_archive=archive,
        runtime_lock=runtime_lock,
        archive_compile_verification=compiled,
    )
    document = issued.to_document()
    assert issued.build_kernel.source_archive_id == archive.archive_id
    assert document["source_archive_role"] == (
        "CALLER_SUPPLIED_SELF_CONSISTENT_COMPILE_FIXTURE"
    )
    assert document["live_current_issuer_source_provenance_proven"] is False
    assert document["issuer_code_provenance_proven"] is False


def test_byte_identical_claimant_and_current_source_remain_distinct_roles(
    proof_bytes: bytes,
    current_source,
    proof_match,
) -> None:
    assert current_source.build_kernel.current_source_proof_sha256 == (
        proof_match.claimant_proof_sha256
    )
    assert current_source.build_kernel.current_source_proof_byte_count == len(
        proof_bytes
    )
    assert current_source.build_kernel.current_source_proof_id == (
        proof_match.durable_proof_id
    )
    assert current_source.fixture_id != proof_match.attestation_id
    assert current_v1.CURRENT_SOURCE_DOMAIN != current_v1.PROOF_MATCH_DOMAIN
    assert current_source.build_kernel.to_document()["current_source_role"] == (
        "PREREGISTERED_PROOF_DERIVED_CURRENT_SOURCE_CANDIDATE"
    )
    assert current_source.to_document()[
        "current_source_issued_before_claimant_comparison"
    ] is True
    assert proof_match.to_document()[
        "current_identity_supplied_explicitly_to_durable_verifier"
    ] is True


def test_legacy_canonical_fallback_current_identity_is_not_stage_a_authority(
    legacy_current,
    proof_match,
    recipe,
) -> None:
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="caller-minted",
    ):
        current_v1.freeze_h1_production_current_identity_candidate_v1(
            current_source=legacy_current,
            proof_match_attestation=proof_match,
            recipe=recipe,
        )


def test_preregistered_current_bytes_are_checked_before_semantic_verifier(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    source_chain,
) -> None:
    document = loads_canonical_json(proof_bytes)
    document["reward_profile"]["normalizer"] = 2
    tampered = canonical_json_bytes(document)
    verifier_called = False

    def forbidden_verifier(*_args, **_kwargs):
        nonlocal verifier_called
        verifier_called = True
        raise AssertionError("semantic verifier ran before preregistration match")

    monkeypatch.setattr(
        current_v1,
        "issue_phase3e_exact_infeasibility_durable_proof_v1",
        lambda _root: tampered,
    )
    monkeypatch.setattr(
        current_v1,
        "verify_phase3e_exact_infeasibility_durable_proof_bytes_v1",
        forbidden_verifier,
    )
    closure, archive, runtime_lock, compiled = source_chain
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="preregistered current proof bytes",
    ):
        current_v1.issue_h1_current_source_fixture_v1(
            CANONICAL_BUNDLE,
            source_closure=closure,
            source_archive=archive,
            runtime_lock=runtime_lock,
            archive_compile_verification=compiled,
        )
    assert verifier_called is False


def test_stage_a_passes_frozen_identity_explicitly_to_semantic_verifier(
    monkeypatch: pytest.MonkeyPatch,
    source_chain,
) -> None:
    original = current_v1.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1
    observed = []

    def recording_verifier(raw, *, current_identity=None):
        observed.append(current_identity)
        return original(raw, current_identity=current_identity)

    monkeypatch.setattr(
        current_v1,
        "verify_phase3e_exact_infeasibility_durable_proof_bytes_v1",
        recording_verifier,
    )
    closure, archive, runtime_lock, compiled = source_chain
    issued = current_v1.issue_h1_current_source_fixture_v1(
        CANONICAL_BUNDLE,
        source_closure=closure,
        source_archive=archive,
        runtime_lock=runtime_lock,
        archive_compile_verification=compiled,
    )
    assert observed == [current_v1.EXPECTED_CURRENT_IDENTITY]
    assert issued.identity is current_v1.EXPECTED_CURRENT_IDENTITY
    assert issued.build_kernel.current_source_proof_id == (
        current_v1.EXPECTED_CURRENT_PROOF_ID
    )
    assert issued.build_kernel.current_source_proof_sha256 == (
        current_v1.EXPECTED_CURRENT_PROOF_SHA256
    )
    assert issued.build_kernel.current_source_proof_byte_count == (
        current_v1.EXPECTED_CURRENT_PROOF_BYTE_COUNT
    )


def test_all_six_candidate_types_reject_direct_private_sentinel_construction(
    current_source,
    proof_match,
    recipe,
    candidate,
) -> None:
    build = current_source.build_kernel
    query = current_source.query
    constructors = (
        lambda: current_v1.H1CurrentBuildKernelAttestationV1(
            current_v1._BUILD_KERNEL_ISSUER,
            build.current_source_proof_id,
            build.current_source_proof_sha256,
            build.current_source_proof_byte_count,
            build.current_source_verification_id,
            build.structural_profile_bytes,
            build.source_projection_bytes,
            build.kernel_profile_bytes,
            build.build_epoch_bytes,
            build.source_closure_id,
            build.source_archive_id,
            build.source_archive_sha256,
            build.source_archive_byte_count,
            build.runtime_lock_verification_id,
            build.archive_compile_verification_id,
            build.source_module_ids,
        ),
        lambda: current_v1.H1CurrentQueryAttestationV1(
            current_v1._QUERY_ISSUER,
            query.current_source_proof_id,
            query.current_source_verification_id,
            query.query_profile_bytes,
            query.threshold_profile_bytes,
            query.reward_profile_bytes,
            query.policy_class_profile_bytes,
            query.complete_search_profile_bytes,
        ),
        lambda: current_v1.H1CurrentSourceFixtureV1(
            current_v1._CURRENT_SOURCE_ISSUER,
            build,
            query,
            current_source.identity,
        ),
        lambda: current_v1.H1DurableProofMatchAttestationV1(
            current_v1._PROOF_MATCH_ISSUER,
            proof_match.current_source_fixture_id,
            proof_match.claimant_proof_sha256,
            proof_match.claimant_proof_byte_count,
            proof_match.durable_proof_id,
            proof_match.recipe_id,
            proof_match.preexecution_candidate_sha256,
            proof_match.preexecution_candidate_byte_count,
            proof_match.preexecution_candidate_id,
            dict(proof_match.recipe_chain),
            dict(proof_match.verification_result),
            proof_match.plan_binding,
        ),
        lambda: current_v1.H1ProductionCurrentIdentityCandidateV1(
            current_v1._CURRENT_IDENTITY_ISSUER,
            current_source,
            proof_match,
            recipe,
        ),
        lambda: current_v1.H1ProductionCurrentIdentityCandidateVerificationV1(
            current_v1._VERIFICATION_ISSUER,
            candidate.candidate_id,
            "f" * 64,
            len(candidate.canonical_bytes),
            current_source.fixture_id,
            proof_match.attestation_id,
            recipe.recipe_id,
        ),
    )
    for constructor in constructors:
        with pytest.raises(
            current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
            match="bypassed its exact public issuer",
        ):
            constructor()


def test_direct_retain_cannot_promote_a_copy(
    current_source,
) -> None:
    copied = copy.copy(current_source)
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="not produced by its exact public issuer",
    ):
        current_v1._retain(
            copied,
            "H1_CURRENT_SOURCE_FIXTURE",
            copied._payload(),
        )


def test_alternative_live_legacy_recipe_chain_is_rejected_before_proof_match(
    proof_bytes: bytes,
    current_source,
    recipe,
    preexecution_candidate_bytes: bytes,
) -> None:
    crossed_source = replace(recipe.source, preexecution_sha256="f" * 64)
    crossed_recipe = recipe_v1.H1DirectFallbackTwoRoleRecipeV1(
        recipe_v1._RECIPE_ISSUER,
        crossed_source,
    )
    raw = canonical_json_bytes(crossed_recipe._unchecked_document())
    recipe_v1._LIVE_RECIPES[id(crossed_recipe)] = (crossed_recipe, raw)
    with pytest.raises(
        current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
        match="does not replay from the exact preexecution bytes",
    ):
        current_v1.issue_h1_durable_proof_match_attestation_v1(
            proof_bytes,
            current_source=current_source,
            recipe=crossed_recipe,
            preexecution_candidate_bytes=preexecution_candidate_bytes,
        )


def test_exact_projection_registry_injection_cannot_fill_hidden_recipe_ids(
    proof_bytes: bytes,
    current_source,
    recipe,
    preexecution_candidate_bytes: bytes,
) -> None:
    # The legacy recipe projection omits this cap identity.  A caller can
    # inject a structurally exact projection into the old process-local recipe
    # registry, but Stage B must still observe the real preexecution bytes.
    injected_recipe = recipe_v1.H1DirectFallbackTwoRoleRecipeV1(
        recipe_v1._RECIPE_ISSUER,
        recipe.source,
    )
    recipe_v1._LIVE_RECIPES[id(injected_recipe)] = (
        injected_recipe,
        canonical_json_bytes(injected_recipe._unchecked_document()),
    )
    document = loads_canonical_json(preexecution_candidate_bytes)
    document["cap_profile"]["ground_fallback_cap_profile_id"] = "f" * 64
    payload = dict(document)
    payload.pop("direct_fallback_preexecution_candidate_id")
    document["direct_fallback_preexecution_candidate_id"] = phase3e_ids.content_id(
        phase3e_ids.CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
        payload,
    )
    tampered = canonical_json_bytes(document)
    try:
        with pytest.raises(
            current_v1.ConstructionK7H1ProductionCurrentIdentityV1Error,
            match="preregistered digest",
        ):
            current_v1.issue_h1_durable_proof_match_attestation_v1(
                proof_bytes,
                current_source=current_source,
                recipe=injected_recipe,
                preexecution_candidate_bytes=tampered,
            )
    finally:
        recipe_v1._LIVE_RECIPES.pop(id(injected_recipe), None)


def test_all_hidden_recipe_ids_are_observed_before_recipe_registry_replay(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_source,
    recipe,
    preexecution_candidate_bytes: bytes,
) -> None:
    observed_fields: list[str] = []
    original_nested_id = current_v1._preexecution_nested_id
    original_recipe_replay = (
        recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1
    )

    def recording_nested_id(document, object_name, field_name):
        observed_fields.append(field_name)
        return original_nested_id(document, object_name, field_name)

    def guarded_recipe_replay(*args, **kwargs):
        assert observed_fields == [
            "ground_fallback_cap_profile_id",
            "ground_fallback_cardinality_bound_id",
            "cardinality_evidence_id",
            "formula_id",
            "derivation_proof_id",
        ]
        return original_recipe_replay(*args, **kwargs)

    monkeypatch.setattr(current_v1, "_preexecution_nested_id", recording_nested_id)
    monkeypatch.setattr(
        recipe_v1,
        "verify_h1_direct_fallback_two_role_recipe_bytes_v1",
        guarded_recipe_replay,
    )
    issued = current_v1.issue_h1_durable_proof_match_attestation_v1(
        proof_bytes,
        current_source=current_source,
        recipe=recipe,
        preexecution_candidate_bytes=preexecution_candidate_bytes,
    )
    assert issued.recipe_chain == dict(current_v1.EXPECTED_H1_RECIPE_CHAIN)
