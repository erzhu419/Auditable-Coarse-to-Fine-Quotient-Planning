from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_prefix_failure_closure_independent_verifier_v2 as independent
from acfqp import construction_k7_query_bound_campaign_prefix_failure_closure_v2 as subject
from acfqp import construction_k7_query_bound_campaign_preregistration_v1 as prereg_v1
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id


def test_public_surfaces_and_domains_are_additive() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error",
        "FAILURE_FILENAME",
        "QueryBoundCampaignPrefixFailureClosureV2",
        "run_query_bound_campaign_with_prefix_failure_closure_v2",
    }
    assert set(independent.__all__) == {
        "ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error",
        "QueryBoundCampaignPrefixFailureClosureVerificationV2",
        "verify_query_bound_campaign_prefix_failure_closure_bytes_v2",
    }
    assert {
        subject.CLOSURE_DOMAIN,
        independent.VERIFICATION_PROFILE_DOMAIN,
        independent.VERIFICATION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_prefix_failure_closure_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignPrefixFailureClosureV2Error
    ):
        subject.QueryBoundCampaignPrefixFailureClosureV2(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            b"{}",
            ("4" * 64, "5" * 64),
            (),
            1,
            None,
            (),
        )


def test_independent_verifier_has_no_prefix_failure_or_campaign_runner_import() -> None:
    tree = ast.parse(Path(independent.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert (
        "acfqp.construction_k7_query_bound_campaign_prefix_failure_closure_v2"
        not in imported
    )
    assert (
        "acfqp.construction_k7_query_bound_preregistered_campaign_runner_v1"
        not in imported
    )


def test_prefix_failure_verification_is_not_caller_mintable() -> None:
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error
    ):
        independent.QueryBoundCampaignPrefixFailureClosureVerificationV2(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            1,
            "4" * 64,
            "5" * 64,
            "6" * 64,
            ("7" * 64, "8" * 64),
            ("9" * 64,),
            ("a" * 64, "b" * 64),
        )


def _logical_id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-campaign-prefix-failure-real-test:v2\x00"
        + label.encode()
    ).hexdigest()


def _occurrence_input(
    *,
    trace_raw: bytes,
    envelope,
    envelope_bytes: bytes,
    label: str,
    ordinal: int,
) -> prereg_v1.QueryBoundCampaignOccurrenceInputsV1:
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_logical_id(label),
        query_ordinal=ordinal,
    )
    root = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_bytes = canonical_json_bytes(root.to_document())
    overlay = overlay_v1.apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
    )
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    request = request_v1.prepare_query_bound_recovery_request_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
    )
    return prereg_v1.QueryBoundCampaignOccurrenceInputsV1(
        trace_raw,
        envelope_bytes,
        root_bytes,
        overlay_bytes,
        canonical_json_bytes(request.to_document()),
    )


def test_real_failure_after_first_commit_retains_certificate_and_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.environ.get("ACFQP_RUN_REAL_K7_CAMPAIGN_PREFIX_FAILURE_CLOSURE") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_CAMPAIGN_PREFIX_FAILURE_CLOSURE=1")
    repository_root = Path(__file__).parents[1]
    trace_raw = (
        repository_root
        / "markdown/local_artifacts/v075_k7_causal_recovery_trace_v1.json"
    ).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    inputs = tuple(
        _occurrence_input(
            trace_raw=trace_raw,
            envelope=envelope,
            envelope_bytes=envelope_bytes,
            label=f"later-failure-{index}",
            ordinal=index,
        )
        for index in (1, 2)
    )
    registration = prereg_v1.preregister_query_bound_campaign_v1(
        repository_root=repository_root,
        runtime_cas_root=tmp_path / "cas",
        occurrence_inputs=inputs,
        permutation_cap=2,
    )

    original_commit_event = subject.runner_v1._commit_event

    def commit_then_fail(**kwargs):
        event = original_commit_event(**kwargs)
        if kwargs["kind"] == "OCCURRENCE_COMMITTED" and kwargs["index"] == 2:
            raise RuntimeError("injected failure after first occurrence commit")
        return event

    monkeypatch.setattr(subject.runner_v1, "_commit_event", commit_then_fail)
    wrapper = tmp_path / "prefix-failure-run"
    closure = subject.run_query_bound_campaign_with_prefix_failure_closure_v2(
        registration,
        output_directory=wrapper,
    )
    assert type(closure) is subject.QueryBoundCampaignPrefixFailureClosureV2
    document = closure.to_document()
    assert document["completed_occurrence_count"] == 1
    assert document["logical_occurrence_count"] == 2
    assert document["plan_certificate_count"] == 1
    assert document["noncertificate_count"] == 1
    assert document["closure_denominator"] == 2
    assert document["construction_certificate_coverage_status"] == "FAIL"
    assert document["official_certificate_coverage_gate_status"] == "NOT_RUN"
    assert document["pending_occurrence_directory"] is None
    assert document["pending_occurrence_inventory"] == []
    assert document["occurrence_rows"][0]["terminal_class"] == "PLAN_CERTIFICATE"
    assert document["occurrence_rows"][1]["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["failure_path_campaign_closure_present"] is True
    assert document["campaign_orchestration_work_vector_present"] is False
    assert document["official_execution_allowed"] is False

    verification = independent.verify_query_bound_campaign_prefix_failure_closure_bytes_v2(
        closure.canonical_bytes,
        wrapper_directory=wrapper,
    )
    assert len(verification.completed_bundle_verification_ids) == 1
    assert verification.logical_occurrence_ids == tuple(
        row.logical_occurrence_id for row in registration.occurrences
    )

    attacked = document.copy()
    attacked_rows = [dict(row) for row in attacked["occurrence_rows"]]
    attacked_rows[0]["terminal_class"] = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    attacked_rows[0]["terminal_code"] = "PROTOCOL_FAILURE"
    attacked["occurrence_rows"] = attacked_rows
    payload = dict(attacked)
    payload.pop("query_bound_campaign_prefix_failure_closure_id")
    attacked["query_bound_campaign_prefix_failure_closure_id"] = content_id(
        subject.CLOSURE_DOMAIN,
        payload,
    )
    attacked_raw = canonical_json_bytes(attacked)
    closure_path = wrapper / subject.FAILURE_FILENAME
    closure_path.chmod(0o600)
    closure_path.write_bytes(attacked_raw)
    closure_path.chmod(0o400)
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignPrefixFailureClosureIndependentVerifierV2Error
    ):
        independent.verify_query_bound_campaign_prefix_failure_closure_bytes_v2(
            attacked_raw,
            wrapper_directory=wrapper,
        )
