"""Exact source-closed WORKER/BUSINESS leaf images for the H1 creator chain.

One freestanding source is compiled with two frozen role tags.  This module
only verifies the checked-in exact bytes and creates sealed executable memfds;
it never invokes a compiler or launches a process.  The direct lifecycle
evidence for this slice proves the role protocol and independent guardian and
actual-parent PID/lifetime checks, not registered-BROKER image attestation,
WORKER/BUSINESS resource semantics, E3/E4,
accounting completeness, current-access authority, or official execution.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import struct
from typing import NoReturn
import zlib


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.61-E-C-E5B-B2-D-LEAF-ROLES-V2"
PROFILE_KEY = "construction_k7_h1_nested_creator_leaf_roles_native_v2"
READINESS = "SOURCE_CLOSED_LEAF_ROLE_IMAGES_WITH_DIRECT_LIFECYCLE_ONLY"

FREESTANDING_NO_LIBC_SOURCE_PRESENT = True
EXACT_STATIC_WORKER_ELF_IMAGE_PRESENT = True
EXACT_STATIC_BUSINESS_ELF_IMAGE_PRESENT = True
EXTERNAL_GUARDIAN_CREDENTIAL_CHECK_IMPLEMENTATION_PRESENT = True
ACTUAL_PARENT_PID_BINDING_IMPLEMENTATION_PRESENT = True
PDEATHSIG_PARENT_LIFETIME_BINDING_IMPLEMENTATION_PRESENT = True
BOUNDED_READY_GO_SHUTDOWN_IMPLEMENTATION_PRESENT = True
RUNTIME_TOOLCHAIN_INVOCATION_PRESENT = False
REGISTERED_BROKER_IMAGE_ATTESTATION_PRESENT = False

WORKER_RESOURCE_SEMANTICS_PRESENT = False
BUSINESS_RESOURCE_SEMANTICS_PRESENT = False
WORKER_ROLE_BIRTH_BY_BROKER_OBSERVED = False
BUSINESS_ROLE_BIRTH_BY_BROKER_OBSERVED = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_AUTHORITY_PRESENT = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE = "NOT_RUN"
WORKLOAD_ECONOMICS_GATE = "NOT_RUN"

SOURCE_PATH = (
    Path(__file__).resolve(strict=True).parent
    / "native"
    / "h1_nested_creator_leaf_role_x86_64_v2.c"
).resolve(strict=True)
SOURCE_SHA256 = "567c47a2a6e63b86b14bd81ec6cd63dc868958dc3cc86ac6841222f02a9b9d90"
ELF_BYTE_COUNT = 6000
WORKER_ELF_SHA256 = "1b2cee17dfa9a9b22428dd026c3abfd7006268e211b852812e4dfdaa977bc9aa"
BUSINESS_ELF_SHA256 = "174a917ea776eabe063df572e7a55b127144d13d35ceaa48dad343ad5f0e7b32"
BUILD_TOOLCHAIN = {
    "cc": "gcc 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)",
    "ld": "GNU ld (GNU Binutils for Ubuntu) 2.38",
}
BUILD_ARGV_PREFIX = (
    "gcc", "-Os", "-nostdlib", "-static", "-fno-pie", "-no-pie",
    "-fno-stack-protector", "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables", "-fcf-protection=none", "-Wl,--build-id=none",
    "-Wl,-z,noexecstack", "-Wl,-s",
)

MFD_CLOEXEC = getattr(os, "MFD_CLOEXEC", 0x0001)
MFD_ALLOW_SEALING = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
F_ADD_SEALS = getattr(fcntl, "F_ADD_SEALS", 1033)
F_GET_SEALS = getattr(fcntl, "F_GET_SEALS", 1034)
F_SEAL_SEAL = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
F_SEAL_SHRINK = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
F_SEAL_GROW = getattr(fcntl, "F_SEAL_GROW", 0x0004)
F_SEAL_WRITE = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
REQUIRED_SEALS = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE

FRAME_MAGIC = 0x3256524C43514641
FRAME_VERSION = 2
FRAME_BYTES = 64
CONTROL_FD = 3
OPCODES = {
    "ROLE_READY": 1,
    "ROLE_GO": 2,
    "ROLE_GO_ECHO": 3,
    "ROLE_SHUTDOWN": 4,
    "ROLE_BYE": 5,
    "PROTOCOL_FAILURE": 6,
}
ROLE_SLOTS = {"WORKER": 1, "BUSINESS": 2}
GO_SEQUENCE = 1
SHUTDOWN_SEQUENCE = 2
_FRAME = struct.Struct("<QIIQ16sqiIQ")

_EXACT_COMPRESSED_WORKER_ELF_BYTES = bytes.fromhex(
    "78daed585d4c1c55149efd2ba85b6669b02596078293744d646590286313335b967ac70c0a656b4d7f126d45792920cca5db04a9cdba89575ce38b892fd63e34c6983ef40193299a652954da34b1956878b3d6683b0624358d9102653ce7ce0c026d8c3126becc79b8e79e73cfcffdce9d7b377b8e35eb3b838180e05150785a40a97193ca65d5d5f76c5e31015da31082310c23da8685d5a4aee1962b795c88390cfd22ab6421a6aee1351b8435dcb36bfbd9786583f0cf2926f8e4934f3ef9e4934f3ef9e4934f3ef9e4934fec37b978ebb3f1768d2db05b05fcefadb14bd675dbb693933b4a83201333b9b3ad49dff5427d92ed8d6a6c574c6341b9987ca722907c3b1dac24769164e76374ae85ed8def03af06fc6fdfc276348eb7175ee401e747b01f408ecf9ec44e0083e07a3e2db5ea795daa2cb4824e67d3562faad9e54223da748040f229a954677cf89a008f8f8660cd7c0c3735999278a7002775011e222d35a2a4624031a2652fdab02f55cc7d02f21f29891cb3ed5131f721eee86c80b73a0441bea87d1170db116468405249be2d4694e9de035abee17e32b4996417c4fe9748beaa9c288b47f690a1c1525db94cb782be8ac6418c0df557266d55d758464db21e32b34557aed23292efbd49c6e682c9404feb4c180cd2247bae24fbe33c097c33f301516e6b93637710b198ba305302c232223e3e719243b9b06f9c64675b095be0e5d0a112953a9bb49e5b76cb42002d94e5ab556549c030825d97bb6b23464876a2150ff926bb54c0f60961b7c53d459e233f20c1895e13cbc392f5fb1d8c0f0ab65f52ada3b02533c4ad27c588790366a3dd3cdccc72320dfee6369076b7c3c116515d0ebb84c2b309b3cb49cace9bafbab371b393cf5a723f696c4c3c5124b95fc513e74aafd088a6ccd2a813bd87db34cb53cd72d1fc0835b8fdc27d7852531026573c5ae658beeeec23eaa552ced3ebe630588f6237aa003bb73d0f37762f37c40faf3369a291f9040c50a24eccc16b58c0d948cc89f897671f578c84f84960dde104c2e018e6519ef41c099be66e99b2ec00acd11260a511c30d62aca48f727fee8741a26bb3977bd933db304c94569343e0939b1adc4294ef8c4d9af2adb151d92fc568494ad1a50a2f3ee57ef2141e5f9cdf2c8d593abbc6a35a554bcec1c6ad5378c4702f3cbf7e271fac755afa92edde99ef419bfd521ac6ab21e6ae203a104d7c31c4dc188c432929aabc257dca15671c450c14a7b9e2634751018a335cf1de9a8784285075fa06e0eb09d27e6046907613e099007d4ddf7e4a7a1fcce901935775ec876a0271f0ded267c9f6d3125e11aa72340ec4117efff3ef4a6f6215b194d6a38b1ede611793b1d5c17bc4f97036c2f3c0fd7e59c2241c7ecbe2ff053fecc20ffe2bf8c1d5f0b1a96ad52e78f03f7731190f3bf0330efc07cfe27bc33d099bd3d90debeae25d975db6f1a63fd3d4f454757cf741da65d06a594e3424ea6a65ca4579b0be3e51d79078fc11774110127d9d7d46aff1f241216174640c2171a8fbf0e18e2ee3bffabd7ac07dac577ac02b7d6387d5ac6b0e07d6f997bbbaba75fa1ab7bf5d2bdcdb7f350fdd635fcfbbfe0f097f9fff4ffea131db"
)
_EXACT_COMPRESSED_BUSINESS_ELF_BYTES = bytes.fromhex(
    "78daed585d4c1c55149e5d760bea96591a6c89e50171926e13591924cad8c4cc96a5de318342a1d6f427d156745f0a0873e936416ab36ee215d7f862e28bb50f8d314d1ffa80c9149b652954da34b1956878b3d6683b0624358d9102653ce7ce0c026d8c3126becc79b8e79e33e7e77ee7eeb98473b449df110c04048f82c2b3024a0d1b542eabaebe7be3b209e81a84225843b0a26d485849ea2a6eb992c785a8c3d02fbc4216a2ea2a5ebd4e58c53dbbd69f8dd7d609ff9ca2824f3ef9e4934f3ef9e4934f3ef9e4934f3ef9c47e930bb74f8db5696c9eddcee3ffde1abb6cddb06d3b31b1bd24083231133b5a1bf59d2fd525d89e88c676463516940b89f7ca038977db8315c42e90cc5c94ce36b33db1bde0558f5ecd6c7bc3585bfe651e706e18e701e4d8cc099c043008aee7daa5163da74b15f916d0e96ccaea4135bb926f409b0e10482e2995e88c2f5f13e0b19122f8663e81879a484a7c52809bda000fd12e35a0a4624031ac652ed9702e55cc7e06f21f49891cb5ed1131fb319ee86c808f3a0441bea47d1970c71164b05f5249ae354a94a99efd5aaefe4132b89164e6c5be5748aeb28c280b877793c181125db9423783be92c6408c0ef655246c55d7585a4db06e32bd4957aed15292ebb945466783894077cb74080cda49e67c71e6c73912f866fa23a2dcd12646ef2262317971ba188425447c6cfc04877271ef18c9ccb41036cfcba143252a743661bdb0e49685005a28cb572bca12876518a72ef7d6460c93cc780b5ef22d76398fe313c2ee88bb0b3c47ae5f821bbd2e968524ebf7bb181f146c9fa45a47e0486611b79e10c3e64dd88d74f170d34b8976f037b780b4ab0d2eb680ea323825149e8d9b9d4e5276c17cdddd8d9929be6bcefea4b151f17881647f158f9f2fb94ac39a3243234ef46e6ed3244f36c905f313d4e0f1f30fe04d4d42986ce148a963f9a6738e88974ab9406f9843603d82d3a83c9cdcf63cdcd83ddc107f78a9848946e653b04089529883d7308fbbe1a813f12fcf5eae182ee2378175871b088163884779da73246c8abba54b33fdf08d16032b091b6e1063397d84fb733f0c12599dbdcccb9ede826122b48a1c049fece4c026a27c676cd0946f8df5ca3e294a8b938a2e957bf129f79327f1fa62bcb33466e9ec3a8f6a552e3a171bb34ee215435f787e7d4e3ef896b2f445dbed99ef419b39270d616b88d9ab880e44135f0c313b0aeb60528a28ef489f73c519471105c569aef8d4519483e20c577cb0ea21210a549dbe05f8ba83b40f9811a45d04783a40dfd0b79d943e0473badfe4551dfde1510271b06fe9f364db69095b84aa1c8d037198f77fee7de96dac2296d27a7cc1c33be46232363b780f3b3f9cf5f03c70bf5f16310987dfbcf07fc10fb9f083ff0a7e70257c1caa5a35f31efc2f5c4cc6630efcb403ffe1b3f8de704fc2667576d3bab6704fb3cb3676fa738d8dcf54c5761da09d06ad92e5787dbcb646a65c9407eaeae2b5f5f127b7ba1f0421de9bea357a8c570f0871a3236d08f1835d870e75741affd5dfab87dcc77a7906bc3c377658f59ae170608d7f99abab5da3af76e7db35c2fdfd57f2a2fb9ceb45d7ff11e1eff3ff090a6531de"
)
WORKER_ELF_BYTES = zlib.decompress(_EXACT_COMPRESSED_WORKER_ELF_BYTES)
BUSINESS_ELF_BYTES = zlib.decompress(_EXACT_COMPRESSED_BUSINESS_ELF_BYTES)


class ConstructionK7H1NestedCreatorLeafRolesNativeV2Error(ValueError):
    """The registered leaf source, image, ABI, claims, or seals changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorLeafRolesNativeV2Error(message)


