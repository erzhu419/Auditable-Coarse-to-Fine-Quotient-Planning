"""Pretarget adaptive-acquisition proposal authority for V0-075.

The authority has two deliberately separate jobs:

* freeze the complete root discovery/validation schedule before any target
  observation is requested; and
* after a *noncertificate* H=2 planner envelope, rank only the rows on the
  diagnostic policy frontier and authorize one validation-prefix extension.

The source archive is proposal-only.  Its three ``APPLIED`` midranks may
multiply a target-local uncertainty score, but they are never copied into a
statistical row, confidence interval, quotient, planner envelope, or exact
lift.  Target features independently replay the exact
``portable_acquisition_core_feature.v2`` payload and content-ID domain.  The
feature contains no context, vertex, identity, count, or probability field.

This module issues intents only.  It has no observer/session, transition
kernel, hidden law, reveal, salt, signer, random tape, callback, or target-open
surface.  A later executor must bind an intent to the independently frozen
public stream and must return a batch-native result.  The next round verifies
that the exact frozen prefix extension, and no post-hoc replacement, occurred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_pretarget_adaptive_acquisition_proposal_v1"
PRODUCTION_INTEGRATION_READY = False

SOURCE_FEATURE_SCHEMA_VERSION = "2.0.0"
SOURCE_FEATURE_SCHEMA_ID = (
    "6c5867ab74182b98faf776ec6a544799c745b5bf6c7cd9943733da5fe96951de"
)
SOURCE_ARCHIVE_ID = (
    "4b25945b07d94ace9a6af8cbf979a9133e3780b6306c0bc3b7d8055b2c25bf92"
)
SOURCE_ARCHIVE_VERIFICATION_ID = (
    "e23c98ce70ebee04dd6dcccd29149a16c90b48ef5e62b5e006a524c58818157c"
)
SOURCE_FEATURE_DOMAIN = (
    "acfqp:verified-source-acquisition-archive:portable-feature:v2"
)
OOD_MISMATCH_FEATURE_SCHEMA_ID = hashlib.sha256(
    b"acfqp:v075-registered-ood-feature-schema:v1"
).hexdigest()

REGISTERED_APPLIED_SOURCE_MIDRANKS = (
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
REGISTERED_APPLIED_SOURCE_KEYS = tuple(
    key for key, _midrank in REGISTERED_APPLIED_SOURCE_MIDRANKS
)

MAX_ADAPTIVE_ROUNDS = 2
MAX_SELECTED_ROWS_PER_ROUND = 1
INITIAL_VALIDATION_ACCEPTED_DRAW_CAP = (
    worker.V075WorkerCapProfileV1().initial_validation_draws_per_row
    + MAX_ADAPTIVE_ROUNDS
    * worker.V075WorkerCapProfileV1().promotion_validation_draws_per_round
)

_ISSUER = object()

DOMAIN_TAGS = {
    "source_view": "acfqp:v075-pretarget-source-proposal-view:v1",
    "initial_intent": "acfqp:v075-initial-row-acquisition-intent:v1",
    "initial_schedule": "acfqp:v075-initial-root-acquisition-schedule:v1",
    "candidate": "acfqp:v075-adaptive-acquisition-candidate:v1",
    "frontier": "acfqp:v075-adaptive-acquisition-frontier:v1",
    "round_intent": "acfqp:v075-adaptive-round-row-intent:v1",
    "authorization": "acfqp:v075-adaptive-round-authorization:v1",
    "execution": "acfqp:v075-adaptive-round-execution-verification:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 adaptive-acquisition domains must be unique")


class V075AdaptiveAcquisitionInvariantViolation(ValueError):
    """A feature, prior, frontier, cap, or execution-order invariant failed."""


class V075InitialIntentKindV1(str, Enum):
    ROOT_DISCOVERY = "ROOT_DISCOVERY"
    ROOT_VALIDATION = "ROOT_VALIDATION"


class V075PriorDispositionV1(str, Enum):
    SOURCE_APPLIED = "SOURCE_APPLIED"
    WRONG_REVERSED_APPLIED = "WRONG_REVERSED_APPLIED"
    SOURCE_FEATURE_NO_MATCH_NEUTRAL = "SOURCE_FEATURE_NO_MATCH_NEUTRAL"
    WRONG_FEATURE_NO_MATCH_NEUTRAL = "WRONG_FEATURE_NO_MATCH_NEUTRAL"
    NO_PRIOR_NEUTRAL = "NO_PRIOR_NEUTRAL"
    OOD_SCHEMA_ABSTAINED = "OOD_SCHEMA_ABSTAINED"


class V075RoundProposalStatusV1(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    NO_UNCERTAIN_SELECTED_FRONTIER = "NO_UNCERTAIN_SELECTED_FRONTIER"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"


def _fail(message: str) -> None:
    raise V075AdaptiveAcquisitionInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075AdaptiveAcquisitionInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075AdaptiveAcquisitionInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("adaptive-acquisition arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_document(value: Any, field_name: str) -> Fraction:
    # ``loads_canonical_json`` already validates and decodes every reduced
    # rational-shaped object to ``Fraction``.  Retain the mapping branch for
    # typed in-memory callers that have not crossed that byte boundary.
    if type(value) is Fraction:
        return value
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{field_name} is not one reduced rational document")
    result = Fraction(value["numerator"], value["denominator"])
    if _fdoc(result) != value:
        _fail(f"{field_name} is not reduced")
    return result


def _count_bin(value: int) -> str:
    if type(value) is not int or value < 0:
        _fail("portable feature count input is invalid")
    if value == 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _registered_context(
    context: public_authority.V075PublicReplicateContextV1,
) -> public_authority.V075PublicReplicateContextV1:
    if type(context) is not public_authority.V075PublicReplicateContextV1:
        _fail("adaptive-acquisition context is not typed")
    matches = tuple(
        item
        for item in (
            public_authority.freeze_v075_public_family_generation_v1()
            .replicate_contexts
        )
        if item.context_id == context.context_id
    )
    if len(matches) != 1 or matches[0] != context:
        _fail("adaptive-acquisition context is not preregistered")
    return matches[0]


@dataclass(frozen=True, slots=True)
class V075PortableAcquisitionCoreFeatureReplayV2:
    """Independent exact replay of the frozen source feature key space."""

    stage_role: str
    selected_row_category: str
    catalogue_action_count_bin: str
    concretizer_support_count_bin: str
    destination_category_presence: tuple[str, ...]
    feature_schema_id: str = SOURCE_FEATURE_SCHEMA_ID
    ids_stripped: bool = True
    exact_probabilities_absent: bool = True

    def __post_init__(self) -> None:
        selected = {
            "ROOT_SELECTED",
            "CONTINUATION_SELECTED",
            "ROOT_CONCRETIZER_COMPONENT",
            "CONTINUATION_CONCRETIZER_COMPONENT",
        }
        destinations = {"ACTIVE_STATE", "FAILURE", "SUCCESS_TERMINAL"}
        bins = {"0", "1", "2", "3_PLUS"}
        if (
            self.stage_role not in {"ROOT", "CONTINUATION"}
            or self.selected_row_category not in selected
            or self.catalogue_action_count_bin not in bins
            or self.concretizer_support_count_bin not in bins
            or type(self.destination_category_presence) is not tuple
            or not self.destination_category_presence
            or self.destination_category_presence
            != tuple(sorted(set(self.destination_category_presence)))
            or not set(self.destination_category_presence) <= destinations
            or self.feature_schema_id != SOURCE_FEATURE_SCHEMA_ID
            or self.ids_stripped is not True
            or self.exact_probabilities_absent is not True
        ):
            _fail("portable acquisition feature replay is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.portable_acquisition_core_feature.v2",
            "schema_version": SOURCE_FEATURE_SCHEMA_VERSION,
            "feature_schema_id": SOURCE_FEATURE_SCHEMA_ID,
            "stage_role": self.stage_role,
            "selected_row_category": self.selected_row_category,
            "catalogue_action_count_bin": self.catalogue_action_count_bin,
            "concretizer_support_count_bin": (
                self.concretizer_support_count_bin
            ),
            "destination_category_presence": list(
                self.destination_category_presence
            ),
            "ids_stripped": True,
            "exact_probabilities_absent": True,
            "exact_counts_absent": True,
            "vertex_labels_absent": True,
            "context_identity_absent": True,
            "observed_support_count_absent": True,
        }

    @property
    def feature_key(self) -> str:
        return hashlib.sha256(
            SOURCE_FEATURE_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(self._payload())
        ).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "feature_key": self.feature_key}


@dataclass(frozen=True, slots=True)
class V075SourceProposalViewV1:
    """Minimal proposal-only view; no source model or target field is admitted."""

    _issuer: object = field(repr=False, compare=False)
    arm: worker.V075WorkerArmV1
    source_reference_id: str | None
    applicable_feature_schema_id: str
    feature_midranks: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self.arm) is not worker.V075WorkerArmV1:
            _fail("source proposal views are compiler-issued only")
        if self.source_reference_id is not None:
            _cid(self.source_reference_id, "source proposal reference")
        if self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
            _fail("direct ground route has no adaptive proposal view")
        if (
            type(self.feature_midranks) is not tuple
            or self.feature_midranks
            != tuple(sorted(self.feature_midranks))
            or len({key for key, _value in self.feature_midranks})
            != len(self.feature_midranks)
            or any(
                type(value) is not Fraction or not 0 <= value <= 1
                for _key, value in self.feature_midranks
            )
        ):
            _fail("source proposal midranks are noncanonical")
        for key, _value in self.feature_midranks:
            _cid(key, "source proposal feature")
        if self.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
            if (
                self.source_reference_id is None
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                != tuple(sorted(REGISTERED_APPLIED_SOURCE_MIDRANKS))
            ):
                _fail("SOURCE proposal view differs from verified source evidence")
        elif self.arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
            if (
                self.source_reference_id is None
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
                != tuple(sorted(REGISTERED_APPLIED_SOURCE_MIDRANKS))
            ):
                _fail("WRONG proposal view differs from frozen reverse control")
        elif self.arm is worker.V075WorkerArmV1.NO_PRIOR:
            if (
                self.source_reference_id is not None
                or self.applicable_feature_schema_id
                != SOURCE_FEATURE_SCHEMA_ID
                or self.feature_midranks
            ):
                _fail("NO_PRIOR proposal view contains source inputs")
        elif (
            self.arm is worker.V075WorkerArmV1.OOD_ABSTENTION
            and (
                self.source_reference_id is not None
                or self.applicable_feature_schema_id
                != OOD_MISMATCH_FEATURE_SCHEMA_ID
                or self.feature_midranks
            )
        ):
            _fail("OOD proposal view did not abstain without source numbers")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_proposal_view.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "source_reference_id": self.source_reference_id,
            "applicable_feature_schema_id": (
                self.applicable_feature_schema_id
            ),
            "feature_midranks": [
                {"feature_key": key, "mean_midrank": _fdoc(value)}
                for key, value in self.feature_midranks
            ],
            "proposal_only": True,
            "may_certify": False,
            "target_fields_present": False,
            "source_dynamics_present": False,
        }

    @property
    def source_view_id(self) -> str:
        return _hash("source_view", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "source_view_id": self.source_view_id}

    def midrank_for(self, feature_key: str) -> Fraction | None:
        key = _cid(feature_key, "target portable feature")
        if self.applicable_feature_schema_id != SOURCE_FEATURE_SCHEMA_ID:
            return None
        return dict(self.feature_midranks).get(key)


def _source_view_from_transport(
    transport: worker.V075SourcePriorTransportV1,
) -> V075SourceProposalViewV1:
    if type(transport) is not worker.V075SourcePriorTransportV1:
        _fail("SOURCE proposal requires one exact verified source transport")
    try:
        adapter = loads_canonical_json(transport.adapter_bytes)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075AdaptiveAcquisitionInvariantViolation(
            "source transport adapter is not canonical JSON"
        ) from error
    if type(adapter) is not dict or canonical_json_bytes(adapter) != transport.adapter_bytes:
        _fail("source transport adapter is not one canonical object")
    catalogue = adapter.get("catalogue")
    entries = None if type(catalogue) is not dict else catalogue.get("entries")
    if (
        adapter.get("schema") != "acfqp.v075_source_prior_adapter.v1"
        or adapter.get("adapter_id") != transport.adapter_id
        or adapter.get("source_archive_id") != SOURCE_ARCHIVE_ID
        or adapter.get("source_archive_verification_id")
        != SOURCE_ARCHIVE_VERIFICATION_ID
        or adapter.get("registered_applied_feature_keys")
        != list(REGISTERED_APPLIED_SOURCE_KEYS)
        or adapter.get("source_only") is not True
        or adapter.get("proposal_only") is not True
        or adapter.get("may_certify") is not False
        or type(catalogue) is not dict
        or catalogue.get("source_feature_schema_id")
        != SOURCE_FEATURE_SCHEMA_ID
        or catalogue.get("registered_applied_feature_keys")
        != list(REGISTERED_APPLIED_SOURCE_KEYS)
        or type(entries) is not list
        or len(entries) != 3
    ):
        _fail("source prior was transplanted or changed feature schema")
    actual: list[tuple[str, Fraction]] = []
    for ordinal, entry in enumerate(entries):
        if (
            type(entry) is not dict
            or entry.get("applied_ordinal") != ordinal
            or entry.get("feature_key") != REGISTERED_APPLIED_SOURCE_KEYS[ordinal]
            or entry.get("disposition") != "APPLIED"
            or entry.get("source_only") is not True
            or entry.get("proposal_only") is not True
            or entry.get("may_certify") is not False
        ):
            _fail("source APPLIED entry was reordered or transplanted")
        actual.append(
            (
                entry["feature_key"],
                _fraction_from_document(
                    entry.get("exact_mean_midrank"),
                    "source exact mean midrank",
                ),
            )
        )
    if tuple(actual) != REGISTERED_APPLIED_SOURCE_MIDRANKS:
        _fail("source APPLIED midrank vector changed")
    return V075SourceProposalViewV1(
        _ISSUER,
        worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
        transport.transport_id,
        SOURCE_FEATURE_SCHEMA_ID,
        tuple(sorted(actual)),
    )


def freeze_v075_source_proposal_view_v1(
    *,
    arm: worker.V075WorkerArmV1,
    source_transport: worker.V075SourcePriorTransportV1 | None = None,
) -> V075SourceProposalViewV1:
    """Freeze one arm's proposal numbers without reading target evidence."""

    if type(arm) is not worker.V075WorkerArmV1:
        _fail("proposal arm is not typed")
    if arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR:
        if source_transport is None:
            _fail("SOURCE arm lacks verified source transport")
        return _source_view_from_transport(source_transport)
    if source_transport is not None:
        _fail("only SOURCE may consume the transported source artifact")
    if arm is worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR:
        return V075SourceProposalViewV1(
            _ISSUER,
            arm,
            hashlib.sha256(
                b"acfqp:v075-registered-wrong-source-reference:v1\x00"
                + canonical_json_bytes(
                    [
                        {
                            "feature_key": key,
                            "mean_midrank": _fdoc(midrank),
                        }
                        for key, midrank in REGISTERED_APPLIED_SOURCE_MIDRANKS
                    ]
                )
            ).hexdigest(),
            SOURCE_FEATURE_SCHEMA_ID,
            tuple(sorted(REGISTERED_APPLIED_SOURCE_MIDRANKS)),
        )
    if arm is worker.V075WorkerArmV1.NO_PRIOR:
        return V075SourceProposalViewV1(
            _ISSUER,
            arm,
            None,
            SOURCE_FEATURE_SCHEMA_ID,
            (),
        )
    if arm is worker.V075WorkerArmV1.OOD_ABSTENTION:
        return V075SourceProposalViewV1(
            _ISSUER,
            arm,
            None,
            OOD_MISMATCH_FEATURE_SCHEMA_ID,
            (),
        )
    _fail("matched direct route has no adaptive proposal")
    raise AssertionError("unreachable")


