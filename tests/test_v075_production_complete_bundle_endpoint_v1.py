from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_production_campaign_reconciliation_v1 as campaign
from acfqp import v075_production_complete_bundle_endpoint_v1 as endpoint
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
        b"acfqp:v075-production-endpoint-construction-test:v1"
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


@pytest.fixture(scope="module")
def frozen_graph() -> tuple[
    public.V075PublicTargetTapeNamespaceV1,
    occurrence_plan.V075ProductionOccurrencePlanV1,
    occurrence_plan.V075ProductionOccurrencePlanVerificationV1,
]:
    family = public.freeze_v075_public_family_generation_v1()
    salt = hashlib.sha512(b"v075-production-endpoint-test").digest()
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
    namespace = public.derive_public_target_tape_namespace_v1(
        family=family,
        environment_commitment=commitment,
        signer_registry=registry,
        claimed_final_preregistration_registry_id=registry.registry_id,
        remote_main_anchor=_claim(
            registry,
            role.REMOTE_MAIN_ANCHOR,
            "endpoint",
        ),
        final_preregistration=_claim(
            registry,
            role.FINAL_PREREGISTRATION,
            "endpoint",
        ),
        observer_profile=_claim(
            registry,
            role.OBSERVER_PROFILE,
            "endpoint",
        ),
    )
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


def _default_draw(entry) -> int:
    by_arm = {
        "SOURCE_CONSENSUS_PRIOR": 10,
        "NO_PRIOR": 20,
        "WRONG_CONSENSUS_PRIOR": 25,
        "OOD_ABSTENTION": 30,
        "MATCHED_DIRECT_GROUND": 10,
    }
    return by_arm[entry.arm.value] + entry.context_ordinal


def _semantic_standins(
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    *,
    draws: dict[int, int] | None = None,
    terminals: dict[
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
    """Issue exact-type nonproduction stand-ins for endpoint mechanics tests."""

    draws = {} if draws is None else draws
    terminals = {} if terminals is None else terminals
    default_terminal = (
        occurrence.V075ProductionOccurrenceTerminalClassV1.PLAN_CERTIFICATE,
        occurrence.V075ProductionOccurrenceTerminalCodeV1
        .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE,
    )
    results = []
    verifications = []
    for index, entry in enumerate(plan.entries):
        terminal_class, terminal_code = terminals.get(
            index,
            default_terminal,
        )
        result_id = _id(f"result-{entry.entry_id}-{terminal_code.value}")
        ipc_result_id = _id(f"ipc-{entry.entry_id}")
        work_id = _id(f"work-{entry.entry_id}")
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
        object.__setattr__(
            result,
            "ipc_result",
            SimpleNamespace(
                result_id=ipc_result_id,
                actual_work=SimpleNamespace(work_id=work_id),
            ),
        )
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
            "plan_verification_id": plan_verification.verification_id,
            "ipc_result_id": ipc_result_id,
            "ipc_actual_work_id": work_id,
            "lifecycle_closure_id": _id(f"closure-{entry.entry_id}"),
            "terminal_class": terminal_class,
            "terminal_code": terminal_code,
            "accepted_draw_count": draws.get(index, _default_draw(entry)),
            "outcome_aggregate_count": 2 * (index + 1),
            "process_launch_count": 1,
            "child_message_count": 3 + index,
            "parent_message_count": 4 + index,
            "child_bytes_read": 100 + index,
            "parent_bytes_written": 200 + index,
            "protocol_check_count": 5 + index,
            "batch_intent_count": 6 + index,
            "support_freeze_intent_count": 7 + index,
            "round_begin_intent_count": 8 + index,
            "host_operational_planner_replay_count": 0,
            "child_exit_code": 0,
            "stderr_byte_count": 0,
            "operational_transport_present": True,
            "exact_chain_present": terminal_code
            not in {
                occurrence.V075ProductionOccurrenceTerminalCodeV1
                .PROTOCOL_FAILURE,
                occurrence.V075ProductionOccurrenceTerminalCodeV1
                .INTEGRITY_FAILURE,
            },
            "_verification_id": _id(f"verification-{result_id}"),
        }
        for name, value in values.items():
            object.__setattr__(verification, name, value)
        results.append(result)
        verifications.append(verification)
    return tuple(results), tuple(verifications)


def _reconciliation(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    *,
    draws: dict[int, int] | None = None,
    terminals: dict[
        int,
        tuple[
            occurrence.V075ProductionOccurrenceTerminalClassV1,
            occurrence.V075ProductionOccurrenceTerminalCodeV1,
        ],
    ]
    | None = None,
) -> tuple[
    public.V075PublicTargetTapeNamespaceV1,
    campaign.V075ProductionCampaignReconciliationV1,
]:
    namespace, plan, plan_verification = frozen_graph
    results, verifications = _semantic_standins(
        plan,
        plan_verification,
        draws=draws,
        terminals=terminals,
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
    value = campaign.reconcile_v075_production_campaign_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        plan=plan,
        plan_verification=plan_verification,
        occurrence_results=results,
        occurrence_verifications=verifications,
    )
    return namespace, value


def _verify(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    **kwargs,
) -> endpoint.V075ProductionCompleteBundleEndpointVerificationV1:
    namespace, value = _reconciliation(
        frozen_graph,
        monkeypatch,
        **kwargs,
    )
    return endpoint.verify_v075_production_complete_bundle_endpoint_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        claimed=value,
    )


