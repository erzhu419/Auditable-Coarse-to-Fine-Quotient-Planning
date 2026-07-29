from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v072_registered_campaign_attempt_journal_v1 as journal
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _root(tmp_path: Path) -> Path:
    root = tmp_path.resolve()
    (root / "artifacts").mkdir()
    return root


def _identity(label: str = "base") -> journal.AttemptJournalIdentityV1:
    return journal.AttemptJournalIdentityV1(
        authority_chain_id=_id(f"{label}:chain"),
        anchor_id=_id(f"{label}:anchor"),
        anchor_commit_id="1" * 40,
        anchor_tree_id="2" * 40,
        source_reconstruction_recipe_id=_id(f"{label}:recipe"),
        manifest_id=_id(f"{label}:manifest"),
        final_preregistration_id=_id(f"{label}:preregistration"),
        environment_manifest_id=_id(f"{label}:environment"),
        execution_plan_id=_id(f"{label}:plan"),
        occurrence_ids=tuple(
            _id(f"{label}:occurrence:{index}") for index in range(15)
        ),
        output_repository_path=journal.CANONICAL_OUTPUT_REPOSITORY_PATH,
    )


def _append_source(
    writer: journal.AttemptJournalWriterV1,
) -> None:
    writer._append(
        journal.AttemptJournalEventKindV1.SOURCE_REPLAY_BOUND,
        {
            "recipe_id": writer.identity.source_reconstruction_recipe_id,
        },
    )
    writer._source_bound = True


def _real_plan_writer(
    tmp_path: Path,
    label: str,
) -> tuple[
    journal.AttemptJournalWriterV1,
    consumer.RegisteredCampaignExecutionPlanV1,
]:
    chain_id = _id(f"{label}:chain")
    occurrences = tuple(
        consumer.RegisteredOccurrenceExecutionPlanV1(chain_id, template)
        for template in consumer.registered_occurrence_templates_v1()
    )
    plan = consumer.RegisteredCampaignExecutionPlanV1(
        chain_id,
        occurrences,
    )
    base = _identity(label)
    identity = journal.AttemptJournalIdentityV1(
        authority_chain_id=chain_id,
        anchor_id=base.anchor_id,
        anchor_commit_id=base.anchor_commit_id,
        anchor_tree_id=base.anchor_tree_id,
        source_reconstruction_recipe_id=(
            base.source_reconstruction_recipe_id
        ),
        manifest_id=base.manifest_id,
        final_preregistration_id=base.final_preregistration_id,
        environment_manifest_id=base.environment_manifest_id,
        execution_plan_id=plan.plan_id,
        occurrence_ids=tuple(item.occurrence_id for item in occurrences),
        output_repository_path=base.output_repository_path,
    )
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        identity,
    )
    _append_source(writer)
    return writer, plan