@dataclass(frozen=True, slots=True)
class V075InitialRootRowIntentV1:
    _issuer: object = field(repr=False, compare=False)
    arm: worker.V075WorkerArmV1
    row_binding: public_graph.V075ObservationRowBindingV1
    kind: V075InitialIntentKindV1
    observer_epoch_index: int
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    dependency_intent_id: str | None
    cap_profile_id: str

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.row_binding) is not public_graph.V075ObservationRowBindingV1
            or self.row_binding.remaining_horizon != 2
            or type(self.kind) is not V075InitialIntentKindV1
            or self.accepted_draw_start != 1
        ):
            _fail("initial root intent is malformed")
        _cid(self.cap_profile_id, "initial intent cap profile")
        caps = worker.V075WorkerCapProfileV1()
        if self.kind is V075InitialIntentKindV1.ROOT_DISCOVERY:
            expected = (0, caps.initial_discovery_draws_per_row, caps.initial_discovery_draws_per_row)
            if self.dependency_intent_id is not None:
                _fail("root discovery cannot depend on target evidence")
        else:
            expected = (1, caps.initial_validation_draws_per_row, INITIAL_VALIDATION_ACCEPTED_DRAW_CAP)
            if self.dependency_intent_id is None:
                _fail("root validation lacks its frozen discovery dependency")
            _cid(self.dependency_intent_id, "root validation dependency")
        if (
            (
                self.observer_epoch_index,
                self.accepted_draw_count,
                self.accepted_draw_cap,
            )
            != expected
            or self.cap_profile_id != caps.cap_profile_id
        ):
            _fail("initial root intent counts or caps drifted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_initial_root_row_intent.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm.value,
            "context_id": self.row_binding.context_id,
            "row_binding_id": self.row_binding.row_binding_id,
            "catalogue_id": self.row_binding.catalogue_id,
            "action": list(self.row_binding.action),
            "kind": self.kind.value,
            "lane": (
                public_graph.V075ObservationLaneV1.DISCOVERY.value
                if self.kind is V075InitialIntentKindV1.ROOT_DISCOVERY
                else public_graph.V075ObservationLaneV1.VALIDATION.value
            ),
            "observer_epoch_index": self.observer_epoch_index,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": (
                self.accepted_draw_start + self.accepted_draw_count - 1
            ),
            "accepted_draw_cap": self.accepted_draw_cap,
            "dependency_intent_id": self.dependency_intent_id,
            "cap_profile_id": self.cap_profile_id,
            "stream_identity_minted_at_execution": True,
            "observer_calls": 0,
            "kernel_calls": 0,
        }

    @property
    def intent_id(self) -> str:
        return _hash("initial_intent", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075InitialRootAcquisitionScheduleV1:
    context: public_authority.V075PublicReplicateContextV1
    arm: worker.V075WorkerArmV1
    intents: tuple[V075InitialRootRowIntentV1, ...]
    cap_profile: worker.V075WorkerCapProfileV1

    def __post_init__(self) -> None:
        _registered_context(self.context)
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.intents) is not tuple
            or type(self.cap_profile) is not worker.V075WorkerCapProfileV1
        ):
            _fail("initial root schedule is malformed")
        root = public_graph.root_catalogue_v1(self.context)
        discoveries = tuple(
            item for item in self.intents
            if item.kind is V075InitialIntentKindV1.ROOT_DISCOVERY
        )
        validations = tuple(
            item for item in self.intents
            if item.kind is V075InitialIntentKindV1.ROOT_VALIDATION
        )
        if (
            len(discoveries) != len(root.actions)
            or len(validations) != len(root.actions)
            or tuple(item.row_binding.action for item in discoveries)
            != root.actions
            or tuple(item.row_binding.action for item in validations)
            != root.actions
            or any(item.arm is not self.arm for item in self.intents)
            or tuple(item.dependency_intent_id for item in validations)
            != tuple(item.intent_id for item in discoveries)
            or self.online_draw_upper
            > self.cap_profile.maximum_incremental_draws_per_adaptive_arm
        ):
            _fail("initial schedule omitted, reordered, or over-capped a root row")

    @property
    def online_draw_upper(self) -> int:
        return sum(item.accepted_draw_count for item in self.intents)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_initial_root_acquisition_schedule.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context.context_id,
            "arm": self.arm.value,
            "intent_ids": [item.intent_id for item in self.intents],
            "cap_profile_id": self.cap_profile.cap_profile_id,
            "online_draw_upper": self.online_draw_upper,
            "maximum_adaptive_rounds_after_initial": MAX_ADAPTIVE_ROUNDS,
            "complete_root_action_catalogue": True,
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "private_law_reads": 0,
        }

    @property
    def schedule_id(self) -> str:
        return _hash("initial_schedule", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "intents": [item.to_document() for item in self.intents],
            "schedule_id": self.schedule_id,
        }


