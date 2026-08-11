from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_causal_recovery_chain_v1 as subject
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import v075_k7_causal_promotion_accounted_executor_v1 as executor_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _resign_trace(document: dict) -> bytes:
    chain = document["causal_recovery_chain"]
    chain_payload = copy.deepcopy(chain)
    chain_payload.pop("causal_recovery_chain_id", None)
    chain["causal_recovery_chain_id"] = content_id(
        CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN,
        chain_payload,
    )
    document["causal_recovery_chain_id"] = chain["causal_recovery_chain_id"]
    trace_payload = copy.deepcopy(document)
    trace_payload.pop("operational_trace_id", None)
    document["operational_trace_id"] = content_id(
        V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN,
        trace_payload,
    )
    return canonical_json_bytes(document)


def test_domains_and_export_contract_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert executor_v1.RECOVERY_EXPORT_TRACE_SCHEMA.endswith(".v1")
    assert executor_v1.RECOVERY_EXPORT_TRACE_KEYS > executor_v1.MODEL_EXPORT_TRACE_KEYS


@pytest.fixture(scope="module")
def real_recovery_chain(tmp_path_factory: pytest.TempPathFactory):
    if os.environ.get("ACFQP_RUN_REAL_K7_CAUSAL_RECOVERY") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_CAUSAL_RECOVERY=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if retained:
        trace_raw = Path(retained).read_bytes()
        envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    else:
        root = tmp_path_factory.mktemp("k7-causal-recovery")
        preparation = executor_v1.prepare_v075_k7_causal_promotion_accounted_runtime_v1(
            repository_root=REPOSITORY_ROOT,
            runtime_cas_root=root / "runtime-cas",
        )
        execution = executor_v1.execute_v075_k7_causal_recovery_export_v3(
            preparation,
            trace_output_path=root / "recovery-trace.json",
            construction_fixture_marker="real-reusable-build-epoch",
            timeout_seconds=3_600,
        )
        envelope = build_v1.issue_reusable_build_epoch_authority_v1(execution)
        trace_raw = execution.trace_raw
    replayed = subject.replay_construction_k7_causal_recovery_chain_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=canonical_json_bytes(envelope.to_document()),
    )
    return trace_raw, envelope, replayed


def test_real_failure_authorization_ground_successor_replanning_chain(
    real_recovery_chain,
) -> None:
    trace_raw, envelope, replayed = real_recovery_chain
    document = replayed.to_document()
    assert replayed.source_operational_trace_id == envelope.source_operational_trace_id
    assert replayed.authorized_row_count > 0
    assert replayed.incremental_ground_draw_count > 0
    assert replayed.replanning_epoch_count == 3
    assert document["root_and_successor_proofs_exactly_recomputed"] is True
    assert document["root_failed_frontier_bound_to_authorization"] is True
    assert document["incremental_ground_distinctions_only_after_failed_prefix"] is True
    assert document["fresh_query_rebinding_performed"] is False
    assert document["fresh_query_local_recovery_authorized"] is False
    assert document["final_plan_certificate_issued"] is False
    checked = subject.verify_construction_k7_causal_recovery_chain_bytes_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=canonical_json_bytes(envelope.to_document()),
        replay_bytes=canonical_json_bytes(document),
    )
    assert checked.result_id == replayed.result_id


def test_real_recovery_claim_flip_is_rejected_after_full_resign(
    real_recovery_chain,
) -> None:
    trace_raw, _envelope, _replayed = real_recovery_chain
    changed = loads_canonical_json(trace_raw)
    changed["causal_recovery_chain"]["fresh_query_rebinding_performed"] = True
    changed_raw = _resign_trace(changed)
    changed_envelope = build_v1.replay_reusable_build_epoch_source_v1(changed_raw)
    with pytest.raises(subject.ConstructionK7CausalRecoveryChainV1Error):
        subject.replay_construction_k7_causal_recovery_chain_v1(
            source_trace_bytes=changed_raw,
            build_epoch_envelope_bytes=canonical_json_bytes(
                changed_envelope.to_document()
            ),
        )


def test_real_final_proof_tamper_is_rejected_after_trace_resign(
    real_recovery_chain,
) -> None:
    trace_raw, _envelope, _replayed = real_recovery_chain
    changed = loads_canonical_json(trace_raw)
    changed["causal_recovery_chain"]["final_numerical_proof"][
        "policy_assignments_evaluated"
    ] += 1
    changed_raw = _resign_trace(changed)
    changed_envelope = build_v1.replay_reusable_build_epoch_source_v1(changed_raw)
    with pytest.raises(subject.ConstructionK7CausalRecoveryChainV1Error):
        subject.replay_construction_k7_causal_recovery_chain_v1(
            source_trace_bytes=changed_raw,
            build_epoch_envelope_bytes=canonical_json_bytes(
                changed_envelope.to_document()
            ),
        )
