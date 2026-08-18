"""Total V20 boundary for adaptive residual acquisition.

The V19 statistical stop remains unchanged.  If its calibrated evidence is
insufficient, V20 returns a typed abstention after accounting the complete
available query pool; exhaustion is never reinterpreted as a positive model.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_adaptive_residual_factor_acquisition_v19 import (
    GenericAdaptiveResidualFactorAcquisitionV19Error,
    acquire_adaptive_residual_factor_v19,
    replay_adaptive_residual_factor_v19,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericTotalAdaptiveResidualAcquisitionV20Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericTotalAdaptiveResidualAcquisitionV20Error(message)


def _query_pool_facts(evidence: Mapping[str, Any]) -> tuple[int, int]:
    rows = evidence.get("raw_transition_rows")
    if type(rows) is not list or not rows:
        _fail("V20 residual query pool changed")
    contexts = set()
    for row in rows:
        selected = row.get("selected_action") if type(row) is dict else None
        if type(selected) is not dict:
            _fail("V20 residual query row changed")
        pre = row.get("pre_vector")
        key = selected.get("action_key")
        if type(pre) is not list or type(key) is not int:
            _fail("V20 residual query context changed")
        contexts.add((tuple(pre), key))
    return len(contexts), len(rows)


def acquire_total_adaptive_residual_factor_v20(
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    query_count, row_count = _query_pool_facts(evidence)
    arm = (
        "RESIDUAL_FACTOR_PRIOR_ON"
        if prior_library is not None
        else "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
    )
    try:
        predecessor = acquire_adaptive_residual_factor_v19(
            evidence,
            prior_library=prior_library,
            confidence_denominator=confidence_denominator,
        )
    except GenericAdaptiveResidualFactorAcquisitionV19Error as error:
        if str(error) != "V19 adaptive residual acquisition did not stop on available evidence":
            raise
        payload = {
            "schema": "acfqp.total_adaptive_residual_acquisition.v20",
            "status": "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE",
            "arm": arm,
            "prior_library_id": None
            if prior_library is None
            else prior_library.get("residual_factor_library_id"),
            "ground_support_labels": query_count,
            "raw_transition_rows_consumed": row_count,
            "candidate": None,
            "predecessor_acquisition": None,
            "confidence_denominator": confidence_denominator,
            "successful_statistical_stop": False,
            "available_query_pool_exhausted_without_issuance": True,
            "query_pool_exhaustion_used_as_positive_stop": False,
            "same_generic_synthesizer_and_stop_rule": True,
            "proposal_only_not_safety_authority": True,
            "ground_fact_transfer_present": False,
            "complete_residual_world_model_synthesized": False,
        }
    else:
        if predecessor["ground_support_labels"] > query_count:
            _fail("V20 predecessor consumed more than the available query pool")
        payload = {
            "schema": "acfqp.total_adaptive_residual_acquisition.v20",
            "status": "STATISTICAL_PROPOSAL_ISSUED",
            "arm": arm,
            "prior_library_id": predecessor["prior_library_id"],
            "ground_support_labels": predecessor["ground_support_labels"],
            "raw_transition_rows_consumed": predecessor[
                "raw_transition_rows_consumed"
            ],
            "candidate": predecessor["candidate"],
            "predecessor_acquisition": predecessor,
            "confidence_denominator": confidence_denominator,
            "successful_statistical_stop": True,
            "available_query_pool_exhausted_without_issuance": False,
            "query_pool_exhaustion_used_as_positive_stop": False,
            "same_generic_synthesizer_and_stop_rule": True,
            "proposal_only_not_safety_authority": True,
            "ground_fact_transfer_present": False,
            "complete_residual_world_model_synthesized": False,
        }
    return {
        **payload,
        "total_acquisition_id": hashlib.sha256(
            b"acfqp:total-adaptive-residual-acquisition:v20\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def replay_total_adaptive_residual_factor_v20(
    acquisition: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any]:
    query_count, row_count = _query_pool_facts(evidence)
    if acquisition.get("status") == "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE":
        if (
            acquisition.get("ground_support_labels") != query_count
            or acquisition.get("raw_transition_rows_consumed") != row_count
            or acquisition.get("candidate") is not None
            or acquisition.get("predecessor_acquisition") is not None
            or acquisition.get("successful_statistical_stop") is not False
            or acquisition.get("query_pool_exhaustion_used_as_positive_stop") is not False
        ):
            _fail("V20 abstention evidence changed")
        return {
            "total_acquisition_id": acquisition.get("total_acquisition_id"),
            "status": acquisition["status"],
            "full_query_stream_label_count": query_count,
            "full_query_stream_raw_transition_count": row_count,
            "failed_query_batch_count": None,
            "exact_support_on_full_frozen_query_stream": None,
            "abstention_replayed": True,
            "future_transition_prediction_authority_present": False,
        }
    if acquisition.get("status") != "STATISTICAL_PROPOSAL_ISSUED":
        _fail("V20 total acquisition status changed")
    replay = replay_adaptive_residual_factor_v19(
        acquisition.get("predecessor_acquisition"), evidence
    )
    return {
        "total_acquisition_id": acquisition.get("total_acquisition_id"),
        "status": acquisition["status"],
        **{key: value for key, value in replay.items() if key != "acquisition_id"},
        "abstention_replayed": False,
    }


__all__ = (
    "acquire_total_adaptive_residual_factor_v20",
    "replay_total_adaptive_residual_factor_v20",
)
