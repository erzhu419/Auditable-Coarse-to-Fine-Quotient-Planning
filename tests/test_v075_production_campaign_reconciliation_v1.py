from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_production_campaign_reconciliation_v1 as campaign
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public
from tests.v075_signature_test_support import (
    make_public_key,
    sign_test_message,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-production-reconciliation-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _secret_laws() -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    return (
        ((1, Fraction(2, 3)), (2, Fraction(1, 3))),
        ((1, Fraction(3, 4)), (2, Fraction(1, 4))),
        ((1, Fraction(4, 5)), (2, Fraction(1, 5))),
    )


def _claim(
    registry: public.V075TrustedSignerRegistryV1,
    role: public.V075ExternalAuthorityRoleV1,
    marker: str,
) -> public.V075SignedExternalAuthorityClaimV1:
    external_id = _id(f"{marker}-{role.value}")
    message = public.external_authority_claim_signing_bytes_v1(
        signer_registry=registry,
        role=role,
        external_id=external_id,
    )
    return public.V075SignedExternalAuthorityClaimV1(
        registry,
        role,
        external_id,
        sign_test_message(message),
    )


def _namespace(
    marker: str = "primary",
) -> public.V075PublicTargetTapeNamespaceV1:
    family = public.freeze_v075_public_family_generation_v1()
    salt = hashlib.sha512(
        f"v075-production-reconciliation-{marker}".encode("utf-8")
    ).digest()
    commitment = public.seal_opaque_environment_commitment_v1(
        family=family,
        secret_salt=salt,
        secret_laws=_secret_laws(),
    )
    registry = public.V075TrustedSignerRegistryV1(
        make_public_key("CAMPAIGN_AUTHORITY"),
        make_public_key("OBSERVER_EVIDENCE"),
    )
    role = public.V075ExternalAuthorityRoleV1
    return public.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=_claim(
            registry,
            role.REMOTE_MAIN_ANCHOR,
            marker,
        ),
        final_preregistration=_claim(
            registry,
            role.FINAL_PREREGISTRATION,
            marker,
        ),
        observer_profile=_claim(
            registry,
            role.OBSERVER_PROFILE,
            marker,
        ),
    )


@pytest.fixture(scope="module")
def frozen_graph() -> tuple[
    public.V075PublicTargetTapeNamespaceV1,
    occurrence_plan.V075ProductionOccurrencePlanV1,
    occurrence_plan.V075ProductionOccurrencePlanVerificationV1,
]:
    namespace = _namespace()
    plan = occurrence_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
    )
    replayed, verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )
    assert replayed == plan
    return namespace, plan, verification


def _terminal(
    index: int,
) -> tuple[
    occurrence.V075ProductionOccurrenceTerminalClassV1,
    occurrence.V075ProductionOccurrenceTerminalCodeV1,
]:
    if index == 13:
        return (
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .INFEASIBILITY_CERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_INFEASIBILITY_CERTIFICATE,
        )
    if index == 14:
        return (
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            occurrence.V075ProductionOccurrenceTerminalCodeV1
            .EXACT_POLICY_RISK_FAILURE,
        )
    return (
        occurrence.V075ProductionOccurrenceTerminalClassV1
        .PLAN_CERTIFICATE,
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE,
    )


