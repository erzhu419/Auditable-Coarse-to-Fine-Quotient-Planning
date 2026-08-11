from __future__ import annotations

import ast
import hashlib
import inspect
import os
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_query_bound_campaign_preregistration_v1 as prereg_v1
from acfqp import construction_k7_query_bound_preregistered_campaign_independent_verifier_v1 as independent
from acfqp import construction_k7_query_bound_preregistered_campaign_runner_v1 as subject
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def test_public_surface_and_domains_freeze_positive_path_boundary() -> None:
    assert set(subject.__all__) == {
        "ANALYSIS_FILENAME",
        "ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error",
        "PREREGISTRATION_FILENAME",
        "QueryBoundCampaignCommitEventV1",
        "QueryBoundPreregisteredCampaignOccurrenceV1",
        "QueryBoundPreregisteredCampaignResultV1",
        "RESULT_FILENAME",
        "run_query_bound_preregistered_campaign_v1",
        "verify_query_bound_preregistered_campaign_result_v1",
    }
    assert {
        subject.EVENT_DOMAIN,
        subject.OCCURRENCE_DOMAIN,
        subject.RESULT_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)


def test_registration_commit_precedes_occurrence_execution_in_source() -> None:
    source = inspect.getsource(subject.run_query_bound_preregistered_campaign_v1)
    assert source.index("_commit_file(root, PREREGISTRATION_FILENAME") < source.index(
        "executor_v1.execute_query_bound_accounted_v1"
    )
    assert source.index('kind="PREREGISTRATION_COMMITTED"') < source.index(
        "executor_v1.execute_query_bound_accounted_v1"
    )


def test_durable_writer_is_exclusive_and_exact(tmp_path: Path) -> None:
    root = tmp_path / "campaign"
    root.mkdir(mode=0o700)
    target = subject._commit_file(root, "record.json", b"{}")
    assert target.read_bytes() == b"{}"
    with pytest.raises(FileExistsError):
        subject._commit_file(root, "record.json", b"{}")


def test_commit_event_is_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error
    ):
        subject.QueryBoundCampaignCommitEventV1(
            object(),
            1,
            "PREREGISTRATION_COMMITTED",
            None,
            "1" * 64,
            "2" * 64,
            subject.PREREGISTRATION_FILENAME,
            "3" * 64,
            1,
            None,
            None,
        )


def test_runner_rejects_foreign_registration_before_output(tmp_path: Path) -> None:
    output = tmp_path / "output"
    with pytest.raises(
        subject.ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error
    ):
        subject.run_query_bound_preregistered_campaign_v1(
            object(),  # type: ignore[arg-type]
            output_directory=output,
        )
    assert not output.exists()


def test_result_verifier_rejects_foreign_values() -> None:
    with pytest.raises(
        subject.ConstructionK7QueryBoundPreregisteredCampaignRunnerV1Error
    ):
        subject.verify_query_bound_preregistered_campaign_result_v1(
            object(),  # type: ignore[arg-type]
            registration=object(),  # type: ignore[arg-type]
        )


def test_independent_verifier_has_no_campaign_producer_imports() -> None:
    assert set(independent.__all__) == {
        "ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error",
        "QueryBoundPreregisteredCampaignVerificationV1",
        "verify_query_bound_preregistered_campaign_directory_v1",
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
        "acfqp.construction_k7_query_bound_preregistered_campaign_runner_v1"
        not in imported
    )
    assert "acfqp.construction_k7_query_bound_campaign_preregistration_v1" not in imported
    assert "acfqp.construction_k7_query_bound_campaign_analysis_v1" not in imported


def test_independent_verification_result_is_not_caller_mintable() -> None:
    with pytest.raises(
        independent.ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error
    ):
        independent.QueryBoundPreregisteredCampaignVerificationV1(
            object(),
            "1" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
            "5" * 64,
            ("6" * 64,),
            ("7" * 64, "8" * 64),
            ("9" * 64, "a" * 64),
            "b" * 64,
            "c" * 64,
            "d" * 64,
            1,
        )


def _logical_id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-preregistered-campaign-real-test:v1\x00"
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


@pytest.fixture(scope="module")
def real_campaign(tmp_path_factory):
    if os.environ.get("ACFQP_RUN_REAL_K7_PREREGISTERED_CAMPAIGN") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_PREREGISTERED_CAMPAIGN=1")
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
            label=f"fresh-preregistered-{index}",
            ordinal=index,
        )
        for index in (1, 2)
    )
    root = tmp_path_factory.mktemp("query-bound-preregistered-campaign")
    registration = prereg_v1.preregister_query_bound_campaign_v1(
        repository_root=repository_root,
        runtime_cas_root=root / "cas",
        occurrence_inputs=inputs,
        permutation_cap=2,
    )
    output = root / "output"
    result = subject.run_query_bound_preregistered_campaign_v1(
        registration,
        output_directory=output,
    )
    return result, registration, output


def test_real_runner_consumes_registered_denominator_in_order(real_campaign) -> None:
    result, registration, output = real_campaign
    subject.verify_query_bound_preregistered_campaign_result_v1(
        result,
        registration=registration,
    )
    document = result.to_document()
    assert len(result.occurrences) == 2
    assert len(result.events) == 4
    assert document["campaign_preregistration_present"] is True
    assert document["preregistration_committed_before_first_occurrence"] is True
    assert document["all_registered_occurrences_executed_exactly_once"] is True
    assert document["scientific_planner_executed_for_every_occurrence"] is True
    assert document["scientific_campaign_closure_issued"] is False
    assert document["failure_path_campaign_closure_present"] is False
    assert document["campaign_orchestration_work_vector_present"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert (output / subject.PREREGISTRATION_FILENAME).is_file()


def test_real_campaign_directory_replays_without_producers(real_campaign) -> None:
    _result, _registration, output = real_campaign
    verified = independent.verify_query_bound_preregistered_campaign_directory_v1(
        output
    )
    document = verified.to_document()
    assert document["durable_preregistration_first_sequence_replayed"] is True
    assert document["all_registered_occurrence_directories_replayed"] is True
    assert document["all_registered_input_inventory_joins_replayed"] is True
    assert document["all_vector_prefixes_recomputed"] is True
    assert document["scientific_planner_recomputed_by_this_verifier"] is False
    assert document["scientific_campaign_closure_issued"] is False
    assert document["official_execution_allowed"] is False


def test_real_campaign_rejects_deleted_occurrence_event(
    real_campaign,
    tmp_path: Path,
) -> None:
    _result, _registration, output = real_campaign
    attacked = tmp_path / "attacked"
    shutil.copytree(output, attacked)
    (attacked / subject.EVENT_FILENAME_TEMPLATE.format(index=2)).unlink()
    with pytest.raises(
        independent.ConstructionK7QueryBoundPreregisteredCampaignIndependentVerifierV1Error
    ):
        independent.verify_query_bound_preregistered_campaign_directory_v1(attacked)
