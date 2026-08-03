from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_route_segment_v4 as route_v4
from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_k7_h1_broker_ipc_v1 as ipc_v1
from acfqp import construction_k7_h1_business_adapter_v1 as adapter_v1
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_execution_topology_profile_v1 as topology_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import phase3e_fallback_owned_v3 as owned_v3
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_fallback_v1 import GroundFallbackOutcome
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"
OWNED_SOURCE = ROOT / "src" / "acfqp" / "phase3e_fallback_owned_v3.py"


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _CurrentAuthorityStub:
    identity: DurableExactInfeasibilityIdentityV1
    predecision_read_barrier_sequence: int = 10
    route_decision_freeze_sequence: int = 30

    @property
    def current_access_candidate_id(self) -> str:
        return content_id(adapter_v1.CURRENT_CANDIDATE_DOMAIN, self._payload())

    @property
    def observed_access_log_id(self) -> str:
        return _id("observed-access-log")

    @property
    def route_decision_freeze_barrier_id(self) -> str:
        return _id("route-decision-freeze-barrier")

    def _payload(self):
        return {
            "schema": "acfqp.h1_current_access_candidate.v1",
            "observed_access_log_id": self.observed_access_log_id,
            "route_decision_freeze_barrier_id": self.route_decision_freeze_barrier_id,
            "identity": self.identity.to_dict(),
            "predecision_read_barrier_sequence": (
                self.predecision_read_barrier_sequence
            ),
            "route_decision_freeze_sequence": self.route_decision_freeze_sequence,
            "observed_forbidden_call_counts": {
                name: 0 for name in adapter_v1.OBSERVED_FORBIDDEN_CALLS
            },
            "route_time_ground_free": True,
            "production_current_access_authority": False,
            "construction_candidate": True,
            "production_consumers_must_reject_candidate": True,
        }

    def to_document(self):
        return {**self._payload(), "current_access_candidate_id": self.current_access_candidate_id}


@dataclass(frozen=True)
class _FormalAuthorityStub:
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1
    identity: DurableExactInfeasibilityIdentityV1
    cap_profile_id: str
    upper_id: str = _id("formal-v7-upper")
    decision_id: str = _id("formal-v7-decision")
    decision_verification_sequence: int = 20
    route_decision_freeze_sequence: int = 30

    @property
    def route_decision_freeze_barrier_id(self) -> str:
        return _id("route-decision-freeze-barrier")

    @property
    def formal_v7_decision_candidate_id(self) -> str:
        return content_id(adapter_v1.FORMAL_CANDIDATE_DOMAIN, self._payload())

    def _payload(self):
        source = self.recipe.source
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        comparison = registry_v6.official_comparison_profile_v6(registry)
        projection = registry_v6.official_actual_projection_profile_v6(
            registry, comparison
        )
        return {
            "schema": "acfqp.h1_formal_v7_decision_candidate.v1",
            "RouteDecisionContext_id": _id("formal-v7-context"),
            "decision_point_id": _id("formal-v7-point"),
            "formal_v7_route_upper_id": self.upper_id,
            "formal_v7_route_decision_id": self.decision_id,
            "selected_route": "FALLBACK",
            "structural_id": source.structural_id,
            "query_id": source.query_id,
            "selected_plan_id": source.selected_plan_id,
            "threshold_profile_id": source.threshold_profile_id,
            "BuildEpoch_id": source.build_epoch_id,
            "kernel_id": self.identity.kernel_id,
            "reward_profile_id": self.identity.reward_profile_id,
            "policy_class_id": self.identity.policy_class_id,
            "complete_search_profile_id": self.identity.complete_search_profile_id,
            "exact_infeasibility_identity_id": (
                self.identity.exact_infeasibility_identity_id
            ),
            "logical_occurrence_id": source.logical_occurrence_id,
            "route_attempt_id": source.route_attempt_id,
            "ground_fallback_cap_profile_id": self.cap_profile_id,
            "ground_fallback_cardinality_bound_id": _id("formal-cardinality-bound"),
            "cardinality_evidence_id": _id("formal-cardinality-evidence"),
            "route_upper_formula_id": _id("formal-v7-formula"),
            "route_upper_derivation_proof_id": _id("formal-v7-derivation"),
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": stage.stage_profile_id,
            "comparison_profile_id": comparison.comparison_profile_id,
            "actual_projection_profile_id": projection.actual_projection_profile_id,
            "decision_verification_sequence": self.decision_verification_sequence,
            "route_decision_freeze_sequence": self.route_decision_freeze_sequence,
            "route_decision_freeze_barrier_id": (
                self.route_decision_freeze_barrier_id
            ),
            "formal_v7_route_authority": False,
            "construction_candidate": True,
            "production_consumers_must_reject_candidate": True,
        }

    def to_document(self):
        return {
            **self._payload(),
            "formal_v7_decision_candidate_id": self.formal_v7_decision_candidate_id,
        }


