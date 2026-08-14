from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from acfqp import construction_k7_standard_2048_adaptive_accounted_campaign_v36 as campaign
from acfqp import (
    construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36
    as verifier,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v35-campaign", type=Path, required=True)
    parser.add_argument("--v35-verification", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--campaign-output", type=Path, required=True)
    parser.add_argument("--verification-output", type=Path, required=True)
    arguments = parser.parse_args()
    v35_campaign_bytes = arguments.v35_campaign.read_bytes()
    v35_verification_bytes = arguments.v35_verification.read_bytes()
    accounted = campaign.run_standard_2048_adaptive_accounted_campaign_v36(
        v35_campaign_bytes=v35_campaign_bytes,
        v35_verification_bytes=v35_verification_bytes,
        output_root=arguments.output_root,
    )
    arguments.campaign_output.write_bytes(accounted.canonical_bytes)
    print(
        "CAMPAIGN",
        accounted.campaign_id,
        len(accounted.canonical_bytes),
        hashlib.sha256(accounted.canonical_bytes).hexdigest(),
        flush=True,
    )
    verification = verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
        campaign_bytes=accounted.canonical_bytes,
        output_root=arguments.output_root,
        v35_campaign_bytes=v35_campaign_bytes,
        v35_verification_bytes=v35_verification_bytes,
    )
    arguments.verification_output.write_bytes(verification.canonical_bytes)
    print(
        "VERIFICATION",
        verification.verification_id,
        len(verification.canonical_bytes),
        hashlib.sha256(verification.canonical_bytes).hexdigest(),
        flush=True,
    )


if __name__ == "__main__":
    main()
