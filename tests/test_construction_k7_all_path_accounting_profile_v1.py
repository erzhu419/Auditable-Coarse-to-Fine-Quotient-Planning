from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from functools import cache

import pytest

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_all_path_accounting_profile_v1 as profile_v1
from acfqp.routing_v1 import TerminalClass, TerminalCode


@cache
def _profile() -> profile_v1.ConstructionK7AllPathAccountingProfileV1:
    return profile_v1.freeze_construction_k7_all_path_accounting_profile_v1()


def test_profile_freezes_exact_fq9_routes_stages_families_and_locks() -> None:
    profile = _profile()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )

    assert profile.counter_registry_id == registry.registry_id
    assert profile.stage_profile_id == stage.stage_profile_id
    assert profile.comparison_profile_id == comparison.comparison_profile_id
    assert (
        profile.actual_projection_profile_id
        == projection.actual_projection_profile_id
    )
    assert len(profile.terminal_path_rules) == 10
    assert set(profile.terminal_path_rule_by_code) == set(TerminalCode)
    assert {row.terminal_class for row in profile.terminal_path_rules} == set(
        TerminalClass
    )

    for rule in profile.terminal_path_rules:
        assert len(rule.stage_plan) == 10
        assert {row.stage_kind for row in rule.stage_plan} == set(
            registry_v6.ConstructionStageKindV6
        )
        assert len(rule.accounting_family_rules) == 7
        assert {row.family for row in rule.accounting_family_rules} == set(
            profile_v1.AccountingFamilyV1
        )
        assert rule.separate_work_vector_per_route_segment_required
        assert rule.local_failure_and_fallback_must_remain_distinct_vectors

    document = profile.to_document()
    assert document["proposed_contract_version"] == "2.0.33"
    assert document["profile_only"] is True
    assert document["terminal_execution_performed"] is False
    assert document["counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
    assert document["all_path_native_accounting_complete"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"].endswith("NOT_RUN")
    assert document["workload_economics_gate_status"].endswith("NOT_RUN")


def test_route_recipes_preserve_separate_vectors_and_failure_cutoffs() -> None:
    rules = _profile().terminal_path_rule_by_code

    abstract = rules[TerminalCode.ABSTRACT_CERTIFIED]
    assert abstract.route_kinds_permitted_in_attempt == (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
    )
    abstract_families = {
        row.family: row.disposition for row in abstract.accounting_family_rules
    }
    assert abstract_families[profile_v1.AccountingFamilyV1.LOCAL_OWNER] is (
        profile_v1.AccountingFamilyDispositionV1
        .NATIVE_ZERO_ATTESTATION_REQUIRED
    )

    local = rules[TerminalCode.LOCAL_GROUND_RECOVERY]
    assert local.route_kinds_permitted_in_attempt == (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        RouteKindEnum.LOCAL_ATTEMPT,
    )
    local_families = {
        row.family: row.disposition for row in local.accounting_family_rules
    }
    assert local_families[profile_v1.AccountingFamilyV1.LOCAL_OWNER] is (
        profile_v1.AccountingFamilyDispositionV1.OWNER_EVIDENCE_REQUIRED
    )
    assert local_families[profile_v1.AccountingFamilyV1.FALLBACK_OWNER] is (
        profile_v1.AccountingFamilyDispositionV1
        .NATIVE_ZERO_ATTESTATION_REQUIRED
    )

    fallback = rules[TerminalCode.FULL_GROUND_FALLBACK]
    assert fallback.route_kinds_permitted_in_attempt == (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.DIRECT_FALLBACK,
    )
    fallback_families = {
        row.family: row.disposition for row in fallback.accounting_family_rules
    }
    assert fallback_families[profile_v1.AccountingFamilyV1.LOCAL_OWNER] is (
        profile_v1.AccountingFamilyDispositionV1
        .OWNER_EVIDENCE_IF_REACHED_ELSE_NATIVE_ZERO
    )
    assert fallback_families[profile_v1.AccountingFamilyV1.FALLBACK_OWNER] is (
        profile_v1.AccountingFamilyDispositionV1.OWNER_EVIDENCE_REQUIRED
    )

    protocol = rules[TerminalCode.PROTOCOL_FAILURE]
    assert protocol.route_kinds_permitted_in_attempt == tuple(RouteKindEnum)
    protocol_stage = {row.stage_kind: row.disposition for row in protocol.stage_plan}
    for stage_kind, disposition in protocol_stage.items():
        if stage_kind is (
            registry_v6.ConstructionStageKindV6
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ):
            assert disposition is profile_v1.StageDispositionV1.REQUIRED_ONCE
        else:
            assert disposition is (
                profile_v1.StageDispositionV1
                .PREFIX_DEPENDENT_THROUGH_FAILURE_CUTOFF
            )


def test_attempt_rebuild_and_missing_semantic_authorities_are_explicit() -> None:
    profile = _profile()
    policy = profile.attempt_rebuild_policy
    assert policy.max_local_transactions_per_logical_occurrence == 2
    assert policy.legal_transaction_indices == (1, 2)
    assert policy.default_rebuild_allowed is False
    assert policy.max_rebuild_attempts_when_registered == 1
    assert policy.max_route_attempts_per_logical_occurrence == 2
    assert policy.economics_denominator == "LOGICAL_OCCURRENCE"

    rules = profile.terminal_path_rule_by_code
    assert rules[TerminalCode.REBUILD_REQUIRED].retry_disposition is (
        profile_v1.RetryDispositionV1.REBUILD_POLICY_CONTROLLED
    )
    assert all(
        row.retry_disposition
        is profile_v1.RetryDispositionV1.CLOSE_LOGICAL_OCCURRENCE
        for code, row in rules.items()
        if code is not TerminalCode.REBUILD_REQUIRED
    )

    budget_roles = {
        row.role: row for row in rules[
            TerminalCode.ATTEMPT_BUDGET_EXHAUSTED
        ].required_evidence_roles
    }
    assert budget_roles["TRUSTED_BUDGET_REPLAY"].required_outcome == (
        "ATTEMPT_BUDGET_EXHAUSTED"
    )
    assert budget_roles["TRUSTED_BUDGET_REPLAY"].authority_state is (
        profile_v1.EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED
    )

    integrity_roles = {
        row.role: row
        for row in rules[TerminalCode.INTEGRITY_FAILURE].required_evidence_roles
    }
    assert integrity_roles["INTEGRITY_FAILURE_EVIDENCE"].authority_state is (
        profile_v1.EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED
    )

    cache_roles = {
        row.role: row
        for row in rules[
            TerminalCode.CACHED_EXACT_INFEASIBLE
        ].required_evidence_roles
    }
    assert cache_roles["DURABLE_EXACT_PROOF_PAYLOAD"].authority_state is (
        profile_v1.EvidenceAuthorityStateV1.SUCCESSOR_AUTHORITY_REQUIRED
    )


def test_v075_terminal_status_inventory_is_exhaustive_and_explicit() -> None:
    profile = _profile()
    live = profile_v1._discover_live_v075_status_enum_inventory_v1()  # noqa: SLF001
    expected = profile_v1._EXPECTED_V075_STATUS_ENUM_INVENTORY_V1  # noqa: SLF001

    assert live == expected
    assert len(live) == 47
    assert sum(len(row[2]) for row in live) == 164
    assert len(profile.v075_status_mappings) == 164
    assert len(profile.v075_status_mapping_by_key) == 164
    assert {
        row.disposition for row in profile.v075_status_mappings
    } == set(profile_v1.V075StatusDispositionV1)

    counts = {
        disposition: sum(
            row.disposition is disposition
            for row in profile.v075_status_mappings
        )
        for disposition in profile_v1.V075StatusDispositionV1
    }
    assert counts == {
        profile_v1.V075StatusDispositionV1.MAP_TO_FQ9: 22,
        profile_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED: 14,
        profile_v1.V075StatusDispositionV1.NONTERMINAL: 128,
    }

    by_key = profile.v075_status_mapping_by_key
    direct_cap = by_key[
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:"
        "DIRECT_PHYSICAL_ROW_CAP_EXHAUSTED"
    ]
    assert direct_cap.disposition is profile_v1.V075StatusDispositionV1.MAP_TO_FQ9
    assert direct_cap.fq9_terminal_code == TerminalCode.ATTEMPT_BUDGET_EXHAUSTED.value

    route_ambiguous_plan = by_key[
        "v075_production_occurrence_authority_v1:"
        "V075ProductionOccurrenceTerminalCodeV1:"
        "EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE"
    ]
    assert route_ambiguous_plan.disposition is (
        profile_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED
    )
    assert route_ambiguous_plan.fq9_terminal_code is None

    awaiting = by_key[
        "v075_schedule_bound_sound_planning_authority_v2:"
        "V075ScheduleBoundPlanningTerminalCodeV2:"
        "CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT"
    ]
    assert awaiting.disposition is profile_v1.V075StatusDispositionV1.NONTERMINAL


def test_independent_document_replay_recomputes_identity_and_keeps_gates_locked() -> None:
    profile = _profile()
    replay = (
        profile_v1.verify_construction_k7_all_path_accounting_profile_document_v1(
            profile.to_document()
        )
    )

    assert replay.profile_id == profile.profile_id
    assert (
        replay.v075_terminal_status_inventory_id
        == profile.v075_terminal_status_inventory_id
    )
    assert replay.fq9_terminal_class_count == 3
    assert replay.fq9_terminal_code_count == 10
    assert replay.route_kind_count == 5
    assert replay.stage_count == 10
    assert replay.accounting_family_count == 7
    assert replay.v075_status_enum_class_count == 47
    assert replay.v075_status_enum_member_count == 164
    assert replay.mapped_to_fq9_count == 22
    assert replay.profile_extension_required_count == 14
    assert replay.nonterminal_count == 128
    assert replay.execution_performed is False
    assert replay.gate_unlocked is False
    assert replay.to_document()["counter_completeness_gate_status"].endswith(
        "NOT_RUN"
    )


def test_independent_replay_does_not_call_profile_freezer(monkeypatch) -> None:
    document = _profile().to_document()

    def forbidden_freezer():
        raise AssertionError("independent replay called the producer/freezer")

    monkeypatch.setattr(
        profile_v1,
        "freeze_construction_k7_all_path_accounting_profile_v1",
        forbidden_freezer,
    )
    replay = (
        profile_v1.verify_construction_k7_all_path_accounting_profile_document_v1(
            document
        )
    )
    assert replay.profile_id == document["profile_id"]


@pytest.mark.parametrize(
    "attack",
    (
        "missing_terminal_rule",
        "missing_v075_mapping",
        "gate_claim",
        "unknown_field",
        "forged_profile_id",
    ),
)
def test_independent_replay_rejects_omission_relabel_and_gate_attacks(
    attack: str,
) -> None:
    document = deepcopy(_profile().to_document())
    if attack == "missing_terminal_rule":
        document["terminal_path_rules"].pop()
    elif attack == "missing_v075_mapping":
        document["v075_status_mappings"].pop()
    elif attack == "gate_claim":
        document["all_path_native_accounting_complete"] = True
    elif attack == "unknown_field":
        document["caller_summary"] = "trusted"
    else:
        document["profile_id"] = "0" * 64

    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="differs|does not replay",
    ):
        profile_v1.verify_construction_k7_all_path_accounting_profile_document_v1(
            document
        )


def test_dataclass_attacks_cannot_drop_a_stage_family_role_or_status() -> None:
    profile = _profile()
    local = profile.terminal_path_rule_by_code[TerminalCode.LOCAL_GROUND_RECOVERY]

    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="coverage is incomplete",
    ):
        replace(local, stage_plan=local.stage_plan[:-1])

    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="coverage is incomplete",
    ):
        replace(local, accounting_family_rules=local.accounting_family_rules[:-1])

    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="coverage is incomplete",
    ):
        replace(local, required_evidence_roles=local.required_evidence_roles[:-1])

    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="Contract 2.0.33",
    ):
        replace(
            profile,
            _issuer=profile_v1._PROFILE_ISSUER,  # noqa: SLF001 - attack
            v075_status_mappings=profile.v075_status_mappings[:-1],
        )


def test_nonmapping_status_cannot_smuggle_an_fq9_target() -> None:
    mapping = next(
        row
        for row in _profile().v075_status_mappings
        if row.disposition is profile_v1.V075StatusDispositionV1.NONTERMINAL
    )
    with pytest.raises(
        profile_v1.ConstructionK7AllPathAccountingProfileV1Error,
        match="must not carry",
    ):
        replace(
            mapping,
            fq9_terminal_class=TerminalClass.PLAN_CERTIFICATE.value,
            fq9_terminal_code=TerminalCode.ABSTRACT_CERTIFIED.value,
        )