@pytest.fixture(scope="module")
def construction_inputs():
    proof_bytes = issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
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
        proof_bytes, current_identity=current
    )
    preexecution_bytes = canonical_json_bytes(candidate.to_document())
    recipe = recipe_v1.freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_bytes
    )
    source_bytes = OWNED_SOURCE.read_bytes()
    authority = route_v4.verify_sealed_owned_engine_authority_v4(source_bytes)
    return (
        identity,
        candidate,
        preexecution_bytes,
        recipe,
        source_bytes,
        authority,
        proof_bytes,
    )


def _request(construction_inputs, *, cap_profile=None, formal=None):
    (
        identity,
        preexecution,
        raw,
        recipe,
        source_bytes,
        authority,
        proof_bytes,
    ) = construction_inputs
    cap = cap_profile or preexecution.cap_profile
    formal = formal or _FormalAuthorityStub(
        recipe, identity, cap.ground_fallback_cap_profile_id
    )
    return adapter_v1.freeze_h1_production_business_request_candidate_v1(
        recipe=recipe,
        preexecution_candidate_bytes=raw,
        current_access_candidate=_CurrentAuthorityStub(identity),
        formal_route_candidate=formal,
        durable_proof_bytes=proof_bytes,
        owned_engine_source_bytes=source_bytes,
        owned_engine_authority=authority,
        route_segment_id=_id("h1-route-segment:" + formal.upper_id),
        recorder_id="h1-business-adapter-test",
        issuance_sequence=40,
    )


def _run(construction_inputs, *, cap_profile=None):
    identity, preexecution, _raw, _recipe, source_bytes, authority, _proof = (
        construction_inputs
    )
    del identity
    cap = cap_profile or preexecution.cap_profile
    request = _request(construction_inputs, cap_profile=cap)
    document = request.to_document()
    session = route_v4.OwnedEngineFallbackRouteSegmentSessionV4(
        route_segment_id=document["route_segment_id"],
        occurrence_id=document["logical_occurrence_id"],
        route_attempt_id=document["route_attempt_id"],
        recorder_id=document["recorder_id"],
        route_decision_context_id=document["RouteDecisionContext_id"],
        decision_point_id=document["decision_point_id"],
        route_decision_id=document["formal_v7_route_decision_id"],
        selected_upper_id=document["formal_v7_route_upper_id"],
        query_id=document["query_id"],
        ground_fallback_cap_profile_id=document["ground_fallback_cap_profile_id"],
        search_counter_registry_id=document["owned_search_counter_registry_id"],
        expected_search_semantics=(
            adapter_v1.replay_h1_request_search_semantics_v1(request)
        ),
        source_member_bytes=source_bytes,
        engine_authority=authority,
        engine_binding=owned_v3.require_frozen_owned_fallback_engine_binding_v3(),
    )
    kernel = G2048Kernel(2)
    query = acquisition_v1._canonical_query(kernel)
    with route_v4.activate_owned_route_segment_v4(session):
        execution = owned_v3.run_owned_ground_fallback_search_v3(
            kernel,
            query,
            route_decision_context_id=document["RouteDecisionContext_id"],
            decision_point_id=document["decision_point_id"],
            route_decision_id=document["formal_v7_route_decision_id"],
            selected_upper_id=document["formal_v7_route_upper_id"],
            route_attempt_id=document["route_attempt_id"],
            query_id=document["query_id"],
            cap_profile=cap,
            recorder_id=document["recorder_id"],
        )
        transcript = session.complete()
    result = adapter_v1.issue_h1_production_business_result_candidate_v1(
        request=request,
        execution=execution,
        owned_transcript=transcript,
    )
    return request, execution, transcript, result


