from __future__ import annotations

import copy
import dataclasses
from pathlib import Path

import pytest

import acfqp.construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from acfqp.routing_v1 import RouteSelection


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)


@pytest.fixture(scope="module")
def current_identity(proof_bytes: bytes):
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    return acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )


@pytest.fixture(scope="module")
def acquired(proof_bytes: bytes, current_identity):
    return acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
        proof_bytes,
        current_identity=current_identity,
    )


def _disposition_counts(acquired) -> dict[str, int]:
    return {
        row["disposition"]: row["count"]
        for row in acquired.to_document()["path_disposition_counts"]
    }


def test_all_acquisition_domains_are_central_and_role_separated() -> None:
    domains = acquisition_v1.REGISTERED_DOMAINS
    assert len(domains) == 7
    assert domains <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-canonical-fallback-payload"}
    assert len({content_id(domain, payload) for domain in domains}) == 7


def test_raw_fallback_retains_13_source_values_but_blocks_all_202_paths(
    acquired,
) -> None:
    document = acquired.to_document()
    assert document["fq9_target_terminal_code"] == "FULL_GROUND_EXACT_INFEASIBLE"
    assert acquired.execution.result.outcome is (
        GroundFallbackOutcome.INFEASIBLE_CERTIFIED
    )
    assert acquired.acquisition_outcome == (
        "EXACT_INFEASIBILITY_RAW_SOURCE_VALUES_ACQUIRED"
    )
    assert len(acquired.path_evidence) == 202
    assert _disposition_counts(acquired) == {
        "STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED": 178,
        "SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE": 7,
        "SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE": 6,
        "UNRESOLVED_SHARED_RESOURCE_RECEIPT": 9,
        "UNRESOLVED_PROCESS_DERIVED_PROOF": 2,
    }
    assert document["exact_source_value_path_count"] == 13
    assert document["formal_resolved_path_count"] == 0
    assert document["formal_blocked_path_count"] == 202
    assert document["all_202_paths_formal_blocked"] is True
    assert document["unresolved_no_value_path_count"] == 189
    assert document["required_v6_path_count"] == 202
    assert document["raw_infeasibility_source_values_acquired"] is True
    assert document["operational_infeasibility_terminal_authorized"] is False
    assert document["raw_marginal_segment"] is True
    assert document["trusted_provenance"] is None
    assert document["production_authorized"] is False
    assert document["production_chain_closed"] is False
    assert document["official_execution_allowed"] is False
    assert document["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )


def test_preexecution_upper_and_fallback_decision_are_frozen_before_real_search(
    acquired,
) -> None:
    pre = acquired.preexecution
    result = acquired.execution.result
    assert pre.decision.selected_route is RouteSelection.FALLBACK
    assert pre.decision.selected_upper_id == pre.upper.route_upper_bound_envelope_id
    assert result.route_decision_id == pre.decision.route_decision_id
    assert result.selected_upper_id == pre.upper.route_upper_bound_envelope_id
    assert result.decision_point_id == pre.decision_point.decision_point_id
    assert pre.to_document()["route_decision_frozen_before_kernel_access"] is True
    assert pre.to_document()["scope"] == "RAW_IN_PROCESS_MARGINAL_SEGMENT"
    assert pre.to_document()["production_route_authority"] is False
    assert pre.to_document()["claimant_self_match_used"] is False
    actual = acquired.execution.work_vector.values
    uppers = dict(pre.upper_proof.leaf_upper_bounds)
    for path in (
        "control.cap_checks",
        "control.cap_rejections",
        "fallback.actions_evaluated",
        "fallback.bellman_backups",
        "fallback.ground_steps",
        "fallback.outcome_rows",
        "fallback.states_expanded",
    ):
        assert actual[path] <= uppers[path]


def test_real_solver_and_complete_live_transition_trace_match_durable_witness(
    acquired,
) -> None:
    work = acquired.execution.work_vector.values
    assert work["fallback.states_expanded"] == 8
    assert work["fallback.actions_evaluated"] == 16
    assert work["fallback.ground_steps"] == 16
    assert work["fallback.outcome_rows"] == 96
    assert work["fallback.bellman_backups"] == 16
    assert work["control.cap_checks"] == 56
    assert work["control.cap_rejections"] == 0
    assert acquired.execution.result.composed_candidate_count == 16
    assert acquired.execution.result.search_complete is True
    assert acquired.execution.selected_policy is None


def test_v1_rows_are_sources_only_and_never_relabelled_as_v6(acquired) -> None:
    document = acquired.to_document()
    assert document["source_v1_counter_record_count"] == 42
    assert document["source_v1_counter_records_relabelled_as_v6"] is False
    assert document["v6_counter_records_issued"] == 0
    assert document["work_vectors_issued"] == 0
    assert document["comparison_vectors_issued"] == 0
    assert document["formal_materializer_v1_called"] is False
    assert document["formal_materializer_v1_compatible"] is False
    assert document["formal_materializer_v1_expected_profile_native_zeros"] == 114
    assert document["direct_fallback_stage_zero_candidate_count"] == 178
    assert document["route_generic_materializer_v2_required"] is True
    assert "materialize_k7_formal_accounting_v1" not in vars(acquisition_v1)
    assert "FALLBACK_BOUNDARY_CATALOGUE_ONLY_PRODUCTION_SITE_NOT_EXECUTED" in (
        document["readiness_blockers_remaining"]
    )
    assert "COUNTER_RECORD_SET_AUTHORITY_MISSING_ALL_202_PATHS" in (
        document["readiness_blockers_remaining"]
    )
    for row in acquired.path_evidence:
        payload = row.to_document()
        assert payload["source_v1_record_relabelled_as_v6"] is False
        assert payload["source_v1_zero_record_used_as_native_zero"] is False
        assert payload["v6_counter_record_issued"] is False
        assert payload["formal_path_resolved"] is False
        assert payload["formal_materialization_eligible"] is False
        assert payload["blocker"]


def test_exact_202_paths_equal_the_v6_required_catalogue(acquired) -> None:
    registry = registry_v6.official_counter_registry_v6()
    assert tuple(row.path for row in acquired.path_evidence) == registry.required_paths
    native = {
        row.path: row.value
        for row in acquired.path_evidence
        if row.disposition
        is acquisition_v1.FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_NATIVE_VALUE_CANDIDATE
    }
    assert native == {
        "control.cap_checks": 56,
        "control.cap_rejections": 0,
        "fallback.actions_evaluated": 16,
        "fallback.bellman_backups": 16,
        "fallback.ground_steps": 16,
        "fallback.outcome_rows": 96,
        "fallback.states_expanded": 8,
    }
    derived = {
        row.path: row.value
        for row in acquired.path_evidence
        if row.disposition
        is acquisition_v1.FallbackPathDispositionV1.SOURCE_BOUND_LEGACY_RECONCILIATION_VALUE_CANDIDATE
    }
    assert derived == {
        "route.attempts": 1,
        "route.failures": 0,
        "route.successes": 1,
        "solver.attempts": 1,
        "solver.failures": 0,
        "solver.successes": 1,
    }
    stage_zero_candidates = [
        row
        for row in acquired.path_evidence
        if row.disposition
        is acquisition_v1.FallbackPathDispositionV1.STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED
    ]
    assert len(stage_zero_candidates) == 178
    assert all(row.value is None and row.blocker for row in stage_zero_candidates)


def test_nine_shared_and_two_process_derived_paths_remain_typed_blockers(
    acquired,
) -> None:
    document = acquired.to_document()
    assert document["unresolved_shared_resource_paths"] == [
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.mounted_bytes_peak",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "memory.working_bytes_peak",
        "process.launches",
    ]
    assert document["unresolved_process_derived_paths"] == [
        "process.exit_failures",
        "process.exit_successes",
    ]
    for path in (
        *document["unresolved_shared_resource_paths"],
        *document["unresolved_process_derived_paths"],
    ):
        row = acquired.by_path[path]
        assert row.value is None
        assert row.blocker
        assert row.source_ids == ()


def test_raw_segment_explicitly_fails_the_full_occurrence_stage_plan(acquired) -> None:
    document = acquired.to_document()
    status = {
        row["stage_kind"]: row["acquisition_status"]
        for row in document["fq9_occurrence_stage_plan"]
    }
    assert status["PREOPEN_COMMON_PREFIX"] == "REQUIRED_OCCURRENCE_STAGE_MISSING"
    assert status["INITIAL_ACQUISITION"] == "REQUIRED_OCCURRENCE_STAGE_MISSING"
    assert status["INITIAL_MODEL_BUILD"] == "REQUIRED_OCCURRENCE_STAGE_MISSING"
    assert status["FAILED_ABSTRACT_PREFIX"] == "REQUIRED_OCCURRENCE_STAGE_MISSING"
    assert status["DIRECT_FALLBACK"] == (
        "RAW_SOURCE_SEGMENT_ONLY_PRODUCTION_STAGE_MISSING"
    )
    assert status["REBUILD"] == "PROFILE_FORBIDDEN_NOT_EXECUTED"
    assert status["CLOSED_RECONCILIATION_AND_TERMINALIZATION"] == (
        "REQUIRED_OCCURRENCE_STAGE_MISSING"
    )
    assert document["production_direct_fallback_stage_missing"] is True
    assert document["complete_occurrence_stage_plan_satisfied"] is False


def test_current_identity_is_issuer_owned_live_source_attestation(
    current_identity,
) -> None:
    document = current_identity.to_document()
    assert document["current_identity_source_supplied_separately_from_claimant"] is True
    assert document["claimant_identity_used_as_current_by_default"] is False
    assert document["live_kernel_and_query_replayed"] is True
    assert document["explicit_current_identity_components_required"] == [
        "BuildEpoch_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    ]
    assert document["build_lane"] == "EVALUATION"
    assert document["production_authority"] is False


def test_none_and_claimant_self_match_current_identity_are_rejected(
    proof_bytes: bytes,
) -> None:
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="fresh current identity is required",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(proof_bytes)
    claimant_identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="claimant self-match is forbidden",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
            proof_bytes,
            current_identity=claimant_identity,
        )


def test_stale_or_missing_explicit_current_components_are_rejected(
    proof_bytes: bytes,
) -> None:
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="explicit current BuildEpoch",
    ):
        acquisition_v1.build_current_canonical_fallback_identity_v1(CANONICAL_BUNDLE)
    stale_build = "0" * 64
    assert stale_build != identity.build_epoch_id
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="explicit current identity components differ from current source",
    ):
        acquisition_v1.build_current_canonical_fallback_identity_v1(
            CANONICAL_BUNDLE,
            build_epoch_id=stale_build,
            threshold_profile_id=identity.threshold_profile_id,
            reward_profile_id=identity.reward_profile_id,
            policy_class_id=identity.policy_class_id,
            complete_search_profile_id=identity.complete_search_profile_id,
        )


