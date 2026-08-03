from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_output_bytes_fixed_point_v1 as output_v1
from acfqp import phase3e_ids
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@pytest.fixture(scope="module")
def preexecution_bytes() -> bytes:
    proof = issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof)["identity"]
    )
    current = acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )
    candidate = acquisition_v1.replay_canonical_direct_fallback_preexecution_candidate_v1(
        proof,
        current_identity=current,
    )
    return canonical_json_bytes(candidate.to_document())


@pytest.fixture(scope="module")
def recipe(preexecution_bytes: bytes):
    return recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_bytes
    )


def test_recipe_domains_and_profile_are_exact_and_construction_only() -> None:
    profile = recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1()
    document = profile.to_document()
    assert set(recipe_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= phase3e_ids.PHASE3E_DOMAIN_TAGS
    assert len(set(recipe_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 2
    assert document["construction_only"] is True
    assert document["official_execution_allowed"] is False
    assert document["formal_v7_route_authority_present"] is False
    assert document["numeric_aggregate_candidate_issued"] is False
    assert document["numeric_memory_upper"] is None
    assert document["numeric_memory_operand_authority_ids"] is None


def test_primary_input_is_preexecution_only_and_never_postrun_acquisition(
    preexecution_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("recipe construction must not access ground execution")

    monkeypatch.setattr(acquisition_v1.G2048Kernel, "step", forbidden)
    monkeypatch.setattr(acquisition_v1, "run_ground_fallback_search_v1", forbidden)
    frozen = recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_bytes
    )
    document = frozen.to_document()
    assert document["postrun_acquisition_required"] is False
    assert document["bytes_only_projection_calls_kernel_step"] is False
    assert document["bytes_only_projection_calls_fallback_solver"] is False
    assert "acquisition_bytes" not in inspect.signature(
        recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1
    ).parameters


def test_legacy_h1_identity_chain_is_bound_but_not_promoted(recipe) -> None:
    document = recipe.to_document()
    source = document["legacy_h1_preexecution_projection"]
    assert source["preexecution_candidate_id"] == recipe.source.preexecution_candidate_id
    assert source["RouteDecisionContext_id"] == recipe.source.route_decision_context_id
    assert source["decision_point_id"] == recipe.source.decision_point_id
    assert source["legacy_selected_upper_id"] == recipe.source.legacy_selected_upper_id
    assert source["legacy_route_decision_id"] == recipe.source.legacy_route_decision_id
    assert source["projection_status"] == (
        "STRUCTURAL_BYTES_ONLY_NOT_SEMANTIC_AUTHORITY"
    )
    assert source["source_bytes_semantically_verified"] is False
    assert source["content_addressing_authenticates_current_identity"] is False
    assert source["claimed_h1_semantics_authenticated"] is False
    assert source["durable_proof_bytes_bound"] is False
    assert source["current_kernel_law_authenticated"] is False
    assert source["production_current_identity_verifier_required"] is True
    assert source["legacy_upper_used_as_formal_v7_upper"] is False
    assert source["legacy_route_decision_used_as_formal_v7_decision"] is False
    assert document["formal_v7_route_upper_id"] is None
    assert document["formal_v7_route_decision_id"] is None
    assert document["bytes_only_projection_is_semantic_current_identity_authority"] is False


def test_root_cap_profiles_are_reference_only_and_h1_successors_are_missing(
    recipe,
) -> None:
    profile = recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().to_document()
    assert profile["reference_existing_root_cap_role_manifest_profile_id"] == (
        manifest_v2.official_v075_k7_production_role_manifest_profile_v2().profile_id
    )
    assert profile["reference_existing_root_cap_runtime_profile_id"] == (
        runtime_v2.official_v075_k7_production_broker_runtime_profile_v2().profile_id
    )
    assert profile["required_h1_role_manifest_profile_id"] is None
    assert profile["required_h1_runtime_profile_id"] is None
    assert profile["root_cap_profiles_are_h1_profiles"] is False
    assert profile["current_root_cap_manifest_or_runtime_instance_accepted"] is False
    document = recipe.to_document()
    assert document["current_root_cap_instance_accepted"] is False
    assert document["production_role_manifest_id"] is None
    assert document["production_runtime_envelope_id"] is None
    parameters = inspect.signature(
        recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1
    ).parameters
    assert set(parameters) == {"preexecution_candidate_bytes"}


def test_postdecision_order_is_exact_and_keeps_all_side_effects_after_decision() -> None:
    profile = recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().to_document()
    steps = profile["post_decision_steps"]
    assert [row["ordinal"] for row in steps] == list(range(1, len(steps) + 1))
    position = {row["step_key"]: row["ordinal"] for row in steps}
    assert position["assert_formal_route_decision"] == 1
    assert position["open_complete_route_window"] == 2
    assert position["activate_frozen_broker_parent_memory_scope"] < position[
        "launch_worker_then_business"
    ]
    assert position["bind_outer_broker_worker_business_caps"] < position[
        "launch_worker_then_business"
    ]
    assert position["reserve_whole_route_output_upper"] < position[
        "launch_worker_then_business"
    ]
    assert position["stage_and_open_payloads"] < position[
        "launch_worker_then_business"
    ]
    assert position["execute_h1_business_adapter"] > position[
        "launch_worker_then_business"
    ]
    assert position["seal_pre_reap_business_result"] < position[
        "authenticate_protocol_and_reap"
    ]
    assert position["render_and_commit_post_reap_roles"] > position[
        "authenticate_protocol_and_reap"
    ]
    assert position["observe_peak_and_close_visibility"] > position[
        "authenticate_protocol_and_reap"
    ]
    assert profile["post_decision_steps_are_success_or_postbusiness_order"] is True
    assert "preserve the exact prefix" in profile["failure_transition_rule"]
    assert profile["predecision_prerequisites_satisfied"] is False
    assert profile["postdecision_scope_or_formula_resolution_allowed"] is False
    prerequisites = profile["required_predecision_prerequisites"]
    assert "BROKER_PARENT_CONTINUOUS_MEMORY_SCOPE_AUTHORITY" in prerequisites
    assert "OFFICIAL_MEMORY_FORMULA_AUTHORITY" in prerequisites
    assert "FORMAL_V7_DIRECT_FALLBACK_UPPER" in prerequisites
    assert "FORMAL_V7_FALLBACK_ROUTE_DECISION" in prerequisites


def test_memory_scope_schema_blocks_child_only_peak_and_all_numeric_values() -> None:
    profile = recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().to_document()
    scopes = {row["scope_key"]: row for row in profile["memory_scope_requirements"]}
    assert tuple(scopes) == ("OUTER", "BROKER_PARENT", "WORKER", "BUSINESS")
    assert scopes["OUTER"]["members"] == [
        "BROKER_PARENT",
        "WORKER_PROCESS",
        "BUSINESS_PROCESS",
    ]
    assert scopes["WORKER"]["members"] == ["WORKER_PROCESS"]
    assert scopes["BUSINESS"]["members"] == ["BUSINESS_PROCESS"]
    assert scopes["BROKER_PARENT"]["members"] == ["BROKER_PARENT"]
    assert all(row["numeric_cap_bytes"] is None for row in scopes.values())
    assert all(
        row["operand_authority_status"] == "REQUIRED_UNBOUND"
        for row in scopes.values()
    )
    assert profile["memory_scope_status"] == "UNRESOLVED"
    assert profile["broker_parent_child_only_peak_is_complete_route_peak"] is False
    assert profile["broker_parent_allowed_outside_continuous_route_scope"] is False
    assert profile["official_memory_formula"] is None
    assert profile["source_manifest_two_child_role_formula_is_complete_route_formula"] is False
    assert profile["safe_memory_formula_candidates"] == [
        "OUTER_CGROUP_CAP_BYTES if OUTER continuously contains BROKER_PARENT+WORKER_PROCESS+BUSINESS_PROCESS",
        "min(OUTER_CGROUP_CAP_BYTES,BROKER_PARENT_CGROUP_CAP_BYTES+WORKER_ROLE_CGROUP_CAP_BYTES+BUSINESS_ROLE_CGROUP_CAP_BYTES)",
    ]
    assert "BROKER_PARENT_CONTINUOUS_MEMORY_SCOPE_UNRESOLVED" in profile["blockers"]


def test_eight_role_output_and_failure_branch_schema_remain_required_unbound() -> None:
    profile = recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().to_document()
    roles = profile["output_roles"]
    assert [row["artifact_role"] for row in roles] == list(
        output_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
    )
    assert len(roles) == profile["durable_output_role_registry_count"] == 8
    assert roles[0]["artifact_role"] == "BUSINESS_RESULT"
    assert roles[0]["durable_timing"] == "PRE_REAP_IMMUTABLE"
    assert all(
        row["durable_timing"] == "POST_REAP_FINALIZATION"
        for row in roles[1:]
    )
    manifest = roles[-1]
    assert "EMBED_CANDIDATE_TOTAL_NOT_OWN_HASH" in manifest["required_semantics"]
    assert profile["ninth_durable_output_wrapper_allowed"] is False
    assert profile["output_manifest_self_hash_allowed"] is False
    assert profile["successful_finalization_requires_all_eight_roles"] is True
    assert profile[
        "postbusiness_finalization_failure_guarantees_all_eight_roles"
    ] is False
    assert profile["failed_finalization_preserves_committed_role_subset"] is True
    assert profile["failed_finalization_requires_typed_uncommitted_role_absence"] is True
    assert profile["failed_finalization_official_run_valid"] is False
    assert profile["broker_output_recovery_renderer_present"] is False
    assert profile["broker_fabricated_business_result_allowed"] is False
    assert profile["early_failure_typed_business_result_absence_allowed"] is True
    assert profile["early_failure_broker_owned_role_subset"] == list(
        output_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[1:]
    )
    assert profile[
        "early_failure_output_manifest_requires_typed_business_result_absence"
    ] is True
    assert profile["branch_presence_matrix_authority_id"] is None
    assert profile["output_fixed_point_result_id"] is None
    assert profile["output_failure_branch_catalogue_id"] is None
    branches = profile["required_failure_branches"]
    assert len(branches) == 7
    presence = {row["branch_key"]: row["business_result_presence"] for row in branches}
    assert presence["EXACT_INFEASIBLE_SUCCESS"] == "REQUIRED"
    assert presence["AMBIGUOUS_NATIVE_LAUNCH"] == "TYPED_ABSENT_REQUIRED"
    assert presence["PROTOCOL_OR_ACCOUNTING_FAILURE"] == "PHASE_SPLIT_REQUIRED"
    presence_rule = {
        row["branch_key"]: row["durable_role_presence_rule"] for row in branches
    }
    assert presence_rule["EXACT_INFEASIBLE_SUCCESS"] == (
        "ALL_EIGHT_AFTER_SUCCESSFUL_FINALIZATION"
    )
    assert presence_rule["OUTPUT_FINALIZATION_FAILURE"] == (
        "PRESERVE_COMMITTED_SUBSET_AND_TYPED_UNCOMMITTED_ABSENCE_OFFICIAL_INVALID"
    )
    assert all(row["renderer_schema_authority_id"] is None for row in branches)
    assert all(row["branch_upper_operand_authority_id"] is None for row in branches)
    assert all(row["authority_status"] == "REQUIRED_UNBOUND" for row in branches)
    assert profile["minimum_failure_branch_set_claimed_complete"] is False
    assert profile["branch_complete_renderer_and_reachability_proof_required"] is True
    assert profile["unregistered_reachable_failure_branch_allowed"] is False
    assert "OUTPUT_BRANCH_PRESENCE_MATRIX_AUTHORITY_MISSING" in profile["blockers"]
    assert profile["read_family_catalogue_id"] is None
    assert profile["staging_family_catalogue_id"] is None
    assert profile["mount_interval_catalogue_id"] is None
    assert profile["hash_purpose_catalogue_id"] is None
    assert profile["integrity_obligation_catalogue_id"] is None
    assert profile["protocol_obligation_catalogue_id"] is None
    assert profile["path_specific_shared_admission_catalogue_id"] is None
    assert profile["control_cap_check_formula_authority_id"] is None


def test_exact_replay_rejects_recipe_and_preexecution_tampering(
    recipe,
    preexecution_bytes: bytes,
) -> None:
    replay = recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1(
        raw=recipe.canonical_bytes,
        preexecution_candidate_bytes=preexecution_bytes,
    )
    assert replay.to_document() == recipe.to_document()

    attacked_recipe = loads_canonical_json(recipe.canonical_bytes)
    attacked_recipe["required_h1_runtime_profile_id"] = (
        attacked_recipe["reference_existing_root_cap_runtime_profile_id"]
    )
    payload = dict(attacked_recipe)
    payload.pop("h1_direct_fallback_two_role_recipe_id")
    attacked_recipe["h1_direct_fallback_two_role_recipe_id"] = content_id(
        recipe_v1.RECIPE_DOMAIN, payload
    )
    with pytest.raises(recipe_v1.ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error):
        recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1(
            raw=canonical_json_bytes(attacked_recipe),
            preexecution_candidate_bytes=preexecution_bytes,
        )

    attacked_pre = loads_canonical_json(preexecution_bytes)
    attacked_pre["selected_route"] = "LOCAL"
    payload = dict(attacked_pre)
    payload.pop("direct_fallback_preexecution_candidate_id")
    attacked_pre["direct_fallback_preexecution_candidate_id"] = content_id(
        phase3e_ids.CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
        payload,
    )
    with pytest.raises(recipe_v1.ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error):
        recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
            preexecution_candidate_bytes=canonical_json_bytes(attacked_pre)
        )

    unknown_pre = loads_canonical_json(preexecution_bytes)
    unknown_pre["caller_extension"] = "forbidden"
    payload = dict(unknown_pre)
    payload.pop("direct_fallback_preexecution_candidate_id")
    unknown_pre["direct_fallback_preexecution_candidate_id"] = content_id(
        phase3e_ids.CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
        payload,
    )
    with pytest.raises(recipe_v1.ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error):
        recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
            preexecution_candidate_bytes=canonical_json_bytes(unknown_pre)
        )


def test_recipe_is_issuer_retained_and_cannot_be_directly_constructed(recipe) -> None:
    with pytest.raises(recipe_v1.ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error):
        recipe_v1.H1DirectFallbackTwoRoleRecipeV1(object(), recipe.source)


def test_caller_rehashed_current_law_remains_explicitly_nonauthoritative(
    preexecution_bytes: bytes,
) -> None:
    attacked = loads_canonical_json(preexecution_bytes)
    current = attacked["current_identity_attestation"]
    identity = current["identity"]
    fake_kernel_id = hashlib.sha256(b"caller-rehashed-kernel-claim").hexdigest()
    identity["kernel_id"] = fake_kernel_id
    identity_payload = dict(identity)
    identity_payload.pop("exact_infeasibility_identity_id")
    identity["exact_infeasibility_identity_id"] = content_id(
        phase3e_ids.PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN,
        identity_payload,
    )
    current_payload = dict(current)
    current_payload.pop("current_identity_attestation_id")
    current["current_identity_attestation_id"] = content_id(
        phase3e_ids.CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN,
        current_payload,
    )
    attacked["current_identity_attestation_id"] = current[
        "current_identity_attestation_id"
    ]
    attacked_payload = dict(attacked)
    attacked_payload.pop("direct_fallback_preexecution_candidate_id")
    attacked["direct_fallback_preexecution_candidate_id"] = content_id(
        phase3e_ids.CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
        attacked_payload,
    )

    projected = recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=canonical_json_bytes(attacked)
    ).to_document()["legacy_h1_preexecution_projection"]
    assert projected["kernel_id"] == fake_kernel_id
    assert projected["source_bytes_semantically_verified"] is False
    assert projected["content_addressing_authenticates_current_identity"] is False
    assert projected["claimed_h1_semantics_authenticated"] is False
    assert projected["durable_proof_bytes_bound"] is False
