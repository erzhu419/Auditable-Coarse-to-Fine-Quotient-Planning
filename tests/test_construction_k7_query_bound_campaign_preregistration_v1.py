from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_campaign_preregistration_v1 as subject
from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as independent
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-campaign-preregistration-test:v1\x00"
        + label.encode()
    ).hexdigest()


def _input(
    *,
    trace_raw: bytes,
    envelope,
    envelope_bytes: bytes,
    label: str,
    ordinal: int,
) -> subject.QueryBoundCampaignOccurrenceInputsV1:
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id(label),
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
    return subject.QueryBoundCampaignOccurrenceInputsV1(
        trace_raw,
        envelope_bytes,
        root_bytes,
        overlay_bytes,
        canonical_json_bytes(request.to_document()),
    )


@pytest.fixture(scope="module")
def preregistered(tmp_path_factory):
    repository_root = Path(__file__).parents[1]
    trace_raw = (
        repository_root
        / "markdown/local_artifacts/v075_k7_causal_recovery_trace_v1.json"
    ).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    inputs = tuple(
        _input(
            trace_raw=trace_raw,
            envelope=envelope,
            envelope_bytes=envelope_bytes,
            label=f"preregistered-{index}",
            ordinal=index,
        )
        for index in (1, 2)
    )
    root = tmp_path_factory.mktemp("query-bound-campaign-preregistration")
    result = subject.preregister_query_bound_campaign_v1(
        repository_root=repository_root,
        runtime_cas_root=root / "cas",
        occurrence_inputs=inputs,
        permutation_cap=2,
    )
    return result, inputs


def test_public_surface_and_domains_freeze_preexecution_only() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundCampaignPreregistrationV1Error",
        "MAX_EXPLICIT_PERMUTATIONS",
        "QueryBoundCampaignInputBlobV1",
        "QueryBoundCampaignOccurrenceInputsV1",
        "QueryBoundCampaignPreregisteredOccurrenceV1",
        "QueryBoundCampaignPreregistrationV1",
        "QueryBoundCampaignWorkloadSpecV1",
        "preregister_query_bound_campaign_v1",
        "verify_query_bound_campaign_preregistration_v1",
    }
    assert {
        subject.INPUT_BLOB_DOMAIN,
        subject.OCCURRENCE_DOMAIN,
        subject.WORKLOAD_SPEC_DOMAIN,
        subject.PREREGISTRATION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_preregistration_embeds_source_inputs_and_denominator(
    preregistered,
) -> None:
    result, _inputs = preregistered
    verified = subject.verify_query_bound_campaign_preregistration_v1(result)
    document = verified.to_document()
    assert len(verified.occurrences) == 2
    assert len(verified.input_blobs) == 8
    assert len(set(document["ordered_logical_occurrence_ids"])) == 2
    assert document["registration_stage"] == subject.REGISTRATION_STAGE
    assert document["campaign_preregistration_present"] is True
    assert document["source_bytes_embedded"] is True
    assert document["preregistration_contains_execution_result"] is False
    assert document["execution_started_by_this_api"] is False
    assert document["scientific_campaign_closure_issued"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert len(bytes.fromhex(document["source_archive_bytes_hex"])) > 1_000_000
    for role in subject.COMMON_INPUT_ROLES:
        assert len(
            {
                dict(row.role_blobs)[role].blob_id
                for row in verified.occurrences
            }
        ) == 1


def test_preregistration_does_not_execute_the_occurrence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    preregistered,
) -> None:
    frozen, inputs = preregistered

    def forbidden(*_args, **_kwargs):
        raise AssertionError("pre-registration called the execution boundary")

    monkeypatch.setattr(
        subject.executor_v1,
        "execute_query_bound_accounted_v1",
        forbidden,
    )
    monkeypatch.setattr(
        subject.executor_v1,
        "prepare_query_bound_accounted_runtime_v1",
        lambda **_kwargs: frozen.runtime_preparation,
    )
    monkeypatch.setattr(
        subject,
        "_source_archive",
        lambda **_kwargs: (frozen.source_archive, frozen.source_module_bytes),
    )
    def cached_occurrence(*, index, blobs_by_digest, **_kwargs):
        row = frozen.occurrences[index - 1]
        for _role, blob in row.role_blobs:
            blobs_by_digest[hashlib.sha256(blob.canonical_bytes).hexdigest()] = blob
        return row

    monkeypatch.setattr(subject, "_semantic_occurrence", cached_occurrence)
    result = subject.preregister_query_bound_campaign_v1(
        repository_root=Path(__file__).parents[1],
        runtime_cas_root=tmp_path / "cas",
        occurrence_inputs=inputs,
        permutation_cap=2,
    )
    assert result.to_document()["execution_started_by_this_api"] is False


def test_duplicate_occurrence_input_is_rejected(preregistered, tmp_path: Path) -> None:
    _result, inputs = preregistered
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignPreregistrationV1Error
    ):
        subject.preregister_query_bound_campaign_v1(
            repository_root=Path(__file__).parents[1],
            runtime_cas_root=tmp_path / "cas",
            occurrence_inputs=(inputs[0], inputs[0]),
            permutation_cap=2,
        )


