"""Law-free registered occurrence-worker boundary for V0-075.

The production worker registry is intentionally complete before any backend
is enabled.  All five preregistered arms have distinct route and proposal
semantics, but every scientific backend remains ``NOT_READY`` until the
tracked V0-075 total-lift authority and route-native wrappers exist.

The process-facing construction entrypoint accepts canonical bytes only.  It
never accepts a kernel, transition law, reveal, salt, private signer,
observer session, callback, cache, or resume object.  Observation payloads
are capability projections countersigned for this worker boundary; the
worker receives public verification keys and signatures, never signing
authority.  The source-prior payload is accepted only by the SOURCE arm and
is transported as the exact canonical adapter bytes plus an independent
verification reference.

This module does not open a target and does not execute a scientific route.
Its deterministic construction executor exists to validate serialization,
arm separation, accounting, and fail-closed reconstruction before the final
production worker registry is frozen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_public_campaign_authority_v1 as public_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_registered_occurrence_worker_v1"
PRODUCTION_EXECUTION_STATUS = (
    "NOT_READY_V075_ROUTE_BACKENDS_AND_TOTAL_LIFT_AUTHORITY_UNBOUND"
)
CONSTRUCTION_FIXTURE_ONLY = True

MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_RESULT_BYTES = 512 * 1024
MAX_CAPABILITIES_PER_REQUEST = 200_000
MAX_SOURCE_PRIOR_BYTES = 128 * 1024
MAX_SOURCE_VERIFICATION_BYTES = 64 * 1024

SOURCE_PRIOR_PROFILE_KEY = "v075_source_prior_adapter_v1"
SOURCE_PRIOR_ADAPTER_DOMAIN = "acfqp:v075-source-prior-adapter:v1"
SOURCE_PRIOR_VERIFICATION_DOMAIN = (
    "acfqp:v075-source-prior-adapter-verification:v1"
)
SOURCE_PRIOR_ADAPTER_TYPE = (
    "acfqp.v075_source_prior_adapter_v1.V075SourcePriorAdapterV1"
)
SOURCE_PRIOR_VERIFICATION_TYPE = (
    "acfqp.v075_source_prior_adapter_v1."
    "V075SourcePriorAdapterVerificationV1"
)

DOMAIN_TAGS = {
    "arm_registration": "acfqp:v075-worker-arm-registration:v1",
    "worker_registry": "acfqp:v075-production-worker-registry-draft:v1",
    "threshold_profile": "acfqp:v075-worker-threshold-profile:v1",
    "cap_profile": "acfqp:v075-worker-cap-profile:v1",
    "source_transport": "acfqp:v075-worker-source-prior-transport:v1",
    "total_lift_ref": "acfqp:v075-worker-total-lift-authority-ref:v1",
    "capability_ref": "acfqp:v075-worker-observation-capability-ref:v1",
    "occurrence": "acfqp:v075-law-free-worker-occurrence:v1",
    "request": "acfqp:v075-registered-occurrence-worker-request:v1",
    "counter": "acfqp:v075-registered-worker-counter:v1",
    "work": "acfqp:v075-registered-worker-work:v1",
    "result": "acfqp:v075-registered-occurrence-worker-result:v1",
}

CAPABILITY_ATTESTATION_DOMAIN = (
    b"acfqp:v075-worker-accepted-observation-capability:v1"
)

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 occurrence-worker domains must be unique")


class V075RegisteredOccurrenceWorkerInvariantViolation(ValueError):
    """A worker registry, request, capability, result, or counter drifted."""


class V075RegisteredOccurrenceWorkerNotReady(RuntimeError):
    """Production execution is locked until route authorities are concrete."""


def _fail(message: str) -> None:
    raise V075RegisteredOccurrenceWorkerInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 128
        or any(not (character.isupper() or character.isdigit() or character == "_")
                for character in value)
    ):
        _fail(f"{field_name} must be one bounded uppercase token")
    return value


def _strict_mapping(
    value: Any,
    *,
    keys: set[str],
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} fields are missing, unknown, or malformed")
    return value


def _strict_load(raw: bytes, *, byte_cap: int, field_name: str) -> Any:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{field_name} bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
        if canonical_json_bytes(document) != raw:
            _fail(f"{field_name} bytes are not canonical")
        return document
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            f"{field_name} bytes are invalid: {error}"
        ) from error


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("worker arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


class V075WorkerArmV1(str, Enum):
    SOURCE_CONSENSUS_PRIOR = "SOURCE_CONSENSUS_PRIOR"
    NO_PRIOR = "NO_PRIOR"
    WRONG_CONSENSUS_PRIOR = "WRONG_CONSENSUS_PRIOR"
    OOD_ABSTENTION = "OOD_ABSTENTION"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class V075WorkerRouteV1(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class V075WorkerProposalSemanticsV1(str, Enum):
    SOURCE_FORWARD_MIDRANK = "SOURCE_ARCHIVE_FORWARD_MIDRANK"
    NO_PRIOR = "NO_PRIOR"
    WRONG_FIXED_REVERSED_MIDRANK = (
        "REGISTERED_WRONG_REVERSED_MIDRANK_NO_SOURCE_PAYLOAD"
    )
    OOD_TYPED_ABSTENTION = "OOD_TYPED_SCHEMA_ABSTENTION_NEUTRAL"
    DIRECT_NOT_APPLICABLE = "MATCHED_DIRECT_NO_SELECTOR"


class V075WorkerBackendStatusV1(str, Enum):
    NOT_READY = "NOT_READY"


_ARM_SPEC = (
    (
        V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        V075WorkerRouteV1.ADAPTIVE_QUOTIENT,
        V075WorkerProposalSemanticsV1.SOURCE_FORWARD_MIDRANK,
        True,
    ),
    (
        V075WorkerArmV1.NO_PRIOR,
        V075WorkerRouteV1.ADAPTIVE_QUOTIENT,
        V075WorkerProposalSemanticsV1.NO_PRIOR,
        False,
    ),
    (
        V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
        V075WorkerRouteV1.ADAPTIVE_QUOTIENT,
        V075WorkerProposalSemanticsV1.WRONG_FIXED_REVERSED_MIDRANK,
        False,
    ),
    (
        V075WorkerArmV1.OOD_ABSTENTION,
        V075WorkerRouteV1.ADAPTIVE_QUOTIENT,
        V075WorkerProposalSemanticsV1.OOD_TYPED_ABSTENTION,
        False,
    ),
    (
        V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        V075WorkerRouteV1.MATCHED_DIRECT_GROUND,
        V075WorkerProposalSemanticsV1.DIRECT_NOT_APPLICABLE,
        False,
    ),
)


@dataclass(frozen=True, slots=True)
class V075WorkerArmRegistrationV1:
    ordinal: int
    arm: V075WorkerArmV1
    route: V075WorkerRouteV1
    proposal_semantics: V075WorkerProposalSemanticsV1
    source_prior_required: bool
    backend_status: V075WorkerBackendStatusV1 = (
        V075WorkerBackendStatusV1.NOT_READY
    )

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal not in range(5)
            or type(self.arm) is not V075WorkerArmV1
            or type(self.route) is not V075WorkerRouteV1
            or type(self.proposal_semantics)
            is not V075WorkerProposalSemanticsV1
            or type(self.source_prior_required) is not bool
            or self.backend_status is not V075WorkerBackendStatusV1.NOT_READY
            or (
                self.arm is V075WorkerArmV1.MATCHED_DIRECT_GROUND
            )
            != (self.route is V075WorkerRouteV1.MATCHED_DIRECT_GROUND)
            or self.source_prior_required
            != (self.arm is V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR)
        ):
            _fail("worker arm registration is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_worker_arm_registration.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "arm": self.arm.value,
            "route": self.route.value,
            "proposal_semantics": self.proposal_semantics.value,
            "source_prior_requirement": (
                "REQUIRED_VERIFIED_CANONICAL_BYTES_AND_REF"
                if self.source_prior_required
                else "FORBIDDEN"
            ),
            "observation_input": "SIGNED_CAPABILITIES_ONLY",
            "total_lift_authority_required": True,
            "backend_status": self.backend_status.value,
            "v072_target_authority_allowed": False,
        }

    @property
    def registration_id(self) -> str:
        return _hash("arm_registration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registration_id": self.registration_id}


@dataclass(frozen=True, slots=True)
class V075ProductionWorkerRegistryDraftV1:
    registrations: tuple[V075WorkerArmRegistrationV1, ...]

    def __post_init__(self) -> None:
        expected = tuple(
            V075WorkerArmRegistrationV1(index, *spec)
            for index, spec in enumerate(_ARM_SPEC)
        )
        if (
            type(self.registrations) is not tuple
            or self.registrations != expected
        ):
            _fail("worker registry is incomplete, reordered, or altered")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_worker_registry_draft.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "arm_order": [item.arm.value for item in self.registrations],
            "registration_ids": [
                item.registration_id for item in self.registrations
            ],
            "production_execution_status": PRODUCTION_EXECUTION_STATUS,
            "final_spec_frozen": False,
            "construction_fixture_only": True,
        }

    @property
    def registry_id(self) -> str:
        return _hash("worker_registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "registrations": [
                item.to_document() for item in self.registrations
            ],
            "registry_id": self.registry_id,
        }

    def require_arm(
        self,
        arm: V075WorkerArmV1,
    ) -> V075WorkerArmRegistrationV1:
        if type(arm) is not V075WorkerArmV1:
            _fail("worker arm lookup is not typed")
        return self.registrations[list(V075WorkerArmV1).index(arm)]


def freeze_v075_worker_registry_draft_v1(
) -> V075ProductionWorkerRegistryDraftV1:
    return V075ProductionWorkerRegistryDraftV1(
        tuple(
            V075WorkerArmRegistrationV1(index, *spec)
            for index, spec in enumerate(_ARM_SPEC)
        )
    )


@dataclass(frozen=True, slots=True)
class V075WorkerThresholdProfileV1:
    horizon: int = 2
    risk_tolerance: Fraction = Fraction(1, 20)
    normalized_regret_tolerance: Fraction = Fraction(1, 20)
    reward_ceiling: Fraction = Fraction(3, 64)

    def __post_init__(self) -> None:
        if (
            self.horizon != 2
            or self.risk_tolerance != Fraction(1, 20)
            or self.normalized_regret_tolerance != Fraction(1, 20)
            or self.reward_ceiling != Fraction(3, 64)
        ):
            _fail("worker threshold profile drifted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_worker_threshold_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "horizon": self.horizon,
            "risk_tolerance": _fraction_document(self.risk_tolerance),
            "normalized_regret_tolerance": _fraction_document(
                self.normalized_regret_tolerance
            ),
            "reward_ceiling": _fraction_document(self.reward_ceiling),
            "exact_rational_arithmetic": True,
        }

    @property
    def threshold_profile_id(self) -> str:
        return _hash("threshold_profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "threshold_profile_id": self.threshold_profile_id,
        }


@dataclass(frozen=True, slots=True)
class V075WorkerCapProfileV1:
    maximum_adaptive_rounds: int = 2
    initial_discovery_draws_per_row: int = 64
    initial_validation_draws_per_row: int = 2_048
    promotion_validation_draws_per_round: int = 2_048
    new_child_discovery_draws_per_row: int = 64
    new_child_validation_draws_per_row: int = 8_192
    maximum_new_child_action_rows: int = 19
    maximum_incremental_draws_per_adaptive_arm: int = 160_960
    direct_validation_checkpoints: tuple[int, ...] = (
        2_048,
        4_096,
        8_192,
        16_384,
    )

    def __post_init__(self) -> None:
        if (
            self.maximum_adaptive_rounds != 2
            or self.initial_discovery_draws_per_row != 64
            or self.initial_validation_draws_per_row != 2_048
            or self.promotion_validation_draws_per_round != 2_048
            or self.new_child_discovery_draws_per_row != 64
            or self.new_child_validation_draws_per_row != 8_192
            or self.maximum_new_child_action_rows != 19
            or self.maximum_incremental_draws_per_adaptive_arm != 160_960
            or self.direct_validation_checkpoints
            != (2_048, 4_096, 8_192, 16_384)
        ):
            _fail("worker cap profile drifted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_worker_cap_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "maximum_adaptive_rounds": self.maximum_adaptive_rounds,
            "initial_discovery_draws_per_row": (
                self.initial_discovery_draws_per_row
            ),
            "initial_validation_draws_per_row": (
                self.initial_validation_draws_per_row
            ),
            "promotion_validation_draws_per_round": (
                self.promotion_validation_draws_per_round
            ),
            "new_child_discovery_draws_per_row": (
                self.new_child_discovery_draws_per_row
            ),
            "new_child_validation_draws_per_row": (
                self.new_child_validation_draws_per_row
            ),
            "maximum_new_child_action_rows": (
                self.maximum_new_child_action_rows
            ),
            "maximum_incremental_draws_per_adaptive_arm": (
                self.maximum_incremental_draws_per_adaptive_arm
            ),
            "direct_validation_checkpoints": list(
                self.direct_validation_checkpoints
            ),
            "post_run_cap_adjustment_allowed": False,
        }

    @property
    def cap_profile_id(self) -> str:
        return _hash("cap_profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_profile_id": self.cap_profile_id}


@dataclass(frozen=True, slots=True)
class V075TotalLiftAuthorityRefV1:
    authority_id: str
    independent_verification_id: str
    canonical_artifact_sha256: str
    authority_status: str

    def __post_init__(self) -> None:
        ids = tuple(
            _cid(value, name)
            for value, name in (
                (self.authority_id, "total-lift authority"),
                (
                    self.independent_verification_id,
                    "total-lift independent verification",
                ),
                (
                    self.canonical_artifact_sha256,
                    "total-lift artifact digest",
                ),
            )
        )
        if (
            len(set(ids)) != 3
            or self.authority_status
            != "CONSTRUCTION_REFERENCE_PRODUCTION_AUTHORITY_NOT_READY"
        ):
            _fail("total-lift authority reference is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_worker_total_lift_authority_ref.v1",
            "schema_version": SCHEMA_VERSION,
            "authority_id": self.authority_id,
            "independent_verification_id": (
                self.independent_verification_id
            ),
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "semantic_profile": (
                "V074_MODELED_SUPPORT_TOTAL_LIFT_ENVIRONMENT_FAILURE_"
                "PLUS_POLICY_ABORT"
            ),
            "environment_failure_preserved": True,
            "unmodeled_reachable_child": (
                "ABSORBING_POLICY_ABORT_FAILURE"
            ),
            "policy_abort_continuation_reward": {
                "numerator": 0,
                "denominator": 1,
            },
            "complete_disjoint_exhaustive_partition_required": True,
            "authority_status": self.authority_status,
            "production_authorizing": False,
        }

    @property
    def ref_id(self) -> str:
        return _hash("total_lift_ref", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "ref_id": self.ref_id}


def construction_total_lift_authority_ref_v1(
    marker: str,
) -> V075TotalLiftAuthorityRefV1:
    _token(marker, "construction total-lift marker")

    def fixture_id(role: str) -> str:
        return hashlib.sha256(
            b"acfqp:v075-construction-total-lift-ref:v1"
            + b"\x00"
            + role.encode("ascii")
            + b"\x00"
            + marker.encode("ascii")
        ).hexdigest()

    return V075TotalLiftAuthorityRefV1(
        fixture_id("AUTHORITY"),
        fixture_id("VERIFICATION"),
        fixture_id("ARTIFACT"),
        "CONSTRUCTION_REFERENCE_PRODUCTION_AUTHORITY_NOT_READY",
    )


_CAPABILITY_KEYS = {
    "schema",
    "schema_version",
    "observation_record_id",
    "target_tape_namespace_id",
    "environment_commitment_id",
    "context_id",
    "row_binding_id",
    "source_state_id",
    "remaining_horizon",
    "action",
    "stream_id",
    "pairing_group_id",
    "observer_epoch_index",
    "lane",
    "arm",
    "accepted_draw_index",
    "next_ranks",
    "failure",
    "terminal",
    "spawn_cell",
    "spawn_rank",
    "realized_row_reward",
    "observer_signature_hex",
    "authority_scope",
    "capability_id",
}


def capability_attestation_signing_bytes_v1(
    *,
    signer_registry_id: str,
    observer_signer_key_id: str,
    capability_bytes: bytes,
) -> bytes:
    _cid(signer_registry_id, "capability signer registry")
    _cid(observer_signer_key_id, "capability observer signer key")
    document = _strict_load(
        capability_bytes,
        byte_cap=64 * 1024,
        field_name="observation capability",
    )
    _validate_capability_document(document)
    return (
        CAPABILITY_ATTESTATION_DOMAIN
        + b"\x00"
        + canonical_json_bytes(
            {
                "schema": (
                    "acfqp.v075_worker_capability_attestation_message.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "signer_registry_id": signer_registry_id,
                "observer_signer_key_id": observer_signer_key_id,
                "capability_id": document["capability_id"],
                "capability_bytes_sha256": hashlib.sha256(
                    capability_bytes
                ).hexdigest(),
            }
        )
    )


def _validate_capability_document(document: Any) -> dict[str, Any]:
    item = _strict_mapping(
        document,
        keys=_CAPABILITY_KEYS,
        field_name="observation capability",
    )
    for key in (
        "observation_record_id",
        "target_tape_namespace_id",
        "environment_commitment_id",
        "context_id",
        "row_binding_id",
        "source_state_id",
        "stream_id",
        "pairing_group_id",
        "capability_id",
    ):
        _cid(item[key], f"capability {key}")
    if (
        item["schema"] != "acfqp.v075_public_observation_capability.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or type(item["remaining_horizon"]) is not int
        or item["remaining_horizon"] not in (1, 2)
        or type(item["action"]) is not list
        or len(item["action"]) != 3
        or any(type(value) is not int for value in item["action"])
        or item["action"][0] >= item["action"][1]
        or item["action"][2] not in item["action"][:2]
        or type(item["observer_epoch_index"]) is not int
        or item["observer_epoch_index"] not in range(4)
        or item["lane"] not in {"DISCOVERY", "VALIDATION"}
        or item["arm"] not in tuple(arm.value for arm in V075WorkerArmV1)
        or type(item["accepted_draw_index"]) is not int
        or item["accepted_draw_index"] < 0
        or type(item["next_ranks"]) is not list
        or not item["next_ranks"]
        or any(type(value) is not int or not 0 <= value <= 6
               for value in item["next_ranks"])
        or type(item["failure"]) is not bool
        or type(item["terminal"]) is not bool
        or type(item["spawn_cell"]) not in {int, type(None)}
        or type(item["spawn_rank"]) not in {int, type(None)}
        or type(item["realized_row_reward"]) is not Fraction
        or item["realized_row_reward"] < 0
        or type(item["observer_signature_hex"]) is not str
        or not item["observer_signature_hex"]
        or len(item["observer_signature_hex"]) % 2
        or any(character not in "0123456789abcdef"
               for character in item["observer_signature_hex"])
        or item["authority_scope"] not in {
            "PRODUCTION_OPEN",
            "CONSTRUCTION_ONLY",
        }
    ):
        _fail("observation capability semantics are malformed")
    expected_id = hashlib.sha256(
        b"acfqp:v075-public-observation-capability:v1"
        + b"\x00"
        + canonical_json_bytes(
            {key: value for key, value in item.items()
             if key != "capability_id"}
        )
    ).hexdigest()
    if item["capability_id"] != expected_id:
        _fail("observation capability identity changed")
    return item


@dataclass(frozen=True, slots=True)
class V075WorkerObservationCapabilityRefV1:
    capability_bytes: bytes = field(repr=False)
    signer_registry: public_authority.V075TrustedSignerRegistryV1
    capability_attestation_signature_hex: str
    _document: dict[str, Any] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            type(self.signer_registry)
            is not public_authority.V075TrustedSignerRegistryV1
        ):
            _fail("capability signer registry is not typed")
        document = _validate_capability_document(
            _strict_load(
                self.capability_bytes,
                byte_cap=64 * 1024,
                field_name="observation capability",
            )
        )
        key = self.signer_registry.observer_evidence_key
        message = capability_attestation_signing_bytes_v1(
            signer_registry_id=self.signer_registry.registry_id,
            observer_signer_key_id=key.key_id,
            capability_bytes=self.capability_bytes,
        )
        if not public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=key,
            message=message,
            signature_hex=self.capability_attestation_signature_hex,
        ):
            _fail("worker capability attestation signature is invalid")
        object.__setattr__(self, "_document", document)

    @property
    def capability_id(self) -> str:
        return self._document["capability_id"]

    @property
    def arm(self) -> V075WorkerArmV1:
        return V075WorkerArmV1(self._document["arm"])

    @property
    def accepted_draw_index(self) -> int:
        return self._document["accepted_draw_index"]

    @property
    def target_tape_namespace_id(self) -> str:
        return self._document["target_tape_namespace_id"]

    @property
    def context_id(self) -> str:
        return self._document["context_id"]

    @property
    def row_binding_id(self) -> str:
        return self._document["row_binding_id"]

    @property
    def stream_id(self) -> str:
        return self._document["stream_id"]

    def _payload(self) -> dict[str, Any]:
        key = self.signer_registry.observer_evidence_key
        return {
            "schema": "acfqp.v075_worker_observation_capability_ref.v1",
            "schema_version": SCHEMA_VERSION,
            "capability_id": self.capability_id,
            "capability_bytes_sha256": hashlib.sha256(
                self.capability_bytes
            ).hexdigest(),
            "capability_bytes_hex": self.capability_bytes.hex(),
            "signer_registry_id": self.signer_registry.registry_id,
            "observer_signer_key_id": key.key_id,
            "observer_verification_key": {
                "schema": (
                    "acfqp.v075_worker_observer_verification_key.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "key_role": key.key_role,
                "algorithm": "RSASSA-PKCS1-v1_5-SHA256",
                "modulus_hex": format(key.modulus, "x"),
                "public_exponent": key.public_exponent,
                "key_id": key.key_id,
            },
            "capability_attestation_signature_hex": (
                self.capability_attestation_signature_hex
            ),
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "stream_id": self.stream_id,
            "arm": self.arm.value,
            "accepted_draw_index": self.accepted_draw_index,
            "capability_only": True,
            "production_trust_root_bound": False,
        }

    @property
    def ref_id(self) -> str:
        return _hash("capability_ref", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "ref_id": self.ref_id}


def _public_key_from_document(
    document: Any,
) -> public_authority.V075RSAPublicVerificationKeyV1:
    item = _strict_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "key_role",
            "algorithm",
            "modulus_hex",
            "public_exponent",
            "key_id",
        },
        field_name="capability public key",
    )
    if (
        item["schema"]
        != "acfqp.v075_worker_observer_verification_key.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["algorithm"] != "RSASSA-PKCS1-v1_5-SHA256"
        or type(item["modulus_hex"]) is not str
        or not item["modulus_hex"]
    ):
        _fail("capability public key document changed")
    try:
        key = public_authority.V075RSAPublicVerificationKeyV1(
            item["key_role"],
            int(item["modulus_hex"], 16),
            item["public_exponent"],
        )
    except (ValueError, TypeError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            "capability public key is invalid"
        ) from error
    if item["key_id"] != key.key_id:
        _fail("capability public key identity changed")
    return key


def _capability_ref_from_document(
    document: Any,
    *,
    expected_signer_registry_id: str | None,
) -> dict[str, Any]:
    item = _strict_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "capability_id",
            "capability_bytes_sha256",
            "capability_bytes_hex",
            "signer_registry_id",
            "observer_signer_key_id",
            "observer_verification_key",
            "capability_attestation_signature_hex",
            "target_tape_namespace_id",
            "context_id",
            "row_binding_id",
            "stream_id",
            "arm",
            "accepted_draw_index",
            "capability_only",
            "production_trust_root_bound",
            "ref_id",
        },
        field_name="worker capability ref",
    )
    if (
        item["schema"]
        != "acfqp.v075_worker_observation_capability_ref.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["capability_only"] is not True
        or item["production_trust_root_bound"] is not False
        or (
            expected_signer_registry_id is not None
            and item["signer_registry_id"] != expected_signer_registry_id
        )
    ):
        _fail("worker capability-ref contract changed")
    for key_name in (
        "capability_id",
        "capability_bytes_sha256",
        "signer_registry_id",
        "observer_signer_key_id",
        "target_tape_namespace_id",
        "context_id",
        "row_binding_id",
        "stream_id",
        "ref_id",
    ):
        _cid(item[key_name], f"worker capability {key_name}")
    try:
        capability_bytes = bytes.fromhex(item["capability_bytes_hex"])
    except (TypeError, ValueError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            "worker capability bytes are not hexadecimal"
        ) from error
    capability = _validate_capability_document(
        _strict_load(
            capability_bytes,
            byte_cap=64 * 1024,
            field_name="worker capability",
        )
    )
    public_key = _public_key_from_document(item["observer_verification_key"])
    if (
        public_key.key_role != "OBSERVER_EVIDENCE"
        or public_key.key_id != item["observer_signer_key_id"]
        or capability["capability_id"] != item["capability_id"]
        or hashlib.sha256(capability_bytes).hexdigest()
        != item["capability_bytes_sha256"]
        or capability["target_tape_namespace_id"]
        != item["target_tape_namespace_id"]
        or capability["context_id"] != item["context_id"]
        or capability["row_binding_id"] != item["row_binding_id"]
        or capability["stream_id"] != item["stream_id"]
        or capability["arm"] != item["arm"]
        or capability["accepted_draw_index"]
        != item["accepted_draw_index"]
    ):
        _fail("worker capability-ref projection changed")
    message = capability_attestation_signing_bytes_v1(
        signer_registry_id=item["signer_registry_id"],
        observer_signer_key_id=public_key.key_id,
        capability_bytes=capability_bytes,
    )
    if not public_authority.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=public_key,
        message=message,
        signature_hex=item["capability_attestation_signature_hex"],
    ):
        _fail("worker capability-ref attestation is invalid")
    expected_ref_id = _hash(
        "capability_ref",
        {key: value for key, value in item.items() if key != "ref_id"},
    )
    if item["ref_id"] != expected_ref_id:
        _fail("worker capability-ref identity changed")
    return item


@dataclass(frozen=True, slots=True)
class V075SourcePriorTransportV1:
    adapter_bytes: bytes = field(repr=False)
    verification_bytes: bytes = field(repr=False)
    adapter_id: str
    verification_id: str

    def __post_init__(self) -> None:
        _cid(self.adapter_id, "source-prior adapter")
        _cid(self.verification_id, "source-prior verification")
        adapter = _strict_load(
            self.adapter_bytes,
            byte_cap=MAX_SOURCE_PRIOR_BYTES,
            field_name="source-prior adapter",
        )
        verification = _strict_load(
            self.verification_bytes,
            byte_cap=MAX_SOURCE_VERIFICATION_BYTES,
            field_name="source-prior verification",
        )
        _validate_source_transport_documents(
            adapter,
            verification,
            adapter_bytes=self.adapter_bytes,
            expected_adapter_id=self.adapter_id,
            expected_verification_id=self.verification_id,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_worker_source_prior_transport.v1",
            "schema_version": SCHEMA_VERSION,
            "adapter_id": self.adapter_id,
            "adapter_bytes_sha256": hashlib.sha256(
                self.adapter_bytes
            ).hexdigest(),
            "adapter_bytes_hex": self.adapter_bytes.hex(),
            "verification_id": self.verification_id,
            "verification_bytes_sha256": hashlib.sha256(
                self.verification_bytes
            ).hexdigest(),
            "verification_bytes_hex": self.verification_bytes.hex(),
            "source_only": True,
            "proposal_only": True,
            "work_reference_only": True,
            "target_fields_present": False,
        }

    @property
    def transport_id(self) -> str:
        return _hash("source_transport", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "transport_id": self.transport_id}


def bind_verified_source_prior_transport_v1(
    *,
    adapter: Any,
    verification: Any,
) -> V075SourcePriorTransportV1:
    adapter_type = f"{type(adapter).__module__}.{type(adapter).__name__}"
    verification_type = (
        f"{type(verification).__module__}.{type(verification).__name__}"
    )
    try:
        adapter_bytes = adapter.canonical_bytes
        verification_document = verification.to_document()
        adapter_id = adapter.adapter_id
        verification_id = verification.verification_id
        catalogue_id = adapter.catalogue.catalogue_id
    except AttributeError as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            "source-prior binder requires exact upstream authority objects"
        ) from error
    if (
        adapter_type != SOURCE_PRIOR_ADAPTER_TYPE
        or verification_type != SOURCE_PRIOR_VERIFICATION_TYPE
        or type(adapter_bytes) is not bytes
        or type(verification_document) is not dict
        or verification.adapter_id != adapter_id
        or verification.recomputed_adapter_id != adapter_id
        or verification.catalogue_id != catalogue_id
        or verification.adapter_bytes_sha256
        != hashlib.sha256(adapter_bytes).hexdigest()
    ):
        _fail("source-prior transport requires one exact verified adapter")
    verification_bytes = canonical_json_bytes(verification_document)
    return V075SourcePriorTransportV1(
        adapter_bytes,
        verification_bytes,
        adapter_id,
        verification_id,
    )


def _validate_source_transport_documents(
    adapter: Any,
    verification: Any,
    *,
    adapter_bytes: bytes,
    expected_adapter_id: str,
    expected_verification_id: str,
) -> None:
    if type(adapter) is not dict or type(verification) is not dict:
        _fail("source-prior transport documents are not mappings")
    forbidden = {
        "result",
        "certificate",
        "cache",
        "observer",
        "kernel",
        "law",
        "reveal",
        "salt",
    }
    if any(
        any(token in key.lower() for token in forbidden)
        for key in _walk_mapping_keys(adapter)
    ):
        _fail("source-prior adapter contains a forbidden dependency")
    if (
        adapter.get("schema") != "acfqp.v075_source_prior_adapter.v1"
        or adapter.get("profile_key") != SOURCE_PRIOR_PROFILE_KEY
        or adapter.get("adapter_id") != expected_adapter_id
        or adapter.get("source_only") is not True
        or adapter.get("proposal_only") is not True
        or adapter.get("may_certify") is not False
        or adapter.get("source_work_reference_only") is not True
        or adapter.get("source_work_embedded") is not False
        or verification.get("schema")
        != "acfqp.v075_source_prior_adapter_verification.v1"
        or verification.get("profile_key") != SOURCE_PRIOR_PROFILE_KEY
        or verification.get("adapter_id") != expected_adapter_id
        or verification.get("recomputed_adapter_id") != expected_adapter_id
        or verification.get("adapter_bytes_sha256")
        != hashlib.sha256(adapter_bytes).hexdigest()
        or verification.get("valid") is not True
        or verification.get("verification_id") != expected_verification_id
    ):
        _fail("source-prior adapter or verification is stale")
    adapter_payload = dict(adapter)
    adapter_payload.pop("catalogue", None)
    claimed_adapter_id = adapter_payload.pop("adapter_id")
    expected_adapter_id_recomputed = hashlib.sha256(
        SOURCE_PRIOR_ADAPTER_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(adapter_payload)
    ).hexdigest()
    verification_payload = dict(verification)
    claimed_verification_id = verification_payload.pop("verification_id")
    expected_verification_id_recomputed = hashlib.sha256(
        SOURCE_PRIOR_VERIFICATION_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(verification_payload)
    ).hexdigest()
    if (
        claimed_adapter_id != expected_adapter_id_recomputed
        or claimed_verification_id != expected_verification_id_recomputed
    ):
        _fail("source-prior content identity changed")


def _walk_mapping_keys(value: Any) -> tuple[str, ...]:
    if type(value) is dict:
        return tuple(value) + tuple(
            key
            for child in value.values()
            for key in _walk_mapping_keys(child)
        )
    if type(value) is list:
        return tuple(
            key for child in value for key in _walk_mapping_keys(child)
        )
    return ()


def _source_transport_from_document(
    document: Any,
) -> V075SourcePriorTransportV1:
    item = _strict_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "adapter_id",
            "adapter_bytes_sha256",
            "adapter_bytes_hex",
            "verification_id",
            "verification_bytes_sha256",
            "verification_bytes_hex",
            "source_only",
            "proposal_only",
            "work_reference_only",
            "target_fields_present",
            "transport_id",
        },
        field_name="source-prior transport",
    )
    if (
        item["schema"] != "acfqp.v075_worker_source_prior_transport.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["source_only"] is not True
        or item["proposal_only"] is not True
        or item["work_reference_only"] is not True
        or item["target_fields_present"] is not False
    ):
        _fail("source-prior transport contract changed")
    try:
        adapter_bytes = bytes.fromhex(item["adapter_bytes_hex"])
        verification_bytes = bytes.fromhex(item["verification_bytes_hex"])
    except (TypeError, ValueError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            "source-prior transport bytes are not hexadecimal"
        ) from error
    result = V075SourcePriorTransportV1(
        adapter_bytes,
        verification_bytes,
        item["adapter_id"],
        item["verification_id"],
    )
    if (
        item["adapter_bytes_sha256"]
        != hashlib.sha256(adapter_bytes).hexdigest()
        or item["verification_bytes_sha256"]
        != hashlib.sha256(verification_bytes).hexdigest()
        or item["transport_id"] != result.transport_id
    ):
        _fail("source-prior transport identity changed")
    return result


def _total_lift_ref_from_document(
    document: Any,
) -> V075TotalLiftAuthorityRefV1:
    item = _strict_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "authority_id",
            "independent_verification_id",
            "canonical_artifact_sha256",
            "semantic_profile",
            "environment_failure_preserved",
            "unmodeled_reachable_child",
            "policy_abort_continuation_reward",
            "complete_disjoint_exhaustive_partition_required",
            "authority_status",
            "production_authorizing",
            "ref_id",
        },
        field_name="total-lift authority ref",
    )
    result = V075TotalLiftAuthorityRefV1(
        item["authority_id"],
        item["independent_verification_id"],
        item["canonical_artifact_sha256"],
        item["authority_status"],
    )
    if (
        item["schema"]
        != "acfqp.v075_worker_total_lift_authority_ref.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["semantic_profile"]
        != result.to_document()["semantic_profile"]
        or item["environment_failure_preserved"] is not True
        or item["unmodeled_reachable_child"]
        != "ABSORBING_POLICY_ABORT_FAILURE"
        or item["policy_abort_continuation_reward"] != Fraction(0)
        or item["complete_disjoint_exhaustive_partition_required"] is not True
        or item["production_authorizing"] is not False
        or item["ref_id"] != result.ref_id
    ):
        _fail("total-lift authority ref changed")
    return result


@dataclass(frozen=True, slots=True)
class V075RegisteredOccurrenceWorkerRequestV1:
    registry: V075ProductionWorkerRegistryDraftV1
    arm: V075WorkerArmV1
    scientific_ordinal: int
    target_tape_namespace_id: str
    context_id: str
    capability_refs: tuple[V075WorkerObservationCapabilityRefV1, ...]
    threshold_profile: V075WorkerThresholdProfileV1
    cap_profile: V075WorkerCapProfileV1
    total_lift_authority: V075TotalLiftAuthorityRefV1
    source_prior_transport: V075SourcePriorTransportV1 | None
    _occurrence_id: str = field(init=False, repr=False)
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.registry) is not V075ProductionWorkerRegistryDraftV1
            or self.registry != freeze_v075_worker_registry_draft_v1()
            or type(self.arm) is not V075WorkerArmV1
            or type(self.scientific_ordinal) is not int
            or self.scientific_ordinal < 0
            or type(self.capability_refs) is not tuple
            or not self.capability_refs
            or len(self.capability_refs) > MAX_CAPABILITIES_PER_REQUEST
            or any(
                type(item) is not V075WorkerObservationCapabilityRefV1
                for item in self.capability_refs
            )
            or type(self.threshold_profile)
            is not V075WorkerThresholdProfileV1
            or type(self.cap_profile) is not V075WorkerCapProfileV1
            or type(self.total_lift_authority)
            is not V075TotalLiftAuthorityRefV1
        ):
            _fail("worker request graph is malformed")
        _cid(self.target_tape_namespace_id, "worker target namespace")
        _cid(self.context_id, "worker context")
        registration = self.registry.require_arm(self.arm)
        if (
            (self.source_prior_transport is not None)
            != registration.source_prior_required
            or (
                self.source_prior_transport is not None
                and type(self.source_prior_transport)
                is not V075SourcePriorTransportV1
            )
        ):
            _fail("source-prior payload escaped or is missing from SOURCE")
        identities = {
            (
                item.target_tape_namespace_id,
                item.context_id,
                item.arm,
            )
            for item in self.capability_refs
        }
        if identities != {
            (
                self.target_tape_namespace_id,
                self.context_id,
                self.arm,
            )
        }:
            _fail("worker capabilities are transplanted across occurrence")
        ref_ids = tuple(item.ref_id for item in self.capability_refs)
        if len(set(ref_ids)) != len(ref_ids):
            _fail("worker capability refs contain duplicates")
        stream_groups: dict[str, list[int]] = {}
        for item in self.capability_refs:
            stream_groups.setdefault(item.stream_id, []).append(
                item.accepted_draw_index
            )
        if any(
            values != list(range(1, len(values) + 1))
            for values in stream_groups.values()
        ):
            _fail("worker capability prefixes are reordered, gapped, or reset")
        occurrence_payload = {
            "schema": "acfqp.v075_law_free_worker_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "worker_registry_id": self.registry.registry_id,
            "scientific_ordinal": self.scientific_ordinal,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "row_binding_ids": sorted(
                {item.row_binding_id for item in self.capability_refs}
            ),
            "stream_ids": sorted(stream_groups),
            "law_serialized": False,
        }
        object.__setattr__(
            self,
            "_occurrence_id",
            _hash("occurrence", occurrence_payload),
        )
        object.__setattr__(
            self,
            "_request_id",
            _hash("request", self._payload()),
        )

    @property
    def registration(self) -> V075WorkerArmRegistrationV1:
        return self.registry.require_arm(self.arm)

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id

    @property
    def request_id(self) -> str:
        return self._request_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_registered_occurrence_worker_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_scope": "CONSTRUCTION_ONLY",
            "worker_registry_id": self.registry.registry_id,
            "arm_registration_id": self.registration.registration_id,
            "scientific_ordinal": self.scientific_ordinal,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "route": self.registration.route.value,
            "proposal_semantics": (
                self.registration.proposal_semantics.value
            ),
            "capability_ref_ids": [
                item.ref_id for item in self.capability_refs
            ],
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "cap_profile_id": self.cap_profile.cap_profile_id,
            "total_lift_authority_ref_id": (
                self.total_lift_authority.ref_id
            ),
            "source_prior_transport_id": (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.transport_id
            ),
            "no_target_persistence": True,
            "scientific_backend_ready": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "registry": self.registry.to_document(),
            "capability_refs": [
                item.to_document() for item in self.capability_refs
            ],
            "threshold_profile": self.threshold_profile.to_document(),
            "cap_profile": self.cap_profile.to_document(),
            "total_lift_authority": (
                self.total_lift_authority.to_document()
            ),
            "source_prior_transport": (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.to_document()
            ),
            "request_id": self.request_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        result = canonical_json_bytes(self.to_document())
        if len(result) > MAX_REQUEST_BYTES:
            _fail("worker request exceeds canonical byte cap")
        return result


_REQUEST_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "execution_scope",
    "worker_registry_id",
    "arm_registration_id",
    "scientific_ordinal",
    "occurrence_id",
    "target_tape_namespace_id",
    "context_id",
    "arm",
    "route",
    "proposal_semantics",
    "capability_ref_ids",
    "threshold_profile_id",
    "cap_profile_id",
    "total_lift_authority_ref_id",
    "source_prior_transport_id",
    "no_target_persistence",
    "scientific_backend_ready",
    "registry",
    "capability_refs",
    "threshold_profile",
    "cap_profile",
    "total_lift_authority",
    "source_prior_transport",
    "request_id",
}


def load_v075_registered_occurrence_worker_request_v1(
    raw: bytes,
) -> dict[str, Any]:
    """Strictly reconstruct one construction request from canonical bytes."""

    item = _strict_mapping(
        _strict_load(raw, byte_cap=MAX_REQUEST_BYTES, field_name="worker request"),
        keys=_REQUEST_KEYS,
        field_name="worker request",
    )
    registry = freeze_v075_worker_registry_draft_v1()
    if (
        item["schema"]
        != "acfqp.v075_registered_occurrence_worker_request.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["execution_scope"] != "CONSTRUCTION_ONLY"
        or item["worker_registry_id"] != registry.registry_id
        or item["registry"] != registry.to_document()
        or item["no_target_persistence"] is not True
        or item["scientific_backend_ready"] is not False
    ):
        _fail("worker request contract or registry changed")
    try:
        arm = V075WorkerArmV1(item["arm"])
    except (TypeError, ValueError) as error:
        raise V075RegisteredOccurrenceWorkerInvariantViolation(
            "worker request arm is not registered"
        ) from error
    registration = registry.require_arm(arm)
    if (
        item["arm_registration_id"] != registration.registration_id
        or item["route"] != registration.route.value
        or item["proposal_semantics"]
        != registration.proposal_semantics.value
        or type(item["scientific_ordinal"]) is not int
        or item["scientific_ordinal"] < 0
    ):
        _fail("worker request route semantics changed")
    _cid(item["occurrence_id"], "worker request occurrence")
    _cid(item["target_tape_namespace_id"], "worker request namespace")
    _cid(item["context_id"], "worker request context")
    if (
        type(item["capability_refs"]) is not list
        or not item["capability_refs"]
        or len(item["capability_refs"]) > MAX_CAPABILITIES_PER_REQUEST
    ):
        _fail("worker request capability refs are empty or over cap")
    capability_refs: list[dict[str, Any]] = []
    registry_ids: set[str] = set()
    for document in item["capability_refs"]:
        loaded = _capability_ref_from_document(
            document,
            expected_signer_registry_id=None,
        )
        registry_ids.add(loaded["signer_registry_id"])
        capability_refs.append(loaded)
    if len(registry_ids) != 1:
        _fail("worker capabilities use different signer registries")
    if item["capability_ref_ids"] != [
        value["ref_id"] for value in capability_refs
    ]:
        _fail("worker capability-ref order or identity changed")
    if {
        (
            value["target_tape_namespace_id"],
            value["context_id"],
            value["arm"],
        )
        for value in capability_refs
    } != {
        (
            item["target_tape_namespace_id"],
            item["context_id"],
            arm.value,
        )
    }:
        _fail("worker capabilities escaped their occurrence")
    stream_groups: dict[str, list[int]] = {}
    for value in capability_refs:
        stream_groups.setdefault(value["stream_id"], []).append(
            value["accepted_draw_index"]
        )
    if any(
        values != list(range(1, len(values) + 1))
        for values in stream_groups.values()
    ):
        _fail("worker capability streams are reordered, gapped, or reset")
    threshold = V075WorkerThresholdProfileV1()
    caps = V075WorkerCapProfileV1()
    if (
        canonical_json_bytes(item["threshold_profile"])
        != canonical_json_bytes(threshold.to_document())
        or item["threshold_profile_id"] != threshold.threshold_profile_id
        or canonical_json_bytes(item["cap_profile"])
        != canonical_json_bytes(caps.to_document())
        or item["cap_profile_id"] != caps.cap_profile_id
    ):
        _fail("worker thresholds or caps changed")
    total_lift = _total_lift_ref_from_document(
        item["total_lift_authority"]
    )
    if item["total_lift_authority_ref_id"] != total_lift.ref_id:
        _fail("worker total-lift authority identity changed")
    source_transport: V075SourcePriorTransportV1 | None
    if item["source_prior_transport"] is None:
        source_transport = None
    else:
        source_transport = _source_transport_from_document(
            item["source_prior_transport"]
        )
    if (
        (source_transport is not None) != registration.source_prior_required
        or item["source_prior_transport_id"]
        != (
            None
            if source_transport is None
            else source_transport.transport_id
        )
    ):
        _fail("worker source-prior arm boundary changed")
    occurrence_payload = {
        "schema": "acfqp.v075_law_free_worker_occurrence.v1",
        "schema_version": SCHEMA_VERSION,
        "worker_registry_id": registry.registry_id,
        "scientific_ordinal": item["scientific_ordinal"],
        "target_tape_namespace_id": item["target_tape_namespace_id"],
        "context_id": item["context_id"],
        "arm": arm.value,
        "row_binding_ids": sorted(
            {value["row_binding_id"] for value in capability_refs}
        ),
        "stream_ids": sorted(stream_groups),
        "law_serialized": False,
    }
    if item["occurrence_id"] != _hash("occurrence", occurrence_payload):
        _fail("worker occurrence identity changed")
    expected_request_id = _hash(
        "request",
        {
            key: value
            for key, value in item.items()
            if key
            not in {
                "registry",
                "capability_refs",
                "threshold_profile",
                "cap_profile",
                "total_lift_authority",
                "source_prior_transport",
                "request_id",
            }
        },
    )
    if item["request_id"] != expected_request_id:
        _fail("worker request identity changed")
    return item


REGISTERED_COUNTER_PATHS = (
    "common.request_reconstructions",
    "common.request_bytes_read",
    "common.capability_attestation_verifications",
    "common.capability_records",
    "common.total_lift_authority_bindings",
    "source_prior.adapter_reads",
    "source_prior.read_bytes",
    "adaptive.route_dispatches",
    "adaptive.observation_capabilities",
    "adaptive.proposal_dispatches",
    "adaptive.source_proposal_dispatches",
    "adaptive.no_prior_dispatches",
    "adaptive.wrong_prior_dispatches",
    "adaptive.ood_abstention_dispatches",
    "adaptive.model_builds",
    "adaptive.planner_invocations",
    "adaptive.total_lift_evaluations",
    "direct.route_dispatches",
    "direct.observation_capabilities",
    "direct.ground_planner_invocations",
    "direct.total_lift_evaluations",
    "integrity.no_persistence_checks",
)


@dataclass(frozen=True, slots=True)
class V075WorkerCounterV1:
    path: str
    value: int
    observed: bool = True

    def __post_init__(self) -> None:
        if (
            self.path not in REGISTERED_COUNTER_PATHS
            or type(self.value) is not int
            or self.value < 0
            or self.observed is not True
        ):
            _fail("worker counter is unknown, negative, or not observed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_registered_worker_counter.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "value": self.value,
            "observed": True,
            "lane": "OPERATIONAL_CONSTRUCTION",
        }

    @property
    def counter_id(self) -> str:
        return _hash("counter", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_id": self.counter_id}


@dataclass(frozen=True, slots=True)
class V075WorkerWorkV1:
    request_id: str
    arm: V075WorkerArmV1
    counters: tuple[V075WorkerCounterV1, ...]

    def __post_init__(self) -> None:
        _cid(self.request_id, "worker work request")
        if (
            type(self.arm) is not V075WorkerArmV1
            or type(self.counters) is not tuple
            or tuple(item.path for item in self.counters)
            != REGISTERED_COUNTER_PATHS
            or any(type(item) is not V075WorkerCounterV1 for item in self.counters)
        ):
            _fail("worker work vector is incomplete or reordered")
        values = {item.path: item.value for item in self.counters}
        adaptive = self.arm is not V075WorkerArmV1.MATCHED_DIRECT_GROUND
        source = self.arm is V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        adaptive_semantic_dispatches = (
            values["adaptive.source_proposal_dispatches"],
            values["adaptive.no_prior_dispatches"],
            values["adaptive.wrong_prior_dispatches"],
            values["adaptive.ood_abstention_dispatches"],
        )
        expected_semantic_dispatches = tuple(
            int(self.arm is candidate)
            for candidate in tuple(V075WorkerArmV1)[:4]
        )
        if (
            values["source_prior.adapter_reads"] != int(source)
            or (not source and values["source_prior.read_bytes"] != 0)
            or values["adaptive.route_dispatches"] != int(adaptive)
            or values["direct.route_dispatches"] != int(not adaptive)
            or values["adaptive.proposal_dispatches"] != int(adaptive)
            or adaptive_semantic_dispatches
            != expected_semantic_dispatches
            or (
                adaptive
                and (
                    values["direct.observation_capabilities"] != 0
                    or values["direct.ground_planner_invocations"] != 0
                    or values["direct.total_lift_evaluations"] != 0
                )
            )
            or (
                not adaptive
                and (
                    values["adaptive.observation_capabilities"] != 0
                    or values["adaptive.proposal_dispatches"] != 0
                    or values["adaptive.model_builds"] != 0
                    or values["adaptive.planner_invocations"] != 0
                    or values["adaptive.total_lift_evaluations"] != 0
                )
            )
        ):
            _fail("worker route-native accounting is mixed across arms")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_registered_worker_work.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "arm": self.arm.value,
            "counter_ids": [item.counter_id for item in self.counters],
            "required_counter_paths": list(REGISTERED_COUNTER_PATHS),
            "complete_native_zeros": True,
            "route_native_lanes_disjoint": True,
        }

    @property
    def work_id(self) -> str:
        return _hash("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": [item.to_document() for item in self.counters],
            "work_id": self.work_id,
        }


@dataclass(frozen=True, slots=True)
class V075RegisteredOccurrenceWorkerResultV1:
    request_id: str
    occurrence_id: str
    arm: V075WorkerArmV1
    route: V075WorkerRouteV1
    capability_ref_ids: tuple[str, ...]
    source_prior_transport_id: str | None
    total_lift_authority_ref_id: str
    work: V075WorkerWorkV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.request_id, "worker result request")
        _cid(self.occurrence_id, "worker result occurrence")
        _cid(
            self.total_lift_authority_ref_id,
            "worker result total-lift authority",
        )
        if (
            type(self.arm) is not V075WorkerArmV1
            or type(self.route) is not V075WorkerRouteV1
            or type(self.capability_ref_ids) is not tuple
            or not self.capability_ref_ids
            or len(set(self.capability_ref_ids))
            != len(self.capability_ref_ids)
            or type(self.work) is not V075WorkerWorkV1
            or self.work.request_id != self.request_id
            or self.work.arm is not self.arm
            or (
                self.source_prior_transport_id is not None
            )
            != (self.arm is V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR)
            or (
                self.route is V075WorkerRouteV1.MATCHED_DIRECT_GROUND
            )
            != (self.arm is V075WorkerArmV1.MATCHED_DIRECT_GROUND)
        ):
            _fail("worker result graph is malformed")
        for item in self.capability_ref_ids:
            _cid(item, "worker result capability ref")
        if self.source_prior_transport_id is not None:
            _cid(
                self.source_prior_transport_id,
                "worker result source-prior transport",
            )
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_registered_occurrence_worker_result.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_scope": "CONSTRUCTION_ONLY",
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "route": self.route.value,
            "capability_ref_ids": list(self.capability_ref_ids),
            "source_prior_transport_id": self.source_prior_transport_id,
            "total_lift_authority_ref_id": (
                self.total_lift_authority_ref_id
            ),
            "status": "BACKEND_NOT_READY_NONCERTIFICATE",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": "PRODUCTION_BACKEND_NOT_READY",
            "work_id": self.work.work_id,
            "scientific_result": False,
            "target_accessed": False,
            "plan_certificate_id": None,
            "exact_evaluation_id": None,
            "v072_target_authority_used": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        result = canonical_json_bytes(self.to_document())
        if len(result) > MAX_RESULT_BYTES:
            _fail("worker result exceeds canonical byte cap")
        return result


def _fixture_work(
    request: Mapping[str, Any],
    *,
    request_bytes: bytes,
) -> V075WorkerWorkV1:
    arm = V075WorkerArmV1(request["arm"])
    adaptive = arm is not V075WorkerArmV1.MATCHED_DIRECT_GROUND
    source = request["source_prior_transport"]
    capability_count = len(request["capability_refs"])
    values = {
        "common.request_reconstructions": 1,
        "common.request_bytes_read": len(request_bytes),
        "common.capability_attestation_verifications": capability_count,
        "common.capability_records": capability_count,
        "common.total_lift_authority_bindings": 1,
        "source_prior.adapter_reads": int(source is not None),
        "source_prior.read_bytes": (
            0
            if source is None
            else (
                len(bytes.fromhex(source["adapter_bytes_hex"]))
                + len(bytes.fromhex(source["verification_bytes_hex"]))
            )
        ),
        "adaptive.route_dispatches": int(adaptive),
        "adaptive.observation_capabilities": (
            capability_count if adaptive else 0
        ),
        "adaptive.proposal_dispatches": int(adaptive),
        "adaptive.source_proposal_dispatches": int(
            arm is V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        ),
        "adaptive.no_prior_dispatches": int(
            arm is V075WorkerArmV1.NO_PRIOR
        ),
        "adaptive.wrong_prior_dispatches": int(
            arm is V075WorkerArmV1.WRONG_CONSENSUS_PRIOR
        ),
        "adaptive.ood_abstention_dispatches": int(
            arm is V075WorkerArmV1.OOD_ABSTENTION
        ),
        "adaptive.model_builds": 0,
        "adaptive.planner_invocations": 0,
        "adaptive.total_lift_evaluations": 0,
        "direct.route_dispatches": int(not adaptive),
        "direct.observation_capabilities": (
            capability_count if not adaptive else 0
        ),
        "direct.ground_planner_invocations": 0,
        "direct.total_lift_evaluations": 0,
        "integrity.no_persistence_checks": 1,
    }
    # Touching the length ensures construction accounting is tied to the exact
    # bytes consumed without adding a caller-controlled aggregate counter.
    if len(request_bytes) <= 0:  # pragma: no cover
        _fail("fixture request bytes unexpectedly empty")
    return V075WorkerWorkV1(
        request["request_id"],
        arm,
        tuple(
            V075WorkerCounterV1(path, values[path])
            for path in REGISTERED_COUNTER_PATHS
        ),
    )


def execute_construction_fixture_occurrence_worker_v1(
    request_bytes: bytes,
) -> bytes:
    """Reconstruct and route one request without opening a scientific backend."""

    request = load_v075_registered_occurrence_worker_request_v1(request_bytes)
    arm = V075WorkerArmV1(request["arm"])
    route = V075WorkerRouteV1(request["route"])
    result = V075RegisteredOccurrenceWorkerResultV1(
        request["request_id"],
        request["occurrence_id"],
        arm,
        route,
        tuple(request["capability_ref_ids"]),
        request["source_prior_transport_id"],
        request["total_lift_authority_ref_id"],
        _fixture_work(request, request_bytes=request_bytes),
    )
    return result.canonical_bytes


def verify_construction_fixture_occurrence_result_v1(
    *,
    request_bytes: bytes,
    result_bytes: bytes,
) -> V075RegisteredOccurrenceWorkerResultV1:
    """Verify by deterministic reconstruction, never by claimed result fields."""

    expected = execute_construction_fixture_occurrence_worker_v1(
        request_bytes
    )
    if type(result_bytes) is not bytes or result_bytes != expected:
        _fail("worker result differs from deterministic reconstruction")
    request = load_v075_registered_occurrence_worker_request_v1(request_bytes)
    work = _fixture_work(request, request_bytes=request_bytes)
    return V075RegisteredOccurrenceWorkerResultV1(
        request["request_id"],
        request["occurrence_id"],
        V075WorkerArmV1(request["arm"]),
        V075WorkerRouteV1(request["route"]),
        tuple(request["capability_ref_ids"]),
        request["source_prior_transport_id"],
        request["total_lift_authority_ref_id"],
        work,
    )


def execute_production_occurrence_worker_v1(
    request_bytes: bytes,
) -> bytes:
    """Fail before execution while every route-native backend is unbound."""

    load_v075_registered_occurrence_worker_request_v1(request_bytes)
    raise V075RegisteredOccurrenceWorkerNotReady(
        PRODUCTION_EXECUTION_STATUS
    )


__all__ = [
    "CAPABILITY_ATTESTATION_DOMAIN",
    "CONSTRUCTION_FIXTURE_ONLY",
    "DOMAIN_TAGS",
    "MAX_REQUEST_BYTES",
    "MAX_RESULT_BYTES",
    "PROFILE_KEY",
    "PRODUCTION_EXECUTION_STATUS",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_COUNTER_PATHS",
    "SCHEMA_VERSION",
    "V075ProductionWorkerRegistryDraftV1",
    "V075RegisteredOccurrenceWorkerInvariantViolation",
    "V075RegisteredOccurrenceWorkerNotReady",
    "V075RegisteredOccurrenceWorkerRequestV1",
    "V075RegisteredOccurrenceWorkerResultV1",
    "V075SourcePriorTransportV1",
    "V075TotalLiftAuthorityRefV1",
    "V075WorkerArmRegistrationV1",
    "V075WorkerArmV1",
    "V075WorkerBackendStatusV1",
    "V075WorkerCapProfileV1",
    "V075WorkerCounterV1",
    "V075WorkerObservationCapabilityRefV1",
    "V075WorkerProposalSemanticsV1",
    "V075WorkerRouteV1",
    "V075WorkerThresholdProfileV1",
    "V075WorkerWorkV1",
    "bind_verified_source_prior_transport_v1",
    "capability_attestation_signing_bytes_v1",
    "construction_total_lift_authority_ref_v1",
    "execute_construction_fixture_occurrence_worker_v1",
    "execute_production_occurrence_worker_v1",
    "freeze_v075_worker_registry_draft_v1",
    "load_v075_registered_occurrence_worker_request_v1",
    "verify_construction_fixture_occurrence_result_v1",
]
