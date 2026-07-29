"""Target-free production occurrence-plan authority for V0-075.

The authority freezes the complete context-major fifteen-occurrence schedule
before any target observation.  Scientific ordinals are zero based; transport
ordinals are the corresponding one-based values.  Each entry contains the
exact batch-native occurrence identity used by the downstream statistical
backend.

The SOURCE arm is bound only to the independently replayed, already tracked
V0-075 source adapter and verification artifacts.  No caller may supply source
totals, a source identity, target evidence, an observer, or a target callback.
This module never opens an observer and never samples a target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_tracked_source_authority_v1 as tracked_source


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_production_occurrence_plan_v1"
EXPECTED_CONTEXT_COUNT = 3
EXPECTED_ARM_COUNT = 5
EXPECTED_OCCURRENCE_COUNT = 15
MAX_PLAN_BYTES = 2 * 1024 * 1024

REGISTERED_ARM_ORDER = tuple(
    worker.V075WorkerArmV1(value) for value in public.ARM_ORDER
)

if (
    REGISTERED_ARM_ORDER != tuple(worker.V075WorkerArmV1)
    or len(REGISTERED_ARM_ORDER) != EXPECTED_ARM_COUNT
):
    raise RuntimeError("V0-075 production-plan arm registry drifted")


DOMAIN_TAGS = {
    "entry": "acfqp:v075-production-occurrence-plan-entry:v1",
    "plan": "acfqp:v075-production-occurrence-plan:v1",
    "verification": (
        "acfqp:v075-production-occurrence-plan-verification:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 production-plan content domains overlap")


class V075ProductionOccurrencePlanInvariantViolation(ValueError):
    """A source binding, namespace, order, identity, or replay was invalid."""


def _fail(message: str) -> None:
    raise V075ProductionOccurrencePlanInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _read_bound_regular_file_v1(
    root: Path,
    relative_path: str,
    *,
    maximum_bytes: int,
) -> bytes:
    if (
        type(relative_path) is not str
        or not relative_path
        or relative_path.startswith("/")
        or ".." in relative_path.split("/")
    ):
        _fail("tracked source path is not one canonical relative path")
    try:
        candidate = root
        for component in relative_path.split("/"):
            candidate = candidate / component
            if candidate.is_symlink():
                _fail("tracked source path contains a symlink")
        before = candidate.stat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > maximum_bytes
        ):
            _fail("tracked source artifact is absent, empty, or over cap")
        raw = candidate.read_bytes()
        after = candidate.stat()
    except OSError as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            "tracked source artifact disappeared or became unreadable"
        ) from error
    if (
        len(raw) != before.st_size
        or before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        _fail("tracked source artifact changed during the bound read")
    return raw


def _load_tracked_source_authority_graph_v1(
    repository_root: str | Path,
) -> tuple[
    worker.V075SourcePriorTransportV1,
    tracked_source.V075TrackedSourceAuthorityBundleV1,
    tracked_source.V075TrackedSourceAuthorityVerificationV1,
]:
    try:
        root = Path(repository_root).resolve(strict=True)
    except (OSError, TypeError, ValueError) as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            "repository root is absent or malformed"
        ) from error
    if not root.is_dir():
        _fail("repository root is not one directory")

    try:
        bundle, verification = (
            tracked_source.verify_tracked_v075_source_authorities_v1(root)
        )
    except Exception as error:
        if isinstance(error, V075ProductionOccurrencePlanInvariantViolation):
            raise
        raise V075ProductionOccurrencePlanInvariantViolation(
            f"tracked source replay failed: {error}"
        ) from error

    if (
        type(bundle)
        is not tracked_source.V075TrackedSourceAuthorityBundleV1
        or type(verification)
        is not tracked_source.V075TrackedSourceAuthorityVerificationV1
        or verification.bundle_id != bundle.bundle_id
        or verification.source_prior_adapter_id
        != bundle.source_prior_adapter_id
        or verification.source_prior_verification_id
        != bundle.source_prior_verification_id
        or verification.artifact_ids
        != tuple(item.artifact_id for item in bundle.artifacts)
    ):
        _fail("tracked source replay returned a partial authority graph")

    artifacts = {item.role: item for item in bundle.artifacts}
    expected_roles = {
        "SOURCE_PRIOR_ADAPTER",
        "SOURCE_PRIOR_ADAPTER_VERIFICATION",
    }
    if not expected_roles.issubset(artifacts):
        _fail("tracked source replay lacks the source transport pair")

    adapter_artifact = artifacts["SOURCE_PRIOR_ADAPTER"]
    verification_artifact = artifacts[
        "SOURCE_PRIOR_ADAPTER_VERIFICATION"
    ]
    adapter_bytes = _read_bound_regular_file_v1(
        root,
        adapter_artifact.repository_path,
        maximum_bytes=worker.MAX_SOURCE_PRIOR_BYTES,
    )
    verification_bytes = _read_bound_regular_file_v1(
        root,
        verification_artifact.repository_path,
        maximum_bytes=worker.MAX_SOURCE_VERIFICATION_BYTES,
    )
    if (
        len(adapter_bytes) != adapter_artifact.byte_count
        or hashlib.sha256(adapter_bytes).hexdigest()
        != adapter_artifact.canonical_bytes_sha256
        or adapter_artifact.semantic_id
        != bundle.source_prior_adapter_id
        or len(verification_bytes) != verification_artifact.byte_count
        or hashlib.sha256(verification_bytes).hexdigest()
        != verification_artifact.canonical_bytes_sha256
        or verification_artifact.semantic_id
        != bundle.source_prior_verification_id
    ):
        _fail("tracked source transport bytes differ from replayed metadata")

    try:
        transport = worker.V075SourcePriorTransportV1(
            adapter_bytes,
            verification_bytes,
            bundle.source_prior_adapter_id,
            bundle.source_prior_verification_id,
        )
    except Exception as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            f"tracked source transport binding failed: {error}"
        ) from error
    document = transport.to_document()
    if (
        document["source_only"] is not True
        or document["proposal_only"] is not True
        or document["work_reference_only"] is not True
        or document["target_fields_present"] is not False
    ):
        _fail("tracked source transport acquired a target or result channel")
    return transport, bundle, verification


def load_tracked_v075_source_prior_transport_v1(
    repository_root: str | Path,
) -> worker.V075SourcePriorTransportV1:
    """Load the exact tracked SOURCE transport without caller-owned values."""

    transport, _bundle, _verification = (
        _load_tracked_source_authority_graph_v1(repository_root)
    )
    return transport


def _validated_namespace_document_v1(
    namespace: public.V075PublicTargetTapeNamespaceV1,
) -> dict[str, Any]:
    family = public.freeze_v075_public_family_generation_v1()
    if (
        type(namespace) is not public.V075PublicTargetTapeNamespaceV1
        or namespace.family != family
    ):
        _fail("production plan requires one exact current public namespace")
    document = namespace.to_document()
    expected_external_ids = (
        namespace.remote_main_anchor.external_id,
        namespace.final_preregistration.external_id,
        namespace.observer_profile.external_id,
    )
    if (
        document.get("remote_main_anchor_id") != expected_external_ids[0]
        or document.get("final_preregistration_id")
        != expected_external_ids[1]
        or document.get("observer_profile_id") != expected_external_ids[2]
        or document.get("remote_main_anchor_claim_id")
        != namespace.remote_main_anchor.claim_id
        or document.get("final_preregistration_claim_id")
        != namespace.final_preregistration.claim_id
        or document.get("observer_profile_claim_id")
        != namespace.observer_profile.claim_id
        or document.get("family_generation_id") != family.generation_id
        or document.get("target_tape_namespace_id")
        != namespace.target_tape_namespace_id
        or len(set(expected_external_ids)) != 3
        or any(
            value in public.FORBIDDEN_HISTORICAL_TARGET_IDS
            for value in expected_external_ids
        )
    ):
        _fail(
            "namespace does not bind the exact external anchor, final "
            "preregistration, and observer-profile identities"
        )
    return document


_ENTRY_ISSUER = object()
_PLAN_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrencePlanEntryV1:
    _issuer: object = field(repr=False, compare=False)
    remote_main_anchor_id: str
    final_preregistration_id: str
    target_tape_namespace_id: str
    public_family_generation_id: str
    context_id: str
    context_ordinal: int
    arm: worker.V075WorkerArmV1
    arm_ordinal: int
    scientific_ordinal: int
    transport_ordinal: int
    threshold_profile_id: str
    cap_profile_id: str
    source_transport_id: str | None
    occurrence_identity: (
        batch_native.V075BatchNativeOccurrenceIdentityV1
    )
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.remote_main_anchor_id, "plan-entry remote-main anchor"),
            (
                self.final_preregistration_id,
                "plan-entry final preregistration",
            ),
            (
                self.target_tape_namespace_id,
                "plan-entry target namespace",
            ),
            (
                self.public_family_generation_id,
                "plan-entry public family",
            ),
            (self.context_id, "plan-entry context"),
            (
                self.threshold_profile_id,
                "plan-entry threshold profile",
            ),
            (self.cap_profile_id, "plan-entry cap profile"),
        ):
            _cid(value, field_name)
        if self.source_transport_id is not None:
            _cid(self.source_transport_id, "plan-entry source transport")
        expected_scientific = (
            self.context_ordinal * EXPECTED_ARM_COUNT + self.arm_ordinal
        )
        source_arm = (
            self.arm is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
        )
        identity = self.occurrence_identity
        if (
            self._issuer is not _ENTRY_ISSUER
            or self.remote_main_anchor_id
            in public.FORBIDDEN_HISTORICAL_TARGET_IDS
            or self.final_preregistration_id
            in public.FORBIDDEN_HISTORICAL_TARGET_IDS
            or type(self.context_ordinal) is not int
            or self.context_ordinal not in range(EXPECTED_CONTEXT_COUNT)
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.arm_ordinal) is not int
            or self.arm_ordinal not in range(EXPECTED_ARM_COUNT)
            or REGISTERED_ARM_ORDER[self.arm_ordinal] is not self.arm
            or type(self.scientific_ordinal) is not int
            or self.scientific_ordinal != expected_scientific
            or type(self.transport_ordinal) is not int
            or self.transport_ordinal != self.scientific_ordinal + 1
            or (self.source_transport_id is not None) != source_arm
            or type(identity)
            is not batch_native.V075BatchNativeOccurrenceIdentityV1
            or identity.target_tape_namespace_id
            != self.target_tape_namespace_id
            or identity.context_id != self.context_id
            or identity.arm is not self.arm
            or identity.occurrence_ordinal != self.scientific_ordinal
            or identity.threshold_profile_id != self.threshold_profile_id
            or identity.cap_profile_id != self.cap_profile_id
            or identity.source_transport_id != self.source_transport_id
        ):
            _fail("production occurrence-plan entry is stale or transplanted")
        object.__setattr__(
            self,
            "_entry_id",
            _hash("entry", self._payload()),
        )

    @property
    def occurrence_id(self) -> str:
        return self.occurrence_identity.occurrence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_occurrence_plan_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "public_family_generation_id": (
                self.public_family_generation_id
            ),
            "context_id": self.context_id,
            "context_ordinal": self.context_ordinal,
            "arm": self.arm.value,
            "arm_ordinal": self.arm_ordinal,
            "scientific_ordinal": self.scientific_ordinal,
            "transport_ordinal": self.transport_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "cap_profile_id": self.cap_profile_id,
            "source_transport_id": self.source_transport_id,
            "occurrence_id": self.occurrence_id,
            "frozen_before_observation": True,
            "observer_open_calls_at_freeze": 0,
            "target_accesses_at_freeze": 0,
            "observation_batches_at_freeze": 0,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence_identity": self.occurrence_identity.to_document(),
            "entry_id": self.entry_id,
        }


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrencePlanV1:
    _issuer: object = field(repr=False, compare=False)
    remote_main_anchor_id: str
    final_preregistration_id: str
    target_tape_namespace_id: str
    public_family_generation_id: str
    context_ids: tuple[str, ...]
    threshold_profile: worker.V075WorkerThresholdProfileV1
    cap_profile: worker.V075WorkerCapProfileV1
    source_prior_transport: worker.V075SourcePriorTransportV1 = field(
        repr=False
    )
    tracked_source_bundle_id: str
    tracked_source_verification_id: str
    entries: tuple[V075ProductionOccurrencePlanEntryV1, ...]
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.remote_main_anchor_id, "plan remote-main anchor"),
            (
                self.final_preregistration_id,
                "plan final preregistration",
            ),
            (self.target_tape_namespace_id, "plan target namespace"),
            (
                self.public_family_generation_id,
                "plan public family",
            ),
            (self.tracked_source_bundle_id, "plan tracked source bundle"),
            (
                self.tracked_source_verification_id,
                "plan tracked source verification",
            ),
        ):
            _cid(value, field_name)
        family = public.freeze_v075_public_family_generation_v1()
        expected_context_ids = tuple(
            item.context_id for item in family.replicate_contexts
        )
        if (
            self._issuer is not _PLAN_ISSUER
            or self.remote_main_anchor_id
            in public.FORBIDDEN_HISTORICAL_TARGET_IDS
            or self.final_preregistration_id
            in public.FORBIDDEN_HISTORICAL_TARGET_IDS
            or self.public_family_generation_id != family.generation_id
            or type(self.context_ids) is not tuple
            or self.context_ids != expected_context_ids
            or len(set(self.context_ids)) != EXPECTED_CONTEXT_COUNT
            or type(self.threshold_profile)
            is not worker.V075WorkerThresholdProfileV1
            or self.threshold_profile != worker.V075WorkerThresholdProfileV1()
            or type(self.cap_profile) is not worker.V075WorkerCapProfileV1
            or self.cap_profile != worker.V075WorkerCapProfileV1()
            or type(self.source_prior_transport)
            is not worker.V075SourcePriorTransportV1
            or type(self.entries) is not tuple
            or len(self.entries) != EXPECTED_OCCURRENCE_COUNT
            or any(
                type(item) is not V075ProductionOccurrencePlanEntryV1
                for item in self.entries
            )
            or tuple(item.scientific_ordinal for item in self.entries)
            != tuple(range(EXPECTED_OCCURRENCE_COUNT))
            or tuple(item.transport_ordinal for item in self.entries)
            != tuple(range(1, EXPECTED_OCCURRENCE_COUNT + 1))
            or len({item.entry_id for item in self.entries})
            != EXPECTED_OCCURRENCE_COUNT
            or len({item.occurrence_id for item in self.entries})
            != EXPECTED_OCCURRENCE_COUNT
        ):
            _fail("production occurrence plan is incomplete or reordered")

        source_transport_id = self.source_prior_transport.transport_id
        threshold_id = self.threshold_profile.threshold_profile_id
        cap_id = self.cap_profile.cap_profile_id
        for item in self.entries:
            expected_context = family.replicate_contexts[
                item.context_ordinal
            ]
            if (
                item.remote_main_anchor_id != self.remote_main_anchor_id
                or item.final_preregistration_id
                != self.final_preregistration_id
                or item.target_tape_namespace_id
                != self.target_tape_namespace_id
                or item.public_family_generation_id
                != self.public_family_generation_id
                or item.context_id != expected_context.context_id
                or item.threshold_profile_id != threshold_id
                or item.cap_profile_id != cap_id
                or item.source_transport_id
                != (
                    source_transport_id
                    if item.arm
                    is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                    else None
                )
            ):
                _fail("production occurrence plan contains a transplant")
        object.__setattr__(
            self,
            "_plan_id",
            _hash("plan", self._payload()),
        )

    @property
    def source_transport_id(self) -> str:
        return self.source_prior_transport.transport_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_occurrence_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "public_family_generation_id": (
                self.public_family_generation_id
            ),
            "context_ids": list(self.context_ids),
            "arm_order": [item.value for item in REGISTERED_ARM_ORDER],
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "cap_profile_id": self.cap_profile.cap_profile_id,
            "source_transport_id": self.source_transport_id,
            "source_prior_adapter_id": (
                self.source_prior_transport.adapter_id
            ),
            "source_prior_verification_id": (
                self.source_prior_transport.verification_id
            ),
            "tracked_source_bundle_id": self.tracked_source_bundle_id,
            "tracked_source_verification_id": (
                self.tracked_source_verification_id
            ),
            "entry_ids": [item.entry_id for item in self.entries],
            "occurrence_ids": [
                item.occurrence_id for item in self.entries
            ],
            "scientific_ordinals": list(
                range(EXPECTED_OCCURRENCE_COUNT)
            ),
            "transport_ordinals": list(
                range(1, EXPECTED_OCCURRENCE_COUNT + 1)
            ),
            "order": "CONTEXT_MAJOR_THEN_FROZEN_ARM_ORDER",
            "occurrence_count": EXPECTED_OCCURRENCE_COUNT,
            "source_transport_used_only_by_source_arm": True,
            "caller_totals_accepted": False,
            "caller_target_fields_accepted": False,
            "frozen_before_observation": True,
            "observer_open_calls_at_freeze": 0,
            "target_accesses_at_freeze": 0,
            "observation_batches_at_freeze": 0,
        }

    @property
    def plan_id(self) -> str:
        return self._plan_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "threshold_profile": self.threshold_profile.to_document(),
            "cap_profile": self.cap_profile.to_document(),
            "entries": [item.to_document() for item in self.entries],
            "plan_id": self.plan_id,
        }


def freeze_v075_production_occurrence_plan_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
) -> V075ProductionOccurrencePlanV1:
    """Freeze the exact fifteen-entry plan without opening the target."""

    namespace_document = _validated_namespace_document_v1(namespace)
    family = public.freeze_v075_public_family_generation_v1()
    threshold_profile = worker.V075WorkerThresholdProfileV1()
    cap_profile = worker.V075WorkerCapProfileV1()
    source_transport, source_bundle, source_verification = (
        _load_tracked_source_authority_graph_v1(repository_root)
    )
    entries = []
    for context_ordinal, context in enumerate(family.replicate_contexts):
        for arm_ordinal, arm in enumerate(REGISTERED_ARM_ORDER):
            scientific_ordinal = (
                context_ordinal * EXPECTED_ARM_COUNT + arm_ordinal
            )
            per_arm_transport = (
                source_transport
                if arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
                else None
            )
            occurrence_identity = (
                batch_native.freeze_v075_batch_native_occurrence_identity_v1(
                    namespace=namespace,
                    context=context,
                    arm=arm,
                    occurrence_ordinal=scientific_ordinal,
                    threshold_profile=threshold_profile,
                    cap_profile=cap_profile,
                    source_prior_transport=per_arm_transport,
                )
            )
            entries.append(
                V075ProductionOccurrencePlanEntryV1(
                    _ENTRY_ISSUER,
                    namespace_document["remote_main_anchor_id"],
                    namespace_document["final_preregistration_id"],
                    namespace.target_tape_namespace_id,
                    family.generation_id,
                    context.context_id,
                    context_ordinal,
                    arm,
                    arm_ordinal,
                    scientific_ordinal,
                    scientific_ordinal + 1,
                    threshold_profile.threshold_profile_id,
                    cap_profile.cap_profile_id,
                    (
                        source_transport.transport_id
                        if per_arm_transport is not None
                        else None
                    ),
                    occurrence_identity,
                )
            )
    return V075ProductionOccurrencePlanV1(
        _PLAN_ISSUER,
        namespace_document["remote_main_anchor_id"],
        namespace_document["final_preregistration_id"],
        namespace.target_tape_namespace_id,
        family.generation_id,
        tuple(item.context_id for item in family.replicate_contexts),
        threshold_profile,
        cap_profile,
        source_transport,
        source_bundle.bundle_id,
        source_verification.verification_id,
        tuple(entries),
    )


@dataclass(frozen=True, slots=True)
class V075ProductionOccurrencePlanVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    plan_id: str
    plan_bytes_sha256: str
    remote_main_anchor_id: str
    final_preregistration_id: str
    target_tape_namespace_id: str
    public_family_generation_id: str
    source_transport_id: str
    tracked_source_bundle_id: str
    tracked_source_verification_id: str
    entry_ids: tuple[str, ...]
    occurrence_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.plan_id, "verified production plan"),
            (self.plan_bytes_sha256, "verified production-plan bytes"),
            (self.remote_main_anchor_id, "verified remote-main anchor"),
            (
                self.final_preregistration_id,
                "verified final preregistration",
            ),
            (
                self.target_tape_namespace_id,
                "verified target namespace",
            ),
            (
                self.public_family_generation_id,
                "verified public family",
            ),
            (self.source_transport_id, "verified source transport"),
            (
                self.tracked_source_bundle_id,
                "verified tracked source bundle",
            ),
            (
                self.tracked_source_verification_id,
                "verified tracked source verification",
            ),
            *((item, "verified plan entry") for item in self.entry_ids),
            *(
                (item, "verified batch-native occurrence")
                for item in self.occurrence_ids
            ),
        ):
            _cid(value, field_name)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or type(self.entry_ids) is not tuple
            or type(self.occurrence_ids) is not tuple
            or len(self.entry_ids) != EXPECTED_OCCURRENCE_COUNT
            or len(self.occurrence_ids) != EXPECTED_OCCURRENCE_COUNT
            or len(set(self.entry_ids)) != EXPECTED_OCCURRENCE_COUNT
            or len(set(self.occurrence_ids)) != EXPECTED_OCCURRENCE_COUNT
        ):
            _fail("production-plan verification is partial or caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_occurrence_plan_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "plan_id": self.plan_id,
            "plan_bytes_sha256": self.plan_bytes_sha256,
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "public_family_generation_id": (
                self.public_family_generation_id
            ),
            "source_transport_id": self.source_transport_id,
            "tracked_source_bundle_id": self.tracked_source_bundle_id,
            "tracked_source_verification_id": (
                self.tracked_source_verification_id
            ),
            "entry_ids": list(self.entry_ids),
            "occurrence_ids": list(self.occurrence_ids),
            "exact_context_major_order_replayed": True,
            "scientific_transport_ordinal_map_replayed": True,
            "batch_native_occurrence_identities_recomputed": True,
            "tracked_source_authorities_replayed": True,
            "caller_totals_accepted": False,
            "target_accessed": False,
            "observer_open_calls": 0,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_production_occurrence_plan_bytes_v1(
    *,
    repository_root: str | Path,
    namespace: public.V075PublicTargetTapeNamespaceV1,
    raw: bytes,
) -> tuple[
    V075ProductionOccurrencePlanV1,
    V075ProductionOccurrencePlanVerificationV1,
]:
    """Recompute and byte-compare the complete target-free plan."""

    if type(raw) is not bytes or not raw or len(raw) > MAX_PLAN_BYTES:
        _fail("claimed production-plan bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionOccurrencePlanInvariantViolation(
            "claimed production plan is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("claimed production plan is not one canonical object")

    expected = freeze_v075_production_occurrence_plan_v1(
        repository_root=repository_root,
        namespace=namespace,
    )
    # ``loads_canonical_json`` restores registered rational documents to
    # ``Fraction`` objects, so object equality with ``to_document`` is not a
    # meaningful byte-authority check.  The canonical byte comparison is
    # exact and includes every nested field.
    if raw != expected.canonical_bytes:
        _fail(
            "claimed production plan is stale, reordered, duplicated, "
            "transplanted, or caller-authored"
        )
    verification = V075ProductionOccurrencePlanVerificationV1(
        _VERIFICATION_ISSUER,
        expected.plan_id,
        hashlib.sha256(raw).hexdigest(),
        expected.remote_main_anchor_id,
        expected.final_preregistration_id,
        expected.target_tape_namespace_id,
        expected.public_family_generation_id,
        expected.source_transport_id,
        expected.tracked_source_bundle_id,
        expected.tracked_source_verification_id,
        tuple(item.entry_id for item in expected.entries),
        tuple(item.occurrence_id for item in expected.entries),
    )
    return expected, verification


__all__ = [
    "DOMAIN_TAGS",
    "EXPECTED_ARM_COUNT",
    "EXPECTED_CONTEXT_COUNT",
    "EXPECTED_OCCURRENCE_COUNT",
    "MAX_PLAN_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_ARM_ORDER",
    "SCHEMA_VERSION",
    "V075ProductionOccurrencePlanEntryV1",
    "V075ProductionOccurrencePlanInvariantViolation",
    "V075ProductionOccurrencePlanV1",
    "V075ProductionOccurrencePlanVerificationV1",
    "freeze_v075_production_occurrence_plan_v1",
    "load_tracked_v075_source_prior_transport_v1",
    "verify_v075_production_occurrence_plan_bytes_v1",
]
