"""Phase-3E logical-occurrence retry and campaign closure contracts.

This module implements only the FQ8/FQ9 closure layer.  A route attempt is not
the campaign denominator: all attempts, failed local work, fallback work, and a
single authorized rebuild remain charged to one registered logical occurrence.
The module classifies certificates but deliberately keeps official execution
locked and scalar economics unset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.phase3e_ids import (
    CAMPAIGN_OCCURRENCE_CLOSURE_DOMAIN,
    CAMPAIGN_SUMMARY_DOMAIN,
    LOGICAL_OCCURRENCE_DOMAIN,
    REBUILD_EVENT_DOMAIN,
    REBUILD_POLICY_DOMAIN,
    ROUTE_ATTEMPT_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    SCHEMA_VERSION,
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp.semantic_verification_v1 import (
    SemanticVerificationResultV1,
    SemanticVerificationV1Error,
    require_terminal_classification_result_v1,
)


WORKLOAD_ECONOMICS_GATE_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_GATE_NOT_RUN = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
SCALAR_GATE_NOT_RUN = "NOT_RUN"
CERTIFICATE_COVERAGE_PASS = "PASS"
CERTIFICATE_COVERAGE_FAIL = "FAIL"


_CAMPAIGN_SUMMARY_AUTHORITY = object()
_CAMPAIGN_CLOSURE_AUTHORITY = object()
_REBUILD_EVENT_AUTHORITY = object()


class CampaignV1Error(ValueError):
    """An FQ8/FQ9 occurrence, retry, or closure invariant was violated."""


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CampaignV1Error(f"{field} must be a full Phase-3E content ID") from error


def _positive(value: Any, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise CampaignV1Error(f"{field} must be a positive exact integer")
    return value


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise CampaignV1Error(f"{field} must be a nonnegative exact integer")
    return value


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise CampaignV1Error(str(error)) from error


def _verify_id(
    document: Mapping[str, Any], id_field: str, domain: str, payload: Mapping[str, Any]
) -> None:
    supplied = _cid(document[id_field], id_field)
    if supplied != content_id(domain, payload):
        raise CampaignV1Error(f"{id_field} content ID mismatch")


ContentRef = str | TypedNotApplicable


def _ref(value: Any, field: str, *, allow_not_applicable: bool) -> ContentRef:
    if isinstance(value, TypedNotApplicable):
        if not allow_not_applicable:
            raise CampaignV1Error(f"{field} cannot be NOT_APPLICABLE")
        return value
    return _cid(value, field)


def _parse_ref(value: Any, field: str, *, allow_not_applicable: bool) -> ContentRef:
    if isinstance(value, Mapping):
        return _ref(
            TypedNotApplicable.from_dict(value),
            field,
            allow_not_applicable=allow_not_applicable,
        )
    return _ref(value, field, allow_not_applicable=allow_not_applicable)


def _ref_dict(value: ContentRef) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


def _terminal_class(value: Any) -> TerminalClass:
    try:
        return TerminalClass(value)
    except (TypeError, ValueError) as error:
        raise CampaignV1Error(f"invalid terminal class {value!r}") from error


def _terminal_code(value: Any) -> TerminalCode:
    try:
        return TerminalCode(value)
    except (TypeError, ValueError) as error:
        raise CampaignV1Error(f"invalid terminal code {value!r}") from error


_CLASS_BY_CODE = {
    TerminalCode.ABSTRACT_CERTIFIED: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.LOCAL_GROUND_RECOVERY: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.FULL_GROUND_FALLBACK: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.CACHED_EXACT_INFEASIBLE: TerminalClass.INFEASIBILITY_CERTIFICATE,
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: TerminalClass.INFEASIBILITY_CERTIFICATE,
    TerminalCode.INTEGRITY_FAILURE: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.PROTOCOL_FAILURE: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.REBUILD_REQUIRED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.FALLBACK_CAP_EXHAUSTED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
}


@dataclass(frozen=True, slots=True)
class RebuildPolicyV1:
    rebuild_allowed: bool = False
    rebuild_recipe_id: ContentRef = TypedNotApplicable(
        "rebuild is disabled for this workload"
    )
    max_rebuild_attempts: int = 0
    max_route_attempts_per_logical_occurrence: int = 2

    def __post_init__(self) -> None:
        if type(self.rebuild_allowed) is not bool:
            raise CampaignV1Error("rebuild_allowed must be boolean")
        _nonnegative(self.max_rebuild_attempts, "max_rebuild_attempts")
        _positive(
            self.max_route_attempts_per_logical_occurrence,
            "max_route_attempts_per_logical_occurrence",
        )
        object.__setattr__(
            self,
            "rebuild_recipe_id",
            _ref(
                self.rebuild_recipe_id,
                "rebuild_recipe_id",
                allow_not_applicable=not self.rebuild_allowed,
            ),
        )
        if self.max_route_attempts_per_logical_occurrence != 2:
            raise CampaignV1Error("V0 allows at most two route attempts per occurrence")
        expected_rebuilds = 1 if self.rebuild_allowed else 0
        if self.max_rebuild_attempts != expected_rebuilds:
            raise CampaignV1Error(
                "V0 rebuild budget is zero when disabled and exactly one when enabled"
            )
        if self.rebuild_allowed and isinstance(
            self.rebuild_recipe_id, TypedNotApplicable
        ):
            raise CampaignV1Error("enabled rebuild requires a registered recipe")
        if not self.rebuild_allowed and not isinstance(
            self.rebuild_recipe_id, TypedNotApplicable
        ):
            raise CampaignV1Error("disabled rebuild must use a typed-null recipe")

    @classmethod
    def allowing_one(cls, rebuild_recipe_id: str) -> "RebuildPolicyV1":
        return cls(True, rebuild_recipe_id, 1, 2)

    def can_retry(self, *, route_attempt_count: int, rebuild_count: int) -> bool:
        return (
            self.rebuild_allowed
            and route_attempt_count < self.max_route_attempts_per_logical_occurrence
            and rebuild_count < self.max_rebuild_attempts
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.rebuild_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "rebuild_allowed": self.rebuild_allowed,
            "rebuild_recipe_id": _ref_dict(self.rebuild_recipe_id),
            "max_rebuild_attempts": self.max_rebuild_attempts,
            "max_route_attempts_per_logical_occurrence": 2,
        }

    @property
    def rebuild_policy_id(self) -> str:
        return content_id(REBUILD_POLICY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "rebuild_policy_id": self.rebuild_policy_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RebuildPolicyV1":
        expected = {
            "schema",
            "schema_version",
            "rebuild_allowed",
            "rebuild_recipe_id",
            "max_rebuild_attempts",
            "max_route_attempts_per_logical_occurrence",
            "rebuild_policy_id",
        }
        _fields(document, expected, "rebuild policy")
        if (
            document["schema"] != "acfqp.rebuild_policy.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise CampaignV1Error("rebuild-policy schema mismatch")
        allowed = document["rebuild_allowed"]
        result = cls(
            allowed,
            _parse_ref(
                document["rebuild_recipe_id"],
                "rebuild_recipe_id",
                allow_not_applicable=allowed is False,
            ),
            document["max_rebuild_attempts"],
            document["max_route_attempts_per_logical_occurrence"],
        )
        _verify_id(
            document, "rebuild_policy_id", REBUILD_POLICY_DOMAIN, result._payload()
        )
        return result


@dataclass(frozen=True, slots=True)
class LogicalOccurrenceV1:
    workload_spec_id: str
    protocol_id: str
    occurrence_index: int
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    initial_build_epoch_id: str
    rebuild_policy_id: str
    registered: bool = True

    def __post_init__(self) -> None:
        for field in (
            "workload_spec_id",
            "protocol_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "initial_build_epoch_id",
            "rebuild_policy_id",
        ):
            _cid(getattr(self, field), field)
        _positive(self.occurrence_index, "occurrence_index")
        if self.registered is not True:
            raise CampaignV1Error("only registered logical occurrences enter a campaign")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.logical_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "workload_spec_id": self.workload_spec_id,
            "protocol_id": self.protocol_id,
            "occurrence_index": self.occurrence_index,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "initial_BuildEpoch_id": self.initial_build_epoch_id,
            "rebuild_policy_id": self.rebuild_policy_id,
            "registered": True,
        }

    @property
    def logical_occurrence_id(self) -> str:
        return content_id(LOGICAL_OCCURRENCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "logical_occurrence_id": self.logical_occurrence_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "LogicalOccurrenceV1":
        expected = {
            "schema",
            "schema_version",
            "workload_spec_id",
            "protocol_id",
            "occurrence_index",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "initial_BuildEpoch_id",
            "rebuild_policy_id",
            "registered",
            "logical_occurrence_id",
        }
        _fields(document, expected, "logical occurrence")
        if (
            document["schema"] != "acfqp.logical_occurrence.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise CampaignV1Error("logical-occurrence schema mismatch")
        result = cls(
            document["workload_spec_id"],
            document["protocol_id"],
            document["occurrence_index"],
            document["structural_id"],
            document["query_id"],
            document["selected_plan_id"],
            document["threshold_profile_id"],
            document["initial_BuildEpoch_id"],
            document["rebuild_policy_id"],
            document["registered"],
        )
        _verify_id(
            document,
            "logical_occurrence_id",
            LOGICAL_OCCURRENCE_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class RouteAttemptV1:
    logical_occurrence_id: str
    route_attempt_index: int
    build_epoch_id: str
    predecessor_route_attempt_id: ContentRef

    def __post_init__(self) -> None:
        _cid(self.logical_occurrence_id, "logical_occurrence_id")
        _positive(self.route_attempt_index, "route_attempt_index")
        if self.route_attempt_index > 2:
            raise CampaignV1Error("V0 route-attempt index cannot exceed 2")
        _cid(self.build_epoch_id, "build_epoch_id")
        first = self.route_attempt_index == 1
        object.__setattr__(
            self,
            "predecessor_route_attempt_id",
            _ref(
                self.predecessor_route_attempt_id,
                "predecessor_route_attempt_id",
                allow_not_applicable=first,
            ),
        )
        predecessor_absent = isinstance(
            self.predecessor_route_attempt_id, TypedNotApplicable
        )
        if first != predecessor_absent:
            raise CampaignV1Error(
                "only the initial route attempt may omit its predecessor"
            )

    @classmethod
    def initial(cls, occurrence: LogicalOccurrenceV1) -> "RouteAttemptV1":
        return cls(
            occurrence.logical_occurrence_id,
            1,
            occurrence.initial_build_epoch_id,
            TypedNotApplicable("initial route attempt has no predecessor"),
        )

    @classmethod
    def retry(
        cls,
        occurrence: LogicalOccurrenceV1,
        policy: RebuildPolicyV1,
        predecessor: "RouteAttemptV1",
        source_terminal_result: SemanticVerificationResultV1,
        new_build_epoch_id: str,
    ) -> "RouteAttemptV1":
        try:
            source_terminal, attestation = require_terminal_classification_result_v1(
                source_terminal_result
            )
        except SemanticVerificationV1Error as error:
            raise CampaignV1Error(
                "retry requires verified REBUILD_REQUIRED terminal evidence"
            ) from error
        if occurrence.rebuild_policy_id != policy.rebuild_policy_id:
            raise CampaignV1Error("retry uses another rebuild policy")
        if not policy.can_retry(route_attempt_count=1, rebuild_count=0):
            raise CampaignV1Error("rebuild is not allowed or its retry budget is exhausted")
        if predecessor.logical_occurrence_id != occurrence.logical_occurrence_id:
            raise CampaignV1Error("retry predecessor belongs to another occurrence")
        if predecessor.route_attempt_index != 1:
            raise CampaignV1Error("V0 has no third route attempt")
        if new_build_epoch_id == predecessor.build_epoch_id:
            raise CampaignV1Error("rebuild retry requires a new BuildEpoch")
        expected_context = (
            occurrence.protocol_id,
            occurrence.structural_id,
            occurrence.query_id,
            occurrence.selected_plan_id,
            occurrence.threshold_profile_id,
            occurrence.logical_occurrence_id,
            predecessor.route_attempt_id,
            predecessor.build_epoch_id,
        )
        attested_context = (
            source_terminal_result.binding.route_context.protocol_id,
            attestation.structural_id,
            attestation.query_id,
            attestation.selected_plan_id,
            attestation.threshold_profile_id,
            attestation.logical_occurrence_id,
            attestation.route_attempt_id,
            attestation.build_epoch_id,
        )
        if (
            attested_context != expected_context
            or source_terminal.logical_occurrence_id
            != occurrence.logical_occurrence_id
            or source_terminal.route_attempt_id != predecessor.route_attempt_id
            or source_terminal.terminal_code is not TerminalCode.REBUILD_REQUIRED
        ):
            raise CampaignV1Error(
                "retry terminal authority does not bind the occurrence/predecessor"
            )
        return cls(
            occurrence.logical_occurrence_id,
            2,
            new_build_epoch_id,
            predecessor.route_attempt_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_attempt.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_index": self.route_attempt_index,
            "BuildEpoch_id": self.build_epoch_id,
            "predecessor_route_attempt_id": _ref_dict(
                self.predecessor_route_attempt_id
            ),
        }

    @property
    def route_attempt_id(self) -> str:
        return content_id(ROUTE_ATTEMPT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "route_attempt_id": self.route_attempt_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteAttemptV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "route_attempt_index",
            "BuildEpoch_id",
            "predecessor_route_attempt_id",
            "route_attempt_id",
        }
        _fields(document, expected, "route attempt")
        if (
            document["schema"] != "acfqp.route_attempt.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise CampaignV1Error("route-attempt schema mismatch")
        first = document["route_attempt_index"] == 1
        result = cls(
            document["logical_occurrence_id"],
            document["route_attempt_index"],
            document["BuildEpoch_id"],
            _parse_ref(
                document["predecessor_route_attempt_id"],
                "predecessor_route_attempt_id",
                allow_not_applicable=first,
            ),
        )
        _verify_id(
            document, "route_attempt_id", ROUTE_ATTEMPT_DOMAIN, result._payload()
        )
        return result


@dataclass(frozen=True, slots=True)
class RebuildEventV1:
    logical_occurrence_id: str
    rebuild_policy_id: str
    rebuild_attempt_index: int
    source_route_attempt_id: str
    source_route_attempt_index: int
    source_build_epoch_id: str
    source_terminal_artifact_id: str
    source_terminal_code: TerminalCode
    target_route_attempt_id: str
    target_route_attempt_index: int
    target_build_epoch_id: str
    rebuild_work_vector_id: str
    _authority: object = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _REBUILD_EVENT_AUTHORITY:
            raise CampaignV1Error(
                "rebuild event requires verified REBUILD_REQUIRED authorization"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_REBUILD_EVENT_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise CampaignV1Error(
                    "rebuild event is a copied or modified authority"
                ) from error
        for field in (
            "logical_occurrence_id",
            "rebuild_policy_id",
            "source_route_attempt_id",
            "source_build_epoch_id",
            "source_terminal_artifact_id",
            "target_route_attempt_id",
            "target_build_epoch_id",
            "rebuild_work_vector_id",
        ):
            _cid(getattr(self, field), field)
        _positive(self.rebuild_attempt_index, "rebuild_attempt_index")
        _positive(self.source_route_attempt_index, "source_route_attempt_index")
        _positive(self.target_route_attempt_index, "target_route_attempt_index")
        if self.rebuild_attempt_index != 1:
            raise CampaignV1Error("V0 permits exactly one registered rebuild")
        if self.source_route_attempt_index != 1 or self.target_route_attempt_index != 2:
            raise CampaignV1Error("rebuild must connect route attempt 1 to attempt 2")
        object.__setattr__(
            self, "source_terminal_code", _terminal_code(self.source_terminal_code)
        )
        if self.source_terminal_code is not TerminalCode.REBUILD_REQUIRED:
            raise CampaignV1Error("only REBUILD_REQUIRED can authorize a rebuild")
        if self.source_route_attempt_id == self.target_route_attempt_id:
            raise CampaignV1Error("rebuild retry requires a new route-attempt ID")
        if self.source_build_epoch_id == self.target_build_epoch_id:
            raise CampaignV1Error("rebuild retry requires a new BuildEpoch ID")

    @classmethod
    def authorize(
        cls,
        occurrence: LogicalOccurrenceV1,
        policy: RebuildPolicyV1,
        source_attempt: RouteAttemptV1,
        source_terminal_result: SemanticVerificationResultV1,
        target_attempt: RouteAttemptV1,
        rebuild_work_vector_id: str,
    ) -> "RebuildEventV1":
        try:
            source_terminal, attestation = require_terminal_classification_result_v1(
                source_terminal_result
            )
        except SemanticVerificationV1Error as error:
            raise CampaignV1Error(
                "rebuild authorization requires verified TERMINAL_CLASSIFICATION evidence"
            ) from error
        if occurrence.rebuild_policy_id != policy.rebuild_policy_id:
            raise CampaignV1Error("occurrence/rebuild-policy binding mismatch")
        if not policy.can_retry(route_attempt_count=1, rebuild_count=0):
            raise CampaignV1Error("rebuild is not allowed or its retry budget is exhausted")
        if source_attempt.logical_occurrence_id != occurrence.logical_occurrence_id:
            raise CampaignV1Error("source attempt belongs to another occurrence")
        if target_attempt.logical_occurrence_id != occurrence.logical_occurrence_id:
            raise CampaignV1Error("target attempt belongs to another occurrence")
        if source_terminal.logical_occurrence_id != occurrence.logical_occurrence_id:
            raise CampaignV1Error("source terminal belongs to another occurrence")
        if source_terminal.route_attempt_id != source_attempt.route_attempt_id:
            raise CampaignV1Error("source terminal/attempt mismatch")
        expected_context = (
            occurrence.protocol_id,
            occurrence.structural_id,
            occurrence.query_id,
            occurrence.selected_plan_id,
            occurrence.threshold_profile_id,
            occurrence.logical_occurrence_id,
            source_attempt.route_attempt_id,
            source_attempt.build_epoch_id,
        )
        attested_context = (
            source_terminal_result.binding.route_context.protocol_id,
            attestation.structural_id,
            attestation.query_id,
            attestation.selected_plan_id,
            attestation.threshold_profile_id,
            attestation.logical_occurrence_id,
            attestation.route_attempt_id,
            attestation.build_epoch_id,
        )
        if attested_context != expected_context:
            raise CampaignV1Error(
                "verified rebuild terminal uses another occurrence, query, attempt, or BuildEpoch"
            )
        if source_terminal.terminal_code is not TerminalCode.REBUILD_REQUIRED:
            raise CampaignV1Error("only REBUILD_REQUIRED is retryable")
        if target_attempt.predecessor_route_attempt_id != source_attempt.route_attempt_id:
            raise CampaignV1Error("target attempt does not bind its predecessor")
        if target_attempt.build_epoch_id == source_attempt.build_epoch_id:
            raise CampaignV1Error("rebuild did not create a new BuildEpoch")
        event = cls(
            occurrence.logical_occurrence_id,
            policy.rebuild_policy_id,
            1,
            source_attempt.route_attempt_id,
            source_attempt.route_attempt_index,
            source_attempt.build_epoch_id,
            source_terminal.terminal_artifact_id,
            source_terminal.terminal_code,
            target_attempt.route_attempt_id,
            target_attempt.route_attempt_index,
            target_attempt.build_epoch_id,
            rebuild_work_vector_id,
            _authority=_REBUILD_EVENT_AUTHORITY,
        )
        return bind_runtime_authority_v1(
            event,
            issuer=_REBUILD_EVENT_AUTHORITY,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.rebuild_event.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "rebuild_policy_id": self.rebuild_policy_id,
            "rebuild_attempt_index": self.rebuild_attempt_index,
            "source_route_attempt_id": self.source_route_attempt_id,
            "source_route_attempt_index": self.source_route_attempt_index,
            "source_BuildEpoch_id": self.source_build_epoch_id,
            "source_terminal_artifact_id": self.source_terminal_artifact_id,
            "source_terminal_code": self.source_terminal_code.value,
            "target_route_attempt_id": self.target_route_attempt_id,
            "target_route_attempt_index": self.target_route_attempt_index,
            "target_BuildEpoch_id": self.target_build_epoch_id,
            "rebuild_work_vector_id": self.rebuild_work_vector_id,
        }

    @property
    def rebuild_event_id(self) -> str:
        return content_id(REBUILD_EVENT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "rebuild_event_id": self.rebuild_event_id}

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        occurrence: LogicalOccurrenceV1 | None = None,
        policy: RebuildPolicyV1 | None = None,
        source_attempt: RouteAttemptV1 | None = None,
        source_terminal_result: SemanticVerificationResultV1 | None = None,
        target_attempt: RouteAttemptV1 | None = None,
    ) -> "RebuildEventV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "rebuild_policy_id",
            "rebuild_attempt_index",
            "source_route_attempt_id",
            "source_route_attempt_index",
            "source_BuildEpoch_id",
            "source_terminal_artifact_id",
            "source_terminal_code",
            "target_route_attempt_id",
            "target_route_attempt_index",
            "target_BuildEpoch_id",
            "rebuild_work_vector_id",
            "rebuild_event_id",
        }
        _fields(document, expected, "rebuild event")
        if (
            document["schema"] != "acfqp.rebuild_event.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise CampaignV1Error("rebuild-event schema mismatch")
        supplied_id = _cid(document["rebuild_event_id"], "rebuild_event_id")
        raw_payload = {
            key: value for key, value in document.items() if key != "rebuild_event_id"
        }
        if supplied_id != content_id(REBUILD_EVENT_DOMAIN, raw_payload):
            raise CampaignV1Error("rebuild_event_id content ID mismatch")
        if (
            occurrence is None
            or policy is None
            or source_attempt is None
            or source_terminal_result is None
            or target_attempt is None
        ):
            raise CampaignV1Error(
                "rebuild-event transport requires verified terminal replay inputs"
            )
        result = cls.authorize(
            occurrence,
            policy,
            source_attempt,
            source_terminal_result,
            target_attempt,
            document["rebuild_work_vector_id"],
        )
        if result.to_dict() != dict(document):
            raise CampaignV1Error("rebuild event does not match authorization replay")
        return result


def require_rebuild_event_authority_v1(event: object) -> RebuildEventV1:
    """Require the exact terminal-replay rebuild authorization instance."""

    if type(event) is not RebuildEventV1:
        raise CampaignV1Error("rebuild event lacks semantic terminal authority")
    try:
        require_runtime_authority_v1(event, issuer=_REBUILD_EVENT_AUTHORITY)
    except ValueError as error:
        raise CampaignV1Error(
            "rebuild event is not the retained authorized instance"
        ) from error
    return event


@dataclass(frozen=True, slots=True)
class AttemptClosureRecordV1:
    route_attempt_index: int
    route_attempt_id: str
    build_epoch_id: str
    terminal_artifact_id: str
    terminal_verification_attestation_id: str
    terminal_class: TerminalClass
    terminal_code: TerminalCode
    terminal_actual_work_vector_id: str
    attempt_work_vector_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _positive(self.route_attempt_index, "route_attempt_index")
        if self.route_attempt_index > 2:
            raise CampaignV1Error("V0 attempt closure index exceeds 2")
        for field in (
            "route_attempt_id",
            "build_epoch_id",
            "terminal_artifact_id",
            "terminal_verification_attestation_id",
            "terminal_actual_work_vector_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(self, "terminal_class", _terminal_class(self.terminal_class))
        object.__setattr__(self, "terminal_code", _terminal_code(self.terminal_code))
        if _CLASS_BY_CODE[self.terminal_code] is not self.terminal_class:
            raise CampaignV1Error("attempt terminal class/code mismatch")
        if (
            not self.attempt_work_vector_ids
            or tuple(sorted(self.attempt_work_vector_ids)) != self.attempt_work_vector_ids
            or len(set(self.attempt_work_vector_ids)) != len(self.attempt_work_vector_ids)
        ):
            raise CampaignV1Error(
                "attempt work IDs must be nonempty, unique, and sorted"
            )
        for work_id in self.attempt_work_vector_ids:
            _cid(work_id, "attempt_work_vector_id")
        if self.terminal_actual_work_vector_id not in self.attempt_work_vector_ids:
            raise CampaignV1Error("terminal actual work was omitted from attempt work")

    @classmethod
    def bind(
        cls,
        occurrence: LogicalOccurrenceV1,
        attempt: RouteAttemptV1,
        terminal_result: SemanticVerificationResultV1,
        work_vector_ids: Sequence[str],
    ) -> "AttemptClosureRecordV1":
        try:
            terminal, attestation = require_terminal_classification_result_v1(
                terminal_result
            )
        except SemanticVerificationV1Error as error:
            raise CampaignV1Error(
                "attempt closure requires verified TERMINAL_CLASSIFICATION evidence"
            ) from error
        if terminal.logical_occurrence_id != attempt.logical_occurrence_id:
            raise CampaignV1Error("attempt terminal belongs to another occurrence")
        if terminal.route_attempt_id != attempt.route_attempt_id:
            raise CampaignV1Error("attempt terminal route-attempt mismatch")
        if terminal.terminal_scope != "ROUTE_ATTEMPT":
            raise CampaignV1Error("campaign attempt closure requires ROUTE_ATTEMPT scope")
        expected_context = (
            occurrence.protocol_id,
            occurrence.structural_id,
            occurrence.query_id,
            occurrence.selected_plan_id,
            occurrence.threshold_profile_id,
            occurrence.logical_occurrence_id,
            attempt.route_attempt_id,
            attempt.build_epoch_id,
        )
        attested_context = (
            terminal_result.binding.route_context.protocol_id,
            attestation.structural_id,
            attestation.query_id,
            attestation.selected_plan_id,
            attestation.threshold_profile_id,
            attestation.logical_occurrence_id,
            attestation.route_attempt_id,
            attestation.build_epoch_id,
        )
        if attested_context != expected_context:
            raise CampaignV1Error(
                "verified terminal uses another occurrence, query, attempt, or BuildEpoch"
            )
        return cls(
            attempt.route_attempt_index,
            attempt.route_attempt_id,
            attempt.build_epoch_id,
            terminal.terminal_artifact_id,
            attestation.verification_attestation_id,
            terminal.terminal_class,
            terminal.terminal_code,
            terminal.actual_work_vector_id,
            tuple(sorted(work_vector_ids)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_attempt_index": self.route_attempt_index,
            "route_attempt_id": self.route_attempt_id,
            "BuildEpoch_id": self.build_epoch_id,
            "terminal_artifact_id": self.terminal_artifact_id,
            "terminal_verification_attestation_id": (
                self.terminal_verification_attestation_id
            ),
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "terminal_actual_work_vector_id": self.terminal_actual_work_vector_id,
            "attempt_work_vector_ids": list(self.attempt_work_vector_ids),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "AttemptClosureRecordV1":
        expected = {
            "route_attempt_index",
            "route_attempt_id",
            "BuildEpoch_id",
            "terminal_artifact_id",
            "terminal_verification_attestation_id",
            "terminal_class",
            "terminal_code",
            "terminal_actual_work_vector_id",
            "attempt_work_vector_ids",
        }
        _fields(document, expected, "attempt closure record")
        if type(document["attempt_work_vector_ids"]) is not list:
            raise CampaignV1Error("attempt work IDs must be a list")
        return cls(
            document["route_attempt_index"],
            document["route_attempt_id"],
            document["BuildEpoch_id"],
            document["terminal_artifact_id"],
            document["terminal_verification_attestation_id"],
            document["terminal_class"],
            document["terminal_code"],
            document["terminal_actual_work_vector_id"],
            tuple(document["attempt_work_vector_ids"]),
        )


@dataclass(frozen=True, slots=True)
class CampaignOccurrenceClosureV1:
    logical_occurrence_id: str
    rebuild_policy_id: str
    attempts: tuple[AttemptClosureRecordV1, ...]
    rebuild_event_ids: tuple[str, ...]
    rebuild_work_vector_ids: tuple[str, ...]
    occurrence_work_sum_id: str
    final_terminal_artifact_id: str
    final_terminal_class: TerminalClass
    final_terminal_code: TerminalCode
    closure_denominator_included: bool = True
    certification_denominator_included: bool = True
    economics_denominator_included: bool = True
    _authority: object = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _CAMPAIGN_CLOSURE_AUTHORITY:
            raise CampaignV1Error(
                "campaign occurrence closure requires semantic terminal replay"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_CAMPAIGN_CLOSURE_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise CampaignV1Error(
                    "campaign occurrence closure is a copied or modified authority"
                ) from error
        _cid(self.logical_occurrence_id, "logical_occurrence_id")
        _cid(self.rebuild_policy_id, "rebuild_policy_id")
        if not self.attempts or len(self.attempts) > 2:
            raise CampaignV1Error("occurrence closure requires one or two attempts")
        if tuple(row.route_attempt_index for row in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise CampaignV1Error("attempt closure indices must start at 1 and be continuous")
        if len({row.route_attempt_id for row in self.attempts}) != len(self.attempts):
            raise CampaignV1Error("occurrence closure repeats a route attempt")
        expected_rebuilds = len(self.attempts) - 1
        if (
            len(self.rebuild_event_ids) != expected_rebuilds
            or len(self.rebuild_work_vector_ids) != expected_rebuilds
        ):
            raise CampaignV1Error("retry closure must retain exactly one rebuild event/work vector")
        for event_id in self.rebuild_event_ids:
            _cid(event_id, "rebuild_event_id")
        for work_id in self.rebuild_work_vector_ids:
            _cid(work_id, "rebuild_work_vector_id")
        _cid(self.occurrence_work_sum_id, "occurrence_work_sum_id")
        _cid(self.final_terminal_artifact_id, "final_terminal_artifact_id")
        object.__setattr__(
            self, "final_terminal_class", _terminal_class(self.final_terminal_class)
        )
        object.__setattr__(
            self, "final_terminal_code", _terminal_code(self.final_terminal_code)
        )
        if _CLASS_BY_CODE[self.final_terminal_code] is not self.final_terminal_class:
            raise CampaignV1Error("final terminal class/code mismatch")
        final = self.attempts[-1]
        if (
            final.terminal_artifact_id != self.final_terminal_artifact_id
            or final.terminal_class is not self.final_terminal_class
            or final.terminal_code is not self.final_terminal_code
        ):
            raise CampaignV1Error("final terminal does not match the last attempt")
        if len(self.attempts) == 2 and (
            self.attempts[0].terminal_code is not TerminalCode.REBUILD_REQUIRED
        ):
            raise CampaignV1Error("a second attempt requires a REBUILD_REQUIRED predecessor")
        if not all(
            value is True
            for value in (
                self.closure_denominator_included,
                self.certification_denominator_included,
                self.economics_denominator_included,
            )
        ):
            raise CampaignV1Error("registered occurrence cannot be removed from a denominator")

    @property
    def certificate_covered(self) -> bool:
        return self.final_terminal_class is not TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE

    @classmethod
    def close(
        cls,
        occurrence: LogicalOccurrenceV1,
        policy: RebuildPolicyV1,
        attempts: Sequence[RouteAttemptV1],
        terminal_results: Sequence[SemanticVerificationResultV1],
        attempt_work_vector_ids: Sequence[Sequence[str]],
        occurrence_work_sum_id: str,
        *,
        rebuild_events: Sequence[RebuildEventV1] = (),
    ) -> "CampaignOccurrenceClosureV1":
        attempt_rows = tuple(attempts)
        result_rows = tuple(terminal_results)
        work_rows = tuple(attempt_work_vector_ids)
        events = tuple(rebuild_events)
        if not (
            len(attempt_rows) == len(result_rows) == len(work_rows)
        ):
            raise CampaignV1Error("attempt, terminal, and work rows must align")
        if not attempt_rows:
            raise CampaignV1Error("occurrence closure requires at least one attempt")
        if occurrence.rebuild_policy_id != policy.rebuild_policy_id:
            raise CampaignV1Error("occurrence/rebuild-policy binding mismatch")
        if (
            attempt_rows[0].route_attempt_index != 1
            or attempt_rows[0].build_epoch_id != occurrence.initial_build_epoch_id
            or not isinstance(
                attempt_rows[0].predecessor_route_attempt_id, TypedNotApplicable
            )
        ):
            raise CampaignV1Error(
                "initial route attempt does not bind the occurrence BuildEpoch"
            )
        for attempt in attempt_rows:
            if attempt.logical_occurrence_id != occurrence.logical_occurrence_id:
                raise CampaignV1Error("closure mixes logical occurrences")
        records = tuple(
            AttemptClosureRecordV1.bind(occurrence, attempt, result, work_ids)
            for attempt, result, work_ids in zip(
                attempt_rows, result_rows, work_rows
            )
        )
        terminal_rows = tuple(
            require_terminal_classification_result_v1(result)[0]
            for result in result_rows
        )
        if len(events) != max(0, len(attempt_rows) - 1):
            raise CampaignV1Error("retry closure has missing or extra rebuild events")
        for index, event in enumerate(events):
            event = require_rebuild_event_authority_v1(event)
            source = attempt_rows[index]
            target = attempt_rows[index + 1]
            source_terminal = terminal_rows[index]
            if (
                event.logical_occurrence_id != occurrence.logical_occurrence_id
                or event.rebuild_policy_id != policy.rebuild_policy_id
                or event.source_route_attempt_id != source.route_attempt_id
                or event.target_route_attempt_id != target.route_attempt_id
                or event.source_terminal_artifact_id
                != source_terminal.terminal_artifact_id
            ):
                raise CampaignV1Error("rebuild event does not bind adjacent attempts")
            if (
                event.source_route_attempt_index != source.route_attempt_index
                or event.target_route_attempt_index != target.route_attempt_index
                or event.source_build_epoch_id != source.build_epoch_id
                or event.target_build_epoch_id != target.build_epoch_id
                or target.predecessor_route_attempt_id != source.route_attempt_id
            ):
                raise CampaignV1Error(
                    "rebuild event/attempt index, predecessor, or BuildEpoch mismatch"
                )
        final_terminal = terminal_rows[-1]
        if (
            final_terminal.terminal_code is TerminalCode.REBUILD_REQUIRED
            and policy.can_retry(
                route_attempt_count=len(attempt_rows), rebuild_count=len(events)
            )
        ):
            raise CampaignV1Error(
                "REBUILD_REQUIRED is retryable and cannot yet close the logical occurrence"
            )
        closure = cls(
            occurrence.logical_occurrence_id,
            policy.rebuild_policy_id,
            records,
            tuple(event.rebuild_event_id for event in events),
            tuple(event.rebuild_work_vector_id for event in events),
            occurrence_work_sum_id,
            final_terminal.terminal_artifact_id,
            final_terminal.terminal_class,
            final_terminal.terminal_code,
            _authority=_CAMPAIGN_CLOSURE_AUTHORITY,
        )
        return bind_runtime_authority_v1(
            closure,
            issuer=_CAMPAIGN_CLOSURE_AUTHORITY,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_occurrence_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "rebuild_policy_id": self.rebuild_policy_id,
            "attempts": [row.to_dict() for row in self.attempts],
            "rebuild_event_ids": list(self.rebuild_event_ids),
            "rebuild_work_vector_ids": list(self.rebuild_work_vector_ids),
            "occurrence_work_sum_id": self.occurrence_work_sum_id,
            "final_terminal_artifact_id": self.final_terminal_artifact_id,
            "final_terminal_class": self.final_terminal_class.value,
            "final_terminal_code": self.final_terminal_code.value,
            "closure_denominator_included": True,
            "certification_denominator_included": True,
            "economics_denominator_included": True,
        }

    @property
    def campaign_occurrence_closure_id(self) -> str:
        return content_id(CAMPAIGN_OCCURRENCE_CLOSURE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_occurrence_closure_id": self.campaign_occurrence_closure_id,
        }

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        occurrence: LogicalOccurrenceV1 | None = None,
        policy: RebuildPolicyV1 | None = None,
        attempts: Sequence[RouteAttemptV1] | None = None,
        terminal_results: Sequence[SemanticVerificationResultV1] | None = None,
        attempt_work_vector_ids: Sequence[Sequence[str]] | None = None,
        rebuild_events: Sequence[RebuildEventV1] | None = None,
    ) -> "CampaignOccurrenceClosureV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "rebuild_policy_id",
            "attempts",
            "rebuild_event_ids",
            "rebuild_work_vector_ids",
            "occurrence_work_sum_id",
            "final_terminal_artifact_id",
            "final_terminal_class",
            "final_terminal_code",
            "closure_denominator_included",
            "certification_denominator_included",
            "economics_denominator_included",
            "campaign_occurrence_closure_id",
        }
        _fields(document, expected, "campaign occurrence closure")
        if (
            document["schema"] != "acfqp.campaign_occurrence_closure.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["attempts"]) is not list
            or type(document["rebuild_event_ids"]) is not list
            or type(document["rebuild_work_vector_ids"]) is not list
        ):
            raise CampaignV1Error("campaign occurrence-closure schema mismatch")
        supplied_id = _cid(
            document["campaign_occurrence_closure_id"],
            "campaign_occurrence_closure_id",
        )
        raw_payload = {
            key: value
            for key, value in document.items()
            if key != "campaign_occurrence_closure_id"
        }
        if supplied_id != content_id(CAMPAIGN_OCCURRENCE_CLOSURE_DOMAIN, raw_payload):
            raise CampaignV1Error(
                "campaign_occurrence_closure_id content ID mismatch"
            )
        if (
            occurrence is None
            or policy is None
            or attempts is None
            or terminal_results is None
            or attempt_work_vector_ids is None
            or rebuild_events is None
        ):
            raise CampaignV1Error(
                "campaign occurrence-closure transport requires semantic replay inputs"
            )
        result = cls.close(
            occurrence,
            policy,
            attempts,
            terminal_results,
            attempt_work_vector_ids,
            document["occurrence_work_sum_id"],
            rebuild_events=rebuild_events,
        )
        if result.to_dict() != dict(document):
            raise CampaignV1Error(
                "campaign occurrence closure does not match semantic replay"
            )
        return result


def require_campaign_occurrence_closure_authority_v1(
    closure: object,
) -> CampaignOccurrenceClosureV1:
    """Require the exact occurrence closure minted by terminal replay."""

    if type(closure) is not CampaignOccurrenceClosureV1:
        raise CampaignV1Error(
            "campaign occurrence closure lacks terminal replay authority"
        )
    try:
        require_runtime_authority_v1(
            closure,
            issuer=_CAMPAIGN_CLOSURE_AUTHORITY,
        )
    except ValueError as error:
        raise CampaignV1Error(
            "campaign occurrence closure is not the retained minted instance"
        ) from error
    return closure


@dataclass(frozen=True, slots=True)
class CampaignSummaryRowV1:
    occurrence_index: int
    logical_occurrence_id: str
    occurrence_closure_id: str
    final_terminal_class: TerminalClass
    final_terminal_code: TerminalCode
    route_attempt_count: int

    def __post_init__(self) -> None:
        _positive(self.occurrence_index, "occurrence_index")
        _cid(self.logical_occurrence_id, "logical_occurrence_id")
        _cid(self.occurrence_closure_id, "occurrence_closure_id")
        object.__setattr__(
            self, "final_terminal_class", _terminal_class(self.final_terminal_class)
        )
        object.__setattr__(
            self, "final_terminal_code", _terminal_code(self.final_terminal_code)
        )
        if _CLASS_BY_CODE[self.final_terminal_code] is not self.final_terminal_class:
            raise CampaignV1Error("campaign row terminal class/code mismatch")
        if self.route_attempt_count not in {1, 2}:
            raise CampaignV1Error("campaign row route-attempt count must be 1 or 2")
        _positive(self.route_attempt_count, "route_attempt_count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.logical_occurrence_id,
            "occurrence_closure_id": self.occurrence_closure_id,
            "final_terminal_class": self.final_terminal_class.value,
            "final_terminal_code": self.final_terminal_code.value,
            "route_attempt_count": self.route_attempt_count,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CampaignSummaryRowV1":
        expected = {
            "occurrence_index",
            "logical_occurrence_id",
            "occurrence_closure_id",
            "final_terminal_class",
            "final_terminal_code",
            "route_attempt_count",
        }
        _fields(document, expected, "campaign summary row")
        return cls(
            document["occurrence_index"],
            document["logical_occurrence_id"],
            document["occurrence_closure_id"],
            document["final_terminal_class"],
            document["final_terminal_code"],
            document["route_attempt_count"],
        )


@dataclass(frozen=True, slots=True)
class CampaignClosureSummaryV1:
    workload_spec_id: str
    rows: tuple[CampaignSummaryRowV1, ...]
    closure_denominator: int
    certification_coverage_denominator: int
    economics_cost_denominator: int
    plan_certificate_count: int
    infeasibility_certificate_count: int
    noncertificate_count: int
    official_run_valid: bool
    certificate_coverage_gate: str
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    workload_economics_gate_status: str = WORKLOAD_ECONOMICS_GATE_NOT_RUN
    counter_completeness_gate_status: str = COUNTER_COMPLETENESS_GATE_NOT_RUN
    scalar_gate_status: str = SCALAR_GATE_NOT_RUN
    _authority: object = field(default=None, repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _CAMPAIGN_SUMMARY_AUTHORITY:
            raise CampaignV1Error(
                "campaign summary requires authoritative closure replay"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_CAMPAIGN_SUMMARY_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise CampaignV1Error(
                    "campaign summary is a copied or modified authority"
                ) from error
        _cid(self.workload_spec_id, "workload_spec_id")
        if not self.rows:
            raise CampaignV1Error("campaign summary cannot omit all registered occurrences")
        if tuple(row.occurrence_index for row in self.rows) != tuple(
            range(1, len(self.rows) + 1)
        ):
            raise CampaignV1Error("campaign occurrence indices must start at 1 and be continuous")
        if len({row.logical_occurrence_id for row in self.rows}) != len(self.rows):
            raise CampaignV1Error("campaign summary repeats a logical occurrence")
        if len({row.occurrence_closure_id for row in self.rows}) != len(self.rows):
            raise CampaignV1Error("campaign summary repeats an occurrence closure")
        occurrence_count = len(self.rows)
        for field in (
            "closure_denominator",
            "certification_coverage_denominator",
            "economics_cost_denominator",
            "plan_certificate_count",
            "infeasibility_certificate_count",
            "noncertificate_count",
        ):
            _nonnegative(getattr(self, field), field)
        if (
            self.closure_denominator != occurrence_count
            or self.certification_coverage_denominator != occurrence_count
            or self.economics_cost_denominator != occurrence_count
        ):
            raise CampaignV1Error("all Gate/economics denominators must use logical occurrences")
        expected_plan = sum(
            row.final_terminal_class is TerminalClass.PLAN_CERTIFICATE
            for row in self.rows
        )
        expected_infeasible = sum(
            row.final_terminal_class is TerminalClass.INFEASIBILITY_CERTIFICATE
            for row in self.rows
        )
        expected_noncertificate = sum(
            row.final_terminal_class
            is TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
            for row in self.rows
        )
        if (
            self.plan_certificate_count,
            self.infeasibility_certificate_count,
            self.noncertificate_count,
        ) != (expected_plan, expected_infeasible, expected_noncertificate):
            raise CampaignV1Error("campaign terminal counts do not match registered rows")
        expected_valid = not any(
            row.final_terminal_code
            in {TerminalCode.INTEGRITY_FAILURE, TerminalCode.PROTOCOL_FAILURE}
            for row in self.rows
        )
        if self.official_run_valid is not expected_valid:
            raise CampaignV1Error("official-run validity misclassifies integrity/protocol failure")
        expected_coverage = (
            CERTIFICATE_COVERAGE_PASS
            if expected_noncertificate == 0
            else CERTIFICATE_COVERAGE_FAIL
        )
        if self.certificate_coverage_gate != expected_coverage:
            raise CampaignV1Error("certificate-coverage Gate result mismatch")
        if self.official_execution_allowed is not False:
            raise CampaignV1Error("official execution remains locked")
        if self.official_scalar_cost is not None or self.official_N_break_even is not None:
            raise CampaignV1Error("official scalar and break-even must remain null")
        if self.workload_economics_gate_status != WORKLOAD_ECONOMICS_GATE_NOT_RUN:
            raise CampaignV1Error("workload-economics Gate must remain NOT_RUN")
        if self.counter_completeness_gate_status != COUNTER_COMPLETENESS_GATE_NOT_RUN:
            raise CampaignV1Error("counter-completeness Gate must remain NOT_RUN")
        if self.scalar_gate_status != SCALAR_GATE_NOT_RUN:
            raise CampaignV1Error("scalar Gate must remain NOT_RUN")

    @property
    def total_route_attempt_count(self) -> int:
        return sum(row.route_attempt_count for row in self.rows)

    @classmethod
    def summarize(
        cls,
        workload_spec_id: str,
        occurrences: Sequence[LogicalOccurrenceV1],
        closures: Sequence[CampaignOccurrenceClosureV1],
        final_terminal_results: Sequence[SemanticVerificationResultV1],
    ) -> "CampaignClosureSummaryV1":
        occurrence_rows = tuple(occurrences)
        closure_rows = tuple(closures)
        result_rows = tuple(final_terminal_results)
        if not (
            len(occurrence_rows) == len(closure_rows) == len(result_rows)
        ):
            raise CampaignV1Error(
                "every registered occurrence requires one closure and one verified final terminal"
            )
        if tuple(row.occurrence_index for row in occurrence_rows) != tuple(
            range(1, len(occurrence_rows) + 1)
        ):
            raise CampaignV1Error("registered occurrences must be supplied in canonical order")
        rows: list[CampaignSummaryRowV1] = []
        for occurrence, closure, result in zip(
            occurrence_rows, closure_rows, result_rows
        ):
            closure = require_campaign_occurrence_closure_authority_v1(closure)
            if occurrence.workload_spec_id != workload_spec_id:
                raise CampaignV1Error("campaign mixes workload specifications")
            if closure.logical_occurrence_id != occurrence.logical_occurrence_id:
                raise CampaignV1Error("closure does not match its registered occurrence")
            if closure.rebuild_policy_id != occurrence.rebuild_policy_id:
                raise CampaignV1Error("closure uses another occurrence rebuild policy")
            try:
                terminal, attestation = require_terminal_classification_result_v1(
                    result
                )
            except SemanticVerificationV1Error as error:
                raise CampaignV1Error(
                    "campaign summary requires verified TERMINAL_CLASSIFICATION evidence"
                ) from error
            final_attempt = closure.attempts[-1]
            if (
                terminal.terminal_artifact_id != closure.final_terminal_artifact_id
                or terminal.terminal_class is not closure.final_terminal_class
                or terminal.terminal_code is not closure.final_terminal_code
                or attestation.verification_attestation_id
                != final_attempt.terminal_verification_attestation_id
                or attestation.logical_occurrence_id
                != occurrence.logical_occurrence_id
                or attestation.route_attempt_id != final_attempt.route_attempt_id
                or attestation.build_epoch_id != final_attempt.build_epoch_id
                or result.binding.route_context.protocol_id != occurrence.protocol_id
                or attestation.structural_id != occurrence.structural_id
                or attestation.query_id != occurrence.query_id
                or attestation.selected_plan_id != occurrence.selected_plan_id
                or attestation.threshold_profile_id
                != occurrence.threshold_profile_id
            ):
                raise CampaignV1Error(
                    "campaign terminal evidence does not match the closure/occurrence"
                )
            rows.append(
                CampaignSummaryRowV1(
                    occurrence.occurrence_index,
                    occurrence.logical_occurrence_id,
                    closure.campaign_occurrence_closure_id,
                    closure.final_terminal_class,
                    closure.final_terminal_code,
                    len(closure.attempts),
                )
            )
        row_tuple = tuple(rows)
        plan_count = sum(
            row.final_terminal_class is TerminalClass.PLAN_CERTIFICATE
            for row in row_tuple
        )
        infeasible_count = sum(
            row.final_terminal_class is TerminalClass.INFEASIBILITY_CERTIFICATE
            for row in row_tuple
        )
        noncertificate_count = len(row_tuple) - plan_count - infeasible_count
        official_run_valid = not any(
            row.final_terminal_code
            in {TerminalCode.INTEGRITY_FAILURE, TerminalCode.PROTOCOL_FAILURE}
            for row in row_tuple
        )
        denominator = len(row_tuple)
        summary = cls(
            workload_spec_id,
            row_tuple,
            denominator,
            denominator,
            denominator,
            plan_count,
            infeasible_count,
            noncertificate_count,
            official_run_valid,
            CERTIFICATE_COVERAGE_PASS
            if noncertificate_count == 0
            else CERTIFICATE_COVERAGE_FAIL,
            _authority=_CAMPAIGN_SUMMARY_AUTHORITY,
        )
        return bind_runtime_authority_v1(
            summary,
            issuer=_CAMPAIGN_SUMMARY_AUTHORITY,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.campaign_closure_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "workload_spec_id": self.workload_spec_id,
            "rows": [row.to_dict() for row in self.rows],
            "closure_denominator": self.closure_denominator,
            "certification_coverage_denominator": self.certification_coverage_denominator,
            "economics_cost_denominator": self.economics_cost_denominator,
            "total_route_attempt_count": self.total_route_attempt_count,
            "plan_certificate_count": self.plan_certificate_count,
            "infeasibility_certificate_count": self.infeasibility_certificate_count,
            "noncertificate_count": self.noncertificate_count,
            "official_run_valid": self.official_run_valid,
            "certificate_coverage_gate": self.certificate_coverage_gate,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": WORKLOAD_ECONOMICS_GATE_NOT_RUN,
            "counter_completeness_gate_status": COUNTER_COMPLETENESS_GATE_NOT_RUN,
            "scalar_gate_status": SCALAR_GATE_NOT_RUN,
        }

    @property
    def campaign_summary_id(self) -> str:
        return content_id(CAMPAIGN_SUMMARY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_summary_id": self.campaign_summary_id}

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        occurrences: Sequence[LogicalOccurrenceV1] | None = None,
        closures: Sequence[CampaignOccurrenceClosureV1] | None = None,
        final_terminal_results: Sequence[SemanticVerificationResultV1] | None = None,
    ) -> "CampaignClosureSummaryV1":
        expected = {
            "schema",
            "schema_version",
            "workload_spec_id",
            "rows",
            "closure_denominator",
            "certification_coverage_denominator",
            "economics_cost_denominator",
            "total_route_attempt_count",
            "plan_certificate_count",
            "infeasibility_certificate_count",
            "noncertificate_count",
            "official_run_valid",
            "certificate_coverage_gate",
            "official_execution_allowed",
            "official_scalar_cost",
            "official_N_break_even",
            "workload_economics_gate_status",
            "counter_completeness_gate_status",
            "scalar_gate_status",
            "campaign_summary_id",
        }
        _fields(document, expected, "campaign closure summary")
        if (
            document["schema"] != "acfqp.campaign_closure_summary.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["rows"]) is not list
        ):
            raise CampaignV1Error("campaign closure-summary schema mismatch")
        supplied_id = _cid(document["campaign_summary_id"], "campaign_summary_id")
        raw_payload = {
            key: value for key, value in document.items() if key != "campaign_summary_id"
        }
        if supplied_id != content_id(CAMPAIGN_SUMMARY_DOMAIN, raw_payload):
            raise CampaignV1Error("campaign_summary_id content ID mismatch")
        if occurrences is None or closures is None or final_terminal_results is None:
            raise CampaignV1Error(
                "campaign summary transport requires occurrence, closure, and semantic-terminal replay"
            )
        result = cls.summarize(
            document["workload_spec_id"],
            occurrences,
            closures,
            final_terminal_results,
        )
        if result.to_dict() != dict(document):
            raise CampaignV1Error(
                "campaign summary does not match authoritative closure replay"
            )
        return result


def require_campaign_closure_summary_authority_v1(
    summary: object,
) -> CampaignClosureSummaryV1:
    """Require the exact campaign summary minted from retained closures."""

    if type(summary) is not CampaignClosureSummaryV1:
        raise CampaignV1Error("campaign summary lacks closure replay authority")
    try:
        require_runtime_authority_v1(
            summary,
            issuer=_CAMPAIGN_SUMMARY_AUTHORITY,
        )
    except ValueError as error:
        raise CampaignV1Error(
            "campaign summary is not the retained minted instance"
        ) from error
    return summary


__all__ = [
    "AttemptClosureRecordV1",
    "CampaignClosureSummaryV1",
    "CampaignOccurrenceClosureV1",
    "CampaignSummaryRowV1",
    "CampaignV1Error",
    "LogicalOccurrenceV1",
    "RebuildEventV1",
    "RebuildPolicyV1",
    "RouteAttemptV1",
    "require_campaign_closure_summary_authority_v1",
    "require_campaign_occurrence_closure_authority_v1",
    "require_rebuild_event_authority_v1",
]
