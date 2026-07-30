"""Pretarget five-arm acquisition authority for the V0-075 V2 namespace.

This module freezes only public, static acquisition intent.  It does not own
an observer, transition kernel, target tape, private law, reveal, callback, or
execution surface.  In particular:

* the five arms and their order are rebound to the exact V2 namespace;
* SOURCE proposals are rederived from the complete tracked source authority;
* all non-SOURCE proposals are source-transport-free controls;
* every adaptive root row is frozen as discovery -> support promotion ->
  validation; and
* the matched direct arm freezes discovery -> support promotion plus the
  registered future child-expansion and checkpoint rules without inventing
  any child state.

All public factories are deterministic.  The byte verifier reconstructs the
occurrence from its canonical bytes, independently replays any required
tracked SOURCE graph, rebuilds the complete expected artifact, and accepts
only exact canonical-byte equality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.47.0"
PROFILE_KEY = "v075_five_arm_acquisition_authority_v2"
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_OCCURRENCE_IDENTITY_BYTES = 64 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PRODUCTION_AUTHORIZING = False
OBSERVER_OPEN_ALLOWED = False
TARGET_ACCESS_ALLOWED = False

SUPPORT_SELECTION_RULE = "ALL_DISTINCT_SIGNED_DISCOVERY_SUPPORT"
SUPPORT_PROMOTION_RULE = (
    "PROMOTE_ALL_DISTINCT_SIGNED_DISCOVERY_OUTCOMES_IN_CANONICAL_ORDER"
)
MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND = 1
ADAPTIVE_ROUND_SELECTION_RULE = (
    "AT_MOST_ONE_REGISTERED_FRONTIER_ROW_PER_ADAPTIVE_ROUND"
)
DIRECT_CHILD_EXPANSION_RULE = (
    "AFTER_COMPLETE_ROOT_SUPPORT_PROMOTION_EXPAND_EVERY_DISTINCT_"
    "NONFAILURE_NONTERMINAL_CHILD_WITH_ITS_COMPLETE_LEGAL_ACTION_CATALOGUE"
)
DIRECT_CHECKPOINT_RULE = (
    "VALIDATE_EVERY_FROZEN_ROOT_AND_DISCOVERED_CHILD_ROW_AT_EACH_"
    "REGISTERED_CUMULATIVE_PREFIX_CHECKPOINT"
)
PROPOSAL_USE_RULES = {
    worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR: (
        "REGISTERED_TRACKED_FORWARD_MIDRANK_INPUT_FOR_FUTURE_"
        "ADAPTIVE_FRONTIER_RANKING"
    ),
    worker.V075WorkerArmV1.NO_PRIOR: (
        "REGISTERED_NEUTRAL_INPUT_FOR_FUTURE_ADAPTIVE_FRONTIER_RANKING"
    ),
    worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR: (
        "REGISTERED_FIXED_REVERSED_MIDRANK_INPUT_FOR_FUTURE_"
        "ADAPTIVE_FRONTIER_RANKING"
    ),
    worker.V075WorkerArmV1.OOD_ABSTENTION: (
        "REGISTERED_INCOMPATIBLE_SCHEMA_ABSTENTION_INPUT_FOR_FUTURE_"
        "NEUTRAL_FRONTIER_RANKING"
    ),
    worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND: (
        "DIRECT_GROUND_ROUTE_HAS_NO_PROPOSAL"
    ),
}

SOURCE_FEATURE_SCHEMA_ID = (
    "6c5867ab74182b98faf776ec6a544799c745b5bf6c7cd9943733da5fe96951de"
)
SOURCE_ARCHIVE_ID = (
    "4b25945b07d94ace9a6af8cbf979a9133e3780b6306c0bc3b7d8055b2c25bf92"
)
SOURCE_ARCHIVE_VERIFICATION_ID = (
    "e23c98ce70ebee04dd6dcccd29149a16c90b48ef5e62b5e006a524c58818157c"
)
SOURCE_TRANSPORT_ID = (
    "5c115853cb45c0362c29f3ad92e0925e01f79e5074790c13f9a0e5f0373f99f0"
)
SOURCE_TRANSPORT_BYTES_SHA256 = (
    "342cb34dae0236a60ab20827a3919ca975dbea77cc2abe2ac60a70ac2e0d7cc5"
)
SOURCE_ADAPTER_ID = (
    "41a204b8b0a0c28d7b5c10417644635860e741544eef63e20f93d60e5f522e4e"
)
SOURCE_VERIFICATION_ID = (
    "69626f89a3ace9e8312242d820cc71582721eb5165ef60acb1de20586980dbf9"
)
SOURCE_CATALOGUE_ID = (
    "4886417564f392bc8ca00fcb1e671e17171eeb916bac9f1d06c486e94059f8ec"
)
OOD_INCOMPATIBLE_FEATURE_SCHEMA_ID = hashlib.sha256(
    b"acfqp:v075-five-arm-acquisition:registered-ood-schema:v2"
).hexdigest()

# The WRONG control is a preregistered V2 constant.  Its construction path
# never imports or opens the tracked source transport.  These source-coordinate
# keys and their control values are mathematical constants copied into the V2
# contract; the values are the exact 1-q reversal of the registered forward
# midranks.
REGISTERED_FORWARD_MIDRANKS = (
    (
        "9fe53537e8657540c657163cb437e1b3885a06a558ca27f0b92cb9d57135e28a",
        Fraction(1, 6),
    ),
    (
        "7045f3287922411f0648501de97cc6c00ff6dad38fcd11ecf525e0a869e72a6a",
        Fraction(19, 36),
    ),
    (
        "19ae3b19be43564c7781aab562d7e6261848f4b00e30cc7a65360a44056faadc",
        Fraction(1),
    ),
)
REGISTERED_FORWARD_KEYS = tuple(
    key for key, _value in REGISTERED_FORWARD_MIDRANKS
)
REGISTERED_WRONG_REVERSED_MIDRANKS = tuple(
    sorted((key, 1 - value) for key, value in REGISTERED_FORWARD_MIDRANKS)
)
WRONG_FIXED_CONTROL_ID = hashlib.sha256(
    b"acfqp:v075-five-arm-fixed-reversed-midrank-control:v2"
    + b"\x00"
    + canonical_json_bytes(
        [
            {
                "feature_key": key,
                "reversed_mean_midrank": {
                    "numerator": value.numerator,
                    "denominator": value.denominator,
                },
            }
            for key, value in REGISTERED_WRONG_REVERSED_MIDRANKS
        ]
    )
).hexdigest()

ARM_ORDER = tuple(
    worker.V075WorkerArmV1(value) for value in public.ARM_ORDER
)
ADAPTIVE_ARM_ORDER = ARM_ORDER[:-1]
DIRECT_ARM = worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND

DOMAIN_TAGS = {
    "arm_registration": (
        "acfqp:v075-five-arm-acquisition-arm-registration:v2"
    ),
    "profile": "acfqp:v075-five-arm-acquisition-profile:v2",
    "occurrence_slot": "acfqp:v075-five-arm-occurrence-slot:v2",
    "source_provenance": (
        "acfqp:v075-five-arm-tracked-source-provenance:v2"
    ),
    "proposal_view": "acfqp:v075-five-arm-proposal-view:v2",
    "initial_intent": "acfqp:v075-five-arm-initial-row-intent:v2",
    "initial_schedule": (
        "acfqp:v075-five-arm-initial-acquisition-schedule:v2"
    ),
    "verification": (
        "acfqp:v075-five-arm-initial-acquisition-verification:v2"
    ),
}

if (
    ARM_ORDER != tuple(worker.V075WorkerArmV1)
    or len(ARM_ORDER) != 5
    or len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
):
    raise RuntimeError("V0-075 five-arm V2 static registry drifted")


class V075FiveArmAcquisitionAuthorityV2InvariantViolation(ValueError):
    """A namespace, arm, proposal, schedule, cap, or replay was invalid."""


def _fail(message: str) -> None:
    raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("five-arm acquisition arithmetic must use exact Fraction")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _fraction(value: Any, field_name: str) -> Fraction:
    if type(value) is Fraction:
        return value
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{field_name} is not one reduced rational")
    result = Fraction(value["numerator"], value["denominator"])
    if _fdoc(result) != value:
        _fail(f"{field_name} is not reduced")
    return result


def _zero_access_payload() -> dict[str, Any]:
    return {
        "observer_calls": 0,
        "kernel_calls": 0,
        "target_access_count": 0,
        "target_accessed": False,
        "private_material_serialized": False,
        "official_execution_allowed": False,
        "scientific_endpoint_credit_allowed": False,
        "production_authorizing": False,
    }


def _strict_load(
    raw: bytes,
    *,
    cap: int,
    field_name: str,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > cap:
        _fail(f"{field_name} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            f"{field_name} is not strict canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
    ):
        _fail(f"{field_name} is not one canonical object")
    return document


def _replay_namespace(
    claimed: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> namespace_v2.V075PublicTargetTapeNamespaceV2:
    if type(claimed) is not namespace_v2.V075PublicTargetTapeNamespaceV2:
        _fail("five-arm authority requires one exact V2 namespace")
    try:
        replayed = namespace_v2.V075PublicTargetTapeNamespaceV2(
            namespace_v2._NAMESPACE_ISSUER,  # type: ignore[attr-defined]
            claimed.anchor,
            claimed.workload,
            claimed.family,
            claimed.runner_profile,
            claimed.environment_commitment,
            claimed.signer_registry,
        )
        if (
            replayed.target_tape_namespace_id
            != claimed.target_tape_namespace_id
            or replayed.canonical_bytes != claimed.canonical_bytes
        ):
            _fail("V2 namespace differs from semantic replay")
    except (
        AttributeError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        if type(error) is V075FiveArmAcquisitionAuthorityV2InvariantViolation:
            raise
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "V2 namespace semantic replay failed"
        ) from error
    return replayed


def _context_by_id(
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    context_id: str,
) -> public.V075PublicReplicateContextV1:
    matches = tuple(
        item
        for item in namespace.family.replicate_contexts
        if item.context_id == context_id
    )
    if len(matches) != 1:
        _fail("occurrence context is outside the exact V2 workload")
    return matches[0]


def _load_tracked_source_transport(
    repository_root: str | Path,
) -> worker.V075SourcePriorTransportV1:
    # Lazy import is deliberate: non-SOURCE arms must not even enter the
    # tracked-source transport path.
    try:
        from acfqp import v075_production_occurrence_plan_v1 as plan

        transport = plan.load_tracked_v075_source_prior_transport_v1(
            repository_root
        )
    except Exception as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "complete tracked SOURCE authority replay failed"
        ) from error
    if type(transport) is not worker.V075SourcePriorTransportV1:
        _fail("tracked SOURCE replay returned a partial transport")
    return transport


def _transport_bytes(
    transport: worker.V075SourcePriorTransportV1,
) -> bytes:
    return canonical_json_bytes(transport.to_document())


def _replay_source_transport(
    claimed: worker.V075SourcePriorTransportV1,
) -> worker.V075SourcePriorTransportV1:
    if type(claimed) is not worker.V075SourcePriorTransportV1:
        _fail("SOURCE provenance requires one exact typed transport")
    try:
        replayed = worker.V075SourcePriorTransportV1(
            claimed.adapter_bytes,
            claimed.verification_bytes,
            claimed.adapter_id,
            claimed.verification_id,
        )
        if (
            replayed.transport_id != claimed.transport_id
            or _transport_bytes(replayed) != _transport_bytes(claimed)
        ):
            _fail("SOURCE transport differs from exact semantic replay")
    except (
        AttributeError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        if type(error) is V075FiveArmAcquisitionAuthorityV2InvariantViolation:
            raise
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "SOURCE transport semantic replay failed"
        ) from error
    return replayed


def _proposal_use_rule(arm: worker.V075WorkerArmV1) -> str:
    if type(arm) is not worker.V075WorkerArmV1:
        _fail("proposal-use lookup requires one typed arm")
    return PROPOSAL_USE_RULES[arm]


class V075AcquisitionRouteV2(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class V075ProposalDispositionV2(str, Enum):
    SOURCE_FORWARD_MIDRANK = "SOURCE_FORWARD_MIDRANK"
    NO_PRIOR_NEUTRAL = "NO_PRIOR_NEUTRAL"
    WRONG_FIXED_REVERSED_MIDRANK = "WRONG_FIXED_REVERSED_MIDRANK"
    OOD_INCOMPATIBLE_SCHEMA_ABSTENTION = (
        "OOD_INCOMPATIBLE_SCHEMA_EXPLICIT_ABSTENTION"
    )
    DIRECT_NO_PROPOSAL = "DIRECT_NO_PROPOSAL"


class V075InitialIntentKindV2(str, Enum):
    ROOT_DISCOVERY = "ROOT_DISCOVERY"
    SUPPORT_PROMOTION_TEMPLATE = "SUPPORT_PROMOTION_TEMPLATE"
    ROOT_VALIDATION = "ROOT_VALIDATION"


_REGISTRATION_ISSUER = object()
_OCCURRENCE_SLOT_ISSUER = object()
_PROFILE_ISSUER = object()
_SOURCE_PROVENANCE_ISSUER = object()
_PROPOSAL_ISSUER = object()
_INTENT_ISSUER = object()
_SCHEDULE_ISSUER = object()
_VERIFICATION_ISSUER = object()


_ARM_SPECS = (
    (
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        V075AcquisitionRouteV2.ADAPTIVE_QUOTIENT,
        V075ProposalDispositionV2.SOURCE_FORWARD_MIDRANK,
        True,
        True,
    ),
    (
        worker.V075WorkerArmV1.NO_PRIOR,
        V075AcquisitionRouteV2.ADAPTIVE_QUOTIENT,
        V075ProposalDispositionV2.NO_PRIOR_NEUTRAL,
        False,
        True,
    ),
    (
        worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
        V075AcquisitionRouteV2.ADAPTIVE_QUOTIENT,
        V075ProposalDispositionV2.WRONG_FIXED_REVERSED_MIDRANK,
        False,
        True,
    ),
    (
        worker.V075WorkerArmV1.OOD_ABSTENTION,
        V075AcquisitionRouteV2.ADAPTIVE_QUOTIENT,
        V075ProposalDispositionV2.OOD_INCOMPATIBLE_SCHEMA_ABSTENTION,
        False,
        True,
    ),
    (
        worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        V075AcquisitionRouteV2.MATCHED_DIRECT_GROUND,
        V075ProposalDispositionV2.DIRECT_NO_PROPOSAL,
        False,
        False,
    ),
)


@dataclass(frozen=True, slots=True)
class V075ArmRegistrationV2:
    """One compiler-issued V2 arm registration."""

    _issuer: object = field(repr=False, compare=False)
    ordinal: int
    arm: worker.V075WorkerArmV1
    route: V075AcquisitionRouteV2
    proposal_disposition: V075ProposalDispositionV2
    source_transport_required: bool
    proposal_artifact_required: bool
    _registration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = (
            _ARM_SPECS[self.ordinal]
            if type(self.ordinal) is int and self.ordinal in range(5)
            else None
        )
        if (
            self._issuer is not _REGISTRATION_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.route) is not V075AcquisitionRouteV2
            or type(self.proposal_disposition)
            is not V075ProposalDispositionV2
            or type(self.source_transport_required) is not bool
            or type(self.proposal_artifact_required) is not bool
            or expected
            != (
                self.arm,
                self.route,
                self.proposal_disposition,
                self.source_transport_required,
                self.proposal_artifact_required,
            )
        ):
            _fail("five-arm V2 registration is incomplete or collapsed")
        object.__setattr__(
            self,
            "_registration_id",
            _hash("arm_registration", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_acquisition_registration.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ordinal": self.ordinal,
            "arm": self.arm.value,
            "route": self.route.value,
            "proposal_disposition": self.proposal_disposition.value,
            "source_transport_requirement": (
                "COMPLETE_TRACKED_AUTHORITY_REPLAY_REQUIRED"
                if self.source_transport_required
                else "FORBIDDEN"
            ),
            "proposal_artifact_required": self.proposal_artifact_required,
            "proposal_use_rule": _proposal_use_rule(self.arm),
            "proposal_input_binding_mandatory": (
                self.proposal_artifact_required
            ),
            "proposal_ranking_executed_by_static_schedule": False,
            "future_adaptive_round_must_consume_proposal": (
                self.proposal_artifact_required
            ),
            "support_selection_rule": SUPPORT_SELECTION_RULE,
            **_zero_access_payload(),
        }

    @property
    def registration_id(self) -> str:
        return self._registration_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "registration_id": self.registration_id,
        }


def _registrations() -> tuple[V075ArmRegistrationV2, ...]:
    return tuple(
        V075ArmRegistrationV2(
            _REGISTRATION_ISSUER,
            ordinal,
            *spec,
        )
        for ordinal, spec in enumerate(_ARM_SPECS)
    )


@dataclass(frozen=True, slots=True)
class V075PreregisteredOccurrenceSlotV2:
    """One typed context-major occurrence slot frozen before target access."""

    _issuer: object = field(repr=False, compare=False)
    target_tape_namespace_id: str
    workload_id: str
    family_generation_id: str
    threshold_profile_id: str
    cap_profile_id: str
    context_ordinal: int
    context_id: str
    arm_ordinal: int
    arm: worker.V075WorkerArmV1
    occurrence_ordinal: int
    source_transport_required: bool
    _slot_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.target_tape_namespace_id, "occurrence slot namespace"),
            (self.workload_id, "occurrence slot workload"),
            (self.family_generation_id, "occurrence slot family"),
            (self.threshold_profile_id, "occurrence slot threshold"),
            (self.cap_profile_id, "occurrence slot cap"),
            (self.context_id, "occurrence slot context"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _OCCURRENCE_SLOT_ISSUER
            or type(self.context_ordinal) is not int
            or self.context_ordinal not in range(3)
            or type(self.arm_ordinal) is not int
            or self.arm_ordinal not in range(len(ARM_ORDER))
            or type(self.arm) is not worker.V075WorkerArmV1
            or self.arm is not ARM_ORDER[self.arm_ordinal]
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal
            != self.context_ordinal * len(ARM_ORDER) + self.arm_ordinal
            or type(self.source_transport_required) is not bool
            or self.source_transport_required
            != (
                self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            )
        ):
            _fail("preregistered occurrence slot is malformed")
        object.__setattr__(
            self,
            "_slot_id",
            _hash("occurrence_slot", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_occurrence_slot.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "workload_id": self.workload_id,
            "family_generation_id": self.family_generation_id,
            "threshold_profile_id": self.threshold_profile_id,
            "cap_profile_id": self.cap_profile_id,
            "context_ordinal": self.context_ordinal,
            "context_id": self.context_id,
            "arm_ordinal": self.arm_ordinal,
            "arm": self.arm.value,
            "occurrence_ordinal": self.occurrence_ordinal,
            "source_transport_required": self.source_transport_required,
            "context_major_order": True,
            "frozen_before_target_access": True,
            **_zero_access_payload(),
        }

    @property
    def slot_id(self) -> str:
        return self._slot_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "slot_id": self.slot_id}


def _occurrence_slots(
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> tuple[V075PreregisteredOccurrenceSlotV2, ...]:
    workload = namespace.workload
    return tuple(
        V075PreregisteredOccurrenceSlotV2(
            _OCCURRENCE_SLOT_ISSUER,
            namespace.target_tape_namespace_id,
            workload.workload_id,
            namespace.family.generation_id,
            workload.threshold_profile.threshold_profile_id,
            workload.cap_profile.cap_profile_id,
            context_ordinal,
            context.context_id,
            arm_ordinal,
            arm,
            context_ordinal * len(ARM_ORDER) + arm_ordinal,
            arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        )
        for context_ordinal, context in enumerate(
            namespace.family.replicate_contexts
        )
        for arm_ordinal, arm in enumerate(ARM_ORDER)
    )


@dataclass(frozen=True, slots=True)
class V075FiveArmAcquisitionProfileV2:
    """The unique V2 namespace-bound five-arm static profile."""

    _issuer: object = field(repr=False, compare=False)
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2
    registrations: tuple[V075ArmRegistrationV2, ...]
    occurrence_slots: tuple[V075PreregisteredOccurrenceSlotV2, ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        replayed = _replay_namespace(self.namespace)
        expected = _registrations()
        expected_slots = _occurrence_slots(replayed)
        caps = replayed.workload.cap_profile
        threshold = replayed.workload.threshold_profile
        if (
            self._issuer is not _PROFILE_ISSUER
            or type(self.registrations) is not tuple
            or self.registrations != expected
            or tuple(item.arm for item in self.registrations) != ARM_ORDER
            or type(self.occurrence_slots) is not tuple
            or self.occurrence_slots != expected_slots
            or len(self.occurrence_slots)
            != len(replayed.family.replicate_contexts) * len(ARM_ORDER)
            or replayed.workload != self.namespace.workload
            or replayed.workload.family != replayed.family
            or threshold.threshold_profile_id
            != replayed.workload.threshold_profile.threshold_profile_id
            or caps.cap_profile_id
            != replayed.workload.cap_profile.cap_profile_id
            or caps.maximum_adaptive_rounds != 2
            or caps.direct_validation_checkpoints
            != (2_048, 4_096, 8_192, 16_384)
            or caps.maximum_incremental_draws_per_adaptive_arm
            != (
                caps.maximum_new_child_action_rows
                * (
                    caps.new_child_discovery_draws_per_row
                    + caps.new_child_validation_draws_per_row
                )
                + caps.maximum_adaptive_rounds
                * MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
                * caps.promotion_validation_draws_per_round
            )
        ):
            _fail("five-arm V2 profile is stale, reordered, or transplanted")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("profile", self._payload()),
        )

    def _context_bindings(self) -> list[dict[str, Any]]:
        result = []
        for ordinal, context in enumerate(
            self.namespace.family.replicate_contexts
        ):
            catalogue = graph.root_catalogue_v1(context)
            result.append(
                {
                    "context_ordinal": ordinal,
                    "context_id": context.context_id,
                    "root_catalogue_id": catalogue.catalogue_id,
                    "root_state_id": catalogue.state.state_id,
                    "remaining_horizon": catalogue.remaining_horizon,
                    "complete_root_actions": [
                        list(action) for action in catalogue.actions
                    ],
                    "complete_root_action_count": len(catalogue.actions),
                }
            )
        return result

    def _payload(self) -> dict[str, Any]:
        workload = self.namespace.workload
        caps = workload.cap_profile
        return {
            "schema": "acfqp.v075_five_arm_acquisition_profile.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "workload_id": workload.workload_id,
            "family_generation_id": self.namespace.family.generation_id,
            "runner_profile_id": self.namespace.runner_profile.profile_id,
            "threshold_profile_id": (
                workload.threshold_profile.threshold_profile_id
            ),
            "cap_profile_id": workload.cap_profile.cap_profile_id,
            "arm_order": [item.value for item in ARM_ORDER],
            "arm_registration_ids": [
                item.registration_id for item in self.registrations
            ],
            "occurrence_slot_ids": [
                item.slot_id for item in self.occurrence_slots
            ],
            "context_bindings": self._context_bindings(),
            "support_selection_rule": SUPPORT_SELECTION_RULE,
            "support_promotion_rule": SUPPORT_PROMOTION_RULE,
            "maximum_adaptive_rounds": caps.maximum_adaptive_rounds,
            "initial_discovery_draws_per_row": (
                caps.initial_discovery_draws_per_row
            ),
            "initial_validation_draws_per_row": (
                caps.initial_validation_draws_per_row
            ),
            "promotion_validation_draws_per_round": (
                caps.promotion_validation_draws_per_round
            ),
            "new_child_discovery_draws_per_row": (
                caps.new_child_discovery_draws_per_row
            ),
            "new_child_validation_draws_per_row": (
                caps.new_child_validation_draws_per_row
            ),
            "maximum_new_child_action_rows": (
                caps.maximum_new_child_action_rows
            ),
            "maximum_incremental_draws_per_adaptive_arm": (
                caps.maximum_incremental_draws_per_adaptive_arm
            ),
            "maximum_dynamic_promotion_draws": (
                caps.maximum_adaptive_rounds
                * MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
                * caps.promotion_validation_draws_per_round
            ),
            "maximum_selected_rows_per_adaptive_round": (
                MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
            ),
            "adaptive_round_selection_rule": (
                ADAPTIVE_ROUND_SELECTION_RULE
            ),
            "maximum_dynamic_child_base_draws": (
                caps.maximum_new_child_action_rows
                * (
                    caps.new_child_discovery_draws_per_row
                    + caps.new_child_validation_draws_per_row
                )
            ),
            "adaptive_incremental_cap_formula": (
                "MAX_CHILD_ROWS*(CHILD_DISCOVERY+CHILD_VALIDATION)"
                "+MAX_ROUNDS*MAX_SELECTED_ROWS_PER_ROUND"
                "*PROMOTION_VALIDATION"
            ),
            "direct_validation_checkpoints": list(
                caps.direct_validation_checkpoints
            ),
            "direct_maximum_validation_checkpoint": (
                caps.direct_validation_checkpoints[-1]
            ),
            "direct_child_expansion_rule": DIRECT_CHILD_EXPANSION_RULE,
            "direct_checkpoint_rule": DIRECT_CHECKPOINT_RULE,
            "frozen_before_target_access": True,
            **_zero_access_payload(),
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def registration_for(
        self,
        arm: worker.V075WorkerArmV1,
    ) -> V075ArmRegistrationV2:
        if type(arm) is not worker.V075WorkerArmV1:
            _fail("arm registration lookup requires one typed arm")
        return self.registrations[ARM_ORDER.index(arm)]

    def occurrence_slot_for(
        self,
        *,
        context_id: str,
        arm: worker.V075WorkerArmV1,
    ) -> V075PreregisteredOccurrenceSlotV2:
        if type(arm) is not worker.V075WorkerArmV1:
            _fail("occurrence slot lookup requires one typed arm")
        matches = tuple(
            item
            for item in self.occurrence_slots
            if item.context_id == context_id and item.arm is arm
        )
        if len(matches) != 1:
            _fail("occurrence slot is absent or duplicated")
        return matches[0]

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "registrations": [
                item.to_document() for item in self.registrations
            ],
            "occurrence_slots": [
                item.to_document() for item in self.occurrence_slots
            ],
            "profile_id": self.profile_id,
        }


def freeze_v075_five_arm_acquisition_profile_v2(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075FiveArmAcquisitionProfileV2:
    exact_namespace = _replay_namespace(namespace)
    return V075FiveArmAcquisitionProfileV2(
        _PROFILE_ISSUER,
        exact_namespace,
        _registrations(),
        _occurrence_slots(exact_namespace),
    )


@lru_cache(maxsize=32)
def _replay_profile(
    claimed: V075FiveArmAcquisitionProfileV2,
) -> V075FiveArmAcquisitionProfileV2:
    if type(claimed) is not V075FiveArmAcquisitionProfileV2:
        _fail("profile replay requires one exact typed claim")
    expected = freeze_v075_five_arm_acquisition_profile_v2(
        namespace=claimed.namespace
    )
    if (
        expected.profile_id != claimed.profile_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("five-arm profile differs from exact semantic replay")
    return expected


def verify_v075_five_arm_acquisition_profile_bytes_v2(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    raw: bytes,
) -> V075FiveArmAcquisitionProfileV2:
    document = _strict_load(
        raw,
        cap=MAX_ARTIFACT_BYTES,
        field_name="five-arm acquisition profile",
    )
    expected = freeze_v075_five_arm_acquisition_profile_v2(
        namespace=namespace
    )
    if (
        set(document) != set(expected.to_document())
        or raw != expected.canonical_bytes
    ):
        _fail("five-arm acquisition profile differs from exact replay")
    return expected


@dataclass(frozen=True, slots=True)
class V075TrackedSourceProposalProvenanceV2:
    """Typed replay of the complete tracked SOURCE proposal authority.

    The transport object is retained as a semantic witness.  Every exposed
    identifier and the forward-midrank vector are rederived from its canonical
    bytes, so replacing any standalone CID cannot preserve this object.
    """

    _issuer: object = field(repr=False, compare=False)
    transport: worker.V075SourcePriorTransportV1 = field(repr=False)
    source_catalogue_id: str
    _provenance_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        replayed = _replay_source_transport(self.transport)
        _values, exact_catalogue_id = _source_values_from_transport(replayed)
        if (
            self._issuer is not _SOURCE_PROVENANCE_ISSUER
            or replayed.transport_id != SOURCE_TRANSPORT_ID
            or hashlib.sha256(_transport_bytes(replayed)).hexdigest()
            != SOURCE_TRANSPORT_BYTES_SHA256
            or replayed.adapter_id != SOURCE_ADAPTER_ID
            or replayed.verification_id != SOURCE_VERIFICATION_ID
            or self.source_catalogue_id != exact_catalogue_id
            or exact_catalogue_id != SOURCE_CATALOGUE_ID
        ):
            _fail(
                "tracked SOURCE provenance is caller-minted, partial, "
                "or differs from the preregistered source archive"
            )
        object.__setattr__(
            self,
            "_provenance_id",
            _hash("source_provenance", self._payload()),
        )

    @property
    def source_transport_id(self) -> str:
        return self.transport.transport_id

    @property
    def source_adapter_id(self) -> str:
        return self.transport.adapter_id

    @property
    def source_verification_id(self) -> str:
        return self.transport.verification_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_five_arm_tracked_source_provenance.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_transport_id": self.source_transport_id,
            "source_transport_bytes_sha256": hashlib.sha256(
                _transport_bytes(self.transport)
            ).hexdigest(),
            "source_adapter_id": self.source_adapter_id,
            "source_adapter_bytes_sha256": hashlib.sha256(
                self.transport.adapter_bytes
            ).hexdigest(),
            "source_verification_id": self.source_verification_id,
            "source_verification_bytes_sha256": hashlib.sha256(
                self.transport.verification_bytes
            ).hexdigest(),
            "source_catalogue_id": self.source_catalogue_id,
            "source_archive_id": SOURCE_ARCHIVE_ID,
            "source_archive_verification_id": (
                SOURCE_ARCHIVE_VERIFICATION_ID
            ),
            "complete_tracked_authority_replayed": True,
            "proposal_only": True,
            "may_certify": False,
            **_zero_access_payload(),
        }

    @property
    def provenance_id(self) -> str:
        return self._provenance_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "provenance_id": self.provenance_id,
        }


@dataclass(frozen=True, slots=True)
class V075ProposalViewV2:
    """Occurrence-bound proposal view with arm-exclusive provenance."""

    _issuer: object = field(repr=False, compare=False)
    profile: V075FiveArmAcquisitionProfileV2 = field(repr=False)
    occurrence: identity_backend.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    target_tape_namespace_id: str
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    disposition: V075ProposalDispositionV2
    applicable_feature_schema_id: str
    feature_midranks: tuple[tuple[str, Fraction], ...]
    source_provenance: V075TrackedSourceProposalProvenanceV2 | None = field(
        repr=False
    )
    fixed_control_id: str | None
    _proposal_view_id: str = field(init=False, repr=False)

    @property
    def source_transport_id(self) -> str | None:
        return (
            None
            if self.source_provenance is None
            else self.source_provenance.source_transport_id
        )

    @property
    def source_adapter_id(self) -> str | None:
        return (
            None
            if self.source_provenance is None
            else self.source_provenance.source_adapter_id
        )

    @property
    def source_verification_id(self) -> str | None:
        return (
            None
            if self.source_provenance is None
            else self.source_provenance.source_verification_id
        )

    @property
    def source_catalogue_id(self) -> str | None:
        return (
            None
            if self.source_provenance is None
            else self.source_provenance.source_catalogue_id
        )

    def __post_init__(self) -> None:
        if type(self.profile) is not V075FiveArmAcquisitionProfileV2:
            _fail("proposal view lacks its exact V2 profile witness")
        replayed_profile = _replay_profile(self.profile)
        try:
            replayed_occurrence = (
                identity_backend
                .replay_v075_batch_native_occurrence_identity_v1(
                    self.occurrence
                )
            )
        except Exception as error:
            raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
                "proposal occurrence replay failed"
            ) from error
        _cid(self.target_tape_namespace_id, "proposal namespace")
        _cid(self.occurrence_id, "proposal occurrence")
        if (
            self._issuer is not _PROPOSAL_ISSUER
            or replayed_profile.canonical_bytes != self.profile.canonical_bytes
            or replayed_occurrence.occurrence_id
            != self.occurrence.occurrence_id
            or self.target_tape_namespace_id
            != self.profile.namespace.target_tape_namespace_id
            or self.target_tape_namespace_id
            != replayed_occurrence.target_tape_namespace_id
            or self.occurrence_id != replayed_occurrence.occurrence_id
            or self.arm is not replayed_occurrence.arm
            or replayed_occurrence.threshold_profile_id
            != (
                self.profile.namespace.workload.threshold_profile
                .threshold_profile_id
            )
            or replayed_occurrence.cap_profile_id
            != self.profile.namespace.workload.cap_profile.cap_profile_id
            or type(self.arm) is not worker.V075WorkerArmV1
            or self.arm is DIRECT_ARM
            or type(self.disposition) is not V075ProposalDispositionV2
            or type(self.applicable_feature_schema_id) is not str
            or type(self.feature_midranks) is not tuple
            or self.feature_midranks
            != tuple(sorted(self.feature_midranks))
            or len({key for key, _value in self.feature_midranks})
            != len(self.feature_midranks)
        ):
            _fail("V2 proposal view is malformed or direct")
        for key, value in self.feature_midranks:
            _cid(key, "proposal feature")
            if type(value) is not Fraction or not 0 <= value <= 1:
                _fail("proposal midrank is not one exact unit interval value")
        if self.source_provenance is not None:
            if (
                type(self.source_provenance)
                is not V075TrackedSourceProposalProvenanceV2
            ):
                _fail("SOURCE proposal provenance is not one exact type")
            replayed_provenance = V075TrackedSourceProposalProvenanceV2(
                _SOURCE_PROVENANCE_ISSUER,
                _replay_source_transport(self.source_provenance.transport),
                self.source_provenance.source_catalogue_id,
            )
            if (
                replayed_provenance.canonical_bytes
                != self.source_provenance.canonical_bytes
            ):
                _fail("SOURCE proposal provenance differs from exact replay")
        for value, label in (
            (self.source_transport_id, "proposal source transport"),
            (self.source_adapter_id, "proposal source adapter"),
            (self.source_verification_id, "proposal source verification"),
            (self.source_catalogue_id, "proposal source catalogue"),
            (self.fixed_control_id, "proposal fixed control"),
        ):
            if value is not None:
                _cid(value, label)
        source_fields = (
            self.source_transport_id,
            self.source_adapter_id,
            self.source_verification_id,
            self.source_catalogue_id,
        )
        if self.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            if (
                self.disposition
                is not V075ProposalDispositionV2.SOURCE_FORWARD_MIDRANK
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                != tuple(sorted(REGISTERED_FORWARD_MIDRANKS))
                or any(value is None for value in source_fields)
                or self.source_provenance is None
                or self.feature_midranks
                != _source_values_from_transport(
                    self.source_provenance.transport
                )[0]
                or self.fixed_control_id is not None
            ):
                _fail("SOURCE proposal is incomplete or changed")
        elif self.arm is worker.V075WorkerArmV1.NO_PRIOR:
            if (
                self.disposition
                is not V075ProposalDispositionV2.NO_PRIOR_NEUTRAL
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                or any(value is not None for value in source_fields)
                or self.source_provenance is not None
                or self.fixed_control_id is not None
            ):
                _fail("NO_PRIOR proposal is not neutral and source-free")
        elif self.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
            if (
                self.disposition
                is not (
                    V075ProposalDispositionV2
                    .WRONG_FIXED_REVERSED_MIDRANK
                )
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                != REGISTERED_WRONG_REVERSED_MIDRANKS
                or any(value is not None for value in source_fields)
                or self.source_provenance is not None
                or self.fixed_control_id != WRONG_FIXED_CONTROL_ID
            ):
                _fail("WRONG proposal is not the fixed source-free reversal")
        elif self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION:
            if (
                self.disposition
                is not (
                    V075ProposalDispositionV2
                    .OOD_INCOMPATIBLE_SCHEMA_ABSTENTION
                )
                or self.applicable_feature_schema_id
                != OOD_INCOMPATIBLE_FEATURE_SCHEMA_ID
                or self.applicable_feature_schema_id
                == SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                or any(value is not None for value in source_fields)
                or self.source_provenance is not None
                or self.fixed_control_id is not None
            ):
                _fail("OOD proposal did not explicitly abstain")
        object.__setattr__(
            self,
            "_proposal_view_id",
            _hash("proposal_view", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_proposal_view.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "acquisition_profile_id": self.profile.profile_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "disposition": self.disposition.value,
            "applicable_feature_schema_id": (
                self.applicable_feature_schema_id
            ),
            "feature_midranks": [
                {
                    "feature_key": key,
                    "mean_midrank": _fdoc(value),
                }
                for key, value in self.feature_midranks
            ],
            "source_transport_id": self.source_transport_id,
            "source_provenance_id": (
                None
                if self.source_provenance is None
                else self.source_provenance.provenance_id
            ),
            "source_adapter_id": self.source_adapter_id,
            "source_verification_id": self.source_verification_id,
            "source_catalogue_id": self.source_catalogue_id,
            "source_archive_id": (
                SOURCE_ARCHIVE_ID
                if self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                else None
            ),
            "source_archive_verification_id": (
                SOURCE_ARCHIVE_VERIFICATION_ID
                if self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                else None
            ),
            "fixed_control_id": self.fixed_control_id,
            "source_transport_accessed": (
                self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ),
            "source_transport_forbidden": (
                self.arm
                is not worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ),
            "explicit_abstention": (
                self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            ),
            "proposal_only": True,
            "may_certify": False,
            "target_fields_present": False,
            "source_dynamics_present": False,
            **_zero_access_payload(),
        }

    @property
    def proposal_view_id(self) -> str:
        return self._proposal_view_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_provenance": (
                None
                if self.source_provenance is None
                else self.source_provenance.to_document()
            ),
            "proposal_view_id": self.proposal_view_id,
        }


def _replay_proposal_view(
    claimed: V075ProposalViewV2,
) -> V075ProposalViewV2:
    if type(claimed) is not V075ProposalViewV2:
        _fail("proposal replay requires one exact typed view")
    try:
        expected = V075ProposalViewV2(
            _PROPOSAL_ISSUER,
            claimed.profile,
            claimed.occurrence,
            claimed.target_tape_namespace_id,
            claimed.occurrence_id,
            claimed.arm,
            claimed.disposition,
            claimed.applicable_feature_schema_id,
            claimed.feature_midranks,
            claimed.source_provenance,
            claimed.fixed_control_id,
        )
        if expected.canonical_bytes != claimed.canonical_bytes:
            _fail("proposal view differs from exact semantic replay")
    except (
        AttributeError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        if type(error) is V075FiveArmAcquisitionAuthorityV2InvariantViolation:
            raise
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "proposal view semantic replay failed"
        ) from error
    return expected


def _source_values_from_transport(
    transport: worker.V075SourcePriorTransportV1,
) -> tuple[
    tuple[tuple[str, Fraction], ...],
    str,
]:
    if type(transport) is not worker.V075SourcePriorTransportV1:
        _fail("SOURCE view requires one exact tracked transport")
    try:
        adapter = loads_canonical_json(transport.adapter_bytes)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "tracked SOURCE adapter is not canonical JSON"
        ) from error
    catalogue = (
        adapter.get("catalogue") if type(adapter) is dict else None
    )
    entries = (
        catalogue.get("entries")
        if type(catalogue) is dict
        else None
    )
    if (
        type(adapter) is not dict
        or canonical_json_bytes(adapter) != transport.adapter_bytes
        or adapter.get("schema")
        != "acfqp.v075_source_prior_adapter.v1"
        or adapter.get("adapter_id") != transport.adapter_id
        or adapter.get("source_archive_id") != SOURCE_ARCHIVE_ID
        or adapter.get("source_archive_verification_id")
        != SOURCE_ARCHIVE_VERIFICATION_ID
        or adapter.get("registered_applied_feature_keys")
        != list(REGISTERED_FORWARD_KEYS)
        or adapter.get("source_only") is not True
        or adapter.get("proposal_only") is not True
        or adapter.get("may_certify") is not False
        or type(catalogue) is not dict
        or catalogue.get("source_feature_schema_id")
        != SOURCE_FEATURE_SCHEMA_ID
        or catalogue.get("registered_applied_feature_keys")
        != list(REGISTERED_FORWARD_KEYS)
        or type(entries) is not list
        or len(entries) != len(REGISTERED_FORWARD_MIDRANKS)
    ):
        _fail("tracked SOURCE authority changed schema or provenance")
    actual = []
    for ordinal, entry in enumerate(entries):
        if (
            type(entry) is not dict
            or entry.get("applied_ordinal") != ordinal
            or entry.get("feature_key") != REGISTERED_FORWARD_KEYS[ordinal]
            or entry.get("disposition") != "APPLIED"
            or entry.get("source_only") is not True
            or entry.get("proposal_only") is not True
            or entry.get("may_certify") is not False
        ):
            _fail("tracked SOURCE APPLIED entries changed or reordered")
        actual.append(
            (
                entry["feature_key"],
                _fraction(
                    entry.get("exact_mean_midrank"),
                    "tracked SOURCE exact midrank",
                ),
            )
        )
    if tuple(actual) != REGISTERED_FORWARD_MIDRANKS:
        _fail("tracked SOURCE forward midranks differ from V2 registration")
    source_catalogue_id = _cid(
        catalogue.get("catalogue_id"),
        "tracked SOURCE catalogue",
    )
    return tuple(sorted(actual)), source_catalogue_id


def _replay_occurrence(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    occurrence: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
) -> tuple[
    identity_backend.V075BatchNativeOccurrenceIdentityV1,
    worker.V075SourcePriorTransportV1 | None,
]:
    exact_namespace = _replay_namespace(namespace)
    try:
        replayed = (
            identity_backend
            .replay_v075_batch_native_occurrence_identity_v1(occurrence)
        )
    except Exception as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "occurrence identity semantic replay failed"
        ) from error
    if (
        replayed.target_tape_namespace_id
        != exact_namespace.target_tape_namespace_id
        or replayed.threshold_profile_id
        != exact_namespace.workload.threshold_profile.threshold_profile_id
        or replayed.cap_profile_id
        != exact_namespace.workload.cap_profile.cap_profile_id
    ):
        _fail("occurrence identity is transplanted across V2 bindings")
    context = _context_by_id(exact_namespace, replayed.context_id)
    context_ordinal = exact_namespace.family.replicate_contexts.index(
        context
    )
    expected_occurrence_ordinal = (
        context_ordinal * len(ARM_ORDER) + ARM_ORDER.index(replayed.arm)
    )
    if replayed.occurrence_ordinal != expected_occurrence_ordinal:
        _fail("occurrence ordinal differs from context-major arm order")
    transport = None
    if replayed.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        transport = _load_tracked_source_transport(repository_root)
        if replayed.source_transport_id != transport.transport_id:
            _fail("SOURCE occurrence differs from tracked source authority")
    elif replayed.source_transport_id is not None:
        _fail("non-SOURCE occurrence injected source transport")
    return replayed, transport


def freeze_v075_occurrence_proposal_view_v2(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    occurrence: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
) -> V075ProposalViewV2 | None:
    """Freeze the exact arm-specific proposal without accessing a target."""

    replayed, transport = _replay_occurrence(
        repository_root=repository_root,
        namespace=namespace,
        occurrence=occurrence,
    )
    profile = freeze_v075_five_arm_acquisition_profile_v2(
        namespace=namespace
    )
    common = (
        _PROPOSAL_ISSUER,
        profile,
        replayed,
        replayed.target_tape_namespace_id,
        replayed.occurrence_id,
        replayed.arm,
    )
    if replayed.arm is DIRECT_ARM:
        if transport is not None:
            _fail("direct occurrence acquired a proposal transport")
        return None
    if replayed.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        if transport is None:  # pragma: no cover - guarded by replay
            _fail("SOURCE occurrence lacks tracked transport")
        values, catalogue_id = _source_values_from_transport(transport)
        provenance = V075TrackedSourceProposalProvenanceV2(
            _SOURCE_PROVENANCE_ISSUER,
            _replay_source_transport(transport),
            catalogue_id,
        )
        return V075ProposalViewV2(
            *common,
            V075ProposalDispositionV2.SOURCE_FORWARD_MIDRANK,
            SOURCE_FEATURE_SCHEMA_ID,
            values,
            provenance,
            None,
        )
    if transport is not None:  # pragma: no cover - guarded by replay
        _fail("non-SOURCE proposal consumed source transport")
    if replayed.arm is worker.V075WorkerArmV1.NO_PRIOR:
        return V075ProposalViewV2(
            *common,
            V075ProposalDispositionV2.NO_PRIOR_NEUTRAL,
            SOURCE_FEATURE_SCHEMA_ID,
            (),
            None,
            None,
        )
    if replayed.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
        return V075ProposalViewV2(
            *common,
            V075ProposalDispositionV2.WRONG_FIXED_REVERSED_MIDRANK,
            SOURCE_FEATURE_SCHEMA_ID,
            REGISTERED_WRONG_REVERSED_MIDRANKS,
            None,
            WRONG_FIXED_CONTROL_ID,
        )
    if replayed.arm is worker.V075WorkerArmV1.OOD_ABSTENTION:
        return V075ProposalViewV2(
            *common,
            V075ProposalDispositionV2.OOD_INCOMPATIBLE_SCHEMA_ABSTENTION,
            OOD_INCOMPATIBLE_FEATURE_SCHEMA_ID,
            (),
            None,
            None,
        )
    _fail("unregistered five-arm occurrence")
    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class V075InitialRowIntentV2:
    """One root-row pretarget intent or support-promotion template."""

    _issuer: object = field(repr=False, compare=False)
    profile: V075FiveArmAcquisitionProfileV2 = field(repr=False)
    occurrence: identity_backend.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    proposal_view: V075ProposalViewV2 | None = field(repr=False)
    proposal_use_rule: str
    target_tape_namespace_id: str
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    row_binding: graph.V075ObservationRowBindingV1
    ordinal: int
    row_ordinal: int
    kind: V075InitialIntentKindV2
    observer_epoch_index: int | None
    accepted_draw_start: int | None
    accepted_draw_count: int
    accepted_draw_cap: int
    dependency_intent_ids: tuple[str, ...]
    cap_profile_id: str
    _intent_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.profile) is not V075FiveArmAcquisitionProfileV2:
            _fail("initial intent lacks its exact V2 profile witness")
        replayed_profile = _replay_profile(self.profile)
        try:
            replayed_occurrence = (
                identity_backend
                .replay_v075_batch_native_occurrence_identity_v1(
                    self.occurrence
                )
            )
        except Exception as error:
            raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
                "initial intent occurrence replay failed"
            ) from error
        _cid(self.target_tape_namespace_id, "initial intent namespace")
        _cid(self.occurrence_id, "initial intent occurrence")
        _cid(self.cap_profile_id, "initial intent cap profile")
        if (
            self._issuer is not _INTENT_ISSUER
            or replayed_profile.canonical_bytes != self.profile.canonical_bytes
            or type(self.occurrence)
            is not identity_backend.V075BatchNativeOccurrenceIdentityV1
            or type(self.arm) is not worker.V075WorkerArmV1
            or self.target_tape_namespace_id
            != replayed_occurrence.target_tape_namespace_id
            or self.target_tape_namespace_id
            != self.profile.namespace.target_tape_namespace_id
            or self.occurrence_id != replayed_occurrence.occurrence_id
            or self.arm is not replayed_occurrence.arm
            or self.cap_profile_id != replayed_occurrence.cap_profile_id
            or self.proposal_use_rule != _proposal_use_rule(self.arm)
            or type(self.row_binding)
            is not graph.V075ObservationRowBindingV1
            or self.row_binding.remaining_horizon != 2
            or type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.row_ordinal) is not int
            or self.row_ordinal < 0
            or type(self.kind) is not V075InitialIntentKindV2
            or type(self.dependency_intent_ids) is not tuple
            or self.dependency_intent_ids
            != tuple(dict.fromkeys(self.dependency_intent_ids))
        ):
            _fail("initial row intent is malformed")
        registered_contexts = {
            item.context_id: (ordinal, item)
            for ordinal, item in enumerate(
                self.profile.namespace.family.replicate_contexts
            )
        }
        occurrence_context_pair = registered_contexts.get(
            replayed_occurrence.context_id
        )
        if occurrence_context_pair is None:
            _fail("initial intent occurrence context is not registered")
        context_ordinal, occurrence_context = occurrence_context_pair
        expected_occurrence_ordinal = (
            context_ordinal * len(ARM_ORDER)
            + ARM_ORDER.index(replayed_occurrence.arm)
        )
        thresholds = self.profile.namespace.workload.threshold_profile
        caps = self.profile.namespace.workload.cap_profile
        if (
            replayed_occurrence.occurrence_ordinal
            != expected_occurrence_ordinal
            or replayed_occurrence.threshold_profile_id
            != thresholds.threshold_profile_id
            or replayed_occurrence.cap_profile_id != caps.cap_profile_id
        ):
            _fail(
                "initial intent occurrence differs from the context-major "
                "threshold/cap registration"
            )
        root = graph.root_catalogue_v1(occurrence_context)
        if self.row_ordinal not in range(len(root.actions)):
            _fail("initial intent row ordinal is outside root catalogue")
        expected_row = graph.observation_row_binding_v1(
            occurrence_context,
            root,
            root.actions[self.row_ordinal],
        )
        if self.row_binding != expected_row:
            _fail(
                "initial intent row is transplanted across occurrence context "
                "or root catalogue"
            )
        if self.arm is DIRECT_ARM:
            if self.proposal_view is not None:
                _fail("direct intent cannot carry one adaptive proposal")
        elif (
            type(self.proposal_view) is not V075ProposalViewV2
        ):
            _fail("adaptive intent lacks its exact typed proposal view")
        if self.proposal_view is not None:
            replayed_proposal = _replay_proposal_view(self.proposal_view)
            if (
                replayed_proposal.canonical_bytes
                != self.proposal_view.canonical_bytes
                or self.proposal_view.profile.canonical_bytes
                != self.profile.canonical_bytes
                or self.proposal_view.occurrence
                != replayed_occurrence
                or self.proposal_view.arm is not self.arm
                or self.proposal_view.occurrence_id != self.occurrence_id
                or self.proposal_view.target_tape_namespace_id
                != self.target_tape_namespace_id
            ):
                _fail("adaptive intent proposal was transplanted or forged")
        if (
            self.arm
            is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            and (
                self.proposal_view is None
                or self.proposal_view.source_transport_id
                != replayed_occurrence.source_transport_id
            )
        ):
            _fail("SOURCE intent proposal differs from its occurrence")
        if (
            self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            and (
                self.proposal_view is None
                or self.proposal_view.disposition
                is not (
                    V075ProposalDispositionV2
                    .OOD_INCOMPATIBLE_SCHEMA_ABSTENTION
                )
                or self.proposal_use_rule
                != PROPOSAL_USE_RULES[
                    worker.V075WorkerArmV1.OOD_ABSTENTION
                ]
            )
        ):
            _fail("OOD intent does not preserve explicit abstention")
        for value in self.dependency_intent_ids:
            _cid(value, "initial intent dependency")
        if self.cap_profile_id != caps.cap_profile_id:
            _fail("initial intent cap profile changed")
        if self.kind is V075InitialIntentKindV2.ROOT_DISCOVERY:
            expected = (
                0,
                1,
                caps.initial_discovery_draws_per_row,
                caps.initial_discovery_draws_per_row,
                (),
            )
        elif (
            self.kind
            is V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
        ):
            expected = (None, None, 0, 0, self.dependency_intent_ids)
            if len(self.dependency_intent_ids) != 1:
                _fail("support promotion must depend on one discovery intent")
        else:
            accepted_cap = (
                caps.initial_validation_draws_per_row
                + caps.maximum_adaptive_rounds
                * caps.promotion_validation_draws_per_round
            )
            expected = (
                1,
                1,
                caps.initial_validation_draws_per_row,
                accepted_cap,
                self.dependency_intent_ids,
            )
            if self.arm is DIRECT_ARM or len(self.dependency_intent_ids) != 1:
                _fail("root validation requires one adaptive promotion")
        if (
            self.observer_epoch_index,
            self.accepted_draw_start,
            self.accepted_draw_count,
            self.accepted_draw_cap,
            self.dependency_intent_ids,
        ) != expected:
            _fail("initial row intent counts, dependencies, or caps changed")
        object.__setattr__(
            self,
            "_intent_id",
            _hash("initial_intent", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_five_arm_initial_row_intent.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "acquisition_profile_id": self.profile.profile_id,
            "occurrence_id": self.occurrence_id,
            "occurrence_context_id": self.occurrence.context_id,
            "arm": self.arm.value,
            "context_id": self.row_binding.context_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "catalogue_id": self.row_binding.catalogue_id,
            "root_state_id": self.row_binding.state_id,
            "action": list(self.row_binding.action),
            "ordinal": self.ordinal,
            "row_ordinal": self.row_ordinal,
            "kind": self.kind.value,
            "lane": {
                V075InitialIntentKindV2.ROOT_DISCOVERY: "DISCOVERY",
                V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE: (
                    "SUPPORT_PROMOTION_BARRIER"
                ),
                V075InitialIntentKindV2.ROOT_VALIDATION: "VALIDATION",
            }[self.kind],
            "observer_epoch_index": self.observer_epoch_index,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": (
                None
                if self.accepted_draw_start is None
                else (
                    self.accepted_draw_start
                    + self.accepted_draw_count
                    - 1
                )
            ),
            "accepted_draw_cap": self.accepted_draw_cap,
            "dependency_intent_ids": list(self.dependency_intent_ids),
            "cap_profile_id": self.cap_profile_id,
            "proposal_view_id": (
                None
                if self.proposal_view is None
                else self.proposal_view.proposal_view_id
            ),
            "proposal_use_rule": self.proposal_use_rule,
            "proposal_input_binding_mandatory": self.arm is not DIRECT_ARM,
            "proposal_ranking_executed": False,
            "future_adaptive_round_must_consume_proposal": (
                self.arm is not DIRECT_ARM
            ),
            "ood_explicit_abstention_required": (
                self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            ),
            "support_selection_rule": SUPPORT_SELECTION_RULE,
            "support_promotion_rule": SUPPORT_PROMOTION_RULE,
            "template_only": (
                self.kind
                is V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
            ),
            "stream_identity_minted_at_execution": (
                self.kind
                is not V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
            ),
            "support_materialized_at_execution": (
                self.kind
                is V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
            ),
            "frozen_before_target_access": True,
            **_zero_access_payload(),
        }

    @property
    def intent_id(self) -> str:
        return self._intent_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075InitialAcquisitionScheduleV2:
    """Complete occurrence-bound static root schedule."""

    _issuer: object = field(repr=False, compare=False)
    profile: V075FiveArmAcquisitionProfileV2
    occurrence: identity_backend.V075BatchNativeOccurrenceIdentityV1
    proposal_view: V075ProposalViewV2 | None
    proposal_use_rule: str
    intents: tuple[V075InitialRowIntentV2, ...]
    _schedule_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _SCHEDULE_ISSUER
            or type(self.profile) is not V075FiveArmAcquisitionProfileV2
            or type(self.occurrence)
            is not identity_backend.V075BatchNativeOccurrenceIdentityV1
            or self.proposal_use_rule
            != _proposal_use_rule(self.occurrence.arm)
            or type(self.intents) is not tuple
        ):
            _fail("initial acquisition schedule is caller-minted")
        replayed_profile = _replay_profile(self.profile)
        try:
            replayed_occurrence = (
                identity_backend
                .replay_v075_batch_native_occurrence_identity_v1(
                    self.occurrence
                )
            )
        except Exception as error:
            raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
                "schedule occurrence replay failed"
            ) from error
        if (
            replayed_profile.canonical_bytes != self.profile.canonical_bytes
            or replayed_occurrence.occurrence_id
            != self.occurrence.occurrence_id
            or self.profile.namespace.target_tape_namespace_id
            != self.occurrence.target_tape_namespace_id
        ):
            _fail("schedule profile or occurrence is transplanted")
        arm = self.occurrence.arm
        registration = self.profile.registration_for(arm)
        if (
            (self.proposal_view is None)
            != (arm is DIRECT_ARM)
            or (
                self.proposal_view is not None
                and (
                    type(self.proposal_view) is not V075ProposalViewV2
                    or self.proposal_view.arm is not arm
                    or self.proposal_view.occurrence_id
                    != self.occurrence.occurrence_id
                    or self.proposal_view.target_tape_namespace_id
                    != self.occurrence.target_tape_namespace_id
                )
            )
            or registration.proposal_artifact_required
            != (self.proposal_view is not None)
        ):
            _fail("schedule proposal view collapsed or crossed arms")
        if self.proposal_view is not None:
            replayed_proposal = _replay_proposal_view(self.proposal_view)
            if (
                replayed_proposal.canonical_bytes
                != self.proposal_view.canonical_bytes
                or self.proposal_view.profile.canonical_bytes
                != self.profile.canonical_bytes
                or self.proposal_view.occurrence != replayed_occurrence
            ):
                _fail("schedule proposal view is forged or transplanted")
        context = _context_by_id(
            self.profile.namespace,
            self.occurrence.context_id,
        )
        context_ordinal = (
            self.profile.namespace.family.replicate_contexts.index(context)
        )
        if (
            self.occurrence.occurrence_ordinal
            != context_ordinal * len(ARM_ORDER) + ARM_ORDER.index(arm)
            or self.occurrence.threshold_profile_id
            != (
                self.profile.namespace.workload.threshold_profile
                .threshold_profile_id
            )
            or self.occurrence.cap_profile_id
            != self.profile.namespace.workload.cap_profile.cap_profile_id
            or (
                arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                and (
                    self.proposal_view is None
                    or self.proposal_view.source_transport_id
                    != self.occurrence.source_transport_id
                )
            )
        ):
            _fail(
                "schedule occurrence differs from its context-major "
                "threshold/cap/source registration"
            )
        root = graph.root_catalogue_v1(context)
        exact_rows = tuple(
            graph.observation_row_binding_v1(
                context,
                root,
                action,
            )
            for action in root.actions
        )
        discoveries = tuple(
            item
            for item in self.intents
            if item.kind is V075InitialIntentKindV2.ROOT_DISCOVERY
        )
        promotions = tuple(
            item
            for item in self.intents
            if item.kind
            is V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE
        )
        validations = tuple(
            item
            for item in self.intents
            if item.kind is V075InitialIntentKindV2.ROOT_VALIDATION
        )
        expected_intent_count = (
            2 * len(root.actions)
            if arm is DIRECT_ARM
            else 3 * len(root.actions)
        )
        expected_order = (
            (*discoveries, *promotions)
            if arm is DIRECT_ARM
            else (*discoveries, *promotions, *validations)
        )
        if (
            len(self.intents) != expected_intent_count
            or self.intents != expected_order
            or tuple(item.ordinal for item in self.intents)
            != tuple(range(expected_intent_count))
            or tuple(item.row_ordinal for item in discoveries)
            != tuple(range(len(root.actions)))
            or tuple(item.row_ordinal for item in promotions)
            != tuple(range(len(root.actions)))
            or tuple(item.row_binding.action for item in discoveries)
            != root.actions
            or tuple(item.row_binding.action for item in promotions)
            != root.actions
            or tuple(item.row_binding for item in discoveries) != exact_rows
            or tuple(item.row_binding for item in promotions) != exact_rows
            or tuple(
                item.dependency_intent_ids for item in promotions
            )
            != tuple((item.intent_id,) for item in discoveries)
            or any(
                item.arm is not arm
                or item.profile.canonical_bytes
                != self.profile.canonical_bytes
                or item.occurrence != self.occurrence
                or item.occurrence_id != self.occurrence.occurrence_id
                or item.target_tape_namespace_id
                != self.occurrence.target_tape_namespace_id
                or item.proposal_view != self.proposal_view
                or item.proposal_use_rule != self.proposal_use_rule
                for item in self.intents
            )
        ):
            _fail("initial schedule omitted, reordered, or aliased a root row")
        if arm is DIRECT_ARM:
            if validations:
                _fail("direct schedule invented pretarget validation rows")
        elif (
            tuple(item.row_ordinal for item in validations)
            != tuple(range(len(root.actions)))
            or tuple(item.row_binding.action for item in validations)
            != root.actions
            or tuple(item.row_binding for item in validations) != exact_rows
            or tuple(
                item.dependency_intent_ids for item in validations
            )
            != tuple((item.intent_id,) for item in promotions)
        ):
            _fail("adaptive validation chain is incomplete or reordered")
        caps = self.profile.namespace.workload.cap_profile
        child_base_upper = caps.maximum_new_child_action_rows * (
            caps.new_child_discovery_draws_per_row
            + caps.new_child_validation_draws_per_row
        )
        promotion_upper = (
            caps.maximum_adaptive_rounds
            * MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
            * caps.promotion_validation_draws_per_round
        )
        if (
            arm is not DIRECT_ARM
            and child_base_upper + promotion_upper
            != caps.maximum_incremental_draws_per_adaptive_arm
        ):
            _fail("adaptive sound route draw formula differs from cap profile")
        expected_initial = len(root.actions) * (
            caps.initial_discovery_draws_per_row
            + (
                0
                if arm is DIRECT_ARM
                else caps.initial_validation_draws_per_row
            )
        )
        expected_route_upper = (
            expected_initial
            + caps.maximum_incremental_draws_per_adaptive_arm
            if arm is not DIRECT_ARM
            else (
                expected_initial
                + caps.maximum_new_child_action_rows
                * caps.new_child_discovery_draws_per_row
                + (
                    len(root.actions)
                    + caps.maximum_new_child_action_rows
                )
                * caps.direct_validation_checkpoints[-1]
            )
        )
        if (
            self.initial_committed_draws != expected_initial
            or self.sound_route_draw_upper != expected_route_upper
        ):
            _fail("initial commitment or sound route upper is incomplete")
        object.__setattr__(
            self,
            "_schedule_id",
            _hash("initial_schedule", self._payload()),
        )

    @property
    def initial_committed_draws(self) -> int:
        return sum(item.accepted_draw_count for item in self.intents)

    @property
    def sound_route_draw_upper(self) -> int:
        caps = self.profile.namespace.workload.cap_profile
        context = _context_by_id(
            self.profile.namespace,
            self.occurrence.context_id,
        )
        root_row_count = len(graph.root_catalogue_v1(context).actions)
        if self.occurrence.arm is not DIRECT_ARM:
            return (
                self.initial_committed_draws
                + caps.maximum_incremental_draws_per_adaptive_arm
            )
        return (
            self.initial_committed_draws
            + caps.maximum_new_child_action_rows
            * caps.new_child_discovery_draws_per_row
            + (
                root_row_count + caps.maximum_new_child_action_rows
            )
            * caps.direct_validation_checkpoints[-1]
        )

    def _payload(self) -> dict[str, Any]:
        arm = self.occurrence.arm
        caps = self.profile.namespace.workload.cap_profile
        context = _context_by_id(
            self.profile.namespace,
            self.occurrence.context_id,
        )
        root_row_count = len(graph.root_catalogue_v1(context).actions)
        child_discovery_upper = (
            caps.maximum_new_child_action_rows
            * caps.new_child_discovery_draws_per_row
        )
        child_validation_upper = (
            caps.maximum_new_child_action_rows
            * caps.new_child_validation_draws_per_row
        )
        dynamic_promotion_upper = (
            caps.maximum_adaptive_rounds
            * MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
            * caps.promotion_validation_draws_per_round
        )
        direct_validation_upper = (
            root_row_count + caps.maximum_new_child_action_rows
        ) * caps.direct_validation_checkpoints[-1]
        return {
            "schema": "acfqp.v075_five_arm_initial_acquisition_schedule.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": (
                self.occurrence.target_tape_namespace_id
            ),
            "workload_id": self.profile.namespace.workload.workload_id,
            "profile_id": self.profile.profile_id,
            "occurrence_id": self.occurrence.occurrence_id,
            "occurrence_ordinal": self.occurrence.occurrence_ordinal,
            "context_id": self.occurrence.context_id,
            "arm": arm.value,
            "arm_ordinal": ARM_ORDER.index(arm),
            "route": self.profile.registration_for(arm).route.value,
            "proposal_view_id": (
                None
                if self.proposal_view is None
                else self.proposal_view.proposal_view_id
            ),
            "proposal_use_rule": self.proposal_use_rule,
            "proposal_input_binding_mandatory": arm is not DIRECT_ARM,
            "proposal_ranking_executed": False,
            "future_adaptive_round_must_consume_proposal": (
                arm is not DIRECT_ARM
            ),
            "ood_explicit_abstention_required": (
                arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            ),
            "intent_ids": [item.intent_id for item in self.intents],
            "intent_count": len(self.intents),
            "root_action_row_count": root_row_count,
            "initial_root_discovery_draws": (
                root_row_count * caps.initial_discovery_draws_per_row
            ),
            "initial_root_validation_draws": (
                0
                if arm is DIRECT_ARM
                else root_row_count
                * caps.initial_validation_draws_per_row
            ),
            "initial_committed_draws": self.initial_committed_draws,
            "initial_committed_draws_are_not_route_upper": True,
            "new_child_discovery_draws_per_row": (
                caps.new_child_discovery_draws_per_row
            ),
            "new_child_validation_draws_per_row": (
                caps.new_child_validation_draws_per_row
            ),
            "maximum_new_child_action_rows": (
                caps.maximum_new_child_action_rows
            ),
            "maximum_dynamic_child_discovery_draws": (
                child_discovery_upper
            ),
            "maximum_dynamic_child_validation_draws": (
                child_validation_upper
                if arm is not DIRECT_ARM
                else 0
            ),
            "maximum_dynamic_promotion_draws": (
                dynamic_promotion_upper
                if arm is not DIRECT_ARM
                else 0
            ),
            "maximum_selected_rows_per_adaptive_round": (
                MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND
            ),
            "adaptive_round_selection_rule": (
                ADAPTIVE_ROUND_SELECTION_RULE
            ),
            "maximum_incremental_draws_per_adaptive_arm": (
                caps.maximum_incremental_draws_per_adaptive_arm
            ),
            "direct_maximum_validation_checkpoint": (
                caps.direct_validation_checkpoints[-1]
            ),
            "direct_maximum_validation_rows": (
                root_row_count + caps.maximum_new_child_action_rows
                if arm is DIRECT_ARM
                else 0
            ),
            "direct_maximum_validation_draws": (
                direct_validation_upper if arm is DIRECT_ARM else 0
            ),
            "sound_route_draw_upper": self.sound_route_draw_upper,
            "sound_route_draw_upper_formula": (
                "INITIAL_COMMITTED+ADAPTIVE_INCREMENTAL_CAP"
                if arm is not DIRECT_ARM
                else (
                    "ROOT_DISCOVERY+MAX_CHILD_ROWS*CHILD_DISCOVERY"
                    "+(ROOT_ROWS+MAX_CHILD_ROWS)*MAX_DIRECT_CHECKPOINT"
                )
            ),
            "threshold_profile_id": self.occurrence.threshold_profile_id,
            "cap_profile_id": self.occurrence.cap_profile_id,
            "support_selection_rule": SUPPORT_SELECTION_RULE,
            "support_promotion_rule": SUPPORT_PROMOTION_RULE,
            "maximum_adaptive_rounds": caps.maximum_adaptive_rounds,
            "direct_validation_checkpoints": list(
                caps.direct_validation_checkpoints
            ),
            "direct_child_expansion_rule": (
                DIRECT_CHILD_EXPANSION_RULE if arm is DIRECT_ARM else None
            ),
            "direct_checkpoint_rule": (
                DIRECT_CHECKPOINT_RULE if arm is DIRECT_ARM else None
            ),
            "direct_child_catalogues_present": False,
            "direct_child_rows_present": False,
            "complete_root_action_catalogue": True,
            "frozen_before_target_access": True,
            **_zero_access_payload(),
        }

    @property
    def schedule_id(self) -> str:
        return self._schedule_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "profile": self.profile.to_document(),
            "occurrence": self.occurrence.to_document(),
            "proposal_view": (
                None
                if self.proposal_view is None
                else self.proposal_view.to_document()
            ),
            "intents": [item.to_document() for item in self.intents],
            "schedule_id": self.schedule_id,
        }


def _build_initial_intents(
    *,
    profile: V075FiveArmAcquisitionProfileV2,
    occurrence: identity_backend.V075BatchNativeOccurrenceIdentityV1,
    proposal_view: V075ProposalViewV2 | None,
) -> tuple[V075InitialRowIntentV2, ...]:
    namespace = profile.namespace
    context = _context_by_id(namespace, occurrence.context_id)
    catalogue = graph.root_catalogue_v1(context)
    bindings = tuple(
        graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
        )
        for action in catalogue.actions
    )
    caps = namespace.workload.cap_profile
    discoveries = tuple(
        V075InitialRowIntentV2(
            _INTENT_ISSUER,
            profile,
            occurrence,
            proposal_view,
            _proposal_use_rule(occurrence.arm),
            occurrence.target_tape_namespace_id,
            occurrence.occurrence_id,
            occurrence.arm,
            binding,
            row_ordinal,
            row_ordinal,
            V075InitialIntentKindV2.ROOT_DISCOVERY,
            0,
            1,
            caps.initial_discovery_draws_per_row,
            caps.initial_discovery_draws_per_row,
            (),
            caps.cap_profile_id,
        )
        for row_ordinal, binding in enumerate(bindings)
    )
    promotion_offset = len(discoveries)
    promotions = tuple(
        V075InitialRowIntentV2(
            _INTENT_ISSUER,
            profile,
            occurrence,
            proposal_view,
            _proposal_use_rule(occurrence.arm),
            occurrence.target_tape_namespace_id,
            occurrence.occurrence_id,
            occurrence.arm,
            binding,
            promotion_offset + row_ordinal,
            row_ordinal,
            V075InitialIntentKindV2.SUPPORT_PROMOTION_TEMPLATE,
            None,
            None,
            0,
            0,
            (discovery.intent_id,),
            caps.cap_profile_id,
        )
        for row_ordinal, (binding, discovery) in enumerate(
            zip(bindings, discoveries)
        )
    )
    if occurrence.arm is DIRECT_ARM:
        return (*discoveries, *promotions)
    validation_offset = len(discoveries) + len(promotions)
    validations = tuple(
        V075InitialRowIntentV2(
            _INTENT_ISSUER,
            profile,
            occurrence,
            proposal_view,
            _proposal_use_rule(occurrence.arm),
            occurrence.target_tape_namespace_id,
            occurrence.occurrence_id,
            occurrence.arm,
            binding,
            validation_offset + row_ordinal,
            row_ordinal,
            V075InitialIntentKindV2.ROOT_VALIDATION,
            1,
            1,
            caps.initial_validation_draws_per_row,
            (
                caps.initial_validation_draws_per_row
                + caps.maximum_adaptive_rounds
                * caps.promotion_validation_draws_per_round
            ),
            (promotion.intent_id,),
            caps.cap_profile_id,
        )
        for row_ordinal, (binding, promotion) in enumerate(
            zip(bindings, promotions)
        )
    )
    return (*discoveries, *promotions, *validations)


def freeze_v075_occurrence_initial_acquisition_schedule_v2(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    occurrence: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
) -> V075InitialAcquisitionScheduleV2:
    replayed, _transport = _replay_occurrence(
        repository_root=repository_root,
        namespace=namespace,
        occurrence=occurrence,
    )
    profile = freeze_v075_five_arm_acquisition_profile_v2(
        namespace=namespace
    )
    proposal = freeze_v075_occurrence_proposal_view_v2(
        repository_root=repository_root,
        namespace=namespace,
        occurrence=replayed,
    )
    return V075InitialAcquisitionScheduleV2(
        _SCHEDULE_ISSUER,
        profile,
        replayed,
        proposal,
        _proposal_use_rule(replayed.arm),
        _build_initial_intents(
            profile=profile,
            occurrence=replayed,
            proposal_view=proposal,
        ),
    )


def replay_v075_initial_acquisition_schedule_v2(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    claimed: V075InitialAcquisitionScheduleV2,
) -> V075InitialAcquisitionScheduleV2:
    if type(claimed) is not V075InitialAcquisitionScheduleV2:
        _fail("schedule replay requires one exact typed claim")
    try:
        expected = freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=repository_root,
            namespace=namespace,
            occurrence=claimed.occurrence,
        )
        if (
            claimed.schedule_id != expected.schedule_id
            or claimed.canonical_bytes != expected.canonical_bytes
        ):
            _fail("typed schedule differs from exact semantic replay")
    except (
        AttributeError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        if type(error) is V075FiveArmAcquisitionAuthorityV2InvariantViolation:
            raise
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "typed schedule semantic replay failed"
        ) from error
    return expected


@dataclass(frozen=True, slots=True)
class V075InitialAcquisitionVerificationV2:
    """Canonical-byte replay proof for one static schedule."""

    _issuer: object = field(repr=False, compare=False)
    schedule: V075InitialAcquisitionScheduleV2 = field(repr=False)
    expected_slot: V075PreregisteredOccurrenceSlotV2 = field(repr=False)
    schedule_bytes_sha256: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.schedule_bytes_sha256, "verification byte digest")
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.schedule) is not V075InitialAcquisitionScheduleV2
            or type(self.expected_slot)
            is not V075PreregisteredOccurrenceSlotV2
        ):
            _fail("initial acquisition verification is caller-minted")
        try:
            replayed = V075InitialAcquisitionScheduleV2(
                _SCHEDULE_ISSUER,
                self.schedule.profile,
                self.schedule.occurrence,
                self.schedule.proposal_view,
                self.schedule.proposal_use_rule,
                self.schedule.intents,
            )
        except Exception as error:
            raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
                "verification schedule semantic replay failed"
            ) from error
        expected_slot = self.schedule.profile.occurrence_slot_for(
            context_id=self.schedule.occurrence.context_id,
            arm=self.schedule.occurrence.arm,
        )
        if (
            replayed.canonical_bytes != self.schedule.canonical_bytes
            or self.expected_slot != expected_slot
            or self.schedule_bytes_sha256
            != hashlib.sha256(self.schedule.canonical_bytes).hexdigest()
        ):
            _fail("verification witnesses differ from exact replay")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_five_arm_initial_acquisition_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "target_tape_namespace_id": (
                self.schedule.occurrence.target_tape_namespace_id
            ),
            "occurrence_id": self.schedule.occurrence.occurrence_id,
            "occurrence_slot_id": self.expected_slot.slot_id,
            "schedule_id": self.schedule.schedule_id,
            "schedule_bytes_sha256": self.schedule_bytes_sha256,
            "profile_id": self.schedule.profile.profile_id,
            "arm": self.schedule.occurrence.arm.value,
            "canonical_bytes_exact": True,
            "namespace_replayed": True,
            "occurrence_replayed": True,
            "source_authority_replayed_if_required": True,
            "all_unknown_fields_rejected": True,
            "frozen_before_target_access": True,
            **_zero_access_payload(),
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_v075_initial_acquisition_verification_bytes_v2(
    *,
    schedule: V075InitialAcquisitionScheduleV2,
    expected_slot: V075PreregisteredOccurrenceSlotV2,
    raw: bytes,
) -> V075InitialAcquisitionVerificationV2:
    """Reconstruct a typed verification from its exact schedule witnesses."""

    document = _strict_load(
        raw,
        cap=MAX_ARTIFACT_BYTES,
        field_name="initial acquisition verification",
    )
    expected = V075InitialAcquisitionVerificationV2(
        _VERIFICATION_ISSUER,
        schedule,
        expected_slot,
        hashlib.sha256(schedule.canonical_bytes).hexdigest(),
    )
    if (
        set(document) != set(expected.to_document())
        or raw != expected.canonical_bytes
    ):
        _fail("initial acquisition verification differs from exact replay")
    return expected


def _load_occurrence_bytes(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    profile: V075FiveArmAcquisitionProfileV2,
    expected_slot: V075PreregisteredOccurrenceSlotV2,
    raw: bytes,
) -> identity_backend.V075BatchNativeOccurrenceIdentityV1:
    replayed_profile = _replay_profile(profile)
    if (
        type(profile) is not V075FiveArmAcquisitionProfileV2
        or replayed_profile.canonical_bytes != profile.canonical_bytes
        or type(expected_slot) is not V075PreregisteredOccurrenceSlotV2
        or expected_slot not in profile.occurrence_slots
    ):
        _fail("occurrence loader lacks one preregistered typed slot")
    document = _strict_load(
        raw,
        cap=MAX_OCCURRENCE_IDENTITY_BYTES,
        field_name="occurrence identity",
    )
    expected_arm = expected_slot.arm
    if (
        document.get("arm") != expected_arm.value
    ):
        _fail(
            "occurrence arm differs from trusted preregistered arm before "
            "any source access"
        )
    expected_ordinal = expected_slot.occurrence_ordinal
    expected_source_presence = (
        expected_arm
        is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
    )
    if (
        document.get("occurrence_ordinal") != expected_ordinal
        or document.get("context_id") != expected_slot.context_id
        or document.get("target_tape_namespace_id")
        != namespace.target_tape_namespace_id
        or document.get("threshold_profile_id")
        != namespace.workload.threshold_profile.threshold_profile_id
        or document.get("cap_profile_id")
        != namespace.workload.cap_profile.cap_profile_id
        or (document.get("source_transport_id") is not None)
        != expected_source_presence
    ):
        _fail(
            "occurrence skeleton is not the context-major preregistered "
            "identity"
        )
    try:
        skeleton = identity_backend.V075BatchNativeOccurrenceIdentityV1(
            identity_backend._OCCURRENCE_IDENTITY_ISSUER,  # type: ignore[attr-defined]
            namespace.target_tape_namespace_id,
            document["context_id"],
            expected_arm,
            expected_ordinal,
            namespace.workload.threshold_profile.threshold_profile_id,
            namespace.workload.cap_profile.cap_profile_id,
            document["source_transport_id"],
        )
    except Exception as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "occurrence skeleton semantic reconstruction failed"
        ) from error
    if raw != canonical_json_bytes(skeleton.to_document()):
        _fail(
            "occurrence skeleton fields, content ID, or canonical bytes "
            "changed before source access"
        )
    if expected_source_presence:
        transport = _load_tracked_source_transport(repository_root)
        source_bytes = _transport_bytes(transport)
    else:
        source_bytes = None
    try:
        return (
            identity_backend
            .load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
                repository_root=repository_root,
                namespace=namespace,
                raw=raw,
                expected_arm=expected_arm,
                source_prior_transport_bytes=source_bytes,
            )
        )
    except Exception as error:
        raise V075FiveArmAcquisitionAuthorityV2InvariantViolation(
            "occurrence identity bytes failed exact namespace replay"
        ) from error


def verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
    *,
    repository_root: str | Path,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    expected_slot: V075PreregisteredOccurrenceSlotV2,
    occurrence_identity_bytes: bytes,
    raw: bytes,
) -> tuple[
    V075InitialAcquisitionScheduleV2,
    V075InitialAcquisitionVerificationV2,
]:
    """Rebuild and byte-verify one occurrence's complete static authority."""

    exact_namespace = _replay_namespace(namespace)
    profile = freeze_v075_five_arm_acquisition_profile_v2(
        namespace=exact_namespace
    )
    occurrence = _load_occurrence_bytes(
        repository_root=repository_root,
        namespace=exact_namespace,
        profile=profile,
        expected_slot=expected_slot,
        raw=occurrence_identity_bytes,
    )
    document = _strict_load(
        raw,
        cap=MAX_ARTIFACT_BYTES,
        field_name="initial acquisition schedule",
    )
    expected = freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=repository_root,
        namespace=exact_namespace,
        occurrence=occurrence,
    )
    expected_document = expected.to_document()
    if (
        set(document) != set(expected_document)
        or raw != expected.canonical_bytes
    ):
        _fail("initial acquisition schedule differs from exact replay")
    verification = V075InitialAcquisitionVerificationV2(
        _VERIFICATION_ISSUER,
        expected,
        expected_slot,
        hashlib.sha256(raw).hexdigest(),
    )
    return expected, verification


