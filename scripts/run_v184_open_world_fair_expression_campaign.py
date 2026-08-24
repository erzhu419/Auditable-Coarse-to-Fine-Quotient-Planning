#!/usr/bin/env python3
"""Execute the preregistered V184 campaign exactly once."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from acfqp import construction_k7_domain_registry_extension_v184 as domains
from acfqp import construction_k7_open_world_fair_expression_campaign_v184 as campaign
from acfqp import construction_k7_open_world_fair_expression_execution_preregistration_v184 as preregistration
from acfqp import construction_k7_open_world_fair_expression_independent_verifier_v184 as verifier
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / ".tmp" / "exact-freeze" / "v184_fair_expression_campaign"
CAMPAIGN_PATH = OUTPUT_ROOT / "CAMPAIGN.json"
VERIFICATION_PATH = OUTPUT_ROOT / "VERIFICATION.json"
FAILURE_PATH = OUTPUT_ROOT / "FAILURE.json"


def _write_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V184 output short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    frozen = preregistration.freeze_open_world_fair_expression_execution_preregistration_v184()
    if OUTPUT_ROOT.exists():
        raise RuntimeError("V184 output root exists; same-identity rerun forbidden")
    OUTPUT_ROOT.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        document = campaign.run_open_world_fair_expression_campaign_v184(
            execution_preregistration_id=frozen.execution_preregistration_id,
        )
        campaign_bytes = canonical_json_bytes(document)
        _write_once(CAMPAIGN_PATH, campaign_bytes)
        verification = verifier.verify_open_world_fair_expression_campaign_bytes_independently_v184(
            campaign_bytes,
            execution_preregistration_id=frozen.execution_preregistration_id,
        )
        verification_bytes = canonical_json_bytes(verification)
        _write_once(VERIFICATION_PATH, verification_bytes)
    except BaseException as error:
        if not FAILURE_PATH.exists():
            payload = {
                "schema": "acfqp.open_world_fair_expression_campaign_failure.v184",
                "execution_preregistration_id": frozen.execution_preregistration_id,
                "campaign_output_present": CAMPAIGN_PATH.is_file(),
                "verification_output_present": VERIFICATION_PATH.is_file(),
                "failure_type": type(error).__name__,
                "failure_message": str(error),
                "same_identity_rerun_forbidden": True,
                "scientific_success_claimed": False,
                "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
                "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
                "official_execution_allowed": False,
            }
            failure = {
                **payload,
                "failure_id": domains.extension_content_id_v184(
                    domains.CONSTRUCTION_K7_FAILURE_V184_DOMAIN,
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
                "campaign_byte_count": len(campaign_bytes),
                "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
                "verification_id": verification["verification_id"],
                "verification_byte_count": len(verification_bytes),
                "verification_sha256": hashlib.sha256(verification_bytes).hexdigest(),
                "target_labels_avoided": document["target_labels_avoided"],
            }
        ).decode("utf-8")
    )


if __name__ == "__main__":
    main()
