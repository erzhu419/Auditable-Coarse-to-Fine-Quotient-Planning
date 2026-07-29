"""Exact production campaign reconciliation for V0-075.

The immutable production plan contains fifteen logical occurrences in
context-major order.  This authority accepts exactly those fifteen
production-scope occurrence results and their independently issued semantic
verifications, replays every result, preserves every certificate and
noncertificate, and derives all terminal and native online-work totals from
the verifications.

SOURCE reconstruction work is independently reloaded from the tracked public
source artifacts and charged exactly once outside all per-occurrence online
totals.  No target observer, private law, private salt, target callback,
caller-supplied total, scalar cost, or break-even value is accepted here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import stat
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_production_occurrence_authority_v1 as occurrence
from acfqp import v075_production_occurrence_plan_v1 as occurrence_plan
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_source_work_authority_v1 as public_source_work
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_tracked_source_authority_v1 as tracked_source


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_production_campaign_reconciliation_v1"

LOGICAL_OCCURRENCE_DENOMINATOR = (
    occurrence_plan.EXPECTED_OCCURRENCE_COUNT
)
SCIENTIFIC_ORDINALS = tuple(range(LOGICAL_OCCURRENCE_DENOMINATOR))
TRANSPORT_ORDINALS = tuple(
    range(1, LOGICAL_OCCURRENCE_DENOMINATOR + 1)
)
ARM_ORDER = occurrence_plan.REGISTERED_ARM_ORDER

TARGET_EXECUTION_OPENED = False
CALLER_SUMMARIES_ACCEPTED = False
CALLER_TOTALS_ACCEPTED = False
REORDERING_ACCEPTED = False

OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"

DOMAIN_TAGS = {
    "source_accounting": (
        "acfqp:v075-production-source-offline-accounting-once:v1"
    ),
    "occurrence": (
        "acfqp:v075-production-reconciled-occurrence:v1"
    ),
    "arm_accounting": (
        "acfqp:v075-production-arm-online-accounting:v1"
    ),
    "reconciliation": (
        "acfqp:v075-production-campaign-reconciliation:v1"
    ),
    "verification": (
        "acfqp:v075-production-campaign-reconciliation-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 production reconciliation domains overlap")


class V075ProductionCampaignReconciliationInvariantViolation(ValueError):
    """A production schedule, semantic result, or work identity was invalid."""


def _fail(message: str) -> None:
    raise V075ProductionCampaignReconciliationInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionCampaignReconciliationInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionCampaignReconciliationInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _read_tracked_regular_file_v1(
    repository_root: str | Path,
    relative_path: str,
    *,
    maximum_bytes: int,
) -> bytes:
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, TypeError, ValueError) as error:
        raise V075ProductionCampaignReconciliationInvariantViolation(
            "repository root is absent or malformed"
        ) from error
    if (
        not root.is_dir()
        or type(relative_path) is not str
        or not relative_path
        or relative_path.startswith("/")
        or ".." in relative_path.split("/")
    ):
        _fail("tracked source path is not one repository-relative file")
    candidate = root
    try:
        for component in relative_path.split("/"):
            candidate = candidate / component
            if candidate.is_symlink():
                _fail("tracked source path contains a symlink")
        before = candidate.stat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            _fail("tracked source artifact is absent, empty, or over cap")
        raw = candidate.read_bytes()
        after = candidate.stat()
    except OSError as error:
        raise V075ProductionCampaignReconciliationInvariantViolation(
            "tracked source artifact disappeared or became unreadable"
        ) from error
    if (
        len(raw) != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        _fail("tracked source artifact changed during its bound read")
    return raw


_ISSUER = object()
_VERIFIER_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionSourceOfflineAccountingOnceV1:
    """Replay-derived SOURCE work charged exactly once."""

    _issuer: object = field(repr=False, compare=False)
    plan_id: str
    tracked_source_bundle_id: str
    tracked_source_verification_id: str
    source_bundle: (
        public_source_work.V075VerifiedPublicSourceWorkBundleV1
    )
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.plan_id, "source accounting plan"),
            (
                self.tracked_source_bundle_id,
                "source accounting tracked bundle",
            ),
            (
                self.tracked_source_verification_id,
                "source accounting tracked verification",
            ),
        ):
            _cid(value, field_name)
        if (
            self._issuer is not _ISSUER
            or type(self.source_bundle)
            is not public_source_work.V075VerifiedPublicSourceWorkBundleV1
        ):
            _fail("SOURCE offline accounting was not replay-issued")
        object.__setattr__(
            self,
            "_accounting_id",
            _hash("source_accounting", self._payload()),
        )

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    @property
    def offline_draw_count(self) -> int:
        return self.source_bundle.offline_draw_count

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_source_offline_accounting_once.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan_id,
            "tracked_source_bundle_id": self.tracked_source_bundle_id,
            "tracked_source_verification_id": (
                self.tracked_source_verification_id
            ),
            "public_source_work_bundle_id": self.source_bundle.bundle_id,
            "source_work_materialization_id": (
                self.source_bundle.materialization_id
            ),
            "source_work_verification_id": (
                self.source_bundle.verification_id
            ),
            "source_replay_controller_status_id": (
                self.source_bundle.controller_status_id
            ),
            "source_campaign_counters_id": (
                self.source_bundle.campaign_counters_id
            ),
            "offline_draw_count": self.offline_draw_count,
            "offline_random_word_call_count": (
                self.source_bundle.offline_random_word_call_count
            ),
            "offline_rejection_count": (
                self.source_bundle.offline_rejection_count
            ),
            "source_offline_charge_count": 1,
            "source_offline_in_online_totals": False,
            "caller_total_accepted": False,
            "target_accessed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_bundle": self.source_bundle.to_document(),
            "accounting_id": self.accounting_id,
        }


def _replay_source_accounting_once_v1(
    *,
    repository_root: str | Path,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
) -> V075ProductionSourceOfflineAccountingOnceV1:
    try:
        tracked_bundle, tracked_verification = (
            tracked_source.verify_tracked_v075_source_authorities_v1(
                repository_root
            )
        )
    except Exception as error:
        raise V075ProductionCampaignReconciliationInvariantViolation(
            f"tracked SOURCE replay failed: {error}"
        ) from error
    if (
        tracked_bundle.bundle_id != plan.tracked_source_bundle_id
        or tracked_verification.verification_id
        != plan.tracked_source_verification_id
        or tracked_bundle.source_prior_adapter_id
        != plan.source_prior_transport.adapter_id
        or tracked_bundle.source_prior_verification_id
        != plan.source_prior_transport.verification_id
    ):
        _fail("tracked SOURCE graph differs from the immutable plan")
    paths = dict(tracked_source.TRACKED_ARTIFACT_PATHS)
    try:
        materialization = _read_tracked_regular_file_v1(
            repository_root,
            paths["SOURCE_WORK"],
            maximum_bytes=(
                public_source_work.MAX_MATERIALIZATION_BYTES
            ),
        )
        verification = _read_tracked_regular_file_v1(
            repository_root,
            paths["SOURCE_WORK_VERIFICATION"],
            maximum_bytes=public_source_work.MAX_VERIFICATION_BYTES,
        )
        controller_status = _read_tracked_regular_file_v1(
            repository_root,
            paths["SOURCE_REPLAY_STATUS"],
            maximum_bytes=public_source_work.MAX_STATUS_BYTES,
        )
        source_bundle = (
            public_source_work.verify_v075_public_source_work_artifacts_v1(
                materialization_raw=materialization,
                verification_raw=verification,
                controller_status_raw=controller_status,
            )
        )
    except Exception as error:
        if isinstance(
            error,
            V075ProductionCampaignReconciliationInvariantViolation,
        ):
            raise
        raise V075ProductionCampaignReconciliationInvariantViolation(
            f"public SOURCE-work replay failed: {error}"
        ) from error
    if source_bundle.bundle_id != tracked_bundle.public_source_work_bundle_id:
        _fail("public SOURCE-work bundle is stale or transplanted")
    return V075ProductionSourceOfflineAccountingOnceV1(
        _ISSUER,
        plan.plan_id,
        tracked_bundle.bundle_id,
        tracked_verification.verification_id,
        source_bundle,
    )


@dataclass(frozen=True, slots=True)
class V075ProductionReconciledOccurrenceV1:
    """One retained, verifier-derived production occurrence record."""

    _issuer: object = field(repr=False, compare=False)
    result: occurrence.V075ProductionOccurrenceAuthorityResultV1 = field(
        repr=False
    )
    verification: (
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1
    )
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.result)
            is not occurrence.V075ProductionOccurrenceAuthorityResultV1
            or type(self.verification)
            is not occurrence
            .V075ProductionOccurrenceAuthorityVerificationV1
            or self.result.authority_scope
            is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
            or self.verification.result_id != self.result.result_id
            or self.verification.occurrence_id
            != self.result.occurrence_id
            or self.verification.plan_id != self.result.plan.plan_id
            or self.verification.plan_entry_id
            != self.result.plan_entry.entry_id
            or self.verification.plan_verification_id
            != self.result.plan_verification.verification_id
            or self.verification.ipc_result_id
            != self.result.ipc_result.result_id
            or self.verification.ipc_actual_work_id
            != self.result.ipc_result.actual_work.work_id
            or self.verification.terminal_class
            is not self.result.terminal_class
            or self.verification.terminal_code
            is not self.result.terminal_code
            or self.verification.host_operational_planner_replay_count
            != 0
        ):
            _fail("production occurrence/result verification is transplanted")
        object.__setattr__(
            self,
            "_record_id",
            _hash("occurrence", self._payload()),
        )

    @property
    def entry(self) -> occurrence_plan.V075ProductionOccurrencePlanEntryV1:
        return self.result.plan_entry

    @property
    def record_id(self) -> str:
        return self._record_id

    def _payload(self) -> dict[str, Any]:
        value = self.verification
        return {
            "schema": (
                "acfqp.v075_production_reconciled_occurrence.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "result_id": value.result_id,
            "verification_id": value.verification_id,
            "occurrence_id": value.occurrence_id,
            "plan_entry_id": value.plan_entry_id,
            "context_id": self.entry.context_id,
            "context_ordinal": self.entry.context_ordinal,
            "arm": self.entry.arm.value,
            "arm_ordinal": self.entry.arm_ordinal,
            "scientific_ordinal": self.entry.scientific_ordinal,
            "transport_ordinal": self.entry.transport_ordinal,
            "terminal_class": value.terminal_class.value,
            "terminal_code": value.terminal_code.value,
            "ipc_result_id": value.ipc_result_id,
            "online_work_id": value.ipc_actual_work_id,
            "accepted_draw_count": value.accepted_draw_count,
            "outcome_aggregate_count": value.outcome_aggregate_count,
            "process_launch_count": value.process_launch_count,
            "child_message_count": value.child_message_count,
            "parent_message_count": value.parent_message_count,
            "batch_intent_count": value.batch_intent_count,
            "support_freeze_intent_count": (
                value.support_freeze_intent_count
            ),
            "round_begin_intent_count": value.round_begin_intent_count,
            "child_bytes_read": value.child_bytes_read,
            "parent_bytes_written": value.parent_bytes_written,
            "protocol_check_count": value.protocol_check_count,
            "host_operational_planner_replay_count": (
                value.host_operational_planner_replay_count
            ),
            "stderr_byte_count": value.stderr_byte_count,
            "child_exit_code": value.child_exit_code,
            "operational_transport_present": (
                value.operational_transport_present
            ),
            "exact_chain_present": value.exact_chain_present,
            "retained": True,
            "production_evidence": True,
            "caller_summary_accepted": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification": self.verification.to_document(),
            "record_id": self.record_id,
        }


_WORK_FIELDS = (
    "accepted_draw_count",
    "outcome_aggregate_count",
    "process_launch_count",
    "child_message_count",
    "parent_message_count",
    "batch_intent_count",
    "support_freeze_intent_count",
    "round_begin_intent_count",
    "child_bytes_read",
    "parent_bytes_written",
    "protocol_check_count",
    "host_operational_planner_replay_count",
    "stderr_byte_count",
)


def _sum_work(
    values: tuple[V075ProductionReconciledOccurrenceV1, ...],
    field_name: str,
) -> int:
    if field_name not in _WORK_FIELDS:
        _fail("unregistered online-work field")
    return sum(
        getattr(item.verification, field_name) for item in values
    )


@dataclass(frozen=True, slots=True)
class V075ProductionArmOnlineAccountingV1:
    """Three-context native online work for one immutable arm."""

    _issuer: object = field(repr=False, compare=False)
    arm: worker.V075WorkerArmV1
    occurrences: tuple[V075ProductionReconciledOccurrenceV1, ...]
    _accounting_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.occurrences) is not tuple
            or len(self.occurrences)
            != occurrence_plan.EXPECTED_CONTEXT_COUNT
            or any(
                type(item)
                is not V075ProductionReconciledOccurrenceV1
                for item in self.occurrences
            )
            or tuple(
                item.entry.context_ordinal for item in self.occurrences
            )
            != tuple(range(occurrence_plan.EXPECTED_CONTEXT_COUNT))
            or any(item.entry.arm is not self.arm for item in self.occurrences)
        ):
            _fail("per-arm online accounting is incomplete or reordered")
        object.__setattr__(
            self,
            "_accounting_id",
            _hash("arm_accounting", self._payload()),
        )

    @property
    def accounting_id(self) -> str:
        return self._accounting_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_arm_online_accounting.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "occurrence_record_ids": [
                item.record_id for item in self.occurrences
            ],
            "online_work_ids": [
                item.verification.ipc_actual_work_id
                for item in self.occurrences
            ],
            **{
                field_name: _sum_work(self.occurrences, field_name)
                for field_name in _WORK_FIELDS
            },
            "source_offline_work_included": False,
            "crn_draw_discount": 0,
            "caller_total_accepted": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


class V075ProductionCampaignValidityV1(str, Enum):
    VALID = "VALID"
    INVALID_PROTOCOL_OR_INTEGRITY = "INVALID_PROTOCOL_OR_INTEGRITY"


_INVALIDATING_TERMINALS = {
    occurrence.V075ProductionOccurrenceTerminalCodeV1.PROTOCOL_FAILURE,
    occurrence.V075ProductionOccurrenceTerminalCodeV1.INTEGRITY_FAILURE,
}


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignReconciliationV1:
    """The exact retained fifteen-occurrence production campaign."""

    _issuer: object = field(repr=False, compare=False)
    plan: occurrence_plan.V075ProductionOccurrencePlanV1 = field(
        repr=False
    )
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    )
    source_offline_accounting: (
        V075ProductionSourceOfflineAccountingOnceV1
    )
    occurrences: tuple[V075ProductionReconciledOccurrenceV1, ...]
    arm_online_accounting: tuple[
        V075ProductionArmOnlineAccountingV1, ...
    ]
    _reconciliation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        source = self.source_offline_accounting
        expected_arm = tuple(
            V075ProductionArmOnlineAccountingV1(
                _ISSUER,
                arm,
                tuple(
                    item
                    for item in self.occurrences
                    if item.entry.arm is arm
                ),
            )
            for arm in ARM_ORDER
        )
        source_role_ids = (
            source.accounting_id,
            source.tracked_source_bundle_id,
            source.tracked_source_verification_id,
            source.source_bundle.bundle_id,
            source.source_bundle.materialization_id,
            source.source_bundle.verification_id,
            source.source_bundle.controller_status_id,
            source.source_bundle.campaign_counters_id,
        )
        role_sets = (
            set(source_role_ids),
            {item.record_id for item in self.occurrences},
            {
                item.verification.result_id for item in self.occurrences
            },
            {
                item.verification.verification_id
                for item in self.occurrences
            },
            {
                item.verification.occurrence_id
                for item in self.occurrences
            },
            {
                item.verification.ipc_result_id
                for item in self.occurrences
            },
            {
                item.verification.ipc_actual_work_id
                for item in self.occurrences
            },
            {
                item.verification.lifecycle_closure_id
                for item in self.occurrences
            },
        )
        role_union: set[str] = set()
        incompatible_role_alias = False
        for identities in role_sets:
            if role_union & identities:
                incompatible_role_alias = True
                break
            role_union.update(identities)
        if (
            self._issuer is not _ISSUER
            or type(self.plan)
            is not occurrence_plan.V075ProductionOccurrencePlanV1
            or type(self.plan_verification)
            is not occurrence_plan
            .V075ProductionOccurrencePlanVerificationV1
            or self.plan_verification.plan_id != self.plan.plan_id
            or type(self.source_offline_accounting)
            is not V075ProductionSourceOfflineAccountingOnceV1
            or self.source_offline_accounting.plan_id != self.plan.plan_id
            or self.source_offline_accounting.tracked_source_bundle_id
            != self.plan.tracked_source_bundle_id
            or self.source_offline_accounting
            .tracked_source_verification_id
            != self.plan.tracked_source_verification_id
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != LOGICAL_OCCURRENCE_DENOMINATOR
            or any(
                type(item)
                is not V075ProductionReconciledOccurrenceV1
                for item in self.occurrences
            )
            or tuple(item.entry for item in self.occurrences)
            != self.plan.entries
            or tuple(
                item.entry.scientific_ordinal for item in self.occurrences
            )
            != SCIENTIFIC_ORDINALS
            or tuple(
                item.entry.transport_ordinal for item in self.occurrences
            )
            != TRANSPORT_ORDINALS
            or len(
                {
                    item.verification.result_id
                    for item in self.occurrences
                }
            )
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or len(
                {
                    item.verification.verification_id
                    for item in self.occurrences
                }
            )
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or len(
                {
                    item.verification.occurrence_id
                    for item in self.occurrences
                }
            )
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or self.arm_online_accounting != expected_arm
            or len(set(source_role_ids)) != len(source_role_ids)
            or incompatible_role_alias
            or _sum_work(
                self.occurrences,
                "host_operational_planner_replay_count",
            )
            != 0
        ):
            _fail(
                "production campaign omitted, duplicated, reordered, "
                "transplanted, or role-confused an occurrence"
            )
        object.__setattr__(
            self,
            "_reconciliation_id",
            _hash("reconciliation", self._payload()),
        )

    @property
    def reconciliation_id(self) -> str:
        return self._reconciliation_id

    @property
    def plan_certificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is occurrence.V075ProductionOccurrenceTerminalClassV1
            .PLAN_CERTIFICATE
            for item in self.occurrences
        )

    @property
    def infeasibility_certificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is occurrence.V075ProductionOccurrenceTerminalClassV1
            .INFEASIBILITY_CERTIFICATE
            for item in self.occurrences
        )

    @property
    def noncertificate_count(self) -> int:
        return sum(
            item.verification.terminal_class
            is occurrence.V075ProductionOccurrenceTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
            for item in self.occurrences
        )

    @property
    def invalidating_occurrence_ids(self) -> tuple[str, ...]:
        return tuple(
            item.verification.occurrence_id
            for item in self.occurrences
            if item.verification.terminal_code in _INVALIDATING_TERMINALS
        )

    @property
    def campaign_validity(self) -> V075ProductionCampaignValidityV1:
        return (
            V075ProductionCampaignValidityV1.VALID
            if not self.invalidating_occurrence_ids
            else V075ProductionCampaignValidityV1
            .INVALID_PROTOCOL_OR_INTEGRITY
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_campaign_reconciliation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan.plan_id,
            "plan_verification_id": (
                self.plan_verification.verification_id
            ),
            "remote_main_anchor_id": self.plan.remote_main_anchor_id,
            "final_preregistration_id": (
                self.plan.final_preregistration_id
            ),
            "target_tape_namespace_id": (
                self.plan.target_tape_namespace_id
            ),
            "public_family_generation_id": (
                self.plan.public_family_generation_id
            ),
            "source_offline_accounting_id": (
                self.source_offline_accounting.accounting_id
            ),
            "source_offline_charge_count": 1,
            "source_offline_draw_count": (
                self.source_offline_accounting.offline_draw_count
            ),
            "source_offline_in_online_totals": False,
            "occurrence_record_ids": [
                item.record_id for item in self.occurrences
            ],
            "arm_online_accounting_ids": [
                item.accounting_id for item in self.arm_online_accounting
            ],
            "campaign_online_work": {
                field_name: _sum_work(
                    self.occurrences,
                    field_name,
                )
                for field_name in _WORK_FIELDS
            },
            "logical_occurrence_denominator": (
                LOGICAL_OCCURRENCE_DENOMINATOR
            ),
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "noncertificate_count": self.noncertificate_count,
            "campaign_validity": self.campaign_validity.value,
            "invalidating_occurrence_ids": list(
                self.invalidating_occurrence_ids
            ),
            "protocol_failure_invalidates_campaign": True,
            "integrity_failure_invalidates_campaign": True,
            "all_occurrences_retained": True,
            "context_major_order": True,
            "replacement_allowed": False,
            "early_stop_allowed": False,
            "caller_summaries_accepted": False,
            "caller_totals_accepted": False,
            "target_execution_opened_by_reconciliation": False,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
            "official_scalar_cost": OFFICIAL_SCALAR_COST,
            "official_N_break_even": OFFICIAL_N_BREAK_EVEN,
            "workload_economics_gate_status": (
                WORKLOAD_ECONOMICS_GATE_STATUS
            ),
            "counter_completeness_gate_status": (
                COUNTER_COMPLETENESS_GATE_STATUS
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "plan": self.plan.to_document(),
            "plan_verification": self.plan_verification.to_document(),
            "source_offline_accounting": (
                self.source_offline_accounting.to_document()
            ),
            "occurrences": [
                item.to_document() for item in self.occurrences
            ],
            "arm_online_accounting": [
                item.to_document() for item in self.arm_online_accounting
            ],
            "reconciliation_id": self.reconciliation_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def reconcile_v075_production_campaign_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    plan: occurrence_plan.V075ProductionOccurrencePlanV1,
    plan_verification: (
        occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ),
    occurrence_results: Iterable[
        occurrence.V075ProductionOccurrenceAuthorityResultV1
    ],
    occurrence_verifications: Iterable[
        occurrence.V075ProductionOccurrenceAuthorityVerificationV1
    ],
) -> V075ProductionCampaignReconciliationV1:
    """Replay and retain the exact ordered fifteen-occurrence campaign."""

    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or type(plan)
        is not occurrence_plan.V075ProductionOccurrencePlanV1
        or type(plan_verification)
        is not occurrence_plan.V075ProductionOccurrencePlanVerificationV1
    ):
        _fail("production reconciliation requires exact plan authorities")
    replayed_plan, replayed_plan_verification = (
        occurrence_plan.verify_v075_production_occurrence_plan_bytes_v1(
            repository_root=repository_root,
            namespace=namespace,
            raw=plan.canonical_bytes,
        )
    )
    if (
        replayed_plan != plan
        or replayed_plan_verification != plan_verification
    ):
        _fail("production plan differs under exact independent replay")

    results = tuple(occurrence_results)
    verifications = tuple(occurrence_verifications)
    if (
        len(results) != LOGICAL_OCCURRENCE_DENOMINATOR
        or len(verifications) != LOGICAL_OCCURRENCE_DENOMINATOR
        or any(
            type(item)
            is not occurrence.V075ProductionOccurrenceAuthorityResultV1
            for item in results
        )
        or any(
            type(item)
            is not occurrence
            .V075ProductionOccurrenceAuthorityVerificationV1
            for item in verifications
        )
    ):
        _fail("production reconciliation requires exactly 15 typed pairs")

    reconciled: list[V075ProductionReconciledOccurrenceV1] = []
    for index, (result, verification) in enumerate(
        zip(results, verifications, strict=True)
    ):
        if (
            result.authority_scope
            is not lifecycle.V075LifecycleAuthorityScopeV1.PRODUCTION
            or result.plan != plan
            or result.plan_verification != plan_verification
            or result.plan_entry != plan.entries[index]
        ):
            _fail(
                "production occurrence sequence is reordered or transplanted"
            )
        try:
            replayed_verification = (
                occurrence
                .verify_v075_production_occurrence_authority_result_v1(
                    repository_root=repository_root,
                    namespace=namespace,
                    claimed=result,
                )
            )
        except Exception as error:
            raise V075ProductionCampaignReconciliationInvariantViolation(
                f"production occurrence {index} failed replay: {error}"
            ) from error
        if replayed_verification != verification:
            _fail(
                "provided occurrence verification differs from semantic replay"
            )
        reconciled.append(
            V075ProductionReconciledOccurrenceV1(
                _ISSUER,
                result,
                replayed_verification,
            )
        )

    canonical = tuple(reconciled)
    source_accounting = _replay_source_accounting_once_v1(
        repository_root=repository_root,
        plan=plan,
    )
    arm_accounting = tuple(
        V075ProductionArmOnlineAccountingV1(
            _ISSUER,
            arm,
            tuple(item for item in canonical if item.entry.arm is arm),
        )
        for arm in ARM_ORDER
    )
    return V075ProductionCampaignReconciliationV1(
        _ISSUER,
        plan,
        plan_verification,
        source_accounting,
        canonical,
        arm_accounting,
    )


@dataclass(frozen=True, slots=True)
class V075ProductionCampaignReconciliationVerificationV1:
    """Independent exact replay result for one production reconciliation."""

    _issuer: object = field(repr=False, compare=False)
    reconciliation_id: str
    replayed_reconciliation_id: str
    plan_id: str
    plan_verification_id: str
    source_offline_accounting_id: str
    occurrence_record_ids: tuple[str, ...]
    denominator: int
    plan_certificate_count: int
    infeasibility_certificate_count: int
    noncertificate_count: int
    campaign_validity: V075ProductionCampaignValidityV1
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.reconciliation_id, "verified reconciliation"),
            (
                self.replayed_reconciliation_id,
                "replayed reconciliation",
            ),
            (self.plan_id, "verified plan"),
            (self.plan_verification_id, "verified plan verification"),
            (
                self.source_offline_accounting_id,
                "verified SOURCE accounting",
            ),
            *(
                (item, "verified occurrence record")
                for item in self.occurrence_record_ids
            ),
        ):
            _cid(value, field_name)
        if (
            self._issuer is not _VERIFIER_ISSUER
            or self.reconciliation_id
            != self.replayed_reconciliation_id
            or type(self.occurrence_record_ids) is not tuple
            or len(self.occurrence_record_ids)
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or len(set(self.occurrence_record_ids))
            != LOGICAL_OCCURRENCE_DENOMINATOR
            or self.denominator != LOGICAL_OCCURRENCE_DENOMINATOR
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.plan_certificate_count,
                    self.infeasibility_certificate_count,
                    self.noncertificate_count,
                )
            )
            or (
                self.plan_certificate_count
                + self.infeasibility_certificate_count
                + self.noncertificate_count
            )
            != self.denominator
            or type(self.campaign_validity)
            is not V075ProductionCampaignValidityV1
        ):
            _fail("campaign verification is partial or caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_campaign_reconciliation_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "reconciliation_id": self.reconciliation_id,
            "replayed_reconciliation_id": (
                self.replayed_reconciliation_id
            ),
            "plan_id": self.plan_id,
            "plan_verification_id": self.plan_verification_id,
            "source_offline_accounting_id": (
                self.source_offline_accounting_id
            ),
            "occurrence_record_ids": list(self.occurrence_record_ids),
            "logical_occurrence_denominator": self.denominator,
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": (
                self.infeasibility_certificate_count
            ),
            "noncertificate_count": self.noncertificate_count,
            "campaign_validity": self.campaign_validity.value,
            "semantic_occurrence_replays": self.denominator,
            "caller_status_accepted": False,
            "caller_validity_accepted": False,
            "caller_totals_accepted": False,
            "all_occurrences_retained": True,
            "source_offline_charge_count": 1,
            "target_execution_opened_by_verifier": False,
            "valid": (
                self.campaign_validity
                is V075ProductionCampaignValidityV1.VALID
            ),
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_production_campaign_reconciliation_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    claimed: V075ProductionCampaignReconciliationV1,
) -> V075ProductionCampaignReconciliationVerificationV1:
    """Replay every authority edge and byte-compare the campaign artifact."""

    if type(claimed) is not V075ProductionCampaignReconciliationV1:
        _fail("campaign verifier requires the exact reconciliation type")
    replayed = reconcile_v075_production_campaign_v1(
        repository_root=repository_root,
        namespace=namespace,
        plan=claimed.plan,
        plan_verification=claimed.plan_verification,
        occurrence_results=tuple(
            item.result for item in claimed.occurrences
        ),
        occurrence_verifications=tuple(
            item.verification for item in claimed.occurrences
        ),
    )
    if (
        replayed.reconciliation_id != claimed.reconciliation_id
        or replayed.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("campaign reconciliation differs from exact replay")
    return V075ProductionCampaignReconciliationVerificationV1(
        _VERIFIER_ISSUER,
        claimed.reconciliation_id,
        replayed.reconciliation_id,
        claimed.plan.plan_id,
        claimed.plan_verification.verification_id,
        claimed.source_offline_accounting.accounting_id,
        tuple(item.record_id for item in claimed.occurrences),
        len(claimed.occurrences),
        claimed.plan_certificate_count,
        claimed.infeasibility_certificate_count,
        claimed.noncertificate_count,
        claimed.campaign_validity,
    )


__all__ = [
    "ARM_ORDER",
    "CALLER_SUMMARIES_ACCEPTED",
    "CALLER_TOTALS_ACCEPTED",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "DOMAIN_TAGS",
    "LOGICAL_OCCURRENCE_DENOMINATOR",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REORDERING_ACCEPTED",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ORDINALS",
    "TARGET_EXECUTION_OPENED",
    "TRANSPORT_ORDINALS",
    "V075ProductionArmOnlineAccountingV1",
    "V075ProductionCampaignReconciliationInvariantViolation",
    "V075ProductionCampaignReconciliationV1",
    "V075ProductionCampaignReconciliationVerificationV1",
    "V075ProductionCampaignValidityV1",
    "V075ProductionReconciledOccurrenceV1",
    "V075ProductionSourceOfflineAccountingOnceV1",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "reconcile_v075_production_campaign_v1",
    "verify_v075_production_campaign_reconciliation_v1",
]
