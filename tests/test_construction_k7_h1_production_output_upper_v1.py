from __future__ import annotations

from functools import cache
from pathlib import Path

import pytest

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_current_access_authority_v1 as access_v1
from acfqp import construction_k7_h1_current_access_fresh_exec_runtime_v1 as runtime_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import construction_k7_h1_production_output_upper_v1 as output_v1
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


@cache
def _current_chain():
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
    candidate_verification = current_v1.verify_h1_production_current_identity_candidate_bytes_v1(
        raw=candidate.canonical_bytes,
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
    )
    return (
        current_source,
        proof_match,
        recipe,
        candidate,
        candidate_verification,
    )


@pytest.fixture(scope="module")
def output_context():
    current_source, proof_match, recipe, candidate, verification = _current_chain()
    profile = access_v1.official_h1_current_access_execution_profile_v1()
    nonce = content_id(
        access_v1.FIXTURE_DOMAIN,
        {"schema": "acfqp.h1_output_upper_test_nonce.v1", "ordinal": 1},
    )
    context = access_v1.freeze_h1_current_access_predecision_context_v1(
        execution_profile=profile,
        current_source=current_source,
        proof_match_attestation=proof_match,
        recipe=recipe,
        current_identity_candidate=candidate,
        candidate_verification=verification,
        logical_occurrence_id=recipe.source.logical_occurrence_id,
        route_attempt_id=recipe.source.route_attempt_id,
        session_nonce=nonce,
    )
    input_set = access_v1.freeze_h1_current_access_predecision_input_set_v1(
        execution_profile=profile,
        context=context,
    )
    runtime_verification = runtime_v1.run_h1_current_access_fresh_exec_runtime_v1(
        predecision_context_bytes=context.canonical_bytes,
        current_source_fixture_bytes=current_source.canonical_bytes,
        proof_match_attestation_bytes=canonical_json_bytes(proof_match.to_document()),
        h1_two_role_recipe_bytes=recipe.canonical_bytes,
        current_identity_candidate_bytes=candidate.canonical_bytes,
        candidate_verification_bytes=canonical_json_bytes(verification.to_document()),
        predecision_input_set=input_set,
    )
    child = access_v1.issue_h1_current_access_child_result_v1(
        execution_profile=profile,
        context=context,
        input_set=input_set,
        runtime_verification=runtime_verification,
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
    output = output_v1.freeze_h1_production_output_operand_context_v1(
        current_access_authority=authority,
        recipe=recipe,
    )
    return output, authority, recorder


def _solve(output_context, key: str):
    context, _, _ = output_context
    return output_v1.solve_h1_production_output_branch_fixed_point_v1(
        context=context,
        branch_key=key,
    )


def test_predecision_serializer_context_contains_no_future_decision_fields(
    output_context,
) -> None:
    context, _, _ = output_context
    document = context.to_document()
    assert document["predecision_production_output_serializer_context"] is True
    assert document["route_execution_started"] is False
    assert not {
        "decision_point_id",
        "formal_v7_route_upper_id",
        "formal_v7_route_decision_id",
        "selected_route",
    } & set(document)


def test_contract_profiles_are_registered_candidates_not_fixture_numeric() -> None:
    assert output_v1.PROPOSED_CONTRACT_VERSION == "2.0.58"
    assert len(set(output_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 7
    assert set(output_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= phase3e_ids.PHASE3E_DOMAIN_TAGS
    assert output_v1.LEGACY_72_CASE_FIXTURE_IMPORTED is False
    assert output_v1.LEGACY_FIXTURE_NUMERIC_VALUE_USED is False
    assert "construction_k7_h1_branch_aware_output_contract_v1" not in output_v1.__dict__
    assert output_v1.PRODUCTION_SEMANTIC_SERIALIZER_UNIVERSE_PRESENT is False
    assert output_v1.SERIALIZER_TEMPLATE_UNIVERSE_CANDIDATE_PRESENT is True
    assert output_v1.PRODUCTION_OUTPUT_OPERAND_AUTHORITY_PRESENT is False
    assert output_v1.PRODUCTION_OUTPUT_SERIALIZER_UPPER_AUTHORITY_PRESENT is False
    assert output_v1.PRODUCTION_OUTPUT_SERIALIZER_TEMPLATE_CANDIDATE_PRESENT is True
    assert output_v1.JOINT_OUTPUT_READ_FIXED_POINT_PRESENT is False
    assert output_v1.PREDECISION_ONLY is True
    assert output_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert output_v1.ROUTE_EXECUTION_AUTHORIZED is False
    assert output_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert output_v1.OFFICIAL_SCALAR_COST is None
    assert output_v1.OFFICIAL_N_BREAK_EVEN is None

    universe = (
        output_v1.registered_h1_production_output_serializer_universe_candidate_v1()
        .to_document()
    )
    assert universe["schema"].endswith("_candidate.v1")
    assert universe["registered_template_candidate"] is True
    assert universe["production_semantic_authority"] is False
    assert universe["registered_output_roles"] == list(
        output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    )
    assert universe["durable_output_role_count"] == 8
    assert universe["ninth_durable_wrapper_allowed"] is False
    assert universe["operational_trace_contains_broker_trace"] is True
    assert universe["shared_receipt_count"] == 9
    assert universe["required_counter_record_count"] == 202
    assert universe["projection_term_count"] == 182
    assert universe["comparison_axis_count"] == 8
    assert universe["numeric_witnesses_are_actual_counter_records"] is False
    with pytest.raises(ValueError, match="authority is unavailable"):
        output_v1.official_h1_production_output_serializer_universe_v1()


def test_production_branch_dag_is_complete_and_prefix_exact() -> None:
    dag = output_v1.registered_h1_production_output_branch_dag_candidate_v1()
    document = dag.to_document()
    assert document["schema"].endswith("_candidate.v1")
    assert document["registered_template_candidate"] is True
    assert document["production_semantic_authority"] is False
    assert document["branch_completeness_source"] == (
        "PREREGISTERED_SERIALIZER_TEMPLATE_CANDIDATE_TABLE"
    )
    assert document["production_lifecycle_source_authority_present"] is False
    assert document["branch_completeness_proven"] is False
    assert document["legacy_72_case_fixture_imported"] is False
    assert document["legacy_fixture_numeric_value_used"] is False
    assert document["context_count"] == 10
    assert document["terminal_leaf_count"] == len(dag.leaves) == 90
    assert document["terminal_leaf_count_derived_from_dag"] is True
    assert document["shared_cap_rejection_before_first_business_result_present"] is True
    assert document["shared_cap_rejection_after_business_result_commit_present"] is True
    assert len(dag.by_key) == len(dag.leaves)
    with pytest.raises(ValueError, match="authority is unavailable"):
        output_v1.official_h1_production_output_branch_dag_v1()
    assert all("PHASE_SPLIT" not in leaf.branch_key for leaf in dag.leaves)

    pre = dag.by_key["PROTOCOL_PRE_BUSINESS_P7_FINALIZED"]
    assert pre.present_roles == output_v1.BROKER_OUTPUT_ROLE_ORDER
    assert pre.absent_roles == (output_v1.BUSINESS_RESULT_ROLE,)
    post = dag.by_key["INTEGRITY_POST_BUSINESS_P4_OUTPUT_COMMIT_FAILURE"]
    assert post.present_roles == output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES[:5]
    assert post.absent_roles == output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES[5:]
    exact = dag.by_key["EXACT_INFEASIBLE_P7_FINALIZED"]
    assert exact.present_roles == output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    assert exact.invalidates_official_run is False
    assert exact.certificate_coverage_satisfied is True
    cap = dag.by_key["CAP_EXHAUSTED_P7_FINALIZED"]
    assert cap.invalidates_official_run is False
    assert cap.certificate_coverage_satisfied is False
    assert cap.effective_terminal_code == "FALLBACK_CAP_EXHAUSTED"
    output_failure = dag.by_key["EXACT_INFEASIBLE_P7_CLOSURE_FAILURE"]
    assert output_failure.invalidates_official_run is True
    assert output_failure.certificate_coverage_satisfied is False
    assert output_failure.effective_terminal_class == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert output_failure.effective_terminal_code == "PROTOCOL_FAILURE"
    assert output_failure.terminal_artifact_matches_effective_closure is False
    shared_cap = dag.by_key[
        "SHARED_CAP_EXHAUSTED_PRE_BUSINESS_P7_FINALIZED"
    ]
    assert shared_cap.present_roles == output_v1.BROKER_OUTPUT_ROLE_ORDER
    assert shared_cap.absent_roles == (output_v1.BUSINESS_RESULT_ROLE,)
    shared_context = dag.context_by_kind[
        output_v1.H1ProductionOutputContextKindV1.SHARED_CAP_EXHAUSTED_PRE_BUSINESS
    ]
    assert shared_context.terminal_code == "FALLBACK_CAP_EXHAUSTED"
    assert shared_context.business_variants == ()
    post_shared_cap = dag.by_key[
        "SHARED_CAP_EXHAUSTED_POST_BUSINESS_P7_FINALIZED"
    ]
    assert post_shared_cap.present_roles == output_v1.REGISTERED_OPERATIONAL_OUTPUT_ROLES
    post_shared_context = dag.context_by_kind[
        output_v1.H1ProductionOutputContextKindV1.SHARED_CAP_EXHAUSTED_POST_BUSINESS
    ]
    assert post_shared_context.terminal_code == "FALLBACK_CAP_EXHAUSTED"
    assert post_shared_context.business_variants == (
        output_v1.H1BusinessResultVariantV1.EXACT_INFEASIBLE,
        output_v1.H1BusinessResultVariantV1.CAP_EXHAUSTED,
    )
    assert "BUSINESS_RESULT_RELAYED_AND_WORKER_ACKED" in post_shared_context.runtime_path
    assert "WORKER_REAPED" in post_shared_context.runtime_path
    assert "SHARED_RECEIPT_INPUTS_FROZEN_BEFORE_OUTPUT" in post_shared_context.runtime_path


@pytest.mark.parametrize(
    "branch_key",
    (
        "EXACT_INFEASIBLE_P7_FINALIZED",
        "CAP_EXHAUSTED_P7_FINALIZED",
        "SHARED_CAP_EXHAUSTED_PRE_BUSINESS_P7_FINALIZED",
        "SHARED_CAP_EXHAUSTED_POST_BUSINESS_P7_FINALIZED",
        "PROTOCOL_PRE_BUSINESS_P0_OUTPUT_COMMIT_FAILURE",
        "PROTOCOL_PRE_BUSINESS_P3_OUTPUT_COMMIT_FAILURE",
        "INTEGRITY_POST_BUSINESS_P4_OUTPUT_COMMIT_FAILURE",
        "INTEGRITY_POST_BUSINESS_P7_CLOSURE_FAILURE",
        "AMBIGUOUS_NATIVE_LAUNCH_P7_FINALIZED",
    ),
)
def test_success_cap_protocol_integrity_and_partial_prefix_fixed_points(
    output_context,
    branch_key: str,
) -> None:
    point = _solve(output_context, branch_key)
    leaf = output_v1.registered_h1_production_output_branch_dag_candidate_v1().by_key[branch_key]
    assert tuple(item.role for item in point.final_role_uppers) == leaf.present_roles
    assert point.output_bytes_upper == sum(
        item.upper_bytes for item in point.final_role_uppers
    )
    assert point.iterations[-1].candidate_output_bytes == point.output_bytes_upper
    assert point.iterations[-1].observed_output_bytes == point.output_bytes_upper
    assert point.iterations[-1].converged is True
    assert len(point.terminal_replay_role_upper_id_sets) == 2
    point_document = point.to_document()
    assert point_document["schema"].endswith("_candidate.v1")
    assert point_document["production_upper_authority"] is False
    assert point_document["source_authoritative_upper"] is False
    assert "h1_production_output_branch_fixed_point_id" not in point_document
    assert point.iterations[0]._payload()["schema"].endswith("_candidate.v1")
    assert point.iterations[0]._payload()["production_upper_authority"] is False
    assert all(
        item._payload()["schema"].endswith("_width_witness.v1")
        and item._payload()["production_upper_authority"] is False
        and "role_upper_id" not in item.descriptor()
        for item in point.final_role_uppers
    )
    assert (
        output_v1.replay_h1_production_output_branch_fixed_point_v1(point).fixed_point_id
        == point.fixed_point_id
    )
    assert all(item.upper_bytes <= output_v1.MAX_ROLE_BYTES for item in point.final_role_uppers)


def test_full_serializer_witness_covers_9_202_182_8_and_manifest(output_context) -> None:
    point = _solve(output_context, "EXACT_INFEASIBLE_P7_FINALIZED")
    by_role = {item.role: item for item in point.final_role_uppers}

    trace = loads_canonical_json(by_role["OPERATIONAL_TRACE"].raw_bytes)
    assert len(trace["shared_resource_receipts"]) == 9
    assert [row["path"] for row in trace["shared_resource_receipts"]] == list(
        output_v1.SHARED_RECEIPT_PATHS
    )
    assert trace["broker_trace"]

    records = loads_canonical_json(by_role["COUNTER_RECORD_SET"].raw_bytes)
    assert records["schema"].endswith(".width_witness.v1")
    assert records["counter_record_count"] == 202
    assert len(records["records"]) == 202
    assert len(records["counter_record_width_witness_ids"]) == 202
    assert all(row["observed"] is False for row in records["records"])
    assert all(row["formal_counter_record"] is False for row in records["records"])

    work = loads_canonical_json(by_role["WORK_VECTOR"].raw_bytes)
    assert work["schema"] == "acfqp.work_vector.width_witness.v1"
    assert len(work["records"]) == 202
    assert len(work["counter_record_width_witness_ids"]) == 202
    assert work["formal_work_vector"] is False

    comparison = loads_canonical_json(by_role["COMPARISON_VECTOR"].raw_bytes)
    assert comparison["schema"] == "acfqp.comparison_vector.width_witness.v1"
    assert len(comparison["values"]) == 8
    assert comparison["formal_comparison_vector"] is False

    projection = loads_canonical_json(by_role["ACTUAL_PROJECTION_PROOF"].raw_bytes)
    assert projection["schema"].endswith(".width_witness.v1")
    assert projection["projection_term_count"] == 182
    assert len(projection["projection_terms"]) == 182
    assert len({row["source_leaf"] for row in projection["projection_terms"]}) == 182
    assert projection["formal_actual_projection_proof"] is False

    terminal = loads_canonical_json(by_role["TERMINAL_ARTIFACT"].raw_bytes)
    assert terminal["schema"] == "acfqp.terminal_artifact.width_witness.v1"
    assert terminal["terminal_code"] == "FULL_GROUND_EXACT_INFEASIBLE"
    assert len(terminal["evidence_attestation_ids"]) == 32
    assert terminal["terminal_classification_issued"] is False
    assert terminal["formal_terminal_artifact"] is False

    manifest = loads_canonical_json(by_role["OUTPUT_MANIFEST"].raw_bytes)
    assert len(manifest["present_non_manifest_role_uppers"]) == 7
    assert manifest["hidden_or_wrapper_output_count"] == 0
    assert manifest["manifest_self_identity_fields_present"] is False
    assert manifest["unregistered_ninth_output_present"] is False
    assert not {
        "output_manifest_id",
        "manifest_sha256",
        "manifest_byte_count",
        "own_sha256",
    } & set(manifest)


def test_committed_terminal_is_provisional_when_later_output_closure_fails(
    output_context,
) -> None:
    point = _solve(output_context, "EXACT_INFEASIBLE_P7_CLOSURE_FAILURE")
    terminal = loads_canonical_json(
        {item.role: item for item in point.final_role_uppers}[
            "TERMINAL_ARTIFACT"
        ].raw_bytes
    )
    assert terminal["terminal_code"] == "FULL_GROUND_EXACT_INFEASIBLE"
    assert terminal["authoritative_for_effective_attempt_closure"] is False
    assert terminal["effective_attempt_closure_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert terminal["effective_attempt_closure_code"] == "PROTOCOL_FAILURE"


def test_registered_candidate_uses_strict_max_and_has_no_route_decision(output_context) -> None:
    context, _, _ = output_context
    candidate = output_v1.issue_h1_production_output_operand_candidate_v1(
        context=context
    )
    document = candidate.to_document()
    expected_count = len(
        output_v1.registered_h1_production_output_branch_dag_candidate_v1().leaves
    )
    assert len(candidate.branch_fixed_points) == expected_count
    assert document["registered_candidate_leaf_count"] == expected_count
    assert candidate.output_bytes_upper == max(
        item.output_bytes_upper for item in candidate.branch_fixed_points
    )
    assert candidate.maximizing_branch_keys == tuple(
        item.branch_key
        for item in candidate.branch_fixed_points
        if item.output_bytes_upper == candidate.output_bytes_upper
    )
    assert document["branch_reducer"] == "max"
    assert document["all_registered_output_commit_prefixes_included"] is True
    assert document["production_branch_completeness_claimed"] is False
    assert document["legacy_fixture_numeric_value_used"] is False
    assert document["ninth_durable_output_wrapper_allowed"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["route_execution_authorized"] is False
    assert document["predecision_output_serializer_upper_authority"] is False
    assert document["predecision_output_serializer_template_candidate"] is True
    assert document["final_tight_output_operand_authority"] is False
    assert document["joint_output_read_fixed_point_present"] is False
    assert document["downstream_verified_read_catalogue_required"] is True
    assert document["atomic_multi_authority_consumption_present"] is False
    assert document["typed_consumption_receipt_present"] is False
    assert "decision_point_id" not in document
    assert "formal_v7_route_upper_id" not in document
    assert "formal_v7_route_decision_id" not in document
    assert (
        output_v1.require_h1_production_output_operand_candidate_v1(
            candidate,
            replay_all_branches=False,
        )
        is candidate
    )
    with pytest.raises(ValueError, match="cannot be consumed"):
        output_v1.consume_h1_production_output_operand_candidate_v1(candidate)
    assert "h1_production_output_operand_authority_id" not in document
    assert document["schema"] == "acfqp.h1_production_output_operand_candidate.v1"
    same_payload = dict(document)
    same_payload.pop("h1_production_output_operand_candidate_id")
    assert candidate.candidate_id == content_id(
        output_v1.OPERAND_CANDIDATE_DOMAIN, same_payload
    )
    assert candidate.candidate_id != content_id(
        phase3e_ids.CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_AUTHORITY_V1_DOMAIN,
        same_payload,
    )
    with pytest.raises(ValueError, match="no authority_id"):
        _ = candidate.authority_id
    with pytest.raises(ValueError, match="authority issuance is unavailable"):
        output_v1.issue_h1_production_output_operand_authority_v1(context=context)
    with pytest.raises(ValueError, match="authority verification is unavailable"):
        output_v1.require_h1_production_output_operand_authority_v1(candidate)
    with pytest.raises(ValueError, match="authority consumption is unavailable"):
        output_v1.consume_h1_production_output_operand_authority_v1(candidate)
    legacy_shell = object.__new__(output_v1.H1ProductionOutputOperandAuthorityV1)
    with pytest.raises(ValueError, match="authority_id is unavailable"):
        _ = legacy_shell.authority_id


def test_missing_branch_ninth_wrapper_foreign_shell_and_wrong_max_fail_closed(
    output_context,
) -> None:
    context, _, _ = output_context
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="missing or unregistered",
    ):
        output_v1.solve_h1_production_output_branch_fixed_point_v1(
            context=context,
            branch_key="UNREGISTERED_BRANCH",
        )

    leaf = output_v1.registered_h1_production_output_branch_dag_candidate_v1().leaves[0]
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="ninth role",
    ):
        output_v1._freeze_role_upper(
            context=context,
            leaf=leaf,
            role="NINTH_WRAPPER",
            candidate=0,
            variants=(("ATTACK", b"{}"),),
        )

    shell = object.__new__(output_v1.H1ProductionOutputOperandCandidateV1)
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="not issuer retained",
    ):
        output_v1.require_h1_production_output_operand_candidate_v1(shell)

    candidate = output_v1.issue_h1_production_output_operand_candidate_v1(
        context=context
    )
    exact_max = candidate.output_bytes_upper
    object.__setattr__(candidate, "output_bytes_upper", exact_max + 1)
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="max reducer",
    ):
        output_v1.require_h1_production_output_operand_candidate_v1(
            candidate,
            replay_all_branches=False,
        )
    object.__setattr__(candidate, "output_bytes_upper", exact_max)
    object.__setattr__(
        candidate,
        "branch_fixed_points",
        candidate.branch_fixed_points[:-1],
    )
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="omits",
    ):
        output_v1.require_h1_production_output_operand_candidate_v1(
            candidate,
            replay_all_branches=False,
        )


def test_nondeterminism_and_nonconvergence_fail_closed(
    output_context,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, _, _ = output_context
    branch_key = "EXACT_INFEASIBLE_P7_FINALIZED"
    leaf = output_v1.registered_h1_production_output_branch_dag_candidate_v1().by_key[branch_key]

    calls = 0
    original = output_v1._render_branch_candidate

    def alternating(context_arg, leaf_arg, candidate):
        nonlocal calls
        calls += 1
        result = original(context_arg, leaf_arg, candidate)
        if calls % 2 == 0:
            first = result[0]
            attacked = output_v1._freeze_role_upper(
                context=context_arg,
                leaf=leaf_arg,
                role=first.role,
                candidate=candidate,
                variants=(("NONDETERMINISTIC_ATTACK", first.raw_bytes + b" "),),
            )
            return (attacked, *result[1:])
        return result

    monkeypatch.setattr(output_v1, "_render_branch_candidate", alternating)
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="nondeterministic",
    ):
        output_v1.solve_h1_production_output_branch_fixed_point_v1(
            context=context,
            branch_key=branch_key,
        )

    def growing(context_arg, leaf_arg, candidate):
        size = candidate + 1
        return (
            output_v1._freeze_role_upper(
                context=context_arg,
                leaf=leaf_arg,
                role=leaf.present_roles[0],
                candidate=candidate,
                variants=(("GROWING_ATTACK", b"x" * size),),
            ),
        )

    monkeypatch.setattr(output_v1, "_render_branch_candidate", growing)
    with pytest.raises(
        output_v1.ConstructionK7H1ProductionOutputUpperV1Error,
        match="did not converge",
    ):
        output_v1.solve_h1_production_output_branch_fixed_point_v1(
            context=context,
            branch_key=branch_key,
        )
