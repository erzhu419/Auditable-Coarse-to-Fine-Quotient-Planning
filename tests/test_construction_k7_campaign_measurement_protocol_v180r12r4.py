from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path
import pickle

import pytest

from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger
from acfqp import construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer
from acfqp import construction_k7_campaign_measurement_protocol_v180r12r4 as protocol
from acfqp import construction_k7_campaign_measurement_supervisor_v180r12r4 as supervisor
from acfqp import construction_k7_campaign_measurement_worker_v180r12r4 as worker
from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import bootstrap_v180r12r4_campaign_measurement as bootstrap_script
from scripts import launch_v180r12r4_campaign_measurement_prelaunch as launch_script
from scripts import run_v180r12r4_campaign_measurement as run_script
from scripts import supervise_v180r12r4_campaign_measurement as supervise_script
from scripts import materialize_v180r12r4_campaign_measurement_prelaunch as materialize_script
from scripts import verify_v180r12r4_campaign_measurement as verify_script


def cgroup_parent_fact() -> dict:
    return {
        "schema": "acfqp.v180r12r4_cgroup_parent_fact.v1",
        "mount_point": "/sys/fs/cgroup",
        "mount_fstype": "cgroup2",
        "mount_device": 30,
        "mount_inode": 1,
        "mount_options": [
            "memory_recursiveprot",
            "nodev",
            "noexec",
            "nosuid",
            "nsdelegate",
            "relatime",
            "rw",
        ],
        "parent_path": (
            "/sys/fs/cgroup/user.slice/user-1000.slice/"
            "user@1000.service/app.slice"
        ),
        "parent_device": 30,
        "parent_inode": 6_987,
        "owner_uid": 1_000,
        "owner_gid": 1_000,
        "mode": 0o755,
        "controllers": ["cpu", "memory", "pids"],
        "subtree_control": ["cpu", "memory", "pids"],
        "cgroup_type": "domain",
        "cgroup_namespace_inode": 4_026_531_835,
        "cgroup_events_present": True,
        "memory_events_present": True,
        "pids_events_present": True,
        "cgroup_kill_present": True,
        "cgroup_procs_present": True,
        "memory_peak_present": True,
        "pids_peak_present": True,
        "self_membership": (
            "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
            "acfqp-v180r12r4r5-freeze-capture-20260829.service"
        ),
    }


def runtime_capability_fact() -> dict:
    return {
        "schema": "acfqp.v180r12r4_runtime_capability_fact.v1",
        "machine_architecture": "x86_64",
        "single_threaded": True,
        "clone3_probe_errno": 22,
        "clone3_syscall_recognized": True,
        "pidfd_send_signal_probe_errno": 9,
        "pidfd_send_signal_recognized": True,
        "execveat_probe_errno": 9,
        "execveat_recognized": True,
        "pidfd_wait_present": True,
        "landlock_abi": 7,
        "uid": 1_000,
        "gid": 1_000,
        "effective_capability_mask": 0,
        "admitted": True,
    }


def test_production_service_tokens_bind_immediate_ordinal13_failure_terminals() -> None:
    contract = protocol.production_systemd_service_contract_v180r12r4()
    assert contract["token_input_fields"] == [
        "failed_predecessor_freeze_id",
        "failed_inner_launch_failure_id",
        "failed_outer_service_failure_id",
        "repair_scope",
        "purpose",
    ]
    expected_tokens = {
        "measurement": (
            "1ba5304a7d653a3805fdca4754eeb7ff2feaa63794c6b866f47adda85160668d"
        ),
        "verification": (
            "14e3fead4dab312dd06026196922d455600e970d5de64624e3d47b66525c0221"
        ),
    }
    for row in contract["target_rows"]:
        token_input = row["token_input"]
        assert token_input["failed_predecessor_freeze_id"] == (
            protocol.V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID
        )
        assert token_input["failed_inner_launch_failure_id"] == (
            protocol.V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID
        )
        assert token_input["failed_outer_service_failure_id"] == (
            protocol.V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID
        )
        assert token_input["repair_scope"] == protocol.V180R12R4_REPAIR_SCOPE
        assert row["token"] == expected_tokens[row["target"]]


def test_ordinal14_c_pre_freezes_protocol_and_slot_self_literals() -> None:
    assert protocol.EXPECTED_PROTOCOL_ID == (
        "9fc6ecbe63cdb65752d5bac6690903ab34ffc540abb3062b5ffde7a3695ebd49"
    )
    assert protocol.EXPECTED_CANONICAL_BYTE_COUNT == 492_573
    assert protocol.EXPECTED_CANONICAL_SHA256 == (
        "e32acda505c2e7dc98593290fe5fb60561e22df8481581a1f4e25846348f7cba"
    )
    assert protocol.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID == (
        "441e52cd3721793a0541288196776aa214dd44b91f01e1822114b0e4442559f5"
    )
    assert protocol.EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID == (
        "5ec6496223fdd24664d142d581847f3e95456a3b0bb171df2950302e413ac60b"
    )
    assert protocol.EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID == (
        "ee833b2260347a85442802459cd3ae6edd62b3abd35ba8d15b1829f7e9fa04f8"
    )
    assert protocol.EXPECTED_PRELAUNCH_LAUNCH_RULE_ID == (
        "9bedb474878ba9f3c7eb9735278b03fd91299c978f959ae30433a22b41b23817"
    )
    assert protocol.LOGICAL_OCCURRENCE_ID == (
        "a37770e56698857e162b2099766573ec5cabfc876145496f7d54756271d66599"
    )
    assert protocol.EXECUTION_NONCE == (
        "7d4ebffb564caeb42550670bf06276f9ef7f456cfa5231acef56497f2bd62ea4"
    )


def test_pre_attempt_host_conformance_v2_binds_socket_capability_minima() -> None:
    assert protocol.PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA == (
        "acfqp.v180r12r4_pre_attempt_host_conformance.v2"
    )
    contract = protocol.socket_buffer_capability_contract_v180r12r4()
    assert contract["fact_schema"] == (
        "acfqp.v180r12r4_socket_buffer_capability_fact.v1"
    )
    assert tuple(contract["fact_fields"]) == (
        *contract["exact_fields"],
        *contract["at_least_fields"],
    )
    assert tuple(contract["exact_fields"]) == (
        "schema",
        "probe_boundary",
        "socket_family",
        "socket_type",
        "endpoint_count",
        "buffer_request_bytes",
        "effective_min_bytes",
    )
    assert contract["expected_exact_properties"] == {
        "schema": protocol.SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA,
        "probe_boundary": "PRE_CAMPAIGN_ATTEMPT_O_EXCL",
        "socket_family": "AF_UNIX",
        "socket_type": "SOCK_SEQPACKET|SOCK_CLOEXEC",
        "endpoint_count": 2,
        "buffer_request_bytes": 1_048_576,
        "effective_min_bytes": 2_097_152,
    }
    assert contract["expected_minimum_properties"] == {
        "net_core_wmem_max_bytes": 1_048_576,
        "net_core_rmem_max_bytes": 1_048_576,
        "endpoint_0_so_sndbuf_bytes": 2_097_152,
        "endpoint_0_so_rcvbuf_bytes": 2_097_152,
        "endpoint_1_so_sndbuf_bytes": 2_097_152,
        "endpoint_1_so_rcvbuf_bytes": 2_097_152,
    }
    assert contract["mismatch_row_fields"] == [
        "scope",
        "field",
        "minimum",
        "observed",
    ]
    assert contract["mismatch_scope"] == "socket_buffer_capability"
    assert contract["insufficient_cause"] == (
        "SOCKET_BUFFER_CAPABILITY_INSUFFICIENT"
    )
    prelaunch = protocol.prelaunch_contract_v180r12r4()
    assert prelaunch[
        "pre_attempt_host_conformance_socket_buffer_capability_contract"
    ] == contract
    assert prelaunch["pre_attempt_host_conformance_socket_low_value_mismatch_row"] == [
        "socket_buffer_capability",
        "{field}",
        "{minimum}",
        "{observed}",
    ]
    assert prelaunch["pre_attempt_host_conformance_unit_ownership_is_separate"]


def test_topology_conformance_r4_declares_complete_t3_diagnostic() -> None:
    contract = protocol.topology_conformance_diagnostic_r4_contract_v180r12r4()
    assert contract["schema"] == (
        "acfqp.campaign_cgroup_topology_conformance_diagnostic.v180r12r4r4"
    )
    assert tuple(contract["fields"]) == (
        "schema",
        "scope",
        "unit_ownership_acquired",
        "full_conformance",
        "property_snapshots",
        "expected_properties",
        "observed_properties",
        "mismatch_rows",
        "cause",
    )
    assert tuple(contract["scopes"]) == (
        "PARENT_AND_CHILD_TOPOLOGY",
        "T1_T2_PLACEMENT",
        "T3_CHECKPOINT_CONFORMANCE",
    )
    assert tuple(contract["property_snapshot_fields"]) == (
        "unit_ownership",
        "parent_delegation",
        "measurement_topology",
        "production_runtime_placement_t3",
    )
    assert tuple(contract["production_runtime_placement_t3_fields"]) == (
        protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
    )
    assert tuple(contract["production_runtime_placement_t3_checkpoint_fields"]) == (
        protocol.PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
    )
    assert contract["pre_t3_scope_retains_explicit_null_t3_snapshot"]
    assert contract["t3_scope_retains_complete_outer_t3_snapshot"]
    assert contract["t3_expected_boundary"] == "T3_IMMEDIATELY_BEFORE_CLONE3"
    assert contract["t3_all_checkpoint_fields_compared_by_canonical_json"]
    assert contract["unit_ownership_acquired_is_separate_from_full_conformance"]


def test_source_bound_service_context_capture_is_exact_and_cpu_enabled() -> None:
    root = Path(protocol.__file__).resolve().parents[2]
    raw = (root / protocol.SERVICE_CONTEXT_CAPTURE_RELATIVE_PATH).read_bytes()
    contract = protocol.service_context_capture_contract_v180r12r4()
    expected_raw = canonical_json_bytes(
        {
            "capture_purpose": protocol.SERVICE_CONTEXT_CAPTURE_PURPOSE,
            "cgroup_parent_fact": (
                protocol.SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT
            ),
            "runtime_capability_fact": (
                protocol.SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT
            ),
            "schema": protocol.SERVICE_CONTEXT_CAPTURE_SCHEMA,
        }
    ) + b"\n"
    assert raw == expected_raw
    assert len(raw) == contract["canonical_byte_count"] == 1_459
    expected_sha256 = (
        "53508b200ae3b0279bda887cec804a8dd06f7d800734fe3d760f1712ea866fd3"
    )
    assert hashlib.sha256(raw).hexdigest() == expected_sha256
    assert contract["canonical_sha256"] == expected_sha256
    parent = contract["cgroup_parent_fact"]
    assert parent["controllers"] == ["cpu", "memory", "pids"]
    assert parent["subtree_control"] == ["cpu", "memory", "pids"]
    assert parent["self_membership"].endswith(
        "/acfqp-v180r12r4r5-freeze-capture-20260829.service"
    )


def frozen():
    return protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
    )


