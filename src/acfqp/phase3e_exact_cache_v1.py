"""Strict Phase-3E replay and planner-free preflight for exact infeasibility.

This module implements the deliberately narrow V1 cache authority.  A cache
entry can only be established from a retained
``SemanticVerificationResultV1`` whose role is ``GROUND_FALLBACK`` and whose
recomputed outcome is ``INFEASIBLE_CERTIFIED``.  Raw result JSON, an
unverified ground result, a feasible result, and a cap-exhausted result are
not exact sources.

The retained-runtime lookup remains plan-frozen because the present 1.0.0
attestation schema requires a real ``selected_plan_id``.  The additive
preflight schema instead derives current coordinates from a live,
manifest-verified model/query source before plan selection and never invents
a dummy plan.

The serializable legacy source and proof objects are content-addressed, but
search completeness is covered only by an opaque in-memory handle.  The
planner-free preflight therefore implements the honest identity/index slice:
it never authorizes an infeasibility terminal and explicitly records the
missing independently replayable proof payload.  A future profile must add
and replay that durable payload before removing the blocker.

All three role domains are registered centrally in :mod:`acfqp.phase3e_ids`.
The scoped helper delegates to the normative
``SHA256(domain || 0x00 || canonical-json)`` implementation and additionally
rejects use of any registered domain belonging to another artifact role.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.phase3e_ids import (
    EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN,
    EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN,
    EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN,
    EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN,
    EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN,
    EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
    GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
    MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
    PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN,
    VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import RouteDecisionContextV1


SCHEMA_VERSION = "1.0.0"

_DOMAINS = frozenset(
    {
        PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN,
        VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN,
        EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN,
        EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
        EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN,
        EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN,
        EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN,
        EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN,
    }
)

SOURCE_KIND = "FULL_GROUND_EXACT_INFEASIBLE"
SOURCE_SCHEMA = "VerifiedExactInfeasibilitySourceV1"
PROOF_SCHEMA = "ExactCachedInfeasibilityProofV1"
CURRENT_BINDING_SCHEMA = "PlanFrozenExactCacheBindingV1"
PREFLIGHT_REQUEST_SCHEMA = "ExactCachePreflightRequestV1"
PREFLIGHT_ENTRY_SCHEMA = "ExactCachePreflightEntryV1"
PREFLIGHT_RESULT_SCHEMA = "ExactCachePreflightResultV1"

MISSING_DURABLE_PROOF_BLOCKER = "MISSING_INDEPENDENT_EXACT_PROOF_PAYLOAD"
NON_OFFICIAL_PREFLIGHT_BLOCKERS = (
    MISSING_DURABLE_PROOF_BLOCKER,
    "NO_REGISTERED_DURABLE_EXACT_PROOF_VERIFIER",
)


class Phase3EExactCacheV1Error(ValueError):
    """The exact source, cache proof, or replay binding is invalid."""


class ExactCacheOutcome(str, Enum):
    """The closed exact-cache/preflight semantic outcome vocabulary."""

    IDENTICAL_MATCH = "IDENTICAL_MATCH"
    NO_MATCH = "NO_MATCH"
    INVALID = "INVALID"


def derive_exact_kernel_identity_v1(
    context: RouteDecisionContextV1,
) -> str:
    """Derive the kernel coordinate from a retained frozen route context.

    V1 has no separately attested public kernel object.  The BuildEpoch and
    structural namespace are the registered authority for the kernel used by
    a route attempt, while preregistration/protocol prevent cross-profile
    reuse.  Consequently callers never supply a free ``kernel_id`` string.
    A future durable cache may replace this scoped coordinate only with an
    independently verified simulator/kernel artifact.
    """

    if type(context) is not RouteDecisionContextV1:
        raise Phase3EExactCacheV1Error(
            "kernel identity requires a retained RouteDecisionContextV1"
        )
    try:
        parsed = RouteDecisionContextV1.from_dict(context.to_dict())
    except ValueError as error:
        raise Phase3EExactCacheV1Error(
            f"kernel identity context does not replay: {error}"
        ) from error
    return _content_id(
        EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
        {
            "schema": "acfqp.exact_kernel_context_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": parsed.preregistration_id,
            "protocol_id": parsed.protocol_id,
            "structural_id": parsed.structural_id,
            "BuildEpoch_id": parsed.build_epoch_id,
        },
    )


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in _DOMAINS:
        raise Phase3EExactCacheV1Error(
            f"unregistered exact-cache domain tag: {domain!r}"
        )
    try:
        return content_id(domain, dict(payload))
    except ValueError as error:
        raise Phase3EExactCacheV1Error(str(error)) from error


EXACT_INFEASIBILITY_PROOF_PROFILE_ID = _content_id(
    EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN,
    {
        "schema": "acfqp.exact_infeasibility_proof_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proof_kind": "complete_finite_horizon_ground_infeasibility",
        "requires_kernel_bound_payload": True,
        "requires_independent_replay": True,
        "opaque_runtime_seal_is_sufficient": False,
    },
)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3EExactCacheV1Error(
            f"{field_name} must be a full Phase-3E content ID"
        ) from error


def _fields(
    document: Mapping[str, Any], expected: set[str], context: str
) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise Phase3EExactCacheV1Error(str(error)) from error


def _ground_parent_id(role: str, payload: Any) -> str:
    try:
        return content_id(
            GROUND_FALLBACK_PARENT_BINDING_DOMAIN,
            {
                "schema": "acfqp.safe_chain_fallback_parent_binding.v1",
                "role": role,
                "payload": payload,
            },
        )
    except ValueError as error:
        raise Phase3EExactCacheV1Error(str(error)) from error


def _model_only_binding_id(role: str, payload: Any) -> str:
    try:
        return content_id(
            MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
            {
                "schema": "acfqp.phase3e_model_only_orchestration_binding.v1",
                "schema_version": SCHEMA_VERSION,
                "role": role,
                "payload": payload,
            },
        )
    except ValueError as error:
        raise Phase3EExactCacheV1Error(str(error)) from error


def _model_source_coordinates_v1(source: object) -> tuple[object, dict[str, str]]:
    """Replay a live model source and derive cache coordinates without planning."""

    from acfqp.phase3e_rapm_consumer_v1 import (
        RAPMSourceLeaseV1,
        require_model_only_source_authority_v1,
    )

    try:
        retained = require_model_only_source_authority_v1(source)
        lease = RAPMSourceLeaseV1.from_dict(retained.lease.to_dict())
    except ValueError as error:
        raise Phase3EExactCacheV1Error(
            f"exact cache requires a live manifest-verified model source: {error}"
        ) from error
    structural_id = _ground_parent_id(
        "structural", {"legacy_structural_id": lease.legacy_structural_id}
    )
    query_id = _ground_parent_id(
        "query",
        {
            "legacy_query_id": lease.legacy_ground_query_id,
            "query_key": lease.query_key,
        },
    )
    build_epoch_id = _ground_parent_id(
        "build_epoch",
        {
            "legacy_build_epoch_id": lease.legacy_build_epoch_id,
            "serialized_sha256": lease.build_epoch_sha256,
        },
    )
    manifest_id = _ground_parent_id(
        "manifest",
        {
            "manifest_sha256": lease.source_manifest_sha256,
            "run_id": lease.source_run_id,
        },
    )
    kernel_id = _content_id(
        EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
        {
            "schema": "acfqp.exact_kernel_source_identity.v1",
            "schema_version": SCHEMA_VERSION,
            "source_lease_id": lease.source_lease_id,
            "structural_id": structural_id,
            "BuildEpoch_id": build_epoch_id,
            "manifest_id": manifest_id,
            "kernel_sha256": lease.kernel_sha256,
        },
    )
    return retained, {
        "source_lease_id": lease.source_lease_id,
        "structural_id": structural_id,
        "query_id": query_id,
        "build_epoch_id": build_epoch_id,
        "manifest_id": manifest_id,
        "kernel_id": kernel_id,
    }


def derive_exact_kernel_identity_from_model_source_v1(source: object) -> str:
    """Derive the real source-bound kernel coordinate; no label is accepted."""

    return _model_source_coordinates_v1(source)[1]["kernel_id"]


def derive_exact_threshold_profile_from_model_source_v1(
    source: object,
    *,
    regret_tolerance: Fraction | int = Fraction(1, 20),
) -> str:
    """Reproduce the model-only threshold ID before selecting a plan."""

    from acfqp.portable import fraction_from_json

    retained, _ = _model_source_coordinates_v1(source)
    if isinstance(regret_tolerance, bool) or not isinstance(
        regret_tolerance, (int, Fraction)
    ):
        raise Phase3EExactCacheV1Error("regret_tolerance must be exact")
    tolerance = Fraction(regret_tolerance)
    if tolerance < 0:
        raise Phase3EExactCacheV1Error("regret_tolerance must be nonnegative")
    query_document = retained.query.to_dict()
    return _model_only_binding_id(
        "threshold_profile",
        {
            "profile_key": "canonical_regret_005_and_query_risk_v1",
            "regret_tolerance": tolerance,
            "risk_tolerance": fraction_from_json(
                query_document["delta"], field="portable query delta"
            ),
        },
    )


def _complete_search_profile_id_v1(profile: object) -> str:
    from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1

    if type(profile) is not GroundFallbackCapProfileV1:
        raise Phase3EExactCacheV1Error(
            "complete search profile must be GroundFallbackCapProfileV1"
        )
    try:
        replayed = GroundFallbackCapProfileV1.from_dict(profile.to_dict())
    except ValueError as error:
        raise Phase3EExactCacheV1Error(
            f"complete search profile does not replay: {error}"
        ) from error
    return replayed.ground_fallback_cap_profile_id


@dataclass(frozen=True, slots=True)
class ExactInfeasibilityIdentityV1:
    """All reusable identity coordinates of one exact infeasibility claim."""

    structural_id: str
    query_id: str
    build_epoch_id: str
    kernel_id: str
    manifest_id: str
    threshold_profile_id: str
    proof_profile_id: str
    complete_search_profile_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "structural_id",
            "query_id",
            "build_epoch_id",
            "kernel_id",
            "manifest_id",
            "threshold_profile_id",
            "proof_profile_id",
            "complete_search_profile_id",
        ):
            _cid(getattr(self, field_name), field_name)
        if self.proof_profile_id != EXACT_INFEASIBILITY_PROOF_PROFILE_ID:
            raise Phase3EExactCacheV1Error(
                "exact identity uses an unregistered proof profile"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "manifest_id": self.manifest_id,
            "threshold_profile_id": self.threshold_profile_id,
            "proof_profile_id": self.proof_profile_id,
            "complete_search_profile_id": self.complete_search_profile_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactInfeasibilityIdentityV1":
        _fields(
            document,
            {
                "structural_id",
                "query_id",
                "BuildEpoch_id",
                "kernel_id",
                "manifest_id",
                "threshold_profile_id",
                "proof_profile_id",
                "complete_search_profile_id",
            },
            "exact infeasibility identity",
        )
        return cls(
            document["structural_id"],
            document["query_id"],
            document["BuildEpoch_id"],
            document["kernel_id"],
            document["manifest_id"],
            document["threshold_profile_id"],
            document["proof_profile_id"],
            document["complete_search_profile_id"],
        )


@dataclass(frozen=True, slots=True)
class PlanFrozenExactCacheBindingV1:
    """Current identity after a real selected plan and route context exist."""

    route_decision_context_id: str
    source_model_lease_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    kernel_id: str
    manifest_id: str
    proof_profile_id: str
    complete_search_profile_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "route_decision_context_id",
            "source_model_lease_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "kernel_id",
            "manifest_id",
            "proof_profile_id",
            "complete_search_profile_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            _cid(getattr(self, field_name), field_name)
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3EExactCacheV1Error(
                "plan-frozen exact-cache binding version mismatch"
            )
        if self.proof_profile_id != EXACT_INFEASIBILITY_PROOF_PROFILE_ID:
            raise Phase3EExactCacheV1Error(
                "plan-frozen binding uses an unregistered proof profile"
            )

    @classmethod
    def from_route_context(
        cls,
        context: RouteDecisionContextV1,
        *,
        model_source: object,
        complete_search_profile: object,
    ) -> "PlanFrozenExactCacheBindingV1":
        if not isinstance(context, RouteDecisionContextV1):
            raise Phase3EExactCacheV1Error(
                "current cache binding requires RouteDecisionContextV1"
            )
        # Strictly replay the context ID and all of its fields.  A caller
        # cannot pass an object whose cached property was detached from bytes.
        try:
            parsed = RouteDecisionContextV1.from_dict(context.to_dict())
        except ValueError as error:
            raise Phase3EExactCacheV1Error(
                f"invalid plan-frozen route context: {error}"
            ) from error
        _, coordinates = _model_source_coordinates_v1(model_source)
        for field_name in ("structural_id", "query_id", "build_epoch_id"):
            if getattr(parsed, field_name) != coordinates[field_name]:
                raise Phase3EExactCacheV1Error(
                    f"plan-frozen context/model-source mismatch for {field_name}"
                )
        return cls(
            parsed.route_decision_context_id,
            coordinates["source_lease_id"],
            parsed.structural_id,
            parsed.query_id,
            parsed.selected_plan_id,
            parsed.threshold_profile_id,
            parsed.build_epoch_id,
            coordinates["kernel_id"],
            coordinates["manifest_id"],
            EXACT_INFEASIBILITY_PROOF_PROFILE_ID,
            _complete_search_profile_id_v1(complete_search_profile),
            parsed.logical_occurrence_id,
            parsed.route_attempt_id,
        )

    @property
    def exact_identity(self) -> ExactInfeasibilityIdentityV1:
        return ExactInfeasibilityIdentityV1(
            self.structural_id,
            self.query_id,
            self.build_epoch_id,
            self.kernel_id,
            self.manifest_id,
            self.threshold_profile_id,
            self.proof_profile_id,
            self.complete_search_profile_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.plan_frozen_exact_cache_binding.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "source_model_lease_id": self.source_model_lease_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "manifest_id": self.manifest_id,
            "proof_profile_id": self.proof_profile_id,
            "complete_search_profile_id": self.complete_search_profile_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
        }

    @property
    def plan_frozen_exact_cache_binding_id(self) -> str:
        return _content_id(
            PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "plan_frozen_exact_cache_binding_id": (
                self.plan_frozen_exact_cache_binding_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "PlanFrozenExactCacheBindingV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "RouteDecisionContext_id",
                "source_model_lease_id",
                "structural_id",
                "query_id",
                "selected_plan_id",
                "threshold_profile_id",
                "BuildEpoch_id",
                "kernel_id",
                "manifest_id",
                "proof_profile_id",
                "complete_search_profile_id",
                "logical_occurrence_id",
                "route_attempt_id",
                "plan_frozen_exact_cache_binding_id",
            },
            "plan-frozen exact-cache binding",
        )
        if document["schema"] != "acfqp.plan_frozen_exact_cache_binding.v1":
            raise Phase3EExactCacheV1Error(
                "plan-frozen exact-cache binding schema mismatch"
            )
        result = cls(
            document["RouteDecisionContext_id"],
            document["source_model_lease_id"],
            document["structural_id"],
            document["query_id"],
            document["selected_plan_id"],
            document["threshold_profile_id"],
            document["BuildEpoch_id"],
            document["kernel_id"],
            document["manifest_id"],
            document["proof_profile_id"],
            document["complete_search_profile_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["schema_version"],
        )
        if (
            document["plan_frozen_exact_cache_binding_id"]
            != result.plan_frozen_exact_cache_binding_id
        ):
            raise Phase3EExactCacheV1Error(
                "plan-frozen exact-cache binding content ID mismatch"
            )
        return result


@dataclass(frozen=True, slots=True)
class ExactInfeasibilitySourceArtifactV1:
    """Serializable projection of a retained exact ground authority."""

    exact_identity: ExactInfeasibilityIdentityV1
    source_model_lease_id: str
    source_ground_fallback_result_id: str
    source_ground_fallback_attestation_id: str
    source_ground_fallback_work_vector_id: str
    source_verification_work_counter_record_id: str
    complete_search_profile_id: str
    source_route_decision_context_id: str
    source_recomputed_evidence_ids: tuple[str, ...]
    source_kind: str = SOURCE_KIND
    source_artifact_schema_id: str = "GroundFallbackResultV1"
    source_artifact_role: str = "GROUND_FALLBACK"
    source_verification_result: str = "INFEASIBLE_CERTIFIED"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.exact_identity, ExactInfeasibilityIdentityV1):
            raise Phase3EExactCacheV1Error(
                "exact source requires ExactInfeasibilityIdentityV1"
            )
        for field_name in (
            "source_model_lease_id",
            "source_ground_fallback_result_id",
            "source_ground_fallback_attestation_id",
            "source_ground_fallback_work_vector_id",
            "source_verification_work_counter_record_id",
            "complete_search_profile_id",
            "source_route_decision_context_id",
        ):
            _cid(getattr(self, field_name), field_name)
        if (
            self.exact_identity.complete_search_profile_id
            != self.complete_search_profile_id
            or self.exact_identity.proof_profile_id
            != EXACT_INFEASIBILITY_PROOF_PROFILE_ID
        ):
            raise Phase3EExactCacheV1Error(
                "exact source identity/profile binding mismatch"
            )
        if (
            not self.source_recomputed_evidence_ids
            or tuple(sorted(self.source_recomputed_evidence_ids))
            != self.source_recomputed_evidence_ids
            or len(set(self.source_recomputed_evidence_ids))
            != len(self.source_recomputed_evidence_ids)
        ):
            raise Phase3EExactCacheV1Error(
                "exact source evidence IDs must be nonempty, unique, and sorted"
            )
        for evidence_id in self.source_recomputed_evidence_ids:
            _cid(evidence_id, "source_recomputed_evidence_id")
        if (
            self.source_kind != SOURCE_KIND
            or self.source_artifact_schema_id != "GroundFallbackResultV1"
            or self.source_artifact_role != "GROUND_FALLBACK"
            or self.source_verification_result != "INFEASIBLE_CERTIFIED"
        ):
            raise Phase3EExactCacheV1Error(
                "exact cache source must be a complete verified ground infeasibility"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3EExactCacheV1Error("exact source version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_exact_infeasibility_source.v1",
            "schema_version": self.schema_version,
            "source_kind": self.source_kind,
            "source_artifact_schema_id": self.source_artifact_schema_id,
            "source_artifact_role": self.source_artifact_role,
            "source_verification_result": self.source_verification_result,
            "exact_identity": self.exact_identity.to_dict(),
            "source_model_lease_id": self.source_model_lease_id,
            "source_ground_fallback_result_id": (
                self.source_ground_fallback_result_id
            ),
            "source_ground_fallback_attestation_id": (
                self.source_ground_fallback_attestation_id
            ),
            "source_ground_fallback_work_vector_id": (
                self.source_ground_fallback_work_vector_id
            ),
            "source_verification_work_counter_record_id": (
                self.source_verification_work_counter_record_id
            ),
            "complete_search_profile_id": self.complete_search_profile_id,
            "source_route_decision_context_id": (
                self.source_route_decision_context_id
            ),
            "source_recomputed_evidence_ids": list(
                self.source_recomputed_evidence_ids
            ),
        }

    @property
    def verified_exact_infeasibility_source_id(self) -> str:
        return _content_id(
            VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verified_exact_infeasibility_source_id": (
                self.verified_exact_infeasibility_source_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactInfeasibilitySourceArtifactV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "source_kind",
                "source_artifact_schema_id",
                "source_artifact_role",
                "source_verification_result",
                "exact_identity",
                "source_model_lease_id",
                "source_ground_fallback_result_id",
                "source_ground_fallback_attestation_id",
                "source_ground_fallback_work_vector_id",
                "source_verification_work_counter_record_id",
                "complete_search_profile_id",
                "source_route_decision_context_id",
                "source_recomputed_evidence_ids",
                "verified_exact_infeasibility_source_id",
            },
            "verified exact infeasibility source",
        )
        if (
            document["schema"]
            != "acfqp.verified_exact_infeasibility_source.v1"
            or type(document["exact_identity"]) is not dict
            or type(document["source_recomputed_evidence_ids"]) is not list
        ):
            raise Phase3EExactCacheV1Error(
                "verified exact infeasibility source schema mismatch"
            )
        result = cls(
            ExactInfeasibilityIdentityV1.from_dict(document["exact_identity"]),
            document["source_model_lease_id"],
            document["source_ground_fallback_result_id"],
            document["source_ground_fallback_attestation_id"],
            document["source_ground_fallback_work_vector_id"],
            document["source_verification_work_counter_record_id"],
            document["complete_search_profile_id"],
            document["source_route_decision_context_id"],
            tuple(document["source_recomputed_evidence_ids"]),
            document["source_kind"],
            document["source_artifact_schema_id"],
            document["source_artifact_role"],
            document["source_verification_result"],
            document["schema_version"],
        )
        if (
            document["verified_exact_infeasibility_source_id"]
            != result.verified_exact_infeasibility_source_id
        ):
            raise Phase3EExactCacheV1Error(
                "verified exact infeasibility source content ID mismatch"
            )
        return result


_VERIFIED_EXACT_SOURCE_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class VerifiedExactInfeasibilitySourceV1:
    """Opaque handle proving that ``artifact`` came from semantic replay."""

    artifact: ExactInfeasibilitySourceArtifactV1
    semantic_result: object = field(repr=False, compare=False)
    model_source: object = field(repr=False, compare=False)
    complete_search_profile: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._authority is not _VERIFIED_EXACT_SOURCE_AUTHORITY:
            raise Phase3EExactCacheV1Error(
                "exact source was not minted from retained semantic authority"
            )
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_VERIFIED_EXACT_SOURCE_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EExactCacheV1Error(
                    "exact source is a copied or modified runtime authority"
                ) from error


def verify_exact_infeasibility_source_v1(
    semantic_result: object,
    *,
    model_source: object,
    complete_search_profile: object,
) -> VerifiedExactInfeasibilitySourceV1:
    """Project one verified complete ground-infeasibility result into cache.

    Structural/query/build/manifest/kernel coordinates are derived from a
    retained manifest-verified model source; callers cannot provide a kernel
    label.  The retained ground semantic result remains the V1 trust root for
    search completeness, so this handle is not yet a durable proof.
    """

    from acfqp.phase3e_fallback_v1 import (
        GroundFallbackOutcome,
        GroundFallbackResultV1,
    )
    from acfqp.semantic_verification_v1 import (
        SemanticRole,
        SemanticVerificationResultV1,
    )

    if type(semantic_result) is not SemanticVerificationResultV1:
        raise Phase3EExactCacheV1Error(
            "exact cache source requires a retained typed semantic result"
        )
    if (
        semantic_result.role is not SemanticRole.GROUND_FALLBACK
        or semantic_result.outcome != GroundFallbackOutcome.INFEASIBLE_CERTIFIED.value
        or type(semantic_result.artifact) is not GroundFallbackResultV1
    ):
        raise Phase3EExactCacheV1Error(
            "exact cache source must be GROUND_FALLBACK/INFEASIBLE_CERTIFIED"
        )
    result = semantic_result.artifact
    attestation = semantic_result.attestation
    context = semantic_result.binding.route_context
    retained_model_source, coordinates = _model_source_coordinates_v1(model_source)
    search_profile_id = _complete_search_profile_id_v1(complete_search_profile)
    if (
        result.outcome is not GroundFallbackOutcome.INFEASIBLE_CERTIFIED
        or not result.search_complete
        or result.cap_exhausted_name is not None
        or not result.frontier
        or result.selected_policy_signature
        or result.selected_expected_reward is not None
        or result.selected_failure_probability is not None
    ):
        raise Phase3EExactCacheV1Error(
            "ground source is feasible, incomplete, cap-exhausted, or malformed"
        )
    if (
        attestation.artifact_id != result.ground_fallback_result_id
        or attestation.artifact_schema_id != "GroundFallbackResultV1"
        or attestation.artifact_role != "GROUND_FALLBACK"
        or attestation.verification_result != "INFEASIBLE_CERTIFIED"
        or attestation.route_decision_context_id
        != context.route_decision_context_id
        or result.route_decision_context_id
        != context.route_decision_context_id
        or result.query_id != context.query_id
        or result.route_attempt_id != context.route_attempt_id
        or result.ground_fallback_cap_profile_id != search_profile_id
    ):
        raise Phase3EExactCacheV1Error(
            "ground exact source result/attestation/context binding mismatch"
        )
    for field_name in ("structural_id", "query_id", "build_epoch_id"):
        if getattr(context, field_name) != coordinates[field_name]:
            raise Phase3EExactCacheV1Error(
                f"ground exact source/model identity mismatch for {field_name}"
            )
    if result.work_vector_id not in semantic_result.recomputed_evidence_ids:
        raise Phase3EExactCacheV1Error(
            "ground exact source does not retain its authoritative WorkVector evidence"
        )
    if (
        result.ground_fallback_cap_profile_id
        not in semantic_result.recomputed_evidence_ids
    ):
        raise Phase3EExactCacheV1Error(
            "ground exact source does not retain its complete-search profile evidence"
        )

    artifact = ExactInfeasibilitySourceArtifactV1(
        ExactInfeasibilityIdentityV1(
            context.structural_id,
            context.query_id,
            context.build_epoch_id,
            coordinates["kernel_id"],
            coordinates["manifest_id"],
            context.threshold_profile_id,
            EXACT_INFEASIBILITY_PROOF_PROFILE_ID,
            search_profile_id,
        ),
        coordinates["source_lease_id"],
        result.ground_fallback_result_id,
        attestation.verification_attestation_id,
        result.work_vector_id,
        semantic_result.verification_work_record.record_id,
        search_profile_id,
        context.route_decision_context_id,
        semantic_result.recomputed_evidence_ids,
    )
    source = VerifiedExactInfeasibilitySourceV1(
        artifact,
        semantic_result,
        retained_model_source,
        complete_search_profile,
        _VERIFIED_EXACT_SOURCE_AUTHORITY,
    )
    return bind_runtime_authority_v1(
        source,
        issuer=_VERIFIED_EXACT_SOURCE_AUTHORITY,
    )


@dataclass(frozen=True, slots=True)
class ExactCachedInfeasibilityProofV1:
    """One plan-frozen lookup against one retained exact source."""

    current_binding: PlanFrozenExactCacheBindingV1
    cached_identity: ExactInfeasibilityIdentityV1
    verified_exact_infeasibility_source_id: str
    source_ground_fallback_result_id: str
    source_ground_fallback_attestation_id: str
    source_ground_fallback_work_vector_id: str
    source_verification_work_counter_record_id: str
    complete_search_profile_id: str
    claimed_outcome: ExactCacheOutcome
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.current_binding, PlanFrozenExactCacheBindingV1):
            raise Phase3EExactCacheV1Error(
                "cached proof requires PlanFrozenExactCacheBindingV1"
            )
        if not isinstance(self.cached_identity, ExactInfeasibilityIdentityV1):
            raise Phase3EExactCacheV1Error(
                "cached proof requires ExactInfeasibilityIdentityV1"
            )
        for field_name in (
            "verified_exact_infeasibility_source_id",
            "source_ground_fallback_result_id",
            "source_ground_fallback_attestation_id",
            "source_ground_fallback_work_vector_id",
            "source_verification_work_counter_record_id",
            "complete_search_profile_id",
        ):
            _cid(getattr(self, field_name), field_name)
        try:
            parsed_outcome = ExactCacheOutcome(self.claimed_outcome)
        except (TypeError, ValueError) as error:
            raise Phase3EExactCacheV1Error(
                "cached proof outcome must be IDENTICAL_MATCH or NO_MATCH"
            ) from error
        if parsed_outcome is ExactCacheOutcome.INVALID:
            raise Phase3EExactCacheV1Error(
                "cached proof cannot self-claim INVALID"
            )
        object.__setattr__(self, "claimed_outcome", parsed_outcome)
        if self.schema_version != SCHEMA_VERSION:
            raise Phase3EExactCacheV1Error("cached proof version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_cached_infeasibility_proof.v1",
            "schema_version": self.schema_version,
            "current_binding": self.current_binding.to_dict(),
            "cached_identity": self.cached_identity.to_dict(),
            "verified_exact_infeasibility_source_id": (
                self.verified_exact_infeasibility_source_id
            ),
            "source_ground_fallback_result_id": (
                self.source_ground_fallback_result_id
            ),
            "source_ground_fallback_attestation_id": (
                self.source_ground_fallback_attestation_id
            ),
            "source_ground_fallback_work_vector_id": (
                self.source_ground_fallback_work_vector_id
            ),
            "source_verification_work_counter_record_id": (
                self.source_verification_work_counter_record_id
            ),
            "complete_search_profile_id": self.complete_search_profile_id,
            "claimed_outcome": self.claimed_outcome.value,
        }

    @property
    def exact_cached_infeasibility_proof_id(self) -> str:
        return _content_id(
            EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN, self._payload()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "exact_cached_infeasibility_proof_id": (
                self.exact_cached_infeasibility_proof_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactCachedInfeasibilityProofV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "current_binding",
                "cached_identity",
                "verified_exact_infeasibility_source_id",
                "source_ground_fallback_result_id",
                "source_ground_fallback_attestation_id",
                "source_ground_fallback_work_vector_id",
                "source_verification_work_counter_record_id",
                "complete_search_profile_id",
                "claimed_outcome",
                "exact_cached_infeasibility_proof_id",
            },
            "exact cached infeasibility proof",
        )
        if (
            document["schema"]
            != "acfqp.exact_cached_infeasibility_proof.v1"
            or type(document["current_binding"]) is not dict
            or type(document["cached_identity"]) is not dict
        ):
            raise Phase3EExactCacheV1Error(
                "exact cached infeasibility proof schema mismatch"
            )
        result = cls(
            PlanFrozenExactCacheBindingV1.from_dict(
                document["current_binding"]
            ),
            ExactInfeasibilityIdentityV1.from_dict(
                document["cached_identity"]
            ),
            document["verified_exact_infeasibility_source_id"],
            document["source_ground_fallback_result_id"],
            document["source_ground_fallback_attestation_id"],
            document["source_ground_fallback_work_vector_id"],
            document["source_verification_work_counter_record_id"],
            document["complete_search_profile_id"],
            document["claimed_outcome"],
            document["schema_version"],
        )
        if (
            document["exact_cached_infeasibility_proof_id"]
            != result.exact_cached_infeasibility_proof_id
        ):
            raise Phase3EExactCacheV1Error(
                "exact cached infeasibility proof content ID mismatch"
            )
        return result


def _recomputed_outcome(
    cached: ExactInfeasibilityIdentityV1,
    current: ExactInfeasibilityIdentityV1,
) -> ExactCacheOutcome:
    return (
        ExactCacheOutcome.IDENTICAL_MATCH
        if cached == current
        else ExactCacheOutcome.NO_MATCH
    )


def build_exact_cached_infeasibility_proof_v1(
    source: VerifiedExactInfeasibilitySourceV1,
    *,
    current_context: RouteDecisionContextV1,
    current_model_source: object | None = None,
    complete_search_profile: object | None = None,
) -> ExactCachedInfeasibilityProofV1:
    """Build the serializable lookup artifact for one current context."""

    _verify_retained_source_handle(source)
    selected_model_source = (
        source.model_source
        if current_model_source is None
        else current_model_source
    )
    selected_search_profile = (
        source.complete_search_profile
        if complete_search_profile is None
        else complete_search_profile
    )
    current = PlanFrozenExactCacheBindingV1.from_route_context(
        current_context,
        model_source=selected_model_source,
        complete_search_profile=selected_search_profile,
    )
    artifact = source.artifact
    return ExactCachedInfeasibilityProofV1(
        current,
        artifact.exact_identity,
        artifact.verified_exact_infeasibility_source_id,
        artifact.source_ground_fallback_result_id,
        artifact.source_ground_fallback_attestation_id,
        artifact.source_ground_fallback_work_vector_id,
        artifact.source_verification_work_counter_record_id,
        artifact.complete_search_profile_id,
        _recomputed_outcome(artifact.exact_identity, current.exact_identity),
    )


def _verify_retained_source_handle(
    source: VerifiedExactInfeasibilitySourceV1,
) -> None:
    if (
        not isinstance(source, VerifiedExactInfeasibilitySourceV1)
        or source._authority is not _VERIFIED_EXACT_SOURCE_AUTHORITY
    ):
        raise Phase3EExactCacheV1Error(
            "cache replay requires retained exact-source runtime authority"
        )
    try:
        require_runtime_authority_v1(
            source,
            issuer=_VERIFIED_EXACT_SOURCE_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EExactCacheV1Error(
            "cache replay requires the exact retained source instance"
        ) from error
    # Re-run the source projection against the retained semantic result.  This
    # catches a dataclass-replacement splice even inside the same process.
    recomputed = verify_exact_infeasibility_source_v1(
        source.semantic_result,
        model_source=source.model_source,
        complete_search_profile=source.complete_search_profile,
    )
    if recomputed.artifact != source.artifact:
        raise Phase3EExactCacheV1Error(
            "retained exact-source artifact does not replay from its authority"
        )
    parsed = ExactInfeasibilitySourceArtifactV1.from_dict(
        source.artifact.to_dict()
    )
    if parsed != source.artifact:
        raise Phase3EExactCacheV1Error(
            "retained exact-source artifact differs from strict schema replay"
        )


def verify_exact_cached_infeasibility_v1(
    proof: ExactCachedInfeasibilityProofV1 | Mapping[str, Any],
    *,
    source: VerifiedExactInfeasibilitySourceV1,
    current_context: RouteDecisionContextV1,
    current_model_source: object | None = None,
    complete_search_profile: object | None = None,
) -> ExactCacheOutcome:
    """Replay a cache lookup and return ``IDENTICAL_MATCH`` or ``NO_MATCH``.

    Identity differences are ordinary cache misses.  Malformed artifacts,
    stale current bindings, untrusted sources, and source/reference splices are
    errors and must become semantic ``INVALID`` at the caller boundary.
    """

    _verify_retained_source_handle(source)
    selected_model_source = (
        source.model_source
        if current_model_source is None
        else current_model_source
    )
    selected_search_profile = (
        source.complete_search_profile
        if complete_search_profile is None
        else complete_search_profile
    )
    try:
        parsed = ExactCachedInfeasibilityProofV1.from_dict(
            proof.to_dict()
            if isinstance(proof, ExactCachedInfeasibilityProofV1)
            else proof
        )
    except (TypeError, ValueError) as error:
        raise Phase3EExactCacheV1Error(
            f"exact cached infeasibility proof is malformed: {error}"
        ) from error
    current = PlanFrozenExactCacheBindingV1.from_route_context(
        current_context,
        model_source=selected_model_source,
        complete_search_profile=selected_search_profile,
    )
    if parsed.current_binding != current:
        raise Phase3EExactCacheV1Error(
            "cached proof is stale or bound to another plan-frozen context"
        )
    artifact = source.artifact
    source_refs = (
        parsed.cached_identity,
        parsed.verified_exact_infeasibility_source_id,
        parsed.source_ground_fallback_result_id,
        parsed.source_ground_fallback_attestation_id,
        parsed.source_ground_fallback_work_vector_id,
        parsed.source_verification_work_counter_record_id,
        parsed.complete_search_profile_id,
    )
    authoritative_refs = (
        artifact.exact_identity,
        artifact.verified_exact_infeasibility_source_id,
        artifact.source_ground_fallback_result_id,
        artifact.source_ground_fallback_attestation_id,
        artifact.source_ground_fallback_work_vector_id,
        artifact.source_verification_work_counter_record_id,
        artifact.complete_search_profile_id,
    )
    if source_refs != authoritative_refs:
        raise Phase3EExactCacheV1Error(
            "cached proof splices or misbinds its verified exact source"
        )
    outcome = _recomputed_outcome(
        artifact.exact_identity, current.exact_identity
    )
    if parsed.claimed_outcome is not outcome:
        raise Phase3EExactCacheV1Error(
            "cached proof claimed outcome disagrees with exact identity replay"
        )
    return outcome


_PREFLIGHT_COORDINATES = (
    "structural_id",
    "query_id",
    "build_epoch_id",
    "kernel_id",
    "manifest_id",
    "threshold_profile_id",
    "proof_profile_id",
    "complete_search_profile_id",
)


@dataclass(frozen=True, slots=True)
class ExactCachePreflightRequestV1:
    """Plan-free current-query identity derived from a verified model source."""

    source_model_lease_id: str
    query_key: str
    exact_identity: ExactInfeasibilityIdentityV1
    complete_search_profile: dict[str, Any]
    regret_tolerance: Fraction = Fraction(1, 20)
    schema_version: str = SCHEMA_VERSION
    planner_free: bool = True

    def __post_init__(self) -> None:
        _cid(self.source_model_lease_id, "source_model_lease_id")
        if type(self.query_key) is not str or not self.query_key:
            raise Phase3EExactCacheV1Error("preflight query_key must be nonempty")
        if not isinstance(self.exact_identity, ExactInfeasibilityIdentityV1):
            raise Phase3EExactCacheV1Error(
                "preflight request requires ExactInfeasibilityIdentityV1"
            )
        if type(self.complete_search_profile) is not dict:
            raise Phase3EExactCacheV1Error(
                "preflight complete search profile must be an object"
            )
        from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1

        try:
            profile = GroundFallbackCapProfileV1.from_dict(
                self.complete_search_profile
            )
        except ValueError as error:
            raise Phase3EExactCacheV1Error(
                f"preflight complete search profile is invalid: {error}"
            ) from error
        if (
            profile.ground_fallback_cap_profile_id
            != self.exact_identity.complete_search_profile_id
        ):
            raise Phase3EExactCacheV1Error(
                "preflight identity/search-profile mismatch"
            )
        if isinstance(self.regret_tolerance, bool) or not isinstance(
            self.regret_tolerance, (int, Fraction)
        ):
            raise Phase3EExactCacheV1Error(
                "preflight regret_tolerance must be exact"
            )
        object.__setattr__(self, "regret_tolerance", Fraction(self.regret_tolerance))
        if self.regret_tolerance < 0:
            raise Phase3EExactCacheV1Error(
                "preflight regret_tolerance must be nonnegative"
            )
        if self.schema_version != SCHEMA_VERSION or self.planner_free is not True:
            raise Phase3EExactCacheV1Error(
                "preflight request schema/profile mismatch"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_cache_preflight_request.v1",
            "schema_version": self.schema_version,
            "source_model_lease_id": self.source_model_lease_id,
            "query_key": self.query_key,
            "exact_identity": self.exact_identity.to_dict(),
            "complete_search_profile": dict(self.complete_search_profile),
            "regret_tolerance": self.regret_tolerance,
            "planner_free": True,
            "selected_plan_id": None,
        }

    @property
    def exact_cache_preflight_request_id(self) -> str:
        return _content_id(EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "exact_cache_preflight_request_id": (
                self.exact_cache_preflight_request_id
            ),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactCachePreflightRequestV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "source_model_lease_id",
                "query_key",
                "exact_identity",
                "complete_search_profile",
                "regret_tolerance",
                "planner_free",
                "selected_plan_id",
                "exact_cache_preflight_request_id",
            },
            "exact-cache preflight request",
        )
        if (
            document["schema"] != "acfqp.exact_cache_preflight_request.v1"
            or document["selected_plan_id"] is not None
            or type(document["exact_identity"]) is not dict
            or type(document["complete_search_profile"]) is not dict
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight request schema mismatch"
            )
        result = cls(
            document["source_model_lease_id"],
            document["query_key"],
            ExactInfeasibilityIdentityV1.from_dict(document["exact_identity"]),
            dict(document["complete_search_profile"]),
            document["regret_tolerance"],
            document["schema_version"],
            document["planner_free"],
        )
        if (
            document["exact_cache_preflight_request_id"]
            != result.exact_cache_preflight_request_id
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight request content ID mismatch"
            )
        return result


def build_exact_cache_preflight_request_v1(
    model_source: object,
    *,
    complete_search_profile: object,
    regret_tolerance: Fraction | int = Fraction(1, 20),
) -> ExactCachePreflightRequestV1:
    """Build the current identity without a plan, audit, J0, or ground call."""

    retained, coordinates = _model_source_coordinates_v1(model_source)
    search_profile_id = _complete_search_profile_id_v1(complete_search_profile)
    threshold_profile_id = derive_exact_threshold_profile_from_model_source_v1(
        retained, regret_tolerance=regret_tolerance
    )
    identity = ExactInfeasibilityIdentityV1(
        coordinates["structural_id"],
        coordinates["query_id"],
        coordinates["build_epoch_id"],
        coordinates["kernel_id"],
        coordinates["manifest_id"],
        threshold_profile_id,
        EXACT_INFEASIBILITY_PROOF_PROFILE_ID,
        search_profile_id,
    )
    return ExactCachePreflightRequestV1(
        coordinates["source_lease_id"],
        retained.lease.query_key,
        identity,
        dict(complete_search_profile.to_dict()),
        Fraction(regret_tolerance),
    )


@dataclass(frozen=True, slots=True)
class ExactCachePreflightEntryV1:
    """Serializable cache index row; V1 deliberately lacks durable proof bytes."""

    source_artifact: ExactInfeasibilitySourceArtifactV1
    durable_proof_payload: None = None
    durable_proof_payload_id: None = None
    durable_proof_replay_status: str = MISSING_DURABLE_PROOF_BLOCKER
    authorizes_infeasibility: bool = False
    official: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_artifact, ExactInfeasibilitySourceArtifactV1
        ):
            raise Phase3EExactCacheV1Error(
                "preflight entry requires an exact source artifact"
            )
        if (
            self.durable_proof_payload is not None
            or self.durable_proof_payload_id is not None
            or self.durable_proof_replay_status != MISSING_DURABLE_PROOF_BLOCKER
            or self.authorizes_infeasibility is not False
            or self.official is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3EExactCacheV1Error(
                "V1 preflight entry cannot claim a missing durable proof or official authority"
            )

    @property
    def exact_identity(self) -> ExactInfeasibilityIdentityV1:
        return self.source_artifact.exact_identity

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_cache_preflight_entry.v1",
            "schema_version": self.schema_version,
            "source_artifact": self.source_artifact.to_dict(),
            "durable_proof_payload": None,
            "durable_proof_payload_id": None,
            "durable_proof_replay_status": self.durable_proof_replay_status,
            "authorizes_infeasibility": False,
            "official": False,
        }

    @property
    def exact_cache_preflight_entry_id(self) -> str:
        return _content_id(EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "exact_cache_preflight_entry_id": self.exact_cache_preflight_entry_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactCachePreflightEntryV1":
        _fields(
            document,
            {
                "schema",
                "schema_version",
                "source_artifact",
                "durable_proof_payload",
                "durable_proof_payload_id",
                "durable_proof_replay_status",
                "authorizes_infeasibility",
                "official",
                "exact_cache_preflight_entry_id",
            },
            "exact-cache preflight entry",
        )
        if (
            document["schema"] != "acfqp.exact_cache_preflight_entry.v1"
            or type(document["source_artifact"]) is not dict
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight entry schema mismatch"
            )
        result = cls(
            ExactInfeasibilitySourceArtifactV1.from_dict(
                document["source_artifact"]
            ),
            document["durable_proof_payload"],
            document["durable_proof_payload_id"],
            document["durable_proof_replay_status"],
            document["authorizes_infeasibility"],
            document["official"],
            document["schema_version"],
        )
        if (
            document["exact_cache_preflight_entry_id"]
            != result.exact_cache_preflight_entry_id
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight entry content ID mismatch"
            )
        return result


def build_exact_cache_preflight_entry_v1(
    source: VerifiedExactInfeasibilitySourceV1,
) -> ExactCachePreflightEntryV1:
    """Project retained authority into a non-authorizing serializable index row."""

    _verify_retained_source_handle(source)
    return ExactCachePreflightEntryV1(source.artifact)


@dataclass(frozen=True, slots=True)
class ExactCachePreflightResultV1:
    """Content-addressed identity decision; never an infeasibility certificate."""

    request_id: str
    outcome: ExactCacheOutcome
    cache_entry_id: str | None
    mismatched_coordinates: tuple[str, ...]
    durable_proof_replay_status: str
    blockers: tuple[str, ...]
    authorizes_infeasibility: bool = False
    official: bool = False
    portable_planner_called: bool = False
    abstract_auditor_called: bool = False
    j0_called: bool = False
    ground_solver_called: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.request_id, "request_id")
        try:
            parsed_outcome = ExactCacheOutcome(self.outcome)
        except (TypeError, ValueError) as error:
            raise Phase3EExactCacheV1Error(
                "preflight outcome must be IDENTICAL_MATCH, NO_MATCH, or INVALID"
            ) from error
        object.__setattr__(self, "outcome", parsed_outcome)
        if self.cache_entry_id is not None:
            _cid(self.cache_entry_id, "cache_entry_id")
        if (
            tuple(name for name in _PREFLIGHT_COORDINATES if name in self.mismatched_coordinates)
            != self.mismatched_coordinates
            or len(set(self.mismatched_coordinates)) != len(self.mismatched_coordinates)
        ):
            raise Phase3EExactCacheV1Error(
                "preflight mismatch coordinates are invalid or out of order"
            )
        if any(type(blocker) is not str or not blocker for blocker in self.blockers):
            raise Phase3EExactCacheV1Error("preflight blockers must be nonempty strings")
        if (
            self.authorizes_infeasibility is not False
            or self.official is not False
            or self.portable_planner_called is not False
            or self.abstract_auditor_called is not False
            or self.j0_called is not False
            or self.ground_solver_called is not False
            or self.schema_version != SCHEMA_VERSION
        ):
            raise Phase3EExactCacheV1Error(
                "planner-free V1 preflight cannot claim execution, authority, or official status"
            )
        if parsed_outcome is ExactCacheOutcome.IDENTICAL_MATCH:
            if (
                self.cache_entry_id is None
                or self.mismatched_coordinates
                or self.durable_proof_replay_status
                != MISSING_DURABLE_PROOF_BLOCKER
                or self.blockers != NON_OFFICIAL_PREFLIGHT_BLOCKERS
            ):
                raise Phase3EExactCacheV1Error(
                    "identical preflight must retain the explicit durable-proof blocker"
                )
        elif parsed_outcome is ExactCacheOutcome.NO_MATCH:
            if self.blockers or self.durable_proof_replay_status not in {
                "NOT_PRESENT",
                "NOT_REPLAYED_IDENTITY_MISMATCH",
            }:
                raise Phase3EExactCacheV1Error(
                    "NO_MATCH cannot carry proof authority or an invalidity blocker"
                )
        elif not self.blockers or self.durable_proof_replay_status != "INVALID":
            raise Phase3EExactCacheV1Error(
                "INVALID preflight must identify a blocker"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.exact_cache_preflight_result.v1",
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "outcome": self.outcome.value,
            "cache_entry_id": self.cache_entry_id,
            "mismatched_coordinates": list(self.mismatched_coordinates),
            "durable_proof_replay_status": self.durable_proof_replay_status,
            "blockers": list(self.blockers),
            "authorizes_infeasibility": False,
            "official": False,
            "portable_planner_called": False,
            "abstract_auditor_called": False,
            "j0_called": False,
            "ground_solver_called": False,
        }

    @property
    def exact_cache_preflight_result_id(self) -> str:
        return _content_id(EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "exact_cache_preflight_result_id": self.exact_cache_preflight_result_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "ExactCachePreflightResultV1":
        expected = {
            "schema",
            "schema_version",
            "request_id",
            "outcome",
            "cache_entry_id",
            "mismatched_coordinates",
            "durable_proof_replay_status",
            "blockers",
            "authorizes_infeasibility",
            "official",
            "portable_planner_called",
            "abstract_auditor_called",
            "j0_called",
            "ground_solver_called",
            "exact_cache_preflight_result_id",
        }
        _fields(document, expected, "exact-cache preflight result")
        if (
            document["schema"] != "acfqp.exact_cache_preflight_result.v1"
            or type(document["mismatched_coordinates"]) is not list
            or type(document["blockers"]) is not list
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight result schema mismatch"
            )
        result = cls(
            document["request_id"],
            document["outcome"],
            document["cache_entry_id"],
            tuple(document["mismatched_coordinates"]),
            document["durable_proof_replay_status"],
            tuple(document["blockers"]),
            document["authorizes_infeasibility"],
            document["official"],
            document["portable_planner_called"],
            document["abstract_auditor_called"],
            document["j0_called"],
            document["ground_solver_called"],
            document["schema_version"],
        )
        if (
            document["exact_cache_preflight_result_id"]
            != result.exact_cache_preflight_result_id
        ):
            raise Phase3EExactCacheV1Error(
                "exact-cache preflight result content ID mismatch"
            )
        return result


def verify_exact_cache_preflight_v1(
    request: ExactCachePreflightRequestV1 | Mapping[str, Any],
    cache_entry: ExactCachePreflightEntryV1 | Mapping[str, Any] | None,
    *,
    current_model_source: object,
) -> ExactCachePreflightResultV1:
    """Check a cache row before planning; invalid rows fail closed as ``INVALID``."""

    parsed_request = ExactCachePreflightRequestV1.from_dict(
        request.to_dict() if isinstance(request, ExactCachePreflightRequestV1) else request
    )
    from acfqp.phase3e_fallback_v1 import GroundFallbackCapProfileV1

    profile = GroundFallbackCapProfileV1.from_dict(
        parsed_request.complete_search_profile
    )
    expected_request = build_exact_cache_preflight_request_v1(
        current_model_source,
        complete_search_profile=profile,
        regret_tolerance=parsed_request.regret_tolerance,
    )
    if parsed_request != expected_request:
        return ExactCachePreflightResultV1(
            parsed_request.exact_cache_preflight_request_id,
            ExactCacheOutcome.INVALID,
            None,
            (),
            "INVALID",
            ("REQUEST_DOES_NOT_REPLAY_FROM_CURRENT_MODEL_SOURCE",),
        )
    if cache_entry is None:
        return ExactCachePreflightResultV1(
            parsed_request.exact_cache_preflight_request_id,
            ExactCacheOutcome.NO_MATCH,
            None,
            (),
            "NOT_PRESENT",
            (),
        )
    try:
        parsed_entry = ExactCachePreflightEntryV1.from_dict(
            cache_entry.to_dict()
            if isinstance(cache_entry, ExactCachePreflightEntryV1)
            else cache_entry
        )
    except (Phase3EExactCacheV1Error, TypeError, ValueError):
        return ExactCachePreflightResultV1(
            parsed_request.exact_cache_preflight_request_id,
            ExactCacheOutcome.INVALID,
            None,
            (),
            "INVALID",
            ("CACHE_ENTRY_SCHEMA_OR_CONTENT_ID_INVALID",),
        )
    cached_identity = parsed_entry.exact_identity
    current_identity = parsed_request.exact_identity
    mismatches = tuple(
        name
        for name in _PREFLIGHT_COORDINATES
        if getattr(cached_identity, name) != getattr(current_identity, name)
    )
    if mismatches:
        return ExactCachePreflightResultV1(
            parsed_request.exact_cache_preflight_request_id,
            ExactCacheOutcome.NO_MATCH,
            parsed_entry.exact_cache_preflight_entry_id,
            mismatches,
            "NOT_REPLAYED_IDENTITY_MISMATCH",
            (),
        )
    return ExactCachePreflightResultV1(
        parsed_request.exact_cache_preflight_request_id,
        ExactCacheOutcome.IDENTICAL_MATCH,
        parsed_entry.exact_cache_preflight_entry_id,
        (),
        MISSING_DURABLE_PROOF_BLOCKER,
        NON_OFFICIAL_PREFLIGHT_BLOCKERS,
    )


__all__ = [
    "CURRENT_BINDING_SCHEMA",
    "EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN",
    "EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN",
    "EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN",
    "EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN",
    "EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN",
    "EXACT_INFEASIBILITY_PROOF_PROFILE_ID",
    "ExactCacheOutcome",
    "ExactCachePreflightEntryV1",
    "ExactCachePreflightRequestV1",
    "ExactCachePreflightResultV1",
    "ExactCachedInfeasibilityProofV1",
    "ExactInfeasibilityIdentityV1",
    "ExactInfeasibilitySourceArtifactV1",
    "MISSING_DURABLE_PROOF_BLOCKER",
    "NON_OFFICIAL_PREFLIGHT_BLOCKERS",
    "PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN",
    "PREFLIGHT_ENTRY_SCHEMA",
    "PREFLIGHT_REQUEST_SCHEMA",
    "PREFLIGHT_RESULT_SCHEMA",
    "PROOF_SCHEMA",
    "Phase3EExactCacheV1Error",
    "PlanFrozenExactCacheBindingV1",
    "SOURCE_KIND",
    "SOURCE_SCHEMA",
    "VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN",
    "VerifiedExactInfeasibilitySourceV1",
    "build_exact_cache_preflight_entry_v1",
    "build_exact_cache_preflight_request_v1",
    "build_exact_cached_infeasibility_proof_v1",
    "derive_exact_kernel_identity_from_model_source_v1",
    "derive_exact_kernel_identity_v1",
    "derive_exact_threshold_profile_from_model_source_v1",
    "verify_exact_cache_preflight_v1",
    "verify_exact_cached_infeasibility_v1",
    "verify_exact_infeasibility_source_v1",
]
