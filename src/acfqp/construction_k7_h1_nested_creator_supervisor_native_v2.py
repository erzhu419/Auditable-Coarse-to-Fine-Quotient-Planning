"""Exact source-closed BROKER-command-capable SUPERVISOR V2 role image.

V2 preserves the complete V1 wire prefix and adds one post-probe command
branch.  Opcode 13 consumes four ordered SCM_RIGHTS descriptors and the
SUPERVISOR itself performs clone3/execveat, pidfd escrow, ACK echo, WNOWAIT,
consuming reap, and an ECHILD proof for BROKER.  This module verifies and
materializes the role image only.  It launches no process and issues no
three/five-birth or accounting authority.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import platform
import struct
from typing import Any, NoReturn
import zlib


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-E-C-E5B-B2-D-SUPERVISOR-V2"
PROFILE_KEY = "construction_k7_h1_nested_creator_supervisor_native_v2"
READINESS = "AUDITED_SOURCE_CLOSED_BROKER_COMMAND_ROLE_IMAGE_ONLY"

FREESTANDING_NO_LIBC_ROLE_SOURCE_PRESENT = True
EXACT_STATIC_ELF_IMAGE_PRESENT = True
V1_WIRE_PREFIX_COMPATIBILITY_PRESENT = True
POST_PROBE_BROKER_COMMAND_GRAMMAR_PRESENT = True
BROKER_CLONE_EXEC_REAP_BRANCH_IMPLEMENTATION_PRESENT = True
BROKER_DESCRIPTOR_VALIDATION_IMPLEMENTATION_PRESENT = True
BROKER_CGROUP_O_PATH_VALIDATION_IMPLEMENTATION_PRESENT = True
BROKER_CONTROLLER_PEERCRED_VALIDATION_IMPLEMENTATION_PRESENT = True
BROKER_FAILURE_PIDFD_CONVERGENCE_IMPLEMENTATION_PRESENT = True
RUNTIME_TOOLCHAIN_INVOCATION_PRESENT = False

ACTUAL_SUPERVISOR_EXEC_OBSERVED = False
ACTUAL_NESTED_PIDFD_PROBE_BIRTH_OBSERVED = False
ACTUAL_BROKER_BIRTH_OBSERVED = False
THREE_BIRTH_PREFIX_AUTHORITY_PRESENT = False
FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT = False
ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT = False
E4_V2_COMPLETION_PRESENT = False
PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT = False
FQ11_COUNTER_COMPLETENESS_PRESENT = False
FORMAL_COUNTER_RECORDS_ISSUED = False
FORMAL_WORK_VECTOR_ISSUED = False
FORMAL_COMPARISON_VECTOR_ISSUED = False
FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED = False
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
    / "h1_nested_creator_supervisor_x86_64_v2.c"
).resolve(strict=True)
V1_SOURCE_PATH = (
    Path(__file__).resolve(strict=True).parent
    / "native"
    / "h1_nested_creator_supervisor_x86_64_v1.c"
).resolve(strict=True)
SOURCE_SHA256 = "a06c90bd9137b3b59171f0137400aa5964560ba7411833591446bb39205fc252"
V1_SOURCE_SHA256 = "3461a4b7215f04cf4a2c7274a8737968f438ed1bc8270027400c00b920c52750"
ELF_BYTE_COUNT = 16960
ELF_SHA256 = "d2c24e8d837a7528e894fe9d21da24fcd7950d7868a5713accde147710eab16b"
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

FRAME_MAGIC = 0x31564E5043514641
FRAME_VERSION = 1
FRAME_BYTES = 64
CONTROL_FD = 3
CHILD_GATE_FD = 4
BROKER_CHANNEL_FD = 3
BROKER_EXECUTABLE_FD = 4
BROKER_ELF_BYTE_COUNT = 12720
BROKER_ELF_REQUIRED_SEALS = 15
PID_CELL_BYTES = 4096
CLONE_PIDFD = 0x00001000
CLONE_PARENT_SETTID = 0x00100000
CLONE_CLEAR_SIGHAND = 0x100000000
CLONE_INTO_CGROUP = 0x200000000
REQUIRED_CLONE_FLAGS = (
    CLONE_PIDFD | CLONE_PARENT_SETTID | CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP
)
V1_OPCODES = {
    "SUPERVISOR_READY": 1,
    "PROBE_COMMAND": 2,
    "PROBE_PARENT_RETURN": 3,
    "PROBE_ACK": 4,
    "PROBE_REAP": 5,
    "SUPERVISOR_SHUTDOWN": 6,
    "SUPERVISOR_BYE": 7,
    "PROTOCOL_FAILURE": 8,
    "CHILD_CELL_WITHDRAWN": 9,
    "CHILD_GATE_READY": 10,
    "CHILD_RELEASE": 11,
    "CHILD_RELEASE_ECHO": 12,
}
OPCODES = {
    **V1_OPCODES,
    "BROKER_COMMAND": 13,
    "BROKER_PARENT_RETURN": 14,
    "BROKER_ACK": 15,
    "BROKER_ACK_ECHO": 16,
    "BROKER_REAP": 17,
}
BROKER_COMMAND_SEQUENCE = 2
BROKER_SHUTDOWN_SEQUENCE = 3
DIRECT_SHUTDOWN_SEQUENCE = 2
BROKER_COMMAND_DESCRIPTOR_ROLES = (
    "CONTROL_O_PATH_LEAF_GRANT",
    "PRISTINE_PID_CELL_MEMFD",
    "SEALED_BROKER_ELF_MEMFD",
    "BROKER_CHILD_SOCK_SEQPACKET_ENDPOINT",
)
BROKER_PARENT_RETURN_RIGHTS = ("CREATOR_PIDFD",)
BROKER_ACK_DIRECTION = "GUARDIAN_TO_SUPERVISOR_AFTER_DURABLE_ACK"
BROKER_ACK_ECHO_DIRECTION = "SUPERVISOR_TO_GUARDIAN_BEFORE_BLOCKING_WAIT"
BROKER_REAP_SEMANTICS = "WNOWAIT_THEN_CONSUME_THEN_ECHILD"
BROKER_FAILURE_SEMANTICS = (
    "PIDFD_KILL_OR_IMMEDIATE_DIRECT_CHILD_FALLBACK_THEN_CONSUME_"
    "THEN_ECHILD_THEN_CLOSE"
)
BROKER_FRAME_GRAMMAR = (
    (
        "BROKER_COMMAND",
        13,
        2,
        "GUARDIAN_TO_SUPERVISOR",
        "PID_IS_SUPERVISOR",
        4,
        "STATUS_FLAGS_FACT_A_ALL_ZERO",
    ),
    (
        "BROKER_PARENT_RETURN",
        14,
        2,
        "SUPERVISOR_TO_GUARDIAN",
        "PID_IS_BROKER",
        1,
        "RIGHT_IS_CREATOR_PIDFD_AND_FACT_A_IS_SUPERVISOR",
    ),
    (
        "BROKER_ACK",
        15,
        2,
        "GUARDIAN_TO_SUPERVISOR",
        "PID_IS_BROKER",
        0,
        "AFTER_DURABLE_ACK",
    ),
    (
        "BROKER_ACK_ECHO",
        16,
        2,
        "SUPERVISOR_TO_GUARDIAN",
        "PID_IS_BROKER",
        0,
        "BEFORE_SUPERVISOR_BLOCKING_WAIT",
    ),
    (
        "BROKER_REAP",
        17,
        2,
        "SUPERVISOR_TO_GUARDIAN",
        "PID_IS_BROKER",
        0,
        "STATUS_EXIT_STATUS_FLAGS_SI_CODE_FACT_A_ECHILD",
    ),
)

_COMPRESSED_ROLE_ELF_BYTES = bytes.fromhex(
    """
