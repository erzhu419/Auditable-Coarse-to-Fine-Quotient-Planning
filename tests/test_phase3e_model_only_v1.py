from __future__ import annotations

import ast
import copy
from fractions import Fraction
import inspect
from pathlib import Path

import pytest

from acfqp.phase3e_ids import (
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    content_id,
)
from acfqp.phase3e_model_only_v1 import (
    ModelOnlyOutcome,
    Phase3EModelOnlyResultV1,
    derive_model_only_phase3e_identities_v1,
    run_phase3e_model_only_from_source_v1,
    run_phase3e_model_only_v1,
    verify_phase3e_model_only_result_without_replanning_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)


ROOT = Path(__file__).resolve().parents[1]
PHASE3C = ROOT / "artifacts" / "phase3c"


def _ground_parent_id(role: str, payload: object) -> str:
    return content_id(
        GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
        {
            "schema": "acfqp.safe_chain_fallback_parent_binding.v1",
            "role": role,
            "payload": payload,
        },
    )


def test_model_only_orchestration_has_exact_h1_pass_and_h2_fail_goldens() -> None:
    h1 = run_phase3e_model_only_v1(PHASE3C, query_key=ABSTRACT_QUERY_KEY)
    h2 = run_phase3e_model_only_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)

    assert h1.outcome is ModelOnlyOutcome.PASS
    assert h1.ground_binding_required is False
    assert h1.audit.unrestricted_reward_upper == Fraction(1, 32)
    assert h1.audit.policy_reward_lower == Fraction(1, 32)
    assert h1.audit.policy_failure_upper == 0
    assert h1.audit.regret_upper == 0
    assert h1.audit.risk_tolerance == 0

    assert h2.outcome is ModelOnlyOutcome.FAIL
    assert h2.ground_binding_required is True
    assert h2.audit.unrestricted_reward_upper == Fraction(3, 64)
    assert h2.audit.policy_reward_lower == Fraction(3, 64)
    assert h2.audit.policy_failure_upper == Fraction(5099, 10000)
    assert h2.audit.regret_upper == 0
    assert h2.audit.risk_tolerance == Fraction(1, 20)

    # A plan-frozen route context exists for both outcomes.  It is an identity
    # and attestation context, not evidence that a ground route was executed.
    for result in (h1, h2):
        assert result.route_context.selected_plan_id == (
            result.selected_plan.selected_contingent_plan_id
        )
        assert result.route_context.logical_occurrence_id == (
            result.logical_occurrence.logical_occurrence_id
        )
        assert result.route_context.route_attempt_id == result.route_attempt.route_attempt_id
        assert result.route_attempt.route_attempt_index == 1
        assert result.logical_occurrence.rebuild_policy_id == (
            result.rebuild_policy.rebuild_policy_id
        )


def test_h1_pass_never_calls_ground_fixture_kernel_or_frozen_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.domains as domains
    from acfqp.domains.g2048 import G2048SafeChainKernel
    import acfqp.frozen_phase3c as frozen_phase3c
    import acfqp.phase3e_model_only_v1 as model_only

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ground namespace opened before a failed sound audit")

    monkeypatch.setattr(domains, "safe_chain_fixture", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "actions", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)

    result = model_only.run_phase3e_model_only_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    assert result.outcome is ModelOnlyOutcome.PASS
    assert result.ground_binding_required is False

    imported_modules = {
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(model_only)))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.domains" not in imported_modules
    assert "acfqp.frozen_phase3c" not in imported_modules
    assert "acfqp.phase3e_fallback_v1" not in imported_modules
    assert "acfqp.phase3e_local_preselection_v1" not in imported_modules


def test_h2_fail_authorizes_but_does_not_open_ground_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import acfqp.domains as domains
    from acfqp.domains.g2048 import G2048SafeChainKernel
    import acfqp.frozen_phase3c as frozen_phase3c

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("model-only FAIL result tried to execute ground work")

    monkeypatch.setattr(domains, "safe_chain_fixture", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "actions", forbidden)
    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    monkeypatch.setattr(frozen_phase3c, "load_frozen_phase3c_world", forbidden)

    result = run_phase3e_model_only_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    assert result.outcome is ModelOnlyOutcome.FAIL
    assert result.ground_binding_required is True
    assert result.route_context.structural_id == result.identities.structural_id
    assert result.route_context.query_id == result.identities.query_id
    assert result.route_context.build_epoch_id == result.identities.build_epoch_id


def test_parent_identity_derivation_matches_ground_binder_payload_exactly() -> None:
    h1_source = load_phase3c_model_source_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    h2_source = load_phase3c_model_source_v1(PHASE3C, query_key=LOCAL_QUERY_KEY)
    h1 = derive_model_only_phase3e_identities_v1(h1_source)
    h2 = derive_model_only_phase3e_identities_v1(h2_source)

    # Both queries consume one reusable model/epoch/manifest; only the query
    # namespace differs.  Every payload below is the exact later-binder payload,
    # independently reconstructed here without loading a ground world.
    assert h1.structural_id == h2.structural_id == _ground_parent_id(
        "structural",
        {"legacy_structural_id": h2_source.lease.legacy_structural_id},
    )
    assert h1.build_epoch_id == h2.build_epoch_id == _ground_parent_id(
        "build_epoch",
        {
            "legacy_build_epoch_id": h2_source.lease.legacy_build_epoch_id,
            "serialized_sha256": h2_source.lease.build_epoch_sha256,
        },
    )
    assert h1.manifest_id == h2.manifest_id == _ground_parent_id(
        "manifest",
        {
            "manifest_sha256": h2_source.lease.source_manifest_sha256,
            "run_id": h2_source.lease.source_run_id,
        },
    )
    assert h1.portable_rapm_id == h2.portable_rapm_id == _ground_parent_id(
        "portable_rapm",
        {
            "model_id": h2_source.lease.legacy_portable_rapm_id,
            "serialized_sha256": h2_source.lease.portable_rapm_sha256,
        },
    )
    assert h2.query_id == _ground_parent_id(
        "query",
        {
            "legacy_query_id": h2_source.lease.legacy_ground_query_id,
            "query_key": LOCAL_QUERY_KEY,
        },
    )
    assert h1.query_id != h2.query_id


@pytest.mark.parametrize("query_key", [ABSTRACT_QUERY_KEY, LOCAL_QUERY_KEY])
def test_model_only_result_round_trips_by_semantic_replay(query_key: str) -> None:
    source = load_phase3c_model_source_v1(PHASE3C, query_key=query_key)
    result = run_phase3e_model_only_v1(PHASE3C, query_key=query_key)

    replayed = Phase3EModelOnlyResultV1.from_dict(result.to_dict(), source=source)
    assert replayed == result
    assert replayed.result_id == result.result_id


def test_run_and_no_replanning_verifier_reject_lost_source_authority() -> None:
    source = load_phase3c_model_source_v1(
        PHASE3C, query_key=ABSTRACT_QUERY_KEY
    )
    result = run_phase3e_model_only_from_source_v1(source)
    lost_authority = copy.copy(source)
    with pytest.raises(ValueError, match="live RAPM authority"):
        run_phase3e_model_only_from_source_v1(lost_authority)
    with pytest.raises(ValueError, match="live source authority"):
        verify_phase3e_model_only_result_without_replanning_v1(
            result,
            source=lost_authority,
        )
