"""Batch-native statistical backend adapter for production V0-075.

One verified signed batch remains one artifact throughout this component.
Accepted-draw counts and public outcome aggregates are projected directly
into statistical rows; no per-draw ``ObservationCapability`` objects are
materialized.

The adapter consumes exact typed public batch, public-verification, and
contiguous-sequence objects.  It preserves row/action/catalogue, arm, lane,
epoch, support-chain, pairing-group, stream, observer-open, namespace, and
route-cap identities.  Discovery outcomes provide the observed candidate
support.  The latest validation support epoch freezes a possibly strict
subset of that discovery support; every validation outcome outside the
frozen subset is counted in the single ``OTHER`` event.

Only public aggregates are read.  No private environment, law, reveal, salt,
kernel, random word, signer, observer session, callback, cache, or resume
object is accepted by the API.  Exact private batch replay remains a
standalone authority upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    parse_content_id,
)
from acfqp.sequential_bernoulli_acquisition_v1 import (
    SequentialBernoulliProfileV1,
    build_anytime_bernoulli_checkpoint_v1,
)
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_batch_native_statistical_backend_v1"
PRODUCTION_INTEGRATION_READY = False
PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False

DOMAIN_TAGS = {
    "occurrence": "acfqp:v075-batch-native-occurrence:v1",
    "request": "acfqp:v075-batch-native-backend-request:v1",
    "counter": "acfqp:v075-batch-native-backend-counter:v1",
    "work": "acfqp:v075-batch-native-backend-work:v1",
    "result": "acfqp:v075-batch-native-backend-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 batch-native backend domains must be unique")


class V075BatchNativeBackendInvariantViolation(ValueError):
    """A batch, sequence, route, support, interval, or identity is invalid."""


def _fail(message: str) -> None:
    raise V075BatchNativeBackendInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchNativeBackendInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchNativeBackendInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _is_exact_public_target_namespace_v1_or_v2(value: Any) -> bool:
    """Accept only one registered concrete namespace generation.

    The V2 import is intentionally lazy: the V2 namespace freezes the
    production runner, whose dependency graph reaches this backend.  A
    module-level import would therefore create a namespace/runner/backend
    cycle.  Exact ``type`` checks reject subclasses and duck-typed claim
    projections.
    """

    if type(value) is public_authority.V075PublicTargetTapeNamespaceV1:
        return True
    try:
        from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
    except ImportError:
        return False
    if type(value) is not namespace_v2.V075PublicTargetTapeNamespaceV2:
        return False
    try:
        return (
            value.family
            == public_authority.freeze_v075_public_family_generation_v1()
            and type(value.signer_registry)
            is public_authority.V075TrustedSignerRegistryV1
            and value.signer_registry == value.anchor.signer_registry
            and _cid(
                value.target_tape_namespace_id,
                "V2 occurrence target namespace",
            )
            == value.target_tape_namespace_id
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("batch-native arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _batch_order_key(
    item: batched.V075SignedBatchedObservationV1,
) -> tuple[str, int, int]:
    return (
        item.request.stream_identity.stream_id,
        item.request.accepted_draw_start,
        item.request.accepted_draw_end,
    )


def _sequence_order_key(
    item: batched.V075BatchedObservationSequenceVerificationV1,
) -> str:
    return item.stream_id


_OCCURRENCE_IDENTITY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchNativeOccurrenceIdentityV1:
    """Law-free occurrence identity frozen before the first target draw."""

    _issuer: object = field(repr=False, compare=False)
    target_tape_namespace_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    occurrence_ordinal: int
    threshold_profile_id: str
    cap_profile_id: str
    source_transport_id: str | None
    _occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (
                self.target_tape_namespace_id,
                "occurrence identity target namespace",
            ),
            (self.context_id, "occurrence identity context"),
            (
                self.threshold_profile_id,
                "occurrence identity threshold profile",
            ),
            (self.cap_profile_id, "occurrence identity cap profile"),
        ):
            _cid(value, label)
        if self.source_transport_id is not None:
            _cid(
                self.source_transport_id,
                "occurrence identity source transport",
            )
        if (
            self._issuer is not _OCCURRENCE_IDENTITY_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal < 0
            or (
                self.source_transport_id is not None
            )
            != (
                self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            )
        ):
            _fail("pre-sampling occurrence identity is malformed")
        object.__setattr__(
            self,
            "_occurrence_id",
            _hash("occurrence", self._identity_payload()),
        )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_native_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "occurrence_ordinal": self.occurrence_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "cap_profile_id": self.cap_profile_id,
            "source_transport_id": self.source_transport_id,
        }

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "occurrence_id": self.occurrence_id,
            "frozen_before_observation": True,
            "batch_count_at_freeze": 0,
            "observer_calls": 0,
            "kernel_calls": 0,
            "target_accessed": False,
            "private_material_serialized": False,
        }


def freeze_v075_batch_native_occurrence_identity_v1(
    *,
    namespace: Any,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    threshold_profile: worker.V075WorkerThresholdProfileV1,
    cap_profile: worker.V075WorkerCapProfileV1,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
) -> V075BatchNativeOccurrenceIdentityV1:
    """Freeze the exact occurrence identity without accepting observations."""

    if (
        not _is_exact_public_target_namespace_v1_or_v2(namespace)
        or type(context)
        is not public_authority.V075PublicReplicateContextV1
        or context
        not in namespace.family.replicate_contexts
        or type(arm) is not worker.V075WorkerArmV1
        or type(occurrence_ordinal) is not int
        or occurrence_ordinal < 0
        or type(threshold_profile)
        is not worker.V075WorkerThresholdProfileV1
        or type(cap_profile) is not worker.V075WorkerCapProfileV1
        or (
            source_prior_transport is not None
            and type(source_prior_transport)
            is not worker.V075SourcePriorTransportV1
        )
        or (
            source_prior_transport is not None
        )
        != (arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR)
    ):
        _fail(
            "occurrence identity inputs are untyped, transplanted, or "
            "inconsistent with the arm"
        )
    return V075BatchNativeOccurrenceIdentityV1(
        _OCCURRENCE_IDENTITY_ISSUER,
        namespace.target_tape_namespace_id,
        context.context_id,
        arm,
        occurrence_ordinal,
        threshold_profile.threshold_profile_id,
        cap_profile.cap_profile_id,
        (
            None
            if source_prior_transport is None
            else source_prior_transport.transport_id
        ),
    )


def freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
    *,
    namespace: Any,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    threshold_profile: worker.V075WorkerThresholdProfileV1,
    cap_profile: worker.V075WorkerCapProfileV1,
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
) -> V075BatchNativeOccurrenceIdentityV1:
    """Freeze a V1 occurrence artifact directly from one exact V2 namespace.

    This is an explicit migration entry point, not a V2-to-V1 authority
    projection: the occurrence artifact stores only the opaque namespace
    content ID and never synthesizes historical external claims.
    """

    try:
        from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2
    except ImportError as error:  # pragma: no cover - deployment corruption
        raise V075BatchNativeBackendInvariantViolation(
            "public target namespace V2 authority is unavailable"
        ) from error
    if type(namespace) is not namespace_v2.V075PublicTargetTapeNamespaceV2:
        _fail("V2 occurrence factory requires one exact V2 namespace")
    return freeze_v075_batch_native_occurrence_identity_v1(
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=occurrence_ordinal,
        threshold_profile=threshold_profile,
        cap_profile=cap_profile,
        source_prior_transport=source_prior_transport,
    )


def replay_v075_batch_native_occurrence_identity_v1(
    claimed: V075BatchNativeOccurrenceIdentityV1,
) -> V075BatchNativeOccurrenceIdentityV1:
    """Reconstruct one occurrence identity instead of trusting its object graph.

    Exact ``type`` alone is insufficient because an object created through
    ``object.__new__`` can carry forged cached IDs or hidden fields.  Every
    consumer trust boundary must use the returned reconstruction.
    """

    if type(claimed) is not V075BatchNativeOccurrenceIdentityV1:
        _fail("occurrence identity replay requires one exact typed claim")
    try:
        replayed = V075BatchNativeOccurrenceIdentityV1(
            _OCCURRENCE_IDENTITY_ISSUER,
            claimed.target_tape_namespace_id,
            claimed.context_id,
            claimed.arm,
            claimed.occurrence_ordinal,
            claimed.threshold_profile_id,
            claimed.cap_profile_id,
            claimed.source_transport_id,
        )
        if (
            replayed.occurrence_id != claimed.occurrence_id
            or canonical_json_bytes(replayed.to_document())
            != canonical_json_bytes(claimed.to_document())
        ):
            _fail(
                "occurrence identity fields, content ID, or document differ "
                "from exact replay"
            )
    except (
        AttributeError,
        TypeError,
        ValueError,
        Phase3EIdentityError,
    ) as error:
        if type(error) is V075BatchNativeBackendInvariantViolation:
            raise
        raise V075BatchNativeBackendInvariantViolation(
            "occurrence identity semantic replay failed"
        ) from error
    return replayed


@dataclass(frozen=True, slots=True)
class V075BatchNativeBackendRequestV1:
    arm: worker.V075WorkerArmV1
    occurrence_ordinal: int
    batches: tuple[batched.V075SignedBatchedObservationV1, ...]
    public_verifications: tuple[
        batched.V075BatchedObservationPublicVerificationV1,
        ...,
    ]
    sequence_verifications: tuple[
        batched.V075BatchedObservationSequenceVerificationV1,
        ...,
    ]
    threshold_profile: worker.V075WorkerThresholdProfileV1
    cap_profile: worker.V075WorkerCapProfileV1
    source_prior_transport: worker.V075SourcePriorTransportV1 | None
    occurrence_identity: V075BatchNativeOccurrenceIdentityV1

    def __post_init__(self) -> None:
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal < 0
            or type(self.batches) is not tuple
            or not self.batches
            or any(
                type(item) is not batched.V075SignedBatchedObservationV1
                for item in self.batches
            )
            or self.batches
            != tuple(sorted(self.batches, key=_batch_order_key))
            or len({item.batch_id for item in self.batches})
            != len(self.batches)
            or type(self.public_verifications) is not tuple
            or any(
                type(item)
                is not batched.V075BatchedObservationPublicVerificationV1
                for item in self.public_verifications
            )
            or self.public_verifications
            != tuple(
                sorted(
                    self.public_verifications,
                    key=lambda item: item.batch_id,
                )
            )
            or type(self.sequence_verifications) is not tuple
            or any(
                type(item)
                is not batched.V075BatchedObservationSequenceVerificationV1
                for item in self.sequence_verifications
            )
            or self.sequence_verifications
            != tuple(
                sorted(
                    self.sequence_verifications,
                    key=_sequence_order_key,
                )
            )
            or type(self.threshold_profile)
            is not worker.V075WorkerThresholdProfileV1
            or type(self.cap_profile) is not worker.V075WorkerCapProfileV1
            or type(self.occurrence_identity)
            is not V075BatchNativeOccurrenceIdentityV1
        ):
            _fail("batch-native request is untyped or noncanonical")
        replay_v075_batch_native_occurrence_identity_v1(
            self.occurrence_identity
        )
        first = self.batches[0].request
        first_stream = first.stream_identity
        if any(
            (
                item.request.stream_identity.target_tape_namespace_id,
                item.request.stream_identity.context_id,
                item.request.stream_identity.arm,
                item.request.session_public_id,
                item.request.observer_open_binding.binding_id,
                item.request.authority_scope,
            )
            != (
                first_stream.target_tape_namespace_id,
                first_stream.context_id,
                self.arm.value,
                first.session_public_id,
                first.observer_open_binding.binding_id,
                first.authority_scope,
            )
            for item in self.batches
        ):
            _fail("batch-native request mixes namespace/context/arm/session")
        public_by_batch = {
            item.batch_id: item for item in self.public_verifications
        }
        if (
            len(public_by_batch) != len(self.public_verifications)
            or set(public_by_batch)
            != {item.batch_id for item in self.batches}
        ):
            _fail("public batch-verification registry is incomplete")
        for item in self.batches:
            replayed = batched.verify_v075_signed_batched_observation_v1(
                item
            )
            if public_by_batch[item.batch_id] != replayed:
                _fail("public batch verification differs from semantic replay")
        grouped = self.batches_by_stream
        sequence_by_stream = {
            item.stream_id: item for item in self.sequence_verifications
        }
        if (
            len(sequence_by_stream) != len(self.sequence_verifications)
            or set(sequence_by_stream) != set(grouped)
        ):
            _fail("batch sequence-verification registry is incomplete")
        for stream_id, values in grouped.items():
            replayed = batched.verify_v075_batched_observation_sequence_v1(
                values
            )
            if sequence_by_stream[stream_id] != replayed:
                _fail("batch sequence verification differs from exact replay")
        if self.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            if type(self.source_prior_transport) is not worker.V075SourcePriorTransportV1:
                _fail("SOURCE batch-native route lacks verified source transport")
        elif self.source_prior_transport is not None:
            _fail("non-SOURCE batch-native route received source payload")
        if (
            self.occurrence_identity.target_tape_namespace_id
            != first_stream.target_tape_namespace_id
            or self.occurrence_identity.context_id
            != first_stream.context_id
            or self.occurrence_identity.arm is not self.arm
            or self.occurrence_identity.occurrence_ordinal
            != self.occurrence_ordinal
            or self.occurrence_identity.threshold_profile_id
            != self.threshold_profile.threshold_profile_id
            or self.occurrence_identity.cap_profile_id
            != self.cap_profile.cap_profile_id
            or self.occurrence_identity.source_transport_id
            != (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.transport_id
            )
        ):
            _fail(
                "batch-native request differs from its pre-sampling "
                "occurrence identity"
            )
        _validate_route_caps(self)

    @property
    def namespace(self):
        return self.batches[0].request.stream_identity.namespace

    @property
    def context(self):
        return self.batches[0].request.stream_identity.row_binding.context

    @property
    def authority_scope(self) -> batched.V075BatchAuthorityScopeV1:
        return self.batches[0].request.authority_scope

    @property
    def route(self) -> worker.V075WorkerRouteV1:
        return (
            worker.V075WorkerRouteV1.MATCHED_DIRECT_GROUND
            if self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            else worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
        )

    @property
    def batches_by_stream(
        self,
    ) -> dict[str, tuple[batched.V075SignedBatchedObservationV1, ...]]:
        result: dict[
            str,
            list[batched.V075SignedBatchedObservationV1],
        ] = {}
        for item in self.batches:
            result.setdefault(
                item.request.stream_identity.stream_id,
                [],
            ).append(item)
        return {
            key: tuple(sorted(values, key=_batch_order_key))
            for key, values in result.items()
        }

    @property
    def occurrence_id(self) -> str:
        return self.occurrence_identity.occurrence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_native_backend_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "occurrence_identity_id": (
                self.occurrence_identity.occurrence_id
            ),
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "context_id": self.context.context_id,
            "arm": self.arm.value,
            "route": self.route.value,
            "occurrence_ordinal": self.occurrence_ordinal,
            "authority_scope": self.authority_scope.value,
            "batch_ids": [item.batch_id for item in self.batches],
            "public_verification_ids": [
                item.verification_id for item in self.public_verifications
            ],
            "sequence_verification_ids": [
                item.verification_id for item in self.sequence_verifications
            ],
            "threshold_profile_id": self.threshold_profile.threshold_profile_id,
            "cap_profile_id": self.cap_profile.cap_profile_id,
            "source_transport_id": (
                None
                if self.source_prior_transport is None
                else self.source_prior_transport.transport_id
            ),
            "per_draw_capability_expansion_allowed": False,
            "private_material_serialized": False,
        }

    @property
    def request_id(self) -> str:
        return _hash("request", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


def _validate_route_caps(request: V075BatchNativeBackendRequestV1) -> None:
    grouped = request.batches_by_stream
    discovery_records: list[
        tuple[public_graph.V075TransitionStreamIdentityV1, int, int]
    ] = []
    validation_records: list[
        tuple[public_graph.V075TransitionStreamIdentityV1, int, int]
    ] = []
    row_ids: set[str] = set()
    child_row_ids: set[str] = set()
    for values in grouped.values():
        stream = values[0].request.stream_identity
        count = sum(item.request.accepted_draw_count for item in values)
        accepted_cap = values[0].request.accepted_draw_cap
        row_ids.add(stream.row_binding_id)
        if stream.row_binding.remaining_horizon == 1:
            child_row_ids.add(stream.row_binding_id)
        if stream.lane is public_graph.V075ObservationLaneV1.DISCOVERY:
            discovery_records.append((stream, count, accepted_cap))
            if stream.observer_epoch_index != 0:
                _fail("discovery stream must be observer epoch zero")
        else:
            validation_records.append((stream, count, accepted_cap))
            if stream.observer_epoch_index <= 0:
                _fail("validation stream must follow discovery")
    caps = request.cap_profile
    if any(
        count
        not in {
            caps.initial_discovery_draws_per_row,
            caps.new_child_discovery_draws_per_row,
        }
        or accepted_cap != count
        for _stream, count, accepted_cap in discovery_records
    ):
        _fail("batch discovery sequence is outside registered draw caps")
    if request.route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT:
        root_validation_cap = (
            caps.initial_validation_draws_per_row
            + caps.maximum_adaptive_rounds
            * caps.promotion_validation_draws_per_round
        )
        child_validation_cap = (
            caps.new_child_validation_draws_per_row
            + caps.maximum_adaptive_rounds
            * caps.promotion_validation_draws_per_round
        )
        for stream, count, accepted_cap in validation_records:
            if stream.row_binding.remaining_horizon == 2:
                base = caps.initial_validation_draws_per_row
                hard_cap = root_validation_cap
            else:
                base = caps.new_child_validation_draws_per_row
                hard_cap = child_validation_cap
            allowed = {
                base
                + round_index * caps.promotion_validation_draws_per_round
                for round_index in range(caps.maximum_adaptive_rounds + 1)
            }
            if count not in allowed or accepted_cap != hard_cap:
                _fail(
                    "adaptive validation prefix or hard cap is outside the "
                    "registered cumulative schedule"
                )
        incremental_draws = sum(
            count
            for stream, count, _cap in discovery_records
            if stream.row_binding.remaining_horizon == 1
        )
        incremental_draws += sum(
            (
                count - caps.initial_validation_draws_per_row
                if (
                    stream.row_binding.remaining_horizon == 2
                    and stream.observer_epoch_index == 1
                )
                else count
            )
            for stream, count, _cap in validation_records
        )
        if (
            incremental_draws
            > caps.maximum_incremental_draws_per_adaptive_arm
            or len(child_row_ids) > caps.maximum_new_child_action_rows
        ):
            _fail("adaptive batch route exceeds draw or child-row hard cap")
    elif any(
        count not in caps.direct_validation_checkpoints
        or accepted_cap not in caps.direct_validation_checkpoints
        or count > accepted_cap
        for _stream, count, accepted_cap in validation_records
    ):
        _fail("direct validation sequence is outside registered checkpoints")
    if len(row_ids) > request.context.maximum_physical_rows_per_confidence_epoch:
        _fail("batch route exceeds the context physical-row cap")


def _adaptive_cap_charged_draws(
    request: V075BatchNativeBackendRequestV1,
) -> int:
    if request.route is not worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT:
        return 0
    caps = request.cap_profile
    total = 0
    for values in request.batches_by_stream.values():
        stream = values[0].request.stream_identity
        count = sum(item.request.accepted_draw_count for item in values)
        if (
            stream.row_binding.remaining_horizon == 2
            and stream.lane is public_graph.V075ObservationLaneV1.DISCOVERY
        ):
            continue
        if (
            stream.row_binding.remaining_horizon == 2
            and stream.lane is public_graph.V075ObservationLaneV1.VALIDATION
            and stream.observer_epoch_index == 1
        ):
            total += count - caps.initial_validation_draws_per_row
        else:
            total += count
    return total


def freeze_v075_batch_native_backend_request_v1(
    *,
    arm: worker.V075WorkerArmV1,
    occurrence_ordinal: int,
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    source_prior_transport: worker.V075SourcePriorTransportV1 | None = None,
    occurrence_identity: V075BatchNativeOccurrenceIdentityV1 | None = None,
) -> V075BatchNativeBackendRequestV1:
    """Reverify and freeze one canonical batch-native route request."""

    canonical_batches = tuple(sorted(batches, key=_batch_order_key))
    public_verifications = tuple(
        sorted(
            (
                batched.verify_v075_signed_batched_observation_v1(item)
                for item in canonical_batches
            ),
            key=lambda item: item.batch_id,
        )
    )
    grouped: dict[
        str,
        list[batched.V075SignedBatchedObservationV1],
    ] = {}
    for item in canonical_batches:
        grouped.setdefault(
            item.request.stream_identity.stream_id,
            [],
        ).append(item)
    sequences = tuple(
        sorted(
            (
                batched.verify_v075_batched_observation_sequence_v1(
                    tuple(sorted(values, key=_batch_order_key))
                )
                for values in grouped.values()
            ),
            key=_sequence_order_key,
        )
    )
    threshold_profile = worker.V075WorkerThresholdProfileV1()
    cap_profile = worker.V075WorkerCapProfileV1()
    if occurrence_identity is None:
        if not canonical_batches:
            _fail("batch-native backend request has no observation batches")
        first_stream = canonical_batches[0].request.stream_identity
        occurrence_identity = (
            freeze_v075_batch_native_occurrence_identity_v1(
                namespace=first_stream.namespace,
                context=first_stream.row_binding.context,
                arm=arm,
                occurrence_ordinal=occurrence_ordinal,
                threshold_profile=threshold_profile,
                cap_profile=cap_profile,
                source_prior_transport=source_prior_transport,
            )
        )
    elif type(occurrence_identity) is not V075BatchNativeOccurrenceIdentityV1:
        _fail("backend request rejects a duck-typed occurrence identity")
    return V075BatchNativeBackendRequestV1(
        arm,
        occurrence_ordinal,
        canonical_batches,
        public_verifications,
        sequences,
        threshold_profile,
        cap_profile,
        source_prior_transport,
        occurrence_identity,
    )


def _merge_reward(row_binding: public_graph.V075ObservationRowBindingV1) -> Fraction:
    state = row_binding.catalogue.state
    rank = state.ranks[row_binding.action[0]]
    context = row_binding.context
    return (
        Fraction(2 ** (rank + 1), 2 ** (context.rank_cap + 1))
        / context.horizon
    )


def _project_outcome(
    row_binding: public_graph.V075ObservationRowBindingV1,
    outcome: batched.V075BatchedPublicOutcomeAggregateV1,
) -> backend.V075OutcomeDescriptorV1:
    if (
        type(row_binding) is not public_graph.V075ObservationRowBindingV1
        or type(outcome) is not batched.V075BatchedPublicOutcomeAggregateV1
    ):
        _fail("batch outcome projection rejects duck-typed inputs")
    try:
        state = public_graph.V075SymbolicGraphStateV1(
            row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
    except public_graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075BatchNativeBackendInvariantViolation(str(error)) from error
    expected_terminal = (
        outcome.failure or row_binding.remaining_horizon == 1
    )
    if (
        outcome.terminal != expected_terminal
        or outcome.realized_row_reward != _merge_reward(row_binding)
        or outcome.reward_sum != outcome.realized_row_reward * outcome.count
    ):
        _fail("batch outcome terminal or deterministic reward semantics changed")
    return backend.V075OutcomeDescriptorV1(
        row_binding.context_id,
        state.state_id,
        state.ranks,
        state.failure,
        outcome.terminal,
        outcome.realized_row_reward,
    )


def _sequence_records(
    request: V075BatchNativeBackendRequestV1,
) -> dict[
    str,
    tuple[
        public_graph.V075TransitionStreamIdentityV1,
        tuple[batched.V075SignedBatchedObservationV1, ...],
    ],
]:
    result = {}
    for stream_id, values in request.batches_by_stream.items():
        stream = values[0].request.stream_identity
        if any(item.request.stream_identity != stream for item in values):
            _fail("one batch sequence mixes typed stream identities")
        result[stream_id] = (stream, values)
    return result


def _intervals_from_batches(
    *,
    row_binding: public_graph.V075ObservationRowBindingV1,
    support: tuple[backend.V075OutcomeDescriptorV1, ...],
    values: tuple[batched.V075SignedBatchedObservationV1, ...],
    route: worker.V075WorkerRouteV1,
    caps: worker.V075WorkerCapProfileV1,
) -> tuple[backend.V075EventIntervalV1, ...]:
    counts = {item.descriptor_id: 0 for item in support}
    other = 0
    draw_count = 0
    by_descriptor = {item.descriptor_id: item for item in support}
    for batch in values:
        draw_count += batch.request.accepted_draw_count
        for outcome in batch.outcomes:
            descriptor = _project_outcome(row_binding, outcome)
            if descriptor.descriptor_id in counts:
                counts[descriptor.descriptor_id] += outcome.count
            else:
                other += outcome.count
    if sum(counts.values()) + other != draw_count:
        _fail("batch outcome projection does not conserve accepted draws")
    if route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT:
        base = (
            caps.initial_validation_draws_per_row
            if row_binding.remaining_horizon == 2
            else caps.new_child_validation_draws_per_row
        )
        checkpoints = tuple(
            base + index * caps.promotion_validation_draws_per_round
            for index in range(caps.maximum_adaptive_rounds + 1)
        )
    else:
        checkpoints = caps.direct_validation_checkpoints
    event_count = len(support) + 1
    canonical_checkpoints = tuple(sorted(set(checkpoints)))
    result: list[backend.V075EventIntervalV1] = []
    for event_key, success_count in (
        *((item.descriptor_id, counts[item.descriptor_id]) for item in support),
        ("OTHER", other),
    ):
        checkpoint = _cached_checkpoint(
            draw_count,
            success_count,
            event_count,
            canonical_checkpoints,
        )
        result.append(
            backend.V075EventIntervalV1(
                event_key,
                None if event_key == "OTHER" else by_descriptor[event_key],
                draw_count,
                success_count,
                checkpoint.empirical_probability,
                checkpoint.lower_probability,
                checkpoint.upper_probability,
                checkpoint.exact_likelihood_comparisons,
                checkpoint.log_search_evaluations,
            )
        )
    return tuple(result)


@lru_cache(maxsize=512)
def _cached_checkpoint(
    draw_count: int,
    success_count: int,
    event_count: int,
    checkpoints: tuple[int, ...],
):
    """Reuse identical exact CS obligations without changing arithmetic."""

    profile = SequentialBernoulliProfileV1(
        confidence_alpha=backend.ROW_EPOCH_BETA / event_count,
        target_half_width=backend.TARGET_HALF_WIDTH,
        checkpoints=checkpoints,
        boundary_grid_bits=backend.BOUNDARY_GRID_BITS,
    )
    return build_anytime_bernoulli_checkpoint_v1(
        draw_count,
        success_count,
        profile,
    )


def _compile_rows(
    request: V075BatchNativeBackendRequestV1,
) -> tuple[
    tuple[backend.V075StatisticalRowV1, ...],
    tuple[str, ...],
    int,
]:
    records = _sequence_records(request)
    by_row: dict[
        str,
        list[
            tuple[
                public_graph.V075TransitionStreamIdentityV1,
                tuple[batched.V075SignedBatchedObservationV1, ...],
            ]
        ],
    ] = {}
    for stream, values in records.values():
        by_row.setdefault(stream.row_binding_id, []).append((stream, values))
    rows: list[backend.V075StatisticalRowV1] = []
    selected_batch_ids: set[str] = set()
    superseded_validation_draws = 0
    for row_binding_id in sorted(by_row):
        values = by_row[row_binding_id]
        discovery = tuple(
            item
            for item in values
            if item[0].lane is public_graph.V075ObservationLaneV1.DISCOVERY
        )
        validations = tuple(
            sorted(
                (
                    item
                    for item in values
                    if item[0].lane
                    is public_graph.V075ObservationLaneV1.VALIDATION
                ),
                key=lambda item: item[0].observer_epoch_index,
            )
        )
        if len(discovery) != 1 or not validations:
            _fail("each learned row requires one discovery and validation")
        discovery_stream, discovery_batches = discovery[0]
        epochs = tuple(item[0].observer_epoch_index for item in validations)
        if epochs != tuple(range(1, epochs[-1] + 1)):
            _fail("row validation support epochs are gapped or duplicated")
        if any(
            item[0].row_binding != discovery_stream.row_binding
            or item[0].pairing_authority.support_chain.epochs[0]
            != discovery_stream.pairing_authority.support_chain.epochs[0]
            for item in validations
        ):
            _fail("row validation lineage does not extend discovery")
        latest_stream, latest_batches = validations[-1]
        discovery_descriptors: dict[
            str,
            backend.V075OutcomeDescriptorV1,
        ] = {}
        discovery_batch_by_id = {
            item.batch_id: item for item in discovery_batches
        }
        projected_by_batch_outcome: dict[
            tuple[str, str],
            backend.V075OutcomeDescriptorV1,
        ] = {}
        for item in discovery_batches:
            for outcome in item.outcomes:
                descriptor = _project_outcome(
                    discovery_stream.row_binding,
                    outcome,
                )
                discovery_descriptors[descriptor.descriptor_id] = descriptor
                projected_by_batch_outcome[
                    (item.batch_id, outcome.outcome_id)
                ] = descriptor
        evidence = (
            latest_stream.pairing_authority.support_chain.leaf.evidence
        )
        if any(
            type(item)
            is not public_graph.V075BatchAggregateSupportEvidenceV1
            for item in evidence
        ):
            _fail(
                "batch-native support requires signed aggregate evidence; "
                "per-draw support evidence is forbidden"
            )
        for item in evidence:
            discovery_batch = discovery_batch_by_id.get(
                item.discovery_batch_id
            )
            descriptor = projected_by_batch_outcome.get(
                (item.discovery_batch_id, item.discovery_outcome_id)
            )
            outcome = next(
                (
                    candidate
                    for candidate in (
                        ()
                        if discovery_batch is None
                        else discovery_batch.outcomes
                    )
                    if candidate.outcome_id
                    == item.discovery_outcome_id
                ),
                None,
            )
            if (
                discovery_batch is None
                or descriptor is None
                or outcome is None
                or item.namespace != discovery_stream.namespace
                or item.row_binding != discovery_stream.row_binding
                or item.source_observer_epoch_index
                != discovery_stream.observer_epoch_index
                or item.discovery_request_id
                != discovery_batch.request.request_id
                or item.discovery_outcome_count != outcome.count
                or item.observed_state.state_id
                != descriptor.next_state_id
            ):
                _fail(
                    "aggregate support evidence is stale, transplanted, or "
                    "not an observed DISCOVERY outcome"
                )
        evidence_state_ids = {
            item.observed_state.state_id for item in evidence
        }
        descriptor_by_state = {
            item.next_state_id: item
            for item in discovery_descriptors.values()
        }
        if (
            not evidence_state_ids
            or not evidence_state_ids <= set(descriptor_by_state)
            or len(evidence_state_ids) > backend.MAX_SUPPORT_OUTCOMES
        ):
            _fail(
                "frozen validation support is empty, undiscovered, or over-cap"
            )
        support = tuple(
            sorted(
                (
                    descriptor_by_state[state_id]
                    for state_id in evidence_state_ids
                ),
                key=lambda item: item.descriptor_id,
            )
        )
        intervals = _intervals_from_batches(
            row_binding=latest_stream.row_binding,
            support=support,
            values=latest_batches,
            route=request.route,
            caps=request.cap_profile,
        )
        discovery_ids = tuple(item.batch_id for item in discovery_batches)
        validation_ids = tuple(item.batch_id for item in latest_batches)
        selected_batch_ids.update((*discovery_ids, *validation_ids))
        superseded_validation_draws += sum(
            batch.request.accepted_draw_count
            for _stream, batches in validations[:-1]
            for batch in batches
        )
        row = latest_stream.row_binding
        rows.append(
            backend.V075StatisticalRowV1(
                row.context_id,
                row_binding_id,
                row.state_id,
                row.remaining_horizon,
                row.action,
                discovery_ids,
                validation_ids,
                support,
                intervals,
                latest_stream.observer_epoch_index,
                "BATCH_NATIVE_PUBLIC_AGGREGATES_VERIFIED",
            )
        )
    return (
        tuple(sorted(rows, key=lambda item: item.row_id)),
        tuple(sorted(selected_batch_ids)),
        superseded_validation_draws,
    )


def _validate_modeled_closure(
    request: V075BatchNativeBackendRequestV1,
    rows: tuple[backend.V075StatisticalRowV1, ...],
) -> None:
    root = public_graph.root_catalogue_v1(request.context)
    rows_by_state: dict[str, dict[tuple[int, int, int], backend.V075StatisticalRowV1]] = {}
    for item in rows:
        if item.source_state_id in rows_by_state and (
            item.action in rows_by_state[item.source_state_id]
        ):
            _fail("batch-native model duplicates one state-action row")
        rows_by_state.setdefault(item.source_state_id, {})[item.action] = item
    if set(rows_by_state.get(root.state.state_id, {})) != set(root.actions):
        _fail("batch-native root action catalogue is incomplete")
    child_states = {
        descriptor.next_state_id: public_graph.V075SymbolicGraphStateV1(
            request.context,
            descriptor.next_ranks,
            descriptor.failure,
        )
        for row in rows_by_state[root.state.state_id].values()
        for descriptor in row.support
        if not descriptor.failure and not descriptor.terminal
    }
    actual_child_states = set(rows_by_state) - {root.state.state_id}
    if not actual_child_states <= set(child_states):
        _fail(
            "batch-native materialized child is unobserved or transplanted"
        )
    for state_id, state in child_states.items():
        if state_id not in actual_child_states:
            continue
        catalogue = public_graph.V075LegalActionCatalogueV1(
            request.context,
            state,
            1,
            public_graph.legal_action_triples_v1(
                request.context,
                state.ranks,
                state.failure,
            ),
        )
        if set(rows_by_state[state_id]) != set(catalogue.actions):
            _fail("batch-native child action catalogue is incomplete")


BATCH_NATIVE_COUNTER_PATHS = (
    "common.request_checks",
    "common.public_batch_verifications",
    "common.sequence_verifications",
    "common.aggregate_support_evidence_verified",
    "common.accepted_draws_consumed",
    "common.adaptive_cap_charged_incremental_draws",
    "common.outcome_aggregates_projected",
    "common.discovery_draws_consumed",
    "common.validation_draws_consumed",
    "common.superseded_validation_draws",
    "common.statistical_rows_built",
    "common.confidence_event_evaluations",
    "common.exact_likelihood_comparisons",
    "common.log_search_evaluations",
    "adaptive.route_attempts",
    "direct.route_attempts",
    "common.per_draw_capabilities_materialized",
)


@dataclass(frozen=True, slots=True)
class V075BatchNativeCounterV1:
    path: str
    value: int
    observed: bool = True

    def __post_init__(self) -> None:
        if (
            self.path not in BATCH_NATIVE_COUNTER_PATHS
            or type(self.value) is not int
            or self.value < 0
            or self.observed is not True
        ):
            _fail("batch-native counter is unknown or malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_native_backend_counter.v1",
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
class V075BatchNativeWorkV1:
    request_id: str
    arm: worker.V075WorkerArmV1
    counters: tuple[V075BatchNativeCounterV1, ...]

    def __post_init__(self) -> None:
        _cid(self.request_id, "batch-native work request")
        if (
            type(self.arm) is not worker.V075WorkerArmV1
            or tuple(item.path for item in self.counters)
            != BATCH_NATIVE_COUNTER_PATHS
        ):
            _fail("batch-native work counters are incomplete or reordered")
        values = {item.path: item.value for item in self.counters}
        adaptive = self.arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
        if (
            values["adaptive.route_attempts"] != int(adaptive)
            or values["direct.route_attempts"] != int(not adaptive)
            or values["common.per_draw_capabilities_materialized"] != 0
        ):
            _fail("batch-native work route lanes or no-expansion rule changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_native_backend_work.v1",
            "schema_version": SCHEMA_VERSION,
            "request_id": self.request_id,
            "arm": self.arm.value,
            "counter_ids": [item.counter_id for item in self.counters],
            "required_counter_paths": list(BATCH_NATIVE_COUNTER_PATHS),
            "native_zeros_complete": True,
            "per_draw_capability_expansion": False,
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
class V075BatchNativeBackendResultV1:
    request: V075BatchNativeBackendRequestV1
    route_native_result: backend.V075RouteNativeBackendResultV1
    aggregate_support_evidence_ids: tuple[str, ...]
    selected_batch_ids: tuple[str, ...]
    superseded_batch_ids: tuple[str, ...]
    work: V075BatchNativeWorkV1

    def __post_init__(self) -> None:
        if (
            type(self.request) is not V075BatchNativeBackendRequestV1
            or type(self.route_native_result)
            is not backend.V075RouteNativeBackendResultV1
            or type(self.work) is not V075BatchNativeWorkV1
            or self.route_native_result.request_id != self.request.request_id
            or self.route_native_result.occurrence_id
            != self.request.occurrence_id
            or self.route_native_result.arm is not self.request.arm
            or self.work.request_id != self.request.request_id
            or self.work.arm is not self.request.arm
            or self.aggregate_support_evidence_ids
            != tuple(sorted(set(self.aggregate_support_evidence_ids)))
            or self.aggregate_support_evidence_ids
            != _aggregate_support_evidence_ids(self.request)
            or self.selected_batch_ids
            != tuple(sorted(set(self.selected_batch_ids)))
            or self.superseded_batch_ids
            != tuple(sorted(set(self.superseded_batch_ids)))
            or set(self.selected_batch_ids) & set(self.superseded_batch_ids)
            or set(self.selected_batch_ids) | set(self.superseded_batch_ids)
            != {item.batch_id for item in self.request.batches}
            or tuple(
                sorted(
                    self.route_native_result
                    .total_lift_input.capability_ref_ids
                )
            )
            != self.selected_batch_ids
        ):
            _fail("batch-native backend result identity graph is inconsistent")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_native_backend_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request.request_id,
            "occurrence_id": self.request.occurrence_id,
            "arm": self.request.arm.value,
            "route": self.request.route.value,
            "authority_scope": self.request.authority_scope.value,
            "route_native_result_id": self.route_native_result.result_id,
            "aggregate_support_evidence_ids": list(
                self.aggregate_support_evidence_ids
            ),
            "selected_batch_ids": list(self.selected_batch_ids),
            "superseded_batch_ids": list(self.superseded_batch_ids),
            "work_id": self.work.work_id,
            "per_draw_capability_expansion": False,
            "public_aggregate_projection_only": True,
            "production_integration_ready": False,
            "scientific_plan_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def result_id(self) -> str:
        return _hash("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "request": self.request.to_document(),
            "route_native_result": self.route_native_result.to_document(),
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _proposal(
    request: V075BatchNativeBackendRequestV1,
) -> backend.V075ProposalBasisV1:
    registration = (
        worker.freeze_v075_worker_registry_draft_v1()
        .require_arm(request.arm)
    )
    if request.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        assert request.source_prior_transport is not None
        vector = backend.SOURCE_FORWARD_MIDRANK
        transport_id = request.source_prior_transport.transport_id
    elif request.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
        vector = backend.REGISTERED_WRONG_REVERSED_MIDRANK
        transport_id = None
    else:
        vector = ()
        transport_id = None
    return backend.V075ProposalBasisV1(
        request.request_id,
        request.arm,
        registration.proposal_semantics,
        vector,
        transport_id,
    )


def _schedule(
    request: V075BatchNativeBackendRequestV1,
) -> backend.V075RouteScheduleV1:
    discovery: list[tuple[str, int]] = []
    validation: list[tuple[str, int]] = []
    for stream_id, values in request.batches_by_stream.items():
        stream = values[0].request.stream_identity
        count = sum(item.request.accepted_draw_count for item in values)
        target = (
            discovery
            if stream.lane is public_graph.V075ObservationLaneV1.DISCOVERY
            else validation
        )
        target.append((stream_id, count))
    return backend.V075RouteScheduleV1(
        request.request_id,
        request.arm,
        request.route,
        tuple(sorted(discovery)),
        tuple(sorted(validation)),
        backend.V075BackendScheduleStatusV1.COMPLETE_REGISTERED_CHECKPOINT,
        request.cap_profile.cap_profile_id,
    )


def _route_projection_work(
    request: V075BatchNativeBackendRequestV1,
    rows: tuple[backend.V075StatisticalRowV1, ...],
    selected_batch_ids: tuple[str, ...],
) -> backend.V075BackendWorkV1:
    selected = {
        item.batch_id: item
        for item in request.batches
        if item.batch_id in selected_batch_ids
    }
    discovery_batches = sum(
        item.request.stream_identity.lane
        is public_graph.V075ObservationLaneV1.DISCOVERY
        for item in selected.values()
    )
    validation_batches = len(selected) - discovery_batches
    intervals = tuple(
        interval for row in rows for interval in row.intervals
    )
    adaptive = request.route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
    values = {path: 0 for path in backend.COUNTER_PATHS}
    values.update(
        {
            "common.request_reconstructions": 1,
            "common.capability_refs_consumed": len(selected),
            "common.discovery_capabilities_consumed": discovery_batches,
            "common.validation_capabilities_consumed": validation_batches,
            "common.outcome_projections": sum(
                len(item.outcomes) for item in selected.values()
            ),
            "common.schedule_checks": 1,
            "common.confidence_event_evaluations": len(intervals),
            "common.exact_likelihood_comparisons": sum(
                item.exact_likelihood_comparisons for item in intervals
            ),
            "common.log_search_evaluations": sum(
                item.log_search_evaluations for item in intervals
            ),
            "common.statistical_rows_built": len(rows),
            "source.adapter_payload_reads": int(
                request.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ),
            "source.proposal_entries_bound": (
                3
                if request.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                else 0
            ),
            "adaptive.route_attempts": int(adaptive),
            "adaptive.source_proposal_attempts": int(
                request.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            ),
            "adaptive.no_prior_attempts": int(
                request.arm is worker.V075WorkerArmV1.NO_PRIOR
            ),
            "adaptive.wrong_prior_attempts": int(
                request.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR
            ),
            "adaptive.ood_abstention_attempts": int(
                request.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            ),
            "direct.route_attempts": int(not adaptive),
            "adaptive.model_rows": len(rows) if adaptive else 0,
            "direct.model_rows": len(rows) if not adaptive else 0,
        }
    )
    return backend.V075BackendWorkV1(
        request.request_id,
        request.arm,
        tuple(
            backend.V075BackendCounterV1(path, values[path])
            for path in backend.COUNTER_PATHS
        ),
    )


def _native_work(
    *,
    request: V075BatchNativeBackendRequestV1,
    rows: tuple[backend.V075StatisticalRowV1, ...],
    superseded_validation_draws: int,
) -> V075BatchNativeWorkV1:
    discovery_draws = sum(
        item.request.accepted_draw_count
        for item in request.batches
        if item.request.stream_identity.lane
        is public_graph.V075ObservationLaneV1.DISCOVERY
    )
    validation_draws = sum(
        item.request.accepted_draw_count
        for item in request.batches
        if item.request.stream_identity.lane
        is public_graph.V075ObservationLaneV1.VALIDATION
    )
    intervals = tuple(
        interval for row in rows for interval in row.intervals
    )
    adaptive = request.route is worker.V075WorkerRouteV1.ADAPTIVE_QUOTIENT
    aggregate_support_evidence_ids = _aggregate_support_evidence_ids(request)
    values = {
        "common.request_checks": 1,
        "common.public_batch_verifications": len(
            request.public_verifications
        ),
        "common.sequence_verifications": len(
            request.sequence_verifications
        ),
        "common.aggregate_support_evidence_verified": len(
            aggregate_support_evidence_ids
        ),
        "common.accepted_draws_consumed": discovery_draws + validation_draws,
        "common.adaptive_cap_charged_incremental_draws": (
            _adaptive_cap_charged_draws(request)
        ),
        "common.outcome_aggregates_projected": sum(
            len(item.outcomes) for item in request.batches
        ),
        "common.discovery_draws_consumed": discovery_draws,
        "common.validation_draws_consumed": validation_draws,
        "common.superseded_validation_draws": (
            superseded_validation_draws
        ),
        "common.statistical_rows_built": len(rows),
        "common.confidence_event_evaluations": len(intervals),
        "common.exact_likelihood_comparisons": sum(
            item.exact_likelihood_comparisons for item in intervals
        ),
        "common.log_search_evaluations": sum(
            item.log_search_evaluations for item in intervals
        ),
        "adaptive.route_attempts": int(adaptive),
        "direct.route_attempts": int(not adaptive),
        "common.per_draw_capabilities_materialized": 0,
    }
    return V075BatchNativeWorkV1(
        request.request_id,
        request.arm,
        tuple(
            V075BatchNativeCounterV1(path, values[path])
            for path in BATCH_NATIVE_COUNTER_PATHS
        ),
    )


def _aggregate_support_evidence_ids(
    request: V075BatchNativeBackendRequestV1,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                evidence.evidence_id
                for item in request.batches
                if item.request.stream_identity.lane
                is public_graph.V075ObservationLaneV1.VALIDATION
                for evidence in (
                    item.request.stream_identity.pairing_authority
                    .support_chain.leaf.evidence
                )
                if type(evidence)
                is public_graph.V075BatchAggregateSupportEvidenceV1
            }
        )
    )


def compile_v075_batch_native_statistical_backend_v1(
    request: V075BatchNativeBackendRequestV1,
) -> V075BatchNativeBackendResultV1:
    """Project verified batch aggregates directly into route-native rows."""

    if type(request) is not V075BatchNativeBackendRequestV1:
        _fail("batch-native compiler rejects duck-typed requests")
    rows, selected_batch_ids, superseded_draws = _compile_rows(request)
    _validate_modeled_closure(request, rows)
    proposal = _proposal(request)
    schedule = _schedule(request)
    model = backend.V075StatisticalModelV1(
        request.request_id,
        request.occurrence_id,
        request.arm,
        proposal.proposal_id,
        schedule.schedule_id,
        rows,
        True,
        True,
        (),
    )
    status = (
        backend.V075BackendCandidateStatusV1
        .NOT_READY_TYPED_SUPPORT_GRAPH_BINDER
    )
    root_state_id = public_graph.root_catalogue_v1(
        request.context
    ).state.state_id
    policy = backend.V075PolicyCandidateV1(
        model.model_id,
        request.arm,
        status,
        tuple(
            sorted(
                row.row_id
                for row in rows
                if row.source_state_id == root_state_id
            )
        ),
    )
    envelope = backend.V075EnvelopeCandidateV1(
        model.model_id,
        policy.policy_candidate_id,
        status,
    )
    total_lift = backend.V075TotalLiftCandidateInputV1(
        request.occurrence_id,
        model.model_id,
        policy.policy_candidate_id,
        envelope.envelope_candidate_id,
        status,
        tuple(row.row_id for row in rows),
        selected_batch_ids,
    )
    route_result = backend.V075RouteNativeBackendResultV1(
        request.request_id,
        request.occurrence_id,
        request.arm,
        schedule,
        proposal,
        model,
        policy,
        envelope,
        total_lift,
        _route_projection_work(
            request,
            rows,
            selected_batch_ids,
        ),
    )
    all_batch_ids = {item.batch_id for item in request.batches}
    superseded_ids = tuple(sorted(all_batch_ids - set(selected_batch_ids)))
    return V075BatchNativeBackendResultV1(
        request,
        route_result,
        _aggregate_support_evidence_ids(request),
        selected_batch_ids,
        superseded_ids,
        _native_work(
            request=request,
            rows=rows,
            superseded_validation_draws=superseded_draws,
        ),
    )


def compile_v075_batch_native_support_graph_v1(
    result: V075BatchNativeBackendResultV1,
) -> planners.V075LearnedSupportGraphV1:
    if type(result) is not V075BatchNativeBackendResultV1:
        _fail("support bridge rejects duck-typed batch-native results")
    return planners.compile_v075_learned_support_graph_v1(
        result.route_native_result
    )


def plan_v075_batch_native_route_v1(
    result: V075BatchNativeBackendResultV1,
) -> planners.V075SupportPlannerResultV1:
    graph = compile_v075_batch_native_support_graph_v1(result)
    if result.request.route is worker.V075WorkerRouteV1.MATCHED_DIRECT_GROUND:
        return planners.plan_v075_exact_h2_matched_direct_ground_v1(graph)
    return planners.plan_v075_exact_h2_abstract_v1(graph)


def verify_v075_batch_native_backend_result_v1(
    *,
    request: V075BatchNativeBackendRequestV1,
    claimed_bytes: bytes,
) -> V075BatchNativeBackendResultV1:
    expected = compile_v075_batch_native_statistical_backend_v1(request)
    if type(claimed_bytes) is not bytes or claimed_bytes != expected.canonical_bytes:
        _fail("batch-native backend result differs from exact recomputation")
    return expected


__all__ = [
    "BATCH_NATIVE_COUNTER_PATHS",
    "DOMAIN_TAGS",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075BatchNativeBackendInvariantViolation",
    "V075BatchNativeOccurrenceIdentityV1",
    "V075BatchNativeBackendRequestV1",
    "V075BatchNativeBackendResultV1",
    "V075BatchNativeCounterV1",
    "V075BatchNativeWorkV1",
    "compile_v075_batch_native_statistical_backend_v1",
    "compile_v075_batch_native_support_graph_v1",
    "freeze_v075_batch_native_backend_request_v1",
    "freeze_v075_batch_native_occurrence_identity_v1",
    "freeze_v075_batch_native_occurrence_identity_from_namespace_v2",
    "replay_v075_batch_native_occurrence_identity_v1",
    "plan_v075_batch_native_route_v1",
    "verify_v075_batch_native_backend_result_v1",
]
