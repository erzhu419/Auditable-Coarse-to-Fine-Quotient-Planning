from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_current_access_authority_v1 as access_v1
from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable_v1
from acfqp import phase3e_ids
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


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


@pytest.fixture()
def profile_context(current_chain):
    current_source, proof_match, recipe, candidate, candidate_verification = current_chain
    profile = access_v1.official_h1_current_access_execution_profile_v1()
    nonce = content_id(
        access_v1.FIXTURE_DOMAIN,
        {"schema": "acfqp.h1_current_access_test_nonce.v1", "ordinal": 1},
    )
    context = access_v1.freeze_h1_current_access_predecision_context_v1(
        execution_profile=profile,
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
        current_identity_candidate=candidate,
        candidate_verification=candidate_verification,
        logical_occurrence_id=recipe.source.logical_occurrence_id,
        route_attempt_id=recipe.source.route_attempt_id,
        session_nonce=nonce,
    )
    input_set = access_v1.freeze_h1_current_access_predecision_input_set_v1(
        execution_profile=profile,
        context=context,
    )
    return profile, context, input_set


def _complete_fixture(profile, context, input_set):
    recorder = access_v1.H1PredecisionAccessLogRecorderV1(
        execution_profile=profile,
        context=context,
    )
    access_v1.record_h1_predecision_identity_inputs_v1(recorder)
    child = access_v1.build_h1_current_access_child_result_fixture_v1(
        execution_profile=profile,
        context=context,
        input_set=input_set,
    )
    access_v1.record_h1_current_access_child_result_v1(
        recorder=recorder,
        child_result=child,
    )
    cutoff = access_v1.freeze_h1_predecision_current_access_cutoff_v1(recorder)
    evidence = access_v1.freeze_h1_current_access_observed_evidence_v1(
        recorder=recorder,
        cutoff=cutoff,
        child_result=child,
        input_set=input_set,
    )
    return recorder, child, cutoff, evidence


def _issue_observed_authority(current_chain, profile_context):
    current_source, proof_match, recipe, candidate, candidate_verification = current_chain
    profile, context, input_set = profile_context
    verification = runtime_v1.run_h1_current_access_fresh_exec_runtime_v1(
        predecision_context_bytes=context.canonical_bytes,
        current_source_fixture_bytes=current_source.canonical_bytes,
        proof_match_attestation_bytes=canonical_json_bytes(proof_match.to_document()),
        h1_two_role_recipe_bytes=recipe.canonical_bytes,
        current_identity_candidate_bytes=candidate.canonical_bytes,
        candidate_verification_bytes=canonical_json_bytes(
            candidate_verification.to_document()
        ),
        predecision_input_set=input_set,
    )
    assert type(verification) is runtime_v1.H1CurrentAccessObservedRuntimeFactsVerificationV1
    child = access_v1.issue_h1_current_access_child_result_v1(
        execution_profile=profile,
        context=context,
        input_set=input_set,
        runtime_verification=verification,
    )
    recorder = access_v1.H1PredecisionAccessLogRecorderV1(
        execution_profile=profile,
        context=context,
    )
    access_v1.record_h1_predecision_identity_inputs_v1(recorder)
    access_v1.record_h1_current_access_child_result_v1(
        recorder=recorder,
        child_result=child,
    )
    cutoff = access_v1.freeze_h1_predecision_current_access_cutoff_v1(recorder)
    evidence = access_v1.freeze_h1_current_access_observed_evidence_v1(
        recorder=recorder,
        cutoff=cutoff,
        child_result=child,
        input_set=input_set,
    )
    authority = access_v1.issue_h1_production_current_access_authority_v1(
        execution_profile=profile,
        context=context,
        observed_evidence=evidence,
    )
    return authority, recorder


