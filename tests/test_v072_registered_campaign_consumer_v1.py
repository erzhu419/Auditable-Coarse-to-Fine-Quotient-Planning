from __future__ import annotations

import ast
from dataclasses import fields, replace
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_cold_h2_model_builders_v1 as builders
from acfqp import v072_confidence_row_projection_v1 as projection
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_incremental_materializer_v1 as incremental
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_matched_direct_ground_baseline_v1 as direct
from acfqp import (
    v072_remote_main_anchor_independent_verifier_v1
    as anchor_independent,
)
from acfqp import (
    v072_registered_adaptive_quotient_runtime_v1 as adaptive_runtime,
)
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import (
    v072_registered_campaign_reconciliation_independent_verifier_v1
    as reconciliation_independent,
)
from acfqp import (
    v072_registered_campaign_reconciliation_v1 as reconciliation,
)
from acfqp import (
    v072_registered_complete_bundle_endpoint_verifier_v1 as endpoint,
)
from acfqp import (
    v072_registered_matched_direct_runtime_v1 as direct_runtime,
)
from acfqp import (
    v072_registered_operational_terminal_authority_v1
    as terminal_authority,
)
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _unsafe_exact(cls: type[Any], **values: Any) -> Any:
    result = object.__new__(cls)
    names = {
        item.name for item in fields(cls)
    } if hasattr(cls, "__dataclass_fields__") else set()
    for name in names | set(values):
        object.__setattr__(result, name, values.get(name))
    return result


def _mechanics_authority_chain() -> consumer.RegisteredCampaignAuthorityChainV1:
    return _unsafe_exact(
        consumer.RegisteredCampaignAuthorityChainV1,
        manifest=SimpleNamespace(),
        final_preregistration=SimpleNamespace(),
        remote_main_anchor=SimpleNamespace(anchor_id=_id("mechanics-anchor")),
        remote_main_anchor_attestation=SimpleNamespace(),
        repository_root="/registered/mechanics",
        _chain_id=_id("mechanics-chain"),
    )


def _placeholder() -> observer.TargetExecutionAnchorPlaceholderV1:
    return observer.bind_target_execution_anchor_placeholder_v1(
        prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
        remote_main_commit_sha="1" * 40,
        remote_main_containment_attestation_id=_id(
            "registered-consumer-placeholder"
        ),
    )


def _local_only_anchor_claim(
) -> final_authority.V072RemoteMainAnchorClaimV1:
    return final_authority.V072RemoteMainAnchorClaimV1(
        (
            final_authority.RemoteMainAnchorVerificationScopeV1
            .DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING
        ),
        manifest.REPOSITORY_URL,
        "main",
        "1" * 40,
        "2" * 40,
        "3" * 40,
        "4" * 40,
        "5" * 40,
        "6" * 40,
        _id("unminted-source-reconstruction-recipe"),
        _id("unminted-final-manifest"),
        _id("unminted-final-preregistration"),
    )


def test_readiness_freezes_exact_context_major_five_arm_denominator() -> None:
    readiness = (
        consumer.inspect_registered_campaign_consumer_readiness_v1()
    )
    contexts = prereg.registered_heldout_public_contexts_v2()
    assert len(contexts) == 3
    assert len(readiness.occurrence_templates) == 15
    assert tuple(
        (item.context_id, item.arm)
        for item in readiness.occurrence_templates
    ) == tuple(
        (context.context_id, arm)
        for context in contexts
        for arm in prereg.ARM_ORDER
    )
    assert tuple(
        item.occurrence_ordinal
        for item in readiness.occurrence_templates
    ) == tuple(range(15))
    assert all(
        item.to_document()["replacement_allowed"] is False
        and item.to_document()["campaign_early_stop_allowed"] is False
        and item.to_document()["crn_pairing_allowed"] is True
        and item.to_document()["crn_draw_discount"] == 0
        for item in readiness.occurrence_templates
    )
    assert all(
        item.to_document()["round_two_requires_fresh_frontier"]
        == (item.arm != "MATCHED_DIRECT_GROUND")
        for item in readiness.occurrence_templates
    )
    expected_semantics = {
        "SOURCE_CONSENSUS_PRIOR":
            "SOURCE_ARCHIVE_FORWARD_MIDRANK",
        "NO_PRIOR": "NO_PRIOR",
        "WRONG_CONSENSUS_PRIOR":
            "SOURCE_ARCHIVE_REVERSED_MIDRANK",
        "OOD_ABSTENTION":
            "OOD_TYPED_SCHEMA_ABSTENTION_NEUTRAL",
        "MATCHED_DIRECT_GROUND": "MATCHED_DIRECT_NO_SELECTOR",
    }
    assert all(
        item.proposal_semantics.value == expected_semantics[item.arm]
        and item.to_document()["source_quantities_in_confidence_or_certificate"]
        == 0
        and tuple(item.to_document()["crn_pairing_key_fields"])
        == consumer.CRN_PAIRING_KEY_FIELDS
        for item in readiness.occurrence_templates
    )
    assert (
        readiness.to_document()["logical_occurrence_denominator"] == 15
    )
    assert readiness.target_execution_allowed is False
    assert readiness.registered_observations_generated == 0
    assert readiness.access_audit == consumer.ZERO_ACCESS_AUDIT
    assert readiness.access_audit.target_access_started is False
    assert readiness.sample_efficiency_gate_status == "NOT_RUN"


