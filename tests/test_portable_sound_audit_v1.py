from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.portable import PortableQuery, PortableRAPM
from acfqp.portable_planner import PortablePolicy
from acfqp.portable_sound_audit_v1 import (
    AbstractPlanAuditV1,
    PortableSoundAuditV1Error,
    PortableSoundBellmanProofV1,
    build_portable_sound_audit_v1,
    verify_portable_sound_audit_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _inputs() -> tuple[
    PortableRAPM,
    tuple[PortableQuery, PortableQuery],
    tuple[PortablePolicy, PortablePolicy],
]:
    model = PortableRAPM.from_dict(
        json.loads((PHASE3C / "build/portable_rapm.json").read_text(encoding="utf-8"))
    )
    query_rows = [
        json.loads(line)
        for line in (PHASE3C / "campaign/portable_queries.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    plan_rows = [
        json.loads(line)
        for line in (PHASE3C / "campaign/portable_plans.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    queries = tuple(
        PortableQuery.from_dict(row["portable_query"], model) for row in query_rows
    )
    policies = tuple(
        PortablePolicy.from_dict(row["proposal_policy"]) for row in plan_rows
    )
    assert len(queries) == len(policies) == 2
    return model, queries, policies  # type: ignore[return-value]


def _forbidden(*_args: object, **_kwargs: object) -> object:
    raise AssertionError("ground/full-planner API crossed the portable audit boundary")


def test_frozen_phase3c_h1_pass_is_proved_from_serialized_rapm_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, queries, policies = _inputs()
    monkeypatch.setattr(G2048SafeChainKernel, "step", _forbidden)

    # The sound audit does not reconstruct the deterministic-policy frontier.
    import acfqp.portable_planner as portable_planner

    monkeypatch.setattr(portable_planner, "solve_portable_pareto", _forbidden)
    proof, audit = build_portable_sound_audit_v1(model, queries[0], policies[0])

    assert audit.outcome == "PASS"
    assert audit.certified is True
    assert audit.unrestricted_reward_upper == Fraction(1, 32)
    assert audit.policy_reward_lower == Fraction(1, 32)
    assert audit.policy_failure_upper == 0
    assert audit.regret_upper == 0
    assert audit.reachable_cell_horizon_pairs == 2
    assert len(proof.coverage_rows) == 20
    assert len(proof.unrestricted_rows) == 10
    assert len(proof.policy_rows) == 2
    assert verify_portable_sound_audit_v1(
        model, queries[0], policies[0], proof, audit
    ) == audit

    # Both containers have strict full-SHA content IDs and round trip exactly.
    assert len(proof.proof_id) == len(audit.audit_id) == 64
    assert PortableSoundBellmanProofV1.from_dict(proof.to_dict()) == proof
    assert AbstractPlanAuditV1.from_dict(audit.to_dict()) == audit


def test_frozen_phase3c_h2_recovery_policy_fails_sound_risk_gate() -> None:
    model, queries, policies = _inputs()

    proof, audit = build_portable_sound_audit_v1(model, queries[1], policies[1])

    assert audit.outcome == "FAIL"
    assert audit.certified is False
    assert audit.unrestricted_reward_upper == Fraction(3, 64)
    assert audit.policy_reward_lower == Fraction(3, 64)
    assert audit.policy_failure_upper == Fraction(5099, 10000)
    assert audit.regret_upper == 0
    assert audit.risk_tolerance == Fraction(1, 20)
    assert audit.reachable_cell_horizon_pairs == 4
    assert len(proof.coverage_rows) == 20
    assert len(proof.unrestricted_rows) == 20
    assert len(proof.policy_rows) == 4
    assert verify_portable_sound_audit_v1(
        model, queries[1], policies[1], proof.to_dict(), audit.to_dict()
    ).outcome == "FAIL"


def test_re_signed_false_bellman_row_and_audit_binding_are_rejected() -> None:
    model, queries, policies = _inputs()
    proof, audit = build_portable_sound_audit_v1(model, queries[0], policies[0])

    forged_row = replace(
        proof.unrestricted_rows[0],
        reward_upper=proof.unrestricted_rows[0].reward_upper + Fraction(1, 1000),
    )
    forged_proof = replace(
        proof,
        unrestricted_rows=tuple(sorted((forged_row, *proof.unrestricted_rows[1:]))),
    )
    # The container is internally re-signed, so only semantic replay catches it.
    assert PortableSoundBellmanProofV1.from_dict(forged_proof.to_dict()) == forged_proof
    with pytest.raises(PortableSoundAuditV1Error, match="false, incomplete"):
        verify_portable_sound_audit_v1(
            model, queries[0], policies[0], forged_proof, audit
        )

    rebound_audit = replace(audit, proof_id="0" * 64)
    assert AbstractPlanAuditV1.from_dict(rebound_audit.to_dict()) == rebound_audit
    with pytest.raises(PortableSoundAuditV1Error, match="abstract plan audit is false"):
        verify_portable_sound_audit_v1(
            model, queries[0], policies[0], proof, rebound_audit
        )


def test_missing_reachable_policy_decision_and_incomplete_envelope_fail_closed() -> None:
    model, queries, _policies = _inputs()
    with pytest.raises(PortableSoundAuditV1Error, match="undefined or unavailable"):
        build_portable_sound_audit_v1(model, queries[0], PortablePolicy(()))

    # Even if an attacker re-signs the outer model, PortableRAPM validation
    # rejects a semantic action that no longer realizes every active member.
    document = model.to_dict()
    document["envelope"][0]["realizations"].pop()
    payload = dict(document)
    payload.pop("model_id")
    from acfqp.portable import logical_id

    document["model_id"] = logical_id("rapm", payload)
    with pytest.raises(ValueError, match="every active member"):
        PortableRAPM.from_dict(document)


def test_row_byte_tampering_breaks_content_id_before_semantic_replay() -> None:
    model, queries, policies = _inputs()
    proof, _audit = build_portable_sound_audit_v1(model, queries[0], policies[0])
    document = proof.to_dict()
    document["policy_rows"][0]["failure_upper"] = {
        "numerator": 1,
        "denominator": 100,
    }
    with pytest.raises(PortableSoundAuditV1Error, match="content ID mismatch"):
        PortableSoundBellmanProofV1.from_dict(document)