def _append_occurrence(
    writer: journal.AttemptJournalWriterV1,
    ordinal: int,
    *,
    direct_checkpoint: int | None = None,
) -> None:
    occurrence_id = writer.identity.occurrence_ids[ordinal]
    arm = (
        "MATCHED_DIRECT_GROUND"
        if direct_checkpoint is not None
        else "SOURCE_CONSENSUS_PRIOR"
    )
    writer._append(
        journal.AttemptJournalEventKindV1.OCCURRENCE_STARTED,
        {
            "occurrence_ordinal": ordinal,
            "occurrence_id": occurrence_id,
            "context_id": _id(f"context:{ordinal // 5}"),
            "arm": arm,
            "route_kind": (
                "MATCHED_DIRECT_GROUND"
                if direct_checkpoint is not None
                else "ADAPTIVE_QUOTIENT"
            ),
        },
        (("occurrence_plan", {"occurrence_id": occurrence_id}),),
    )
    writer._current_occurrence_ordinal = ordinal
    writer._current_occurrence_id = occurrence_id
    writer._current_occurrence_context_id = _id(
        f"context:{ordinal // 5}"
    )
    writer._current_occurrence_arm = arm
    if direct_checkpoint is not None:
        writer._append(
            (
                journal.AttemptJournalEventKindV1
                .DIRECT_CHECKPOINT_COMPLETED
            ),
            {
                "occurrence_ordinal": ordinal,
                "occurrence_id": occurrence_id,
                "context_id": writer._current_occurrence_context_id,
                "arm": arm,
                "checkpoint": direct_checkpoint,
            },
            (
                (
                    "direct_checkpoint_record",
                    {
                        "checkpoint": direct_checkpoint,
                        "work_id": _id(f"work:{ordinal}:{direct_checkpoint}"),
                    },
                ),
            ),
        )
    writer._append(
        journal.AttemptJournalEventKindV1.OCCURRENCE_COMPLETED,
        {
            "occurrence_ordinal": ordinal,
            "occurrence_id": occurrence_id,
            "context_id": writer._current_occurrence_context_id,
            "arm": arm,
            "completed_occurrence_count": ordinal + 1,
        },
        (
            (
                "route_result",
                {
                    "occurrence_id": occurrence_id,
                    "work_id": _id(f"work:{ordinal}"),
                },
            ),
        ),
    )
    writer._completed_occurrences += 1
    writer._current_occurrence_ordinal = None
    writer._current_occurrence_id = None
    writer._current_occurrence_context_id = None
    writer._current_occurrence_arm = None


def test_failure_retains_completed_prefix_and_unknown_tail(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity(),
    )
    _append_source(writer)
    for ordinal in range(3):
        _append_occurrence(writer, ordinal)
    try:
        raise RuntimeError("injected failure after occurrence three")
    except RuntimeError as error:
        writer.commit_caught_failure(
            error,
            runner_phase="CAMPAIGN_EXECUTION",
        )

    verification = journal.verify_attempt_journal_v1(
        writer.attempt_directory,
        expected_identity=writer.identity,
    )

    assert verification.closure is journal.AttemptJournalClosureV1.CAUGHT_FAILURE
    assert verification.completed_occurrence_count == 3
    assert verification.resume_allowed is False
    assert verification.artifact_reuse_allowed is False
    final = json.loads(
        sorted(writer.events_directory.iterdir())[-1].read_text()
    )
    assert final["metadata"]["registered_occurrence_denominator"] == 15
    assert (
        final["metadata"]["unknown_tail_work"]["kind"]
        == "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY"
    )
    assert (
        final["metadata"]["plan_or_infeasibility_credit_allowed"]
        is False
    )


def test_direct_checkpoint_is_durable_before_occurrence_completion(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("direct"),
    )
    _append_source(writer)
    _append_occurrence(writer, 0, direct_checkpoint=4096)
    verification = journal.verify_attempt_journal_v1(
        writer.attempt_directory,
        expected_identity=writer.identity,
    )
    kinds = [
        json.loads(path.read_text())["event_kind"]
        for path in sorted(writer.events_directory.iterdir())
    ]

    assert "DIRECT_CHECKPOINT_COMPLETED" in kinds
    assert kinds.index("DIRECT_CHECKPOINT_COMPLETED") < kinds.index(
        "OCCURRENCE_COMPLETED"
    )
    assert verification.completed_occurrence_count == 1
    assert verification.closure is journal.AttemptJournalClosureV1.UNCLOSED_ABRUPT


def test_real_occurrence_plan_starts_with_compact_typed_binding(
    tmp_path: Path,
) -> None:
    writer, plan = _real_plan_writer(tmp_path, "real-plan")
    occurrences = plan.occurrences

    writer.begin_occurrence(occurrences[0])

    event = json.loads(
        sorted(writer.events_directory.iterdir())[-1].read_text()
    )
    assert event["event_kind"] == "OCCURRENCE_STARTED"
    assert event["object_refs"][0]["role"] == "occurrence_plan_binding"
    binding_path = (
        writer.objects_directory
        / f"{event['object_refs'][0]['object_id']}.json"
    )
    binding = json.loads(binding_path.read_text())["document"]
    assert binding["occurrence_id"] == occurrences[0].occurrence_id
    assert binding["template"]["template_id"] == (
        occurrences[0].template.template_id
    )
    assert binding["resume_allowed"] is False