def test_production_code_capabilities_are_installed_but_not_authorizing() -> None:
    readiness = (
        consumer.inspect_registered_campaign_consumer_readiness_v1()
    )
    assert consumer.PRODUCTION_CAPABILITY_BLOCKERS == ()
    assert readiness.capability_blockers == ()
    assert consumer.REGISTERED_EXECUTION_STATUS == (
        "PRODUCTION_EXECUTOR_INSTALLED_AUTHORITY_CHAIN_REQUIRED"
    )
    # Installed code is deliberately not runtime authority: readiness remains
    # zero-access and cannot execute without the exact chain/source artifacts.
    assert readiness.target_execution_allowed is False
    assert readiness.final_manifest_available is False
    assert readiness.final_preregistration_available is False
    assert readiness.verified_remote_main_anchor_available is False
    assert readiness.access_audit == consumer.ZERO_ACCESS_AUDIT


def test_registered_consumer_imports_no_development_transition_authority() -> None:
    tree = ast.parse(inspect.getsource(consumer))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert all(
        "development_synthetic_transition" not in item
        and "development_complete_adaptive" not in item
        and "five_arm_confirmatory_campaign" not in item
        for item in imported
    )
    roles = {
        item.component_role: item.repository_relative_path
        for item in manifest.COMPONENT_ROLE_SPECS
    }
    assert roles["five-arm confirmatory campaign runner"] == (
        "src/acfqp/v072_registered_campaign_consumer_v1.py"
    )
    assert roles["standalone complete-bundle and endpoint verifier"] == (
        "src/acfqp/"
        "v072_registered_complete_bundle_endpoint_verifier_v1.py"
    )