def test_acquisition_rejects_stale_current_identity_before_solver(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proof_bytes: bytes,
    current_identity,
) -> None:
    marker = tmp_path / "stale-current-reached-solver"
    stale_build = "0" * 64
    assert stale_build != current_identity.identity.build_epoch_id
    stale_identity = dataclasses.replace(
        current_identity.identity,
        build_epoch_id=stale_build,
    )
    stale_current = acquisition_v1.CanonicalFallbackCurrentIdentityV1(
        acquisition_v1._CURRENT_IDENTITY_ISSUER,
        stale_identity,
        current_identity.current_source_proof_sha256,
        current_identity.live_initial_law_id,
        current_identity.live_transition_law_id,
    )

    def forbidden(*args, **kwargs):  # type: ignore[no-untyped-def]
        marker.write_text("unexpected", encoding="utf-8")
        raise AssertionError("ground solver ran for stale current identity")

    # Replace both the invocation and its guard anchor solely to observe the
    # proof-check/solver ordering.  Production callers cannot issue
    # ``stale_current`` because its issuer token is private to this module.
    monkeypatch.setattr(acquisition_v1, "run_ground_fallback_search_v1", forbidden)
    monkeypatch.setattr(acquisition_v1, "_EXPECTED_RAW_SOLVER_CALLABLE", forbidden)
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="does not match the fresh current live/build identity",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
            proof_bytes,
            current_identity=stale_current,
        )
    assert not marker.exists()


