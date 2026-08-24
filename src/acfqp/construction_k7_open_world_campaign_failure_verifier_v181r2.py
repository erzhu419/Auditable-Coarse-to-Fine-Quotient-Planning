"""Producer-free verifier for the retained V181r2 interrupted campaign.

This verifier treats the interruption as a typed, non-success terminal.  It
replays the exact append-only progress chain and does not import the campaign,
oracle, compiler, or synthesizer producers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp import construction_k7_open_world_execution_preregistration_v181r2 as prereg
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_FAILURE_ID = (
    "6033595cb16f33d473de02e2c2329a13411678f14e1a979c5976207de6de1e47"
)
EXPECTED_FAILURE_BYTE_COUNT = 755
EXPECTED_FAILURE_SHA256 = (
    "500ec2390c1ad5b6d0975c9b7136a48dce1ca08f2d6ef8896c5360d3e951272c"
)
EXPECTED_CHECKPOINT_BYTE_COUNTS = (
    4916,
    13291,
    18587,
    23853,
    29149,
    34445,
    34443,
    4977,
    13290,
    18586,
    23853,
    29149,
    34445,
    34443,
)
EXPECTED_CHECKPOINT_SHA256 = (
    "530ecc61ac6c2199c2dbfb2283c14887572ad967dfa8bd9ebbcf0f86f3f78026",
    "5e6b16e42b344b19e78a20ef99e3c1603e23621295a1c9e28eadb5333864b780",
    "445b7817b9f784a2d5cf0354d60cba7e51bea20d5019610685424b762e80e9b6",
    "8e6b9ffc2d72ef7b8f49f7a1e6beb5bbf0b02e49e832c2c844b4cf81506d965b",
    "b0eb94ee926693642a46b881f033712757868ca208b78c8b6cab8dec21371364",
    "c29beec4c7737da0942242ff3a9090d1679b7d79fe19141c71b418ff4f4345da",
    "6d0aa07aaa146073a7630e4fee427ca1a40d72963d8dabb8e2f35d46fd68f283",
    "5b61c31e7f5ad96104f2ac30ad3bb63a600632e2b63753feb8d3a13a235e6dc5",
    "73307d140deba88b1e056f8c221636e12900f7a7a5266963d490836bebd2f237",
    "fa479a41929f12c7fa37382b7f86506d98f07a6e41cd40aa2f1d0f4ad38ed349",
    "ba49e9a8a223a4b6f60711870c32acf4f490bf41bd2f3f7bae47eb5a9a870c1c",
    "5fdf019817d3ef116476ea15ddb8062a4bcf48fa23bcea62eb20eec1735009d2",
    "98b14269f199af65abcac292dd5e7a48dd1c3f3c48923f504a0adc746c1fa36a",
    "889a3d12ed3cdccea3aa166642a968f76570f68e0fb8b0a4366438cd8ffd2abe",
)
EXPECTED_CHECKPOINT_IDS = (
    "381f2c71bdb22bb4812c7fde3c9fddf727e8a893960219e11daccd71333540cf",
    "7949cccff1cd4d6b3b34aa7db457b0fe9315fb555f183cc551833681bdc403dd",
    "26acf6f79600566b19b674fa8761eff6ef79a928ebd51885c50ff17d5ccbd01f",
    "ab13c0a5bf083bf7c091b8cd19f42252ced0e67cd3b21edde2d88b9247a0e29c",
    "9c0d7979e7f9ffe343cde2f9332d1f91addaa0c07e84ba542541ec9622f1d18b",
    "94130907ef90c65e406a535561b1eb34a66523fca5d652bb9f474d4adaf82cbc",
    "60f3523bb9e217a9def2d27627b2499545b2f1a7f25e48d50e5fa71adfd94c26",
    "bfe6c1aa801d965f4158cde8ed501da38fd41e53accf058b3df19b764ea02430",
    "4d7d51e2aea2e87d0cb89a5e3f72b8eef722f102a5d5dd22b6673e4a04d53ec3",
    "810161920649b690f143e14ebe49d977373902683b923225e6ca80d3a0ce1702",
    "b32745d67fbc92347622a03bc06c3a74d5493a8baa3adf7af1e9c452b5c2a005",
    "0e737f47bce4f97f7ea704cec98448ba26b7967672daf6e79ea707f205c5305d",
    "7045c8a13c8d7934c678f472f7ae95b74df2ac3d4db07010e7545d489b3430fb",
    "5d3815869653e32fd5fd437599abbbca214ca6f4cdaa826644b48c39accf062d",
)
EXPECTED_VERIFICATION_ID = (
    "dc3a679cd46a5c56c7abddef6a84c8002777e9efb2b3c3573286de679534ba56"
)
EXPECTED_VERIFICATION_BYTE_COUNT = 2_907
EXPECTED_VERIFICATION_SHA256 = (
    "aa4e9d5e904ec1b43194cbb74eb967bb99bdebd70f54cbb5b4c1534fad1eb249"
)


_CHECKPOINT_KEYS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "arm",
    "block_index",
    "compiled_model",
    "completed_row_ids",
    "execution_preregistration_id",
    "failure_message",
    "failure_type",
    "manifest_index",
    "official_execution_allowed",
    "previous_checkpoint_id",
    "progress_checkpoint_id",
    "schema",
    "sequence",
    "source_label_count",
    "source_observations",
    "stage",
    "target_outcome_progress_not_success_claim",
}


def _verify_checkpoint(raw: bytes, sequence: int) -> dict[str, Any]:
    document = loads_canonical_json(raw)
    expected_arm = (
        "REUSED_SUBPROGRAM_PRIOR" if sequence <= 6 else "EMPTY_ARCHIVE_NO_PRIOR"
    )
    local = sequence if sequence <= 6 else sequence - 7
    expected_stage = (
        "ACQUISITION_BLOCK_RETAINED_BEFORE_MINIMUM"
        if local == 0
        else "ACQUISITION_ARM_COMPLETE"
        if local == 6
        else "ACQUISITION_BLOCK_COMPILED"
    )
    expected_count = 16 if local == 0 else 16 * (local + 1) if local <= 5 else 96
    if (
        type(document) is not dict
        or set(document) != _CHECKPOINT_KEYS
        or canonical_json_bytes(document) != raw
        or len(raw) != EXPECTED_CHECKPOINT_BYTE_COUNTS[sequence]
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CHECKPOINT_SHA256[sequence]
        or document["schema"] != "acfqp.open_world_progress_checkpoint.v181r2"
        or document["execution_preregistration_id"]
        != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
        or document["sequence"] != sequence
        or document["previous_checkpoint_id"]
        != (EXPECTED_CHECKPOINT_IDS[sequence - 1] if sequence else None)
        or document["progress_checkpoint_id"] != EXPECTED_CHECKPOINT_IDS[sequence]
        or document["stage"] != expected_stage
        or document["manifest_index"] != 0
        or document["arm"] != expected_arm
        or document["block_index"] != min(local, 5)
        or document["source_label_count"] != expected_count
        or type(document["source_observations"]) is not list
        or len(document["source_observations"]) != expected_count
        or document["failure_type"] is not None
        or document["failure_message"] is not None
        or document["completed_row_ids"] != []
        or document["target_outcome_progress_not_success_claim"] is not True
        or document["official_execution_allowed"] is not False
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
        or (local == 0 and document["compiled_model"] is not None)
        or (local != 0 and type(document["compiled_model"]) is not dict)
    ):
        raise ValueError(f"V181r2 checkpoint {sequence} bytes or semantics changed")
    payload = dict(document)
    checkpoint_id = payload.pop("progress_checkpoint_id")
    if checkpoint_id != domains.extension_content_id_v181r2(
        domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V181R2_DOMAIN,
        payload,
    ):
        raise ValueError(f"V181r2 checkpoint {sequence} content ID changed")
    return document


def verify_open_world_campaign_failure_bundle_v181r2(
    failure_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> dict[str, Any]:
    if type(checkpoint_raws) not in {tuple, list} or len(checkpoint_raws) != 14:
        raise ValueError("V181r2 exact checkpoint denominator changed")
    checkpoints = [
        _verify_checkpoint(raw, sequence)
        for sequence, raw in enumerate(checkpoint_raws)
    ]
    document = loads_canonical_json(failure_raw)
    keys = {
        "COUNTER_COMPLETENESS_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "durable_checkpoint_count",
        "execution_preregistration_id",
        "failure_id",
        "failure_message",
        "failure_type",
        "last_arm",
        "last_block_index",
        "last_durable_progress_checkpoint_id",
        "last_durable_stage",
        "last_manifest_index",
        "official_execution_allowed",
        "same_identity_rerun_forbidden",
        "schema",
        "success_claimed",
        "target_outcome_run_started",
    }
    if (
        type(document) is not dict
        or set(document) != keys
        or canonical_json_bytes(document) != failure_raw
        or len(failure_raw) != EXPECTED_FAILURE_BYTE_COUNT
        or hashlib.sha256(failure_raw).hexdigest() != EXPECTED_FAILURE_SHA256
        or document["schema"] != "acfqp.open_world_campaign_failure.v181r2"
        or document["execution_preregistration_id"]
        != prereg.EXPECTED_EXECUTION_PREREGISTRATION_ID
        or document["failure_type"] != "KeyboardInterrupt"
        or document["failure_message"] != ""
        or document["target_outcome_run_started"] is not True
        or document["durable_checkpoint_count"] != 14
        or document["last_manifest_index"] != 0
        or document["last_arm"] != "EMPTY_ARCHIVE_NO_PRIOR"
        or document["last_block_index"] != 5
        or document["last_durable_stage"] != "ACQUISITION_ARM_COMPLETE"
        or document["last_durable_progress_checkpoint_id"]
        != checkpoints[-1]["progress_checkpoint_id"]
        or document["same_identity_rerun_forbidden"] is not True
        or document["success_claimed"] is not False
        or document["official_execution_allowed"] is not False
        or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN"
        or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN"
    ):
        raise ValueError("V181r2 failure bytes or semantics changed")
    payload = dict(document)
    failure_id = payload.pop("failure_id")
    if (
        failure_id != EXPECTED_FAILURE_ID
        or failure_id
        != domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_FAILURE_V181R2_DOMAIN,
            payload,
        )
    ):
        raise ValueError("V181r2 failure content ID changed")
    verification_payload = {
        "schema": "acfqp.open_world_campaign_failure_verification.v181r2",
        "failure_id": failure_id,
        "execution_preregistration_id": document["execution_preregistration_id"],
        "failure_bytes_sha256": EXPECTED_FAILURE_SHA256,
        "checkpoint_count": len(checkpoints),
        "checkpoint_ids": list(EXPECTED_CHECKPOINT_IDS),
        "checkpoint_bytes_sha256": list(EXPECTED_CHECKPOINT_SHA256),
        "last_durable_progress_checkpoint_id": EXPECTED_CHECKPOINT_IDS[-1],
        "typed_operator_interruption_independently_verified": True,
        "resource_cap_violation_observed": False,
        "scientific_campaign_success_independently_verified": False,
        "scientific_campaign_failure_independently_verified": False,
        "performance_successor_requires_fresh_identity": True,
        "same_identity_rerun_forbidden_independently_verified": True,
        "official_execution_allowed": False,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_VERIFICATION_V181R2_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignFailureVerificationV181R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def freeze_open_world_campaign_failure_verification_v181r2(
    failure_raw: bytes,
    checkpoint_raws: Sequence[bytes],
) -> OpenWorldCampaignFailureVerificationV181R2:
    document = verify_open_world_campaign_failure_bundle_v181r2(
        failure_raw,
        checkpoint_raws,
    )
    canonical = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(canonical) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(canonical).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        raise ValueError("V181r2 frozen failure verification changed")
    return OpenWorldCampaignFailureVerificationV181R2(
        _ISSUER,
        canonical,
        document["verification_id"],
    )


__all__ = (
    "EXPECTED_FAILURE_ID",
    "EXPECTED_VERIFICATION_ID",
    "freeze_open_world_campaign_failure_verification_v181r2",
    "verify_open_world_campaign_failure_bundle_v181r2",
)
