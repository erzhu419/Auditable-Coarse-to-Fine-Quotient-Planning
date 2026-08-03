from __future__ import annotations

from copy import deepcopy
import hashlib
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import campaign_v1
from acfqp import construction_k7_formal_accounting_materializer_v1 as materializer
from acfqp import construction_k7_production_complete_bundle_independent_verifier_v1 as verifier
from acfqp import construction_k7_root_cap_terminal_authority_v1 as terminal
from acfqp import construction_k7_semantic_evidence_closure_v1 as closure_v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as route_ipc_v1
from acfqp import v075_live_dynamic_acquisition_authority_v2 as dynamic_v2
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as multiround_v2
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_v2
from acfqp.phase3e_ids import (
    TYPED_VERIFICATION_ATTESTATION_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_formal_accounting_materializer_v1 import (
    _refreeze as _refreeze_formal,
)
from tests.test_construction_k7_formal_accounting_materializer_v1 import (
    _synthetic_complete_closure,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _domain_id(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


@pytest.fixture(scope="module")
def synthetic_complete_case():
    semantic_closure = _synthetic_complete_closure()
    context = semantic_closure.context
    formal = materializer._materialize_verified_closure(  # noqa: SLF001
        semantic_closure
    )

    child_closure_id = _id("child-closure")
    child_verification_id = _id("child-verification")
    result_id = _id("multiround-result")
    closure_record = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE",
        record_id=_id("child-closure-record"),
        semantic_artifact_id=child_closure_id,
        artifact_document={
            "schema": "acfqp.v075_live_dynamic_child_closure.v2",
            "profile_key": dynamic_v2.PROFILE_KEY,
            "closure_id": child_closure_id,
            "status": verifier.SOURCE_CAUSE,
            "terminal_class": verifier.TERMINAL_CLASS,
            "existing_child_action_row_count": 10,
            "unresolved_child_action_row_count": 10,
            "maximum_new_child_action_rows": (
                dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS
            ),
            "discovery_intent_ids": [],
            "validation_template_ids": [],
            "discovery_intents": [],
            "validation_templates": [],
            "all_root_support_descriptors_examined": True,
            "complete_child_catalogues": True,
            "all_or_none_child_base_authorization": True,
            "official_execution_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        },
    )
    closure_verification_record = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        record_id=_id("child-verification-record"),
        semantic_artifact_id=child_verification_id,
        artifact_document={
            "verification_id": child_verification_id,
            "closure_id": child_closure_id,
            "status": verifier.SOURCE_CAUSE,
            "semantic_replay_complete": True,
            "discovery_intent_ids": [],
            "validation_template_ids": [],
        },
    )
    multiround_record = SimpleNamespace(
        role="MULTIROUND_RESULT",
        record_id=_id("multiround-record"),
        semantic_artifact_id=result_id,
        artifact_document={
            "result_id": result_id,
            "status": verifier.SOURCE_CAUSE,
            "child_closure_status": verifier.SOURCE_CAUSE,
            "child_closure_id": child_closure_id,
            "child_closure_verification_id": child_verification_id,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
        },
    )
    portable = SimpleNamespace(
        records=(
            closure_record,
            closure_verification_record,
            multiround_record,
        ),
        bundle_id=_id("portable-bundle"),
        occurrence_id=context.scientific_occurrence_id,
    )
    owned_wrapper_id = _id("owned-wrapper")
    transcript_id = _id("transcript")
    business = {
        "owned_partial_result_id": owned_wrapper_id,
        "portable_evidence_bundle_id": portable.bundle_id,
        "portable_evidence_bundle": {"synthetic_portable": True},
    }
    business_raw = canonical_json_bytes(business)
    business_id = _id("business-result")
    output_document = {
        "business_result_id": business_id,
        "business_result_sha256": hashlib.sha256(business_raw).hexdigest(),
        "business_result_byte_count": len(business_raw),
        "business_result": business,
    }
    output = SimpleNamespace(to_document=lambda: output_document)

    registry, stage, comparison, _actual = verifier._official_profiles()  # noqa: SLF001
    logical = SimpleNamespace(
        logical_occurrence_id=context.logical_occurrence_id,
        protocol_id=_id("protocol"),
        structural_id=_id("structural"),
        query_id=_id("query"),
        selected_plan_id=_id("selected-plan"),
        threshold_profile_id=_id("threshold"),
        initial_build_epoch_id=_id("build-epoch"),
        rebuild_policy_id=campaign_v1.RebuildPolicyV1().rebuild_policy_id,
    )
    attempt = SimpleNamespace(
        logical_occurrence_id=logical.logical_occurrence_id,
        route_attempt_id=context.route_attempt_id,
        build_epoch_id=logical.initial_build_epoch_id,
    )
    route_context = SimpleNamespace(
        logical_occurrence_id=logical.logical_occurrence_id,
        route_attempt_id=attempt.route_attempt_id,
        route_decision_context_id=_id("route-decision-context"),
        protocol_id=logical.protocol_id,
        structural_id=logical.structural_id,
        query_id=logical.query_id,
        selected_plan_id=logical.selected_plan_id,
        threshold_profile_id=logical.threshold_profile_id,
        build_epoch_id=attempt.build_epoch_id,
        counter_registry_id=registry.registry_id,
        comparison_profile_id=comparison.comparison_profile_id,
    )
    decision = SimpleNamespace(
        decision_point_id=context.decision_point_id,
        route_decision_context_id=route_context.route_decision_context_id,
        transaction_index=1,
    )
    transaction = SimpleNamespace(
        transaction_id=_id("transaction"),
        logical_occurrence_id=logical.logical_occurrence_id,
        route_attempt_id=attempt.route_attempt_id,
        decision_point_id=decision.decision_point_id,
        transaction_index=1,
        route_cap_profile_id=_id("route-cap-profile"),
    )
    profile = SimpleNamespace(
        counter_registry_id=registry.registry_id,
        stage_profile_id=stage.stage_profile_id,
        comparison_profile_id=comparison.comparison_profile_id,
        boundary_manifest_id=context.boundary_profile_id,
        execution_profile_id=context.execution_profile_id,
    )
    route = SimpleNamespace(
        profile=profile,
        logical_occurrence=logical,
        route_attempt=attempt,
        route_context=route_context,
        decision_point=decision,
        transaction=transaction,
        to_document=lambda: {"synthetic_route_replayed": True},
    )
    request_replay = SimpleNamespace(
        replay_id=context.portable_request_replay_id,
        request=SimpleNamespace(route_identity=route),
    )
    runtime = SimpleNamespace(
        envelope_id=context.production_runtime_envelope_id,
        binding=SimpleNamespace(),
    )
    result = SimpleNamespace(
        status=(
            multiround_v2.V075ObserverSignedMultiroundTerminalStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        ),
        child_closure_status=(
            dynamic_v2.V075LiveDynamicChildClosureStatusV2
            .CHILD_ACTION_ROW_CAP_EXCEEDED
        ),
        result_id=result_id,
        child_closure_id=child_closure_id,
        child_closure_verification_id=child_verification_id,
    )
    owned = SimpleNamespace(
        wrapper_id=owned_wrapper_id,
        transcript=SimpleNamespace(transcript_id=transcript_id),
        result=result,
    )
    occurrence_row = SimpleNamespace(
        authority_id=context.occurrence_authority_id,
        scientific_occurrence_id=context.scientific_occurrence_id,
        logical_occurrence_id=context.logical_occurrence_id,
        route_attempt_id=context.route_attempt_id,
        decision_point_id=context.decision_point_id,
        terminal_status=verifier.SOURCE_CAUSE,
        terminal_kind="COMPLETED",
        route_attempt_outcome="FAILURE",
        route_attempt_count=1,
        route_success_count=0,
        route_failure_count=1,
        owned_partial_result_id=owned_wrapper_id,
        partial_native_transcript_id=transcript_id,
        transcript_terminal_id=_id("transcript-terminal"),
        transcript_document_sha256=_id("transcript-document"),
        ordered_chain_node_ids=(_id("chain-node"),),
        terminal_closure_observation_id=context.terminal_closure_observation_id,
        production_runtime_envelope_id=context.production_runtime_envelope_id,
        portable_request_replay_id=context.portable_request_replay_id,
        runtime_business_result_id=business_id,
        runtime_business_result_sha256=hashlib.sha256(business_raw).hexdigest(),
        runtime_business_result_byte_count=len(business_raw),
    )
    cutoff_row = SimpleNamespace(
        authority_id=context.cutoff_authority_id,
        terminal_closure_observation_id=context.terminal_closure_observation_id,
    )
    occurrence = SimpleNamespace(
        bundle_id=context.occurrence_authority_bundle_id,
        occurrence_authority=occurrence_row,
        cutoff_authority=cutoff_row,
    )
    roots = {
        "runtime_envelope": runtime,
        "request_replay": request_replay,
        "owned_result": owned,
        "operational_output_bytes": b"synthetic-operational-output",
    }
    replay_inputs = {
        "replay_roots": roots,
        "occurrence_authority": occurrence,
    }

    cap = terminal.K7RootCapExhaustionEvidenceV1(
        terminal._CAP_EVIDENCE_ISSUER,  # noqa: SLF001
        occurrence.bundle_id,
        occurrence_row.authority_id,
        cutoff_row.authority_id,
        occurrence_row.production_runtime_envelope_id,
        occurrence_row.portable_request_replay_id,
        owned.wrapper_id,
        owned.transcript.transcript_id,
        occurrence_row.transcript_terminal_id,
        occurrence_row.transcript_document_sha256,
        len(occurrence_row.ordered_chain_node_ids),
        occurrence_row.terminal_closure_observation_id,
        occurrence_row.runtime_business_result_id,
        occurrence_row.runtime_business_result_sha256,
        occurrence_row.runtime_business_result_byte_count,
        portable.bundle_id,
        multiround_record.record_id,
        result.result_id,
        closure_record.record_id,
        result.child_closure_id,
        closure_verification_record.record_id,
        result.child_closure_verification_id,
        occurrence_row.logical_occurrence_id,
        logical.rebuild_policy_id,
        occurrence_row.route_attempt_id,
        occurrence_row.decision_point_id,
        transaction.transaction_id,
        transaction.transaction_index,
        transaction.route_cap_profile_id,
        terminal.K7_ROOT_CAP_SEMANTICS_PROFILE_ID_V1,
        verifier._terminal_derivation_registry_id(),  # noqa: SLF001
        10,
        10,
        dynamic_v2.MAXIMUM_NEW_CHILD_ACTION_ROWS,
    )
    terminal_authority = terminal.K7AttemptBudgetTerminalAuthorityV1(
        terminal._TERMINAL_AUTHORITY_ISSUER,  # noqa: SLF001
        cap,
        formal.bundle_id,
        semantic_closure.closure_id,
        semantic_closure.context.context_id,
        formal.actual_projection_proof.proof_id,
        formal.work_vector.work_vector_id,
        formal.comparison_vector.comparison_vector_id,
        tuple(row.record_id for row in formal.work_vector.records),
        1,
        0,
        1,
    )
    terminal_bundle = terminal.K7RootCapTerminalAccountingBundleV1(
        terminal._BUNDLE_ISSUER,  # noqa: SLF001
        formal,
        cap,
        terminal_authority,
    )
    return SimpleNamespace(
        semantic_closure=semantic_closure,
        formal=formal,
        terminal_bundle=terminal_bundle,
        replay_inputs=replay_inputs,
        occurrence=occurrence,
        output=output,
        portable=portable,
        route=route,
    )


@pytest.fixture
def synthetic_replay(monkeypatch, synthetic_complete_case):
    case = synthetic_complete_case
    calls: list[str] = []

    def replay_closure(*, raw: bytes, **_kwargs):
        assert raw == case.semantic_closure.canonical_bytes
        calls.append("closure")
        return case.semantic_closure

    def replay_occurrence(_claimed, **_kwargs):
        calls.append("occurrence")
        return case.occurrence

    def replay_output(**_kwargs):
        calls.append("output")
        return case.output

    def replay_portable(_raw):
        calls.append("portable")
        return case.portable

    monkeypatch.setattr(
        closure_v1,
        "verify_k7_semantic_evidence_closure_bytes_v1",
        replay_closure,
    )
    monkeypatch.setattr(
        occurrence_v2,
        "replay_k7_occurrence_cutoff_semantic_authorities_v2",
        replay_occurrence,
    )
    monkeypatch.setattr(
        worker_v1,
        "verify_v075_k7_broker_operational_output_bytes_v1",
        replay_output,
    )
    monkeypatch.setattr(
        portable_v2,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        replay_portable,
    )
    monkeypatch.setattr(
        occurrence_v2,
        "K7OccurrenceCutoffSemanticAuthorityBundleV2",
        SimpleNamespace,
    )
    monkeypatch.setattr(
        portable_v2,
        "V075PortableOccurrenceEvidenceBundleV2",
        SimpleNamespace,
    )
    monkeypatch.setattr(
        multiround_v2,
        "V075ObserverSignedMultiroundResultV2",
        SimpleNamespace,
    )
    monkeypatch.setattr(
        route_ipc_v1,
        "V075K7RootCapAccountedSealedRouteIdentityV1",
        SimpleNamespace,
    )
    return case, calls


def _rehash_terminal(
    document: dict[str, Any],
    *,
    align_formal_refs: bool = True,
) -> bytes:
    result = deepcopy(document)
    cap = result.get("root_cap_exhaustion_evidence")
    if type(cap) is dict and "root_cap_exhaustion_evidence_id" in cap:
        cap_payload = dict(cap)
        cap_payload.pop("root_cap_exhaustion_evidence_id")
        cap["root_cap_exhaustion_evidence_id"] = _domain_id(
            verifier.K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN,
            cap_payload,
        )
    terminal_document = result.get("attempt_budget_terminal_authority")
    if type(terminal_document) is dict:
        if type(cap) is dict:
            terminal_document["root_cap_exhaustion_evidence_id"] = cap.get(
                "root_cap_exhaustion_evidence_id"
            )
        formal = result.get("formal_accounting_materialization_bundle")
        if align_formal_refs and type(formal) is dict and "work_vector" in formal:
            terminal_document["formal_accounting_materialization_bundle_id"] = (
                formal["formal_accounting_materialization_bundle_id"]
            )
            terminal_document["formal_actual_projection_proof_id"] = formal[
                "actual_projection_proof"
            ]["formal_actual_projection_proof_id"]
            terminal_document["actual_work_vector_id"] = formal["work_vector"][
                "work_vector_id"
            ]
            terminal_document["actual_comparison_vector_id"] = formal[
                "comparison_vector"
            ]["comparison_vector_id"]
            terminal_document["counter_record_ids"] = formal["counter_record_ids"]
        terminal_payload = dict(terminal_document)
        terminal_payload.pop("attempt_budget_terminal_authority_id", None)
        terminal_document["attempt_budget_terminal_authority_id"] = _domain_id(
            verifier.K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN,
            terminal_payload,
        )
    bundle_payload = dict(result)
    bundle_payload.pop("root_cap_terminal_accounting_bundle_id", None)
    result["root_cap_terminal_accounting_bundle_id"] = _domain_id(
        verifier.K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
        bundle_payload,
    )
    return canonical_json_bytes(result)


def _inputs(case) -> dict[str, Any]:
    return {
        "semantic_closure_raw": case.semantic_closure.canonical_bytes,
        "formal_materialization_raw": case.formal.canonical_bytes,
        "terminal_accounting_bundle_raw": case.terminal_bundle.canonical_bytes,
        "closure_replay_inputs": case.replay_inputs,
    }


def test_independent_verifier_recomputes_complete_bundle_without_producer_calls(
    synthetic_replay,
    monkeypatch,
) -> None:
    case, calls = synthetic_replay

    def forbidden(*_args, **_kwargs):
        raise AssertionError("producer implementation was called")

    monkeypatch.setattr(
        materializer,
        "verify_k7_formal_accounting_materialization_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        terminal,
        "verify_k7_root_cap_terminal_accounting_bundle_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        terminal,
        "issue_k7_root_cap_terminal_accounting_bundle_v1",
        forbidden,
    )
    result = verifier.verify_k7_production_complete_bundle_independently_v1(
        **_inputs(case)
    )
    replayed = (
        verifier.verify_k7_production_complete_bundle_verification_bytes_v1(
            raw=result.canonical_bytes,
            **_inputs(case),
        )
    )
    document = replayed.to_document()

    assert calls == [
        "closure", "occurrence", "output", "portable",
        "closure", "occurrence", "output", "portable",
    ]
    assert replayed.verification_id == result.verification_id
    assert replayed.verified_work_vector.work_vector_id == case.formal.work_vector.work_vector_id
    assert replayed.verified_comparison_vector.comparison_vector_id == (
        case.formal.comparison_vector.comparison_vector_id
    )
    assert len(replayed.counter_record_ids) == 202
    assert len(replayed.verified_role_bindings) == 8
    assert replayed.verification_work_record.lane.value == "evaluation"
    assert replayed.verification_work_record.path == "evaluation.semantic_protocol_checks"
    assert document["all_182_operational_projection_terms_recomputed"] is True
    assert document["source_cap_and_specific_cause_recomputed"] is True
    assert document["terminal_mapping_recomputed"] is True
    assert document["producer_materializer_verifier_called"] is False
    assert document["producer_terminal_verifier_called"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False


@pytest.mark.parametrize(
    "attack",
    (
        "record",
        "projection",
        "actual",
        "cap",
        "cause",
        "terminal",
        "cross_role",
        "id_only",
        "hash_only",
    ),
)
def test_rehashed_record_projection_terminal_cap_and_role_attacks_fail_closed(
    synthetic_replay,
    attack: str,
) -> None:
    case, _calls = synthetic_replay
    formal_document = loads_canonical_json(case.formal.canonical_bytes)
    terminal_document = loads_canonical_json(case.terminal_bundle.canonical_bytes)
    assert type(formal_document) is dict and type(terminal_document) is dict
    native_zero_paths = {
        row.path
        for row in case.semantic_closure.resolutions
        if row.kind is closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
    }
    if attack in {"record", "projection", "actual"}:
        if attack == "record":
            formal_document["work_vector"]["records"][0]["value"] += 1
        elif attack == "projection":
            proof = formal_document["actual_projection_proof"]
            proof["projected_source_paths"][0] = next(
                row.path
                for row in verifier.registry_v6.official_counter_registry_v6().leaves
                if row.required and row.lane.value != "operational"
            )
        else:
            formal_document["comparison_vector"]["values"][0]["value"] += 1
        formal_raw = _refreeze_formal(
            formal_document,
            native_zero_paths=native_zero_paths,
        )
        attacked_formal = loads_canonical_json(formal_raw)
        terminal_document["formal_accounting_materialization_bundle"] = attacked_formal
        terminal_raw = _rehash_terminal(terminal_document)
    else:
        formal_raw = case.formal.canonical_bytes
        if attack == "cap":
            terminal_document["root_cap_exhaustion_evidence"][
                "maximum_new_child_action_rows"
            ] = 10_000
        elif attack == "cause":
            terminal_document["specific_cause"] = "FORGED_CAUSE"
            terminal_document["root_cap_exhaustion_evidence"][
                "source_cause"
            ] = "FORGED_CAUSE"
            terminal_document["attempt_budget_terminal_authority"][
                "specific_cause"
            ] = "FORGED_CAUSE"
        elif attack == "terminal":
            terminal_document["terminal_class"] = "INFEASIBILITY_CERTIFICATE"
            terminal_document["attempt_budget_terminal_authority"][
                "terminal_class"
            ] = "INFEASIBILITY_CERTIFICATE"
        elif attack == "cross_role":
            authority = terminal_document["attempt_budget_terminal_authority"]
            authority["actual_work_vector_id"] = authority[
                "actual_comparison_vector_id"
            ]
        elif attack == "id_only":
            embedded = terminal_document["formal_accounting_materialization_bundle"]
            terminal_document["formal_accounting_materialization_bundle"] = {
                "formal_accounting_materialization_bundle_id": embedded[
                    "formal_accounting_materialization_bundle_id"
                ]
            }
        else:
            cap = terminal_document["root_cap_exhaustion_evidence"]
            terminal_document["root_cap_exhaustion_evidence"] = {
                "root_cap_exhaustion_evidence_id": cap[
                    "root_cap_exhaustion_evidence_id"
                ]
            }
        terminal_raw = _rehash_terminal(
            terminal_document,
            align_formal_refs=attack != "cross_role",
        )

    with pytest.raises(
        verifier.ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error,
    ):
        verifier.verify_k7_production_complete_bundle_independently_v1(
            semantic_closure_raw=case.semantic_closure.canonical_bytes,
            formal_materialization_raw=formal_raw,
            terminal_accounting_bundle_raw=terminal_raw,
            closure_replay_inputs=case.replay_inputs,
        )


def test_rehashed_self_reported_verification_result_is_rejected(
    synthetic_replay,
) -> None:
    case, _calls = synthetic_replay
    result = verifier.verify_k7_production_complete_bundle_independently_v1(
        **_inputs(case)
    )
    document = loads_canonical_json(result.canonical_bytes)
    assert type(document) is dict
    attestation = document["typed_verification_attestation"]
    attestation["verification_result"] = "SELF_REPORTED_PASS"
    attestation_payload = dict(attestation)
    attestation_payload.pop("typed_verification_attestation_id")
    attestation["typed_verification_attestation_id"] = content_id(
        TYPED_VERIFICATION_ATTESTATION_DOMAIN,
        attestation_payload,
    )
    payload = dict(document)
    payload.pop("production_complete_bundle_verification_id")
    document["production_complete_bundle_verification_id"] = _domain_id(
        verifier.K7_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
        payload,
    )
    with pytest.raises(
        verifier.ConstructionK7ProductionCompleteBundleIndependentVerifierV1Error,
        match="differs from fresh replay",
    ):
        verifier.verify_k7_production_complete_bundle_verification_bytes_v1(
            raw=canonical_json_bytes(document),
            **_inputs(case),
        )