def test_exact_adaptive_route_uses_compact_work_summary(
    tmp_path: Path,
) -> None:
    writer, plan = _real_plan_writer(tmp_path, "compact-adaptive")
    occurrence = plan.occurrences[0]
    writer.begin_occurrence(occurrence)
    work = SimpleNamespace(
        work_id=_id("adaptive-work"),
        to_document=lambda: {
            "schema": "test.adaptive_work.v1",
            "work_id": _id("adaptive-work"),
        },
    )
    execution = object.__new__(adaptive.RegisteredAdaptiveOccurrenceResultV1)
    for name, value in (
        ("occurrence_plan", occurrence),
        ("context", SimpleNamespace(context_id=occurrence.template.context_id)),
        ("epochs", (SimpleNamespace(epoch_id=_id("epoch")),)),
        (
            "planner_results",
            (SimpleNamespace(component_result_id=_id("planner")),),
        ),
        ("selector_closures", ()),
        ("status", adaptive.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER),
        (
            "adapter_status",
            (
                adaptive.RegisteredAdaptiveGroundAdapterStatusV1
                .NOT_APPLICABLE_NONCERTIFICATE
            ),
        ),
        ("work", work),
        ("_certificate_id", None),
        ("_result_id", _id("adaptive-result")),
    ):
        object.__setattr__(execution, name, value)
    route = object.__new__(
        adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
    )
    object.__setattr__(route, "execution", execution)
    object.__setattr__(
        route,
        "independent_verification",
        SimpleNamespace(verification_id=_id("adaptive-verification")),
    )
    object.__setattr__(route, "_verified_result_id", _id("verified-route"))

    writer.complete_occurrence(
        occurrence_plan=occurrence,
        route_result=route,
        terminal_authority=None,
        exact_evaluation=None,
    )

    event = json.loads(
        sorted(writer.events_directory.iterdir())[-1].read_text()
    )
    roles = {item["role"] for item in event["object_refs"]}
    assert roles == {"adaptive_route_summary", "adaptive_route_work"}
    assert event["metadata"]["route_result_id"] == _id("verified-route")


def test_fresh_only_open_rejects_resume_and_reuse(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    identity = _identity("fresh")
    journal.open_test_attempt_journal_v1(root, identity)

    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="resume and reuse are forbidden",
    ):
        journal.open_test_attempt_journal_v1(root, identity)


def test_attempt_slot_binds_predecessor_and_rejects_output_path_bypass() -> None:
    document = _identity("slot").to_document()
    assert document["replacement_attempt_ordinal"] == 2
    assert document["predecessor_failure_record_id"] == (
        journal.PREDECESSOR_FAILURE_RECORD_ID
    )
    assert document["max_authorized_attempts_for_this_chain"] == 1
    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="ledger-frozen path",
    ):
        journal.AttemptJournalIdentityV1(
            authority_chain_id=_id("foreign-output:chain"),
            anchor_id=_id("foreign-output:anchor"),
            anchor_commit_id="1" * 40,
            anchor_tree_id="2" * 40,
            source_reconstruction_recipe_id=_id("foreign-output:recipe"),
            manifest_id=_id("foreign-output:manifest"),
            final_preregistration_id=_id("foreign-output:prereg"),
            environment_manifest_id=_id("foreign-output:environment"),
            execution_plan_id=_id("foreign-output:plan"),
            occurrence_ids=tuple(
                _id(f"foreign-output:occurrence:{index}")
                for index in range(15)
            ),
            output_repository_path="artifacts/alternate.json",
        )


