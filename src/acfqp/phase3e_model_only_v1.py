"""Production model-only Phase-3E planning and certification orchestration.

This module is the query-time front door for a reusable Phase-3C RAPM.  It
opens an integrity-checked model/query source lease, selects a contingent plan,
and constructs and replays the rectangular-envelope sound certificate.  A
ground binding is authorized *only* by a typed ``FAIL`` result; a ``PASS``
result is complete without constructing a ground state, action, kernel, or
concretizer.

The module deliberately does not import ``acfqp.domains``,
``acfqp.frozen_phase3c``, or any local/fallback executor.  The five parent
identities below reproduce the exact domain and payload used by
``safe_chain_fallback_context_identity_v1`` so a later FAIL consumer can open
the ground namespace without changing structural, query, epoch, manifest, or
portable-model identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping

from acfqp.accounting_v1 import (
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.campaign_v1 import LogicalOccurrenceV1, RebuildPolicyV1, RouteAttemptV1
from acfqp.phase3e_ids import (
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
    MODEL_ONLY_RESULT_DOMAIN,
    Phase3EIdentityError,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    ABSTRACT_QUERY_KEY,
    LOCAL_QUERY_KEY,
    ModelOnlyRAPMSourceV1,
    RAPMSourceLeaseV1,
    SelectedContingentPlanV1,
    load_phase3c_model_source_v1,
    require_model_only_source_authority_v1,
    select_contingent_plan_v1,
)
from acfqp.portable import fraction_from_json
from acfqp.portable_sound_audit_v1 import (
    AbstractPlanAuditV1,
    PortableSoundAuditV1Error,
    PortableSoundBellmanProofV1,
    build_portable_sound_audit_v1,
    verify_portable_sound_audit_v1,
)
from acfqp.routing_v1 import RouteDecisionContextV1


SCHEMA_VERSION = "1.0.0"
MODEL_ONLY_IDENTITIES_SCHEMA = "acfqp.phase3e_model_only_identities.v1"
MODEL_ONLY_RESULT_SCHEMA = "acfqp.phase3e_model_only_result.v1"
MODEL_ONLY_PROTOCOL_KEY = "manifest_rapm_plan_sound_audit_then_ground_on_fail_v1"
MODEL_ONLY_PREREGISTRATION_KEY = "phase3e_model_only_consumer_v1"

_OCCURRENCE_INDEX_BY_QUERY_KEY = {
    ABSTRACT_QUERY_KEY: 1,
    LOCAL_QUERY_KEY: 2,
}


class Phase3EModelOnlyV1Error(ValueError):
    """The model-only chain or one of its typed bindings is invalid."""


class ModelOnlyOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _orchestration_binding_id(role: str, payload: Any) -> str:
    if type(role) is not str or not role:
        raise Phase3EModelOnlyV1Error("orchestration binding role is empty")
    return content_id(
        MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
        {
            "schema": "acfqp.phase3e_model_only_orchestration_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "role": role,
            "payload": payload,
        },
    )


def _fallback_parent_id(role: str, payload: Any) -> str:
    """Exact duplicate of the ground binder's parent-identity construction."""

    return content_id(
        GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
        {
            "schema": "acfqp.safe_chain_fallback_parent_binding.v1",
            "role": role,
            "payload": payload,
        },
    )


