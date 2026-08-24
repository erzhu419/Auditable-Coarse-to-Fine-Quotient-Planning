#!/usr/bin/env python3
"""Execute the frozen V182r2 campaign once; never reuse its identity."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp import construction_k7_open_world_total_machine_campaign_v182r2 as campaign
from acfqp import construction_k7_open_world_total_machine_execution_preregistration_v182r2 as preregistration
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp" / "v182r2-open-world-total-machine-campaign"
PROGRESS_ROOT = OUTPUT_ROOT / "progress"
CAMPAIGN_PATH = OUTPUT_ROOT / "CAMPAIGN.json"
FAILURE_PATH = OUTPUT_ROOT / "FAILURE.json"


def _write_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o400,
    )
    try:
        if os.write(descriptor, raw) != len(raw):
            raise OSError("V182r2 output short write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    frozen = preregistration.freeze_open_world_total_machine_execution_preregistration_v182r2()
    if OUTPUT_ROOT.exists():
        raise RuntimeError("V182r2 output root exists; same-identity rerun forbidden")
    OUTPUT_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    PROGRESS_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        document = campaign.run_open_world_total_machine_campaign_v182r2(
            PROGRESS_ROOT,
            execution_preregistration_id=frozen.execution_preregistration_id,
        )
        raw = canonical_json_bytes(document)
        _write_once(CAMPAIGN_PATH, raw)
    except BaseException as error:
        if not FAILURE_PATH.exists() and not CAMPAIGN_PATH.exists():
            payload = {
                "schema": "acfqp.open_world_total_machine_campaign_failure.v182r2",
                "execution_preregistration_id": frozen.execution_preregistration_id,
                "failed_predecessor_failure_id": (
                    preregistration.FAILED_PREDECESSOR_FAILURE_ID
                ),
                "failure_type": type(error).__name__,
                "failure_message": str(error),
                "progress_checkpoint_count": len(list(PROGRESS_ROOT.glob("*.json"))),
                "same_identity_rerun_forbidden": True,
                "scientific_success_claimed": False,
                "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
                "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
                "official_execution_allowed": False,
            }
            failure = {
                **payload,
                "failure_id": domains.extension_content_id_v182r2(
                    domains.CONSTRUCTION_K7_FAILURE_V182R2_DOMAIN,
                    payload,
                ),
            }
            _write_once(FAILURE_PATH, canonical_json_bytes(failure))
        raise
    print(
        canonical_json_bytes(
            {
                "execution_preregistration_id": frozen.execution_preregistration_id,
                "campaign_id": document["campaign_id"],
                "campaign_byte_count": len(raw),
                "campaign_sha256": hashlib.sha256(raw).hexdigest(),
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