def test_protocol_binds_exact_v180r12r2_success_evidence_without_rerun() -> None:
    document = frozen().to_document()
    predecessor = document["predecessor_evidence"]
    assert predecessor["aggregation_protocol_id"] == (
        "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
    )
    assert predecessor["execution_authorization_id"] == (
        "4a1424a1d27e97139acd10a50cac79ab012b8459be79b884d9adc3fd4b39e3a9"
    )
    assert predecessor["authorization_evidence_id"] == (
        "19836faa57f88a429f321720108724e2deebe0b9b7aa8c3742dc0f97930c5319"
    )
    assert predecessor["production_aggregation_bundle_id"] == (
        "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
    )
    assert predecessor["verification_id"] == (
        "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
    )
    assert predecessor["retained_file_fact_count"] == 10
    assert predecessor["verification_and_replay_exact_bytes_equal"] is True
    assert predecessor["producer_free_static_evidence_replay_only"] is True
    assert predecessor["v180r12r2_producer_rerun_forbidden"] is True
    assert predecessor["v180r12r2_verifier_rerun_forbidden"] is True
    assert predecessor["all_five_source_independent_verifiers_replayed"] is True
    assert predecessor[
        "all_ten_occurrence_shared_resource_receipt_sets_present"
    ] is True
    assert predecessor["all_twelve_route_component_chains_present"] is True
    assert predecessor["producer_bundle_independently_replayed"] is False
    assert predecessor["V180R12R2_COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert predecessor["source_receipt_count"] == 5
    assert predecessor["route_component_chain_receipt_count"] == 12
    assert predecessor["terminal_receipt_count"] == 10
    assert predecessor["terminal_shared_resource_receipt_count"] == 90
    assert predecessor["terminal_shared_resource_receipt_set_count"] == 10
    assert predecessor["v180r7r1_construction_axis_receipt_count"] == 1
    source = predecessor["evidence_freeze_source_fact"]
    assert source == {
        "relative_path": protocol.V180R12R2_EVIDENCE_SOURCE_RELATIVE_PATH,
        "byte_count": 38_850,
        "sha256": "cbaea06c412ed4aea0859b2b839759b9eba035a5724a9e7d4ed54de08938f9da",
        "git_commit_id": "1e6203e87fd7c7b2bde0c69264854c2bce6e374a",
        "git_tree_id": "d00a2e53681308d861fb1532859ce678d3547c99",
    }


def test_protocol_binds_exact_failed_dispatch_repair_lineage_without_scientific_attempt() -> None:
    document = frozen().to_document()
    lineage = document["failed_dispatch_repair_lineage"]
    assert lineage == (
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()
    )
    assert lineage["campaign_attempt_id"] == (
        "457a889a690549ad5efaeb6d3f4799ec2a859068d93eac71730088f90889f967"
    )
    assert lineage["launch_attempt_id"] == (
        "26ab9ac75aa950418708dcdacf674673f22609e87df055b0b1d8d3d96e9f1ee9"
    )
    assert lineage["launch_failure_id"] == (
        "d120a3e442d3079040e2d635e1e1808990070eece5be44ae84e73d83a52398e8"
    )
    assert lineage["materialization_terminal_id"] == (
        "344511707dfc5e623e95e868d282d03182c359e6160fe04542adc2eebff55b7a"
    )
    assert lineage["launch_rule_id"] == (
        "1700936d9145bfa7bcd858128548fd57f003ccf86a63dfdd43d6487f3aae4572"
    )
    assert lineage["failure_freeze_source_fact"] == {
        "relative_path": (
            "src/acfqp/construction_k7_campaign_measurement_"
            "prelaunch_failure_freeze_v180r12r3.py"
        ),
        "byte_count": 18_677,
        "sha256": (
            "93b52ecb67eb71c0965d37a8cf4194b5d21128798f6e5fc68a30947d8d74ded4"
        ),
        "git_commit_id": "ab06af5d4160cdf107a770d208876c06898b85b8",
        "git_tree_id": "a16cbb5dda71b5cd99a4060365478103b6ec20b8",
        "git_blob_id": "2258fef806253f0c451ad60afd087c60f4269752",
    }
    assert lineage["retained_file_fact_count"] == 7
    assert lineage["required_absent_successor_path_count"] == 12
    assert lineage["prelaunch_exact_entry_count"] == 5
    assert lineage["all_required_successor_paths_absent_at_failure_freeze"]
    assert lineage["scientific_attempt_record_present"] is False
    assert lineage["scientific_occurrence_started"] is False
    assert lineage["campaign_actual_measurement"] is False
    assert lineage["measurement_cgroup_created"] is False
    assert lineage["measurement_cgroup_absent_at_failure_freeze"] is True
    assert lineage["same_campaign_attempt_rerun_forbidden"] is True
    assert lineage["same_launch_attempt_rerun_forbidden"] is True
    assert lineage["fresh_successor_identity_required"] is True
    assert document["failed_v180r12r3_identity_rerun_forbidden"] is True
    assert document["failed_v180r12r3r1_identity_rerun_forbidden"] is True
    assert document["failed_v180r12r3r2_identity_rerun_forbidden"] is True
    assert document["fresh_v180r12r4_physical_paths_and_identities_required"]
    assert document["repair_scope"] == protocol.V180R12R4_REPAIR_SCOPE
    assert document[
        "repair_changes_campaign_path_roles_event_schedule_evidence_cardinality_or_reducers"
    ] is False
    assert "repair_changes_campaign_paths_events_evidence_or_reducers" not in document


def test_protocol_preserves_r3r1_external_replay_failure_lineage() -> None:
    document = frozen().to_document()
    lineage = document["failed_external_replay_repair_lineage"]
    assert lineage == (
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()
    )
    assert lineage["campaign_attempt_id"] == (
        "cbffcb66d23630ef46fa014f9467d3ac3054b39dde32ec0b9de22bba41078040"
    )
    assert lineage["launch_attempt_id"] == (
        "eac1fc0f3ca572a736deaf9292101a1835a04ba5176c23e6b2bcceadc26b53c9"
    )
    assert lineage["launch_failure_id"] == (
        "c2b957cf8556560696da92b959706bb7a74b2915df3776c6c28c65a266c1be60"
    )
    assert lineage["materialization_terminal_id"] == (
        "8fe982f053c1a2577310f4452881ba4bdb9f9f95758c50c520a3a0a37c17ec11"
    )
    assert lineage["launch_rule_id"] == (
        "7d337317b583520daeb335ff57e2b7814390472fa639d44a0974e0b3dab2c214"
    )
    assert lineage["failure_freeze_source_fact"] == {
        "relative_path": (
            "src/acfqp/construction_k7_campaign_measurement_"
            "prelaunch_failure_freeze_v180r12r3r1.py"
        ),
        "byte_count": 19_731,
        "sha256": (
            "3e7d34319755523d233fbe275df5d49a1aae172da1b5126f7d77b42ef0bc4adf"
        ),
        "git_commit_id": "4f8d92c208949758fcb98242f1e485d84520d4d1",
        "git_tree_id": "c8f4618edb8ff105d6fda1c7a23f54882046bb67",
        "git_blob_id": "bef5ffc073c2e57c72d6bd7256a811800d49b1e5",
    }
    assert lineage["retained_file_fact_count"] == 7
    assert lineage["required_absent_successor_path_count"] == 12
    assert lineage["prelaunch_exact_entry_count"] == 5
    assert lineage["scientific_attempt_record_present"] is False
    assert lineage["scientific_occurrence_started"] is False
    assert lineage["campaign_actual_measurement"] is False
    assert lineage["measurement_cgroup_created"] is False
    assert lineage["measurement_cgroup_absent_at_failure_freeze"] is True
    assert lineage["same_campaign_attempt_rerun_forbidden"] is True
    assert lineage["same_launch_attempt_rerun_forbidden"] is True
    assert lineage["primary_failure_type"] == "V180R12R3R1RuntimeError"
    assert lineage["primary_failure_boundary"] == (
        "EXTERNAL_REPLAY_DOCUMENT_BYTE_JOIN_CHANGED"
    )
    assert lineage["repair_scope"] == (
        "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
    )
    slot = document["campaign_measurement_execution_slot"]
    assert slot["pre_scientific_failed_predecessor_campaign_attempt_id"] == (
        lineage["campaign_attempt_id"]
    )
    assert slot["pre_scientific_failed_predecessor_launch_attempt_id"] == (
        lineage["launch_attempt_id"]
    )
    assert slot["pre_scientific_failed_predecessor_launch_failure_id"] == (
        lineage["launch_failure_id"]
    )


def test_protocol_preserves_r3r2_scientific_birth_failure_lineage() -> None:
    document = frozen().to_document()
    lineage = document["failed_scientific_birth_repair_lineage"]
    assert lineage == (
        protocol.failed_scientific_birth_repair_lineage_contract_v180r12r4()
    )
    assert lineage["failure_freeze_source_fact"] == {
        "relative_path": (
            "src/acfqp/construction_k7_campaign_measurement_"
            "failure_freeze_v180r12r3r2.py"
        ),
        "byte_count": 47_108,
        "sha256": (
            "48704c3c2217b47e59a023843d3cc3671d8d810c18729c63faa1b48c3f99ce3b"
        ),
        "git_commit_id": "f4bb4981f15a602d156e7ec88338a880c7a5a167",
        "git_tree_id": "521d6b3d39ec944a361ce801de8bde8beca29f1c",
        "git_blob_id": "87bc7bfa34772cfcb8b75ab6d627861473bbf904",
    }
    assert lineage["campaign_attempt_id"] == (
        "3de63370a50ba83d42ab45d5dc4a22fac9799bc2ab6bd1816d667e009b85292e"
    )
    assert lineage["scientific_attempt_record_present"] is True
    assert lineage["scientific_occurrence_started"] is True
    assert lineage["durable_event_kinds"] == [
        "ATTEMPT_OPEN",
        "PROCESS_BIRTH_INTENT",
    ]
    assert lineage["retained_event_count"] == 2
    assert lineage["success_event_count"] == 625
    assert lineage["campaign_counter_records_issued"] is False
    assert lineage["successful_ledger_claimed"] is False
    assert lineage["producer_free_verification_attempted"] is False
    assert lineage["exact_failing_syscall_proven"] is False
    assert lineage["primary_failure_boundary"] == (
        "PERMISSION_DENIED_DURING_SUPERVISOR_BIRTH_OR_CLONE_PATH;"
        "EXACT_FAILING_SYSCALL_UNPROVEN"
    )
    assert lineage["repair_scope"] == protocol.V180R12R3R2_REPAIR_SCOPE
    slot = document["campaign_measurement_execution_slot"]
    assert slot["historical_failed_scientific_birth_campaign_attempt_id"] == (
        lineage["campaign_attempt_id"]
    )
    assert slot["historical_failed_scientific_birth_launch_attempt_id"] == (
        lineage["launch_attempt_id"]
    )
    assert slot["historical_failed_scientific_birth_launch_failure_id"] == (
        lineage["launch_failure_id"]
    )


def test_protocol_preserves_ordinal8_as_historical_failure_lineage() -> None:
    document = frozen().to_document()
    lineage = document["failed_ordinal8_repair_lineage"]
    assert lineage == protocol.failed_ordinal8_repair_lineage_contract_v180r12r4()
    assert lineage["campaign_attempt_id"] == (
        "7dd2a5bdf2704655b41652b28a63c9309c557cc0470395870e77db7869b0a3f6"
    )
    assert lineage["campaign_failure_id"] == (
        "7f98d4f33e7e6d3c36636ffad27dbc56f54da32cd006f6d5e94cb217cd569a02"
    )
    assert lineage["inner_launch_failure_id"] == (
        "8be9a12c613373cdfde80d3fd9d64d18a8ca9aaca841ee0d2a454326748c5f43"
    )
    assert lineage["outer_service_failure_id"] == (
        "62ed6bf62f94b8c1c9d53ff8bb902ee26045c5896263f59bf28dd8ac1114c458"
    )
    assert lineage["outer_service_unit_ownership_acquired"] is True
    assert lineage["full_cgroup_conformance"] is False
    assert lineage["parent_contract_mismatch_fields"] == [
        "controllers",
        "subtree_control",
    ]
    assert lineage["full_property_diagnostic_recorded"] is False
    assert lineage["repair_scope"] == protocol.V180R12R4R3_REPAIR_SCOPE
    slot = document["campaign_measurement_execution_slot"]
    assert slot["historical_failed_ordinal8_campaign_attempt_id"] == (
        lineage["campaign_attempt_id"]
    )
    assert slot["historical_failed_ordinal8_campaign_failure_id"] == (
        lineage["campaign_failure_id"]
    )
    assert slot["historical_failed_ordinal8_inner_launch_failure_id"] == (
        lineage["inner_launch_failure_id"]
    )
    assert slot["historical_failed_ordinal8_outer_service_failure_id"] == (
        lineage["outer_service_failure_id"]
    )
    assert document["failed_v180r12r4r2_ordinal8_identity_rerun_forbidden"]


def test_protocol_binds_ordinal13_as_immediate_and_ordinal12_as_historical_lineage() -> None:
    document = frozen().to_document()
    historical = document["failed_ordinal12_repair_lineage"]
    lineage = document["failed_ordinal13_repair_lineage"]
    assert historical == protocol.failed_ordinal12_repair_lineage_contract_v180r12r4()
    assert lineage == protocol.failed_ordinal13_repair_lineage_contract_v180r12r4()
    assert historical["freeze_id"] == (
        protocol.V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID
    )
    assert historical["campaign_attempt_id"] == (
        protocol.V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
    )
    assert lineage["freeze_id"] == (
        protocol.V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID
    )
    assert lineage["campaign_attempt_id"] == (
        protocol.V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
    )
    assert lineage["campaign_failure_id"] == (
        protocol.V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID
    )
    assert lineage["scientific_attempt_opened"] is True
    assert lineage["event_kinds"] == [
        "ATTEMPT_OPEN",
        "PROCESS_BIRTH_INTENT",
        "PROCESS_BIRTH_OUTCOME",
    ]
    assert lineage["completed_event_count"] == 3
    assert lineage["successful_process_birth_outcome_recorded"] is True
    assert lineage["full_source_conformance"] is True
    assert lineage["full_host_conformance"] is True
    assert lineage["host_conformance_mismatch_count"] == 0
    assert lineage["host_conformance_cause"] is None
    assert lineage["production_runtime_placement_t1_complete"] is True
    assert lineage["production_unit_ownership_t1_acquired"] is True
    assert lineage["full_cgroup_topology_conformance_recorded"] is False
    assert lineage["formal_cgroup_topology_conformance_diagnostic"] is None
    assert lineage["formal_failure_classification"] == {
        "failure_code": "INPUT_DRIFT",
        "message": "ConnectionResetError: (104, 'Connection reset by peer')",
    }
    assert lineage["formal_failure_is_secondary"] is True
    assert lineage["diagnosed_exact_cause"] == {
        "error_type": "RuntimeError",
        "message": "V180r12r4 precompiled source binding changed",
    }
    assert lineage["diagnosed_exact_cause_is_primary"] is True
    assert lineage["source_binding_full_conformance"] is False
    assert lineage["source_binding_mismatch_count"] == 21
    assert len(lineage["source_binding_mismatch_rows"]) == 21
    assert lineage["first_source_binding_mismatch_index"] == 85
    assert lineage["first_source_binding_mismatch_module"] == "packaging"
    assert lineage["source_binding_cause"]["failure_code"] == (
        "PRECOMPILED_SOURCE_BINDING_CONFORMANCE_FAILURE"
    )
    assert lineage["cleanup_complete"] is True
    assert lineage["counter_record_count"] == 0
    assert lineage["work_vector_count"] == 0
    assert lineage["comparison_vector_count"] == 0
    assert set(lineage["gate_statuses"].values()) == {"NOT_RUN"}
    assert lineage["official_execution_allowed"] is False
    assert lineage["same_identity_rerun_forbidden"] is True
    assert lineage["repair_scope"] == protocol.V180R12R4R8_REPAIR_SCOPE
    slot = document["campaign_measurement_execution_slot"]
    assert slot["historical_failed_ordinal12_freeze_id"] == historical["freeze_id"]
    assert slot["historical_failed_ordinal12_logical_campaign_attempt_id"] == (
        historical["campaign_attempt_id"]
    )
    assert slot["historical_failed_ordinal12_campaign_failure_id"] == (
        historical["campaign_failure_id"]
    )
    assert slot["immediate_failed_predecessor_freeze_id"] == lineage["freeze_id"]
    assert slot["immediate_failed_predecessor_logical_campaign_attempt_id"] == (
        lineage["campaign_attempt_id"]
    )
    assert slot["immediate_failed_predecessor_campaign_failure_id"] == (
        lineage["campaign_failure_id"]
    )
    assert slot["immediate_failed_predecessor_inner_launch_failure_id"] == (
        lineage["inner_launch_failure_id"]
    )
    assert slot["immediate_failed_predecessor_outer_service_failure_id"] == (
        lineage["outer_service_failure_id"]
    )
    assert document["failed_v180r12r4r4_ordinal9_identity_rerun_forbidden"]
    assert document["failed_v180r12r4r5_ordinal10_identity_rerun_forbidden"]
    assert document["failed_v180r12r4r6_ordinal11_identity_rerun_forbidden"]
    assert document["failed_v180r12r4r7_ordinal12_identity_rerun_forbidden"]
    assert document["failed_v180r12r4r8_ordinal13_identity_rerun_forbidden"]


def test_r3r2_scientific_birth_lineage_rejects_public_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_scientific_birth_predecessor,
        "EXPECTED_EVENT_IDS",
        ("0" * 64, "1" * 64),
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="scientific failure authority changed",
    ):
        protocol.failed_scientific_birth_repair_lineage_contract_v180r12r4()


