"""Literal source and canonical-artifact pins for the registered V0-056 gate.

This module deliberately imports no project module and exposes no execution
authority.  The orchestrator verifies these literals before it can produce or
verify a campaign.
"""

from __future__ import annotations


EXPECTED_QUERY_FAMILY_MODULE_SHA256 = (
    "dad8e65bbcd58d0a15a368dc18166f93bc7be37da837dd98e7d934a987b063de"
)
EXPECTED_CONDITIONAL_DIRECT_MODULE_SHA256 = (
    "3d6910ba7f437bbdb92f82c068109541f6268071d601e72f9f5dc9b43a0c4bba"
)
EXPECTED_V0055_RECOVERY_MODULE_SHA256 = (
    "5ce67266946f97469f2ad580c087dc6504b5f7790ceea87b3a355408a57e8f8b"
)
EXPECTED_ORCHESTRATOR_MODULE_SHA256 = (
    "4cdb2f98e141eb25662c22c03e69c3ad65c632750ae5cfa37f7ea5c3f303244f"
)

EXPECTED_QUERY_LAUNCH_SOURCE_SHA256 = (
    "a713fe981e858f736b9b08695c3c2d60d243557af44fbf3bd18f2f6473788cca"
)
EXPECTED_QUERY_INITIALIZE_SOURCE_SHA256 = (
    "9cd7742ba6bd54a2491ef54c5d2867fd485efb43ea493fae7adda562d0a2419a"
)
EXPECTED_DIRECT_LAUNCH_SOURCE_SHA256 = (
    "f8ee03e868f67bd618f1d700cde61889013e4aa253790e49fbaa4609cf58cbd3"
)
EXPECTED_SOURCE_RUN_SOURCE_SHA256 = (
    "e6f858cab5adf2cd42b2175ffba4f6cc7f836c5d141245a594866242b16b895c"
)

EXPECTED_CANONICAL_IDS: dict[str, str] = {
    "campaign_result": (
        "8edf8a660fe3ceca19543aeb41d9c2683b540f15956abf0fe898f41aeb376122"
    ),
    "campaign_snapshot": (
        "85428384dace2b0ee86b086a1ec9ce465eb07557faf4bc03e283e33530427ab5"
    ),
    "direct_occurrences": (
        "0102e747996ba0c96a2fd3dbda7639fa2a3c92866eb6153f95a7208529d4b159"
    ),
    "direct_offline_base": (
        "88e0aba4c82ba709fde40ae49b39ce4c6c058447686b532cb8e937cb0cde53da"
    ),
    "direct_structural": (
        "423779b87731d094f6bfcf1f009c1f05ce0e03f55a8a4dcea1e3c052646464ac"
    ),
    "evaluation_replay_report": (
        "48e8919a089986892a2141f0b06edced07f0ae86a623d68b75817f6b33400ce7"
    ),
    "matched_occurrences": (
        "f8fe8f4dd5849b5d7092a4858be721997d63b4c9d1cdc471bff8608f78e441ba"
    ),
    "occurrences": (
        "bf68f4da74a553eae8817ef7f9602b3d4e6afae41c13b6573836c0d41bde3d2a"
    ),
    "offline_base_equivalence": (
        "52ef15351b2db72455f3821c3d5d17da98d297dea401cdf42ade614b94c1564a"
    ),
    "prefixes": (
        "e6dd91250127127ac49bd939fb3b92cbd87275725b2a99b38b849f7b8369ace3"
    ),
    "preregistration": (
        "2cde4f37b9e7cfd3f89d87c3f2a29811060f5a481accda6351c432a4da6761fb"
    ),
    "promotion_trace": (
        "ce7241d8e9e3e684cce11fb5b32518f112a667b86484c9ddc9a368786534bafd"
    ),
    "proof_semantics": (
        "5880e0a9a4d70efe5bfc387c3faf81fe1587f8e56c0130f10dc49fbe8c28c224"
    ),
    "protocol": (
        "928b8233021b2f961a485c57709e43dc1b368f167b46ecf7e15d9f5bf61f7787"
    ),
    "query_1": (
        "70840b5a859261981d4e3daba6bd5be9f19ac2b3de69b5c56c3f6dc8c73576ea"
    ),
    "query_2": (
        "02fe1960c53fc33711f15825ddc686eb98772764048977d4aa29a816e7caf11e"
    ),
    "query_3": (
        "f1f05b93d43517419e0ea24ee9c8430e061d9f6f9dbd9a5eb440fc7a22c1926a"
    ),
    "reset_occurrences": (
        "dd219556fa7c8e76bd8f2949f705e2a8fff9f9cfab40ee98db57b67635bb3add"
    ),
    "reset_initializations": (
        "20339c4e312e229ea5c002dc713b769751e2a55bbb86139b435a9bb1b67f3629"
    ),
    "source_c1_commit": (
        "c6ad62138768a969c302c8d78445789899f1f1cdad8eb73e1207c255d3859a68"
    ),
    "source_c2_commit": (
        "cb644f0ba1fc61c7a589cf2f0779d5a852c6519512e4e235aed2893b97c57783"
    ),
    "source_failed_verification": (
        "aecdd95396aa48ef963268e1fa61058a5b441ca0926238f3aca31c36476b7198"
    ),
    "source_ground_authorization": (
        "1746808a1f68edbbec9dcff34215f82c51a73cac9c1e5e52f867bb440b9ecde3"
    ),
    "source_result": (
        "e912ed1ee00f4d937e63cb41e732a183012013f56abff222efa522f19d7f4e89"
    ),
    "source_trace": (
        "27936f2fff9e4b4ad863a963f3a996705e9f027e65fa539d7c7d806a12a9ae4f"
    ),
    "telemetry": (
        "347e5b288c67d3c5d6116cd812e034573505db2c65248b60e205f5d099138f0b"
    ),
    "w0_commit": (
        "4e9deaec2baf32b8ccf8227d81c0f60572736e4dd465b08a761ddef851b55004"
    ),
    "w1_commit": (
        "8d15aae30b4932d155759178c4d89aeaccd4e9948c535ba505954f403703e5f5"
    ),
    "w2_commit": (
        "8e33d23a1369f7cad6d97981dda5e73d227cac0da73d9f394aa675309a8a0f51"
    ),
    "warm_occurrences": (
        "05ffab5931ca9b2cc895672dce69f4e5562cfa89ffe785543e29acef2db31a77"
    ),
}


__all__ = [
    "EXPECTED_CANONICAL_IDS",
    "EXPECTED_CONDITIONAL_DIRECT_MODULE_SHA256",
    "EXPECTED_DIRECT_LAUNCH_SOURCE_SHA256",
    "EXPECTED_ORCHESTRATOR_MODULE_SHA256",
    "EXPECTED_QUERY_FAMILY_MODULE_SHA256",
    "EXPECTED_QUERY_INITIALIZE_SOURCE_SHA256",
    "EXPECTED_QUERY_LAUNCH_SOURCE_SHA256",
    "EXPECTED_SOURCE_RUN_SOURCE_SHA256",
    "EXPECTED_V0055_RECOVERY_MODULE_SHA256",
]
