"""Fresh-target one-shot execution registration for V185."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp import construction_k7_open_world_composite_macro_manifest_reveal_v185 as reveal
from acfqp import construction_k7_open_world_composite_macro_protocol_v185 as protocol
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_PREREGISTRATION_ID = "32c73702b5a69c3b2b004ce40086a7f6fd2d2c80d5ab2e869a8cc5a05b17e48f"
EXPECTED_CANONICAL_BYTE_COUNT = 4_759
EXPECTED_CANONICAL_SHA256 = "a61ef16c757d1e77dfbdcfae51e8b3438e2fccae1ba5d300e71a4efe2b6a801b"

_SOURCE_PATHS = (
    "src/acfqp/construction_k7_domain_registry_extension_v185.py",
    "src/acfqp/construction_k7_open_world_composite_macro_protocol_v185.py",
    "src/acfqp/construction_k7_open_world_composite_macro_manifest_reveal_v185.py",
    "src/acfqp/open_world_composite_macro_machine_v185.py",
    "src/acfqp/open_world_adaptive_composite_synthesizer_v185.py",
    "src/acfqp/open_world_composite_macro_oracle_v185.py",
    "src/acfqp/construction_k7_open_world_composite_macro_campaign_v185.py",
    "src/acfqp/construction_k7_open_world_composite_macro_independent_verifier_v185.py",
    "src/acfqp/open_world_ranked_machine_v183.py",
    "src/acfqp/open_world_universal_machine_v182.py",
    "src/acfqp/open_world_machine_compiled_model_v182.py",
    "src/acfqp/phase3e_ids.py",
    "scripts/run_v185_open_world_composite_macro_campaign.py",
)


def _fact(root: Path, relative_path: str) -> dict[str, Any]:
    raw = (root / relative_path).read_bytes()
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def build_open_world_composite_macro_execution_preregistration_v185() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    protocol_document = protocol.freeze_open_world_composite_macro_protocol_v185().to_document()
    reveal_document = reveal.freeze_open_world_composite_macro_manifest_reveal_v185().to_document()
    output = root / ".tmp" / "exact-freeze" / "v185_composite_macro_campaign"
    payload = {
        "schema": "acfqp.open_world_composite_macro_execution_preregistration.v185",
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_verification_id": protocol_document["predecessor_verification_id"],
        "predecessor_evidence_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V185),
        "source_checkpoint_label_counts": [24, 28],
        "source_checkpoint_rule_frozen_before_fresh_target_access": True,
        "offline_source_training_is_not_held_out_target_evidence": True,
        "offline_source_development_access_occurred": True,
        "fresh_target_outcomes_accessed": False,
        "source_facts": [_fact(root, path) for path in _SOURCE_PATHS],
        "entrypoint": (
            "acfqp.construction_k7_open_world_composite_macro_campaign_v185:"
            "run_open_world_composite_macro_campaign_v185"
        ),
        "output_root_relative_path": ".tmp/exact-freeze/v185_composite_macro_campaign",
        "output_root_must_be_absent": True,
        "campaign_output_must_be_absent": True,
        "verification_output_must_be_absent": True,
        "failure_output_must_be_absent": True,
        "output_root_absent_at_preregistration": not output.exists(),
        "same_identity_rerun_after_any_progress_forbidden": True,
        "no_other_registered_full_campaign_may_run_concurrently": True,
        "target_execution_started": False,
        "actual_worker_process_count": 0,
        "producer_free_reconstruction_required": True,
        "partial_campaign_cannot_unlock_any_gate": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "only_macro_library_prior_toggled_between_arms": True,
        "positive_exact_token_mdl_macro_required": True,
        "target_macro_instantiations_revalidated_on_every_current_row": True,
        "strict_ood_rejection_before_query_required": True,
        "new_low_level_primitive_opcode_invention_claimed": False,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    if payload["output_root_absent_at_preregistration"] is not True:
        raise ValueError("V185 target output exists before preregistration")
    return {
        **payload,
        "execution_preregistration_id": domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_EXECUTION_PREREGISTRATION_V185_DOMAIN,
            payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCompositeMacroExecutionPreregistrationV185:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    execution_preregistration_id: str

    def to_document(self) -> dict[str, Any]:
        document = loads_canonical_json(self.canonical_bytes)
        if type(document) is not dict:
            raise ValueError("V185 execution preregistration is not canonical")
        return document


@lru_cache(maxsize=1)
def freeze_open_world_composite_macro_execution_preregistration_v185() -> OpenWorldCompositeMacroExecutionPreregistrationV185:
    document = build_open_world_composite_macro_execution_preregistration_v185()
    raw = canonical_json_bytes(document)
    if EXPECTED_PREREGISTRATION_ID != "0" * 64 and not (
        document["execution_preregistration_id"] == EXPECTED_PREREGISTRATION_ID
        and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
    ):
        raise ValueError("V185 execution preregistration changed")
    return OpenWorldCompositeMacroExecutionPreregistrationV185(
        _ISSUER,
        raw,
        document["execution_preregistration_id"],
    )


__all__ = (
    "EXPECTED_PREREGISTRATION_ID",
    "build_open_world_composite_macro_execution_preregistration_v185",
    "freeze_open_world_composite_macro_execution_preregistration_v185",
)