78daed5c7f7413f7915fc932185bb02698d6a4e43064e19c6ba11621172b10aa8d656ed52e392535817b0d0d44098f6b0249
8836350de5476415368aae691fb9428fbb72efe82bef42efe81dd7536c23191c7068d3c6711a70e3063ba4c00a19ecf0c336
18a39b99efee6a254c5e5efbdf3ded1fdefdee7e7766bef39d99cfccac9e37d5ca8bec361b671c766e2187a397eef1d0d863
3c10cd2970af9a73c0df42f88b731d9cf5f0649d2b74d2c6992b65271c165ac65ca927eb7c78269775b6bee7c862e3c93aef
d76f1b67e3bd874e079f18c37df6a394cb1ff9237fe48ffc913ff247fec81ff9237fe48ffc913ffeff1cae0e491daa7575d4
ba5a6a5dc724f584a41ee70b5bd54f5c2d97febdd5d522b9db83252f3bc76c738e95d22da9fe56e90d71d14335fe071f71e1
435e290b6d2ab22913dcdf762ae3f0ced2527e7b4baba85e8c6341ee53877cea31ede7e9745a6cf31461f52ec50c023e95ab
55fd4e9fea2f5d1c3e169ce08bd6973762e12dabbf4d35b48a4b49ae63e223e212517dbf118b7cb14e54df5ef275491d96b6
f4560339759e105f8daf443708e57234282cf5aa5ec12145f7093be0362c4bab02e6525b8d074e69594dc7ab5188b61a09c7
da24ba3918c7f686360667aa7df1dd38b87a030651af5024ab41fc734302c29589027816fb3291f00aa5a27e51452b539f16
aa71e441027ca118fa755a0a0d79f870001e47bc823473533a9d28f10a157cd80fb71a3db4d80139fa358fa4766b516419a9
133cbee803a592fb30ffd20198f0d5a83c999323365f6888e7bf77115fb9abc3e76ee7b79e81ebd0fa229b2feaefe7c33d30
8af89ca1ab76e58b52e89a930f1fc7e72faee0f8f0db285e3458087f5eacd366029fb69a152873aa367d8c0fff0f3e0e77f0
0dc86fe070011f7e9d5ef5c3abff8acf42d726f15b7f446b7c97e8c8ea3bd2a1a45dfd9a5f3b31924efb422d637da19ea1c5
b6c3c9fb508bd107c64a3096d17cc4a6ab70cbe7ee50be09d2d8c4a621182a0f7bdd4fd529b2d71d58a62c02e538dc358f2a
f7d7baba220ec15de317f9edad8ba2533fc4b9a95962d30d3cff85d83482e7cf894dd7f13c416cba86e73162d33072ddf226
da8457edfcc672f15171b9f84df1b1d625927a8d199214ea5d2d459f16aa64d8d672d85507b305b54f738ea019b4c5cb71e7
d3d7f59d97d43af80346e5c0bdf7486063958d0eb2619bde8b92e1811fac0c27549049787493906cfac5b272fda2bc0ca9ef
05eab1397045a624a9171ab197c5174aa137572f6f7575b85a5e768e9deb1c03ee36ee57603ea54a9faba5a103bdca705649
1d34fc159d75096e0a385c11d0fb3a7846a817ace9342e4b015e89bf44ae6570a53e2a5419ef81298bc438f6252605494306
c917aa9d6fa0a889b3f067b093975a770e5e0d1d7e420a5cd4d6a3272f4597f4a957c43a70c52dbda5b0d2f0b14d2562f309
789a9c014351bdaebea7fe26dc515f2905ae99f125b6179ec5c751dc01ff88155088382aaabf4fcd92025733f3167259f36c
c6bca414ad134ae39bb121c976423da1fd2decbd2f7088d6e5107c811629324fd0f7a4283688b3221b8422beb0d69596c22d
cab4f94f0b15ca94c5e101917fadcd17ba31c2bfd6224e6f134383b65afe97b0f7db85575180cd2c82b0c0283662bf523b75
0d7d14c82113228e5b3734a02c0c77d54f87bd090c6796c17618f608d8f2e13f800dd786d37cc37b37d0dacec5ed1c1aeb59
6d3e3e70a5c35deb13c9ffc518101824dd6b253750dbcc7a63ff8c8b7ec4a70e9062c425722029d62d56df045e4bd491848d
76ff3d90604b2f6727b1c22debc726ead1cbef4eac457a1340785787ecd6142d2364092e151b9e1007d94bc589f5385b4197
0a8c8cb29cc4772860b4d47785861dc119596b16708b1da497c48bfab403f102c3e0b57b4770b1c6ec03303b818a8d6338c6
dd4e6c602ff1db5ea440f2b4e097d58f1a6d8645805d37a1cd8a079189f6c3ab8689bbae2261a44a668cbb5fcf6c5c523b65
b50f8c1ca87f9799128bcb5388c33eda6d9349b11e13aaafe24e0311469491627464f5a2a43608319ad90954375290449247
716f118c0896d842a568b3b0c38611789f80711fa8693f1eb2a011181c3a91161e62004468544f831384a3da5343261af519
58c460086254356123c24fd128a88480c4fc5a5fb7f27929b441f0700a9f8549c1e2c426989674c00a740d5e40c9db91ffc5
41b849ea4173d10660186e09de29ab67708a86f7c461bac7cb9147857ad9bd4b1882bb4014bd28f99f23b43253c94e7ce3f8
a0b163a0c51cfdcaea2ea1de4656b4c554eedf0315573af9389c96b8ce631ae07ecaffc2ccd0882358210582af7bc203f5c5
ccccdac1d4dbbcaf13ea4be923a9e36d357e4c78beb11c120bf206ca2b20823591596fe9ad07a7d17a07401bab988d68dd38
584d9a38a2750ce8868641467b7300b7b90e032a08df4da1268e2b8bfd35928ea16d1a3b40390d0ce6a12c2c166c53c65046
508498524d5bccd60fea20dd033d417b01990430d60007336d425ed5884ad51918227cf2aafd787e96857484208eec7a83b0
0282e8c1674d358e01e65e805935e905d8a0300a9b8816082654a68580adda065b39ced5416b4addcb36cd6e99a95dba42db
5d2ccf6f161075839f4733ae44efc7c9895e4caf56820f451a0ca387f0ab7e2007f6097508118c26061e10ba1c662d831b8b
550d465361f4a88d1e54c4c6b118ab1ec1d05496cd2485e8bf13658a99de06422fe39893dd0332c66cb62ad0cf3eb26363a6
d4d62074c279225e1fea719ade0c2e360f072d1ced4f395e63da1afb6f1b93a21511e40b11591020519b0ab6ea05ab8e3690
4c9a1f8c4ec4886c8dade8d0b84a0a6e05b423173417fa73202894336b9da10fa7b2e124184628a160ba43c369630ac24b95
6907ee600e47fb17eeda58ec05c79b570b2832c3dca4e394ca58340670935c050e4e01198daf9eb6410e7c2c455f618bf05c
06a54da3b927690628a84256f708bb69310dc25e4eb75db8c6ef6cda4e3018b4aca060325e0e8cd9169d4b674448a6c073d1
f2407f65ae01b03e0c89433616704b2ea345296e66180e3d0c472eb15023450f100d6281aefaee8061807b840ab811fc124e
ffe330b2d3a538316c4891b44af124062374bc4c443357ffc0258ccb4f082bf4c004ee5761c994586044e723d8b72ef95b26
33cdca6c08b740bd411b2b1ec484419b0792c77023751e3015431de51b92beb994ded830bd79f622b38d79b2aa11150a21ca
2488b0db60a2521c6a165e45beb91e7816b3b1f5d719a46472196d1a1254cf1934592265a17c27502e02852ab78798aa39a5
141c723310753708985be4723a839cf8ebba56299c315e145b59e684995bb5f66f9fe88b617999dacdb2a75c82a791607c98
e13f33d17821330873a7767c9285f72021ca6a207e37c108335ab119b7ceb05cb604742d34de62f6641ff9650f8b33b8af39
02fd11059a3dac0bcfbc74cde58c318329bb064c53103fc13870047439b311f5171f638d9c6ff4df3272e2e4c4c7c8ebd035
c34689c058ab8dfe4b3fdae806c3460de4eca1559fb358a732c59278c52f51c574f0198ce863c483cf11ecbd89b0e755354b
c5740b7c7c0bcedadb7d3a3e22d2946b07fb4c84848444fb8f3e1323213e683fe96320e9c98064d52820e9b182a4d702920b
cb28d05459f09152292e0b2717680ff6a141776384d891d5614067da9155afe11d8a6301a08b36b0576f84a070a5b9911f21
83dc1ef0339ec1cfcb93d8142f4641133f633a60c1cd4ac0860af51081f83d7db968ba201b4df13deda71758f2840967a934
bf41e8310da33d1b52275c24481d3221d4954648bd8e856f640fd936a89b1007d01673056fa45970d8095b4701d3f66c30fd
098ab4c2360a986ae72d605aaf47629c896ac4e0600553ba0f60eac5c16ad6fea826c0b8094c6f07ff59e0554f65b01445d2
1c97d0878e7e062c3dddcfdcb29ad9f9f17e2c072fb3c131187855b67e94732883a6a829fd12a35d168c7a4d18a5ddf9fe15
16d0db33303a985c9781d1664a266837a4400afd949630001bb68a5f0b9606504a908a506a4c4735723666929862ace28f37
b000e1ebb3e2294930fe4a2e9e2287e405c253b0424c485800aa0091d0fcb4e65e82d3851638d51f6bf7f66630b55ddfc96a
7cf0dd3e169aa4f9fb04096e045de63b91cb0c58499c8d97738195c4796c84cdd96168c3c456d2c79914ee4cda1ab5f4f6c3
3e723b1d5c99175bf19578165fcec557e299b2e26bf320a12c6dfd6f2fe4a06c33a50926ca3aec06ca6ae353cc82bc1044b1
0201da15762bd056d975a0adb67337fb25016de03a5bfb6e7b56e740fbc5b90c6d06b53a87dd268759c0613f72b8c31b3920
c4d083c30384b99576c2dcbdf69b9912e65e18ce28dc02bb62b31577b7d363add21084a05756cf5aa1b73d1b7aff51a76b9a
35435f6323ef38970bbd310bf432b30606e87068d0c5fab67632ac45638fb045c1c86933636c0678dbb38177ac0ebc5ee6f3
9013acc0c4b19c4c7717b3cf6eb0e99c9a3bc6ca0eaa8eb5bb92089a7d7afb371309244b28d01c494b013ea811acb076f039
8d15e07e5817041d56687d59effafaa9cf6794ddf50c6876099b7556dbe0bcdb5c211f7e912900bb0e46f5bd9a0f3f697484
f5ba9b8cfe3bc836c248f8a2cf954aee7efea543d4157696984d61d7786c0abfe573b7f05b678eb73685a7c328223aa5e8bc
bb434376652e6b0c4fc639cd42391a331f1e3b9e45002766d5e3348a88f888c04a4abfc587fb9cc8ddd307e2dfc66f4d39f5
26f12927912962647ee744d1db911265f48734bbca42ab76e0acb5457c28f957e4c0feb152e8d490ecfe55b0d0e73ea4acd1
25b229df4270050c448194e588a7f35972a7f831d6c1a00c0735de08a32f0eb660fb5799cb72a5f1566095cf5214bc53440b
e5922e0848a177d22967027bd2a9c2c410b59d92ef14d096a0e05838d3b782c01e4255cc5af4a411d134c22207261e6268c8
a1085990ad4cc6ddd270fd250d42bf0d1b096d169bce24787703e72654f1412cd3c9d881b3ccb1b35fcf8d563809539a775d
c6266b9adf765f8961e158507748aa0656857b34bd849a512052709a946e89bcd280afb85fa137158daf2c7cf573a080c308
84e95629345ca8fc0c08d3920dacc7c4813e704864ad7c63cf643eb4d64e12902ee841bcd8c1e0fb2804afa013289f990c94
57c3bca622ce229e78d0ce65dea52edc3978ef7e4470e52dcb7d49bd682425ca7ebc8fcacef092e835b07462b613990ddb2c
7c9082fe1265fdc464bf0b98b467ee77322ac0a1096307c68c3876b91bcbf442b3e83406199df744e687c4b68c0f3f0fec36
3320dcc43c1546d36154cb8797b2d10c18c97cd8c74677c268111f9ecf46028cec7c78361bcd84918d0f4f63a3596c34918d
aad8cc02369a0ba385de97f709ae02f4b0f3987914ef13eea651378c9aee4503a20a1ef26c19c547e3c40f1c7e5af28546b3
aee3c3bfc48f3a1bc0b6f4ef3b1b04b9900fef36fa71f8d68ac689baf7607095c16cf1acf57ecc74e33054899a51db509b6b
80cc0aa7b24af7599caefc9deeb3537120eb3e8b3f0156bec272d6c56a0fa5a294cc1922b2a4f4e1d42ad8e40648b15353e0
e2d778510a17ff851763e1429d6471ef2b80dc7ce5f8f72731a06ba73ceac6a155fcc636f2b5e4db90352c2a7efa7ece976e
f36d4993e9f5d5369cb72416bf001acc314f59138b1fea09cfa8c970d7a93f2119962cc970d5a8c9301f6eb065f2b4a3b08b
a0228f0733f93726a163e247804b7b126637dc68d8bf846badc1663a35fa678278921be29272faa6049adac71f40fe1c321a
ed25f01ee54c168fd210bfd59306fd06a4ff3179f3066c7a66e6d18cfa9360050b0a8277e0e305f40d80b5dbc3068f9f3183
ab7604efc239d5a37c30009c2ec27eeff7f4af06dffed4cf045bf5590f495031a0b6b0eef5a3fa8ddf9a8b31560435e889c2
76dda6ebb0703e8648bd02a7c51e40e2fa170bc4596dc3196ae36d7c3c52cbb93b952f48d15a87147d0da9798b2b21b84aee
76e50a1a916794cf281894fb402b86793d0c390524e49257fdc8c8b7131f2102fc93dda2f15bbf7f1be624e12e2c4ba48d77
6061f21520e5553f48bc4fe6ca48261753dad8553fde17b8c46a9fdf7c6ca95af46f4dc9666cc0e8791c83cb09d4ff4b19e9
9ee6e9b1f6fff45a855a80b7aa5776a2b5e97d9329fa52133d56e1f653753a7a9d52d64308ed67d2f0d63ae5fbdd548edc73
539df2fe297a3055d6eb14e536845d7f0183dd6558b9cc32a9bc7bf6e60de8c60db8ddd4412997692d88ecc3ac91ebbaba8d
5c97b25459af5564157b68465322ab64315570d2aa829f1b0bcba90f7e7092e5b6125064e5086b8d596b1024a88cd3eb90e0
6dd6857c88694c1d11d45dd82876761bf50da7cd261e17f59e5b76f581b43147996ca5fa074c86cb4e611274ca284e2a40c3
d5ac1ec15ceaa6fa4421219aac426ca70dd0eb10f584f65390d668fcc9ea19568050a0e9f4f0db8fa02f74d00746bd39c26c
1751660289e46938cf87af415d97a02fcdfd1746ad7eb48519367d8c397da7da9ed9a401300fd43973943d3d0600745901e0
07172c451099c944ab61947f78eb2228e32b7d7f4a1184115202f102834cc00253c00fac02f69fb77c4aa5907d4356afd1ae
e6a69cbf437db59cbfa95b801186bcf01f40bfec833c35ab9c80753848be02ef18397e70b24154568f267e8f24d79cc7aaea
b0d9e0a488d5d9355a332bebe54e7cb9ea7c66ff0cb552a7536bee62df5e4badbd82cc4f148c3e9de17816d5296571f6fd0f
4c3ef5a018a76ee72231be0ecf0b217df83104da64f320d810fea424c901ca27f04725c9814b70853f2b49f6e215feb02479
0aafb0b648765ea2df976013d4abf65bbaa5fe65626391697b318ca6093bfb6555a8b71451a688d3bf1914f185da2608caf4
715f0af46b5f04213ff5fdf29bde7fec9ce5fd149860fe376cf9237fe48ffc913ff247fec81ff9e3b31f2b03ab9e7b76f66a
d7ecc7d73df3d493eb66bf3037fb39b6c7ade3eb39e3c19cf170cef86acef85ace7824677c23677c3c67fc373535f755542e
795c591b542a5cae39f3e654cd762934746d9c3b774ed5bc3977dfa53fe0b839cfaf7e3eb82eb8f2716e4ef0c9fa203767dd
334fac0caee4e6049e59b3e6c9b5c13f5f7f25faef0accff2d60fe1f037632ff7f817ed872de9fa8dfb31b37ccff67c04efb
73e6e7fe5f8229fafb5539f7f7ebefcfe646e76f3d178cb2ae0ff5f767709f2effff018d0078c8
    """
)
ROLE_ELF_BYTES = zlib.decompress(_COMPRESSED_ROLE_ELF_BYTES)

class ConstructionK7H1NestedCreatorSupervisorNativeV2Error(ValueError):
    """The registered V2 source, dependency, ELF, ABI, or seal changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1NestedCreatorSupervisorNativeV2Error(message)


