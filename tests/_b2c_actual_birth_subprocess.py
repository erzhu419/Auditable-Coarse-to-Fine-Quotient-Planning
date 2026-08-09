from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

from acfqp import construction_k7_h1_actual_observed_supervisor_birth_v1 as b2c
from acfqp import construction_k7_h1_e5a_runtime_lease_successor_v1 as b2a
from acfqp import construction_k7_h1_guardian_runtime_genesis_v1 as b2b
from acfqp import construction_k7_h1_route_wide_working_set_cgroup_v1 as e5a


MIB = 1024 * 1024


def _ident(label: str) -> str:
    return hashlib.sha256(f"b2c-subprocess:{label}".encode()).hexdigest()


def main() -> int:
    if len(sys.argv) != 4:
        raise RuntimeError("expected stage and two journal directories")
    stage_arg, b2b_path, b2c_path = sys.argv[1:]
    stage = None if stage_arg == "NONE" else stage_arg
    parent = Path(os.environ["ACFQP_E5A_DELEGATED_PARENT_CGROUP"])
    parent_fd = os.open(
        parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    original_pread = os.pread
    primary_reads = 0
    try:
        preregistration = b2b.preregister_h1_guardian_runtime_genesis_v1()
        lease = e5a.prepare_h1_route_wide_working_set_cgroup_v1(
            delegated_parent_cgroup_fd=parent_fd,
            registered_hard_cap_bytes=96 * MIB,
            requested_outer_memory_max_bytes=64 * MIB,
            logical_occurrence_id=_ident(f"occurrence:{stage_arg}"),
            route_attempt_id=_ident(f"attempt:{stage_arg}"),
            decision_point_id=_ident(f"decision:{stage_arg}"),
            build_epoch_id=_ident(f"epoch:{stage_arg}"),
        )
        runtime = b2a.consume_h1_e5a_runtime_lease_successor_v1(lease)
        target_fd = runtime._memory_peak_fd

        def counted_pread(descriptor: int, count: int, offset: int) -> bytes:
            nonlocal primary_reads
            if descriptor == target_fd:
                primary_reads += 1
            return original_pread(descriptor, count, offset)

        os.pread = counted_pread
        b2c._TEST_ONLY_PEAK_FINISH_FAULT_STAGE = stage
        if stage is None:
            result = b2c.run_h1_actual_observed_supervisor_birth_v1(
                runtime,
                b2b_preregistration=preregistration,
                b2b_journal_directory=Path(b2b_path),
                birth_journal_directory=Path(b2c_path),
            )
            reads_before_retry = primary_reads
        else:
            try:
                b2c.run_h1_actual_observed_supervisor_birth_v1(
                    runtime,
                    b2b_preregistration=preregistration,
                    b2b_journal_directory=Path(b2b_path),
                    birth_journal_directory=Path(b2c_path),
                )
            except b2c.ConstructionK7H1ActualObservedSupervisorBirthV1Error as error:
                takeover = error.cleanup_handle
                if takeover is None:
                    raise
            else:
                raise RuntimeError("registered peak finish fault did not fire")
            reads_before_retry = primary_reads
            b2c._TEST_ONLY_PEAK_FINISH_FAULT_STAGE = None
            result = b2c.complete_h1_actual_observed_supervisor_birth_v1(takeover)
        document = b2c.verify_h1_actual_observed_supervisor_birth_result_bytes_v1(
            result.canonical_bytes
        )
        output = {
            "actual_process_birth_present": document[
                "actual_process_birth_present"
            ],
            "creator_reap_exactly_once": document["creator_reap_exactly_once"],
            "memory_peak_primary_read_count": document[
                "memory_peak_primary_read_count"
            ],
            "memory_peak_witness_read_count": document[
                "memory_peak_witness_read_count"
            ],
            "protocol_record_count": len(document["protocol_record_ids"]),
            "primary_reads_before_retry": reads_before_retry,
            "primary_reads_after_retry": primary_reads,
            "live_prebindings": len(b2c._LIVE_PREBINDINGS),
            "consumed_prebindings": len(b2c._CONSUMED_PREBINDINGS),
            "live_takeovers": len(b2c._LIVE_TAKEOVERS),
            "quarantined_takeovers": len(b2c._QUARANTINED_TAKEOVERS),
        }
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        b2c._TEST_ONLY_PEAK_FINISH_FAULT_STAGE = None
        os.pread = original_pread
        os.close(parent_fd)


if __name__ == "__main__":
    raise SystemExit(main())