def test_contract_domains_and_locks_are_exact() -> None:
    assert access_v1.PROPOSED_CONTRACT_VERSION == "2.0.57"
    assert access_v1.PROFILE_KEY == "construction_k7_h1_current_access_authority_v1"
    assert len(set(access_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 11
    assert set(access_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= phase3e_ids.PHASE3E_DOMAIN_TAGS
    assert access_v1.CONSTRUCTION_ONLY is False
    assert access_v1.FRESH_EXEC_RUNTIME_EVIDENCE_INTEGRATED is True
    assert access_v1.PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT is True
    assert access_v1.FUTURE_FORMAL_V7_JOIN_PRESENT is False
    assert access_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert access_v1.OFFICIAL_SCALAR_COST is None
    assert access_v1.OFFICIAL_N_BREAK_EVEN is None
    assert access_v1.COUNTER_COMPLETENESS_GATE_STATUS.endswith("NOT_RUN")
    assert access_v1.WORKLOAD_ECONOMICS_GATE_STATUS.endswith("NOT_RUN")
    assert access_v1.SAMPLE_EFFICIENCY_GATE_STATUS.endswith("NOT_RUN")


def test_context_reuses_all_eight_contract_2052_identities_without_route_fields(
    profile_context,
) -> None:
    profile, context, input_set = profile_context
    document = context.to_document()
    assert document["h1_current_access_execution_profile_id"] == profile.profile_id
    assert tuple(row["role"] for row in document["precontext_sealed_inputs"]) == (
        access_v1.SEALED_INPUT_ROLES[1:]
    )
    input_document = input_set.to_document()
    assert tuple(row["role"] for row in input_document["sealed_inputs"]) == (
        access_v1.SEALED_INPUT_ROLES
    )
    assert input_document["semantic_context_contains_input_set_backreference"] is False
    assert "h1_current_access_predecision_input_set_id" not in document
    assert set(context.identity_document) == {
        "structural_id",
        "query_id",
        "BuildEpoch_id",
        "kernel_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    }
    assert document["stage_scope"] == "PREDECISION_CURRENT_ACCESS"
    assert document["downstream_route_authority_join_present"] is False
    keys = "\n".join(document)
    for fragment in access_v1.production_current_access_authority_field_fragments_v1():
        assert fragment not in keys


def test_append_only_log_and_exact_cutoff_bind_context_attempt_epoch_nonce(
    profile_context,
) -> None:
    profile, context, input_set = profile_context
    recorder, child, cutoff, evidence = _complete_fixture(profile, context, input_set)
    log = access_v1.require_h1_predecision_current_access_cutoff_v1(
        recorder=recorder,
        cutoff=cutoff,
    )
    assert tuple(event.operation for event in log.events) == access_v1.EXPECTED_OPERATION_SEQUENCE
    assert [event.sequence for event in log.events] == [1, 2, 3, 4]
    assert log.events[0].predecessor_event_id is None
    assert all(
        event.predecessor_event_id == log.events[index - 1].event_id
        for index, event in enumerate(log.events[1:], 1)
    )
    assert evidence.context_id == context.context_id
    assert evidence.route_attempt_id == context.route_attempt_id
    assert evidence.build_epoch_id == context.build_epoch_id
    assert evidence.session_nonce == context.session_nonce
    assert evidence.child_result_id == child.child_result_id


def test_extra_event_makes_cutoff_stale_and_cannot_form_new_cutoff(profile_context) -> None:
    profile, context, input_set = profile_context
    recorder, child, cutoff, evidence = _complete_fixture(profile, context, input_set)
    recorder.append(
        access_v1.H1PredecisionAccessOperationV1.FORMAL_V7_DECISION_VERIFIED,
        resource_id=content_id(
            access_v1.FIXTURE_DOMAIN,
            {"schema": "acfqp.formal_v7_decision_fixture.v1"},
        ),
    )
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="stale"):
        access_v1.require_h1_predecision_current_access_cutoff_v1(
            recorder=recorder,
            cutoff=cutoff,
        )
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="exact access sequence"):
        access_v1.freeze_h1_predecision_current_access_cutoff_v1(recorder)
    assert evidence.verification_status == "CONSTRUCTION_FIXTURE_ONLY"
    assert child.construction_fixture is True


def test_unknown_postcutoff_event_is_rejected(profile_context) -> None:
    profile, context, input_set = profile_context
    recorder, _, _, _ = _complete_fixture(profile, context, input_set)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="unknown"):
        recorder.append(
            "UNREGISTERED_FUTURE_PHASE",
            resource_id=context.context_id,
        )


def test_cross_context_attempt_epoch_nonce_and_wrong_attempt_fail_closed(
    current_chain,
    profile_context,
) -> None:
    current_source, proof_match, recipe, candidate, candidate_verification = current_chain
    profile, first_context, first_input_set = profile_context
    second_context = access_v1.freeze_h1_current_access_predecision_context_v1(
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
            {"schema": "acfqp.h1_current_access_test_nonce.v1", "ordinal": 2},
        ),
    )
    child = access_v1.build_h1_current_access_child_result_fixture_v1(
        execution_profile=profile,
        context=first_context,
        input_set=first_input_set,
    )
    recorder = access_v1.H1PredecisionAccessLogRecorderV1(
        execution_profile=profile,
        context=second_context,
    )
    access_v1.record_h1_predecision_identity_inputs_v1(recorder)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="context/attempt/epoch/nonce"):
        access_v1.record_h1_current_access_child_result_v1(
            recorder=recorder,
            child_result=child,
        )
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="identities differ"):
        access_v1.freeze_h1_current_access_predecision_context_v1(
            execution_profile=profile,
            current_source=current_source,
            proof_match_attestation=proof_match,
            recipe=recipe,
            current_identity_candidate=candidate,
            candidate_verification=candidate_verification,
            logical_occurrence_id=recipe.source.logical_occurrence_id,
            route_attempt_id=content_id(
                access_v1.FIXTURE_DOMAIN,
                {"schema": "acfqp.foreign_route_attempt.v1"},
            ),
            session_nonce=second_context.session_nonce,
        )
    shell = object.__new__(access_v1.H1CurrentAccessChildResultV1)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="retained"):
        access_v1.record_h1_current_access_child_result_v1(
            recorder=recorder,
            child_result=shell,
        )


