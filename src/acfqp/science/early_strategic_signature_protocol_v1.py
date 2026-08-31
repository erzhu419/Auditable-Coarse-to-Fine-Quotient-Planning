"""Pre-outcome protocol for the candidate-only early-signature pilot.

The protocol selects the 24 u005 candidate models from the parent launch
manifest.  It binds their execution identities and two new fixed evaluation
tapes, but consumes no model outcome, episode score, or prefix observation.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, NoReturn, Sequence

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2,
    RESOURCE_CANDIDATE_ARM_V2,
    LatentResourceHybridConfirmatoryProtocolV2Error,
    registered_hybrid_confirmatory_device_v2,
    validate_ratified_hybrid_confirmatory_protocol_v2,
)


PILOT_PROTOCOL_SCHEMA_V1 = (
    "acfqp.science.early_strategic_signature_protocol.v1"
)
PILOT_PROTOCOL_DOMAIN_V1 = (
    "acfqp:science:early-strategic-signature-protocol:v1"
)
PARENT_MANIFEST_SCHEMA_V1 = (
    "acfqp.science.latent_resource_hybrid_confirmatory_launch_manifest.v2"
)
PARENT_MANIFEST_DOMAIN_V1 = (
    "acfqp:science:early-strategic-signature-parent-manifest:v1"
)

PILOT_ARMS_V1 = (
    "raw",
    "raw_plus_rotated_redundancy",
    "raw_plus_strategic",
)
RAW_ARM_V1 = PILOT_ARMS_V1[0]
ROTATED_REDUNDANCY_ARM_V1 = PILOT_ARMS_V1[1]
STRATEGIC_ARM_V1 = PILOT_ARMS_V1[2]

LABEL_TAPE_ROOT_V1 = "acfqp-early-strategic-signature-label-v1"
PREFIX_TAPE_ROOT_V1 = "acfqp-early-strategic-signature-prefix-v1"
LABEL_EPISODE_INDICES_V1 = tuple(range(64))
PREFIX_EPISODE_INDICES_V1 = tuple(range(64))
PREFIX_ACTION_COUNT_V1 = 8
LABELED_POLICY_COUNT_PER_CLASS_V1 = 8
EXCLUDED_MIDDLE_POLICY_COUNT_V1 = 8
BOOTSTRAP_REPLICATES_V1 = 2_000
BOOTSTRAP_RANDOM_SEED_V1 = 180_001
LOGISTIC_L2_STRENGTH_V1 = 1.0
PARENT_U005_SOURCE_COMMIT_V1 = "70bb7726f220d6ad7eb6ab83f5207186d9f7f42a"
PARENT_U005_PROTOCOL_ID_V1 = (
    "38c19039d83af72f80333674451ccc968a4df9df834a6e8622af21157bf27393"
)
PILOT_EXECUTION_IDENTITY_V1 = (
    "acfqp-early-strategic-signature-2048-pilot-v1-ordinal1-attempt1"
)

_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_CONTENT_ID = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_MODEL_FIELDS = frozenset(
    {"seed", "model_filename", "parent_execution_id", "worker", "device"}
)


class EarlyStrategicSignatureProtocolV1Error(ValueError):
    """The feasibility-pilot protocol or its parent binding is invalid."""


def _fail(message: str) -> NoReturn:
    raise EarlyStrategicSignatureProtocolV1Error(message)


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _candidate_filename(seed: int) -> str:
    return f"{RESOURCE_CANDIDATE_ARM_V2.lower()}-seed-{seed}.pt"


def _validate_parent_manifest(
    parent_protocol: Mapping[str, Any], parent_manifest: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    try:
        protocol = validate_ratified_hybrid_confirmatory_protocol_v2(
            parent_protocol
        )
    except LatentResourceHybridConfirmatoryProtocolV2Error as error:
        raise EarlyStrategicSignatureProtocolV1Error(str(error)) from error
    if (
        protocol["protocol_id"] != PARENT_U005_PROTOCOL_ID_V1
        or protocol["source_commit"] != PARENT_U005_SOURCE_COMMIT_V1
    ):
        _fail("parent protocol is not the frozen u005 execution")
    if type(parent_manifest) is not dict:
        _fail("parent u005 manifest must be a plain object")
    jobs = parent_manifest.get("jobs")
    if (
        parent_manifest.get("schema") != PARENT_MANIFEST_SCHEMA_V1
        or parent_manifest.get("protocol_id") != protocol["protocol_id"]
        or parent_manifest.get("source_commit") != protocol["source_commit"]
        or parent_manifest.get("job_count") != 72
        or parent_manifest.get("worker_count") != 2
        or type(jobs) is not list
        or len(jobs) != 72
        or any(type(row) is not dict for row in jobs)
    ):
        _fail("parent u005 manifest identity or 72-job shape changed")

    ordered = sorted(jobs, key=lambda row: row.get("job_ordinal", -1))
    if [row.get("job_ordinal") for row in ordered] != list(range(72)):
        _fail("parent u005 job ordinals changed")
    expected = {
        (arm, seed)
        for arm in HYBRID_CONFIRMATORY_ARMS_V2
        for seed in HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2
    }
    identities: set[tuple[str, int]] = set()
    execution_ids: set[str] = set()
    for row in ordered:
        identity = (row.get("arm"), row.get("seed"))
        execution_id = row.get("execution_id")
        seed = row.get("seed")
        if (
            identity not in expected
            or identity in identities
            or type(execution_id) is not str
            or not execution_id
            or execution_id in execution_ids
            or type(seed) is not int
        ):
            _fail("parent u005 manifest has a foreign or duplicate job")
        seed_index = HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2.index(seed)
        expected_worker = seed_index % 2
        expected_device = registered_hybrid_confirmatory_device_v2(seed)
        if (
            row.get("worker") != expected_worker
            or row.get("device") != expected_device
        ):
            _fail("parent u005 worker/device assignment changed")
        identities.add(identity)
        execution_ids.add(execution_id)
    if identities != expected:
        _fail("parent u005 manifest does not close the exact 72 jobs")

    candidates = [
        {
            "seed": row["seed"],
            "model_filename": _candidate_filename(row["seed"]),
            "parent_execution_id": row["execution_id"],
            "worker": row["worker"],
            "device": row["device"],
        }
        for row in ordered
        if row["arm"] == RESOURCE_CANDIDATE_ARM_V2
    ]
    candidates.sort(key=lambda row: row["seed"])
    expected_seeds = list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)
    if [row["seed"] for row in candidates] != expected_seeds:
        _fail("parent u005 candidate roster is not the exact 24 policies")
    manifest_id = _content_id(PARENT_MANIFEST_DOMAIN_V1, parent_manifest)
    return protocol, candidates, manifest_id


def _validate_candidate_models(value: Any) -> list[dict[str, Any]]:
    if (
        type(value) is not list
        or len(value) != 24
        or any(type(row) is not dict for row in value)
    ):
        _fail("candidate_models must contain exactly 24 rows")
    rows = [dict(row) for row in value]
    if any(set(row) != _CANDIDATE_MODEL_FIELDS for row in rows):
        _fail("candidate model field set changed")
    expected_seeds = list(HYBRID_CONFIRMATORY_TRAINING_SEEDS_V2)
    if [row["seed"] for row in rows] != expected_seeds:
        _fail("candidate model seed order changed")
    execution_ids: set[str] = set()
    for index, row in enumerate(rows):
        seed = row["seed"]
        execution_id = row["parent_execution_id"]
        if (
            row["model_filename"] != _candidate_filename(seed)
            or type(execution_id) is not str
            or not execution_id
            or execution_id in execution_ids
            or row["worker"] != index % 2
            or row["device"] != f"cuda:{index % 2}"
        ):
            _fail("candidate model roster binding changed")
        execution_ids.add(execution_id)
    return rows


def _payload(
    *,
    parent_protocol_id: str,
    parent_manifest_id: str,
    source_commit: str,
    candidate_models: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": PILOT_PROTOCOL_SCHEMA_V1,
        "schema_version": "1.0.0",
        "pilot_kind": "CANDIDATE_ONLY_FEASIBILITY_DESIGN_SIGNAL",
        "parent_u005_protocol_id": parent_protocol_id,
        "parent_u005_source_commit": PARENT_U005_SOURCE_COMMIT_V1,
        "parent_u005_manifest_id": parent_manifest_id,
        "source_commit": source_commit,
        "pilot_execution_identity": PILOT_EXECUTION_IDENTITY_V1,
        "parent_candidate_arm": RESOURCE_CANDIDATE_ARM_V2,
        "candidate_models": [dict(row) for row in candidate_models],
        "label_tape_root": LABEL_TAPE_ROOT_V1,
        "prefix_tape_root": PREFIX_TAPE_ROOT_V1,
        "label_episode_indices": list(LABEL_EPISODE_INDICES_V1),
        "prefix_episode_indices": list(PREFIX_EPISODE_INDICES_V1),
        "prefix_action_count": PREFIX_ACTION_COUNT_V1,
        "labeling_contract": {
            "label_score_field": "total_merge_score",
            "aggregation": "ARITHMETIC_MEAN_ACROSS_64_FULL_EPISODES",
            "rank_order": "ASCENDING_MEAN_THEN_ASCENDING_POLICY_SEED",
            "novice": "BOTTOM_8",
            "expert": "TOP_8",
            "excluded": "MIDDLE_8",
            "policy_seed_is_statistical_cluster": True,
        },
        "arms": list(PILOT_ARMS_V1),
        "modeling_contract": {
            "cross_validation": "LEAVE_ONE_POLICY_OUT_GROUPED",
            "standardization": "TRAINING_FOLD_ONLY_Z_STANDARDIZATION",
            "zero_variance_training_coordinate_scale": 1,
            "classifier": "L2_LOGISTIC_REGRESSION",
            "optimizer": "SCIPY_OPTIMIZE_L_BFGS_B",
            "l2_strength": LOGISTIC_L2_STRENGTH_V1,
            "intercept_penalized": False,
            "training_label_weighting": (
                "EQUAL_TOTAL_WEIGHT_PER_LABEL_WITHIN_FOLD"
            ),
            "heldout_policy_rows_never_enter_fit_or_standardization": True,
        },
        "bootstrap_contract": {
            "kind": "PAIRED_STRATIFIED_POLICY_CLUSTER_BOOTSTRAP",
            "replicates": BOOTSTRAP_REPLICATES_V1,
            "random_seed": BOOTSTRAP_RANDOM_SEED_V1,
            "confidence_interval": "PERCENTILE_95",
            "same_cluster_draws_for_all_arms": True,
        },
        "provisional_design_signal_contract": {
            "strategic_auroc_minimum": {"numerator": 4, "denominator": 5},
            "strategic_auroc_ci95_lower_minimum": {
                "numerator": 3,
                "denominator": 4,
            },
            "strategic_minus_each_control_auroc_ci95_lower_strictly_positive": True,
            "strategic_minus_each_control_brier_ci95_upper_nonpositive": True,
            "confirmatory_or_scientific_gate": False,
        },
        "claim_boundary": {
            "feasibility_pilot_only": True,
            "feasibility_pilot_execution_authorized": True,
            "confirmatory_execution_authorized": False,
            "scientific_success_claimed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "SCALAR_CALIBRATION_GATE": "NOT_RUN",
            "BREAK_EVEN_GATE": "NOT_RUN",
            "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
            "official_execution_allowed": False,
        },
    }


def build_pilot_protocol_v1(
    parent_protocol: Mapping[str, Any],
    parent_manifest: Mapping[str, Any],
    source_commit: str,
) -> dict[str, Any]:
    """Freeze the 24 candidate policies and pilot tapes without outcomes."""

    if type(source_commit) is not str or _COMMIT.fullmatch(source_commit) is None:
        _fail("pilot source commit must be one lowercase full Git object ID")
    protocol, candidate_models, manifest_id = _validate_parent_manifest(
        parent_protocol, parent_manifest
    )
    payload = _payload(
        parent_protocol_id=protocol["protocol_id"],
        parent_manifest_id=manifest_id,
        source_commit=source_commit,
        candidate_models=candidate_models,
    )
    return {
        **payload,
        "protocol_id": _content_id(PILOT_PROTOCOL_DOMAIN_V1, payload),
    }


def validate_pilot_protocol_v1(document: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the exact standalone pilot protocol identity and fixed contract."""

    if type(document) is not dict:
        _fail("pilot protocol must be a plain object")
    protocol_id = document.get("protocol_id")
    if type(protocol_id) is not str or _CONTENT_ID.fullmatch(protocol_id) is None:
        _fail("pilot protocol ID changed shape")
    payload = dict(document)
    del payload["protocol_id"]
    if _content_id(PILOT_PROTOCOL_DOMAIN_V1, payload) != protocol_id:
        _fail("pilot protocol identity is not replayable")

    source_commit = payload.get("source_commit")
    parent_protocol_id = payload.get("parent_u005_protocol_id")
    parent_source_commit = payload.get("parent_u005_source_commit")
    parent_manifest_id = payload.get("parent_u005_manifest_id")
    if (
        type(source_commit) is not str
        or _COMMIT.fullmatch(source_commit) is None
        or type(parent_protocol_id) is not str
        or _CONTENT_ID.fullmatch(parent_protocol_id) is None
        or parent_protocol_id != PARENT_U005_PROTOCOL_ID_V1
        or parent_source_commit != PARENT_U005_SOURCE_COMMIT_V1
        or type(parent_manifest_id) is not str
        or _CONTENT_ID.fullmatch(parent_manifest_id) is None
    ):
        _fail("pilot parent/source binding changed")
    candidates = _validate_candidate_models(payload.get("candidate_models"))
    expected = _payload(
        parent_protocol_id=parent_protocol_id,
        parent_manifest_id=parent_manifest_id,
        source_commit=source_commit,
        candidate_models=candidates,
    )
    if payload != expected:
        _fail("pilot protocol differs from the frozen feasibility design")
    return dict(document)


__all__ = (
    "BOOTSTRAP_RANDOM_SEED_V1",
    "BOOTSTRAP_REPLICATES_V1",
    "EarlyStrategicSignatureProtocolV1Error",
    "LABEL_EPISODE_INDICES_V1",
    "LABEL_TAPE_ROOT_V1",
    "LOGISTIC_L2_STRENGTH_V1",
    "PILOT_ARMS_V1",
    "PILOT_PROTOCOL_DOMAIN_V1",
    "PILOT_PROTOCOL_SCHEMA_V1",
    "PILOT_EXECUTION_IDENTITY_V1",
    "PARENT_U005_PROTOCOL_ID_V1",
    "PARENT_U005_SOURCE_COMMIT_V1",
    "PREFIX_ACTION_COUNT_V1",
    "PREFIX_EPISODE_INDICES_V1",
    "PREFIX_TAPE_ROOT_V1",
    "RAW_ARM_V1",
    "ROTATED_REDUNDANCY_ARM_V1",
    "STRATEGIC_ARM_V1",
    "build_pilot_protocol_v1",
    "validate_pilot_protocol_v1",
)