def test_ordinal8_lineage_rejects_public_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_ordinal8_predecessor,
        "EXPECTED_OUTER_SERVICE_FAILURE_ID",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="ordinal8 failure authority changed",
    ):
        protocol.failed_ordinal8_repair_lineage_contract_v180r12r4()


def test_ordinal11_lineage_rejects_public_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_ordinal11_predecessor,
        "EXPECTED_OUTER_SERVICE_FAILURE_ID",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="ordinal11 failure authority changed",
    ):
        protocol.failed_ordinal11_repair_lineage_contract_v180r12r4()


def test_ordinal12_lineage_rejects_public_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_ordinal12_predecessor,
        "EXPECTED_OUTER_SERVICE_FAILURE_ID",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="ordinal12 failure authority changed",
    ):
        protocol.failed_ordinal12_repair_lineage_contract_v180r12r4()


def test_ordinal13_lineage_rejects_public_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_ordinal13_predecessor,
        "EXPECTED_OUTER_SERVICE_FAILURE_ID",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="ordinal13 failure authority changed",
    ):
        protocol.failed_ordinal13_repair_lineage_contract_v180r12r4()


def test_failed_dispatch_replay_is_source_bound_pre_scientific_authority_not_measurement() -> None:
    lineage = protocol.failed_dispatch_repair_lineage_contract_v180r12r4()
    assert lineage["failure_freeze_source_relative_path"] == (
        protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    )
    assert lineage["failure_freeze_source_is_required_authorization_source_root"]
    assert lineage["failure_freeze_source_is_resolved_from_source_bound_module_file"]
    assert lineage[
        "failure_freeze_artifact_base_is_repository_root_tmp_exact_freeze"
    ]
    assert lineage["runtime_replay_is_pre_scientific_prereg_authority"]
    assert lineage[
        "runtime_replay_precedes_successor_campaign_attempt_publication"
    ]
    assert lineage[
        "retained_artifact_absence_and_cgroup_reads_are_campaign_actual_measurement"
    ] is False
    assert lineage[
        "retained_artifact_absence_and_cgroup_reads_are_in_five_measured_input_read_chains"
    ] is False
    assert lineage[
        "retained_artifact_absence_and_cgroup_reads_are_in_nine_campaign_paths"
    ] is False
    assert lineage[
        "retained_artifact_absence_and_cgroup_reads_are_trusted_prereg_authority_replay"
    ] is True
    roots = protocol.SOURCE_CLOSURE_REQUIRED_ROOTS
    assert len(roots) == len(set(roots)) == 28
    assert tuple(roots) == tuple(sorted(roots))
    assert roots.count(protocol.V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1
    assert roots.count(protocol.V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH) == 1


def test_failed_dispatch_lineage_rejects_absence_inventory_drift_before_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_dispatch_predecessor,
        "_REQUIRED_ABSENT_PATHS",
        protocol.V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS[:-1],
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="source authority changed",
    ):
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()


def test_failed_dispatch_lineage_rejects_failure_freeze_source_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol,
        "V180R12R3_FAILURE_FREEZE_SOURCE_SHA256",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="source byte identity changed",
    ):
        protocol.failed_dispatch_repair_lineage_contract_v180r12r4()


def test_immediate_failed_replay_lineage_rejects_absence_inventory_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol.failed_external_replay_predecessor,
        "_REQUIRED_ABSENT_PATHS",
        protocol.V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS[:-1],
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="source authority changed",
    ):
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()


def test_immediate_failed_replay_lineage_rejects_source_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        protocol,
        "V180R12R3R1_FAILURE_FREEZE_SOURCE_SHA256",
        "0" * 64,
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="source byte identity changed",
    ):
        protocol.failed_external_replay_repair_lineage_contract_v180r12r4()


def test_protocol_grammar_exactly_matches_route_free_kernel_and_lifecycle() -> None:
    document = frozen().to_document()
    grammar = document["event_grammar"]
    assert tuple(grammar["phase_order"]) == protocol.PHASE_ORDER
    assert protocol.PHASE_ORDER == ledger.CAMPAIGN_LEDGER_PHASES
    assert tuple(grammar["actor_roles"]) == ("OBSERVER", "SUPERVISOR", "WORKER")
    assert tuple(grammar["required_event_kinds"]) == tuple(ledger.REQUIRED_EVENT_KINDS)
    assert dict(protocol.EVENT_KIND_ROLE_PHASES) == ledger.EVENT_KIND_ROLE_PHASES
    assert grammar["successful_minimum_event_count"] == 625
    assert grammar["successful_exact_event_count"] == 625
    assert grammar["phase_order_is_monotone"] is True
    assert grammar["required_event_kinds_are_not_a_one_each_total_order"] is True
    assert grammar["successful_expanded_event_schedule_order_is_exact"] is True
    assert grammar["successful_event_order_is_exact"] is True
    assert grammar["successful_event_schedule_template_count"] == 625
    assert grammar["successful_event_schedule_operation_ids_present"] is False
    operations = {
        row.operation_id: row
        for row in ledger.build_campaign_operation_schedule_v180r12r4("0" * 64)
    }
    expected_schedule = []
    for sequence, event in enumerate(
        ledger.build_campaign_success_event_schedule_v180r12r4("0" * 64)
    ):
        operation = operations[event.operation_id]
        expected_schedule.append(
            {
                "sequence": sequence,
                "event_kind": event.event_kind,
                "actor_role": event.actor_role,
                "phase": event.phase,
                "operation_slot": operation.slot,
                "operation_family": operation.family,
                "operation_ordinal": operation.ordinal,
            }
        )
    assert grammar["successful_event_schedule_template"] == expected_schedule
    counts = {
        row["event_kind"]: row["count"]
        for row in grammar["successful_event_cardinalities"]
    }
    assert counts["INPUT_READ_INTENT"] == counts["INPUT_READ_OUTCOME"] == 5
    assert counts["STAGE_WRITE_OUTCOME"] == 2
    assert counts["MOUNT_VISIBILITY_OPEN"] == 2
    assert counts["MOUNT_VISIBILITY_CLOSE"] == 2
    assert counts["PROCESS_BIRTH_OUTCOME"] == counts["PROCESS_REAP"] == 2
    assert counts["SEMANTIC_HASH_OUTCOME"] == 137
    assert counts["INTEGRITY_CHECK_OUTCOME"] == 145
    assert counts["PROTOCOL_CHECK_OUTCOME"] == 15
    assert grammar["subject_write_pair_phase"] == "WORKER"
    assert grammar["subject_write_pair_actor_role"] == "WORKER"
    assert grammar["subject_commit_phase"] == "COMMIT"
    assert grammar["subject_commit_actor_role"] == "SUPERVISOR"
    assert grammar["successful_mount_open_measured_values_in_exact_order"] == [
        199_755,
        202_507,
    ]
    assert grammar["successful_mount_close_measured_values_in_exact_order"] == [
        None,
        None,
    ]
    assert grammar["fallible_paired_operation_count"] == 307
    assert grammar[
        "every_fallible_paired_operation_emits_exact_intent_then_outcome"
    ] is True
    assert grammar["process_birth_operations_emit_intent_outcome_then_reap"] is True
    assert grammar["mount_interval_operations_emit_open_then_close"] is True
    assert grammar["singleton_operation_count"] == 5
    assert grammar["singleton_operation_slots"] == [
        "ATTEMPT",
        "SUBJECT_COMMIT",
        "WINDOW",
        "CGROUP",
        "LEDGER",
    ]
    assert grammar["unqualified_every_operation_intent_outcome_claim"] is False
    assert grammar["monotonic_ns_strictly_increasing"] is True