def freeze_v075_initial_root_acquisition_schedule_v1(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    arm: worker.V075WorkerArmV1,
) -> V075InitialRootAcquisitionScheduleV1:
    registered = _registered_context(context)
    if (
        type(arm) is not worker.V075WorkerArmV1
        or arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    ):
        _fail("initial adaptive schedule requires one adaptive arm")
    caps = worker.V075WorkerCapProfileV1()
    bindings = tuple(
        public_graph.observation_row_binding_v1(
            registered,
            public_graph.root_catalogue_v1(registered),
            action,
        )
        for action in public_graph.root_catalogue_v1(registered).actions
    )
    discoveries = tuple(
        V075InitialRootRowIntentV1(
            _ISSUER,
            arm,
            binding,
            V075InitialIntentKindV1.ROOT_DISCOVERY,
            0,
            1,
            caps.initial_discovery_draws_per_row,
            caps.initial_discovery_draws_per_row,
            None,
            caps.cap_profile_id,
        )
        for binding in bindings
    )
    validations = tuple(
        V075InitialRootRowIntentV1(
            _ISSUER,
            arm,
            binding,
            V075InitialIntentKindV1.ROOT_VALIDATION,
            1,
            1,
            caps.initial_validation_draws_per_row,
            INITIAL_VALIDATION_ACCEPTED_DRAW_CAP,
            discovery.intent_id,
            caps.cap_profile_id,
        )
        for binding, discovery in zip(bindings, discoveries)
    )
    return V075InitialRootAcquisitionScheduleV1(
        registered,
        arm,
        (*discoveries, *validations),
        caps,
    )


