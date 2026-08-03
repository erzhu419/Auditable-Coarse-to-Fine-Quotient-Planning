from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from acfqp import campaign_v1
from acfqp import construction_k7_formal_accounting_materializer_v1 as materializer
from acfqp import construction_k7_root_cap_terminal_authority_v1 as terminal
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests.test_construction_k7_semantic_evidence_closure_v1 import semantic_case


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_id_only_bundle_is_rejected_before_any_production_replay() -> None:
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="field set changed",
    ):
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=canonical_json_bytes(
                {"root_cap_terminal_accounting_bundle_id": _id("id-only")}
            ),
            semantic_closure_raw=b"{}",
            closure_replay_inputs={},
        )


def test_terminal_authority_cannot_be_caller_minted_without_production() -> None:
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="caller-minted",
    ):
        terminal.K7AttemptBudgetTerminalAuthorityV1(
            _issuer=object(),
            cap_evidence=object(),  # type: ignore[arg-type]
            formal_materialization_bundle_id=_id("formal"),
            semantic_evidence_closure_id=_id("closure"),
            semantic_evidence_closure_context_id=_id("context"),
            actual_projection_proof_id=_id("projection"),
            work_vector_id=_id("work"),
            comparison_vector_id=_id("comparison"),
            counter_record_ids=tuple(_id(f"record-{index}") for index in range(202)),
            route_attempt_count=1,
            route_success_count=0,
            route_failure_count=1,
        )


@pytest.fixture(scope="module")
def terminal_case(semantic_case):
    closure_inputs, semantic_closure = semantic_case
    formal = materializer.materialize_k7_formal_accounting_v1(
        semantic_closure_raw=semantic_closure.canonical_bytes,
        closure_replay_inputs=closure_inputs,
    )
    result = terminal.issue_k7_root_cap_terminal_accounting_bundle_v1(
        formal_materialization_raw=formal.canonical_bytes,
        semantic_closure_raw=semantic_closure.canonical_bytes,
        closure_replay_inputs=closure_inputs,
    )
    return closure_inputs, semantic_closure, formal, result


def _rehash_outer(document: dict[str, Any]) -> bytes:
    result = deepcopy(document)
    payload = dict(result)
    payload.pop("root_cap_terminal_accounting_bundle_id", None)
    result["root_cap_terminal_accounting_bundle_id"] = terminal._local_id(  # noqa: SLF001
        terminal.K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN,
        payload,
    )
    return canonical_json_bytes(result)


def test_exact_root_cap_terminal_preserves_complete_actual_work(terminal_case) -> None:
    inputs, semantic_closure, formal, result = terminal_case
    verification = (
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=result.canonical_bytes,
            semantic_closure_raw=semantic_closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )
    )
    cap = result.cap_evidence
    authority = result.terminal_authority
    document = result.to_document()

    assert verification.verified_bundle.to_document() == document
    assert verification.to_document()["full_semantic_roots_replayed"] is True
    assert cap.existing_child_action_row_count + cap.unresolved_child_action_row_count > 19
    assert cap.maximum_new_child_action_rows == 19
    assert cap.route_cap_profile_id == inputs["replay_roots"][
        "request_replay"
    ].request.route_identity.transaction.route_cap_profile_id
    assert cap.rebuild_policy_id == campaign_v1.RebuildPolicyV1().rebuild_policy_id
    assert authority.route_attempt_count == 1
    assert authority.route_success_count == 0
    assert authority.route_failure_count == 1
    assert len(authority.counter_record_ids) == 202
    assert authority.counter_record_ids == tuple(
        row.record_id for row in formal.work_vector.records
    )
    assert authority.work_vector_id == formal.work_vector.work_vector_id
    assert authority.comparison_vector_id == formal.comparison_vector.comparison_vector_id
    assert document["formal_accounting_materialization_bundle"] == formal.to_document()
    assert document["terminal_scope"] == "ROUTE_ATTEMPT"
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert document["specific_cause"] == "CHILD_ACTION_ROW_CAP_EXCEEDED"
    assert document["terminal_is_infeasibility_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["plan_certificate"] is False
    assert document["logical_occurrence_closed"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize("attack", ["id_only", "missing_record"])
def test_id_only_or_incomplete_formal_work_is_rejected(
    terminal_case,
    attack: str,
) -> None:
    inputs, semantic_closure, _formal, result = terminal_case
    document = result.to_document()
    if attack == "id_only":
        embedded = document["formal_accounting_materialization_bundle"]
        document["formal_accounting_materialization_bundle"] = {
            "formal_accounting_materialization_bundle_id": embedded[
                "formal_accounting_materialization_bundle_id"
            ]
        }
    else:
        document["formal_accounting_materialization_bundle"]["work_vector"][
            "records"
        ].pop()
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error
    ):
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=_rehash_outer(document),
            semantic_closure_raw=semantic_closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )


@pytest.mark.parametrize(
    ("field", "forged_value"),
    [
        ("worker_terminal_self_report_authoritative", True),
        ("terminal_class", "INFEASIBILITY_CERTIFICATE"),
        ("terminal_code", "FULL_GROUND_EXACT_INFEASIBLE"),
        ("official_execution_allowed", True),
        ("counter_completeness_gate_passed", True),
    ],
)
def test_worker_claim_forged_terminal_and_gate_unlock_are_rejected(
    terminal_case,
    field: str,
    forged_value: Any,
) -> None:
    inputs, semantic_closure, _formal, result = terminal_case
    document = result.to_document()
    document[field] = forged_value
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="differs from replay",
    ):
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=_rehash_outer(document),
            semantic_closure_raw=semantic_closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )


def test_forged_cap_value_and_id_only_occurrence_authority_are_rejected(
    terminal_case,
) -> None:
    inputs, semantic_closure, _formal, result = terminal_case
    document = result.to_document()
    document["root_cap_exhaustion_evidence"][
        "maximum_new_child_action_rows"
    ] = 10_000
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="differs from replay",
    ):
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=_rehash_outer(document),
            semantic_closure_raw=semantic_closure.canonical_bytes,
            closure_replay_inputs=inputs,
        )

    id_only_inputs = dict(inputs)
    id_only_inputs["occurrence_authority"] = {
        "occurrence_authority_bundle_id": inputs[
            "occurrence_authority"
        ].bundle_id
    }
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="formal accounting materialization failed replay",
    ):
        terminal.issue_k7_root_cap_terminal_accounting_bundle_v1(
            formal_materialization_raw=result.formal_materialization.canonical_bytes,
            semantic_closure_raw=semantic_closure.canonical_bytes,
            closure_replay_inputs=id_only_inputs,
        )


def test_caller_cannot_mint_terminal_authority(terminal_case) -> None:
    _inputs, _semantic_closure, _formal, result = terminal_case
    authority = result.terminal_authority
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="caller-minted",
    ):
        terminal.K7AttemptBudgetTerminalAuthorityV1(
            object(),
            result.cap_evidence,
            authority.formal_materialization_bundle_id,
            authority.semantic_evidence_closure_id,
            authority.semantic_evidence_closure_context_id,
            authority.actual_projection_proof_id,
            authority.work_vector_id,
            authority.comparison_vector_id,
            authority.counter_record_ids,
            authority.route_attempt_count,
            authority.route_success_count,
            authority.route_failure_count,
        )


def test_portable_bundle_is_strict_canonical_json(terminal_case) -> None:
    _inputs, _semantic_closure, _formal, result = terminal_case
    assert loads_canonical_json(result.canonical_bytes) == result.to_document()
    with pytest.raises(
        terminal.ConstructionK7RootCapTerminalAuthorityV1Error,
        match="noncanonical",
    ):
        terminal.verify_k7_root_cap_terminal_accounting_bundle_bytes_v1(
            raw=result.canonical_bytes + b" ",
            semantic_closure_raw=b"{}",
            closure_replay_inputs={},
        )
