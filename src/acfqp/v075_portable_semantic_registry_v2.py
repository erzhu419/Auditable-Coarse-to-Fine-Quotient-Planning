"""Independent semantic-registry foundation for portable V0-075 evidence.

The portable bundle is a transport and topology authority, not its own
semantic authority.  This module therefore duplicates the normative
role/schema/identity/domain/shape table as an independent, content-addressed
declaration and cross-checks that declaration against the transport surface.

Every record receives a typed attestation after independent canonical-shape,
record-ID, and role-specific semantic-content-ID replay.  The two
self-contained roles are also fully replayed.  The other roles still require
dependency-aware reconstruction through their typed semantic verifiers, so
the aggregate completeness bit remains unconditionally false.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_production_semantic_authority_registry_v2 as surface


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.63.0"
PROFILE_KEY = "v075_portable_semantic_registry_v2"
PORTABLE_BUNDLE_PROFILE_KEY = "v075_portable_occurrence_evidence_bundle_v2"
SOURCE_MANIFEST_PROFILE_KEY = "v075_public_replay_occurrence_ipc_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
SEMANTIC_REGISTRY_REPLAY_COMPLETE = False

TERMINAL_SCOPE = "CONSTRUCTION_SEMANTIC_REGISTRY_FOUNDATION_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "PORTABLE_ARTIFACT_SEMANTIC_REPLAY_FOUNDATION_INCOMPLETE"
PRODUCTION_BLOCKER = (
    "all portable roles have independent canonical-shape and content-ID "
    "replay, but dependency-aware typed-object semantic replay remains "
    "incomplete for 65 non-self-contained roles"
)

DOMAIN_TAGS = MappingProxyType(
    {
        "declaration": (
            "acfqp:v075-portable-semantic-role-declaration:v2"
        ),
        "registry": "acfqp:v075-portable-semantic-registry:v2",
        "attestation": (
            "acfqp:v075-portable-record-semantic-attestation:v2"
        ),
        "attestation_set": (
            "acfqp:v075-portable-semantic-attestation-set:v2"
        ),
    }
)

_PORTABLE_RECORD_SCHEMA = (
    "acfqp.v075_portable_evidence_artifact_record.v2"
)
_PORTABLE_RECORD_SCHEMA_VERSION = "2.0.0"
_PORTABLE_RECORD_DOMAIN_BASE = (
    "acfqp:v075-portable-occurrence-evidence-record:v2"
)
_EXPECTED_ROLE_COUNT = 67


class V075PortableSemanticRegistryV2InvariantViolation(ValueError):
    """An independent declaration, record, or attestation was invalid."""


class V075PortableSemanticRegistryProductionV2NotReady(RuntimeError):
    """The incomplete registry foundation cannot authorize production."""


class V075PortableSemanticReplayStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


def _fail(message: str) -> NoReturn:
    raise V075PortableSemanticRegistryV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortableSemanticRegistryV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash_domain(domain: str, payload: Mapping[str, Any]) -> str:
    if type(domain) is not str or not domain.startswith("acfqp:"):
        _fail("semantic registry content domain is malformed")
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075PortableSemanticRegistryV2InvariantViolation(
            str(error)
        ) from error


def _hash_raw_domain(domain: str, raw: bytes) -> str:
    if (
        type(domain) is not str
        or not domain.startswith("acfqp:")
        or type(raw) is not bytes
        or not raw
    ):
        _fail("raw semantic content hash input is malformed")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + raw
    ).hexdigest()


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
    except KeyError as error:  # pragma: no cover - programming invariant
        raise RuntimeError("unknown semantic registry hash role") from error
    return _hash_domain(domain, payload)


def _strict_document(
    raw: bytes,
    *,
    label: str,
    byte_cap: int = 64 * 1024 * 1024,
) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or type(byte_cap) is not int
        or byte_cap <= 0
        or len(raw) > byte_cap
    ):
        _fail(f"{label} is empty, mistyped, or over its byte cap")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail(f"{label} contains a duplicate JSON key")
            result[key] = value
        return result

    try:
        document = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=unique_pairs,
            parse_constant=lambda value: _fail(
                f"{label} contains forbidden numeric constant {value}"
            ),
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as error:
        if type(error) is V075PortableSemanticRegistryV2InvariantViolation:
            raise
        raise V075PortableSemanticRegistryV2InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


def _document_keyset_sha256(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(sorted(document))
    ).hexdigest()


_PRIVATE_SERIALIZATION_FLAGS = frozenset(
    {
        "private_material_serialized",
        "private_law_serialized",
        "private_salt_serialized",
        "private_kernel_serialized",
        "individual_random_words_retained",
        "individual_random_words_serialized",
    }
)
_FORBIDDEN_TRUE_CLAIM_KEYS = frozenset(
    {
        "fresh_heldout_accessed",
        "infeasibility_certificate",
        "official_execution_allowed",
        "official_execution_unlocked",
        "plan_certificate",
        "production_authorizing",
        "production_positive_path_ready",
        "scientific_endpoint_credit_allowed",
        "semantic_registry_replay_complete",
    }
)
_FORBIDDEN_PRIVATE_PAYLOAD_KEYS = frozenset(
    {
        "individual_random_words",
        "private_environment",
        "private_kernel",
        "private_law",
        "private_salt",
    }
)


def _assert_public_document(value: Any) -> None:
    if type(value) is list:
        for item in value:
            _assert_public_document(item)
        return
    if type(value) is not dict:
        return
    for key, item in value.items():
        if key in _FORBIDDEN_TRUE_CLAIM_KEYS and item is not False:
            _fail("semantic replay input attempts to unlock a forbidden claim")
        if key in _PRIVATE_SERIALIZATION_FLAGS and item is not False:
            _fail("semantic replay input attempts to serialize private material")
        if key in _FORBIDDEN_PRIVATE_PAYLOAD_KEYS:
            _fail("semantic replay input contains undeclared private material")
        _assert_public_document(item)


@dataclass(frozen=True, slots=True)
class V075PortableSemanticRoleDeclarationV2:
    """Independent declaration for exactly one portable artifact role."""

    ordinal: int
    role: str
    artifact_schema: str
    record_identity_field: str | None
    embedded_content_id_field: str | None
    record_domain_tag: str
    semantic_hash_domain_tag: str
    excluded_content_id_fields: tuple[str, ...]
    included_content_id_fields: tuple[str, ...]
    payload_schema_override: str | None
    document_keyset_sha256: str
    semantic_hash_authority_module: str
    semantic_verifier_authority: str
    semantic_replay_status: V075PortableSemanticReplayStatusV2
    _declaration_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.document_keyset_sha256, "role document shape"),
        ):
            _cid(value, label)
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.role) is not str
            or not self.role
            or self.role != self.role.upper()
            or type(self.artifact_schema) is not str
            or not self.artifact_schema.startswith("acfqp.")
            or self.record_identity_field is not None
            and (
                type(self.record_identity_field) is not str
                or not self.record_identity_field.isidentifier()
            )
            or self.embedded_content_id_field is not None
            and (
                type(self.embedded_content_id_field) is not str
                or not self.embedded_content_id_field.isidentifier()
            )
            or self.record_domain_tag
            != f"{_PORTABLE_RECORD_DOMAIN_BASE}:{self.role.lower()}"
            or type(self.semantic_hash_domain_tag) is not str
            or not self.semantic_hash_domain_tag.startswith("acfqp:")
            or type(self.excluded_content_id_fields) is not tuple
            or tuple(sorted(set(self.excluded_content_id_fields)))
            != self.excluded_content_id_fields
            or type(self.included_content_id_fields) is not tuple
            or len(set(self.included_content_id_fields))
            != len(self.included_content_id_fields)
            or (
                self.excluded_content_id_fields
                and self.included_content_id_fields
            )
            or self.payload_schema_override is not None
            and (
                type(self.payload_schema_override) is not str
                or not self.payload_schema_override.startswith("acfqp.")
            )
            or type(self.semantic_hash_authority_module) is not str
            or not self.semantic_hash_authority_module.startswith("acfqp.")
            or type(self.semantic_verifier_authority) is not str
            or self.semantic_verifier_authority
            != (
                f"{PROFILE_KEY}:ROLE_DISPATCH:{self.role}:"
                + (
                    "SELF_CONTAINED_SEMANTIC_REPLAY"
                    if self.role
                    in {"OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME"}
                    else "HASH_AND_SHAPE_ONLY"
                )
            )
            or type(self.semantic_replay_status)
            is not V075PortableSemanticReplayStatusV2
            or (
                self.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
            )
            != (self.role in {"OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME"})
            or (
                self.record_identity_field is not None
                and self.embedded_content_id_field
                != self.record_identity_field
            )
            or (
                self.record_identity_field is None
                and self.role != "SIGNED_BATCH_OUTCOME"
                and self.embedded_content_id_field is not None
            )
        ):
            _fail("portable semantic role declaration is malformed")
        object.__setattr__(
            self,
            "_declaration_id",
            _hash("declaration", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_semantic_role_declaration.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ordinal": self.ordinal,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "record_identity_field": (
                self.record_identity_field
                if self.record_identity_field is not None
                else {
                    "kind": "DERIVED_FROM_ROLE_AND_CANONICAL_BYTES",
                    "reason": "PORTABLE_ROLE_HAS_NO_PRIMARY_OBJECT_ID",
                }
            ),
            "embedded_content_id_field": (
                self.embedded_content_id_field
                if self.embedded_content_id_field is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "NO_EMBEDDED_CONTENT_ID",
                }
            ),
            "record_domain_tag": self.record_domain_tag,
            "semantic_hash_domain_tag": self.semantic_hash_domain_tag,
            "excluded_content_id_fields": list(
                self.excluded_content_id_fields
            ),
            "included_content_id_fields": list(
                self.included_content_id_fields
            ),
            "payload_schema_override": (
                self.payload_schema_override
                if self.payload_schema_override is not None
                else {"kind": "NOT_APPLICABLE"}
            ),
            "document_keyset_sha256": self.document_keyset_sha256,
            "semantic_hash_authority_module": (
                self.semantic_hash_authority_module
            ),
            "semantic_verifier_module": (
                "acfqp.v075_portable_semantic_registry_v2"
            ),
            "semantic_verifier_function": (
                "attest_v075_portable_evidence_record_document_v2"
            ),
            "semantic_verifier_authority": (
                self.semantic_verifier_authority
            ),
            "semantic_verifier_scope": (
                "CANONICAL_SHAPE_RECORD_ID_AND_CONTENT_ID_ONLY"
            ),
            "semantic_replay_status": (
                self.semantic_replay_status.value
            ),
            "independent_role_semantics_complete": (
                self.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
            ),
            "producer_typed_object_reconstructed": False,
            "dependency_aware_typed_object_replay_complete": False,
            "typed_object_reconstruction_required": (
                self.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.INCOMPLETE
            ),
            "producer_claim_is_semantic_evidence": False,
            "portable_bundle_registry_is_semantic_evidence": False,
            "official_execution_allowed": False,
        }

    @property
    def declaration_id(self) -> str:
        return self._declaration_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "declaration_id": self.declaration_id}


def _declaration(
    ordinal: int,
    role: str,
    artifact_schema: str,
    record_identity_field: str,
    embedded_content_id_field: str,
    semantic_hash_domain_tag: str,
    excluded_fields: str,
    included_fields: str,
    payload_schema_override: str,
    document_keyset_sha256: str,
    semantic_hash_authority_module: str,
) -> V075PortableSemanticRoleDeclarationV2:
    return V075PortableSemanticRoleDeclarationV2(
        ordinal,
        role,
        artifact_schema,
        record_identity_field or None,
        embedded_content_id_field or None,
        f"{_PORTABLE_RECORD_DOMAIN_BASE}:{role.lower()}",
        semantic_hash_domain_tag,
        tuple(sorted(filter(None, excluded_fields.split(",")))),
        tuple(filter(None, included_fields.split(","))),
        payload_schema_override or None,
        document_keyset_sha256,
        semantic_hash_authority_module,
        (
            f"{PROFILE_KEY}:ROLE_DISPATCH:{role}:"
            + (
                "SELF_CONTAINED_SEMANTIC_REPLAY"
                if role in {"OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME"}
                else "HASH_AND_SHAPE_ONLY"
            )
        ),
        (
            V075PortableSemanticReplayStatusV2.COMPLETE
            if role in {"OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME"}
            else V075PortableSemanticReplayStatusV2.INCOMPLETE
        ),
    )


# This table is intentionally independent literal data.  It is not derived
# from portable.ROLE_SCHEMA_REGISTRY or any private bundle registry at runtime.
# Columns:
# role, schema, record-ID field, embedded-ID field, semantic domain,
# excluded fields, included fields, payload schema override, shape digest,
# original semantic hash authority module.
_DECLARATION_ROWS_TEXT = """\
BATCH_PUBLIC_VERIFICATION	acfqp.v075_batch_public_verification.v2	verification_id	verification_id	acfqp:v075-batch-public-verification:v2				0a5826971732384c247355608fd15cfc4bec9afc1518a9b77e1df91ab301cc4d	acfqp.v075_batched_observer_authority_v2
BATCH_SEQUENCE_VERIFICATION	acfqp.v075_batch_sequence_verification.v2	verification_id	verification_id	acfqp:v075-batch-sequence-verification:v2				ee3028311ab34e5c6e483106adb6c285aff5b0b330fbaf198a789c7a2a52a76b	acfqp.v075_batched_observer_authority_v2
CLOSED_RECONCILIATION	acfqp.v075_observer_signed_closed_reconciliation.v2	reconciliation_id	reconciliation_id	acfqp:v075-observer-signed-closed-reconciliation:v2				3ef39d75dade16da64151fac08e595dfa54eebaafd0992779cddf5a442812914	acfqp.v075_observer_signed_multiround_occurrence_runner_v2
CONSTRUCTION_LIFECYCLE	acfqp.v075_batch_occurrence_lifecycle.v2	closure_id	closure_id	acfqp:v075-construction-batch-occurrence-lifecycle:v2	events,support_evidence,support_freezes			6238104a7a22f22b26fd7b65badf0d40b5a23090acdd87fec1938b1790226710	acfqp.v075_batch_occurrence_lifecycle_authority_v2
CONSTRUCTION_LIFECYCLE_VERIFICATION	acfqp.v075_batch_occurrence_lifecycle_verification.v2	verification_id	verification_id	acfqp:v075-construction-batch-occurrence-lifecycle-verification:v2				9b2e43c943973f5f999bb0e9d68f97f54f6491d04a485b13f62836ddde20b05f	acfqp.v075_batch_occurrence_lifecycle_authority_v2
CONSTRUCTION_LINEAGE	acfqp.v075_batch_occurrence_lineage.v2	lineage_id	lineage_id	acfqp:v075-batch-occurrence-lineage:v2				f846f508c4e61678e873d8ce6de326cc7079b27cdc472ce9032f3864cc8d2b2c	acfqp.v075_batched_observer_authority_v2
CONSTRUCTION_PLANNING_INPUT	acfqp.v075_batch_planning_construction_input.v2	input_id	input_id	acfqp:v075-batch-planning-construction-input:v2	evidence_bindings,model			2368014978ef73122250c1680dc33379280e0b2647b17955bd9f0234d9908006	acfqp.v075_batch_native_planning_backend_v2
CONTROLLED_CHILD_APPEND	acfqp.v075_controlled_batch_append.v2			acfqp:v075-portable-occurrence-evidence-derived-artifact:v2:controlled_child_append				bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed	acfqp.v075_portable_occurrence_evidence_bundle_v2
CONTROLLED_CHILD_INTENT	acfqp.v075_head_bound_exact_batch_intent.v2	intent_id	intent_id	acfqp:v075-head-bound-exact-batch-intent:v2	semantic_authority,stream_identity			59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_CHILD_SEMANTIC_AUTHORITY	acfqp.v075_controlled_batch_semantic_authority_binding.v2	binding_id	binding_id	acfqp:v075-controlled-batch-semantic-authority-binding:v2				ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_COMPLETE_SUPPORT_FREEZE	acfqp.v075_controlled_complete_support_freeze.v2	freeze_id	freeze_id	acfqp:v075-controlled-complete-support-freeze:v2	evidence			b0854575e4891aec158f61f68d4b60d379ee875996d46eaa8ea303e838e26ca2	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_JOURNAL_CLOSURE	acfqp.v075_controlled_batch_journal_closure.v2			acfqp:v075-portable-occurrence-evidence-derived-artifact:v2:controlled_journal_closure				24b098e3afc6ffc24e33f386a5fdabc5a830e75191ca9e877dbb9d15cee0adc5	acfqp.v075_portable_occurrence_evidence_bundle_v2
CONTROLLED_PROMOTION_APPEND	acfqp.v075_controlled_batch_append.v2			acfqp:v075-portable-occurrence-evidence-derived-artifact:v2:controlled_promotion_append				bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed	acfqp.v075_portable_occurrence_evidence_bundle_v2
CONTROLLED_PROMOTION_INTENT	acfqp.v075_head_bound_exact_batch_intent.v2	intent_id	intent_id	acfqp:v075-head-bound-exact-batch-intent:v2	semantic_authority,stream_identity			59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY	acfqp.v075_controlled_batch_semantic_authority_binding.v2	binding_id	binding_id	acfqp:v075-controlled-batch-semantic-authority-binding:v2				ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_ROOT_APPEND	acfqp.v075_controlled_batch_append.v2			acfqp:v075-portable-occurrence-evidence-derived-artifact:v2:controlled_root_append				bee467214b56feb9a8f2bf7abcb3be69d627c420abf676e7afe20784e2fb5fed	acfqp.v075_portable_occurrence_evidence_bundle_v2
CONTROLLED_ROOT_INTENT	acfqp.v075_head_bound_exact_batch_intent.v2	intent_id	intent_id	acfqp:v075-head-bound-exact-batch-intent:v2	semantic_authority,stream_identity			59f6929124cd2d281ccdebd691d18290559e18a33f73078f8cc18d0dabe1bf48	acfqp.v075_observer_signed_batch_control_authority_v2
CONTROLLED_ROOT_SEMANTIC_AUTHORITY	acfqp.v075_controlled_batch_semantic_authority_binding.v2	binding_id	binding_id	acfqp:v075-controlled-batch-semantic-authority-binding:v2				ca2afab5e59f39da1d0e6c6b6bf1cfd76e09d0107fc5ff55a712a0661d1db11b	acfqp.v075_observer_signed_batch_control_authority_v2
DYNAMIC_CHILD_CAUSAL_EDGE	acfqp.v075_live_dynamic_child_causal_edge.v2	edge_id	edge_id	acfqp:v075-live-dynamic-child-causal-edge:v2				72022868a2e93cef8752c37331f0cffd20e5d9343515f4193e0853422945fc8e	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_CLOSURE	acfqp.v075_live_dynamic_child_closure.v2	closure_id	closure_id	acfqp:v075-live-dynamic-child-closure:v2	child_states,discovery_intents,validation_templates			f88b173f0d278cc7bedce1e2dfcf22a7f5c9bf76bb89c158621e7692873cbe74	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_CLOSURE_VERIFICATION	acfqp.v075_live_dynamic_child_closure_verification.v2	verification_id	verification_id	acfqp:v075-live-dynamic-child-closure-verification:v2				e36453b946f5bf7e12e743f35597a4de353ced096f948436350a043bcee93206	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_DISCOVERY_INTENT	acfqp.v075_live_dynamic_child_acquisition_intent.v2	intent_id	intent_id	acfqp:v075-live-dynamic-child-discovery-intent:v2	row_binding,stream_identity			130d1ff882eb5bc6bd02d11cb2297f7d5d51821049291b177e9af47a8995b781	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_EXECUTED_ROW	acfqp.v075_live_dynamic_child_executed_row.v2	executed_row_id	executed_row_id	acfqp:v075-live-dynamic-child-executed-row:v2				24edad4174e5cf0721c8c248a974ed942582ddee54925ce4d0ed435b30e6b339	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_EXECUTION_LEDGER	acfqp.v075_live_dynamic_child_execution_ledger.v2	ledger_id	ledger_id	acfqp:v075-live-dynamic-child-execution-ledger:v2	executed_rows			e1b369775ac6f07037e92c309547c5646a7eed51de339e4ced7366ac78a85378	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_EXECUTION_VERIFICATION	acfqp.v075_live_dynamic_child_execution_verification.v2	verification_id	verification_id	acfqp:v075-live-dynamic-child-execution-verification:v2				18f6449f9d66c8af41e2ddfe19068397e568a1c1d51a5f1d74e04c5597853cac	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_REPLANNING_BARRIER	acfqp.v075_live_dynamic_child_replanning_barrier.v2	barrier_id	barrier_id	acfqp:v075-live-dynamic-child-replanning-barrier:v2				c0ba8f4e207404b491a41761b8257d9908a170bd6f78bacbe8b38d7a123824a7	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_REPLANNING_BARRIER_VERIFICATION	acfqp.v075_live_dynamic_child_replanning_barrier_verification.v2	verification_id	verification_id	acfqp:v075-live-dynamic-child-replanning-barrier-verification:v2				ef34a95159ed460f4219cb9e9a9b5e07560b89ec017a383d10d4fa0eea46e750	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_STATE	acfqp.v075_live_dynamic_child_state.v2	child_binding_id	child_binding_id	acfqp:v075-live-dynamic-child-state:v2	catalogue,causal_edges,row_bindings,state			5191afe6d77833a76b25ea24559a18fdd124f817f6d1bb149f00901ebf3bc6d3	acfqp.v075_live_dynamic_acquisition_authority_v2
DYNAMIC_CHILD_VALIDATION_TEMPLATE	acfqp.v075_live_dynamic_child_validation_intent_template.v2	template_id	template_id	acfqp:v075-live-dynamic-child-validation-template:v2				362493446c8d6aa58e4e78d2ecb80962745c38a6e3f706fc0a05470158995776	acfqp.v075_live_dynamic_acquisition_authority_v2
INITIAL_ACQUISITION_SCHEDULE	acfqp.v075_five_arm_initial_acquisition_schedule.v2	schedule_id	schedule_id	acfqp:v075-five-arm-initial-acquisition-schedule:v2	intents,occurrence,profile,proposal_view			3acadf984d8643be09d03f0963555888edb398fc1a424bb618eb8a7cb448c9f8	acfqp.v075_five_arm_acquisition_authority_v2
INITIAL_ACQUISITION_VERIFICATION	acfqp.v075_five_arm_initial_acquisition_verification.v2	verification_id	verification_id	acfqp:v075-five-arm-initial-acquisition-verification:v2				bc38b03b410ccb74c72aef0f0bb1bba0de670acc018054fc9f964f761a408eab	acfqp.v075_five_arm_acquisition_authority_v2
INITIAL_ROW_INTENT	acfqp.v075_five_arm_initial_row_intent.v2	intent_id	intent_id	acfqp:v075-five-arm-initial-row-intent:v2	row_binding			12b81c697ef7e5f3558bd1cc01ad1798498d97ab693ae0830e9c9b0a8ce5317e	acfqp.v075_five_arm_acquisition_authority_v2
LEGAL_ACTION_CATALOGUE	acfqp.v075_heldout_legal_action_catalogue.v2	catalogue_id	catalogue_id	acfqp:v075-heldout-legal-action-catalogue:v2	context,state			142ebf97d626e456f7d5ad10d225b3066ea6ccaad13308846f7a849b7a997586	acfqp.v075_public_graph_semantics_v1
LIFECYCLE_EVENT	acfqp.v075_batch_lifecycle_event.v2	event_id	event_id	acfqp:v075-batch-lifecycle-event:v2				0c32870baa0ea35e14a5c264b918214873ed8f4791f9a30385526df78a56800e	acfqp.v075_batch_occurrence_lifecycle_authority_v2
LIFECYCLE_SUPPORT_EVIDENCE	acfqp.v075_batch_support_evidence.v2	evidence_id	evidence_id	acfqp:v075-batch-support-evidence:v2				979ed93808266670561c0a0bf14a3885c88d916ba8fe22540d4a4bcdd010b0a0	acfqp.v075_batch_occurrence_lifecycle_authority_v2
LIFECYCLE_SUPPORT_FREEZE	acfqp.v075_batch_support_freeze.v2	freeze_id	freeze_id	acfqp:v075-batch-support-freeze:v2				64193324c9ebe7182ce84d09ae65ee541e389ca783e1a03f53ad66cd3cb0a5c1	acfqp.v075_batch_occurrence_lifecycle_authority_v2
LIVE_MODEL_EPOCH	acfqp.v075_live_incremental_model_epoch.v2	model_epoch_id	model_epoch_id	acfqp:v075-live-incremental-model-epoch:v2	model,proof,row_sources			c90de81d540737f1970933dfdc8c1343c7e8173326ba385943c54be186ed9fcb	acfqp.v075_live_incremental_model_authority_v2
LIVE_PROMOTION_DECISION	acfqp.v075_live_promotion_decision.v2	decision_id	decision_id	acfqp:v075-live-promotion-decision:v2	intent			d94a7808c2ff70336a199f20fa4fcd722cb3969de785298135f3548b3844fd66	acfqp.v075_live_dynamic_acquisition_authority_v2
LIVE_PROMOTION_DECISION_VERIFICATION	acfqp.v075_live_promotion_decision_verification.v2	verification_id	verification_id	acfqp:v075-live-promotion-decision-verification:v2				acebe246876ba5a4cba950181af0820816aaaa96964483ba3bf43d055c41e42d	acfqp.v075_live_dynamic_acquisition_authority_v2
LIVE_PROMOTION_INTENT	acfqp.v075_live_promotion_authorization.v2	intent_id	intent_id	acfqp:v075-live-promotion-intent:v2	stream_identity			65c696da7f141d685606ffbda2f0dc83e87bf6840a33d55699d09067d2a0d1f5	acfqp.v075_live_dynamic_acquisition_authority_v2
LIVE_PROMOTION_REPLANNING_BARRIER	acfqp.v075_live_promotion_replanning_barrier.v2	barrier_id	barrier_id	acfqp:v075-live-promotion-replanning-barrier:v2				77e214c297c4425f847ef117b563679d810b68cf1838ebba01011946f8ad3edf	acfqp.v075_live_dynamic_acquisition_authority_v2
LIVE_PROMOTION_REPLANNING_BARRIER_VERIFICATION	acfqp.v075_live_promotion_replanning_barrier_verification.v2	verification_id	verification_id	acfqp:v075-live-promotion-replanning-barrier-verification:v2				bce30b827ffab841e14bfdc6f6d22e6f44b38979627a474adac599dbf135bd29	acfqp.v075_live_dynamic_acquisition_authority_v2
LIVE_ROW_SOURCE_BINDING	acfqp.v075_live_model_row_source_binding.v2	binding_id	binding_id	acfqp:v075-live-incremental-row-source-binding:v2				f9d8a13b5a09f8f17edc66f16dfaf3b1ac46b75236e497f96771b5669c99034e	acfqp.v075_live_incremental_model_authority_v2
MULTIROUND_RESULT	acfqp.v075_observer_signed_multiround_occurrence_result.v2	result_id	result_id	acfqp:v075-observer-signed-multiround-result:v2				683335e0a1d9f43929977f1414c8ded0498be206bf22d68aaf72ccc215d59a4a	acfqp.v075_observer_signed_multiround_occurrence_runner_v2
NUMERICAL_MODEL	acfqp.v075_batch_planning_numerical_model.v2	model_id	model_id	acfqp:v075-batch-planning-numerical-model:v2	rows			226bbde8194d0ed8a04566f6045f543f238a650265ffc621dab351ad0ce97dcc	acfqp.v075_batch_native_planning_backend_v2
NUMERICAL_PLANNING_PROOF	acfqp.v075_batch_planning_numerical_proof.v2	proof_id	proof_id	acfqp:v075-batch-planning-numerical-proof:v2	envelope,failed_frontier,model,policy,quotient			ebdb2100a89a798bd1487a0fd89f29d0d4b8f4a893b7c562d3da353998630883	acfqp.v075_batch_native_planning_backend_v2
OBSERVATION_ROW_BINDING	acfqp.v075_heldout_observation_row_binding.v2	row_binding_id	row_binding_id	acfqp:v075-heldout-observation-row-binding:v2	catalogue,context			93cf8898f8b771603a92f19e2bf82c8cf511b97378076c7b36f11287662b94ac	acfqp.v075_public_graph_semantics_v1
OBSERVER_OPEN_BINDING	acfqp.v075_observer_open_authority_binding.v2	binding_id	binding_id	acfqp:v075-observer-open-authority-binding:v2				3e826ca19f92c25fb174f8192a8184d7ba785176a3a2e1954f7f4592aedacacc	acfqp.v075_private_observer_boundary_v2
OBSERVER_SIGNED_SUPPORT_EVIDENCE	acfqp.v075_batch_aggregate_support_evidence.v1	evidence_id	evidence_id	acfqp:v075-batch-aggregate-support-evidence:v1	namespace,observed_state,row_binding			3618c51e42eed7b3275a64638b61949bbcd71749372c03e422592779e9c8e8be	acfqp.v075_public_graph_semantics_v1
OCCURRENCE_IDENTITY	acfqp.v075_batch_native_occurrence.v1	occurrence_id	occurrence_id	acfqp:v075-batch-native-occurrence:v1	batch_count_at_freeze,frozen_before_observation,kernel_calls,observer_calls,private_material_serialized,target_accessed			b479e54ee0fa1c6fbb4a201667e44dc11651debd8317b372cc8d4226cc9e45d9	acfqp.v075_batch_native_statistical_backend_v1
OPEN_CONTROLLED_PREFIX_VERIFICATION	acfqp.v075_open_controlled_batch_prefix_verification.v2	verification_id	verification_id	acfqp:v075-open-controlled-batch-prefix-verification:v2				924c7111089d908fa9be43e14b319bda97fdf9075ecd553a55ca8942158ff1f1	acfqp.v075_observer_signed_batch_control_authority_v2
PAIRING_AUTHORITY	acfqp.v075_five_arm_pairing_authority.v2	pairing_authority_id	pairing_authority_id	acfqp:v075-five-arm-pairing-authority:v2	namespace,row_binding,support_chain			6af86000963c6a3c9a972d330d0705eb6a88aca23bf7c542c741e0fda72b104d	acfqp.v075_public_graph_semantics_v1
ROOT_EXECUTION	acfqp.v075_observer_signed_root_execution.v2	execution_id	execution_id	acfqp:v075-observer-signed-root-execution:v2				27a139af71444adf1cf041009058576966f98b60acb8aab9dd4e2813c9c08ddb	acfqp.v075_observer_signed_multiround_occurrence_runner_v2
SHARED_SUPPORT_CHAIN	acfqp.v075_heldout_shared_support_chain.v2	chain_id	chain_id	acfqp:v075-heldout-shared-support-chain:v2	epochs,namespace,row_binding			2640693b5fe8581cf20ad4ba03ceedcbc8663510523914e250ecf508c1217880	acfqp.v075_public_graph_semantics_v1
SHARED_SUPPORT_EPOCH	acfqp.v075_heldout_shared_support_epoch.v2	epoch_id	epoch_id	acfqp:v075-heldout-shared-support-epoch:v2	evidence,namespace,row_binding			63d5a098c299b9c8f56d480c23af5faebd8cb00cd3fd2752c725a3fed677952e	acfqp.v075_public_graph_semantics_v1
SIGNED_APPEND_RECEIPT	acfqp.v075_observer_signed_batch_append_receipt.v2	receipt_id	receipt_id	acfqp:v075-observer-signed-batch-append-receipt:v2	observer_open_binding			ed3f44d0db87f7377e2b997b0d90bfd2efab91f23232c9b7043df24097eadd49	acfqp.v075_observer_signed_batch_control_authority_v2
SIGNED_BATCH_JOURNAL_CLOSURE	acfqp.v075_observer_batch_journal_closure.v2	closure_id	closure_id	acfqp:v075-observer-batch-journal-closure:v2	entries,observer_open_binding			8691cc9c92bb15051182794a2c361a4c5239937e969860574ea1f3365b8ff7ca	acfqp.v075_private_observer_boundary_v2
SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION	acfqp.v075_observer_batch_journal_closure_verification.v2	verification_id	verification_id	acfqp:v075-observer-batch-journal-closure-verification:v2				fcab01511420f0c9c7f65877693983864670bd1d109086c940abb32ea282f523	acfqp.v075_private_observer_boundary_v2
SIGNED_BATCH_JOURNAL_ENTRY	acfqp.v075_observer_batch_journal_entry.v2	entry_id	entry_id	acfqp:v075-observer-batch-journal-entry:v2	batch			f5bc843572903d6f6db2feb44faeb84a8d48334a0f5cdeaacf178c289e06caec	acfqp.v075_private_observer_boundary_v2
SIGNED_BATCH_OUTCOME	acfqp.v075_batch_outcome_aggregate.v2		outcome_id	acfqp:v075-batch-outcome-aggregate:v2		schema,schema_version,next_ranks,failure,terminal,spawn_cell,spawn_rank,realized_row_reward		a332e47b6bbfc96964f330451bddf9e731858f8e5729ce4a9e4686fe93601d09	acfqp.v075_private_observer_boundary_v2
SIGNED_BATCH_REQUEST	acfqp.v075_batch_observation_request.v2	request_id	request_id	acfqp:v075-batch-observation-request:v2				8438d9aec51db1865c0f5c9d6ec47150c21c3dcbda652e75824419cb75ff55e0	acfqp.v075_private_observer_boundary_v2
SIGNED_CONTROL_CLOSURE	acfqp.v075_observer_signed_batch_control_closure.v2	control_closure_id	control_closure_id	acfqp:v075-observer-signed-batch-control-closure:v2	observer_open_binding			bf5ebae9a8f5c220d05be899170f156e84c2454a66f60ca2a164349a2edb0e37	acfqp.v075_observer_signed_batch_control_authority_v2
SIGNED_CONTROL_JOURNAL_HEAD	acfqp.v075_observer_signed_batch_journal_head.v2	head_id	head_id	acfqp:v075-observer-signed-batch-journal-head:v2	observer_open_binding			b67ee987cbad8d10b07ba40b75ae478928a5b180bbbe2244d409dd88e5000d8e	acfqp.v075_observer_signed_batch_control_authority_v2
SIGNED_CONTROL_RECONCILIATION	acfqp.v075_observer_signed_batch_control_reconciliation.v2	reconciliation_id	reconciliation_id	acfqp:v075-observer-signed-batch-control-reconciliation:v2				a629e7c42c77f76bb221a1ed2bd89ebd5f0f8512b41f11f9ba9fd6367926628b	acfqp.v075_observer_signed_batch_control_authority_v2
SIGNED_OBSERVATION_BATCH	acfqp.v075_signed_observation_batch.v2	batch_id	batch_id	acfqp:v075-signed-observation-batch:v2	observer_open_binding,outcomes,request			f7409cd713f7ef8fb495341b393fc0c47bb46680cc090e53816bdb21324689c5	acfqp.v075_private_observer_boundary_v2
SYMBOLIC_GRAPH_STATE	acfqp.v075_heldout_symbolic_graph_state.v2	state_id	state_id	acfqp:v075-heldout-symbolic-graph-state:v2	context			f60b3b5cf9dfc4163b311820c933ad54c0c23501f8d30aa71aef6e05bf76e571	acfqp.v075_public_graph_semantics_v1
TRANSITION_STREAM	acfqp.v075_arm_isolated_stream_pair.v2	stream_id	stream_id	acfqp:v075-arm-isolated-transition-stream:v2		pair_id,arm,lane	acfqp.v075_arm_isolated_transition_stream.v2	7a0117ffda200b78170e8ca44c348d143f7395d35c0be404a34d313f4daaadd8	acfqp.v075_public_graph_semantics_v1
"""


def _canonical_declarations(
) -> tuple[V075PortableSemanticRoleDeclarationV2, ...]:
    rows = tuple(
        line.split("\t")
        for line in _DECLARATION_ROWS_TEXT.splitlines()
        if line
    )
    if (
        len(rows) != _EXPECTED_ROLE_COUNT
        or any(len(row) != 10 for row in rows)
        or tuple(row[0] for row in rows)
        != tuple(sorted(row[0] for row in rows))
        or len({row[0] for row in rows}) != len(rows)
    ):
        raise RuntimeError("independent portable role declaration table broke")
    return tuple(
        _declaration(index, *row) for index, row in enumerate(rows)
    )


_REGISTRY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSemanticRegistryV2:
    """Content-addressed exact independent role registry."""

    _issuer: InitVar[object]
    declarations: tuple[V075PortableSemanticRoleDeclarationV2, ...]
    static_surface_registry_id: str
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        _cid(
            self.static_surface_registry_id,
            "static implementation-surface registry",
        )
        if (
            _issuer is not _REGISTRY_ISSUER
            or type(self.declarations) is not tuple
            or len(self.declarations) != _EXPECTED_ROLE_COUNT
            or any(
                type(item) is not V075PortableSemanticRoleDeclarationV2
                for item in self.declarations
            )
            or tuple(item.ordinal for item in self.declarations)
            != tuple(range(len(self.declarations)))
            or tuple(item.role for item in self.declarations)
            != tuple(sorted(item.role for item in self.declarations))
            or len({item.role for item in self.declarations})
            != len(self.declarations)
            or len({item.declaration_id for item in self.declarations})
            != len(self.declarations)
        ):
            _fail("portable semantic registry is malformed")
        object.__setattr__(
            self,
            "_registry_id",
            _hash("registry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_semantic_registry.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_profile_key": PORTABLE_BUNDLE_PROFILE_KEY,
            "static_surface_registry_id": self.static_surface_registry_id,
            "static_surface_scope": "STATIC_IMPLEMENTATION_SURFACE_ONLY",
            "static_surface_used_as_artifact_semantic_evidence": False,
            "role_order": [item.role for item in self.declarations],
            "declaration_ids": [
                item.declaration_id for item in self.declarations
            ],
            "role_count": len(self.declarations),
            "complete_role_count": sum(
                item.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
                for item in self.declarations
            ),
            "incomplete_role_count": sum(
                item.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.INCOMPLETE
                for item in self.declarations
            ),
            "all_roles_independently_declared": True,
            "all_record_shapes_and_content_ids_replayable": True,
            "semantic_registry_replay_complete": False,
            "dependency_aware_typed_object_replay_complete": False,
            "producer_claim_is_semantic_evidence": False,
            "portable_bundle_claimed_registry_is_semantic_evidence": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def registry_id(self) -> str:
        return self._registry_id

    @property
    def by_role(
        self,
    ) -> Mapping[str, V075PortableSemanticRoleDeclarationV2]:
        return MappingProxyType(
            {item.role: item for item in self.declarations}
        )

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "declarations": [
                item.to_document() for item in self.declarations
            ],
            "registry_id": self.registry_id,
        }


def freeze_v075_portable_semantic_registry_v2(
) -> V075PortableSemanticRegistryV2:
    """Freeze independent declarations and cross-check both static surfaces."""

    declarations = _canonical_declarations()
    independent_role_schema = {
        item.role: item.artifact_schema for item in declarations
    }
    if independent_role_schema != dict(portable.ROLE_SCHEMA_REGISTRY):
        _fail(
            "portable transport role/schema surface differs from the "
            "independent semantic declaration"
        )
    static_registry = (
        surface.freeze_v075_production_semantic_authority_registry_v2()
    )
    if (
        surface.ARTIFACT_SEMANTIC_ATTESTATION_ALLOWED is not False
        or static_registry.to_document().get(
            "registered_verifier_scope"
        )
        != "STATIC_IMPLEMENTATION_SURFACE_ONLY"
        or static_registry.to_document().get(
            "role_specific_artifact_replay_still_required"
        )
        is not True
    ):
        _fail("static readiness registry attempts to attest artifact semantics")
    return V075PortableSemanticRegistryV2(
        _REGISTRY_ISSUER,
        declarations,
        static_registry.registry_id,
    )


def verify_v075_portable_semantic_registry_bytes_v2(
    raw: bytes,
) -> V075PortableSemanticRegistryV2:
    document = _strict_document(
        raw,
        label="portable semantic registry",
        byte_cap=4 * 1024 * 1024,
    )
    if (
        document.get("semantic_registry_replay_complete") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("production_authorizing") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("plan_certificate") is not False
        or document.get("infeasibility_certificate") is not False
    ):
        _fail("portable semantic registry attempts to claim completion")
    expected = freeze_v075_portable_semantic_registry_v2()
    if raw != expected.canonical_bytes:
        _fail(
            "portable semantic registry differs from independent declarations"
        )
    return expected


_SCHEMA_SHAPES: Mapping[str, frozenset[str]] | None = None


def _schema_shapes(
    registry: V075PortableSemanticRegistryV2,
) -> Mapping[str, frozenset[str]]:
    global _SCHEMA_SHAPES
    if _SCHEMA_SHAPES is None:
        mutable: dict[str, set[str]] = {}
        for item in registry.declarations:
            mutable.setdefault(item.artifact_schema, set()).add(
                item.document_keyset_sha256
            )
        _SCHEMA_SHAPES = MappingProxyType(
            {
                key: frozenset(value)
                for key, value in mutable.items()
            }
        )
    return _SCHEMA_SHAPES


def _assert_declared_shape(
    *,
    declaration: V075PortableSemanticRoleDeclarationV2,
    document: Mapping[str, Any],
    registry: V075PortableSemanticRegistryV2,
) -> None:
    if (
        document.get("schema") != declaration.artifact_schema
        or _document_keyset_sha256(document)
        != declaration.document_keyset_sha256
    ):
        _fail("portable record shape is missing, extended, or role-transplanted")

    allowed_by_schema = _schema_shapes(registry)

    def visit(value: Any, *, outermost: bool = False) -> None:
        if type(value) is list:
            for item in value:
                visit(item)
            return
        if type(value) is not dict:
            return
        if not outermost:
            allowed = allowed_by_schema.get(value.get("schema"))
            if (
                allowed is not None
                and _document_keyset_sha256(value) not in allowed
            ):
                _fail("embedded portable artifact has an undeclared shape")
        for item in value.values():
            visit(item)

    visit(document, outermost=True)


_CONTROL_KIND_BY_SEMANTIC_ROLE = MappingProxyType(
    {
        "INITIAL_SCHEDULE_ROW_INTENT": "ROOT",
        "DYNAMIC_CHILD_DISCOVERY_INTENT": "CHILD",
        "LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT": "CHILD",
        "LIVE_PROMOTION_AUTHORIZATION": "PROMOTION",
    }
)
_CONTROL_SCHEMA_BY_SEMANTIC_ROLE = MappingProxyType(
    {
        "INITIAL_SCHEDULE_ROW_INTENT": (
            "acfqp.v075_five_arm_initial_row_intent.v2"
        ),
        "DYNAMIC_CHILD_DISCOVERY_INTENT": (
            "acfqp.v075_dynamic_child_discovery_intent.v2"
        ),
        "LIVE_DYNAMIC_CHILD_ACQUISITION_INTENT": (
            "acfqp.v075_live_dynamic_child_acquisition_intent.v2"
        ),
        "LIVE_PROMOTION_AUTHORIZATION": (
            "acfqp.v075_live_promotion_authorization.v2"
        ),
    }
)


def _assert_dynamic_control_role(
    *,
    role: str,
    document: Mapping[str, Any],
    controlled_intent_semantic_roles: Mapping[str, str],
) -> None:
    if not role.startswith("CONTROLLED_"):
        return
    suffix: str | None = None
    semantic_role: Any = None
    semantic_schema: Any = None
    if role.endswith("_SEMANTIC_AUTHORITY"):
        suffix = "SEMANTIC_AUTHORITY"
        semantic_role = document.get("semantic_authority_role")
        semantic_schema = document.get("semantic_authority_schema")
    elif role.endswith("_INTENT"):
        suffix = "INTENT"
        semantic_role = document.get("semantic_authority_role")
        semantic_schema = document.get("semantic_authority_schema")
    elif role.endswith("_APPEND"):
        suffix = "APPEND"
        intent_id = _cid(
            document.get("intent_id"),
            "controlled append intent",
        )
        semantic_role = controlled_intent_semantic_roles.get(intent_id)
        if semantic_role is None:
            _fail("controlled append lacks its exact controlled intent role")
    if suffix is None:
        return
    kind = _CONTROL_KIND_BY_SEMANTIC_ROLE.get(semantic_role)
    if kind is None or role != f"CONTROLLED_{kind}_{suffix}":
        _fail(
            "portable controlled record role differs from embedded semantic "
            "authority"
        )
    if (
        suffix != "APPEND"
        and semantic_schema
        != _CONTROL_SCHEMA_BY_SEMANTIC_ROLE.get(semantic_role)
    ):
        _fail("portable controlled semantic role/schema binding changed")


def _canonical_fraction(value: Any, label: str) -> Fraction:
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value.get("numerator")) is not int
        or type(value.get("denominator")) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{label} is not one exact rational")
    result = Fraction(value["numerator"], value["denominator"])
    if value != {
        "numerator": result.numerator,
        "denominator": result.denominator,
    }:
        _fail(f"{label} is not one reduced canonical rational")
    return result


def _assert_self_contained_role_semantics(
    *,
    declaration: V075PortableSemanticRoleDeclarationV2,
    document: Mapping[str, Any],
) -> None:
    """Replay the two roles whose full artifact semantics are self-contained."""

    if declaration.role == "OCCURRENCE_IDENTITY":
        for key in (
            "target_tape_namespace_id",
            "context_id",
            "threshold_profile_id",
            "cap_profile_id",
        ):
            _cid(document.get(key), f"occurrence identity {key}")
        arm = document.get("arm")
        source_transport_id = document.get("source_transport_id")
        if source_transport_id is not None:
            _cid(source_transport_id, "occurrence source transport")
        if (
            document.get("schema_version") != "1.0.0"
            or arm
            not in {
                "SOURCE_CONSENSUS_PRIOR",
                "NO_PRIOR",
                "WRONG_CONSENSUS_PRIOR",
                "OOD_ABSTENTION",
                "MATCHED_DIRECT_GROUND",
            }
            or type(document.get("occurrence_ordinal")) is not int
            or document["occurrence_ordinal"] < 0
            or (source_transport_id is not None)
            != (arm == "SOURCE_CONSENSUS_PRIOR")
            or document.get("frozen_before_observation") is not True
            or type(document.get("batch_count_at_freeze")) is not int
            or document["batch_count_at_freeze"] != 0
            or type(document.get("observer_calls")) is not int
            or document["observer_calls"] != 0
            or type(document.get("kernel_calls")) is not int
            or document["kernel_calls"] != 0
            or document.get("target_accessed") is not False
            or document.get("private_material_serialized") is not False
        ):
            _fail("occurrence identity self-contained semantics changed")
        return
    if declaration.role == "SIGNED_BATCH_OUTCOME":
        next_ranks = document.get("next_ranks")
        realized_reward = _canonical_fraction(
            document.get("realized_row_reward"),
            "signed batch outcome reward",
        )
        reward_sum = _canonical_fraction(
            document.get("reward_sum"),
            "signed batch outcome reward sum",
        )
        count = document.get("count")
        if (
            document.get("schema_version") != "2.0.0"
            or type(next_ranks) is not list
            or not next_ranks
            or any(type(rank) is not int or rank < 0 for rank in next_ranks)
            or type(document.get("failure")) is not bool
            or type(document.get("terminal")) is not bool
            or type(document.get("spawn_cell")) is not int
            or document["spawn_cell"] < 0
            or type(document.get("spawn_rank")) is not int
            or document["spawn_rank"] <= 0
            or realized_reward < 0
            or type(count) is not int
            or count <= 0
            or reward_sum != realized_reward * count
        ):
            _fail("signed batch outcome self-contained semantics changed")


def _expected_embedded_content_id(
    *,
    declaration: V075PortableSemanticRoleDeclarationV2,
    document: Mapping[str, Any],
) -> str | None:
    id_key = declaration.embedded_content_id_field
    if id_key is None:
        return None
    if declaration.payload_schema_override is not None:
        try:
            payload = {
                "schema": declaration.payload_schema_override,
                "schema_version": document["schema_version"],
                **{
                    key: document[key]
                    for key in declaration.included_content_id_fields
                },
            }
        except KeyError as error:
            raise V075PortableSemanticRegistryV2InvariantViolation(
                "portable semantic content-ID payload is incomplete"
            ) from error
    elif declaration.included_content_id_fields:
        try:
            payload = {
                key: document[key]
                for key in declaration.included_content_id_fields
            }
        except KeyError as error:
            raise V075PortableSemanticRegistryV2InvariantViolation(
                "portable semantic content-ID payload is incomplete"
            ) from error
    else:
        payload = {
            key: value
            for key, value in document.items()
            if key != id_key
            and key not in declaration.excluded_content_id_fields
        }
    return _hash_domain(declaration.semantic_hash_domain_tag, payload)


_PORTABLE_RECORD_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "index",
        "role",
        "artifact_schema",
        "artifact_domain_tag",
        "semantic_artifact_id",
        "dependency_record_ids",
        "canonical_artifact_bytes_hex",
        "raw_bytes_complete",
        "private_material_serialized",
        "official_execution_allowed",
        "record_id",
    }
)


def _replay_portable_record_document(
    *,
    record_document: Mapping[str, Any],
    registry: V075PortableSemanticRegistryV2,
    controlled_intent_semantic_roles: Mapping[str, str],
) -> tuple[
    V075PortableSemanticRoleDeclarationV2,
    bytes,
    dict[str, Any],
]:
    if type(record_document) is not dict or set(record_document) != (
        _PORTABLE_RECORD_KEYS
    ):
        _fail("portable record wrapper fields are hidden, missing, or malformed")
    if (
        record_document.get("schema") != _PORTABLE_RECORD_SCHEMA
        or record_document.get("schema_version")
        != _PORTABLE_RECORD_SCHEMA_VERSION
        or record_document.get("profile_key") != PORTABLE_BUNDLE_PROFILE_KEY
        or record_document.get("raw_bytes_complete") is not True
        or record_document.get("private_material_serialized") is not False
        or record_document.get("official_execution_allowed") is not False
        or type(record_document.get("index")) is not int
        or record_document["index"] < 0
    ):
        _fail("portable record wrapper metadata changed")
    role = record_document.get("role")
    if type(role) is not str:
        _fail("portable record lacks one typed role")
    declaration = registry.by_role.get(role)
    if declaration is None:
        _fail("portable record uses an undeclared semantic role")
    if (
        record_document.get("artifact_schema")
        != declaration.artifact_schema
        or record_document.get("artifact_domain_tag")
        != declaration.record_domain_tag
    ):
        _fail("portable record role/schema/domain binding changed")
    semantic_artifact_id = _cid(
        record_document.get("semantic_artifact_id"),
        "portable record semantic artifact",
    )
    dependencies = record_document.get("dependency_record_ids")
    if (
        type(dependencies) is not list
        or dependencies != sorted(set(dependencies))
    ):
        _fail("portable record dependencies are malformed")
    for dependency in dependencies:
        _cid(dependency, "portable record dependency")
    artifact_hex = record_document.get("canonical_artifact_bytes_hex")
    if type(artifact_hex) is not str:
        _fail("portable record raw bytes are mistyped")
    try:
        artifact_raw = bytes.fromhex(artifact_hex)
    except ValueError as error:
        raise V075PortableSemanticRegistryV2InvariantViolation(
            "portable record raw bytes are not lowercase hexadecimal"
        ) from error
    if not artifact_raw or artifact_raw.hex() != artifact_hex:
        _fail("portable record raw bytes are not canonical lowercase hex")
    artifact_document = _strict_document(
        artifact_raw,
        label=f"{role} semantic artifact",
    )
    _assert_public_document(artifact_document)
    _assert_declared_shape(
        declaration=declaration,
        document=artifact_document,
        registry=registry,
    )
    _assert_dynamic_control_role(
        role=role,
        document=artifact_document,
        controlled_intent_semantic_roles=(
            controlled_intent_semantic_roles
        ),
    )
    _assert_self_contained_role_semantics(
        declaration=declaration,
        document=artifact_document,
    )
    expected_embedded_id = _expected_embedded_content_id(
        declaration=declaration,
        document=artifact_document,
    )
    if expected_embedded_id is not None:
        actual_embedded_id = _cid(
            artifact_document.get(declaration.embedded_content_id_field),
            f"{role} embedded semantic content ID",
        )
        if actual_embedded_id != expected_embedded_id:
            _fail("portable artifact cached semantic content ID changed")
    if declaration.record_identity_field is None:
        expected_record_semantic_id = _hash_raw_domain(
            declaration.semantic_hash_domain_tag,
            artifact_raw,
        )
    else:
        expected_record_semantic_id = _cid(
            artifact_document.get(declaration.record_identity_field),
            f"{role} record identity field",
        )
    if semantic_artifact_id != expected_record_semantic_id:
        _fail("portable record semantic identity differs from artifact bytes")
    record_payload = {
        key: value
        for key, value in record_document.items()
        if key != "record_id"
    }
    if _cid(record_document.get("record_id"), "portable record") != (
        _hash_domain(declaration.record_domain_tag, record_payload)
    ):
        _fail("portable record content ID differs from independent replay")
    return declaration, artifact_raw, artifact_document


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableRecordSemanticAttestationV2:
    """Typed partial semantic replay bound to one transport and source build."""

    _issuer: InitVar[object]
    registry_id: str
    static_surface_registry_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    source_manifest_id: str
    declaration_id: str
    record_id: str
    record_index: int
    role: str
    artifact_schema: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    semantic_hash_authority_module: str
    semantic_verifier_authority: str
    embedded_content_id_replay_status: str
    semantic_replay_status: V075PortableSemanticReplayStatusV2
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.registry_id, "portable semantic registry"),
            (
                self.static_surface_registry_id,
                "static surface registry",
            ),
            (self.portable_bundle_id, "portable bundle"),
            (self.portable_bundle_sha256, "portable bundle bytes"),
            (self.source_manifest_id, "public replay source manifest"),
            (self.declaration_id, "semantic role declaration"),
            (self.record_id, "portable record"),
            (self.semantic_artifact_id, "portable semantic artifact"),
            (
                self.canonical_artifact_sha256,
                "portable canonical artifact bytes",
            ),
        ):
            _cid(value, label)
        if (
            _issuer is not _ATTESTATION_ISSUER
            or type(self.record_index) is not int
            or self.record_index < 0
            or type(self.role) is not str
            or not self.role
            or type(self.artifact_schema) is not str
            or not self.artifact_schema.startswith("acfqp.")
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or type(self.semantic_hash_authority_module) is not str
            or not self.semantic_hash_authority_module.startswith("acfqp.")
            or type(self.semantic_verifier_authority) is not str
            or not self.semantic_verifier_authority
            or self.embedded_content_id_replay_status
            not in {"RECOMPUTED", "NOT_APPLICABLE"}
            or type(self.semantic_replay_status)
            is not V075PortableSemanticReplayStatusV2
        ):
            _fail("portable record semantic attestation is malformed")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_record_semantic_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "registry_id": self.registry_id,
            "static_surface_registry_id": self.static_surface_registry_id,
            "portable_bundle_profile_key": PORTABLE_BUNDLE_PROFILE_KEY,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "portable_bundle_membership_verified_by_this_attestation": False,
            "source_manifest_profile_key": SOURCE_MANIFEST_PROFILE_KEY,
            "source_manifest_id": self.source_manifest_id,
            "source_manifest_reference_status": (
                "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
            ),
            "source_manifest_semantically_verified_by_this_module": False,
            "declaration_id": self.declaration_id,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "artifact_schema": self.artifact_schema,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "semantic_hash_authority_module": (
                self.semantic_hash_authority_module
            ),
            "semantic_verifier_module": (
                "acfqp.v075_portable_semantic_registry_v2"
            ),
            "semantic_verifier_function": (
                "attest_v075_portable_evidence_record_document_v2"
            ),
            "semantic_verifier_authority": (
                self.semantic_verifier_authority
            ),
            "canonical_shape_recomputed": True,
            "record_content_id_recomputed": True,
            "semantic_content_id_recomputed": True,
            "embedded_content_id_replay_status": (
                self.embedded_content_id_replay_status
            ),
            "role_specific_hash_authority_applied": True,
            "static_surface_used_as_artifact_semantic_evidence": False,
            "semantic_replay_status": (
                self.semantic_replay_status.value
            ),
            "independent_semantic_replay_complete": (
                self.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
            ),
            "producer_typed_object_reconstructed": False,
            "dependency_aware_typed_object_replay_complete": False,
            "incomplete_reason": (
                {
                    "kind": "NOT_APPLICABLE",
                    "reason": "SELF_CONTAINED_ROLE_EXACTLY_REPLAYED",
                }
                if self.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
                else (
                    "DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_NOT_YET_"
                    "IMPLEMENTED"
                )
            ),
            "semantic_registry_replay_complete": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestation_id": self.attestation_id,
        }


def attest_v075_portable_evidence_record_document_v2(
    *,
    record_document: Mapping[str, Any],
    portable_bundle_id: str,
    portable_bundle_sha256: str,
    source_manifest_id: str,
    registry: V075PortableSemanticRegistryV2 | None = None,
    controlled_intent_semantic_roles: Mapping[str, str] | None = None,
) -> V075PortableRecordSemanticAttestationV2:
    """Independently replay one portable wrapper and its canonical artifact."""

    exact_registry = freeze_v075_portable_semantic_registry_v2()
    candidate_registry = exact_registry if registry is None else registry
    if (
        type(candidate_registry) is not V075PortableSemanticRegistryV2
        or candidate_registry != exact_registry
        or candidate_registry.registry_id != exact_registry.registry_id
    ):
        _fail("portable record uses a foreign or caller-authored registry")
    bundle_id = _cid(portable_bundle_id, "portable bundle")
    bundle_sha256 = _cid(
        portable_bundle_sha256,
        "portable bundle canonical bytes",
    )
    manifest_id = _cid(source_manifest_id, "public replay source manifest")
    role_map = (
        {}
        if controlled_intent_semantic_roles is None
        else controlled_intent_semantic_roles
    )
    if not isinstance(role_map, Mapping) or any(
        type(key) is not str or type(value) is not str
        for key, value in role_map.items()
    ):
        _fail("controlled intent role context is malformed")
    declaration, artifact_raw, _artifact_document = (
        _replay_portable_record_document(
            record_document=record_document,
            registry=exact_registry,
            controlled_intent_semantic_roles=role_map,
        )
    )
    return V075PortableRecordSemanticAttestationV2(
        _ATTESTATION_ISSUER,
        exact_registry.registry_id,
        exact_registry.static_surface_registry_id,
        bundle_id,
        bundle_sha256,
        manifest_id,
        declaration.declaration_id,
        record_document["record_id"],
        record_document["index"],
        declaration.role,
        declaration.artifact_schema,
        record_document["semantic_artifact_id"],
        hashlib.sha256(artifact_raw).hexdigest(),
        len(artifact_raw),
        declaration.semantic_hash_authority_module,
        declaration.semantic_verifier_authority,
        (
            "RECOMPUTED"
            if declaration.embedded_content_id_field is not None
            else "NOT_APPLICABLE"
        ),
        declaration.semantic_replay_status,
    )


def verify_v075_portable_record_semantic_attestation_bytes_v2(
    *,
    attestation_bytes: bytes,
    record_document: Mapping[str, Any],
    portable_bundle_id: str,
    portable_bundle_sha256: str,
    source_manifest_id: str,
    controlled_intent_semantic_roles: Mapping[str, str] | None = None,
) -> V075PortableRecordSemanticAttestationV2:
    document = _strict_document(
        attestation_bytes,
        label="portable record semantic attestation",
        byte_cap=256 * 1024,
    )
    if (
        document.get("semantic_replay_status")
        not in {
            V075PortableSemanticReplayStatusV2.COMPLETE.value,
            V075PortableSemanticReplayStatusV2.INCOMPLETE.value,
        }
        or (
            document.get("independent_semantic_replay_complete")
            is not (
                document.get("semantic_replay_status")
                == V075PortableSemanticReplayStatusV2.COMPLETE.value
            )
        )
        or document.get("semantic_registry_replay_complete") is not False
        or document.get("official_execution_allowed") is not False
        or document.get("production_authorizing") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("plan_certificate") is not False
        or document.get("infeasibility_certificate") is not False
    ):
        _fail("portable record attestation attempts to claim completion")
    expected = attest_v075_portable_evidence_record_document_v2(
        record_document=record_document,
        portable_bundle_id=portable_bundle_id,
        portable_bundle_sha256=portable_bundle_sha256,
        source_manifest_id=source_manifest_id,
        controlled_intent_semantic_roles=(
            controlled_intent_semantic_roles
        ),
    )
    if attestation_bytes != expected.canonical_bytes:
        _fail(
            "portable record semantic attestation is stale, transplanted, "
            "or caller-authored"
        )
    return expected


_ATTESTATION_SET_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortableSemanticAttestationSetV2:
    """One exact attestation per record in one verified portable bundle."""

    _issuer: InitVar[object]
    registry_id: str
    static_surface_registry_id: str
    portable_bundle_id: str
    portable_bundle_sha256: str
    source_manifest_id: str
    attestations: tuple[V075PortableRecordSemanticAttestationV2, ...]
    _attestation_set_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.registry_id, "portable semantic registry"),
            (
                self.static_surface_registry_id,
                "static implementation-surface registry",
            ),
            (self.portable_bundle_id, "portable bundle"),
            (self.portable_bundle_sha256, "portable bundle bytes"),
            (self.source_manifest_id, "public replay source manifest"),
        ):
            _cid(value, label)
        if (
            _issuer is not _ATTESTATION_SET_ISSUER
            or type(self.attestations) is not tuple
            or not self.attestations
            or any(
                type(item) is not V075PortableRecordSemanticAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(range(len(self.attestations)))
            or len({item.record_id for item in self.attestations})
            != len(self.attestations)
            or len({item.attestation_id for item in self.attestations})
            != len(self.attestations)
            or any(
                item.registry_id != self.registry_id
                or item.static_surface_registry_id
                != self.static_surface_registry_id
                or item.portable_bundle_id != self.portable_bundle_id
                or item.portable_bundle_sha256
                != self.portable_bundle_sha256
                or item.source_manifest_id != self.source_manifest_id
                for item in self.attestations
            )
        ):
            _fail("portable semantic attestation set is malformed")
        object.__setattr__(
            self,
            "_attestation_set_id",
            _hash("attestation_set", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_semantic_attestation_set.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "registry_id": self.registry_id,
            "static_surface_registry_id": self.static_surface_registry_id,
            "portable_bundle_profile_key": PORTABLE_BUNDLE_PROFILE_KEY,
            "portable_bundle_id": self.portable_bundle_id,
            "portable_bundle_sha256": self.portable_bundle_sha256,
            "source_manifest_profile_key": SOURCE_MANIFEST_PROFILE_KEY,
            "source_manifest_id": self.source_manifest_id,
            "source_manifest_reference_status": (
                "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
            ),
            "source_manifest_semantically_verified_by_this_module": False,
            "record_ids": [item.record_id for item in self.attestations],
            "attestation_ids": [
                item.attestation_id for item in self.attestations
            ],
            "record_count": len(self.attestations),
            "complete_record_count": sum(
                item.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.COMPLETE
                for item in self.attestations
            ),
            "incomplete_record_count": sum(
                item.semantic_replay_status
                is V075PortableSemanticReplayStatusV2.INCOMPLETE
                for item in self.attestations
            ),
            "all_bundle_records_attested": True,
            "portable_bundle_membership_verified_by_aggregate": True,
            "canonical_shape_and_content_id_replay_complete": True,
            "aggregate_semantic_replay_complete": False,
            "semantic_registry_replay_complete": False,
            "dependency_aware_typed_object_replay_complete": False,
            "static_surface_used_as_artifact_semantic_evidence": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def attestation_set_id(self) -> str:
        return self._attestation_set_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestations": [
                item.to_document() for item in self.attestations
            ],
            "attestation_set_id": self.attestation_set_id,
        }


def _controlled_intent_role_context(
    record_documents: tuple[dict[str, Any], ...],
) -> Mapping[str, str]:
    result: dict[str, str] = {}
    for record in record_documents:
        role = record.get("role")
        if role not in {
            "CONTROLLED_ROOT_INTENT",
            "CONTROLLED_CHILD_INTENT",
            "CONTROLLED_PROMOTION_INTENT",
        }:
            continue
        raw_hex = record.get("canonical_artifact_bytes_hex")
        if type(raw_hex) is not str:
            _fail("controlled intent portable bytes are malformed")
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError as error:
            raise V075PortableSemanticRegistryV2InvariantViolation(
                "controlled intent portable bytes are malformed"
            ) from error
        document = _strict_document(
            raw,
            label="controlled intent semantic role context",
        )
        intent_id = _cid(
            record.get("semantic_artifact_id"),
            "controlled intent semantic artifact",
        )
        semantic_role = document.get("semantic_authority_role")
        if (
            type(semantic_role) is not str
            or intent_id in result
            or _CONTROL_KIND_BY_SEMANTIC_ROLE.get(semantic_role) is None
        ):
            _fail("controlled intent semantic role context is invalid")
        result[intent_id] = semantic_role
    return MappingProxyType(result)


def attest_v075_portable_occurrence_evidence_bundle_bytes_v2(
    *,
    bundle_bytes: bytes,
    source_manifest_id: str,
) -> V075PortableSemanticAttestationSetV2:
    """Transport-replay a full bundle, then attest every record independently."""

    manifest_id = _cid(source_manifest_id, "public replay source manifest")
    try:
        replayed_bundle = (
            portable.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                bundle_bytes
            )
        )
    except Exception as error:
        raise V075PortableSemanticRegistryV2InvariantViolation(
            "portable transport replay failed before semantic attestation"
        ) from error
    registry = freeze_v075_portable_semantic_registry_v2()
    bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    record_documents = tuple(
        record.to_document() for record in replayed_bundle.records
    )
    role_context = _controlled_intent_role_context(record_documents)
    attestations = tuple(
        attest_v075_portable_evidence_record_document_v2(
            record_document=document,
            portable_bundle_id=replayed_bundle.bundle_id,
            portable_bundle_sha256=bundle_sha256,
            source_manifest_id=manifest_id,
            registry=registry,
            controlled_intent_semantic_roles=role_context,
        )
        for document in record_documents
    )
    if tuple(item.record_id for item in attestations) != tuple(
        record.record_id for record in replayed_bundle.records
    ):
        _fail("semantic attestation set omitted or reordered bundle records")
    return V075PortableSemanticAttestationSetV2(
        _ATTESTATION_SET_ISSUER,
        registry.registry_id,
        registry.static_surface_registry_id,
        replayed_bundle.bundle_id,
        bundle_sha256,
        manifest_id,
        attestations,
    )


def verify_v075_portable_semantic_attestation_set_bytes_v2(
    *,
    attestation_set_bytes: bytes,
    bundle_bytes: bytes,
    source_manifest_id: str,
) -> V075PortableSemanticAttestationSetV2:
    """Reject self-claims and exactly reconstruct the aggregate evidence."""

    document = _strict_document(
        attestation_set_bytes,
        label="portable semantic attestation set",
        byte_cap=128 * 1024 * 1024,
    )
    if (
        document.get("aggregate_semantic_replay_complete") is not False
        or document.get("semantic_registry_replay_complete") is not False
        or document.get(
            "dependency_aware_typed_object_replay_complete"
        )
        is not False
        or document.get("official_execution_allowed") is not False
        or document.get("production_authorizing") is not False
        or document.get("fresh_heldout_accessed") is not False
        or document.get("plan_certificate") is not False
        or document.get("infeasibility_certificate") is not False
    ):
        _fail("portable semantic attestation set claims false completion")
    expected = attest_v075_portable_occurrence_evidence_bundle_bytes_v2(
        bundle_bytes=bundle_bytes,
        source_manifest_id=source_manifest_id,
    )
    if attestation_set_bytes != expected.canonical_bytes:
        _fail(
            "portable semantic attestation set is stale, transplanted, "
            "incomplete, or caller-authored"
        )
    return expected


def open_v075_production_portable_semantic_registry_v2(
    **_forbidden: Any,
) -> NoReturn:
    raise V075PortableSemanticRegistryProductionV2NotReady(
        PRODUCTION_BLOCKER
    )


__all__ = [
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
    "PORTABLE_BUNDLE_PROFILE_KEY",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "SEMANTIC_REGISTRY_REPLAY_COMPLETE",
    "SOURCE_MANIFEST_PROFILE_KEY",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_SCOPE",
    "V075PortableRecordSemanticAttestationV2",
    "V075PortableSemanticAttestationSetV2",
    "V075PortableSemanticRegistryProductionV2NotReady",
    "V075PortableSemanticRegistryV2",
    "V075PortableSemanticRegistryV2InvariantViolation",
    "V075PortableSemanticReplayStatusV2",
    "V075PortableSemanticRoleDeclarationV2",
    "attest_v075_portable_evidence_record_document_v2",
    "attest_v075_portable_occurrence_evidence_bundle_bytes_v2",
    "freeze_v075_portable_semantic_registry_v2",
    "open_v075_production_portable_semantic_registry_v2",
    "verify_v075_portable_record_semantic_attestation_bytes_v2",
    "verify_v075_portable_semantic_attestation_set_bytes_v2",
    "verify_v075_portable_semantic_registry_bytes_v2",
]
