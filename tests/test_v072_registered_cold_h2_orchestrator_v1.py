from __future__ import annotations

import hashlib
import inspect

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_closure_v1 as cold
from acfqp import v072_heldout_public_graph_adapter_v1 as adapter_module
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as orchestrator


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _synthetic_root_row(
    *,
    adapter: adapter_module.HeldoutPublicGraphColdClosureAdapterV1,
) -> cold.ColdRowEvidenceV1:
    public_child = observer.HeldoutSymbolicGraphStateV2(
        adapter.context.root_ranks,
        False,
    )
    child = adapter.adapt_public_state_v1(public_child, 1)
    discovery = cold.ColdOutcomeDescriptorV1(
        _id("registered-cold-orchestrator-discovery-descriptor"),
        failure=False,
        terminal=False,
        successor_state=child,
        document={
            "kind": "registration-disjoint-active-child",
            "state_id": child.semantic_state_id,
        },
    )
    validation_novel = cold.ColdOutcomeDescriptorV1(
        _id("registered-cold-orchestrator-validation-descriptor"),
        failure=True,
        terminal=True,
        successor_state=None,
        document={"kind": "validation-only-terminal"},
    )
    return cold.ColdRowEvidenceV1(
        adapter.context_id,
        adapter.root_state,
        2,
        adapter.root_actions[0],
        (discovery,),
        (validation_novel,),
        _id("registered-cold-orchestrator-support-epoch"),
        _id("registered-cold-orchestrator-confidence"),
        _id("registered-cold-orchestrator-row-replay"),
        _id("registered-cold-orchestrator-physical-evidence"),
        cold.ColdRowNativeWorkV1(),
    )


def test_production_signature_accepts_no_injected_evidence() -> None:
    signature = inspect.signature(
        orchestrator.build_registered_cold_h2_model_epoch_v1
    )
    assert tuple(signature.parameters) == (
        "authority_chain",
        "anchor",
        "occurrence_plan",
        "context",
    )
    assert all(
        item.kind is inspect.Parameter.KEYWORD_ONLY
        for item in signature.parameters.values()
    )
    assert {
        "observations",
        "transcript",
        "law",
        "seed",
        "counts",
        "support",
        "rows",
        "projections",
        "model",
        "callback",
    }.isdisjoint(signature.parameters)


def test_invalid_authority_fails_with_zero_target_access() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    template = next(
        item
        for item in consumer.registered_occurrence_templates_v1()
        if item.context_id == context.context_id
        and item.arm == "NO_PRIOR"
    )
    plan = consumer.RegisteredOccurrenceExecutionPlanV1(
        _id("nonauthorizing-cold-orchestrator-chain"),
        template,
    )
    with pytest.raises(
        orchestrator.RegisteredColdH2OrchestratorLockedV1
    ) as caught:
        orchestrator.build_registered_cold_h2_model_epoch_v1(
            authority_chain=object(),
            anchor=object(),
            occurrence_plan=plan,
            context=context,
        )
    assert caught.value.access_audit == orchestrator.ZERO_ACCESS_AUDIT
    assert caught.value.access_audit.target_access_started is False


def test_public_action_order_is_complete_and_content_deterministic() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    adapter = adapter_module.registered_heldout_public_graph_adapter_v1(
        context
    )
    actions = orchestrator._ordered_public_actions_v1(
        context,
        adapter.public_root_catalogue,
    )
    assert set(actions) == set(adapter.public_root_catalogue.actions)
    row_ids = tuple(
        observer.observation_row_binding_v2(
            context,
            adapter.public_root_catalogue,
            action,
        ).row_binding_id
        for action in actions
    )
    assert row_ids == tuple(sorted(row_ids))


def test_child_catalogues_use_discovery_support_not_validation_novel() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    adapter = adapter_module.registered_heldout_public_graph_adapter_v1(
        context
    )
    row = _synthetic_root_row(adapter=adapter)
    catalogues = (
        orchestrator._public_child_catalogues_from_root_evidence_v1(
            adapter=adapter,
            root_row_evidence=(row,),
        )
    )
    assert len(catalogues) == 1
    assert catalogues[0].remaining_horizon == 1
    assert catalogues[0].state.state_id == (
        row.discovery_support[0].successor_state.semantic_state_id
    )
    assert catalogues[0].actions


def test_duplicate_discovery_child_is_deduplicated_by_public_identity() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    adapter = adapter_module.registered_heldout_public_graph_adapter_v1(
        context
    )
    first = _synthetic_root_row(adapter=adapter)
    second = cold.ColdRowEvidenceV1(
        first.context_id,
        first.state,
        first.remaining_horizon,
        adapter.root_actions[1],
        first.discovery_support,
        (),
        _id("registered-cold-orchestrator-support-epoch-2"),
        _id("registered-cold-orchestrator-confidence-2"),
        _id("registered-cold-orchestrator-row-replay-2"),
        _id("registered-cold-orchestrator-physical-evidence-2"),
        cold.ColdRowNativeWorkV1(),
    )
    catalogues = (
        orchestrator._public_child_catalogues_from_root_evidence_v1(
            adapter=adapter,
            root_row_evidence=(first, second),
        )
    )
    assert len(catalogues) == 1


def test_access_audit_separates_sample_evidence_from_replay_work() -> None:
    with pytest.raises(
        orchestrator.V072RegisteredColdH2OrchestratorInvariantViolation,
        match="sample evidence and observer replay work",
    ):
        orchestrator.RegisteredColdH2OrchestratorAccessAuditV1(
            producer_draw_calls=1,
            replay_draw_calls=2,
            unique_online_sample_evidence_draws=1,
            total_observer_draw_calls=2,
        )
    valid = orchestrator.RegisteredColdH2OrchestratorAccessAuditV1(
        producer_draw_calls=1,
        replay_draw_calls=2,
        unique_online_sample_evidence_draws=1,
        total_observer_draw_calls=3,
    )
    assert valid.unique_online_sample_evidence_draws == 1
    assert valid.total_observer_draw_calls == 3


def test_registered_orchestrator_declares_exact_authority_only() -> None:
    assert orchestrator.REGISTERED_COLD_ORCHESTRATOR_ENABLED is True
    assert (
        orchestrator.REGISTERED_COLD_ORCHESTRATOR_STATUS
        == "ENABLED_ONLY_BY_EXACT_REMOTE_MAIN_AUTHORITY_CHAIN"
    )
    source = inspect.getsource(
        orchestrator.build_registered_cold_h2_model_epoch_v1
    )
    assert "source" not in source.lower()
    assert "callback" not in source.lower()