def test_protocol_freezes_nine_actual_paths_and_os_backed_derivations() -> None:
    document = frozen().to_document()
    assert tuple(document["campaign_paths"]) == protocol.CAMPAIGN_PATHS
    assert document["campaign_path_count"] == 9
    assert document["route_kind"] is None
    assert document["route_free_campaign_scope_required"] is True
    rules = {
        row["path"]: row["rule"]
        for row in document["measurement_derivation_contract"]
    }
    assert tuple(rules) == protocol.CAMPAIGN_PATHS
    assert rules["io.read_bytes"] == "SUM_INPUT_READ_OUTCOME_RETURNED_BYTES"
    assert rules["io.staged_bytes"] == "SUM_STAGE_WRITE_OUTCOME_RETURNED_BYTES"
    assert rules["io.output_bytes"] == "SUM_SUBJECT_WRITE_OUTCOME_RETURNED_BYTES"
    assert rules["memory.working_bytes_peak"] == (
        "SAME_MEASUREMENT_ROOT_CGROUP_MEMORY_PEAK_AFTER_REAP"
    )
    assert document["actual_read_and_write_return_values_required"] is True
    assert document["native_zero_required_for_each_zero_valued_path"] is False
    assert document["derived_denominator_or_authorization_cap_is_actual_measurement"] is False
    assert document["campaign_actual_counter_record_count"] == 0
    assert document["successful_campaign_counter_record_count"] == 9
    assert document["successful_campaign_work_vector_count"] == 1
    assert document["successful_campaign_comparison_vector_count"] == 1
    assert document["successful_campaign_projection_proof_count"] == 1
    assert document["successful_campaign_native_zero_attestation_count"] == 1
    assert document["campaign_scope_kind"] == (
        "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
    )
    assert document["work_scope_kind"] == "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
    assert document["counter_registry_reference"] == "acfqp_counter_registry_v6"
    assert document["native_zero_required_for_each_zero_valued_path"] is False
    assert document["native_zero_comparison_axis"] == "kernel_transition_calls"
    assert document["native_zero_comparison_axis_value"] == 0
    assert document["projection_proof_references_native_zero_attestation"] is True


def test_protocol_freezes_every_actual_check_operation_without_grouping_inner_ids() -> None:
    document = frozen().to_document()
    manifest = document["actual_operation_manifest"]
    assert manifest["operation_schedule_template_count"] == 314
    assert manifest["semantic_operation_count"] == 297
    assert manifest["lifecycle_operation_count"] == 17
    assert manifest["operation_ids_present_in_protocol_template"] is False
    expected_template = [
        {
            "slot": row.slot,
            "family": row.family,
            "ordinal": row.ordinal,
            "phase": row.phase,
            "actor_role": row.actor_role,
        }
        for row in ledger.build_campaign_operation_schedule_v180r12r4("0" * 64)
    ]
    assert manifest["operation_schedule_template"] == expected_template
    assert manifest["semantic_hash_operation_count"] == 137
    assert manifest["integrity_check_operation_count"] == 145
    assert manifest["protocol_check_operation_count"] == 15
    assert manifest["inner_content_id_operation_count"] == 129
    assert len(manifest["semantic_hash_operation_labels"]) == 137
    assert len(manifest["integrity_check_operation_labels"]) == 145
    assert len(manifest["protocol_check_operation_labels"]) == 15
    assert tuple(manifest["protocol_check_families"]) == protocol.PROTOCOL_CHECK_FAMILIES
    assert manifest["manifest_labels_are_runtime_operation_ids"] is False
    assert manifest["runtime_operation_id_derivation"] == (
        "REGISTERED_CONTENT_ID_OF_ATTEMPT_ID_SLOT_FAMILY_AND_ORDINAL"
    )
    assert manifest["grouped_inner_content_id_operation_forbidden"] is True
    assert manifest["fallible_paired_operation_count"] == 307
    assert manifest[
        "every_fallible_paired_operation_requires_one_intent_and_one_success_or_pass_outcome"
    ] is True
    assert manifest["mount_interval_operation_count"] == 2
    assert manifest[
        "mount_interval_operations_use_open_close_not_intent_outcome"
    ] is True
    assert manifest["singleton_operation_count"] == 5
    assert manifest[
        "singleton_operations_are_post_effect_atomic_observations_without_intent_claim"
    ] is True
    assert manifest["unqualified_every_operation_intent_outcome_claim"] is False
    segments = {
        (row["family"], row["actor_role"], row["phase"]): row["operation_count"]
        for row in manifest["operation_role_phase_segments"]
    }
    assert segments == {
        ("SEMANTIC_HASH", "SUPERVISOR", "STAGE"): 2,
        ("SEMANTIC_HASH", "WORKER", "WORKER"): 134,
        ("SEMANTIC_HASH", "SUPERVISOR", "COMMIT"): 1,
        ("INTEGRITY_CHECK", "SUPERVISOR", "STAGE"): 6,
        ("INTEGRITY_CHECK", "WORKER", "WORKER"): 137,
        ("INTEGRITY_CHECK", "SUPERVISOR", "COMMIT"): 2,
        ("PROTOCOL_CHECK", "WORKER", "WORKER"): 15,
    }
    assert document["v180r12r2_top_and_129_inner_content_ids_replayed"] is True
    assert document["worker_imports_v180r12r2_result_evidence_helper"] is False
    assert document[
        "v180r7r1_construction_axis_replayed_as_independent_predecessor_evidence"
    ] is True
    assert document[
        "v180r7r1_construction_axis_charged_as_successor_campaign_authoritative_receipt"
    ] is False
    assert document["worker_import_contract"] == (
        protocol.worker_import_contract_v180r12r4()
    )
    assert document["worker_import_contract"][
        "lazy_local_imports_after_attempt_open_forbidden"
    ] is True
    assert set(document["worker_import_contract"]) == {
        "schema",
        "allowed_local_imports",
        "forbidden_imports",
        "repo_and_runtime_sources_precompiled_before_attempt",
        "lazy_local_imports_after_attempt_open_forbidden",
        "producer_or_heavy_verifier_import_forbidden",
        "import_manifest_replayed_before_independent_counter_pass",
    }
    assert (
        "acfqp.construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2"
        in document["worker_forbidden_imports"]
    )


def test_protocol_binds_cgroup_parent_capability_without_using_self_membership_as_identity(
) -> None:
    parent = cgroup_parent_fact()
    capability = runtime_capability_fact()
    document = protocol.build_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=parent,
        runtime_capability_fact=capability,
    )
    assert document["cgroup_parent_fact"] == parent
    assert document["runtime_capability_fact"] == capability
    assert document["cgroup_parent_fact_bound_at_protocol_freeze"] is True
    assert document[
        "cgroup_parent_identity_fields_except_observer_self_membership_must_be_"
        "reobserved_exactly_before_attempt"
    ] is True
    assert document["cgroup_parent_reobserved_identity_fields"] == [
        field for field in protocol.CGROUP_PARENT_FACT_FIELDS
        if field != "self_membership"
    ]
    assert document["self_membership_is_parent_identity"] is False
    assert document["frozen_self_membership_is_capture_provenance_only"] is True
    assert document[
        "production_source_self_membership_is_verified_separately_at_t1_t2_t3"
    ] is True
    assert document["measurement_root_children"] == ["SUPERVISOR", "WORKER"]
    assert document["measurement_root_and_leaf_role_fact_count"] == 3
    assert document["measurement_root_no_internal_process_rule_required"] is True
    assert document["cgroup_parent_owner_uid_equals_runtime_uid"] is True
    assert document["cgroup_parent_owner_gid_equals_runtime_gid"] is True
    assert document["cgroup_parent_owner_write_and_execute_required"] is True


@pytest.mark.parametrize(("field", "replacement"), [("owner_uid", 999), ("owner_gid", 999)])
def test_protocol_rejects_resigned_foreign_cgroup_owner(
    field: str, replacement: int
) -> None:
    parent = cgroup_parent_fact()
    parent[field] = replacement
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="owner/runtime identity",
    ):
        protocol.build_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=parent,
            runtime_capability_fact=runtime_capability_fact(),
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("subtree_control", ["memory"]),
        ("memory_peak_present", False),
        ("parent_device", 26),
        ("self_membership", "1:name=/"),
        ("mount_options", ["rw", "nodev"]),
    ],
)
def test_protocol_rejects_cgroup_parent_drift(field: str, replacement) -> None:
    value = cgroup_parent_fact()
    value[field] = replacement
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        protocol.build_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=value,
            runtime_capability_fact=runtime_capability_fact(),
        )


def test_generic_cgroup_validator_accepts_available_cpu_without_enabling_it(
) -> None:
    parent = cgroup_parent_fact()
    parent["subtree_control"] = ["memory", "pids"]
    assert parent["controllers"] == ["cpu", "memory", "pids"]
    assert parent["subtree_control"] == ["memory", "pids"]
    assert protocol.validate_cgroup_parent_fact_v180r12r4(parent) == parent


def test_supervisor_contract_separates_parent_available_and_enabled_controllers(
) -> None:
    contract = supervisor.supervisor_contract_v180r12r4()
    assert contract["required_parent_controllers"] == ["memory", "pids"]
    assert contract["measurement_root_available_controllers_source"] == (
        "PARENT_SUBTREE_CONTROL"
    )
    assert contract["measurement_root_enabled_controllers"] == ["memory", "pids"]
    assert "cgroup_controllers" not in contract


def test_failure_contract_binds_topology_diagnostic_as_top_level_field() -> None:
    contract = protocol.failure_observation_contract_v180r12r4()
    assert "cgroup_topology_conformance_diagnostic" in (
        contract["failure_state_fields"]
    )
    assert supervisor.FAILURE_STATE_FIELD_KEYS == frozenset(
        contract["failure_state_fields"]
    )
    assert "cgroup_topology_conformance_diagnostic" not in (
        contract["failure_cgroup_observation_fields"]
    )


def test_protocol_rejects_bootstrap_container_types_before_explicit_thaw() -> None:
    value = cgroup_parent_fact()
    value["mount_options"] = tuple(value["mount_options"])
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="not canonically serializable",
    ):
        protocol.validate_cgroup_parent_fact_v180r12r4(value)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("single_threaded", False),
        ("clone3_syscall_recognized", False),
        ("pidfd_wait_present", False),
        ("landlock_abi", 0),
        ("effective_capability_mask", 1),
        ("admitted", False),
    ],
)
def test_protocol_rejects_runtime_capability_drift(field: str, replacement) -> None:
    value = runtime_capability_fact()
    value[field] = replacement
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        protocol.build_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=cgroup_parent_fact(),
            runtime_capability_fact=value,
        )


def test_protocol_caps_one_shot_failure_and_claim_boundaries_are_exact() -> None:
    document = frozen().to_document()
    caps = document["resource_contract"]
    assert caps["wall_timeout_seconds"] == 14_400
    assert caps["memory_max_bytes"] == 16 * 1024 * 1024 * 1024
    assert caps["address_space_hard_cap_bytes"] == 16 * 1024 * 1024 * 1024
    assert caps["pids_max"] == 2
    assert caps["input_file_byte_cap"] == 1 * 1024 * 1024
    assert caps["input_total_byte_cap"] == 2 * 1024 * 1024
    assert caps["subject_result_byte_cap"] == 1 * 1024 * 1024
    assert caps["terminal_byte_cap"] == caps["verification_byte_cap"] == 16 * 1024 * 1024
    assert caps["max_event_count"] == 4_096
    assert caps["max_event_byte_count"] == 65_536
    assert caps["max_ledger_byte_count"] == 64 * 1024 * 1024
    assert caps["clone3_clone_into_cgroup_required"] is True
    assert caps["pidfd_required"] is True
    assert document["same_attempt_identity_rerun_forbidden"] is True
    assert document["attempt_identity_consumed_by_success_failure_timeout_or_cap_violation"] is True
    assert document[
        "campaign_failure_forbidden_at_terminal_publication_attempt_entry"
    ] is True
    assert document[
        "terminal_publication_attempt_entry_precedes_open_parent_and_o_excl"
    ] is True
    assert document["post_terminal_child_or_bootstrap_error_is_outer_launch_failure"] is True
    assert document["pending_terminal_requires_measurement_launch_receipt_for_acceptance"] is True
    assert document["V180R12R2_COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["terminal_counter_completeness_gate_on_success"] == (
        "PENDING_INDEPENDENT_REPLAY"
    )
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
    assert document["BREAK_EVEN_GATE"] == "NOT_RUN"
    assert document["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False
    assert document["measured_scope_is_fresh_replay_successor_overhead"] is True
    assert document["measured_scope_is_retroactive_v180r12r2_aggregation_cost"] is False
    assert document["campaign_measurement_authorization_issued"] is False
    assert document["campaign_measurement_execution_started"] is False
    assert document["zero_sentinel_draft_is_executable_authorization"] is False
    assert document["source_bound_prelaunch_required_before_real_outcome_execution"] is True


def test_protocol_identity_phase_and_content_ids_are_replayable() -> None:
    first = frozen()
    second = frozen()
    assert first.canonical_bytes == second.canonical_bytes
    document = first.to_document()
    final_phase = protocol.EXPECTED_PROTOCOL_ID != protocol.ZERO_ID
    assert document["identity_literals_frozen"] is final_phase
    if final_phase:
        assert protocol.EXPECTED_CANONICAL_BYTE_COUNT > 0
        assert all(
            value != protocol.ZERO_ID
            for value in (
                protocol.EXPECTED_CANONICAL_SHA256,
                protocol.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID,
                protocol.LOGICAL_OCCURRENCE_ID,
                protocol.EXECUTION_NONCE,
            )
        )
    else:
        assert protocol.EXPECTED_CANONICAL_BYTE_COUNT == 0
        assert all(
            value == protocol.ZERO_ID
            for value in (
                protocol.EXPECTED_CANONICAL_SHA256,
                protocol.EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID,
            )
        )
        assert protocol.LOGICAL_OCCURRENCE_ID != protocol.ZERO_ID
        assert protocol.EXECUTION_NONCE != protocol.ZERO_ID
    rule_ids = (
        protocol.EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID,
        protocol.EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID,
        protocol.EXPECTED_PRELAUNCH_LAUNCH_RULE_ID,
    )
    assert all(value == protocol.ZERO_ID for value in rule_ids) or all(
        value != protocol.ZERO_ID for value in rule_ids
    )
    payload = dict(document)
    identity = payload.pop("campaign_measurement_protocol_id")
    assert identity == domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_PROTOCOL_V180R12R4_DOMAIN,
        payload,
    )
    assert hashlib.sha256(first.canonical_bytes).hexdigest()


