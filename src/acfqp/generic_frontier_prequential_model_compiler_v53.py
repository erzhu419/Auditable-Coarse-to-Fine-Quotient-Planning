"""Compile V53 all-frontier evidence through the verified V52/V42 path."""

from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import generic_compiler_ready_model_compiler_v52 as v52
from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericFrontierPrequentialModelCompilerV53Error(ValueError):
    pass


_V53_ACQUISITION_DOMAIN = b"acfqp:generic-frontier-prequential-acquisition:v53\x00"
_V53_BUNDLE_DOMAIN = b"acfqp:relation-covering-frontier-prequential-acquisition:v53\x00"
_V52_ACQUISITION_DOMAIN = b"acfqp:generic-compiler-ready-acquisition:v52\x00"
_V52_BUNDLE_DOMAIN = b"acfqp:relation-covering-compiler-ready-acquisition:v52\x00"
_MODEL_DOMAIN = b"acfqp:generic-joint-successor-version-space-model:v42\x00"


def _fail(message: str) -> NoReturn:
    raise GenericFrontierPrequentialModelCompilerV53Error(message)


def _content_id(domain: bytes, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(domain + canonical_json_bytes(payload)).hexdigest()


def compile_frontier_prequential_model_v53(
    candidate: PartialFactorCandidateV15,
    source_complete_evidence: Mapping[str, Any],
    relation_covering_acquisition: Mapping[str, Any],
) -> dict[str, Any]:
    if type(candidate) is not PartialFactorCandidateV15:
        _fail("V53 partial candidate type changed")
    if (
        type(source_complete_evidence) is not dict
        or type(relation_covering_acquisition) is not dict
    ):
        _fail("V53 source artifact type changed")
    schedule = relation_covering_acquisition.get("query_schedule")
    acquisition = relation_covering_acquisition.get(
        "frontier_prequential_acquisition"
    )
    expected_schedule = schedule_relation_covering_queries_v39(
        source_complete_evidence
    )
    if (
        type(schedule) is not dict
        or canonical_json_bytes(schedule) != canonical_json_bytes(expected_schedule)
        or type(acquisition) is not dict
        or relation_covering_acquisition.get("schema")
        != "acfqp.relation_covering_frontier_prequential_acquisition.v53"
        or relation_covering_acquisition.get("query_schedule_id")
        != schedule.get("query_schedule_id")
        or relation_covering_acquisition.get("frontier_prequential_acquisition_id")
        != acquisition.get("frontier_prequential_acquisition_id")
    ):
        _fail("V53 acquisition bundle join changed")
    acquisition_payload = {
        key: value
        for key, value in acquisition.items()
        if key != "frontier_prequential_acquisition_id"
    }
    bundle_payload = {
        key: value
        for key, value in relation_covering_acquisition.items()
        if key != "relation_covering_frontier_prequential_acquisition_id"
    }
    if (
        _content_id(_V53_ACQUISITION_DOMAIN, acquisition_payload)
        != acquisition.get("frontier_prequential_acquisition_id")
        or _content_id(_V53_BUNDLE_DOMAIN, bundle_payload)
        != relation_covering_acquisition.get(
            "relation_covering_frontier_prequential_acquisition_id"
        )
        or acquisition.get("status") != "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        or acquisition.get("heldout_exact_prediction") is not True
        or acquisition.get("heldout_rows_accessed_before_stop") is not False
        or acquisition.get(
            "every_retained_terminal_frontier_candidate_prequentially_checked"
        )
        is not True
        or acquisition.get(
            "every_retained_terminal_frontier_candidate_heldout_checked"
        )
        is not True
        or acquisition.get("nonempty_residual_version_space_required_before_issuance")
        is not True
        or acquisition.get("proposal_only_not_safety_authority") is not True
    ):
        _fail("V53 requires a content-bound all-frontier proposal")

    v52_payload = copy.deepcopy(acquisition_payload)
    v52_payload["schema"] = "acfqp.generic_compiler_ready_acquisition.v52"
    v52_payload.pop(
        "every_retained_terminal_frontier_candidate_prequentially_checked", None
    )
    v52_payload.pop(
        "every_retained_terminal_frontier_candidate_heldout_checked", None
    )
    v52_acquisition = {
        **v52_payload,
        "compiler_ready_acquisition_id": _content_id(
            _V52_ACQUISITION_DOMAIN, v52_payload
        ),
    }
    v52_bundle_payload = {
        "schema": "acfqp.relation_covering_compiler_ready_acquisition.v52",
        "query_schedule": copy.deepcopy(schedule),
        "compiler_ready_acquisition": v52_acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "compiler_ready_acquisition_id": v52_acquisition[
            "compiler_ready_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "nonempty_residual_version_space_used_as_readiness_gate": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    v52_bundle = {
        **v52_bundle_payload,
        "relation_covering_compiler_ready_acquisition_id": _content_id(
            _V52_BUNDLE_DOMAIN, v52_bundle_payload
        ),
    }
    model = v52.compile_compiler_ready_model_v52(
        candidate, source_complete_evidence, v52_bundle
    )
    payload = {
        key: copy.deepcopy(value)
        for key, value in model.items()
        if key != "joint_successor_version_space_model_id"
    }
    payload.update(
        source_relation_covering_acquisition_id=relation_covering_acquisition[
            "relation_covering_frontier_prequential_acquisition_id"
        ],
        source_learned_successor_acquisition_id=acquisition[
            "frontier_prequential_acquisition_id"
        ],
        source_acquisition_protocol="ALL_FRONTIER_PREQUENTIAL_V53",
        every_retained_terminal_frontier_candidate_prequentially_checked=True,
        every_retained_terminal_frontier_candidate_heldout_checked=True,
        v52_compile_implementation_reused_through_nonpersistent_content_view=True,
    )
    result = {
        **payload,
        "joint_successor_version_space_model_id": _content_id(
            _MODEL_DOMAIN, payload
        ),
    }
    v42.verify_joint_successor_version_space_model_v42(result)
    return result


__all__ = ("compile_frontier_prequential_model_v53",)
