"""Exact-V2 private observer boundary for the V0-075 production campaign.

This is the first target-reading component in the exact V2 authority chain.
It accepts only an issuer-gated ``V075ObserverOpenAuthorizationV2`` and the
original ``V075PublicTargetTapeNamespaceV2`` named by that authorization.  It
does not project either object into a V1 authority or namespace.

The public graph's state/action/support/stream objects remain law-free
semantic primitives.  V2 observation records, journal entries, closures, and
replay attestations use new domains and bind the complete V2 anchor,
authorization, reveal, namespace, commitment, and signer-registry graph.
Private salts and transition laws never cross the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from acfqp.h2_graph_transition_engine_v1 import (
    DeterministicH2GraphStreamV1,
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphSampleV1,
    H2GraphStateV1,
    H2GraphTransitionInvariantViolation,
    verify_deterministic_samples_v1,
)
from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import construction_accounting_owned_runtime_v1 as accounting_runtime
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_public_campaign_authority_v1 as public
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.43.0"
PROFILE_KEY = "v075_private_observer_boundary_v2"

EXACT_V2_AUTHORITY_REQUIRED = True
V1_AUTHORITY_PROJECTION_ALLOWED = False
V1_NAMESPACE_PROJECTION_ALLOWED = False
PRODUCTION_ENVIRONMENT_INCLUDED = False
PRODUCTION_PRIVATE_SIGNER_INCLUDED = False

DOMAIN_TAGS = {
    "open_binding": "acfqp:v075-observer-open-authority-binding:v2",
    "session": "acfqp:v075-private-observer-session-public-identity:v2",
    "observation_signature": (
        "acfqp:v075-signed-canonical-observation-record-signature:v2"
    ),
    "observation_artifact": (
        "acfqp:v075-signed-canonical-observation-record:v2"
    ),
    "journal_entry": "acfqp:v075-append-only-observer-journal-entry:v2",
    "journal_closure_signature": (
        "acfqp:v075-append-only-observer-journal-closure-signature:v2"
    ),
    "journal_closure_artifact": (
        "acfqp:v075-append-only-observer-journal-closure:v2"
    ),
    "capability": "acfqp:v075-public-observation-capability:v2",
    "batch_request": "acfqp:v075-batch-observation-request:v2",
    "batch_open_eligibility": (
        "acfqp:v075-batch-open-eligibility:v2"
    ),
    "batch_outcome": "acfqp:v075-batch-outcome-aggregate:v2",
    "batch_signature": "acfqp:v075-signed-observation-batch-signature:v2",
    "batch_artifact": "acfqp:v075-signed-observation-batch:v2",
    "batch_journal_entry": (
        "acfqp:v075-observer-batch-journal-entry:v2"
    ),
    "batch_journal_closure_signature": (
        "acfqp:v075-observer-batch-journal-closure-signature:v2"
    ),
    "batch_journal_closure_artifact": (
        "acfqp:v075-observer-batch-journal-closure:v2"
    ),
    "batch_closure_verification": (
        "acfqp:v075-observer-batch-journal-closure-verification:v2"
    ),
    "closure_verification": (
        "acfqp:v075-private-observer-journal-closure-verification:v2"
    ),
}

MAX_CANONICAL_CLOSURE_BYTES = 64 * 1024 * 1024
MAX_PER_DRAW_RECORD_BYTES = 256 * 1024
MAX_PER_DRAW_RECORDS_PER_SESSION = 128
MAX_BATCH_ACCEPTED_DRAW_COUNT = 25_000_000
MAX_BATCH_ACCEPTED_DRAW_CAP = 25_000_000
MAX_BATCH_OUTCOME_COUNT = 4_096
MAX_BATCHES_PER_SESSION = 4_096
MAX_OBSERVER_OPEN_BINDING_BYTES = 256 * 1024

BATCH_TRANSCRIPT_INITIAL_DOMAIN = (
    b"acfqp:v075-batch-observation-transcript-initial:v2"
)
BATCH_TRANSCRIPT_LEAF_DOMAIN = (
    b"acfqp:v075-batch-observation-transcript-leaf:v2"
)
BATCH_TRANSCRIPT_STEP_DOMAIN = (
    b"acfqp:v075-batch-observation-transcript-step:v2"
)

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 observer-boundary V2 domains must be unique")


class V075PrivateObserverBoundaryV2InvariantViolation(ValueError):
    """The exact-V2 observer boundary or its public evidence was invalid."""


def _fail(message: str) -> None:
    raise V075PrivateObserverBoundaryV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("observer arithmetic must remain exact")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


@runtime_checkable
class V075ObserverEvidenceSignerProtocolV2(Protocol):
    """In-memory observer signer; private key material is never serialized."""

    def public_verification_key_v1(
        self,
    ) -> public.V075RSAPublicVerificationKeyV1:
        """Return the exact public observer-evidence key."""

    def sign_observer_evidence_v1(self, message: bytes) -> str:
        """Sign one domain-separated V2 observer-evidence message."""


_BINDING_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverOpenAuthorityBindingV2:
    """Verifier-derived exact-V2 binding used by every emitted record."""

    _issuer: object = field(repr=False, compare=False)
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2
    authorization_id: str
    private_reveal_attestation_id: str
    remote_main_anchor_id: str
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _BINDING_ISSUER
            or type(self.namespace)
            is not namespace_v2.V075PublicTargetTapeNamespaceV2
        ):
            _fail("observer-open V2 binding is verifier-issued only")
        for value, label in (
            (self.authorization_id, "V2 observer-open authorization"),
            (
                self.private_reveal_attestation_id,
                "V2 private reveal attestation",
            ),
            (self.remote_main_anchor_id, "V2 remote-main anchor"),
        ):
            _cid(value, label)
        if self.remote_main_anchor_id != self.namespace.anchor.anchor_id:
            _fail("observer-open V2 binding carries a foreign anchor")
        object.__setattr__(
            self,
            "_binding_id",
            _hash("open_binding", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        anchor = self.namespace.anchor
        return {
            "schema": "acfqp.v075_observer_open_authority_binding.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "observer_open_authorization_id": self.authorization_id,
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "anchor_commit_id": anchor.commit_id,
            "anchor_tree_id": anchor.tree_id,
            "manifest_id": anchor.manifest_id,
            "final_preregistration_id": anchor.final_preregistration_id,
            "component_registry_id": anchor.component_registry_id,
            "semantic_registry_binding_id": (
                anchor.semantic_registry_binding_id
            ),
            "semantic_artifact_replay_id": (
                anchor.semantic_artifact_replay_id
            ),
            "workload_id": self.namespace.workload.workload_id,
            "runner_profile_id": self.namespace.runner_profile.profile_id,
            "family_generation_id": self.namespace.family.generation_id,
            "target_tape_namespace_id": (
                self.namespace.target_tape_namespace_id
            ),
            "opaque_environment_commitment_id": (
                self.namespace.environment_commitment.commitment_id
            ),
            "signer_registry_id": self.namespace.signer_registry.registry_id,
            "observer_evidence_key_id": (
                self.namespace.signer_registry.observer_evidence_key.key_id
            ),
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_authority_projection_issued": False,
            "legacy_v1_namespace_projection_issued": False,
            "independent_final_authority_verified": True,
            "observer_open_authorized": True,
            "private_material_serialized": False,
        }

    @property
    def binding_id(self) -> str:
        return self._binding_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def _require_exact_v2_binding(
    *,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
) -> V075ObserverOpenAuthorityBindingV2:
    if (
        type(authority) is not preopen.V075ObserverOpenAuthorizationV2
        or type(namespace)
        is not namespace_v2.V075PublicTargetTapeNamespaceV2
    ):
        _fail(
            "observer V2 requires exact V2 authorization and namespace types"
        )
    anchor = authority.anchor
    reveal = authority.private_reveal_attestation
    if (
        authority.tracked_blobs.anchor != anchor
        or authority.signer_registry != namespace.signer_registry
        or authority.opaque_environment_commitment
        != namespace.environment_commitment
        or reveal.anchor != anchor
        or namespace.anchor != anchor
        or anchor.signer_registry != namespace.signer_registry
        or anchor.family_generation_id != namespace.family.generation_id
        or anchor.workload_id != namespace.workload.workload_id
        or anchor.runner_profile_id != namespace.runner_profile.profile_id
        or anchor.opaque_environment_commitment_id
        != namespace.environment_commitment.commitment_id
        or authority.to_document()["legacy_v1_projection_issued"] is not False
        or authority.to_document()["authorization_ready"] is not True
    ):
        _fail("observer V2 authority/namespace graph was transplanted")
    return V075ObserverOpenAuthorityBindingV2(
        _BINDING_ISSUER,
        namespace,
        authority.authorization_id,
        reveal.attestation_id,
        anchor.anchor_id,
    )


def _replay_exact_v2_authority_namespace(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
) -> tuple[
    preopen.V075ObserverOpenAuthorizationV2,
    namespace_v2.V075PublicTargetTapeNamespaceV2,
    V075ObserverOpenAuthorityBindingV2,
]:
    """Rebuild the complete production gate from tracked canonical bytes."""

    try:
        authority = preopen.verify_v075_observer_open_authorization_v2(
            repository_root=repository_root,
            private_reveal_attestation_bytes=(
                private_reveal_attestation_bytes
            ),
            claimed_authorization_bytes=claimed_authorization_bytes,
        )
        namespace, _verification = (
            namespace_v2.verify_v075_public_target_tape_namespace_bytes_v2(
                repository_root=repository_root,
                anchor=authority.anchor,
                environment_commitment=(
                    authority.opaque_environment_commitment
                ),
                raw=namespace_bytes,
            )
        )
    except (
        preopen.V075PreopenAuthorizationV2InvariantViolation,
        preopen.V075PreopenAuthorizationV2NotReady,
        namespace_v2.V075PublicTargetTapeNamespaceV2InvariantViolation,
        namespace_v2.V075PublicTargetTapeNamespaceV2NotReady,
        OSError,
    ) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "exact V2 production authority replay failed"
        ) from error
    binding = _require_exact_v2_binding(
        authority=authority,
        namespace=namespace,
    )
    return authority, namespace, binding


def replay_v075_observer_open_authority_binding_bytes_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    observer_open_binding_bytes: bytes,
) -> V075ObserverOpenAuthorityBindingV2:
    """Replay one public observer-open binding without opening an observer.

    The authorization, reveal attestation, namespace, anchor, commitment, and
    public signer registry are reconstructed from their canonical bytes before
    the issuer-gated binding is minted.  No private salt, environment, target
    law, signer, session, or observer channel is accepted by this API.
    """

    if (
        type(observer_open_binding_bytes) is not bytes
        or not observer_open_binding_bytes
        or len(observer_open_binding_bytes)
        > MAX_OBSERVER_OPEN_BINDING_BYTES
    ):
        _fail(
            "observer-open binding bytes are empty, mistyped, or exceed "
            "their cap"
        )
    _authority, _namespace, binding = _replay_exact_v2_authority_namespace(
        repository_root=repository_root,
        private_reveal_attestation_bytes=private_reveal_attestation_bytes,
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
    )
    try:
        claimed = loads_canonical_json(observer_open_binding_bytes)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "observer-open binding is not strict canonical JSON"
        ) from error
    if (
        type(claimed) is not dict
        or canonical_json_bytes(claimed) != observer_open_binding_bytes
        or observer_open_binding_bytes
        != canonical_json_bytes(binding.to_document())
    ):
        _fail(
            "observer-open binding fields, content ID, namespace, "
            "authorization, reveal, anchor, commitment, or public key "
            "differ from exact replay"
        )
    return binding


def _canonical_private_environment(
    *,
    family: public.V075PublicFamilyGenerationV1,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    try:
        result = tuple(tuple(row) for row in private_environment)
    except TypeError as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "private environment must be one concrete exact sequence"
        ) from error
    if len(result) != len(family.replicate_contexts):
        _fail("private environment does not cover the frozen V2 family")
    try:
        for context, row in zip(
            family.replicate_contexts,
            result,
            strict=True,
        ):
            H2GraphKernelV1(
                context.topology,
                context.rank_cap,
                context.horizon,
                row,
            )
    except H2GraphTransitionInvariantViolation as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            str(error)
        ) from error
    return result


def _verify_private_reveal(
    *,
    binding: V075ObserverOpenAuthorityBindingV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    private_salt: bytes,
    private_environment: tuple[
        tuple[tuple[int, Fraction], ...],
        ...,
    ],
) -> None:
    try:
        verification = public.verify_opaque_environment_reveal_v1(
            commitment=binding.namespace.environment_commitment,
            secret_salt=private_salt,
            secret_laws=private_environment,
        )
    except public.V075PublicCampaignAuthorityInvariantViolation as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            str(error)
        ) from error
    if (
        not verification.matched
        or verification.verification_id
        != authority.private_reveal_attestation.private_verification_external_id
    ):
        _fail(
            "private environment does not match the exact V2 reveal "
            "attestation"
        )


def _sign(
    *,
    signer: V075ObserverEvidenceSignerProtocolV2,
    expected_key: public.V075RSAPublicVerificationKeyV1,
    message: bytes,
) -> str:
    if not isinstance(signer, V075ObserverEvidenceSignerProtocolV2):
        _fail("observer signer does not implement the strict V2 protocol")
    key = signer.public_verification_key_v1()
    if (
        type(key) is not public.V075RSAPublicVerificationKeyV1
        or key != expected_key
        or key.key_role != "OBSERVER_EVIDENCE"
    ):
        _fail("private signer does not match the V2 namespace registry")
    signature = signer.sign_observer_evidence_v1(message)
    if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
        public_key=expected_key,
        message=message,
        signature_hex=signature,
    ):
        _fail("private signer emitted an invalid V2 observer signature")
    return signature


def _replay_v2_stream_identity(
    value: graph.V075TransitionStreamIdentityV1,
) -> graph.V075TransitionStreamIdentityV1:
    """Reconstruct one law-free stream graph without trusting its objects."""

    if type(value) is not graph.V075TransitionStreamIdentityV1:
        _fail("observer V2 stream has a foreign concrete type")
    try:
        namespace = graph.validate_v075_public_graph_namespace_v2(
            value.namespace
        )
        original_row = value.row_binding
        context = original_row.context
        if (
            type(context)
            is not public.V075PublicReplicateContextV1
            or type(context.replicate_ordinal) is not int
            or context.replicate_ordinal < 0
            or context.replicate_ordinal
            >= len(namespace.family.replicate_contexts)
            or namespace.family.replicate_contexts[
                context.replicate_ordinal
            ]
            != context
        ):
            _fail("observer V2 stream context is not registered")
        original_catalogue = original_row.catalogue
        replayed_state = graph.V075SymbolicGraphStateV1(
            context,
            original_catalogue.state.ranks,
            original_catalogue.state.failure,
        )
        replayed_catalogue = graph.V075LegalActionCatalogueV1(
            context,
            replayed_state,
            original_catalogue.remaining_horizon,
            original_catalogue.actions,
        )
        replayed_row = graph.observation_row_binding_v1(
            context,
            replayed_catalogue,
            original_row.action,
        )
        replayed_epochs: list[graph.V075SharedSupportEpochV1] = []
        for original_epoch in value.pairing_authority.support_chain.epochs:
            replayed_evidence: list[
                graph.V075SupportEvidenceV1
                | graph.V075BatchAggregateSupportEvidenceV1
            ] = []
            for item in original_epoch.evidence:
                replayed_observed_state = graph.V075SymbolicGraphStateV1(
                    context,
                    item.observed_state.ranks,
                    item.observed_state.failure,
                )
                if type(item) is graph.V075SupportEvidenceV1:
                    replayed_item = graph.V075SupportEvidenceV1(
                        namespace,
                        replayed_row,
                        replayed_observed_state,
                        item.source_observer_epoch_index,
                        item.accepted_draw_index,
                        item.observer_signature_hex,
                    )
                elif (
                    type(item)
                    is graph.V075BatchAggregateSupportEvidenceV1
                ):
                    replayed_item = (
                        graph.V075BatchAggregateSupportEvidenceV1(
                            namespace,
                            replayed_row,
                            replayed_observed_state,
                            item.source_observer_epoch_index,
                            item.discovery_request_id,
                            item.discovery_batch_id,
                            item.discovery_outcome_id,
                            item.discovery_outcome_count,
                            item.observer_signature_hex,
                        )
                    )
                else:
                    _fail("observer V2 stream support evidence is untyped")
                if (
                    replayed_item != item
                    or replayed_item.to_document() != item.to_document()
                ):
                    _fail("observer V2 stream support evidence was forged")
                replayed_evidence.append(replayed_item)
            replayed_epoch = graph.derive_shared_support_epoch_v1(
                namespace=namespace,
                row_binding=replayed_row,
                epoch_index=original_epoch.epoch_index,
                evidence=tuple(replayed_evidence),
                parent=(
                    None if not replayed_epochs else replayed_epochs[-1]
                ),
            )
            if (
                replayed_epoch != original_epoch
                or replayed_epoch.to_document()
                != original_epoch.to_document()
            ):
                _fail("observer V2 support epoch was forged")
            replayed_epochs.append(replayed_epoch)
        replayed_chain = graph.freeze_shared_support_chain_v1(
            namespace=namespace,
            row_binding=replayed_row,
            epochs=tuple(replayed_epochs),
        )
        replayed_pairing = graph.freeze_five_arm_pairing_authority_v1(
            namespace=namespace,
            row_binding=replayed_row,
            support_chain=replayed_chain,
        )
        replayed = graph.derive_transition_stream_identity_v1(
            pairing_authority=replayed_pairing,
            arm=value.arm,
        )
        if (
            replayed != value
            or replayed.to_document() != value.to_document()
        ):
            _fail("observer V2 stream differs from semantic reconstruction")
        return replayed
    except (
        AttributeError,
        IndexError,
        TypeError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "observer V2 stream semantic reconstruction failed"
        ) from error


def _validate_v2_stream_shallow(
    *,
    binding: V075ObserverOpenAuthorityBindingV2,
    stream_identity: graph.V075TransitionStreamIdentityV1,
) -> graph.V075TransitionStreamIdentityV1:
    if (
        type(stream_identity)
        is not graph.V075TransitionStreamIdentityV1
        or type(stream_identity.namespace)
        is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or stream_identity.namespace != binding.namespace
        or stream_identity.row_binding.context
        not in binding.namespace.family.replicate_contexts
    ):
        _fail(
            "observer V2 stream must directly hold the exact bound V2 "
            "namespace"
        )
    return stream_identity


def _validate_v2_stream(
    *,
    binding: V075ObserverOpenAuthorityBindingV2,
    stream_identity: graph.V075TransitionStreamIdentityV1,
) -> graph.V075TransitionStreamIdentityV1:
    replayed = _replay_v2_stream_identity(stream_identity)
    return _validate_v2_stream_shallow(
        binding=binding,
        stream_identity=replayed,
    )


def _observation_payload(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    stream_identity: graph.V075TransitionStreamIdentityV1,
    sample: H2GraphSampleV1,
) -> dict[str, Any]:
    _validate_v2_stream_shallow(
        binding=authority_binding,
        stream_identity=stream_identity,
    )
    return {
        "schema": "acfqp.v075_signed_canonical_observation_record.v2",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "observer_session_public_id": _cid(
            session_public_id,
            "observer V2 session",
        ),
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": (
            authority_binding.authorization_id
        ),
        "private_reveal_attestation_id": (
            authority_binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": authority_binding.remote_main_anchor_id,
        "target_tape_namespace_id": (
            stream_identity.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            authority_binding.namespace.environment_commitment.commitment_id
        ),
        "signer_registry_id": (
            authority_binding.namespace.signer_registry.registry_id
        ),
        "observer_signer_key_id": (
            authority_binding.namespace.signer_registry.observer_evidence_key
            .key_id
        ),
        "context_id": stream_identity.context_id,
        "row_binding_id": stream_identity.row_binding_id,
        "catalogue_id": stream_identity.catalogue_id,
        "source_state_id": (
            stream_identity.row_binding.catalogue.state.state_id
        ),
        "remaining_horizon": (
            stream_identity.row_binding.remaining_horizon
        ),
        "action": list(stream_identity.action),
        "pairing_group_id": stream_identity.pairing_group_id,
        "pairing_lineage_id": stream_identity.pairing_lineage_id,
        "support_epoch_id": stream_identity.support_epoch_id,
        "observer_epoch_index": stream_identity.observer_epoch_index,
        "lane": stream_identity.lane.value,
        "arm": stream_identity.arm,
        "stream_id": stream_identity.stream_id,
        "accepted_draw_index": sample.accepted_draw_index,
        "random_word_start_index": sample.random_word_start_index,
        "random_words": list(sample.random_words),
        "next_ranks": list(sample.next_state.ranks),
        "failure": sample.failure,
        "terminal": sample.terminal,
        "spawn_cell": sample.spawn_cell,
        "spawn_rank": sample.spawn_rank,
        "realized_row_reward": _fraction_document(
            sample.realized_row_reward
        ),
        "authority_version": "V2",
        "namespace_version": "V2",
        "legacy_v1_projection_issued": False,
        "arm_absent_from_raw_pairing_key": True,
        "private_material_serialized": False,
    }


def observation_record_signing_bytes_v2(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    stream_identity: graph.V075TransitionStreamIdentityV1,
    sample: H2GraphSampleV1,
) -> bytes:
    if (
        type(authority_binding) is not V075ObserverOpenAuthorityBindingV2
        or type(sample) is not H2GraphSampleV1
    ):
        _fail("observation V2 signing graph is untyped")
    return (
        DOMAIN_TAGS["observation_signature"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(
            _observation_payload(
                session_public_id=session_public_id,
                authority_binding=authority_binding,
                stream_identity=stream_identity,
                sample=sample,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class V075SignedObservationRecordV2:
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV2
    stream_identity: graph.V075TransitionStreamIdentityV1
    sample: H2GraphSampleV1
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV2
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or type(self.sample) is not H2GraphSampleV1
        ):
            _fail("signed observation V2 graph is untyped")
        _validate_v2_stream_shallow(
            binding=self.authority_binding,
            stream_identity=self.stream_identity,
        )
        _cid(self.session_public_id, "observer V2 session")
        message = observation_record_signing_bytes_v2(
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            stream_identity=self.stream_identity,
            sample=self.sample,
        )
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
            signature_hex=self.observer_signature_hex,
        ):
            _fail("observation V2 signature is invalid or transplanted")
        try:
            graph.V075SymbolicGraphStateV1(
                self.stream_identity.row_binding.context,
                self.sample.next_state.ranks,
                self.sample.next_state.failure,
            )
        except graph.V075PublicGraphSemanticsInvariantViolation as error:
            raise V075PrivateObserverBoundaryV2InvariantViolation(
                str(error)
            ) from error

    @property
    def record_id(self) -> str:
        return _hash(
            "observation_artifact",
            {
                **_observation_payload(
                    session_public_id=self.session_public_id,
                    authority_binding=self.authority_binding,
                    stream_identity=self.stream_identity,
                    sample=self.sample,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_observation_payload(
                session_public_id=self.session_public_id,
                authority_binding=self.authority_binding,
                stream_identity=self.stream_identity,
                sample=self.sample,
            ),
            "observer_open_binding": self.authority_binding.to_document(),
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "record_id": self.record_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class V075ObservationCapabilityV2:
    """Law-free V2 record capability safe for a planner or worker."""

    record: V075SignedObservationRecordV2

    def __post_init__(self) -> None:
        if type(self.record) is not V075SignedObservationRecordV2:
            _fail("observation capability V2 requires one exact record")
        try:
            replayed = V075SignedObservationRecordV2(
                self.record.session_public_id,
                self.record.authority_binding,
                self.record.stream_identity,
                self.record.sample,
                self.record.observer_signature_hex,
            )
            if (
                replayed.record_id != self.record.record_id
                or replayed.canonical_bytes != self.record.canonical_bytes
            ):
                _fail("observation capability V2 record differs from replay")
        except (
            AttributeError,
            TypeError,
            ValueError,
        ) as error:
            if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
                raise
            raise V075PrivateObserverBoundaryV2InvariantViolation(
                "observation capability V2 rejected a forged record"
            ) from error

    def _payload(self) -> dict[str, Any]:
        record = self.record
        stream = record.stream_identity
        sample = record.sample
        return {
            "schema": "acfqp.v075_public_observation_capability.v2",
            "schema_version": SCHEMA_VERSION,
            "observation_record_id": record.record_id,
            "observer_open_binding_id": (
                record.authority_binding.binding_id
            ),
            "remote_main_anchor_id": (
                record.authority_binding.remote_main_anchor_id
            ),
            "target_tape_namespace_id": (
                stream.target_tape_namespace_id
            ),
            "environment_commitment_id": (
                record.authority_binding.namespace.environment_commitment
                .commitment_id
            ),
            "context_id": stream.context_id,
            "row_binding_id": stream.row_binding_id,
            "source_state_id": stream.row_binding.catalogue.state.state_id,
            "remaining_horizon": stream.row_binding.remaining_horizon,
            "action": list(stream.action),
            "stream_id": stream.stream_id,
            "pairing_group_id": stream.pairing_group_id,
            "observer_epoch_index": stream.observer_epoch_index,
            "lane": stream.lane.value,
            "arm": stream.arm,
            "accepted_draw_index": sample.accepted_draw_index,
            "next_ranks": list(sample.next_state.ranks),
            "failure": sample.failure,
            "terminal": sample.terminal,
            "spawn_cell": sample.spawn_cell,
            "spawn_rank": sample.spawn_rank,
            "realized_row_reward": _fraction_document(
                sample.realized_row_reward
            ),
            "observer_signature_hex": record.observer_signature_hex,
            "authority_version": "V2",
            "namespace_version": "V2",
            "private_material_serialized": False,
        }

    @property
    def capability_id(self) -> str:
        return _hash("capability", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "record": self.record.to_document(),
            "capability_id": self.capability_id,
        }


_BATCH_REQUEST_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchObservationRequestV2:
    """One contiguous, occurrence-bound interval on an exact V2 stream."""

    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV2
    stream_identity: graph.V075TransitionStreamIdentityV1
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "batch V2 occurrence")
        _cid(self.session_public_id, "batch V2 observer session")
        end = self.accepted_draw_start + self.accepted_draw_count - 1
        if (
            self._issuer is not _BATCH_REQUEST_ISSUER
            or type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV2
            or type(self.stream_identity)
            is not graph.V075TransitionStreamIdentityV1
            or type(self.accepted_draw_start) is not int
            or self.accepted_draw_start <= 0
            or type(self.accepted_draw_count) is not int
            or not 0
            < self.accepted_draw_count
            <= MAX_BATCH_ACCEPTED_DRAW_COUNT
            or type(self.accepted_draw_cap) is not int
            or not 0 < self.accepted_draw_cap
            <= MAX_BATCH_ACCEPTED_DRAW_CAP
            or end > self.accepted_draw_cap
        ):
            _fail("batch V2 request is untyped, empty, or over cap")
        _validate_v2_stream_shallow(
            binding=self.authority_binding,
            stream_identity=self.stream_identity,
        )
        object.__setattr__(
            self,
            "_request_id",
            _hash("batch_request", self._payload()),
        )

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    @property
    def request_id(self) -> str:
        return self._request_id

    def _payload(self) -> dict[str, Any]:
        binding = self.authority_binding
        stream = self.stream_identity
        return {
            "schema": "acfqp.v075_batch_observation_request.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "observer_session_public_id": self.session_public_id,
            "observer_open_binding_id": binding.binding_id,
            "observer_open_authorization_id": binding.authorization_id,
            "private_reveal_attestation_id": (
                binding.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": binding.remote_main_anchor_id,
            "target_tape_namespace_id": stream.target_tape_namespace_id,
            "environment_commitment_id": (
                binding.namespace.environment_commitment.commitment_id
            ),
            "signer_registry_id": (
                binding.namespace.signer_registry.registry_id
            ),
            "context_id": stream.context_id,
            "row_binding_id": stream.row_binding_id,
            "catalogue_id": stream.catalogue_id,
            "stream_id": stream.stream_id,
            "pairing_group_id": stream.pairing_group_id,
            "support_epoch_id": stream.support_epoch_id,
            "observer_epoch_index": stream.observer_epoch_index,
            "lane": stream.lane.value,
            "arm": stream.arm,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "authority_version": "V2",
            "namespace_version": "V2",
            "per_draw_record_generation_allowed": False,
            "request_nonce_allowed": False,
            "reroll_allowed": False,
            "private_material_serialized": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class V075BatchOutcomeAggregateV2:
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    spawn_cell: int
    spawn_rank: int
    realized_row_reward: Fraction
    count: int
    reward_sum: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(rank) is not int or rank < 0 for rank in self.next_ranks)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or type(self.spawn_cell) is not int
            or self.spawn_cell < 0
            or type(self.spawn_rank) is not int
            or self.spawn_rank <= 0
            or type(self.realized_row_reward) is not Fraction
            or self.realized_row_reward < 0
            or type(self.count) is not int
            or self.count <= 0
            or type(self.reward_sum) is not Fraction
            or self.reward_sum != self.realized_row_reward * self.count
        ):
            _fail("batch V2 outcome aggregate is malformed")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_outcome_aggregate.v2",
            "schema_version": SCHEMA_VERSION,
            "next_ranks": list(self.next_ranks),
            "failure": self.failure,
            "terminal": self.terminal,
            "spawn_cell": self.spawn_cell,
            "spawn_rank": self.spawn_rank,
            "realized_row_reward": _fraction_document(
                self.realized_row_reward
            ),
        }

    @property
    def outcome_id(self) -> str:
        return _hash("batch_outcome", self._identity_payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "outcome_id": self.outcome_id,
            "count": self.count,
            "reward_sum": _fraction_document(self.reward_sum),
        }


@dataclass(frozen=True, slots=True)
class _V075BatchFactsV2:
    outcomes: tuple[V075BatchOutcomeAggregateV2, ...]
    reward_sum: Fraction
    failure_count: int
    terminal_count: int
    random_word_count: int
    rejection_count: int
    first_random_word_index: int
    next_random_word_index: int
    transcript_commitment: str

    def __post_init__(self) -> None:
        _cid(self.transcript_commitment, "batch V2 transcript")
        accepted = sum(item.count for item in self.outcomes)
        if (
            type(self.outcomes) is not tuple
            or not self.outcomes
            or len(self.outcomes) > MAX_BATCH_OUTCOME_COUNT
            or any(
                type(item) is not V075BatchOutcomeAggregateV2
                for item in self.outcomes
            )
            or tuple(item.outcome_id for item in self.outcomes)
            != tuple(sorted(item.outcome_id for item in self.outcomes))
            or len({item.outcome_id for item in self.outcomes})
            != len(self.outcomes)
            or type(self.reward_sum) is not Fraction
            or self.reward_sum
            != sum(
                (item.reward_sum for item in self.outcomes),
                Fraction(0),
            )
            or type(self.failure_count) is not int
            or self.failure_count
            != sum(item.count for item in self.outcomes if item.failure)
            or type(self.terminal_count) is not int
            or self.terminal_count
            != sum(item.count for item in self.outcomes if item.terminal)
            or type(self.random_word_count) is not int
            or self.random_word_count < accepted
            or type(self.rejection_count) is not int
            or self.rejection_count != self.random_word_count - accepted
            or type(self.first_random_word_index) is not int
            or self.first_random_word_index <= 0
            or type(self.next_random_word_index) is not int
            or self.next_random_word_index
            != self.first_random_word_index + self.random_word_count
        ):
            _fail("batch V2 aggregate facts do not reconcile")


def _batch_sample_leaf_payload(sample: H2GraphSampleV1) -> dict[str, Any]:
    if type(sample) is not H2GraphSampleV1:
        _fail("batch V2 transcript leaf requires one exact sample")
    return {
        "schema": "acfqp.v075_batch_observation_transcript_leaf.v2",
        "schema_version": SCHEMA_VERSION,
        "accepted_draw_index": sample.accepted_draw_index,
        "random_word_start_index": sample.random_word_start_index,
        "random_words": list(sample.random_words),
        "next_ranks": list(sample.next_state.ranks),
        "failure": sample.failure,
        "terminal": sample.terminal,
        "spawn_cell": sample.spawn_cell,
        "spawn_rank": sample.spawn_rank,
        "realized_row_reward": _fraction_document(
            sample.realized_row_reward
        ),
    }


class _StreamingBatchAccumulatorV2:
    """O(outcomes) aggregate; individual samples are never retained."""

    __slots__ = (
        "_accepted_count",
        "_failure_count",
        "_first_random_word_index",
        "_outcomes",
        "_random_word_count",
        "_request",
        "_reward_sum",
        "_terminal_count",
        "_transcript_state",
    )

    def __init__(self, request: V075BatchObservationRequestV2) -> None:
        if type(request) is not V075BatchObservationRequestV2:
            _fail("batch V2 accumulator requires one exact request")
        self._request = request
        self._accepted_count = 0
        self._failure_count = 0
        self._terminal_count = 0
        self._random_word_count = 0
        self._reward_sum = Fraction(0)
        self._first_random_word_index: int | None = None
        self._outcomes: dict[
            tuple[Any, ...],
            tuple[int, Fraction],
        ] = {}
        self._transcript_state = hashlib.sha256(
            BATCH_TRANSCRIPT_INITIAL_DOMAIN
            + b"\x00"
            + request.request_id.encode("ascii")
        ).digest()

    def append(self, sample: H2GraphSampleV1) -> None:
        expected_index = (
            self._request.accepted_draw_start + self._accepted_count
        )
        if (
            type(sample) is not H2GraphSampleV1
            or sample.accepted_draw_index != expected_index
            or (
                self._first_random_word_index is not None
                and sample.random_word_start_index
                != self._first_random_word_index + self._random_word_count
            )
        ):
            _fail("batch V2 sample interval is gapped or reordered")
        if self._first_random_word_index is None:
            self._first_random_word_index = sample.random_word_start_index
        key = (
            sample.next_state.ranks,
            sample.failure,
            sample.terminal,
            sample.spawn_cell,
            sample.spawn_rank,
            sample.realized_row_reward,
        )
        prior_count, prior_reward = self._outcomes.get(
            key,
            (0, Fraction(0)),
        )
        self._outcomes[key] = (
            prior_count + 1,
            prior_reward + sample.realized_row_reward,
        )
        if len(self._outcomes) > MAX_BATCH_OUTCOME_COUNT:
            _fail("batch V2 outcome support exceeded its hard cap")
        self._accepted_count += 1
        self._failure_count += int(sample.failure)
        self._terminal_count += int(sample.terminal)
        self._random_word_count += len(sample.random_words)
        self._reward_sum += sample.realized_row_reward
        leaf = hashlib.sha256(
            BATCH_TRANSCRIPT_LEAF_DOMAIN
            + b"\x00"
            + canonical_json_bytes(_batch_sample_leaf_payload(sample))
        ).digest()
        self._transcript_state = hashlib.sha256(
            BATCH_TRANSCRIPT_STEP_DOMAIN
            + b"\x00"
            + self._transcript_state
            + b"\x00"
            + leaf
        ).digest()
        accounting_runtime.emit_owned_operation_v1(
            "private-observer.accumulator.append"
        )

    def finish(self) -> _V075BatchFactsV2:
        if (
            self._accepted_count != self._request.accepted_draw_count
            or self._first_random_word_index is None
        ):
            _fail("batch V2 accumulator did not consume its exact interval")
        materialized_outcomes: list[V075BatchOutcomeAggregateV2] = []
        for key, (count, reward) in self._outcomes.items():
            outcome = V075BatchOutcomeAggregateV2(
                key[0],
                key[1],
                key[2],
                key[3],
                key[4],
                key[5],
                count,
                reward,
            )
            materialized_outcomes.append(outcome)
            accounting_runtime.emit_owned_operation_v1(
                "private-observer.outcome-aggregate.materialize"
            )
        outcomes = tuple(
            sorted(materialized_outcomes, key=lambda item: item.outcome_id)
        )
        return _V075BatchFactsV2(
            outcomes,
            self._reward_sum,
            self._failure_count,
            self._terminal_count,
            self._random_word_count,
            self._random_word_count - self._accepted_count,
            self._first_random_word_index,
            self._first_random_word_index + self._random_word_count,
            self._transcript_state.hex(),
        )


def _batch_payload(
    *,
    request: V075BatchObservationRequestV2,
    facts: _V075BatchFactsV2,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_signed_observation_batch.v2",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "request_id": request.request_id,
        "occurrence_id": request.occurrence_id,
        "observer_session_public_id": request.session_public_id,
        "observer_open_binding_id": request.authority_binding.binding_id,
        "observer_open_authorization_id": (
            request.authority_binding.authorization_id
        ),
        "private_reveal_attestation_id": (
            request.authority_binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": (
            request.authority_binding.remote_main_anchor_id
        ),
        "target_tape_namespace_id": (
            request.stream_identity.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            request.authority_binding.namespace.environment_commitment
            .commitment_id
        ),
        "context_id": request.stream_identity.context_id,
        "row_binding_id": request.stream_identity.row_binding_id,
        "stream_id": request.stream_identity.stream_id,
        "arm": request.stream_identity.arm,
        "observer_epoch_index": (
            request.stream_identity.observer_epoch_index
        ),
        "accepted_draw_start": request.accepted_draw_start,
        "accepted_draw_count": request.accepted_draw_count,
        "accepted_draw_end": request.accepted_draw_end,
        "accepted_draw_cap": request.accepted_draw_cap,
        "outcome_aggregate_ids": [
            item.outcome_id for item in facts.outcomes
        ],
        "outcome_aggregate_commitments": [
            {
                "outcome_id": item.outcome_id,
                "count": item.count,
                "reward_sum": _fraction_document(item.reward_sum),
            }
            for item in facts.outcomes
        ],
        "reward_sum": _fraction_document(facts.reward_sum),
        "failure_count": facts.failure_count,
        "terminal_count": facts.terminal_count,
        "random_word_count": facts.random_word_count,
        "rejection_count": facts.rejection_count,
        "first_random_word_index": facts.first_random_word_index,
        "next_random_word_index": facts.next_random_word_index,
        "transcript_commitment": facts.transcript_commitment,
        "transcript_scheme": (
            "SHA256_DOMAIN_SEPARATED_ORDERED_SAMPLE_HASH_CHAIN_V2"
        ),
        "rsa_signatures_per_batch": 1,
        "per_draw_records_created": False,
        "per_draw_records_serialized": False,
        "individual_random_words_retained": False,
        "individual_random_words_serialized": False,
        "private_law_serialized": False,
        "private_salt_serialized": False,
        "private_kernel_serialized": False,
    }


def batch_observation_signing_bytes_v2(
    *,
    request: V075BatchObservationRequestV2,
    facts: _V075BatchFactsV2,
) -> bytes:
    if (
        type(request) is not V075BatchObservationRequestV2
        or type(facts) is not _V075BatchFactsV2
    ):
        _fail("batch V2 signing graph is untyped")
    return (
        DOMAIN_TAGS["batch_signature"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(_batch_payload(request=request, facts=facts))
    )


@dataclass(frozen=True, slots=True)
class V075SignedObservationBatchV2:
    request: V075BatchObservationRequestV2
    outcomes: tuple[V075BatchOutcomeAggregateV2, ...]
    reward_sum: Fraction
    failure_count: int
    terminal_count: int
    random_word_count: int
    rejection_count: int
    first_random_word_index: int
    next_random_word_index: int
    transcript_commitment: str
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.request) is not V075BatchObservationRequestV2
            or self.request._issuer is not _BATCH_REQUEST_ISSUER
        ):
            _fail("signed batch V2 requires one exact request")
        facts = self.facts
        if sum(item.count for item in facts.outcomes) != (
            self.request.accepted_draw_count
        ):
            _fail("signed batch V2 omits or duplicates accepted draws")
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.request.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=batch_observation_signing_bytes_v2(
                request=self.request,
                facts=facts,
            ),
            signature_hex=self.observer_signature_hex,
        ):
            _fail("signed batch V2 signature is invalid or transplanted")

    @property
    def facts(self) -> _V075BatchFactsV2:
        return _V075BatchFactsV2(
            self.outcomes,
            self.reward_sum,
            self.failure_count,
            self.terminal_count,
            self.random_word_count,
            self.rejection_count,
            self.first_random_word_index,
            self.next_random_word_index,
            self.transcript_commitment,
        )

    @property
    def batch_id(self) -> str:
        return _hash(
            "batch_artifact",
            {
                **_batch_payload(
                    request=self.request,
                    facts=self.facts,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_batch_payload(request=self.request, facts=self.facts),
            "request": self.request.to_document(),
            "outcomes": [item.to_document() for item in self.outcomes],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "batch_id": self.batch_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def replay_signed_observation_batch_object_v2(
    claimed: V075SignedObservationBatchV2,
) -> V075SignedObservationBatchV2:
    """Reconstruct one signed batch without trusting its nested object graph."""

    if type(claimed) is not V075SignedObservationBatchV2:
        _fail("signed batch V2 object replay requires one exact batch")
    try:
        claimed_request = claimed.request
        if (
            type(claimed_request) is not V075BatchObservationRequestV2
            or claimed_request._issuer is not _BATCH_REQUEST_ISSUER
        ):
            _fail("signed batch V2 request is caller-minted")
        claimed_binding = claimed_request.authority_binding
        if (
            type(claimed_binding)
            is not V075ObserverOpenAuthorityBindingV2
            or claimed_binding._issuer is not _BINDING_ISSUER
        ):
            _fail("signed batch V2 binding is caller-minted")
        replayed_stream = _replay_v2_stream_identity(
            claimed_request.stream_identity
        )
        replayed_binding = V075ObserverOpenAuthorityBindingV2(
            _BINDING_ISSUER,
            replayed_stream.namespace,
            claimed_binding.authorization_id,
            claimed_binding.private_reveal_attestation_id,
            claimed_binding.remote_main_anchor_id,
        )
        if (
            replayed_binding.to_document()
            != claimed_binding.to_document()
            or replayed_binding.namespace != claimed_binding.namespace
        ):
            _fail("signed batch V2 binding differs from semantic replay")
        replayed_request = V075BatchObservationRequestV2(
            _BATCH_REQUEST_ISSUER,
            claimed_request.occurrence_id,
            claimed_request.session_public_id,
            replayed_binding,
            replayed_stream,
            claimed_request.accepted_draw_start,
            claimed_request.accepted_draw_count,
            claimed_request.accepted_draw_cap,
        )
        if (
            replayed_request.to_document()
            != claimed_request.to_document()
        ):
            _fail("signed batch V2 request differs from semantic replay")
        if (
            type(claimed.outcomes) is not tuple
            or any(
                type(item) is not V075BatchOutcomeAggregateV2
                for item in claimed.outcomes
            )
        ):
            _fail("signed batch V2 outcomes are noncanonical")
        replayed_outcomes = tuple(
            V075BatchOutcomeAggregateV2(
                item.next_ranks,
                item.failure,
                item.terminal,
                item.spawn_cell,
                item.spawn_rank,
                item.realized_row_reward,
                item.count,
                item.reward_sum,
            )
            for item in claimed.outcomes
        )
        if (
            tuple(item.to_document() for item in replayed_outcomes)
            != tuple(item.to_document() for item in claimed.outcomes)
        ):
            _fail("signed batch V2 outcomes differ from semantic replay")
        replayed = V075SignedObservationBatchV2(
            replayed_request,
            replayed_outcomes,
            claimed.reward_sum,
            claimed.failure_count,
            claimed.terminal_count,
            claimed.random_word_count,
            claimed.rejection_count,
            claimed.first_random_word_index,
            claimed.next_random_word_index,
            claimed.transcript_commitment,
            claimed.observer_signature_hex,
        )
        if replayed.canonical_bytes != claimed.canonical_bytes:
            _fail("signed batch V2 bytes differ from semantic replay")
        return replayed
    except (
        AttributeError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "signed batch V2 semantic reconstruction failed"
        ) from error


@dataclass(frozen=True, slots=True)
class V075ObserverBatchJournalEntryV2:
    sequence_number: int
    previous_entry_id: str | None
    batch: V075SignedObservationBatchV2

    def __post_init__(self) -> None:
        if (
            type(self.sequence_number) is not int
            or self.sequence_number <= 0
            or type(self.batch) is not V075SignedObservationBatchV2
            or (self.sequence_number == 1)
            != (self.previous_entry_id is None)
        ):
            _fail("observer batch journal entry V2 is malformed")
        if self.previous_entry_id is not None:
            _cid(
                self.previous_entry_id,
                "previous observer batch journal entry V2",
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observer_batch_journal_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.batch.request.occurrence_id,
            "observer_session_public_id": (
                self.batch.request.session_public_id
            ),
            "observer_open_binding_id": (
                self.batch.request.authority_binding.binding_id
            ),
            "sequence_number": self.sequence_number,
            "previous_entry_id": self.previous_entry_id,
            "batch_id": self.batch.batch_id,
        }

    @property
    def entry_id(self) -> str:
        return _hash("batch_journal_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "batch": self.batch.to_document(),
            "entry_id": self.entry_id,
        }


class _AppendOnlyObserverBatchJournalV2:
    __slots__ = (
        "_authority_binding",
        "_closed",
        "_entries",
        "_entry_document_bytes_total",
        "_occurrence_id",
        "_session_public_id",
    )

    def __init__(
        self,
        *,
        occurrence_id: str,
        session_public_id: str,
        authority_binding: V075ObserverOpenAuthorityBindingV2,
    ) -> None:
        self._occurrence_id = _cid(
            occurrence_id,
            "observer batch occurrence",
        )
        self._session_public_id = _cid(
            session_public_id,
            "observer batch session",
        )
        self._authority_binding = authority_binding
        self._entries: list[V075ObserverBatchJournalEntryV2] = []
        self._entry_document_bytes_total = 0
        self._closed = False

    @property
    def entries(self) -> tuple[V075ObserverBatchJournalEntryV2, ...]:
        return tuple(self._entries)

    def append(
        self,
        batch: V075SignedObservationBatchV2,
    ) -> V075ObserverBatchJournalEntryV2:
        if self._closed:
            _fail("observer batch journal V2 is already closed")
        if len(self._entries) >= MAX_BATCHES_PER_SESSION:
            _fail("observer batch journal V2 batch-count cap is exhausted")
        if (
            type(batch) is not V075SignedObservationBatchV2
            or batch.request.occurrence_id != self._occurrence_id
            or batch.request.session_public_id != self._session_public_id
            or batch.request.authority_binding != self._authority_binding
        ):
            _fail("observer batch journal V2 rejected a foreign batch")
        entry = V075ObserverBatchJournalEntryV2(
            len(self._entries) + 1,
            None if not self._entries else self._entries[-1].entry_id,
            batch,
        )
        prospective_entries = (*self._entries, entry)
        entry_document_size = len(
            canonical_json_bytes(entry.to_document())
        )
        prospective_entry_bytes = (
            self._entry_document_bytes_total + entry_document_size
        )
        if (
            _projected_observer_batch_journal_closure_size_v2(
                occurrence_id=self._occurrence_id,
                session_public_id=self._session_public_id,
                authority_binding=self._authority_binding,
                entries=prospective_entries,
                entry_document_bytes_total=prospective_entry_bytes,
            )
            > MAX_CANONICAL_CLOSURE_BYTES
        ):
            _fail(
                "observer batch journal V2 cumulative closure byte cap "
                "would be exceeded"
            )
        self._entries.append(entry)
        self._entry_document_bytes_total = prospective_entry_bytes
        return entry

    def close(
        self,
        *,
        signer: V075ObserverEvidenceSignerProtocolV2,
    ) -> "V075ObserverBatchJournalClosureV2":
        if self._closed or not self._entries:
            _fail("observer batch journal V2 cannot close empty or twice")
        entries = self.entries
        message = observer_batch_journal_closure_signing_bytes_v2(
            occurrence_id=self._occurrence_id,
            session_public_id=self._session_public_id,
            authority_binding=self._authority_binding,
            entries=entries,
        )
        signature = _sign(
            signer=signer,
            expected_key=(
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
        )
        closure = V075ObserverBatchJournalClosureV2(
            self._occurrence_id,
            self._session_public_id,
            self._authority_binding,
            entries,
            signature,
        )
        self._closed = True
        return closure


@dataclass(frozen=True, slots=True)
class V075ObserverJournalEntryV2:
    sequence_number: int
    previous_entry_id: str | None
    record: V075SignedObservationRecordV2

    def __post_init__(self) -> None:
        if (
            type(self.sequence_number) is not int
            or self.sequence_number <= 0
            or type(self.record) is not V075SignedObservationRecordV2
            or (self.sequence_number == 1)
            != (self.previous_entry_id is None)
        ):
            _fail("observer journal entry V2 is malformed")
        if self.previous_entry_id is not None:
            _cid(
                self.previous_entry_id,
                "previous observer journal entry V2",
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_append_only_observer_journal_entry.v2",
            "schema_version": SCHEMA_VERSION,
            "observer_session_public_id": self.record.session_public_id,
            "observer_open_binding_id": (
                self.record.authority_binding.binding_id
            ),
            "sequence_number": self.sequence_number,
            "previous_entry_id": self.previous_entry_id,
            "record_id": self.record.record_id,
        }

    @property
    def entry_id(self) -> str:
        return _hash("journal_entry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "record": self.record.to_document(),
            "entry_id": self.entry_id,
        }


def _journal_closure_payload(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    entries: tuple[V075ObserverJournalEntryV2, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_append_only_observer_journal_closure.v2",
        "schema_version": SCHEMA_VERSION,
        "observer_session_public_id": _cid(
            session_public_id,
            "observer V2 session",
        ),
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": (
            authority_binding.authorization_id
        ),
        "private_reveal_attestation_id": (
            authority_binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": authority_binding.remote_main_anchor_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            authority_binding.namespace.environment_commitment.commitment_id
        ),
        "signer_registry_id": (
            authority_binding.namespace.signer_registry.registry_id
        ),
        "entry_ids": [entry.entry_id for entry in entries],
        "entry_count": len(entries),
        "tail_entry_id": None if not entries else entries[-1].entry_id,
        "authority_version": "V2",
        "namespace_version": "V2",
        "append_only_hash_chain_closed": True,
        "private_material_serialized": False,
    }


def observer_journal_closure_signing_bytes_v2(
    *,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    entries: tuple[V075ObserverJournalEntryV2, ...],
) -> bytes:
    if (
        type(authority_binding) is not V075ObserverOpenAuthorityBindingV2
        or type(entries) is not tuple
        or any(type(entry) is not V075ObserverJournalEntryV2 for entry in entries)
    ):
        _fail("observer journal closure V2 signing graph is untyped")
    return (
        DOMAIN_TAGS["journal_closure_signature"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(
            _journal_closure_payload(
                session_public_id=session_public_id,
                authority_binding=authority_binding,
                entries=entries,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class V075ObserverJournalClosureV2:
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV2
    entries: tuple[V075ObserverJournalEntryV2, ...]
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV2
            or type(self.entries) is not tuple
            or any(
                type(entry) is not V075ObserverJournalEntryV2
                for entry in self.entries
            )
        ):
            _fail("observer journal closure V2 is untyped")
        expected_previous: str | None = None
        for index, entry in enumerate(self.entries, start=1):
            if (
                entry.sequence_number != index
                or entry.previous_entry_id != expected_previous
                or entry.record.session_public_id != self.session_public_id
                or entry.record.authority_binding != self.authority_binding
            ):
                _fail("observer journal V2 chain is reordered or transplanted")
            expected_previous = entry.entry_id
        message = observer_journal_closure_signing_bytes_v2(
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            entries=self.entries,
        )
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
            signature_hex=self.observer_signature_hex,
        ):
            _fail("observer journal closure V2 signature is invalid")

    @property
    def closure_id(self) -> str:
        return _hash(
            "journal_closure_artifact",
            {
                **_journal_closure_payload(
                    session_public_id=self.session_public_id,
                    authority_binding=self.authority_binding,
                    entries=self.entries,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_journal_closure_payload(
                session_public_id=self.session_public_id,
                authority_binding=self.authority_binding,
                entries=self.entries,
            ),
            "observer_open_binding": self.authority_binding.to_document(),
            "entries": [entry.to_document() for entry in self.entries],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _observer_batch_journal_closure_payload(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    entries: tuple[V075ObserverBatchJournalEntryV2, ...],
) -> dict[str, Any]:
    stream_ids = tuple(
        sorted({entry.batch.request.stream_identity.stream_id for entry in entries})
    )
    return {
        "schema": "acfqp.v075_observer_batch_journal_closure.v2",
        "schema_version": SCHEMA_VERSION,
        "occurrence_id": _cid(occurrence_id, "batch closure occurrence"),
        "observer_session_public_id": _cid(
            session_public_id,
            "batch closure session",
        ),
        "observer_open_binding_id": authority_binding.binding_id,
        "observer_open_authorization_id": (
            authority_binding.authorization_id
        ),
        "private_reveal_attestation_id": (
            authority_binding.private_reveal_attestation_id
        ),
        "remote_main_anchor_id": authority_binding.remote_main_anchor_id,
        "target_tape_namespace_id": (
            authority_binding.namespace.target_tape_namespace_id
        ),
        "environment_commitment_id": (
            authority_binding.namespace.environment_commitment.commitment_id
        ),
        "entry_ids": [entry.entry_id for entry in entries],
        "batch_ids": [entry.batch.batch_id for entry in entries],
        "stream_ids": list(stream_ids),
        "entry_count": len(entries),
        "batch_count": len(entries),
        "accepted_draw_count": sum(
            entry.batch.request.accepted_draw_count for entry in entries
        ),
        "tail_entry_id": None if not entries else entries[-1].entry_id,
        "journal_role": "BATCH_NATIVE_ONLY",
        "per_draw_journal_entries": 0,
        "append_only_hash_chain_closed": True,
        "private_material_serialized": False,
    }


def _projected_observer_batch_journal_closure_size_v2(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    entries: tuple[V075ObserverBatchJournalEntryV2, ...],
    entry_document_bytes_total: int | None = None,
) -> int:
    """Exact byte length using fixed-width signature/content-ID placeholders."""

    if (
        type(entries) is not tuple
        or not entries
        or any(
            type(entry) is not V075ObserverBatchJournalEntryV2
            for entry in entries
        )
    ):
        _fail("batch closure V2 size projection requires typed entries")
    if entry_document_bytes_total is None:
        entry_document_bytes_total = sum(
            len(canonical_json_bytes(entry.to_document()))
            for entry in entries
        )
    if (
        type(entry_document_bytes_total) is not int
        or entry_document_bytes_total <= 0
    ):
        _fail("batch closure V2 entry-byte total is invalid")
    key = authority_binding.namespace.signer_registry.observer_evidence_key
    signature_hex_width = ((key.modulus.bit_length() + 7) // 8) * 2
    shell = {
        **_observer_batch_journal_closure_payload(
            occurrence_id=occurrence_id,
            session_public_id=session_public_id,
            authority_binding=authority_binding,
            entries=entries,
        ),
        "observer_open_binding": authority_binding.to_document(),
        "entries": [],
        "observer_signature_hex": "0" * signature_hex_width,
        "observer_signature_verified": True,
        "closure_id": "0" * 64,
    }
    shell_size = len(canonical_json_bytes(shell))
    # ``[]`` occupies two bytes in the shell.  A nonempty canonical array is
    # one opening byte, the exact entry documents, n-1 commas, and one close.
    entries_array_size = (
        entry_document_bytes_total + len(entries) + 1
    )
    return shell_size - 2 + entries_array_size


def observer_batch_journal_closure_signing_bytes_v2(
    *,
    occurrence_id: str,
    session_public_id: str,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    entries: tuple[V075ObserverBatchJournalEntryV2, ...],
) -> bytes:
    if (
        type(authority_binding) is not V075ObserverOpenAuthorityBindingV2
        or type(entries) is not tuple
        or not entries
        or any(
            type(entry) is not V075ObserverBatchJournalEntryV2
            for entry in entries
        )
    ):
        _fail("observer batch closure V2 signing graph is untyped")
    return (
        DOMAIN_TAGS["batch_journal_closure_signature"].encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(
            _observer_batch_journal_closure_payload(
                occurrence_id=occurrence_id,
                session_public_id=session_public_id,
                authority_binding=authority_binding,
                entries=entries,
            )
        )
    )


@dataclass(frozen=True, slots=True)
class V075ObserverBatchJournalClosureV2:
    occurrence_id: str
    session_public_id: str
    authority_binding: V075ObserverOpenAuthorityBindingV2
    entries: tuple[V075ObserverBatchJournalEntryV2, ...]
    observer_signature_hex: str

    def __post_init__(self) -> None:
        if (
            type(self.authority_binding)
            is not V075ObserverOpenAuthorityBindingV2
            or type(self.entries) is not tuple
            or not self.entries
            or len(self.entries) > MAX_BATCHES_PER_SESSION
            or any(
                type(entry) is not V075ObserverBatchJournalEntryV2
                for entry in self.entries
            )
        ):
            _fail(
                "observer batch journal closure V2 is untyped, empty, "
                "or over its batch-count cap"
            )
        expected_previous: str | None = None
        next_index_by_stream: dict[str, int] = {}
        cap_by_stream: dict[str, int] = {}
        request_ids: set[str] = set()
        batch_ids: set[str] = set()
        for index, entry in enumerate(self.entries, start=1):
            request = entry.batch.request
            stream_id = request.stream_identity.stream_id
            expected_start = next_index_by_stream.get(stream_id, 1)
            prior_cap = cap_by_stream.setdefault(
                stream_id,
                request.accepted_draw_cap,
            )
            if (
                entry.sequence_number != index
                or entry.previous_entry_id != expected_previous
                or request.occurrence_id != self.occurrence_id
                or request.session_public_id != self.session_public_id
                or request.authority_binding != self.authority_binding
                or request.accepted_draw_start != expected_start
                or request.accepted_draw_cap != prior_cap
                or request.request_id in request_ids
                or entry.batch.batch_id in batch_ids
            ):
                _fail(
                    "observer batch journal V2 is gapped, reused, or "
                    "transplanted"
                )
            expected_previous = entry.entry_id
            next_index_by_stream[stream_id] = request.accepted_draw_end + 1
            request_ids.add(request.request_id)
            batch_ids.add(entry.batch.batch_id)
        message = observer_batch_journal_closure_signing_bytes_v2(
            occurrence_id=self.occurrence_id,
            session_public_id=self.session_public_id,
            authority_binding=self.authority_binding,
            entries=self.entries,
        )
        if not public.verify_rsa_pkcs1_v1_5_sha256_signature_v1(
            public_key=(
                self.authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
            signature_hex=self.observer_signature_hex,
        ):
            _fail("observer batch journal closure V2 signature is invalid")

    @property
    def closure_id(self) -> str:
        return _hash(
            "batch_journal_closure_artifact",
            {
                **_observer_batch_journal_closure_payload(
                    occurrence_id=self.occurrence_id,
                    session_public_id=self.session_public_id,
                    authority_binding=self.authority_binding,
                    entries=self.entries,
                ),
                "observer_signature_hex": self.observer_signature_hex,
                "observer_signature_verified": True,
            },
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **_observer_batch_journal_closure_payload(
                occurrence_id=self.occurrence_id,
                session_public_id=self.session_public_id,
                authority_binding=self.authority_binding,
                entries=self.entries,
            ),
            "observer_open_binding": self.authority_binding.to_document(),
            "entries": [entry.to_document() for entry in self.entries],
            "observer_signature_hex": self.observer_signature_hex,
            "observer_signature_verified": True,
            "closure_id": self.closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


class _AppendOnlyObserverJournalV2:
    __slots__ = (
        "_authority_binding",
        "_closed",
        "_entries",
        "_session_public_id",
    )

    def __init__(
        self,
        *,
        session_public_id: str,
        authority_binding: V075ObserverOpenAuthorityBindingV2,
    ) -> None:
        self._session_public_id = _cid(
            session_public_id,
            "observer V2 session",
        )
        self._authority_binding = authority_binding
        self._entries: list[V075ObserverJournalEntryV2] = []
        self._closed = False

    @property
    def entries(self) -> tuple[V075ObserverJournalEntryV2, ...]:
        return tuple(self._entries)

    def append(
        self,
        record: V075SignedObservationRecordV2,
    ) -> V075ObserverJournalEntryV2:
        if self._closed:
            _fail("observer journal V2 is already closed")
        if (
            type(record) is not V075SignedObservationRecordV2
            or record.session_public_id != self._session_public_id
            or record.authority_binding != self._authority_binding
        ):
            _fail("observer journal V2 rejected a foreign record")
        entry = V075ObserverJournalEntryV2(
            len(self._entries) + 1,
            None if not self._entries else self._entries[-1].entry_id,
            record,
        )
        self._entries.append(entry)
        return entry

    def close(
        self,
        *,
        signer: V075ObserverEvidenceSignerProtocolV2,
    ) -> V075ObserverJournalClosureV2:
        if self._closed:
            _fail("observer journal V2 already emitted its unique closure")
        entries = self.entries
        message = observer_journal_closure_signing_bytes_v2(
            session_public_id=self._session_public_id,
            authority_binding=self._authority_binding,
            entries=entries,
        )
        signature = _sign(
            signer=signer,
            expected_key=(
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key
            ),
            message=message,
        )
        closure = V075ObserverJournalClosureV2(
            self._session_public_id,
            self._authority_binding,
            entries,
            signature,
        )
        self._closed = True
        return closure


_BATCH_OPEN_ELIGIBILITY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOpenEligibilityV2:
    """Immutable public view of whether this session may start a batch."""

    _issuer: object = field(repr=False, compare=False)
    session_public_id: str
    observer_open_binding_id: str
    eligible: bool
    status: str
    session_mode: str
    occurrence_id: str | None
    existing_batch_count: int
    maximum_batch_count: int
    _eligibility_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.session_public_id, "batch eligibility session")
        _cid(self.observer_open_binding_id, "batch eligibility binding")
        if self.occurrence_id is not None:
            _cid(self.occurrence_id, "batch eligibility occurrence")
        valid_statuses = {
            "ELIGIBLE",
            "INELIGIBLE_PER_DRAW_MODE",
            "INELIGIBLE_CLOSED",
            "INELIGIBLE_POISONED",
            "INELIGIBLE_BATCH_COUNT_CAP",
        }
        if (
            self._issuer is not _BATCH_OPEN_ELIGIBILITY_ISSUER
            or type(self.eligible) is not bool
            or self.status not in valid_statuses
            or self.eligible != (self.status == "ELIGIBLE")
            or self.session_mode
            not in {"UNUSED", "PER_DRAW", "BATCH_NATIVE"}
            or type(self.existing_batch_count) is not int
            or self.existing_batch_count < 0
            or type(self.maximum_batch_count) is not int
            or self.maximum_batch_count <= 0
            or self.existing_batch_count > self.maximum_batch_count
            or (
                self.session_mode == "BATCH_NATIVE"
                and self.occurrence_id is None
            )
            or (
                self.session_mode != "BATCH_NATIVE"
                and self.occurrence_id is not None
            )
        ):
            _fail("batch-open eligibility V2 is malformed or caller-minted")
        object.__setattr__(
            self,
            "_eligibility_id",
            _hash("batch_open_eligibility", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_open_eligibility.v2",
            "schema_version": SCHEMA_VERSION,
            "observer_session_public_id": self.session_public_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "eligible": self.eligible,
            "status": self.status,
            "session_mode": self.session_mode,
            "occurrence_id": self.occurrence_id,
            "existing_batch_count": self.existing_batch_count,
            "maximum_batch_count": self.maximum_batch_count,
            "read_only": True,
            "private_material_serialized": False,
        }

    @property
    def eligibility_id(self) -> str:
        return self._eligibility_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "eligibility_id": self.eligibility_id}


_SESSION_ISSUER = object()


class V075PrivateObserverSessionV2:
    """Private exact-V2 session; only signed law-free records leave it."""

    __slots__ = (
        "_authority_binding",
        "_batch_cap_by_stream",
        "_batch_journal",
        "_batch_occurrence_id",
        "_closed",
        "_journal",
        "_kernels",
        "_mode",
        "_poisoned",
        "_session_public_id",
        "_signer",
        "_stream_identities",
        "_streams",
    )

    def __init__(
        self,
        *,
        authority_binding: V075ObserverOpenAuthorityBindingV2,
        kernels: Mapping[str, H2GraphKernelV1],
        signer: V075ObserverEvidenceSignerProtocolV2,
        session_external_id: str,
        issuer: object,
    ) -> None:
        if (
            issuer is not _SESSION_ISSUER
            or type(authority_binding)
            is not V075ObserverOpenAuthorityBindingV2
        ):
            _fail("private observer V2 sessions are boundary-issued only")
        external_id = _cid(
            session_external_id,
            "observer V2 session external identity",
        )
        self._authority_binding = authority_binding
        self._session_public_id = _hash(
            "session",
            {
                "schema": (
                    "acfqp.v075_private_observer_session_public_identity.v2"
                ),
                "schema_version": SCHEMA_VERSION,
                "observer_open_binding_id": authority_binding.binding_id,
                "observer_open_authorization_id": (
                    authority_binding.authorization_id
                ),
                "private_reveal_attestation_id": (
                    authority_binding.private_reveal_attestation_id
                ),
                "remote_main_anchor_id": (
                    authority_binding.remote_main_anchor_id
                ),
                "target_tape_namespace_id": (
                    authority_binding.namespace.target_tape_namespace_id
                ),
                "environment_commitment_id": (
                    authority_binding.namespace.environment_commitment
                    .commitment_id
                ),
                "signer_registry_id": (
                    authority_binding.namespace.signer_registry.registry_id
                ),
                "observer_signer_key_id": (
                    authority_binding.namespace.signer_registry
                    .observer_evidence_key.key_id
                ),
                "session_external_id": external_id,
                "authority_version": "V2",
                "namespace_version": "V2",
                "private_material_serialized": False,
            },
        )
        self._kernels = dict(kernels)
        self._signer = signer
        self._streams: dict[str, DeterministicH2GraphStreamV1] = {}
        self._stream_identities: dict[
            str,
            graph.V075TransitionStreamIdentityV1,
        ] = {}
        self._journal = _AppendOnlyObserverJournalV2(
            session_public_id=self._session_public_id,
            authority_binding=authority_binding,
        )
        self._batch_journal: _AppendOnlyObserverBatchJournalV2 | None = None
        self._batch_occurrence_id: str | None = None
        self._batch_cap_by_stream: dict[str, int] = {}
        self._mode: str | None = None
        self._closed = False
        self._poisoned = False

    @property
    def session_public_id(self) -> str:
        return self._session_public_id

    @property
    def authority_binding(self) -> V075ObserverOpenAuthorityBindingV2:
        return self._authority_binding

    @property
    def journal_entries(self) -> tuple[V075ObserverJournalEntryV2, ...]:
        return self._journal.entries

    @property
    def batch_journal_entries(
        self,
    ) -> tuple[V075ObserverBatchJournalEntryV2, ...]:
        if self._batch_journal is None:
            return ()
        return self._batch_journal.entries

    @property
    def batch_open_eligibility_v2(self) -> V075BatchOpenEligibilityV2:
        batch_count = len(self.batch_journal_entries)
        if self._poisoned:
            status = "INELIGIBLE_POISONED"
        elif self._closed:
            status = "INELIGIBLE_CLOSED"
        elif self._mode == "PER_DRAW":
            status = "INELIGIBLE_PER_DRAW_MODE"
        elif batch_count >= MAX_BATCHES_PER_SESSION:
            status = "INELIGIBLE_BATCH_COUNT_CAP"
        else:
            status = "ELIGIBLE"
        return V075BatchOpenEligibilityV2(
            _BATCH_OPEN_ELIGIBILITY_ISSUER,
            self._session_public_id,
            self._authority_binding.binding_id,
            status == "ELIGIBLE",
            status,
            "UNUSED" if self._mode is None else self._mode,
            self._batch_occurrence_id,
            batch_count,
            MAX_BATCHES_PER_SESSION,
        )

    def _clear_private_state_v2(self, *, poisoned: bool) -> None:
        self._poisoned = poisoned
        self._closed = True
        self._streams.clear()
        self._stream_identities.clear()
        self._batch_cap_by_stream.clear()
        self._kernels.clear()
        self._signer = None

    def _private_stream_v2(
        self,
        stream_identity: graph.V075TransitionStreamIdentityV1,
    ) -> tuple[
        graph.V075TransitionStreamIdentityV1,
        DeterministicH2GraphStreamV1,
    ]:
        stream_identity = _validate_v2_stream_shallow(
            binding=self._authority_binding,
            stream_identity=stream_identity,
        )
        context = stream_identity.row_binding.context
        kernel = self._kernels.get(context.context_id)
        if type(kernel) is not H2GraphKernelV1:
            _fail("observer V2 lacks the private kernel for this context")
        stream = self._streams.get(stream_identity.stream_id)
        prior_identity = self._stream_identities.get(
            stream_identity.stream_id
        )
        if stream is None:
            stream_identity = _validate_v2_stream(
                binding=self._authority_binding,
                stream_identity=stream_identity,
            )
            try:
                stream = DeterministicH2GraphStreamV1(
                    kernel=kernel,
                    state=(
                        stream_identity.row_binding.catalogue.state
                        .to_kernel_state()
                    ),
                    action=H2GraphActionV1(*stream_identity.action),
                    remaining_horizon=(
                        stream_identity.row_binding.remaining_horizon
                    ),
                    seed=stream_identity.seed,
                )
            except H2GraphTransitionInvariantViolation as error:
                raise V075PrivateObserverBoundaryV2InvariantViolation(
                    str(error)
                ) from error
            self._streams[stream_identity.stream_id] = stream
            self._stream_identities[stream_identity.stream_id] = (
                stream_identity
            )
        elif prior_identity != stream_identity:
            _fail("one V2 stream ID was assigned multiple typed identities")
        return stream_identity, stream

    def public_session_document_v2(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_observer_session_public_identity.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "observer_session_public_id": self._session_public_id,
            "observer_open_binding_id": self._authority_binding.binding_id,
            "observer_open_authorization_id": (
                self._authority_binding.authorization_id
            ),
            "private_reveal_attestation_id": (
                self._authority_binding.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": (
                self._authority_binding.remote_main_anchor_id
            ),
            "target_tape_namespace_id": (
                self._authority_binding.namespace.target_tape_namespace_id
            ),
            "environment_commitment_id": (
                self._authority_binding.namespace.environment_commitment
                .commitment_id
            ),
            "signer_registry_id": (
                self._authority_binding.namespace.signer_registry.registry_id
            ),
            "observer_signer_key_id": (
                self._authority_binding.namespace.signer_registry
                .observer_evidence_key.key_id
            ),
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_projection_issued": False,
            "private_material_serialized": False,
        }

    def observe_v2(
        self,
        stream_identity: graph.V075TransitionStreamIdentityV1,
    ) -> V075ObservationCapabilityV2:
        if self._closed or self._poisoned:
            _fail("private observer V2 session is closed")
        if self._mode not in (None, "PER_DRAW"):
            _fail("batch-native and per-draw observer journals cannot mix")
        if (
            len(self._journal.entries)
            >= MAX_PER_DRAW_RECORDS_PER_SESSION
        ):
            _fail("per-draw observer V2 session record cap is exhausted")
        stream_identity, stream = self._private_stream_v2(stream_identity)
        self._mode = "PER_DRAW"
        self._poisoned = True
        try:
            sample = stream.draw()
            message = observation_record_signing_bytes_v2(
                session_public_id=self._session_public_id,
                authority_binding=self._authority_binding,
                stream_identity=stream_identity,
                sample=sample,
            )
            signature = _sign(
                signer=self._signer,
                expected_key=(
                    self._authority_binding.namespace.signer_registry
                    .observer_evidence_key
                ),
                message=message,
            )
            record = V075SignedObservationRecordV2(
                self._session_public_id,
                self._authority_binding,
                stream_identity,
                sample,
                signature,
            )
            if len(record.canonical_bytes) > MAX_PER_DRAW_RECORD_BYTES:
                _fail(
                    "per-draw observer V2 record exceeded its generation cap"
                )
            self._journal.append(record)
            capability = V075ObservationCapabilityV2(record)
        except Exception:
            self._clear_private_state_v2(poisoned=True)
            raise
        self._poisoned = False
        return capability

    def observe_batch_v2(
        self,
        *,
        occurrence_id: str,
        stream_identity: graph.V075TransitionStreamIdentityV1,
        accepted_draw_start: int,
        accepted_draw_count: int,
        accepted_draw_cap: int,
    ) -> V075SignedObservationBatchV2:
        """Observe one exact interval without retaining per-draw evidence."""

        if self._closed or self._poisoned:
            _fail("private observer V2 session is closed")
        if self._mode not in (None, "BATCH_NATIVE"):
            _fail("batch-native and per-draw observer journals cannot mix")
        if (
            self._batch_journal is not None
            and len(self._batch_journal.entries)
            >= MAX_BATCHES_PER_SESSION
        ):
            _fail("observer batch journal V2 batch-count cap is exhausted")
        occurrence_id = _cid(occurrence_id, "batch V2 occurrence")
        if self._batch_occurrence_id not in (None, occurrence_id):
            _fail("one batch-native session cannot cross occurrences")
        stream_identity, stream = self._private_stream_v2(stream_identity)
        request = V075BatchObservationRequestV2(
            _BATCH_REQUEST_ISSUER,
            occurrence_id,
            self._session_public_id,
            self._authority_binding,
            stream_identity,
            accepted_draw_start,
            accepted_draw_count,
            accepted_draw_cap,
        )
        prior_cap = self._batch_cap_by_stream.get(stream_identity.stream_id)
        if prior_cap not in (None, request.accepted_draw_cap):
            _fail("one batch V2 stream cannot change its frozen draw cap")
        if request.accepted_draw_start != stream.accepted_draw_count + 1:
            _fail("batch V2 request does not continue the stream prefix")
        if self._batch_journal is None:
            self._batch_journal = _AppendOnlyObserverBatchJournalV2(
                occurrence_id=occurrence_id,
                session_public_id=self._session_public_id,
                authority_binding=self._authority_binding,
            )
            self._batch_occurrence_id = occurrence_id
        self._mode = "BATCH_NATIVE"
        self._poisoned = True
        try:
            accumulator = _StreamingBatchAccumulatorV2(request)
            for _ in range(request.accepted_draw_count):
                accumulator.append(stream.draw())
            facts = accumulator.finish()
            signature = _sign(
                signer=self._signer,
                expected_key=(
                    self._authority_binding.namespace.signer_registry
                    .observer_evidence_key
                ),
                message=batch_observation_signing_bytes_v2(
                    request=request,
                    facts=facts,
                ),
            )
            batch = V075SignedObservationBatchV2(
                request,
                facts.outcomes,
                facts.reward_sum,
                facts.failure_count,
                facts.terminal_count,
                facts.random_word_count,
                facts.rejection_count,
                facts.first_random_word_index,
                facts.next_random_word_index,
                facts.transcript_commitment,
                signature,
            )
            accounting_runtime.emit_owned_operation_v1(
                "private-observer.signed-batch.materialize"
            )
            if len(batch.canonical_bytes) > MAX_CANONICAL_CLOSURE_BYTES:
                _fail("batch V2 artifact exceeded its generation byte cap")
            self._batch_journal.append(batch)
            self._batch_cap_by_stream[stream_identity.stream_id] = (
                request.accepted_draw_cap
            )
            accounting_runtime.emit_owned_operation_v1(
                "private-observer.signed-batch.commit"
            )
        except Exception:
            self._clear_private_state_v2(poisoned=True)
            raise
        self._poisoned = False
        return batch

    def close_v2(self) -> V075ObserverJournalClosureV2:
        if self._closed or self._poisoned:
            _fail("private observer V2 session already closed")
        if self._mode == "BATCH_NATIVE":
            _fail("batch-native sessions must use close_batch_v2")
        self._mode = "PER_DRAW"
        self._poisoned = True
        try:
            closure = self._journal.close(signer=self._signer)
            if len(closure.canonical_bytes) > MAX_CANONICAL_CLOSURE_BYTES:
                _fail("per-draw observer V2 closure exceeded its byte cap")
        except Exception:
            self._clear_private_state_v2(poisoned=True)
            raise
        self._clear_private_state_v2(poisoned=False)
        return closure

    def close_batch_v2(self) -> V075ObserverBatchJournalClosureV2:
        if self._closed or self._poisoned:
            _fail("private observer V2 session already closed")
        if self._mode != "BATCH_NATIVE" or self._batch_journal is None:
            _fail("batch-native observer V2 session has no batch journal")
        self._poisoned = True
        try:
            closure = self._batch_journal.close(signer=self._signer)
            if len(closure.canonical_bytes) > MAX_CANONICAL_CLOSURE_BYTES:
                _fail("batch observer V2 closure exceeded its byte cap")
        except Exception:
            self._clear_private_state_v2(poisoned=True)
            raise
        self._clear_private_state_v2(poisoned=False)
        return closure


def _open_private_observer_from_verified_gate_v2(
    *,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    binding: V075ObserverOpenAuthorityBindingV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
) -> V075PrivateObserverSessionV2:
    if (
        type(authority) is not preopen.V075ObserverOpenAuthorizationV2
        or type(namespace)
        is not namespace_v2.V075PublicTargetTapeNamespaceV2
        or type(binding) is not V075ObserverOpenAuthorityBindingV2
        or binding
        != _require_exact_v2_binding(
            authority=authority,
            namespace=namespace,
        )
    ):
        _fail("verified observer V2 gate was altered before opening")
    environment = _canonical_private_environment(
        family=namespace.family,
        private_environment=private_environment,
    )
    _verify_private_reveal(
        binding=binding,
        authority=authority,
        private_salt=private_salt,
        private_environment=environment,
    )
    expected_key = namespace.signer_registry.observer_evidence_key
    if (
        not isinstance(observer_signer, V075ObserverEvidenceSignerProtocolV2)
        or observer_signer.public_verification_key_v1() != expected_key
    ):
        _fail("observer signer is not bound to the exact V2 namespace")
    kernels = {
        context.context_id: H2GraphKernelV1(
            context.topology,
            context.rank_cap,
            context.horizon,
            law,
        )
        for context, law in zip(
            namespace.family.replicate_contexts,
            environment,
            strict=True,
        )
    }
    return V075PrivateObserverSessionV2(
        authority_binding=binding,
        kernels=kernels,
        signer=observer_signer,
        session_external_id=session_external_id,
        issuer=_SESSION_ISSUER,
    )


def open_private_observer_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    observer_signer: V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
) -> V075PrivateObserverSessionV2:
    """Open only after repository, authorization, and namespace byte replay."""

    authority, namespace, binding = _replay_exact_v2_authority_namespace(
        repository_root=repository_root,
        private_reveal_attestation_bytes=(
            private_reveal_attestation_bytes
        ),
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
    )
    return _open_private_observer_from_verified_gate_v2(
        authority=authority,
        namespace=namespace,
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
        observer_signer=observer_signer,
        session_external_id=session_external_id,
    )


_CLOSURE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverClosureVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    observer_open_binding_id: str
    observer_open_authorization_id: str
    private_reveal_attestation_id: str
    remote_main_anchor_id: str
    target_tape_namespace_id: str
    replayed_record_count: int
    replayed_stream_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "observer journal closure V2"),
            (self.observer_open_binding_id, "observer-open binding V2"),
            (
                self.observer_open_authorization_id,
                "observer-open authorization V2",
            ),
            (
                self.private_reveal_attestation_id,
                "private reveal attestation V2",
            ),
            (self.remote_main_anchor_id, "remote-main anchor V2"),
            (self.target_tape_namespace_id, "target namespace V2"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CLOSURE_VERIFICATION_ISSUER
            or type(self.replayed_record_count) is not int
            or self.replayed_record_count < 0
            or type(self.replayed_stream_count) is not int
            or self.replayed_stream_count < 0
        ):
            _fail("observer closure verification V2 is invalid")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("closure_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_private_observer_journal_closure_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "verification_result": "EXACT_V2_REPLAY_VERIFIED",
            "replayed_record_count": self.replayed_record_count,
            "replayed_stream_count": self.replayed_stream_count,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_projection_used": False,
            "private_material_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _fraction_from_document(value: Any, field_name: str) -> Fraction:
    if type(value) is Fraction:
        return value
    if (
        type(value) is not dict
        or frozenset(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{field_name} is not one exact rational")
    result = Fraction(value["numerator"], value["denominator"])
    if _fraction_document(result) != value:
        _fail(f"{field_name} is not reduced canonical rational form")
    return result


def _sample_from_record_document(
    document: Mapping[str, Any],
) -> H2GraphSampleV1:
    try:
        next_ranks_raw = document["next_ranks"]
        random_words_raw = document["random_words"]
        if (
            type(next_ranks_raw) is not list
            or any(type(rank) is not int for rank in next_ranks_raw)
            or type(random_words_raw) is not list
            or any(type(word) is not int for word in random_words_raw)
        ):
            _fail("closure record sample arrays are not canonical")
        sample = H2GraphSampleV1(
            H2GraphStateV1(
                tuple(next_ranks_raw),
                document["failure"],
            ),
            _fraction_from_document(
                document["realized_row_reward"],
                "closure record reward",
            ),
            document["failure"],
            document["terminal"],
            document["spawn_cell"],
            document["spawn_rank"],
            document["accepted_draw_index"],
            document["random_word_start_index"],
            tuple(random_words_raw),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        H2GraphTransitionInvariantViolation,
    ) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "closure record sample reconstruction failed"
        ) from error
    return sample


def _load_and_replay_observer_journal_closure_v2(
    *,
    raw: bytes,
    binding: V075ObserverOpenAuthorityBindingV2,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
) -> V075ObserverJournalClosureV2:
    """Strictly reconstruct every record, entry, signature, ID, and link."""

    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_CLOSURE_BYTES
        or type(known_stream_identities) is not tuple
    ):
        _fail("closure V2 bytes or known-stream tuple is invalid")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "closure V2 is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("closure V2 is not one canonical object")
    streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for claimed in known_stream_identities:
        replayed = _replay_v2_stream_identity(claimed)
        if replayed.namespace != binding.namespace:
            _fail("known closure stream carries a foreign V2 namespace")
        if replayed.stream_id in streams:
            _fail("known closure stream IDs are duplicated")
        streams[replayed.stream_id] = replayed
    try:
        entries_document = document["entries"]
        if type(entries_document) is not list:
            _fail("closure V2 entries must be one canonical array")
        entries: list[V075ObserverJournalEntryV2] = []
        used_stream_ids: set[str] = set()
        for item in entries_document:
            if type(item) is not dict or type(item.get("record")) is not dict:
                _fail("closure V2 entry/record is not canonical")
            record_document = item["record"]
            stream_id = _cid(
                record_document["stream_id"],
                "closure record stream",
            )
            stream = streams.get(stream_id)
            if stream is None:
                _fail("closure V2 record lacks a prereplayed stream identity")
            used_stream_ids.add(stream_id)
            record = V075SignedObservationRecordV2(
                _cid(
                    record_document["observer_session_public_id"],
                    "closure record session",
                ),
                binding,
                stream,
                _sample_from_record_document(record_document),
                record_document["observer_signature_hex"],
            )
            if canonical_json_bytes(
                record.to_document()
            ) != canonical_json_bytes(record_document):
                _fail(
                    "closure V2 record fields, signature, or content ID "
                    "differ from replay"
                )
            entry = V075ObserverJournalEntryV2(
                item["sequence_number"],
                item["previous_entry_id"],
                record,
            )
            if canonical_json_bytes(
                entry.to_document()
            ) != canonical_json_bytes(item):
                _fail("closure V2 entry ID or hash-chain link differs")
            entries.append(entry)
        if set(streams) != used_stream_ids:
            _fail("known closure stream set is not the exact used stream set")
        closure = V075ObserverJournalClosureV2(
            _cid(
                document["observer_session_public_id"],
                "closure V2 session",
            ),
            binding,
            tuple(entries),
            document["observer_signature_hex"],
        )
        if (
            canonical_json_bytes(closure.to_document()) != raw
        ):
            _fail(
                "closure V2 fields, signature, IDs, or chain differ from "
                "canonical replay"
            )
        return closure
    except (
        KeyError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "closure V2 semantic reconstruction failed"
        ) from error


def _verify_private_observer_journal_closure_from_verified_gate_v2(
    *,
    closure: V075ObserverJournalClosureV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    binding: V075ObserverOpenAuthorityBindingV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverClosureVerificationV2:
    """Replay a closure only after both public byte graphs were rebuilt."""

    if (
        type(closure) is not V075ObserverJournalClosureV2
        or type(binding) is not V075ObserverOpenAuthorityBindingV2
        or binding != closure.authority_binding
        or binding
        != _require_exact_v2_binding(
            authority=authority,
            namespace=namespace,
        )
    ):
        _fail("verified closure V2 gate was altered before private replay")
    environment = _canonical_private_environment(
        family=namespace.family,
        private_environment=private_environment,
    )
    _verify_private_reveal(
        binding=binding,
        authority=authority,
        private_salt=private_salt,
        private_environment=environment,
    )
    kernels = {
        context.context_id: H2GraphKernelV1(
            context.topology,
            context.rank_cap,
            context.horizon,
            law,
        )
        for context, law in zip(
            namespace.family.replicate_contexts,
            environment,
            strict=True,
        )
    }
    groups: dict[str, list[V075SignedObservationRecordV2]] = {}
    identities: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for entry in closure.entries:
        record = entry.record
        stream_id = record.stream_identity.stream_id
        prior = identities.setdefault(stream_id, record.stream_identity)
        if prior != record.stream_identity:
            _fail("one V2 stream ID was assigned multiple typed identities")
        groups.setdefault(stream_id, []).append(record)
    try:
        for stream_id, records in groups.items():
            stream_identity = identities[stream_id]
            if tuple(
                record.sample.accepted_draw_index for record in records
            ) != tuple(range(1, len(records) + 1)):
                _fail("V2 stream sample prefix is gapped or reordered")
            verify_deterministic_samples_v1(
                kernel=kernels[stream_identity.context_id],
                state=(
                    stream_identity.row_binding.catalogue.state
                    .to_kernel_state()
                ),
                action=H2GraphActionV1(*stream_identity.action),
                remaining_horizon=(
                    stream_identity.row_binding.remaining_horizon
                ),
                seed=stream_identity.seed,
                samples=tuple(record.sample for record in records),
            )
    except (
        H2GraphTransitionInvariantViolation,
        KeyError,
    ) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            str(error)
        ) from error
    return V075ObserverClosureVerificationV2(
        _CLOSURE_VERIFICATION_ISSUER,
        closure.closure_id,
        binding.binding_id,
        binding.authorization_id,
        binding.private_reveal_attestation_id,
        binding.remote_main_anchor_id,
        namespace.target_tape_namespace_id,
        len(closure.entries),
        len(groups),
    )


def verify_private_observer_journal_closure_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    closure_bytes: bytes,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverClosureVerificationV2:
    """Rebuild authority and closure bytes, then replay every sample prefix."""

    authority, namespace, binding = _replay_exact_v2_authority_namespace(
        repository_root=repository_root,
        private_reveal_attestation_bytes=(
            private_reveal_attestation_bytes
        ),
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
    )
    closure = _load_and_replay_observer_journal_closure_v2(
        raw=closure_bytes,
        binding=binding,
        known_stream_identities=known_stream_identities,
    )
    return _verify_private_observer_journal_closure_from_verified_gate_v2(
        closure=closure,
        authority=authority,
        namespace=namespace,
        binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def _outcome_from_batch_document(
    document: Mapping[str, Any],
) -> V075BatchOutcomeAggregateV2:
    try:
        next_ranks_raw = document["next_ranks"]
        if (
            type(next_ranks_raw) is not list
            or any(type(rank) is not int for rank in next_ranks_raw)
        ):
            _fail("batch closure outcome ranks are not canonical")
        outcome = V075BatchOutcomeAggregateV2(
            tuple(next_ranks_raw),
            document["failure"],
            document["terminal"],
            document["spawn_cell"],
            document["spawn_rank"],
            _fraction_from_document(
                document["realized_row_reward"],
                "batch closure outcome reward",
            ),
            document["count"],
            _fraction_from_document(
                document["reward_sum"],
                "batch closure outcome reward sum",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "batch closure outcome reconstruction failed"
        ) from error
    if canonical_json_bytes(outcome.to_document()) != canonical_json_bytes(
        dict(document)
    ):
        _fail("batch closure outcome ID or fields differ from replay")
    return outcome


def load_observer_batch_journal_closure_bytes_v2(
    *,
    raw: bytes,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
) -> V075ObserverBatchJournalClosureV2:
    """Reconstruct every batch, signature, ID, and chain link from bytes."""

    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_CLOSURE_BYTES
        or type(authority_binding)
        is not V075ObserverOpenAuthorityBindingV2
        or type(known_stream_identities) is not tuple
    ):
        _fail("batch closure V2 bytes, binding, or streams are invalid")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "batch closure V2 is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("batch closure V2 is not one canonical object")
    streams: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for claimed in known_stream_identities:
        replayed = _replay_v2_stream_identity(claimed)
        if replayed.namespace != authority_binding.namespace:
            _fail("known batch closure stream carries a foreign V2 namespace")
        if replayed.stream_id in streams:
            _fail("known batch closure stream IDs are duplicated")
        streams[replayed.stream_id] = replayed
    try:
        entries_document = document["entries"]
        if (
            type(entries_document) is not list
            or not entries_document
            or len(entries_document) > MAX_BATCHES_PER_SESSION
        ):
            _fail(
                "batch closure V2 entries must be one nonempty array "
                "within the batch-count cap"
            )
        entries: list[V075ObserverBatchJournalEntryV2] = []
        used_stream_ids: set[str] = set()
        for item in entries_document:
            if (
                type(item) is not dict
                or type(item.get("batch")) is not dict
            ):
                _fail("batch closure V2 entry/batch is not canonical")
            batch_document = item["batch"]
            request_document = batch_document.get("request")
            outcomes_document = batch_document.get("outcomes")
            if (
                type(request_document) is not dict
                or type(outcomes_document) is not list
                or not outcomes_document
            ):
                _fail("batch closure V2 request/outcomes are not canonical")
            stream_id = _cid(
                request_document["stream_id"],
                "batch closure request stream",
            )
            stream = streams.get(stream_id)
            if stream is None:
                _fail(
                    "batch closure V2 request lacks a prereplayed stream "
                    "identity"
                )
            used_stream_ids.add(stream_id)
            request = V075BatchObservationRequestV2(
                _BATCH_REQUEST_ISSUER,
                _cid(
                    request_document["occurrence_id"],
                    "batch closure request occurrence",
                ),
                _cid(
                    request_document["observer_session_public_id"],
                    "batch closure request session",
                ),
                authority_binding,
                stream,
                request_document["accepted_draw_start"],
                request_document["accepted_draw_count"],
                request_document["accepted_draw_cap"],
            )
            if canonical_json_bytes(
                request.to_document()
            ) != canonical_json_bytes(request_document):
                _fail("batch closure V2 request fields or ID differ")
            outcomes = tuple(
                _outcome_from_batch_document(outcome_document)
                for outcome_document in outcomes_document
            )
            batch = V075SignedObservationBatchV2(
                request,
                outcomes,
                _fraction_from_document(
                    batch_document["reward_sum"],
                    "batch closure reward sum",
                ),
                batch_document["failure_count"],
                batch_document["terminal_count"],
                batch_document["random_word_count"],
                batch_document["rejection_count"],
                batch_document["first_random_word_index"],
                batch_document["next_random_word_index"],
                _cid(
                    batch_document["transcript_commitment"],
                    "batch closure transcript",
                ),
                batch_document["observer_signature_hex"],
            )
            if canonical_json_bytes(
                batch.to_document()
            ) != canonical_json_bytes(batch_document):
                _fail(
                    "batch closure V2 batch fields, signature, or ID differ"
                )
            entry = V075ObserverBatchJournalEntryV2(
                item["sequence_number"],
                item["previous_entry_id"],
                batch,
            )
            if canonical_json_bytes(
                entry.to_document()
            ) != canonical_json_bytes(item):
                _fail("batch closure V2 entry ID or chain link differs")
            entries.append(entry)
        if set(streams) != used_stream_ids:
            _fail(
                "known batch closure stream set is not the exact used set"
            )
        closure = V075ObserverBatchJournalClosureV2(
            _cid(
                document["occurrence_id"],
                "batch closure V2 occurrence",
            ),
            _cid(
                document["observer_session_public_id"],
                "batch closure V2 session",
            ),
            authority_binding,
            tuple(entries),
            document["observer_signature_hex"],
        )
        if canonical_json_bytes(closure.to_document()) != raw:
            _fail(
                "batch closure V2 fields, signatures, IDs, or chain differ "
                "from canonical replay"
            )
        return closure
    except (
        KeyError,
        TypeError,
        ValueError,
        graph.V075PublicGraphSemanticsInvariantViolation,
    ) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            "batch closure V2 semantic reconstruction failed"
        ) from error


_BATCH_CLOSURE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ObserverBatchClosureVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    occurrence_id: str
    batch_ids: tuple[str, ...]
    observer_open_binding_id: str
    observer_open_authorization_id: str
    private_reveal_attestation_id: str
    remote_main_anchor_id: str
    target_tape_namespace_id: str
    replayed_batch_count: int
    replayed_draw_count: int
    replayed_stream_count: int
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "observer batch closure V2"),
            (self.occurrence_id, "observer batch occurrence V2"),
            (self.observer_open_binding_id, "observer-open binding V2"),
            (
                self.observer_open_authorization_id,
                "observer-open authorization V2",
            ),
            (
                self.private_reveal_attestation_id,
                "private reveal attestation V2",
            ),
            (self.remote_main_anchor_id, "remote-main anchor V2"),
            (self.target_tape_namespace_id, "target namespace V2"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _BATCH_CLOSURE_VERIFICATION_ISSUER
            or type(self.batch_ids) is not tuple
            or not self.batch_ids
            or any(
                _cid(value, "observer batch V2") != value
                for value in self.batch_ids
            )
            or len(set(self.batch_ids)) != len(self.batch_ids)
            or type(self.replayed_batch_count) is not int
            or self.replayed_batch_count != len(self.batch_ids)
            or self.replayed_batch_count > MAX_BATCHES_PER_SESSION
            or type(self.replayed_draw_count) is not int
            or self.replayed_draw_count <= 0
            or type(self.replayed_stream_count) is not int
            or self.replayed_stream_count <= 0
        ):
            _fail("observer batch closure verification V2 is invalid")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("batch_closure_verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_observer_batch_journal_closure_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "occurrence_id": self.occurrence_id,
            "batch_ids": list(self.batch_ids),
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "verification_result": "EXACT_BATCH_NATIVE_V2_REPLAY_VERIFIED",
            "replayed_batch_count": self.replayed_batch_count,
            "replayed_draw_count": self.replayed_draw_count,
            "replayed_stream_count": self.replayed_stream_count,
            "per_draw_records_replayed": 0,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_v1_projection_used": False,
            "private_material_serialized": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_loaded_private_observer_batch_closure_v2(
    *,
    closure: V075ObserverBatchJournalClosureV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    authority_binding: V075ObserverOpenAuthorityBindingV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverBatchClosureVerificationV2:
    """Privately regenerate every aggregate and transcript from its seed."""

    if (
        type(closure) is not V075ObserverBatchJournalClosureV2
        or type(closure.entries) is not tuple
        or not closure.entries
        or len(closure.entries) > MAX_BATCHES_PER_SESSION
        or type(authority_binding)
        is not V075ObserverOpenAuthorityBindingV2
        or authority_binding != closure.authority_binding
        or authority_binding
        != _require_exact_v2_binding(
            authority=authority,
            namespace=namespace,
        )
    ):
        _fail(
            "verified batch closure V2 gate was altered or exceeds the "
            "batch-count cap before replay"
        )
    environment = _canonical_private_environment(
        family=namespace.family,
        private_environment=private_environment,
    )
    _verify_private_reveal(
        binding=authority_binding,
        authority=authority,
        private_salt=private_salt,
        private_environment=environment,
    )
    kernels = {
        context.context_id: H2GraphKernelV1(
            context.topology,
            context.rank_cap,
            context.horizon,
            law,
        )
        for context, law in zip(
            namespace.family.replicate_contexts,
            environment,
            strict=True,
        )
    }
    streams: dict[str, DeterministicH2GraphStreamV1] = {}
    identities: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    replayed_draw_count = 0
    try:
        for entry in closure.entries:
            batch = entry.batch
            request = batch.request
            identity = request.stream_identity
            prior_identity = identities.setdefault(
                identity.stream_id,
                identity,
            )
            if prior_identity != identity:
                _fail(
                    "one batch V2 stream ID has multiple typed identities"
                )
            stream = streams.get(identity.stream_id)
            if stream is None:
                kernel = kernels[identity.context_id]
                stream = DeterministicH2GraphStreamV1(
                    kernel=kernel,
                    state=(
                        identity.row_binding.catalogue.state.to_kernel_state()
                    ),
                    action=H2GraphActionV1(*identity.action),
                    remaining_horizon=identity.row_binding.remaining_horizon,
                    seed=identity.seed,
                )
                streams[identity.stream_id] = stream
            if request.accepted_draw_start != stream.accepted_draw_count + 1:
                _fail("batch V2 private replay found a gapped interval")
            accumulator = _StreamingBatchAccumulatorV2(request)
            for _ in range(request.accepted_draw_count):
                accumulator.append(stream.draw())
            if accumulator.finish() != batch.facts:
                _fail(
                    "batch V2 aggregate or transcript differs from exact "
                    "private deterministic replay"
                )
            replayed_draw_count += request.accepted_draw_count
    except (H2GraphTransitionInvariantViolation, KeyError) as error:
        if type(error) is V075PrivateObserverBoundaryV2InvariantViolation:
            raise
        raise V075PrivateObserverBoundaryV2InvariantViolation(
            str(error)
        ) from error
    return V075ObserverBatchClosureVerificationV2(
        _BATCH_CLOSURE_VERIFICATION_ISSUER,
        closure.closure_id,
        closure.occurrence_id,
        tuple(entry.batch.batch_id for entry in closure.entries),
        authority_binding.binding_id,
        authority_binding.authorization_id,
        authority_binding.private_reveal_attestation_id,
        authority_binding.remote_main_anchor_id,
        namespace.target_tape_namespace_id,
        len(closure.entries),
        replayed_draw_count,
        len(streams),
    )


def replay_and_verify_private_observer_batch_journal_closure_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    batch_closure_bytes: bytes,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[
    V075ObserverBatchJournalClosureV2,
    V075ObserverBatchClosureVerificationV2,
]:
    """Return only the canonical byte-replayed closure and its verification."""

    authority, namespace, binding = _replay_exact_v2_authority_namespace(
        repository_root=repository_root,
        private_reveal_attestation_bytes=(
            private_reveal_attestation_bytes
        ),
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
    )
    closure = load_observer_batch_journal_closure_bytes_v2(
        raw=batch_closure_bytes,
        authority_binding=binding,
        known_stream_identities=known_stream_identities,
    )
    verification = verify_loaded_private_observer_batch_closure_v2(
        closure=closure,
        authority=authority,
        namespace=namespace,
        authority_binding=binding,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    return closure, verification


def verify_private_observer_batch_journal_closure_v2(
    *,
    repository_root: str | Path,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    batch_closure_bytes: bytes,
    known_stream_identities: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075ObserverBatchClosureVerificationV2:
    """Compatibility wrapper over the canonical production replay API."""

    _, verification = (
        replay_and_verify_private_observer_batch_journal_closure_v2(
            repository_root=repository_root,
            private_reveal_attestation_bytes=(
                private_reveal_attestation_bytes
            ),
            claimed_authorization_bytes=claimed_authorization_bytes,
            namespace_bytes=namespace_bytes,
            batch_closure_bytes=batch_closure_bytes,
            known_stream_identities=known_stream_identities,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    return verification


__all__ = [
    "DOMAIN_TAGS",
    "EXACT_V2_AUTHORITY_REQUIRED",
    "MAX_BATCHES_PER_SESSION",
    "MAX_CANONICAL_CLOSURE_BYTES",
    "MAX_OBSERVER_OPEN_BINDING_BYTES",
    "PROFILE_KEY",
    "PRODUCTION_ENVIRONMENT_INCLUDED",
    "PRODUCTION_PRIVATE_SIGNER_INCLUDED",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V1_AUTHORITY_PROJECTION_ALLOWED",
    "V1_NAMESPACE_PROJECTION_ALLOWED",
    "V075BatchOpenEligibilityV2",
    "V075BatchObservationRequestV2",
    "V075BatchOutcomeAggregateV2",
    "V075ObservationCapabilityV2",
    "V075ObserverBatchClosureVerificationV2",
    "V075ObserverBatchJournalClosureV2",
    "V075ObserverBatchJournalEntryV2",
    "V075ObserverClosureVerificationV2",
    "V075ObserverEvidenceSignerProtocolV2",
    "V075ObserverJournalClosureV2",
    "V075ObserverJournalEntryV2",
    "V075ObserverOpenAuthorityBindingV2",
    "V075PrivateObserverBoundaryV2InvariantViolation",
    "V075PrivateObserverSessionV2",
    "V075SignedObservationBatchV2",
    "V075SignedObservationRecordV2",
    "batch_observation_signing_bytes_v2",
    "load_observer_batch_journal_closure_bytes_v2",
    "observation_record_signing_bytes_v2",
    "observer_batch_journal_closure_signing_bytes_v2",
    "observer_journal_closure_signing_bytes_v2",
    "open_private_observer_v2",
    "replay_signed_observation_batch_object_v2",
    "replay_v075_observer_open_authority_binding_bytes_v2",
    "replay_and_verify_private_observer_batch_journal_closure_v2",
    "verify_loaded_private_observer_batch_closure_v2",
    "verify_private_observer_batch_journal_closure_v2",
    "verify_private_observer_journal_closure_v2",
]