def test_deleted_or_reordered_event_breaks_hash_chain(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("delete"),
    )
    _append_source(writer)
    _append_occurrence(writer, 0)
    paths = sorted(writer.events_directory.iterdir())
    paths[1].unlink()

    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="gapped",
    ):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=writer.identity,
        )


def test_event_and_cas_byte_tampering_fail_closed(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("tamper"),
    )
    _append_source(writer)
    event = sorted(writer.events_directory.iterdir())[-1]
    document = json.loads(event.read_text())
    document["metadata"]["recipe_id"] = _id("foreign-recipe")
    event.write_bytes(canonical_json_bytes(document))

    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="hash chain changed",
    ):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=writer.identity,
        )

    cas_root = tmp_path / "cas"
    cas_root.mkdir()
    writer_two = journal.open_test_attempt_journal_v1(
        _root(cas_root),
        _identity("cas"),
    )
    object_path = sorted(writer_two.objects_directory.iterdir())[0]
    object_document = json.loads(object_path.read_text())
    object_document["role"] = "foreign_role"
    object_path.write_bytes(canonical_json_bytes(object_document))
    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="content identity changed",
    ):
        journal.verify_attempt_journal_v1(
            writer_two.attempt_directory,
            expected_identity=writer_two.identity,
        )


def test_identical_cas_object_is_referenced_without_duplicate_write(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("cas-reuse"),
    )
    document = {"schema": "test.shared_work.v1", "value": 7}

    first_ref, first_bytes = writer._put_object("shared_work", document)
    second_ref, second_bytes = writer._put_object("shared_work", document)

    assert first_ref == second_ref
    assert first_bytes > 0
    assert second_bytes == 0


def test_missing_cas_and_symlink_attacks_fail_closed(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("cas-missing"),
    )
    _append_source(writer)
    _append_occurrence(writer, 0)
    object_path = sorted(writer.objects_directory.iterdir())[-1]
    object_path.unlink()

    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="file is missing",
    ):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=writer.identity,
        )

    foreign = tmp_path / "foreign.json"
    foreign.write_text("{}")
    object_path.symlink_to(foreign)
    with pytest.raises(journal.V072AttemptJournalInvariantViolation):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=writer.identity,
        )


def test_duplicate_json_key_and_extra_object_are_rejected(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("duplicate"),
    )
    event = sorted(writer.events_directory.iterdir())[0]
    raw = event.read_text()
    event.write_text(raw[:-1] + ',"event_id":"' + "0" * 64 + '"}')
    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="duplicate JSON key",
    ):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=writer.identity,
        )

    extra_root = tmp_path / "extra"
    extra_root.mkdir()
    writer_two = journal.open_test_attempt_journal_v1(
        _root(extra_root),
        _identity("extra"),
    )
    (writer_two.objects_directory / f"{'f' * 64}.json").write_text("{}")
    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="extra",
    ):
        journal.verify_attempt_journal_v1(
            writer_two.attempt_directory,
            expected_identity=writer_two.identity,
        )


def test_journal_identity_never_enters_scientific_authority(
    tmp_path: Path,
) -> None:
    identity = _identity("boundary")
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        identity,
    )
    document = identity.to_document()
    verification = journal.verify_attempt_journal_v1(
        writer.attempt_directory,
        expected_identity=writer.identity,
    )

    assert document["resume_allowed"] is False
    assert document["artifact_reuse_allowed"] is False
    assert document["scientific_input"] is False
    assert document["journal_identity_enters_target_seed"] is False
    assert verification.scientific_input is False
    assert verification.lossless_execution_transport_claimed is False


def test_self_consistent_foreign_journal_fails_external_identity_binding(
    tmp_path: Path,
) -> None:
    writer = journal.open_test_attempt_journal_v1(
        _root(tmp_path),
        _identity("expected"),
    )

    with pytest.raises(
        journal.V072AttemptJournalInvariantViolation,
        match="externally expected identity",
    ):
        journal.verify_attempt_journal_v1(
            writer.attempt_directory,
            expected_identity=_identity("foreign"),
        )