def _destination_categories(
    row: backend.V075StatisticalRowV1,
) -> tuple[str, ...]:
    result = set()
    for descriptor in row.support:
        if descriptor.failure:
            result.add("FAILURE")
        elif descriptor.terminal:
            result.add("SUCCESS_TERMINAL")
        else:
            result.add("ACTIVE_STATE")
    if not result:
        _fail("selected frontier row has no observed support category")
    return tuple(sorted(result))


def replay_v075_target_portable_feature_v2(
    *,
    node: planners.V075LearnedStateNodeV1,
    row: backend.V075StatisticalRowV1,
    choice: planners.V075PolicyStateChoiceV1,
) -> V075PortableAcquisitionCoreFeatureReplayV2:
    """Compile only sample-independent public feature fields."""

    if (
        type(node) is not planners.V075LearnedStateNodeV1
        or type(row) is not backend.V075StatisticalRowV1
        or type(choice) is not planners.V075PolicyStateChoiceV1
        or row not in node.rows
        or row.row_id not in choice.row_ids
        or choice.state_id != node.state_id
    ):
        _fail("portable target feature inputs are stale or transplanted")
    stage = "ROOT" if row.remaining_horizon == 2 else "CONTINUATION"
    component = len(choice.ground_actions) > 1
    selected_category = (
        f"{stage}_CONCRETIZER_COMPONENT"
        if component
        else f"{stage}_SELECTED"
    )
    return V075PortableAcquisitionCoreFeatureReplayV2(
        stage,
        selected_category,
        _count_bin(len(node.catalogue.actions)),
        _count_bin(len(choice.ground_actions)),
        _destination_categories(row),
    )


def _prior_fields(
    *,
    source_view: V075SourceProposalViewV1,
    feature_key: str,
) -> tuple[V075PriorDispositionV1, Fraction | None, Fraction, Fraction]:
    q = source_view.midrank_for(feature_key)
    if source_view.arm is worker.V075WorkerArmV1.NO_PRIOR:
        return (
            V075PriorDispositionV1.NO_PRIOR_NEUTRAL,
            None,
            Fraction(1),
            Fraction(1),
        )
    if source_view.arm is worker.V075WorkerArmV1.OOD_ABSTENTION:
        return (
            V075PriorDispositionV1.OOD_SCHEMA_ABSTAINED,
            None,
            Fraction(1),
            Fraction(1),
        )
    if q is None:
        return (
            (
                V075PriorDispositionV1.SOURCE_FEATURE_NO_MATCH_NEUTRAL
                if source_view.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                else V075PriorDispositionV1.WRONG_FEATURE_NO_MATCH_NEUTRAL
            ),
            None,
            Fraction(1),
            Fraction(1),
        )
    applied = (
        q
        if source_view.arm
        is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        else 1 - q
    )
    multiplier = Fraction(1, 2) + Fraction(3, 2) * applied
    return (
        (
            V075PriorDispositionV1.SOURCE_APPLIED
            if source_view.arm
            is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            else V075PriorDispositionV1.WRONG_REVERSED_APPLIED
        ),
        q,
        applied,
        multiplier,
    )


def _latest_validation_stream(
    *,
    result: batch_native.V075BatchNativeBackendResultV1,
    row_binding_id: str,
) -> tuple[public_graph.V075TransitionStreamIdentityV1, int, int]:
    streams: dict[
        str,
        list[Any],
    ] = {}
    for item in result.request.batches:
        stream = item.request.stream_identity
        if (
            stream.row_binding_id == row_binding_id
            and stream.lane is public_graph.V075ObservationLaneV1.VALIDATION
        ):
            streams.setdefault(stream.stream_id, []).append(item)
    if not streams:
        _fail("selected frontier row has no batch-native validation prefix")
    ranked = sorted(
        (
            (values[0].request.stream_identity.observer_epoch_index, key, values)
            for key, values in streams.items()
        )
    )
    latest_epoch = ranked[-1][0]
    latest = tuple(item for item in ranked if item[0] == latest_epoch)
    if len(latest) != 1:
        _fail("selected row has multiple latest validation streams")
    _epoch, _stream_id, batches = latest[0]
    ordered = tuple(
        sorted(batches, key=lambda item: item.request.accepted_draw_start)
    )
    expected = 1
    caps = set()
    for item in ordered:
        if item.request.accepted_draw_start != expected:
            _fail("selected validation prefix is gapped or reordered")
        expected = item.request.accepted_draw_end + 1
        caps.add(item.request.accepted_draw_cap)
    if len(caps) != 1:
        _fail("selected validation prefix changed its hard cap")
    return ordered[0].request.stream_identity, expected - 1, next(iter(caps))


