"""Fresh-exec business entry for the K7 production broker successor."""

from __future__ import annotations

from acfqp import v075_k7_business_entry_core_v1 as business_v1
from acfqp import v075_k7_broker_process_entry_common_v2 as common_v2
from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2


ENTRY_MODULE = "acfqp.v075_k7_broker_business_process_entry_v2"
ENTRY_SYMBOL = "run_v075_k7_broker_business_process_entry_v2"
SUCCESS_EXIT = 0
INPUT_FAILURE_EXIT = 121
EXECUTION_FAILURE_EXIT = 122


def run_v075_k7_broker_business_process_entry_v2() -> int:
    """Run the fixed business core; never write diagnostics to its protocol FD."""

    inputs = None
    try:
        inputs = common_v2.load_v075_k7_broker_process_inputs_v2(
            role=manifest_v2.K7ProductionBrokerRoleV2.BUSINESS
        )
    except BaseException:
        return INPUT_FAILURE_EXIT
    try:
        if (
            inputs.sealed_secret_fd is None
            or inputs.signer_private_root is None
            or inputs.signer_private_key_path is None
        ):
            return INPUT_FAILURE_EXIT
        business_v1.execute_v075_k7_business_entry_core_v1(
            request_replay=inputs.request_replay,
            source_archive_fd=inputs.source_archive_fd,
            sealed_secret_fd=inputs.sealed_secret_fd,
            repository_root=inputs.repository_root,
            signer_private_root=inputs.signer_private_root,
            signer_private_key_path=inputs.signer_private_key_path,
            output_memfd=inputs.result_fd,
            business_result_endpoint=inputs.endpoint,
            binding=inputs.binding,
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
    "run_v075_k7_broker_business_process_entry_v2",
)
