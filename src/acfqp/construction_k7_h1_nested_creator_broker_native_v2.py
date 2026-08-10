"""Exact source-closed BROKER V2 role image for the H1 creator chain.

This module verifies and seals one checked-in freestanding Linux x86-64 ELF.
It never invokes a compiler, launches a process, consumes a construction
permit, or issues an authority claim.  The image implements the full bounded
four-right WORKER/BUSINESS creator protocol, while the runtime evidence added
with this slice intentionally exercises only READY -> GO -> SHUTDOWN.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import struct
from typing import Any, NoReturn
import zlib


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.61-E-C-E5B-B2-D-BROKER-ROLE-V2"
PROFILE_KEY = "construction_k7_h1_nested_creator_broker_native_v2"
READINESS = "SOURCE_CLOSED_ROLE_IMAGE_WITH_UNACTIVATED_CREATOR_BRANCH"

FREESTANDING_NO_LIBC_ROLE_SOURCE_PRESENT = True
EXACT_STATIC_ELF_IMAGE_PRESENT = True
LONG_LIVED_BROKER_COMMAND_LOOP_IMPLEMENTATION_PRESENT = True
GENERAL_FOUR_RIGHT_CREATOR_GRAMMAR_IMPLEMENTATION_PRESENT = True
CLONE3_EXECVEAT_PIDFD_CREATOR_IMPLEMENTATION_PRESENT = True
CREATOR_WNOWAIT_CONSUMING_REAP_IMPLEMENTATION_PRESENT = True
RUNTIME_TOOLCHAIN_INVOCATION_PRESENT = False

BROKER_CREATED_BY_SUPERVISOR_OBSERVED = False
WORKER_ROLE_BIRTH_OBSERVED = False
BUSINESS_ROLE_BIRTH_OBSERVED = False
CHANNEL_INDEPENDENCE_AUTHORITY_PRESENT = False
ROLE_IMAGE_SLOT_IDENTITY_AUTHORITY_PRESENT = False
ONE_SHOT_LEAF_AUTHORITY_PRESENT = False
FAILURE_CLOSURE_AUTHORITY_PRESENT = False
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
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
    / "h1_nested_creator_broker_x86_64_v2.c"
).resolve(strict=True)
SOURCE_SHA256 = "862971314b9c7b6120692eccab5fabc5ae8c99acf8affa5e2cf5a1c14fb4107a"
ELF_BYTE_COUNT = 12720
ELF_SHA256 = "7d4e0939ffadec8e1c1d21d24a91623dc31096dae946d8673caa6f1ddfb74139"
BUILD_TOOLCHAIN = {
    "cc": "gcc 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)",
    "ld": "GNU ld (GNU Binutils for Ubuntu) 2.38",
}
BUILD_ARGV = (
    "gcc",
    "-Os",
    "-nostdlib",
    "-static",
    "-fno-pie",
    "-no-pie",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-fcf-protection=none",
    "-Wl,--build-id=none",
    "-Wl,-z,noexecstack",
    "-Wl,-s",
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

FRAME_MAGIC = 0x3256524243514641
FRAME_VERSION = 2
FRAME_BYTES = 64
CONTROL_FD = 3
CHILD_EXEC_FD = 4
PID_CELL_BYTES = 4096
OPCODES = {
    "BROKER_READY": 1,
    "BROKER_GO": 2,
    "BROKER_GO_ECHO": 3,
    "CREATE_ROLE": 4,
    "ROLE_PARENT_RETURN": 5,
    "ROLE_ACK": 6,
    "ROLE_ACK_ECHO": 7,
    "ROLE_REAP": 8,
    "BROKER_SHUTDOWN": 9,
    "BROKER_BYE": 10,
    "PROTOCOL_FAILURE": 11,
}
ROLE_SLOTS = {"WORKER": 1, "BUSINESS": 2}
CREATE_ROLE_SEQUENCES = {"WORKER": 2, "BUSINESS": 3}
SHUTDOWN_SEQUENCE = 4
CREATE_ROLE_RIGHTS = (
    "GUARDIAN_SUPPLIED_CGROUP_V2_DIRECTORY",
    "WRITABLE_SHARED_PID_CELL_MEMFD",
    "SEALED_LINUX_X86_64_ET_EXEC_ELF_MEMFD",
    "GUARDIAN_SUPPLIED_SOCK_SEQPACKET_ENDPOINT",
)

_FRAME = struct.Struct("<QIIQ16sqiIQ")
_COMPRESSED_ROLE_ELF_BYTES = bytes.fromhex(
    """