def test_solver_callable_substitution_is_rejected_before_external_side_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proof_bytes: bytes,
    current_identity,
) -> None:
    marker = tmp_path / "solver-side-effect"

    def substituted(*args, **kwargs):  # type: ignore[no-untyped-def]
        marker.write_text("unexpected", encoding="utf-8")
        raise AssertionError("substituted solver executed")

    monkeypatch.setattr(acquisition_v1, "run_ground_fallback_search_v1", substituted)
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="callable substitution detected",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
            proof_bytes,
            current_identity=current_identity,
        )
    assert not marker.exists()


@pytest.mark.parametrize(
    "method_name",
    ("step", "actions", "initial_distribution"),
)
def test_kernel_callable_substitution_is_rejected_before_external_side_effect(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    proof_bytes: bytes,
    current_identity,
    method_name: str,
) -> None:
    marker = tmp_path / f"kernel-{method_name}-side-effect"
    original = getattr(acquisition_v1.G2048Kernel, method_name)

    def substituted(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        marker.write_text("unexpected", encoding="utf-8")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(acquisition_v1.G2048Kernel, method_name, substituted)
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="callable substitution detected",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
            proof_bytes,
            current_identity=current_identity,
        )
    assert not marker.exists()


def test_full_bytes_verifier_reruns_proof_route_and_solver(
    proof_bytes: bytes,
    current_identity,
    acquired,
) -> None:
    replayed = (
        acquisition_v1.verify_canonical_infeasible_direct_fallback_acquisition_bytes_v1(
            raw=acquired.canonical_bytes,
            proof_bytes=proof_bytes,
            current_identity=current_identity,
        )
    )
    assert replayed.acquisition_id == acquired.acquisition_id
    assert replayed.to_document() == acquired.to_document()
    assert replayed.to_document()["durable_proof_lane"] == "EVALUATION"
    assert (
        replayed.to_document()["durable_proof_charged_as_operational_route_work"]
        is False
    )


