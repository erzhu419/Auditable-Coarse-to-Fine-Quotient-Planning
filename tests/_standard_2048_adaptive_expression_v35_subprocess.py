from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from acfqp import construction_k7_standard_2048_adaptive_expression_campaign_v35 as campaign
from acfqp import construction_k7_standard_2048_adaptive_expression_independent_verifier_v35 as verifier
from acfqp import construction_k7_standard_2048_adaptive_expression_preregistration_v35 as preregistration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-output", type=Path, required=True)
    parser.add_argument("--verification-output", type=Path, required=True)
    arguments = parser.parse_args()
    result = campaign.run_standard_2048_adaptive_expression_campaign_v35()
    arguments.campaign_output.write_bytes(result.canonical_bytes)
    document = result.to_document()
    print(
        "CAMPAIGN",
        result.campaign_id,
        len(result.canonical_bytes),
        hashlib.sha256(result.canonical_bytes).hexdigest(),
        flush=True,
    )
    print(
        "SAMPLE_TAX",
        document["ground_distinction_query_count"],
        document["first_frontier_no_prior_label_count"],
        document["adaptive_label_fraction_of_no_prior"],
        flush=True,
    )
    print(
        "EPISODES",
        [
            (
                row["episode_index"],
                row["decision_count"],
                row["closure_reason"],
                row["maximum_final_board_tile_rank"],
            )
            for row in document["episodes"]
        ],
        flush=True,
    )
    print(
        "CHECKPOINTS",
        document["cold_evaluation_checkpoint_count"],
        document["all_checkpoint_root_values_and_actions_exactly_equal"],
        flush=True,
    )
    verification = verifier.verify_standard_2048_adaptive_expression_campaign_bytes_independently_v35(
        result.canonical_bytes,
        preregistration.freeze_standard_2048_adaptive_expression_preregistration_v35().canonical_bytes,
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
