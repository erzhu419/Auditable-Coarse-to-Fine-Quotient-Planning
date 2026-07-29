"""Frozen proposal-only source boundary for the fresh V0-075 campaign.

The operational target path must not reconstruct the historical source
campaign.  This module reads exactly one tracked, canonical V0-072 source
recipe and compiles the small proposal surface needed by a future V0-075
selector:

* all seven source-consensus summaries;
* the three ``APPLIED`` feature-to-midrank entries;
* the complete ordered source commitments;
* every upstream source/archive verification identity; and
* a nonzero-by-reference source-offline work obligation.

No target observation, result, certificate, cache, transition law, or caller
proposal enters the compiler.  The archive is proposal-only and cannot mint a
plan or any other scientific conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping, Sequence

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v072_source_reconstruction_recipe_v1 as v072_recipe


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_frozen_source_proposal_archive_v1"
TRACKED_SOURCE_RECIPE_RELATIVE_PATH = Path(
    "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
)
MAX_COMPILED_ARCHIVE_BYTES = 2 * 1024 * 1024

EXPECTED_SOURCE_RECIPE_ID = (
    "7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1"
)
EXPECTED_SOURCE_CAMPAIGN_ID = (
    "f13ce791b6a50f1f8152d4727d062d47629518636f01c71008c0f0cc9fd649d0"
)
EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID = (
    "fa04bbd41693e870adc2ae538b42c6791575818e355017b673e94d27d8829c73"
)
EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID = (
    "16b383ff8fd9ce3ec52737c9e68c079f2e908be4f9abd07ac4c4b41c16a9c7be"
)
EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID = (
    "000c8630a569e8ee225724cb4708d2d0e43b66ae3f61820d1624ee40a5ca394e"
)
EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID = (
    "f1892c934776d5601146b4b1fddbdcebb9dd4bb146f164ad3538c704633a6c34"
)
EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID = (
    "1b8e28bad911237cfaea535a02d4e9a9cf9c47bcaf40b9cd28a6ad26d1d537b9"
)
EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID = (
    "b487bcdb7642ba0e169e81e0a6550915e201604728b8e3fb6350ae6849cc391a"
)
OFFLINE_WORK_MATERIALIZATION_STATUS = "IDENTITY_BOUND_REPLAY_REQUIRED"

EXPECTED_ORDERED_COMMITMENTS = {
    "context_results": {
        "role": "CONTEXT_RESULT_IDS",
        "count": 3,
        "ordered_merkle_root": (
            "b0b6de144a98053fede24743ac2596b0bf91686b3694616510491a2d39888c1e"
        ),
    },
    "replayed_source_rows": {
        "role": "REPLAYED_SOURCE_ROW_IDS",
        "count": 223,
        "ordered_merkle_root": (
            "836fb835858cce992c2428c995d8f2da51840436564378481c76e2e659b6def0"
        ),
    },
    "archive_adjacent_pairs": {
        "role": "ARCHIVE_ADJACENT_PAIR_IDS",
        "count": 7,
        "ordered_merkle_root": (
            "bc56724c07fe9c50f08bc0a61ecf455eee81900b29d8f919c09b47641e161b00"
        ),
    },
    "archive_trials": {
        "role": "ARCHIVE_TRIAL_IDS",
        "count": 137,
        "ordered_merkle_root": (
            "21c6ac962d1f8717982dec764619a6d411a39527d5230eeb471ce873f10da1bd"
        ),
    },
    "archive_feature_consensus": {
        "role": "ARCHIVE_FEATURE_CONSENSUS_IDS",
        "count": 7,
        "ordered_merkle_root": (
            "c6104d1e1a1a4c9ed5f017ebc73e82f0f19bab635fb40b25db10e1930a529899"
        ),
    },
    "family_manifest_id": (
        "bae77aeca2178dea0da44cb339274bb585be6f4518c8ee43ab05b3de3827fca7"
    ),
    "family_authority_id": (
        "16117fd39086feb46c21f087bdad6e4b6a48cb119c429d000e559901d1c80925"
    ),
    "campaign_counters_id": EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID,
}

_MERKLE_KEYS = (
    "context_results",
    "replayed_source_rows",
    "archive_adjacent_pairs",
    "archive_trials",
    "archive_feature_consensus",
)
_UPSTREAM_ARCHIVE_DOCUMENT_DIGEST_DOMAIN = (
    b"acfqp:v072-independent-archive-document:v2\x00"
)
_V072_ARCHIVE_DOMAIN_PREFIX = (
    "acfqp:verified-source-acquisition-archive:"
)
_V072_INDEPENDENT_DOMAIN_PREFIX = (
    "acfqp:verified-source-acquisition-archive-independent-verifier:"
)
_V072_COMPONENT_DOMAIN = "acfqp:v072-verified-source-archive-component:v1"
_V072_MERKLE_LEAF_DOMAIN = (
    b"acfqp:v072-source-recipe-merkle-leaf:v1\x00"
)
_V072_MERKLE_NODE_DOMAIN = (
    b"acfqp:v072-source-recipe-merkle-node:v1\x00"
)

DOMAIN_TAGS = {
    "consensus_summary": (
        "acfqp:v075-frozen-source-consensus-summary:v1"
    ),
    "applied_lookup": (
        "acfqp:v075-frozen-source-applied-proposal-lookup:v1"
    ),
    "ordered_commitment": (
        "acfqp:v075-frozen-source-ordered-commitment:v1"
    ),
    "ordered_commitments": (
        "acfqp:v075-frozen-source-ordered-commitments:v1"
    ),
    "offline_work": (
        "acfqp:v075-frozen-source-offline-work-reference:v1"
    ),
    "archive": "acfqp:v075-frozen-source-proposal-archive:v1",
    "verification": (
        "acfqp:v075-frozen-source-proposal-archive-verification:v1"
    ),
}

_FORBIDDEN_FIELD_FRAGMENTS = (
    "target",
    "result",
    "certificate",
    "cache",
)


class V075FrozenSourceProposalArchiveViolation(ValueError):
    """The tracked recipe or compiled source boundary failed closed."""


def _fail(message: str) -> None:
    raise V075FrozenSourceProposalArchiveViolation(message)


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V075FrozenSourceProposalArchiveViolation(str(error)) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _legacy_content_id(
    domain: str,
    payload: Mapping[str, Any],
) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075FrozenSourceProposalArchiveViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field_name} must be one canonical nonempty string")
    return value


def _exact_dict(
    value: Any,
    *,
    keys: set[str],
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field_name} has an invalid field set")
    return value


def _fraction_from_document(
    value: Any,
    field_name: str,
) -> Fraction:
    # ``loads_canonical_json`` decodes the canonical
    # ``{"numerator", "denominator"}`` form back to ``Fraction``.  The
    # tracked V0-072 recipe exposes the same value as its document form, so
    # both exact representations meet this boundary.
    if type(value) is Fraction:
        return value
    item = _exact_dict(
        value,
        keys={"numerator", "denominator"},
        field_name=field_name,
    )
    if (
        type(item["numerator"]) is not int
        or type(item["denominator"]) is not int
        or item["denominator"] <= 0
    ):
        _fail(f"{field_name} is not an exact rational")
    result = Fraction(item["numerator"], item["denominator"])
    if (
        result.numerator != item["numerator"]
        or result.denominator != item["denominator"]
    ):
        _fail(f"{field_name} is not reduced")
    return result


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("source proposal arithmetic must use exact Fractions")
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _forbidden_field_scan(value: Any) -> None:
    if type(value) is list:
        for item in value:
            _forbidden_field_scan(item)
        return
    if type(value) is not dict:
        return
    for key, item in value.items():
        normalized = key.lower().replace("-", "_")
        if normalized == "target_execution_allowed":
            if item is not False:
                _fail("source archive must forbid target execution")
            continue
        if any(fragment in normalized for fragment in _FORBIDDEN_FIELD_FRAGMENTS):
            _fail("compiled source archive contains a forbidden field")
        _forbidden_field_scan(item)


def _strict_load(raw: Any) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_COMPILED_ARCHIVE_BYTES
    ):
        _fail("compiled source archive bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075FrozenSourceProposalArchiveViolation(
            "compiled source archive is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("compiled source archive bytes are not one canonical object")
    _forbidden_field_scan(document)
    return document


def _read_regular_file(path: Path) -> bytes:
    if not path.is_absolute() or path.is_symlink():
        _fail("tracked source recipe path is relative or linked")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise V075FrozenSourceProposalArchiveViolation(
            "tracked source recipe cannot be opened"
        ) from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            _fail("tracked source recipe is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _repository_root(value: str | os.PathLike[str]) -> Path:
    root = Path(value)
    if (
        not root.is_absolute()
        or not root.is_dir()
        or root.is_symlink()
        or root.resolve(strict=True) != root
    ):
        _fail("repository root must be one absolute real directory")
    recipe = root / TRACKED_SOURCE_RECIPE_RELATIVE_PATH
    if recipe.parent.is_symlink() or recipe.parent.resolve(strict=True) != (
        root / "specs"
    ):
        _fail("tracked source recipe parent is not the repository specs directory")
    return root


def _load_tracked_recipe(
    repository_root: str | os.PathLike[str],
) -> tuple[bytes, dict[str, Any]]:
    root = _repository_root(repository_root)
    path = root / TRACKED_SOURCE_RECIPE_RELATIVE_PATH
    try:
        recipe = v072_recipe.load_source_reconstruction_recipe_v1(path)
        rendered = v072_recipe.render_source_reconstruction_recipe_v1(recipe)
    except (
        OSError,
        ValueError,
        v072_recipe.V072SourceReconstructionRecipeInvariantViolation,
    ) as error:
        raise V075FrozenSourceProposalArchiveViolation(
            "tracked V0-072 source recipe failed strict replay"
        ) from error
    raw = _read_regular_file(path)
    if (
        raw != rendered
        or recipe.recipe_id != EXPECTED_SOURCE_RECIPE_ID
        or recipe.replay_ready is not True
    ):
        _fail("tracked source recipe bytes or pinned identity changed")
    document = recipe.to_document()
    if canonical_json_bytes(document) != raw:
        _fail("tracked source recipe canonical bytes changed after replay")
    return raw, document


def _legacy_archive_id(document: Mapping[str, Any]) -> str:
    excluded = {
        "adjacent_pairs",
        "trials",
        "context_feature_aggregates",
        "consensus",
        "archive_id",
    }
    payload = {
        key: value for key, value in document.items() if key not in excluded
    }
    return _legacy_content_id(
        _V072_ARCHIVE_DOMAIN_PREFIX + "archive:v2",
        payload,
    )


def _legacy_archive_verification_id(
    document: Mapping[str, Any],
) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "verification_id"
    }
    return _legacy_content_id(
        _V072_ARCHIVE_DOMAIN_PREFIX + "archive-verification:v2",
        payload,
    )


def _legacy_independent_attestation_id(
    document: Mapping[str, Any],
) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "verification_id"
    }
    return _legacy_content_id(
        _V072_INDEPENDENT_DOMAIN_PREFIX + "verification:v2",
        payload,
    )


def _legacy_component_id(document: Mapping[str, Any]) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "component_id"
    }
    return _legacy_content_id(_V072_COMPONENT_DOMAIN, payload)


def _legacy_consensus_id(document: Mapping[str, Any]) -> str:
    payload = {
        key: value for key, value in document.items()
        if key != "consensus_id"
    }
    return _legacy_content_id(
        _V072_ARCHIVE_DOMAIN_PREFIX + "feature-consensus:v2",
        payload,
    )


def _legacy_merkle(
    values: Sequence[str],
    *,
    role: str,
) -> dict[str, Any]:
    ordered = tuple(_cid(item, role) for item in values)
    leaves = [
        hashlib.sha256(
            _V072_MERKLE_LEAF_DOMAIN
            + role.encode("utf-8")
            + b"\x00"
            + index.to_bytes(8, "big")
            + bytes.fromhex(value)
        ).digest()
        for index, value in enumerate(ordered)
    ]
    if not leaves:
        root = hashlib.sha256(
            _V072_MERKLE_NODE_DOMAIN
            + role.encode("utf-8")
            + b"\x00EMPTY"
        ).hexdigest()
    else:
        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level = [*level, level[-1]]
            level = [
                hashlib.sha256(
                    _V072_MERKLE_NODE_DOMAIN
                    + level[index]
                    + level[index + 1]
                ).digest()
                for index in range(0, len(level), 2)
            ]
        root = level[0].hex()
    return {
        "role": role,
        "count": len(ordered),
        "ordered_merkle_root": root,
    }


@dataclass(frozen=True, slots=True)
class V075SourceConsensusSummaryV1:
    ordinal: int
    consensus_id: str
    feature_key: str
    disposition: str
    mean_midrank: Fraction
    source_context_ids: tuple[str, ...]
    aggregate_ids: tuple[str, ...]
    _summary_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.ordinal) is not int or self.ordinal not in range(7):
            _fail("source consensus ordinal is outside the frozen seven entries")
        for value, name in (
            (self.consensus_id, "source consensus"),
            (self.feature_key, "source feature"),
            *((item, "source context") for item in self.source_context_ids),
            *((item, "source aggregate") for item in self.aggregate_ids),
        ):
            _cid(value, name)
        if (
            self.disposition not in {"APPLIED", "INSUFFICIENT_CONTEXTS"}
            or type(self.mean_midrank) is not Fraction
            or not 0 <= self.mean_midrank <= 1
            or type(self.source_context_ids) is not tuple
            or not self.source_context_ids
            or self.source_context_ids
            != tuple(sorted(set(self.source_context_ids)))
            or type(self.aggregate_ids) is not tuple
            or not self.aggregate_ids
            or self.aggregate_ids != tuple(sorted(set(self.aggregate_ids)))
        ):
            _fail("source consensus summary is malformed")
        object.__setattr__(
            self,
            "_summary_id",
            _content_id("consensus_summary", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_consensus_summary.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ordinal": self.ordinal,
            "consensus_id": self.consensus_id,
            "feature_key": self.feature_key,
            "disposition": self.disposition,
            "mean_midrank": _fraction_document(self.mean_midrank),
            "source_context_ids": list(self.source_context_ids),
            "aggregate_ids": list(self.aggregate_ids),
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
        }

    @property
    def summary_id(self) -> str:
        return self._summary_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "summary_id": self.summary_id}

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> "V075SourceConsensusSummaryV1":
        item = _exact_dict(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "ordinal",
                "consensus_id",
                "feature_key",
                "disposition",
                "mean_midrank",
                "source_context_ids",
                "aggregate_ids",
                "source_only",
                "proposal_only",
                "may_certify",
                "summary_id",
            },
            field_name="source consensus summary",
        )
        if (
            item["schema"] != "acfqp.v075_source_consensus_summary.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["source_only"] is not True
            or item["proposal_only"] is not True
            or item["may_certify"] is not False
            or type(item["source_context_ids"]) is not list
            or type(item["aggregate_ids"]) is not list
        ):
            _fail("source consensus summary contract changed")
        result = cls(
            item["ordinal"],
            item["consensus_id"],
            item["feature_key"],
            item["disposition"],
            _fraction_from_document(item["mean_midrank"], "mean midrank"),
            tuple(item["source_context_ids"]),
            tuple(item["aggregate_ids"]),
        )
        if result.summary_id != _cid(item["summary_id"], "summary"):
            _fail("source consensus summary identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075AppliedProposalLookupV1:
    ordinal: int
    source_consensus_ordinal: int
    consensus_id: str
    feature_key: str
    mean_midrank: Fraction
    _lookup_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal not in range(3)
            or type(self.source_consensus_ordinal) is not int
            or self.source_consensus_ordinal not in range(7)
            or type(self.mean_midrank) is not Fraction
            or not 0 <= self.mean_midrank <= 1
        ):
            _fail("applied source proposal lookup is malformed")
        _cid(self.consensus_id, "applied source consensus")
        _cid(self.feature_key, "applied source feature")
        object.__setattr__(
            self,
            "_lookup_id",
            _content_id("applied_lookup", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_applied_source_proposal_lookup.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ordinal": self.ordinal,
            "source_consensus_ordinal": self.source_consensus_ordinal,
            "consensus_id": self.consensus_id,
            "feature_key": self.feature_key,
            "mean_midrank": _fraction_document(self.mean_midrank),
            "disposition": "APPLIED",
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
        }

    @property
    def lookup_id(self) -> str:
        return self._lookup_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "lookup_id": self.lookup_id}

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> "V075AppliedProposalLookupV1":
        item = _exact_dict(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "ordinal",
                "source_consensus_ordinal",
                "consensus_id",
                "feature_key",
                "mean_midrank",
                "disposition",
                "source_only",
                "proposal_only",
                "may_certify",
                "lookup_id",
            },
            field_name="applied source proposal lookup",
        )
        if (
            item["schema"]
            != "acfqp.v075_applied_source_proposal_lookup.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["disposition"] != "APPLIED"
            or item["source_only"] is not True
            or item["proposal_only"] is not True
            or item["may_certify"] is not False
        ):
            _fail("applied source proposal lookup contract changed")
        result = cls(
            item["ordinal"],
            item["source_consensus_ordinal"],
            item["consensus_id"],
            item["feature_key"],
            _fraction_from_document(item["mean_midrank"], "applied midrank"),
        )
        if result.lookup_id != _cid(item["lookup_id"], "applied lookup"):
            _fail("applied source proposal lookup identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075OrderedMerkleCommitmentV1:
    name: str
    role: str
    count: int
    ordered_merkle_root: str
    _commitment_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _token(self.name, "ordered commitment name")
        _token(self.role, "ordered commitment role")
        _cid(self.ordered_merkle_root, "ordered commitment root")
        expected = EXPECTED_ORDERED_COMMITMENTS.get(self.name)
        if (
            self.name not in _MERKLE_KEYS
            or type(self.count) is not int
            or self.count <= 0
            or type(expected) is not dict
            or self.to_upstream_document() != expected
        ):
            _fail("ordered source commitment differs from the pinned recipe")
        object.__setattr__(
            self,
            "_commitment_id",
            _content_id("ordered_commitment", self._payload()),
        )

    def to_upstream_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "count": self.count,
            "ordered_merkle_root": self.ordered_merkle_root,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_ordered_commitment.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "name": self.name,
            **self.to_upstream_document(),
        }

    @property
    def commitment_id(self) -> str:
        return self._commitment_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> "V075OrderedMerkleCommitmentV1":
        item = _exact_dict(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "name",
                "role",
                "count",
                "ordered_merkle_root",
                "commitment_id",
            },
            field_name="ordered source commitment",
        )
        if (
            item["schema"] != "acfqp.v075_source_ordered_commitment.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
        ):
            _fail("ordered source commitment contract changed")
        result = cls(
            item["name"],
            item["role"],
            item["count"],
            item["ordered_merkle_root"],
        )
        if result.commitment_id != _cid(
            item["commitment_id"],
            "ordered source commitment",
        ):
            _fail("ordered source commitment identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075OrderedSourceCommitmentsV1:
    merkle_commitments: tuple[V075OrderedMerkleCommitmentV1, ...]
    family_manifest_id: str
    family_authority_id: str
    campaign_counters_id: str
    _commitments_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.family_manifest_id, "source family manifest"),
            (self.family_authority_id, "source family authority"),
            (self.campaign_counters_id, "source campaign counters"),
        ):
            _cid(value, name)
        if (
            type(self.merkle_commitments) is not tuple
            or tuple(item.name for item in self.merkle_commitments)
            != _MERKLE_KEYS
            or any(
                type(item) is not V075OrderedMerkleCommitmentV1
                for item in self.merkle_commitments
            )
            or self.to_upstream_document() != EXPECTED_ORDERED_COMMITMENTS
        ):
            _fail("complete ordered source commitments changed")
        object.__setattr__(
            self,
            "_commitments_id",
            _content_id("ordered_commitments", self._payload()),
        )

    def to_upstream_document(self) -> dict[str, Any]:
        return {
            **{
                item.name: item.to_upstream_document()
                for item in self.merkle_commitments
            },
            "family_manifest_id": self.family_manifest_id,
            "family_authority_id": self.family_authority_id,
            "campaign_counters_id": self.campaign_counters_id,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_ordered_commitments.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "commitment_ids": [
                item.commitment_id for item in self.merkle_commitments
            ],
            "family_manifest_id": self.family_manifest_id,
            "family_authority_id": self.family_authority_id,
            "campaign_counters_id": self.campaign_counters_id,
            "source_only": True,
        }

    @property
    def commitments_id(self) -> str:
        return self._commitments_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "merkle_commitments": [
                item.to_document() for item in self.merkle_commitments
            ],
            "commitments_id": self.commitments_id,
        }

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> "V075OrderedSourceCommitmentsV1":
        item = _exact_dict(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "commitment_ids",
                "family_manifest_id",
                "family_authority_id",
                "campaign_counters_id",
                "source_only",
                "merkle_commitments",
                "commitments_id",
            },
            field_name="complete ordered source commitments",
        )
        if (
            item["schema"] != "acfqp.v075_source_ordered_commitments.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["source_only"] is not True
            or type(item["merkle_commitments"]) is not list
            or type(item["commitment_ids"]) is not list
        ):
            _fail("complete ordered source commitments contract changed")
        merkle = tuple(
            V075OrderedMerkleCommitmentV1.from_document(value)
            for value in item["merkle_commitments"]
        )
        result = cls(
            merkle,
            item["family_manifest_id"],
            item["family_authority_id"],
            item["campaign_counters_id"],
        )
        if (
            item["commitment_ids"]
            != [value.commitment_id for value in merkle]
            or result.commitments_id
            != _cid(item["commitments_id"], "ordered commitments")
        ):
            _fail("complete ordered source commitments identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075SourceOfflineWorkReferenceV1:
    source_recipe_id: str
    source_campaign_id: str
    source_campaign_verification_id: str
    source_campaign_counters_id: str
    ordered_commitments_id: str
    _work_reference_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_recipe_id, "offline source recipe"),
            (self.source_campaign_id, "offline source campaign"),
            (
                self.source_campaign_verification_id,
                "offline source campaign verification",
            ),
            (self.source_campaign_counters_id, "offline source counters"),
            (self.ordered_commitments_id, "offline source commitments"),
        ):
            _cid(value, name)
        if (
            self.source_recipe_id != EXPECTED_SOURCE_RECIPE_ID
            or self.source_campaign_id != EXPECTED_SOURCE_CAMPAIGN_ID
            or self.source_campaign_verification_id
            != EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID
            or self.source_campaign_counters_id
            != EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID
            or len(
                {
                    self.source_recipe_id,
                    self.source_campaign_id,
                    self.source_campaign_verification_id,
                    self.source_campaign_counters_id,
                    self.ordered_commitments_id,
                }
            )
            != 5
        ):
            _fail("source offline work reference is stale or role-confused")
        object.__setattr__(
            self,
            "_work_reference_id",
            _content_id("offline_work", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_source_offline_work_reference.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "source_campaign_counters_id": self.source_campaign_counters_id,
            "ordered_commitments_id": self.ordered_commitments_id,
            "lane": "SOURCE_ARCHIVE_OFFLINE",
            "upstream_native_counter_vector_required": True,
            "counter_values_inlined": False,
            "zero_work_claimed": False,
            "offline_work_retained": True,
            "offline_work_materialization_status": (
                OFFLINE_WORK_MATERIALIZATION_STATUS
            ),
            "target_execution_allowed": False,
        }

    @property
    def work_reference_id(self) -> str:
        return self._work_reference_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "work_reference_id": self.work_reference_id,
        }

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> "V075SourceOfflineWorkReferenceV1":
        item = _exact_dict(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "source_recipe_id",
                "source_campaign_id",
                "source_campaign_verification_id",
                "source_campaign_counters_id",
                "ordered_commitments_id",
                "lane",
                "upstream_native_counter_vector_required",
                "counter_values_inlined",
                "zero_work_claimed",
                "offline_work_retained",
                "offline_work_materialization_status",
                "target_execution_allowed",
                "work_reference_id",
            },
            field_name="source offline work reference",
        )
        if (
            item["schema"] != "acfqp.v075_source_offline_work_reference.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["lane"] != "SOURCE_ARCHIVE_OFFLINE"
            or item["upstream_native_counter_vector_required"] is not True
            or item["counter_values_inlined"] is not False
            or item["zero_work_claimed"] is not False
            or item["offline_work_retained"] is not True
            or item["offline_work_materialization_status"]
            != OFFLINE_WORK_MATERIALIZATION_STATUS
            or item["target_execution_allowed"] is not False
        ):
            _fail("source offline work reference contract changed")
        result = cls(
            item["source_recipe_id"],
            item["source_campaign_id"],
            item["source_campaign_verification_id"],
            item["source_campaign_counters_id"],
            item["ordered_commitments_id"],
        )
        if result.work_reference_id != _cid(
            item["work_reference_id"],
            "source offline work reference",
        ):
            _fail("source offline work reference identity changed")
        return result


@dataclass(frozen=True, slots=True)
class V075FrozenSourceProposalArchiveV1:
    source_recipe_id: str
    source_recipe_bytes_sha256: str
    source_campaign_id: str
    source_campaign_verification_id: str
    upstream_source_archive_id: str
    production_archive_verification_id: str
    independent_archive_attestation_id: str
    source_archive_component_id: str
    upstream_archive_document_digest: str
    feature_schema_id: str
    ordered_commitments: V075OrderedSourceCommitmentsV1
    offline_work: V075SourceOfflineWorkReferenceV1
    consensus_summaries: tuple[V075SourceConsensusSummaryV1, ...]
    applied_lookup: tuple[V075AppliedProposalLookupV1, ...]
    _archive_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_recipe_id, "source recipe"),
            (self.source_recipe_bytes_sha256, "source recipe byte digest"),
            (self.source_campaign_id, "source campaign"),
            (
                self.source_campaign_verification_id,
                "source campaign verification",
            ),
            (self.upstream_source_archive_id, "upstream source archive"),
            (
                self.production_archive_verification_id,
                "production archive verification",
            ),
            (
                self.independent_archive_attestation_id,
                "independent archive attestation",
            ),
            (self.source_archive_component_id, "source archive component"),
            (
                self.upstream_archive_document_digest,
                "upstream archive document digest",
            ),
            (self.feature_schema_id, "source feature schema"),
        ):
            _cid(value, name)
        if (
            self.source_recipe_id != EXPECTED_SOURCE_RECIPE_ID
            or self.source_campaign_id != EXPECTED_SOURCE_CAMPAIGN_ID
            or self.source_campaign_verification_id
            != EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID
            or self.upstream_source_archive_id
            != EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID
            or self.production_archive_verification_id
            != EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID
            or self.independent_archive_attestation_id
            != EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID
            or self.source_archive_component_id
            != EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID
            or type(self.ordered_commitments)
            is not V075OrderedSourceCommitmentsV1
            or type(self.offline_work)
            is not V075SourceOfflineWorkReferenceV1
            or self.offline_work.source_recipe_id != self.source_recipe_id
            or self.offline_work.source_campaign_id != self.source_campaign_id
            or self.offline_work.source_campaign_verification_id
            != self.source_campaign_verification_id
            or self.offline_work.source_campaign_counters_id
            != self.ordered_commitments.campaign_counters_id
            or self.offline_work.ordered_commitments_id
            != self.ordered_commitments.commitments_id
            or type(self.consensus_summaries) is not tuple
            or len(self.consensus_summaries) != 7
            or any(
                type(item) is not V075SourceConsensusSummaryV1
                for item in self.consensus_summaries
            )
            or tuple(item.ordinal for item in self.consensus_summaries)
            != tuple(range(7))
            or len(
                {item.consensus_id for item in self.consensus_summaries}
            )
            != 7
            or len({item.feature_key for item in self.consensus_summaries})
            != 7
            or type(self.applied_lookup) is not tuple
            or len(self.applied_lookup) != 3
            or any(
                type(item) is not V075AppliedProposalLookupV1
                for item in self.applied_lookup
            )
            or tuple(item.ordinal for item in self.applied_lookup)
            != tuple(range(3))
        ):
            _fail("frozen source proposal archive is incomplete or stale")
        applied = tuple(
            (
                item.ordinal,
                item.consensus_id,
                item.feature_key,
                item.mean_midrank,
            )
            for item in self.consensus_summaries
            if item.disposition == "APPLIED"
        )
        lookup = tuple(
            (
                item.source_consensus_ordinal,
                item.consensus_id,
                item.feature_key,
                item.mean_midrank,
            )
            for item in self.applied_lookup
        )
        if applied != lookup:
            _fail("applied proposal lookup differs from all APPLIED summaries")
        object.__setattr__(
            self,
            "_archive_id",
            _content_id("archive", self._payload()),
        )
        _forbidden_field_scan(self.to_document())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_frozen_source_proposal_archive.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "source_recipe_bytes_sha256": self.source_recipe_bytes_sha256,
            "source_campaign_id": self.source_campaign_id,
            "source_campaign_verification_id": (
                self.source_campaign_verification_id
            ),
            "upstream_source_archive_id": self.upstream_source_archive_id,
            "production_archive_verification_id": (
                self.production_archive_verification_id
            ),
            "independent_archive_attestation_id": (
                self.independent_archive_attestation_id
            ),
            "source_archive_component_id": self.source_archive_component_id,
            "upstream_archive_document_digest": (
                self.upstream_archive_document_digest
            ),
            "feature_schema_id": self.feature_schema_id,
            "ordered_commitments_id": (
                self.ordered_commitments.commitments_id
            ),
            "offline_work_reference_id": self.offline_work.work_reference_id,
            "consensus_summary_ids": [
                item.summary_id for item in self.consensus_summaries
            ],
            "applied_lookup_ids": [
                item.lookup_id for item in self.applied_lookup
            ],
            "consensus_count": 7,
            "applied_count": 3,
            "source_only": True,
            "proposal_only": True,
            "may_certify": False,
            "target_execution_allowed": False,
            "observer_calls": 0,
            "environment_law_reads": 0,
            "source_campaign_reconstruction_calls": 0,
        }

    @property
    def archive_id(self) -> str:
        return self._archive_id

    @property
    def proposal_midrank_by_feature(self) -> dict[str, Fraction]:
        return {
            item.feature_key: item.mean_midrank
            for item in self.applied_lookup
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "ordered_commitments": self.ordered_commitments.to_document(),
            "offline_work": self.offline_work.to_document(),
            "consensus_summaries": [
                item.to_document() for item in self.consensus_summaries
            ],
            "applied_lookup": [
                item.to_document() for item in self.applied_lookup
            ],
            "archive_id": self.archive_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _validate_upstream_recipe(
    raw_recipe: bytes,
    recipe_document: Mapping[str, Any],
) -> tuple[
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
    V075OrderedSourceCommitmentsV1,
]:
    if (
        recipe_document.get("recipe_id") != EXPECTED_SOURCE_RECIPE_ID
        or canonical_json_bytes(recipe_document) != raw_recipe
    ):
        _fail("source recipe identity or canonical bytes changed")
    expected_outputs = recipe_document.get("expected_output_ids")
    expected_output_values = {
        "source_campaign_id": EXPECTED_SOURCE_CAMPAIGN_ID,
        "source_campaign_verification_id": (
            EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID
        ),
        "source_archive_id": EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID,
        "production_archive_verification_id": (
            EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID
        ),
        "independent_archive_attestation_id": (
            EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID
        ),
        "source_archive_component_id": (
            EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID
        ),
    }
    compact = recipe_document.get("compact_derived_artifacts")
    if (
        expected_outputs != expected_output_values
        or type(compact) is not dict
        or set(compact)
        != {
            "source_archive",
            "production_archive_verification",
            "independent_archive_attestation",
            "source_archive_component_summary",
        }
    ):
        _fail("source recipe upstream identity graph changed")
    archive = compact["source_archive"]
    production = compact["production_archive_verification"]
    independent = compact["independent_archive_attestation"]
    component = compact["source_archive_component_summary"]
    if any(type(value) is not dict for value in compact.values()):
        _fail("source recipe compact artifacts are not canonical objects")
    if (
        archive.get("archive_id") != EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID
        or _legacy_archive_id(archive) != archive["archive_id"]
        or archive.get("source_campaign_id") != EXPECTED_SOURCE_CAMPAIGN_ID
        or archive.get("source_campaign_verification_id")
        != EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID
        or production.get("verification_id")
        != EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID
        or _legacy_archive_verification_id(production)
        != production["verification_id"]
        or production.get("archive_id") != archive["archive_id"]
        or production.get("replayed_archive_id") != archive["archive_id"]
        or independent.get("verification_id")
        != EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID
        or _legacy_independent_attestation_id(independent)
        != independent["verification_id"]
        or independent.get("archive_id") != archive["archive_id"]
        or independent.get("independently_recomputed_archive_id")
        != archive["archive_id"]
        or component.get("component_id")
        != EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID
        or _legacy_component_id(component) != component["component_id"]
        or component.get("archive_id") != archive["archive_id"]
        or component.get("production_verification_id")
        != production["verification_id"]
        or component.get("independent_archive_transform_attestation_id")
        != independent["verification_id"]
    ):
        _fail("source archive production/independent identity chain changed")
    digest = hashlib.sha256(
        _UPSTREAM_ARCHIVE_DOCUMENT_DIGEST_DOMAIN
        + canonical_json_bytes(archive)
    ).hexdigest()
    if independent.get("archive_document_digest") != digest:
        _fail("independent archive document digest differs")

    upstream_commitments = recipe_document.get("ordered_commitments")
    if upstream_commitments != EXPECTED_ORDERED_COMMITMENTS:
        _fail("tracked source ordered commitments changed")
    merkle = tuple(
        V075OrderedMerkleCommitmentV1(
            name,
            upstream_commitments[name]["role"],
            upstream_commitments[name]["count"],
            upstream_commitments[name]["ordered_merkle_root"],
        )
        for name in _MERKLE_KEYS
    )
    commitments = V075OrderedSourceCommitmentsV1(
        merkle,
        upstream_commitments["family_manifest_id"],
        upstream_commitments["family_authority_id"],
        upstream_commitments["campaign_counters_id"],
    )
    for name, values_key in (
        ("archive_adjacent_pairs", "adjacent_pair_ids"),
        ("archive_trials", "trial_ids"),
        ("archive_feature_consensus", "consensus_ids"),
    ):
        values = archive.get(values_key)
        if type(values) is not list:
            _fail(f"source archive {values_key} is not an ordered list")
        replayed = _legacy_merkle(
            values,
            role=upstream_commitments[name]["role"],
        )
        if replayed != upstream_commitments[name]:
            _fail(f"source archive {name} commitment differs")
    return archive, production, independent, component, commitments


def _compile_from_tracked_recipe(
    repository_root: str | os.PathLike[str],
) -> V075FrozenSourceProposalArchiveV1:
    raw, recipe = _load_tracked_recipe(repository_root)
    (
        archive_document,
        _production,
        independent,
        _component,
        commitments,
    ) = _validate_upstream_recipe(raw, recipe)
    consensus_documents = archive_document.get("consensus")
    consensus_ids = archive_document.get("consensus_ids")
    if (
        type(consensus_documents) is not list
        or len(consensus_documents) != 7
        or type(consensus_ids) is not list
        or len(consensus_ids) != 7
    ):
        _fail("source archive does not contain exactly seven consensus entries")
    summaries: list[V075SourceConsensusSummaryV1] = []
    for ordinal, (document, consensus_id) in enumerate(
        zip(consensus_documents, consensus_ids, strict=True)
    ):
        if (
            type(document) is not dict
            or document.get("consensus_id") != consensus_id
            or _legacy_consensus_id(document) != consensus_id
            or type(document.get("source_context_ids")) is not list
            or type(document.get("aggregate_ids")) is not list
        ):
            _fail("source consensus document identity changed")
        summaries.append(
            V075SourceConsensusSummaryV1(
                ordinal,
                consensus_id,
                document.get("feature_key"),
                document.get("disposition"),
                _fraction_from_document(
                    document.get("mean_midrank"),
                    "source consensus mean midrank",
                ),
                tuple(document["source_context_ids"]),
                tuple(document["aggregate_ids"]),
            )
        )
    frozen_summaries = tuple(summaries)
    applied_summaries = tuple(
        item for item in frozen_summaries if item.disposition == "APPLIED"
    )
    if len(applied_summaries) != 3:
        _fail("source proposal does not contain exactly three APPLIED entries")
    applied = tuple(
        V075AppliedProposalLookupV1(
            ordinal,
            summary.ordinal,
            summary.consensus_id,
            summary.feature_key,
            summary.mean_midrank,
        )
        for ordinal, summary in enumerate(applied_summaries)
    )
    offline = V075SourceOfflineWorkReferenceV1(
        EXPECTED_SOURCE_RECIPE_ID,
        EXPECTED_SOURCE_CAMPAIGN_ID,
        EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID,
        commitments.campaign_counters_id,
        commitments.commitments_id,
    )
    result = V075FrozenSourceProposalArchiveV1(
        EXPECTED_SOURCE_RECIPE_ID,
        hashlib.sha256(raw).hexdigest(),
        EXPECTED_SOURCE_CAMPAIGN_ID,
        EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID,
        EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID,
        EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID,
        EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID,
        EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID,
        independent["archive_document_digest"],
        archive_document["feature_schema_id"],
        commitments,
        offline,
        frozen_summaries,
        applied,
    )
    if len(result.canonical_bytes) > MAX_COMPILED_ARCHIVE_BYTES:
        _fail("compiled source proposal archive exceeds its frozen byte cap")
    return result


def compile_v075_frozen_source_proposal_archive_v1(
    repository_root: str | os.PathLike[str],
) -> V075FrozenSourceProposalArchiveV1:
    """Compile only the pinned tracked recipe; no source or target replay."""

    return _compile_from_tracked_recipe(repository_root)


def _archive_from_document(
    document: Mapping[str, Any],
) -> V075FrozenSourceProposalArchiveV1:
    item = _exact_dict(
        document,
        keys={
            "schema",
            "schema_version",
            "proposed_contract_version",
            "profile_key",
            "source_recipe_id",
            "source_recipe_bytes_sha256",
            "source_campaign_id",
            "source_campaign_verification_id",
            "upstream_source_archive_id",
            "production_archive_verification_id",
            "independent_archive_attestation_id",
            "source_archive_component_id",
            "upstream_archive_document_digest",
            "feature_schema_id",
            "ordered_commitments_id",
            "offline_work_reference_id",
            "consensus_summary_ids",
            "applied_lookup_ids",
            "consensus_count",
            "applied_count",
            "source_only",
            "proposal_only",
            "may_certify",
            "target_execution_allowed",
            "observer_calls",
            "environment_law_reads",
            "source_campaign_reconstruction_calls",
            "ordered_commitments",
            "offline_work",
            "consensus_summaries",
            "applied_lookup",
            "archive_id",
        },
        field_name="frozen source proposal archive",
    )
    if (
        item["schema"] != "acfqp.v075_frozen_source_proposal_archive.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["consensus_count"] != 7
        or item["applied_count"] != 3
        or item["source_only"] is not True
        or item["proposal_only"] is not True
        or item["may_certify"] is not False
        or item["target_execution_allowed"] is not False
        or item["observer_calls"] != 0
        or item["environment_law_reads"] != 0
        or item["source_campaign_reconstruction_calls"] != 0
        or type(item["consensus_summaries"]) is not list
        or type(item["applied_lookup"]) is not list
        or type(item["consensus_summary_ids"]) is not list
        or type(item["applied_lookup_ids"]) is not list
    ):
        _fail("frozen source proposal archive contract changed")
    commitments = V075OrderedSourceCommitmentsV1.from_document(
        item["ordered_commitments"]
    )
    offline = V075SourceOfflineWorkReferenceV1.from_document(
        item["offline_work"]
    )
    summaries = tuple(
        V075SourceConsensusSummaryV1.from_document(value)
        for value in item["consensus_summaries"]
    )
    applied = tuple(
        V075AppliedProposalLookupV1.from_document(value)
        for value in item["applied_lookup"]
    )
    result = V075FrozenSourceProposalArchiveV1(
        item["source_recipe_id"],
        item["source_recipe_bytes_sha256"],
        item["source_campaign_id"],
        item["source_campaign_verification_id"],
        item["upstream_source_archive_id"],
        item["production_archive_verification_id"],
        item["independent_archive_attestation_id"],
        item["source_archive_component_id"],
        item["upstream_archive_document_digest"],
        item["feature_schema_id"],
        commitments,
        offline,
        summaries,
        applied,
    )
    if (
        item["ordered_commitments_id"] != commitments.commitments_id
        or item["offline_work_reference_id"] != offline.work_reference_id
        or item["consensus_summary_ids"]
        != [value.summary_id for value in summaries]
        or item["applied_lookup_ids"]
        != [value.lookup_id for value in applied]
        or result.archive_id != _cid(item["archive_id"], "compiled archive")
    ):
        _fail("frozen source proposal archive references or identity changed")
    return result


def load_v075_frozen_source_proposal_archive_v1(
    raw: bytes,
    *,
    expected_archive_id: str,
    expected_source_recipe_id: str,
    expected_offline_work_reference_id: str,
) -> V075FrozenSourceProposalArchiveV1:
    """Strictly load one externally expected, domain-bound archive."""

    document = _strict_load(raw)
    result = _archive_from_document(document)
    expected = (
        _cid(expected_archive_id, "expected compiled archive"),
        _cid(expected_source_recipe_id, "expected source recipe"),
        _cid(
            expected_offline_work_reference_id,
            "expected source offline work",
        ),
    )
    claimed = (
        result.archive_id,
        result.source_recipe_id,
        result.offline_work.work_reference_id,
    )
    if claimed != expected or result.canonical_bytes != raw:
        _fail("compiled source proposal archive external binding changed")
    return result


@dataclass(frozen=True, slots=True)
class V075FrozenSourceProposalArchiveVerificationV1:
    source_recipe_id: str
    archive_id: str
    recomputed_archive_id: str
    archive_bytes_sha256: str
    offline_work_reference_id: str
    consensus_summary_ids: tuple[str, ...]
    applied_lookup_ids: tuple[str, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, name in (
            (self.source_recipe_id, "verified source recipe"),
            (self.archive_id, "verified source archive"),
            (self.recomputed_archive_id, "recomputed source archive"),
            (self.archive_bytes_sha256, "source archive byte digest"),
            (
                self.offline_work_reference_id,
                "verified source offline work",
            ),
            *((item, "verified consensus summary") for item in self.consensus_summary_ids),
            *((item, "verified applied lookup") for item in self.applied_lookup_ids),
        ):
            _cid(value, name)
        if (
            self.source_recipe_id != EXPECTED_SOURCE_RECIPE_ID
            or self.archive_id != self.recomputed_archive_id
            or len(self.consensus_summary_ids) != 7
            or len(set(self.consensus_summary_ids)) != 7
            or len(self.applied_lookup_ids) != 3
            or len(set(self.applied_lookup_ids)) != 3
        ):
            _fail("source proposal verification is incomplete or stale")
        object.__setattr__(
            self,
            "_verification_id",
            _content_id("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_frozen_source_proposal_archive_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recipe_id": self.source_recipe_id,
            "archive_id": self.archive_id,
            "recomputed_archive_id": self.recomputed_archive_id,
            "archive_bytes_sha256": self.archive_bytes_sha256,
            "offline_work_reference_id": self.offline_work_reference_id,
            "consensus_summary_ids": list(self.consensus_summary_ids),
            "applied_lookup_ids": list(self.applied_lookup_ids),
            "tracked_recipe_recompiled": True,
            "claimed_values_guided_recompilation": False,
            "source_campaign_reconstruction_calls": 0,
            "observer_calls": 0,
            "environment_law_reads": 0,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_frozen_source_proposal_archive_independently_v1(
    *,
    repository_root: str | os.PathLike[str],
    claimed: V075FrozenSourceProposalArchiveV1,
) -> V075FrozenSourceProposalArchiveVerificationV1:
    """Recompile from the tracked recipe and compare complete canonical bytes."""

    if type(claimed) is not V075FrozenSourceProposalArchiveV1:
        _fail("source proposal verifier requires the exact archive type")
    recomputed = _compile_from_tracked_recipe(repository_root)
    if (
        recomputed.archive_id != claimed.archive_id
        or recomputed.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("claimed source proposal archive differs from recipe recompilation")
    return V075FrozenSourceProposalArchiveVerificationV1(
        recomputed.source_recipe_id,
        claimed.archive_id,
        recomputed.archive_id,
        hashlib.sha256(claimed.canonical_bytes).hexdigest(),
        claimed.offline_work.work_reference_id,
        tuple(item.summary_id for item in claimed.consensus_summaries),
        tuple(item.lookup_id for item in claimed.applied_lookup),
    )


def verify_v075_frozen_source_proposal_archive_bytes_independently_v1(
    *,
    repository_root: str | os.PathLike[str],
    raw: bytes,
) -> V075FrozenSourceProposalArchiveVerificationV1:
    """Recompile first, then load and verify untrusted archive bytes."""

    recomputed = _compile_from_tracked_recipe(repository_root)
    claimed = load_v075_frozen_source_proposal_archive_v1(
        raw,
        expected_archive_id=recomputed.archive_id,
        expected_source_recipe_id=recomputed.source_recipe_id,
        expected_offline_work_reference_id=(
            recomputed.offline_work.work_reference_id
        ),
    )
    return verify_v075_frozen_source_proposal_archive_independently_v1(
        repository_root=repository_root,
        claimed=claimed,
    )


__all__ = [
    "DOMAIN_TAGS",
    "EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID",
    "EXPECTED_ORDERED_COMMITMENTS",
    "EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID",
    "EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID",
    "EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID",
    "EXPECTED_SOURCE_CAMPAIGN_ID",
    "EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID",
    "EXPECTED_SOURCE_RECIPE_ID",
    "EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID",
    "MAX_COMPILED_ARCHIVE_BYTES",
    "OFFLINE_WORK_MATERIALIZATION_STATUS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TRACKED_SOURCE_RECIPE_RELATIVE_PATH",
    "V075AppliedProposalLookupV1",
    "V075FrozenSourceProposalArchiveV1",
    "V075FrozenSourceProposalArchiveVerificationV1",
    "V075FrozenSourceProposalArchiveViolation",
    "V075OrderedMerkleCommitmentV1",
    "V075OrderedSourceCommitmentsV1",
    "V075SourceConsensusSummaryV1",
    "V075SourceOfflineWorkReferenceV1",
    "compile_v075_frozen_source_proposal_archive_v1",
    "load_v075_frozen_source_proposal_archive_v1",
    "verify_v075_frozen_source_proposal_archive_bytes_independently_v1",
    "verify_v075_frozen_source_proposal_archive_independently_v1",
]