def test_protocol_wrapper_rejects_foreign_issuer_and_pickle() -> None:
    value = frozen()
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        protocol.CampaignMeasurementProtocolV180R12R4(
            object(),
            value.canonical_bytes,
            value.campaign_measurement_protocol_id,
            value.campaign_measurement_execution_slot_id,
        )
    with pytest.raises((TypeError, pickle.PicklingError)):
        pickle.dumps(value)


def _protocol_anchor_source(values: dict[str, object]) -> bytes:
    return "".join(
        f"{name} = {values[name]!r}\n"
        for name in protocol.PROTOCOL_FINAL_ANCHOR_NAMES
    ).encode("utf-8")


def test_protocol_final_anchor_gate_requires_exact_direct_nonzero_literals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values: dict[str, object] = {
        name: (101 if name == "EXPECTED_CANONICAL_BYTE_COUNT" else "1" * 64)
        for name in protocol.PROTOCOL_FINAL_ANCHOR_NAMES
    }
    for name, value in values.items():
        monkeypatch.setattr(protocol, name, value)
    monkeypatch.setattr(
        protocol,
        "_read_protocol_source_bytes_v180r12r4",
        lambda: _protocol_anchor_source(values),
    )
    assert protocol.require_frozen_protocol_final_anchor_set_v180r12r4() == values

    nonliteral = _protocol_anchor_source(values).replace(
        b"EXPECTED_PROTOCOL_ID = '" + b"1" * 64 + b"'",
        b"EXPECTED_PROTOCOL_ID = ZERO_ID",
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="duplicated or nonliteral",
    ):
        protocol.protocol_final_anchor_literals_v180r12r4(nonliteral)

    values["EXPECTED_PRELAUNCH_LAUNCH_RULE_ID"] = protocol.ZERO_ID
    monkeypatch.setattr(
        protocol, "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID", protocol.ZERO_ID
    )
    monkeypatch.setattr(
        protocol,
        "_read_protocol_source_bytes_v180r12r4",
        lambda: _protocol_anchor_source(values),
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="not fully frozen",
    ):
        protocol.require_frozen_protocol_final_anchor_set_v180r12r4()


def test_protocol_nonzero_identity_fails_before_build_on_incomplete_final_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(protocol, "EXPECTED_PROTOCOL_ID", "1" * 64)
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="final anchor",
    ):
        protocol.build_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=cgroup_parent_fact(),
            runtime_capability_fact=runtime_capability_fact(),
        )


def test_protocol_complete_direct_final_anchor_set_freezes_exact_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_gate = protocol.require_frozen_protocol_final_anchor_set_v180r12r4
    for name, value in (
        ("EXPECTED_PROTOCOL_ID", "a" * 64),
        ("EXPECTED_CANONICAL_BYTE_COUNT", 1),
        ("EXPECTED_CANONICAL_SHA256", "b" * 64),
        ("EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID", protocol.ZERO_ID),
        ("LOGICAL_OCCURRENCE_ID", "c" * 64),
        ("EXECUTION_NONCE", "d" * 64),
        ("EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID", "e" * 64),
        ("EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID", "f" * 64),
        ("EXPECTED_PRELAUNCH_LAUNCH_RULE_ID", "1" * 64),
    ):
        monkeypatch.setattr(protocol, name, value)
    monkeypatch.setattr(
        protocol,
        "require_frozen_protocol_final_anchor_set_v180r12r4",
        lambda: {},
    )
    candidate = protocol.build_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
    )
    slot_id = candidate["campaign_measurement_execution_slot"][
        "campaign_measurement_execution_slot_id"
    ]
    monkeypatch.setattr(
        protocol, "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID", slot_id
    )
    candidate = protocol.build_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
    )
    protocol_id = candidate["campaign_measurement_protocol_id"]
    raw = canonical_json_bytes(candidate)
    monkeypatch.setattr(protocol, "EXPECTED_PROTOCOL_ID", protocol_id)
    monkeypatch.setattr(protocol, "EXPECTED_CANONICAL_BYTE_COUNT", len(raw))
    monkeypatch.setattr(
        protocol, "EXPECTED_CANONICAL_SHA256", hashlib.sha256(raw).hexdigest()
    )
    values = {
        name: getattr(protocol, name)
        for name in protocol.PROTOCOL_FINAL_ANCHOR_NAMES
    }
    monkeypatch.setattr(
        protocol,
        "_read_protocol_source_bytes_v180r12r4",
        lambda: _protocol_anchor_source(values),
    )
    # Restore the real gate after the candidate-only bypass above.
    monkeypatch.setattr(
        protocol,
        "require_frozen_protocol_final_anchor_set_v180r12r4",
        original_gate,
    )
    frozen_value = protocol.freeze_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact(),
        runtime_capability_fact=runtime_capability_fact(),
    )
    assert frozen_value.canonical_bytes == raw
    assert frozen_value.campaign_measurement_protocol_id == protocol_id


def test_protocol_freeze_rejects_parent_fact_outside_source_bound_capture() -> None:
    first = frozen()
    changed = cgroup_parent_fact()
    changed["parent_inode"] += 1
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="same V180r12r4r5 source-bound service-context capture",
    ):
        protocol.freeze_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=changed,
            runtime_capability_fact=runtime_capability_fact(),
        )
    assert canonical_json_bytes(first.to_document()) == first.canonical_bytes


def test_protocol_rejects_unregistered_extra_fact_field() -> None:
    value = copy.deepcopy(cgroup_parent_fact())
    value["observed_outcome"] = "NOT_ALLOWED"
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        protocol.validate_cgroup_parent_fact_v180r12r4(value)


def test_protocol_prelaunch_contract_is_fresh_outcome_free_and_externally_observed() -> None:
    document = frozen().to_document()
    contract = document["prelaunch_contract"]
    assert contract == protocol.prelaunch_contract_v180r12r4()
    rule_ids = (
        protocol.EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID,
        protocol.EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID,
        protocol.EXPECTED_PRELAUNCH_LAUNCH_RULE_ID,
    )
    assert contract["source_closure_rule_id"] == rule_ids[0]
    assert contract["materialization_rule_id"] == rule_ids[1]
    assert contract["launch_rule_id"] == rule_ids[2]
    assert contract["rule_identities_frozen"] is all(
        value != protocol.ZERO_ID for value in rule_ids
    )
    assert contract["source_bootstrap_relative_path"] == (
        "scripts/bootstrap_v180r12r4_campaign_measurement.py"
    )
    assert contract["materializer_relative_path"] == (
        "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py"
    )
    assert contract["retained_source_launcher_relative_path"] == (
        "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"
    )
    assert contract["trusted_outer_observer_relative_path"] == (
        "scripts/run_v180r12r4_campaign_measurement.py"
    )
    assert contract["measured_supervisor_entrypoint_relative_path"] == (
        "scripts/supervise_v180r12r4_campaign_measurement.py"
    )
    assert contract["measured_worker_entrypoint_relative_path"] == (
        "scripts/work_v180r12r4_campaign_measurement.py"
    )
    assert contract["producer_free_verifier_relative_path"] == (
        "scripts/verify_v180r12r4_campaign_measurement.py"
    )
    assert contract["retained_launcher_is_outside_campaign_accounting"] is True
    assert contract["trusted_outer_observer_is_outside_campaign_accounting"] is True
    assert contract["only_supervisor_and_worker_children_are_measured"] is True
    assert contract["outer_observer_births_exactly_one_supervisor"] is True
    assert contract["supervisor_births_exactly_one_worker"] is True
    assert contract["all_prelaunch_outcome_identities_absent"] is True
    assert contract["outcome_free"] is True


