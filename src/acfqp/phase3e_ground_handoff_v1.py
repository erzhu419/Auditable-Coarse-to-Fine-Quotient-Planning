"""Open the ground namespace only after a retained failed abstract audit.

The model-only Phase-3E front door deliberately ends before any ground-domain
binding.  This module is the narrow continuation boundary: it replays the
model-only source/result chain, requires the non-serializable semantic
authority emitted by the ``ABSTRACT_AUDIT`` handler, and only then imports and
calls the frozen Phase-3C ground binder.

The returned object is an opaque capability, not a serializable claim.  Its
metadata is content-addressed for downstream provenance, while the actual
frozen world and retained semantic authority remain process-local.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from acfqp._runtime_authority_v1 import (
    RuntimeAuthorityMintV1,
    bind_runtime_authority_v1,
    require_runtime_authority_v1,
    runtime_authority_fingerprint_v1,
)
from acfqp.phase3e_ids import (
    GROUND_BINDING_AFTER_FAILED_AUDIT_DOMAIN,
    Phase3EIdentityError,
    content_id,
    parse_content_id,
)
from acfqp.phase3e_model_only_v1 import (
    ModelOnlyOutcome,
    Phase3EModelOnlyResultV1,
    Phase3EModelOnlyV1Error,
    verify_phase3e_model_only_result_without_replanning_v1,
)
from acfqp.phase3e_rapm_consumer_v1 import (
    Phase3ERAPMConsumerError,
    load_phase3c_model_source_v1,
)
from acfqp.portable_sound_audit_v1 import AbstractPlanAuditV1
from acfqp.semantic_verification_v1 import (
    SemanticRole,
    SemanticVerificationResultV1,
    SemanticVerificationV1Error,
    require_semantic_verification_result_v1,
    verify_typed_attestation_v1,
)


SCHEMA_VERSION = "1.0.0"
GROUND_BINDING_AFTER_FAILED_AUDIT_SCHEMA = (
    "acfqp.ground_binding_after_failed_audit.v1"
)

_GROUND_BINDING_AUTHORITY = object()

_GROUND_BINDING_PUBLIC_IDENTITY_FIELDS = (
    "model_only_result_id",
    "source_lease_id",
    "selected_plan_id",
    "sound_proof_id",
    "abstract_audit_id",
    "abstract_audit_verification_attestation_id",
    "verification_work_record_id",
    "route_decision_context_id",
    "structural_id",
    "query_id",
    "build_epoch_id",
    "manifest_id",
    "portable_rapm_id",
    "bound_ground_action_catalogue_id",
    "locality_metadata_id",
)


class Phase3EGroundHandoffV1Error(ValueError):
    """The failed-audit authority does not permit a ground binding."""


@dataclass(frozen=True, slots=True)
class _GroundBindingMintV1:
    """Process-local issuer record behind a public ground-binding capability.

    Keeping the exact public identity tuple in a distinct retained object is
    intentional.  ``dataclasses.replace`` copies this mint when it copies a
    capability, so changing even one public field cannot silently mint a new
    authority while retaining the original private token.
    """

    public_identity: tuple[tuple[str, str], ...]
    world: object = field(repr=False, compare=False)
    semantic_authority: SemanticVerificationResultV1 = field(
        repr=False, compare=False
    )
    issuer: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.issuer is not _GROUND_BINDING_AUTHORITY:
            raise Phase3EGroundHandoffV1Error(
                "ground binding mint has no trusted issuer"
            )
        if tuple(name for name, _value in self.public_identity) != (
            _GROUND_BINDING_PUBLIC_IDENTITY_FIELDS
        ):
            raise Phase3EGroundHandoffV1Error(
                "ground binding mint has a malformed public identity"
            )
        if self.world is None:
            raise Phase3EGroundHandoffV1Error("opaque ground world is absent")


def _handoff_content_id(payload: dict[str, Any]) -> str:
    return content_id(
        GROUND_BINDING_AFTER_FAILED_AUDIT_DOMAIN,
        {
            "schema": "acfqp.phase3e_model_only_orchestration_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "role": "ground_binding_after_failed_audit",
            "payload": payload,
        },
    )


@dataclass(frozen=True, slots=True)
class GroundBindingAfterFailedAuditV1:
    """Opaque authority-bearing ground lease opened after ``ABSTRACT_AUDIT=FAIL``."""

    model_only_result_id: str
    source_lease_id: str
    selected_plan_id: str
    sound_proof_id: str
    abstract_audit_id: str
    abstract_audit_verification_attestation_id: str
    verification_work_record_id: str
    route_decision_context_id: str
    structural_id: str
    query_id: str
    build_epoch_id: str
    manifest_id: str
    portable_rapm_id: str
    bound_ground_action_catalogue_id: str
    locality_metadata_id: str
    _mint: _GroundBindingMintV1 = field(repr=False, compare=False)
    _instance_mint: RuntimeAuthorityMintV1 | None = field(
        default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self._instance_mint is not None:
            try:
                self._instance_mint.validate_construction(
                    self,
                    issuer=_GROUND_BINDING_AUTHORITY,
                    fingerprint=runtime_authority_fingerprint_v1(self),
                )
            except ValueError as error:
                raise Phase3EGroundHandoffV1Error(
                    "ground binding is a copied or modified live authority"
                ) from error
        if (
            type(self._mint) is not _GroundBindingMintV1
            or self._mint.issuer is not _GROUND_BINDING_AUTHORITY
        ):
            raise Phase3EGroundHandoffV1Error(
                "ground binding was not opened by the failed-audit handoff"
            )
        public_identity = tuple(
            (field_name, getattr(self, field_name))
            for field_name in _GROUND_BINDING_PUBLIC_IDENTITY_FIELDS
        )
        if public_identity != self._mint.public_identity:
            raise Phase3EGroundHandoffV1Error(
                "ground binding public identity differs from its retained mint"
            )
        for field_name, field_value in public_identity:
            try:
                parse_content_id(field_value)
            except Phase3EIdentityError as error:
                raise Phase3EGroundHandoffV1Error(
                    f"{field_name} must be a full content ID"
                ) from error
        try:
            retained = require_semantic_verification_result_v1(
                self._mint.semantic_authority, SemanticRole.ABSTRACT_AUDIT
            )
        except SemanticVerificationV1Error as error:
            raise Phase3EGroundHandoffV1Error(
                "opaque ground binding lost its abstract-audit authority"
            ) from error
        if (
            retained.outcome != "FAIL"
            or retained.attestation.verification_attestation_id
            != self.abstract_audit_verification_attestation_id
            or retained.attestation.artifact_id != self.abstract_audit_id
            or retained.verification_work_record.record_id
            != self.verification_work_record_id
            or retained.binding.route_context.route_decision_context_id
            != self.route_decision_context_id
            or retained.binding.route_context.structural_id != self.structural_id
            or retained.binding.route_context.query_id != self.query_id
            or retained.binding.route_context.build_epoch_id != self.build_epoch_id
        ):
            raise Phase3EGroundHandoffV1Error(
                "opaque ground binding does not retain ABSTRACT_AUDIT=FAIL"
            )

    def __copy__(self) -> object:
        raise Phase3EGroundHandoffV1Error(
            "ground binding live authority cannot be copied"
        )

    def __deepcopy__(self, memo: dict[int, object]) -> object:
        raise Phase3EGroundHandoffV1Error(
            "ground binding live authority cannot be deep-copied"
        )

    def __reduce_ex__(self, protocol: int) -> object:
        raise Phase3EGroundHandoffV1Error(
            "ground binding live authority cannot be serialized"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": GROUND_BINDING_AFTER_FAILED_AUDIT_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "model_only_result_id": self.model_only_result_id,
            "source_lease_id": self.source_lease_id,
            "selected_plan_id": self.selected_plan_id,
            "sound_proof_id": self.sound_proof_id,
            "abstract_audit_id": self.abstract_audit_id,
            "abstract_audit_verification_attestation_id": (
                self.abstract_audit_verification_attestation_id
            ),
            "verification_work_record_id": self.verification_work_record_id,
            "route_decision_context_id": self.route_decision_context_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "BuildEpoch_id": self.build_epoch_id,
            "manifest_id": self.manifest_id,
            "portable_rapm_id": self.portable_rapm_id,
            "bound_ground_action_catalogue_id": (
                self.bound_ground_action_catalogue_id
            ),
            "locality_metadata_id": self.locality_metadata_id,
        }

    @property
    def ground_binding_id(self) -> str:
        return _handoff_content_id(self._payload())

    @property
    def world(self) -> object:
        """Return the frozen ground world only from the opaque live capability."""

        if self._mint.issuer is not _GROUND_BINDING_AUTHORITY:  # pragma: no cover
            raise Phase3EGroundHandoffV1Error("ground binding authority is absent")
        return self._mint.world

    @property
    def semantic_authority(self) -> SemanticVerificationResultV1:
        """Retain the exact failed-audit handle for downstream chaining."""

        if self._mint.issuer is not _GROUND_BINDING_AUTHORITY:  # pragma: no cover
            raise Phase3EGroundHandoffV1Error("ground binding authority is absent")
        return self._mint.semantic_authority

    def metadata(self) -> dict[str, Any]:
        """Return auditable metadata without serializing the live capability."""

        return {**self._payload(), "ground_binding_id": self.ground_binding_id}


def _validated_failed_authority_v1(
    *,
    model_only_result: Phase3EModelOnlyResultV1,
    abstract_audit_authority: SemanticVerificationResultV1,
) -> SemanticVerificationResultV1:
    """Validate the retained semantic handle before any ground import/call."""

    if type(abstract_audit_authority) is not SemanticVerificationResultV1:
        raise Phase3EGroundHandoffV1Error(
            "ground handoff requires a retained SemanticVerificationResultV1, "
            "not raw audit bytes, an audit hash, or a typed attestation alone"
        )
    try:
        authority = require_semantic_verification_result_v1(
            abstract_audit_authority, SemanticRole.ABSTRACT_AUDIT
        )
        verify_typed_attestation_v1(
            authority.attestation, authority_result=authority
        )
    except SemanticVerificationV1Error as error:
        raise Phase3EGroundHandoffV1Error(
            f"invalid abstract-audit semantic authority: {error}"
        ) from error
    if authority.outcome != "FAIL":
        raise Phase3EGroundHandoffV1Error(
            "ground handoff requires ABSTRACT_AUDIT=FAIL"
        )
    if type(authority.artifact) is not AbstractPlanAuditV1:
        raise Phase3EGroundHandoffV1Error(
            "abstract-audit authority retains the wrong artifact type"
        )
    if authority.binding.route_context != model_only_result.route_context:
        raise Phase3EGroundHandoffV1Error(
            "abstract-audit authority belongs to a foreign route context"
        )
    audit = model_only_result.audit
    if (
        authority.artifact.to_dict() != audit.to_dict()
        or authority.attestation.artifact_id != audit.audit_id
    ):
        raise Phase3EGroundHandoffV1Error(
            "abstract-audit authority does not bind the model-only audit"
        )
    expected_evidence_ids = tuple(
        sorted(
            (
                model_only_result.source_lease.source_lease_id,
                model_only_result.selected_plan.selected_contingent_plan_id,
                model_only_result.sound_proof.proof_id,
                model_only_result.result_id,
                model_only_result.identities.identities_id,
                model_only_result.rebuild_policy.rebuild_policy_id,
                model_only_result.logical_occurrence.logical_occurrence_id,
                model_only_result.route_attempt.route_attempt_id,
                model_only_result.route_context.route_decision_context_id,
            )
        )
    )
    if authority.recomputed_evidence_ids != expected_evidence_ids:
        raise Phase3EGroundHandoffV1Error(
            "abstract-audit authority omits or substitutes model-only evidence"
        )
    return authority


def open_ground_binding_after_failed_audit_v1(
    source_bundle: str | Path,
    *,
    model_only_result: Phase3EModelOnlyResultV1,
    abstract_audit_authority: SemanticVerificationResultV1,
) -> GroundBindingAfterFailedAuditV1:
    """Replay model-only evidence, then and only then bind the ground world."""

    if type(model_only_result) is not Phase3EModelOnlyResultV1:
        raise Phase3EGroundHandoffV1Error(
            "model_only_result must be Phase3EModelOnlyResultV1"
        )
    if (
        model_only_result.outcome is not ModelOnlyOutcome.FAIL
        or model_only_result.ground_binding_required is not True
        or model_only_result.audit.outcome != "FAIL"
    ):
        raise Phase3EGroundHandoffV1Error(
            "ground binding is forbidden unless the model-only result is FAIL"
        )

    # Everything above and below this comment, until the lazy imports, remains
    # in the model-only namespace.  In particular, a swapped bundle/model/epoch
    # or stale source lease fails before ``load_frozen_phase3c_world`` exists in
    # this module's runtime namespace.
    try:
        source = load_phase3c_model_source_v1(
            source_bundle, query_key=model_only_result.source_lease.query_key
        )
        replayed = verify_phase3e_model_only_result_without_replanning_v1(
            model_only_result, source=source
        )
    except (Phase3ERAPMConsumerError, Phase3EModelOnlyV1Error, ValueError) as error:
        raise Phase3EGroundHandoffV1Error(
            f"model-only source/result replay failed before ground binding: {error}"
        ) from error
    if replayed.to_dict() != model_only_result.to_dict():
        raise Phase3EGroundHandoffV1Error(
            "model-only semantic replay changed the supplied result"
        )
    authority = _validated_failed_authority_v1(
        model_only_result=replayed,
        abstract_audit_authority=abstract_audit_authority,
    )

    # This is the unique authorization boundary.  Do not move either import or
    # call above the complete model-only and semantic-authority checks.
    from acfqp.frozen_phase3c import load_frozen_phase3c_world
    from acfqp.phase3e_fallback_v1 import safe_chain_fallback_context_identity_v1

    try:
        world = load_frozen_phase3c_world(source_bundle)
        ground_identities = safe_chain_fallback_context_identity_v1(world)
    except (TypeError, ValueError, OSError) as error:
        raise Phase3EGroundHandoffV1Error(
            f"authorized ground binding failed: {error}"
        ) from error

    expected_identities = {
        "structural_id": replayed.identities.structural_id,
        "query_id": replayed.identities.query_id,
        "build_epoch_id": replayed.identities.build_epoch_id,
        "manifest_id": replayed.identities.manifest_id,
        "portable_rapm_id": replayed.identities.portable_rapm_id,
    }
    for field_name, expected in expected_identities.items():
        if ground_identities.get(field_name) != expected:
            raise Phase3EGroundHandoffV1Error(
                f"ground/model-only identity mismatch for {field_name}"
            )
    for field_name in (
        "bound_ground_action_catalogue_id",
        "locality_metadata_id",
    ):
        try:
            parse_content_id(ground_identities[field_name])
        except (KeyError, Phase3EIdentityError) as error:
            raise Phase3EGroundHandoffV1Error(
                f"ground binder omitted {field_name}"
            ) from error

    public_identity = {
        "model_only_result_id": replayed.result_id,
        "source_lease_id": replayed.source_lease.source_lease_id,
        "selected_plan_id": replayed.selected_plan.selected_contingent_plan_id,
        "sound_proof_id": replayed.sound_proof.proof_id,
        "abstract_audit_id": replayed.audit.audit_id,
        "abstract_audit_verification_attestation_id": (
            authority.attestation.verification_attestation_id
        ),
        "verification_work_record_id": authority.verification_work_record.record_id,
        "route_decision_context_id": (
            replayed.route_context.route_decision_context_id
        ),
        "structural_id": ground_identities["structural_id"],
        "query_id": ground_identities["query_id"],
        "build_epoch_id": ground_identities["build_epoch_id"],
        "manifest_id": ground_identities["manifest_id"],
        "portable_rapm_id": ground_identities["portable_rapm_id"],
        "bound_ground_action_catalogue_id": (
            ground_identities["bound_ground_action_catalogue_id"]
        ),
        "locality_metadata_id": ground_identities["locality_metadata_id"],
    }
    mint = _GroundBindingMintV1(
        public_identity=tuple(
            (field_name, public_identity[field_name])
            for field_name in _GROUND_BINDING_PUBLIC_IDENTITY_FIELDS
        ),
        world=world,
        semantic_authority=authority,
        issuer=_GROUND_BINDING_AUTHORITY,
    )
    binding = GroundBindingAfterFailedAuditV1(**public_identity, _mint=mint)
    return bind_runtime_authority_v1(
        binding,
        issuer=_GROUND_BINDING_AUTHORITY,
    )


def require_ground_binding_after_failed_audit_v1(
    binding: GroundBindingAfterFailedAuditV1,
) -> GroundBindingAfterFailedAuditV1:
    """Reject metadata-shaped or manually constructed substitutes."""

    if (
        type(binding) is not GroundBindingAfterFailedAuditV1
        or type(binding._mint) is not _GroundBindingMintV1
        or binding._mint.issuer is not _GROUND_BINDING_AUTHORITY
    ):
        raise Phase3EGroundHandoffV1Error(
            "ground binding is not an authority-bearing live capability"
        )
    try:
        require_runtime_authority_v1(
            binding,
            issuer=_GROUND_BINDING_AUTHORITY,
        )
    except ValueError as error:
        raise Phase3EGroundHandoffV1Error(
            "ground binding is not the retained minted instance"
        ) from error
    # Trigger the retained-authority checks in one stable public boundary.
    binding.__post_init__()
    return binding


__all__ = [
    "GROUND_BINDING_AFTER_FAILED_AUDIT_SCHEMA",
    "GroundBindingAfterFailedAuditV1",
    "Phase3EGroundHandoffV1Error",
    "open_ground_binding_after_failed_audit_v1",
    "require_ground_binding_after_failed_audit_v1",
]
