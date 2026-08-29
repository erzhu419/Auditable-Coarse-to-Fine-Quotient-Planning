"""Outcome-free V180r12r4 campaign-measurement protocol scaffold.

The protocol measures a fresh, producer-free replay successor over the exact
retained V180r12r2 terminal and verification.  It does not retrospectively
turn V180r12r2 structural declarations into observations, and it never runs
the V180r12r2 producer or verifier.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r4e as evidence_domains
from acfqp import (
    construction_k7_campaign_measurement_finalizer_v180r12r4 as finalizer_contract,
)
from acfqp import construction_k7_campaign_measurement_ledger_v180r12r4 as ledger_contract
from acfqp import (
    construction_k7_campaign_measurement_supervisor_v180r12r4 as supervisor_contract,
)
from acfqp import construction_k7_campaign_measurement_worker_v180r12r4 as worker_contract
from acfqp import (
    construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2
    as predecessor_evidence,
)
from acfqp import (
    construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3
    as failed_dispatch_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3r1
    as failed_external_replay_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r3r2
    as failed_scientific_birth_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r2
    as failed_ordinal8_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r4
    as failed_ordinal9_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r5
    as failed_ordinal10_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r6
    as failed_ordinal11_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r7
    as failed_ordinal12_predecessor,
)
from acfqp import (
    construction_k7_campaign_measurement_failure_freeze_v180r12r4r8
    as failed_ordinal13_predecessor,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ZERO_ID = "0" * 64
EXPECTED_PROTOCOL_ID = "9fc6ecbe63cdb65752d5bac6690903ab34ffc540abb3062b5ffde7a3695ebd49"
EXPECTED_CANONICAL_BYTE_COUNT = 492_573
EXPECTED_CANONICAL_SHA256 = "e32acda505c2e7dc98593290fe5fb60561e22df8481581a1f4e25846348f7cba"
EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID = (
    "441e52cd3721793a0541288196776aa214dd44b91f01e1822114b0e4442559f5"
)
LOGICAL_OCCURRENCE_ID = "a37770e56698857e162b2099766573ec5cabfc876145496f7d54756271d66599"
EXECUTION_NONCE = "7d4ebffb564caeb42550670bf06276f9ef7f456cfa5231acef56497f2bd62ea4"

CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA = domains.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA
CAMPAIGN_MEASUREMENT_ATTEMPT_DOMAIN = (
    domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
)
CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
)
CAMPAIGN_MEASUREMENT_ATTEMPT_IDENTITY_INPUT_FIELDS = (
    CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS[1:]
)

V180R12R2_EVIDENCE_COMMIT_ID = "1e6203e87fd7c7b2bde0c69264854c2bce6e374a"
V180R12R2_EVIDENCE_TREE_ID = "d00a2e53681308d861fb1532859ce678d3547c99"
V180R12R2_EVIDENCE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2.py"
)
V180R12R2_EVIDENCE_SOURCE_BYTE_COUNT = 38_850
V180R12R2_EVIDENCE_SOURCE_SHA256 = (
    "cbaea06c412ed4aea0859b2b839759b9eba035a5724a9e7d4ed54de08938f9da"
)
V180R12R2_AGGREGATION_PROTOCOL_ID = (
    "d15ec6d29ffbb4908e20cabfbbc98f3aa53ec4ad38d1d4681930c3306737c965"
)
V180R12R2_EXECUTION_AUTHORIZATION_ID = (
    "4a1424a1d27e97139acd10a50cac79ab012b8459be79b884d9adc3fd4b39e3a9"
)
V180R12R2_AUTHORIZATION_EVIDENCE_ID = (
    "19836faa57f88a429f321720108724e2deebe0b9b7aa8c3742dc0f97930c5319"
)
V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID = (
    "aba966326ff9e245d1758c65d8c3103614dd1a5a7be96b86e5eb2306bade15f0"
)
V180R12R2_VERIFICATION_ID = (
    "551881bb9bc6baa8dfaa112228f9160986b8106572d6f3f6c85af49434ec14ee"
)
V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3.py"
)
V180R12R3_FAILURE_FREEZE_SOURCE_BYTE_COUNT = 18_677
V180R12R3_FAILURE_FREEZE_SOURCE_SHA256 = (
    "93b52ecb67eb71c0965d37a8cf4194b5d21128798f6e5fc68a30947d8d74ded4"
)
V180R12R3_FAILURE_FREEZE_COMMIT_ID = (
    "ab06af5d4160cdf107a770d208876c06898b85b8"
)
V180R12R3_FAILURE_FREEZE_TREE_ID = (
    "a16cbb5dda71b5cd99a4060365478103b6ec20b8"
)
V180R12R3_FAILURE_FREEZE_GIT_BLOB_ID = (
    "2258fef806253f0c451ad60afd087c60f4269752"
)
V180R12R3_FAILED_CAMPAIGN_ATTEMPT_ID = (
    "457a889a690549ad5efaeb6d3f4799ec2a859068d93eac71730088f90889f967"
)
V180R12R3_FAILED_LAUNCH_ATTEMPT_ID = (
    "26ab9ac75aa950418708dcdacf674673f22609e87df055b0b1d8d3d96e9f1ee9"
)
V180R12R3_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT = 1_944
V180R12R3_FAILED_LAUNCH_ATTEMPT_SHA256 = (
    "72c0bae1bb862078de23a905d8a8c9c1742dfc4a1803d33c7eb6cef3b37cc64b"
)
V180R12R3_FAILED_LAUNCH_FAILURE_ID = (
    "d120a3e442d3079040e2d635e1e1808990070eece5be44ae84e73d83a52398e8"
)
V180R12R3_FAILED_LAUNCH_FAILURE_BYTE_COUNT = 8_957
V180R12R3_FAILED_LAUNCH_FAILURE_SHA256 = (
    "b6d14be33a05ad03b8c1f54a01a5c6190db8127adc9c2a77c79fb026a420c055"
)
V180R12R3_FAILED_CHILD_STDERR_BYTE_COUNT = 2_297
V180R12R3_FAILED_CHILD_STDERR_SHA256 = (
    "8e4b4ac3c42aa32771886128dde29260c1cffa40fa2939dd37c5d0675ec0683f"
)
V180R12R3_FAILED_MATERIALIZATION_TERMINAL_ID = (
    "344511707dfc5e623e95e868d282d03182c359e6160fe04542adc2eebff55b7a"
)
V180R12R3_FAILED_LAUNCH_RULE_ID = (
    "1700936d9145bfa7bcd858128548fd57f003ccf86a63dfdd43d6487f3aae4572"
)
V180R12R3_FAILED_RETAINED_FILE_FACT_ROWS = (
    (
        "v180r12r3_campaign_measurement_prelaunch_external_root.json",
        3_901,
        "c8452c16b6b5eb3e44ec04545526558d1a9eeff285a09fbfa9a6d4c91adef195",
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch/bootstrap.py",
        114_437,
        "6e74df6f0cdf296150bb413b82b01c658e2c3e577516e3f7707c9160a1680470",
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch/launcher.py",
        158_529,
        "25da098ab9ac26c57f79e2a97c363efbbcc69417dc2a668251c1a42d19096dd3",
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch/launch_manifest.json",
        46_288,
        "3d0fdcd2719168427bbb066ade57721c62262c9e1ce4752850f97a051314c314",
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch/MATERIALIZATION_TERMINAL.json",
        5_477,
        "208999305db03091ca744e3e0ab758647cdcc3c3aaf59be48acf854dabc24537",
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_ATTEMPT.json",
        V180R12R3_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT,
        V180R12R3_FAILED_LAUNCH_ATTEMPT_SHA256,
    ),
    (
        "v180r12r3_campaign_measurement_prelaunch_measurement_launch_failure.json",
        V180R12R3_FAILED_LAUNCH_FAILURE_BYTE_COUNT,
        V180R12R3_FAILED_LAUNCH_FAILURE_SHA256,
    ),
)
V180R12R3_FAILED_PRELAUNCH_EXACT_ENTRIES = (
    "MATERIALIZATION_TERMINAL.json",
    "MEASUREMENT_LAUNCH_ATTEMPT.json",
    "bootstrap.py",
    "launch_manifest.json",
    "launcher.py",
)
V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS = (
    "v180r12r3_campaign_measurement_prelaunch_failure.json",
    "v180r12r3_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_RECEIPT.json",
    "v180r12r3_campaign_measurement_prelaunch/VERIFICATION_LAUNCH_ATTEMPT.json",
    "v180r12r3_campaign_measurement_prelaunch/VERIFICATION_LAUNCH_RECEIPT.json",
    "v180r12r3_campaign_measurement_prelaunch_verification_launch_failure.json",
    "v180r12r3_campaign_measurement_cas",
    "v180r12r3_campaign_measurement_attempt.json",
    "v180r12r3_campaign_measurement",
    "v180r12r3_campaign_measurement_failure.json",
    "v180r12r3_campaign_measurement_verification.json",
    "v180r12r3_campaign_measurement_verification_failure.json",
    "v180r12r3_campaign_measurement_verification_replay.json",
)
V180R12R3_FAILED_MEASUREMENT_CGROUP_PARENT_PATH = (
    "/sys/fs/cgroup/user.slice/user-1000.slice/"
    "user@1000.service/app.slice"
)
V180R12R3_FAILED_MEASUREMENT_CGROUP_ROOT_NAME = (
    f"v180r12r3-{V180R12R3_FAILED_CAMPAIGN_ATTEMPT_ID}"
)

V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_prelaunch_failure_freeze_v180r12r3r1.py"
)
V180R12R3R1_FAILURE_FREEZE_SOURCE_BYTE_COUNT = 19_731
V180R12R3R1_FAILURE_FREEZE_SOURCE_SHA256 = (
    "3e7d34319755523d233fbe275df5d49a1aae172da1b5126f7d77b42ef0bc4adf"
)
V180R12R3R1_FAILURE_FREEZE_COMMIT_ID = (
    "4f8d92c208949758fcb98242f1e485d84520d4d1"
)
V180R12R3R1_FAILURE_FREEZE_TREE_ID = (
    "c8f4618edb8ff105d6fda1c7a23f54882046bb67"
)
V180R12R3R1_FAILURE_FREEZE_GIT_BLOB_ID = (
    "bef5ffc073c2e57c72d6bd7256a811800d49b1e5"
)
V180R12R3R1_FAILED_CAMPAIGN_ATTEMPT_ID = (
    "cbffcb66d23630ef46fa014f9467d3ac3054b39dde32ec0b9de22bba41078040"
)
V180R12R3R1_FAILED_LAUNCH_ATTEMPT_ID = (
    "eac1fc0f3ca572a736deaf9292101a1835a04ba5176c23e6b2bcceadc26b53c9"
)
V180R12R3R1_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT = 1_956
V180R12R3R1_FAILED_LAUNCH_ATTEMPT_SHA256 = (
    "416dc788bf4406b15c5cd82ad627f707420d3c24c51c850efd13f8ca74905558"
)
V180R12R3R1_FAILED_LAUNCH_FAILURE_ID = (
    "c2b957cf8556560696da92b959706bb7a74b2915df3776c6c28c65a266c1be60"
)
V180R12R3R1_FAILED_LAUNCH_FAILURE_BYTE_COUNT = 9_307
V180R12R3R1_FAILED_LAUNCH_FAILURE_SHA256 = (
    "74c6fe36e51ec703abfb3fc6e3d9f88e4f8644ccc0640892d9bef58da4473ff0"
)
V180R12R3R1_FAILED_CHILD_STDERR_BYTE_COUNT = 2_467
V180R12R3R1_FAILED_CHILD_STDERR_SHA256 = (
    "22d64a9a2df0b37a4780726f1b48e1cb41c376810d05200ffb5f2071f6ce833d"
)
V180R12R3R1_FAILED_MATERIALIZATION_TERMINAL_ID = (
    "8fe982f053c1a2577310f4452881ba4bdb9f9f95758c50c520a3a0a37c17ec11"
)
V180R12R3R1_FAILED_LAUNCH_RULE_ID = (
    "7d337317b583520daeb335ff57e2b7814390472fa639d44a0974e0b3dab2c214"
)
V180R12R3R1_FAILED_RETAINED_FILE_FACT_ROWS = (
    (
        "v180r12r3r1_campaign_measurement_prelaunch_external_root.json",
        3_919,
        "08dbcc07fee57acd48c5a419d4f73a9d4eaec37758ef8f8b3c0076e73dd8e1f0",
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch/bootstrap.py",
        119_050,
        "0c9d85bce72b7abf2199e1b7aca21a7febb44c5a81b64908d04e9c7fde1b08c7",
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch/launcher.py",
        160_494,
        "a50ab9b13f98442fe8695988c581a6be0e3bd9a19dfddfd4e27f03f24728325c",
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch/launch_manifest.json",
        48_295,
        "e8843ae4b8194b65179de4ccb59133fa6791e6ad8817de28699349c6645e9766",
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch/MATERIALIZATION_TERMINAL.json",
        5_503,
        "ceb58f7b09f1a1ac638f0f3e44c7919d1f0a3fde4a8b5172ee8d719755235cb6",
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_ATTEMPT.json",
        V180R12R3R1_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT,
        V180R12R3R1_FAILED_LAUNCH_ATTEMPT_SHA256,
    ),
    (
        "v180r12r3r1_campaign_measurement_prelaunch_measurement_launch_failure.json",
        V180R12R3R1_FAILED_LAUNCH_FAILURE_BYTE_COUNT,
        V180R12R3R1_FAILED_LAUNCH_FAILURE_SHA256,
    ),
)
V180R12R3R1_FAILED_PRELAUNCH_EXACT_ENTRIES = (
    "MATERIALIZATION_TERMINAL.json",
    "MEASUREMENT_LAUNCH_ATTEMPT.json",
    "bootstrap.py",
    "launch_manifest.json",
    "launcher.py",
)
V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS = (
    "v180r12r3r1_campaign_measurement_prelaunch_failure.json",
    "v180r12r3r1_campaign_measurement_prelaunch/MEASUREMENT_LAUNCH_RECEIPT.json",
    "v180r12r3r1_campaign_measurement_prelaunch/VERIFICATION_LAUNCH_ATTEMPT.json",
    "v180r12r3r1_campaign_measurement_prelaunch/VERIFICATION_LAUNCH_RECEIPT.json",
    "v180r12r3r1_campaign_measurement_prelaunch_verification_launch_failure.json",
    "v180r12r3r1_campaign_measurement_cas",
    "v180r12r3r1_campaign_measurement_attempt.json",
    "v180r12r3r1_campaign_measurement",
    "v180r12r3r1_campaign_measurement_failure.json",
    "v180r12r3r1_campaign_measurement_verification.json",
    "v180r12r3r1_campaign_measurement_verification_failure.json",
    "v180r12r3r1_campaign_measurement_verification_replay.json",
)
V180R12R3R1_FAILED_MEASUREMENT_CGROUP_PARENT_PATH = (
    "/sys/fs/cgroup/user.slice/user-1000.slice/"
    "user@1000.service/app.slice"
)
V180R12R3R1_FAILED_MEASUREMENT_CGROUP_ROOT_NAME = (
    f"v180r12r3r1-{V180R12R3R1_FAILED_CAMPAIGN_ATTEMPT_ID}"
)

V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r3r2.py"
)
V180R12R3R2_FAILURE_FREEZE_SOURCE_BYTE_COUNT = 47_108
V180R12R3R2_FAILURE_FREEZE_SOURCE_SHA256 = (
    "48704c3c2217b47e59a023843d3cc3671d8d810c18729c63faa1b48c3f99ce3b"
)
V180R12R3R2_FAILURE_FREEZE_COMMIT_ID = (
    "f4bb4981f15a602d156e7ec88338a880c7a5a167"
)
V180R12R3R2_FAILURE_FREEZE_TREE_ID = (
    "521d6b3d39ec944a361ce801de8bde8beca29f1c"
)
V180R12R3R2_FAILURE_FREEZE_GIT_BLOB_ID = (
    "87bc7bfa34772cfcb8b75ab6d627861473bbf904"
)
V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_ID = (
    "3de63370a50ba83d42ab45d5dc4a22fac9799bc2ab6bd1816d667e009b85292e"
)
V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_RECORD_ID = (
    "6acbbba7d8754550f3f474df21433b6a41b1166847619559064f912d8f96fb2c"
)
V180R12R3R2_FAILED_LAUNCH_ATTEMPT_ID = (
    "4e0a7ab35b5d1d8f0bd13a2c19d474d7fae871baf767f15e821f2fcf734e3c68"
)
V180R12R3R2_FAILED_LAUNCH_FAILURE_ID = (
    "594c08d5932d0f7188b232485f6e9a08a0d4b041aa2c9f84aa0095d2b1591935"
)
V180R12R3R2_FAILED_FAILURE_STATE_ID = (
    "1ff2239cd5ca71f588149e987cded8fe5b8dbf75e7d7098435fda0955fffd09d"
)
V180R12R3R2_FAILED_EVENT_IDS = (
    "f7cb99e26ef03caaead41d987d031ad7636fe81216a34f2c4c36591abb6f0282",
    "356b136e203aa884f4a40352a4e62c20f9c92d855279e9396666c77485843c9e",
)
V180R12R3R2_FAILURE_CLAIM_BOUNDARY = (
    "PERMISSION_DENIED_DURING_SUPERVISOR_BIRTH_OR_CLONE_PATH;"
    "EXACT_FAILING_SYSCALL_UNPROVEN"
)
V180R12R3R2_FAILED_MEASUREMENT_CGROUP_PARENT_PATH = (
    "/sys/fs/cgroup/user.slice/user-1000.slice/"
    "user@1000.service/app.slice"
)
V180R12R3R2_FAILED_MEASUREMENT_CGROUP_ROOT_NAME = (
    f"v180r12r3r2-{V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_ID}"
)
V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r2.py"
)
V180R12R4R2_FAILED_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal8_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R2_FAILED_CAMPAIGN_FAILURE_ID = (
    failed_ordinal8_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
)
V180R12R4R2_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal8_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R2_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal8_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r4.py"
)
V180R12R4R4_FAILED_PREDECESSOR_FREEZE_ID = (
    failed_ordinal9_predecessor.ORDINAL9_FAILURE_FREEZE_ID
)
V180R12R4R4_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal9_predecessor.EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R4_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal9_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R4_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal9_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r5.py"
)
V180R12R4R5_FAILED_PREDECESSOR_FREEZE_ID = (
    failed_ordinal10_predecessor.ORDINAL10_FAILURE_FREEZE_ID
)
V180R12R4R5_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal10_predecessor.EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R5_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal10_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R5_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal10_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r6.py"
)
V180R12R4R6_FAILED_PREDECESSOR_FREEZE_ID = (
    failed_ordinal11_predecessor.ORDINAL11_FAILURE_FREEZE_ID
)
V180R12R4R6_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal11_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R6_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal11_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R6_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal11_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r7.py"
)
V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID = (
    failed_ordinal12_predecessor.ORDINAL12_FAILURE_FREEZE_ID
)
V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal12_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R7_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal12_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R7_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal12_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH = (
    "src/acfqp/"
    "construction_k7_campaign_measurement_failure_freeze_v180r12r4r8.py"
)
V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID = (
    failed_ordinal13_predecessor.ORDINAL13_FAILURE_FREEZE_ID
)
V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID = (
    failed_ordinal13_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
)
V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID = (
    failed_ordinal13_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
)
V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID = (
    failed_ordinal13_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
)
V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID = (
    failed_ordinal13_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
)
V180R12R3R2_REPAIR_SCOPE = (
    "OUTER_OBSERVER_DELEGATED_SOURCE_CGROUP_PLACEMENT_AND_ATOMIC_BIRTH_"
    "PREFLIGHT_ONLY"
)
V180R12R4R3_REPAIR_SCOPE = (
    "CGROUP_CONTROLLER_SEMANTICS_AND_TYPED_DIAGNOSTIC_SUCCESSOR"
)
V180R12R4R4_REPAIR_SCOPE = failed_ordinal9_predecessor.REPAIR_SCOPE
V180R12R4R5_REPAIR_SCOPE = failed_ordinal10_predecessor.REPAIR_SCOPE
V180R12R4R6_REPAIR_SCOPE = failed_ordinal11_predecessor.REPAIR_SCOPE
V180R12R4R7_REPAIR_SCOPE = failed_ordinal12_predecessor.REPAIR_SCOPE
V180R12R4R8_REPAIR_SCOPE = failed_ordinal13_predecessor.REPAIR_SCOPE
V180R12R4_REPAIR_SCOPE = V180R12R4R8_REPAIR_SCOPE

PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN = (
    "acfqp:construction-k7-production-transient-service-token:v180r12r4"
)
PRODUCTION_TRANSIENT_SERVICE_TOKEN_INPUT_FIELDS = (
    "failed_predecessor_freeze_id",
    "failed_inner_launch_failure_id",
    "failed_outer_service_failure_id",
    "repair_scope",
    "purpose",
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT = {
    "failed_predecessor_freeze_id": V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID,
    "failed_inner_launch_failure_id": (
        V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID
    ),
    "failed_outer_service_failure_id": (
        V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID
    ),
    "repair_scope": V180R12R4_REPAIR_SCOPE,
    "purpose": "MEASUREMENT",
}
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN = hashlib.sha256(
    PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
    + b"\x00"
    + canonical_json_bytes(PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT)
).hexdigest()
EXPECTED_PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN = (
    "1ba5304a7d653a3805fdca4754eeb7ff2feaa63794c6b866f47adda85160668d"
)
PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-measurement-"
    + PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN
    + ".service"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT = {
    **PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT,
    "purpose": "VERIFICATION",
}
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN = hashlib.sha256(
    PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN.encode("ascii")
    + b"\x00"
    + canonical_json_bytes(PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT)
).hexdigest()
EXPECTED_PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN = (
    "14e3fead4dab312dd06026196922d455600e970d5de64624e3d47b66525c0221"
)
PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME = (
    "acfqp-v180r12r4-verification-"
    + PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN
    + ".service"
)
PRODUCTION_TRANSIENT_SERVICE_ROWS = {
    "measurement": (
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT,
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
        PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME,
    ),
    "verification": (
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT,
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
        PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME,
    ),
}
PRODUCTION_TRANSIENT_SERVICE_SLICE = "app.slice"
PRODUCTION_SYSTEMD_RUN_EXECUTABLE = "/usr/bin/systemd-run"
PRODUCTION_ENV_EXECUTABLE = "/usr/bin/env"
PRODUCTION_MATERIALIZATION_TERMINAL_SHA256_TEMPLATE = (
    "__V180R12R4_MATERIALIZATION_TERMINAL_SHA256__"
)
ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA = (
    "acfqp.v180r12r4_atomic_cgroup_birth_preflight_receipt_interface.v1"
)
ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_FIELDS = (
    "schema",
    "receipt_id",
    "receipt_byte_count",
    "receipt_sha256",
    "authority_accepted",
    "production_launch_authorized",
)
ZERO_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE = {
    "schema": ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA,
    "receipt_id": ZERO_ID,
    "receipt_byte_count": 0,
    "receipt_sha256": ZERO_ID,
    "authority_accepted": False,
    "production_launch_authorized": False,
}
PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA = (
    "acfqp.v180r12r4_production_systemd_service_invocation.v1"
)
PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS = (
    "schema",
    "token_domain",
    "target",
    "token_input",
    "token",
    "unit_name",
    "unit_kind",
    "slice",
    "service_type",
    "delegate",
    "umask",
    "launcher_command",
    "systemd_run_argv",
)
PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t1.v1"
)
PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS = (
    "schema",
    "target",
    "token",
    "unit_name",
    "slice",
    "source_membership",
    "expected_source_membership",
    "self_pid",
    "self_pid_in_source_cgroup_procs",
    "cgroup_namespace_inode",
    "delegated_parent_fd_fact",
    "cgroup2_mount_fd_fact",
    "source_service_fd_fact",
    "nearest_common_ancestor_path",
    "nearest_common_ancestor_is_app_slice",
    "parent_cgroup_procs_o_wronly_openable",
    "planned_measurement_root_observation",
    "planned_measurement_root_absent",
    "t1_complete_before_child_popen",
)
PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t2.v2"
)
PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS = (
    "schema",
    "boundary",
    "target",
    "token",
    "unit_name",
    "source_membership",
    "expected_source_membership",
    "self_pid",
    "self_pid_in_source_cgroup_procs",
    "parent_pid",
    "parent_pid_in_source_cgroup_procs",
    "source_service_fd",
    "source_service_device",
    "source_service_inode",
    "cgroup_namespace_inode",
    "nearest_common_ancestor_path",
    "nearest_common_ancestor_is_app_slice",
    "parent_cgroup_procs_o_wronly_openable",
    "planned_measurement_root_state",
    "scientific_progress_present_paths",
    "scientific_progress_absent",
)
PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA = (
    "acfqp.v180r12r4_production_runtime_placement_t3.v2"
)
PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS = (
    *PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS,
    "measurement_root_device",
    "measurement_root_inode",
    "supervisor_leaf_device",
    "supervisor_leaf_inode",
    "worker_leaf_device",
    "worker_leaf_inode",
    "target_cgroup_role",
    "target_cgroup_fd",
    "target_cgroup_device",
    "target_cgroup_inode",
    "target_cgroup_path",
    "target_membership_path",
    "root_empty_before_birth",
    "supervisor_leaf_empty_before_birth",
    "worker_leaf_empty_before_birth",
    "programmed_limits_revalidated",
)
PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS = (
    "schema",
    "target",
    "token",
    "unit_name",
    "before_getrandom",
    "immediately_before_clone3",
    "stable_across_boundaries",
)
TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA = (
    supervisor_contract.TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA
)
TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_FIELDS = (
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
TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCOPES = (
    "PARENT_AND_CHILD_TOPOLOGY",
    "T1_T2_PLACEMENT",
    "T3_CHECKPOINT_CONFORMANCE",
)
TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_PROPERTY_SNAPSHOT_FIELDS = (
    "unit_ownership",
    "parent_delegation",
    "measurement_topology",
    "production_runtime_placement_t3",
)
TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_UNIT_OWNERSHIP_FIELDS = (
    "production_runtime_placement_t1",
    "production_runtime_placement_t2",
)
REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_revalidated_external_measurement_context.v1"
)
TYPED_LAUNCH_FAILURE_SUBSTAGES = (
    "T3_BEFORE_GETRANDOM",
    "GETRANDOM",
    "SOCKETPAIR",
    "SOCKET_BUFFER_CONFIGURATION",
    "SUPERVISOR_ARGV_AND_CONTEXT_BUILD",
    "KEY_MEMFD_CREATE",
    "CONTEXT_MEMFD_CREATE",
    "TARGET_CGROUP_FSTAT",
    "T3_IMMEDIATELY_BEFORE_CLONE3",
    "EXEC_STATUS_PIPE",
    "CLONE3",
    "CHILD_PREEXEC",
    "PIDFD_ACQUISITION",
    "PROC_CHILD_IDENTITY_OBSERVATION",
    "BIRTH_RECEIPT_CONSTRUCTION",
    "AUTHENTICATED_CHANNEL_CONSTRUCTION",
)
TYPED_LAUNCH_FAILURE_FIELDS = (
    "launch_substage",
    "launch_errno",
    "launch_child_created",
    "launch_pidfd_acquired",
    "launch_exec_observed",
)

SOURCE_BOUND_RUNNER_TARGET_ORDER = (
    "measurement",
    "verification",
    "supervisor",
    "worker",
)
SOURCE_BOUND_RUNNER_MODULE_ROWS = tuple(
    (
        target,
        f"_acfqp_v180r12r4_precompiled_runner_{target}",
    )
    for target in SOURCE_BOUND_RUNNER_TARGET_ORDER
)
SOURCE_BOUND_RUNNER_MODULE_METADATA_FIELDS = (
    "__name__",
    "__file__",
    "__package__",
    "__cached__",
    "__loader__",
    "__spec__",
)

CAMPAIGN_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)
CAMPAIGN_PATH_COUNT = 9
CAMPAIGN_COUNTER_RECORD_COUNT_BEFORE_EXECUTION = 0
CAMPAIGN_WORK_VECTOR_COUNT_BEFORE_EXECUTION = 0
CAMPAIGN_COMPARISON_VECTOR_COUNT_BEFORE_EXECUTION = 0
CAMPAIGN_PROJECTION_PROOF_COUNT_BEFORE_EXECUTION = 0
CAMPAIGN_NATIVE_ZERO_ATTESTATION_COUNT_BEFORE_EXECUTION = 0
SUCCESS_CAMPAIGN_COUNTER_RECORD_COUNT = 9
SUCCESS_CAMPAIGN_WORK_VECTOR_COUNT = 1
SUCCESS_CAMPAIGN_COMPARISON_VECTOR_COUNT = 1
SUCCESS_CAMPAIGN_PROJECTION_PROOF_COUNT = 1
SUCCESS_CAMPAIGN_NATIVE_ZERO_ATTESTATION_COUNT = 1
CAMPAIGN_SCOPE_KIND = "TEN_TERMINAL_AGGREGATION_MEASURED_REPLAY_SUCCESSOR"
WORK_SCOPE_KIND = "ROUTE_FREE_MEASURED_REPLAY_SUCCESSOR"
COUNTER_REGISTRY_REFERENCE = "acfqp_counter_registry_v6"
NATIVE_ZERO_COMPARISON_AXIS = "kernel_transition_calls"

PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT = 90
PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT = 0
PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT = 9
SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT = 9
SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT = 99

SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES = (
    "EVIDENCE_RECEIPT_CANONICALIZATION",
    "EVIDENCE_RECEIPT_CONTENT_ID_ISSUANCE",
    "EVIDENCE_SUPPORT_DOCUMENT_CANONICALIZATION",
    "EVIDENCE_SUPPORT_DOCUMENT_CONTENT_ID_ISSUANCE",
    "EVIDENCE_AND_SUPPORT_SHA256_FIELDS",
    "IPC_FRAME_MAC_AND_TRANSPORT_DIGESTS",
    "JOURNAL_EVENT_CONTENT_IDS_AND_FILE_DIGESTS",
    "LEDGER_CHAIN_CONTENT_IDS_AND_ARTIFACT_DIGESTS",
    "PRELAUNCH_SOURCE_AND_ARTIFACT_DIGESTS",
)

PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT = 199_755
PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT = 2_752
PREDECESSOR_INPUT_TOTAL_BYTE_COUNT = 202_507
SUCCESS_STAGED_BYTE_COUNT = PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
SUCCESS_MOUNTED_BYTES_PEAK = PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
SUCCESS_READ_BYTES_FIXED_ADDEND = 2 * PREDECESSOR_INPUT_TOTAL_BYTE_COUNT

INNER_CONTENT_ID_OPERATION_SUFFIXES = (
    *(f"source_receipt.{index:02d}" for index in range(5)),
    *(f"route_component_chain_receipt.{index:02d}" for index in range(12)),
    *(f"terminal_receipt.{index:02d}" for index in range(10)),
    *(f"terminal_shared_resource_receipt.{index:03d}" for index in range(90)),
    *(f"terminal_shared_resource_receipt_set.{index:02d}" for index in range(10)),
    "v180r7r1_construction_axis_receipt",
    "campaign_scope_structural_boundary",
)
SEMANTIC_HASH_OPERATION_LABELS = (
    "hash.source_file_sha256.terminal",
    "hash.source_file_sha256.verification",
    "hash.staged_file_sha256.terminal",
    "hash.staged_file_sha256.verification",
    "hash.top_content_id.terminal",
    "hash.top_content_id.verification",
    *(f"hash.inner_content_id.{suffix}" for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES),
    "hash.subject_result_id",
    "hash.subject_readback_sha256",
)
INTEGRITY_CHECK_OPERATION_LABELS = (
    "integrity.stage_source.terminal.stable_read",
    "integrity.stage_source.verification.stable_read",
    "integrity.stage_source.terminal.sha256",
    "integrity.stage_source.verification.sha256",
    "integrity.stage_source.terminal.memfd_seals",
    "integrity.stage_source.verification.memfd_seals",
    "integrity.worker_staged.terminal.sha256",
    "integrity.worker_staged.verification.sha256",
    "integrity.worker_staged.terminal.canonical_json",
    "integrity.worker_staged.verification.canonical_json",
    "integrity.worker_staged.terminal.top_content_id",
    "integrity.worker_staged.verification.top_content_id",
    *(
        f"integrity.worker_inner_content_id.{suffix}"
        for suffix in INNER_CONTENT_ID_OPERATION_SUFFIXES
    ),
    "integrity.worker_inner_content_id.denominator_and_uniqueness",
    "integrity.worker_subject.canonical_json_and_content_id",
    "integrity.commit_subject.readback_size_and_sha256",
    "integrity.commit_subject.stable_mode_and_nlink",
)
PROTOCOL_CHECK_FAMILIES = (
    "TERMINAL_SCHEMA_AND_KEYSET",
    "VERIFICATION_SCHEMA_AND_KEYSET",
    "LINEAGE_IDS",
    "SOURCE_RECEIPT_ORDER",
    "ROUTE_COMPONENT_ORDER",
    "TERMINAL_RECEIPT_ORDER",
    "SHARED_SET_AND_RECEIPT_ORDER",
    "CONSTRUCTION_AXIS_SEPARATION",
    "STRUCTURAL_NINE_ZERO_ROUTE_FREE",
    "VERIFICATION_TERMINAL_BYTES_SHA_JOIN",
    "GLOBAL_DENOMINATORS",
    "PENDING_TO_PASS_TRANSITION",
    "FOUR_GATES_BLOCKER_AND_OFFICIAL",
    "SUCCESSOR_NONRETROACTIVITY_AND_IMPORT_BOUNDARY",
    "SUBJECT_SCHEMA_AND_KEYSET",
)
PROTOCOL_CHECK_OPERATION_LABELS = tuple(
    f"protocol.{family.lower()}" for family in PROTOCOL_CHECK_FAMILIES
)
SEMANTIC_HASH_OPERATION_FAMILIES = (
    ("SOURCE_SHA256", 2, "STAGE", "SUPERVISOR"),
    ("STAGED_SHA256", 2, "WORKER", "WORKER"),
    ("TOP_CONTENT_ID", 2, "WORKER", "WORKER"),
    ("INNER_CONTENT_ID", 129, "WORKER", "WORKER"),
    ("SUBJECT_CONTENT_ID", 1, "WORKER", "WORKER"),
    ("SUBJECT_READBACK_SHA256", 1, "COMMIT", "SUPERVISOR"),
)
INTEGRITY_CHECK_OPERATION_FAMILIES = (
    ("STAGE_STABLE_INPUT", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SHA_MATCH", 2, "STAGE", "SUPERVISOR"),
    ("STAGE_SEAL_SET", 2, "STAGE", "SUPERVISOR"),
    ("WORKER_STAGED_SHA", 2, "WORKER", "WORKER"),
    ("WORKER_CANONICAL_JSON", 2, "WORKER", "WORKER"),
    ("WORKER_TOP_ID_MATCH", 2, "WORKER", "WORKER"),
    ("WORKER_INNER_ID_MATCH", 129, "WORKER", "WORKER"),
    ("WORKER_INNER_COUNT_AND_UNIQUENESS", 1, "WORKER", "WORKER"),
    ("WORKER_SUBJECT_CANONICAL_AND_ID", 1, "WORKER", "WORKER"),
    ("COMMIT_READBACK_SIZE_AND_SHA", 1, "COMMIT", "SUPERVISOR"),
    ("COMMIT_STABLE_MODE_AND_NLINK", 1, "COMMIT", "SUPERVISOR"),
)
SEMANTIC_HASH_OPERATION_COUNT = 137
INTEGRITY_CHECK_OPERATION_COUNT = 145
PROTOCOL_CHECK_OPERATION_COUNT = 15

PHASE_ORDER = (
    "ATTEMPT",
    "STAGE",
    "WORKER",
    "COMMIT",
    "WINDOW_CLOSE",
    "OS_OBSERVE",
    "LEDGER_CLOSE",
)
EVENT_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "sequence",
    "phase",
    "actor_role",
    "operation_id",
    "event_kind",
    "previous_event_id",
    "monotonic_ns",
    "payload",
    "event_id",
)
EVENT_PAYLOAD_FIELDS = (
    "evidence_id",
    "outcome_code",
    "measured_value",
    "auxiliary_values",
)
AUXILIARY_VALUE_FIELDS = ("name", "value")
OUTCOME_CODES = (
    "INTENT",
    "SUCCESS",
    "PASS",
    "FAIL",
    "ERROR",
    "OPEN",
    "CLOSED",
    "OBSERVED",
    "COMMITTED",
)
SUCCESS_FORBIDDEN_OUTCOME_CODES = ("FAIL", "ERROR")
REQUIRED_EVENT_KINDS = (
    "ATTEMPT_OPEN",
    "INPUT_READ_INTENT",
    "INPUT_READ_OUTCOME",
    "STAGE_WRITE_INTENT",
    "STAGE_WRITE_OUTCOME",
    "MOUNT_VISIBILITY_OPEN",
    "MOUNT_VISIBILITY_CLOSE",
    "SEMANTIC_HASH_INTENT",
    "SEMANTIC_HASH_OUTCOME",
    "INTEGRITY_CHECK_INTENT",
    "INTEGRITY_CHECK_OUTCOME",
    "PROTOCOL_CHECK_INTENT",
    "PROTOCOL_CHECK_OUTCOME",
    "PROCESS_BIRTH_INTENT",
    "PROCESS_BIRTH_OUTCOME",
    "PROCESS_REAP",
    "SUBJECT_WRITE_INTENT",
    "SUBJECT_WRITE_OUTCOME",
    "SUBJECT_COMMIT",
    "WINDOW_CLOSED",
    "CGROUP_OBSERVED",
    "LEDGER_CLOSED",
)
EVENT_KIND_PHASES = (
    ("ATTEMPT_OPEN", ("ATTEMPT",)),
    ("INPUT_READ_INTENT", ("STAGE", "WORKER", "COMMIT")),
    ("INPUT_READ_OUTCOME", ("STAGE", "WORKER", "COMMIT")),
    ("STAGE_WRITE_INTENT", ("STAGE",)),
    ("STAGE_WRITE_OUTCOME", ("STAGE",)),
    ("MOUNT_VISIBILITY_OPEN", ("STAGE",)),
    ("MOUNT_VISIBILITY_CLOSE", ("WINDOW_CLOSE",)),
    ("SEMANTIC_HASH_INTENT", ("STAGE", "WORKER", "COMMIT")),
    ("SEMANTIC_HASH_OUTCOME", ("STAGE", "WORKER", "COMMIT")),
    ("INTEGRITY_CHECK_INTENT", ("STAGE", "WORKER", "COMMIT")),
    ("INTEGRITY_CHECK_OUTCOME", ("STAGE", "WORKER", "COMMIT")),
    ("PROTOCOL_CHECK_INTENT", ("WORKER",)),
    ("PROTOCOL_CHECK_OUTCOME", ("WORKER",)),
    ("PROCESS_BIRTH_INTENT", ("STAGE", "WORKER")),
    ("PROCESS_BIRTH_OUTCOME", ("STAGE", "WORKER")),
    ("PROCESS_REAP", ("WORKER", "OS_OBSERVE")),
    ("SUBJECT_WRITE_INTENT", ("WORKER",)),
    ("SUBJECT_WRITE_OUTCOME", ("WORKER",)),
    ("SUBJECT_COMMIT", ("COMMIT",)),
    ("WINDOW_CLOSED", ("WINDOW_CLOSE",)),
    ("CGROUP_OBSERVED", ("OS_OBSERVE",)),
    ("LEDGER_CLOSED", ("LEDGER_CLOSE",)),
)
EVENT_KIND_ROLE_PHASES = (
    ("ATTEMPT_OPEN", (("OBSERVER", "ATTEMPT"),)),
    (
        "INPUT_READ_INTENT",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    (
        "INPUT_READ_OUTCOME",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    ("STAGE_WRITE_INTENT", (("SUPERVISOR", "STAGE"),)),
    ("STAGE_WRITE_OUTCOME", (("SUPERVISOR", "STAGE"),)),
    ("MOUNT_VISIBILITY_OPEN", (("SUPERVISOR", "STAGE"),)),
    ("MOUNT_VISIBILITY_CLOSE", (("SUPERVISOR", "WINDOW_CLOSE"),)),
    (
        "SEMANTIC_HASH_INTENT",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    (
        "SEMANTIC_HASH_OUTCOME",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    (
        "INTEGRITY_CHECK_INTENT",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    (
        "INTEGRITY_CHECK_OUTCOME",
        (("SUPERVISOR", "STAGE"), ("WORKER", "WORKER"), ("SUPERVISOR", "COMMIT")),
    ),
    ("PROTOCOL_CHECK_INTENT", (("WORKER", "WORKER"),)),
    ("PROTOCOL_CHECK_OUTCOME", (("WORKER", "WORKER"),)),
    (
        "PROCESS_BIRTH_INTENT",
        (("OBSERVER", "STAGE"), ("SUPERVISOR", "WORKER")),
    ),
    (
        "PROCESS_BIRTH_OUTCOME",
        (("OBSERVER", "STAGE"), ("SUPERVISOR", "WORKER")),
    ),
    (
        "PROCESS_REAP",
        (("SUPERVISOR", "WORKER"), ("OBSERVER", "OS_OBSERVE")),
    ),
    ("SUBJECT_WRITE_INTENT", (("WORKER", "WORKER"),)),
    ("SUBJECT_WRITE_OUTCOME", (("WORKER", "WORKER"),)),
    ("SUBJECT_COMMIT", (("SUPERVISOR", "COMMIT"),)),
    ("WINDOW_CLOSED", (("SUPERVISOR", "WINDOW_CLOSE"),)),
    ("CGROUP_OBSERVED", (("OBSERVER", "OS_OBSERVE"),)),
    ("LEDGER_CLOSED", (("OBSERVER", "LEDGER_CLOSE"),)),
)
SUCCESS_EVENT_CARDINALITIES = (
    ("ATTEMPT_OPEN", 1),
    ("INPUT_READ_INTENT", 5),
    ("INPUT_READ_OUTCOME", 5),
    ("STAGE_WRITE_INTENT", 2),
    ("STAGE_WRITE_OUTCOME", 2),
    ("MOUNT_VISIBILITY_OPEN", 2),
    ("MOUNT_VISIBILITY_CLOSE", 2),
    ("SEMANTIC_HASH_INTENT", SEMANTIC_HASH_OPERATION_COUNT),
    ("SEMANTIC_HASH_OUTCOME", SEMANTIC_HASH_OPERATION_COUNT),
    ("INTEGRITY_CHECK_INTENT", INTEGRITY_CHECK_OPERATION_COUNT),
    ("INTEGRITY_CHECK_OUTCOME", INTEGRITY_CHECK_OPERATION_COUNT),
    ("PROTOCOL_CHECK_INTENT", PROTOCOL_CHECK_OPERATION_COUNT),
    ("PROTOCOL_CHECK_OUTCOME", PROTOCOL_CHECK_OPERATION_COUNT),
    ("PROCESS_BIRTH_INTENT", 2),
    ("PROCESS_BIRTH_OUTCOME", 2),
    ("PROCESS_REAP", 2),
    ("SUBJECT_WRITE_INTENT", 1),
    ("SUBJECT_WRITE_OUTCOME", 1),
    ("SUBJECT_COMMIT", 1),
    ("WINDOW_CLOSED", 1),
    ("CGROUP_OBSERVED", 1),
    ("LEDGER_CLOSED", 1),
)
SUCCESS_MINIMUM_EVENT_COUNT = sum(value for _, value in SUCCESS_EVENT_CARDINALITIES)
SUCCESS_EXACT_EVENT_COUNT = SUCCESS_MINIMUM_EVENT_COUNT

INTENT_OUTCOME_PAIRS = (
    ("INPUT_READ_INTENT", "INPUT_READ_OUTCOME"),
    ("STAGE_WRITE_INTENT", "STAGE_WRITE_OUTCOME"),
    ("SEMANTIC_HASH_INTENT", "SEMANTIC_HASH_OUTCOME"),
    ("INTEGRITY_CHECK_INTENT", "INTEGRITY_CHECK_OUTCOME"),
    ("PROTOCOL_CHECK_INTENT", "PROTOCOL_CHECK_OUTCOME"),
    ("PROCESS_BIRTH_INTENT", "PROCESS_BIRTH_OUTCOME"),
    ("SUBJECT_WRITE_INTENT", "SUBJECT_WRITE_OUTCOME"),
)
CGROUP_ROLE_ORDER = ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
PROCESS_ROLE_ORDER = ("SUPERVISOR", "WORKER")
ACTOR_ROLES = ("OBSERVER", "SUPERVISOR", "WORKER")
SEMANTIC_RECEIPT_AUXILIARY_ROWS = (
    ("SEMANTIC_HASH", "observed_sha256", "LOWERCASE_64_HEX", 137),
    ("INTEGRITY_CHECK", "check_passed", "EXACT_TRUE", 145),
    ("PROTOCOL_CHECK", "check_passed", "EXACT_TRUE", 15),
)

# These are type/count preregistrations, never outcome documents or identities.
# The finalizer must materialize exactly one canonical document for each row
# occurrence and register it under the stated fresh V180r12r4e domain.
EVIDENCE_INVENTORY_ROWS = (
    (
        "CAMPAIGN_ATTEMPT_RECORD",
        "acfqp.campaign_attempt_record.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R4E_DOMAIN,
        "campaign_attempt_record_id",
        1,
        1,
    ),
    (
        "STABLE_INPUT_SNAPSHOT",
        "acfqp.campaign_stable_input_snapshot.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_STABLE_INPUT_SNAPSHOT_V180R12R4E_DOMAIN,
        "stable_input_snapshot_id",
        2,
        0,
    ),
    (
        "IO_TRANSFER_RECEIPT",
        "acfqp.campaign_io_transfer_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_IO_TRANSFER_RECEIPT_V180R12R4E_DOMAIN,
        "io_transfer_receipt_id",
        8,
        8,
    ),
    (
        "MEMFD_STAGE_RECEIPT",
        "acfqp.campaign_memfd_stage_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_MEMFD_STAGE_RECEIPT_V180R12R4E_DOMAIN,
        "memfd_stage_receipt_id",
        2,
        0,
    ),
    (
        "FD_VISIBILITY_RECEIPT",
        "acfqp.campaign_fd_visibility_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_FD_VISIBILITY_RECEIPT_V180R12R4E_DOMAIN,
        "fd_visibility_receipt_id",
        4,
        4,
    ),
    (
        "SEMANTIC_OPERATION_RECEIPT",
        "acfqp.campaign_semantic_operation_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_SEMANTIC_OPERATION_RECEIPT_V180R12R4E_DOMAIN,
        "semantic_operation_receipt_id",
        297,
        297,
    ),
    (
        "PIDFD_BIRTH_RECEIPT",
        "acfqp.campaign_pidfd_birth_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_PIDFD_BIRTH_RECEIPT_V180R12R4E_DOMAIN,
        "pidfd_birth_receipt_id",
        2,
        2,
    ),
    (
        "PIDFD_REAP_RECEIPT",
        "acfqp.campaign_pidfd_reap_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_PIDFD_REAP_RECEIPT_V180R12R4E_DOMAIN,
        "pidfd_reap_receipt_id",
        2,
        2,
    ),
    (
        "CGROUP_TOPOLOGY_RECEIPT",
        "acfqp.campaign_cgroup_topology_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CGROUP_TOPOLOGY_RECEIPT_V180R12R4E_DOMAIN,
        "cgroup_topology_receipt_id",
        1,
        0,
    ),
    (
        "CGROUP_OBSERVATION_RECEIPT",
        "acfqp.campaign_cgroup_observation_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CGROUP_OBSERVATION_RECEIPT_V180R12R4E_DOMAIN,
        "cgroup_observation_receipt_id",
        1,
        1,
    ),
    (
        "REPLAY_SUBJECT_RECEIPT",
        "acfqp.campaign_replay_subject_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_REPLAY_SUBJECT_RECEIPT_V180R12R4E_DOMAIN,
        "replay_subject_receipt_id",
        1,
        0,
    ),
    (
        "CAMPAIGN_SUBJECT_RESULT",
        "acfqp.campaign_measurement_subject_result.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_SUBJECT_RESULT_V180R12R4E_DOMAIN,
        "subject_result_id",
        1,
        0,
    ),
    (
        "SUBJECT_COMMIT_RECEIPT",
        "acfqp.campaign_subject_commit_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_SUBJECT_COMMIT_RECEIPT_V180R12R4E_DOMAIN,
        "subject_commit_receipt_id",
        1,
        1,
    ),
    (
        "WINDOW_CLOSURE_RECEIPT",
        "acfqp.campaign_window_closure_receipt.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_WINDOW_CLOSURE_RECEIPT_V180R12R4E_DOMAIN,
        "window_closure_receipt_id",
        1,
        1,
    ),
    (
        "CAMPAIGN_EXECUTION_CLOSURE",
        "acfqp.campaign_execution_closure.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R4E_DOMAIN,
        "campaign_execution_closure_id",
        1,
        0,
    ),
    (
        "CAMPAIGN_OPERATION_MANIFEST",
        "acfqp.campaign_operation_manifest.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_OPERATION_MANIFEST_V180R12R4E_DOMAIN,
        "campaign_operation_manifest_id",
        1,
        0,
    ),
    (
        "NATIVE_ZERO_SOURCE_MANIFEST",
        "acfqp.campaign_native_zero_source_manifest.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_MANIFEST_V180R12R4E_DOMAIN,
        "native_zero_source_manifest_id",
        1,
        0,
    ),
    (
        "NATIVE_ZERO_IMPORT_INVENTORY",
        "acfqp.campaign_native_zero_import_inventory.v180r12r4",
        evidence_domains.CONSTRUCTION_K7_NATIVE_ZERO_IMPORT_INVENTORY_V180R12R4E_DOMAIN,
        "native_zero_import_inventory_id",
        1,
        0,
    ),
)

# Every successful event kind has one exact evidence-ID policy.  The seven
# intent families account for 307 nulls; LEDGER_CLOSED contributes the final
# null to avoid a closure self-cycle.
SUCCESS_EVENT_EVIDENCE_REQUIREMENTS = (
    ("ATTEMPT_OPEN", "CAMPAIGN_ATTEMPT_RECORD", 1),
    ("INPUT_READ_INTENT", None, 5),
    ("INPUT_READ_OUTCOME", "IO_TRANSFER_RECEIPT", 5),
    ("STAGE_WRITE_INTENT", None, 2),
    ("STAGE_WRITE_OUTCOME", "IO_TRANSFER_RECEIPT", 2),
    ("MOUNT_VISIBILITY_OPEN", "FD_VISIBILITY_RECEIPT", 2),
    ("MOUNT_VISIBILITY_CLOSE", "FD_VISIBILITY_RECEIPT", 2),
    ("SEMANTIC_HASH_INTENT", None, SEMANTIC_HASH_OPERATION_COUNT),
    (
        "SEMANTIC_HASH_OUTCOME",
        "SEMANTIC_OPERATION_RECEIPT",
        SEMANTIC_HASH_OPERATION_COUNT,
    ),
    ("INTEGRITY_CHECK_INTENT", None, INTEGRITY_CHECK_OPERATION_COUNT),
    (
        "INTEGRITY_CHECK_OUTCOME",
        "SEMANTIC_OPERATION_RECEIPT",
        INTEGRITY_CHECK_OPERATION_COUNT,
    ),
    ("PROTOCOL_CHECK_INTENT", None, PROTOCOL_CHECK_OPERATION_COUNT),
    (
        "PROTOCOL_CHECK_OUTCOME",
        "SEMANTIC_OPERATION_RECEIPT",
        PROTOCOL_CHECK_OPERATION_COUNT,
    ),
    ("PROCESS_BIRTH_INTENT", None, 2),
    ("PROCESS_BIRTH_OUTCOME", "PIDFD_BIRTH_RECEIPT", 2),
    ("PROCESS_REAP", "PIDFD_REAP_RECEIPT", 2),
    ("SUBJECT_WRITE_INTENT", None, 1),
    ("SUBJECT_WRITE_OUTCOME", "IO_TRANSFER_RECEIPT", 1),
    ("SUBJECT_COMMIT", "SUBJECT_COMMIT_RECEIPT", 1),
    ("WINDOW_CLOSED", "WINDOW_CLOSURE_RECEIPT", 1),
    ("CGROUP_OBSERVED", "CGROUP_OBSERVATION_RECEIPT", 1),
    ("LEDGER_CLOSED", None, 1),
)
SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT = sum(
    count
    for _event_kind, evidence_type, count in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS
    if evidence_type is not None
)
SUCCESS_NULL_EVENT_EVIDENCE_COUNT = sum(
    count
    for _event_kind, evidence_type, count in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS
    if evidence_type is None
)
SUCCESS_EVIDENCE_DOCUMENT_COUNT = sum(row[4] for row in EVIDENCE_INVENTORY_ROWS)
SUCCESS_DIRECT_EVENT_EVIDENCE_DOCUMENT_COUNT = sum(
    row[5] for row in EVIDENCE_INVENTORY_ROWS
)
SUCCESS_SUPPORT_EVIDENCE_DOCUMENT_COUNT = (
    SUCCESS_EVIDENCE_DOCUMENT_COUNT - SUCCESS_DIRECT_EVENT_EVIDENCE_DOCUMENT_COUNT
)

EVIDENCE_CAUSAL_JOIN_RULES = (
    "ATTEMPT_RECORD_PRECEDES_CGROUP_CREATION_AND_EXCLUDES_CGROUP_TOPOLOGY_ID",
    "FINAL_SUBJECT_REFERENCES_CAMPAIGN_ATTEMPT_RECORD_NOT_SEMANTIC_RECEIPT_IDS",
    "ALL_297_SEMANTIC_RECEIPTS_REFERENCE_CAMPAIGN_ATTEMPT_RECORD_AS_"
    "EVIDENCE_SUBJECT",
    "REPLAY_SUBJECT_REFERENCES_ATTEMPT_FINAL_SUBJECT_AND_EXACT_297_SEMANTIC_"
    "RECEIPTS",
    "SUBJECT_WRITE_IO_RECEIPT_REFERENCES_SUBJECT_RESULT_AND_WORKER_BIRTH_RECEIPT",
    "REPLAY_SUBJECT_FIRST_CONSUMED_BY_LATER_SUBJECT_COMMIT",
    "SUBJECT_READBACK_IO_RECEIPT_REFERENCES_SUBJECT_RESULT_AND_SUPERVISOR_BIRTH_"
    "RECEIPT",
    "SUCCESS_EVENT_EVIDENCE_ID_MUST_BE_ISSUED_BEFORE_EVENT_APPEND",
)

WALL_TIMEOUT_SECONDS = 14_400
CAMPAIGN_CLEANUP_GRACE_SECONDS = 600
TERMINATION_GRACE_SECONDS = 10
MEMORY_MAX_BYTES = 16 * 1024 * 1024 * 1024
ADDRESS_SPACE_HARD_CAP_BYTES = MEMORY_MAX_BYTES
PIDS_MAX = 2
INPUT_FILE_BYTE_CAP = 1 * 1024 * 1024
INPUT_TOTAL_BYTE_CAP = 2 * 1024 * 1024
SUBJECT_RESULT_BYTE_CAP = 1 * 1024 * 1024
# The semantic contract retains the 1 MiB absolute subject bound, while the
# physical subject-result document is deliberately smaller so its complete
# signed seq608 EVENT_PROPOSAL fits the one-frame transport cap.
SUBJECT_RESULT_RUNTIME_BYTE_CAP = 768 * 1024
FRAME_BYTE_CAP = 1 * 1024 * 1024
SOCK_SEQPACKET_BUFFER_REQUEST_BYTES = FRAME_BYTE_CAP
SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES = 2 * FRAME_BYTE_CAP
TERMINAL_BYTE_CAP = 16 * 1024 * 1024
VERIFICATION_BYTE_CAP = 16 * 1024 * 1024
EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP = 64 * 1024 * 1024
EXECUTION_CLOSURE_BYTE_CAP = 1 * 1024 * 1024
OS_RECEIPT_BUNDLE_BYTE_CAP = 16 * 1024 * 1024
LEDGER_CLOSURE_BYTE_CAP = 64 * 1024 * 1024
STDOUT_BYTE_CAP = 1 * 1024 * 1024
STDERR_BYTE_CAP = 1 * 1024 * 1024
FAILURE_EMERGENCY_RESERVE_BYTES = 4 * 1024 * 1024
FAILURE_MESSAGE_BYTE_CAP = 4_096
MAX_EVENT_COUNT = 4_096
MAX_EVENT_BYTE_COUNT = 65_536
MAX_LEDGER_BYTE_COUNT = 64 * 1024 * 1024
FAILURE_ARTIFACT_OBSERVATION_ROW_CAP = 4_112
FAILURE_ARTIFACT_METADATA_BYTE_CAP = 2 * 1024 * 1024
FAILURE_DIRECTORY_ENTRY_CAP = 4_096
FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP = 256 * 1024
FAILURE_ARTIFACT_HASH_BYTE_CAP = MAX_LEDGER_BYTE_COUNT + MAX_EVENT_BYTE_COUNT
FAILURE_ARTIFACT_OBSERVATION_FIELDS = (
    "relative_path",
    "kind",
    "state",
    "mode",
    "nlink",
    "byte_count",
    "sha256",
    "directory_entries",
    "read_error_type",
    "read_error_message",
)
FAILURE_CGROUP_OBSERVATION_FIELDS = (
    "root_populated",
    "supervisor_leaf_populated",
    "worker_leaf_populated",
    "root_process_count",
    "supervisor_leaf_process_count",
    "worker_leaf_process_count",
    "memory_peak_bytes",
    "pids_peak",
    "memory_events",
    "pids_events",
    "kill_outcome",
    "reap_outcome",
    "close_outcome",
    "observation_errors",
    "node_observations",
)
FAILURE_CGROUP_NODE_OBSERVATION_FIELDS = (
    "role",
    "path",
    "state",
    "mode",
    "nlink",
    "device",
    "inode",
    "populated",
    "process_count",
    "read_error_type",
    "read_error_message",
)
FAILURE_CGROUP_NODE_ROLES = ("MEASUREMENT_ROOT", "SUPERVISOR", "WORKER")
FAILURE_CGROUP_NODE_STATES = (
    "ABSENT",
    "LINKED_OR_NONDIR",
    "PRESENT",
    "READ_ERROR",
)
FAILURE_STATE_FIELDS = (
    "schema",
    "schema_version",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "failure_code",
    "phase",
    "operation_id",
    "last_event_id",
    "completed_event_count",
    "launch_substage",
    "launch_errno",
    "launch_child_created",
    "launch_pidfd_acquired",
    "launch_exec_observed",
    "message",
    "message_sha256",
    "process_may_remain",
    "output_may_exist",
    "partial_artifact_observations",
    "partial_artifact_observation_boundary",
    "cgroup_failure_observation",
    "cgroup_topology_conformance_diagnostic",
    "same_identity_rerun_forbidden",
    "successful_ledger_claimed",
    "counter_records_issued",
    "failure_state_id",
)

VERIFICATION_FAILURE_SCHEMA = (
    "acfqp.campaign_measurement_verification_failure.v180r12r4"
)
VERIFICATION_FAILURE_FIELDS = (
    "schema",
    "schema_version",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "verification_launch_attempt_id",
    "failure_code",
    "phase",
    "operation_id",
    "last_event_id",
    "completed_event_count",
    "failure_type",
    "message",
    "message_sha256",
    "process_may_remain",
    "output_may_exist",
    "partial_artifact_observations",
    "partial_artifact_observation_boundary",
    "cgroup_failure_observation",
    "same_identity_rerun_forbidden",
    "successful_ledger_claimed",
    "counter_records_issued",
    "failure_memory_reserve_bytes",
    "failure_memory_reserve_allocated",
    "failure_memory_reserve_released_before_failure",
    "watchdog_was_armed",
    "watchdog_cleanup_observation",
    "traceback_retained",
    "campaign_actual_measurement",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "CAMPAIGN_CLEANUP_GRACE_SECONDS",
    "OFFICIAL_EXECUTION_GATE",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "verification_failure_id",
)
VERIFICATION_FAILURE_WATCHDOG_CLEANUP_FIELDS = (
    "cancel_attempted",
    "cancel_succeeded",
    "ignore_attempted",
    "ignore_succeeded",
    "handler_restore_attempted",
    "handler_restore_succeeded",
    "teardown_completed",
    "secondary_observations",
)
VERIFICATION_FAILURE_WATCHDOG_SECONDARY_FIELDS = (
    "failure_type",
    "failure_message",
)
VERIFICATION_FAILURE_OBSERVATION_BOUNDARY = (
    "IMMEDIATELY_BEFORE_FAILURE_WRITE"
)
VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES = 64 * 1024
VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP = 4_096
VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP = 256 * 1024
VERIFICATION_FAILURE_WATCHDOG_SECONDARY_OBSERVATION_CAP = 3

EVIDENCE_INVENTORY_BUNDLE_SCHEMA = (
    "acfqp.campaign_evidence_inventory_bundle.v180r12r4"
)
EXECUTION_CLOSURE_SCHEMA = "acfqp.campaign_execution_closure.v180r12r4"
OS_RECEIPT_BUNDLE_SCHEMA = "acfqp.campaign_os_receipt_bundle.v180r12r4"
LEDGER_CLOSURE_SCHEMA = "acfqp.campaign_measurement_ledger_closure.v180r12r4"
TERMINAL_SCHEMA = "acfqp.campaign_measurement_terminal.v180r12r4"
CAMPAIGN_SUBJECT_RESULT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "scope",
        "protocol_id",
        "authorization_id",
        "authorization_evidence_id",
        "attempt_id",
        "campaign_attempt_record_id",
        "execution_slot_id",
        "execution_nonce",
        "logical_occurrence_id",
        "prelaunch_materialization_terminal_id",
        "prelaunch_launch_manifest_sha256",
        "prelaunch_launch_rule_id",
        "measurement_launch_attempt_id",
        "terminal_content_id",
        "terminal_byte_count",
        "terminal_sha256",
        "verification_content_id",
        "verification_byte_count",
        "verification_sha256",
        "terminal_snapshot_id",
        "verification_snapshot_id",
        "memfd_stage_receipt_ids",
        "open_visibility_receipt_ids",
        "worker_birth_receipt_id",
        "operation_manifest_id",
        "inner_content_ids",
        "inner_content_id_count",
        "semantic_hash_operation_count",
        "integrity_check_operation_count",
        "protocol_check_operation_count",
        "route_component_counter_closure_status",
        "exact_v180r12r2_verification_replayed",
        "producer_module_imported",
        "producer_entrypoint_called",
        "v180r12r2_verifier_imported",
        "v180r12r2_verifier_called",
        "retroactive_v180r12r2_cost_claimed",
        "counter_completeness_gate",
        "workload_economics_gate",
        "scalar_calibration_gate",
        "break_even_gate",
        "official_execution_gate",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
        "subject_byte_count",
        "subject_result_id",
    }
)

EVIDENCE_INVENTORY_BUNDLE_FIELDS = (
    "schema",
    "schema_version",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "evidence_document_count",
    "evidence_document_type_counts",
    "ordered_evidence_document_ids",
    "evidence_documents",
    "campaign_evidence_inventory_bundle_id",
)
EXECUTION_CLOSURE_FIELDS = (
    "schema",
    "schema_version",
    "scope",
    "scope_model",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "subject_id",
    "window_closed_event_id",
    "window_closure_receipt_id",
    "operation_manifest_id",
    "source_manifest_id",
    "import_inventory_id",
    "precompiled_source_bundle_sha256",
    "comparison_axis",
    "kernel_transition_calls",
    "registered_planning_operation_site_fact_count",
    "kernel_transition_operation_site_fact_ids",
    "kernel_transition_import_fact_ids",
    "unregistered_operation_site_fact_ids",
    "unregistered_import_fact_ids",
    "registered_planning_comparison_ground_kernel_axis_only",
    "prelaunch_sealed_application_import_allowlist_only",
    "runtime_role_exit_origin_guard_required",
    "runtime_role_exit_origin_guard_status",
    "not_an_os_syscall_count",
    "unregistered_or_dynamic_sites_forbidden",
    "closed_registered_planning_operation_window_only",
    "open_world_absence_claimed",
    "execution_window_closed",
    "campaign_execution_closure_id",
)
OS_RECEIPT_BUNDLE_FIELDS = (
    "schema",
    "schema_version",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "campaign_evidence_inventory_bundle_id",
    "os_receipt_document_count",
    "os_receipt_schema_counts",
    "ordered_os_receipt_ids",
    "os_receipt_documents",
    "campaign_os_receipt_bundle_id",
)
LEDGER_CLOSURE_FIELDS = (
    "schema",
    "schema_version",
    "scope",
    "scope_model",
    "protocol_id",
    "authorization_id",
    "attempt_id",
    "subject_id",
    "campaign_operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "campaign_execution_closure_id",
    "max_event_count",
    "max_event_byte_count",
    "max_ledger_byte_count",
    "events",
    "ordered_event_ids",
    "event_count",
    "ledger_event_byte_count",
    "first_event_id",
    "last_event_id",
    "evidence_documents",
    "campaign_evidence_document_count",
    "direct_event_evidence_document_count",
    "support_evidence_document_count",
    "campaign_evidence_document_type_counts",
    "event_evidence_nonnull_count",
    "event_evidence_null_count",
    "path_receipts",
    "campaign_receipt_set",
    "counter_records",
    "campaign_work_vector",
    "campaign_comparison_vector",
    "campaign_projection_proof",
    "campaign_native_zero_attestation",
    "campaign_path_receipt_count",
    "campaign_counter_record_count",
    "campaign_work_vector_count",
    "campaign_comparison_vector_count",
    "campaign_projection_proof_count",
    "campaign_native_zero_attestation_count",
    "predecessor_occurrence_authoritative_receipt_count",
    "predecessor_structural_obligation_count",
    "predecessor_campaign_scope_structural_obligation_count",
    "predecessor_campaign_actual_receipt_count",
    "predecessor_campaign_authoritative_receipt_count",
    "successor_campaign_actual_receipt_count",
    "successor_campaign_counter_record_count",
    "combined_successor_authoritative_receipt_count",
    "successful_campaign_authoritative_receipt_count",
    "successful_combined_authoritative_receipt_count",
    "terminal_pending_authoritative_receipt_join",
    "independent_verifier_pass_authoritative_receipt_join",
    "predecessor_structural_nine_are_successor_actual_receipts",
    "predecessor_structural_obligations_are_not_current_measurements",
    "authoritative_receipt_arithmetic_90_plus_9_equals_99",
    "hash_chain_complete",
    "lifecycle_phase_order_complete",
    "actual_measurements_present",
    "all_nine_campaign_paths_strictly_positive",
    "independent_comparison_axis_native_zero_complete",
    "route_free_campaign_accounting",
    "independent_verification_present",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "OFFICIAL_EXECUTION_GATE",
    "v180r13_weight_agnostic_economics_input_ready",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "scientific_success_claimed",
    "campaign_ledger_closure_id",
)
TERMINAL_FIELDS = (
    "schema",
    "schema_version",
    "scope",
    "scope_model",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "precompiled_source_bundle_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "subject_id",
    "campaign_operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "campaign_execution_closure_id",
    "campaign_execution_closure_byte_count",
    "campaign_execution_closure_sha256",
    "campaign_evidence_inventory_bundle_id",
    "campaign_evidence_inventory_bundle_byte_count",
    "campaign_evidence_inventory_bundle_sha256",
    "campaign_os_receipt_bundle_id",
    "campaign_os_receipt_bundle_byte_count",
    "campaign_os_receipt_bundle_sha256",
    "campaign_ledger_closure_id",
    "campaign_ledger_closure_byte_count",
    "campaign_ledger_closure_sha256",
    "campaign_measurement_ledger",
    "os_receipt_documents",
    "os_receipt_ids",
    "os_receipt_schema_counts",
    "event_count",
    "evidence_document_count",
    "os_receipt_document_count",
    "campaign_path_receipt_count",
    "campaign_counter_record_count",
    "campaign_work_vector_count",
    "campaign_comparison_vector_count",
    "campaign_projection_proof_count",
    "campaign_native_zero_attestation_count",
    "predecessor_occurrence_authoritative_receipt_count",
    "successor_campaign_authoritative_receipt_count",
    "combined_successor_authoritative_receipt_count",
    "authoritative_receipt_arithmetic_90_plus_9_equals_99",
    "raw_event_evidence_and_os_receipts_replayed",
    "route_free_campaign_accounting",
    "all_nine_campaign_paths_strictly_positive",
    "independent_native_zero_attestation_present",
    "independent_verification_present",
    "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS",
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "BREAK_EVEN_GATE",
    "OFFICIAL_EXECUTION_GATE",
    "v180r13_weight_agnostic_economics_input_ready",
    "official_scalar_cost",
    "official_N_break_even",
    "official_execution_allowed",
    "scientific_success_claimed",
    "output_bytes_fixed_point",
    "campaign_measurement_terminal_id",
)

SUCCESS_ARTIFACT_ORDER = (
    "evidence_inventory",
    "execution_closure",
    "os_receipt",
    "ledger_closure",
)
SUCCESS_ARTIFACT_SCHEMA_ROWS = (
    (
        "evidence_inventory",
        EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle",
    ),
    (
        "execution_closure",
        EXECUTION_CLOSURE_SCHEMA,
        "campaign_execution_closure_id",
        "campaign_execution_closure",
    ),
    (
        "os_receipt",
        OS_RECEIPT_BUNDLE_SCHEMA,
        "campaign_os_receipt_bundle_id",
        "campaign_os_receipt_bundle",
    ),
    (
        "ledger_closure",
        LEDGER_CLOSURE_SCHEMA,
        "campaign_ledger_closure_id",
        "campaign_ledger_closure",
    ),
)
SUCCESS_DURABLE_WRITE_ORDER = (
    "EVIDENCE_INVENTORY",
    "EXECUTION_CLOSURE",
    "OS_RECEIPT",
    "LEDGER_CLOSURE",
    "TERMINAL",
)

EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID = (
    "5ec6496223fdd24664d142d581847f3e95456a3b0bb171df2950302e413ac60b"
)
EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID = (
    "ee833b2260347a85442802459cd3ae6edd62b3abd35ba8d15b1829f7e9fa04f8"
)
EXPECTED_PRELAUNCH_LAUNCH_RULE_ID = (
    "9bedb474878ba9f3c7eb9735278b03fd91299c978f959ae30433a22b41b23817"
)
PROTOCOL_FINAL_ANCHOR_NAMES = (
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
    "LOGICAL_OCCURRENCE_ID",
    "EXECUTION_NONCE",
    "EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID",
    "EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID",
    "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID",
)
_PROTOCOL_FINAL_ID_ANCHOR_NAMES = frozenset(PROTOCOL_FINAL_ANCHOR_NAMES) - {
    "EXPECTED_CANONICAL_BYTE_COUNT"
}
_PROTOCOL_SOURCE_BYTE_CAP = 4 * 1024 * 1024
PRELAUNCH_EXTERNAL_ROOT_SCHEMA = "acfqp.v180r12r4_prelaunch_external_root.v1"
PRELAUNCH_MANIFEST_SCHEMA = (
    "acfqp.v180r12r4_source_bound_launch_manifest.v1"
)
PRELAUNCH_MATERIALIZATION_TERMINAL_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_terminal.v1"
)
PRELAUNCH_MATERIALIZATION_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_materialization_failure.v1"
)
PRELAUNCH_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_launch_attempt.v1"
)
PRELAUNCH_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_launch_receipt.v1"
)
PRELAUNCH_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_launch_failure.v1"
)
PRELAUNCH_LAUNCH_PUBLICATION_STAGES = (
    "BEFORE_PARENT_OPEN",
    "BEFORE_O_EXCL",
    "AFTER_O_EXCL",
    "AFTER_FULL_WRITE",
    "AFTER_FILE_FSYNC",
    "AFTER_PARENT_FSYNC",
    "AFTER_READBACK",
)
PRELAUNCH_LAUNCH_PUBLICATION_STATES = (
    "ABSENT",
    "PRESENT_PARTIAL_OR_INVALID",
    "PRESENT_EXACT",
)
PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS = (
    "publication_failure_artifact",
    "publication_failure_stage",
    "publication_failure_path_created",
    "publication_failure_completed",
    "publication_failure_observed_state",
)
PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_attempt.v1"
)
PRELAUNCH_SERVICE_LAUNCH_RECEIPT_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_receipt.v1"
)
PRELAUNCH_SERVICE_LAUNCH_FAILURE_SCHEMA = (
    "acfqp.v180r12r4_prelaunch_service_launch_failure.v1"
)
PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES = (
    "BEFORE_PARENT_OPEN",
    "BEFORE_O_EXCL",
    "AFTER_O_EXCL",
    "AFTER_FULL_WRITE",
    "AFTER_FILE_FSYNC",
    "AFTER_PARENT_FSYNC",
    "AFTER_READBACK",
)
PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-attempt:v180r12r4"
)
PRELAUNCH_SERVICE_LAUNCH_RECEIPT_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-receipt:v180r12r4"
)
PRELAUNCH_SERVICE_LAUNCH_FAILURE_DOMAIN = (
    "acfqp:construction-k7-prelaunch-service-launch-failure:v180r12r4"
)
PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS = (
    "schema",
    "target",
    "token",
    "unit_name",
    "materialization_terminal_id",
    "materialization_terminal_sha256",
    "launch_rule_id",
    "production_systemd_service_invocation",
    "systemd_run_argv",
    "systemd_run_environment",
    "pre_attempt_unit_absence_observation",
    "inner_launch_artifact_paths",
    "monotonic_origin_ns",
    "hard_deadline_ns",
    "campaign_deadline_ns",
    "attempt_o_excl_before_systemd_run",
    "same_target_identity_rerun_forbidden",
    "pre_scientific_outer_dispatch",
    "campaign_event_or_evidence_document",
    "service_launch_attempt_id",
)
PRELAUNCH_SERVICE_LAUNCH_INNER_JOIN_FIELDS = (
    "inner_launch_attempt_fact",
    "inner_launch_receipt_fact",
    "inner_launch_failure_fact",
    "inner_launch_attempt_id",
    "inner_launch_terminal_kind",
    "inner_launch_terminal_id",
    "exact_attempt_terminal_join",
)
PRELAUNCH_SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS = (
    "systemctl_argv",
    "systemctl_environment",
    "return_code",
    "timed_out",
    "stdout",
    "stderr",
    "expected_load_state",
    "unit_absent_after_wait_collect",
)
PRELAUNCH_SERVICE_LAUNCH_TERMINAL_COMMON_FIELDS = (
    "schema",
    "target",
    "service_launch_attempt_id",
    "token",
    "unit_name",
    "production_systemd_service_invocation",
    "systemd_run_return_code",
    "systemd_run_timed_out",
    "systemd_run_stdout",
    "systemd_run_stderr",
    "collected_unit_absence_observation",
    *PRELAUNCH_SERVICE_LAUNCH_INNER_JOIN_FIELDS,
    "attempt_lock_preserved",
    "same_target_identity_rerun_forbidden",
    "pre_scientific_outer_dispatch",
    "campaign_event_or_evidence_document",
    "success",
    "failure_type",
    "failure_message",
)
PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS = (
    *PRELAUNCH_SERVICE_LAUNCH_TERMINAL_COMMON_FIELDS,
    "service_launch_receipt_id",
)
PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS = (
    *PRELAUNCH_SERVICE_LAUNCH_TERMINAL_COMMON_FIELDS,
    "publication_failure_artifact",
    "publication_failure_stage",
    "publication_failure_path_created",
    "publication_failure_completed",
    "publication_failure_observed_state",
    "service_launch_failure_id",
)
EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_external_launch_context.v1"
)
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_verified_external_launch_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_frozen_authorization_context.v1"
)
FROZEN_AUTHORIZATION_CONTEXT_FIELDS = (
    "schema",
    "protocol_id",
    "protocol_byte_count",
    "protocol_sha256",
    "authorization_id",
    "authorization_byte_count",
    "authorization_sha256",
    "authorization_evidence_id",
    "authorization_evidence_byte_count",
    "authorization_evidence_sha256",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_id",
    "cgroup_parent_fact",
    "runtime_capability_fact",
)
EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    "schema",
    "target",
    "actor_role",
    "repository_root",
    "c_pre_root",
    "prereg_commit_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_materialization_terminal_byte_count",
    "prelaunch_materialization_terminal_sha256",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "current_launch_attempt_id",
    "current_launch_attempt_byte_count",
    "current_launch_attempt_sha256",
    "measurement_launch_attempt_id",
    "measurement_launch_attempt_byte_count",
    "measurement_launch_attempt_sha256",
    "protocol_id",
    "protocol_byte_count",
    "protocol_sha256",
    "authorization_id",
    "authorization_byte_count",
    "authorization_sha256",
    "authorization_evidence_id",
    "authorization_evidence_byte_count",
    "authorization_evidence_sha256",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_id",
    "monotonic_origin_ns",
    "hard_deadline_ns",
    "campaign_deadline_ns",
    "cgroup_parent_fact",
    "runtime_capability_fact",
    "production_systemd_service_invocation",
    "production_runtime_placement_t1",
    "inherited_fd_roles",
    "target_payload",
    "one_shot",
)
VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS = (
    *EXTERNAL_LAUNCH_CONTEXT_FIELDS,
    "precompiled_source_bundle_sha256",
    "native_zero_precompiled_source_rows",
    "external_launch_context_sha256",
    "context_consumed_once",
)
REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS = (
    *VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS,
    "production_runtime_placement_t2",
)
MEASUREMENT_CGROUP_OBSERVATION_PHASES = (
    "BEFORE_POPEN", "CLEANUP", "AFTER_CHILD",
)
MEASUREMENT_CGROUP_OBSERVATION_FIELDS = (
    "phase", "applicable", "campaign_attempt_id", "root_name",
    "ownership_acquired", "root_state", "root_mode", "root_nlink",
    "root_device", "root_inode", "root_populated", "root_process_count",
    "supervisor_state", "worker_state", "kill_attempted", "kill_succeeded",
    "wait_empty_attempted", "wait_empty_succeeded", "remove_attempted",
    "remove_succeeded", "residual_tree_or_process_possible", "error_type",
    "error_message",
)
EXTERNAL_LAUNCH_CONTEXT_FD = 249
DELEGATED_CGROUP_PARENT_FD = 250
CGROUP2_MOUNT_FD = 251
SOURCE_SYSTEMD_SERVICE_FD = 252
EXTERNAL_FD_ROLE_MAP = {
    "measurement": (
        (EXTERNAL_LAUNCH_CONTEXT_FD, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),
        (DELEGATED_CGROUP_PARENT_FD, "DELEGATED_CGROUP_PARENT_DIRECTORY"),
        (CGROUP2_MOUNT_FD, "CGROUP2_MOUNT_DIRECTORY"),
        (SOURCE_SYSTEMD_SERVICE_FD, "SOURCE_SYSTEMD_SERVICE_DIRECTORY"),
    ),
    "verification": (
        (EXTERNAL_LAUNCH_CONTEXT_FD, "EXTERNAL_LAUNCH_CONTEXT_MEMFD"),
    ),
}
EXTERNAL_FD_ROLE_RULES = {
    "EXTERNAL_LAUNCH_CONTEXT_MEMFD": (
        "SEALED_MEMFD",
        "READ_ONLY",
        "0400",
        ("F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE"),
        True,
        False,
    ),
    "DELEGATED_CGROUP_PARENT_DIRECTORY": (
        "DIRECTORY",
        "O_RDONLY|O_DIRECTORY|O_NOFOLLOW",
        None,
        (),
        False,
        True,
    ),
    "CGROUP2_MOUNT_DIRECTORY": (
        "DIRECTORY",
        "O_PATH|O_DIRECTORY|O_NOFOLLOW",
        None,
        (),
        False,
        True,
    ),
    "SOURCE_SYSTEMD_SERVICE_DIRECTORY": (
        "DIRECTORY",
        "O_RDONLY|O_DIRECTORY|O_NOFOLLOW",
        None,
        (),
        False,
        True,
    ),
}
RUNTIME_IPC_FRAME_SCHEMA = "acfqp.v180r12r4_runtime_ipc_frame.v1"
RUNTIME_IPC_FRAME_FIELDS = (
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
RUNTIME_IPC_UNSIGNED_FRAME_FIELDS = RUNTIME_IPC_FRAME_FIELDS[:-1]
SNAPSHOT_BYTES_TRANSPORT_SCHEMA = (
    "acfqp.v180r12r4_snapshot_bytes_transport.v1"
)
SNAPSHOT_BYTES_TRANSPORT_FIELDS = (
    "schema",
    "snapshot_receipt_id",
    "role",
    "byte_count",
    "sha256",
    "canonical_bytes_hex",
)
SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP = 512 * 1024
SNAPSHOT_BYTES_TRANSPORT_EVENT_ROWS = (
    (4, "STAGE", "SUPERVISOR", "INPUT_READ_OUTCOME", "TERMINAL"),
    (6, "STAGE", "SUPERVISOR", "INPUT_READ_OUTCOME", "VERIFICATION"),
)
RUNTIME_CHANNEL_KEY_CONTEXT_SCHEMA = (
    "acfqp.v180r12r4_runtime_channel_key_context.v1"
)
RUNTIME_CHANNEL_KEY_CONTEXT_FIELDS = (
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
RUNTIME_IPC_ROLE_FRAME_TYPE_ROWS = (
    (
        "OBSERVER",
        "SUPERVISOR",
        "PARENT_TO_CHILD",
        ("EVENT_ACK", "SUPERVISOR_START"),
    ),
    ("OBSERVER", "SUPERVISOR", "CHILD_TO_PARENT", ("EVENT_PROPOSAL",)),
    (
        "SUPERVISOR",
        "WORKER",
        "PARENT_TO_CHILD",
        ("EVENT_ACK", "WORKER_HANDOFF"),
    ),
    ("SUPERVISOR", "WORKER", "CHILD_TO_PARENT", ("EVENT_PROPOSAL",)),
)
RUNTIME_IPC_FIRST_PARENT_FRAME_ROWS = (
    ("OBSERVER", "SUPERVISOR", "SUPERVISOR_START"),
    ("SUPERVISOR", "WORKER", "WORKER_HANDOFF"),
)
RUNTIME_IPC_UNDEFINED_CONTROL_FRAME_TYPES = (
    "FAILURE_NOTICE",
    "SUPERVISOR_COMPLETE",
    "WORKER_COMPLETE",
)
OBSERVER_SUPERVISOR_START_SCHEMA = (
    "acfqp.v180r12r4_observer_supervisor_start.v1"
)
OBSERVER_SUPERVISOR_START_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_measurement_execution_slot_id",
    "logical_occurrence_id",
    "execution_nonce",
    "campaign_attempt_record_id",
    "campaign_operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "cgroup_topology_receipt_id",
    "cgroup_topology_document",
    "supervisor_birth_operation_id",
    "supervisor_birth_receipt_id",
    "supervisor_birth_document",
    "supervisor_birth_event_id",
    "supervisor_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_start",
)
SUPERVISOR_WORKER_HANDOFF_SCHEMA = (
    "acfqp.v180r12r4_supervisor_worker_handoff.v1"
)
SUPERVISOR_WORKER_HANDOFF_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_attempt_record_id",
    "execution_slot_id",
    "execution_nonce",
    "logical_occurrence_id",
    "prelaunch_materialization_terminal_id",
    "prelaunch_launch_manifest_sha256",
    "prelaunch_launch_rule_id",
    "measurement_launch_attempt_id",
    "operation_manifest_id",
    "native_zero_source_manifest_id",
    "native_zero_import_inventory_id",
    "terminal_snapshot_document",
    "verification_snapshot_document",
    "terminal_memfd_stage_document",
    "verification_memfd_stage_document",
    "terminal_open_visibility_document",
    "verification_open_visibility_document",
    "stage_semantic_receipt_documents",
    "terminal_stage_binding",
    "verification_stage_binding",
    "subject_output_binding",
    "worker_birth_operation_id",
    "worker_birth_receipt_id",
    "worker_birth_document",
    "worker_birth_event_id",
    "worker_birth_event_sequence",
    "next_campaign_event_sequence",
    "one_shot_handoff",
)
EVENT_PROPOSAL_BODY_SCHEMA = "acfqp.v180r12r4_event_proposal.v1"
EVENT_PROPOSAL_BODY_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_event_sequence",
    "phase",
    "actor_role",
    "event_kind",
    "operation_id",
    "payload",
    "evidence_documents",
)
EVENT_ACK_BODY_SCHEMA = "acfqp.v180r12r4_event_ack.v1"
EVENT_ACK_BODY_FIELDS = (
    "schema",
    "protocol_id",
    "authorization_id",
    "authorization_evidence_id",
    "attempt_id",
    "campaign_event_sequence",
    "event_id",
    "event_file_sha256",
    "durable_file_and_directory_fsync_complete",
)
STAGE_FD_BINDING_FIELDS = (
    "fd",
    "device",
    "inode",
    "byte_count",
    "memfd_stage_receipt_id",
    "open_visibility_receipt_id",
)
SUBJECT_OUTPUT_FD_BINDING_FIELDS = (
    "fd",
    "device",
    "inode",
    "mode",
    "nlink",
    "initial_byte_count",
)
PRELAUNCH_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch"
)
PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch_external_root.json"
)
PRELAUNCH_BOOTSTRAP_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/bootstrap.py"
PRELAUNCH_LAUNCHER_RELATIVE_PATH = f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launcher.py"
PRELAUNCH_MANIFEST_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/launch_manifest.json"
)
PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MATERIALIZATION_TERMINAL.json"
)
PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_prelaunch_failure.json"
)
PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_LAUNCH_RECEIPT.json"
)
PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_measurement_launch_failure.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_LAUNCH_RECEIPT.json"
)
PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_verification_launch_failure.json"
)
PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/MEASUREMENT_SERVICE_LAUNCH_RECEIPT.json"
)
PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_measurement_service_launch_failure.json"
)
PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_SERVICE_LAUNCH_ATTEMPT.json"
)
PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH = (
    f"{PRELAUNCH_ROOT_RELATIVE_PATH}/VERIFICATION_SERVICE_LAUNCH_RECEIPT.json"
)
PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_prelaunch_verification_service_launch_failure.json"
)
PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/"
    "v180r12r4_campaign_measurement_pre_attempt_host_conformance.json"
)

OUTPUT_ROOT_RELATIVE_PATH = ".tmp/exact-freeze/v180r12r4_campaign_measurement"
ATTEMPT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_attempt.json"
)
TERMINAL_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/TERMINAL.json"
FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_failure.json"
)
VERIFICATION_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification.json"
)
VERIFICATION_FAILURE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_failure.json"
)
RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_verification_replay.json"
)
RUNTIME_CAS_ROOT_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r12r4_campaign_measurement_cas"
)
EVENTS_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/EVENTS"
SUBJECT_TEMP_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/SUBJECT_RESULT.json.partial"
SUBJECT_RESULT_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/SUBJECT_RESULT.json"
EVIDENCE_INVENTORY_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/EVIDENCE_INVENTORY.json"
)
EXECUTION_CLOSURE_RELATIVE_PATH = (
    f"{OUTPUT_ROOT_RELATIVE_PATH}/EXECUTION_CLOSURE.json"
)
OS_RECEIPT_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/OS_RECEIPT.json"
LEDGER_CLOSURE_RELATIVE_PATH = f"{OUTPUT_ROOT_RELATIVE_PATH}/LEDGER_CLOSURE.json"

VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS = tuple(
    sorted(
        (
            (
                EVIDENCE_INVENTORY_RELATIVE_PATH,
                "FILE",
                EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
            ),
            (
                EXECUTION_CLOSURE_RELATIVE_PATH,
                "FILE",
                EXECUTION_CLOSURE_BYTE_CAP,
            ),
            (OS_RECEIPT_RELATIVE_PATH, "FILE", OS_RECEIPT_BUNDLE_BYTE_CAP),
            (LEDGER_CLOSURE_RELATIVE_PATH, "FILE", LEDGER_CLOSURE_BYTE_CAP),
            (TERMINAL_RELATIVE_PATH, "FILE", TERMINAL_BYTE_CAP),
            (RUNTIME_CAS_ROOT_RELATIVE_PATH, "DIRECTORY", 1),
            (VERIFICATION_RELATIVE_PATH, "FILE", VERIFICATION_BYTE_CAP),
            (VERIFICATION_FAILURE_RELATIVE_PATH, "FILE", VERIFICATION_BYTE_CAP),
            (
                RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
                "FILE",
                VERIFICATION_BYTE_CAP,
            ),
        )
    )
)

SUCCESS_DURABLE_ARTIFACT_ROWS = (
    (
        "EVIDENCE_INVENTORY",
        "evidence_inventory",
        EVIDENCE_INVENTORY_RELATIVE_PATH,
        EVIDENCE_INVENTORY_BUNDLE_SCHEMA,
        domains.CONSTRUCTION_K7_CAMPAIGN_EVIDENCE_INVENTORY_BUNDLE_V180R12R4_DOMAIN,
        "campaign_evidence_inventory_bundle_id",
        "campaign_evidence_inventory_bundle",
        EVIDENCE_INVENTORY_BUNDLE_FIELDS,
        EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP,
    ),
    (
        "EXECUTION_CLOSURE",
        "execution_closure",
        EXECUTION_CLOSURE_RELATIVE_PATH,
        EXECUTION_CLOSURE_SCHEMA,
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_EXECUTION_CLOSURE_V180R12R4E_DOMAIN,
        "campaign_execution_closure_id",
        "campaign_execution_closure",
        EXECUTION_CLOSURE_FIELDS,
        EXECUTION_CLOSURE_BYTE_CAP,
    ),
    (
        "OS_RECEIPT",
        "os_receipt",
        OS_RECEIPT_RELATIVE_PATH,
        OS_RECEIPT_BUNDLE_SCHEMA,
        domains.CONSTRUCTION_K7_CAMPAIGN_OS_RECEIPT_BUNDLE_V180R12R4_DOMAIN,
        "campaign_os_receipt_bundle_id",
        "campaign_os_receipt_bundle",
        OS_RECEIPT_BUNDLE_FIELDS,
        OS_RECEIPT_BUNDLE_BYTE_CAP,
    ),
    (
        "LEDGER_CLOSURE",
        "ledger_closure",
        LEDGER_CLOSURE_RELATIVE_PATH,
        LEDGER_CLOSURE_SCHEMA,
        evidence_domains.CONSTRUCTION_K7_CAMPAIGN_LEDGER_CLOSURE_V180R12R4E_DOMAIN,
        "campaign_ledger_closure_id",
        "campaign_ledger_closure",
        LEDGER_CLOSURE_FIELDS,
        LEDGER_CLOSURE_BYTE_CAP,
    ),
)

FAILURE_PROGRESS_PATH_KIND_ROWS = tuple(
    sorted(
        (
            (ATTEMPT_RELATIVE_PATH, "FILE"),
            (OUTPUT_ROOT_RELATIVE_PATH, "DIRECTORY"),
            (EVENTS_RELATIVE_PATH, "DIRECTORY"),
            (FAILURE_RELATIVE_PATH, "FILE"),
            (SUBJECT_TEMP_RELATIVE_PATH, "FILE"),
            (SUBJECT_RESULT_RELATIVE_PATH, "FILE"),
            (EVIDENCE_INVENTORY_RELATIVE_PATH, "FILE"),
            (EXECUTION_CLOSURE_RELATIVE_PATH, "FILE"),
            (OS_RECEIPT_RELATIVE_PATH, "FILE"),
            (LEDGER_CLOSURE_RELATIVE_PATH, "FILE"),
            (TERMINAL_RELATIVE_PATH, "FILE"),
            (RUNTIME_CAS_ROOT_RELATIVE_PATH, "DIRECTORY"),
            (VERIFICATION_RELATIVE_PATH, "FILE"),
            (VERIFICATION_FAILURE_RELATIVE_PATH, "FILE"),
            (RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH, "FILE"),
        )
    )
)

CGROUP_PARENT_FACT_FIELDS = (
    "schema",
    "mount_point",
    "mount_fstype",
    "mount_device",
    "mount_inode",
    "mount_options",
    "parent_path",
    "parent_device",
    "parent_inode",
    "owner_uid",
    "owner_gid",
    "mode",
    "controllers",
    "subtree_control",
    "cgroup_type",
    "cgroup_namespace_inode",
    "cgroup_events_present",
    "memory_events_present",
    "pids_events_present",
    "cgroup_kill_present",
    "cgroup_procs_present",
    "memory_peak_present",
    "pids_peak_present",
    "self_membership",
)
RUNTIME_CAPABILITY_FACT_FIELDS = (
    "schema",
    "machine_architecture",
    "single_threaded",
    "clone3_probe_errno",
    "clone3_syscall_recognized",
    "pidfd_send_signal_probe_errno",
    "pidfd_send_signal_recognized",
    "execveat_probe_errno",
    "execveat_recognized",
    "pidfd_wait_present",
    "landlock_abi",
    "uid",
    "gid",
    "effective_capability_mask",
    "admitted",
)
PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA = (
    "acfqp.v180r12r4_pre_attempt_host_conformance.v2"
)
PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP = 65_536
SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA = (
    "acfqp.v180r12r4_socket_buffer_capability_fact.v1"
)
SOCKET_BUFFER_CAPABILITY_FACT_FIELDS = (
    "schema",
    "probe_boundary",
    "socket_family",
    "socket_type",
    "endpoint_count",
    "buffer_request_bytes",
    "effective_min_bytes",
    "net_core_wmem_max_bytes",
    "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes",
    "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes",
    "endpoint_1_so_rcvbuf_bytes",
)
SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS = (
    "schema",
    "probe_boundary",
    "socket_family",
    "socket_type",
    "endpoint_count",
    "buffer_request_bytes",
    "effective_min_bytes",
)
SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS = (
    "net_core_wmem_max_bytes",
    "net_core_rmem_max_bytes",
    "endpoint_0_so_sndbuf_bytes",
    "endpoint_0_so_rcvbuf_bytes",
    "endpoint_1_so_sndbuf_bytes",
    "endpoint_1_so_rcvbuf_bytes",
)
SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES = {
    "schema": SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA,
    "probe_boundary": "PRE_CAMPAIGN_ATTEMPT_O_EXCL",
    "socket_family": "AF_UNIX",
    "socket_type": "SOCK_SEQPACKET|SOCK_CLOEXEC",
    "endpoint_count": 2,
    "buffer_request_bytes": SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
    "effective_min_bytes": SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES,
}
SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES = {
    "net_core_wmem_max_bytes": SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
    "net_core_rmem_max_bytes": SOCK_SEQPACKET_BUFFER_REQUEST_BYTES,
    "endpoint_0_so_sndbuf_bytes": SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES,
    "endpoint_0_so_rcvbuf_bytes": SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES,
    "endpoint_1_so_sndbuf_bytes": SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES,
    "endpoint_1_so_rcvbuf_bytes": SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES,
}
SOCKET_BUFFER_CAPABILITY_MISMATCH_ROW_FIELDS = (
    "scope",
    "field",
    "minimum",
    "observed",
)
SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE = "socket_buffer_capability"
SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE = (
    "SOCKET_BUFFER_CAPABILITY_INSUFFICIENT"
)

SERVICE_CONTEXT_CAPTURE_RELATIVE_PATH = (
    "retained_evidence/v180r12r4r5_service_context_capture/"
    "service_context_capture.json"
)
SERVICE_CONTEXT_CAPTURE_SCHEMA = (
    "acfqp.v180r12r4r5_service_context_capture.v1"
)
SERVICE_CONTEXT_CAPTURE_PURPOSE = (
    "BENIGN_PRE_FREEZE_SERVICE_CONTEXT_OBSERVATION_NO_CAMPAIGN_ATTEMPT"
)
SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT = 1_459
SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256 = (
    "53508b200ae3b0279bda887cec804a8dd06f7d800734fe3d760f1712ea866fd3"
)
SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT = {
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
SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT = {
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

SOURCE_CLOSURE_REQUIRED_ROOTS = tuple(sorted((
    "scripts/bootstrap_v180r12r4_campaign_measurement.py",
    "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py",
    "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py",
    "scripts/run_v180r12r4_campaign_measurement.py",
    "scripts/supervise_v180r12r4_campaign_measurement.py",
    "scripts/verify_v180r12r4_campaign_measurement.py",
    "scripts/work_v180r12r4_campaign_measurement.py",
    "src/acfqp/construction_accounting_registry_v6.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r4.py",
    "src/acfqp/construction_k7_domain_registry_extension_v180r12r4e.py",
    "src/acfqp/construction_k7_campaign_measurement_ledger_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_protocol_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_execution_authorization_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_authorization_evidence_freeze_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_supervisor_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_worker_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_finalizer_v180r12r4.py",
    "src/acfqp/construction_k7_campaign_measurement_independent_verifier_v180r12r4.py",
    V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
    V180R12R2_EVIDENCE_SOURCE_RELATIVE_PATH,
)))
WORKER_ALLOWED_LOCAL_IMPORTS = (
    "acfqp.construction_k7_domain_registry_extension_v180r12r4e",
    "acfqp.phase3e_ids",
)
WORKER_FORBIDDEN_IMPORTS = (
    "acfqp.construction_k7_ten_terminal_aggregation_finalizer_v180r12r2",
    "acfqp.construction_k7_ten_terminal_aggregation_independent_verifier_v180r12r2",
    "acfqp.construction_k7_ten_terminal_aggregation_production_evidence_freeze_v180r12r2",
    "scripts.run_v180r12r2_ten_terminal_aggregation",
    "scripts.verify_v180r12r2_ten_terminal_aggregation",
)

_ROOT = Path(__file__).resolve().parents[2]


class CampaignMeasurementProtocolV180R12R4Error(ValueError):
    """The predecessor evidence or outcome-free measurement contract changed."""


def _fail(message: str) -> NoReturn:
    raise CampaignMeasurementProtocolV180R12R4Error(message)


def _read_protocol_source_bytes_v180r12r4() -> bytes:
    """Read this protocol source once through a stable, symlink-free FD."""

    try:
        descriptor = os.open(
            Path(__file__), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        )
    except OSError as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r4 protocol source is unreadable"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not (
            stat.S_ISREG(before.st_mode)
            and 0 < before.st_size <= _PROTOCOL_SOURCE_BYTE_CAP
        ):
            _fail("V180r12r4 protocol source is not one bounded regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                _fail("V180r12r4 protocol source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V180r12r4 protocol source grew during read")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    if identity(before) != identity(after):
        _fail("V180r12r4 protocol source changed during read")
    return b"".join(chunks)


def protocol_final_anchor_literals_v180r12r4(
    raw: bytes | None = None,
) -> dict[str, Any]:
    """Extract the exact nine direct final-anchor literals from protocol source."""

    source = _read_protocol_source_bytes_v180r12r4() if raw is None else raw
    if type(source) is not bytes:
        raise TypeError("protocol source must be exact bytes")
    try:
        tree = ast.parse(source, filename="V180r12r4 campaign protocol source")
    except (SyntaxError, UnicodeDecodeError, ValueError) as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r4 protocol source is not static UTF-8 Python"
        ) from error
    wanted = set(PROTOCOL_FINAL_ANCHOR_NAMES)
    values: dict[str, Any] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and len(statement.targets) == 1
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in wanted
        ):
            continue
        name = statement.targets[0].id
        if name in values or not isinstance(statement.value, ast.Constant):
            _fail("V180r12r4 protocol final anchor is duplicated or nonliteral")
        values[name] = statement.value.value
    if set(values) != wanted:
        _fail("V180r12r4 protocol final anchor set is incomplete")
    return values


def _is_nonzero_lower_sha256(value: object) -> bool:
    return (
        type(value) is str
        and value != ZERO_ID
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def require_frozen_protocol_final_anchor_set_v180r12r4() -> dict[str, Any]:
    """Fail closed unless all nine final anchors are direct, frozen literals."""

    values = protocol_final_anchor_literals_v180r12r4()
    current = {name: globals()[name] for name in PROTOCOL_FINAL_ANCHOR_NAMES}
    if values != current:
        _fail("V180r12r4 protocol final anchors differ from direct source literals")
    if not (
        type(values["EXPECTED_CANONICAL_BYTE_COUNT"]) is int
        and values["EXPECTED_CANONICAL_BYTE_COUNT"] > 0
        and all(
            _is_nonzero_lower_sha256(values[name])
            for name in _PROTOCOL_FINAL_ID_ANCHOR_NAMES
        )
    ):
        _fail("V180r12r4 protocol final anchor set is not fully frozen")
    return values


def _canonical_mapping(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{label} must be one mapping")
    try:
        document = loads_canonical_json(canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            f"{label} is not canonically serializable"
        ) from error
    if type(document) is not dict:
        _fail(f"{label} must be one exact object")
    return document


def _sorted_unique_strings(value: Any, label: str) -> list[str]:
    if not (
        type(value) is list
        and all(type(row) is str and row for row in value)
        and value == sorted(set(value))
    ):
        _fail(f"{label} must be sorted unique nonempty strings")
    return value


def validate_cgroup_parent_fact_v180r12r4(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_mapping(value, "cgroup parent fact")
    if set(document) != set(CGROUP_PARENT_FACT_FIELDS):
        _fail("cgroup parent fact field set changed")
    integers = (
        "mount_device",
        "mount_inode",
        "parent_device",
        "parent_inode",
        "owner_uid",
        "owner_gid",
        "mode",
        "cgroup_namespace_inode",
    )
    if any(type(document.get(key)) is not int or document[key] < 0 for key in integers):
        _fail("cgroup parent identity contains a non-integer or negative value")
    if document["mount_inode"] <= 0 or document["parent_inode"] <= 0:
        _fail("cgroup mount and parent inode must be positive")
    mount_point = document.get("mount_point")
    parent_path = document.get("parent_path")
    if not (
        document.get("schema") == "acfqp.v180r12r4_cgroup_parent_fact.v1"
        and document.get("mount_fstype") == "cgroup2"
        and type(mount_point) is str
        and PurePosixPath(mount_point).is_absolute()
        and PurePosixPath(mount_point).as_posix() == mount_point
        and type(parent_path) is str
        and PurePosixPath(parent_path).is_absolute()
        and PurePosixPath(parent_path).as_posix() == parent_path
        and PurePosixPath(mount_point) in PurePosixPath(parent_path).parents
        and document["parent_device"] == document["mount_device"]
        and 0 <= document["mode"] <= 0o7777
        and document.get("cgroup_type") == "domain"
        and type(document.get("self_membership")) is str
        and document["self_membership"].startswith("0::/")
    ):
        _fail("cgroup parent topology or schema changed")
    mount_options = _sorted_unique_strings(
        document.get("mount_options"), "cgroup mount options"
    )
    controllers = _sorted_unique_strings(
        document.get("controllers"), "cgroup controllers"
    )
    subtree = _sorted_unique_strings(
        document.get("subtree_control"), "cgroup subtree control"
    )
    if not (
        {"rw", "nsdelegate"} <= set(mount_options)
        and {"memory", "pids"} <= set(controllers)
        and {"memory", "pids"} <= set(subtree)
        and document["mode"] & 0o700 == 0o700
    ):
        _fail("cgroup parent does not delegate memory and pids")
    required_presence = (
        "cgroup_events_present",
        "memory_events_present",
        "pids_events_present",
        "cgroup_kill_present",
        "cgroup_procs_present",
        "memory_peak_present",
        "pids_peak_present",
    )
    if any(document.get(key) is not True for key in required_presence):
        _fail("cgroup parent lacks a required observation or cleanup surface")
    return document


def validate_runtime_capability_fact_v180r12r4(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    document = _canonical_mapping(value, "runtime capability fact")
    if set(document) != set(RUNTIME_CAPABILITY_FACT_FIELDS):
        _fail("runtime capability fact field set changed")
    nonnegative = (
        "clone3_probe_errno",
        "pidfd_send_signal_probe_errno",
        "execveat_probe_errno",
        "uid",
        "gid",
        "effective_capability_mask",
    )
    if any(type(document.get(key)) is not int or document[key] < 0 for key in nonnegative):
        _fail("runtime capability numeric fact changed")
    if not (
        document.get("schema") == "acfqp.v180r12r4_runtime_capability_fact.v1"
        and type(document.get("machine_architecture")) is str
        and bool(document["machine_architecture"])
        and document.get("single_threaded") is True
        and document.get("clone3_syscall_recognized") is True
        and document.get("pidfd_send_signal_recognized") is True
        and document.get("execveat_recognized") is True
        and document.get("pidfd_wait_present") is True
        and type(document.get("landlock_abi")) is int
        and document["landlock_abi"] > 0
        and document.get("effective_capability_mask") == 0
        and document.get("admitted") is True
    ):
        _fail("runtime capability admission changed")
    return document


def service_context_capture_contract_v180r12r4() -> dict[str, Any]:
    """Bind the exact same-observation parent/runtime pair used by ordinal11."""

    parent = validate_cgroup_parent_fact_v180r12r4(
        SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT
    )
    runtime = validate_runtime_capability_fact_v180r12r4(
        SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT
    )
    capture = {
        "capture_purpose": SERVICE_CONTEXT_CAPTURE_PURPOSE,
        "cgroup_parent_fact": parent,
        "runtime_capability_fact": runtime,
        "schema": SERVICE_CONTEXT_CAPTURE_SCHEMA,
    }
    raw = canonical_json_bytes(capture) + b"\n"
    membership = parent["self_membership"].removeprefix("0::")
    parent_membership = parent["parent_path"].removeprefix(parent["mount_point"])
    if not (
        len(raw) == SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256
        and parent["controllers"] == ["cpu", "memory", "pids"]
        and parent["subtree_control"] == ["cpu", "memory", "pids"]
        and PurePosixPath(membership).parent
        == PurePosixPath(parent_membership)
        and PurePosixPath(membership).name
        == "acfqp-v180r12r4r5-freeze-capture-20260829.service"
        and PurePosixPath(membership).suffix == ".service"
        and parent["owner_uid"] == runtime["uid"]
        and parent["owner_gid"] == runtime["gid"]
    ):
        _fail("V180r12r4r5 source-bound service-context capture changed")
    return {
        "schema": "acfqp.v180r12r4r5_service_context_capture_contract.v1",
        "source_relative_path": SERVICE_CONTEXT_CAPTURE_RELATIVE_PATH,
        "capture_schema": SERVICE_CONTEXT_CAPTURE_SCHEMA,
        "capture_purpose": SERVICE_CONTEXT_CAPTURE_PURPOSE,
        "canonical_byte_count": SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT,
        "canonical_sha256": SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256,
        "cgroup_parent_fact": parent,
        "runtime_capability_fact": runtime,
        "parent_and_runtime_facts_share_one_capture_document": True,
        "capture_parent_is_cpu_enabled_app_slice_direct_service": True,
        "capture_provenance_fields": ["cgroup_parent_fact.self_membership"],
        "all_other_parent_and_runtime_fields_are_exact_identity": True,
        "production_source_self_membership_replaced_and_checked_at_t1_t2_t3": (
            True
        ),
        "measurement_root_enabled_controllers": ["memory", "pids"],
    }


def campaign_measurement_attempt_identity_contract_v180r12r4() -> dict[str, Any]:
    """Return the registered, six-authority attempt-ID formula without issuing it."""

    return {
        "schema": "acfqp.v180r12r4_campaign_measurement_attempt_identity_contract.v1",
        "attempt_schema": CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA,
        "attempt_domain": CAMPAIGN_MEASUREMENT_ATTEMPT_DOMAIN,
        "domain_registry_key": "campaign_measurement_attempt",
        "domain_registry_value": domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4[
            "campaign_measurement_attempt"
        ],
        "payload_fields": list(CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS),
        "identity_input_fields": list(
            CAMPAIGN_MEASUREMENT_ATTEMPT_IDENTITY_INPUT_FIELDS
        ),
        "identity_input_count": 6,
        "derive_api": "derive_campaign_measurement_attempt_id_v180r12r4",
        "derive_api_is_registry_implementation": (
            domains.derive_campaign_measurement_attempt_id_v180r12r4.__module__
            == domains.__name__
        ),
        "content_id_formula": "SHA256(DOMAIN_UTF8 || NUL || CANONICAL_JSON_PAYLOAD)",
        "cgroup_runtime_and_transport_facts_excluded": True,
        "outcome_identity_issued": False,
    }


def semantic_hash_counter_scope_contract_v180r12r4() -> dict[str, Any]:
    """Bound the 137-count metric to the explicit semantic operation manifest."""

    return {
        "schema": "acfqp.v180r12r4_semantic_hash_counter_scope.v1",
        "counter_path": "common.hash_invocations",
        "counted_operation_family": "SEMANTIC_HASH",
        "counted_operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS),
        "counted_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "excluded_instrumentation_classes": list(
            SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES
        ),
        "all_evidence_receipt_and_support_document_content_ids_excluded": True,
        "all_evidence_receipt_and_support_document_canonicalization_excluded": True,
        "all_evidence_and_support_sha_fields_excluded": True,
        "ipc_journal_ledger_and_prelaunch_hashing_excluded": True,
        "unmanifested_semantic_hash_site_permitted": False,
        "instrumentation_memory_inside_measured_children_remains_in_cgroup_peak": (
            True
        ),
    }


def _read_source_fact(relative_path: str) -> dict[str, Any]:
    path = _ROOT / relative_path
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r2 evidence-freeze source is unreadable"
        ) from error
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = V180R12R2_EVIDENCE_SOURCE_BYTE_COUNT
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                _fail("V180r12r2 evidence-freeze source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V180r12r2 evidence-freeze source exceeded its exact size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    fact = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    if not (
        stat.S_ISREG(before.st_mode)
        and before.st_nlink == 1
        and fact(before) == fact(after)
        and len(raw) == V180R12R2_EVIDENCE_SOURCE_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == V180R12R2_EVIDENCE_SOURCE_SHA256
    ):
        _fail("V180r12r2 evidence-freeze source identity changed")
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_commit_id": V180R12R2_EVIDENCE_COMMIT_ID,
        "git_tree_id": V180R12R2_EVIDENCE_TREE_ID,
    }


def _predecessor_evidence_contract() -> dict[str, Any]:
    frozen = predecessor_evidence.freeze_ten_terminal_aggregation_production_evidence_v180r12r2()
    terminal = frozen.terminal_document()
    verification = frozen.verification_document()
    retained = [
        {
            "role": role,
            "relative_path": relative_path,
            "identity_field": identity_field,
            "content_id": identity,
            "byte_count": byte_count,
            "sha256": sha256,
        }
        for role, relative_path, identity_field, identity, byte_count, sha256 in (
            frozen.retained_file_facts
        )
    ]
    by_role = {row["role"]: row for row in retained}
    if not (
        frozen.production_aggregation_bundle_id
        == V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID
        and frozen.verification_id == V180R12R2_VERIFICATION_ID
        and frozen.verification_bytes == frozen.replay_bytes
        and terminal.get("aggregation_protocol_id") == V180R12R2_AGGREGATION_PROTOCOL_ID
        and terminal.get("execution_authorization_id")
        == V180R12R2_EXECUTION_AUTHORIZATION_ID
        and verification.get("aggregation_protocol_id")
        == V180R12R2_AGGREGATION_PROTOCOL_ID
        and verification.get("execution_authorization_id")
        == V180R12R2_EXECUTION_AUTHORIZATION_ID
        and terminal.get("production_aggregation_bundle_id")
        == V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID
        and verification.get("production_aggregation_bundle_id")
        == V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID
        and verification.get("verification_id") == V180R12R2_VERIFICATION_ID
        and terminal.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and verification.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and terminal.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and verification.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and terminal.get("occurrence_shared_resource_receipt_count")
        == PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        and terminal.get("campaign_scope_authoritative_receipt_count")
        == PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        and terminal.get("campaign_scope_structural_obligation_count")
        == PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and terminal.get("total_authoritative_shared_resource_receipt_count")
        == PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        and terminal.get("source_verification_receipt_count") == 5
        and terminal.get("route_component_chain_receipt_count") == 12
        and terminal.get("terminal_receipt_count") == 10
        and terminal.get("all_five_source_independent_verifiers_replayed") is True
        and terminal.get(
            "all_ten_occurrence_shared_resource_receipt_sets_present"
        )
        is True
        and terminal.get("all_twelve_route_component_chains_present") is True
        and terminal.get("producer_bundle_independently_replayed") is False
        and type(terminal.get("terminal_shared_resource_receipt_sets")) is list
        and len(terminal["terminal_shared_resource_receipt_sets"]) == 10
        and terminal.get("v180r7r1_construction_axis_receipt_count") == 1
        and verification.get("occurrence_shared_resource_receipt_count")
        == PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        and verification.get("campaign_scope_authoritative_receipt_count")
        == PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        and verification.get("campaign_scope_structural_obligation_count")
        == PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and verification.get("total_authoritative_shared_resource_receipt_count")
        == PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        and by_role["TERMINAL"]["byte_count"]
        == PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT
        and by_role["VERIFICATION"]["byte_count"]
        == PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT
        and by_role["TERMINAL"]["byte_count"] <= INPUT_FILE_BYTE_CAP
        and by_role["VERIFICATION"]["byte_count"] <= INPUT_FILE_BYTE_CAP
        and by_role["TERMINAL"]["byte_count"]
        + by_role["VERIFICATION"]["byte_count"]
        == PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
        and PREDECESSOR_INPUT_TOTAL_BYTE_COUNT <= INPUT_TOTAL_BYTE_CAP
    ):
        _fail("frozen V180r12r2 predecessor evidence or claim boundary changed")
    return {
        "schema": "acfqp.v180r12r2_frozen_success_input_contract.v180r12r4",
        "evidence_freeze_source_fact": _read_source_fact(
            V180R12R2_EVIDENCE_SOURCE_RELATIVE_PATH
        ),
        "aggregation_protocol_id": V180R12R2_AGGREGATION_PROTOCOL_ID,
        "execution_authorization_id": V180R12R2_EXECUTION_AUTHORIZATION_ID,
        "authorization_evidence_id": V180R12R2_AUTHORIZATION_EVIDENCE_ID,
        "production_aggregation_bundle_id": V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID,
        "verification_id": V180R12R2_VERIFICATION_ID,
        "terminal_input_fact": by_role["TERMINAL"],
        "verification_input_fact": by_role["VERIFICATION"],
        "retained_replay_fact": by_role["REPLAY"],
        "retained_file_facts": retained,
        "retained_file_fact_count": len(retained),
        "verification_and_replay_exact_bytes_equal": True,
        "producer_free_static_evidence_replay_only": True,
        "v180r12r2_producer_rerun_forbidden": True,
        "v180r12r2_verifier_rerun_forbidden": True,
        "all_five_source_independent_verifiers_replayed": True,
        "all_ten_occurrence_shared_resource_receipt_sets_present": True,
        "all_twelve_route_component_chains_present": True,
        "producer_bundle_independently_replayed": False,
        "occurrence_authoritative_receipt_count": (
            PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "campaign_authoritative_receipt_count": (
            PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "campaign_scope_structural_obligation_count": (
            PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ),
        "terminal_input_byte_count": PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT,
        "verification_input_byte_count": PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT,
        "input_total_byte_count": PREDECESSOR_INPUT_TOTAL_BYTE_COUNT,
        "source_receipt_count": 5,
        "route_component_chain_receipt_count": 12,
        "terminal_receipt_count": 10,
        "terminal_shared_resource_receipt_count": 90,
        "terminal_shared_resource_receipt_set_count": 10,
        "v180r7r1_construction_axis_receipt_count": 1,
        "campaign_scope_structural_boundary_count": 1,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "V180R12R2_WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
    }


def source_bound_runner_execution_envelope_contract_v180r12r4() -> dict[str, Any]:
    """Return the exact four-target ModuleType execution repair contract."""

    return {
        "module_type": "types.ModuleType",
        "target_order": list(SOURCE_BOUND_RUNNER_TARGET_ORDER),
        "target_rows": [
            {"target": target, "module_name": module_name}
            for target, module_name in SOURCE_BOUND_RUNNER_MODULE_ROWS
        ],
        "exact_metadata_fields": list(
            SOURCE_BOUND_RUNNER_MODULE_METADATA_FIELDS
        ),
        "registered_before_runner_exec": True,
        "registration_spans_exec_entrypoint_and_postchecks": True,
        "preexisting_registration_fails_before_mutation": True,
        "preexisting_registration_is_preserved": True,
        "replaced_deleted_or_metadata_drifted_registration_fails": True,
        "registration_removed_after_postchecks_on_success_or_failure": True,
        "runner_module_registration_leak_forbidden": True,
        "runner_primary_error_precedes_registration_secondary": True,
    }


def _read_failed_dispatch_freeze_source_fact_v180r12r4() -> dict[str, Any]:
    path = _ROOT / V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r3 failure-freeze source is unreadable"
        ) from error
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = V180R12R3_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                _fail("V180r12r3 failure-freeze source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V180r12r3 failure-freeze source exceeded its exact size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    stable = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_uid,
        row.st_gid,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    git_blob_id = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()
    if not (
        stat.S_ISREG(before.st_mode)
        and stat.S_IMODE(before.st_mode) == 0o644
        and before.st_nlink == 1
        and stable(before) == stable(after)
        and len(raw) == V180R12R3_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == V180R12R3_FAILURE_FREEZE_SOURCE_SHA256
        and git_blob_id == V180R12R3_FAILURE_FREEZE_GIT_BLOB_ID
    ):
        _fail("V180r12r3 failure-freeze source byte identity changed")
    return {
        "relative_path": V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_commit_id": V180R12R3_FAILURE_FREEZE_COMMIT_ID,
        "git_tree_id": V180R12R3_FAILURE_FREEZE_TREE_ID,
        "git_blob_id": git_blob_id,
    }


def failed_dispatch_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Replay the retained pre-scientific V180r12r3 dispatch failure."""

    failure_freeze_source_fact = (
        _read_failed_dispatch_freeze_source_fact_v180r12r4()
    )
    failure_freeze_source = Path(failed_dispatch_predecessor.__file__).resolve()
    expected_failure_freeze_source = (
        _ROOT / V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    expected_failure_base = (_ROOT / ".tmp" / "exact-freeze").resolve()
    if not (
        failure_freeze_source == expected_failure_freeze_source
        and failure_freeze_source.parents[2] == _ROOT.resolve()
        and Path(failed_dispatch_predecessor._BASE).resolve()
        == expected_failure_base
        and tuple(failed_dispatch_predecessor._RETAINED_FILE_FACTS)
        == V180R12R3_FAILED_RETAINED_FILE_FACT_ROWS
        and frozenset(failed_dispatch_predecessor._PRELAUNCH_EXACT_ENTRIES)
        == frozenset(V180R12R3_FAILED_PRELAUNCH_EXACT_ENTRIES)
        and tuple(failed_dispatch_predecessor._REQUIRED_ABSENT_PATHS)
        == V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS
        and failed_dispatch_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R3_FAILED_CAMPAIGN_ATTEMPT_ID
        and failed_dispatch_predecessor.EXPECTED_LAUNCH_ATTEMPT_ID
        == V180R12R3_FAILED_LAUNCH_ATTEMPT_ID
        and failed_dispatch_predecessor.EXPECTED_LAUNCH_FAILURE_ID
        == V180R12R3_FAILED_LAUNCH_FAILURE_ID
        and failed_dispatch_predecessor.EXPECTED_MATERIALIZATION_TERMINAL_ID
        == V180R12R3_FAILED_MATERIALIZATION_TERMINAL_ID
        and failed_dispatch_predecessor.EXPECTED_LAUNCH_RULE_ID
        == V180R12R3_FAILED_LAUNCH_RULE_ID
    ):
        _fail("frozen V180r12r3 failure-freeze source authority changed")
    frozen = failed_dispatch_predecessor.load_frozen_campaign_measurement_prelaunch_failure_v180r12r3()
    attempt = frozen.launch_attempt_document()
    failure = frozen.launch_failure_document()
    if not (
        frozen.launch_attempt_id == V180R12R3_FAILED_LAUNCH_ATTEMPT_ID
        and len(frozen.launch_attempt_bytes)
        == V180R12R3_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT
        and hashlib.sha256(frozen.launch_attempt_bytes).hexdigest()
        == V180R12R3_FAILED_LAUNCH_ATTEMPT_SHA256
        and frozen.launch_failure_id == V180R12R3_FAILED_LAUNCH_FAILURE_ID
        and len(frozen.launch_failure_bytes)
        == V180R12R3_FAILED_LAUNCH_FAILURE_BYTE_COUNT
        and hashlib.sha256(frozen.launch_failure_bytes).hexdigest()
        == V180R12R3_FAILED_LAUNCH_FAILURE_SHA256
        and attempt.get("scientific_occurrence_started") is False
        and failure.get("campaign_actual_measurement") is False
        and failure.get("authorized_child_measurement_execution_completed")
        is False
        and failure.get("attempt_lock_preserved") is True
        and failure.get("same_target_identity_rerun_forbidden") is True
        and failure.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and failure.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and failure.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and failure.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and failure.get("official_execution_allowed") is False
        and failure.get("child_stderr", {}).get("byte_count")
        == V180R12R3_FAILED_CHILD_STDERR_BYTE_COUNT
        and failure.get("child_stderr", {}).get("sha256")
        == V180R12R3_FAILED_CHILD_STDERR_SHA256
        and attempt.get("materialization_terminal_id")
        == V180R12R3_FAILED_MATERIALIZATION_TERMINAL_ID
        and attempt.get("materialization_terminal_byte_count") == 5_477
        and attempt.get("materialization_terminal_sha256")
        == "208999305db03091ca744e3e0ab758647cdcc3c3aaf59be48acf854dabc24537"
        and attempt.get("launch_manifest_sha256")
        == "3d0fdcd2719168427bbb066ade57721c62262c9e1ce4752850f97a051314c314"
        and attempt.get("launch_rule_id")
        == failure.get("launch_rule_id")
        == V180R12R3_FAILED_LAUNCH_RULE_ID
    ):
        _fail("frozen V180r12r3 failed dispatch lineage changed")
    return {
        "schema": "acfqp.v180r12r3_failed_dispatch_repair_lineage.v180r12r4",
        "failure_freeze_source_relative_path": (
            V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_fact": failure_freeze_source_fact,
        "campaign_attempt_id": V180R12R3_FAILED_CAMPAIGN_ATTEMPT_ID,
        "materialization_terminal_id": (
            V180R12R3_FAILED_MATERIALIZATION_TERMINAL_ID
        ),
        "materialization_terminal_byte_count": 5_477,
        "materialization_terminal_sha256": (
            "208999305db03091ca744e3e0ab758647cdcc3c3aaf59be48acf854dabc24537"
        ),
        "launch_manifest_sha256": (
            "3d0fdcd2719168427bbb066ade57721c62262c9e1ce4752850f97a051314c314"
        ),
        "launch_rule_id": V180R12R3_FAILED_LAUNCH_RULE_ID,
        "launch_attempt_id": frozen.launch_attempt_id,
        "launch_attempt_byte_count": len(frozen.launch_attempt_bytes),
        "launch_attempt_sha256": hashlib.sha256(
            frozen.launch_attempt_bytes
        ).hexdigest(),
        "launch_failure_id": frozen.launch_failure_id,
        "launch_failure_byte_count": len(frozen.launch_failure_bytes),
        "launch_failure_sha256": hashlib.sha256(
            frozen.launch_failure_bytes
        ).hexdigest(),
        "child_stderr_byte_count": V180R12R3_FAILED_CHILD_STDERR_BYTE_COUNT,
        "child_stderr_sha256": V180R12R3_FAILED_CHILD_STDERR_SHA256,
        "retained_file_facts": [
            {
                "relative_path": relative_path,
                "byte_count": byte_count,
                "sha256": sha256,
            }
            for relative_path, byte_count, sha256
            in V180R12R3_FAILED_RETAINED_FILE_FACT_ROWS
        ],
        "retained_file_fact_count": len(
            V180R12R3_FAILED_RETAINED_FILE_FACT_ROWS
        ),
        "prelaunch_exact_entries": list(
            V180R12R3_FAILED_PRELAUNCH_EXACT_ENTRIES
        ),
        "prelaunch_exact_entry_count": len(
            V180R12R3_FAILED_PRELAUNCH_EXACT_ENTRIES
        ),
        "required_absent_successor_paths": list(
            V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS
        ),
        "required_absent_successor_path_count": len(
            V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS
        ),
        "all_required_successor_paths_absent_at_failure_freeze": True,
        "measurement_cgroup_parent_path": (
            V180R12R3_FAILED_MEASUREMENT_CGROUP_PARENT_PATH
        ),
        "measurement_cgroup_root_name": (
            V180R12R3_FAILED_MEASUREMENT_CGROUP_ROOT_NAME
        ),
        "measurement_cgroup_absent_at_failure_freeze": True,
        "primary_failure_type": "AttributeError",
        "primary_failure_boundary": (
            "PRECOMPILED_RUNNER_MODULE_NOT_REGISTERED_IN_SYS_MODULES"
        ),
        "secondary_observation": "SIX_PROCESS_GIT_CONTRACT_INCOMPLETE",
        "scientific_attempt_record_present": False,
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
        "measurement_cgroup_created": False,
        "same_campaign_attempt_rerun_forbidden": True,
        "same_launch_attempt_rerun_forbidden": True,
        "repair_changes_scientific_scope_or_denominators": False,
        "fresh_successor_identity_required": True,
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "failure_freeze_artifact_base_is_repository_root_tmp_exact_freeze": True,
        "runtime_replay_is_pre_scientific_prereg_authority": True,
        "runtime_replay_precedes_successor_campaign_attempt_publication": True,
        "retained_artifact_absence_and_cgroup_reads_are_campaign_actual_"
        "measurement": False,
        "retained_artifact_absence_and_cgroup_reads_are_in_five_measured_"
        "input_read_chains": False,
        "retained_artifact_absence_and_cgroup_reads_are_in_nine_campaign_"
        "paths": False,
        "retained_artifact_absence_and_cgroup_reads_are_trusted_prereg_"
        "authority_replay": True,
    }


def _read_failed_external_replay_freeze_source_fact_v180r12r4() -> dict[str, Any]:
    path = _ROOT / V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r3r1 failure-freeze source is unreadable"
        ) from error
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = V180R12R3R1_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                _fail("V180r12r3r1 failure-freeze source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V180r12r3r1 failure-freeze source exceeded its exact size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    stable = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_uid,
        row.st_gid,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    git_blob_id = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()
    if not (
        stat.S_ISREG(before.st_mode)
        and stat.S_IMODE(before.st_mode) == 0o644
        and before.st_nlink == 1
        and stable(before) == stable(after)
        and len(raw) == V180R12R3R1_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == V180R12R3R1_FAILURE_FREEZE_SOURCE_SHA256
        and git_blob_id == V180R12R3R1_FAILURE_FREEZE_GIT_BLOB_ID
    ):
        _fail("V180r12r3r1 failure-freeze source byte identity changed")
    return {
        "relative_path": V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_commit_id": V180R12R3R1_FAILURE_FREEZE_COMMIT_ID,
        "git_tree_id": V180R12R3R1_FAILURE_FREEZE_TREE_ID,
        "git_blob_id": git_blob_id,
    }


def failed_external_replay_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Replay the immediate pre-scientific V180r12r3r1 source-bound failure."""

    failure_freeze_source_fact = (
        _read_failed_external_replay_freeze_source_fact_v180r12r4()
    )
    failure_freeze_source = Path(
        failed_external_replay_predecessor.__file__
    ).resolve()
    expected_failure_freeze_source = (
        _ROOT / V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    expected_failure_base = (_ROOT / ".tmp" / "exact-freeze").resolve()
    if not (
        failure_freeze_source == expected_failure_freeze_source
        and failure_freeze_source.parents[2] == _ROOT.resolve()
        and Path(failed_external_replay_predecessor._BASE).resolve()
        == expected_failure_base
        and tuple(failed_external_replay_predecessor._RETAINED_FILE_FACTS)
        == V180R12R3R1_FAILED_RETAINED_FILE_FACT_ROWS
        and frozenset(failed_external_replay_predecessor._PRELAUNCH_EXACT_ENTRIES)
        == frozenset(V180R12R3R1_FAILED_PRELAUNCH_EXACT_ENTRIES)
        and tuple(failed_external_replay_predecessor._REQUIRED_ABSENT_PATHS)
        == V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS
        and failed_external_replay_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R3R1_FAILED_CAMPAIGN_ATTEMPT_ID
        and failed_external_replay_predecessor.EXPECTED_LAUNCH_ATTEMPT_ID
        == V180R12R3R1_FAILED_LAUNCH_ATTEMPT_ID
        and failed_external_replay_predecessor.EXPECTED_LAUNCH_FAILURE_ID
        == V180R12R3R1_FAILED_LAUNCH_FAILURE_ID
        and failed_external_replay_predecessor.EXPECTED_MATERIALIZATION_TERMINAL_ID
        == V180R12R3R1_FAILED_MATERIALIZATION_TERMINAL_ID
        and failed_external_replay_predecessor.EXPECTED_LAUNCH_RULE_ID
        == V180R12R3R1_FAILED_LAUNCH_RULE_ID
    ):
        _fail("frozen V180r12r3r1 failure-freeze source authority changed")
    failure_loader = getattr(
        failed_external_replay_predecessor,
        "load_frozen_campaign_measurement_prelaunch_failure_v180r12r3r1",
    )
    frozen = failure_loader()
    attempt = frozen.launch_attempt_document()
    failure = frozen.launch_failure_document()
    if not (
        frozen.launch_attempt_id == V180R12R3R1_FAILED_LAUNCH_ATTEMPT_ID
        and len(frozen.launch_attempt_bytes)
        == V180R12R3R1_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT
        and hashlib.sha256(frozen.launch_attempt_bytes).hexdigest()
        == V180R12R3R1_FAILED_LAUNCH_ATTEMPT_SHA256
        and frozen.launch_failure_id == V180R12R3R1_FAILED_LAUNCH_FAILURE_ID
        and len(frozen.launch_failure_bytes)
        == V180R12R3R1_FAILED_LAUNCH_FAILURE_BYTE_COUNT
        and hashlib.sha256(frozen.launch_failure_bytes).hexdigest()
        == V180R12R3R1_FAILED_LAUNCH_FAILURE_SHA256
        and attempt.get("scientific_occurrence_started") is False
        and attempt.get("campaign_actual_measurement") is False
        and failure.get("campaign_actual_measurement") is False
        and failure.get("authorized_child_measurement_execution_completed")
        is False
        and failure.get("attempt_lock_preserved") is True
        and failure.get("same_target_identity_rerun_forbidden") is True
        and failure.get("failure_type")
        == "V180r12r3r1PrelaunchLaunchError"
        and failure.get("failure_message")
        == "source-bound child did not reach its exact durable success state"
        and failure.get("return_code") == 1
        and failure.get("timed_out") is False
        and failure.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and failure.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and failure.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and failure.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and failure.get("official_execution_allowed") is False
        and failure.get("child_stderr", {}).get("byte_count")
        == V180R12R3R1_FAILED_CHILD_STDERR_BYTE_COUNT
        and failure.get("child_stderr", {}).get("sha256")
        == V180R12R3R1_FAILED_CHILD_STDERR_SHA256
        and attempt.get("materialization_terminal_id")
        == V180R12R3R1_FAILED_MATERIALIZATION_TERMINAL_ID
        and attempt.get("materialization_terminal_byte_count") == 5_503
        and attempt.get("materialization_terminal_sha256")
        == "ceb58f7b09f1a1ac638f0f3e44c7919d1f0a3fde4a8b5172ee8d719755235cb6"
        and attempt.get("launch_manifest_sha256")
        == "e8843ae4b8194b65179de4ccb59133fa6791e6ad8817de28699349c6645e9766"
        and attempt.get("launch_rule_id")
        == failure.get("launch_rule_id")
        == V180R12R3R1_FAILED_LAUNCH_RULE_ID
    ):
        _fail("frozen V180r12r3r1 failed external replay lineage changed")
    return {
        "schema": (
            "acfqp.v180r12r3r1_failed_external_replay_repair_lineage."
            "v180r12r4"
        ),
        "failure_freeze_source_relative_path": (
            V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_fact": failure_freeze_source_fact,
        "campaign_attempt_id": V180R12R3R1_FAILED_CAMPAIGN_ATTEMPT_ID,
        "materialization_terminal_id": (
            V180R12R3R1_FAILED_MATERIALIZATION_TERMINAL_ID
        ),
        "materialization_terminal_byte_count": 5_503,
        "materialization_terminal_sha256": (
            "ceb58f7b09f1a1ac638f0f3e44c7919d1f0a3fde4a8b5172ee8d719755235cb6"
        ),
        "launch_manifest_sha256": (
            "e8843ae4b8194b65179de4ccb59133fa6791e6ad8817de28699349c6645e9766"
        ),
        "launch_rule_id": V180R12R3R1_FAILED_LAUNCH_RULE_ID,
        "launch_attempt_id": frozen.launch_attempt_id,
        "launch_attempt_byte_count": len(frozen.launch_attempt_bytes),
        "launch_attempt_sha256": hashlib.sha256(
            frozen.launch_attempt_bytes
        ).hexdigest(),
        "launch_failure_id": frozen.launch_failure_id,
        "launch_failure_byte_count": len(frozen.launch_failure_bytes),
        "launch_failure_sha256": hashlib.sha256(
            frozen.launch_failure_bytes
        ).hexdigest(),
        "child_stderr_byte_count": V180R12R3R1_FAILED_CHILD_STDERR_BYTE_COUNT,
        "child_stderr_sha256": V180R12R3R1_FAILED_CHILD_STDERR_SHA256,
        "retained_file_facts": [
            {
                "relative_path": relative_path,
                "byte_count": byte_count,
                "sha256": sha256,
            }
            for relative_path, byte_count, sha256
            in V180R12R3R1_FAILED_RETAINED_FILE_FACT_ROWS
        ],
        "retained_file_fact_count": len(
            V180R12R3R1_FAILED_RETAINED_FILE_FACT_ROWS
        ),
        "prelaunch_exact_entries": list(
            V180R12R3R1_FAILED_PRELAUNCH_EXACT_ENTRIES
        ),
        "prelaunch_exact_entry_count": len(
            V180R12R3R1_FAILED_PRELAUNCH_EXACT_ENTRIES
        ),
        "required_absent_successor_paths": list(
            V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS
        ),
        "required_absent_successor_path_count": len(
            V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS
        ),
        "all_required_successor_paths_absent_at_failure_freeze": True,
        "measurement_cgroup_parent_path": (
            V180R12R3R1_FAILED_MEASUREMENT_CGROUP_PARENT_PATH
        ),
        "measurement_cgroup_root_name": (
            V180R12R3R1_FAILED_MEASUREMENT_CGROUP_ROOT_NAME
        ),
        "measurement_cgroup_absent_at_failure_freeze": True,
        "outer_failure_type": "V180r12r3r1PrelaunchLaunchError",
        "primary_failure_type": "V180R12R3R1RuntimeError",
        "primary_failure_boundary": "EXTERNAL_REPLAY_DOCUMENT_BYTE_JOIN_CHANGED",
        "scientific_attempt_record_present": False,
        "scientific_occurrence_started": False,
        "campaign_actual_measurement": False,
        "measurement_cgroup_created": False,
        "same_campaign_attempt_rerun_forbidden": True,
        "same_launch_attempt_rerun_forbidden": True,
        "repair_scope": (
            "AUTHORIZATION_EVIDENCE_WRAPPER_SOURCE_FACT_NORMALIZATION_ONLY"
        ),
        "repair_changes_scientific_scope_or_denominators": False,
        "inherited_v180r12r3_dispatch_repair_preserved": True,
        "source_bound_authorization_replay_must_use_c_pre_normalized_sources": True,
        "raw_post_literal_wrapper_authorization_replay_forbidden": True,
        "fresh_successor_identity_required": True,
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "failure_freeze_artifact_base_is_repository_root_tmp_exact_freeze": True,
        "runtime_replay_is_pre_scientific_prereg_authority": True,
        "runtime_replay_precedes_successor_campaign_attempt_publication": True,
        "retained_artifact_absence_and_cgroup_reads_are_campaign_actual_"
        "measurement": False,
        "retained_artifact_absence_and_cgroup_reads_are_in_five_measured_"
        "input_read_chains": False,
        "retained_artifact_absence_and_cgroup_reads_are_in_nine_campaign_"
        "paths": False,
        "retained_artifact_absence_and_cgroup_reads_are_trusted_prereg_"
        "authority_replay": True,
    }


def _read_failed_scientific_birth_freeze_source_fact_v180r12r4(
) -> dict[str, Any]:
    path = _ROOT / V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        raise CampaignMeasurementProtocolV180R12R4Error(
            "V180r12r3r2 failure-freeze source is unreadable"
        ) from error
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        remaining = V180R12R3R2_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                _fail("V180r12r3r2 failure-freeze source ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("V180r12r3r2 failure-freeze source exceeded its exact size")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    raw = b"".join(chunks)
    stable = lambda row: (  # noqa: E731
        row.st_dev,
        row.st_ino,
        row.st_mode,
        row.st_nlink,
        row.st_uid,
        row.st_gid,
        row.st_size,
        row.st_mtime_ns,
        row.st_ctime_ns,
    )
    git_blob_id = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    ).hexdigest()
    if not (
        stat.S_ISREG(before.st_mode)
        and stat.S_IMODE(before.st_mode) == 0o644
        and before.st_nlink == 1
        and stable(before) == stable(after)
        and len(raw) == V180R12R3R2_FAILURE_FREEZE_SOURCE_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest()
        == V180R12R3R2_FAILURE_FREEZE_SOURCE_SHA256
        and git_blob_id == V180R12R3R2_FAILURE_FREEZE_GIT_BLOB_ID
    ):
        _fail("V180r12r3r2 failure-freeze source byte identity changed")
    return {
        "relative_path": V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_commit_id": V180R12R3R2_FAILURE_FREEZE_COMMIT_ID,
        "git_tree_id": V180R12R3R2_FAILURE_FREEZE_TREE_ID,
        "git_blob_id": git_blob_id,
    }


def failed_scientific_birth_repair_lineage_contract_v180r12r4(
) -> dict[str, Any]:
    """Replay the consumed V180r12r3r2 scientific birth failure."""

    source_fact = _read_failed_scientific_birth_freeze_source_fact_v180r12r4()
    failure_freeze_source = Path(
        failed_scientific_birth_predecessor.__file__
    ).resolve()
    expected_failure_freeze_source = (
        _ROOT / V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    expected_failure_base = (_ROOT / ".tmp" / "exact-freeze").resolve()
    if not (
        failure_freeze_source == expected_failure_freeze_source
        and failure_freeze_source.parents[2] == _ROOT.resolve()
        and Path(failed_scientific_birth_predecessor._BASE).resolve()
        == expected_failure_base
        and failed_scientific_birth_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_ID
        and failed_scientific_birth_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
        == V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_RECORD_ID
        and failed_scientific_birth_predecessor.EXPECTED_LAUNCH_ATTEMPT_ID
        == V180R12R3R2_FAILED_LAUNCH_ATTEMPT_ID
        and failed_scientific_birth_predecessor.EXPECTED_LAUNCH_FAILURE_ID
        == V180R12R3R2_FAILED_LAUNCH_FAILURE_ID
        and failed_scientific_birth_predecessor.EXPECTED_FAILURE_STATE_ID
        == V180R12R3R2_FAILED_FAILURE_STATE_ID
        and failed_scientific_birth_predecessor.EXPECTED_EVENT_IDS
        == V180R12R3R2_FAILED_EVENT_IDS
        and failed_scientific_birth_predecessor.EXPECTED_RETAINED_EVENT_COUNT == 2
        and failed_scientific_birth_predecessor.EXPECTED_SUCCESS_EVENT_COUNT
        == SUCCESS_EXACT_EVENT_COUNT
        and failed_scientific_birth_predecessor.FAILURE_CLAIM_BOUNDARY
        == V180R12R3R2_FAILURE_CLAIM_BOUNDARY
    ):
        _fail("frozen V180r12r3r2 scientific failure authority changed")
    failure_loader = getattr(
        failed_scientific_birth_predecessor,
        "load_frozen_campaign_measurement_failure_v180r12r3r2",
    )
    frozen = failure_loader()
    launch_attempt = frozen.launch_attempt_document()
    launch_failure = frozen.launch_failure_document()
    scientific_attempt = frozen.scientific_attempt_document()
    measurement_failure = frozen.measurement_failure_document()
    event_zero, event_one = frozen.event_documents()
    if not (
        frozen.campaign_attempt_id == V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_ID
        and frozen.campaign_attempt_record_id
        == V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_RECORD_ID
        and frozen.launch_attempt_id == V180R12R3R2_FAILED_LAUNCH_ATTEMPT_ID
        and frozen.launch_failure_id == V180R12R3R2_FAILED_LAUNCH_FAILURE_ID
        and frozen.failure_state_id == V180R12R3R2_FAILED_FAILURE_STATE_ID
        and frozen.event_ids == V180R12R3R2_FAILED_EVENT_IDS
        and launch_attempt.get("scientific_occurrence_started") is False
        and launch_attempt.get("campaign_actual_measurement") is False
        and launch_attempt.get("authorized_child_measurement_execution_attempted")
        is True
        and launch_failure.get("authorized_child_measurement_execution_completed")
        is False
        and launch_failure.get("producer_free_verification_attempted") is False
        and scientific_attempt.get("one_shot_attempt_opened") is True
        and scientific_attempt.get("attempt_id") == frozen.campaign_attempt_id
        and event_zero.get("sequence") == 0
        and event_zero.get("event_kind") == "ATTEMPT_OPEN"
        and event_one.get("sequence") == 1
        and event_one.get("event_kind") == "PROCESS_BIRTH_INTENT"
        and event_one.get("previous_event_id") == frozen.event_ids[0]
        and measurement_failure.get("failure_code")
        == "SUPERVISOR_BIRTH_FAILURE"
        and measurement_failure.get("phase") == "STAGE"
        and measurement_failure.get("last_event_id") == frozen.event_ids[1]
        and measurement_failure.get("completed_event_count") == 2
        and measurement_failure.get("counter_records_issued") is False
        and measurement_failure.get("successful_ledger_claimed") is False
        and measurement_failure.get("same_identity_rerun_forbidden") is True
        and measurement_failure.get("process_may_remain") is False
    ):
        _fail("frozen V180r12r3r2 scientific failure lineage changed")
    return {
        "schema": (
            "acfqp.v180r12r3r2_scientific_birth_failure_repair_lineage."
            "v180r12r4"
        ),
        "failure_freeze_source_relative_path": (
            V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_fact": source_fact,
        "campaign_attempt_id": frozen.campaign_attempt_id,
        "campaign_attempt_record_id": frozen.campaign_attempt_record_id,
        "launch_attempt_id": frozen.launch_attempt_id,
        "launch_failure_id": frozen.launch_failure_id,
        "failure_state_id": frozen.failure_state_id,
        "event_ids": list(frozen.event_ids),
        "retained_event_count": 2,
        "success_event_count": SUCCESS_EXACT_EVENT_COUNT,
        "outer_launch_attempt_scientific_occurrence_started": False,
        "scientific_attempt_record_present": True,
        "scientific_attempt_opened": True,
        "scientific_occurrence_started": True,
        "durable_scientific_event_prefix_present": True,
        "durable_event_kinds": ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT"],
        "campaign_counter_records_issued": False,
        "successful_ledger_claimed": False,
        "producer_free_verification_attempted": False,
        "measurement_cgroup_topology_creation_returned_before_birth_intent": True,
        "measurement_cgroup_parent_path": (
            V180R12R3R2_FAILED_MEASUREMENT_CGROUP_PARENT_PATH
        ),
        "measurement_cgroup_root_name": (
            V180R12R3R2_FAILED_MEASUREMENT_CGROUP_ROOT_NAME
        ),
        "measurement_cgroup_absent_at_failure_freeze": True,
        "primary_failure_code": "SUPERVISOR_BIRTH_FAILURE",
        "primary_failure_phase": "STAGE",
        "primary_failure_boundary": V180R12R3R2_FAILURE_CLAIM_BOUNDARY,
        "exact_failing_syscall_proven": False,
        "process_may_remain": False,
        "same_campaign_attempt_rerun_forbidden": True,
        "same_launch_attempt_rerun_forbidden": True,
        "fresh_successor_identity_required": True,
        "repair_scope": V180R12R3R2_REPAIR_SCOPE,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
        "inherited_v180r12r3_dispatch_repair_preserved": True,
        "inherited_v180r12r3r1_external_replay_repair_preserved": True,
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "failure_freeze_artifact_base_is_repository_root_tmp_exact_freeze": True,
        "runtime_replay_precedes_successor_campaign_attempt_publication": True,
        "retained_failure_replay_is_prelaunch_authority_not_fresh_"
        "campaign_measurement": True,
    }


def failed_ordinal8_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind the consumed ordinal8 failure as historical repair lineage."""

    source = Path(failed_ordinal8_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal8_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R2_FAILED_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal8_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
        == V180R12R4R2_FAILED_CAMPAIGN_FAILURE_ID
        and failed_ordinal8_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R2_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal8_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R2_FAILED_OUTER_SERVICE_FAILURE_ID
    ):
        _fail("frozen ordinal8 failure authority changed")
    contract = (
        failed_ordinal8_predecessor.freeze_ordinal8_failure_v180r12r4r2()
        .to_contract()
    )
    required_keys = {
        "schema",
        "campaign_attempt_id",
        "campaign_attempt_record_id",
        "campaign_failure_id",
        "event_ids",
        "event_kinds",
        "completed_event_count",
        "materialization_terminal_id",
        "outer_service_launch_attempt_id",
        "outer_service_failure_id",
        "inner_launch_attempt_id",
        "inner_launch_failure_id",
        "phase",
        "historical_failure_code",
        "diagnosed_failure_class",
        "historical_failure_code_misclassified",
        "launch_child_created",
        "outer_service_unit_ownership_acquired",
        "full_cgroup_conformance",
        "counter_records_issued",
        "work_vectors_issued",
        "comparison_vectors_issued",
        "gate_statuses",
        "official_execution_allowed",
        "same_identity_rerun_forbidden",
        "terminal_present",
        "independent_replay_present",
        "cgroup_parent_fact",
        "historical_parent_contract",
        "parent_contract_mismatch_fields",
        "full_property_diagnostic_recorded",
    }
    expected_gates = {
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
    }
    if not (
        set(contract) == required_keys
        and contract["schema"]
        == "acfqp.v180r12r4r2_ordinal8_failure_freeze.v1"
        and contract["campaign_attempt_id"]
        == V180R12R4R2_FAILED_CAMPAIGN_ATTEMPT_ID
        and contract["campaign_failure_id"]
        == V180R12R4R2_FAILED_CAMPAIGN_FAILURE_ID
        and contract["inner_launch_failure_id"]
        == V180R12R4R2_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract["outer_service_failure_id"]
        == V180R12R4R2_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract["event_kinds"] == ["ATTEMPT_OPEN"]
        and contract["completed_event_count"] == 1
        and contract["phase"] == "STAGE"
        and contract["historical_failure_code"] == "SUPERVISOR_BIRTH_FAILURE"
        and contract["diagnosed_failure_class"]
        == "CGROUP_TOPOLOGY_CONFORMANCE_FAILURE"
        and contract["historical_failure_code_misclassified"] is True
        and contract["launch_child_created"] is False
        and contract["outer_service_unit_ownership_acquired"] is True
        and contract["full_cgroup_conformance"] is False
        and contract["counter_records_issued"] is False
        and contract["work_vectors_issued"] is False
        and contract["comparison_vectors_issued"] is False
        and contract["gate_statuses"] == expected_gates
        and contract["official_execution_allowed"] is False
        and contract["same_identity_rerun_forbidden"] is True
        and contract["terminal_present"] is False
        and contract["independent_replay_present"] is False
        and contract["cgroup_parent_fact"]["controllers"]
        == ["cpu", "memory", "pids"]
        and contract["cgroup_parent_fact"]["subtree_control"]
        == ["cpu", "memory", "pids"]
        and contract["historical_parent_contract"]
        == {
            "controllers": ["memory", "pids"],
            "subtree_control": ["memory", "pids"],
        }
        and contract["parent_contract_mismatch_fields"]
        == ["controllers", "subtree_control"]
        and contract["full_property_diagnostic_recorded"] is False
    ):
        _fail("frozen ordinal8 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "repair_scope": V180R12R4R3_REPAIR_SCOPE,
        "fresh_successor_identity_required": True,
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def failed_ordinal9_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind consumed ordinal9 as retained historical lineage."""

    source = Path(failed_ordinal9_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal9_predecessor.ORDINAL9_FAILURE_FREEZE_ID
        == V180R12R4R4_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal9_predecessor.EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R4_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal9_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R4_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal9_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R4_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal9_predecessor.REPAIR_SCOPE == V180R12R4R4_REPAIR_SCOPE
    ):
        _fail("frozen ordinal9 failure authority changed")
    contract = (
        failed_ordinal9_predecessor.freeze_ordinal9_failure_v180r12r4r4()
        .to_contract()
    )
    diagnostic = contract.get("source_conformance_diagnostic")
    if not (
        contract.get("schema")
        == "acfqp.v180r12r4r4_ordinal9_failure_freeze.v1"
        and contract.get("freeze_id")
        == V180R12R4R4_FAILED_PREDECESSOR_FREEZE_ID
        and contract.get("logical_campaign_attempt_id")
        == V180R12R4R4_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and contract.get("campaign_attempt_artifact_present") is False
        and contract.get("campaign_started") is False
        and contract.get("campaign_ledger_event_count") == 0
        and contract.get("inner_launch_failure_id")
        == V180R12R4R4_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract.get("outer_service_failure_id")
        == V180R12R4R4_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract.get("outer_service_unit_ownership_acquired") is True
        and contract.get("full_source_conformance") is False
        and contract.get("runtime_full_property_diagnostic_recorded") is False
        and contract.get("postmortem_full_property_diagnostic_recorded") is True
        and type(diagnostic) is dict
        and diagnostic.get("source_root_count") == 23
        and diagnostic.get("mismatch_fields") == ["mode"]
        and diagnostic.get("expected", {}).get("mode") == 0o644
        and diagnostic.get("failed_source_snapshot", {})
        .get("before", {})
        .get("mode")
        == 0o664
        and contract.get("counter_records_issued") is False
        and contract.get("work_vectors_issued") is False
        and contract.get("comparison_vectors_issued") is False
        and set(contract.get("gate_statuses", {}).values()) == {"NOT_RUN"}
        and contract.get("official_execution_allowed") is False
        and contract.get("independent_replay_present") is False
        and contract.get("identity_consumed") is True
        and contract.get("same_identity_rerun_forbidden") is True
        and contract.get("fresh_successor_identity_required") is True
        and contract.get("repair_scope") == V180R12R4R4_REPAIR_SCOPE
    ):
        _fail("frozen ordinal9 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def failed_ordinal10_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind consumed ordinal10 as the immediate pre-campaign predecessor."""

    source = Path(failed_ordinal10_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal10_predecessor.ORDINAL10_FAILURE_FREEZE_ID
        == V180R12R4R5_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal10_predecessor.EXPECTED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R5_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal10_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R5_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal10_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R5_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal10_predecessor.REPAIR_SCOPE == V180R12R4R5_REPAIR_SCOPE
    ):
        _fail("frozen ordinal10 failure authority changed")
    contract = (
        failed_ordinal10_predecessor.freeze_ordinal10_failure_v180r12r4r5()
        .to_contract()
    )
    diagnostic = contract.get("source_conformance_diagnostic")
    if not (
        contract.get("schema")
        == "acfqp.v180r12r4r5_ordinal10_failure_freeze.v1"
        and contract.get("freeze_id")
        == V180R12R4R5_FAILED_PREDECESSOR_FREEZE_ID
        and contract.get("logical_campaign_attempt_id")
        == V180R12R4R5_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and contract.get("campaign_attempt_artifact_present") is False
        and contract.get("campaign_started") is False
        and contract.get("campaign_ledger_event_count") == 0
        and contract.get("campaign_artifacts_absent") is True
        and contract.get("inner_launch_failure_id")
        == V180R12R4R5_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract.get("outer_service_failure_id")
        == V180R12R4R5_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract.get("outer_service_unit_ownership_acquired") is True
        and contract.get("prelaunch_materialization_succeeded") is True
        and contract.get("production_runtime_placement_t1_complete") is True
        and contract.get("production_runtime_placement_t2_complete") is False
        and contract.get("full_source_conformance") is True
        and contract.get("source_root_count") == 24
        and contract.get("source_conformance_mismatch_count") == 0
        and contract.get("source_conformance_cause") is None
        and type(diagnostic) is dict
        and diagnostic.get("source_root_count") == 24
        and diagnostic.get("mismatch_count") == 0
        and diagnostic.get("per_field_mismatches") == []
        and contract.get("runtime_failure_generic_cause_recorded") is True
        and contract.get("runtime_failure_property_snapshots_recorded") is False
        and contract.get("runtime_failure_per_field_mismatch_recorded") is False
        and contract.get("runtime_failure_exact_cause_dimension_recorded") is False
        and contract.get("postmortem_delegate_diagnostic_consumed") is False
        and contract.get("failure_class")
        == "PRE_ATTEMPT_CGROUP_OR_RUNTIME_CAPABILITY_FACT_DRIFT"
        and contract.get("counter_records_issued") is False
        and contract.get("work_vectors_issued") is False
        and contract.get("comparison_vectors_issued") is False
        and set(contract.get("gate_statuses", {}).values()) == {"NOT_RUN"}
        and contract.get("official_execution_allowed") is False
        and contract.get("independent_replay_present") is False
        and contract.get("identity_consumed") is True
        and contract.get("same_identity_rerun_forbidden") is True
        and contract.get("fresh_successor_identity_required") is True
        and contract.get("repair_scope") == V180R12R4R5_REPAIR_SCOPE
    ):
        _fail("frozen ordinal10 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def failed_ordinal11_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind consumed ordinal11 as retained historical lineage."""

    source = Path(failed_ordinal11_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal11_predecessor.ORDINAL11_FAILURE_FREEZE_ID
        == V180R12R4R6_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal11_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R6_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal11_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R6_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal11_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R6_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal11_predecessor.REPAIR_SCOPE
        == V180R12R4R6_REPAIR_SCOPE
    ):
        _fail("frozen ordinal11 failure authority changed")
    contract = (
        failed_ordinal11_predecessor.freeze_ordinal11_failure_v180r12r4r6()
        .to_contract()
    )
    host = contract.get("host_conformance")
    diagnostic = contract.get("topology_diagnostic")
    if not (
        contract.get("schema")
        == "acfqp.v180r12r4r6_ordinal11_failure_freeze.v1"
        and contract.get("freeze_id")
        == V180R12R4R6_FAILED_PREDECESSOR_FREEZE_ID
        and contract.get("campaign_attempt_id")
        == V180R12R4R6_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and contract.get("campaign_attempt_record_id")
        == failed_ordinal11_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
        and contract.get("campaign_failure_id")
        == failed_ordinal11_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
        and contract.get("inner_launch_failure_id")
        == V180R12R4R6_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract.get("outer_service_failure_id")
        == V180R12R4R6_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract.get("full_source_conformance") is True
        and contract.get("source_root_count") == 25
        and contract.get("full_host_conformance") is True
        and contract.get("host_conformance_mismatch_count") == 0
        and contract.get("host_conformance_cause") is None
        and type(host) is dict
        and host.get("full_host_conformance") is True
        and host.get("mismatch_count") == 0
        and host.get("mismatch_rows") == []
        and host.get("cause") is None
        and contract.get("scientific_attempt_opened") is True
        and contract.get("event_kinds") == ["ATTEMPT_OPEN"]
        and contract.get("completed_event_count") == 1
        and contract.get("full_t1_t2_conformance") is False
        and contract.get("topology_diagnostic_unit_ownership_acquired")
        is False
        and contract.get("t1_t2_same_formal_service") is True
        and contract.get("t1_t2_same_source_membership") is True
        and contract.get("t1_t2_same_service_directory") is True
        and contract.get("only_mismatch")
        == {
            "field": "t2.pid",
            "expected": failed_ordinal11_predecessor.EXPECTED_T1_PID,
            "observed": failed_ordinal11_predecessor.OBSERVED_T2_PID,
        }
        and contract.get("exact_failure_cause")
        == "T1_T2_PID_ROLE_CONFLATION"
        and contract.get("t1_process_role") == "SERVICE_ENTRY_LAUNCHER"
        and contract.get("t2_process_role") == "BOOTSTRAP_CHILD"
        and contract.get("distinct_process_roles") is True
        and contract.get("predecessor_t2_schema")
        == "acfqp.v180r12r4_production_runtime_placement_t2.v1"
        and contract.get("successor_t2_schema")
        == "acfqp.v180r12r4_production_runtime_placement_t2.v2"
        and contract.get("ordinal11_t3_present") is False
        and type(diagnostic) is dict
        and contract.get("measurement_root_created_before_failure") is True
        and contract.get("cleanup_complete") is True
        and contract.get("post_child_measurement_root_state") == "ABSENT"
        and contract.get("counter_record_count") == 0
        and contract.get("work_vector_count") == 0
        and contract.get("comparison_vector_count") == 0
        and set(contract.get("gate_statuses", {}).values()) == {"NOT_RUN"}
        and contract.get("official_execution_allowed") is False
        and contract.get("terminal_present") is False
        and contract.get("independent_replay_present") is False
        and contract.get("scientific_effect_claimed") is False
        and contract.get("identity_consumed") is True
        and contract.get("same_identity_rerun_forbidden") is True
        and contract.get("fresh_successor_identity_required") is True
        and contract.get("repair_scope") == V180R12R4R6_REPAIR_SCOPE
    ):
        _fail("frozen ordinal11 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def failed_ordinal12_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind consumed ordinal12 as retained historical lineage."""

    source = Path(failed_ordinal12_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal12_predecessor.ORDINAL12_FAILURE_FREEZE_ID
        == V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal12_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal12_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R7_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal12_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R7_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal12_predecessor.REPAIR_SCOPE
        == V180R12R4R7_REPAIR_SCOPE
    ):
        _fail("frozen ordinal12 failure authority changed")
    contract = (
        failed_ordinal12_predecessor.freeze_ordinal12_failure_v180r12r4r7()
        .to_contract()
    )
    host = contract.get("host_conformance")
    placement_t1 = contract.get("production_runtime_placement_t1")
    socket_observation = contract.get("socket_capability_observation")
    socket_cause = contract.get("socket_capability_cause")
    if not (
        contract.get("schema")
        == "acfqp.v180r12r4r7_ordinal12_failure_freeze.v1"
        and contract.get("freeze_id")
        == V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID
        and contract.get("campaign_attempt_id")
        == V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and contract.get("campaign_attempt_record_id")
        == failed_ordinal12_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
        and contract.get("campaign_failure_id")
        == failed_ordinal12_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
        and contract.get("inner_launch_failure_id")
        == V180R12R4R7_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract.get("outer_service_failure_id")
        == V180R12R4R7_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract.get("formal_artifact_count") == 12
        and contract.get("post_failure_diagnostic_artifact_count") == 1
        and contract.get("post_failure_diagnostic_is_formal_campaign_artifact")
        is False
        and contract.get("all_self_ids_verified") is True
        and contract.get("self_id_count") == 9
        and contract.get("prelaunch_materialization_succeeded") is True
        and contract.get("full_source_conformance") is True
        and contract.get("source_root_count") == 26
        and contract.get("source_conformance_mismatch_count") == 0
        and contract.get("source_conformance_cause") is None
        and contract.get("full_host_conformance") is True
        and contract.get("host_conformance_mismatch_count") == 0
        and contract.get("host_conformance_cause") is None
        and type(host) is dict
        and host.get("schema")
        == "acfqp.v180r12r4_pre_attempt_host_conformance.v1"
        and host.get("full_host_conformance") is True
        and host.get("mismatch_count") == 0
        and host.get("mismatch_rows") == []
        and host.get("cause") is None
        and contract.get("scientific_attempt_opened") is True
        and contract.get("event_kinds")
        == ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT"]
        and contract.get("completed_event_count") == 2
        and contract.get("failure_code") == "SUPERVISOR_BIRTH_FAILURE"
        and contract.get("failure_stage") == "SOCKET_BUFFER_CONFIGURATION"
        and contract.get("launch_child_created") is False
        and contract.get("launch_exec_observed") is False
        and contract.get("launch_pidfd_acquired") is False
        and type(placement_t1) is dict
        and placement_t1.get("schema")
        == PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and contract.get("production_runtime_placement_t1_complete") is True
        and contract.get("production_runtime_placement_t2_reached") is False
        and contract.get("production_runtime_placement_t3_reached") is False
        and contract.get("t2_t3_full_conformance_reached") is False
        and contract.get("cgroup_topology_conformance_diagnostic") is None
        and type(socket_observation) is dict
        and socket_observation.get("scope")
        == "PRE_CHILD_IPC_SEQPACKET_CAPABILITY"
        and contract.get("socket_capability_full_conformance") is False
        and contract.get("socket_capability_mismatch_count") == 6
        and type(contract.get("socket_capability_mismatch_rows")) is list
        and len(contract["socket_capability_mismatch_rows"]) == 6
        and type(socket_cause) is dict
        and socket_cause.get("failure_code")
        == "SOCKET_BUFFER_CAPABILITY_CONFORMANCE_FAILURE"
        and contract.get("socket_request_bytes")
        == SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        and contract.get("socket_required_effective_min_bytes")
        == SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        and contract.get("cleanup_complete") is True
        and contract.get("post_failure_measurement_root_state") == "ABSENT"
        and contract.get("formal_service_collected") is True
        and contract.get("process_may_remain") is False
        and contract.get("counter_record_count") == 0
        and contract.get("work_vector_count") == 0
        and contract.get("comparison_vector_count") == 0
        and set(contract.get("gate_statuses", {}).values()) == {"NOT_RUN"}
        and contract.get("official_execution_allowed") is False
        and contract.get("terminal_present") is False
        and contract.get("independent_replay_present") is False
        and contract.get("scientific_effect_claimed") is False
        and contract.get("identity_consumed") is True
        and contract.get("same_identity_rerun_forbidden") is True
        and contract.get("fresh_successor_identity_required") is True
        and contract.get("repair_scope") == V180R12R4R7_REPAIR_SCOPE
    ):
        _fail("frozen ordinal12 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def failed_ordinal13_repair_lineage_contract_v180r12r4() -> dict[str, Any]:
    """Bind consumed ordinal13 as the immediate scientific predecessor."""

    source = Path(failed_ordinal13_predecessor.__file__).resolve()
    expected_source = (
        _ROOT / V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
    ).resolve()
    if not (
        source == expected_source
        and source.parents[2] == _ROOT.resolve()
        and failed_ordinal13_predecessor.ORDINAL13_FAILURE_FREEZE_ID
        == V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal13_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_ID
        == V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal13_predecessor.EXPECTED_CAMPAIGN_FAILURE_ID
        == V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID
        and failed_ordinal13_predecessor.EXPECTED_INNER_LAUNCH_FAILURE_ID
        == V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal13_predecessor.EXPECTED_OUTER_SERVICE_FAILURE_ID
        == V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal13_predecessor.REPAIR_SCOPE
        == V180R12R4R8_REPAIR_SCOPE
    ):
        _fail("frozen ordinal13 failure authority changed")
    contract = (
        failed_ordinal13_predecessor.freeze_ordinal13_failure_v180r12r4r8()
        .to_contract()
    )
    host = contract.get("host_conformance")
    placement_t1 = contract.get("production_runtime_placement_t1")
    binding_observation = contract.get("binding_observation")
    binding_cause = contract.get("source_binding_cause")
    formal_failure = contract.get("formal_failure_classification")
    diagnosed_cause = contract.get("diagnosed_exact_cause")
    if not (
        contract.get("schema")
        == "acfqp.v180r12r4r8_ordinal13_failure_freeze.v1"
        and contract.get("freeze_id")
        == V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID
        and contract.get("campaign_attempt_id")
        == V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and contract.get("campaign_attempt_record_id")
        == failed_ordinal13_predecessor.EXPECTED_CAMPAIGN_ATTEMPT_RECORD_ID
        and contract.get("campaign_failure_id")
        == V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID
        and contract.get("inner_launch_failure_id")
        == V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID
        and contract.get("outer_service_failure_id")
        == V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID
        and contract.get("formal_artifact_count") == 13
        and contract.get("post_failure_diagnostic_artifact_count") == 1
        and contract.get("post_failure_diagnostic_is_formal_campaign_artifact")
        is False
        and contract.get("all_self_ids_verified") is True
        and contract.get("self_id_count") == 10
        and contract.get("prelaunch_materialization_succeeded") is True
        and contract.get("source_root_count") == 27
        and contract.get("full_source_conformance") is True
        and contract.get("source_conformance_mismatch_count") == 0
        and contract.get("source_conformance_cause") is None
        and contract.get("full_host_conformance") is True
        and contract.get("host_conformance_mismatch_count") == 0
        and contract.get("host_conformance_cause") is None
        and type(host) is dict
        and host.get("schema") == PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA
        and host.get("full_host_conformance") is True
        and host.get("mismatch_count") == 0
        and host.get("mismatch_rows") == []
        and host.get("cause") is None
        and contract.get("socket_buffer_capability_host_conformant") is True
        and contract.get("scientific_attempt_opened") is True
        and contract.get("event_kinds")
        == ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT", "PROCESS_BIRTH_OUTCOME"]
        and contract.get("completed_event_count") == 3
        and contract.get("successful_process_birth_outcome_recorded") is True
        and type(formal_failure) is dict
        and formal_failure.get("failure_code") == "INPUT_DRIFT"
        and formal_failure.get("message")
        == "ConnectionResetError: (104, 'Connection reset by peer')"
        and contract.get("formal_failure_is_secondary") is True
        and type(diagnosed_cause) is dict
        and diagnosed_cause.get("error_type") == "RuntimeError"
        and diagnosed_cause.get("message")
        == "V180r12r4 precompiled source binding changed"
        and contract.get("diagnosed_exact_cause_is_primary") is True
        and contract.get("formal_campaign_failure_launch_child_created") is False
        and contract.get("formal_campaign_failure_launch_exec_observed") is False
        and contract.get("formal_campaign_failure_launch_pidfd_acquired") is False
        and type(placement_t1) is dict
        and placement_t1.get("schema") == PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        and contract.get("production_runtime_placement_t1_complete") is True
        and contract.get("production_unit_ownership_t1_acquired") is True
        and contract.get("formal_cgroup_topology_conformance_diagnostic") is None
        and contract.get("full_cgroup_topology_conformance_recorded") is False
        and contract.get("t2_t3_full_conformance_claimed") is False
        and type(binding_observation) is dict
        and binding_observation.get("schema")
        == (
            "acfqp.v180r12r4r8_post_failure_precompiled_source_binding_"
            "observation.v1"
        )
        and binding_observation.get("campaign_attempt_id")
        == V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and binding_observation.get("campaign_failure_state_id")
        == V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID
        and binding_observation.get("production_unit_ownership_t1_acquired")
        is True
        and binding_observation.get("full_cgroup_topology_conformance_recorded")
        is False
        and contract.get("application_source_record_count") == 85
        and contract.get("third_party_source_record_count") == 21
        and contract.get("total_source_record_count") == 106
        and contract.get("source_binding_full_conformance") is False
        and contract.get("source_binding_mismatch_count") == 21
        and type(contract.get("source_binding_mismatch_rows")) is list
        and len(contract["source_binding_mismatch_rows"]) == 21
        and contract.get("first_source_binding_mismatch_index") == 85
        and contract.get("first_source_binding_mismatch_module") == "packaging"
        and type(binding_cause) is dict
        and binding_cause.get("failure_code")
        == "PRECOMPILED_SOURCE_BINDING_CONFORMANCE_FAILURE"
        and binding_cause.get("error_type") == "RuntimeError"
        and binding_cause.get("message")
        == "V180r12r4 precompiled source binding changed"
        and binding_cause.get("scope")
        == "PRECOMPILED_SOURCE_RECORD_REPOSITORY_PREFIX"
        and binding_cause.get("child_stderr_truncated") is False
        and contract.get("cleanup_complete") is True
        and contract.get("post_failure_measurement_root_state") == "ABSENT"
        and contract.get("formal_service_collected") is True
        and contract.get("process_may_remain") is False
        and contract.get("counter_record_count") == 0
        and contract.get("work_vector_count") == 0
        and contract.get("comparison_vector_count") == 0
        and contract.get("counter_records_issued") is False
        and contract.get("work_vectors_issued") is False
        and contract.get("comparison_vectors_issued") is False
        and set(contract.get("gate_statuses", {}).values()) == {"NOT_RUN"}
        and contract.get("official_execution_allowed") is False
        and contract.get("terminal_present") is False
        and contract.get("independent_replay_present") is False
        and contract.get("scientific_effect_observed") is False
        and contract.get("scientific_effect_claimed") is False
        and contract.get("identity_consumed") is True
        and contract.get("same_identity_rerun_forbidden") is True
        and contract.get("fresh_successor_identity_required") is True
        and contract.get("repair_scope") == V180R12R4R8_REPAIR_SCOPE
    ):
        _fail("frozen ordinal13 failure lineage changed")
    return {
        **contract,
        "failure_freeze_source_relative_path": (
            V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        ),
        "failure_freeze_source_is_required_authorization_source_root": True,
        "failure_freeze_source_is_resolved_from_source_bound_module_file": True,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
    }


def socket_buffer_capability_contract_v180r12r4() -> dict[str, Any]:
    """Return the preregistered exact/minimum socket host-fact contract."""

    if not (
        SOCKET_BUFFER_CAPABILITY_FACT_FIELDS
        == (
            *SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS,
            *SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS,
        )
        and tuple(SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES)
        == SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS
        and tuple(SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES)
        == SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS
    ):
        _fail("socket-buffer capability fact contract changed")
    return {
        "schema": "acfqp.v180r12r4_socket_buffer_capability_contract.v1",
        "fact_schema": SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA,
        "fact_fields": list(SOCKET_BUFFER_CAPABILITY_FACT_FIELDS),
        "exact_fields": list(SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS),
        "at_least_fields": list(SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS),
        "expected_exact_properties": dict(
            SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES
        ),
        "expected_minimum_properties": dict(
            SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES
        ),
        "mismatch_row_fields": list(
            SOCKET_BUFFER_CAPABILITY_MISMATCH_ROW_FIELDS
        ),
        "mismatch_scope": SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE,
        "insufficient_cause": SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE,
        "observed_fact_retained_in_full": True,
        "probe_precedes_campaign_attempt_o_excl": True,
        "probe_socket_is_closed_before_campaign_attempt_o_excl": True,
        "socket_conformance_is_host_conformance_not_unit_ownership": True,
    }


def topology_conformance_diagnostic_r4_contract_v180r12r4(
) -> dict[str, Any]:
    """Return the full-snapshot T3-capable diagnostic contract."""

    if not (
        TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA
        == supervisor_contract.TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA
        and PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        == supervisor_contract.PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        and PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        == supervisor_contract.PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        and PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
        == supervisor_contract.PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
    ):
        _fail("topology conformance diagnostic r4 authority changed")
    return {
        "schema": TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA,
        "fields": list(TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_FIELDS),
        "scopes": list(TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCOPES),
        "property_snapshot_fields": list(
            TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_PROPERTY_SNAPSHOT_FIELDS
        ),
        "unit_ownership_fields": list(
            TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_UNIT_OWNERSHIP_FIELDS
        ),
        "production_runtime_placement_t3_schema": (
            PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        ),
        "production_runtime_placement_t3_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
        ),
        "production_runtime_placement_t3_checkpoint_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        ),
        "pre_t3_scope_retains_explicit_null_t3_snapshot": True,
        "t3_scope_retains_complete_outer_t3_snapshot": True,
        "t3_expected_boundary": "T3_IMMEDIATELY_BEFORE_CLONE3",
        "t3_all_checkpoint_fields_compared_by_canonical_json": True,
        "unit_ownership_acquired_is_separate_from_full_conformance": True,
        "mismatch_rows_and_exact_cause_retained": True,
    }


def production_systemd_service_contract_v180r12r4() -> dict[str, Any]:
    """Return the exact effect-free transient-service invocation template."""

    launcher_template = (
        "{repository_root}/"
        + PRELAUNCH_LAUNCHER_RELATIVE_PATH
    )
    rows: list[dict[str, Any]] = []
    expected_tokens = {
        "measurement": EXPECTED_PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN,
        "verification": EXPECTED_PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN,
    }
    for target in ("measurement", "verification"):
        token_input, token, unit_name = PRODUCTION_TRANSIENT_SERVICE_ROWS[target]
        if not (
            tuple(token_input) == PRODUCTION_TRANSIENT_SERVICE_TOKEN_INPUT_FIELDS
            and token == expected_tokens[target]
        ):
            _fail("V180r12r4 production transient-service token changed")
        command = [
            PRODUCTION_ENV_EXECUTABLE,
            "-i",
            (
                "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
                + PRODUCTION_MATERIALIZATION_TERMINAL_SHA256_TEMPLATE
            ),
            "LC_CTYPE=C.UTF-8",
            "/usr/bin/python3",
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=/dev/null/v180r12r4",
            launcher_template,
            "service-entry",
            target,
            "{repository_root}",
        ]
        rows.append(
            {
                "target": target,
                "token_input": dict(token_input),
                "token": token,
                "unit_name": unit_name,
                "outer_dispatch_cwd_template": "{repository_root}",
                "outer_dispatch_argv_template": [
                    PRODUCTION_ENV_EXECUTABLE,
                    "-i",
                    (
                        "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256="
                        + PRODUCTION_MATERIALIZATION_TERMINAL_SHA256_TEMPLATE
                    ),
                    "LC_CTYPE=C.UTF-8",
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "-B",
                    "-X",
                    "pycache_prefix=/dev/null/v180r12r4",
                    launcher_template,
                    "dispatch",
                    target,
                    "{repository_root}",
                ],
                "launcher_command_template": command,
                "service_working_directory_template": "{repository_root}",
                "systemd_run_argv_template": [
                    PRODUCTION_SYSTEMD_RUN_EXECUTABLE,
                    "--user",
                    "--wait",
                    "--collect",
                    "--pipe",
                    "--quiet",
                    "--no-ask-password",
                    "--unit=" + unit_name,
                    "--slice=" + PRODUCTION_TRANSIENT_SERVICE_SLICE,
                    "--service-type=exec",
                    "--property=Delegate=yes",
                    "--property=UMask=0077",
                    "--working-directory={repository_root}",
                    *command,
                ],
            }
        )
    return {
        "schema": "acfqp.v180r12r4_production_systemd_service_contracts.v1",
        "token_domain": PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN,
        "token_input_fields": list(
            PRODUCTION_TRANSIENT_SERVICE_TOKEN_INPUT_FIELDS
        ),
        "target_order": ["measurement", "verification"],
        "target_rows": rows,
        "unit_kind": "SERVICE_NOT_SCOPE",
        "slice": PRODUCTION_TRANSIENT_SERVICE_SLICE,
        "service_type": "exec",
        "delegate": True,
        "umask": "0077",
        "systemd_run_executable": PRODUCTION_SYSTEMD_RUN_EXECUTABLE,
        "environment_executable": PRODUCTION_ENV_EXECUTABLE,
        "materialization_terminal_sha256_template": (
            PRODUCTION_MATERIALIZATION_TERMINAL_SHA256_TEMPLATE
        ),
        "repository_root_and_launcher_paths_must_be_absolute": True,
        "outer_dispatch_process_cwd_must_equal_repository_root": True,
        "service_working_directory_must_equal_repository_root": True,
        "service_source_cgroup_is_exact_direct_child_of_app_slice": True,
        "active_protocol_authorization_attempt_ids_in_token": False,
        "host_facts_in_token": False,
        "preflight_receipt_interface": dict(
            ZERO_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE
        ),
    }


def prelaunch_contract_v180r12r4() -> dict[str, Any]:
    """Return frozen prelaunch rules and zero sentinels, never outcomes."""

    return {
        "schema": "acfqp.v180r12r4_campaign_measurement_prelaunch_contract.v1",
        "precompiled_runner_module_contract": (
            source_bound_runner_execution_envelope_contract_v180r12r4()
        ),
        "external_root_schema": PRELAUNCH_EXTERNAL_ROOT_SCHEMA,
        "launch_manifest_schema": PRELAUNCH_MANIFEST_SCHEMA,
        "materialization_terminal_schema": PRELAUNCH_MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_failure_schema": PRELAUNCH_MATERIALIZATION_FAILURE_SCHEMA,
        "launch_attempt_schema": PRELAUNCH_LAUNCH_ATTEMPT_SCHEMA,
        "launch_receipt_schema": PRELAUNCH_LAUNCH_RECEIPT_SCHEMA,
        "launch_failure_schema": PRELAUNCH_LAUNCH_FAILURE_SCHEMA,
        "pre_attempt_host_conformance_relative_path": (
            PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH
        ),
        "pre_attempt_host_conformance_schema": (
            PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA
        ),
        "pre_attempt_host_conformance_byte_cap": (
            PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP
        ),
        "pre_attempt_host_conformance_mode": 0o400,
        "pre_attempt_host_conformance_expected_facts_equal_frozen_context": True,
        "pre_attempt_host_conformance_observed_facts_exact_except_"
        "self_membership": True,
        "pre_attempt_host_conformance_socket_buffer_capability_contract": (
            socket_buffer_capability_contract_v180r12r4()
        ),
        "pre_attempt_host_conformance_socket_observed_fact_retained_in_full": True,
        "pre_attempt_host_conformance_socket_exact_fields_replay_exactly": True,
        "pre_attempt_host_conformance_socket_at_least_fields_replay_by_minimum": True,
        "pre_attempt_host_conformance_socket_low_value_mismatch_row": [
            SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE,
            "{field}",
            "{minimum}",
            "{observed}",
        ],
        "pre_attempt_host_conformance_socket_only_cause": (
            SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE
        ),
        "pre_attempt_host_conformance_unit_ownership_is_separate": True,
        "pre_attempt_host_conformance_mismatch_rows_empty_on_success": True,
        "pre_attempt_host_conformance_is_campaign_event_or_counter_record": False,
        "measurement_success_requires_pre_attempt_host_conformance": True,
        "measurement_failure_progress_preserves_pre_attempt_host_conformance": True,
        "verification_predecessor_rejoins_same_pre_attempt_host_conformance": True,
        "inner_launch_publication_stages": list(
            PRELAUNCH_LAUNCH_PUBLICATION_STAGES
        ),
        "inner_launch_publication_states": list(
            PRELAUNCH_LAUNCH_PUBLICATION_STATES
        ),
        "inner_launch_failure_publication_fields": list(
            PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS
        ),
        "inner_launch_attempt_publication_path_created_allows_typed_failure": True,
        "inner_exact_receipt_publication_error_requires_file_parent_fsync_"
        "readback_recovery": True,
        "inner_partial_or_unrecoverable_receipt_allows_typed_failure_"
        "coexistence": True,
        "inner_receipt_consumers_recover_exact_bytes_and_reject_failure_"
        "coexistence": True,
        "inner_launch_partial_failure_publication_is_progress_classifiable": True,
        "service_launch_attempt_schema": PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_SCHEMA,
        "service_launch_receipt_schema": PRELAUNCH_SERVICE_LAUNCH_RECEIPT_SCHEMA,
        "service_launch_failure_schema": PRELAUNCH_SERVICE_LAUNCH_FAILURE_SCHEMA,
        "service_launch_attempt_domain": PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_DOMAIN,
        "service_launch_receipt_domain": PRELAUNCH_SERVICE_LAUNCH_RECEIPT_DOMAIN,
        "service_launch_failure_domain": PRELAUNCH_SERVICE_LAUNCH_FAILURE_DOMAIN,
        "service_launch_attempt_fields": list(
            PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS
        ),
        "service_launch_receipt_fields": list(
            PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS
        ),
        "service_launch_failure_fields": list(
            PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS
        ),
        "service_launch_inner_join_fields": list(
            PRELAUNCH_SERVICE_LAUNCH_INNER_JOIN_FIELDS
        ),
        "service_launch_unit_absence_fields": list(
            PRELAUNCH_SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS
        ),
        "service_launch_artifact_relative_paths": {
            "measurement": {
                "attempt": PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                "receipt": PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
                "failure": PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
            },
            "verification": {
                "attempt": PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                "receipt": PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
                "failure": PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
            },
        },
        "official_outer_dispatch_mode": "dispatch",
        "retained_inner_service_entry_mode": "service-entry",
        "outer_service_launch_attempt_o_excl_before_systemd_run": True,
        "outer_service_launch_pre_attempt_exact_unit_absence_no_spend_gate": True,
        "outer_service_launch_no_spend_check_to_manager_claim_race_is_typed_failure": (
            True
        ),
        "outer_service_normal_or_recovered_success_is_receipt_only": True,
        "outer_service_ordinary_pre_receipt_failure_is_failure_only": True,
        "outer_service_launch_exact_receipt_publication_error_requires_file_"
        "parent_fsync_readback_recovery": True,
        "outer_service_launch_partial_or_unrecoverable_receipt_allows_typed_"
        "failure_coexistence": True,
        "outer_service_launch_receipt_consumers_recover_exact_bytes_and_reject_"
        "failure_coexistence": True,
        "outer_service_launch_publication_states": [
            "ABSENT",
            "PRESENT_PARTIAL_OR_INVALID",
            "PRESENT_EXACT",
        ],
        "outer_service_launch_publication_stages": list(
            PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES
        ),
        "outer_service_launch_partial_failure_is_progress_classifiable": True,
        "outer_service_launch_captures_bounded_return_stdout_stderr": True,
        "outer_service_launch_requires_collected_unit_absence": True,
        "outer_service_launch_joins_inner_launch_attempt_and_terminal": True,
        "outer_service_artifacts_are_pre_scientific_and_not_campaign_evidence": True,
        "external_launch_context_schema": EXTERNAL_LAUNCH_CONTEXT_SCHEMA,
        "frozen_authorization_context_schema": (
            FROZEN_AUTHORIZATION_CONTEXT_SCHEMA
        ),
        "frozen_authorization_context_fields": list(
            FROZEN_AUTHORIZATION_CONTEXT_FIELDS
        ),
        "verified_external_launch_context_schema": (
            VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA
        ),
        "external_launch_context_fields": list(EXTERNAL_LAUNCH_CONTEXT_FIELDS),
        "verified_external_launch_context_fields": list(
            VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS
        ),
        "production_systemd_service_contract": (
            production_systemd_service_contract_v180r12r4()
        ),
        "production_systemd_service_invocation_schema": (
            PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA
        ),
        "production_systemd_service_invocation_fields": list(
            PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS
        ),
        "production_runtime_placement_t1_schema": (
            PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA
        ),
        "production_runtime_placement_t1_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS
        ),
        "production_runtime_placement_t2_schema": (
            PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
        ),
        "production_runtime_placement_t2_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS
        ),
        "production_runtime_placement_t3_schema": (
            PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA
        ),
        "production_runtime_placement_t3_checkpoint_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS
        ),
        "production_runtime_placement_t3_fields": list(
            PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS
        ),
        "topology_conformance_diagnostic_r4_contract": (
            topology_conformance_diagnostic_r4_contract_v180r12r4()
        ),
        "revalidated_external_measurement_context_schema": (
            REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA
        ),
        "revalidated_external_measurement_context_fields": list(
            REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS
        ),
        "measurement_cgroup_observation_phases": list(
            MEASUREMENT_CGROUP_OBSERVATION_PHASES
        ),
        "measurement_cgroup_observation_fields": list(
            MEASUREMENT_CGROUP_OBSERVATION_FIELDS
        ),
        "measurement_cgroup_root_name_template": (
            "v180r12r4-{campaign_attempt_id}"
        ),
        "measurement_cgroup_absence_via_fd_250_before_popen_acquires_cleanup_ownership": True,
        "delegated_parent_is_cooperative_exclusive_for_the_single_authorized_attempt": True,
        "nonconcurrent_external_delegated_parent_mutation_is_a_preregistered_assumption": True,
        "unowned_or_root_identity_drifted_measurement_cgroup_is_never_removed": True,
        "leaf_name_race_is_within_cooperative_exclusive_parent_assumption": True,
        "owned_measurement_cgroup_empty_wait_uses_same_hard_deadline": True,
        "no_cleanup_syscall_is_started_after_sampled_hard_deadline": True,
        "individual_cgroupfs_syscall_completion_before_hard_deadline_claimed": False,
        "cgroupfs_syscall_blocking_is_trusted_runtime_boundary": True,
        "measurement_success_requires_after_child_root_absent": True,
        "measurement_failure_binds_before_cleanup_after_typed_observations": True,
        "external_target_actor_roles": {
            "measurement": "OBSERVER",
            "verification": "VERIFIER",
        },
        "external_target_inherited_fd_rows": {
            target: [
                {
                    "fd": descriptor,
                    "role": role,
                    "kind": EXTERNAL_FD_ROLE_RULES[role][0],
                    "access": EXTERNAL_FD_ROLE_RULES[role][1],
                    "mode": EXTERNAL_FD_ROLE_RULES[role][2],
                    "required_seals": list(EXTERNAL_FD_ROLE_RULES[role][3]),
                    "closed_before_runner_dispatch": (
                        EXTERNAL_FD_ROLE_RULES[role][4]
                    ),
                    "cloexec_at_runner_dispatch": (
                        EXTERNAL_FD_ROLE_RULES[role][5]
                    ),
                }
                for descriptor, role in EXTERNAL_FD_ROLE_MAP[target]
            ]
            for target in ("measurement", "verification")
        },
        "external_context_memfd": EXTERNAL_LAUNCH_CONTEXT_FD,
        "delegated_cgroup_parent_fd": DELEGATED_CGROUP_PARENT_FD,
        "cgroup2_mount_fd": CGROUP2_MOUNT_FD,
        "source_systemd_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
        "external_context_measurement_target_payload": {
            "delegated_cgroup_parent_fd": DELEGATED_CGROUP_PARENT_FD,
            "cgroup2_mount_fd": CGROUP2_MOUNT_FD,
            "source_systemd_service_fd": SOURCE_SYSTEMD_SERVICE_FD,
        },
        "external_context_verification_target_payload": {},
        "external_context_has_no_mac_or_secret": True,
        "external_context_integrity_is_sealed_bytes_plus_sha256": True,
        "external_context_authority_is_source_bound_bootstrap_replay": True,
        "frozen_authorization_context_unique_data_flow": (
            "EXTERNAL_ROOT_TO_MANIFEST_TO_MATERIALIZATION_TERMINAL_DIGEST_TO_"
            "LAUNCHER_TO_SEALED_FD249_TO_BOOTSTRAP_REFREEZE_TO_VERIFIED_RUNNER"
        ),
        "launcher_may_not_source_authority_from_environment_or_unbound_json": True,
        "bootstrap_refreezes_protocol_authorization_and_authorization_evidence_"
        "canonical_bytes": True,
        "bootstrap_requires_refrozen_identity_byte_count_and_sha256_exact": True,
        "frozen_authorization_context_creates_identity_cycle": False,
        "external_context_frozen_fact_rows": [
            "protocol_id_byte_count_sha256",
            "authorization_id_byte_count_sha256",
            "authorization_evidence_id_byte_count_sha256",
            "campaign_measurement_execution_slot_id",
            "logical_occurrence_id",
            "execution_nonce",
            "campaign_attempt_id",
            "cgroup_parent_fact",
            "runtime_capability_fact",
            "production_systemd_service_invocation",
            "production_runtime_placement_t1",
        ],
        "external_context_campaign_attempt_identity_input_fields": [
            "protocol_id",
            "authorization_id",
            "authorization_evidence_id",
            "campaign_measurement_execution_slot_id",
            "logical_occurrence_id",
            "execution_nonce",
        ],
        "external_context_campaign_attempt_identity_excludes_transport_fields": (
            True
        ),
        "external_context_transport_provenance_fields": [
            "prelaunch_materialization_terminal_id",
            "prelaunch_launch_manifest_sha256",
            "prelaunch_launch_rule_id",
            "measurement_launch_attempt_id",
        ],
        "measurement_launch_attempt_byte_count_and_sha256_replayed": True,
        "measurement_context_current_attempt_equals_measurement_attempt": True,
        "verification_context_independently_replays_measurement_attempt": True,
        "measurement_launch_receipt_excluded_from_campaign_terminal_to_avoid_"
        "fixed_point": True,
        "verification_launcher_joins_post_outcome_measurement_launch_receipt": True,
        "external_root_domain": (
            domains.CONSTRUCTION_K7_PRELAUNCH_EXTERNAL_ROOT_V180R12R4_DOMAIN
        ),
        "launch_manifest_domain": (
            domains.CONSTRUCTION_K7_PRELAUNCH_MANIFEST_V180R12R4_DOMAIN
        ),
        "materialization_terminal_domain": (
            domains.CONSTRUCTION_K7_PRELAUNCH_MATERIALIZATION_TERMINAL_V180R12R4_DOMAIN
        ),
        "materialization_failure_domain": (
            domains.CONSTRUCTION_K7_PRELAUNCH_MATERIALIZATION_FAILURE_V180R12R4_DOMAIN
        ),
        "launch_attempt_domain": (
            domains.CONSTRUCTION_K7_LAUNCH_ATTEMPT_V180R12R4_DOMAIN
        ),
        "launch_receipt_domain": (
            domains.CONSTRUCTION_K7_LAUNCH_RECEIPT_V180R12R4_DOMAIN
        ),
        "launch_failure_domain": (
            domains.CONSTRUCTION_K7_LAUNCH_FAILURE_V180R12R4_DOMAIN
        ),
        "source_closure_rule_id": EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID,
        "materialization_rule_id": EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID,
        "launch_rule_id": EXPECTED_PRELAUNCH_LAUNCH_RULE_ID,
        "rule_identities_frozen": all(
            value != ZERO_ID
            for value in (
                EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID,
                EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID,
                EXPECTED_PRELAUNCH_LAUNCH_RULE_ID,
            )
        ),
        "source_bootstrap_relative_path": (
            "scripts/bootstrap_v180r12r4_campaign_measurement.py"
        ),
        "materializer_relative_path": (
            "scripts/materialize_v180r12r4_campaign_measurement_prelaunch.py"
        ),
        "retained_source_launcher_relative_path": (
            "scripts/launch_v180r12r4_campaign_measurement_prelaunch.py"
        ),
        "trusted_outer_observer_relative_path": (
            "scripts/run_v180r12r4_campaign_measurement.py"
        ),
        "measured_supervisor_entrypoint_relative_path": (
            "scripts/supervise_v180r12r4_campaign_measurement.py"
        ),
        "measured_worker_entrypoint_relative_path": (
            "scripts/work_v180r12r4_campaign_measurement.py"
        ),
        "producer_free_verifier_relative_path": (
            "scripts/verify_v180r12r4_campaign_measurement.py"
        ),
        "output_root_relative_path": PRELAUNCH_ROOT_RELATIVE_PATH,
        "external_root_relative_path": PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH,
        "bootstrap_relative_path": PRELAUNCH_BOOTSTRAP_RELATIVE_PATH,
        "launcher_relative_path": PRELAUNCH_LAUNCHER_RELATIVE_PATH,
        "launch_manifest_relative_path": PRELAUNCH_MANIFEST_RELATIVE_PATH,
        "materialization_terminal_relative_path": (
            PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "measurement_launch_attempt_relative_path": (
            PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH
        ),
        "measurement_launch_receipt_relative_path": (
            PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH
        ),
        "measurement_launch_failure_relative_path": (
            PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH
        ),
        "verification_launch_attempt_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH
        ),
        "verification_launch_receipt_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH
        ),
        "verification_launch_failure_relative_path": (
            PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH
        ),
        "external_root_sha256_environment_variable": (
            "ACFQP_V180R12R4_EXTERNAL_ROOT_SHA256"
        ),
        "launch_manifest_sha256_environment_variable": (
            "ACFQP_V180R12R4_LAUNCH_MANIFEST_SHA256"
        ),
        "materialization_terminal_sha256_environment_variable": (
            "ACFQP_V180R12R4_MATERIALIZATION_TERMINAL_SHA256"
        ),
        "prereg_commit_environment_variable": "ACFQP_V180R12R4_PREREG_COMMIT",
        "python_executable": "/usr/bin/python3",
        "git_executable": "/usr/bin/git",
        "isolated_python_argv_prefix": [
            "/usr/bin/python3",
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=/dev/null/v180r12r4",
        ],
        "launch_wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "launch_campaign_cleanup_grace_seconds": CAMPAIGN_CLEANUP_GRACE_SECONDS,
        "launch_termination_grace_seconds": TERMINATION_GRACE_SECONDS,
        "launch_monotonic_origin_is_taken_once_after_attempt_o_excl": True,
        "launch_hard_deadline_ns_formula": (
            "monotonic_origin_ns+14400_SECONDS"
        ),
        "launch_campaign_deadline_ns_formula": (
            "hard_deadline_ns-600_SECONDS"
        ),
        "measurement_and_verification_targets_have_distinct_launch_origins": True,
        "inner_target_uses_absolute_campaign_deadline_without_relative_reset": True,
        "outer_sigterm_at_hard_minus_termination_grace": True,
        "outer_sigkill_issued_at_hard_deadline_if_group_still_observed": True,
        "post_sigkill_reap_is_bounded_and_residual_state_is_typed": True,
        "whole_child_address_space_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "whole_child_address_space_cap_mechanism": (
            "RLIMIT_AS_IN_CHILD_PREEXEC_BEFORE_ISOLATED_EXEC"
        ),
        "measurement_launch_one_shot_order": [
            "O_EXCL_MEASUREMENT_LAUNCH_ATTEMPT",
            "FREEZE_SINGLE_CLOCK_MONOTONIC_ORIGIN_AND_TWO_ABSOLUTE_DEADLINES",
            "OPEN_AND_VALIDATE_FD_250_AND_FD_251",
            "OPEN_AND_VALIDATE_SOURCE_SERVICE_FD_252_AND_T1_PLACEMENT",
            "CONSTRUCT_AND_SEAL_FD_249",
            "EXEC_SOURCE_BOUND_BOOTSTRAP",
            "REPLAY_EXTERNAL_CONTEXT_AND_FACTS",
            "T2_REVALIDATE_SOURCE_PLACEMENT_BEFORE_ATTEMPT_O_EXCL",
            "O_EXCL_CAMPAIGN_ATTEMPT",
        ],
        "prelaunch_attempt_lock_precedes_external_fd_open_or_context_create": True,
        "external_fd_or_context_failure_writes_launch_failure": True,
        "external_prevalidation_failure_claims_scientific_attempt": False,
        "preopened_parent_and_mount_validation_is_trusted_excluded_overhead": True,
        "cgroup_mkdir_and_control_writes_only_after_campaign_attempt_o_excl": True,
        "run_cgroup_parent_reobserve_api": (
            "reobserve_cgroup_parent_fact_from_inherited_fds_v180r12r4"
        ),
        "run_runtime_capability_reobserve_api": (
            "reobserve_runtime_capability_fact_v180r12r4"
        ),
        "run_reobserves_cgroup_parent_via_fd_250_fd_251_and_proc_controls": True,
        "run_t2_revalidates_source_membership_pid_fd252_namespace_nca_parent_"
        "writable_and_progress_absence": True,
        "run_t2_records_bootstrap_child_and_service_entry_parent_pid": True,
        "run_t2_requires_child_and_parent_in_same_fd252_cgroup_procs_read": True,
        "run_t2_requires_direct_child_pid_relation_to_t1": True,
        "run_t2_failure_precedes_and_forbids_campaign_attempt_o_excl": True,
        "launch_supervisor_t3_revalidates_before_getrandom_and_adjacent_to_"
        "clone3": True,
        "run_t3_exactly_preserves_t2_child_and_parent_pid_evidence": True,
        "run_reobserves_runtime_capability_without_side_effects": True,
        "run_requires_reobserved_parent_identity_fields_except_observer_"
        "self_membership_equal_external_context": True,
        "run_validates_current_source_self_membership_separately_at_t1_t2_t3": True,
        "run_reobserves_before_campaign_attempt_o_excl": True,
        "run_uses_same_parent_open_file_description_for_cgroup_create_observe_"
        "cleanup": True,
        "bootstrap_dynamic_parent_discovery_forbidden": True,
        "bootstrap_exact_external_fd_inventory_required": True,
        "bootstrap_closes_external_context_fd_before_runner_dispatch": True,
        "bootstrap_retains_fd_250_fd_251_cloexec_for_measurement_runner": True,
        "bootstrap_verification_has_no_parent_or_mount_fd": True,
        "runtime_ipc_frame_schema": RUNTIME_IPC_FRAME_SCHEMA,
        "runtime_ipc_frame_fields": list(RUNTIME_IPC_FRAME_FIELDS),
        "runtime_ipc_unsigned_frame_fields": list(
            RUNTIME_IPC_UNSIGNED_FRAME_FIELDS
        ),
        "runtime_ipc_frame_byte_cap": FRAME_BYTE_CAP,
        "sock_seqpacket_buffer_request_bytes": (
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        ),
        "sock_seqpacket_effective_min_bytes": (
            SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        ),
        "sock_seqpacket_buffer_pair_roles": [
            "OBSERVER_SUPERVISOR_SOCK_SEQPACKET",
            "SUPERVISOR_WORKER_SOCK_SEQPACKET",
        ],
        "sock_seqpacket_so_sndbuf_and_so_rcvbuf_required_on_both_endpoints": True,
        "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send": True,
        "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation": True,
        "subject_result_runtime_byte_cap": SUBJECT_RESULT_RUNTIME_BYTE_CAP,
        "subject_result_runtime_byte_cap_is_physical_write_bound": True,
        "subject_result_semantic_absolute_byte_cap": SUBJECT_RESULT_BYTE_CAP,
        "seq608_full_signed_canonical_event_proposal_prevalidated_before_write": True,
        "seq608_actual_write_chunk_schedule_must_equal_prevalidated_schedule": True,
        "snapshot_bytes_transport_schema": SNAPSHOT_BYTES_TRANSPORT_SCHEMA,
        "snapshot_bytes_transport_fields": list(SNAPSHOT_BYTES_TRANSPORT_FIELDS),
        "snapshot_bytes_transport_byte_cap": SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP,
        "snapshot_bytes_transport_event_rows": [
            {
                "campaign_event_sequence": sequence,
                "phase": phase,
                "actor_role": actor_role,
                "event_kind": event_kind,
                "role": role,
            }
            for sequence, phase, actor_role, event_kind, role
            in SNAPSHOT_BYTES_TRANSPORT_EVENT_ROWS
        ],
        "snapshot_bytes_transport_exact_occurrence_count": 2,
        "snapshot_bytes_transport_authenticated_inside_event_proposal": True,
        "snapshot_bytes_transport_is_transport_only_not_evidence_document": True,
        "snapshot_bytes_transport_excluded_from_328_evidence_inventory": True,
        "snapshot_bytes_transport_excluded_from_five_measured_read_receipts": True,
        "snapshot_bytes_transport_excluded_from_nine_campaign_paths": True,
        "snapshot_bytes_transport_child_memory_included_in_cgroup_peak": True,
        "observer_filesystem_reread_for_snapshot_rehydration_forbidden": True,
        "observer_rehydrates_with_original_stable_snapshot_constructor": True,
        "snapshot_bytes_transport_lowercase_hex_byte_count_sha256_and_receipt_"
        "id_join_required": True,
        "snapshot_bytes_transport_missing_foreign_duplicate_or_late_forbidden": True,
        "independent_verifier_validates_resultant_snapshot_receipts_not_"
        "ephemeral_transport_attachment": True,
        "runtime_ipc_directional_sequence_starts_at_zero_and_increments_one": True,
        "runtime_ipc_mac_algorithm": "BLAKE2S_KEYED_256",
        "runtime_ipc_mac_covers_every_unsigned_frame_field": True,
        "runtime_ipc_channel_id_is_exact_birth_or_launch_operation_id": True,
        "runtime_ipc_role_direction_and_frame_type_allowlist_exact": True,
        "runtime_ipc_role_frame_type_rows": [
            {
                "parent_actor_role": parent,
                "child_actor_role": child,
                "direction": direction,
                "frame_types": list(frame_types),
            }
            for parent, child, direction, frame_types in (
                RUNTIME_IPC_ROLE_FRAME_TYPE_ROWS
            )
        ],
        "runtime_ipc_first_parent_frame_rows": [
            {
                "parent_actor_role": parent,
                "child_actor_role": child,
                "frame_type": frame_type,
            }
            for parent, child, frame_type in RUNTIME_IPC_FIRST_PARENT_FRAME_ROWS
        ],
        "runtime_ipc_undefined_control_frame_types": list(
            RUNTIME_IPC_UNDEFINED_CONTROL_FRAME_TYPES
        ),
        "runtime_ipc_undefined_control_frames_forbidden": True,
        "runtime_ipc_completion_uses_exact_channel_eof_then_pidfd_wait_status": True,
        "runtime_ipc_eof_before_exact_expected_event_boundary_is_failure": True,
        "runtime_ipc_recvmsg_flags_must_be_zero": True,
        "runtime_ipc_recvmsg_ancillary_must_be_empty": True,
        "runtime_ipc_recvmsg_address_must_be_empty_or_none": True,
        "runtime_channel_key_context_schema": (
            RUNTIME_CHANNEL_KEY_CONTEXT_SCHEMA
        ),
        "runtime_channel_key_context_fields": list(
            RUNTIME_CHANNEL_KEY_CONTEXT_FIELDS
        ),
        "runtime_ipc_effect_or_progress_before_ack_forbidden": True,
        "event_proposal_body_schema": EVENT_PROPOSAL_BODY_SCHEMA,
        "event_proposal_body_fields": list(EVENT_PROPOSAL_BODY_FIELDS),
        "event_ack_body_schema": EVENT_ACK_BODY_SCHEMA,
        "event_ack_body_fields": list(EVENT_ACK_BODY_FIELDS),
        "event_proposal_intent_evidence_documents_exactly_empty": True,
        "event_proposal_evidence_documents_are_exact_canonical_documents": True,
        "event_ack_after_evidence_and_event_file_and_directory_fsync_only": True,
        "observer_supervisor_start_schema": OBSERVER_SUPERVISOR_START_SCHEMA,
        "observer_supervisor_start_fields": list(
            OBSERVER_SUPERVISOR_START_FIELDS
        ),
        "observer_supervisor_start_requires_full_canonical_topology_document": (
            True
        ),
        "observer_supervisor_start_requires_full_canonical_supervisor_birth_"
        "document": True,
        "observer_supervisor_start_documents_recompute_exact_schema_keyset_"
        "domain_identity": True,
        "observer_supervisor_start_topology_joins_worker_leaf_fd_245": True,
        "observer_supervisor_start_birth_joins_topology_attempt_operation_and_"
        "internal_context": True,
        "observer_supervisor_start_id_only_authority_forbidden": True,
        "supervisor_worker_handoff_schema": SUPERVISOR_WORKER_HANDOFF_SCHEMA,
        "supervisor_worker_handoff_fields": list(
            SUPERVISOR_WORKER_HANDOFF_FIELDS
        ),
        "supervisor_worker_handoff_requires_full_canonical_worker_birth_"
        "document": True,
        "supervisor_worker_handoff_worker_birth_recomputes_exact_schema_keyset_"
        "domain_identity": True,
        "supervisor_worker_handoff_worker_birth_joins_worker_pid_fd_cgroup_and_"
        "internal_context": True,
        "supervisor_worker_handoff_worker_birth_id_only_authority_forbidden": (
            True
        ),
        "stage_fd_binding_fields": list(STAGE_FD_BINDING_FIELDS),
        "subject_output_fd_binding_fields": list(
            SUBJECT_OUTPUT_FD_BINDING_FIELDS
        ),
        "child_stdout_byte_cap": STDOUT_BYTE_CAP,
        "child_stderr_byte_cap": STDERR_BYTE_CAP,
        "source_closure_file_count_cap": 4_096,
        "source_closure_total_byte_count_cap": 128 * 1024 * 1024,
        "launch_artifact_byte_cap": 16 * 1024 * 1024,
        "evidence_inventory_bundle_byte_cap": (
            EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP
        ),
        "execution_closure_byte_cap": EXECUTION_CLOSURE_BYTE_CAP,
        "os_receipt_bundle_byte_cap": OS_RECEIPT_BUNDLE_BYTE_CAP,
        "ledger_closure_byte_cap": LEDGER_CLOSURE_BYTE_CAP,
        "terminal_byte_cap": TERMINAL_BYTE_CAP,
        "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
        "outer_monotonic_watchdog_process_group_required": True,
        "source_closure_contract": source_closure_contract_v180r12r4(),
        "source_closure_and_normalized_wrapper_freeze_required": True,
        "actual_manifest_digest_preregistered": False,
        "actual_manifest_digest_is_runtime_transport_receipt": True,
        "actual_manifest_digest_is_scientific_identity": False,
        "external_root_materialization_is_preattempt_trusted_work": True,
        "external_root_materialization_is_campaign_actual_measurement": False,
        "retained_launcher_is_outside_campaign_accounting": True,
        "trusted_outer_observer_is_outside_campaign_accounting": True,
        "only_supervisor_and_worker_children_are_measured": True,
        "outer_observer_births_exactly_one_supervisor": True,
        "supervisor_births_exactly_one_worker": True,
        "observer_never_births_worker_directly": True,
        "measurement_launch_precedes_producer_free_verification_launch": True,
        "verification_launch_requires_typed_measurement_terminal_and_receipt": True,
        "measurement_launch_success_requires_four_exact_terminal_bound_"
        "artifacts": True,
        "verification_launch_rejoins_four_exact_terminal_bound_artifacts": True,
        "verification_launch_requires_runtime_cas_absent": True,
        "launch_attempt_written_o_excl_and_fsynced_before_child_exec": True,
        "launch_attempt_is_concurrency_and_replay_lock": True,
        "retained_launcher_and_child_share_one_exact_launch_identity": True,
        "child_requires_current_exact_launch_attempt_and_absent_same_target_"
        "receipt_and_failure": True,
        "direct_child_invocation_cannot_supersede_a_consumed_launch_identity": True,
        "measurement_and_verification_launch_attempt_count": 2,
        "attempt_receipt_failure_and_progress_freshness_matrix_required": True,
        "materialization_terminal_and_failure_mutually_exclusive": True,
        "ordinary_launch_receipt_and_failure_are_mutually_exclusive": True,
        "unrecoverable_receipt_publication_allows_typed_failure_coexistence_"
        "but_never_success": True,
        "materialization_or_launch_failure_consumes_exact_identity": True,
        "same_materialization_or_launch_identity_rerun_forbidden": True,
        "materialization_failure_forbids_any_launch": True,
        "launch_receipts_are_structural_transport_receipts": True,
        "launch_receipts_are_campaign_actual_measurements": False,
        "launch_attempt_and_terminal_child_execution_state_fields": [
            "authorized_child_measurement_execution_attempted",
            "authorized_child_measurement_execution_completed",
            "producer_free_verification_attempted",
            "producer_free_verification_completed",
        ],
        "measurement_launch_marks_measurement_attempted_at_attempt_lock": True,
        "measurement_launch_marks_measurement_completed_only_on_exact_success": True,
        "verification_launch_marks_verification_attempted_at_attempt_lock": True,
        "verification_launch_marks_verification_completed_only_on_exact_success": True,
        "successful_measurement_and_verification_child_stdout_exact_byte_count": 0,
        "successful_measurement_and_verification_child_stderr_exact_byte_count": 0,
        "successful_child_diagnostic_streams_must_be_exactly_empty": True,
        "preauthorization_predecessor_and_source_validation_reads_are_trusted": True,
        "preauthorization_validation_reads_are_campaign_actual_measurements": False,
        "success_durable_artifact_contract": (
            success_durable_artifact_contract_v180r12r4()
        ),
        "all_prelaunch_outcome_identities_absent": True,
        "materialization_started": False,
        "measurement_launch_started": False,
        "verification_launch_started": False,
        "outcome_free": True,
    }


def evidence_inventory_contract_v180r12r4() -> dict[str, Any]:
    """Preregister the exact typed evidence denominator and event joins."""

    rows = [
        {
            "evidence_type": evidence_type,
            "schema": schema,
            "domain_tag": domain_tag,
            "identity_field": identity_field,
            "document_count": document_count,
            "direct_event_reference_count": direct_event_reference_count,
        }
        for (
            evidence_type,
            schema,
            domain_tag,
            identity_field,
            document_count,
            direct_event_reference_count,
        ) in EVIDENCE_INVENTORY_ROWS
    ]
    requirements = [
        {
            "event_kind": event_kind,
            "evidence_type": evidence_type,
            "event_count": event_count,
            "evidence_id_requirement": (
                "REQUIRED_REGISTERED_UNIQUE" if evidence_type is not None else "NULL"
            ),
            "auxiliary_names": [],
        }
        for event_kind, evidence_type, event_count in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS
    ]
    return {
        "schema": "acfqp.v180r12r4_terminal_evidence_inventory_contract.v1",
        "typed_document_rows": rows,
        "typed_document_row_order_is_exact": True,
        "typed_document_type_count": len(rows),
        "typed_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "direct_event_evidence_document_count": (
            SUCCESS_DIRECT_EVENT_EVIDENCE_DOCUMENT_COUNT
        ),
        "support_evidence_document_count": SUCCESS_SUPPORT_EVIDENCE_DOCUMENT_COUNT,
        "event_evidence_requirements": requirements,
        "event_evidence_requirement_order_is_event_kind_grammar_order": True,
        "nonnull_event_evidence_count": SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT,
        "null_event_evidence_count": SUCCESS_NULL_EVENT_EVIDENCE_COUNT,
        "successful_event_count": SUCCESS_EXACT_EVENT_COUNT,
        "io_transfer_subcounts": {
            "input_read": 5,
            "stage_write": 2,
            "subject_write": 1,
        },
        "visibility_subcounts": {"open": 2, "close": 2},
        "semantic_operation_subcounts": {
            "semantic_hash": SEMANTIC_HASH_OPERATION_COUNT,
            "integrity_check": INTEGRITY_CHECK_OPERATION_COUNT,
            "protocol_check": PROTOCOL_CHECK_OPERATION_COUNT,
        },
        "native_zero_support_manifest_types": [
            "CAMPAIGN_OPERATION_MANIFEST",
            "NATIVE_ZERO_SOURCE_MANIFEST",
            "NATIVE_ZERO_IMPORT_INVENTORY",
        ],
        "native_zero_support_manifest_count": 3,
        "native_zero_precompiled_source_row_fields": sorted(
            ledger_contract.PRECOMPILED_SOURCE_ROW_FIELDS
        ),
        "native_zero_source_fact_fields": sorted(
            ledger_contract.NATIVE_ZERO_SOURCE_FACT_FIELDS
        ),
        "native_zero_operation_site_fact_fields": sorted(
            ledger_contract.NATIVE_ZERO_OPERATION_SITE_FACT_FIELDS
        ),
        "native_zero_import_fact_fields": sorted(
            ledger_contract.NATIVE_ZERO_IMPORT_FACT_FIELDS
        ),
        "native_zero_measured_target_source_paths": dict(
            ledger_contract.PRECOMPILED_TARGET_SOURCE_PATHS
        ),
        "native_zero_measured_target_source_fact_count": 3,
        "native_zero_verification_target_is_part_of_measured_source_axis": False,
        "native_zero_registered_planning_operation_site_fact_count": 314,
        "native_zero_nested_fact_ids_independently_rederived": True,
        "native_zero_source_and_import_fact_counts_bound_by_sealed_bundle": True,
        "native_zero_source_import_manifests_known_before_attempt": True,
        "native_zero_source_import_manifests_depend_on_role_exit_observations": False,
        "native_zero_runtime_role_exit_origin_guard_required": True,
        "producer_terminal_runtime_role_exit_origin_guard_status": (
            "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "independent_pass_requires_frozen_bootstrap_and_successful_measurement_"
        "launch_receipt_join": True,
        "native_zero_attestation_is_inventory_document": False,
        "native_zero_attestation_is_separate_accounting_chain_object": True,
        "terminal_evidence_bundle_field": "evidence_documents",
        "terminal_bundle_domain": (
            domains.CONSTRUCTION_K7_TERMINAL_BUNDLE_V180R12R4_DOMAIN
        ),
        "production_evidence_domain": (
            domains.CONSTRUCTION_K7_PRODUCTION_EVIDENCE_V180R12R4_DOMAIN
        ),
        "terminal_evidence_documents_sorted_by_evidence_id": True,
        "one_canonical_typed_document_per_inventory_occurrence_required": True,
        "canonical_json_exact_bytes_required": True,
        "document_identity_is_registered_domain_content_id": True,
        "document_schema_and_domain_must_match_exact_type_row": True,
        "document_ids_pairwise_unique_required": True,
        "direct_event_evidence_ids_pairwise_unique_required": True,
        "every_nonnull_event_evidence_id_resolves_exactly_once": True,
        "every_nonnull_success_event_evidence_id_maps_to_one_canonical_typed_"
        "document": True,
        "every_direct_event_evidence_document_referenced_exactly_once": True,
        "every_support_document_joined_transitively": True,
        "unknown_event_evidence_id_forbidden": True,
        "missing_required_event_evidence_id_forbidden": True,
        "duplicate_event_or_document_evidence_id_forbidden": True,
        "unregistered_evidence_id_forbidden": True,
        "extra_or_orphan_evidence_document_forbidden": True,
        "intent_event_evidence_ids_are_null": True,
        "ledger_closed_evidence_id_is_null_to_avoid_self_cycle": True,
        "successful_event_auxiliary_values_exactly_empty": True,
        "event_payload_auxiliary_is_distinct_from_typed_evidence_auxiliary": True,
        "semantic_operation_receipt_auxiliary_rows": [
            {
                "kind": kind,
                "name": name,
                "value_semantics": value_semantics,
                "receipt_count": count,
            }
            for kind, name, value_semantics, count
            in SEMANTIC_RECEIPT_AUXILIARY_ROWS
        ],
        "semantic_operation_receipt_auxiliary_row_count": 297,
        "semantic_operation_receipt_exactly_one_auxiliary_row": True,
        "semantic_hash_observed_value_rederived_from_subject_input_and_inner_"
        "content_facts": True,
        "integrity_and_protocol_check_passed_is_exact_true": True,
        "support_join_rules": [
            "SOURCE_READ_IO_RECEIPTS_REFERENCE_TWO_STABLE_INPUT_SNAPSHOTS",
            "STAGE_AND_WORKER_READ_IO_RECEIPTS_REFERENCE_TWO_MEMFD_STAGE_RECEIPTS",
            "VISIBILITY_RECEIPTS_REFERENCE_MEMFD_STAGES_AND_CGROUP_TOPOLOGY",
            "SEMANTIC_RECEIPTS_REFERENCE_EXACT_OPERATION_SOURCE_AND_IMPORT_MANIFESTS",
            "REPLAY_SUBJECT_SHARES_EXACT_OPERATION_SOURCE_AND_IMPORT_MANIFEST_IDS_"
            "WITH_ALL_SEMANTIC_RECEIPTS",
            *EVIDENCE_CAUSAL_JOIN_RULES,
            "BIRTH_REAP_AND_CGROUP_RECEIPTS_REFERENCE_ONE_CGROUP_TOPOLOGY",
            "COMMIT_AND_WINDOW_RECEIPTS_JOIN_ONE_CAMPAIGN_EXECUTION_CLOSURE",
        ],
        "causal_join_rules": list(EVIDENCE_CAUSAL_JOIN_RULES),
        "campaign_attempt_record_written_o_excl_before_cgroup_creation": True,
        "campaign_attempt_record_contains_cgroup_topology_receipt_id": False,
        "final_subject_references_campaign_attempt_record_id": True,
        "final_subject_contains_semantic_operation_receipt_ids": False,
        "semantic_receipt_evidence_subject_is_campaign_attempt_record": True,
        "semantic_receipt_evidence_subject_is_future_final_subject": False,
        "semantic_receipt_count_bound_to_attempt_record": 297,
        "replay_subject_binds_attempt_record_final_subject_and_semantic_receipts": True,
        "replay_subject_exact_semantic_receipt_id_count": 297,
        "subject_write_source_evidence_type": "CAMPAIGN_SUBJECT_RESULT",
        "subject_write_target_evidence_type": "WORKER_PIDFD_BIRTH_RECEIPT",
        "subject_write_references_future_replay_subject": False,
        "replay_subject_first_consumer_event_kind": "SUBJECT_COMMIT",
        "subject_readback_source_evidence_type": "CAMPAIGN_SUBJECT_RESULT",
        "subject_readback_target_evidence_type": "SUPERVISOR_PIDFD_BIRTH_RECEIPT",
        "successful_event_may_reference_not_yet_issued_evidence": False,
        "outcome_documents_present": False,
        "outcome_free": True,
    }


def success_durable_artifact_contract_v180r12r4() -> dict[str, Any]:
    """Freeze the four terminal-bound success files without materializing them."""

    execution_rows = tuple(
        (schema, identity_field, fields)
        for _name, schema, identity_field, fields in (
            ledger_contract.EVIDENCE_DOCUMENT_FIELD_KEYSET_ROWS
        )
        if schema == EXECUTION_CLOSURE_SCHEMA
    )
    if not (
        finalizer_contract.EVIDENCE_INVENTORY_BUNDLE_SCHEMA
        == EVIDENCE_INVENTORY_BUNDLE_SCHEMA
        and finalizer_contract.OS_RECEIPT_BUNDLE_SCHEMA
        == OS_RECEIPT_BUNDLE_SCHEMA
        and finalizer_contract.TERMINAL_SCHEMA == TERMINAL_SCHEMA
        and finalizer_contract.SUCCESS_ARTIFACT_ORDER == SUCCESS_ARTIFACT_ORDER
        and finalizer_contract.SUCCESS_ARTIFACT_SCHEMA_ROWS
        == SUCCESS_ARTIFACT_SCHEMA_ROWS
        and finalizer_contract.EVIDENCE_INVENTORY_BUNDLE_FIELDS
        == frozenset(EVIDENCE_INVENTORY_BUNDLE_FIELDS)
        and finalizer_contract.OS_RECEIPT_BUNDLE_FIELDS
        == frozenset(OS_RECEIPT_BUNDLE_FIELDS)
        and finalizer_contract.TERMINAL_FIELDS == frozenset(TERMINAL_FIELDS)
        and finalizer_contract.SUCCESS_EVIDENCE_DOCUMENT_COUNT == 328
        and finalizer_contract.OS_EVIDENCE_DOCUMENT_COUNT == 12
        and execution_rows
        == ((EXECUTION_CLOSURE_SCHEMA, "campaign_execution_closure_id",
             frozenset(EXECUTION_CLOSURE_FIELDS)),)
        and tuple(row[0] for row in SUCCESS_DURABLE_ARTIFACT_ROWS)
        == SUCCESS_DURABLE_WRITE_ORDER[:-1]
        and tuple(row[1] for row in SUCCESS_DURABLE_ARTIFACT_ROWS)
        == SUCCESS_ARTIFACT_ORDER
        and min(row[8] for row in SUCCESS_DURABLE_ARTIFACT_ROWS) > 0
        and FAILURE_ARTIFACT_HASH_BYTE_CAP
        >= max(row[8] for row in SUCCESS_DURABLE_ARTIFACT_ROWS)
    ):
        _fail("V180r12r4 success durable artifact producer contract changed")

    return {
        "schema": "acfqp.v180r12r4_success_durable_artifact_contract.v1",
        "artifact_rows": [
            {
                "artifact_name": artifact_name,
                "finalizer_mapping_key": mapping_key,
                "relative_path": relative_path,
                "document_schema": document_schema,
                "content_id_domain": content_id_domain,
                "identity_field": identity_field,
                "terminal_fact_prefix": terminal_fact_prefix,
                "exact_field_keyset": sorted(fields),
                "byte_cap": byte_cap,
                "required_mode": "0400",
            }
            for (
                artifact_name,
                mapping_key,
                relative_path,
                document_schema,
                content_id_domain,
                identity_field,
                terminal_fact_prefix,
                fields,
                byte_cap,
            ) in SUCCESS_DURABLE_ARTIFACT_ROWS
        ],
        "finalizer_mapping_order": list(SUCCESS_ARTIFACT_ORDER),
        "producer_write_order": list(SUCCESS_DURABLE_WRITE_ORDER),
        "terminal_schema": TERMINAL_SCHEMA,
        "terminal_exact_field_keyset": sorted(TERMINAL_FIELDS),
        "terminal_byte_cap": TERMINAL_BYTE_CAP,
        "terminal_fact_suffixes": ["id", "byte_count", "sha256"],
        "artifact_content_id_recomputed_under_exact_registered_domain": True,
        "artifact_byte_count_and_sha256_join_terminal_exactly": True,
        "evidence_inventory_document_count": 328,
        "os_receipt_document_count": 12,
        "execution_closure_is_exact_inventory_document": True,
        "os_receipts_are_exact_twelve_document_inventory_subset": True,
        "ledger_closure_evidence_documents_equal_inventory_documents": True,
        "terminal_embedded_ledger_equals_durable_ledger_closure": True,
        "terminal_embedded_os_documents_equal_durable_os_bundle": True,
        "write_flags": ["O_CREAT", "O_EXCL", "O_NOFOLLOW", "O_WRONLY"],
        "file_mode": "0400",
        "file_fsync_before_close_required": True,
        "parent_directory_fsync_after_each_file_required": True,
        "bounded_stable_exact_readback_after_each_file_required": True,
        "byte_cap_checked_before_o_excl_create": True,
        "terminal_written_only_after_four_artifacts": True,
        "unknown_missing_duplicate_or_foreign_artifact_forbidden": True,
        "verification_predecessor_rejoins_current_exact_artifact_bytes": True,
        "failure_partial_observation_includes_all_four_artifacts": True,
        "outcome_documents_present": False,
        "outcome_free": True,
    }


def durable_artifact_contract_v180r12r4() -> dict[str, Any]:
    """Freeze internal paths and fail-closed freshness, without writing them."""

    success_artifacts = success_durable_artifact_contract_v180r12r4()

    return {
        "schema": "acfqp.v180r12r4_durable_artifact_contract.v1",
        "success_artifact_contract": success_artifacts,
        "attempt_record_relative_path": ATTEMPT_RELATIVE_PATH,
        "output_root_relative_path": OUTPUT_ROOT_RELATIVE_PATH,
        "events_directory_relative_path": EVENTS_RELATIVE_PATH,
        "event_filename_pattern": "{sequence:06d}.json",
        "successful_event_file_count": SUCCESS_EXACT_EVENT_COUNT,
        "subject_temp_relative_path": SUBJECT_TEMP_RELATIVE_PATH,
        "subject_result_relative_path": SUBJECT_RESULT_RELATIVE_PATH,
        "evidence_inventory_relative_path": EVIDENCE_INVENTORY_RELATIVE_PATH,
        "execution_closure_relative_path": EXECUTION_CLOSURE_RELATIVE_PATH,
        "os_receipt_relative_path": OS_RECEIPT_RELATIVE_PATH,
        "ledger_closure_relative_path": LEDGER_CLOSURE_RELATIVE_PATH,
        "terminal_relative_path": TERMINAL_RELATIVE_PATH,
        "failure_relative_path": FAILURE_RELATIVE_PATH,
        "runtime_cas_root_relative_path": RUNTIME_CAS_ROOT_RELATIVE_PATH,
        "verification_relative_path": VERIFICATION_RELATIVE_PATH,
        "verification_failure_relative_path": VERIFICATION_FAILURE_RELATIVE_PATH,
        "retained_verification_replay_relative_path": (
            RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH
        ),
        "one_o_excl_canonical_event_file_per_sequence": True,
        "event_file_fsync_and_events_directory_fsync_required": True,
        "subject_temp_preopened_o_excl_before_worker_birth": True,
        "subject_result_commit_requires_atomic_no_replace_rename": True,
        "subject_result_file_and_parent_directory_fsync_required": True,
        "evidence_inventory_execution_closure_os_receipt_and_ledger_closure_"
        "written_o_excl": True,
        "success_durable_write_order": list(SUCCESS_DURABLE_WRITE_ORDER),
        "success_durable_file_mode": "0400",
        "success_durable_file_and_parent_directory_fsync_required": True,
        "success_durable_bounded_stable_exact_readback_required": True,
        "terminal_written_o_excl_after_ledger_closure": True,
        "failure_written_o_excl_at_most_once": True,
        "freshness_stage_matrices": [
            {
                "stage": "MATERIALIZATION_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_ROOT_RELATIVE_PATH,
                    PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH,
                    PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
                    PRELAUNCH_MATERIALIZATION_FAILURE_RELATIVE_PATH,
                ],
                "must_be_present_exact": [],
            },
            {
                "stage": "MEASUREMENT_SERVICE_LAUNCH_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
                    ATTEMPT_RELATIVE_PATH,
                    OUTPUT_ROOT_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
                    PRELAUNCH_MANIFEST_RELATIVE_PATH,
                ],
            },
            {
                "stage": "MEASUREMENT_LAUNCH_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
                    ATTEMPT_RELATIVE_PATH,
                    OUTPUT_ROOT_RELATIVE_PATH,
                    EVIDENCE_INVENTORY_RELATIVE_PATH,
                    EXECUTION_CLOSURE_RELATIVE_PATH,
                    OS_RECEIPT_RELATIVE_PATH,
                    LEDGER_CLOSURE_RELATIVE_PATH,
                    TERMINAL_RELATIVE_PATH,
                    FAILURE_RELATIVE_PATH,
                    RUNTIME_CAS_ROOT_RELATIVE_PATH,
                    VERIFICATION_RELATIVE_PATH,
                    VERIFICATION_FAILURE_RELATIVE_PATH,
                    RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
                    PRELAUNCH_MANIFEST_RELATIVE_PATH,
                ],
            },
            {
                "stage": "MEASUREMENT_ATTEMPT_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_FAILURE_RELATIVE_PATH,
                    ATTEMPT_RELATIVE_PATH,
                    OUTPUT_ROOT_RELATIVE_PATH,
                    EVENTS_RELATIVE_PATH,
                    SUBJECT_TEMP_RELATIVE_PATH,
                    SUBJECT_RESULT_RELATIVE_PATH,
                    EVIDENCE_INVENTORY_RELATIVE_PATH,
                    EXECUTION_CLOSURE_RELATIVE_PATH,
                    OS_RECEIPT_RELATIVE_PATH,
                    LEDGER_CLOSURE_RELATIVE_PATH,
                    TERMINAL_RELATIVE_PATH,
                    FAILURE_RELATIVE_PATH,
                    RUNTIME_CAS_ROOT_RELATIVE_PATH,
                    VERIFICATION_RELATIVE_PATH,
                    VERIFICATION_FAILURE_RELATIVE_PATH,
                    RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MATERIALIZATION_TERMINAL_RELATIVE_PATH,
                ],
            },
            {
                "stage": "VERIFICATION_SERVICE_LAUNCH_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH,
                    RUNTIME_CAS_ROOT_RELATIVE_PATH,
                    VERIFICATION_RELATIVE_PATH,
                    VERIFICATION_FAILURE_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    TERMINAL_RELATIVE_PATH,
                ],
            },
            {
                "stage": "VERIFICATION_LAUNCH_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH,
                    RUNTIME_CAS_ROOT_RELATIVE_PATH,
                    VERIFICATION_RELATIVE_PATH,
                    VERIFICATION_FAILURE_RELATIVE_PATH,
                    RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    EVIDENCE_INVENTORY_RELATIVE_PATH,
                    EXECUTION_CLOSURE_RELATIVE_PATH,
                    OS_RECEIPT_RELATIVE_PATH,
                    LEDGER_CLOSURE_RELATIVE_PATH,
                    TERMINAL_RELATIVE_PATH,
                ],
            },
            {
                "stage": "VERIFICATION_ATTEMPT_PRECREATE",
                "must_be_absent": [
                    PRELAUNCH_VERIFICATION_LAUNCH_RECEIPT_RELATIVE_PATH,
                    PRELAUNCH_VERIFICATION_LAUNCH_FAILURE_RELATIVE_PATH,
                    RUNTIME_CAS_ROOT_RELATIVE_PATH,
                    VERIFICATION_RELATIVE_PATH,
                    VERIFICATION_FAILURE_RELATIVE_PATH,
                    RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH,
                ],
                "must_be_present_exact": [
                    PRELAUNCH_VERIFICATION_LAUNCH_ATTEMPT_RELATIVE_PATH,
                    PRELAUNCH_MEASUREMENT_LAUNCH_RECEIPT_RELATIVE_PATH,
                    EVIDENCE_INVENTORY_RELATIVE_PATH,
                    EXECUTION_CLOSURE_RELATIVE_PATH,
                    OS_RECEIPT_RELATIVE_PATH,
                    LEDGER_CLOSURE_RELATIVE_PATH,
                    TERMINAL_RELATIVE_PATH,
                ],
            },
        ],
        "retained_launcher_and_child_share_one_exact_launch_identity": True,
        "measurement_child_requires_current_exact_measurement_launch_attempt": True,
        "verification_child_requires_current_exact_verification_launch_attempt": True,
        "child_rejects_same_target_launch_receipt_or_failure": True,
        "old_launch_failure_cannot_be_superseded_by_direct_child_invocation": True,
        "direct_child_invocation_without_current_exact_launch_attempt_forbidden": True,
        "any_preexisting_blocker_in_corresponding_precreate_matrix_forbids_same_"
        "identity": True,
        "current_exact_o_excl_prerequisite_is_not_a_stale_blocker": True,
        "partial_event_subject_or_receipt_state_is_preserved_on_failure": True,
        "success_and_failure_preserve_exact_partial_observations": True,
        "resume_from_partial_state_forbidden": True,
        "same_attempt_identity_rerun_forbidden": True,
        "no_paths_created_by_this_contract": True,
        "outcome_free": True,
    }


def failure_observation_contract_v180r12r4() -> dict[str, Any]:
    """Freeze bounded failure-only observations without success authority."""

    runtime_contract = supervisor_contract.supervisor_contract_v180r12r4()
    if not (
        runtime_contract["failure_artifact_observation_row_cap"]
        == FAILURE_ARTIFACT_OBSERVATION_ROW_CAP
        and runtime_contract["failure_artifact_metadata_byte_cap"]
        == FAILURE_ARTIFACT_METADATA_BYTE_CAP
        and runtime_contract["failure_directory_entry_cap"]
        == FAILURE_DIRECTORY_ENTRY_CAP
        and runtime_contract["failure_directory_entry_name_total_byte_cap"]
        == FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        and runtime_contract["failure_artifact_stream_hash_byte_cap"]
        == FAILURE_ARTIFACT_HASH_BYTE_CAP
        and runtime_contract["failure_artifact_states"]
        == ["ABSENT", "LINKED_OR_NONREGULAR", "PRESENT", "READ_ERROR"]
        and runtime_contract["failure_artifact_kinds"] == ["DIRECTORY", "FILE"]
        and runtime_contract["failure_cgroup_observation_is_not_success_receipt"]
        is True
        and runtime_contract["failure_artifact_fixed_path_kind_rows"]
        == [list(row) for row in FAILURE_PROGRESS_PATH_KIND_ROWS]
        and runtime_contract["failure_artifact_observation_boundary"]
        == "IMMEDIATELY_BEFORE_FAILURE_WRITE"
        and supervisor_contract.FAILURE_ARTIFACT_FIXED_PATH_KIND_ROWS
        == FAILURE_PROGRESS_PATH_KIND_ROWS
        and supervisor_contract.FAILURE_ARTIFACT_OBSERVATION_BOUNDARY
        == "IMMEDIATELY_BEFORE_FAILURE_WRITE"
        and supervisor_contract.FAILURE_ARTIFACT_OBSERVATION_KEYS
        == frozenset(FAILURE_ARTIFACT_OBSERVATION_FIELDS)
        and supervisor_contract.FAILURE_CGROUP_OBSERVATION_KEYS
        == frozenset(FAILURE_CGROUP_OBSERVATION_FIELDS)
        and supervisor_contract.FAILURE_CGROUP_NODE_OBSERVATION_KEYS
        == frozenset(FAILURE_CGROUP_NODE_OBSERVATION_FIELDS)
        and runtime_contract["failure_cgroup_node_roles"]
        == list(FAILURE_CGROUP_NODE_ROLES)
        and runtime_contract["failure_cgroup_node_states"]
        == list(FAILURE_CGROUP_NODE_STATES)
        and runtime_contract["failure_cgroup_node_observation_keys"]
        == sorted(FAILURE_CGROUP_NODE_OBSERVATION_FIELDS)
        and supervisor_contract.FAILURE_STATE_FIELD_KEYS
        == frozenset(FAILURE_STATE_FIELDS)
        and len(FAILURE_PROGRESS_PATH_KIND_ROWS) == 15
        and len({row[0] for row in FAILURE_PROGRESS_PATH_KIND_ROWS}) == 15
        and tuple(row[0] for row in FAILURE_PROGRESS_PATH_KIND_ROWS)
        == tuple(sorted(row[0] for row in FAILURE_PROGRESS_PATH_KIND_ROWS))
        and len(VERIFICATION_FAILURE_FIELDS) == 39
        and len(set(VERIFICATION_FAILURE_FIELDS)) == 39
        and len(VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS) == 9
        and tuple(
            row[0] for row in VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
        )
        == tuple(
            sorted(
                row[0]
                for row in VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
            )
        )
        and len(VERIFICATION_FAILURE_WATCHDOG_CLEANUP_FIELDS) == 8
        and len(set(VERIFICATION_FAILURE_WATCHDOG_CLEANUP_FIELDS)) == 8
        and VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES == 64 * 1024
        and 6 * FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        + FAILURE_ARTIFACT_METADATA_BYTE_CAP
        < FAILURE_EMERGENCY_RESERVE_BYTES
    ):
        _fail("V180r12r4 runtime failure observation contract changed")
    return {
        "schema": "acfqp.v180r12r4_failure_observation_contract.v1",
        "failure_state_schema": "acfqp.campaign_failure_state.v180r12r4",
        "failure_state_domain": (
            evidence_domains.CONSTRUCTION_K7_FAILURE_STATE_RECEIPT_V180R12R4E_DOMAIN
        ),
        "failure_artifact_observation_fields": list(
            FAILURE_ARTIFACT_OBSERVATION_FIELDS
        ),
        "failure_cgroup_observation_fields": list(
            FAILURE_CGROUP_OBSERVATION_FIELDS
        ),
        "failure_cgroup_node_observation_fields": list(
            FAILURE_CGROUP_NODE_OBSERVATION_FIELDS
        ),
        "failure_cgroup_node_roles": list(FAILURE_CGROUP_NODE_ROLES),
        "failure_cgroup_node_states": list(FAILURE_CGROUP_NODE_STATES),
        "failure_state_fields": list(FAILURE_STATE_FIELDS),
        "typed_launch_failure_substages": list(
            TYPED_LAUNCH_FAILURE_SUBSTAGES
        ),
        "typed_launch_failure_fields": list(TYPED_LAUNCH_FAILURE_FIELDS),
        "typed_launch_failure_preserves_original_primary_exception": True,
        "failure_artifact_kinds": ["DIRECTORY", "FILE"],
        "failure_artifact_states": [
            "ABSENT",
            "LINKED_OR_NONREGULAR",
            "PRESENT",
            "READ_ERROR",
        ],
        "fixed_progress_path_kind_rows": [
            {"relative_path": path, "kind": kind}
            for path, kind in FAILURE_PROGRESS_PATH_KIND_ROWS
        ],
        "fixed_progress_path_count": len(FAILURE_PROGRESS_PATH_KIND_ROWS),
        "partial_artifact_observation_boundary": (
            "IMMEDIATELY_BEFORE_FAILURE_WRITE"
        ),
        "fixed_progress_rows_are_exactly_required": True,
        "additional_rows_are_exact_events_directory_direct_entries_only": True,
        "failure_path_observation_is_absent_before_failure_o_excl_write": True,
        "failure_document_written_o_excl_after_partial_observation_snapshot": True,
        "events_directory_direct_entry_kind": "FILE",
        "events_directory_direct_entry_count_cap": MAX_EVENT_COUNT,
        "failure_artifact_observation_row_cap": (
            FAILURE_ARTIFACT_OBSERVATION_ROW_CAP
        ),
        "failure_artifact_metadata_byte_cap": FAILURE_ARTIFACT_METADATA_BYTE_CAP,
        "failure_directory_entry_cap": FAILURE_DIRECTORY_ENTRY_CAP,
        "failure_directory_entry_name_total_byte_cap": (
            FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        ),
        "failure_directory_entry_name_worst_case_json_escape_factor": 6,
        "failure_directory_entry_name_worst_case_escaped_bytes_at_cap": (
            6 * FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        ),
        "failure_worst_case_names_plus_bounded_metadata_fit_emergency_reserve": (
            True
        ),
        "failure_artifact_streaming_hash_byte_cap": (
            FAILURE_ARTIFACT_HASH_BYTE_CAP
        ),
        "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
        "partial_artifact_observations_sorted_unique_nonempty": True,
        "regular_file_present_requires_mode_nlink_byte_count_and_streaming_sha256": (
            True
        ),
        "directory_present_requires_mode_nlink_and_sorted_unique_bounded_entries": (
            True
        ),
        "absent_state_carries_no_invented_metadata": True,
        "linked_or_nonregular_state_carries_no_digest_or_directory_entries": True,
        "read_error_state_requires_bounded_type_and_message": True,
        "failure_cgroup_observation_nullable": True,
        "failure_cgroup_observation_is_best_effort_raw_cleanup_observation": True,
        "failure_cgroup_cleanup_outcome_fields": [
            "kill_outcome",
            "reap_outcome",
            "close_outcome",
        ],
        "failure_observation_error_count_cap": 32,
        "failure_observation_error_byte_cap_each": 512,
        "success_evidence_inventory_document_count": SUCCESS_EVIDENCE_DOCUMENT_COUNT,
        "failure_observations_in_success_evidence_inventory": False,
        "failure_artifact_observations_are_campaign_success_authority": False,
        "failure_cgroup_observation_is_campaign_success_receipt": False,
        "failure_state_issues_counter_records": False,
        "verification_failure_schema": VERIFICATION_FAILURE_SCHEMA,
        "verification_failure_domain": (
            domains.CONSTRUCTION_K7_FAILURE_V180R12R4_DOMAIN
        ),
        "verification_failure_fields": sorted(VERIFICATION_FAILURE_FIELDS),
        "verification_failure_artifact_observation_rows": [
            {
                "relative_path": relative_path,
                "kind": kind,
                "byte_cap": byte_cap,
            }
            for relative_path, kind, byte_cap in (
                VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
            )
        ],
        "verification_failure_artifact_observation_row_count": len(
            VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS
        ),
        "verification_failure_observation_boundary": (
            VERIFICATION_FAILURE_OBSERVATION_BOUNDARY
        ),
        "verification_failure_self_path_absent_at_observation_boundary": True,
        "verification_failure_written_o_excl_after_observation_snapshot": True,
        "verification_failure_attempt_id_nullable_until_terminal_stable_read": True,
        "verification_failure_launch_attempt_id_is_current_exact_identity": True,
        "verification_failure_file_hashes_are_constant_memory_streaming": True,
        "verification_failure_observation_stream_chunk_bytes": (
            VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES
        ),
        "verification_failure_directory_entry_count_cap": (
            VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP
        ),
        "verification_failure_directory_name_total_byte_cap": (
            VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
        ),
        "verification_failure_directory_name_worst_case_json_escape_factor": 6,
        "verification_failure_directory_name_worst_case_escaped_bytes_at_cap": (
            6 * VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP
        ),
        "verification_failure_worst_case_names_plus_bounded_metadata_fit_"
        "emergency_reserve": True,
        "verification_failure_watchdog_cleanup_fields": sorted(
            VERIFICATION_FAILURE_WATCHDOG_CLEANUP_FIELDS
        ),
        "verification_failure_watchdog_secondary_fields": sorted(
            VERIFICATION_FAILURE_WATCHDOG_SECONDARY_FIELDS
        ),
        "verification_failure_watchdog_secondary_observation_cap": (
            VERIFICATION_FAILURE_WATCHDOG_SECONDARY_OBSERVATION_CAP
        ),
        "verification_failure_memory_reserve_bytes": (
            FAILURE_EMERGENCY_RESERVE_BYTES
        ),
        "verification_failure_cleanup_order": [
            "NEUTRALIZE_WATCHDOG_USING_PREALLOCATED_SLOTS",
            "RELEASE_FAILURE_MEMORY_RESERVE",
            "RESTORE_WATCHDOG_AND_FORMAT_FAILURE",
        ],
        "verification_failure_is_campaign_actual_measurement": False,
        "verification_failure_is_campaign_success_authority": False,
        "same_failure_identity_rerun_allowed": False,
        "success_inventory_denominator_changed_by_failure_observations": False,
        "outcome_documents_present": False,
        "outcome_free": True,
    }


def source_closure_contract_v180r12r4() -> dict[str, Any]:
    """Return precommitted closure requirements, not a source outcome."""

    return {
        "schema": "acfqp.v180r12r4_source_closure_contract.v1",
        "required_static_roots": list(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "required_static_root_count": len(SOURCE_CLOSURE_REQUIRED_ROOTS),
        "transitive_local_import_closure_required": True,
        "regular_symlink_free_stable_reads_required": True,
        "relative_paths_sorted_unique_required": True,
        "module_count_cap": 4_096,
        "total_byte_count_cap": 128 * 1024 * 1024,
        "authorization_self_source_excluded_from_initial_fixed_point": True,
        "authorization_self_source_bound_by_post_prereg_evidence_freeze": True,
        "normalized_wrapper_literal_freeze_required": True,
        "expected_source_closure_id": ZERO_ID,
        "expected_source_closure_sha256": ZERO_ID,
        "expected_source_closure_file_count": 0,
        "expected_source_closure_total_byte_count": 0,
        "source_closure_identity_frozen": False,
        "placeholder_only": True,
    }


def worker_import_contract_v180r12r4() -> dict[str, Any]:
    return {
        "schema": "acfqp.v180r12r4_worker_import_contract.v1",
        "allowed_local_imports": list(WORKER_ALLOWED_LOCAL_IMPORTS),
        "forbidden_imports": list(WORKER_FORBIDDEN_IMPORTS),
        "repo_and_runtime_sources_precompiled_before_attempt": True,
        "lazy_local_imports_after_attempt_open_forbidden": True,
        "producer_or_heavy_verifier_import_forbidden": True,
        "import_manifest_replayed_before_independent_counter_pass": True,
    }


def successful_event_schedule_template_v180r12r4() -> list[dict[str, Any]]:
    """Return the exact ID-free expansion of 314 operations into 625 events."""

    operations = ledger_contract.build_campaign_operation_schedule_v180r12r4(
        ZERO_ID
    )
    operations_by_id = {row.operation_id: row for row in operations}
    events = ledger_contract.build_campaign_success_event_schedule_v180r12r4(
        ZERO_ID
    )
    if len(operations_by_id) != len(operations):
        _fail("V180r12r4 operation schedule identities are not unique")
    result: list[dict[str, Any]] = []
    for sequence, event in enumerate(events):
        operation = operations_by_id.get(event.operation_id)
        if operation is None:
            _fail("V180r12r4 event schedule references an unknown operation")
        result.append(
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
    return result


def event_grammar_v180r12r4() -> dict[str, Any]:
    successful_event_schedule = successful_event_schedule_template_v180r12r4()
    return {
        "schema": "acfqp.v180r12r4_campaign_ledger_event_grammar.v1",
        "phase_order": list(PHASE_ORDER),
        "phase_order_is_monotone": True,
        "required_event_kinds_are_not_a_one_each_total_order": True,
        "successful_expanded_event_schedule_order_is_exact": True,
        "event_fields": list(EVENT_FIELDS),
        "event_payload_fields": list(EVENT_PAYLOAD_FIELDS),
        "actor_roles": list(ACTOR_ROLES),
        "trusted_observer_owns_all_durable_event_files_and_acks": True,
        "supervisor_and_worker_submit_observations_only": True,
        "supervisor_forwards_worker_observations_to_observer": True,
        "measured_children_append_durable_event_files": False,
        "auxiliary_value_fields": list(AUXILIARY_VALUE_FIELDS),
        "auxiliary_values_sorted_unique_by_name": True,
        "auxiliary_value_types": ["NONNEGATIVE_INTEGER", "STRING", "BOOLEAN", "NULL"],
        "successful_event_auxiliary_values_exactly_empty": True,
        "successful_event_auxiliary_keysets": [
            {"event_kind": event_kind, "auxiliary_names": []}
            for event_kind in REQUIRED_EVENT_KINDS
        ],
        "nonempty_successful_event_auxiliary_values_forbidden": True,
        "outcome_codes": list(OUTCOME_CODES),
        "successful_ledger_forbidden_outcome_codes": list(
            SUCCESS_FORBIDDEN_OUTCOME_CODES
        ),
        "required_event_kinds": list(REQUIRED_EVENT_KINDS),
        "event_kind_phases": [
            {"event_kind": kind, "allowed_phases": list(phases)}
            for kind, phases in EVENT_KIND_PHASES
        ],
        "event_kind_role_phases": [
            {
                "event_kind": kind,
                "allowed_role_phases": [
                    {"actor_role": role, "phase": phase} for role, phase in pairs
                ],
            }
            for kind, pairs in EVENT_KIND_ROLE_PHASES
        ],
        "successful_event_cardinalities": [
            {"event_kind": kind, "count": count}
            for kind, count in SUCCESS_EVENT_CARDINALITIES
        ],
        "successful_minimum_event_count": SUCCESS_MINIMUM_EVENT_COUNT,
        "successful_exact_event_count": SUCCESS_EXACT_EVENT_COUNT,
        "successful_extra_events_forbidden": True,
        "successful_event_order_is_exact": True,
        "successful_event_schedule_template": successful_event_schedule,
        "successful_event_schedule_template_count": len(
            successful_event_schedule
        ),
        "successful_event_schedule_operation_ids_present": False,
        "successful_event_schedule_runtime_operation_ids_derived_from_attempt": True,
        "successful_event_evidence_requirements": [
            {
                "event_kind": event_kind,
                "evidence_type": evidence_type,
                "event_count": count,
                "evidence_id_requirement": (
                    "REQUIRED_REGISTERED_UNIQUE"
                    if evidence_type is not None
                    else "NULL"
                ),
            }
            for event_kind, evidence_type, count in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS
        ],
        "successful_nonnull_event_evidence_count": (
            SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT
        ),
        "successful_null_event_evidence_count": SUCCESS_NULL_EVENT_EVIDENCE_COUNT,
        "successful_event_evidence_id_must_be_issued_before_event_append": True,
        "successful_event_may_reference_not_yet_issued_evidence": False,
        "attempt_open_record_written_o_excl_before_cgroup_creation": True,
        "attempt_open_record_contains_cgroup_topology_receipt_id": False,
        "intent_event_evidence_ids_are_null": True,
        "ledger_closed_evidence_id_is_null_to_avoid_self_cycle": True,
        "intent_outcome_pairs": [
            {"intent_kind": intent, "outcome_kind": outcome}
            for intent, outcome in INTENT_OUTCOME_PAIRS
        ],
        "intent_outcome_operation_id_exact_pairing_required": True,
        "operation_ids_unique_across_distinct_operations": True,
        "sequence_starts_at_zero_and_is_contiguous": True,
        "first_previous_event_id_is_null": True,
        "later_previous_event_id_equals_exact_predecessor": True,
        "event_id_is_registered_content_id": True,
        "monotonic_ns_strictly_increasing": True,
        "attempt_open_count": 1,
        "source_input_read_chain_count": 2,
        "staged_worker_input_read_chain_count": 2,
        "subject_readback_chain_count": 1,
        "total_input_read_chain_count": 5,
        "stage_write_mount_chain_count": 2,
        "process_birth_reap_chain_count": 2,
        "worker_process_birth_intent_success_sequence": 29,
        "worker_process_birth_preregistered_pre_birth_effect": {
            "effect": "SUBJECT_TEMP_O_EXCL_PREOPEN_AND_PARENT_DIRECTORY_FSYNC",
            "after_durable_event_ack_sequence": 29,
            "before_clone": True,
            "exact_occurrence_count": 1,
            "failure_preserves_durable_prefix_through_sequence": 29,
            "failure_requires_typed_partial_observation": True,
        },
        "process_role_order": list(PROCESS_ROLE_ORDER),
        "cgroup_role_order": list(CGROUP_ROLE_ORDER),
        "cgroup_role_dev_inode_facts_required": True,
        "measurement_root_and_sibling_leaf_topology_required": True,
        "measurement_root_must_remain_process_empty": True,
        "supervisor_and_worker_are_sibling_leaves": True,
        "root_and_leaf_populated_zero_required_before_cgroup_observed": True,
        "mount_open_measured_value_is_current_aggregate_visible_bytes": True,
        "successful_mount_open_measured_values_in_exact_order": [
            PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT,
            PREDECESSOR_INPUT_TOTAL_BYTE_COUNT,
        ],
        "mount_close_measured_value_is_null": True,
        "successful_mount_close_measured_values_in_exact_order": [None, None],
        "mount_open_occurs_after_supervisor_birth": True,
        "mount_open_attests_sealed_payload_fd_visible_in_supervisor_and_root": True,
        "mount_open_designates_inherited_worker_fd": True,
        "mount_open_claims_worker_visibility_before_worker_birth": False,
        "worker_checks_inherited_read_only_dev_inode_before_each_staged_read": True,
        "mount_close_occurs_after_subject_commit": True,
        "mounted_bytes_peak_replays_unique_root_visible_payload_intervals": True,
        "cgroup_observed_measured_value_is_memory_peak_bytes": True,
        "cgroup_observed_pids_peak_auxiliary_required": False,
        "cgroup_observed_pids_peak_is_in_registered_evidence_document": True,
        "subject_result_preopened_o_excl_by_supervisor": True,
        "subject_write_pair_phase": "WORKER",
        "subject_write_pair_actor_role": "WORKER",
        "subject_commit_phase": "COMMIT",
        "subject_commit_actor_role": "SUPERVISOR",
        "subject_commit_requires_supervisor_readback_fsync_chmod_and_dir_fsync": True,
        "fallible_paired_operation_count": 307,
        "fallible_paired_operation_scope": (
            "EXACT_REGISTERED_IO_SEMANTIC_HASH_INTEGRITY_PROTOCOL_PROCESS_"
            "AND_SUBJECT_WRITE_SITES"
        ),
        "all_307_fallible_paired_operation_sites_require_durable_intent_ack_"
        "before_listed_operation": True,
        "every_fallible_paired_operation_emits_exact_intent_then_outcome": True,
        "deterministic_local_parse_shape_and_subject_computation_emits_separate_"
        "ledger_event": False,
        "failure_between_registered_hooks_preserves_current_phase_typed_failure_"
        "and_exact_durable_prefix": True,
        "failure_between_registered_hooks_can_claim_success": False,
        "process_birth_operation_count": 2,
        "process_birth_operations_emit_intent_outcome_then_reap": True,
        "mount_interval_operation_count": 2,
        "mount_interval_operations_emit_open_then_close": True,
        "mount_interval_operations_use_open_close_not_intent_outcome": True,
        "singleton_operation_count": 5,
        "singleton_operation_slots": [
            "ATTEMPT",
            "SUBJECT_COMMIT",
            "WINDOW",
            "CGROUP",
            "LEDGER",
        ],
        "singleton_operations_emit_one_event_each": True,
        "singleton_operations_are_post_effect_atomic_observations_without_"
        "intent_claim": True,
        "unqualified_every_operation_intent_outcome_claim": False,
        "ledger_and_outer_terminal_output_bytes_are_instrumentation_overhead": True,
    }


def measurement_derivation_contract_v180r12r4() -> list[dict[str, Any]]:
    return [
        {
            "path": "common.hash_invocations",
            "rule": "COUNT_SUCCESSFUL_SEMANTIC_HASH_OUTCOME_EVENTS",
            "successful_exact_value": SEMANTIC_HASH_OPERATION_COUNT,
        },
        {
            "path": "common.integrity_checks",
            "rule": "COUNT_SUCCESSFUL_INTEGRITY_CHECK_OUTCOME_EVENTS",
            "successful_exact_value": INTEGRITY_CHECK_OPERATION_COUNT,
        },
        {
            "path": "common.protocol_checks",
            "rule": "COUNT_SUCCESSFUL_PROTOCOL_CHECK_OUTCOME_EVENTS",
            "successful_exact_value": PROTOCOL_CHECK_OPERATION_COUNT,
        },
        {
            "path": "io.mounted_bytes_peak",
            "rule": "MAX_MOUNT_VISIBILITY_OPEN_AGGREGATE_VISIBLE_BYTES",
            "successful_exact_value": SUCCESS_MOUNTED_BYTES_PEAK,
            "two_payload_intervals_overlap": True,
        },
        {
            "path": "io.output_bytes",
            "rule": "SUM_SUBJECT_WRITE_OUTCOME_RETURNED_BYTES",
            "successful_value_formula": "SUBJECT_RESULT_BYTE_COUNT",
            "successful_value_strictly_positive": True,
        },
        {
            "path": "io.read_bytes",
            "rule": "SUM_INPUT_READ_OUTCOME_RETURNED_BYTES",
            "successful_value_formula": (
                "405014_PLUS_SUBJECT_RESULT_BYTE_COUNT"
            ),
            "successful_fixed_addend": SUCCESS_READ_BYTES_FIXED_ADDEND,
        },
        {
            "path": "io.staged_bytes",
            "rule": "SUM_STAGE_WRITE_OUTCOME_RETURNED_BYTES",
            "successful_exact_value": SUCCESS_STAGED_BYTE_COUNT,
        },
        {
            "path": "memory.working_bytes_peak",
            "rule": "SAME_MEASUREMENT_ROOT_CGROUP_MEMORY_PEAK_AFTER_REAP",
            "successful_value_strictly_positive": True,
            "successful_value_upper_bound_inclusive": MEMORY_MAX_BYTES,
        },
        {
            "path": "process.launches",
            "rule": "COUNT_SUCCESSFUL_PIDFD_BOUND_PROCESS_BIRTH_OUTCOMES",
            "successful_exact_value": 2,
        },
    ]


def operation_manifest_v180r12r4() -> dict[str, Any]:
    schedule = ledger_contract.build_campaign_operation_schedule_v180r12r4(ZERO_ID)
    return {
        "schema": "acfqp.v180r12r4_actual_operation_manifest.v1",
        "operation_schedule_template": [
            {
                "slot": row.slot,
                "family": row.family,
                "ordinal": row.ordinal,
                "phase": row.phase,
                "actor_role": row.actor_role,
            }
            for row in schedule
        ],
        "operation_schedule_template_count": len(schedule),
        "semantic_operation_count": (
            SEMANTIC_HASH_OPERATION_COUNT
            + INTEGRITY_CHECK_OPERATION_COUNT
            + PROTOCOL_CHECK_OPERATION_COUNT
        ),
        "lifecycle_operation_count": (
            len(schedule)
            - SEMANTIC_HASH_OPERATION_COUNT
            - INTEGRITY_CHECK_OPERATION_COUNT
            - PROTOCOL_CHECK_OPERATION_COUNT
        ),
        "operation_ids_present_in_protocol_template": False,
        "runtime_operation_ids_derived_only_after_exact_attempt_id_exists": True,
        "semantic_hash_operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS),
        "semantic_hash_operation_count": SEMANTIC_HASH_OPERATION_COUNT,
        "semantic_hash_operation_families": [
            {
                "family": family,
                "count": count,
                "phase": phase,
                "actor_role": actor_role,
            }
            for family, count, phase, actor_role in SEMANTIC_HASH_OPERATION_FAMILIES
        ],
        "integrity_check_operation_labels": list(INTEGRITY_CHECK_OPERATION_LABELS),
        "integrity_check_operation_count": INTEGRITY_CHECK_OPERATION_COUNT,
        "integrity_check_operation_families": [
            {
                "family": family,
                "count": count,
                "phase": phase,
                "actor_role": actor_role,
            }
            for family, count, phase, actor_role in INTEGRITY_CHECK_OPERATION_FAMILIES
        ],
        "protocol_check_families": list(PROTOCOL_CHECK_FAMILIES),
        "protocol_check_operation_labels": list(PROTOCOL_CHECK_OPERATION_LABELS),
        "protocol_check_operation_count": PROTOCOL_CHECK_OPERATION_COUNT,
        "operation_role_phase_segments": [
            {
                "family": "SEMANTIC_HASH",
                "actor_role": "SUPERVISOR",
                "phase": "STAGE",
                "operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS[:2]),
                "operation_count": 2,
            },
            {
                "family": "SEMANTIC_HASH",
                "actor_role": "WORKER",
                "phase": "WORKER",
                "operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS[2:-1]),
                "operation_count": 134,
            },
            {
                "family": "SEMANTIC_HASH",
                "actor_role": "SUPERVISOR",
                "phase": "COMMIT",
                "operation_labels": list(SEMANTIC_HASH_OPERATION_LABELS[-1:]),
                "operation_count": 1,
            },
            {
                "family": "INTEGRITY_CHECK",
                "actor_role": "SUPERVISOR",
                "phase": "STAGE",
                "operation_labels": list(INTEGRITY_CHECK_OPERATION_LABELS[:6]),
                "operation_count": 6,
            },
            {
                "family": "INTEGRITY_CHECK",
                "actor_role": "WORKER",
                "phase": "WORKER",
                "operation_labels": list(INTEGRITY_CHECK_OPERATION_LABELS[6:-2]),
                "operation_count": 137,
            },
            {
                "family": "INTEGRITY_CHECK",
                "actor_role": "SUPERVISOR",
                "phase": "COMMIT",
                "operation_labels": list(INTEGRITY_CHECK_OPERATION_LABELS[-2:]),
                "operation_count": 2,
            },
            {
                "family": "PROTOCOL_CHECK",
                "actor_role": "WORKER",
                "phase": "WORKER",
                "operation_labels": list(PROTOCOL_CHECK_OPERATION_LABELS),
                "operation_count": 15,
            },
        ],
        "inner_content_id_operation_suffixes": list(
            INNER_CONTENT_ID_OPERATION_SUFFIXES
        ),
        "inner_content_id_operation_count": len(
            INNER_CONTENT_ID_OPERATION_SUFFIXES
        ),
        "fallible_paired_operation_count": 307,
        "every_fallible_paired_operation_requires_one_intent_and_one_success_"
        "or_pass_outcome": True,
        "mount_interval_operation_count": 2,
        "mount_interval_operations_use_open_close_not_intent_outcome": True,
        "singleton_operation_count": 5,
        "singleton_operations_are_post_effect_atomic_observations_without_"
        "intent_claim": True,
        "unqualified_every_operation_intent_outcome_claim": False,
        "operation_id_order_is_exact_manifest_order": True,
        "lexical_operation_id_sort_required": False,
        "operation_labels_are_exact_unique_across_all_families": True,
        "runtime_operation_id_derivation": (
            "REGISTERED_CONTENT_ID_OF_ATTEMPT_ID_SLOT_FAMILY_AND_ORDINAL"
        ),
        "manifest_labels_are_runtime_operation_ids": False,
        "grouped_inner_content_id_operation_forbidden": True,
        "unmanifested_successful_check_operation_forbidden": True,
    }


def _resource_contract() -> dict[str, Any]:
    return {
        "wall_timeout_seconds": WALL_TIMEOUT_SECONDS,
        "wall_timeout_mechanism": "MONOTONIC_DEADLINE_AND_PARENT_ENFORCEMENT",
        "memory_max_bytes": MEMORY_MAX_BYTES,
        "address_space_hard_cap_bytes": ADDRESS_SPACE_HARD_CAP_BYTES,
        "address_space_cap_mechanism": "RLIMIT_AS",
        "pids_max": PIDS_MAX,
        "input_file_byte_cap": INPUT_FILE_BYTE_CAP,
        "input_file_count": 2,
        "input_total_byte_cap": INPUT_TOTAL_BYTE_CAP,
        "subject_result_byte_cap": SUBJECT_RESULT_BYTE_CAP,
        "subject_result_runtime_byte_cap": SUBJECT_RESULT_RUNTIME_BYTE_CAP,
        "runtime_ipc_frame_byte_cap": FRAME_BYTE_CAP,
        "sock_seqpacket_buffer_request_bytes": (
            SOCK_SEQPACKET_BUFFER_REQUEST_BYTES
        ),
        "sock_seqpacket_effective_min_bytes": (
            SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES
        ),
        "sock_seqpacket_buffer_applies_to_both_endpoints_of_both_pairs": True,
        "sock_seqpacket_buffers_configured_and_read_back_before_clone_or_send": True,
        "sock_seqpacket_insufficient_effective_buffer_fails_before_child_creation": True,
        "terminal_byte_cap": TERMINAL_BYTE_CAP,
        "verification_byte_cap": VERIFICATION_BYTE_CAP,
        "evidence_inventory_bundle_byte_cap": (
            EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP
        ),
        "execution_closure_byte_cap": EXECUTION_CLOSURE_BYTE_CAP,
        "os_receipt_bundle_byte_cap": OS_RECEIPT_BUNDLE_BYTE_CAP,
        "ledger_closure_byte_cap": LEDGER_CLOSURE_BYTE_CAP,
        "stdout_byte_cap": STDOUT_BYTE_CAP,
        "stderr_byte_cap": STDERR_BYTE_CAP,
        "failure_emergency_reserve_bytes": FAILURE_EMERGENCY_RESERVE_BYTES,
        "failure_message_byte_cap": FAILURE_MESSAGE_BYTE_CAP,
        "failure_artifact_observation_row_cap": (
            FAILURE_ARTIFACT_OBSERVATION_ROW_CAP
        ),
        "failure_artifact_metadata_byte_cap": FAILURE_ARTIFACT_METADATA_BYTE_CAP,
        "failure_directory_entry_cap": FAILURE_DIRECTORY_ENTRY_CAP,
        "failure_directory_entry_name_total_byte_cap": (
            FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP
        ),
        "failure_artifact_streaming_hash_byte_cap": (
            FAILURE_ARTIFACT_HASH_BYTE_CAP
        ),
        "max_event_count": MAX_EVENT_COUNT,
        "max_event_byte_count": MAX_EVENT_BYTE_COUNT,
        "max_ledger_byte_count": MAX_LEDGER_BYTE_COUNT,
        "caps_may_be_lowered_before_identity_freeze": True,
        "caps_may_never_be_raised_under_frozen_identity": True,
        "clone3_clone_into_cgroup_required": True,
        "pidfd_required": True,
        "measurement_root_memory_max_required": True,
        "measurement_root_pids_max_required": True,
        "memory_peak_read_from_same_measurement_root_after_both_reaps": True,
        "pids_peak_read_from_same_measurement_root_after_both_reaps": True,
        "ledger_observer_overhead_is_campaign_actual_measurement": False,
    }


def build_campaign_measurement_protocol_v180r12r4(
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
) -> dict[str, Any]:
    if EXPECTED_PROTOCOL_ID != ZERO_ID:
        require_frozen_protocol_final_anchor_set_v180r12r4()
    cgroup_fact = validate_cgroup_parent_fact_v180r12r4(cgroup_parent_fact)
    capability_fact = validate_runtime_capability_fact_v180r12r4(
        runtime_capability_fact
    )
    if not (
        cgroup_fact["owner_uid"] == capability_fact["uid"]
        and cgroup_fact["owner_gid"] == capability_fact["gid"]
        and cgroup_fact["mode"] & (stat.S_IWUSR | stat.S_IXUSR)
        == (stat.S_IWUSR | stat.S_IXUSR)
    ):
        _fail("cgroup parent owner/runtime identity or owner permissions changed")
    service_context_capture = service_context_capture_contract_v180r12r4()
    if not (
        cgroup_fact == service_context_capture["cgroup_parent_fact"]
        and capability_fact
        == service_context_capture["runtime_capability_fact"]
    ):
        _fail(
            "cgroup parent and runtime capability facts do not exact-join the "
            "same V180r12r4r5 source-bound service-context capture"
        )
    attempt_identity_contract = (
        campaign_measurement_attempt_identity_contract_v180r12r4()
    )
    semantic_hash_scope = semantic_hash_counter_scope_contract_v180r12r4()
    predecessor = _predecessor_evidence_contract()
    failed_dispatch = failed_dispatch_repair_lineage_contract_v180r12r4()
    failed_external_replay = (
        failed_external_replay_repair_lineage_contract_v180r12r4()
    )
    failed_scientific_birth = (
        failed_scientific_birth_repair_lineage_contract_v180r12r4()
    )
    failed_ordinal8 = failed_ordinal8_repair_lineage_contract_v180r12r4()
    failed_ordinal9 = failed_ordinal9_repair_lineage_contract_v180r12r4()
    failed_ordinal10 = failed_ordinal10_repair_lineage_contract_v180r12r4()
    failed_ordinal11 = failed_ordinal11_repair_lineage_contract_v180r12r4()
    failed_ordinal12 = failed_ordinal12_repair_lineage_contract_v180r12r4()
    failed_ordinal13 = failed_ordinal13_repair_lineage_contract_v180r12r4()
    runner_execution_envelope = (
        source_bound_runner_execution_envelope_contract_v180r12r4()
    )
    if not (
        CAMPAIGN_PATH_COUNT == len(CAMPAIGN_PATHS)
        and len(set(CAMPAIGN_PATHS)) == CAMPAIGN_PATH_COUNT
        and len(INNER_CONTENT_ID_OPERATION_SUFFIXES) == 129
        and len(SEMANTIC_HASH_OPERATION_LABELS) == SEMANTIC_HASH_OPERATION_COUNT
        and len(INTEGRITY_CHECK_OPERATION_LABELS) == INTEGRITY_CHECK_OPERATION_COUNT
        and len(PROTOCOL_CHECK_OPERATION_LABELS) == PROTOCOL_CHECK_OPERATION_COUNT
        and INNER_CONTENT_ID_OPERATION_SUFFIXES
        == worker_contract.INNER_CONTENT_ID_OPERATION_SUFFIXES
        and SEMANTIC_HASH_OPERATION_LABELS
        == worker_contract.SEMANTIC_HASH_OPERATION_LABELS
        and INTEGRITY_CHECK_OPERATION_LABELS
        == worker_contract.INTEGRITY_CHECK_OPERATION_LABELS
        and PROTOCOL_CHECK_FAMILIES == worker_contract.PROTOCOL_CHECK_FAMILIES
        and PROTOCOL_CHECK_OPERATION_LABELS
        == worker_contract.PROTOCOL_CHECK_OPERATION_LABELS
        and SEMANTIC_HASH_OPERATION_FAMILIES == ledger_contract.HASH_OPERATION_FAMILIES
        and INTEGRITY_CHECK_OPERATION_FAMILIES
        == ledger_contract.INTEGRITY_OPERATION_FAMILIES
        and PROTOCOL_CHECK_FAMILIES == ledger_contract.PROTOCOL_CHECK_FAMILIES
        and len(
            ledger_contract.build_campaign_operation_schedule_v180r12r4(ZERO_ID)
        )
        == 314
        and len(
            ledger_contract.build_campaign_success_event_schedule_v180r12r4(
                ZERO_ID
            )
        )
        == SUCCESS_EXACT_EVENT_COUNT
        and len(successful_event_schedule_template_v180r12r4())
        == SUCCESS_EXACT_EVENT_COUNT
        and tuple(
            row["sequence"]
            for row in successful_event_schedule_template_v180r12r4()
        )
        == tuple(range(SUCCESS_EXACT_EVENT_COUNT))
        and ledger_contract.SUCCESS_EVENT_COUNT == SUCCESS_EXACT_EVENT_COUNT
        and ledger_contract.SUCCESS_EVENT_EVIDENCE_COUNT
        == SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT
        and ledger_contract.SUCCESS_NULL_EVIDENCE_COUNT
        == SUCCESS_NULL_EVENT_EVIDENCE_COUNT
        and ledger_contract.CAMPAIGN_EVIDENCE_DOCUMENT_COUNT
        == SUCCESS_EVIDENCE_DOCUMENT_COUNT
        and ledger_contract.PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        == PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        and ledger_contract.PREDECESSOR_STRUCTURAL_OBLIGATION_COUNT
        == PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        and ledger_contract.PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        == PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        and ledger_contract.SUCCESSOR_CAMPAIGN_ACTUAL_RECEIPT_COUNT
        == SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        and ledger_contract.COMBINED_SUCCESSOR_AUTHORITATIVE_RECEIPT_COUNT
        == SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT
        and ledger_contract.TERMINAL_INPUT_BYTE_COUNT
        == PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT
        and ledger_contract.VERIFICATION_INPUT_BYTE_COUNT
        == PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT
        and ledger_contract.TOTAL_STAGED_INPUT_BYTE_COUNT
        == PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
        and sum(row[1] for row in SEMANTIC_HASH_OPERATION_FAMILIES)
        == SEMANTIC_HASH_OPERATION_COUNT
        and sum(row[1] for row in INTEGRITY_CHECK_OPERATION_FAMILIES)
        == INTEGRITY_CHECK_OPERATION_COUNT
        and len(
            set(
                SEMANTIC_HASH_OPERATION_LABELS
                + INTEGRITY_CHECK_OPERATION_LABELS
                + PROTOCOL_CHECK_OPERATION_LABELS
            )
        )
        == (
            SEMANTIC_HASH_OPERATION_COUNT
            + INTEGRITY_CHECK_OPERATION_COUNT
            + PROTOCOL_CHECK_OPERATION_COUNT
        )
        and SUCCESS_EXACT_EVENT_COUNT == 625
        and SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT == 317
        and SUCCESS_NULL_EVENT_EVIDENCE_COUNT == 308
        and SUCCESS_EVIDENCE_DOCUMENT_COUNT == 328
        and SUCCESS_DIRECT_EVENT_EVIDENCE_DOCUMENT_COUNT == 317
        and SUCCESS_SUPPORT_EVIDENCE_DOCUMENT_COUNT == 11
        and len({row[0] for row in EVIDENCE_INVENTORY_ROWS})
        == len(EVIDENCE_INVENTORY_ROWS)
        and len({row[1] for row in EVIDENCE_INVENTORY_ROWS})
        == len(EVIDENCE_INVENTORY_ROWS)
        and len({row[2] for row in EVIDENCE_INVENTORY_ROWS})
        == len(EVIDENCE_INVENTORY_ROWS)
        and len({row[3] for row in EVIDENCE_INVENTORY_ROWS})
        == len(EVIDENCE_INVENTORY_ROWS)
        and len(
            worker_contract.EVIDENCE_DOCUMENT_CONTRACT_ROWS
            + supervisor_contract.EVIDENCE_DOCUMENT_CONTRACT_ROWS
        )
        == len(EVIDENCE_INVENTORY_ROWS)
        and set(
            worker_contract.EVIDENCE_DOCUMENT_CONTRACT_ROWS
            + supervisor_contract.EVIDENCE_DOCUMENT_CONTRACT_ROWS
        )
        == {row[:4] for row in EVIDENCE_INVENTORY_ROWS}
        and all(
            direct_event_reference_count
            == sum(
                event_count
                for _event_kind, required_type, event_count in (
                    SUCCESS_EVENT_EVIDENCE_REQUIREMENTS
                )
                if required_type == evidence_type
            )
            for (
                evidence_type,
                _schema,
                _domain_tag,
                _identity_field,
                _document_count,
                direct_event_reference_count,
            ) in EVIDENCE_INVENTORY_ROWS
        )
        and tuple(row[0] for row in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS)
        == tuple(row[0] for row in SUCCESS_EVENT_CARDINALITIES)
        and tuple(row[2] for row in SUCCESS_EVENT_EVIDENCE_REQUIREMENTS)
        == tuple(row[1] for row in SUCCESS_EVENT_CARDINALITIES)
        and PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        + SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        == SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT
        and PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT == 0
        and PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT == 9
        and PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT
        + PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT
        == PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
        and SUCCESS_READ_BYTES_FIXED_ADDEND
        == 2 * PREDECESSOR_INPUT_TOTAL_BYTE_COUNT
        and MAX_EVENT_COUNT >= SUCCESS_MINIMUM_EVENT_COUNT
        and INPUT_TOTAL_BYTE_CAP == 2 * INPUT_FILE_BYTE_CAP
        and PIDS_MAX == len(PROCESS_ROLE_ORDER)
        and failure_observation_contract_v180r12r4()[
            "success_evidence_inventory_document_count"
        ]
        == 328
        and failure_observation_contract_v180r12r4()[
            "failure_observations_in_success_evidence_inventory"
        ]
        is False
        and attempt_identity_contract["attempt_schema"]
        == domains.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA
        and attempt_identity_contract["attempt_domain"]
        == domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
        and attempt_identity_contract["domain_registry_value"]
        == attempt_identity_contract["attempt_domain"]
        and tuple(attempt_identity_contract["payload_fields"])
        == CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS
        and tuple(attempt_identity_contract["identity_input_fields"])
        == CAMPAIGN_MEASUREMENT_ATTEMPT_IDENTITY_INPUT_FIELDS
        and attempt_identity_contract["identity_input_count"] == 6
        and attempt_identity_contract["derive_api_is_registry_implementation"]
        is True
        and semantic_hash_scope["counted_operation_labels"]
        == list(SEMANTIC_HASH_OPERATION_LABELS)
        and semantic_hash_scope["counted_operation_count"]
        == SEMANTIC_HASH_OPERATION_COUNT
        and tuple(semantic_hash_scope["excluded_instrumentation_classes"])
        == SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES
        and len(SOURCE_CLOSURE_REQUIRED_ROOTS) == 28
        and V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH
        in SOURCE_CLOSURE_REQUIRED_ROOTS
        and failed_external_replay["scientific_attempt_record_present"] is False
        and failed_external_replay["scientific_occurrence_started"] is False
        and failed_external_replay["campaign_actual_measurement"] is False
        and failed_external_replay["measurement_cgroup_created"] is False
        and failed_external_replay[
            "all_required_successor_paths_absent_at_failure_freeze"
        ]
        is True
        and failed_external_replay["fresh_successor_identity_required"] is True
        and failed_scientific_birth["scientific_attempt_record_present"] is True
        and failed_scientific_birth["scientific_occurrence_started"] is True
        and failed_scientific_birth["durable_scientific_event_prefix_present"]
        is True
        and failed_scientific_birth["retained_event_count"] == 2
        and failed_scientific_birth["success_event_count"]
        == SUCCESS_EXACT_EVENT_COUNT
        and failed_scientific_birth["campaign_counter_records_issued"] is False
        and failed_scientific_birth["successful_ledger_claimed"] is False
        and failed_scientific_birth["producer_free_verification_attempted"]
        is False
        and failed_scientific_birth["same_campaign_attempt_rerun_forbidden"]
        is True
        and failed_scientific_birth["same_launch_attempt_rerun_forbidden"]
        is True
        and failed_scientific_birth["fresh_successor_identity_required"] is True
        and failed_scientific_birth["repair_scope"]
        == V180R12R3R2_REPAIR_SCOPE
        and failed_scientific_birth["exact_failing_syscall_proven"] is False
        and failed_ordinal8["campaign_attempt_id"]
        == V180R12R4R2_FAILED_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal8["campaign_failure_id"]
        == V180R12R4R2_FAILED_CAMPAIGN_FAILURE_ID
        and failed_ordinal8["inner_launch_failure_id"]
        == V180R12R4R2_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal8["outer_service_failure_id"]
        == V180R12R4R2_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal8["historical_failure_code_misclassified"] is True
        and failed_ordinal8["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal8["full_cgroup_conformance"] is False
        and failed_ordinal8["full_property_diagnostic_recorded"] is False
        and failed_ordinal8["counter_records_issued"] is False
        and failed_ordinal8["work_vectors_issued"] is False
        and failed_ordinal8["comparison_vectors_issued"] is False
        and failed_ordinal8["same_identity_rerun_forbidden"] is True
        and failed_ordinal8["fresh_successor_identity_required"] is True
        and failed_ordinal8["repair_scope"] == V180R12R4R3_REPAIR_SCOPE
        and failed_ordinal9["freeze_id"]
        == V180R12R4R4_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal9["logical_campaign_attempt_id"]
        == V180R12R4R4_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal9["campaign_attempt_artifact_present"] is False
        and failed_ordinal9["campaign_started"] is False
        and failed_ordinal9["campaign_ledger_event_count"] == 0
        and failed_ordinal9["inner_launch_failure_id"]
        == V180R12R4R4_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal9["outer_service_failure_id"]
        == V180R12R4R4_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal9["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal9["full_source_conformance"] is False
        and failed_ordinal9["postmortem_full_property_diagnostic_recorded"]
        is True
        and failed_ordinal9["counter_records_issued"] is False
        and failed_ordinal9["work_vectors_issued"] is False
        and failed_ordinal9["comparison_vectors_issued"] is False
        and failed_ordinal9["same_identity_rerun_forbidden"] is True
        and failed_ordinal9["fresh_successor_identity_required"] is True
        and failed_ordinal9["repair_scope"] == V180R12R4R4_REPAIR_SCOPE
        and failed_ordinal10["freeze_id"]
        == V180R12R4R5_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal10["logical_campaign_attempt_id"]
        == V180R12R4R5_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal10["campaign_attempt_artifact_present"] is False
        and failed_ordinal10["campaign_started"] is False
        and failed_ordinal10["campaign_ledger_event_count"] == 0
        and failed_ordinal10["inner_launch_failure_id"]
        == V180R12R4R5_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal10["outer_service_failure_id"]
        == V180R12R4R5_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal10["outer_service_unit_ownership_acquired"] is True
        and failed_ordinal10["full_source_conformance"] is True
        and failed_ordinal10["runtime_failure_generic_cause_recorded"] is True
        and failed_ordinal10["runtime_failure_property_snapshots_recorded"]
        is False
        and failed_ordinal10["runtime_failure_per_field_mismatch_recorded"]
        is False
        and failed_ordinal10["runtime_failure_exact_cause_dimension_recorded"]
        is False
        and failed_ordinal10["counter_records_issued"] is False
        and failed_ordinal10["work_vectors_issued"] is False
        and failed_ordinal10["comparison_vectors_issued"] is False
        and failed_ordinal10["same_identity_rerun_forbidden"] is True
        and failed_ordinal10["fresh_successor_identity_required"] is True
        and failed_ordinal10["repair_scope"] == V180R12R4R5_REPAIR_SCOPE
        and failed_ordinal11["freeze_id"]
        == V180R12R4R6_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal11["campaign_attempt_id"]
        == V180R12R4R6_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal11["scientific_attempt_opened"] is True
        and failed_ordinal11["completed_event_count"] == 1
        and failed_ordinal11["full_source_conformance"] is True
        and failed_ordinal11["full_host_conformance"] is True
        and failed_ordinal11["host_conformance_mismatch_count"] == 0
        and failed_ordinal11["host_conformance_cause"] is None
        and failed_ordinal11["full_t1_t2_conformance"] is False
        and failed_ordinal11["t1_t2_same_formal_service"] is True
        and failed_ordinal11["t1_t2_same_source_membership"] is True
        and failed_ordinal11["t1_t2_same_service_directory"] is True
        and failed_ordinal11["only_mismatch"]["field"] == "t2.pid"
        and failed_ordinal11["exact_failure_cause"]
        == "T1_T2_PID_ROLE_CONFLATION"
        and failed_ordinal11["distinct_process_roles"] is True
        and failed_ordinal11["predecessor_t2_schema"]
        == "acfqp.v180r12r4_production_runtime_placement_t2.v1"
        and failed_ordinal11["successor_t2_schema"]
        == PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA
        and failed_ordinal11["ordinal11_t3_present"] is False
        and failed_ordinal11["cleanup_complete"] is True
        and failed_ordinal11["counter_records_issued"] is False
        and failed_ordinal11["work_vectors_issued"] is False
        and failed_ordinal11["comparison_vectors_issued"] is False
        and failed_ordinal11["same_identity_rerun_forbidden"] is True
        and failed_ordinal11["fresh_successor_identity_required"] is True
        and failed_ordinal11["repair_scope"] == V180R12R4R6_REPAIR_SCOPE
        and failed_ordinal12["freeze_id"]
        == V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal12["campaign_attempt_id"]
        == V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal12["scientific_attempt_opened"] is True
        and failed_ordinal12["event_kinds"]
        == ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT"]
        and failed_ordinal12["completed_event_count"] == 2
        and failed_ordinal12["full_source_conformance"] is True
        and failed_ordinal12["full_host_conformance"] is True
        and failed_ordinal12["production_runtime_placement_t1_complete"] is True
        and failed_ordinal12["production_runtime_placement_t2_reached"] is False
        and failed_ordinal12["production_runtime_placement_t3_reached"] is False
        and failed_ordinal12["socket_capability_full_conformance"] is False
        and failed_ordinal12["socket_capability_mismatch_count"] == 6
        and failed_ordinal12["failure_stage"] == "SOCKET_BUFFER_CONFIGURATION"
        and failed_ordinal12["launch_child_created"] is False
        and failed_ordinal12["cleanup_complete"] is True
        and failed_ordinal12["counter_records_issued"] is False
        and failed_ordinal12["work_vectors_issued"] is False
        and failed_ordinal12["comparison_vectors_issued"] is False
        and failed_ordinal12["same_identity_rerun_forbidden"] is True
        and failed_ordinal12["fresh_successor_identity_required"] is True
        and failed_ordinal12["repair_scope"] == V180R12R4R7_REPAIR_SCOPE
        and failed_ordinal13["freeze_id"]
        == V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID
        and failed_ordinal13["campaign_attempt_id"]
        == V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID
        and failed_ordinal13["campaign_failure_id"]
        == V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID
        and failed_ordinal13["inner_launch_failure_id"]
        == V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID
        and failed_ordinal13["outer_service_failure_id"]
        == V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID
        and failed_ordinal13["scientific_attempt_opened"] is True
        and failed_ordinal13["event_kinds"]
        == ["ATTEMPT_OPEN", "PROCESS_BIRTH_INTENT", "PROCESS_BIRTH_OUTCOME"]
        and failed_ordinal13["completed_event_count"] == 3
        and failed_ordinal13["successful_process_birth_outcome_recorded"]
        is True
        and failed_ordinal13["full_source_conformance"] is True
        and failed_ordinal13["full_host_conformance"] is True
        and failed_ordinal13["production_runtime_placement_t1_complete"] is True
        and failed_ordinal13["production_unit_ownership_t1_acquired"] is True
        and failed_ordinal13["full_cgroup_topology_conformance_recorded"]
        is False
        and failed_ordinal13["source_binding_full_conformance"] is False
        and failed_ordinal13["source_binding_mismatch_count"] == 21
        and failed_ordinal13["first_source_binding_mismatch_index"] == 85
        and failed_ordinal13["first_source_binding_mismatch_module"]
        == "packaging"
        and failed_ordinal13["cleanup_complete"] is True
        and failed_ordinal13["counter_records_issued"] is False
        and failed_ordinal13["work_vectors_issued"] is False
        and failed_ordinal13["comparison_vectors_issued"] is False
        and failed_ordinal13["same_identity_rerun_forbidden"] is True
        and failed_ordinal13["fresh_successor_identity_required"] is True
        and failed_ordinal13["repair_scope"] == V180R12R4R8_REPAIR_SCOPE
        and runner_execution_envelope["module_type"] == "types.ModuleType"
        and tuple(runner_execution_envelope["target_order"])
        == SOURCE_BOUND_RUNNER_TARGET_ORDER
        and tuple(
            (row["target"], row["module_name"])
            for row in runner_execution_envelope["target_rows"]
        )
        == SOURCE_BOUND_RUNNER_MODULE_ROWS
        and tuple(runner_execution_envelope["exact_metadata_fields"])
        == SOURCE_BOUND_RUNNER_MODULE_METADATA_FIELDS
        and all(
            runner_execution_envelope[name] is True
            for name in (
                "registered_before_runner_exec",
                "registration_spans_exec_entrypoint_and_postchecks",
                "preexisting_registration_fails_before_mutation",
                "preexisting_registration_is_preserved",
                "replaced_deleted_or_metadata_drifted_registration_fails",
                "registration_removed_after_postchecks_on_success_or_failure",
                "runner_module_registration_leak_forbidden",
                "runner_primary_error_precedes_registration_secondary",
            )
        )
    ):
        _fail("V180r12r4 frozen denominator or event cap changed")

    slot_payload = {
        "schema": "acfqp.campaign_measurement_execution_slot.v180r12r4",
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "execution_nonce": EXECUTION_NONCE,
        "predecessor_production_aggregation_bundle_id": (
            V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID
        ),
        "predecessor_verification_id": V180R12R2_VERIFICATION_ID,
        "failed_predecessor_campaign_attempt_id": (
            failed_dispatch["campaign_attempt_id"]
        ),
        "failed_predecessor_launch_attempt_id": (
            failed_dispatch["launch_attempt_id"]
        ),
        "failed_predecessor_launch_failure_id": (
            failed_dispatch["launch_failure_id"]
        ),
        "historical_failed_scientific_birth_campaign_attempt_id": (
            failed_scientific_birth["campaign_attempt_id"]
        ),
        "historical_failed_scientific_birth_launch_attempt_id": (
            failed_scientific_birth["launch_attempt_id"]
        ),
        "historical_failed_scientific_birth_launch_failure_id": (
            failed_scientific_birth["launch_failure_id"]
        ),
        "historical_failed_ordinal8_campaign_attempt_id": (
            failed_ordinal8["campaign_attempt_id"]
        ),
        "historical_failed_ordinal8_campaign_failure_id": (
            failed_ordinal8["campaign_failure_id"]
        ),
        "historical_failed_ordinal8_inner_launch_failure_id": (
            failed_ordinal8["inner_launch_failure_id"]
        ),
        "historical_failed_ordinal8_outer_service_failure_id": (
            failed_ordinal8["outer_service_failure_id"]
        ),
        "historical_failed_ordinal9_freeze_id": failed_ordinal9["freeze_id"],
        "historical_failed_ordinal9_logical_campaign_attempt_id": (
            failed_ordinal9["logical_campaign_attempt_id"]
        ),
        "historical_failed_ordinal9_inner_launch_failure_id": (
            failed_ordinal9["inner_launch_failure_id"]
        ),
        "historical_failed_ordinal9_outer_service_failure_id": (
            failed_ordinal9["outer_service_failure_id"]
        ),
        "historical_failed_ordinal10_freeze_id": failed_ordinal10["freeze_id"],
        "historical_failed_ordinal10_logical_campaign_attempt_id": (
            failed_ordinal10["logical_campaign_attempt_id"]
        ),
        "historical_failed_ordinal10_inner_launch_failure_id": (
            failed_ordinal10["inner_launch_failure_id"]
        ),
        "historical_failed_ordinal10_outer_service_failure_id": (
            failed_ordinal10["outer_service_failure_id"]
        ),
        "historical_failed_ordinal11_freeze_id": failed_ordinal11["freeze_id"],
        "historical_failed_ordinal11_logical_campaign_attempt_id": (
            failed_ordinal11["campaign_attempt_id"]
        ),
        "historical_failed_ordinal11_inner_launch_failure_id": (
            failed_ordinal11["inner_launch_failure_id"]
        ),
        "historical_failed_ordinal11_outer_service_failure_id": (
            failed_ordinal11["outer_service_failure_id"]
        ),
        "historical_failed_ordinal12_freeze_id": failed_ordinal12["freeze_id"],
        "historical_failed_ordinal12_logical_campaign_attempt_id": (
            failed_ordinal12["campaign_attempt_id"]
        ),
        "historical_failed_ordinal12_campaign_failure_id": (
            failed_ordinal12["campaign_failure_id"]
        ),
        "historical_failed_ordinal12_inner_launch_failure_id": (
            failed_ordinal12["inner_launch_failure_id"]
        ),
        "historical_failed_ordinal12_outer_service_failure_id": (
            failed_ordinal12["outer_service_failure_id"]
        ),
        "immediate_failed_predecessor_freeze_id": failed_ordinal13[
            "freeze_id"
        ],
        "immediate_failed_predecessor_logical_campaign_attempt_id": (
            failed_ordinal13["campaign_attempt_id"]
        ),
        "immediate_failed_predecessor_campaign_failure_id": (
            failed_ordinal13["campaign_failure_id"]
        ),
        "immediate_failed_predecessor_inner_launch_failure_id": (
            failed_ordinal13["inner_launch_failure_id"]
        ),
        "immediate_failed_predecessor_outer_service_failure_id": (
            failed_ordinal13["outer_service_failure_id"]
        ),
        "pre_scientific_failed_predecessor_campaign_attempt_id": (
            failed_external_replay["campaign_attempt_id"]
        ),
        "pre_scientific_failed_predecessor_launch_attempt_id": (
            failed_external_replay["launch_attempt_id"]
        ),
        "pre_scientific_failed_predecessor_launch_failure_id": (
            failed_external_replay["launch_failure_id"]
        ),
        "measurement_subject": (
            CAMPAIGN_SCOPE_KIND
        ),
        "campaign_path_count": CAMPAIGN_PATH_COUNT,
        "service_context_capture_schema": service_context_capture[
            "capture_schema"
        ],
        "service_context_capture_purpose": service_context_capture[
            "capture_purpose"
        ],
        "service_context_capture_sha256": service_context_capture[
            "canonical_sha256"
        ],
        "cgroup_parent_fact": cgroup_fact,
        "runtime_capability_fact": capability_fact,
    }
    slot = {
        **slot_payload,
        "campaign_measurement_execution_slot_id": domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_V180R12R4_DOMAIN,
            slot_payload,
        ),
    }
    if (
        EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID != ZERO_ID
        and slot["campaign_measurement_execution_slot_id"]
        != EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
    ):
        _fail("V180r12r4 campaign measurement execution slot identity changed")

    payload = {
        "schema": "acfqp.campaign_measurement_protocol.v180r12r4",
        "identity_literals_frozen": EXPECTED_PROTOCOL_ID != ZERO_ID,
        "logical_occurrence_id": LOGICAL_OCCURRENCE_ID,
        "execution_nonce": EXECUTION_NONCE,
        "campaign_measurement_execution_slot": slot,
        "campaign_measurement_attempt_identity_contract": (
            attempt_identity_contract
        ),
        "fresh_execution_slot_count": 1,
        "predecessor_evidence": predecessor,
        "failed_dispatch_repair_lineage": failed_dispatch,
        "failed_external_replay_repair_lineage": failed_external_replay,
        "failed_scientific_birth_repair_lineage": failed_scientific_birth,
        "failed_ordinal8_repair_lineage": failed_ordinal8,
        "failed_ordinal9_repair_lineage": failed_ordinal9,
        "failed_ordinal10_repair_lineage": failed_ordinal10,
        "failed_ordinal11_repair_lineage": failed_ordinal11,
        "failed_ordinal12_repair_lineage": failed_ordinal12,
        "failed_ordinal13_repair_lineage": failed_ordinal13,
        "failed_v180r12r3_identity_rerun_forbidden": True,
        "failed_v180r12r3r1_identity_rerun_forbidden": True,
        "failed_v180r12r3r2_identity_rerun_forbidden": True,
        "failed_v180r12r4r2_ordinal8_identity_rerun_forbidden": True,
        "failed_v180r12r4r4_ordinal9_identity_rerun_forbidden": True,
        "failed_v180r12r4r5_ordinal10_identity_rerun_forbidden": True,
        "failed_v180r12r4r6_ordinal11_identity_rerun_forbidden": True,
        "failed_v180r12r4r7_ordinal12_identity_rerun_forbidden": True,
        "failed_v180r12r4r8_ordinal13_identity_rerun_forbidden": True,
        "fresh_v180r12r4_protocol_authorization_evidence_attempt_and_"
        "prelaunch_identities_required": True,
        "fresh_v180r12r4_physical_paths_and_identities_required": True,
        "repair_scope": V180R12R4_REPAIR_SCOPE,
        "repair_changes_campaign_path_roles_event_schedule_evidence_"
        "cardinality_or_reducers": False,
        "source_bound_runner_execution_envelope_contract": (
            runner_execution_envelope
        ),
        "measurement_subject_scope": slot_payload["measurement_subject"],
        "campaign_scope_kind": CAMPAIGN_SCOPE_KIND,
        "work_scope_kind": WORK_SCOPE_KIND,
        "counter_registry_reference": COUNTER_REGISTRY_REFERENCE,
        "measured_scope_is_fresh_replay_successor_overhead": True,
        "measured_scope_is_retroactive_v180r12r2_aggregation_cost": False,
        "v180r12r2_structural_declarations_promoted_to_measurements": False,
        "v180r12r2_producer_or_verifier_execution_permitted": False,
        "campaign_paths": list(CAMPAIGN_PATHS),
        "campaign_path_count": CAMPAIGN_PATH_COUNT,
        "route_kind": None,
        "route_free_campaign_scope_required": True,
        "event_grammar": event_grammar_v180r12r4(),
        "terminal_evidence_inventory_contract": (
            evidence_inventory_contract_v180r12r4()
        ),
        "campaign_subject_result_fields": sorted(
            CAMPAIGN_SUBJECT_RESULT_FIELDS
        ),
        "campaign_subject_result_echoes_authorization_evidence_and_transport_"
        "provenance": True,
        "measurement_derivation_contract": measurement_derivation_contract_v180r12r4(),
        "semantic_hash_counter_scope_contract": semantic_hash_scope,
        "successful_measurement_arithmetic": {
            "terminal_input_byte_count": PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT,
            "verification_input_byte_count": (
                PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT
            ),
            "input_total_byte_count": PREDECESSOR_INPUT_TOTAL_BYTE_COUNT,
            "io.staged_bytes": SUCCESS_STAGED_BYTE_COUNT,
            "io.mounted_bytes_peak": SUCCESS_MOUNTED_BYTES_PEAK,
            "io.output_bytes_formula": "SUBJECT_RESULT_BYTE_COUNT",
            "subject_result_byte_count_lower_bound_inclusive": 1,
            "subject_result_byte_count_upper_bound_inclusive": SUBJECT_RESULT_BYTE_CAP,
            "subject_result_physical_write_byte_count_upper_bound_inclusive": (
                SUBJECT_RESULT_RUNTIME_BYTE_CAP
            ),
            "subject_result_full_signed_seq608_event_proposal_byte_count_"
            "upper_bound_inclusive": FRAME_BYTE_CAP,
            "subject_result_full_signed_seq608_event_proposal_prevalidated_"
            "before_write": True,
            "subject_result_actual_write_chunk_schedule_equals_prevalidated_"
            "schedule": True,
            "io.read_bytes_fixed_addend": SUCCESS_READ_BYTES_FIXED_ADDEND,
            "io.read_bytes_formula": "405014_PLUS_SUBJECT_RESULT_BYTE_COUNT",
            "common.hash_invocations": SEMANTIC_HASH_OPERATION_COUNT,
            "common.integrity_checks": INTEGRITY_CHECK_OPERATION_COUNT,
            "common.protocol_checks": PROTOCOL_CHECK_OPERATION_COUNT,
            "process.launches": 2,
            "cgroup.pids_peak": 2,
            "memory.working_bytes_peak": "POSITIVE_OS_OBSERVED_AT_MOST_MEMORY_MAX",
        },
        "actual_operation_manifest": operation_manifest_v180r12r4(),
        "prelaunch_contract": prelaunch_contract_v180r12r4(),
        "durable_artifact_contract": durable_artifact_contract_v180r12r4(),
        "failure_observation_contract": failure_observation_contract_v180r12r4(),
        "resource_contract": _resource_contract(),
        "cgroup_parent_fact": cgroup_fact,
        "runtime_capability_fact": capability_fact,
        "service_context_capture_contract": service_context_capture,
        "cgroup_parent_and_runtime_facts_exact_join_same_source_bound_capture": (
            True
        ),
        "cgroup_parent_fact_bound_at_protocol_freeze": True,
        "cgroup_parent_identity_fields_except_observer_self_membership_must_be_"
        "reobserved_exactly_before_attempt": True,
        "cgroup_parent_reobserved_identity_fields": [
            field for field in CGROUP_PARENT_FACT_FIELDS
            if field != "self_membership"
        ],
        "cgroup_parent_owner_uid_equals_runtime_uid": True,
        "cgroup_parent_owner_gid_equals_runtime_gid": True,
        "cgroup_parent_owner_write_and_execute_required": True,
        "cgroup_parent_group_bits_are_not_permission_authority_when_owner_uid_"
        "matches": True,
        "self_membership_is_parent_identity": False,
        "frozen_self_membership_is_capture_provenance_only": True,
        "production_source_self_membership_is_verified_separately_at_t1_t2_t3": True,
        "measurement_root_created_empty_under_bound_parent": True,
        "measurement_root_children": list(CGROUP_ROLE_ORDER[1:]),
        "measurement_root_and_leaf_role_fact_count": len(CGROUP_ROLE_ORDER),
        "measurement_root_no_internal_process_rule_required": True,
        "campaign_actual_counter_record_count": (
            CAMPAIGN_COUNTER_RECORD_COUNT_BEFORE_EXECUTION
        ),
        "campaign_actual_work_vector_count": CAMPAIGN_WORK_VECTOR_COUNT_BEFORE_EXECUTION,
        "campaign_actual_comparison_vector_count": (
            CAMPAIGN_COMPARISON_VECTOR_COUNT_BEFORE_EXECUTION
        ),
        "campaign_actual_projection_proof_count": (
            CAMPAIGN_PROJECTION_PROOF_COUNT_BEFORE_EXECUTION
        ),
        "campaign_actual_native_zero_attestation_count": (
            CAMPAIGN_NATIVE_ZERO_ATTESTATION_COUNT_BEFORE_EXECUTION
        ),
        "successful_campaign_counter_record_count": SUCCESS_CAMPAIGN_COUNTER_RECORD_COUNT,
        "successful_campaign_work_vector_count": SUCCESS_CAMPAIGN_WORK_VECTOR_COUNT,
        "successful_campaign_comparison_vector_count": (
            SUCCESS_CAMPAIGN_COMPARISON_VECTOR_COUNT
        ),
        "successful_campaign_projection_proof_count": (
            SUCCESS_CAMPAIGN_PROJECTION_PROOF_COUNT
        ),
        "successful_campaign_native_zero_attestation_count": (
            SUCCESS_CAMPAIGN_NATIVE_ZERO_ATTESTATION_COUNT
        ),
        "predecessor_occurrence_authoritative_receipt_count": (
            PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "predecessor_campaign_authoritative_receipt_count": (
            PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "predecessor_campaign_scope_structural_obligation_count": (
            PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT
        ),
        "successful_campaign_authoritative_receipt_count": (
            SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "successful_combined_authoritative_receipt_count": (
            SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT
        ),
        "terminal_pending_authoritative_receipt_join": {
            "counter_status": "PENDING_INDEPENDENT_REPLAY",
            "predecessor_occurrence_receipt_count": (
                PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "campaign_actual_receipt_count": (
                SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "combined_authoritative_receipt_count": (
                SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT
            ),
        },
        "independent_verifier_pass_authoritative_receipt_join": {
            "counter_status": "PASS",
            "predecessor_occurrence_receipt_count": (
                PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "campaign_actual_receipt_count": (
                SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT
            ),
            "combined_authoritative_receipt_count": (
                SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT
            ),
        },
        "predecessor_structural_nine_are_successor_actual_receipts": False,
        "successful_campaign_path_values_strictly_positive": True,
        "successful_zero_valued_campaign_path_receipt_count": 0,
        "successful_campaign_path_native_zero_observed_count": 0,
        "native_zero_observed_false_for_all_nine_campaign_paths": True,
        "native_zero_required_for_each_zero_valued_path": False,
        "zero_valued_campaign_path_receipts_if_present_are_observations": True,
        "zero_valued_campaign_path_receipts_permitted_on_success": False,
        "zero_valued_campaign_path_receipts_are_kernel_axis_zero_authority": False,
        "native_zero_requires_closed_window_and_os_receipts": True,
        "independent_native_zero_authority_required": True,
        "native_zero_comparison_axis": NATIVE_ZERO_COMPARISON_AXIS,
        "native_zero_comparison_axis_value": 0,
        "kernel_transition_calls_is_linux_syscall_count": False,
        "kernel_transition_calls_semantics": (
            "REGISTERED_PLANNING_GROUND_KERNEL_TRANSITION_OPERATION_SITES"
        ),
        "native_zero_registered_planning_operation_site_fact_count": 314,
        "native_zero_bound_campaign_operation_schedule_count": 314,
        "native_zero_bound_semantic_operation_receipt_count": 297,
        "native_zero_is_open_world_no_kernel_call_claim": False,
        "unregistered_or_dynamic_ground_kernel_operation_sites_forbidden": True,
        "prelaunch_sealed_application_import_allowlist_required": True,
        "producer_terminal_runtime_role_exit_origin_guard_status": (
            "PENDING_INDEPENDENT_MEASUREMENT_LAUNCH_RECEIPT"
        ),
        "independent_native_zero_pass_requires_measurement_launch_receipt_exit_zero_"
        "and_empty_streams": True,
        "measurement_launch_receipt_is_direct_origin_guard_observation": False,
        "measurement_launch_receipt_transitively_proves_frozen_bootstrap_post_dispatch_"
        "guard": True,
        "native_zero_binds_closed_window_event": True,
        "native_zero_binds_exact_operation_manifest": True,
        "native_zero_binds_exact_source_and_import_manifest_facts": True,
        "native_zero_references_campaign_operation_manifest": True,
        "native_zero_references_native_zero_source_manifest": True,
        "native_zero_references_native_zero_import_inventory": True,
        "native_zero_references_window_closure_receipt": True,
        "native_zero_references_campaign_execution_closure": True,
        "projection_proof_references_native_zero_attestation": True,
        "derived_denominator_or_authorization_cap_is_actual_measurement": False,
        "all_nine_counter_records_join_one_work_vector_and_one_comparison_vector": True,
        "one_projection_proof_over_all_nine_paths_required": True,
        "append_only_hash_chain_required": True,
        "actual_read_and_write_return_values_required": True,
        "semantic_integrity_protocol_event_receipts_required": True,
        "fallible_paired_operation_count": 307,
        "fallible_paired_operation_scope": event_grammar_v180r12r4()[
            "fallible_paired_operation_scope"
        ],
        "every_fallible_paired_operation_emits_exact_intent_then_outcome": True,
        "deterministic_local_parse_shape_and_subject_computation_emits_separate_"
        "ledger_event": False,
        "failure_between_registered_hooks_preserves_current_phase_typed_failure_"
        "and_exact_durable_prefix": True,
        "process_birth_operations_emit_intent_outcome_then_reap": True,
        "mount_interval_operations_emit_open_then_close": True,
        "singleton_operation_count": 5,
        "unqualified_every_operation_intent_outcome_claim": False,
        "v180r12r2_top_and_129_inner_content_ids_replayed": True,
        "predecessor_source_receipt_count_replayed": 5,
        "predecessor_route_component_chain_receipt_count_replayed": 12,
        "predecessor_terminal_receipt_count_replayed": 10,
        "predecessor_terminal_shared_resource_receipt_count_replayed": 90,
        "predecessor_terminal_shared_resource_receipt_set_count_replayed": 10,
        "v180r7r1_construction_axis_replayed_as_independent_predecessor_"
        "evidence": True,
        "v180r7r1_construction_axis_charged_as_successor_campaign_"
        "authoritative_receipt": False,
        "v180r7r1_construction_axis_identity_replay_check_overhead_is_successor_"
        "campaign_measurement": True,
        "worker_import_contract": worker_import_contract_v180r12r4(),
        "worker_forbidden_imports": list(WORKER_FORBIDDEN_IMPORTS),
        "worker_imports_v180r12r2_result_evidence_helper": False,
        "pidfd_birth_exit_reap_receipts_required": True,
        "cgroup_v2_memory_peak_and_pids_peak_receipts_required": True,
        "mount_visibility_and_stage_receipts_required": True,
        "five_actual_input_read_chains_required": True,
        "subject_result_is_separate_from_ledger_and_outer_terminal": True,
        "trusted_launcher_precompiles_repo_and_runtime_sources_before_attempt": True,
        "measured_children_lazy_repo_imports_forbidden": True,
        "journal_ipc_ledger_hashing_and_storage_are_instrumentation_overhead": True,
        "all_evidence_receipt_content_id_canonicalization_and_support_sha_are_"
        "instrumentation_overhead": True,
        "semantic_hash_counter_counts_only_exact_operation_manifest_labels": True,
        "semantic_hash_counter_excluded_instrumentation_classes": list(
            SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES
        ),
        "instrumentation_overhead_is_campaign_actual_measurement": False,
        "instrumentation_memory_inside_measured_children_remains_in_cgroup_peak": True,
        "closed_window_native_zero_receipts_required": True,
        "source_closure_contract": source_closure_contract_v180r12r4(),
        "authorization_evidence_freeze_required_before_attempt": True,
        "source_bound_prelaunch_required_before_real_outcome_execution": True,
        "zero_sentinel_draft_is_executable_authorization": False,
        "execution_forbidden_until_all_protocol_authorization_source_closure_"
        "prelaunch_rule_and_evidence_identities_are_frozen": True,
        "attempt_record_o_excl_before_measurement_root_or_authorized_measured_"
        "subject_input_read": True,
        "attempt_record_excludes_cgroup_topology_receipt_id": True,
        "successful_event_evidence_id_issued_before_event_append_required": True,
        "successful_event_future_evidence_reference_forbidden": True,
        "terminal_evidence_causal_join_rules": list(EVIDENCE_CAUSAL_JOIN_RULES),
        "preauthorization_predecessor_and_source_validation_reads_are_trusted_"
        "excluded_overhead": True,
        "preauthorization_validation_reads_are_campaign_actual_measurement": False,
        "supervisor_first_measured_source_reads_occur_after_attempt_open": True,
        "campaign_attempt_identity_input_fields": [
            "protocol_id",
            "authorization_id",
            "authorization_evidence_id",
            "campaign_measurement_execution_slot_id",
            "logical_occurrence_id",
            "execution_nonce",
        ],
        "campaign_attempt_id_derived_from_exact_six_authorities": True,
        "campaign_attempt_identity_includes_fresh_authorization_evidence_id": True,
        "campaign_attempt_identity_excludes_cgroup_runtime_and_transport_facts": True,
        "campaign_attempt_record_and_terminal_echo_authorization_evidence_id": True,
        "campaign_attempt_record_and_terminal_transport_provenance_fields": [
            "prelaunch_materialization_terminal_id",
            "prelaunch_launch_manifest_sha256",
            "prelaunch_launch_rule_id",
            "measurement_launch_attempt_id",
        ],
        "measurement_launch_receipt_excluded_from_terminal_fixed_point": True,
        "verification_launcher_joins_post_outcome_measurement_launch_receipt": True,
        "attempt_identity_consumed_by_success_failure_timeout_or_cap_violation": True,
        "same_attempt_identity_rerun_forbidden": True,
        "success_failure_and_runtime_cas_mutually_exclusive": True,
        "campaign_failure_forbidden_at_terminal_publication_attempt_entry": True,
        "terminal_publication_attempt_entry_precedes_open_parent_and_o_excl": True,
        "post_terminal_child_or_bootstrap_error_is_outer_launch_failure": True,
        "pending_terminal_requires_measurement_launch_receipt_for_acceptance": True,
        "post_terminal_outer_launch_failure_preserves_exact_or_partial_terminal_observation": True,
        "failure_prefix_ledger_events_retained": True,
        "producer_free_independent_replay_required": True,
        "retained_verification_replay_exact_bytes_required": True,
        "campaign_measurement_authorization_issued": False,
        "campaign_measurement_execution_started": False,
        "campaign_measurement_execution_count": 0,
        "V180R12R2_COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "V180R12R4_CAMPAIGN_COUNTER_CLOSURE_STATUS": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "terminal_counter_closure_status_on_success": "PENDING_INDEPENDENT_REPLAY",
        "terminal_counter_completeness_gate_on_success": "PENDING_INDEPENDENT_REPLAY",
        "independent_verifier_is_only_counter_pass_authority": True,
        "independent_verifier_counter_completeness_gate_on_success": "PASS",
        "independent_verifier_campaign_counter_closure_status_on_success": "PASS",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "OFFICIAL_EXECUTION_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
        "future_v180r13_must_carry_fresh_replay_successor_scope": True,
        "outcome_free": True,
    }
    return {
        **payload,
        "campaign_measurement_protocol_id": domains.extension_content_id_v180r12r4(
            domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_PROTOCOL_V180R12R4_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class CampaignMeasurementProtocolV180R12R4:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_measurement_protocol_id: str
    campaign_measurement_execution_slot_id: str

    def __post_init__(self) -> None:
        document = loads_canonical_json(self.canonical_bytes)
        if not (
            self._issuer is _ISSUER
            and type(document) is dict
            and canonical_json_bytes(document) == self.canonical_bytes
            and document.get("campaign_measurement_protocol_id")
            == self.campaign_measurement_protocol_id
            and document.get("campaign_measurement_execution_slot", {}).get(
                "campaign_measurement_execution_slot_id"
            )
            == self.campaign_measurement_execution_slot_id
        ):
            _fail("V180r12r4 campaign measurement protocol is foreign or noncanonical")

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:  # pragma: no cover
            raise AssertionError
        return document

    def __reduce__(self) -> NoReturn:
        raise TypeError("V180r12r4 campaign measurement protocol is not picklable")


def freeze_campaign_measurement_protocol_v180r12r4(
    *,
    cgroup_parent_fact: Mapping[str, Any],
    runtime_capability_fact: Mapping[str, Any],
) -> CampaignMeasurementProtocolV180R12R4:
    document = build_campaign_measurement_protocol_v180r12r4(
        cgroup_parent_fact=cgroup_parent_fact,
        runtime_capability_fact=runtime_capability_fact,
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_PROTOCOL_ID != ZERO_ID:
        contract = document.get("prelaunch_contract")
        if not (
            document["campaign_measurement_protocol_id"] == EXPECTED_PROTOCOL_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
            and document["campaign_measurement_execution_slot"][
                "campaign_measurement_execution_slot_id"
            ]
            == EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID
            and document["logical_occurrence_id"] == LOGICAL_OCCURRENCE_ID
            and document["execution_nonce"] == EXECUTION_NONCE
            and type(contract) is dict
            and contract.get("source_closure_rule_id")
            == EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID
            and contract.get("materialization_rule_id")
            == EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID
            and contract.get("launch_rule_id")
            == EXPECTED_PRELAUNCH_LAUNCH_RULE_ID
            and contract.get("rule_identities_frozen") is True
        ):
            _fail("V180r12r4 frozen campaign measurement protocol identity changed")
    return CampaignMeasurementProtocolV180R12R4(
        _ISSUER,
        raw,
        document["campaign_measurement_protocol_id"],
        document["campaign_measurement_execution_slot"][
            "campaign_measurement_execution_slot_id"
        ],
    )


__all__ = (
    "ADDRESS_SPACE_HARD_CAP_BYTES",
    "ACTOR_ROLES",
    "ATTEMPT_RELATIVE_PATH",
    "AUXILIARY_VALUE_FIELDS",
    "CAMPAIGN_MEASUREMENT_ATTEMPT_DOMAIN",
    "CAMPAIGN_MEASUREMENT_ATTEMPT_IDENTITY_INPUT_FIELDS",
    "CAMPAIGN_MEASUREMENT_ATTEMPT_PAYLOAD_FIELDS",
    "CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA",
    "CAMPAIGN_PATHS",
    "CAMPAIGN_SUBJECT_RESULT_FIELDS",
    "CAMPAIGN_PATH_COUNT",
    "CAMPAIGN_SCOPE_KIND",
    "CGROUP_PARENT_FACT_FIELDS",
    "CGROUP_ROLE_ORDER",
    "COUNTER_REGISTRY_REFERENCE",
    "CampaignMeasurementProtocolV180R12R4",
    "CampaignMeasurementProtocolV180R12R4Error",
    "EVENT_FIELDS",
    "EVENTS_RELATIVE_PATH",
    "EVENT_KIND_PHASES",
    "EVENT_KIND_ROLE_PHASES",
    "EVENT_PAYLOAD_FIELDS",
    "EVIDENCE_CAUSAL_JOIN_RULES",
    "EVIDENCE_INVENTORY_BUNDLE_BYTE_CAP",
    "EVIDENCE_INVENTORY_BUNDLE_FIELDS",
    "EVIDENCE_INVENTORY_BUNDLE_SCHEMA",
    "EVENT_ACK_BODY_FIELDS",
    "EVENT_ACK_BODY_SCHEMA",
    "EVENT_PROPOSAL_BODY_FIELDS",
    "EVENT_PROPOSAL_BODY_SCHEMA",
    "EXECUTION_NONCE",
    "EXPECTED_CAMPAIGN_MEASUREMENT_EXECUTION_SLOT_ID",
    "EXPECTED_CANONICAL_BYTE_COUNT",
    "EXPECTED_CANONICAL_SHA256",
    "EXPECTED_PROTOCOL_ID",
    "EXPECTED_PRELAUNCH_LAUNCH_RULE_ID",
    "EXPECTED_PRELAUNCH_MATERIALIZATION_RULE_ID",
    "EXPECTED_PRELAUNCH_SOURCE_CLOSURE_RULE_ID",
    "PROTOCOL_FINAL_ANCHOR_NAMES",
    "EVIDENCE_INVENTORY_RELATIVE_PATH",
    "EVIDENCE_INVENTORY_ROWS",
    "EXECUTION_CLOSURE_RELATIVE_PATH",
    "EXECUTION_CLOSURE_BYTE_CAP",
    "EXECUTION_CLOSURE_FIELDS",
    "EXECUTION_CLOSURE_SCHEMA",
    "EXTERNAL_FD_ROLE_MAP",
    "EXTERNAL_FD_ROLE_RULES",
    "EXTERNAL_LAUNCH_CONTEXT_FD",
    "EXTERNAL_LAUNCH_CONTEXT_FIELDS",
    "EXTERNAL_LAUNCH_CONTEXT_SCHEMA",
    "SOURCE_SYSTEMD_SERVICE_FD",
    "FAILURE_ARTIFACT_HASH_BYTE_CAP",
    "FAILURE_ARTIFACT_METADATA_BYTE_CAP",
    "FAILURE_ARTIFACT_OBSERVATION_FIELDS",
    "FAILURE_ARTIFACT_OBSERVATION_ROW_CAP",
    "FAILURE_CGROUP_OBSERVATION_FIELDS",
    "FAILURE_CGROUP_NODE_OBSERVATION_FIELDS",
    "FAILURE_CGROUP_NODE_ROLES",
    "FAILURE_CGROUP_NODE_STATES",
    "FAILURE_DIRECTORY_ENTRY_CAP",
    "FAILURE_DIRECTORY_ENTRY_NAME_TOTAL_BYTE_CAP",
    "FAILURE_EMERGENCY_RESERVE_BYTES",
    "FAILURE_MESSAGE_BYTE_CAP",
    "FRAME_BYTE_CAP",
    "SOCK_SEQPACKET_BUFFER_REQUEST_BYTES",
    "SOCK_SEQPACKET_EFFECTIVE_MIN_BYTES",
    "SOCKET_BUFFER_CAPABILITY_AT_LEAST_FIELDS",
    "SOCKET_BUFFER_CAPABILITY_EXACT_FIELDS",
    "SOCKET_BUFFER_CAPABILITY_EXPECTED_EXACT_PROPERTIES",
    "SOCKET_BUFFER_CAPABILITY_EXPECTED_MINIMUM_PROPERTIES",
    "SOCKET_BUFFER_CAPABILITY_FACT_FIELDS",
    "SOCKET_BUFFER_CAPABILITY_FACT_SCHEMA",
    "SOCKET_BUFFER_CAPABILITY_INSUFFICIENT_CAUSE",
    "SOCKET_BUFFER_CAPABILITY_MISMATCH_ROW_FIELDS",
    "SOCKET_BUFFER_CAPABILITY_MISMATCH_SCOPE",
    "FAILURE_PROGRESS_PATH_KIND_ROWS",
    "FAILURE_RELATIVE_PATH",
    "FAILURE_STATE_FIELDS",
    "FROZEN_AUTHORIZATION_CONTEXT_FIELDS",
    "FROZEN_AUTHORIZATION_CONTEXT_SCHEMA",
    "INPUT_FILE_BYTE_CAP",
    "INPUT_TOTAL_BYTE_CAP",
    "INNER_CONTENT_ID_OPERATION_SUFFIXES",
    "INTEGRITY_CHECK_OPERATION_COUNT",
    "INTEGRITY_CHECK_OPERATION_FAMILIES",
    "INTEGRITY_CHECK_OPERATION_LABELS",
    "INTENT_OUTCOME_PAIRS",
    "LOGICAL_OCCURRENCE_ID",
    "LEDGER_CLOSURE_RELATIVE_PATH",
    "LEDGER_CLOSURE_BYTE_CAP",
    "LEDGER_CLOSURE_FIELDS",
    "LEDGER_CLOSURE_SCHEMA",
    "MAX_EVENT_BYTE_COUNT",
    "MAX_EVENT_COUNT",
    "MAX_LEDGER_BYTE_COUNT",
    "MEMORY_MAX_BYTES",
    "MEASUREMENT_CGROUP_OBSERVATION_FIELDS",
    "MEASUREMENT_CGROUP_OBSERVATION_PHASES",
    "NATIVE_ZERO_COMPARISON_AXIS",
    "OUTCOME_CODES",
    "OUTPUT_ROOT_RELATIVE_PATH",
    "OS_RECEIPT_RELATIVE_PATH",
    "OS_RECEIPT_BUNDLE_BYTE_CAP",
    "OS_RECEIPT_BUNDLE_FIELDS",
    "OS_RECEIPT_BUNDLE_SCHEMA",
    "OBSERVER_SUPERVISOR_START_FIELDS",
    "OBSERVER_SUPERVISOR_START_SCHEMA",
    "PHASE_ORDER",
    "PIDS_MAX",
    "PROCESS_ROLE_ORDER",
    "PREDECESSOR_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT",
    "PREDECESSOR_CAMPAIGN_SCOPE_STRUCTURAL_OBLIGATION_COUNT",
    "PREDECESSOR_INPUT_TOTAL_BYTE_COUNT",
    "PREDECESSOR_OCCURRENCE_AUTHORITATIVE_RECEIPT_COUNT",
    "PREDECESSOR_TERMINAL_INPUT_BYTE_COUNT",
    "PREDECESSOR_VERIFICATION_INPUT_BYTE_COUNT",
    "PRELAUNCH_BOOTSTRAP_RELATIVE_PATH",
    "PRE_ATTEMPT_HOST_CONFORMANCE_BYTE_CAP",
    "PRE_ATTEMPT_HOST_CONFORMANCE_RELATIVE_PATH",
    "PRE_ATTEMPT_HOST_CONFORMANCE_SCHEMA",
    "PRELAUNCH_EXTERNAL_ROOT_RELATIVE_PATH",
    "PRELAUNCH_LAUNCHER_RELATIVE_PATH",
    "PRELAUNCH_LAUNCH_FAILURE_PUBLICATION_FIELDS",
    "PRELAUNCH_LAUNCH_PUBLICATION_STAGES",
    "PRELAUNCH_LAUNCH_PUBLICATION_STATES",
    "PRELAUNCH_MANIFEST_RELATIVE_PATH",
    "PRELAUNCH_ROOT_RELATIVE_PATH",
    "PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH",
    "PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH",
    "PRELAUNCH_MEASUREMENT_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH",
    "PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_ATTEMPT_RELATIVE_PATH",
    "PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_RECEIPT_RELATIVE_PATH",
    "PRELAUNCH_VERIFICATION_SERVICE_LAUNCH_FAILURE_RELATIVE_PATH",
    "PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_SCHEMA",
    "PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_DOMAIN",
    "PRELAUNCH_SERVICE_LAUNCH_ATTEMPT_FIELDS",
    "PRELAUNCH_SERVICE_LAUNCH_RECEIPT_SCHEMA",
    "PRELAUNCH_SERVICE_LAUNCH_RECEIPT_DOMAIN",
    "PRELAUNCH_SERVICE_LAUNCH_RECEIPT_FIELDS",
    "PRELAUNCH_SERVICE_LAUNCH_FAILURE_SCHEMA",
    "PRELAUNCH_SERVICE_LAUNCH_FAILURE_DOMAIN",
    "PRELAUNCH_SERVICE_LAUNCH_FAILURE_FIELDS",
    "PRELAUNCH_SERVICE_LAUNCH_PUBLICATION_STAGES",
    "PRELAUNCH_SERVICE_LAUNCH_INNER_JOIN_FIELDS",
    "PRELAUNCH_SERVICE_LAUNCH_TERMINAL_COMMON_FIELDS",
    "PRELAUNCH_SERVICE_LAUNCH_UNIT_ABSENCE_FIELDS",
    "ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_FIELDS",
    "ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE_SCHEMA",
    "ZERO_ATOMIC_CGROUP_BIRTH_PREFLIGHT_RECEIPT_INTERFACE",
    "PRODUCTION_ENV_EXECUTABLE",
    "PRODUCTION_MATERIALIZATION_TERMINAL_SHA256_TEMPLATE",
    "PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN",
    "PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_TOKEN_INPUT",
    "PRODUCTION_MEASUREMENT_TRANSIENT_SERVICE_UNIT_NAME",
    "PRODUCTION_RUNTIME_PLACEMENT_T1_FIELDS",
    "PRODUCTION_RUNTIME_PLACEMENT_T1_SCHEMA",
    "PRODUCTION_RUNTIME_PLACEMENT_T2_FIELDS",
    "PRODUCTION_RUNTIME_PLACEMENT_T2_SCHEMA",
    "PRODUCTION_RUNTIME_PLACEMENT_T3_CHECKPOINT_FIELDS",
    "PRODUCTION_RUNTIME_PLACEMENT_T3_FIELDS",
    "PRODUCTION_RUNTIME_PLACEMENT_T3_SCHEMA",
    "TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_FIELDS",
    "TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_PROPERTY_SNAPSHOT_FIELDS",
    "TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCHEMA",
    "TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_SCOPES",
    "TOPOLOGY_CONFORMANCE_DIAGNOSTIC_R4_UNIT_OWNERSHIP_FIELDS",
    "PRODUCTION_SYSTEMD_RUN_EXECUTABLE",
    "PRODUCTION_SYSTEMD_SERVICE_INVOCATION_FIELDS",
    "PRODUCTION_SYSTEMD_SERVICE_INVOCATION_SCHEMA",
    "PRODUCTION_TRANSIENT_SERVICE_ROWS",
    "PRODUCTION_TRANSIENT_SERVICE_SLICE",
    "PRODUCTION_TRANSIENT_SERVICE_TOKEN_DOMAIN",
    "PRODUCTION_TRANSIENT_SERVICE_TOKEN_INPUT_FIELDS",
    "PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN",
    "PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_TOKEN_INPUT",
    "PRODUCTION_VERIFICATION_TRANSIENT_SERVICE_UNIT_NAME",
    "PROTOCOL_CHECK_OPERATION_COUNT",
    "PROTOCOL_CHECK_FAMILIES",
    "PROTOCOL_CHECK_OPERATION_LABELS",
    "REQUIRED_EVENT_KINDS",
    "RETAINED_VERIFICATION_REPLAY_RELATIVE_PATH",
    "RUNTIME_CAPABILITY_FACT_FIELDS",
    "RUNTIME_CHANNEL_KEY_CONTEXT_FIELDS",
    "RUNTIME_CHANNEL_KEY_CONTEXT_SCHEMA",
    "RUNTIME_IPC_FRAME_FIELDS",
    "RUNTIME_IPC_FRAME_SCHEMA",
    "RUNTIME_IPC_FIRST_PARENT_FRAME_ROWS",
    "RUNTIME_IPC_ROLE_FRAME_TYPE_ROWS",
    "RUNTIME_IPC_UNDEFINED_CONTROL_FRAME_TYPES",
    "RUNTIME_IPC_UNSIGNED_FRAME_FIELDS",
    "RUNTIME_CAS_ROOT_RELATIVE_PATH",
    "SOURCE_CLOSURE_REQUIRED_ROOTS",
    "SERVICE_CONTEXT_CAPTURE_CANONICAL_BYTE_COUNT",
    "SERVICE_CONTEXT_CAPTURE_CANONICAL_SHA256",
    "SERVICE_CONTEXT_CAPTURE_CGROUP_PARENT_FACT",
    "SERVICE_CONTEXT_CAPTURE_PURPOSE",
    "SERVICE_CONTEXT_CAPTURE_RELATIVE_PATH",
    "SERVICE_CONTEXT_CAPTURE_RUNTIME_CAPABILITY_FACT",
    "SERVICE_CONTEXT_CAPTURE_SCHEMA",
    "SOURCE_BOUND_RUNNER_MODULE_METADATA_FIELDS",
    "SOURCE_BOUND_RUNNER_MODULE_ROWS",
    "SOURCE_BOUND_RUNNER_TARGET_ORDER",
    "SNAPSHOT_BYTES_TRANSPORT_BYTE_CAP",
    "SNAPSHOT_BYTES_TRANSPORT_EVENT_ROWS",
    "SNAPSHOT_BYTES_TRANSPORT_FIELDS",
    "SNAPSHOT_BYTES_TRANSPORT_SCHEMA",
    "SEMANTIC_HASH_OPERATION_COUNT",
    "SEMANTIC_HASH_COUNTER_EXCLUDED_INSTRUMENTATION_CLASSES",
    "SEMANTIC_HASH_OPERATION_FAMILIES",
    "SEMANTIC_HASH_OPERATION_LABELS",
    "SEMANTIC_RECEIPT_AUXILIARY_ROWS",
    "STDERR_BYTE_CAP",
    "STDOUT_BYTE_CAP",
    "SUBJECT_RESULT_RELATIVE_PATH",
    "SUBJECT_RESULT_BYTE_CAP",
    "SUBJECT_RESULT_RUNTIME_BYTE_CAP",
    "SUBJECT_OUTPUT_FD_BINDING_FIELDS",
    "SUBJECT_TEMP_RELATIVE_PATH",
    "SUCCESS_CAMPAIGN_AUTHORITATIVE_RECEIPT_COUNT",
    "SUCCESS_COMBINED_AUTHORITATIVE_RECEIPT_COUNT",
    "SUCCESS_DIRECT_EVENT_EVIDENCE_DOCUMENT_COUNT",
    "SUCCESS_EVIDENCE_DOCUMENT_COUNT",
    "SUCCESS_EVENT_CARDINALITIES",
    "SUCCESS_EVENT_EVIDENCE_REQUIREMENTS",
    "SUCCESS_EXACT_EVENT_COUNT",
    "SUCCESS_CAMPAIGN_NATIVE_ZERO_ATTESTATION_COUNT",
    "SUCCESS_MINIMUM_EVENT_COUNT",
    "SUCCESS_NONNULL_EVENT_EVIDENCE_COUNT",
    "SUCCESS_NULL_EVENT_EVIDENCE_COUNT",
    "SUCCESS_SUPPORT_EVIDENCE_DOCUMENT_COUNT",
    "STAGE_FD_BINDING_FIELDS",
    "SUPERVISOR_WORKER_HANDOFF_FIELDS",
    "SUPERVISOR_WORKER_HANDOFF_SCHEMA",
    "SUCCESS_ARTIFACT_ORDER",
    "SUCCESS_ARTIFACT_SCHEMA_ROWS",
    "SUCCESS_DURABLE_ARTIFACT_ROWS",
    "SUCCESS_DURABLE_WRITE_ORDER",
    "TERMINAL_BYTE_CAP",
    "TERMINAL_FIELDS",
    "TERMINAL_RELATIVE_PATH",
    "TERMINAL_SCHEMA",
    "TERMINATION_GRACE_SECONDS",
    "VERIFICATION_BYTE_CAP",
    "VERIFICATION_FAILURE_ARTIFACT_OBSERVATION_ROWS",
    "VERIFICATION_FAILURE_DIRECTORY_ENTRY_COUNT_CAP",
    "VERIFICATION_FAILURE_DIRECTORY_NAME_TOTAL_BYTE_CAP",
    "VERIFICATION_FAILURE_FIELDS",
    "VERIFICATION_FAILURE_OBSERVATION_BOUNDARY",
    "VERIFICATION_FAILURE_OBSERVATION_STREAM_CHUNK_BYTES",
    "VERIFICATION_FAILURE_RELATIVE_PATH",
    "VERIFICATION_FAILURE_SCHEMA",
    "VERIFICATION_FAILURE_WATCHDOG_CLEANUP_FIELDS",
    "VERIFICATION_FAILURE_WATCHDOG_SECONDARY_FIELDS",
    "VERIFICATION_FAILURE_WATCHDOG_SECONDARY_OBSERVATION_CAP",
    "VERIFIED_EXTERNAL_LAUNCH_CONTEXT_FIELDS",
    "VERIFIED_EXTERNAL_LAUNCH_CONTEXT_SCHEMA",
    "REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_FIELDS",
    "REVALIDATED_EXTERNAL_MEASUREMENT_CONTEXT_SCHEMA",
    "TYPED_LAUNCH_FAILURE_FIELDS",
    "TYPED_LAUNCH_FAILURE_SUBSTAGES",
    "production_systemd_service_contract_v180r12r4",
    "DELEGATED_CGROUP_PARENT_FD",
    "CGROUP2_MOUNT_FD",
    "VERIFICATION_RELATIVE_PATH",
    "V180R12R2_PRODUCTION_AGGREGATION_BUNDLE_ID",
    "V180R12R2_VERIFICATION_ID",
    "V180R12R3_FAILED_CAMPAIGN_ATTEMPT_ID",
    "V180R12R3_FAILED_CHILD_STDERR_BYTE_COUNT",
    "V180R12R3_FAILED_CHILD_STDERR_SHA256",
    "V180R12R3_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT",
    "V180R12R3_FAILED_LAUNCH_ATTEMPT_ID",
    "V180R12R3_FAILED_LAUNCH_ATTEMPT_SHA256",
    "V180R12R3_FAILED_LAUNCH_FAILURE_BYTE_COUNT",
    "V180R12R3_FAILED_LAUNCH_FAILURE_ID",
    "V180R12R3_FAILED_LAUNCH_FAILURE_SHA256",
    "V180R12R3_FAILED_LAUNCH_RULE_ID",
    "V180R12R3_FAILED_MATERIALIZATION_TERMINAL_ID",
    "V180R12R3_FAILED_MEASUREMENT_CGROUP_PARENT_PATH",
    "V180R12R3_FAILED_MEASUREMENT_CGROUP_ROOT_NAME",
    "V180R12R3_FAILED_PRELAUNCH_EXACT_ENTRIES",
    "V180R12R3_FAILED_RETAINED_FILE_FACT_ROWS",
    "V180R12R3_FAILURE_FREEZE_COMMIT_ID",
    "V180R12R3_FAILURE_FREEZE_GIT_BLOB_ID",
    "V180R12R3_FAILURE_FREEZE_SOURCE_BYTE_COUNT",
    "V180R12R3_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R3_FAILURE_FREEZE_SOURCE_SHA256",
    "V180R12R3_FAILURE_FREEZE_TREE_ID",
    "V180R12R3_REQUIRED_ABSENT_SUCCESSOR_PATHS",
    "V180R12R3R1_FAILED_CAMPAIGN_ATTEMPT_ID",
    "V180R12R3R1_FAILED_CHILD_STDERR_BYTE_COUNT",
    "V180R12R3R1_FAILED_CHILD_STDERR_SHA256",
    "V180R12R3R1_FAILED_LAUNCH_ATTEMPT_BYTE_COUNT",
    "V180R12R3R1_FAILED_LAUNCH_ATTEMPT_ID",
    "V180R12R3R1_FAILED_LAUNCH_ATTEMPT_SHA256",
    "V180R12R3R1_FAILED_LAUNCH_FAILURE_BYTE_COUNT",
    "V180R12R3R1_FAILED_LAUNCH_FAILURE_ID",
    "V180R12R3R1_FAILED_LAUNCH_FAILURE_SHA256",
    "V180R12R3R1_FAILED_LAUNCH_RULE_ID",
    "V180R12R3R1_FAILED_MATERIALIZATION_TERMINAL_ID",
    "V180R12R3R1_FAILED_MEASUREMENT_CGROUP_PARENT_PATH",
    "V180R12R3R1_FAILED_MEASUREMENT_CGROUP_ROOT_NAME",
    "V180R12R3R1_FAILED_PRELAUNCH_EXACT_ENTRIES",
    "V180R12R3R1_FAILED_RETAINED_FILE_FACT_ROWS",
    "V180R12R3R1_FAILURE_FREEZE_COMMIT_ID",
    "V180R12R3R1_FAILURE_FREEZE_GIT_BLOB_ID",
    "V180R12R3R1_FAILURE_FREEZE_SOURCE_BYTE_COUNT",
    "V180R12R3R1_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R3R1_FAILURE_FREEZE_SOURCE_SHA256",
    "V180R12R3R1_FAILURE_FREEZE_TREE_ID",
    "V180R12R3R1_REQUIRED_ABSENT_SUCCESSOR_PATHS",
    "V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_ID",
    "V180R12R3R2_FAILED_CAMPAIGN_ATTEMPT_RECORD_ID",
    "V180R12R3R2_FAILED_EVENT_IDS",
    "V180R12R3R2_FAILED_FAILURE_STATE_ID",
    "V180R12R3R2_FAILED_LAUNCH_ATTEMPT_ID",
    "V180R12R3R2_FAILED_LAUNCH_FAILURE_ID",
    "V180R12R3R2_FAILED_MEASUREMENT_CGROUP_PARENT_PATH",
    "V180R12R3R2_FAILED_MEASUREMENT_CGROUP_ROOT_NAME",
    "V180R12R3R2_FAILURE_CLAIM_BOUNDARY",
    "V180R12R3R2_FAILURE_FREEZE_COMMIT_ID",
    "V180R12R3R2_FAILURE_FREEZE_GIT_BLOB_ID",
    "V180R12R3R2_FAILURE_FREEZE_SOURCE_BYTE_COUNT",
    "V180R12R3R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R3R2_FAILURE_FREEZE_SOURCE_SHA256",
    "V180R12R3R2_FAILURE_FREEZE_TREE_ID",
    "V180R12R3R2_REPAIR_SCOPE",
    "V180R12R4R2_FAILED_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R2_FAILED_CAMPAIGN_FAILURE_ID",
    "V180R12R4R2_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R2_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R2_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R4_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R4_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R4_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R4_FAILED_PREDECESSOR_FREEZE_ID",
    "V180R12R4R4_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R4_REPAIR_SCOPE",
    "V180R12R4R5_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R5_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R5_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R5_FAILED_PREDECESSOR_FREEZE_ID",
    "V180R12R4R5_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R5_REPAIR_SCOPE",
    "V180R12R4R6_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R6_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R6_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R6_FAILED_PREDECESSOR_FREEZE_ID",
    "V180R12R4R6_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R6_REPAIR_SCOPE",
    "V180R12R4R7_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R7_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R7_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R7_FAILED_PREDECESSOR_FREEZE_ID",
    "V180R12R4R7_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R7_REPAIR_SCOPE",
    "V180R12R4R8_FAILED_CAMPAIGN_FAILURE_ID",
    "V180R12R4R8_FAILED_INNER_LAUNCH_FAILURE_ID",
    "V180R12R4R8_FAILED_LOGICAL_CAMPAIGN_ATTEMPT_ID",
    "V180R12R4R8_FAILED_OUTER_SERVICE_FAILURE_ID",
    "V180R12R4R8_FAILED_PREDECESSOR_FREEZE_ID",
    "V180R12R4R8_FAILURE_FREEZE_SOURCE_RELATIVE_PATH",
    "V180R12R4R8_REPAIR_SCOPE",
    "V180R12R4_REPAIR_SCOPE",
    "WALL_TIMEOUT_SECONDS",
    "WORK_SCOPE_KIND",
    "WORKER_ALLOWED_LOCAL_IMPORTS",
    "WORKER_FORBIDDEN_IMPORTS",
    "ZERO_ID",
    "build_campaign_measurement_protocol_v180r12r4",
    "campaign_measurement_attempt_identity_contract_v180r12r4",
    "durable_artifact_contract_v180r12r4",
    "evidence_inventory_contract_v180r12r4",
    "event_grammar_v180r12r4",
    "failure_observation_contract_v180r12r4",
    "failed_dispatch_repair_lineage_contract_v180r12r4",
    "failed_external_replay_repair_lineage_contract_v180r12r4",
    "failed_scientific_birth_repair_lineage_contract_v180r12r4",
    "failed_ordinal8_repair_lineage_contract_v180r12r4",
    "failed_ordinal9_repair_lineage_contract_v180r12r4",
    "failed_ordinal10_repair_lineage_contract_v180r12r4",
    "failed_ordinal11_repair_lineage_contract_v180r12r4",
    "failed_ordinal12_repair_lineage_contract_v180r12r4",
    "failed_ordinal13_repair_lineage_contract_v180r12r4",
    "successful_event_schedule_template_v180r12r4",
    "freeze_campaign_measurement_protocol_v180r12r4",
    "measurement_derivation_contract_v180r12r4",
    "operation_manifest_v180r12r4",
    "prelaunch_contract_v180r12r4",
    "protocol_final_anchor_literals_v180r12r4",
    "require_frozen_protocol_final_anchor_set_v180r12r4",
    "semantic_hash_counter_scope_contract_v180r12r4",
    "source_closure_contract_v180r12r4",
    "service_context_capture_contract_v180r12r4",
    "source_bound_runner_execution_envelope_contract_v180r12r4",
    "socket_buffer_capability_contract_v180r12r4",
    "success_durable_artifact_contract_v180r12r4",
    "topology_conformance_diagnostic_r4_contract_v180r12r4",
    "validate_cgroup_parent_fact_v180r12r4",
    "validate_runtime_capability_fact_v180r12r4",
    "worker_import_contract_v180r12r4",
)