def _exact_type_semantic_standins(
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    *,
    override_terminal: dict[
        int,
        tuple[
            occurrence.V075ProductionOccurrenceTerminalClassV1,
            occurrence.V075ProductionOccurrenceTerminalCodeV1,
        ],
    ]
    | None = None,
) -> tuple[
    tuple[occurrence.V075ProductionOccurrenceAuthorityResultV1, ...],
    tuple[occurrence.V075ProductionOccurrenceAuthorityVerificationV1, ...],
]:
    """Make issuer-inaccessible unit stand-ins; never production evidence.

    Production reconciliation still invokes the occurrence semantic authority
    for every item.  Tests replace that expensive boundary with its exact
    expected verification so the fifteen-way accounting and attack surface
    can be exercised without opening a target or launching fifteen workers.
    """

    results = []
    verifications = []
    override_terminal = {} if override_terminal is None else override_terminal
    for index, entry in enumerate(plan.entries):
        terminal_class, terminal_code = override_terminal.get(
            index,
            _terminal(index),
        )
        result_id = _id(f"result-{entry.entry_id}")
        ipc_result_id = _id(f"ipc-result-{entry.entry_id}")
        work_id = _id(f"work-{entry.entry_id}")
        verification_id = _id(f"verification-{entry.entry_id}")
        work = SimpleNamespace(work_id=work_id)
        ipc_result = SimpleNamespace(
            result_id=ipc_result_id,
            actual_work=work,
        )

        result = object.__new__(
            occurrence.V075ProductionOccurrenceAuthorityResultV1
        )
        object.__setattr__(
            result,
            "authority_scope",
            lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION,
        )
        object.__setattr__(result, "plan", plan)
        object.__setattr__(result, "plan_entry", entry)
        object.__setattr__(result, "plan_verification", plan_verification)
        object.__setattr__(result, "ipc_result", ipc_result)
        object.__setattr__(result, "terminal_class", terminal_class)
        object.__setattr__(result, "terminal_code", terminal_code)
        object.__setattr__(result, "_result_id", result_id)

        verification = object.__new__(
            occurrence.V075ProductionOccurrenceAuthorityVerificationV1
        )
        values = {
            "result_id": result_id,
            "occurrence_id": entry.occurrence_id,
            "plan_id": plan.plan_id,
            "plan_entry_id": entry.entry_id,
            "plan_verification_id": (
                result.plan_verification.verification_id
            ),
            "ipc_result_id": ipc_result_id,
            "ipc_actual_work_id": work_id,
            "lifecycle_closure_id": _id(f"closure-{entry.entry_id}"),
            "terminal_class": terminal_class,
            "terminal_code": terminal_code,
            "accepted_draw_count": index + 1,
            "outcome_aggregate_count": 2 * (index + 1),
            "process_launch_count": 1,
            "child_message_count": 3 + index,
            "parent_message_count": 4 + index,
            "batch_intent_count": 6 + index,
            "support_freeze_intent_count": 7 + index,
            "round_begin_intent_count": 8 + index,
            "child_bytes_read": 100 + index,
            "parent_bytes_written": 200 + index,
            "protocol_check_count": 5 + index,
            "host_operational_planner_replay_count": 0,
            "child_exit_code": 0,
            "stderr_byte_count": 9 + index,
            "operational_transport_present": (
                terminal_code
                not in {
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .PROTOCOL_FAILURE,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .PROCESS_FAILURE,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1.TIMEOUT,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .INTEGRITY_FAILURE,
                }
            ),
            "exact_chain_present": (
                terminal_class
                is occurrence.V075ProductionOccurrenceTerminalClassV1
                .PLAN_CERTIFICATE
                or terminal_class
                is occurrence.V075ProductionOccurrenceTerminalClassV1
                .INFEASIBILITY_CERTIFICATE
                or terminal_code
                in {
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .EXACT_POLICY_RISK_FAILURE,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .EXACT_POLICY_REGRET_FAILURE,
                    occurrence.V075ProductionOccurrenceTerminalCodeV1
                    .STATISTICAL_ENVELOPE_MISS,
                }
            ),
            "_verification_id": verification_id,
        }
        for name, value in values.items():
            object.__setattr__(verification, name, value)
        results.append(result)
        verifications.append(verification)
    return tuple(results), tuple(verifications)


@pytest.fixture()
def semantic_graph(
    frozen_graph: tuple[
        public.V075PublicTargetTapeNamespaceV1,
        occurrence_plan.V075ProductionOccurrencePlanV1,
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    public.V075PublicTargetTapeNamespaceV1,
    occurrence_plan.V075ProductionOccurrencePlanV1,
    occurrence_plan.V075ProductionOccurrencePlanVerificationV1,
    tuple[occurrence.V075ProductionOccurrenceAuthorityResultV1, ...],
    tuple[
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1, ...
    ],
]:
    namespace, plan, plan_verification = frozen_graph
    results, verifications = _exact_type_semantic_standins(
        plan,
        plan_verification,
    )
    expected = {
        result.result_id: verification
        for result, verification in zip(
            results,
            verifications,
            strict=True,
        )
    }

    def verify_result(*, repository_root, namespace, claimed):
        assert Path(repository_root).resolve() == REPOSITORY_ROOT
        assert namespace == frozen_graph[0]
        return expected[claimed.result_id]

    monkeypatch.setattr(
        occurrence,
        "verify_v075_production_occurrence_authority_result_v1",
        verify_result,
    )
    return namespace, plan, plan_verification, results, verifications


def _reconcile(
    graph,
) -> campaign.V075ProductionCampaignReconciliationV1:
    namespace, plan, plan_verification, results, verifications = graph
    return campaign.reconcile_v075_production_campaign_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        plan=plan,
        plan_verification=plan_verification,
        occurrence_results=results,
        occurrence_verifications=verifications,
    )


