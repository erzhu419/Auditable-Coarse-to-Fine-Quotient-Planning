#!/usr/bin/env python3
"""Ratify the frozen fresh u005 successor against one clean source commit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    build_ratified_hybrid_confirmatory_protocol_v2,
    validate_ratified_hybrid_confirmatory_protocol_v2,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def ratify_hybrid_confirmatory_protocol_file_v2(
    *, repository: Path, output: Path
) -> dict:
    resolved_output = require_path_outside_repository_v1(
        repository=repository,
        path=output,
        label="ratified hybrid confirmatory protocol output",
    )
    source_commit = bound_clean_source_commit_v1(repository)
    protocol = build_ratified_hybrid_confirmatory_protocol_v2(source_commit)
    validate_ratified_hybrid_confirmatory_protocol_v2(protocol)
    write_exclusive_bytes_v1(resolved_output, canonical_json_bytes(protocol))
    return protocol


def main() -> int:
    args = _arguments()
    try:
        protocol = ratify_hybrid_confirmatory_protocol_file_v2(
            repository=REPOSITORY, output=args.output
        )
    except ScienceExecutionIOV1Error as error:
        raise SystemExit(str(error)) from error
    print(
        json.dumps(
            {
                "success": True,
                "protocol": str(args.output.resolve()),
                "protocol_id": protocol["protocol_id"],
                "source_commit": protocol["source_commit"],
                "campaign_kind": protocol["campaign_kind"],
                "authorization": protocol["authorization"],
                "confirmatory_execution_authorized": protocol[
                    "confirmatory_execution_authorized"
                ],
                "official_execution_allowed": protocol["claim_boundary"][
                    "official_execution_allowed"
                ],
                "official_execution_gate": protocol["claim_boundary"][
                    "OFFICIAL_EXECUTION_GATE"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