@dataclass(frozen=True, slots=True)
class LeafRoleFrameV2:
    opcode: int
    sequence: int
    nonce: bytes
    pid: int
    role_slot: int
    parent_pid: int
    status: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.opcode) is not int or self.opcode not in OPCODES.values()
            or type(self.sequence) is not int or not 0 <= self.sequence < 1 << 64
            or type(self.nonce) is not bytes or len(self.nonce) != 16
            or type(self.pid) is not int or not -(1 << 63) <= self.pid < 1 << 63
            or type(self.role_slot) is not int or self.role_slot not in ROLE_SLOTS.values()
            or type(self.parent_pid) is not int or not 0 < self.parent_pid < 1 << 64
            or type(self.status) is not int or not -(1 << 31) <= self.status < 1 << 31
        ):
            _fail("leaf V2 frame fields are outside the exact ABI")

    def to_bytes(self) -> bytes:
        return _FRAME.pack(
            FRAME_MAGIC, FRAME_VERSION, self.opcode, self.sequence, self.nonce,
            self.pid, self.status, self.role_slot, self.parent_pid,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> "LeafRoleFrameV2":
        if type(raw) is not bytes or len(raw) != FRAME_BYTES:
            _fail("leaf V2 frame length changed")
        magic, version, opcode, sequence, nonce, pid, status, slot, parent = _FRAME.unpack(raw)
        if magic != FRAME_MAGIC or version != FRAME_VERSION:
            _fail("leaf V2 frame prefix changed")
        return cls(opcode, sequence, nonce, pid, slot, parent, status)


def _exact_role(slot_or_name: int | str) -> tuple[str, int, bytes, str]:
    if type(slot_or_name) is str and slot_or_name in ROLE_SLOTS:
        name = slot_or_name
    elif type(slot_or_name) is int and slot_or_name in ROLE_SLOTS.values():
        name = next(key for key, value in ROLE_SLOTS.items() if value == slot_or_name)
    else:
        _fail("unknown leaf role slot")
    if name == "WORKER":
        return name, ROLE_SLOTS[name], WORKER_ELF_BYTES, WORKER_ELF_SHA256
    return name, ROLE_SLOTS[name], BUSINESS_ELF_BYTES, BUSINESS_ELF_SHA256


def verify_nested_creator_leaf_role_images_v2() -> dict[str, object]:
    source = SOURCE_PATH.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        _fail("leaf V2 source digest changed")
    if (
        len(WORKER_ELF_BYTES) != ELF_BYTE_COUNT
        or len(BUSINESS_ELF_BYTES) != ELF_BYTE_COUNT
        or hashlib.sha256(WORKER_ELF_BYTES).hexdigest() != WORKER_ELF_SHA256
        or hashlib.sha256(BUSINESS_ELF_BYTES).hexdigest() != BUSINESS_ELF_SHA256
        or WORKER_ELF_BYTES == BUSINESS_ELF_BYTES
        or WORKER_ELF_BYTES[:4] != b"\x7fELF"
        or BUSINESS_ELF_BYTES[:4] != b"\x7fELF"
        or platform.machine() not in {"x86_64", "AMD64"}
    ):
        _fail("leaf V2 exact static ELF registration changed")
    expected_opcodes = {
        "ROLE_READY": 1, "ROLE_GO": 2, "ROLE_GO_ECHO": 3,
        "ROLE_SHUTDOWN": 4, "ROLE_BYE": 5, "PROTOCOL_FAILURE": 6,
    }
    if (
        OPCODES != expected_opcodes or ROLE_SLOTS != {"WORKER": 1, "BUSINESS": 2}
        or GO_SEQUENCE != 1 or SHUTDOWN_SEQUENCE != 2
        or FRAME_MAGIC != 0x3256524C43514641 or FRAME_VERSION != 2
        or FRAME_BYTES != 64 or CONTROL_FD != 3
        or _FRAME.size != 64 or _FRAME.format != "<QIIQ16sqiIQ"
        or REQUIRED_SEALS != 15
        or BUILD_ARGV_PREFIX != (
            "gcc", "-Os", "-nostdlib", "-static", "-fno-pie", "-no-pie",
            "-fno-stack-protector", "-fno-asynchronous-unwind-tables",
            "-fno-unwind-tables", "-fcf-protection=none", "-Wl,--build-id=none",
            "-Wl,-z,noexecstack", "-Wl,-s",
        )
    ):
        _fail("leaf V2 ABI/build registration changed")
    source_text = source.decode("utf-8")
    required_tokens = (
        "ACFQP_LEAF_ROLE_SLOT", "SO_PEERCRED", "SCM_CREDENTIALS",
        "PR_SET_PDEATHSIG", "SYS_getppid", "SYS_close_range",
        "guardian.pid == parent_pid", "OP_ROLE_READY", "OP_ROLE_GO_ECHO",
        "OP_ROLE_SHUTDOWN", "OP_ROLE_BYE", "OP_PROTOCOL_FAILURE",
    )
    if any(token not in source_text for token in required_tokens):
        _fail("leaf V2 source-closed identity/protocol implementation changed")
    claims = (
        FREESTANDING_NO_LIBC_SOURCE_PRESENT,
        EXACT_STATIC_WORKER_ELF_IMAGE_PRESENT,
        EXACT_STATIC_BUSINESS_ELF_IMAGE_PRESENT,
        EXTERNAL_GUARDIAN_CREDENTIAL_CHECK_IMPLEMENTATION_PRESENT,
        ACTUAL_PARENT_PID_BINDING_IMPLEMENTATION_PRESENT,
        PDEATHSIG_PARENT_LIFETIME_BINDING_IMPLEMENTATION_PRESENT,
        BOUNDED_READY_GO_SHUTDOWN_IMPLEMENTATION_PRESENT,
    )
    negative_claims = (
        RUNTIME_TOOLCHAIN_INVOCATION_PRESENT,
        REGISTERED_BROKER_IMAGE_ATTESTATION_PRESENT,
        WORKER_RESOURCE_SEMANTICS_PRESENT,
        BUSINESS_RESOURCE_SEMANTICS_PRESENT,
        WORKER_ROLE_BIRTH_BY_BROKER_OBSERVED,
        BUSINESS_ROLE_BIRTH_BY_BROKER_OBSERVED,
        ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT,
        E4_V2_COMPLETION_PRESENT,
        PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT,
        FQ11_COUNTER_COMPLETENESS_PRESENT,
        FORMAL_COUNTER_RECORDS_ISSUED,
        FORMAL_WORK_VECTOR_ISSUED,
        FORMAL_COMPARISON_VECTOR_ISSUED,
        CURRENT_ACCESS_AUTHORITY_PRESENT,
        FORMAL_V7_AUTHORITY_PRESENT,
        OFFICIAL_EXECUTION_ALLOWED,
    )
    if any(value is not True for value in claims) or any(value is not False for value in negative_claims):
        _fail("leaf V2 claim boundary changed")
    if OFFICIAL_SCALAR_COST is not None or OFFICIAL_N_BREAK_EVEN is not None:
        _fail("leaf V2 official scalar claims changed")
    if COUNTER_COMPLETENESS_GATE != "NOT_RUN" or WORKLOAD_ECONOMICS_GATE != "NOT_RUN":
        _fail("leaf V2 gate boundary changed")
    return {
        "profile_key": PROFILE_KEY,
        "readiness": READINESS,
        "source_sha256": SOURCE_SHA256,
        "worker_elf_sha256": WORKER_ELF_SHA256,
        "business_elf_sha256": BUSINESS_ELF_SHA256,
        "elf_byte_count": ELF_BYTE_COUNT,
        "role_slots": dict(ROLE_SLOTS),
        "control_fd": CONTROL_FD,
        "external_guardian_credential_check_implementation_present": True,
        "actual_parent_pid_binding_implementation_present": True,
        "pdeathsig_parent_lifetime_binding_implementation_present": True,
        "registered_broker_image_attestation_present": False,
        "direct_lifecycle_observed": False,
        "worker_resource_semantics_present": False,
        "business_resource_semantics_present": False,
        "worker_role_birth_by_broker_observed": False,
        "business_role_birth_by_broker_observed": False,
        "actual_observed_e3_v2_completion_present": False,
        "e4_v2_completion_present": False,
        "production_shared_resource_receipts_present": False,
        "formal_v7_authority_present": False,
        "official_execution_allowed": False,
    }


def create_sealed_nested_creator_leaf_role_memfd_v2(slot_or_name: int | str) -> int:
    name, _slot, image, expected_sha = _exact_role(slot_or_name)
    verify_nested_creator_leaf_role_images_v2()
    descriptor = os.memfd_create(
        f"acfqp-h1-{name.lower()}-role-v2", MFD_CLOEXEC | MFD_ALLOW_SEALING
    )
    try:
        written = 0
        while written < len(image):
            count = os.write(descriptor, image[written:])
            if count <= 0:
                _fail("leaf V2 ELF memfd short write")
            written += count
        if hashlib.sha256(os.pread(descriptor, len(image) + 1, 0)).hexdigest() != expected_sha:
            _fail("leaf V2 ELF memfd bytes changed")
        fcntl.fcntl(descriptor, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEALS:
            _fail("leaf V2 ELF memfd seal set changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def create_sealed_nested_creator_worker_memfd_v2() -> int:
    return create_sealed_nested_creator_leaf_role_memfd_v2("WORKER")


def create_sealed_nested_creator_business_memfd_v2() -> int:
    return create_sealed_nested_creator_leaf_role_memfd_v2("BUSINESS")


verify_nested_creator_leaf_role_images_v2()
