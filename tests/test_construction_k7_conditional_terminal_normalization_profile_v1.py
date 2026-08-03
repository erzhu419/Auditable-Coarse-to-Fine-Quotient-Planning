from __future__ import annotations

from copy import deepcopy
from functools import cache
import hashlib

import pytest

from acfqp.accounting_v1 import RouteKindEnum
from acfqp import construction_k7_all_path_accounting_profile_v1 as all_path_v1
from acfqp import construction_k7_conditional_terminal_normalization_profile_v1 as norm_v1
from acfqp.routing_v1 import TerminalClass, TerminalCode


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@cache
def _profile() -> norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1:
    return norm_v1.freeze_construction_k7_conditional_terminal_normalization_profile_v1()


def _rules(family: norm_v1.NormalizationFamilyV1):
    return tuple(row for row in _profile().rules if row.normalization_family is family)


def _normalize(
    rule: norm_v1.ConditionalNormalizationRuleV1,
    evidence: norm_v1.ConditionalNormalizationEvidenceV1,
) -> norm_v1.ConditionalNormalizationResultV1:
    return norm_v1.normalize_v075_profile_extension_status_v1(
        profile=_profile(),
        source_key=rule.source_key,
        member_value=rule.member_value,
        evidence=evidence,
    )


def test_profile_consumes_exact_fourteen_source_rows_and_keeps_gates_locked() -> None:
    profile = _profile()
    source = all_path_v1.freeze_construction_k7_all_path_accounting_profile_v1()
    extension = tuple(
        row
        for row in source.v075_status_mappings
        if row.disposition
        is all_path_v1.V075StatusDispositionV1.PROFILE_EXTENSION_REQUIRED
    )

    assert profile.source_all_path_accounting_profile_id == source.profile_id
    assert (
        profile.source_v075_terminal_status_inventory_id
        == source.v075_terminal_status_inventory_id
    )
    assert len(profile.rules) == len(extension) == 14
    assert {row.source_key for row in profile.rules} == {
        row.source_key for row in extension
    }
    assert {
        (row.source_key, row.member_value, row.source_mapping_reason_code)
        for row in profile.rules
    } == {
        (row.source_key, row.member_value, row.reason_code) for row in extension
    }
    assert tuple(row.source_key for row in profile.rules) == tuple(
        sorted(row.source_key for row in profile.rules)
    )

    counts = {
        family: len(_rules(family)) for family in norm_v1.NormalizationFamilyV1
    }
    assert counts == {
        norm_v1.NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED: 2,
        norm_v1.NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL: 7,
        norm_v1.NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED: 2,
        norm_v1.NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE: 2,
        norm_v1.NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED: 1,
    }

    document = profile.to_document()
    assert document["proposed_contract_version"] == "2.0.40"
    assert document["no_default_or_class_level_inheritance"] is True
    assert document["conditional_normalization_only"] is True
    assert document["source_status_string_alone_never_authorizes_terminal"] is True
    assert document["terminal_artifacts_issued"] == 0
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_n_break_even"] is None
    assert document["counter_completeness_gate_status"].endswith("NOT_RUN")
    assert document["workload_economics_gate_status"].endswith("NOT_RUN")


def test_each_freeze_is_a_fresh_authority_object_and_mutation_is_isolated() -> None:
    first = norm_v1.freeze_construction_k7_conditional_terminal_normalization_profile_v1()
    second = norm_v1.freeze_construction_k7_conditional_terminal_normalization_profile_v1()
    assert first is not second
    assert first.rules is not second.rules
    assert first.rules[0] is not second.rules[0]
    expected_id = second.profile_id

    # frozen dataclasses are not a security boundary against object.__setattr__;
    # the freezer therefore must never return a shared authority-bearing object.
    object.__setattr__(first, "terminal_artifacts_issued", 1)
    object.__setattr__(first.rules[0], "member_value", "POISONED_CACHED_VALUE")
    third = norm_v1.freeze_construction_k7_conditional_terminal_normalization_profile_v1()
    assert third is not first and third is not second
    assert third.profile_id == expected_id
    assert third.terminal_artifacts_issued == 0
    assert third.rules[0].member_value != "POISONED_CACHED_VALUE"