@pytest.fixture(scope="module")
def exact_run(construction_inputs):
    return _run(construction_inputs)


def test_contract_domains_profiles_and_locks() -> None:
    assert adapter_v1.PROPOSED_CONTRACT_VERSION == "2.0.55"
    assert len(set(adapter_v1.REQUESTED_PHASE3E_DOMAIN_TAGS)) == 6
    assert set(adapter_v1.REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
    assert adapter_v1.PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT is False
    assert adapter_v1.FORMAL_V7_ROUTE_AUTHORITY_PRESENT is False
    assert adapter_v1.PRODUCTION_REQUEST_AUTHORITY_PRESENT is False
    assert adapter_v1.PROCESS_RUNTIME_WIRED is False
    assert adapter_v1.OFFICIAL_EXECUTION_ALLOWED is False
    assert adapter_v1.OFFICIAL_SCALAR_COST is None
    assert adapter_v1.OFFICIAL_N_BREAK_EVEN is None
    profile = adapter_v1.official_h1_business_adapter_profile_v1().to_document()
    assert profile["legacy_search_work_vector_promoted"] is False
    assert profile["formal_counter_records_issued"] == 0


def test_fake_protocol_can_only_mint_explicit_candidate(construction_inputs) -> None:
    request = _request(construction_inputs)
    document = request.to_document()
    assert type(request) is adapter_v1.H1ProductionBusinessRequestCandidateV1
    assert document["production_request_authority"] is False
    assert document["production_consumers_must_reject_candidate"] is True
    assert document["post_formal_decision_issuance"] is True
    semantics = adapter_v1.replay_h1_request_search_semantics_v1(request)
    assert document["search_semantics_id"] == semantics.semantics_id
    assert document["kernel_replay_document_id"] == semantics.kernel_id
    assert document["query_replay_document_id"] == semantics.derived_query_id
    assert document["search_semantics_bridge"][
        "caller_semantic_label_accepted"
    ] is False
    assert document["search_semantics_bridge"][
        "fresh_exec_transition_authority"
    ] is False
    assert document["search_semantics_bridge"]["bridge_scope"] == (
        "METADATA_CONFIGURATION_COMPATIBILITY_ONLY"
    )
    assert document["search_semantics_bridge"][
        "transition_table_equivalence_proved"
    ] is False
    assert document["search_semantics_bridge"][
        "durable_kernel_source_equivalence_proved"
    ] is False
    assert document["search_semantics_bridge"][
        "production_consumers_must_reject_candidate"
    ] is True
    assert document["observed_forbidden_call_counts"] == {
        name: 0 for name in adapter_v1.OBSERVED_FORBIDDEN_CALLS
    }
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="production H1 request issuance is blocked",
    ):
        adapter_v1.freeze_h1_production_business_request_v1(
            current_access_candidate=_CurrentAuthorityStub(construction_inputs[0]),
            formal_route_candidate=_FormalAuthorityStub(
                construction_inputs[3],
                construction_inputs[0],
                construction_inputs[1].cap_profile.ground_fallback_cap_profile_id,
            ),
        )


def test_reserved_production_classes_never_validate_by_exact_type() -> None:
    request_shell = object.__new__(adapter_v1.H1ProductionBusinessRequestV1)
    result_shell = object.__new__(adapter_v1.H1ProductionBusinessResultV1)
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="exact class identity is never sufficient",
    ):
        adapter_v1.require_h1_production_business_request_authority_v1(
            request_shell
        )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="exact class identity is never sufficient",
    ):
        adapter_v1.require_h1_production_business_result_authority_v1(result_shell)


def test_request_rejects_noncanonical_durable_replay_bytes(
    construction_inputs,
) -> None:
    identity, preexecution, raw, recipe, source_bytes, authority, proof_bytes = (
        construction_inputs
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="durable proof did not replay",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            recipe=recipe,
            preexecution_candidate_bytes=raw,
            current_access_candidate=_CurrentAuthorityStub(identity),
            formal_route_candidate=_FormalAuthorityStub(
                recipe,
                identity,
                preexecution.cap_profile.ground_fallback_cap_profile_id,
            ),
            durable_proof_bytes=proof_bytes + b" ",
            owned_engine_source_bytes=source_bytes,
            owned_engine_authority=authority,
            route_segment_id=_id("bad-durable-proof-segment"),
            recorder_id="bad-durable-proof",
            issuance_sequence=40,
        )