@dataclass(frozen=True, slots=True)
class ModelOnlyPhase3EIdentitiesV1:
    """Ground-independent subset of the eventual Phase-3E route namespace."""

    structural_id: str
    query_id: str
    build_epoch_id: str
    manifest_id: str
    portable_rapm_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "structural_id",
            "query_id",
            "build_epoch_id",
            "manifest_id",
            "portable_rapm_id",
        ):
            try:
                parse_content_id(getattr(self, field_name))
            except Phase3EIdentityError as error:
                raise Phase3EModelOnlyV1Error(
                    f"{field_name} must be a full content ID"
                ) from error

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MODEL_ONLY_IDENTITIES_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "manifest_id": self.manifest_id,
            "portable_rapm_id": self.portable_rapm_id,
        }

    @property
    def identities_id(self) -> str:
        return _orchestration_binding_id("model_only_parent_identities", self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "identities_id": self.identities_id}

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ModelOnlyPhase3EIdentitiesV1":
        try:
            require_exact_fields(
                document,
                {
                    "schema",
                    "schema_version",
                    "structural_id",
                    "query_id",
                    "BuildEpoch_id",
                    "manifest_id",
                    "portable_rapm_id",
                    "identities_id",
                },
                context="ModelOnlyPhase3EIdentitiesV1",
            )
        except Phase3EIdentityError as error:
            raise Phase3EModelOnlyV1Error(str(error)) from error
        if (
            document["schema"] != MODEL_ONLY_IDENTITIES_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3EModelOnlyV1Error("unsupported model-only identity schema")
        result = cls(
            document["structural_id"],
            document["query_id"],
            document["BuildEpoch_id"],
            document["manifest_id"],
            document["portable_rapm_id"],
        )
        if document["identities_id"] != result.identities_id:
            raise Phase3EModelOnlyV1Error("model-only identities ID mismatch")
        return result


def derive_model_only_phase3e_identities_v1(
    source: ModelOnlyRAPMSourceV1,
) -> ModelOnlyPhase3EIdentitiesV1:
    """Derive identities byte-for-byte compatible with the later ground binder."""

    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyV1Error(
            f"source lacks live RAPM authority: {error}"
        ) from error
    lease = source.lease
    return ModelOnlyPhase3EIdentitiesV1(
        structural_id=_fallback_parent_id(
            "structural", {"legacy_structural_id": lease.legacy_structural_id}
        ),
        query_id=_fallback_parent_id(
            "query",
            {
                "legacy_query_id": lease.legacy_ground_query_id,
                "query_key": lease.query_key,
            },
        ),
        build_epoch_id=_fallback_parent_id(
            "build_epoch",
            {
                "legacy_build_epoch_id": lease.legacy_build_epoch_id,
                "serialized_sha256": lease.build_epoch_sha256,
            },
        ),
        manifest_id=_fallback_parent_id(
            "manifest",
            {
                "manifest_sha256": lease.source_manifest_sha256,
                "run_id": lease.source_run_id,
            },
        ),
        portable_rapm_id=_fallback_parent_id(
            "portable_rapm",
            {
                "model_id": lease.legacy_portable_rapm_id,
                "serialized_sha256": lease.portable_rapm_sha256,
            },
        ),
    )


def _campaign_bindings_v1(
    *,
    source: ModelOnlyRAPMSourceV1,
    identities: ModelOnlyPhase3EIdentitiesV1,
    selected_plan: SelectedContingentPlanV1,
    regret_tolerance: Fraction,
) -> tuple[
    RebuildPolicyV1,
    LogicalOccurrenceV1,
    RouteAttemptV1,
    RouteDecisionContextV1,
]:
    """Freeze the canonical campaign/attempt/context chain without ground data."""

    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyV1Error(
            f"source lacks live RAPM authority: {error}"
        ) from error

    registry = official_counter_registry_v1()
    comparison = official_comparison_profile_v1(registry)
    workload_spec_id = _orchestration_binding_id(
        "workload_spec",
        {
            "profile_key": MODEL_ONLY_PREREGISTRATION_KEY,
            "source_lease_id": source.lease.source_lease_id,
            "source_manifest_id": identities.manifest_id,
        },
    )
    protocol_id = _orchestration_binding_id(
        "protocol", {"profile_key": MODEL_ONLY_PROTOCOL_KEY}
    )
    query_document = source.query.to_dict()
    # Route continuation must retain the one canonical threshold identity
    # consumed by local post-audit.  The helper lives outside the forbidden
    # local/ground module family so the model-only worker keeps its isolation.
    from acfqp.phase3e_threshold_v1 import portable_threshold_profile_id_v1

    threshold_profile_id = portable_threshold_profile_id_v1(
        identities.query_id,
        regret_tolerance,
        fraction_from_json(
            query_document["delta"], field="portable query delta"
        ),
    )
    rebuild_policy = RebuildPolicyV1()
    occurrence = LogicalOccurrenceV1(
        workload_spec_id=workload_spec_id,
        protocol_id=protocol_id,
        occurrence_index=_OCCURRENCE_INDEX_BY_QUERY_KEY[source.lease.query_key],
        structural_id=identities.structural_id,
        query_id=identities.query_id,
        selected_plan_id=selected_plan.selected_contingent_plan_id,
        threshold_profile_id=threshold_profile_id,
        initial_build_epoch_id=identities.build_epoch_id,
        rebuild_policy_id=rebuild_policy.rebuild_policy_id,
    )
    attempt = RouteAttemptV1.initial(occurrence)
    context = RouteDecisionContextV1(
        preregistration_id=_orchestration_binding_id(
            "preregistration",
            {
                "profile_key": MODEL_ONLY_PREREGISTRATION_KEY,
                "source_lease_id": source.lease.source_lease_id,
                "query_key": source.lease.query_key,
            },
        ),
        protocol_id=protocol_id,
        comparison_profile_id=comparison.comparison_profile_id,
        counter_registry_id=registry.registry_id,
        structural_id=identities.structural_id,
        query_id=identities.query_id,
        selected_plan_id=selected_plan.selected_contingent_plan_id,
        threshold_profile_id=threshold_profile_id,
        build_epoch_id=identities.build_epoch_id,
        logical_occurrence_id=occurrence.logical_occurrence_id,
        route_attempt_id=attempt.route_attempt_id,
    )
    return rebuild_policy, occurrence, attempt, context


@dataclass(frozen=True, slots=True)
class Phase3EModelOnlyResultV1:
    """Replayable result of planning and auditing wholly inside the RAPM."""

    source_lease: RAPMSourceLeaseV1
    identities: ModelOnlyPhase3EIdentitiesV1
    selected_plan: SelectedContingentPlanV1
    sound_proof: PortableSoundBellmanProofV1
    audit: AbstractPlanAuditV1
    outcome: ModelOnlyOutcome
    ground_binding_required: bool
    rebuild_policy: RebuildPolicyV1
    logical_occurrence: LogicalOccurrenceV1
    route_attempt: RouteAttemptV1
    route_context: RouteDecisionContextV1

    def __post_init__(self) -> None:
        if self.selected_plan.source_lease_id != self.source_lease.source_lease_id:
            raise Phase3EModelOnlyV1Error("selected plan/source lease mismatch")
        if (
            self.selected_plan.legacy_portable_model_id
            != self.source_lease.legacy_portable_rapm_id
            or self.selected_plan.legacy_portable_query_id
            != self.source_lease.legacy_portable_query_id
        ):
            raise Phase3EModelOnlyV1Error("selected plan/source model mismatch")
        if (
            self.sound_proof.model_id != self.source_lease.legacy_portable_rapm_id
            or self.sound_proof.query_id != self.source_lease.legacy_portable_query_id
        ):
            raise Phase3EModelOnlyV1Error("sound proof/source mismatch")
        if (
            self.audit.model_id != self.sound_proof.model_id
            or self.audit.query_id != self.sound_proof.query_id
            or self.audit.policy_id != self.sound_proof.policy_id
            or self.audit.proof_id != self.sound_proof.proof_id
        ):
            raise Phase3EModelOnlyV1Error("abstract audit/proof mismatch")
        if self.outcome.value != self.audit.outcome:
            raise Phase3EModelOnlyV1Error("typed outcome/audit mismatch")
        expected_ground = self.outcome is ModelOnlyOutcome.FAIL
        if self.ground_binding_required is not expected_ground:
            raise Phase3EModelOnlyV1Error(
                "ground binding is required exactly for a failed audit"
            )
        if not isinstance(self.route_context, RouteDecisionContextV1):
            raise Phase3EModelOnlyV1Error(
                "route_context must freeze the selected plan before audit handling"
            )
        if not isinstance(self.rebuild_policy, RebuildPolicyV1):
            raise Phase3EModelOnlyV1Error("rebuild_policy must be RebuildPolicyV1")
        if not isinstance(self.logical_occurrence, LogicalOccurrenceV1):
            raise Phase3EModelOnlyV1Error(
                "logical_occurrence must be LogicalOccurrenceV1"
            )
        if not isinstance(self.route_attempt, RouteAttemptV1):
            raise Phase3EModelOnlyV1Error("route_attempt must be RouteAttemptV1")
        if (
            self.logical_occurrence.rebuild_policy_id
            != self.rebuild_policy.rebuild_policy_id
            or self.logical_occurrence.logical_occurrence_id
            != self.route_attempt.logical_occurrence_id
            or self.logical_occurrence.initial_build_epoch_id
            != self.route_attempt.build_epoch_id
            or self.route_attempt.route_attempt_index != 1
        ):
            raise Phase3EModelOnlyV1Error(
                "campaign occurrence/attempt/rebuild chain is inconsistent"
            )
        context = self.route_context
        expected = {
            "structural_id": self.identities.structural_id,
            "query_id": self.identities.query_id,
            "selected_plan_id": self.selected_plan.selected_contingent_plan_id,
            "build_epoch_id": self.identities.build_epoch_id,
        }
        for field_name, value in expected.items():
            if getattr(context, field_name) != value:
                raise Phase3EModelOnlyV1Error(
                    f"route context mismatch for {field_name}"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MODEL_ONLY_RESULT_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "source_lease": self.source_lease.to_dict(),
            "identities": self.identities.to_dict(),
            "selected_plan": self.selected_plan.to_dict(),
            "sound_proof": self.sound_proof.to_dict(),
            "audit": self.audit.to_dict(),
            "outcome": self.outcome.value,
            "ground_binding_required": self.ground_binding_required,
            "rebuild_policy": self.rebuild_policy.to_dict(),
            "logical_occurrence": self.logical_occurrence.to_dict(),
            "route_attempt": self.route_attempt.to_dict(),
            "route_context": self.route_context.to_dict(),
        }

    @property
    def result_id(self) -> str:
        return content_id(MODEL_ONLY_RESULT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        source: ModelOnlyRAPMSourceV1,
    ) -> "Phase3EModelOnlyResultV1":
        try:
            require_model_only_source_authority_v1(source)
        except ValueError as error:
            raise Phase3EModelOnlyV1Error(
                f"source lacks live RAPM authority: {error}"
            ) from error
        try:
            require_exact_fields(
                document,
                {
                    "schema",
                    "schema_version",
                    "source_lease",
                    "identities",
                    "selected_plan",
                    "sound_proof",
                    "audit",
                    "outcome",
                    "ground_binding_required",
                    "rebuild_policy",
                    "logical_occurrence",
                    "route_attempt",
                    "route_context",
                    "result_id",
                },
                context="Phase3EModelOnlyResultV1",
            )
        except Phase3EIdentityError as error:
            raise Phase3EModelOnlyV1Error(str(error)) from error
        if (
            document["schema"] != MODEL_ONLY_RESULT_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3EModelOnlyV1Error("unsupported model-only result schema")
        try:
            lease = RAPMSourceLeaseV1.from_dict(document["source_lease"])
            identities = ModelOnlyPhase3EIdentitiesV1.from_dict(
                document["identities"]
            )
            selected_plan = SelectedContingentPlanV1.from_dict(
                document["selected_plan"], source=source
            )
            proof = PortableSoundBellmanProofV1.from_dict(document["sound_proof"])
            audit = AbstractPlanAuditV1.from_dict(document["audit"])
            outcome = ModelOnlyOutcome(document["outcome"])
            rebuild_policy = RebuildPolicyV1.from_dict(document["rebuild_policy"])
            occurrence = LogicalOccurrenceV1.from_dict(
                document["logical_occurrence"]
            )
            attempt = RouteAttemptV1.from_dict(document["route_attempt"])
            context = RouteDecisionContextV1.from_dict(document["route_context"])
        except (ValueError, TypeError, KeyError) as error:
            raise Phase3EModelOnlyV1Error(
                f"invalid model-only result member: {error}"
            ) from error
        result = cls(
            lease,
            identities,
            selected_plan,
            proof,
            audit,
            outcome,
            document["ground_binding_required"],
            rebuild_policy,
            occurrence,
            attempt,
            context,
        )
        expected = run_phase3e_model_only_from_source_v1(
            source, regret_tolerance=audit.regret_tolerance
        )
        if result.to_dict() != expected.to_dict():
            raise Phase3EModelOnlyV1Error(
                "model-only result does not match deterministic semantic replay"
            )
        if document["result_id"] != result.result_id:
            raise Phase3EModelOnlyV1Error("model-only result content ID mismatch")
        return result


def verify_phase3e_model_only_result_without_replanning_v1(
    value: Phase3EModelOnlyResultV1 | Mapping[str, Any],
    *,
    source: ModelOnlyRAPMSourceV1,
) -> Phase3EModelOnlyResultV1:
    """Strictly replay a frozen model-only result without invoking a planner.

    ``Phase3EModelOnlyResultV1.from_dict`` is the independent end-to-end replay
    entry point and intentionally runs the portable planner again.  Operational
    semantic verification must not do that hidden duplicate work.  This helper
    instead validates every serialized member, replays the sound Bellman proof,
    and re-derives the identity/campaign/context chain from the already frozen
    selected plan.  It never calls ``solve_portable_pareto`` or
    ``select_contingent_plan_v1``.
    """

    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyV1Error(
            f"no-replanning verification requires live source authority: {error}"
        ) from error
    document = value.to_dict() if type(value) is Phase3EModelOnlyResultV1 else value
    try:
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "source_lease",
                "identities",
                "selected_plan",
                "sound_proof",
                "audit",
                "outcome",
                "ground_binding_required",
                "rebuild_policy",
                "logical_occurrence",
                "route_attempt",
                "route_context",
                "result_id",
            },
            context="Phase3EModelOnlyResultV1 no-replanning replay",
        )
    except Phase3EIdentityError as error:
        raise Phase3EModelOnlyV1Error(str(error)) from error
    if (
        document["schema"] != MODEL_ONLY_RESULT_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise Phase3EModelOnlyV1Error("unsupported model-only result schema")
    try:
        # Round-trip the lease on both sides; a retained source object is not a
        # license to skip its immutable content binding.
        source_lease = RAPMSourceLeaseV1.from_dict(source.lease.to_dict())
        lease = RAPMSourceLeaseV1.from_dict(document["source_lease"])
        identities = ModelOnlyPhase3EIdentitiesV1.from_dict(
            document["identities"]
        )
        selected_plan = SelectedContingentPlanV1.from_dict(
            document["selected_plan"], source=source
        )
        proof = PortableSoundBellmanProofV1.from_dict(document["sound_proof"])
        audit = AbstractPlanAuditV1.from_dict(document["audit"])
        outcome = ModelOnlyOutcome(document["outcome"])
        rebuild_policy = RebuildPolicyV1.from_dict(document["rebuild_policy"])
        occurrence = LogicalOccurrenceV1.from_dict(document["logical_occurrence"])
        attempt = RouteAttemptV1.from_dict(document["route_attempt"])
        context = RouteDecisionContextV1.from_dict(document["route_context"])
    except (ValueError, TypeError, KeyError) as error:
        raise Phase3EModelOnlyV1Error(
            f"invalid no-replanning model-only result member: {error}"
        ) from error
    if lease != source_lease:
        raise Phase3EModelOnlyV1Error("model-only result/source lease mismatch")

    try:
        verified_audit = verify_portable_sound_audit_v1(
            source.model,
            source.query,
            selected_plan.proposal.policy,
            proof,
            audit,
        )
    except PortableSoundAuditV1Error as error:
        raise Phase3EModelOnlyV1Error(
            f"portable sound audit failed no-replanning replay: {error}"
        ) from error
    if verified_audit != audit:
        raise Phase3EModelOnlyV1Error("sound-audit replay changed the claimed audit")

    expected_identities = derive_model_only_phase3e_identities_v1(source)
    expected_campaign = _campaign_bindings_v1(
        source=source,
        identities=expected_identities,
        selected_plan=selected_plan,
        regret_tolerance=audit.regret_tolerance,
    )
    if identities != expected_identities:
        raise Phase3EModelOnlyV1Error(
            "model-only identities differ from source-lease derivation"
        )
    if (
        rebuild_policy,
        occurrence,
        attempt,
        context,
    ) != expected_campaign:
        raise Phase3EModelOnlyV1Error(
            "model-only campaign/context differs from frozen-plan derivation"
        )

    result = Phase3EModelOnlyResultV1(
        lease,
        identities,
        selected_plan,
        proof,
        audit,
        outcome,
        document["ground_binding_required"],
        rebuild_policy,
        occurrence,
        attempt,
        context,
    )
    try:
        claimed_result_id = parse_content_id(document["result_id"])
    except Phase3EIdentityError as error:
        raise Phase3EModelOnlyV1Error("model-only result ID is invalid") from error
    if claimed_result_id != result.result_id:
        raise Phase3EModelOnlyV1Error("model-only result content ID mismatch")
    return result


def run_phase3e_model_only_from_source_v1(
    source: ModelOnlyRAPMSourceV1,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
    operation_counter: Callable[[str, int], None] | None = None,
) -> Phase3EModelOnlyResultV1:
    """Plan, prove, and replay one already-acquired model-only source."""

    try:
        require_model_only_source_authority_v1(source)
    except ValueError as error:
        raise Phase3EModelOnlyV1Error(
            f"source lacks live RAPM authority: {error}"
        ) from error
    if isinstance(regret_tolerance, bool) or not isinstance(
        regret_tolerance, (int, Fraction)
    ):
        raise Phase3EModelOnlyV1Error("regret_tolerance must be exact")
    tolerance = Fraction(regret_tolerance)
    if tolerance < 0:
        raise Phase3EModelOnlyV1Error("regret_tolerance must be nonnegative")
    selected_plan = select_contingent_plan_v1(
        source, operation_counter=operation_counter
    )
    try:
        proof, audit = build_portable_sound_audit_v1(
            source.model,
            source.query,
            selected_plan.proposal.policy,
            regret_tolerance=tolerance,
            operation_counter=operation_counter,
        )
        verify_portable_sound_audit_v1(
            source.model,
            source.query,
            selected_plan.proposal.policy,
            proof,
            audit,
            operation_counter=operation_counter,
        )
    except PortableSoundAuditV1Error as error:
        raise Phase3EModelOnlyV1Error(f"portable sound audit failed closed: {error}") from error
    identities = derive_model_only_phase3e_identities_v1(source)
    outcome = ModelOnlyOutcome(audit.outcome)
    rebuild_policy, occurrence, attempt, context = _campaign_bindings_v1(
        source=source,
        identities=identities,
        selected_plan=selected_plan,
        regret_tolerance=tolerance,
    )
    return Phase3EModelOnlyResultV1(
        source.lease,
        identities,
        selected_plan,
        proof,
        audit,
        outcome,
        outcome is ModelOnlyOutcome.FAIL,
        rebuild_policy,
        occurrence,
        attempt,
        context,
    )


def run_phase3e_model_only_v1(
    source_bundle: str | Path,
    *,
    query_key: str,
    regret_tolerance: Fraction | int = Fraction(1, 20),
) -> Phase3EModelOnlyResultV1:
    """Run the production model-only chain from a Phase-3C manifest bundle."""

    source = load_phase3c_model_source_v1(source_bundle, query_key=query_key)
    return run_phase3e_model_only_from_source_v1(
        source, regret_tolerance=regret_tolerance
    )


__all__ = [
    "MODEL_ONLY_IDENTITIES_SCHEMA",
    "MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN",
    "MODEL_ONLY_PROTOCOL_KEY",
    "MODEL_ONLY_RESULT_DOMAIN",
    "MODEL_ONLY_RESULT_SCHEMA",
    "ModelOnlyOutcome",
    "ModelOnlyPhase3EIdentitiesV1",
    "Phase3EModelOnlyResultV1",
    "Phase3EModelOnlyV1Error",
    "derive_model_only_phase3e_identities_v1",
    "run_phase3e_model_only_from_source_v1",
    "run_phase3e_model_only_v1",
    "verify_phase3e_model_only_result_without_replanning_v1",
]