def test_protocol_freezes_exact_four_target_moduletype_execution_envelope() -> None:
    document = frozen().to_document()
    expected = (
        protocol.source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    assert document["source_bound_runner_execution_envelope_contract"] == expected
    assert document["prelaunch_contract"]["precompiled_runner_module_contract"] == (
        expected
    )
    assert expected == bootstrap_script._INTERNAL_TARGET_CONTRACT[
        "precompiled_runner_module_contract"
    ]
    assert expected == materialize_script.INTERNAL_TARGET_CONTRACT[
        "precompiled_runner_module_contract"
    ]
    assert expected == launch_script.INTERNAL_TARGET_CONTRACT[
        "precompiled_runner_module_contract"
    ]
    assert tuple(expected["target_order"]) == (
        "measurement",
        "verification",
        "supervisor",
        "worker",
    )
    assert len({row["module_name"] for row in expected["target_rows"]}) == 4
    assert expected["module_type"] == "types.ModuleType"
    assert expected["registered_before_runner_exec"] is True
    assert expected["registration_spans_exec_entrypoint_and_postchecks"] is True
    assert expected["preexisting_registration_fails_before_mutation"] is True
    assert expected["preexisting_registration_is_preserved"] is True
    assert expected[
        "replaced_deleted_or_metadata_drifted_registration_fails"
    ] is True
    assert expected[
        "registration_removed_after_postchecks_on_success_or_failure"
    ] is True
    assert expected["runner_module_registration_leak_forbidden"] is True
    assert expected[
        "runner_primary_error_precedes_registration_secondary"
    ] is True


def test_protocol_rejects_foreign_runner_module_execution_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = copy.deepcopy(
        protocol.source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    changed["target_rows"][0]["module_name"] = "_foreign_runner"
    monkeypatch.setattr(
        protocol,
        "source_bound_runner_execution_envelope_contract_v180r12r4",
        lambda: copy.deepcopy(changed),
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="denominator or event cap changed",
    ):
        frozen()


def test_protocol_freezes_external_context_transport_and_runtime_ipc_exactly() -> None:
    contract = frozen().to_document()["prelaunch_contract"]
    assert contract["external_launch_context_schema"] == (
        run_script.EXTERNAL_LAUNCH_CONTEXT_SCHEMA
    )
    assert tuple(contract["external_launch_context_fields"]) == (
        run_script.EXTERNAL_LAUNCH_CONTEXT_FIELDS
    )
    assert contract["verified_external_launch_context_schema"] == (
        run_script.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA
    )
    assert tuple(contract["verified_external_launch_context_fields"]) == (
        run_script.VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
    )
    assert tuple(contract["frozen_authorization_context_fields"]) == (
        verify_script.FROZEN_AUTHORIZATION_CONTEXT_FIELDS
    )
    assert tuple(contract["measurement_cgroup_observation_phases"]) == (
        protocol.MEASUREMENT_CGROUP_OBSERVATION_PHASES
    )
    assert frozenset(contract["measurement_cgroup_observation_fields"]) == (
        frozenset(protocol.MEASUREMENT_CGROUP_OBSERVATION_FIELDS)
    )
    assert (
        contract["sock_seqpacket_buffer_request_bytes"]
        == protocol.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == run_script.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == supervise_script.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == materialize_script.SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        == 1_048_576
    )
    assert (
        contract["sock_seqpacket_effective_min_bytes"]
        == protocol.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == run_script.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == supervise_script.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == materialize_script.SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        == 2_097_152
    )
    assert contract[
        "sock_seqpacket_so_sndbuf_and_so_rcvbuf_required_on_both_endpoints"
    ] is True
    assert contract[
        "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send"
    ] is True
    assert contract[
        "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation"
    ] is True
    assert contract["external_target_actor_roles"] == {
        "measurement": "OBSERVER",
        "verification": "VERIFIER",
    }
    assert contract["external_context_memfd"] == 249
    assert contract["delegated_cgroup_parent_fd"] == 250
    assert contract["cgroup2_mount_fd"] == 251
    assert contract["measurement_launch_one_shot_order"] == [
        "O_EXCL_MEASUREMENT_LAUNCH_ATTEMPT",
        "FREEZE_SINGLE_CLOCK_MONOTONIC_ORIGIN_AND_TWO_ABSOLUTE_DEADLINES",
        "OPEN_AND_VALIDATE_FD_250_AND_FD_251",
        "OPEN_AND_VALIDATE_SOURCE_SERVICE_FD_252_AND_T1_PLACEMENT",
        "CONSTRUCT_AND_SEAL_FD_249",
        "EXEC_SOURCE_BOUND_BOOTSTRAP",
        "REPLAY_EXTERNAL_CONTEXT_AND_FACTS",
        "T2_REVALIDATE_SOURCE_PLACEMENT_BEFORE_ATTEMPT_O_EXCL",
        "O_EXCL_CAMPAIGN_ATTEMPT",
    ]
    assert contract["run_cgroup_parent_reobserve_api"] == (
        "reobserve_cgroup_parent_fact_from_inherited_fds_v180r12r4"
    )
    assert contract["run_runtime_capability_reobserve_api"] == (
        "reobserve_runtime_capability_fact_v180r12r4"
    )
    assert tuple(contract["runtime_ipc_frame_fields"]) == (
        "schema",
        "channel_id",
        "direction",
        "sender_actor_role",
        "recipient_actor_role",
        "frame_type",
        "sequence",
        "body",
        "mac",
    )
    assert tuple(contract["runtime_ipc_unsigned_frame_fields"]) == tuple(
        contract["runtime_ipc_frame_fields"][:-1]
    )
    assert tuple(contract["runtime_channel_key_context_fields"]) == (
        "schema",
        "channel_id",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "parent_actor_role",
        "child_actor_role",
        "direction",
    )
    assert tuple(contract["event_proposal_body_fields"]) == (
        run_script.EVENT_PROPOSAL_BODY_FIELDS
    )
    assert tuple(contract["event_ack_body_fields"]) == (
        run_script.EVENT_ACK_BODY_FIELDS
    )
    assert contract["snapshot_bytes_transport_schema"] == (
        run_script.SNAPSHOT_BYTES_TRANSPORT_SCHEMA
    )
    assert tuple(contract["snapshot_bytes_transport_fields"]) == (
        run_script.SNAPSHOT_BYTES_TRANSPORT_FIELDS
    )
    assert contract["snapshot_bytes_transport_byte_cap"] == (
        run_script.SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP
    )
    assert contract["snapshot_bytes_transport_event_rows"] == [
        {
            "campaign_event_sequence": sequence,
            "phase": phase,
            "actor_role": actor_role,
            "event_kind": event_kind,
            "role": role,
        }
        for sequence, phase, actor_role, event_kind, role
        in protocol.SNAPSHOT_BYTES_TRANSPORT_EVENT_ROWS
    ]
    assert contract["snapshot_bytes_transport_exact_occurrence_count"] == 2
    assert contract["snapshot_bytes_transport_is_transport_only_not_evidence_document"]
    assert contract["snapshot_bytes_transport_excluded_from_328_evidence_inventory"]
    assert contract["snapshot_bytes_transport_excluded_from_five_measured_read_receipts"]
    assert contract["observer_filesystem_reread_for_snapshot_rehydration_forbidden"]
    assert contract["observer_rehydrates_with_original_stable_snapshot_constructor"]
    assert contract["runtime_ipc_mac_covers_every_unsigned_frame_field"] is True
    assert contract["runtime_ipc_effect_or_progress_before_ack_forbidden"] is True
    runtime_rows = tuple(
        (
            parent,
            child,
            direction,
            tuple(sorted(frame_types)),
        )
        for parent, child in (("OBSERVER", "SUPERVISOR"), ("SUPERVISOR", "WORKER"))
        for direction in ("PARENT_TO_CHILD", "CHILD_TO_PARENT")
        for frame_types in (
            run_script.AuthenticatedFrameChannelV180R12R4._ROLE_FRAME_TYPES[
                (parent, child)
            ][direction],
        )
    )
    assert runtime_rows == protocol.RUNTIME_IPC_ROLE_FRAME_TYPE_ROWS
    assert tuple(
        (parent, child, frame_type)
        for (parent, child), frame_type in sorted(
            run_script.AuthenticatedFrameChannelV180R12R4._FIRST_PARENT_FRAME.items()
        )
    ) == protocol.RUNTIME_IPC_FIRST_PARENT_FRAME_ROWS
    assert contract["runtime_ipc_undefined_control_frame_types"] == [
        "FAILURE_NOTICE",
        "SUPERVISOR_COMPLETE",
        "WORKER_COMPLETE",
    ]
    assert contract["runtime_ipc_undefined_control_frames_forbidden"] is True
    assert contract[
        "runtime_ipc_completion_uses_exact_channel_eof_then_pidfd_wait_status"
    ] is True
    assert contract[
        "runtime_ipc_eof_before_exact_expected_event_boundary_is_failure"
    ] is True
    assert contract["runtime_ipc_recvmsg_flags_must_be_zero"] is True
    assert contract["runtime_ipc_recvmsg_ancillary_must_be_empty"] is True
    assert contract["runtime_ipc_recvmsg_address_must_be_empty_or_none"] is True


def test_protocol_start_requires_canonical_topology_and_birth_documents() -> None:
    contract = frozen().to_document()["prelaunch_contract"]
    assert tuple(contract["observer_supervisor_start_fields"]) == (
        run_script.OBSERVER_SUPERVISOR_START_FIELDS
    )
    assert "cgroup_topology_document" in contract[
        "observer_supervisor_start_fields"
    ]
    assert "supervisor_birth_document" in contract[
        "observer_supervisor_start_fields"
    ]
    assert contract[
        "observer_supervisor_start_requires_full_canonical_topology_document"
    ] is True
    assert contract[
        "observer_supervisor_start_requires_full_canonical_supervisor_birth_document"
    ] is True
    assert contract[
        "observer_supervisor_start_documents_recompute_exact_schema_keyset_domain_identity"
    ] is True
    assert contract["observer_supervisor_start_topology_joins_worker_leaf_fd_245"]
    assert contract[
        "observer_supervisor_start_birth_joins_topology_attempt_operation_and_internal_context"
    ]
    assert contract["observer_supervisor_start_id_only_authority_forbidden"]


def test_protocol_attempt_authority_uses_six_inputs_and_excludes_transport() -> None:
    document = frozen().to_document()
    expected = [
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
    ]
    assert document["campaign_attempt_identity_input_fields"] == expected
    assert document["campaign_attempt_identity_includes_fresh_authorization_evidence_id"]
    assert document[
        "campaign_attempt_identity_excludes_cgroup_runtime_and_transport_facts"
    ]
    transport = [
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
    ]
    assert document[
        "campaign_attempt_record_and_terminal_transport_provenance_fields"
    ] == transport
    assert set(expected).isdisjoint(transport)
    assert document["measurement_launch_receipt_excluded_from_terminal_fixed_point"]


def test_protocol_mechanically_binds_registered_campaign_attempt_formula() -> None:
    contract = protocol.campaign_measurement_attempt_identity_contract_v180r12r4()
    assert contract == frozen().to_document()[
        "campaign_measurement_attempt_identity_contract"
    ]
    assert contract["attempt_schema"] == domains.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA
    assert contract["attempt_domain"] == (
        domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
    )
    assert contract["domain_registry_value"] == contract["attempt_domain"]
    assert tuple(contract["payload_fields"]) == (
        "schema",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "campaign_measurement_execution_slot_id",
        "logical_occurrence_id",
        "execution_nonce",
    )
    values = {
        field: f"{index:x}" * 64
        for index, field in enumerate(contract["identity_input_fields"], start=1)
    }
    payload = {"schema": contract["attempt_schema"], **values}
    expected = domains.extension_content_id_v180r12r4(
        contract["attempt_domain"], payload
    )
    assert domains.derive_campaign_measurement_attempt_id_v180r12r4(
        **values
    ) == expected
    for field in contract["identity_input_fields"]:
        changed = dict(values)
        changed[field] = "f" * 64
        assert domains.derive_campaign_measurement_attempt_id_v180r12r4(
            **changed
        ) != expected


def test_protocol_preregisters_exact_328_document_evidence_inventory() -> None:
    document = frozen().to_document()
    inventory = document["terminal_evidence_inventory_contract"]
    assert inventory == protocol.evidence_inventory_contract_v180r12r4()
    assert inventory["typed_document_type_count"] == 18
    assert inventory["typed_document_count"] == 328
    assert inventory["direct_event_evidence_document_count"] == 317
    assert inventory["support_evidence_document_count"] == 11
    assert inventory["nonnull_event_evidence_count"] == 317
    assert inventory["null_event_evidence_count"] == 308
    counts = {
        row["evidence_type"]: row["document_count"]
        for row in inventory["typed_document_rows"]
    }
    assert counts == {
        "CAMPAIGN_ATTEMPT_RECORD": 1,
        "STABLE_INPUT_SNAPSHOT": 2,
        "IO_TRANSFER_RECEIPT": 8,
        "MEMFD_STAGE_RECEIPT": 2,
        "FD_VISIBILITY_RECEIPT": 4,
        "SEMANTIC_OPERATION_RECEIPT": 297,
        "PIDFD_BIRTH_RECEIPT": 2,
        "PIDFD_REAP_RECEIPT": 2,
        "CGROUP_TOPOLOGY_RECEIPT": 1,
        "CGROUP_OBSERVATION_RECEIPT": 1,
        "REPLAY_SUBJECT_RECEIPT": 1,
        "CAMPAIGN_SUBJECT_RESULT": 1,
        "SUBJECT_COMMIT_RECEIPT": 1,
        "WINDOW_CLOSURE_RECEIPT": 1,
        "CAMPAIGN_EXECUTION_CLOSURE": 1,
        "CAMPAIGN_OPERATION_MANIFEST": 1,
        "NATIVE_ZERO_SOURCE_MANIFEST": 1,
        "NATIVE_ZERO_IMPORT_INVENTORY": 1,
    }
    requirements = {
        row["event_kind"]: (row["evidence_type"], row["event_count"])
        for row in inventory["event_evidence_requirements"]
    }
    assert requirements["ATTEMPT_OPEN"] == ("CAMPAIGN_ATTEMPT_RECORD", 1)
    assert requirements["INPUT_READ_OUTCOME"] == ("IO_TRANSFER_RECEIPT", 5)
    assert requirements["SEMANTIC_HASH_OUTCOME"] == (
        "SEMANTIC_OPERATION_RECEIPT",
        137,
    )
    assert requirements["LEDGER_CLOSED"] == (None, 1)
    assert inventory["unknown_event_evidence_id_forbidden"] is True
    assert inventory["missing_required_event_evidence_id_forbidden"] is True
    assert inventory["duplicate_event_or_document_evidence_id_forbidden"] is True
    assert inventory["unregistered_evidence_id_forbidden"] is True
    assert inventory["extra_or_orphan_evidence_document_forbidden"] is True
    assert inventory["native_zero_attestation_is_inventory_document"] is False
    assert (
        "SEMANTIC_RECEIPTS_REFERENCE_EXACT_OPERATION_SOURCE_AND_IMPORT_MANIFESTS"
        in inventory["support_join_rules"]
    )
    assert (
        "REPLAY_SUBJECT_SHARES_EXACT_OPERATION_SOURCE_AND_IMPORT_MANIFEST_IDS_"
        "WITH_ALL_SEMANTIC_RECEIPTS"
        in inventory["support_join_rules"]
    )
    assert inventory["causal_join_rules"] == list(protocol.EVIDENCE_CAUSAL_JOIN_RULES)
    assert set(protocol.EVIDENCE_CAUSAL_JOIN_RULES) <= set(
        inventory["support_join_rules"]
    )
    assert inventory["campaign_attempt_record_written_o_excl_before_cgroup_creation"]
    assert inventory["campaign_attempt_record_contains_cgroup_topology_receipt_id"] is False
    assert inventory["final_subject_references_campaign_attempt_record_id"] is True
    assert inventory["final_subject_contains_semantic_operation_receipt_ids"] is False
    assert inventory["semantic_receipt_evidence_subject_is_campaign_attempt_record"]
    assert inventory["semantic_receipt_evidence_subject_is_future_final_subject"] is False
    assert inventory["semantic_receipt_count_bound_to_attempt_record"] == 297
    assert inventory["replay_subject_exact_semantic_receipt_id_count"] == 297
    assert inventory["subject_write_source_evidence_type"] == "CAMPAIGN_SUBJECT_RESULT"
    assert inventory["subject_write_target_evidence_type"] == (
        "WORKER_PIDFD_BIRTH_RECEIPT"
    )
    assert inventory["subject_write_references_future_replay_subject"] is False
    assert inventory["replay_subject_first_consumer_event_kind"] == "SUBJECT_COMMIT"
    assert inventory["subject_readback_source_evidence_type"] == (
        "CAMPAIGN_SUBJECT_RESULT"
    )
    assert inventory["subject_readback_target_evidence_type"] == (
        "SUPERVISOR_PIDFD_BIRTH_RECEIPT"
    )
    assert inventory["successful_event_may_reference_not_yet_issued_evidence"] is False


def test_protocol_freezes_pre_cgroup_attempt_anchor_and_no_future_evidence() -> None:
    document = frozen().to_document()
    grammar = document["event_grammar"]
    assert grammar["successful_event_evidence_id_must_be_issued_before_event_append"]
    assert grammar["successful_event_may_reference_not_yet_issued_evidence"] is False
    assert grammar["attempt_open_record_written_o_excl_before_cgroup_creation"]
    assert grammar["attempt_open_record_contains_cgroup_topology_receipt_id"] is False
    assert document["attempt_record_excludes_cgroup_topology_receipt_id"] is True
    assert document["successful_event_evidence_id_issued_before_event_append_required"]
    assert document["successful_event_future_evidence_reference_forbidden"]
    assert document["terminal_evidence_causal_join_rules"] == list(
        protocol.EVIDENCE_CAUSAL_JOIN_RULES
    )


def test_evidence_schema_identity_and_domain_rows_match_runtime_mechanically() -> None:
    protocol_rows = {row[:4] for row in protocol.EVIDENCE_INVENTORY_ROWS}
    runtime_rows = set(
        worker.EVIDENCE_DOCUMENT_CONTRACT_ROWS
        + supervisor.EVIDENCE_DOCUMENT_CONTRACT_ROWS
    )
    assert len(protocol_rows) == len(runtime_rows) == 18
    assert protocol_rows == runtime_rows
    assert protocol.CAMPAIGN_SUBJECT_RESULT_FIELDS == (
        worker.CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET
    )
    assert set(frozen().to_document()["campaign_subject_result_fields"]) == (
        worker.CAMPAIGN_SUBJECT_RESULT_FIELD_KEYSET
    )
    assert frozen().to_document()[
        "campaign_subject_result_echoes_authorization_evidence_and_transport_provenance"
    ] is True


def test_protocol_success_auxiliary_values_are_exactly_empty_by_every_kind() -> None:
    grammar = frozen().to_document()["event_grammar"]
    assert grammar["successful_event_auxiliary_values_exactly_empty"] is True
    assert grammar["nonempty_successful_event_auxiliary_values_forbidden"] is True
    assert {
        row["event_kind"]: row["auxiliary_names"]
        for row in grammar["successful_event_auxiliary_keysets"]
    } == {event_kind: [] for event_kind in protocol.REQUIRED_EVENT_KINDS}
    assert grammar["cgroup_observed_pids_peak_auxiliary_required"] is False
    assert grammar["cgroup_observed_pids_peak_is_in_registered_evidence_document"] is True
    assert grammar["trusted_observer_owns_all_durable_event_files_and_acks"] is True
    assert grammar["measured_children_append_durable_event_files"] is False


def test_protocol_distinguishes_empty_event_auxiliary_from_typed_semantic_receipts() -> None:
    contract = frozen().to_document()["terminal_evidence_inventory_contract"]
    assert contract[
        "event_payload_auxiliary_is_distinct_from_typed_evidence_auxiliary"
    ] is True
    rows = contract["semantic_operation_receipt_auxiliary_rows"]
    assert rows == [
        {
            "kind": kind,
            "name": name,
            "value_semantics": value_semantics,
            "receipt_count": count,
        }
        for kind, name, value_semantics, count
        in protocol.SEMANTIC_RECEIPT_AUXILIARY_ROWS
    ]
    assert sum(row["receipt_count"] for row in rows) == 297
    assert dict(ledger.SEMANTIC_RECEIPT_AUXILIARY_NAME_BY_KIND) == {
        kind: name
        for kind, name, _semantics, _count
        in protocol.SEMANTIC_RECEIPT_AUXILIARY_ROWS
    }
    assert contract["semantic_operation_receipt_exactly_one_auxiliary_row"] is True
    assert contract[
        "semantic_hash_observed_value_rederived_from_subject_input_and_inner_content_facts"
    ] is True
    assert contract["integrity_and_protocol_check_passed_is_exact_true"] is True


def test_protocol_freezes_90_plus_9_equals_99_without_relabeling_structural_lines() -> None:
    document = frozen().to_document()
    assert document["predecessor_occurrence_authoritative_receipt_count"] == 90
    assert document["predecessor_campaign_authoritative_receipt_count"] == 0
    assert document["predecessor_campaign_scope_structural_obligation_count"] == 9
    assert document["successful_campaign_authoritative_receipt_count"] == 9
    assert document["successful_combined_authoritative_receipt_count"] == 99
    assert document["terminal_pending_authoritative_receipt_join"] == {
        "counter_status": "PENDING_INDEPENDENT_REPLAY",
        "predecessor_occurrence_receipt_count": 90,
        "campaign_actual_receipt_count": 9,
        "combined_authoritative_receipt_count": 99,
    }
    assert document["independent_verifier_pass_authoritative_receipt_join"] == {
        **document["terminal_pending_authoritative_receipt_join"],
        "counter_status": "PASS",
    }
    assert document["predecessor_structural_nine_are_successor_actual_receipts"] is False


@pytest.mark.parametrize(
    ("constant", "replacement"),
    [
        ("PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT", 91),
        ("SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT", 10),
        ("SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT", 98),
    ],
)
def test_protocol_rejects_authoritative_receipt_denominator_drift(
    monkeypatch: pytest.MonkeyPatch, constant: str, replacement: int
) -> None:
    monkeypatch.setattr(protocol, constant, replacement)
    with pytest.raises(protocol.CampaignMeasurementProtocolV180R12R4Error):
        protocol.build_campaign_measurement_protocol_v180r12r4(
            cgroup_parent_fact=cgroup_parent_fact(),
            runtime_capability_fact=runtime_capability_fact(),
        )


def test_protocol_freezes_exact_arithmetic_positive_paths_and_bounded_native_zero() -> None:
    document = frozen().to_document()
    arithmetic = document["successful_measurement_arithmetic"]
    assert arithmetic["terminal_input_byte_count"] == 199_755
    assert arithmetic["verification_input_byte_count"] == 2_752
    assert arithmetic["input_total_byte_count"] == 202_507
    assert arithmetic["io.staged_bytes"] == 202_507
    assert arithmetic["io.mounted_bytes_peak"] == 202_507
    assert arithmetic["io.read_bytes_fixed_addend"] == 405_014
    assert arithmetic["common.hash_invocations"] == 137
    assert arithmetic["common.integrity_checks"] == 145
    assert arithmetic["common.protocol_checks"] == 15
    assert arithmetic["process.launches"] == 2
    assert document["successful_campaign_path_values_strictly_positive"] is True
    assert document["successful_zero_valued_campaign_path_receipt_count"] == 0
    assert document[
        "zero_valued_campaign_path_receipts_if_present_are_observations"
    ] is True
    assert document["native_zero_observed_false_for_all_nine_campaign_paths"] is True
    assert document["kernel_transition_calls_is_linux_syscall_count"] is False
    assert document["native_zero_registered_planning_operation_site_fact_count"] == 314
    assert document["native_zero_is_open_world_no_kernel_call_claim"] is False
    assert document["unregistered_or_dynamic_ground_kernel_operation_sites_forbidden"] is True
    assert document["prelaunch_sealed_application_import_allowlist_required"] is True
    assert document["producer_terminal_runtime_role_exit_origin_guard_status"] == (
        "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
    )
    assert document[
        "measurement_launch_receipt_transitively_proves_frozen_bootstrap_post_dispatch_guard"
    ] is True


def test_semantic_hash_counter_excludes_all_registered_instrumentation_hashes() -> None:
    document = frozen().to_document()
    contract = document["semantic_hash_counter_scope_contract"]
    assert contract == protocol.semantic_hash_counter_scope_contract_v180r12r4()
    assert contract["counter_path"] == "common.hash_invocations"
    assert contract["counted_operation_count"] == 137
    assert tuple(contract["counted_operation_labels"]) == (
        protocol.SEMANTIC_HASH_OPERATION_LABELS
    )
    assert tuple(contract["excluded_instrumentation_classes"]) == (
        protocol.SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES
    )
    assert contract[
        "all_evidence_receipt_and_support_document_content_ids_excluded"
    ] is True
    assert contract[
        "all_evidence_receipt_and_support_document_canonicalization_excluded"
    ] is True
    assert contract["all_evidence_and_support_sha_fields_excluded"] is True
    assert contract["ipc_journal_ledger_and_prelaunch_hashing_excluded"] is True
    assert contract["unmanifested_semantic_hash_site_permitted"] is False
    assert document[
        "all_evidence_receipt_content_id_canonicalization_and_support_sha_are_instrumentation_overhead"
    ] is True
    assert document[
        "semantic_hash_counter_counts_only_exact_operation_manifest_labels"
    ] is True


def test_event_pair_claim_is_limited_to_exact_registered_fallible_sites() -> None:
    grammar = frozen().to_document()["event_grammar"]
    assert grammar["fallible_paired_operation_count"] == 307
    assert grammar["fallible_paired_operation_scope"] == (
        "EXACT_REGISTERED_IO_SEMANTIC_HASH_INTEGRITY_PROTOCOL_PROCESS_"
        "AND_SUBJECT_WRITE_SITES"
    )
    assert grammar[
        "all_307_fallible_paired_operation_sites_require_durable_intent_ack_before_listed_operation"
    ] is True
    assert grammar[
        "mount_interval_operations_use_open_close_not_intent_outcome"
    ] is True
    assert grammar[
        "singleton_operations_are_post_effect_atomic_observations_without_intent_claim"
    ] is True
    assert grammar[
        "deterministic_local_parse_shape_and_subject_computation_emits_separate_ledger_event"
    ] is False
    assert grammar[
        "failure_between_registered_hooks_preserves_current_phase_typed_failure_and_exact_durable_prefix"
    ] is True
    assert grammar["failure_between_registered_hooks_can_claim_success"] is False
    assert grammar["unqualified_every_operation_intent_outcome_claim"] is False


def test_protocol_freezes_internal_durable_paths_and_no_resume_freshness() -> None:
    document = frozen().to_document()
    contract = document["durable_artifact_contract"]
    assert contract == protocol.durable_artifact_contract_v180r12r4()
    assert contract["events_directory_relative_path"].endswith("/EVENTS")
    assert contract["successful_event_file_count"] == 625
    assert contract["subject_temp_relative_path"].endswith(
        "/SUBJECT_RESULT.json.partial"
    )
    assert contract["subject_result_relative_path"].endswith("/SUBJECT_RESULT.json")
    assert contract["one_o_excl_canonical_event_file_per_sequence"] is True
    assert contract[
        "any_preexisting_blocker_in_corresponding_precreate_matrix_forbids_same_identity"
    ] is True
    assert contract["current_exact_o_excl_prerequisite_is_not_a_stale_blocker"] is True
    matrices = {
        row["stage"]: row for row in contract["freshness_stage_matrices"]
    }
    measurement_child = matrices["MEASUREMENT_ATTEMPT_PRECREATE"]
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH in (
        measurement_child["must_be_present_exact"]
    )
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH in (
        measurement_child["must_be_absent"]
    )
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH in (
        measurement_child["must_be_absent"]
    )
    verification_child = matrices["VERIFICATION_ATTEMPT_PRECREATE"]
    assert protocol.PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH in (
        verification_child["must_be_present_exact"]
    )
    assert protocol.PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH in (
        verification_child["must_be_absent"]
    )
    assert protocol.PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH in (
        verification_child["must_be_absent"]
    )
    assert protocol.PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH in (
        verification_child["must_be_present_exact"]
    )
    assert protocol.TERMINAL_RELATIVE_PATH in verification_child[
        "must_be_present_exact"
    ]
    for relative_path in (
        protocol.EVIDENCE_INVENTORY_RELATIVE_PATH,
        protocol.EXECUTION_CLOSURE_RELATIVE_PATH,
        protocol.OS_RECEIPT_RELATIVE_PATH,
        protocol.LEDGER_CLOSURE_RELATIVE_PATH,
    ):
        assert relative_path in verification_child["must_be_present_exact"]
    assert contract["retained_launcher_and_child_share_one_exact_launch_identity"] is True
    assert contract["child_rejects_same_target_launch_receipt_or_failure"] is True
    assert contract[
        "old_launch_failure_cannot_be_superseded_by_direct_child_invocation"
    ] is True
    assert contract["partial_event_subject_or_receipt_state_is_preserved_on_failure"] is True
    assert contract["resume_from_partial_state_forbidden"] is True
    assert document[
        "attempt_record_o_excl_before_measurement_root_or_authorized_measured_subject_input_read"
    ] is True
    assert document[
        "preauthorization_predecessor_and_source_validation_reads_are_trusted_excluded_overhead"
    ] is True
    assert document["preauthorization_validation_reads_are_campaign_actual_measurement"] is False


def test_failure_observation_contract_mechanically_matches_runtime_and_stays_out_of_success() -> None:
    document = frozen().to_document()
    contract = document["failure_observation_contract"]
    assert contract == protocol.failure_observation_contract_v180r12r4()
    runtime_contract = supervisor.supervisor_contract_v180r12r4()
    assert (
        contract["failure_artifact_observation_row_cap"]
        == runtime_contract["failure_artifact_observation_row_cap"]
        == run_script.FAILURE_ARTIFACT_ROW_CAP
        == 4_112
    )
    assert (
        contract["failure_artifact_metadata_byte_cap"]
        == runtime_contract["failure_artifact_metadata_byte_cap"]
        == 2 * 1024 * 1024
    )
    assert (
        contract["failure_directory_entry_cap"]
        == runtime_contract["failure_directory_entry_cap"]
        == 4_096
    )
    assert (
        contract["failure_directory_entry_name_total_byte_cap"]
        == runtime_contract["failure_directory_entry_name_total_byte_cap"]
        == 256 * 1024
    )
    assert (
        contract["failure_artifact_streaming_hash_byte_cap"]
        == runtime_contract["failure_artifact_stream_hash_byte_cap"]
        == run_script.FAILURE_ARTIFACT_HASH_BYTE_CAP
        == protocol.MAX_LEDGER_BYTE_COUNT + protocol.MAX_EVENT_BYTE_COUNT
    )
    expected_rows = tuple(sorted(run_script.FAILURE_ARTIFACT_FIXED_PATH_KINDS))
    assert protocol.FAILURE_PROGRESS_PATH_KIND_ROWS == expected_rows
    assert protocol.FAILURE_PROGRESS_PATH_KIND_ROWS == (
        supervisor.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
    )
    assert contract["fixed_progress_path_kind_rows"] == [
        {"relative_path": path, "kind": kind} for path, kind in expected_rows
    ]
    assert contract["fixed_progress_path_count"] == 15
    assert contract["partial_artifact_observation_boundary"] == (
        supervisor.FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
    ) == "IMMEDIATELY_BEFORE_FAILURE_WRITE"
    assert contract["fixed_progress_rows_are_exactly_required"] is True
    assert contract[
        "additional_rows_are_exact_events_directory_direct_entries_only"
    ] is True
    assert contract[
        "failure_path_observation_is_absent_before_failure_o_excl_write"
    ] is True

    artifacts = tuple(
        supervisor.FailureArtifactObservationV180R12R4(
            relative_path,
            kind,
            "ABSENT",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        for relative_path, kind in protocol.FAILURE_PROGRESS_PATH_KIND_ROWS
    )
    cgroup = supervisor.FailureCgroupObservationV180R12R4(
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
        "NOT_ATTEMPTED",
        (),
        tuple(
            supervisor.FailureCgroupNodeObservationV180R12R4(
                role,
                (
                    "/synthetic/MEASUREMENT_ROOT"
                    if role == "MEASUREMENT_ROOT"
                    else f"/synthetic/MEASUREMENT_ROOT/{role}"
                ),
                "ABSENT",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
            for role in protocol.FAILURE_CGROUP_NODE_ROLES
        ),
    )
    failure = supervisor.CampaignFailureStateV180R12R4(
        "1" * 64,
        "2" * 64,
        "3" * 64,
        supervisor.FailureCodeV180R12R4.PROTOCOL_FAILURE,
        supervisor.CampaignPhaseV180R12R4.ATTEMPT,
        None,
        None,
        0,
        "bounded failure",
        False,
        False,
        artifacts,
        cgroup,
    )
    assert set(artifacts[0].to_document()) == set(
        contract["failure_artifact_observation_fields"]
    )
    assert set(cgroup.to_document()) == set(
        contract["failure_cgroup_observation_fields"]
    )
    assert set(failure.to_document()) == set(contract["failure_state_fields"])
    assert failure.to_document()["cgroup_topology_conformance_diagnostic"] is None
    assert "cgroup_topology_conformance_diagnostic" in (
        contract["failure_state_fields"]
    )
    assert supervisor.FAILURE_ARTIFACT_OBSERVATION_KEYS == set(
        contract["failure_artifact_observation_fields"]
    )
    assert supervisor.FAILURE_CGROUP_OBSERVATION_KEYS == set(
        contract["failure_cgroup_observation_fields"]
    )
    assert supervisor.FAILURE_CGROUP_NODE_OBSERVATION_KEYS == set(
        contract["failure_cgroup_node_observation_fields"]
    ) == set(protocol.FAILURE_CGROUP_NODE_OBSERVATION_FIELDS)
    assert contract["failure_cgroup_node_roles"] == list(
        protocol.FAILURE_CGROUP_NODE_ROLES
    ) == ["MEASUREMENT_ROOT", "SUPERVISOR", "WORKER"]
    assert contract["failure_cgroup_node_states"] == list(
        protocol.FAILURE_CGROUP_NODE_STATES
    ) == ["ABSENT", "LINKED_OR_NONDIR", "PRESENT", "READ_ERROR"]
    assert contract[
        "failure_directory_entry_name_worst_case_json_escape_factor"
    ] == 6
    assert contract[
        "failure_directory_entry_name_worst_case_escaped_bytes_at_cap"
    ] == 1_572_864
    assert contract[
        "failure_worst_case_names_plus_bounded_metadata_fit_emergency_reserve"
    ] is True
    assert supervisor.FAILURE_STATE_FIELD_KEYS == set(
        contract["failure_state_fields"]
    )
    assert contract["success_evidence_inventory_document_count"] == 328
    assert contract["failure_observations_in_success_evidence_inventory"] is False
    assert contract["failure_artifact_observations_are_campaign_success_authority"] is False
    assert contract["failure_cgroup_observation_is_campaign_success_receipt"] is False

    assert protocol.VERIFICATION_FAILURE_SCHEMA == (
        verify_script.VERIFICATION_FAILURE_SCHEMA
    )
    assert frozenset(protocol.VERIFICATION_FAILURE_FIELDS) == (
        verify_script.VERIFICATION_FAILURE_FIELDS
    )
    assert protocol.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS == (
        verify_script.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
    )
    assert contract["verification_failure_artifact_observation_row_count"] == (
        verify_script.VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROW_COUNT
    ) == 9
    assert contract["verification_failure_observation_boundary"] == (
        verify_script.VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
    ) == "IMMEDIATELY_BEFORE_FAILURE_WRITE"
    assert contract["verification_failure_observation_stream_chunk_bytes"] == (
        verify_script.VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
    ) == 65_536
    assert contract["verification_failure_directory_entry_count_cap"] == (
        verify_script.VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP
    ) == 4_096
    assert contract["verification_failure_directory_name_total_byte_cap"] == (
        verify_script.VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
    ) == 262_144
    assert contract[
        "verification_failure_directory_name_worst_case_json_escape_factor"
    ] == 6
    assert contract[
        "verification_failure_directory_name_worst_case_escaped_bytes_at_cap"
    ] == 1_572_864
    assert contract[
        "verification_failure_worst_case_names_plus_bounded_metadata_fit_emergency_reserve"
    ] is True
    assert contract["verification_failure_watchdog_cleanup_fields"] == sorted(
        verify_script._WATCHDOG_CLEANUP_FIELDS
    )
    assert contract["verification_failure_watchdog_secondary_fields"] == sorted(
        verify_script._WATCHDOG_SECONDARY_FIELDS
    )
    assert contract["verification_failure_watchdog_secondary_observation_cap"] == 3
    assert contract["verification_failure_self_path_absent_at_observation_boundary"] is True
    assert contract["verification_failure_is_campaign_success_authority"] is False


def test_failure_observation_contract_rejects_runtime_cap_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = supervisor.supervisor_contract_v180r12r4

    def drifted() -> dict:
        value = original()
        value["failure_artifact_observation_row_cap"] += 1
        return value

    monkeypatch.setattr(supervisor, "supervisor_contract_v180r12r4", drifted)
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="runtime failure observation contract changed",
    ):
        protocol.failure_observation_contract_v180r12r4()


def test_success_durable_artifact_contract_mechanically_matches_producers() -> None:
    contract = protocol.success_durable_artifact_contract_v180r12r4()
    assert contract["finalizer_mapping_order"] == list(
        finalizer.SUCCESS_ARTIFACT_ORDER
    )
    assert protocol.SUCCESS_ARTIFACT_SCHEMA_ROWS == (
        finalizer.SUCCESS_ARTIFACT_SCHEMA_ROWS
    )
    assert set(protocol.EVIDENCE_INVENTORY_BUNDLE_FIELDS) == (
        finalizer.EVIDENCE_INVENTORY_BUNDLE_FIELDS
    )
    assert set(protocol.OS_RECEIPT_BUNDLE_FIELDS) == (
        finalizer.OS_RECEIPT_BUNDLE_FIELDS
    )
    assert set(protocol.TERMINAL_FIELDS) == finalizer.TERMINAL_FIELDS
    assert contract["producer_write_order"] == [
        "EVIDENCE_INVENTORY",
        "EXECUTION_CLOSURE",
        "OS_RECEIPT",
        "LEDGER_CLOSURE",
        "TERMINAL",
    ]
    rows = {row["artifact_name"]: row for row in contract["artifact_rows"]}
    assert {name: row["byte_cap"] for name, row in rows.items()} == {
        "EVIDENCE_INVENTORY": 64 * 1024 * 1024,
        "EXECUTION_CLOSURE": 1 * 1024 * 1024,
        "OS_RECEIPT": 16 * 1024 * 1024,
        "LEDGER_CLOSURE": 64 * 1024 * 1024,
    }
    assert all(row["required_mode"] == "0400" for row in rows.values())
    execution = next(
        row
        for _name, schema, _identity, row in ledger.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
        if schema == protocol.EXECUTION_CLOSURE_SCHEMA
    )
    assert set(rows["EXECUTION_CLOSURE"]["exact_field_keyset"]) == execution

    tree = ast.parse(Path(ledger.__file__).read_text(encoding="utf-8"))
    ledger_payload_keys: set[str] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "_payload":
            continue
        for returned in ast.walk(node):
            if not isinstance(returned, ast.Return) or not isinstance(
                returned.value, ast.Dict
            ):
                continue
            keys = {
                key.value
                for key in returned.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if protocol.LEDGER_CLOSURE_SCHEMA in ast.unparse(returned.value):
                ledger_payload_keys = keys
    assert ledger_payload_keys is not None
    assert set(rows["LEDGER_CLOSURE"]["exact_field_keyset"]) == (
        ledger_payload_keys | {"campaign_ledger_closure_id"}
    )


def test_success_durable_artifact_contract_rejects_producer_keyset_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        finalizer,
        "EVIDENCE_INVENTORY_BUNDLE_FIELDS",
        finalizer.EVIDENCE_INVENTORY_BUNDLE_FIELDS | {"foreign"},
    )
    with pytest.raises(
        protocol.CampaignMeasurementProtocolV180R12R4Error,
        match="success durable artifact producer contract changed",
    ):
        protocol.success_durable_artifact_contract_v180r12r4()
