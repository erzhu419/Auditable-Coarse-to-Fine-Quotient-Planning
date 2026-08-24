#!/usr/bin/env python3
"""Execute the V180r7 full-ground-fallback authorization exactly once."""

from __future__ import annotations

from pathlib import Path

from acfqp import construction_k7_all_path_fallback_execution_authorization_v180r7 as authorization
from acfqp import construction_k7_domain_registry_extension_v180r7 as domains
from acfqp import construction_k7_full_ground_fallback_production_terminal_finalizer_v180r7 as finalizer
from acfqp.phase3e_ids import canonical_json_bytes


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp" / "exact-freeze"
INPUT_ROOT = ROOT / ".tmp" / "recovery-eligible-retained-v1"
CAS_ROOT = BASE / "v180r7_full_ground_fallback_cas"
OUTPUT_ROOT = BASE / "v180r7_full_ground_fallback_output"
SUCCESS = BASE / "v180r7_full_ground_fallback_terminal_bundle.json"
FAILURE = BASE / "v180r7_full_ground_fallback_failure.json"


def _write_failure(error: BaseException) -> None:
    payload = {
        "schema": "acfqp.full_ground_fallback_execution_failure.v180r7",
        "fallback_execution_authorization_id": authorization.EXPECTED_AUTHORIZATION_ID,
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "cas_root_created": CAS_ROOT.exists(),
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
        "failure_id": domains.extension_content_id_v180r7(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_FAILURE_V180R7_DOMAIN,
            payload,
        ),
    }
    with FAILURE.open("xb") as stream:
        raw = canonical_json_bytes(document)
        if stream.write(raw) != len(raw):
            raise RuntimeError("V180r7 failure terminal short write")
    print("V180R7_FALLBACK_FAILURE", document["failure_id"], flush=True)


def main() -> None:
    if any(path.exists() for path in (CAS_ROOT, OUTPUT_ROOT, SUCCESS, FAILURE)):
        raise RuntimeError("V180r7 fallback authorization already has progress or terminal")
    frozen = authorization.freeze_fallback_execution_authorization_v180r7()
    if frozen.authorization_id != authorization.EXPECTED_AUTHORIZATION_ID:
        raise RuntimeError("V180r7 fallback authorization identity changed")
    try:
        result = finalizer.run_full_ground_fallback_production_occurrence_v180r7(
            repository_root=ROOT,
            runtime_cas_root=CAS_ROOT,
            output_directory=OUTPUT_ROOT,
            binding_bytes=(INPUT_ROOT / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
            snapshot_bytes=(INPUT_ROOT / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
            transition_bytes=(
                INPUT_ROOT / "PROOF_DEPENDENCY_TRANSITION.json"
            ).read_bytes(),
        )
        with SUCCESS.open("xb") as stream:
            if stream.write(result.canonical_bytes) != len(result.canonical_bytes):
                raise RuntimeError("V180r7 fallback terminal bundle short write")
        print(
            "V180R7_FALLBACK_SUCCESS",
            result.production_terminal_bundle_id,
            flush=True,
        )
    except BaseException as error:
        _write_failure(error)
        raise


if __name__ == "__main__":
    main()
