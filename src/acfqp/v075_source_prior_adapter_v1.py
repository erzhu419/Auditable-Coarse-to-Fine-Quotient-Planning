"""Verified source-only prior bridge for the V0-075 campaign.

This module never opens the V0-072 recipe and has no target observer, hidden
law, result, or certificate dependency.  It consumes already verified V0-075
source authorities:

* the compact proposal archive and its verification;
* the replay-materialized source work and its verification.

The first stage compiles an immutable catalogue of the three source
``APPLIED`` feature consensuses.  The final adapter is minted only when the
source-work identity graph matches the archive exactly.  It references the
materialized work and verification identities; counter values are neither
duplicated nor replaced by zeros.

The production work replay is currently ``NOT_RUN``.  Consequently the
catalogue can be compiled and audited now, while a production adapter cannot
honestly be minted until that replay materializes the counters whose identity
is already frozen in the source archive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_frozen_source_proposal_archive_v1 as archive_v1
from acfqp import v075_source_offline_work_materializer_v1 as work_v1


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_source_prior_adapter_v1"
MAX_CANONICAL_CATALOGUE_BYTES = 64 * 1024
MAX_CANONICAL_ADAPTER_BYTES = 128 * 1024
PRODUCTION_ADAPTER_STATUS = (
    "BLOCKED_SOURCE_OFFLINE_WORK_PRODUCTION_REPLAY_NOT_RUN"
)
REQUIRED_SOURCE_REPLAY_COMMIT = (
    "63cc0f5f78f64b7845319d1c1a5856212e3b8097"
)
REQUIRED_SOURCE_REPLAY_TREE = (
    "8c88ef5e2747267a309834d155136c40ba926b61"
)
REGISTERED_SOURCE_PROPOSAL_ARCHIVE_ID = (
    "4b25945b07d94ace9a6af8cbf979a9133e3780b6306c0bc3b7d8055b2c25bf92"
)
REGISTERED_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION_ID = (
    "e23c98ce70ebee04dd6dcccd29149a16c90b48ef5e62b5e006a524c58818157c"
)
REGISTERED_SOURCE_RECIPE_BYTES_SHA256 = (
    "041d52af80d56de3d427c8d44a3048d77521f15da9dcbc476659fd7724c6c76b"
)
REGISTERED_SOURCE_FEATURE_SCHEMA_ID = (
    "6c5867ab74182b98faf776ec6a544799c745b5bf6c7cd9943733da5fe96951de"
)

DOMAIN_TAGS = {
    "entry": "acfqp:v075-source-prior-entry:v1",
    "catalogue": "acfqp:v075-source-prior-catalogue:v1",
    "adapter": "acfqp:v075-source-prior-adapter:v1",
    "verification": "acfqp:v075-source-prior-adapter-verification:v1",
    "production_status": (
        "acfqp:v075-source-prior-adapter-production-status:v1"
    ),
    "snapshot_requirement": (
        "acfqp:v075-source-prior-replay-snapshot-requirement:v1"
    ),
}

# This registry is source-only and is copied from the already frozen proposal
# boundary.  Keeping it here prevents each selector construction from reading
# the historical V0-072 recipe.
#
# Fields:
#   source ordinal, feature key, disposition, consensus ID,
#   exact midrank numerator/denominator, summary ID, optional lookup ID.
REGISTERED_SOURCE_CONSENSUS = (
    (
        0,
        "9f5884cbc527188468c0ebc857752bcea61d00288ee5b928d5919fee75e3a550",
        "INSUFFICIENT_CONTEXTS",
        "0422765414313d5b59d0a50399489195bebb76add200d8eaec05b6cb1ff7d04c",
        1,
        1,
        "607c7946d8eab974129a7540252717d5dfe57d4ea373c9f92a9c9f5875299cf1",
        None,
    ),
    (
        1,
        "2201bad0d29ae45e7ba877ef1aa40e633deeee3ff7b45f65a43134ec53dfdc52",
        "INSUFFICIENT_CONTEXTS",
        "4094f8ad7132221e25b9a7dbb72ad75cb52e5b9c358b5067b778affdd2e1daa9",
        1,
        4,
        "55c38527d58a76ef59a1da458fb6c6ca97e6acda6a8a46c9185e949329229e67",
        None,
    ),
    (
        2,
        "1d5bff475fa3e1bd7c0ba16754362e10a0e96987ae1b9731adf35209c992a594",
        "INSUFFICIENT_CONTEXTS",
        "52cdb4efa990c1ca412b190a1a55a303f3972afe9621d879037e339299a62832",
        2,
        3,
        "5a1d977e303c19bec58e3ff8197a7caa3e5571751ad010b355222c0d7b1177f4",
        None,
    ),
    (
        3,
        "9fe53537e8657540c657163cb437e1b3885a06a558ca27f0b92cb9d57135e28a",
        "APPLIED",
        "7dcd4446362466618ee5e063a47e650c6c9d02668e2ebe4bdb645ec5932f934e",
        1,
        6,
        "1ad34de3543729574352e79f6b9beb2a6c390c390cbff124224da2f3b8790b9b",
        "9e36a5014efbe2e28922a83e63a4677133b5324c0c33ce1b984897140ff55561",
    ),
    (
        4,
        "7045f3287922411f0648501de97cc6c00ff6dad38fcd11ecf525e0a869e72a6a",
        "APPLIED",
        "a5dba2f67f72c6d923c8e0fc48959bf3f5d8a51b1348d8e809d065a433ccdbc4",
        19,
        36,
        "c3c834524a9d79816bad349af8ef0c7a8f00118535343d60e88d0983ab154356",
        "8676ec02ccae46cf5f0973c71f636a59ace03775bf0eaf6e71da5e4a9875f551",
    ),
    (
        5,
        "19ae3b19be43564c7781aab562d7e6261848f4b00e30cc7a65360a44056faadc",
        "APPLIED",
        "afa322421e2956f33c6912182eb4124b800c0501e3ac93aa481bfb4435e2e846",
        1,
        1,
        "292e8dfe121f3eba13aece59d93fca7417c131939b5b4ffdcc4a13084367f444",
        "0e555a7e29474b4e78591aa9a6f1994968115cbfeab37d48dde29f474ccb5813",
    ),
    (
        6,
        "71ff403cae8d2e5fd571200f4f1886e7aa7ad0d45c5b30315d14fc77817348a8",
        "INSUFFICIENT_CONTEXTS",
        "f3b5f8e817976b26bed416096033e5935612a5bef147ac644efc08ce7b208081",
        0,
        1,
        "e21377bd27606a3fda948cc7ffa879d04ee0559bb3c6b333b7338f6cc52e8a31",
        None,
    ),
)

REGISTERED_SOURCE_FEATURE_KEYS = tuple(
    item[1] for item in REGISTERED_SOURCE_CONSENSUS
)
REGISTERED_APPLIED_FEATURE_KEYS = tuple(
    item[1] for item in REGISTERED_SOURCE_CONSENSUS
    if item[2] == "APPLIED"
)
REGISTERED_NONAPPLIED_FEATURE_KEYS = tuple(
    item[1] for item in REGISTERED_SOURCE_CONSENSUS
    if item[2] != "APPLIED"
)
_ISSUER = object()


class V075SourcePriorAdapterViolation(ValueError):
    """A source-prior authority, mapping, or identity transplant is invalid."""


def _fail(message: str) -> None:
    raise V075SourcePriorAdapterViolation(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075SourcePriorAdapterViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075SourcePriorAdapterViolation(
            "source-prior content identity cannot be derived"
        ) from error
    return hashlib.sha256(domain + b"\x00" + encoded).hexdigest()


def _snapshot_requirement_id() -> str:
    return _content_id(
        "snapshot_requirement",
        {
            "schema": (
                "acfqp.v075_source_prior_replay_snapshot_requirement.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "required_source_replay_commit": REQUIRED_SOURCE_REPLAY_COMMIT,
            "required_source_replay_tree": REQUIRED_SOURCE_REPLAY_TREE,
            "clean_detached_worktree_required": True,
            "replay_and_materialization_same_process_required": True,
        },
    )


def _exact_mapping(
    value: Any,
    *,
    keys: set[str],
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} has an invalid field set")
    return value


def _strict_load(raw: Any, *, maximum_bytes: int) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > maximum_bytes
    ):
        _fail("source-prior bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075SourcePriorAdapterViolation(
            "source-prior bytes are not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("source-prior bytes are not one canonical object")
    return document


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("source-prior midrank must use exact Fraction arithmetic")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _fraction_from_document(value: Any) -> Fraction:
    if type(value) is Fraction:
        return value
    item = _exact_mapping(
        value,
        keys={"numerator", "denominator"},
        field_name="source-prior midrank",
    )
    if (
        type(item["numerator"]) is not int
        or type(item["denominator"]) is not int
        or item["denominator"] <= 0
    ):
        _fail("source-prior midrank is not an exact rational")
    result = Fraction(item["numerator"], item["denominator"])
    if (
        result.numerator != item["numerator"]
        or result.denominator != item["denominator"]
    ):
        _fail("source-prior midrank is not reduced")
    return result


def _verify_archive_authorities(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
) -> None:
    if (
        type(source_archive)
        is not archive_v1.V075FrozenSourceProposalArchiveV1
        or type(archive_verification)
        is not archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ):
        _fail("source catalogue requires exact archive/verification types")
    if (
        source_archive.archive_id
        != REGISTERED_SOURCE_PROPOSAL_ARCHIVE_ID
        or archive_verification.verification_id
        != REGISTERED_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION_ID
        or source_archive.source_recipe_bytes_sha256
        != REGISTERED_SOURCE_RECIPE_BYTES_SHA256
        or source_archive.feature_schema_id
        != REGISTERED_SOURCE_FEATURE_SCHEMA_ID
        or archive_verification.source_recipe_id
        != source_archive.source_recipe_id
        or archive_verification.archive_id != source_archive.archive_id
        or archive_verification.recomputed_archive_id
        != source_archive.archive_id
        or archive_verification.archive_bytes_sha256
        != hashlib.sha256(source_archive.canonical_bytes).hexdigest()
        or archive_verification.offline_work_reference_id
        != source_archive.offline_work.work_reference_id
        or archive_verification.consensus_summary_ids
        != tuple(
            item.summary_id for item in source_archive.consensus_summaries
        )
        or archive_verification.applied_lookup_ids
        != tuple(item.lookup_id for item in source_archive.applied_lookup)
        or source_archive.to_document()["proposal_only"] is not True
        or source_archive.to_document()["may_certify"] is not False
        or source_archive.to_document()["target_execution_allowed"] is not False
    ):
        _fail("source archive verification does not bind the claimed archive")


def _verify_registered_source_consensus(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
) -> None:
    actual = tuple(
        (
            item.ordinal,
            item.feature_key,
            item.disposition,
            item.consensus_id,
            item.mean_midrank.numerator,
            item.mean_midrank.denominator,
            item.summary_id,
            (
                next(
                    (
                        lookup.lookup_id
                        for lookup in source_archive.applied_lookup
                        if lookup.source_consensus_ordinal == item.ordinal
                    ),
                    None,
                )
            ),
        )
        for item in source_archive.consensus_summaries
    )
    if actual != REGISTERED_SOURCE_CONSENSUS:
        _fail("source archive differs from the registered consensus catalogue")


@dataclass(frozen=True, slots=True)
class V075SourcePriorEntryV1:
    _issuer: object = field(repr=False, compare=False)
    applied_ordinal: int
    source_consensus_ordinal: int
    feature_key: str
    consensus_id: str
    source_summary_id: str
    source_lookup_id: str
    exact_mean_midrank: Fraction
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("source-prior entries are compiler-issued only")
        for value, name in (
            (self.feature_key, "source-prior feature"),
            (self.consensus_id, "source-prior consensus"),
            (self.source_summary_id, "source-prior summary"),
            (self.source_lookup_id, "source-prior lookup"),
        ):
            _cid(value, name)
        if (
            type(self.applied_ordinal) is not int
            or self.applied_ordinal not in range(3)
            or type(self.source_consensus_ordinal) is not int
            or self.source_consensus_ordinal not in (3, 4, 5)
            or type(self.exact_mean_midrank) is not Fraction
            or not 0 <= self.exact_mean_midrank <= 1
        ):
            _fail("source-prior APPLIED entry is malformed")
        expected = REGISTERED_SOURCE_CONSENSUS[
            self.source_consensus_ordinal
        ]
        if (
            expected[2] != "APPLIED"
            or (
                self.feature_key,
                self.consensus_id,
                self.exact_mean_midrank,
                self.source_summary_id,
                self.source_lookup_id,
            )
            != (
                expected[1],
                expected[3],
                Fraction(expected[4], expected[5]),
                expected[6],
                expected[7],
            )
        ):
            _fail("source-prior entry differs from registered APPLIED evidence")
        object.__setattr__(
            self,
            "_entry_id",
            _content_id("entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_prior_entry.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "applied_ordinal": self.applied_ordinal,
            "source_consensus_ordinal": self.source_consensus_ordinal,
            "feature_key": self.feature_key,
            "consensus_id": self.consensus_id,
            "source_summary_id": self.source_summary_id,
            "source_lookup_id": self.source_lookup_id,
            "exact_mean_midrank": _fraction_document(
                self.exact_mean_midrank
            ),
            "disposition": "APPLIED",
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}

    @classmethod
    def from_document(cls, document: Any) -> "V075SourcePriorEntryV1":
        item = _exact_mapping(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "applied_ordinal",
                "source_consensus_ordinal",
                "feature_key",
                "consensus_id",
                "source_summary_id",
                "source_lookup_id",
                "exact_mean_midrank",
                "disposition",
                "source_only",
                "proposal_only",
                "may_certify",
                "entry_id",
            },
            field_name="source-prior entry",
        )
        if (
            item["schema"] != "acfqp.v075_source_prior_entry.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["disposition"] != "APPLIED"
            or item["source_only"] is not True
            or item["proposal_only"] is not True
            or item["may_certify"] is not False
        ):
            _fail("source-prior entry contract changed")
        result = cls(
            _ISSUER,
            item["applied_ordinal"],
            item["source_consensus_ordinal"],
            item["feature_key"],
            item["consensus_id"],
            item["source_summary_id"],
            item["source_lookup_id"],
            _fraction_from_document(item["exact_mean_midrank"]),
        )
        if result.entry_id != _cid(item["entry_id"], "source-prior entry"):
            _fail("source-prior entry identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075SourcePriorCatalogueV1:
    _issuer: object = field(repr=False, compare=False)
    source_recipe_id: str
    source_archive_id: str
    source_archive_verification_id: str
    source_offline_work_reference_id: str
    source_feature_schema_id: str
    consensus_summary_ids: tuple[str, ...]
    entries: tuple[V075SourcePriorEntryV1, ...]
    _catalogue_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("source-prior catalogues are compiler-issued only")
        for value, name in (
            (self.source_recipe_id, "catalogue source recipe"),
            (self.source_archive_id, "catalogue source archive"),
            (
                self.source_archive_verification_id,
                "catalogue archive verification",
            ),
            (
                self.source_offline_work_reference_id,
                "catalogue offline-work reference",
            ),
            (self.source_feature_schema_id, "catalogue feature schema"),
            *((item, "catalogue consensus summary") for item in self.consensus_summary_ids),
        ):
            _cid(value, name)
        if (
            type(self.consensus_summary_ids) is not tuple
            or len(self.consensus_summary_ids) != 7
            or len(set(self.consensus_summary_ids)) != 7
            or self.consensus_summary_ids
            != tuple(item[6] for item in REGISTERED_SOURCE_CONSENSUS)
            or type(self.entries) is not tuple
            or len(self.entries) != 3
            or any(type(item) is not V075SourcePriorEntryV1 for item in self.entries)
            or tuple(item.applied_ordinal for item in self.entries)
            != tuple(range(3))
            or tuple(item.feature_key for item in self.entries)
            != REGISTERED_APPLIED_FEATURE_KEYS
        ):
            _fail("source-prior catalogue is incomplete or reordered")
        object.__setattr__(
            self,
            "_catalogue_id",
            _content_id("catalogue", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_prior_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "source_archive_id": self.source_archive_id,
            "source_archive_verification_id": (
                self.source_archive_verification_id
            ),
            "source_offline_work_reference_id": (
                self.source_offline_work_reference_id
            ),
            "source_feature_schema_id": self.source_feature_schema_id,
            "consensus_summary_ids": list(self.consensus_summary_ids),
            "entry_ids": [item.entry_id for item in self.entries],
            "registered_source_feature_keys": list(
                REGISTERED_SOURCE_FEATURE_KEYS
            ),
            "registered_applied_feature_keys": list(
                REGISTERED_APPLIED_FEATURE_KEYS
            ),
            "registered_nonapplied_feature_keys": list(
                REGISTERED_NONAPPLIED_FEATURE_KEYS
            ),
            "source_consensus_count": 7,
            "applied_entry_count": 3,
            "source_replay_snapshot_requirement_id": (
                _snapshot_requirement_id()
            ),
            "required_source_replay_commit": REQUIRED_SOURCE_REPLAY_COMMIT,
            "required_source_replay_tree": REQUIRED_SOURCE_REPLAY_TREE,
            "clean_detached_worktree_required": True,
            "replay_and_materialization_same_process_required": True,
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
            "work_binding_required": True,
            "selector_use_authorized": False,
            "target_execution_allowed": False,
            "historical_recipe_reads": 0,
        }

    @property
    def catalogue_id(self) -> str:
        return self._catalogue_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "catalogue_id": self.catalogue_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def require_applied_feature(
        self,
        feature_key: str,
    ) -> V075SourcePriorEntryV1:
        key = _cid(feature_key, "requested source-prior feature")
        if key in REGISTERED_NONAPPLIED_FEATURE_KEYS:
            _fail("registered source feature is not APPLIED")
        if key not in REGISTERED_SOURCE_FEATURE_KEYS:
            _fail("unknown source feature is not registered")
        for entry in self.entries:
            if entry.feature_key == key:
                return entry
        _fail("registered APPLIED source feature is missing")

    @classmethod
    def from_document(cls, document: Any) -> "V075SourcePriorCatalogueV1":
        item = _exact_mapping(
            document,
            keys={
                "schema",
                "schema_version",
                "proposed_contract_version",
                "profile_key",
                "source_recipe_id",
                "source_archive_id",
                "source_archive_verification_id",
                "source_offline_work_reference_id",
                "source_feature_schema_id",
                "consensus_summary_ids",
                "entry_ids",
                "registered_source_feature_keys",
                "registered_applied_feature_keys",
                "registered_nonapplied_feature_keys",
                "source_consensus_count",
                "applied_entry_count",
                "source_replay_snapshot_requirement_id",
                "required_source_replay_commit",
                "required_source_replay_tree",
                "clean_detached_worktree_required",
                "replay_and_materialization_same_process_required",
                "source_only",
                "proposal_only",
                "may_certify",
                "work_binding_required",
                "selector_use_authorized",
                "target_execution_allowed",
                "historical_recipe_reads",
                "entries",
                "catalogue_id",
            },
            field_name="source-prior catalogue",
        )
        if (
            item["schema"] != "acfqp.v075_source_prior_catalogue.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["registered_source_feature_keys"]
            != list(REGISTERED_SOURCE_FEATURE_KEYS)
            or item["registered_applied_feature_keys"]
            != list(REGISTERED_APPLIED_FEATURE_KEYS)
            or item["registered_nonapplied_feature_keys"]
            != list(REGISTERED_NONAPPLIED_FEATURE_KEYS)
            or item["source_consensus_count"] != 7
            or item["applied_entry_count"] != 3
            or item["source_replay_snapshot_requirement_id"]
            != _snapshot_requirement_id()
            or item["required_source_replay_commit"]
            != REQUIRED_SOURCE_REPLAY_COMMIT
            or item["required_source_replay_tree"]
            != REQUIRED_SOURCE_REPLAY_TREE
            or item["clean_detached_worktree_required"] is not True
            or item["replay_and_materialization_same_process_required"]
            is not True
            or item["source_only"] is not True
            or item["proposal_only"] is not True
            or item["may_certify"] is not False
            or item["work_binding_required"] is not True
            or item["selector_use_authorized"] is not False
            or item["target_execution_allowed"] is not False
            or item["historical_recipe_reads"] != 0
            or type(item["entries"]) is not list
            or type(item["entry_ids"]) is not list
            or type(item["consensus_summary_ids"]) is not list
        ):
            _fail("source-prior catalogue contract changed")
        entries = tuple(
            V075SourcePriorEntryV1.from_document(value)
            for value in item["entries"]
        )
        result = cls(
            _ISSUER,
            item["source_recipe_id"],
            item["source_archive_id"],
            item["source_archive_verification_id"],
            item["source_offline_work_reference_id"],
            item["source_feature_schema_id"],
            tuple(item["consensus_summary_ids"]),
            entries,
        )
        if (
            item["entry_ids"] != [value.entry_id for value in entries]
            or result.catalogue_id
            != _cid(item["catalogue_id"], "source-prior catalogue")
        ):
            _fail("source-prior catalogue references or identity changed")
        return result


def compile_v075_source_prior_catalogue_v1(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
) -> V075SourcePriorCatalogueV1:
    """Compile from passed verified objects; never read the V0-072 recipe."""

    _verify_archive_authorities(source_archive, archive_verification)
    _verify_registered_source_consensus(source_archive)
    summary_by_ordinal = {
        item.ordinal: item for item in source_archive.consensus_summaries
    }
    entries = tuple(
        V075SourcePriorEntryV1(
            _ISSUER,
            lookup.ordinal,
            lookup.source_consensus_ordinal,
            lookup.feature_key,
            lookup.consensus_id,
            summary_by_ordinal[lookup.source_consensus_ordinal].summary_id,
            lookup.lookup_id,
            lookup.mean_midrank,
        )
        for lookup in source_archive.applied_lookup
    )
    result = V075SourcePriorCatalogueV1(
        _ISSUER,
        source_archive.source_recipe_id,
        source_archive.archive_id,
        archive_verification.verification_id,
        source_archive.offline_work.work_reference_id,
        source_archive.feature_schema_id,
        tuple(
            item.summary_id for item in source_archive.consensus_summaries
        ),
        entries,
    )
    if len(result.canonical_bytes) > MAX_CANONICAL_CATALOGUE_BYTES:
        _fail("source-prior catalogue exceeds its canonical byte cap")
    return result


def load_v075_source_prior_catalogue_v1(
    raw: bytes,
    *,
    expected_catalogue_id: str,
    expected_source_archive_id: str,
    expected_source_archive_verification_id: str,
) -> V075SourcePriorCatalogueV1:
    result = V075SourcePriorCatalogueV1.from_document(
        _strict_load(raw, maximum_bytes=MAX_CANONICAL_CATALOGUE_BYTES)
    )
    if (
        (
            result.catalogue_id,
            result.source_archive_id,
            result.source_archive_verification_id,
        )
        != (
            _cid(expected_catalogue_id, "expected source-prior catalogue"),
            _cid(expected_source_archive_id, "expected source archive"),
            _cid(
                expected_source_archive_verification_id,
                "expected archive verification",
            ),
        )
        or result.canonical_bytes != raw
    ):
        _fail("source-prior catalogue external binding changed")
    return result


def _verify_work_authorities(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    source_work: work_v1.V075SourceOfflineWorkMaterializationV1,
    work_verification: (
        work_v1.V075SourceOfflineWorkMaterializationVerificationV1
    ),
) -> None:
    if (
        type(source_work)
        is not work_v1.V075SourceOfflineWorkMaterializationV1
        or type(work_verification)
        is not work_v1.V075SourceOfflineWorkMaterializationVerificationV1
    ):
        _fail("source adapter requires exact work/verification types")
    reference = source_archive.offline_work
    if (
        source_work.source_recipe_id != source_archive.source_recipe_id
        or source_work.source_campaign_id != source_archive.source_campaign_id
        or source_work.source_campaign_verification_id
        != source_archive.source_campaign_verification_id
        or source_work.source_archive_id != source_archive.upstream_source_archive_id
        or source_work.production_archive_verification_id
        != source_archive.production_archive_verification_id
        or source_work.independent_archive_attestation_id
        != source_archive.independent_archive_attestation_id
        or source_work.source_archive_component_id
        != source_archive.source_archive_component_id
        or source_work.campaign_counters.counters_id
        != source_archive.ordered_commitments.campaign_counters_id
        or reference.source_recipe_id != source_work.source_recipe_id
        or reference.source_campaign_id != source_work.source_campaign_id
        or reference.source_campaign_verification_id
        != source_work.source_campaign_verification_id
        or reference.source_campaign_counters_id
        != source_work.campaign_counters.counters_id
        or work_verification.source_recipe_id != source_work.source_recipe_id
        or work_verification.source_campaign_id != source_work.source_campaign_id
        or work_verification.campaign_counters_id
        != source_work.campaign_counters.counters_id
        or work_verification.materialization_id
        != source_work.materialization_id
        or work_verification.recomputed_materialization_id
        != source_work.materialization_id
        or work_verification.materialization_bytes_sha256
        != hashlib.sha256(source_work.canonical_bytes).hexdigest()
        or source_work.to_document()["counter_completeness_claimed"] is not False
        or source_work.to_document()["economics_available"] is not False
        or source_work.to_document()["target_execution_allowed"] is not False
    ):
        _fail("source offline work is transplanted, stale, or unverified")


@dataclass(frozen=True, slots=True)
class V075SourcePriorAdapterV1:
    _issuer: object = field(repr=False, compare=False)
    catalogue: V075SourcePriorCatalogueV1
    source_offline_work_materialization_id: str
    source_offline_work_verification_id: str
    source_campaign_counters_id: str
    _adapter_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.catalogue) is not V075SourcePriorCatalogueV1
        ):
            _fail("source-prior adapters are verified-factory-issued only")
        for value, name in (
            (
                self.source_offline_work_materialization_id,
                "adapter source work materialization",
            ),
            (
                self.source_offline_work_verification_id,
                "adapter source work verification",
            ),
            (
                self.source_campaign_counters_id,
                "adapter source campaign counters",
            ),
        ):
            _cid(value, name)
        if len(
            {
                self.catalogue.catalogue_id,
                self.catalogue.source_archive_id,
                self.catalogue.source_archive_verification_id,
                self.source_offline_work_materialization_id,
                self.source_offline_work_verification_id,
                self.source_campaign_counters_id,
            }
        ) != 6:
            _fail("source-prior adapter aliases incompatible identity roles")
        object.__setattr__(
            self,
            "_adapter_id",
            _content_id("adapter", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_prior_adapter.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "catalogue_id": self.catalogue.catalogue_id,
            "source_recipe_id": self.catalogue.source_recipe_id,
            "source_archive_id": self.catalogue.source_archive_id,
            "source_archive_verification_id": (
                self.catalogue.source_archive_verification_id
            ),
            "source_offline_work_reference_id": (
                self.catalogue.source_offline_work_reference_id
            ),
            "source_offline_work_materialization_id": (
                self.source_offline_work_materialization_id
            ),
            "source_offline_work_verification_id": (
                self.source_offline_work_verification_id
            ),
            "source_campaign_counters_id": (
                self.source_campaign_counters_id
            ),
            "source_replay_snapshot_requirement_id": (
                _snapshot_requirement_id()
            ),
            "required_source_replay_commit": REQUIRED_SOURCE_REPLAY_COMMIT,
            "required_source_replay_tree": REQUIRED_SOURCE_REPLAY_TREE,
            "source_replay_snapshot_reverified_by_adapter": False,
            "replay_and_materialization_same_process_required": True,
            "entry_ids": [item.entry_id for item in self.catalogue.entries],
            "registered_applied_feature_keys": list(
                REGISTERED_APPLIED_FEATURE_KEYS
            ),
            "source_work_reference_only": True,
            "source_work_embedded": False,
            "source_work_zero_claimed": False,
            "source_work_charged_again": False,
            "selector_use_authorized": True,
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
            "target_execution_allowed": False,
            "historical_recipe_reads": 0,
        }

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogue": self.catalogue.to_document(),
            "adapter_id": self.adapter_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def require_applied_feature(
        self,
        feature_key: str,
    ) -> V075SourcePriorEntryV1:
        return self.catalogue.require_applied_feature(feature_key)

def bind_v075_source_prior_adapter_v1(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
    source_work: work_v1.V075SourceOfflineWorkMaterializationV1,
    work_verification: (
        work_v1.V075SourceOfflineWorkMaterializationVerificationV1
    ),
) -> V075SourcePriorAdapterV1:
    """Bind the four exact authorities; accepts no target or caller mapping."""

    catalogue = compile_v075_source_prior_catalogue_v1(
        source_archive,
        archive_verification,
    )
    _verify_work_authorities(
        source_archive,
        source_work,
        work_verification,
    )
    result = V075SourcePriorAdapterV1(
        _ISSUER,
        catalogue,
        source_work.materialization_id,
        work_verification.verification_id,
        source_work.campaign_counters.counters_id,
    )
    if len(result.canonical_bytes) > MAX_CANONICAL_ADAPTER_BYTES:
        _fail("source-prior adapter exceeds its canonical byte cap")
    return result


def _adapter_from_untrusted_document(
    document: Any,
) -> V075SourcePriorAdapterV1:
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "catalogue_id",
            "source_recipe_id",
            "source_archive_id",
            "source_archive_verification_id",
            "source_offline_work_reference_id",
            "source_offline_work_materialization_id",
            "source_offline_work_verification_id",
            "source_campaign_counters_id",
            "source_replay_snapshot_requirement_id",
            "required_source_replay_commit",
            "required_source_replay_tree",
            "source_replay_snapshot_reverified_by_adapter",
            "replay_and_materialization_same_process_required",
            "entry_ids",
            "registered_applied_feature_keys",
            "source_work_reference_only",
            "source_work_embedded",
            "source_work_zero_claimed",
            "source_work_charged_again",
            "selector_use_authorized",
            "source_only",
            "proposal_only",
            "may_certify",
            "target_execution_allowed",
            "historical_recipe_reads",
            "catalogue",
            "adapter_id",
        },
        field_name="source-prior adapter",
    )
    if (
        item["schema"] != "acfqp.v075_source_prior_adapter.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["registered_applied_feature_keys"]
        != list(REGISTERED_APPLIED_FEATURE_KEYS)
        or item["source_replay_snapshot_requirement_id"]
        != _snapshot_requirement_id()
        or item["required_source_replay_commit"]
        != REQUIRED_SOURCE_REPLAY_COMMIT
        or item["required_source_replay_tree"]
        != REQUIRED_SOURCE_REPLAY_TREE
        or item["source_replay_snapshot_reverified_by_adapter"] is not False
        or item["replay_and_materialization_same_process_required"] is not True
        or item["source_work_reference_only"] is not True
        or item["source_work_embedded"] is not False
        or item["source_work_zero_claimed"] is not False
        or item["source_work_charged_again"] is not False
        or item["selector_use_authorized"] is not True
        or item["source_only"] is not True
        or item["proposal_only"] is not True
        or item["may_certify"] is not False
        or item["target_execution_allowed"] is not False
        or item["historical_recipe_reads"] != 0
        or type(item["entry_ids"]) is not list
    ):
        _fail("source-prior adapter contract changed")
    catalogue = V075SourcePriorCatalogueV1.from_document(item["catalogue"])
    result = V075SourcePriorAdapterV1(
        _ISSUER,
        catalogue,
        item["source_offline_work_materialization_id"],
        item["source_offline_work_verification_id"],
        item["source_campaign_counters_id"],
    )
    if (
        item["catalogue_id"] != catalogue.catalogue_id
        or item["source_recipe_id"] != catalogue.source_recipe_id
        or item["source_archive_id"] != catalogue.source_archive_id
        or item["source_archive_verification_id"]
        != catalogue.source_archive_verification_id
        or item["source_offline_work_reference_id"]
        != catalogue.source_offline_work_reference_id
        or item["entry_ids"] != [value.entry_id for value in catalogue.entries]
        or result.adapter_id
        != _cid(item["adapter_id"], "source-prior adapter")
    ):
        _fail("source-prior adapter references or identity changed")
    return result


def load_v075_source_prior_adapter_v1(
    raw: bytes,
    *,
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
    source_work: work_v1.V075SourceOfflineWorkMaterializationV1,
    work_verification: (
        work_v1.V075SourceOfflineWorkMaterializationVerificationV1
    ),
) -> V075SourcePriorAdapterV1:
    """Load only by rebuilding from all four exact source authorities."""

    recomputed = bind_v075_source_prior_adapter_v1(
        source_archive,
        archive_verification,
        source_work,
        work_verification,
    )
    result = _adapter_from_untrusted_document(
        _strict_load(raw, maximum_bytes=MAX_CANONICAL_ADAPTER_BYTES)
    )
    if (
        result.adapter_id != recomputed.adapter_id
        or result.canonical_bytes != recomputed.canonical_bytes
        or result.canonical_bytes != raw
    ):
        _fail("source-prior adapter differs from exact source authorities")
    return result


@dataclass(frozen=True, slots=True)
class V075SourcePriorAdapterVerificationV1:
    adapter_id: str
    recomputed_adapter_id: str
    catalogue_id: str
    source_archive_id: str
    source_archive_verification_id: str
    source_work_materialization_id: str
    source_work_verification_id: str
    adapter_bytes_sha256: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = tuple(
            _cid(value, name)
            for value, name in (
                (self.adapter_id, "verified source-prior adapter"),
                (self.recomputed_adapter_id, "recomputed source-prior adapter"),
                (self.catalogue_id, "verified source-prior catalogue"),
                (self.source_archive_id, "verified source archive"),
                (
                    self.source_archive_verification_id,
                    "verified archive verification",
                ),
                (
                    self.source_work_materialization_id,
                    "verified source work materialization",
                ),
                (
                    self.source_work_verification_id,
                    "verified source work verification",
                ),
                (self.adapter_bytes_sha256, "source-prior adapter byte digest"),
            )
        )
        if (
            self.adapter_id != self.recomputed_adapter_id
            or len(set(values[0:1] + values[2:7])) != 6
        ):
            _fail("source-prior adapter verification is role-confused")
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_prior_adapter_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "adapter_id": self.adapter_id,
            "recomputed_adapter_id": self.recomputed_adapter_id,
            "catalogue_id": self.catalogue_id,
            "source_archive_id": self.source_archive_id,
            "source_archive_verification_id": (
                self.source_archive_verification_id
            ),
            "source_work_materialization_id": (
                self.source_work_materialization_id
            ),
            "source_work_verification_id": (
                self.source_work_verification_id
            ),
            "adapter_bytes_sha256": self.adapter_bytes_sha256,
            "claimed_values_guided_recomputation": False,
            "historical_recipe_reads": 0,
            "source_work_recharged": False,
            "target_execution_allowed": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_source_prior_adapter_independently_v1(
    *,
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
    source_work: work_v1.V075SourceOfflineWorkMaterializationV1,
    work_verification: (
        work_v1.V075SourceOfflineWorkMaterializationVerificationV1
    ),
    claimed: V075SourcePriorAdapterV1,
) -> V075SourcePriorAdapterVerificationV1:
    if type(claimed) is not V075SourcePriorAdapterV1:
        _fail("adapter verifier requires the exact claimed adapter type")
    recomputed = bind_v075_source_prior_adapter_v1(
        source_archive,
        archive_verification,
        source_work,
        work_verification,
    )
    if (
        claimed.adapter_id != recomputed.adapter_id
        or claimed.canonical_bytes != recomputed.canonical_bytes
    ):
        _fail("claimed source-prior adapter differs from source authorities")
    return V075SourcePriorAdapterVerificationV1(
        claimed.adapter_id,
        recomputed.adapter_id,
        claimed.catalogue.catalogue_id,
        claimed.catalogue.source_archive_id,
        claimed.catalogue.source_archive_verification_id,
        claimed.source_offline_work_materialization_id,
        claimed.source_offline_work_verification_id,
        hashlib.sha256(claimed.canonical_bytes).hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class V075SourcePriorProductionStatusV1:
    catalogue_id: str
    source_archive_id: str
    source_archive_verification_id: str
    expected_source_campaign_counters_id: str
    _status_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        values = tuple(
            _cid(value, name)
            for value, name in (
                (self.catalogue_id, "production source-prior catalogue"),
                (self.source_archive_id, "production source archive"),
                (
                    self.source_archive_verification_id,
                    "production archive verification",
                ),
                (
                    self.expected_source_campaign_counters_id,
                    "expected source campaign counters",
                ),
            )
        )
        if len(set(values)) != 4:
            _fail("production source-prior status aliases identity roles")
        object.__setattr__(
            self,
            "_status_id",
            _content_id("production_status", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_prior_production_status.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "catalogue_id": self.catalogue_id,
            "source_archive_id": self.source_archive_id,
            "source_archive_verification_id": (
                self.source_archive_verification_id
            ),
            "expected_source_campaign_counters_id": (
                self.expected_source_campaign_counters_id
            ),
            "source_replay_snapshot_requirement_id": (
                _snapshot_requirement_id()
            ),
            "required_source_replay_commit": REQUIRED_SOURCE_REPLAY_COMMIT,
            "required_source_replay_tree": REQUIRED_SOURCE_REPLAY_TREE,
            "clean_detached_worktree_required": True,
            "replay_and_materialization_same_process_required": True,
            "current_checkout_replay_allowed": False,
            "replay_allowed_only_at_required_snapshot": True,
            "source_replay_snapshot_status": "NOT_RUN",
            "source_replay_snapshot_attestation_id": None,
            "production_adapter_status": PRODUCTION_ADAPTER_STATUS,
            "source_work_materialization_id": None,
            "source_work_verification_id": None,
            "adapter_id": None,
            "selector_use_authorized": False,
            "historical_recipe_reads_by_adapter": 0,
            "target_execution_allowed": False,
        }

    @property
    def status_id(self) -> str:
        return self._status_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "status_id": self.status_id}


def freeze_v075_source_prior_production_status_v1(
    source_archive: archive_v1.V075FrozenSourceProposalArchiveV1,
    archive_verification: (
        archive_v1.V075FrozenSourceProposalArchiveVerificationV1
    ),
) -> V075SourcePriorProductionStatusV1:
    catalogue = compile_v075_source_prior_catalogue_v1(
        source_archive,
        archive_verification,
    )
    return V075SourcePriorProductionStatusV1(
        catalogue.catalogue_id,
        source_archive.archive_id,
        archive_verification.verification_id,
        source_archive.ordered_commitments.campaign_counters_id,
    )


__all__ = [
    "DOMAIN_TAGS",
    "MAX_CANONICAL_ADAPTER_BYTES",
    "MAX_CANONICAL_CATALOGUE_BYTES",
    "PROFILE_KEY",
    "PRODUCTION_ADAPTER_STATUS",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_SOURCE_REPLAY_COMMIT",
    "REQUIRED_SOURCE_REPLAY_TREE",
    "REGISTERED_APPLIED_FEATURE_KEYS",
    "REGISTERED_NONAPPLIED_FEATURE_KEYS",
    "REGISTERED_SOURCE_FEATURE_SCHEMA_ID",
    "REGISTERED_SOURCE_PROPOSAL_ARCHIVE_ID",
    "REGISTERED_SOURCE_PROPOSAL_ARCHIVE_VERIFICATION_ID",
    "REGISTERED_SOURCE_RECIPE_BYTES_SHA256",
    "REGISTERED_SOURCE_CONSENSUS",
    "REGISTERED_SOURCE_FEATURE_KEYS",
    "SCHEMA_VERSION",
    "V075SourcePriorAdapterV1",
    "V075SourcePriorAdapterVerificationV1",
    "V075SourcePriorAdapterViolation",
    "V075SourcePriorCatalogueV1",
    "V075SourcePriorEntryV1",
    "V075SourcePriorProductionStatusV1",
    "bind_v075_source_prior_adapter_v1",
    "compile_v075_source_prior_catalogue_v1",
    "freeze_v075_source_prior_production_status_v1",
    "load_v075_source_prior_adapter_v1",
    "load_v075_source_prior_catalogue_v1",
    "verify_v075_source_prior_adapter_independently_v1",
]