def test_current_candidate_and_legacy_upper_decision_are_hard_rejected(
    construction_inputs,
) -> None:
    identity, preexecution, raw, recipe, source_bytes, authority, proof_bytes = (
        construction_inputs
    )
    common = dict(
        recipe=recipe,
        preexecution_candidate_bytes=raw,
        durable_proof_bytes=proof_bytes,
        formal_route_candidate=_FormalAuthorityStub(
            recipe,
            identity,
            preexecution.cap_profile.ground_fallback_cap_profile_id,
        ),
        owned_engine_source_bytes=source_bytes,
        owned_engine_authority=authority,
        route_segment_id=_id("reject-route-segment"),
        recorder_id="reject-test",
        issuance_sequence=40,
    )
    legacy_candidate = object.__new__(
        current_v1.H1ProductionCurrentIdentityCandidateV1
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="current candidate is never",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            current_access_candidate=legacy_candidate, **common
        )

    legacy_formal = _FormalAuthorityStub(
        recipe,
        identity,
        preexecution.cap_profile.ground_fallback_cap_profile_id,
        upper_id=recipe.source.legacy_selected_upper_id,
        decision_id=recipe.source.legacy_route_decision_id,
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="Contract 2.0.50 upper/decision",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            current_access_candidate=_CurrentAuthorityStub(identity),
            **{**common, "formal_route_candidate": legacy_formal},
        )


def test_request_api_rejects_postrun_objects_and_bad_sequence(construction_inputs) -> None:
    with pytest.raises(TypeError):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            **{}, postrun_work_vector=object()
        )
    identity, preexecution, raw, recipe, source_bytes, authority, proof_bytes = (
        construction_inputs
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="request issuance sequence or shared route freeze is invalid",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            recipe=recipe,
            preexecution_candidate_bytes=raw,
            current_access_candidate=_CurrentAuthorityStub(identity),
            formal_route_candidate=_FormalAuthorityStub(
                recipe,
                identity,
                preexecution.cap_profile.ground_fallback_cap_profile_id,
            ),
            durable_proof_bytes=proof_bytes,
            owned_engine_source_bytes=source_bytes,
            owned_engine_authority=authority,
            route_segment_id=_id("bad-sequence-segment"),
            recorder_id="bad-sequence",
            issuance_sequence=30,
        )

    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="request issuance sequence or shared route freeze is invalid",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            recipe=recipe,
            preexecution_candidate_bytes=raw,
            current_access_candidate=_CurrentAuthorityStub(identity),
            formal_route_candidate=_FormalAuthorityStub(
                recipe,
                identity,
                preexecution.cap_profile.ground_fallback_cap_profile_id,
            ),
            durable_proof_bytes=proof_bytes,
            owned_engine_source_bytes=source_bytes,
            owned_engine_authority=authority,
            route_segment_id=_id("bool-sequence-segment"),
            recorder_id="bool-sequence",
            issuance_sequence=True,
        )