def test_edited_native_value_fails_independent_full_replay(
    proof_bytes: bytes,
    current_identity,
    acquired,
) -> None:
    document = copy.deepcopy(acquired.to_document())
    target = next(
        row
        for row in document["path_evidence"]
        if row["path"] == "fallback.ground_steps"
    )
    target["value"] += 1
    raw = canonical_json_bytes(document)
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="differ from independent full replay",
    ):
        acquisition_v1.verify_canonical_infeasible_direct_fallback_acquisition_bytes_v1(
            raw=raw,
            proof_bytes=proof_bytes,
            current_identity=current_identity,
        )


def test_cap_exhaustion_is_retained_only_as_noncertificate_acquisition(
    proof_bytes: bytes,
    current_identity,
) -> None:
    cap = GroundFallbackCapProfileV1(
        max_states_expanded=8,
        max_actions_evaluated=1,
        max_ground_steps=1,
        max_outcome_rows=6,
        max_bellman_backups=16,
        max_composed_candidates=16,
        max_cap_checks=56,
        max_positive_outcomes_per_step=6,
    )
    acquired = acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
        proof_bytes,
        current_identity=current_identity,
        cap_profile=cap,
    )
    document = acquired.to_document()
    assert acquired.execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED
    assert acquired.acquisition_outcome == (
        "CAP_EXHAUSTED_NONCERTIFICATE_ACQUISITION"
    )
    assert document["fq9_target_terminal_code"] == "FALLBACK_CAP_EXHAUSTED"
    assert document["raw_infeasibility_source_values_acquired"] is False
    assert document["operational_infeasibility_terminal_authorized"] is False
    assert document["cap_exhausted_is_infeasibility"] is False
    assert acquired.by_path["route.failures"].value == 1
    assert acquired.by_path["route.successes"].value == 0
    assert acquired.by_path["solver.failures"].value == 1
    assert acquired.by_path["solver.successes"].value == 0


def test_invalid_durable_proof_fails_before_ground_solver(
    proof_bytes: bytes,
    current_identity,
) -> None:
    document = loads_canonical_json(proof_bytes)
    document["claim"]["search_complete"] = False
    changed = canonical_json_bytes(document)

    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="durable exact-infeasibility proof failed",
    ):
        acquisition_v1.acquire_canonical_infeasible_direct_fallback_v1(
            changed,
            current_identity=current_identity,
        )


def test_issuer_owned_objects_cannot_be_reclassified(acquired) -> None:
    row = acquired.by_path["fallback.ground_steps"]
    with pytest.raises(
        acquisition_v1.ConstructionK7CanonicalInfeasibleFallbackAcquisitionV1Error,
        match="caller-minted",
    ):
        dataclasses.replace(
            row,
            _issuer=object(),
            disposition=(
                acquisition_v1.FallbackPathDispositionV1.STAGE_FORBIDDEN_ZERO_CANDIDATE_UNRESOLVED
            ),
            value=None,
        )
