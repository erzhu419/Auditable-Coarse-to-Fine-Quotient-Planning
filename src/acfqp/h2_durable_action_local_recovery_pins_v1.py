"""Literal source and canonical-artifact pins for the registered V0-055 gate.

This module deliberately contains no executable authority and imports no
project module.  Keeping the literals outside the orchestrator lets that
orchestrator verify its complete source file without a self-hash cycle.
"""

from __future__ import annotations


EXPECTED_ACTION_INDEXED_SOURCE_SHA256 = (
    "4c13ddfd21f84c4d73a696fc3adb9bf3ef2d6a08b2e9551eaa331d1b5e9ed9b5"
)
EXPECTED_TRANSPORT_MODULE_SHA256 = (
    "be28e08fd6afb7a58ff2a21d8db5cd0ffde66eb825fe55c18b2d679391edc2f1"
)
EXPECTED_B_RUNNER_SOURCE_SHA256 = (
    "36c19bde129ee48c67908ad0b0bb4c4322aadf3258997185849f9b318073e6e2"
)
EXPECTED_B_MODULE_SHA256 = (
    "bf5518ca07693f8796140095afe118510a920ed7e1acf92714cca6871739a57e"
)
EXPECTED_ORCHESTRATOR_MODULE_SHA256 = (
    "5ce67266946f97469f2ad580c087dc6504b5f7790ceea87b3a355408a57e8f8b"
)

EXPECTED_CANONICAL_IDS: dict[str, str] = {
    "c1_commit": (
        "c6ad62138768a969c302c8d78445789899f1f1cdad8eb73e1207c255d3859a68"
    ),
    "c1_manifest": (
        "f3e67443ad64b9bc69179ed7df0cfa925e35cdd164a202a65621ccc8c95c26ab"
    ),
    "c1_payload": (
        "9b715ce256b4bebad0f228cc4972d543a9a97d9ed7fbe444a693e0d2b8167508"
    ),
    "c1_snapshot": (
        "309c55509bcbadd79b0d8c33b1bcf7ba4c942ff793207cecd4f77e0a600014c6"
    ),
    "c2_commit": (
        "cb644f0ba1fc61c7a589cf2f0779d5a852c6519512e4e235aed2893b97c57783"
    ),
    "c2_manifest": (
        "44f4c9f4d839c0269cae3714baacd9b0d27b91c7f4614baeb70e2a08f1babc9c"
    ),
    "c2_payload": (
        "b6d2c58d4586eabae72ded584531547858671b54e3808a0907cc37bf490c65dc"
    ),
    "c2_snapshot": (
        "3ecfa6d7da777b43dc9e2295dd9aa1992fef77941fdf9fe1c3750cb57e842593"
    ),
    "campaign_result": (
        "e912ed1ee00f4d937e63cb41e732a183012013f56abff222efa522f19d7f4e89"
    ),
    "evaluation_replay_report": (
        "833659d5a7a934c260192544bbe8202754974d5a6e9c97e4248fb34ba98d37e9"
    ),
    "failed_proof_verification": (
        "aecdd95396aa48ef963268e1fa61058a5b441ca0926238f3aca31c36476b7198"
    ),
    "ground_authorization": (
        "1746808a1f68edbbec9dcff34215f82c51a73cac9c1e5e52f867bb440b9ecde3"
    ),
    "overlay_projection": (
        "7bd717073903c8e47231615e0f007c1373412eba8b1a879b4b20868e8bd77aee"
    ),
    "overlay_snapshot": (
        "d32a77dfba1e454b8ac8d586af8ff2a562ed08fe99b0b4e51a71bc653f9a6d0f"
    ),
    "p1_attestation": (
        "fed5b9eb802d56737303150253297abb56452be47eb2a62545e28068f62c055b"
    ),
    "p1_root_replay": (
        "d8d823f7ecf36d0948befb47a193564ca48360814acfd84e57a21f774c3ebd18"
    ),
    "p2_continuation": (
        "fee2e53b86333fbc3db02009ecd7ab4a6ad1544f2da703d7a209d0266fd11a28"
    ),
    "p3_attestation": (
        "8b09a7af65a35c1c76147be3060cefe1bdb08da7e81aa105b0cf85f06729149f"
    ),
    "p3_root_replay": (
        "c36d41749061e503f1491d472af0b0094683226620e19f59e4d987020b92db53"
    ),
    "protocol": (
        "461aedcae3b3acade7bf197e8d6f12371531d8b69acfbb08f8ce39dddd851a42"
    ),
    "recovery_trace": (
        "b49802387a00e4834075c268f6fba9701c10feb9952f2a29df6c6ce4f7bbefc2"
    ),
    "source_evidence_bundle": (
        "76b4d028d9cda285ed6692d940d7d5a2062f9bf7859eb5f01fe01426a3f2f85c"
    ),
    "source_overlay_build": (
        "0614d53923d44abae6ffbea765743bb11524ae33096dbe282eb9f4d2dc9824a2"
    ),
    "source_v0054b_result": (
        "1389019bf1b5eddd088246ec591a100fef243069615294d1c686e1242b24ffa1"
    ),
}


__all__ = [
    "EXPECTED_ACTION_INDEXED_SOURCE_SHA256",
    "EXPECTED_B_MODULE_SHA256",
    "EXPECTED_B_RUNNER_SOURCE_SHA256",
    "EXPECTED_CANONICAL_IDS",
    "EXPECTED_ORCHESTRATOR_MODULE_SHA256",
    "EXPECTED_TRANSPORT_MODULE_SHA256",
]