@pytest.mark.parametrize(
    "identity_field",
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
def test_request_rejects_every_spliced_exact_identity_coordinate(
    construction_inputs, identity_field
) -> None:
    identity, preexecution, raw, recipe, source_bytes, authority, proof_bytes = (
        construction_inputs
    )
    spliced = replace(identity, **{identity_field: _id(f"spliced-{identity_field}")})
    formal = _FormalAuthorityStub(
        recipe,
        spliced,
        preexecution.cap_profile.ground_fallback_cap_profile_id,
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="identity|identities|frozen H1 recipe",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            recipe=recipe,
            preexecution_candidate_bytes=raw,
            current_access_candidate=_CurrentAuthorityStub(identity),
            formal_route_candidate=formal,
            durable_proof_bytes=proof_bytes,
            owned_engine_source_bytes=source_bytes,
            owned_engine_authority=authority,
            route_segment_id=_id(f"spliced-segment-{identity_field}"),
            recorder_id="spliced-identity",
            issuance_sequence=40,
        )


def test_request_rejects_different_current_and_formal_route_freeze(
    construction_inputs,
) -> None:
    identity, preexecution, raw, recipe, source_bytes, authority, proof_bytes = (
        construction_inputs
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="shared route freeze",
    ):
        adapter_v1.freeze_h1_production_business_request_candidate_v1(
            recipe=recipe,
            preexecution_candidate_bytes=raw,
            current_access_candidate=_CurrentAuthorityStub(identity),
            formal_route_candidate=_FormalAuthorityStub(
                recipe,
                identity,
                preexecution.cap_profile.ground_fallback_cap_profile_id,
                route_decision_freeze_sequence=31,
            ),
            durable_proof_bytes=proof_bytes,
            owned_engine_source_bytes=source_bytes,
            owned_engine_authority=authority,
            route_segment_id=_id("different-freeze-segment"),
            recorder_id="different-freeze",
            issuance_sequence=40,
        )


def test_exact_infeasible_result_binds_owned_transcript_without_workvector_promotion(
    exact_run,
) -> None:
    request, execution, transcript, result = exact_run
    document = result.to_document()
    assert execution.result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    assert document["outcome"] == "INFEASIBLE_CERTIFIED"
    assert document["owned_event_count"] == len(transcript.events) == 208
    assert document["owned_values"] == {
        "fallback.states_expanded": 8,
        "fallback.actions_evaluated": 16,
        "fallback.ground_steps": 16,
        "fallback.outcome_rows": 96,
        "fallback.bellman_backups": 16,
        "control.cap_checks": 56,
        "control.cap_rejections": 0,
    }
    assert document["frontier"][0]["expected_reward"] == Fraction(83, 2624)
    assert document["frontier"][0]["failure_probability"] == Fraction(383, 410)
    assert document["legacy_search_work_vector"]["promoted_to_h1_work_vector"] is False
    assert document["formal_work_vector_id"] is None
    assert document["owned_engine_finished_execution_binding_id"] == (
        transcript.terminal.finished_execution_binding.binding_id
    )
    assert document["production_result_authority"] is False
    assert result.sha256 == hashlib.sha256(result.canonical_bytes).hexdigest()
    assert result.byte_count == len(result.canonical_bytes)
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="production H1 result issuance is blocked",
    ):
        adapter_v1.issue_h1_production_business_result_v1(
            request=request, execution=execution, owned_transcript=transcript
        )


def test_same_transcript_cannot_authorize_changed_execution(exact_run) -> None:
    request, execution, transcript, _result = exact_run
    changed_execution = replace(
        execution,
        result=replace(execution.result, composed_candidate_count=15),
    )
    with pytest.raises(
        adapter_v1.ConstructionK7H1BusinessAdapterV1Error,
        match="transcript-frozen fingerprint",
    ):
        adapter_v1.issue_h1_production_business_result_candidate_v1(
            request=request,
            execution=changed_execution,
            owned_transcript=transcript,
        )


def test_cap_exhaustion_is_typed_and_never_infeasible(construction_inputs) -> None:
    cap = replace(construction_inputs[1].cap_profile, max_states_expanded=7)
    _request_value, execution, transcript, result = _run(
        construction_inputs, cap_profile=cap
    )
    document = result.to_document()
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert document["outcome"] == "CAP_EXHAUSTED"
    assert document["search_complete"] is False
    assert document["frontier"] == []
    assert document["selected"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "CAP_EXHAUSTED",
    }
    assert document["cap_outcome"] == {
        "kind": "EXHAUSTED_CAP",
        "name": "max_states_expanded",
    }
    assert document["owned_values"]["control.cap_rejections"] == 1
    assert document["search_semantics_id"] == _request_value.to_document()[
        "search_semantics_id"
    ]
    assert transcript.terminal.exact_search_finished is True