def test_route_continuation_rows_never_become_terminals() -> None:
    evidence = norm_v1.ConditionalNormalizationEvidenceV1.none()
    for rule in _rules(
        norm_v1.NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL
    ):
        result = _normalize(rule, evidence)
        assert result.outcome is (
            norm_v1.ConditionalNormalizationOutcomeV1
            .ROUTE_CONTINUATION_NONTERMINAL
        )
        assert result.fq9_terminal_class is None
        assert result.fq9_terminal_code is None
        assert result.terminal_artifact_issued is False
        assert result.normalization_only is True
        assert result.downstream_semantic_terminal_authority_required is True

    # The seven rows are the exact frozen families named in the decision.
    names = {row.member_name for row in _rules(
        norm_v1.NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL
    )}
    assert names == {
        "POLICY_ABORT_NONCERTIFICATE",
        "NO_UNCERTAIN_PROOF_FRONTIER",
        "EXACT_POLICY_REGRET_FAILURE",
        "EXACT_POLICY_RISK_FAILURE",
        "STATISTICAL_ENVELOPE_MISS",
        "CONSTRUCTION_CONTROL_ONLY",
    }


@pytest.mark.parametrize(
    ("route_kind", "expected_code"),
    (
        (RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE, TerminalCode.ABSTRACT_CERTIFIED),
        (RouteKindEnum.LOCAL_ATTEMPT, TerminalCode.LOCAL_GROUND_RECOVERY),
        (RouteKindEnum.DIRECT_FALLBACK, TerminalCode.FULL_GROUND_FALLBACK),
    ),
)
def test_plan_certificate_rows_require_route_provenance(
    route_kind: RouteKindEnum, expected_code: TerminalCode
) -> None:
    for rule in _rules(
        norm_v1.NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED
    ):
        missing = _normalize(rule, norm_v1.ConditionalNormalizationEvidenceV1.none())
        assert missing.outcome is (
            norm_v1.ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED
        )
        assert missing.fq9_terminal_code is None

        result = _normalize(
            rule,
            norm_v1.ConditionalNormalizationEvidenceV1.plan_route(
                route_kind, _id(f"route:{route_kind.value}")
            ),
        )
        assert result.outcome is (
            norm_v1.ConditionalNormalizationOutcomeV1
            .FQ9_TARGET_SELECTED_REQUIRES_TERMINAL_AUTHORITY
        )
        assert result.fq9_terminal_class is TerminalClass.PLAN_CERTIFICATE
        assert result.fq9_terminal_code is expected_code
        assert result.terminal_artifact_issued is False


def test_failed_prefix_or_rebuild_cannot_impersonate_plan_route_provenance() -> None:
    for route in (RouteKindEnum.ABSTRACT_FAILED_PREFIX, RouteKindEnum.REBUILD):
        with pytest.raises(
            norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
        ):
            norm_v1.ConditionalNormalizationEvidenceV1.plan_route(
                route, _id(f"forbidden:{route.value}")
            )


def test_process_failure_requires_both_process_and_protocol_evidence() -> None:
    for rule in _rules(
        norm_v1.NormalizationFamilyV1.PROCESS_AND_PROTOCOL_EVIDENCE_REQUIRED
    ):
        missing = _normalize(rule, norm_v1.ConditionalNormalizationEvidenceV1.none())
        assert missing.outcome is (
            norm_v1.ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED
        )
        result = _normalize(
            rule,
            norm_v1.ConditionalNormalizationEvidenceV1.process_and_protocol(
                _id("retained-process-failure"), _id("retained-protocol-evidence")
            ),
        )
        assert result.fq9_terminal_class is (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        )
        assert result.fq9_terminal_code is TerminalCode.PROTOCOL_FAILURE
        assert result.terminal_artifact_issued is False

    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.ConditionalNormalizationEvidenceV1(
            norm_v1.NormalizationEvidenceKindV1.PROCESS_AND_PROTOCOL,
            process_failure_evidence_id=_id("process-only"),
        )


