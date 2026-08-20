"""Immutable record of the failed preregistered V72 execution.

All six worker occurrences had returned to the parent before aggregation read
an absent schedule-accounting key.  No campaign document or occurrence bytes
were persisted, so the scientific identity is retired rather than rerun.
"""

from __future__ import annotations

import hashlib
from types import MappingProxyType
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


_PAYLOAD = {
    "schema": "acfqp.successor_version_space_registered_failure.v72",
    "preregistration_id": "79c720e3f6db4102b86467cb5af31107e6254e8695c7b42035fd49038d413c7b",
    "implementation_commit": "155c628",
    "preregistration_commit": "2d9cbae",
    "producer_commit": "8fec663",
    "fresh_seed_families": {
        "BALANCED_BATCH_REFINEMENT": [731101, 731102],
        "COUPLED_EXCHANGE": [732101, 732102],
        "MAINTENANCE_CASCADE": [733101, 733102],
    },
    "failure_phase": "POST_WORKER_OCCURRENCE_AGGREGATION",
    "exception_type": "KeyError",
    "exception_message": "'outcome_blind_score_evaluation_count'",
    "failing_source": "src/acfqp/successor_version_space_campaign_core_v72.py",
    "failing_expression": (
        "shared_outcome_blind_query_schedule[outcome_blind_score_evaluation_count]"
    ),
    "all_worker_occurrence_results_materialized_in_parent_memory": True,
    "campaign_document_constructed": False,
    "campaign_id": None,
    "registered_gate_evaluated": False,
    "partial_occurrence_artifact_bytes_persisted": False,
    "same_preregistration_identity_rerun_allowed": False,
    "failure_preserved_before_any_corrected_successor_execution": True,
    "official_execution_allowed": False,
    "official_scalar_cost": None,
    "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
}
FAILURE_ID = hashlib.sha256(
    b"acfqp:construction-k7-successor-version-space-execution-failure:v72\x00"
    + canonical_json_bytes(_PAYLOAD)
).hexdigest()
REGISTERED_V72_FAILURE: Mapping[str, Any] = MappingProxyType(
    {**_PAYLOAD, "failure_id": FAILURE_ID}
)


__all__ = ("FAILURE_ID", "REGISTERED_V72_FAILURE")