def test_exact_fifteen_way_reconciliation_and_source_charge_once(
    semantic_graph,
) -> None:
    value = _reconcile(semantic_graph)
    document = value.to_document()

    assert len(value.occurrences) == 15
    assert document["logical_occurrence_denominator"] == 15
    assert tuple(
        item.entry.scientific_ordinal for item in value.occurrences
    ) == tuple(range(15))
    assert tuple(
        item.entry.transport_ordinal for item in value.occurrences
    ) == tuple(range(1, 16))
    assert value.plan_certificate_count == 13
    assert value.infeasibility_certificate_count == 1
    assert value.noncertificate_count == 1
    assert sum(
        (
            value.plan_certificate_count,
            value.infeasibility_certificate_count,
            value.noncertificate_count,
        )
    ) == 15
    assert document["source_offline_charge_count"] == 1
    assert document["source_offline_in_online_totals"] is False
    assert value.source_offline_accounting.offline_draw_count > 0
    assert document["campaign_online_work"]["accepted_draw_count"] == sum(
        range(1, 16)
    )
    assert document["campaign_online_work"]["process_launch_count"] == 15
    assert (
        document["campaign_online_work"][
            "host_operational_planner_replay_count"
        ]
        == 0
    )
    assert document["campaign_online_work"]["stderr_byte_count"] == sum(
        range(9, 24)
    )
    assert all(
        item.to_document()["child_exit_code"] == 0
        for item in value.occurrences
    )
    assert len(value.arm_online_accounting) == 5
    assert all(len(item.occurrences) == 3 for item in value.arm_online_accounting)
    assert value.campaign_validity is campaign.V075ProductionCampaignValidityV1.VALID
    assert document["all_occurrences_retained"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"


def test_independent_reconciliation_replay_and_no_target_open(
    semantic_graph,
) -> None:
    value = _reconcile(semantic_graph)
    verification = (
        campaign.verify_v075_production_campaign_reconciliation_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=semantic_graph[0],
            claimed=value,
        )
    )
    assert verification.denominator == 15
    assert verification.reconciliation_id == value.reconciliation_id
    assert verification.campaign_validity is (
        campaign.V075ProductionCampaignValidityV1.VALID
    )
    assert verification.to_document()["semantic_occurrence_replays"] == 15
    assert verification.to_document()["valid"] is True
    source = inspect.getsource(campaign)
    assert "open_production" not in source
    assert "open_construction" not in source
    assert campaign.TARGET_EXECUTION_OPENED is False


@pytest.mark.parametrize("mode", ["missing", "duplicate", "reordered"])
def test_missing_duplicate_and_reordered_results_are_rejected(
    semantic_graph,
    mode: str,
) -> None:
    namespace, plan, plan_verification, results, verifications = (
        semantic_graph
    )
    results = list(results)
    verifications = list(verifications)
    if mode == "missing":
        results.pop()
        verifications.pop()
    elif mode == "duplicate":
        results[-1] = results[0]
        verifications[-1] = verifications[0]
    else:
        results[0], results[1] = results[1], results[0]
        verifications[0], verifications[1] = (
            verifications[1],
            verifications[0],
        )
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=results,
            occurrence_verifications=verifications,
        )


def test_ducks_and_construction_scope_are_rejected(semantic_graph) -> None:
    namespace, plan, plan_verification, results, verifications = (
        semantic_graph
    )
    ducks = list(results)
    ducks[0] = SimpleNamespace(
        authority_scope=lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
    )
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=ducks,
            occurrence_verifications=verifications,
        )

    construction = list(results)
    object.__setattr__(
        construction[0],
        "authority_scope",
        lifecycle.V075LifecycleAuthorityScopeV1.CONSTRUCTION_ONLY,
    )
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=construction,
            occurrence_verifications=verifications,
        )


def test_transplanted_plan_and_verification_are_rejected(
    semantic_graph,
) -> None:
    namespace, plan, plan_verification, results, verifications = (
        semantic_graph
    )
    foreign_namespace = _namespace("foreign")
    foreign_plan = occurrence_plan.freeze_v075_production_occurrence_plan_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=foreign_namespace,
    )
    _foreign_replayed, foreign_plan_verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=foreign_namespace,
            raw=foreign_plan.canonical_bytes,
        )
    )
    foreign_results, _ = _exact_type_semantic_standins(
        foreign_plan,
        foreign_plan_verification,
    )
    transplanted = list(results)
    transplanted[5] = foreign_results[5]
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=transplanted,
            occurrence_verifications=verifications,
        )

    swapped = list(verifications)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=results,
            occurrence_verifications=swapped,
        )


