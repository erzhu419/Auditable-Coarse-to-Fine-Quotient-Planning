#!/usr/bin/env python3
"""Run the exact preregistered V181r6 campaign once and retain its terminal."""

from __future__ import annotations

import json
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v181r6 as domains
from acfqp import construction_k7_open_world_campaign_v181r6 as campaign
from acfqp import construction_k7_open_world_execution_preregistration_v181r6 as prereg
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
PROGRESS = BASE / "v181r6_open_world_progress"
SUCCESS = BASE / "v181r6_open_world_campaign.json"
FAILURE = BASE / "v181r6_open_world_campaign_failure.json"


def _last_checkpoint() -> dict | None:
    paths = sorted(PROGRESS.glob("checkpoint-*.json"))
    return json.loads(paths[-1].read_bytes()) if paths else None


def _write_failure(error: BaseException) -> None:
    last = _last_checkpoint()
    payload = {
        "schema": "acfqp.open_world_campaign_failure.v181r6",
        "execution_preregistration_id": prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "target_outcome_run_started": True,
        "durable_checkpoint_count": len(list(PROGRESS.glob("checkpoint-*.json"))),
        "last_durable_progress_checkpoint_id": (
            last["progress_checkpoint_id"] if last is not None else None
        ),
        "last_resolution": (
            {
                key: last[key]
                for key in (
                    "stage",
                    "manifest_index",
                    "arm",
                    "block_index",
                    "occurrence_index",
                    "decision_index",
                )
            }
            if last is not None
            else None
        ),
        "same_identity_rerun_forbidden": True,
        "success_claimed": False,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v181r6(
            domains.CONSTRUCTION_K7_FAILURE_V181R6_DOMAIN,
            payload,
        ),
    }
    FAILURE.write_bytes(canonical_json_bytes(document))
    print("V181R6_FAILURE", document["failure_id"], flush=True)


def main() -> None:
    if SUCCESS.exists() or FAILURE.exists() or PROGRESS.exists():
        raise RuntimeError("V181r6 exact identity already has terminal or progress bytes")
    preregistration = prereg.freeze_open_world_execution_preregistration_v181r6()
    PROGRESS.mkdir(parents=True, exist_ok=False)
    try:
        result = campaign.run_open_world_campaign_v181r6(
            execution_preregistration_id=preregistration.execution_preregistration_id,
            progress_directory=PROGRESS,
        )
        with SUCCESS.open("xb") as stream:
            if stream.write(result.canonical_bytes) != len(result.canonical_bytes):
                raise RuntimeError("V181r6 campaign short write")
        print("V181R6_SUCCESS", result.campaign_id, flush=True)
    except BaseException as error:
        _write_failure(error)
        raise


if __name__ == "__main__":
    main()
