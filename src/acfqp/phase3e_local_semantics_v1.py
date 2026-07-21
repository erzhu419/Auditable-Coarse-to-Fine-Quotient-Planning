"""Scoped Phase-3E local-solver and post-audit semantic artifacts.

The serializable V1 artifacts in this module are content-addressed transport
objects, never authorities by themselves.  Runtime authority is represented by
an opaque, non-serializable seal whose profile is restricted to outputs of the
existing Phase-3D safe-chain isolated worker and sound ground post-auditor.
The production adapter that mints this seal directly at those two execution
boundaries is intentionally left to the integrated local-route stage; the
private mint here exists only for microscopic semantic-verifier tests.

This is deliberately a V0 vertical-slice trust root.  It does not claim a
general local executor, portable process provenance, complete Phase-3E native
counter instrumentation, or official execution eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.accounting_v1 import RouteKindEnum, WorkVectorV1
from acfqp.phase3e_ids import (
    LOCAL_TRANSACTION_RESULT_DOMAIN,
    PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
    POST_AUDIT_CERTIFICATE_DOMAIN,
    canonical_json,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_threshold_v1 import portable_threshold_profile_id_v1
from acfqp.planning.common import as_fraction
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    TransactionV1,
    TypedNotApplicable,
)


SCHEMA_VERSION = "1.0.0"
TRUSTED_LOCAL_EXECUTOR_PROFILE = (
    "phase3e_phase3d_safe_chain_isolated_local_executor_v1"
)
TRUSTED_POSTAUDIT_PROFILE = "phase3e_phase3d_safe_chain_ground_postauditor_v1"
TRUST_SCOPE = "PHASE3D_SAFE_CHAIN_RUNTIME_VERTICAL_SLICE"


class Phase3ELocalSemanticV1Error(ValueError):
    """A local semantic artifact or its runtime provenance is invalid."""


class LocalSolverOutcome(str, Enum):
    CANDIDATE_FOUND = "CANDIDATE_FOUND"
    SEARCH_CAP_EXHAUSTED = "SEARCH_CAP_EXHAUSTED"
    NO_FEASIBLE_ASSIGNMENT = "NO_FEASIBLE_ASSIGNMENT"


class PostAuditOutcome(str, Enum):
    CERTIFIED = "CERTIFIED"
    FAILED = "FAILED"


def _fraction_payload(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_transport(value: Any, field_name: str) -> Any:
    """Parse canonical JSON rational records while preserving ``None``."""

    if value is None or not isinstance(value, Mapping):
        return value
    try:
        require_exact_fields(
            value,
            {"numerator", "denominator"},
            context=f"{field_name} rational",
        )
        numerator = value["numerator"]
        denominator = value["denominator"]
        if (
            type(numerator) is not int
            or type(denominator) is not int
            or denominator <= 0
        ):
            raise Phase3ELocalSemanticV1Error(
                f"{field_name} rational is not reduced positive-denominator data"
            )
        result = Fraction(numerator, denominator)
    except (TypeError, ValueError) as error:
        if isinstance(error, Phase3ELocalSemanticV1Error):
            raise
        raise Phase3ELocalSemanticV1Error(
            f"{field_name} rational is invalid: {error}"
        ) from error
    if result.numerator != numerator or result.denominator != denominator:
        raise Phase3ELocalSemanticV1Error(
            f"{field_name} rational must be reduced"
        )
    return result


@dataclass(frozen=True, slots=True)
class FrozenThresholdProfileV1:
    """Strict typed binding to the frozen Phase-3B threshold profile.

    The identifier intentionally replays Phase 3B's existing
    ``acfqp:portable-threshold-profile:v1`` identity instead of introducing a
    second Phase-3E interpretation of the same tolerances.  A post-audit may
    cite the identifier, but only this independently supplied binding provides
    the exact risk/regret values used to recompute its outcome.
    """

    query_id: str
    regret_tolerance: Fraction
    risk_tolerance: Fraction
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.query_id, "query_id")
        object.__setattr__(
            self, "regret_tolerance", as_fraction(self.regret_tolerance)
        )
        object.__setattr__(
            self, "risk_tolerance", as_fraction(self.risk_tolerance)
        )
        if self.regret_tolerance < 0:
            raise Phase3ELocalSemanticV1Error(
                "regret tolerance must be nonnegative"
            )
        if not 0 <= self.risk_tolerance <= 1:
            raise Phase3ELocalSemanticV1Error(
                "risk tolerance lies outside [0,1]"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ELocalSemanticV1Error(
                "threshold-profile binding schema version mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_threshold_profile.v1",
            "query_id": self.query_id,
            "delta": _fraction_payload(self.risk_tolerance),
            "regret_tolerance": _fraction_payload(self.regret_tolerance),
        }

    @property
    def threshold_profile_id(self) -> str:
        return portable_threshold_profile_id_v1(
            self.query_id,
            self.regret_tolerance,
            self.risk_tolerance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "schema_version": self.schema_version,
            "threshold_profile_id": self.threshold_profile_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "FrozenThresholdProfileV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "query_id",
                "delta",
                "regret_tolerance",
                "threshold_profile_id",
            },
            context="frozen threshold profile",
        )
        if document["schema"] != "acfqp.portable_threshold_profile.v1":
            raise Phase3ELocalSemanticV1Error(
                "threshold-profile binding schema mismatch"
            )

        def fraction(value: Any, name: str) -> Fraction:
            if (
                not isinstance(value, Mapping)
                or set(value) != {"numerator", "denominator"}
                or type(value["numerator"]) is not int
                or type(value["denominator"]) is not int
                or value["denominator"] <= 0
            ):
                raise Phase3ELocalSemanticV1Error(
                    f"{name} must be a reduced rational object"
                )
            result = Fraction(value["numerator"], value["denominator"])
            if _fraction_payload(result) != dict(value):
                raise Phase3ELocalSemanticV1Error(
                    f"{name} must be a reduced rational object"
                )
            return result

        result = cls(
            document["query_id"],
            fraction(document["regret_tolerance"], "regret_tolerance"),
            fraction(document["delta"], "delta"),
            document["schema_version"],
        )
        if document["threshold_profile_id"] != result.threshold_profile_id:
            raise Phase3ELocalSemanticV1Error(
                "threshold-profile binding content ID mismatch"
            )
        return result


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3ELocalSemanticV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


def _nonnegative(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise Phase3ELocalSemanticV1Error(
            f"{field_name} must be a nonnegative exact integer"
        )
    return value


def _parent_binding(role: str, legacy_id: Any) -> str:
    if type(role) is not str or not role or type(legacy_id) is not str or not legacy_id:
        raise Phase3ELocalSemanticV1Error("legacy parent binding is malformed")
    return content_id(
        PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
        {
            "schema": "acfqp.phase3d_local_parent_binding.v1",
            "role": role,
            "legacy_id": legacy_id,
        },
    )


@dataclass(frozen=True, slots=True)
class LocalTransactionResultV1:
    """Serializable local-worker result; not semantic authority by itself."""

    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str
    route_attempt_id: str
    query_id: str
    selected_plan_id: str
    route_cap_profile_id: str
    selected_upper_id: str
    work_vector_id: str
    capability_binding_id: str
    worker_result_binding_id: str
    runtime_attestation_binding_id: str
    candidate_overlay_binding_id: str | TypedNotApplicable
    stitched_plan_binding_id: str | TypedNotApplicable
    outcome: LocalSolverOutcome
    search_complete: bool
    cap_reason: str | None
    semantic_authority: bool = False
    authorizes_continuation: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id",
            "decision_point_id",
            "transaction_id",
            "route_attempt_id",
            "query_id",
            "selected_plan_id",
            "route_cap_profile_id",
            "selected_upper_id",
            "work_vector_id",
            "capability_binding_id",
            "worker_result_binding_id",
            "runtime_attestation_binding_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(self, "outcome", LocalSolverOutcome(self.outcome))
        overlay = self.candidate_overlay_binding_id
        if isinstance(overlay, TypedNotApplicable):
            overlay = TypedNotApplicable.from_dict(overlay.to_dict())
        else:
            overlay = _cid(overlay, "candidate_overlay_binding_id")
        object.__setattr__(self, "candidate_overlay_binding_id", overlay)
        stitched = self.stitched_plan_binding_id
        if isinstance(stitched, TypedNotApplicable):
            stitched = TypedNotApplicable.from_dict(stitched.to_dict())
        else:
            stitched = _cid(stitched, "stitched_plan_binding_id")
        object.__setattr__(self, "stitched_plan_binding_id", stitched)
        if type(self.search_complete) is not bool:
            raise Phase3ELocalSemanticV1Error("search_complete must be boolean")
        if self.semantic_authority is not False or self.authorizes_continuation is not False:
            raise Phase3ELocalSemanticV1Error(
                "raw local results cannot self-assert semantic authority"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ELocalSemanticV1Error("local-result schema version mismatch")
        if self.outcome is LocalSolverOutcome.CANDIDATE_FOUND:
            if (
                not self.search_complete
                or isinstance(overlay, TypedNotApplicable)
                or isinstance(stitched, TypedNotApplicable)
            ):
                raise Phase3ELocalSemanticV1Error(
                    "CANDIDATE_FOUND requires complete search, an overlay, and a "
                    "stitched-plan binding"
                )
            if self.cap_reason is not None:
                raise Phase3ELocalSemanticV1Error(
                    "CANDIDATE_FOUND cannot carry a cap reason"
                )
        elif self.outcome is LocalSolverOutcome.SEARCH_CAP_EXHAUSTED:
            if self.search_complete or not self.cap_reason:
                raise Phase3ELocalSemanticV1Error(
                    "SEARCH_CAP_EXHAUSTED must be incomplete and name its cap"
                )
            if not isinstance(overlay, TypedNotApplicable) or not isinstance(
                stitched, TypedNotApplicable
            ):
                raise Phase3ELocalSemanticV1Error(
                    "cap-exhausted search cannot expose an overlay or stitched plan"
                )
        else:
            if not self.search_complete or self.cap_reason is not None:
                raise Phase3ELocalSemanticV1Error(
                    "NO_FEASIBLE_ASSIGNMENT requires complete capped search"
                )
            if not isinstance(overlay, TypedNotApplicable) or not isinstance(
                stitched, TypedNotApplicable
            ):
                raise Phase3ELocalSemanticV1Error(
                    "no-feasible result cannot expose an overlay or stitched plan"
                )

    def _payload(self) -> dict[str, Any]:
        overlay = self.candidate_overlay_binding_id
        stitched = self.stitched_plan_binding_id
        return {
            "schema": "acfqp.local_transaction_result.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "route_attempt_id": self.route_attempt_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "route_cap_profile_id": self.route_cap_profile_id,
            "selected_upper_id": self.selected_upper_id,
            "work_vector_id": self.work_vector_id,
            "capability_binding_id": self.capability_binding_id,
            "worker_result_binding_id": self.worker_result_binding_id,
            "runtime_attestation_binding_id": self.runtime_attestation_binding_id,
            "candidate_overlay_binding_id": (
                overlay.to_dict() if isinstance(overlay, TypedNotApplicable) else overlay
            ),
            "stitched_plan_binding_id": (
                stitched.to_dict()
                if isinstance(stitched, TypedNotApplicable)
                else stitched
            ),
            "outcome": self.outcome.value,
            "search_complete": self.search_complete,
            "cap_reason": self.cap_reason,
            "semantic_authority": False,
            "authorizes_continuation": False,
        }

    @property
    def local_transaction_result_id(self) -> str:
        return content_id(LOCAL_TRANSACTION_RESULT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "local_transaction_result_id": self.local_transaction_result_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "LocalTransactionResultV1":
        expected = {
            "schema", "schema_version", "RouteDecisionContext_id",
            "decision_point_id", "transaction_id", "route_attempt_id", "query_id",
            "selected_plan_id",
            "route_cap_profile_id", "selected_upper_id", "work_vector_id",
            "capability_binding_id", "worker_result_binding_id",
            "runtime_attestation_binding_id",
            "candidate_overlay_binding_id", "outcome", "search_complete", "cap_reason",
            "stitched_plan_binding_id",
            "semantic_authority", "authorizes_continuation", "local_transaction_result_id",
        }
        require_exact_fields(document, expected, context="local transaction result")
        if document["schema"] != "acfqp.local_transaction_result.v1":
            raise Phase3ELocalSemanticV1Error("local-result schema mismatch")
        raw_overlay = document["candidate_overlay_binding_id"]
        overlay = (
            TypedNotApplicable.from_dict(raw_overlay)
            if isinstance(raw_overlay, Mapping)
            else raw_overlay
        )
        raw_stitched = document["stitched_plan_binding_id"]
        stitched = (
            TypedNotApplicable.from_dict(raw_stitched)
            if isinstance(raw_stitched, Mapping)
            else raw_stitched
        )
        result = cls(
            document["RouteDecisionContext_id"], document["decision_point_id"],
            document["transaction_id"], document["route_attempt_id"], document["query_id"],
            document["selected_plan_id"],
            document["route_cap_profile_id"], document["selected_upper_id"],
            document["work_vector_id"], document["capability_binding_id"],
            document["worker_result_binding_id"],
            document["runtime_attestation_binding_id"], overlay, stitched,
            document["outcome"],
            document["search_complete"], document["cap_reason"],
            document["semantic_authority"], document["authorizes_continuation"],
            document["schema_version"],
        )
        if document["local_transaction_result_id"] != result.local_transaction_result_id:
            raise Phase3ELocalSemanticV1Error("local-result content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class PostAuditCertificateV1:
    """Exact sound-post-audit transport; never an authority by itself."""

    route_decision_context_id: str
    decision_point_id: str
    transaction_id: str
    route_attempt_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    local_transaction_result_id: str
    work_vector_id: str
    overlay_binding_id: str
    stitched_plan_binding_id: str
    audit_issue_set_id: str
    outcome: PostAuditOutcome
    lifted_reward_lower: Fraction | None
    lifted_failure_upper: Fraction | None
    regret_upper: Fraction | None
    postaudit_ground_steps: int
    postaudit_positive_outcomes: int
    semantic_authority: bool = False
    authorizes_terminal_classification: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "route_decision_context_id", "decision_point_id", "transaction_id",
            "route_attempt_id", "query_id", "selected_plan_id",
            "threshold_profile_id", "local_transaction_result_id", "work_vector_id",
            "overlay_binding_id", "stitched_plan_binding_id", "audit_issue_set_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(self, "outcome", PostAuditOutcome(self.outcome))
        for name in ("lifted_reward_lower", "lifted_failure_upper", "regret_upper"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, as_fraction(value))
        _nonnegative(self.postaudit_ground_steps, "postaudit_ground_steps")
        _nonnegative(self.postaudit_positive_outcomes, "postaudit_positive_outcomes")
        if self.lifted_failure_upper is not None and not 0 <= self.lifted_failure_upper <= 1:
            raise Phase3ELocalSemanticV1Error("failure upper lies outside [0,1]")
        if self.semantic_authority is not False or self.authorizes_terminal_classification is not False:
            raise Phase3ELocalSemanticV1Error(
                "raw post-audit artifacts cannot self-assert semantic authority"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3ELocalSemanticV1Error("post-audit schema version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.post_audit_certificate.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": self.transaction_id,
            "route_attempt_id": self.route_attempt_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "local_transaction_result_id": self.local_transaction_result_id,
            "work_vector_id": self.work_vector_id,
            "overlay_binding_id": self.overlay_binding_id,
            "stitched_plan_binding_id": self.stitched_plan_binding_id,
            "audit_issue_set_id": self.audit_issue_set_id,
            "outcome": self.outcome.value,
            "lifted_reward_lower": self.lifted_reward_lower,
            "lifted_failure_upper": self.lifted_failure_upper,
            "regret_upper": self.regret_upper,
            "postaudit_ground_steps": self.postaudit_ground_steps,
            "postaudit_positive_outcomes": self.postaudit_positive_outcomes,
            "semantic_authority": False,
            "authorizes_terminal_classification": False,
        }

    @property
    def post_audit_certificate_id(self) -> str:
        return content_id(POST_AUDIT_CERTIFICATE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "post_audit_certificate_id": self.post_audit_certificate_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "PostAuditCertificateV1":
        expected = {
            "schema", "schema_version", "RouteDecisionContext_id", "decision_point_id",
            "transaction_id", "route_attempt_id", "query_id", "selected_plan_id",
            "threshold_profile_id", "local_transaction_result_id", "work_vector_id",
            "overlay_binding_id", "stitched_plan_binding_id",
            "audit_issue_set_id", "outcome", "lifted_reward_lower",
            "lifted_failure_upper", "regret_upper",
            "postaudit_ground_steps", "postaudit_positive_outcomes", "semantic_authority",
            "authorizes_terminal_classification", "post_audit_certificate_id",
        }
        require_exact_fields(document, expected, context="post-audit certificate")
        if document["schema"] != "acfqp.post_audit_certificate.v1":
            raise Phase3ELocalSemanticV1Error("post-audit schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"], document["decision_point_id"],
            document["transaction_id"], document["route_attempt_id"], document["query_id"],
            document["selected_plan_id"], document["threshold_profile_id"],
            document["local_transaction_result_id"], document["work_vector_id"],
            document["overlay_binding_id"], document["stitched_plan_binding_id"],
            document["audit_issue_set_id"], document["outcome"],
            _fraction_from_transport(
                document["lifted_reward_lower"], "lifted_reward_lower"
            ),
            _fraction_from_transport(
                document["lifted_failure_upper"], "lifted_failure_upper"
            ),
            _fraction_from_transport(document["regret_upper"], "regret_upper"),
            document["postaudit_ground_steps"],
            document["postaudit_positive_outcomes"], document["semantic_authority"],
            document["authorizes_terminal_classification"], document["schema_version"],
        )
        if document["post_audit_certificate_id"] != result.post_audit_certificate_id:
            raise Phase3ELocalSemanticV1Error("post-audit content ID mismatch")
        return result


_TRUSTED_LOCAL_RUNTIME_AUTHORITY = object()
_TRUSTED_POSTAUDIT_RUNTIME_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class TrustedLocalRuntimeProvenanceV1:
    binding_digest: str
    executor_profile: str = TRUSTED_LOCAL_EXECUTOR_PROFILE
    trust_scope: str = TRUST_SCOPE
    isolated_worker_observed: bool = True
    host_full_solver_replay: bool = False
    native_counter_completeness_claimed: bool = False
    official_execution_allowed: bool = False
    _authority: object = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.binding_digest, "binding_digest")
        if (
            self.executor_profile != TRUSTED_LOCAL_EXECUTOR_PROFILE
            or self.trust_scope != TRUST_SCOPE
            or self.isolated_worker_observed is not True
            or self.host_full_solver_replay is not False
            or self.native_counter_completeness_claimed is not False
            or self.official_execution_allowed is not False
            or self._authority is not _TRUSTED_LOCAL_RUNTIME_AUTHORITY
        ):
            raise Phase3ELocalSemanticV1Error("local runtime provenance overclaims its scope")


@dataclass(frozen=True, slots=True)
class TrustedPostAuditRuntimeProvenanceV1:
    binding_digest: str
    auditor_profile: str = TRUSTED_POSTAUDIT_PROFILE
    trust_scope: str = TRUST_SCOPE
    ground_postaudit_executed: bool = True
    host_full_solver_replay: bool = False
    official_execution_allowed: bool = False
    _authority: object = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.binding_digest, "binding_digest")
        if (
            self.auditor_profile != TRUSTED_POSTAUDIT_PROFILE
            or self.trust_scope != TRUST_SCOPE
            or self.ground_postaudit_executed is not True
            or self.host_full_solver_replay is not False
            or self.official_execution_allowed is not False
            or self._authority is not _TRUSTED_POSTAUDIT_RUNTIME_AUTHORITY
        ):
            raise Phase3ELocalSemanticV1Error("post-audit provenance overclaims its scope")


@dataclass(frozen=True, slots=True)
class TrustedLocalExecutionV1:
    local_result: LocalTransactionResultV1
    post_audit: PostAuditCertificateV1 | None
    work_vector: WorkVectorV1
    threshold_profile: FrozenThresholdProfileV1 | None
    local_provenance: TrustedLocalRuntimeProvenanceV1
    postaudit_provenance: TrustedPostAuditRuntimeProvenanceV1 | None
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.local_result.work_vector_id != self.work_vector.work_vector_id:
            raise Phase3ELocalSemanticV1Error("local result/work-vector mismatch")
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_TRUSTED_LOCAL_RUNTIME_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3ELocalSemanticV1Error(
                    "trusted local execution is a copied or modified authority"
                ) from error
        if self.post_audit is None:
            if self.postaudit_provenance is not None or self.threshold_profile is not None:
                raise Phase3ELocalSemanticV1Error(
                    "post-audit provenance/threshold lacks an artifact"
                )
            return
        if self.local_result.outcome is not LocalSolverOutcome.CANDIDATE_FOUND:
            raise Phase3ELocalSemanticV1Error(
                "only CANDIDATE_FOUND can enter trusted post-audit execution"
            )
        overlay = self.local_result.candidate_overlay_binding_id
        stitched = self.local_result.stitched_plan_binding_id
        if isinstance(overlay, TypedNotApplicable) or isinstance(
            stitched, TypedNotApplicable
        ):
            raise Phase3ELocalSemanticV1Error(
                "trusted post-audit requires concrete overlay and stitched-plan bindings"
            )
        threshold = self.threshold_profile
        post = self.post_audit
        if (
            self.postaudit_provenance is None
            or not isinstance(threshold, FrozenThresholdProfileV1)
            or post.local_transaction_result_id
            != self.local_result.local_transaction_result_id
            or post.work_vector_id != self.work_vector.work_vector_id
            or post.overlay_binding_id != overlay
            or post.stitched_plan_binding_id != stitched
            or post.route_decision_context_id
            != self.local_result.route_decision_context_id
            or post.decision_point_id != self.local_result.decision_point_id
            or post.transaction_id != self.local_result.transaction_id
            or post.route_attempt_id != self.local_result.route_attempt_id
            or post.query_id != self.local_result.query_id
            or post.selected_plan_id != self.local_result.selected_plan_id
            or post.threshold_profile_id != threshold.threshold_profile_id
            or threshold.query_id != post.query_id
        ):
            raise Phase3ELocalSemanticV1Error(
                "local/post-audit/threshold execution chain mismatch"
            )
        recomputed_certified = (
            post.lifted_reward_lower is not None
            and post.lifted_failure_upper is not None
            and post.regret_upper is not None
            and post.regret_upper <= threshold.regret_tolerance
            and post.lifted_failure_upper <= threshold.risk_tolerance
        )
        if (post.outcome is PostAuditOutcome.CERTIFIED) is not recomputed_certified:
            raise Phase3ELocalSemanticV1Error(
                "post-audit outcome differs from the frozen threshold profile"
            )


def require_trusted_local_execution_authority_v1(
    execution: object,
) -> TrustedLocalExecutionV1:
    """Require the exact trusted-executor result instance."""

    if type(execution) is not TrustedLocalExecutionV1:
        raise Phase3ELocalSemanticV1Error(
            "local semantic replay requires an in-memory execution"
        )
    try:
        require_runtime_authority_v1(
            execution,
            issuer=_TRUSTED_LOCAL_RUNTIME_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3ELocalSemanticV1Error(
            "local execution lacks trusted provenance from the retained "
            "trusted-executor instance"
        ) from error
    return execution


def _local_digest(execution: TrustedLocalExecutionV1) -> str:
    payload = {
        "schema": "acfqp.trusted_phase3d_local_runtime_binding.v1",
        "local_transaction_result_id": execution.local_result.local_transaction_result_id,
        "work_vector_id": execution.work_vector.work_vector_id,
        "capability_binding_id": execution.local_result.capability_binding_id,
        "worker_result_binding_id": execution.local_result.worker_result_binding_id,
        "runtime_attestation_binding_id": execution.local_result.runtime_attestation_binding_id,
        "executor_profile": TRUSTED_LOCAL_EXECUTOR_PROFILE,
        "host_full_solver_replay": False,
        "official_execution_allowed": False,
    }
    return hashlib.sha256(
        b"acfqp:trusted-phase3d-local-runtime-binding:v1\x00"
        + canonical_json(payload).encode("utf-8")
    ).hexdigest()


def _postaudit_digest(execution: TrustedLocalExecutionV1) -> str:
    if execution.post_audit is None:
        raise Phase3ELocalSemanticV1Error("post-audit digest requires an artifact")
    payload = {
        "schema": "acfqp.trusted_phase3d_postaudit_runtime_binding.v1",
        "post_audit_certificate_id": execution.post_audit.post_audit_certificate_id,
        "local_transaction_result_id": execution.local_result.local_transaction_result_id,
        "work_vector_id": execution.work_vector.work_vector_id,
        "threshold_profile_id": execution.post_audit.threshold_profile_id,
        "auditor_profile": TRUSTED_POSTAUDIT_PROFILE,
        "host_full_solver_replay": False,
        "official_execution_allowed": False,
    }
    return hashlib.sha256(
        b"acfqp:trusted-phase3d-postaudit-runtime-binding:v1\x00"
        + canonical_json(payload).encode("utf-8")
    ).hexdigest()


def verify_trusted_local_runtime_provenance_v1(
    execution: TrustedLocalExecutionV1,
) -> None:
    execution = require_trusted_local_execution_authority_v1(execution)
    provenance = execution.local_provenance
    if (
        not isinstance(provenance, TrustedLocalRuntimeProvenanceV1)
        or provenance._authority is not _TRUSTED_LOCAL_RUNTIME_AUTHORITY
        or provenance.binding_digest != _local_digest(execution)
    ):
        raise Phase3ELocalSemanticV1Error("local execution lacks matching trusted provenance")


def verify_trusted_postaudit_runtime_provenance_v1(
    execution: TrustedLocalExecutionV1,
) -> None:
    verify_trusted_local_runtime_provenance_v1(execution)
    provenance = execution.postaudit_provenance
    if (
        execution.post_audit is None
        or not isinstance(provenance, TrustedPostAuditRuntimeProvenanceV1)
        or provenance._authority is not _TRUSTED_POSTAUDIT_RUNTIME_AUTHORITY
        or provenance.binding_digest != _postaudit_digest(execution)
    ):
        raise Phase3ELocalSemanticV1Error("post-audit execution lacks matching trusted provenance")


def _seal_trusted_execution_v1(
    *,
    local_result: LocalTransactionResultV1,
    post_audit: PostAuditCertificateV1 | None,
    work_vector: WorkVectorV1,
    threshold_profile: FrozenThresholdProfileV1 | None = None,
) -> TrustedLocalExecutionV1:
    """Private microscopic-test mint; production must mint at execution sites."""

    provisional = TrustedLocalExecutionV1(
        local_result,
        post_audit,
        work_vector,
        threshold_profile,
        TrustedLocalRuntimeProvenanceV1(
            "0" * 64, _authority=_TRUSTED_LOCAL_RUNTIME_AUTHORITY
        ),
        (
            None
            if post_audit is None
            else TrustedPostAuditRuntimeProvenanceV1(
                "0" * 64, _authority=_TRUSTED_POSTAUDIT_RUNTIME_AUTHORITY
            )
        ),
    )
    local_seal = TrustedLocalRuntimeProvenanceV1(
        _local_digest(provisional), _authority=_TRUSTED_LOCAL_RUNTIME_AUTHORITY
    )
    with_local = TrustedLocalExecutionV1(
        local_result,
        post_audit,
        work_vector,
        threshold_profile,
        local_seal,
        provisional.postaudit_provenance,
    )
    if post_audit is None:
        return bind_runtime_authority_v1(
            with_local,
            issuer=_TRUSTED_LOCAL_RUNTIME_AUTHORITY,
        )
    post_seal = TrustedPostAuditRuntimeProvenanceV1(
        _postaudit_digest(with_local), _authority=_TRUSTED_POSTAUDIT_RUNTIME_AUTHORITY
    )
    sealed = TrustedLocalExecutionV1(
        local_result,
        post_audit,
        work_vector,
        threshold_profile,
        local_seal,
        post_seal,
    )
    return bind_runtime_authority_v1(
        sealed,
        issuer=_TRUSTED_LOCAL_RUNTIME_AUTHORITY,
    )


def validate_local_execution_context_v1(
    execution: TrustedLocalExecutionV1,
    *,
    context: RouteDecisionContextV1,
    decision_point: DecisionPointV1,
    transaction: TransactionV1,
    cap_profile: RouteCapProfileV1,
) -> None:
    """Bind a trusted execution to one exact Phase-3E local transaction."""

    verify_trusted_local_runtime_provenance_v1(execution)
    result = execution.local_result
    expected = (
        context.route_decision_context_id,
        decision_point.decision_point_id,
        transaction.transaction_id,
        context.route_attempt_id,
        context.query_id,
        context.selected_plan_id,
        cap_profile.route_cap_profile_id,
    )
    actual = (
        result.route_decision_context_id,
        result.decision_point_id,
        result.transaction_id,
        result.route_attempt_id,
        result.query_id,
        result.selected_plan_id,
        result.route_cap_profile_id,
    )
    if actual != expected:
        raise Phase3ELocalSemanticV1Error("trusted local execution uses another context")
    if execution.post_audit is not None:
        threshold = execution.threshold_profile
        post = execution.post_audit
        if (
            threshold is None
            or threshold.threshold_profile_id != context.threshold_profile_id
            or threshold.query_id != context.query_id
            or post.threshold_profile_id != context.threshold_profile_id
            or post.route_decision_context_id != context.route_decision_context_id
            or post.selected_plan_id != context.selected_plan_id
        ):
            raise Phase3ELocalSemanticV1Error(
                "trusted post-audit uses another context or frozen threshold"
            )
    if (
        decision_point.route_decision_context_id != context.route_decision_context_id
        or transaction.logical_occurrence_id != context.logical_occurrence_id
        or transaction.route_attempt_id != context.route_attempt_id
        or transaction.decision_point_id != decision_point.decision_point_id
        or transaction.route_cap_profile_id != cap_profile.route_cap_profile_id
        or execution.work_vector.route_kind is not RouteKindEnum.LOCAL_ATTEMPT
        or execution.work_vector.subject_id != transaction.transaction_id
    ):
        raise Phase3ELocalSemanticV1Error("local transaction identity chain is inconsistent")


__all__ = [
    "FrozenThresholdProfileV1",
    "LocalSolverOutcome",
    "LocalTransactionResultV1",
    "Phase3ELocalSemanticV1Error",
    "PostAuditCertificateV1",
    "PostAuditOutcome",
    "TRUST_SCOPE",
    "TRUSTED_LOCAL_EXECUTOR_PROFILE",
    "TRUSTED_POSTAUDIT_PROFILE",
    "TrustedLocalExecutionV1",
    "TrustedLocalRuntimeProvenanceV1",
    "TrustedPostAuditRuntimeProvenanceV1",
    "require_trusted_local_execution_authority_v1",
    "validate_local_execution_context_v1",
    "verify_trusted_local_runtime_provenance_v1",
    "verify_trusted_postaudit_runtime_provenance_v1",
]