@dataclass(frozen=True, slots=True)
class V075AdaptiveAcquisitionCandidateV1:
    _issuer: object = field(repr=False, compare=False)
    batch_result_id: str
    planner_result_id: str
    envelope_id: str
    round_index: int
    arm: worker.V075WorkerArmV1
    row_id: str
    row_binding_id: str
    stream_id: str
    observer_epoch_index: int
    current_accepted_draw_count: int
    stream_accepted_draw_cap: int
    feature: V075PortableAcquisitionCoreFeatureReplayV2
    source_view_id: str
    prior_disposition: V075PriorDispositionV1
    source_mean_midrank: Fraction | None
    applied_midrank: Fraction
    prior_multiplier: Fraction
    uncertainty_width: Fraction
    base_priority: Fraction
    ranking_score: Fraction
    incremental_draw_count: int

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("adaptive candidates are compiler-issued only")
        for value, name in (
            (self.batch_result_id, "candidate batch result"),
            (self.planner_result_id, "candidate planner result"),
            (self.envelope_id, "candidate failed envelope"),
            (self.row_id, "candidate row"),
            (self.row_binding_id, "candidate row binding"),
            (self.stream_id, "candidate validation stream"),
            (self.source_view_id, "candidate source view"),
        ):
            _cid(value, name)
        if (
            self.round_index not in (1, 2)
            or self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or type(self.feature) is not V075PortableAcquisitionCoreFeatureReplayV2
            or type(self.prior_disposition) is not V075PriorDispositionV1
            or type(self.applied_midrank) is not Fraction
            or not 0 <= self.applied_midrank <= 1
            or type(self.prior_multiplier) is not Fraction
            or type(self.uncertainty_width) is not Fraction
            or self.uncertainty_width <= 0
            or type(self.base_priority) is not Fraction
            or type(self.ranking_score) is not Fraction
            or self.incremental_draw_count
            != worker.V075WorkerCapProfileV1().promotion_validation_draws_per_round
            or self.base_priority
            != self.uncertainty_width / self.incremental_draw_count
            or self.ranking_score != self.base_priority * self.prior_multiplier
            or self.current_accepted_draw_count <= 0
            or self.stream_accepted_draw_cap <= 0
        ):
            _fail("adaptive candidate arithmetic or identity is malformed")
        if self.source_mean_midrank is not None and (
            type(self.source_mean_midrank) is not Fraction
            or not 0 <= self.source_mean_midrank <= 1
        ):
            _fail("candidate source midrank is malformed")
        applied = self.prior_disposition in {
            V075PriorDispositionV1.SOURCE_APPLIED,
            V075PriorDispositionV1.WRONG_REVERSED_APPLIED,
        }
        if (
            applied != (self.source_mean_midrank is not None)
            or (
                not applied
                and (
                    self.applied_midrank != 1
                    or self.prior_multiplier != 1
                )
            )
            or (
                applied
                and self.prior_multiplier
                != Fraction(1, 2)
                + Fraction(3, 2) * self.applied_midrank
            )
        ):
            _fail("candidate prior disposition leaked or altered a midrank")

    @property
    def cap_eligible(self) -> bool:
        return (
            self.current_accepted_draw_count + self.incremental_draw_count
            <= self.stream_accepted_draw_cap
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_acquisition_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "batch_result_id": self.batch_result_id,
            "planner_result_id": self.planner_result_id,
            "failed_envelope_id": self.envelope_id,
            "round_index": self.round_index,
            "arm": self.arm.value,
            "row_id": self.row_id,
            "row_binding_id": self.row_binding_id,
            "stream_id": self.stream_id,
            "observer_epoch_index": self.observer_epoch_index,
            "current_accepted_draw_count": self.current_accepted_draw_count,
            "stream_accepted_draw_cap": self.stream_accepted_draw_cap,
            "feature_key": self.feature.feature_key,
            "source_view_id": self.source_view_id,
            "prior_disposition": self.prior_disposition.value,
            "source_mean_midrank": (
                None
                if self.source_mean_midrank is None
                else _fdoc(self.source_mean_midrank)
            ),
            "applied_midrank": _fdoc(self.applied_midrank),
            "prior_multiplier": _fdoc(self.prior_multiplier),
            "uncertainty_width": _fdoc(self.uncertainty_width),
            "base_priority": _fdoc(self.base_priority),
            "ranking_score": _fdoc(self.ranking_score),
            "incremental_draw_count": self.incremental_draw_count,
            "cap_eligible": self.cap_eligible,
            "ranking_only": True,
            "model_interval_or_certificate_modified": False,
        }

    @property
    def candidate_id(self) -> str:
        return _hash("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "feature": self.feature.to_document(),
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveCandidateFrontierV1:
    batch_result_id: str
    planner_result_id: str
    failed_envelope_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    source_view: V075SourceProposalViewV1
    candidate_registry: tuple[V075AdaptiveAcquisitionCandidateV1, ...]
    ranked_candidate_ids: tuple[str, ...]
    preproposal_batch_ids: tuple[str, ...]
    total_online_draws_before_round: int
    cap_profile_id: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.batch_result_id, "frontier batch result"),
            (self.planner_result_id, "frontier planner result"),
            (self.failed_envelope_id, "frontier failed envelope"),
            (self.occurrence_id, "frontier occurrence"),
            (self.context_id, "frontier context"),
            (self.cap_profile_id, "frontier cap profile"),
        ):
            _cid(value, name)
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or type(self.source_view) is not V075SourceProposalViewV1
            or self.source_view.arm is not self.arm
            or type(self.candidate_registry) is not tuple
            or tuple(item.candidate_id for item in self.candidate_registry)
            != tuple(sorted({item.candidate_id for item in self.candidate_registry}))
            or self.ranked_candidate_ids
            != tuple(
                item.candidate_id
                for item in sorted(
                    self.candidate_registry,
                    key=lambda item: (
                        -item.ranking_score,
                        -item.base_priority,
                        item.candidate_id,
                    ),
                )
            )
            or self.preproposal_batch_ids
            != tuple(sorted(set(self.preproposal_batch_ids)))
            or type(self.total_online_draws_before_round) is not int
            or self.total_online_draws_before_round <= 0
            or self.cap_profile_id
            != worker.V075WorkerCapProfileV1().cap_profile_id
        ):
            _fail("adaptive candidate frontier is malformed or reordered")
        if any(
            item.batch_result_id != self.batch_result_id
            or item.planner_result_id != self.planner_result_id
            or item.envelope_id != self.failed_envelope_id
            or item.round_index != self.round_index
            or item.arm is not self.arm
            or item.source_view_id != self.source_view.source_view_id
            for item in self.candidate_registry
        ):
            _fail("adaptive frontier contains a transplanted candidate")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_acquisition_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "batch_result_id": self.batch_result_id,
            "planner_result_id": self.planner_result_id,
            "failed_envelope_id": self.failed_envelope_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "source_view_id": self.source_view.source_view_id,
            "candidate_ids": [
                item.candidate_id for item in self.candidate_registry
            ],
            "ranked_candidate_ids": list(self.ranked_candidate_ids),
            "preproposal_batch_ids": list(self.preproposal_batch_ids),
            "total_online_draws_before_round": (
                self.total_online_draws_before_round
            ),
            "cap_profile_id": self.cap_profile_id,
            "feature_schema_id": SOURCE_FEATURE_SCHEMA_ID,
            "failed_proof_frontier_only": True,
            "frozen_before_authorized_observer_access": True,
            "prior_changes_model_or_certificate": False,
        }

    @property
    def frontier_id(self) -> str:
        return _hash("frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_view": self.source_view.to_document(),
            "candidates": [item.to_document() for item in self.candidate_registry],
            "frontier_id": self.frontier_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundRowIntentV1:
    _issuer: object = field(repr=False, compare=False)
    frontier_id: str
    candidate_id: str
    occurrence_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    row_binding_id: str
    stream_id: str
    observer_epoch_index: int
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("adaptive round intents are compiler-issued only")
        for value, name in (
            (self.frontier_id, "round intent frontier"),
            (self.candidate_id, "round intent candidate"),
            (self.occurrence_id, "round intent occurrence"),
            (self.row_binding_id, "round intent row"),
            (self.stream_id, "round intent stream"),
        ):
            _cid(value, name)
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or self.observer_epoch_index <= 0
            or self.accepted_draw_start <= 1
            or self.accepted_draw_count
            != worker.V075WorkerCapProfileV1().promotion_validation_draws_per_round
            or self.accepted_draw_cap < self.accepted_draw_end
        ):
            _fail("adaptive round intent is malformed or over cap")

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_row_intent.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_id": self.frontier_id,
            "candidate_id": self.candidate_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "row_binding_id": self.row_binding_id,
            "stream_id": self.stream_id,
            "lane": public_graph.V075ObservationLaneV1.VALIDATION.value,
            "observer_epoch_index": self.observer_epoch_index,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "extend_existing_prefix": True,
            "new_stream_or_reroll_allowed": False,
        }

    @property
    def intent_id(self) -> str:
        return _hash("round_intent", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "intent_id": self.intent_id}


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundAuthorizationV1:
    frontier: V075AdaptiveCandidateFrontierV1
    status: V075RoundProposalStatusV1
    selected_candidate_id: str | None
    intent: V075AdaptiveRoundRowIntentV1 | None
    authorization_sequence: int
    minimum_observer_sequence: int

    def __post_init__(self) -> None:
        if (
            type(self.frontier) is not V075AdaptiveCandidateFrontierV1
            or type(self.status) is not V075RoundProposalStatusV1
            or self.authorization_sequence != 2 * self.frontier.round_index - 1
            or self.minimum_observer_sequence != self.authorization_sequence + 1
        ):
            _fail("adaptive round authorization sequence is malformed")
        authorized = self.status is V075RoundProposalStatusV1.AUTHORIZED
        if authorized:
            candidates = {
                item.candidate_id: item
                for item in self.frontier.candidate_registry
            }
            selected = candidates.get(self.selected_candidate_id)
            eligible = tuple(
                item
                for item in sorted(
                    self.frontier.candidate_registry,
                    key=lambda value: (
                        -value.ranking_score,
                        -value.base_priority,
                        value.candidate_id,
                    ),
                )
                if item.cap_eligible
                and (
                    self.frontier.total_online_draws_before_round
                    + item.incremental_draw_count
                    <= worker.V075WorkerCapProfileV1()
                    .maximum_incremental_draws_per_adaptive_arm
                )
            )
            if (
                selected is None
                or not selected.cap_eligible
                or not eligible
                or selected != eligible[0]
                or type(self.intent) is not V075AdaptiveRoundRowIntentV1
                or self.intent.frontier_id != self.frontier.frontier_id
                or self.intent.candidate_id != selected.candidate_id
                or self.intent.occurrence_id != self.frontier.occurrence_id
                or self.intent.arm is not self.frontier.arm
                or self.intent.round_index != self.frontier.round_index
                or self.intent.row_binding_id != selected.row_binding_id
                or self.intent.stream_id != selected.stream_id
                or self.intent.observer_epoch_index
                != selected.observer_epoch_index
                or self.intent.accepted_draw_start
                != selected.current_accepted_draw_count + 1
                or self.intent.accepted_draw_count
                != selected.incremental_draw_count
                or self.intent.accepted_draw_cap
                != selected.stream_accepted_draw_cap
            ):
                _fail("adaptive authorization did not select its frozen rank one")
        elif self.selected_candidate_id is not None or self.intent is not None:
            _fail("nonauthorization cannot carry a selected row intent")
        if (
            self.status
            is V075RoundProposalStatusV1.NO_UNCERTAIN_SELECTED_FRONTIER
        ) != (not self.frontier.candidate_registry):
            _fail("no-frontier status disagrees with candidate registry")
        if (
            self.status
            is V075RoundProposalStatusV1.INCREMENTAL_CAP_EXHAUSTED
            and (
                not self.frontier.candidate_registry
                or any(
                    item.cap_eligible
                    and (
                        self.frontier.total_online_draws_before_round
                        + item.incremental_draw_count
                        <= worker.V075WorkerCapProfileV1()
                        .maximum_incremental_draws_per_adaptive_arm
                    )
                    for item in self.frontier.candidate_registry
                )
            )
        ):
            _fail("cap-exhausted status has an eligible candidate")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_id": self.frontier.frontier_id,
            "status": self.status.value,
            "selected_candidate_id": self.selected_candidate_id,
            "intent_id": None if self.intent is None else self.intent.intent_id,
            "authorization_sequence": self.authorization_sequence,
            "minimum_observer_sequence": self.minimum_observer_sequence,
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
        }

    @property
    def authorization_id(self) -> str:
        return _hash("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": self.frontier.to_document(),
            "intent": None if self.intent is None else self.intent.to_document(),
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundExecutionVerificationV1:
    authorization_id: str
    intent_id: str
    prior_batch_result_id: str
    resulting_batch_result_id: str
    appended_batch_ids: tuple[str, ...]
    exact_frozen_prefix_executed: bool = True

    def __post_init__(self) -> None:
        for value, name in (
            (self.authorization_id, "execution authorization"),
            (self.intent_id, "execution intent"),
            (self.prior_batch_result_id, "execution prior result"),
            (self.resulting_batch_result_id, "execution resulting result"),
        ):
            _cid(value, name)
        if (
            self.appended_batch_ids
            != tuple(sorted(set(self.appended_batch_ids)))
            or not self.appended_batch_ids
            or self.exact_frozen_prefix_executed is not True
        ):
            _fail("adaptive execution verification is malformed")
        for item in self.appended_batch_ids:
            _cid(item, "execution appended batch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_adaptive_round_execution_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "authorization_id": self.authorization_id,
            "intent_id": self.intent_id,
            "prior_batch_result_id": self.prior_batch_result_id,
            "resulting_batch_result_id": self.resulting_batch_result_id,
            "appended_batch_ids": list(self.appended_batch_ids),
            "exact_frozen_prefix_executed": True,
            "post_run_reorder_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return _hash("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _planner_result_id(
    result: planners.V075SupportPlannerResultV1,
) -> str:
    return result.result_id


def _verify_failed_planner_result(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
) -> None:
    if (
        type(batch_result) is not batch_native.V075BatchNativeBackendResultV1
        or type(planner_result) is not planners.V075SupportPlannerResultV1
        or planner_result.route
        is not planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT
        or planner_result.graph.backend_result
        != batch_result.route_native_result
    ):
        _fail("failed planner result is untyped or batch-transplanted")
    recomputed = planners.plan_v075_exact_h2_abstract_v1(
        planner_result.graph
    )
    if recomputed != planner_result:
        _fail("failed planner result differs from exact semantic replay")
    if (
        planner_result.status
        not in {
            planners.V075PlannerStatusV1.STATISTICAL_ENVELOPE_NOT_CERTIFIED,
            planners.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY,
        }
        or planner_result.policy is None
        or planner_result.envelope is None
    ):
        _fail(
            "adaptive acquisition requires a typed diagnostic policy and "
            "failed envelope"
        )
    threshold = worker.V075WorkerThresholdProfileV1()
    if (
        planner_result.envelope.selected_failure_upper
        <= threshold.risk_tolerance
        and planner_result.envelope.normalized_regret_upper
        <= threshold.normalized_regret_tolerance
    ):
        _fail("certified envelope cannot trigger adaptive acquisition")


def _selected_rows(
    planner_result: planners.V075SupportPlannerResultV1,
) -> tuple[
    tuple[
        planners.V075LearnedStateNodeV1,
        backend.V075StatisticalRowV1,
        planners.V075PolicyStateChoiceV1,
    ],
    ...,
]:
    assert planner_result.policy is not None
    nodes = {item.state_id: item for item in planner_result.graph.nodes}
    rows = {
        item.row_id: item
        for item in planner_result.graph.nodes
        for item in item.rows
    }
    selected = []
    seen: set[str] = set()
    for decision in planner_result.policy.decisions:
        for choice in decision.state_choices:
            node = nodes.get(choice.state_id)
            if node is None:
                _fail("diagnostic policy references an unknown graph state")
            for row_id in choice.row_ids:
                row = rows.get(row_id)
                if row is None or row_id in seen:
                    _fail("diagnostic policy row is missing or duplicated")
                seen.add(row_id)
                selected.append((node, row, choice))
    result = tuple(sorted(selected, key=lambda item: item[1].row_id))
    if (
        planner_result.status
        is planners.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        and set(planner_result.diagnostic_failed_frontier_row_ids)
        != {item[1].row_id for item in result}
    ):
        _fail("planner diagnostic frontier differs from its policy choices")
    return result


def freeze_v075_adaptive_candidate_frontier_v1(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    source_view: V075SourceProposalViewV1,
    round_index: int,
    previous_execution: V075AdaptiveRoundExecutionVerificationV1 | None = None,
) -> V075AdaptiveCandidateFrontierV1:
    """Recompute one failed selected-policy frontier without target access."""

    if round_index not in (1, 2):
        _fail("adaptive round index exceeds the registered two-round cap")
    _verify_failed_planner_result(
        batch_result=batch_result,
        planner_result=planner_result,
    )
    if (
        type(source_view) is not V075SourceProposalViewV1
        or source_view.arm is not batch_result.request.arm
    ):
        _fail("proposal view arm differs from the batch-native occurrence")
    if round_index == 1:
        if previous_execution is not None:
            _fail("round one cannot consume a prior execution")
    elif (
        type(previous_execution) is not V075AdaptiveRoundExecutionVerificationV1
        or previous_execution.resulting_batch_result_id
        != batch_result.result_id
    ):
        _fail("round two lacks the exact verified round-one execution")
    assert planner_result.envelope is not None
    candidates: list[V075AdaptiveAcquisitionCandidateV1] = []
    for node, row, choice in _selected_rows(planner_result):
        width = sum(
            (
                interval.upper_probability - interval.lower_probability
                for interval in row.intervals
            ),
            Fraction(0),
        )
        if width <= 0:
            continue
        feature = replay_v075_target_portable_feature_v2(
            node=node,
            row=row,
            choice=choice,
        )
        disposition, source_q, applied_q, multiplier = _prior_fields(
            source_view=source_view,
            feature_key=feature.feature_key,
        )
        stream, current_count, accepted_cap = _latest_validation_stream(
            result=batch_result,
            row_binding_id=row.row_binding_id,
        )
        increment = (
            worker.V075WorkerCapProfileV1()
            .promotion_validation_draws_per_round
        )
        base = width / increment
        candidates.append(
            V075AdaptiveAcquisitionCandidateV1(
                _ISSUER,
                batch_result.result_id,
                _planner_result_id(planner_result),
                planner_result.envelope.envelope_id,
                round_index,
                source_view.arm,
                row.row_id,
                row.row_binding_id,
                stream.stream_id,
                stream.observer_epoch_index,
                current_count,
                accepted_cap,
                feature,
                source_view.source_view_id,
                disposition,
                source_q,
                applied_q,
                multiplier,
                width,
                base,
                base * multiplier,
                increment,
            )
        )
    registry = tuple(sorted(candidates, key=lambda item: item.candidate_id))
    ranked = tuple(
        item.candidate_id
        for item in sorted(
            registry,
            key=lambda item: (
                -item.ranking_score,
                -item.base_priority,
                item.candidate_id,
            ),
        )
    )
    all_batches = tuple(
        sorted(item.batch_id for item in batch_result.request.batches)
    )
    total_draws = sum(
        item.request.accepted_draw_count
        for item in batch_result.request.batches
    )
    return V075AdaptiveCandidateFrontierV1(
        batch_result.result_id,
        _planner_result_id(planner_result),
        planner_result.envelope.envelope_id,
        batch_result.request.occurrence_id,
        batch_result.request.context.context_id,
        source_view.arm,
        round_index,
        source_view,
        registry,
        ranked,
        all_batches,
        total_draws,
        worker.V075WorkerCapProfileV1().cap_profile_id,
    )


def authorize_v075_adaptive_acquisition_round_v1(
    frontier: V075AdaptiveCandidateFrontierV1,
) -> V075AdaptiveRoundAuthorizationV1:
    if type(frontier) is not V075AdaptiveCandidateFrontierV1:
        _fail("round authorizer requires one exact frozen frontier")
    if not frontier.candidate_registry:
        return V075AdaptiveRoundAuthorizationV1(
            frontier,
            V075RoundProposalStatusV1.NO_UNCERTAIN_SELECTED_FRONTIER,
            None,
            None,
            2 * frontier.round_index - 1,
            2 * frontier.round_index,
        )
    eligible = tuple(
        item
        for item in sorted(
            frontier.candidate_registry,
            key=lambda value: (
                -value.ranking_score,
                -value.base_priority,
                value.candidate_id,
            ),
        )
        if item.cap_eligible
        and (
            frontier.total_online_draws_before_round
            + item.incremental_draw_count
            <= worker.V075WorkerCapProfileV1()
            .maximum_incremental_draws_per_adaptive_arm
        )
    )
    if not eligible:
        return V075AdaptiveRoundAuthorizationV1(
            frontier,
            V075RoundProposalStatusV1.INCREMENTAL_CAP_EXHAUSTED,
            None,
            None,
            2 * frontier.round_index - 1,
            2 * frontier.round_index,
        )
    selected = eligible[0]
    intent = V075AdaptiveRoundRowIntentV1(
        _ISSUER,
        frontier.frontier_id,
        selected.candidate_id,
        frontier.occurrence_id,
        frontier.arm,
        frontier.round_index,
        selected.row_binding_id,
        selected.stream_id,
        selected.observer_epoch_index,
        selected.current_accepted_draw_count + 1,
        selected.incremental_draw_count,
        selected.stream_accepted_draw_cap,
    )
    return V075AdaptiveRoundAuthorizationV1(
        frontier,
        V075RoundProposalStatusV1.AUTHORIZED,
        selected.candidate_id,
        intent,
        2 * frontier.round_index - 1,
        2 * frontier.round_index,
    )


def verify_v075_adaptive_round_execution_v1(
    *,
    authorization: V075AdaptiveRoundAuthorizationV1,
    resulting_batch_result: batch_native.V075BatchNativeBackendResultV1,
) -> V075AdaptiveRoundExecutionVerificationV1:
    """Verify exact append-only execution of the frozen row intent."""

    if (
        type(authorization) is not V075AdaptiveRoundAuthorizationV1
        or authorization.status is not V075RoundProposalStatusV1.AUTHORIZED
        or authorization.intent is None
        or type(resulting_batch_result)
        is not batch_native.V075BatchNativeBackendResultV1
    ):
        _fail("execution verifier requires an authorized intent and batch result")
    intent = authorization.intent
    frontier = authorization.frontier
    if (
        resulting_batch_result.request.occurrence_id != frontier.occurrence_id
        or resulting_batch_result.request.arm is not frontier.arm
        or resulting_batch_result.request.context.context_id
        != frontier.context_id
    ):
        _fail("executed acquisition was transplanted across occurrence or arm")
    before = set(frontier.preproposal_batch_ids)
    after = {item.batch_id for item in resulting_batch_result.request.batches}
    if not before < after:
        _fail("executed acquisition did not append to the frozen batch set")
    appended = tuple(
        sorted(
            (
                item
                for item in resulting_batch_result.request.batches
                if item.batch_id not in before
            ),
            key=lambda item: item.request.accepted_draw_start,
        )
    )
    if (
        any(
            item.request.stream_identity.stream_id != intent.stream_id
            or item.request.stream_identity.row_binding_id
            != intent.row_binding_id
            or item.request.stream_identity.lane
            is not public_graph.V075ObservationLaneV1.VALIDATION
            or item.request.stream_identity.observer_epoch_index
            != intent.observer_epoch_index
            or item.request.accepted_draw_cap != intent.accepted_draw_cap
            for item in appended
        )
        or appended[0].request.accepted_draw_start
        != intent.accepted_draw_start
        or appended[-1].request.accepted_draw_end != intent.accepted_draw_end
        or any(
            left.request.accepted_draw_end + 1
            != right.request.accepted_draw_start
            for left, right in zip(appended, appended[1:])
        )
        or sum(item.request.accepted_draw_count for item in appended)
        != intent.accepted_draw_count
    ):
        _fail("post-run batches reordered or replaced the frozen prefix intent")
    return V075AdaptiveRoundExecutionVerificationV1(
        authorization.authorization_id,
        intent.intent_id,
        frontier.batch_result_id,
        resulting_batch_result.result_id,
        tuple(sorted(item.batch_id for item in appended)),
    )


__all__ = [
    "INITIAL_VALIDATION_ACCEPTED_DRAW_CAP",
    "MAX_ADAPTIVE_ROUNDS",
    "OOD_MISMATCH_FEATURE_SCHEMA_ID",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "REGISTERED_APPLIED_SOURCE_KEYS",
    "REGISTERED_APPLIED_SOURCE_MIDRANKS",
    "SOURCE_FEATURE_SCHEMA_ID",
    "V075AdaptiveAcquisitionCandidateV1",
    "V075AdaptiveAcquisitionInvariantViolation",
    "V075AdaptiveCandidateFrontierV1",
    "V075AdaptiveRoundAuthorizationV1",
    "V075AdaptiveRoundExecutionVerificationV1",
    "V075AdaptiveRoundRowIntentV1",
    "V075InitialIntentKindV1",
    "V075InitialRootAcquisitionScheduleV1",
    "V075InitialRootRowIntentV1",
    "V075PortableAcquisitionCoreFeatureReplayV2",
    "V075PriorDispositionV1",
    "V075RoundProposalStatusV1",
    "V075SourceProposalViewV1",
    "authorize_v075_adaptive_acquisition_round_v1",
    "freeze_v075_adaptive_candidate_frontier_v1",
    "freeze_v075_initial_root_acquisition_schedule_v1",
    "freeze_v075_source_proposal_view_v1",
    "replay_v075_target_portable_feature_v2",
    "verify_v075_adaptive_round_execution_v1",
]
