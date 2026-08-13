from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as campaign


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--campaign-output", type=Path, required=True)
    arguments = parser.parse_args()
    result = campaign.run_standard_2048_expression_full_accounted_campaign_v34(
        arguments.output_root
    )
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
        "SUMMARY",
        document["segment_count"],
        document["complete_decision_count"],
        document["won_occurrence_count"],
        document["lost_occurrence_count"],
        document["operational_work_vector_count"],
        document["evaluation_work_vector_count"],
        flush=True,
    )
    print(
        "SEGMENTS",
        [
            (
                row["profile"],
                row["decision_count"],
                row["active_worker_count"],
                row["terminal_carry_forward_count"],
                row["cold_evaluation_checkpoint_count"],
            )
            for row in document["segments"]
        ],
        flush=True,
    )
    print("COMPARISON", document["final_operational_comparison_totals"], flush=True)
    print(
        "OUTPUT",
        sum(
            path.stat().st_size
            for path in arguments.output_root.rglob("*")
            if path.is_file()
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