78daed1b6b7054d5f9ee66033159b84b9b220ad88897024a629652650ddabdb0b1677533134b22b1820536517cf030dc4b42
8d3cbab9ca65bbd69962a79da2c30fa6630b6d9da933dd8475130910a82f88ad52a31251e126e1115e4904c2f6fbbe73ef66
37755aa6d35f9d3d33ecb9e7dcef7cefd7b99a0da5817bed369b600dbb708f80abb9e3bdb4f69afbab8b9320b0374770c06f
36fc22ac43481ddeb4b9c0446dcd828b4fb8cc4e590b2e6fdabc7fbc9036a79e237a163fc5deb479b2b96dcdd6b907be54aa
4709d73e5c426664466664466664466664466664466664466664c6ffcfd0cfba5bcfffbecdddca3c8794bc2dce519b9da359
a2b5b7af8d35c9f73e307fde0f1f9c852f45353fb421c7ae8ef5d439d5eb7067a14bdcdada26ebe7e278f3f6eb837efda0f1
87442221b77b73ecb0c5a21602bf2e94eae54ebf5eee2ad30e2a63fd91fa09cd78c30ee8eff636b62d08040febe7b5447d21
0b0e94ba5b4bdd07a303f0b6250b7ec46ca6b52ad35968b05f9912df8878f50f8d52a0c382e753816d04fc709bbb83e983a5
f86be262fa0762761ba06e390120c6c7c862851c7a3b51b9806d3ab911ce69fde20b5e98f5cbfa452db1ae980587008189fc
1e3814bf0e7edc1d9c973b809721a5588e5d054cdd489b0513c3f0afda46c08f427875a7c9fb09a61f339e83a34d0e41b0e9
a7f5a3c61558a17c6a4ea9fb8beedf2298d6aa8ef23c25b9943c393684645e442e08432426f1792bcdc65d262e8170bd86b8
e0f42d9e5d129e516f0cfba4099e46e957b818038b1c586c86859223c7ae00eade3949bcf87505f1e26c1c03ba4dd916de2a
9347b1b10af517bb0cbf5a67fd18300299c9d01060d35e54a74fef7a78b1bca84d5ee827abe03ff941bfde2f57faf521b9a2
7281bb93854e4e677abea407a47c1659e06225f992f8fc26802c8b4837f9c3f9120b5d12d7ae61e1d9129bf129f39cab7bac
ccd320e528e3f8cb3da359e8d820b3bddfdbca22b57d1b8f65a9c7997e2ea07f09fb57ee8b38a6301d8465254fc199b75944
75353b48cc064932c60ca1fb2892a4f5d7e772fef7e156689fa3f71db9bdb41c43037495cf427ba7a32cf262f911f9c72051
d2cef28372a5ac5f8c2f47e12a2a993eb4407fbf19bf7b8153cd41670a488e00509b108828d242e317a06bd65eea05bd2502
7a223e0799692f65b48eec20fb182bafe0cb81b88c8ba5b43811df8e8b0a3c1e018102ba823f5751bae9c47af47642e5935c
b2f9506ca3d8aa96e6e0cabb9d875168d0ab8a20149bba219168c9f349054a4ee860a27b1140377be9443fd3cf8084c6a9cb
c8549997852b24af3f52eb02fd8b3f6d0798fb238efc4058f08706c5badc268a809bd16bf4c3811987fd9e0375bda1fa1c5b
59a4aa4fc96d22cfb5c3ebb0d7191ab4abc5fed06527eca3db75f700b6d0b34b04b52f603bce22cf56343b51d05a20dd5eba
0425e8f5270ea825655aa79adb84fed6fd17d4757f5b96da177ab65c507b00dd37ebbe08e847004340ff28a0bfc7de34ec7a
69b93113e07b739b2ee129742a7fa875b43fd4355866dbd33d0d7347641ef84fd76000b25e6ed357b0e3f774a83f027e6c6a
becfb3a20212dde22af53a5097c353ba4819dd3488a1e27177ca6f300c45e4cfb3b87ced6c166c78d99bf40a7747403740d7
89369638a07cda3480b45089011dbcf38cd10da2f7da217d6eda8b3e92e25a95ee530b987ed9f364f9daa9a121875200feb9
d33bec9f53512fbe9de43f2cb1aff783f6f9e4a50f2f6e03e73b0cae1fcf83e502fd32849697411800b9474001c89a959ba6
f1f44919516ec64fb4296e3413637d91544cbec0f4d362b67ea4291f532be6cd8123226bfbf5c057a13dd52c78cef8256096
17521054501ec52fa62ce494047836009fdc9c03a72cad44c7221ebbe99ff4a996415878c5ec3756125807670b5e4e771279
d4a2de461c03af319bc0792da0d41a7d197e00762677f4139468d7e5c97144d6fd994818adec6f5812b3e05bccf3a6fa8fe8
eb70ac05b3411cb54987c5cd1a9c7a03151188544833e5a883501f8fde0133152b50a809ba4ce4892410779af081e67168a4
3f0e62dc800c008b67efb40a98a8dd0167420d209da8dd2652720980384e78f5c244be2e4794f5a1cfa196b4524de5162273
00a80b402a60ce37185061fa36e935ced4709d4505d54741b88da8dc7ad6ce333d69dbd6caf4465e3982a046a63b24dcd86e
591e941cafc5b7902644ed15b057185233b8ae0b2b4314f3a122398d4b60f7bc46290788a825cda8feb8ddac1e0863ec078f
879a57c0c280bfa451eac2b2f30d166e940c0483a37d587baec73273c80aa4969318a79bcdf45ccfd166d1f2670465bc3480
71e490ccdc4b8a21af359d950b42529bd270390e8c1184dd88ce12061c7c128b3c694361924c4f4567d6f703df4e74c4d37a
bbf12a042a150cf2b724e4897e12af2814231508aa9426e8f891828a8d1d4ee4af27ee4845b39da3b93dedf0cd81708c0e97
6909359f79b6110635d7a4e550a624cfbf77195318d720f0dbd28bfa6354497649dbb10179911c738784ffdd052b022f3b67
9261017bb3c979f54bf088c508c1e62297867191171e6a2f3a2f62a98c4983e828d974e2b4e9d2413000c88b0e3755005eef
46ab885a202b25fca25bc8e3f8790809f3e87480619b62c4deeadac782a2363e8b33dc95854e01f1d68c3fc086f190c9c115
e4605c12cddd987144ed38b89fbbd5dd21e7e63ba071e5dbead9c60e517b0b5eedc66c2dc7721dc4d37052388209d9444ace
324ad47e6347167649c5764b8190423b2f70ead8c5a4c8afef213956db4905cc9e54c14664ea213b06524c5a02f3f7c517ee
b3a725a423163e2e089452519b46b4aba5ea3866dce67c9ed78cc5a9d487650f0de68bda150cf406a97a83a89de58f35a5a0
0ffef86840d43af9e363f78ada21feb8dc2e6afbf8e3e336516be68f4fc0e39ff8a302003bf8e3da7bb6f82455d45e8265ae
4faadbec93268adaf3369ef0e6609a9b4b090ef973d8cc506ece1a4e79411ba5bcb90e51abe28f73b245adccc6c3bc2a993c
ab78f27cfa3c4f9eb3ff15ebb0c2afe78866431a75da286d3a4b7c5295a85de51d9b0b568b44adcfecdf60b544d48e09a641
77670b9625d0d0ad76ee73e559dcd667ce91e31b2760a6ec427e9234b7fa2d8b29ee3fbcbd870ebd13c32f84f0e00b888c41
8f8dc879e6ab32770ec08e7258a6f486a14197844420d8485e1847c7b5d4a7b701eafa25701fe8f5cab1cfb0f7f88e1cebc2
f926397614e7f172ec539cc7cab14f701e25c73ea6cec6cc113b2165764f027cf3b6386ff127f6e604a489fe4d57283c4e82
7d270a290965fd407a42f980ae369786130a571ab63767e2559c7fa3f56c2211b5d98a052c4651f2e73358735ae1112dcade
ec72526a268b4312c2055e8f40278366daee43c7feb30d85f6ebfbc8c47a0a04f08709c1178e993a2af60ae15d140ebef0eb
648ba6c914163de777603da50b07b50794b8796390db528f7dc16db6d4c4b4920738b7afc721a91f45f388a9a364da9675fc
1e266ebe80fd23dc1ea90d7be52cbf3938f9f2e7b0944357b39419fee0d561dc92cd2c60c017a0fa8985ea77d8f34273372d
ed8649d09879e1fa90032cb73cc3e1eb9f1d86a19625db6a59f06ad9d260422d649146d212c0c5278182d006e87382a963f2
48302eb939cce89972141d213acfea84c86e767e0670af47e10ef66159dcbbbe2e9c257bf6a9135964be8345c278d0dd91eb
c26ceb39a0f637762895c38ce659ae8c95f428a8d672b18990c6c30d52b14f3f6e34f4a5bbdbdff13609a6d7a0b369f91bfa
de33f0740d48f7437e2cd34eadbfd31786ceb554eb5ce705fc3eb8b0de308244bb49620a92d88f24260ca641f8f413ddd9b4
d54865098b763699fe13ab0d61d018e49d01312aa402c82e93b06d353d94ee73c02d8602a3d35ba52adbb0de410ab04405dd
8eb7518531369dc636eec3f8041444399d4a19aee00e3cfb3a41a20dd136f89ecf50590027bfd06210a181a3d6551b7728e5
b4f394e335cd3b9865be87e71c383ac17c46f6b0de1803a7209e8bac0f2ffc7a002ca078bc9f528a2c03ee3e9daeddf74ded
ee85c6a6a503b5db0c4fa91d240a421d64b48f3ac88d981e1f47258f32039d94f2dc29ea8ccae76d699c8b5575deacc6b948
c49f68cf8102e40f255ceae794bdd499ac649b548568a698a5565027a05920d556e3761e96e0e5b8af9424096c3d37ec8617
4fa54b71d894e22ab86acb2194e202b6429158d22146534c27927de91074aedc137869e7c64f69dce1a66eda7df892355299
2b47b0f19ec9461db2f12eb2b1e2228740eb535b66d1fb504627b019df3bc9d352f1880f673e60ae58cdf595ec920e61f529
a4e868372e9f4c27f98e49d28124df4692972e7008f40e224994044ed5d8071da73fd847d4809791046f4582e8a26a0164f2
2340196cb21cd7ae30774a0ff7d124434f8c60e82d93a135c046cb5f91a1c74d86ba920cc5b2920cc9cd18aa46513a5bfc66
885f0ebf4dca31ba7ad3a91c44c42e44acf730d3ccf19cd48bc7a45ecc43a86c3267988bc10d0ce8e9430c373a265a5eb9ac
e0c3f8cf15e80d3a408aed891b529a72a371ff08a60e50fe8366c870c39bdd74bd0a0d6589da9cf3e92195bc94d58003e9ed
fcfa4285a47beef9afbdbe4cefa1e8ba35797db9f67b1a226be941d6bace21bf784f2302b9a9ea3ad5fddfdcd3d499542c0d
b987fa9cf82afcf873931c5f8df37839fe34ce63e5f81a9c47c97185d2723fff9eeb844399eff89991199991199991199991
19d73a96061f7d7a75e1b2da554fd6d416066b6b962a35d585b5ab9eaa295c3b4bf8c1fcf977154caf5ca6ae54d402b7bb68
765171a15ba5a57bfdac5945c5b38bbe3bc37c2108456b96af516a95a5cb8422a5a65e118a6a57552f55960a45c1552b56d4
ac54fe27fce69997dce4ffcb9ffcbb013e25ff5ec01cb611e7c7997bb3ac8de4df0ff069b2f0f5e7adf906f3b97804dc6473
a3f03f9cc739eb6be4bacf3c3f45f8f7fcff13b734de94
"""
)
ROLE_ELF_BYTES = zlib.decompress(_COMPRESSED_ROLE_ELF_BYTES)


class ConstructionK7H1NestedCreatorBrokerNativeV2Error(ValueError):
    """The registered BROKER source, ELF, frame ABI, or seals changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorBrokerNativeV2Error(message)