def test_construction_and_fake_evidence_never_mint_production_authority(
    profile_context,
) -> None:
    profile, context, input_set = profile_context
    _, _, _, evidence = _complete_fixture(profile, context, input_set)
    with pytest.raises(access_v1.H1CurrentAccessAuthorityBlockedV1, match="cannot mint"):
        access_v1.issue_h1_production_current_access_authority_v1(
            execution_profile=profile,
            context=context,
            observed_evidence=evidence,
        )
    fake = object.__new__(access_v1.H1CurrentAccessObservedEvidenceV1)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="retained"):
        access_v1.issue_h1_production_current_access_authority_v1(
            execution_profile=profile,
            context=context,
            observed_evidence=fake,
        )
    fake_runtime = object.__new__(
        runtime_v1.H1CurrentAccessObservedRuntimeFactsVerificationV1
    )
    with pytest.raises(access_v1.H1CurrentAccessAuthorityBlockedV1, match="not retained"):
        access_v1.issue_h1_current_access_child_result_v1(
            execution_profile=profile,
            context=context,
            input_set=input_set,
            runtime_verification=fake_runtime,
        )


def test_authority_schema_has_no_circular_fields_and_unretained_shell_is_not_one_shot_authority() -> None:
    field_names = {item.name for item in fields(access_v1.H1ProductionCurrentAccessAuthorityV1)}
    flattened = "\n".join(field_names)
    for fragment in access_v1.production_current_access_authority_field_fragments_v1():
        assert fragment not in flattened
    assert "downstream_route_authority_join_present" not in field_names
    shell = object.__new__(access_v1.H1ProductionCurrentAccessAuthorityV1)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="retained"):
        access_v1.require_h1_production_current_access_authority_v1(shell)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="retained"):
        access_v1.consume_h1_production_current_access_authority_v1(shell)


def test_real_fresh_exec_evidence_issues_exact_one_shot_authority(
    current_chain,
    profile_context,
) -> None:
    authority, _ = _issue_observed_authority(current_chain, profile_context)
    assert access_v1.require_h1_production_current_access_authority_v1(authority) is authority
    document = authority.to_document()
    flattened = "\n".join(document)
    for fragment in access_v1.production_current_access_authority_field_fragments_v1():
        assert fragment not in flattened
    assert document["verification_status"] == access_v1.REQUIRED_RUNTIME_VERIFICATION_STATUS
    assert document["downstream_route_authority_join_present"] is False
    expected = canonical_json_bytes(document)
    assert access_v1.consume_h1_production_current_access_authority_v1(authority) == expected
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="already consumed"):
        access_v1.require_h1_production_current_access_authority_v1(authority)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="already consumed"):
        access_v1.consume_h1_production_current_access_authority_v1(authority)


def test_authority_revalidates_cutoff_and_rejects_registered_postcutoff_append(
    current_chain,
    profile_context,
) -> None:
    authority, recorder = _issue_observed_authority(current_chain, profile_context)
    recorder.append(
        access_v1.H1PredecisionAccessOperationV1.FORMAL_V7_DECISION_VERIFIED,
        resource_id=content_id(
            access_v1.FIXTURE_DOMAIN,
            {"schema": "acfqp.formal_v7_decision_after_authority.v1"},
        ),
    )
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="stale"):
        access_v1.require_h1_production_current_access_authority_v1(authority)
    with pytest.raises(access_v1.ConstructionK7H1CurrentAccessAuthorityV1Error, match="stale"):
        access_v1.consume_h1_production_current_access_authority_v1(authority)


def test_typed_blocker_is_nonauthoritative_and_context_bound(profile_context) -> None:
    profile, context, _ = profile_context
    blocker = access_v1.build_h1_production_current_access_authority_blocker_v1(
        execution_profile=profile,
        context=context,
    )
    document = blocker.to_document()
    assert document["blocker_code"] == "FRESH_EXEC_RUNTIME_EVIDENCE_UNAVAILABLE"
    assert document["h1_current_access_predecision_context_id"] == context.context_id
    assert document["route_attempt_id"] == context.route_attempt_id
    assert document["BuildEpoch_id"] == context.build_epoch_id
    assert document["session_nonce"] == context.session_nonce
    assert document["production_current_access_authority"] is False
    assert document["official_execution_allowed"] is False
