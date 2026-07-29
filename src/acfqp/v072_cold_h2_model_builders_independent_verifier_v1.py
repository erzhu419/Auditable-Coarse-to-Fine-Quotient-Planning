"""Independent replay for V0-072 cold-H2 direct/quotient model pairs.

No production builder or coordinate-derivation helper is called.  Ground
identities, closure/projection one-to-one bindings, row-bound OTHER
destinations, behavioral coordinates, concretizers, model IDs, and pair IDs
are reconstructed from the frozen closure and exact planner value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_cold_h2_closure_v1 as closure
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import v072_confidence_row_projection_v1 as registered_projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import (
    v072_remote_main_anchor_independent_verifier_v1
    as remote_anchor_independent,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_cold_h2_model_pair_independent_verifier_v0"

MODEL_DOMAINS = {
    "ground_state": "acfqp:v072-cold-model-ground-state:v1",
    "ground_action": "acfqp:v072-cold-model-ground-action:v1",
    "observed_destination": (
        "acfqp:v072-cold-model-observed-destination:v1"
    ),
    "other_destination": (
        "acfqp:v072-cold-model-row-bound-other-destination:v1"
    ),
    "projection_binding": (
        "acfqp:v072-cold-model-confidence-row-projection-binding:v1"
    ),
    "relational_context": (
        "acfqp:v072-cold-model-public-relational-context:v1"
    ),
    "coordinate": "acfqp:v072-cold-model-relational-coordinate:v1",
    "global_other": (
        "acfqp:v072-cold-model-absorbing-policy-abort-failure:v1"
    ),
    "collapse_entry": (
        "acfqp:v072-cold-model-row-bound-other-collapse-entry:v1"
    ),
    "collapse_proof": (
        "acfqp:v072-cold-model-row-bound-other-collapse-proof:v1"
    ),
    "planner_projection": (
        "acfqp:v072-cold-model-planner-projection:v1"
    ),
    "direct_snapshot": (
        "acfqp:v072-cold-model-ground-direct-checkpoint-snapshot:v1"
    ),
    "model": "acfqp:v072-cold-model-interval-simplex-model:v1",
    "pair": "acfqp:v072-cold-model-direct-quotient-pair:v1",
}
VERIFICATION_DOMAIN = (
    "acfqp:v072-cold-h2-model-pair-independent-verification:v1"
)

REGISTERED_RANK_CAP = 6
REGISTERED_RANK_PROFILE = "PRODUCTION_G2048_RANK_CAP_6_REGISTERED"
REGISTERED_RISK_TOLERANCE = Fraction(1, 20)
REGISTERED_REWARD_CEILING = Fraction(3, 64)
REGISTERED_PROJECTION_CONTRACT_VERSION = "1.36.0"
REGISTERED_PROJECTION_PROFILE_KEY = (
    "v072_confidence_interval_simplex_row_projection_v0"
)
REGISTERED_MODEL_REPLAY_STATUS = (
    "SEPARATE_IDENTITY_BOUND_ATTESTATION_REQUIRED"
)
REGISTERED_VERIFICATION_DOMAIN = (
    "acfqp:v072-registered-cold-h2-model-independent-attestation:v1"
)
REGISTERED_AUTHORITY_CHAIN_DOMAIN = (
    "acfqp:v072-registered-cold-h2-model-replay-authority-chain:v1"
)
REGISTRATION_DISJOINT_VERIFICATION_DOMAIN = (
    "acfqp:v072-registration-disjoint-cold-h2-model-replay:v1"
)
REGISTRATION_DISJOINT_FIXTURE_DOMAIN = (
    "acfqp:v072-registration-disjoint-cold-h2-model-fixture:v1"
)
REMOTE_ANCHOR_CLAIM_DOMAIN = (
    "acfqp:v072-remote-main-anchor-claim:v1"
)
REMOTE_ANCHOR_DOMAIN = "acfqp:v072-remote-main-anchor:v1"
REMOTE_ANCHOR_ATTESTATION_DOMAIN = (
    "acfqp:v072-remote-main-anchor-independent-attestation:v1"
)

REGISTERED_DOMAINS = {
    "relational_context": (
        "acfqp:v072-registered-cold-h2-relational-context:v1"
    ),
    "model": "acfqp:v072-registered-cold-h2-model:v1",
    "global_other": (
        "acfqp:v072-registered-cold-h2-global-other:v1"
    ),
    "collapse": (
        "acfqp:v072-registered-cold-h2-other-collapse-proof:v1"
    ),
    "pair": (
        "acfqp:v072-registered-cold-h2-direct-quotient-pair:v1"
    ),
    "confidence_event": (
        "acfqp:v072-registered-confidence-event-interval:v1"
    ),
    "confidence_authority": (
        "acfqp:v072-registered-confidence-projection-authority:v1"
    ),
    "confidence_projection": (
        "acfqp:v072-registered-confidence-interval-row-projection:v1"
    ),
}


class V072ColdH2ModelIndependentVerificationFailure(ValueError):
    """The model pair differs from independent closure/projection replay."""


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        body = canonical_json_bytes(dict(payload))
    except (TypeError, ValueError) as error:
        raise V072ColdH2ModelIndependentVerificationFailure(
            str(error)
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + body
    ).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ColdH2ModelIndependentVerificationFailure(
            f"{field_name} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _all_keys(value: Any) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, member in value.items():
            keys.append(str(key))
            keys.extend(_all_keys(member))
    elif isinstance(value, (tuple, list)):
        for member in value:
            keys.extend(_all_keys(member))
    return tuple(keys)


def _ground_state_id(
    context_id: str,
    state: closure.ColdPublicStateV1,
    horizon: int,
) -> str:
    return _hash(
        MODEL_DOMAINS["ground_state"],
        {
            "schema": "acfqp.v072_cold_model_ground_state.v1",
            "schema_version": models.SCHEMA_VERSION,
            "context_id": context_id,
            "state_record_id": state.state_record_id,
            "semantic_state_id": state.semantic_state_id,
            "remaining_horizon": horizon,
            "ground_identity_preserved": True,
        },
    )


def _ground_action_id(
    context_id: str,
    state: closure.ColdPublicStateV1,
    horizon: int,
    action: closure.ColdPublicActionV1,
) -> str:
    state_id = _ground_state_id(context_id, state, horizon)
    return _hash(
        MODEL_DOMAINS["ground_action"],
        {
            "schema": "acfqp.v072_cold_model_ground_action.v1",
            "schema_version": models.SCHEMA_VERSION,
            "context_id": context_id,
            "state_id": state_id,
            "state_record_id": state.state_record_id,
            "remaining_horizon": horizon,
            "action_record_id": action.action_record_id,
            "semantic_action_id": action.semantic_action_id,
            "ground_identity_preserved": True,
        },
    )


def _observed_destination_id(
    row: closure.ColdRowEvidenceV1,
    descriptor: closure.ColdOutcomeDescriptorV1,
) -> str:
    return _hash(
        MODEL_DOMAINS["observed_destination"],
        {
            "schema": "acfqp.v072_cold_model_observed_destination.v1",
            "schema_version": models.SCHEMA_VERSION,
            "row_evidence_id": row.row_evidence_id,
            "descriptor_record_id": descriptor.descriptor_record_id,
            "semantic_descriptor_id": descriptor.semantic_descriptor_id,
            "row_bound": True,
        },
    )


def _other_id(row: closure.ColdRowEvidenceV1) -> str:
    return _hash(
        MODEL_DOMAINS["other_destination"],
        {
            "schema": (
                "acfqp.v072_cold_model_row_bound_other_destination.v1"
            ),
            "schema_version": models.SCHEMA_VERSION,
            "context_id": row.context_id,
            "row_evidence_id": row.row_evidence_id,
            "physical_evidence_id": row.physical_evidence_id,
            "state_semantic_id": row.state.semantic_state_id,
            "remaining_horizon": row.remaining_horizon,
            "action_semantic_id": row.action.semantic_action_id,
            "adversarial_failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )


def _expected_destination(
    row: closure.ColdRowEvidenceV1,
    descriptor: closure.ColdOutcomeDescriptorV1,
) -> tuple[str, robust.DestinationCategory, str | None]:
    destination_id = _observed_destination_id(row, descriptor)
    if descriptor.failure:
        return destination_id, robust.DestinationCategory.FAILURE, None
    if descriptor.terminal:
        return (
            destination_id,
            robust.DestinationCategory.SUCCESS_TERMINAL,
            None,
        )
    assert descriptor.successor_state is not None
    return (
        destination_id,
        robust.DestinationCategory.ACTIVE_STATE,
        _ground_state_id(
            row.context_id,
            descriptor.successor_state,
            row.remaining_horizon - 1,
        ),
    )


def _verify_projection_binding(
    row: closure.ColdRowEvidenceV1,
    item: models.VerifiedColdH2ConfidenceRowProjectionV1,
) -> None:
    if type(item) is not models.VerifiedColdH2ConfidenceRowProjectionV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "row projection has a noncanonical concrete type"
        )
    state_id = _ground_state_id(
        row.context_id, row.state, row.remaining_horizon
    )
    action_id = _ground_action_id(
        row.context_id, row.state, row.remaining_horizon, row.action
    )
    expected_destinations = [
        _expected_destination(row, descriptor)
        for descriptor in row.discovery_support
    ]
    expected_destinations.append(
        (_other_id(row), robust.DestinationCategory.OTHER, None)
    )
    expected_destinations.sort(key=lambda value: value[0])
    if (
        item.context_id != row.context_id
        or item.row_evidence_id != row.row_evidence_id
        or item.physical_evidence_id != row.physical_evidence_id
        or item.support_epoch_id != row.support_epoch_id
        or item.confidence_snapshot_id != row.confidence_snapshot_id
        or item.row_replay_verification_id
        != row.row_replay_verification_id
        or item.selected_checkpoint_draw_count
        not in (2_048, 4_096, 8_192, 16_384)
        or item.state_semantic_id != row.state.semantic_state_id
        or item.remaining_horizon != row.remaining_horizon
        or item.action_semantic_id != row.action.semantic_action_id
        or item.discovery_support_descriptor_ids
        != tuple(
            sorted(
                descriptor.descriptor_record_id
                for descriptor in row.discovery_support
            )
        )
        or item.validation_novel_descriptor_ids
        != tuple(
            sorted(
                descriptor.descriptor_record_id
                for descriptor in row.validation_novel
            )
        )
        or item.interval_row.state_id != state_id
        or item.interval_row.action_id != action_id
        or item.interval_row.remaining_horizon != row.remaining_horizon
        or item.interval_row.reward_lower
        != item.interval_row.reward_upper
        or item.interval_row.reward_upper > 1
        or item.interval_row.other_destination_id != _other_id(row)
        or item.rank_cap != 4
        or item.rank_profile != models.DEVELOPMENT_RANK_PROFILE
        or item.evidence_class
        is not (
            models.RowProjectionEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
        or item.registered_target_evidence is not False
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "projection identity/reward/profile was transplanted"
        )
    actual_destinations = tuple(
        (
            destination.destination_id,
            destination.category,
            destination.state_id,
        )
        for destination in item.destinations
    )
    if actual_destinations != tuple(expected_destinations):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "projection destination registry differs from discovery support"
        )
    if {
        mass.destination_id for mass in item.interval_row.masses
    } != {value[0] for value in expected_destinations}:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "projection mass registry is incomplete"
        )
    payload = {
        "schema": (
            "acfqp.v072_cold_model_confidence_row_projection_binding.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "context_id": item.context_id,
        "row_evidence_id": item.row_evidence_id,
        "physical_evidence_id": item.physical_evidence_id,
        "support_epoch_id": item.support_epoch_id,
        "confidence_snapshot_id": item.confidence_snapshot_id,
        "row_replay_verification_id": item.row_replay_verification_id,
        "discovery_transcript_id": item.discovery_transcript_id,
        "validation_transcript_id": item.validation_transcript_id,
        "validation_prefix_id": item.validation_prefix_id,
        "selected_checkpoint_draw_count": (
            item.selected_checkpoint_draw_count
        ),
        "source_projection_id": item.source_projection_id,
        "projection_verification_id": item.projection_verification_id,
        "state_semantic_id": item.state_semantic_id,
        "remaining_horizon": item.remaining_horizon,
        "action_semantic_id": item.action_semantic_id,
        "discovery_support_descriptor_ids": list(
            item.discovery_support_descriptor_ids
        ),
        "validation_novel_descriptor_ids": list(
            item.validation_novel_descriptor_ids
        ),
        "interval_row_id": item.interval_row.row_id,
        "destination_entry_ids": [
            member.registry_entry_id for member in item.destinations
        ],
        "rank_cap": 4,
        "rank_profile": models.DEVELOPMENT_RANK_PROFILE,
        "evidence_class": item.evidence_class.value,
        "registered_target_evidence": False,
    }
    if item.projection_binding_id != _hash(
        MODEL_DOMAINS["projection_binding"], payload
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "projection binding content ID does not replay"
        )


def _coordinate_id(
    role: models.RelationalCoordinateRoleV1,
    horizon: int,
    signature: Mapping[str, Any],
) -> str:
    return _hash(
        MODEL_DOMAINS["coordinate"],
        {
            "schema": "acfqp.v072_cold_model_relational_coordinate.v1",
            "schema_version": models.SCHEMA_VERSION,
            "role": role.value,
            "remaining_horizon": horizon,
            "signature": dict(signature),
            "derivation": models.COORDINATE_DERIVATION,
        },
    )


def _context_payload(
    context: models.ColdH2PublicRelationalContextV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_model_public_relational_context.v1",
        "schema_version": models.SCHEMA_VERSION,
        "context_id": context.context_id,
        "topology_id": context.topology_id,
        "vertex_count": context.vertex_count,
        "edges": [list(edge) for edge in context.edges],
        "rank_cap": 4,
        "source_skeleton_id": context.source_skeleton_id,
        "state_program_id": context.state_program_id,
        "action_program_id": context.action_program_id,
        "coordinate_profile_id": context.coordinate_profile_id,
        "bounded_refinement": {
            "kind": "NOT_APPLICABLE",
            "status": context.bounded_refinement_status,
            "refinement_generation_id": None,
        },
        "public_semantics_only": True,
        "source_observation_rows_imported": False,
        "source_feature_ranks_imported": False,
    }


def _catalogue_values(
    context: models.ColdH2PublicRelationalContextV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, dict[str, int]]:
    state_document = dict(catalogue.state.document)
    ranks = state_document.get("ranks")
    if (
        state_document.get("context_id") != context.context_id
        or state_document.get("topology_id") != context.topology_id
        or type(ranks) is not list
        or len(ranks) != context.vertex_count
        or any(
            type(rank) is not int or not 0 <= rank <= 4
            for rank in ranks
        )
        or type(state_document.get("failure")) is not bool
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "public state relational semantics do not replay"
        )
    expected = tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )
    actual: dict[str, tuple[int, int, int]] = {}
    for action in catalogue.actions:
        document = dict(action.document)
        raw = document.get("action")
        if (
            document.get("context_id") != context.context_id
            or document.get("topology_id") != context.topology_id
            or type(raw) is not list
            or len(raw) != 3
            or any(type(value) is not int for value in raw)
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "public action relational semantics do not replay"
            )
        triple = tuple(raw)
        first, second, survivor = triple
        if (
            tuple(sorted((first, second))) not in context.edges
            or survivor not in (first, second)
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "public action is outside public topology"
            )
        actual[action.action_record_id] = triple
    if tuple(sorted(actual.values())) != expected:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "public legal catalogue is incomplete"
        )
    active = {index for index, rank in enumerate(ranks) if rank > 0}
    neighbours = {index: set() for index in range(context.vertex_count)}
    for first, second in context.edges:
        neighbours[first].add(second)
        neighbours[second].add(first)
    return len(expected), {
        key: len(neighbours[value[2]] & active)
        for key, value in actual.items()
    }


def _base_signature(program: str, value: int) -> dict[str, Any]:
    return {
        "portable_base_program": program,
        "portable_base_value": value,
        "bounded_refinement": {
            "kind": "NOT_APPLICABLE",
            "status": models.BOUNDED_REFINEMENT_STATUS,
            "values": [],
        },
        "sample_independent": True,
    }


def _model_payload(
    model: models.ColdH2IntervalSimplexModelV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_model_interval_simplex_model.v1",
        "schema_version": models.SCHEMA_VERSION,
        "proposed_contract_version": models.PROPOSED_CONTRACT_VERSION,
        "profile_key": models.PROFILE_KEY,
        "context_id": model.context_id,
        "closure_id": model.closure_id,
        "model_kind": model.model_kind.value,
        "root_state_id": model.root_state_id,
        "catalogue_ids": [
            item.catalogue_id for item in model.catalogues
        ],
        "destination_entry_ids": [
            item.registry_entry_id for item in model.destinations
        ],
        "row_ids": [item.row_id for item in model.rows],
        "concretizer_entry_ids": [
            item.concretizer_entry_id
            for item in model.concretizer_entries
        ],
        "physical_evidence_ids": list(model.physical_evidence_ids),
        "projection_binding_ids": list(model.projection_binding_ids),
        "relational_context_id": model.relational_context_id,
        "source_skeleton_id": model.source_skeleton_id,
        "coordinate_profile_id": model.coordinate_profile_id,
        "bounded_refinement_status": model.bounded_refinement_status,
        "rank_cap": 4,
        "rank_profile": models.DEVELOPMENT_RANK_PROFILE,
        "row_bound_other": True,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "source_prior_reads": 0,
    }


def _verify_planner_projection(
    source: models.ColdH2IntervalSimplexModelV1,
    claimed: models.ColdH2PlannerProjectionV1,
    threshold: robust.RobustThresholdProfileV1,
) -> None:
    if (
        type(claimed) is not models.ColdH2PlannerProjectionV1
        or claimed.source_model != source
        or claimed.threshold_profile != threshold
        or threshold.context_id != source.context_id
        or threshold.risk_tolerance
        != models.DEVELOPMENT_RISK_TOLERANCE
        or threshold.reward_ceiling
        != models.DEVELOPMENT_REWARD_CEILING
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "planner projection or development threshold was transplanted"
        )
    global_other_id = _hash(
        MODEL_DOMAINS["global_other"],
        {
            "schema": (
                "acfqp.v072_cold_model_absorbing_policy_abort_failure.v1"
            ),
            "schema_version": models.SCHEMA_VERSION,
            "context_id": source.context_id,
            "semantic_role": "ABSORBING_POLICY_ABORT_FAILURE",
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )
    global_other = robust.RegisteredDestinationV1(
        global_other_id, robust.DestinationCategory.OTHER
    )
    source_destination = {
        item.destination_id: item for item in source.destinations
    }
    planner_rows: list[robust.IntervalSimplexRowV1] = []
    entry_payloads: list[dict[str, Any]] = []
    for row in source.rows:
        if (
            source_destination[row.other_destination_id].category
            is not robust.DestinationCategory.OTHER
            or sum(
                source_destination[mass.destination_id].category
                is robust.DestinationCategory.OTHER
                for mass in row.masses
            )
            != 1
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "source row does not have exactly one adversarial OTHER"
            )
        source_other = row.other_mass
        planner_other = robust.IntervalDestinationMassV1(
            global_other_id, source_other.lower, source_other.upper
        )
        preserved = tuple(
            mass
            for mass in row.masses
            if mass.destination_id != row.other_destination_id
        )
        planner_row = robust.IntervalSimplexRowV1(
            row.state_id,
            row.remaining_horizon,
            row.action_id,
            row.reward_lower,
            row.reward_upper,
            global_other_id,
            tuple(
                sorted(
                    (*preserved, planner_other),
                    key=lambda item: item.destination_id,
                )
            ),
        )
        planner_rows.append(planner_row)
        entry_payloads.append(
            {
                "schema": (
                    "acfqp.v072_cold_model_row_bound_other_collapse_entry.v1"
                ),
                "schema_version": models.SCHEMA_VERSION,
                "source_row_id": row.row_id,
                "source_other_destination_id": (
                    row.other_destination_id
                ),
                "source_other_mass_id": source_other.mass_id,
                "planner_row_id": planner_row.row_id,
                "planner_global_other_destination_id": global_other_id,
                "planner_other_mass_id": planner_other.mass_id,
                "preserved_non_other_mass_ids": sorted(
                    mass.mass_id for mass in preserved
                ),
                "failure_value": 1,
                "continuation_reward_lower": _fdoc(Fraction(0)),
                "mass_merging": False,
            }
        )
    expected_model = robust.PartialSupportIntervalModelV1(
        source.context_id,
        source.root_state_id,
        source.catalogues,
        tuple(
            sorted(
                (
                    *(
                        item
                        for item in source.destinations
                        if item.category
                        is not robust.DestinationCategory.OTHER
                    ),
                    global_other,
                ),
                key=lambda item: item.destination_id,
            )
        ),
        tuple(sorted(planner_rows, key=lambda item: item.row_id)),
        source.concretizer_entries,
    )
    if claimed.planner_model != expected_model:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "planner model did not preserve rows under global OTHER mapping"
        )
    expected_entry_ids = tuple(
        sorted(
            _hash(MODEL_DOMAINS["collapse_entry"], payload)
            for payload in entry_payloads
        )
    )
    expected_entry_payload_by_id = {
        _hash(MODEL_DOMAINS["collapse_entry"], payload): payload
        for payload in entry_payloads
    }
    proof_payload = {
        "schema": (
            "acfqp.v072_cold_model_row_bound_other_collapse_proof.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "context_id": source.context_id,
        "source_model_id": source.model_id,
        "planner_model_id": expected_model.model_id,
        "global_other_destination_id": global_other_id,
        "entry_ids": list(expected_entry_ids),
        "source_row_count": len(source.rows),
        "planner_row_count": len(expected_model.rows),
        "source_other_per_row": 1,
        "planner_other_per_row": 1,
        "failure_value": 1,
        "continuation_reward_lower": _fdoc(Fraction(0)),
        "no_mass_merging": True,
        "behavior_preserved": True,
    }
    proof = claimed.collapse_proof
    if (
        type(proof) is not models.RowBoundOtherCollapseProofV1
        or tuple(item.entry_id for item in proof.entries)
        != expected_entry_ids
        or proof.proof_id
        != _hash(MODEL_DOMAINS["collapse_proof"], proof_payload)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "row-bound OTHER collapse proof does not replay"
        )
    for entry in proof.entries:
        actual_payload = {
            "schema": (
                "acfqp.v072_cold_model_row_bound_other_collapse_entry.v1"
            ),
            "schema_version": models.SCHEMA_VERSION,
            "source_row_id": entry.source_row_id,
            "source_other_destination_id": (
                entry.source_other_destination_id
            ),
            "source_other_mass_id": entry.source_other_mass_id,
            "planner_row_id": entry.planner_row_id,
            "planner_global_other_destination_id": (
                entry.planner_global_other_destination_id
            ),
            "planner_other_mass_id": entry.planner_other_mass_id,
            "preserved_non_other_mass_ids": list(
                entry.preserved_non_other_mass_ids
            ),
            "failure_value": entry.failure_value,
            "continuation_reward_lower": _fdoc(
                entry.continuation_reward_lower
            ),
            "mass_merging": False,
        }
        if (
            expected_entry_payload_by_id.get(entry.entry_id)
            != actual_payload
            or entry.entry_id
            != _hash(MODEL_DOMAINS["collapse_entry"], actual_payload)
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "collapse entry fields do not replay"
            )
    projection_payload = {
        "schema": "acfqp.v072_cold_model_planner_projection.v1",
        "schema_version": models.SCHEMA_VERSION,
        "source_model_id": source.model_id,
        "source_model_kind": source.model_kind.value,
        "planner_model_id": expected_model.model_id,
        "collapse_proof_id": proof.proof_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "rank_cap": 4,
        "rank_profile": models.DEVELOPMENT_RANK_PROFILE,
        "registered_target_threshold_used": False,
    }
    if claimed.projection_id != _hash(
        MODEL_DOMAINS["planner_projection"], projection_payload
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "planner projection content ID does not replay"
        )


@dataclass(frozen=True, slots=True)
class V072ColdH2ModelIndependentVerificationV1:
    model_pair_id: str
    closure_id: str
    direct_model_id: str
    quotient_model_id: str
    physical_row_count: int
    relational_state_coordinate_count: int
    relational_action_coordinate_count: int
    relational_support_coordinate_count: int
    strict_state_compression: bool
    strict_action_compression: bool
    registered_target_evidence_count: int = 0
    verification_result: str = (
        "VALID_INDEPENDENT_COLD_H2_DIRECT_RELATIONAL_MODEL_PAIR"
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.model_pair_id, "verified model pair"),
            (self.closure_id, "verified closure"),
            (self.direct_model_id, "verified direct model"),
            (self.quotient_model_id, "verified quotient model"),
        ):
            _cid(value, label)
        if (
            self.physical_row_count <= 0
            or self.relational_state_coordinate_count <= 0
            or self.relational_action_coordinate_count <= 0
            or self.relational_support_coordinate_count <= 0
            or type(self.strict_state_compression) is not bool
            or type(self.strict_action_compression) is not bool
            or self.registered_target_evidence_count != 0
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "independent model verification result is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_h2_model_pair_independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "model_pair_id": self.model_pair_id,
            "closure_id": self.closure_id,
            "direct_model_id": self.direct_model_id,
            "quotient_model_id": self.quotient_model_id,
            "physical_row_count": self.physical_row_count,
            "relational_state_coordinate_count": (
                self.relational_state_coordinate_count
            ),
            "relational_action_coordinate_count": (
                self.relational_action_coordinate_count
            ),
            "relational_support_coordinate_count": (
                self.relational_support_coordinate_count
            ),
            "strict_state_compression": self.strict_state_compression,
            "strict_action_compression": self.strict_action_compression,
            "registered_target_evidence_count": 0,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id


@dataclass(frozen=True, slots=True)
class V072ColdH2GroundDirectSnapshotIndependentVerificationV1:
    snapshot_id: str
    closure_id: str
    source_model_id: str
    planner_model_id: str
    collapse_proof_id: str
    threshold_profile_id: str
    physical_row_count: int
    checkpoint_row_count: int
    registered_target_evidence_count: int = 0
    verification_result: str = (
        "VALID_INDEPENDENT_COLD_H2_GROUND_DIRECT_CHECKPOINT"
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.snapshot_id, "direct checkpoint"),
            (self.closure_id, "direct checkpoint closure"),
            (self.source_model_id, "direct source model"),
            (self.planner_model_id, "direct planner model"),
            (self.collapse_proof_id, "direct collapse proof"),
            (self.threshold_profile_id, "direct threshold"),
        ):
            _cid(value, label)
        if (
            self.physical_row_count <= 0
            or self.checkpoint_row_count != self.physical_row_count
            or self.registered_target_evidence_count != 0
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "direct checkpoint verification result is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                VERIFICATION_DOMAIN,
                {
                    "schema": (
                        "acfqp.v072_cold_h2_ground_direct_snapshot_"
                        "independent_verification.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "profile_key": PROFILE_KEY,
                    "snapshot_id": self.snapshot_id,
                    "closure_id": self.closure_id,
                    "source_model_id": self.source_model_id,
                    "planner_model_id": self.planner_model_id,
                    "collapse_proof_id": self.collapse_proof_id,
                    "threshold_profile_id": self.threshold_profile_id,
                    "physical_row_count": self.physical_row_count,
                    "checkpoint_row_count": self.checkpoint_row_count,
                    "registered_target_evidence_count": 0,
                    "verification_result": self.verification_result,
                },
            ),
        )

    @property
    def verification_id(self) -> str:
        return self._verification_id


def verify_v072_cold_h2_ground_direct_snapshot_independently_v1(
    claimed: models.V072ColdH2GroundDirectSnapshotV1,
) -> V072ColdH2GroundDirectSnapshotIndependentVerificationV1:
    if type(claimed) is not models.V072ColdH2GroundDirectSnapshotV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct verifier requires one exact checkpoint snapshot"
        )
    bundle = claimed.closure_bundle
    projections = claimed.row_projections
    rows_by_id = {
        item.row_evidence_id: item for item in bundle.all_rows
    }
    projections_by_id = {
        item.row_evidence_id: item for item in projections
    }
    if (
        type(bundle) is not closure.V072ColdH2ClosureBundleV1
        or bundle.cap_evidence.evidence_class
        is not (
            closure.ColdH2CapEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
        or len(projections_by_id) != len(projections)
        or set(projections_by_id) != set(rows_by_id)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct checkpoint closure/projection inventory is invalid"
        )
    for row_id, row in rows_by_id.items():
        _verify_projection_binding(row, projections_by_id[row_id])
    source = claimed.direct_model
    catalogues = (
        (bundle.root_catalogue,) + bundle.child_catalogues
    )
    expected_catalogues: list[robust.StateActionCatalogueV1] = []
    for catalogue in catalogues:
        state_id = _ground_state_id(
            bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        expected_catalogues.append(
            robust.StateActionCatalogueV1(
                state_id,
                state_id,
                tuple(
                    sorted(
                        (
                            robust.CatalogueActionV1(action_id, action_id)
                            for action in catalogue.actions
                            for action_id in (
                                _ground_action_id(
                                    bundle.context_id,
                                    catalogue.state,
                                    catalogue.remaining_horizon,
                                    action,
                                ),
                            )
                        ),
                        key=lambda item: item.action_id,
                    )
                ),
            )
        )
    expected_rows = tuple(
        sorted(
            (item.interval_row for item in projections),
            key=lambda item: item.row_id,
        )
    )
    destination_by_id: dict[str, robust.RegisteredDestinationV1] = {}
    for item in projections:
        for destination in item.destinations:
            previous = destination_by_id.setdefault(
                destination.destination_id, destination
            )
            if previous != destination:
                raise V072ColdH2ModelIndependentVerificationFailure(
                    "direct destination registry conflicts"
                )
    expected_destinations = tuple(
        sorted(
            destination_by_id.values(),
            key=lambda item: item.destination_id,
        )
    )
    expected_physical = tuple(
        sorted(item.physical_evidence_id for item in projections)
    )
    expected_projection_ids = tuple(
        sorted(item.projection_binding_id for item in projections)
    )
    root_id = _ground_state_id(
        bundle.context_id, bundle.root_state, 2
    )
    if (
        type(source) is not models.ColdH2IntervalSimplexModelV1
        or source.model_kind
        is not models.ColdH2ModelKindV1.GROUND_DIRECT
        or source.context_id != bundle.context_id
        or source.closure_id != bundle.closure_id
        or source.root_state_id != root_id
        or source.catalogues
        != tuple(
            sorted(expected_catalogues, key=lambda item: item.state_id)
        )
        or source.destinations != expected_destinations
        or source.rows != expected_rows
        or source.concretizer_entries
        or source.physical_evidence_ids != expected_physical
        or source.projection_binding_ids != expected_projection_ids
        or source.relational_context_id is not None
        or source.source_skeleton_id is not None
        or source.coordinate_profile_id is not None
        or source.model_id
        != _hash(MODEL_DOMAINS["model"], _model_payload(source))
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct source model does not replay from closure rows"
        )
    threshold = claimed.threshold_profile
    _verify_planner_projection(
        source, claimed.planner_projection, threshold
    )
    payload = {
        "schema": (
            "acfqp.v072_cold_model_ground_direct_checkpoint_snapshot.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "context_id": bundle.context_id,
        "closure_id": bundle.closure_id,
        "direct_source_model_id": source.model_id,
        "planner_projection_id": (
            claimed.planner_projection.projection_id
        ),
        "planner_model_id": claimed.planner_model.model_id,
        "collapse_proof_id": claimed.collapse_proof.proof_id,
        "threshold_profile_id": threshold.threshold_profile_id,
        "checkpoint_rows": [
            {
                "row_evidence_id": item.row_evidence_id,
                "physical_evidence_id": item.physical_evidence_id,
                "support_epoch_id": item.support_epoch_id,
                "confidence_snapshot_id": item.confidence_snapshot_id,
                "discovery_transcript_id": item.discovery_transcript_id,
                "validation_transcript_id": item.validation_transcript_id,
                "validation_prefix_id": item.validation_prefix_id,
                "selected_checkpoint_draw_count": (
                    item.selected_checkpoint_draw_count
                ),
                "row_replay_verification_id": (
                    item.row_replay_verification_id
                ),
                "projection_binding_id": item.projection_binding_id,
            }
            for item in projections
        ],
        "relational_coordinates_built": 0,
        "concretizer_entries_built": 0,
        "source_skeleton_reads": 0,
        "source_prior_reads": 0,
    }
    if claimed.snapshot_id != _hash(
        MODEL_DOMAINS["direct_snapshot"], payload
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct checkpoint content ID does not replay"
        )
    return V072ColdH2GroundDirectSnapshotIndependentVerificationV1(
        claimed.snapshot_id,
        bundle.closure_id,
        source.model_id,
        claimed.planner_model.model_id,
        claimed.collapse_proof.proof_id,
        threshold.threshold_profile_id,
        len(expected_physical),
        len(projections),
    )


def verify_v072_cold_h2_model_pair_independently_v1(
    claimed: models.V072ColdH2ModelPairV1,
) -> V072ColdH2ModelIndependentVerificationV1:
    if type(claimed) is not models.V072ColdH2ModelPairV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "verification requires an exact model-pair artifact"
        )
    bundle = claimed.closure_bundle
    if (
        type(bundle) is not closure.V072ColdH2ClosureBundleV1
        or bundle.cap_evidence.evidence_class
        is not (
            closure.ColdH2CapEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "model verifier accepts only exact development cold closures"
        )
    rows_by_id = {
        row.row_evidence_id: row for row in bundle.all_rows
    }
    projections_by_row = {
        item.row_evidence_id: item for item in claimed.row_projections
    }
    if (
        len(projections_by_row) != len(claimed.row_projections)
        or set(projections_by_row) != set(rows_by_id)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "projection inventory is not one-to-one with closure rows"
        )
    for row_id, row in rows_by_id.items():
        _verify_projection_binding(row, projections_by_row[row_id])
    projections = tuple(claimed.row_projections)
    expected_rows = tuple(
        sorted(
            (item.interval_row for item in projections),
            key=lambda item: item.row_id,
        )
    )
    expected_destinations_by_id: dict[
        str, robust.RegisteredDestinationV1
    ] = {}
    for item in projections:
        for destination in item.destinations:
            previous = expected_destinations_by_id.setdefault(
                destination.destination_id, destination
            )
            if previous != destination:
                raise V072ColdH2ModelIndependentVerificationFailure(
                    "destination registry has conflicting duplicate IDs"
                )
    expected_destinations = tuple(
        sorted(
            expected_destinations_by_id.values(),
            key=lambda item: item.destination_id,
        )
    )
    direct = claimed.direct_model
    quotient = claimed.quotient_model
    if (
        type(direct) is not models.ColdH2IntervalSimplexModelV1
        or type(quotient) is not models.ColdH2IntervalSimplexModelV1
        or direct.model_kind
        is not models.ColdH2ModelKindV1.GROUND_DIRECT
        or quotient.model_kind
        is not (
            models.ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT
        )
        or direct.rows != expected_rows
        or quotient.rows != expected_rows
        or direct.destinations != expected_destinations
        or quotient.destinations != expected_destinations
        or direct.root_state_id != quotient.root_state_id
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "model views do not share exact rows/destinations/root"
        )
    catalogue_sources = (
        (bundle.root_catalogue,) + bundle.child_catalogues
    )
    expected_direct: dict[str, tuple[str, ...]] = {}
    source_by_ground_state: dict[str, closure.ColdPublicCatalogueV1] = {}
    for catalogue in catalogue_sources:
        state_id = _ground_state_id(
            bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        actions = tuple(
            sorted(
                _ground_action_id(
                    bundle.context_id,
                    catalogue.state,
                    catalogue.remaining_horizon,
                    action,
                )
                for action in catalogue.actions
            )
        )
        expected_direct[state_id] = actions
        source_by_ground_state[state_id] = catalogue
    if {
        item.state_id for item in direct.catalogues
    } != set(expected_direct):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct catalogue state inventory differs from closure"
        )
    for catalogue in direct.catalogues:
        if (
            catalogue.state_coordinate_key != catalogue.state_id
            or tuple(item.action_id for item in catalogue.actions)
            != expected_direct[catalogue.state_id]
            or any(
                item.action_coordinate_key != item.action_id
                for item in catalogue.actions
            )
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "direct catalogue changed a ground state/action identity"
            )
    context = claimed.relational_context
    if (
        type(context) is not models.ColdH2PublicRelationalContextV1
        or context.context_id != bundle.context_id
        or context.rank_cap != 4
        or context.source_skeleton_id
        != models.V0066_SOURCE_SKELETON_ID
        or context.state_program_id != models.V0066_STATE_PROGRAM_ID
        or context.action_program_id != models.V0066_ACTION_PROGRAM_ID
        or context.coordinate_profile_id
        != models.V0068_BASE_COORDINATE_PROFILE_ID
        or context.bounded_refinement_status
        != models.BOUNDED_REFINEMENT_STATUS
        or context.relational_context_id
        != _hash(
            MODEL_DOMAINS["relational_context"],
            _context_payload(context),
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "public relational context does not replay"
        )
    expected_coordinates: dict[
        str, tuple[models.RelationalCoordinateRoleV1, int, dict[str, Any]]
    ] = {}
    expected_action_coordinate: dict[tuple[str, str], str] = {}
    expected_support_coordinate: dict[tuple[str, str], str] = {}
    state_coordinate: dict[str, str] = {}
    for state_id, catalogue in source_by_ground_state.items():
        state_value, action_values = _catalogue_values(
            context, catalogue
        )
        state_doc = _base_signature(
            "cardinality_actions(legal_actions)", state_value
        )
        coordinate_id = _coordinate_id(
            models.RelationalCoordinateRoleV1.STATE,
            catalogue.remaining_horizon,
            state_doc,
        )
        expected_coordinates[coordinate_id] = (
            models.RelationalCoordinateRoleV1.STATE,
            catalogue.remaining_horizon,
            state_doc,
        )
        state_coordinate[state_id] = coordinate_id
        source_action_by_ground = {
            _ground_action_id(
                bundle.context_id,
                catalogue.state,
                catalogue.remaining_horizon,
                action,
            ): action
            for action in catalogue.actions
        }
        for action_id in expected_direct[state_id]:
            source_action = source_action_by_ground[action_id]
            action_value = action_values[source_action.action_record_id]
            action_doc = _base_signature(
                (
                    "cardinality_resources("
                    "linked_filter(action_anchor,active_resources))"
                ),
                action_value,
            )
            support_doc = {
                "portable_support_tuple": [
                    catalogue.remaining_horizon,
                    state_value,
                    action_value,
                ],
                "bounded_refinement": {
                    "kind": "NOT_APPLICABLE",
                    "status": models.BOUNDED_REFINEMENT_STATUS,
                    "values": [],
                },
                "sample_independent": True,
            }
            action_coord = _coordinate_id(
                models.RelationalCoordinateRoleV1.ACTION,
                catalogue.remaining_horizon,
                action_doc,
            )
            support_coord = _coordinate_id(
                models.RelationalCoordinateRoleV1.SUPPORT,
                catalogue.remaining_horizon,
                support_doc,
            )
            expected_coordinates[action_coord] = (
                models.RelationalCoordinateRoleV1.ACTION,
                catalogue.remaining_horizon,
                action_doc,
            )
            expected_coordinates[support_coord] = (
                models.RelationalCoordinateRoleV1.SUPPORT,
                catalogue.remaining_horizon,
                support_doc,
            )
            expected_action_coordinate[(state_id, action_id)] = action_coord
            expected_support_coordinate[(state_id, action_id)] = support_coord
    root_id = _ground_state_id(
        bundle.context_id, bundle.root_state, 2
    )
    actual_coordinate_by_id = {
        item.coordinate_id: item
        for item in claimed.relational_coordinates
    }
    if set(actual_coordinate_by_id) != set(expected_coordinates):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "relational coordinate registry is missing or overcomplete"
        )
    for coordinate_id, expected in expected_coordinates.items():
        actual = actual_coordinate_by_id[coordinate_id]
        if (
            actual.role is not expected[0]
            or actual.remaining_horizon != expected[1]
            or actual.signature != expected[2]
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "relational coordinate differs from label-free behavior"
            )
        keys = {
            str(key).lower()
            for key in _all_keys(actual.signature)
        }
        if keys & models.FORBIDDEN_COORDINATE_KEYS:
            raise V072ColdH2ModelIndependentVerificationFailure(
                "relational coordinate leaks forbidden identity"
            )
    quotient_by_state = {
        item.state_id: item for item in quotient.catalogues
    }
    if set(quotient_by_state) != set(expected_direct):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "quotient catalogue state inventory changed"
        )
    for state_id, expected_actions in expected_direct.items():
        catalogue = quotient_by_state[state_id]
        if (
            catalogue.state_coordinate_key
            != state_coordinate[state_id]
            or tuple(item.action_id for item in catalogue.actions)
            != expected_actions
            or any(
                item.action_coordinate_key
                != expected_action_coordinate[
                    (state_id, item.action_id)
                ]
                for item in catalogue.actions
            )
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "quotient catalogue coordinates do not replay"
            )
    expected_concretizers: list[
        tuple[str, str, str, tuple[str, ...]]
    ] = []
    for state_id, catalogue in quotient_by_state.items():
        grouped: dict[str, list[str]] = {}
        for action in catalogue.actions:
            grouped.setdefault(
                action.action_coordinate_key, []
            ).append(action.action_id)
        expected_concretizers.extend(
            (
                catalogue.state_coordinate_key,
                state_id,
                coordinate,
                tuple(sorted(action_ids)),
            )
            for coordinate, action_ids in grouped.items()
        )
    actual_concretizers = {
        (
            item.state_coordinate_key,
            item.state_id,
            item.abstract_action_key,
            item.ground_action_ids,
        )
        for item in quotient.concretizer_entries
    }
    if actual_concretizers != set(expected_concretizers):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "fixed distinct-action concretizer differs from quotient groups"
        )
    physical_ids = tuple(
        sorted(item.physical_evidence_id for item in projections)
    )
    projection_ids = tuple(
        sorted(item.projection_binding_id for item in projections)
    )
    for model in (direct, quotient):
        if (
            model.context_id != bundle.context_id
            or model.closure_id != bundle.closure_id
            or model.root_state_id != root_id
            or model.physical_evidence_ids != physical_ids
            or model.projection_binding_ids != projection_ids
            or model.rank_cap != 4
            or model.rank_profile != models.DEVELOPMENT_RANK_PROFILE
            or model.row_bound_other is not True
            or model.model_id
            != _hash(MODEL_DOMAINS["model"], _model_payload(model))
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "model ID/closure/physical-row/profile binding does not replay"
            )
    if (
        direct.relational_context_id is not None
        or direct.source_skeleton_id is not None
        or direct.coordinate_profile_id is not None
        or direct.bounded_refinement_status is not None
        or quotient.relational_context_id
        != context.relational_context_id
        or quotient.source_skeleton_id != context.source_skeleton_id
        or quotient.coordinate_profile_id
        != context.coordinate_profile_id
        or quotient.bounded_refinement_status
        != context.bounded_refinement_status
        or type(claimed.threshold_profile)
        is not robust.RobustThresholdProfileV1
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "direct/quotient relational provenance is invalid"
        )
    _verify_planner_projection(
        direct,
        claimed.direct_planner_projection,
        claimed.threshold_profile,
    )
    _verify_planner_projection(
        quotient,
        claimed.quotient_planner_projection,
        claimed.threshold_profile,
    )
    pair_payload = {
        "schema": "acfqp.v072_cold_model_direct_quotient_pair.v1",
        "schema_version": models.SCHEMA_VERSION,
        "proposed_contract_version": models.PROPOSED_CONTRACT_VERSION,
        "profile_key": models.PROFILE_KEY,
        "closure_id": bundle.closure_id,
        "relational_context_id": context.relational_context_id,
        "source_skeleton_id": context.source_skeleton_id,
        "coordinate_profile_id": context.coordinate_profile_id,
        "bounded_refinement_status": (
            context.bounded_refinement_status
        ),
        "row_projection_binding_ids": [
            item.projection_binding_id for item in projections
        ],
        "relational_coordinate_ids": [
            item.coordinate_id for item in claimed.relational_coordinates
        ],
        "direct_model_id": direct.model_id,
        "quotient_model_id": quotient.model_id,
        "direct_planner_projection_id": (
            claimed.direct_planner_projection.projection_id
        ),
        "direct_planner_model_id": (
            claimed.direct_planner_projection.planner_model.model_id
        ),
        "quotient_planner_projection_id": (
            claimed.quotient_planner_projection.projection_id
        ),
        "quotient_planner_model_id": (
            claimed.quotient_planner_projection.planner_model.model_id
        ),
        "threshold_profile_id": (
            claimed.threshold_profile.threshold_profile_id
        ),
        "shared_physical_row_ids": list(physical_ids),
        "shared_interval_row_ids": [
            item.row_id for item in expected_rows
        ],
        "rank_cap": 4,
        "rank_profile": models.DEVELOPMENT_RANK_PROFILE,
        "registered_target_evidence": False,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "source_prior_reads": 0,
    }
    pair_id = _hash(MODEL_DOMAINS["pair"], pair_payload)
    if (
        claimed.model_pair_id != pair_id
        or claimed.shared_physical_row_ids != physical_ids
        or claimed.shared_interval_row_ids
        != tuple(item.row_id for item in expected_rows)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "model-pair content ID/shared inventory does not replay"
        )
    state_coordinate_count = len(set(state_coordinate.values()))
    action_coordinate_count = len(
        set(expected_action_coordinate.values())
    )
    support_coordinate_count = len(
        set(expected_support_coordinate.values())
    )
    return V072ColdH2ModelIndependentVerificationV1(
        pair_id,
        bundle.closure_id,
        direct.model_id,
        quotient.model_id,
        len(expected_rows),
        state_coordinate_count,
        action_coordinate_count,
        support_coordinate_count,
        state_coordinate_count < len(state_coordinate),
        action_coordinate_count < len(expected_action_coordinate),
    )


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayEventViewV1:
    """Untrusted normalized view of one registered confidence event."""

    confidence_event_id: str
    event_ordinal: int
    event_kind: str
    descriptor_record_id: str | None
    lower_probability: Fraction
    upper_probability: Fraction
    event_id: str


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayProjectionViewV1:
    """Untrusted normalized view of one registered row projection."""

    anchor_id: str
    final_preregistration_id: str
    row_evidence_id: str
    physical_evidence_id: str
    support_epoch_id: str
    confidence_snapshot_id: str
    row_replay_verification_id: str
    discovery_transcript_id: str
    validation_transcript_id: str
    validation_prefix_id: str
    confidence_verification_id: str
    selected_checkpoint_draw_count: int
    events: tuple[RegisteredColdH2ReplayEventViewV1, ...]
    confidence_authority_id: str
    interval_row: robust.IntervalSimplexRowV1
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    exact_row_reward: Fraction
    projection_id: str


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayRelationalContextViewV1:
    context_id: str
    topology_id: str
    vertex_count: int
    edges: tuple[tuple[int, int], ...]
    rank_cap: int
    source_skeleton_id: str
    state_program_id: str
    action_program_id: str
    coordinate_profile_id: str
    bounded_refinement_status: str
    relational_context_id: str


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayModelViewV1:
    model_id: str
    context_id: str
    closure_id: str
    model_kind: models.ColdH2ModelKindV1
    root_state_id: str
    catalogues: tuple[robust.StateActionCatalogueV1, ...]
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    rows: tuple[robust.IntervalSimplexRowV1, ...]
    concretizer_entries: tuple[
        robust.DistinctActionConcretizerEntryV1, ...
    ]
    physical_evidence_ids: tuple[str, ...]
    projection_ids: tuple[str, ...]
    relational_context_id: str | None
    rank_cap: int
    rank_profile: str


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayCollapseProofViewV1:
    source_model_id: str
    planner_model_id: str
    global_other_destination_id: str
    row_mappings: tuple[tuple[str, str, str], ...]
    proof_id: str


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplaySourceV1:
    anchor_id: str
    final_preregistration_id: str
    closure_bundle: closure.V072ColdH2ClosureBundleV1
    row_projections: tuple[RegisteredColdH2ReplayProjectionViewV1, ...]
    relational_context: RegisteredColdH2ReplayRelationalContextViewV1


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ReplayClaimV1:
    relational_coordinates: tuple[
        models.ObservationRelationalCoordinateV1, ...
    ]
    direct_model: RegisteredColdH2ReplayModelViewV1
    quotient_model: RegisteredColdH2ReplayModelViewV1
    direct_planner_model: robust.PartialSupportIntervalModelV1
    quotient_planner_model: robust.PartialSupportIntervalModelV1
    direct_collapse_proof: RegisteredColdH2ReplayCollapseProofViewV1
    quotient_collapse_proof: RegisteredColdH2ReplayCollapseProofViewV1
    threshold_profile: robust.RobustThresholdProfileV1
    model_pair_id: str


@dataclass(frozen=True, slots=True)
class RegistrationDisjointColdH2ReplayVerificationV1:
    model_pair_id: str
    closure_id: str
    context_id: str
    physical_row_count: int
    coordinate_count: int
    production_attestation_minted: bool = False
    registered_target_accesses: int = 0
    verification_result: str = (
        "VALID_REGISTRATION_DISJOINT_REGISTERED_MATH_REPLAY"
    )
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.model_pair_id, "synthetic replay pair"),
            (self.closure_id, "synthetic replay closure"),
            (self.context_id, "synthetic replay context"),
        ):
            _cid(value, label)
        if (
            type(self.physical_row_count) is not int
            or self.physical_row_count <= 0
            or type(self.coordinate_count) is not int
            or self.coordinate_count <= 0
            or self.production_attestation_minted is not False
            or self.registered_target_accesses != 0
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registration-disjoint replay result is malformed"
            )
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                REGISTRATION_DISJOINT_VERIFICATION_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registration_disjoint_cold_h2_"
                "model_replay_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "model_pair_id": self.model_pair_id,
            "closure_id": self.closure_id,
            "context_id": self.context_id,
            "physical_row_count": self.physical_row_count,
            "coordinate_count": self.coordinate_count,
            "production_attestation_minted": False,
            "registered_target_accesses": 0,
            "verification_result": self.verification_result,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _registered_context_payload(
    context: RegisteredColdH2ReplayRelationalContextViewV1,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_registered_cold_h2_relational_context.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "context_id": context.context_id,
        "topology_id": context.topology_id,
        "vertex_count": context.vertex_count,
        "edges": [list(edge) for edge in context.edges],
        "rank_cap": REGISTERED_RANK_CAP,
        "source_skeleton_id": context.source_skeleton_id,
        "state_program_id": context.state_program_id,
        "action_program_id": context.action_program_id,
        "coordinate_profile_id": context.coordinate_profile_id,
        "bounded_refinement_status": context.bounded_refinement_status,
        "public_semantics_only": True,
        "source_observation_rows_imported": False,
        "source_feature_ranks_imported": False,
        "registered_target_evidence": True,
    }


def _registered_model_payload(
    model: RegisteredColdH2ReplayModelViewV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_cold_h2_model.v1",
        "schema_version": models.SCHEMA_VERSION,
        "context_id": model.context_id,
        "closure_id": model.closure_id,
        "model_kind": model.model_kind.value,
        "root_state_id": model.root_state_id,
        "catalogue_ids": [
            item.catalogue_id for item in model.catalogues
        ],
        "destination_entry_ids": [
            item.registry_entry_id for item in model.destinations
        ],
        "row_ids": [item.row_id for item in model.rows],
        "concretizer_entry_ids": [
            item.concretizer_entry_id
            for item in model.concretizer_entries
        ],
        "physical_evidence_ids": list(model.physical_evidence_ids),
        "registered_projection_ids": list(model.projection_ids),
        "relational_context_id": model.relational_context_id,
        "rank_cap": REGISTERED_RANK_CAP,
        "rank_profile": REGISTERED_RANK_PROFILE,
        "registered_target_evidence": True,
        "independent_model_replay_status": (
            REGISTERED_MODEL_REPLAY_STATUS
        ),
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "source_prior_reads": 0,
    }


def _registered_collapse_payload(
    proof: RegisteredColdH2ReplayCollapseProofViewV1,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_registered_cold_h2_other_collapse_proof.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "source_model_id": proof.source_model_id,
        "planner_model_id": proof.planner_model_id,
        "global_other_destination_id": (
            proof.global_other_destination_id
        ),
        "row_mappings": [list(item) for item in proof.row_mappings],
        "row_bound_other_per_source_row": 1,
        "global_other_in_planner": True,
        "failure_value": 1,
        "continuation_reward_lower": _fdoc(Fraction(0)),
        "mass_merging": False,
    }


def _registered_pair_payload(
    source: RegisteredColdH2ReplaySourceV1,
    claim: RegisteredColdH2ReplayClaimV1,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_registered_cold_h2_direct_quotient_pair.v1"
        ),
        "schema_version": models.SCHEMA_VERSION,
        "anchor_id": source.anchor_id,
        "final_preregistration_id": source.final_preregistration_id,
        "closure_id": source.closure_bundle.closure_id,
        "registered_projection_ids": [
            item.projection_id for item in source.row_projections
        ],
        "relational_context_id": (
            source.relational_context.relational_context_id
        ),
        "relational_coordinate_ids": [
            item.coordinate_id for item in claim.relational_coordinates
        ],
        "direct_model_id": claim.direct_model.model_id,
        "quotient_model_id": claim.quotient_model.model_id,
        "direct_planner_model_id": (
            claim.direct_planner_model.model_id
        ),
        "quotient_planner_model_id": (
            claim.quotient_planner_model.model_id
        ),
        "direct_collapse_proof_id": (
            claim.direct_collapse_proof.proof_id
        ),
        "quotient_collapse_proof_id": (
            claim.quotient_collapse_proof.proof_id
        ),
        "threshold_profile_id": (
            claim.threshold_profile.threshold_profile_id
        ),
        "rank_cap": REGISTERED_RANK_CAP,
        "rank_profile": REGISTERED_RANK_PROFILE,
        "registered_target_evidence": True,
        "independent_model_replay_attestation_id": None,
        "independent_model_replay_status": (
            REGISTERED_MODEL_REPLAY_STATUS
        ),
        "shared_physical_rows": True,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "source_prior_reads": 0,
    }


def _registered_event_payload(
    event: RegisteredColdH2ReplayEventViewV1,
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_registered_confidence_event_interval.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "confidence_event_id": event.confidence_event_id,
        "event_ordinal": event.event_ordinal,
        "event_kind": event.event_kind,
        "descriptor_record_id": event.descriptor_record_id,
        "lower_probability": _fdoc(event.lower_probability),
        "upper_probability": _fdoc(event.upper_probability),
    }


def _registered_exact_reward(
    row: closure.ColdRowEvidenceV1,
) -> Fraction:
    state_document = dict(row.state.document)
    action_document = dict(row.action.document)
    ranks = state_document.get("ranks")
    action = action_document.get("action")
    if (
        state_document.get("context_id") != row.context_id
        or action_document.get("context_id") != row.context_id
        or type(ranks) is not list
        or not ranks
        or any(
            type(rank) is not int
            or not 0 <= rank <= REGISTERED_RANK_CAP
            for rank in ranks
        )
        or type(action) is not list
        or len(action) != 3
        or any(type(item) is not int for item in action)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay row lacks public rank/action semantics"
        )
    first, second, survivor = action
    if (
        min(first, second, survivor) < 0
        or max(first, second, survivor) >= len(ranks)
        or first == second
        or survivor not in (first, second)
        or ranks[first] <= 0
        or ranks[first] != ranks[second]
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay row action is not a legal equal-rank merge"
        )
    reward = (
        Fraction(
            2 ** (ranks[first] + 1),
            2 ** (REGISTERED_RANK_CAP + 1),
        )
        / 2
    )
    if reward > REGISTERED_REWARD_CEILING:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay row exceeds the frozen reward ceiling"
        )
    return reward


def _verify_registered_projection_view(
    *,
    source: RegisteredColdH2ReplaySourceV1,
    row: closure.ColdRowEvidenceV1,
    projection: RegisteredColdH2ReplayProjectionViewV1,
) -> tuple[
    robust.IntervalSimplexRowV1,
    tuple[robust.RegisteredDestinationV1, ...],
]:
    if type(projection) is not RegisteredColdH2ReplayProjectionViewV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay projection view has a noncanonical type"
        )
    for value, label in (
        (projection.anchor_id, "projection anchor"),
        (
            projection.final_preregistration_id,
            "projection final preregistration",
        ),
        (projection.row_evidence_id, "projection row evidence"),
        (projection.physical_evidence_id, "projection physical evidence"),
        (projection.support_epoch_id, "projection support epoch"),
        (
            projection.confidence_snapshot_id,
            "projection confidence snapshot",
        ),
        (
            projection.row_replay_verification_id,
            "projection row replay verification",
        ),
        (
            projection.discovery_transcript_id,
            "projection discovery transcript",
        ),
        (
            projection.validation_transcript_id,
            "projection validation transcript",
        ),
        (
            projection.validation_prefix_id,
            "projection validation prefix",
        ),
        (
            projection.confidence_verification_id,
            "projection confidence verification",
        ),
        (
            projection.confidence_authority_id,
            "projection confidence authority",
        ),
        (projection.projection_id, "registered projection"),
    ):
        _cid(value, label)
    if (
        projection.anchor_id != source.anchor_id
        or projection.final_preregistration_id
        != source.final_preregistration_id
        or projection.row_evidence_id != row.row_evidence_id
        or projection.physical_evidence_id != row.physical_evidence_id
        or projection.support_epoch_id != row.support_epoch_id
        or projection.confidence_snapshot_id
        != row.confidence_snapshot_id
        or projection.row_replay_verification_id
        != row.row_replay_verification_id
        or type(projection.selected_checkpoint_draw_count) is not int
        or projection.selected_checkpoint_draw_count
        not in (2_048, 4_096, 8_192, 16_384)
        or type(projection.events) is not tuple
        or len(projection.events) != len(row.discovery_support) + 1
        or any(
            type(item) is not RegisteredColdH2ReplayEventViewV1
            for item in projection.events
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered projection is stale or transplanted"
        )
    support_events = projection.events[:-1]
    other_event = projection.events[-1]
    if (
        tuple(item.event_ordinal for item in projection.events)
        != tuple(range(len(projection.events)))
        or tuple(item.event_kind for item in support_events)
        != ("SUPPORT",) * len(support_events)
        or tuple(
            item.descriptor_record_id for item in support_events
        )
        != tuple(
            item.descriptor_record_id
            for item in row.discovery_support
        )
        or other_event.event_kind != "OTHER"
        or other_event.descriptor_record_id is not None
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered projection event ordering/support changed"
        )
    for event in projection.events:
        _cid(event.confidence_event_id, "registered confidence event")
        _cid(event.event_id, "registered event interval")
        if (
            type(event.lower_probability) is not Fraction
            or type(event.upper_probability) is not Fraction
            or not (
                0
                <= event.lower_probability
                <= event.upper_probability
                <= 1
            )
            or event.event_id
            != _hash(
                REGISTERED_DOMAINS["confidence_event"],
                _registered_event_payload(event),
            )
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered confidence event interval does not replay"
            )
    if (
        sum(
            (item.lower_probability for item in projection.events),
            Fraction(0),
        )
        > 1
        or sum(
            (item.upper_probability for item in projection.events),
            Fraction(0),
        )
        < 1
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered event intervals admit no probability simplex"
        )
    authority_payload = {
        "schema": (
            "acfqp.v072_registered_confidence_projection_authority.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "anchor_id": source.anchor_id,
        "final_preregistration_id": source.final_preregistration_id,
        "row_evidence_id": row.row_evidence_id,
        "event_ids": [item.event_id for item in projection.events],
        "discovery_transcript_id": (
            projection.discovery_transcript_id
        ),
        "validation_transcript_id": (
            projection.validation_transcript_id
        ),
        "validation_prefix_id": projection.validation_prefix_id,
        "confidence_verification_id": (
            projection.confidence_verification_id
        ),
        "selected_checkpoint_draw_count": (
            projection.selected_checkpoint_draw_count
        ),
        "rank_cap": REGISTERED_RANK_CAP,
        "registered_target_evidence": True,
        "caller_supplied_intervals_allowed": False,
    }
    if projection.confidence_authority_id != _hash(
        REGISTERED_DOMAINS["confidence_authority"],
        authority_payload,
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered confidence authority ID does not replay"
        )
    destinations = tuple(
        sorted(
            (
                *(
                    robust.RegisteredDestinationV1(
                        *_expected_destination(row, descriptor)[:2],
                        _expected_destination(row, descriptor)[2],
                    )
                    for descriptor in row.discovery_support
                ),
                robust.RegisteredDestinationV1(
                    _other_id(row),
                    robust.DestinationCategory.OTHER,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    destination_by_descriptor = {
        descriptor.descriptor_record_id: _observed_destination_id(
            row, descriptor
        )
        for descriptor in row.discovery_support
    }
    masses = tuple(
        sorted(
            (
                robust.IntervalDestinationMassV1(
                    (
                        _other_id(row)
                        if event.event_kind == "OTHER"
                        else destination_by_descriptor[
                            event.descriptor_record_id
                        ]
                    ),
                    event.lower_probability,
                    event.upper_probability,
                )
                for event in projection.events
            ),
            key=lambda item: item.destination_id,
        )
    )
    reward = _registered_exact_reward(row)
    interval_row = robust.IntervalSimplexRowV1(
        _ground_state_id(
            row.context_id, row.state, row.remaining_horizon
        ),
        row.remaining_horizon,
        _ground_action_id(
            row.context_id,
            row.state,
            row.remaining_horizon,
            row.action,
        ),
        reward,
        reward,
        _other_id(row),
        masses,
    )
    projection_payload = {
        "schema": (
            "acfqp.v072_registered_confidence_interval_"
            "simplex_row_projection.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": (
            REGISTERED_PROJECTION_CONTRACT_VERSION
        ),
        "profile_key": REGISTERED_PROJECTION_PROFILE_KEY,
        "confidence_authority_id": (
            projection.confidence_authority_id
        ),
        "row_evidence_id": row.row_evidence_id,
        "interval_row_id": interval_row.row_id,
        "destination_entry_ids": [
            item.registry_entry_id for item in destinations
        ],
        "exact_row_reward": _fdoc(reward),
        "rank_cap": REGISTERED_RANK_CAP,
        "rank_profile": REGISTERED_RANK_PROFILE,
        "registered_target_evidence": True,
        "source_prior_quantities_used": False,
    }
    if (
        projection.interval_row != interval_row
        or projection.destinations != destinations
        or projection.exact_row_reward != reward
        or projection.projection_id
        != _hash(
            REGISTERED_DOMAINS["confidence_projection"],
            projection_payload,
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered row/destination/OTHER/projection ID does not replay"
        )
    return interval_row, destinations


def _registered_catalogue_relational_values(
    context: RegisteredColdH2ReplayRelationalContextViewV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, dict[str, int]]:
    state_document = dict(catalogue.state.document)
    ranks = state_document.get("ranks")
    if (
        catalogue.context_id != context.context_id
        or state_document.get("context_id") != context.context_id
        or state_document.get("topology_id") != context.topology_id
        or type(state_document.get("failure")) is not bool
        or type(ranks) is not list
        or len(ranks) != context.vertex_count
        or any(
            type(rank) is not int
            or not 0 <= rank <= REGISTERED_RANK_CAP
            for rank in ranks
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered public state/topology semantics do not replay"
        )
    expected_actions = tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )
    actual: dict[str, tuple[int, int, int]] = {}
    for action in catalogue.actions:
        document = dict(action.document)
        raw = document.get("action")
        if (
            document.get("context_id") != context.context_id
            or document.get("topology_id") != context.topology_id
            or type(raw) is not list
            or len(raw) != 3
            or any(type(item) is not int for item in raw)
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered public action semantics do not replay"
            )
        triple = tuple(raw)
        if (
            tuple(sorted(triple[:2])) not in context.edges
            or triple[2] not in triple[:2]
            or action.action_record_id in actual
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered action is duplicated or outside topology"
            )
        actual[action.action_record_id] = triple
    if (
        tuple(sorted(actual.values())) != expected_actions
        or len(actual) != len(expected_actions)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered legal-action catalogue is incomplete"
        )
    active = {
        vertex for vertex, rank in enumerate(ranks) if rank > 0
    }
    neighbours = {
        vertex: set() for vertex in range(context.vertex_count)
    }
    for first, second in context.edges:
        neighbours[first].add(second)
        neighbours[second].add(first)
    return len(expected_actions), {
        record_id: len(neighbours[action[2]] & active)
        for record_id, action in actual.items()
    }


def _registered_planner_expectation(
    source: RegisteredColdH2ReplayModelViewV1,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    RegisteredColdH2ReplayCollapseProofViewV1,
]:
    global_other_id = _hash(
        REGISTERED_DOMAINS["global_other"],
        {
            "schema": (
                "acfqp.v072_registered_cold_h2_global_other.v1"
            ),
            "schema_version": models.SCHEMA_VERSION,
            "context_id": source.context_id,
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )
    global_other = robust.RegisteredDestinationV1(
        global_other_id,
        robust.DestinationCategory.OTHER,
    )
    destination_by_id = {
        item.destination_id: item for item in source.destinations
    }
    rows: list[robust.IntervalSimplexRowV1] = []
    mappings: list[tuple[str, str, str]] = []
    for row in source.rows:
        source_other = destination_by_id.get(
            row.other_destination_id
        )
        if (
            source_other is None
            or source_other.category
            is not robust.DestinationCategory.OTHER
            or sum(
                destination_by_id[mass.destination_id].category
                is robust.DestinationCategory.OTHER
                for mass in row.masses
            )
            != 1
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered source row lacks exactly one row-bound OTHER"
            )
        planner_other = robust.IntervalDestinationMassV1(
            global_other_id,
            row.other_mass.lower,
            row.other_mass.upper,
        )
        planner_row = robust.IntervalSimplexRowV1(
            row.state_id,
            row.remaining_horizon,
            row.action_id,
            row.reward_lower,
            row.reward_upper,
            global_other_id,
            tuple(
                sorted(
                    (
                        *(
                            mass
                            for mass in row.masses
                            if mass.destination_id
                            != row.other_destination_id
                        ),
                        planner_other,
                    ),
                    key=lambda item: item.destination_id,
                )
            ),
        )
        rows.append(planner_row)
        mappings.append(
            (
                row.row_id,
                row.other_destination_id,
                planner_row.row_id,
            )
        )
    planner = robust.PartialSupportIntervalModelV1(
        source.context_id,
        source.root_state_id,
        source.catalogues,
        tuple(
            sorted(
                (
                    *(
                        item
                        for item in source.destinations
                        if item.category
                        is not robust.DestinationCategory.OTHER
                    ),
                    global_other,
                ),
                key=lambda item: item.destination_id,
            )
        ),
        tuple(sorted(rows, key=lambda item: item.row_id)),
        source.concretizer_entries,
    )
    provisional = RegisteredColdH2ReplayCollapseProofViewV1(
        source.model_id,
        planner.model_id,
        global_other_id,
        tuple(sorted(mappings)),
        source.model_id,
    )
    proof = replace(
        provisional,
        proof_id=_hash(
            REGISTERED_DOMAINS["collapse"],
            _registered_collapse_payload(provisional),
        ),
    )
    return planner, proof


def _reconstruct_registered_cold_h2_replay_claim(
    source: RegisteredColdH2ReplaySourceV1,
) -> RegisteredColdH2ReplayClaimV1:
    if (
        type(source) is not RegisteredColdH2ReplaySourceV1
        or type(source.closure_bundle)
        is not closure.V072ColdH2ClosureBundleV1
        or type(source.row_projections) is not tuple
        or not source.row_projections
        or type(source.relational_context)
        is not RegisteredColdH2ReplayRelationalContextViewV1
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay source has a noncanonical type"
        )
    _cid(source.anchor_id, "registered replay anchor")
    _cid(
        source.final_preregistration_id,
        "registered replay final preregistration",
    )
    bundle = source.closure_bundle
    context = source.relational_context
    if (
        context.context_id != bundle.context_id
        or context.rank_cap != REGISTERED_RANK_CAP
        or type(context.vertex_count) is not int
        or context.vertex_count <= 1
        or type(context.edges) is not tuple
        or not context.edges
        or context.edges != tuple(sorted(set(context.edges)))
        or any(
            type(edge) is not tuple
            or len(edge) != 2
            or any(type(vertex) is not int for vertex in edge)
            or not 0 <= edge[0] < edge[1] < context.vertex_count
            for edge in context.edges
        )
        or context.source_skeleton_id
        != models.V0066_SOURCE_SKELETON_ID
        or context.state_program_id != models.V0066_STATE_PROGRAM_ID
        or context.action_program_id != models.V0066_ACTION_PROGRAM_ID
        or context.coordinate_profile_id
        != models.V0068_BASE_COORDINATE_PROFILE_ID
        or context.bounded_refinement_status
        != models.BOUNDED_REFINEMENT_STATUS
        or context.relational_context_id
        != _hash(
            REGISTERED_DOMAINS["relational_context"],
            _registered_context_payload(context),
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered rank-cap-6 relational context does not replay"
        )
    rows_by_id = {
        item.row_evidence_id: item for item in bundle.all_rows
    }
    projections_by_row = {
        item.row_evidence_id: item
        for item in source.row_projections
    }
    if (
        len(rows_by_id) != len(bundle.all_rows)
        or len(projections_by_row) != len(source.row_projections)
        or set(rows_by_id) != set(projections_by_row)
        or tuple(
            item.projection_id for item in source.row_projections
        )
        != tuple(
            sorted(
                item.projection_id for item in source.row_projections
            )
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "closure and registered projections are not one-to-one"
        )
    projected_rows: list[robust.IntervalSimplexRowV1] = []
    destinations_by_id: dict[str, robust.RegisteredDestinationV1] = {}
    for row_id, row in rows_by_id.items():
        interval_row, destinations = _verify_registered_projection_view(
            source=source,
            row=row,
            projection=projections_by_row[row_id],
        )
        projected_rows.append(interval_row)
        for destination in destinations:
            prior = destinations_by_id.setdefault(
                destination.destination_id,
                destination,
            )
            if prior != destination:
                raise V072ColdH2ModelIndependentVerificationFailure(
                    "registered destination ID has conflicting semantics"
                )
    source_catalogues = (
        (bundle.root_catalogue,) + bundle.child_catalogues
    )
    state_id_by_catalogue_id: dict[str, str] = {}
    action_id_by_record: dict[tuple[str, str], str] = {}
    direct_catalogues: list[robust.StateActionCatalogueV1] = []
    source_by_state_id: dict[str, closure.ColdPublicCatalogueV1] = {}
    for catalogue in source_catalogues:
        state_id = _ground_state_id(
            bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        if state_id in source_by_state_id:
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered closure repeats a ground state-time catalogue"
            )
        state_id_by_catalogue_id[catalogue.catalogue_id] = state_id
        source_by_state_id[state_id] = catalogue
        actions: list[robust.CatalogueActionV1] = []
        for action in catalogue.actions:
            action_id = _ground_action_id(
                bundle.context_id,
                catalogue.state,
                catalogue.remaining_horizon,
                action,
            )
            action_id_by_record[
                (catalogue.catalogue_id, action.action_record_id)
            ] = action_id
            actions.append(
                robust.CatalogueActionV1(action_id, action_id)
            )
        direct_catalogues.append(
            robust.StateActionCatalogueV1(
                state_id,
                state_id,
                tuple(
                    sorted(actions, key=lambda item: item.action_id)
                ),
            )
        )
    direct_catalogue_tuple = tuple(
        sorted(direct_catalogues, key=lambda item: item.state_id)
    )
    root_id = _ground_state_id(
        bundle.context_id, bundle.root_state, 2
    )
    rows = tuple(
        sorted(projected_rows, key=lambda item: item.row_id)
    )
    destinations = tuple(
        sorted(
            destinations_by_id.values(),
            key=lambda item: item.destination_id,
        )
    )
    required_row_keys = {
        (
            catalogue.state_id,
            2 if catalogue.state_id == root_id else 1,
            action.action_id,
        )
        for catalogue in direct_catalogue_tuple
        for action in catalogue.actions
    }
    if (
        {item.row_key for item in rows} != required_row_keys
        or len({item.row_key for item in rows}) != len(rows)
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay rows do not cover every catalogue action once"
        )
    physical_ids = tuple(
        sorted(
            item.physical_evidence_id
            for item in source.row_projections
        )
    )
    projection_ids = tuple(
        sorted(item.projection_id for item in source.row_projections)
    )
    provisional_direct = RegisteredColdH2ReplayModelViewV1(
        bundle.closure_id,
        bundle.context_id,
        bundle.closure_id,
        models.ColdH2ModelKindV1.GROUND_DIRECT,
        root_id,
        direct_catalogue_tuple,
        destinations,
        rows,
        (),
        physical_ids,
        projection_ids,
        None,
        REGISTERED_RANK_CAP,
        REGISTERED_RANK_PROFILE,
    )
    direct = replace(
        provisional_direct,
        model_id=_hash(
            REGISTERED_DOMAINS["model"],
            _registered_model_payload(provisional_direct),
        ),
    )
    state_coordinates: dict[
        str, models.ObservationRelationalCoordinateV1
    ] = {}
    action_coordinates: dict[
        tuple[str, str], models.ObservationRelationalCoordinateV1
    ] = {}
    for state_id, catalogue in source_by_state_id.items():
        state_value, action_values = (
            _registered_catalogue_relational_values(
                context,
                catalogue,
            )
        )
        state_coordinate = models.ObservationRelationalCoordinateV1(
            models.RelationalCoordinateRoleV1.STATE,
            catalogue.remaining_horizon,
            _base_signature(
                "cardinality_actions(legal_actions)",
                state_value,
            ),
        )
        if state_coordinate.coordinate_id != _coordinate_id(
            models.RelationalCoordinateRoleV1.STATE,
            catalogue.remaining_horizon,
            state_coordinate.signature,
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered state coordinate ID does not replay"
            )
        state_coordinates[state_id] = state_coordinate
        for action in catalogue.actions:
            action_id = action_id_by_record[
                (catalogue.catalogue_id, action.action_record_id)
            ]
            action_coordinate = (
                models.ObservationRelationalCoordinateV1(
                    models.RelationalCoordinateRoleV1.ACTION,
                    catalogue.remaining_horizon,
                    _base_signature(
                        (
                            "cardinality_resources(linked_filter("
                            "action_anchor,active_resources))"
                        ),
                        action_values[action.action_record_id],
                    ),
                )
            )
            if action_coordinate.coordinate_id != _coordinate_id(
                models.RelationalCoordinateRoleV1.ACTION,
                catalogue.remaining_horizon,
                action_coordinate.signature,
            ):
                raise V072ColdH2ModelIndependentVerificationFailure(
                    "registered action coordinate ID does not replay"
                )
            action_coordinates[(state_id, action_id)] = (
                action_coordinate
            )
    quotient_catalogues: list[robust.StateActionCatalogueV1] = []
    concretizers: list[
        robust.DistinctActionConcretizerEntryV1
    ] = []
    for direct_catalogue in direct_catalogue_tuple:
        actions = tuple(
            robust.CatalogueActionV1(
                action.action_id,
                action_coordinates[
                    (direct_catalogue.state_id, action.action_id)
                ].coordinate_id,
            )
            for action in direct_catalogue.actions
        )
        quotient_catalogue = robust.StateActionCatalogueV1(
            direct_catalogue.state_id,
            state_coordinates[
                direct_catalogue.state_id
            ].coordinate_id,
            actions,
        )
        quotient_catalogues.append(quotient_catalogue)
        groups: dict[str, list[str]] = {}
        for action in actions:
            groups.setdefault(
                action.action_coordinate_key,
                [],
            ).append(action.action_id)
        concretizers.extend(
            robust.DistinctActionConcretizerEntryV1(
                quotient_catalogue.state_coordinate_key,
                quotient_catalogue.state_id,
                coordinate,
                tuple(sorted(action_ids)),
            )
            for coordinate, action_ids in groups.items()
        )
    quotient_catalogue_tuple = tuple(
        sorted(quotient_catalogues, key=lambda item: item.state_id)
    )
    concretizer_tuple = tuple(
        sorted(
            concretizers,
            key=lambda item: item.concretizer_entry_id,
        )
    )
    provisional_quotient = RegisteredColdH2ReplayModelViewV1(
        bundle.closure_id,
        bundle.context_id,
        bundle.closure_id,
        models.ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT,
        root_id,
        quotient_catalogue_tuple,
        destinations,
        rows,
        concretizer_tuple,
        physical_ids,
        projection_ids,
        context.relational_context_id,
        REGISTERED_RANK_CAP,
        REGISTERED_RANK_PROFILE,
    )
    quotient = replace(
        provisional_quotient,
        model_id=_hash(
            REGISTERED_DOMAINS["model"],
            _registered_model_payload(provisional_quotient),
        ),
    )
    direct_planner, direct_proof = (
        _registered_planner_expectation(direct)
    )
    quotient_planner, quotient_proof = (
        _registered_planner_expectation(quotient)
    )
    threshold = robust.RobustThresholdProfileV1(
        bundle.context_id,
        REGISTERED_RISK_TOLERANCE,
        REGISTERED_REWARD_CEILING,
    )
    coordinates = tuple(
        sorted(
            {
                item.coordinate_id: item
                for item in (
                    *state_coordinates.values(),
                    *action_coordinates.values(),
                )
            }.values(),
            key=lambda item: item.coordinate_id,
        )
    )
    provisional_claim = RegisteredColdH2ReplayClaimV1(
        coordinates,
        direct,
        quotient,
        direct_planner,
        quotient_planner,
        direct_proof,
        quotient_proof,
        threshold,
        bundle.closure_id,
    )
    return replace(
        provisional_claim,
        model_pair_id=_hash(
            REGISTERED_DOMAINS["pair"],
            _registered_pair_payload(source, provisional_claim),
        ),
    )


def _verify_registered_replay_claim(
    source: RegisteredColdH2ReplaySourceV1,
    claimed: RegisteredColdH2ReplayClaimV1,
) -> RegisteredColdH2ReplayClaimV1:
    if type(claimed) is not RegisteredColdH2ReplayClaimV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay claim has a noncanonical type"
        )
    expected = _reconstruct_registered_cold_h2_replay_claim(source)
    if claimed != expected:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered direct/quotient model claim differs from "
            "independent rank-cap-6 replay"
        )
    return expected


def _registration_disjoint_projection_view(
    *,
    anchor_id: str,
    final_preregistration_id: str,
    row: closure.ColdRowEvidenceV1,
) -> RegisteredColdH2ReplayProjectionViewV1:
    events: list[RegisteredColdH2ReplayEventViewV1] = []
    descriptors: tuple[str | None, ...] = (
        tuple(
            item.descriptor_record_id
            for item in row.discovery_support
        )
        + (None,)
    )
    for ordinal, descriptor_id in enumerate(descriptors):
        confidence_event_id = _hash(
            REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
            {
                "schema": (
                    "acfqp.v072_registration_disjoint_confidence_event.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "row_evidence_id": row.row_evidence_id,
                "event_ordinal": ordinal,
            },
        )
        provisional = RegisteredColdH2ReplayEventViewV1(
            confidence_event_id,
            ordinal,
            "OTHER" if descriptor_id is None else "SUPPORT",
            descriptor_id,
            Fraction(0),
            Fraction(1),
            confidence_event_id,
        )
        events.append(
            replace(
                provisional,
                event_id=_hash(
                    REGISTERED_DOMAINS["confidence_event"],
                    _registered_event_payload(provisional),
                ),
            )
        )
    event_tuple = tuple(events)
    discovery_transcript_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "discovery_transcript",
            "row_evidence_id": row.row_evidence_id,
        },
    )
    validation_transcript_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "validation_transcript",
            "row_evidence_id": row.row_evidence_id,
        },
    )
    validation_prefix_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "validation_prefix",
            "row_evidence_id": row.row_evidence_id,
        },
    )
    confidence_verification_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "confidence_verification",
            "row_evidence_id": row.row_evidence_id,
        },
    )
    authority_payload = {
        "schema": (
            "acfqp.v072_registered_confidence_projection_authority.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "anchor_id": anchor_id,
        "final_preregistration_id": final_preregistration_id,
        "row_evidence_id": row.row_evidence_id,
        "event_ids": [item.event_id for item in event_tuple],
        "discovery_transcript_id": discovery_transcript_id,
        "validation_transcript_id": validation_transcript_id,
        "validation_prefix_id": validation_prefix_id,
        "confidence_verification_id": confidence_verification_id,
        "selected_checkpoint_draw_count": 2_048,
        "rank_cap": REGISTERED_RANK_CAP,
        "registered_target_evidence": True,
        "caller_supplied_intervals_allowed": False,
    }
    authority_id = _hash(
        REGISTERED_DOMAINS["confidence_authority"],
        authority_payload,
    )
    destinations = tuple(
        sorted(
            (
                *(
                    robust.RegisteredDestinationV1(
                        _expected_destination(row, descriptor)[0],
                        _expected_destination(row, descriptor)[1],
                        _expected_destination(row, descriptor)[2],
                    )
                    for descriptor in row.discovery_support
                ),
                robust.RegisteredDestinationV1(
                    _other_id(row),
                    robust.DestinationCategory.OTHER,
                ),
            ),
            key=lambda item: item.destination_id,
        )
    )
    destination_by_descriptor = {
        descriptor.descriptor_record_id: _observed_destination_id(
            row, descriptor
        )
        for descriptor in row.discovery_support
    }
    masses = tuple(
        sorted(
            (
                robust.IntervalDestinationMassV1(
                    (
                        _other_id(row)
                        if event.event_kind == "OTHER"
                        else destination_by_descriptor[
                            event.descriptor_record_id
                        ]
                    ),
                    event.lower_probability,
                    event.upper_probability,
                )
                for event in event_tuple
            ),
            key=lambda item: item.destination_id,
        )
    )
    reward = _registered_exact_reward(row)
    interval_row = robust.IntervalSimplexRowV1(
        _ground_state_id(
            row.context_id, row.state, row.remaining_horizon
        ),
        row.remaining_horizon,
        _ground_action_id(
            row.context_id,
            row.state,
            row.remaining_horizon,
            row.action,
        ),
        reward,
        reward,
        _other_id(row),
        masses,
    )
    projection_payload = {
        "schema": (
            "acfqp.v072_registered_confidence_interval_"
            "simplex_row_projection.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": (
            REGISTERED_PROJECTION_CONTRACT_VERSION
        ),
        "profile_key": REGISTERED_PROJECTION_PROFILE_KEY,
        "confidence_authority_id": authority_id,
        "row_evidence_id": row.row_evidence_id,
        "interval_row_id": interval_row.row_id,
        "destination_entry_ids": [
            item.registry_entry_id for item in destinations
        ],
        "exact_row_reward": _fdoc(reward),
        "rank_cap": REGISTERED_RANK_CAP,
        "rank_profile": REGISTERED_RANK_PROFILE,
        "registered_target_evidence": True,
        "source_prior_quantities_used": False,
    }
    return RegisteredColdH2ReplayProjectionViewV1(
        anchor_id,
        final_preregistration_id,
        row.row_evidence_id,
        row.physical_evidence_id,
        row.support_epoch_id,
        row.confidence_snapshot_id,
        row.row_replay_verification_id,
        discovery_transcript_id,
        validation_transcript_id,
        validation_prefix_id,
        confidence_verification_id,
        2_048,
        event_tuple,
        authority_id,
        interval_row,
        destinations,
        reward,
        _hash(
            REGISTERED_DOMAINS["confidence_projection"],
            projection_payload,
        ),
    )


def build_registration_disjoint_cold_h2_replay_fixture_v1(
    *,
    closure_bundle: closure.V072ColdH2ClosureBundleV1,
    topology_id: str,
    vertex_count: int,
    edges: tuple[tuple[int, int], ...],
) -> tuple[
    RegisteredColdH2ReplaySourceV1,
    RegisteredColdH2ReplayClaimV1,
]:
    """Build only a development-synthetic input for verifier attack tests.

    The function rejects every confirmatory closure and cannot mint the
    production attestation.  It exists so the registered rank-cap-6 replay
    mathematics can be exercised before a real remote-main anchor exists.
    """

    if (
        type(closure_bundle) is not closure.V072ColdH2ClosureBundleV1
        or closure_bundle.cap_evidence.evidence_class
        is not (
            closure.ColdH2CapEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registration-disjoint fixture rejects registered target evidence"
        )
    _cid(topology_id, "registration-disjoint topology")
    anchor_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "nonauthorizing_anchor_identity",
            "closure_id": closure_bundle.closure_id,
        },
    )
    final_id = _hash(
        REGISTRATION_DISJOINT_FIXTURE_DOMAIN,
        {
            "role": "nonauthorizing_final_identity",
            "closure_id": closure_bundle.closure_id,
        },
    )
    provisional_context = RegisteredColdH2ReplayRelationalContextViewV1(
        closure_bundle.context_id,
        topology_id,
        vertex_count,
        edges,
        REGISTERED_RANK_CAP,
        models.V0066_SOURCE_SKELETON_ID,
        models.V0066_STATE_PROGRAM_ID,
        models.V0066_ACTION_PROGRAM_ID,
        models.V0068_BASE_COORDINATE_PROFILE_ID,
        models.BOUNDED_REFINEMENT_STATUS,
        closure_bundle.context_id,
    )
    context = replace(
        provisional_context,
        relational_context_id=_hash(
            REGISTERED_DOMAINS["relational_context"],
            _registered_context_payload(provisional_context),
        ),
    )
    projections = tuple(
        sorted(
            (
                _registration_disjoint_projection_view(
                    anchor_id=anchor_id,
                    final_preregistration_id=final_id,
                    row=row,
                )
                for row in closure_bundle.all_rows
            ),
            key=lambda item: item.projection_id,
        )
    )
    source = RegisteredColdH2ReplaySourceV1(
        anchor_id,
        final_id,
        closure_bundle,
        projections,
        context,
    )
    return source, _reconstruct_registered_cold_h2_replay_claim(source)


def verify_registration_disjoint_cold_h2_replay_core_v1(
    *,
    source: RegisteredColdH2ReplaySourceV1,
    claimed: RegisteredColdH2ReplayClaimV1,
) -> RegistrationDisjointColdH2ReplayVerificationV1:
    """Exercise registered replay math without touching registered evidence."""

    if (
        type(source) is not RegisteredColdH2ReplaySourceV1
        or type(source.closure_bundle)
        is not closure.V072ColdH2ClosureBundleV1
        or source.closure_bundle.cap_evidence.evidence_class
        is not (
            closure.ColdH2CapEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "synthetic replay core cannot consume registered target evidence"
        )
    expected = _verify_registered_replay_claim(source, claimed)
    return RegistrationDisjointColdH2ReplayVerificationV1(
        expected.model_pair_id,
        source.closure_bundle.closure_id,
        source.closure_bundle.context_id,
        len(source.row_projections),
        len(expected.relational_coordinates),
    )


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ModelIndependentReplayWorkV1:
    kernel_transition_calls: int = 0
    registered_observer_calls: int = 0
    hidden_law_queries: int = 0
    source_reads: int = 0
    source_prior_reads: int = 0

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value != 0
            for value in (
                self.kernel_transition_calls,
                self.registered_observer_calls,
                self.hidden_law_queries,
                self.source_reads,
                self.source_prior_reads,
            )
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "independent registered replay work must remain zero-access"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_model_"
                "independent_replay_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "kernel_transition_calls": 0,
            "registered_observer_calls": 0,
            "hidden_law_queries": 0,
            "source_reads": 0,
            "source_prior_reads": 0,
        }


_REGISTERED_REPLAY_ATTESTATION_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ModelIndependentReplayAttestationV1:
    _minting_capability: object
    authority_chain_identity_id: str
    remote_main_anchor_id: str
    remote_main_anchor_attestation_id: str
    final_preregistration_id: str
    context_id: str
    closure_id: str
    model_pair_id: str
    physical_row_count: int
    relational_coordinate_count: int
    work: RegisteredColdH2ModelIndependentReplayWorkV1
    verification_result: str = (
        "VALID_REGISTERED_COLD_H2_MODEL_PAIR_INDEPENDENT_REPLAY"
    )
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (
                self.authority_chain_identity_id,
                "registered replay authority chain",
            ),
            (self.remote_main_anchor_id, "registered replay anchor"),
            (
                self.remote_main_anchor_attestation_id,
                "registered replay anchor attestation",
            ),
            (
                self.final_preregistration_id,
                "registered replay final preregistration",
            ),
            (self.context_id, "registered replay context"),
            (self.closure_id, "registered replay closure"),
            (self.model_pair_id, "registered replay model pair"),
        ):
            _cid(value, label)
        if (
            self._minting_capability
            is not _REGISTERED_REPLAY_ATTESTATION_MINTING_SENTINEL
            or type(self.physical_row_count) is not int
            or self.physical_row_count <= 0
            or type(self.relational_coordinate_count) is not int
            or self.relational_coordinate_count <= 0
            or type(self.work)
            is not RegisteredColdH2ModelIndependentReplayWorkV1
            or self.work
            != RegisteredColdH2ModelIndependentReplayWorkV1()
        ):
            raise V072ColdH2ModelIndependentVerificationFailure(
                "registered independent replay attestation was not "
                "privately minted from zero-access exact replay"
            )
        object.__setattr__(
            self,
            "_attestation_id",
            _hash(REGISTERED_VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_model_"
                "independent_replay_attestation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": (
                "v072_registered_cold_h2_model_independent_replay_v1"
            ),
            "authority_chain_identity_id": (
                self.authority_chain_identity_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "remote_main_anchor_attestation_id": (
                self.remote_main_anchor_attestation_id
            ),
            "final_preregistration_id": (
                self.final_preregistration_id
            ),
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "model_pair_id": self.model_pair_id,
            "physical_row_count": self.physical_row_count,
            "relational_coordinate_count": (
                self.relational_coordinate_count
            ),
            "rank_cap": REGISTERED_RANK_CAP,
            "rank_profile": REGISTERED_RANK_PROFILE,
            "pair_embedded_attestation_id": None,
            "identity_cycle_avoided": True,
            "work": self.work.to_document(),
            "verification_result": self.verification_result,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


def _remote_anchor_claim_payload(
    claim: final_authority.V072RemoteMainAnchorClaimV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_remote_main_anchor_claim.v1",
        "schema_version": SCHEMA_VERSION,
        "verification_scope": claim.verification_scope.value,
        "repository_url": claim.repository_url,
        "target_branch": claim.target_branch,
        "remote_tracking_ref": "refs/remotes/origin/main",
        "local_branch_ref": "refs/heads/main",
        "commit_id": claim.commit_id,
        "tree_id": claim.tree_id,
        "parent_commit_id": claim.parent_commit_id,
        "source_reconstruction_recipe_repository_path": (
            claim.source_reconstruction_recipe_repository_path
        ),
        "manifest_repository_path": claim.manifest_repository_path,
        "final_preregistration_repository_path": (
            claim.final_preregistration_repository_path
        ),
        "source_reconstruction_recipe_blob_id": (
            claim.source_reconstruction_recipe_blob_id
        ),
        "manifest_blob_id": claim.manifest_blob_id,
        "final_preregistration_blob_id": (
            claim.final_preregistration_blob_id
        ),
        "source_reconstruction_recipe_id": (
            claim.source_reconstruction_recipe_id
        ),
        "manifest_id": claim.manifest_id,
        "final_preregistration_id": claim.final_preregistration_id,
        "first_qualifying_origin_main_commit_required": True,
        "parent_and_all_ancestors_must_lack_anchored_identity_ids": [
            "source_reconstruction_recipe_id",
            "final_preregistration_id",
        ],
        "target_execution_allowed": False,
        "registered_observer_calls": 0,
    }


def _remote_anchor_payload(
    anchor: final_authority.V072RemoteMainAnchorV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_remote_main_anchor.v1",
        "schema_version": SCHEMA_VERSION,
        "claim_id": anchor.claim.claim_id,
        "source_reconstruction_recipe_id": (
            anchor.claim.source_reconstruction_recipe_id
        ),
        "source_reconstruction_recipe_blob_id": (
            anchor.claim.source_reconstruction_recipe_blob_id
        ),
        "source_reconstruction_recipe_repository_path": (
            anchor.claim.source_reconstruction_recipe_repository_path
        ),
        "manifest_id": anchor.claim.manifest_id,
        "final_preregistration_id": (
            anchor.claim.final_preregistration_id
        ),
        "repository_url": anchor.claim.repository_url,
        "target_branch": anchor.claim.target_branch,
        "commit_id": anchor.claim.commit_id,
        "tree_id": anchor.claim.tree_id,
        "parent_commit_id": anchor.claim.parent_commit_id,
        "independent_semantic_attestation_id": (
            anchor.independent_semantic_attestation_id
        ),
        "target_execution_allowed": True,
    }


def _remote_anchor_attestation_payload(
    attestation: (
        remote_anchor_independent
        .IndependentRemoteMainAnchorAttestationV1
    ),
) -> dict[str, Any]:
    return {
        "schema": (
            "acfqp.v072_remote_main_anchor_independent_attestation.v1"
        ),
        "schema_version": SCHEMA_VERSION,
        "profile_key": (
            "v072_remote_main_anchor_independent_verifier_v1"
        ),
        "claim_id": attestation.claim_id,
        "verification_scope": attestation.verification_scope.value,
        "repository_url": attestation.repository_url,
        "target_branch": "main",
        "commit_id": attestation.commit_id,
        "tree_id": attestation.tree_id,
        "parent_commit_id": attestation.parent_commit_id,
        "source_reconstruction_recipe_repository_path": (
            final_authority
            .SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
        ),
        "source_reconstruction_recipe_blob_id": (
            attestation.source_reconstruction_recipe_blob_id
        ),
        "manifest_blob_id": attestation.manifest_blob_id,
        "final_preregistration_blob_id": (
            attestation.final_preregistration_blob_id
        ),
        "source_reconstruction_recipe_id": (
            attestation.source_reconstruction_recipe_id
        ),
        "manifest_id": attestation.manifest_id,
        "final_preregistration_id": (
            attestation.final_preregistration_id
        ),
        "prior_history_commit_count": (
            attestation.prior_history_commit_count
        ),
        "clean_attached_main_verified": True,
        "origin_main_verified": True,
        "git_object_graph_verified": True,
        "canonical_blob_triple_verified": True,
        "first_qualifying_commit_verified": True,
        "executable_anchor_minted": False,
        "target_execution_allowed": False,
        "registered_observer_calls": 0,
    }


def _verify_registered_replay_authority_chain(
    anchor: Any,
    attestation: Any,
) -> str:
    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or type(attestation)
        is not (
            remote_anchor_independent
            .IndependentRemoteMainAnchorAttestationV1
        )
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered model replay requires exact anchor and independent "
            "anchor-attestation types"
        )
    claim = anchor.claim
    production_scope = (
        final_authority.RemoteMainAnchorVerificationScopeV1
        .REGISTERED_PRODUCTION_CANDIDATE
    )
    if (
        type(claim)
        is not final_authority.V072RemoteMainAnchorClaimV1
        or claim.verification_scope is not production_scope
        or attestation.verification_scope is not production_scope
        or anchor.target_execution_allowed is not True
        or claim.target_execution_allowed is not False
        or attestation.target_execution_allowed is not False
        or claim.registered_observer_calls != 0
        or attestation.registered_observer_calls != 0
        or claim.claim_id
        != _hash(
            REMOTE_ANCHOR_CLAIM_DOMAIN,
            _remote_anchor_claim_payload(claim),
        )
        or anchor.anchor_id
        != _hash(
            REMOTE_ANCHOR_DOMAIN,
            _remote_anchor_payload(anchor),
        )
        or attestation.verification_id
        != _hash(
            REMOTE_ANCHOR_ATTESTATION_DOMAIN,
            _remote_anchor_attestation_payload(attestation),
        )
        or anchor.independent_semantic_attestation_id
        != attestation.verification_id
        or attestation.claim_id != claim.claim_id
        or attestation.repository_url != claim.repository_url
        or attestation.commit_id != claim.commit_id
        or attestation.tree_id != claim.tree_id
        or attestation.parent_commit_id != claim.parent_commit_id
        or attestation.source_reconstruction_recipe_blob_id
        != claim.source_reconstruction_recipe_blob_id
        or attestation.manifest_blob_id != claim.manifest_blob_id
        or attestation.final_preregistration_blob_id
        != claim.final_preregistration_blob_id
        or attestation.source_reconstruction_recipe_id
        != claim.source_reconstruction_recipe_id
        or attestation.manifest_id != claim.manifest_id
        or attestation.final_preregistration_id
        != claim.final_preregistration_id
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "remote-main anchor/attestation identity chain is stale"
        )
    return _hash(
        REGISTERED_AUTHORITY_CHAIN_DOMAIN,
        {
            "schema": (
                "acfqp.v072_registered_cold_h2_model_"
                "replay_authority_chain.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_reconstruction_recipe_id": (
                claim.source_reconstruction_recipe_id
            ),
            "manifest_id": claim.manifest_id,
            "final_preregistration_id": (
                claim.final_preregistration_id
            ),
            "remote_main_anchor_id": anchor.anchor_id,
            "remote_main_anchor_attestation_id": (
                attestation.verification_id
            ),
            "target_access_before_chain_verification": False,
        },
    )


def _registered_projection_view_from_exact_artifact(
    item: (
        registered_projection
        .RegisteredConfidenceIntervalSimplexRowProjectionV1
    ),
) -> RegisteredColdH2ReplayProjectionViewV1:
    authority = item.confidence_authority
    events = tuple(
        RegisteredColdH2ReplayEventViewV1(
            event.confidence_event_id,
            event.event_ordinal,
            event.event_kind.value,
            event.descriptor_record_id,
            event.lower_probability,
            event.upper_probability,
            event.event_id,
        )
        for event in authority.event_intervals
    )
    return RegisteredColdH2ReplayProjectionViewV1(
        authority.anchor_id,
        authority.final_preregistration_id,
        item.row_evidence_id,
        item.physical_evidence_id,
        item.support_epoch_id,
        item.confidence_snapshot_id,
        item.row_replay_verification_id,
        item.discovery_transcript_id,
        item.validation_transcript_id,
        item.validation_prefix_id,
        authority.confidence_verification_id,
        item.selected_checkpoint_draw_count,
        events,
        authority.authority_id,
        item.interval_row,
        item.destinations,
        item.exact_row_reward,
        item.projection_id,
    )


def _registered_context_view_from_exact_artifact(
    item: models.RegisteredColdH2PublicRelationalContextV1,
) -> RegisteredColdH2ReplayRelationalContextViewV1:
    return RegisteredColdH2ReplayRelationalContextViewV1(
        item.context_id,
        item.topology_id,
        item.vertex_count,
        item.edges,
        item.rank_cap,
        item.source_skeleton_id,
        item.state_program_id,
        item.action_program_id,
        item.coordinate_profile_id,
        item.bounded_refinement_status,
        item.relational_context_id,
    )


def _registered_model_view_from_exact_artifact(
    item: models.RegisteredColdH2IntervalSimplexModelV1,
) -> RegisteredColdH2ReplayModelViewV1:
    return RegisteredColdH2ReplayModelViewV1(
        item.model_id,
        item.context_id,
        item.closure_id,
        item.model_kind,
        item.root_state_id,
        item.catalogues,
        item.destinations,
        item.rows,
        item.concretizer_entries,
        item.physical_evidence_ids,
        item.projection_ids,
        item.relational_context_id,
        item.rank_cap,
        item.rank_profile,
    )


def _registered_collapse_view_from_exact_artifact(
    item: models.RegisteredRowBoundOtherCollapseProofV1,
) -> RegisteredColdH2ReplayCollapseProofViewV1:
    return RegisteredColdH2ReplayCollapseProofViewV1(
        item.source_model_id,
        item.planner_model_id,
        item.global_other_destination_id,
        item.row_mappings,
        item.proof_id,
    )


def verify_registered_cold_h2_model_pair_independently_v1(
    anchor: Any,
    remote_main_anchor_attestation: Any,
    claimed: Any,
) -> RegisteredColdH2ModelIndependentReplayAttestationV1:
    """Replay a registered model pair only after exact anchor-chain gating."""

    # This gate intentionally precedes every read from the target artifact.
    authority_chain_identity_id = (
        _verify_registered_replay_authority_chain(
            anchor,
            remote_main_anchor_attestation,
        )
    )
    if type(claimed) is not models.RegisteredColdH2ModelPairV1:
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered replay requires one exact model-pair artifact"
        )
    # Header-only rebound checks precede closure, projection, or model access.
    if (
        claimed.anchor_id != anchor.anchor_id
        or claimed.final_preregistration_id
        != anchor.claim.final_preregistration_id
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered model pair is rebound to a stale authority header"
        )
    bundle = claimed.closure_bundle
    projections = claimed.row_projections
    relational_context = claimed.relational_context
    if (
        type(bundle) is not closure.V072ColdH2ClosureBundleV1
        or bundle.cap_evidence.evidence_class
        is not closure.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
        or type(projections) is not tuple
        or not projections
        or any(
            type(item)
            is not (
                registered_projection
                .RegisteredConfidenceIntervalSimplexRowProjectionV1
            )
            for item in projections
        )
        or type(relational_context)
        is not models.RegisteredColdH2PublicRelationalContextV1
        or type(claimed.direct_model)
        is not models.RegisteredColdH2IntervalSimplexModelV1
        or type(claimed.quotient_model)
        is not models.RegisteredColdH2IntervalSimplexModelV1
        or type(claimed.direct_collapse_proof)
        is not models.RegisteredRowBoundOtherCollapseProofV1
        or type(claimed.quotient_collapse_proof)
        is not models.RegisteredRowBoundOtherCollapseProofV1
        or type(claimed.direct_planner_model)
        is not robust.PartialSupportIntervalModelV1
        or type(claimed.quotient_planner_model)
        is not robust.PartialSupportIntervalModelV1
        or type(claimed.threshold_profile)
        is not robust.RobustThresholdProfileV1
        or type(claimed.relational_coordinates) is not tuple
        or any(
            type(item)
            is not models.ObservationRelationalCoordinateV1
            for item in claimed.relational_coordinates
        )
        or claimed.independent_model_replay_attestation_id is not None
    ):
        raise V072ColdH2ModelIndependentVerificationFailure(
            "registered pair body mixes unregistered or noncanonical evidence"
        )
    source = RegisteredColdH2ReplaySourceV1(
        claimed.anchor_id,
        claimed.final_preregistration_id,
        bundle,
        tuple(
            _registered_projection_view_from_exact_artifact(item)
            for item in projections
        ),
        _registered_context_view_from_exact_artifact(
            relational_context
        ),
    )
    normalized_claim = RegisteredColdH2ReplayClaimV1(
        claimed.relational_coordinates,
        _registered_model_view_from_exact_artifact(
            claimed.direct_model
        ),
        _registered_model_view_from_exact_artifact(
            claimed.quotient_model
        ),
        claimed.direct_planner_model,
        claimed.quotient_planner_model,
        _registered_collapse_view_from_exact_artifact(
            claimed.direct_collapse_proof
        ),
        _registered_collapse_view_from_exact_artifact(
            claimed.quotient_collapse_proof
        ),
        claimed.threshold_profile,
        claimed.model_pair_id,
    )
    expected = _verify_registered_replay_claim(
        source,
        normalized_claim,
    )
    return RegisteredColdH2ModelIndependentReplayAttestationV1(
        _REGISTERED_REPLAY_ATTESTATION_MINTING_SENTINEL,
        authority_chain_identity_id,
        anchor.anchor_id,
        remote_main_anchor_attestation.verification_id,
        anchor.claim.final_preregistration_id,
        bundle.context_id,
        bundle.closure_id,
        expected.model_pair_id,
        len(source.row_projections),
        len(expected.relational_coordinates),
        RegisteredColdH2ModelIndependentReplayWorkV1(),
    )

__all__ = [
    "PROFILE_KEY",
    "REGISTERED_RANK_CAP",
    "REGISTERED_RANK_PROFILE",
    "SCHEMA_VERSION",
    "RegisteredColdH2ModelIndependentReplayAttestationV1",
    "RegisteredColdH2ModelIndependentReplayWorkV1",
    "RegisteredColdH2ReplayClaimV1",
    "RegisteredColdH2ReplayCollapseProofViewV1",
    "RegisteredColdH2ReplayEventViewV1",
    "RegisteredColdH2ReplayModelViewV1",
    "RegisteredColdH2ReplayProjectionViewV1",
    "RegisteredColdH2ReplayRelationalContextViewV1",
    "RegisteredColdH2ReplaySourceV1",
    "RegistrationDisjointColdH2ReplayVerificationV1",
    "V072ColdH2GroundDirectSnapshotIndependentVerificationV1",
    "V072ColdH2ModelIndependentVerificationFailure",
    "V072ColdH2ModelIndependentVerificationV1",
    "build_registration_disjoint_cold_h2_replay_fixture_v1",
    "verify_registered_cold_h2_model_pair_independently_v1",
    "verify_registration_disjoint_cold_h2_replay_core_v1",
    "verify_v072_cold_h2_ground_direct_snapshot_independently_v1",
    "verify_v072_cold_h2_model_pair_independently_v1",
]
