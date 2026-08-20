"""Compile a content-bound V52 acquisition into the verified V42 model format."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp import generic_version_space_retaining_model_compiler_v51 as v51
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericCompilerReadyModelCompilerV52Error(ValueError):
    pass


_V52_ACQUISITION_DOMAIN = b"acfqp:generic-compiler-ready-acquisition:v52\x00"
_V52_BUNDLE_DOMAIN = b"acfqp:relation-covering-compiler-ready-acquisition:v52\x00"
_V51_ACQUISITION_DOMAIN = b"acfqp:generic-version-space-retaining-acquisition:v51\x00"
_V51_BUNDLE_DOMAIN = b"acfqp:relation-covering-version-space-retaining-acquisition:v51\x00"
_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"


def _fail(message: str) -> NoReturn:
    raise GenericCompilerReadyModelCompilerV52Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def compile_compiler_ready_model_v52(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    relation_covering_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V52 partial candidate type changed")
    if (
        type(source_complete_evidence) is not dict
        or type(relation_covering_acquisition) is not dict
    ):
        _fail("V52 source artifact type changed")
    schedule = relation_covering_acquisition.get("query_schedule")
    acquisition = relation_covering_acquisition.get("compiler_ready_acquisition")
    expected_schedule = schedule_relation_covering_queries_v39(
        source_complete_evidence
    )
    if (
        type(schedule) is not dict
        or canonical_json_bytes(schedule) != canonical_json_bytes(expected_schedule)
        or type(acquisition) is not dict
        or relation_covering_acquisition.get("schema")
        != "acfqp.relation_covering_compiler_ready_acquisition.v52"
        or relation_covering_acquisition.get("query_schedule_id")
        != schedule.get("query_schedule_id")
        or relation_covering_acquisition.get("compiler_ready_acquisition_id")
        != acquisition.get("compiler_ready_acquisition_id")
    ):
        _fail("V52 acquisition bundle join changed")
    acquisition_payload = {
        key: value
        for key, value in acquisition.items()
        if key != "compiler_ready_acquisition_id"
    }
    bundle_payload = {
        key: value
        for key, value in relation_covering_acquisition.items()
        if key != "relation_covering_compiler_ready_acquisition_id"
    }
    if (
        _content_id(_V52_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("compiler_ready_acquisition_id")
        or _content_id(_V52_BUNDLE_DOMAIN, bundle_payload)
        != relation_covering_acquisition.get(
            "relation_covering_compiler_ready_acquisition_id"
        )
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get(
            "residual_successor_version_space_consensus_required_before_issuance"
        )
        is not False
        or acquisition.get("nonempty_residual_version_space_required_before_issuance")
        is not True
        or acquisition.get(
            "every_batch_exact_residual_proposal_retained_by_compiler_required"
        )
        is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V52 requires a content-bound compiler-ready proposal")

    # Reuse the already verified V51 compile implementation through a local,
    # content-addressed compatibility view.  The view is never emitted as
    # scientific evidence; final provenance is rewritten to the V52 IDs.
    v51_payload = copy.deepcopy(acquisition_payload)
    v51_payload["schema"] = "acfqp.generic_version_space_retaining_acquisition.v51"
    v51_payload.pop("compiler_readiness_compute_events", None)
    v51_payload.pop("nonempty_residual_version_space_required_before_issuance", None)
    v51_payload["residual_successor_version_space_deferred_to_joint_compiler"] = True
    v51_acquisition = {
        **v51_payload,
        "version_space_retaining_acquisition_id": _content_id(
            _V51_ACQUISITION_DOMAIN, v51_payload
        ),
    }
    v51_bundle_payload = {
        "schema": "acfqp.relation_covering_version_space_retaining_acquisition.v51",
        "query_schedule": copy.deepcopy(schedule),
        "version_space_retaining_acquisition": v51_acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "version_space_retaining_acquisition_id": v51_acquisition[
            "version_space_retaining_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    v51_bundle = {
        **v51_bundle_payload,
        "relation_covering_version_space_retaining_acquisition_id": _content_id(
            _V51_BUNDLE_DOMAIN, v51_bundle_payload
        ),
    }
    model = v51.compile_version_space_retaining_model_v51(
        candidate, source_complete_evidence, v51_bundle
    )
    payload = {
        key: copy.deepcopy(value)
        for key, value in model.items()
        if key != "joint_successor_version_space_model_id"
    }
    payload.update(
        source_relation_covering_acquisition_id=relation_covering_acquisition[
            "relation_covering_compiler_ready_acquisition_id"
        ],
        source_learned_successor_acquisition_id=acquisition[
            "compiler_ready_acquisition_id"
        ],
        source_acquisition_protocol="COMPILER_READY_VERSION_SPACE_V52",
        nonempty_residual_version_space_used_as_acquisition_gate=True,
        v51_compile_implementation_reused_through_nonpersistent_content_view=True,
    )
    result = {
        **payload,
        "joint_successor_version_space_model_id": _content_id(
            _MODEL_DOMAIN, payload
        ),
    }
    v42.verify_joint_successor_version_space_model_v42(result)
    return result


__all__ = ("compile_compiler_ready_model_v52",)