def test_pass_requires_all_fifteen_exact_plans_and_each_context_draw_rule(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _verify(frozen_graph, monkeypatch)
    assert value.verdict is (
        endpoint.V075ProductionScientificEndpointVerdictV1.PASS
    )
    assert value.plan_certificate_count == 15
    assert value.infeasibility_certificate_count == 0
    assert value.noncertificate_count == 0
    assert len(value.context_evidence) == 3
    assert all(item.context_pass for item in value.context_evidence)
    assert all(
        item.source_online_accepted_draws
        < item.no_prior_online_accepted_draws
        for item in value.context_evidence
    )
    assert all(
        item.source_online_accepted_draws
        <= item.matched_direct_online_accepted_draws
        for item in value.context_evidence
    )
    assert tuple(
        evidence.entry.scientific_ordinal
        for context in value.context_evidence
        for evidence in context.occurrences
    ) == tuple(range(15))


@pytest.mark.parametrize(
    "draws",
    (
        {0: 20},
        {5: 13, 9: 12},
    ),
)
def test_complete_valid_contrary_draw_result_is_scientific_fail(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    draws: dict[int, int],
) -> None:
    value = _verify(frozen_graph, monkeypatch, draws=draws)
    assert value.verdict is (
        endpoint.V075ProductionScientificEndpointVerdictV1.FAIL
    )
    assert value.plan_certificate_count == 15
    assert value.infeasibility_certificate_count == 0
    assert value.noncertificate_count == 0


@pytest.mark.parametrize(
    ("terminal", "infeasible", "noncertificate"),
    (
        (
            (
                occurrence.V075ProductionOccurrenceTerminalClassV1
                .INFEASIBILITY_CERTIFICATE,
                occurrence.V075ProductionOccurrenceTerminalCodeV1
                .EXACT_INFEASIBILITY_CERTIFICATE,
            ),
            1,
            0,
        ),
        (
            (
                occurrence.V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE,
                occurrence.V075ProductionOccurrenceTerminalCodeV1
                .EXACT_POLICY_RISK_FAILURE,
            ),
            0,
            1,
        ),
    ),
)
def test_complete_valid_nonpass_terminal_is_retained_as_scientific_fail(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    terminal,
    infeasible: int,
    noncertificate: int,
) -> None:
    value = _verify(
        frozen_graph,
        monkeypatch,
        terminals={7: terminal},
    )
    assert value.verdict is (
        endpoint.V075ProductionScientificEndpointVerdictV1.FAIL
    )
    assert value.plan_certificate_count == 14
    assert value.infeasibility_certificate_count == infeasible
    assert value.noncertificate_count == noncertificate
    assert (
        value.plan_certificate_count
        + value.infeasibility_certificate_count
        + value.noncertificate_count
    ) == 15
    evidence = value.context_evidence[1].occurrences[2]
    assert evidence.terminal_class is terminal[0]
    assert evidence.terminal_code is terminal[1]


@pytest.mark.parametrize(
    "terminal_code",
    (
        occurrence.V075ProductionOccurrenceTerminalCodeV1.PROTOCOL_FAILURE,
        occurrence.V075ProductionOccurrenceTerminalCodeV1.INTEGRITY_FAILURE,
    ),
)
def test_protocol_or_integrity_invalidates_instead_of_scientific_fail(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
    terminal_code,
) -> None:
    namespace, value = _reconciliation(
        frozen_graph,
        monkeypatch,
        terminals={
            3: (
                occurrence.V075ProductionOccurrenceTerminalClassV1
                .ATTEMPT_CLOSURE_NONCERTIFICATE,
                terminal_code,
            )
        },
    )
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleProtocolOrIntegrityFailure
    ) as raised:
        endpoint.verify_v075_production_complete_bundle_endpoint_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=value,
        )
    assert raised.value.invalidating_occurrence_ids == (
        value.occurrences[3].verification.occurrence_id,
    )