def test_topology_exact_fd_origins_and_capability_separation() -> None:
    profile = topology_v1.official_h1_execution_topology_profile_v1()
    document = profile.to_document()
    grants = document["fd_grants"]
    assert document["child_launch_order"] == ["WORKER", "BUSINESS"]
    assert document["expected_child_process_launches"] == 2
    assert document["scm_rights_allowed"] is False
    assert all(
        row["inherited_at_fresh_exec"] is (row["role"] != "BROKER")
        for row in grants
    )
    assert {
        row["descriptor_role"] for row in grants if row["role"] == "WORKER"
    } == {"broker_channel", "business_result"}
    assert {
        row["descriptor_role"] for row in grants if row["role"] == "BUSINESS"
    } == {"broker_channel", "business_result", "output_directory"}
    pidfds = [row for row in grants if row["object_kind"] == "PIDFD"]
    assert len(pidfds) == 2
    assert all(row["origin"] == "CLONE3_PIDFD_RESULT" for row in pidfds)
    channel_rows = [row for row in grants if row["channel_pair_id"] is not None]
    assert {
        row["channel_pair_id"] for row in channel_rows
    } == {
        topology_v1.WORKER_CHANNEL_PAIR_ID,
        topology_v1.BUSINESS_CHANNEL_PAIR_ID,
    }
    for pair_id in {
        topology_v1.WORKER_CHANNEL_PAIR_ID,
        topology_v1.BUSINESS_CHANNEL_PAIR_ID,
    }:
        endpoints = [row for row in channel_rows if row["channel_pair_id"] == pair_id]
        assert len(endpoints) == 2
        assert len({row["physical_object"] for row in endpoints}) == 2
    result_grants = [row for row in grants if row["physical_object"] == "business_result_inode"]
    assert [row["access"] for row in result_grants] == [
        "READ_ONLY",
        "READ_ONLY",
        "READ_WRITE",
    ]
    assert {row["object_kind"] for row in result_grants} == {
        "O_TMPFILE_REGULAR_FILE"
    }
    assert len({row["open_file_description"] for row in result_grants}) == 3
    sealed = document["sealed_input_grants"]
    assert {(row["role"], row["fd_number"]) for row in sealed} == {
        ("WORKER", 10),
        ("WORKER", 11),
        ("WORKER", 12),
        ("BUSINESS", 10),
        ("BUSINESS", 11),
        ("BUSINESS", 12),
        ("BUSINESS", 13),
        ("BUSINESS", 14),
        ("BUSINESS", 15),
        ("BUSINESS", 16),
    }
    assert all(row["ambient_path_fallback_allowed"] is False for row in sealed)
    assert all(row["scm_rights_delivery_allowed"] is False for row in sealed)
    lifecycle = document["lifecycle"]
    assert [row["ordinal"] for row in lifecycle] == list(range(1, 22))
    assert [row["step"] for row in lifecycle[:4]] == [
        "PREDECISION_INPUTS_FROZEN",
        "FORMAL_DECISION_VERIFIED",
        "ROUTE_DECISION_FROZEN",
        "REQUEST_CANDIDATE_SERIALIZED_AND_SEALED",
    ]
    assert all(row["runtime_implemented"] is False for row in lifecycle)


def test_five_frame_ipc_binding_and_payload_chain(exact_run) -> None:
    request, _execution, _owned, result = exact_run
    binding = ipc_v1.freeze_h1_broker_ipc_binding_v1(
        request=request,
        topology=topology_v1.official_h1_execution_topology_profile_v1(),
        broker_execution_spec_id=_id("h1-broker-execution-spec"),
        session_nonce=_id("h1-broker-session-nonce"),
    )
    ready = ipc_v1.issue_worker_ready_v1(
        binding=binding, worker_role_instance_id=_id("worker-role-instance")
    )
    business_request = ipc_v1.issue_business_request_v1(
        binding=binding, worker_ready=ready
    )
    commit_candidate = ipc_v1.freeze_business_result_commit_receipt_candidate_v1(
        business_result=result
    )
    commit_document = commit_candidate.to_document()
    assert commit_document["write_observed"] is False
    assert commit_document["fsync_observed"] is False
    assert commit_document["linkat_observed"] is False
    assert commit_document["rename_noreplace_observed"] is False
    assert commit_document["business_exit_before_relay_observed"] is False
    business_result = ipc_v1.issue_business_result_v1(
        binding=binding,
        business_request=business_request,
        business_result=result,
        commit_candidate=commit_candidate,
    )
    worker_candidate = ipc_v1.freeze_worker_result_verification_candidate_v1(
        commit_candidate=commit_candidate,
        topology=topology_v1.official_h1_execution_topology_profile_v1(),
    )
    ack = ipc_v1.issue_worker_ack_v1(
        binding=binding,
        business_result=business_result,
        worker_verification_candidate=worker_candidate,
    )
    eof = ipc_v1.issue_worker_eof_v1(binding=binding, worker_ack=ack)
    transcript = ipc_v1.freeze_h1_broker_ipc_transcript_v1(
        binding=binding,
        worker_ready=ready,
        business_request=business_request,
        business_result=business_result,
        worker_ack=ack,
        worker_eof=eof,
    )
    document = transcript.to_document()
    assert [row["frame_role"] for row in document["frames"]] == [
        "WORKER_READY",
        "BUSINESS_REQUEST",
        "BUSINESS_RESULT",
        "WORKER_ACK",
        "WORKER_EOF",
    ]
    assert ipc_v1.FRAME_AUTHORS == (
        "WORKER",
        "WORKER",
        "BUSINESS",
        "WORKER",
        "WORKER",
    )
    assert business_request.payload["worker_frame_is_authorization_signal_only"] is True
    assert ack.payload["read_only_distinct_ofd_authority"] is False
    assert ack.payload["worker_runtime_verification_pending"] is True
    assert ack.payload["business_result_commit_receipt_candidate_id"] == (
        business_result.payload["business_result_commit_receipt_candidate_id"]
    )
    assert ack.payload["worker_verification_authority"] is False
    assert all(row["kernel_sender_credentials_verified"] is False for row in document["frames"])
    assert document["official_execution_allowed"] is False