@dataclass(frozen=True, slots=True)
class BrokerRoleFrameV2:
    opcode: int
    sequence: int
    nonce: bytes
    pid: int
    status: int = 0
    flags: int = 0
    fact_a: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.opcode) is not int
            or self.opcode not in OPCODES.values()
            or type(self.sequence) is not int
            or not 0 <= self.sequence <= (1 << 64) - 1
            or type(self.nonce) is not bytes
            or len(self.nonce) != 16
            or type(self.pid) is not int
            or not -(1 << 63) <= self.pid < (1 << 63)
            or type(self.status) is not int
            or not -(1 << 31) <= self.status < (1 << 31)
            or type(self.flags) is not int
            or not 0 <= self.flags < (1 << 32)
            or type(self.fact_a) is not int
            or not 0 <= self.fact_a < (1 << 64)
        ):
            _fail("BROKER V2 frame fields are outside the exact ABI")

    def to_bytes(self) -> bytes:
        return _FRAME.pack(
            FRAME_MAGIC,
            FRAME_VERSION,
            self.opcode,
            self.sequence,
            self.nonce,
            self.pid,
            self.status,
            self.flags,
            self.fact_a,
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> BrokerRoleFrameV2:
        if type(raw) is not bytes or len(raw) != FRAME_BYTES:
            _fail("BROKER V2 frame size changed")
        magic, version, opcode, sequence, nonce, pid, status, flags, fact_a = (
            _FRAME.unpack(raw)
        )
        if magic != FRAME_MAGIC or version != FRAME_VERSION:
            _fail("BROKER V2 frame identity changed")
        return cls(opcode, sequence, nonce, pid, status, flags, fact_a)


def verify_nested_creator_broker_native_image_v2() -> dict[str, Any]:
    """Replay the source, static ELF, bounded creator ABI, and claim locks."""

    expected_build_toolchain = {
        "cc": "gcc 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)",
        "ld": "GNU ld (GNU Binutils for Ubuntu) 2.38",
    }
    expected_build_argv = (
        "gcc",
        "-Os",
        "-nostdlib",
        "-static",
        "-fno-pie",
        "-no-pie",
        "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables",
        "-fcf-protection=none",
        "-Wl,--build-id=none",
        "-Wl,-z,noexecstack",
        "-Wl,-s",
    )
    expected_opcodes = {
        "BROKER_READY": 1,
        "BROKER_GO": 2,
        "BROKER_GO_ECHO": 3,
        "CREATE_ROLE": 4,
        "ROLE_PARENT_RETURN": 5,
        "ROLE_ACK": 6,
        "ROLE_ACK_ECHO": 7,
        "ROLE_REAP": 8,
        "BROKER_SHUTDOWN": 9,
        "BROKER_BYE": 10,
        "PROTOCOL_FAILURE": 11,
    }
    expected_rights = (
        "GUARDIAN_SUPPLIED_CGROUP_V2_DIRECTORY",
        "WRITABLE_SHARED_PID_CELL_MEMFD",
        "SEALED_LINUX_X86_64_ET_EXEC_ELF_MEMFD",
        "GUARDIAN_SUPPLIED_SOCK_SEQPACKET_ENDPOINT",
    )
    if (
        SCHEMA_VERSION != "1.0.0"
        or PROPOSED_CONTRACT_VERSION
        != "2.0.61-E-C-E5B-B2-D-BROKER-ROLE-V2"
        or PROFILE_KEY != "construction_k7_h1_nested_creator_broker_native_v2"
        or READINESS != "SOURCE_CLOSED_ROLE_IMAGE_WITH_UNACTIVATED_CREATOR_BRANCH"
        or SOURCE_PATH
        != (
            Path(__file__).resolve(strict=True).parent
            / "native"
            / "h1_nested_creator_broker_x86_64_v2.c"
        ).resolve(strict=True)
        or SOURCE_SHA256
        != "862971314b9c7b6120692eccab5fabc5ae8c99acf8affa5e2cf5a1c14fb4107a"
        or ELF_BYTE_COUNT != 12720
        or ELF_SHA256
        != "7d4e0939ffadec8e1c1d21d24a91623dc31096dae946d8673caa6f1ddfb74139"
        or BUILD_TOOLCHAIN != expected_build_toolchain
        or BUILD_ARGV != expected_build_argv
        or MFD_CLOEXEC != 0x0001
        or MFD_ALLOW_SEALING != 0x0002
        or F_ADD_SEALS != 1033
        or F_GET_SEALS != 1034
        or F_SEAL_SEAL != 0x0001
        or F_SEAL_SHRINK != 0x0002
        or F_SEAL_GROW != 0x0004
        or F_SEAL_WRITE != 0x0008
        or REQUIRED_SEALS != 0x000F
        or FRAME_MAGIC != 0x3256524243514641
        or FRAME_VERSION != 2
        or FRAME_BYTES != 64
        or CONTROL_FD != 3
        or CHILD_EXEC_FD != 4
        or PID_CELL_BYTES != 4096
        or OPCODES != expected_opcodes
        or ROLE_SLOTS != {"WORKER": 1, "BUSINESS": 2}
        or CREATE_ROLE_SEQUENCES != {"WORKER": 2, "BUSINESS": 3}
        or SHUTDOWN_SEQUENCE != 4
        or CREATE_ROLE_RIGHTS != expected_rights
        or _FRAME.format != "<QIIQ16sqiIQ"
        or _FRAME.size != 64
    ):
        _fail("BROKER V2 registered ABI, build, seal, or grammar changed")
    if not all(
        (
            FREESTANDING_NO_LIBC_ROLE_SOURCE_PRESENT,
            EXACT_STATIC_ELF_IMAGE_PRESENT,
            LONG_LIVED_BROKER_COMMAND_LOOP_IMPLEMENTATION_PRESENT,
            GENERAL_FOUR_RIGHT_CREATOR_GRAMMAR_IMPLEMENTATION_PRESENT,
            CLONE3_EXECVEAT_PIDFD_CREATOR_IMPLEMENTATION_PRESENT,
            CREATOR_WNOWAIT_CONSUMING_REAP_IMPLEMENTATION_PRESENT,
        )
    ) or RUNTIME_TOOLCHAIN_INVOCATION_PRESENT:
        _fail("BROKER V2 positive implementation claim locks changed")

    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        _fail("BROKER V2 is registered only for Linux x86-64")
    try:
        source = SOURCE_PATH.read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorBrokerNativeV2Error(
            "BROKER V2 source is unavailable"
        ) from error
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        _fail("BROKER V2 source digest changed")
    if (
        len(ROLE_ELF_BYTES) != ELF_BYTE_COUNT
        or hashlib.sha256(ROLE_ELF_BYTES).hexdigest() != ELF_SHA256
    ):
        _fail("BROKER V2 ELF image changed")
    if ROLE_ELF_BYTES[:16] != b"\x7fELF\x02\x01\x01" + bytes(9):
        _fail("BROKER V2 ELF identity changed")
    header = struct.unpack_from("<HHIQQQIHHHHHH", ROLE_ELF_BYTES, 16)
    if header != (2, 62, 1, 0x40163C, 64, 12400, 0, 64, 56, 4, 64, 5, 4):
        _fail("BROKER V2 ELF header changed")
    program_rows = [
        struct.unpack_from("<IIQQQQQQ", ROLE_ELF_BYTES, 64 + 56 * index)
        for index in range(4)
    ]
    if program_rows != [
        (1, 4, 0, 0x400000, 0x400000, 0x120, 0x120, 0x1000),
        (1, 5, 0x1000, 0x401000, 0x401000, 0x16C6, 0x16C6, 0x1000),
        (1, 4, 0x3000, 0x403000, 0x403000, 0x1D, 0x1D, 0x1000),
        (0x6474E551, 6, 0, 0, 0, 0, 0, 0x10),
    ]:
        _fail("BROKER V2 load or non-executable-stack segments changed")
    if _FRAME.size != FRAME_BYTES:
        _fail("BROKER V2 frame width changed")
    required_source_tokens = (
        b"SO_PEERCRED",
        b"guardian_credential.pid",
        b"child_peer.pid != guardian_pid",
        b"REQUIRED_PID_CELL_PRE_SEALS",
        b"!all_zero_bytes(pid_cell_bytes, PID_CELL_BYTES)",
        b"discard_control_rights",
        b"CLONE_PIDFD | CLONE_PARENT_SETTID |",
        b"CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP",
        b"SYS_execveat",
        b"CHILD_EXEC_FD, O_CLOEXEC",
        b"wait_known_child",
        b"struct siginfo_v2 empty",
        b"OP_ROLE_PARENT_RETURN",
        b"OP_ROLE_ACK_ECHO",
        b"WEXITED | WNOWAIT",
        b"result != -ECHILD",
        b"for (expected_sequence = 2, expected_slot = ROLE_WORKER;",
        b"valid_frame(&command.frame, OP_BROKER_SHUTDOWN, 4)",
    )
    if any(token not in source for token in required_source_tokens):
        _fail("BROKER V2 source creator or credential grammar changed")
    if any(
        (
            BROKER_CREATED_BY_SUPERVISOR_OBSERVED,
            WORKER_ROLE_BIRTH_OBSERVED,
            BUSINESS_ROLE_BIRTH_OBSERVED,
            CHANNEL_INDEPENDENCE_AUTHORITY_PRESENT,
            ROLE_IMAGE_SLOT_IDENTITY_AUTHORITY_PRESENT,
            ONE_SHOT_LEAF_AUTHORITY_PRESENT,
            FAILURE_CLOSURE_AUTHORITY_PRESENT,
            THREE_BIRTH_PREFIX_AUTHORITY_PRESENT,
            FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT,
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
    ):
        _fail("BROKER V2 static role image was promoted to authority")
    if (
        OFFICIAL_SCALAR_COST is not None
        or OFFICIAL_N_BREAK_EVEN is not None
        or COUNTER_COMPLETENESS_GATE != "NOT_RUN"
        or WORKLOAD_ECONOMICS_GATE != "NOT_RUN"
    ):
        _fail("BROKER V2 locked gate state changed")
    return {
        "source_sha256": SOURCE_SHA256,
        "elf_sha256": ELF_SHA256,
        "elf_byte_count": ELF_BYTE_COUNT,
        "entry_point": header[3],
        "program_headers": [list(row) for row in program_rows],
        "frame_magic": FRAME_MAGIC,
        "frame_version": FRAME_VERSION,
        "frame_bytes": FRAME_BYTES,
        "control_fd": CONTROL_FD,
        "opcodes": dict(OPCODES),
        "role_slots": dict(ROLE_SLOTS),
        "create_role_sequences": dict(CREATE_ROLE_SEQUENCES),
        "create_role_rights": list(CREATE_ROLE_RIGHTS),
        "shutdown_sequence": SHUTDOWN_SEQUENCE,
        "long_lived_broker_command_loop_implementation_present": (
            LONG_LIVED_BROKER_COMMAND_LOOP_IMPLEMENTATION_PRESENT
        ),
        "general_four_right_creator_grammar_implementation_present": (
            GENERAL_FOUR_RIGHT_CREATOR_GRAMMAR_IMPLEMENTATION_PRESENT
        ),
        "clone3_execveat_pidfd_creator_implementation_present": (
            CLONE3_EXECVEAT_PIDFD_CREATOR_IMPLEMENTATION_PRESENT
        ),
        "creator_wnowait_consuming_reap_implementation_present": (
            CREATOR_WNOWAIT_CONSUMING_REAP_IMPLEMENTATION_PRESENT
        ),
        "guardian_command_credentials_frozen_from_socket_peer": True,
        "ready_parent_fact_uses_actual_creator_parent": True,
        "pid_cell_full_width_zero_and_size_check_present": True,
        "pid_cell_resize_preseals_required": True,
        "sealed_linux_x86_64_et_exec_header_check_present": True,
        "guardian_supplied_child_channel_type_and_peer_check_present": True,
        "same_endpoint_inode_alias_rejection_present": True,
        "channel_independence_authority_present": False,
        "role_image_slot_identity_authority_present": False,
        "one_shot_leaf_authority_present": False,
        "failure_closure_authority_present": False,
        "malformed_rights_are_closed": True,
        "runtime_toolchain_invocation_present": False,
        "broker_created_by_supervisor_observed": False,
        "worker_role_birth_observed": False,
        "business_role_birth_observed": False,
        "three_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "official_execution_allowed": False,
    }


def create_sealed_nested_creator_broker_memfd_v2() -> int:
    """Return one exact immutable BROKER V2 executable memfd; launch nothing."""

    verify_nested_creator_broker_native_image_v2()
    if not callable(getattr(os, "memfd_create", None)):
        _fail("memfd_create is unavailable")
    descriptor = os.memfd_create(
        "acfqp-h1-nested-creator-broker-v2",
        MFD_CLOEXEC | MFD_ALLOW_SEALING,
    )
    try:
        offset = 0
        while offset < len(ROLE_ELF_BYTES):
            written = os.write(descriptor, ROLE_ELF_BYTES[offset:])
            if written <= 0:
                _fail("BROKER V2 memfd write made no progress")
            offset += written
        if os.lseek(descriptor, 0, os.SEEK_SET) != 0:
            _fail("BROKER V2 memfd seek changed")
        fcntl.fcntl(descriptor, F_ADD_SEALS, REQUIRED_SEALS)
        status = os.fstat(descriptor)
        if (
            status.st_size != ELF_BYTE_COUNT
            or fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEALS
            or os.pread(descriptor, ELF_BYTE_COUNT + 1, 0) != ROLE_ELF_BYTES
            or fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
        ):
            _fail("BROKER V2 sealed memfd changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


__all__ = (
    "BUILD_ARGV",
    "BUILD_TOOLCHAIN",
    "BrokerRoleFrameV2",
    "CHILD_EXEC_FD",
    "CONTROL_FD",
    "CREATE_ROLE_RIGHTS",
    "CREATE_ROLE_SEQUENCES",
    "ConstructionK7H1NestedCreatorBrokerNativeV2Error",
    "ELF_BYTE_COUNT",
    "ELF_SHA256",
    "FRAME_BYTES",
    "FRAME_MAGIC",
    "FRAME_VERSION",
    "OPCODES",
    "PID_CELL_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "REQUIRED_SEALS",
    "ROLE_ELF_BYTES",
    "ROLE_SLOTS",
    "SCHEMA_VERSION",
    "SHUTDOWN_SEQUENCE",
    "SOURCE_PATH",
    "SOURCE_SHA256",
    "create_sealed_nested_creator_broker_memfd_v2",
    "verify_nested_creator_broker_native_image_v2",
)