def test_endpoint_replays_reconciliation_exactly_once_and_accepts_no_attestation(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace, value = _reconciliation(frozen_graph, monkeypatch)
    original = campaign.verify_v075_production_campaign_reconciliation_v1
    calls = []

    def replay(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(
        campaign,
        "verify_v075_production_campaign_reconciliation_v1",
        replay,
    )
    result = endpoint.verify_v075_production_complete_bundle_endpoint_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        claimed=value,
    )
    assert result.verdict is (
        endpoint.V075ProductionScientificEndpointVerdictV1.PASS
    )
    assert len(calls) == 1
    assert calls[0]["claimed"] is value
    assert set(
        inspect.signature(
            endpoint.verify_v075_production_complete_bundle_endpoint_v1
        ).parameters
    ) == {"repository_root", "namespace", "claimed"}


def test_ducks_foreign_verification_and_reordering_are_rejected(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    namespace, first = _reconciliation(frozen_graph, monkeypatch)
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleEndpointInvariantViolation
    ):
        endpoint.verify_v075_production_complete_bundle_endpoint_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=SimpleNamespace(
                reconciliation_id=first.reconciliation_id
            ),
        )

    _, second = _reconciliation(
        frozen_graph,
        monkeypatch,
        draws={0: 11},
    )
    foreign = campaign.verify_v075_production_campaign_reconciliation_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        claimed=second,
    )
    monkeypatch.setattr(
        campaign,
        "verify_v075_production_campaign_reconciliation_v1",
        lambda **_: foreign,
    )
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleEndpointInvariantViolation
    ):
        endpoint.verify_v075_production_complete_bundle_endpoint_v1(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            claimed=first,
        )

    with pytest.raises(
        campaign.V075ProductionCampaignReconciliationInvariantViolation
    ):
        replace(
            first,
            occurrences=tuple(reversed(first.occurrences)),
        )


def test_endpoint_cannot_accept_or_replace_a_caller_verdict(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _verify(frozen_graph, monkeypatch, draws={0: 20})
    assert value.verdict is (
        endpoint.V075ProductionScientificEndpointVerdictV1.FAIL
    )
    with pytest.raises(TypeError):
        replace(
            value,
            verdict=endpoint.V075ProductionScientificEndpointVerdictV1.PASS,
        )
    names = set(
        inspect.signature(
            endpoint.verify_v075_production_complete_bundle_endpoint_v1
        ).parameters
    )
    assert not any(
        fragment in name
        for name in names
        for fragment in (
            "verdict",
            "status",
            "expected",
            "total",
            "observer",
            "callback",
            "secret",
            "private",
        )
    )


def test_exact_evidence_and_unrun_economics_locks_are_serialized(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _verify(frozen_graph, monkeypatch)
    document = value.to_document()
    assert len(document["reconciliation"]["occurrences"]) == 15
    assert len(document["context_evidence"]) == 3
    assert all(
        len(item["occurrences"]) == 5
        for item in document["context_evidence"]
    )
    assert document["all_occurrences_retained"] is True
    assert document["independent_reconciliation_replay"] is True
    assert document["target_execution_opened_by_endpoint"] is False
    assert document["private_target_inputs_accepted"] is False
    assert document["caller_verdict_accepted"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert endpoint.PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS == "READY"
    assert endpoint.PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED is True
    assert endpoint.TARGET_EXECUTION_OPENED is False


def test_hash_or_nested_evidence_tamper_cannot_retain_endpoint_identity(
    frozen_graph,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = _verify(frozen_graph, monkeypatch)
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleEndpointInvariantViolation
    ):
        replace(
            value.context_evidence[0],
            context_id=value.context_evidence[1].context_id,
        )
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleEndpointInvariantViolation
    ):
        replace(
            value,
            context_evidence=tuple(reversed(value.context_evidence)),
        )
    assert value.verification_id == hashlib.sha256(
        endpoint.DOMAIN_TAGS["endpoint_verification"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(value._payload())
    ).hexdigest()
