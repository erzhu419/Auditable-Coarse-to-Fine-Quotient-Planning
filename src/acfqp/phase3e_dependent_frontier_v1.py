"""Oracle-free derivation of a transaction-2 proof frontier.

The occurrence runner already enforces the transaction budget and the fresh
identity chain.  This module narrows the missing causal seam: transaction 2 is
not opened from a caller-supplied hash or raw certificate.  Instead, a retained
``POST_AUDIT=FAILED`` semantic authority is reduced to explicit failed
obligations and those obligations determine a fresh stage-2 frontier.

The registered profile is deliberately small and synthetic.  It is a
non-official regression benchmark for dependent continuation mechanics, not a
claim that the general strategic quotient has been learned.  In particular,
the selector consumes only immutable proof artifacts and exact rational
bounds; it imports neither a ground kernel nor J0.

This module also does **not** provide production semantic handlers for the
synthetic route cardinalities/uppers used by the regression test.  The test
uses a test-only runtime/semantic-authority bridge while exercising the real
``run_phase3e`` executors, access protocol, transaction state machine, and
native occurrence aggregation.  Consequently this slice narrows, but does
not close, the remaining production obligation: this is a synthetic fresh
stage-2 obligation, not proof that a genuinely deeper ground distinction was
found.  A ground-derived dependent frontier with production semantic
authorities is still required.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    DEPENDENT_FRONTIER_DERIVATION_DOMAIN,
    DEPENDENT_POSTAUDIT_OBLIGATION_DOMAIN,
    DEPENDENT_TRANSACTION_BENCHMARK_PROFILE_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_local_semantics_v1 import (
    FrozenThresholdProfileV1,
    PostAuditCertificateV1,
    PostAuditOutcome,
)
from acfqp.routing_v1 import (
    CausalEvidenceV1,
    CausalOutcome,
    FrontierSnapshotV1,
    RouteCapProfileV1,
    RouteDecisionContextV1,
    TransactionV1,
)
from acfqp.semantic_verification_v1 import (
    SemanticRole,
    SemanticVerificationResultV1,
    SemanticVerificationV1Error,
    require_semantic_verification_result_v1,
    verify_typed_attestation_v1,
)


SCHEMA_VERSION = "1.0.0"
DEPENDENT_TRANSACTION_TWO_PROFILE_KEY = (
    "phase3e_dependent_postaudit_transaction_two_v0"
)


class DependentFrontierV1Error(ValueError):
    """A failed audit does not authorize the claimed stage-2 obligation."""


class FailedAuditObligationKind(str, Enum):
    REWARD_LOWER_MISSING = "REWARD_LOWER_MISSING"
    RISK_BOUND_MISSING = "RISK_BOUND_MISSING"
    RISK_EXCEEDS_THRESHOLD = "RISK_EXCEEDS_THRESHOLD"
    REGRET_BOUND_MISSING = "REGRET_BOUND_MISSING"
    REGRET_EXCEEDS_THRESHOLD = "REGRET_EXCEEDS_THRESHOLD"


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DependentFrontierV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class DependentTransactionBenchmarkProfileV1:
    """Frozen finite profile for the dependent-transaction regression."""

    profile_key: str = DEPENDENT_TRANSACTION_TWO_PROFILE_KEY
    first_transaction_index: int = 1
    second_transaction_index: int = 2
    max_local_transactions_per_logical_occurrence: int = 2
    selector_uses_ground_kernel: bool = False
    selector_uses_j0: bool = False
    synthetic_nonofficial_benchmark: bool = True
    synthetic_fresh_stage_two_obligation: bool = True
    proves_deeper_ground_distinction: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            self.profile_key != DEPENDENT_TRANSACTION_TWO_PROFILE_KEY
            or self.first_transaction_index != 1
            or self.second_transaction_index != 2
            or self.max_local_transactions_per_logical_occurrence != 2
            or self.selector_uses_ground_kernel is not False
            or self.selector_uses_j0 is not False
            or self.synthetic_nonofficial_benchmark is not True
            or self.synthetic_fresh_stage_two_obligation is not True
            or self.proves_deeper_ground_distinction is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise DependentFrontierV1Error(
                "dependent transaction benchmark profile was relaxed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.dependent_transaction_benchmark_profile.v1",
            "schema_version": self.schema_version,
            "profile_key": self.profile_key,
            "first_transaction_index": self.first_transaction_index,
            "second_transaction_index": self.second_transaction_index,
            "max_local_transactions_per_logical_occurrence": (
                self.max_local_transactions_per_logical_occurrence
            ),
            "selector_uses_ground_kernel": False,
            "selector_uses_j0": False,
            "synthetic_nonofficial_benchmark": True,
            "synthetic_fresh_stage_two_obligation": True,
            "proves_deeper_ground_distinction": False,
        }

    @property
    def dependent_transaction_benchmark_profile_id(self) -> str:
        return content_id(
            DEPENDENT_TRANSACTION_BENCHMARK_PROFILE_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "dependent_transaction_benchmark_profile_id": (
                self.dependent_transaction_benchmark_profile_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "DependentTransactionBenchmarkProfileV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "profile_key",
                "first_transaction_index",
                "second_transaction_index",
                "max_local_transactions_per_logical_occurrence",
                "selector_uses_ground_kernel",
                "selector_uses_j0",
                "synthetic_nonofficial_benchmark",
                "synthetic_fresh_stage_two_obligation",
                "proves_deeper_ground_distinction",
                "dependent_transaction_benchmark_profile_id",
            },
            context="dependent transaction benchmark profile",
        )
        if document["schema"] != (
            "acfqp.dependent_transaction_benchmark_profile.v1"
        ):
            raise DependentFrontierV1Error("benchmark profile schema mismatch")
        result = cls(
            document["profile_key"],
            document["first_transaction_index"],
            document["second_transaction_index"],
            document["max_local_transactions_per_logical_occurrence"],
            document["selector_uses_ground_kernel"],
            document["selector_uses_j0"],
            document["synthetic_nonofficial_benchmark"],
            document["synthetic_fresh_stage_two_obligation"],
            document["proves_deeper_ground_distinction"],
            document["schema_version"],
        )
        if document["dependent_transaction_benchmark_profile_id"] != (
            result.dependent_transaction_benchmark_profile_id
        ):
            raise DependentFrontierV1Error("benchmark profile ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DependentPostAuditObligationV1:
    """One synthetic stage-2 obligation extracted from verified post-audit."""

    profile_id: str
    post_audit_certificate_id: str
    post_audit_verification_attestation_id: str
    audit_issue_set_id: str
    stitched_plan_binding_id: str
    threshold_profile_id: str
    kind: FailedAuditObligationKind
    observed_bound: Fraction | None
    required_bound: Fraction | None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "profile_id",
            "post_audit_certificate_id",
            "post_audit_verification_attestation_id",
            "audit_issue_set_id",
            "stitched_plan_binding_id",
            "threshold_profile_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(
            self, "kind", FailedAuditObligationKind(self.kind)
        )
        for name in ("observed_bound", "required_bound"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, Fraction(value))
        if self.kind in {
            FailedAuditObligationKind.RISK_EXCEEDS_THRESHOLD,
            FailedAuditObligationKind.REGRET_EXCEEDS_THRESHOLD,
        }:
            if (
                self.observed_bound is None
                or self.required_bound is None
                or self.observed_bound <= self.required_bound
            ):
                raise DependentFrontierV1Error(
                    "exceeded-threshold obligation lacks an exact violation"
                )
        elif self.observed_bound is not None:
            raise DependentFrontierV1Error(
                "missing-bound obligation cannot carry an observed bound"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise DependentFrontierV1Error("obligation version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.dependent_postaudit_obligation.v1",
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "post_audit_certificate_id": self.post_audit_certificate_id,
            "post_audit_verification_attestation_id": (
                self.post_audit_verification_attestation_id
            ),
            "audit_issue_set_id": self.audit_issue_set_id,
            "stitched_plan_binding_id": self.stitched_plan_binding_id,
            "threshold_profile_id": self.threshold_profile_id,
            "kind": self.kind.value,
            "observed_bound": self.observed_bound,
            "required_bound": self.required_bound,
        }

    @property
    def dependent_postaudit_obligation_id(self) -> str:
        return content_id(
            DEPENDENT_POSTAUDIT_OBLIGATION_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "dependent_postaudit_obligation_id": (
                self.dependent_postaudit_obligation_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "DependentPostAuditObligationV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "profile_id",
                "post_audit_certificate_id",
                "post_audit_verification_attestation_id",
                "audit_issue_set_id",
                "stitched_plan_binding_id",
                "threshold_profile_id",
                "kind",
                "observed_bound",
                "required_bound",
                "dependent_postaudit_obligation_id",
            },
            context="dependent post-audit obligation",
        )
        if document["schema"] != "acfqp.dependent_postaudit_obligation.v1":
            raise DependentFrontierV1Error("obligation schema mismatch")
        result = cls(
            document["profile_id"],
            document["post_audit_certificate_id"],
            document["post_audit_verification_attestation_id"],
            document["audit_issue_set_id"],
            document["stitched_plan_binding_id"],
            document["threshold_profile_id"],
            document["kind"],
            document["observed_bound"],
            document["required_bound"],
            document["schema_version"],
        )
        if document["dependent_postaudit_obligation_id"] != (
            result.dependent_postaudit_obligation_id
        ):
            raise DependentFrontierV1Error("obligation ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DependentFrontierDerivationV1:
    """Replayable proof of a synthetic fresh stage-2 obligation."""

    profile_id: str
    first_route_decision_context_id: str
    first_frontier_snapshot_id: str
    first_causal_evidence_id: str
    first_transaction_id: str
    failed_post_audit_certificate_id: str
    failed_post_audit_verification_attestation_id: str
    failed_local_transaction_result_id: str
    failed_work_vector_id: str
    audit_issue_set_id: str
    stitched_plan_binding_id: str
    second_route_decision_context_id: str
    second_frontier_snapshot_id: str
    second_causal_evidence_id: str
    obligation_ids: tuple[str, ...]
    selector_uses_ground_kernel: bool = False
    selector_uses_j0: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "profile_id",
            "first_route_decision_context_id",
            "first_frontier_snapshot_id",
            "first_causal_evidence_id",
            "first_transaction_id",
            "failed_post_audit_certificate_id",
            "failed_post_audit_verification_attestation_id",
            "failed_local_transaction_result_id",
            "failed_work_vector_id",
            "audit_issue_set_id",
            "stitched_plan_binding_id",
            "second_route_decision_context_id",
            "second_frontier_snapshot_id",
            "second_causal_evidence_id",
        ):
            _cid(getattr(self, name), name)
        if (
            not self.obligation_ids
            or tuple(sorted(self.obligation_ids)) != self.obligation_ids
            or len(set(self.obligation_ids)) != len(self.obligation_ids)
        ):
            raise DependentFrontierV1Error(
                "dependent obligations must be nonempty, sorted, and unique"
            )
        for obligation_id in self.obligation_ids:
            _cid(obligation_id, "obligation_id")
        if (
            self.first_route_decision_context_id
            == self.second_route_decision_context_id
            or self.first_frontier_snapshot_id
            == self.second_frontier_snapshot_id
            or self.first_causal_evidence_id == self.second_causal_evidence_id
        ):
            raise DependentFrontierV1Error(
                "dependent transaction must use fresh context/frontier/causal IDs"
            )
        if (
            self.selector_uses_ground_kernel is not False
            or self.selector_uses_j0 is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise DependentFrontierV1Error(
                "dependent frontier selector exceeded its oracle-free scope"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.dependent_frontier_derivation.v1",
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "first_route_decision_context_id": (
                self.first_route_decision_context_id
            ),
            "first_frontier_snapshot_id": self.first_frontier_snapshot_id,
            "first_causal_evidence_id": self.first_causal_evidence_id,
            "first_transaction_id": self.first_transaction_id,
            "failed_post_audit_certificate_id": (
                self.failed_post_audit_certificate_id
            ),
            "failed_post_audit_verification_attestation_id": (
                self.failed_post_audit_verification_attestation_id
            ),
            "failed_local_transaction_result_id": (
                self.failed_local_transaction_result_id
            ),
            "failed_work_vector_id": self.failed_work_vector_id,
            "audit_issue_set_id": self.audit_issue_set_id,
            "stitched_plan_binding_id": self.stitched_plan_binding_id,
            "second_route_decision_context_id": (
                self.second_route_decision_context_id
            ),
            "second_frontier_snapshot_id": self.second_frontier_snapshot_id,
            "second_causal_evidence_id": self.second_causal_evidence_id,
            "obligation_ids": list(self.obligation_ids),
            "selector_uses_ground_kernel": False,
            "selector_uses_j0": False,
        }

    @property
    def dependent_frontier_derivation_id(self) -> str:
        return content_id(DEPENDENT_FRONTIER_DERIVATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "dependent_frontier_derivation_id": (
                self.dependent_frontier_derivation_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "DependentFrontierDerivationV1":
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "profile_id",
                "first_route_decision_context_id",
                "first_frontier_snapshot_id",
                "first_causal_evidence_id",
                "first_transaction_id",
                "failed_post_audit_certificate_id",
                "failed_post_audit_verification_attestation_id",
                "failed_local_transaction_result_id",
                "failed_work_vector_id",
                "audit_issue_set_id",
                "stitched_plan_binding_id",
                "second_route_decision_context_id",
                "second_frontier_snapshot_id",
                "second_causal_evidence_id",
                "obligation_ids",
                "selector_uses_ground_kernel",
                "selector_uses_j0",
                "dependent_frontier_derivation_id",
            },
            context="dependent frontier derivation",
        )
        if (
            document["schema"] != "acfqp.dependent_frontier_derivation.v1"
            or type(document["obligation_ids"]) is not list
        ):
            raise DependentFrontierV1Error("derivation schema mismatch")
        result = cls(
            document["profile_id"],
            document["first_route_decision_context_id"],
            document["first_frontier_snapshot_id"],
            document["first_causal_evidence_id"],
            document["first_transaction_id"],
            document["failed_post_audit_certificate_id"],
            document["failed_post_audit_verification_attestation_id"],
            document["failed_local_transaction_result_id"],
            document["failed_work_vector_id"],
            document["audit_issue_set_id"],
            document["stitched_plan_binding_id"],
            document["second_route_decision_context_id"],
            document["second_frontier_snapshot_id"],
            document["second_causal_evidence_id"],
            tuple(document["obligation_ids"]),
            document["selector_uses_ground_kernel"],
            document["selector_uses_j0"],
            document["schema_version"],
        )
        if document["dependent_frontier_derivation_id"] != (
            result.dependent_frontier_derivation_id
        ):
            raise DependentFrontierV1Error("derivation ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class DerivedDependentFrontierV1:
    profile: DependentTransactionBenchmarkProfileV1
    obligations: tuple[DependentPostAuditObligationV1, ...]
    frontier: FrontierSnapshotV1
    causal: CausalEvidenceV1
    derivation: DependentFrontierDerivationV1

    def __post_init__(self) -> None:
        obligation_ids = tuple(
            sorted(row.dependent_postaudit_obligation_id for row in self.obligations)
        )
        if (
            not self.obligations
            or obligation_ids != self.frontier.failed_obligation_ids
            or obligation_ids != self.causal.proof_obligation_ids
            or obligation_ids != self.derivation.obligation_ids
            or self.frontier.frontier_snapshot_id
            != self.causal.frontier_snapshot_id
            or self.frontier.frontier_snapshot_id
            != self.derivation.second_frontier_snapshot_id
            or self.causal.causal_evidence_id
            != self.derivation.second_causal_evidence_id
            or self.profile.dependent_transaction_benchmark_profile_id
            != self.derivation.profile_id
            or any(
                row.post_audit_verification_attestation_id
                != self.derivation.failed_post_audit_verification_attestation_id
                for row in self.obligations
            )
        ):
            raise DependentFrontierV1Error(
                "derived frontier result has a stale causal/obligation chain"
            )


_STABLE_CONTEXT_FIELDS = (
    "preregistration_id",
    "protocol_id",
    "comparison_profile_id",
    "counter_registry_id",
    "structural_id",
    "query_id",
    "threshold_profile_id",
    "build_epoch_id",
    "logical_occurrence_id",
    "route_attempt_id",
)


def _failed_obligations_v1(
    *,
    profile: DependentTransactionBenchmarkProfileV1,
    post_audit: PostAuditCertificateV1,
    post_audit_verification_attestation_id: str,
    threshold: FrozenThresholdProfileV1,
) -> tuple[DependentPostAuditObligationV1, ...]:
    common = (
        profile.dependent_transaction_benchmark_profile_id,
        post_audit.post_audit_certificate_id,
        post_audit_verification_attestation_id,
        post_audit.audit_issue_set_id,
        post_audit.stitched_plan_binding_id,
        post_audit.threshold_profile_id,
    )
    rows: list[DependentPostAuditObligationV1] = []
    if post_audit.lifted_reward_lower is None:
        rows.append(
            DependentPostAuditObligationV1(
                *common,
                FailedAuditObligationKind.REWARD_LOWER_MISSING,
                None,
                None,
            )
        )
    if post_audit.lifted_failure_upper is None:
        rows.append(
            DependentPostAuditObligationV1(
                *common,
                FailedAuditObligationKind.RISK_BOUND_MISSING,
                None,
                threshold.risk_tolerance,
            )
        )
    elif post_audit.lifted_failure_upper > threshold.risk_tolerance:
        rows.append(
            DependentPostAuditObligationV1(
                *common,
                FailedAuditObligationKind.RISK_EXCEEDS_THRESHOLD,
                post_audit.lifted_failure_upper,
                threshold.risk_tolerance,
            )
        )
    if post_audit.regret_upper is None:
        rows.append(
            DependentPostAuditObligationV1(
                *common,
                FailedAuditObligationKind.REGRET_BOUND_MISSING,
                None,
                threshold.regret_tolerance,
            )
        )
    elif post_audit.regret_upper > threshold.regret_tolerance:
        rows.append(
            DependentPostAuditObligationV1(
                *common,
                FailedAuditObligationKind.REGRET_EXCEEDS_THRESHOLD,
                post_audit.regret_upper,
                threshold.regret_tolerance,
            )
        )
    return tuple(
        sorted(rows, key=lambda row: row.dependent_postaudit_obligation_id)
    )


def derive_dependent_frontier_from_failed_postaudit_v1(
    *,
    first_context: RouteDecisionContextV1,
    first_frontier: FrontierSnapshotV1,
    first_causal: CausalEvidenceV1,
    first_transaction: TransactionV1,
    post_audit_failure_result: SemanticVerificationResultV1,
    threshold_profile: FrozenThresholdProfileV1,
    second_context: RouteDecisionContextV1,
    cap_profile: RouteCapProfileV1,
    profile: DependentTransactionBenchmarkProfileV1 | None = None,
) -> DerivedDependentFrontierV1:
    """Derive the registered synthetic stage-2 obligation without an oracle.

    The failed audit must be an authority-bearing runtime semantic result, not
    a raw certificate or attestation.  Numeric causes are taken from exact
    post-audit bounds, never from a ground-state query.  The resulting stage-2
    frontier is fresh and dependent, but does not prove that a deeper ground
    distinction was discovered.
    """

    frozen_profile = profile or DependentTransactionBenchmarkProfileV1()
    try:
        verified_post_audit = require_semantic_verification_result_v1(
            post_audit_failure_result, SemanticRole.POST_AUDIT
        )
        verify_typed_attestation_v1(
            verified_post_audit.attestation,
            authority_result=verified_post_audit,
        )
    except (SemanticVerificationV1Error, TypeError, ValueError) as error:
        raise DependentFrontierV1Error(
            f"transaction 2 requires retained POST_AUDIT=FAILED authority: {error}"
        ) from error
    if type(verified_post_audit.artifact) is not PostAuditCertificateV1:
        raise DependentFrontierV1Error(
            "transaction 2 POST_AUDIT authority carries the wrong artifact"
        )
    failed_post_audit = verified_post_audit.artifact
    if (
        verified_post_audit.outcome != PostAuditOutcome.FAILED.value
        or verified_post_audit.attestation.artifact_id
        != failed_post_audit.post_audit_certificate_id
        or verified_post_audit.attestation.verification_result
        != PostAuditOutcome.FAILED.value
        or verified_post_audit.binding.route_context != first_context
        or verified_post_audit.binding.decision_point_id
        != first_transaction.decision_point_id
        or verified_post_audit.binding.transaction_id
        != first_transaction.transaction_id
    ):
        raise DependentFrontierV1Error(
            "POST_AUDIT=FAILED authority uses another context or transaction"
        )
    if failed_post_audit.outcome is not PostAuditOutcome.FAILED:
        raise DependentFrontierV1Error(
            "transaction 2 requires a sound FAILED post-audit"
        )
    if (
        first_transaction.transaction_index
        != frozen_profile.first_transaction_index
        or first_frontier.frontier_stage
        != frozen_profile.first_transaction_index
    ):
        raise DependentFrontierV1Error(
            "dependent continuation must begin at transaction/frontier stage 1"
        )
    if (
        first_frontier.route_decision_context_id
        != first_context.route_decision_context_id
        or first_causal.frontier_snapshot_id
        != first_frontier.frontier_snapshot_id
        or first_causal.outcome is not CausalOutcome.FOUND
        or first_causal.local_allowed is not True
        or first_causal.cap_id != cap_profile.route_cap_profile_id
        or first_transaction.logical_occurrence_id
        != first_context.logical_occurrence_id
        or first_transaction.route_attempt_id != first_context.route_attempt_id
        or first_transaction.frontier_snapshot_id
        != first_frontier.frontier_snapshot_id
        or first_transaction.route_cap_profile_id
        != cap_profile.route_cap_profile_id
    ):
        raise DependentFrontierV1Error(
            "transaction-1 context/frontier/causal/cap chain is stale"
        )
    if (
        failed_post_audit.route_decision_context_id
        != first_context.route_decision_context_id
        or failed_post_audit.decision_point_id
        != first_transaction.decision_point_id
        or failed_post_audit.transaction_id != first_transaction.transaction_id
        or failed_post_audit.route_attempt_id != first_context.route_attempt_id
        or failed_post_audit.query_id != first_context.query_id
        or failed_post_audit.selected_plan_id != first_context.selected_plan_id
        or failed_post_audit.threshold_profile_id
        != first_context.threshold_profile_id
        or threshold_profile.threshold_profile_id
        != first_context.threshold_profile_id
        or threshold_profile.query_id != first_context.query_id
    ):
        raise DependentFrontierV1Error(
            "failed post-audit does not bind transaction 1 and its threshold"
        )
    for field_name in _STABLE_CONTEXT_FIELDS:
        if getattr(second_context, field_name) != getattr(
            first_context, field_name
        ):
            raise DependentFrontierV1Error(
                f"transaction 2 changed stable context field {field_name}"
            )
    if second_context.selected_plan_id != (
        failed_post_audit.stitched_plan_binding_id
    ):
        raise DependentFrontierV1Error(
            "transaction-2 context must bind the failed audit's stitched plan"
        )
    if second_context.route_decision_context_id == (
        first_context.route_decision_context_id
    ):
        raise DependentFrontierV1Error(
            "transaction 2 reused the first route-decision context"
        )

    obligations = _failed_obligations_v1(
        profile=frozen_profile,
        post_audit=failed_post_audit,
        post_audit_verification_attestation_id=(
            verified_post_audit.attestation.verification_attestation_id
        ),
        threshold=threshold_profile,
    )
    if not obligations:
        raise DependentFrontierV1Error(
            "FAILED post-audit has no replayable value/risk proof cause"
        )
    obligation_ids = tuple(
        sorted(row.dependent_postaudit_obligation_id for row in obligations)
    )
    frontier = FrontierSnapshotV1(
        second_context.route_decision_context_id,
        frozen_profile.second_transaction_index,
        obligation_ids,
    )
    causal = CausalEvidenceV1(
        frontier.frontier_snapshot_id,
        CausalOutcome.FOUND,
        True,
        None,
        len(obligations),
        cap_profile.route_cap_profile_id,
        obligation_ids,
    )
    derivation = DependentFrontierDerivationV1(
        frozen_profile.dependent_transaction_benchmark_profile_id,
        first_context.route_decision_context_id,
        first_frontier.frontier_snapshot_id,
        first_causal.causal_evidence_id,
        first_transaction.transaction_id,
        failed_post_audit.post_audit_certificate_id,
        verified_post_audit.attestation.verification_attestation_id,
        failed_post_audit.local_transaction_result_id,
        failed_post_audit.work_vector_id,
        failed_post_audit.audit_issue_set_id,
        failed_post_audit.stitched_plan_binding_id,
        second_context.route_decision_context_id,
        frontier.frontier_snapshot_id,
        causal.causal_evidence_id,
        obligation_ids,
    )
    return DerivedDependentFrontierV1(
        frozen_profile, obligations, frontier, causal, derivation
    )


__all__ = [
    "DEPENDENT_TRANSACTION_TWO_PROFILE_KEY",
    "DependentFrontierDerivationV1",
    "DependentFrontierV1Error",
    "DependentPostAuditObligationV1",
    "DependentTransactionBenchmarkProfileV1",
    "DerivedDependentFrontierV1",
    "FailedAuditObligationKind",
    "derive_dependent_frontier_from_failed_postaudit_v1",
]
