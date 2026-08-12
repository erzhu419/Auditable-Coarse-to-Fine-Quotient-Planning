from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from acfqp.phase3e_ids import canonical_json_bytes


def _occurrence_id(family: str) -> str:
    return hashlib.sha256(
        f"heldout-cross-structural-{family.lower()}-occurrence-v1".encode("utf-8")
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=("W5", "K6"))
    parser.add_argument("output")
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(mode=0o700)
    campaign_directory = root / "child-campaign"
    if args.family == "W5":
        from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
        from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
        from acfqp import construction_k7_heldout_abstract_campaign_v1 as campaign_v1

        source = source_v1.run_heldout_checkpoint_recertification_v1()
        reuse = reuse_v1.run_heldout_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id=_occurrence_id(args.family),
            occurrence_ordinal=51,
        )
        campaign = campaign_v1.run_heldout_abstract_campaign_v1(
            reuse,
            campaign_directory=campaign_directory,
        )
    else:
        from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as source_v1
        from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as reuse_v1
        from acfqp import construction_k7_heldout_k6_abstract_campaign_v1 as campaign_v1

        source = source_v1.run_heldout_k6_checkpoint_recertification_v1()
        reuse = reuse_v1.run_heldout_k6_overlay_abstract_reuse_v1(
            source,
            logical_occurrence_id=_occurrence_id(args.family),
            occurrence_ordinal=61,
        )
        campaign = campaign_v1.run_heldout_k6_abstract_campaign_v1(
            reuse,
            campaign_directory=campaign_directory,
        )
    (root / "reuse-result.json").write_bytes(
        canonical_json_bytes(reuse.to_document())
    )
    (root / "manifest.json").write_bytes(
        canonical_json_bytes(
            {
                "family": args.family,
                "campaign_preregistration_id": (
                    campaign.preregistration.preregistration_id
                ),
                "campaign_closure_id": campaign.closure.closure_id,
                "campaign_directory": "child-campaign",
            }
        )
    )


if __name__ == "__main__":
    main()