__all__ = [
    "ADAPTIVE_ARM_ORDER",
    "ADAPTIVE_ROUND_SELECTION_RULE",
    "ARM_ORDER",
    "DIRECT_ARM",
    "DIRECT_CHECKPOINT_RULE",
    "DIRECT_CHILD_EXPANSION_RULE",
    "DOMAIN_TAGS",
    "MAX_ARTIFACT_BYTES",
    "MAX_SELECTED_ROWS_PER_ADAPTIVE_ROUND",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OOD_INCOMPATIBLE_FEATURE_SCHEMA_ID",
    "PROFILE_KEY",
    "PROPOSAL_USE_RULES",
    "PRODUCTION_AUTHORIZING",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_FORWARD_MIDRANKS",
    "REGISTERED_WRONG_REVERSED_MIDRANKS",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SOURCE_ADAPTER_ID",
    "SOURCE_CATALOGUE_ID",
    "SOURCE_FEATURE_SCHEMA_ID",
    "SOURCE_TRANSPORT_BYTES_SHA256",
    "SOURCE_TRANSPORT_ID",
    "SOURCE_VERIFICATION_ID",
    "SUPPORT_PROMOTION_RULE",
    "SUPPORT_SELECTION_RULE",
    "TARGET_ACCESS_ALLOWED",
    "V075AcquisitionRouteV2",
    "V075ArmRegistrationV2",
    "V075FiveArmAcquisitionAuthorityV2InvariantViolation",
    "V075FiveArmAcquisitionProfileV2",
    "V075InitialAcquisitionScheduleV2",
    "V075InitialAcquisitionVerificationV2",
    "V075InitialIntentKindV2",
    "V075InitialRowIntentV2",
    "V075ProposalDispositionV2",
    "V075ProposalViewV2",
    "V075PreregisteredOccurrenceSlotV2",
    "V075TrackedSourceProposalProvenanceV2",
    "WRONG_FIXED_CONTROL_ID",
    "freeze_v075_five_arm_acquisition_profile_v2",
    "freeze_v075_occurrence_initial_acquisition_schedule_v2",
    "freeze_v075_occurrence_proposal_view_v2",
    "replay_v075_initial_acquisition_schedule_v2",
    "verify_v075_five_arm_acquisition_profile_bytes_v2",
    "verify_v075_initial_acquisition_verification_bytes_v2",
    "verify_v075_occurrence_initial_acquisition_schedule_bytes_v2",
]
