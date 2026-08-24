#!/usr/bin/env python3
"""Execute the source-pinned V180r4 V34 occurrence exactly once."""

from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_all_path_production_terminal_finalizer_v180r3 as finalizer
from acfqp import construction_k7_all_path_v34_execution_authorization_v180r4 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r4 as domains
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
OUTPUT_ROOT = BASE / "v180r4_v34_production_output"
SUCCESS = BASE / "v180r4_v34_production_terminal_bundle.json"
FAILURE = BASE / "v180r4_v34_production_failure.json"


def _write_failure(error: BaseException) -> None:
    payload = {
        "schema": "acfqp.v34_production_execution_failure.v180r4",
        "v34_execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "output_root_created": OUTPUT_ROOT.exists(),
        "retained_output_file_count": (
            sum(path.is_file() for path in OUTPUT_ROOT.rglob("*"))
            if OUTPUT_ROOT.exists()
            else 0
        ),
        "same_authorization_rerun_forbidden": True,
        "success_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "failure_id": domains.extension_content_id_v180r4(
            domains.CONSTRUCTION_K7_V34_EXECUTION_FAILURE_V180R4_DOMAIN,
            payload,
        ),
    }
    with FAILURE.open("xb") as stream:
        raw = canonical_json_bytes(document)
        if stream.write(raw) != len(raw):
            raise RuntimeError("V180r4 failure terminal short write")
    print("V180R4_V34_FAILURE", document["failure_id"], flush=True)


def main() -> None:
    if OUTPUT_ROOT.exists() or SUCCESS.exists() or FAILURE.exists():
        raise RuntimeError("V180r4 V34 authorization already has progress or terminal")
    frozen = authorization.freeze_v34_execution_authorization_v180r4()
    if frozen.authorization_id != authorization.EXPECTED_AUTHORIZATION_ID:
        raise RuntimeError("V180r4 V34 authorization identity changed")
    try:
        result = finalizer.run_v34_abstract_certified_production_occurrence_v180r3(
            OUTPUT_ROOT
        )
        with SUCCESS.open("xb") as stream:
            if stream.write(result.canonical_bytes) != len(result.canonical_bytes):
                raise RuntimeError("V180r4 V34 terminal bundle short write")
        print(
            "V180R4_V34_SUCCESS",
            result.production_terminal_bundle_id,
            flush=True,
        )
    except BaseException as error:
        _write_failure(error)
        raise


if __name__ == "__main__":
    main()
