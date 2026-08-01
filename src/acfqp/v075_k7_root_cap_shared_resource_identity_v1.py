"""Exact typed K7 route-to-shared-resource identity derivation.

The shared-resource accounting schemas predate the complete typed K7 route
identity and therefore expose seven identity fields as constructor inputs.
This successor closes that structural gap for K7: callers provide only one
``V075K7RootCapAccountedSealedRouteIdentityV1`` and this module derives the
entire ``SharedResourceIdentityBindingV1`` from its verified authority graph.

This is deliberately only an identity authority.  It does not make live
measurement source claims, issue formal accounting vectors, or authorize an
official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_shared_resource_receipts_v1 as receipts_v1
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as ipc_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN,
    V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.93.0"
PROFILE_KEY = "v075_k7_root_cap_shared_resource_identity_v1"

REQUESTED_PHASE3E_DOMAIN_CONSTANTS = (
    "V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN",
    "V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN",
)
LOCAL_DOMAIN_TAGS = frozenset(
    {
        V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN,
        V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN,
    }
)
if not LOCAL_DOMAIN_TAGS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("K7 shared-resource identity domains are not registered")

DERIVED_FIELD_SOURCES = (
    ("counter_registry_id", "profile.counter_registry_id"),
    ("stage_profile_id", "profile.stage_profile_id"),
    ("boundary_profile_id", "profile.boundary_manifest_id"),
    ("execution_profile_id", "profile.execution_profile_id"),
    ("occurrence_id", "logical_occurrence.logical_occurrence_id"),
    ("route_attempt_id", "route_attempt.route_attempt_id"),
    ("decision_point_id", "decision_point.decision_point_id"),
)

_DERIVATION_ISSUER = object()
_VERIFICATION_ISSUER = object()


class V075K7RootCapSharedResourceIdentityV1Error(ValueError):
    """The typed route identity or its derived binding is stale/crossed."""


def _fail(message: str) -> NoReturn:
    raise V075K7RootCapSharedResourceIdentityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7RootCapSharedResourceIdentityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _derived_fields(
    route_identity: ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1,
) -> dict[str, str]:
    """Replay the source authority and return the only permitted mapping."""

    if (
        type(route_identity)
        is not ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
    ):
        _fail("identity derivation requires the exact typed accounted K7 route")
    try:
        route_identity._assert_current()  # noqa: SLF001 - exact source replay
    except Exception as error:
        raise V075K7RootCapSharedResourceIdentityV1Error(
            "typed accounted K7 route identity failed replay"
        ) from error

    profile = route_identity.profile
    occurrence = route_identity.logical_occurrence
    attempt = route_identity.route_attempt
    context = route_identity.route_context
    decision = route_identity.decision_point
    transaction = route_identity.transaction

    # Repeat the joins at this boundary.  This prevents the derivation from
    # becoming dependent on a future relaxation of the upstream route class.
    if (
        context.counter_registry_id != profile.counter_registry_id
        or occurrence.logical_occurrence_id != attempt.logical_occurrence_id
        or occurrence.logical_occurrence_id != context.logical_occurrence_id
        or attempt.route_attempt_id != context.route_attempt_id
        or decision.route_decision_context_id != context.route_decision_context_id
        or transaction.logical_occurrence_id != occurrence.logical_occurrence_id
        or transaction.route_attempt_id != attempt.route_attempt_id
        or transaction.decision_point_id != decision.decision_point_id
    ):
        _fail("typed K7 route graph crossed at the shared-resource boundary")

    values = {
        "counter_registry_id": profile.counter_registry_id,
        "stage_profile_id": profile.stage_profile_id,
        "boundary_profile_id": profile.boundary_manifest_id,
        "execution_profile_id": profile.execution_profile_id,
        "occurrence_id": occurrence.logical_occurrence_id,
        "route_attempt_id": attempt.route_attempt_id,
        "decision_point_id": decision.decision_point_id,
    }
    for name, value in values.items():
        _cid(value, name)
    return values


def _binding_field_tuple(
    binding: receipts_v1.SharedResourceIdentityBindingV1,
) -> tuple[str, ...]:
    return tuple(getattr(binding, name) for name, _source in DERIVED_FIELD_SOURCES)


@dataclass(frozen=True, slots=True)
class V075K7RootCapSharedResourceIdentityDerivationV1:
    """Issuer-owned derivation containing no caller-selected identity field."""

    _issuer: InitVar[object]
    route_identity: ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1 = field(
        repr=False, compare=False
    )
    _identity_binding: receipts_v1.SharedResourceIdentityBindingV1 = field(
        init=False, repr=False, compare=False
    )
    _validated_route_identity: (
        ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
    ) = field(init=False, repr=False, compare=False)
    _validated_identity_binding: receipts_v1.SharedResourceIdentityBindingV1 = field(
        init=False, repr=False, compare=False
    )
    _route_identity_id: str = field(init=False, repr=False)
    _identity_binding_id: str = field(init=False, repr=False)
    _derived_field_values: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _DERIVATION_ISSUER:
            _fail("K7 shared-resource identity derivation is caller-minted")
        values = _derived_fields(self.route_identity)
        try:
            binding = receipts_v1.SharedResourceIdentityBindingV1(**values)
        except Exception as error:
            raise V075K7RootCapSharedResourceIdentityV1Error(
                "derived shared-resource identity binding is invalid"
            ) from error
        object.__setattr__(self, "_identity_binding", binding)
        object.__setattr__(self, "_validated_route_identity", self.route_identity)
        object.__setattr__(self, "_validated_identity_binding", binding)
        object.__setattr__(
            self, "_route_identity_id", self.route_identity.route_identity_id
        )
        object.__setattr__(
            self, "_identity_binding_id", binding.identity_binding_id
        )
        object.__setattr__(
            self,
            "_derived_field_values",
            tuple(values[name] for name, _source in DERIVED_FIELD_SOURCES),
        )
        self._assert_current()

    def _assert_current(self) -> None:
        if (
            self.route_identity is not self._validated_route_identity
            or self._identity_binding is not self._validated_identity_binding
            or type(self.route_identity)
            is not ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1
            or type(self._identity_binding)
            is not receipts_v1.SharedResourceIdentityBindingV1
        ):
            _fail("K7 route or derived shared-resource binding object was replaced")
        values = _derived_fields(self.route_identity)
        current_values = tuple(
            values[name] for name, _source in DERIVED_FIELD_SOURCES
        )
        binding_values = _binding_field_tuple(self._identity_binding)
        if (
            self.route_identity.route_identity_id != self._route_identity_id
            or current_values != self._derived_field_values
            or binding_values != self._derived_field_values
            or self._identity_binding.identity_binding_id
            != self._identity_binding_id
        ):
            _fail("derived shared-resource identity binding is stale or crossed")

    @property
    def identity_binding(self) -> receipts_v1.SharedResourceIdentityBindingV1:
        self._assert_current()
        return self._identity_binding

    def _payload(self) -> dict[str, Any]:
        fields = {
            name: value
            for (name, _source), value in zip(
                DERIVED_FIELD_SOURCES, self._derived_field_values
            )
        }
        return {
            "schema": (
                "acfqp.v075_k7_root_cap_shared_resource_identity_derivation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "route_identity_id": self._route_identity_id,
            "shared_resource_identity_binding_id": self._identity_binding_id,
            "shared_resource_identity_binding": self._identity_binding.to_document(),
            "derived_field_sources": [
                {"target_field": target, "source_field": source}
                for target, source in DERIVED_FIELD_SOURCES
            ],
            **fields,
            "all_identity_fields_route_derived": True,
            "caller_selected_identity_fields": [],
            "exact_typed_route_identity_verified": True,
            "semantic_source_authority_present": False,
            "shared_resource_semantics_verified": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "actual_projection_proof_issued": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def derivation_id(self) -> str:
        self._assert_current()
        return content_id(
            V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        payload = self._payload()
        return {**payload, "identity_derivation_id": self.derivation_id}


def derive_v075_k7_root_cap_shared_resource_identity_v1(
    route_identity: ipc_v1.V075K7RootCapAccountedSealedRouteIdentityV1,
) -> V075K7RootCapSharedResourceIdentityDerivationV1:
    """Derive the seven-field binding; no field-level overrides exist."""

    return V075K7RootCapSharedResourceIdentityDerivationV1(
        _DERIVATION_ISSUER, route_identity
    )


@dataclass(frozen=True, slots=True)
class V075K7RootCapSharedResourceIdentityVerificationV1:
    """Fail-closed structural replay of one derivation."""

    _issuer: InitVar[object]
    derivation: V075K7RootCapSharedResourceIdentityDerivationV1 = field(
        repr=False, compare=False
    )
    _validated_derivation: V075K7RootCapSharedResourceIdentityDerivationV1 = field(
        init=False, repr=False, compare=False
    )
    _derivation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("K7 shared-resource identity verification is caller-minted")
        if (
            type(self.derivation)
            is not V075K7RootCapSharedResourceIdentityDerivationV1
        ):
            _fail("identity verification requires the exact derivation type")
        self.derivation._assert_current()
        object.__setattr__(self, "_validated_derivation", self.derivation)
        object.__setattr__(self, "_derivation_id", self.derivation.derivation_id)
        self._assert_current()

    def _assert_current(self) -> None:
        if self.derivation is not self._validated_derivation:
            _fail("K7 shared-resource identity derivation object was replaced")
        self.derivation._assert_current()
        if self.derivation.derivation_id != self._derivation_id:
            _fail("K7 shared-resource identity derivation changed after verification")

    def _payload(self) -> dict[str, Any]:
        derivation = self.derivation
        return {
            "schema": (
                "acfqp.v075_k7_root_cap_shared_resource_identity_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "identity_derivation_id": self._derivation_id,
            "route_identity_id": derivation._route_identity_id,  # noqa: SLF001
            "shared_resource_identity_binding_id": (
                derivation._identity_binding_id  # noqa: SLF001
            ),
            "verified_fields": [name for name, _source in DERIVED_FIELD_SOURCES],
            "verification_result": "PASS",
            "structural_identity_authority_only": True,
            "semantic_source_authority_present": False,
            "shared_resource_semantics_verified": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "actual_projection_proof_issued": False,
            "formal_vector_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        self._assert_current()
        return content_id(
            V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        payload = self._payload()
        return {**payload, "identity_verification_id": self.verification_id}


def verify_v075_k7_root_cap_shared_resource_identity_v1(
    derivation: V075K7RootCapSharedResourceIdentityDerivationV1,
) -> V075K7RootCapSharedResourceIdentityVerificationV1:
    return V075K7RootCapSharedResourceIdentityVerificationV1(
        _VERIFICATION_ISSUER, derivation
    )


__all__ = [
    "DERIVED_FIELD_SOURCES",
    "LOCAL_DOMAIN_TAGS",
    "PROFILE_KEY",
    "REQUESTED_PHASE3E_DOMAIN_CONSTANTS",
    "V075K7RootCapSharedResourceIdentityDerivationV1",
    "V075K7RootCapSharedResourceIdentityV1Error",
    "V075K7RootCapSharedResourceIdentityVerificationV1",
    "derive_v075_k7_root_cap_shared_resource_identity_v1",
    "verify_v075_k7_root_cap_shared_resource_identity_v1",
]
