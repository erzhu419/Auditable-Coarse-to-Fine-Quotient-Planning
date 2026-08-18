"""Totalized multi-target residual proposals over one shared query pool.

Each unknown target is passed through the unchanged V20 totalizer with the
same raw rows.  Physical ground labels are counted once by distinct
state-action context; per-target model-selection consumption is retained as a
separate compute/evidence axis and is never summed into physical sample cost.
Only action-conditioned zero-excess proposals are eligible for later abstract
planning.  Abstentions and non-actionable proposals remain explicit.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.generic_total_adaptive_residual_acquisition_v20 import (
    acquire_total_adaptive_residual_factor_v20,
    replay_total_adaptive_residual_factor_v20,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericMultiResidualAcquisitionV24Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericMultiResidualAcquisitionV24Error(message)


def _shared_pool_facts(evidence: Mapping[str, Any]) -> tuple[int, int]:
    rows = evidence.get("raw_transition_rows")
    if type(rows) is not list or not rows:
        _fail("V24 shared residual query pool changed")
    contexts = set()
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        if (
            type(action) is not dict
            or type(row.get("pre_vector")) is not list
            or type(action.get("action_key")) is not int
        ):
            _fail("V24 shared residual row changed")
        contexts.add((tuple(row["pre_vector"]), action["action_key"]))
    return len(contexts), len(rows)


def acquire_multi_residual_factors_v24(
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    targets = evidence.get("unknown_residual_target_columns")
    layout = evidence.get("layout")
    rows = evidence.get("raw_transition_rows")
    if (
        type(targets) is not list
        or not targets
        or targets != sorted(set(targets))
        or type(layout) is not dict
        or type(rows) is not list
    ):
        _fail("V24 residual target inventory changed")
    shared_labels, shared_rows = _shared_pool_facts(evidence)
    target_results = []
    actionable = []
    for target in targets:
        singleton_evidence = {
            "layout": layout,
            "unknown_residual_target_columns": [target],
            "raw_transition_rows": rows,
        }
        acquisition = acquire_total_adaptive_residual_factor_v20(
            singleton_evidence,
            prior_library=prior_library,
            confidence_denominator=confidence_denominator,
        )
        replay = replay_total_adaptive_residual_factor_v20(
            acquisition, singleton_evidence
        )
        candidate = acquisition.get("candidate")
        usable = (
            type(candidate) is dict
            and candidate.get("target_column") == target
            and type(candidate.get("action_field_binding")) is int
            and candidate.get("predictive_support_excess") == 0
        )
        row = {
            "target_column": target,
            "total_acquisition": acquisition,
            "full_shared_pool_replay": replay,
            "actionable_for_abstract_planning": usable,
        }
        target_results.append(row)
        if usable:
            actionable.append(candidate)
    payload = {
        "schema": "acfqp.generic_multi_residual_acquisition.v24",
        "arm": (
            "RESIDUAL_FACTOR_PRIOR_ON"
            if prior_library is not None
            else "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
        ),
        "prior_library_id": (
            None
            if prior_library is None
            else prior_library.get("residual_factor_library_id")
        ),
        "unknown_residual_target_columns": targets,
        "shared_physical_ground_support_labels": shared_labels,
        "shared_raw_transition_row_count": shared_rows,
        "per_target_model_selection_label_consumption": [
            {
                "target_column": row["target_column"],
                "ground_support_labels": row["total_acquisition"][
                    "ground_support_labels"
                ],
            }
            for row in target_results
        ],
        "per_target_label_consumption_summed_as_physical_samples": False,
        "target_results": target_results,
        "actionable_candidates": actionable,
        "actionable_target_columns": [row["target_column"] for row in actionable],
        "actionable_candidate_count": len(actionable),
        "abstention_count": sum(
            row["total_acquisition"]["status"]
            == "ABSTAINED_INSUFFICIENT_CALIBRATED_EVIDENCE"
            for row in target_results
        ),
        "same_shared_raw_query_pool_for_every_target": True,
        "proposal_only_not_safety_authority": True,
        "unmodeled_targets_remain_explicit": len(actionable) < len(targets),
        "complete_residual_world_model_synthesized": len(actionable) == len(targets),
        "global_exact_dynamics_claimed": False,
    }
    return {
        **payload,
        "multi_residual_acquisition_id": hashlib.sha256(
            b"acfqp:generic-multi-residual-acquisition:v24\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def replay_multi_residual_factors_v24(
    acquisition: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    expected = acquire_multi_residual_factors_v24(
        evidence,
        prior_library=prior_library,
        confidence_denominator=confidence_denominator,
    )
    if acquisition != expected:
        _fail("V24 multi-target acquisition differs from exact replay")
    return {
        "multi_residual_acquisition_id": expected["multi_residual_acquisition_id"],
        "shared_physical_ground_support_labels": expected[
            "shared_physical_ground_support_labels"
        ],
        "target_count": len(expected["target_results"]),
        "actionable_candidate_count": expected["actionable_candidate_count"],
        "abstention_count": expected["abstention_count"],
        "all_target_totalizers_reconstructed": True,
        "per_target_label_consumption_summed_as_physical_samples": False,
        "future_transition_prediction_authority_present": False,
    }


__all__ = (
    "acquire_multi_residual_factors_v24",
    "replay_multi_residual_factors_v24",
)