def test_ipc_payload_schemas_are_exact_and_bool_is_not_an_integer(exact_run) -> None:
    request, _execution, _owned, result = exact_run
    topology = topology_v1.official_h1_execution_topology_profile_v1()
    binding = ipc_v1.freeze_h1_broker_ipc_binding_v1(
        request=request,
        topology=topology,
        broker_execution_spec_id=_id("strict-ipc-spec"),
        session_nonce=_id("strict-ipc-nonce"),
    )
    ready = ipc_v1.issue_worker_ready_v1(
        binding=binding, worker_role_instance_id=_id("strict-ipc-worker")
    )
    extra = dict(ready.payload)
    extra["extra"] = 0
    with pytest.raises(
        ipc_v1.ConstructionK7H1BrokerIPCV1Error,
        match="payload fields are not exact",
    ):
        ipc_v1._H1BrokerFrameV1(
            ipc_v1._FRAME_ISSUER,
            ready.role,
            binding.binding_id,
            ready.sequence,
            ready.predecessor_id,
            extra,
        )

    commit = ipc_v1.freeze_business_result_commit_receipt_candidate_v1(
        business_result=result
    )
    request_frame = ipc_v1.issue_business_request_v1(
        binding=binding, worker_ready=ready
    )
    result_frame = ipc_v1.issue_business_result_v1(
        binding=binding,
        business_request=request_frame,
        business_result=result,
        commit_candidate=commit,
    )
    bool_extent = dict(result_frame.payload)
    bool_extent["business_result_byte_count"] = True
    with pytest.raises(
        ipc_v1.ConstructionK7H1BrokerIPCV1Error,
        match="payload values are invalid",
    ):
        ipc_v1._H1BrokerFrameV1(
            ipc_v1._FRAME_ISSUER,
            result_frame.role,
            binding.binding_id,
            result_frame.sequence,
            result_frame.predecessor_id,
            bool_extent,
        )


def test_ipc_rejects_cross_binding_and_legacy_parent_output(exact_run) -> None:
    request, _execution, _owned, _result = exact_run
    topology = topology_v1.official_h1_execution_topology_profile_v1()
    left = ipc_v1.freeze_h1_broker_ipc_binding_v1(
        request=request,
        topology=topology,
        broker_execution_spec_id=_id("left-spec"),
        session_nonce=_id("left-nonce"),
    )
    right = ipc_v1.freeze_h1_broker_ipc_binding_v1(
        request=request,
        topology=topology,
        broker_execution_spec_id=_id("right-spec"),
        session_nonce=_id("right-nonce"),
    )
    ready = ipc_v1.issue_worker_ready_v1(
        binding=left, worker_role_instance_id=_id("cross-worker")
    )
    with pytest.raises(ipc_v1.ConstructionK7H1BrokerIPCV1Error):
        ipc_v1.issue_business_request_v1(binding=right, worker_ready=ready)
    assert "PARENT_OUTPUT" not in {role.value for role in ipc_v1.H1BrokerFrameRoleV1}
