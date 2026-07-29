"""Compact deterministic reconstruction recipe for the V0-068 source graph.

The recipe persists no raw observation IDs.  A complete recipe binds the
constructor profile, registered public contexts, code/runtime/test trees,
expected campaign/archive/component identities, and ordered Merkle
commitments.  Replay calls the registered campaign and verifier directly;
there is no caller-provided runner, artifact, status, or expected ID.

The small historical mechanics fixture is intentionally incomplete.  It can
exercise canonical recipe I/O, but cannot set ``replay_ready`` and therefore
cannot close the source-persistence blocker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping, Sequence

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import observation_support_graph_acquisition_v1 as acquisition_v1
from acfqp import verified_source_acquisition_archive_v2 as archive_v2
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as independent_v2,
)
from acfqp import v072_verified_source_archive_component_v1 as component_v1
from acfqp import v072_execution_environment_authority_v1 as environment_v1
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as environment_independent_v1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_source_reconstruction_recipe_v1"
RECONSTRUCTION_MAX_WORKERS = 32
MAX_CANONICAL_RECIPE_BYTES = 16 * 1024 * 1024
RECIPE_DOMAIN = "acfqp:v072-source-reconstruction-recipe:v1"
MERKLE_LEAF_DOMAIN = b"acfqp:v072-source-recipe-merkle-leaf:v1\x00"
MERKLE_NODE_DOMAIN = b"acfqp:v072-source-recipe-merkle-node:v1\x00"
INCOMPLETE_BLOCKER = (
    "REAL_SOURCE_RECONSTRUCTION_RECIPE_NOT_FROZEN_AND_REPLAYED"
)
REGISTERED_CONSTRUCTOR = (
    "acfqp.observation_support_campaign_v1."
    "run_observation_support_campaign_v1"
)
REGISTERED_VERIFIER = (
    "acfqp.observation_support_campaign_v1."
    "verify_observation_support_campaign_v1"
)
_ID = re.compile(r"[0-9a-f]{64}")
_ISSUER = object()


class V072SourceReconstructionRecipeInvariantViolation(ValueError):
    """The compact recipe, its environment, or its replay failed."""


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072SourceReconstructionRecipeInvariantViolation(
            f"{field_name} is not one lowercase SHA-256 content ID"
        ) from error


def _recipe_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        RECIPE_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _merkle_commitment(
    values: Sequence[str],
    *,
    role: str,
) -> dict[str, Any]:
    if type(values) not in (tuple, list):
        raise V072SourceReconstructionRecipeInvariantViolation(
            f"{role} values are not ordered"
        )
    ordered = tuple(_cid(item, role) for item in values)
    leaves = [
        hashlib.sha256(
            MERKLE_LEAF_DOMAIN
            + role.encode("utf-8")
            + b"\x00"
            + index.to_bytes(8, "big")
            + bytes.fromhex(value)
        ).digest()
        for index, value in enumerate(ordered)
    ]
    if not leaves:
        root = hashlib.sha256(
            MERKLE_NODE_DOMAIN + role.encode("utf-8") + b"\x00EMPTY"
        ).hexdigest()
    else:
        level = leaves
        while len(level) > 1:
            if len(level) % 2:
                level = [*level, level[-1]]
            level = [
                hashlib.sha256(
                    MERKLE_NODE_DOMAIN + level[index] + level[index + 1]
                ).digest()
                for index in range(0, len(level), 2)
            ]
        root = level[0].hex()
    return {
        "role": role,
        "count": len(ordered),
        "ordered_merkle_root": root,
    }


def _typed_missing(reason: str) -> dict[str, str]:
    return {
        "kind": "NOT_AVAILABLE_IN_MECHANICS_FIXTURE",
        "reason": reason,
    }


def _component_summary(
    component: component_v1.V072VerifiedSourceArchiveComponentV1,
) -> dict[str, Any]:
    document = component.to_document()
    for name in (
        "archive",
        "production_verification",
        "independent_attestation",
    ):
        document.pop(name)
    return document


def _derive_source_commitments(
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
    archive: archive_v2.VerifiedSourceAcquisitionArchiveV2,
) -> tuple[dict[str, Any], bool]:
    complete = True
    try:
        context_result_ids = tuple(
            item.context_result_id for item in source_campaign.context_results
        )
        family_manifest_id: str | dict[str, str] = (
            source_campaign.family_manifest.manifest_id
        )
        family_authority_id: str | dict[str, str] = (
            source_campaign.family_authority.authority_id
        )
        campaign_counters_id: str | dict[str, str] = (
            source_campaign.counters.counters_id
        )
    except AttributeError:
        complete = False
        context_result_ids = ()
        family_manifest_id = _typed_missing(
            "miniature campaign omits the family manifest"
        )
        family_authority_id = _typed_missing(
            "miniature campaign omits the family authority"
        )
        campaign_counters_id = _typed_missing(
            "miniature campaign omits campaign counters"
        )
    replayed_row_ids = tuple(source_verification.replayed_row_ids)
    pair_ids = tuple(item.pair_id for item in archive.adjacent_pairs)
    trial_ids = tuple(item.trial_id for item in archive.trials)
    feature_consensus_ids = tuple(
        item.consensus_id for item in archive.consensus
    )
    commitments = {
        "context_results": _merkle_commitment(
            context_result_ids,
            role="CONTEXT_RESULT_IDS",
        ),
        "replayed_source_rows": _merkle_commitment(
            replayed_row_ids,
            role="REPLAYED_SOURCE_ROW_IDS",
        ),
        "archive_adjacent_pairs": _merkle_commitment(
            pair_ids,
            role="ARCHIVE_ADJACENT_PAIR_IDS",
        ),
        "archive_trials": _merkle_commitment(
            trial_ids,
            role="ARCHIVE_TRIAL_IDS",
        ),
        "archive_feature_consensus": _merkle_commitment(
            feature_consensus_ids,
            role="ARCHIVE_FEATURE_CONSENSUS_IDS",
        ),
        "family_manifest_id": family_manifest_id,
        "family_authority_id": family_authority_id,
        "campaign_counters_id": campaign_counters_id,
    }
    if complete:
        for value, name in (
            (family_manifest_id, "family manifest"),
            (family_authority_id, "family authority"),
            (campaign_counters_id, "campaign counters"),
        ):
            _cid(value, name)
        if len(context_result_ids) != len(campaign_v1.REGISTERED_CONTEXT_ORDER):
            complete = False
    return commitments, complete


def _strict_recipe_payload(document: Any) -> dict[str, Any]:
    expected = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "reconstruction_inputs",
        "expected_output_ids",
        "ordered_commitments",
        "compact_derived_artifacts",
        "source_graph_commitment_complete",
        "replay_ready",
        "replay_blocker",
        "raw_observation_ids_persisted",
        "caller_supplied_expected_ids_accepted",
        "caller_supplied_runner_accepted",
        "new_observer_draws",
        "max_canonical_recipe_bytes",
        "official_execution_allowed",
    }
    if type(document) is not dict or set(document) != expected:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source reconstruction recipe schema changed"
        )
    inputs = document["reconstruction_inputs"]
    expected_input_keys = {
        "constructor",
        "verifier",
        "max_workers",
        "registered_context_order",
        "registered_context_documents",
        "registered_checkpoints",
        "registered_adjacent_pairs",
        "discovery_draw_count",
        "randomness_implementation",
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "environment_independent_attestation_id",
    }
    output_ids = document["expected_output_ids"]
    expected_output_keys = {
        "source_campaign_id",
        "source_campaign_verification_id",
        "source_archive_id",
        "production_archive_verification_id",
        "independent_archive_attestation_id",
        "source_archive_component_id",
    }
    artifact_docs = document["compact_derived_artifacts"]
    if (
        type(inputs) is not dict
        or set(inputs) != expected_input_keys
        or inputs["constructor"] != REGISTERED_CONSTRUCTOR
        or inputs["verifier"] != REGISTERED_VERIFIER
        or inputs["max_workers"] != RECONSTRUCTION_MAX_WORKERS
        or inputs["registered_context_order"]
        != list(campaign_v1.REGISTERED_CONTEXT_ORDER)
        or inputs["registered_checkpoints"]
        != list(campaign_v1.REGISTERED_CHECKPOINTS)
        or inputs["discovery_draw_count"] != acquisition_v1.DISCOVERY_DRAW_COUNT
        or inputs["randomness_implementation"]
        != campaign_v1.RANDOMNESS_IMPLEMENTATION
        or type(output_ids) is not dict
        or set(output_ids) != expected_output_keys
        or any(
            _ID.fullmatch(value) is None for value in output_ids.values()
        )
        or type(artifact_docs) is not dict
        or set(artifact_docs)
        != {
            "source_archive",
            "production_archive_verification",
            "independent_archive_attestation",
            "source_archive_component_summary",
        }
        or document["raw_observation_ids_persisted"] is not False
        or document["caller_supplied_expected_ids_accepted"] is not False
        or document["caller_supplied_runner_accepted"] is not False
        or document["new_observer_draws"] != 0
        or document["max_canonical_recipe_bytes"]
        != MAX_CANONICAL_RECIPE_BYTES
        or document["official_execution_allowed"] is not False
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source reconstruction recipe semantics changed"
        )
    for name in (
        "component_tree_digest",
        "test_command_manifest_id",
        "runtime_dependency_lock_id",
        "interpreter_build_identity_id",
        "environment_independent_attestation_id",
    ):
        _cid(inputs[name], name)
    contexts = campaign_v1.observer.registered_public_graph_contexts_v1()
    if inputs["registered_context_documents"] != [
        item.to_document() for item in contexts
    ]:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "registered source contexts changed"
        )
    expected_pairs = [
        {
            "context_key": key,
            "checkpoint_pairs": [list(pair) for pair in pairs],
        }
        for key, pairs in archive_v2.REGISTERED_ADJACENT_PAIRS.items()
    ]
    if inputs["registered_adjacent_pairs"] != expected_pairs:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "registered source archive chronology changed"
        )
    for key, identity_field in (
        ("source_archive", "archive_id"),
        ("production_archive_verification", "verification_id"),
        ("independent_archive_attestation", "verification_id"),
        ("source_archive_component_summary", "component_id"),
    ):
        if artifact_docs[key].get(identity_field) != output_ids[
            {
                "source_archive": "source_archive_id",
                "production_archive_verification": (
                    "production_archive_verification_id"
                ),
                "independent_archive_attestation": (
                    "independent_archive_attestation_id"
                ),
                "source_archive_component_summary": (
                    "source_archive_component_id"
                ),
            }[key]
        ]:
            raise V072SourceReconstructionRecipeInvariantViolation(
                "compact derived artifact differs from expected output ID"
            )
    archive_document = artifact_docs["source_archive"]
    production_document = artifact_docs[
        "production_archive_verification"
    ]
    independent_document = artifact_docs[
        "independent_archive_attestation"
    ]
    component_document = artifact_docs[
        "source_archive_component_summary"
    ]
    if (
        archive_document.get("source_campaign_id")
        != output_ids["source_campaign_id"]
        or archive_document.get("source_campaign_verification_id")
        != output_ids["source_campaign_verification_id"]
        or production_document.get("archive_id")
        != output_ids["source_archive_id"]
        or production_document.get("replayed_archive_id")
        != output_ids["source_archive_id"]
        or independent_document.get("archive_id")
        != output_ids["source_archive_id"]
        or independent_document.get("independently_recomputed_archive_id")
        != output_ids["source_archive_id"]
        or component_document.get("archive_id")
        != output_ids["source_archive_id"]
        or component_document.get("production_verification_id")
        != output_ids["production_archive_verification_id"]
        or component_document.get(
            "independent_archive_transform_attestation_id"
        )
        != output_ids["independent_archive_attestation_id"]
        or component_document.get("source_campaign_id")
        != output_ids["source_campaign_id"]
        or component_document.get("source_campaign_verification_id")
        != output_ids["source_campaign_verification_id"]
        or {
            "archive",
            "production_verification",
            "independent_attestation",
        }
        & set(component_document)
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "compact source identity graph does not close"
        )
    commitments = document["ordered_commitments"]
    commitment_specs = {
        "context_results": ("CONTEXT_RESULT_IDS", None),
        "replayed_source_rows": ("REPLAYED_SOURCE_ROW_IDS", None),
        "archive_adjacent_pairs": ("ARCHIVE_ADJACENT_PAIR_IDS", 7),
        "archive_trials": ("ARCHIVE_TRIAL_IDS", None),
        "archive_feature_consensus": (
            "ARCHIVE_FEATURE_CONSENSUS_IDS",
            None,
        ),
    }
    if (
        type(commitments) is not dict
        or set(commitments)
        != {
            *commitment_specs,
            "family_manifest_id",
            "family_authority_id",
            "campaign_counters_id",
        }
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe commitment schema changed"
        )
    for name, (role, exact_count) in commitment_specs.items():
        value = commitments[name]
        if (
            type(value) is not dict
            or set(value) != {"role", "count", "ordered_merkle_root"}
            or value["role"] != role
            or type(value["count"]) is not int
            or value["count"] < 0
            or (
                exact_count is not None
                and value["count"] != exact_count
            )
        ):
            raise V072SourceReconstructionRecipeInvariantViolation(
                "source recipe ordered commitment is malformed"
            )
        _cid(value["ordered_merkle_root"], f"{role} Merkle root")
    complete = document["source_graph_commitment_complete"]
    if type(complete) is not bool or document["replay_ready"] is not complete:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe replay readiness is not mechanically derived"
        )
    blocker = document["replay_blocker"]
    if (
        (complete and blocker is not None)
        or (not complete and blocker != INCOMPLETE_BLOCKER)
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe blocker differs from completeness"
        )
    if complete:
        if commitments["context_results"]["count"] != len(
            campaign_v1.REGISTERED_CONTEXT_ORDER
        ):
            raise V072SourceReconstructionRecipeInvariantViolation(
                "complete source recipe omits registered context results"
            )
        for name in (
            "family_manifest_id",
            "family_authority_id",
            "campaign_counters_id",
        ):
            _cid(commitments[name], name)
    else:
        if commitments["context_results"]["count"] != 0 or any(
            type(commitments[name]) is not dict
            or commitments[name].get("kind")
            != "NOT_AVAILABLE_IN_MECHANICS_FIXTURE"
            for name in (
                "family_manifest_id",
                "family_authority_id",
                "campaign_counters_id",
            )
        ):
            raise V072SourceReconstructionRecipeInvariantViolation(
                "incomplete mechanics recipe hides partial source evidence"
            )
    if (
        commitments["replayed_source_rows"]["count"] <= 0
        or commitments["archive_trials"]["count"] <= 0
        or commitments["archive_feature_consensus"]["count"] <= 0
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe omits archive or replay commitments"
        )
    canonical_json_bytes(document["ordered_commitments"])
    canonical_json_bytes(artifact_docs)
    return document


@dataclass(frozen=True, slots=True)
class SourceReconstructionRecipeV1:
    _issuer: object = field(repr=False)
    _payload_json: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER or type(self._payload_json) is not bytes:
            raise V072SourceReconstructionRecipeInvariantViolation(
                "source recipe was not internally frozen or strictly loaded"
            )
        document = json.loads(self._payload_json.decode("utf-8"))
        _strict_recipe_payload(document)
        if canonical_json_bytes(document) != self._payload_json:
            raise V072SourceReconstructionRecipeInvariantViolation(
                "source recipe payload bytes are not canonical"
            )

    def _payload(self) -> dict[str, Any]:
        value = json.loads(self._payload_json.decode("utf-8"))
        return _strict_recipe_payload(value)

    @property
    def recipe_id(self) -> str:
        return _recipe_id(self._payload())

    @property
    def replay_ready(self) -> bool:
        return self._payload()["replay_ready"]

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "recipe_id": self.recipe_id}


def _freeze_recipe_from_verified_graph(
    repository_root: str | os.PathLike[str],
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
) -> tuple[
    SourceReconstructionRecipeV1,
    archive_v2.VerifiedSourceAcquisitionArchiveV2,
    archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2,
    independent_v2.IndependentSourceAcquisitionArchiveVerificationV2,
    component_v1.V072VerifiedSourceArchiveComponentV1,
]:
    if (
        type(source_campaign) is not campaign_v1.ObservationSupportCampaignV1
        or type(source_verification)
        is not campaign_v1.ObservationSupportCampaignVerificationV1
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe requires exact campaign and verification objects"
        )
    archive = archive_v2.freeze_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    production = archive_v2.verify_verified_source_acquisition_archive_v2(
        source_campaign=source_campaign,
        source_verification=source_verification,
        claimed=archive,
    )
    independent = (
        independent_v2.verify_source_acquisition_archive_independently_v2(
            source_campaign=source_campaign,
            source_verification=source_verification,
            claimed=archive,
        )
    )
    component = component_v1.bind_v072_verified_source_archive_component_v1(
        archive=archive,
        production_verification=production,
        independent_attestation=independent,
    )
    environment = environment_v1.freeze_v072_execution_environment_authorities_v1(
        repository_root
    )
    environment_attestation = (
        environment_independent_v1
        .verify_execution_environment_authorities_independently_v1(
            repository_root,
            environment,
        )
    )
    # Lazy import avoids a manifest-authority import cycle.
    from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1

    registry = manifest_v1.freeze_internal_component_registry_v1(
        repository_root
    )
    commitments, complete = _derive_source_commitments(
        source_campaign,
        source_verification,
        archive,
    )
    payload = {
        "schema": "acfqp.v072_source_reconstruction_recipe.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "reconstruction_inputs": {
            "constructor": REGISTERED_CONSTRUCTOR,
            "verifier": REGISTERED_VERIFIER,
            "max_workers": RECONSTRUCTION_MAX_WORKERS,
            "registered_context_order": list(
                campaign_v1.REGISTERED_CONTEXT_ORDER
            ),
            "registered_context_documents": [
                item.to_document()
                for item in (
                    campaign_v1.observer
                    .registered_public_graph_contexts_v1()
                )
            ],
            "registered_checkpoints": list(
                campaign_v1.REGISTERED_CHECKPOINTS
            ),
            "registered_adjacent_pairs": [
                {
                    "context_key": key,
                    "checkpoint_pairs": [
                        list(pair) for pair in pairs
                    ],
                }
                for key, pairs in (
                    archive_v2.REGISTERED_ADJACENT_PAIRS.items()
                )
            ],
            "discovery_draw_count": acquisition_v1.DISCOVERY_DRAW_COUNT,
            "randomness_implementation": (
                campaign_v1.RANDOMNESS_IMPLEMENTATION
            ),
            "component_tree_digest": registry.component_tree_digest,
            "test_command_manifest_id": (
                environment.test_command_manifest.test_command_manifest_id
            ),
            "runtime_dependency_lock_id": (
                environment.runtime_dependency_lock.runtime_dependency_lock_id
            ),
            "interpreter_build_identity_id": (
                environment.interpreter_build_identity
                .interpreter_build_identity_id
            ),
            "environment_independent_attestation_id": (
                environment_attestation.attestation_id
            ),
        },
        "expected_output_ids": {
            "source_campaign_id": source_campaign.campaign_id,
            "source_campaign_verification_id": (
                source_verification.verification_id
            ),
            "source_archive_id": archive.archive_id,
            "production_archive_verification_id": (
                production.verification_id
            ),
            "independent_archive_attestation_id": (
                independent.verification_id
            ),
            "source_archive_component_id": component.component_id,
        },
        "ordered_commitments": commitments,
        "compact_derived_artifacts": {
            "source_archive": archive.to_document(),
            "production_archive_verification": production.to_document(),
            "independent_archive_attestation": independent.to_document(),
            "source_archive_component_summary": _component_summary(component),
        },
        "source_graph_commitment_complete": complete,
        "replay_ready": complete,
        "replay_blocker": None if complete else INCOMPLETE_BLOCKER,
        "raw_observation_ids_persisted": False,
        "caller_supplied_expected_ids_accepted": False,
        "caller_supplied_runner_accepted": False,
        "new_observer_draws": 0,
        "max_canonical_recipe_bytes": MAX_CANONICAL_RECIPE_BYTES,
        "official_execution_allowed": False,
    }
    _strict_recipe_payload(payload)
    recipe = SourceReconstructionRecipeV1(
        _ISSUER,
        canonical_json_bytes(payload),
    )
    return recipe, archive, production, independent, component


def freeze_source_reconstruction_recipe_v1(
    repository_root: str | os.PathLike[str],
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
) -> SourceReconstructionRecipeV1:
    recipe, _, _, _, _ = _freeze_recipe_from_verified_graph(
        repository_root,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    return recipe


def render_source_reconstruction_recipe_v1(
    recipe: SourceReconstructionRecipeV1,
) -> bytes:
    if type(recipe) is not SourceReconstructionRecipeV1:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "recipe renderer requires the exact recipe type"
        )
    data = canonical_json_bytes(recipe.to_document())
    if len(data) > MAX_CANONICAL_RECIPE_BYTES:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source reconstruction recipe exceeds its frozen byte cap"
        )
    return data


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise V072SourceReconstructionRecipeInvariantViolation(
                f"duplicate source recipe JSON key: {key}"
            )
        result[key] = value
    return result


def _load_json_bytes(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_CANONICAL_RECIPE_BYTES:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source reconstruction recipe exceeds its frozen byte cap"
        )
    try:
        document = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                V072SourceReconstructionRecipeInvariantViolation(
                    f"non-finite source recipe JSON token: {value}"
                )
            ),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        V072SourceReconstructionRecipeInvariantViolation,
    ) as error:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe is not strict canonical JSON"
        ) from error
    if canonical_json_bytes(document) != data:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe bytes are not canonical JSON"
        )
    if type(document) is not dict or set(document) != {
        *set(_strict_recipe_payload(
            {key: value for key, value in document.items() if key != "recipe_id"}
        )),
        "recipe_id",
    }:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe outer document changed"
        )
    claimed_id = document.pop("recipe_id")
    payload = _strict_recipe_payload(document)
    if claimed_id != _recipe_id(payload):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe ID differs from canonical bytes"
        )
    return payload


def _read_no_symlink(path: str | os.PathLike[str]) -> bytes:
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink():
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe input path is relative or linked"
        )
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe input cannot be opened"
        ) from error
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise V072SourceReconstructionRecipeInvariantViolation(
                "source recipe input is not a regular file"
            )
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def load_source_reconstruction_recipe_v1(
    path: str | os.PathLike[str],
) -> SourceReconstructionRecipeV1:
    payload = _load_json_bytes(_read_no_symlink(path))
    return SourceReconstructionRecipeV1(
        _ISSUER,
        canonical_json_bytes(payload),
    )


def write_source_reconstruction_recipe_v1(
    path: str | os.PathLike[str],
    repository_root: str | os.PathLike[str],
    *,
    source_campaign: campaign_v1.ObservationSupportCampaignV1,
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1,
) -> SourceReconstructionRecipeV1:
    output = Path(path)
    if (
        not output.is_absolute()
        or output.exists()
        or output.is_symlink()
        or not output.parent.is_dir()
        or output.parent.is_symlink()
    ):
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source recipe output must be a new absolute regular path"
        )
    recipe = freeze_source_reconstruction_recipe_v1(
        repository_root,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    data = render_source_reconstruction_recipe_v1(recipe)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(output, flags, 0o600)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return recipe


@dataclass(frozen=True, slots=True)
class SourceReconstructionReplayV1:
    recipe_id: str
    source_campaign: campaign_v1.ObservationSupportCampaignV1
    source_verification: campaign_v1.ObservationSupportCampaignVerificationV1
    archive: archive_v2.VerifiedSourceAcquisitionArchiveV2
    production_verification: (
        archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2
    )
    independent_attestation: (
        independent_v2.IndependentSourceAcquisitionArchiveVerificationV2
    )
    component: component_v1.V072VerifiedSourceArchiveComponentV1

    def __post_init__(self) -> None:
        _cid(self.recipe_id, "source reconstruction recipe")
        if (
            type(self.source_campaign)
            is not campaign_v1.ObservationSupportCampaignV1
            or type(self.source_verification)
            is not campaign_v1.ObservationSupportCampaignVerificationV1
            or type(self.archive)
            is not archive_v2.VerifiedSourceAcquisitionArchiveV2
            or type(self.production_verification)
            is not archive_v2.VerifiedSourceAcquisitionArchiveVerificationV2
            or type(self.independent_attestation)
            is not independent_v2.IndependentSourceAcquisitionArchiveVerificationV2
            or type(self.component)
            is not component_v1.V072VerifiedSourceArchiveComponentV1
        ):
            raise V072SourceReconstructionRecipeInvariantViolation(
                "source reconstruction replay result is incomplete"
            )


def replay_source_reconstruction_recipe_v1(
    repository_root: str | os.PathLike[str],
    recipe: SourceReconstructionRecipeV1,
) -> SourceReconstructionReplayV1:
    if type(recipe) is not SourceReconstructionRecipeV1:
        raise V072SourceReconstructionRecipeInvariantViolation(
            "source replay requires the exact recipe type"
        )
    if not recipe.replay_ready:
        raise V072SourceReconstructionRecipeInvariantViolation(
            INCOMPLETE_BLOCKER
        )
    source_campaign = campaign_v1.run_observation_support_campaign_v1(
        max_workers=RECONSTRUCTION_MAX_WORKERS
    )
    source_verification = campaign_v1.verify_observation_support_campaign_v1(
        source_campaign,
        max_workers=RECONSTRUCTION_MAX_WORKERS,
    )
    (
        replayed_recipe,
        archive,
        production,
        independent,
        component,
    ) = _freeze_recipe_from_verified_graph(
        repository_root,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    if replayed_recipe.to_document() != recipe.to_document():
        raise V072SourceReconstructionRecipeInvariantViolation(
            "real source reconstruction differs from the frozen recipe"
        )
    return SourceReconstructionReplayV1(
        recipe.recipe_id,
        source_campaign,
        source_verification,
        archive,
        production,
        independent,
        component,
    )


__all__ = [
    "INCOMPLETE_BLOCKER",
    "MAX_CANONICAL_RECIPE_BYTES",
    "PROFILE_KEY",
    "RECONSTRUCTION_MAX_WORKERS",
    "REGISTERED_CONSTRUCTOR",
    "REGISTERED_VERIFIER",
    "SourceReconstructionRecipeV1",
    "SourceReconstructionReplayV1",
    "V072SourceReconstructionRecipeInvariantViolation",
    "freeze_source_reconstruction_recipe_v1",
    "load_source_reconstruction_recipe_v1",
    "render_source_reconstruction_recipe_v1",
    "replay_source_reconstruction_recipe_v1",
    "write_source_reconstruction_recipe_v1",
]
