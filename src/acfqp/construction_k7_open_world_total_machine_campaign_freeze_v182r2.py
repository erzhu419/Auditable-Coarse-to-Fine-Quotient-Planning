"""Freeze the successful V182r2 campaign and producer-free verification."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_open_world_total_machine_campaign_independent_verifier_v182r2 as verifier
from acfqp import construction_k7_open_world_total_machine_execution_preregistration_v182r2 as preregistration
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = (
    "93c4b9bb327d3f1ed7e050e7effe9a421461a5210c5fc4a00416062aa346f914"
)
EXPECTED_CAMPAIGN_BYTE_COUNT = 129_036
EXPECTED_CAMPAIGN_SHA256 = (
    "be128d64b82d353a0e189ea293b6cb2d440bc6f90d8a08e7d9c513f836aaddcb"
)
EXPECTED_VERIFICATION_ID = (
    "bcdf5d0a45f6749065a63e3c9e8af5255217a7b7aa1fed1c949d9300c5242cbe"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 1_488
EXPECTED_VERIFICATION_SHA256 = (
    "f16675e9e6de3df0c963f39c505d5ca1a38aef13fafd2d7f98213100786b81b1"
)
EXPECTED_PROGRESS_IDS = (
    "dddb031c34727470fd7d68a7816ef4548dc4ca7ebaa5a2fcb7b79e5d5f77ff45",
    "6581a04b2ea6ab09d211c9088e09d0091d7dec752f4fefa8d94a7c8d06e06597",
    "38bfbfdfdddc4ca51caabb689e332e07b2a4f53ffeef4e1ce55064703deda088",
    "40753f938643328d05f22591be8c5ff87dd1722e40661fec3699a1b59c3c0171",
    "67c50d354f441868524a0b16709f4a17d1183e96a3b79bfd245cd94cb6d53b94",
    "efbb4bfa04e1e3f4d726d0e7b19c64753684b5285d4a6f43102b1dd19d05b785",
    "6c87b51aec551ab22476488ffa797b9e5b998c40519108686c55461246c1bbb9",
    "8f2472f9185737b79358676d8e78e9ac149aeb02ae3cfdc2ca55193ea1c74fd5",
    "99c64b85d88ae7179375b354531a69f1e78d9a9a25f6ef2991d425472fd54eba",
    "4e912d8dcea81376355f1ff6d6a089ee321ce0d71ecedfaa73619d131cf9f942",
    "723b359d4520e5be8db62705c150115c437744fc4f707d6948c5635ccc75792a",
    "75bea303ccd482162e5a798bf9e373e9d2c82b7a9d21e6f39cd3c35781d8a23b",
    "563090495489a27919430cb86b192c9963f1a2ff316cbd12ca4726220860a053",
    "59753f609d7a5a1ca89884bfe91ef0035325bb959042cc7ddb9e6ff7822a7688",
    "b379f6f3aa0080f5af77312f218177d9d5ef9d274915a8542b4c4820a4874c4f",
    "e092ebbe4c87b0f3de6f81e15a123682383fcc8ffe22c661006fd52648c4e289",
    "3d8040ae7e44e9ab9fe4052c51638b270d91aa10e442c67c3efbcc9387ebe2d0",
    "af083cba216bf137cac7596b785630ab1fa2e7d09ae6d806e248a712bbf72e06",
    "13a80a40e7cc983f3a82571789ed9d710efe7215db903bab6645fb0199326067",
    "a83ddb98e94e967767f2c428038125160e007d13c14b4b4eb9db96ece3430f0c",
    "1c07ffc4b3a9eab799f20bb1e6d5815b63df4b59dbba50e8cc91336aa09d5b9c",
    "49edba1e135132a7d5dd033a50f46ede3b67b55153d76a38cffee188e42df0d4",
)


def verify_retained_open_world_total_machine_campaign_v182r2(
    root: Path,
) -> dict[str, Any]:
    campaign_bytes = (root / "CAMPAIGN.json").read_bytes()
    campaign = loads_canonical_json(campaign_bytes)
    if not (
        type(campaign) is dict
        and canonical_json_bytes(campaign) == campaign_bytes
        and campaign["campaign_id"] == EXPECTED_CAMPAIGN_ID
        and len(campaign_bytes) == EXPECTED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_bytes).hexdigest() == EXPECTED_CAMPAIGN_SHA256
        and tuple(campaign["progress_checkpoint_ids"]) == EXPECTED_PROGRESS_IDS
        and campaign["progress_checkpoint_count"] == len(EXPECTED_PROGRESS_IDS)
    ):
        raise ValueError("V182r2 frozen campaign identity or progress changed")
    verification = (
        verifier.verify_open_world_total_machine_campaign_independently_v182r2(
            campaign_bytes,
            root / "progress",
            expected_execution_preregistration_id=(
                preregistration.EXPECTED_PREREGISTRATION_ID
            ),
        )
    )
    verification_bytes = canonical_json_bytes(verification)
    if not (
        verification["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(verification_bytes) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(verification_bytes).hexdigest()
        == EXPECTED_VERIFICATION_SHA256
        and verification["target_labels_avoided"] == 6
        and verification["all_registered_episodes_terminal"] is True
        and verification["broad_iid_sample_efficiency_claimed"] is False
        and verification["arbitrary_domain_transfer_claimed"] is False
        and verification["total_work_dominance_claimed"] is False
        and verification["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and verification["official_execution_allowed"] is False
    ):
        raise ValueError("V182r2 frozen independent verification changed")
    return verification


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_PROGRESS_IDS",
    "EXPECTED_VERIFICATION_ID",
    "verify_retained_open_world_total_machine_campaign_v182r2",
)