def test_timeout_needs_preregistered_cap_and_trusted_replay_for_cap_terminal() -> None:
    for rule in _rules(
        norm_v1.NormalizationFamilyV1.TIMEOUT_CAP_REPLAY_OR_PROTOCOL_FAILURE
    ):
        no_cap = _normalize(rule, norm_v1.ConditionalNormalizationEvidenceV1.none())
        assert no_cap.fq9_terminal_code is TerminalCode.PROTOCOL_FAILURE

        attempt = _normalize(
            rule,
            norm_v1.ConditionalNormalizationEvidenceV1.timeout_cap_replay(
                norm_v1.TimeoutCapScopeV1.ATTEMPT_BUDGET,
                _id("attempt-cap-profile"),
                _id("attempt-trusted-replay"),
            ),
        )
        assert attempt.fq9_terminal_code is TerminalCode.ATTEMPT_BUDGET_EXHAUSTED

        fallback = _normalize(
            rule,
            norm_v1.ConditionalNormalizationEvidenceV1.timeout_cap_replay(
                norm_v1.TimeoutCapScopeV1.DIRECT_FALLBACK,
                _id("fallback-cap-profile"),
                _id("fallback-trusted-replay"),
            ),
        )
        assert fallback.fq9_terminal_code is TerminalCode.FALLBACK_CAP_EXHAUSTED
        assert all(
            result.terminal_artifact_issued is False
            for result in (no_cap, attempt, fallback)
        )

    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.ConditionalNormalizationEvidenceV1(
            norm_v1.NormalizationEvidenceKindV1
            .PREREGISTERED_CAP_AND_TRUSTED_REPLAY,
            preregistered_cap_profile_id=_id("cap-without-replay"),
            timeout_cap_scope=norm_v1.TimeoutCapScopeV1.ATTEMPT_BUDGET,
        )


def test_generic_noncertificate_requires_typed_cause_evidence() -> None:
    (rule,) = _rules(
        norm_v1.NormalizationFamilyV1.TYPED_NONCERTIFICATE_CAUSE_REQUIRED
    )
    missing = _normalize(rule, norm_v1.ConditionalNormalizationEvidenceV1.none())
    assert missing.outcome is (
        norm_v1.ConditionalNormalizationOutcomeV1.EVIDENCE_REQUIRED
    )
    expected_codes = {
        TerminalCode.INTEGRITY_FAILURE,
        TerminalCode.PROTOCOL_FAILURE,
        TerminalCode.REBUILD_REQUIRED,
        TerminalCode.FALLBACK_CAP_EXHAUSTED,
        TerminalCode.ATTEMPT_BUDGET_EXHAUSTED,
    }
    observed = set()
    for code in expected_codes:
        result = _normalize(
            rule,
            norm_v1.ConditionalNormalizationEvidenceV1.typed_noncertificate_cause(
                code, _id(f"typed-cause:{code.value}")
            ),
        )
        observed.add(result.fq9_terminal_code)
        assert result.fq9_terminal_class is (
            TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
        )
        assert result.terminal_artifact_issued is False
    assert observed == expected_codes

    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.ConditionalNormalizationEvidenceV1.typed_noncertificate_cause(
            TerminalCode.ABSTRACT_CERTIFIED, _id("plan-is-not-generic-cause")
        )


def test_evidence_kinds_cannot_cross_conditional_families() -> None:
    plan_rule = _rules(
        norm_v1.NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED
    )[0]
    process_evidence = norm_v1.ConditionalNormalizationEvidenceV1.process_and_protocol(
        _id("process"), _id("protocol")
    )
    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        _normalize(plan_rule, process_evidence)

    continuation = _rules(
        norm_v1.NormalizationFamilyV1.ROUTE_CONTINUATION_NONTERMINAL
    )[0]
    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        _normalize(continuation, process_evidence)


