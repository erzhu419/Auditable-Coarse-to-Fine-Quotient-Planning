from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from acfqp import construction_k7_cached_exact_infeasibility_production_terminal_finalizer_v180r8 as finalizer
from acfqp import phase3e_exact_infeasibility_durable_proof_v1 as durable


def main() -> None:
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=False)
    proof_path = root / "DURABLE_EXACT_PROOF.json"
    proof_path.write_bytes(
        durable.issue_phase3e_exact_infeasibility_durable_proof_v1(
            Path(__file__).resolve().parents[1] / "artifacts" / "phase05" / "g2048"
        )
    )
    result = finalizer.run_cached_exact_infeasibility_production_occurrence_v180r8(
        proof_path
    )
    terminal_path = root / "TERMINAL.json"
    terminal_path.write_bytes(result.canonical_bytes)
    print(
        json.dumps(
            {
                "terminal_path": str(terminal_path),
                "terminal_id": result.production_terminal_bundle_id,
                "byte_count": len(result.canonical_bytes),
                "sha256": hashlib.sha256(result.canonical_bytes).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
