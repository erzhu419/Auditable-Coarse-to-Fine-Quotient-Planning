from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from acfqp import (
    construction_k7_standard_2048_expression_full_accounted_independent_verifier_v34
    as verifier,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-input", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--verification-output", type=Path, required=True)
    arguments = parser.parse_args()
    result = verifier.verify_standard_2048_expression_full_accounting_bytes_independently_v34(
        arguments.campaign_input.read_bytes(),
        arguments.output_root,
    )
    arguments.verification_output.write_bytes(result.canonical_bytes)
    print(
        "VERIFICATION",
        result.verification_id,
        len(result.canonical_bytes),
        hashlib.sha256(result.canonical_bytes).hexdigest(),
        flush=True,
    )


if __name__ == "__main__":
    main()
