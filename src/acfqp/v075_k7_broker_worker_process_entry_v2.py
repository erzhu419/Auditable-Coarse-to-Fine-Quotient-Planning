"""Fresh-exec worker entry for the K7 production broker successor."""

from __future__ import annotations

import importlib
import os

from acfqp import v075_k7_production_role_sandbox_v2 as sandbox_v2


ENTRY_MODULE = "acfqp.v075_k7_broker_worker_process_entry_v2"
ENTRY_SYMBOL = "run_v075_k7_broker_worker_process_entry_v2"
SUCCESS_EXIT = 0
INPUT_FAILURE_EXIT = 111
EXECUTION_FAILURE_EXIT = 112


def run_v075_k7_broker_worker_process_entry_v2(
    postexec_attestation: object = None,
    source_archive_fd: object = None,
) -> int:
    """Run the fixed worker core; never write diagnostics to its protocol FD."""

    inputs = None
    try:
        sandbox_v2.consume_v075_k7_production_role_postexec_entry_attestation_v2(
            postexec_attestation,
            role=sandbox_v2.K7ProductionSandboxRoleV2.WORKER,
            source_archive_fd=source_archive_fd,
        )
        manifest_v2 = importlib.import_module(
            "acfqp.v075_k7_production_role_manifest_v2"
        )
        common_v2 = importlib.import_module(
            "acfqp.v075_k7_broker_process_entry_common_v2"
        )
        worker_v1 = importlib.import_module(
            "acfqp.v075_k7_broker_worker_entry_v1"
        )
        inputs = common_v2.load_v075_k7_broker_process_inputs_v2(
            role=manifest_v2.K7ProductionBrokerRoleV2.WORKER
        )
    except BaseException:
        return INPUT_FAILURE_EXIT
    try:
        os.umask(0o077)
        if inputs.output_directory_fd is None:
            return INPUT_FAILURE_EXIT
        worker_v1.execute_v075_k7_broker_worker_core_v1(
            expected_request_replay=inputs.request_replay,
            binding=inputs.binding,
            endpoint=inputs.endpoint,
            sealed_business_result_fd=inputs.result_fd,
            output_directory_fd=inputs.output_directory_fd,
        )
        return SUCCESS_EXIT
    except BaseException:
        return EXECUTION_FAILURE_EXIT
    finally:
        inputs.close_endpoint()


__all__ = (
    "ENTRY_MODULE",
    "ENTRY_SYMBOL",
    "EXECUTION_FAILURE_EXIT",
    "INPUT_FAILURE_EXIT",
    "SUCCESS_EXIT",
    "run_v075_k7_broker_worker_process_entry_v2",
)