def test_independent_profile_replay_recomputes_exact_identity() -> None:
    profile = _profile()
    replay = (
        norm_v1.verify_construction_k7_conditional_terminal_normalization_profile_document_v1(
            profile.to_document()
        )
    )
    assert replay.profile_id == profile.profile_id
    assert replay.source_all_path_accounting_profile_id == (
        profile.source_all_path_accounting_profile_id
    )
    assert replay.source_v075_terminal_status_inventory_id == (
        profile.source_v075_terminal_status_inventory_id
    )
    assert replay.exact_source_row_count == 14
    assert replay.plan_route_row_count == 2
    assert replay.continuation_row_count == 7
    assert replay.process_failure_row_count == 2
    assert replay.timeout_row_count == 2
    assert replay.generic_noncertificate_row_count == 1
    assert replay.exact_source_binding_replayed
    assert replay.no_default_or_new_member_inheritance
    assert replay.terminal_artifacts_issued == 0
    assert replay.gate_unlocked is False


@pytest.mark.parametrize(
    "mutation",
    (
        "profile_id",
        "source_profile_id",
        "row_member_value",
        "row_reason",
        "row_family",
        "row_target",
        "row_order",
        "extra_row",
        "terminal_claim",
        "unknown_field",
    ),
)
def test_independent_profile_replay_rejects_resigned_or_structural_attacks(
    mutation: str,
) -> None:
    document = deepcopy(_profile().to_document())
    if mutation == "profile_id":
        document["profile_id"] = _id("forged-profile")
    elif mutation == "source_profile_id":
        document["source_all_path_accounting_profile_id"] = _id("wrong-source")
    elif mutation == "row_member_value":
        document["rules"][0]["member_value"] = "NEW_VALUE"
    elif mutation == "row_reason":
        document["rules"][0]["source_mapping_reason_code"] = "FORGED_REASON"
    elif mutation == "row_family":
        document["rules"][0]["normalization_family"] = (
            norm_v1.NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED.value
        )
    elif mutation == "row_target":
        document["rules"][1]["allowed_fq9_terminal_codes"] = [
            TerminalCode.ABSTRACT_CERTIFIED.value
        ]
    elif mutation == "row_order":
        document["rules"][0], document["rules"][1] = (
            document["rules"][1], document["rules"][0]
        )
    elif mutation == "extra_row":
        document["rules"].append(deepcopy(document["rules"][0]))
        document["exact_source_row_count"] = 15
    elif mutation == "terminal_claim":
        document["terminal_artifacts_issued"] = 1
    else:
        document["unknown_field"] = "attack"
    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.verify_construction_k7_conditional_terminal_normalization_profile_document_v1(
            document
        )


def test_unknown_or_changed_source_member_has_no_default_inheritance() -> None:
    rule = _profile().rules[0]
    evidence = norm_v1.ConditionalNormalizationEvidenceV1.none()
    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.normalize_v075_profile_extension_status_v1(
            profile=_profile(),
            source_key=f"{rule.source_key}_NEW_MEMBER",
            member_value=rule.member_value,
            evidence=evidence,
        )
    with pytest.raises(
        norm_v1.ConstructionK7ConditionalTerminalNormalizationProfileV1Error
    ):
        norm_v1.normalize_v075_profile_extension_status_v1(
            profile=_profile(),
            source_key=rule.source_key,
            member_value="CHANGED_VALUE",
            evidence=evidence,
        )


def test_normalization_result_is_identity_bound_but_never_a_terminal() -> None:
    rule = _rules(
        norm_v1.NormalizationFamilyV1.PLAN_ROUTE_PROVENANCE_REQUIRED
    )[0]
    first = _normalize(
        rule,
        norm_v1.ConditionalNormalizationEvidenceV1.plan_route(
            RouteKindEnum.LOCAL_ATTEMPT, _id("local-provenance-a")
        ),
    )
    second = _normalize(
        rule,
        norm_v1.ConditionalNormalizationEvidenceV1.plan_route(
            RouteKindEnum.LOCAL_ATTEMPT, _id("local-provenance-b")
        ),
    )
    assert first.result_id != second.result_id
    assert first.fq9_terminal_code is second.fq9_terminal_code
    assert first.to_document()["terminal_artifact_issued"] is False
    assert "terminal_artifact_id" not in first.to_document()