def verify_nested_creator_supervisor_native_image_v2() -> dict[str, Any]:
    """Replay both source inputs, static ELF layout, ABI, and claim locks."""

    if platform.system() != "Linux" or platform.machine().lower() not in {
        "x86_64",
        "amd64",
    }:
        _fail("nested-creator supervisor V2 is registered only for Linux x86-64")
    try:
        source = SOURCE_PATH.read_bytes()
        v1_source = V1_SOURCE_PATH.read_bytes()
    except OSError as error:
        raise ConstructionK7H1NestedCreatorSupervisorNativeV2Error(
            "nested-creator supervisor V2 source closure is unavailable"
        ) from error
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        _fail("nested-creator supervisor V2 source digest changed")
    if hashlib.sha256(v1_source).hexdigest() != V1_SOURCE_SHA256:
        _fail("nested-creator supervisor V2 V1-source dependency changed")
    if (
        SCHEMA_VERSION != "1.0.0"
        or PROPOSED_CONTRACT_VERSION
        != "2.0.59-E-C-E5B-B2-D-SUPERVISOR-V2"
        or PROFILE_KEY
        != "construction_k7_h1_nested_creator_supervisor_native_v2"
        or READINESS
        != "AUDITED_SOURCE_CLOSED_BROKER_COMMAND_ROLE_IMAGE_ONLY"
        or BUILD_TOOLCHAIN
        != {
            "cc": "gcc 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)",
            "ld": "GNU ld (GNU Binutils for Ubuntu) 2.38",
        }
        or BUILD_ARGV
        != (
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
    ):
        _fail("nested-creator supervisor V2 registration identity changed")
    if (
        len(ROLE_ELF_BYTES) != ELF_BYTE_COUNT
        or hashlib.sha256(ROLE_ELF_BYTES).hexdigest() != ELF_SHA256
    ):
        _fail("nested-creator supervisor V2 ELF image changed")
    if ROLE_ELF_BYTES[:16] != b"\x7fELF\x02\x01\x01" + bytes(9):
        _fail("nested-creator supervisor V2 ELF identity changed")
    (
        elf_type,
        machine,
        elf_version,
        entry,
        program_offset,
        section_offset,
        flags,
        header_bytes,
        program_entry_bytes,
        program_count,
        section_entry_bytes,
        section_count,
        section_string_index,
    ) = struct.unpack_from("<HHIQQQIHHHHHH", ROLE_ELF_BYTES, 16)
    if (
        elf_type != 2
        or machine != 62
        or elf_version != 1
        or entry != 0x403582
        or program_offset != 64
        or section_offset != 16640
        or flags != 0
        or header_bytes != 64
        or program_entry_bytes != 56
        or program_count != 4
        or section_entry_bytes != 64
        or section_count != 5
        or section_string_index != 4
    ):
        _fail("nested-creator supervisor V2 ELF header changed")
    program_rows = [
        struct.unpack_from("<IIQQQQQQ", ROLE_ELF_BYTES, program_offset + 56 * index)
        for index in range(program_count)
    ]
    expected_rows = [
        (1, 4, 0, 0x400000, 0x400000, 0x120, 0x120, 0x1000),
        (1, 5, 0x1000, 0x401000, 0x401000, 0x25C2, 0x25C2, 0x1000),
        (1, 4, 0x4000, 0x404000, 0x404000, 0xB0, 0xB0, 0x1000),
        (0x6474E551, 6, 0, 0, 0, 0, 0, 0x10),
    ]
    if program_rows != expected_rows:
        _fail("nested-creator supervisor V2 load or stack segments changed")
    if (
        tuple(V1_OPCODES.values()) != tuple(range(1, 13))
        or tuple(OPCODES.values()) != tuple(range(1, 18))
        or tuple(OPCODES.items())[:12] != tuple(V1_OPCODES.items())
    ):
        _fail("nested-creator supervisor V2 additive opcode registry changed")
    if (
        FRAME_MAGIC != 0x31564E5043514641
        or FRAME_VERSION != 1
        or FRAME_BYTES != 64
        or CONTROL_FD != 3
        or CHILD_GATE_FD != 4
        or BROKER_CHANNEL_FD != 3
        or BROKER_EXECUTABLE_FD != 4
        or BROKER_ELF_BYTE_COUNT != 12720
        or BROKER_ELF_REQUIRED_SEALS != 15
        or PID_CELL_BYTES != 4096
        or CLONE_PIDFD != 0x00001000
        or CLONE_PARENT_SETTID != 0x00100000
        or CLONE_CLEAR_SIGHAND != 0x100000000
        or CLONE_INTO_CGROUP != 0x200000000
        or REQUIRED_CLONE_FLAGS != 0x300101000
        or REQUIRED_SEALS != 15
        or BROKER_COMMAND_SEQUENCE != 2
        or BROKER_SHUTDOWN_SEQUENCE != 3
        or DIRECT_SHUTDOWN_SEQUENCE != 2
        or BROKER_COMMAND_DESCRIPTOR_ROLES
        != (
            "CONTROL_O_PATH_LEAF_GRANT",
            "PRISTINE_PID_CELL_MEMFD",
            "SEALED_BROKER_ELF_MEMFD",
            "BROKER_CHILD_SOCK_SEQPACKET_ENDPOINT",
        )
        or BROKER_PARENT_RETURN_RIGHTS != ("CREATOR_PIDFD",)
        or BROKER_ACK_DIRECTION
        != "GUARDIAN_TO_SUPERVISOR_AFTER_DURABLE_ACK"
        or BROKER_ACK_ECHO_DIRECTION
        != "SUPERVISOR_TO_GUARDIAN_BEFORE_BLOCKING_WAIT"
        or BROKER_REAP_SEMANTICS != "WNOWAIT_THEN_CONSUME_THEN_ECHILD"
        or BROKER_FAILURE_SEMANTICS
        != (
            "PIDFD_KILL_OR_IMMEDIATE_DIRECT_CHILD_FALLBACK_THEN_CONSUME_"
            "THEN_ECHILD_THEN_CLOSE"
        )
    ):
        _fail("nested-creator supervisor V2 fixed command ABI changed")
    expected_frame_grammar = (
        (
            "BROKER_COMMAND", 13, 2, "GUARDIAN_TO_SUPERVISOR",
            "PID_IS_SUPERVISOR", 4, "STATUS_FLAGS_FACT_A_ALL_ZERO",
        ),
        (
            "BROKER_PARENT_RETURN", 14, 2, "SUPERVISOR_TO_GUARDIAN",
            "PID_IS_BROKER", 1,
            "RIGHT_IS_CREATOR_PIDFD_AND_FACT_A_IS_SUPERVISOR",
        ),
        (
            "BROKER_ACK", 15, 2, "GUARDIAN_TO_SUPERVISOR",
            "PID_IS_BROKER", 0, "AFTER_DURABLE_ACK",
        ),
        (
            "BROKER_ACK_ECHO", 16, 2, "SUPERVISOR_TO_GUARDIAN",
            "PID_IS_BROKER", 0, "BEFORE_SUPERVISOR_BLOCKING_WAIT",
        ),
        (
            "BROKER_REAP", 17, 2, "SUPERVISOR_TO_GUARDIAN",
            "PID_IS_BROKER", 0,
            "STATUS_EXIT_STATUS_FLAGS_SI_CODE_FACT_A_ECHILD",
        ),
    )
    if BROKER_FRAME_GRAMMAR != expected_frame_grammar:
        _fail("nested-creator supervisor V2 frame grammar changed")
    if (
        FREESTANDING_NO_LIBC_ROLE_SOURCE_PRESENT is not True
        or EXACT_STATIC_ELF_IMAGE_PRESENT is not True
        or V1_WIRE_PREFIX_COMPATIBILITY_PRESENT is not True
        or POST_PROBE_BROKER_COMMAND_GRAMMAR_PRESENT is not True
        or BROKER_CLONE_EXEC_REAP_BRANCH_IMPLEMENTATION_PRESENT is not True
        or BROKER_DESCRIPTOR_VALIDATION_IMPLEMENTATION_PRESENT is not True
        or BROKER_CGROUP_O_PATH_VALIDATION_IMPLEMENTATION_PRESENT is not True
        or BROKER_CONTROLLER_PEERCRED_VALIDATION_IMPLEMENTATION_PRESENT is not True
        or BROKER_FAILURE_PIDFD_CONVERGENCE_IMPLEMENTATION_PRESENT is not True
        or RUNTIME_TOOLCHAIN_INVOCATION_PRESENT is not False
        or ACTUAL_SUPERVISOR_EXEC_OBSERVED is not False
        or ACTUAL_NESTED_PIDFD_PROBE_BIRTH_OBSERVED is not False
        or ACTUAL_BROKER_BIRTH_OBSERVED is not False
        or THREE_BIRTH_PREFIX_AUTHORITY_PRESENT is not False
        or FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT is not False
        or ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT is not False
        or E4_V2_COMPLETION_PRESENT is not False
        or PRODUCTION_SHARED_RESOURCE_RECEIPTS_PRESENT is not False
        or FQ11_COUNTER_COMPLETENESS_PRESENT is not False
        or FORMAL_COUNTER_RECORDS_ISSUED is not False
        or FORMAL_WORK_VECTOR_ISSUED is not False
        or FORMAL_COMPARISON_VECTOR_ISSUED is not False
        or FORMAL_ACTUAL_PROJECTION_PROOF_ISSUED is not False
        or CURRENT_ACCESS_AUTHORITY_PRESENT is not False
        or FORMAL_V7_AUTHORITY_PRESENT is not False
        or OFFICIAL_EXECUTION_ALLOWED is not False
        or OFFICIAL_SCALAR_COST is not None
        or OFFICIAL_N_BREAK_EVEN is not None
        or COUNTER_COMPLETENESS_GATE != "NOT_RUN"
        or WORKLOAD_ECONOMICS_GATE != "NOT_RUN"
    ):
        _fail("nested-creator supervisor V2 claim locks changed")
    required_source_tokens = (
        b"CLONE_PIDFD | CLONE_PARENT_SETTID |",
        b"CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP",
        b"SYS_execveat",
        b"OP_BROKER_PARENT_RETURN",
        b"OP_BROKER_ACK_ECHO",
        b"WEXITED | WNOWAIT",
        b"result != -ECHILD",
        b"received->fd_count != 0 && received->fd_count != 4",
        b"broker_cgroup_fd = command.fds[0]",
        b"broker_pid_cell_fd = command.fds[1]",
        b"broker_executable_fd = command.fds[2]",
        b"broker_channel_fd = command.fds[3]",
        b"validate_broker_command_descriptors(",
        b"REQUIRED_BROKER_ELF_SEALS",
        b"BROKER_ELF_BYTE_COUNT",
        b"F_GETFL) & O_PATH",
        b"SO_PEERCRED",
        b"kill_consume_prove_close_broker",
        b"SYS_pidfd_send_signal",
        b"command.frame.status != 0 || command.frame.flags != 0 ||",
        b"report.fact_a = (uint64_t)(uint32_t)self_pid",
        b"report.fact_a = ECHILD",
    )
    if any(token not in source for token in required_source_tokens):
        _fail("nested-creator supervisor V2 source grammar changed")
    return {
        "source_sha256": SOURCE_SHA256,
        "v1_source_dependency_sha256": V1_SOURCE_SHA256,
        "elf_sha256": ELF_SHA256,
        "elf_byte_count": ELF_BYTE_COUNT,
        "entry_point": entry,
        "program_headers": [list(row) for row in program_rows],
        "frame_magic": FRAME_MAGIC,
        "frame_version": FRAME_VERSION,
        "frame_bytes": FRAME_BYTES,
        "opcodes": dict(OPCODES),
        "v1_wire_prefix_compatible": True,
        "post_probe_broker_command_grammar_present": True,
        "broker_command_sequence": BROKER_COMMAND_SEQUENCE,
        "broker_command_descriptor_roles": list(BROKER_COMMAND_DESCRIPTOR_ROLES),
        "broker_parent_return_rights": list(BROKER_PARENT_RETURN_RIGHTS),
        "broker_frame_grammar": [
            {
                "name": row[0],
                "opcode": row[1],
                "sequence": row[2],
                "direction": row[3],
                "pid_semantics": row[4],
                "scm_rights_count": row[5],
                "payload_semantics": row[6],
            }
            for row in BROKER_FRAME_GRAMMAR
        ],
        "broker_shutdown_sequence": BROKER_SHUTDOWN_SEQUENCE,
        "direct_shutdown_sequence": DIRECT_SHUTDOWN_SEQUENCE,
        "required_clone_flags": REQUIRED_CLONE_FLAGS,
        "broker_elf_byte_count": BROKER_ELF_BYTE_COUNT,
        "broker_elf_required_seals": BROKER_ELF_REQUIRED_SEALS,
        "broker_reap_semantics": BROKER_REAP_SEMANTICS,
        "broker_failure_semantics": BROKER_FAILURE_SEMANTICS,
        "broker_clone_exec_reap_branch_implementation_present": True,
        "broker_descriptor_validation_implementation_present": True,
        "broker_cgroup_o_path_validation_implementation_present": True,
        "broker_controller_peercred_validation_implementation_present": True,
        "broker_failure_pidfd_convergence_implementation_present": True,
        "runtime_toolchain_invocation_present": False,
        "actual_supervisor_exec_observed": False,
        "actual_nested_pidfd_probe_birth_observed": False,
        "actual_broker_birth_observed": False,
        "three_birth_prefix_authority_present": False,
        "five_birth_process_authority_present": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate": "NOT_RUN",
        "workload_economics_gate": "NOT_RUN",
    }


def create_sealed_nested_creator_supervisor_memfd_v2() -> int:
    """Return the exact immutable V2 executable memfd; launch nothing."""

    verify_nested_creator_supervisor_native_image_v2()
    if not callable(getattr(os, "memfd_create", None)):
        _fail("memfd_create is unavailable")
    descriptor = os.memfd_create(
        "acfqp-h1-nested-creator-supervisor-v2",
        MFD_CLOEXEC | MFD_ALLOW_SEALING,
    )
    try:
        offset = 0
        while offset < len(ROLE_ELF_BYTES):
            written = os.write(descriptor, ROLE_ELF_BYTES[offset:])
            if written <= 0:
                _fail("nested-creator supervisor V2 memfd write made no progress")
            offset += written
        if os.lseek(descriptor, 0, os.SEEK_SET) != 0:
            _fail("nested-creator supervisor V2 memfd seek changed")
        fcntl.fcntl(descriptor, F_ADD_SEALS, REQUIRED_SEALS)
        status = os.fstat(descriptor)
        if (
            status.st_size != ELF_BYTE_COUNT
            or fcntl.fcntl(descriptor, F_GET_SEALS) != REQUIRED_SEALS
            or os.pread(descriptor, ELF_BYTE_COUNT + 1, 0) != ROLE_ELF_BYTES
            or fcntl.fcntl(descriptor, fcntl.F_GETFD) & fcntl.FD_CLOEXEC == 0
        ):
            _fail("nested-creator supervisor V2 sealed memfd changed")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


__all__ = (
    "BROKER_ACK_DIRECTION",
    "BROKER_ACK_ECHO_DIRECTION",
    "BROKER_CHANNEL_FD",
    "BROKER_COMMAND_DESCRIPTOR_ROLES",
    "BROKER_COMMAND_SEQUENCE",
    "BROKER_EXECUTABLE_FD",
    "BROKER_ELF_BYTE_COUNT",
    "BROKER_ELF_REQUIRED_SEALS",
    "BROKER_FAILURE_SEMANTICS",
    "BROKER_FRAME_GRAMMAR",
    "BROKER_PARENT_RETURN_RIGHTS",
    "BROKER_REAP_SEMANTICS",
    "BROKER_SHUTDOWN_SEQUENCE",
    "BUILD_ARGV",
    "BUILD_TOOLCHAIN",
    "ConstructionK7H1NestedCreatorSupervisorNativeV2Error",
    "DIRECT_SHUTDOWN_SEQUENCE",
    "ELF_BYTE_COUNT",
    "ELF_SHA256",
    "FRAME_BYTES",
    "FRAME_MAGIC",
    "FRAME_VERSION",
    "OPCODES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "READINESS",
    "REQUIRED_CLONE_FLAGS",
    "REQUIRED_SEALS",
    "ROLE_ELF_BYTES",
    "SCHEMA_VERSION",
    "SOURCE_PATH",
    "SOURCE_SHA256",
    "V1_OPCODES",
    "V1_SOURCE_PATH",
    "V1_SOURCE_SHA256",
    "create_sealed_nested_creator_supervisor_memfd_v2",
    "verify_nested_creator_supervisor_native_image_v2",
)
