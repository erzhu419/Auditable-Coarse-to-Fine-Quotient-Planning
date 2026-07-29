"""Fresh-only durable accounting journal for registered V0-072 attempts.

The journal preserves immutable byte prefixes and caught failures.  It is not
a checkpoint/resume mechanism: serialized route documents are not yet a
lossless execution authority, and no journal object may enter target seeds,
planning, certification, or evidence reuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import traceback
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_DOMAIN,
    V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_EVENT_DOMAIN,
    V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_OBJECT_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_fresh_only_durable_attempt_journal_v1"
JOURNAL_ROOT_RELATIVE_PATH = PurePosixPath(
    "artifacts/v072_attempt_journals"
)
EXPECTED_OCCURRENCE_COUNT = 15
CANONICAL_OUTPUT_REPOSITORY_PATH = (
    "artifacts/v072_registered_campaign_result_v1.json"
)
REPLACEMENT_ATTEMPT_ORDINAL = 2
PREDECESSOR_FAILURE_RECORD_ID = (
    "ca9159f19534f73291206b5a86d792f5a2336458afe521c46ed77171bfeda74f"
)
MAX_AUTHORIZED_ATTEMPTS_FOR_CHAIN = 1
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_EVENT_FILE = re.compile(r"([0-9]{4})_([0-9a-f]{64})\.json\Z")
_ACTIVE_WRITER: AttemptJournalWriterV1 | None = None


class V072AttemptJournalInvariantViolation(ValueError):
    """Raised when a journal write, identity, or replay is invalid."""


class AttemptJournalEventKindV1(str, Enum):
    ATTEMPT_OPENED = "ATTEMPT_OPENED"
    SOURCE_REPLAY_BOUND = "SOURCE_REPLAY_BOUND"
    OCCURRENCE_STARTED = "OCCURRENCE_STARTED"
    DIRECT_CHECKPOINT_COMPLETED = "DIRECT_CHECKPOINT_COMPLETED"
    OCCURRENCE_COMPLETED = "OCCURRENCE_COMPLETED"
    CAMPAIGN_COMPUTATION_COMPLETED = "CAMPAIGN_COMPUTATION_COMPLETED"
    OUTPUT_PUBLISHED = "OUTPUT_PUBLISHED"
    CAUGHT_FAILURE = "CAUGHT_FAILURE"


class AttemptJournalClosureV1(str, Enum):
    OUTPUT_PUBLISHED = "OUTPUT_PUBLISHED"
    CAUGHT_FAILURE = "CAUGHT_FAILURE"
    UNCLOSED_ABRUPT = "UNCLOSED_ABRUPT"


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072AttemptJournalInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _commit(value: Any, field: str) -> str:
    if type(value) is not str or _HEX40.fullmatch(value) is None:
        raise V072AttemptJournalInvariantViolation(
            f"{field} must be one lowercase 40-hex Git object ID"
        )
    return value


def _token(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        raise V072AttemptJournalInvariantViolation(
            f"{field} must be one nonempty canonical string"
        )
    return value


def _output_path(value: Any) -> str:
    token = _token(value, "journal output path")
    path = PurePosixPath(token)
    if (
        path.is_absolute()
        or str(path) != token
        or len(path.parts) < 2
        or path.parts[0] != "artifacts"
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V072AttemptJournalInvariantViolation(
            "journal output path must be canonical under artifacts/"
        )
    return token


def _unknown_tail() -> dict[str, Any]:
    return {
        "kind": "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY",
        "must_not_be_interpreted_as_zero": True,
    }


@dataclass(frozen=True, slots=True)
class AttemptJournalIdentityV1:
    authority_chain_id: str
    anchor_id: str
    anchor_commit_id: str
    anchor_tree_id: str
    source_reconstruction_recipe_id: str
    manifest_id: str
    final_preregistration_id: str
    environment_manifest_id: str
    execution_plan_id: str
    occurrence_ids: tuple[str, ...]
    output_repository_path: str
    profile_key: str = PROFILE_KEY

    def __post_init__(self) -> None:
        for value, field in (
            (self.authority_chain_id, "authority chain"),
            (self.anchor_id, "anchor"),
            (
                self.source_reconstruction_recipe_id,
                "source reconstruction recipe",
            ),
            (self.manifest_id, "manifest"),
            (self.final_preregistration_id, "final preregistration"),
            (self.environment_manifest_id, "environment manifest"),
            (self.execution_plan_id, "execution plan"),
        ):
            _cid(value, field)
        _commit(self.anchor_commit_id, "anchor commit")
        _commit(self.anchor_tree_id, "anchor tree")
        if (
            type(self.occurrence_ids) is not tuple
            or len(self.occurrence_ids) != EXPECTED_OCCURRENCE_COUNT
            or len(set(self.occurrence_ids)) != EXPECTED_OCCURRENCE_COUNT
        ):
            raise V072AttemptJournalInvariantViolation(
                "attempt journal must bind exactly 15 distinct occurrences"
            )
        for item in self.occurrence_ids:
            _cid(item, "occurrence")
        if (
            _output_path(self.output_repository_path)
            != CANONICAL_OUTPUT_REPOSITORY_PATH
        ):
            raise V072AttemptJournalInvariantViolation(
                "production attempt output path is not the ledger-frozen path"
            )
        if self.profile_key != PROFILE_KEY:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal profile changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_campaign_attempt_journal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": self.profile_key,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "anchor_commit_id": self.anchor_commit_id,
            "anchor_tree_id": self.anchor_tree_id,
            "source_reconstruction_recipe_id": (
                self.source_reconstruction_recipe_id
            ),
            "manifest_id": self.manifest_id,
            "final_preregistration_id": self.final_preregistration_id,
            "environment_manifest_id": self.environment_manifest_id,
            "execution_plan_id": self.execution_plan_id,
            "occurrence_ids": list(self.occurrence_ids),
            "logical_occurrence_denominator": EXPECTED_OCCURRENCE_COUNT,
            "output_repository_path": self.output_repository_path,
            "replacement_attempt_ordinal": REPLACEMENT_ATTEMPT_ORDINAL,
            "predecessor_failure_record_id": (
                PREDECESSOR_FAILURE_RECORD_ID
            ),
            "max_authorized_attempts_for_this_chain": (
                MAX_AUTHORIZED_ATTEMPTS_FOR_CHAIN
            ),
            "resume_allowed": False,
            "artifact_reuse_allowed": False,
            "scientific_input": False,
            "journal_identity_enters_target_seed": False,
            "lossless_execution_transport_claimed": False,
            "journal_work_lane": "PROVENANCE_NOT_ROUTE_WORK",
        }

    @property
    def attempt_id(self) -> str:
        return content_id(
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attempt_id": self.attempt_id}


def _strict_json_load(raw: bytes, *, context: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise V072AttemptJournalInvariantViolation(
                    f"{context} contains a duplicate JSON key"
                )
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
    ) as error:
        raise V072AttemptJournalInvariantViolation(
            f"{context} is not strict UTF-8 JSON"
        ) from error
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise V072AttemptJournalInvariantViolation(
            f"{context} is not canonical JSON"
        )
    return value


def _require_real_directory(path: Path, *, create: bool = False) -> Path:
    if create and not path.exists():
        path.mkdir(mode=0o700)
    if (
        not path.is_dir()
        or path.is_symlink()
        or path.resolve(strict=True) != path
    ):
        raise V072AttemptJournalInvariantViolation(
            "attempt journal directory is missing, linked, or noncanonical"
        )
    return path


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_new(path: Path, data: bytes) -> int:
    parent = _require_real_directory(path.parent)
    if path.exists() or path.is_symlink():
        raise V072AttemptJournalInvariantViolation(
            "attempt journal refuses to overwrite an existing path"
        )
    temporary = parent / (
        f".{path.name}.{secrets.token_hex(16)}.tmp"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as error:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal publication target already exists"
            ) from error
        _fsync_directory(parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return len(data)


def _safe_existing_file(path: Path) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise V072AttemptJournalInvariantViolation(
            "attempt journal file is missing"
        ) from error
    if (
        stat.S_ISREG(metadata.st_mode) is not True
        or path.is_symlink()
        or metadata.st_nlink != 1
    ):
        raise V072AttemptJournalInvariantViolation(
            "attempt journal file is linked or not a regular file"
        )
    return path.read_bytes()


class AttemptJournalWriterV1:
    """Single-use in-process writer for one fresh attempt directory."""

    __slots__ = (
        "identity",
        "repository_root",
        "attempt_directory",
        "objects_directory",
        "events_directory",
        "_next_sequence",
        "_previous_event_id",
        "_current_occurrence_ordinal",
        "_current_occurrence_id",
        "_current_occurrence_context_id",
        "_current_occurrence_arm",
        "_completed_occurrences",
        "_source_bound",
        "_computation_completed",
        "_terminal",
    )

    def __init__(
        self,
        repository_root: Path,
        identity: AttemptJournalIdentityV1,
    ) -> None:
        if type(identity) is not AttemptJournalIdentityV1:
            raise V072AttemptJournalInvariantViolation(
                "journal writer requires one exact identity"
            )
        root = repository_root.resolve(strict=True)
        artifacts = _require_real_directory(root / "artifacts")
        journal_root = artifacts / "v072_attempt_journals"
        if not journal_root.exists():
            _require_real_directory(journal_root, create=True)
            _fsync_directory(artifacts)
        else:
            _require_real_directory(journal_root)
        attempt = journal_root / identity.attempt_id
        if attempt.exists() or attempt.is_symlink():
            raise V072AttemptJournalInvariantViolation(
                "attempt journal already exists; resume and reuse are forbidden"
            )
        attempt.mkdir(mode=0o700)
        objects = attempt / "objects"
        events = attempt / "events"
        objects.mkdir(mode=0o700)
        events.mkdir(mode=0o700)
        _fsync_directory(attempt)
        _fsync_directory(journal_root)
        self.identity = identity
        self.repository_root = root
        self.attempt_directory = attempt
        self.objects_directory = objects
        self.events_directory = events
        self._next_sequence = 0
        self._previous_event_id: str | None = None
        self._current_occurrence_ordinal: int | None = None
        self._current_occurrence_id: str | None = None
        self._current_occurrence_context_id: str | None = None
        self._current_occurrence_arm: str | None = None
        self._completed_occurrences = 0
        self._source_bound = False
        self._computation_completed = False
        self._terminal = False
        manifest_bytes = canonical_json_bytes(identity.to_document())
        _atomic_write_new(attempt / "attempt.json", manifest_bytes)
        self._append(
            AttemptJournalEventKindV1.ATTEMPT_OPENED,
            {
                "attempt_id": identity.attempt_id,
                "registered_occurrence_denominator": 15,
            },
            (("attempt_manifest", identity.to_document()),),
        )

    def _put_object(
        self,
        role: str,
        document: Mapping[str, Any],
    ) -> tuple[dict[str, Any], int]:
        canonical_role = _token(role, "journal object role")
        if not isinstance(document, Mapping):
            raise V072AttemptJournalInvariantViolation(
                "journal object must be a mapping"
            )
        payload = {
            "schema": "acfqp.v072_attempt_journal_object.v1",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.identity.attempt_id,
            "role": canonical_role,
            "document": dict(document),
        }
        object_id = content_id(
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_OBJECT_DOMAIN,
            payload,
        )
        body = canonical_json_bytes({**payload, "object_id": object_id})
        path = self.objects_directory / f"{object_id}.json"
        if path.exists() or path.is_symlink():
            if _safe_existing_file(path) != body:
                raise V072AttemptJournalInvariantViolation(
                    "attempt journal CAS identity collided with different bytes"
                )
            bytes_written = 0
        else:
            bytes_written = _atomic_write_new(path, body)
        return (
            {"role": canonical_role, "object_id": object_id},
            bytes_written,
        )

    def _append(
        self,
        kind: AttemptJournalEventKindV1,
        metadata: Mapping[str, Any],
        objects: tuple[tuple[str, Mapping[str, Any]], ...] = (),
    ) -> str:
        if type(kind) is not AttemptJournalEventKindV1:
            raise V072AttemptJournalInvariantViolation(
                "journal event kind is not registered"
            )
        if self._terminal:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal is already terminal"
            )
        refs: list[dict[str, Any]] = []
        object_bytes = 0
        for role, document in objects:
            ref, written = self._put_object(role, document)
            refs.append(ref)
            object_bytes += written
        payload = {
            "schema": "acfqp.v072_attempt_journal_event.v1",
            "schema_version": SCHEMA_VERSION,
            "attempt_id": self.identity.attempt_id,
            "sequence_index": self._next_sequence,
            "previous_event_id": self._previous_event_id,
            "event_kind": kind.value,
            "metadata": dict(metadata),
            "object_refs": refs,
            "journal_accounting": {
                "object_bytes_written": object_bytes,
                "object_file_writes": len(refs),
                "event_file_writes": 1,
                "journal_work_lane": "PROVENANCE_NOT_ROUTE_WORK",
            },
        }
        event_id = content_id(
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_EVENT_DOMAIN,
            payload,
        )
        document = {**payload, "event_id": event_id}
        body = canonical_json_bytes(document)
        path = self.events_directory / (
            f"{self._next_sequence:04d}_{event_id}.json"
        )
        _atomic_write_new(path, body)
        self._next_sequence += 1
        self._previous_event_id = event_id
        if kind in (
            AttemptJournalEventKindV1.OUTPUT_PUBLISHED,
            AttemptJournalEventKindV1.CAUGHT_FAILURE,
        ):
            self._terminal = True
        return event_id

    def bind_source_replay(self, replay: Any) -> str:
        from acfqp import v072_source_reconstruction_recipe_v1 as source

        if (
            type(replay) is not source.SourceReconstructionReplayV1
            or replay.recipe_id
            != self.identity.source_reconstruction_recipe_id
            or self._source_bound
            or self._next_sequence != 1
        ):
            raise V072AttemptJournalInvariantViolation(
                "source replay journal binding is stale or out of order"
            )
        summary = {
            "schema": "acfqp.v072_attempt_source_replay_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "recipe_id": replay.recipe_id,
            "source_campaign_id": replay.source_campaign.campaign_id,
            "source_verification_id": (
                replay.source_verification.verification_id
            ),
            "source_archive_id": replay.archive.archive_id,
            "production_verification_id": (
                replay.production_verification.verification_id
            ),
            "independent_attestation_id": (
                replay.independent_attestation.verification_id
            ),
            "source_component_id": replay.component.component_id,
        }
        event_id = self._append(
            AttemptJournalEventKindV1.SOURCE_REPLAY_BOUND,
            summary,
        )
        self._source_bound = True
        return event_id

    def begin_occurrence(self, occurrence_plan: Any) -> str:
        from acfqp import v072_registered_campaign_consumer_v1 as consumer

        if (
            type(occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or not self._source_bound
            or self._current_occurrence_id is not None
            or self._completed_occurrences >= EXPECTED_OCCURRENCE_COUNT
        ):
            raise V072AttemptJournalInvariantViolation(
                "occurrence journal start is ill-typed or out of order"
            )
        ordinal = occurrence_plan.template.occurrence_ordinal
        if (
            ordinal != self._completed_occurrences
            or occurrence_plan.occurrence_id
            != self.identity.occurrence_ids[ordinal]
            or occurrence_plan.chain_id != self.identity.authority_chain_id
        ):
            raise V072AttemptJournalInvariantViolation(
                "occurrence journal start changed the registered schedule"
            )
        plan_document = {
            "schema": (
                "acfqp.v072_attempt_journal_occurrence_plan_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authority_chain_id": occurrence_plan.chain_id,
            "occurrence_id": occurrence_plan.occurrence_id,
            "template": occurrence_plan.template.to_document(),
            "resume_allowed": False,
            "replacement_allowed": False,
        }
        event_id = self._append(
            AttemptJournalEventKindV1.OCCURRENCE_STARTED,
            {
                "occurrence_ordinal": ordinal,
                "occurrence_id": occurrence_plan.occurrence_id,
                "context_id": occurrence_plan.template.context_id,
                "arm": occurrence_plan.template.arm,
                "route_kind": occurrence_plan.template.route_kind.value,
            },
            (("occurrence_plan_binding", plan_document),),
        )
        self._current_occurrence_ordinal = ordinal
        self._current_occurrence_id = occurrence_plan.occurrence_id
        self._current_occurrence_context_id = (
            occurrence_plan.template.context_id
        )
        self._current_occurrence_arm = occurrence_plan.template.arm
        return event_id

    def commit_direct_checkpoint(
        self,
        *,
        context_id: str,
        checkpoint_record: Any,
    ) -> str:
        from acfqp import (
            v072_registered_matched_direct_runtime_v1 as direct,
        )

        if (
            type(checkpoint_record)
            is not direct.RegisteredMatchedDirectCheckpointRecordV1
            or self._current_occurrence_id is None
            or self._current_occurrence_context_id != context_id
            or self._current_occurrence_arm != "MATCHED_DIRECT_GROUND"
        ):
            raise V072AttemptJournalInvariantViolation(
                "direct checkpoint journal binding is stale or ill-typed"
            )
        checkpoint = checkpoint_record.inventory_checkpoint
        audit = checkpoint_record.planner_result.audit
        checkpoint_summary = {
            "schema": (
                "acfqp.v072_attempt_journal_direct_checkpoint_summary.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "checkpoint_record_id": checkpoint_record.record_id,
            "inventory_checkpoint_id": checkpoint.checkpoint_id,
            "previous_inventory_checkpoint_id": (
                checkpoint.previous_checkpoint_id
            ),
            "direct_snapshot_id": checkpoint.direct_snapshot.snapshot_id,
            "model_attestation_id": checkpoint.model_attestation.attestation_id,
            "planner_status": checkpoint_record.planner_result.status.value,
            "audit_id": None if audit is None else audit.audit_id,
            "proof_verification_id": (
                None
                if checkpoint_record.proof_verification is None
                else checkpoint_record.proof_verification.verification_id
            ),
            "deterministic_policy_id": (
                None
                if checkpoint_record.deterministic_policy is None
                else checkpoint_record.deterministic_policy.policy_id
            ),
            "status": checkpoint_record.status.value,
            "work_id": checkpoint.work.work_id,
            "full_inventory_serialized": False,
            "lossless_execution_transport_claimed": False,
        }
        return self._append(
            AttemptJournalEventKindV1.DIRECT_CHECKPOINT_COMPLETED,
            {
                "occurrence_ordinal": self._current_occurrence_ordinal,
                "occurrence_id": self._current_occurrence_id,
                "context_id": context_id,
                "arm": self._current_occurrence_arm,
                "checkpoint": checkpoint_record.checkpoint,
                "checkpoint_record_id": checkpoint_record.record_id,
                "inventory_checkpoint_id": checkpoint.checkpoint_id,
                "work_id": checkpoint.work.work_id,
                "status": checkpoint_record.status.value,
            },
            (
                ("direct_checkpoint_summary", checkpoint_summary),
                (
                    "direct_checkpoint_work",
                    checkpoint.work.to_document(),
                ),
            ),
        )

    def complete_occurrence(
        self,
        *,
        occurrence_plan: Any,
        route_result: Any,
        terminal_authority: Any | None,
        exact_evaluation: Any | None,
    ) -> str:
        from acfqp import v072_registered_campaign_consumer_v1 as consumer
        from acfqp import (
            v072_registered_adaptive_quotient_runtime_v1 as adaptive,
        )
        from acfqp import (
            v072_registered_matched_direct_runtime_v1 as direct,
        )
        from acfqp import (
            v072_registered_operational_terminal_authority_v1 as terminal,
        )
        from acfqp import (
            v072_independent_exact_ground_evaluator_v1 as evaluator,
        )

        if (
            type(occurrence_plan)
            is not consumer.RegisteredOccurrenceExecutionPlanV1
            or occurrence_plan.occurrence_id != self._current_occurrence_id
            or occurrence_plan.template.occurrence_ordinal
            != self._current_occurrence_ordinal
        ):
            raise V072AttemptJournalInvariantViolation(
                "occurrence completion changed the active occurrence"
            )
        if (
            type(route_result)
            is adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1
        ):
            execution = route_result.execution
            route_summary = {
                "schema": (
                    "acfqp.v072_attempt_journal_adaptive_route_summary.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "verified_result_id": route_result.verified_result_id,
                "execution_result_id": execution.result_id,
                "independent_verification_id": (
                    route_result.independent_verification_id
                ),
                "occurrence_id": execution.occurrence_plan.occurrence_id,
                "context_id": execution.context.context_id,
                "arm": execution.occurrence_plan.template.arm,
                "epoch_ids": [item.epoch_id for item in execution.epochs],
                "planner_component_result_ids": [
                    item.component_result_id
                    for item in execution.planner_results
                ],
                "selector_closure_ids": [
                    item.closure_id for item in execution.selector_closures
                ],
                "status": execution.status.value,
                "certificate_id": execution.certificate_id,
                "adapter_status": execution.adapter_status.value,
                "work_id": execution.work.work_id,
                "full_route_serialized": False,
                "lossless_execution_transport_claimed": False,
            }
            objects: list[tuple[str, Mapping[str, Any]]] = [
                ("adaptive_route_summary", route_summary),
                ("adaptive_route_work", execution.work.to_document()),
            ]
            route_result_id = route_result.verified_result_id
        elif (
            type(route_result)
            is direct.RegisteredMatchedDirectOccurrenceResultV1
        ):
            route_summary = {
                "schema": (
                    "acfqp.v072_attempt_journal_direct_route_summary.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "result_id": route_result.result_id,
                "occurrence_plan_id": route_result.occurrence_plan_id,
                "context_id": route_result.context_id,
                "checkpoint_record_ids": [
                    item.record_id
                    for item in route_result.checkpoint_records
                ],
                "terminal_class": route_result.terminal_class.value,
                "terminal_code": route_result.terminal_code.value,
                "stopped_checkpoint": route_result.stopped_checkpoint,
                "physical_row_count": route_result.physical_row_count,
                "acquisition_sample_total": (
                    route_result.acquisition_sample_total
                ),
                "deterministic_verifier_replay_total": (
                    route_result.deterministic_verifier_replay_total
                ),
                "access_audit_id": route_result.access_audit.audit_id,
                "full_route_serialized": False,
                "lossless_execution_transport_claimed": False,
            }
            objects = [
                ("direct_route_summary", route_summary),
                (
                    "direct_route_access_audit",
                    route_result.access_audit.to_document(),
                ),
            ]
            route_result_id = route_result.result_id
        else:
            raise V072AttemptJournalInvariantViolation(
                "occurrence journal received an unknown route result type"
            )
        terminal_id: str | None = None
        evaluation_id: str | None = None
        if terminal_authority is not None:
            if (
                type(terminal_authority)
                is not terminal.RegisteredOperationalTerminalAuthorityResultV1
            ):
                raise V072AttemptJournalInvariantViolation(
                    "occurrence journal received a foreign terminal authority"
                )
            bundle = terminal_authority.evaluator_bundle
            objects.append(
                (
                    "operational_terminal_authority",
                    {
                        "schema": (
                            "acfqp.v072_attempt_journal_operational_"
                            "terminal_authority.v1"
                        ),
                        "schema_version": SCHEMA_VERSION,
                        "verified_runtime_adapter_id": (
                            terminal_authority.verified_runtime_adapter_id
                        ),
                        "mint_authority_id": (
                            terminal_authority.mint_authority_id
                        ),
                        "evaluator_bundle_id": bundle.bundle_id,
                        "occurrence_id": (
                            bundle.operational_terminal.occurrence.occurrence_id
                        ),
                        "operational_terminal_id": (
                            bundle.operational_terminal.terminal_id
                        ),
                        "selected_policy_id": (
                            bundle.selected_policy.selected_policy_id
                        ),
                        "access_audit": (
                            terminal_authority.access_audit.to_document()
                        ),
                        "authority_result_id": (
                            terminal_authority.authority_result_id
                        ),
                    },
                )
            )
            terminal_id = terminal_authority.authority_result_id
        if exact_evaluation is not None:
            if (
                type(exact_evaluation)
                is not evaluator.RegisteredIndependentExactGroundEvaluationResultV1
            ):
                raise V072AttemptJournalInvariantViolation(
                    "occurrence journal received a foreign exact evaluation"
                )
            objects.append(
                (
                    "exact_evaluation_summary",
                    {
                        "schema": (
                            "acfqp.v072_attempt_journal_exact_evaluation_"
                            "summary.v1"
                        ),
                        "schema_version": SCHEMA_VERSION,
                        "result_id": exact_evaluation.result_id,
                        "occurrence": (
                            exact_evaluation.occurrence.to_document()
                        ),
                        "status": exact_evaluation.status.value,
                        "selected_expected_reward": (
                            exact_evaluation.selected_expected_reward
                        ),
                        "selected_failure_probability": (
                            exact_evaluation.selected_failure_probability
                        ),
                        "regret": exact_evaluation.regret,
                        "normalized_regret": (
                            exact_evaluation.normalized_regret
                        ),
                        "risk_pass": exact_evaluation.risk_pass,
                        "regret_pass": exact_evaluation.regret_pass,
                        "certificate_metrics_pass": (
                            exact_evaluation.certificate_metrics_pass
                        ),
                        "work_id": exact_evaluation.work.work_id,
                        "full_evaluation_serialized": False,
                        "lossless_execution_transport_claimed": False,
                    },
                )
            )
            objects.append(
                (
                    "exact_evaluation_work",
                    exact_evaluation.work.to_document(),
                )
            )
            evaluation_id = exact_evaluation.result_id
        event_id = self._append(
            AttemptJournalEventKindV1.OCCURRENCE_COMPLETED,
            {
                "occurrence_ordinal": self._current_occurrence_ordinal,
                "occurrence_id": self._current_occurrence_id,
                "context_id": self._current_occurrence_context_id,
                "arm": self._current_occurrence_arm,
                "route_result_id": route_result_id,
                "terminal_authority_id": terminal_id,
                "exact_evaluation_id": evaluation_id,
                "completed_occurrence_count": self._completed_occurrences + 1,
                "registered_occurrence_denominator": 15,
            },
            tuple(objects),
        )
        self._completed_occurrences += 1
        self._current_occurrence_ordinal = None
        self._current_occurrence_id = None
        self._current_occurrence_context_id = None
        self._current_occurrence_arm = None
        return event_id

    def commit_computation_result(self, execution_result: Any) -> str:
        from acfqp import v072_registered_campaign_consumer_v1 as consumer

        if (
            type(execution_result)
            is not consumer.RegisteredCampaignExecutionResultV1
            or self._completed_occurrences != EXPECTED_OCCURRENCE_COUNT
            or self._current_occurrence_id is not None
            or execution_result.execution_plan.plan_id
            != self.identity.execution_plan_id
            or self._computation_completed
        ):
            raise V072AttemptJournalInvariantViolation(
                "campaign computation journal closure is partial or stale"
            )
        computation_summary = {
            "schema": (
                "acfqp.v072_attempt_journal_campaign_computation_summary.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "execution_result_id": execution_result.execution_result_id,
            "execution_plan_id": execution_result.execution_plan.plan_id,
            "complete_bundle_id": execution_result.complete_bundle.bundle_id,
            "endpoint_verification_id": (
                execution_result.endpoint_verification.verification_id
            ),
            "access_audit_id": execution_result.access_audit.audit_id,
            "logical_occurrence_denominator": 15,
            "registered_v072_endpoints_pass": (
                execution_result.endpoint_verification
                .registered_v072_endpoints_pass
            ),
            "full_campaign_result_serialized": False,
            "lossless_execution_transport_claimed": False,
        }
        event_id = self._append(
            AttemptJournalEventKindV1.CAMPAIGN_COMPUTATION_COMPLETED,
            {
                "execution_result_id": execution_result.execution_result_id,
                "completed_occurrence_count": 15,
                "endpoint_verified": True,
            },
            (
                ("campaign_computation_summary", computation_summary),
                (
                    "campaign_endpoint_verification",
                    execution_result.endpoint_verification.to_document(),
                ),
                (
                    "campaign_access_audit",
                    execution_result.access_audit.to_document(),
                ),
            ),
        )
        self._computation_completed = True
        return event_id

    def commit_output_published(
        self,
        *,
        output_path: Path,
        execution_result_id: str,
    ) -> str:
        result_id = _cid(execution_result_id, "published execution result")
        expected = (
            self.repository_root
            / PurePosixPath(self.identity.output_repository_path)
        )
        if (
            not self._computation_completed
            or output_path != expected
            or not output_path.is_file()
            or output_path.is_symlink()
        ):
            raise V072AttemptJournalInvariantViolation(
                "published output is missing, linked, or out of order"
            )
        raw = _safe_existing_file(output_path)
        document = _strict_json_load(raw, context="published campaign output")
        if document.get("execution_result_id") != result_id:
            raise V072AttemptJournalInvariantViolation(
                "published output result identity changed"
            )
        return self._append(
            AttemptJournalEventKindV1.OUTPUT_PUBLISHED,
            {
                "execution_result_id": result_id,
                "output_repository_path": (
                    self.identity.output_repository_path
                ),
                "output_sha256": hashlib.sha256(raw).hexdigest(),
                "output_byte_count": len(raw),
                "scientific_endpoint_transport_complete": True,
            },
        )

    def commit_caught_failure(
        self,
        error: BaseException,
        *,
        runner_phase: str,
    ) -> str:
        if not isinstance(error, BaseException):
            raise V072AttemptJournalInvariantViolation(
                "caught failure requires one BaseException"
            )
        phase = _token(runner_phase, "runner phase")
        formatted = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        diagnostic = {
            "schema": "acfqp.v072_attempt_caught_failure_diagnostic.v1",
            "schema_version": SCHEMA_VERSION,
            "exception_type": (
                f"{type(error).__module__}.{type(error).__qualname__}"
            ),
            "exception_message": str(error),
            "traceback": formatted,
            "traceback_sha256": hashlib.sha256(
                formatted.encode("utf-8")
            ).hexdigest(),
        }
        return self._append(
            AttemptJournalEventKindV1.CAUGHT_FAILURE,
            {
                "runner_phase": phase,
                "last_durable_event_id": self._previous_event_id,
                "active_occurrence_ordinal": (
                    self._current_occurrence_ordinal
                ),
                "active_occurrence_id": self._current_occurrence_id,
                "active_context_id": self._current_occurrence_context_id,
                "active_arm": self._current_occurrence_arm,
                "completed_occurrence_count": self._completed_occurrences,
                "registered_occurrence_denominator": 15,
                "unknown_tail_work": _unknown_tail(),
                "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
                "terminal_code": "PROTOCOL_FAILURE",
                "plan_or_infeasibility_credit_allowed": False,
                "scientific_endpoint_read_allowed": False,
            },
            (("caught_failure_diagnostic", diagnostic),),
        )

    @property
    def terminal(self) -> bool:
        return self._terminal


@dataclass(frozen=True, slots=True)
class AttemptJournalVerificationV1:
    attempt_id: str
    event_ids: tuple[str, ...]
    object_ids: tuple[str, ...]
    completed_occurrence_count: int
    closure: AttemptJournalClosureV1
    valid_hash_chain: bool = True
    resume_allowed: bool = False
    artifact_reuse_allowed: bool = False
    scientific_input: bool = False
    lossless_execution_transport_claimed: bool = False


def _identity_from_document(
    document: Mapping[str, Any],
) -> AttemptJournalIdentityV1:
    try:
        identity = AttemptJournalIdentityV1(
            authority_chain_id=document["authority_chain_id"],
            anchor_id=document["anchor_id"],
            anchor_commit_id=document["anchor_commit_id"],
            anchor_tree_id=document["anchor_tree_id"],
            source_reconstruction_recipe_id=(
                document["source_reconstruction_recipe_id"]
            ),
            manifest_id=document["manifest_id"],
            final_preregistration_id=document["final_preregistration_id"],
            environment_manifest_id=document["environment_manifest_id"],
            execution_plan_id=document["execution_plan_id"],
            occurrence_ids=tuple(document["occurrence_ids"]),
            output_repository_path=document["output_repository_path"],
            profile_key=document["profile_key"],
        )
    except (KeyError, TypeError) as error:
        raise V072AttemptJournalInvariantViolation(
            "attempt journal manifest is malformed"
        ) from error
    if dict(document) != identity.to_document():
        raise V072AttemptJournalInvariantViolation(
            "attempt journal manifest semantics or identity changed"
        )
    return identity


def verify_attempt_journal_v1(
    attempt_directory: Path,
    *,
    expected_identity: AttemptJournalIdentityV1,
) -> AttemptJournalVerificationV1:
    """Verify one externally bound immutable prefix without granting reuse."""

    if type(expected_identity) is not AttemptJournalIdentityV1:
        raise V072AttemptJournalInvariantViolation(
            "journal verification requires one external exact identity"
        )
    attempt = _require_real_directory(attempt_directory)
    if {item.name for item in attempt.iterdir()} != {
        "attempt.json",
        "events",
        "objects",
    }:
        raise V072AttemptJournalInvariantViolation(
            "attempt journal contains missing or extra top-level paths"
        )
    events_directory = _require_real_directory(attempt / "events")
    objects_directory = _require_real_directory(attempt / "objects")
    manifest = _strict_json_load(
        _safe_existing_file(attempt / "attempt.json"),
        context="attempt journal manifest",
    )
    identity = _identity_from_document(manifest)
    if (
        identity != expected_identity
        or attempt.name != identity.attempt_id
    ):
        raise V072AttemptJournalInvariantViolation(
            "attempt journal differs from its externally expected identity"
        )

    event_paths = sorted(events_directory.iterdir(), key=lambda item: item.name)
    if not event_paths:
        raise V072AttemptJournalInvariantViolation(
            "attempt journal lacks ATTEMPT_OPENED"
        )
    prior: str | None = None
    event_ids: list[str] = []
    referenced_objects: list[str] = []
    completed = 0
    active_ordinal: int | None = None
    source_bound = False
    computation_complete = False
    terminal: AttemptJournalClosureV1 | None = None
    for sequence, path in enumerate(event_paths):
        match = _EVENT_FILE.fullmatch(path.name)
        if match is None or int(match.group(1)) != sequence:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal event sequence is gapped or noncanonical"
            )
        document = _strict_json_load(
            _safe_existing_file(path),
            context="attempt journal event",
        )
        claimed_id = _cid(document.get("event_id"), "journal event")
        payload = dict(document)
        payload.pop("event_id")
        expected_id = content_id(
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_EVENT_DOMAIN,
            payload,
        )
        if (
            claimed_id != expected_id
            or claimed_id != match.group(2)
            or document.get("attempt_id") != identity.attempt_id
            or document.get("sequence_index") != sequence
            or document.get("previous_event_id") != prior
        ):
            raise V072AttemptJournalInvariantViolation(
                "attempt journal event hash chain changed"
            )
        try:
            kind = AttemptJournalEventKindV1(document["event_kind"])
            refs = document["object_refs"]
            metadata = document["metadata"]
        except (KeyError, TypeError, ValueError) as error:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal event is malformed"
            ) from error
        if type(refs) is not list or type(metadata) is not dict:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal refs or metadata are malformed"
            )
        for ref in refs:
            if (
                type(ref) is not dict
                or set(ref) != {"role", "object_id"}
            ):
                raise V072AttemptJournalInvariantViolation(
                    "attempt journal object reference is malformed"
                )
            object_id = _cid(ref["object_id"], "journal object")
            object_path = objects_directory / f"{object_id}.json"
            object_document = _strict_json_load(
                _safe_existing_file(object_path),
                context="attempt journal object",
            )
            object_payload = dict(object_document)
            object_payload.pop("object_id", None)
            if (
                set(object_document)
                != {
                    "schema",
                    "schema_version",
                    "attempt_id",
                    "role",
                    "document",
                    "object_id",
                }
                or object_document.get("schema")
                != "acfqp.v072_attempt_journal_object.v1"
                or object_document.get("schema_version") != SCHEMA_VERSION
                or object_document.get("object_id") != object_id
                or object_document.get("attempt_id") != identity.attempt_id
                or object_document.get("role") != ref["role"]
                or type(object_document.get("document")) is not dict
                or content_id(
                    V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_OBJECT_DOMAIN,
                    object_payload,
                )
                != object_id
            ):
                raise V072AttemptJournalInvariantViolation(
                    "attempt journal object content identity changed"
                )
            referenced_objects.append(object_id)

        if sequence == 0:
            if (
                kind is not AttemptJournalEventKindV1.ATTEMPT_OPENED
                or tuple(item["role"] for item in refs)
                != ("attempt_manifest",)
            ):
                raise V072AttemptJournalInvariantViolation(
                    "attempt journal does not begin with ATTEMPT_OPENED"
                )
        elif kind is AttemptJournalEventKindV1.ATTEMPT_OPENED:
            raise V072AttemptJournalInvariantViolation(
                "ATTEMPT_OPENED may occur exactly once"
            )
        elif kind is AttemptJournalEventKindV1.SOURCE_REPLAY_BOUND:
            if (
                sequence != 1
                or refs
                or source_bound
                or active_ordinal is not None
                or completed
            ):
                raise V072AttemptJournalInvariantViolation(
                    "source replay event is duplicated or out of order"
                )
            source_bound = True
        elif kind is AttemptJournalEventKindV1.OCCURRENCE_STARTED:
            ordinal = metadata.get("occurrence_ordinal")
            if (
                not source_bound
                or active_ordinal is not None
                or ordinal != completed
                or metadata.get("occurrence_id")
                != identity.occurrence_ids[completed]
            ):
                raise V072AttemptJournalInvariantViolation(
                    "occurrence start changed the registered order"
                )
            active_ordinal = ordinal
        elif (
            kind
            is AttemptJournalEventKindV1.DIRECT_CHECKPOINT_COMPLETED
        ):
            if (
                active_ordinal is None
                or metadata.get("occurrence_ordinal") != active_ordinal
                or metadata.get("arm") != "MATCHED_DIRECT_GROUND"
            ):
                raise V072AttemptJournalInvariantViolation(
                    "direct checkpoint lacks its active occurrence"
                )
        elif kind is AttemptJournalEventKindV1.OCCURRENCE_COMPLETED:
            if (
                active_ordinal is None
                or metadata.get("occurrence_ordinal") != active_ordinal
                or metadata.get("completed_occurrence_count")
                != completed + 1
            ):
                raise V072AttemptJournalInvariantViolation(
                    "occurrence completion is missing or out of order"
                )
            completed += 1
            active_ordinal = None
        elif (
            kind
            is AttemptJournalEventKindV1.CAMPAIGN_COMPUTATION_COMPLETED
        ):
            if (
                completed != EXPECTED_OCCURRENCE_COUNT
                or active_ordinal is not None
                or computation_complete
            ):
                raise V072AttemptJournalInvariantViolation(
                    "campaign computation closed a partial attempt"
                )
            computation_complete = True
        elif kind is AttemptJournalEventKindV1.OUTPUT_PUBLISHED:
            if not computation_complete:
                raise V072AttemptJournalInvariantViolation(
                    "output was published before complete computation"
                )
            terminal = AttemptJournalClosureV1.OUTPUT_PUBLISHED
        elif kind is AttemptJournalEventKindV1.CAUGHT_FAILURE:
            if (
                metadata.get("terminal_class")
                != "ATTEMPT_CLOSURE_NONCERTIFICATE"
                or metadata.get("terminal_code") != "PROTOCOL_FAILURE"
                or metadata.get("plan_or_infeasibility_credit_allowed")
                is not False
                or metadata.get("scientific_endpoint_read_allowed")
                is not False
                or metadata.get("registered_occurrence_denominator") != 15
            ):
                raise V072AttemptJournalInvariantViolation(
                    "caught failure was reclassified or removed from denominator"
                )
            terminal = AttemptJournalClosureV1.CAUGHT_FAILURE
        if terminal is not None and sequence != len(event_paths) - 1:
            raise V072AttemptJournalInvariantViolation(
                "attempt journal contains events after terminal closure"
            )
        prior = claimed_id
        event_ids.append(claimed_id)

    object_names = {
        item.name
        for item in objects_directory.iterdir()
        if item.is_file() and not item.is_symlink()
    }
    expected_object_names = {
        f"{item}.json" for item in referenced_objects
    }
    if object_names != expected_object_names or any(
        item.is_symlink() or not item.is_file()
        for item in objects_directory.iterdir()
    ):
        raise V072AttemptJournalInvariantViolation(
            "attempt journal CAS contains missing, extra, or linked objects"
        )
    closure = (
        terminal
        if terminal is not None
        else AttemptJournalClosureV1.UNCLOSED_ABRUPT
    )
    return AttemptJournalVerificationV1(
        identity.attempt_id,
        tuple(event_ids),
        tuple(sorted(set(referenced_objects))),
        completed,
        closure,
    )


def _production_identity(
    authority_chain: Any,
    execution_plan: Any,
    output_repository_path: str,
) -> AttemptJournalIdentityV1:
    from acfqp import v072_final_preregistration_authority_v1 as final
    from acfqp import v072_registered_campaign_consumer_v1 as consumer

    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(execution_plan)
        is not consumer.RegisteredCampaignExecutionPlanV1
        or type(authority_chain.remote_main_anchor)
        is not final.V072RemoteMainAnchorV1
        or execution_plan.authority_chain_id != authority_chain.chain_id
    ):
        raise V072AttemptJournalInvariantViolation(
            "production journal requires the exact campaign authority and plan"
        )
    claim = authority_chain.remote_main_anchor.claim
    bindings = authority_chain.manifest.global_bindings
    return AttemptJournalIdentityV1(
        authority_chain_id=authority_chain.chain_id,
        anchor_id=authority_chain.remote_main_anchor.anchor_id,
        anchor_commit_id=claim.commit_id,
        anchor_tree_id=claim.tree_id,
        source_reconstruction_recipe_id=(
            claim.source_reconstruction_recipe_id
        ),
        manifest_id=claim.manifest_id,
        final_preregistration_id=claim.final_preregistration_id,
        environment_manifest_id=bindings["environment_manifest_id"],
        execution_plan_id=execution_plan.plan_id,
        occurrence_ids=tuple(
            item.occurrence_id for item in execution_plan.occurrences
        ),
        output_repository_path=output_repository_path,
    )


def open_registered_campaign_attempt_journal_v1(
    *,
    repository_root: Path,
    authority_chain: Any,
    execution_plan: Any,
    output_repository_path: str,
) -> AttemptJournalWriterV1:
    """Open the one fresh production journal; never load or resume one."""

    global _ACTIVE_WRITER
    if _ACTIVE_WRITER is not None:
        raise V072AttemptJournalInvariantViolation(
            "another V0-072 attempt journal is already active"
        )
    identity = _production_identity(
        authority_chain,
        execution_plan,
        output_repository_path,
    )
    writer = AttemptJournalWriterV1(repository_root, identity)
    _ACTIVE_WRITER = writer
    return writer


def active_attempt_journal_v1(
    *,
    authority_chain: Any,
    execution_plan: Any | None = None,
) -> AttemptJournalWriterV1 | None:
    """Return only the matching internal sink; never reconstruct from bytes."""

    writer = _ACTIVE_WRITER
    if writer is None:
        return None
    chain_id = getattr(authority_chain, "chain_id", None)
    plan_id = (
        None if execution_plan is None else getattr(execution_plan, "plan_id", None)
    )
    if (
        chain_id != writer.identity.authority_chain_id
        or (
            plan_id is not None
            and plan_id != writer.identity.execution_plan_id
        )
    ):
        raise V072AttemptJournalInvariantViolation(
            "active attempt journal was transplanted across authority or plan"
        )
    return writer


def close_active_attempt_journal_v1(
    writer: AttemptJournalWriterV1,
) -> None:
    global _ACTIVE_WRITER
    if writer is not _ACTIVE_WRITER:
        raise V072AttemptJournalInvariantViolation(
            "cannot close a foreign attempt journal"
        )
    _ACTIVE_WRITER = None


def open_test_attempt_journal_v1(
    repository_root: Path,
    identity: AttemptJournalIdentityV1,
) -> AttemptJournalWriterV1:
    """Test-only fresh writer with no production authority or target access."""

    return AttemptJournalWriterV1(repository_root, identity)


__all__ = [
    "AttemptJournalClosureV1",
    "AttemptJournalEventKindV1",
    "AttemptJournalIdentityV1",
    "AttemptJournalVerificationV1",
    "AttemptJournalWriterV1",
    "CANONICAL_OUTPUT_REPOSITORY_PATH",
    "EXPECTED_OCCURRENCE_COUNT",
    "JOURNAL_ROOT_RELATIVE_PATH",
    "MAX_AUTHORIZED_ATTEMPTS_FOR_CHAIN",
    "PREDECESSOR_FAILURE_RECORD_ID",
    "PROFILE_KEY",
    "REPLACEMENT_ATTEMPT_ORDINAL",
    "SCHEMA_VERSION",
    "V072AttemptJournalInvariantViolation",
    "active_attempt_journal_v1",
    "close_active_attempt_journal_v1",
    "open_registered_campaign_attempt_journal_v1",
    "open_test_attempt_journal_v1",
    "verify_attempt_journal_v1",
]