def test_registered_entrypoints_accept_no_observer_law_seed_or_status() -> None:
    signature = inspect.signature(
        consumer.run_registered_v072_campaign_v1
    )
    assert tuple(signature.parameters) == ("authority_chain",)
    assert (
        signature.parameters["authority_chain"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    endpoint_signature = inspect.signature(
        endpoint.verify_registered_v072_complete_bundle_v1
    )
    assert tuple(endpoint_signature.parameters) == ("bundle",)
    assert (
        endpoint_signature.parameters["bundle"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )
    forbidden = {
        "observer",
        "law",
        "seed",
        "splitmix",
        "draws",
        "endpoint",
        "status",
        "terminal",
        "counts",
    }
    assert forbidden.isdisjoint(signature.parameters)
    assert forbidden.isdisjoint(endpoint_signature.parameters)


def test_observer_is_wired_only_to_the_exact_minted_anchor_type() -> None:
    signature = inspect.signature(
        observer.open_heldout_target_transition_stream_v2
    )
    assert signature.parameters["anchor"].annotation == (
        "final_authority.V072RemoteMainAnchorV1"
    )
    assert all(
        blocker.stage is not consumer.RegisteredStageV1.OBSERVER
        for blocker in consumer.PRODUCTION_CAPABILITY_BLOCKERS
    )
    for nonauthority in (
        None,
        object(),
        _placeholder(),
        _local_only_anchor_claim(),
    ):
        with pytest.raises(
            observer.HeldoutGraphTransitionObserverV2InvariantViolation
        ):
            observer._require_execution_anchor(nonauthority)


def _patch_every_postgate_access(
    monkeypatch: pytest.MonkeyPatch,
) -> list[str]:
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        calls.append("POSTGATE_ACCESS")
        raise AssertionError("post-gate target access occurred")

    for module, name in (
        (consumer, "_load_and_replay_source_recipe_v1"),
        (consumer, "_execute_registered_occurrences_v1"),
        (observer, "_environment_law"),
        (observer, "_stream_seed"),
        (observer, "_splitmix64"),
        (observer, "open_heldout_target_transition_stream_v2"),
        (projection, "project_registered_target_confidence_row_v1"),
        (builders, "build_registered_target_cold_h2_models_v1"),
        (incremental, "run_registered_v072_incremental_materializer_v1"),
        (direct, "run_registered_matched_direct_ground_baseline_v1"),
        (evaluator, "evaluate_registered_independent_exact_ground_v1"),
        (reconciliation, "reconcile_registered_v072_campaign_v1"),
        (
            reconciliation_independent,
            "verify_registered_v072_campaign_reconciliation_independently_v1",
        ),
        (endpoint, "mint_registered_v072_complete_bundle_v1"),
        (endpoint, "verify_registered_v072_complete_bundle_v1"),
        (
            anchor_independent,
            "verify_remote_main_anchor_claim_independently_v1",
        ),
    ):
        monkeypatch.setattr(module, name, forbidden)
    return calls


@pytest.mark.parametrize(
    "authority_claim",
    (
        None,
        object(),
        prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
        _local_only_anchor_claim(),
    ),
)
def test_foreign_draft_and_null_claims_fail_before_all_target_access(
    authority_claim: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_every_postgate_access(monkeypatch)
    with pytest.raises(
        consumer.RegisteredCampaignAuthorityGateLockedV1
    ) as captured:
        consumer.run_registered_v072_campaign_v1(
            authority_chain=authority_claim
        )
    assert captured.value.access_audit == consumer.ZERO_ACCESS_AUDIT
    assert captured.value.access_audit.target_access_started is False
    assert calls == []
    assert consumer.REGISTERED_OBSERVATIONS_GENERATED == 0


def test_chain_bound_source_replay_precedes_all_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _mechanics_authority_chain()
    calls: list[str] = []

    def verify_chain(
        value: consumer.RegisteredCampaignAuthorityChainV1,
    ) -> tuple[str, str, str, str, str]:
        assert value is chain
        calls.append("VERIFY_CHAIN")
        return (
            _id("source-recipe"),
            _id("manifest"),
            _id("final-preregistration"),
            chain.remote_main_anchor.anchor_id,
            _id("anchor-attestation"),
        )

    def fail_source(
        value: consumer.RegisteredCampaignAuthorityChainV1,
    ) -> None:
        assert value is chain
        calls.append("SOURCE_REPLAY")
        raise consumer.RegisteredCampaignAuthorityGateLockedV1(
            "source replay unavailable",
            access_audit=consumer.RegisteredAccessAuditV1(
                authority_chain_verifications=1,
            ),
        )

    def forbidden_target(**_kwargs: Any) -> None:
        calls.append("TARGET_EXECUTION")
        raise AssertionError("target execution preceded source replay")

    monkeypatch.setattr(
        consumer,
        "_verify_exact_authority_chain_v1",
        verify_chain,
    )
    monkeypatch.setattr(
        consumer,
        "_load_and_replay_source_recipe_v1",
        fail_source,
    )
    monkeypatch.setattr(
        consumer,
        "_execute_registered_occurrences_v1",
        forbidden_target,
    )
    with pytest.raises(consumer.RegisteredCampaignAuthorityGateLockedV1):
        consumer.run_registered_v072_campaign_v1(
            authority_chain=chain,
        )
    assert calls == ["VERIFY_CHAIN", "SOURCE_REPLAY"]


def test_chain_bound_source_replay_is_reused_without_second_reconstruction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe_id = _id("already-paid-source-recipe")
    recipe = SimpleNamespace(recipe_id=recipe_id)
    already_paid = SimpleNamespace(recipe_id=recipe_id)
    chain = SimpleNamespace(
        repository_root=str(tmp_path.resolve()),
        manifest=SimpleNamespace(
            global_bindings={
                "source_reconstruction_recipe_id": recipe_id,
            },
            source_reconstruction_replay=already_paid,
        ),
    )
    calls: list[str] = []

    def load_recipe(path: Path) -> Any:
        assert path == (
            tmp_path.resolve()
            / manifest.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        )
        calls.append("LOAD_RECIPE")
        return recipe

    def forbidden_reconstruction(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("source reconstruction was charged twice")

    monkeypatch.setattr(
        source_recipe,
        "load_source_reconstruction_recipe_v1",
        load_recipe,
    )
    monkeypatch.setattr(
        source_recipe,
        "replay_source_reconstruction_recipe_v1",
        forbidden_reconstruction,
    )

    replay = consumer._load_and_replay_source_recipe_v1(chain)
    assert replay is already_paid
    assert calls == ["LOAD_RECIPE"]


def test_exact_context_major_dispatch_and_certified_only_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _mechanics_authority_chain()
    plan = consumer._execution_plan_v1(chain)
    route_calls: list[tuple[str, int, str, str]] = []
    direct_plan_ids: dict[int, Any] = {}
    terminal_calls: list[tuple[int, Any]] = []
    evaluator_calls: list[int] = []
    certified_ordinals = {0, 4}

    def run_adaptive(**kwargs: Any) -> Any:
        occurrence = kwargs["occurrence_plan"]
        context = kwargs["context"]
        ordinal = occurrence.template.occurrence_ordinal
        route_calls.append(
            ("ADAPTIVE", ordinal, context.context_id, occurrence.template.arm)
        )
        execution = SimpleNamespace(
            status=(
                adaptive_runtime.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
                if ordinal in certified_ordinals
                else (
                    adaptive_runtime.RegisteredAdaptiveOccurrenceStatusV1
                    .NO_SOUND_COVER
                )
            ),
        )
        return _unsafe_exact(
            adaptive_runtime.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
            execution=execution,
            independent_verification=SimpleNamespace(),
            _verified_result_id=_id(f"adaptive-route:{ordinal}"),
        )

    def adapt_direct_plan(**kwargs: Any) -> Any:
        context = kwargs["context"]
        ordinal = next(
            item.template.occurrence_ordinal
            for item in plan.occurrences
            if item.template.context_id == context.context_id
            and item.template.arm == "MATCHED_DIRECT_GROUND"
        )
        adapted = SimpleNamespace(
            source_occurrence_id=plan.occurrences[ordinal].occurrence_id,
            occurrence_ordinal=ordinal,
        )
        direct_plan_ids[ordinal] = adapted
        return adapted

    def run_direct(**kwargs: Any) -> Any:
        adapted = kwargs["occurrence_plan"]
        context = kwargs["context"]
        ordinal = adapted.occurrence_ordinal
        route_calls.append(
            ("DIRECT", ordinal, context.context_id, "MATCHED_DIRECT_GROUND")
        )
        return _unsafe_exact(
            direct_runtime.RegisteredMatchedDirectOccurrenceResultV1,
            terminal_class=(
                direct_runtime.RegisteredMatchedDirectTerminalClassV1
                .PLAN_CERTIFICATE
                if ordinal in certified_ordinals
                else (
                    direct_runtime.RegisteredMatchedDirectTerminalClassV1
                    .ATTEMPT_CLOSURE_NONCERTIFICATE
                )
            ),
            _result_id=_id(f"direct-route:{ordinal}"),
        )

    def derive_terminal(**kwargs: Any) -> Any:
        occurrence_plan = kwargs["occurrence_plan"]
        ordinal = (
            occurrence_plan.occurrence_ordinal
            if hasattr(occurrence_plan, "occurrence_ordinal")
            else occurrence_plan.template.occurrence_ordinal
        )
        terminal_calls.append((ordinal, occurrence_plan))
        return SimpleNamespace(
            evaluator_bundle=SimpleNamespace(
                operational_terminal=SimpleNamespace(ordinal=ordinal),
                selected_policy=SimpleNamespace(ordinal=ordinal),
            ),
        )

    def evaluate(**kwargs: Any) -> Any:
        ordinal = kwargs["operational_terminal"].ordinal
        evaluator_calls.append(ordinal)
        assert kwargs["selected_policy"].ordinal == ordinal
        return SimpleNamespace(certificate_metrics_pass=True)

    monkeypatch.setattr(
        adaptive_runtime,
        "run_registered_adaptive_quotient_occurrence_v1",
        run_adaptive,
    )
    monkeypatch.setattr(
        direct_runtime,
        "registered_matched_direct_occurrence_plan_v1",
        adapt_direct_plan,
    )
    monkeypatch.setattr(
        direct_runtime,
        "run_registered_matched_direct_occurrence_v1",
        run_direct,
    )
    monkeypatch.setattr(
        terminal_authority,
        "derive_registered_operational_terminal_authority_v1",
        derive_terminal,
    )
    monkeypatch.setattr(
        evaluator,
        "evaluate_registered_independent_exact_ground_v1",
        evaluate,
    )

    routes, terminals, evaluations = (
        consumer._execute_registered_occurrences_v1(
            authority_chain=chain,
            execution_plan=plan,
        )
    )
    expected = tuple(
        (
            (
                "DIRECT"
                if item.template.route_kind
                is consumer.RegisteredRouteKindV1.MATCHED_DIRECT_GROUND
                else "ADAPTIVE"
            ),
            item.template.occurrence_ordinal,
            item.template.context_id,
            item.template.arm,
        )
        for item in plan.occurrences
    )
    assert tuple(route_calls) == expected
    assert len(routes) == len(terminals) == len(evaluations) == 15
    assert {
        index for index, value in enumerate(terminals) if value is not None
    } == certified_ordinals
    assert {
        index for index, value in enumerate(evaluations) if value is not None
    } == certified_ordinals
    assert tuple(evaluator_calls) == (0, 4)
    assert terminal_calls[0][1] is plan.occurrences[0]
    assert terminal_calls[1][1] is direct_plan_ids[4]
    assert all(
        terminals[index] is None and evaluations[index] is None
        for index in set(range(15)) - certified_ordinals
    )


def test_production_executor_reconciles_then_verifies_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chain = _mechanics_authority_chain()
    calls: list[str] = []
    source_replay = SimpleNamespace(recipe_id=_id("source-replay"))
    routes = tuple(SimpleNamespace(index=index) for index in range(15))
    terminals = tuple(None for _index in range(15))
    evaluations = tuple(None for _index in range(15))
    reconciled = SimpleNamespace(reconciliation_id=_id("reconciliation"))
    reconciliation_attestation = SimpleNamespace(
        verification_id=_id("reconciliation-attestation"),
    )

    def verify_chain(value: Any) -> tuple[str, str, str, str, str]:
        assert value is chain
        calls.append("VERIFY_CHAIN")
        return (
            source_replay.recipe_id,
            _id("manifest"),
            _id("final-preregistration"),
            chain.remote_main_anchor.anchor_id,
            _id("anchor-attestation"),
        )

    def load_source(value: Any) -> Any:
        assert value is chain
        calls.append("SOURCE_REPLAY")
        return source_replay

    def execute(**kwargs: Any) -> tuple[tuple[Any, ...], ...]:
        assert kwargs["authority_chain"] is chain
        assert tuple(
            item.template.occurrence_ordinal
            for item in kwargs["execution_plan"].occurrences
        ) == tuple(range(15))
        calls.append("EXECUTE_15")
        return routes, terminals, evaluations

    def reconcile(**kwargs: Any) -> Any:
        assert kwargs["route_results"] is routes
        assert kwargs["operational_terminal_authorities"] is terminals
        assert kwargs["exact_evaluations"] is evaluations
        assert kwargs["source_reconstruction_replay"] is source_replay
        calls.append("RECONCILE")
        return reconciled

    def verify_reconciliation(**kwargs: Any) -> Any:
        assert kwargs["claimed"] is reconciled
        calls.append("VERIFY_RECONCILIATION")
        return reconciliation_attestation

    def mint_bundle(**kwargs: Any) -> Any:
        assert kwargs["reconciliation"] is reconciled
        assert (
            kwargs["reconciliation_attestation"]
            is reconciliation_attestation
        )
        calls.append("MINT_BUNDLE")
        return _unsafe_exact(
            endpoint.RegisteredCampaignCompleteBundleV1,
            execution_plan=kwargs["execution_plan"],
            _bundle_id=_id("complete-bundle"),
        )

    def verify_endpoint(*, bundle: Any) -> Any:
        calls.append("VERIFY_ENDPOINT")
        return _unsafe_exact(
            endpoint.RegisteredCompleteBundleEndpointVerificationV1,
            bundle_id=bundle.bundle_id,
            execution_plan_id=bundle.execution_plan.plan_id,
            logical_occurrence_denominator=15,
            registered_v072_endpoints_pass=True,
            _verification_id=_id("endpoint-verification"),
        )

    def derive_audit(**kwargs: Any) -> consumer.RegisteredAccessAuditV1:
        assert kwargs["route_results"] is routes
        assert kwargs["exact_evaluations"] is evaluations
        assert kwargs["endpoint_verification_calls"] == 1
        calls.append("DERIVE_AUDIT")
        return consumer.RegisteredAccessAuditV1(
            adaptive_route_calls=12,
            matched_direct_calls=3,
            reconciliation_calls=1,
            endpoint_verification_calls=1,
        )

    monkeypatch.setattr(
        consumer,
        "_verify_exact_authority_chain_v1",
        verify_chain,
    )
    monkeypatch.setattr(
        consumer,
        "_load_and_replay_source_recipe_v1",
        load_source,
    )
    monkeypatch.setattr(
        consumer,
        "_execute_registered_occurrences_v1",
        execute,
    )
    monkeypatch.setattr(
        reconciliation,
        "reconcile_registered_v072_campaign_v1",
        reconcile,
    )
    monkeypatch.setattr(
        reconciliation_independent,
        "verify_registered_v072_campaign_reconciliation_independently_v1",
        verify_reconciliation,
    )
    monkeypatch.setattr(
        endpoint,
        "mint_registered_v072_complete_bundle_v1",
        mint_bundle,
    )
    monkeypatch.setattr(
        endpoint,
        "verify_registered_v072_complete_bundle_v1",
        verify_endpoint,
    )
    monkeypatch.setattr(
        consumer,
        "_derive_execution_access_audit_v1",
        derive_audit,
    )

    result = consumer.run_registered_v072_campaign_v1(
        authority_chain=chain,
    )
    assert type(result) is consumer.RegisteredCampaignExecutionResultV1
    assert calls == [
        "VERIFY_CHAIN",
        "SOURCE_REPLAY",
        "EXECUTE_15",
        "RECONCILE",
        "VERIFY_RECONCILIATION",
        "MINT_BUNDLE",
        "VERIFY_ENDPOINT",
        "DERIVE_AUDIT",
    ]
    assert result.endpoint_verification.registered_v072_endpoints_pass is True


def test_placeholder_and_forged_exact_wrapper_fail_before_target_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_every_postgate_access(monkeypatch)
    forged = object.__new__(
        consumer.RegisteredCampaignAuthorityChainV1
    )
    object.__setattr__(forged, "manifest", object())
    object.__setattr__(
        forged,
        "final_preregistration",
        prereg.freeze_transfer_guided_acquisition_preregistration_v1(),
    )
    object.__setattr__(forged, "remote_main_anchor", _placeholder())
    object.__setattr__(
        forged,
        "remote_main_anchor_attestation",
        object(),
    )
    object.__setattr__(
        forged,
        "repository_root",
        str(Path(__file__).resolve().parents[1]),
    )
    with pytest.raises(
        consumer.RegisteredCampaignAuthorityGateLockedV1
    ) as captured:
        consumer.run_registered_v072_campaign_v1(
            authority_chain=forged
        )
    assert captured.value.access_audit.target_access_started is False
    assert calls == []


def test_sequence_reorder_and_replacement_attacks_fail_closed() -> None:
    readiness = (
        consumer.inspect_registered_campaign_consumer_readiness_v1()
    )
    with pytest.raises(
        consumer.V072RegisteredCampaignConsumerInvariantViolation
    ):
        replace(
            readiness,
            occurrence_templates=tuple(
                reversed(readiness.occurrence_templates)
            ),
        )
    with pytest.raises(
        consumer.V072RegisteredCampaignConsumerInvariantViolation
    ):
        replace(
            readiness,
            occurrence_templates=(
                *readiness.occurrence_templates[:-1],
                readiness.occurrence_templates[-2],
            ),
        )
    with pytest.raises(
        consumer.V072RegisteredCampaignConsumerInvariantViolation
    ):
        replace(
            readiness.occurrence_templates[0],
            occurrence_ordinal=1,
        )


def test_registered_endpoint_is_bundle_only_and_nonauthorizing() -> None:
    readiness = (
        endpoint
        .inspect_registered_complete_bundle_verifier_readiness_v1()
    )
    assert readiness.bundle_minting_enabled is True
    assert readiness.registered_bundle_available is False
    assert readiness.registered_endpoint_verification_allowed is True
    assert readiness.registered_observations_generated == 0
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        endpoint.verify_registered_v072_complete_bundle_v1(
            bundle=object()
        )
    for claim in (
        {"endpoint": "PASS"},
        {"status": "CERTIFIED"},
        {"counts": 15},
    ):
        with pytest.raises(TypeError):
            endpoint.verify_registered_v072_complete_bundle_v1(
                bundle=object(),
                **claim,
            )


def test_direct_complete_bundle_construction_is_impossible_pre_anchor() -> None:
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        endpoint.RegisteredCampaignCompleteBundleV1(
            object(),
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            (),
            (),
            object(),
            object(),
        )