def test_process_local_replay_rejects_input_blob_mutation(preregistered) -> None:
    result, _inputs = preregistered
    target = result.input_blobs[0]
    original = target.canonical_bytes
    try:
        object.__setattr__(target, "canonical_bytes", b"{}")
        with pytest.raises(
            subject.ConstructionK7QueryBoundCampaignPreregistrationV1Error
        ):
            subject.verify_query_bound_campaign_preregistration_v1(result)
    finally:
        object.__setattr__(target, "canonical_bytes", original)


def test_types_are_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundCampaignPreregistrationV1Error
    ):
        subject.QueryBoundCampaignInputBlobV1(object(), b"{}")


def test_independent_verifier_has_no_producer_import() -> None:
    assert set(independent.__all__) == {
        "ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error",
        "QueryBoundCampaignPreregistrationVerificationV1",
        "verify_query_bound_campaign_preregistration_bytes_v1",
    }
    tree = ast.parse(Path(independent.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert (
        "acfqp.construction_k7_query_bound_campaign_preregistration_v1"
        not in imported
    )


def test_independent_verification_result_is_not_caller_mintable() -> None:
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error
    ):
        independent.QueryBoundCampaignPreregistrationVerificationV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
            "5" * 64,
            "6" * 64,
            "7" * 64,
            ("8" * 64, "9" * 64),
            ("a" * 64, "b" * 64),
            ("c" * 64,),
            "d" * 64,
            1,
        )


def test_independent_bytes_replay_closes_source_inputs_and_denominator(
    preregistered,
) -> None:
    result, _inputs = preregistered
    verification = independent.verify_query_bound_campaign_preregistration_bytes_v1(
        result.canonical_bytes
    )
    document = verification.to_document()
    assert document["embedded_source_archive_replayed"] is True
    assert document["all_scientific_input_chains_replayed"] is True
    assert document["ordered_denominator_replayed"] is True
    assert document["execution_result_present"] is False
    assert document["scientific_campaign_closure_issued"] is False
    assert document["official_execution_allowed"] is False


def test_independent_replay_rejects_fully_resigned_wrong_request_blob(
    preregistered,
) -> None:
    result, _inputs = preregistered
    document = loads_canonical_json(result.canonical_bytes)
    occurrence = document["preregistered_occurrences"][0]
    role = next(row for row in occurrence["input_roles"] if row["role"] == "RECOVERY_REQUEST")
    old_blob_id = role["campaign_input_blob_id"]
    blob = next(
        row
        for row in document["input_blobs"]
        if row["campaign_input_blob_id"] == old_blob_id
    )
    forged_raw = b"{}"
    blob_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_input_blob.v1",
        "schema_version": subject.SCHEMA_VERSION,
        "profile_key": subject.PROFILE_KEY,
        "canonical_json_bytes_hex": forged_raw.hex(),
        "byte_count": len(forged_raw),
        "sha256": hashlib.sha256(forged_raw).hexdigest(),
    }
    forged_blob_id = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN,
        blob_payload,
    )
    blob.clear()
    blob.update({**blob_payload, "campaign_input_blob_id": forged_blob_id})
    document["input_blobs"].sort(key=lambda row: row["campaign_input_blob_id"])
    role.update(
        {
            "campaign_input_blob_id": forged_blob_id,
            "sha256": hashlib.sha256(forged_raw).hexdigest(),
            "byte_count": len(forged_raw),
        }
    )
    occurrence_payload = dict(occurrence)
    occurrence_payload.pop("preregistered_occurrence_spec_id")
    occurrence["preregistered_occurrence_spec_id"] = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN,
        occurrence_payload,
    )
    workload = document["campaign_workload_spec"]
    workload["ordered_occurrence_spec_ids"][0] = occurrence[
        "preregistered_occurrence_spec_id"
    ]
    workload_payload = dict(workload)
    workload_payload.pop("campaign_workload_spec_id")
    workload["campaign_workload_spec_id"] = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN,
        workload_payload,
    )
    document["campaign_workload_spec_id"] = workload["campaign_workload_spec_id"]
    preregistration_payload = dict(document)
    preregistration_payload.pop("query_bound_campaign_preregistration_id")
    document["query_bound_campaign_preregistration_id"] = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN,
        preregistration_payload,
    )
    with pytest.raises(
        independent.ConstructionK7QueryBoundCampaignPreregistrationIndependentVerifierV1Error
    ):
        independent.verify_query_bound_campaign_preregistration_bytes_v1(
            canonical_json_bytes(document)
        )