def test_work_tampering_fails_against_semantic_replay(
    semantic_graph,
) -> None:
    namespace, plan, plan_verification, results, verifications = (
        semantic_graph
    )
    tampered = list(verifications)
    clone = object.__new__(
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1
    )
    for name in (
        "result_id",
        "occurrence_id",
        "plan_id",
        "plan_entry_id",
        "plan_verification_id",
        "ipc_result_id",
        "ipc_actual_work_id",
        "lifecycle_closure_id",
        "terminal_class",
        "terminal_code",
        "accepted_draw_count",
        "outcome_aggregate_count",
        "process_launch_count",
        "child_message_count",
        "parent_message_count",
        "batch_intent_count",
        "support_freeze_intent_count",
        "round_begin_intent_count",
        "child_bytes_read",
        "parent_bytes_written",
        "protocol_check_count",
        "host_operational_planner_replay_count",
        "child_exit_code",
        "stderr_byte_count",
        "operational_transport_present",
        "exact_chain_present",
        "_verification_id",
    ):
        object.__setattr__(clone, name, getattr(tampered[2], name))
    object.__setattr__(
        clone,
        "accepted_draw_count",
        clone.accepted_draw_count + 1,
    )
    tampered[2] = clone
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=results,
            occurrence_verifications=tampered,
        )


def test_source_offline_work_tampering_fails_exact_replay(
    semantic_graph,
) -> None:
    value = _reconcile(semantic_graph)
    source_bundle = value.source_offline_accounting.source_bundle
    object.__setattr__(
        source_bundle,
        "offline_draw_count",
        source_bundle.offline_draw_count + 1,
    )
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.verify_v075_production_campaign_reconciliation_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=semantic_graph[0],
            claimed=value,
        )


def test_nonzero_host_operational_replay_is_never_accounted_as_valid(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace, plan, plan_verification = frozen_graph
    results, verifications = _exact_type_semantic_standins(
        plan,
        plan_verification,
    )
    object.__setattr__(
        verifications[0],
        "host_operational_planner_replay_count",
        1,
    )
    expected = {
        result.result_id: verification
        for result, verification in zip(
            results,
            verifications,
            strict=True,
        )
    }
    monkeypatch.setattr(
        occurrence,
        "verify_v075_production_occurrence_authority_result_v1",
        lambda **kwargs: expected[kwargs["claimed"].result_id],
    )
    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        campaign.reconcile_v075_production_campaign_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            plan=plan,
            plan_verification=plan_verification,
            occurrence_results=results,
            occurrence_verifications=verifications,
        )


@pytest.mark.parametrize(
    "code",
    [
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .PROTOCOL_FAILURE,
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .INTEGRITY_FAILURE,
    ],
)
def test_protocol_or_integrity_failure_is_retained_and_invalidates_campaign(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    code: occurrence.V075ProductionOccurrenceTerminalCodeV1,
) -> None:
    namespace, plan, plan_verification = frozen_graph
    terminal = {
        0: (
            occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE,
            code,
        )
    }
    results, verifications = _exact_type_semantic_standins(
        plan,
        plan_verification,
        override_terminal=terminal,
    )
    expected = {
        result.result_id: verification
        for result, verification in zip(
            results,
            verifications,
            strict=True,
        )
    }
    monkeypatch.setattr(
        occurrence,
        "verify_v075_production_occurrence_authority_result_v1",
        lambda **kwargs: expected[kwargs["claimed"].result_id],
    )
    value = campaign.reconcile_v075_production_campaign_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        plan=plan,
        plan_verification=plan_verification,
        occurrence_results=results,
        occurrence_verifications=verifications,
    )
    assert len(value.occurrences) == 15
    assert value.noncertificate_count == 2
    assert value.invalidating_occurrence_ids == (
        plan.entries[0].occurrence_id,
    )
    assert value.campaign_validity is (
        campaign.V075ProductionCampaignValidityV1
        .INVALID_PROTOCOL_OR_INTEGRITY
    )
    verification = (
        campaign.verify_v075_production_campaign_reconciliation_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=value,
        )
    )
    assert verification.to_document()["valid"] is False


def test_api_accepts_no_caller_denominator_totals_or_status() -> None:
    signature = inspect.signature(
        campaign.reconcile_v075_production_campaign_v1
    )
    assert tuple(signature.parameters) == (
        "repository_root",
        "namespace",
        "plan",
        "plan_verification",
        "occurrence_results",
        "occurrence_verifications",
    )
    forbidden = {
        "denominator",
        "online_draw_count",
        "offline_draw_count",
        "terminal_class",
        "terminal_code",
        "campaign_valid",
        "official_scalar_cost",
        "N_break_even",
    }
    assert forbidden.isdisjoint(signature.parameters)
    assert campaign.CALLER_SUMMARIES_ACCEPTED is False
    assert campaign.CALLER_TOTALS_ACCEPTED is False
    assert campaign.REORDERING_ACCEPTED is False
