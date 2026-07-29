"""Independent semantic verifier for the V0-072 cold H=2 closure.

No production closure builder or production derivation helper is called.
The verifier consumes a separate public-graph semantics implementation and
the authoritative frozen row summaries, then recomputes catalogues, closure
membership, native work, charge, content IDs, and the complete document.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import v072_cold_h2_closure_v1 as cold
from . import partial_support_confidence_v2 as confidence_v2
from . import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_cold_h2_closure_independent_verifier_v1"


class V072ColdH2IndependentVerificationViolation(ValueError):
    """A claimed closure differs from independent public replay."""


def _fail(message: str) -> None:
    raise V072ColdH2IndependentVerificationViolation(message)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ColdH2IndependentVerificationViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = cold.DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V072ColdH2IndependentVerificationViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _verification_id(role: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        (
            "acfqp:v072-cold-h2-independent-verifier:"
            f"{role}:v1"
        ).encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _state_payload(state: cold.ColdPublicStateV1) -> dict[str, Any]:
    if type(state) is not cold.ColdPublicStateV1:
        _fail("public state has a noncanonical type")
    _cid(state.semantic_state_id, "semantic state")
    return {
        "schema": "acfqp.v072_cold_h2_public_state.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "semantic_state_id": state.semantic_state_id,
        "document": dict(state.document),
    }


def _state_id(state: cold.ColdPublicStateV1) -> str:
    result = _content_id("state", _state_payload(state))
    if state.state_record_id != result:
        _fail("public state record ID is not independently reproducible")
    return result


def _state_document(state: cold.ColdPublicStateV1) -> dict[str, Any]:
    payload = _state_payload(state)
    return {**payload, "state_record_id": _state_id(state)}


def _action_payload(action: cold.ColdPublicActionV1) -> dict[str, Any]:
    if type(action) is not cold.ColdPublicActionV1:
        _fail("public action has a noncanonical type")
    _cid(action.semantic_action_id, "semantic action")
    return {
        "schema": "acfqp.v072_cold_h2_public_action.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "semantic_action_id": action.semantic_action_id,
        "document": dict(action.document),
    }


def _action_id(action: cold.ColdPublicActionV1) -> str:
    result = _content_id("action", _action_payload(action))
    if action.action_record_id != result:
        _fail("public action record ID is not independently reproducible")
    return result


def _action_document(action: cold.ColdPublicActionV1) -> dict[str, Any]:
    payload = _action_payload(action)
    return {**payload, "action_record_id": _action_id(action)}


def _catalogue_payload(
    *,
    context_id: str,
    state: cold.ColdPublicStateV1,
    remaining_horizon: int,
    actions: tuple[cold.ColdPublicActionV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_h2_public_catalogue.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "context_id": context_id,
        "state_record_id": _state_id(state),
        "remaining_horizon": remaining_horizon,
        "action_record_ids": [_action_id(item) for item in actions],
    }


def _catalogue_id(
    catalogue: cold.ColdPublicCatalogueV1,
) -> str:
    if type(catalogue) is not cold.ColdPublicCatalogueV1:
        _fail("public catalogue has a noncanonical type")
    payload = _catalogue_payload(
        context_id=catalogue.context_id,
        state=catalogue.state,
        remaining_horizon=catalogue.remaining_horizon,
        actions=catalogue.actions,
    )
    result = _content_id("catalogue", payload)
    if catalogue.catalogue_id != result:
        _fail("public catalogue ID is not independently reproducible")
    return result


def _catalogue_document(
    catalogue: cold.ColdPublicCatalogueV1,
) -> dict[str, Any]:
    payload = _catalogue_payload(
        context_id=catalogue.context_id,
        state=catalogue.state,
        remaining_horizon=catalogue.remaining_horizon,
        actions=catalogue.actions,
    )
    return {
        **payload,
        "state": _state_document(catalogue.state),
        "actions": [
            _action_document(item) for item in catalogue.actions
        ],
        "catalogue_id": _catalogue_id(catalogue),
    }


def _descriptor_payload(
    descriptor: cold.ColdOutcomeDescriptorV1,
) -> dict[str, Any]:
    if type(descriptor) is not cold.ColdOutcomeDescriptorV1:
        _fail("outcome descriptor has a noncanonical type")
    _cid(descriptor.semantic_descriptor_id, "semantic descriptor")
    if (
        descriptor.active_nonterminal
        != (not descriptor.failure and not descriptor.terminal)
        or (
            descriptor.active_nonterminal
            and type(descriptor.successor_state)
            is not cold.ColdPublicStateV1
        )
        or (
            not descriptor.active_nonterminal
            and descriptor.successor_state is not None
        )
    ):
        _fail("outcome descriptor state/terminal semantics changed")
    return {
        "schema": "acfqp.v072_cold_h2_outcome_descriptor.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "semantic_descriptor_id": descriptor.semantic_descriptor_id,
        "failure": descriptor.failure,
        "terminal": descriptor.terminal,
        "successor_state_record_id": (
            None
            if descriptor.successor_state is None
            else _state_id(descriptor.successor_state)
        ),
        "document": dict(descriptor.document),
    }


def _descriptor_id(descriptor: cold.ColdOutcomeDescriptorV1) -> str:
    result = _content_id("descriptor", _descriptor_payload(descriptor))
    if descriptor.descriptor_record_id != result:
        _fail("outcome descriptor ID is not independently reproducible")
    return result


def _descriptor_document(
    descriptor: cold.ColdOutcomeDescriptorV1,
) -> dict[str, Any]:
    payload = _descriptor_payload(descriptor)
    return {
        **payload,
        "successor_state": (
            None
            if descriptor.successor_state is None
            else _state_document(descriptor.successor_state)
        ),
        "descriptor_record_id": _descriptor_id(descriptor),
    }


def _work_payload(work: cold.ColdRowNativeWorkV1) -> dict[str, Any]:
    if type(work) is not cold.ColdRowNativeWorkV1:
        _fail("row native work has a noncanonical type")
    expected_total_draws = work.discovery_draws + work.validation_draws
    expected_words = (
        work.discovery_random_word_calls
        + work.validation_random_word_calls
    )
    expected_rejections = (
        work.discovery_rejections + work.validation_rejections
    )
    if (
        type(work.acquisition_purpose)
        is not cold.ColdRowAcquisitionPurposeV1
        or (
            work.acquisition_purpose
            is (
                cold.ColdRowAcquisitionPurposeV1
                .MATCHED_DIRECT_CHECKPOINT
            )
            and (
                work.discovery_draws
                != cold.DISCOVERY_DRAWS_PER_ROW
                or work.validation_draws
                not in prereg.DIRECT_VALIDATION_CHECKPOINTS
            )
        )
        or (
            work.acquisition_purpose
            is not (
                cold.ColdRowAcquisitionPurposeV1
                .MATCHED_DIRECT_CHECKPOINT
            )
            and (
                work.discovery_draws,
                work.validation_draws,
            )
            != {
                cold.ColdRowAcquisitionPurposeV1.COLD_INITIAL: (
                    cold.DISCOVERY_DRAWS_PER_ROW,
                    cold.VALIDATION_DRAWS_PER_ROW,
                ),
                cold.ColdRowAcquisitionPurposeV1
                .INCREMENTAL_PROMOTION: (
                    0,
                    cold.VALIDATION_DRAWS_PER_ROW,
                ),
                cold.ColdRowAcquisitionPurposeV1
                .INCREMENTAL_NEW_CHILD: (
                    cold.DISCOVERY_DRAWS_PER_ROW,
                    cold.NEW_CHILD_VALIDATION_DRAWS_PER_ROW,
                ),
            }[work.acquisition_purpose]
        )
        or work.discovery_random_word_calls
        != work.discovery_draws + work.discovery_rejections
        or work.validation_random_word_calls
        != work.validation_draws + work.validation_rejections
        or any(
            value != 0
            for value in (
                work.planner_calls,
                work.audit_calls,
                work.kernel_calls,
                work.hidden_law_queries,
            )
        )
    ):
        _fail("row work fails independent purpose-bound reconciliation")
    return {
        "schema": "acfqp.v072_cold_h2_row_native_work.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "acquisition_purpose": work.acquisition_purpose.value,
        "discovery_draws": work.discovery_draws,
        "validation_draws": work.validation_draws,
        "total_draws": expected_total_draws,
        "discovery_random_word_calls": (
            work.discovery_random_word_calls
        ),
        "validation_random_word_calls": (
            work.validation_random_word_calls
        ),
        "total_random_word_calls": expected_words,
        "discovery_rejections": work.discovery_rejections,
        "validation_rejections": work.validation_rejections,
        "total_rejections": expected_rejections,
        "planner_calls": 0,
        "audit_calls": 0,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
    }


def _work_id(work: cold.ColdRowNativeWorkV1) -> str:
    result = _content_id("row_work", _work_payload(work))
    if work.work_id != result:
        _fail("row work ID is not independently reproducible")
    return result


def _work_document(work: cold.ColdRowNativeWorkV1) -> dict[str, Any]:
    payload = _work_payload(work)
    return {**payload, "work_id": _work_id(work)}


def _row_payload(row: cold.ColdRowEvidenceV1) -> dict[str, Any]:
    if type(row) is not cold.ColdRowEvidenceV1:
        _fail("row evidence has a noncanonical type")
    for value, field_name in (
        (row.context_id, "row context"),
        (row.support_epoch_id, "support epoch"),
        (row.confidence_snapshot_id, "confidence snapshot"),
        (row.row_replay_verification_id, "row replay verification"),
        (row.physical_evidence_id, "physical row evidence"),
    ):
        _cid(value, field_name)
    discovery_ids = tuple(
        _descriptor_id(item) for item in row.discovery_support
    )
    novel_ids = tuple(
        _descriptor_id(item) for item in row.validation_novel
    )
    if (
        not discovery_ids
        or discovery_ids != tuple(sorted(set(discovery_ids)))
        or novel_ids != tuple(sorted(set(novel_ids)))
        or {
            item.semantic_descriptor_id
            for item in row.discovery_support
        }
        & {
            item.semantic_descriptor_id
            for item in row.validation_novel
        }
        or row.discovery_frozen is not True
        or row.validation_novel_separate is not True
        or row.route_independent_physical_evidence is not True
    ):
        _fail("row support/novel evidence is not independently split")
    return {
        "schema": "acfqp.v072_cold_h2_row_evidence.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "context_id": row.context_id,
        "state_record_id": _state_id(row.state),
        "remaining_horizon": row.remaining_horizon,
        "action_record_id": _action_id(row.action),
        "discovery_support_descriptor_ids": list(discovery_ids),
        "validation_novel_descriptor_ids": list(novel_ids),
        "support_epoch_id": row.support_epoch_id,
        "confidence_snapshot_id": row.confidence_snapshot_id,
        "row_replay_verification_id": row.row_replay_verification_id,
        "physical_evidence_id": row.physical_evidence_id,
        "native_work_id": _work_id(row.native_work),
        "discovery_frozen": True,
        "validation_novel_separate": True,
        "route_independent_physical_evidence": True,
    }


def _row_id(row: cold.ColdRowEvidenceV1) -> str:
    result = _content_id("row", _row_payload(row))
    if row.row_evidence_id != result:
        _fail("row evidence ID is not independently reproducible")
    return result


def _row_document(row: cold.ColdRowEvidenceV1) -> dict[str, Any]:
    payload = _row_payload(row)
    return {
        **payload,
        "state": _state_document(row.state),
        "action": _action_document(row.action),
        "discovery_support": [
            _descriptor_document(item) for item in row.discovery_support
        ],
        "validation_novel": [
            _descriptor_document(item) for item in row.validation_novel
        ],
        "native_work": _work_document(row.native_work),
        "row_evidence_id": _row_id(row),
    }


def _external_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _source_cap_key(context_id: str, context_key: str) -> str:
    return _external_id(
        "acfqp:v072-heldout-public-context-total-row-cap-key:v1",
        {
            "schema": (
                "acfqp.v072_heldout_public_context_total_row_cap_key.v1"
            ),
            "schema_version": cold.SCHEMA_VERSION,
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_id": context_id,
            "context_key": context_key,
            "cap_semantics": (
                "COMPLETE_COLD_H2_TOTAL_PHYSICAL_STATE_ACTION_ROWS"
            ),
        },
    )


def _source_cap_binding_id(
    context_id: str,
    context_key: str,
    total_cap: int,
) -> str:
    cap_key = _source_cap_key(context_id, context_key)
    return _external_id(
        "acfqp:v072-heldout-public-total-row-cap-binding:v1",
        {
            "schema": (
                "acfqp.v072_heldout_public_total_row_cap_binding.v1"
            ),
            "schema_version": cold.SCHEMA_VERSION,
            "context_id": context_id,
            "context_key": context_key,
            "total_physical_row_cap": total_cap,
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "authority_class": "CONFIRMATORY_REGISTERED_PUBLIC_ONLY",
            "context_specific_total_row_cap_key": cap_key,
            "preregistration_binding": {
                "kind": "NOT_FINALIZED_PUBLIC_ONLY",
                "final_preregistration_id": None,
            },
            "target_execution_allowed": False,
        },
    )


def _cap_evidence_payload(
    evidence: cold.ColdH2ContextTotalRowCapEvidenceV1,
) -> dict[str, Any]:
    if type(evidence) is not cold.ColdH2ContextTotalRowCapEvidenceV1:
        _fail("closure cap evidence has a noncanonical type")
    _cid(evidence.context_id, "cap-evidence context")
    registered = {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    registered_keys = {item.context_key for item in registered.values()}
    if (
        evidence.evidence_class
        is cold.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
    ):
        expected = registered.get(evidence.context_id)
        if (
            expected is None
            or evidence.context_key != expected.context_key
            or evidence.total_physical_row_cap
            != expected.maximum_physical_rows_per_confidence_epoch
            or evidence.confirmatory_family_generation
            != prereg.CONFIRMATORY_FAMILY_GENERATION
            or evidence.context_specific_total_row_cap_key
            != _source_cap_key(
                evidence.context_id,
                evidence.context_key,
            )
            or evidence.source_total_row_cap_binding_id
            != _source_cap_binding_id(
                evidence.context_id,
                evidence.context_key,
                evidence.total_physical_row_cap,
            )
            or evidence.development_scope_id is not None
        ):
            _fail("confirmatory cap evidence is not the public registry value")
    elif (
        evidence.evidence_class
        is cold.ColdH2CapEvidenceClassV1
        .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
    ):
        if (
            evidence.context_id in registered
            or evidence.context_key in registered_keys
            or evidence.confirmatory_family_generation is not None
            or evidence.source_total_row_cap_binding_id is not None
            or evidence.context_specific_total_row_cap_key is not None
            or evidence.development_scope_id is None
        ):
            _fail("synthetic cap evidence impersonates confirmatory authority")
        _cid(evidence.development_scope_id, "synthetic development scope")
    else:
        _fail("unknown cold H2 cap-evidence class")
    if (
        type(evidence.context_key) is not str
        or not evidence.context_key
        or type(evidence.total_physical_row_cap) is not int
        or evidence.total_physical_row_cap <= 0
    ):
        _fail("total-row cap evidence is malformed")
    return {
        "schema": (
            "acfqp.v072_cold_h2_context_total_row_cap_evidence.v1"
        ),
        "schema_version": cold.SCHEMA_VERSION,
        "profile_key": cold.PROFILE_KEY,
        "context_id": evidence.context_id,
        "context_key": evidence.context_key,
        "total_physical_row_cap": evidence.total_physical_row_cap,
        "evidence_class": evidence.evidence_class.value,
        "confirmatory_family_generation": (
            evidence.confirmatory_family_generation
        ),
        "source_total_row_cap_binding_id": (
            evidence.source_total_row_cap_binding_id
        ),
        "context_specific_total_row_cap_key": (
            evidence.context_specific_total_row_cap_key
        ),
        "development_scope_id": evidence.development_scope_id,
        "preregistration_binding": {
            "kind": "NOT_FINALIZED",
            "reason": (
                "PUBLIC_ONLY_CAP_AUTHORITY_PRECEDES_FINAL_ANCHORED_"
                "CONFIRMATORY_PREREGISTRATION"
            ),
        },
        "cap_semantics": (
            "TOTAL_ROOT_PLUS_DISCOVERY_CHILD_ACTION_ROWS_PER_CONTEXT"
        ),
        "root_subcap_claimed": False,
        "child_state_subcap_claimed": False,
        "child_row_subcap_claimed": False,
    }


def _cap_evidence_id(
    evidence: cold.ColdH2ContextTotalRowCapEvidenceV1,
) -> str:
    result = _content_id("cap_evidence", _cap_evidence_payload(evidence))
    if evidence.cap_evidence_id != result:
        _fail("cap-evidence ID is not independently reproducible")
    return result


def _cap_evidence_document(
    evidence: cold.ColdH2ContextTotalRowCapEvidenceV1,
) -> dict[str, Any]:
    payload = _cap_evidence_payload(evidence)
    return {**payload, "cap_evidence_id": _cap_evidence_id(evidence)}


def _confirmatory_registry_payload(
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], str]:
    contexts = prereg.registered_heldout_public_contexts_v2()
    evidence_documents: list[dict[str, Any]] = []
    evidence_ids: list[str] = []
    for context in contexts:
        evidence_payload = {
            "schema": (
                "acfqp.v072_cold_h2_context_total_row_cap_evidence.v1"
            ),
            "schema_version": cold.SCHEMA_VERSION,
            "profile_key": cold.PROFILE_KEY,
            "context_id": context.context_id,
            "context_key": context.context_key,
            "total_physical_row_cap": (
                context.maximum_physical_rows_per_confidence_epoch
            ),
            "evidence_class": "CONFIRMATORY_REGISTERED",
            "confirmatory_family_generation": (
                prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "source_total_row_cap_binding_id": _source_cap_binding_id(
                context.context_id,
                context.context_key,
                context.maximum_physical_rows_per_confidence_epoch,
            ),
            "context_specific_total_row_cap_key": _source_cap_key(
                context.context_id,
                context.context_key,
            ),
            "development_scope_id": None,
            "preregistration_binding": {
                "kind": "NOT_FINALIZED",
                "reason": (
                    "PUBLIC_ONLY_CAP_AUTHORITY_PRECEDES_FINAL_ANCHORED_"
                    "CONFIRMATORY_PREREGISTRATION"
                ),
            },
            "cap_semantics": (
                "TOTAL_ROOT_PLUS_DISCOVERY_CHILD_ACTION_ROWS_PER_CONTEXT"
            ),
            "root_subcap_claimed": False,
            "child_state_subcap_claimed": False,
            "child_row_subcap_claimed": False,
        }
        evidence_id = _content_id("cap_evidence", evidence_payload)
        evidence_ids.append(evidence_id)
        evidence_documents.append(
            {**evidence_payload, "cap_evidence_id": evidence_id}
        )
    total_cap = sum(
        item.maximum_physical_rows_per_confidence_epoch
        for item in contexts
    )
    row_epoch_cap = 2 * total_cap
    if (
        tuple(
            item.maximum_physical_rows_per_confidence_epoch
            for item in contexts
        )
        != (96, 48, 96)
        or prereg.MAX_EPOCHS != 3
        or prereg.MAX_PROMOTIONS_PER_PHYSICAL_ROW != 2
        or prereg.MAX_PROMOTION_AUTHORITIES_PER_CONTEXT != 2
        or row_epoch_cap != prereg.MAX_ROW_EPOCH_AUTHORITIES_PER_ARM
        or row_epoch_cap != confidence_v2.MAX_ARM_ROW_EPOCH_AUTHORITIES
        or total_cap
        * (cold.DISCOVERY_DRAWS_PER_ROW + cold.VALIDATION_DRAWS_PER_ROW)
        != prereg.MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM
    ):
        _fail("public cap registry and confidence authority are inconsistent")
    payload = {
        "schema": "acfqp.v072_cold_h2_confirmatory_cap_registry.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "profile_key": cold.PROFILE_KEY,
        "confirmatory_family_generation": (
            prereg.CONFIRMATORY_FAMILY_GENERATION
        ),
        "preregistration_binding": {
            "kind": "NOT_FINALIZED",
            "reason": (
                "PUBLIC_ONLY_CAP_REGISTRY_PRECEDES_FINAL_ANCHORED_"
                "CONFIRMATORY_PREREGISTRATION"
            ),
        },
        "context_cap_evidence_ids": evidence_ids,
        "context_total_physical_row_caps": [
            {
                "context_id": item.context_id,
                "context_key": item.context_key,
                "total_physical_row_cap": (
                    item.maximum_physical_rows_per_confidence_epoch
                ),
            }
            for item in contexts
        ],
        "total_physical_row_cap_sum": total_cap,
        "maximum_confidence_epochs_per_physical_row": prereg.MAX_EPOCHS,
        "maximum_promotions_per_physical_row": (
            prereg.MAX_PROMOTIONS_PER_PHYSICAL_ROW
        ),
        "maximum_promotion_authorities_per_context": (
            prereg.MAX_PROMOTION_AUTHORITIES_PER_CONTEXT
        ),
        "row_epoch_authority_cap_rule": (
            prereg.ROW_EPOCH_AUTHORITY_CAP_RULE
        ),
        "maximum_row_epoch_authorities_per_arm": row_epoch_cap,
        "confidence_authority_row_epoch_cap_per_arm": (
            confidence_v2.MAX_ARM_ROW_EPOCH_AUTHORITIES
        ),
        "maximum_initial_accepted_draw_cap_per_arm": (
            prereg.MAX_INITIAL_ACCEPTED_DRAW_CAP_PER_ARM
        ),
    }
    registry_id = _content_id("cap_registry", payload)
    return payload, tuple(evidence_documents), registry_id


def _independent_counters(
    *,
    root_rows: tuple[cold.ColdRowEvidenceV1, ...],
    child_catalogues: tuple[cold.ColdPublicCatalogueV1, ...],
    child_rows: tuple[cold.ColdRowEvidenceV1, ...],
    active_descriptor_count: int,
    cap_evidence_id: str,
    context_total_physical_row_cap: int,
) -> dict[str, Any]:
    rows = (*root_rows, *child_rows)
    return {
        "cap_evidence_id": cap_evidence_id,
        "context_total_physical_row_cap": (
            context_total_physical_row_cap
        ),
        "root_catalogue_count": 1,
        "child_catalogue_count": len(child_catalogues),
        "root_action_row_count": len(root_rows),
        "child_action_row_count": len(child_rows),
        "total_action_row_count": len(rows),
        "cold_initial_row_count": sum(
            row.native_work.acquisition_purpose
            is cold.ColdRowAcquisitionPurposeV1.COLD_INITIAL
            for row in rows
        ),
        "incremental_promotion_row_count": sum(
            row.native_work.acquisition_purpose
            is (
                cold.ColdRowAcquisitionPurposeV1
                .INCREMENTAL_PROMOTION
            )
            for row in rows
        ),
        "incremental_new_child_row_count": sum(
            row.native_work.acquisition_purpose
            is (
                cold.ColdRowAcquisitionPurposeV1
                .INCREMENTAL_NEW_CHILD
            )
            for row in rows
        ),
        "matched_direct_checkpoint_row_count": sum(
            row.native_work.acquisition_purpose
            is (
                cold.ColdRowAcquisitionPurposeV1
                .MATCHED_DIRECT_CHECKPOINT
            )
            for row in rows
        ),
        "discovery_active_descriptor_count": active_descriptor_count,
        "discovery_child_state_count": len(child_catalogues),
        "discovery_support_descriptor_count": sum(
            len(row.discovery_support) for row in rows
        ),
        "validation_novel_descriptor_count": sum(
            len(row.validation_novel) for row in rows
        ),
        "discovery_draws": sum(
            row.native_work.discovery_draws for row in rows
        ),
        "validation_draws": sum(
            row.native_work.validation_draws for row in rows
        ),
        "total_draws": sum(
            row.native_work.discovery_draws
            + row.native_work.validation_draws
            for row in rows
        ),
        "discovery_random_word_calls": sum(
            row.native_work.discovery_random_word_calls for row in rows
        ),
        "validation_random_word_calls": sum(
            row.native_work.validation_random_word_calls for row in rows
        ),
        "total_random_word_calls": sum(
            row.native_work.discovery_random_word_calls
            + row.native_work.validation_random_word_calls
            for row in rows
        ),
        "discovery_rejections": sum(
            row.native_work.discovery_rejections for row in rows
        ),
        "validation_rejections": sum(
            row.native_work.validation_rejections for row in rows
        ),
        "total_rejections": sum(
            row.native_work.discovery_rejections
            + row.native_work.validation_rejections
            for row in rows
        ),
        "public_root_state_queries": 1,
        "public_canonical_state_queries": 1 + active_descriptor_count,
        "public_legal_catalogue_queries": 1 + len(child_catalogues),
        "row_evidence_reads": len(rows),
        "validation_novel_child_expansions": 0,
        "planner_calls": 0,
        "audit_calls": 0,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "cap_checked_after_complete_derivation": 1,
        "native_physical_charge_count": 1,
    }


def _counters_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_h2_closure_native_counters.v1",
        "schema_version": cold.SCHEMA_VERSION,
        **dict(values),
    }


def _assert_counters(
    claimed: cold.ColdH2ClosureNativeCountersV1,
    expected: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    if type(claimed) is not cold.ColdH2ClosureNativeCountersV1:
        _fail("closure native counters have a noncanonical type")
    if any(
        getattr(claimed, field_name) != value
        for field_name, value in expected.items()
    ):
        _fail("closure native counters differ from independent replay")
    payload = _counters_payload(expected)
    counters_id = _content_id("counters", payload)
    if claimed.counters_id != counters_id:
        _fail("closure counter ID is not independently reproducible")
    return counters_id, payload


def _consumer_routes(arm: str) -> tuple[str, ...]:
    if arm not in prereg.ARM_ORDER:
        _fail("closure consumer arm is not preregistered")
    if arm == "MATCHED_DIRECT_GROUND":
        return ("DIRECT",)
    return ("DIRECT", "QUOTIENT")


def _consumer_profile_payload(arm: str) -> dict[str, Any]:
    routes = _consumer_routes(arm)
    return {
        "schema": "acfqp.v072_cold_h2_consumer_profile.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "profile_key": cold.PROFILE_KEY,
        "arm": arm,
        "consumer_routes": list(routes),
        "ground_model_built": True,
        "quotient_model_built": routes == ("DIRECT", "QUOTIENT"),
        "native_physical_charge_count": 1,
    }


def _consumer_profile_id(arm: str) -> str:
    return _content_id("consumer_profile", _consumer_profile_payload(arm))


def _consumer_profile_document(arm: str) -> dict[str, Any]:
    payload = _consumer_profile_payload(arm)
    return {
        **payload,
        "consumer_profile_id": _consumer_profile_id(arm),
    }


def _charge_payload(
    *,
    logical_occurrence_id: str,
    physical_bundle_id: str,
    physical_evidence_ids: tuple[str, ...],
    counters_id: str,
    cap_evidence_id: str,
    arm: str,
    consumer_profile_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_h2_shared_logical_charge.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "logical_occurrence_id": logical_occurrence_id,
        "physical_bundle_id": physical_bundle_id,
        "physical_evidence_ids": list(physical_evidence_ids),
        "counters_id": counters_id,
        "cap_evidence_id": cap_evidence_id,
        "arm": arm,
        "consumer_profile_id": consumer_profile_id,
        "consumer_routes": list(_consumer_routes(arm)),
        "native_physical_charge_count": 1,
        "shared_charge_rule": cold.SHARED_CHARGE_RULE,
    }


def _bundle_payload(
    *,
    context_id: str,
    arm: str,
    consumer_profile_id: str,
    root_state_id: str,
    root_catalogue_id: str,
    child_state_ids: tuple[str, ...],
    child_catalogue_ids: tuple[str, ...],
    root_row_ids: tuple[str, ...],
    child_row_ids: tuple[str, ...],
    physical_evidence_ids: tuple[str, ...],
    cap_evidence_id: str,
    cap_evidence_class: str,
    confirmatory_cap_registry_id: str | None,
    counters_id: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_cold_h2_closure_bundle.v1",
        "schema_version": cold.SCHEMA_VERSION,
        "proposed_contract_version": cold.PROPOSED_CONTRACT_VERSION,
        "profile_key": cold.PROFILE_KEY,
        "context_id": context_id,
        "arm": arm,
        "consumer_profile_id": consumer_profile_id,
        "horizon": cold.HORIZON,
        "root_state_record_id": root_state_id,
        "root_catalogue_id": root_catalogue_id,
        "child_state_record_ids": list(child_state_ids),
        "child_catalogue_ids": list(child_catalogue_ids),
        "root_row_evidence_ids": list(root_row_ids),
        "child_row_evidence_ids": list(child_row_ids),
        "physical_evidence_ids": list(physical_evidence_ids),
        "cap_evidence_id": cap_evidence_id,
        "cap_evidence_class": cap_evidence_class,
        "confirmatory_cap_registry_id": confirmatory_cap_registry_id,
        "counters_id": counters_id,
        "discovery_expansion_rule": cold.DISCOVERY_EXPANSION_RULE,
        "validation_novel_rule": cold.VALIDATION_NOVEL_RULE,
        "validation_novel_child_expansion_allowed": False,
        "observation_only": True,
        "planner_calls": 0,
        "audit_calls": 0,
        "kernel_calls": 0,
        "hidden_law_queries": 0,
        "route_independent_physical_evidence": True,
    }


def _independent_public_catalogue(
    public_graph: cold.ColdH2PublicGraphProtocolV1,
    state: cold.ColdPublicStateV1,
    remaining_horizon: int,
) -> tuple[
    cold.ColdPublicCatalogueV1,
    str,
]:
    actions = public_graph.legal_actions_v1(
        state,
        remaining_horizon,
    )
    if (
        type(actions) is not tuple
        or not actions
        or any(type(item) is not cold.ColdPublicActionV1 for item in actions)
    ):
        _fail("independent public semantics returned invalid legal actions")
    actions = tuple(sorted(actions, key=_action_id))
    if (
        len({_action_id(item) for item in actions}) != len(actions)
        or len({item.semantic_action_id for item in actions})
        != len(actions)
    ):
        _fail("independent public legal catalogue is duplicated")
    expected = cold.ColdPublicCatalogueV1(
        public_graph.context_id,
        state,
        remaining_horizon,
        actions,
    )
    return expected, _catalogue_id(expected)


@dataclass(frozen=True, slots=True)
class V072ColdH2IndependentVerificationV1:
    closure_id: str
    independently_recomputed_closure_id: str
    shared_charge_id: str
    document_digest: str
    context_id: str
    root_row_count: int
    child_state_count: int
    child_row_count: int
    independent_public_semantics_replay: bool = True
    independent_row_inventory_replay: bool = True
    production_closure_builder_called: bool = False
    planner_calls: int = 0
    audit_calls: int = 0
    kernel_calls: int = 0
    hidden_law_queries: int = 0
    valid: bool = True

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.closure_id, "verified closure"),
            (
                self.independently_recomputed_closure_id,
                "independently replayed closure",
            ),
            (self.shared_charge_id, "verified shared charge"),
            (self.document_digest, "verified closure document"),
            (self.context_id, "verified closure context"),
        ):
            _cid(value, field_name)
        if (
            self.closure_id != self.independently_recomputed_closure_id
            or self.root_row_count <= 0
            or self.child_state_count < 0
            or self.child_row_count < 0
            or self.independent_public_semantics_replay is not True
            or self.independent_row_inventory_replay is not True
            or self.production_closure_builder_called is not False
            or any(
                value != 0
                for value in (
                    self.planner_calls,
                    self.audit_calls,
                    self.kernel_calls,
                    self.hidden_law_queries,
                )
            )
            or self.valid is not True
        ):
            _fail("independent cold H2 verification is incomplete")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_h2_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "closure_id": self.closure_id,
            "independently_recomputed_closure_id": (
                self.independently_recomputed_closure_id
            ),
            "shared_charge_id": self.shared_charge_id,
            "document_digest": self.document_digest,
            "context_id": self.context_id,
            "root_row_count": self.root_row_count,
            "child_state_count": self.child_state_count,
            "child_row_count": self.child_row_count,
            "independent_public_semantics_replay": True,
            "independent_row_inventory_replay": True,
            "production_closure_builder_called": False,
            "planner_calls": 0,
            "audit_calls": 0,
            "kernel_calls": 0,
            "hidden_law_queries": 0,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _verification_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v072_cold_h2_closure_independently_v1(
    *,
    public_graph: cold.ColdH2PublicGraphProtocolV1,
    authoritative_row_evidence: tuple[cold.ColdRowEvidenceV1, ...],
    claimed: cold.V072ColdH2ClosureBundleV1,
) -> V072ColdH2IndependentVerificationV1:
    """Replay the closure without invoking production closure construction."""

    if (
        not isinstance(public_graph, cold.ColdH2PublicGraphProtocolV1)
        or public_graph.horizon != cold.HORIZON
        or type(claimed) is not cold.V072ColdH2ClosureBundleV1
    ):
        _fail("independent verifier requires public H2 semantics and V1 bundle")
    context_id = _cid(public_graph.context_id, "public graph context")
    if claimed.context_id != context_id:
        _fail("claimed closure is bound to a different public context")
    cap_evidence_id = _cap_evidence_id(claimed.cap_evidence)
    if claimed.cap_evidence.context_id != context_id:
        _fail("closure cap evidence was transplanted across contexts")
    consumer_profile_id = _consumer_profile_id(claimed.arm)
    if (
        type(claimed.consumer_profile) is not cold.ColdH2ConsumerProfileV1
        or claimed.consumer_profile.arm != claimed.arm
        or claimed.consumer_profile.consumer_routes
        != _consumer_routes(claimed.arm)
        or claimed.consumer_profile.native_physical_charge_count != 1
        or claimed.consumer_profile.consumer_profile_id
        != consumer_profile_id
    ):
        _fail("closure arm/consumer profile was transplanted")
    registry_payload, registry_evidence_documents, registry_id = (
        _confirmatory_registry_payload()
    )
    if (
        claimed.cap_evidence.evidence_class
        is cold.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
    ):
        if (
            claimed.confirmatory_cap_registry_id != registry_id
            or cap_evidence_id
            not in {
                item["cap_evidence_id"]
                for item in registry_evidence_documents
            }
        ):
            _fail("confirmatory cap evidence is not registry-bound")
    elif claimed.confirmatory_cap_registry_id is not None:
        _fail("synthetic closure claimed the confirmatory cap registry")
    if (
        type(authoritative_row_evidence) is not tuple
        or not authoritative_row_evidence
        or any(
            type(item) is not cold.ColdRowEvidenceV1
            for item in authoritative_row_evidence
        )
    ):
        _fail("authoritative row evidence is not one immutable typed tuple")
    authoritative_by_key: dict[
        tuple[str, int, str],
        cold.ColdRowEvidenceV1,
    ] = {}
    authoritative_id_by_key: dict[tuple[str, int, str], str] = {}
    for row in authoritative_row_evidence:
        if row.context_id != context_id:
            _fail("authoritative row evidence was transplanted by context")
        row_id = _row_id(row)
        if row.semantic_key in authoritative_by_key:
            _fail("authoritative row evidence duplicates a semantic key")
        authoritative_by_key[row.semantic_key] = row
        authoritative_id_by_key[row.semantic_key] = row_id

    root_state = public_graph.root_state_v1()
    if type(root_state) is not cold.ColdPublicStateV1:
        _fail("independent public root state is not canonical")
    canonical_root = public_graph.canonical_state_v1(root_state)
    if (
        type(canonical_root) is not cold.ColdPublicStateV1
        or canonical_root != root_state
        or _state_id(canonical_root) != _state_id(root_state)
    ):
        _fail("independent public root canonicalization changed")
    expected_root_catalogue, root_catalogue_id = (
        _independent_public_catalogue(
            public_graph,
            root_state,
            cold.HORIZON,
        )
    )
    if (
        claimed.root_state != root_state
        or _state_id(claimed.root_state) != _state_id(root_state)
        or claimed.root_catalogue != expected_root_catalogue
        or _catalogue_id(claimed.root_catalogue)
        != root_catalogue_id
    ):
        _fail("claimed root state/catalogue is incomplete or fabricated")
    expected_root_keys = tuple(
        (
            root_state.semantic_state_id,
            cold.HORIZON,
            action.semantic_action_id,
        )
        for action in expected_root_catalogue.actions
    )
    root_rows: list[cold.ColdRowEvidenceV1] = []
    for key, action in zip(
        expected_root_keys,
        expected_root_catalogue.actions,
    ):
        row = authoritative_by_key.get(key)
        if (
            row is None
            or row.state != root_state
            or row.action != action
        ):
            _fail("authoritative evidence omits a complete root legal row")
        root_rows.append(row)
    root_row_tuple = tuple(sorted(root_rows, key=_row_id))

    child_by_semantic_id: dict[str, cold.ColdPublicStateV1] = {}
    active_descriptor_count = 0
    for row in root_row_tuple:
        for descriptor in row.discovery_support:
            _descriptor_id(descriptor)
            if not descriptor.active_nonterminal:
                continue
            active_descriptor_count += 1
            assert descriptor.successor_state is not None
            canonical = public_graph.canonical_state_v1(
                descriptor.successor_state
            )
            if (
                type(canonical) is not cold.ColdPublicStateV1
                or canonical != descriptor.successor_state
                or _state_id(canonical)
                != _state_id(descriptor.successor_state)
            ):
                _fail("discovery-known child state is not canonical")
            previous = child_by_semantic_id.setdefault(
                canonical.semantic_state_id,
                canonical,
            )
            if previous != canonical:
                _fail("one child identity has conflicting public documents")
        # Validation novelty is content-verified but deliberately never
        # canonicalized into a state closure or queried for legal actions.
        for descriptor in row.validation_novel:
            _descriptor_id(descriptor)
    child_states = tuple(
        sorted(child_by_semantic_id.values(), key=_state_id)
    )
    expected_child_catalogues = tuple(
        sorted(
            (
                _independent_public_catalogue(
                    public_graph,
                    state,
                    1,
                )[0]
                for state in child_states
            ),
            key=_catalogue_id,
        )
    )
    if (
        tuple(_state_id(item) for item in claimed.child_states)
        != tuple(_state_id(item) for item in child_states)
        or claimed.child_states != child_states
        or tuple(
            _catalogue_id(item) for item in claimed.child_catalogues
        )
        != tuple(
            _catalogue_id(item) for item in expected_child_catalogues
        )
        or claimed.child_catalogues != expected_child_catalogues
    ):
        _fail(
            "claimed child closure expands validation novelty or omits "
            "discovery support"
        )
    expected_child_keys: list[tuple[str, int, str]] = []
    child_rows: list[cold.ColdRowEvidenceV1] = []
    for catalogue in expected_child_catalogues:
        for action in catalogue.actions:
            key = (
                catalogue.state.semantic_state_id,
                1,
                action.semantic_action_id,
            )
            expected_child_keys.append(key)
            row = authoritative_by_key.get(key)
            if (
                row is None
                or row.state != catalogue.state
                or row.action != action
            ):
                _fail("authoritative child catalogue lacks one H1 row")
            child_rows.append(row)
    child_row_tuple = tuple(sorted(child_rows, key=_row_id))
    expected_key_set = set(expected_root_keys) | set(expected_child_keys)
    if set(authoritative_by_key) != expected_key_set:
        _fail(
            "authoritative inventory contains an extra/non-discovery child row"
        )
    total_action_row_count = len(expected_root_keys) + len(
        expected_child_keys
    )
    if (
        total_action_row_count
        > claimed.cap_evidence.total_physical_row_cap
    ):
        _fail(
            "complete independently derived root-plus-child inventory "
            "exceeds its context total-row cap"
        )

    claimed_root_ids = tuple(_row_id(item) for item in claimed.root_rows)
    claimed_child_ids = tuple(_row_id(item) for item in claimed.child_rows)
    expected_root_ids = tuple(_row_id(item) for item in root_row_tuple)
    expected_child_ids = tuple(_row_id(item) for item in child_row_tuple)
    if (
        claimed_root_ids != expected_root_ids
        or claimed_child_ids != expected_child_ids
        or claimed.root_rows != root_row_tuple
        or claimed.child_rows != child_row_tuple
    ):
        _fail("claimed row inventory is missing, extra, or fabricated")

    expected_counter_values = _independent_counters(
        root_rows=root_row_tuple,
        child_catalogues=expected_child_catalogues,
        child_rows=child_row_tuple,
        active_descriptor_count=active_descriptor_count,
        cap_evidence_id=cap_evidence_id,
        context_total_physical_row_cap=(
            claimed.cap_evidence.total_physical_row_cap
        ),
    )
    counters_id, counters_payload = _assert_counters(
        claimed.counters,
        expected_counter_values,
    )
    child_state_ids = tuple(_state_id(item) for item in child_states)
    child_catalogue_ids = tuple(
        _catalogue_id(item) for item in expected_child_catalogues
    )
    physical_evidence_ids = tuple(
        sorted(
            row.physical_evidence_id
            for row in (*root_row_tuple, *child_row_tuple)
        )
    )
    bundle_payload = _bundle_payload(
        context_id=context_id,
        arm=claimed.arm,
        consumer_profile_id=consumer_profile_id,
        root_state_id=_state_id(root_state),
        root_catalogue_id=root_catalogue_id,
        child_state_ids=child_state_ids,
        child_catalogue_ids=child_catalogue_ids,
        root_row_ids=expected_root_ids,
        child_row_ids=expected_child_ids,
        physical_evidence_ids=physical_evidence_ids,
        cap_evidence_id=cap_evidence_id,
        cap_evidence_class=claimed.cap_evidence.evidence_class.value,
        confirmatory_cap_registry_id=(
            claimed.confirmatory_cap_registry_id
        ),
        counters_id=counters_id,
    )
    closure_id = _content_id("bundle", bundle_payload)
    if (
        claimed.shared_charge.physical_bundle_id != closure_id
        or claimed.observation_only is not True
        or claimed.validation_novel_child_expansion_allowed is not False
        or claimed.route_independent_physical_evidence is not True
    ):
        _fail("claimed closure ID/authority flags fail independent replay")
    charge = claimed.shared_charge
    if type(charge) is not cold.ColdH2SharedLogicalChargeV1:
        _fail("claimed closure lacks its typed shared charge")
    _cid(charge.logical_occurrence_id, "charge logical occurrence")
    expected_charge_payload = _charge_payload(
        logical_occurrence_id=charge.logical_occurrence_id,
        physical_bundle_id=closure_id,
        physical_evidence_ids=physical_evidence_ids,
        counters_id=counters_id,
        cap_evidence_id=cap_evidence_id,
        arm=claimed.arm,
        consumer_profile_id=consumer_profile_id,
    )
    charge_id = _content_id("charge", expected_charge_payload)
    if (
        charge.physical_bundle_id != closure_id
        or charge.physical_evidence_ids != physical_evidence_ids
        or charge.counters_id != counters_id
        or charge.cap_evidence_id != cap_evidence_id
        or charge.arm != claimed.arm
        or charge.consumer_profile_id != consumer_profile_id
        or charge.consumer_routes != _consumer_routes(claimed.arm)
        or charge.native_physical_charge_count != 1
        or charge.charge_id != charge_id
        or claimed.counters.native_physical_charge_count != 1
    ):
        _fail("direct/quotient physical work was duplicated or mischarged")

    document = {
        **bundle_payload,
        "consumer_profile": _consumer_profile_document(claimed.arm),
        "root_state": _state_document(root_state),
        "root_catalogue": _catalogue_document(
            expected_root_catalogue
        ),
        "child_states": [
            _state_document(item) for item in child_states
        ],
        "child_catalogues": [
            _catalogue_document(item)
            for item in expected_child_catalogues
        ],
        "root_rows": [_row_document(item) for item in root_row_tuple],
        "child_rows": [_row_document(item) for item in child_row_tuple],
        "cap_evidence": _cap_evidence_document(claimed.cap_evidence),
        "counters": {**counters_payload, "counters_id": counters_id},
        "shared_charge": {
            **expected_charge_payload,
            "charge_id": charge_id,
        },
        "shared_charge_id": charge_id,
        "closure_id": closure_id,
    }
    document_digest = hashlib.sha256(
        b"acfqp:v072-cold-h2-independent-document:v1\x00"
        + canonical_json_bytes(document)
    ).hexdigest()
    return V072ColdH2IndependentVerificationV1(
        closure_id,
        closure_id,
        charge_id,
        document_digest,
        context_id,
        len(root_row_tuple),
        len(child_states),
        len(child_row_tuple),
    )


__all__ = [
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V072ColdH2IndependentVerificationV1",
    "V072ColdH2IndependentVerificationViolation",
    "verify_v072_cold_h2_closure_independently_v1",
]
